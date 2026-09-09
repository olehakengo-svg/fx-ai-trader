"""Pins for tools/ps_seat_supply_remeasure.py (ps-seat-supply-remeasure-30d harness).

The pins target *properties* of the pre-registered estimand rather than the
literal syntax of the implementation (lesson: pin は構文でなく性質で書く):
  - a partial window cannot produce a verdict unless the early-execution
    condition holds,
  - the decision boundaries are the ones the packet froze,
  - live/shadow are split by the canonical `oanda_trade_id` test,
  - the design count comes from the production strategy object,
  - the frozen top-up merge is a union (pre-existing bars are never replaced).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import ps_seat_supply_remeasure as R


def _row(entry_time, entry_type="price_shock_rev_eur_gbp_h1_long",
         instrument="EUR_GBP", direction="BUY", oanda_trade_id="", dedup=0):
    return {
        "entry_time": entry_time,
        "entry_type": entry_type,
        "instrument": instrument,
        "direction": direction,
        "oanda_trade_id": oanda_trade_id,
        "dedup_violation": dedup,
    }


class TestVerdictBoundaries:
    def test_partial_window_below_early_exec_cannot_yield_verdict(self):
        """中途窓での verdict 禁止 — enforced in code, not only in prose."""
        out = R.decide_verdict(design_total=34, observed_unique=7, window_complete=False)
        assert out["verdict"] == "MID_WINDOW_DIAGNOSTIC"

    def test_partial_window_at_early_exec_threshold_does_decide(self):
        """N>=15 is the registry's early-execution escape hatch."""
        out = R.decide_verdict(
            design_total=20, observed_unique=R.EARLY_EXEC_OBSERVED_N,
            window_complete=False,
        )
        assert out["verdict"] in {"ACCEPT", "REJECT"}

    def test_design_floor_gives_needs_more_evidence(self):
        out = R.decide_verdict(design_total=R.DESIGN_N_FLOOR - 1, observed_unique=0,
                               window_complete=True)
        assert out["verdict"] == "NEEDS_MORE_EVIDENCE"

    def test_capture_at_accept_threshold_accepts(self):
        n = 20
        out = R.decide_verdict(design_total=n, observed_unique=int(n * R.CAPTURE_ACCEPT),
                               window_complete=True)
        assert out["verdict"] == "ACCEPT"

    def test_capture_below_threshold_rejects(self):
        out = R.decide_verdict(design_total=20, observed_unique=15, window_complete=True)
        assert out["verdict"] == "REJECT"
        assert out["capture"] == pytest.approx(0.75)

    def test_boundaries_match_the_frozen_packet(self):
        assert (R.DESIGN_N_FLOOR, R.CAPTURE_ACCEPT, R.EARLY_EXEC_OBSERVED_N) == (15, 0.80, 15)

    def test_window_is_the_registry_window(self):
        assert R.WINDOW_START.startswith("2026-08-11")
        # end is exclusive, so the inclusive last day is 2026-09-10
        assert (pd.Timestamp(R.WINDOW_END) - pd.Timedelta(seconds=1)).date() == \
            pd.Timestamp("2026-09-10").date()


class TestRowClassification:
    def test_live_is_decided_by_oanda_trade_id_not_is_shadow(self):
        """MEMORY feedback_live_vs_shadow_strict_separation: is_shadow=0 alone
        is not a live test."""
        assert R.is_live(_row("2026-08-20T07:41:00Z", oanda_trade_id="12345"))
        assert not R.is_live(_row("2026-08-20T07:41:00Z", oanda_trade_id=""))
        assert not R.is_live(_row("2026-08-20T07:41:00Z", oanda_trade_id="   "))
        blank_but_flagged = _row("2026-08-20T07:41:00Z", oanda_trade_id="")
        blank_but_flagged["is_shadow"] = 0
        assert not R.is_live(blank_but_flagged)

    def test_dedup_violations_are_dropped(self, tmp_path):
        payload = {"trades": [
            _row("2026-08-20T07:41:00Z"),
            _row("2026-08-20T09:41:00Z", dedup=1),
            _row("2026-08-20T10:41:00Z", entry_type="donchian_momentum_breakout"),
        ]}
        import json
        p = tmp_path / "t.json"
        p.write_text(json.dumps(payload))
        rows = R.load_observed(str(p), "2026-08-11")
        assert len(rows) == 1

    def test_unique_key_collapses_same_bar_duplicates(self):
        a = _row("2026-08-20T07:01:00Z")
        b = _row("2026-08-20T07:59:00Z")
        assert R.unique_key(a) == R.unique_key(b)

    def test_unique_key_separates_adjacent_bars(self):
        a = _row("2026-08-20T07:59:00Z")
        b = _row("2026-08-20T08:01:00Z")
        assert R.unique_key(a) != R.unique_key(b)


