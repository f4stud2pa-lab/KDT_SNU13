import { AGENTS, type AgentName } from "./agents";

export const COMMON_PRINCIPLES = `1. 단순 복사 금지. 홈페이지·공고 문구를 옮기지 말고 이 회사의 사업·제품·공정과 연결해 풀어 쓴다.
2. 모든 사실 진술 끝에 출처 등급을 붙인다: [공식자료 확인] [복수자료 확인] [외부자료 참고] [합리적 추정](추론 근거 한 줄) [판단 근거 부족]
3. "소통", "책임감", "열정", "문제해결력"을 단독으로 쓰지 않는다. 누구와/어떤 상황에서/무엇을/어떻게 했는지 행동 수준으로 쓴다.
4. 사용자가 주지 않은 경험을 사용자 경험처럼 쓰지 않는다. 예시는 반드시 [예시 경험 – 실제 경험 아님] 표기. 관점 전환(재해석)은 허용.
5. 기업분석 → 직무분석 → 필요역량 → 컬처핏 → 내 경험 → 자소서/면접이 앞 단계 결론을 근거로 이어지게 한다.
6. 공식 인재상을 그대로 조직문화로 쓰지 않는다. 직무 단위의 구체적 일하는 방식으로 분해한다.
7. 진행 중인 채용은 게시일·마감일을 확인한다. 수치는 기준 연도를 표기하고, 2년 이상 지난 자료는 (YYYY년 자료)를 붙인다.
8. 업계 용어는 처음 나올 때 한 줄로 풀어 쓴다.`;

const WEB_ENVIRONMENT = `[실행 환경 안내 – 웹앱]
- 이 환경에서는 파일을 읽거나 쓸 수 없다. 시스템 지시의 "입력 파일"은 아래 [앞 단계 결과] 블록으로 제공된다.
- 시스템 지시의 "출력 파일"에 저장할 내용 전체를 마크다운으로 응답 본문에 바로 작성한다. 파일 저장 안내, 인사말, 작업 후기는 쓰지 않는다.
- 섹션 제목은 반드시 "## 번호. 제목" 형식(예: "## 2-1. 직무의 존재 이유", "## 12. 커리어패스")을 지킨다. 하위 항목은 ### 이하를 쓴다.
- 서브에이전트를 호출할 수 없다. 맡은 섹션은 직접 끝까지 작성한다.`;

function block(key: string, content: string | undefined) {
  return `<<<${key}.md\n${content?.trim() || "(이 단계 결과 없음 – 실패했거나 건너뜀. 해당 근거는 [판단 근거 부족]으로 처리)"}\n>>>`;
}

export function buildAgentInput(
  agent: AgentName,
  baseDate: string,
  outputs: Record<string, string | undefined>,
  extra?: string
): string {
  const meta = AGENTS[agent];
  const parts = [
    WEB_ENVIRONMENT,
    `[작업] ${meta.label} – ${meta.sections}\n[기준일] ${baseDate}`,
    `[공통 원칙]\n${COMMON_PRINCIPLES}`,
    `[앞 단계 결과]\n${meta.inputs.map((key) => block(key, outputs[key])).join("\n\n")}`,
  ];

  if (agent === "quality-auditor") {
    parts.push(`[추가 출력 규칙]
응답의 맨 마지막 줄에 재실행이 필요한 담당 서브에이전트를 다음 형식으로 한 줄 적는다. 치명 이슈가 있는 에이전트만 적고 없으면 none.
RERUN: agent-name-1, agent-name-2
사용 가능한 이름: company-industry-analyst, role-reality-analyst, posting-interpreter, competency-skill-mapper, culture-fit-analyst, experience-strategist, interview-designer`);
  }

  if (agent === "job-analysis-orchestrator") {
    parts.push(`[이번 작업 범위]
서브에이전트 결과는 이미 모두 위에 있다. 섹션 1~15는 웹앱이 자동으로 합치므로 다시 쓰지 않는다.
너는 다음 두 부분만 작성한다.
1. "## 분석 전제" – 공고 확보 여부와 게시/마감일, 조직 미지정 여부, 경험 미입력 여부, 품질 감사에서 남은 한계를 bullet로 정리
2. "## 16. 최종 합격자 관점 압축 정리" – 시스템 지시의 섹션 16 템플릿 13개 항목을 모두 작성 (### 1. ~ ### 13.)`);
  }

  if (extra) parts.push(extra);
  return parts.join("\n\n");
}

export function parseRerun(auditText: string, allowed: readonly AgentName[]): AgentName[] {
  const line = auditText
    .split("\n")
    .reverse()
    .find((l) => /^\s*\**RERUN\**\s*:/i.test(l));
  if (!line) return [];
  const names = line.split(":").slice(1).join(":").split(/[,\s]+/).map((s) => s.replace(/[`*]/g, "").trim());
  return allowed.filter((name) => names.includes(name));
}

export function stripRerunLine(text: string): string {
  return text.replace(/\n?\s*\**RERUN\**\s*:.*\s*$/i, "").trimEnd();
}
