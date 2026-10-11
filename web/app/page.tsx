"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ApiKeyDialog from "@/components/ApiKeyDialog";
import BriefForm from "@/components/BriefForm";
import ProgressBoard from "@/components/ProgressBoard";
import ReportView from "@/components/ReportView";
import { MODEL_OPTIONS, type AgentName } from "@/lib/agents";
import { EMPTY_BRIEF, validateBrief, type BriefInput } from "@/lib/brief";
import { createRun, isRunFinished, PipelineRunner, type RunState } from "@/lib/pipeline";
import { assembleReport } from "@/lib/report";
import { loadApiKey, loadRun, loadSettings, saveApiKey, saveRun, saveSettings } from "@/lib/storage";

type Tab = "progress" | "report";

export default function Home() {
  const [hydrated, setHydrated] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(MODEL_OPTIONS[0].id);
  const [effort, setEffort] = useState("medium");
  const [brief, setBrief] = useState<BriefInput>(EMPTY_BRIEF);
  const [run, setRun] = useState<RunState | null>(null);
  const [busy, setBusy] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("progress");
  const runnerRef = useRef<PipelineRunner | null>(null);
  const apiKeyRef = useRef("");

  useEffect(() => {
    const savedKey = loadApiKey();
    const settings = loadSettings();
    const savedRun = loadRun();
    /* eslint-disable react-hooks/set-state-in-effect -- one-time restore from localStorage after hydration */
    setApiKey(savedKey);
    if (settings) {
      setModel(settings.model);
      setEffort(settings.effort);
    }
    if (savedRun) {
      setRun(savedRun);
      setBrief(savedRun.brief);
      if (isRunFinished(savedRun)) setTab("report");
    }
    setHydrated(true);
    /* eslint-enable react-hooks/set-state-in-effect */
  }, []);

  useEffect(() => {
    apiKeyRef.current = apiKey;
  }, [apiKey]);

  const report = useMemo(() => (run ? assembleReport(run) : ""), [run]);
  const finished = run ? isRunFinished(run) : false;
  const hasUnfinished = run && !finished && !busy;
  const doneCount = run ? Object.values(run.agents).filter((a) => a.status === "done").length : 0;

  function makeRunner(state: RunState) {
    const runner = new PipelineRunner(
      state,
      () => apiKeyRef.current,
      (next) => {
        setRun(next);
        saveRun(next);
      }
    );
    runnerRef.current = runner;
    return runner;
  }

  async function execute(task: (runner: PipelineRunner) => Promise<void>, state: RunState) {
    if (!apiKeyRef.current) {
      setDialogOpen(true);
      return;
    }
    setBusy(true);
    const runner = makeRunner(state);
    try {
      await task(runner);
    } finally {
      setBusy(false);
      runnerRef.current = null;
    }
    if (isRunFinished(runner.current)) setTab("report");
  }

  async function start() {
    const error = validateBrief(brief);
    setFormError(error);
    if (error) return;
    if (!apiKeyRef.current) {
      setDialogOpen(true);
      return;
    }
    const state = createRun(brief, model, effort);
    setRun(state);
    saveRun(state);
    setTab("progress");
    await execute((runner) => runner.run(), state);
  }

  async function resume() {
    if (run) await execute((runner) => runner.run(), { ...run, model, effort });
  }

  async function retry(name: AgentName) {
    if (run) await execute((runner) => runner.rerunSingle(name), { ...run, model, effort });
  }

  async function stop() {
    await runnerRef.current?.stop();
  }

  function reset() {
    if (busy) return;
    if (run && !window.confirm("현재 분석 결과를 지우고 새로 시작할까요? 필요하면 먼저 보고서를 다운로드하세요.")) return;
    setRun(null);
    saveRun(null);
    setTab("progress");
  }

  const formLocked = Boolean(run);

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6">
      <header className="mb-6 flex flex-wrap items-center gap-3">
        <div>
          <h1 className="text-xl font-bold sm:text-2xl">취업 준비 기업·직무 심층분석 에이전트</h1>
          <p className="text-sm text-slate-600">
            채용 컨설턴트 + 현직자 직무분석가 + 산업분석 애널리스트 관점의 9개 전문 에이전트가 단계별로 분석해 16개 섹션 보고서를 만듭니다.
          </p>
        </div>
        <button className="btn-ghost ml-auto" onClick={() => setDialogOpen(true)}>
          {hydrated && apiKey ? "API 키 설정됨 · " : "API 키 설정 · "}
          {model}
        </button>
      </header>

      <section className="card mb-6">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold">분석 대상</h2>
          {formLocked && <span className="text-xs text-slate-500">진행 중인 분석의 입력값입니다. 바꾸려면 &lsquo;새 분석&rsquo;을 누르세요.</span>}
        </div>
        <BriefForm value={brief} onChange={setBrief} disabled={formLocked} />
        {formError && <p className="mt-3 text-sm text-rose-600">{formError}</p>}
        <div className="mt-5 flex flex-wrap items-center gap-2">
          {!run && (
            <button className="btn-primary" onClick={start} disabled={!hydrated}>
              분석 시작
            </button>
          )}
          {busy && (
            <button className="btn-ghost text-rose-600" onClick={stop}>
              중지
            </button>
          )}
          {hasUnfinished && (
            <button className="btn-primary" onClick={resume}>
              이어서 실행
            </button>
          )}
          {run && !busy && (
            <button className="btn-ghost" onClick={reset}>
              새 분석
            </button>
          )}
          {run && (
            <span className="text-sm text-slate-600">
              {doneCount}/10 단계 완료{busy ? " · 실행 중 (탭을 닫으면 멈춥니다)" : ""}
            </span>
          )}
        </div>
        {!run && (
          <p className="mt-3 text-xs text-slate-500">
            분석 1회는 모델과 검색량에 따라 보통 10~30분이 걸립니다. 단계별 결과는 이 브라우저에 저장되어, 중간에 멈춰도 &lsquo;이어서 실행&rsquo;으로 계속할 수 있습니다.
          </p>
        )}
      </section>

      {run && (
        <section className="card">
          <div className="mb-4 flex gap-1 border-b border-slate-200">
            {(["progress", "report"] as Tab[]).map((t) => (
              <button
                key={t}
                className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${tab === t ? "border-blue-600 text-blue-700" : "border-transparent text-slate-500"}`}
                onClick={() => setTab(t)}
              >
                {t === "progress" ? "진행 상황" : finished ? "최종 보고서" : "보고서 미리보기"}
              </button>
            ))}
          </div>
          {tab === "progress" ? (
            <ProgressBoard run={run} busy={busy} onRetry={retry} />
          ) : (
            <ReportView
              markdown={report}
              finished={finished}
              fileName={`${run.brief.company}_${run.brief.role}_FINAL_REPORT.md`.replace(/[\\/:*?"<>|\s]+/g, "_")}
            />
          )}
        </section>
      )}

      {dialogOpen && (
        <ApiKeyDialog
          initialKey={apiKey}
          initialModel={model}
          initialEffort={effort}
          onClose={() => setDialogOpen(false)}
          onSave={(key, nextModel, nextEffort) => {
            setApiKey(key);
            apiKeyRef.current = key;
            saveApiKey(key);
            setModel(nextModel);
            setEffort(nextEffort);
            saveSettings({ model: nextModel, effort: nextEffort });
            setDialogOpen(false);
          }}
        />
      )}
    </div>
  );
}
