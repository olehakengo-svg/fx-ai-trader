"""
FX AI Trader — Configuration constants
=======================================
Timeframe settings, strategy profiles, directional biases,
agent mission, MTF hierarchy, and cache TTL values.
"""

import os

# ═══════════════════════════════════════════════════════
#  Timeframe config
# ═══════════════════════════════════════════════════════
TF_CFG = {
    "1m":  dict(interval="1m",  period="5d",   resample=None,  sr_w=10, sr_tol=0.0020, ch_lb=200),
    "5m":  dict(interval="5m",  period="25d",  resample=None,  sr_w=10, sr_tol=0.0020, ch_lb=150),
    "15m": dict(interval="15m", period="55d",  resample=None,  sr_w=8,  sr_tol=0.0025, ch_lb=120),
    "30m": dict(interval="30m", period="55d",  resample=None,  sr_w=6,  sr_tol=0.0030, ch_lb=100),
    "1h":  dict(interval="1h",  period="55d",  resample=None,  sr_w=5,  sr_tol=0.0030, ch_lb=80),
    "4h":  dict(interval="1h",  period="90d",  resample="4h",  sr_w=4,  sr_tol=0.0050, ch_lb=60),
    "1d":  dict(interval="1d",  period="2y",   resample=None,  sr_w=5,  sr_tol=0.0060, ch_lb=50),
    "1w":  dict(interval="1wk", period="10y",  resample=None,  sr_w=3,  sr_tol=0.0100, ch_lb=30),
    "1M":  dict(interval="1mo", period="max",  resample=None,  sr_w=2,  sr_tol=0.0150, ch_lb=20),
}

# ═══════════════════════════════════════════════════════
#  Strategy Mode: "A" (Trend Following) or "B" (Mean Reversion)
# ═══════════════════════════════════════════════════════
STRATEGY_MODE = os.environ.get("STRATEGY_MODE", "A")

STRATEGY_PROFILES = {
    "A": {
        "name": "Trend Following",
        "scalp_sl": 0.75, "scalp_tp": 1.8,    # 1:2.4 RR for scalp (BE=29.4%)
        "daytrade_sl": 0.7, "daytrade_tp": 1.5,  # 1:2.14 RR for daytrade (BE=31.8%)
        "kpi_wr": 0.30, "kpi_ev": 0.08, "kpi_sharpe": 1.0, "kpi_maxdd": 0.15,
        "breakeven_wr": 0.294,  # for 1:2.4 RR -> SL/(SL+TP)=0.75/2.55
        "random_baseline_wr": 0.28,
        "trades_per_day_min": 1, "trades_per_day_max": 50,
    },
    "B": {
        "name": "Mean Reversion",
        "scalp_sl": 1.0, "scalp_tp": 1.0,    # 1:1 RR for scalp
        "daytrade_sl": 1.0, "daytrade_tp": 1.2,  # keep
        "kpi_wr": 0.55, "kpi_ev": 0.05, "kpi_sharpe": 0.8, "kpi_maxdd": 0.15,
        "breakeven_wr": 0.50,
        "random_baseline_wr": 0.45,
        "trades_per_day_min": 1, "trades_per_day_max": 50,
    },
}

# ═══════════════════════════════════════════════════════
#  Per-strategy profile-mode classification
#  Used by promotion-gate (modules.demo_trader._evaluate_promotions)
#  to look up KPI thresholds (kpi_wr / kpi_ev) per strategy.
#  Strategies absent from this map fall back to the legacy hardcoded
#  promotion thresholds (back-compat).
# ═══════════════════════════════════════════════════════
STRATEGY_PROFILE_MODE_A = frozenset({
    # Scalp-class strategies — Mode A (Trend Following, low-WR/high-RR)
    "bb_rsi_reversion", "macdh_reversal", "stoch_trend_pullback",
    "bb_squeeze_breakout", "london_breakout", "tokyo_bb",
    "mtf_reversal_confluence", "fib_reversal", "ema_pullback",
    "session_vol_expansion", "vol_momentum_scalp", "ema_ribbon_ride",
    "gold_pips_hunter", "london_shrapnel", "vol_surge_detector",
    "confluence_scalp", "v_reversal", "trend_rebound",
    "sr_channel_reversal", "engulfing_bb", "three_bar_reversal",
    "ema_trend_scalp",
})

STRATEGY_PROFILE_MODE_B = frozenset({
    # Daytrade-class strategies — Mode B (Mean Reversion, high-WR/low-RR)
    "sr_fib_confluence", "ema_cross", "htf_false_breakout",
    "london_session_breakout", "tokyo_nakane_momentum",
    "adx_trend_continuation", "sr_break_retest", "lin_reg_channel",
    "orb_trap", "london_close_reversal", "london_close_reversal_v2",
    "gbp_deep_pullback", "turtle_soup", "trendline_sweep",
    "inducement_ob", "dual_sr_bounce", "london_ny_swing",
    "jpy_basket_trend", "gold_vol_break", "gold_trend_momentum",
    "liquidity_sweep", "session_time_bias", "gotobi_fix",
    "london_fix_reversal", "vix_carry_unwind", "xs_momentum",
    "hmm_regime_filter", "vol_spike_mr", "doji_breakout",
    "ny_close_reversal", "streak_reversal", "vwap_mean_reversion",
    "post_news_vol", "dt_fib_reversal", "dt_sr_channel_reversal",
    "ema200_trend_reversal", "squeeze_release_momentum",
    "eurgbp_daily_mr", "dt_bb_rsi_mr", "intraday_seasonality",
    "wick_imbalance_reversion", "atr_regime_break",
    "tokyo_range_breakout_up", "pullback_to_liquidity_v1",
    "asia_range_fade_v1", "sr_anti_hunt_bounce", "sr_liquidity_grab",
    "cpd_divergence", "vdr_jpy", "vsg_jpy_reversal",
    "keltner_squeeze_breakout", "donchian_momentum_breakout",
})


