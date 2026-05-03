#!/usr/bin/env python3
"""S6 chart pattern detector for USDJPY M5 Wave 1 Phase 0.

Detector-only: this module does not touch live/shadow routing.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


EPS_FLAT_MULT = 0.05
EPS_SLOPE_MULT = 0.10
MIN_PATTERN_HEIGHT_MULT = 1.5
MIN_DURATION_BARS = 5
MAX_DURATION_BARS = 80
BREAKOUT_BUFFER_MULT = 0.10
SL_BUFFER_MULT = 0.50
PIVOT_TOLERANCE_MULT = 0.30

SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS chart_pattern_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL CHECK (pattern_id BETWEEN 1 AND 12),
    pattern_name TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('BUY','SELL')),
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_ts TEXT NOT NULL,
    detection_ts TEXT NOT NULL,
    entry_px REAL NOT NULL,
    sl_px REAL NOT NULL,
    tp_px REAL NOT NULL,
    pattern_height_atr REAL NOT NULL,
    duration_bars INTEGER NOT NULL,
    atr_at_detection REAL NOT NULL,
    pivot_anchor_ts TEXT NOT NULL,
    pivot_opposite_ts TEXT NOT NULL,
    pivot_count INTEGER NOT NULL,
    confidence_score REAL,
    raw_geometry_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pattern_id, pair, timeframe, pivot_anchor_ts, pivot_opposite_ts)
);

CREATE INDEX IF NOT EXISTS idx_cps_pair_tf_ts ON chart_pattern_signals(pair, timeframe, signal_ts);
CREATE INDEX IF NOT EXISTS idx_cps_pattern ON chart_pattern_signals(pattern_id, pair, timeframe);
"""


@dataclass(frozen=True)
class PatternSpec:
    pattern_id: int
    name: str
    direction: str


PATTERNS = [
    PatternSpec(1, "ascending_triangle", "BUY"),
    PatternSpec(2, "rising_wedge", "BUY"),
    PatternSpec(3, "bull_flag", "BUY"),
    PatternSpec(4, "descending_triangle", "SELL"),
    PatternSpec(5, "falling_wedge", "SELL"),
    PatternSpec(6, "bear_flag", "SELL"),
    PatternSpec(7, "double_bottom", "BUY"),
    PatternSpec(8, "triple_bottom", "BUY"),
    PatternSpec(9, "inverse_head_shoulders", "BUY"),
    PatternSpec(10, "double_top", "SELL"),
    PatternSpec(11, "triple_top", "SELL"),
    PatternSpec(12, "head_shoulders", "SELL"),
]
PATTERN_BY_NAME = {p.name: p for p in PATTERNS}
PATTERN_BY_ID = {p.pattern_id: p for p in PATTERNS}


@dataclass(frozen=True)
class Pivot:
    kind: str
    pos: int
    ts: pd.Timestamp
    price: float


@dataclass(frozen=True)
class ChartPatternSignal:
    pattern_id: int
    pattern_name: str
    direction: str
    pair: str
    timeframe: str
    signal_ts: str
    detection_ts: str
    entry_px: float
    sl_px: float
    tp_px: float
    pattern_height_atr: float
    duration_bars: int
    atr_at_detection: float
    pivot_anchor_ts: str
    pivot_opposite_ts: str
    pivot_count: int
    confidence_score: float
    raw_geometry_json: str


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.rename(columns={c: c.lower() for c in out.columns})
    missing = {"open", "high", "low", "close"} - set(out.columns)
    if missing:
        raise ValueError(f"OHLC missing columns: {sorted(missing)}")
    out.index = pd.to_datetime(out.index, utc=True)
    return out.sort_index()


def compute_atr_wilder(df: pd.DataFrame, period: int = 14) -> pd.Series:
    df = normalize_ohlcv(df)
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    values = [math.nan] * len(tr)
    if len(tr) >= period:
        first = float(tr.iloc[:period].mean())
        values[period - 1] = first
        prev = first
        for i in range(period, len(tr)):
            prev = (prev * (period - 1) + float(tr.iloc[i])) / period
            values[i] = prev
    return pd.Series(values, index=df.index, name="atr_14")


