import sqlite3

import pytest

from modules.demo_trader import DemoTrader
from tools.backfill_stale_signal_slippage import (
    apply_backfill,
    find_candidates,
    signed_slippage_pips,
)


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """CREATE TABLE demo_trades (
            trade_id TEXT PRIMARY KEY,
            instrument TEXT,
            entry_type TEXT,
            direction TEXT,
            entry_time TEXT,
            entry_price REAL,
            signal_price REAL,
            slippage_pips REAL,
            oanda_trade_id TEXT
        )"""
    )
    return conn


def test_signed_slippage_matches_live_formula_for_buy_and_sell():
    assert signed_slippage_pips("BUY", 1.33843, 1.34245, "GBP_USD") == pytest.approx(-40.2)
    assert signed_slippage_pips("SELL", 1.34245, 1.33843, "GBP_USD") == pytest.approx(-40.2)


def test_find_candidates_and_apply_backfill_without_oanda():
    conn = _conn()
    conn.execute(
        "INSERT INTO demo_trades VALUES (?,?,?,?,?,?,?,?,?)",
        (
            "T-1",
            "GBP_USD",
            "wick_imbalance_reversion",
            "BUY",
            "2026-06-10T17:46:20+00:00",
            1.33843,
            1.34245,
            -40.2,
            "",
        ),
    )
    conn.execute(
        "INSERT INTO demo_trades VALUES (?,?,?,?,?,?,?,?,?)",
        (
            "T-OK",
            "GBP_USD",
            "wick_imbalance_reversion",
            "BUY",
            "2026-06-11T07:16:07+00:00",
            1.33851,
            1.33843,
            0.8,
            "508698",
        ),
    )

    assert find_candidates(conn) == []
    candidates = find_candidates(
        conn,
        strategy="wick_imbalance_reversion",
        instrument="GBP_USD",
        include_no_oanda=True,
    )
    assert [c.trade_id for c in candidates] == ["T-1"]

    assert apply_backfill(conn, candidates) == 1
    row = conn.execute(
        "SELECT signal_price, slippage_pips FROM demo_trades WHERE trade_id='T-1'"
    ).fetchone()
    assert row == pytest.approx((1.33843, 0.0))


def test_rebase_tp_to_current_price_preserves_distance():
    assert DemoTrader._rebase_tp_to_current_price(
        signal="BUY",
        current_price=1.33843,
        signal_price=1.34245,
        tp=1.34395,
    ) == pytest.approx(1.33993)
    assert DemoTrader._rebase_tp_to_current_price(
        signal="SELL",
        current_price=1.33843,
        signal_price=1.34245,
        tp=1.34095,
    ) == pytest.approx(1.33693)
