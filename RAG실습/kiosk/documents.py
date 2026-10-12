"""menu.json / store_info.json → RAG 검색용 문서(chunk) 생성.

문서 구성 전략
- 메뉴 문서: 메뉴 1개 = 문서 1개. 설명, 사이즈별 가격표, 온도, 맛 프로필, 옵션(가능/불가), 알레르기, 페어링을 모두 담아
  "아메리카노 중 사이즈 얼마?" 같은 질문이 문서 1개만으로 답변되도록 한다.
- 옵션 문서: 옵션 그룹 1개 = 문서 1개 (어떤 메뉴에 적용 가능한지 역색인 포함).
- 카테고리 문서: 카테고리별 메뉴 목록 + 가격 요약 ("디저트 뭐 있어요?" 대응).
- 추천 문서: 선호도별 추천 가이드 + 맛 프로필 순위 (달콤한/상큼한/카페인 없는 …).
- 매장 FAQ 문서: 질문-답변 1쌍 = 문서 1개.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from .menu import Menu


@dataclass
class Document:
    id: str
    title: str
    text: str
    metadata: dict = field(default_factory=dict)


def _price_line(menu: Menu, item: dict) -> str:
    if not item["sizes"]:
        return f"{item['base_price']:,}원 (단일 사이즈)"
    parts = []
    for s in item["sizes"]:
        size = menu.options["size"]["choices"][s]
        price, _ = menu.price(item, s)
        parts.append(f"{size['name']} {size['ml']}ml {price:,}원")
    return " / ".join(parts)


def _option_line(menu: Menu, opt_id: str) -> str:
    opt = menu.options[opt_id]
    if opt["type"] == "count":
        return f"{opt['name']}(+{opt['price']:,}원/회, 최대 {opt['max']}회)"
    if opt["type"] == "bool":
        return f"{opt['name']}({'+' + format(opt['price'], ',') + '원' if opt['price'] else '무료'})"
    choices = ", ".join(
        f"{c['name']}{'(+' + format(c['price'], ',') + '원)' if c['price'] else ''}"
        for c in opt["choices"].values()
    )
    return f"{opt['name']}: {choices}"


def item_document(menu: Menu, item: dict) -> Document:
    is_drink = item["category"] not in ("dessert", "bakery")
    cat = menu.categories[item["category"]]
    status = "판매 중" if item.get("available", True) else f"품절 - {item.get('unavailable_reason', '')}"
    lines = [
        f"[메뉴] {item['name']} ({item['en']})",
        f"분류: {cat} | 판매 상태: {status}",
    ]
    if item.get("aliases"):
        lines.append(f"다른 이름: {', '.join(item['aliases'])}")
    lines.append(f"설명: {item['description']}")
    lines.append(f"가격: {_price_line(menu, item)}")
    if item["sizes"]:
        lines.append("사이즈 안내: 작은 사이즈=Tall, 중간(중) 사이즈=Grande, 큰 사이즈=Venti")
    if is_drink:
        temps = ", ".join(menu.option_name("temperature", t) for t in item["temperatures"])
        only = " 전용" if len(item["temperatures"]) == 1 else ""
        lines.append(f"온도: {temps}{only}")

    p = item["profile"]
    prof = []
    if "coffee_intensity" in p and p["coffee_intensity"]:
        prof.append(f"커피 진하기 {p['coffee_intensity']}/5")
    if "sweetness" in p:
        prof.append(f"단맛 {p['sweetness']}/5")
    if "caffeine_mg" in p:
        prof.append(f"카페인 {p['caffeine_mg']}mg" + (" (Tall 기준)" if item["sizes"] else ""))
    prof.append(f"칼로리 {p['kcal']}kcal" + (" (Tall 기준)" if item["sizes"] else ""))
    lines.append("맛/영양 정보: " + ", ".join(prof))
    if item.get("intensity_note"):
        lines.append(f"맛 특징: {item['intensity_note']}")
    lines.append(f"알레르기 유발 성분: {', '.join(item['allergens']) if item['allergens'] else '없음'}")

    if item["options"]:
        lines.append("선택 가능 옵션: " + " / ".join(_option_line(menu, o) for o in item["options"]))
    if is_drink:
        not_allowed = [menu.options[o]["name"] for o in
                       ("extra_shot", "syrup", "milk", "whipped_cream", "decaf", "sweetness")
                       if o not in item["options"]]
        if not_allowed:
            lines.append("선택 불가 옵션: " + ", ".join(not_allowed))
    lines.append(f"특징 태그: {', '.join(item['tags'])}")
    if item.get("pairings"):
        pair_names = [menu.items[i]["name"] for i in item["pairings"] if i in menu.items]
        lines.append(f"함께 먹기 좋은 메뉴: {', '.join(pair_names)}")
    return Document(
        id=f"item:{item['id']}", title=item["name"], text="\n".join(lines),
        metadata={"type": "menu", "item_id": item["id"], "category": item["category"]},
    )


def option_documents(menu: Menu) -> list[Document]:
    docs = []
    for opt_id, opt in menu.options.items():
        applicable = [i["name"] for i in menu.items.values()
                      if opt_id in i["options"]
                      or (opt_id == "size" and i["sizes"])
                      or (opt_id == "temperature" and len(i["temperatures"]) > 1)]
        lines = [f"[옵션] {opt['name']}", _option_line(menu, opt_id)]
        if opt_id == "size":
            for c in opt["choices"].values():
                lines.append(f"- {c['name']}: {c['ml']}ml, 기본가 대비 +{c['price']:,}원 (다른 표현: {', '.join(c['aliases'])})")
        if opt.get("description"):
            lines.append(opt["description"])
        if opt.get("applies_to"):
            lines.append(opt["applies_to"])
        lines.append(f"적용 가능 메뉴: {', '.join(applicable)}")
        docs.append(Document(id=f"option:{opt_id}", title=opt["name"], text="\n".join(lines),
                             metadata={"type": "option", "option_id": opt_id}))
    return docs


def category_documents(menu: Menu) -> list[Document]:
    docs = []
    for cat_id, cat_name in menu.categories.items():
        items = [i for i in menu.items.values() if i["category"] == cat_id]
        lines = [f"[카테고리] {cat_name} 메뉴 목록 ({len(items)}종)"]
        for i in items:
            sold = "" if i.get("available", True) else " (품절)"
            lines.append(f"- {i['name']}: {i['base_price']:,}원~{sold} | {i['description'][:40]}")
        docs.append(Document(id=f"category:{cat_id}", title=cat_name, text="\n".join(lines),
                             metadata={"type": "category", "category": cat_id}))
    return docs


def recommendation_documents(menu: Menu, store: dict) -> list[Document]:
    docs = []
    for i, rec in enumerate(store["recommendation_guide"]):
        docs.append(Document(
            id=f"rec:{i}", title=f"{rec['preference']} 추천",
            text=f"[추천 가이드] {rec['preference']}\n{rec['guide']}",
            metadata={"type": "recommendation"},
        ))
    drinks = [i for i in menu.items.values() if i["category"] not in ("dessert", "bakery") and i.get("available", True)]
    rankings = {
        "단맛이 강한 순": sorted(drinks, key=lambda i: -i["profile"]["sweetness"]),
        "커피 맛이 진한 순": sorted([d for d in drinks if d["profile"].get("coffee_intensity")],
                               key=lambda i: -i["profile"]["coffee_intensity"]),
        "카페인이 적은 순": sorted(drinks, key=lambda i: i["profile"]["caffeine_mg"]),
        "칼로리가 낮은 순": sorted(drinks, key=lambda i: i["profile"]["kcal"]),
    }
    for title, ranked in rankings.items():
        key = {"단맛이 강한 순": "sweetness", "커피 맛이 진한 순": "coffee_intensity",
               "카페인이 적은 순": "caffeine_mg", "칼로리가 낮은 순": "kcal"}[title]
        lines = [f"[음료 순위] {title}"] + [
            f"{n}. {d['name']} ({key}={d['profile'][key]})" for n, d in enumerate(ranked[:10], 1)
        ]
        docs.append(Document(id=f"rank:{key}", title=title, text="\n".join(lines),
                             metadata={"type": "recommendation"}))
    return docs


def faq_documents(store: dict) -> list[Document]:
    return [
        Document(id=f"faq:{i}", title=f["q"], text=f"[매장 안내] Q: {f['q']}\nA: {f['a']}",
                 metadata={"type": "faq"})
        for i, f in enumerate(store["faq"])
    ]


def build_documents(menu: Menu, store_path: Path) -> list[Document]:
    store = json.loads(Path(store_path).read_text(encoding="utf-8"))
    docs = [item_document(menu, item) for item in menu.items.values()]
    docs += option_documents(menu)
    docs += category_documents(menu)
    docs += recommendation_documents(menu, store)
    docs += faq_documents(store)
    return docs
