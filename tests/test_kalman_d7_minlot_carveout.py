"""kalman_d7 min-lot carve-out (2026-09-01 DRAFT、user 最終承認待ち) の契約固定。

対象: knowledge-base/wiki/decisions/kalman-d7-minlot-carveout-prereg-2026-09-01.md
- 05-28 決裁 (SUCCESS = OANDA fill >=1) が bypass set 非所属 + FLAT 5000u の
  二重不適格で 96 日 fill ゼロだった構造の修復。
- 固定する性質: ①bypass set 所属 ∧ 1000u で agg-Kelly gate を通過する
  ②lot 昇格 (>1000u) で bypass は自動失効する (eligible vs effective)
  ③MIN lot 契約が実効 lot を決め、FLAT が上書きできない
  ④「carve-out が実効である」不変条件 = MIN_UNITS <= bypass 上限
"""

import inspect

import pytest

import modules.demo_trader as dt
from modules.demo_trader import DemoTrader, KALMAN_D7_MIN_UNITS

KALMAN_TYPES = [
    "kalman_d7_po_dn_flip",
    "kalman_d7_ema75_break",
    "kalman_d7_trail_atr",
]


class _BypassHost:
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


@pytest.mark.parametrize("et", KALMAN_TYPES)
def test_kalman_in_agg_kelly_bypass_frozenset(et):
    assert et in DemoTrader._AGG_KELLY_GATE_MINLOT_BYPASS_TYPES


@pytest.mark.parametrize("et", KALMAN_TYPES)
def test_kalman_bypass_at_min_lot(et):
    assert _bypass(et, 1000) is True
    assert _bypass(et, -1000) is True


@pytest.mark.parametrize("et", KALMAN_TYPES)
def test_kalman_bypass_expires_above_min_lot(et):
    # eligible vs effective: 旧 FLAT 5000u が正に無効化していた点の再発防止
    assert _bypass(et, 5000) is False
    assert _bypass(et, 1001) is False


def test_kalman_override_set_matches_bypass_addition():
    """bypass に足した 3 type = _KALMAN_D7_LIVE_OVERRIDE と完全一致。
    片方だけ増減すると「live eligible だが gate で死ぬ」構造が再発する。"""
    assert set(KALMAN_TYPES) == set(DemoTrader._KALMAN_D7_LIVE_OVERRIDE)
    assert set(KALMAN_TYPES) <= set(
        DemoTrader._AGG_KELLY_GATE_MINLOT_BYPASS_TYPES)


def test_min_units_within_bypass_ceiling():
    """carve-out 実効性の不変条件: MIN lot が bypass 上限を超えたら
    全テスト green のまま fill ゼロに戻る — それをここで音にする。"""
    assert KALMAN_D7_MIN_UNITS == 1000
    assert KALMAN_D7_MIN_UNITS <= DemoTrader._AGG_KELLY_GATE_MINLOT_MAX_UNITS


def test_tick_entry_has_min_lot_block_and_flat_shield():
    """_tick_entry の実装が①MIN lot 契約ブロック ②FLAT 上書き遮断の両方で
    _KALMAN_D7_LIVE_OVERRIDE を参照していることの到達性 pin。"""
    src = inspect.getsource(dt.DemoTrader._tick_entry)
    assert "KALMAN_D7_MIN_LOT" in src, "MIN lot 契約ブロックが _tick_entry に無い"
    assert src.count("self._KALMAN_D7_LIVE_OVERRIDE") >= 2, (
        "MIN lot ブロックと FLAT 遮断の両方が override set を参照していること"
    )
