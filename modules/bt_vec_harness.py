"""Vectorized BT Harness — common infrastructure for vec BT runners (rule:R3).

Background:
  app.py:4761-4766 のコメント通り、本番 run_scalp_backtest は per-bar の
  M15/M5 features を populate しない (7d BT で 1h+ かかるため)。
  そのため MTF features を必要とする戦略 (mtf_*_scalp,
  mtf_regime_*_cascade_scalp 等) は run_scalp_backtest 経由では N=0 に
  終わる。

  これらの戦略は HTF を 1 度だけ前計算 → merge_asof で 1m に forward-fill
  する vec runner で BT する必要がある。当初 _bt_regime_cascade_scalp_vec.py
  と _bt_mtf_cascade_scalp_vec.py がそれぞれ独立に実装したが、共通コード
  (~250行) が重複していた。本 module はその共通基盤。

Architecture:
  - HtfFeatureSpec: どの HTF feature を per-bar に展開するかの宣言
  - load_1m / load_htf: ローカル parquet キャッシュ + OANDA + yfinance fallback
  - precompute_htf_features: M15 / M5 features の事前計算
  - simulate_outcome: SL/TP touch シミュレーション (pip_mult bug fixed)
  - run_vec_bt: メインループ (cascade な if-cooldown ループ)
  - cell_stats: 統計サマリ (Wilson + PF + Kelly)

Usage example:
  from modules.bt_vec_harness import VecBacktestRunner, HtfFeatureSpec

  spec = HtfFeatureSpec(
      m15_fields=["adx", "ema9", "ema21", "ema_slope"],
      m5_fields=["sma21", "bbpb", "swing_high", "swing_low",
                 "rsi_div_bear", "rsi_div_bull"],
  )
  runner = VecBacktestRunner(spec=spec, strategy_factory=lambda: MyStrategy())
  result = runner.run(symbol="USDJPY=X", days=90)

Notes:
  - 本 module は live trading コードに副作用を持たない (BT 専用)
  - autostart 抑制は呼び出し側スクリプトの責任 (BT_MODE / NO_AUTOSTART)
"""
from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd


# ─── Stats helpers ───────────────────────────────────────────────────
def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    """Wilson score interval lower bound, returned as percentage (0-100)."""
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / den) * 100.0


def profit_factor_local(pnls: list[float]) -> float:
    """PF over a list of signed pnls (positive=win, negative=loss)."""
    gw = sum(p for p in pnls if p > 0)
    gl = abs(sum(p for p in pnls if p < 0))
    if gl <= 0:
        return float("inf") if gw > 0 else 0.0
    return gw / gl


def kelly_pct(wr: float, avg_win: float, avg_loss: float) -> float:
    """Kelly fraction as percentage. wr ∈ [0,1], avg_win > 0, avg_loss < 0."""
    if avg_loss >= 0 or avg_win <= 0:
        return 0.0
    b = avg_win / abs(avg_loss)
    p = wr
    q = 1 - p
    if b <= 0:
        return 0.0
    f = (b * p - q) / b
    return max(0.0, f) * 100.0


# ─── Data loading ────────────────────────────────────────────────────
_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "cache", "massive",
)
_CACHE_SYMBOL_MAP = {
    "USDJPY=X": "USD_JPY", "EURUSD=X": "EUR_USD", "GBPUSD=X": "GBP_USD",
    "USDJPY": "USD_JPY", "EURUSD": "EUR_USD",
    "USD_JPY": "USD_JPY", "EUR_USD": "EUR_USD",
}


def _load_local_cache(symbol: str, interval: str, days: int) -> Optional[pd.DataFrame]:
    """Read parquet from data/cache/massive/. Returns None on miss / too-small.

    `days=0` means return the entire cache (used for HTF reference frames).
    """
    cache_sym = _CACHE_SYMBOL_MAP.get(
        symbol, symbol.replace("=X", "").replace("/", "_")
    )
    suffix_map = {
        "1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h",
        "M5": "5m", "M15": "15m", "H1": "1h",
    }
    suffix = suffix_map.get(interval, interval)
    path = os.path.join(_CACHE_DIR, f"{cache_sym}_{suffix}.parquet")
    if not os.path.exists(path):
        return None
    df = pd.read_parquet(path)
    if days > 0:
        cutoff = df.index[-1] - pd.Timedelta(days=days)
        df = df[df.index >= cutoff]
    return df if len(df) >= 50 else None


def load_1m(symbol: str, days: int, verbose: bool = True) -> pd.DataFrame:
    """Load 1m bars: local parquet → yfinance fallback (7d max)."""
    df = _load_local_cache(symbol, "1m", days)
    if df is not None and len(df) >= 100:
        if verbose:
            print(f"  [local-cache] 1m: {len(df)} bars")
        return df
    from modules.data import fetch_ohlcv
    period = f"{min(days, 7)}d"
    df = fetch_ohlcv(symbol, period=period, interval="1m")
    if df is None or len(df) < 100:
        raise RuntimeError(f"All data sources failed for {symbol}/1m")
    return df


