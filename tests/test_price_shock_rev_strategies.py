from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from strategies.hourly.price_shock_rev_aud_jpy_h1_long import PriceShockRevAudJpyH1Long
from strategies.hourly.price_shock_rev_eur_aud_h1_long import PriceShockRevEurAudH1Long
from strategies.hourly.price_shock_rev_eur_gbp_h1_long import PriceShockRevEurGbpH1Long
from strategies.hourly.price_shock_rev_nzd_jpy_h1_long import PriceShockRevNzdJpyH1Long
from strategies.hourly.price_shock_rev_usd_cad_h1_long import PriceShockRevUsdCadH1Long
from tools.price_shock_reversion_bt import add_precomputed_columns


MASSIVE = Path("data/cache/massive")

STRATEGY_CASES = [
    ("EUR_GBP", PriceShockRevEurGbpH1Long, "Q5"),
    ("EUR_AUD", PriceShockRevEurAudH1Long, "Q5"),
    ("USD_CAD", PriceShockRevUsdCadH1Long, "Q5"),
    ("NZD_JPY", PriceShockRevNzdJpyH1Long, "Q5"),
    ("AUD_JPY", PriceShockRevAudJpyH1Long, "ALL"),
]


def _read_massive(pair: str) -> pd.DataFrame:
    path = MASSIVE / f"{pair}_1h.parquet"
    assert path.exists(), f"MASSIVE {pair} H1 parquet 必須 (BT must use MASSIVE)"
    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def eur_gbp_h1_df() -> pd.DataFrame:
    return _read_massive("EUR_GBP")


def test_lower_percentile_excludes_current_bar(eur_gbp_h1_df: pd.DataFrame):
    """current bar の log_return が 252-bar rolling quantile に含まれてはいけない。"""
    df = eur_gbp_h1_df.copy()
    df["log_return"] = np.log(df["Close"] / df["Close"].shift(1))
    shifted = df["log_return"].shift(1)
    quantile_correct = shifted.rolling(252, min_periods=252).quantile(0.01)
    quantile_wrong = df["log_return"].rolling(252, min_periods=252).quantile(0.01)

    strat = PriceShockRevEurGbpH1Long()
    got = strat.add_precomputed_columns(eur_gbp_h1_df)["lower_0p01"]
    diff = (got - quantile_correct).dropna().abs()
    assert diff.max() <= 1e-12
    aligned = pd.concat([quantile_correct, quantile_wrong], axis=1).dropna()
    assert (aligned.iloc[:, 0] != aligned.iloc[:, 1]).any(), (
        "shifted vs non-shifted が同じなら test 自体無意味"
    )


@pytest.mark.parametrize(("pair", "strategy_cls", "vol_q"), STRATEGY_CASES)
def test_strategy_matches_bt_runner_bar_by_bar(pair: str, strategy_cls, vol_q: str):
    """BT runner と戦略実装で同一 bar に同一シグナルが出ること。"""
    df = _read_massive(pair)
    strat = strategy_cls()
    bt_df = add_precomputed_columns(df, "H1")
    if vol_q == "ALL":
        bt_mask = (bt_df["log_return"] <= bt_df["lower_0p01"]).fillna(False)
    else:
        bt_mask = (
            (bt_df["log_return"] <= bt_df["lower_0p01"])
            & (bt_df["vol_quintile_calc"] == vol_q)
        ).fillna(False)

    strategy_mask = strat.signal_mask_from_dataframe(df)
    diff = bt_mask.fillna(False) ^ strategy_mask.fillna(False)
    assert int(diff.sum()) == 0, f"{pair}: BT runner と戦略実装が {int(diff.sum())} bar で不一致"

    strategy_df = strat.add_precomputed_columns(df)
    for col in ["log_return", "vol20", "lower_0p01", "vol_q20", "vol_q40", "vol_q60", "vol_q80"]:
        delta = (bt_df[col] - strategy_df[col]).dropna().abs()
        assert delta.max() <= 1e-12, f"{pair}: {col} differs from BT runner"
    assert (
        bt_df["vol_quintile_calc"].fillna("NA").eq(strategy_df["vol_quintile_calc"].fillna("NA")).all()
    )


def test_catastrophic_sl_distance_is_finite_and_positive(eur_gbp_h1_df: pd.DataFrame):
    """SL distance が NaN / 負 / 0 にならないこと。"""
    strat = PriceShockRevEurGbpH1Long()
    mask = strat.signal_mask_from_dataframe(eur_gbp_h1_df)
    signal_positions = np.flatnonzero(mask.to_numpy())
    assert len(signal_positions) > 0

    result = None
    for pos in signal_positions:
        result = strat.evaluate_from_dataframe(eur_gbp_h1_df.iloc[: pos + 1])
        if result is not None:
            break

    assert result is not None
    sl_distance = result.sr_meta["sl_distance"]
    assert np.isfinite(sl_distance)
    assert sl_distance > 0
    assert result.sr_meta["is_shadow"] is True
