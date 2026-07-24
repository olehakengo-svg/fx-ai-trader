#!/usr/bin/env python3
"""MoF 円買い介入 forward explore — pre-reg DRAFT §4 実行スクリプト (2026-07-24).

Pre-reg doc:
  knowledge-base/wiki/decisions/mof-intervention-forward-prereg-DRAFT-2026-07-24.md

Scope (doc §4, LOCK 前 explore — OOS 非接触):
  1. 既知 7 日の現代円買い介入 (2022-09-22, 2022-10-21, 2022-10-24,
     2024-04-29, 2024-05-01, 2024-07-11, 2024-07-12) について、
     翌東京営業日 00:00 UTC anchor の forward net / SELL-MFE / SELL-MAE を
     h ∈ {1d, 2d, 5d, 10d} (東京営業日) で計測 (doc §2.2 estimand)。
  2. episode-block permutation null (エピソード = gap>=30d クラスタ = 3 blocks、
     matched placebo: 同一曜日 + trailing-20d realized vol quintile 一致、
     event±10d 除外)。有効 N≈3 のため記述統計のみ (doc §4)。
  3. 識別 rule 校正: candidate(d)=1 <=> close/open-1 <= -Y% AND
     range(d) >= X * trailing-20d median range。2022/2024 の 7 日 + 周辺
     placebo のみで校正し (X, Y) を凍結 (doc §2.2)。
  4. 凍結 rule の 2026 窓 (2026-04-28..05-27) への一回適用 → candidate list S
     と M (窓内営業日数) を確定。--skip-2026 で開発中はこのステップを飛ばし、
     2026 窓への接触を最終 1 回に限定する (doc §7 リーク経路封鎖 (i))。

事前宣言 (実行前に固定 — 結果を見た後の変更禁止):
  - 校正 grid: Y ∈ {0.25, 0.50, ..., 2.00} [%] (step 0.25),
               X ∈ {1.5, 2.0, ..., 4.0} (step 0.5)。
  - 機械的選択基準 (裁量ゼロ): feasible = 7 日中 hits >= 6。
    feasible 内で lexicographic に (1) FP 件数最小 (2) hits 最大
    (3) Y 最小 (4) X 最小 (= 最緩値)。
  - FP 母集団 (primary): 2022-01-01..2024-12-31 の営業日から 7 event days を
    除いた全日。感度: event±10 暦日も除外した版を併記。
  - permutation: N_PERM=10000, seed=20260724。
  - §8.3 の ±20% 摂動チェックは校正データ (2022/2024) のみで実施。
    2026 窓への摂動 rule 適用は verdict 時 (doc §8) — ここでは行わない。

Swap (doc §2.2): h5/h10 の short USDJPY キャリーは政策金利差の推定値で
net-after-carry を併記 (判定は gross 符号)。OANDA financing 実測値の記録は
LOCK 手順 (doc §9 step 3) — 本スクリプトは推定値と明記する。

Outputs:
  - bt-results/mof_intervention_explore-2026-07-24.json
  - (report .md は別途手書き — reports/mof_intervention_explore-2026-07-24.md)

Usage:
  python3 tools/mof_intervention_explore.py [--skip-2026] [--out PATH]
"""

import argparse
import bisect
import datetime as dt
import json
import math
import sys

import numpy as np
import pandas as pd

REPO = "/Users/jg-n-012/test/fx-ai-trader"
PARQUET = f"{REPO}/data/cache/massive/USD_JPY_15m_2014_2026.parquet"
OUT_JSON = f"{REPO}/bt-results/mof_intervention_explore-2026-07-24.json"

PIP = 0.01  # USDJPY pip (doc §2.2)

# 現代円買い 7 日 (doc §4 / data/external/mof_interventions.csv)
EVENT_DAYS = [
    dt.date(2022, 9, 22),
    dt.date(2022, 10, 21),
    dt.date(2022, 10, 24),
    dt.date(2024, 4, 29),
    dt.date(2024, 5, 1),
    dt.date(2024, 7, 11),
    dt.date(2024, 7, 12),
]
EPISODE_GAP_DAYS = 30      # doc §4: gap>=30d クラスタ
HORIZONS = [1, 2, 5, 10]   # 東京営業日 (doc §2.2)

