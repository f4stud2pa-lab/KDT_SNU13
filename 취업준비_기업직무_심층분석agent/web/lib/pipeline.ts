import { buildAgentInput, parseRerun, stripRerunLine } from "./agentPrompt";
import { AGENTS, PARALLEL_PHASES, PHASES, RERUNNABLE_AGENTS, type AgentName } from "./agents";
import { buildBriefMarkdown, type BriefInput } from "./brief";

export type AgentStatus = "idle" | "running" | "done" | "error" | "cancelled";

export type AgentRun = {
  status: AgentStatus;
  attempts: number;
  responseId?: string;
  output?: string;
  error?: string;
  warning?: string;
  startedAt?: number;
  finishedAt?: number;
  usage?: { input: number; output: number };
};

export type RunState = {
  version: 1;
  brief: BriefInput;
  baseDate: string;
  model: string;
  effort: string;
  agents: Record<AgentName, AgentRun>;
  currentPhase: number | null;
  reruns?: AgentName[];
  rerunDone?: boolean;
  completedAt?: number;
};

const POLL_MS = 4000;
const MAX_POLL_FAILURES = 5;

export function createRun(brief: BriefInput, model: string, effort: string): RunState {
  const agents = Object.fromEntries(
    Object.keys(AGENTS).map((name) => [name, { status: "idle", attempts: 0 } satisfies AgentRun])
  ) as Record<AgentName, AgentRun>;
  return {
    version: 1,
    brief,
    baseDate: todayKST(),
    model,
    effort,
    agents,
    currentPhase: null,
  };
}

function todayKST(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul" }).format(new Date());
}

export function collectOutputs(state: RunState): Record<string, string | undefined> {
  const outputs: Record<string, string | undefined> = {
    "00_brief": buildBriefMarkdown(state.brief, state.baseDate),
  };
  for (const meta of Object.values(AGENTS)) outputs[meta.outputKey] = state.agents[meta.name].output;
  return outputs;
}

export function isRunFinished(state: RunState) {
  return state.agents["job-analysis-orchestrator"].status === "done";
}

class StoppedError extends Error {}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

async function readError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.error === "string") return data.error;
  } catch {}
  return `서버 오류 (HTTP ${res.status})`;
}

export class PipelineRunner {
  private state: RunState;
  private stopped = false;

  constructor(
    initial: RunState,
    private readonly getApiKey: () => string,
    private readonly onChange: (state: RunState) => void
  ) {
    this.state = initial;
  }

  get current(): RunState {
    return this.state;
  }

  private update(mutator: (draft: RunState) => void) {
    const next: RunState = structuredClone(this.state);
    mutator(next);
    this.state = next;
    this.onChange(next);
  }

  private patchAgent(name: AgentName, patch: Partial<AgentRun>) {
    this.update((draft) => {
      draft.agents[name] = { ...draft.agents[name], ...patch };
    });
  }

  private headers(): HeadersInit {
    return { "Content-Type": "application/json", "x-openai-key": this.getApiKey() };
  }

  async stop() {
    this.stopped = true;
    const running = (Object.keys(this.state.agents) as AgentName[]).filter(
      (name) => this.state.agents[name].status === "running"
    );
    await Promise.all(
      running.map(async (name) => {
        const id = this.state.agents[name].responseId;
        if (id) await fetch(`/api/agent/${id}`, { method: "DELETE", headers: this.headers() }).catch(() => {});
        this.patchAgent(name, { status: "cancelled", error: "사용자가 중지했습니다.", responseId: undefined });
      })
    );
    this.update((draft) => {
      draft.currentPhase = null;
    });
  }

  async run(): Promise<void> {
    this.stopped = false;
    try {
      for (const phase of PHASES) {
        if (phase.id === 6) await this.applyAuditReruns();
        const pending = phase.agents.filter((name) => this.state.agents[name].status !== "done");
        if (pending.length === 0) continue;

        this.update((draft) => {
          draft.currentPhase = phase.id;
        });

        if (PARALLEL_PHASES.has(phase.id)) {
          await Promise.all(pending.map((name) => this.runAgent(name)));
        } else {
          for (const name of pending) await this.runAgent(name);
        }

        const failed = phase.agents.filter((name) => this.state.agents[name].status !== "done");
        if (failed.length > 0) {
          this.update((draft) => {
            draft.currentPhase = null;
          });
          return;
        }
      }
      this.update((draft) => {
        draft.currentPhase = null;
        draft.completedAt = Date.now();
      });
    } catch (err) {
      if (!(err instanceof StoppedError)) throw err;
    }
  }

