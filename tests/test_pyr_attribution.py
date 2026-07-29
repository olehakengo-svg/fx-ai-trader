from __future__ import annotations

import threading
from unittest.mock import MagicMock

from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader
from modules.oanda_bridge import OandaBridge


class _FakeDB:
    def __init__(self, trade):
        self.trade = trade
        self.updated = []

    def get_open_trades(self):
        return [dict(self.trade)]

    def update_sl_tp(self, trade_id, sl, tp):
        self.updated.append((trade_id, sl, tp))


class _FakeOanda:
    def __init__(self, trader):
        self.trader = trader
        self.open_calls = []

    def modify_sl_sync(self, trade_id, sl, instrument=""):
        return True

    def open_trade(self, **kwargs):
        assert self.trader._pyramided_trades == {"parent-1"}
        assert self.trader._pyramid_inflight == {"parent-1"}
        self.open_calls.append(kwargs)


def test_pyr_child_uses_parent_strategy_and_marks_inflight_before_open(monkeypatch):
    # 2026-07-28 Track C R2: PYR は code pin で恒久停止 (test_track_c_plumbing.py)。
    # 本テストは attribution ロジック自体の回帰検証として、将来の R1 再武装
    # (pre-reg 必須: child の demo 台帳行 + dedup 永続化) に備え pin を外して実行する。
    monkeypatch.setattr(
        "modules.demo_trader._PYRAMIDING_CODE_PIN_DISABLED", False
    )
    trade = {
        "trade_id": "parent-1",
        "direction": "BUY",
        "sl": 1.0900,
        "tp": 1.3000,
        "tf": "15m",
        "mode": "",
        "entry_price": 1.1000,
        "entry_type": "vix_carry_unwind",
        "oanda_trade_id": "403857",
    }
    trader = DemoTrader.__new__(DemoTrader)
    trader._db = _FakeDB(trade)
    trader._tracker_lock = threading.RLock()
    trader._mafe_tracker = {}
    trader._entry_atr = {"parent-1": 0.0005}
    trader._entry_adx = {}
    trader._pyramided_trades = set()
    trader._pyramid_inflight = set()
    trader._profit_extended = set()
    trader._dd_phase_at_entry = {}
    trader._OANDA_LOT_CAP = 10000
    trader._add_log = lambda *_args, **_kwargs: None
    trader._get_realtime_price = lambda *_args, **_kwargs: 1.1010
    trader._is_promoted = lambda entry_type, instrument="": True
    fake_oanda = _FakeOanda(trader)
    trader._oanda = fake_oanda

    monkeypatch.setattr(
        "modules.data.fetch_oanda_bid_ask",
        lambda _inst: {"bid": 1.1010, "ask": 1.10102, "mid": 1.10101},
    )

    trader._check_sltp_realtime()
    trader._check_sltp_realtime()

    assert len(fake_oanda.open_calls) == 1
    call = fake_oanda.open_calls[0]
    assert call["demo_trade_id"] == "PYR_parent-1"
    assert call["entry_type"] == "vix_carry_unwind"
    assert call["units"] == 10000
    assert trader._pyramided_trades == {"parent-1"}
    assert trader._pyramid_inflight == set()


def test_oanda_bridge_writes_sent_audit_with_strategy_before_market_order(tmp_path, monkeypatch):
    db = DemoDB(str(tmp_path / "bridge.db"))
    bridge = OandaBridge(db=db)
    monkeypatch.setattr(type(bridge), "active", property(lambda self: True))
    bridge._allowed_modes = {"scalp"}
    bridge._check_daily_loss_gate = lambda: (False, 0.0)
    bridge._fire = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    bridge._client.market_order = MagicMock(
        return_value=(True, {"orderFillTransaction": {
            "tradeOpened": {"tradeID": "OANDA-PYR-1"},
            "price": "1.1010",
        }})
    )
    db.save_oanda_audit({
        "timestamp": "2026-05-19T11:55:00+00:00",
        "demo_trade_id": "parent-1",
        "entry_type": "vix_carry_unwind",
        "direction": "BUY",
        "instrument": "EUR_USD",
        "units": 1000,
        "is_live": True,
        "bridge_status": "sent",
        "block_reason": "",
        "oanda_trade_id": "",
    })

    bridge.open_trade(
        demo_trade_id="PYR_parent-1",
        direction="BUY",
        sl=1.1000,
        tp=1.3000,
        mode="scalp",
        instrument="EUR_USD",
        units=10000,
        entry_type="vix_carry_unwind",
    )

    rows = db.get_oanda_audit(limit=10)
    sent = [r for r in rows if r["bridge_status"] == "sent"]
    filled = [r for r in rows if r["bridge_status"] == "filled"]
    assert len(sent) == 2
    assert {r["demo_trade_id"] for r in sent} == {"parent-1", "PYR_parent-1"}
    assert {r["entry_type"] for r in sent} == {"vix_carry_unwind"}
    assert filled and filled[0]["entry_type"] == "scalp"


