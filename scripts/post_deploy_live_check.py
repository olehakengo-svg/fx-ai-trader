#!/usr/bin/env python3
"""
Post-deploy Live observation tool — 4修正の即時効果検証.

Coverage:
  1. bb_rsi_reversion 緊急トリップ (commit ef759ea, 2026-04-25)
  2. vwap_mean_reversion 緊急トリップ (commit c195d16, 2026-04-24)
  3. ELITE 3戦略 patch (MTF/Q4 gate 免除, commit c195d16)
  4. Grail Sentinel bypass (commit ef759ea)

Plus: Phase 1 holdout (2026-05-07) までの aggregated metrics.

Usage:
    python3 scripts/post_deploy_live_check.py [--since 2026-04-24T15:00] [--full]

Network: shells out to curl (avoid urllib for security policy compliance).
"""
import argparse, json, math, subprocess, sys
from collections import Counter, defaultdict
from statistics import mean
from typing import Optional

# Hardcoded API base — no dynamic URL construction
_API_TRADES = "https://fx-ai-trader.onrender.com/api/demo/trades"
_API_LOGS = "https://fx-ai-trader.onrender.com/api/demo/logs"

def _curl_json(url: str, params: Optional[dict] = None):
    """Fetch JSON via curl. URL must be a hardcoded constant; params are appended safely."""
    if url not in (_API_TRADES, _API_LOGS):
        raise ValueError(f"URL not whitelisted: {url}")
    args = ["curl", "-s", "-G", "--max-time", "30", "-H", "Accept: application/json", url]
    if params:
        for k, v in params.items():
            args.extend(["--data-urlencode", f"{k}={v}"])
    try:
        out = subprocess.check_output(args, timeout=35)
        return json.loads(out)
    except Exception as e:
        print(f"[err] curl {url}: {e}", file=sys.stderr)
        return None

