"""Pine overlay ↔ Python BT-runner signal equivalence test.

The Pine scripts at ``bt-results/tv-overlays/price_shock_rev_*_h1_long.pine``
must emit *exactly* the same shock signals as the production strategy base
``strategies/hourly/price_shock_reversion_base.PriceShockReversionBase``.

This test re-implements the Pine logic in plain pandas (mirroring Pine's
``ta.percentile_linear_interpolation`` and ``ta.stdev(_, _, biased=false)``
semantics literally), then compares the boolean signal mask against the
BT runner's ``signal_mask_from_dataframe`` on the **real** MASSIVE H1
parquet for each pair. No mock data — feedback_codex_mock_test_trap.

Per task spec, equivalence is asserted on the most-recent 1000 fully-valid
bars (post-warmup), which is more than enough to catch any off-by-one or
window-alignment divergence.
"""
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


REPO_ROOT = Path(__file__).resolve().parent.parent
MASSIVE_DIR = REPO_ROOT / "data" / "cache" / "massive"
OVERLAY_DIR = REPO_ROOT / "bt-results" / "tv-overlays"


# ---------------------------------------------------------------------------
# Plain-pandas reimplementation of the Pine v6 overlay logic.
#
# Mapping (line-for-line with the .pine sources):
#   log_ret   = math.log(close / close[1])
#       → pandas: np.log(close / close.shift(1))
#
#   lower_thr = ta.percentile_linear_interpolation(log_ret[1], 252, 1)
#       Pine evaluates the source at bar i, i-1, ..., i-(length-1).  With
#       log_ret[1] as source, that is log_ret values at bars i-1 ... i-252,
#       which is exactly ``log_ret.shift(1).rolling(252).quantile(0.01)``.
#
#   vol20     = ta.stdev(log_ret, 20, false)
#       biased=false → unbiased / ddof=1.  Matches pandas .std() default.
#
#   q80       = ta.percentile_linear_interpolation(vol20[1], 252, 80)
#       Same shift(1).rolling(252) pattern, quantile=0.80.
#
#   in_q5    = vol20 > q80
#       (matches np.select last bucket "vol20 > vol_q80" → "Q5" in the
#       BT runner.)
#
#   vol_pass = vol_q == "ALL" or in_q5
#   shock    = (log_ret <= lower_thr) and vol_pass
# ---------------------------------------------------------------------------
def pine_signal_mask(df: pd.DataFrame, vol_q: str) -> pd.Series:
    close = df["Close"]
    log_ret = np.log(close / close.shift(1))
    lower_thr = log_ret.shift(1).rolling(252, min_periods=252).quantile(0.01)
    vol20 = log_ret.rolling(20, min_periods=20).std()  # ddof=1 (sample) by default
    q80 = vol20.shift(1).rolling(252, min_periods=252).quantile(0.80)
    in_q5 = vol20 > q80
    vol_pass = pd.Series(True, index=df.index) if vol_q == "ALL" else in_q5
    mask = (log_ret <= lower_thr) & vol_pass.fillna(False)
    return mask.fillna(False).astype(bool)


STRATEGIES = [
    ("EUR_GBP", "Q5", 3,  PriceShockRevEurGbpH1Long),
    ("EUR_AUD", "Q5", 12, PriceShockRevEurAudH1Long),
    ("USD_CAD", "Q5", 3,  PriceShockRevUsdCadH1Long),
    ("NZD_JPY", "Q5", 12, PriceShockRevNzdJpyH1Long),
    ("AUD_JPY", "ALL", 12, PriceShockRevAudJpyH1Long),
]


def _load_parquet(pair: str) -> pd.DataFrame:
    path = MASSIVE_DIR / f"{pair}_1h.parquet"
    if not path.exists():
        pytest.skip(f"MASSIVE parquet missing for {pair}: {path}")
    df = pd.read_parquet(path)
    assert {"Open", "High", "Low", "Close"}.issubset(df.columns), \
        f"{pair} parquet missing OHLC columns"
    assert len(df) >= 1500, f"{pair} parquet too small for warmup + 1000 bars"
    return df


