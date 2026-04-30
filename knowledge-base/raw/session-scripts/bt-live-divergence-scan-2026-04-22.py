#!/usr/bin/env python3
"""BT vs Live divergence analysis (2026-04-22).

Strategy:
1. BT baseline = full-bt-scan-2026-04-15.md (365d DT 15m + 180d scalp 1m/5m)
2. Live observed = /api/demo/trades (is_shadow included, filter non-XAU)
3. Compute per-cell (strategy, pair):
     ΔEV = Live_EV - BT_EV
     ΔWR = Live_WR - BT_WR
     z_wr = (p_live - p_bt) / sqrt(p_bt*(1-p_bt)/n_live)  two-proportion z
     fisher_p (exact) when N < 30 or n_bt small
4. Rank by |ΔEV| * sqrt(N_live) (effect-size weighted by sample)
5. Mechanistic investigation for top-10 divergent cells.
"""
from __future__ import annotations
import json, math, statistics, re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

# ── Load Live/Shadow trades ──
TRADES_PATH = "/tmp/bt_divergence/live_trades.json"
with open(TRADES_PATH) as f:
    raw = json.load(f)
LIVE = [t for t in raw.get("trades", []) if t.get("instrument") != "XAU_USD"]

# Keep only W/L outcomes for WR calculation; separate shadow vs live
def _is_wl(o): return o in ("WIN", "LOSS")

# Index by (entry_type, instrument, is_shadow)
def group_trades(trades):
    groups = defaultdict(list)
    for t in trades:
        if not _is_wl(t.get("outcome")):
            continue
        groups[(t.get("entry_type"), t.get("instrument"), int(t.get("is_shadow") or 0))].append(t)
    return groups

GRP = group_trades(LIVE)

def agg(trades):
    if not trades:
        return None
    N = len(trades)
    wins = sum(1 for t in trades if t.get("outcome") == "WIN")
    WR = wins / N * 100
    pnls = [float(t.get("pnl_pips") or 0) for t in trades]
    EV = sum(pnls) / N
    gp = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p < 0))
    PF = gp / max(gl, 1e-9)
    return {"N": N, "wins": wins, "WR": WR, "EV": EV, "PF": PF, "pnl_sum": sum(pnls)}

