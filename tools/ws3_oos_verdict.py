#!/usr/bin/env python3
"""WS3 方向性非対称 OOS 検証 — pre-reg §4 の機械判定 (rule:R1 stage-1)

仕様 (変更禁止): knowledge-base/wiki/decisions/ws3-asymmetry-oos-prereg-2026-07-09.md
入力: ws3_mfe_scan.py --out-suffix _oos_2024_2025 の per-entry checkpoint JSON
判定: セル毎 median(MFE)/median(MAE) @ 型別 primary horizon、
      日次ブロックブートストラップ B=10,000 → p=P(ratio<=1)、BH-FDR q=0.10 (m=8)
      PASS = FDR ∧ ratio>=1.2 ∧ N>=30

実行: python3 tools/ws3_oos_verdict.py --entries <checkpoint.json>
"""

import argparse
import json
import os
from datetime import datetime, timezone

# pre-reg §2 固定 (変更禁止): (entry_type, pair) -> primary horizon
CANDIDATES = {
    ("htf_false_breakout", "EUR_JPY"): 24,
    ("trendline_sweep", "EUR_USD"): 24,
    ("dt_sr_channel_reversal", "EUR_USD"): 24,
    ("london_fix_reversal", "EUR_USD"): 24,
    ("htf_false_breakout", "AUD_JPY"): 24,
    ("lin_reg_channel", "EUR_USD"): 96,
    ("hull_donchian_fade", "EUR_USD"): 24,
    ("dt_fib_reversal", "USD_JPY"): 96,
}
EXPLORATION_RATIO = {  # 探索標本の参照値 (記述用)
    ("htf_false_breakout", "EUR_JPY"): 1.81,
    ("trendline_sweep", "EUR_USD"): 1.65,
    ("dt_sr_channel_reversal", "EUR_USD"): 1.55,
    ("london_fix_reversal", "EUR_USD"): 1.51,
    ("htf_false_breakout", "AUD_JPY"): 1.39,
    ("lin_reg_channel", "EUR_USD"): 1.94,   # h96
    ("hull_donchian_fade", "EUR_USD"): 1.30,
    ("dt_fib_reversal", "USD_JPY"): 2.05,   # h96
}
N_BOOT = 10000
SEED = 20260709
FDR_Q = 0.10
RATIO_FLOOR = 1.2
MIN_N = 30

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(REPO, "knowledge-base", "raw", "bt-results",
                        "ws3_asymmetry_oos_2026_07.json")
OUT_MD = os.path.join(REPO, "knowledge-base", "raw", "bt-results",
                      "ws3_asymmetry_oos_2026_07.md")


def bh_fdr(pvals: dict, q: float) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    cutoff = 0
    for rank, (_, p) in enumerate(items, 1):
        if p <= q * rank / m:
            cutoff = rank
    return {k: {"p": p, "rank": r, "bh_threshold": round(q * r / m, 5),
                "survive": r <= cutoff}
            for r, (k, p) in enumerate(items, 1)}