# 校正 / placebo 期間 (現代レジーム、2026 窓を含まない)
CAL_START = dt.date(2022, 1, 1)
CAL_END = dt.date(2024, 12, 31)
PLACEBO_EXCLUDE_CAL_DAYS = 10  # event±10 暦日除外 (doc §4)
VOL_LOOKBACK = 20              # trailing-20d realized vol (doc §4)
N_QUINTILES = 5
N_PERM = 10000
SEED = 20260724

# 識別 rule 校正 grid (事前宣言 — docstring 参照)
Y_GRID_PCT = [0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00]
X_GRID = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
RULE_MIN_HITS = 6
RANGE_MED_LOOKBACK = 20  # trailing-20d median range (doc §2.2)

# 2026 窓 (doc §5.0 / P-2)
WIN26_START = dt.date(2026, 4, 28)
WIN26_END = dt.date(2026, 5, 27)
S_MAX = 5  # |S| <= 5 事前上限 (doc §5.2)

# short USDJPY キャリー推定 (年率金利差、推定値 — LOCK 時に OANDA financing
# 実測へ差し替え記録。EFFR: FRED FEDFUNDS、JPY: BoJ 政策金利)
CARRY_RATE_DIFF = {
    2022: 0.0318,  # EFFR ~3.08% (2022-09-21 利上げ後) - BoJ -0.10%
    2024: 0.0528,  # EFFR 5.33% - BoJ ~0.05% (0-0.1% レンジ)
}

E_A_ALPHA = 0.10  # doc §5.2 PASS: 超幾何 p <= 0.10


# ---------------------------------------------------------------- data layer

def load_bars(path: str) -> pd.DataFrame:
    """Load 15m mid bars; return tz-aware UTC-indexed OHLC frame."""
    df = pd.read_parquet(path)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df.sort_index()
    need = {"Open", "High", "Low", "Close"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"parquet missing columns: {missing}")
    return df[["Open", "High", "Low", "Close"]]


def build_daily(df15: pd.DataFrame) -> pd.DataFrame:
    """UTC-day OHLC bars (doc §2.2: 00:00 UTC = 09:00 JST 区切り = 東京営業日).

    営業日判定: その UTC 日の最初のバーが 06:00 UTC より前に存在すること
    (日曜 21/22 UTC 開場のみの日・元日等の遅開き日を除外)。
    """
    g = df15.groupby(df15.index.date)
    daily = pd.DataFrame({
        "open": g["Open"].first(),
        "high": g["High"].max(),
        "low": g["Low"].min(),
        "close": g["Close"].last(),
        "first_bar": g.apply(lambda x: x.index.min()),
        "n_bars": g.size(),
    })
    daily.index = pd.Index([d for d in daily.index], name="date")
    first_hr = pd.Series([t.hour for t in daily["first_bar"]], index=daily.index)
    daily = daily[first_hr < 6]
    daily["range"] = daily["high"] - daily["low"]
    daily["co_ret_pct"] = (daily["close"] / daily["open"] - 1.0) * 100.0
    # trailing-20d median range (d-1 まで、当日を含まない)
    daily["med20_range"] = daily["range"].shift(1).rolling(RANGE_MED_LOOKBACK).median()
    daily["range_ratio"] = daily["range"] / daily["med20_range"]
    # trailing-20d realized vol (log close-to-close, d-1 まで)
    logret = np.log(daily["close"] / daily["close"].shift(1))
    daily["vol20"] = logret.shift(1).rolling(VOL_LOOKBACK).std()
    return daily


class BizCalendar:
    """営業日リスト上の add/next 演算。"""

    def __init__(self, biz_dates):
        self.dates = sorted(biz_dates)

    def next_after(self, d: dt.date) -> dt.date:
        """d より後の最初の営業日 (roll forward、doc §2.2 anchor)。"""
        i = bisect.bisect_right(self.dates, d)
        if i >= len(self.dates):
            raise ValueError(f"no business day after {d}")
        return self.dates[i]

    def add(self, d: dt.date, n: int) -> dt.date:
        """営業日 d から n 営業日先。d は営業日であること。"""
        i = bisect.bisect_left(self.dates, d)
        if i >= len(self.dates) or self.dates[i] != d:
            raise ValueError(f"{d} is not a business day")
        j = i + n
        if j >= len(self.dates):
            raise ValueError(f"not enough business days after {d} (+{n})")
        return self.dates[j]


