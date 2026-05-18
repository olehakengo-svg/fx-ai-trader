#!/usr/bin/env python3
"""Pre-registered USD_JPY M5 volatility-exhaustion fade grid BT.

Uses repo-local MASSIVE parquet only. No partial TF fallback.
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
SPREAD_PIP = 1.3
ROUND_TRIP_SPREAD_PIP = SPREAD_PIP * 2.0
K_VALUES = [3.0, 3.5, 4.0, 4.5]
H_BARS = [3, 6, 12]
SESSIONS = {
    "ALL": None,
    "ASIAN_15-22_UTC": (15, 22),
    "LONDON_07-14_UTC": (7, 14),
    "NY_12-20_UTC": (12, 20),
}
M_TESTS = len(K_VALUES) * len(H_BARS) * len(SESSIONS)
BONF_ALPHA = 0.05 / M_TESTS
FAMILY_A = "pure_vol_exhaustion_fade"
FAMILY_B = "v_reversal_current"
DATA_SOURCE = "MASSIVE_parquet"
DEFAULT_END_DATE = "2026-05-14"
TASK_FILE = ROOT / ".ai" / "tasks" / "queue" / "20260515-2235-vol-exhaustion-fade-bt-usdjpy-m5.md"


@dataclass(frozen=True)
class Trade:
    signal_i: int
    entry_i: int
    exit_i: int
    entry_time: str
    exit_time: str
    direction: str
    pnl_pip: float
    gross_pip: float
    exit_reason: str


def pip_mult(pair: str) -> float:
    return 100.0 if "JPY" in pair else 10000.0


def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    rename = {col: col.capitalize() for col in df.columns if col.lower() in {"open", "high", "low", "close", "volume"}}
    out = df.rename(columns=rename).copy()
    required = ["Open", "High", "Low", "Close"]
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"missing OHLC columns: {missing}")
    if not isinstance(out.index, pd.DatetimeIndex):
        for candidate in ("timestamp_utc", "time", "timestamp", "datetime", "Date", "date"):
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


def load_usdjpy_m5(cache_dir: Path, end_date: str | None = DEFAULT_END_DATE) -> tuple[pd.DataFrame, Path]:
    path = cache_dir / "USD_JPY_5m.parquet"
    if not path.exists():
        raise FileNotFoundError(f"missing MASSIVE parquet cache: {path}")
    df = normalize_ohlc(pd.read_parquet(path))
    if end_date:
        end_exclusive = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)
        df = df[df.index < end_exclusive]
    if df.empty:
        raise ValueError("USD_JPY M5 parquet has no rows after end-date filter")
    return df, path


def atr14(df: pd.DataFrame) -> pd.Series:
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    # Wilder-style ATR without requiring indicator side effects.
    return tr.ewm(alpha=1.0 / 14.0, adjust=False, min_periods=14).mean()


def add_family_a_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    body = (out["Close"] - out["Open"]).abs()
    out["body_abs"] = body
    out["body_sma20_prior"] = body.shift(1).rolling(20, min_periods=20).mean()
    out["atr14"] = atr14(out)
    out["bar_dir"] = np.sign(out["Close"] - out["Open"]).astype(float)
    return out


def add_family_b_columns(df: pd.DataFrame) -> pd.DataFrame:
    from modules.indicators import add_indicators

    out = add_indicators(df.copy())
    # Preserve full-length alignment after indicator warmup by recomputing A columns
    # on the indicator frame used by Family B.
    return add_family_a_columns(out)


def session_mask(index: pd.DatetimeIndex, session: str) -> np.ndarray:
    spec = SESSIONS[session]
    if spec is None:
        return np.ones(len(index), dtype=bool)
    start, end = spec
    hours = index.hour.to_numpy()
    if start <= end:
        return (hours >= start) & (hours <= end)
    return (hours >= start) | (hours <= end)


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


def family_a_signal_indices(df: pd.DataFrame, k: float, session: str) -> list[int]:
    valid = (
        (df["body_abs"] >= k * df["body_sma20_prior"])
        & (df["bar_dir"] != 0)
        & df["atr14"].notna()
    ).to_numpy(copy=True)
    valid &= session_mask(df.index, session)
    # Need at least one future bar for exit scanning; actual H validity is handled per cell.
    valid[-1:] = False
    return apply_cooldown(np.flatnonzero(valid))


def family_b_signal_indices(df: pd.DataFrame, session: str) -> list[int]:
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
    valid &= session_mask(df.index, session)
    valid[-1:] = False
    return apply_cooldown(np.flatnonzero(valid))


def direction_for_family_a(row: pd.Series) -> int:
    # Fade the signal bar body.
    return -1 if float(row["Close"]) > float(row["Open"]) else 1


def direction_for_family_b(row: pd.Series) -> int:
    # Existing v_reversal buys after down-move recovery, sells after up-move rejection.
    return 1 if float(row["Close"]) > float(row["Open"]) else -1


def tp_sl_for_family_a(row: pd.Series, direction: int) -> tuple[float, float]:
    entry = float(row["Close"])
    atr = float(row["atr14"])
    tp = entry + direction * atr
    sl = entry - direction * atr * 1.5
    return tp, sl


def tp_sl_for_family_b(df: pd.DataFrame, i: int, direction: int) -> tuple[float, float]:
    row = df.iloc[i]
    entry = float(row["Close"])
    atr7_value = float(row.get("atr7", row.get("atr", 0.0)))
    if direction > 0:
        tp = entry + atr7_value * 1.5
        recent_low = float(df["Low"].iloc[max(0, i - 2) : i + 1].min())
        sl = min(entry - atr7_value * 0.7, recent_low - 0.002)
    else:
        tp = entry - atr7_value * 1.5
        recent_high = float(df["High"].iloc[max(0, i - 2) : i + 1].max())
        sl = max(entry + atr7_value * 0.7, recent_high + 0.002)
    return tp, sl


def simulate_trades(df: pd.DataFrame, signal_indices: Iterable[int], horizon: int, family: str) -> list[Trade]:
    opens = df["Open"].to_numpy(dtype=float)
    highs = df["High"].to_numpy(dtype=float)
    lows = df["Low"].to_numpy(dtype=float)
    closes = df["Close"].to_numpy(dtype=float)
    trades: list[Trade] = []
    n = len(df)
    for i in signal_indices:
        exit_i = i + horizon
        if i < 20 or exit_i >= n:
            continue
        row = df.iloc[i]
        direction = direction_for_family_a(row) if family == FAMILY_A else direction_for_family_b(row)
        if direction == 0:
            continue
        entry = closes[i]
        tp, sl = tp_sl_for_family_a(row, direction) if family == FAMILY_A else tp_sl_for_family_b(df, i, direction)
        hit_i = exit_i
        exit_price = closes[exit_i]
        exit_reason = "TIME"
        for j in range(i + 1, exit_i + 1):
            if direction > 0:
                hit_sl = lows[j] <= sl
                hit_tp = highs[j] >= tp
                if hit_sl and hit_tp:
                    hit_i, exit_price, exit_reason = j, sl, "SL_BOTH_HIT_CONSERVATIVE"
                    break
                if hit_sl:
                    hit_i, exit_price, exit_reason = j, sl, "SL"
                    break
                if hit_tp:
                    hit_i, exit_price, exit_reason = j, tp, "TP"
                    break
            else:
                hit_sl = highs[j] >= sl
                hit_tp = lows[j] <= tp
                if hit_sl and hit_tp:
                    hit_i, exit_price, exit_reason = j, sl, "SL_BOTH_HIT_CONSERVATIVE"
                    break
                if hit_sl:
                    hit_i, exit_price, exit_reason = j, sl, "SL"
                    break
                if hit_tp:
                    hit_i, exit_price, exit_reason = j, tp, "TP"
                    break
        gross_pip = (exit_price - entry) * PIP_MULT * direction
        pnl_pip = gross_pip - ROUND_TRIP_SPREAD_PIP
        trades.append(
            Trade(
                signal_i=int(i),
                entry_i=int(i),
                exit_i=int(hit_i),
                entry_time=df.index[i].isoformat(),
                exit_time=df.index[hit_i].isoformat(),
                direction="BUY" if direction > 0 else "SELL",
                pnl_pip=float(pnl_pip),
                gross_pip=float(gross_pip),
                exit_reason=exit_reason,
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


def wf_stats(trades: list[Trade]) -> list[dict]:
    if not trades:
        return [{"fold": i, "n": 0, "ev_pip": 0.0, "pass_ev_gt_0": False} for i in range(1, 4)]
    folds = np.array_split(np.arange(len(trades)), 3)
    out: list[dict] = []
    for fold_no, idx in enumerate(folds, start=1):
        values = np.asarray([trades[int(i)].pnl_pip for i in idx], dtype=float)
        ev = float(values.mean()) if len(values) else 0.0
        out.append({"fold": fold_no, "n": int(len(values)), "ev_pip": ev, "pass_ev_gt_0": bool(len(values) and ev > 0)})
    return out


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
    row["gates"] = {"G1_N": g1, "G2_Wilson": g2, "G3_EV": g3, "G4_Bonf_BH": g4, "G5_PF": g5, "G6_Kelly": g6, "G7_WF": g7}
    if all(row["gates"].values()):
        return "SHADOW_CANDIDATE"
    if g1 and g2 and g3:
        return "NEEDS_MORE_EVIDENCE"
    return "REJECT"


def cell_id(family: str, k: float, horizon: int, session: str) -> str:
    return f"{PAIR}_{TF}_{family}_K{k:g}_H{horizon}_{session}"


def stats_for_cell(
    *,
    family: str,
    k: float,
    horizon: int,
    session: str,
    trades: list[Trade],
    period_start: str,
    period_end: str,
    generated_at: str,
    source_path: Path,
) -> dict:
    values = np.asarray([t.pnl_pip for t in trades], dtype=float)
    n = int(len(values))
    wins = int((values > 0).sum()) if n else 0
    wf = wf_stats(trades)
    return {
        "cell_id": cell_id(family, k, horizon, session),
        "family": family,
        "pair": PAIR,
        "tf": TF,
        "K": k,
        "H_bar": horizon,
        "session": session,
        "n": n,
        "wins": wins,
        "wr": float(wins / n) if n else 0.0,
        "wilson_lo": wilson_lower(wins, n),
        "ev_pip": float(values.mean()) if n else 0.0,
        "total_pip": float(values.sum()) if n else 0.0,
        "pf": profit_factor(values) if n else 0.0,
        "kelly": kelly_fraction(values),
        "p_value": p_value_mean_positive(values),
        "p_bh": 1.0,
        "wf_all_ev_gt_0": all(item["pass_ev_gt_0"] for item in wf),
        "wf": wf,
        "tp_count": sum(1 for t in trades if t.exit_reason == "TP"),
        "sl_count": sum(1 for t in trades if t.exit_reason.startswith("SL")),
        "time_count": sum(1 for t in trades if t.exit_reason == "TIME"),
        "spread_pip_per_side": SPREAD_PIP,
        "round_trip_spread_pip": ROUND_TRIP_SPREAD_PIP,
        "period_start": period_start,
        "period_end": period_end,
        "bt_data_source": DATA_SOURCE,
        "source_path": str(source_path.relative_to(ROOT)) if source_path.is_relative_to(ROOT) else str(source_path),
        "generated_at": generated_at,
    }


def compute_family_grid(df: pd.DataFrame, source_path: Path, family: str, generated_at: str) -> tuple[list[dict], dict[str, list[Trade]]]:
    period_start = df.index.min().isoformat()
    period_end = df.index.max().isoformat()
    rows: list[dict] = []
    trades_by_cell: dict[str, list[Trade]] = {}
    b_cache: dict[str, list[int]] = {}
    for session in SESSIONS:
        if family == FAMILY_B:
            b_cache[session] = family_b_signal_indices(df, session)
        for k in K_VALUES:
            signal_indices = family_a_signal_indices(df, k, session) if family == FAMILY_A else b_cache[session]
            for horizon in H_BARS:
                trades = simulate_trades(df, signal_indices, horizon, family)
                row = stats_for_cell(
                    family=family,
                    k=k,
                    horizon=horizon,
                    session=session,
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
        f"K={row['K']:g} H={row['H_bar']} session={row['session']} "
        f"N={row['n']} WR={fmt(row['wr'], 3)} Wilson_lo={fmt(row['wilson_lo'], 3)} "
        f"EV={fmt(row['ev_pip'], 2)}pip PF={fmt(row['pf'], 2)} "
        f"Kelly={fmt(row['kelly'], 3)} p_BH={fmt(row['p_bh'], 6)} "
        f"WF={row['wf_all_ev_gt_0']} Verdict={row['verdict']}"
    )


def write_reports(
    out_dir: Path,
    rows_a: list[dict],
    rows_b: list[dict],
    trades_a: dict[str, list[Trade]],
    generated_at: str,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "per_cell").mkdir(exist_ok=True)
    (out_dir / "wf_3fold").mkdir(exist_ok=True)
    all_rows = rows_a + rows_b
    for row in all_rows:
        payload = finite_json_value(row)
        (out_dir / "per_cell" / f"{row['cell_id']}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        wf_payload = {"cell_id": row["cell_id"], "family": row["family"], "wf": row["wf"]}
        (out_dir / "wf_3fold" / f"{row['cell_id']}.json").write_text(json.dumps(finite_json_value(wf_payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = build_summary(rows_a, rows_b, generated_at)
    null_summary = build_null_summary(rows_a, rows_b, generated_at)
    ablation = build_ablation(rows_a, rows_b, generated_at)
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    (out_dir / "null_summary.md").write_text(null_summary, encoding="utf-8")
    (out_dir / "ablation.md").write_text(ablation, encoding="utf-8")
    append_result_section(TASK_FILE, rows_a, rows_b, generated_at)

    shadow_a = [r for r in rows_a if r["verdict"] == "SHADOW_CANDIDATE"]
    if shadow_a:
        best = sorted(shadow_a, key=lambda r: (r["ev_pip"], r["pf"]), reverse=True)[0]
        write_shadow_strategy(ROOT / "strategies" / "scalp" / "vol_exhaustion_fade.py", best)


def build_summary(rows_a: list[dict], rows_b: list[dict], generated_at: str) -> str:
    ref_rows = rows_a or rows_b
    period_start = ref_rows[0]["period_start"] if ref_rows else "unknown"
    period_end = ref_rows[0]["period_end"] if ref_rows else "unknown"
    caveat = ""
    if ref_rows and pd.Timestamp(period_end) < pd.Timestamp(DEFAULT_END_DATE, tz="UTC"):
        caveat = f"Data caveat: local cache ends before target {DEFAULT_END_DATE}; backfill required for exact target-window rerun."
    shadow = [r for r in rows_a if r["verdict"] == "SHADOW_CANDIDATE"]
    needs = [r for r in rows_a if r["verdict"] == "NEEDS_MORE_EVIDENCE"]
    reject = [r for r in rows_a if r["verdict"] == "REJECT"]
    top = sorted(rows_a, key=lambda r: (r["verdict"] == "SHADOW_CANDIDATE", r["ev_pip"], r["pf"]), reverse=True)[:10]
    b_top = sorted(rows_b, key=lambda r: (r["ev_pip"], r["pf"]), reverse=True)[:5]
    lines = [
        "# Vol Exhaustion Fade BT Summary",
        "",
        f"Generated: {generated_at}",
        f"Data: {DATA_SOURCE} USD_JPY M5, spread={SPREAD_PIP} pip per side",
        f"Period: {period_start} .. {period_end}",
        caveat,
        f"Pre-reg m: {M_TESTS}, Bonferroni alpha: {BONF_ALPHA:.8f}",
        "",
        "## Verdict Matrix",
        f"- Family A SHADOW_CANDIDATE: {len(shadow)}",
        f"- Family A NEEDS_MORE_EVIDENCE: {len(needs)}",
        f"- Family A REJECT: {len(reject)}",
        f"- Family B generated cells: {len(rows_b)}",
        "",
        "## Family A Top Cells",
    ]
    for row in top:
        lines.append(f"- {evidence_line(row)}")
    lines.append("")
    lines.append("## Family B Top Cells")
    for row in b_top:
        lines.append(f"- {evidence_line(row)}")
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
        ]
    )
    if not shadow:
        lines.extend(
            [
                "",
                "## Re-grid Candidates",
                "- Keep MA trend filters out; the current failure/survival pattern should be explored with K/cooldown/session/exit geometry only.",
                "- Phase B candidates: cross-pair OOS on non-XAU FX majors and a cooldown sweep around 0/3/6 bars.",
            ]
        )
    return "\n".join(lines) + "\n"


def build_null_summary(rows_a: list[dict], rows_b: list[dict], generated_at: str) -> str:
    def fail_counts(rows: list[dict]) -> dict[str, int]:
        return {
            "G1_N_fail": sum(1 for r in rows if not r["gates"]["G1_N"]),
            "G2_Wilson_fail": sum(1 for r in rows if not r["gates"]["G2_Wilson"]),
            "G3_EV_fail": sum(1 for r in rows if not r["gates"]["G3_EV"]),
            "G4_Bonf_BH_fail": sum(1 for r in rows if not r["gates"]["G4_Bonf_BH"]),
            "G5_PF_fail": sum(1 for r in rows if not r["gates"]["G5_PF"]),
            "G6_Kelly_fail": sum(1 for r in rows if not r["gates"]["G6_Kelly"]),
            "G7_WF_fail": sum(1 for r in rows if not r["gates"]["G7_WF"]),
        }

    lines = ["# Null Summary", "", f"Generated: {generated_at}", ""]
    for name, rows in (("Family A", rows_a), ("Family B", rows_b)):
        lines.append(f"## {name}")
        lines.append(f"- cells: {len(rows)}")
        lines.append(f"- N<30 cells: {sum(1 for r in rows if r['n'] < 30)}")
        for key, value in fail_counts(rows).items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    n_short = [r for r in rows_a if r["n"] < 30]
    if n_short:
        lines.append("## Family A N不足 Cell")
        for row in n_short:
            lines.append(f"- K={row['K']:g} H={row['H_bar']} session={row['session']} N={row['n']}")
    else:
        lines.append("## Family A N不足 Cell\n- none")
    return "\n".join(lines) + "\n"


def build_ablation(rows_a: list[dict], rows_b: list[dict], generated_at: str) -> str:
    b_by_key = {(r["K"], r["H_bar"], r["session"]): r for r in rows_b}
    lines = [
        "# Family A vs v_reversal Ablation",
        "",
        f"Generated: {generated_at}",
        "",
        "## Design Diff",
        "| Item | Family A Pure Vol Exhaustion Fade | Family B v_reversal current |",
        "|---|---|---|",
        "| Entry trigger | `body_t >= K * SMA20_prior(abs(body))` on the closed M5 bar | 10-bar pip drop/surge plus RSI, BB%B, Stoch, candle color, body-ratio, and Stoch recovery/rejection |",
        "| K grid usage | Active body-exhaustion threshold | Inert label for one-to-one grid comparison; current v_reversal has no body/SMA K parameter |",
        "| Direction | Fade the signal bar body | Reversal after 10-bar down/up move with confirming reversal candle |",
        "| Exit | TP 1.0*ATR14, SL 1.5*ATR14, H-bar time stop | v_reversal TP 1.5*ATR7, SL 0.7*ATR7 plus recent high/low guard, H-bar time stop for cell comparability |",
        "| Filters | Session only; no MA trend filter | RSI/BB%B/Stoch/MACD score internals; confidence ADX penalty is not part of this vector BT PnL |",
        "",
        "## Per-cell Comparison",
        "| K | H | Session | A N | A EV | A PF | A Verdict | B N | B EV | B PF | B Verdict |",
        "|---:|---:|---|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for row in sorted(rows_a, key=lambda r: (r["K"], r["H_bar"], r["session"])):
        b = b_by_key[(row["K"], row["H_bar"], row["session"])]
        lines.append(
            f"| {row['K']:g} | {row['H_bar']} | {row['session']} | "
            f"{row['n']} | {fmt(row['ev_pip'], 2)} | {fmt(row['pf'], 2)} | {row['verdict']} | "
            f"{b['n']} | {fmt(b['ev_pip'], 2)} | {fmt(b['pf'], 2)} | {b['verdict']} |"
        )
    return "\n".join(lines) + "\n"


def append_result_section(path: Path, rows_a: list[dict], rows_b: list[dict], generated_at: str) -> None:
    ref_rows = rows_a or rows_b
    period_start = ref_rows[0]["period_start"] if ref_rows else "unknown"
    period_end = ref_rows[0]["period_end"] if ref_rows else "unknown"
    caveat = ""
    if ref_rows and pd.Timestamp(period_end) < pd.Timestamp(DEFAULT_END_DATE, tz="UTC"):
        caveat = f"Data caveat: local MASSIVE cache ends before target {DEFAULT_END_DATE}; backfill/rerun required for exact target-window evidence."
    shadow = [r for r in rows_a if r["verdict"] == "SHADOW_CANDIDATE"]
    needs = [r for r in rows_a if r["verdict"] == "NEEDS_MORE_EVIDENCE"]
    reject = [r for r in rows_a if r["verdict"] == "REJECT"]
    top = sorted(rows_a, key=lambda r: (r["verdict"] == "SHADOW_CANDIDATE", r["ev_pip"], r["pf"]), reverse=True)[:3]
    result = [
        "",
        "<!-- vol_exhaustion_fade_bt_result -->",
        "## Result: Vol Exhaustion Fade BT",
        "",
        f"Generated: {generated_at}",
        f"Data period: {period_start} .. {period_end}",
        caveat,
        f"投入 cell 数: {len(rows_a)}",
        f"SHADOW_CANDIDATE: {len(shadow)}",
        f"NEEDS_MORE_EVIDENCE: {len(needs)}",
        f"REJECT: {len(reject)}",
        "",
        "Top 3 cell:",
    ]
    for row in top:
        result.append(
            f"- K={row['K']:g}, H={row['H_bar']}, session={row['session']}, "
            f"N={row['n']}, WR={fmt(row['wr'], 3)}, Wilson_lo={fmt(row['wilson_lo'], 3)}, "
            f"EV={fmt(row['ev_pip'], 2)}, PF={fmt(row['pf'], 2)}, p_BH={fmt(row['p_bh'], 6)}"
        )
    result.extend(
        [
            "",
            "Ablation major diff: Family A uses body/SMA20 exhaustion fade; current v_reversal uses 10-bar pip shock plus RSI/BB%B/Stoch reversal confirmation. Family B has no native K parameter, so K is retained only as a grid label.",
            "Next task: Phase B cross-pair OOS and cooldown sweep without adding MA trend filters.",
            "",
        ]
    )
    existing = path.read_text(encoding="utf-8") if path.exists() else "# final.md\n"
    marker = "<!-- vol_exhaustion_fade_bt_result -->"
    if marker in existing:
        existing = existing.split(marker)[0].rstrip() + "\n"
    path.write_text(existing + "\n".join(result), encoding="utf-8")


def write_shadow_strategy(path: Path, best: dict) -> None:
    text = f'''"""Vol Exhaustion Fade shadow candidate.

