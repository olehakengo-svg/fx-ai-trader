#!/usr/bin/env python3
"""Mechanistic investigation for top divergent BT vs Live cells.

For each target cell:
  - Pre vs Post-cutoff WR (regime shift?)
  - Shadow vs Live WR (Kelly learning artifact?)
  - MFE/MAE distribution (SL too tight? TP too far?)
  - Immediate death rate (entry timing break?)
  - Regime distribution (mtf_regime / mtf_vol_state)
  - Hour distribution (session gate drift?)
  - Spread at entry (friction gate drift?)
"""
import json, statistics, math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

with open("/tmp/bt_divergence/live_trades.json") as f:
    LIVE = [t for t in json.load(f).get("trades", []) if t.get("instrument") != "XAU_USD"]

CUTOFF = "2026-04-16"

# Targets from divergence_report.md top 10 LIVE<BT
TARGETS = [
    ("dt_sr_channel_reversal", "GBP_USD"),
    ("vwap_mean_reversion", "EUR_JPY"),
    ("session_time_bias", "GBP_USD"),
    ("post_news_vol", "USD_JPY"),
    ("dual_sr_bounce", "GBP_USD"),
    ("bb_squeeze_breakout", "EUR_USD"),
    ("vix_carry_unwind", "USD_JPY"),
    ("post_news_vol", "GBP_USD"),
    ("sr_fib_confluence", "GBP_USD"),
    ("engulfing_bb", "USD_JPY"),
]

def _entry_date(t):
    s = t.get("entry_time") or t.get("created_at") or ""
    try: return s[:10]
    except: return ""

def _is_wl(o): return o in ("WIN", "LOSS")

def pct(x, n):
    return 100 * x / max(n, 1)

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n
    d = 1 + z*z/n
    centre = (p + z*z/(2*n)) / d
    margin = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (max(0, centre - margin) * 100, min(1, centre + margin) * 100)

def agg(trades):
    if not trades: return None
    N = len(trades)
    wins = sum(1 for t in trades if t.get("outcome") == "WIN")
    WR = 100 * wins / N
    pnls = [float(t.get("pnl_pips") or 0) for t in trades]
    EV = sum(pnls) / N
    return {"N": N, "wins": wins, "WR": WR, "EV": EV, "PnL": sum(pnls)}

def investigate(strat, pair):
    cells = [t for t in LIVE if t.get("entry_type") == strat and t.get("instrument") == pair and _is_wl(t.get("outcome"))]
    if not cells: return None

    out = [f"\n## {strat} × {pair}  (total W/L N={len(cells)})"]

    # Shadow split
    sh = [t for t in cells if int(t.get("is_shadow") or 0) == 1]
    lv = [t for t in cells if int(t.get("is_shadow") or 0) == 0]
    a_sh, a_lv = agg(sh), agg(lv)
    out.append(f"- shadow vs live: shadow N={len(sh)} WR={a_sh['WR']:.1f}% EV={a_sh['EV']:+.2f} | live N={len(lv)} WR={a_lv['WR']:.1f}% EV={a_lv['EV']:+.2f}" if a_sh and a_lv else f"- shadow {a_sh}, live {a_lv}")

    # Pre vs post-cutoff
    pre = [t for t in cells if _entry_date(t) <= CUTOFF]
    post = [t for t in cells if _entry_date(t) > CUTOFF]
    a_pre, a_post = agg(pre), agg(post)
    out.append(f"- pre/post-cutoff: pre(≤{CUTOFF}) N={len(pre)} WR={a_pre['WR']:.1f}% | post N={len(post)} WR={a_post['WR']:.1f}%" if a_pre and a_post else f"- pre {a_pre}, post {a_post}")

    # MFE/MAE
    wins = [t for t in cells if t.get("outcome") == "WIN"]
    losses = [t for t in cells if t.get("outcome") == "LOSS"]

    def _med(xs, key):
        vals = [float(t.get(key) or 0) for t in xs]
        if not vals: return 0.0
        return statistics.median(vals)

    out.append(f"- WIN  (N={len(wins)}): MFE_med={_med(wins,'mafe_favorable_pips'):.1f}p MAE_med={_med(wins,'mafe_adverse_pips'):.1f}p")
    out.append(f"- LOSS (N={len(losses)}): MFE_med={_med(losses,'mafe_favorable_pips'):.1f}p MAE_med={_med(losses,'mafe_adverse_pips'):.1f}p")

    # Immediate death rate (MFE<=0.5)
    if losses:
        imm = sum(1 for t in losses if float(t.get("mafe_favorable_pips") or 0) <= 0.5)
        out.append(f"- immediate death: {imm}/{len(losses)} = {pct(imm, len(losses)):.0f}% of LOSS")

    # regime distribution
    reg_counter = Counter((t.get("mtf_regime") or "?") for t in cells)
    vol_counter = Counter((t.get("mtf_vol_state") or "?") for t in cells)
    ali_counter = Counter((t.get("mtf_alignment") or "?") for t in cells)
    out.append(f"- mtf_regime dist: {dict(reg_counter.most_common(5))}")
    out.append(f"- mtf_vol_state dist: {dict(vol_counter.most_common(5))}")
    out.append(f"- mtf_alignment dist: {dict(ali_counter.most_common(5))}")

    # Session/hour
    hours = Counter()
    for t in cells:
        h = (t.get("entry_time") or "")[11:13]
        hours[h] += 1
    out.append(f"- hour dist (top 8): {dict(hours.most_common(8))}")

    # Spread at entry
    sprs = [float(t.get("spread_at_entry") or 0) for t in cells if t.get("spread_at_entry") is not None]
    if sprs:
        out.append(f"- spread_at_entry: med={statistics.median(sprs):.2f} p90={sorted(sprs)[int(0.9*len(sprs))]:.2f} max={max(sprs):.2f}")

    # Confidence distribution
    confs = [float(t.get("confidence") or 0) for t in cells]
    if confs:
        out.append(f"- confidence: med={statistics.median(confs):.1f} p10={sorted(confs)[max(0,int(0.1*len(confs))-1)]:.1f} p90={sorted(confs)[int(0.9*len(confs))-1]:.1f}")

    # Wilson 95% on total WR
    all_wins = sum(1 for t in cells if t.get("outcome") == "WIN")
    lo, hi = wilson(all_wins, len(cells))
    out.append(f"- Wilson 95%: [{lo:.1f}%, {hi:.1f}%]")

    return "\n".join(out)

# Generate report
lines = ["# BT vs Live Divergence — Mechanistic Investigation (2026-04-22)\n"]
lines.append(f"**Cutoff** for pre/post split: {CUTOFF}\n")
lines.append("## Investigation Protocol")
lines.append("- shadow/live split: Kelly learning contamination?")
lines.append("- pre/post-cutoff: regime-shift overfitting?")
lines.append("- MFE/MAE: SL too tight (WIN MAE=0 yet massive LOSS MFE=0) or TP too far (WIN MFE doesn't reach TP)?")
lines.append("- Immediate death ≥60%: entry timing bad (bad direction at entry)")
lines.append("- mtf_regime/vol/alignment: feature shift between BT sample and LIVE sample?")
lines.append("- hour dist: session gate drift?")
lines.append("- spread: friction gate drift?\n")

for strat, pair in TARGETS:
    res = investigate(strat, pair)
    if res: lines.append(res)

report = "\n".join(lines)
Path("/tmp/bt_divergence/mechanistic_report.md").write_text(report)
print(f"wrote /tmp/bt_divergence/mechanistic_report.md")
print()
print(report)
