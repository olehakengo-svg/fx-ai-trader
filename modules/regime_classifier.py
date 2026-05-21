"""15m Regime Classifier — DATA-DRIVEN binary gate (rule:R1)

設計の歴史 (重要):
  v1 (2026-04-29 廃案):
    {trend_up, trend_down, range, choppy} の 4 ラベル。
    range_tight で MR が勝つ / strong trend で TF が勝つ という教科書仮説。

  v2 (2026-04-30, 現行):
    demo_trades.db (N=462) のラベル実測クエリで v1 仮説が**否定方向**:
    - bb_rsi_reversion × range_tight: N=8 WR=12.5% (MR が range で最低)
    - ema_trend_scalp × trend_up_strong: N=30 WR=16.7% (trend が strong で最低)
    - ema_trend_scalp × trend_up_weak: N=12 WR=41.7% (中間が最高)
    - dt_bb_rsi_mr × trend_up_weak: N=8 WR=62.5% (中間が最高)

    → **「moderate trend (中庸 ADX + 緩やか slope)」が唯一勝ちうる regime**.
    binary 分類 {moderate_trend, no_go} に簡素化。

実測根拠 (KB 参照):
  knowledge-base/wiki/decisions/regime-cascade-empirical-redesign-2026-04-30.md (作成予定)
  demo_trades.db query: SELECT entry_type, mtf_regime, COUNT(*), WR%
  Wilson_lo は全 cell <40% で BEV floor 未達だが、「方向性は明確」.
"""
from __future__ import annotations
from typing import Optional, Iterable, Literal
import math

import pandas as pd


# ─── Regime labels (v2: binary) ──────────────────────────────────────
REGIME_MODERATE_TREND = "moderate_trend"   # ADX 18-25 + 緩やか slope + Hurst 0.40-0.55
REGIME_NO_GO = "no_go"                      # 上記以外は全て発火させない

# Backwards-compat aliases (古いコードが import しても壊れないように)
REGIME_TREND_UP = REGIME_MODERATE_TREND     # 旧 trend_up は moderate_trend に吸収
REGIME_TREND_DOWN = REGIME_MODERATE_TREND
REGIME_RANGE = REGIME_NO_GO                 # 旧 range は実測 NO-GO
REGIME_CHOPPY = REGIME_NO_GO

# ─── Thresholds (data-driven, BT で感度分析) ─────────────────────────
# trend_up_weak (= moderate trend) の demo_trades 実測ラベル定義に倣う
ADX_MODERATE_MIN = 18.0
ADX_MODERATE_MAX = 25.0     # ≥25 (trend_up_strong) は実測で WR drop
# Hurst R/S 64-bar の実測分布 (USD_JPY 90d 1m→M15 実測 2026-04-30, rule:R3 calibration):
#   L0通過バー(12-15/20-21 UTC)でHurst>0.5のサンプルN=475:
#   P5=0.858  P25=0.905  P50=0.932  P75=0.949  P90=0.986
#
#   旧設定 [0.65, 0.85] は実測分布の完全下方に外れており N=0 を引き起こしていた。
#   (理論 H=0.5 のランダムウォーク仮定と実測 R/S 値の混同 = キャリブレーションバグ)
#
#   修正: 実測 P5–P90 (≈ 0.75–0.97) のうち中庸帯 [P5, P75] = [0.858, 0.949] を採用。
#   BT 感度分析対象として [0.75, 0.95] を初期値に設定。
#   (0.95 超は extreme persistent → strong trend / choppy として除外)
HURST_MODERATE_LOW = 0.75
HURST_MODERATE_HIGH = 0.95  # 実測 P75=0.949。極端な strong trend を除外
SLOPE_DIRECTIONAL_THRESHOLD = 0.0  # |slope|>0 で方向性あり


