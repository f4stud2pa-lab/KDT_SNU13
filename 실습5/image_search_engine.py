"""
텍스트 쿼리 기반 이미지 검색 및 분류 엔진 (image_search_engine.py)
=================================================================
주요 기능:
1. Vision API (OpenAI gpt-4o / gpt-4o-mini)를 활용한 이미지 시각 정보 텍스트 설명 자동 생성 및 캐싱 저장
2. OpenAI 임베딩 API (text-embedding-3-small)를 활용한 이미지 설명 및 검색 쿼리의 고차원 벡터 임베딩 변환
3. 코사인 유사도(Cosine Similarity) 계산을 통한 벡터 간 유사도 분석
4. 가장 관련성 높은 최상위 이미지 및 상위 K개(기본 Top 3) 랭킹 검색 결과 반환
5. [신규 확장] 임의의 이미지 분류 (Zero-Shot Image Classification via Embedding & Vision)
6. [신규 확장] 이미지-투-이미지 유사도 검색 (Image-to-Image Search)
7. [신규 확장] 임의의 신규 이미지 동적 추가 및 실시간 인덱싱 (Dynamic Image Ingestion)
8. 오프라인/테스트 환경을 위한 Graceful Fallback (시뮬레이션 임베딩 및 사전 설명 모드) 지원
"""

import base64
import json
import math
import mimetypes
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# OpenAI 공식 SDK 로드
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# dotenv 로드 시도 (없으면 내장 로더 사용)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def load_env_file_fallback(env_path: str = ".env"):
    """dotenv 라이브러리가 없을 때 표준 라이브러리로 .env 파일을 파싱합니다."""
    env_file = Path(env_path)
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("\"'")
                    if key and key not in os.environ:
                        os.environ[key] = val


# .env fallback 적용
load_env_file_fallback()


@dataclass
class ImageItem:
    """인덱싱된 개별 이미지 메타데이터"""
    image_id: str
    filename: str
    file_path: str
    title: str
    description: str
    embedding: List[float] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source: str = "vision_api"  # "vision_api", "cached", "preset", "user_added"


