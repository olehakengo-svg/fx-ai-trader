"""[SLTP_CONSTRUCT] / [BROKER_TP] row-marker pins (rule:R3 2026-09-26, record-only).

Why: `_tick_entry` の共有 SL/TP 経路 (C0a SR/ATR 選択 + MIN/MAX clamp、C0c 低流動性 /
fast-SL / カウンタートレンド / ラウンドナンバー、C0d MTF TP ×1.3、C0b quick-harvest) は
どの分岐を通ったかを row に残さなかった。kalman_d7 (PR #299 review 11 巡目) と
usdjpy_carry_dip_accumulator (16/16 で宣言 150p SL が 9.8–28.5p に置換、機構未特定) の
「live 実測率が導出できない」がここで閉じる。

Design (tests/test_pre_send_guard_observability_r3.py と同型のハーネス):
  - synthetic ELITE (trendline_sweep) で非 preserve 経路、preserve 型は
    tests/test_preserve_types_tick_entry.py と同じ sig で駆動。
  - marker は provenance のみ: is_shadow / sl / tp / 送信可否を変えない (最後の pin)。
  - 各 pin は「その分岐を通った入力 → marker の該当キーが 1 / 該当値」と
    「通らない入力 → 0 / 別値」の両側を持つ (片側だけの pin は恒真になり得る)。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime as real_datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
from modules.demo_db import DemoDB
from modules.demo_trader import (
    DemoTrader,
    _BROKER_TP_REASON_TAG,
    _SLTP_CONSTRUCT_REASON_TAG,
    _SLTP_TRACE_KEYS,
    _format_sltp_construct_marker,
    _new_sltp_trace,
    parse_sltp_construct_marker,
)

ELITE = "trendline_sweep"


def _pinned_datetime(now_utc: real_datetime):
    class _Pinned(real_datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return now_utc.replace(tzinfo=None)
            return now_utc.astimezone(tz)
    return _Pinned


_LONDON_THU_12 = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
_NYCLOSE_THU_21 = real_datetime(2026, 5, 28, 21, 0, tzinfo=timezone.utc)


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"sltp_{uuid.uuid4().hex}.db")))
    logs: list = []
    monkeypatch.setattr(trader, "_add_log", logs.append)
    monkeypatch.setattr(trader, "_check_drawdown", lambda: False)
    monkeypatch.setattr(
        trader._exposure_mgr, "check_new_trade", lambda *_a, **_k: (True, ""),
    )
    monkeypatch.setattr(
        trader, "_get_mtf_regime",
        lambda _inst: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": "normal"},
    )
    monkeypatch.setattr(trader, "_compute_dow_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(trader, "_compute_v2_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(
        trader, "_compute_confluence_tag", lambda *_a, **_k: {"score": 0, "details": ""},
    )
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_get_aggregate_kelly", lambda *_a, **_k: None)
    monkeypatch.setattr(trader, "_get_ruin_probability", lambda *_a, **_k: None)
    return trader, logs


def _sig(entry_type=ELITE, *, signal="BUY", entry=1.2000, tp=1.2060, sl=None,
         atr=0.0008, confidence=80, extra=None):
    # atr 0.0008 → ATR×1.0 SL = 8p (MIN 5p / MAX 20p の内側、clamp なし)。0.0005 だと
    # 浮動小数で MIN_SL_DIST 0.0005 をわずかに下回り clamp=min になる (marker は正直に報告する)。
    sig = {
        "signal": signal,
        "entry": entry,
        "tp": tp,
        "entry_type": entry_type,
        "confidence": confidence,
        "score": 1.0,
        "reasons": ["✅ unit-test"],
        "atr": atr,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }
    if sl is not None:
        sig["sl"] = sl
    if extra:
        sig.update(extra)
    return sig


def _cfg(instrument):
    return {"instrument": instrument, "icon": "UT", "label": "unit-test"}


def _fake_bridge(*, accept=True):
    fake = MagicMock()
    fake.active = True
    fake.is_mode_allowed.return_value = True
    fake.get_strategy_mode.return_value = "live"
    if accept:
        def _accept(**kwargs):
            cb = kwargs.get("callback")
            if cb:
                cb(kwargs["demo_trade_id"], "OANDA-TEST-1")
            return True
        fake.open_trade.side_effect = _accept
    else:
        fake.open_trade.return_value = False
    return fake


def _promote_synthetic_elite(monkeypatch, now=_LONDON_THU_12):
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    monkeypatch.setattr(demo_trader_mod, "datetime", _pinned_datetime(now))
    monkeypatch.setattr(DemoTrader, "_ELITE_LIVE", frozenset({ELITE}))
    monkeypatch.setattr(
        DemoTrader, "_PAIR_DEMOTED",
        {c for c in DemoTrader._PAIR_DEMOTED if c[0] != ELITE},
    )


def _run(tmp_path, monkeypatch, *, sig, instrument="EUR_USD", now=_LONDON_THU_12,
         bridge=None, mode="daytrade", tf="15m", setup=None):
    _promote_synthetic_elite(monkeypatch, now)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    monkeypatch.setattr(trader, "_oanda", bridge or _fake_bridge(accept=False))
    if setup:
        setup(trader)
    trader._tick_entry(mode, _cfg(instrument), sig, tf, instrument)
    return trader, logs


def _rows(trader):
    with trader._db._safe_conn() as conn:
        return conn.execute(
            "SELECT trade_id, is_shadow, oanda_trade_id, entry_price, sl, tp, reasons "
            "FROM demo_trades"
        ).fetchall()


def _reasons(row) -> list:
    raw = row["reasons"]
    try:
        out = json.loads(raw) if raw else []
    except Exception:
        out = [raw]
    return out if isinstance(out, list) else [out]


def _marker(trader) -> dict:
    rows = _rows(trader)
    assert rows, f"expected a demo_trades row; blocks={trader._block_counts_per_strategy}"
    parsed = parse_sltp_construct_marker(_reasons(rows[0]))
    assert parsed is not None, _reasons(rows[0])
    return parsed


# ── 1. formatter / parser contract ─────────────────────────────────────────


def test_marker_format_has_every_key_in_stable_order():
    trace = _new_sltp_trace(1.1950, 1.2060)
    m = _format_sltp_construct_marker(trace, current_price=1.2000, sl=1.1950,
                                      tp=1.2060, pip_mult=10000)
    assert m.startswith(_SLTP_CONSTRUCT_REASON_TAG + " ")
    keys = [kv.split("=")[0] for kv in m.split(" ")[1:]]
    assert keys == list(_SLTP_TRACE_KEYS) + ["decl_sl_p", "sl_p", "decl_tp_p", "tp_p"]
    parsed = parse_sltp_construct_marker(["✅ x", m, "[EMIT_PROC] import:autostart"])
    assert parsed["sl"] == "unset" and parsed["decl_sl_p"] == "50.0"
    assert parsed["sl_p"] == "50.0" and parsed["tp_p"] == "60.0"


def test_marker_format_na_when_declared_sl_missing():
    trace = _new_sltp_trace(0, 1.2060)
    m = _format_sltp_construct_marker(trace, current_price=1.2000, sl=1.1950,
                                      tp=1.2060, pip_mult=10000)
    assert " decl_sl_p=na " in m
    assert parse_sltp_construct_marker(["no marker here"]) is None
    assert parse_sltp_construct_marker(None) is None


# ── 2. SL 選択枝 (C0a) ─────────────────────────────────────────────────────


def test_atr_fallback_when_no_sr_map(tmp_path, monkeypatch):
    trader, _ = _run(tmp_path, monkeypatch, sig=_sig())
    m = _marker(trader)
    assert m["sl"] == "atr_nosr", m
    assert m["clamp"] == "none" and m["lowliq"] == "0" and m["fastsl"] == "0"
    assert m["ct"] == "0" and m["rn"] == "0" and m["mtf_tp"] == "1.0"
    assert m["decl_sl_p"] == "na"  # sig に sl なし
    row = _rows(trader)[0]
    # marker が報告する距離は挿入された行の sl/tp と一致する (provenance の自己整合)
    assert abs(float(m["sl_p"]) - abs(row["entry_price"] - row["sl"]) * 10000) < 0.11
    assert abs(float(m["tp_p"]) - abs(row["tp"] - row["entry_price"]) * 10000) < 0.11


def test_sr_stop_selected_when_rr_floor_met(tmp_path, monkeypatch):
    # nearest_support 1.1985 − margin(0.3×ATR=0.00024) = 1.19826 → dist 17.4p (< MAX 20p、
    # RR 3.4 ≥ 1.0)。support を遠くに置くと SR 採用のまま clamp=max が立つ (別 pin 参照)
    sig = _sig(extra={"sr_entry_map": {"nearest_support": {"price": 1.1985}}})
    trader, _ = _run(tmp_path, monkeypatch, sig=sig)
    m = _marker(trader)
    assert m["sl"] == "sr" and m["clamp"] == "none", m
    assert abs(float(m["sl_p"]) - 17.4) < 0.2

    # SR 採用 + cap: support 1.1970 → dist 32.4p > 20p → sl=sr かつ clamp=max、sl_p=20
    sig2 = _sig(extra={"sr_entry_map": {"nearest_support": {"price": 1.1970}}})
    trader2, _ = _run(tmp_path, monkeypatch, sig=sig2)
    m2 = _marker(trader2)
    assert m2["sl"] == "sr" and m2["clamp"] == "max", m2
    assert abs(float(m2["sl_p"]) - 20.0) < 0.2


def test_sr_stop_rejected_by_rr_floor_falls_back_to_atr(tmp_path, monkeypatch):
    # support far away: dist 0.0100 vs tp_dist 0.0060 → RR 0.6 < 1.0 → ATR 退避
    sig = _sig(extra={"sr_entry_map": {"nearest_support": {"price": 1.1900}}})
    trader, _ = _run(tmp_path, monkeypatch, sig=sig)
    m = _marker(trader)
    assert m["sl"] == "atr_rrlow", m


def test_preserve_type_marker_reports_declared_sl(tmp_path, monkeypatch):
    sig = _sig("keltner_squeeze_breakout", sl=1.1960, tp=1.2080, entry=1.2000)
    trader, _ = _run(tmp_path, monkeypatch, sig=sig, tf="1h")
    m = _marker(trader)
    assert m["sl"] == "preserve", m
    assert m["decl_sl_p"] == "40.0" and m["sl_p"] == "40.0"


# ── 3. clamp ───────────────────────────────────────────────────────────────


def test_max_clamp_flagged_when_atr_sl_exceeds_cap(tmp_path, monkeypatch):
    # EUR_USD daytrade: ATR×1.0 = 0.0050 > MAX_SL_DIST 0.0020 → clamp=max, sl_p=20
    sig = _sig(atr=0.0050, tp=1.2100)
    trader, _ = _run(tmp_path, monkeypatch, sig=sig)
    m = _marker(trader)
    assert m["clamp"] == "max", m
    assert abs(float(m["sl_p"]) - 20.0) < 0.2


def test_min_clamp_flagged_when_atr_sl_below_floor(tmp_path, monkeypatch):
    # ATR×1.0 = 0.0002 < MIN_SL_DIST 0.0005 → clamp=min, sl_p=5
    sig = _sig(atr=0.0002, tp=1.2010)
    trader, _ = _run(tmp_path, monkeypatch, sig=sig)
    m = _marker(trader)
    assert m["clamp"] == "min", m
    assert abs(float(m["sl_p"]) - 5.0) < 0.2


# ── 4. C0c buffers ─────────────────────────────────────────────────────────


def test_lowliq_buffer_flag_follows_utc_hour(tmp_path, monkeypatch):
    # 21 UTC ∈ _low_liq_hours。EUR_USD は promoted 経路で session_pair (Late NY) に
    # 落ちるので USD_JPY (静的 H16-20 block の外) で駆動。ATR SL 150.100 (frac .100 →
    # rn なし) に +0.2×ATR=0.038 → 150.062。
    sig = _sig(entry=150.290, tp=150.700, atr=0.19)
    trader, _ = _run(tmp_path, monkeypatch, sig=sig, instrument="USD_JPY",
                     now=_NYCLOSE_THU_21)
    m = _marker(trader)
    assert m["lowliq"] == "1" and m["rn"] == "0", m
    assert abs(float(m["sl_p"]) - 22.8) < 0.2  # 19.0 + 3.8

    # 対照: 同じ入力を 12 UTC で流すと lowliq=0、sl_p=19.0
    trader2, _ = _run(tmp_path, monkeypatch, sig=_sig(entry=150.290, tp=150.700, atr=0.19),
                      instrument="USD_JPY")
    m2 = _marker(trader2)
    assert m2["lowliq"] == "0" and abs(float(m2["sl_p"]) - 19.0) < 0.2, m2


def test_fast_sl_buffer_flag_follows_recent_history(tmp_path, monkeypatch):
    # 200s 前の fast SL (hold 60s < 120s): cascade_cd (daytrade 90s) の外、fast-SL 窓 (5 分) の内
    _ago = _LONDON_THU_12 - timedelta(seconds=200)

    def _seed(trader):
        trader._sl_hit_history.append((_ago, "EUR_USD", ELITE, 60))
    trader, _ = _run(tmp_path, monkeypatch, sig=_sig(), setup=_seed)
    m = _marker(trader)
    assert m["fastsl"] == "1", m

    def _seed_other_pair(trader):
        trader._sl_hit_history.append((_ago, "USD_JPY", ELITE, 60))
    trader2, _ = _run(tmp_path, monkeypatch, sig=_sig(), setup=_seed_other_pair)
    assert _marker(trader2)["fastsl"] == "0"


def test_round_number_nudge_flag_on_jpy(tmp_path, monkeypatch):
    # USD_JPY daytrade: entry 150.190, ATR 0.19 → ATR SL 150.000 (= .000 ラウンド) → nudge
    sig = _sig(entry=150.190, tp=150.600, atr=0.19)
    trader, _ = _run(tmp_path, monkeypatch, sig=sig, instrument="USD_JPY")
    m = _marker(trader)
    assert m["rn"] == "1", m
    row = _rows(trader)[0]
    assert abs(row["sl"] - 149.975) < 1e-6  # 2.5pip 外側

    # 対照: SL が .300 に落ちる入力では nudge しない
    sig2 = _sig(entry=150.490, tp=150.900, atr=0.19)
    trader2, _ = _run(tmp_path, monkeypatch, sig=sig2, instrument="USD_JPY")
    assert _marker(trader2)["rn"] == "0"


# ── 5. C0d MTF TP bonus ────────────────────────────────────────────────────


def test_mtf_tp_bonus_recorded_when_strong_bias_aligned(tmp_path, monkeypatch):
    def _bias(trader):
        trader._15m_tactical_bias["EUR_USD"] = {
            "direction": "BUY", "entry_type": "x", "confidence": 80,
            "updated_at": _LONDON_THU_12, "signal_price": 1.2, "strength": "strong",
        }
    trader, _ = _run(tmp_path, monkeypatch, sig=_sig(), setup=_bias)
    m = _marker(trader)
    assert m["mtf_tp"] == "1.3", m
    assert abs(float(m["tp_p"]) - 78.0) < 0.2  # 60p × 1.3
    assert m["decl_tp_p"] == "60.0"


# ── 6. [BROKER_TP] (C0b) ───────────────────────────────────────────────────


def test_broker_tp_marker_records_quick_harvest_on_send(tmp_path, monkeypatch):
    trader, _ = _run(tmp_path, monkeypatch, sig=_sig(), bridge=_fake_bridge(accept=True))
    rows = _rows(trader)
    assert rows and rows[0]["oanda_trade_id"] == "OANDA-TEST-1"
    reasons = _reasons(rows[0])
    btp = [r for r in reasons if r.startswith(_BROKER_TP_REASON_TAG + " ")]
    assert btp, reasons
    assert " basis=qh " in btp[0] and f" mult={DemoTrader._QUICK_HARVEST_MULT} " in btp[0]
    assert btp[0].endswith(" tp_p=51.0")  # 60p × 0.85
    # demo 行の tp 列は宣言のまま (marker は記録のみ)
    assert abs(rows[0]["tp"] - 1.2060) < 1e-9


def test_broker_tp_marker_present_even_when_bridge_refuses(tmp_path, monkeypatch):
    trader, _ = _run(tmp_path, monkeypatch, sig=_sig(), bridge=_fake_bridge(accept=False))
    reasons = _reasons(_rows(trader)[0])
    assert any(r.startswith(_BROKER_TP_REASON_TAG + " basis=qh ") for r in reasons), reasons


# ── 7. record-only: 選択子・数値は marker なしの世界と同一 ───────────────────


def test_marker_is_record_only(tmp_path, monkeypatch):
    """同じ入力を marker 生成を無効化した trader で流し、row の is_shadow / sl / tp が
    一致することを pin する (marker が値や送信判定に介入していない)。"""
    trader_a, _ = _run(tmp_path, monkeypatch, sig=_sig(), bridge=_fake_bridge(accept=True))
    row_a = _rows(trader_a)[0]

    monkeypatch.setattr(
        demo_trader_mod, "_format_sltp_construct_marker",
        lambda *_a, **_k: "[SLTP_CONSTRUCT] disabled",
    )
    trader_b, _ = _run(tmp_path, monkeypatch, sig=_sig(), bridge=_fake_bridge(accept=True))
    row_b = _rows(trader_b)[0]
    assert (row_a["is_shadow"], row_a["sl"], row_a["tp"], row_a["oanda_trade_id"]) == \
        (row_b["is_shadow"], row_b["sl"], row_b["tp"], row_b["oanda_trade_id"])
