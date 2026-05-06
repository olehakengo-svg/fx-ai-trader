import pandas as pd

from strategies.base import Candidate
from strategies.context import SignalContext
from strategies.scalp import ScalperEngine
from strategies.scalp.vol_momentum import VolMomentumScalp


def _df(
    *,
    signal_pband=0.92,
    current_pband=0.20,
    signal_open=150.00,
    signal_close=150.08,
    current_open=150.10,
    current_close=150.04,
    signal_adx=32.0,
    current_adx=32.0,
) -> pd.DataFrame:
    rows = []
    for i in range(60):
        rows.append(
            {
                "Open": 149.80 + i * 0.001,
                "High": 149.86 + i * 0.001,
                "Low": 149.76 + i * 0.001,
                "Close": 149.82 + i * 0.001,
                "atr": 0.05,
                "atr7": 0.05,
                "adx": 30.0,
                "adx_pos": 35.0,
                "adx_neg": 20.0,
                "rsi": 55.0,
                "rsi5": 55.0,
                "bb_pband": 0.50,
                "bb_width": 0.010,
                "ema9": 150.0,
                "ema21": 149.9,
                "ema50": 149.8,
                "ema200": 149.0,
                "macd_hist": 0.02,
            }
        )
    rows[-2].update(
        {
            "Open": signal_open,
            "High": max(signal_open, signal_close) + 0.03,
            "Low": min(signal_open, signal_close) - 0.03,
            "Close": signal_close,
            "adx": signal_adx,
            "adx_pos": 36.0,
            "adx_neg": 20.0,
            "bb_pband": signal_pband,
            "bb_width": 0.020,
        }
    )
    rows[-1].update(
        {
            "Open": current_open,
            "High": max(current_open, current_close) + 0.03,
            "Low": min(current_open, current_close) - 0.03,
            "Close": current_close,
            "adx": current_adx,
            "adx_pos": 36.0,
            "adx_neg": 20.0,
            "bb_pband": current_pband,
        }
    )
    return pd.DataFrame(
        rows,
        index=pd.date_range("2026-05-05 00:00", periods=len(rows), freq="5min", tz="UTC"),
    )


def _ctx(df: pd.DataFrame) -> SignalContext:
    row = df.iloc[-1]
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        ema50=float(row["ema50"]),
        ema200=float(row["ema200"]),
        ema200_bull=float(row["Close"]) > float(row["ema200"]),
        adx=float(row["adx"]),
        adx_pos=float(row["adx_pos"]),
        adx_neg=float(row["adx_neg"]),
        rsi=float(row["rsi"]),
        rsi5=float(row["rsi5"]),
        bbpb=float(row["bb_pband"]),
        bb_width=float(row["bb_width"]),
        bb_width_pct=0.60,
        macdh=float(row["macd_hist"]),
        symbol="USDJPY=X",
        tf="5m",
        hour_utc=12,
        is_jpy=True,
        pip_mult=100,
        df=df,
        bar_time=df.index[-1],
    )


def test_redesign_v2_default_off_preserves_current_bar_signal(monkeypatch):
    monkeypatch.delenv("VOL_MOMENTUM_REDESIGN_V2", raising=False)
    monkeypatch.delenv("VOL_MOMENTUM_SCALP_REDESIGN_V2", raising=False)
    VolMomentumScalp.reset_dedup_state()
    df = _df(signal_pband=0.50, current_pband=0.92, current_open=150.00, current_close=150.08)

    got = VolMomentumScalp().evaluate(_ctx(df))

    assert got is not None
    assert got.signal == "BUY"


def test_redesign_v2_uses_closed_signal_bar_not_current_bar(monkeypatch):
    monkeypatch.setenv("VOL_MOMENTUM_REDESIGN_V2", "1")
    VolMomentumScalp.reset_dedup_state()

    got = VolMomentumScalp().evaluate(_ctx(_df()))

    assert got is not None
    assert got.signal == "BUY"
    assert any("%B=0.92" in reason for reason in got.reasons)
    assert got.tp > _ctx(_df()).entry


def test_redesign_v2_rejects_current_bar_only_signal(monkeypatch):
    monkeypatch.setenv("VOL_MOMENTUM_REDESIGN_V2", "1")
    VolMomentumScalp.reset_dedup_state()
    df = _df(signal_pband=0.50, current_pband=0.92, current_open=150.00, current_close=150.08)

    got = VolMomentumScalp().evaluate(_ctx(df))

    assert got is None


def test_redesign_v2_dedups_by_signal_bar(monkeypatch):
    monkeypatch.setenv("VOL_MOMENTUM_REDESIGN_V2", "1")
    VolMomentumScalp.reset_dedup_state()
    strategy = VolMomentumScalp()
    ctx = _ctx(_df())

    assert strategy.evaluate(ctx) is not None
    assert strategy.evaluate(ctx) is None


def test_shadow_promote_worker_registration_is_double_flagged(monkeypatch):
    other = Candidate("SELL", 80, 2.0, 1.0, [], "other", 9.0)
    vol_momentum = Candidate("BUY", 70, 1.0, 2.0, [], "vol_momentum_scalp", 4.0)
    engine = ScalperEngine()

    monkeypatch.setenv("VOL_MOMENTUM_REDESIGN_V2", "1")
    monkeypatch.delenv("VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE", raising=False)
    assert engine.split_shadow_always([other, vol_momentum], other) == []

    monkeypatch.setenv("VOL_MOMENTUM_REDESIGN_V2_SHADOW_PROMOTE", "1")
    assert engine.split_shadow_always([other, vol_momentum], other) == [vol_momentum]
