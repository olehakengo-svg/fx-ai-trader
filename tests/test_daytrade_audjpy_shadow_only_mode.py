"""15m AUD_JPY shadow-only mode (daytrade_audjpy) regression tests.

2026-07-10 user 承認 D2: WS3 stage-2 (htf_false_breakout×AUD_JPY 15m,
pre-reg 🔒 ws3-stage2-barrier-ev-prereg-2026-07-09) の shadow parity 検証準備
+ AUD_JPY 実測摩擦 (spread/slippage) 取得のための shadow-only モード新設。
live 変更なし・OANDA 発注ゼロが絶対条件。

Pins:
  (a) MODE_CONFIG エントリの構造
  (b) shadow-only 構造保証 — 最悪ケース (N<10 sentinel × strategy_mode=live
      × bridge active × SHADOW_MODE off) でも OANDA open_trade が呼ばれない
  (c) resend (補完送信) gate / write-path safeguard でも同判定が効く
  (d) control: 同一入力で mode だけ非 shadow_only にすると send に到達する
      (= (b) の block が shadow_only 起因であることの帰属証明)
"""
import uuid
from datetime import datetime as real_datetime, timezone

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
import tools.alpha_factor_snapshot as alpha_snap_mod
from modules.demo_db import DemoDB
from modules.demo_trader import (
    MODE_CONFIG,
    DemoTrader,
    _get_base_mode,
    _mode_is_shadow_only,
)


class _FixedDatetime(real_datetime):
    """2026-05-28 (木) 12:00 UTC — London 時間帯、週末/セッション block なし。"""

    @classmethod
    def now(cls, tz=None):
        base = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
        if tz is None:
            return base.replace(tzinfo=None)
        return base.astimezone(tz)


