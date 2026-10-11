# AnalReport — 주식 데이터 수집 · Notion 분석 보고서

네이버 증권에서 관심 종목 시세를 수집해 Notion `Stock-DB`에 쌓고, 그 데이터로 그래프가 들어간 분석 보고서를 Notion 페이지에 작성하는 프로젝트다.
모든 결과물(DB 행, 보고서)은 **Notion**에 있고, 이 폴더에는 재현용 스크립트·지침·에이전트 정의만 둔다.

- 전체 흐름을 한 번에 돌리려면: `/stock-report` 스킬 (`.claude/skills/stock-report/SKILL.md`)
- 단계별 전문 작업: `.claude/agents/` 의 서브에이전트 4개 (아래 "에이전트 구성")
- 응답·보고서 언어: **한국어**. 쉬운 말로, 숫자에는 단위와 기준일을 붙인다.

---

## 1. Notion 연결 정보 (claude.ai Notion 커넥터)

| 항목 | 값 |
|---|---|
| 워크스페이스 | `StockAgent-Workspace` (id `f3cc854c-4547-8164-9719-00038d1d9876`) |
| 계정 | jjini55@swu.ac.kr |
| 섹션 | 모두 **Private**. Shared 섹션은 비어 있음 |

### 페이지 · DB 지도

| 이름 | 종류 | ID | 용도 |
|---|---|---|---|
| 🔋 Stock-News | 페이지 | `3f6c854c454780faa623d4516568856f` | 삼성SDI 단일 종목 리포트 (2026-10-11 작성). 맨 위 "정리글" 토글에 중복 문장 있음 |
| Stock-DataPage | 페이지 | `3f6c854c4547800f8739dfae4bc976c2` | **Stock-DB(인라인) + 그 아래 다종목 분석 보고서** |
| Stock-DB | 데이터베이스 | `3f6c854c454780c6b0b4e6c341026387` | 시세 수집 DB (Stock-DataPage 안 인라인) |
| └ 데이터 소스 | collection | `collection://3f6c854c-4547-8040-b994-000bbabddf29` | 행 추가·스키마 변경 시 이 ID 사용 |
| └ 기본 뷰 | view | `view://3f6c854c-4547-804c-9834-000c4cab8006` | 테이블 뷰 |
| Stock-MultiAgent | 페이지 | `3f6c854c454780d690ebe6290454093b` | 빈 페이지 (예약) |
| 프롬프트 | 페이지 | `3f6c854c454780de8ca0cdce50b6a2f6` | 사용자가 보낸 프롬프트 기록. **읽기만 하고 수정하지 않는다** |

> ID가 바뀌었거나 찾을 수 없으면 `notion-search` 로 제목 검색 → `notion-fetch` 로 확인한 뒤 이 표를 갱신한다.

### Stock-DB 스키마 (1행 = 1종목 × 1거래일 스냅샷)

| 컬럼 | 타입 | 넣는 값 / 네이버 API 필드 |
|---|---|---|
| 종목명 | title | watchlist 이름 (예: `에코프로머티리얼즈` — 네이버는 `에코프로머티`로 줄여 줌) |
| 종목코드 | text | 6자리 `itemCode` |
| 시장 | select | 코스피 / 코스닥 / 코넥스 |
| 기준일 | date | `localTradedAt` 의 날짜 (`date:기준일:start`, `date:기준일:is_datetime: 0`) |
| 현재가 · 전일대비 · 시가 · 고가 · 저가 · 52주 최고 · 52주 최저 · 시간외 가격 | number(won) | **원 단위 정수** |
| 등락률(%) | number | `-2.05` 처럼 퍼센트 숫자 그대로 (0.0205 아님) |
| 등락구분 | select | 상한가 / 상승 / 보합 / 하락 / 하한가 |
| 거래량 | number | 주 단위 |
| 거래대금 · 시가총액 | number(won) | **원 단위**. 네이버의 `7,240억`·`45조 6,920억` 을 환산 (억 미만 반올림) |
| 외국인 소진율(%) · PER · PBR | number | 적자로 PER 이 `N/A` 면 **비워 둔다** (0 넣지 않음) |
| 장 상태 | select | 장중 / 장마감 / 거래정지 |
| 수집 랭킹 | multi_select | 랭킹 탭에서 수집했을 때만: 시가총액, 거래량 상위, 거래대금 상위, 거래량 급증, 거래량 급감, 상승, 하락, 52주 최고, 52주 최저, 인기 종목 |
| 상세 URL | url | `newPcUrl` |
| 메모 | text | 전일·추정PER·EPS·원문 대금/시총·출처, KRX 단독값과의 차이 |
| 수집일시 | created_time | 자동 |

스키마를 바꿀 때는 `notion-update-data-source` 의 SQL DDL(`ADD COLUMN` 등)을 쓰고, 이 표도 함께 고친다.

