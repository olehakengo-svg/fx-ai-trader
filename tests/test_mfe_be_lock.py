"""Unit tests for MFE-pip Break-Even Lock helpers.

Pure-function tests for the giveback-prevention BE-lock added 2026-06-03.
Design: knowledge-base/wiki/analyses/mfe-be-lock-design-2026-06-03.md
"""
from __future__ import annotations

import pytest

from modules.demo_trader import (
    MFE_BE_LOCK_DEFAULT_FLOOR_PIPS,
    MFE_BE_LOCK_DEFAULT_TRIGGER_PIPS,
    MFE_BE_LOCK_STRATEGY_TRIGGERS,
    _compute_mfe_be_lock_sl,
    _mfe_be_lock_group,
    _mfe_be_lock_trigger_for,
)


# ── _mfe_be_lock_trigger_for ─────────────────────────────────────────────────

class TestTriggerLookup:
    def test_returns_default_for_unknown_strategy(self):
        assert _mfe_be_lock_trigger_for("totally_made_up", 2.5) == 2.5

    def test_returns_override_for_known_strategy(self):
        # vix_carry_unwind is configured to wait until +3 pips MFE
        assert _mfe_be_lock_trigger_for("vix_carry_unwind", 2.0) == 3.0

    def test_donchian_disabled_returns_zero(self):
        # donchian_momentum_breakout has ΔEV=0 in counterfactual → disabled
        assert _mfe_be_lock_trigger_for("donchian_momentum_breakout", 2.0) == 0.0

    def test_price_shock_rev_disabled_returns_zero(self):
        # 2026-07-28 user 決裁 (rule:R1): LOCK 済み Exit 設計 (horizon or 2×ATR SL
        # のみ) に BE_LOCK は設計外 — analyses/preserve-exit-overlay-2026-07-28.md §5
        # 案(a)。PRICE_SHOCK_REV_TIER1_TYPES 全体をパラメタライズし、family 追加時の
        # drift を強制検知する (test_preserve_types_tick_entry.py と同思想)。
        from modules.demo_trader import PRICE_SHOCK_REV_TIER1_TYPES

        assert PRICE_SHOCK_REV_TIER1_TYPES, "tier-1 set unexpectedly empty"
        for strat in PRICE_SHOCK_REV_TIER1_TYPES:
            assert _mfe_be_lock_trigger_for(strat, 2.0) == 0.0, (
                f"{strat} not BE_LOCK-disabled — preserve exit contract drift"
            )

    def test_empty_entry_type_returns_default(self):
        assert _mfe_be_lock_trigger_for("", 2.0) == 2.0
        assert _mfe_be_lock_trigger_for(None, 2.0) == 2.0

    def test_strategy_map_contains_audit_candidates(self):
        # The audit (2026-06-03) called out these strategies for tuning;
        # regression-protect their inclusion in the override map.
        for strat in (
            "vix_carry_unwind",
            "mqe_gbpusd_fix",
            "dt_bb_rsi_mr",
            "sr_anti_hunt_bounce",
            "orb_trap",
            "wick_imbalance_reversion",
            "donchian_momentum_breakout",
        ):
            assert strat in MFE_BE_LOCK_STRATEGY_TRIGGERS, (
                f"{strat} missing from override map — audit drift"
            )

    def test_price_shock_rev_family_disabled(self):
        # preserve-exit-overlay-2026-07-28 §5(a)+§6: LOCKed estimand is
        # horizon-exit or 2xATR catastrophic SL only — BE-lock must stay OFF.
        from modules.demo_trader import PRICE_SHOCK_REV_TIER1_TYPES

        for strat in PRICE_SHOCK_REV_TIER1_TYPES:
            assert _mfe_be_lock_trigger_for(strat, 2.0) == 0.0, (
                f"{strat} BE-lock re-enabled — estimand deviation "
                "(re-enable requires R1 per mfe-be-lock-design §5)"
            )


# ── price_shock_rev estimand exemption pins (2026-07-28 §5(b)) ──────────────
# The exemption conditions are inline in _sltp_loop / _check_signal_reverse,
# so pin them via source inspection (same idiom as test_hull_donchian_fade).

