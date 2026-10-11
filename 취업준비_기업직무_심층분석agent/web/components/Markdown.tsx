"use client";

import { Children, isValidElement, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { GRADE_LABELS } from "@/lib/report";

const GRADE_PATTERN = new RegExp(
  `(?<!\`)\\[((?:${GRADE_LABELS.map((g) => g.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})[^\\]]*)\\](?![(\`])`,
  "g"
);
const BADGE_PREFIX = "grade:";

const BADGE_STYLES: Record<string, string> = {
  "공식자료 확인": "bg-emerald-100 text-emerald-800 ring-emerald-300",
  "복수자료 확인": "bg-sky-100 text-sky-800 ring-sky-300",
  "외부자료 참고": "bg-amber-100 text-amber-800 ring-amber-300",
  "합리적 추정": "bg-violet-100 text-violet-800 ring-violet-300",
  "판단 근거 부족": "bg-rose-100 text-rose-800 ring-rose-300",
  "예시 경험 – 실제 경험 아님": "bg-orange-100 text-orange-900 ring-orange-400",
};

function markGrades(markdown: string): string {
  let inFence = false;
  return markdown
    .split("\n")
    .map((line) => {
      if (/^\s*(```|~~~)/.test(line)) inFence = !inFence;
      return inFence ? line : line.replace(GRADE_PATTERN, (_, label) => `\`${BADGE_PREFIX}${label}\``);
    })
    .join("\n");
}

function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) {
    const child = node.props.children;
    if (typeof child === "string" && child.startsWith(BADGE_PREFIX)) return child.slice(BADGE_PREFIX.length);
    return textOf(child);
  }
  return "";
}

export function slugify(text: string): string {
  return (
    "h-" +
    text
      .trim()
      .toLowerCase()
      .replace(/[^\p{L}\p{N}]+/gu, "-")
      .replace(/^-|-$/g, "")
  );
}

const components: Components = {
  code({ children, className }) {
    const text = Children.toArray(children).join("");
    if (!className && text.startsWith(BADGE_PREFIX)) {
      const label = text.slice(BADGE_PREFIX.length);
      const style =
        Object.entries(BADGE_STYLES).find(([key]) => label.startsWith(key))?.[1] ?? "bg-slate-100 text-slate-700 ring-slate-300";
      return (
        <span className={`mx-0.5 inline-block whitespace-nowrap rounded px-1.5 align-middle text-[0.72em] leading-5 font-medium ring-1 ring-inset ${style}`}>
          {label}
        </span>
      );
    }
    return <code className={className}>{children}</code>;
  },
  h2({ children }) {
    return <h2 id={slugify(textOf(children))}>{children}</h2>;
  },
  table({ children }) {
    return (
      <div className="table-wrap">
        <table>{children}</table>
      </div>
    );
  },
  a({ children, href }) {
    return (
      <a href={href} target="_blank" rel="noreferrer noopener">
        {children}
      </a>
    );
  },
};

export default function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {markGrades(children)}
      </ReactMarkdown>
    </div>
  );
}
