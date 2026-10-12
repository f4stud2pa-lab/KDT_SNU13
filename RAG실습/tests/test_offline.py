"""API 키 없이 돌아가는 테스트: 가격 계산, 옵션 검증, 장바구니, 키워드 검색.  실행: python -m tests.test_offline"""
from kiosk import DATA
from kiosk.documents import build_documents
from kiosk.menu import Menu
from kiosk.order import Cart
from kiosk.retriever import HybridRetriever

menu = Menu(DATA / "menu.json")
docs = build_documents(menu, DATA / "store_info.json")


def test_price():
    assert menu.price(menu.find("아메리카노"), "grande")[0] == 5000
    assert menu.price(menu.find("바닐라라떼"), "tall", {"milk": "oat"})[0] == 6100
    assert menu.price(menu.find("카페라떼"), "venti", {"extra_shot": 2, "syrup": ["vanilla", "caramel"], "decaf": True})[0] == 8300


def test_find_alias():
    assert menu.find("아아")["id"] == "americano"
    assert menu.find("핫초코")["id"] == "choco_latte"
    assert menu.find("민트초코 프라푸치노") is None


def test_validate():
    assert menu.validate(menu.find("카푸치노"), "tall", "ice", {})
    assert menu.validate(menu.find("아메리카노"), "tall", "ice", {"milk": "oat"})
    assert menu.validate(menu.find("딸기 요거트 스무디"), "tall", "ice", {})
    assert not menu.validate(menu.find("카페라떼"), "grande", "ice", {"milk": "soy", "extra_shot": 1})


def test_cart():
    cart = Cart(menu)
    assert cart.add("카페라떼")["need_more_info"] == ["size", "temperature"]
    assert cart.add("콜드브루", 1, "tall")["ok"]  # ICE 전용 → 온도 자동
    assert cart.add("아메리카노", 2, "venti", "ice")["ok"]
    assert cart.add("치즈케이크")["ok"]
    assert cart.total == 5000 + 11000 + 6500
    cart.update_quantity(1, 3)
    cart.remove(3)
    assert cart.total == 15000 + 11000
    assert cart.checkout("takeout", "card")["ok"] and cart.total == 0


def test_retrieval_keyword_only():
    r = HybridRetriever(docs, menu, client=None)
    assert r.search("아메리카노 중 사이즈 얼마인가요?")[0][0].id == "item:americano"
    ids = [d.id for d, _ in r.multi_search(["아메리카노 진하기", "카푸치노 가격"])]
    assert "item:americano" in ids and "item:cappuccino" in ids
    assert any(d.id.startswith("faq") for d, _ in r.search("텀블러 할인", 3))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
    print(f"\n총 문서 수: {len(docs)}")
    print(docs[0].text)
