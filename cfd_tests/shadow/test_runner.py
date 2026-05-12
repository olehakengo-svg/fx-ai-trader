"""runner: integration of cursor → fetch → replay → persist → advance."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

from cfd_trader.audit.oanda_audit import (
    init_db,
    query_live,
    query_shadow,
    query_unrouted,
)
from cfd_trader.audit.queries import count_shadow
from cfd_trader.broker.protocol import BrokerOrderResult
from cfd_trader.shadow.runner import run_shadow_cycle
from cfd_trader.shadow.state import init_state_table, get_cursor

import cfd_trader.strategies.ported.orb_ny_open_short  # registers strategy  # noqa: F401


def _make_breakdown_day() -> pd.DataFrame:
    times = pd.to_datetime(
        pd.date_range("2026-05-11T14:30:00Z", periods=90, freq="5min", tz="UTC")
    )
    closes = [5005.0] * 6 + [4998.0] + [4995.0] * 83
    df = pd.DataFrame({
        "time": times, "open": closes,
        "high": [c + 1.0 for c in closes], "low": [c - 1.0 for c in closes],
        "close": closes, "volume": [10] * 90, "complete": [True] * 90,
    })
    for i in range(6):
        df.at[i, "high"] = 5010.0
        df.at[i, "low"]  = 5000.0
        df.at[i, "close"] = 5005.0
    return df


def test_run_shadow_cycle_writes_audit_and_advances_cursor(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_db(str(db))
    init_state_table(str(db))

    fake_client = MagicMock()
    fake_client.get_candles.return_value = _make_breakdown_day()

    n_new = run_shadow_cycle(
        db_path=str(db),
        oanda_client=fake_client,
        instrument="SPX500_USD",
        granularity="M5",
        strategy_name="orb_ny_open_short",
        bonferroni_m=2,
        selection_reason="short_only_post_hoc",
    )
    assert n_new == 1
    assert count_shadow(str(db), strategy_name="orb_ny_open_short") == 1
    cursor = get_cursor(str(db), "orb_ny_open_short")
    assert cursor is not None
    assert "2026-05-11" in cursor


def test_run_shadow_cycle_is_idempotent_no_new_candles(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_db(str(db))
    init_state_table(str(db))

    fake_client = MagicMock()
    fake_client.get_candles.return_value = _make_breakdown_day()

    run_shadow_cycle(
        db_path=str(db), oanda_client=fake_client, instrument="SPX500_USD",
        granularity="M5", strategy_name="orb_ny_open_short",
        bonferroni_m=2, selection_reason="short_only_post_hoc",
    )
    # Simulate "no new candles since cursor" on the second call:
    fake_client.get_candles.return_value = pd.DataFrame(columns=[
        "time","open","high","low","close","volume","complete",
    ])
    n_new_2 = run_shadow_cycle(
        db_path=str(db), oanda_client=fake_client, instrument="SPX500_USD",
        granularity="M5", strategy_name="orb_ny_open_short",
        bonferroni_m=2, selection_reason="short_only_post_hoc",
    )
    assert n_new_2 == 0
    assert count_shadow(str(db), strategy_name="orb_ny_open_short") == 1


class _FakeBroker:
    """Records every call; returns a queued BrokerOrderResult."""

    def __init__(self, result: BrokerOrderResult) -> None:
        self.result = result
        self.calls: list[dict] = []

    def place_market_order(self, *, instrument, side, units, signal_price):
        self.calls.append({
            "instrument": instrument, "side": side,
            "units": units, "signal_price": signal_price,
        })
        return self.result


def test_runner_without_broker_writes_shadow_only(tmp_path: Path) -> None:
    """Backward-compat: omit broker → no LIVE rows ever written."""
    db = tmp_path / "t.db"
    init_db(str(db))
    init_state_table(str(db))

    fake_client = MagicMock()
    fake_client.get_candles.return_value = _make_breakdown_day()

    run_shadow_cycle(
        db_path=str(db), oanda_client=fake_client, instrument="SPX500_USD",
        granularity="M5", strategy_name="orb_ny_open_short",
        bonferroni_m=2, selection_reason="short_only_post_hoc",
    )
    assert len(query_shadow(str(db))) == 1
    assert len(query_live(str(db))) == 0
    assert len(query_unrouted(str(db))) == 0


def test_runner_with_filled_broker_writes_shadow_and_live(tmp_path: Path) -> None:
    """live_gate=True + broker filled → one SHADOW row + one LIVE row."""
    db = tmp_path / "t.db"
    init_db(str(db))
    init_state_table(str(db))

    fake_client = MagicMock()
    fake_client.get_candles.return_value = _make_breakdown_day()

    broker = _FakeBroker(BrokerOrderResult(
        status="filled",
        broker_trade_id="MT5#84212391",
        fill_price=4998.5,
        reject_reason=None,
        raw={"deal": 84212391},
    ))

    run_shadow_cycle(
        db_path=str(db), oanda_client=fake_client, instrument="SPX500_USD",
        granularity="M5", strategy_name="orb_ny_open_short",
        bonferroni_m=2, selection_reason="short_only_post_hoc",
        broker=broker, live_gate=lambda _t: True,
    )

    shadow = query_shadow(str(db))
    live = query_live(str(db))
    unrouted = query_unrouted(str(db))

    assert len(shadow) == 1
    assert shadow[0].mode == "SHADOW"
    assert shadow[0].broker_trade_id is None
    # The shadow row still carries its replayed exit fields for cum-PnL.
    assert shadow[0].exit_price is not None
    assert shadow[0].pnl_point is not None

    assert len(live) == 1
    assert live[0].mode == "LIVE"
    assert live[0].broker_trade_id == "MT5#84212391"
    assert live[0].bridge_status == "filled"
    # entry_price MUST be the broker fill, not the strategy signal price.
    assert live[0].entry_price == 4998.5
    # LIVE rows are open positions — no exit fields yet.
    assert live[0].exit_ts is None
    assert live[0].exit_price is None
    # Broker context survives in extra_json for forensics.
    extra = json.loads(live[0].extra_json)
    assert extra["broker"]["status"] == "filled"
    assert extra["broker"]["broker_trade_id"] == "MT5#84212391"
    # Existing keys (bonferroni_m, selection_reason) must still be there.
    assert extra["bonferroni_m"] == 2

    assert len(unrouted) == 0
    assert len(broker.calls) == 1


def test_runner_with_rejected_broker_writes_shadow_and_unrouted(tmp_path: Path) -> None:
    """live_gate=True + broker rejected → SHADOW + UNROUTED (NOT LIVE)."""
    db = tmp_path / "t.db"
    init_db(str(db))
    init_state_table(str(db))

    fake_client = MagicMock()
    fake_client.get_candles.return_value = _make_breakdown_day()

    broker = _FakeBroker(BrokerOrderResult(
        status="rejected",
        broker_trade_id=None,
        fill_price=None,
        reject_reason="TRADE_RETCODE_REJECT",
        raw={},
    ))

    run_shadow_cycle(
        db_path=str(db), oanda_client=fake_client, instrument="SPX500_USD",
        granularity="M5", strategy_name="orb_ny_open_short",
        bonferroni_m=2, selection_reason="short_only_post_hoc",
        broker=broker, live_gate=lambda _t: True,
    )

    assert len(query_shadow(str(db))) == 1
    assert len(query_live(str(db))) == 0  # critical: rejected ≠ live
    unrouted = query_unrouted(str(db))
    assert len(unrouted) == 1
    assert unrouted[0].mode == "LIVE"
    assert unrouted[0].bridge_status == "rejected"
    assert unrouted[0].broker_trade_id is None

    extra = json.loads(unrouted[0].extra_json)
    assert extra["broker"]["reject_reason"] == "TRADE_RETCODE_REJECT"


def test_runner_skips_broker_when_live_gate_false(tmp_path: Path) -> None:
    """A False live_gate must not call the broker at all."""
    db = tmp_path / "t.db"
    init_db(str(db))
    init_state_table(str(db))

    fake_client = MagicMock()
    fake_client.get_candles.return_value = _make_breakdown_day()

    broker = _FakeBroker(BrokerOrderResult(
        status="filled", broker_trade_id="X", fill_price=1.0,
        reject_reason=None, raw={},
    ))

    run_shadow_cycle(
        db_path=str(db), oanda_client=fake_client, instrument="SPX500_USD",
        granularity="M5", strategy_name="orb_ny_open_short",
        bonferroni_m=2, selection_reason="short_only_post_hoc",
        broker=broker, live_gate=lambda _t: False,
    )

    assert len(query_shadow(str(db))) == 1
    assert len(query_live(str(db))) == 0
    assert len(query_unrouted(str(db))) == 0
    assert len(broker.calls) == 0


def test_runner_return_value_counts_shadow_only(tmp_path: Path) -> None:
    """n_new must reflect SHADOW row count for backward compat with catchup."""
    db = tmp_path / "t.db"
    init_db(str(db))
    init_state_table(str(db))

    fake_client = MagicMock()
    fake_client.get_candles.return_value = _make_breakdown_day()

    broker = _FakeBroker(BrokerOrderResult(
        status="filled", broker_trade_id="MT5#1", fill_price=4998.5,
        reject_reason=None, raw={},
    ))

    n_new = run_shadow_cycle(
        db_path=str(db), oanda_client=fake_client, instrument="SPX500_USD",
        granularity="M5", strategy_name="orb_ny_open_short",
        bonferroni_m=2, selection_reason="short_only_post_hoc",
        broker=broker, live_gate=lambda _t: True,
    )
    # 1 SHADOW + 1 LIVE row, but return value counts only SHADOW.
    assert n_new == 1
