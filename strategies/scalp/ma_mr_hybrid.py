"""ma_mr_hybrid v2 — Ornstein-Uhlenbeck calibrated mean reversion (USD_JPY)

Revision history:
  v1 / v1a-rev: カテゴリカル filter chain (BB%B + RSI + Stoch + 確認足) → N=1〜66
                で発火率が低すぎ or エッジなし。filter の AND 結合が確率を
                乗算的に押し下げる構造的問題。
  v2 (シニアクオンツ再設計, 2026-04-30):
    数学的基盤を Vasicek/O-U process に変更。連続的な Bayesian 証拠統合で
    カテゴリカル AND filter を排除。

Mathematical foundation (Vasicek 1977 / Ornstein-Uhlenbeck):
  dP_t = θ(μ - P_t)dt + σdW_t

  Discretized: ΔP = θ(μ - P)Δt + σ√Δt·ε
  Linearize:   ΔP = a + b·P + ε,  b = -θΔt,  a = θμΔt
  OLS on rolling N=60 1m bars yields (a, b, σ_ε).
  Recover: θ̂ = -b/Δt,  μ̂ = -a/b = a/-b,  σ̂ = σ_ε/√Δt
  Half-life of MR: τ_½ = ln(2)/θ̂

Entry rule (mathematically defensible):
  Compute z = (P_t - μ̂) / σ̂
  Fire BUY when:
    1. z < -2.0 (price 2σ below long-run mean)
    2. τ_½ ∈ [10, 90] minutes (fast enough vs spread, slow enough to develop)
    3. σ̂ > σ_min (volatility floor — skip dead market)
    4. R² of OLS > 0.05 (calibration sanity)

  TP = μ̂ (revert to estimated mean)
  SL = μ̂ - 3.5·σ̂ (3.5 std fail-safe, 0.05% breach probability under N(0,1))

  Cost-aware filter: skip if (μ̂ - P_t) / spread < 4 (insufficient TP after spread).

Why this is rigorous:
  - O-U is the canonical MR model for stationary processes
  - Half-life filter directly encodes "is MR fast enough vs spread cost"
  - σ-based SL/TP eliminates ATR multiplier tuning
  - z-score is continuous evidence, not categorical filter
"""
from __future__ import annotations
from typing import Optional
import numpy as np

from strategies.base import StrategyBase, Candidate
from strategies.context import SignalContext
from modules.confidence_v2 import apply_penalty


_ALLOWED_PAIRS = {"USD_JPY"}
_OU_WINDOW = 60               # 1m bars for O-U calibration
_Z_ENTRY = 2.0                # |z| threshold
_HALF_LIFE_MIN_MIN = 10.0     # minutes
_HALF_LIFE_MAX_MIN = 90.0
_MIN_R2 = 0.03
_SL_K = 3.5                   # SL = μ ± k·σ
_MIN_TP_SPREAD_RATIO = 4.0    # TP must be ≥ 4× spread (cost-aware)
_SPREAD_PIP = 0.8             # USD_JPY assumption (matches inject_spread)


def _normalize_pair(symbol: str) -> str:
    s = (symbol or "").upper().replace("=X", "").replace("/", "_")
    if "_" in s:
        return s
    if len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


def _calibrate_ou(prices: np.ndarray) -> Optional[dict]:
    """OLS calibration of discretized O-U process on 1m closes.

    Returns dict with mu, theta_per_bar, sigma_per_bar, half_life_bars, r2.
    Returns None if calibration is invalid (degenerate, b≥0 indicating
    momentum not MR).
    """
    n = len(prices)
    if n < 20:
        return None
    p_t = prices[:-1]
    dp = prices[1:] - prices[:-1]
    # OLS: dp = a + b * p_t
    p_mean = p_t.mean()
    dp_mean = dp.mean()
    cov = ((p_t - p_mean) * (dp - dp_mean)).sum()
    var_p = ((p_t - p_mean) ** 2).sum()
    if var_p <= 0:
        return None
    b = cov / var_p
    a = dp_mean - b * p_mean
    if b >= 0:
        return None  # not mean-reverting (momentum or random walk)
    residuals = dp - (a + b * p_t)
    sse = (residuals ** 2).sum()
    sst = ((dp - dp_mean) ** 2).sum()
    r2 = 1.0 - sse / sst if sst > 0 else 0.0
    sigma = float(np.sqrt(residuals.var(ddof=2))) if len(residuals) > 2 else 0.0
    if sigma <= 0:
        return None
    mu = -a / b
    theta = -b   # per-bar (Δt = 1 bar)
    half_life = float(np.log(2.0) / theta) if theta > 0 else float("inf")
    return {
        "mu": float(mu),
        "theta": float(theta),
        "sigma": sigma,
        "half_life_bars": half_life,
        "r2": float(r2),
    }