def cell_stats(rows: list, h: int, rng) -> dict:
    """median-ratio + 日次ブロックブートストラップ p (pre-reg §4)"""
    import numpy as np
    mfe = np.array([r[f"mfe_{h}"] for r in rows], dtype=float)
    mae = np.array([r[f"mae_{h}"] for r in rows], dtype=float)
    med_mae = float(np.median(mae))
    ratio = float(np.median(mfe) / med_mae) if med_mae > 0 else None
    by_day = {}
    for r in rows:
        by_day.setdefault(r["entry_time"][:10], []).append(
            (r[f"mfe_{h}"], r[f"mae_{h}"]))
    days = [np.array(v, dtype=float) for v in by_day.values()]
    nd = len(days)
    boots = []
    for _ in range(N_BOOT):
        idx = rng.integers(0, nd, size=nd)
        cat = np.concatenate([days[i] for i in idx])
        dm = np.median(cat[:, 1])
        boots.append(np.median(cat[:, 0]) / dm if dm > 0 else np.inf)
    boots = np.asarray(boots)
    p = (1 + int((boots <= 1.0).sum())) / (N_BOOT + 1)
    # lag-1 ρ (ナイフエッジ #2 記録用): entry順の mfe-mae 差
    d = mfe - mae
    rho = float(np.corrcoef(d[:-1], d[1:])[0, 1]) if len(d) > 2 else None
    return {"n": len(rows), "n_days": nd,
            "mfe_p50": round(float(np.median(mfe)), 2),
            "mae_p50": round(med_mae, 2),
            "ratio": round(ratio, 4) if ratio else None,
            "boot_p": round(float(p), 6),
            "boot_ci_lo": round(float(np.percentile(boots, 5)), 3),
            "lag1_rho": round(rho, 4) if rho is not None else None}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--entries", required=True,
                    help="OOS scan の per-entry checkpoint JSON パス")
    args = ap.parse_args()
    import numpy as np
    entries = json.load(open(args.entries))
    rng = np.random.default_rng(SEED)

    cells = {}
    for r in entries:
        cells.setdefault((r["entry_type"], r["pair"]), []).append(r)

    analysis, pvals = {}, {}
    for cand, h in CANDIDATES.items():
        key = f"{cand[0]}__{cand[1]}"
        rows = cells.get(cand, [])
        if not rows:
            analysis[key] = {"n": 0, "note": "OOS エントリーゼロ"}
            continue
        s = cell_stats(rows, h, rng)
        # ナイフエッジ #3: 隣接 horizon の ratio (記述)
        adj = {}
        for ha in (12, 24, 48, 96):
            m = np.array([r[f"mfe_{ha}"] for r in rows], dtype=float)
            a = np.array([r[f"mae_{ha}"] for r in rows], dtype=float)
            am = float(np.median(a))
            adj[f"h{ha}"] = round(float(np.median(m)) / am, 3) if am > 0 else None
        s.update({"primary_h": h, "adjacent_ratios": adj,
                  "exploration_ratio": EXPLORATION_RATIO[cand]})
        analysis[key] = s
        if s["ratio"] is not None:
            pvals[key] = s["boot_p"]

    fdr = bh_fdr(pvals, FDR_Q) if pvals else {}
    passing = []
    for key, f in fdr.items():
        s = analysis[key]
        s["gates"] = {
            "a_fdr": f["survive"],
            "b_ratio_floor": bool(s["ratio"] is not None and s["ratio"] >= RATIO_FLOOR),
            "c_min_n": bool(s["n"] >= MIN_N),
        }
        s["gates"]["pass"] = all(s["gates"].values())
        if s["gates"]["pass"]:
            passing.append(key)

    verdict = "PASS" if passing else "FAIL"
    out = {
        "task": "20260709-0420-ws3-asymmetry-oos-verification",
        "prereg": "knowledge-base/wiki/decisions/ws3-asymmetry-oos-prereg-2026-07-09.md",
        "rule": "R1 stage-1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "oos_window": "2024-07-07..2025-07-07 (truncated-parquet worktree, lookback 365d)",
        "n_boot": N_BOOT, "seed": SEED, "fdr_q": FDR_Q,
        "ratio_floor": RATIO_FLOOR, "min_n": MIN_N,
        "mechanical_verdict": verdict,
        "passing_cells": passing,
        "bh_fdr": fdr,
        "cells": analysis,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    lines = [
        "# WS3 方向性非対称 OOS 検証 (機械判定、pre-reg §4)",
        "",
        f"- 生成: {out['generated_utc']} / verdict(機械): **{verdict}** / "
        f"OOS 窓: {out['oos_window']}",
        f"- PASS = BH-FDR q={FDR_Q} (m={len(CANDIDATES)}) ∧ ratio≥{RATIO_FLOOR} ∧ N≥{MIN_N}",
        "",
        "| cell | H | N | OOS ratio | 探索 ratio | p | FDR | CI5% | PASS |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for key, s in analysis.items():
        if s.get("n", 0) == 0:
            lines.append(f"| {key} | — | 0 | — | — | — | — | — | no-entry |")
            continue
        f_ = fdr.get(key, {})
        g = s.get("gates", {})
        lines.append(
            f"| {key} | h{s['primary_h']} | {s['n']} | **{s['ratio']}** "
            f"| {s['exploration_ratio']} | {s['boot_p']} "
            f"| {'✓' if f_.get('survive') else '✗'} | {s['boot_ci_lo']} "
            f"| {'**PASS**' if g.get('pass') else 'fail'} |")
    lines += ["", "隣接 horizon ratio・lag-1 ρ は JSON 参照。", ""]
    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines))
    print(json.dumps({"mechanical_verdict": verdict, "passing_cells": passing},
                     ensure_ascii=False))
    print(f"saved: {OUT_JSON}\nsaved: {OUT_MD}")


if __name__ == "__main__":
    main()
