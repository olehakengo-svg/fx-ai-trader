#!/usr/bin/env python3
"""WS3 stage-2 barrier/EV grid — pre-reg 機械実行器 (rule:R1 stage-2)

仕様 (変更禁止): knowledge-base/wiki/decisions/ws3-stage2-barrier-ev-prereg-2026-07-09.md
LOCK: 2026-07-09 user 承認。対象 = stage-1 PASS 2 セル限定。

2 モード (pre-reg §3 の執行順序を強制):
  --extract  エントリー抽出のみ。切詰め worktree で BT を走らせ、対象 2 セルの
             {entry_type, pair, sig, entry_time, ep} と N を確定して保存。
             barrier sim はこのモードでは一切実行しない。
  --sim      凍結済みエントリーファイルを読み、first-touch barrier sim +
             §4 エンドポイント (WY max-T) + §5 ナイフエッジ統計を機械計算。

実行 (切詰め worktree 内、BT_MODE=1 NO_AUTOSTART=1 BT_REQUIRE_MASSIVE_CACHE=1):
  python3 tools/ws3_stage2_barrier_sim.py --extract --out <entries.json>
  python3 tools/ws3_stage2_barrier_sim.py --sim --entries <entries.json> \
      --parquet-dir <dir> --out-prefix <prefix>
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

# ── pre-reg §2 固定 (変更禁止) ──
CELLS = {
    ("london_fix_reversal", "EUR_USD"): {
        "tp_grid": [14, 18, 24], "sl_grid": [10, 14, 18],
        "friction": 2.00, "friction_stress": 3.0, "stress_gate": False,
    },
    ("htf_false_breakout", "AUD_JPY"): {
        "tp_grid": [20, 28, 36], "sl_grid": [16, 24, 30],
        "friction": 3.125, "friction_stress": 4.0, "stress_gate": True,  # §4(e)
    },
}
HOLD_BARS = 24          # h24 固定 (15m×24 = 6h)
OOS2_START = "2022-07-07"
OOS2_END = "2024-07-06"
LOOKBACK_DAYS = 730
N_BOOT = 10000
SEED = 20260709
P_CELL_ALPHA = 0.05     # 2 セル Bonferroni で FWER 0.10
NEIGHBOR_EV_FLOOR = 0.5  # §4(b)
MIN_N = 30              # §4(c)
FDR_Q = 0.10            # Secondary (記述)
FRICTION_FLOOR = 1.30   # Secondary (記述)

PARITY_ENV = {
    "WICK_IMBALANCE_REVERSION_REDESIGN_V2": "1",
    "DT_SR_CHANNEL_REDESIGN_V2": "1",
    "VSG_JPY_REVERSAL_REDESIGN_V2": "1",
}
BASE_ENV = {"BT_MODE": "1", "NO_AUTOSTART": "1", "BT_REQUIRE_MASSIVE_CACHE": "1"}

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pip(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


# ══════════════════════ extract mode (§3 stage 1) ══════════════════════

def run_extract(out_path: str) -> None:
    os.environ.update(BASE_ENV)
    os.environ.update(PARITY_ENV)
    for k in ("BT_TP_MULT", "BT_SL_MULT", "BT_TPSL_MULT_TYPES",
              "HTF_FALSE_BREAKOUT_REDESIGN_V2"):  # §7: redesign_v2 は OFF (legacy)
        os.environ.pop(k, None)
    sys.path.insert(0, REPO)
    os.chdir(REPO)
    import app

    pairs = sorted({p for _, p in CELLS})
    entries, t0 = [], time.time()
    for pair in pairs:
        app._dt_bt_cache.clear()
        sym = pair.replace("_", "") + "=X"
        res = app.run_daytrade_backtest(sym, lookback_days=LOOKBACK_DAYS,
                                        interval="15m")
        if "error" in res:
            print(f"[extract] {pair}: BT error {res['error']}",
                  file=sys.stderr, flush=True)
            continue
        kept = 0
        for t in res.get("trade_log", []):
            et, ep, sig = t.get("entry_time"), t.get("ep"), t.get("sig")
            etype = t.get("entry_type")
            if (etype, pair) not in CELLS:
                continue
            if not et or ep is None or sig not in ("BUY", "SELL"):
                continue
            d = et[:10]
            if d < OOS2_START or d > OOS2_END:
                continue  # OOS-2 窓外 (warmup 由来の窓前エントリー等)
            entries.append({"entry_type": etype, "pair": pair, "sig": sig,
                            "entry_time": et, "ep": float(ep)})
            kept += 1
        print(f"[extract] {pair}: BT trades={res.get('trades')} "
              f"target-cell kept={kept} ({time.time()-t0:.0f}s)",
              file=sys.stderr, flush=True)

    n_by_cell = {}
    for e in entries:
        k = f"{e['entry_type']}__{e['pair']}"
        n_by_cell[k] = n_by_cell.get(k, 0) + 1
    out = {
        "prereg": "knowledge-base/wiki/decisions/ws3-stage2-barrier-ev-prereg-2026-07-09.md",
        "mode": "extract (barrier sim 未実行 — §3 執行順序 stage 1)",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "oos2_window": f"{OOS2_START}..{OOS2_END}",
        "lookback_days": LOOKBACK_DAYS,
        "env": {**BASE_ENV, **PARITY_ENV, "HTF_FALSE_BREAKOUT_REDESIGN_V2": "(unset/legacy)"},
        "n_by_cell": n_by_cell,
        "entries": entries,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, ensure_ascii=False)
    print(json.dumps({"mode": "extract", "n_by_cell": n_by_cell}, ensure_ascii=False))
    print(f"saved: {out_path}")


# ══════════════════════ sim mode (§3 stage 2 + §4 + §5) ══════════════════════

def first_touch(hi, lo, cl, ep, sig, tp_px, sl_px):
    """24 bar first-touch。同一バー両ヒット = SL 優先 (§3)。
    戻り: (pnl_price, leg, fut_close_pnl_price)  leg ∈ {tp, sl, timeout}"""
    d = 1.0 if sig == "BUY" else -1.0
    tp_lvl = ep + d * tp_px
    sl_lvl = ep - d * sl_px
    for i in range(len(hi)):
        hit_tp = hi[i] >= tp_lvl if d > 0 else lo[i] <= tp_lvl
        hit_sl = lo[i] <= sl_lvl if d > 0 else hi[i] >= sl_lvl
        if hit_tp and hit_sl:
            # 判定 = SL 優先。感度 (fut_close): 当該バー close が有利側なら TP
            fut = tp_px if (cl[i] - ep) * d > 0 else -sl_px
            return -sl_px, "sl", fut
        if hit_sl:
            return -sl_px, "sl", -sl_px
        if hit_tp:
            return tp_px, "tp", tp_px
    pnl = (cl[-1] - ep) * d
    return pnl, "timeout", pnl


def run_sim(entries_path: str, parquet_dir: str, out_prefix: str) -> None:
    import numpy as np
    import pandas as pd

    frozen = json.load(open(entries_path))
    entries = frozen["entries"]
    rng = np.random.default_rng(SEED)

    dfs = {}
    for pair in sorted({p for _, p in CELLS}):
        dfs[pair] = pd.read_parquet(os.path.join(parquet_dir, f"{pair}_15m.parquet"))

    # ── per-entry × per-config の pnl 行列を構築 ──
    results = {}  # cell_key -> dict
    for (etype, pair), spec in CELLS.items():
        key = f"{etype}__{pair}"
        rows = [e for e in entries
                if e["entry_type"] == etype and e["pair"] == pair]
        df = dfs[pair]
        idx = df.index
        pip = _pip(pair)
        hi_a, lo_a, cl_a = df["High"].values, df["Low"].values, df["Close"].values
        configs = [(tp, sl) for tp in spec["tp_grid"] for sl in spec["sl_grid"]]
        pnl = {c: [] for c in configs}       # 摩擦控除前 (pips)
        leg = {c: [] for c in configs}
        fut = {c: [] for c in configs}       # fut_close tie-break 感度
        days, skipped = [], 0
        for e in rows:
            ts = pd.Timestamp(e["entry_time"])
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            pos = idx.searchsorted(ts)
            if pos >= len(idx) or idx[pos] != ts:
                skipped += 1
                continue
            ep_pos = pos + 1  # entry はシグナルバーの次バー (BT 仕様、stage-1 同一)
            if ep_pos + HOLD_BARS >= len(idx):
                skipped += 1
                continue
            sl_ = slice(ep_pos, ep_pos + HOLD_BARS)
            hi, lo, cl = hi_a[sl_], lo_a[sl_], cl_a[sl_]
            ep = e["ep"]
            days.append(e["entry_time"][:10])
            for (tp, sl) in configs:
                p, lg, fc = first_touch(hi, lo, cl, ep, e["sig"],
                                        tp * pip, sl * pip)
                pnl[(tp, sl)].append(p / pip)
                leg[(tp, sl)].append(lg)
                fut[(tp, sl)].append(fc / pip)
        n = len(days)
        fr = spec["friction"]
        cfg_stats = {}
        pnl_mat = np.array([pnl[c] for c in configs])  # (9, n) friction 控除前
        adj = pnl_mat - fr                              # 摩擦調整後
        ev_obs = adj.mean(axis=1) if n else np.zeros(len(configs))

        # ── WY max-T bootstrap (日次 block、セル内中心化 null) ──
        day_arr = np.array(days)
        uniq_days = np.array(sorted(set(days)))
        day_slices = {d: np.where(day_arr == d)[0] for d in uniq_days}
        nd = len(uniq_days)
        centered = adj - adj.mean(axis=1, keepdims=True)  # (9, n)
        t_obs = float(ev_obs.max()) if n else 0.0
        t_null = np.empty(N_BOOT)
        p_cfg_boot = np.zeros(len(configs))  # Secondary: per-config p
        if n and nd > 1:
            for b in range(N_BOOT):
                di = rng.integers(0, nd, size=nd)
                sel = np.concatenate([day_slices[uniq_days[i]] for i in di])
                t_null[b] = centered[:, sel].mean(axis=1).max()
                p_cfg_boot += (adj[:, sel].mean(axis=1) <= 0)
            p_cell = float((1 + (t_null >= t_obs).sum()) / (N_BOOT + 1))
            p_cfg = (1 + p_cfg_boot) / (N_BOOT + 1)
        else:
            p_cell, p_cfg = 1.0, np.ones(len(configs))

        # ── config 別統計 + §5 ──
        best_i = int(np.argmax(ev_obs)) if n else 0
        for ci, c in enumerate(configs):
            legs = leg[c]
            n_tp = legs.count("tp"); n_sl = legs.count("sl")
            n_to = legs.count("timeout")
            adj_c = adj[ci]
            # §5.1 EV' (timeout price pnl → 0、摩擦維持)
            evp = float(np.mean([(-fr if lg == "timeout" else v)
                                 for v, lg in zip(adj_c, legs)])) if n else None
            # lag-1 ρ
            rho = (float(np.corrcoef(adj_c[:-1], adj_c[1:])[0, 1])
                   if n > 2 and np.std(adj_c) > 0 else None)
            # LOFO (時間三分割)
            folds = np.array_split(np.arange(n), 3) if n >= 3 else []
            fold_ev = [float(adj_c[f].mean()) for f in folds if len(f)]
            lofo = None
            if len(fold_ev) == 3:
                w = int(np.argmax(fold_ev))
                rest = np.concatenate([folds[j] for j in range(3) if j != w])
                lofo = float(adj_c[rest].mean())
            cfg_stats[f"tp{c[0]}_sl{c[1]}"] = {
                "ev": round(float(ev_obs[ci]), 3),
                "ev_fut_close": round(float(np.mean(fut[c]) - fr), 3) if n else None,
                "ev_friction_floor": round(float(pnl_mat[ci].mean() - FRICTION_FLOOR), 3) if n else None,
                "ev_friction_stress": round(float(pnl_mat[ci].mean() - spec["friction_stress"]), 3) if n else None,
                "ev_prime_timeout0": round(evp, 3) if evp is not None else None,
                "p_boot": round(float(p_cfg[ci]), 5),
                "tp_rate": round(n_tp / n, 3) if n else None,
                "sl_rate": round(n_sl / n, 3) if n else None,
                "timeout_rate": round(n_to / n, 3) if n else None,
                "fold_ev": [round(v, 3) for v in fold_ev],
                "lofo_ev": round(lofo, 3) if lofo is not None else None,
                "lag1_rho": round(rho, 4) if rho is not None else None,
            }

        # §4(b) 近傍平均 + §5.3 隣接符号 (最良構成)
        bt_, bs_ = configs[best_i]
        tg, sg = spec["tp_grid"], spec["sl_grid"]
        ti, si = tg.index(bt_), sg.index(bs_)
        nb_all = [(tg[a], sg[b])
                  for a in range(max(0, ti - 1), min(len(tg), ti + 2))
                  for b in range(max(0, si - 1), min(len(sg), si + 2))]
        nb_adjacent = [(t_, s_) for (t_, s_) in nb_all
                       if (abs(tg.index(t_) - ti) + abs(sg.index(s_) - si)) == 1]
        nb_mean = float(np.mean([ev_obs[configs.index(c)] for c in nb_all])) if n else None
        adj_signs = [float(ev_obs[configs.index(c)]) > 0 for c in nb_adjacent]

        results[key] = {
            "n": n, "n_days": nd, "skipped": skipped,
            "friction_judgment": fr,
            "p_cell_wy_maxt": round(p_cell, 6),
            "best_config": f"tp{bt_}_sl{bs_}",
            "best_ev": round(float(ev_obs[best_i]), 3),
            "neighborhood_mean_ev": round(nb_mean, 3) if nb_mean is not None else None,
            "adjacent_positive": f"{sum(adj_signs)}/{len(adj_signs)}",
            "configs": cfg_stats,
        }

    # ── Secondary: BH-FDR m=18 (記述) ──
    all_p = {}
    for key, r in results.items():
        for cname, cs in r["configs"].items():
            all_p[f"{key}::{cname}"] = cs["p_boot"]
    items = sorted(all_p.items(), key=lambda kv: kv[1])
    m = len(items)
    cutoff = 0
    for rank, (_, p) in enumerate(items, 1):
        if p <= FDR_Q * rank / m:
            cutoff = rank
    fdr = {k: {"p": p, "rank": r_, "survive": r_ <= cutoff}
           for r_, (k, p) in enumerate(items, 1)}

    # ── §4 ゲート判定 (TV canon (d) は別途) ──
    gates = {}
    for key, r in results.items():
        spec = CELLS[[c for c in CELLS if f"{c[0]}__{c[1]}" == key][0]]
        best = r["configs"][r["best_config"]]
        g = {
            "a_p_cell": r["p_cell_wy_maxt"] <= P_CELL_ALPHA,
            "b_neighborhood_floor": (r["neighborhood_mean_ev"] is not None
                                     and r["neighborhood_mean_ev"] >= NEIGHBOR_EV_FLOOR),
            "c_min_n": r["n"] >= MIN_N,
            "d_tv_canon": None,  # 別途 (§3b)
            "e_stress": ((best["ev_friction_stress"] is not None
                          and best["ev_friction_stress"] > 0)
                         if spec["stress_gate"] else True),
            "knife_1_evprime": (best["ev_prime_timeout0"] is not None
                                and best["ev_prime_timeout0"] >= 0),
            "knife_3_adjacent": int(r["adjacent_positive"].split("/")[0]) * 2
                                 > int(r["adjacent_positive"].split("/")[1]),
            "knife_4_lofo": (best["lofo_ev"] is not None and best["lofo_ev"] > 0),
        }
        g["pass_pending_tv"] = all(v for k_, v in g.items()
                                   if v is not None and k_ != "d_tv_canon")
        gates[key] = g

    out = {
        "prereg": "knowledge-base/wiki/decisions/ws3-stage2-barrier-ev-prereg-2026-07-09.md",
        "mode": "sim",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "entries_file": entries_path,
        "oos2_window": frozen.get("oos2_window"),
        "n_boot": N_BOOT, "seed": SEED, "p_cell_alpha": P_CELL_ALPHA,
        "tie_break": "SL 優先 (両ヒット=LOSS)。fut_close は感度列",
        "cells": results,
        "gates": gates,
        "secondary_bh_fdr_m18": fdr,
    }
    jp = f"{out_prefix}.json"
    with open(jp, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

    lines = ["# WS3 stage-2 barrier/EV grid (機械計算、pre-reg §4)", "",
             f"- 生成: {out['generated_utc']} / OOS-2: {out['oos2_window']} / "
             f"tie-break: SL 優先", ""]
    for key, r in results.items():
        g = gates[key]
        lines += [f"## {key} (N={r['n']}, days={r['n_days']}, "
                  f"friction={r['friction_judgment']})",
                  f"- p_cell (WY max-T) = **{r['p_cell_wy_maxt']}** "
                  f"(α={P_CELL_ALPHA}) / best = {r['best_config']} "
                  f"EV **{r['best_ev']}** / 近傍平均 {r['neighborhood_mean_ev']} "
                  f"/ 隣接正 {r['adjacent_positive']}",
                  f"- gates: {json.dumps(g, ensure_ascii=False)}",
                  "",
                  "| config | EV | EV' | p | TP% | SL% | TO% | LOFO | stress |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for cn, cs in r["configs"].items():
            lines.append(f"| {cn} | {cs['ev']} | {cs['ev_prime_timeout0']} "
                         f"| {cs['p_boot']} | {cs['tp_rate']} | {cs['sl_rate']} "
                         f"| {cs['timeout_rate']} | {cs['lofo_ev']} "
                         f"| {cs['ev_friction_stress']} |")
        lines.append("")
    with open(f"{out_prefix}.md", "w") as f:
        f.write("\n".join(lines))
    print(json.dumps({"gates": {k: v["pass_pending_tv"] for k, v in gates.items()},
                      "p_cells": {k: r["p_cell_wy_maxt"] for k, r in results.items()}},
                     ensure_ascii=False))
    print(f"saved: {jp}\nsaved: {out_prefix}.md")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--extract", action="store_true")
    mode.add_argument("--sim", action="store_true")
    ap.add_argument("--out", help="[extract] エントリー保存先 JSON")
    ap.add_argument("--entries", help="[sim] 凍結エントリー JSON")
    ap.add_argument("--parquet-dir", help="[sim] 切詰め parquet ディレクトリ")
    ap.add_argument("--out-prefix", help="[sim] 出力 prefix (.json/.md)")
    args = ap.parse_args()
    if args.extract:
        if not args.out:
            ap.error("--extract requires --out")
        run_extract(args.out)
    else:
        if not (args.entries and args.parquet_dir and args.out_prefix):
            ap.error("--sim requires --entries --parquet-dir --out-prefix")
        run_sim(args.entries, args.parquet_dir, args.out_prefix)


if __name__ == "__main__":
    main()
