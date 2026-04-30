#!/usr/bin/env python3
"""BT vs Live divergence v2 — using FRESH 365d BT (2026-04-22).

Updates:
- BT baseline = bt-365d-2026-04-22.json (fresh, USDJPY/EURUSD/GBPUSD × DT 15m × 365d)
- Live data = /api/demo/trades
- Pre/post-Cutoff split on LIVE to distinguish sample-period effect from overfitting
- Bonferroni at M = actual cells with N_live >= 10 (stricter than M=15 estimate)
"""
from __future__ import annotations
import json, math
from collections import defaultdict
from pathlib import Path

# ── Load fresh BT ──
BT_PATH = "/Users/jg-n-012/test/fx-ai-trader/knowledge-base/raw/bt-results/bt-365d-2026-04-22.json"
bt_data = json.load(open(BT_PATH))
SYM_MAP = {"USDJPY=X": "USD_JPY", "EURUSD=X": "EUR_USD", "GBPUSD=X": "GBP_USD"}
# BT[(strat, pair)] = (N, WR%, EV, PnL, PF)
BT = {}
for sym, r in bt_data["results"].items():
    pair = SYM_MAP.get(sym, sym)
    for strat, s in r.get("entry_breakdown", {}).items():
        n = s.get("N") or s.get("total") or 0
        wr = s.get("WR") or s.get("win_rate") or 0
        ev = s.get("EV") or s.get("ev") or 0
        BT[(strat, pair)] = {"N": n, "WR": wr, "EV": ev}

# ── Live data ──
with open("/tmp/bt_divergence/live_trades.json") as f:
    LIVE = [t for t in json.load(f).get("trades", []) if t.get("instrument") != "XAU_USD"]
CUTOFF = "2026-04-16"

def _is_wl(o): return o in ("WIN", "LOSS")
def _date(t): return (t.get("entry_time") or "")[:10]

def agg(trades):
    if not trades: return None
    N = len(trades)
    wins = sum(1 for t in trades if t.get("outcome") == "WIN")
    pnls = [float(t.get("pnl_pips") or 0) for t in trades]
    WR = 100 * wins / N
    EV = sum(pnls) / N
    gp = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p < 0))
    PF = gp / max(gl, 1e-9)
    return {"N": N, "wins": wins, "WR": WR, "EV": EV, "PnL": sum(pnls), "PF": PF}

grp_all = defaultdict(list)
grp_post = defaultdict(list)
for t in LIVE:
    if not _is_wl(t.get("outcome")): continue
    key = (t.get("entry_type"), t.get("instrument"))
    grp_all[key].append(t)
    if _date(t) > CUTOFF:
        grp_post[key].append(t)

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n
    d = 1 + z*z/n
    centre = (p + z*z/(2*n)) / d
    margin = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (max(0, centre - margin) * 100, min(1, centre + margin) * 100)

def two_prop_z(p1, n1, p2, n2):
    if n1 == 0 or n2 == 0: return (0.0, 1.0)
    p_pool = (p1*n1 + p2*n2) / (n1 + n2)
    denom = math.sqrt(max(p_pool*(1-p_pool)*(1/n1 + 1/n2), 1e-12))
    z = (p1 - p2) / denom
    p_two = math.erfc(abs(z)/math.sqrt(2))
    return (z, p_two)

# ── Compare ALL and POST ──
rows_all, rows_post = [], []
for key, bt in BT.items():
    strat, pair = key
    if bt["N"] < 5: continue
    # All live
    live_all = agg(grp_all.get(key, []))
    live_pst = agg(grp_post.get(key, []))
    def push(rows, live, label):
        if not live or live["N"] < 3: return
        z, p = two_prop_z(live["WR"]/100, live["N"], bt["WR"]/100, bt["N"])
        lo, hi = wilson(live["wins"], live["N"])
        rows.append({
            "strat": strat, "pair": pair, "label": label,
            "bt_N": bt["N"], "bt_WR": bt["WR"], "bt_EV": bt["EV"],
            "live_N": live["N"], "live_WR": live["WR"], "live_EV": live["EV"],
            "live_PF": live["PF"], "live_PnL": live["PnL"],
            "dWR": live["WR"]-bt["WR"], "dEV": live["EV"]-bt["EV"],
            "z": z, "p": p, "wilson_lo": lo, "wilson_hi": hi,
        })
    push(rows_all, live_all, "ALL")
    push(rows_post, live_pst, "POST")

