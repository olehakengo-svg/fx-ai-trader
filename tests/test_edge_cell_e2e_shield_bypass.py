from __future__ import annotations

import sys
from pathlib import Path

from modules import data as data_mod

sys.path.append(str(Path(__file__).resolve().parent))
from edge_cell_test_helpers import edge_cfg, make_trader, session_time_bias_sell_sig


def _set_price_feed(monkeypatch, current):
    monkeypatch.setattr(
        data_mod,
        "fetch_oanda_bid_ask",
        lambda _instrument: {
            "bid": current["price"],
            "ask": current["price"] + 0.0001,
        },
    )


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
        "reasons": [f"✅ edge-cell e2e shield bypass {entry_type}"],
        "regime": {"regime": "TREND_BEAR"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
    }


def _rows(db):
    with db._safe_conn() as conn:
        return conn.execute(
            """
            SELECT entry_type, edge_cell_id, is_shadow, oanda_trade_id
            FROM demo_trades
            WHERE entry_type != 'seed_live'
            ORDER BY id
            """
        ).fetchall()


def _seed_live_slot(trader, *, instrument: str = "EUR_USD"):
    trader._db.open_trade(
        direction="SELL",
        entry_price=1.2000,
        sl=1.2015,
        tp=1.1985,
        entry_type="seed_live",
        confidence=99,
        tf="15m",
        reasons=["seed live slot"],
        mode="daytrade_eur",
        instrument=instrument,
        is_shadow=False,
        oanda_trade_id="seed-oanda",
    )


def _close_open_trades(trader):
    with trader._db._safe_conn() as conn:
        conn.execute("UPDATE demo_trades SET status='CLOSED' WHERE status='OPEN'")
        conn.commit()


def _configure_shielded_edge_run(trader):
    trader._OANDA_MODE_BLOCKED = frozenset({"daytrade_eur"})
    trader._strategy_n_cache = {
        "session_time_bias": 20,
        "dt_bb_rsi_mr": 20,
    }
    trader._get_aggregate_kelly = lambda: -0.25


def test_e2e_edge_cells_bypass_shield_mode_and_aggregate_kelly(monkeypatch, tmp_path):
    current = {"price": 1.1000}
    _set_price_feed(monkeypatch, current)

    e8_dir = tmp_path / "e8"
    e8_dir.mkdir()
    e8_trader, e8_logs = make_trader(e8_dir, monkeypatch, hour=8)
    _configure_shielded_edge_run(e8_trader)
    _seed_live_slot(e8_trader)

    for price in [1.1000, 1.1007, 1.1014]:
        current["price"] = price
        e8_trader._tick_entry(
            "daytrade_eur",
            edge_cfg(),
            session_time_bias_sell_sig(price),
            "15m",
            "EUR_USD",
        )

    e8_rows = _rows(e8_trader._db)
    assert len(e8_rows) == 3
    assert all(row["edge_cell_id"] == "E8" for row in e8_rows)
    assert all(row["is_shadow"] == 0 for row in e8_rows)
    assert all(row["oanda_trade_id"] for row in e8_rows)
    assert len(e8_trader._oanda.calls) == 3
    assert sum("[EDGE_CELL] E8 shadow→live force override" in log for log in e8_logs) == 3
    assert sum("[SHIELD] EDGE_CELL bypass: E8 session_time_bias mode=daytrade_eur" in log for log in e8_logs) == 3
    assert sum("[SHIELD] EDGE_CELL Kelly bypass: E8 session_time_bias" in log for log in e8_logs) == 3

    e3_dir = tmp_path / "e3"
    e3_dir.mkdir()
    e3_trader, e3_logs = make_trader(e3_dir, monkeypatch, hour=8)
    _configure_shielded_edge_run(e3_trader)
    _seed_live_slot(e3_trader)

    for price in [1.1100, 1.11025, 1.11050]:
        current["price"] = price
        e3_trader._tick_entry(
            "daytrade_eur",
            edge_cfg(),
            _sell_sig("dt_bb_rsi_mr", entry=price),
            "15m",
            "EUR_USD",
        )

    e3_rows = _rows(e3_trader._db)
    assert len(e3_rows) == 3
    assert all(row["edge_cell_id"] == "E3" for row in e3_rows)
    assert all(row["is_shadow"] == 0 for row in e3_rows)
    assert all(row["oanda_trade_id"] for row in e3_rows)
    assert len(e3_trader._oanda.calls) == 3
    assert sum("[EDGE_CELL] E3 shadow→live force override" in log for log in e3_logs) == 3
    assert sum("[SHIELD] EDGE_CELL bypass: E3 dt_bb_rsi_mr mode=daytrade_eur" in log for log in e3_logs) == 3
    assert sum("[SHIELD] EDGE_CELL Kelly bypass: E3 dt_bb_rsi_mr" in log for log in e3_logs) == 3

    blocked_dir = tmp_path / "blocked"
    blocked_dir.mkdir()
    blocked_trader, blocked_logs = make_trader(blocked_dir, monkeypatch, hour=14)
    blocked_trader._SHADOW_MODE = False
    blocked_trader._OANDA_MODE_BLOCKED = frozenset({"daytrade_eur"})
    blocked_trader._strategy_n_cache = {"session_time_bias": 20}
    blocked_trader._get_aggregate_kelly = lambda: -0.25

    for price in [1.1200, 1.12025, 1.12050]:
        current["price"] = price
        blocked_trader._tick_entry(
            "daytrade_eur",
            edge_cfg(),
            _sell_sig("session_time_bias", entry=price),
            "15m",
            "EUR_USD",
        )
        _close_open_trades(blocked_trader)

    blocked_rows = _rows(blocked_trader._db)
    assert len(blocked_rows) == 3
    assert all(row["edge_cell_id"] == "" for row in blocked_rows)
    assert all(row["is_shadow"] == 1 for row in blocked_rows)
    assert all(not row["oanda_trade_id"] for row in blocked_rows)
    assert not blocked_trader._oanda.calls
    assert sum("[SHIELD] OANDA blocked: mode=daytrade_eur" in log for log in blocked_logs) == 3
    assert not any("[SHIELD] EDGE_CELL bypass" in log for log in blocked_logs)