def detect_swing_pivots(df: pd.DataFrame, k: int = 3) -> list[Pivot]:
    df = normalize_ohlcv(df)
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    pivots: list[Pivot] = []
    for i in range(k, len(df) - k):
        if highs[i] > max(highs[i - k : i]) and highs[i] > max(highs[i + 1 : i + k + 1]):
            pivots.append(Pivot("H", i, df.index[i], float(highs[i])))
        if lows[i] < min(lows[i - k : i]) and lows[i] < min(lows[i + 1 : i + k + 1]):
            pivots.append(Pivot("L", i, df.index[i], float(lows[i])))
    return sorted(pivots, key=lambda p: (p.pos, p.kind))


def _line(p1: Pivot, p2: Pivot) -> tuple[float, float]:
    dx = p2.pos - p1.pos
    if dx == 0:
        return 0.0, p2.price
    slope = (p2.price - p1.price) / dx
    intercept = p2.price - slope * p2.pos
    return slope, intercept


def _value(line: tuple[float, float], pos: int) -> float:
    return line[0] * pos + line[1]


def _ts(ts: pd.Timestamp) -> str:
    return pd.Timestamp(ts).tz_convert("UTC").isoformat()


def _atr_at(atr: pd.Series, pos: int) -> float:
    value = float(atr.iloc[pos])
    if math.isnan(value) or value <= 0:
        valid = atr.iloc[: pos + 1].dropna()
        value = float(valid.iloc[-1]) if not valid.empty else 0.01
    return max(value, 1e-9)