def test_main_entry_path_skip_sent_audit_no_duplicate_sent_rows(tmp_path, monkeypatch):
    """Main-entry path passes entry_type + skip_sent_audit=True.

    Regression for 2026-05-29 visibility fix: the demo_trader main entry path
    writes the 'sent' audit row itself (with sr_meta), so it sets
    skip_sent_audit=True when calling bridge.open_trade. The bridge must:
      1. NOT write a duplicate 'sent' row (skip_sent_audit honored)
      2. Keep the 'filled' row stamped with the mode label.
    """
    db = DemoDB(str(tmp_path / "bridge_main.db"))
    bridge = OandaBridge(db=db)
    monkeypatch.setattr(type(bridge), "active", property(lambda self: True))
    bridge._allowed_modes = {"scalp"}
    bridge._check_daily_loss_gate = lambda: (False, 0.0)
    bridge._fire = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    bridge._client.market_order = MagicMock(
        return_value=(True, {"orderFillTransaction": {
            "tradeOpened": {"tradeID": "OANDA-MAIN-1"},
            "price": "150.10",
        }})
    )

    bridge.open_trade(
        demo_trade_id="demo-main-1",
        direction="SELL",
        sl=150.50,
        tp=149.00,
        mode="scalp",
        instrument="USD_JPY",
        units=5000,
        entry_type="bb_rsi_reversion",
        skip_sent_audit=True,
    )

    rows = db.get_oanda_audit(limit=10)
    sent = [r for r in rows if r["bridge_status"] == "sent"]
    filled = [r for r in rows if r["bridge_status"] == "filled"]
    # Bridge must NOT write a 'sent' row when skip_sent_audit=True
    # (the caller has already written it with sr_meta).
    assert not sent, (
        f"skip_sent_audit=True should suppress bridge-side sent write; got {sent!r}"
    )
    # The filled row must carry the mode label; strategy lives on 'sent'.
    assert filled and filled[0]["entry_type"] == "scalp", (
        f"filled row should keep mode label 'scalp'; got "
        f"{filled[0]['entry_type']!r}"
    )


def test_filled_row_falls_back_to_mode_when_no_entry_type(tmp_path, monkeypatch):
    """Backward compatibility: when caller does NOT pass entry_type,
    the filled row still labels itself with the mode (legacy behavior).

    This documents the fallback path so future refactors don't accidentally
    require entry_type as mandatory.
    """
    db = DemoDB(str(tmp_path / "bridge_fallback.db"))
    bridge = OandaBridge(db=db)
    monkeypatch.setattr(type(bridge), "active", property(lambda self: True))
    bridge._allowed_modes = {"swing"}
    bridge._check_daily_loss_gate = lambda: (False, 0.0)
    bridge._fire = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    bridge._client.market_order = MagicMock(
        return_value=(True, {"orderFillTransaction": {
            "tradeOpened": {"tradeID": "OANDA-FB-1"},
            "price": "1.1010",
        }})
    )

    bridge.open_trade(
        demo_trade_id="demo-fallback-1",
        direction="BUY",
        sl=1.1000,
        tp=1.3000,
        mode="swing",
        instrument="EUR_USD",
        units=3000,
        # entry_type intentionally omitted
    )

    rows = db.get_oanda_audit(limit=10)
    sent = [r for r in rows if r["bridge_status"] == "sent"]
    filled = [r for r in rows if r["bridge_status"] == "filled"]
    assert not sent, "no sent row expected when caller did not pass entry_type"
    assert filled and filled[0]["entry_type"] == "swing", (
        f"filled row should fall back to mode label 'swing'; got "
        f"{filled[0]['entry_type']!r}"
    )
