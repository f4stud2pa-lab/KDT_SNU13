import { stripRerunLine } from "./agentPrompt";
import { AGENTS, type AgentName } from "./agents";
import type { RunState } from "./pipeline";

export const SECTION_TITLES: Record<number, string> = {
  1: "기업 이해",
  2: "실제 업무 기준 직무 분석",
  3: "채용공고 문장별 해석",
  4: "필요 전공지식",
  5: "필요 기술 / Tool",
  6: "핵심 역량",
  7: "이 직무의 '좋은 신입'",
  8: "자소서 키워드",
  9: "경험-직무 연결",
  10: "예상 면접 질문",
  11: "꼬리질문 시나리오",
  12: "커리어패스",
  13: "직무 장단점",
  14: "유사 직무 / 타사 동일 직무 비교",
  15: "인재상·컬처핏",
  16: "최종 합격자 관점 압축 정리",
};

export const GRADE_LABELS = [
  "공식자료 확인",
  "복수자료 확인",
  "외부자료 참고",
  "합리적 추정",
  "판단 근거 부족",
  "예시 경험 – 실제 경험 아님",
] as const;

const SECTION_AGENTS: AgentName[] = [
  "company-industry-analyst",
  "role-reality-analyst",
  "posting-interpreter",
  "competency-skill-mapper",
  "culture-fit-analyst",
  "experience-strategist",
  "interview-designer",
];

type Chunk = { major: number; minor: number; order: number; heading: string; body: string };

const NUMBERED = /^##\s+\**\s*(\d{1,2})(?:-(\d{1,2}))?\s*[.)]?\s*(.*)$/;

function splitByH2(markdown: string): { heading: string | null; body: string }[] {
  const parts: { heading: string | null; body: string }[] = [{ heading: null, body: "" }];
  let inFence = false;
  for (const line of markdown.split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) inFence = !inFence;
    if (!inFence && /^##\s/.test(line)) {
      parts.push({ heading: line, body: "" });
    } else {
      parts[parts.length - 1].body += line + "\n";
    }
  }
  return parts;
}

function demote(markdown: string): string {
  let inFence = false;
  return markdown
    .split("\n")
    .map((line) => {
      if (/^\s*(```|~~~)/.test(line)) inFence = !inFence;
      return !inFence && /^#{1,5}\s/.test(line) ? "#" + line : line;
    })
    .join("\n");
}

export function listH2(markdown: string): string[] {
  return splitByH2(markdown)
    .map((part) => part.heading)
    .filter((heading): heading is string => heading !== null)
    .map((heading) => heading.replace(/^##\s+/, "").trim());
}

function fallbackMajor(agent: AgentName): number {
  const match = AGENTS[agent].sections.match(/\d+/);
  return match ? Number(match[0]) : 99;
}

export function assembleReport(state: RunState): string {
  const chunks: Chunk[] = [];
  const sources: string[] = [];
  let order = 0;

  for (const agent of SECTION_AGENTS) {
    const output = state.agents[agent].output;
    if (!output) continue;
    let lastChunk: Chunk | null = null;

    for (const part of splitByH2(output)) {
      if (part.heading === null) {
        if (part.body.trim()) {
          lastChunk = { major: fallbackMajor(agent), minor: 0, order: order++, heading: "", body: part.body };
          chunks.push(lastChunk);
        }
        continue;
      }
      const numbered = part.heading.match(NUMBERED);
      if (numbered && SECTION_TITLES[Number(numbered[1])]) {
        lastChunk = {
          major: Number(numbered[1]),
          minor: numbered[2] ? Number(numbered[2]) : 0,
          order: order++,
          heading: part.heading,
          body: part.body,
        };
        chunks.push(lastChunk);
      } else if (/출처/.test(part.heading)) {
        sources.push(`### ${AGENTS[agent].label}\n${part.body.trim()}`);
      } else if (/하류|전달용/.test(part.heading)) {
        continue;
      } else if (lastChunk) {
        lastChunk.body += `\n${part.heading.replace(/^##/, "###")}\n${part.body}`;
      }
    }
  }

  chunks.sort((a, b) => a.major - b.major || a.minor - b.minor || a.order - b.order);

  const { company, role } = state.brief;
  const summary = state.agents["job-analysis-orchestrator"].output ?? "";
  const summaryParts = splitByH2(summary);
  const premise = summaryParts.find((p) => p.heading && /분석 전제/.test(p.heading));
  const section16 = summaryParts
    .filter((p) => p.heading && /^##\s+\**\s*16/.test(p.heading))
    .map((p) => p.body)
    .join("\n");

  const lines: string[] = [
    `# ${company} ${role} 심층 분석 보고서`,
    "",
    `- 분석 기준일: ${state.baseDate}`,
    `- 사용 모델: ${state.model} (reasoning: ${state.effort})`,
    `- 근거 표기 범례: ${GRADE_LABELS.map((g) => `[${g}]`).join(" ")}`,
    "",
  ];

  if (premise) lines.push("## 분석 전제", premise.body.trim(), "");

  let currentMajor = -1;
  for (const chunk of chunks) {
    if (chunk.major !== currentMajor) {
      currentMajor = chunk.major;
      lines.push(`## ${chunk.major}. ${SECTION_TITLES[chunk.major] ?? "기타"}`, "");
    }
    if (chunk.minor > 0) {
      lines.push(demote(`${chunk.heading}\n${chunk.body}`).trim(), "");
    } else {
      lines.push(chunk.body.trim(), "");
    }
  }

  if (section16.trim()) {
    lines.push(`## 16. ${SECTION_TITLES[16]}`, "", section16.trim(), "");
  } else if (summary.trim()) {
    lines.push(`## 16. ${SECTION_TITLES[16]}`, "", summary.trim(), "");
  }

  const evidence = state.agents["job-research-scout"].output;
  if (evidence || sources.length) {
    lines.push("## 부록 A. 근거 자료와 출처", "");
    if (evidence) lines.push(demote(demote(evidence)).trim(), "");
    if (sources.length) lines.push("### 분석 단계에서 추가된 출처", "", ...sources.map((s) => demote(s)), "");
  }

  const audit = state.agents["quality-auditor"].output;
  if (audit) lines.push("## 부록 B. 품질 감사 결과", "", demote(demote(stripRerunLine(audit))).trim(), "");

  return lines.join("\n").replace(/\n{3,}/g, "\n\n");
}
