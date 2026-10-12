"""터미널 키오스크.  실행: python main.py [--debug]

명령어: /cart 장바구니 보기, /debug 디버그 토글, /reset 처음부터, /quit 종료
"""
import sys

from kiosk import create_agent
from kiosk.prompts import GREETING


def print_trace(agent):
    t = agent.last_trace
    print("  ┌─ [질의 분석]", t.analysis)
    print("  ├─ [검색 문서]", ", ".join(f"{i}({s})" for i, s in t.retrieved) or "-")
    print("  └─ [도구 호출]", t.tool_calls or "-")


def main():
    debug = "--debug" in sys.argv
    agent = create_agent()
    print(f"\n키오스크: {GREETING}\n")
    while True:
        try:
            user = input("손님: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user:
            continue
        if user == "/quit":
            break
        if user == "/cart":
            print(agent.cart.as_text(), "\n")
            continue
        if user == "/debug":
            debug = not debug
            print(f"(디버그 {'ON' if debug else 'OFF'})\n")
            continue
        if user == "/reset":
            agent.reset()
            print(f"키오스크: {GREETING}\n")
            continue
        reply = agent.chat(user)
        if debug:
            print_trace(agent)
        print(f"키오스크: {reply}\n")


if __name__ == "__main__":
    main()