def load_htf(symbol: str, granularity: str, count: int = 5000,
             verbose: bool = True) -> pd.DataFrame:
    """Load HTF bars: local parquet → OANDA → yfinance fallback.

    granularity ∈ {'M15', 'M5'}.
    """
    df = _load_local_cache(symbol, granularity, days=0)
    if df is not None and len(df) >= 50:
        if verbose:
            print(f"  [local-cache] {granularity}: {len(df)} bars")
        return df
    from modules.htf_data_source import fetch_htf_candles
    from modules.data import fetch_ohlcv
    try:
        df = fetch_htf_candles(symbol, granularity=granularity, count=count)
        if df is not None and len(df) >= 50:
            return df
    except Exception as e:
        print(f"  [htf] fetch_htf_candles({granularity}) failed: {e}")
    interval = "15m" if granularity == "M15" else "5m"
    df = fetch_ohlcv(symbol, period="60d", interval=interval)
    if df is None or len(df) < 50:
        raise RuntimeError(f"{granularity} fetch failed for {symbol}")
    return df


# ─── HTF feature spec ────────────────────────────────────────────────
@dataclass
class HtfFeatureSpec:
    """Declarative spec for which HTF features to populate per-bar.

    Each field name corresponds to a column produced by
    `compute_m15_features()` / `compute_m5_features()` below. Strategy
    consumers look these up via ctx.htf['m15'][field].

    The `include_*` toggles both compute the optional column AND auto-add
    the resulting field name(s) to the corresponding fields list. This
    keeps the spec single-source-of-truth: turn on a feature, the runner
    will both compute it and forward it into the per-bar dict.
    """
    m15_fields: list[str] = field(default_factory=lambda: [
        "close", "adx", "ema9", "ema21", "ema50", "rsi14", "atr", "ema_slope",
    ])
    m5_fields: list[str] = field(default_factory=lambda: [
        "close", "high", "low",
        "prev_close", "prev_high", "prev_low",
        "sma21", "atr", "bbpb", "rsi14",
        "stoch_k", "stoch_d", "ema9", "ema21",
        "swing_high", "swing_low",
    ])
    # Optional: include RSI divergence flags on M5 (lookback in M5 bars)
    include_rsi_divergence_m5: bool = False
    rsi_divergence_lookback: int = 30
    # Optional: include Hurst / range_20 on M15 (used by regime cascade)
    include_hurst_m15: bool = False
    include_range_20_m15: bool = False
    # Optional: load + forward-fill H1 features (used by macro-gated strategies)
    include_h1: bool = False
    h1_fields: list[str] = field(default_factory=lambda: [
        "close", "ema9", "ema21", "ema50", "ema200", "adx", "rsi14",
    ])

    # ── Level 3 production-parity toggles (2026-04-30, rule:R1-bypass) ──
    # All default False so existing runners reproduce bit-identical results.
    # Each toggle injects a piece of compute_scalp_signal's per-bar context
    # so that strategies referencing ctx.sr_levels / ctx.layer{0,2,3} /
    # ctx.regime / ctx.session / ctx.htf['agreement'] etc. behave the same
    # under harness BT as under production run_scalp_backtest.

    # Tier A: SR levels (find_sr_levels_weighted on 1m, recalc'd periodically)
    inject_sr_levels: bool = False
    sr_recalc_interval: int = 100      # mirrors SR_RECALC=100 in app.py:5416
    sr_lookback_bars: int = 300         # mirrors df.iloc[max(0, ci-300):ci]
    sr_max_levels: int = 8
    sr_min_touches: int = 2

    # Tier A: Master HTF bias (1H+4H agreement / score)
    inject_master_bias: bool = False
    htf_recalc_interval: int = 60       # mirrors _BT_HTF_RECALC_SCALP=60
    htf_mode: str = "scalp"             # "scalp" (1H+4H) or "daytrade" (4H+1D)

    # Tier B: Layer scores (Layer 0/2/3 — Layer 1 comes from inject_master_bias)
    # NOTE: Layer 0 (is_trade_prohibited), Layer 2 (compute_layer2_score),
    # Layer 3 (compute_layer3_score) are evaluated per-bar against the same
    # 1m window the strategy sees. Lazy-imported from app.py.
    inject_layer_scores: bool = False

    # Tier B: Market regime (4-class TREND_BULL/BEAR/RANGE/HIGH_VOL)
    inject_regime: bool = False

    # Tier C: Bar-time-aware session info (Tokyo/London/NY/etc with mult)
    inject_session: bool = False

    # Tier C: Apply production score / Wilson / BEV gate post-evaluation.
    # When enabled, candidates that fail the per-strategy R2-A suppress gate
    # (apply_r2a_suppress_gate in modules.strategy_category) are dropped.
    apply_score_gate: bool = False

    # Tier C: Round-trip spread cost subtracted from pnl_pips (2026-04-30).
    # Default 0.0 maintains bit-identical backward compatibility. Set to a
    # positive value (e.g. 0.8 for USD_JPY scalp) to bake friction into the
    # win/loss simulation. Used by ma_generic_family_v1 BT for production
    # parity vs the optimistic High/Low touch model.
    inject_spread: float = 0.0

    def __post_init__(self) -> None:
        """Auto-extend field lists based on `include_*` toggles.

        Fixes a footgun where include_rsi_divergence_m5=True would compute
        the columns but the runner wouldn't forward them into the m5_dict
        because they weren't listed in m5_fields. Now turning the toggle
        on does both.
        """
        if self.include_rsi_divergence_m5:
            for fn in ("rsi_div_bear", "rsi_div_bull"):
                if fn not in self.m5_fields:
                    self.m5_fields.append(fn)
        if self.include_hurst_m15:
            if "hurst_64" not in self.m15_fields:
                self.m15_fields.append("hurst_64")
        if self.include_range_20_m15:
            if "range_20" not in self.m15_fields:
                self.m15_fields.append("range_20")


