import OpenAI, { APIError } from "openai";

export const KEY_HEADER = "x-openai-key";

export function clientFromRequest(request: Request): OpenAI | Response {
  const apiKey = request.headers.get(KEY_HEADER)?.trim();
  if (!apiKey) return errorResponse(401, "OpenAI API 키가 없습니다. 화면 오른쪽 위 'API 키 설정'에서 입력해 주세요.");
  if (!apiKey.startsWith("sk-")) return errorResponse(401, "OpenAI API 키 형식이 아닙니다. 'sk-'로 시작하는 키를 입력해 주세요.");
  return new OpenAI({ apiKey, maxRetries: 1, timeout: 30_000 });
}

export function errorResponse(status: number, message: string): Response {
  return Response.json({ error: message }, { status });
}

export function mapOpenAIError(err: unknown): Response {
  if (err instanceof APIError) {
    const detail = err.message ? ` (OpenAI: ${err.message})` : "";
    switch (err.status) {
      case 401:
        return errorResponse(401, "API 키가 올바르지 않거나 만료되었습니다." + detail);
      case 403:
        return errorResponse(403, "이 API 키로는 선택한 모델이나 기능(웹 검색, 백그라운드 실행)을 쓸 수 없습니다." + detail);
      case 404:
        return errorResponse(404, "선택한 모델을 찾을 수 없습니다. 다른 모델을 선택해 주세요." + detail);
      case 429:
        return errorResponse(429, "요청 한도를 넘었거나 크레딧이 부족합니다. 잠시 후 다시 시도하거나 OpenAI 결제 상태를 확인해 주세요." + detail);
      case 400:
        return errorResponse(400, "요청이 거부되었습니다." + detail);
      default:
        if (err.status && err.status >= 500) {
          return errorResponse(502, "OpenAI 서버 오류입니다. 잠시 후 다시 시도해 주세요." + detail);
        }
        return errorResponse(502, "OpenAI 연결에 실패했습니다." + detail);
    }
  }
  return errorResponse(500, "서버에서 알 수 없는 오류가 발생했습니다.");
}
