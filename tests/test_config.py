"""Tests for configuration constants in app.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import STRATEGY_PROFILES, TF_CFG, HOUR_DIRECTION_BIAS


class TestStrategyProfiles:
    def test_profiles_exist(self):
        assert "A" in STRATEGY_PROFILES
        assert "B" in STRATEGY_PROFILES

    def test_profile_a_has_required_keys(self):
        required = [
            "name", "scalp_sl", "scalp_tp", "daytrade_sl", "daytrade_tp",
            "kpi_wr", "kpi_ev", "kpi_sharpe", "kpi_maxdd",
            "breakeven_wr", "random_baseline_wr",
            "trades_per_day_min", "trades_per_day_max",
        ]
        for key in required:
            assert key in STRATEGY_PROFILES["A"], f"Missing key '{key}' in profile A"

    def test_profile_b_has_required_keys(self):
        required = [
            "name", "scalp_sl", "scalp_tp", "daytrade_sl", "daytrade_tp",
            "kpi_wr", "kpi_ev", "kpi_sharpe", "kpi_maxdd",
            "breakeven_wr", "random_baseline_wr",
            "trades_per_day_min", "trades_per_day_max",
        ]
        for key in required:
            assert key in STRATEGY_PROFILES["B"], f"Missing key '{key}' in profile B"

    def test_sl_tp_positive(self):
        for mode in ("A", "B"):
            p = STRATEGY_PROFILES[mode]
            assert p["scalp_sl"] > 0, f"{mode} scalp_sl must be positive"
            assert p["scalp_tp"] > 0, f"{mode} scalp_tp must be positive"
            assert p["daytrade_sl"] > 0, f"{mode} daytrade_sl must be positive"
            assert p["daytrade_tp"] > 0, f"{mode} daytrade_tp must be positive"

    def test_breakeven_wr_in_range(self):
        for mode in ("A", "B"):
            be = STRATEGY_PROFILES[mode]["breakeven_wr"]
            assert 0.0 < be < 1.0, f"{mode} breakeven_wr should be between 0 and 1"

    def test_kpi_targets_reasonable(self):
        for mode in ("A", "B"):
            p = STRATEGY_PROFILES[mode]
            assert 0 < p["kpi_wr"] < 1.0, f"{mode} kpi_wr out of range"
            assert p["kpi_ev"] > 0, f"{mode} kpi_ev should be positive"
            assert p["kpi_sharpe"] > 0, f"{mode} kpi_sharpe should be positive"
            assert 0 < p["kpi_maxdd"] < 1.0, f"{mode} kpi_maxdd out of range"

    def test_trades_per_day_range_valid(self):
        for mode in ("A", "B"):
            p = STRATEGY_PROFILES[mode]
            assert p["trades_per_day_min"] < p["trades_per_day_max"]
            assert p["trades_per_day_min"] >= 0


class TestTfCfg:
    def test_all_timeframes_present(self):
        expected = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
        for tf in expected:
            assert tf in TF_CFG, f"Missing timeframe '{tf}' in TF_CFG"

    def test_each_tf_has_required_keys(self):
        required = ["interval", "period", "resample", "sr_w", "sr_tol", "ch_lb"]
        for tf, cfg in TF_CFG.items():
            for key in required:
                assert key in cfg, f"TF_CFG['{tf}'] missing key '{key}'"

    def test_sr_w_positive(self):
        for tf, cfg in TF_CFG.items():
            assert cfg["sr_w"] > 0, f"TF_CFG['{tf}'] sr_w must be positive"

    def test_sr_tol_positive(self):
        for tf, cfg in TF_CFG.items():
            assert cfg["sr_tol"] > 0, f"TF_CFG['{tf}'] sr_tol must be positive"

    def test_ch_lb_positive(self):
        for tf, cfg in TF_CFG.items():
            assert cfg["ch_lb"] > 0, f"TF_CFG['{tf}'] ch_lb must be positive"


class TestHourDirectionBias:
    def test_all_hours_present(self):
        for h in range(24):
            assert h in HOUR_DIRECTION_BIAS, f"Missing hour {h}"

    def test_values_are_tuples_of_three(self):
        for h, val in HOUR_DIRECTION_BIAS.items():
            assert isinstance(val, tuple), f"Hour {h}: expected tuple"
            assert len(val) == 3, f"Hour {h}: expected 3 elements, got {len(val)}"

    def test_direction_valid(self):
        valid_dirs = {"LONG", "SHORT", None}
        for h, (direction, wr, edge) in HOUR_DIRECTION_BIAS.items():
            assert direction in valid_dirs, f"Hour {h}: invalid direction '{direction}'"

    def test_wr_in_range(self):
        for h, (_, wr, _) in HOUR_DIRECTION_BIAS.items():
            assert 0 <= wr <= 100, f"Hour {h}: WR {wr} out of range"

    def test_edge_is_numeric(self):
        for h, (_, _, edge) in HOUR_DIRECTION_BIAS.items():
            assert isinstance(edge, (int, float)), f"Hour {h}: edge must be numeric"
