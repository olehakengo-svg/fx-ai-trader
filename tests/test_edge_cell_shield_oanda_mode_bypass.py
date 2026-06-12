from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from modules import data as data_mod

sys.path.append(str(Path(__file__).resolve().parent))
from edge_cell_test_helpers import edge_cfg, make_trader, session_time_bias_sell_sig


def _patch_price(monkeypatch, price: float):
    monkeypatch.setattr(
        data_mod,
        "fetch_oanda_bid_ask",
        lambda _instrument: {"bid": price, "ask": price + 0.0001},
    )


def _sell_sig(entry_type: str, *, entry: float = 1.1000, direction: str = "SELL"):
    is_sell = direction == "SELL"
    return {
        "entry": entry,
        "signal": direction,
        "entry_type": entry_type,
        "confidence": 70,
        "score": -1.0 if is_sell else 1.0,
        "sl": entry + 0.0015 if is_sell else entry - 0.0015,
        "tp": entry - 0.0030 if is_sell else entry + 0.0030,
        "atr": 0.0010,
        "reasons": [f"✅ edge-cell shield bypass test {entry_type}"],
        "regime": {"regime": "TREND_BEAR" if is_sell else "TREND_BULL"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
    }


def _latest_trade(db):
    with db._safe_conn() as conn:
        return conn.execute(
            """
            SELECT edge_cell_id, is_shadow, oanda_trade_id
            FROM demo_trades
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()


def _audit_rows(db):
    with db._safe_conn() as conn:
        return conn.execute(
            """
            SELECT bridge_status, block_reason, is_live
            FROM oanda_audit
            ORDER BY id
            """
        ).fetchall()


def _persist_audit(trader):
    def _add(**kwargs):
        trader._db.save_oanda_audit(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "demo_trade_id": kwargs["trade_id"],
                "entry_type": kwargs["entry_type"],
                "is_live": kwargs["is_live"],
                "bridge_status": kwargs["bridge_status"],
                "block_reason": kwargs["block_reason"],
                "direction": kwargs.get("direction", ""),
                "instrument": kwargs.get("instrument", ""),
                "units": kwargs.get("units", 0),
            }
        )

    trader._add_oanda_audit = _add


def test_shield_oanda_mode_block_bypassed_by_edge_cell(monkeypatch, tmp_path):
    _patch_price(monkeypatch, 1.1000)
    trader, logs = make_trader(tmp_path, monkeypatch, hour=8)
    trader._OANDA_MODE_BLOCKED = frozenset({"daytrade_eur"})

    trader._tick_entry(
        "daytrade_eur",
        edge_cfg(),
        session_time_bias_sell_sig(1.1000),
        "15m",
        "EUR_USD",
    )

    row = _latest_trade(trader._db)
    assert row["edge_cell_id"] == "E8"
    assert row["is_shadow"] == 0
    assert row["oanda_trade_id"]
    assert trader._oanda.calls
    assert any("[SHIELD] EDGE_CELL bypass: E8 session_time_bias mode=daytrade_eur" in log for log in logs)


def test_shield_oanda_mode_block_fires_when_no_edge_cell(monkeypatch, tmp_path):
    _patch_price(monkeypatch, 1.1000)
    trader, logs = make_trader(tmp_path, monkeypatch, hour=14)
    trader._SHADOW_MODE = False
    trader._OANDA_MODE_BLOCKED = frozenset({"daytrade_eur"})
    trader._strategy_n_cache = {"session_time_bias": 20}
    # 800e09f7 (2026-06-01) gated session_time_bias×EUR_USD behind
    # _PAIR_SESSION_FILTER {"London"}; the gate reads the REAL clock
    # (_is_promoted does a local `from datetime import datetime`), so the
    # fixture's patched hour never reaches it. Pin promotion at instance
    # level so the trade reaches the SHIELD branch deterministically.
    trader._PAIR_PROMOTED = frozenset({("session_time_bias", "EUR_USD")})
    trader._PAIR_SESSION_FILTER = {}

    trader._tick_entry(
        "daytrade_eur",
        edge_cfg(),
        _sell_sig("session_time_bias"),
        "15m",
        "EUR_USD",
    )

    row = _latest_trade(trader._db)
    assert row["edge_cell_id"] == ""
    assert row["is_shadow"] == 1
    assert not row["oanda_trade_id"]
    assert not trader._oanda.calls
    assert any("[SHIELD] OANDA blocked: mode=daytrade_eur" in log for log in logs)


def test_aggregate_kelly_gate_bypassed_by_edge_cell(monkeypatch, tmp_path):
    _patch_price(monkeypatch, 1.1000)
    trader, logs = make_trader(tmp_path, monkeypatch, hour=8)
    trader._strategy_n_cache = {"session_time_bias": 20}
    trader._get_aggregate_kelly = lambda: -0.25

    trader._tick_entry(
        "daytrade",
        edge_cfg(),
        session_time_bias_sell_sig(1.1000),
        "15m",
        "EUR_USD",
    )

    row = _latest_trade(trader._db)
    assert row["edge_cell_id"] == "E8"
    assert row["is_shadow"] == 0
    assert row["oanda_trade_id"]
    assert trader._oanda.calls
    assert any("[SHIELD] EDGE_CELL Kelly bypass: E8 session_time_bias" in log for log in logs)
    assert not any("[SHIELD] Aggregate Kelly gate" in log for log in logs)


def test_aggregate_kelly_gate_fires_when_no_edge_cell(monkeypatch, tmp_path):
    _patch_price(monkeypatch, 1.1000)
    trader, logs = make_trader(tmp_path, monkeypatch, hour=14)
    _persist_audit(trader)
    trader._SHADOW_MODE = False
    trader._strategy_n_cache = {"session_time_bias": 20}
    # See test_shield_oanda_mode_block_fires_when_no_edge_cell — same
    # deterministic-promotion pin (800e09f7 session filter reads real clock).
    trader._PAIR_PROMOTED = frozenset({("session_time_bias", "EUR_USD")})
    trader._PAIR_SESSION_FILTER = {}
    trader._get_aggregate_kelly = lambda: -0.25

    trader._tick_entry(
        "daytrade",
        edge_cfg(),
        _sell_sig("session_time_bias"),
        "15m",
        "EUR_USD",
    )

    row = _latest_trade(trader._db)
    assert row["edge_cell_id"] == ""
    assert row["is_shadow"] == 1
    assert not row["oanda_trade_id"]
    assert not trader._oanda.calls
    assert any("[SHIELD] Aggregate Kelly gate: -0.250 < 0" in log for log in logs)
    audit = _audit_rows(trader._db)
    assert any(
        row["bridge_status"] == "blocked" and row["block_reason"] == "agg_kelly=-0.250<0"
        for row in audit
    )


def test_existing_eur_dt_whitelist_still_works(monkeypatch, tmp_path):
    _patch_price(monkeypatch, 1.1000)
    trader, logs = make_trader(tmp_path, monkeypatch, hour=14)
    trader._SHADOW_MODE = False
    trader._OANDA_MODE_BLOCKED = frozenset({"daytrade_eur"})
    trader._strategy_n_cache = {"htf_false_breakout": 20}

    trader._tick_entry(
        "daytrade_eur",
        edge_cfg(),
        _sell_sig("htf_false_breakout", direction="BUY"),
        "15m",
        "EUR_USD",
    )

    row = _latest_trade(trader._db)
    assert row["edge_cell_id"] == ""
    assert row["is_shadow"] == 0
    assert row["oanda_trade_id"]
    assert trader._oanda.calls
    assert any(
        "[SHIELD] EUR DT whitelist bypass: htf_false_breakout mode=daytrade_eur" in log
        for log in logs
    )
