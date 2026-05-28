from __future__ import annotations

import sys
from pathlib import Path

from modules import data as data_mod

sys.path.append(str(Path(__file__).resolve().parent))
from edge_cell_test_helpers import edge_cfg, make_trader, session_time_bias_sell_sig


def test_e2e_e8_force_fire_reaches_live_oanda(monkeypatch, tmp_path):
    prices = [1.1000, 1.1007, 1.1014, 1.1021, 1.1028]
    current = {"price": prices[0]}

    def _bid_ask(_instrument):
        price = current["price"]
        return {"bid": price, "ask": price + 0.0001}

    import hashlib

    class _FakeMD5:
        def hexdigest(self):
            return "00000001"

    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", _bid_ask)
    monkeypatch.setattr(hashlib, "md5", lambda *_args, **_kwargs: _FakeMD5())
    trader, logs = make_trader(tmp_path, monkeypatch, hour=8)

    trader._db.open_trade(
        direction="SELL",
        entry_price=1.2000,
        sl=1.2015,
        tp=1.1985,
        entry_type="seed_live",
        confidence=99,
        tf="15m",
        reasons=["seed live slot"],
        mode="daytrade",
        instrument="EUR_USD",
        is_shadow=False,
        oanda_trade_id="seed-oanda",
    )

    for price in prices:
        current["price"] = price
        trader._tick_entry(
            "daytrade",
            edge_cfg(),
            session_time_bias_sell_sig(price),
            "15m",
            "EUR_USD",
        )

    with trader._db._safe_conn() as conn:
        rows = conn.execute(
            """
            SELECT edge_cell_id, is_shadow, oanda_trade_id
            FROM demo_trades
            WHERE edge_cell_id = 'E8'
            ORDER BY id
            """
        ).fetchall()

    assert len(rows) == 5
    assert all(row["is_shadow"] == 0 for row in rows)
    assert all(row["oanda_trade_id"] for row in rows)
    assert len(trader._oanda.calls) == 5
    assert all(call["units"] == 5000 for call in trader._oanda.calls)
    assert any(
        "[EDGE_CELL] E8 shadow→live force override "
        "(was shadow due to: OTHER_UPSTREAM)" in log
        for log in logs
    ), logs