def detect_chart_patterns(
    df: pd.DataFrame,
    pair: str = "USD_JPY",
    timeframe: str = "M5",
    max_breakout_lookahead: int = 40,
) -> list[ChartPatternSignal]:
    df = normalize_ohlcv(df)
    atr = compute_atr_wilder(df)
    pivots = detect_swing_pivots(df)
    by_key: dict[tuple[int, str, str], ChartPatternSignal] = {}

    def add_signal(
        spec: PatternSpec,
        pivs: list[Pivot],
        breakout_line: tuple[float, float] | None,
        breakout_level: float,
        height: float,
        extreme: float,
        detection_pos: int,
        anchor: Pivot,
        opposite: Pivot,
        raw: dict,
    ) -> None:
        atr_det = _atr_at(atr, detection_pos)
        direction = spec.direction
        buffer = BREAKOUT_BUFFER_MULT * atr_det
        start = min(detection_pos + 1, len(df) - 1)
        end = min(len(df), detection_pos + 1 + max_breakout_lookahead)
        if end <= start:
            return
        for j in range(start, end):
            level = _value(breakout_line, j) if breakout_line is not None else breakout_level
            close = float(df["close"].iloc[j])
            if direction == "BUY":
                if close <= level + buffer:
                    continue
                entry = close
                sl = extreme - SL_BUFFER_MULT * atr_det
                tp = entry + height
            else:
                if close >= level - buffer:
                    continue
                entry = close
                sl = extreme + SL_BUFFER_MULT * atr_det
                tp = entry - height
            duration = max(p.pos for p in pivs) - min(p.pos for p in pivs)
            if duration < MIN_DURATION_BARS or duration > MAX_DURATION_BARS:
                return
            sig = ChartPatternSignal(
                pattern_id=spec.pattern_id,
                pattern_name=spec.name,
                direction=direction,
                pair=pair,
                timeframe=timeframe,
                signal_ts=_ts(df.index[j]),
                detection_ts=_ts(df.index[detection_pos]),
                entry_px=float(entry),
                sl_px=float(sl),
                tp_px=float(tp),
                pattern_height_atr=float(height / atr_det),
                duration_bars=int(duration),
                atr_at_detection=float(atr_det),
                pivot_anchor_ts=_ts(anchor.ts),
                pivot_opposite_ts=_ts(opposite.ts),
                pivot_count=len(pivs),
                confidence_score=float(raw.get("confidence", 0.75)),
                raw_geometry_json=json.dumps(raw, sort_keys=True),
            )
            key = (spec.pattern_id, sig.pivot_anchor_ts, sig.pivot_opposite_ts)
            if key not in by_key:
                by_key[key] = sig
            return

    for i in range(len(pivots) - 3):
        seq = pivots[i : i + 4]
        if not _is_alternating(seq):
            continue
        highs = [p for p in seq if p.kind == "H"]
        lows = [p for p in seq if p.kind == "L"]
        if len(highs) != 2 or len(lows) != 2:
            continue
        detection_pos = max(p.pos for p in seq)
        atr_det = _atr_at(atr, detection_pos)
        eps_flat = EPS_FLAT_MULT * atr_det
        eps_slope = EPS_SLOPE_MULT * atr_det
        min_height = MIN_PATTERN_HEIGHT_MULT * atr_det
        upper = _line(highs[0], highs[1])
        lower = _line(lows[0], lows[1])
        au, al = upper[0], lower[0]
        height = max(p.price for p in seq) - min(p.price for p in seq)
        if height < min_height:
            continue
        width_start = _value(upper, min(p.pos for p in seq)) - _value(lower, min(p.pos for p in seq))
        width_end = _value(upper, detection_pos) - _value(lower, detection_pos)
        convergence = width_start > 0 and width_end <= 0.5 * width_start
        raw = _raw(seq, upper=upper, lower=lower, height=height, confidence=0.75)
        if abs(au) < eps_flat and al > eps_slope:
            add_signal(PATTERN_BY_NAME["ascending_triangle"], seq, upper, 0.0, height, min(p.price for p in lows), detection_pos, highs[0], lows[-1], raw)
        if au > 0 and al > 0 and al > au and convergence:
            add_signal(PATTERN_BY_NAME["rising_wedge"], seq, upper, 0.0, height, min(p.price for p in lows), detection_pos, highs[0], lows[-1], raw | {"confidence": 0.8})
        if abs(al) < eps_flat and au < -eps_slope:
            add_signal(PATTERN_BY_NAME["descending_triangle"], seq, lower, 0.0, height, max(p.price for p in highs), detection_pos, lows[0], highs[-1], raw)
        if au < 0 and al < 0 and au < al and convergence:
            add_signal(PATTERN_BY_NAME["falling_wedge"], seq, lower, 0.0, height, max(p.price for p in highs), detection_pos, lows[0], highs[-1], raw | {"confidence": 0.8})
        _maybe_flag(df, atr, seq, upper, lower, au, al, height, add_signal)

    _detect_reversal_patterns(pivots, df, atr, add_signal)
    return sorted(by_key.values(), key=lambda s: (s.signal_ts, s.pattern_id))


def _maybe_flag(df, atr, seq, upper, lower, au, al, height, add_signal) -> None:
    detection_pos = max(p.pos for p in seq)
    start_pos = min(p.pos for p in seq)
    atr_det = _atr_at(atr, detection_pos)
    eps = EPS_SLOPE_MULT * atr_det
    min_pole_start = max(0, start_pos - 20)
    max_pole_start = max(0, start_pos - 1)
    if max_pole_start <= min_pole_start:
        return
    closes = df["close"]
    pre = closes.iloc[min_pole_start:max_pole_start]
    if pre.empty:
        return
    pole_up = float(closes.iloc[start_pos] - pre.min())
    pole_down = float(pre.max() - closes.iloc[start_pos])
    flag_amp = max(p.price for p in seq) - min(p.price for p in seq)
    highs = [p for p in seq if p.kind == "H"]
    lows = [p for p in seq if p.kind == "L"]
    if au < 0 and al < 0 and abs(au - al) < eps and pole_up >= 3 * atr_det and flag_amp <= 0.5 * pole_up:
        add_signal(
            PATTERN_BY_NAME["bull_flag"],
            seq,
            upper,
            0.0,
            flag_amp,
            min(p.price for p in lows),
            detection_pos,
            highs[0],
            lows[-1],
            _raw(seq, upper=upper, lower=lower, height=flag_amp, pole=pole_up, confidence=0.78),
        )
    if au > 0 and al > 0 and abs(au - al) < eps and pole_down >= 3 * atr_det and flag_amp <= 0.5 * pole_down:
        add_signal(
            PATTERN_BY_NAME["bear_flag"],
            seq,
            lower,
            0.0,
            flag_amp,
            max(p.price for p in highs),
            detection_pos,
            lows[0],
            highs[-1],
            _raw(seq, upper=upper, lower=lower, height=flag_amp, pole=pole_down, confidence=0.78),
        )


