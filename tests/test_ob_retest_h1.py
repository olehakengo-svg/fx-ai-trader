from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from modules.demo_trader import DemoTrader
from strategies.context import SignalContext
from strategies.hourly import HourlyEngine
from strategies.hourly.ob_retest import ObRetestH1


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    prev_close = out["Close"].shift(1)
    tr = pd.concat(
        [
            out["High"] - out["Low"],
            (out["High"] - prev_close).abs(),
            (out["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr"] = tr.rolling(14, min_periods=1).mean()
    out["atr7"] = tr.rolling(7, min_periods=1).mean()
    out["ema9"] = out["Close"].ewm(span=9, adjust=False).mean()
    out["ema21"] = out["Close"].ewm(span=21, adjust=False).mean()
    out["ema50"] = out["Close"].ewm(span=50, adjust=False).mean()
    out["ema200"] = out["Close"].ewm(span=200, adjust=False).mean()
    out["rsi"] = 50.0
    out["macd_hist"] = 0.0
    out["bb_pband"] = 0.5
    return out


def _ctx(df: pd.DataFrame, symbol: str = "USDJPY=X") -> SignalContext:
    row = df.iloc[-1]
    is_jpy = "JPY" in symbol.upper()
    return SignalContext(
        entry=float(row["Close"]),
        open_price=float(row["Open"]),
        atr=float(row["atr"]),
        atr7=float(row["atr7"]),
        ema9=float(row["ema9"]),
        ema21=float(row["ema21"]),
        ema50=float(row["ema50"]),
        ema200=float(row["ema200"]),
        rsi=float(row["rsi"]),
        macdh=float(row["macd_hist"]),
        bbpb=float(row["bb_pband"]),
        symbol=symbol,
        tf="1h",
        is_jpy=is_jpy,
        pip_mult=100 if is_jpy else 10000,
        df=df,
        backtest_mode=True,
        bar_time=df.index[-1],
    )


def _synthetic_df(side: str = "BUY") -> pd.DataFrame:
    n = 65
    idx = pd.date_range(end="2026-05-18 12:00", periods=n, freq="1h", tz="UTC")
    data = {
        "Open": np.full(n, 100.00),
        "High": np.full(n, 100.08),
        "Low": np.full(n, 99.92),
        "Close": np.full(n, 100.01),
        "Volume": np.full(n, 1000.0),
        "atr": np.full(n, 0.20),
        "atr7": np.full(n, 0.20),
        "ema9": np.full(n, 100.08),
        "ema21": np.full(n, 100.02),
        "ema50": np.full(n, 100.00),
        "ema200": np.full(n, 100.00),
        "rsi": np.full(n, 50.0),
        "macd_hist": np.full(n, 0.0),
        "bb_pband": np.full(n, 0.5),
    }
    df = pd.DataFrame(data, index=idx)
    c = n - 5
    if side == "BUY":
        df.iloc[c, df.columns.get_loc("Open")] = 100.05
        df.iloc[c, df.columns.get_loc("High")] = 100.15
        df.iloc[c, df.columns.get_loc("Low")] = 99.85
        df.iloc[c, df.columns.get_loc("Close")] = 99.90
        for j, close in enumerate([100.20, 100.35, 100.55], start=1):
            df.iloc[c + j, df.columns.get_loc("Open")] = close - 0.18
            df.iloc[c + j, df.columns.get_loc("Close")] = close
            df.iloc[c + j, df.columns.get_loc("High")] = close + 0.05
            df.iloc[c + j, df.columns.get_loc("Low")] = close - 0.20
        df.iloc[-1, df.columns.get_loc("Open")] = 100.02
        df.iloc[-1, df.columns.get_loc("Low")] = 100.08
        df.iloc[-1, df.columns.get_loc("High")] = 100.28
        df.iloc[-1, df.columns.get_loc("Close")] = 100.18
    else:
        df["ema9"] = 99.92
        df["ema21"] = 99.98
        df.iloc[c, df.columns.get_loc("Open")] = 99.95
        df.iloc[c, df.columns.get_loc("High")] = 100.15
        df.iloc[c, df.columns.get_loc("Low")] = 99.85
        df.iloc[c, df.columns.get_loc("Close")] = 100.10
        for j, close in enumerate([99.80, 99.65, 99.45], start=1):
            df.iloc[c + j, df.columns.get_loc("Open")] = close + 0.18
            df.iloc[c + j, df.columns.get_loc("Close")] = close
            df.iloc[c + j, df.columns.get_loc("High")] = close + 0.20
            df.iloc[c + j, df.columns.get_loc("Low")] = close - 0.05
        df.iloc[-1, df.columns.get_loc("Open")] = 99.98
        df.iloc[-1, df.columns.get_loc("Low")] = 99.72
        df.iloc[-1, df.columns.get_loc("High")] = 99.92
        df.iloc[-1, df.columns.get_loc("Close")] = 99.82
    return df


def run_ob_retest_h1_backtest(pair: str, days: int = 30) -> dict:
    path = Path("data/cache/massive") / f"{pair}_1h.parquet"
    assert path.exists(), f"real MASSIVE parquet is required: {path}"
    raw = pd.read_parquet(path).sort_index()
    end = raw.index.max()
    start = end - pd.Timedelta(days=days)
    df = _add_indicators(raw.loc[raw.index >= start])
    strategy = ObRetestH1()
    symbol = pair.replace("_", "") + "=X"
    pip_mult = 100 if "JPY" in pair else 10000
    trades = []
    i = max(ObRetestH1.OB_LOOKBACK, 30)
    while i < len(df) - 1:
        window = df.iloc[: i + 1]
        cand = strategy.evaluate(_ctx(window, symbol=symbol))
        if cand is None:
            i += 1
            continue
        entry = float(window.iloc[-1]["Close"])
        max_exit = min(len(df) - 1, i + (cand.max_hold_bars or 24))
        exit_i = max_exit
        exit_price = float(df.iloc[max_exit]["Close"])
        outcome = "TIME"
        for j in range(i + 1, max_exit + 1):
            row = df.iloc[j]
            if cand.signal == "BUY":
                if float(row["Low"]) <= cand.sl:
                    exit_i, exit_price, outcome = j, cand.sl, "LOSS"
                    break
                if float(row["High"]) >= cand.tp:
                    exit_i, exit_price, outcome = j, cand.tp, "WIN"
                    break
            else:
                if float(row["High"]) >= cand.sl:
                    exit_i, exit_price, outcome = j, cand.sl, "LOSS"
                    break
                if float(row["Low"]) <= cand.tp:
                    exit_i, exit_price, outcome = j, cand.tp, "WIN"
                    break
        pnl_pips = (exit_price - entry) * pip_mult
        if cand.signal == "SELL":
            pnl_pips = -pnl_pips
        trades.append({"entry_time": str(df.index[i]), "outcome": outcome, "pnl_pips": pnl_pips})
        i = exit_i + 1
    return {"pair": pair, "trades": trades, "N": len(trades)}


def test_ob_detection_unit_pushes_bullish_and_bearish_ob():
    strategy = ObRetestH1()

    bull = strategy._find_order_blocks(_ctx(_synthetic_df("BUY")))
    bear = strategy._find_order_blocks(_ctx(_synthetic_df("SELL")))

    assert any(ob.side == "BUY" for ob in bull)
    assert any(ob.side == "SELL" for ob in bear)


def test_retest_entry_unit_returns_buy_and_sell_candidate():
    buy = ObRetestH1().evaluate(_ctx(_synthetic_df("BUY")))
    sell = ObRetestH1().evaluate(_ctx(_synthetic_df("SELL")))

    assert buy is not None
    assert buy.signal == "BUY"
    assert sell is not None
    assert sell.signal == "SELL"


def test_risk_geometry_uses_atr_buffer_and_entry_price_basis():
    df = _synthetic_df("BUY")
    ctx = _ctx(df)
    cand = ObRetestH1().evaluate(ctx)

    assert cand is not None
    expected_sl = 99.85 - 0.10 * 0.20
    expected_tp = ctx.entry + (ctx.entry - expected_sl) * 1.5
    assert math.isclose(cand.sl, expected_sl, rel_tol=0, abs_tol=1e-12)
    assert math.isclose(cand.tp, expected_tp, rel_tol=0, abs_tol=1e-12)


def test_hourly_engine_includes_ob_retest_h1():
    assert any(isinstance(s, ObRetestH1) for s in HourlyEngine().strategies)


def test_m5_ob_retest_is_force_demoted():
    assert "ob_retest" in DemoTrader._FORCE_DEMOTED


def test_e2e_massive_usdjpy_h1_30d_no_exception_returns_dict():
    result = run_ob_retest_h1_backtest("USD_JPY", days=30)

    assert isinstance(result, dict)
    assert result["pair"] == "USD_JPY"
    assert result["N"] >= 0
    assert isinstance(result["trades"], list)
