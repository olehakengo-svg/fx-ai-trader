"""v8.9 alpha_scan / session_pair 静的ブロック 10 件の再較正測定.

pre-reg: knowledge-base/wiki/decisions/alpha-scan-static-block-recalibration-prereg-2026-09-02.md

設計規律:
  - モジュールトップに副作用を置かない (os.environ / os.chdir / parse_args / Thread.start 禁止)
    — MEMORY: tools/*.py はスクリプトかつライブラリの二重存在
  - 勝敗は `outcome` 列のみ (`close_reason` 禁止)
  - LIVE = oanda_trade_id != ''。is_shadow==0 単独では判定しない
  - shadow と LIVE を混ぜた集計は作らない

使い方:
    python3 tools/alpha_scan_block_recalibration.py --fetch --cache /tmp/asb.json
    python3 tools/alpha_scan_block_recalibration.py --cache /tmp/asb.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://fx-ai-trader.onrender.com"

# pre-reg §2 で凍結した窓
WINDOW_FROM = "2026-04-15"
WINDOW_TO = "2026-09-01"
# 較正母体の抽出窓 (2026-04-14 の v8.9 較正が見ていた期間)
CALIB_FROM = "2026-04-08"
CALIB_TO = "2026-04-14"

BONFERRONI_M = 10
ALPHA = 0.05 / BONFERRONI_M
BOOTSTRAP_B = 10000
BOOTSTRAP_SEED = 20260902

# CLAUDE.md per-pair RT friction (pip)
FRICTION_RT = {
    "USD_JPY": 2.14, "EUR_USD": 2.00, "GBP_USD": 4.53,
    "EUR_JPY": 2.50, "EUR_GBP": 3.00, "XAU_USD": 217.5,
}
FRICTION_DEFAULT = 2.50  # 表に無いペア (AUD_JPY/GBP_JPY/NZD_* 等) の保守的既定

WEEKEND_GAP_FADE_ENTRY_TYPE = "weekend_gap_fade"
TREND_BULL_MR_EXEMPT = {
    "bb_rsi_reversion", "fib_reversal", "orb_trap",
    "gbp_deep_pullback", "vol_spike_mr",
}
# demo_trader._is_live_tier_exempt の実体 (ELITE_LIVE は空、PAIR_PROMOTED のみ)
LIVE_TIER_EXEMPT_CELLS = {
    ("bb_squeeze_breakout", "EUR_USD"),
    ("doji_breakout", "GBP_USD"), ("doji_breakout", "USD_JPY"),
    ("donchian_momentum_breakout", "NZD_JPY"),
    ("donchian_momentum_breakout", "NZD_USD"),
}


# ─────────────────────────── data ───────────────────────────
def fetch_trades(base_url: str, date_from: str, date_to: str,
                 page: int = 1000, max_pages: int = 200) -> list[dict]:
    """closed trades を offset ページングで全件取得."""
    out: list[dict] = []
    seen: set = set()
    for i in range(max_pages):
        url = (f"{base_url}/api/demo/trades?status=closed&limit={page}"
               f"&offset={i * page}&date_from={date_from}&date_to={date_to}")
        with urllib.request.urlopen(url, timeout=180) as fh:
            payload = json.loads(fh.read().decode())
        rows = payload.get("trades", [])
        if not rows:
            break
        fresh = 0
        for r in rows:
            key = r.get("id") or r.get("trade_id")
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
            fresh += 1
        sys.stderr.write(f"  page {i}: {len(rows)} rows ({fresh} new), total {len(out)}\n")
        if len(rows) < page:
            break
        if fresh == 0:
            break
    return out


def _utc_hour(row: dict):
    ts = row.get("entry_time")
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).hour


def _regime_type(row: dict):
    raw = row.get("regime")
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw.get("regime")
    try:
        return json.loads(raw).get("regime")
    except (ValueError, TypeError):
        return None


def is_live(row: dict) -> bool:
    return (row.get("oanda_trade_id") or "") != ""


def clean_rows(rows: list[dict]) -> list[dict]:
    """pre-reg §2 の除外を適用."""
    out = []
    for r in rows:
        if r.get("dedup_violation") == 1:
            continue
        if (r.get("instrument") or "").startswith("XAU"):
            continue
        if r.get("outcome") not in ("WIN", "LOSS"):
            continue
        if r.get("pnl_pips") is None:
            continue
        out.append(r)
    return out


# ─────────────────────── block conditions ───────────────────────
def _b1(r):
    # NOTE: hour==0 は falsy。`_utc_hour(r) or 99` と書くと東京時間の
    # 0 時台が丸ごと条件から漏れる (実際に混入していた欠陥)。None と 0 を分ける。
    h = _utc_hour(r)
    return r.get("instrument") == "EUR_USD" and h is not None and h < 7
def _b2(r):
    h = _utc_hour(r)
    return (r.get("instrument") == "EUR_USD" and h is not None and h >= 17
            and r.get("entry_type") != WEEKEND_GAP_FADE_ENTRY_TYPE)
def _b3(r):  return r.get("instrument") == "EUR_USD" and r.get("direction") == "SELL"
def _b4(r):  return (_regime_type(r) == "RANGE" and r.get("direction") == "SELL"
                     and (r.get("confidence") or 0) < 65)
def _b5(r):  return (_regime_type(r) == "TREND_BULL" and r.get("direction") == "BUY"
                     and r.get("entry_type") not in TREND_BULL_MR_EXEMPT
                     and (r.get("confidence") or 0) < 65)
def _b6(r):  return _utc_hour(r) == 11 and r.get("instrument") == "EUR_USD"
def _b7(r):  return _utc_hour(r) == 13 and r.get("instrument") == "USD_JPY"
def _b8(r):
    h = _utc_hour(r)
    return r.get("instrument") == "USD_JPY" and h is not None and 16 <= h <= 20
def _b9(r):  return (r.get("direction") == "BUY" and _regime_type(r) == "TREND_BEAR"
                     and (r.get("confidence") or 0) < 70)
def _b10(r): return r.get("instrument") == "EUR_USD" and _utc_hour(r) in (7, 8)

BLOCKS = [
    ("B1",  "session_pair(EUR_USD_Tokyo)",   _b1,  None, None),
    ("B2",  "session_pair(EUR_USD_Late_NY)", _b2,  None, None),
    ("B3",  "alpha_scan(EUR_USD_SELL)",      _b3,  43,   -2.714),
    ("B4",  "alpha_scan(RANGE_SELL)",        _b4,  89,   -1.636),
    ("B5",  "alpha_scan(TREND_BULL_BUY)",    _b5,  70,   -0.776),
    ("B6",  "alpha_scan(H11_EUR_USD)",       _b6,  9,    -4.489),
    ("B7",  "alpha_scan(H13_USD_JPY)",       _b7,  14,   -2.486),
    ("B8",  "alpha_scan(H16-20_USD_JPY)",    _b8,  27,   -2.400),
    ("B9",  "alpha_scan(BUY_TREND_BEAR)",    _b9,  19,   -1.670),
    ("B10", "alpha_scan(H7-8_EUR_USD)",      _b10, 14,   -2.380),
]


# ─────────────────────────── stats ───────────────────────────
def bootstrap_ci(vals: list[float], b: int = BOOTSTRAP_B,
                 seed: int = BOOTSTRAP_SEED, lo: float = 2.5, hi: float = 97.5):
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(vals)
    means = []
    for _ in range(b):
        means.append(sum(vals[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return (means[int(lo / 100 * b)], means[min(b - 1, int(hi / 100 * b))])


def one_sided_p_negative(vals: list[float]) -> float:
    """H0: mean >= 0 に対する「mean < 0」の片側 t 検定 p."""
    n = len(vals)
    if n < 2:
        return 1.0
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    if var <= 0:
        return 0.0 if mean < 0 else 1.0
    t = mean / math.sqrt(var / n)
    # normal approx (n>=30 が判定条件なので妥当)、下側確率
    return 0.5 * math.erfc(-t / math.sqrt(2))


def friction(row: dict) -> float:
    return FRICTION_RT.get(row.get("instrument"), FRICTION_DEFAULT)


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0}
    gross = [float(r["pnl_pips"]) for r in rows]
    net = [float(r["pnl_pips"]) - friction(r) for r in rows]
    n = len(rows)
    wins = sum(1 for r in rows if r.get("outcome") == "WIN")
    ci = bootstrap_ci(net)
    return {
        "n": n,
        "wr": wins / n,
        "ev_gross": sum(gross) / n,
        "ev_net": sum(net) / n,
        "ci_net_lo": ci[0], "ci_net_hi": ci[1],
        "p_neg_net": one_sided_p_negative(net),
    }


def verdict_for(res: dict, overlap: float) -> str:
    if res.get("n", 0) < 30:
        return "UNDERPOWERED"
    if res["ev_net"] < 0 and res["p_neg_net"] < ALPHA:
        return "PREMISE-INTACT"
    if overlap < 0.20:
        return "PREMISE-STALE"
    return "PREMISE-WEAK"


# ─────────────────────────── main ───────────────────────────
def build_report(window_rows: list[dict], calib_rows: list[dict]) -> dict:
    calib_types = {r.get("entry_type") for r in calib_rows if r.get("entry_type")}
    shadow = [r for r in window_rows if not is_live(r)]
    live = [r for r in window_rows if is_live(r)]

    # P0 — 再構成妥当性
    p0 = []
    for bid, name, fn, _, _ in BLOCKS:
        hits = [r for r in live if fn(r)]
        non_exempt = [r for r in hits
                      if (r.get("entry_type"), r.get("instrument"))
                      not in LIVE_TIER_EXEMPT_CELLS]
        p0.append({"block": bid, "name": name, "live_hits": len(hits),
                   "live_hits_non_exempt": len(non_exempt),
                   "non_exempt_cells": sorted({
                       f"{r.get('entry_type')}x{r.get('instrument')}"
                       for r in non_exempt})[:8]})

    # P1/P2
    out = []
    for bid, name, fn, cal_n, cal_ev in BLOCKS:
        hit = [r for r in shadow if fn(r)]
        overlap = (sum(1 for r in hit if r.get("entry_type") in calib_types) / len(hit)
                   if hit else float("nan"))
        res = summarize(hit)
        out.append({
            "block": bid, "name": name,
            "calib_n": cal_n, "calib_ev": cal_ev,
            "overlap": overlap,
            "verdict": verdict_for(res, overlap if overlap == overlap else 1.0),
            **res,
        })
    return {"p0": p0, "blocks": out,
            "n_window": len(window_rows), "n_shadow": len(shadow),
            "n_live": len(live), "n_calib_types": len(calib_types),
            "calib_types": sorted(calib_types)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--cache", default="/tmp/alpha_scan_blocks.json")
    ap.add_argument("--base-url", default=BASE_URL)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args(argv)

    if args.fetch:
        sys.stderr.write(f"fetching window {WINDOW_FROM}..{WINDOW_TO}\n")
        win = fetch_trades(args.base_url, WINDOW_FROM, WINDOW_TO)
        sys.stderr.write(f"fetching calib {CALIB_FROM}..{CALIB_TO}\n")
        cal = fetch_trades(args.base_url, CALIB_FROM, CALIB_TO)
        with open(args.cache, "w") as fh:
            json.dump({"window": win, "calib": cal}, fh)
        sys.stderr.write(f"cached {len(win)} window / {len(cal)} calib rows\n")

    with open(args.cache) as fh:
        blob = json.load(fh)
    win = clean_rows(blob["window"])
    cal = clean_rows(blob["calib"])
    rep = build_report(win, cal)

    print(f"# window rows (clean): {len(win)}  shadow={rep['n_shadow']} live={rep['n_live']}")
    print(f"# calib entry_types (2026-04-08..14): {rep['n_calib_types']}")
    print(f"# Bonferroni m={BONFERRONI_M} alpha={ALPHA}")
    print()
    print("## P0 — 再構成妥当性 (LIVE 行が条件を踏んだ件数)")
    print(f"{'blk':<4} {'name':<32} {'live_hit':>8} {'non_exempt':>11}  cells")
    for r in rep["p0"]:
        print(f"{r['block']:<4} {r['name']:<32} {r['live_hits']:>8} "
              f"{r['live_hits_non_exempt']:>11}  {','.join(r['non_exempt_cells'])}")
    print()
    print("## P1/P2 — 新窓 shadow 母集団")
    print(f"{'blk':<4} {'calN':>5} {'calEV':>7} {'N':>5} {'WR':>6} {'EVgr':>7} "
          f"{'EVnet':>7} {'CIlo':>7} {'CIhi':>7} {'p':>8} {'ovlp':>6}  verdict")
    for r in rep["blocks"]:
        if r["n"] == 0:
            print(f"{r['block']:<4} {str(r['calib_n'] or '-'):>5} "
                  f"{(r['calib_ev'] if r['calib_ev'] is not None else float('nan')):>7.2f} "
                  f"{0:>5}  (no rows)")
            continue
        print(f"{r['block']:<4} {str(r['calib_n'] or '-'):>5} "
              f"{(r['calib_ev'] if r['calib_ev'] is not None else float('nan')):>7.2f} "
              f"{r['n']:>5} {r['wr']*100:>5.1f}% {r['ev_gross']:>7.2f} {r['ev_net']:>7.2f} "
              f"{r['ci_net_lo']:>7.2f} {r['ci_net_hi']:>7.2f} {r['p_neg_net']:>8.4f} "
              f"{r['overlap']*100:>5.1f}%  {r['verdict']}")

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(rep, fh, indent=2, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