def _detect_reversal_patterns(pivots, df, atr, add_signal) -> None:
    for i in range(len(pivots) - 2):
        seq = pivots[i : i + 3]
        kinds = "".join(p.kind for p in seq)
        detection_pos = max(p.pos for p in seq)
        atr_det = _atr_at(atr, detection_pos)
        tol = PIVOT_TOLERANCE_MULT * atr_det
        min_height = MIN_PATTERN_HEIGHT_MULT * atr_det
        duration = seq[-1].pos - seq[0].pos
        if duration < MIN_DURATION_BARS or duration > 50:
            continue
        if kinds == "LHL":
            l1, h, l2 = seq
            height = h.price - min(l1.price, l2.price)
            if abs(l1.price - l2.price) <= tol and height >= min_height:
                add_signal(PATTERN_BY_NAME["double_bottom"], seq, None, h.price, height, min(l1.price, l2.price), detection_pos, l1, l2, _raw(seq, neckline=h.price, height=height, confidence=0.76))
            if l2.price < l1.price and abs(l1.price - l2.price) > tol:
                pass
        if kinds == "HLH":
            h1, l, h2 = seq
            height = max(h1.price, h2.price) - l.price
            if abs(h1.price - h2.price) <= tol and height >= min_height:
                add_signal(PATTERN_BY_NAME["double_top"], seq, None, l.price, height, max(h1.price, h2.price), detection_pos, h1, h2, _raw(seq, neckline=l.price, height=height, confidence=0.76))

    for i in range(len(pivots) - 4):
        seq = pivots[i : i + 5]
        kinds = "".join(p.kind for p in seq)
        detection_pos = max(p.pos for p in seq)
        atr_det = _atr_at(atr, detection_pos)
        tol = PIVOT_TOLERANCE_MULT * atr_det
        min_height = MIN_PATTERN_HEIGHT_MULT * atr_det
        if seq[-1].pos - seq[0].pos > MAX_DURATION_BARS:
            continue
        if kinds == "LHLHL":
            lows = [seq[0], seq[2], seq[4]]
            highs = [seq[1], seq[3]]
            height = max(h.price for h in highs) - min(l.price for l in lows)
            if max(l.price for l in lows) - min(l.price for l in lows) <= tol and abs(highs[0].price - highs[1].price) <= 0.4 * atr_det and height >= min_height:
                neckline = max(h.price for h in highs)
                add_signal(PATTERN_BY_NAME["triple_bottom"], seq, None, neckline, height, min(l.price for l in lows), detection_pos, lows[0], lows[-1], _raw(seq, neckline=neckline, height=height, confidence=0.82))
            l1, h1, head, h2, l3 = seq
            left = head.pos - l1.pos
            right = l3.pos - head.pos
            sym = abs(left - right) / max(left, right)
            neckline = (h1.price + h2.price) / 2
            height_hs = neckline - head.price
            if head.price < l1.price and head.price < l3.price and abs(l1.price - l3.price) <= 0.5 * atr_det and sym <= 0.4 and height_hs >= min_height:
                add_signal(PATTERN_BY_NAME["inverse_head_shoulders"], seq, None, neckline, height_hs, min(l.price for l in [l1, head, l3]), detection_pos, l1, l3, _raw(seq, neckline=neckline, height=height_hs, symmetry=sym, confidence=0.84))
        if kinds == "HLHLH":
            highs = [seq[0], seq[2], seq[4]]
            lows = [seq[1], seq[3]]
            height = max(h.price for h in highs) - min(l.price for l in lows)
            if max(h.price for h in highs) - min(h.price for h in highs) <= tol and abs(lows[0].price - lows[1].price) <= 0.4 * atr_det and height >= min_height:
                neckline = min(l.price for l in lows)
                add_signal(PATTERN_BY_NAME["triple_top"], seq, None, neckline, height, max(h.price for h in highs), detection_pos, highs[0], highs[-1], _raw(seq, neckline=neckline, height=height, confidence=0.82))
            h1, l1, head, l2, h3 = seq
            left = head.pos - h1.pos
            right = h3.pos - head.pos
            sym = abs(left - right) / max(left, right)
            neckline = (l1.price + l2.price) / 2
            height_hs = head.price - neckline
            if head.price > h1.price and head.price > h3.price and abs(h1.price - h3.price) <= 0.5 * atr_det and sym <= 0.4 and height_hs >= min_height:
                add_signal(PATTERN_BY_NAME["head_shoulders"], seq, None, neckline, height_hs, max(h.price for h in [h1, head, h3]), detection_pos, h1, h3, _raw(seq, neckline=neckline, height=height_hs, symmetry=sym, confidence=0.84))


