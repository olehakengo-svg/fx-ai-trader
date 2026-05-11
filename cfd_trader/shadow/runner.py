"""Shadow runner: orchestrates fetch → replay → persist → advance.

I/O-aware. The catch-up script imports this; tests mock the oanda_client.
"""
from __future__ import annotations

import json

import pandas as pd

from cfd_trader.audit.oanda_audit import init_db, record_entry, OandaAuditEntry
from cfd_trader.shadow.replay import replay_strategy
from cfd_trader.shadow.state import get_cursor, init_state_table, advance_cursor


def _to_rfc3339(ts_str: str) -> str:
    """Normalize a pandas-str timestamp to RFC3339 (`YYYY-MM-DDTHH:MM:SSZ`).

    OANDA's v20 candles API rejects the pandas `str(Timestamp)` form
    (`2026-05-11 07:15:00+00:00`); only ISO-8601/RFC3339 is accepted.
    """
    return pd.Timestamp(ts_str).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def run_shadow_cycle(
    *,
    db_path: str,
    oanda_client,             # duck-typed; needs .get_candles(instrument, granularity, from_iso=...)
    instrument: str,
    granularity: str,
    strategy_name: str,
    bonferroni_m: int,
    selection_reason: str,
) -> int:
    """Fetch new candles, replay, persist as is_shadow=1.

    Returns the count of NEW audit rows written this cycle.
    """
    init_db(db_path)
    init_state_table(db_path)

    cursor = get_cursor(db_path, strategy_name)
    candles = oanda_client.get_candles(
        instrument, granularity, from_iso=cursor,
    )
    if len(candles) == 0:
        return 0

    trades, new_cursor = replay_strategy(
        strategy_name=strategy_name, candles=candles,
    )
    extra = json.dumps(
        {"bonferroni_m": bonferroni_m, "selection_reason": selection_reason},
        ensure_ascii=False,
    )

    n_new = 0
    for _, t in trades.iterrows():
        entry = OandaAuditEntry(
            ts=str(t["entry_time"]), instrument=instrument,
            strategy_name=strategy_name, bridge_status="filled",
            side=str(t["side"]), units=int(t["units"]),
            signal_price=float(t["entry_price"]),
            entry_price=float(t["entry_price"]),
            is_shadow=1, mode="SHADOW",
            extra_json=extra,
            exit_ts=str(t["exit_time"]),
            exit_price=float(t["exit_price"]),
            pnl_point=float(t["pnl_point"]),
        )
        record_entry(db_path, entry)
        n_new += 1

    if new_cursor is not None:
        try:
            advance_cursor(db_path, strategy_name, _to_rfc3339(new_cursor))
        except ValueError:
            pass  # cursor unchanged or older — fine
    return n_new
