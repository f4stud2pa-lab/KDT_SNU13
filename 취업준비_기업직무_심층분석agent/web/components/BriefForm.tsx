"use client";

import type { BriefInput } from "@/lib/brief";

type Props = {
  value: BriefInput;
  onChange: (value: BriefInput) => void;
  disabled?: boolean;
};

type Field = {
  key: keyof BriefInput;
  label: string;
  placeholder: string;
  multiline?: boolean;
  required?: boolean;
  half?: boolean;
};

const FIELDS: Field[] = [
  { key: "company", label: "기업명", placeholder: "예: 삼성전자", required: true, half: true },
  { key: "role", label: "지원직무", placeholder: "예: 데이터 분석 / 공정기술", required: true, half: true },
  { key: "org", label: "사업부/조직", placeholder: "비워두면 '조직 미지정'으로 처리", half: true },
  { key: "postingUrl", label: "채용공고 링크", placeholder: "비워두면 공식 채용페이지에서 최신 공고 탐색", half: true },
  { key: "grade", label: "학년", placeholder: "예: 4학년", half: true },
  { key: "major", label: "전공", placeholder: "예: 데이터사이언스", half: true },
  {
    key: "postingText",
    label: "채용공고 내용",
    placeholder: "공고의 수행업무/지원자격/우대사항을 붙여넣으세요. 비워두면 최신 공식 공고를 찾아 분석합니다.",
    multiline: true,
  },
  {
    key: "experience",
    label: "내 경험",
    placeholder:
      "프로젝트, 캡스톤, 인턴, 공모전 등을 경험별로 적어 주세요. 비워두면 전공자에게 유리한 예시 프로젝트를 [예시 경험 – 실제 경험 아님]으로 제시합니다.",
    multiline: true,
  },
  {
    key: "essayQuestions",
    label: "자소서 문항",
    placeholder: "문항과 글자 수를 붙여넣으세요. 비워두면 해당 기업의 최근 문항이나 대기업 공통 유형을 사용합니다.",
    multiline: true,
  },
];

export default function BriefForm({ value, onChange, disabled }: Props) {
  return (
    <fieldset disabled={disabled} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {FIELDS.map((field) => (
        <label key={field.key} className={field.half ? "block" : "block sm:col-span-2"}>
          <span className="text-sm font-medium">
            {field.label}
            {field.required && <span className="ml-1 text-rose-600">*</span>}
          </span>
          {field.multiline ? (
            <textarea
              className="input mt-1 min-h-28"
              value={value[field.key]}
              placeholder={field.placeholder}
              onChange={(e) => onChange({ ...value, [field.key]: e.target.value })}
            />
          ) : (
            <input
              className="input mt-1"
              value={value[field.key]}
              placeholder={field.placeholder}
              onChange={(e) => onChange({ ...value, [field.key]: e.target.value })}
            />
          )}
        </label>
      ))}
    </fieldset>
  );
}
