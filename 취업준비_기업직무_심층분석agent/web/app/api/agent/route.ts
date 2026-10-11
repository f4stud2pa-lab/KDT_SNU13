import type OpenAI from "openai";
import { AGENTS, EFFORT_OPTIONS, isAgentName } from "@/lib/agents";
import { clientFromRequest, errorResponse, mapOpenAIError } from "@/lib/openaiServer";
import { AGENT_PROMPTS } from "@/lib/prompts.generated";

export const maxDuration = 60;

const MAX_INPUT_CHARS = 1_000_000;
const MODEL_PATTERN = /^[a-zA-Z0-9._:-]{1,64}$/;

type CreateBody = {
  agent?: unknown;
  input?: unknown;
  model?: unknown;
  effort?: unknown;
};

export async function POST(request: Request) {
  const client = clientFromRequest(request);
  if (client instanceof Response) return client;

  let body: CreateBody;
  try {
    body = await request.json();
  } catch {
    return errorResponse(400, "요청 본문이 올바른 JSON이 아닙니다.");
  }

  if (!isAgentName(body.agent)) return errorResponse(400, "알 수 없는 에이전트입니다.");
  if (typeof body.input !== "string" || body.input.length === 0) return errorResponse(400, "입력 내용이 비어 있습니다.");
  if (body.input.length > MAX_INPUT_CHARS) return errorResponse(413, "입력이 너무 깁니다. 경험/공고 내용을 줄여 주세요.");
  if (typeof body.model !== "string" || !MODEL_PATTERN.test(body.model)) return errorResponse(400, "모델 이름이 올바르지 않습니다.");
  const effort = EFFORT_OPTIONS.find((o) => o.id === body.effort)?.id ?? "medium";

  const agent = AGENTS[body.agent];
  const tools: OpenAI.Responses.Tool[] = agent.webSearch
    ? [{ type: "web_search", search_context_size: "medium", user_location: { type: "approximate", country: "KR" } }]
    : [];

  try {
    const response = await client.responses.create({
      model: body.model,
      instructions: AGENT_PROMPTS[agent.name],
      input: body.input,
      tools,
      reasoning: { effort },
      max_output_tokens: 64_000,
      background: true,
      store: true,
    });
    return Response.json({ id: response.id, status: response.status });
  } catch (err) {
    return mapOpenAIError(err);
  }
}
