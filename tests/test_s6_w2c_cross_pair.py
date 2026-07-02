import math
import sqlite3
from pathlib import Path

import pandas as pd

from tools import s6_chart_pattern_detector as detector
from tools import s6_w2c_cross_pair as w2c


def test_locked_w2c_ddl_contains_required_unique_tuple():
    assert "chart_pattern_w2c_cross_pair_verdicts" in w2c.W2C_DDL
    assert "UNIQUE(pattern_id, pair, timeframe, axis)" in w2c.W2C_DDL


def test_detector_schema_reused_without_mutating_detector_module():
    assert w2c.SIGNALS_DDL == detector.SQLITE_DDL


def test_gbpjpy_parquet_exists_and_loads_real_bars():
    path = Path("data/cache/massive/GBP_JPY_5m.parquet")
    from tests.conftest import require_data_file
    require_data_file(path, "MASSIVE 5m integration")
    assert path.exists()
    df = pd.read_parquet(path)
    assert len(df) > 900_000
    assert {"open", "high", "low", "close"}.issubset({c.lower() for c in df.columns})
    assert pd.Timestamp(df.index.min()).year == 2014
    assert pd.Timestamp(df.index.max()).year == 2026


def test_detector_generates_signal_from_real_gbpjpy_slice():
    from tests.conftest import require_data_file
    require_data_file("data/cache/massive/GBP_JPY_5m.parquet", "MASSIVE 5m integration")
    df = pd.read_parquet("data/cache/massive/GBP_JPY_5m.parquet").iloc[:80_000]
    signals = detector.detect_chart_patterns(df, pair="GBP_JPY", timeframe="M5")
    assert signals
    assert {s.pair for s in signals} == {"GBP_JPY"}


def test_resolve_spread_uses_literature_default_when_no_demo_samples():
    spread, source = w2c.resolve_spread("GBP_JPY", demo_paths=[])
    assert spread == 2.5
    assert source == "literature_default"


def test_resolve_spread_uses_demo_trades_empirical(tmp_path):
    db = tmp_path / "demo_trades.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE demo_trades(instrument TEXT, spread_at_entry REAL)")
        con.executemany("INSERT INTO demo_trades VALUES (?, ?)", [("GBP_JPY", 2.0), ("GBP_JPY", 3.0), ("GBP_JPY", 0.0)])
    spread, source = w2c.resolve_spread("GBP_JPY", demo_paths=[db])
    assert spread == 2.5
    assert source == "demo_trades_empirical"


def test_pip_factor_handles_jpy_and_eurusd():
    assert w2c.pip_factor("GBP_JPY") == 100.0
    assert w2c.pip_factor("EUR_USD") == 10000.0


def test_wilson_lower_known_value():
    assert math.isclose(w2c.wilson_lower(50, 100), 0.4038315303659956)


def test_profit_factor_handles_losses_and_zero_loss():
    assert w2c.profit_factor([2, -1, 3, -1]) == 2.5
    assert w2c.profit_factor([2, 3]) == math.inf
    assert w2c.profit_factor([0, 0]) == 0.0


def test_binomial_edge_p_is_small_for_clear_edge():
    assert w2c.binomial_edge_p(80, 100, 0.5) < 0.001


def test_aggregate_computes_pair_pattern_stats():
    trades = [w2c.dataclasses.replace(w2c._dummy_trade(), pnl_pips=10.0) for _ in range(60)]
    trades += [w2c.dataclasses.replace(w2c._dummy_trade(), pnl_pips=-5.0) for _ in range(40)]
    stats = w2c.aggregate(trades)
    assert stats.n == 100
    assert math.isclose(stats.wr, 0.6)
    assert math.isclose(stats.ev_pips, 4.0)
    assert math.isclose(stats.pf, 3.0)
    assert stats.max_dd_pips <= 0


def test_verdict_insufficient_before_n100():
    stats = w2c.aggregate([w2c._dummy_trade() for _ in range(99)])
    assert w2c.decide(stats, w2c.PRIMARY_M) == "INSUFFICIENT"


def test_verdict_reject_requires_pf_wilson_bonferroni_and_ev():
    trades = [w2c.dataclasses.replace(w2c._dummy_trade(), pnl_pips=1.0) for _ in range(60)]
    trades += [w2c.dataclasses.replace(w2c._dummy_trade(), pnl_pips=-2.0) for _ in range(40)]
    assert w2c.decide(w2c.aggregate(trades), w2c.PRIMARY_M) == "REJECT"


def test_verdict_can_promote_only_when_all_core_gates_pass():
    trades = [w2c.dataclasses.replace(w2c._dummy_trade(), pnl_pips=10.0) for _ in range(80)]
    trades += [w2c.dataclasses.replace(w2c._dummy_trade(), pnl_pips=-5.0) for _ in range(20)]
    assert w2c.decide(w2c.aggregate(trades), w2c.PRIMARY_M) == "PROMOTE"


def test_cross_pair_consistency_labels_null_and_contradiction():
    assert w2c.cross_pair_consistency(1, "isolated", "REJECT", 100) == "CONFIRMS_USDJPY"
    assert w2c.cross_pair_consistency(1, "isolated", "PROMOTE", 100) == "CONTRADICTS_USDJPY"
    assert w2c.cross_pair_consistency(1, "isolated", "REJECT", 99) == "N_INSUFFICIENT"


def test_d1_regime_tags_use_ema200_alignment():
    idx = pd.date_range("2020-01-01", periods=260 * 288, freq="5min", tz="UTC")
    close = pd.Series(range(len(idx)), index=idx, dtype=float) / 1000 + 100
    bars = pd.DataFrame({"open": close, "high": close + 0.1, "low": close - 0.1, "close": close}, index=idx)
    trade = w2c.dataclasses.replace(w2c._dummy_trade(), entry_ts=idx[-1].isoformat())
    tagged = w2c.tag_regimes([trade], bars)
    assert tagged[0].d1_regime == "BULL"


def test_build_verdict_rows_returns_36_pair_pattern_axis_rows():
    trades = []
    for spec in detector.PATTERNS:
        for i in range(3):
            trade = w2c.dataclasses.replace(
                w2c._dummy_trade(),
                pattern_id=spec.pattern_id,
                pattern_name=spec.name,
                d1_regime="BULL" if i % 2 == 0 else "BEAR",
            )
            trades.append(trade)
    rows = w2c.build_verdict_rows(trades, "GBP_JPY", "M5", 2.5, "literature_default")
    assert len(rows) == 36
    assert {r.axis for r in rows} == {"isolated", "regime_BULL", "regime_BEAR"}
    assert {r.bonferroni_m for r in rows if r.axis == "isolated"} == {24}
    assert {r.bonferroni_m for r in rows if r.axis != "isolated"} == {48}


def test_sqlite_write_roundtrip_for_w2c_rows(tmp_path):
    db = tmp_path / "chart_patterns.db"
    rows = w2c.build_verdict_rows([w2c._dummy_trade() for _ in range(3)], "GBP_JPY", "M5", 2.5, "literature_default")
    w2c.write_verdict_rows(db, "GBP_JPY", "M5", rows)
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM chart_pattern_w2c_cross_pair_verdicts").fetchone()[0] == 36


def test_self_test_passes():
    assert w2c.run_self_test() == {"SELF_TEST_PASS": "ok"}
