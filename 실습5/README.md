# 🔍 AI 텍스트 쿼리 기반 이미지 검색 및 스마트 이미지 분류 시스템

사용자가 입력한 자연어 텍스트 쿼리와 가장 관련성이 높은 이미지를 **OpenAI Vision API**와 **OpenAI 임베딩 API(text-embedding-3-small)**, 그리고 **코사인 유사도(Cosine Similarity)** 분석을 통해 찾아주고, **임의의 이미지를 넣었을 때 카테고리별로 자동 분류(Classification)** 및 **유사 이미지 탐색**까지 수행하는 지능형 Python 프로그램입니다.

---

## 📌 주요 기능 및 특징

1. **Vision API 기반 텍스트 설명 자동 생성 & 캐싱**:
   - 이미지의 시각적 특징(피사체, 배경, 색감, 분위기 등)을 OpenAI Vision API(`gpt-4o`)로 분석하여 고품질 한국어 설명으로 자동 변환.
   - `image_metadata_cache.json`에 영구 캐싱하여 속도 최적화 및 토큰 비용 절약.
   - 오프라인 환경에서도 안전하게 실행되는 Graceful Fallback 내장.

2. **OpenAI Embedding API 벡터 변환**:
   - 이미지 설명 및 검색 쿼리를 최신 임베딩 모델(`text-embedding-3-small`, 1536차원)을 통해 고차원 벡터로 변환.

3. **코사인 유사도(Cosine Similarity) 정밀 분석**:
   - 쿼리 벡터와 모든 이미지 설명 벡터 간 코사인 유사도를 계산하여 관련도 순위 산출.
   - $\cos(\theta) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$

4. **결과 출력 (최우선 1위 및 Top 3 랭킹)**:
   - 1위 매칭 이미지를 단독 하이라이트로 표시하고, 상위 3개(Top 3) 이미지를 순위, 유사도 점수, 일치도 백분율(%), 설명 카드와 함께 출력.

5. **🌟 [신규 확장] 임의의 이미지 자동 분류 (Zero-Shot Classification)**:
   - 사용자가 임의의 새로운 이미지 파일을 제공하면, Vision API가 시각적 요소를 파악하고 사전 정의된 카테고리(자연/풍경, 동물/반려동물, 도시/건축, 겨울/설경, 바다/휴양지, 음식, 인물 등)와의 **벡터 임베딩 코사인 유사도**를 비교하여 가장 알맞은 카테고리로 자동 분류합니다.
   - 분류 신뢰도(%), 판단 사유(Reasoning), 전체 카테고리별 유사도 순위표를 함께 제공합니다.

6. **🌟 [신규 확장] 이미지-to-이미지 유사도 역검색**:
   - 임의의 이미지를 쿼리로 입력하면, 현재 보관함에 있는 이미지들 중 가장 닮은 이미지를 코사인 유사도로 찾아냅니다.

7. **🌟 [신규 확장] 신규 이미지 동적 등록 (Dynamic Ingestion)**:
   - 새로운 이미지를 보관함에 추가하면 Vision 분석 및 임베딩을 즉시 수행하여 이후 검색 대상에 실시간 반영합니다.

8. **인터페이스 지원**:
   - **인터랙티브 CLI (`image_search.py`)**: 검색, 이미지 분류(`classify`), 유사 이미지 검색(`imgsearch`), 새 이미지 추가(`add`)
   - **Streamlit 웹 대시보드 (`image_search_web.py`)**: 4개 탭(텍스트 검색 / 이미지 분류 / 유사 이미지 / 이미지 등록)의 직관적인 UI 제공

---

## 🗂️ 프로젝트 파일 구성

