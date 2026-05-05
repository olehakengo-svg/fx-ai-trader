import json
from collections import Counter
from pathlib import Path

import pandas as pd

from tools.bt.ema10_8pattern_pullback import (
    build_result,
    data_quality,
    filter_weekend_bars,
    resample_m5_to_m15,
    run_backtest,
)


FIXTURE = Path("tests/fixtures/usd_jpy_m15_2024q1.parquet")
REAL_M5 = Path("data/cache/massive/USD_JPY_5m.parquet")


def test_real_fixture_triggers_all_four_long_patterns_and_symmetric_shorts():
    df = filter_weekend_bars(pd.read_parquet(FIXTURE))
    trades, diagnostics = run_backtest(df)

    counts = diagnostics["pattern_triggers"]
    assert counts["L1"] > 0
    assert counts["L2"] > 0
    assert counts["L3"] > 0
    assert counts["L4"] > 0
    assert counts["S1"] > 0
    assert counts["S2"] > 0
    assert counts["S3"] > 0
    assert counts["S4"] > 0
    assert len(trades) > 0


def test_real_fixture_covers_entry_exit_and_management_paths():
    df = filter_weekend_bars(pd.read_parquet(FIXTURE))
    trades, diagnostics = run_backtest(df)
    exits = Counter(t.exit_reason for t in trades)

    assert diagnostics["signal_counts"]["pullback_touch"] > 0
    assert diagnostics["signal_counts"]["trend_crosses"] > 0
    assert exits["tp"] > 0
    assert exits["sl"] > 0
    assert exits["trend_cross"] > 0

    for trade in trades[:25]:
        signal_loc = df.index.get_loc(trade.signal_ts)
        entry_loc = df.index.get_loc(trade.entry_ts)
        assert entry_loc == signal_loc + 1


def test_m5_to_m15_resample_preserves_all_month_end_closes():
    df_m5 = pd.read_parquet(REAL_M5)
    df_m15 = resample_m5_to_m15(df_m5)

    m5_month_end = df_m5["close"].resample("ME").last().dropna()
    m15_month_end = df_m15["Close"].resample("ME").last().dropna()
    common = m5_month_end.index.intersection(m15_month_end.index)

    assert len(common) >= 140
    pd.testing.assert_series_equal(
        m5_month_end.loc[common].rename("Close"),
        m15_month_end.loc[common],
        check_names=False,
    )


def test_stage0_json_schema_exact_on_real_fixture(tmp_path):
    df_full = pd.read_parquet(FIXTURE)
    df = filter_weekend_bars(df_full)
    trades, diagnostics = run_backtest(df)
    result = build_result(
        trades,
        diagnostics,
        data_quality(df_full, df),
        pair="USD_JPY",
        pattern_set="all_four",
        sl_mult=1.0,
        tp_lookback=20,
        spread_pip=1.5,
        slippage_pip=0.5,
    )
    public = {k: v for k, v in result.items() if not k.startswith("_")}
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(public), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))

    assert set(loaded) == {
        "primary_cell",
        "metrics",
        "yearly_breakdown",
        "data_quality",
        "gate_decision",
        "fail_reasons",
    }
    assert set(loaded["primary_cell"]) == {
        "pair",
        "pattern_set",
        "sl_multiplier",
        "tp_lookback",
        "spread_pip",
        "slippage_pip",
    }
    assert set(loaded["metrics"]) == {
        "n",
        "wr",
        "wilson_lo_95",
        "pf",
        "ev_pip_per_trade",
        "avg_rr",
        "max_dd_pip",
        "max_dd_pct",
        "sharpe",
        "profit_year_concentration",
    }
    assert set(loaded["data_quality"]) == {
        "expected_bars",
        "actual_bars",
        "missing_pct",
        "weekend_filtered",
        "resample_method",
    }
    assert loaded["gate_decision"] in {"PASS", "FAIL"}
