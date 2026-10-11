"use client";

import { useEffect, useState } from "react";
import { AGENTS, PARALLEL_PHASES, PHASES, type AgentName } from "@/lib/agents";
import type { AgentRun, RunState } from "@/lib/pipeline";
import Markdown from "./Markdown";

type Props = {
  run: RunState;
  busy: boolean;
  onRetry: (name: AgentName) => void;
};

const STATUS_LABEL: Record<AgentRun["status"], { text: string; style: string }> = {
  idle: { text: "대기", style: "bg-slate-100 text-slate-600" },
  running: { text: "실행 중", style: "bg-blue-100 text-blue-700 animate-pulse" },
  done: { text: "완료", style: "bg-emerald-100 text-emerald-700" },
  error: { text: "오류", style: "bg-rose-100 text-rose-700" },
  cancelled: { text: "중지됨", style: "bg-amber-100 text-amber-800" },
};

function formatDuration(ms: number) {
  const s = Math.max(0, Math.round(ms / 1000));
  return s < 60 ? `${s}초` : `${Math.floor(s / 60)}분 ${s % 60}초`;
}

export default function ProgressBoard({ run, busy, onRetry }: Props) {
  const anyRunning = Object.values(run.agents).some((a) => a.status === "running");
  const [now, setNow] = useState(() => Date.now());
  const [openRaw, setOpenRaw] = useState<AgentName | null>(null);

  useEffect(() => {
    if (!anyRunning) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [anyRunning]);

  const totals = Object.values(run.agents).reduce(
    (acc, a) => ({ input: acc.input + (a.usage?.input ?? 0), output: acc.output + (a.usage?.output ?? 0) }),
    { input: 0, output: 0 }
  );

  return (
    <div className="space-y-4">
      {PHASES.map((phase) => (
        <div key={phase.id} className={`rounded-lg border p-3 ${run.currentPhase === phase.id ? "border-blue-400 bg-blue-50/40" : "border-slate-200"}`}>
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
            <span>
              Phase {phase.id}. {phase.title}
            </span>
            {PARALLEL_PHASES.has(phase.id) && <span className="text-xs font-normal text-slate-500">(동시 실행)</span>}
          </div>
          <ul className="space-y-2">
            {phase.agents.map((name) => {
              const agent = run.agents[name];
              const meta = AGENTS[name];
              const label = STATUS_LABEL[agent.status];
              const elapsed = agent.startedAt ? (agent.finishedAt ?? now) - agent.startedAt : 0;
              return (
                <li key={name} className="rounded-md bg-white p-2 text-sm shadow-sm ring-1 ring-slate-100">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${label.style}`}>{label.text}</span>
                    <span className="font-medium">{meta.label}</span>
                    <span className="text-xs text-slate-500">{meta.sections}</span>
                    <span className="ml-auto flex items-center gap-2 text-xs text-slate-500">
                      {agent.startedAt && <span>{formatDuration(elapsed)}</span>}
                      {agent.attempts > 1 && <span>시도 {agent.attempts}회</span>}
                      {agent.output && (
                        <button className="text-blue-600 underline" onClick={() => setOpenRaw(openRaw === name ? null : name)}>
                          {openRaw === name ? "원문 닫기" : "원문 보기"}
                        </button>
                      )}
                      {!busy && agent.status !== "running" && (agent.status !== "idle" || agent.attempts > 0) && (
                        <button className="text-slate-700 underline" onClick={() => onRetry(name)}>
                          이 단계만 다시 실행
                        </button>
                      )}
                    </span>
                  </div>
                  {agent.error && <p className="mt-1 text-xs text-rose-700">{agent.error}</p>}
                  {agent.warning && <p className="mt-1 text-xs text-amber-700">{agent.warning}</p>}
                  {openRaw === name && agent.output && (
                    <div className="mt-2 max-h-[28rem] overflow-auto rounded border border-slate-200 bg-slate-50 p-3">
                      <Markdown>{agent.output}</Markdown>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
          {phase.id === 5 && run.reruns && run.reruns.length > 0 && (
            <p className="mt-2 text-xs text-slate-600">
              감사 결과 재작성 대상: {run.reruns.map((n) => AGENTS[n].label).join(", ")}
            </p>
          )}
        </div>
      ))}
      {(totals.input > 0 || totals.output > 0) && (
        <p className="text-xs text-slate-500">
          누적 토큰: 입력 {totals.input.toLocaleString()} / 출력 {totals.output.toLocaleString()}
        </p>
      )}
    </div>
  );
}
