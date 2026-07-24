#!/usr/bin/env python3
"""WS3 round-2 §2(ii) — 探索窓 first-touch EV スクリーン (rule:R3、純研究)

pre-reg: knowledge-base/wiki/decisions/ws3-round2-explore-prereg-2026-07-10.md
§2(ii) (2026-07-10 改訂、round-2 スキャン結果の観測前の a priori 変更):
1次スクリーン通過セル (ws3_round2_scan_2026_07.json candidates) に対し、
探索窓で first-touch barrier sim を実行し
「best 構成の摩擦調整 EV > 0 ∧ 隣接構成 (Manhattan 距離1、存在するもの) の
過半が EV > 0」を要求する。不通過セルは脱落。

設計 (a priori 宣言、機械導出のみ — 手動 grid 調整禁止):
- first-touch 判定は `tools/ws3_stage2_barrier_sim.py` (origin/main) の
  first_touch() と同一 (関数を同形移植)。同一バー TP+SL 両ヒット = SL 優先。
  hold = 当該セル primary horizon bars 固定 (減衰型=24 / 持続型=96)。
  timeout = hold 最終バー close で決済。BE/Trail なし。stage-2 の**結果数値**は
  一切参照していない (ツール流用のみ)
- grid (セル毎 3×3): TP = int(round(percentile(mfe_H, {50,75,90}))) /
  SL = int(round(percentile(mae_H, {50,75,90})))、H = primary horizon、
  percentile は np.percentile (linear、round-1 スキャンと同一)。母集団 =
  当該セルの探索窓 entries (checkpoint)。丸め後の重複段はそのまま
  (index 隣接で判定)。SL 下限 1 pip
- 摩擦 (往復 pips、判定値、a priori): EUR_USD 2.00 / USD_JPY 2.14 /
  GBP_USD 4.53 / AUD_JPY 3.125 / GBP_JPY 4.53 (理論テーブル不在のため
  GBP_USD 同値を保守採用)
- entry price (ep) の復元: checkpoint entries は ep を持たないため、round-1
  forward 計測の恒等式から復元する —
  BUY:  ep = max(High[ep_pos .. ep_pos+96]) − mfe_96·pip
  SELL: ep = min(Low[ep_pos .. ep_pos+96]) + mfe_96·pip
  (forward_mfe と同一窓 = h+1 bars)。MAE 側からの独立復元
  (BUY: min(Low)+mae_96·pip) と突き合わせ、さらに h24 の mfe/mae を再計算して
  checkpoint 値と照合 (許容 0.02 pip)。不一致エントリーは fail-loud
- parquet: round-1 と同一系列 (main repo の Massive キャッシュ)。全 entry の
  mfe/mae 再計算一致 = 履歴バーが round-1 実行時と同一であることの機械検証。
  OOS 窓 (2024-07-07〜2025-07-07) の行は position slice の対象外 — 統計計算ゼロ

実行: python3 tools/ws3_round2_ev_screen.py --parquet-dir <dir>
"""

import argparse
import json
import os
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_DIR = os.path.join(REPO, "knowledge-base", "raw", "bt-results")
CAND_JSON = os.path.join(BT_DIR, "ws3_round2_scan_2026_07.json")
R1_CHECKPOINT = os.path.join(BT_DIR, ".ws3_mfe_scan_checkpoint.json")
OUT_JSON = os.path.join(BT_DIR, "ws3_round2_ev_screen_2026_07.json")
OUT_MD = os.path.join(BT_DIR, "ws3_round2_ev_screen_2026_07.md")

FRICTION = {  # 往復 pips (判定値、a priori 宣言)
    "EUR_USD": 2.00,
    "USD_JPY": 2.14,
    "GBP_USD": 4.53,
    "AUD_JPY": 3.125,
    "GBP_JPY": 4.53,  # 理論テーブル不在 → GBP_USD 同値の保守採用 (a priori)
}
PCTS = (50, 75, 90)
RECON_TOL_PIP = 0.02  # ep 復元・mfe/mae 照合の許容 (丸め 0.005×2 + ε)


