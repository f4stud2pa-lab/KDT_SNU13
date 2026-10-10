# -*- coding: utf-8 -*-
"""
AI응용 실습 문제 1: 초개인화 금융상품 추천 (개인)
데이터 정의 모듈
"""

# 1. 고객 프로파일 샘플 (10명)
CUSTOMER_PROFILES = [
    {
        "id": "C01",
        "name": "김은희",
        "age": 52,
        "gender": "여",
        "job": "중소기업 경리",
        "financial_status": "은퇴 3년 전, 자산 1억",
        "risk_tolerance": "낮음",
        "primary_goal": "안정적 은퇴 대비",
        "family_lifestyle": "부모 부양, 자녀 없음"
    },
    {
        "id": "C02",
        "name": "박준영",
        "age": 28,
        "gender": "남",
        "job": "스타트업 마케터",
        "financial_status": "월 400만 소득, 투자 경험 多",
        "risk_tolerance": "높음",
        "primary_goal": "자산 10억 장기 목표",
        "family_lifestyle": "미혼, 1인 가구"
    },
    {
        "id": "C03",
        "name": "이소영",
        "age": 35,
        "gender": "여",
        "job": "계약직 교사",
        "financial_status": "소득 불안정, 지출 많음",
        "risk_tolerance": "매우 낮음",
        "primary_goal": "아이 교육비 확보",
        "family_lifestyle": "2자녀, 싱글맘"
    },
    {
        "id": "C04",
        "name": "전성훈",
        "age": 45,
        "gender": "남",
        "job": "대기업 과장",
        "financial_status": "자산 3억, 대출 없음",
        "risk_tolerance": "중간",
        "primary_goal": "조기 은퇴와 자산 보호",
        "family_lifestyle": "배우자+고등학생 자녀"
    },
    {
        "id": "C05",
        "name": "윤정아",
        "age": 31,
        "gender": "여",
        "job": "프리랜서 디자이너",
        "financial_status": "수입 변동성 큼",
        "risk_tolerance": "중간~높음",
        "primary_goal": "해외 이주 준비",
        "family_lifestyle": "반려동물 2마리, 1인 가구"
    },
    {
        "id": "C06",
        "name": "오지훈",
        "age": 63,
        "gender": "남",
        "job": "은퇴 후 생활",
        "financial_status": "연금 외 수입 無",
        "risk_tolerance": "매우 낮음",
        "primary_goal": "노후 의료비 대비",
        "family_lifestyle": "배우자와 단둘이 거주"
    },
    {
        "id": "C07",
        "name": "장민호",
        "age": 40,
        "gender": "남",
        "job": "자영업자",
        "financial_status": "소득 700만, 지출 과다",
        "risk_tolerance": "높음",
        "primary_goal": "자산 증식 + 절세",
        "family_lifestyle": "배우자+초등학생 2명"
    },
    {
        "id": "C08",
        "name": "최수연",
        "age": 48,
        "gender": "여",
        "job": "공무원",
        "financial_status": "자산 2억+적금",
        "risk_tolerance": "중간",
        "primary_goal": "5년 후 귀촌 준비",
        "family_lifestyle": "배우자 있음, 자녀 독립"
    },
    {
        "id": "C09",
        "name": "임다혜",
        "age": 25,
        "gender": "여",
        "job": "대학원생",
        "financial_status": "생활비 부족, 아르바이트",
        "risk_tolerance": "매우 낮음",
        "primary_goal": "유학 준비 자금 마련",
        "family_lifestyle": "기숙사 생활"
    },
    {
        "id": "C10",
        "name": "남기태",
        "age": 55,
        "gender": "남",
        "job": "고위직 은퇴 예정",
        "financial_status": "자산 5억 이상",
        "risk_tolerance": "중간",
        "primary_goal": "상속 계획 및 안정 운용",
        "family_lifestyle": "배우자+성인 자녀"
    }
]

