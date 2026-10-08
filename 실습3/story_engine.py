"""
그림과 감정 기반 이야기 생성 엔진 (Story Engine)
OpenAI Vision API(gpt-4o)를 활용하여 여러 장의 이미지를 분석하고,
사용자가 선택한 감정(sentiment)과 톤에 맞는 일관된 이야기를 생성합니다.
"""

import base64
import json
import mimetypes
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

# OpenAI 라이브러리 로드 (미설치 환경에서도 Mock 모드 동작 가능하도록 예외 처리)
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# .env 파일 로드 지원
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ---------------------------------------------------------
# 감정별 스토리 템플릿 및 어조(Tone) 가이드 정의
# ---------------------------------------------------------
SENTIMENT_PROFILES: Dict[str, Dict[str, str]] = {
    "행복": {
        "english": "Happy / Joyful",
        "tone": "따뜻하고 희망찬 어조, 밝고 경쾌한 문체, 긍정적인 에너지",
        "story_guide": (
            "일상의 소소한 기쁨과 따스한 온기를 조명합니다. "
            "그림 속 인물(또는 동물)의 미소와 활기찬 움직임, 평화로운 자연과 햇살을 생생하게 묘사하세요. "
            "갈등보다는 서로 간의 유대감, 작은 성취, 즐거움을 강조하며 읽는 이에게 미소를 주는 행복한 결말로 맺어주세요."
        ),
        "example_expressions": ["화창한 햇살", "설레는 발걸음", "환한 미소", "따스한 온기", "행복한 웃음소리"]
    },
    "슬픔": {
        "english": "Sad / Melancholic",
        "tone": "서정적이고 아련한 어조, 잔잔하고 묵직한 문체, 여운이 깊은 문장",
        "story_guide": (
            "지나간 시간에 대한 그리움, 고독함, 아련한 이별이나 쓸쓸한 정취를 담아냅니다. "
            "인물의 깊은 눈빛과 침묵, 그림자, 스쳐 지나가는 바람과 계절감을 섬세하게 포착하세요. "
            "슬픔 속에서도 가슴 깊은 곳에 남는 애틋함과 진한 여운을 표현하세요."
        ),
        "example_expressions": ["아련한 기억", "쓸쓸한 바람", "차오르는 그리움", "긴 침묵", "눈시울이 붉어지는"]
    },
    "긴장감": {
        "english": "Tense / Suspenseful",
        "tone": "긴박하고 서늘한 어조, 호흡이 짧고 속도감 있는 문체, 몰입감 넘치는 묘사",
        "story_guide": (
            "한 치 앞을 알 수 없는 미스터리와 위기감, 심장 박동을 자극하는 서스펜스를 구축합니다. "
            "그림 속 사소한 단서, 인물의 긴장된 표정과 주저하는 손짓, 불길하거나 의문스러운 배경을 강조하세요. "
            "단문 위주의 빠른 전개로 독자가 손에 땀을 쥐게 만드는 극적 긴장감을 연출하세요."
        ),
        "example_expressions": ["숨막히는 정적", "등 뒤의 서늘한 기운", "의문의 그림자", "찰나의 순간", "심장이 쿵쾅거렸다"]
    },
    "설렘": {
        "english": "Fluttering / Romantic",
        "tone": "두근거리고 풋풋한 어조, 부드럽고 감미로운 문체, 낭만적인 묘사",
        "story_guide": (
            "새로운 만남, 수줍은 마음, 첫사랑처럼 가슴 뛰는 순간의 기분 좋은 기대를 묘사합니다. "
            "스치는 시선, 붉어진 뺨, 스쳐가는 봄바람처럼 사소하지만 특별한 순간의 감정선을 살려주세요. "
            "몽글몽글하고 낭만적인 분위기로 마음을 따뜻하게 물들이세요."
        ),
        "example_expressions": ["두근거리는 마음", "수줍은 눈빛", "살랑이는 바람", "기분 좋은 예감", "분홍빛 설렘"]
    },
    "코믹": {
        "english": "Humorous / Comic",
        "tone": "유쾌하고 재치 넘치는 어조, 익살맞고 발랄한 문체, 반전이 있는 서술",
        "story_guide": (
            "인물의 엉뚱한 행동, 예상치 못한 상황, 웃지 못할 해프닝과 유쾌한 반전을 조명합니다. "
            "유머러스한 비유와 생동감 넘치는 의성어/의태어를 적절히 활용하여 독자에게 유쾌한 웃음을 선사하세요. "
            "너무 진지하지 않게, 밝고 익살스럽게 장면을 엮어가세요."
        ),
        "example_expressions": ["엉뚱한 반전", "우당탕탕", "기절초풍할 사건", "능청스러운 표정", "웃음보가 터졌다"]
    },
    "감동": {
        "english": "Touching / Heartwarming",
        "tone": "진솔하고 가슴 뭉클한 어조, 깊은 온기와 진정성이 담긴 문체",
        "story_guide": (
            "서로를 위하는 깊은 마음, 헌신, 위로, 그리고 고난 끝에 마주한 진정한 사랑이나 우정을 담아냅니다. "
            "인물 간의 따스한 눈빛과 말 없는 손길, 서로가 서로에게 주는 위안을 깊이 있게 서술하여 가슴 벅찬 감동을 전달하세요."
        ),
        "example_expressions": ["가슴 벅찬 온기", "말 없는 위로", "서로의 손을 꼭 쥐며", "눈물이 핑 도는", "마음 깊은 연결"]
    },
    "공포": {
        "english": "Eerie / Horror",
        "tone": "음산하고 기괴한 어조, 서서히 옥죄어오는 섬뜩한 문체",
        "story_guide": (
            "낯선 적막, 어둠 속에 숨겨진 무언가, 피할 수 없는 공포감을 조성합니다. "
            "차가운 공기, 기괴하게 일그러진 그림자, 들려서는 안 될 소리 등을 통해 독자의 등골을 서늘하게 만드세요."
        ),
        "example_expressions": ["차가운 적막", "기괴한 형체", "알 수 없는 속삭임", "피가 얼어붙는", "뒤를 돌아보지 마라"]
    }
}


