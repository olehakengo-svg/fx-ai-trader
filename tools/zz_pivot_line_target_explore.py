#!/usr/bin/env python3
"""
zz_pivot_line_target_explore.py — ZZ pivot確定 × 水平線ターゲット explore (2026-08-12)

pre-reg: knowledge-base/wiki/decisions/zz-pivot-line-target-explore-prereg-2026-08-12.md
アルゴリズムは TV "ZZ Spec Visualizer v1" (bt-results/tv-overlays/zz_spec_visualizer_v1.pine)
と同一。user 裁量手法の機械核:
  頂点/底の zigzag 確定イベント → 逆張り方向 → 目処 = 最寄りの反対側ピボット水準
  → race: 目処到達 vs 同距離逆行のどちらが先か (摩擦込み per-event pnl)。

絶対規律:
  1. 因果性: 水準は当該イベントより前に確定したピボットのみ。entry = 確定バーの次バー Open。
  2. explore 窓 2014-2021 hard-clamp。OOS (2022+) は --stage tvcheck (非方向統計のみ) 以外不可触。
  3. two-pass: --stage headroom は方向アウトカムを計算しない (race 関数は primary からのみ呼出)。
     --stage primary は headroom verdict JSON が無ければ REFUSED。
  4. silent except 禁止。skip は理由付き count。
  5. モジュールトップ副作用禁止。

CLI:
  python3 tools/zz_pivot_line_target_explore.py --stage headroom
  python3 tools/zz_pivot_line_target_explore.py --stage primary [--write-events]
  python3 tools/zz_pivot_line_target_explore.py --stage tvcheck   # TV 整合 (非方向統計のみ)
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "cache" / "massive"
OUT_DIR = ROOT / "knowledge-base" / "raw" / "bt-results"

# ── 凍結パラメータ (pre-reg §2-§5) ──
PAIRS = ["EUR_USD", "GBP_USD", "USD_JPY", "EUR_JPY", "AUD_USD", "USD_CAD"]
MULTS = [1.0, 1.5, 2.0, 3.0]
ATR_PERIOD = 14
LEVELS_N = 10
MAX_HOLD = 500          # 1H bars
EXPLORE_START = "2014-01-01"
EXPLORE_END = "2022-01-01"    # exclusive — OOS hard-clamp
SEED = 20260812
N_PERM = 10_000
HEADROOM_MULT = 10.0
N_FLOOR = 200
MIN_SURVIVORS = 3
FDR_Q = 0.10
M_TESTS = len(PAIRS) * len(MULTS)   # 24 (declared)
STRESS_RT = 1.25

RT = {  # frozen per-pair RT friction (pips) — wave-1 protocol
    "EUR_USD": 2.00, "GBP_USD": 4.53, "USD_JPY": 2.14,
    "EUR_JPY": 2.50, "AUD_USD": 2.50, "USD_CAD": 2.80,
}

HEADROOM_JSON = OUT_DIR / "zz-pivot-line-target-headroom-2026-08-12.json"
PRIMARY_JSON = OUT_DIR / "zz-pivot-line-target-primary-2026-08-12.json"
EVENTS_CSV = OUT_DIR / "zz-pivot-line-target-events-2026-08-12.csv"


def _pip(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


def load_1h(pair: str, start: str, end: str) -> pd.DataFrame:
    """MASSIVE 15m parquet → UTC 1H resample。窓 hard-clamp。"""
    f = DATA_DIR / f"{pair}_15m.parquet"
    df = pd.read_parquet(f)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df.loc[(df.index >= pd.Timestamp(start, tz="UTC")) & (df.index < pd.Timestamp(end, tz="UTC"))]
    h = df.resample("1h").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    return h


def _atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> np.ndarray:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev = close.shift(1)
    tr = pd.concat([(high - low), (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean().to_numpy()


@dataclass
class Event:
    pair: str
    mult: float
    t_confirm: pd.Timestamp
    side: str            # "SELL" (頂点確定) / "BUY" (底確定)
    pivot_price: float
    pivot_idx: int
    confirm_idx: int
    lag_bars: int
    adverse_pips: float  # |pivot − confirm close| / pip
    entry: float         # next bar Open
    target: float
    d_pips: float        # |entry − target| / pip


def detect_events(pair: str, df: pd.DataFrame, mult: float) -> tuple[list[Event], dict]:
    """ZZ Spec Visualizer v1 と同一の zigzag + 目処。方向アウトカムは計算しない。"""
    high = df["High"].to_numpy()
    low = df["Low"].to_numpy()
    close = df["Close"].to_numpy()
    open_ = df["Open"].to_numpy()
    atr = _atr(df)
    pip = _pip(pair)
    n = len(df)

    skips = {"no_target": 0, "gap_past_target": 0, "no_next_bar": 0}
    events: list[Event] = []
    piv_p: list[float] = []
    piv_high: list[bool] = []

    direction = 1
    ext_p = high[0]
    ext_b = 0
    for i in range(1, n):
        thr = atr[i] * mult
        if not np.isfinite(thr) or thr <= 0:
            continue
        confirmed = False
        if direction == 1:
            if high[i] > ext_p:
                ext_p, ext_b = high[i], i
            elif ext_p - low[i] >= thr:
                confirmed, is_high, c_price, c_bar = True, True, ext_p, ext_b
                direction, ext_p, ext_b = -1, low[i], i
        else:
            if low[i] < ext_p:
                ext_p, ext_b = low[i], i
            elif high[i] - ext_p >= thr:
                confirmed, is_high, c_price, c_bar = True, False, ext_p, ext_b
                direction, ext_p, ext_b = 1, high[i], i
        if not confirmed:
            continue

        # 目処: 直近 LEVELS_N 個の既確定ピボットから最寄りの反対側水準 (因果: push 前に計算)
        tgt = None
        cnt = 0
        for j in range(len(piv_p) - 1, -1, -1):
            if cnt >= LEVELS_N:
                break
            cnt += 1
            lp, lh = piv_p[j], piv_high[j]
            if is_high:
                if (not lh) and lp < close[i] and (tgt is None or lp > tgt):
                    tgt = lp
            else:
                if lh and lp > close[i] and (tgt is None or lp < tgt):
                    tgt = lp

        lag_bars = i - c_bar
        adverse = abs(c_price - close[i]) / pip

        if tgt is None:
            skips["no_target"] += 1
        elif i + 1 >= n:
            skips["no_next_bar"] += 1
        else:
            entry = open_[i + 1]
            d = (entry - tgt) if is_high else (tgt - entry)
            if d <= 0:
                skips["gap_past_target"] += 1
            else:
                events.append(Event(
                    pair=pair, mult=mult, t_confirm=df.index[i],
                    side="SELL" if is_high else "BUY",
                    pivot_price=float(c_price), pivot_idx=c_bar, confirm_idx=i,
                    lag_bars=lag_bars, adverse_pips=float(adverse),
                    entry=float(entry), target=float(tgt), d_pips=float(d / pip),
                ))

        piv_p.append(float(c_price))
        piv_high.append(bool(is_high))

    return events, skips


# ── primary 専用: race アウトカム (headroom stage からは呼出されない) ──

def race_outcomes(pair: str, df: pd.DataFrame, events: list[Event]) -> list[dict]:
    high = df["High"].to_numpy()
    low = df["Low"].to_numpy()
    close = df["Close"].to_numpy()
    pip = _pip(pair)
    n = len(df)
    rt = RT[pair]
    out = []
    for ev in events:
        s = ev.confirm_idx + 1               # entry bar (race は entry bar から有効)
        e = min(s + MAX_HOLD, n)
        d_price = ev.d_pips * pip
        if ev.side == "SELL":
            fav_px, adv_px = ev.entry - d_price, ev.entry + d_price
            fav_hit = low[s:e] <= fav_px
            adv_hit = high[s:e] >= adv_px
        else:
            fav_px, adv_px = ev.entry + d_price, ev.entry - d_price
            fav_hit = high[s:e] >= fav_px
            adv_hit = low[s:e] <= adv_px
        fi = int(np.argmax(fav_hit)) if fav_hit.any() else -1
        ai = int(np.argmax(adv_hit)) if adv_hit.any() else -1
        if fi >= 0 and (ai < 0 or fi < ai):
            result, gross = "win", ev.d_pips
        elif ai >= 0 and (fi < 0 or ai < fi):
            result, gross = "loss", -ev.d_pips
        elif fi >= 0 and fi == ai:
            result, gross = "loss_tie", -ev.d_pips     # 同一バー両触れ = 保守的に loss
        else:
            last = min(e, n) - 1
            move = (close[last] - ev.entry) / pip
            gross = move if ev.side == "BUY" else -move
            result = "timeout"
        out.append({
            "pair": ev.pair, "mult": ev.mult, "t": str(ev.t_confirm), "side": ev.side,
            "entry": ev.entry, "target": ev.target, "d_pips": ev.d_pips,
            "lag_bars": ev.lag_bars, "adverse_pips": ev.adverse_pips,
            "result": result, "gross_pips": float(gross), "net_pips": float(gross - rt),
            "iso_week": pd.Timestamp(ev.t_confirm).strftime("%G-W%V"),
        })
    return out


def perm_pvalue(rows: list[dict], rng: np.random.Generator) -> float:
    """ISO週 block sign-flip permutation (片側: mean net > 0)。"""
    weeks: dict[str, float] = {}
    for r in rows:
        weeks[r["iso_week"]] = weeks.get(r["iso_week"], 0.0) + r["net_pips"]
    sums = np.array(list(weeks.values()))
    n_ev = len(rows)
    obs = sums.sum() / n_ev
    signs = rng.choice([-1.0, 1.0], size=(N_PERM, len(sums)))
    perm = (signs * sums).sum(axis=1) / n_ev
    return float((np.sum(perm >= obs) + 1) / (N_PERM + 1))


def bh_fdr(pvals: dict, q: float = FDR_Q, m: int = M_TESTS) -> set:
    """BH-FDR。m は宣言済み検定数 24 に固定 (保守的)。"""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    passed, max_k = set(), 0
    for k, (key, p) in enumerate(items, start=1):
        if p <= q * k / m:
            max_k = k
    for k, (key, p) in enumerate(items, start=1):
        if k <= max_k:
            passed.add(key)
    return passed


def stage_headroom() -> None:
    res = {"stage": "headroom", "prereg": "zz-pivot-line-target-explore-prereg-2026-08-12",
           "window": [EXPLORE_START, EXPLORE_END], "cells": {}, "survivors": []}
    for pair in PAIRS:
        df = load_1h(pair, EXPLORE_START, EXPLORE_END)
        for mult in MULTS:
            events, skips = detect_events(pair, df, mult)
            key = f"{pair}|x{mult}"
            if events:
                d_med = float(np.median([e.d_pips for e in events]))
                lag_med = float(np.median([e.lag_bars for e in events]))
                adv_med = float(np.median([e.adverse_pips for e in events]))
            else:
                d_med = lag_med = adv_med = float("nan")
            n_ev = len(events)
            gate_a = bool(n_ev >= N_FLOOR and np.isfinite(d_med) and d_med >= HEADROOM_MULT * RT[pair])
            res["cells"][key] = {
                "n_events": n_ev, "skips": skips, "d_pips_median": d_med,
                "d_over_rt": d_med / RT[pair] if np.isfinite(d_med) else None,
                "lag_bars_median": lag_med, "adverse_pips_median": adv_med,
                "gate_a_pass": gate_a,
            }
            if gate_a:
                res["survivors"].append(key)
            print(f"{key}: N={n_ev} D_med={d_med:.1f}p ({d_med / RT[pair]:.1f}xRT) "
                  f"lag={lag_med:.0f} adv={adv_med:.1f}p gateA={'PASS' if gate_a else 'FAIL'} skips={skips}")
    res["verdict"] = "PROCEED" if len(res["survivors"]) >= MIN_SURVIVORS else "STOP"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HEADROOM_JSON.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(f"\nheadroom verdict: {res['verdict']} ({len(res['survivors'])}/{M_TESTS} survivors) -> {HEADROOM_JSON}")


def stage_primary(write_events: bool) -> None:
    if not HEADROOM_JSON.exists():
        print("REFUSED: headroom verdict JSON がありません。--stage headroom を先に実行。", file=sys.stderr)
        sys.exit(2)
    hr = json.loads(HEADROOM_JSON.read_text())
    if hr.get("verdict") != "PROCEED":
        print(f"REFUSED: headroom verdict = {hr.get('verdict')} (PROCEED のみ pass-2 可)", file=sys.stderr)
        sys.exit(2)
    survivors = set(hr["survivors"])
    rng = np.random.default_rng(SEED)
    all_rows: list[dict] = []
    cells: dict[str, dict] = {}
    pvals: dict[str, float] = {}
    for pair in PAIRS:
        keys = [f"{pair}|x{m}" for m in MULTS if f"{pair}|x{m}" in survivors]
        if not keys:
            continue
        df = load_1h(pair, EXPLORE_START, EXPLORE_END)
        for mult in MULTS:
            key = f"{pair}|x{mult}"
            if key not in survivors:
                continue
            events, _ = detect_events(pair, df, mult)
            rows = race_outcomes(pair, df, events)
            all_rows.extend(rows)
            n = len(rows)
            wins = sum(1 for r in rows if r["result"] == "win")
            losses = sum(1 for r in rows if r["result"].startswith("loss"))
            timeouts = sum(1 for r in rows if r["result"] == "timeout")
            net = np.array([r["net_pips"] for r in rows])
            gross = np.array([r["gross_pips"] for r in rows])
            p = perm_pvalue(rows, rng)
            pvals[key] = p
            # Gate E: 最大単一 ISO週寄与
            wk: dict[str, float] = {}
            for r in rows:
                wk[r["iso_week"]] = wk.get(r["iso_week"], 0.0) + r["net_pips"]
            tot = float(net.sum())
            gate_e = bool(tot > 0 and max(abs(v) for v in wk.values()) / abs(tot) <= 0.5) if tot != 0 else False
            stressed_mean = float(gross.mean() - RT[pair] * STRESS_RT)
            cells[key] = {
                "n": n, "wr_decided": wins / (wins + losses) if wins + losses else None,
                "timeouts": timeouts, "mean_gross_pips": float(gross.mean()),
                "mean_net_pips": float(net.mean()), "stressed_net_pips": stressed_mean,
                "perm_p_one_sided": p, "gate_e_week_conc": gate_e,
            }
            print(f"{key}: N={n} WR(decided)={cells[key]['wr_decided']:.3f} "
                  f"net={net.mean():+.2f}p stressed={stressed_mean:+.2f}p p={p:.4f} timeouts={timeouts}")
    fdr_pass = bh_fdr(pvals)
    verdict_cells = [k for k in fdr_pass
                     if cells[k]["stressed_net_pips"] > 0 and cells[k]["gate_e_week_conc"] and cells[k]["n"] >= N_FLOOR]
    out = {"stage": "primary", "prereg": "zz-pivot-line-target-explore-prereg-2026-08-12",
           "seed": SEED, "n_perm": N_PERM, "m_tests_declared": M_TESTS,
           "cells": cells, "fdr_q010_pass": sorted(fdr_pass), "all_gates_pass": sorted(verdict_cells),
           "explore_verdict": "PROCEED" if verdict_cells else "FAIL"}
    PRIMARY_JSON.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"\nprimary verdict: {out['explore_verdict']} | FDR pass: {sorted(fdr_pass)} | "
          f"all-gates: {sorted(verdict_cells)} -> {PRIMARY_JSON}")
    if write_events:
        pd.DataFrame(all_rows).to_csv(EVENTS_CSV, index=False)
        print(f"events -> {EVENTS_CSV}")


def stage_tvcheck() -> None:
    """TV ZZ Spec Visualizer v1 (USDJPY 1H, ATR×2) との非方向統計の整合チェック (pre-reg §6)。
    方向アウトカムは一切計算しない。TV 実測 (2026-08-11): lag_med=3本, adverse_med=44.1p, d_med=25.9p。"""
    df = load_1h("USD_JPY", "2023-08-01", "2026-08-12")
    events, skips = detect_events("USD_JPY", df, 2.0)
    lag = float(np.median([e.lag_bars for e in events]))
    adv = float(np.median([e.adverse_pips for e in events]))
    d = float(np.median([e.d_pips for e in events]))
    print(f"tvcheck USD_JPY 1H x2.0 (2023-08..2026-08): N={len(events)} lag_med={lag:.0f}本 "
          f"adverse_med={adv:.1f}p d_med={d:.1f}p skips={skips}")
    print("TV 実測 (ロード履歴): lag_med=3本 adverse_med=44.1p d_med=25.9p")
    for name, ours, tv in [("lag", lag, 3.0), ("adverse", adv, 44.1), ("d", d, 25.9)]:
        dev = abs(ours - tv) / tv
        print(f"  {name}: python={ours:.1f} tv={tv:.1f} dev={dev * 100:.0f}% {'OK' if dev <= 0.20 else '⚠️ >20%'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["headroom", "primary", "tvcheck"])
    ap.add_argument("--write-events", action="store_true")
    args = ap.parse_args()
    if args.stage == "headroom":
        stage_headroom()
    elif args.stage == "primary":
        stage_primary(args.write_events)
    else:
        stage_tvcheck()


if __name__ == "__main__":
    main()