def wilson_lo(k, n, z=1.96):
    if n == 0: return 0.0
    p = k / n
    d = 1 + z*z/n
    c = p + z*z/(2*n)
    s = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))
    return max(0.0, (c - s) / d) * 100.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-04-24T15:00",
                    help="ISO timestamp; default 2026-04-24 15:00 UTC (post c195d16 deploy)")
    ap.add_argument("--full", action="store_true", help="Print all per-strategy details")
    args = ap.parse_args()

    print("=" * 78)
    print(f"Post-deploy Live observation — since {args.since}")
    print("=" * 78)

    # Trades
    print("\n[1/3] Fetching trades...")
    trades_raw = _curl_json(_API_TRADES,
                            {"limit": "2000", "date_from": args.since[:10]})
    if trades_raw is None:
        print("[fatal] trades API failed"); return 1
    trades = trades_raw if isinstance(trades_raw, list) else trades_raw.get("trades", [])
    trades = [t for t in trades if t.get("entry_time", "") >= args.since]
    trades = [t for t in trades if "XAU" not in (t.get("instrument") or "")]
    print(f"  trades since {args.since}: {len(trades)} (XAU除外)")

    if not trades:
        print("\n  [info] No trades. Likely market closed (Sat/Sun UTC).")
        print("  Re-run after Mon 09:00 UTC (Tokyo open).")
        return 0
    print(f"  date range: {min(t.get('entry_time','') for t in trades)[:19]} → "
          f"{max(t.get('entry_time','') for t in trades)[:19]}")

    # ---- 1. bb_rsi trip ----
    print("\n" + "=" * 78)
    print("[1] bb_rsi_reversion 緊急トリップ — 期待: post-deploy Live=0")
    print("=" * 78)
    bb_rsi = [t for t in trades if t.get("entry_type") == "bb_rsi_reversion"]
    deploy_ts = "2026-04-25T08:00"
    pre = [t for t in bb_rsi if t.get("entry_time", "") < deploy_ts]
    post = [t for t in bb_rsi if t.get("entry_time", "") >= deploy_ts]
    pre_live = sum(1 for t in pre if not t.get("is_shadow"))
    post_live = sum(1 for t in post if not t.get("is_shadow"))
    print(f"  total N={len(bb_rsi)} live={sum(1 for t in bb_rsi if not t.get('is_shadow'))}")
    print(f"  pre-trip  (< {deploy_ts}): N={len(pre)}, live={pre_live}")
    print(f"  post-trip (≥ {deploy_ts}): N={len(post)}, live={post_live}  ← 期待: 0")
    if post_live == 0 and len(post) > 0:
        print(f"  ✅ TRIP WORKING: {len(post)} trades 全て Shadow")
    elif len(post) == 0:
        print("  ⏳ NO DATA YET — Mon Tokyo open 以降再確認")
    else:
        print(f"  ❌ ALERT: post-deploy {post_live} 件 Live trade 検出")

    # ---- 2. vwap_mr trip ----
    print("\n" + "=" * 78)
    print("[2] vwap_mean_reversion 緊急トリップ — 期待: Live=0")
    print("=" * 78)
    vwap = [t for t in trades if t.get("entry_type") == "vwap_mean_reversion"]
    vwap_live = sum(1 for t in vwap if not t.get("is_shadow"))
    print(f"  total N={len(vwap)} live={vwap_live}")
    print(f"  {'✅ TRIP WORKING' if vwap_live == 0 else '❌ ALERT'}")

    # ---- 3. ELITE patch ----
    print("\n" + "=" * 78)
    print("[3] ELITE 3戦略 patch — 期待: Live N 蓄積")
    print("=" * 78)
    for et in ("gbp_deep_pullback", "session_time_bias", "trendline_sweep"):
        sub = [t for t in trades if t.get("entry_type") == et]
        live = [t for t in sub if not t.get("is_shadow")]
        actions = Counter(t.get("mtf_gate_action") for t in sub)
        print(f"  {et}: total N={len(sub)} live={len(live)} mtf_gate: {dict(actions)}")
        if live:
            pnls = [t.get("pnl_pips", 0) for t in live if t.get("pnl_pips") is not None]
            if pnls:
                wins = sum(1 for p in pnls if p > 0)
                print(f"    Live WR={wins}/{len(pnls)}={wins/len(pnls)*100:.1f}% "
                      f"EV={mean(pnls):+.2f}p Wlo={wilson_lo(wins, len(pnls)):.1f}%")

    # ---- 4. Grail Sentinel ----
    print("\n" + "=" * 78)
    print("[4] Grail Sentinel — 期待: 4戦略 USD_JPY のみ Live trade")
    print("=" * 78)
    for et in ("ema200_trend_reversal", "vol_surge_detector", "vix_carry_unwind", "ny_close_reversal"):
        sub = [t for t in trades if t.get("entry_type") == et]
        live_jpy = [t for t in sub if not t.get("is_shadow") and t.get("instrument") == "USD_JPY"]
        print(f"  {et}: total N={len(sub)} USDJPY_live={len(live_jpy)}")
        if live_jpy:
            pnls = [t.get("pnl_pips", 0) for t in live_jpy if t.get("pnl_pips") is not None]
            if pnls:
                wins = sum(1 for p in pnls if p > 0)
                print(f"    USDJPY Live WR={wins}/{len(pnls)}={wins/len(pnls)*100:.1f}% "
                      f"EV={mean(pnls):+.2f}p Wlo={wilson_lo(wins, len(pnls)):.1f}%")

    # ---- Aggregate ----
    print("\n" + "=" * 78)
    print("[Aggregate] Live KPI (Phase 1 holdout 2026-05-07 まで)")
    print("=" * 78)
    live_all = [t for t in trades if not t.get("is_shadow")]
    pnls_all = [t.get("pnl_pips") for t in live_all if t.get("pnl_pips") is not None]
    if pnls_all:
        pos = [p for p in pnls_all if p > 0]
        neg = [-p for p in pnls_all if p < 0]
        wins = sum(1 for p in pnls_all if p > 0)
        print(f"  Live N={len(live_all)} closed={len(pnls_all)} "
              f"PnL={sum(pnls_all):+.1f}p EV={mean(pnls_all):+.3f}p")
        print(f"  WR={wins/len(pnls_all)*100:.1f}% Wlo={wilson_lo(wins, len(pnls_all)):.1f}% "
              f"PF={sum(pos)/sum(neg):.2f}" if neg else "")

    if args.full:
        print("\n  --- per-strategy ---")
        per = defaultdict(list)
        for t in live_all:
            if t.get("pnl_pips") is not None:
                per[t.get("entry_type")].append(t["pnl_pips"])
        for et, ps in sorted(per.items(), key=lambda x: -sum(x[1])):
            wins = sum(1 for p in ps if p > 0)
            print(f"    {et:<28} N={len(ps):>3} WR={wins/len(ps)*100:>5.1f}% "
                  f"EV={mean(ps):>+6.2f}p ΣPnL={sum(ps):>+6.1f}p")

    # Logs
    print("\n" + "=" * 78)
    print("[Diagnostics] Render logs (latest 30)")
    print("=" * 78)
    logs_raw = _curl_json(_API_LOGS)
    if logs_raw:
        logs = logs_raw if isinstance(logs_raw, list) else logs_raw.get("logs", [])
        for p in ("EMERGENCY_TRIP", "[GRAIL]", "elite_exempt", "MTF_GATE", "MAE_BREAKER"):
            matches = [l for l in logs if p in str(l.get("message", "") if isinstance(l, dict) else l)]
            print(f"  [{p}]: {len(matches)} hits")

    print(f"\n{'=' * 78}\nDone.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