def price_at_boundary(df15: pd.DataFrame, day: dt.date):
    """営業日 day の 00:00 UTC 以降最初の 15m バーの (timestamp, Open)。"""
    t = pd.Timestamp(dt.datetime(day.year, day.month, day.day), tz="UTC")
    idx = df15.index.searchsorted(t)
    if idx >= len(df15.index):
        raise ValueError(f"no bar at/after {t}")
    ts = df15.index[idx]
    if (ts - t) > pd.Timedelta(hours=6):
        raise ValueError(f"first bar after {t} is {ts} (>6h gap; not a session open)")
    return ts, float(df15["Open"].iloc[idx])


# ------------------------------------------------------------ forward metric

def measure_forward(df15: pd.DataFrame, cal: BizCalendar, event_day: dt.date,
                    with_carry: bool = True) -> dict:
    """doc §2.2 estimand: 翌営業日 00:00 UTC anchor の net/MFE/MAE (SELL 方向)。

    with_carry=False は placebo 日用 (permutation は net_pips のみ使用し、
    キャリー推定は event 年しか定義していないため)。
    """
    anchor_day = cal.next_after(event_day)
    t0, entry = price_at_boundary(df15, anchor_day)
    out = {
        "event_day": event_day.isoformat(),
        "anchor_day": anchor_day.isoformat(),
        "anchor_ts": t0.isoformat(),
        "entry_mid": entry,
        "horizons": {},
    }
    for h in HORIZONS:
        end_day = cal.add(anchor_day, h)
        t_end, exit_mid = price_at_boundary(df15, end_day)
        seg = df15[(df15.index >= t0) & (df15.index < t_end)]
        if seg.empty:
            raise ValueError(f"empty forward segment {t0}..{t_end}")
        net_pips = (exit_mid - entry) / PIP          # 負 = SELL 有利 (doc §2.2)
        mfe_pips = (entry - float(seg["Low"].min())) / PIP   # SELL MFE (正=有利)
        mae_pips = (float(seg["High"].max()) - entry) / PIP  # SELL MAE (正=不利)
        rec = {
            "end_day": end_day.isoformat(),
            "net_pips": round(net_pips, 1),
            "mfe_pips": round(mfe_pips, 1),
            "mae_pips": round(mae_pips, 1),
        }
        if h in (5, 10) and with_carry:
            cal_days = (t_end - t0).total_seconds() / 86400.0
            diff = CARRY_RATE_DIFF[event_day.year]
            carry_cost_pips = entry * diff * (cal_days / 365.0) / PIP
            rec["carry_cost_pips_est"] = round(carry_cost_pips, 1)
            # short の carry 費用は SELL 有利方向 (負) の net を悪化 (正方向へ)
            rec["net_after_carry_pips_est"] = round(net_pips + carry_cost_pips, 1)
        out["horizons"][f"h{h}"] = rec
    return out


def cluster_episodes(days):
    """gap>=EPISODE_GAP_DAYS 暦日で新エピソード (doc §4)。"""
    eps = []
    for d in sorted(days):
        if eps and (d - eps[-1][-1]).days < EPISODE_GAP_DAYS:
            eps[-1].append(d)
        else:
            eps.append([d])
    return eps


# --------------------------------------------------------- permutation null

def build_placebo_pools(daily: pd.DataFrame, episodes) -> dict:
    """episode 初日にマッチした placebo 営業日プール (doc §4)。

    match: 同一曜日 + trailing-20d realized vol quintile 一致。
    pool: CAL_START..CAL_END 営業日、全 event±10 暦日除外、vol 有効。
    quintile 境界: 校正期間の全営業日 (vol 有効) から決定論的に計算。
    """
    cal_days = [d for d in daily.index if CAL_START <= d <= CAL_END]
    vol = daily.loc[cal_days, "vol20"].dropna()
    edges = np.quantile(vol.values, [0.2, 0.4, 0.6, 0.8])

    def quintile(v: float) -> int:
        return int(np.searchsorted(edges, v, side="right"))

    excluded = set()
    for e in EVENT_DAYS:
        for k in range(-PLACEBO_EXCLUDE_CAL_DAYS, PLACEBO_EXCLUDE_CAL_DAYS + 1):
            excluded.add(e + dt.timedelta(days=k))

    pools = {}
    for ep in episodes:
        e0 = ep[0]
        v0 = daily.loc[e0, "vol20"]
        if not np.isfinite(v0):
            raise ValueError(f"vol20 not available for episode first day {e0}")
        q0 = quintile(float(v0))
        pool = [
            d for d in vol.index
            if d not in excluded
            and d.weekday() == e0.weekday()
            and quintile(float(vol.loc[d])) == q0
        ]
        if len(pool) < 10:
            raise ValueError(f"placebo pool too small for episode {e0}: {len(pool)}")
        pools[e0.isoformat()] = {"quintile": q0, "weekday": e0.weekday(), "days": pool}
    return pools