# ── BT baseline (hardcoded from 2026-04-15 full-bt-scan.md) ──
# Strategy, Pair, TF, N, WR, EV, PF (from DT 15m 365d table; scalp tables truncated)
# Source: knowledge-base/raw/bt-results/full-bt-scan-2026-04-15.md + bt-365d-2026-04-16.json
BT_365D_DT = {
    # (entry_type, instrument): {"N", "WR", "EV", "PF"}
    # --- From bt-365d-2026-04-16.json (GBPUSD only) ---
    ("vwap_mean_reversion", "GBP_USD"): {"N": 220, "WR": 72.3, "EV": 1.087, "PF": None, "tf": "15m"},
    ("htf_false_breakout", "GBP_USD"): {"N": 23, "WR": 56.5, "EV": -0.108, "PF": None, "tf": "15m"},
    ("gbp_deep_pullback", "GBP_USD"): {"N": 93, "WR": 62.4, "EV": 0.603, "PF": None, "tf": "15m"},
    ("session_time_bias", "GBP_USD"): {"N": 392, "WR": 63.8, "EV": 0.149, "PF": None, "tf": "15m"},
    ("dt_bb_rsi_mr", "GBP_USD"): {"N": 117, "WR": 45.3, "EV": -0.182, "PF": None, "tf": "15m"},
    ("sr_fib_confluence", "GBP_USD"): {"N": 241, "WR": 58.5, "EV": 0.015, "PF": None, "tf": "15m"},
    ("trendline_sweep", "GBP_USD"): {"N": 114, "WR": 77.2, "EV": 0.838, "PF": None, "tf": "15m"},
    ("turtle_soup", "GBP_USD"): {"N": 44, "WR": 63.6, "EV": 0.187, "PF": None, "tf": "15m"},
    ("london_fix_reversal", "GBP_USD"): {"N": 57, "WR": 47.4, "EV": -0.239, "PF": None, "tf": "15m"},
    ("dual_sr_bounce", "GBP_USD"): {"N": 90, "WR": 52.2, "EV": -0.189, "PF": None, "tf": "15m"},
    ("xs_momentum", "GBP_USD"): {"N": 295, "WR": 60.3, "EV": -0.013, "PF": None, "tf": "15m"},
    ("dt_sr_channel_reversal", "GBP_USD"): {"N": 53, "WR": 66.0, "EV": 0.18, "PF": None, "tf": "15m"},
    ("dt_fib_reversal", "GBP_USD"): {"N": 24, "WR": 66.7, "EV": 0.097, "PF": None, "tf": "15m"},
    ("ema200_trend_reversal", "GBP_USD"): {"N": 34, "WR": 58.8, "EV": -0.066, "PF": None, "tf": "15m"},
    ("doji_breakout", "GBP_USD"): {"N": 19, "WR": 78.9, "EV": 0.694, "PF": None, "tf": "15m"},
    ("ema_cross", "GBP_USD"): {"N": 16, "WR": 37.5, "EV": -0.726, "PF": None, "tf": "15m"},
    ("post_news_vol", "GBP_USD"): {"N": 19, "WR": 78.9, "EV": 1.302, "PF": None, "tf": "15m"},
    # --- From full-bt-scan-2026-04-15.md (DT 15m 365d multi-pair) ---
    ("post_news_vol", "USD_JPY"):        {"N": 25, "WR": 80.0, "EV": 0.933, "PF": 1.82, "tf": "15m"},
    ("post_news_vol", "EUR_USD"):        {"N": 26, "WR": 73.1, "EV": 0.836, "PF": 1.72, "tf": "15m"},
    ("htf_false_breakout", "USD_JPY"):   {"N": 14, "WR": 100.0, "EV": 1.291, "PF": None, "tf": "15m"},
    ("htf_false_breakout", "EUR_USD"):   {"N": 12, "WR": 83.3, "EV": 0.625, "PF": 2.04, "tf": "15m"},
    ("trendline_sweep", "EUR_USD"):      {"N": 67, "WR": 82.1, "EV": 0.987, "PF": 2.75, "tf": "15m"},
    ("vwap_mean_reversion", "EUR_USD"):  {"N": 210, "WR": 72.9, "EV": 0.615, "PF": 2.53, "tf": "15m"},
    ("vwap_mean_reversion", "EUR_JPY"):  {"N": 380, "WR": 68.2, "EV": 0.318, "PF": 1.70, "tf": "15m"},
    ("vix_carry_unwind", "USD_JPY"):     {"N": 103, "WR": 69.9, "EV": 0.521, "PF": 1.48, "tf": "15m"},
    ("session_time_bias", "EUR_USD"):    {"N": 526, "WR": 69.0, "EV": 0.301, "PF": 1.47, "tf": "15m"},
    ("turtle_soup", "GBP_USD_m15"):      {"N": 60, "WR": 71.7, "EV": 0.560, "PF": 1.79, "tf": "15m"},
    ("ema_cross", "EUR_JPY"):            {"N": 32, "WR": 71.9, "EV": 0.337, "PF": 1.67, "tf": "15m"},
    ("dt_fib_reversal", "GBP_USD_m15"):  {"N": 22, "WR": 72.7, "EV": 0.310, "PF": 1.63, "tf": "15m"},
    ("doji_breakout", "GBP_USD_m15"):    {"N": 20, "WR": 80.0, "EV": 0.793, "PF": 2.70, "tf": "15m"},
    ("squeeze_release_momentum", "EUR_USD"): {"N": 15, "WR": 66.7, "EV": 0.460, "PF": 1.91, "tf": "15m"},
    ("adx_trend_continuation", "EUR_USD"):  {"N": 11, "WR": 63.6, "EV": 0.303, "PF": 1.31, "tf": "15m"},
}

