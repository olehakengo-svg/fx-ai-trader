"""Shadow runner: orchestrates fetch → replay → persist → advance.

I/O-aware. The catch-up script imports this; tests mock the oanda_client.

Live-routing extension (Section 5.D):
- ``broker`` and ``live_gate`` are both optional. When either is None,
  the runner is SHADOW-only — every replayed trade writes one row with
  is_shadow=1, broker_trade_id=NULL.
- When both are provided, the runner ALSO calls
  ``broker.place_market_order`` for every trade whose ``live_gate``
  returns True, and writes a SECOND audit row marked is_shadow=0. That
  row carries a broker_trade_id iff the broker actually accepted the
  order (then it lands in the LIVE bucket); otherwise broker_trade_id
  stays NULL and the row lands in the UNROUTED bucket for forensics.
- The shadow row is NEVER skipped, even when the order goes live. The
  shadow time series stays unbroken so Kelly / Wilson keep updating
  on the full underlying signal stream.
"""
from __future__ import annotations

import json
from typing import Callable

import pandas as pd

from cfd_trader.audit.oanda_audit import init_db, record_entry, OandaAuditEntry
from cfd_trader.broker.protocol import BrokerClient
from cfd_trader.shadow.replay import replay_strategy
from cfd_trader.shadow.state import get_cursor, init_state_table, advance_cursor


def _to_rfc3339(ts_str: str) -> str:
    """Normalize a pandas-str timestamp to RFC3339 (`YYYY-MM-DDTHH:MM:SSZ`).

    OANDA's v20 candles API rejects the pandas `str(Timestamp)` form
    (`2026-05-11 07:15:00+00:00`); only ISO-8601/RFC3339 is accepted.
    """
    return pd.Timestamp(ts_str).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


# A live_gate is a pure predicate over the replayed trade row.
# It decides: "Given this signal, should we fire it through the broker
# right now?" The runner does NOT impose freshness or risk semantics —
# those belong to the gate. Tests inject ``lambda _t: True/False`` so
# we have one place to think about live-eligibility per deployment.
LiveGate = Callable[[pd.Series], bool]


def run_shadow_cycle(
    *,
    db_path: str,
    oanda_client,             # duck-typed; needs .get_candles(instrument, granularity, from_iso=...)
    instrument: str,
    granularity: str,
    strategy_name: str,
    bonferroni_m: int,
    selection_reason: str,
    broker: BrokerClient | None = None,
    live_gate: LiveGate | None = None,
) -> int:
    """Fetch new candles, replay, persist as is_shadow=1.

    Returns the count of NEW SHADOW audit rows written this cycle. The
    return value does NOT include LIVE rows — those are visible via
    ``query_live(db_path)``. Keeping the return value SHADOW-only
    preserves backward compatibility with existing callers that read
    "number of new shadow trades".
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

    live_routing_enabled = broker is not None and live_gate is not None

    n_new = 0
    for _, t in trades.iterrows():
        # Always write the SHADOW row first. The shadow time series is
        # the estimator for promotion gates and must stay unbroken.
        shadow_entry = OandaAuditEntry(
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
            broker_trade_id=None,
        )
        record_entry(db_path, shadow_entry)
        n_new += 1

        if not live_routing_enabled:
            continue
        if not live_gate(t):  # type: ignore[misc]
            continue

        # Route to broker. The result drives both broker_trade_id and
        # bridge_status; the protocol invariant (filled → ticket present)
        # is enforced at construction time of BrokerOrderResult.
        result = broker.place_market_order(  # type: ignore[union-attr]
            instrument=instrument,
            side=str(t["side"]),
            units=int(t["units"]),
            signal_price=float(t["entry_price"]),
        )

        live_entry = OandaAuditEntry(
            ts=str(t["entry_time"]), instrument=instrument,
            strategy_name=strategy_name,
            bridge_status="filled" if result.status == "filled" else "rejected",
            side=str(t["side"]), units=int(t["units"]),
            signal_price=float(t["entry_price"]),
            # Use the broker's fill_price when present; otherwise fall
            # back to the strategy's intended entry so the row is still
            # well-formed for downstream tooling.
            entry_price=(
                float(result.fill_price)
                if result.fill_price is not None
                else float(t["entry_price"])
            ),
            is_shadow=0, mode="LIVE",
            extra_json=_live_extra(result, base_extra=extra),
            # Exit fields are NOT populated for LIVE rows: the live
            # position is still open as far as the broker is concerned.
            # A separate reconciliation pass closes the row later.
            exit_ts=None, exit_price=None, pnl_point=None,
            broker_trade_id=result.broker_trade_id,
        )
        record_entry(db_path, live_entry)

    if new_cursor is not None:
        try:
            advance_cursor(db_path, strategy_name, _to_rfc3339(new_cursor))
        except ValueError:
            pass  # cursor unchanged or older — fine
    return n_new


def _live_extra(result, *, base_extra: str) -> str:
    """Merge the broker's reject_reason / raw debug into extra_json.

    The base extra (bonferroni_m, selection_reason) stays as the
    top-level object so existing readers keep working; broker metadata
    nests under a single ``broker`` key.
    """
    try:
        base = json.loads(base_extra)
    except (ValueError, TypeError):
        base = {}
    base["broker"] = {
        "status": result.status,
        "broker_trade_id": result.broker_trade_id,
        "fill_price": result.fill_price,
        "reject_reason": result.reject_reason,
    }
    return json.dumps(base, ensure_ascii=False)