@pytest.mark.parametrize("pair,vol_q,horizon,cls", STRATEGIES, ids=lambda x: str(x))
def test_pine_logic_matches_bt_runner(pair, vol_q, horizon, cls):
    """Pine-equivalent pandas logic must agree with the strategy base mask."""
    df = _load_parquet(pair)
    bt_runner = cls()

    # Assert pre-reg constants on the Python side match what the Pine file declares.
    assert bt_runner.cfg.percentile == 0.01, f"{pair} percentile drift"
    assert bt_runner.cfg.horizon_bars == horizon, f"{pair} horizon drift"
    assert bt_runner.cfg.vol_q == vol_q, f"{pair} vol_q drift"

    mask_py = bt_runner.signal_mask_from_dataframe(df).astype(bool)
    mask_pine = pine_signal_mask(df, vol_q)

    # Confirm test scope is non-trivial: at least one shock fires on this dataset.
    assert mask_py.sum() > 0, f"{pair}: BT runner produced zero signals — test trivially passes; check data"
    # Last 1000 fully-valid bars (post-warmup) is required by spec.
    tail = mask_py.index[-1000:]
    diff = mask_py.loc[tail].ne(mask_pine.loc[tail])
    n_diff = int(diff.sum())
    assert n_diff == 0, (
        f"{pair}: {n_diff} disagreeing bars in last 1000 — "
        f"first diverging index = {diff[diff].index[0] if n_diff else 'n/a'}"
    )


@pytest.mark.parametrize("pair,vol_q,horizon,cls", STRATEGIES, ids=lambda x: str(x))
def test_pine_logic_matches_bt_runner_full_history(pair, vol_q, horizon, cls):
    """Equivalence on the FULL parquet (defense-in-depth beyond the last 1000)."""
    df = _load_parquet(pair)
    bt_runner = cls()
    mask_py = bt_runner.signal_mask_from_dataframe(df).astype(bool)
    mask_pine = pine_signal_mask(df, vol_q)
    diff = mask_py.ne(mask_pine)
    n_diff = int(diff.sum())
    assert n_diff == 0, (
        f"{pair} FULL: {n_diff} disagreeing bars over {len(df)}; "
        f"first diverging index = {diff[diff].index[0] if n_diff else 'n/a'}"
    )


def test_overlay_files_exist():
    """All five Pine overlay files exist and declare Pine v6."""
    for pair, *_ in STRATEGIES:
        path = OVERLAY_DIR / f"price_shock_rev_{pair.lower()}_h1_long.pine"
        assert path.exists(), f"missing overlay: {path}"
        text = path.read_text(encoding="utf-8")
        assert text.lstrip().startswith("//@version=6"), \
            f"{path.name} must be Pine v6 (first line)"


def test_overlay_files_declare_locked_constants():
    """Each .pine file must literally declare PERCENTILE=0.01 and match Python horizon/vol_q.

    Guards against silent post-hoc tuning of pre-reg LOCK constants.
    """
    for pair, vol_q, horizon, cls in STRATEGIES:
        path = OVERLAY_DIR / f"price_shock_rev_{pair.lower()}_h1_long.pine"
        text = path.read_text(encoding="utf-8")
        assert "PERCENTILE   = 0.01" in text or "PERCENTILE = 0.01" in text, \
            f"{path.name}: PERCENTILE must be literal 0.01"
        assert f"HORIZON_BARS = {horizon}" in text, \
            f"{path.name}: HORIZON_BARS must equal {horizon}"
        assert f'VOL_Q        = "{vol_q}"' in text or f'VOL_Q = "{vol_q}"' in text, \
            f"{path.name}: VOL_Q must be literal {vol_q!r}"