  private async applyAuditReruns() {
    if (this.state.rerunDone) return;
    const audit = this.state.agents["quality-auditor"].output ?? "";
    const reruns = this.state.reruns ?? parseRerun(audit, RERUNNABLE_AGENTS);
    this.update((draft) => {
      draft.reruns = reruns;
      draft.agents["quality-auditor"].output = stripRerunLine(audit);
    });

    if (reruns.length > 0) {
      this.update((draft) => {
        draft.currentPhase = 5;
      });
      const feedback = `[품질 감사 피드백 – 재작성 요청]
아래 감사 결과에서 너(담당 서브에이전트)에게 지정된 [수정 필요] 항목, 특히 치명 이슈를 모두 고친 완성본 전체를 다시 작성한다. 고친 부분만 쓰지 말고 전체를 다시 쓴다.

<<<09_audit.md
${stripRerunLine(audit)}
>>>`;
      await Promise.all(reruns.map((name) => this.runAgent(name, feedback, true)));
    }

    this.update((draft) => {
      draft.rerunDone = true;
    });
  }

  private async runAgent(name: AgentName, extra?: string, isRerun = false) {
    if (this.stopped) throw new StoppedError();
    const previous = this.state.agents[name];
    let responseId = previous.status === "running" ? previous.responseId : undefined;

    if (!responseId) {
      const input = buildAgentInput(name, this.state.baseDate, collectOutputs(this.state), extra);
      this.patchAgent(name, {
        status: "running",
        attempts: previous.attempts + 1,
        error: undefined,
        warning: undefined,
        startedAt: Date.now(),
        finishedAt: undefined,
      });
      try {
        const res = await fetch("/api/agent", {
          method: "POST",
          headers: this.headers(),
          body: JSON.stringify({ agent: name, input, model: this.state.model, effort: this.state.effort }),
        });
        if (!res.ok) return this.fail(name, await readError(res), isRerun, previous);
        responseId = (await res.json()).id as string;
        this.patchAgent(name, { responseId });
      } catch {
        return this.fail(name, "서버에 연결하지 못했습니다. 인터넷 연결을 확인해 주세요.", isRerun, previous);
      }
    }

    let failures = 0;
    while (true) {
      await sleep(POLL_MS);
      if (this.stopped) throw new StoppedError();
      let data: {
        status: string;
        text?: string;
        error?: string;
        incompleteReason?: string;
        usage?: { input: number; output: number };
      };
      try {
        const res = await fetch(`/api/agent/${responseId}`, { headers: this.headers() });
        if (!res.ok) {
          if (res.status >= 500 && ++failures < MAX_POLL_FAILURES) continue;
          return this.fail(name, await readError(res), isRerun, previous);
        }
        data = await res.json();
        failures = 0;
      } catch {
        if (++failures < MAX_POLL_FAILURES) continue;
        return this.fail(name, "진행 상황을 확인하지 못했습니다. 인터넷 연결을 확인해 주세요.", isRerun, previous);
      }

      if (data.status === "queued" || data.status === "in_progress") continue;

      if ((data.status === "completed" || data.status === "incomplete") && data.text?.trim()) {
        this.patchAgent(name, {
          status: "done",
          output: data.text,
          responseId: undefined,
          finishedAt: Date.now(),
          usage: data.usage,
          warning:
            data.status === "incomplete"
              ? `응답이 중간에 잘렸습니다 (${data.incompleteReason ?? "알 수 없는 이유"}). 필요하면 이 단계만 다시 실행하세요.`
              : isRerun
                ? "품질 감사 후 재작성된 결과입니다."
                : undefined,
        });
        return;
      }

      const reason =
        data.error ??
        (data.status === "cancelled" ? "실행이 취소되었습니다." : "모델이 빈 응답을 반환했습니다.");
      return this.fail(name, reason, isRerun, previous);
    }
  }

  private fail(name: AgentName, message: string, isRerun: boolean, previous: AgentRun) {
    if (isRerun && previous.output) {
      this.patchAgent(name, {
        status: "done",
        output: previous.output,
        responseId: undefined,
        finishedAt: Date.now(),
        warning: `품질 감사 후 재작성에 실패해 첫 결과를 유지했습니다: ${message}`,
      });
      return;
    }
    this.patchAgent(name, { status: "error", error: message, responseId: undefined, finishedAt: Date.now() });
  }

  async rerunSingle(name: AgentName) {
    this.stopped = false;
    this.update((draft) => {
      draft.agents[name] = { ...draft.agents[name], status: "idle" };
      if (name === "quality-auditor") {
        draft.reruns = undefined;
        draft.rerunDone = false;
      }
    });
    try {
      await this.runAgent(name);
    } catch (err) {
      if (!(err instanceof StoppedError)) throw err;
    }
  }
}