@dataclass
class ImageAnalysis:
    """개별 그림 분석 결과"""
    index: int
    summary: str               # 그림 요약
    characters: str            # 등장인물 또는 동물/주체
    background: str            # 배경 및 장소, 분위기
    action_or_event: str       # 주요 행동 또는 일어난 사건
    key_details: List[str] = field(default_factory=list)  # 주목할 만한 시각적 디테일


@dataclass
class StoryResult:
    """전체 이야기 생성 결과"""
    sentiment: str                         # 선택된 감정
    sentiment_profile: Dict[str, str]      # 적용된 톤 프로필
    image_analyses: List[ImageAnalysis]    # 각 그림별 분석 리포트
    title: str                             # 이야기 제목
    story: str                             # 완성된 본문 이야기
    moral_or_thought: Optional[str] = None # 감정적 여운 또는 한 줄 생각


class StoryEngine:
    """OpenAI Vision API 기반 그림 & 감정 연계 이야기 생성기"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o", mock_mode: bool = False):
        self.mock_mode = mock_mode
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.mock_mode and self.api_key and OpenAI is None:
            raise ImportError("openai 패키지가 설치되어 있지 않습니다. 'pip install openai'를 실행해 주세요.")

        if self.api_key and OpenAI is not None:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
        self.model = model

    @staticmethod
    def get_supported_sentiments() -> List[str]:
        """지원하는 감정 목록 반환"""
        return list(SENTIMENT_PROFILES.keys())

    @staticmethod
    def encode_image_to_base64(image_input: Union[str, Path, bytes], mime_type: Optional[str] = None) -> tuple[str, str]:
        """
        파일 경로 또는 바이너리 데이터를 Base64 인코딩 문자열과 MIME 타입으로 변환합니다.
        """
        if isinstance(image_input, (str, Path)):
            path = Path(image_input)
            if not path.exists():
                raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {path}")

            if mime_type is None:
                mime_type, _ = mimetypes.guess_type(str(path))
                if mime_type is None:
                    mime_type = "image/jpeg"

            with open(path, "rb") as f:
                data = f.read()
        elif isinstance(image_input, bytes):
            data = image_input
            if mime_type is None:
                mime_type = "image/jpeg"
        else:
            raise ValueError("image_input은 파일 경로(str, Path) 또는 bytes여야 합니다.")

        b64_str = base64.b64encode(data).decode("utf-8")
        return b64_str, mime_type

    def _resolve_sentiment_profile(self, sentiment: str) -> Dict[str, str]:
        """선택된 감정에 대응하는 프로필을 찾거나 커스텀 프로필을 생성합니다."""
        for key, profile in SENTIMENT_PROFILES.items():
            if key in sentiment or sentiment in key:
                return profile

        # 사전 정의되지 않은 커스텀 감정인 경우 동적 프로필 생성
        return {
            "english": f"Custom Sentiment ({sentiment})",
            "tone": f"'{sentiment}'의 감정과 느낌이 생생히 묻어나는 어조와 분위기",
            "story_guide": (
                f"전체 이야기의 흐름과 인물의 내면, 배경 묘사에 사용자가 지정한 '{sentiment}'의 감정을 "
                f"일관되게 반영하세요. 각 장면의 연결 고리마다 '{sentiment}'의 분위기를 극대화하세요."
            ),
            "example_expressions": [f"'{sentiment}' 느낌의 표현", "감정에 어울리는 수식어"]
        }

    def _generate_mock_result(self, num_images: int, sentiment: str, profile: Dict[str, str]) -> StoryResult:
        """API 키가 없거나 테스트 모드일 때 반환하는 정밀 Mock 결과"""
        # 기본 4컷 강아지 예시 기반 목업
        sample_analyses = [
            ImageAnalysis(
                index=1,
                summary="맑은 날 푸른 공원을 산책하는 활기찬 강아지의 모습",
                characters="노란 털의 골든 리트리버 강아지와 주인",
                background="푸른 잔디밭과 맑은 하늘의 야외 공원 산책로",
                action_or_event="주인의 발걸음에 맞춰 신나게 앞장서 걷고 있음",
                key_details=["기분 좋게 올라간 꼬리", "햇살에 반짝이는 풀잎"]
            ),
            ImageAnalysis(
                index=2,
                summary="시원한 나무 그늘 아래에 엎드려 휴식을 취하는 모습",
                characters="평온한 표정의 강아지",
                background="큰 느티나무 아래 시원한 그늘",
                action_or_event="산책 중 잠시 숨을 고르며 여유롭게 쉬는 중",
                key_details=["살랑이는 나뭇잎 그림자", "혀를 살짝 내민 채 미소 짓는 표정"]
            ),
            ImageAnalysis(
                index=3,
                summary="풀숲에서 빨간 공을 발견하고 입에 물고 달려오는 모습",
                characters="눈을 반짝이며 달리는 강아지",
                background="넓게 트인 잔디 광장",
                action_or_event="던져진 빨간 공을 낚아채 주인에게 되돌아오는 순간",
                key_details=["입에 꽉 문 빨간 공", "역동적으로 흩날리는 귀와 털"]
            ),
            ImageAnalysis(
                index=4,
                summary="노을빛을 받으며 주인과 나란히 집으로 돌아가는 다정한 모습",
                characters="주인과 강아지",
                background="주황빛 저녁노을이 물든 동네 어귀 길목",
                action_or_event="하루를 마무리하며 정답게 나란히 귀가함",
                key_details=["길게 드리운 두 그림자", "만족스럽게 맞닿은 발걸음"]
            )
        ]

        analyses = sample_analyses[:num_images] if num_images <= 4 else sample_analyses + [
            ImageAnalysis(
                index=i + 1,
                summary=f"그림 {i + 1}의 장면",
                characters="주인공",
                background="이어지는 배경",
                action_or_event=f"{sentiment} 분위기 속에서 이어지는 행동",
                key_details=["감성적 디테일"]
            )
            for i in range(4, num_images)
        ]

        if "행복" in sentiment:
            title = "눈부신 햇살 아래, 너와 나의 소중한 하루"
            story = (
                "맑고 화창한 날, 강아지는 공원에서 주인과 함께 발걸음을 맞추며 기분 좋은 산책을 시작했다. "
                "기분 좋게 걷다 보니 시원한 바람이 불어오는 큰 나무 그늘 아래에 멈춰 섰고, 둘은 풀잎 냄새를 맡으며 한참 동안 여유를 즐겼다. "
                "그러다 잔디밭 너머로 굴러간 빨간 공을 발견한 강아지는 바람처럼 신나게 달려가 공을 물어왔다. "
                "칭찬을 바라는 눈빛으로 공을 건넨 강아지는 만족스럽게 꼬리를 흔들었고, 뉘엿뉘엿 지는 노을빛을 받으며 함께 집으로 돌아갔다. "
                "함께 걷는 발걸음마다, 둘 모두의 얼굴에 따스하고 행복한 웃음이 가득 피어올랐다."
            )
            moral = "가장 소박한 일상도 사랑하는 존재와 함께할 때 가장 완전한 행복이 됩니다."
        elif "슬픔" in sentiment:
            title = "바람에 실려간 기억의 조각들"
            story = (
                "어느 쓸쓸한 오후, 텅 빈 공원길을 걷는 발걸음 위로 서늘한 바람이 스쳐 지나갔다. "
                "늘 함께 머물던 나무 그늘 아래 가만히 멈춰 서자, 지난날의 아련한 추억들이 귓가를 맴돌아 발걸음을 무겁게 만들었다. "
                "낡고 빛바랜 공 하나를 조심스레 어루만지는 순간, 다시는 돌아갈 수 없는 그 시절의 따스했던 숨결이 스쳐 지나갔다. "
                "붉게 물드는 노을을 뒤로하고 홀로 돌아오는 길, 길게 늘어선 그림자만이 차오르는 그리움을 말없이 위로해 줄 뿐이었다."
            )
            moral = "시간은 흘러도 마음 깊이 새겨진 그리움의 온기는 쉬이 식지 않습니다."
        elif "긴장감" in sentiment:
            title = "그림자 속의 숨바꼭질"
            story = (
                "적막이 감도는 공원 한가운데, 사소한 바스락거림에도 온 신경이 곤두섰다. "
                "나무 그늘 깊숙한 곳에서 무언가 지켜보는 듯한 서늘한 시선이 느껴져 숨을 죽인 채 자리를 지켰다. "
                "바로 그 찰나, 풀숲 깊은 곳에서 정체불명의 물체가 튀어나왔고, 심장은 쿵쾅거리며 터질 듯 뛰기 시작했다. "
                "어둠이 짙게 깔리기 전, 더 이상의 위험을 피하기 위해 빠르게 뒤를 돌아보며 발걸음을 재촉해 현장을 벗어났다."
            )
            moral = "예측할 수 없는 찰나의 순간, 보이지 않는 긴장이 모든 감각을 깨웁니다."
        else:
            title = f"{sentiment}의 정취가 깃든 하루"
            story = (
                f"오늘 하루는 온통 '{sentiment}'의 분위기로 가득 차 있었다. "
                "공원의 산책로를 걸으며 시작된 순간들은 나무 아래에서의 차분한 쉼으로 이어졌고, "
                f"작은 공 하나를 마주한 순간에는 '{sentiment}'의 감정이 한층 더 짙게 피어올랐다. "
                f"집으로 돌아가는 길목, 스쳐 지나간 모든 장면들이 모여 하나의 잊지 못할 {sentiment}의 이야기로 완성되었다."
            )
            moral = f"마음의 렌즈를 통해 바라본 일상은 언제나 특별한 이야기로 피어납니다."

        return StoryResult(
            sentiment=sentiment,
            sentiment_profile=profile,
            image_analyses=analyses,
            title=title,
            story=story,
            moral_or_thought=moral
        )

    def generate_story(
        self,
        images: List[Union[str, Path, bytes]],
        sentiment: str,
        image_mime_types: Optional[List[str]] = None,
        language: str = "한국어"
    ) -> StoryResult:
        """
        여러 장의 그림과 감정을 입력받아,
        1. 각 그림에 대한 심층 분석(인물, 배경, 상황)을 수행하고
        2. 그림 순서에 맞춰 지정한 감정과 어조를 반영한 짧은 이야기를 생성합니다.
        """
        if not images:
            raise ValueError("최소 1장 이상의 이미지가 필요합니다.")

        profile = self._resolve_sentiment_profile(sentiment)

        # Mock 모드 또는 OpenAI 클라이언트가 초기화되지 않은 경우 목업 결과 반환
        if self.mock_mode or not self.client:
            return self._generate_mock_result(len(images), sentiment, profile)

        # 이미지들을 Base64 URL 포맷으로 인코딩
        encoded_images = []
        for i, img in enumerate(images):
            mime = image_mime_types[i] if (image_mime_types and i < len(image_mime_types)) else None
            b64_str, detected_mime = self.encode_image_to_base64(img, mime)
            encoded_images.append(f"data:{detected_mime};base64,{b64_str}")

        num_images = len(encoded_images)

        # 시스템 프롬프트: 전문 스토리텔러 & 이미지 분석가 역할 부여
        system_prompt = (
            "당신은 그림의 시각적 요소를 정밀하게 읽어내어 깊이 있는 감성 서사로 엮어내는 전문 스토리텔러이자 비주얼 분석가입니다.\n"
            "사용자가 순서대로 제공한 여러 장의 그림과 목표 감정(Sentiment)을 바탕으로, "
            "각 그림의 내용을 꼼꼼히 분석하고 이를 매끄럽게 연결하는 고품질의 짧은 이야기를 창작해야 합니다."
        )

        # 유저 메시지 구성 (다중 이미지 Vision 메시지)
        content_items: List[Dict] = []
        content_items.append({
            "type": "text",
            "text": (
                f"아래에 총 {num_images}장의 그림이 순서대로 제공됩니다.\n"
                f"이야기의 핵심 감정은 **[{sentiment}]**입니다.\n\n"
                f"### 지침 (Guidelines):\n"
                f"1. **각 그림에 대한 정밀 분석**: 각 그림의 등장인물/동물(주체), 배경 및 장소, 행동 및 상황, 독특한 시각적 디테일을 분석하세요.\n"
                f"2. **그림 순서에 따른 자연스러운 스토리 전개**: 그림 1부터 그림 {num_images}까지의 인과관계와 시간의 흐름을 자연스럽게 연결하세요. "
                f"그림에 나타난 시각적 요소(동일 인물/동물의 연속된 행동 등)를 충실히 반영해야 합니다.\n"
                f"3. **감정 및 어조(Tone) 완벽 반영**:\n"
                f"   - 어조: {profile['tone']}\n"
                f"   - 서사 지침: {profile['story_guide']}\n"
                f"4. **이야기 분량 및 형식**: 완결성 있는 매끄러운 단락들로 구성된 짧은 이야기(약 300~600자)로 작성하세요.\n\n"
                f"반드시 아래 JSON 스키마 형식으로 응답하세요:\n"
                "{\n"
                '  "image_analyses": [\n'
                '    {\n'
                '      "index": 1,\n'
                '      "summary": "그림의 핵심 내용 1줄 요약",\n'
                '      "characters": "등장인물, 동물 또는 중심 객체",\n'
                '      "background": "배경, 시간대, 장소 묘사",\n'
                '      "action_or_event": "일어나고 있는 동작 또는 사건",\n'
                '      "key_details": ["디테일1", "디테일2"]\n'
                '    }\n'
                '  ],\n'
                '  "title": "이야기 제목",\n'
                '  "story": "감정과 그림 분석이 자연스럽게 녹아든 완성된 이야기 전문",\n'
                '  "moral_or_thought": "이야기가 남기는 감정적 여운 또는 한 줄 생각"\n'
                "}"
            )
        })

        for idx, img_url in enumerate(encoded_images, start=1):
            content_items.append({
                "type": "text",
                "text": f"--- [그림 {idx}] ---"
            })
            content_items.append({
                "type": "image_url",
                "image_url": {
                    "url": img_url,
                    "detail": "high"
                }
            })

        # OpenAI API 호출 (Structured JSON Response)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_items}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )

        raw_content = response.choices[0].message.content
        if not raw_content:
            raise RuntimeError("OpenAI API로부터 빈 응답을 받았습니다.")

        data = json.loads(raw_content)

        # ImageAnalysis 객체 리스트 파싱
        analyses = []
        for item in data.get("image_analyses", []):
            analyses.append(
                ImageAnalysis(
                    index=item.get("index", len(analyses) + 1),
                    summary=item.get("summary", ""),
                    characters=item.get("characters", ""),
                    background=item.get("background", ""),
                    action_or_event=item.get("action_or_event", ""),
                    key_details=item.get("key_details", [])
                )
            )

        return StoryResult(
            sentiment=sentiment,
            sentiment_profile=profile,
            image_analyses=analyses,
            title=data.get("title", f"{sentiment}의 이야기"),
            story=data.get("story", "").strip(),
            moral_or_thought=data.get("moral_or_thought")
        )
