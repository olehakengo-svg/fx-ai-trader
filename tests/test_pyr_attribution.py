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
        self.open_calls.append(kwargs)


def test_pyr_child_uses_parent_strategy_and_marks_inflight_before_open(monkeypatch):
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


def test_oanda_bridge_writes_sent_audit_with_strategy_before_market_order(tmp_path, monkeypatch):
    db = DemoDB(str(tmp_path / "bridge.db"))
    bridge = OandaBridge(db=db)
    monkeypatch.setattr(type(bridge), "active", property(lambda self: True))
    bridge._allowed_modes = {""}
    bridge._check_daily_loss_gate = lambda: (False, 0.0)
    bridge._fire = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    bridge._client.market_order = MagicMock(
        return_value=(True, {"orderFillTransaction": {
            "tradeOpened": {"tradeID": "OANDA-PYR-1"},
            "price": "1.1010",
        }})
    )

    bridge.open_trade(
        demo_trade_id="PYR_parent-1",
        direction="BUY",
        sl=1.1000,
        tp=1.3000,
        mode="",
        instrument="EUR_USD",
        units=10000,
        entry_type="vix_carry_unwind",
    )

    rows = db.get_oanda_audit(limit=10)
    sent = [r for r in rows if r["bridge_status"] == "sent"]
    filled = [r for r in rows if r["bridge_status"] == "filled"]
    assert sent and sent[0]["entry_type"] == "vix_carry_unwind"
    assert filled and filled[0]["entry_type"] == ""
