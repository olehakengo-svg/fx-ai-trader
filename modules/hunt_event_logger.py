"""Hunt event logger — sr_anti_hunt_bounce / sr_liquidity_grab 戦略の
発火ごとにイベント情報を JSONL に記録する。

Phase 4 BT および tools/sr_audit.py (Stage A+B) の入力データ源。

Output path: knowledge-base/raw/hunt_events/<YYYY-MM-DD>.jsonl

Each line:
    {
        "entry_time": "2026-04-28T10:32:11.123456+00:00",
        "strategy": "sr_anti_hunt_bounce",
        "instrument": "USD_JPY",
        "direction": "BUY" | "SELL",
        "entry_price": 153.50,
        "hunt_extreme": 153.30,    # SL price = expected hunt boundary
        "opposite_sr": 154.20,     # TP target = next SR
        "sl": 153.30,
        "tp": 154.20,
        "atr_pips": 12.0,
        "side": "support" | "resistance",
        "level": 153.42,           # the SR level that triggered the bounce
        "reversal": null,          # post-hoc: filled by sr_audit / outcome attribution
        "actual_outcome": null,    # "WIN" | "LOSS" | null
        "actual_pnl_pips": null
    }

The `reversal / actual_outcome / actual_pnl_pips` fields are appended later by
`tools/attribute_hunt_outcomes.py` (deferred — runs after demo_trades close).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Resolve project root from this file location:
# modules/hunt_event_logger.py -> ../knowledge-base/raw/hunt_events
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _PROJECT_ROOT / "knowledge-base" / "raw" / "hunt_events"


def _pip_size(instrument: str) -> float:
    return 0.01 if "JPY" in instrument.upper() else 0.0001


def log_hunt_event(
    *,
    strategy: str,
    instrument: str,
    direction: str,
    entry_price: float,
    sl: float,
    tp: float,
    level: float,
    side: str,
    atr_price: float,
    extra: dict | None = None,
) -> bool:
    """Append one hunt event to today's JSONL log.

    Returns True on success, False on failure (logged but does not raise — must
    not affect strategy evaluation path).

    Parameters
    ----------
    atr_price : float
        ATR in price units (not pips). Pips are computed internally.
    extra : dict | None
        Optional additional context (e.g. session, ADX, BB%B). Stored as-is.
    """
    try:
        pip = _pip_size(instrument)
        atr_pips = (atr_price / pip) if pip > 0 else 0.0
        # hunt_extreme = SL = expected wick boundary
        # opposite_sr  = TP target (the audit framework expects "where we'd go on success")
        record = {
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "strategy": strategy,
            "instrument": instrument,
            "direction": direction.upper(),
            "entry_price": float(entry_price),
            "hunt_extreme": float(sl),
            "opposite_sr": float(tp),
            "sl": float(sl),
            "tp": float(tp),
            "atr_pips": round(float(atr_pips), 2),
            "atr_price": float(atr_price),
            "side": side,
            "level": float(level),
            # Filled post-hoc by attribute_hunt_outcomes.py
            "reversal": None,
            "actual_outcome": None,
            "actual_pnl_pips": None,
        }
        if extra:
            for k, v in extra.items():
                if k not in record:  # do not overwrite primary fields
                    record[k] = v

        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).date().isoformat()
        fname = _LOG_DIR / f"{date_str}.jsonl"
        with fname.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        # Never raise — strategy path must not be affected
        try:
            print(f"[hunt_event_logger] write failed: {e}", flush=True)
        except Exception:
            pass
        return False