def _is_alternating(seq: Iterable[Pivot]) -> bool:
    kinds = [p.kind for p in seq]
    return all(a != b for a, b in zip(kinds, kinds[1:]))


def _raw(pivs: list[Pivot], **extra) -> dict:
    return {
        "pivots": [{"kind": p.kind, "pos": p.pos, "ts": _ts(p.ts), "price": p.price} for p in pivs],
        **extra,
    }


def synthetic_pattern_bars(pattern_name: str, wick_only: bool = False, duplicate_breakout: bool = False) -> pd.DataFrame:
    if pattern_name not in PATTERN_BY_NAME:
        raise ValueError(pattern_name)
    spec = PATTERN_BY_NAME[pattern_name]
    idx = pd.date_range("2026-01-01", periods=70, freq="5min", tz="UTC")
    if spec.direction == "BUY":
        piv = _synthetic_buy_pivots(pattern_name)
        breakout = 106.0
    else:
        piv = _synthetic_sell_pivots(pattern_name)
        breakout = 94.0

    close = _interpolated_synthetic_closes(piv, len(idx), spec.direction, pattern_name)
    open_ = close[:]
    high = [c + 0.08 for c in close]
    low = [c - 0.08 for c in close]

    def set_bar(i, c, h=None, l=None):
        close[i] = c
        open_[i] = c
        high[i] = h if h is not None else c + 0.08
        low[i] = l if l is not None else c - 0.08

    for pos, kind, price in piv:
        if kind == "H":
            set_bar(pos, price - 0.05, h=price + 0.60, l=price - 0.18)
        else:
            set_bar(pos, price + 0.05, h=price + 0.18, l=price - 0.60)
    signal_pos = max(p[0] for p in piv) + 4
    if wick_only:
        if spec.direction == "BUY":
            set_bar(signal_pos, 104.0, h=breakout + 1.0, l=103.8)
            for i in range(signal_pos + 1, len(idx)):
                set_bar(i, 104.0, h=104.08, l=103.92)
        else:
            set_bar(signal_pos, 96.0, h=96.2, l=breakout - 1.0)
            for i in range(signal_pos + 1, len(idx)):
                set_bar(i, 96.0, h=96.08, l=95.92)
    else:
        set_bar(signal_pos, breakout)
        if duplicate_breakout and signal_pos + 1 < len(idx):
            set_bar(signal_pos + 1, breakout + (0.5 if spec.direction == "BUY" else -0.5))
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": 100}, index=idx)


