"""Bridge send-accept contract regression tests (2026-07-02 gate-asymmetry fix).

Incident: 2026-07-01 20:16 UTC wick_imbalance_reversion GBP_USD BUY —
OandaBridge's daily-loss gate correctly refused transmission and wrote its
own 'blocked' audit row, but demo_trader's main-entry path wrote an
unconditional caller-side 'sent' row right after the open_trade() call.
Result: contradictory 'sent'+'blocked' audit pairs, and an is_shadow=0
trade with oanda_trade_id=NULL polluting clean-live aggregates
(FLAG_DRIFT) and eligible for gate-bypassing resend after restart.
Same pattern observed 2026-06-16/17/19.

Contract under test (rule:R3):
  1. OandaBridge.open_trade() returns True only when all bridge gates
     passed and the background send was fired; False on every refusal
     path (inactive / unsupported instrument / mode excluded /
     daily-loss halt).
  2. demo_trader's promoted path writes the 'sent' audit row ONLY when
     open_trade() returned True; on refusal it writes no 'sent' row and
     escalates the trade to shadow.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime as real_datetime, timezone
from unittest.mock import MagicMock

import pytest

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader
from modules.oanda_bridge import OandaBridge


class _LondonDatetime(real_datetime):
    """Pin 'now' to a London-session weekday so session/pair guards
    do not depend on the wall-clock at test runtime."""

    @classmethod
    def now(cls, tz=None):
        base = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
        if tz is None:
            return base.replace(tzinfo=None)
        return base.astimezone(tz)


# ── 1. Bridge-level return contract ──────────────────────────────


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield DemoDB(db_path=path)
    os.unlink(path)


def _bridge(db, monkeypatch, *, limit_pips: float = 20.0) -> OandaBridge:
    monkeypatch.setenv("DAILY_LOSS_LIMIT_PIPS", str(limit_pips))
    monkeypatch.setenv("OANDA_LIVE", "true")
    b = OandaBridge(db=db)
    b._daily_loss_cache_ttl_s = 0.0
    return b


def test_open_trade_returns_false_when_inactive(db, monkeypatch):
    b = _bridge(db, monkeypatch)
    monkeypatch.setattr(type(b), "active", property(lambda self: False))
    assert b.open_trade(
        demo_trade_id="D1", direction="BUY", sl=149.5, tp=151.0,
        mode="scalp", instrument="USD_JPY", units=1000,
    ) is False


def test_open_trade_returns_false_when_mode_not_allowed(db, monkeypatch):
    """is_mode_allowed is always-True in v9.0; contract still requires the
    refusal path to return False if a mode exclusion is ever reintroduced."""
    b = _bridge(db, monkeypatch)
    monkeypatch.setattr(type(b), "active", property(lambda self: True))
    monkeypatch.setattr(b, "is_mode_allowed", lambda _mode: False)
    assert b.open_trade(
        demo_trade_id="D2", direction="BUY", sl=149.5, tp=151.0,
        mode="daytrade", instrument="USD_JPY", units=1000,
    ) is False


def test_open_trade_returns_false_when_daily_loss_gate_blocks(db, monkeypatch):
    b = _bridge(db, monkeypatch)
    monkeypatch.setattr(type(b), "active", property(lambda self: True))
    monkeypatch.setattr(b, "is_mode_allowed", lambda _mode: True)
    monkeypatch.setattr(b, "_check_daily_loss_gate", lambda: (True, -42.0))
    assert b.open_trade(
        demo_trade_id="D3", direction="SELL", sl=150.5, tp=149.0,
        mode="scalp", instrument="USD_JPY", units=1000,
    ) is False


def test_open_trade_returns_true_when_gates_pass(db, monkeypatch):
    b = _bridge(db, monkeypatch)
    monkeypatch.setattr(type(b), "active", property(lambda self: True))
    monkeypatch.setattr(b, "is_mode_allowed", lambda _mode: True)
    monkeypatch.setattr(b, "_check_daily_loss_gate", lambda: (False, 0.0))
    fired = []
    monkeypatch.setattr(b, "_fire", lambda fn: fired.append(fn))
    assert b.open_trade(
        demo_trade_id="D4", direction="BUY", sl=149.5, tp=151.0,
        mode="scalp", instrument="USD_JPY", units=1000,
    ) is True
    assert len(fired) == 1, "background send must have been fired"


# ── 2. demo_trader caller contract (integration) ─────────────────


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"accept_{uuid.uuid4().hex}.db")))
    logs = []
    monkeypatch.setattr(trader, "_add_log", logs.append)
    monkeypatch.setattr(trader, "_check_drawdown", lambda: False)
    monkeypatch.setattr(
        trader._exposure_mgr, "check_new_trade",
        lambda *_a, **_k: (True, ""),
    )
    monkeypatch.setattr(
        trader, "_get_mtf_regime",
        lambda _inst: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": "normal"},
    )
    monkeypatch.setattr(trader, "_compute_dow_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(trader, "_compute_v2_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(
        trader, "_compute_confluence_tag",
        lambda *_a, **_k: {"score": 0, "details": ""},
    )
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: None)
    return trader, logs


def _sig(entry_type="trendline_sweep", signal="BUY", entry=1.2000, tp=1.2060):
    return {
        "signal": signal,
        "entry": entry,
        "tp": tp,
        "entry_type": entry_type,
        "confidence": 80,
        "score": 1.0,
        "reasons": ["✅ unit-test"],
        "atr": 0.0005,
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }


def _cfg(instrument):
    return {"instrument": instrument, "icon": "UT", "label": "unit-test"}


def _fake_bridge(*, accept: bool) -> MagicMock:
    fake = MagicMock()
    fake.active = True
    fake.is_mode_allowed.return_value = True
    if accept:
        # Simulate the full happy path: bridge accepts, background send
        # fills, and the fill callback stamps the OANDA trade id (the
        # only path to is_shadow=0 under the flag-drift invariant).
        def _accept(**kwargs):
            cb = kwargs.get("callback")
            if cb:
                cb(kwargs["demo_trade_id"], "OANDA-TEST-1")
            return True
        fake.open_trade.side_effect = _accept
    else:
        fake.open_trade.return_value = False
    return fake


def _run_promoted_signal(tmp_path, monkeypatch, *, accept: bool):
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    monkeypatch.setattr(demo_trader_mod, "datetime", _LondonDatetime)
    trader, logs = _make_trader(tmp_path, monkeypatch)
    fake = _fake_bridge(accept=accept)
    monkeypatch.setattr(trader, "_oanda", fake)
    trader._tick_entry(
        "daytrade", _cfg("EUR_USD"), _sig(entry_type="trendline_sweep"),
        "15m", "EUR_USD",
    )
    with trader._db._safe_conn() as conn:
        rows = conn.execute(
            "SELECT trade_id, is_shadow FROM demo_trades"
        ).fetchall()
    audit_statuses = [
        c.kwargs.get("bridge_status")
        for c in fake._add_audit.call_args_list
    ]
    return fake, rows, audit_statuses, logs


def test_bridge_refusal_writes_no_sent_audit_and_escalates_shadow(tmp_path, monkeypatch):
    fake, rows, audit_statuses, logs = _run_promoted_signal(
        tmp_path, monkeypatch, accept=False,
    )
    assert fake.open_trade.called, "promoted ELITE path must reach the bridge"
    assert "sent" not in audit_statuses, (
        f"caller must not write 'sent' when the bridge refused: {audit_statuses}"
    )
    assert rows and all(r["is_shadow"] == 1 for r in rows), (
        "refused transmission must escalate the trade to shadow"
    )
    assert any("[SHADOW_FIX] Bridge refused transmission" in m for m in logs)


def test_bridge_acceptance_writes_sent_audit_and_stays_live(tmp_path, monkeypatch):
    fake, rows, audit_statuses, logs = _run_promoted_signal(
        tmp_path, monkeypatch, accept=True,
    )
    assert fake.open_trade.called
    assert "sent" in audit_statuses, (
        f"accepted transmission must record 'sent': {audit_statuses}"
    )
    assert rows and all(r["is_shadow"] == 0 for r in rows), (
        "accepted+filled transmission must keep the trade live (is_shadow=0)"
    )
    assert not any("[SHADOW_FIX] Bridge refused transmission" in m for m in logs)
