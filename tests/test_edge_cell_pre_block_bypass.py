from __future__ import annotations

import sys
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


def _sell_sig(entry_type: str, *, entry: float = 1.1000):
    return {
        "entry": entry,
        "signal": "SELL",
        "entry_type": entry_type,
        "confidence": 70,
        "score": -1.0,
        "sl": entry + 0.0015,
        "tp": entry - 0.0030,
        "atr": 0.0010,
        "reasons": [f"✅ edge-cell pre-block test {entry_type}"],
        "regime": {"regime": "TREND_BEAR"},
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


def _seed_same_price_shadow(trader, *, entry_type: str, instrument: str, price: float):
    trader._db.open_trade(
        direction="SELL",
        entry_price=price,
        sl=price + 0.0015,
        tp=price - 0.0030,
        entry_type=entry_type,
        confidence=99,
        tf="15m",
        reasons=["same price seed"],
        mode="daytrade",
        instrument=instrument,
        is_shadow=True,
    )


def test_r2_shadow_demote_bypassed_when_edge_cell_matches(monkeypatch, tmp_path):
    _patch_price(monkeypatch, 1.1000)
    trader, logs = make_trader(tmp_path, monkeypatch, hour=14)

    trader._tick_entry(
        "daytrade",
        edge_cfg(),
        _sell_sig("bb_rsi_reversion"),
        "15m",
        "EUR_USD",
    )

    row = _latest_trade(trader._db)
    assert row["edge_cell_id"] == "E4"
    assert row["is_shadow"] == 0
    assert row["oanda_trade_id"]
    assert not any("r2_shadow_demoted_cell" in key for key in trader._block_counts)
    assert any("[R2_SHADOW_DEMOTE] edge cell E4 bypass" in log for log in logs)
    assert any("[EDGE_CELL] E4 shadow→live force override" in log for log in logs)


def test_r2_shadow_demote_still_blocks_when_no_edge_cell(monkeypatch, tmp_path):
    _patch_price(monkeypatch, 1.1000)
    trader, logs = make_trader(tmp_path, monkeypatch, hour=8)

    trader._tick_entry(
        "daytrade",
        edge_cfg(),
        _sell_sig("bb_rsi_reversion"),
        "15m",
        "EUR_USD",
    )

    assert _latest_trade(trader._db) is None
    assert trader._block_counts["daytrade:r2_shadow_demoted_cell"] == 1
    assert any(
        "[R2_SHADOW_DEMOTE] blocked shadow-tracking cell bb_rsi_reversion x EUR_USD"
        in log
        for log in logs
    )


def test_same_price_bypassed_when_edge_cell_matches(monkeypatch, tmp_path):
    # 元々 E8 (session_time_bias EUR_USD LDN) で検証していたが、E8 は 2026-06-25
    # (rule:R2) で code-level DISABLED (edge-cell-e8-demote-2026-06-25.md)。
    # SAME_PRICE bypass 経路は active cell E4 (bb_rsi_reversion NY SELL) で維持。
    _patch_price(monkeypatch, 1.1000)
    trader, logs = make_trader(tmp_path, monkeypatch, hour=14)
    _seed_same_price_shadow(
        trader,
        entry_type="seed_shadow",
        instrument="EUR_USD",
        price=1.1000,
    )

    trader._tick_entry(
        "daytrade",
        edge_cfg(),
        _sell_sig("bb_rsi_reversion"),
        "15m",
        "EUR_USD",
    )

    row = _latest_trade(trader._db)
    assert row["edge_cell_id"] == "E4"
    assert row["is_shadow"] == 0
    assert row["oanda_trade_id"]
    assert not any("same_price_0pip" in key for key in trader._block_counts)
    assert any("[SAME_PRICE] edge cell E4 bypass" in log for log in logs)
    assert any("[EDGE_CELL] E4 shadow→live force override" in log for log in logs)


def test_same_price_blocks_when_matched_cell_disabled(monkeypatch, tmp_path):
    """E8 は match するが DISABLED (lot=0) のため pre-block eligibility を失い、
    SAME_PRICE ブロックが通常どおり効く (rule:R2 止血, 2026-06-25)。"""
    _patch_price(monkeypatch, 1.1000)
    trader, logs = make_trader(tmp_path, monkeypatch, hour=8)
    _seed_same_price_shadow(
        trader,
        entry_type="seed_shadow",
        instrument="EUR_USD",
        price=1.1000,
    )

    trader._tick_entry(
        "daytrade",
        edge_cfg(),
        session_time_bias_sell_sig(1.1000),
        "15m",
        "EUR_USD",
    )

    rows = trader._db.get_open_trades()
    assert len(rows) == 1
    assert rows[0]["entry_type"] == "seed_shadow"
    assert trader._block_counts["daytrade:same_price_0pip"] == 1
    assert not any("[SAME_PRICE] edge cell E8 bypass" in log for log in logs)


def test_same_price_still_blocks_when_no_edge_cell(monkeypatch, tmp_path):
    _patch_price(monkeypatch, 1.1000)
    trader, _logs = make_trader(tmp_path, monkeypatch, hour=8)
    _seed_same_price_shadow(
        trader,
        entry_type="seed_shadow",
        instrument="EUR_USD",
        price=1.1000,
    )

    trader._tick_entry(
        "daytrade",
        edge_cfg(),
        _sell_sig("ema_cross"),
        "15m",
        "EUR_USD",
    )

    rows = trader._db.get_open_trades()
    assert len(rows) == 1
    assert rows[0]["entry_type"] == "seed_shadow"
    assert trader._block_counts["daytrade:same_price_0pip"] == 1


def test_edge_cell_helper_handles_match_exception(monkeypatch, tmp_path):
    from modules import demo_trader as demo_trader_mod

    _patch_price(monkeypatch, 1.1000)
    trader, _logs = make_trader(tmp_path, monkeypatch, hour=14)

    def _raise_match(**_kwargs):
        raise RuntimeError("match unavailable")

    monkeypatch.setattr(demo_trader_mod.edge_cell_promote, "match", _raise_match)

    trader._tick_entry(
        "daytrade",
        edge_cfg(),
        _sell_sig("bb_rsi_reversion"),
        "15m",
        "EUR_USD",
    )

    assert _latest_trade(trader._db) is None
    assert trader._block_counts["daytrade:r2_shadow_demoted_cell"] == 1
