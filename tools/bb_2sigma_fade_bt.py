#!/usr/bin/env python3
"""USD/JPY M5 Bollinger 2-sigma fade long/short asymmetry backtest.

Family A is intentionally minimal: close outside BB + RSI14 extreme, then fade
to BB mid or +1 ATR, with 1.5 ATR stop, H-bar time stop, and fixed spread.
Family B reuses the current BBRsiReversion strategy as an ablation baseline
without editing that strategy file.
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
from scipy.stats import binomtest

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")
sys.modules.setdefault("pytest", object())

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from strategies.context import SignalContext  # noqa: E402
from strategies.scalp.bb_rsi import BBRsiReversion  # noqa: E402


PAIR = "USD_JPY"
TF = "M5"
PIP_SIZE = 0.01
SPREAD_PIP = 1.3
COOLDOWN_BARS = 3
ALPHA = 0.05 / 64
REPORT_DIR = ROOT / "reports" / "bb_2sigma_fade_bt"
DATA_CANDIDATES = (
    ROOT / "data" / "cache" / "massive" / "USD_JPY_M5.parquet",
    ROOT / "data" / "cache" / "massive" / "USD_JPY_5m.parquet",
)

BB_LENGTHS = (20, 30)
BB_MULTS = (2.0, 2.5)
RSI_THRESHOLDS = (25, 30)
H_BARS = (6, 12)
SESSIONS = ("ALL", "LONDON_07-14_UTC")
SIDES = ("long", "short")


@dataclass(frozen=True)
class Cell:
    family: str
    side: str
    bb_len: int
    bb_mult: float
    rsi_threshold: int
    h_bar: int
    session: str

    @property
    def id(self) -> str:
        mult = str(self.bb_mult).replace(".", "p")
        return (
            f"{self.family}_{self.side}_L{self.bb_len}_M{mult}_"
            f"R{self.rsi_threshold}_H{self.h_bar}_{self.session}"
        )


def load_frame(path: Path | None = None) -> tuple[pd.DataFrame, Path]:
    source = path
    if source is None:
        source = next((p for p in DATA_CANDIDATES if p.exists()), None)
    if source is None or not source.exists():
        tried = ", ".join(str(p.relative_to(ROOT)) for p in DATA_CANDIDATES)
        raise FileNotFoundError(f"missing MASSIVE parquet cache; tried {tried}")

    df = pd.read_parquet(source).copy()
    df.columns = [str(c).lower() for c in df.columns]
    rename = {"open": "Open", "high": "High", "low": "Low", "close": "Close"}
    df = df.rename(columns=rename)
    required = {"Open", "High", "Low", "Close"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{source} missing columns: {missing}")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(f"{source} must have a DatetimeIndex")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df.sort_index(), source


def rsi_wilder(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def add_indicators(df: pd.DataFrame, bb_lengths: Iterable[int] = BB_LENGTHS) -> pd.DataFrame:
    out = df.copy()
    high = out["High"]
    low = out["Low"]
    close = out["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    out["atr14"] = tr.rolling(14, min_periods=14).mean()
    out["rsi14"] = rsi_wilder(close, 14)
    out["rsi5"] = rsi_wilder(close, 5)

    low14 = low.rolling(14, min_periods=14).min()
    high14 = high.rolling(14, min_periods=14).max()
    out["stoch_k"] = ((close - low14) / (high14 - low14).replace(0, np.nan) * 100).fillna(50)
    out["stoch_d"] = out["stoch_k"].rolling(3, min_periods=1).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    out["macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    out["adx"] = 25.0
    out["adx_pos"] = 25.0
    out["adx_neg"] = 25.0

    for length in bb_lengths:
        mid = close.rolling(length, min_periods=length).mean()
        sd = close.rolling(length, min_periods=length).std(ddof=0)
        out[f"bb_mid_{length}"] = mid
        for mult in BB_MULTS:
            key = str(mult).replace(".", "p")
            upper = mid + sd * mult
            lower = mid - sd * mult
            out[f"bb_upper_{length}_{key}"] = upper
            out[f"bb_lower_{length}_{key}"] = lower
            out[f"bb_pband_{length}_{key}"] = (close - lower) / (upper - lower).replace(0, np.nan)
    return out


def _session_mask(index: pd.DatetimeIndex, session: str) -> np.ndarray:
    if session == "ALL":
        return np.ones(len(index), dtype=bool)
    if session == "LONDON_07-14_UTC":
        hour = index.hour
        return (hour >= 7) & (hour < 14)
    raise ValueError(f"unknown session: {session}")


def signal_indices_family_a(df: pd.DataFrame, cell: Cell) -> np.ndarray:
    key = str(cell.bb_mult).replace(".", "p")
    close = df["Close"]
    rsi = df["rsi14"]
    if cell.side == "long":
        sig = (close < df[f"bb_lower_{cell.bb_len}_{key}"]) & (rsi < cell.rsi_threshold)
    else:
        sig = (close > df[f"bb_upper_{cell.bb_len}_{key}"]) & (rsi > 100 - cell.rsi_threshold)
    sig = sig.fillna(False).to_numpy() & _session_mask(df.index, cell.session)
    return np.flatnonzero(sig)


def _ctx_for_row(df: pd.DataFrame, i: int, cell: Cell) -> SignalContext:
    row = df.iloc[i]
    prev = df.iloc[i - 1] if i > 0 else row
    key = str(cell.bb_mult).replace(".", "p")
    ts = df.index[i]
    bb_upper = float(row[f"bb_upper_{cell.bb_len}_{key}"])
    bb_lower = float(row[f"bb_lower_{cell.bb_len}_{key}"])
    bb_mid = float(row[f"bb_mid_{cell.bb_len}"])
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr14"]),
        atr7=float(row["atr14"]),
        rsi=float(row["rsi14"]),
        rsi5=float(row["rsi14"]),
        stoch_k=float(row["stoch_k"]),
        stoch_d=float(row["stoch_d"]),
        adx=float(row["adx"]),
        adx_pos=float(row["adx_pos"]),
        adx_neg=float(row["adx_neg"]),
        macdh=float(row["macd_hist"]),
        macdh_prev=float(df["macd_hist"].iloc[i - 1]) if i >= 1 else 0.0,
        macdh_prev2=float(df["macd_hist"].iloc[i - 2]) if i >= 2 else 0.0,
        bbpb=float(row[f"bb_pband_{cell.bb_len}_{key}"]),
        bb_upper=bb_upper,
        bb_mid=bb_mid,
        bb_lower=bb_lower,
        prev_close=float(prev["Close"]),
        prev_open=float(prev["Open"]),
        prev_high=float(prev["High"]),
        prev_low=float(prev["Low"]),
        symbol="USDJPY=X",
        tf="5m",
        is_jpy=True,
        pip_mult=100,
        df=df.iloc[max(0, i - 80): i + 1].rename(
            columns={"atr14": "atr", "rsi14": "rsi", f"bb_pband_{cell.bb_len}_{key}": "bb_pband"}
        ),
        regime={"regime": "RANGE"},
        backtest_mode=True,
        bar_time=ts,
        hour_utc=ts.hour,
    )


def signal_indices_family_b(df: pd.DataFrame, cell: Cell) -> np.ndarray:
    strategy = BBRsiReversion()
    strategy.bbpb_buy = 0.0
    strategy.bbpb_sell = 1.0
    strategy.rsi5_buy = cell.rsi_threshold
    strategy.rsi5_sell = 100 - cell.rsi_threshold
    raw = signal_indices_family_a(df, Cell("A", cell.side, cell.bb_len, cell.bb_mult, cell.rsi_threshold, cell.h_bar, cell.session))
    out: list[int] = []
    want = "BUY" if cell.side == "long" else "SELL"
    for i in raw:
        if i < max(cell.bb_len, 30):
            continue
        cand = strategy.evaluate(_ctx_for_row(df, int(i), cell))
        if cand is not None and cand.signal == want:
            out.append(int(i))
    return np.array(out, dtype=int)


def _target_prices(df: pd.DataFrame, i: int, cell: Cell) -> tuple[float, float]:
    row = df.iloc[i]
    entry = float(row["Close"])
    atr = float(row["atr14"])
    mid = float(row[f"bb_mid_{cell.bb_len}"])
    if cell.side == "long":
        tp = min(mid, entry + atr)
        sl = entry - 1.5 * atr
    else:
        tp = max(mid, entry - atr)
        sl = entry + 1.5 * atr
    return tp, sl


def _b_target_prices(df: pd.DataFrame, i: int, cell: Cell) -> tuple[float, float] | None:
    strategy = BBRsiReversion()
    strategy.bbpb_buy = 0.0
    strategy.bbpb_sell = 1.0
    strategy.rsi5_buy = cell.rsi_threshold
    strategy.rsi5_sell = 100 - cell.rsi_threshold
    cand = strategy.evaluate(_ctx_for_row(df, int(i), cell))
    if cand is None:
        return None
    return float(cand.tp), float(cand.sl)


def simulate_trades(df: pd.DataFrame, indices: Iterable[int], cell: Cell) -> list[dict]:
    trades: list[dict] = []
    last_blocked = -1
    for i in sorted(int(x) for x in indices):
        if i <= last_blocked or i >= len(df) - 1:
            continue
        atr = float(df["atr14"].iloc[i])
        if not math.isfinite(atr) or atr <= 0:
            continue

        if cell.family == "B":
            prices = _b_target_prices(df, i, cell)
            if prices is None:
                continue
            tp, sl = prices
        else:
            tp, sl = _target_prices(df, i, cell)

        entry = float(df["Close"].iloc[i])
        end_i = min(i + cell.h_bar, len(df) - 1)
        exit_i = end_i
        exit_price = float(df["Close"].iloc[end_i])
        outcome = "TIME"
        for j in range(i + 1, end_i + 1):
            high = float(df["High"].iloc[j])
            low = float(df["Low"].iloc[j])
            if cell.side == "long":
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

        gross = (exit_price - entry) / PIP_SIZE if cell.side == "long" else (entry - exit_price) / PIP_SIZE
        net = gross - SPREAD_PIP
        trades.append(
            {
                "entry_i": i,
                "exit_i": exit_i,
                "entry_ts": df.index[i].isoformat(),
                "exit_ts": df.index[exit_i].isoformat(),
                "side": cell.side,
                "entry": round(entry, 5),
                "tp": round(tp, 5),
                "sl": round(sl, 5),
                "exit": round(exit_price, 5),
                "outcome": outcome,
                "gross_pip": round(gross, 4),
                "net_pip": round(net, 4),
                "hold_bars": int(exit_i - i),
            }
        )
        last_blocked = exit_i + COOLDOWN_BARS
    return trades


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def pf_from_pnls(pnls: np.ndarray) -> float:
    gp = float(pnls[pnls > 0].sum())
    gl = float(-pnls[pnls < 0].sum())
    if gl <= 0:
        return float("inf") if gp > 0 else 0.0
    return gp / gl


def kelly_from_pnls(pnls: np.ndarray) -> float:
    wins = pnls[pnls > 0]
    losses = -pnls[pnls < 0]
    if len(wins) == 0 or len(losses) == 0:
        return 0.0
    wr = len(wins) / len(pnls)
    b = float(wins.mean() / losses.mean())
    return float((wr * b - (1 - wr)) / b) if b > 0 else 0.0


def stats_for_trades(cell: Cell, trades: list[dict]) -> dict:
    pnls = np.array([t["net_pip"] for t in trades], dtype=float)
    n = int(len(pnls))
    wins = int((pnls > 0).sum()) if n else 0
    wr = wins / n if n else 0.0
    pf = pf_from_pnls(pnls) if n else 0.0
    p_value = float(binomtest(wins, n, p=0.5, alternative="greater").pvalue) if n else 1.0
    return {
        "cell_id": cell.id,
        "family": cell.family,
        "side": cell.side,
        "bb_len": cell.bb_len,
        "bb_mult": cell.bb_mult,
        "rsi_threshold": cell.rsi_threshold,
        "h_bar": cell.h_bar,
        "session": cell.session,
        "n": n,
        "wins": wins,
        "losses_or_nonwins": n - wins,
        "wr": round(wr, 6),
        "wilson_lower": round(wilson_lower(wins, n), 6),
        "mean_pip": round(float(pnls.mean()), 6) if n else 0.0,
        "total_pip": round(float(pnls.sum()), 4) if n else 0.0,
        "pf": round(pf, 6) if math.isfinite(pf) else "inf",
        "kelly": round(kelly_from_pnls(pnls), 6) if n else 0.0,
        "p_value": p_value,
        "sample_trades": trades[:5],
    }


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


def wf_3fold(df: pd.DataFrame, cell: Cell) -> list[dict]:
    folds: list[dict] = []
    cuts = np.array_split(np.arange(len(df)), 3)
    for fold_no, idxs in enumerate(cuts, start=1):
        part = df.iloc[int(idxs[0]): int(idxs[-1]) + 1]
        shifted = Cell(cell.family, cell.side, cell.bb_len, cell.bb_mult, cell.rsi_threshold, cell.h_bar, cell.session)
        sig = signal_indices_family_a(part, shifted) if cell.family == "A" else signal_indices_family_b(part, shifted)
        trades = simulate_trades(part, sig, shifted)
        stat = stats_for_trades(shifted, trades)
        folds.append(
            {
                "fold": fold_no,
                "period_start": part.index[0].isoformat(),
                "period_end": part.index[-1].isoformat(),
                "n": stat["n"],
                "wr": stat["wr"],
                "mean_pip": stat["mean_pip"],
                "pf": stat["pf"],
                "kelly": stat["kelly"],
            }
        )
    return folds


def verdict_for(row: dict, paired_sign: str, wf: list[dict]) -> dict:
    pf = float("inf") if row["pf"] == "inf" else float(row["pf"])
    gates = {
        "G1_n_ge_30": row["n"] >= 30,
        "G2_wilson_lower_ge_0p50": row["wilson_lower"] >= 0.50,
        "G3_ev_pip_gt_0": row["mean_pip"] > 0,
        "G4_bh_fdr_lt_alpha": row.get("bh_fdr_p", 1.0) < ALPHA,
        "G5_pf_ge_1p20": pf >= 1.20,
        "G6_kelly_ge_0p05": row["kelly"] >= 0.05,
        "G7_wf_all_folds_ev_gt_0": bool(wf) and all(f["mean_pip"] > 0 for f in wf),
        "G8_long_short_sign": paired_sign,
    }
    if all(gates[k] for k in ("G1_n_ge_30", "G2_wilson_lower_ge_0p50", "G3_ev_pip_gt_0", "G4_bh_fdr_lt_alpha", "G5_pf_ge_1p20", "G6_kelly_ge_0p05", "G7_wf_all_folds_ev_gt_0")):
        verdict = "SHADOW_CANDIDATE"
    elif gates["G1_n_ge_30"] and gates["G2_wilson_lower_ge_0p50"] and gates["G3_ev_pip_gt_0"] and (not gates["G4_bh_fdr_lt_alpha"]) and paired_sign == "sign_mismatch":
        verdict = "DIRECTION_LED_NULL"
    else:
        verdict = "REJECT"
    return {"verdict": verdict, "gates": gates}


def iter_cells(family: str = "A") -> Iterable[Cell]:
    for side in SIDES:
        for length in BB_LENGTHS:
            for mult in BB_MULTS:
                for rsi in RSI_THRESHOLDS:
                    for h_bar in H_BARS:
                        for session in SESSIONS:
                            yield Cell(family, side, length, mult, rsi, h_bar, session)


def _pair_key(row: dict) -> tuple:
    return (row["bb_len"], row["bb_mult"], row["rsi_threshold"], row["h_bar"], row["session"])


def add_verdicts(rows: list[dict], wf_map: dict[str, list[dict]]) -> None:
    by_param: dict[tuple, dict[str, dict]] = {}
    for row in rows:
        by_param.setdefault(_pair_key(row), {})[row["side"]] = row
    for row in rows:
        peer = by_param.get(_pair_key(row), {}).get("short" if row["side"] == "long" else "long")
        if peer is None:
            sign = "missing_peer"
        elif row["mean_pip"] == 0 or peer["mean_pip"] == 0:
            sign = "zero_ev"
        elif (row["mean_pip"] > 0) == (peer["mean_pip"] > 0):
            sign = "sign_match"
        else:
            sign = "sign_mismatch"
        row.update(verdict_for(row, sign, wf_map.get(row["cell_id"], [])))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n")


def render_summary(rows: list[dict], meta: dict) -> str:
    top = sorted(rows, key=lambda r: (r["verdict"] != "SHADOW_CANDIDATE", -r["mean_pip"], -r["n"]))[:12]
    survivors = [r for r in rows if r["verdict"] == "SHADOW_CANDIDATE"]
    direction_nulls = [r for r in rows if r["verdict"] == "DIRECTION_LED_NULL"]
    lines = [
        "# BB 2-sigma Fade BT Summary",
        "",
        f"- generated_at: {meta['generated_at']}",
        f"- data_source: `{meta['data_source']}`",
        f"- period: {meta['period_start']} to {meta['period_end']}",
        f"- bars: {meta['bars']:,}",
        f"- spread_pip: {SPREAD_PIP}",
        f"- alpha_bonferroni_64: {ALPHA:.8f}",
        f"- survivors: {len(survivors)}",
        f"- direction_led_null: {len(direction_nulls)}",
        "",
        "## Top Cells",
        "",
        "| verdict | side | L | M | R | H | session | N | WR | Wilson_lo | EV pip | PF | Kelly | BH-FDR | G8 |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in top:
        pf = r["pf"]
        lines.append(
            f"| {r['verdict']} | {r['side']} | {r['bb_len']} | {r['bb_mult']} | "
            f"{r['rsi_threshold']} | {r['h_bar']} | {r['session']} | {r['n']} | "
            f"{r['wr']:.3f} | {r['wilson_lower']:.3f} | {r['mean_pip']:.3f} | "
            f"{pf} | {r['kelly']:.3f} | {r.get('bh_fdr_p', 1):.6g} | "
            f"{r['gates']['G8_long_short_sign']} |"
        )
    if survivors:
        lines += ["", "## Survivor Cell IDs", ""]
        lines += [f"- `{r['cell_id']}`" for r in survivors]
    else:
        lines += ["", "## Survivor Cell IDs", "", "- none"]
    return "\n".join(lines) + "\n"


def render_null_summary(rows: list[dict]) -> str:
    rejects = [r for r in rows if r["verdict"] == "REJECT"]
    nulls = [r for r in rows if r["verdict"] == "DIRECTION_LED_NULL"]
    lines = [
        "# BB 2-sigma Fade Null Summary",
        "",
        f"- rejected_cells: {len(rejects)}",
        f"- direction_led_null_cells: {len(nulls)}",
        "",
        "## Direction-led Nulls",
        "",
    ]
    if not nulls:
        lines.append("- none")
    else:
        for r in nulls:
            lines.append(f"- `{r['cell_id']}` EV={r['mean_pip']:.3f} BH-FDR={r.get('bh_fdr_p', 1):.6g}")
    return "\n".join(lines) + "\n"


def render_ablation(a_rows: list[dict], b_rows: list[dict]) -> str:
    b_by = {r["cell_id"].replace("B_", "A_", 1): r for r in b_rows}
    rows = []
    for a in a_rows:
        b = b_by.get(a["cell_id"])
        if b:
            rows.append((a, b, b["mean_pip"] - a["mean_pip"], b["wr"] - a["wr"], b["n"] - a["n"]))
    rows.sort(key=lambda x: x[2])
    lines = [
        "# BB 2-sigma Fade Ablation",
        "",
        "Family A is the pure close-outside-BB + RSI14 fade. Family B calls current",
        "`strategies/scalp/bb_rsi.py` with the same BB length/multiplier and RSI14",
        "threshold mapped into its context, preserving existing extra filters and exit",
        "geometry.",
        "",
        "Key current-design differences observed in Family B:",
        "- ADX floor and regime guard are active through `BBRsiReversion.evaluate()`.",
        "- Stochastic reversal and confirmation-candle filters are active.",
        "- TP/SL comes from the existing strategy's RR floor geometry, not Family A's mid/ATR target.",
        "- No MA trend filter is introduced by this experiment.",
        "",
        "| side | L | M | R | H | session | A_N | A_EV | A_WR | B_N | B_EV | B_WR | dEV | dWR | dN |",
        "|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for a, b, d_ev, d_wr, d_n in rows[:64]:
        lines.append(
            f"| {a['side']} | {a['bb_len']} | {a['bb_mult']} | {a['rsi_threshold']} | "
            f"{a['h_bar']} | {a['session']} | {a['n']} | {a['mean_pip']:.3f} | "
            f"{a['wr']:.3f} | {b['n']} | {b['mean_pip']:.3f} | {b['wr']:.3f} | "
            f"{d_ev:.3f} | {d_wr:.3f} | {d_n} |"
        )
    return "\n".join(lines) + "\n"


def run_backtest(data_path: Path | None = None, report_dir: Path = REPORT_DIR) -> dict:
    df_raw, source = load_frame(data_path)
    df = add_indicators(df_raw)
    generated_at = datetime.now(timezone.utc).isoformat()
    meta = {
        "generated_at": generated_at,
        "data_source": str(source.relative_to(ROOT) if source.is_relative_to(ROOT) else source),
        "period_start": df.index[0].isoformat(),
        "period_end": df.index[-1].isoformat(),
        "bars": int(len(df)),
        "pair": PAIR,
        "tf": TF,
    }

    a_rows: list[dict] = []
    b_rows: list[dict] = []
    wf_map: dict[str, list[dict]] = {}

    for cell in iter_cells("A"):
        sig = signal_indices_family_a(df, cell)
        trades = simulate_trades(df, sig, cell)
        row = stats_for_trades(cell, trades)
        a_rows.append(row)
        write_json(report_dir / "per_cell" / f"{cell.id}.json", {"meta": meta, "stats": row, "trades": trades})

    bh_fdr(a_rows)
    for row in a_rows:
        cell = Cell("A", row["side"], row["bb_len"], row["bb_mult"], row["rsi_threshold"], row["h_bar"], row["session"])
        wf = wf_3fold(df, cell)
        wf_map[row["cell_id"]] = wf
        write_json(report_dir / "wf_3fold" / f"{row['cell_id']}.json", {"meta": meta, "cell_id": row["cell_id"], "folds": wf})
    add_verdicts(a_rows, wf_map)

    for cell in iter_cells("B"):
        sig = signal_indices_family_b(df, cell)
        trades = simulate_trades(df, sig, cell)
        b_rows.append(stats_for_trades(cell, trades))

    write_json(report_dir / "all_cells.json", {"meta": meta, "family_a": a_rows, "family_b": b_rows})
    (report_dir / "summary.md").write_text(render_summary(a_rows, meta))
    (report_dir / "null_summary.md").write_text(render_null_summary(a_rows))
    (report_dir / "ablation.md").write_text(render_ablation(a_rows, b_rows))
    return {"meta": meta, "family_a": a_rows, "family_b": b_rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    result = run_backtest(args.data, args.report_dir)
    survivors = [r for r in result["family_a"] if r["verdict"] == "SHADOW_CANDIDATE"]
    print(json.dumps({"report_dir": str(args.report_dir), "survivors": len(survivors)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