class TestDesignSide:
    def test_design_count_uses_the_production_strategy(self):
        """The condition must not be re-implemented in the tool: the mask has to
        come from the registered strategy object."""
        strat = R.strategy_for("price_shock_rev_eur_gbp_h1_long")
        assert strat.cfg.pair == "EUR_GBP"
        assert hasattr(strat, "signal_mask_from_dataframe")

    def test_every_seat_resolves_to_a_registered_strategy(self):
        for entry_type, (pair, _symbol) in R.SEATS.items():
            strat = R.strategy_for(entry_type)
            assert strat.cfg.pair == pair

    def test_design_signal_bars_respects_the_window(self):
        idx = pd.date_range("2026-08-01", periods=400, freq="1h", tz="UTC")
        df = pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0}, index=idx)

        class FakeStrategy:
            def signal_mask_from_dataframe(self, d):
                m = pd.Series(False, index=d.index)
                m.iloc[[0, 100, 399]] = True
                return m

        start, end = idx[50], idx[200]
        bars = R.design_signal_bars(FakeStrategy(), df, start, end)
        assert bars == [idx[100]]


class TestTopupMerge:
    def test_merge_is_a_union_and_never_replaces_frozen_bars(self, tmp_path):
        idx = pd.date_range("2026-01-01", periods=50, freq="1h", tz="UTC")
        frozen = pd.DataFrame(
            {"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": np.arange(50.0)}, index=idx
        )
        frozen.to_parquet(tmp_path / "EUR_GBP_1h_12y_audit.parquet")

        # Top-up overlaps the frozen tail with *different* closes and extends past it.
        fresh_idx = pd.date_range(idx[40], periods=30, freq="1h", tz="UTC")
        fresh = pd.DataFrame(
            {"Open": 9.0, "High": 9.0, "Low": 9.0, "Close": 999.0}, index=fresh_idx
        )

        merged, prov = R.load_canonical_h1(
            "EUR_GBP", "EURGBP=X", tmp_path, fetcher=lambda *a, **k: fresh
        )
        # frozen rows survive untouched
        np.testing.assert_allclose(
            merged.loc[idx, "Close"].to_numpy(), frozen["Close"].to_numpy()
        )
        # and the extension is present, minus the still-forming last bar
        assert merged.index.max() == fresh_idx[-2]
        assert prov["overlap_bars"] == 10  # idx[40]..idx[49]

    def test_provenance_reports_frozen_topup_disagreement(self, tmp_path):
        idx = pd.date_range("2026-01-01", periods=20, freq="1h", tz="UTC")
        frozen = pd.DataFrame(
            {"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0}, index=idx
        )
        frozen.to_parquet(tmp_path / "AUD_JPY_1h_12y_audit.parquet")
        fresh = pd.DataFrame(
            {"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.5},
            index=pd.date_range(idx[10], periods=15, freq="1h", tz="UTC"),
        )
        _merged, prov = R.load_canonical_h1(
            "AUD_JPY", "AUDJPY=X", tmp_path, fetcher=lambda *a, **k: fresh
        )
        assert prov["overlap_close_max_abs_diff"] == pytest.approx(0.5)
        assert prov["overlap_bars_exact"] == 0


class TestWilson:
    def test_zero_n_is_nan_not_zero(self):
        lo, hi = R.wilson(0, 0)
        assert np.isnan(lo) and np.isnan(hi)

    def test_interval_brackets_the_point_estimate(self):
        lo, hi = R.wilson(7, 34)
        assert lo < 7 / 34 < hi
        assert 0.0 <= lo and hi <= 1.0

    def test_zero_successes_has_zero_lower_bound(self):
        lo, hi = R.wilson(0, 6)
        assert lo == pytest.approx(0.0)
        assert hi > 0