### 현재 들어 있는 데이터 (2026-10-11 기준)
- 2026-10-08 종가 기준 10행: POSCO홀딩스, 에코프로, 고려아연, 에코프로머티리얼즈, 엔켐, SK아이이테크놀로지(SKIET), 포스코퓨처엠, 삼성SDI, LG에너지솔루션, **SK온(비상장 — 메모만)**
- Stock-DataPage 의 Stock-DB 아래에 "2차전지·소재 10개 종목 분석 보고서" 작성됨 (그래프 3장). DB 와 보고서 사이에 사용자가 넣은 스크린샷 이미지가 하나 있다 — 건드리지 않는다.

---

## 2. 데이터 수집 규칙

### 소스
- `https://stock.naver.com/...` 페이지는 **WebFetch 가 차단**된다. 같은 데이터를 주는 공개 API 를 `curl -A "Mozilla/5.0"` 로 부른다.

| API | 내용 |
|---|---|
| `m.stock.naver.com/api/stock/{code}/basic` | 종목명, 종가, 전일대비, 등락률, 등락구분, 장 상태, 시간외, 기준시각 |
| `m.stock.naver.com/api/stock/{code}/integration` | `totalInfos`: 전일·시가·고가·저가·거래량·대금·시총·외인소진율·52주 최고/최저·PER·EPS·추정PER·PBR·BPS·배당 |
| `m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=N` | 시가총액 랭킹 (KOSDAQ 도 가능) |
| `api.finance.naver.com/siseJson.naver?symbol={code}&requestType=1&startTime=YYYYMMDD&endTime=YYYYMMDD&timeframe=day` | **KRX 단독** 일별 OHLCV + 외국인소진율 |
| `ac.stock.naver.com/ac?q={종목명}&target=stock` | 종목 검색 (코드 확인 · 상장 여부 확인) |

### 반드시 지킬 것
1. **스크립트를 쓴다**: `.venv/bin/python scripts/collect_naver.py --out runs/YYYY-MM-DD` → `rows.json`, `metrics.json`, `checks.md`. 직접 손으로 숫자를 옮겨 적지 않는다.
2. **KRX+NXT 통합값 주의**: 네이버 `basic`/`integration` 의 전일대비·거래량·대금·52주 범위는 넥스트레이드(NXT) 거래를 합친 값이라 **KRX 단독 값과 거의 모든 종목에서 다르다** (예: 삼성SDI 10/8 전일대비 네이버 +5,000 vs KRX +10,000, 52주 최고 820,000 vs 723,000). DB 에는 네이버 통합값을 넣고, KRX 단독값은 `메모`에 남긴다(스크립트가 자동 처리). 보고서에서 이 차이를 반드시 유의사항으로 적는다.
3. **비상장 종목**(예: SK온): 검색 API 로 확인 → 시세 컬럼은 비우고 `메모`에 "비상장, 확인일"만. 숫자를 만들어 넣지 않는다.
4. **휴장일**: 기준일은 API 의 `localTradedAt` 을 따른다. 주말·공휴일(예: 10/9 한글날)에 수집하면 직전 거래일 값이다. 보고서 기준일에 "(휴장)"을 명시.
5. **중복 방지**: 같은 `종목코드` + `기준일` 행이 이미 있으면 새로 만들지 말고 `notion-update-page`(update_properties)로 갱신한다. 확인은 `notion-search`(data_source_url 지정) 또는 `notion-fetch` 로.
6. 숫자는 JSON number 로(문자열 X), 날짜는 `date:기준일:start` 형식으로 넣는다.

---

## 3. 보고서 작성 규칙 (Notion 페이지)

- 위치: 사용자가 정한 페이지. 기본은 **Stock-DataPage 의 Stock-DB 아래** (`notion-update-page` → `insert_content`, `position: end`). 기존 보고서를 새로 쓸 땐 `---` 구분선 아래에 새 보고서를 붙이거나, 사용자에게 교체 여부를 묻는다. **`replace_content` 로 페이지를 통째로 바꾸지 않는다** (인라인 DB·스크린샷이 지워질 수 있음).
- **보고서 맨 위에 그래프**: 제목 → 기준일/작성일 줄 → 개요 차트 이미지 → 요약 callout 순서.
- 구성 (Stock-News, Stock-DataPage 보고서와 같은 스타일):
  1. `# 제목` + 기준일·작성일 (`<mention-date start="YYYY-MM-DD"/>`)
  2. 개요 차트 (`stockdb_overview.png`)
  3. `<callout icon="📌" color="blue_bg">` **한눈에 보기** 3~5줄
  4. `## 1. 종목별 핵심 지표` 표 (`<table fit-page-width="true" header-row="true">`, 상승 `<span color="red">` / 하락 `<span color="blue">`, 비상장 행 `color="gray_bg"`)
  5. `## 2. 52주 가격 위치` + `stockdb_52w.png` + 해석 bullet
  6. `## 3. 밸류에이션과 거래 열기` + `stockdb_valuation.png` + `<columns>` 2단 해석
  7. `## 4. 밸류체인별 정리` 표 (watchlist 의 `group`)
  8. `## 5. 체크 포인트` 체크리스트 `- [ ]`
  9. `<callout icon="ℹ️" color="gray_bg">` **자료 및 유의사항** (출처, KRX/NXT 차이, 추정치 여부, "투자 권유가 아님")
