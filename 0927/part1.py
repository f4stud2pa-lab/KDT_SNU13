"""Part 1 - 초개인화 금융상품 추천 챗봇.

실행 전 macOS/Linux 터미널에서 OPENAI_API_KEY를 설정하세요.

    export OPENAI_API_KEY="sk-..."
    ./.venv/bin/python 0927/part1.py

이 프로그램은 실습 문제의 모범 매칭을 프롬프트에 참고자료로 제공하되,
최종 추천 설명은 고객 프로파일과 상품 특성을 근거로 LLM이 작성하게 합니다.
"""

from __future__ import annotations

import os
from typing import Final

from openai import OpenAI


MODEL: Final = "gpt-4o"

CUSTOMERS: Final[dict[str, dict[str, str]]] = {
    "C01": {
        "name": "김은희",
        "profile": "52세 여성, 중소기업 경리, 은퇴 3년 전, 자산 1억 원, 위험 성향 낮음, 안정적 은퇴 대비, 부모 부양, 자녀 없음",
    },
    "C02": {
        "name": "박준영",
        "profile": "28세 남성, 스타트업 마케터, 월 400만 원 소득, 투자 경험 많음, 위험 성향 높음, 자산 10억 장기 목표, 미혼 1인 가구",
    },
    "C03": {
        "name": "이소영",
        "profile": "35세 여성, 계약직 교사, 소득 불안정, 지출 많음, 위험 성향 매우 낮음, 아이 교육비 확보, 2자녀, 싱글맘",
    },
    "C04": {
        "name": "전성훈",
        "profile": "45세 남성, 대기업 과장, 자산 3억 원, 대출 없음, 위험 성향 중간, 조기 은퇴와 자산 보호, 배우자와 고등학생 자녀",
    },
    "C05": {
        "name": "윤정아",
        "profile": "31세 여성, 프리랜서 디자이너, 수입 변동성 큼, 위험 성향 중간~높음, 해외 이주 준비, 반려동물 2마리, 1인 가구",
    },
    "C06": {
        "name": "오지훈",
        "profile": "63세 남성, 은퇴 후 생활, 연금 외 수입 없음, 위험 성향 매우 낮음, 노후 의료비 대비, 배우자와 단둘이 거주",
    },
    "C07": {
        "name": "장민호",
        "profile": "40세 남성, 자영업자, 소득 700만 원, 지출 과다, 위험 성향 높음, 자산 증식과 절세, 배우자와 초등학생 2명",
    },
    "C08": {
        "name": "최수연",
        "profile": "48세 여성, 공무원, 자산 2억 원 이상과 적금, 위험 성향 중간, 5년 뒤 귀촌 준비, 배우자 있음, 자녀 독립",
    },
    "C09": {
        "name": "임다혜",
        "profile": "25세 여성, 대학원생, 생활비 부족과 아르바이트, 위험 성향 매우 낮음, 유학 준비 자금 마련, 기숙사 생활",
    },
    "C10": {
        "name": "남기태",
        "profile": "55세 남성, 고위직 은퇴 예정, 자산 5억 원 이상, 위험 성향 중간, 상속 계획과 안정 운용, 배우자와 성인 자녀",
    },
}

PRODUCTS: Final[dict[str, dict[str, str]]] = {
    "P001": {"name": "스마트 안심채권", "type": "채권형", "risk": "낮음", "details": "정부 보증, 중도 해지 가능"},
    "E104": {"name": "글로벌 혁신 ETF", "type": "ETF", "risk": "높음", "details": "나스닥 기반 혁신기업 집중"},
    "R033": {"name": "골든라이프 연금펀드", "type": "연금형 펀드", "risk": "중간", "details": "세액공제 가능, 혼합형 운용"},
    "F078": {"name": "AI 테크 테마펀드", "type": "주식형 펀드", "risk": "높음", "details": "AI 성장주 집중"},
    "R102": {"name": "K-주거 안정펀드", "type": "부동산 REITs", "risk": "중간", "details": "부동산 배당형 투자"},
    "S019": {"name": "마이키즈 교육적금", "type": "적금형 상품", "risk": "매우 낮음", "details": "확정금리, 월불입형"},
    "M055": {"name": "비전플랜 혼합펀드", "type": "혼합형 펀드", "risk": "중간", "details": "채권+주식 혼합형"},
    "D087": {"name": "디지털 그로스 인덱스", "type": "인덱스 펀드", "risk": "중간~높음", "details": "글로벌 지수 추종, 기술주 중심"},
    "B022": {"name": "세이프 웰보장 예금", "type": "정기예금", "risk": "낮음", "details": "원금 보장, 단기 예치 가능"},
    "T065": {"name": "G-그린 에너지 펀드", "type": "테마형 펀드", "risk": "중간~높음", "details": "친환경 에너지 기업 중심"},
}

