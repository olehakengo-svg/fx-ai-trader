#!/usr/bin/env python3
"""W3-2 fx_quote_spread_state — QA / coverage / headroom pre-gate / explore (台帳 #17).

凍結プロトコル: knowledge-base/wiki/analyses/fx-quote-spread-state-explore-prereg-2026-07-29.md
敵対的検証 6 条件: knowledge-base/raw/analysis/wave3-adversarial-verification-2026-07-29.md [W3-2]

ステージ分離 (条件 1 の「摩擦測定は forward return への一切の look の前」をコード構造で保証):
  --stage qa        panel QA + coverage assert のみ (イベントなし、リターンなし)
  --stage headroom  イベント抽出 + entry + イベント条件付き摩擦 headroom gate。
                    forward return 系列はこのステージでは一切構築しない
  --stage explore   凍結測定 (primary + gates ii-vi)。explore 窓 2014-2021 のみ
  --stage oos       OOS 単一接触 (explore PASS 記録がある場合のみ、--unlock-oos 必須)

イベント定義 / 閾値は全て凍結定数 (grid なし)。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PANEL_DIR = ROOT / "data" / "external" / "quote_spread"

PAIRS = ["EUR_USD", "GBP_USD", "USD_JPY"]
PIP = {"EUR_USD": 1e4, "GBP_USD": 1e4, "USD_JPY": 1e2}

# KB 凍結 RT (wiki/analyses/friction-analysis.md; cot prereg と同値系)
KB_RT = {"EUR_USD": 2.00, "GBP_USD": 4.53, "USD_JPY": 2.14}
KB_SPREAD = {"EUR_USD": 0.7, "GBP_USD": 1.3, "USD_JPY": 0.7}

# ---- QA (凍結) ----
MIN_QUOTES = 30          # 窓内有効 quote 最小数
MAX_FIRST_LAG_S = 900    # 最初の quote が target から 15 分以内
MAX_CROSSED_SHARE = 0.9  # crossed/locked 比率上限
SPREAD_SANITY_FRAC = 0.005  # spread > mid の 0.5% はデータ異常として invalid

# ---- coverage assert (凍結、事後緩和禁止) ----
COVERAGE_MIN_VALID_SHARE = 0.80  # 年次: 有効サンプル比率
EXPLORE_YEARS = list(range(2014, 2022))
MAX_SKIP_YEARS_PER_PAIR = 1      # explore 8 年中 skip 許容は 1 年まで
MIN_SURVIVING_PAIRS = 2

# ---- baseline / イベント (凍結) ----
BASELINE_N = 60          # trailing 同スロット有効サンプル数
BASELINE_MIN = 40
ONSET_RATIO = 3.0        # spread >= 3.0 x 同スロット baseline median
ONSET_ELEV_PIPS = 1.0    # 絶対 elevation floor (feed 極小スプレッド期の擬似比率対策)
PERSIST_RATIO = 2.0      # 次サンプルでも >= 2.0 x (異常持続 >= 2 連続サンプル)
PERSIST_MAX_GAP_STEPS = 2  # 次サンプルが 2 グリッド step (6h) 以内に存在すること
MOVE_SMALL_MULT = 2.0    # |Δlog mid| <= 2 x trailing 同スロット median (price_shock 分離)
DEDUP_SAMPLES = 8        # 24h 以内の再オンセットは同一イベントに併合
NORM_RATIO = 1.5         # entry: spread <= 1.5 x (onset 時点の同スロット baseline)
ENTRY_MAX_WAIT = 16      # 16 サンプル (~48h) 以内に正常化しなければ event drop

# ---- headroom 事前ゲート (凍結) ----
HEADROOM_MIN = 10.0
SCALE24_N = 60           # trailing 同スロット 24h |move| median の窓
SCALE24_MIN = 40

# ---- primary (凍結) ----
EXPLORE_START = "2014-01-01"
EXPLORE_END = "2021-12-31"
EXPLORE_PANEL_CUTOFF = "2022-01-31"   # exit 用バッファ込み。OOS 域には触れない
OOS_START = "2022-01-01"
OOS_END = "2026-06-30"
MIN_EVENTS = 30
N_BOOT = 10000
SEED = 20260729
ALPHA = 0.05
MAX_EXIT_CAL_DAYS = 4    # 同スロット翌営業日 exit が 4 暦日超なら return set から drop
YEAR_END_SHARE_MAX = 0.50

NY = ZoneInfo("America/New_York")
LON = ZoneInfo("Europe/London")


# ---------------------------------------------------------------- panel / QA

def load_panel(cutoff: str | None = None) -> pd.DataFrame:
    parts = []
    for f in sorted(PANEL_DIR.glob("*.parquet")):
        parts.append(pd.read_parquet(f))
    if not parts:
        raise FileNotFoundError(f"no panel parquet under {PANEL_DIR}")
    df = pd.concat(parts, ignore_index=True)
    df = df.drop_duplicates(subset=["pair", "ts_utc"]).sort_values(["pair", "ts_utc"])
    if cutoff:
        df = df[df["ts_utc"] <= pd.Timestamp(cutoff, tz="UTC")]
    return df.reset_index(drop=True)


def qa_panel(df: pd.DataFrame) -> pd.DataFrame:
    """QA フラグ付与 (凍結ルール)。土曜行はグリッド生成側で構造的に排除済みを assert。"""
    ny_ts = pd.to_datetime(df["ts_utc"]).dt.tz_convert("America/New_York")
    assert (ny_ts.dt.weekday != 5).all(), "Saturday sample leaked into grid"
    n_used = df["n_used"].fillna(0)
    crossed = df["n_crossed"].fillna(0)
    denom = (n_used + crossed).replace(0, np.nan)
    crossed_share = (crossed / denom).fillna(0.0)
    sanity_cap_pips = df.apply(
        lambda r: (r["mid_med"] * PIP[r["pair"]] * SPREAD_SANITY_FRAC)
        if pd.notna(r["mid_med"]) else np.nan, axis=1)
    valid = (
        (n_used >= MIN_QUOTES)
        & df["first_quote_lag_s"].notna()
        & (df["first_quote_lag_s"] <= MAX_FIRST_LAG_S)
        & (crossed_share <= MAX_CROSSED_SHARE)
        & df["spread_med_pips"].notna()
        & df["mid_med"].notna()
        & (df["spread_med_pips"] <= sanity_cap_pips)
    )
    out = df.copy()
    out["valid"] = valid.values
    out["crossed_share"] = crossed_share.values
    return out


def coverage_report(df: pd.DataFrame) -> dict:
    """年次 coverage assert (凍結: 事後緩和禁止)。"""
    rep: dict = {"per_pair": {}, "explore_pass_pairs": [], "skipped_years": {}}
    for pair in PAIRS:
        sub = df[df["pair"] == pair]
        years = {}
        for y, g in sub.groupby(pd.to_datetime(sub["ny_date"]).dt.year):
            years[int(y)] = {
                "samples": int(len(g)),
                "valid": int(g["valid"].sum()),
                "valid_share": round(float(g["valid"].mean()), 4) if len(g) else 0.0,
            }
        rep["per_pair"][pair] = years
        fails = [y for y in EXPLORE_YEARS
                 if years.get(y, {}).get("valid_share", 0.0) < COVERAGE_MIN_VALID_SHARE]
        rep["skipped_years"][pair] = fails
        if len(fails) <= MAX_SKIP_YEARS_PER_PAIR:
            rep["explore_pass_pairs"].append(pair)
    rep["pass"] = len(rep["explore_pass_pairs"]) >= MIN_SURVIVING_PAIRS
    return rep


# ------------------------------------------------------- baselines / events

def _dst_mismatch(date: dt.date) -> bool:
    """US (NY) と EU (London) の DST 状態が不一致の日 (擬似 diurnal シフト窓)。"""
    t = dt.datetime(date.year, date.month, date.day, 12, 0)
    ny_dst = bool(t.replace(tzinfo=NY).dst())
    lon_dst = bool(t.replace(tzinfo=LON).dst())
    return ny_dst != lon_dst


def build_baselines(df: pd.DataFrame) -> pd.DataFrame:
    """同スロット trailing baseline (spread median / |Δlog mid| median) を付与。
    forward return は構築しない (headroom ステージ互換)。"""
    df = df.sort_values(["pair", "ts_utc"]).reset_index(drop=True)
    df["base_spread"] = np.nan
    df["base_move"] = np.nan
    df["move_in"] = np.nan
    df["scale24_pips"] = np.nan
    for pair, g in df.groupby("pair"):
        g = g.sort_values("ts_utc")
        vidx = g.index[g["valid"]]
        vmid = df.loc[vidx, "mid_med"].astype(float)
        # 直前有効サンプルからの |Δlog mid| (スロット遷移 move)
        move = np.abs(np.log(vmid).diff())
        df.loc[vidx, "move_in"] = move.values
        for slot, gs in g[g["valid"]].groupby("ny_slot"):
            gs = gs.sort_values("ts_utc")
            sp = gs["spread_med_pips"].astype(float)
            base = sp.shift(1).rolling(BASELINE_N, min_periods=BASELINE_MIN).median()
            df.loc[gs.index, "base_spread"] = base.values
            mv = df.loc[gs.index, "move_in"].astype(float)
            basemv = mv.shift(1).rolling(BASELINE_N, min_periods=BASELINE_MIN).median()
            df.loc[gs.index, "base_move"] = basemv.values
            # 24h move (同スロット、直前営業日→当日) ending at each sample
            mid = gs["mid_med"].astype(float)
            mv24 = (mid.diff().abs() * PIP[pair])
            scale = mv24.shift(1).rolling(SCALE24_N, min_periods=SCALE24_MIN).median()
            df.loc[gs.index, "scale24_pips"] = scale.values
    return df


def detect_events(df: pd.DataFrame, window_start: str, window_end: str) -> list[dict]:
    """凍結イベント定義でオンセット + entry を抽出。forward return 非接触。"""
    ws = pd.Timestamp(window_start, tz="UTC")
    we = pd.Timestamp(window_end, tz="UTC") + pd.Timedelta(days=1)
    events: list[dict] = []
    for pair in PAIRS:
        g = df[(df["pair"] == pair) & df["valid"]].sort_values("ts_utc").reset_index(drop=True)
        n = len(g)
        last_onset_i = -10**9
        for i in range(n):
            row = g.iloc[i]
            ts = row["ts_utc"]
            if ts < ws or ts >= we:
                continue
            b = row["base_spread"]
            if not np.isfinite(b) or b <= 0:
                continue
            ratio = row["spread_med_pips"] / b
            elev = row["spread_med_pips"] - b
            if ratio < ONSET_RATIO or elev < ONSET_ELEV_PIPS:
                continue
            # price_shock 分離: 同時 |move| 小
            if not (np.isfinite(row["move_in"]) and np.isfinite(row["base_move"])
                    and row["base_move"] > 0):
                continue
            if row["move_in"] > MOVE_SMALL_MULT * row["base_move"]:
                continue
            # 持続 >= 2 連続サンプル (次有効サンプルが 6h 以内 & ratio >= 2)
            if i + 1 >= n:
                continue
            nxt = g.iloc[i + 1]
            gap_h = (nxt["ts_utc"] - ts).total_seconds() / 3600.0
            if gap_h > 3.0 * PERSIST_MAX_GAP_STEPS + 0.1:
                continue
            nb = nxt["base_spread"]
            if not (np.isfinite(nb) and nb > 0
                    and nxt["spread_med_pips"] / nb >= PERSIST_RATIO):
                continue
            # dedup 24h
            if i - last_onset_i < DEDUP_SAMPLES:
                last_onset_i = i
                continue
            # DST mismatch 除外 (条件 4)
            d = pd.Timestamp(ts).tz_convert("America/New_York").date()
            if _dst_mismatch(d):
                last_onset_i = i
                continue
            last_onset_i = i
            # onset 時点の各スロット baseline を凍結 (entry 正常化判定用)
            slot_base: dict[int, float] = {}
            for slot in sorted(g["ny_slot"].unique()):
                prior = g[(g["ny_slot"] == slot) & (g["ts_utc"] < ts)]
                if len(prior):
                    v = prior.iloc[-1]["base_spread"]
                    if np.isfinite(v) and v > 0:
                        slot_base[int(slot)] = float(v)
            # 異常 run の peak ratio (診断 + gate ii の magnitude)
            peak = float(ratio)
            j = i + 1
            while j < n:
                rj = g.iloc[j]
                bj = slot_base.get(int(rj["ny_slot"]))
                if bj is None:
                    break
                rr = rj["spread_med_pips"] / bj
                if rr < NORM_RATIO:
                    break
                peak = max(peak, float(rr))
                j += 1
            # entry = onset 後、slot baseline 比 <= 1.5 の最初の有効サンプル
            entry = None
            for k in range(i + 1, min(i + 1 + ENTRY_MAX_WAIT, n)):
                rk = g.iloc[k]
                bk = slot_base.get(int(rk["ny_slot"]))
                if bk is None or bk <= 0:
                    continue
                if rk["spread_med_pips"] / bk <= NORM_RATIO:
                    entry = rk
                    entry_ratio = float(rk["spread_med_pips"] / bk)
                    break
            ev = {
                "pair": pair,
                "onset_ts": str(ts),
                "onset_ratio": float(ratio),
                "peak_ratio": peak,
                "onset_spread_pips": float(row["spread_med_pips"]),
                "onset_base_pips": float(b),
                "year": int(pd.Timestamp(ts).year),
                "normalized": entry is not None,
            }
            if entry is not None:
                ev.update({
                    "entry_ts": str(entry["ts_utc"]),
                    "entry_date": str(entry["ny_date"]),
                    "entry_slot": int(entry["ny_slot"]),
                    "entry_ratio": entry_ratio,
                    "entry_spread_pips": float(entry["spread_med_pips"]),
                    "entry_scale24": (float(entry["scale24_pips"])
                                      if np.isfinite(entry["scale24_pips"]) else None),
                    "wait_h": (pd.Timestamp(entry["ts_utc"]) - ts).total_seconds() / 3600.0,
                })
            events.append(ev)
    return events


# ------------------------------------------------------------- headroom gate

def headroom_gate(events: list[dict]) -> dict:
    """条件 1: イベント条件付き実測スプレッドでの摩擦 headroom 事前ゲート。
    forward return には一切接触しない (numerator = 後方 trailing 24h vol scale)。
    RT_event = KB_RT − KB_spread + entry_ratio × KB_spread (実測相対 elevation を
    配備先ベース摩擦へ乗法変換)。"""
    usable = [e for e in events if e.get("normalized") and e.get("entry_scale24")]
    per_pair = {}
    pooled_hr: list[float] = []
    for pair in PAIRS:
        evs = [e for e in usable if e["pair"] == pair]
        hrs = []
        for e in evs:
            rt_ev = KB_RT[pair] - KB_SPREAD[pair] + e["entry_ratio"] * KB_SPREAD[pair]
            e["rt_event"] = round(rt_ev, 3)
            e["headroom"] = round(e["entry_scale24"] / rt_ev, 2)
            hrs.append(e["headroom"])
        med = float(np.median(hrs)) if hrs else None
        per_pair[pair] = {
            "n_events": len(evs),
            "median_headroom": round(med, 2) if med is not None else None,
            "pass": bool(med is not None and med >= HEADROOM_MIN),
        }
        pooled_hr += hrs
    pooled_med = float(np.median(pooled_hr)) if pooled_hr else None
    surviving = [p for p in PAIRS if per_pair[p]["pass"]]
    return {
        "per_pair": per_pair,
        "pooled_median_headroom": round(pooled_med, 2) if pooled_med is not None else None,
        "surviving_pairs": surviving,
        "pass": bool(pooled_med is not None and pooled_med >= HEADROOM_MIN
                     and len(surviving) >= MIN_SURVIVING_PAIRS),
        "n_usable_events": len(usable),
        "n_dropped_no_normalization": sum(1 for e in events if not e.get("normalized")),
        "counterfactual_onset_rt": {
            p: round(float(np.median([
                KB_RT[p] - KB_SPREAD[p] + e["onset_ratio"] * KB_SPREAD[p]
                for e in usable if e["pair"] == p])), 2)
            for p in PAIRS if any(e["pair"] == p for e in usable)
        },
    }


# ---------------------------------------------------------------- measurement

def build_return_grid(df: pd.DataFrame) -> dict:
    """pair×slot ごとの (date -> fwd 24h short-pair return) grid。
    ★このヘルパーは stage=explore/oos でのみ呼ばれる (headroom は非接触)。"""
    grid: dict = {}
    for pair in PAIRS:
        g = df[(df["pair"] == pair) & df["valid"]]
        for slot, gs in g.groupby("ny_slot"):
            gs = gs.sort_values("ts_utc").reset_index(drop=True)
            dates = pd.to_datetime(gs["ny_date"]).dt.date.tolist()
            mids = gs["mid_med"].astype(float).tolist()
            scales = gs["scale24_pips"].astype(float).tolist()
            m = {}
            for idx in range(len(gs) - 1):
                gap = (dates[idx + 1] - dates[idx]).days
                if gap > MAX_EXIT_CAL_DAYS:
                    continue
                ret_pips = -(mids[idx + 1] - mids[idx]) * PIP[pair]  # short-pair (risk-off +)
                sc = scales[idx]
                if not (np.isfinite(sc) and sc > 0):
                    continue
                m[dates[idx]] = {"ret_pips": ret_pips, "ret_std": ret_pips / sc,
                                 "scale": sc}
            grid[(pair, int(slot))] = {"map": m, "dates": dates}
    return grid


def measure(events: list[dict], grid: dict, trading_days: list, seed: int = SEED,
            n_boot: int = N_BOOT, shift_unit: str = "day",
            one_sided_sign: int | None = None) -> dict:
    """primary: pooled mean standardized fwd 24h return (short-pair convention)。
    null = 全ペア同時・営業日単位 circular shift (イベント時刻をシフト、grid 固定)。"""
    usable = []
    for e in events:
        if not e.get("normalized"):
            continue
        key = (e["pair"], e["entry_slot"])
        d = dt.date.fromisoformat(e["entry_date"])
        cell = grid.get(key, {}).get("map", {}).get(d)
        if cell is None:
            continue
        e = dict(e)
        e.update(cell)
        usable.append(e)
    n = len(usable)
    if n == 0:
        return {"n": 0, "error": "no measurable events"}
    obs = float(np.mean([e["ret_std"] for e in usable]))

    day_index = {d: i for i, d in enumerate(trading_days)}
    nd = len(trading_days)
    rng = np.random.default_rng(seed)
    null = []
    attempts = 0
    while len(null) < n_boot and attempts < n_boot * 3:
        attempts += 1
        if shift_unit == "day":
            k = int(rng.integers(20, nd - 20))
        else:  # slot-level shift (knife-edge variant): day shift + slot rotation
            k = int(rng.integers(20, nd - 20))
        vals = []
        for e in usable:
            d0 = dt.date.fromisoformat(e["entry_date"])
            i0 = day_index.get(d0)
            if i0 is None:
                continue
            slot = e["entry_slot"]
            if shift_unit == "slot":
                slots = [18, 21, 0, 3, 6, 9, 12, 15]
                slot = slots[(slots.index(slot) + int(rng.integers(0, 8))) % 8]
            d1 = trading_days[(i0 + k) % nd]
            cell = grid.get((e["pair"], slot), {}).get("map", {}).get(d1)
            if cell is not None:
                vals.append(cell["ret_std"])
        if len(vals) < 0.8 * n:
            continue
        null.append(float(np.mean(vals)))
    null = np.array(null)
    if one_sided_sign is None:
        p = (1 + int(np.count_nonzero(np.abs(null) >= abs(obs)))) / (len(null) + 1)
    else:
        s = one_sided_sign
        p = (1 + int(np.count_nonzero(null * s >= obs * s))) / (len(null) + 1)
    return {"n": n, "mean_ret_std": round(obs, 5),
            "mean_ret_pips": round(float(np.mean([e["ret_pips"] for e in usable])), 3),
            "p": float(p), "n_null": int(len(null)), "events": usable}


def gates(usable: list[dict], obs_sign: int, explore: bool = True,
          years: list[int] | None = None) -> dict:
    rets = np.array([e["ret_std"] for e in usable])
    yrs = np.array([e["year"] for e in usable])
    pairs_arr = np.array([e["pair"] for e in usable])
    pooled = rets.mean()
    out: dict = {}

    # (ii) magnitude coherence: peak_ratio tercile 全て pooled と同符号
    peak = np.array([e["peak_ratio"] for e in usable])
    ter = np.quantile(peak, [1 / 3, 2 / 3])
    bins = np.digitize(peak, ter)
    ter_means = [float(rets[bins == k].mean()) if (bins == k).any() else 0.0
                 for k in range(3)]
    out["gate_ii_terciles"] = {
        "means": [round(m, 4) for m in ter_means],
        "pass": bool(all(np.sign(m) == obs_sign for m in ter_means if m != 0.0)),
    }
    # (iii) 集中: LOYO 符号不変 + 年 share <=50% + top-event LOO + SNB 除外
    uyears = sorted(set(yrs.tolist()))
    loyo_signs = {}
    for y in uyears:
        m = rets[yrs != y].mean() if (yrs != y).any() else 0.0
        loyo_signs[int(y)] = float(m)
    year_sums = {int(y): float(np.abs(rets[yrs == y]).sum()) for y in uyears}
    tot = sum(year_sums.values()) or 1.0
    max_year_share = max(year_sums.values()) / tot
    top_i = int(np.argmax(np.abs(rets)))
    loo_top = float(np.delete(rets, top_i).mean()) if len(rets) > 1 else 0.0
    snb_mask = np.array([not e["onset_ts"].startswith("2015-01") for e in usable])
    snb_mean = float(rets[snb_mask].mean()) if snb_mask.any() else 0.0
    out["gate_iii_concentration"] = {
        "loyo_means": {k: round(v, 4) for k, v in loyo_signs.items()},
        "max_year_abs_share": round(max_year_share, 3),
        "loo_top_event_mean": round(loo_top, 4),
        "snb_excl_mean": round(snb_mean, 4),
        "pass": bool(
            all(np.sign(v) == obs_sign for v in loyo_signs.values())
            and max_year_share <= 0.5
            and np.sign(loo_top) == obs_sign
            and np.sign(snb_mean) == obs_sign),
    }
    # (iv) cross-pair coherence: leave-one-pair-out 符号不変 + >=2/3 ペア同符号
    lopo = {}
    for p in sorted(set(pairs_arr.tolist())):
        m = rets[pairs_arr != p].mean() if (pairs_arr != p).any() else 0.0
        lopo[p] = float(m)
    pair_means = {p: float(rets[pairs_arr == p].mean())
                  for p in sorted(set(pairs_arr.tolist()))}
    n_same = sum(1 for v in pair_means.values() if np.sign(v) == obs_sign)
    out["gate_iv_pairs"] = {
        "leave_one_pair_out": {k: round(v, 4) for k, v in lopo.items()},
        "pair_means": {k: round(v, 4) for k, v in pair_means.items()},
        "pass": bool(all(np.sign(v) == obs_sign for v in lopo.values())
                     and n_same >= 2),
    }
    # (v) 実現 headroom: median |realized move| >= 10 x median RT_event
    realized = np.array([abs(e["ret_pips"]) for e in usable])
    rts = np.array([e["rt_event"] for e in usable])
    out["gate_v_realized_headroom"] = {
        "median_abs_move_pips": round(float(np.median(realized)), 2),
        "median_rt_event": round(float(np.median(rts)), 2),
        "ratio": round(float(np.median(realized) / np.median(rts)), 1),
        "pass": bool(np.median(realized) >= HEADROOM_MIN * np.median(rts)),
    }
    # (vi) 年末薄商い集中
    def _ye(e):
        d = dt.date.fromisoformat(e["entry_date"])
        return (d.month == 12 and d.day >= 15) or (d.month == 1 and d.day <= 5)
    ye_share = float(np.mean([_ye(e) for e in usable]))
    out["gate_vi_yearend"] = {"share": round(ye_share, 3),
                              "pass": bool(ye_share <= YEAR_END_SHARE_MAX)}
    return out


# ------------------------------------------------------------------- driver

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True,
                        choices=["qa", "headroom", "explore", "oos"])
    parser.add_argument("--unlock-oos", action="store_true")
    parser.add_argument("--out", default=None)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--shift-unit", default="day", choices=["day", "slot"])
    args = parser.parse_args()

    if args.stage == "oos" and not args.unlock_oos:
        print("OOS is locked: explore PASS + --unlock-oos required", file=sys.stderr)
        return 2

    cutoff = EXPLORE_PANEL_CUTOFF if args.stage in ("qa", "headroom", "explore") else None
    df = qa_panel(load_panel(cutoff=cutoff))
    cov = coverage_report(df)
    result: dict = {"stage": args.stage, "coverage": cov,
                    "frozen": {
                        "onset_ratio": ONSET_RATIO, "onset_elev_pips": ONSET_ELEV_PIPS,
                        "persist_ratio": PERSIST_RATIO, "norm_ratio": NORM_RATIO,
                        "move_small_mult": MOVE_SMALL_MULT,
                        "entry_max_wait": ENTRY_MAX_WAIT,
                        "headroom_min": HEADROOM_MIN, "min_events": MIN_EVENTS,
                        "seed": args.seed, "n_boot": N_BOOT, "alpha": ALPHA, "m": 1,
                        "kb_rt": KB_RT, "kb_spread": KB_SPREAD,
                        "horizon": "24h (same NY slot, next trading day)",
                        "convention": "short-pair pooled (risk-off +)",
                    }}
    if args.stage == "qa":
        pass
    else:
        if not cov["pass"]:
            result["verdict"] = "DATA-BLOCKED (coverage assert fail — 事後緩和禁止)"
            print(json.dumps(result, ensure_ascii=False, indent=1, default=str))
            return 0
        df = build_baselines(df)
        if args.stage in ("headroom", "explore"):
            w0, w1 = EXPLORE_START, EXPLORE_END
        else:
            w0, w1 = OOS_START, OOS_END
        events = detect_events(df, w0, w1)
        # coverage skip 年のイベントは除外 (正直 skip)
        events = [e for e in events
                  if e["year"] not in cov["skipped_years"].get(e["pair"], [])
                  and e["pair"] in cov["explore_pass_pairs"]]
        hr = headroom_gate(events)
        result["headroom_gate"] = hr
        result["n_events_detected"] = len(events)
        if args.stage == "headroom":
            if hr["n_usable_events"] < MIN_EVENTS:
                result["verdict"] = (
                    f"POWER-BLOCKED (usable events {hr['n_usable_events']} < {MIN_EVENTS})")
            elif not hr["pass"]:
                result["verdict"] = "FRICTION-KILL (headroom < 10x, fwd return 未接触)"
            else:
                result["verdict"] = "HEADROOM-PASS (凍結 doc → explore へ)"
        else:
            if hr["n_usable_events"] < MIN_EVENTS or not hr["pass"]:
                result["verdict"] = "BLOCKED at headroom stage — explore 実行不可"
                print(json.dumps(result, ensure_ascii=False, indent=1, default=str))
                return 0
            events = [e for e in events
                      if e.get("normalized") and e.get("entry_scale24")
                      and e["pair"] in hr["surviving_pairs"]]
            grid = build_return_grid(df)
            tdays = sorted({d for (p, s), v in grid.items() for d in v["map"]})
            one_sided = None  # explore は両側。OOS は explore 符号で片側 (実行時指定)
            meas = measure(events, grid, tdays, seed=args.seed,
                           shift_unit=args.shift_unit, one_sided_sign=one_sided)
            usable = meas.pop("events", [])
            result["primary"] = meas
            if meas["n"] < MIN_EVENTS:
                result["verdict"] = f"POWER-BLOCKED (measurable {meas['n']} < {MIN_EVENTS})"
            else:
                sign = 1 if meas["mean_ret_std"] >= 0 else -1
                g = gates(usable, sign)
                result["gates"] = g
                gate_i = meas["p"] < ALPHA
                all_pass = gate_i and all(v["pass"] for v in g.values())
                result["gate_i_p"] = {"p": meas["p"], "pass": bool(gate_i)}
                result["verdict"] = "PASS" if all_pass else "FAIL"
                result["knife_edge_band"] = bool(0.025 <= meas["p"] <= 0.10)
            result["events_sample"] = usable[:5]
            result["n_usable"] = len(usable)
    js = json.dumps(result, ensure_ascii=False, indent=1, default=str)
    print(js)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(js)
    return 0


if __name__ == "__main__":
    sys.exit(main())
