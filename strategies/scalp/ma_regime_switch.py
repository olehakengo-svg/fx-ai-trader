"""ma_regime_switch v2 — Hurst exponent × ATR percentile 2D regime classifier

Revision history:
  v1: H1 EMA50 lazy approx → 機構不全 (N=22)
  v1c-rev: ATR/bb_width percentile 単一軸 → 機構正常化 (N=397) も方向情報なし
  v2 (シニアクオンツ再設計):
    Hurst exponent (R/S analysis) を方向 (persistence / anti-persistence) 情報
    として加え、ATR percentile (vol level) と直交する 2D classifier を構築。

Mathematical foundation (Mandelbrot 1972, Lo 1991):
  Hurst exponent H ∈ (0, 1):
    H > 0.5: persistent / trending (long-memory positive autocorrelation)
    H = 0.5: random walk (Brownian motion baseline)
    H < 0.5: anti-persistent / mean-reverting

  R/S analysis on N bars:
    Y_t = cumulative deviation = Σ_{i=1}^{t} (P_i - mean(P))
    R = max(Y_t) - min(Y_t)
    S = sample std of P
    R/S(N) ∝ N^H

  Multi-window log-log regression: log(R/S) vs log(N) → slope = H

2D regime classifier:
  Bivariate (Hurst H, ATR percentile τ):

    H > 0.55 ∧ τ ≥ 0.60  →  STRONG_TREND   (high vol + persistence)
                              → fire v1b clone (M15 perfect order)
    H < 0.45 ∧ τ ≤ 0.40  →  STRONG_MR      (low vol + anti-persistence)
                              → fire O-U calibrated MR (v1a v2 clone)
    else                  →  AMBIGUOUS     → no fire (信号 → ノイズ排除)

  Both axes are independent statistical measures:
    - Hurst captures temporal autocorrelation structure
    - ATR percentile captures volatility magnitude
  Combined → orthogonal 4-quadrant regime grid.

References:
  - Mandelbrot, B. (1972). "Statistical methodology for non-periodic cycles"
  - Lo, A. W. (1991). "Long-term memory in stock market prices" Econometrica
  - Hurst, H. E. (1951). "Long-term storage capacity of reservoirs"

Why this is rigorous:
  - Hurst is principled long-memory measure, robust to price level
  - 2D classifier eliminates the "vol level alone is uninformative" failure of v1c-rev
  - "AMBIGUOUS → skip" enforces statistical Type I error control
"""
from __future__ import annotations
from typing import Optional
import math
import numpy as np

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty


_ALLOWED_PAIRS = {"USD_JPY"}
_HURST_WINDOW = 64
_HURST_TREND_MIN = 0.55
_HURST_MR_MAX = 0.45
_ATR_PCT_HIGH = 0.60
_ATR_PCT_LOW = 0.40

# O-U params (mirror ma_mr_hybrid v2 for MR sub-strategy)
_OU_WINDOW = 60
_Z_ENTRY = 2.0
_HALF_LIFE_MIN = 10.0
_HALF_LIFE_MAX = 90.0
_MIN_R2 = 0.03
_SL_K = 3.5
_MIN_TP_SPREAD_RATIO = 4.0
_SPREAD_PIP = 0.8


def _normalize_pair(symbol: str) -> str:
    s = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


