#!/usr/bin/env python3
"""WS3 round-2 OOS verdict — pre-reg §3 の機械判定 (rule:R1)

仕様 (変更禁止): knowledge-base/wiki/decisions/ws3-round2-explore-prereg-2026-07-10.md
§2b (LOCK 2026-07-10、m=5、grid/摩擦/型/primary horizon 凍結) + §3 (2 レグ判定)。

2 モード (stage-2 §3 と同じ執行順序 — エントリー抽出→N 凍結を判定より先に):
  --freeze   OOS エントリーを集約し per-cell N を凍結保存。判定統計は一切計算しない。
             入力 = stage-1 凍結資産 ws3_asymmetry_oos_2026_07_entries.json
             (EUR_USD / USD_JPY セル) + .ws3_mfe_scan_checkpoint_round2_oos.json
             (GBP_USD / GBP_JPY セル — 切詰め parquet 環境で新規抽出)
  --verdict  凍結済みエントリーを読み §3 の 2 レグ + ナイフエッジを機械計算。

判定 (§3、全て充足で PASS):
  (A) ratio レグ: median-ratio 日次ブロックブートストラップ (B=10,000、seed=20260709、
      round-1 判定器 tools/ws3_oos_verdict.py の cell_stats/bh_fdr を import 流用)
      → BH-FDR q=0.10 (m=5) ∧ point ratio≥1.2 ∧ N≥30。型別 primary horizon 固定
  (B) EV レグ: §2b 凍結 grid (再アンカー禁止) の OOS first-touch 摩擦調整 EV
      → best 構成の 3×3 近傍平均 ≥ +0.5 p/t ∧ 隣接 (Manhattan 距離1) の過半 EV>0
  ナイフエッジ3点 (stage-2 §5 準拠): 擬似反復 = 日次ブロック設計 + lag-1 ρ 記録 /
      孤立格子点 = (B) の隣接過半 / fold 集中 = best 構成 3-fold + LOFO>0 (gate)。
      EV' (timeout pnl→0) は記録 (Secondary、§2b 事前認識)
ep 復元: EV スクリーンと同一の恒等式復元 + 双方向照合 (fail-loud、許容 0.02p)。

実行:
  python3 tools/ws3_round2_oos_verdict.py --freeze
  python3 tools/ws3_round2_oos_verdict.py --verdict
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_DIR = os.path.join(REPO, "knowledge-base", "raw", "bt-results")
STAGE1_ENTRIES = os.path.join(BT_DIR, "ws3_asymmetry_oos_2026_07_entries.json")
R2_OOS_CHECKPOINT = os.path.join(BT_DIR, ".ws3_mfe_scan_checkpoint_round2_oos.json")
FROZEN = os.path.join(BT_DIR, "ws3_round2_oos_entries.json")
OUT_JSON = os.path.join(BT_DIR, "ws3_round2_oos_2026_07.json")
OUT_MD = os.path.join(BT_DIR, "ws3_round2_oos_2026_07.md")
PARQUET_DIR = os.path.join(REPO, "data", "cache", "massive")  # OOS 切詰め版

# ── pre-reg §2b 固定 (LOCK 2026-07-10、変更禁止) ──
# cell: (entry_type, pair, sig|None) / h: primary horizon / grid: 凍結 / friction: 凍結
CELLS = [
    {"entry_type": "sr_fib_confluence", "pair": "GBP_USD", "sig": "SELL",
     "type": "持続", "h": 96, "tp_grid": [47, 76, 111], "sl_grid": [28, 62, 81],
     "friction": 4.53, "explore_ratio": 1.656, "source": "r2_oos_checkpoint"},
    {"entry_type": "vol_spike_mr", "pair": "USD_JPY", "sig": "BUY",
     "type": "減衰", "h": 24, "tp_grid": [29, 43, 71], "sl_grid": [20, 32, 63],
     "friction": 2.14, "explore_ratio": 1.49, "source": "stage1_entries"},
    {"entry_type": "sr_fib_confluence", "pair": "EUR_USD", "sig": "SELL",
     "type": "持続", "h": 96, "tp_grid": [34, 53, 70], "sl_grid": [23, 42, 74],
     "friction": 2.00, "explore_ratio": 1.487, "source": "stage1_entries"},
    {"entry_type": "vsg_jpy_reversal", "pair": "GBP_JPY", "sig": "SELL",
     "type": "減衰", "h": 24, "tp_grid": [35, 57, 86], "sl_grid": [24, 43, 64],
     "friction": 4.53, "explore_ratio": 1.482, "source": "r2_oos_checkpoint"},
    {"entry_type": "dt_sr_channel_reversal", "pair": "GBP_JPY", "sig": "BUY",
     "type": "持続", "h": 96, "tp_grid": [67, 105, 127], "sl_grid": [51, 83, 132],
     "friction": 4.53, "explore_ratio": 1.327, "source": "r2_oos_checkpoint"},
]
FDR_Q = 0.10
RATIO_FLOOR = 1.2
MIN_N = 30
NB_MEAN_FLOOR = 0.5   # §3(B) best 3×3 近傍平均 ≥ +0.5 p/t
RECON_TOL_PIP = 0.02


def _pip(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


def _cell_key(c) -> str:
    return f"{c['entry_type']}×{c['pair']}" + (f"×{c['sig']}" if c["sig"] else "")


def _match(c, r) -> bool:
    return (r["entry_type"] == c["entry_type"] and r["pair"] == c["pair"]
            and (c["sig"] is None or r["sig"] == c["sig"]))


def first_touch(hi, lo, cl, ep, sig, tp_px, sl_px):
    """stage-2 barrier sim と同形 (SL 優先 / timeout=最終バー close)"""
    d = 1.0 if sig == "BUY" else -1.0
    tp_lvl = ep + d * tp_px
    sl_lvl = ep - d * sl_px
    for i in range(len(hi)):
        hit_tp = hi[i] >= tp_lvl if d > 0 else lo[i] <= tp_lvl
        hit_sl = lo[i] <= sl_lvl if d > 0 else hi[i] >= sl_lvl
        if hit_tp and hit_sl:
            return -sl_px, "sl"
        if hit_sl:
            return -sl_px, "sl"
        if hit_tp:
            return tp_px, "tp"
    return (cl[-1] - ep) * d, "timeout"


def run_freeze() -> None:
    stage1 = json.load(open(STAGE1_ENTRIES))
    r2 = json.load(open(R2_OOS_CHECKPOINT))
    frozen, n_by_cell = [], {}
    for c in CELLS:
        src = stage1 if c["source"] == "stage1_entries" else r2
        rows = [r for r in src if _match(c, r)]
        for r in rows:
            frozen.append({**r, "cell": _cell_key(c)})
        n_by_cell[_cell_key(c)] = len(rows)
    out = {
        "prereg": "ws3-round2-explore-prereg-2026-07-10.md §3 (LOCK)",
        "mode": "freeze (判定統計は未計算 — stage-2 §3 執行順序)",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "oos_window": "2024-07-07..2025-07-07 (truncated-parquet, lookback 365d)",
        "sources": {
            "stage1_entries": os.path.relpath(STAGE1_ENTRIES, REPO),
            "r2_oos_checkpoint": os.path.relpath(R2_OOS_CHECKPOINT, REPO),
        },
        "n_by_cell": n_by_cell,
        "entries": frozen,
    }
    with open(FROZEN, "w") as f:
        json.dump(out, f, ensure_ascii=False)
    print(json.dumps({"mode": "freeze", "n_by_cell": n_by_cell}, ensure_ascii=False))
    print(f"saved: {FROZEN}")


def run_verdict() -> None:
    import numpy as np
    import pandas as pd
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import ws3_oos_verdict as r1judge  # round-1 判定器流用 (cell_stats/bh_fdr/SEED/N_BOOT)

    frozen = json.load(open(FROZEN))
    entries = frozen["entries"]
    rng = np.random.default_rng(r1judge.SEED)

    dfs = {}
    for pair in sorted({c["pair"] for c in CELLS}):
        dfs[pair] = pd.read_parquet(os.path.join(PARQUET_DIR, f"{pair}_15m.parquet"))

    analysis, pvals = {}, {}
    recon_fail_total = 0
    for c in CELLS:
        key = _cell_key(c)
        rows = [r for r in entries if r["cell"] == key]
        n = len(rows)
        s = {"cell": key, "type": c["type"], "primary_h": c["h"],
             "explore_ratio": c["explore_ratio"], "n": n,
             "friction": c["friction"],
             "tp_grid": c["tp_grid"], "sl_grid": c["sl_grid"]}
        if n == 0:
            s["note"] = "OOS エントリーゼロ"
            analysis[key] = s
            continue

        # ── レグ A: ratio (round-1 判定器の cell_stats を流用) ──
        s.update(r1judge.cell_stats(rows, c["h"], rng))
        adj = {}
        for ha in (12, 24, 48, 96):
            m = np.array([r[f"mfe_{ha}"] for r in rows], dtype=float)
            a = np.array([r[f"mae_{ha}"] for r in rows], dtype=float)
            am = float(np.median(a))
            adj[f"h{ha}"] = round(float(np.median(m)) / am, 3) if am > 0 else None
        s["adjacent_horizon_ratios"] = adj
        if s.get("ratio") is not None:
            pvals[key] = s["boot_p"]

        # ── レグ B: 凍結 grid first-touch EV ──
        df = dfs[c["pair"]]
        idx = df.index
        pip = _pip(c["pair"])
        hi_a, lo_a, cl_a = df["High"].values, df["Low"].values, df["Close"].values
        H = c["h"]
        sim_rows, recon_fail = [], 0
        for r in rows:
            ts = pd.Timestamp(r["entry_time"])
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            pos = idx.searchsorted(ts)
            if pos >= len(idx) or idx[pos] != ts:
                recon_fail += 1
                continue
            ep_pos = pos + 1
            w96 = slice(ep_pos, min(ep_pos + 96 + 1, len(idx)))
            hi96, lo96 = hi_a[w96], lo_a[w96]
            d = 1.0 if r["sig"] == "BUY" else -1.0
            if d > 0:
                ep = float(np.max(hi96)) - r["mfe_96"] * pip
                ep_alt = float(np.min(lo96)) + r["mae_96"] * pip
            else:
                ep = float(np.min(lo96)) + r["mfe_96"] * pip
                ep_alt = float(np.max(hi96)) - r["mae_96"] * pip
            w24 = slice(ep_pos, min(ep_pos + 24 + 1, len(idx)))
            hi24, lo24 = hi_a[w24], lo_a[w24]
            if d > 0:
                mfe24 = (float(np.max(hi24)) - ep) / pip
                mae24 = (ep - float(np.min(lo24))) / pip
            else:
                mfe24 = (ep - float(np.min(lo24))) / pip
                mae24 = (float(np.max(hi24)) - ep) / pip
            if (abs(ep - ep_alt) / pip > RECON_TOL_PIP
                    or abs(mfe24 - r["mfe_24"]) > RECON_TOL_PIP
                    or abs(mae24 - r["mae_24"]) > RECON_TOL_PIP):
                recon_fail += 1
                continue
            if ep_pos + H > len(idx):
                recon_fail += 1
                continue
            sim_rows.append({"ep": ep, "ep_pos": ep_pos, "sig": r["sig"]})
        recon_fail_total += recon_fail
        s["recon_fail"] = recon_fail

        configs = [(tp, sl) for tp in c["tp_grid"] for sl in c["sl_grid"]]
        pnl = {cfg: [] for cfg in configs}
        leg = {cfg: [] for cfg in configs}
        for x in sim_rows:
            sl_ = slice(x["ep_pos"], x["ep_pos"] + H)
            hi, lo, cl = hi_a[sl_], lo_a[sl_], cl_a[sl_]
            for (tp, sl) in configs:
                p, lg = first_touch(hi, lo, cl, x["ep"], x["sig"],
                                    tp * pip, sl * pip)
                pnl[(tp, sl)].append(p / pip)
                leg[(tp, sl)].append(lg)
        n_sim = len(pnl[configs[0]])
        fr = c["friction"]
        ev = {cfg: (float(np.mean(v)) - fr if v else None) for cfg, v in pnl.items()}
        ev_arr = [ev[cfg] for cfg in configs]
        best_i = int(np.argmax([e if e is not None else -1e9 for e in ev_arr]))
        bt_, bs_ = configs[best_i]
        ti, si = best_i // 3, best_i % 3
        nb_all_idx = [(a, b) for a in range(max(0, ti - 1), min(3, ti + 2))
                      for b in range(max(0, si - 1), min(3, si + 2))]
        nb_mean = float(np.mean([ev_arr[a * 3 + b] for a, b in nb_all_idx])) if n_sim else None
        adj_idx = [(a, b) for (a, b) in
                   [(ti - 1, si), (ti + 1, si), (ti, si - 1), (ti, si + 1)]
                   if 0 <= a < 3 and 0 <= b < 3]
        adj_evs = [ev_arr[a * 3 + b] for a, b in adj_idx]
        n_pos = sum(1 for e in adj_evs if e is not None and e > 0)

        # ナイフエッジ: fold 集中 (best 構成 3-fold + LOFO) / EV' (記録)
        best_pnl = np.array(pnl[(bt_, bs_)]) - fr
        best_legs = leg[(bt_, bs_)]
        folds = np.array_split(np.arange(n_sim), 3) if n_sim >= 3 else []
        fold_ev = [float(best_pnl[f].mean()) for f in folds if len(f)]
        lofo = None
        if len(fold_ev) == 3:
            w = int(np.argmax(fold_ev))
            rest = np.concatenate([folds[j] for j in range(3) if j != w])
            lofo = float(best_pnl[rest].mean())
        evp = (float(np.mean([(-fr if lg == "timeout" else v)
                              for v, lg in zip(best_pnl, best_legs)]))
               if n_sim else None)
        pnl_lag1 = (float(np.corrcoef(best_pnl[:-1], best_pnl[1:])[0, 1])
                    if n_sim > 2 and np.std(best_pnl) > 0 else None)

        s["ev_leg"] = {
            "n_sim": n_sim,
            "best_config": f"tp{bt_}_sl{bs_}",
            "best_ev_adj": round(ev_arr[best_i], 3) if ev_arr[best_i] is not None else None,
            "nb3x3_mean_ev": round(nb_mean, 3) if nb_mean is not None else None,
            "adjacent_positive": f"{n_pos}/{len(adj_evs)}",
            "best_tp_rate": round(best_legs.count("tp") / n_sim, 3) if n_sim else None,
            "best_sl_rate": round(best_legs.count("sl") / n_sim, 3) if n_sim else None,
            "best_timeout_rate": round(best_legs.count("timeout") / n_sim, 3) if n_sim else None,
            "fold_ev": [round(v, 3) for v in fold_ev],
            "lofo_ev": round(lofo, 3) if lofo is not None else None,
            "ev_prime_timeout0": round(evp, 3) if evp is not None else None,
            "pnl_lag1_rho": round(pnl_lag1, 4) if pnl_lag1 is not None else None,
            "configs": {f"tp{cfg[0]}_sl{cfg[1]}": round(ev[cfg], 3)
                        if ev[cfg] is not None else None for cfg in configs},
        }
        analysis[key] = s

    # ── レグ A: BH-FDR (m=5) ──
    fdr = r1judge.bh_fdr(pvals, FDR_Q) if pvals else {}
    passing = []
    for c in CELLS:
        key = _cell_key(c)
        s = analysis[key]
        if s.get("n", 0) == 0:
            s["gates"] = {"pass": False, "fail_reason": "OOS エントリーゼロ"}
            continue
        f_ = fdr.get(key, {})
        e_ = s.get("ev_leg", {})
        adj_pos = e_.get("adjacent_positive", "0/0").split("/")
        g = {
            "A_fdr": bool(f_.get("survive")),
            "A_ratio_floor": bool(s.get("ratio") is not None
                                  and s["ratio"] >= RATIO_FLOOR),
            "A_min_n": bool(s["n"] >= MIN_N),
            "B_nb_mean_floor": bool(e_.get("nb3x3_mean_ev") is not None
                                    and e_["nb3x3_mean_ev"] >= NB_MEAN_FLOOR),
            "B_adjacent_majority": int(adj_pos[0]) * 2 > int(adj_pos[1]),
            "knife_fold_lofo": bool(e_.get("lofo_ev") is not None
                                    and e_["lofo_ev"] > 0),
        }
        g["pass"] = all(g.values())
        s["gates"] = g
        if g["pass"]:
            passing.append(key)

    verdict = "PASS" if passing else "FAIL"
    out = {
        "task": "20260710-ws3-round2-explore (OOS verdict)",
        "prereg": "knowledge-base/wiki/decisions/ws3-round2-explore-prereg-2026-07-10.md §3 (LOCK)",
        "rule": "R1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "oos_window": frozen["oos_window"],
        "oos_window_reuse": "OOS-1 (2024-07-07..2025-07-07) 再利用 2 回目 — per-cell 未使用のため有効 (§3)",
        "n_boot": r1judge.N_BOOT, "seed": r1judge.SEED,
        "fdr_q": FDR_Q, "m": len(pvals), "ratio_floor": RATIO_FLOOR,
        "min_n": MIN_N, "nb_mean_floor": NB_MEAN_FLOOR,
        "tie_break": "SL 優先 (両ヒット=LOSS)",
        "recon_fail_total": recon_fail_total,
        "mechanical_verdict": verdict,
        "passing_cells": passing,
        "bh_fdr": fdr,
        "cells": analysis,
        "pass_composition": "PASS = A(FDR ∧ ratio≥1.2 ∧ N≥30) ∧ B(近傍平均≥0.5 ∧ 隣接過半>0)"
                            " ∧ knife(LOFO>0)。擬似反復=日次ブロック設計+lag1ρ記録 / "
                            "孤立格子点=B隣接過半 / EV'=記録 (Secondary)",
    }
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    lines = [
        "# WS3 round-2 OOS verdict (機械判定、pre-reg §3)",
        "",
        f"- 生成: {out['generated_utc']} / verdict(機械): **{verdict}** / "
        f"OOS 窓: {out['oos_window']} (再利用 2 回目)",
        f"- PASS = レグA (BH-FDR q={FDR_Q} m={len(pvals)} ∧ ratio≥{RATIO_FLOOR} ∧ "
        f"N≥{MIN_N}) ∧ レグB (best 3×3 近傍平均 ≥ +{NB_MEAN_FLOOR} p/t ∧ 隣接過半 EV>0)"
        f" ∧ ナイフエッジ (LOFO>0)",
        f"- ep 復元検証不一致: {recon_fail_total} (許容 {RECON_TOL_PIP}p)",
        "",
        "| cell | H | N | OOS ratio (探索) | p | FDR | ratio≥1.2 | best EV | "
        "近傍平均 | 隣接正 | LOFO | 判定 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in CELLS:
        key = _cell_key(c)
        s = analysis[key]
        if s.get("n", 0) == 0:
            lines.append(f"| {key} | h{c['h']} | 0 | — | — | — | — | — | — | — | — "
                         f"| FAIL (no-entry) |")
            continue
        g = s["gates"]
        e_ = s["ev_leg"]
        f_ = fdr.get(key, {})
        lines.append(
            f"| {key} | h{s['primary_h']} | {s['n']} | **{s.get('ratio')}** "
            f"({s['explore_ratio']}) | {s.get('boot_p')} "
            f"| {'✓' if g['A_fdr'] else '✗'} "
            f"| {'✓' if g['A_ratio_floor'] else '✗'} "
            f"| {e_['best_ev_adj']} ({e_['best_config']}) "
            f"| {e_['nb3x3_mean_ev']} | {e_['adjacent_positive']} "
            f"| {e_['lofo_ev']} "
            f"| {'**PASS**' if g['pass'] else 'FAIL'} |")
    lines += ["", "config 別 EV・fold・EV'・lag-1 ρ は JSON 参照。", ""]
    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines))
    print(json.dumps({"mechanical_verdict": verdict, "passing_cells": passing},
                     ensure_ascii=False))
    print(f"saved: {OUT_JSON}\nsaved: {OUT_MD}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--verdict", action="store_true")
    args = ap.parse_args()
    if args.freeze:
        run_freeze()
    else:
        run_verdict()


if __name__ == "__main__":
    main()