class TestPriceShockExitEstimandPins:
    def _module_source(self):
        import inspect

        import modules.demo_trader as dt

        return inspect.getsource(dt)

    def test_atr_be_trail_block_exempts_price_shock(self):
        src = self._module_source()
        assert "_is_ps_rev_sltp = _entry_type_t in PRICE_SHOCK_REV_TIER1_TYPES" in src, (
            "price_shock ATR-BE/trail exemption flag removed — estimand deviation"
        )
        assert "and not _is_weekend_gap and not _is_ps_rev_sltp" in src, (
            "ATR-BE/SMC-BE/ATR-trail block no longer skips price_shock_rev"
        )

    def test_signal_reverse_exempts_price_shock(self):
        import inspect

        from modules.demo_trader import DemoTrader

        src = inspect.getsource(DemoTrader._check_signal_reverse)
        assert "PRICE_SHOCK_REV_TIER1_TYPES" in src, (
            "_check_signal_reverse lost the price_shock_rev exemption "
            "(4th estimand-deviation path, preserve-exit-overlay §6.4)"
        )


# ── _mfe_be_lock_group (A/B split) ───────────────────────────────────────────

class TestABGroup:
    def test_zero_fraction_all_a(self):
        assert _mfe_be_lock_group("anything", 0.0) == "A"

    def test_one_fraction_all_b(self):
        assert _mfe_be_lock_group("anything", 1.0) == "B"

    def test_deterministic_same_id_same_group(self):
        tid = "test-trade-abc123"
        g1 = _mfe_be_lock_group(tid, 0.5)
        g2 = _mfe_be_lock_group(tid, 0.5)
        g3 = _mfe_be_lock_group(tid, 0.5)
        assert g1 == g2 == g3

    def test_distribution_approx_balanced(self):
        # 1,000 synthetic trade_ids → roughly 50/50 with ab=0.5
        from uuid import uuid4
        ids = [str(uuid4()) for _ in range(1000)]
        groups = [_mfe_be_lock_group(t, 0.5) for t in ids]
        b_share = sum(1 for g in groups if g == "B") / len(groups)
        # Allow ±5pp slack on 1k samples (CRC32 is well-distributed)
        assert 0.45 <= b_share <= 0.55, f"B share={b_share} out of [0.45,0.55]"

    def test_empty_id_safe(self):
        # Should not crash on empty or None
        assert _mfe_be_lock_group("", 0.5) in ("A", "B")
        assert _mfe_be_lock_group(None, 0.5) in ("A", "B")


# ── _compute_mfe_be_lock_sl (core logic) ─────────────────────────────────────

# JPY pair: pip_size = 0.01, pip_decimals = 3
# Non-JPY: pip_size = 0.0001, pip_decimals = 5