# ─── Vectorized RSI divergence (per-bar bool flags) ─────────────────
def compute_rsi_divergence_flags(df: pd.DataFrame, lookback: int = 30
                                 ) -> tuple[np.ndarray, np.ndarray]:
    """Per-bar bullish/bearish RSI divergence flags.

    Mirrors modules.indicators.detect_divergence() logic, vectorized over
    the full series. Compares price swing-high/low across two halves of a
    `lookback`-bar trailing window vs RSI swing-high/low.

    Returns (bear, bull) — numpy bool arrays of length len(df).
    """
    n = len(df)
    bear = np.zeros(n, dtype=bool)
    bull = np.zeros(n, dtype=bool)
    if n < lookback or "rsi" not in df.columns:
        return bear, bull
    H = df["High"].values
    L = df["Low"].values
    rsi = df["rsi"].fillna(50.0).values
    mid = lookback // 2
    for i in range(lookback, n):
        sub_H = H[i - lookback: i]
        sub_L = L[i - lookback: i]
        sub_R = rsi[i - lookback: i]
        ph_idx = int(np.argmax(sub_H[mid:])) + mid
        pl_idx = int(np.argmin(sub_L[mid:])) + mid
        ph_prev = int(np.argmax(sub_H[:mid]))
        pl_prev = int(np.argmin(sub_L[:mid]))
        if sub_H[ph_idx] > sub_H[ph_prev] and sub_R[ph_idx] < sub_R[ph_prev]:
            bear[i] = True
        if sub_L[pl_idx] < sub_L[pl_prev] and sub_R[pl_idx] > sub_R[pl_prev]:
            bull[i] = True
    return bear, bull


# ─── HTF feature precomputation ─────────────────────────────────────
def compute_m15_features(df_15: pd.DataFrame, spec: HtfFeatureSpec
                         ) -> pd.DataFrame:
    """M15 indicators + custom features per bar."""
    from modules.indicators import add_indicators
    df = add_indicators(df_15.copy())
    out = pd.DataFrame(index=df.index)
    out["close"] = df["Close"]
    out["adx"] = df.get("adx", 0.0)
    out["ema9"] = df.get("ema9", 0.0)
    out["ema21"] = df.get("ema21", 0.0)
    out["ema50"] = df.get("ema50", 0.0)
    out["rsi14"] = df.get("rsi", 50.0)
    out["atr"] = df.get("atr", 0.0)
    # 3-bar ema21 difference (ema_slope used by trend_follow + regime_trend)
    out["ema_slope"] = out["ema21"].diff(3).fillna(0.0)
    if spec.include_range_20_m15:
        out["range_20"] = (
            df["High"].rolling(20, min_periods=5).max()
            - df["Low"].rolling(20, min_periods=5).min()
        ).fillna(0.0)
    if spec.include_hurst_m15:
        try:
            from modules.regime_classifier import hurst_rs
        except Exception:
            hurst_rs = None
        closes = df["Close"].values
        hurst_arr = np.full(len(closes), 0.5)
        if hurst_rs is not None:
            for i in range(64, len(closes)):
                try:
                    hurst_arr[i] = hurst_rs(closes[i - 64:i].tolist())
                except Exception:
                    pass
        out["hurst_64"] = hurst_arr
    return out.fillna(0.0)


def compute_h1_features(df_1h: pd.DataFrame, spec: HtfFeatureSpec
                        ) -> pd.DataFrame:
    """H1 indicators per bar — macro trend gate."""
    from modules.indicators import add_indicators
    df = add_indicators(df_1h.copy())
    out = pd.DataFrame(index=df.index)
    out["close"] = df["Close"]
    out["ema9"] = df.get("ema9", 0.0)
    out["ema21"] = df.get("ema21", 0.0)
    out["ema50"] = df.get("ema50", 0.0)
    out["ema200"] = df.get("ema200", 0.0)
    out["adx"] = df.get("adx", 0.0)
    out["rsi14"] = df.get("rsi", 50.0)
    return out.fillna(0.0)


