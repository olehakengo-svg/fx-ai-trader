"""P-S1(a) AMENDMENT pin テスト: LATE 窓 cell-scoped 執行修正 (第 3/第 4 ブロッカー)。

⚠️ この commit は 2026-07-24 条件付き承認のスコープ外 — user 決裁前の merge 禁止。

背景 (2026-07-31 準備セッションで発見した estimand ブロッカー 2 件):
(3) v8.6 gbp_asia_flash_crash ("GBP" in instrument ∧ UTC 21-06) は
    sweep_reversion_eurgbp_late の LATE 窓 (21-24 UTC) を 100% 内包し、sweep は
    shadow-eligible 集合外のため hard block。HTF exemption 後は rescue 経路も
    外れるため、この免除なしでは live fill 0 のまま shadow 蓄積まで消滅する。
(4) 静的 per-pair spread limit (EUR_GBP 1.5p) + spread/TP 比 gate (20%) は
    LATE rollover 実測 (5.4-16.6p、全 8 発火が超過) と tail-cap TP 設計に対し
    構造的に全 block。weekend_gap pre-reg §2.2 と同型の専用 cap 10.0p で置換
    (cap 超過 = shadow row 分母保存)。動的 spread_sl_gate (35%) は維持。
決裁: knowledge-base/wiki/decisions/sweep-reversion-ps1a-decision-packet-DRAFT.md §8.1
"""
from modules.demo_trader import DemoTrader
from strategies.daytrade.sweep_reversion_eurgbp_late import (
    PS1A_SWEEP_SPREAD_CAP_PIPS,
    ps1a_sweep_spread_cap_skip,
)

SWEEP = "sweep_reversion_eurgbp_late"


def test_exempt_cell_passes_throughout_late_and_asia_window():
    for h in (21, 22, 23, 0, 3, 5):
        assert not DemoTrader._gbp_asia_flash_crash_blocked(SWEEP, "EUR_GBP", h)


def test_other_gbp_cells_still_blocked_in_window():
    """blast radius = 1 cell のみ — gbp_asia ゲート本体・他戦略は不変 (原則3)。"""
    for h in (21, 23, 5):
        assert DemoTrader._gbp_asia_flash_crash_blocked("ema_cross", "GBP_USD", h)
        assert DemoTrader._gbp_asia_flash_crash_blocked("ema_cross", "EUR_GBP", h)
        assert DemoTrader._gbp_asia_flash_crash_blocked("gbp_deep_pullback", "GBP_JPY", h)
        # cell スコープ: 同戦略でも他ペアは免除されない
        assert DemoTrader._gbp_asia_flash_crash_blocked(SWEEP, "GBP_USD", h)


def test_gate_inactive_outside_window_and_for_non_gbp():
    assert not DemoTrader._gbp_asia_flash_crash_blocked("ema_cross", "GBP_USD", 12)
    assert not DemoTrader._gbp_asia_flash_crash_blocked("ema_cross", "GBP_USD", 20)
    assert not DemoTrader._gbp_asia_flash_crash_blocked("ema_cross", "EUR_USD", 22)
    assert not DemoTrader._gbp_asia_flash_crash_blocked("ema_cross", "", 22)


def test_window_boundaries_preserved():
    """UTC 21-06 の境界そのものは変更しない (>=21 or <6)。"""
    assert DemoTrader._gbp_asia_flash_crash_blocked("ema_cross", "GBP_USD", 21)
    assert DemoTrader._gbp_asia_flash_crash_blocked("ema_cross", "GBP_USD", 5)
    assert not DemoTrader._gbp_asia_flash_crash_blocked("ema_cross", "GBP_USD", 6)


def test_exempt_set_is_single_cell():
    assert DemoTrader._GBP_ASIA_FLASH_CRASH_EXEMPT_CELLS == frozenset(
        {(SWEEP, "EUR_GBP")})


class TestPs1aSweepSpreadCap:
    """第 4 ブロッカー修正: 専用 spread cap (wg pre-reg §2.2 同型)。"""

    def test_cap_value_matches_wg_precedent(self):
        from strategies.daytrade.weekend_gap_fade import WEEKEND_GAP_SPREAD_CAP_PIPS
        assert PS1A_SWEEP_SPREAD_CAP_PIPS == 10.0 == WEEKEND_GAP_SPREAD_CAP_PIPS

    def test_skip_boundary(self):
        assert not ps1a_sweep_spread_cap_skip(10.0)   # ちょうど cap は live
        assert ps1a_sweep_spread_cap_skip(10.01)
        assert ps1a_sweep_spread_cap_skip(16.6)       # 実測 worst (07-09) は skip
        assert not ps1a_sweep_spread_cap_skip(6.6)    # 実測中央値は live

    def test_observed_fires_admission_rate(self):
        """rescued shadow 実測 8 発火 (packet §1.3) のうち 7/8 が cap 内。"""
        observed = [6.9, 6.1, 6.3, 5.4, 6.1, 16.6, 7.9, 7.7]
        admitted = [s for s in observed if not ps1a_sweep_spread_cap_skip(s)]
        assert len(admitted) == 7

    def test_cap_gating_is_coupled_to_live_pin(self):
        """cap 経路は _sweep_reversion_eurgbp_live_eligible に連動 — pin 再無効化
        (R2 stop) 時は自動で不活性化する (fail-closed 連成)。"""
        assert DemoTrader._sweep_reversion_eurgbp_live_eligible(SWEEP, "EUR_GBP")
        assert not DemoTrader._sweep_reversion_eurgbp_live_eligible(SWEEP, "GBP_USD")
