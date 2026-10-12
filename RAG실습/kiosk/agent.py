"""키오스크 대화 에이전트: 질의 분석 → 검색(RAG) → 응답 생성(+ function calling) 파이프라인."""
import json
from dataclasses import dataclass, field

from .menu import Menu
from .order import Cart
from .prompts import CONTEXT_TEMPLATE, GREETING, QUERY_ANALYSIS_PROMPT, SYSTEM_PROMPT
from .retriever import HybridRetriever
from .documents import item_document

TOOLS = [
    {"type": "function", "function": {
        "name": "get_menu_item",
        "description": "메뉴 이름으로 해당 메뉴의 정확한 상세 정보(가격, 옵션, 알레르기 등)를 조회한다. 검색 문서에 정보가 없거나 불확실할 때 사용.",
        "parameters": {"type": "object", "properties": {
            "menu_name": {"type": "string", "description": "메뉴 이름 (예: 아메리카노)"}},
            "required": ["menu_name"]}}},
    {"type": "function", "function": {
        "name": "add_to_cart",
        "description": "손님이 주문 의사를 밝힌 메뉴를 장바구니에 담는다. 음료는 size와 temperature가 필요하다.",
        "parameters": {"type": "object", "properties": {
            "menu_name": {"type": "string"},
            "quantity": {"type": "integer", "minimum": 1, "default": 1},
            "size": {"type": "string", "enum": ["tall", "grande", "venti"], "description": "작은=tall, 중간=grande, 큰=venti. 디저트는 생략"},
            "temperature": {"type": "string", "enum": ["hot", "ice"], "description": "디저트는 생략"},
            "options": {"type": "object", "description": "선택한 옵션만 포함", "properties": {
                "extra_shot": {"type": "integer", "minimum": 0, "maximum": 3},
                "syrup": {"type": "array", "items": {"type": "string", "enum": ["vanilla", "hazelnut", "caramel"]}},
                "milk": {"type": "string", "enum": ["regular", "lowfat", "soy", "oat"]},
                "whipped_cream": {"type": "string", "enum": ["normal", "none", "extra"]},
                "decaf": {"type": "boolean"},
                "sweetness": {"type": "string", "enum": ["less", "normal", "more"]},
                "ice_amount": {"type": "string", "enum": ["less", "normal", "more"]},
                "warm_up": {"type": "boolean"}}}},
            "required": ["menu_name"]}}},
    {"type": "function", "function": {
        "name": "update_cart_item",
        "description": "장바구니 항목의 수량을 변경한다. 0이면 삭제.",
        "parameters": {"type": "object", "properties": {
            "line_no": {"type": "integer"}, "quantity": {"type": "integer", "minimum": 0}},
            "required": ["line_no", "quantity"]}}},
    {"type": "function", "function": {
        "name": "remove_from_cart",
        "description": "장바구니에서 항목 하나를 삭제한다. 옵션 변경은 삭제 후 다시 담는다.",
        "parameters": {"type": "object", "properties": {"line_no": {"type": "integer"}}, "required": ["line_no"]}}},
    {"type": "function", "function": {
        "name": "clear_cart",
        "description": "장바구니를 모두 비운다. 손님이 처음부터 다시 하겠다고 할 때만 사용.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "checkout",
        "description": "결제를 진행한다. 반드시 손님이 주문 내역·매장/포장·결제수단을 최종 확인한 뒤에만 호출한다.",
        "parameters": {"type": "object", "properties": {
            "dine_option": {"type": "string", "enum": ["dine_in", "takeout"]},
            "payment_method": {"type": "string", "enum": ["card", "easy_pay", "gifticon"]}},
            "required": ["dine_option", "payment_method"]}}},
]


@dataclass
class TurnTrace:
    """디버그/발표용: 한 턴에서 무슨 일이 일어났는지 기록."""
    analysis: dict = field(default_factory=dict)
    retrieved: list = field(default_factory=list)
    tool_calls: list = field(default_factory=list)


