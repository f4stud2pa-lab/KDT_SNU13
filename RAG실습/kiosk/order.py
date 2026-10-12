"""장바구니 / 주문 관리. LLM은 function calling으로 이 클래스의 메서드만 호출할 수 있다."""
import random
from dataclasses import dataclass, field

from .menu import Menu


@dataclass
class CartLine:
    item_id: str
    name: str
    quantity: int
    size: str | None
    temperature: str | None
    options: dict
    unit_price: int

    def describe(self, menu: Menu) -> str:
        parts = []
        if self.temperature:
            parts.append(self.temperature.upper())
        if self.size:
            parts.append(menu.option_name("size", self.size))
        for opt_id, v in self.options.items():
            opt = menu.options[opt_id]
            if opt["type"] == "count" and v:
                parts.append(f"{opt['name']} {v}회")
            elif opt["type"] == "bool" and v:
                parts.append(opt["name"])
            elif opt["type"] == "single" and v and v != "normal" and v != "regular":
                parts.append(opt["choices"][v]["name"])
            elif opt["type"] == "multi" and v:
                parts += [opt["choices"][x]["name"] for x in v]
        detail = f" ({', '.join(parts)})" if parts else ""
        return f"{self.name}{detail} x{self.quantity} = {self.unit_price * self.quantity:,}원"


@dataclass
class Cart:
    menu: Menu
    lines: list[CartLine] = field(default_factory=list)
    completed_order: dict | None = None

    @property
    def total(self) -> int:
        return sum(l.unit_price * l.quantity for l in self.lines)

    def summary(self) -> dict:
        return {
            "items": [{"line_no": i + 1, "description": l.describe(self.menu)} for i, l in enumerate(self.lines)],
            "total_price": self.total,
            "total_text": f"{self.total:,}원",
        }

    def as_text(self) -> str:
        if not self.lines:
            return "(장바구니가 비어 있음)"
        rows = [f"{i + 1}. {l.describe(self.menu)}" for i, l in enumerate(self.lines)]
        return "\n".join(rows + [f"합계: {self.total:,}원"])

    # ---------- tool 함수들 ----------
    def add(self, menu_name: str, quantity: int = 1, size: str | None = None,
            temperature: str | None = None, options: dict | None = None) -> dict:
        item = self.menu.find(menu_name)
        if item is None:
            return {"ok": False, "error": f"'{menu_name}'은(는) 메뉴에 없습니다."}
        options = {k: v for k, v in (options or {}).items() if v not in (None, False, 0, [], "")}
        is_drink = bool(item["temperatures"])
        missing = []
        if item["sizes"] and size is None:
            missing.append("size")
        if is_drink and len(item["temperatures"]) > 1 and temperature is None:
            missing.append("temperature")
        if missing:
            return {"ok": False, "need_more_info": missing,
                    "error": f"{item['name']}의 {', '.join('사이즈' if m == 'size' else '온도(HOT/ICE)' for m in missing)}를 먼저 확인해야 합니다."}
        if is_drink and len(item["temperatures"]) == 1:
            temperature = temperature or item["temperatures"][0]
        if not item["sizes"]:
            size = None
        errors = self.menu.validate(item, size, temperature, options)
        if quantity < 1 or quantity > 20:
            errors.append("수량은 1~20개 사이로 주문할 수 있습니다.")
        if errors:
            return {"ok": False, "error": " ".join(errors)}
        unit, breakdown = self.menu.price(item, size, options)
        line = CartLine(item["id"], item["name"], quantity, size, temperature, options, unit)
        self.lines.append(line)
        return {"ok": True, "added": line.describe(self.menu), "price_breakdown": breakdown, "cart": self.summary()}

    def remove(self, line_no: int) -> dict:
        if not 1 <= line_no <= len(self.lines):
            return {"ok": False, "error": f"{line_no}번 항목이 없습니다.", "cart": self.summary()}
        removed = self.lines.pop(line_no - 1)
        return {"ok": True, "removed": removed.describe(self.menu), "cart": self.summary()}

    def update_quantity(self, line_no: int, quantity: int) -> dict:
        if not 1 <= line_no <= len(self.lines):
            return {"ok": False, "error": f"{line_no}번 항목이 없습니다.", "cart": self.summary()}
        if quantity == 0:
            return self.remove(line_no)
        if not 1 <= quantity <= 20:
            return {"ok": False, "error": "수량은 1~20개 사이로 주문할 수 있습니다."}
        self.lines[line_no - 1].quantity = quantity
        return {"ok": True, "cart": self.summary()}

    def clear(self) -> dict:
        self.lines.clear()
        return {"ok": True, "cart": self.summary()}

    def checkout(self, dine_option: str, payment_method: str) -> dict:
        if not self.lines:
            return {"ok": False, "error": "장바구니가 비어 있어 결제할 수 없습니다."}
        order = {
            "order_number": random.randint(100, 999),
            "items": self.summary()["items"],
            "total_price": self.total,
            "dine_option": {"dine_in": "매장", "takeout": "포장"}[dine_option],
            "payment_method": {"card": "신용/체크카드", "easy_pay": "간편결제", "gifticon": "기프티콘"}[payment_method],
        }
        self.completed_order = order
        self.lines = []
        return {"ok": True, "order": order}
