"""
MTF Regime Engine — Multi-Timeframe alignment-based regime detection
═════════════════════════════════════════════════════════════════════

背景 (2026-04-17 検証結果):
  単一 TF の slope_t+ADX labeler は全 TF で η² < 0.005 (trivial)
  D1 でのみ sign が揃い始め、EUR_USD で η²=0.018 (fwd-20d) に到達
  → 構造的トレンドは D1 で測定し、H4 で確認、H1/M30 で実行するべき

設計原則:
1. **階層**: D1 dominant → H4 confirm → H1 trigger
2. **予測的**: EMA cloud + slope_sign（t値の閾値ではなく方向性）で lagging 回避
3. **ペア固有性**: 閾値は ATR-normalized（全ペア共通テンプレート）
4. **ボラ次元**: trend / range × squeeze / expansion の 2×3 グリッド
5. **As-of alignment**: 下位 TF の各 bar に対し、最新完成済 D1/H4 ラベルを付与（未来参照なし）

出力 regime (7 classes):
  trend_up_strong    — D1 strong bull + H4 bull
  trend_up_weak      — D1 weak bull + H4 non-bearish
  trend_down_weak    — D1 weak bear + H4 non-bullish
  trend_down_strong  — D1 strong bear + H4 bear
  range_tight        — D1 flat + BB squeezed (reversion期待)
  range_wide         — D1 flat + BB wide (breakout待ち)
  uncertain          — D1/H4 disagreement or insufficient data
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Literal, Dict, List
import math

MTFRegime = Literal[
    "trend_up_strong", "trend_up_weak",
    "trend_down_weak", "trend_down_strong",
    "range_tight", "range_wide",
    "uncertain",
]

# Reuse ADX implementation from the baseline labeler
from research.edge_discovery.regime_labeler import (
    compute_adx as _compute_adx,
    compute_atr_ratio as _compute_atr_ratio,
    _candles_to_df,
)


# ──────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────
@dataclass
class MTFConfig:
    # --- D1 dominant trend ---
    d1_ema_fast: int = 20
    d1_ema_slow: int = 50
    d1_ema_anchor: int = 200      # price vs ema200 = regime bias
    d1_adx_period: int = 14
    d1_adx_strong: float = 25.0
    d1_adx_weak: float = 18.0

    # --- H4 confirmation (2nd opinion) ---
    h4_ema_fast: int = 20
    h4_ema_slow: int = 50

    # --- Volatility state (D1) ---
    bb_period: int = 20
    bb_k: float = 2.0
    bb_pct_window: int = 252       # 1 year of D1
    bb_squeeze_pct: float = 25.0   # width ≤ 25th pct → squeeze
    bb_expansion_pct: float = 75.0 # width ≥ 75th pct → expansion

    # --- Change-point detection (slope reversal) ---
    # For lead-indicator component: compare short MA slope vs long MA slope
    cpd_short_window: int = 10
    cpd_long_window: int = 30

    # --- Strict mode: require H4 agreement ---
    require_h4_agreement: bool = True


# ──────────────────────────────────────────────────────
# Primitives
# ──────────────────────────────────────────────────────
def ema(s, period: int):
    """Exponential moving average (pandas-based)."""
    import pandas as pd
    return s.ewm(span=period, adjust=False).mean()


def bb_width_norm(close, period: int, k: float):
    """Normalized Bollinger Band width: 2k*σ / μ."""
    import pandas as pd
    ma = close.rolling(period).mean()
    sd = close.rolling(period).std(ddof=0)
    return (2 * k * sd) / ma


def rolling_percentile(s, window: int, min_periods: int = 20):
    """Rolling percentile rank (0-100) of each value within its trailing window."""
    return s.rolling(window, min_periods=min_periods).rank(pct=True) * 100


# ──────────────────────────────────────────────────────
# Per-timeframe labeling
# ──────────────────────────────────────────────────────
def label_d1(d1, cfg: MTFConfig):
    """D1 dominant trend label ∈ {-2, -1, 0, +1, +2, NaN_code=3}.

    +2: strong bull  (price>ema200 AND ema_fast>ema_slow AND ADX≥strong)
    +1: weak bull    (price>ema200 AND ema_fast>ema_slow AND ADX≥weak)
     0: no clear trend (mixed or ADX<weak)
    -1: weak bear    (mirror)
    -2: strong bear  (mirror)
     3: insufficient data

    Returns pd.Series of int.
    """
    import pandas as pd
    import numpy as np

    close = d1["close"]
    ema_f = ema(close, cfg.d1_ema_fast)
    ema_s = ema(close, cfg.d1_ema_slow)
    ema_a = ema(close, cfg.d1_ema_anchor)
    adx = _compute_adx(d1, period=cfg.d1_adx_period)

    bull_bias = (close > ema_a) & (ema_f > ema_s)
    bear_bias = (close < ema_a) & (ema_f < ema_s)
    strong = adx >= cfg.d1_adx_strong
    weak = adx >= cfg.d1_adx_weak

    labels = np.full(len(d1), 0, dtype=int)
    labels[bull_bias & strong] = 2
    labels[bull_bias & weak & ~strong] = 1
    labels[bear_bias & strong] = -2
    labels[bear_bias & weak & ~strong] = -1

    # Mark insufficient data as 3 (NaN-sentinel)
    insufficient = ema_a.isna() | adx.isna()
    labels[insufficient.values] = 3

    return pd.Series(labels, index=d1.index, name="d1_label")


def label_h4(h4, cfg: MTFConfig):
    """H4 confirmation label ∈ {-1, 0, +1, 3}.

    +1: ema_fast > ema_slow (bull bias)
     0: |diff| < 0.001 * close (neutral / crossover zone)
    -1: ema_fast < ema_slow (bear bias)
     3: insufficient data
    """
    import pandas as pd
    import numpy as np

    close = h4["close"]
    ema_f = ema(close, cfg.h4_ema_fast)
    ema_s = ema(close, cfg.h4_ema_slow)
    diff = (ema_f - ema_s) / close
    labels = np.zeros(len(h4), dtype=int)
    labels[diff > 0.0005] = 1
    labels[diff < -0.0005] = -1
    labels[ema_s.isna().values] = 3
    return pd.Series(labels, index=h4.index, name="h4_label")


def vol_state_d1(d1, cfg: MTFConfig):
    """D1 volatility state ∈ {'squeeze', 'normal', 'expansion', 'unknown'}."""
    import pandas as pd
    import numpy as np

    width = bb_width_norm(d1["close"], cfg.bb_period, cfg.bb_k)
    pct = rolling_percentile(width, cfg.bb_pct_window, min_periods=50)
    out = np.full(len(d1), "unknown", dtype=object)
    out[(pct <= cfg.bb_squeeze_pct).values] = "squeeze"
    out[(pct > cfg.bb_squeeze_pct).values & (pct < cfg.bb_expansion_pct).values] = "normal"
    out[(pct >= cfg.bb_expansion_pct).values] = "expansion"
    return pd.Series(out, index=d1.index, name="vol_state")


# ──────────────────────────────────────────────────────
# Composite regime
# ──────────────────────────────────────────────────────
def compose_regime(d1_label: int, h4_label: int, vol: str,
                   cfg: MTFConfig) -> str:
    """Single-bar regime composition.

    Rules:
    - D1 insufficient → uncertain
    - D1=+2 + H4≥0 → trend_up_strong
    - D1=+1 + H4≥0 → trend_up_weak
    - D1=-2 + H4≤0 → trend_down_strong
    - D1=-1 + H4≤0 → trend_down_weak
    - D1=0  → range_tight (if squeeze) / range_wide (else)
    - D1/H4 disagreement with require_h4_agreement=True → uncertain
    """
    if d1_label == 3:
        return "uncertain"
    if d1_label == 0:
        if vol == "squeeze":
            return "range_tight"
        return "range_wide"
    # Trend candidate
    if d1_label > 0:
        if cfg.require_h4_agreement and h4_label < 0:
            return "uncertain"
        return "trend_up_strong" if d1_label == 2 else "trend_up_weak"
    # d1_label < 0
    if cfg.require_h4_agreement and h4_label > 0:
        return "uncertain"
    return "trend_down_strong" if d1_label == -2 else "trend_down_weak"


# ──────────────────────────────────────────────────────
# As-of alignment (no look-ahead)
# ──────────────────────────────────────────────────────
def align_higher_tf_to_lower(lower_df, higher_labels_df,
                              lower_time_col: str = "time",
                              higher_time_col: str = "time",
                              label_cols: Optional[List[str]] = None):
    """Merge_asof: for each row in lower_df, attach the MOST RECENT higher-TF
    label whose time ≤ lower_time (exclusive of current higher bar still forming).

    Critical: we use higher-TF bars that completed strictly before the lower
    bar's open time, to avoid any look-ahead.
    """
    import pandas as pd

    if label_cols is None:
        label_cols = [c for c in higher_labels_df.columns
                      if c != higher_time_col]
    right = higher_labels_df[[higher_time_col] + label_cols].copy()
    # Higher-TF bar is usable once its close is stamped at its time;
    # we conservatively use time+granularity as the "available at" time, but
    # OANDA candles are stamped at bar-open. Safer: shift by 1 row (use t-1 bar).
    right = right.sort_values(higher_time_col).reset_index(drop=True)
    # shift labels by 1 so that we never consult the "current" higher bar
    for c in label_cols:
        right[c] = right[c].shift(1)
    right = right.dropna(subset=label_cols)

    merged = pd.merge_asof(
        lower_df.sort_values(lower_time_col).reset_index(drop=True),
        right,
        left_on=lower_time_col,
        right_on=higher_time_col,
        direction="backward",
        suffixes=("", "_htf"),
    )
    return merged


# ──────────────────────────────────────────────────────
# End-to-end labeling pipeline
# ──────────────────────────────────────────────────────
def label_mtf(
    base_df,           # lower TF (H1 or M30) with ['time', OHLC]
    d1_df,             # D1 OHLC
    h4_df,             # H4 OHLC
    config: Optional[MTFConfig] = None,
):
    """Attach MTF regime label to base_df.

    Args:
        base_df: lower-TF candles (H1/M30), sorted, with 'time' + OHLC.
        d1_df, h4_df: D1 and H4 candles (sorted, with 'time' + OHLC).
        config: MTFConfig (defaults if None).

    Returns:
        DataFrame: base_df augmented with
            ['d1_label', 'h4_label', 'vol_state', 'regime_mtf'].
    """
    import pandas as pd
    import numpy as np

    if config is None:
        config = MTFConfig()

    # 1. Per-TF labels
    d1_lab = label_d1(d1_df, config)
    h4_lab = label_h4(h4_df, config)
    vol = vol_state_d1(d1_df, config)

    d1_aux = pd.DataFrame({
        "time": pd.to_datetime(d1_df["time"], utc=True).values,
        "d1_label": d1_lab.values,
        "vol_state": vol.values,
    })
    d1_aux["time"] = pd.to_datetime(d1_aux["time"], utc=True)
    h4_aux = pd.DataFrame({
        "time": pd.to_datetime(h4_df["time"], utc=True).values,
        "h4_label": h4_lab.values,
    })
    h4_aux["time"] = pd.to_datetime(h4_aux["time"], utc=True)
    # ensure base_df time is tz-aware too
    base_df = base_df.copy()
    base_df["time"] = pd.to_datetime(base_df["time"], utc=True)

    # 2. As-of merge (no look-ahead)
    out = align_higher_tf_to_lower(base_df, d1_aux,
                                    label_cols=["d1_label", "vol_state"])
    out = align_higher_tf_to_lower(out, h4_aux,
                                    label_cols=["h4_label"])

    # 3. Compose regime per row
    regimes = []
    for _, r in out.iterrows():
        d1 = r.get("d1_label")
        h4 = r.get("h4_label")
        vs = r.get("vol_state")
        if pd.isna(d1) or pd.isna(h4):
            regimes.append("uncertain")
            continue
        regimes.append(compose_regime(int(d1), int(h4),
                                       vs if isinstance(vs, str) else "unknown",
                                       config))
    out["regime_mtf"] = regimes
    return out


# ──────────────────────────────────────────────────────
# Convenience: fetch all required TFs for an instrument
# ──────────────────────────────────────────────────────
def fetch_mtf_data(
    instrument: str,
    base_granularity: str = "H1",
    base_chunks: int = 8,
    h4_chunks: int = 6,
    d1_chunks: int = 3,
    count_per_chunk: int = 5000,
    client=None,
):
    """Fetch base (H1 default), H4, D1 candles via walking-back chunks.

    Returns:
        {'base': df, 'h4': df, 'd1': df, 'instrument': instrument}
    """
    import pandas as pd
    from datetime import timezone

    if client is None:
        from modules.oanda_client import OandaClient
        client = OandaClient()

    def _walk(gran: str, n_chunks: int):
        frames = []
        next_to = None
        for _ in range(n_chunks):
            if next_to is None:
                ok, data = client.get_candles(
                    instrument=instrument, granularity=gran,
                    count=count_per_chunk, price="M",
                )
            else:
                path = (f"/v3/instruments/{instrument}/candles?"
                        f"granularity={gran}&price=M&count={count_per_chunk}"
                        f"&to={next_to}")
                ok, data = client._request("GET", path, timeout=30)
            if not ok:
                break
            chunk = _candles_to_df(data.get("candles", []))
            if chunk.empty:
                break
            frames.append(chunk)
            earliest = chunk["time"].min()
            next_to = earliest.astimezone(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ")
        if not frames:
            return pd.DataFrame()
        return (pd.concat(frames, ignore_index=True)
                .drop_duplicates("time").sort_values("time")
                .reset_index(drop=True))

    return {
        "instrument": instrument,
        "base": _walk(base_granularity, base_chunks),
        "h4": _walk("H4", h4_chunks),
        "d1": _walk("D", d1_chunks),
    }


if __name__ == "__main__":
    # Smoke test
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    for line in open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
    )):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

    print("=== MTF Engine smoke test ===")
    data = fetch_mtf_data("EUR_USD", base_granularity="H1",
                           base_chunks=2, h4_chunks=2, d1_chunks=1)
    print(f"base H1: {len(data['base'])} bars")
    print(f"H4:      {len(data['h4'])} bars")
    print(f"D1:      {len(data['d1'])} bars")
    labeled = label_mtf(data["base"], data["d1"], data["h4"])
    print(f"\nregime distribution:")
    print(labeled["regime_mtf"].value_counts(normalize=True).round(3))
