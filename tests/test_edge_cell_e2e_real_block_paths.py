from __future__ import annotations

import sys
from pathlib import Path

from modules import data as data_mod

sys.path.append(str(Path(__file__).resolve().parent))
from edge_cell_test_helpers import edge_cfg, make_trader, session_time_bias_sell_sig


def _sell_sig(entry_type: str, *, entry: float):
    return {
        "entry": entry,
        "signal": "SELL",
        "entry_type": entry_type,
        "confidence": 70,
        "score": -1.0,
        "sl": entry + 0.0015,
        "tp": entry - 0.0030,
        "atr": 0.0010,
        "reasons": [f"✅ edge-cell real block path {entry_type}"],
        "regime": {"regime": "TREND_BEAR"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
    }


def _set_price_feed(monkeypatch, current):
    monkeypatch.setattr(
        data_mod,
        "fetch_oanda_bid_ask",
        lambda _instrument: {
            "bid": current["price"],
            "ask": current["price"] + 0.0001,
        },
    )


def _edge_rows(db, cell_id: str):
    with db._safe_conn() as conn:
        return conn.execute(
            """
            SELECT edge_cell_id, is_shadow, oanda_trade_id
            FROM demo_trades
            WHERE edge_cell_id = ?
            ORDER BY id
            """,
            (cell_id,),
        ).fetchall()


def test_e2e_edge_cells_bypass_real_r2_and_same_price_blocks(monkeypatch, tmp_path):
    import hashlib

    class _FakeMD5:
        def hexdigest(self):
            return "00000001"

    monkeypatch.setattr(hashlib, "md5", lambda *_args, **_kwargs: _FakeMD5())

    current = {"price": 1.1000}
    _set_price_feed(monkeypatch, current)

    e4_trader, e4_logs = make_trader(tmp_path, monkeypatch, hour=14)
    e4_prices = [1.1000, 1.1007, 1.1014, 1.1021, 1.1028]
    for price in e4_prices:
        current["price"] = price
        e4_trader._tick_entry(
            "daytrade",
            edge_cfg(),
            _sell_sig("bb_rsi_reversion", entry=price),
            "15m",
            "EUR_USD",
        )

    e4_rows = _edge_rows(e4_trader._db, "E4")
    assert len(e4_rows) == 5
    assert all(row["is_shadow"] == 0 for row in e4_rows)
    assert all(row["oanda_trade_id"] for row in e4_rows)
    assert sum("[R2_SHADOW_DEMOTE] edge cell E4 bypass" in log for log in e4_logs) == 5
    assert sum("[EDGE_CELL] E4 shadow→live force override" in log for log in e4_logs) == 5

    e8_dir = tmp_path / "e8"
    e8_dir.mkdir()
    e8_trader, e8_logs = make_trader(e8_dir, monkeypatch, hour=8)
    e8_trader._db.open_trade(
        direction="SELL",
        entry_price=1.1000,
        sl=1.2500,
        tp=1.0900,
        entry_type="seed_live",
        confidence=99,
        tf="15m",
        reasons=["same price seed"],
        mode="daytrade",
        instrument="EUR_USD",
        is_shadow=False,
        oanda_trade_id="seed-oanda",
    )

    e8_prices = [1.1000, 1.10025, 1.10050, 1.10075, 1.10100]
    for price in e8_prices:
        current["price"] = price
        e8_trader._tick_entry(
            "daytrade",
            edge_cfg(),
            session_time_bias_sell_sig(price),
            "15m",
            "EUR_USD",
        )

    e8_rows = _edge_rows(e8_trader._db, "E8")
    assert len(e8_rows) == 5
    assert all(row["is_shadow"] == 0 for row in e8_rows)
    assert all(row["oanda_trade_id"] for row in e8_rows)
    assert sum("[SAME_PRICE] edge cell E8 bypass" in log for log in e8_logs) == 5
    assert sum("[EDGE_CELL] E8 shadow→live force override" in log for log in e8_logs) == 5
