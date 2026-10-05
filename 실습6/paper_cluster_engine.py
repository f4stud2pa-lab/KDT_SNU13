"""
논문 유사도 분석 및 군집화 핵심 엔진 (paper_cluster_engine.py)
============================================================
주요 기능:
1. PDF 파일에서 텍스트 자동 추출 (pypdf 지원 및 내장 PDF 1.4 스트림 디코더 Fallback)
2. 논문 메타데이터 파싱 (Title, Abstract, Keywords, Body Sections)
3. 텍스트 임베딩 생성 (OpenAI API 및 고성능 내장 TF-IDF/N-gram 벡터라이저 지원)
4. 코사인 유사도(Cosine Similarity) 행렬 계산
5. K-Means 군집화 (사용자 지정 K, K-Means++ 초기화, Scikit-learn 및 내장 알고리즘 지원)
6. PCA 차원 축소 (2D 및 3D 시각화 좌표 생성)
7. 클러스터별 대표 키워드 및 통계 요약 추출
"""

import math
import os
import re
import sys
import zlib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

# ---------------------------------------------------------------------------
# 외부 라이브러리 가용성 체크 (우아한 Fallback 지원)
# ---------------------------------------------------------------------------
# 1. PyPDF
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# 2. Scikit-learn
try:
    from sklearn.cluster import KMeans as SklearnKMeans
    from sklearn.decomposition import PCA as SklearnPCA
    from sklearn.feature_extraction.text import TfidfVectorizer as SklearnTfidf
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# 3. OpenAI
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# 4. python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 수동 .env 로드
    env_file = Path(".env")
    if not env_file.exists():
        env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("\"'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 데이터 구조체 (Dataclasses)
# ---------------------------------------------------------------------------
@dataclass
class PaperDocument:
    """단일 연구 논문 문서 객체"""
    doc_id: int
    filename: str
    file_path: str
    title: str = ""
    authors: str = ""
    journal: str = ""
    category_hint: str = ""
    abstract: str = ""
    keywords: str = ""
    full_text: str = ""
    embedding: Optional[np.ndarray] = None
    cluster_id: int = -1
    pca_2d: Optional[Tuple[float, float]] = None
    pca_3d: Optional[Tuple[float, float, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "category_hint": self.category_hint,
            "abstract": self.abstract[:200] + "..." if len(self.abstract) > 200 else self.abstract,
            "keywords": self.keywords,
            "cluster_id": self.cluster_id,
            "pca_2d": self.pca_2d,
            "pca_3d": self.pca_3d
        }


# ---------------------------------------------------------------------------
# 1. PDF 텍스트 추출 모듈 (PDFTextExtractor)
# ---------------------------------------------------------------------------
class PDFTextExtractor:
    """
    PDF 파일에서 텍스트를 추출하고 논문 구조(제목, 초록, 키워드 등)를 파싱합니다.
    """
    @staticmethod
    def extract_text(file_path: Union[str, Path]) -> str:
        """PDF 파일에서 텍스트를 추출 (pypdf 사용 시도 후 내장 파서 fallback)"""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {path}")

        # 1. pypdf 시도
        if HAS_PYPDF:
            try:
                reader = pypdf.PdfReader(str(path))
                text_pages = []
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        text_pages.append(t)
                full_text = "\n".join(text_pages).strip()
                if len(full_text) > 50:
                    return full_text
            except Exception:
                pass

        # 2. 내장 순수 파이썬 PDF 스트림 파서 Fallback
        return PDFTextExtractor._extract_raw_stream(path)

    @staticmethod
    def _extract_raw_stream(path: Path) -> str:
        """표준 PDF 바이너리 스트림에서 텍스트 연산자(BT...ET, Tj, TJ) 추출"""
        with open(path, "rb") as f:
            data = f.read()

        extracted_lines = []
        # stream ~ endstream 블록 정규식 탐색
        stream_matches = re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.DOTALL)
        for m in stream_matches:
            stream_data = m.group(1)
            # zlib 압축 해제 시도
            try:
                content = zlib.decompress(stream_data)
            except Exception:
                content = stream_data

            # 텍스트 연산자 파싱
            text_chunks = PDFTextExtractor._parse_pdf_operators(content)
            if text_chunks:
                extracted_lines.extend(text_chunks)

        full_text = "\n".join(extracted_lines).strip()
        if not full_text:
            # 바이너리 내 괄호 문자열 직접 수집 (최후의 수단)
            ascii_matches = re.findall(rb"\(([A-Za-z0-9 ,.\-_:;?!\(\)]{3,})\)", data)
            full_text = "\n".join(m.decode("latin-1", errors="ignore") for m in ascii_matches)

        return full_text

    @staticmethod
    def _parse_pdf_operators(stream_bytes: bytes) -> List[str]:
        """PDF 연산자(BT, ET, Tj, TJ)를 순회하며 텍스트 추출"""
        text_lines = []
        try:
            content_str = stream_bytes.decode("latin-1", errors="ignore")
        except Exception:
            return text_lines

        # 괄호 안의 문자열 뒤에 Tj 또는 TJ 연산자가 붙은 패턴 매칭
        # 예: (Attention Mechanisms) Tj 또는 [(Hello) 10 (World)] TJ
        tj_patterns = re.findall(r"\((.*?)\)\s*Tj", content_str)
        if tj_patterns:
            for item in tj_patterns:
                # 이스케이프 복원
                clean = item.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\").strip()
                if clean:
                    text_lines.append(clean)
        else:
            # TJ 배열 형식
            array_matches = re.findall(r"\[(.*?)\]\s*TJ", content_str)
            for arr in array_matches:
                inner_strings = re.findall(r"\((.*?)\)", arr)
                line = " ".join(inner_strings).strip()
                if line:
                    text_lines.append(line)

        return text_lines

    @classmethod
    def parse_paper(cls, file_path: Union[str, Path], doc_id: int) -> PaperDocument:
        """PDF 텍스트를 파싱하여 구조화된 PaperDocument 생성"""
        path = Path(file_path).resolve()
        raw_text = cls.extract_text(path)
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        filename = path.name
        title = ""
        authors = ""
        journal = ""
        category_hint = ""
        abstract = ""
        keywords = ""

        # 라인 기반 메타데이터 추출
        for idx, line in enumerate(lines):
            # Title 탐색 (초기 라인 중 적절한 길이의 문장)
            if not title and not line.startswith("---") and not line.startswith("Authors:"):
                if len(line) > 15:
                    title = line

            if line.startswith("Authors:"):
                authors = line.replace("Authors:", "").strip()
            elif line.startswith("Journal:"):
                parts = line.split("|")
                journal = parts[0].replace("Journal:", "").strip()
                if len(parts) > 1 and "Category:" in parts[1]:
                    category_hint = parts[1].replace("Category:", "").strip()
            elif "Keywords:" in line:
                keywords = line.split("Keywords:", 1)[1].strip()

        # Abstract 추출
        raw_lower = raw_text.lower()
        if "abstract" in raw_lower:
            try:
                abs_part = re.split(r"abstract", raw_text, flags=re.IGNORECASE)[1]
                # keywords나 다음 섹션 전까지 자르기
                end_markers = ["keywords:", "1. introduction", "1.", "introduction"]
                min_end_pos = len(abs_part)
                for em in end_markers:
                    pos = abs_part.lower().find(em)
                    if pos != -1 and pos < min_end_pos:
                        min_end_pos = pos
                abstract = abs_part[:min_end_pos].strip()
                abstract = re.sub(r"\s+", " ", abstract)
            except Exception:
                abstract = ""

        # Fallback 처리: 파일명 및 본문 앞부분 활용
        if not title:
            clean_name = path.stem.replace("_", " ")
            title = clean_name
        if not abstract and len(raw_text) > 100:
            abstract = raw_text[:350].strip()

        return PaperDocument(
            doc_id=doc_id,
            filename=filename,
            file_path=str(path),
            title=title,
            authors=authors,
            journal=journal,
            category_hint=category_hint,
            abstract=abstract,
            keywords=keywords,
            full_text=raw_text
        )


# ---------------------------------------------------------------------------
# 2. 내장 고성능 TF-IDF 벡터라이저 (Numpy 기반)
# ---------------------------------------------------------------------------
# 학술 논문 분석용 불용어 세트
ENGLISH_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "did", "do", "does", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is",
    "it", "its", "itself", "let's", "me", "more", "most", "my", "myself", "no",
    "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "we", "were", "what", "when", "where",
    "which", "while", "who", "whom", "why", "with", "would", "you", "your", "yours",
    "yourself", "yourselves", "paper", "presents", "study", "approach", "results",
    "proposed", "using", "based", "demonstrate", "show", "findings", "evaluate"
}