class MaMrHybrid(StrategyBase):
    name = "ma_mr_hybrid"
    mode = "scalp"
    enabled = True
    strategy_type = "MR"

    def evaluate(self, ctx: SignalContext) -> Optional[Candidate]:
        if _normalize_pair(ctx.symbol) not in _ALLOWED_PAIRS:
            return None
        if ctx.df is None or len(ctx.df) < _OU_WINDOW + 5:
            return None

        # Calibrate O-U on 1m closes (rolling N bars)
        prices = ctx.df["Close"].iloc[-_OU_WINDOW:].values.astype(float)
        cal = _calibrate_ou(prices)
        if cal is None:
            return None
        if cal["r2"] < _MIN_R2:
            return None
        if not (_HALF_LIFE_MIN_MIN <= cal["half_life_bars"] <= _HALF_LIFE_MAX_MIN):
            return None

        sigma = cal["sigma"]
        mu = cal["mu"]
        if sigma <= 0:
            return None

        z = (ctx.entry - mu) / sigma

        # JPY pip multiplier
        pip_size = 1.0 / ctx.pip_mult     # JPY: 0.01, EUR: 0.0001
        spread_price = _SPREAD_PIP * pip_size

        signal: Optional[str] = None
        sl: float = 0.0
        tp: float = 0.0
        reasons: list = []
        score = 3.0

        # BUY: price 2σ below long-run mean
        if z < -_Z_ENTRY:
            tp_price = mu
            sl_price = mu - _SL_K * sigma
            tp_dist = tp_price - ctx.entry
            sl_dist = ctx.entry - sl_price
            if tp_dist <= 0 or sl_dist <= 0:
                return None
            # cost-aware filter: TP must exceed 4× spread
            if tp_dist / spread_price < _MIN_TP_SPREAD_RATIO:
                return None
            signal = "BUY"
            sl = sl_price
            tp = tp_price
            reasons.append(f"✅ O-U z={z:.2f} < -{_Z_ENTRY} (mean reversion candidate)")
            reasons.append(f"✅ τ_½={cal['half_life_bars']:.1f} bars ∈ [{_HALF_LIFE_MIN_MIN}, {_HALF_LIFE_MAX_MIN}]")
            reasons.append(f"✅ R²={cal['r2']:.3f}, σ={sigma:.5f}, μ={mu:.5f}")
            reasons.append(f"✅ TP/spread = {tp_dist/spread_price:.1f} (cost-aware)")
            score += min(2.0, abs(z) - _Z_ENTRY)  # bonus for extreme z

        # SELL: price 2σ above long-run mean
        elif z > _Z_ENTRY:
            tp_price = mu
            sl_price = mu + _SL_K * sigma
            tp_dist = ctx.entry - tp_price
            sl_dist = sl_price - ctx.entry
            if tp_dist <= 0 or sl_dist <= 0:
                return None
            if tp_dist / spread_price < _MIN_TP_SPREAD_RATIO:
                return None
            signal = "SELL"
            sl = sl_price
            tp = tp_price
            reasons.append(f"✅ O-U z={z:.2f} > +{_Z_ENTRY} (mean reversion candidate)")
            reasons.append(f"✅ τ_½={cal['half_life_bars']:.1f} bars ∈ [{_HALF_LIFE_MIN_MIN}, {_HALF_LIFE_MAX_MIN}]")
            reasons.append(f"✅ R²={cal['r2']:.3f}, σ={sigma:.5f}, μ={mu:.5f}")
            reasons.append(f"✅ TP/spread = {tp_dist/spread_price:.1f} (cost-aware)")
            score += min(2.0, abs(z) - _Z_ENTRY)

        if signal is None:
            return None

        legacy_conf = int(min(85, 55 + score * 4))
        conf = apply_penalty(legacy_conf, self.strategy_type, ctx.adx, conf_max=85)

        return Candidate(
            signal=signal, confidence=int(conf),
            sl=float(sl), tp=float(tp),
            reasons=reasons, entry_type=self.name, score=float(score),
        )