def get_strategy_profile_mode(entry_type: str):
    """Return "A" / "B" for known strategies, or None for unmapped entries.

    None signals the legacy hardcoded promotion thresholds should apply.
    """
    if entry_type in STRATEGY_PROFILE_MODE_A:
        return "A"
    if entry_type in STRATEGY_PROFILE_MODE_B:
        return "B"
    return None

# ═══════════════════════════════════════════════════════
#  時間帯x方向バイアス — Massive API 10,518バー第三者評価結果
#  SL=4pip TP=12pip (1:3 RR) ランダム2,094トレード検証
# ═══════════════════════════════════════════════════════
HOUR_DIRECTION_BIAS = {
    # hour_utc: (best_direction, WR%, edge_vs_random)
    0:  ("SHORT", 31.3, 10.1),
    1:  ("LONG",  26.2,  5.0),
    2:  ("LONG",  24.3,  3.1),
    3:  (None,    18.9, -2.3),   # デッドゾーン — 取引回避
    4:  ("LONG",  29.7,  8.5),
    5:  (None,    25.0,  3.8),   # 方向性なし
    6:  ("SHORT", 27.7,  6.5),
    7:  ("LONG",  25.0,  3.8),
    8:  ("LONG",  31.8, 10.6),   # ロンドンオープン
    9:  ("LONG",  27.7,  6.5),
    10: ("SHORT", 29.1,  7.9),
    11: (None,    20.9, -0.3),   # デッドゾーン
    12: ("LONG",  26.4,  5.2),
    13: ("LONG",  27.7,  6.5),
    14: ("SHORT", 29.5,  8.3),
    15: ("LONG",  27.1,  5.9),
    16: ("SHORT", 24.3,  3.1),
    17: ("LONG",  25.7,  4.5),
    18: ("SHORT", 22.9,  1.7),
    19: ("LONG",  25.7,  4.5),
    20: ("SHORT", 30.6,  9.4),   # NY終盤
    21: ("SHORT", 42.8, 21.6),   # 最強ゾーン
    22: ("SHORT", 31.5, 10.3),
    23: ("SHORT", 22.4,  1.2),
}

# ═══════════════════════════════════════════════════════
#  MISSION — 全エージェント共通ミッション定義
# ═══════════════════════════════════════════════════════
AGENT_MISSION = {
    "goal":     "個人トレーダーが大口（機関投資家）の波に乗れる最強FXシグナルインジケーター構築",
    "strategy": "スキャルピング(5m/15m) + デイトレード(30m/1h) 完全最適化",
    "kpi": {
        "win_rate_min":    30.0,   # 勝率最低ライン (%) ※RR3:1では損益分岐25%
        "ev_min":          0.08,   # 期待値最低ライン (R/trade)
        "sharpe_min":      1.0,
        "max_dd_max":      15.0,
        "scalp_trades":    (1, 50),
        "daytrade_trades": (0.5, 8),
    },
    "principles": [
        "大口フロー整合 = 最優先条件",
        "逆張り原則禁止",
        "重要イベント前後30分は取引停止",
        "シグナル → 通知 → 手動発注（自動発注は対象外）",
    ],
    "layer_hierarchy": {
        0: "取引禁止条件チェック (経済指標/セッション/ボラティリティ)",
        1: "大口バイアス判定 — MASTER FILTER (機関投資家フロー方向)",
        2: "トレンド構造確認 (EMA配列/ダウ理論/S/R位置)",
        3: "精密エントリー条件 (OB接触/フィボ/確認足/出来高)",
    },
}

# ① MTF: higher timeframes to check per current TF
MTF_HIGHER = {
    "1m":  ["15m", "1h", "4h"],
    "5m":  ["1h", "4h", "1d"],
    "15m": ["4h", "1d"],
    "30m": ["4h", "1d"],   # 旧["1h","4h","1d"]: 1Hを除外して1hと揃える
    "1h":  ["4h", "1d"],
    "4h":  ["1d", "1w"],
    "1d":  ["1w"],
    "1w":  ["1M"],
    "1M":  [],
}

# Swing-mode ATR multipliers per timeframe
TF_SL_MULT = {
    "1m": 1.5, "5m": 1.5, "15m": 2.0, "30m": 1.8,
    "1h": 2.2, "4h": 2.5, "1d": 3.0, "1w": 3.5, "1M": 4.0,
}
TF_TP_MULT = {
    "1m": 2.5, "5m": 2.5, "15m": 2.5, "30m": 3.0,
    "1h": 3.3, "4h": 3.8, "1d": 5.0, "1w": 6.0, "1M": 7.0,
}
TF_MIN_RR = {
    "1m": 1.2, "5m": 1.2, "15m": 1.3, "30m": 1.4,
    "1h": 1.5, "4h": 1.6, "1d": 1.8, "1w": 1.8, "1M": 2.0,
}

# ═══════════════════════════════════════════════════════
#  Cache TTL constants
# ═══════════════════════════════════════════════════════
CACHE_TTL    = 300       # 5 min data cache
BT_CACHE_TTL = 21600     # 6 hour backtest cache
NEWS_TTL     = 1800      # 30 min news cache
CALENDAR_TTL    = 3600   # 1時間
MASTER_BIAS_TTL = 900    # 15分
SCALP_BT_TTL = 1800      # 30分キャッシュ（トレンド転換時の再計算を早める）
DT_BT_TTL = 1800         # 30分キャッシュ（トレンド転換時の再計算を早める）
