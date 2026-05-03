#!/usr/bin/env python3
"""Wave 1 Phase 0 chart-pattern detector for USD_JPY M5.

Scope guard:
  - Detector and label generation only.
  - No backtest loop, no LIVE/Shadow integration, no OANDA bridge access.

SQLite schema (LOCKED from task spec):

CREATE TABLE IF NOT EXISTS chart_pattern_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER NOT NULL CHECK (pattern_id BETWEEN 1 AND 12),
    pattern_name TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('BUY','SELL')),
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_ts TEXT NOT NULL,            -- ISO8601 UTC of breakout bar close
    detection_ts TEXT NOT NULL,         -- pattern が完成した bar (breakout 前最後の pivot)
    entry_px REAL NOT NULL,
    sl_px REAL NOT NULL,
    tp_px REAL NOT NULL,
    pattern_height_atr REAL NOT NULL,   -- pattern_height / ATR_at_detection
    duration_bars INTEGER NOT NULL,
    atr_at_detection REAL NOT NULL,
    pivot_anchor_ts TEXT NOT NULL,
    pivot_opposite_ts TEXT NOT NULL,
    pivot_count INTEGER NOT NULL,
    confidence_score REAL,              -- optional: 幾何適合度 0-1 (収束率・対称性等の合成)
    raw_geometry_json TEXT,             -- debug 用 JSON (pivots, slopes, neckline 等)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(pattern_id, pair, timeframe, pivot_anchor_ts, pivot_opposite_ts)
);

CREATE INDEX IF NOT EXISTS idx_cps_pair_tf_ts ON chart_pattern_signals(pair, timeframe, signal_ts);
CREATE INDEX IF NOT EXISTS idx_cps_pattern ON chart_pattern_signals(pattern_id, pair, timeframe);
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SCHEMA_SQL = """
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


EPS_FLAT_ATR = 0.05
EPS_SLOPE_ATR = 0.10
MIN_PATTERN_HEIGHT_ATR = 1.5
MIN_DURATION_BARS = 5
MAX_DURATION_BARS = 80
BREAKOUT_BUFFER_ATR = 0.10
SL_BUFFER_ATR = 0.50
PIVOT_TOLERANCE_ATR = 0.30
PIVOT_K = 3
ATR_PERIOD = 14
POST_DETECTION_MAX_BARS = 80


PATTERNS = {
    1: ("ascending_triangle", "BUY"),
    2: ("rising_wedge", "BUY"),
    3: ("bull_flag", "BUY"),
    4: ("descending_triangle", "SELL"),
    5: ("falling_wedge", "SELL"),
    6: ("bear_flag", "SELL"),
    7: ("double_bottom", "BUY"),
    8: ("triple_bottom", "BUY"),
    9: ("inverse_head_shoulders", "BUY"),
    10: ("double_top", "SELL"),
    11: ("triple_top", "SELL"),
    12: ("head_shoulders", "SELL"),
}


@dataclass(frozen=True)
class Pivot:
    idx: int
    ts: str
    kind: str
    price: float
    confirm_idx: int


@dataclass(frozen=True)
class Candidate:
    pattern_id: int
    direction: str
    pivots: tuple[Pivot, ...]
    breakout_level: float
    pattern_height: float
    extreme: float
    anchor: Pivot
    opposite: Pivot
    confidence: float
    raw: dict


@dataclass(frozen=True)
class Signal:
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


def _ts(value) -> str:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.isoformat()


def _line(p1: Pivot, p2: Pivot, x: int) -> float:
    if p2.idx == p1.idx:
        return p2.price
    return p1.price + (p2.price - p1.price) * ((x - p1.idx) / (p2.idx - p1.idx))


def _slope(p1: Pivot, p2: Pivot) -> float:
    return (p2.price - p1.price) / (p2.idx - p1.idx)


def _round(value: float) -> float:
    return round(float(value), 8)


