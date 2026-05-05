import pandas as pd

from strategies.context import SignalContext
from strategies.daytrade.doji_breakout import DojiBreakout


def _ctx(df: pd.DataFrame, *, entry: float = 1.10125) -> SignalContext:
    return SignalContext(
        entry=entry,
        open_price=float(df.iloc[-1]["Open"]),
        atr=0.0010,
        ema9=1.1010,
        ema21=1.1008,
        adx=25.0,
        symbol="EURUSD=X",
        is_jpy=False,
        pip_mult=10000,
        df=df,
        htf={"agreement": "bull"},
    )


def _bars(breakout_open: float, breakout_close: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Open": 1.10050, "High": 1.10100, "Low": 1.10000, "Close": 1.10052},
            {"Open": 1.10045, "High": 1.10095, "Low": 1.10005, "Close": 1.10043},
            {"Open": 1.10055, "High": 1.10090, "Low": 1.10010, "Close": 1.10056},
            {"Open": breakout_open, "High": max(breakout_open, breakout_close) + 0.00005,
             "Low": min(breakout_open, breakout_close) - 0.00005, "Close": breakout_close},
            {"Open": 1.10125, "High": 1.10130, "Low": 1.10110, "Close": 1.10125},
        ]
    )


def test_range_close_variant_rejects_bullish_body_inside_doji_range():
    df = _bars(1.10010, 1.10085)

    result = DojiBreakout(require_range_close=True).evaluate(_ctx(df))

    assert result is None


def test_range_close_variant_accepts_bullish_close_above_doji_high_plus_buffer():
    df = _bars(1.10010, 1.10120)

    result = DojiBreakout(require_range_close=True).evaluate(_ctx(df))

    assert result is not None
    assert result.signal == "BUY"
    assert result.entry_type == "doji_breakout"


def test_range_close_variant_rejects_bearish_body_inside_doji_range():
    df = _bars(1.10090, 1.10020)

    result = DojiBreakout(require_range_close=True).evaluate(_ctx(df, entry=1.10005))

    assert result is None