# Sort by |ΔEV| * sqrt(N)
def rank(rows):
    rows.sort(key=lambda r: abs(r["dEV"]) * math.sqrt(r["live_N"]), reverse=True)
    return rows
rows_all = rank(rows_all)
rows_post = rank(rows_post)

def emit_table(rows, limit=15, side="neg"):
    if side == "neg":
        rows = [r for r in rows if r["dEV"] < 0][:limit]
        hdr = f"## LIVE < BT (top {limit})"
    else:
        rows = [r for r in rows if r["dEV"] > 0][:limit]
        hdr = f"## LIVE > BT (top {limit})"
    lines = [hdr, ""]
    lines.append("| # | Strategy×Pair | BT(N/WR/EV) | Live(N/WR/EV) | ΔWR | ΔEV | z | p | Wilson95 | PnL |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|---|---:|")
    for i, r in enumerate(rows, 1):
        lines.append(
            f"| {i} | {r['strat']}×{r['pair']} "
            f"| {r['bt_N']}/{r['bt_WR']:.1f}%/{r['bt_EV']:+.3f} "
            f"| {r['live_N']}/{r['live_WR']:.1f}%/{r['live_EV']:+.3f} "
            f"| {r['dWR']:+.1f}pp | {r['dEV']:+.3f} "
            f"| {r['z']:+.2f} | {r['p']:.4f} "
            f"| [{r['wilson_lo']:.1f}, {r['wilson_hi']:.1f}] | {r['live_PnL']:+.1f} |"
        )
    return "\n".join(lines)

out = []
out.append("# Fresh 365d BT vs Live Divergence (v2) — 2026-04-22\n")
out.append(f"**BT Source**: bt-365d-2026-04-22.json (USDJPY/EURUSD/GBPUSD × DT15m × 365d, freshly computed)")
out.append(f"**Live Source**: /api/demo/trades N={len(LIVE)}")
out.append(f"**Cells with BT data**: {len(BT)} / with Live counter-part (ALL): {len(rows_all)} / (POST-Cutoff): {len(rows_post)}")
out.append(f"**Ranking**: |ΔEV| × √N_live\n")

out.append("## §A. ALL Live period (2026-04-02 ~ 2026-04-22)\n")
out.append(emit_table(rows_all, 15, "neg"))
out.append("")
out.append(emit_table(rows_all, 10, "pos"))

out.append("\n## §B. POST-Cutoff Only (2026-04-17+, N_live≥5 cleaner regime)\n")
out.append(emit_table(rows_post, 15, "neg"))
out.append("")
out.append(emit_table(rows_post, 10, "pos"))

# Significant cells with Bonferroni
M_all = len([r for r in rows_all if r["live_N"] >= 10])
M_post = len([r for r in rows_post if r["live_N"] >= 10])
alpha_all = 0.05 / max(M_all, 1)
alpha_post = 0.05 / max(M_post, 1)

out.append(f"\n## §C. Bonferroni-filtered significant divergences\n")
out.append(f"**ALL**: M={M_all}, α/M={alpha_all:.5f}")
for r in rows_all:
    if r["live_N"] >= 10 and r["p"] < alpha_all and r["dEV"] < 0:
        out.append(f"- ⭐ {r['strat']}×{r['pair']}  (ALL)  N={r['live_N']}  WR={r['live_WR']:.1f}% vs BT {r['bt_WR']:.1f}%  z={r['z']:.2f} p={r['p']:.5f}")

