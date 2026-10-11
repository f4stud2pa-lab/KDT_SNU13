"""metrics.json → 보고서용 PNG 차트 3장.

사용법:
    .venv/bin/python scripts/make_charts.py runs/YYYY-MM-DD

출력 (같은 폴더의 charts/):
    stockdb_overview.png   시가총액 + 당일 등락률 (보고서 맨 위)
    stockdb_52w.png        52주 범위 안에서 현재가 위치
    stockdb_valuation.png  PBR + 일일 회전율(거래대금 ÷ 시가총액)

색 규칙: 국내 관례대로 상승 빨강(#e34948) / 하락 파랑(#2a78d6). 크기 비교는 파랑 단색.
"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

FONT = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"  # macOS 기본 한글 폰트
fm.fontManager.addfont(FONT)
plt.rcParams.update({
    "font.family": "AppleGothic", "axes.unicode_minus": False,  # AppleGothic 에 U+2212 글리프가 없음
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": "#52514e", "xtick.color": "#898781", "ytick.color": "#0b0b0b", "font.size": 11,
})
UP, DOWN, BLUE, LIGHT, GRID, INK, INK2, MUTED = ("#e34948", "#2a78d6", "#2a78d6", "#86b6ef",
                                                 "#e1e0d9", "#0b0b0b", "#52514e", "#898781")


def clean(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def main(run_dir):
    run = Path(run_dir)
    out = run / "charts"
    out.mkdir(exist_ok=True)
    ms = [m for m in json.load(open(run / "metrics.json", encoding="utf-8")) if m.get("listed")]
    unlisted = [m["종목명"] for m in json.load(open(run / "metrics.json", encoding="utf-8")) if not m.get("listed")]
    day = ms[0]["기준일"]
    note = f"자료: Stock-DB (네이버 증권)" + (f" · 비상장 제외: {', '.join(unlisted)}" if unlisted else "")

    ms.sort(key=lambda m: m["시가총액"])
    names = [m["alias"] for m in ms]
    h = max(4.0, 0.55 * len(ms) + 0.8)

    # 1. 개요: 시가총액 + 등락률
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, h), sharey=True, gridspec_kw={"width_ratios": [1.3, 1]})
    cap = [m["시가총액"] / 1e12 for m in ms]
    a1.barh(names, cap, color=BLUE, height=0.62)
    for i, v in enumerate(cap):
        a1.text(v + max(cap) * 0.01, i, f"{v:.1f}조", va="center", color=INK2, fontsize=10)
    a1.set_xlim(0, max(cap) * 1.15)
    a1.set_title("시가총액 (조원)", loc="left", fontsize=13, color=INK)
    clean(a1)
    chg = [m["등락률(%)"] for m in ms]
    span = max(abs(min(chg)), abs(max(chg)), 1)
    a2.barh(names, chg, color=[UP if v > 0 else DOWN for v in chg], height=0.62)
    a2.axvline(0, color="#c3c2b7", lw=1)
    for i, v in enumerate(chg):
        a2.text(v + (span * 0.04 if v >= 0 else -span * 0.04), i, f"{v:+.2f}%", va="center",
                ha="left" if v >= 0 else "right", color=INK2, fontsize=10)
    a2.set_xlim(-span * 1.35, span * 1.35)
    a2.set_title(f"{day[5:].replace('-', '/')} 등락률 (빨강 상승 · 파랑 하락)", loc="left", fontsize=13, color=INK)
    clean(a2)
    fig.suptitle(f"관심 종목 {len(ms)}개 한눈에 보기 ({day} 종가)", x=0.01, ha="left", fontsize=15)
    fig.text(0.01, 0.01, note, color=MUTED, fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(out / "stockdb_overview.png", dpi=160)
    plt.close(fig)

    # 2. 52주 위치
    ms2 = sorted([m for m in ms if m["52주 위치(%)"] is not None], key=lambda m: m["52주 위치(%)"])
    fig, ax = plt.subplots(figsize=(12, h))
    for i, m in enumerate(ms2):
        p = m["52주 위치(%)"]
        ax.plot([0, 100], [i, i], color=GRID, lw=6, solid_capstyle="round", zorder=1)
        ax.plot([0, p], [i, i], color=LIGHT, lw=6, solid_capstyle="round", zorder=2)
        ax.scatter([p], [i], s=90, color=BLUE, edgecolor="#fcfcfb", linewidth=2, zorder=3)
        ax.text(103, i, f"{p:.0f}%  ·  고점 대비 {m['고점 대비(%)']:+.0f}%", va="center", color=INK2, fontsize=10)
    ax.set_yticks(range(len(ms2)))
    ax.set_yticklabels([m["alias"] for m in ms2])
    ax.set_xlim(-2, 140)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["52주 최저", "25%", "50%", "75%", "52주 최고"])
    clean(ax)
    ax.grid(False)
    ax.set_title("52주 가격 범위 안에서 현재가 위치", loc="left", fontsize=14)
    fig.text(0.01, 0.01, "위치 = (현재가 - 52주 최저) ÷ (52주 최고 - 52주 최저). " + note, color=MUTED, fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "stockdb_52w.png", dpi=160)
    plt.close(fig)

    # 3. PBR + 회전율
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, h), sharey=True)
    pbr = [m["PBR"] or 0 for m in ms]
    to = [m["회전율(%)"] or 0 for m in ms]
    a1.barh(names, pbr, color=BLUE, height=0.62)
    for i, v in enumerate(pbr):
        a1.text(v + max(pbr) * 0.02, i, f"{v:.2f}배", va="center", color=INK2, fontsize=10)
    a1.axvline(1, color=MUTED, lw=1, ls="--", zorder=0)
    a1.set_xlim(0, max(pbr) * 1.2)
    a1.set_title("PBR (배, 점선 = 1배)", loc="left", fontsize=13)
    clean(a1)
    a2.barh(names, to, color=BLUE, height=0.62)
    for i, v in enumerate(to):
        a2.text(v + max(to) * 0.02, i, f"{v:.2f}%", va="center", color=INK2, fontsize=10)
    a2.set_xlim(0, max(to) * 1.2)
    a2.set_title("거래대금 ÷ 시가총액 (일일 회전율, %)", loc="left", fontsize=13)
    clean(a2)
    fig.suptitle("밸류에이션과 거래 열기", x=0.01, ha="left", fontsize=15)
    fig.text(0.01, 0.01, note + ", 거래대금은 KRX+NXT 통합", color=MUTED, fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    fig.savefig(out / "stockdb_valuation.png", dpi=160)
    plt.close(fig)

    for p in sorted(out.glob("*.png")):
        print(p)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("사용법: .venv/bin/python scripts/make_charts.py runs/YYYY-MM-DD")
    main(sys.argv[1])