# 2. 실습용 금융상품 (10개)
FINANCIAL_PRODUCTS = [
    {
        "code": "P001",
        "name": "스마트안심채권",
        "type": "채권형",
        "expected_return": "3.2%",
        "risk_level": "낮음",
        "target_customer": "은퇴 대비 고객",
        "duration": "3년",
        "marketing_slogan": "든든한 미래를 위한 한 걸음",
        "release_year": 2021,
        "features": "정부 보증, 중도 해지 가능"
    },
    {
        "code": "E104",
        "name": "글로벌혁신ETF",
        "type": "ETF",
        "expected_return": "9.5%",
        "risk_level": "높음",
        "target_customer": "수익 추구형",
        "duration": "장기",
        "marketing_slogan": "미래는 기술에 있다!",
        "release_year": 2022,
        "features": "나스닥 기반 혁신기업 집중"
    },
    {
        "code": "R033",
        "name": "골든라이프연금펀드",
        "type": "연금형 펀드",
        "expected_return": "5.0%",
        "risk_level": "중간",
        "target_customer": "은퇴 준비자",
        "duration": "5년 이상",
        "marketing_slogan": "노후를 위한 가장 스마트한 선택",
        "release_year": 2019,
        "features": "세액공제 가능, 혼합형 운용"
    },
    {
        "code": "F078",
        "name": "AI테크테마펀드",
        "type": "주식형 펀드",
        "expected_return": "11.2%",
        "risk_level": "높음",
        "target_customer": "젊은 투자자",
        "duration": "2년 이상",
        "marketing_slogan": "인공지능, 당신의 자산을 업그레이드!",
        "release_year": 2023,
        "features": "AI 성장주 집중"
    },
    {
        "code": "R102",
        "name": "K-주거안정펀드",
        "type": "부동산 REITs",
        "expected_return": "4.0%",
        "risk_level": "중간",
        "target_customer": "실물자산 선호자",
        "duration": "3~5년",
        "marketing_slogan": "안정적인 임대 수익, 부동산으로",
        "release_year": 2020,
        "features": "부동산 배당형 투자"
    },
    {
        "code": "S019",
        "name": "마이키즈교육적금",
        "type": "적금형 상품",
        "expected_return": "2.5%",
        "risk_level": "매우 낮음",
        "target_customer": "교육비 준비자",
        "duration": "5년",
        "marketing_slogan": "아이 미래를 위한 첫걸음",
        "release_year": 2018,
        "features": "확정금리, 월불입형"
    },
    {
        "code": "M055",
        "name": "비전플랜혼합펀드",
        "type": "혼합형 펀드",
        "expected_return": "6.5%",
        "risk_level": "중간",
        "target_customer": "중장기 분산투자자",
        "duration": "3~7년",
        "marketing_slogan": "주식과 채권, 균형의 미학",
        "release_year": 2020,
        "features": "채권+주식 혼합형"
    },
    {
        "code": "D087",
        "name": "디지털그로스인덱스",
        "type": "인덱스 펀드",
        "expected_return": "8.0%",
        "risk_level": "중간~높음",
        "target_customer": "성장 추구형",
        "duration": "3년 이상",
        "marketing_slogan": "글로벌 디지털 경제를 담다",
        "release_year": 2022,
        "features": "글로벌 지수 추종, 기술주 중심"
    },
    {
        "code": "B022",
        "name": "세이프웰보장예금",
        "type": "정기예금",
        "expected_return": "3.0%",
        "risk_level": "낮음",
        "target_customer": "원금 보장 중시",
        "duration": "1년",
        "marketing_slogan": "내 돈은 안전하게",
        "release_year": 2024,
        "features": "원금 보장, 단기 예치 가능"
    },
    {
        "code": "T065",
        "name": "G-그린에너지펀드",
        "type": "테마형 펀드",
        "expected_return": "7.8%",
        "risk_level": "중간~높음",
        "target_customer": "친환경 관심 고객",
        "duration": "2~4년",
        "marketing_slogan": "지구를 살리는 투자",
        "release_year": 2021,
        "features": "친환경 에너지 기업 중심"
    }
]

# 3. 고객별 금융상품 정답안 (모범 매칭)
GROUND_TRUTH = {
    "C01": {
        "customer": "김은희 (52세, 은퇴 3년 전, 리스크 회피)",
        "recommended_products": ["골든라이프연금펀드", "스마트안심채권"],
        "reason": "은퇴 준비, 안정성 중시, 세액공제 가능, 정부 보증"
    },
    "C02": {
        "customer": "박준영 (28세, 수익 추구형)",
        "recommended_products": ["AI테크테마펀드", "글로벌혁신ETF"],
        "reason": "고수익 기대, 기술/ETF 친숙, 장기 목표 있음"
    },
    "C03": {
        "customer": "이소영 (35세, 싱글맘, 소득 불안정)",
        "recommended_products": ["마이키즈교육적금", "세이프웰보장예금"],
        "reason": "원금 보장 중요, 교육비 준비 필요, 고정금리 적합"
    },
    "C04": {
        "customer": "전성훈 (45세, 안정+증식 지향)",
        "recommended_products": ["비전플랜혼합펀드", "골든라이프연금펀드"],
        "reason": "중간 수준 리스크 감내, 안정과 성장 균형 운용"
    },
    "C05": {
        "customer": "윤정아 (31세, 프리랜서, 변동성 큼)",
        "recommended_products": ["디지털그로스인덱스", "K-주거안정펀드"],
        "reason": "성장 추구, 소득 변동성 대응 위한 분산형 투자"
    },
    "C06": {
        "customer": "오지훈 (63세, 은퇴자, 연금 외 무수익)",
        "recommended_products": ["스마트안심채권", "세이프웰보장예금"],
        "reason": "유동성 + 안정성 최우선, 원금 보장 중심"
    },
    "C07": {
        "customer": "장민호 (40세, 소득 높지만 지출 큼)",
        "recommended_products": ["비전플랜혼합펀드", "G-그린에너지펀드"],
        "reason": "자산 증식 희망, 장기 테마형 투자로 리스크 분산"
    },
    "C08": {
        "customer": "최수연 (48세, 공무원, 귀촌 준비)",
        "recommended_products": ["K-주거안정펀드", "골든라이프연금펀드"],
        "reason": "안정적 부동산 수익, 귀촌 이후의 현금 흐름 대비"
    },
    "C09": {
        "customer": "임다혜 (25세, 대학원생, 유학 준비)",
        "recommended_products": ["세이프웰보장예금", "마이키즈교육적금"],
        "reason": "단기 자금 확보 필요, 리스크 허용도 매우 낮음"
    },
    "C10": {
        "customer": "남기태 (55세, 상속과 안정 운용 목표)",
        "recommended_products": ["스마트안심채권", "K-주거안정펀드"],
        "reason": "자산 보호 중시, 부동산 기반 수익 + 정부 보증 활용"
    }
}