class _StubBridge:
    """最悪ケース bridge: active + 全モード許可 + operator 手動 live 昇格。"""

    def __init__(self):
        self.active = True
        self.sent = []
        self.audits = []

    def is_mode_allowed(self, _mode):
        return True

    def _add_audit(self, **kwargs):
        self.audits.append(kwargs)

    def get_strategy_mode(self, _entry_type):
        return "live"

    def open_trade(self, **kwargs):
        self.sent.append(kwargs)
        return True


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(
        DemoDB(str(tmp_path / f"audjpy_shadow_only_{uuid.uuid4().hex}.db"))
    )
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
    monkeypatch.setattr(trader, "_compute_dow_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(trader, "_compute_v2_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(
        trader, "_compute_confluence_tag", lambda *_a, **_k: {"score": 0, "details": ""}
    )
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_get_strategy_kelly", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_get_aggregate_kelly", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_get_ruin_probability", lambda *_a, **_k: None)
    # 最悪ケース: Phase0 SHADOW_MODE master switch が OFF の本番構成を模擬
    monkeypatch.setattr(trader, "_SHADOW_MODE", False)
    bridge = _StubBridge()
    monkeypatch.setattr(trader, "_oanda", bridge)
    return trader, bridge, logs


def _sig(entry_type="htf_false_breakout", signal="BUY", entry=97.500, tp=98.100):
    return {
        "signal": signal,
        "entry": entry,
        "tp": tp,
        "entry_type": entry_type,
        "confidence": 80,
        "score": 5.0 if signal == "BUY" else -5.0,
        "reasons": ["✅ unit-test"],
        "atr": 0.05,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }


def _rows(trader):
    with trader._db._safe_conn() as conn:
        return conn.execute(
            "SELECT trade_id, entry_type, instrument, mode, is_shadow "
            "FROM demo_trades"
        ).fetchall()


def _patch_common(monkeypatch):
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    monkeypatch.setattr(demo_trader_mod, "datetime", _FixedDatetime)
    monkeypatch.setattr(
        alpha_snap_mod, "snapshot_at", lambda *_a, **_k: {"error": "unit-test"}
    )


# ── (a) MODE_CONFIG structure pin ─────────────────────────────────


def test_mode_config_daytrade_audjpy_structure():
    cfg = MODE_CONFIG["daytrade_audjpy"]
    assert cfg["interval_sec"] == 30
    assert cfg["tf"] == "15m"
    assert cfg["period"] == "60d"
    assert cfg["signal_fn"] == "compute_daytrade_signal"
    assert cfg["label"] == "DT AUD/JPY (shadow)"
    assert cfg["symbol"] == "AUDJPY=X"
    assert cfg["instrument"] == "AUD_JPY"
    assert cfg["auto_start"] is True
    assert cfg["base_sl_pips"] == 15
    # shadow-only 構造保証フラグ — これを外す変更は R1 (Shadow→Live 昇格) 手続き必須
    assert cfg["shadow_only"] is True


def test_mode_is_shadow_only_helper():
    assert _mode_is_shadow_only("daytrade_audjpy") is True
    assert _mode_is_shadow_only("daytrade") is False
    assert _mode_is_shadow_only("daytrade_1h_audjpy") is False
    assert _mode_is_shadow_only("nonexistent_mode") is False


def test_base_mode_maps_daytrade_audjpy_to_daytrade():
    # cooldown (900s) / circuit breaker / regime gates が DT クラスで効くこと
    assert _get_base_mode("daytrade_audjpy") == "daytrade"


def test_no_other_mode_gained_shadow_only_flag():
    shadow_only_modes = {
        m for m, c in MODE_CONFIG.items() if c.get("shadow_only")
    }
    assert shadow_only_modes == {"daytrade_audjpy"}


# ── (b) shadow-only structural guarantee (worst case) ─────────────


def test_shadow_only_mode_blocks_oanda_even_for_sentinel_live_bypass(
    tmp_path, monkeypatch
):
    """最悪ケースで OANDA 発注ゼロを pin。

    条件: N=0 (<10 sentinel minlot 経路) × get_strategy_mode='live' (手動昇格)
    × bridge active × 全モード許可 × SHADOW_MODE off。
    htf_false_breakout は _SHIELD_EUR_DT_WHITELIST 登録済みのため
    _OANDA_MODE_BLOCKED 方式では bypass されてしまう — mode-level
    shadow_only gate が唯一の構造防壁であることをこのテストが保証する。
    """
    _patch_common(monkeypatch)
    trader, bridge, logs = _make_trader(tmp_path, monkeypatch)

    trader._tick_entry(
        "daytrade_audjpy",
        MODE_CONFIG["daytrade_audjpy"],
        _sig(),
        "15m",
        "AUD_JPY",
    )

    rows = _rows(trader)
    assert rows, "shadow trade row must be recorded (N 蓄積路の確保)"
    assert rows[0]["entry_type"] == "htf_false_breakout"
    assert rows[0]["instrument"] == "AUD_JPY"
    assert rows[0]["mode"] == "daytrade_audjpy"
    assert rows[0]["is_shadow"] == 1
    assert bridge.sent == [], "shadow-only mode must never reach OANDA open_trade"
    assert any("[SHADOW_ONLY_MODE] daytrade_audjpy" in m for m in logs)
    assert not any("[SENT]" in m for m in logs)


def test_control_same_signal_in_non_shadow_only_mode_reaches_oanda(
    tmp_path, monkeypatch
):
    """帰属証明 control: mode 名以外は完全同一の入力で send に到達する。

    これが green である限り、上のテストの block は「テストハーネスが
    どこか別の gate で落ちていた」のではなく shadow_only gate 起因である。
    同時に「N<10 sentinel が非 shadow-only モードでは live minlot (1000u)
    発注される」という罠そのものも pin する。
    """
    _patch_common(monkeypatch)
    trader, bridge, _logs = _make_trader(tmp_path, monkeypatch)

    trader._tick_entry(
        "daytrade",
        {"instrument": "AUD_JPY", "icon": "UT", "label": "unit-test-control"},
        _sig(),
        "15m",
        "AUD_JPY",
    )

    assert len(bridge.sent) == 1, "control must reach OANDA send"
    assert bridge.sent[0]["instrument"] == "AUD_JPY"
    # N<10 sentinel minlot — agg-Kelly gate を bypass して 1000u live になる経路
    assert bridge.sent[0]["units"] == 1000


# ── (c) resend gate + write-path safeguard ────────────────────────


def test_resend_promote_gate_blocks_shadow_only_mode(tmp_path, monkeypatch):
    trader, _bridge, _logs = _make_trader(tmp_path, monkeypatch)
    block = trader._resend_promote_gate_block_reason(
        "htf_false_breakout", "AUD_JPY", "daytrade_audjpy", confidence=80
    )
    assert block == "SHADOW_ONLY_MODE_GATE"
    # 非 shadow-only モードでは本 gate は発動しない (他 gate 判定へ委譲)
    assert (
        trader._resend_promote_gate_block_reason(
            "htf_false_breakout", "AUD_JPY", "daytrade", confidence=80
        )
        != "SHADOW_ONLY_MODE_GATE"
    )


def test_resend_pending_skips_shadow_only_mode_even_if_shadow_flag_flipped(
    tmp_path, monkeypatch
):
    """is_shadow 反転バグ (defense-in-depth 想定) でも補完送信されない。"""
    trader, bridge, logs = _make_trader(tmp_path, monkeypatch)

    trade_id = trader._db.open_trade(
        "BUY",
        97.500,
        97.350,
        98.100,
        entry_type="htf_false_breakout",
        confidence=80,
        tf="15m",
        mode="daytrade_audjpy",
        instrument="AUD_JPY",
        is_shadow=True,
    )
    # 反転バグを注入: is_shadow=0 かつ oanda_trade_id 空 → resend 候補化
    with trader._db._safe_conn() as conn:
        conn.execute(
            "UPDATE demo_trades SET is_shadow=0, entry_time=? WHERE trade_id=?",
            (real_datetime.now(timezone.utc).isoformat(), trade_id),
        )
        conn.commit()

    trader._resend_pending_oanda_trades()

    assert bridge.sent == [], "resend path must also be blocked for shadow-only mode"
    assert any("SHADOW_ONLY_MODE_GATE" in m for m in logs)


def test_resolve_is_shadow_for_write_forces_shadow_for_shadow_only_mode(
    tmp_path, monkeypatch
):
    trader, _bridge, _logs = _make_trader(tmp_path, monkeypatch)
    # fill 済みを装っても shadow で永続化 (fail-closed write-path)
    assert (
        trader._resolve_is_shadow_for_write(
            "htf_false_breakout",
            "AUD_JPY",
            "daytrade_audjpy",
            bridge_status="filled",
            oanda_trade_id="OANDA-999",
        )
        is True
    )
