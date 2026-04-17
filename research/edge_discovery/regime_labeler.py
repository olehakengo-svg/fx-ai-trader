"""
Regime Labeler — Independent OHLC → regime classification
══════════════════════════════════════════════════════════

OANDA candle を独立 source として、各 bar に regime ラベルを付与する.

目的:
1. 本番 `regime` 列 (production 自己申告) を独立データで検証
2. π_long_run (5年 regime 時間比率) の推定
3. trade レベルの regime re-classification (Simpson's paradox 対策)

アルゴリズム (MVP):
- Features: Slope t-stat (last N bars close) + ADX(14) + ATR(14)/price
- All features are right-aligned (using bars up to and including time t — 未来参照なし)
- Label rules (ternary + uncertain):
    up_trend:   slope_t > +2.0  AND  ADX > 25
    down_trend: slope_t < -2.0  AND  ADX > 25
    range:      |slope_t| < 1.0  AND  ADX < 20
    uncertain:  それ以外 (transition 帯含む)

根拠: knowledge-base/wiki/analyses/conditional-edge-estimand-2026-04-17.md §6
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional, Literal

RegimeLabel = Literal["up_trend", "down_trend", "range", "uncertain"]


# ──────────────────────────────────────────────────────
# Feature computations (all right-aligned, no look-ahead)
# ──────────────────────────────────────────────────────
def compute_slope_t(close_series, window: int = 48):
    """Rolling OLS slope + t-statistic over `window` bars.

    Args:
        close_series: pandas.Series of close prices
        window: regression window (bars)
    Returns:
        pandas.DataFrame with columns ['slope', 'slope_t']
        First (window-1) rows are NaN (insufficient data).

    数式:
        y_i = a + b*x_i + eps_i   with x_i = 0,1,...,window-1
        slope = b (closing price per bar)
        slope_t = b / SE(b) with df = window-2
    """
    import pandas as pd
    import numpy as np

    n = len(close_series)
    slopes = np.full(n, np.nan)
    ts = np.full(n, np.nan)
    x = np.arange(window)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()
    x_centered = x - x_mean

    values = close_series.values
    for i in range(window - 1, n):
        y = values[i - window + 1 : i + 1]
        if np.isnan(y).any():
            continue
        y_mean = y.mean()
        y_centered = y - y_mean
        num = (x_centered * y_centered).sum()
        b = num / x_var
        # residuals
        y_hat = y_mean + b * x_centered
        resid = y - y_hat
        sse = float((resid ** 2).sum())
        df = window - 2
        if df <= 0:
            continue
        slopes[i] = b
        if sse <= 0:
            # Perfect line (no residuals) — t is infinite if slope != 0, else 0
            if abs(b) > 1e-12:
                ts[i] = float("inf") if b > 0 else float("-inf")
            else:
                ts[i] = 0.0
            continue
        sigma2 = sse / df
        se_b = math.sqrt(sigma2 / x_var)
        ts[i] = b / se_b if se_b > 0 else 0.0
    return pd.DataFrame({"slope": slopes, "slope_t": ts},
                        index=close_series.index)


def compute_adx(df, period: int = 14):
    """Wilder's ADX (right-aligned).

    Args: df with columns ['high', 'low', 'close'].
    Returns: pandas.Series of ADX values (first `2*period` rows NaN).
    """
    import pandas as pd
    import numpy as np

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    n = len(df)
    if n < 2 * period:
        return pd.Series([np.nan] * n, index=df.index, name="adx")

    # True Range
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    # Directional Movement
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        up_move = high[i] - high[i - 1]
        down_move = low[i - 1] - low[i]
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0

    # Wilder smoothing
    def _wilder_smooth(arr, period):
        out = np.full(len(arr), np.nan)
        if len(arr) < period:
            return out
        out[period - 1] = arr[:period].sum()
        for i in range(period, len(arr)):
            out[i] = out[i - 1] - (out[i - 1] / period) + arr[i]
        return out

    tr_sm = _wilder_smooth(tr, period)
    plus_dm_sm = _wilder_smooth(plus_dm, period)
    minus_dm_sm = _wilder_smooth(minus_dm, period)

    with np.errstate(invalid="ignore", divide="ignore"):
        plus_di = 100.0 * np.where(tr_sm > 0, plus_dm_sm / tr_sm, 0.0)
        minus_di = 100.0 * np.where(tr_sm > 0, minus_dm_sm / tr_sm, 0.0)
        di_sum = plus_di + minus_di
        dx = 100.0 * np.where(di_sum > 0,
                              np.abs(plus_di - minus_di) / di_sum, 0.0)

    # ADX = Wilder smooth of DX
    adx = np.full(n, np.nan)
    start = 2 * period - 1
    if start < n:
        adx[start] = np.nanmean(dx[period - 1 : start + 1])
        for i in range(start + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    return pd.Series(adx, index=df.index, name="adx")


def compute_atr_ratio(df, period: int = 14):
    """ATR(period) / close — volatility ratio.

    Returns: pandas.Series (first `period` rows NaN).
    """
    import pandas as pd
    import numpy as np

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    n = len(df)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    atr = np.full(n, np.nan)
    if n >= period:
        atr[period - 1] = tr[:period].mean()
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    ratio = atr / close
    return pd.Series(ratio, index=df.index, name="atr_ratio")


# ──────────────────────────────────────────────────────
# Regime labeling
# ──────────────────────────────────────────────────────
@dataclass
class RegimeConfig:
    slope_window: int = 48
    adx_period: int = 14
    atr_period: int = 14
    slope_t_trend: float = 2.0       # |slope_t| > 2 で trend 候補
    slope_t_range: float = 1.0       # |slope_t| < 1 で range 候補
    adx_trend: float = 25.0          # ADX > 25 で trend 確定
    adx_range: float = 20.0          # ADX < 20 で range 確定


def label_regimes(df, config: Optional[RegimeConfig] = None):
    """Attach regime label column to a candle DataFrame.

    Args:
        df: DataFrame with columns ['time', 'open', 'high', 'low', 'close'].
            `time` should be pandas datetime (UTC recommended).
            Must be sorted ascending by time.
        config: RegimeConfig (defaults used if None)
    Returns:
        DataFrame with added columns ['slope', 'slope_t', 'adx', 'atr_ratio',
                                       'regime'].
        First few rows where features are undefined have regime='uncertain'.
    """
    import pandas as pd
    import numpy as np

    if config is None:
        config = RegimeConfig()
    out = df.copy()
    slope_df = compute_slope_t(out["close"], window=config.slope_window)
    out["slope"] = slope_df["slope"]
    out["slope_t"] = slope_df["slope_t"]
    out["adx"] = compute_adx(out, period=config.adx_period)
    out["atr_ratio"] = compute_atr_ratio(out, period=config.atr_period)

    def _classify(row):
        st = row["slope_t"]
        adx = row["adx"]
        if pd.isna(st) or pd.isna(adx):
            return "uncertain"
        if st > config.slope_t_trend and adx > config.adx_trend:
            return "up_trend"
        if st < -config.slope_t_trend and adx > config.adx_trend:
            return "down_trend"
        if abs(st) < config.slope_t_range and adx < config.adx_range:
            return "range"
        return "uncertain"

    out["regime"] = out.apply(_classify, axis=1)
    return out


# ──────────────────────────────────────────────────────
# OANDA fetch + label pipeline
# ──────────────────────────────────────────────────────
def _candles_to_df(candles: list) -> "pd.DataFrame":
    """OANDA candle list → DataFrame."""
    import pandas as pd
    rows = []
    for c in candles:
        if not c.get("complete"):
            continue  # 未確定足は除外 (look-ahead 防止)
        mid = c.get("mid", {})
        rows.append({
            "time": c["time"],
            "open": float(mid.get("o", 0)),
            "high": float(mid.get("h", 0)),
            "low": float(mid.get("l", 0)),
            "close": float(mid.get("c", 0)),
            "volume": int(c.get("volume", 0)),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").reset_index(drop=True)


def fetch_and_label(
    instrument: str = "USD_JPY",
    granularity: str = "M30",
    count: int = 500,
    config: Optional[RegimeConfig] = None,
    client=None,
):
    """Fetch OANDA candles and attach regime labels.

    Args:
        instrument: e.g. 'USD_JPY', 'EUR_USD'
        granularity: OANDA granularity ('M30', 'H1', ...)
        count: max candles per fetch (OANDA max 5000)
        client: OandaClient instance (lazy import if None)
    Returns:
        DataFrame with candle data + regime labels.
    """
    if client is None:
        from modules.oanda_client import OandaClient
        client = OandaClient()
    ok, data = client.get_candles(
        instrument=instrument, granularity=granularity, count=count, price="M"
    )
    if not ok:
        raise RuntimeError(f"OANDA candle fetch failed for {instrument}: {data}")
    df = _candles_to_df(data.get("candles", []))
    if df.empty:
        return df
    return label_regimes(df, config=config)


def estimate_pi_long_run(
    instrument: str,
    n_chunks: int = 4,
    granularity: str = "H1",
    count_per_chunk: int = 5000,
    config: Optional[RegimeConfig] = None,
    client=None,
    verbose: bool = False,
) -> dict:
    """Estimate long-run regime distribution π_long_run(regime) for an instrument.

    OANDA API は 1 req で最大 5000 bars. 過去に walking するには to_time を
    指定して反復 fetch する.

    Default: H1 × 5000 × 4 = ~20000 bars ≈ 2.5 年相当 (H1, 24h market).

    Args:
        n_chunks: number of 5000-bar chunks to fetch (walking backward)
        granularity: 'H1' 推奨 (M30 だと 5000*4=20000 bars ≈ 1.4 年; H1 の方が coverage 大)

    Returns:
        dict {'up_trend': p, 'down_trend': p, 'range': p, 'uncertain': p,
              'n_bars': N, 'start': earliest_time, 'end': latest_time}
    """
    import pandas as pd
    from datetime import timezone

    if client is None:
        from modules.oanda_client import OandaClient
        client = OandaClient()

    all_frames = []
    next_to_time: Optional[str] = None  # None = 最新から
    for i in range(n_chunks):
        if next_to_time is None:
            ok, data = client.get_candles(
                instrument=instrument, granularity=granularity,
                count=count_per_chunk, price="M"
            )
        else:
            # Walk back: fetch ending at next_to_time
            # OANDA は from/to 両方指定が必要なので、from は適当に古く設定
            from_time = "2015-01-01T00:00:00Z"
            # But then count is ignored and may return >5000. Workaround:
            # use only to_time with a short count by using count + to_time? OANDA
            # accepts count + to (returns `count` bars ending at to).
            path = (f"/v3/instruments/{instrument}/candles?"
                    f"granularity={granularity}&price=M&count={count_per_chunk}"
                    f"&to={next_to_time}")
            ok, data = client._request("GET", path, timeout=30)
        if not ok:
            if verbose:
                print(f"  chunk {i}: fetch failed, data={data}")
            break
        chunk_df = _candles_to_df(data.get("candles", []))
        if chunk_df.empty:
            break
        all_frames.append(chunk_df)
        if verbose:
            print(f"  chunk {i}: {len(chunk_df)} bars "
                  f"{chunk_df['time'].min()} → {chunk_df['time'].max()}")
        # next iteration fetches up to the earliest time we've seen
        earliest = chunk_df["time"].min()
        if hasattr(earliest, "isoformat"):
            next_to_time = earliest.astimezone(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            break  # unexpected type

    if not all_frames:
        return {"up_trend": 0, "down_trend": 0, "range": 0, "uncertain": 1.0,
                "n_bars": 0, "start": None, "end": None}
    full = (pd.concat(all_frames, ignore_index=True)
              .drop_duplicates("time")
              .sort_values("time")
              .reset_index(drop=True))
    labeled = label_regimes(full, config=config)
    counts = labeled["regime"].value_counts(normalize=True).to_dict()
    return {
        "up_trend": counts.get("up_trend", 0.0),
        "down_trend": counts.get("down_trend", 0.0),
        "range": counts.get("range", 0.0),
        "uncertain": counts.get("uncertain", 0.0),
        "n_bars": int(len(labeled)),
        "start": str(labeled["time"].min()),
        "end": str(labeled["time"].max()),
    }


# ──────────────────────────────────────────────────────
# Trade → regime join (Simpson's paradox decomposition)
# ──────────────────────────────────────────────────────
def label_trades(
    trades_df,
    candles_by_instrument: dict,
):
    """Attach regime label to each trade based on its entry_time.

    For each trade, join to the most recent FULLY-CLOSED candle at or before
    entry_time (right-aligned, no look-ahead).

    Args:
        trades_df: DataFrame with columns ['entry_time', 'instrument'].
        candles_by_instrument: dict {instrument: labeled_candle_df from
                                      fetch_and_label}.
    Returns:
        trades_df with added column 'regime_independent' ∈ {up_trend, down_trend,
        range, uncertain}.
    """
    import pandas as pd

    out = trades_df.copy()
    regime_col = []
    for _, row in out.iterrows():
        inst = row.get("instrument")
        et = row.get("entry_time")
        candles = candles_by_instrument.get(inst)
        if candles is None or candles.empty or pd.isna(et):
            regime_col.append("uncertain")
            continue
        # find most recent candle with time <= entry_time
        prior = candles[candles["time"] <= et]
        if prior.empty:
            regime_col.append("uncertain")
            continue
        regime_col.append(prior.iloc[-1]["regime"])
    out["regime_independent"] = regime_col
    return out


if __name__ == "__main__":
    # Smoke test
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    for line in open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
    )):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

    print("=== Regime Labeler smoke test ===")
    for inst in ["USD_JPY", "EUR_USD", "GBP_USD"]:
        labeled = fetch_and_label(instrument=inst, granularity="M30", count=500)
        print(f"\n{inst}: {len(labeled)} bars labeled")
        print(labeled["regime"].value_counts(normalize=True).round(3))