Generated only because the pre-registered USD_JPY M5 grid produced at least
one SHADOW_CANDIDATE. Human review is still required before live DB routing.
"""
from __future__ import annotations

from strategies.base import Candidate, StrategyBase


class VolExhaustionFade(StrategyBase):
    name = "vol_exhaustion_fade"
    mode = "scalp"
    enabled = False
    strategy_type = "MR"

    k = {best["K"]!r}
    horizon_bars = {best["H_bar"]!r}
    tp_atr_mult = 1.0
    sl_atr_mult = 1.5
    cooldown_bars = 3

    def evaluate(self, ctx):
        if ctx.df is None or len(ctx.df) < 22:
            return None
        df = ctx.df
        row = df.iloc[-1]
        bodies = (df["Close"] - df["Open"]).abs()
        sma20 = float(bodies.iloc[-21:-1].mean())
        if sma20 <= 0:
            return None
        body = abs(float(row["Close"]) - float(row["Open"]))
        if body < self.k * sma20 or float(row["Close"]) == float(row["Open"]):
            return None
        atr = float(row.get("atr", ctx.atr))
        if atr <= 0:
            return None
        signal = "SELL" if float(row["Close"]) > float(row["Open"]) else "BUY"
        entry = float(row["Close"])
        if signal == "BUY":
            tp = entry + atr * self.tp_atr_mult
            sl = entry - atr * self.sl_atr_mult
        else:
            tp = entry - atr * self.tp_atr_mult
            sl = entry + atr * self.sl_atr_mult
        return Candidate(
            signal=signal,
            confidence=55,
            sl=sl,
            tp=tp,
            reasons=[f"vol exhaustion fade: body/SMA20={{body / sma20:.2f}} >= K={{self.k}}"],
            entry_type=self.name,
            score=3.0,
            max_hold_bars=self.horizon_bars,
        )
'''
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default=str(ROOT / "data" / "cache" / "massive"))
    parser.add_argument("--out-dir", default=str(ROOT / "reports" / "vol_exhaustion_fade_bt"))
    parser.add_argument("--family", choices=["A", "B", "both"], default="both")
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generated_at = datetime.now(timezone.utc).isoformat()
    df_raw, source_path = load_usdjpy_m5(Path(args.cache_dir), args.end_date)
    rows_a: list[dict] = []
    rows_b: list[dict] = []
    trades_a: dict[str, list[Trade]] = {}
    trades_b: dict[str, list[Trade]] = {}
    if args.family in {"A", "both"}:
        df_a = add_family_a_columns(df_raw)
        rows_a, trades_a = compute_family_grid(df_a, source_path, FAMILY_A, generated_at)
    if args.family in {"B", "both"}:
        df_b = add_family_b_columns(df_raw)
        rows_b, trades_b = compute_family_grid(df_b, source_path, FAMILY_B, generated_at)
    write_reports(Path(args.out_dir), rows_a, rows_b, trades_a, generated_at)
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
