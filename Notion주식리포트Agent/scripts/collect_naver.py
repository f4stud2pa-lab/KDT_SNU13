"""네이버 증권에서 관심 종목 시세를 수집해 Stock-DB(Notion) 행 형식으로 저장한다.

사용법:
    .venv/bin/python scripts/collect_naver.py [--watchlist scripts/watchlist.json] [--out runs/YYYY-MM-DD]

출력 (--out 폴더):
    raw/basic_{code}.json, raw/integ_{code}.json, raw/krx_{code}.json   원본 응답
    rows.json      notion-create-pages 의 pages[].properties 로 그대로 넣을 값 목록
    metrics.json   보고서·차트용 파생 지표 (52주 위치, 고점 대비, 회전율 등)
    checks.md      KRX 단독 시세와의 차이, 결측값 등 검증 메모

stock.naver.com 페이지는 WebFetch 로 열리지 않는다. 같은 데이터를 주는 공개 API 를 curl 로 부른다.
"""
import argparse, json, re, subprocess, sys
from datetime import date, timedelta
from pathlib import Path

UA = "Mozilla/5.0"
MARKET = {"KOSPI": "코스피", "KOSDAQ": "코스닥", "KONEX": "코넥스"}


def get(url):
    out = subprocess.run(["curl", "-sL", "--max-time", "20", "-A", UA, url],
                         capture_output=True, text=True, check=True).stdout
    if not out.strip():
        raise RuntimeError(f"빈 응답: {url}")
    return out