def compute_m5_features(df_5: pd.DataFrame, spec: HtfFeatureSpec
                        ) -> pd.DataFrame:
    """M5 indicators + custom features per bar."""
    from modules.indicators import add_indicators
    df = add_indicators(df_5.copy())
    out = pd.DataFrame(index=df.index)
    out["close"] = df["Close"]
    out["high"] = df["High"]
    out["low"] = df["Low"]
    out["prev_close"] = df["Close"].shift(1)
    out["prev_high"] = df["High"].shift(1)
    out["prev_low"] = df["Low"].shift(1)
    out["sma21"] = df["Close"].rolling(21, min_periods=5).mean()
    out["atr"] = df.get("atr", 0.0)
    out["bbpb"] = df.get("bb_pband", 0.5)
    out["rsi14"] = df.get("rsi", 50.0)
    out["stoch_k"] = df.get("stoch_k", 50.0)
    out["stoch_d"] = df.get("stoch_d", 50.0)
    out["ema9"] = df.get("ema9", 0.0)
    out["ema21"] = df.get("ema21", 0.0)
    out["swing_high"] = df["High"].rolling(20, min_periods=5).max()
    out["swing_low"] = df["Low"].rolling(20, min_periods=5).min()
    if spec.include_rsi_divergence_m5:
        bear, bull = compute_rsi_divergence_flags(
            df, lookback=spec.rsi_divergence_lookback
        )
        out["rsi_div_bear"] = bear
        out["rsi_div_bull"] = bull
    return out.fillna(0.0)


# ─── Production-parity helpers (Level 3) ────────────────────────────
def _compute_htf_bias_for_window(df_past: pd.DataFrame, mode: str = "scalp"
                                 ) -> dict:
    """Bar-locked HTF bias mirror of app.py:_compute_bt_htf_bias.

    Re-implemented here to avoid importing app.py (Flask init, sentry, etc).
    Behavior must stay aligned with app.py:4644-4776 — any change to that
    function should be reflected here. Out-of-sync would re-introduce
    BT/Live divergence (lessons/bt-live-divergence).

    Returns dict compatible with get_htf_bias():
      {score, agreement, label, h1: {...}, h4: {...}}
    """
    from modules.data import resample_df
    from modules.indicators import add_indicators

    if mode == "daytrade":
        configs = [("h4", "4h", 100), ("d1", "1D", 50)]
    else:
        configs = [("1h", "1h", 30), ("4h", "4h", 15)]

    results: dict[str, dict] = {}
    for tf_key, rule, min_bars in configs:
        try:
            df_h = resample_df(df_past, rule)
            if len(df_h) < min_bars:
                results[tf_key] = {"score": 0.0, "label": "BT: データ不足",
                                    "rsi": 50.0}
                continue
            df_h = add_indicators(df_h).dropna(subset=["ema9", "ema21"])
            if len(df_h) < 5:
                results[tf_key] = {"score": 0.0, "label": "BT: 不足",
                                    "rsi": 50.0}
                continue
            row = df_h.iloc[-1]
            c = float(row["Close"])
            e9 = float(row["ema9"])
            e21 = float(row["ema21"])
            e50 = float(row["ema50"]) if pd.notna(row.get("ema50")) else e21
            rsi = float(row.get("rsi", 50))
            ema200 = float(row.get("ema200", e50))

            if c > e9 > e21 > e50:    sc, lbl = 1.0,  "↗↗ 強気"
            elif c > e21 and e9 > e21: sc, lbl = 0.6,  "↗ 強気"
            elif c > e21:              sc, lbl = 0.3,  "↗ 弱強気"
            elif c < e9 < e21 < e50:  sc, lbl = -1.0, "↘↘ 弱気"
            elif c < e21 and e9 < e21: sc, lbl = -0.6, "↘ 弱気"
            elif c < e21:              sc, lbl = -0.3, "↘ 弱弱気"
            else:                      sc, lbl = 0.0,  "↔ 中立"

            if mode == "daytrade":
                if c > ema200: sc = min(1.0, sc + 0.1)
                else:          sc = max(-1.0, sc - 0.1)

            results[tf_key] = {
                "score": sc, "label": lbl,
                "rsi": round(rsi, 1),
                "ema9": round(e9, 3), "ema21": round(e21, 3),
                "ema50": round(e50, 3), "close": round(c, 3),
            }
        except Exception:
            results[tf_key] = {"score": 0.0, "label": "BT: 計算失敗",
                                "rsi": 50.0}

    if mode == "daytrade":
        h4_sc = results.get("h4", {}).get("score", 0.0)
        d1_sc = results.get("d1", {}).get("score", 0.0)
        avg = round(h4_sc * 0.40 + d1_sc * 0.60, 3)
        if   h4_sc > 0.2 and d1_sc > 0.2:  agr, lab = "bull",  "📈 4H+1D 上昇"
        elif h4_sc < -0.2 and d1_sc < -0.2: agr, lab = "bear",  "📉 4H+1D 下降"
        else:                                agr, lab = "mixed", "⚖️ 4H+1D 不一致"
        return {"score": avg, "agreement": agr, "label": lab,
                "h4": results.get("h4", {}), "d1": results.get("d1", {}),
                "h1": results.get("h4", {})}

    h1_sc = results.get("1h", {}).get("score", 0.0)
    h4_sc = results.get("4h", {}).get("score", 0.0)
    avg = round(h1_sc * 0.40 + h4_sc * 0.60, 3)
    if   h1_sc > 0.2 and h4_sc > 0.2:  agr, lab = "bull",  "📈 1H+4H 上昇"
    elif h1_sc < -0.2 and h4_sc < -0.2: agr, lab = "bear",  "📉 1H+4H 下降"
    else:                                agr, lab = "mixed", "⚖️ 1H+4H 不一致"
    return {"score": avg, "agreement": agr, "label": lab,
            "h1": results.get("1h", {}), "h4": results.get("4h", {})}


