"""rnb WAIT シグナルの entry=0 汚染回帰テスト。

compute_rnb_signal は WAIT 時も実 Close を entry に返さなければならない。
entry=0 の WAIT は demo_trader._tick 経由で _price_history を 0 汚染し、
USD_JPY の spike/velocity gate を誤発火させる (2026-04-05 db5e3e4c 起源、
2026-07-06 特定。PRICE_HISTORY_GUARD が drop していた ~2,880件/日 の発生源)。
"""
import pandas as pd
import numpy as np
import pytest

import app as app_mod


def _make_df(hour_utc: int, n: int = 60, close: float = 150.123) -> pd.DataFrame:
    idx = pd.date_range(
        end=pd.Timestamp(2026, 7, 6, hour_utc, 45, tz="UTC"), periods=n, freq="15min"
    )
    base = np.full(n, close)
    return pd.DataFrame(
        {
            "Open": base,
            "High": base + 0.02,
            "Low": base - 0.02,
            "Close": base,
            "atr": np.full(n, 0.07),
        },
        index=idx,
    )


def test_wait_outside_utc_window_carries_real_close():
    df = _make_df(hour_utc=3)  # UTC 7-20 外 → 必ず WAIT
    sig = app_mod.compute_rnb_signal(df, symbol="USD_JPY")
    assert sig["signal"] == "WAIT"
    assert sig["entry"] == pytest.approx(150.123)


def test_wait_inside_window_no_zone_match_carries_real_close():
    # 窓内だが round-number zone から外した価格 → zone 不一致 WAIT
    df = _make_df(hour_utc=10, close=150.271)
    sig = app_mod.compute_rnb_signal(df, symbol="USD_JPY")
    assert sig["signal"] == "WAIT"
    assert sig["entry"] == pytest.approx(150.271)


def test_short_df_early_return_keeps_zero_entry():
    # len 不足の早期 return のみ entry=0 を許容 (_tick 側が len<50 で先に return する)
    df = _make_df(hour_utc=10).iloc[-5:]
    sig = app_mod.compute_rnb_signal(df, symbol="USD_JPY")
    assert sig["signal"] == "WAIT"
    assert sig["entry"] == 0
