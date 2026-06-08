"""Test BBRsiReversion pair whitelist + SIZE lever.

Empirical evidence 2026-06-08 (N=239 production shadow):
  USD_JPY      → EDGE 1.0x (LDN/NY) or 0.5x (ASN)
  USD_CHF      → KILL (WR 5-7%, mean -2 to -3p) absolute block
  GBP_USD      → KILL (WR 23%, mean -1.5p) absolute block
  Other pairs  → SKIP (insufficient evidence)
"""
import datetime as dt
import pytest

from strategies.scalp.bb_rsi import BBRsiReversion
from strategies.context import SignalContext


@pytest.fixture(autouse=True)
def _clear_filter_env(monkeypatch):
    """Same hygiene pattern as session_time_bias test — prevent shell env leak."""
    monkeypatch.delenv("BB_RSI_REVERSION_PAIR_WHITELIST_V1", raising=False)


def _make_ctx(*, hour_utc: int, symbol: str):
    ctx = SignalContext()
    ctx.symbol = symbol
    fixed = dt.datetime(2026, 6, 8, hour_utc, 30, 0, tzinfo=dt.timezone.utc)
    ctx.entry_time_utc = fixed
    return ctx


def _filter(ctx):
    return BBRsiReversion()._edge_cell(ctx)


# ── EDGE pair USD_JPY ─────────────────────────────────────────────
def test_usd_jpy_ldn_returns_edge_1x():
    ctx = _make_ctx(hour_utc=10, symbol="USD_JPY")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0


def test_usd_jpy_ny_returns_edge_1x():
    ctx = _make_ctx(hour_utc=15, symbol="USD_JPY")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0


def test_usd_jpy_asn_returns_half_05x():
    ctx = _make_ctx(hour_utc=3, symbol="USD_JPY")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 0.5


# ── KILL pairs ────────────────────────────────────────────────────
def test_usd_chf_blocked_at_all_hours():
    for h in [3, 9, 15, 21]:
        ctx = _make_ctx(hour_utc=h, symbol="USD_CHF")
        edge, mult = _filter(ctx)
        assert edge is False, f"USD_CHF at hour {h} must be skip"


def test_gbp_usd_blocked_at_all_hours():
    for h in [3, 9, 15, 21]:
        ctx = _make_ctx(hour_utc=h, symbol="GBP_USD")
        edge, mult = _filter(ctx)
        assert edge is False


# ── Other pairs (insufficient evidence → skip safely) ─────────────
def test_eur_usd_skipped():
    """Not in EDGE_PAIRS, not in KILL_PAIRS → safe side: skip."""
    ctx = _make_ctx(hour_utc=10, symbol="EUR_USD")
    edge, mult = _filter(ctx)
    assert edge is False


def test_aud_jpy_skipped():
    ctx = _make_ctx(hour_utc=10, symbol="AUD_JPY")
    edge, mult = _filter(ctx)
    assert edge is False


def test_xau_usd_skipped():
    ctx = _make_ctx(hour_utc=10, symbol="XAU_USD")
    edge, mult = _filter(ctx)
    assert edge is False


# ── Symbol format normalization (with =X suffix etc.) ─────────────
def test_usd_jpy_with_x_suffix():
    ctx = _make_ctx(hour_utc=10, symbol="USDJPY=X")
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0


def test_usd_chf_no_underscore():
    """Verify normalization handles both USDCHF and USD_CHF."""
    ctx = _make_ctx(hour_utc=10, symbol="USDCHF")
    edge, mult = _filter(ctx)
    assert edge is False  # USD_CHF normalized → KILL


# ── Fail-safe ─────────────────────────────────────────────────────
def test_missing_symbol_skip():
    ctx = SignalContext()
    ctx.symbol = ""
    fixed = dt.datetime(2026, 6, 8, 10, 30, 0, tzinfo=dt.timezone.utc)
    ctx.entry_time_utc = fixed
    edge, mult = _filter(ctx)
    assert edge is False


# ── Env flag rollback ────────────────────────────────────────────
def test_env_flag_off_disables_whitelist(monkeypatch):
    """BB_RSI_REVERSION_PAIR_WHITELIST_V1=0 → pass-through (edge_on=True, mult=1.0)."""
    monkeypatch.setenv("BB_RSI_REVERSION_PAIR_WHITELIST_V1", "0")
    ctx = _make_ctx(hour_utc=10, symbol="USD_CHF")  # would otherwise KILL
    edge, mult = _filter(ctx)
    assert edge is True
    assert mult == 1.0