def _bt_session_info(bar_time) -> dict:
    """Bar-time-aware mirror of app.py:get_session_info()."""
    h = bar_time.hour if hasattr(bar_time, "hour") else 12
    if 13 <= h < 17:
        return {"name": "NY × London", "mult": 1.20, "color": "green",
                "label": "🟢 NY×ロンドン"}
    if 13 <= h < 22:
        return {"name": "New York", "mult": 1.05, "color": "green",
                "label": "🟢 NY"}
    if 7 <= h < 9:
        return {"name": "東京 × London", "mult": 1.00, "color": "yellow",
                "label": "🟡 東京×London"}
    if 8 <= h < 17:
        return {"name": "London", "mult": 1.05, "color": "green",
                "label": "🟢 London"}
    if 0 <= h < 9:
        return {"name": "Tokyo", "mult": 0.90, "color": "yellow",
                "label": "🟡 Tokyo"}
    return {"name": "Off-hours", "mult": 0.65, "color": "red",
            "label": "🔴 閑散"}


# ─── Trade simulation ────────────────────────────────────────────────
def simulate_outcome(df_1m: pd.DataFrame, entry_idx: int, signal: str,
                     entry_px: float, sl: float, tp: float,
                     pip_mult: int, max_bars: int = 240
                     ) -> tuple[str, float, int]:
    """Walk forward in 1m df from entry_idx+1, find first SL or TP touch.

    Returns (outcome, pnl_pips, exit_offset_bars).
    outcome ∈ {"WIN", "LOSS", "EXPIRED"}.

    Note: pip_mult is taken explicitly (not derived from `if signal`, which
    caused a bug in the original _bt_regime_cascade_scalp_vec.py where
    EXPIRED PnL was 100x understated for non-JPY pairs).
    """
    end = min(entry_idx + 1 + max_bars, len(df_1m))
    for j in range(entry_idx + 1, end):
        bar = df_1m.iloc[j]
        h = float(bar["High"])
        l = float(bar["Low"])
        if signal == "BUY":
            if l <= sl:
                return "LOSS", (sl - entry_px) * pip_mult, j - entry_idx
            if h >= tp:
                return "WIN", (tp - entry_px) * pip_mult, j - entry_idx
        else:  # SELL
            if h >= sl:
                return "LOSS", (entry_px - sl) * pip_mult, j - entry_idx
            if l <= tp:
                return "WIN", (entry_px - tp) * pip_mult, j - entry_idx
    last = float(df_1m.iloc[end - 1]["Close"])
    raw = (last - entry_px) if signal == "BUY" else (entry_px - last)
    return "EXPIRED", raw * pip_mult, end - 1 - entry_idx