def classify_15m(htf_m15: Optional[dict]) -> str:
    """15m features dict から regime ラベルを返す (v2 binary).

    Returns
    -------
    "moderate_trend" : ADX 18-25 + |slope|>0 + 0.75≤Hurst≤0.95 (R/S 実測分布に合わせた閾値)
    "no_go"          : 上記条件を満たさない全ケース (= 戦略発火させない)

    Notes
    -----
    - v1 の trend_up/down/range/choppy ラベルは統合された.
    - 戦略側で BUY/SELL の方向は ema_slope の符号で決定する (本関数は方向情報を返さない).
    - htf_m15 が None / 不足のときは "no_go" で fail-safe.
    """
    if not htf_m15 or not isinstance(htf_m15, dict):
        return REGIME_NO_GO

    adx = float(htf_m15.get("adx", 0.0) or 0.0)
    slope = float(htf_m15.get("ema_slope", 0.0) or 0.0)
    hurst = float(htf_m15.get("hurst_64", 0.5) or 0.5)

    if (ADX_MODERATE_MIN <= adx <= ADX_MODERATE_MAX
            and abs(slope) > SLOPE_DIRECTIONAL_THRESHOLD
            and HURST_MODERATE_LOW <= hurst <= HURST_MODERATE_HIGH):
        return REGIME_MODERATE_TREND

    return REGIME_NO_GO


def slope_direction(htf_m15: Optional[dict]) -> int:
    """Return +1 (bullish), -1 (bearish), 0 (flat / unknown).

    moderate_trend regime での BUY/SELL 方向決定用ヘルパ.
    """
    if not htf_m15 or not isinstance(htf_m15, dict):
        return 0
    slope = float(htf_m15.get("ema_slope", 0.0) or 0.0)
    if slope > 0:
        return 1
    if slope < 0:
        return -1
    return 0


def slope_direction_macro_gated(
    htf_m15: Optional[dict],
    htf_h1: Optional[dict],
) -> int:
    """Macro-trend-aligned slope direction (rule:R3, 2026-04-30).

    実測根拠 (USD_JPY 60d edge collapse 解析):
      古い 120d (横ばい): PF≈3+ / 直近 60d (+337pip 強上昇): PF=0.35.
      M15 短期 EMA21 3-bar slope は強上昇中でも一時的負転し SELL 発火、
      マクロと逆向きで systematic LOSS となる構造を示した.
      H1 EMA21 vs EMA50 で macro trend を判定し、整合方向のみ通過.

    Logic:
      - H1 EMA21 > EMA50  → bullish macro → BUY (M15 slope>0) のみ許可
      - H1 EMA21 < EMA50  → bearish macro → SELL (M15 slope<0) のみ許可
      - H1 不明 / 中立 → fallback to slope_direction(htf_m15)

    Returns +1 / -1 / 0.
    """
    base_dir = slope_direction(htf_m15)
    if base_dir == 0:
        return 0
    if not htf_h1 or not isinstance(htf_h1, dict):
        return base_dir   # fallback
    h1_ema21 = float(htf_h1.get("ema21", 0.0) or 0.0)
    h1_ema50 = float(htf_h1.get("ema50", 0.0) or 0.0)
    if h1_ema21 <= 0 or h1_ema50 <= 0:
        return base_dir
    h1_bull = h1_ema21 > h1_ema50
    h1_bear = h1_ema21 < h1_ema50
    if h1_bull and base_dir > 0:
        return +1
    if h1_bear and base_dir < 0:
        return -1
    return 0  # macro と M15 slope が不一致 → no_go


