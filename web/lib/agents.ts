import type { AgentName } from "./prompts.generated";

export type { AgentName };

export type AgentMeta = {
  name: AgentName;
  label: string;
  outputKey: string;
  sections: string;
  inputs: string[];
  webSearch: boolean;
};

export const AGENTS: Record<AgentName, AgentMeta> = {
  "job-research-scout": {
    name: "job-research-scout",
    label: "채용·1차 자료 리서치",
    outputKey: "01_evidence_pack",
    sections: "근거 자료 (Evidence Pack)",
    inputs: ["00_brief"],
    webSearch: true,
  },
  "company-industry-analyst": {
    name: "company-industry-analyst",
    label: "기업·산업 분석",
    outputKey: "02_company",
    sections: "섹션 1",
    inputs: ["00_brief", "01_evidence_pack"],
    webSearch: true,
  },
  "role-reality-analyst": {
    name: "role-reality-analyst",
    label: "실제 업무 분석",
    outputKey: "03_role",
    sections: "섹션 2, 12, 13, 14",
    inputs: ["00_brief", "01_evidence_pack"],
    webSearch: true,
  },
  "posting-interpreter": {
    name: "posting-interpreter",
    label: "채용공고 해석",
    outputKey: "04_posting",
    sections: "섹션 3",
    inputs: ["00_brief", "01_evidence_pack"],
    webSearch: false,
  },
  "competency-skill-mapper": {
    name: "competency-skill-mapper",
    label: "역량·전공지식·Tool",
    outputKey: "05_competency",
    sections: "섹션 4, 5, 6, 7, 8",
    inputs: ["00_brief", "01_evidence_pack", "02_company", "03_role", "04_posting"],
    webSearch: false,
  },
  "culture-fit-analyst": {
    name: "culture-fit-analyst",
    label: "조직문화·컬처핏",
    outputKey: "06_culture",
    sections: "섹션 15-1~15-4, 15-7",
    inputs: ["00_brief", "01_evidence_pack", "02_company", "03_role", "04_posting"],
    webSearch: true,
  },
  "experience-strategist": {
    name: "experience-strategist",
    label: "경험 연결·자소서 전략",
    outputKey: "07_experience",
    sections: "섹션 9, 15-5~15-9",
    inputs: ["00_brief", "02_company", "03_role", "04_posting", "05_competency", "06_culture"],
    webSearch: false,
  },
  "interview-designer": {
    name: "interview-designer",
    label: "면접 질문 설계",
    outputKey: "08_interview",
    sections: "섹션 10, 11",
    inputs: ["00_brief", "02_company", "03_role", "04_posting", "05_competency", "06_culture", "07_experience"],
    webSearch: false,
  },
  "quality-auditor": {
    name: "quality-auditor",
    label: "품질 감사",
    outputKey: "09_audit",
    sections: "검증",
    inputs: [
      "00_brief",
      "01_evidence_pack",
      "02_company",
      "03_role",
      "04_posting",
      "05_competency",
      "06_culture",
      "07_experience",
      "08_interview",
    ],
    webSearch: false,
  },
  "job-analysis-orchestrator": {
    name: "job-analysis-orchestrator",
    label: "최종 통합 (섹션 16)",
    outputKey: "10_summary",
    sections: "섹션 16",
    inputs: [
      "00_brief",
      "01_evidence_pack",
      "02_company",
      "03_role",
      "04_posting",
      "05_competency",
      "06_culture",
      "07_experience",
      "08_interview",
      "09_audit",
    ],
    webSearch: false,
  },
};

export const PHASES: { id: number; title: string; agents: AgentName[] }[] = [
  { id: 1, title: "근거 수집", agents: ["job-research-scout"] },
  { id: 2, title: "기업·직무·공고 분석", agents: ["company-industry-analyst", "role-reality-analyst", "posting-interpreter"] },
  { id: 3, title: "역량·컬처 분석", agents: ["competency-skill-mapper", "culture-fit-analyst"] },
  { id: 4, title: "경험·면접 설계", agents: ["experience-strategist", "interview-designer"] },
  { id: 5, title: "품질 검증", agents: ["quality-auditor"] },
  { id: 6, title: "통합 및 섹션 16", agents: ["job-analysis-orchestrator"] },
];

export const PARALLEL_PHASES = new Set([2, 3]);

export const RERUNNABLE_AGENTS: AgentName[] = [
  "company-industry-analyst",
  "role-reality-analyst",
  "posting-interpreter",
  "competency-skill-mapper",
  "culture-fit-analyst",
  "experience-strategist",
  "interview-designer",
];

export function isAgentName(value: unknown): value is AgentName {
  return typeof value === "string" && Object.hasOwn(AGENTS, value);
}

export const MODEL_OPTIONS = [
  { id: "gpt-5.4-mini", label: "gpt-5.4-mini (기본, 빠르고 저렴)" },
  { id: "gpt-5.4", label: "gpt-5.4 (균형)" },
  { id: "gpt-5.5", label: "gpt-5.5 (고품질, 비쌈)" },
];

export const EFFORT_OPTIONS = [
  { id: "low", label: "low (빠름)" },
  { id: "medium", label: "medium (권장)" },
  { id: "high", label: "high (느림, 깊게)" },
] as const;

export type Effort = (typeof EFFORT_OPTIONS)[number]["id"];