def permutation_null(df15, cal, daily, episodes, event_fwd) -> dict:
    """episode-block permutation (3 blocks, 各 episode = 1 draw、doc §4)。

    observed stat = median over episodes of (episode 内 per-day net_h の平均)。
    null stat     = median over episodes of (matched placebo 1 日の net_h)。
    記述統計のみ — Bonferroni 級主張不可 (doc §4 事前宣言)。
    """
    pools = build_placebo_pools(daily, episodes)
    rng = np.random.default_rng(SEED)

    # placebo 日の forward net を事前計算 (プール和集合)
    all_pool_days = sorted({d for p in pools.values() for d in p["days"]})
    placebo_net = {}
    skipped = []
    for d in all_pool_days:
        try:
            fwd = measure_forward(df15, cal, d, with_carry=False)
        except ValueError as exc:
            skipped.append({"day": d.isoformat(), "reason": str(exc)})
            continue
        placebo_net[d] = {h: fwd["horizons"][f"h{h}"]["net_pips"] for h in HORIZONS}

    by_day = {f["event_day"]: f for f in event_fwd}
    results = {}
    for h in HORIZONS:
        ep_means = []
        for ep in episodes:
            vals = [by_day[d.isoformat()]["horizons"][f"h{h}"]["net_pips"] for d in ep]
            ep_means.append(float(np.mean(vals)))
        obs = float(np.median(ep_means))

        pool_arrays = []
        for ep in episodes:
            days = [d for d in pools[ep[0].isoformat()]["days"] if d in placebo_net]
            pool_arrays.append(np.array([placebo_net[d][h] for d in days]))
        draws = np.empty((N_PERM, len(episodes)))
        for j, arr in enumerate(pool_arrays):
            draws[:, j] = arr[rng.integers(0, len(arr), size=N_PERM)]
        null_stats = np.median(draws, axis=1)

        if obs < 0:
            p_one = (1 + int(np.sum(null_stats <= obs))) / (N_PERM + 1)
            side = "le (SELL-favorable)"
        else:
            p_one = (1 + int(np.sum(null_stats >= obs))) / (N_PERM + 1)
            side = "ge"
        p_two = (1 + int(np.sum(np.abs(null_stats) >= abs(obs)))) / (N_PERM + 1)
        results[f"h{h}"] = {
            "obs_median_of_episode_means_pips": round(obs, 1),
            "episode_means_pips": [round(v, 1) for v in ep_means],
            "null_median_pips": round(float(np.median(null_stats)), 1),
            "null_p05_pips": round(float(np.quantile(null_stats, 0.05)), 1),
            "null_p95_pips": round(float(np.quantile(null_stats, 0.95)), 1),
            "p_one_sided": round(p_one, 4),
            "one_sided_direction": side,
            "p_two_sided": round(p_two, 4),
        }
    return {
        "n_perm": N_PERM,
        "seed": SEED,
        "pools": {
            k: {"quintile": v["quintile"], "weekday": v["weekday"],
                "n_days": len([d for d in v["days"] if d in placebo_net])}
            for k, v in pools.items()
        },
        "skipped_placebo_days": skipped,
        "by_horizon": results,
        "caveat": "有効 N≈3 エピソード — 記述統計のみ、検定主張不可 (doc §4)",
    }


# ------------------------------------------------------- identification rule

def rule_hits(daily: pd.DataFrame, days, x: float, y_pct: float):
    """candidate(d)=1 <=> co_ret_pct <= -y_pct AND range_ratio >= x."""
    hits = []
    for d in days:
        row = daily.loc[d]
        if not np.isfinite(row["range_ratio"]):
            continue
        if row["co_ret_pct"] <= -y_pct and row["range_ratio"] >= x:
            hits.append(d)
    return hits


