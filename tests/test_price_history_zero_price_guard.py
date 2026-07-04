"""P1 回帰: _price_history への 0/None 価格混入で spike/velocity gate が誤発火するバグ。

2026-07-02 12:31 UTC 実証: fund 系データソース全滅時に 0 価格が _price_history に混入し、
spike gate が `max-min = 価格そのもの` (16153.1pip/60s) で誤発火。vix_carry_unwind ×
USD_JPY Overlap pilot の窓内シグナル 14/14 が shadow 化された。

3 層防御 (rule:R3):
  L1: append 時に current_price > 0 ガード (汚染を記録しない + 検出 print 1 行)
  L2: spike gate 計算側で p > 0 フィルタ (既存汚染への安全網)
  L3: velocity gate 計算側で p > 0 フィルタ + current_price > 0 ガード

KB: knowledge-base/wiki/analyses/zero-fire-diagnosis-carrydip-vix-2026-07-02.md §2.6
"""
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


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"zero_guard_{uuid.uuid4().hex}.db")))
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
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_args, **_kwargs: None)
    return trader, logs


def _sig(entry_type="eurgbp_daily_mr", signal="BUY", entry=1.2000, tp=1.2060):
    return {
        "signal": signal,
        "entry": entry,
        "tp": tp,
        "entry_type": entry_type,
        "confidence": 80,
        "score": 1.0 if signal == "BUY" else -1.0,
        "reasons": ["✅ unit-test"],
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


# ══════════════════════════════════════════════════════════════
# L1: append ガード
# ══════════════════════════════════════════════════════════════

def test_zero_price_tick_not_recorded_in_price_history(tmp_path, monkeypatch, capsys):
    """fetch 全滅で entry=0 の WAIT tick → 履歴に記録しない + 汚染検出 print 1 行。"""
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader, _logs = _make_trader(tmp_path, monkeypatch)

    trader._tick_entry("daytrade", _cfg("USD_JPY"), _sig(signal="WAIT", entry=0), "5m", "USD_JPY")

    assert not trader._price_history.get("USD_JPY"), (
        "0 価格 tick が _price_history に記録された (spike gate 誤発火の火種)"
    )
    assert "PRICE_HISTORY_GUARD" in capsys.readouterr().out


def test_none_price_tick_not_recorded_in_price_history(tmp_path, monkeypatch):
    """entry=None の WAIT tick → クラッシュせず履歴にも記録しない。"""
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader, _logs = _make_trader(tmp_path, monkeypatch)

    trader._tick_entry("daytrade", _cfg("USD_JPY"), _sig(signal="WAIT", entry=None), "5m", "USD_JPY")

    assert not trader._price_history.get("USD_JPY")


def test_valid_price_tick_still_recorded_in_price_history(tmp_path, monkeypatch):
    """正常価格の tick は従来どおり記録される (ガードの過剰遮断防止)。"""
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader, _logs = _make_trader(tmp_path, monkeypatch)

    trader._tick_entry("daytrade", _cfg("USD_JPY"), _sig(signal="WAIT", entry=161.53), "5m", "USD_JPY")

    history = trader._price_history.get("USD_JPY", [])
    assert [p for _t, p in history] == [161.53]


# ══════════════════════════════════════════════════════════════
# L2: spike gate — 汚染履歴で誤発火しない / 正常 spike では発火する
# ══════════════════════════════════════════════════════════════

def test_spike_gate_not_triggered_by_zero_contaminated_history(tmp_path, monkeypatch):
    """2026-07-02 事故再現: 履歴内の 0 tick で spike range が価格そのものになり誤発火。"""
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    now = _FixedDatetime.now(timezone.utc)
    # 過去に混入済みの汚染 (L1 導入前のデータ / 別経路) + 正常 tick 2 本
    trader._price_history["USD_CAD"] = [
        (now - timedelta(seconds=50), 0.0),
        (now - timedelta(seconds=45), 1.2000),
        (now - timedelta(seconds=40), 1.2001),
    ]

    trader._tick_entry("daytrade", _cfg("USD_CAD"), _sig(), "5m", "USD_CAD")

    assert not any("spike" in msg for msg in logs), (
        f"0 tick 汚染で spike gate が誤発火: {[m for m in logs if 'spike' in m]}"
    )
    assert "eurgbp_daily_mr:spike" not in getattr(trader, "_block_counts_per_strategy", {})


def test_spike_gate_still_fires_on_genuine_spike(tmp_path, monkeypatch):
    """正常 tick のみの本物 spike (20pip/60s > ATR) では従来どおり発火する。"""
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    now = _FixedDatetime.now(timezone.utc)
    trader._price_history["USD_CAD"] = [
        (now - timedelta(seconds=50), 1.2000),
        (now - timedelta(seconds=40), 1.2020),
    ]

    trader._tick_entry("daytrade", _cfg("USD_CAD"), _sig(), "5m", "USD_CAD")

    rows = _shadow_rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    assert any("[SHADOW] spike bypass: eurgbp_daily_mr" in msg for msg in logs)


# ══════════════════════════════════════════════════════════════
# L3: velocity gate — 汚染履歴 / 無効 current_price で誤発火しない
# ══════════════════════════════════════════════════════════════

def test_velocity_gate_not_triggered_by_zero_contaminated_history(tmp_path, monkeypatch):
    """oldest=0.0 だと price_move が価格そのものになり velocity_up が誤発火する。"""
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    trader._price_history["USD_CAD"] = [
        (_FixedDatetime.now(timezone.utc) - timedelta(minutes=20), 0.0),
    ]

    trader._tick_entry("daytrade", _cfg("USD_CAD"), _sig(signal="SELL"), "5m", "USD_CAD")

    assert not any("velocity" in msg for msg in logs), (
        f"0 tick 汚染で velocity gate が誤発火: {[m for m in logs if 'velocity' in m]}"
    )
    assert "eurgbp_daily_mr:velocity_up" not in getattr(trader, "_block_counts_per_strategy", {})


def test_velocity_gate_skipped_when_current_price_invalid(tmp_path, monkeypatch):
    """current_price=0 (fetch 全滅) では velocity 計算自体をスキップする。"""
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_get_realtime_price", lambda *_a, **_k: None)
    now = _FixedDatetime.now(timezone.utc)
    trader._price_history["USD_CAD"] = [
        (now - timedelta(minutes=20), 1.2030),
        (now - timedelta(minutes=10), 1.2028),
    ]

    trader._tick_entry("daytrade", _cfg("USD_CAD"), _sig(signal="BUY", entry=0), "5m", "USD_CAD")

    assert not any("velocity" in msg for msg in logs), (
        f"current_price=0 で velocity gate が誤発火: {[m for m in logs if 'velocity' in m]}"
    )
    assert "eurgbp_daily_mr:velocity_down" not in getattr(trader, "_block_counts_per_strategy", {})


def test_velocity_gate_still_fires_on_genuine_move(tmp_path, monkeypatch):
    """正常 tick のみの本物急落 (30pip/20min vs BUY) では従来どおり発火する。"""
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    trader._price_history["USD_CAD"] = [
        (_FixedDatetime.now(timezone.utc) - timedelta(minutes=20), 1.2030),
    ]

    trader._tick_entry("daytrade", _cfg("USD_CAD"), _sig(signal="BUY"), "5m", "USD_CAD")

    rows = _shadow_rows(trader)
    assert rows and rows[0]["is_shadow"] == 1
    assert any("[SHADOW] velocity_down bypass: eurgbp_daily_mr" in msg for msg in logs)