class BuiltinTfidfVectorizer:
    """
    외부 의존성 없이 Numpy만으로 동작하는 TF-IDF + N-gram 벡터라이저.
    학술 논문의 전문 용어(Bigram)를 포착하고 L2 단위 벡터로 정규화합니다.
    """
    def __init__(self, max_features: int = 500, ngram_range: Tuple[int, int] = (1, 2)):
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.vocabulary_: Dict[str, int] = {}
        self.feature_names_: List[str] = []
        self.idf_: Optional[np.ndarray] = None

    def _tokenize(self, text: str) -> List[str]:
        """텍스트 정제 및 유의미한 토큰/불용어 필터링"""
        text = text.lower()
        # 영문 알파벳 및 하이픈 단어 추출
        raw_tokens = re.findall(r"\b[a-z][a-z0-9\-]{2,}\b", text)
        filtered = [t for t in raw_tokens if t not in ENGLISH_STOPWORDS and not t.isdigit()]

        tokens = []
        # 1-gram
        if self.ngram_range[0] <= 1:
            tokens.extend(filtered)

        # 2-gram (Bigram)
        if self.ngram_range[1] >= 2 and len(filtered) >= 2:
            for i in range(len(filtered) - 1):
                tokens.append(f"{filtered[i]}_{filtered[i+1]}")

        return tokens

    def fit_transform(self, documents: List[str]) -> np.ndarray:
        """문서 코퍼스 학습 및 TF-IDF 행렬 반환"""
        doc_tokens = [self._tokenize(doc) for doc in documents]
        n_docs = len(documents)

        # 전체 단어 빈도(Document Frequency) 계산
        df_counts: Dict[str, int] = {}
        total_counts: Dict[str, int] = {}

        for tokens in doc_tokens:
            seen_in_doc = set(tokens)
            for t in seen_in_doc:
                df_counts[t] = df_counts.get(t, 0) + 1
            for t in tokens:
                total_counts[t] = total_counts.get(t, 0) + 1

        # 상위 빈도 단어 선정 (적어도 1개 문서 이상 출현)
        sorted_vocab = sorted(
            df_counts.keys(),
            key=lambda w: (df_counts[w], total_counts[w]),
            reverse=True
        )[:self.max_features]

        self.vocabulary_ = {word: idx for idx, word in enumerate(sorted_vocab)}
        self.feature_names_ = sorted_vocab

        # Smooth IDF 계산: ln((1 + N) / (1 + df)) + 1
        idf_vals = []
        for word in sorted_vocab:
            df = df_counts[word]
            idf = math.log((1 + n_docs) / (1 + df)) + 1.0
            idf_vals.append(idf)
        self.idf_ = np.array(idf_vals, dtype=np.float64)

        # TF-IDF 행렬 구성
        tfidf_matrix = np.zeros((n_docs, len(sorted_vocab)), dtype=np.float64)
        for doc_idx, tokens in enumerate(doc_tokens):
            term_counts: Dict[str, int] = {}
            for t in tokens:
                if t in self.vocabulary_:
                    term_counts[t] = term_counts.get(t, 0) + 1

            for word, count in term_counts.items():
                col_idx = self.vocabulary_[word]
                # Sublinear TF scaling: 1 + log(tf)
                tf = 1.0 + math.log(count)
                tfidf_matrix[doc_idx, col_idx] = tf * self.idf_[col_idx]

        # L2 행 정규화 (각 문서 벡터의 크기를 1로 변환)
        norms = np.linalg.norm(tfidf_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = tfidf_matrix / norms
        return normalized


# ---------------------------------------------------------------------------
# 3. 텍스트 임베딩 통합 엔진 (EmbeddingEngine)
# ---------------------------------------------------------------------------
class EmbeddingEngine:
    """
    OpenAI API 임베딩 및 로컬 고성능 TF-IDF 벡터 임베딩을 제공합니다.
    """
    def __init__(self, mode: str = "auto", openai_model: str = "text-embedding-3-small"):
        self.mode = mode
        self.openai_model = openai_model
        self.vectorizer: Optional[Any] = None
        self.active_backend: str = "tfidf"

        # OpenAI 클라이언트 초기화 검사
        self.openai_client = None
        api_key = os.getenv("OPENAI_API_KEY")
        if HAS_OPENAI and api_key and not api_key.startswith("your_openai"):
            try:
                self.openai_client = OpenAI(api_key=api_key)
                if self.mode in ("auto", "openai"):
                    self.active_backend = "openai"
            except Exception:
                self.openai_client = None

        if self.mode == "tfidf":
            self.active_backend = "tfidf"

    def generate_embeddings(self, papers: List[PaperDocument]) -> np.ndarray:
        """논문 목록으로부터 임베딩 행렬 (N, D) 생성"""
        # 논문별 대표 텍스트 조합 (제목과 초록 및 키워드에 높은 비중 부여)
        corpus = []
        for p in papers:
            # 제목 x 2, 초록 x 2, 키워드 x 3, 본문 1
            combined = (
                f"{p.title}\n{p.title}\n"
                f"{p.keywords}\n{p.keywords}\n{p.keywords}\n"
                f"{p.abstract}\n{p.abstract}\n"
                f"{p.full_text}"
            )
            corpus.append(combined)

        # 1. OpenAI 모드 시도
        if self.active_backend == "openai" and self.openai_client is not None:
            try:
                embeddings = []
                for text in corpus:
                    # 8000자 제한
                    truncated = text[:8000]
                    resp = self.openai_client.embeddings.create(
                        input=truncated,
                        model=self.openai_model
                    )
                    vec = np.array(resp.data[0].embedding, dtype=np.float64)
                    # L2 정규화
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec /= norm
                    embeddings.append(vec)
                return np.array(embeddings)
            except Exception as e:
                print(f"⚠️ OpenAI API 호출 실패 ({e}). 로컬 TF-IDF 모드로 자동 전환합니다.")
                self.active_backend = "tfidf"

        # 2. 로컬 TF-IDF 모드
        if HAS_SKLEARN:
            self.vectorizer = SklearnTfidf(
                max_features=500,
                ngram_range=(1, 2),
                sublinear_tf=True,
                stop_words="english"
            )
            emb_matrix = self.vectorizer.fit_transform(corpus).toarray()
            # L2 정규화
            norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return emb_matrix / norms
        else:
            self.vectorizer = BuiltinTfidfVectorizer(max_features=500, ngram_range=(1, 2))
            return self.vectorizer.fit_transform(corpus)

    def get_feature_names(self) -> List[str]:
        """추출된 어휘 목록 반환"""
        if self.vectorizer is None:
            return []
        if hasattr(self.vectorizer, "get_feature_names_out"):
            return list(self.vectorizer.get_feature_names_out())
        elif hasattr(self.vectorizer, "feature_names_"):
            return self.vectorizer.feature_names_
        return []


# ---------------------------------------------------------------------------
# 4. 내장 K-Means 군집화 (KMeansCustom - Scikit-learn Fallback)
# ---------------------------------------------------------------------------
class BuiltinKMeans:
    """
    Numpy 기반의 K-Means++ 군집화 구현.
    - K-Means++ 스마트 초기화
    - 코사인 거리 / 유클리드 거리 기반 최적화
    - 다중 재실행(n_init) 지원
    """
    def __init__(self, n_clusters: int = 4, max_iter: int = 150, n_init: int = 10, random_state: int = 42):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.n_init = n_init
        self.random_state = random_state
        self.cluster_centers_: Optional[np.ndarray] = None
        self.labels_: Optional[np.ndarray] = None
        self.inertia_: float = float("inf")

    def _kmeans_plus_plus_init(self, X: np.ndarray, rng: np.random.RandomState) -> np.ndarray:
        """K-Means++ 중심점 초기화"""
        n_samples, n_features = X.shape
        centers = np.empty((self.n_clusters, n_features), dtype=X.dtype)

        # 1번째 중심점은 무작위 선택
        first_idx = rng.randint(0, n_samples)
        centers[0] = X[first_idx]

        # 2번째부터는 기존 중심점들과의 최소 거리 제곱에 비례하여 확률적으로 선택
        for c_idx in range(1, self.n_clusters):
            dists = np.full(n_samples, float("inf"))
            for j in range(c_idx):
                diff = X - centers[j]
                d = np.sum(diff * diff, axis=1)
                dists = np.minimum(dists, d)

            probs = dists / np.sum(dists) if np.sum(dists) > 0 else np.ones(n_samples) / n_samples
            next_idx = rng.choice(n_samples, p=probs)
            centers[c_idx] = X[next_idx]

        return centers

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """군집화 수행 및 레이블 반환"""
        n_samples, n_features = X.shape
        k = min(self.n_clusters, n_samples)

        best_inertia = float("inf")
        best_centers = None
        best_labels = None

        rng = np.random.RandomState(self.random_state)

        for _ in range(self.n_init):
            centers = self._kmeans_plus_plus_init(X, rng)
            labels = np.zeros(n_samples, dtype=int)

            for _ in range(self.max_iter):
                # 유클리드 거리 행렬 계산
                dists = np.zeros((n_samples, k))
                for c_idx in range(k):
                    diff = X - centers[c_idx]
                    dists[:, c_idx] = np.sum(diff * diff, axis=1)

                new_labels = np.argmin(dists, axis=1)

                # 수렴 체크
                if np.array_equal(labels, new_labels):
                    break
                labels = new_labels

                # 중심점 갱신
                new_centers = np.zeros_like(centers)
                for c_idx in range(k):
                    members = X[labels == c_idx]
                    if len(members) > 0:
                        new_centers[c_idx] = np.mean(members, axis=0)
                    else:
                        # 빈 클러스터는 무작위 샘플 할당
                        new_centers[c_idx] = X[rng.randint(0, n_samples)]
                centers = new_centers

            # 관성(Inertia) 계산: 오차 제곱합
            cur_inertia = 0.0
            for c_idx in range(k):
                members = X[labels == c_idx]
                if len(members) > 0:
                    cur_inertia += float(np.sum((members - centers[c_idx]) ** 2))

            if cur_inertia < best_inertia:
                best_inertia = cur_inertia
                best_centers = centers.copy()
                best_labels = labels.copy()

        self.cluster_centers_ = best_centers
        self.labels_ = best_labels
        self.inertia_ = best_inertia
        return self.labels_


# ---------------------------------------------------------------------------
# 5. 내장 SVD 기반 PCA 차원 축소기 (PCAReducer)
# ---------------------------------------------------------------------------
class BuiltinPCA:
    """
    Numpy SVD(특이값 분해) 기반의 고정밀 주성분 분석(PCA).
    2D 및 3D 차원으로 임베딩 벡터를 축소합니다.
    """
    def __init__(self, n_components: int = 2):
        self.n_components = n_components
        self.components_: Optional[np.ndarray] = None
        self.explained_variance_ratio_: Optional[np.ndarray] = None
        self.mean_: Optional[np.ndarray] = None

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        n_samples, n_features = X.shape
        self.mean_ = np.mean(X, axis=0)
        X_centered = X - self.mean_

        # SVD: X = U * S * V^T
        U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)
        self.components_ = Vt[:self.n_components]

        # 설명 분산 비율 계산
        explained_variance = (S ** 2) / (n_samples - 1) if n_samples > 1 else S ** 2
        total_var = np.sum(explained_variance)
        if total_var > 0:
            self.explained_variance_ratio_ = (explained_variance[:self.n_components]) / total_var
        else:
            self.explained_variance_ratio_ = np.ones(self.n_components) / self.n_components

        # 저차원 투영: X_projected = X_centered @ Vt^T
        transformed = np.dot(X_centered, self.components_.T)
        return transformed


