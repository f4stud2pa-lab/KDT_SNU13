"use client";

import { useMemo, useState } from "react";
import { listH2 } from "@/lib/report";
import Markdown, { slugify } from "./Markdown";

type Props = {
  markdown: string;
  fileName: string;
  finished: boolean;
};

export default function ReportView({ markdown, fileName, finished }: Props) {
  const [copied, setCopied] = useState(false);
  const toc = useMemo(() => listH2(markdown), [markdown]);

  function download() {
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function copy() {
    await navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[14rem_1fr]">
      <nav className="lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:self-start lg:overflow-auto">
        <div className="mb-3 flex flex-wrap gap-2">
          <button className="btn-primary text-xs" onClick={download}>
            FINAL_REPORT.md 다운로드
          </button>
          <button className="btn-ghost text-xs" onClick={copy}>
            {copied ? "복사됨" : "마크다운 복사"}
          </button>
        </div>
        {!finished && <p className="mb-2 text-xs text-amber-700">분석이 끝나지 않아 일부 섹션만 보입니다.</p>}
        <ol className="space-y-1 text-sm">
          {toc.map((title) => (
            <li key={title}>
              <a href={`#${slugify(title)}`} className="text-slate-700 hover:text-blue-600">
                {title}
              </a>
            </li>
          ))}
        </ol>
      </nav>
      <article className="min-w-0">
        <Markdown>{markdown}</Markdown>
      </article>
    </div>
  );
}
