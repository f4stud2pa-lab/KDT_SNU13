import { clientFromRequest, errorResponse, mapOpenAIError } from "@/lib/openaiServer";

export const maxDuration = 30;

const ID_PATTERN = /^resp_[a-zA-Z0-9]+$/;

export async function GET(request: Request, ctx: RouteContext<"/api/agent/[id]">) {
  const { id } = await ctx.params;
  if (!ID_PATTERN.test(id)) return errorResponse(400, "응답 ID 형식이 올바르지 않습니다.");
  const client = clientFromRequest(request);
  if (client instanceof Response) return client;

  try {
    const response = await client.responses.retrieve(id);
    const done = response.status === "completed" || response.status === "incomplete";
    return Response.json({
      status: response.status,
      text: done ? response.output_text : undefined,
      incompleteReason: response.incomplete_details?.reason ?? undefined,
      error: response.error?.message ?? undefined,
      usage: response.usage
        ? { input: response.usage.input_tokens, output: response.usage.output_tokens }
        : undefined,
    });
  } catch (err) {
    return mapOpenAIError(err);
  }
}

export async function DELETE(request: Request, ctx: RouteContext<"/api/agent/[id]">) {
  const { id } = await ctx.params;
  if (!ID_PATTERN.test(id)) return errorResponse(400, "응답 ID 형식이 올바르지 않습니다.");
  const client = clientFromRequest(request);
  if (client instanceof Response) return client;

  try {
    const response = await client.responses.cancel(id);
    return Response.json({ status: response.status });
  } catch (err) {
    return mapOpenAIError(err);
  }
}