# ── Scalp BT (180d 1m/5m) from full-bt-scan-2026-04-15.md ──
BT_SCALP = {
    # 1m
    ("trend_rebound", "USD_JPY"): {"N": 22, "WR": 81.8, "EV": 0.450, "tf": "1m"},
    ("bb_squeeze_breakout", "GBP_JPY"): {"N": 67, "WR": 73.1, "EV": 0.340, "tf": "1m"},
    ("bb_squeeze_breakout", "EUR_USD"): {"N": 46, "WR": 73.9, "EV": 0.274, "tf": "1m"},
    ("stoch_trend_pullback", "GBP_JPY"): {"N": 90, "WR": 71.1, "EV": 0.240, "tf": "1m"},
    ("vwap_mean_reversion", "USD_JPY"): {"N": 12, "WR": 58.3, "EV": 0.112, "tf": "1m"},
    ("ema_trend_scalp", "GBP_JPY"):     {"N": 1185, "WR": 65.4, "EV": 0.042, "tf": "1m"},
    ("bb_squeeze_breakout", "EUR_JPY"): {"N": 65, "WR": 66.2, "EV": 0.002, "tf": "1m"},
    # 5m
    ("vol_momentum_scalp", "EUR_JPY"):  {"N": 34, "WR": 82.4, "EV": 0.608, "tf": "5m"},
    ("vol_surge_detector", "EUR_JPY"):  {"N": 19, "WR": 78.9, "EV": 0.570, "tf": "5m"},
    ("bb_squeeze_breakout", "USD_JPY"): {"N": 18, "WR": 77.8, "EV": 0.457, "tf": "5m"},
    ("engulfing_bb", "USD_JPY"):         {"N": 36, "WR": 69.4, "EV": 0.213, "tf": "5m"},
    ("sr_channel_reversal", "GBP_JPY"):  {"N": 70, "WR": 65.7, "EV": 0.122, "tf": "5m"},
    ("ema_trend_scalp", "GBP_JPY_5m"):   {"N": 226, "WR": 64.6, "EV": 0.091, "tf": "5m"},
}

# Merge BT tables
BT = {}
for k, v in list(BT_365D_DT.items()) + list(BT_SCALP.items()):
    key = (k[0], k[1].split("_m15")[0].split("_5m")[0])  # strip TF suffix
    if key not in BT:
        BT[key] = v
    else:
        # If duplicate key (e.g. vwap_mean_reversion GBP_USD DT+scalp), prefer DT
        pass

# ── Statistical helpers ──
def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n
    d = 1 + z*z/n
    centre = (p + z*z/(2*n)) / d
    margin = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (max(0, centre - margin) * 100, min(1, centre + margin) * 100)

def two_prop_z(p1, n1, p2, n2):
    """Two-proportion z-test (p1 = live, p2 = BT). Returns z and two-sided p."""
    if n1 == 0 or n2 == 0: return (0.0, 1.0)
    p_pool = (p1*n1 + p2*n2) / (n1 + n2)
    denom = math.sqrt(max(p_pool*(1-p_pool)*(1/n1 + 1/n2), 1e-12))
    z = (p1 - p2) / denom
    # Two-sided p
    p_two = math.erfc(abs(z)/math.sqrt(2))
    return (z, p_two)