def _pip(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


def first_touch(hi, lo, cl, ep, sig, tp_px, sl_px):
    """stage-2 barrier sim と同形 (SL 優先 tie-break、timeout = 最終バー close)"""
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--parquet-dir", required=True,
                    help="{PAIR}_15m.parquet ディレクトリ (round-1 同一系列)")
    ap.add_argument("--candidates", default=CAND_JSON)
    ap.add_argument("--r1-checkpoint", default=R1_CHECKPOINT)
    ap.add_argument("--out-json", default=OUT_JSON)
    ap.add_argument("--out-md", default=OUT_MD)
    args = ap.parse_args()

    import numpy as np
    import pandas as pd

    cands = json.load(open(args.candidates))["candidates"]
    entries_all = json.load(open(args.r1_checkpoint))

    dfs = {}
    for pair in sorted({c["pair"] for c in cands}):
        pq = os.path.join(args.parquet_dir, f"{pair}_15m.parquet")
        dfs[pair] = pd.read_parquet(pq)

    results = {}
    recon_fail_total = 0
    for c in cands:
        et, pair, sig = c["entry_type"], c["pair"], c["sig"]
        H = 96 if c["primary_horizon"] == "h96" else 24
        rows = [r for r in entries_all
                if r["entry_type"] == et and r["pair"] == pair
                and (sig is None or r["sig"] == sig)]
        df = dfs[pair]
        idx = df.index
        pip = _pip(pair)
        hi_a = df["High"].values
        lo_a = df["Low"].values
        cl_a = df["Close"].values

        # ── ep 復元 + 検証 ──
        sim_rows, recon_fail = [], 0
        for r in rows:
            ts = pd.Timestamp(r["entry_time"])
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            pos = idx.searchsorted(ts)
            if pos >= len(idx) or idx[pos] != ts:
                recon_fail += 1
                continue
            ep_pos = pos + 1  # entry = シグナルバーの次バー (round-1/stage-2 同一)
            w96 = slice(ep_pos, min(ep_pos + 96 + 1, len(idx)))
            hi96, lo96 = hi_a[w96], lo_a[w96]
            d = 1.0 if r["sig"] == "BUY" else -1.0
            if d > 0:
                ep = float(np.max(hi96)) - r["mfe_96"] * pip
                ep_alt = float(np.min(lo96)) + r["mae_96"] * pip
            else:
                ep = float(np.min(lo96)) + r["mfe_96"] * pip
                ep_alt = float(np.max(hi96)) - r["mae_96"] * pip
            # 独立復元の一致 + h24 mfe/mae 再計算照合
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
            sim_rows.append({"ep": ep, "ep_pos": ep_pos, "sig": r["sig"],
                             "mfe_H": r[f"mfe_{H}"], "mae_H": r[f"mae_{H}"]})
        recon_fail_total += recon_fail

        # ── grid 機械導出 (探索窓分位点、a priori 規則) ──
        mfe_v = np.array([x["mfe_H"] for x in sim_rows])
        mae_v = np.array([x["mae_H"] for x in sim_rows])
        tp_grid = [max(1, int(round(float(np.percentile(mfe_v, p))))) for p in PCTS]
        sl_grid = [max(1, int(round(float(np.percentile(mae_v, p))))) for p in PCTS]
        fr = FRICTION[pair]
        configs = [(tp, sl) for tp in tp_grid for sl in sl_grid]

        pnl = {cfg: [] for cfg in configs}
        leg = {cfg: [] for cfg in configs}
        skipped = 0
        for x in sim_rows:
            sl_ = slice(x["ep_pos"], x["ep_pos"] + H)  # stage-2 と同一 (H bars)
            if x["ep_pos"] + H > len(idx):
                skipped += 1
                continue
            hi, lo, cl = hi_a[sl_], lo_a[sl_], cl_a[sl_]
            for (tp, sl) in configs:
                p, lg = first_touch(hi, lo, cl, x["ep"], x["sig"],
                                    tp * pip, sl * pip)
                pnl[(tp, sl)].append(p / pip)
                leg[(tp, sl)].append(lg)

        n = len(pnl[configs[0]])
        ev = {cfg: (float(np.mean(v)) - fr if v else None)
              for cfg, v in pnl.items()}
        ev_arr = [ev[cfg] for cfg in configs]
        best_i = int(np.argmax([e if e is not None else -1e9 for e in ev_arr]))
        bt_, bs_ = configs[best_i]
        ti, si = best_i // 3, best_i % 3
        # 隣接 = Manhattan 距離 1 (stage-2 §5.3 と同基準、index ベース)
        adj_idx = [(a, b) for (a, b) in
                   [(ti - 1, si), (ti + 1, si), (ti, si - 1), (ti, si + 1)]
                   if 0 <= a < 3 and 0 <= b < 3]
        adj_evs = [ev[configs[a * 3 + b]] for a, b in adj_idx]
        n_pos = sum(1 for e in adj_evs if e is not None and e > 0)
        passed = (ev_arr[best_i] is not None and ev_arr[best_i] > 0
                  and n_pos * 2 > len(adj_evs))

        cfg_stats = {}
        for ci, cfg in enumerate(configs):
            legs = leg[cfg]
            cfg_stats[f"tp{cfg[0]}_sl{cfg[1]}"] = {
                "ev_adj": round(ev[cfg], 3) if ev[cfg] is not None else None,
                "tp_rate": round(legs.count("tp") / n, 3) if n else None,
                "sl_rate": round(legs.count("sl") / n, 3) if n else None,
                "timeout_rate": round(legs.count("timeout") / n, 3) if n else None,
            }
        results[c["cell"]] = {
            "entry_type": et, "pair": pair, "sig": sig,
            "type": c["type"], "primary_horizon": c["primary_horizon"],
            "hold_bars": H, "n_sim": n, "recon_fail": recon_fail,
            "skipped_tail": skipped, "friction": fr,
            "tp_grid": tp_grid, "sl_grid": sl_grid,
            "best_config": f"tp{bt_}_sl{bs_}",
            "best_ev_adj": round(ev_arr[best_i], 3) if ev_arr[best_i] is not None else None,
            "adjacent_positive": f"{n_pos}/{len(adj_evs)}",
            "pass": bool(passed),
            "configs": cfg_stats,
        }

    survivors = [k for k, v in results.items() if v["pass"]]
    out = {
        "task": "20260710-ws3-round2-explore §2(ii) first-touch EV screen",
        "rule": "R3",
        "prereg": "ws3-round2-explore-prereg-2026-07-10.md §2(ii) (origin/main, "
                  "2026-07-10 改訂 = round-2 スキャン結果観測前の a priori 変更)",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "engine": "tools/ws3_stage2_barrier_sim.py first_touch() 同形移植 "
                  "(SL 優先 tie-break / timeout=最終バー close / BE・Trail なし)。"
                  "stage-2 の結果数値は不参照 (ツールのみ流用)",
        "window": "探索窓 2025-07-08〜2026-06-07 (round-1 checkpoint 母集団と同一)",
        "oos_untouched": "2024-07-07〜2025-07-07 非接触",
        "friction_table": FRICTION,
        "grid_rule": "TP=round(pct(mfe_H,{50,75,90})) / SL=round(pct(mae_H,{50,75,90})) "
                     "per-cell、H=primary horizon、np.percentile linear、SL 下限1pip",
        "pass_rule": "best 摩擦調整 EV>0 ∧ 隣接 (Manhattan 距離1、存在分) の過半 EV>0",
        "recon_fail_total": recon_fail_total,
        "cells": results,
        "survivors": survivors,
    }
    with open(args.out_json, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[ev-screen] saved {args.out_json}")

    # ── md (機械表) ──
    L = ["# WS3 round-2 §2(ii) 探索窓 first-touch EV スクリーン (機械計算、rule:R3)",
         "",
         f"- 生成: {out['generated_utc']} / {out['prereg']}",
         f"- engine: {out['engine']}",
         f"- 窓: {out['window']} / OOS 非接触 / 摩擦 (往復 pips): "
         + ", ".join(f"{k} {v}" for k, v in FRICTION.items()),
         f"- grid: {out['grid_rule']}",
         f"- 通過条件: {out['pass_rule']}",
         f"- ep 復元検証不一致: {recon_fail_total} entries (許容 {RECON_TOL_PIP}p)",
         ""]
    for cell, r in results.items():
        L += [f"## {cell} ({r['type']}型, hold={r['hold_bars']}bars, "
              f"N={r['n_sim']}, friction={r['friction']})",
              f"- grid: TP={r['tp_grid']} / SL={r['sl_grid']} (凍結)",
              f"- best = {r['best_config']} EV_adj **{r['best_ev_adj']}** / "
              f"隣接正 {r['adjacent_positive']} → "
              f"**{'✅ 通過' if r['pass'] else '❌ 脱落'}**",
              "",
              "| config | EV_adj | TP% | SL% | TO% |",
              "|---|---|---|---|---|"]
        for cn, cs in r["configs"].items():
            L.append(f"| {cn} | {cs['ev_adj']} | {cs['tp_rate']} "
                     f"| {cs['sl_rate']} | {cs['timeout_rate']} |")
        L.append("")
    L += [f"## 結果: 通過 {len(survivors)}/{len(results)}", ""]
    for s in survivors:
        L.append(f"- ✅ {s}")
    L.append("")
    with open(args.out_md, "w") as f:
        f.write("\n".join(L))
    print(f"[ev-screen] saved {args.out_md}")
    print(json.dumps({"survivors": survivors,
                      "n_cells": len(results),
                      "recon_fail_total": recon_fail_total},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