# ---------------------------------------------------------------------------
# 6. 논문 군집화 및 분석 종합 엔진 (PaperClusteringEngine)
# ---------------------------------------------------------------------------
class PaperClusteringEngine:
    """
    전체 워크플로우를 관장하는 메인 엔진 클래스:
    1. 디렉토리 내 PDF 스캔 및 텍스트 추출
    2. 벡터 임베딩 생성
    3. 코사인 유사도 행렬 계산
    4. K-Means 클러스터링
    5. PCA 2D/3D 축소 및 클러스터 메타데이터 분석
    """
    def __init__(self, n_clusters: int = 4, embedding_mode: str = "auto", random_state: int = 42):
        self.n_clusters = n_clusters
        self.embedding_mode = embedding_mode
        self.random_state = random_state

        self.papers: List[PaperDocument] = []
        self.embeddings: Optional[np.ndarray] = None
        self.similarity_matrix: Optional[np.ndarray] = None
        self.cluster_labels: Optional[np.ndarray] = None
        self.cluster_keywords: Dict[int, List[Tuple[str, float]]] = {}
        self.cluster_summary: Dict[int, Dict[str, Any]] = {}

        self.embedding_engine = EmbeddingEngine(mode=self.embedding_mode)

    def load_papers(self, folder_path: Union[str, Path]) -> List[PaperDocument]:
        """디렉토리 내 모든 PDF 파일 로드 및 구조화 파싱"""
        folder = Path(folder_path).resolve()
        if not folder.exists():
            raise FileNotFoundError(f"논문 디렉토리가 존재하지 않습니다: {folder}")

        pdf_files = sorted(list(folder.glob("*.pdf")))
        if not pdf_files:
            raise ValueError(f"디렉토리 내에 PDF 파일이 없습니다: {folder}")

        self.papers = []
        for idx, pdf_path in enumerate(pdf_files):
            doc = PDFTextExtractor.parse_paper(pdf_path, doc_id=idx)
            self.papers.append(doc)

        return self.papers

    def compute_embeddings(self) -> np.ndarray:
        """논문들의 벡터 임베딩 생성"""
        if not self.papers:
            raise ValueError("로드된 논문이 없습니다. load_papers()를 먼저 호출하세요.")

        self.embeddings = self.embedding_engine.generate_embeddings(self.papers)
        for idx, p in enumerate(self.papers):
            p.embedding = self.embeddings[idx]

        return self.embeddings

    def compute_similarity_matrix(self) -> np.ndarray:
        """코사인 유사도(Cosine Similarity) 행렬 계산"""
        if self.embeddings is None:
            self.compute_embeddings()

        # 벡터가 L2 정규화되어 있으므로, Dot Product가 곧 코사인 유사도
        E = self.embeddings
        norms = np.linalg.norm(E, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_E = E / norms
        self.similarity_matrix = np.dot(normalized_E, normalized_E.T)
        # 수치 오차 보정 (-1.0 ~ 1.0)
        self.similarity_matrix = np.clip(self.similarity_matrix, -1.0, 1.0)
        return self.similarity_matrix

    def perform_clustering(self, k: Optional[int] = None) -> np.ndarray:
        """K-Means 군집화 수행"""
        if k is not None:
            self.n_clusters = k

        if self.embeddings is None:
            self.compute_embeddings()

        num_papers = len(self.papers)
        actual_k = min(self.n_clusters, num_papers)

        if HAS_SKLEARN:
            kmeans = SklearnKMeans(
                n_clusters=actual_k,
                init="k-means++",
                n_init=10,
                random_state=self.random_state
            )
            labels = kmeans.fit_predict(self.embeddings)
            centers = kmeans.cluster_centers_
        else:
            kmeans = BuiltinKMeans(
                n_clusters=actual_k,
                n_init=10,
                random_state=self.random_state
            )
            labels = kmeans.fit_predict(self.embeddings)
            centers = kmeans.cluster_centers_

        self.cluster_labels = labels

        # 각 논문에 클러스터 ID 할당
        for idx, p in enumerate(self.papers):
            p.cluster_id = int(labels[idx])

        # PCA 2D & 3D 차원 축소 좌표 계산
        self._compute_projections()

        # 클러스터별 대표 키워드 및 요약 정보 생성
        self._analyze_clusters(centers)

        return self.cluster_labels

    def _compute_projections(self):
        """PCA를 사용하여 2D 및 3D 시각화 좌표 계산"""
        if self.embeddings is None:
            return

        n_samples = len(self.papers)

        # 1. 2D PCA
        n_comp_2d = min(2, n_samples, self.embeddings.shape[1])
        if HAS_SKLEARN:
            pca_2d = SklearnPCA(n_components=n_comp_2d, random_state=self.random_state)
            coords_2d = pca_2d.fit_transform(self.embeddings)
        else:
            pca_2d = BuiltinPCA(n_components=n_comp_2d)
            coords_2d = pca_2d.fit_transform(self.embeddings)

        # 2. 3D PCA
        n_comp_3d = min(3, n_samples, self.embeddings.shape[1])
        if HAS_SKLEARN:
            pca_3d = SklearnPCA(n_components=n_comp_3d, random_state=self.random_state)
            coords_3d = pca_3d.fit_transform(self.embeddings)
        else:
            pca_3d = BuiltinPCA(n_components=n_comp_3d)
            coords_3d = pca_3d.fit_transform(self.embeddings)

        for idx, p in enumerate(self.papers):
            c2 = (float(coords_2d[idx, 0]), float(coords_2d[idx, 1]) if n_comp_2d > 1 else 0.0)
            c3 = (
                float(coords_3d[idx, 0]),
                float(coords_3d[idx, 1]) if n_comp_3d > 1 else 0.0,
                float(coords_3d[idx, 2]) if n_comp_3d > 2 else 0.0
            )
            p.pca_2d = c2
            p.pca_3d = c3

    def _analyze_clusters(self, centers: np.ndarray):
        """각 클러스터의 중심 벡터 및 소속 논문으로부터 핵심 키워드 추출"""
        feature_names = self.embedding_engine.get_feature_names()
        self.cluster_keywords = {}
        self.cluster_summary = {}

        for c_id in range(self.n_clusters):
            member_indices = [i for i, p in enumerate(self.papers) if p.cluster_id == c_id]
            member_papers = [self.papers[i] for i in member_indices]

            # 상위 키워드 추출
            top_keywords = []
            if feature_names and c_id < len(centers) and len(feature_names) == centers.shape[1]:
                center_vec = centers[c_id]
                top_indices = np.argsort(center_vec)[::-1][:6]
                for idx in top_indices:
                    val = float(center_vec[idx])
                    if val > 0:
                        word = feature_names[idx].replace("_", " ")
                        top_keywords.append((word, val))

            if not top_keywords:
                # 텍스트 단어 빈도 기반 Fallback
                all_text = " ".join([f"{p.title} {p.keywords} {p.abstract}" for p in member_papers]).lower()
                words = re.findall(r"\b[a-z]{3,}\b", all_text)
                freq: Dict[str, int] = {}
                for w in words:
                    if w not in ENGLISH_STOPWORDS:
                        freq[w] = freq.get(w, 0) + 1
                sorted_f = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:6]
                top_keywords = [(w, float(c)) for w, c in sorted_f]

            self.cluster_keywords[c_id] = top_keywords

            # 클러스터 대표 명칭/도메인 추정
            categories = [p.category_hint for p in member_papers if p.category_hint]
            dominant_category = max(set(categories), key=categories.count) if categories else "General"

            self.cluster_summary[c_id] = {
                "cluster_id": c_id,
                "count": len(member_papers),
                "dominant_category": dominant_category,
                "top_keywords": [k[0] for k in top_keywords],
                "papers": [p.to_dict() for p in member_papers]
            }

    def suggest_optimal_k(self, max_k: int = 6) -> int:
        """Elbow Method 및 관성 변화율을 기반으로 권장 K값 제안"""
        if self.embeddings is None:
            self.compute_embeddings()

        n_samples = len(self.papers)
        max_k = min(max_k, n_samples - 1)
        if max_k < 2:
            return 2

        inertias = []
        k_range = list(range(2, max_k + 1))

        for k in k_range:
            if HAS_SKLEARN:
                km = SklearnKMeans(n_clusters=k, init="k-means++", n_init=5, random_state=self.random_state)
                km.fit(self.embeddings)
                inertias.append(km.inertia_)
            else:
                km = BuiltinKMeans(n_clusters=k, n_init=5, random_state=self.random_state)
                km.fit_predict(self.embeddings)
                inertias.append(km.inertia_)

        # 급격한 변화율(Elbow Point) 탐색
        best_k = 4 if 4 in k_range else k_range[0]
        max_diff = -1
        for i in range(len(inertias) - 1):
            diff = inertias[i] - inertias[i + 1]
            if diff > max_diff:
                max_diff = diff
                best_k = k_range[i]

        return best_k