# ─── Hurst exponent (R/S method) ────────────────────────────────────
# 64 バーで R/S 解析. moderate_trend 判定の安定性を上げるため計算する.
def hurst_rs(series: Iterable[float], min_window: int = 8) -> float:
    """Rescaled-range (R/S) Hurst exponent estimator.

    Returns 0.5 (random walk) when series is too short or computation fails.
    H > 0.55 → persistent (実測 NO-GO: trending too much)
    H < 0.40 → mean-reverting (実測 NO-GO: too noisy)
    H ≈ 0.40-0.55 → moderate persistence (moderate_trend 候補)
    """
    try:
        ys = [float(x) for x in series if x == x]  # drop NaN
    except Exception:
        return 0.5
    n = len(ys)
    if n < max(min_window * 2, 16):
        return 0.5

    windows = []
    w = min_window
    while w <= n // 2:
        windows.append(w)
        w *= 2
    if not windows:
        return 0.5

    log_w = []
    log_rs = []
    for window in windows:
        rs_vals = []
        for start in range(0, n - window + 1, window):
            seg = ys[start:start + window]
            mean = sum(seg) / window
            cum = 0.0
            cum_min = 0.0
            cum_max = 0.0
            for i, v in enumerate(seg):
                cum += v - mean
                if i == 0:
                    cum_min = cum_max = cum
                else:
                    if cum < cum_min:
                        cum_min = cum
                    if cum > cum_max:
                        cum_max = cum
            rng = cum_max - cum_min
            var = sum((v - mean) ** 2 for v in seg) / window
            std = math.sqrt(var) if var > 0 else 0.0
            if std > 0:
                rs_vals.append(rng / std)
        if rs_vals:
            mean_rs = sum(rs_vals) / len(rs_vals)
            if mean_rs > 0:
                log_w.append(math.log(window))
                log_rs.append(math.log(mean_rs))

    if len(log_w) < 2:
        return 0.5
    n_pts = len(log_w)
    sx = sum(log_w)
    sy = sum(log_rs)
    sxx = sum(x * x for x in log_w)
    sxy = sum(x * y for x, y in zip(log_w, log_rs))
    denom = n_pts * sxx - sx * sx
    if denom == 0:
        return 0.5
    h = (n_pts * sxy - sx * sy) / denom
    if h != h or h < 0 or h > 1:
        return 0.5
    return float(h)


# ─── Perfect Order EMA Regime (2026-05-21) ──────────────────────────
# Kalman D7 trend forensic (2026-05-20) で USDJPY M15 用に発見した
# Perfect Order(EMA fast>mid>slow + close strict) を共有モジュール化。
# v2 binary classify_15m (上記) と直交する 3-state UP/DN/RANGE 分類。
#
# Memory:
#   - project_kalman_d7_regime_bound_live_2026_05_20
RegimeType = Literal["UP", "DN", "RANGE"]

REGIME_UP = "UP"
REGIME_DN = "DN"
REGIME_PO_RANGE = "RANGE"


def _resolve_close(df: pd.DataFrame) -> Optional[pd.Series]:
    if df is None:
        return None
    if "close" in df.columns:
        return df["close"]
    if "Close" in df.columns:
        return df["Close"]
    return None


def classify_regime(df: pd.DataFrame, fast: int = 25, mid: int = 75, slow: int = 200,
                    strict_close: bool = True) -> RegimeType:
    """Perfect Order EMA regime classifier.

    Returns
    -------
    "UP"    : EMA fast > mid > slow (and close > EMA fast when strict_close)
    "DN"    : EMA slow > mid > fast (Perfect Order Down)
    "RANGE" : neither / insufficient data

    Parameters
    ----------
    df : DataFrame with 'close' or 'Close' column.
    fast, mid, slow : EMA spans (default 25/75/200).
    strict_close : when True, require last_close > EMA fast for UP.
    """
    if df is None or len(df) < slow + 10:
        return REGIME_PO_RANGE
    s = _resolve_close(df)
    if s is None or len(s) < slow + 10:
        return REGIME_PO_RANGE

    ema_f = s.ewm(span=fast, adjust=False).mean().iloc[-1]
    ema_m = s.ewm(span=mid, adjust=False).mean().iloc[-1]
    ema_s = s.ewm(span=slow, adjust=False).mean().iloc[-1]
    last_close = float(s.iloc[-1])

    if ema_f > ema_m > ema_s:
        if not strict_close or last_close > ema_f:
            return REGIME_UP
    if ema_s > ema_m > ema_f:
        return REGIME_DN
    return REGIME_PO_RANGE


def is_regime_start(df: pd.DataFrame, target: RegimeType,
                    fast: int = 25, mid: int = 75, slow: int = 200,
                    strict_close: bool = True) -> bool:
    """Detect transition into ``target`` regime at the current bar.

    Returns True iff:
      - regime(df) == target
      - regime(df[:-1]) != target
    """
    if df is None or len(df) < slow + 11:
        return False
    now = classify_regime(df, fast, mid, slow, strict_close)
    if now != target:
        return False
    prev = classify_regime(df.iloc[:-1], fast, mid, slow, strict_close)
    return prev != target
