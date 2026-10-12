"""Hybrid Retriever = OpenAI 임베딩 코사인 유사도 + 한국어 문자 bigram 키워드 점수 + 메뉴명 정확 매칭 보너스.

- 임베딩: 의미 기반 검색 ("달콤한 거" → 단맛 높은 메뉴/추천 가이드)
- bigram: 한국어는 띄어쓰기/조사 변형이 많아 단어 단위보다 문자 bigram이 견고함
- 메뉴명 보너스: "아메리카노" 처럼 메뉴명이 직접 언급되면 해당 메뉴 문서를 반드시 상위에 올림
임베딩은 data/.cache 에 저장해 재실행 시 API 비용이 들지 않는다.
API 키가 없으면 키워드 검색만으로 동작한다 (오프라인 테스트용).
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from .documents import Document
from .menu import Menu


def _bigrams(text: str) -> set[str]:
    t = "".join(text.lower().split())
    return {t[i:i + 2] for i in range(len(t) - 1)}


class HybridRetriever:
    def __init__(self, docs: list[Document], menu: Menu, client=None,
                 embed_model: str = "text-embedding-3-small", cache_dir: Path | None = None,
                 semantic_weight: float = 0.7):
        self.docs = docs
        self.menu = menu
        self.client = client
        self.embed_model = embed_model
        self.cache_dir = cache_dir
        self.semantic_weight = semantic_weight if client else 0.0
        self._doc_bigrams = [_bigrams(d.title + " " + d.text) for d in docs]
        self._title_bigrams = [_bigrams(d.title) for d in docs]
        self.doc_vectors = self._load_or_build_embeddings() if client else None

    # ---------- 임베딩 ----------
    def _embed(self, texts: list[str]) -> np.ndarray:
        resp = self.client.embeddings.create(model=self.embed_model, input=texts)
        vecs = np.array([d.embedding for d in resp.data], dtype=np.float32)
        return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    def _load_or_build_embeddings(self) -> np.ndarray:
        texts = [d.text for d in self.docs]
        digest = hashlib.sha256(json.dumps([self.embed_model, texts], ensure_ascii=False).encode()).hexdigest()[:16]
        cache = self.cache_dir / f"embeddings_{digest}.npy" if self.cache_dir else None
        if cache and cache.exists():
            return np.load(cache)
        vecs = self._embed(texts)
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            np.save(cache, vecs)
        return vecs

    # ---------- 검색 ----------
    def search(self, query: str, k: int = 5) -> list[tuple[Document, float]]:
        n = len(self.docs)
        semantic = np.zeros(n, dtype=np.float32)
        if self.doc_vectors is not None:
            semantic = self.doc_vectors @ self._embed([query])[0]

        qb = _bigrams(query)
        keyword = np.zeros(n, dtype=np.float32)
        if qb:
            for i in range(n):
                keyword[i] = (len(qb & self._doc_bigrams[i]) / len(qb)) * 0.6 \
                           + (len(qb & self._title_bigrams[i]) / len(qb)) * 0.4

        scores = self.semantic_weight * semantic + (1 - self.semantic_weight) * keyword
        for item in self.menu.names_in_text(query):
            idx = next(i for i, d in enumerate(self.docs) if d.id == f"item:{item['id']}")
            scores[idx] += 1.0

        top = np.argsort(-scores)[:k]
        return [(self.docs[i], float(scores[i])) for i in top]

    def multi_search(self, queries: list[str], k_each: int = 4, k_total: int = 8) -> list[tuple[Document, float]]:
        """복합 질의를 분해한 하위 질의별로 검색해 합친다 (중복 제거, 최고 점수 유지)."""
        best: dict[str, tuple[Document, float]] = {}
        for q in queries:
            for doc, score in self.search(q, k_each):
                if doc.id not in best or best[doc.id][1] < score:
                    best[doc.id] = (doc, score)
        return sorted(best.values(), key=lambda x: -x[1])[:k_total]
