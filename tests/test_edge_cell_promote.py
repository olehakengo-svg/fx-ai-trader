from __future__ import annotations

import os
import threading
from datetime import datetime, timezone

import pytest

from modules.demo_db import DemoDB
from modules.edge_cell_promote import EDGE_CELLS, get_cell_lot, match


def _dt(hour: int) -> datetime:
    return datetime(2026, 5, 26, hour, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "cell_id,kwargs",
    [
        ("E1", dict(strategy="dt_bb_rsi_mr", symbol="GBP_USD", entry_time=_dt(1), direction="SELL")),
        ("E2", dict(strategy="session_time_bias", symbol="EUR_USD", entry_time=_dt(8), direction="BUY", mtf_gate_action="live_tier_exempt")),
        ("E3", dict(strategy="dt_bb_rsi_mr", symbol="EUR_USD", entry_time=_dt(8), direction="SELL")),
        ("E4", dict(strategy="bb_rsi_reversion", symbol="USD_JPY", entry_time=_dt(14), direction="SELL")),
        ("E5", dict(strategy="dt_bb_rsi_mr", symbol="GBP_USD", entry_time=_dt(8), direction="SELL")),
        ("E6", dict(strategy="rsk_gbpjpy_reversion", symbol="GBP_JPY", entry_time=_dt(8), direction="BUY")),
        ("E7", dict(strategy="dt_bb_rsi_mr", symbol="GBP_USD", entry_time=_dt(1), direction="BUY")),
        ("E8", dict(strategy="session_time_bias", symbol="EUR_USD", entry_time=_dt(8), direction="SELL")),
        ("E9", dict(strategy="orb_trap", symbol="GBP_USD", entry_time=_dt(8), direction="SELL")),
        ("E10", dict(strategy="wick_imbalance_reversion", symbol="GBP_USD", entry_time=_dt(8), direction="BUY", v2_regime="no_go")),
        ("E11", dict(strategy="dt_bb_rsi_mr", symbol="USD_JPY", entry_time=_dt(14), direction="SELL")),
        ("E12", dict(strategy="sr_anti_hunt_bounce", symbol="EUR_JPY", entry_time=_dt(22), direction="BUY")),
    ],
)
def test_match_all_12_cells(cell_id, kwargs):
    assert match(**kwargs).cell_id == cell_id


def test_priority_first_match_wins():
    cell = match(
        strategy="dt_bb_rsi_mr",
        symbol="GBP_USD",
        entry_time=_dt(1),
        direction="SELL",
    )
    assert cell.cell_id == "E1"


def test_non_match_v2_regime():
    assert match(
        strategy="wick_imbalance_reversion",
        symbol="GBP_USD",
        entry_time=_dt(8),
        direction="BUY",
        v2_regime="moderate_trend",
    ) is None


def test_get_cell_lot_ladder(tmp_path):
    db = DemoDB(str(tmp_path / "edge-lot.db"))
    assert get_cell_lot("E3", db) == 5000
    db.set_system_kv("edge_cell_stage:E3", "2")
    assert get_cell_lot("E3", db) == 7500
    db.set_system_kv("edge_cell_stage:E3", "3")
    assert get_cell_lot("E3", db) == 10000
    db.set_system_kv("edge_cell_stage:E3", "0")
    assert get_cell_lot("E3", db) == 0


def test_all_12_cells_default_to_stage1_lot(tmp_path):
    db = DemoDB(str(tmp_path / "edge-lot-all.db"))

    assert len(EDGE_CELLS) == 12
    assert {cell.cell_id: get_cell_lot(cell.cell_id, db) for cell in EDGE_CELLS} == {
        f"E{i}": 5000 for i in range(1, 13)
    }


class _OandaMock:
    active = True

    def __init__(self):
        self.calls = []

    def is_mode_allowed(self, _mode):
        return True

    def get_strategy_mode(self, _entry_type):
        return "normal"

    def open_trade(self, **kwargs):
        self.calls.append(kwargs)
        callback = kwargs.get("callback")
        if callback:
            callback(kwargs["demo_trade_id"], f"test-oanda-{len(self.calls)}")
        # 2026-07-02 send-accept contract: True = gates passed, send fired.
        return True


