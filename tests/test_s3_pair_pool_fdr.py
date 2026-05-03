import json
from pathlib import Path

import pandas as pd
import pytest

from tools.bt import s3_pair_pool_fdr as s3


def test_benjamini_hochberg_marks_all_pairs_up_to_largest_passing_rank():
    rows = [
        {"pair": "USDJPY", "p_value": 0.01},
        {"pair": "USDCAD", "p_value": 0.03},
        {"pair": "USDCHF", "p_value": 0.20},
        {"pair": "GBPUSD", "p_value": 0.40},
        {"pair": "EURUSD", "p_value": 0.50},
        {"pair": "NZDUSD", "p_value": 0.90},
    ]

    adjusted = s3.benjamini_hochberg(rows, q=0.10)

    significant = [row["pair"] for row in adjusted if row["bh_significant"]]
    assert significant == ["USDJPY", "USDCAD"]
    assert adjusted[0]["bh_q_value"] == pytest.approx(0.06)
    assert adjusted[1]["bh_q_value"] == pytest.approx(0.09)


def test_build_trades_uses_literal_mapping_and_next_friday_to_next_friday():
    cot = pd.DataFrame(
        [
            {
                "report_date": "2024-01-02",
                "change_in_dealer_long_all": 10,
                "change_in_dealer_short_all": -3,
            },
            {
                "report_date": "2024-01-09",
                "change_in_dealer_long_all": -7,
                "change_in_dealer_short_all": 2,
            },
            {
                "report_date": "2024-01-16",
                "change_in_dealer_long_all": 1,
                "change_in_dealer_short_all": 1,
            },
        ]
    )
    prices = pd.DataFrame(
        [
            {"date": "2024-01-05", "close": 100.0},
            {"date": "2024-01-12", "close": 101.0},
            {"date": "2024-01-19", "close": 102.0},
        ]
    )

    trades = s3.build_trades("USDJPY", cot, prices, exclude_events=False)

    assert len(trades) == 2
    assert trades.iloc[0]["side"] == "BUY"
    assert trades.iloc[0]["entry_date"].strftime("%Y-%m-%d") == "2024-01-05"
    assert trades.iloc[0]["exit_date"].strftime("%Y-%m-%d") == "2024-01-12"
    assert trades.iloc[0]["return_pips"] == pytest.approx(98.0)
    assert trades.iloc[1]["side"] == "SELL"
    assert trades.iloc[1]["return_pips"] == pytest.approx(-102.0)


def test_cache_only_mode_reports_missing_pair_cache(tmp_path):
    result = s3.run_backtest(
        pairs=["USDJPY"],
        cot_cache=tmp_path / "cot_cache",
        price_cache=tmp_path / "price_cache",
        use_cache_only=True,
        bootstrap_iterations=10,
    )

    assert result["status"] == "Insufficient(cache_missing)"
    assert "USDJPY" in result["missing_cache"]["cot"]
    assert "USDJPY" in result["missing_cache"]["price"]


def test_wave1_regression_checker_uses_five_percent_tolerance():
    assert s3.wave1_regression_status({"pf": 1.205, "wilson_lo": 0.470})["pass"] is True
    assert s3.wave1_regression_status({"pf": 1.05, "wilson_lo": 0.470})["pass"] is False


def test_report_files_are_written_for_insufficient_cache(tmp_path):
    result = {
        "status": "Insufficient(cache_missing)",
        "scenario": "Insufficient(cache_missing)",
        "missing_cache": {"cot": ["USDJPY"], "price": ["USDJPY"]},
        "generated_at": "2026-05-03T17:30:00+09:00",
    }

    json_path = tmp_path / "result.json"
    md_path = tmp_path / "result.md"
    s3.write_outputs(result, json_path=json_path, md_path=md_path)

    assert json.loads(json_path.read_text())["status"] == "Insufficient(cache_missing)"
    assert "Insufficient(cache_missing)" in md_path.read_text()
