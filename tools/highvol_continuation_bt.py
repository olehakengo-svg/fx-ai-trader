#!/usr/bin/env python3
"""Pre-registered USD_JPY M5 high-vol continuation grid BT.

Uses the repo-local MASSIVE parquet only. No network or partial fallback.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PAIR = "USD_JPY"
TF = "M5"
PIP_MULT = 100.0
K_VALUES = [2.5, 3.0, 3.5, 4.0, 4.5]
H_BARS = [3, 6, 12]
SPREAD_PIPS = [0.0, 0.2, 0.5, 1.0, 1.3]
HOURSETS = {
    "AGENT_9_11_15": {9, 11, 15},
    "ALL": None,
    "LONDON_07_14": set(range(7, 15)),
    "NY_12_20": set(range(12, 21)),
    "ASIAN_15_22": set(range(15, 23)),
}
M_TESTS = len(K_VALUES) * len(H_BARS) * len(HOURSETS) * len(SPREAD_PIPS)
BONF_ALPHA = 0.05 / M_TESTS
FAMILY_A = "pure_highvol_continuation"
FAMILY_B = "v_reversal_flipped_continuation"
DATA_SOURCE = "MASSIVE_parquet"
DEFAULT_PARQUET = ROOT / "data" / "cache" / "massive" / "USD_JPY_5m_2014_2026.parquet"
DEFAULT_OUT_DIR = ROOT / "reports" / "highvol_continuation_bt"
TASK_FILE = ROOT / ".ai" / "tasks" / "queue" / "20260518-1900-highvol-continuation-bt-usdjpy-m5.md"


@dataclass(frozen=True)
class Trade:
    signal_i: int
    entry_i: int
    exit_i: int
    entry_time: str
    exit_time: str
    direction: str
    gross_pip: float
    pnl_pip: float


def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    rename = {col: col.capitalize() for col in df.columns if col.lower() in {"open", "high", "low", "close", "volume"}}
    out = df.rename(columns=rename).copy()
    required = ["Open", "High", "Low", "Close"]
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"missing OHLC columns: {missing}")
    if not isinstance(out.index, pd.DatetimeIndex):
        for candidate in ("timestamp_utc", "timestamp", "time", "datetime", "Date", "date"):
            if candidate in out.columns:
                out.index = pd.to_datetime(out[candidate], utc=True)
                break
    if not isinstance(out.index, pd.DatetimeIndex):
        raise ValueError("parquet must have a DatetimeIndex or timestamp column")
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out[required].astype(float).dropna()


def load_usdjpy_m5(path: Path = DEFAULT_PARQUET) -> tuple[pd.DataFrame, Path]:
    if not path.exists():
        raise FileNotFoundError(f"missing MASSIVE parquet cache: {path}")
    df = normalize_ohlc(pd.read_parquet(path))
    if df.empty:
        raise ValueError(f"empty MASSIVE parquet cache: {path}")
    return df, path


def add_family_a_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    body = (out["Close"] - out["Open"]).abs()
    out["body_abs"] = body
    out["body_sma20_prior"] = body.shift(1).rolling(20, min_periods=20).mean()
    out["bar_dir"] = np.sign(out["Close"] - out["Open"]).astype(float)
    return out


def add_family_b_columns(df: pd.DataFrame) -> pd.DataFrame:
    from modules.indicators import add_indicators

    return add_family_a_columns(add_indicators(df.copy()))


def hour_mask(index: pd.DatetimeIndex, hourset: str) -> np.ndarray:
    hours = HOURSETS[hourset]
    if hours is None:
        return np.ones(len(index), dtype=bool)
    return np.isin(index.hour.to_numpy(), list(hours))


def apply_cooldown(indices: np.ndarray, cooldown_bars: int = 3) -> list[int]:
    selected: list[int] = []
    last = -10**12
    for raw_i in indices:
        i = int(raw_i)
        if i <= last + cooldown_bars:
            continue
        selected.append(i)
        last = i
    return selected


def family_a_signal_indices(df: pd.DataFrame, k: float, hourset: str) -> list[int]:
    valid = (
        (df["body_abs"] >= k * df["body_sma20_prior"])
        & (df["bar_dir"] != 0)
        & df["body_sma20_prior"].notna()
    ).to_numpy(copy=True)
    valid &= hour_mask(df.index, hourset)
    valid[-1:] = False
    return apply_cooldown(np.flatnonzero(valid))


def family_b_signal_indices(df: pd.DataFrame, hourset: str) -> list[int]:
    close = df["Close"]
    open_ = df["Open"]
    high = df["High"]
    low = df["Low"]
    price_10 = close.shift(10)
    drop = (price_10 - close) * PIP_MULT
    surge = (close - price_10) * PIP_MULT
    bar_range = (high - low).where(high > low, 0.001)
    body_ratio = (close - open_).abs() / bar_range
    prev_stoch = df["stoch_k"].shift(1)

    buy = (
        (drop >= 5.0)
        & (df["rsi"] < 30.0)
        & (df["bb_pband"] < 0.15)
        & (df["stoch_k"] < 20.0)
        & (close > open_)
        & (body_ratio >= 0.20)
        & (df["stoch_k"] > prev_stoch)
    )
    sell = (
        (surge >= 5.0)
        & (df["rsi"] > 70.0)
        & (df["bb_pband"] > 0.85)
        & (df["stoch_k"] > 80.0)
        & (close < open_)
        & (body_ratio >= 0.20)
        & (df["stoch_k"] < prev_stoch)
    )
    valid = (buy | sell).fillna(False).to_numpy(copy=True)
    valid &= hour_mask(df.index, hourset)
    valid[-1:] = False
    return apply_cooldown(np.flatnonzero(valid))


def direction_for_family_a(row: pd.Series) -> int:
    return 1 if float(row["Close"]) > float(row["Open"]) else -1


def direction_for_family_b(row: pd.Series) -> int:
    # Flip current v_reversal direction for continuation ablation.
    reversal_direction = 1 if float(row["Close"]) > float(row["Open"]) else -1
    return -reversal_direction


def simulate_trades(
    df: pd.DataFrame,
    signal_indices: Iterable[int],
    horizon: int,
    spread_pip: float,
    family: str,
) -> list[Trade]:
    closes = df["Close"].to_numpy(dtype=float)
    trades: list[Trade] = []
    n = len(df)
    for i in signal_indices:
        exit_i = int(i) + horizon
        if i < 20 or exit_i >= n:
            continue
        row = df.iloc[int(i)]
        direction = direction_for_family_a(row) if family == FAMILY_A else direction_for_family_b(row)
        if direction == 0:
            continue
        gross_pip = (closes[exit_i] - closes[int(i)]) * PIP_MULT * direction
        pnl_pip = gross_pip - spread_pip
        trades.append(
            Trade(
                signal_i=int(i),
                entry_i=int(i),
                exit_i=exit_i,
                entry_time=df.index[int(i)].isoformat(),
                exit_time=df.index[exit_i].isoformat(),
                direction="BUY" if direction > 0 else "SELL",
                gross_pip=float(gross_pip),
                pnl_pip=float(pnl_pip),
            )
        )
    return trades


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom)


def profit_factor(values: np.ndarray) -> float:
    gross_profit = float(values[values > 0].sum())
    gross_loss = float(-values[values < 0].sum())
    if gross_loss <= 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def p_value_mean_positive(values: np.ndarray) -> float:
    clean = values[np.isfinite(values)]
    n = len(clean)
    if n < 2:
        return 1.0
    mean = float(clean.mean())
    std = float(clean.std(ddof=1))
    if std <= 0:
        return 0.0 if mean > 0 else 1.0
    t_stat = mean / (std / math.sqrt(n))
    try:
        from scipy import stats

        return float(stats.t.sf(t_stat, n - 1))
    except Exception:
        return float(0.5 * math.erfc(t_stat / math.sqrt(2.0)))


def kelly_fraction(values: np.ndarray) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    wins = values[values > 0]
    losses = values[values < 0]
    wr = len(wins) / n
    if len(wins) and not len(losses):
        return 1.0
    if not len(wins) or not len(losses):
        return 0.0
    rr = float(wins.mean() / -losses.mean())
    if rr <= 0 or not math.isfinite(rr):
        return 0.0
    return float(wr - (1.0 - wr) / rr)


def fold_stats(trades: list[Trade]) -> list[dict]:
    if not trades:
        return [{"fold": i, "n": 0, "ev_pip": 0.0, "pass_ev_gt_0": False} for i in range(1, 4)]
    folds = np.array_split(np.arange(len(trades)), 3)
    out: list[dict] = []
    for fold_no, idx in enumerate(folds, start=1):
        values = np.asarray([trades[int(i)].pnl_pip for i in idx], dtype=float)
        ev = float(values.mean()) if len(values) else 0.0
        out.append({"fold": fold_no, "n": int(len(values)), "ev_pip": ev, "pass_ev_gt_0": bool(len(values) and ev > 0)})
    return out


def direction_null(trades: list[Trade]) -> dict:
    values_long = np.asarray([t.pnl_pip for t in trades if t.direction == "BUY"], dtype=float)
    values_short = np.asarray([t.pnl_pip for t in trades if t.direction == "SELL"], dtype=float)
    long_ev = float(values_long.mean()) if len(values_long) else 0.0
    short_ev = float(values_short.mean()) if len(values_short) else 0.0
    passed = bool(len(values_long) and len(values_short) and long_ev > 0 and short_ev > 0)
    return {
        "long_n": int(len(values_long)),
        "long_ev_pip": long_ev,
        "short_n": int(len(values_short)),
        "short_ev_pip": short_ev,
        "pass_symmetric_positive": passed,
    }


def bh_adjust(rows: list[dict]) -> None:
    ordered = sorted(rows, key=lambda row: float(row["p_value"]))
    m = len(ordered)
    prev = 1.0
    adjusted: dict[str, float] = {}
    for rank_from_end, row in enumerate(reversed(ordered), start=1):
        rank = m - rank_from_end + 1
        p_adj = min(prev, float(row["p_value"]) * m / rank)
        adjusted[row["cell_id"]] = min(1.0, p_adj)
        prev = p_adj
    for row in rows:
        row["p_bh"] = adjusted[row["cell_id"]]
        row["bonf_alpha"] = BONF_ALPHA
        row["g4_bh_bonf_pass"] = bool(row["p_bh"] < BONF_ALPHA)


def classify(row: dict) -> str:
    g1 = row["n"] >= 30
    g2 = row["wilson_lo"] >= 0.50
    g3 = row["ev_pip"] > 0
    g4 = row["p_bh"] < BONF_ALPHA
    g5 = row["pf"] >= 1.20
    g6 = row["kelly"] >= 0.05
    g7 = row["wf_all_ev_gt_0"]
    g8 = row["direction_null"]["pass_symmetric_positive"]
    row["gates"] = {
        "G1_N": g1,
        "G2_Wilson": g2,
        "G3_EV": g3,
        "G4_Bonf_BH": g4,
        "G5_PF": g5,
        "G6_Kelly": g6,
        "G7_WF": g7,
        "G8_Direction_Null": g8,
    }
    if all(row["gates"].values()):
        return "SHADOW_CANDIDATE"
    if g1 and g2 and g3:
        return "NEEDS_MORE_EVIDENCE"
    return "REJECT"


def cell_id(family: str, k: float, horizon: int, hourset: str, spread_pip: float) -> str:
    spread = str(spread_pip).replace(".", "p")
    return f"{PAIR}_{TF}_{family}_K{k:g}_H{horizon}_{hourset}_SP{spread}"


def stats_for_cell(
    *,
    family: str,
    k: float,
    horizon: int,
    hourset: str,
    spread_pip: float,
    trades: list[Trade],
    period_start: str,
    period_end: str,
    generated_at: str,
    source_path: Path,
) -> dict:
    values = np.asarray([t.pnl_pip for t in trades], dtype=float)
    gross_values = np.asarray([t.gross_pip for t in trades], dtype=float)
    n = int(len(values))
    wins = int((values > 0).sum()) if n else 0
    wf = fold_stats(trades)
    dnull = direction_null(trades)
    breakeven = float(gross_values.mean()) if n else 0.0
    return {
        "cell_id": cell_id(family, k, horizon, hourset, spread_pip),
        "family": family,
        "pair": PAIR,
        "tf": TF,
        "K": k,
        "H_bar": horizon,
        "hourset": hourset,
        "spread_pip_round_trip": spread_pip,
        "n": n,
        "wins": wins,
        "wr": float(wins / n) if n else 0.0,
        "wilson_lo": wilson_lower(wins, n),
        "ev_pip": float(values.mean()) if n else 0.0,
        "gross_ev_pip": float(gross_values.mean()) if n else 0.0,
        "total_pip": float(values.sum()) if n else 0.0,
        "pf": profit_factor(values) if n else 0.0,
        "kelly": kelly_fraction(values),
        "p_value": p_value_mean_positive(values),
        "p_bh": 1.0,
        "wf_all_ev_gt_0": all(item["pass_ev_gt_0"] for item in wf),
        "wf": wf,
        "direction_null": dnull,
        "breakeven_spread_pip_round_trip": breakeven,
        "broker_survival": {
            "GMO_DMM_0p2": breakeven > 0.2,
            "OANDA_Japan_0p5": breakeven > 0.5,
            "OANDA_USA_1p3": breakeven > 1.3,
        },
        "period_start": period_start,
        "period_end": period_end,
        "bt_data_source": DATA_SOURCE,
        "source_path": str(source_path.relative_to(ROOT)) if source_path.is_relative_to(ROOT) else str(source_path),
        "generated_at": generated_at,
    }


def compute_family_grid(df: pd.DataFrame, source_path: Path, family: str, generated_at: str) -> tuple[list[dict], dict[str, list[Trade]]]:
    rows: list[dict] = []
    trades_by_cell: dict[str, list[Trade]] = {}
    period_start = df.index.min().isoformat()
    period_end = df.index.max().isoformat()
    b_cache: dict[str, list[int]] = {}
    for hourset in HOURSETS:
        if family == FAMILY_B:
            b_cache[hourset] = family_b_signal_indices(df, hourset)
        for k in K_VALUES:
            indices = family_a_signal_indices(df, k, hourset) if family == FAMILY_A else b_cache[hourset]
            for horizon in H_BARS:
                for spread_pip in SPREAD_PIPS:
                    trades = simulate_trades(df, indices, horizon, spread_pip, family)
                    row = stats_for_cell(
                        family=family,
                        k=k,
                        horizon=horizon,
                        hourset=hourset,
                        spread_pip=spread_pip,
                        trades=trades,
                        period_start=period_start,
                        period_end=period_end,
                        generated_at=generated_at,
                        source_path=source_path,
                    )
                    rows.append(row)
                    trades_by_cell[row["cell_id"]] = trades
    bh_adjust(rows)
    for row in rows:
        row["verdict"] = classify(row)
    return rows, trades_by_cell


def finite_json_value(value):
    if isinstance(value, dict):
        return {k: finite_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [finite_json_value(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return "inf" if value > 0 else "-inf"
    return value


def fmt(value: float | int | str, digits: int = 4) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, float) and not math.isfinite(value):
        return "inf" if value > 0 else "-inf"
    return f"{float(value):.{digits}f}"


def evidence_line(row: dict) -> str:
    return (
        f"K={row['K']:g} H={row['H_bar']} hourset={row['hourset']} spread={row['spread_pip_round_trip']:g} "
        f"N={row['n']} WR={fmt(row['wr'], 3)} Wilson_lo={fmt(row['wilson_lo'], 3)} "
        f"EV={fmt(row['ev_pip'], 2)}pip PF={fmt(row['pf'], 2)} Kelly={fmt(row['kelly'], 3)} "
        f"p_BH={fmt(row['p_bh'], 6)} G8={row['direction_null']['pass_symmetric_positive']} "
        f"Verdict={row['verdict']}"
    )


def baseline_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if abs(float(r["spread_pip_round_trip"]) - 0.5) < 1e-12]


def build_summary(rows_a: list[dict], rows_b: list[dict], generated_at: str) -> str:
    shadow = [r for r in rows_a if r["verdict"] == "SHADOW_CANDIDATE"]
    needs = [r for r in rows_a if r["verdict"] == "NEEDS_MORE_EVIDENCE"]
    reject = [r for r in rows_a if r["verdict"] == "REJECT"]
    top = sorted(rows_a, key=lambda r: (r["verdict"] == "SHADOW_CANDIDATE", r["ev_pip"], r["pf"]), reverse=True)[:10]
    top_baseline = sorted(baseline_rows(rows_a), key=lambda r: (r["verdict"] == "SHADOW_CANDIDATE", r["ev_pip"], r["pf"]), reverse=True)[:10]
    ref = rows_a[0] if rows_a else {}
    lines = [
        "# HighVol Continuation USDJPY M5 BT Summary",
        "",
        f"Generated: {generated_at}",
        f"Data: {DATA_SOURCE} {ref.get('source_path', 'unknown')}",
        f"Period: {ref.get('period_start', 'unknown')} .. {ref.get('period_end', 'unknown')}",
        f"Pre-reg cells: {M_TESTS}, Bonferroni alpha: {BONF_ALPHA:.8f}",
        "",
        "## Verdict Matrix",
        f"- Family A cells: {len(rows_a)}",
        f"- Family A SHADOW_CANDIDATE: {len(shadow)}",
        f"- Family A NEEDS_MORE_EVIDENCE: {len(needs)}",
        f"- Family A REJECT: {len(reject)}",
        f"- Family B ablation cells: {len(rows_b)}",
        "",
        "## Family A Top Cells All Spreads",
    ]
    lines.extend(f"- {evidence_line(row)}" for row in top)
    lines.extend(["", "## Family A Top Cells Baseline Spread 0.5"])
    lines.extend(f"- {evidence_line(row)}" for row in top_baseline)
    lines.extend(
        [
            "",
            "## Gate Definitions",
            "- G1 N: N >= 30",
            "- G2 Wilson: Wilson lower 95% >= 0.50",
            "- G3 EV: EV pip/trade after round-trip spread > 0",
            f"- G4 Bonf/BH: BH adjusted p < {BONF_ALPHA:.8f}",
            "- G5 PF: PF >= 1.20",
            "- G6 Kelly: Kelly fraction >= 0.05",
            "- G7 WF: 3 chronological folds all EV > 0",
            "- G8 Direction-led null: both BUY-only and SELL-only EV are positive",
        ]
    )
    return "\n".join(lines) + "\n"


def build_null_summary(rows_a: list[dict], rows_b: list[dict], generated_at: str) -> str:
    def fail_counts(rows: list[dict]) -> dict[str, int]:
        keys = ["G1_N", "G2_Wilson", "G3_EV", "G4_Bonf_BH", "G5_PF", "G6_Kelly", "G7_WF", "G8_Direction_Null"]
        return {f"{key}_fail": sum(1 for r in rows if not r["gates"][key]) for key in keys}

    lines = ["# HighVol Continuation Null Summary", "", f"Generated: {generated_at}", ""]
    for name, rows in (("Family A", rows_a), ("Family B", rows_b)):
        lines.append(f"## {name}")
        lines.append(f"- cells: {len(rows)}")
        for key, value in fail_counts(rows).items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    return "\n".join(lines)


def build_ablation(rows_a: list[dict], rows_b: list[dict], generated_at: str) -> str:
    b_by_key = {(r["K"], r["H_bar"], r["hourset"], r["spread_pip_round_trip"]): r for r in rows_b}
    baseline_a = baseline_rows(rows_a)
    lines = [
        "# Family A vs v_reversal-Flipped Ablation",
        "",
        f"Generated: {generated_at}",
        "",
        "## Design Diff",
        "| Item | Family A Pure HighVol Continuation | Family B v_reversal flipped |",
        "|---|---|---|",
        "| Entry trigger | `body_t >= K * SMA20_prior(abs(body))` at configured UTC hours | Current v_reversal shock + RSI/BB%B/Stoch reversal trigger |",
        "| Direction | Continuation of signal bar body | Opposite of current v_reversal signal direction |",
        "| Exit | H-bar close time stop | Same H-bar close time stop for comparability |",
        "| Spread | Round-trip spread grid applied to each trade | Same |",
        "",
        "## Baseline Spread 0.5 Per-cell Comparison",
        "| K | H | Hourset | A N | A EV | A PF | A Verdict | B N | B EV | B PF | B Verdict |",
        "|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for row in sorted(baseline_a, key=lambda r: (r["K"], r["H_bar"], r["hourset"])):
        b = b_by_key[(row["K"], row["H_bar"], row["hourset"], row["spread_pip_round_trip"])]
        lines.append(
            f"| {row['K']:g} | {row['H_bar']} | {row['hourset']} | "
            f"{row['n']} | {fmt(row['ev_pip'], 2)} | {fmt(row['pf'], 2)} | {row['verdict']} | "
            f"{b['n']} | {fmt(b['ev_pip'], 2)} | {fmt(b['pf'], 2)} | {b['verdict']} |"
        )
    return "\n".join(lines) + "\n"


def build_spread_sensitivity(rows_a: list[dict], generated_at: str) -> str:
    best_by_shape: dict[tuple[float, int, str], dict] = {}
    for row in rows_a:
        key = (row["K"], row["H_bar"], row["hourset"])
        current = best_by_shape.get(key)
        if current is None or row["breakeven_spread_pip_round_trip"] > current["breakeven_spread_pip_round_trip"]:
            best_by_shape[key] = row
    ranked = sorted(best_by_shape.values(), key=lambda r: r["breakeven_spread_pip_round_trip"], reverse=True)
    lines = [
        "# HighVol Continuation Spread Sensitivity",
        "",
        f"Generated: {generated_at}",
        "",
        "## Breakeven Spread Ranking",
        "| Rank | K | H | Hourset | N | Gross EV | Breakeven RT Spread | GMO/DMM 0.2 | OANDA JP 0.5 | OANDA USA 1.3 |",
        "|---:|---:|---:|---|---:|---:|---:|---|---|---|",
    ]
    for rank, row in enumerate(ranked[:30], start=1):
        surv = row["broker_survival"]
        lines.append(
            f"| {rank} | {row['K']:g} | {row['H_bar']} | {row['hourset']} | {row['n']} | "
            f"{fmt(row['gross_ev_pip'], 2)} | {fmt(row['breakeven_spread_pip_round_trip'], 2)} | "
            f"{surv['GMO_DMM_0p2']} | {surv['OANDA_Japan_0p5']} | {surv['OANDA_USA_1p3']} |"
        )
    lines.extend(["", "## All Cells", "| K | H | Hourset | Spread | N | EV | PF | Verdict |", "|---:|---:|---|---:|---:|---:|---:|---|"])
    for row in sorted(rows_a, key=lambda r: (r["K"], r["H_bar"], r["hourset"], r["spread_pip_round_trip"])):
        lines.append(
            f"| {row['K']:g} | {row['H_bar']} | {row['hourset']} | {row['spread_pip_round_trip']:g} | "
            f"{row['n']} | {fmt(row['ev_pip'], 2)} | {fmt(row['pf'], 2)} | {row['verdict']} |"
        )
    return "\n".join(lines) + "\n"


def append_result_section(path: Path, rows_a: list[dict], rows_b: list[dict], generated_at: str) -> None:
    shadow = [r for r in rows_a if r["verdict"] == "SHADOW_CANDIDATE"]
    needs = [r for r in rows_a if r["verdict"] == "NEEDS_MORE_EVIDENCE"]
    reject = [r for r in rows_a if r["verdict"] == "REJECT"]
    top = sorted(rows_a, key=lambda r: (r["verdict"] == "SHADOW_CANDIDATE", r["ev_pip"], r["pf"]), reverse=True)[:5]
    best_by_shape: dict[tuple[float, int, str], dict] = {}
    for row in rows_a:
        key = (row["K"], row["H_bar"], row["hourset"])
        if key not in best_by_shape:
            best_by_shape[key] = row
    best_breakeven = sorted(best_by_shape.values(), key=lambda r: r["breakeven_spread_pip_round_trip"], reverse=True)[:5]
    result = [
        "",
        "<!-- highvol_continuation_bt_result -->",
        "## Result: HighVol Continuation BT",
        "",
        f"Generated: {generated_at}",
        f"投入 cell 数: {len(rows_a)}",
        f"SHADOW_CANDIDATE: {len(shadow)}",
        f"NEEDS_MORE_EVIDENCE: {len(needs)}",
        f"REJECT: {len(reject)}",
        "",
        "Top 5 cell:",
    ]
    for row in top:
        result.append(
            f"- K={row['K']:g}, H={row['H_bar']}, hourset={row['hourset']}, spread={row['spread_pip_round_trip']:g}, "
            f"N={row['n']}, WR={fmt(row['wr'], 3)}, Wilson_lo={fmt(row['wilson_lo'], 3)}, "
            f"EV={fmt(row['ev_pip'], 2)}, PF={fmt(row['pf'], 2)}, p_BH={fmt(row['p_bh'], 6)}"
        )
    result.extend(["", "Family A vs B ablation major diff: Family A uses direct body/SMA20 continuation; Family B reuses current v_reversal trigger and flips its direction, so K is an inert comparison label for B."])
    result.append("")
    result.append("Spread breakeven pip ranking:")
    for row in best_breakeven:
        result.append(f"- K={row['K']:g}, H={row['H_bar']}, hourset={row['hourset']}: {fmt(row['breakeven_spread_pip_round_trip'], 2)} pip RT")
    result.extend(["", "Next task: Phase B cross-pair OOS and exact TV 1yr window reconciliation if local May 2026 cache is backfilled.", ""])
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    marker = "<!-- highvol_continuation_bt_result -->"
    if marker in existing:
        existing = existing.split(marker)[0].rstrip() + "\n"
    path.write_text(existing + "\n".join(result), encoding="utf-8")


def write_shadow_strategy(path: Path, best: dict) -> None:
    text = f'''"""HighVol Continuation JPY M5 shadow candidate.

