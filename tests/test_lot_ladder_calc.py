"""Tests for tools/lot_ladder_calc.py (lot-ladder-template-2026-08 §3-§8).

数値は knowledge-base/wiki/analyses/lot-ladder-template-2026-08.md §9 の
worked example (placeholder 統計 WR55%/30p/20p、NAV 326,473) と一致させて pin する。
"""
import math

import pytest

from tools.lot_ladder_calc import (
    CELL_EVENT_LOSS_CAP_PCT,
    MARGIN_CAP_PCT,
    MAX_CURRENCY_EXPOSURE,
    RUNGS,
    bev_wr,
    demote_rung,
    ev_wilson_lower,
    evaluate,
    jpy_per_pip_per_1000u,
    margin_jpy_per_1000u,
    n_required_for_gate,
    next_rung,
    render_packet,
    unit_ceilings,
    wilson_lower,
)

NAV = 326_473.0


class TestWilsonGate:
    def test_wilson_lower_known_value(self):
        # WR 55% N=30 → Wilson_lo ≈ 0.3766 (template §9)
        assert wilson_lower(0.55, 30) == pytest.approx(0.3766, abs=1e-3)

    def test_bev_wr(self):
        assert bev_wr(30, 20) == pytest.approx(0.4)

    def test_ev_wilson_lower_sign_flip_at_n41(self):
        # template §9: wg 級統計は N=41 でゲート開通
        assert ev_wilson_lower(0.55, 40, 30, 20) < 0
        assert ev_wilson_lower(0.55, 41, 30, 20) > 0

    def test_n_required_matches(self):
        assert n_required_for_gate(0.55, 30, 20) == 41

    def test_n_required_none_when_point_wr_below_bev(self):
        # 点推定 WR が BEV 以下ならゲートは永遠に開かない
        assert n_required_for_gate(0.40, 30, 20) is None
        assert n_required_for_gate(0.35, 30, 20) is None


class TestUnitConversion:
    def test_jpy_quote_pip_value(self):
        assert jpy_per_pip_per_1000u("USD_JPY") == 10.0
        assert jpy_per_pip_per_1000u("EUR_JPY") == 10.0

    def test_usd_quote_needs_usdjpy(self):
        with pytest.raises(ValueError):
            jpy_per_pip_per_1000u("EUR_USD")
        assert jpy_per_pip_per_1000u("EUR_USD", usdjpy=147.0) == pytest.approx(14.7)

    def test_explicit_override(self):
        assert jpy_per_pip_per_1000u("EUR_GBP", explicit=18.5) == 18.5

    def test_margin_usdjpy_147(self):
        # 1000u USD_JPY @147 / 25x = 5,880 JPY (template §9)
        assert margin_jpy_per_1000u("USD_JPY", 147.0) == pytest.approx(5880.0)


class TestCeilings:
    def kwargs(self, **over):
        base = dict(nav=NAV, wr=0.55, avg_win=30.0, avg_loss=20.0,
                    disaster_sl_pips=150.0, v1000=10.0,
                    margin_1000=5880.0, max_concurrent=3)
        base.update(over)
        return base

    def test_wg_binding_is_cell_dd(self):
        # template §9: U_cellDD ≈ 5,441u → floor 5,000u が binding
        res = unit_ceilings(**self.kwargs())
        assert res["binding"] == "U_cellDD"
        assert res["max_units"] == 5000

    def test_ceiling_values_match_template(self):
        res = unit_ceilings(**self.kwargs())
        c = res["ceilings"]
        assert c["U_avg"] == 204_000     # half-Kelly avg_loss 基底
        assert c["U_dis"] == 27_000      # half-Kelly disaster 基底
        assert c["U_cellDD"] == 5000     # 2.5% NAV worst-case event
        # margin: 0.40×NAV/(5880×3)×1000 ≈ 7,403 → 7,000
        assert c["U_margin"] == 7000
        # exposure: 20k / 3 同時 = 6,666 → floor 6,000
        assert c["U_exposure"] == 6000
        assert MAX_CURRENCY_EXPOSURE == 20_000

    def test_zero_kelly_when_negative_edge(self):
        res = unit_ceilings(**self.kwargs(wr=0.30))
        assert res["kelly"]["half_kelly"] == 0.0
        assert res["ceilings"]["U_avg"] == 0

    def test_constants_frozen(self):
        # テンプレ §4 凍結値の drift 検知 pin (変更は R1)
        assert CELL_EVENT_LOSS_CAP_PCT == 0.025
        assert MARGIN_CAP_PCT == 0.40
        assert MAX_CURRENCY_EXPOSURE == 20_000
        assert RUNGS == [1000, 5000, 10000, 30000]