class KioskAgent:
    def __init__(self, menu: Menu, retriever: HybridRetriever, client, model: str = "gpt-4o-mini",
                 max_history_turns: int = 8):
        self.menu = menu
        self.retriever = retriever
        self.client = client
        self.model = model
        self.max_history_turns = max_history_turns
        self.cart = Cart(menu)
        self.history: list[dict] = [{"role": "assistant", "content": GREETING}]
        self.system_prompt = SYSTEM_PROMPT.format(store_name=menu.store["name"])
        self.last_trace = TurnTrace()

    def reset(self):
        self.cart = Cart(self.menu)
        self.history = [{"role": "assistant", "content": GREETING}]

    # ---------- 1. 질의 분석 ----------
    def analyze(self, user_msg: str) -> dict:
        recent = self.history[-6:]
        convo = "\n".join(f"{'손님' if m['role'] == 'user' else '키오스크'}: {m['content']}" for m in recent)
        resp = self.client.chat.completions.create(
            model=self.model, temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": QUERY_ANALYSIS_PROMPT},
                {"role": "user", "content": f"[이전 대화]\n{convo}\n\n[마지막 발화]\n{user_msg}"},
            ],
        )
        try:
            result = json.loads(resp.choices[0].message.content)
        except json.JSONDecodeError:
            result = {}
        result.setdefault("standalone_query", user_msg)
        result.setdefault("sub_queries", [user_msg])
        result.setdefault("intents", [])
        result.setdefault("off_topic", False)
        result.setdefault("preferences", [])
        return result

    # ---------- 2. 검색 ----------
    def retrieve(self, analysis: dict, user_msg: str):
        if analysis["off_topic"]:
            return []
        queries = [analysis["standalone_query"], *analysis["sub_queries"]]
        if analysis["preferences"]:
            queries.append(" ".join(analysis["preferences"]) + " 음료 추천")
        return self.retriever.multi_search(queries)

    # ---------- 3. 도구 실행 ----------
    def _run_tool(self, name: str, args: dict) -> dict:
        if name == "get_menu_item":
            item = self.menu.find(args["menu_name"])
            if not item:
                return {"ok": False, "error": f"'{args['menu_name']}'은(는) 메뉴에 없습니다."}
            return {"ok": True, "info": item_document(self.menu, item).text}
        if name == "add_to_cart":
            return self.cart.add(args["menu_name"], args.get("quantity", 1), args.get("size"),
                                 args.get("temperature"), args.get("options"))
        if name == "update_cart_item":
            return self.cart.update_quantity(args["line_no"], args["quantity"])
        if name == "remove_from_cart":
            return self.cart.remove(args["line_no"])
        if name == "clear_cart":
            return self.cart.clear()
        if name == "checkout":
            return self.cart.checkout(args["dine_option"], args["payment_method"])
        return {"ok": False, "error": f"unknown tool {name}"}

    # ---------- 전체 파이프라인 ----------
    def chat(self, user_msg: str) -> str:
        trace = TurnTrace()
        analysis = self.analyze(user_msg)
        trace.analysis = analysis
        hits = self.retrieve(analysis, user_msg)
        trace.retrieved = [(d.id, round(s, 3)) for d, s in hits]

        docs_text = "\n\n".join(f"<doc id=\"{d.id}\">\n{d.text}\n</doc>" for d, _ in hits) or "(검색 결과 없음)"
        context = CONTEXT_TEMPLATE.format(
            standalone_query=analysis["standalone_query"],
            intents=", ".join(analysis["intents"]) or "-",
            preferences=", ".join(analysis["preferences"]) or "-",
            off_topic=analysis["off_topic"],
            documents=docs_text,
            cart=self.cart.as_text(),
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.history[-self.max_history_turns * 2:],
            {"role": "system", "content": context},
            {"role": "user", "content": user_msg},
        ]

        reply = ""
        for _ in range(6):  # tool 호출 루프 (최대 6회)
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0.3, messages=messages, tools=TOOLS,
            )
            msg = resp.choices[0].message
            if not msg.tool_calls:
                reply = msg.content or ""
                break
            messages.append({"role": "assistant", "content": msg.content,
                             "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                result = self._run_tool(tc.function.name, args)
                trace.tool_calls.append({"name": tc.function.name, "args": args, "ok": result.get("ok")})
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(result, ensure_ascii=False)})
        else:
            reply = "죄송해요, 처리 중 문제가 생겼어요. 다시 한 번 말씀해 주시겠어요?"

        self.history += [{"role": "user", "content": user_msg}, {"role": "assistant", "content": reply}]
        self.last_trace = trace
        return reply