Generated only because the pre-registered grid produced at least one
SHADOW_CANDIDATE. Human review is still required before live DB routing.
"""
from __future__ import annotations

from strategies.base import Candidate, StrategyBase


class HighVolContinuationJpyM5(StrategyBase):
    name = "highvol_continuation_jpy_m5"
    mode = "scalp"
    enabled = False
    strategy_type = "MOMENTUM"

    k = {best["K"]!r}
    horizon_bars = {best["H_bar"]!r}

    def evaluate(self, ctx):
        if ctx.df is None or len(ctx.df) < 22:
            return None
        df = ctx.df
        row = df.iloc[-1]
        bodies = (df["Close"] - df["Open"]).abs()
        sma20 = float(bodies.iloc[-21:-1].mean())
        if sma20 <= 0:
            return None
        close = float(row["Close"])
        open_ = float(row["Open"])
        body = abs(close - open_)
        if body < self.k * sma20 or close == open_:
            return None
        signal = "BUY" if close > open_ else "SELL"
        return Candidate(
            signal=signal,
            confidence=55,
            sl=0.0,
            tp=0.0,
            reasons=[f"highvol continuation: body/SMA20={{body / sma20:.2f}} >= K={{self.k}}"],
            entry_type=self.name,
            score=3.0,
            max_hold_bars=self.horizon_bars,
        )
'''
    path.write_text(text, encoding="utf-8")


def write_reports(out_dir: Path, rows_a: list[dict], rows_b: list[dict], generated_at: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "per_cell").mkdir(exist_ok=True)
    (out_dir / "wf_3fold").mkdir(exist_ok=True)
    for row in rows_a:
        (out_dir / "per_cell" / f"{row['cell_id']}.json").write_text(json.dumps(finite_json_value(row), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        wf_payload = {"cell_id": row["cell_id"], "family": row["family"], "wf": row["wf"]}
        (out_dir / "wf_3fold" / f"{row['cell_id']}.json").write_text(json.dumps(finite_json_value(wf_payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(build_summary(rows_a, rows_b, generated_at), encoding="utf-8")
    (out_dir / "null_summary.md").write_text(build_null_summary(rows_a, rows_b, generated_at), encoding="utf-8")
    (out_dir / "ablation.md").write_text(build_ablation(rows_a, rows_b, generated_at), encoding="utf-8")
    (out_dir / "spread_sensitivity.md").write_text(build_spread_sensitivity(rows_a, generated_at), encoding="utf-8")
    append_result_section(TASK_FILE, rows_a, rows_b, generated_at)
    shadow_a = [r for r in rows_a if r["verdict"] == "SHADOW_CANDIDATE"]
    if shadow_a:
        best = sorted(shadow_a, key=lambda r: (r["spread_pip_round_trip"] == 0.5, r["ev_pip"], r["pf"]), reverse=True)[0]
        write_shadow_strategy(ROOT / "strategies" / "scalp" / "highvol_continuation_jpy_m5.py", best)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet", default=str(DEFAULT_PARQUET))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--family", choices=["A", "B", "both"], default="both")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generated_at = datetime.now(timezone.utc).isoformat()
    df_raw, source_path = load_usdjpy_m5(Path(args.parquet))
    rows_a: list[dict] = []
    rows_b: list[dict] = []
    if args.family in {"A", "both"}:
        rows_a, _ = compute_family_grid(add_family_a_columns(df_raw), source_path, FAMILY_A, generated_at)
    if args.family in {"B", "both"}:
        rows_b, _ = compute_family_grid(add_family_b_columns(df_raw), source_path, FAMILY_B, generated_at)
    write_reports(Path(args.out_dir), rows_a, rows_b, generated_at)
    print(f"period_start={df_raw.index.min().isoformat()}")
    print(f"period_end={df_raw.index.max().isoformat()}")
    print(f"family_a_cells={len(rows_a)}")
    print(f"family_b_cells={len(rows_b)}")
    print(f"family_a_shadow={sum(1 for r in rows_a if r['verdict'] == 'SHADOW_CANDIDATE')}")
    print(f"family_a_needs={sum(1 for r in rows_a if r['verdict'] == 'NEEDS_MORE_EVIDENCE')}")
    print(f"family_a_reject={sum(1 for r in rows_a if r['verdict'] == 'REJECT')}")
    print(f"reports={Path(args.out_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
