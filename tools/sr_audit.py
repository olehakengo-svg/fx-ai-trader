"""S/R Anti-Hunt Edge Audit (Stage A — 統計的厳密性レビュー)

S78 監査メモ (knowledge-base/wiki/sessions/2026-04-27-session.md) に基づく
sr_anti_hunt_bounce / sr_liquidity_grab の hunt event エッジ評価。

## Stage A 内容

A1. Wilson 95% CI lower bound (BEV比較)
A2. Bonferroni 補正 — k=40 (4 tf × 5 pair × 2 side)
A3. BH-FDR 補正 — 探索 pool として
A4. Quarterly stability (4-window split)
A5. Benchmark net_edge — SR近接 全 bar reversal WR との差分

## Stage B (別タスク)

B1. Hunt event 毎の hypothetical trade simulation
    SL = hunt_extreme + 0.3 × ATR
    TP = MIN(対側SR, RR=1.5)
B2. friction_for(pair) 控除
B3. EV / PF / Sharpe / Kelly 計算

## Usage

    python3 tools/sr_audit.py --pair USD_JPY --side bull --window 365d \\
        --benchmark-mode all_bars

## Output

    raw/audits/sr_audit_<date>_<pair>_<side>.json
    raw/audits/sr_audit_<date>_<pair>_<side>.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Stats helpers (mirror tools/cell_edge_audit.py)
WILSON_Z_95 = 1.96
WILSON_Z_BF40 = 2.94   # k=40 Bonferroni: α=0.05/40 → two-sided z
WILSON_Z_BF624 = 3.94  # k=624 Bonferroni: ultra-strict


def wilson_lower(wins: int, n: int, z: float = WILSON_Z_95) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / den)


def wilson_upper(wins: int, n: int, z: float = WILSON_Z_95) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return min(1.0, (centre + spread) / den)


def binomial_two_sided_p(wins: int, n: int, p0: float = 0.5) -> float:
    """Normal approximation."""
    if n <= 0:
        return 1.0
    var = n * p0 * (1 - p0)
    if var <= 0:
        return 1.0
    z = (wins - n * p0) / math.sqrt(var)
    return max(0.0, min(1.0,
        2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2.0))))))


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """BH (FDR) adjusted p-values, returned in original order."""
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adj = [0.0] * n
    cum_min = 1.0
    for rank in range(n - 1, -1, -1):
        orig_idx, p = indexed[rank]
        bh = min(1.0, p * n / (rank + 1))
        cum_min = min(cum_min, bh)
        adj[orig_idx] = cum_min
    return adj


def quarterly_split(events: list[dict]) -> list[list[dict]]:
    """Split events into 4 quarters by entry_time (chronological)."""
    if not events:
        return [[], [], [], []]
    sorted_e = sorted(events, key=lambda e: e.get("entry_time", ""))
    n = len(sorted_e)
    q = n // 4
    return [
        sorted_e[:q],
        sorted_e[q:2*q],
        sorted_e[2*q:3*q],
        sorted_e[3*q:],
    ]


def stage_a_audit(events: list[dict],
                  benchmark_events: list[dict] | None = None,
                  k_bonferroni: int = 40) -> dict:
    """Stage A: 統計的厳密性レビュー.

    events: hunt event dicts with at least:
        - "reversal" (bool): 仮説通り反転したか
        - "entry_time" (str)
        - "instrument" (str)
        - "pnl_pips" (float, optional, Stage B 用)

    benchmark_events: SR近接 全 bar の reversal events
        (= hunt 検出無関係の baseline reversal rate)

    Returns dict with all Stage A metrics.
    """
    n = len(events)
    if n == 0:
        return {"n": 0, "verdict": "no_data"}

    wins = sum(1 for e in events if e.get("reversal"))
    wr = wins / n

    wL_95 = wilson_lower(wins, n, WILSON_Z_95)
    wL_bf40 = wilson_lower(wins, n, WILSON_Z_BF40)
    wL_bf624 = wilson_lower(wins, n, WILSON_Z_BF624)
    wU_95 = wilson_upper(wins, n, WILSON_Z_95)

    p_raw = binomial_two_sided_p(wins, n, 0.5)
    p_bonf = min(1.0, p_raw * k_bonferroni)

    # Benchmark net_edge: hunt-detected WR vs SR近接 全 bar reversal WR
    bench_n = len(benchmark_events) if benchmark_events else 0
    bench_wins = (sum(1 for e in benchmark_events if e.get("reversal"))
                  if benchmark_events else 0)
    bench_wr = (bench_wins / bench_n) if bench_n > 0 else None
    net_edge = (wr - bench_wr) if bench_wr is not None else None

    # Quarterly stability
    quarters = quarterly_split(events)
    quarter_wrs = []
    for qi, qe in enumerate(quarters):
        if not qe:
            quarter_wrs.append({"q": qi+1, "n": 0, "wr": None})
            continue
        qwins = sum(1 for e in qe if e.get("reversal"))
        quarter_wrs.append({"q": qi+1, "n": len(qe),
                            "wr": round(qwins / len(qe) * 100, 1)})
    active = [q for q in quarter_wrs if q["n"] >= 5]
    if len(active) >= 3:
        evs = [q["wr"] for q in active]
        mu = sum(evs) / len(evs)
        sigma = (sum((e-mu)**2 for e in evs) / len(evs)) ** 0.5
        cv = sigma / abs(mu) if abs(mu) > 0.01 else None
        qstab_verdict = ("stable" if cv is not None and cv < 0.5
                         else "borderline" if cv is not None and cv < 1.0
                         else "unstable")
    else:
        cv = None
        qstab_verdict = "insufficient_data"

    # Promotion verdict (Stage A only — Stage B EV check は別)
    pass_strict = (wL_bf40 > 0.50 and p_bonf < 0.05
                   and (net_edge is None or net_edge > 0.05))
    pass_lenient = (wL_95 > 0.50 and p_raw < 0.05
                    and (net_edge is None or net_edge > 0.05))

    return {
        "n": n,
        "wins": wins,
        "wr": round(wr * 100, 2),
        "wilson_lower_95": round(wL_95 * 100, 2),
        "wilson_upper_95": round(wU_95 * 100, 2),
        "wilson_lower_bf40": round(wL_bf40 * 100, 2),
        "wilson_lower_bf624": round(wL_bf624 * 100, 2),
        "p_value_raw": round(p_raw, 5),
        "p_value_bonferroni": round(p_bonf, 5),
        "k_bonferroni": k_bonferroni,
        "benchmark": {
            "n": bench_n,
            "wr": round(bench_wr * 100, 2) if bench_wr is not None else None,
            "net_edge_pp": round(net_edge * 100, 2) if net_edge is not None else None,
        },
        "quarters": quarter_wrs,
        "quarterly_cv": round(cv, 3) if cv is not None else None,
        "quarterly_verdict": qstab_verdict,
        "verdict_strict": pass_strict,
        "verdict_lenient": pass_lenient,
    }


def stage_b_simulation(events: list[dict],
                        pair: str,
                        rr_target: float = 1.5,
                        sl_buffer_atr_mult: float = 0.3) -> dict:
    """Stage B: hypothetical trade simulation per hunt event.

    Each event must have:
      - hunt_extreme (float): worst price reached during hunt
      - opposite_sr (float): nearest SR on the opposite side (for TP cap)
      - atr_pips (float): ATR at the time of hunt
      - direction (str): "BUY"/"SELL" (post-hunt entry direction)
      - entry_price (float): assumed entry price
      - actual_outcome (str, optional): "WIN"/"LOSS" if known
      - actual_pnl_pips (float, optional)

    Computes:
      - SL distance = hunt_extreme + sl_buffer_atr_mult * atr_pips (in pips)
      - TP distance = MIN(|opposite_sr - entry_price|, rr_target * SL_dist)
      - RR realized
      - friction_for(pair) 控除後 EV
      - PF, Sharpe (over events)
    """
    if not events:
        return {"n": 0, "verdict": "no_data"}

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from modules.friction_model_v2 import friction_for
        f = friction_for(pair, mode="DT")
        friction_pip = f.get("adjusted_rt_pips", 2.0) if not f.get("unsupported") else 2.0
    except Exception:
        friction_pip = 2.0

    sims = []
    for e in events:
        hunt = e.get("hunt_extreme")
        sr_opp = e.get("opposite_sr")
        atr = e.get("atr_pips", 0)
        direction = (e.get("direction") or "").upper()
        entry = e.get("entry_price", 0)
        if not all([hunt, sr_opp, atr > 0, direction, entry]):
            continue
        # SL pips = distance from entry to hunt_extreme + buffer
        sl_pip = abs(entry - hunt) * (100 if "JPY" in pair else 10000) + sl_buffer_atr_mult * atr
        if sl_pip <= 0:
            continue
        # TP pips = min(|opposite SR - entry|, RR * SL)
        tp_dist = abs(sr_opp - entry) * (100 if "JPY" in pair else 10000)
        tp_pip = min(tp_dist, rr_target * sl_pip)
        if tp_pip <= 0:
            continue
        rr_realized = tp_pip / sl_pip
        # Outcome: prefer actual; fallback to reversal proxy
        if e.get("actual_outcome") == "WIN":
            pnl = tp_pip
        elif e.get("actual_outcome") == "LOSS":
            pnl = -sl_pip
        elif e.get("reversal") is True:
            pnl = tp_pip * 0.7  # conservative haircut for partial-fills
        elif e.get("reversal") is False:
            pnl = -sl_pip
        else:
            continue
        sims.append({"sl_pip": sl_pip, "tp_pip": tp_pip,
                     "rr": rr_realized, "pnl_raw": pnl,
                     "pnl_net": pnl - friction_pip})

    if not sims:
        return {"n": 0, "verdict": "no_simulatable_events"}

    n = len(sims)
    pnls_net = [s["pnl_net"] for s in sims]
    avg_net = sum(pnls_net) / n
    var = sum((p - avg_net)**2 for p in pnls_net) / n
    sd = math.sqrt(var) if var > 0 else 1e-9
    sharpe = avg_net / sd
    wins = [p for p in pnls_net if p > 0]
    losses = [p for p in pnls_net if p <= 0]
    gw = sum(wins); gl = -sum(losses) or 1e-9
    pf = gw / gl
    aw = (sum(wins) / len(wins)) if wins else 0
    al = (sum(losses) / len(losses)) if losses else 0
    p_win = len(wins) / n
    b = -aw / al if al < 0 else 1
    kelly = (p_win * (b + 1) - 1) / b if b > 0 else 0

    return {
        "n": n,
        "friction_pip": round(friction_pip, 3),
        "rr_target": rr_target,
        "sl_buffer_atr_mult": sl_buffer_atr_mult,
        "avg_sl_pip": round(sum(s["sl_pip"] for s in sims) / n, 2),
        "avg_tp_pip": round(sum(s["tp_pip"] for s in sims) / n, 2),
        "avg_rr": round(sum(s["rr"] for s in sims) / n, 2),
        "avg_pnl_net_pip": round(avg_net, 3),
        "sum_pnl_net_pip": round(sum(pnls_net), 1),
        "sharpe": round(sharpe, 4),
        "profit_factor": round(pf, 3),
        "kelly_fraction": round(kelly, 4),
        "win_rate": round(p_win * 100, 2),
        "verdict_ev_positive": avg_net > 0,
        "verdict_pf_above_1": pf > 1.0,
        "verdict_kelly_positive": kelly > 0,
    }


def render_markdown(audit: dict, pair: str, side: str, window: str,
                    stage_b: dict | None = None) -> str:
    """Render Stage A audit to markdown."""
    if audit.get("verdict") == "no_data":
        return f"# S/R Audit ({pair} {side} {window})\n\n**No data.**\n"

    bench = audit["benchmark"]
    lines = [
        f"# S/R Anti-Hunt Audit Stage A — {pair} {side} ({window})",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Sample",
        f"- Hunt events: **{audit['n']}**",
        f"- Reversals: {audit['wins']}",
        f"- Hunt-detected WR: **{audit['wr']:.2f}%**",
        "",
        "## Wilson CI",
        f"- 95% lower: {audit['wilson_lower_95']:.2f}%",
        f"- 95% upper: {audit['wilson_upper_95']:.2f}%",
        f"- Bonferroni-40 lower (k=40, z=2.94): **{audit['wilson_lower_bf40']:.2f}%**",
        f"- Bonferroni-624 lower (z=3.94, ultra-strict): {audit['wilson_lower_bf624']:.2f}%",
        "",
        "## Hypothesis Test",
        f"- Two-sided binomial p (raw): {audit['p_value_raw']:.4f}",
        f"- Bonferroni-{audit['k_bonferroni']} adjusted p: **{audit['p_value_bonferroni']:.4f}**",
        "",
        "## Benchmark net_edge",
    ]
    if bench["wr"] is not None:
        lines += [
            f"- SR近接 全 bar reversal WR (baseline): {bench['wr']:.2f}% (N={bench['n']})",
            f"- net_edge (hunt - baseline): **{bench['net_edge_pp']:+.2f} pp**",
        ]
    else:
        lines.append("- (benchmark events not provided)")

    lines += ["", "## Quarterly Stability"]
    for q in audit["quarters"]:
        wr = f"{q['wr']:.1f}%" if q["wr"] is not None else "—"
        lines.append(f"- Q{q['q']}: N={q['n']} WR={wr}")
    if audit["quarterly_cv"] is not None:
        lines.append(f"- CV across active quarters: {audit['quarterly_cv']:.3f}")
    lines.append(f"- Verdict: **{audit['quarterly_verdict']}**")

    lines += ["", "## Promotion Verdict (Stage A only)"]
    if audit["verdict_strict"]:
        lines.append("🟢 **STRICT** — Wilson_BF40 > 50% AND p_bonf < 0.05 AND net_edge > 5pp")
    elif audit["verdict_lenient"]:
        lines.append("🟡 **LENIENT** — Wilson95 > 50% AND p_raw < 0.05 AND net_edge > 5pp")
    else:
        lines.append("⚪ **NOT YET** — see Wilson_BF40 / p_bonf / net_edge above")

    if stage_b and stage_b.get("n", 0) > 0:
        b = stage_b
        lines += ["", "## Stage B — Hypothetical Trade Simulation", "",
                  f"- Friction (pair-specific): {b['friction_pip']:.2f}pip",
                  f"- SL buffer: hunt_extreme + {b['sl_buffer_atr_mult']}×ATR",
                  f"- TP: MIN(対側SR, RR={b['rr_target']}×SL)",
                  f"- Avg SL: {b['avg_sl_pip']:.2f}pip / Avg TP: {b['avg_tp_pip']:.2f}pip / Avg RR: {b['avg_rr']:.2f}",
                  f"- **avg_pnl_net (post-friction): {b['avg_pnl_net_pip']:+.2f}pip**",
                  f"- Sum PnL: {b['sum_pnl_net_pip']:+.1f}pip / WR: {b['win_rate']:.1f}%",
                  f"- Profit Factor: {b['profit_factor']:.2f}",
                  f"- Sharpe: {b['sharpe']:.3f}",
                  f"- Kelly fraction: {b['kelly_fraction']:.4f}",
                  ""]
        ev_ok = "✓" if b["verdict_ev_positive"] else "✗"
        pf_ok = "✓" if b["verdict_pf_above_1"] else "✗"
        ke_ok = "✓" if b["verdict_kelly_positive"] else "✗"
        lines += [f"- EV>0: {ev_ok} / PF>1: {pf_ok} / Kelly>0: {ke_ok}", ""]

    lines += ["", "## Next Steps", "",
              "1. (Stage A 失敗) → 4週間 N 蓄積後再 audit",
              "2. (Stage A 通過 ∧ Stage B EV>0 ∧ PF>1 ∧ Kelly>0) → Pre-reg LOCK 起案",
              "3. (Stage A 通過 ∧ Stage B EV<0) → SL/TP パラメータ感度分析 (RR を 1.0/2.0 で試行)",
              "4. Pre-reg LOCK 通過 → tier_master.json に追加 + lot=0.01 mini-pilot",
              ""]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--events-json", required=True,
                        help="Path to hunt events JSON (list of dicts with reversal/entry_time/instrument)")
    parser.add_argument("--benchmark-json", default=None,
                        help="Optional baseline events JSON for net_edge calc")
    parser.add_argument("--pair", default="USD_JPY")
    parser.add_argument("--side", default="bull", choices=["bull", "bear", "both"])
    parser.add_argument("--window", default="365d")
    parser.add_argument("--bonferroni-k", type=int, default=40,
                        help="Bonferroni multiplicity (default 40 = 4tf×5pair×2side)")
    parser.add_argument("--rr-target", type=float, default=1.5,
                        help="Stage B: TP target RR (default 1.5)")
    parser.add_argument("--sl-buffer-atr", type=float, default=0.3,
                        help="Stage B: SL buffer in ATR multiples beyond hunt_extreme")
    parser.add_argument("--out-dir", default="raw/audits")
    args = parser.parse_args()

    events = json.loads(Path(args.events_json).read_text())
    if isinstance(events, dict):
        events = events.get("events", [])
    bench = None
    if args.benchmark_json:
        bench_data = json.loads(Path(args.benchmark_json).read_text())
        bench = bench_data.get("events", []) if isinstance(bench_data, dict) else bench_data

    audit = stage_a_audit(events, benchmark_events=bench,
                          k_bonferroni=args.bonferroni_k)

    # Stage B: only run if events have hypothetical trade fields
    stage_b = None
    if events and any("hunt_extreme" in e for e in events[:5]):
        stage_b = stage_b_simulation(events, pair=args.pair,
                                      rr_target=args.rr_target,
                                      sl_buffer_atr_mult=args.sl_buffer_atr)

    today = datetime.now(timezone.utc).date().isoformat()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{today}_{args.pair}_{args.side}_{args.window}"
    json_path = out_dir / f"sr_audit{suffix}.json"
    md_path = out_dir / f"sr_audit{suffix}.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pair": args.pair, "side": args.side, "window": args.window,
        "k_bonferroni": args.bonferroni_k,
        "stage_a": audit,
    }
    if stage_b is not None:
        payload["stage_b"] = stage_b
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    md_path.write_text(render_markdown(audit, args.pair, args.side, args.window,
                                        stage_b=stage_b))

    print(f"[sr_audit] Stage A: N={audit['n']} WR={audit.get('wr')}% "
          f"Wilson_BF40={audit.get('wilson_lower_bf40')}% "
          f"p_bonf={audit.get('p_value_bonferroni')}")
    print(f"[sr_audit] Stage A verdict: strict={audit.get('verdict_strict')} "
          f"lenient={audit.get('verdict_lenient')}")
    if stage_b:
        print(f"[sr_audit] Stage B: avg_net={stage_b.get('avg_pnl_net_pip')}pip "
              f"PF={stage_b.get('profit_factor')} Kelly={stage_b.get('kelly_fraction')}")
    print(f"[sr_audit] Output: {json_path} + {md_path}")


if __name__ == "__main__":
    sys.exit(main() or 0)