class TestLadderSteps:
    def test_next_rung_sequence(self):
        assert next_rung(1000) == 5000
        assert next_rung(5000) == 10000
        assert next_rung(10000) == 30000
        assert next_rung(30000) is None

    def test_demote_one_step_with_floor(self):
        assert demote_rung(30000) == 10000
        assert demote_rung(5000) == 1000
        assert demote_rung(1000) == 1000  # floor: L0 未満なし

    def test_invalid_rung_raises(self):
        with pytest.raises(ValueError):
            next_rung(7500)
        with pytest.raises(ValueError):
            demote_rung(2000)


class TestEvaluate:
    def wg_like(self, **over):
        base = dict(nav=NAV, pair="USD_JPY", price=147.0, n=30, mean=7.9,
                    sigma=35.0, wr=0.55, avg_win=30.0, avg_loss=20.0,
                    disaster_sl_pips=150.0, events_per_month=3.28,
                    current_rung=1000, max_concurrent=3)
        base.update(over)
        return evaluate(**base)

    def test_hold_at_n30_wilson_gate(self):
        # G3 (N=30) 到達 ≠ ゲート開通 (template §9)
        res = self.wg_like()
        assert res["verdict"] == "HOLD"
        assert any("Wilson gate FAIL" in r for r in res["hold_reasons"])
        assert res["wilson"]["n_required"] == 41

    def test_propose_when_gate_opens(self):
        res = self.wg_like(n=60)
        assert res["wilson"]["gate_pass"] is True
        assert res["verdict"] == "PROPOSE"
        assert res["recommended_units"] == 5000

    def test_l2_blocked_by_cell_dd_at_current_nav(self):
        # template §9: L2 (10k) は現 NAV では制約 4.2 違反
        res = self.wg_like(n=100, current_rung=5000)
        assert res["verdict"] == "HOLD"
        assert any("binding ceiling" in r for r in res["hold_reasons"])

    def test_l2_at_nav_600k_still_blocked_by_exposure_for_3pair_cell(self):
        # NAV 600k で U_cellDD は開くが、3 ペア同時セルは exposure cap が縛る
        # (template §9: L2 以上は cap 改定 R1 同梱が必要)
        res = self.wg_like(n=100, current_rung=5000, nav=600_000.0)
        assert res["ceilings"]["U_cellDD"] == 10_000
        assert res["verdict"] == "HOLD"
        assert res["binding_constraint"] == "U_exposure"

    def test_l2_opens_at_nav_600k_for_single_pair_cell(self):
        res = self.wg_like(n=100, current_rung=5000, nav=600_000.0,
                           max_concurrent=1)
        assert res["verdict"] == "PROPOSE"
        assert res["recommended_units"] == 10_000

    def test_top_rung_holds(self):
        res = self.wg_like(n=500, current_rung=30000, nav=10_000_000.0)
        assert res["target_rung"] is None
        assert res["verdict"] == "HOLD"

    def test_counterfactual_matches_template(self):
        # template §9: L0→L1 機会費用 ≈ +1,036 JPY/月 (+0.32% NAV)
        res = self.wg_like()
        cf = res["counterfactual"]
        assert cf["opportunity_jpy_per_month"] == pytest.approx(1036.5, abs=0.5)
        assert cf["opportunity_pct_nav_per_month"] == pytest.approx(0.317, abs=0.01)
        assert cf["worst_case_event_jpy_target"] == 7500

    def test_mc_gate_wired(self):
        # 十分に正の pnl 系列なら MC gate PASS、極端に負なら FAIL
        good = [20.0] * 20 + [-10.0] * 10
        res = self.wg_like(n=60, pnl_pips=good)
        assert res["mc"] is not None
        assert res["mc"]["gate_pass"] is True
        bad = [-150.0] * 10 + [5.0] * 20
        res2 = self.wg_like(n=60, pnl_pips=bad)
        assert res2["mc"]["gate_pass"] is False
        assert res2["verdict"] == "HOLD"


class TestPacket:
    def test_render_contains_required_sections(self):
        res = evaluate(nav=NAV, pair="USD_JPY", price=147.0, n=60, mean=7.9,
                       sigma=35.0, wr=0.55, avg_win=30.0, avg_loss=20.0,
                       disaster_sl_pips=150.0, events_per_month=3.28,
                       current_rung=1000, max_concurrent=3)
        md = render_packet(res, cell_id="WG_USDJPY", strategy="weekend_gap_fade",
                           date="2026-08-05")
        for needle in ("## 1. 遷移", "## 3. ゲート判定", "## 4. counterfactual",
                       "## 5. 停止条件", "## 6. rollback", "## 9. user 承認",
                       "binding constraint", "LOT_LADDER_WG_USDJPY_DEMOTED",
                       "lot-ladder-template-2026-08"):
            assert needle in md, needle
