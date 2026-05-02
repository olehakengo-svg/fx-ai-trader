"""Daily Loss Gate regression tests (audit 2026-05-01 P0-2).

The gate enforces a transmit-only halt when today's Live `total_pnl`
(is_shadow=0, exclude_xau, exclude_seed) drops below the configured
threshold. demo_trader is unaffected; only OANDA forwarding is suppressed.

Tests cover:
  1. Gate disabled (limit <= 0) always allows
  2. Below threshold blocks with the correct cached value
  3. Above-but-near threshold permits
  4. Cache is honored within TTL (no DB hit on second call)
  5. open_trade short-circuits before retrying when the gate blocks
  6. Audit row is written with bridge_status='blocked' on halt
"""
from __future__ import annotations

import os
import tempfile
import threading
from unittest.mock import MagicMock, patch

import pytest

from modules.demo_db import DemoDB
from modules.oanda_bridge import OandaBridge


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield DemoDB(db_path=path)
    os.unlink(path)


def _bridge(db, monkeypatch, *, limit_pips: float = 20.0,
            ttl: float = 0.0) -> OandaBridge:
    monkeypatch.setenv("DAILY_LOSS_LIMIT_PIPS", str(limit_pips))
    monkeypatch.setenv("OANDA_LIVE", "true")
    b = OandaBridge(db=db)
    b._daily_loss_cache_ttl_s = ttl  # bypass cache between assertions
    return b


def test_gate_disabled_when_limit_zero(db, monkeypatch):
    b = _bridge(db, monkeypatch, limit_pips=0)
    blocked, pnl = b._check_daily_loss_gate()
    assert blocked is False
    assert pnl == 0.0


def test_gate_blocks_when_today_pnl_below_threshold(db, monkeypatch):
    b = _bridge(db, monkeypatch, limit_pips=20)
    fake_stats = {"total_pnl": -25.5, "total": 5}
    with patch.object(db, "get_stats", return_value=fake_stats) as gs:
        blocked, pnl = b._check_daily_loss_gate()
    assert gs.called
    assert gs.call_args.kwargs["date_field"] == "exit_time"
    assert blocked is True
    assert pnl == pytest.approx(-25.5)


def test_gate_permits_when_today_pnl_above_threshold(db, monkeypatch):
    b = _bridge(db, monkeypatch, limit_pips=20)
    fake_stats = {"total_pnl": -15.0, "total": 5}
    with patch.object(db, "get_stats", return_value=fake_stats):
        blocked, pnl = b._check_daily_loss_gate()
    assert blocked is False
    assert pnl == pytest.approx(-15.0)


def test_gate_at_exact_threshold_blocks(db, monkeypatch):
    """`<=` boundary: -20 with limit 20 must block (defensive)."""
    b = _bridge(db, monkeypatch, limit_pips=20)
    with patch.object(db, "get_stats", return_value={"total_pnl": -20.0}):
        blocked, _ = b._check_daily_loss_gate()
    assert blocked is True


def test_gate_cache_avoids_repeat_db_calls(db, monkeypatch):
    b = _bridge(db, monkeypatch, limit_pips=20, ttl=300.0)  # very long TTL
    with patch.object(db, "get_stats", return_value={"total_pnl": -25.0}) as gs:
        b._check_daily_loss_gate()
        b._check_daily_loss_gate()
        b._check_daily_loss_gate()
    assert gs.call_count == 1, "cache must coalesce repeat calls inside TTL"


def test_gate_latches_until_utc_day_rollover(db, monkeypatch):
    """Once tripped, the halt remains active for the UTC day.

    Existing OANDA positions can close after the halt and improve same-day
    realized PnL; the roadmap rule is still a rest-of-day transmit halt.
    """
    b = _bridge(db, monkeypatch, limit_pips=20)
    with patch.object(db, "get_stats", side_effect=[
        {"total_pnl": -25.0},
        {"total_pnl": 5.0},
    ]) as gs:
        blocked_1, pnl_1 = b._check_daily_loss_gate()
        b._daily_loss_cache_ts = 0.0  # prove the latch, not cache, blocks
        blocked_2, pnl_2 = b._check_daily_loss_gate()
    assert blocked_1 is True
    assert pnl_1 == pytest.approx(-25.0)
    assert blocked_2 is True
    assert pnl_2 == pytest.approx(-25.0)
    assert gs.call_count == 1


def test_gate_fails_open_on_db_error(db, monkeypatch):
    """If get_stats raises, the gate must NOT block (fail-open)."""
    b = _bridge(db, monkeypatch, limit_pips=20)
    with patch.object(db, "get_stats", side_effect=RuntimeError("boom")):
        blocked, pnl = b._check_daily_loss_gate()
    assert blocked is False
    assert pnl == 0.0


def test_open_trade_short_circuits_when_blocked(db, monkeypatch):
    b = _bridge(db, monkeypatch, limit_pips=20)
    # Force active and mode-allowed
    monkeypatch.setattr(type(b), "active", property(lambda self: True))
    b._allowed_modes = {"scalp"}

    def _blocked():
        return True, -42.0

    market_order = MagicMock(return_value=(True, {"orderFillTransaction": {"tradeOpened": {"tradeID": "X"}}}))
    monkeypatch.setattr(b, "_check_daily_loss_gate", _blocked)
    monkeypatch.setattr(b._client, "market_order", market_order)

    b.open_trade(
        demo_trade_id="DEMO_X", direction="BUY", sl=149.5, tp=151.0,
        mode="scalp", instrument="USD_JPY", units=1000,
    )
    # Bridge must NOT call market_order when the gate blocks (transmit-only halt)
    assert market_order.call_count == 0


def test_blocked_transmit_writes_audit_row(db, monkeypatch):
    b = _bridge(db, monkeypatch, limit_pips=20)
    monkeypatch.setattr(type(b), "active", property(lambda self: True))
    b._allowed_modes = {"scalp"}
    monkeypatch.setattr(b, "_check_daily_loss_gate", lambda: (True, -42.0))

    captured = []
    real_add = b._add_audit

    def _spy(**kw):
        captured.append(kw)
        return real_add(**kw)
    monkeypatch.setattr(b, "_add_audit", _spy)

    b.open_trade(
        demo_trade_id="DEMO_Y", direction="SELL", sl=150.5, tp=149.0,
        mode="scalp", instrument="USD_JPY", units=1000,
    )
    assert any(c.get("bridge_status") == "blocked"
               and "daily_loss_limit" in c.get("block_reason", "")
               for c in captured), f"expected blocked audit row, got {captured}"
