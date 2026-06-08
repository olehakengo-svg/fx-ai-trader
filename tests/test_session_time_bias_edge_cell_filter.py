"""Test SessionTimeBias._edge_cell helper.

Empirical edge cell from 2026-06-08 production data analysis (N=396, 40 days):
  LDN × ADX[15,30] × dist_EMA200 < 0.5%  → EDGE_ON, lot 1.0x
  +ADX[25,30] OR regime=RANGE             → CORE BOOST, lot 1.5x
  All others                              → SKIP

See docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md §3.2
"""
import os
import datetime as dt
from typing import Optional
import pytest

from strategies.daytrade.session_time_bias import SessionTimeBias
from strategies.context import SignalContext


def _make_ctx(*, hour_utc: int, adx: float, entry_px: float = 1.1000,
              ema200: float = 1.1000, regime_label: Optional[str] = "RANGE",
              symbol: str = "EUR_USD"):
    """Build a minimal SignalContext for filter testing."""
    ctx = SignalContext()
    ctx.entry = entry_px
    ctx.ema200 = ema200
    ctx.adx = adx
    ctx.symbol = symbol
    # SignalContext stores regime as dict per strategies/context.py:80
    ctx.regime = {"regime": regime_label} if regime_label else {}
    # Mock entry_time at given UTC hour
    fixed = dt.datetime(2026, 6, 8, hour_utc, 30, 0, tzinfo=dt.timezone.utc)
    ctx.entry_time_utc = fixed
    return ctx


def _filter(ctx):
    """Call the helper under test."""
    strat = SessionTimeBias()
    return strat._edge_cell(ctx)


# ── EDGE 1.0x cells ────────────────────────────────────────────
def test_ldn_adx_18_range_dist_03pct_returns_edge_1x():
    ctx = _make_ctx(hour_utc=9, adx=18, ema200=1.1000, entry_px=1.1030, regime_label="CHOP")  # dist 0.27%, non-RANGE
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0  # ADX < 25 and not RANGE label → base edge


def test_ldn_adx_24_range_dist_04pct_returns_edge_1x():
    ctx = _make_ctx(hour_utc=11, adx=24, ema200=1.1000, entry_px=1.1043, regime_label="CHOP")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0


# ── CORE BOOST 1.5x cells ───────────────────────────────────────
def test_ldn_adx_27_returns_core_boost_1_5x():
    """ADX in [25,30] triggers core boost regardless of regime label."""
    ctx = _make_ctx(hour_utc=10, adx=27, ema200=1.1000, entry_px=1.1020, regime_label="CHOP")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.5


def test_ldn_adx_18_range_label_returns_core_boost_1_5x():
    """regime=RANGE triggers core boost even at lower ADX."""
    ctx = _make_ctx(hour_utc=8, adx=18, ema200=1.1000, entry_px=1.1020, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.5


# ── KILL cells (skip) ───────────────────────────────────────────
def test_asn_session_skip():
    """Hour 3 UTC = ASN, mean -3.85p in data → skip."""
    ctx = _make_ctx(hour_utc=3, adx=18, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_ny_session_skip():
    """Hour 15 UTC = NY, mean -3.88p → skip."""
    ctx = _make_ctx(hour_utc=15, adx=18, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_late_session_skip():
    """Hour 22 UTC = LATE, mean -4.14p → skip."""
    ctx = _make_ctx(hour_utc=22, adx=18, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_ldn_adx_too_low_skip():
    """ADX 12 < 15 → skip (vol scale issue)."""
    ctx = _make_ctx(hour_utc=10, adx=12, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_ldn_adx_too_high_skip():
    """ADX 35 > 30 → skip (strong trend kills MR, mean -3.98p)."""
    ctx = _make_ctx(hour_utc=10, adx=35, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_ldn_far_from_ema200_skip():
    """dist 0.7% > 0.5% → skip (price not in range vicinity)."""
    ctx = _make_ctx(hour_utc=10, adx=22, ema200=1.1000, entry_px=1.1080, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


def test_ldn_boundary_hour_7_included():
    """Hour 7 UTC start of LDN — must be edge_on."""
    ctx = _make_ctx(hour_utc=7, adx=20, entry_px=1.1030, ema200=1.1000, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is True


def test_ldn_boundary_hour_12_included():
    """Hour 12 UTC last LDN — must be edge_on."""
    ctx = _make_ctx(hour_utc=12, adx=20, entry_px=1.1030, ema200=1.1000, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is True


def test_ldn_boundary_hour_13_excluded():
    """Hour 13 UTC = NY start — must skip."""
    ctx = _make_ctx(hour_utc=13, adx=20, entry_px=1.1030, ema200=1.1000, regime_label="RANGE")
    edge, mult = _filter(ctx)
    assert edge is False


# ── Fail-safe: missing inputs ────────────────────────────────────
def test_adx_none_skip():
    ctx = _make_ctx(hour_utc=10, adx=25, regime_label="RANGE")
    ctx.adx = None
    edge, mult = _filter(ctx)
    assert edge is False


def test_ema200_zero_skip():
    """Division by zero protection."""
    ctx = _make_ctx(hour_utc=10, adx=25, regime_label="RANGE")
    ctx.ema200 = 0.0
    edge, mult = _filter(ctx)
    assert edge is False


# ── Env flag rollback ────────────────────────────────────────────
def test_env_flag_off_disables_filter(monkeypatch):
    """SESSION_TIME_BIAS_CELL_FILTER_V1=0 → filter pass-through (edge_on=True, mult=1.0)."""
    monkeypatch.setenv("SESSION_TIME_BIAS_CELL_FILTER_V1", "0")
    ctx = _make_ctx(hour_utc=3, adx=18, regime_label="RANGE")  # would otherwise SKIP
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0