def num(s):
    """'1,234' '18.25배' '25.93%' '458원' → float. 'N/A'·빈 값 → None."""
    if s is None:
        return None
    s = str(s).replace(",", "").replace("배", "").replace("%", "").replace("원", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def kwon(s):
    """'45조 6,920억' '7,240억' → 원 단위 float (억 미만 반올림된 값)."""
    if not s or s == "N/A":
        return None
    s = s.replace(",", "").replace(" ", "")
    total = 0.0
    if m := re.search(r"([\d.]+)조", s):
        total += float(m.group(1)) * 1e12
    if m := re.search(r"([\d.]+)억", s):
        total += float(m.group(1)) * 1e8
    return total or None


def intify(d):
    return {k: (int(v) if isinstance(v, float) and v.is_integer() else v) for k, v in d.items()}


def krx_daily(code, end):
    """KRX 단독 일별 시세 1년치: [(yyyymmdd, 시가, 고가, 저가, 종가, 거래량, 외국인소진율), ...]"""
    start = (end - timedelta(days=372)).strftime("%Y%m%d")
    txt = get(f"https://api.finance.naver.com/siseJson.naver?symbol={code}&requestType=1"
              f"&startTime={start}&endTime={end.strftime('%Y%m%d')}&timeframe=day")
    rows = re.findall(r'\["(\d{8})",\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\]', txt)
    return [(r[0], *map(float, r[1:])) for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watchlist", default="scripts/watchlist.json")
    ap.add_argument("--out", default=f"runs/{date.today().isoformat()}")
    a = ap.parse_args()

    out = Path(a.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    stocks = json.load(open(a.watchlist, encoding="utf-8"))["stocks"]
    rows, metrics, checks = [], [], []

    for s in stocks:
        if not s.get("code"):
            rows.append({"종목명": s["name"], "메모": f"{s.get('unlisted_note', '비상장')} 확인일 {date.today().isoformat()}"})
            metrics.append({"종목명": s["name"], "alias": s.get("alias", s["name"]), "group": s["group"], "listed": False})
            checks.append(f"- {s['name']}: 비상장 → 시세 없음 (메모 행만 생성)")
            continue

        c = s["code"]
        basic_txt = get(f"https://m.stock.naver.com/api/stock/{c}/basic")
        integ_txt = get(f"https://m.stock.naver.com/api/stock/{c}/integration")
        (out / "raw" / f"basic_{c}.json").write_text(basic_txt, encoding="utf-8")
        (out / "raw" / f"integ_{c}.json").write_text(integ_txt, encoding="utf-8")
        b, g = json.loads(basic_txt), json.loads(integ_txt)
        ti = {x["code"]: x["value"] for x in g["totalInfos"]}
        o = b.get("overMarketPriceInfo") or {}
        trade_day = b["localTradedAt"][:10]

        if b["stockName"] != s["name"]:
            checks.append(f"- {s['name']}({c}): 네이버 종목명은 '{b['stockName']}' — watchlist 이름으로 저장")

        memo = (f"{s.get('alias', '') + ' · ' if s.get('alias') else ''}전일 {ti.get('lastClosePrice')} · "
                f"추정PER {ti.get('cnsPer', 'N/A')} · EPS {ti.get('eps')} · 대금 {ti.get('accumulatedTradingValue')} · "
                f"시총 {ti.get('marketValue')} · 출처: 네이버 증권(거래량·대금은 KRX+NXT 통합)")
        if num(ti.get("per")) is None:
            memo = memo.replace("추정PER", "PER N/A(적자) · 추정PER", 1)

        row = {
            "종목명": s["name"], "종목코드": c,
            "시장": MARKET.get(b.get("stockExchangeName"), b.get("stockExchangeName")),
            "date:기준일:start": trade_day, "date:기준일:is_datetime": 0,
            "현재가": num(b["closePrice"]), "전일대비": num(b["compareToPreviousClosePrice"]),
            "등락률(%)": num(b["fluctuationsRatio"]),
            "등락구분": (b.get("compareToPreviousPrice") or {}).get("text"),
            "시가": num(ti.get("openPrice")), "고가": num(ti.get("highPrice")), "저가": num(ti.get("lowPrice")),
            "거래량": num(ti.get("accumulatedTradingVolume")),
            "거래대금": kwon(ti.get("accumulatedTradingValue")), "시가총액": kwon(ti.get("marketValue")),
            "52주 최고": num(ti.get("highPriceOf52Weeks")), "52주 최저": num(ti.get("lowPriceOf52Weeks")),
            "외국인 소진율(%)": num(ti.get("foreignRate")),
            "PER": num(ti.get("per")), "PBR": num(ti.get("pbr")),
            "시간외 가격": num(o.get("overPrice")),
            "장 상태": "장마감" if b.get("marketStatus") == "CLOSE" else "장중",
            "상세 URL": b.get("newPcUrl"),
        }
        if (b.get("tradeStopType") or {}).get("name") not in (None, "TRADING"):
            row["장 상태"] = "거래정지"

        # 등락구분 옵션 이름 맞추기 (네이버는 상한/하한도 내려줌)
        row["등락구분"] = {"상한": "상한가", "하한": "하한가"}.get(row["등락구분"], row["등락구분"])

        # KRX 단독 시세와 교차 검증
        try:
            krx = krx_daily(c, date.fromisoformat(trade_day))
            (out / "raw" / f"krx_{c}.json").write_text(json.dumps(krx), encoding="utf-8")
            today = [r for r in krx if r[0] == trade_day.replace("-", "")]
            prev = [r for r in krx if r[0] < trade_day.replace("-", "")]
            if today and prev:
                krx_chg = today[0][4] - prev[-1][4]
                krx_hi, krx_lo = max(r[2] for r in krx), min(r[3] for r in krx)
                diffs = []
                if row["전일대비"] is not None and abs(krx_chg - row["전일대비"]) > 0.5:
                    diffs.append(f"KRX 전일대비 {krx_chg:+,.0f}(전일종가 {prev[-1][4]:,.0f})")
                if row["52주 최고"] and abs(krx_hi - row["52주 최고"]) > 0.5:
                    diffs.append(f"KRX 52주 장중최고 {krx_hi:,.0f}")
                if row["52주 최저"] and abs(krx_lo - row["52주 최저"]) > 0.5:
                    diffs.append(f"KRX 52주 장중최저 {krx_lo:,.0f}")
                if diffs:
                    memo += ". 참고(KRX 단독 기준): " + ", ".join(diffs)
                    checks.append(f"- {s['name']}: 네이버 통합값과 KRX 단독값 차이 → " + ", ".join(diffs))
        except Exception as e:  # 교차검증 실패는 수집을 막지 않는다
            checks.append(f"- {s['name']}: KRX 교차검증 실패 ({e})")

        row["메모"] = memo
        missing = [k for k, v in row.items() if v is None and k not in ("PER", "시간외 가격")]
        if missing:
            checks.append(f"- {s['name']}: 결측 {missing}")
        row = intify({k: v for k, v in row.items() if v is not None})
        rows.append(row)

        hi, lo, px = row.get("52주 최고"), row.get("52주 최저"), row["현재가"]
        metrics.append({
            "종목명": s["name"], "alias": s.get("alias", s["name"]), "group": s["group"], "listed": True,
            **{k: row.get(k) for k in ("시장", "현재가", "전일대비", "등락률(%)", "시가총액", "거래대금",
                                       "52주 최고", "52주 최저", "PER", "PBR", "외국인 소진율(%)", "저가")},
            "기준일": trade_day,
            "52주 위치(%)": round((px - lo) / (hi - lo) * 100, 1) if hi and lo and hi > lo else None,
            "고점 대비(%)": round((px / hi - 1) * 100, 1) if hi else None,
            "저점 대비(%)": round((px / lo - 1) * 100, 1) if lo else None,
            "회전율(%)": round(row["거래대금"] / row["시가총액"] * 100, 2) if row.get("거래대금") and row.get("시가총액") else None,
            "EPS": ti.get("eps"), "추정PER": ti.get("cnsPer"),
        })

    json.dump(rows, open(out / "rows.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(metrics, open(out / "metrics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    (out / "checks.md").write_text("# 수집 검증 메모\n\n" + ("\n".join(checks) or "- 특이사항 없음") + "\n", encoding="utf-8")

    days = sorted({m["기준일"] for m in metrics if m.get("listed")})
    print(f"수집 완료: {len(rows)}행 → {out}/rows.json  (기준일 {', '.join(days)})")
    print((out / "checks.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    sys.exit(main())
