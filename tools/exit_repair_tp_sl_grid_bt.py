#!/usr/bin/env python3
"""exit-repair TP/SL 実走距離整合 grid BT — pre-reg 2026-07-07 LOCK の機械的実行 (rule:R1)

仕様 (変更禁止): knowledge-base/wiki/decisions/exit-repair-tp-sl-prereg-2026-07-07.md
タスク票: .ai/tasks/queue/20260707-1640-exit-repair-tp-sl-grid.md

- Grid: TP_mult {0.4, 0.6, 0.8} × SL_mult {0.6, 0.8, 1.0} (9構成) + baseline 1.0/1.0 (記述のみ、判定外)
- エンジン: app.run_daytrade_backtest (本番 signal 関数 backtest_mode=True)、365d、15m
- BE/Trail OFF (BT default = TV-aligned、BT_ABLATE_BE_TRAIL=1 明示)
- 診断窓 2026-06-07〜 は評価から除外 (trade_log post-filter)
- 対象セル: 診断窓 clean live N≥7 の 6 entry_type × live 発火 pair (下記 CELLS)
- Primary: pooled 摩擦調整 EV (per-pair 理論値控除)、日次ブロックブートストラップ p、
  m=9 BH-FDR q=0.10。Secondary: セル別/実測フロア 1.30 感度 (記述のみ)
- 摩擦の扱い: BT 内部摩擦 (spread/2+slip × entry/exit) を算術的に足し戻して gross 化し、
  pre-reg 理論 RT 値を控除 (理論値 > BT 内部値のため保守側)。バリア幾何に埋まる
  entry 摩擦の path 効果は残存 (保守方向) — verdict caveat に記載

実行:
  BT_MODE=1 NO_AUTOSTART=1 BT_REQUIRE_MASSIVE_CACHE=1 \
    python3 tools/exit_repair_tp_sl_grid_bt.py [--smoke] [--workers 3] [--out PREFIX]
"""

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from datetime import datetime, timezone

# ── pre-reg 固定パラメータ (LOCK — 変更禁止) ──────────────────────────
CELLS = {  # (entry_type, pair): 診断窓 clean live N (payoff-asymmetry-diagnosis §3)
    ("trendline_sweep", "GBP_USD"): 19,
    ("wick_imbalance_reversion", "GBP_USD"): 12,
    ("zz_pivot_v60_sr", "EUR_USD"): 10,
    ("vix_carry_unwind", "USD_JPY"): 10,
    ("dt_sr_channel_reversal", "EUR_JPY"): 9,
    ("vsg_jpy_reversal", "EUR_JPY"): 7,
}
TARGET_TYPES = sorted({et for et, _ in CELLS})
PAIRS = ["GBP_USD", "EUR_USD", "USD_JPY", "EUR_JPY"]
SYMBOLS = {"GBP_USD": "GBPUSD=X", "EUR_USD": "EURUSD=X",
           "USD_JPY": "USDJPY=X", "EUR_JPY": "EURJPY=X"}
FRICTION_THEORY = {"USD_JPY": 2.14, "EUR_USD": 2.00,
                   "GBP_USD": 4.53, "EUR_JPY": 2.50}  # friction-analysis RT pips
FRICTION_FLOOR = 1.30  # 実測フロア pips/trade (感度、判定不使用)
DIAG_START_UTC = "2026-06-07"  # 評価 = entry_time < この日付 (in-sample 除外)
GRID = [(tp, sl) for tp in (0.4, 0.6, 0.8) for sl in (0.6, 0.8, 1.0)]
BASELINE = (1.0, 1.0)
LOOKBACK_DAYS = 365
INTERVAL = "15m"
N_BOOT = 10000
SEED = 20260708
FDR_Q = 0.10
WF_FOLDS = 3

# BT/本番 parity: 3戦略とも「V2=1 でなければ live 挙動にならない」ことをコードで確認済み
# (diagnostic 窓で live 発火している事実 = 本番 V2=1。wick は BT 側 R3 強制の前例 079174bb)
PARITY_ENV = {
    "WICK_IMBALANCE_REVERSION_REDESIGN_V2": "1",
    "DT_SR_CHANNEL_REDESIGN_V2": "1",
    "VSG_JPY_REVERSAL_REDESIGN_V2": "1",
}
BASE_ENV = {
    "BT_MODE": "1",
    "NO_AUTOSTART": "1",
    "BT_REQUIRE_MASSIVE_CACHE": "1",
    "BT_ABLATE_BE_TRAIL": "1",  # BT default で既に OFF だが自己文書化のため明示
}

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(REPO, "knowledge-base", "raw", "bt-results",
                        "exit_repair_tp_sl_grid_2026_07.json")