- 문장 규칙: 근거 없는 전망·매수/매도 권유 금지. 해석은 DB 숫자에서 바로 나오는 것만. 외부 뉴스를 쓰면 링크를 단다.
- 작성 후 **반드시 `notion-fetch` 로 다시 읽어** 이미지 3장·표·columns·callout 이 들어갔는지 확인한다.

### 차트 → Notion 이미지 업로드 절차
1. `.venv/bin/python scripts/make_charts.py runs/YYYY-MM-DD` → `runs/.../charts/*.png`. 생성 후 `Read` 로 이미지를 열어 글자 겹침·잘림을 눈으로 확인.
2. 파일마다 `notion-create-file-upload {"filename": "xxx.png"}` → 응답의 `upload_url`, `upload_headers.authorization`.
3. `curl -s -X POST "<upload_url>" -H "authorization: <값>" -F "file=@<경로>;type=image/png"` → `"status":"uploaded"` 확인. (URL 은 약 1시간 내 만료, 1회용)
4. 본문에 `<image src="file-upload://<file_upload_id>"></image>` 로 넣는다.

### 차트 규칙
- 한글 폰트: macOS `AppleGothic` (`/System/Library/Fonts/Supplemental/AppleGothic.ttf`). `axes.unicode_minus=False` 필수, 본문에 `−`(U+2212) 쓰지 말 것. bold 굵기 없음(경고는 무시 가능).
- 색: 상승 빨강 `#e34948`, 하락 파랑 `#2a78d6` (국내 관례). 크기 비교는 파랑 단색, 한 축만 사용(이중 축 금지).
- 각 차트에 제목·단위·출처 한 줄.

---

## 4. 에이전트 구성

메인 세션(또는 `/stock-report` 스킬)이 **오케스트레이터** 역할을 한다. 서브에이전트는 다른 서브에이전트를 부를 수 없으므로, 단계 연결은 메인 세션이 한다. 각 단계는 `runs/YYYY-MM-DD/` 의 파일로 결과를 넘긴다.

| 순서 | 에이전트 | 하는 일 | 읽는 것 → 쓰는 것 |
|---|---|---|---|
| 1 | `stock-data-collector` | watchlist 갱신, 네이버 수집, KRX 교차검증 | `scripts/watchlist.json` → `runs/D/rows.json`, `metrics.json`, `checks.md` |
| 2 | `notion-db-manager` | Stock-DB 스키마 확인, 중복 확인 후 행 추가/갱신 | `rows.json` → Notion Stock-DB, `runs/D/notion_rows.md` |
| 3 | `stock-report-writer` | 차트 생성·업로드, 보고서 작성 | `metrics.json`, `checks.md` → `charts/*.png`, Notion 페이지 |
| 4 | `stock-report-auditor` | 숫자 대조·형식·유의사항 검증 (수정은 하지 않음) | Notion 페이지 + `metrics.json` → `runs/D/audit.md` |

감사에서 문제가 나오면 메인 세션이 `stock-report-writer` 에게 `audit.md` 를 근거로 수정을 맡긴다 (최대 2회).

간단한 요청(행 몇 개 추가, 표 한 줄 수정)은 서브에이전트 없이 메인 세션이 바로 처리해도 된다.

---

## 5. 도구 사용 메모

- Notion·WebFetch 도구는 **지연 로딩**된다. 쓰기 전에 `ToolSearch` 로 불러온다:
  `select:mcp__claude_ai_Notion__notion-fetch,mcp__claude_ai_Notion__notion-search,mcp__claude_ai_Notion__notion-create-pages,mcp__claude_ai_Notion__notion-update-page,mcp__claude_ai_Notion__notion-update-data-source,mcp__claude_ai_Notion__notion-create-file-upload`
- 행 추가: `notion-create-pages` + `parent: {"type":"data_source_id","data_source_id":"3f6c854c-4547-8040-b994-000bbabddf29"}`, `pages[].properties` 에 `rows.json` 항목을 그대로.
- Notion 본문 문법이 헷갈리면 `notion-fetch` 에 `notion://docs/enhanced-markdown-spec` 을 넘겨 확인.
- Python: 이 폴더의 `.venv` (matplotlib 설치됨). 없으면 `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
- 날짜·숫자는 추측하지 말고 API 응답과 `checks.md` 를 근거로 쓴다. 오늘 날짜는 시스템 날짜 기준.