# ── Core comparison ──
rows = []
for (strat, pair), bt in BT.items():
    live = agg(GRP.get((strat, pair, 0), []))
    shadow = agg(GRP.get((strat, pair, 1), []))
    # Combine live+shadow where applicable (both are post-cutoff samples)
    combined = GRP.get((strat, pair, 0), []) + GRP.get((strat, pair, 1), [])
    comb = agg(combined)
    bt_N = bt["N"]; bt_WR = bt["WR"]; bt_EV = bt["EV"]
    if comb is None or comb["N"] < 5:
        continue
    live_N = comb["N"]; live_WR = comb["WR"]; live_EV = comb["EV"]
    dWR = live_WR - bt_WR
    dEV = live_EV - bt_EV
    z, p_two = two_prop_z(live_WR/100, live_N, bt_WR/100, bt_N)
    lo, hi = wilson(comb["wins"], comb["N"])
    rows.append({
        "strat": strat, "pair": pair,
        "bt_N": bt_N, "bt_WR": bt_WR, "bt_EV": bt_EV,
        "live_N": live_N, "live_WR": live_WR, "live_EV": live_EV,
        "live_PF": comb["PF"], "live_PnL": comb["pnl_sum"],
        "dWR": dWR, "dEV": dEV, "z": z, "p": p_two,
        "wilson_lo": lo, "wilson_hi": hi,
        "live_shadow_split": (len(GRP.get((strat, pair, 1), [])), len(GRP.get((strat, pair, 0), []))),
    })

# ── Rank by |dEV| weighted by sqrt(live_N) ──
rows.sort(key=lambda r: abs(r["dEV"]) * math.sqrt(r["live_N"]), reverse=True)

out_lines = []
out_lines.append("# BT vs Live Divergence — Full Portfolio Scan (2026-04-22)\n")
out_lines.append(f"**BT baseline**: full-bt-scan-2026-04-15.md (365d DT + 180d Scalp)")
out_lines.append(f"**Live data**: /api/demo/trades N={len(LIVE)} (W/L only, non-XAU, shadow+live combined)")
out_lines.append(f"**Cells compared**: {len(rows)}")
out_lines.append(f"**Method**: ΔEV = Live_EV - BT_EV (pip); two-proportion z on WR; Wilson 95% on Live WR")
out_lines.append(f"**Ranking**: |ΔEV| × √N_live (effect × sample weight)\n")

# Top divergent (negative — Live underperform BT)
neg = [r for r in rows if r["dEV"] < 0][:15]
pos = [r for r in rows if r["dEV"] > 0][:10]

out_lines.append("## §1. LIVE < BT (under-performance, top 15)\n")
out_lines.append("| # | Strategy×Pair | BT (N/WR/EV) | Live (N/WR/EV) | ΔWR | ΔEV | z(WR) | p | Wilson95 | PnL |")
out_lines.append("|---|---|---|---|---:|---:|---:|---:|---|---:|")
for i, r in enumerate(neg, 1):
    out_lines.append(
        f"| {i} | {r['strat']}×{r['pair']} "
        f"| {r['bt_N']}/{r['bt_WR']:.1f}%/{r['bt_EV']:+.3f} "
        f"| {r['live_N']}/{r['live_WR']:.1f}%/{r['live_EV']:+.3f} "
        f"| {r['dWR']:+.1f}pp | {r['dEV']:+.3f} | {r['z']:+.2f} | {r['p']:.4f} "
        f"| [{r['wilson_lo']:.1f}, {r['wilson_hi']:.1f}] | {r['live_PnL']:+.1f} |"
    )

out_lines.append("\n## §2. LIVE > BT (over-performance, top 10)\n")
out_lines.append("| # | Strategy×Pair | BT (N/WR/EV) | Live (N/WR/EV) | ΔWR | ΔEV | z | PnL |")
out_lines.append("|---|---|---|---|---:|---:|---:|---:|")
for i, r in enumerate(pos, 1):
    out_lines.append(
        f"| {i} | {r['strat']}×{r['pair']} "
        f"| {r['bt_N']}/{r['bt_WR']:.1f}%/{r['bt_EV']:+.3f} "
        f"| {r['live_N']}/{r['live_WR']:.1f}%/{r['live_EV']:+.3f} "
        f"| {r['dWR']:+.1f}pp | {r['dEV']:+.3f} | {r['z']:+.2f} | {r['live_PnL']:+.1f} |"
    )

# ── Save report ──
report = "\n".join(out_lines)
OUT = Path("/tmp/bt_divergence/divergence_report.md")
OUT.write_text(report)
print(f"wrote {OUT} ({len(out_lines)} lines)")
print()
print(report[:4500])