# ─── Core BT runner ──────────────────────────────────────────────────
@dataclass
class VecBacktestRunner:
    """Vectorized BT runner.

    Takes an `HtfFeatureSpec` and a strategy factory (no-arg callable that
    returns a strategy instance with `.evaluate(ctx)` and `.enabled`).
    """
    spec: HtfFeatureSpec
    strategy_factory: Callable[[], Any]
    burn_in_bars: int = 240
    cooldown_bars: int = 30
    max_hold_bars: int = 240
    window_bars: int = 100   # df window passed to SignalContext.from_df
    _has_h1: bool = field(default=False, init=False, repr=False)

    # Internal caches populated by _build_*_cache helpers when the
    # corresponding inject_* toggle is enabled. Keyed by `i // recalc`.
    _sr_cache: dict = field(default_factory=dict, init=False, repr=False)
    _htf_bias_cache: dict = field(default_factory=dict, init=False, repr=False)
    _layer1_static: dict = field(default_factory=dict, init=False, repr=False)

    def run(self, symbol: str, days: int, verbose: bool = True) -> dict:
        t_load = time.perf_counter()
        df_1m = load_1m(symbol, days, verbose=verbose)
        df_15 = load_htf(symbol, "M15", verbose=verbose)
        df_5 = load_htf(symbol, "M5", verbose=verbose)
        df_1h = None
        if self.spec.include_h1:
            df_1h = _load_local_cache(symbol, "1h", days=0)
        df_1m.attrs["symbol"] = symbol
        if verbose:
            h1_n = len(df_1h) if df_1h is not None else 0
            print(f"  1m={len(df_1m)} bars  M5={len(df_5)}  M15={len(df_15)} "
                  f" H1={h1_n} (load={time.perf_counter() - t_load:.1f}s)")

        t_feat = time.perf_counter()
        feat_15 = compute_m15_features(df_15, self.spec)
        feat_5 = compute_m5_features(df_5, self.spec)
        feat_1h = compute_h1_features(df_1h, self.spec) if df_1h is not None else None
        if verbose:
            print(f"  HTF features done ({time.perf_counter() - t_feat:.1f}s)")

        from modules.indicators import add_indicators
        df_1m = add_indicators(df_1m)

        # merge_asof: forward-fill latest M15/M5 onto each 1m bar
        feat_15_re = feat_15.reset_index().rename(
            columns={feat_15.index.name or "index": "ts"}
        )
        feat_5_re = feat_5.reset_index().rename(
            columns={feat_5.index.name or "index": "ts"}
        )
        df_1m_re = df_1m.reset_index().rename(
            columns={df_1m.index.name or "index": "ts"}
        )
        for d in (df_1m_re, feat_15_re, feat_5_re):
            d["ts"] = pd.to_datetime(d["ts"])
            d.sort_values("ts", inplace=True)
        merged = pd.merge_asof(
            df_1m_re,
            feat_15_re.add_prefix("m15_").rename(columns={"m15_ts": "ts"}),
            on="ts", direction="backward",
        )
        merged = pd.merge_asof(
            merged,
            feat_5_re.add_prefix("m5_").rename(columns={"m5_ts": "ts"}),
            on="ts", direction="backward",
        )
        if feat_1h is not None:
            feat_1h_re = feat_1h.reset_index().rename(
                columns={feat_1h.index.name or "index": "ts"}
            )
            feat_1h_re["ts"] = pd.to_datetime(feat_1h_re["ts"])
            feat_1h_re.sort_values("ts", inplace=True)
            merged = pd.merge_asof(
                merged,
                feat_1h_re.add_prefix("h1_").rename(columns={"h1_ts": "ts"}),
                on="ts", direction="backward",
            )
        merged = merged.set_index("ts")
        self._has_h1 = feat_1h is not None

        strat = self.strategy_factory()
        if not getattr(strat, "enabled", True):
            return {
                "symbol": symbol,
                "days": days,
                "n_evaluated": 0,
                "n_trades": 0,
                "note": "strategy.enabled=False (skip)",
            }

        is_jpy_or_xau = ("JPY" in symbol) or ("XAU" in symbol)
        pip_mult = 100 if is_jpy_or_xau else 10000

        from strategies.context import SignalContext

        # ── Level 3 caches (built once, looked up per-bar) ────────────
        if self.spec.inject_sr_levels:
            t_sr = time.perf_counter()
            self._sr_cache = self._build_sr_cache(df_1m)
            if verbose:
                print(f"  SR cache: {len(self._sr_cache)} snapshots "
                      f"({time.perf_counter() - t_sr:.1f}s)")
        if self.spec.inject_master_bias:
            t_htf = time.perf_counter()
            self._htf_bias_cache = self._build_htf_bias_cache(df_1m)
            if verbose:
                print(f"  HTF bias cache: {len(self._htf_bias_cache)} snapshots "
                      f"({time.perf_counter() - t_htf:.1f}s)")
            self._layer1_static = self._fetch_layer1_static(symbol)

        trades = []
        last_exit_idx = -self.cooldown_bars
        n_eval = 0

        t_eval = time.perf_counter()
        for i in range(self.burn_in_bars, len(merged) - 60):
            if i <= last_exit_idx + self.cooldown_bars:
                continue
            n_eval += 1
            row = merged.iloc[i]

            m15_dict = {k: self._coerce(row.get(f"m15_{k}"), k)
                        for k in self.spec.m15_fields}
            m5_dict = {k: self._coerce(row.get(f"m5_{k}"), k)
                       for k in self.spec.m5_fields}
            h1_dict = (
                {k: self._coerce(row.get(f"h1_{k}"), k)
                 for k in self.spec.h1_fields}
                if self._has_h1 else {}
            )

            try:
                window = df_1m.iloc[max(0, i - self.window_bars): i + 1]
                bar_time = window.index[-1]

                # ── ctx.htf: features for mtf_*, optionally + bias keys ──
                htf_payload: dict[str, Any] = {
                    "m15": m15_dict, "m5": m5_dict,
                    "h1": h1_dict, "h4": {},
                }
                if self.spec.inject_master_bias and self._htf_bias_cache:
                    bias = self._htf_bias_cache.get(
                        i // self.spec.htf_recalc_interval, {}
                    )
                    # Merge bias keys (agreement/score/label) without
                    # overwriting feature dicts when we have H1 features
                    # (mtf strategies need ema21/ema50; bias h1 has same).
                    htf_payload.setdefault("h1", bias.get("h1", {}))
                    if not h1_dict:
                        htf_payload["h1"] = bias.get("h1", {})
                    htf_payload["h4"] = bias.get("h4", {})
                    htf_payload["agreement"] = bias.get("agreement", "mixed")
                    htf_payload["score"] = bias.get("score", 0.0)
                    htf_payload["label"] = bias.get("label", "")

                # ── ctx.sr_levels ─────────────────────────────────────
                sr_levels: list = []
                if self.spec.inject_sr_levels and self._sr_cache:
                    sr_levels = self._sr_cache.get(
                        i // self.spec.sr_recalc_interval, []
                    )

                # ── Layer 0/2/3, regime, session (lazy-imported helpers) ──
                layer0 = self._compute_layer0(window, bar_time) \
                    if self.spec.inject_layer_scores else {}
                layer2 = self._compute_layer2(window) \
                    if self.spec.inject_layer_scores else {}
                layer3 = self._compute_layer3(window, sr_levels) \
                    if self.spec.inject_layer_scores else {}
                regime = self._compute_regime(window) \
                    if self.spec.inject_regime else {}
                session = _bt_session_info(bar_time) \
                    if self.spec.inject_session else {}

                ctx = SignalContext.from_df(
                    df=window, row=window.iloc[-1], symbol=symbol, tf="1m",
                    sr_levels=sr_levels,
                    layer0=layer0, layer1=self._layer1_static,
                    regime=regime, layer2=layer2, layer3=layer3,
                    htf=htf_payload, session=session,
                    backtest_mode=True,
                    bar_time=bar_time,
                )
            except Exception:
                continue

            try:
                cand = strat.evaluate(ctx)
            except Exception:
                continue
            if cand is None:
                continue

            # ── Tier C: optional production score gate ────────────────
            if self.spec.apply_score_gate and cand is not None:
                try:
                    cand = self._apply_score_gate(cand, ctx, symbol, bar_time)
                except Exception:
                    pass
                if cand is None:
                    continue

            outcome, pnl_pips, exit_off = simulate_outcome(
                df_1m=df_1m, entry_idx=i, signal=cand.signal,
                entry_px=ctx.entry, sl=cand.sl, tp=cand.tp,
                pip_mult=pip_mult, max_bars=self.max_hold_bars,
            )
            # Round-trip spread cost (rule:R3 friction, 2026-04-30).
            if self.spec.inject_spread > 0:
                pnl_pips -= self.spec.inject_spread
            trades.append({
                "ts": str(window.index[-1]),
                "signal": cand.signal,
                "entry_px": ctx.entry,
                "sl": cand.sl,
                "tp": cand.tp,
                "outcome": outcome,
                "pnl_pips": pnl_pips,
                "exit_bars": exit_off,
                "confidence": getattr(cand, "confidence", None),
                "score": getattr(cand, "score", None),
            })
            last_exit_idx = i + exit_off

        eval_secs = time.perf_counter() - t_eval
        return self._stats(symbol, days, trades, n_eval, eval_secs)

    @staticmethod
    def _coerce(value: Any, field_name: str):
        """Best-effort scalar coercion for HTF-injected fields.

        bool fields (rsi_div_*) → bool, others → float with fallback.
        """
        if field_name.startswith("rsi_div_"):
            return bool(value) if value is not None else False
        try:
            v = float(value) if value is not None else 0.0
            if math.isnan(v):
                # Sensible defaults for known indicators
                if field_name == "rsi14":
                    return 50.0
                if field_name == "bbpb":
                    return 0.5
                if field_name in ("stoch_k", "stoch_d"):
                    return 50.0
                if field_name == "hurst_64":
                    return 0.5
                return 0.0
            return v
        except (TypeError, ValueError):
            return 0.0

    # ── Level 3 cache builders ───────────────────────────────────────
    def _build_sr_cache(self, df_1m: pd.DataFrame) -> dict:
        """Pre-compute SR levels every `sr_recalc_interval` bars.

        Mirror of app.py:5416-5423. Returns dict keyed by bar_idx//recalc.
        Stored values are lists of float prices (compute_layer3_score
        accepts both float-list and dict-list, but production passes
        float prices).
        """
        from modules.indicators import find_sr_levels_weighted
        cache: dict[int, list[float]] = {}
        recalc = self.spec.sr_recalc_interval
        lookback = self.spec.sr_lookback_bars
        for ci in range(2 * recalc, len(df_1m), recalc):
            sl = df_1m.iloc[max(0, ci - lookback):ci]
            try:
                levels = find_sr_levels_weighted(
                    sl, window=5, tolerance_pct=0.003,
                    min_touches=self.spec.sr_min_touches,
                    max_levels=self.spec.sr_max_levels,
                    bars_per_day=288,
                )
                cache[ci // recalc] = [lv["price"] for lv in levels]
            except Exception:
                cache[ci // recalc] = []
        return cache

    def _build_htf_bias_cache(self, df_1m: pd.DataFrame) -> dict:
        """Pre-compute HTF bias every `htf_recalc_interval` bars.

        Mirrors app.py:_compute_bt_htf_bias (5454-5457 recalc loop).
        """
        cache: dict[int, dict] = {}
        recalc = self.spec.htf_recalc_interval
        n = len(df_1m)
        for bar_idx in range(0, n, recalc):
            df_past = df_1m.iloc[:bar_idx + 1]
            if len(df_past) < 60:
                cache[bar_idx // recalc] = {
                    "score": 0, "agreement": "neutral", "label": "BT: 不足",
                    "h1": {"score": 0.0, "rsi": 50.0},
                    "h4": {"score": 0.0, "rsi": 50.0},
                }
                continue
            cache[bar_idx // recalc] = _compute_htf_bias_for_window(
                df_past, mode=self.spec.htf_mode
            )
        return cache

    @staticmethod
    def _fetch_layer1_static(symbol: str) -> dict:
        """One-shot get_master_bias call (Layer 1 institutional flow).

        Mirrors app.py:5403-5408. master_bias depends on global market
        state (DXY/VIX/COT) so it's effectively static over a BT window;
        a single fetch matches production behavior of caching for
        MASTER_BIAS_TTL.
        """
        try:
            from app import get_master_bias
            return get_master_bias(symbol)
        except Exception:
            return {"direction": "neutral", "label": "—", "score": 0}

    # ── Per-bar layer score helpers (lazy-import from app) ──────────
    @staticmethod
    def _compute_layer0(window: pd.DataFrame, bar_time) -> dict:
        try:
            from app import is_trade_prohibited
            return is_trade_prohibited(window, bar_time=bar_time)
        except Exception:
            return {"prohibited": False, "reason": "", "layer": 0}

    @staticmethod
    def _compute_layer2(window: pd.DataFrame) -> dict:
        try:
            from app import compute_layer2_score
            return compute_layer2_score(window, "1m")
        except Exception:
            return {"score": 0.0, "label": "—", "components": {}}

    @staticmethod
    def _compute_layer3(window: pd.DataFrame, sr_levels: list) -> dict:
        try:
            from app import compute_layer3_score
            return compute_layer3_score(window, "1m", sr_levels)
        except Exception:
            return {"score": 0.0, "label": "—", "components": {}}

    @staticmethod
    def _compute_regime(window: pd.DataFrame) -> dict:
        try:
            from app import detect_market_regime
            return detect_market_regime(window)
        except Exception:
            return {"regime": "UNKNOWN", "label": "—"}

    @staticmethod
    def _apply_score_gate(cand: Any, ctx: Any, symbol: str, bar_time) -> Any:
        """Apply production R2-A suppress gate post-evaluation.

        Mirrors app.py:_make_result U20 gate (8324-8352). Only applies
        when entry_type + session + spread_q are computable; fail-open
        on any error (returns cand unchanged) — matches production
        fail-open behavior.
        """
        sig = getattr(cand, "signal", None)
        entry_type = getattr(cand, "entry_type", None)
        if sig not in ("BUY", "SELL") or not entry_type or entry_type == "wait":
            return cand
        try:
            from modules.strategy_category import (
                apply_r2a_suppress_gate, compute_spread_quartile,
            )
            from app import _bt_spread
            pip_unit = 0.01 if "JPY" in symbol.upper() else 0.0001
            spread_pips = _bt_spread(bar_time, symbol) / pip_unit
            spread_q = compute_spread_quartile(spread_pips, symbol)
            sess = ctx.session.get("name") if ctx.session else None
            conf = float(getattr(cand, "confidence", 0) or 0)
            new_conf = apply_r2a_suppress_gate(
                entry_type, sess, spread_q, conf
            )
            if new_conf <= 0:
                return None
            try:
                cand.confidence = new_conf
            except AttributeError:
                pass
            return cand
        except Exception:
            return cand

    @staticmethod
    def _stats(symbol: str, days: int, trades: list[dict],
               n_eval: int, eval_secs: float) -> dict:
        n = len(trades)
        wins = [t for t in trades if t["outcome"] == "WIN"]
        losses = [t for t in trades if t["outcome"] == "LOSS"]
        expired = [t for t in trades if t["outcome"] == "EXPIRED"]
        n_w = len(wins)
        wr = n_w / n if n > 0 else 0.0
        pnls = [t["pnl_pips"] for t in trades]
        ev = sum(pnls) / n if n > 0 else 0.0
        pf = profit_factor_local(pnls)
        wlow = wilson_lower(n_w, n)
        avg_win = (sum(t["pnl_pips"] for t in wins) / len(wins)) if wins else 0.0
        avg_loss = (sum(t["pnl_pips"] for t in losses) / len(losses)) if losses else 0.0
        kelly = kelly_pct(wr, avg_win, avg_loss)
        return {
            "symbol": symbol,
            "days": days,
            "n_evaluated": n_eval,
            "n_trades": n,
            "n_wins": n_w,
            "n_losses": len(losses),
            "n_expired": len(expired),
            "wr_pct": round(wr * 100, 2),
            "wilson_lower_pct": round(wlow, 2),
            "ev_pips": round(ev, 3),
            "pf": round(pf, 3) if pf != float("inf") else "inf",
            "kelly_pct": round(kelly, 3),
            "avg_win_pips": round(avg_win, 3),
            "avg_loss_pips": round(avg_loss, 3),
            "eval_secs": round(eval_secs, 2),
            "trades_sample": trades[:10],
            # Full trade list — added 2026-04-30 for ma_family_validation.
            # Backward-compatible: existing callers use trades_sample.
            "trades_full": trades,
        }