| 파일명 | 역할 및 설명 |
| :--- | :--- |
| [image_search_engine.py](file:///Users/jeong-uijin/Desktop/fintech13/16.%20AI응용/psLLMChatBot/%EC%8B%A4%EC%8A%B55/image_search_engine.py) | **핵심 엔진**: Vision 설명 생성, 임베딩 변환, 코사인 유사도, 이미지 분류, 동적 인덱싱 |
| [image_search.py](file:///Users/jeong-uijin/Desktop/fintech13/16.%20AI응용/psLLMChatBot/%EC%8B%A4%EC%8A%B55/image_search.py) | **메인 CLI 프로그램**: 텍스트 검색, `classify`, `imgsearch`, `add` 명령어 지원 |
| [image_search_web.py](file:///Users/jeong-uijin/Desktop/fintech13/16.%20AI응용/psLLMChatBot/%EC%8B%A4%EC%8A%B55/image_search_web.py) | **웹 대시보드 UI**: Streamlit 기반 4개 탭 브라우저 대시보드 |
| [prepare_search_images.py](file:///Users/jeong-uijin/Desktop/fintech13/16.%20AI응용/psLLMChatBot/%EC%8B%A4%EC%8A%B55/prepare_search_images.py) | **샘플 이미지 생성기**: 5가지 테마의 고품질 샘플 이미지 자동 생성 |
| [test_image_search.py](file:///Users/jeong-uijin/Desktop/fintech13/16.%20AI응용/psLLMChatBot/%EC%8B%A4%EC%8A%B55/test_image_search.py) | **단위 테스트 스위트**: 코사인 유사도 및 검색/분류 시나리오 자동 검증 (15개 테스트 100% 통과) |
| `search_images/` | 검색 대상 이미지 파일들이 보관되는 디렉토리 |
| `image_metadata_cache.json` | 이미지 설명 및 임베딩 벡터가 저장되는 캐시 파일 |

---

## 💻 실행 및 사용 방법

### 1. 임의의 이미지 카테고리 자동 분류 (신규 기능)
```bash
python3 image_search.py --classify search_images/image1_sunset_mountain.bmp
```
**출력 예시:**
```text
🏷️ [이미지 분류 결과] 최적 카테고리: 자연 및 풍경 (Nature & Landscape)
📊 신뢰도/유사도: 0.7717 (77.2%)
📝 이미지 분석 내용:
  산 위로 붉고 따뜻하게 저무는 황금빛 노을과 웅장한 자연 속 석양 풍경입니다.
💡 판단 사유:
  이미지 분석 내용의 의미 벡터가 '자연 및 풍경' 카테고리의 정의 벡터와 가장 높은 일치도(77.2%)를 보였습니다.
📋 전체 카테고리별 유사도 순위:
 #1 자연 및 풍경 (Nature & Landscape)     | +0.7717 ( 77.2%) [███████]
 #2 겨울 및 설경 (Winter & Snow)          | +0.3263 ( 32.6%) [███]
 #3 인물 및 일상 (People & Daily Life)    | +0.2596 ( 26.0%) [██]
 ...
```

### 2. 임의의 이미지를 통한 유사 이미지 역검색 (신규 기능)
```bash
python3 image_search.py --imgsearch search_images/image1_sunset_mountain.bmp
```

### 3. 대화형 CLI 모드 (모든 기능 통합 콘솔)
```bash
python3 image_search.py
```
- 검색어 입력: `자연 속 석양`
- 이미지 분류: `classify <이미지경로>`
- 유사 이미지: `imgsearch <이미지경로>`
- 이미지 추가: `add <이미지경로> [제목]`
- 목록 확인: `list`
- 종료: `q`

### 4. 텍스트 쿼리 즉시 검색
```bash
python3 image_search.py --query "자연 속 석양"
```

### 5. Streamlit 웹 대시보드 실행
```bash
streamlit run image_search_web.py
```
> 브라우저에서 4개 탭을 통해 검색, 이미지 파일 업로드 분류, 유사 이미지 찾기, 새 이미지 등록을 마우스 클릭으로 간편하게 이용할 수 있습니다.

### 6. 단위 테스트 실행
```bash
python3 test_image_search.py
```
