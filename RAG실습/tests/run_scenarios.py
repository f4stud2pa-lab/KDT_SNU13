"""HTI 기반 시나리오 테스트를 실제 LLM으로 실행하고 결과를 마크다운 리포트로 저장한다.

실행: python -m tests.run_scenarios            (전체)
     python -m tests.run_scenarios 4.1 7.1    (특정 HTI 번호만)
"""
import json
import sys
from pathlib import Path

from kiosk import create_agent

HERE = Path(__file__).parent


def main():
    scenarios = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))
    only = sys.argv[1:]
    if only:
        scenarios = [s for s in scenarios if s["hti"] in only]
    agent = create_agent()
    report, passed, checked = ["# 시나리오 테스트 결과\n"], 0, 0

    for s in scenarios:
        agent.reset()
        tools_used, transcript = [], []
        for turn in s["turns"]:
            reply = agent.chat(turn)
            tools_used += [t["name"] for t in agent.last_trace.tool_calls]
            transcript.append(f"- **손님**: {turn}\n- **키오스크**: {reply}\n"
                              f"  - 검색: `{[i for i, _ in agent.last_trace.retrieved]}`\n"
                              f"  - 도구: `{agent.last_trace.tool_calls}`")

        failures = []
        last_reply = reply
        for text in s.get("expect_contains", []):
            if text not in last_reply:
                failures.append(f"응답에 '{text}' 없음")
        if "expect_tool" in s and s["expect_tool"] not in tools_used:
            failures.append(f"도구 {s['expect_tool']} 미호출")
        if "expect_cart_total" in s:
            total = agent.cart.completed_order["total_price"] if agent.cart.completed_order else agent.cart.total
            if total != s["expect_cart_total"]:
                failures.append(f"장바구니 합계 {total:,} ≠ 기대 {s['expect_cart_total']:,}")
        auto = any(k in s for k in ("expect_contains", "expect_tool", "expect_cart_total"))
        if auto:
            checked += 1
            passed += not failures
        status = "⚪ 수동 확인" if not auto else ("✅ PASS" if not failures else "❌ FAIL: " + "; ".join(failures))
        print(f"[{s['hti']}] {s['name']}: {status}")
        report.append(f"## [{s['hti']}] {s['name']} — {status}\n기대 동작: {s['expect']}\n\n" + "\n".join(transcript) + "\n")

    report.insert(1, f"자동 검증 {passed}/{checked} 통과\n")
    out = HERE / "scenario_report.md"
    out.write_text("\n".join(report), encoding="utf-8")
    print(f"\n자동 검증 {passed}/{checked} 통과 → {out}")


if __name__ == "__main__":
    main()