class TestComputeMfeBeLockSl:
    def test_disabled_when_trigger_zero(self):
        new_sl, fired = _compute_mfe_be_lock_sl(
            direction="BUY", entry_price=1.1000, current_sl=1.0950,
            mfe_favorable_price=1.1050, instrument="EUR_USD",
            spread_amt=0.00002, trigger_pips=0.0, floor_pips=1.0,
        )
        assert new_sl is None
        assert fired is False

    def test_no_fire_below_trigger(self):
        # MFE only +1 pip, trigger +2 → no fire
        new_sl, fired = _compute_mfe_be_lock_sl(
            direction="BUY", entry_price=1.1000, current_sl=1.0950,
            mfe_favorable_price=1.10010, instrument="EUR_USD",
            spread_amt=0.00002, trigger_pips=2.0, floor_pips=1.0,
        )
        assert new_sl is None
        assert fired is False

    def test_fire_at_exact_trigger_buy_non_jpy(self):
        # MFE = +2 pips exactly, trigger = +2 → fires
        # entry=1.10000, MFE_price=1.10020, spread=0.00002, floor=1pip
        # new_sl = 1.10000 + 0.00002 + 0.00010 = 1.10012
        new_sl, fired = _compute_mfe_be_lock_sl(
            direction="BUY", entry_price=1.10000, current_sl=1.09500,
            mfe_favorable_price=1.10020, instrument="EUR_USD",
            spread_amt=0.00002, trigger_pips=2.0, floor_pips=1.0,
        )
        assert fired is True
        assert new_sl == pytest.approx(1.10012, abs=1e-6)

    def test_fire_for_sell_non_jpy(self):
        # SELL: MFE_price is the LOWEST price reached.
        # entry=1.10000, MFE_price=1.09980 (favorable −2 pips for SELL)
        # new_sl = 1.10000 − 0.00002 − 0.00010 = 1.09988
        new_sl, fired = _compute_mfe_be_lock_sl(
            direction="SELL", entry_price=1.10000, current_sl=1.10500,
            mfe_favorable_price=1.09980, instrument="EUR_USD",
            spread_amt=0.00002, trigger_pips=2.0, floor_pips=1.0,
        )
        assert fired is True
        assert new_sl == pytest.approx(1.09988, abs=1e-6)

    def test_fire_for_buy_jpy(self):
        # JPY: pip_size=0.01, decimals=3
        # entry=150.000, MFE_price=150.030 (+3 pips), trigger=+2, floor=+1
        # new_sl = 150.000 + 0.008 + 0.010 = 150.018
        new_sl, fired = _compute_mfe_be_lock_sl(
            direction="BUY", entry_price=150.000, current_sl=149.500,
            mfe_favorable_price=150.030, instrument="USD_JPY",
            spread_amt=0.008, trigger_pips=2.0, floor_pips=1.0,
        )
        assert fired is True
        assert new_sl == pytest.approx(150.018, abs=1e-4)

    def test_no_fire_when_new_sl_below_current(self):
        # If current SL already higher (e.g. trail engaged earlier), don't downgrade
        new_sl, fired = _compute_mfe_be_lock_sl(
            direction="BUY", entry_price=1.10000, current_sl=1.10050,  # already +5 lock
            mfe_favorable_price=1.10020, instrument="EUR_USD",
            spread_amt=0.00002, trigger_pips=2.0, floor_pips=1.0,
        )
        # new_sl would be 1.10012, which is LOWER than current 1.10050 → not fired
        assert fired is False
        assert new_sl == pytest.approx(1.10012, abs=1e-6)  # value still computed

    def test_no_fire_for_sell_when_new_sl_above_current(self):
        # SELL trail engaged: current SL lower (better) than proposed
        new_sl, fired = _compute_mfe_be_lock_sl(
            direction="SELL", entry_price=1.10000, current_sl=1.09950,  # +5 lock
            mfe_favorable_price=1.09980, instrument="EUR_USD",
            spread_amt=0.00002, trigger_pips=2.0, floor_pips=1.0,
        )
        # new_sl = 1.09988 > current 1.09950 → would DOWNGRADE → don't fire
        assert fired is False

    def test_fires_at_higher_floor_when_trigger_exceeded(self):
        # MFE=+5, trigger=+2, floor=+2 → still locks at entry+spread+2pip
        new_sl, fired = _compute_mfe_be_lock_sl(
            direction="BUY", entry_price=1.10000, current_sl=1.09500,
            mfe_favorable_price=1.10050, instrument="EUR_USD",
            spread_amt=0.00002, trigger_pips=2.0, floor_pips=2.0,
        )
        assert fired is True
        # 1.10000 + 0.00002 + 0.00020 = 1.10022
        assert new_sl == pytest.approx(1.10022, abs=1e-6)

    def test_invalid_direction_no_fire(self):
        new_sl, fired = _compute_mfe_be_lock_sl(
            direction="UNKNOWN", entry_price=1.10000, current_sl=1.09500,
            mfe_favorable_price=1.10050, instrument="EUR_USD",
            spread_amt=0.00002, trigger_pips=2.0, floor_pips=1.0,
        )
        assert new_sl is None
        assert fired is False


# ── Defaults sanity ──────────────────────────────────────────────────────────

class TestDefaults:
    def test_default_trigger_is_2pip(self):
        # Counterfactual showed +2 pip trigger → EV flip on full pool
        assert MFE_BE_LOCK_DEFAULT_TRIGGER_PIPS == 2.0

    def test_default_floor_is_1pip(self):
        # +1 pip lock floor — conservative against execution slippage
        assert MFE_BE_LOCK_DEFAULT_FLOOR_PIPS == 1.0


# ── Integration: simulated end-to-end with realistic numbers ─────────────────

class TestRealisticScenario:
    """Counterfactual: shadow trade that gave back from MFE +5 to SL_HIT −7.

    Validates that BE-lock fires at +2 and would have prevented the loser.
    """

    def test_eurusd_buy_giveback_scenario(self):
        entry = 1.10000
        original_sl = 1.09930  # 7 pip stop
        spread = 0.00002
        # MFE peaked at +5 pips (1.10050) → BE-lock should fire at +2
        new_sl, fired = _compute_mfe_be_lock_sl(
            direction="BUY", entry_price=entry, current_sl=original_sl,
            mfe_favorable_price=1.10050, instrument="EUR_USD",
            spread_amt=spread, trigger_pips=2.0, floor_pips=1.0,
        )
        assert fired is True
        # New SL at entry + spread + 1pip = 1.10012
        # If price retraces to 1.10012 → close at +1 pip (vs original SL_HIT at -7)
        # Net delta: +1 - (-7) = +8 pip rescue per trade
        assert new_sl > entry  # Strictly profitable lock
        assert new_sl == pytest.approx(1.10012, abs=1e-6)
        # Demonstrate the rescue magnitude
        original_loss_pips = (original_sl - entry) / 0.0001  # = -7
        locked_pips = (new_sl - entry) / 0.0001  # = +1.2 (entry+spread+1pip)
        assert locked_pips - original_loss_pips > 7  # ≥ 7 pip rescue per trade
