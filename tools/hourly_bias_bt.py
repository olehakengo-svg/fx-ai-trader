#!/usr/bin/env python3
"""USD/JPY M5 hour x weekday directional bias backtest.

Family A is the pre-registered pure hourly directional grid:
UTC hour x weekday x side = 24 x 5 x 2 = 240 cells.

Family B is an ablation of the current london_breakout and
session_vol_expansion strategies, called read-only through their evaluate()
methods and summarized by signal hour x weekday.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")
sys.modules.setdefault("pytest", object())

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from strategies.context import SignalContext  # noqa: E402
from strategies.scalp.london_breakout import LondonBreakout  # noqa: E402
from strategies.scalp.session_vol_expansion import SessionVolExpansion  # noqa: E402


PAIR = "USD_JPY"
SYMBOL = "USDJPY=X"
TF = "M5"
PIP_SIZE = 0.01
PIP_MULT = 100
SPREAD_PIP = 1.3
PRE_REG_M = 240
ALPHA = 0.05 / PRE_REG_M
FDR_Q = 0.05
REPORT_DIR = ROOT / "reports" / "hourly_bias_bt"
DATA_CANDIDATES = (
    ROOT / "data" / "cache" / "massive" / "USD_JPY_M5.parquet",
    ROOT / "data" / "cache" / "massive" / "USD_JPY_5m.parquet",
)
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri")
SIDES = ("long", "short")
ABLATION_STRATEGIES = ("london_breakout", "session_vol_expansion")


@dataclass(frozen=True)
class Cell:
    hour: int
    weekday: int
    side: str

    @property
    def weekday_name(self) -> str:
        return WEEKDAYS[self.weekday]

    @property
    def id(self) -> str:
        return f"h{self.hour:02d}_{self.weekday_name}_{self.side}"


def load_frame(path: Path | None = None) -> tuple[pd.DataFrame, Path]:
    source = path
    if source is None:
        source = next((p for p in DATA_CANDIDATES if p.exists()), None)
    if source is None or not source.exists():
        tried = ", ".join(str(p.relative_to(ROOT)) for p in DATA_CANDIDATES)
        raise FileNotFoundError(f"missing MASSIVE parquet cache; tried {tried}")

    df = pd.read_parquet(source).copy()
    df.columns = [str(c).lower() for c in df.columns]
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    required = {"Open", "High", "Low", "Close"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{source} missing OHLC columns: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex):
        for candidate in ("time", "timestamp", "datetime", "date"):
            if candidate in df.columns:
                df.index = pd.to_datetime(df[candidate], utc=True)
                break
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{source} must have a DatetimeIndex or timestamp column")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    cols = ["Open", "High", "Low", "Close"] + (["Volume"] if "Volume" in df.columns else [])
    return df[cols].astype(float).sort_index().dropna(subset=["Open", "High", "Low", "Close"]), source


def rsi_wilder(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50.0)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    high = out["High"]
    low = out["Low"]
    close = out["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    out["atr"] = tr.rolling(14, min_periods=14).mean()
    out["atr7"] = tr.rolling(7, min_periods=7).mean()
    out["ema9"] = close.ewm(span=9, adjust=False).mean()
    out["ema21"] = close.ewm(span=21, adjust=False).mean()
    out["ema50"] = close.ewm(span=50, adjust=False).mean()
    out["ema200"] = close.ewm(span=200, adjust=False).mean()
    out["rsi"] = rsi_wilder(close, 14)
    out["rsi5"] = rsi_wilder(close, 5)
    out["rsi9"] = rsi_wilder(close, 9)
    low14 = low.rolling(14, min_periods=14).min()
    high14 = high.rolling(14, min_periods=14).max()
    out["stoch_k"] = ((close - low14) / (high14 - low14).replace(0, np.nan) * 100).fillna(50.0)
    out["stoch_d"] = out["stoch_k"].rolling(3, min_periods=1).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    out["macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    mid = close.rolling(20, min_periods=20).mean()
    sd = close.rolling(20, min_periods=20).std(ddof=0)
    out["bb_mid"] = mid
    out["bb_upper"] = mid + 2.0 * sd
    out["bb_lower"] = mid - 2.0 * sd
    out["bb_pband"] = ((close - out["bb_lower"]) / (out["bb_upper"] - out["bb_lower"]).replace(0, np.nan)).fillna(0.5)
    out["bb_width"] = ((out["bb_upper"] - out["bb_lower"]) / close.replace(0, np.nan)).fillna(0.01)
    out["adx"] = 25.0
    out["adx_pos"] = 25.0
    out["adx_neg"] = 25.0
    return out


def iter_cells() -> Iterable[Cell]:
    for hour in range(24):
        for weekday in range(5):
            for side in SIDES:
                yield Cell(hour, weekday, side)


def hourly_trades(df: pd.DataFrame) -> list[dict]:
    tmp = df.copy()
    tmp["date"] = tmp.index.date
    tmp["hour"] = tmp.index.hour
    tmp["weekday"] = tmp.index.weekday
    rows: list[dict] = []
    for (date, hour), part in tmp.groupby(["date", "hour"], sort=True):
        if part.empty:
            continue
        weekday = int(part.index[0].weekday())
        if weekday >= 5:
            continue
        entry = float(part["Open"].iloc[0])
        exit_ = float(part["Close"].iloc[-1])
        rows.append(
            {
                "date": str(date),
                "hour": int(hour),
                "weekday": weekday,
                "entry_ts": part.index[0].isoformat(),
                "exit_ts": part.index[-1].isoformat(),
                "bar_count": int(len(part)),
                "entry": entry,
                "exit": exit_,
                "long_pip": (exit_ - entry) * PIP_MULT - SPREAD_PIP,
                "short_pip": (entry - exit_) * PIP_MULT - SPREAD_PIP,
                "gross_long_pip": (exit_ - entry) * PIP_MULT,
            }
        )
    return rows


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def binom_p_greater(wins: int, n: int) -> float:
    if n <= 0:
        return 1.0
    try:
        from scipy.stats import binomtest

        return float(binomtest(wins, n, p=0.5, alternative="greater").pvalue)
    except Exception:
        mean = 0.5 * n
        sd = math.sqrt(0.25 * n)
        z = (wins - 0.5 - mean) / sd
        return max(0.0, min(1.0, 0.5 * math.erfc(z / math.sqrt(2.0))))


def pf_from_pnls(pnls: np.ndarray) -> float:
    gp = float(pnls[pnls > 0].sum())
    gl = float(-pnls[pnls < 0].sum())
    if gl <= 0:
        return float("inf") if gp > 0 else 0.0
    return gp / gl


def kelly_from_pnls(pnls: np.ndarray) -> float:
    wins = pnls[pnls > 0]
    losses = -pnls[pnls < 0]
    if len(pnls) == 0 or len(wins) == 0 or len(losses) == 0:
        return 0.0
    wr = len(wins) / len(pnls)
    b = float(wins.mean() / losses.mean())
    return float(wr - (1.0 - wr) / b) if b > 0 else 0.0


def stats_for_pnls(cell_id: str, pnls: Iterable[float], extra: dict | None = None) -> dict:
    arr = np.asarray(list(pnls), dtype=float)
    n = int(len(arr))
    wins = int((arr > 0).sum()) if n else 0
    wr = wins / n if n else 0.0
    pf = pf_from_pnls(arr) if n else 0.0
    row = {
        "cell_id": cell_id,
        "n": n,
        "wins": wins,
        "losses_or_nonwins": n - wins,
        "wr": round(wr, 6),
        "wilson_lower": round(wilson_lower(wins, n), 6),
        "mean_pip": round(float(arr.mean()), 6) if n else 0.0,
        "median_pip": round(float(np.median(arr)), 6) if n else 0.0,
        "total_pip": round(float(arr.sum()), 4) if n else 0.0,
        "pf": round(pf, 6) if math.isfinite(pf) else "inf",
        "kelly": round(kelly_from_pnls(arr), 6) if n else 0.0,
        "p_value": binom_p_greater(wins, n),
    }
    if extra:
        row.update(extra)
    return row


def family_a_rows(trades: list[dict]) -> tuple[list[dict], dict[str, list[dict]]]:
    rows: list[dict] = []
    trade_map: dict[str, list[dict]] = {}
    for cell in iter_cells():
        key = "long_pip" if cell.side == "long" else "short_pip"
        selected = [t for t in trades if t["hour"] == cell.hour and t["weekday"] == cell.weekday]
        pnls = [float(t[key]) for t in selected]
        row = stats_for_pnls(
            cell.id,
            pnls,
            {
                "hour": cell.hour,
                "weekday": cell.weekday,
                "weekday_name": cell.weekday_name,
                "side": cell.side,
            },
        )
        rows.append(row)
        trade_map[cell.id] = [
            {
                "date": t["date"],
                "entry_ts": t["entry_ts"],
                "exit_ts": t["exit_ts"],
                "bar_count": t["bar_count"],
                "net_pip": round(float(t[key]), 4),
                "gross_long_pip": round(float(t["gross_long_pip"]), 4),
            }
            for t in selected
        ]
    return rows, trade_map


def bh_fdr(rows: list[dict]) -> None:
    ordered = sorted(rows, key=lambda r: r["p_value"])
    m = len(ordered)
    prev = 1.0
    adjusted = [1.0] * m
    for pos in range(m, 0, -1):
        raw = ordered[pos - 1]["p_value"] * m / pos
        prev = min(prev, raw)
        adjusted[pos - 1] = min(prev, 1.0)
    for row, q in zip(ordered, adjusted):
        row["bh_fdr_p"] = float(q)
        row["bonferroni_alpha"] = ALPHA


def wf_3fold_for_cell(trades: list[dict], row: dict) -> list[dict]:
    selected = [t for t in trades if t["hour"] == row["hour"] and t["weekday"] == row["weekday"]]
    folds: list[dict] = []
    key = "long_pip" if row["side"] == "long" else "short_pip"
    for fold_no, fold in enumerate(np.array_split(np.array(selected, dtype=object), 3), start=1):
        fold_list = [x.item() if hasattr(x, "item") else x for x in fold]
        stat = stats_for_pnls(row["cell_id"], [float(t[key]) for t in fold_list])
        folds.append(
            {
                "fold": fold_no,
                "period_start": fold_list[0]["entry_ts"] if fold_list else None,
                "period_end": fold_list[-1]["exit_ts"] if fold_list else None,
                "n": stat["n"],
                "wr": stat["wr"],
                "mean_pip": stat["mean_pip"],
                "pf": stat["pf"],
                "kelly": stat["kelly"],
            }
        )
    return folds


def add_verdicts(rows: list[dict], wf_map: dict[str, list[dict]]) -> None:
    by_hour_wd_side = {(r["hour"], r["weekday"], r["side"]): r for r in rows}
    for row in rows:
        peer_side = "short" if row["side"] == "long" else "long"
        peer = by_hour_wd_side.get((row["hour"], row["weekday"], peer_side))
        if peer is None:
            g8 = "missing_peer"
        elif row["mean_pip"] == 0 or peer["mean_pip"] == 0:
            g8 = "zero_ev"
        elif (row["mean_pip"] > 0) == (peer["mean_pip"] > 0):
            g8 = "sign_same"
        else:
            g8 = "sign_opposite"
        pf = float("inf") if row["pf"] == "inf" else float(row["pf"])
        gates = {
            "G1_n_ge_100": row["n"] >= 100,
            "G2_wilson_lower_ge_0p55": row["wilson_lower"] >= 0.55,
            "G3_ev_pip_gt_0p5": row["mean_pip"] > 0.5,
            "G4_bh_fdr_p_lt_0p000208": row.get("bh_fdr_p", 1.0) < ALPHA,
            "G5_pf_ge_1p30": pf >= 1.30,
            "G6_kelly_ge_0p08": row["kelly"] >= 0.08,
            "G7_wf_all_folds_ev_gt_0": all(f["mean_pip"] > 0 for f in wf_map.get(row["cell_id"], [])),
            "G8_long_short_sign": g8,
        }
        if all(gates[k] for k in ("G1_n_ge_100", "G2_wilson_lower_ge_0p55", "G3_ev_pip_gt_0p5", "G4_bh_fdr_p_lt_0p000208", "G5_pf_ge_1p30", "G6_kelly_ge_0p08", "G7_wf_all_folds_ev_gt_0")):
            verdict = "SHADOW_CANDIDATE"
        elif gates["G1_n_ge_100"] and gates["G2_wilson_lower_ge_0p55"] and gates["G3_ev_pip_gt_0p5"] and (not gates["G4_bh_fdr_p_lt_0p000208"]) and g8 == "sign_same":
            verdict = "DRIFT_LED_NULL"
        else:
            verdict = "REJECT"
        row["gates"] = gates
        row["verdict"] = verdict


def _ctx_for_row(df: pd.DataFrame, i: int) -> SignalContext:
    row = df.iloc[i]
    prev = df.iloc[i - 1] if i > 0 else row
    entry = float(row["Close"])
    atr = float(row.get("atr", 0.0) or 0.0)
    ts = df.index[i]
    return SignalContext(
        entry=entry,
        open_price=float(row["Open"]),
        atr=atr,
        atr7=float(row.get("atr7", atr) or atr),
        ema9=float(row.get("ema9", entry)),
        ema21=float(row.get("ema21", entry)),
        ema50=float(row.get("ema50", entry)),
        ema200=float(row.get("ema200", entry)),
        ema9_prev=float(prev.get("ema9", entry)),
        ema21_prev=float(prev.get("ema21", entry)),
        rsi=float(row.get("rsi", 50.0)),
        rsi5=float(row.get("rsi5", 50.0)),
        rsi9=float(row.get("rsi9", 50.0)),
        stoch_k=float(row.get("stoch_k", 50.0)),
        stoch_d=float(row.get("stoch_d", 50.0)),
        adx=float(row.get("adx", 25.0)),
        adx_pos=float(row.get("adx_pos", 25.0)),
        adx_neg=float(row.get("adx_neg", 25.0)),
        macdh=float(row.get("macd_hist", 0.0)),
        macdh_prev=float(prev.get("macd_hist", 0.0)),
        macdh_prev2=float(df.iloc[i - 2].get("macd_hist", 0.0)) if i >= 2 else 0.0,
        bbpb=float(row.get("bb_pband", 0.5)),
        bb_upper=float(row.get("bb_upper", entry + atr)),
        bb_mid=float(row.get("bb_mid", entry)),
        bb_lower=float(row.get("bb_lower", entry - atr)),
        bb_width=float(row.get("bb_width", 0.01)),
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        htf={"agreement": "bull" if row.get("ema9", entry) > row.get("ema21", entry) else "bear"},
        session={"spread_pip": SPREAD_PIP},
        symbol=SYMBOL,
        tf="5m",
        is_jpy=True,
        pip_mult=PIP_MULT,
        df=df.iloc[max(0, i - 500): i + 1],
        backtest_mode=True,
        bar_time=ts,
        hour_utc=ts.hour,
    )


def _strategy_object(name: str):
    if name == "london_breakout":
        return LondonBreakout()
    if name == "session_vol_expansion":
        SessionVolExpansion.reset_dedup_state()
        return SessionVolExpansion()
    raise ValueError(f"unknown strategy {name}")


def strategy_signal_trades(df: pd.DataFrame, strategy_name: str) -> list[dict]:
    strategy = _strategy_object(strategy_name)
    min_i = 500 if strategy_name in {"london_breakout", "session_vol_expansion"} else 220
    default_hold = 12 if strategy_name == "london_breakout" else int(getattr(strategy, "max_hold_bars", 30))
    trades: list[dict] = []
    last_exit = -1
    for i in range(min_i, len(df) - 2):
        if i <= last_exit:
            continue
        ts = df.index[i]
        if ts.weekday() >= 5:
            continue
        ctx = _ctx_for_row(df, i)
        cand = strategy.evaluate(ctx)
        if cand is None:
            continue
        side = "long" if cand.signal == "BUY" else "short"
        entry = float(df["Close"].iloc[i])
        tp = float(cand.tp)
        sl = float(cand.sl)
        if not all(math.isfinite(x) for x in (entry, tp, sl)) or tp == sl:
            continue
        end_i = min(i + default_hold, len(df) - 1)
        exit_i = end_i
        exit_price = float(df["Close"].iloc[end_i])
        outcome = "TIME"
        for j in range(i + 1, end_i + 1):
            high = float(df["High"].iloc[j])
            low = float(df["Low"].iloc[j])
            if side == "long":
                if low <= sl:
                    exit_i, exit_price, outcome = j, sl, "SL"
                    break
                if high >= tp:
                    exit_i, exit_price, outcome = j, tp, "TP"
                    break
            else:
                if high >= sl:
                    exit_i, exit_price, outcome = j, sl, "SL"
                    break
                if low <= tp:
                    exit_i, exit_price, outcome = j, tp, "TP"
                    break
        gross = (exit_price - entry) * PIP_MULT if side == "long" else (entry - exit_price) * PIP_MULT
        trades.append(
            {
                "strategy": strategy_name,
                "entry_ts": ts.isoformat(),
                "exit_ts": df.index[exit_i].isoformat(),
                "hour": int(ts.hour),
                "weekday": int(ts.weekday()),
                "weekday_name": WEEKDAYS[int(ts.weekday())],
                "side": side,
                "signal": cand.signal,
                "entry": round(entry, 5),
                "tp": round(tp, 5),
                "sl": round(sl, 5),
                "exit": round(exit_price, 5),
                "outcome": outcome,
                "net_pip": round(gross - SPREAD_PIP, 4),
                "hold_bars": int(exit_i - i),
            }
        )
        last_exit = exit_i
    return trades


def family_b_rows(df: pd.DataFrame) -> tuple[list[dict], dict[str, list[dict]]]:
    rows: list[dict] = []
    trade_map: dict[str, list[dict]] = {}
    for strategy_name in ABLATION_STRATEGIES:
        trades = strategy_signal_trades(df, strategy_name)
        for hour in range(24):
            for weekday in range(5):
                selected = [t for t in trades if t["hour"] == hour and t["weekday"] == weekday]
                cell_id = f"{strategy_name}_h{hour:02d}_{WEEKDAYS[weekday]}"
                row = stats_for_pnls(
                    cell_id,
                    [float(t["net_pip"]) for t in selected],
                    {
                        "strategy": strategy_name,
                        "hour": hour,
                        "weekday": weekday,
                        "weekday_name": WEEKDAYS[weekday],
                    },
                )
                rows.append(row)
                trade_map[cell_id] = selected[:100]
    return rows, trade_map


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def fmt_pf(value) -> str:
    return "inf" if value == "inf" else f"{float(value):.3f}"


def render_summary(rows: list[dict], meta: dict) -> str:
    top = sorted(rows, key=lambda r: (r["verdict"] != "SHADOW_CANDIDATE", -r["mean_pip"], -r["n"]))[:20]
    survivors = [r for r in rows if r["verdict"] == "SHADOW_CANDIDATE"]
    drift_nulls = [r for r in rows if r["verdict"] == "DRIFT_LED_NULL"]
    lines = [
        "# Hourly Bias BT Summary",
        "",
        f"- generated_at: {meta['generated_at']}",
        f"- data_source: `{meta['data_source']}`",
        f"- period: {meta['period_start']} to {meta['period_end']}",
        f"- bars: {meta['bars']:,}",
        f"- pair/tf: {PAIR} {TF}",
        f"- grid: 24 hour x 5 weekday x 2 side = {PRE_REG_M} cells",
        f"- spread_pip_round_trip: {SPREAD_PIP}",
        f"- bonferroni_alpha_240: {ALPHA:.9f}",
        f"- fdr_q: {FDR_Q}",
        f"- survivors: {len(survivors)}",
        f"- drift_led_null: {len(drift_nulls)}",
        "",
        "## Top Cells",
        "",
        "| verdict | hour | weekday | side | N | WR | Wilson_lo | EV pip | PF | Kelly | BH-FDR | G8 |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in top:
        lines.append(
            f"| {r['verdict']} | {r['hour']:02d} | {r['weekday_name']} | {r['side']} | "
            f"{r['n']} | {r['wr']:.3f} | {r['wilson_lower']:.3f} | {r['mean_pip']:.3f} | "
            f"{fmt_pf(r['pf'])} | {r['kelly']:.3f} | {r.get('bh_fdr_p', 1):.6g} | "
            f"{r['gates']['G8_long_short_sign']} |"
        )
    lines += ["", "## Survivor Cell IDs", ""]
    lines += [f"- `{r['cell_id']}`" for r in survivors] if survivors else ["- none"]
    return "\n".join(lines) + "\n"


def render_null_summary(rows: list[dict]) -> str:
    lines = [
        "# Hourly Bias Null Summary",
        "",
        f"- rejected_cells: {sum(1 for r in rows if r['verdict'] == 'REJECT')}",
        f"- drift_led_null_cells: {sum(1 for r in rows if r['verdict'] == 'DRIFT_LED_NULL')}",
        "",
        "## Gate Fail Counts",
        "",
    ]
    gate_names = [k for k in rows[0]["gates"].keys() if k != "G8_long_short_sign"] if rows else []
    for gate in gate_names:
        lines.append(f"- {gate}: {sum(1 for r in rows if not r['gates'][gate])}")
    return "\n".join(lines) + "\n"


def render_heatmap(rows: list[dict]) -> str:
    lines = ["# Hour x Weekday PF Heatmap", ""]
    for side in SIDES:
        lines += [
            f"## {side.title()} PF",
            "",
            "| hour | Mon | Tue | Wed | Thu | Fri |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
        by = {(r["hour"], r["weekday"], r["side"]): r for r in rows}
        for hour in range(24):
            vals = []
            for weekday in range(5):
                r = by[(hour, weekday, side)]
                vals.append(fmt_pf(r["pf"]))
            lines.append(f"| {hour:02d} | " + " | ".join(vals) + " |")
        lines.append("")
    return "\n".join(lines)


def render_ablation(a_rows: list[dict], b_rows: list[dict]) -> str:
    a_by = {(r["hour"], r["weekday"]): r for r in a_rows if r["side"] == "long"}
    lines = [
        "# Hourly Bias Ablation",
        "",
        "Family B calls current `london_breakout.py` and `session_vol_expansion.py`",
        "through their `evaluate()` methods without editing those files. Signals are",
        "bucketed by UTC entry hour x weekday and simulated against the emitted TP/SL",
        "with a time stop: 12 M5 bars for london_breakout, strategy max_hold_bars for",
        "session_vol_expansion.",
        "",
        "The `A_long_EV` column is the naive same-hour long baseline for the same",
        "hour x weekday cohort.",
        "",
        "| strategy | hour | weekday | N | WR | EV pip | PF | Kelly | A_long_EV |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(b_rows, key=lambda x: (x["strategy"], -x["mean_pip"], -x["n"]))[:80]:
        base = a_by.get((r["hour"], r["weekday"]))
        lines.append(
            f"| {r['strategy']} | {r['hour']:02d} | {r['weekday_name']} | {r['n']} | "
            f"{r['wr']:.3f} | {r['mean_pip']:.3f} | {fmt_pf(r['pf'])} | {r['kelly']:.3f} | "
            f"{base['mean_pip'] if base else 0.0:.3f} |"
        )
    return "\n".join(lines) + "\n"


def shadow_strategy_text(row: dict) -> str:
    side = "BUY" if row["side"] == "long" else "SELL"
    class_name = f"HourlyBiasH{row['hour']:02d}{row['weekday_name']}{row['side'].title()}"
    return f'''"""Generated hourly bias shadow candidate for {row["cell_id"]}."""
from strategies.base import StrategyBase, Candidate


class {class_name}(StrategyBase):
    name = "hourly_bias_{row["hour"]:02d}_{row["weekday_name"].lower()}_{row["side"]}"
    mode = "scalp"
    hour_utc = {row["hour"]}
    weekday = {row["weekday"]}
    side = "{row["side"]}"

    def evaluate(self, ctx):
        if ctx.bar_time is None or ctx.bar_time.weekday() != self.weekday:
            return None
        if ctx.hour_utc != self.hour_utc:
            return None
        atr = ctx.atr7 if ctx.atr7 > 0 else ctx.atr
        if atr <= 0:
            return None
        if self.side == "long":
            sl = ctx.entry - atr
            tp = ctx.entry + atr
        else:
            sl = ctx.entry + atr
            tp = ctx.entry - atr
        return Candidate(
            signal="{side}",
            confidence=50,
            sl=sl,
            tp=tp,
            reasons=["hourly_bias shadow candidate: {row["cell_id"]}"],
            entry_type=self.name,
            score=1.0,
            max_hold_bars=12,
        )
'''


def write_shadow_candidates(rows: list[dict]) -> list[Path]:
    written: list[Path] = []
    for row in rows:
        if row["verdict"] != "SHADOW_CANDIDATE":
            continue
        path = ROOT / "strategies" / "scalp" / f"hourly_bias_{row['hour']:02d}_{row['weekday_name'].lower()}_{row['side']}.py"
        path.write_text(shadow_strategy_text(row), encoding="utf-8")
        written.append(path)
    return written


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def run_backtest(data_path: Path | None = None, report_dir: Path = REPORT_DIR, write_strategies: bool = True) -> dict:
    df_raw, source = load_frame(data_path)
    df = add_indicators(df_raw)
    generated_at = datetime.now(timezone.utc).isoformat()
    meta = {
        "generated_at": generated_at,
        "data_source": _rel(source),
        "period_start": df.index[0].isoformat(),
        "period_end": df.index[-1].isoformat(),
        "bars": int(len(df)),
        "pair": PAIR,
        "tf": TF,
    }

    h_trades = hourly_trades(df)
    a_rows, a_trade_map = family_a_rows(h_trades)
    bh_fdr(a_rows)
    wf_map: dict[str, list[dict]] = {}
    for row in a_rows:
        wf = wf_3fold_for_cell(h_trades, row)
        wf_map[row["cell_id"]] = wf
    add_verdicts(a_rows, wf_map)

    b_rows, b_trade_map = family_b_rows(df)
    report_dir.mkdir(parents=True, exist_ok=True)
    for row in a_rows:
        write_json(report_dir / "per_cell" / f"{row['cell_id']}.json", {"meta": meta, "stats": row, "trades": a_trade_map[row["cell_id"]]})
        write_json(report_dir / "wf_3fold" / f"{row['cell_id']}.json", {"meta": meta, "cell_id": row["cell_id"], "folds": wf_map[row["cell_id"]]})
    write_json(report_dir / "all_cells.json", {"meta": meta, "family_a": a_rows, "family_b": b_rows})
    write_json(report_dir / "ablation_trades_sample.json", {"meta": meta, "samples": b_trade_map})
    (report_dir / "summary.md").write_text(render_summary(a_rows, meta), encoding="utf-8")
    (report_dir / "null_summary.md").write_text(render_null_summary(a_rows), encoding="utf-8")
    (report_dir / "heatmap_hour_x_weekday.md").write_text(render_heatmap(a_rows), encoding="utf-8")
    (report_dir / "ablation.md").write_text(render_ablation(a_rows, b_rows), encoding="utf-8")
    written = write_shadow_candidates(a_rows) if write_strategies else []
    return {"meta": meta, "family_a": a_rows, "family_b": b_rows, "shadow_strategy_files": [_rel(p) for p in written]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--no-write-strategies", action="store_true")
    args = parser.parse_args()
    result = run_backtest(args.data, args.report_dir, write_strategies=not args.no_write_strategies)
    survivors = [r for r in result["family_a"] if r["verdict"] == "SHADOW_CANDIDATE"]
    print(json.dumps({"report_dir": str(args.report_dir), "survivors": len(survivors), "shadow_strategy_files": result["shadow_strategy_files"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
