export type BriefInput = {
  company: string;
  role: string;
  org: string;
  postingUrl: string;
  postingText: string;
  grade: string;
  major: string;
  experience: string;
  essayQuestions: string;
};

export const EMPTY_BRIEF: BriefInput = {
  company: "",
  role: "",
  org: "",
  postingUrl: "",
  postingText: "",
  grade: "4학년",
  major: "데이터사이언스",
  experience: "",
  essayQuestions: "",
};

export function validateBrief(input: BriefInput): string | null {
  if (!input.company.trim()) return "기업명을 입력해 주세요.";
  if (!input.role.trim()) return "지원직무를 입력해 주세요.";
  if (input.postingUrl.trim() && !/^https?:\/\//.test(input.postingUrl.trim())) {
    return "채용공고 링크는 http:// 또는 https://로 시작해야 합니다.";
  }
  return null;
}

function orDefault(value: string, fallback: string) {
  return value.trim() || fallback;
}

export function buildBriefMarkdown(input: BriefInput, baseDate: string): string {
  return `# 00_brief – 정규화된 입력
- 분석 기준일: ${baseDate}

| 필드 | 값 |
|---|---|
| 기업명 | ${input.company.trim()} |
| 지원직무 | ${input.role.trim()} |
| 사업부/조직 | ${orDefault(input.org, "해당 없음 (조직 미지정) → 배치 가능성이 높은 조직 후보를 [합리적 추정]으로 제시")} |
| 채용공고 링크 | ${orDefault(input.postingUrl, "제공되지 않음 → 공식 채용페이지, 사업보고서 등 최신 1차 자료 탐색")} |
| 학년 | ${orDefault(input.grade, "미입력")} |
| 전공 | ${orDefault(input.major, "미입력")} |

## 채용공고 내용
${orDefault(input.postingText, "공고 내용 직접 입력 없음 → 해당 기업 최신 공식 채용공고 탐색")}

## 내 경험
${orDefault(
  input.experience,
  "직접 입력한 경험 없음 → 해당 직무 합격을 위해 이 전공자가 어필하기 가장 유리한 일반적인 캡스톤/프로젝트/실습 예시를 제시하되, 모든 예시에 [예시 경험 – 실제 경험 아님] 표기"
)}

## 자소서 문항
${orDefault(input.essayQuestions, "입력 없음 → 해당 기업 최근 공개 문항 탐색, 없으면 대기업 공통 문항 유형으로 대체하고 명시")}
`;
}
