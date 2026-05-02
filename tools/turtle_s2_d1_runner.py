"""Daily Turtle System 2 (USDJPY long-only Shadow) runner.

Designed to be invoked once per D1 close (NY 17:00 ≈ 21:00 UTC):

    python3 tools/turtle_s2_d1_runner.py --pair USD_JPY --source render

It is **deliberately decoupled** from the live demo_trader hot loop because
the strategy fires on D1 boundaries, while demo_trader runs M1/M5/H1/H4
ticks. The runner:

1. Loads ~120 D1 bars for the pair (Render API or local parquet).
2. If a trade is already active for the pair (per-pair singleton state on disk),
   reloads the manager and:
     a. evaluates the 20-day exit rule → maybe_close_all
     b. else evaluates the +0.5N pyramid → maybe_add_unit
3. Else, if no trade is active, evaluates :func:`evaluate_d1`. If a signal
   fires, persists unit-1 via :class:`TurtleS2PyramidManager.open_initial`.

State is persisted as JSON under ``data/turtle_s2_state/<pair>.json``.
This file is intentionally tiny (open units + initial signal hash) — the
ground-truth audit trail lives in the trades DB and oanda_audit.

Live promotion is **NOT** automatic: this runner only ever opens Shadow
trades. A separate promotion gate (live shadow N ≥ 80, Bonferroni p < 0.10,
OOS PF maintained) is responsible for raising the strategy out of Shadow.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional, Sequence

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from modules.turtle_s2_pyramid import TurtleS2PyramidManager, UnitState  # noqa: E402
from strategies.daytrade.turtle_s2_donchian import (  # noqa: E402
    SUPPORTED_PAIRS,
    evaluate_d1,
    is_exit_signal,
)


STATE_DIR = REPO_ROOT / "data" / "turtle_s2_state"


def _state_path(pair: str) -> Path:
    return STATE_DIR / f"{pair}.json"


def _load_state(pair: str) -> Optional[dict]:
    p = _state_path(pair)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def _save_state(pair: str, manager: TurtleS2PyramidManager) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "pair": manager.pair,
        "max_units": manager.max_units,
        "atr_n": manager.atr_n,
        "units": [
            {
                **asdict(u),
                "bar_time": str(u.bar_time),
            }
            for u in manager.units
        ],
    }
    _state_path(pair).write_text(json.dumps(payload, indent=2))


def _clear_state(pair: str) -> None:
    p = _state_path(pair)
    if p.exists():
        p.unlink()


def _load_d1_dataframe(pair: str, source: str, lookback: int = 120) -> pd.DataFrame:
    """Load the most recent ``lookback`` D1 bars for ``pair``.

    For now supports the local parquet sidecar that the BT pipeline produces
    at ``data/{PAIR}_d1.parquet``. The Render path is intentionally a TODO:
    pulling D1 history through the bridge belongs to a follow-up because it
    needs a new endpoint contract; the runner falls through to parquet when
    ``source != "render"``.
    """
    parquet_path = REPO_ROOT / "data" / f"{pair}_d1.parquet"
    if not parquet_path.exists():
        raise FileNotFoundError(
            f"D1 cache missing: {parquet_path}. Run the Wave-1 BT data fetch "
            "(tools/bt/s2_turtle_donchian.py) first to populate the cache."
        )
    df = pd.read_parquet(parquet_path)
    if "timestamp" in df.columns and not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index("timestamp")
    df = df.sort_index().tail(lookback)
    return df


def run_once(pair: str,
             source: str,
             *,
             intervention_days: Sequence[pd.Timestamp] = (),
             open_trade_fn=None,
             close_trade_fn=None,
             dry_run: bool = False) -> dict:
    """Execute one D1 evaluation cycle.

    Returns a result dict for logging / audit:
        {"action": "open_initial" | "add_unit" | "exit_all" | "noop",
         "units": [...], "pair": ..., "bar_time": ...}
    """
    if pair not in SUPPORTED_PAIRS:
        return {"action": "noop", "reason": "unsupported_pair", "pair": pair}

    df = _load_d1_dataframe(pair, source)

    # Default IO: real demo_db.open_trade / close_trade. Tests inject mocks.
    if open_trade_fn is None or close_trade_fn is None:
        if dry_run:
            open_trade_fn = _dry_open
            close_trade_fn = _dry_close
        else:
            from modules.demo_db import DemoDB  # noqa: WPS433 (deferred import)
            db = DemoDB()
            open_trade_fn = db.open_trade
            close_trade_fn = db.close_trade

    state = _load_state(pair)
    manager = TurtleS2PyramidManager(
        pair=pair,
        open_trade_fn=open_trade_fn,
        close_trade_fn=close_trade_fn,
        intervention_days=tuple(intervention_days),
    )

    # Re-hydrate active state if any
    if state and state.get("units"):
        manager.units = [
            UnitState(
                idx=u["idx"],
                entry_price=u["entry_price"],
                sl=u["sl"],
                atr_n_at_entry=u["atr_n_at_entry"],
                bar_time=pd.Timestamp(u["bar_time"]),
                entry_type=u["entry_type"],
                db_trade_id=u.get("db_trade_id"),
            )
            for u in state["units"]
        ]
        # initial_signal is partially restored from state metadata so
        # max_units & atr_n properties still resolve.
        from strategies.daytrade.turtle_s2_donchian import TurtleS2Signal
        first = manager.units[0]
        manager.initial_signal = TurtleS2Signal(
            signal="BUY",
            entry=first.entry_price,
            sl=first.sl,
            tp=first.entry_price + 20 * state["atr_n"],
            atr_n=state["atr_n"],
            pyramid_step=0.5 * state["atr_n"],
            max_units=state["max_units"],
            pair=pair,
            bar_time=first.bar_time,
            reasons=[],
        )

    # Active trade → check exit / pyramid
    if manager.is_active:
        closed = manager.maybe_close_all(df)
        if closed:
            _clear_state(pair)
            return {
                "action": "exit_all",
                "pair": pair,
                "bar_time": str(df.index[-1]),
                "closed_units": [u.idx for u in closed],
            }
        added = manager.maybe_add_unit(df)
        if added is not None:
            _save_state(pair, manager)
            return {
                "action": "add_unit",
                "pair": pair,
                "bar_time": str(df.index[-1]),
                "unit_idx": added.idx,
            }
        return {"action": "noop", "pair": pair, "bar_time": str(df.index[-1])}

    # No active trade → look for fresh breakout
    sig = evaluate_d1(df, pair=pair, intervention_days=intervention_days)
    if sig is None:
        return {"action": "noop", "pair": pair, "bar_time": str(df.index[-1])}
    manager.open_initial(sig)
    _save_state(pair, manager)
    return {
        "action": "open_initial",
        "pair": pair,
        "bar_time": str(sig.bar_time),
        "entry": sig.entry,
        "sl": sig.sl,
        "atr_n": sig.atr_n,
        "max_units": sig.max_units,
    }


# ---------- dry-run stubs --------------------------------------------------
_DRY_TRADE_ID_COUNTER = {"v": 0}


def _dry_open(**kwargs) -> int:
    _DRY_TRADE_ID_COUNTER["v"] += 1
    print(f"[turtle_s2_d1_runner DRY] open: {kwargs}")
    return _DRY_TRADE_ID_COUNTER["v"]


def _dry_close(**kwargs) -> None:
    print(f"[turtle_s2_d1_runner DRY] close: {kwargs}")


# ---------- entrypoint -----------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pair", default="USD_JPY", choices=sorted(SUPPORTED_PAIRS))
    p.add_argument("--source", default="parquet", choices=["parquet", "render"])
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would happen without writing to demo_db.")
    p.add_argument("--intervention-day", action="append", default=[],
                   help="ISO date (e.g. 2024-07-12) — can be repeated.")
    args = p.parse_args(argv)

    intervention_days = [pd.Timestamp(d) for d in args.intervention_day]
    result = run_once(
        pair=args.pair,
        source=args.source,
        intervention_days=intervention_days,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
