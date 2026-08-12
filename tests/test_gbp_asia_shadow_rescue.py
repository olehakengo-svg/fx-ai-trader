"""gbp_asia_flash_crash gate の cell 限定 shadow 退避 pin (2026-08-12 rule:R3).

zero-fire forensic (knowledge-base/wiki/analyses/sweep-zero-fire-forensic-2026-08-12.md):
sweep_reversion_eurgbp_late は LATE 窓 (21-24 UTC) が gbp_asia ブロック帯 (21-06) に
100% 内包される。HTF Hard Block が外れた regime では本 gate の rowless hard block に
落ち、P-S1(a) トリガ分母が silent 枯渇した (07-26/07-29/08-06/08-09 の 4 イベント消失)。

Pin する契約:
1. rescue cell (sweep_reversion_eurgbp_late × EUR_GBP) はゾーン内で shadow row として
   記録される (is_shadow=1、OANDA 送信なし)
2. rescue 集合外はゾーン内で従来どおり rowless hard block (defense 縮小なし)
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone

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
            callback(kwargs["demo_trade_id"], f"gbp-asia-test-{len(self.calls)}")
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
            value = cls(2026, 8, 12, hour, 0, tzinfo=timezone.utc)
            return value if tz is None else value.astimezone(tz)

    return FixedDateTime


def _make_trader(tmp_path, monkeypatch, *, hour: int, price: float = 0.8560):
    from modules import data as data_mod
    import modules.demo_trader as demo_trader_mod
    from modules.demo_trader import DemoTrader

    logs = []
    monkeypatch.setattr(demo_trader_mod, "datetime", _fixed_datetime(hour))
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask",
                        lambda _inst: {"bid": price, "ask": price + 0.0001})
    monkeypatch.setattr(demo_trader_mod, "classify_prime", lambda *_args, **_kwargs: None)

    trader = DemoTrader.__new__(DemoTrader)
    trader._db = DemoDB(str(tmp_path / "gbp-asia-rescue.db"))
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


def _sweep_buy_sig(entry: float = 0.8560, atr: float = 0.0007, entry_type: str = "sweep_reversion_eurgbp_late"):
    return {
        "entry": entry,
        "signal": "BUY",
        "entry_type": entry_type,
        "confidence": 65,
        "score": 3.5,
        "sl": entry - 4.0 * atr,
        "tp": entry + 6.0 * atr,
        "atr": atr,
        "reasons": ["✅ gbp-asia shadow rescue pin"],
        "regime": {"regime": "RANGE"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
        "max_hold_bars": 48,
    }


def _cfg(symbol: str = "EURGBP=X"):
    return {
        "label": "DT EUR/GBP",
        "icon": "D",
        "symbol": symbol,
        "base_sl_pips": 15,
        "active_hours_utc": (0, 23),
    }


def _rows(db: DemoDB, entry_type: str):
    with db._safe_conn() as conn:
        return conn.execute(
            "SELECT entry_type, instrument, is_shadow, oanda_trade_id FROM demo_trades "
            "WHERE entry_type = ? ORDER BY id",
            (entry_type,),
        ).fetchall()


def _gbp_asia_blocks(trader):
    return {k: v for k, v in trader._block_counts.items() if "gbp_asia_flash_crash" in k}


def test_sweep_cell_shadow_rescued_in_gbp_asia_zone(tmp_path, monkeypatch):
    trader, _logs = _make_trader(tmp_path, monkeypatch, hour=22)

    trader._tick_entry("daytrade_eurgbp", _cfg(), _sweep_buy_sig(), "15m", "EUR_GBP")

    rows = _rows(trader._db, "sweep_reversion_eurgbp_late")
    assert rows, "rescue cell must write a shadow row inside the gbp_asia zone (4原則#3)"
    for _et, inst, is_shadow, oanda_id in rows:
        assert inst == "EUR_GBP"
        assert is_shadow == 1, "rescue is shadow-only — live 例外は P-S1(a) Option B のみ"
        assert not oanda_id, "shadow row must not carry an OANDA trade id"
    assert not trader._oanda.calls, "rescue must not send to OANDA"
    assert not _gbp_asia_blocks(trader), "rescue cell must not be counted as gbp_asia hard block"


def test_non_rescued_cell_still_hard_blocked(tmp_path, monkeypatch):
    trader, _logs = _make_trader(tmp_path, monkeypatch, hour=22, price=1.2800)

    # 同じ entry_type でも rescue 集合外の instrument (GBP_USD) は従来どおり
    # rowless hard block — cell 限定であることを固定する
    trader._tick_entry(
        "daytrade_gbpusd", _cfg("GBPUSD=X"),
        _sweep_buy_sig(entry=1.2800, atr=0.0010), "15m", "GBP_USD",
    )

    assert not _rows(trader._db, "sweep_reversion_eurgbp_late"), \
        "non-rescued cell must not write any row"
    assert not trader._oanda.calls
    assert _gbp_asia_blocks(trader), "non-rescued cell must hit the gbp_asia hard block"


def test_rescue_inactive_outside_gbp_asia_zone(tmp_path, monkeypatch):
    trader, _logs = _make_trader(tmp_path, monkeypatch, hour=12)

    trader._tick_entry("daytrade_eurgbp", _cfg(), _sweep_buy_sig(), "15m", "EUR_GBP")

    # ゾーン外では gbp_asia gate 自体が非適用 (block も rescue も発生しない)
    assert not _gbp_asia_blocks(trader)
