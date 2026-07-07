from __future__ import annotations

from tools import donchian_nzd_365d_bt as bt


def test_massive_15m_cache_loads_and_pip_mult_is_pair_correct():
    from tests.conftest import require_data_file
    require_data_file(bt.cache_path("NZD_JPY"), "MASSIVE 15m integration")
    require_data_file(bt.cache_path("NZD_USD"), "MASSIVE 15m integration")
    nzd_jpy = bt.load_massive_15m("NZD_JPY")
    nzd_usd = bt.load_massive_15m("NZD_USD")

    assert len(nzd_jpy) > 0
    assert len(nzd_usd) > 0
    assert bt.pip_mult("NZD_JPY") == 100
    assert bt.pip_mult("NZD_USD") == 10000
    assert str(bt.cache_path("NZD_JPY")).endswith("data/cache/massive/NZD_JPY_15m.parquet")


def test_real_bt_function_calls_production_signal_and_generates_trades():
    from tests.conftest import require_data_file
    require_data_file(bt.cache_path("NZD_JPY"), "MASSIVE 15m integration")
    result = bt.run_pair_bt("NZD_JPY")
    stats = bt.stats_for(result["trades"])

    assert result["pip_mult"] == 100
    assert result["source"].endswith("NZD_JPY_15m.parquet")
    assert stats["N"] > 0
    assert all(trade.pair == "NZD_JPY" for trade in result["trades"])
    assert {trade.direction for trade in result["trades"]} <= {"BUY", "SELL"}
