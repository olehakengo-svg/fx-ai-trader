"""Round Number Utility — RNR (Round Number Repulsion / Magnetism).

ストップ・指値が集中する psychological round numbers (.000 / .500) からの距離と
方向を計算するユーティリティ。各戦略の SL/TP/confidence 配置を round-number-aware に。

依拠: Osler 2003, Schmidt-Werner 2002, Mitchell 2001
- .000 (whole-number) は最強の magnet/repulsion
- .500 (half-number) は次点
- .200/.800 は弱い (FX 特有)

戦略への注入例:
  from modules.round_number import nearest_round, distance_to_round, shift_tp_inside
  # SR 戦略の SL placement で round-number 越えにバッファ追加
  rn_dist = distance_to_round(level, pip_size, scope="major")
  if rn_dist < 5 * pip_size:
      sl_buffer *= 1.5  # round number 近傍の SR は更に深い SL

  # MR 戦略の TP placement
  tp_safe = shift_tp_inside(tp_raw, signal, pip_size, shift_pips=3)
"""
from __future__ import annotations
from typing import Literal, Optional


Scope = Literal["major", "all"]


def pip_size(instrument_or_pip: str | float) -> float:
    """Resolve pip size: 0.01 for JPY pairs, 0.0001 for non-JPY, or pass float through."""
    if isinstance(instrument_or_pip, (int, float)):
        return float(instrument_or_pip)
    return 0.01 if "JPY" in str(instrument_or_pip).upper() else 0.0001


def nearest_round(price: float, pip: float,
                   scope: Scope = "major") -> tuple[float, str, float]:
    """Find the nearest round-number magnet to `price`.

    Args:
        price: current price
        pip: pip size (0.01 for JPY, 0.0001 for others)
        scope: "major" (only .000 / .500), "all" (also .200 / .800)

    Returns:
        (round_price, round_type, distance_in_pip)
        round_type: "00" (whole), "50" (half), "20"/"80" (other)
    """
    pip_units = price / pip   # e.g. 150.000 / 0.01 = 15000

    if scope == "major":
        candidates_mod = [(0, "00"), (50, "50")]
    else:
        candidates_mod = [(0, "00"), (50, "50"), (20, "20"), (80, "80")]

    best_dist = float("inf")
    best_round_pip_units = pip_units
    best_type = "00"
    for mod, rt in candidates_mod:
        # Floor and ceiling candidates that match this mod
        cycle = 100
        base = (pip_units // cycle) * cycle
        cands = [base + mod, base + mod + cycle, base + mod - cycle]
        for c in cands:
            d = abs(pip_units - c)
            if d < best_dist:
                best_dist = d
                best_round_pip_units = c
                best_type = rt

    return (best_round_pip_units * pip, best_type, best_dist)


def distance_to_round(price: float, pip: float,
                       scope: Scope = "major") -> float:
    """Pip distance to nearest round-number magnet."""
    _, _, dist_pip = nearest_round(price, pip, scope=scope)
    return dist_pip


def is_near_round(price: float, pip: float,
                   threshold_pips: float = 5.0,
                   scope: Scope = "major") -> bool:
    """Check if price is within `threshold_pips` of a round number."""
    return distance_to_round(price, pip, scope=scope) < threshold_pips


def shift_tp_inside(tp_raw: float, signal: str, pip: float,
                     shift_pips: float = 3.0,
                     scope: Scope = "major") -> float:
    """Shift TP `shift_pips` toward entry if it's near a round-number resistance.

    Reason: round numbers attract opposing limit orders → TP just before round
    number gets filled with higher probability than TP at or beyond it.

    BUY: shift down (closer to entry)
    SELL: shift up (closer to entry)
    """
    rn_price, _, dist_pip = nearest_round(tp_raw, pip, scope=scope)
    if dist_pip > shift_pips * 2:
        return tp_raw  # Far from round number — no shift needed

    # If TP is at or beyond a round number that opposes the trade, pull back
    if signal == "BUY":
        # Going up; TP is resistance. Don't TP at or above round number;
        # place just below it.
        if tp_raw >= rn_price:
            return rn_price - shift_pips * pip
    else:  # SELL
        if tp_raw <= rn_price:
            return rn_price + shift_pips * pip
    return tp_raw


def expand_sl_for_round(sl_raw: float, level: float, signal: str,
                         pip: float, scope: Scope = "major",
                         expand_factor: float = 1.5,
                         atr: float = 0.0) -> float:
    """Expand SL distance when the SR `level` itself sits on a round number.

    Reason: round-number SR levels attract more stop hunting → need more buffer.
    Used by sr_anti_hunt_bounce / sr_liquidity_grab when level near round number.

    Args:
        sl_raw: current SL price
        level: SR level (anchor)
        signal: "BUY" or "SELL"
        expand_factor: multiplier on existing SL distance (default 1.5x)
        atr: optional ATR for additional expansion floor

    Returns:
        Adjusted SL price (further from entry).
    """
    rn_dist = distance_to_round(level, pip, scope=scope)
    if rn_dist > 5.0:  # Not near round number — no expansion
        return sl_raw

    sl_dist = abs(sl_raw - level)
    new_sl_dist = sl_dist * expand_factor
    if atr > 0:
        new_sl_dist = max(new_sl_dist, sl_dist + 0.3 * atr)

    if signal == "BUY":
        return level - new_sl_dist
    else:
        return level + new_sl_dist


def round_confluence_boost(level: float, pip: float,
                            scope: Scope = "major",
                            threshold_pips: float = 3.0) -> float:
    """Score boost (0.0-1.0) if `level` is near a major round number.

    Used to upweight SR/Fib confluence at psychological levels.
    Returns 1.0 if exact, scales linearly to 0 at threshold_pips distance.
    """
    rn_dist = distance_to_round(level, pip, scope=scope)
    if rn_dist >= threshold_pips:
        return 0.0
    return max(0.0, 1.0 - rn_dist / threshold_pips)