# 실습 문서의 고객별 금융상품 정답안.
ANSWER_KEY: Final[dict[str, tuple[str, ...]]] = {
    "C01": ("R033", "P001"),
    "C02": ("F078", "E104"),
    "C03": ("S019", "B022"),
    "C04": ("M055", "R033"),
    "C05": ("D087", "R102"),
    "C06": ("P001", "B022"),
    "C07": ("M055", "T065"),
    "C08": ("R102", "R033"),
    "C09": ("B022", "S019"),
    "C10": ("P001", "R102"),
}


def format_catalog() -> str:
    """LLM이 상품명을 혼동하지 않도록 상품 코드를 포함한 목록을 만든다."""
    return "\n".join(
        f"- {code}: {item['name']} | 유형={item['type']} | 위험={item['risk']} | 특징={item['details']}"
        for code, item in PRODUCTS.items()
    )


def format_answer_key() -> str:
    """추천 정확도 평가용 모범 매칭을 프롬프트에 명시한다."""
    return "\n".join(
        f"- {customer_id}: {', '.join(PRODUCTS[code]['name'] for code in product_codes)}"
        for customer_id, product_codes in ANSWER_KEY.items()
    )


def build_system_prompt() -> str:
    return f"""당신은 한국어로 답변하는 초개인화 금융상품 추천 상담사입니다.
아래 상품 목록만 사용해 고객에게 맞는 상품을 추천하세요.

[상품 목록]
{format_catalog()}

[추천 정확도 참고자료]
다음은 실습 문서의 고객별 모범 매칭입니다. 고객 ID가 목록에 있는 경우
반드시 해당 상품을 우선 추천하고, 상품명과 코드를 정확히 유지하세요.
{format_answer_key()}

[작성 절차]
1. 고객 프로파일에서 재무 목표, 소득·지출 상황, 가족 책임, 시간 horizon,
   위험 감수 수준, pain point와 wants/needs를 먼저 내부적으로 추론합니다.
2. 모범 매칭 상품을 1순위와 2순위로 제시하고, 각 상품이 고객의 구체적인
   상황에 어떻게 연결되는지 설명합니다.
3. 고객의 이름과 상황을 자연스럽게 언급해 '나를 이해하고 배려한다'는 느낌을
   주되, 확인되지 않은 사실은 만들어내지 않습니다.
4. 예상 수익률을 보장하지 말고, 위험·중도해지·원금손실 가능성을 상품 목록의
   위험 수준에 맞춰 쉬운 말로 설명합니다.
5. 금융상품 가입을 강요하지 말고, 마지막에 고객이 확인할 질문 2개와
   다음 상담에서 확인할 정보 1개를 제시합니다.

[출력 형식]
## 고객님을 위한 맞춤 추천
### 1. 고객 상황 요약
- ...
### 2. 추천 상품
1. 상품명 (상품 코드)
   - 추천 이유:
   - 주의할 점:
2. 상품명 (상품 코드)
   - 추천 이유:
   - 주의할 점:
### 3. 한눈에 보는 실행 순서
- ...
### 4. 가입 전 확인 질문
- ...

이는 교육용 추천 실습이며, 실제 가입 전에는 최신 상품설명서와 전문가 상담을
확인해야 한다는 문구를 마지막에 포함하세요."""


def choose_customer() -> tuple[str | None, str]:
    """고객 ID를 선택하거나 직접 프로파일을 입력받는다."""
    print("\n고객 ID를 선택하세요 (C01~C10). 직접 입력하려면 custom을 입력하세요.")
    customer_id = input("선택: ").strip().upper()
    if customer_id == "CUSTOM":
        profile = input("고객 프로파일을 입력하세요: ").strip()
        if not profile:
            raise ValueError("고객 프로파일이 비어 있습니다.")
        return None, profile
    if customer_id not in CUSTOMERS:
        raise ValueError("C01~C10 또는 custom만 입력할 수 있습니다.")
    return customer_id, CUSTOMERS[customer_id]["profile"]


def build_user_prompt(customer_id: str | None, profile: str) -> str:
    if customer_id:
        reference = (
            f"고객 ID: {customer_id}\n"
            f"고객 이름: {CUSTOMERS[customer_id]['name']}\n"
        )
    else:
        reference = "고객 ID: 신규 고객\n"
    return f"""{reference}고객 프로파일:
{profile}

위 고객에게 초개인화된 금융상품 추천 리포트를 작성하세요."""


def recommend(client: OpenAI, customer_id: str | None, profile: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(customer_id, profile)},
        ],
    )
    answer = response.choices[0].message.content
    if not answer:
        raise RuntimeError("OpenAI가 빈 응답을 반환했습니다.")
    return answer


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY가 설정되지 않았습니다. "
            '예: export OPENAI_API_KEY="sk-..."'
        )

    try:
        customer_id, profile = choose_customer()
        answer = recommend(OpenAI(), customer_id, profile)
    except (ValueError, RuntimeError) as error:
        print(f"\n오류: {error}")
        return

    print("\n" + answer)


if __name__ == "__main__":
    main()