def _hurst_rs(prices: np.ndarray) -> Optional[float]:
    """R/S analysis Hurst exponent on a price series.

    Uses sub-window sizes [8, 16, 32, len/1] for log-log regression.
    Returns Hurst H or None on degenerate data.
    """
    n = len(prices)
    if n < 16:
        return None
    log_returns = np.diff(np.log(prices))
    if len(log_returns) < 16:
        return None

    sizes = [s for s in (8, 16, 32, len(log_returns)) if s <= len(log_returns)]
    if len(sizes) < 2:
        return None

    rs_values = []
    for s in sizes:
        # Split into chunks of size s
        n_chunks = len(log_returns) // s
        if n_chunks < 1:
            continue
        rs_chunks = []
        for i in range(n_chunks):
            chunk = log_returns[i * s:(i + 1) * s]
            mean = chunk.mean()
            cum = (chunk - mean).cumsum()
            R = cum.max() - cum.min()
            S = chunk.std(ddof=1)
            if S > 0 and R > 0:
                rs_chunks.append(R / S)
        if rs_chunks:
            rs_values.append((s, float(np.mean(rs_chunks))))

    if len(rs_values) < 2:
        return None

    log_n = np.array([math.log(s) for s, _ in rs_values])
    log_rs = np.array([math.log(rs) for _, rs in rs_values])
    cov = ((log_n - log_n.mean()) * (log_rs - log_rs.mean())).sum()
    var = ((log_n - log_n.mean()) ** 2).sum()
    if var <= 0:
        return None
    H = float(cov / var)
    return max(0.0, min(1.0, H))


def _atr_percentile(df, atr_col: str = "atr", window: int = 50) -> float:
    """Current ATR's percentile rank within the last `window` bars."""
    if atr_col not in df.columns or len(df) < window:
        return 0.5
    series = df[atr_col].iloc[-window:]
    cur = float(series.iloc[-1])
    if not math.isfinite(cur):
        return 0.5
    rank = float((series < cur).sum()) / len(series)
    return rank


def _calibrate_ou(prices: np.ndarray) -> Optional[dict]:
    n = len(prices)
    if n < 20:
        return None
    p_t = prices[:-1]
    dp = prices[1:] - prices[:-1]
    p_mean = p_t.mean()
    dp_mean = dp.mean()
    cov = ((p_t - p_mean) * (dp - dp_mean)).sum()
    var_p = ((p_t - p_mean) ** 2).sum()
    if var_p <= 0:
        return None
    b = cov / var_p
    a = dp_mean - b * p_mean
    if b >= 0:
        return None
    residuals = dp - (a + b * p_t)
    sst = ((dp - dp_mean) ** 2).sum()
    sse = (residuals ** 2).sum()
    r2 = 1.0 - sse / sst if sst > 0 else 0.0
    sigma = float(np.sqrt(residuals.var(ddof=2))) if len(residuals) > 2 else 0.0
    if sigma <= 0:
        return None
    mu = -a / b
    theta = -b
    half_life = float(math.log(2.0) / theta) if theta > 0 else float("inf")
    return {"mu": float(mu), "theta": float(theta), "sigma": sigma,
            "half_life_bars": half_life, "r2": float(r2)}


