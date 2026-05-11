import math

import pandas as pd

from modules.strategies.session_mr_cross import (
    DEFAULT_PARAMS,
    atr_series,
    friction_cost_pips,
    in_session_window,
    signal_session_mr_cross,
)


def _frame(closes, *, start="2026-05-01 18:00:00+00:00"):
    idx = pd.date_range(start, periods=len(closes), freq="5min")
    rows = []
    for c in closes:
        rows.append(
            {
                "Open": c,
                "High": c + 0.0010,
                "Low": c - 0.0010,
                "Close": c,
                "Volume": 1,
            }
        )
    return pd.DataFrame(rows, index=idx)


def _params(**overrides):
    out = dict(DEFAULT_PARAMS)
    out.update({"pair": "EUR_NZD", "window": "NY_LATE"})
    out.update(overrides)
    return out


def test_window_boundaries_ny_late_and_tokyo_open():
    assert in_session_window(pd.Timestamp("2026-05-01T19:00:00Z"), "NY_LATE")
    assert in_session_window(pd.Timestamp("2026-05-01T22:55:00Z"), "NY_LATE")
    assert not in_session_window(pd.Timestamp("2026-05-01T23:00:00Z"), "NY_LATE")
    assert in_session_window(pd.Timestamp("2026-05-01T22:00:00Z"), "TOKYO_OPEN")
    assert in_session_window(pd.Timestamp("2026-05-02T01:55:00Z"), "TOKYO_OPEN")
    assert not in_session_window(pd.Timestamp("2026-05-02T02:00:00Z"), "TOKYO_OPEN")


def test_buy_signal_on_low_quantile_break_uses_next_open_entry():
    closes = [1.0000] * 21 + [0.9960, 0.9962]
    df = _frame(closes, start="2026-05-01 18:15:00+00:00")
    sig = signal_session_mr_cross(df, _params(), signal_index=21)
    assert sig is not None
    assert sig.side == "BUY"
    assert sig.entry == df.iloc[22]["Open"]
    assert sig.entry_ts == df.index[22]


def test_sell_signal_on_high_quantile_break():
    closes = [1.0000] * 21 + [1.0040, 1.0038]
    df = _frame(closes, start="2026-05-01 18:15:00+00:00")
    sig = signal_session_mr_cross(df, _params(), signal_index=21)
    assert sig is not None
    assert sig.side == "SELL"
    assert sig.sl > sig.entry
    assert sig.tp < sig.entry


def test_sl_tp_distances_follow_locked_atr_multipliers():
    closes = [1.0000] * 21 + [0.9960, 0.9962]
    df = _frame(closes, start="2026-05-01 18:15:00+00:00")
    sig = signal_session_mr_cross(df, _params(), signal_index=21)
    atr = float(atr_series(df, 14).iloc[21])
    assert sig is not None
    assert math.isclose(sig.entry - sig.sl, 1.5 * atr)
    assert math.isclose(sig.tp - sig.entry, 0.5 * atr)


def test_no_signal_outside_window():
    closes = [1.0000] * 21 + [0.9960, 0.9962]
    df = _frame(closes, start="2026-05-01 10:15:00+00:00")
    assert signal_session_mr_cross(df, _params(), signal_index=21) is None


def test_no_signal_inside_quantile_band():
    closes = [1.0000] * 23
    df = _frame(closes, start="2026-05-01 18:15:00+00:00")
    assert signal_session_mr_cross(df, _params(), signal_index=21) is None


def test_friction_falls_back_for_cross_pairs_not_in_model():
    cost, source = friction_cost_pips("EUR_NZD", "NY_LATE", 20, 0.6)
    assert cost == 0.6
    assert source == "params.entry_cost_pips_fallback"