def _interpolated_synthetic_closes(piv, n: int, direction: str, pattern_name: str) -> list[float]:
    points = [(0, 101.5 if direction == "BUY" else 98.5)]
    if "flag" in pattern_name:
        if direction == "BUY":
            points = [(0, 95.0), (max(1, piv[0][0] - 1), 101.5)]
        else:
            points = [(0, 105.0), (max(1, piv[0][0] - 1), 98.5)]
    points += [(pos, price) for pos, _kind, price in piv]
    end_price = (106.0 if direction == "BUY" else 94.0)
    last_pos, last_kind, last_price = max(piv, key=lambda p: p[0])
    pullback = last_price - 1.0 if last_kind == "H" else last_price + 1.0
    points += [(last_pos + 3, pullback), (last_pos + 4, end_price), (n - 1, end_price)]
    points = sorted(points)
    close = [points[0][1]] * n
    for (p0, v0), (p1, v1) in zip(points, points[1:]):
        span = max(1, p1 - p0)
        for i in range(p0, min(p1 + 1, n)):
            frac = (i - p0) / span
            close[i] = v0 + (v1 - v0) * frac
    return close


def _synthetic_buy_pivots(pattern_name: str):
    mapping = {
        "ascending_triangle": [(10, "L", 100.0), (16, "H", 104.0), (22, "L", 102.0), (28, "H", 104.05)],
        "rising_wedge": [(10, "L", 100.0), (16, "H", 103.0), (22, "L", 102.5), (28, "H", 103.35)],
        "bull_flag": [(10, "H", 104.0), (16, "L", 102.0), (22, "H", 103.4), (28, "L", 101.0)],
        "double_bottom": [(10, "L", 100.0), (18, "H", 104.0), (28, "L", 100.05)],
        "triple_bottom": [(8, "L", 100.0), (16, "H", 104.0), (24, "L", 100.05), (32, "H", 104.1), (40, "L", 99.98)],
        "inverse_head_shoulders": [(8, "L", 100.0), (16, "H", 104.0), (24, "L", 98.0), (32, "H", 104.2), (40, "L", 100.1)],
    }
    return mapping[pattern_name]


def _synthetic_sell_pivots(pattern_name: str):
    mapping = {
        "descending_triangle": [(10, "H", 104.0), (16, "L", 100.0), (22, "H", 102.0), (28, "L", 99.95)],
        "falling_wedge": [(10, "H", 104.0), (16, "L", 101.0), (22, "H", 101.5), (28, "L", 100.65)],
        "bear_flag": [(10, "L", 96.0), (16, "H", 98.2), (22, "L", 97.0), (28, "H", 99.2)],
        "double_top": [(10, "H", 104.0), (18, "L", 100.0), (28, "H", 103.95)],
        "triple_top": [(8, "H", 104.0), (16, "L", 100.0), (24, "H", 103.95), (32, "L", 99.9), (40, "H", 104.02)],
        "head_shoulders": [(8, "H", 104.0), (16, "L", 100.0), (24, "H", 106.0), (32, "L", 99.8), (40, "H", 103.9)],
    }
    return mapping[pattern_name]


def synthetic_expected_levels(pattern_name: str) -> dict[str, float]:
    df = synthetic_pattern_bars(pattern_name)
    sig = [s for s in detect_chart_patterns(df) if s.pattern_name == pattern_name][0]
    return {"entry_px": sig.entry_px, "sl_px": sig.sl_px, "tp_px": sig.tp_px}


def run_self_test() -> dict[str, bool]:
    results = {}
    for spec in PATTERNS:
        signals = [s for s in detect_chart_patterns(synthetic_pattern_bars(spec.name)) if s.pattern_name == spec.name]
        results[spec.name] = bool(signals)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--parquet")
    args = parser.parse_args()
    if args.self_test:
        results = run_self_test()
        for name in [p.name for p in PATTERNS]:
            print(f"{name}: {'HIT' if results[name] else 'MISS'}")
        return 0 if all(results.values()) else 1
    if args.parquet:
        df = pd.read_parquet(args.parquet)
        signals = detect_chart_patterns(df)
        print(json.dumps({"signals": len(signals)}, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
