"""메뉴 데이터 로딩, 메뉴 검색, 가격 계산, 옵션 검증.

가격은 LLM이 아니라 항상 이 모듈이 계산한다 (환각 방지를 위한 single source of truth).
"""
import json
from pathlib import Path


def _norm(text: str) -> str:
    return "".join(text.lower().split())


class Menu:
    def __init__(self, path: Path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.store = data["store"]
        self.categories = data["categories"]
        self.options = data["options"]
        self.items = {item["id"]: item for item in data["items"]}

    # ---------- 조회 ----------
    def find(self, query: str):
        """id, 한글명, 영문명, 별칭으로 메뉴를 찾는다. 정확 일치 → 부분 일치 순."""
        q = _norm(query)
        for item in self.items.values():
            names = [item["id"], item["name"], item["en"], *item.get("aliases", [])]
            if q in (_norm(n) for n in names):
                return item
        candidates = []
        for item in self.items.values():
            for n in [item["name"], *item.get("aliases", [])]:
                if _norm(n) in q or q in _norm(n):
                    candidates.append((len(_norm(n)), item))
        if candidates:
            return max(candidates, key=lambda c: c[0])[1]
        return None

    def names_in_text(self, text: str):
        """문장 안에 언급된 메뉴들을 반환 (키워드 검색 보강용)."""
        t = _norm(text)
        found = []
        for item in self.items.values():
            for n in [item["name"], *item.get("aliases", [])]:
                if len(_norm(n)) >= 2 and _norm(n) in t:
                    found.append(item)
                    break
        return found

    def option_name(self, opt_id: str, choice: str | None = None) -> str:
        opt = self.options[opt_id]
        if choice is None:
            return opt["name"]
        return opt["choices"][choice]["name"]

    # ---------- 가격 ----------
    def price(self, item: dict, size: str | None = None, options: dict | None = None) -> tuple[int, list[str]]:
        """(단가, 가격 내역) 반환."""
        options = options or {}
        total = item["base_price"]
        breakdown = [f"{item['name']} 기본가 {total:,}원"]
        if size and item["sizes"]:
            p = self.options["size"]["choices"][size]["price"]
            if p:
                total += p
                breakdown.append(f"{self.option_name('size', size)} +{p:,}원")
        for opt_id, value in options.items():
            opt = self.options[opt_id]
            if opt["type"] == "count" and value:
                p = opt["price"] * int(value)
                total += p
                breakdown.append(f"{opt['name']} {value}회 +{p:,}원")
            elif opt["type"] == "bool" and value:
                if opt["price"]:
                    total += opt["price"]
                    breakdown.append(f"{opt['name']} +{opt['price']:,}원")
            elif opt["type"] == "single" and value:
                p = opt["choices"][value]["price"]
                if p:
                    total += p
                    breakdown.append(f"{opt['choices'][value]['name']} +{p:,}원")
            elif opt["type"] == "multi" and value:
                for v in value:
                    p = opt["choices"][v]["price"]
                    total += p
                    breakdown.append(f"{opt['choices'][v]['name']} +{p:,}원")
        return total, breakdown

    # ---------- 검증 ----------
    def validate(self, item: dict, size: str | None, temperature: str | None, options: dict) -> list[str]:
        """주문 가능 여부를 검사하고, 문제가 있으면 사용자에게 보여줄 오류 메시지 목록을 반환."""
        errors = []
        if not item.get("available", True):
            errors.append(f"{item['name']}: {item.get('unavailable_reason', '현재 품절입니다.')}")
        if item["sizes"]:
            if size and size not in item["sizes"]:
                allowed = ", ".join(self.option_name("size", s) for s in item["sizes"])
                errors.append(f"{item['name']}은(는) {allowed} 사이즈만 가능합니다.")
        elif size and size != "tall":
            errors.append(f"{item['name']}은(는) 단일 사이즈 메뉴입니다.")
        if item["temperatures"]:
            if temperature and temperature not in item["temperatures"]:
                allowed = "/".join(t.upper() for t in item["temperatures"])
                errors.append(f"{item['name']}은(는) {allowed}로만 제공됩니다.")
        elif temperature:
            errors.append(f"{item['name']}은(는) 온도 선택이 없는 메뉴입니다.")
        for opt_id, value in options.items():
            if opt_id not in self.options:
                errors.append(f"알 수 없는 옵션입니다: {opt_id}")
                continue
            if opt_id not in item["options"]:
                errors.append(f"{item['name']}에는 '{self.options[opt_id]['name']}' 옵션을 선택할 수 없습니다.")
                continue
            opt = self.options[opt_id]
            if opt["type"] == "count" and not (0 <= int(value) <= opt["max"]):
                errors.append(f"{opt['name']}은(는) 최대 {opt['max']}회까지 가능합니다.")
            if opt["type"] == "single" and value not in opt["choices"]:
                errors.append(f"{opt['name']}에 '{value}' 선택지는 없습니다.")
            if opt["type"] == "multi" and any(v not in opt["choices"] for v in value):
                errors.append(f"{opt['name']}에 없는 선택지가 포함되어 있습니다.")
        if options.get("ice_amount") and temperature == "hot":
            errors.append("얼음 양 조절은 ICE 음료에만 가능합니다.")
        return errors
