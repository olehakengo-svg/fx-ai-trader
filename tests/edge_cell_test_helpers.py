from __future__ import annotations

import threading
from datetime import datetime, timezone

from modules.demo_db import DemoDB


class OandaMock:
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
            callback(kwargs["demo_trade_id"], f"edge-e2e-{len(self.calls)}")
        # 2026-07-02 send-accept contract: True = gates passed, send fired.
        return True


class ExposureMock:
    def check_new_trade(self, *_args, **_kwargs):
        return True, ""

    def add_position(self, *_args, **_kwargs):
        return None

    def set_shadow_status(self, *_args, **_kwargs):
        return None


class AlertMock:
    def alert_exposure_blocked(self, *_args, **_kwargs):
        return None


def fixed_datetime(hour: int):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 5, 26, hour, 0, tzinfo=timezone.utc)
            return value if tz is None else value.astimezone(tz)

    return FixedDateTime


def make_trader(tmp_path, monkeypatch, *, hour: int):
    import modules.data as data_mod
    import modules.demo_trader as demo_trader_mod
    from modules.demo_trader import DemoTrader

    logs = []
    monkeypatch.setattr(demo_trader_mod, "datetime", fixed_datetime(hour))
    monkeypatch.setattr(demo_trader_mod, "classify_prime", lambda *_args, **_kwargs: None)
    # _tick_entry は modules.data.fetch_oanda_bid_ask で実勢 bid/ask を引く。
    # suite 内で app が import 済みだと (.env ロード経由で) 実ネットワークの
    # 価格が返り、fixture の entry/tp/sl と実勢価格の乖離次第で rr_floor 等の
    # 手前の gate に落ちてテスト結果が市場価格依存になる。常に None に固定。
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda *_a, **_k: None)

    trader = DemoTrader.__new__(DemoTrader)
    trader._db = DemoDB(str(tmp_path / "edge-e2e.db"))
    trader._lock = threading.RLock()
    trader._oanda = OandaMock()
    trader._exposure_mgr = ExposureMock()
    trader._alert_mgr = AlertMock()
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


def edge_cfg():
    return {
        "label": "Daytrade",
        "icon": "D",
        "symbol": "EURUSD=X",
        "base_sl_pips": 15,
        "active_hours_utc": (0, 23),
    }


def session_time_bias_sell_sig(entry: float):
    return {
        "entry": entry,
        "signal": "SELL",
        "entry_type": "session_time_bias",
        "confidence": 70,
        "score": -1.0,
        "sl": entry + 0.0015,
        "tp": entry - 0.0030,
        "atr": 0.0010,
        "reasons": ["✅ edge-cell E8 force-fire"],
        "regime": {"regime": "TREND_BEAR"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
    }