def calibrate_rule(daily: pd.DataFrame) -> dict:
    """(X, Y) を事前宣言 grid + 機械的基準で校正 (docstring 参照)。"""
    cal_days = [d for d in daily.index
                if CAL_START <= d <= CAL_END and np.isfinite(daily.loc[d, "range_ratio"])]
    event_set = set(EVENT_DAYS)
    non_event = [d for d in cal_days if d not in event_set]
    excluded10 = set()
    for e in EVENT_DAYS:
        for k in range(-PLACEBO_EXCLUDE_CAL_DAYS, PLACEBO_EXCLUDE_CAL_DAYS + 1):
            excluded10.add(e + dt.timedelta(days=k))
    non_event_x10 = [d for d in non_event if d not in excluded10]

    grid = []
    for y in Y_GRID_PCT:
        for x in X_GRID:
            ev_hits = rule_hits(daily, EVENT_DAYS, x, y)
            fp = rule_hits(daily, non_event, x, y)
            fp_x10 = rule_hits(daily, non_event_x10, x, y)
            grid.append({
                "x": x, "y_pct": y,
                "event_hits": len(ev_hits),
                "event_hit_days": [d.isoformat() for d in ev_hits],
                "fp_count": len(fp),
                "fp_rate": round(len(fp) / len(non_event), 4),
                "fp_days": [d.isoformat() for d in fp],
                "fp_count_excl10": len(fp_x10),
                "fp_rate_excl10": round(len(fp_x10) / len(non_event_x10), 4),
            })

    feasible = [g for g in grid if g["event_hits"] >= RULE_MIN_HITS]
    if not feasible:
        raise ValueError("no (X, Y) in grid captures >= 6/7 event days")
    # lexicographic: min FP -> max hits -> min Y -> min X (事前宣言)
    feasible.sort(key=lambda g: (g["fp_count"], -g["event_hits"], g["y_pct"], g["x"]))
    chosen = feasible[0]

    # §8.3 摂動チェック (校正データのみ — 2026 窓には適用しない)
    perturb = []
    for fx in (0.8, 1.0, 1.2):
        for fy in (0.8, 1.0, 1.2):
            if fx == 1.0 and fy == 1.0:
                continue
            px, py = chosen["x"] * fx, chosen["y_pct"] * fy
            ev = rule_hits(daily, EVENT_DAYS, px, py)
            fp = rule_hits(daily, non_event, px, py)
            perturb.append({
                "x": round(px, 2), "y_pct": round(py, 3),
                "event_hits": len(ev), "fp_count": len(fp),
            })

    event_table = []
    for d in EVENT_DAYS:
        row = daily.loc[d]
        event_table.append({
            "date": d.isoformat(),
            "co_ret_pct": round(float(row["co_ret_pct"]), 3),
            "range_pips": round(float(row["range"]) / PIP, 1),
            "med20_range_pips": round(float(row["med20_range"]) / PIP, 1),
            "range_ratio": round(float(row["range_ratio"]), 2),
        })

    return {
        "grid_declared": {"y_pct": Y_GRID_PCT, "x": X_GRID,
                          "selection": "hits>=6 -> min FP -> max hits -> min Y -> min X"},
        "n_calibration_days": len(cal_days),
        "n_non_event_days": len(non_event),
        "event_day_stats": event_table,
        "chosen": chosen,
        "top5_feasible": feasible[:5],
        "perturbation_pm20pct_calibration_only": perturb,
    }


def apply_rule_2026(daily: pd.DataFrame, x: float, y_pct: float) -> dict:
    """凍結 rule の 2026 窓への一回適用 (doc §2.2 / §7 封鎖 (i))。"""
    win_days = [d for d in daily.index if WIN26_START <= d <= WIN26_END]
    if not win_days:
        raise ValueError("no 2026 window business days in data")
    bad = [d for d in win_days if not np.isfinite(daily.loc[d, "range_ratio"])]
    if bad:
        raise ValueError(f"range_ratio unavailable for window days: {bad}")
    hits = rule_hits(daily, win_days, x, y_pct)
    detail = []
    for d in hits:
        row = daily.loc[d]
        detail.append({
            "date": d.isoformat(),
            "co_ret_pct": round(float(row["co_ret_pct"]), 3),
            "range_ratio": round(float(row["range_ratio"]), 2),
        })
    return {
        "window": [WIN26_START.isoformat(), WIN26_END.isoformat()],
        "M_business_days": len(win_days),
        "business_days": [d.isoformat() for d in win_days],
        "candidate_list_S": [d.isoformat() for d in hits],
        "S_size": len(hits),
        "S_max_constraint": S_MAX,
        "S_within_constraint": len(hits) <= S_MAX,
        "candidate_detail": detail,
    }