OUT_MD = os.path.join(REPO, "knowledge-base", "raw", "bt-results",
                      "exit_repair_tp_sl_grid_2026_07.md")
CHECKPOINT = os.path.join(REPO, "knowledge-base", "raw", "bt-results",
                          ".exit_repair_grid_checkpoint.json")


def _pip(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


def _json_default(o):
    """numpy scalar → Python native (json.dump 用)"""
    import numpy as np
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    return str(o)


def _pnl_atr(t: dict) -> float:
    """app.py _dt_pnl と同式 (ATR 倍率単位、BT 内部摩擦込み net)"""
    ef = t.get("exit_friction_m") or 0.0
    if t["outcome"] == "WIN":
        return (t.get("tp_m") or 0.0) - ef
    asl = t.get("actual_sl_m")
    if asl is None:
        asl = t.get("sl_m") or 0.0
    return -(asl + ef)


def run_config(job: dict) -> dict:
    """1 config × 全 pair の BT を独立プロセスで実行 (env 隔離のため spawn 前提)"""
    tp_mult, sl_mult = job["tp_mult"], job["sl_mult"]
    lookback = job["lookback"]
    pairs = job["pairs"]

    env = dict(BASE_ENV)
    env.update(PARITY_ENV)
    env["BT_TP_MULT"] = str(tp_mult)
    env["BT_SL_MULT"] = str(sl_mult)
    env["BT_TPSL_MULT_TYPES"] = ",".join(TARGET_TYPES)
    os.environ.update(env)

    sys.path.insert(0, REPO)
    os.chdir(REPO)
    t0 = time.time()
    import app  # env 設定後に import (BT_MODE/NO_AUTOSTART 反映)

    out = {"tp_mult": tp_mult, "sl_mult": sl_mult, "pairs": {}, "errors": {}}
    for pair in pairs:
        app._dt_bt_cache.clear()
        res = app.run_daytrade_backtest(
            SYMBOLS[pair], lookback_days=lookback, interval=INTERVAL)
        if "error" in res:
            out["errors"][pair] = res["error"]
            out["pairs"][pair] = []
            continue
        keep = []
        for t in res.get("trade_log", []):
            if (t.get("entry_type"), pair) not in CELLS:
                continue
            keep.append({
                "pair": pair,
                "entry_type": t.get("entry_type"),
                "entry_time": t.get("entry_time"),
                "outcome": t.get("outcome"),
                "exit_reason": t.get("exit_reason"),
                "bars_held": t.get("bars_held"),
                "sig": t.get("sig"),
                "atr": t.get("atr"),
                "sl_m": t.get("sl_m"),
                "tp_m": t.get("tp_m"),
                "actual_sl_m": t.get("actual_sl_m"),
                "exit_friction_m": t.get("exit_friction_m", 0.0),
                "entry_friction": t.get("entry_friction", 0.0),
                "exit_friction": t.get("exit_friction", 0.0),
            })
        out["pairs"][pair] = keep
        print(f"[grid] tp={tp_mult} sl={sl_mult} {pair}: "
              f"total={res.get('trades')} cell_trades={len(keep)} "
              f"({time.time()-t0:.0f}s elapsed)", file=sys.stderr, flush=True)
    out["elapsed_sec"] = round(time.time() - t0, 1)
    return out


def enrich(trades: list) -> list:
    """pips 変換 + gross / 理論摩擦控除 / フロア感度列を付与"""
    rows = []
    skipped = 0
    for t in trades:
        atr = t.get("atr")
        if not atr:
            skipped += 1
            continue
        pip = _pip(t["pair"])
        net_bt = _pnl_atr(t) * atr / pip
        fr_bt = (t.get("entry_friction", 0.0) + t.get("exit_friction", 0.0)) / pip
        gross = net_bt + fr_bt
        rows.append({
            **t,
            "net_bt_pips": round(net_bt, 3),
            "friction_bt_pips": round(fr_bt, 3),
            "gross_pips": round(gross, 3),
            "net_theory_pips": round(gross - FRICTION_THEORY[t["pair"]], 3),
            "net_floor_pips": round(gross - FRICTION_FLOOR, 3),
            "entry_date": t["entry_time"][:10],
        })
    if skipped:
        print(f"[grid] WARN: {skipped} trades skipped (atr missing)",
              file=sys.stderr, flush=True)
    return rows


def day_block_bootstrap(rows: list, key: str, n_boot: int, seed: int) -> dict:
    """日次ブロックブートストラップ: day 単位 resample → pooled mean 分布。
    p = P(mean <= 0) one-sided (H1: EV > 0)、repo 慣行 (wick bootstrap_p) の day-block 版"""
    import numpy as np
    by_day = {}
    for r in rows:
        by_day.setdefault(r["entry_date"], []).append(r[key])
    days = sorted(by_day)
    if not days:
        return {"p": None, "se": None, "n_days": 0}
    arrs = [np.asarray(by_day[d], dtype=float) for d in days]
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    nd = len(arrs)
    for b in range(n_boot):
        idx = rng.integers(0, nd, size=nd)
        cat = np.concatenate([arrs[i] for i in idx])
        means[b] = cat.mean()
    p = (1 + int((means <= 0).sum())) / (n_boot + 1)
    return {"p": round(float(p), 6), "se": round(float(means.std(ddof=1)), 4),
            "n_days": nd}


def bh_fdr(pvals: dict, q: float) -> dict:
    """Benjamini-Hochberg step-up (tools/wick_imb_continuation_gbpusd_bt.py:126 と同型)"""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    cutoff = 0
    for rank, (_, p) in enumerate(items, 1):
        if p <= q * rank / m:
            cutoff = rank
    out = {}
    for rank, (k, p) in enumerate(items, 1):
        out[k] = {"p": p, "rank": rank,
                  "bh_threshold": round(q * rank / m, 5),
                  "survive": rank <= cutoff}
    return out


def wf_folds(rows: list, key: str, n_folds: int) -> dict:
    """カレンダー時間 3-fold: 評価期間を等分し fold 別 EV 符号を記録"""
    if not rows:
        return {"folds": [], "pos_ratio": 0.0}
    dates = sorted(r["entry_date"] for r in rows)
    d0 = datetime.fromisoformat(dates[0]).replace(tzinfo=timezone.utc)
    d1 = datetime.fromisoformat(dates[-1]).replace(tzinfo=timezone.utc)
    span = (d1 - d0).total_seconds() or 1.0
    folds = [[] for _ in range(n_folds)]
    for r in rows:
        dt = datetime.fromisoformat(r["entry_date"]).replace(tzinfo=timezone.utc)
        fi = min(n_folds - 1, int((dt - d0).total_seconds() / span * n_folds))
        folds[fi].append(r[key])
    stats = []
    for fi, vals in enumerate(folds):
        ev = sum(vals) / len(vals) if vals else None
        stats.append({"fold": fi + 1, "n": len(vals),
                      "ev": round(ev, 4) if ev is not None else None,
                      "positive": bool(ev is not None and ev > 0)})
    pos = sum(1 for s in stats if s["positive"])
    return {"folds": stats, "pos_ratio": round(pos / n_folds, 3)}


def summarize_config(rows: list) -> dict:
    """pooled + セル別統計"""
    def _agg(rs):
        if not rs:
            return {"n": 0}
        n = len(rs)
        wins = [r for r in rs if r["net_theory_pips"] > 0]
        losses = [r for r in rs if r["net_theory_pips"] <= 0]
        aw = sum(r["net_theory_pips"] for r in wins) / len(wins) if wins else 0.0
        al = sum(r["net_theory_pips"] for r in losses) / len(losses) if losses else 0.0
        tp_hits = sum(1 for r in rs
                      if r["outcome"] == "WIN" and r["exit_reason"] == "tp_sl")
        return {
            "n": n,
            "wr_pct": round(100 * len(wins) / n, 1),
            "ev_bt_pips": round(sum(r["net_bt_pips"] for r in rs) / n, 4),
            "ev_gross_pips": round(sum(r["gross_pips"] for r in rs) / n, 4),
            "ev_theory_pips": round(sum(r["net_theory_pips"] for r in rs) / n, 4),
            "ev_floor_pips": round(sum(r["net_floor_pips"] for r in rs) / n, 4),
            "payoff": round(abs(aw / al), 3) if al else None,
            "tp_hit_ratio": round(tp_hits / n, 3),
            "avg_bars_held": round(sum(r["bars_held"] for r in rs) / n, 1),
            "exit_reasons": {er: sum(1 for r in rs if r["exit_reason"] == er)
                             for er in sorted({r["exit_reason"] for r in rs})},
        }
    cells = {}
    for (et, pair) in CELLS:
        cell_rows = [r for r in rows
                     if r["entry_type"] == et and r["pair"] == pair]
        cells[f"{et}__{pair}"] = _agg(cell_rows)
    return {"pooled": _agg(rows), "cells": cells}


def check_data_freshness(pairs: list, max_stale_hours: int = 72) -> None:
    """silent stale-window 罠の防止: parquet 末尾が古ければ abort"""
    import pandas as pd
    problems = []
    for pair in pairs:
        path = os.path.join(REPO, "data", "cache", "massive",
                            f"{pair}_15m.parquet")
        if not os.path.exists(path):
            problems.append(f"{pair}: parquet 不在 ({path})")
            continue
        df = pd.read_parquet(path, columns=[])
        tail = df.index.max()
        age_h = (pd.Timestamp.now(tz="UTC") - tail).total_seconds() / 3600
        span_d = (tail - df.index.min()).days
        print(f"[grid] data {pair}: {df.index.min()} → {tail} "
              f"({span_d}d, tail age {age_h:.0f}h)", file=sys.stderr, flush=True)
        if age_h > max_stale_hours:
            problems.append(f"{pair}: 末尾 {tail} が {age_h:.0f}h stale")
        if span_d < LOOKBACK_DAYS + 30:
            problems.append(f"{pair}: カバレッジ {span_d}d < {LOOKBACK_DAYS + 30}d")
    if problems:
        raise SystemExit("[grid] DATA CHECK FAILED:\n  " + "\n  ".join(problems))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", action="store_true",
                    help="baseline × GBP_USD × 90d のみ (配管検証、保存なし)")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--lookback", type=int, default=LOOKBACK_DAYS)
    ap.add_argument("--stats-only", action="store_true",
                    help="BT をスキップし checkpoint から統計・出力のみ再実行")
    ap.add_argument("--out-suffix", default="",
                    help="出力ファイル名 suffix (感度 run の退避用)")
    args = ap.parse_args()

    if args.smoke:
        job = {"tp_mult": 1.0, "sl_mult": 1.0, "lookback": 90,
               "pairs": ["GBP_USD"]}
        res = run_config(job)
        rows = enrich([t for ts in res["pairs"].values() for t in ts])
        print(json.dumps({"smoke": True,
                          "n_rows": len(rows),
                          "sample": rows[:3],
                          "summary": summarize_config(rows)["pooled"],
                          "errors": res["errors"]},
                         indent=2, ensure_ascii=False))
        return

    t0 = time.time()
    if args.stats_only:
        with open(CHECKPOINT) as f:
            results = json.load(f)
        print(f"[grid] stats-only: {len(results)} configs from checkpoint",
              file=sys.stderr, flush=True)
    else:
        check_data_freshness(PAIRS)
        configs = [BASELINE] + GRID
        jobs = [{"tp_mult": tp, "sl_mult": sl, "lookback": args.lookback,
                 "pairs": PAIRS} for (tp, sl) in configs]
        results = {}
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=args.workers, maxtasksperchild=1) as pool:
            for res in pool.imap_unordered(run_config, jobs):
                key = f"tp{res['tp_mult']}_sl{res['sl_mult']}"
                results[key] = res
                print(f"[grid] config {key} done "
                      f"({len(results)}/{len(jobs)}, {time.time()-t0:.0f}s total)",
                      file=sys.stderr, flush=True)
                with open(CHECKPOINT, "w") as f:
                    json.dump(results, f, default=_json_default)

    # ── 統計 (親プロセス) ──
    analysis = {}
    pvals = {}
    for key, res in sorted(results.items()):
        all_trades = [t for ts in res["pairs"].values() for t in ts]
        rows = enrich(all_trades)
        eval_rows = [r for r in rows if r["entry_time"][:10] < DIAG_START_UTC]
        diag_rows = [r for r in rows if r["entry_time"][:10] >= DIAG_START_UTC]
        summ = summarize_config(eval_rows)
        boot = day_block_bootstrap(eval_rows, "net_theory_pips", N_BOOT, SEED)
        wf = wf_folds(eval_rows, "net_theory_pips", WF_FOLDS)
        is_grid = (res["tp_mult"], res["sl_mult"]) in GRID
        analysis[key] = {
            "tp_mult": res["tp_mult"], "sl_mult": res["sl_mult"],
            "in_grid": is_grid,
            "n_eval": len(eval_rows), "n_diag_excluded": len(diag_rows),
            "summary": summ, "bootstrap": boot, "walk_forward": wf,
            "errors": res["errors"],
        }
        if is_grid and boot["p"] is not None:
            pvals[key] = boot["p"]

    fdr = bh_fdr(pvals, FDR_Q) if pvals else {}
    passing = []
    for key, f in fdr.items():
        a = analysis[key]
        cond_a = f["survive"]
        cond_b = a["walk_forward"]["pos_ratio"] >= 2 / 3 - 1e-9
        cond_c = a["summary"]["pooled"].get("ev_theory_pips", -1) > 0
        a["gates"] = {"a_fdr": cond_a, "b_wf": cond_b, "c_ev": cond_c,
                      "pass": cond_a and cond_b and cond_c}
        if a["gates"]["pass"]:
            passing.append(key)

    verdict = "PASS" if passing else "FAIL"
    output = {
        "task": "20260707-1640-exit-repair-tp-sl-grid",
        "prereg": "knowledge-base/wiki/decisions/exit-repair-tp-sl-prereg-2026-07-07.md",
        "rule": "R1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "engine": "app.run_daytrade_backtest backtest_mode=True",
        "interval": INTERVAL, "lookback_days": args.lookback,
        "diag_window_excluded_from": DIAG_START_UTC,
        "cells": {f"{et}__{p}": n for (et, p), n in CELLS.items()},
        "friction": {"theory_rt_pips": FRICTION_THEORY,
                     "floor_sensitivity_pips": FRICTION_FLOOR,
                     "method": "BT内部摩擦を算術足し戻し→gross→理論RT控除 (保守側)"},
        "env": {**BASE_ENV, **PARITY_ENV,
                "BT_TPSL_MULT_TYPES": ",".join(TARGET_TYPES)},
        "n_boot": N_BOOT, "seed": SEED, "fdr_q": FDR_Q,
        "mechanical_verdict": verdict,
        "passing_configs": passing,
        "bh_fdr": fdr,
        "configs": analysis,
        "caveats": [
            "Time-decay SL tightening (app.py L7005-7009) は BE/Trail ablation の対象外で"
            " BT/live 双方に存在するため残置 (prod parity)",
            "entry 摩擦はバリア幾何に埋め込み済み (算術 gross 化では path 効果は不可逆)"
            " — 理論摩擦控除は二重計上方向 = 保守側",
            "エントリー母集団は cooldown の exit 依存で構成間に微小ドリフトあり"
            " (ナイフエッジ検査 #3 で隣接格子整合を確認)",
            "MFE/MAE バー粒度 (tick 未満) の実行差は残存リスク (pre-reg §7)",
        ],
    }
    out_json = OUT_JSON.replace(".json", f"{args.out_suffix}.json")
    out_md = OUT_MD.replace(".md", f"{args.out_suffix}.md")
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(output, f, indent=1, ensure_ascii=False, default=_json_default)
    print(f"[grid] saved {out_json}", file=sys.stderr, flush=True)

    # ── markdown 集計 ──
    lines = [
        "# exit-repair TP/SL grid BT 結果 (機械集計)",
        "",
        f"- 生成: {output['generated_utc']} / verdict(機械): **{verdict}**",
        f"- 評価: {args.lookback}d 15m、診断窓 {DIAG_START_UTC}〜 除外、"
        f"摩擦 = per-pair 理論 RT 控除",
        f"- PASS 条件: BH-FDR q={FDR_Q} (m={len(GRID)}) ∧ WF pos_ratio≥2/3 ∧ EV>0",
        "",
        "| config | N | WR% | EV_theory | EV_floor | payoff | TPhit | p | FDR | WF+ | PASS |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key in sorted(analysis, key=lambda k: (analysis[k]["tp_mult"],
                                               analysis[k]["sl_mult"])):
        a = analysis[key]
        po = a["summary"]["pooled"]
        f_ = fdr.get(key, {})
        g = a.get("gates", {})
        tag = "**PASS**" if g.get("pass") else ("—" if not a["in_grid"] else "fail")
        lines.append(
            f"| {key}{' (base)' if not a['in_grid'] else ''} | {po.get('n', 0)} "
            f"| {po.get('wr_pct', '—')} | {po.get('ev_theory_pips', '—')} "
            f"| {po.get('ev_floor_pips', '—')} | {po.get('payoff', '—')} "
            f"| {po.get('tp_hit_ratio', '—')} | {a['bootstrap'].get('p', '—')} "
            f"| {'✓' if f_.get('survive') else '✗' if a['in_grid'] else '—'} "
            f"| {a['walk_forward']['pos_ratio']} | {tag} |")
    lines += ["", "セル別詳細は JSON (`configs.*.summary.cells`) を参照。", ""]
    with open(out_md, "w") as f:
        f.write("\n".join(lines))
    print(f"[grid] saved {out_md}", file=sys.stderr, flush=True)
    print(json.dumps({"mechanical_verdict": verdict,
                      "passing_configs": passing,
                      "elapsed_sec": round(time.time() - t0, 1)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