out.append(f"\n**POST**: M={M_post}, α/M={alpha_post:.5f}")
for r in rows_post:
    if r["live_N"] >= 10 and r["p"] < alpha_post and r["dEV"] < 0:
        out.append(f"- ⭐ {r['strat']}×{r['pair']}  (POST)  N={r['live_N']}  WR={r['live_WR']:.1f}% vs BT {r['bt_WR']:.1f}%  z={r['z']:.2f} p={r['p']:.5f}")

# ── BT-only drift: 2026-04-15 scan vs 2026-04-22 scan ──
OLD_BT = {
    # (strat, pair): (N, WR, EV)
    ("vwap_mean_reversion", "GBP_USD"): (220, 72.3, 1.087),
    ("gbp_deep_pullback", "GBP_USD"): (93, 62.4, 0.603),
    ("session_time_bias", "GBP_USD"): (392, 63.8, 0.149),
    ("trendline_sweep", "GBP_USD"): (114, 77.2, 0.838),
    ("post_news_vol", "GBP_USD"): (19, 78.9, 1.302),
    ("dt_sr_channel_reversal", "GBP_USD"): (53, 66.0, 0.18),
    ("xs_momentum", "GBP_USD"): (295, 60.3, -0.013),
    ("sr_fib_confluence", "GBP_USD"): (241, 58.5, 0.015),
    ("dt_bb_rsi_mr", "GBP_USD"): (117, 45.3, -0.182),
    ("dual_sr_bounce", "GBP_USD"): (90, 52.2, -0.189),
    ("london_fix_reversal", "GBP_USD"): (57, 47.4, -0.239),
    ("dt_fib_reversal", "GBP_USD"): (24, 66.7, 0.097),
    ("ema_cross", "GBP_USD"): (16, 37.5, -0.726),
    ("ema200_trend_reversal", "GBP_USD"): (34, 58.8, -0.066),
    ("turtle_soup", "GBP_USD"): (44, 63.6, 0.187),
    ("post_news_vol", "USD_JPY"): (25, 80.0, 0.933),
    ("htf_false_breakout", "USD_JPY"): (14, 100.0, 1.291),
    ("vix_carry_unwind", "USD_JPY"): (103, 69.9, 0.521),
    ("post_news_vol", "EUR_USD"): (26, 73.1, 0.836),
    ("session_time_bias", "EUR_USD"): (526, 69.0, 0.301),
    ("trendline_sweep", "EUR_USD"): (67, 82.1, 0.987),
    ("vwap_mean_reversion", "EUR_USD"): (210, 72.9, 0.615),
    ("squeeze_release_momentum", "EUR_USD"): (15, 66.7, 0.460),
    ("htf_false_breakout", "EUR_USD"): (12, 83.3, 0.625),
}

out.append("\n## §D. BT itself drift (2026-04-15 → 2026-04-22, 7日差)\n")
out.append("| Strategy×Pair | BT_15 N/WR/EV | BT_22 N/WR/EV | ΔN | ΔWR | ΔEV |")
out.append("|---|---|---|---:|---:|---:|")
drift_rows = []
for key, old in OLD_BT.items():
    new = BT.get(key)
    if not new: continue
    oN, oWR, oEV = old
    nN, nWR, nEV = new["N"], new["WR"], new["EV"]
    drift_rows.append((key, old, new, nWR-oWR, nEV-oEV))
drift_rows.sort(key=lambda x: -abs(x[4]))  # sort by |ΔEV|
for (k, old, new, dWR, dEV) in drift_rows[:20]:
    out.append(f"| {k[0]}×{k[1]} | {old[0]}/{old[1]:.1f}/{old[2]:+.3f} | {new['N']}/{new['WR']:.1f}/{new['EV']:+.3f} | {new['N']-old[0]:+d} | {dWR:+.1f} | {dEV:+.3f} |")

report = "\n".join(out)
Path("/tmp/bt_divergence/divergence_v2_report.md").write_text(report)
print(f"wrote /tmp/bt_divergence/divergence_v2_report.md")
print()
print(report)