@dataclass
class SearchResult:
    """검색 결과 단위"""
    rank: int
    image_id: str
    filename: str
    file_path: str
    title: str
    description: str
    similarity: float
    score_percent: float

    def format_card(self) -> str:
        """결과를 보기 좋은 텍스트 카드로 포맷팅합니다."""
        bar_len = int(max(0.0, min(100.0, self.score_percent)) / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        return (
            f"┌────────────────────────────────────────────────────────────\n"
            f"│ 🏆 [순위 {self.rank}] {self.title} ({self.filename})\n"
            f"│ 📊 유사도: {self.similarity:.4f} ({self.score_percent:5.1f}%) [{bar}]\n"
            f"│ 📁 파일 경로: {self.file_path}\n"
            f"│ 📝 이미지 설명:\n"
            f"│    {self.description}\n"
            f"└────────────────────────────────────────────────────────────"
        )


@dataclass
class ClassificationResult:
    """이미지 분류 결과"""
    predicted_category: str
    confidence_percent: float
    similarity_score: float
    image_description: str
    reasoning: str
    all_category_scores: List[Tuple[str, float, float]]  # (카테고리명, 코사인 유사도, 퍼센트)

    def format_summary(self) -> str:
        lines = [
            "━" * 66,
            f" 🏷️ [이미지 분류 결과] 최적 카테고리: {self.predicted_category}",
            f" 📊 신뢰도/유사도: {self.similarity_score:.4f} ({self.confidence_percent:.1f}%)",
            f" 📝 이미지 분석 내용:\n   {self.image_description}",
            f" 💡 판단 사유:\n   {self.reasoning}",
            "━" * 66,
            " 📋 전체 카테고리별 유사도 순위:",
        ]
        for rank, (cat, sim, pct) in enumerate(self.all_category_scores, 1):
            bar = "█" * int(max(0.0, min(100.0, pct)) / 10)
            lines.append(f"  #{rank} {cat:<32} | {sim:+.4f} ({pct:5.1f}%) [{bar}]")
        lines.append("━" * 66)
        return "\n".join(lines)


class CosineSimilarityCalculator:
    """순수 파이썬 기반 고정밀 코사인 유사도 계산기"""

    @staticmethod
    def dot_product(vec_a: List[float], vec_b: List[float]) -> float:
        """두 벡터의 내적(Dot Product)을 계산합니다."""
        return sum(a * b for a, b in zip(vec_a, vec_b))

    @staticmethod
    def norm(vec: List[float]) -> float:
        """벡터의 L2 Norm(유클리드 노름)을 계산합니다."""
        return math.sqrt(sum(x * x for x in vec))

    @classmethod
    def calculate(cls, vec_a: List[float], vec_b: List[float]) -> float:
        """
        두 벡터 간의 코사인 유사도를 계산합니다.
        수식: cos(theta) = (A · B) / (||A|| * ||B||)
        """
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        norm_a = cls.norm(vec_a)
        norm_b = cls.norm(vec_b)

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        similarity = cls.dot_product(vec_a, vec_b) / (norm_a * norm_b)
        # 부동소수점 오차 보정 (-1.0 ~ 1.0 클리핑)
        return max(-1.0, min(1.0, similarity))


class SemanticFallbackEmbedder:
    """
    OpenAI API 키가 없거나 네트워크가 오프라인일 때 동작하는
    한국어 형태소/의미 기반 결정론적 시뮬레이션 임베더 (128차원)
    """

    DIMENSION = 128

    TOPIC_SEEDS = {
        "석양": [0, 1, 2],
        "일몰": [0, 1, 3],
        "노을": [0, 2, 4],
        "산": [0, 5, 6],
        "봉우리": [0, 5, 7],
        "자연": [0, 8, 9],
        "하늘": [0, 10, 11],
        "풍경": [0, 8, 12],
        "붉": [1, 2, 12],
        "황금": [1, 3, 13],

        "강아지": [20, 21, 22],
        "개": [20, 21, 23],
        "동물": [20, 24, 25],
        "반려": [20, 24, 26],
        "고양이": [20, 23, 27],
        "귀여": [21, 27, 28],
        "공원": [22, 29, 30],
        "잔디": [29, 30, 31],
        "뛰": [21, 32, 33],
        "놀": [21, 32, 34],

        "도시": [40, 41, 42],
        "스카이라인": [40, 41, 43],
        "야경": [40, 44, 45],
        "밤": [44, 45, 46],
        "빌딩": [41, 47, 48],
        "네온": [44, 48, 49],
        "도심": [40, 42, 50],
        "번화": [42, 49, 51],
        "건축": [41, 47, 52],

        "겨울": [60, 61, 62],
        "눈": [60, 61, 63],
        "설경": [60, 63, 64],
        "숲": [62, 65, 66],
        "침엽수": [65, 66, 67],
        "나무": [65, 68, 69],
        "고요": [61, 70, 71],
        "하얀": [60, 63, 72],

        "바다": [80, 81, 82],
        "해변": [80, 82, 83],
        "휴양지": [82, 84, 85],
        "백사장": [83, 86, 87],
        "야자수": [84, 87, 88],
        "파도": [81, 89, 90],
        "에메랄드": [80, 81, 91],
        "여름": [82, 85, 92],

        "음식": [100, 101, 102],
        "요리": [100, 102, 103],
        "식사": [100, 101, 104],
        "카페": [101, 105, 106],
        "디저트": [102, 106, 107],

        "인물": [110, 111, 112],
        "사람": [110, 111, 113],
        "얼굴": [111, 114, 115],
        "초상": [110, 115, 116]
    }

    @classmethod
    def get_embedding(cls, text: str) -> List[float]:
        vec = [0.0] * cls.DIMENSION
        text_lower = text.lower()

        for kw, dims in cls.TOPIC_SEEDS.items():
            if kw in text_lower:
                for d in dims:
                    vec[d] += 2.5

        clean_text = re.sub(r"[^\w\s]", "", text_lower)
        tokens = clean_text.split()
        for token in tokens:
            for i in range(len(token)):
                sub = token[i:i+2]
                h = abs(hash(sub)) % cls.DIMENSION
                vec[h] += 0.8

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        else:
            vec[0] = 1.0

        return vec


# 기본 카테고리 후보군 정의
DEFAULT_CLASSIFICATION_CATEGORIES = {
    "자연 및 풍경 (Nature & Landscape)": "산, 일몰, 석양, 숲, 바다, 해변, 하늘, 눈 등 광활하고 아름다운 자연 경관과 풍경",
    "동물 및 반려동물 (Animals & Pets)": "강아지, 고양이, 새, 야생동물 등 동물과 사랑스러운 반려동물이 뛰어노는 모습",
    "도시 및 건축 (City & Architecture)": "고층 빌딩, 야경, 번화한 도심 거리, 스카이라인, 네온사인 및 현대 건축물",
    "겨울 및 설경 (Winter & Snow)": "눈 덮인 산, 침엽수림, 겨울 숲, 하얀 설원, 겨울철 차분하고 시원한 계절 풍경",
    "바다 및 휴양지 (Ocean & Beach)": "에메랄드빛 바다, 백사장, 야자수, 파도, 여름철 해변과 평화로운 휴양지",
    "음식 및 카페 (Food & Beverage)": "맛있는 요리, 커피, 디저트, 식당, 베이커리 등 음식 문화",
    "인물 및 일상 (People & Daily Life)": "사람들의 표정, 일상적인 활동, 산책, 운동, 대화하는 인물 중심 장면"
}


class ImageSearchEngine:
    """
    텍스트 쿼리 기반 이미지 검색 및 이미지 분류 통합 엔진
    Vision API(설명 생성) + Embedding API(벡터화) + 코사인 유사도 분석 + 이미지 분류(Classification)
    """

    DEFAULT_CACHE_FILE = "image_metadata_cache.json"
    DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
    DEFAULT_VISION_MODEL = "gpt-4o"

    def __init__(
        self,
        image_dir: str = "search_images",
        cache_file: str = DEFAULT_CACHE_FILE,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        vision_model: str = DEFAULT_VISION_MODEL,
        api_key: Optional[str] = None
    ):
        self.image_dir = Path(image_dir)
        self.cache_file = Path(cache_file)
        self.embedding_model = embedding_model
        self.vision_model = vision_model

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client: Optional[OpenAI] = None
        self.is_offline_mode = False

        if OpenAI and self.api_key and not self.api_key.startswith("your_"):
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                print(f"[경고] OpenAI 클라이언트 초기화 실패 ({e}). 오프라인 시뮬레이션 모드로 전환합니다.")
                self.is_offline_mode = True
        else:
            self.is_offline_mode = True

        self.indexed_items: Dict[str, ImageItem] = {}

    def is_api_ready(self) -> bool:
        """실제 OpenAI API가 사용 가능한 상태인지 반환합니다."""
        return (not self.is_offline_mode) and (self.client is not None)

    # -------------------------------------------------------------
    # 1. Vision API: 이미지 텍스트 설명 생성
    # -------------------------------------------------------------
    def describe_image_with_vision(self, image_path: Union[str, Path], prompt: Optional[str] = None) -> str:
        """
        OpenAI Vision API를 사용하여 이미지의 시각적 요소를 분석하고 상세 텍스트 설명을 생성합니다.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

        if not self.is_api_ready():
            # 오프라인 모드 시뮬레이션 설명 생성
            return self._generate_fallback_description(image_path)

        system_instruction = (
            "당신은 전문 시각 자료 분석가입니다. 제공된 이미지의 주요 피사체, 배경, 색감, 분위기, "
            "행동 및 환경적 특징을 자연어 검색 및 이미지 분류에 적합하도록 명확하고 생생한 한국어로 2~3문장 설명해주세요."
        )

        user_prompt = prompt or (
            "이 이미지의 핵심 피사체와 배경 분위기를 설명해주세요. "
            "어떤 대상이 있고 어떤 상황이며 어떤 감성과 색감을 띠고 있는지 구체적으로 작성해주세요."
        )

        mime_type, _ = mimetypes.guess_type(str(image_path))
        if not mime_type:
            mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/bmp"

        with open(image_path, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode("utf-8")

        response = self.client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {"role": "system", "content": system_instruction},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()

    def _generate_fallback_description(self, image_path: Path) -> str:
        """API 미연결 시 파일명/경로 기반 휴리스틱 또는 프리셋 설명 생성"""
        fname_lower = image_path.name.lower()
        if "sunset" in fname_lower or "석양" in fname_lower:
            return "산 위로 붉고 따뜻하게 저무는 황금빛 노을과 웅장한 자연 속 석양 풍경입니다."
        elif "puppy" in fname_lower or "dog" in fname_lower or "강아지" in fname_lower:
            return "푸른 잔디밭이 펼쳐진 화창한 공원에서 신나게 뛰어노는 귀여운 강아지의 활기찬 모습입니다."
        elif "city" in fname_lower or "night" in fname_lower or "도시" in fname_lower:
            return "화려한 네온사인과 고층 빌딩들이 밤하늘을 수놓은 번화한 도심의 야경 스카이라인입니다."
        elif "winter" in fname_lower or "snow" in fname_lower or "겨울" in fname_lower:
            return "하얀 눈이 소복하게 쌓인 침엽수림과 고요하고 깨끗한 겨울 숲의 정취를 담은 설경입니다."
        elif "beach" in fname_lower or "ocean" in fname_lower or "바다" in fname_lower:
            return "투명한 에메랄드빛 바다와 야자수가 어우러진 여름철 시원하고 평화로운 휴양지 해변입니다."
        else:
            clean_name = image_path.stem.replace("_", " ").replace("-", " ")
            return f"시각적 요소와 배경이 담긴 '{clean_name}' 이미지입니다."

    # -------------------------------------------------------------
    # 2. Embedding API: 텍스트 벡터 변환
    # -------------------------------------------------------------
    def get_embedding(self, text: str) -> List[float]:
        """
        OpenAI Embedding API를 통해 텍스트를 벡터 임베딩으로 변환합니다.
        (API 사용 불가 시 SemanticFallbackEmbedder로 자동 대체)
        """
        clean_text = text.replace("\n", " ").strip()
        if not clean_text:
            clean_text = "빈 텍스트"

        if self.is_api_ready():
            try:
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=clean_text
                )
                return response.data[0].embedding
            except Exception as e:
                print(f"[경고] OpenAI 임베딩 생성 오류 ({e}). 내장 시맨틱 임베더로 대체합니다.")

        return SemanticFallbackEmbedder.get_embedding(clean_text)

    # -------------------------------------------------------------
    # 3. 인덱스 구축 및 캐싱 (Vision 설명 + 임베딩)
    # -------------------------------------------------------------
    def build_index(self, force_refresh: bool = False, verbose: bool = True) -> int:
        """
        지정된 이미지 디렉토리의 모든 이미지를 스캔하여
        Vision API 설명 생성 및 벡터 임베딩을 완료하고 캐시에 저장합니다.
        """
        if not self.image_dir.exists():
            self.image_dir.mkdir(parents=True, exist_ok=True)

        cached_data: Dict[str, Any] = {}
        if self.cache_file.exists() and not force_refresh:
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                if verbose:
                    print(f"[캐시 로드] 기존 메타데이터 캐시에서 {len(cached_data)}개 항목 로드 완료.")
            except Exception as e:
                if verbose:
                    print(f"[캐시 경고] 캐시 파일 읽기 실패 ({e}), 새로 생성합니다.")

        supported_exts = {".bmp", ".png", ".jpg", ".jpeg", ".webp"}
        image_files = sorted([
            f for f in self.image_dir.iterdir()
            if f.is_file() and f.suffix.lower() in supported_exts
        ])

        if not image_files:
            return 0

        if verbose:
            print(f"============================================================")
            mode_str = "OpenAI API 실시간 연동" if self.is_api_ready() else "내장 시맨틱 시뮬레이션 모드"
            print(f" 🚀 이미지 데이터셋 인덱싱 시작 (모드: {mode_str})")
            print(f"    - 대상 디렉토리: {self.image_dir} ({len(image_files)}개 이미지)")
            print(f"============================================================")

        try:
            from prepare_search_images import IMAGE_DATASET
            dataset_lookup = {item["filename"]: item for item in IMAGE_DATASET}
        except ImportError:
            dataset_lookup = {}

        updated_cache = {}
        self.indexed_items.clear()

        for idx, img_path in enumerate(image_files, 1):
            fname = img_path.name
            cache_key = fname
            item_cached = cached_data.get(cache_key)

            preset_info = dataset_lookup.get(fname, {})
            title = preset_info.get("title", img_path.stem.replace("_", " "))
            tags = preset_info.get("tags", [])

            description = ""
            embedding = []
            source = "cached"

            if item_cached and "description" in item_cached and "embedding" in item_cached:
                description = item_cached["description"]
                embedding = item_cached["embedding"]
                title = item_cached.get("title", title)
                tags = item_cached.get("tags", tags)
                source = "cached"
                if verbose:
                    print(f"  [{idx}/{len(image_files)}] 📦 [캐시 활용] {fname} - '{title}'")
            else:
                if self.is_api_ready():
                    if verbose:
                        print(f"  [{idx}/{len(image_files)}] 👁️ [Vision API 분석 중] {fname}...")
                    try:
                        description = self.describe_image_with_vision(img_path)
                        source = "vision_api"
                    except Exception as e:
                        if verbose:
                            print(f"    ⚠️ Vision API 호출 실패 ({e}). 기본 설명 적용")
                        description = preset_info.get("default_description", self._generate_fallback_description(img_path))
                        source = "preset_fallback"
                else:
                    if verbose:
                        print(f"  [{idx}/{len(image_files)}] 📝 [사전 설명 로드] {fname} - '{title}'")
                    description = preset_info.get("default_description", self._generate_fallback_description(img_path))
                    source = "preset"

                if verbose:
                    print(f"    ↳ 🔢 임베딩 벡터 생성 중...")
                embedding = self.get_embedding(description)

            item = ImageItem(
                image_id=f"img_{idx}",
                filename=fname,
                file_path=str(img_path),
                title=title,
                description=description,
                embedding=embedding,
                tags=tags,
                source=source
            )
            self.indexed_items[item.image_id] = item

            updated_cache[cache_key] = {
                "image_id": item.image_id,
                "filename": item.filename,
                "file_path": item.file_path,
                "title": item.title,
                "description": item.description,
                "embedding": item.embedding,
                "tags": item.tags,
                "source": item.source
            }

        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(updated_cache, f, ensure_ascii=False, indent=2)
            if verbose:
                print(f"\n💾 인덱스 및 임베딩 캐시가 '{self.cache_file}'에 안전하게 저장되었습니다.")
        except Exception as e:
            if verbose:
                print(f"[경고] 캐시 파일 저장 실패: {e}")

        if verbose:
            print(f"✨ 총 {len(self.indexed_items)}개 이미지 인덱싱 완료!\n")

        return len(self.indexed_items)

    # -------------------------------------------------------------
    # 4. 검색 수행: 쿼리 벡터 변환 & 코사인 유사도 랭킹
    # -------------------------------------------------------------
    def search(self, query: str, top_k: int = 3) -> List[SearchResult]:
        """
        사용자가 입력한 텍스트 쿼리를 기반으로 코사인 유사도를 계산하여
        가장 관련성이 높은 상위 K개의 이미지를 반환합니다.
        """
        if not self.indexed_items:
            self.build_index(verbose=False)

        if not query or not query.strip():
            return []

        query_embedding = self.get_embedding(query.strip())

        scores: List[Tuple[float, ImageItem]] = []
        for item in self.indexed_items.values():
            sim = CosineSimilarityCalculator.calculate(query_embedding, item.embedding)
            scores.append((sim, item))

        scores.sort(key=lambda x: x[0], reverse=True)

        results: List[SearchResult] = []
        for rank, (sim, item) in enumerate(scores[:top_k], start=1):
            percent = max(0.0, sim) * 100.0
            results.append(
                SearchResult(
                    rank=rank,
                    image_id=item.image_id,
                    filename=item.filename,
                    file_path=item.file_path,
                    title=item.title,
                    description=item.description,
                    similarity=sim,
                    score_percent=percent
                )
            )

        return results

    # -------------------------------------------------------------
    # 5. [신규 확장] 임의의 이미지 카테고리 분류 (Zero-Shot Classification)
    # -------------------------------------------------------------
    def classify_image(
        self,
        image_path: Union[str, Path],
        candidate_categories: Optional[Dict[str, str]] = None
    ) -> ClassificationResult:
        """
        사용자가 입력한 '임의의 이미지'를 Vision API 및 벡터 임베딩 유사도로 분류합니다.
        
        Args:
            image_path: 분류할 임의의 이미지 경로
            candidate_categories: 카테고리명 -> 상세 설명 매핑 (생략 시 기본 7개 카테고리 사용)
        
        Returns:
            ClassificationResult: 최적 카테고리, 유사도, 상세 분석 사유, 전체 순위
        """
        img_path = Path(image_path)
        if not img_path.exists():
            raise FileNotFoundError(f"분류할 이미지를 찾을 수 없습니다: {img_path}")

        categories = candidate_categories or DEFAULT_CLASSIFICATION_CATEGORIES

        # 1. 대상 이미지에 대한 Vision 텍스트 설명 생성
        description = self.describe_image_with_vision(img_path)

        # 2. 이미지 설명의 임베딩 벡터 생성
        img_embedding = self.get_embedding(description)

        # 3. 각 카테고리 후보들의 임베딩 벡터 생성 및 코사인 유사도 분석
        category_scores: List[Tuple[str, float, float]] = []
        for cat_name, cat_desc in categories.items():
            cat_query = f"{cat_name}. {cat_desc}"
            cat_embedding = self.get_embedding(cat_query)
            sim = CosineSimilarityCalculator.calculate(img_embedding, cat_embedding)
            pct = max(0.0, sim) * 100.0
            category_scores.append((cat_name, sim, pct))

        # 유사도 내림차순 정렬
        category_scores.sort(key=lambda x: x[1], reverse=True)
        top_cat, top_sim, top_pct = category_scores[0]

        # 4. 판단 사유 도출 (Vision API가 가능하면 모델의 시각적 추론 사유 획득)
        reasoning = ""
        if self.is_api_ready():
            try:
                cat_list_str = "\n".join([f"- {k}: {v}" for k, v in categories.items()])
                prompt = (
                    f"이 이미지는 다음 카테고리 후보군 중에서 '{top_cat}'(으)로 가장 높게 분류되었습니다.\n"
                    f"후보군:\n{cat_list_str}\n\n"
                    f"이미지 속 어떤 시각적 특징, 객체, 색감이나 분위기 때문에 이 카테고리로 분류되는 것이 타당한지 1~2문장으로 명확히 설명해주세요."
                )
                reasoning = self.describe_image_with_vision(img_path, prompt=prompt)
            except Exception:
                reasoning = f"이미지 설명 속 핵심 단어와 시각 요소가 '{top_cat}'의 개념과 가장 높은 코사인 유사도({top_sim:.4f})를 나타냅니다."
        else:
            reasoning = (
                f"이미지 분석 내용('{description[:40]}...')의 의미 벡터가 "
                f"'{top_cat}' 카테고리의 정의 벡터와 가장 높은 일치도({top_pct:.1f}%)를 보였습니다."
            )

        return ClassificationResult(
            predicted_category=top_cat,
            confidence_percent=top_pct,
            similarity_score=top_sim,
            image_description=description,
            reasoning=reasoning,
            all_category_scores=category_scores
        )

    # -------------------------------------------------------------
    # 6. [신규 확장] 이미지-to-이미지 유사도 검색 (Image Reverse Search)
    # -------------------------------------------------------------
    def search_by_image(self, query_image_path: Union[str, Path], top_k: int = 3) -> List[SearchResult]:
        """
        임의의 이미지를 쿼리로 입력받아, 기존 이미지 보관함에서 가장 시각적/의미적으로 유사한 이미지를 찾습니다.
        """
        query_path = Path(query_image_path)
        if not query_path.exists():
            raise FileNotFoundError(f"쿼리 이미지를 찾을 수 없습니다: {query_path}")

        # 1. 쿼리 이미지 설명 생성
        query_desc = self.describe_image_with_vision(query_path)

        # 2. 텍스트 검색 엔진을 활용해 유사한 이미지 탐색
        return self.search(query=query_desc, top_k=top_k)

    # -------------------------------------------------------------
    # 7. [신규 확장] 임의의 새 이미지 동적 추가 및 실시간 인덱싱
    # -------------------------------------------------------------
    def add_custom_image(
        self,
        source_image_path: Union[str, Path],
        title: Optional[str] = None,
        copy_to_library: bool = True
    ) -> ImageItem:
        """
        사용자가 제공한 임의의 새로운 이미지 파일을 보관함에 추가하고,
        Vision 설명 생성 및 임베딩을 즉시 수행하여 검색 가능하도록 등록합니다.
        """
        src = Path(source_image_path)
        if not src.exists():
            raise FileNotFoundError(f"추가할 이미지 파일이 없습니다: {src}")

        if copy_to_library:
            dest = self.image_dir / src.name
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
            target_path = dest
        else:
            target_path = src

        item_title = title or target_path.stem.replace("_", " ")

        # 설명 및 임베딩 생성
        description = self.describe_image_with_vision(target_path)
        embedding = self.get_embedding(description)

        new_idx = len(self.indexed_items) + 1
        item = ImageItem(
            image_id=f"img_{new_idx}",
            filename=target_path.name,
            file_path=str(target_path),
            title=item_title,
            description=description,
            embedding=embedding,
            tags=["사용자 추가"],
            source="user_added"
        )

        self.indexed_items[item.image_id] = item

        # 캐시 업데이트
        cached_data = {}
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
            except Exception:
                pass

        cached_data[item.filename] = {
            "image_id": item.image_id,
            "filename": item.filename,
            "file_path": item.file_path,
            "title": item.title,
            "description": item.description,
            "embedding": item.embedding,
            "tags": item.tags,
            "source": item.source
        }

        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(cached_data, f, ensure_ascii=False, indent=2)

        return item

    def get_indexed_items_list(self) -> List[ImageItem]:
        """현재 인덱싱된 모든 이미지 목록을 반환합니다."""
        return list(self.indexed_items.values())
