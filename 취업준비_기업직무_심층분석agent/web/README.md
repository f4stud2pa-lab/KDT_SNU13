# 취업 준비 기업·직무 심층분석 웹앱

`.cursor/agents/`의 오케스트레이터와 9개 서브에이전트 프롬프트를 그대로 사용하는 Next.js 앱입니다.
사용자가 자기 OpenAI API 키를 입력하면, 브라우저가 Phase 1~6을 순서대로 실행해 16개 섹션 보고서를 만듭니다.

## 로컬 실행

```bash
cd web
npm install
npm run dev   # http://localhost:3000
```

`npm run dev`와 `npm run build`는 시작 전에 `scripts/sync-prompts.mjs`를 실행해 `.cursor/agents/*.md`를 `lib/prompts.generated.ts`로 복사합니다. 에이전트 프롬프트를 고친 뒤에는 생성된 파일도 함께 커밋하세요.

`npm run check`는 보고서 조립 로직(섹션 정렬, 감사 재실행 파싱)을 검사합니다.

## Vercel 배포

1. 이 저장소(워크스페이스 루트)를 GitHub에 push합니다.
2. [vercel.com/new](https://vercel.com/new)에서 저장소를 Import합니다.
3. **Root Directory를 `web`으로 지정**합니다. Framework는 Next.js로 자동 인식됩니다.
4. 환경변수는 필요 없습니다. API 키는 각 사용자가 화면에서 입력합니다.
5. Deploy 후 발급된 `https://<프로젝트>.vercel.app` 주소를 공유하면 됩니다.

## 동작 방식

- `POST /api/agent`: 에이전트 이름(화이트리스트), 입력, 모델을 받아 OpenAI Responses API에 백그라운드 작업으로 등록하고 응답 ID를 돌려줍니다. 리서치 계열 에이전트에는 `web_search` 도구가 켜집니다.
- `GET /api/agent/[id]`: 작업 상태와 완료된 결과를 돌려줍니다. 브라우저가 4초마다 확인합니다.
- `DELETE /api/agent/[id]`: 실행 중인 작업을 취소합니다.
- 에이전트 하나가 몇 분씩 걸려도 서버 요청은 각각 짧게 끝나므로 Vercel 함수 시간 제한에 걸리지 않습니다.
- 단계별 결과와 API 키는 브라우저 localStorage에만 저장됩니다. 서버는 아무것도 저장하지 않습니다.
