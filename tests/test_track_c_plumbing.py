"""Track C 資本配管修復 (user 承認 2026-07-28) の回帰テスト。

対象: knowledge-base/wiki/decisions/track-c-capital-plumbing-decision-packet-2026-07-28.md
- D-c-1: price_shock_rev ×5 の agg-Kelly min-lot bypass + BE_LOCK OFF
- D-c-2: donchian は bypass 対象外 (意図的 — 365d BT FAIL、shadow N 蓄積継続)
- D-b:   JPY 台帳 (pip_value_jpy 換算 + DD tier 判定)
- R2:    PYR (Risk-Free Pyramiding) code pin
"""

import pytest

from modules.demo_trader import (
    DemoTrader,
    MFE_BE_LOCK_STRATEGY_TRIGGERS,
    _mfe_be_lock_trigger_for,
    _PYRAMIDING_CODE_PIN_DISABLED,
    pip_value_jpy,
)
from modules.risk_analytics import get_dd_lot_multiplier

PS_TYPES = [
    "price_shock_rev_eur_gbp_h1_long",
    "price_shock_rev_eur_aud_h1_long",
    "price_shock_rev_usd_cad_h1_long",
    "price_shock_rev_nzd_jpy_h1_long",
    "price_shock_rev_aud_jpy_h1_long",
]


class _BypassHost:
    """クラス属性のみを使う _agg_kelly_gate_minlot_bypass 用のスタブ host。"""
    _AGG_KELLY_GATE_MINLOT_BYPASS_TYPES = (
        DemoTrader._AGG_KELLY_GATE_MINLOT_BYPASS_TYPES
    )
    _AGG_KELLY_GATE_MINLOT_MAX_UNITS = (
        DemoTrader._AGG_KELLY_GATE_MINLOT_MAX_UNITS
    )


def _bypass(entry_type, units, is_xau=False):
    return DemoTrader._agg_kelly_gate_minlot_bypass(
        _BypassHost(), entry_type, units, is_xau
    )


# ── D-c-1: carve-out ──

@pytest.mark.parametrize("et", PS_TYPES)
def test_ps_in_agg_kelly_bypass_frozenset(et):
    assert et in DemoTrader._AGG_KELLY_GATE_MINLOT_BYPASS_TYPES


@pytest.mark.parametrize("et", PS_TYPES)
def test_ps_bypass_at_min_lot(et):
    assert _bypass(et, 1000) is True
    assert _bypass(et, -1000) is True   # SELL units


@pytest.mark.parametrize("et", PS_TYPES)
def test_ps_bypass_expires_above_min_lot(et):
    # eligible vs effective 教訓: lot 昇格したら bypass は自動失効する
    assert _bypass(et, 1001) is False
    assert _bypass(et, 5000) is False


def test_ps_bypass_rejects_xau():
    assert _bypass(PS_TYPES[0], 1000, is_xau=True) is False


def test_weekend_gap_bypass_unchanged():
    assert _bypass("weekend_gap_fade", 1000) is True


# ── D-c-2: donchian は意図的に対象外 ──

def test_donchian_not_in_bypass():
    assert "donchian_momentum_breakout" not in (
        DemoTrader._AGG_KELLY_GATE_MINLOT_BYPASS_TYPES
    )
    assert _bypass("donchian_momentum_breakout", 1000) is False


# ── exit overlay §5 案(a): BE_LOCK OFF ──

@pytest.mark.parametrize("et", PS_TYPES)
def test_ps_be_lock_disabled(et):
    assert MFE_BE_LOCK_STRATEGY_TRIGGERS[et] == 0.0
    assert _mfe_be_lock_trigger_for(et, 2.0) == 0.0


def test_be_lock_default_preserved_for_unknown():
    assert _mfe_be_lock_trigger_for("some_other_strategy", 2.0) == 2.0


# ── R2: PYR code pin ──

def test_pyramiding_code_pin_is_irreversible_constant():
    assert _PYRAMIDING_CODE_PIN_DISABLED is True


# ── D-b: pip_value_jpy ──

def _rates(**kw):
    table = dict(kw)
    return lambda pair: table.get(pair)


def test_pip_value_jpy_quote_jpy():
    # JPY クロス: units × 0.01、レート不要
    assert pip_value_jpy("USD_JPY", 1000, _rates()) == pytest.approx(10.0)
    assert pip_value_jpy("AUD_JPY", 3000, _rates()) == pytest.approx(30.0)


def test_pip_value_jpy_usd_quote():
    # USD quote: units × 0.0001 × USDJPY
    r = _rates(USD_JPY=150.0)
    assert pip_value_jpy("EUR_USD", 1000, r) == pytest.approx(15.0)


def test_pip_value_jpy_direct_quote_jpy_pair():
    # quote 通貨の直接 JPY ペアがあればそれを使う (GBP → GBP_JPY)
    r = _rates(GBP_JPY=190.0)
    assert pip_value_jpy("EUR_GBP", 1000, r) == pytest.approx(19.0)


def test_pip_value_jpy_usd_cross_synthesis():
    # USD_CAD: CADJPY = USDJPY / USDCAD
    r = _rates(USD_JPY=150.0, USD_CAD=1.35)
    expected = 1000 * 0.0001 * (150.0 / 1.35)
    assert pip_value_jpy("USD_CAD", 1000, r) == pytest.approx(expected)


def test_pip_value_jpy_fallback_constant():
    # レート全滅時は 150.0 定数フォールバック
    assert pip_value_jpy("EUR_USD", 1000, _rates()) == pytest.approx(15.0)


def test_pip_value_jpy_zero_units_defaults_to_min_lot():
    assert pip_value_jpy("USD_JPY", 0, _rates()) == pytest.approx(10.0)


def test_pip_value_jpy_malformed_instrument():
    assert pip_value_jpy("XAUUSD", 1000, _rates()) == 0.0


# ── D-b: JPY DD → tier 判定 (D-a 実測値の再現) ──

def test_dd_tier_from_jpy_ledger_matches_da_measurement():
    base = 359109.0
    # D-a 実測: max DD 32,835 JPY = 9.14% → 0.20x (現状維持で開始)
    assert get_dd_lot_multiplier(32835.0 / base) == pytest.approx(0.20)
    # 回復経路: 8% 境界 (28,728.7 JPY) を下回れば 0.40x 復帰 — pip 台帳の
    # +928p (≈57,000 JPY 相当) ではなく ~+4.1k JPY で届く (恒久ロックの解消)
    boundary_jpy = 0.08 * base
    assert get_dd_lot_multiplier((boundary_jpy - 1.0) / base) == pytest.approx(0.40)
    assert get_dd_lot_multiplier((boundary_jpy + 1.0) / base) == pytest.approx(0.20)
