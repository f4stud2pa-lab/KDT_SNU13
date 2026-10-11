---
name: stock-report
description: >-
  관심 종목 시세 수집 → Notion Stock-DB 적재 → 그래프 포함 분석 보고서 작성 → 감사까지 한 번에 실행하는 오케스트레이션.
  Use when the user asks to 주식 정보를 조사해서 Stock-DB 에 넣고 보고서까지 작성, 시세 업데이트 후 리포트 갱신, or invokes /stock-report.
  인자 예: "/stock-report 삼성SDI, LG에너지솔루션 추가" · "/stock-report 수집만" · "/stock-report 보고서만 runs/2026-10-08"
---

# /stock-report — 주식 데이터 → Notion 보고서 파이프라인

이 스킬을 실행하는 메인 세션이 **오케스트레이터**다. 서브에이전트는 서로를 부를 수 없으므로 단계 연결과 결과 전달은 여기서 한다.
시작 전에 `CLAUDE.md` 전체를 읽는다 (Notion ID, 스키마, 수집·보고서 규칙).

## 0. 요청 해석
인자/요청에서 정한다. 비어 있으면 괄호 안 기본값.
- **종목**: 추가·제외할 종목 (기본: `scripts/watchlist.json` 그대로)
- **범위**: 전체 / 수집만 / DB만 / 보고서만 / 감사만 (기본: 전체)
- **보고서 위치**: (기본: Stock-DataPage 의 Stock-DB 아래 — 새 보고서를 끝에 추가)
- **실행 폴더**: `runs/<기준일>` — 수집 후 `rows.json` 의 기준일로 정한다. 먼저 `runs/<오늘>` 로 수집한 뒤 기준일과 다르면 폴더 이름을 기준일로 바꾼다.

기존 보고서를 **교체**할지 **새로 추가**할지 모호하면, 사용자에게 한 번만 묻는다 (기본은 추가).

## 1. 사전 점검 (직접)
```bash
test -x .venv/bin/python || (python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt)
```
- `ToolSearch` 로 Notion 도구를 불러오고 `notion-get-self` 로 워크스페이스가 `StockAgent-Workspace` 인지 확인. 다르면 멈추고 사용자에게 알린다.
- `notion-fetch` 로 Stock-DataPage 와 Stock-DB 가 `CLAUDE.md` 의 ID 로 열리는지 확인.

## 2. 수집 → `stock-data-collector`
Agent 호출 프롬프트에 포함할 것: 종목 변경 내용, 실행 폴더 경로, "결과는 rows.json/metrics.json/checks.md 로, Notion 에는 쓰지 말 것".
완료 후 직접 확인: `rows.json` 행 수, `checks.md` 핵심.

## 3. DB 적재 → `notion-db-manager`
프롬프트: 실행 폴더 경로, "중복(종목코드+기준일)은 갱신", "notion_rows.md 기록".
완료 후 생성/갱신 수를 확인.

## 4. 보고서 → `stock-report-writer`
프롬프트: 실행 폴더, 대상 페이지 ID, 새로 추가인지 교체인지, "그래프를 맨 위에".

## 5. 감사 → `stock-report-auditor`
프롬프트: 실행 폴더, 대상 페이지 ID.
- "수정 필요"면 `audit.md` 경로를 주고 `stock-report-writer` 에 수정 요청 → 다시 감사. **최대 2회**. 그래도 남으면 남은 항목을 사용자에게 그대로 알린다.

## 6. 사용자 보고 (한국어, 짧게)
- Notion 페이지 링크, 기준일(휴장 여부)
- 넣은 행 수(생성/갱신), 비상장 등 예외
- 보고서 핵심 3~4줄
- 주의할 점: KRX/NXT 차이, 감사에서 남은 항목, 확인하지 못한 것

## 실패 시
- 네이버 API 빈 응답/오류 → 1회 재시도, 계속 실패하면 해당 종목만 빼고 진행하고 보고.
- Notion 권한/ID 오류 → `notion-search` 로 제목 검색해 새 ID 를 찾고 `CLAUDE.md` 갱신 후 진행.
- 업로드 URL 만료 → `notion-create-file-upload` 를 다시 호출.