class _ExposureMock:
    def check_new_trade(self, *_args, **_kwargs):
        return True, ""

    def add_position(self, *_args, **_kwargs):
        return None

    def set_shadow_status(self, *_args, **_kwargs):
        return None


class _AlertMock:
    def alert_exposure_blocked(self, *_args, **_kwargs):
        return None


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 5, 26, 12, 0, tzinfo=timezone.utc)
        return value if tz is None else value.astimezone(tz)


def test_e2e_tick_entry_force_fires_e3_to_oanda(monkeypatch, tmp_path):
    from modules import data as data_mod
    import modules.demo_trader as demo_trader_mod
    from modules.demo_trader import DemoTrader

    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDateTime)
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: {"bid": 1.1000, "ask": 1.1001})
    monkeypatch.setattr(demo_trader_mod, "classify_prime", lambda *_args, **_kwargs: None)

    db = DemoDB(str(tmp_path / "edge-e2e.db"))
    trader = DemoTrader.__new__(DemoTrader)
    trader._db = db
    trader._lock = threading.RLock()
    trader._oanda = _OandaMock()
    trader._exposure_mgr = _ExposureMock()
    trader._alert_mgr = _AlertMock()
    trader._params = {
        "max_open_trades": 10,
        "entry_type_blacklist": [],
        "max_consecutive_losses": 99,
        "confidence_threshold": 1,
    }
    trader._price_history = {}
    trader._15m_tactical_bias = {}
    trader._block_counts = {}
    trader._consec_losses = {}
    trader._total_losses_window = []
    trader._sl_hit_history = []
    trader._limit_expired_cd = {}
    trader._pending_limits = {}
    trader._recent_signal_emits = {}
    trader._dedup_stats = {}
    trader._mtf_cache = {}
    trader._entry_atr = {}
    trader._entry_adx = {}
    trader._dd_phase_at_entry = {}
    trader._defensive_mode = False
    trader._dd_lot_mult = 1.0
    trader._strategy_n_cache = {"dt_bb_rsi_mr": 20}
    trader._N_LOT_TIERS = []
    trader._PAIR_LOT_BOOST = {}
    trader._STRATEGY_LOT_BOOST = {}
    trader._SHADOW_MODE = True
    trader._OANDA_MODE_BLOCKED = frozenset()
    trader._add_log = lambda _msg: None
    trader._add_oanda_audit = lambda **_kwargs: None
    trader._check_signal_reverse = lambda *_args, **_kwargs: None
    trader._check_drawdown = lambda: False
    trader._get_cooldown_age = lambda *_args, **_kwargs: None
    trader._get_mtf_regime = lambda _instrument: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": ""}
    trader._compute_dow_regime = lambda *_args, **_kwargs: "range"
    trader._compute_v2_regime = lambda *_args, **_kwargs: "moderate_trend"
    trader._compute_confluence_tag = lambda *_args, **_kwargs: {"score": "", "details": ""}
    trader._get_strategy_kelly = lambda *_args, **_kwargs: None
    trader._get_agg_kelly_lot_boost = lambda: 1.0
    trader._get_aggregate_kelly = lambda: None
    trader._get_ruin_probability = lambda: None

    sig = {
        "entry": 1.1000,
        "signal": "SELL",
        "entry_type": "dt_bb_rsi_mr",
        "confidence": 70,
        "score": -1.0,
        "tp": 1.0988,
        "atr": 0.0010,
        "reasons": ["✅ edge-cell synthetic E3"],
        "regime": {"type": "RANGE"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
    }
    cfg = {
        "label": "Daytrade",
        "icon": "D",
        "symbol": "EURUSD=X",
        "base_sl_pips": 15,
        "active_hours_utc": (0, 23),
    }

    trader._tick_entry("daytrade", cfg, sig, "15m", "EUR_USD")

    assert len(EDGE_CELLS) == 12
    assert trader._oanda.calls, "edge-cell E3 should force an OANDA boundary call"
    assert trader._oanda.calls[0]["units"] == 5000
    with db._safe_conn() as conn:
        row = conn.execute("SELECT edge_cell_id, is_shadow FROM demo_trades").fetchone()
    assert row["edge_cell_id"] == "E3"
    assert row["is_shadow"] == 0