# ----------------------------------------------------------- hypergeometric

def hypergeom_sf(overlap: int, M: int, K: int, k: int) -> float:
    """P(X >= overlap), X ~ Hypergeom(M, K, k)。"""
    denom = math.comb(M, k)
    num = sum(math.comb(K, j) * math.comb(M - K, k - j)
              for j in range(overlap, min(K, k) + 1))
    return num / denom


def hypergeom_thresholds(M: int, K: int) -> list:
    """k=1..5 について p<=0.10 に必要な最小 overlap (doc §5.2)。"""
    rows = []
    for k in range(1, 6):
        thr = None
        for o in range(1, min(K, k) + 1):
            p = hypergeom_sf(o, M, K, k)
            if p <= E_A_ALPHA:
                thr = {"min_overlap": o, "p_at_threshold": round(p, 4)}
                break
        rows.append({
            "k": k,
            "p_overlap_ge_1": round(hypergeom_sf(1, M, K, k), 4) if K >= 1 else None,
            "threshold": thr if thr else "not attainable",
        })
    return rows


# -------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip-2026", action="store_true",
                    help="2026 窓への rule 適用を飛ばす (開発用 — 接触回数を最終 1 回に限定)")
    ap.add_argument("--out", default=OUT_JSON)
    args = ap.parse_args(argv)

    df15 = load_bars(PARQUET)
    daily = build_daily(df15)
    cal = BizCalendar(list(daily.index))

    for d in EVENT_DAYS:
        if d not in daily.index:
            raise ValueError(f"event day {d} missing from daily bars")

    episodes = cluster_episodes(EVENT_DAYS)
    if len(episodes) != 3:
        raise ValueError(f"expected 3 episodes, got {len(episodes)}: {episodes}")

    # 1) forward 計測 (7 日)
    event_fwd = [measure_forward(df15, cal, d) for d in EVENT_DAYS]

    # per-horizon 記述統計 (per-day / episode-初日変種)
    desc = {}
    first_days = [ep[0] for ep in episodes]
    for h in HORIZONS:
        nets = [f["horizons"][f"h{h}"]["net_pips"] for f in event_fwd]
        mfes = [f["horizons"][f"h{h}"]["mfe_pips"] for f in event_fwd]
        maes = [f["horizons"][f"h{h}"]["mae_pips"] for f in event_fwd]
        fd_nets = [f["horizons"][f"h{h}"]["net_pips"] for f in event_fwd
                   if f["event_day"] in {d.isoformat() for d in first_days}]
        desc[f"h{h}"] = {
            "net_median_pips": round(float(np.median(nets)), 1),
            "net_p25_pips": round(float(np.quantile(nets, 0.25)), 1),
            "net_p75_pips": round(float(np.quantile(nets, 0.75)), 1),
            "net_sign_consistency": f"{sum(1 for v in nets if v < 0)}/7 negative",
            "n_negative": sum(1 for v in nets if v < 0),
            "mfe_median_pips": round(float(np.median(mfes)), 1),
            "mae_median_pips": round(float(np.median(maes)), 1),
            "episode_first_day_nets_pips": [round(v, 1) for v in fd_nets],
        }

    # h* 選択 (doc §5.3): 符号最一貫 (多数派符号の日数最大)、tie-break |median| 最大
    def h_key(h):
        nets = [f["horizons"][f"h{h}"]["net_pips"] for f in event_fwd]
        majority = max(sum(1 for v in nets if v < 0), sum(1 for v in nets if v > 0))
        return (majority, abs(float(np.median(nets))))
    h_star = max(HORIZONS, key=h_key)
    h_star_nets = [f["horizons"][f"h{h_star}"]["net_pips"] for f in event_fwd]
    h_star_median = float(np.median(h_star_nets))
    predicted_sign = "negative (SELL-favorable)" if h_star_median < 0 else "positive (retracement)"

    # 2) permutation null
    perm = permutation_null(df15, cal, daily, episodes, event_fwd)

    # 3) rule 校正
    calib = calibrate_rule(daily)
    x_frozen = calib["chosen"]["x"]
    y_frozen = calib["chosen"]["y_pct"]

    out = {
        "meta": {
            "script": "tools/mof_intervention_explore.py",
            "run_date": "2026-07-24",
            "prereg_doc": "knowledge-base/wiki/decisions/mof-intervention-forward-prereg-DRAFT-2026-07-24.md",
            "data": PARQUET.replace(REPO + "/", ""),
            "data_span": [str(df15.index.min()), str(df15.index.max())],
            "pip": PIP,
            "carry_note": "swap は政策金利差からの推定値。OANDA financing 実測の記録は LOCK 手順 (doc §9 step 3)",
        },
        "episodes": [[d.isoformat() for d in ep] for ep in episodes],
        "per_event_forward": event_fwd,
        "descriptive_by_horizon": desc,
        "e_c_prediction": {
            "h_star": f"{h_star}d",
            "h_star_rule": "符号最一貫 (多数派符号日数最大)、tie-break |median| 最大 (doc §5.3)",
            "predicted_sign": predicted_sign,
            "median_net_pips": round(h_star_median, 1),
            "band_p25_p75_pips": [
                round(float(np.quantile(h_star_nets, 0.25)), 1),
                round(float(np.quantile(h_star_nets, 0.75)), 1),
            ],
        },
        "permutation_null": perm,
        "identification_rule_calibration": calib,
        "frozen_rule": {
            "form": "candidate(d)=1 <=> close/open-1 <= -Y% AND range(d) >= X*trailing20d_median_range",
            "X": x_frozen,
            "Y_pct": y_frozen,
        },
    }

    if args.skip_2026:
        out["candidate_2026"] = {"skipped": True,
                                 "note": "開発 run — 2026 窓非接触 (最終 run でのみ適用)"}
    else:
        cand = apply_rule_2026(daily, x_frozen, y_frozen)
        cand["hypergeom_thresholds_alpha_0_10"] = hypergeom_thresholds(
            cand["M_business_days"], cand["S_size"])
        out["candidate_2026"] = cand

    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    # console summary
    print(f"episodes: {out['episodes']}")
    print("\nper-event forward (net pips, SELL-favorable = negative):")
    for f in event_fwd:
        nets = {h: f["horizons"][f"h{h}"]["net_pips"] for h in HORIZONS}
        print(f"  {f['event_day']} anchor={f['anchor_day']} entry={f['entry_mid']:.3f} {nets}")
    print("\ndescriptive by horizon:")
    for h in HORIZONS:
        d = desc[f"h{h}"]
        print(f"  h{h}: median={d['net_median_pips']} [{d['net_p25_pips']},{d['net_p75_pips']}] "
              f"sign={d['net_sign_consistency']} mfe_med={d['mfe_median_pips']} mae_med={d['mae_median_pips']}")
    print(f"\nE-C: h*={h_star}d sign={predicted_sign} median={h_star_median:.1f}p "
          f"band={out['e_c_prediction']['band_p25_p75_pips']}")
    print("\npermutation (descriptive only):")
    for h in HORIZONS:
        r = perm["by_horizon"][f"h{h}"]
        print(f"  h{h}: obs={r['obs_median_of_episode_means_pips']} "
              f"null[{r['null_p05_pips']},{r['null_p95_pips']}] "
              f"p1={r['p_one_sided']} p2={r['p_two_sided']}")
    ch = calib["chosen"]
    print(f"\nfrozen rule: Y={y_frozen}% X={x_frozen} "
          f"hits={ch['event_hits']}/7 FP={ch['fp_count']}/{calib['n_non_event_days']} "
          f"({ch['fp_rate']*100:.2f}%)")
    print(f"event hit days: {ch['event_hit_days']}")
    print(f"FP days: {ch['fp_days']}")
    if not args.skip_2026:
        c = out["candidate_2026"]
        print(f"\n2026 window: M={c['M_business_days']} |S|={c['S_size']} S={c['candidate_list_S']}")
        for row in c["hypergeom_thresholds_alpha_0_10"]:
            print(f"  k={row['k']}: P(>=1 overlap)={row['p_overlap_ge_1']} thr={row['threshold']}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