class MaRegimeSwitch(StrategyBase):
    name = "ma_regime_switch"
    mode = "scalp"
    enabled = True
    strategy_type = "trend"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if _normalize_pair(ctx.symbol) not in _ALLOWED_PAIRS:
            return None
        if ctx.df is None or len(ctx.df) < max(_HURST_WINDOW, _OU_WINDOW) + 10:
            return None

        # Compute Hurst on last 64 bars (1m closes)
        prices = ctx.df["Close"].iloc[-_HURST_WINDOW:].values.astype(float)
        H = _hurst_rs(prices)
        if H is None:
            return None

        # ATR percentile on last 50 1m bars
        atr_pct = _atr_percentile(ctx.df, "atr", 50)

        signal: Optional[str] = None
        sl: float = 0.0
        tp: float = 0.0
        reasons: list = []
        score = 3.0
        regime = "AMBIGUOUS"
        st = self.strategy_type

        # ───── STRONG_TREND quadrant: H>0.55, τ≥0.60 → trend follow ─────
        if H > _HURST_TREND_MIN and atr_pct >= _ATR_PCT_HIGH:
            regime = "STRONG_TREND"
            st = "trend"
            # Use M15 perfect order if available
            m15 = ctx.htf.get("m15") if isinstance(ctx.htf, dict) else None
            if not m15:
                return None
            m15_ema9 = float(m15.get("ema9", 0))
            m15_ema21 = float(m15.get("ema21", 0))
            m15_ema50 = float(m15.get("ema50", 0))
            m15_adx = float(m15.get("adx", 0))
            m15_slope = float(m15.get("ema_slope", 0))
            if m15_adx < 22.0:
                return None
            perfect_bull = m15_ema9 > m15_ema21 > m15_ema50 and m15_slope > 0
            perfect_bear = m15_ema9 < m15_ema21 < m15_ema50 and m15_slope < 0
            sl_dist = ctx.atr7 * 1.0
            tp_dist = ctx.atr7 * 1.6
            if perfect_bull and ctx.entry > ctx.open_price and ctx.macdh > ctx.macdh_prev:
                signal = "BUY"
                sl = ctx.entry - sl_dist
                tp = ctx.entry + tp_dist
                reasons.append(f"📊 Regime=STRONG_TREND (H={H:.3f}>{_HURST_TREND_MIN}, ATR_pct={atr_pct:.2f})")
                reasons.append(f"✅ M15 perfect order BUY ADX={m15_adx:.1f}")
            elif perfect_bear and ctx.entry < ctx.open_price and ctx.macdh < ctx.macdh_prev:
                signal = "SELL"
                sl = ctx.entry + sl_dist
                tp = ctx.entry - tp_dist
                reasons.append(f"📊 Regime=STRONG_TREND (H={H:.3f}>{_HURST_TREND_MIN}, ATR_pct={atr_pct:.2f})")
                reasons.append(f"✅ M15 perfect order SELL ADX={m15_adx:.1f}")

        # ───── STRONG_MR quadrant: H<0.45, τ≤0.40 → O-U calibrated MR ─────
        elif H < _HURST_MR_MAX and atr_pct <= _ATR_PCT_LOW:
            regime = "STRONG_MR"
            st = "MR"
            cal = _calibrate_ou(ctx.df["Close"].iloc[-_OU_WINDOW:].values.astype(float))
            if cal is None or cal["r2"] < _MIN_R2:
                return None
            if not (_HALF_LIFE_MIN <= cal["half_life_bars"] <= _HALF_LIFE_MAX):
                return None
            sigma = cal["sigma"]; mu = cal["mu"]
            if sigma <= 0:
                return None
            z = (ctx.entry - mu) / sigma
            pip_size = 1.0 / ctx.pip_mult
            spread_price = _SPREAD_PIP * pip_size

            if z < -_Z_ENTRY:
                tp_price = mu
                sl_price = mu - _SL_K * sigma
                tp_dist = tp_price - ctx.entry
                if tp_dist <= 0 or tp_dist / spread_price < _MIN_TP_SPREAD_RATIO:
                    return None
                signal = "BUY"
                sl = sl_price; tp = tp_price
                reasons.append(f"📊 Regime=STRONG_MR (H={H:.3f}<{_HURST_MR_MAX}, ATR_pct={atr_pct:.2f})")
                reasons.append(f"✅ O-U z={z:.2f} τ_½={cal['half_life_bars']:.1f}b R²={cal['r2']:.3f}")
            elif z > _Z_ENTRY:
                tp_price = mu
                sl_price = mu + _SL_K * sigma
                tp_dist = ctx.entry - tp_price
                if tp_dist <= 0 or tp_dist / spread_price < _MIN_TP_SPREAD_RATIO:
                    return None
                signal = "SELL"
                sl = sl_price; tp = tp_price
                reasons.append(f"📊 Regime=STRONG_MR (H={H:.3f}<{_HURST_MR_MAX}, ATR_pct={atr_pct:.2f})")
                reasons.append(f"✅ O-U z={z:.2f} τ_½={cal['half_life_bars']:.1f}b R²={cal['r2']:.3f}")

        # AMBIGUOUS quadrant → skip (Type I error control)
        else:
            return None

        if signal is None:
            return None

        legacy_conf = int(min(85, 55 + score * 4))
        conf = apply_penalty(legacy_conf, st, ctx.adx, conf_max=85)

        return Candidate(
            signal=signal, confidence=int(conf),
            sl=float(sl), tp=float(tp),
            reasons=reasons, entry_type=self.name, score=float(score),
        )