def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    cols = {str(c).lower(): c for c in df.columns}
    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in cols]
    if missing:
        raise ValueError(f"OHLC columns missing: {missing}; got {list(df.columns)}")
    out = pd.DataFrame(index=df.index.copy())
    for c in required:
        out[c] = pd.to_numeric(df[cols[c]], errors="raise")
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def compute_atr_wilder(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    ohlc = normalize_ohlc(df)
    high = ohlc["high"].to_numpy(float)
    low = ohlc["low"].to_numpy(float)
    close = ohlc["close"].to_numpy(float)
    tr = np.empty(len(ohlc), dtype=float)
    tr[0] = high[0] - low[0]
    for i in range(1, len(ohlc)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    atr = np.full(len(ohlc), np.nan, dtype=float)
    if len(ohlc) >= period:
        atr[period - 1] = float(np.mean(tr[:period]))
        for i in range(period, len(ohlc)):
            atr[i] = ((atr[i - 1] * (period - 1)) + tr[i]) / period
    return pd.Series(atr, index=ohlc.index, name="atr_14")


def find_swing_pivots(df: pd.DataFrame, k: int = PIVOT_K) -> list[Pivot]:
    ohlc = normalize_ohlc(df)
    high = ohlc["high"].to_numpy(float)
    low = ohlc["low"].to_numpy(float)
    idx = ohlc.index
    pivots: list[Pivot] = []
    for i in range(k, len(ohlc) - k):
        if high[i] > np.max(high[i - k:i]) and high[i] > np.max(high[i + 1:i + 1 + k]):
            pivots.append(Pivot(i, _ts(idx[i]), "H", float(high[i]), i + k))
        if low[i] < np.min(low[i - k:i]) and low[i] < np.min(low[i + 1:i + 1 + k]):
            pivots.append(Pivot(i, _ts(idx[i]), "L", float(low[i]), i + k))
    pivots.sort(key=lambda p: (p.confirm_idx, p.idx, p.kind))
    return pivots


def _alternating(pivots: Iterable[Pivot]) -> bool:
    seq = list(sorted(pivots, key=lambda p: p.idx))
    return all(seq[i].kind != seq[i - 1].kind for i in range(1, len(seq)))


def _base_ok(pivots: tuple[Pivot, ...], atr: float) -> bool:
    if not math.isfinite(atr) or atr <= 0:
        return False
    duration = pivots[-1].idx - pivots[0].idx
    if duration < MIN_DURATION_BARS or duration > MAX_DURATION_BARS:
        return False
    height = max(p.price for p in pivots) - min(p.price for p in pivots)
    return height >= MIN_PATTERN_HEIGHT_ATR * atr


def _make_candidate(
    pattern_id: int,
    pivots: tuple[Pivot, ...],
    breakout_level: float,
    height: float,
    extreme: float,
    anchor: Pivot,
    opposite: Pivot,
    confidence: float,
    raw: dict,
) -> Candidate:
    name, direction = PATTERNS[pattern_id]
    raw = dict(raw)
    raw["pattern_name"] = name
    raw["pivots"] = [{"idx": p.idx, "ts": p.ts, "kind": p.kind, "price": _round(p.price)} for p in pivots]
    raw["breakout_level"] = _round(breakout_level)
    raw["pattern_height"] = _round(height)
    return Candidate(pattern_id, direction, pivots, float(breakout_level), float(height), float(extreme), anchor, opposite, max(0.0, min(1.0, confidence)), raw)


def _triangle_wedge_candidates(recent: list[Pivot], t: int, atr: float) -> list[Candidate]:
    out: list[Candidate] = []
    eps_flat = EPS_FLAT_ATR * atr
    eps_slope = EPS_SLOPE_ATR * atr
    for window_size in (4, 5, 6):
        if len(recent) < window_size:
            continue
        piv = tuple(sorted(recent[-window_size:], key=lambda p: p.idx))
        if not _base_ok(piv, atr) or not _alternating(piv):
            continue
        highs = [p for p in piv if p.kind == "H"]
        lows = [p for p in piv if p.kind == "L"]
        if len(highs) < 2 or len(lows) < 2:
            continue
        h1, h2 = highs[-2], highs[-1]
        l1, l2 = lows[-2], lows[-1]
        au, al = _slope(h1, h2), _slope(l1, l2)
        height = max(p.price for p in piv) - min(p.price for p in piv)
        duration = piv[-1].idx - piv[0].idx
        upper_now = _line(h1, h2, t)
        lower_now = _line(l1, l2, t)
        width_start = _line(h1, h2, piv[0].idx) - _line(l1, l2, piv[0].idx)
        width_end = _line(h1, h2, piv[-1].idx) - _line(l1, l2, piv[-1].idx)
        conv = (width_start - width_end) / width_start if width_start > 0 else -1.0
        raw = {"upper_slope": au, "lower_slope": al, "duration_bars": duration, "convergence": conv}
        if abs(au) < eps_flat and al > eps_slope:
            out.append(_make_candidate(1, piv, upper_now, height, min(p.price for p in lows), lows[0], highs[-1], 0.65 + min(0.35, al / (5 * eps_slope)), raw))
        if au > 0 and al > 0 and al > au and conv >= 0.50:
            out.append(_make_candidate(2, piv, upper_now, height, min(p.price for p in lows), lows[0], highs[-1], min(1.0, conv), raw))
        if abs(al) < eps_flat and au < -eps_slope:
            out.append(_make_candidate(4, piv, lower_now, height, max(p.price for p in highs), highs[0], lows[-1], 0.65 + min(0.35, abs(au) / (5 * eps_slope)), raw))
        if au < 0 and al < 0 and al > au and conv >= 0.50:
            out.append(_make_candidate(5, piv, lower_now, height, max(p.price for p in highs), highs[0], lows[-1], min(1.0, conv), raw))
    return out


def _flag_candidates(recent: list[Pivot], t: int, atr: float, close: np.ndarray) -> list[Candidate]:
    out: list[Candidate] = []
    eps = EPS_SLOPE_ATR * atr
    for window_size in (4, 5, 6):
        if len(recent) < window_size:
            continue
        piv = tuple(sorted(recent[-window_size:], key=lambda p: p.idx))
        if not _base_ok(piv, atr) or not _alternating(piv):
            continue
        start = piv[0].idx
        highs = [p for p in piv if p.kind == "H"]
        lows = [p for p in piv if p.kind == "L"]
        if len(highs) < 2 or len(lows) < 2:
            continue
        h1, h2 = highs[-2], highs[-1]
        l1, l2 = lows[-2], lows[-1]
        au, al = _slope(h1, h2), _slope(l1, l2)
        if abs(au - al) >= eps:
            continue
        flag_amp = max(p.price for p in piv) - min(p.price for p in piv)
        raw = {"upper_slope": au, "lower_slope": al, "flag_amplitude": flag_amp}
        for n in range(10, 21):
            pole_start = start - n
            if pole_start < 0:
                continue
            pole_delta = close[start] - close[pole_start]
            if pole_delta >= 3.0 * atr and au < 0 and al < 0 and flag_amp <= 0.5 * pole_delta:
                raw2 = dict(raw, pole_bars=n, pole_delta=pole_delta)
                out.append(_make_candidate(3, piv, _line(h1, h2, t), flag_amp, min(p.price for p in lows), lows[0], highs[-1], min(1.0, pole_delta / (6 * atr)), raw2))
                break
            bear_delta = close[pole_start] - close[start]
            if bear_delta >= 3.0 * atr and au > 0 and al > 0 and flag_amp <= 0.5 * bear_delta:
                raw2 = dict(raw, pole_bars=n, pole_delta=-bear_delta)
                out.append(_make_candidate(6, piv, _line(l1, l2, t), flag_amp, max(p.price for p in highs), highs[0], lows[-1], min(1.0, bear_delta / (6 * atr)), raw2))
                break
    return out


def _double_triple_candidates(recent: list[Pivot], atr: float) -> list[Candidate]:
    out: list[Candidate] = []
    tol = PIVOT_TOLERANCE_ATR * atr
    for kind, pid2, pid3 in (("L", 7, 8), ("H", 10, 11)):
        same = [p for p in recent if p.kind == kind]
        opp_kind = "H" if kind == "L" else "L"
        if len(same) >= 2:
            p1, p2 = same[-2], same[-1]
            piv = tuple(p for p in recent if p1.idx <= p.idx <= p2.idx)
            opp = [p for p in piv if p.kind == opp_kind]
            if opp and 5 <= p2.idx - p1.idx <= 50 and abs(p1.price - p2.price) <= tol:
                neck = max(opp, key=lambda p: p.price) if kind == "L" else min(opp, key=lambda p: p.price)
                extreme = min(p1.price, p2.price) if kind == "L" else max(p1.price, p2.price)
                height = abs(neck.price - extreme)
                if height >= MIN_PATTERN_HEIGHT_ATR * atr:
                    confidence = 1.0 - min(1.0, abs(p1.price - p2.price) / max(tol, 1e-12)) * 0.4
                    out.append(_make_candidate(pid2, (p1, neck, p2), neck.price, height, extreme, p1, neck, confidence, {"neckline": neck.price}))
        if len(same) >= 3:
            p1, p2, p3 = same[-3], same[-2], same[-1]
            if p3.idx - p1.idx <= MAX_DURATION_BARS and max(p.price for p in (p1, p2, p3)) - min(p.price for p in (p1, p2, p3)) <= tol:
                piv = tuple(p for p in recent if p1.idx <= p.idx <= p3.idx)
                opp1 = [p for p in piv if p.kind == opp_kind and p1.idx < p.idx < p2.idx]
                opp2 = [p for p in piv if p.kind == opp_kind and p2.idx < p.idx < p3.idx]
                if opp1 and opp2:
                    o1 = max(opp1, key=lambda p: p.price) if kind == "L" else min(opp1, key=lambda p: p.price)
                    o2 = max(opp2, key=lambda p: p.price) if kind == "L" else min(opp2, key=lambda p: p.price)
                    if abs(o1.price - o2.price) <= 0.4 * atr:
                        neck = (o1.price + o2.price) / 2.0
                        extreme = min(p.price for p in (p1, p2, p3)) if kind == "L" else max(p.price for p in (p1, p2, p3))
                        height = abs(neck - extreme)
                        if height >= MIN_PATTERN_HEIGHT_ATR * atr:
                            out.append(_make_candidate(pid3, (p1, o1, p2, o2, p3), neck, height, extreme, p1, o2, 0.75, {"neckline": neck, "intermediate_flatness": abs(o1.price - o2.price)}))
    return out


def _head_shoulders_candidates(recent: list[Pivot], t: int, atr: float) -> list[Candidate]:
    out: list[Candidate] = []
    for kind, pid in (("L", 9), ("H", 12)):
        same = [p for p in recent if p.kind == kind]
        opp_kind = "H" if kind == "L" else "L"
        if len(same) < 3:
            continue
        s1, head, s2 = same[-3], same[-2], same[-1]
        piv = tuple(p for p in recent if s1.idx <= p.idx <= s2.idx)
        if not _base_ok(piv, atr):
            continue
        left_dt = head.idx - s1.idx
        right_dt = s2.idx - head.idx
        if min(left_dt, right_dt) <= 0:
            continue
        sym = abs(left_dt - right_dt) / max(left_dt, right_dt)
        if sym > 0.4:
            continue
        if abs(s1.price - s2.price) > 0.5 * atr:
            continue
        opp1 = [p for p in piv if p.kind == opp_kind and s1.idx < p.idx < head.idx]
        opp2 = [p for p in piv if p.kind == opp_kind and head.idx < p.idx < s2.idx]
        if not opp1 or not opp2:
            continue
        n1 = max(opp1, key=lambda p: p.price) if kind == "L" else min(opp1, key=lambda p: p.price)
        n2 = max(opp2, key=lambda p: p.price) if kind == "L" else min(opp2, key=lambda p: p.price)
        neck = _line(n1, n2, t)
        if kind == "L":
            if not (head.price < s1.price and head.price < s2.price):
                continue
            height = neck - head.price
            extreme = head.price
        else:
            if not (head.price > s1.price and head.price > s2.price):
                continue
            height = head.price - neck
            extreme = head.price
        if height >= MIN_PATTERN_HEIGHT_ATR * atr:
            out.append(_make_candidate(pid, (s1, n1, head, n2, s2), neck, height, extreme, s1, n2, 1.0 - sym * 0.5, {"neckline_slope": _slope(n1, n2), "time_symmetry_ratio": sym}))
    return out


def build_candidates(recent: list[Pivot], t: int, atr: float, close: np.ndarray) -> list[Candidate]:
    usable = [p for p in recent if 0 <= t - p.idx <= MAX_DURATION_BARS + POST_DETECTION_MAX_BARS]
    candidates: list[Candidate] = []
    candidates.extend(_triangle_wedge_candidates(usable, t, atr))
    candidates.extend(_flag_candidates(usable, t, atr, close))
    candidates.extend(_double_triple_candidates(usable, atr))
    candidates.extend(_head_shoulders_candidates(usable, t, atr))
    return candidates


def candidate_triggers(candidate: Candidate, close_px: float, atr: float) -> bool:
    if candidate.direction == "BUY":
        return close_px > candidate.breakout_level + BREAKOUT_BUFFER_ATR * atr
    return close_px < candidate.breakout_level - BREAKOUT_BUFFER_ATR * atr


def candidate_to_signal(candidate: Candidate, df: pd.DataFrame, t: int, atr_series: pd.Series, pair: str, timeframe: str) -> Signal:
    ohlc = df
    signal_ts = _ts(ohlc.index[t])
    detection_pivot = max(candidate.pivots, key=lambda p: p.idx)
    detection_idx = detection_pivot.confirm_idx
    atr_det = float(atr_series.iloc[detection_idx]) if detection_idx < len(atr_series) and math.isfinite(float(atr_series.iloc[detection_idx])) else float(atr_series.iloc[t])
    atr_t = float(atr_series.iloc[t])
    entry = float(ohlc["close"].iloc[t])
    lows = [p.price for p in candidate.pivots if p.kind == "L"]
    highs = [p.price for p in candidate.pivots if p.kind == "H"]
    if candidate.direction == "BUY":
        sl = min(lows) - SL_BUFFER_ATR * atr_t
        if candidate.pattern_id in (7, 8, 9):
            tp = entry + abs(candidate.breakout_level - candidate.extreme)
        else:
            tp = entry + candidate.pattern_height
    else:
        sl = max(highs) + SL_BUFFER_ATR * atr_t
        if candidate.pattern_id in (10, 11, 12):
            tp = entry - abs(candidate.extreme - candidate.breakout_level)
        else:
            tp = entry - candidate.pattern_height
    name, direction = PATTERNS[candidate.pattern_id]
    raw = dict(candidate.raw)
    raw["entry_rule"] = "bar_close"
    raw["signal_bar_index"] = t
    raw["atr_at_signal"] = _round(atr_t)
    return Signal(
        pattern_id=candidate.pattern_id,
        pattern_name=name,
        direction=direction,
        pair=pair,
        timeframe=timeframe,
        signal_ts=signal_ts,
        detection_ts=detection_pivot.ts,
        entry_px=_round(entry),
        sl_px=_round(sl),
        tp_px=_round(tp),
        pattern_height_atr=_round(candidate.pattern_height / atr_det),
        duration_bars=candidate.pivots[-1].idx - candidate.pivots[0].idx,
        atr_at_detection=_round(atr_det),
        pivot_anchor_ts=candidate.anchor.ts,
        pivot_opposite_ts=candidate.opposite.ts,
        pivot_count=len(candidate.pivots),
        confidence_score=_round(candidate.confidence),
        raw_geometry_json=json.dumps(raw, sort_keys=True, separators=(",", ":")),
    )


def detect_chart_patterns(df: pd.DataFrame, pair: str = "USD_JPY", timeframe: str = "M5") -> list[Signal]:
    ohlc = normalize_ohlc(df)
    close = ohlc["close"].to_numpy(float)
    atr = compute_atr_wilder(ohlc)
    pivots = find_swing_pivots(ohlc)
    by_confirm: dict[int, list[Pivot]] = {}
    for p in pivots:
        by_confirm.setdefault(p.confirm_idx, []).append(p)

    recent: list[Pivot] = []
    fired: set[tuple[int, str, str]] = set()
    signals: list[Signal] = []
    for t in range(len(ohlc)):
        if t in by_confirm:
            recent.extend(by_confirm[t])
            recent.sort(key=lambda p: p.idx)
            if len(recent) > 80:
                recent = recent[-80:]
        atr_t = float(atr.iloc[t])
        if not math.isfinite(atr_t) or atr_t <= 0:
            continue
        for cand in build_candidates(recent, t, atr_t, close):
            if t < max(p.confirm_idx for p in cand.pivots):
                continue
            if t - max(p.confirm_idx for p in cand.pivots) > POST_DETECTION_MAX_BARS:
                continue
            key = (cand.pattern_id, cand.anchor.ts, cand.opposite.ts)
            if key in fired:
                continue
            if candidate_triggers(cand, close[t], atr_t):
                fired.add(key)
                signals.append(candidate_to_signal(cand, ohlc, t, atr, pair, timeframe))
    signals.sort(key=lambda s: (s.signal_ts, s.pattern_id, s.pivot_anchor_ts, s.pivot_opposite_ts))
    return signals


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def insert_signals(conn: sqlite3.Connection, signals: Iterable[Signal]) -> int:
    ensure_schema(conn)
    rows = [s.__dict__ for s in signals]
    before = conn.total_changes
    conn.executemany(
        """
        INSERT OR IGNORE INTO chart_pattern_signals (
            pattern_id, pattern_name, direction, pair, timeframe, signal_ts, detection_ts,
            entry_px, sl_px, tp_px, pattern_height_atr, duration_bars, atr_at_detection,
            pivot_anchor_ts, pivot_opposite_ts, pivot_count, confidence_score, raw_geometry_json
        ) VALUES (
            :pattern_id, :pattern_name, :direction, :pair, :timeframe, :signal_ts, :detection_ts,
            :entry_px, :sl_px, :tp_px, :pattern_height_atr, :duration_bars, :atr_at_detection,
            :pivot_anchor_ts, :pivot_opposite_ts, :pivot_count, :confidence_score, :raw_geometry_json
        )
        """,
        rows,
    )
    conn.commit()
    return conn.total_changes - before


def synthetic_pattern_df(pattern_id: int) -> pd.DataFrame:
    """Deterministic OHLC fixtures that exercise each LOCKED geometry."""
    base = 100.0
    if pattern_id == 1:
        pts = [(0, base), (15, 101.0), (25, 99.2), (35, 101.02), (45, 99.7), (55, 101.0), (61, 101.45)]
    elif pattern_id == 2:
        pts = [(0, base), (15, 101.0), (25, 99.0), (35, 101.4), (45, 100.4), (55, 101.7), (61, 102.1)]
    elif pattern_id == 3:
        pts = [(0, base), (20, 103.4), (30, 103.0), (38, 103.25), (46, 102.8), (54, 103.05), (60, 103.55)]
    elif pattern_id == 4:
        pts = [(0, base + 1), (15, 100.0), (25, 101.8), (35, 99.98), (45, 101.3), (55, 100.0), (61, 99.55)]
    elif pattern_id == 5:
        pts = [(0, base + 2), (15, 101.0), (25, 103.0), (35, 100.6), (45, 101.6), (55, 100.3), (61, 99.9)]
    elif pattern_id == 6:
        pts = [(0, base + 3.6), (20, 100.0), (30, 100.4), (38, 100.15), (46, 100.6), (54, 100.35), (60, 99.85)]
    elif pattern_id == 7:
        pts = [(0, base + 1), (15, 99.0), (30, 101.2), (45, 99.05), (55, 101.55)]
    elif pattern_id == 8:
        pts = [(0, base + 1), (12, 99.0), (24, 101.2), (36, 99.04), (48, 101.25), (60, 98.98), (68, 101.6)]
    elif pattern_id == 9:
        pts = [(0, base + 1), (12, 99.2), (24, 101.25), (36, 98.4), (48, 101.35), (60, 99.25), (68, 101.7)]
    elif pattern_id == 10:
        pts = [(0, base), (15, 101.0), (30, 98.8), (45, 100.95), (55, 98.45)]
    elif pattern_id == 11:
        pts = [(0, base), (12, 101.0), (24, 98.8), (36, 100.96), (48, 98.75), (60, 101.02), (68, 98.4)]
    elif pattern_id == 12:
        pts = [(0, base), (12, 100.8), (24, 98.75), (36, 101.6), (48, 98.65), (60, 100.75), (68, 98.3)]
    else:
        raise ValueError(pattern_id)

    n = max(i for i, _ in pts) + 10
    x = np.arange(n)
    xp = np.array([i for i, _ in pts], dtype=float)
    fp = np.array([p for _, p in pts], dtype=float)
    close = np.interp(x, xp, fp)
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) + 0.025
    low = np.minimum(open_, close) - 0.025
    ts = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC")
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=ts)
    # Make declared turning points unambiguous strict pivots.
    for j in range(1, len(pts) - 1):
        i, p = pts[j]
        is_high = p > pts[j - 1][1] and p > pts[j + 1][1]
        is_low = p < pts[j - 1][1] and p < pts[j + 1][1]
        if is_high:
            df.iloc[i, df.columns.get_loc("high")] = p + 0.05
            df.iloc[i, df.columns.get_loc("close")] = p - 0.01
        if is_low:
            df.iloc[i, df.columns.get_loc("low")] = p - 0.05
            df.iloc[i, df.columns.get_loc("close")] = p + 0.01
    return df


def self_test() -> int:
    ok = True
    for pid in range(1, 13):
        df = synthetic_pattern_df(pid)
        hits = [s for s in detect_chart_patterns(df, "USD_JPY", "M5") if s.pattern_id == pid]
        if hits:
            first = hits[0]
            print(f"pattern {pid:02d} {first.pattern_name:24s} HIT {first.signal_ts} entry={first.entry_px:.5f} sl={first.sl_px:.5f} tp={first.tp_px:.5f}")
        else:
            ok = False
            print(f"pattern {pid:02d} {PATTERNS[pid][0]:24s} MISS")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
