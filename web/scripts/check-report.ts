import assert from "node:assert/strict";
import { buildAgentInput, parseRerun, stripRerunLine } from "../lib/agentPrompt";
import { RERUNNABLE_AGENTS } from "../lib/agents";
import { EMPTY_BRIEF } from "../lib/brief";
import { collectOutputs, createRun } from "../lib/pipeline";
import { assembleReport, listH2 } from "../lib/report";

const run = createRun({ ...EMPTY_BRIEF, company: "테스트전자", role: "데이터 분석" }, "gpt-5.4-mini", "medium");
const done = (output: string) => ({ status: "done" as const, attempts: 1, output });

run.agents["job-research-scout"] = done("# Evidence Pack\n## A. 채용공고\n- 공고 [공식자료 확인]");
run.agents["company-industry-analyst"] = done(
  "## 1-2. 최근 방향성\n투자 [공식자료 확인]\n## 1-1. 핵심 사업\n### (0) 요약\n반도체\n## 하류 에이전트 전달용 요약\n- 내부용\n## 추가 출처\n| a | b |"
);
run.agents["role-reality-analyst"] = done(
  "## 2-1. 존재 이유\n```\n## 코드블록 안 제목\n```\n## 12. 커리어패스\n표\n## 2-2. 실제 업무\n업무"
);
run.agents["competency-skill-mapper"] = done("## 4. 필요한 전공지식\n통계\n## 6. 핵심 역량\n역량");
run.agents["quality-auditor"] = done("# 품질 감사 결과\n- 판정: FAIL\nRERUN: role-reality-analyst, `posting-interpreter`, bogus-agent");
run.agents["job-analysis-orchestrator"] = done("## 분석 전제\n- 공고 미확인\n## 16. 최종 정리\n### 1. 한 문장 직무 정의\n정의");

const reruns = parseRerun(run.agents["quality-auditor"].output!, RERUNNABLE_AGENTS);
assert.deepEqual(reruns, ["role-reality-analyst", "posting-interpreter"]);
assert.ok(!stripRerunLine(run.agents["quality-auditor"].output!).includes("RERUN"));
assert.deepEqual(parseRerun("감사\nRERUN: none", RERUNNABLE_AGENTS), []);

const report = assembleReport(run);
assert.deepEqual(listH2(report), [
  "분석 전제",
  "1. 기업 이해",
  "2. 실제 업무 기준 직무 분석",
  "4. 필요 전공지식",
  "6. 핵심 역량",
  "12. 커리어패스",
  "16. 최종 합격자 관점 압축 정리",
  "부록 A. 근거 자료와 출처",
  "부록 B. 품질 감사 결과",
]);
assert.ok(report.indexOf("### 1-1. 핵심 사업") < report.indexOf("### 1-2. 최근 방향성"), "1-1 before 1-2");
assert.ok(report.indexOf("### 2-1.") < report.indexOf("### 2-2."), "2-1 before 2-2");
assert.ok(report.includes("#### (0) 요약"), "subheadings demoted");
assert.ok(report.includes("## 코드블록 안 제목"), "fenced heading untouched");
assert.ok(!report.includes("내부용"), "handoff summary dropped");
assert.ok(report.includes("### 기업·산업 분석"), "extra sources moved to appendix");

const input = buildAgentInput("interview-designer", run.baseDate, collectOutputs(run));
assert.ok(input.includes("<<<00_brief.md") && input.includes("<<<07_experience.md"));
assert.ok(input.includes("(이 단계 결과 없음"), "missing outputs are marked");

console.log("report checks passed\n");
console.log(report);
