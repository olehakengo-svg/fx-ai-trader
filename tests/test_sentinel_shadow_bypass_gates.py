import uuid
from datetime import datetime as real_datetime, timezone, timedelta

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


class _FixedDatetime(real_datetime):
    @classmethod
    def now(cls, tz=None):
        base = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
        if tz is None:
            return base.replace(tzinfo=None)
        return base.astimezone(tz)


class _TokyoDatetime(real_datetime):
    @classmethod
    def now(cls, tz=None):
        base = real_datetime(2026, 5, 28, 3, 0, tzinfo=timezone.utc)
        if tz is None:
            return base.replace(tzinfo=None)
        return base.astimezone(tz)


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"shadow_bypass_{uuid.uuid4().hex}.db")))
    logs = []
    monkeypatch.setattr(trader, "_add_log", logs.append)
    monkeypatch.setattr(trader, "_check_drawdown", lambda: False)
    monkeypatch.setattr(
        trader._exposure_mgr,
        "check_new_trade",
        lambda *_args, **_kwargs: (True, ""),
    )
    monkeypatch.setattr(
        trader,
        "_get_mtf_regime",
        lambda _instrument: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": "normal"},
    )
    monkeypatch.setattr(trader, "_compute_dow_regime", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(trader, "_compute_v2_regime", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(trader, "_compute_confluence_tag", lambda *_args, **_kwargs: {"score": 0, "details": ""})
    return trader, logs


def _sig(entry_type="eurgbp_daily_mr", signal="BUY", entry=1.2000, tp=1.2060):
    return {
        "signal": signal,
        "entry": entry,
        "tp": tp,
        "entry_type": entry_type,
        "confidence": 80,
        "score": 1.0 if signal == "BUY" else -1.0,
        "reasons": ["\u2705 unit-test"],
        "atr": 0.0005,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }


def _cfg(instrument):
    return {"instrument": instrument, "icon": "UT", "label": "unit-test"}


def _shadow_rows(trader):
    with trader._db._safe_conn() as conn:
        return conn.execute(
            "SELECT entry_type, instrument, is_shadow FROM demo_trades"
        ).fetchall()


def test_sentinel_recent_emit_bypasses_to_shadow_and_non_sentinel_still_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)

    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_args, **_kwargs: 30)
    trader._tick_entry("daytrade", _cfg("USD_CAD"), _sig(), "5m", "USD_CAD")

    rows = _shadow_rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    assert any("[SHADOW] recent_emit bypass: eurgbp_daily_mr" in msg for msg in logs)
    assert "eurgbp_daily_mr:recent_emit" not in getattr(trader, "_block_counts_per_strategy", {})

    non_sentinel, _logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(non_sentinel, "_maybe_reserve_signal_emit", lambda *_args, **_kwargs: 30)
    non_sentinel._tick_entry(
        "daytrade",
        _cfg("USD_CAD"),
        _sig(entry_type="trendline_sweep"),
        "5m",
        "USD_CAD",
    )

    assert not _shadow_rows(non_sentinel)
    assert non_sentinel._block_counts_per_strategy["trendline_sweep:recent_emit"] == 1


def test_sentinel_spread_guard_bypasses_to_shadow(tmp_path, monkeypatch):
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    trader, _initial_logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_args, **_kwargs: None)
    logs = []
    monkeypatch.setattr(trader, "_add_log", logs.append)
    monkeypatch.setattr(
        data_mod,
        "fetch_oanda_bid_ask",
        lambda _inst: {"bid": 1.19995, "ask": 1.20005},
    )

    trader._tick_entry(
        "daytrade",
        _cfg("USD_CAD"),
        _sig(entry=1.2000, tp=1.2009),
        "5m",
        "USD_CAD",
    )

    rows = _shadow_rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    assert any("[SHADOW] spread_guard bypass: eurgbp_daily_mr" in msg for msg in logs)


def test_sentinel_session_pair_bypasses_to_shadow(tmp_path, monkeypatch):
    monkeypatch.setattr(demo_trader_mod, "datetime", _TokyoDatetime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_args, **_kwargs: None)

    trader._tick_entry(
        "daytrade",
        _cfg("EUR_USD"),
        _sig(entry_type="session_time_bias"),
        "5m",
        "EUR_USD",
    )

    rows = _shadow_rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    assert any("[SHADOW] session_pair bypass: session_time_bias" in msg for msg in logs)


def test_sentinel_spike_bypasses_to_shadow(tmp_path, monkeypatch):
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_args, **_kwargs: None)
    now = _FixedDatetime.now(timezone.utc)
    trader._price_history["USD_CAD"] = [
        (now - timedelta(seconds=50), 1.2000),
        (now - timedelta(seconds=40), 1.2020),
    ]

    trader._tick_entry("daytrade", _cfg("USD_CAD"), _sig(), "5m", "USD_CAD")

    rows = _shadow_rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    assert any("[SHADOW] spike bypass: eurgbp_daily_mr" in msg for msg in logs)


def test_sentinel_velocity_down_bypasses_to_shadow(tmp_path, monkeypatch):
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_args, **_kwargs: None)
    trader._price_history["USD_CAD"] = [
        (_FixedDatetime.now(timezone.utc) - timedelta(minutes=20), 1.2030),
    ]

    trader._tick_entry("daytrade", _cfg("USD_CAD"), _sig(signal="BUY"), "5m", "USD_CAD")

    rows = _shadow_rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    assert any("[SHADOW] velocity_down bypass: eurgbp_daily_mr" in msg for msg in logs)
