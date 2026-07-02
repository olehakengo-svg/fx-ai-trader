from __future__ import annotations

import threading
from datetime import datetime, timezone

import pytest

from modules.demo_db import DemoDB


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
            callback(kwargs["demo_trade_id"], f"edge-test-{len(self.calls)}")
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


def _fixed_datetime(hour: int):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 5, 26, hour, 0, tzinfo=timezone.utc)
            return value if tz is None else value.astimezone(tz)

    return FixedDateTime


def _make_trader(tmp_path, monkeypatch, *, hour: int, price: float = 1.1000):
    from modules import data as data_mod
    import modules.demo_trader as demo_trader_mod
    from modules.demo_trader import DemoTrader

    logs = []
    monkeypatch.setattr(demo_trader_mod, "datetime", _fixed_datetime(hour))
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: {"bid": price, "ask": price + 0.0001})
    monkeypatch.setattr(demo_trader_mod, "classify_prime", lambda *_args, **_kwargs: None)

    trader = DemoTrader.__new__(DemoTrader)
    trader._db = DemoDB(str(tmp_path / "edge-force-live.db"))
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
    trader._block_counts_per_strategy = {}
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
    trader._strategy_n_cache = {}
    trader._N_LOT_TIERS = []
    trader._PAIR_LOT_BOOST = {}
    trader._STRATEGY_LOT_BOOST = {}
    trader._SHADOW_MODE = True
    trader._OANDA_MODE_BLOCKED = frozenset()
    trader._promoted_types = {}
    trader._runtime_pair_demoted = set()
    trader._add_log = logs.append
    trader._add_oanda_audit = lambda **_kwargs: None
    trader._check_signal_reverse = lambda *_args, **_kwargs: None
    trader._check_drawdown = lambda: False
    trader._get_cooldown_age = lambda *_args, **_kwargs: None
    trader._maybe_reserve_signal_emit = lambda *_args, **_kwargs: None
    trader._get_mtf_regime = lambda _instrument: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": ""}
    trader._compute_dow_regime = lambda *_args, **_kwargs: "range"
    trader._compute_v2_regime = lambda *_args, **_kwargs: "moderate_trend"
    trader._compute_confluence_tag = lambda *_args, **_kwargs: {"score": "", "details": ""}
    trader._get_strategy_kelly = lambda *_args, **_kwargs: None
    trader._get_agg_kelly_lot_boost = lambda: 1.0
    trader._get_aggregate_kelly = lambda: None
    trader._get_ruin_probability = lambda: None
    return trader, logs


def _sell_sig(entry_type: str, *, confidence: int = 70, score: float = -1.0, entry: float = 1.1000):
    return {
        "entry": entry,
        "signal": "SELL",
        "entry_type": entry_type,
        "confidence": confidence,
        "score": score,
        "sl": entry + 0.0015,
        "tp": entry - 0.0030,
        "atr": 0.0010,
        "reasons": [f"✅ edge-cell force-live test {entry_type}"],
        "regime": {"regime": "TREND_BEAR"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
    }


def _cfg():
    return {
        "label": "Daytrade",
        "icon": "D",
        "symbol": "EURUSD=X",
        "base_sl_pips": 15,
        "active_hours_utc": (0, 23),
    }


def _latest_trade(db: DemoDB):
    with db._safe_conn() as conn:
        return conn.execute(
            "SELECT edge_cell_id, is_shadow, oanda_trade_id FROM demo_trades ORDER BY id DESC LIMIT 1"
        ).fetchone()


@pytest.mark.parametrize(
    "case_name,hour,instrument,sig,setup,expected_cell,expected_source",
    [
        (
            "slot_bypass",
            8,
            "EUR_USD",
            _sell_sig("session_time_bias"),
            "seed_live_slot",
            "E8",
            "OTHER_UPSTREAM",
        ),
        (
            "eurusd_sell_alpha_shadow",
            8,
            "EUR_USD",
            _sell_sig("dt_bb_rsi_mr"),
            None,
            "E3",
            "OTHER_UPSTREAM",
        ),
        (
            "range_sell_shadow",
            8,
            "GBP_USD",
            _sell_sig("orb_trap", confidence=60),
            "range_regime",
            "E9",
            "OTHER_UPSTREAM",
        ),
        (
            "mtf_downgrade_shadow",
            8,
            "GBP_USD",
            _sell_sig("dt_bb_rsi_mr"),
            "mtf_conflict",
            "E5",
            "MTF_DOWNGRADE",
        ),
    ],
)
def test_edge_cell_force_live_overrides_shadow_sources(
    monkeypatch, tmp_path, case_name, hour, instrument, sig, setup, expected_cell, expected_source
):
    trader, logs = _make_trader(tmp_path, monkeypatch, hour=hour, price=sig["entry"])

    if setup == "seed_live_slot":
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
            instrument=instrument,
            is_shadow=False,
            oanda_trade_id="seed-oanda",
        )
    elif setup == "range_regime":
        sig["regime"] = {"regime": "RANGE"}
    elif setup == "mtf_conflict":
        import hashlib
        import research.edge_discovery.strategy_family_map as sfm

        class _FakeMD5:
            def hexdigest(self):
                return "00000000"

        monkeypatch.setattr(hashlib, "md5", lambda *_args, **_kwargs: _FakeMD5())
        monkeypatch.setattr(sfm, "strategy_aware_alignment", lambda *_args, **_kwargs: "conflict")

    trader._tick_entry("daytrade", _cfg(), sig, "15m", instrument)

    row = _latest_trade(trader._db)
    assert row["edge_cell_id"] == expected_cell, case_name
    assert row["is_shadow"] == 0, case_name
    assert row["oanda_trade_id"], case_name
    assert trader._oanda.calls, case_name
    expected_units = 2500 if expected_cell == "E5" else 5000
    assert trader._oanda.calls[-1]["units"] == expected_units
    assert any(
        f"[EDGE_CELL] {expected_cell} shadow→live force override "
        f"(was shadow due to: {expected_source})" in log
        for log in logs
    ), logs
