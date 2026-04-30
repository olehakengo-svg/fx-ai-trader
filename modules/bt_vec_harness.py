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
    suffix_map = {"1m": "1m", "5m": "5m", "15m": "15m", "M5": "5m", "M15": "15m"}
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

    def run(self, symbol: str, days: int, verbose: bool = True) -> dict:
        t_load = time.perf_counter()
        df_1m = load_1m(symbol, days, verbose=verbose)
        df_15 = load_htf(symbol, "M15", verbose=verbose)
        df_5 = load_htf(symbol, "M5", verbose=verbose)
        df_1m.attrs["symbol"] = symbol
        if verbose:
            print(f"  1m={len(df_1m)} bars  M5={len(df_5)}  M15={len(df_15)} "
                  f"(load={time.perf_counter() - t_load:.1f}s)")

        t_feat = time.perf_counter()
        feat_15 = compute_m15_features(df_15, self.spec)
        feat_5 = compute_m5_features(df_5, self.spec)
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
        merged = merged.set_index("ts")

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

            try:
                window = df_1m.iloc[max(0, i - self.window_bars): i + 1]
                ctx = SignalContext.from_df(
                    df=window, row=window.iloc[-1], symbol=symbol, tf="1m",
                    sr_levels=[],
                    layer0={}, layer1={}, regime={}, layer2={}, layer3={},
                    htf={"m15": m15_dict, "m5": m5_dict, "h1": {}, "h4": {}},
                    session={},
                    backtest_mode=True,
                    bar_time=window.index[-1],
                )
            except Exception:
                continue

            try:
                cand = strat.evaluate(ctx)
            except Exception:
                continue
            if cand is None:
                continue

            outcome, pnl_pips, exit_off = simulate_outcome(
                df_1m=df_1m, entry_idx=i, signal=cand.signal,
                entry_px=ctx.entry, sl=cand.sl, tp=cand.tp,
                pip_mult=pip_mult, max_bars=self.max_hold_bars,
            )
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
        }
