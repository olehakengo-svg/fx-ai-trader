# mtf_regime_trend_cascade_scalp

## Status: REDESIGNED v2 (2026-04-30) — Pre-reg LOCK pending Rule 1 BT

データ駆動 regime gate を持つ別軸 cascade scalp 戦略。走行中 `mtf_trend_follow_scalp` との差別化 3 軸:

1. **spread_gate を最上位に昇格** (`hour_mult ≤ 0.85` + 4 重ハードゲート)
2. **既存 `ema_pullback` の 1m bounce トリガーを継承再利用**
3. **15m regime classifier v2: `moderate_trend` (binary) のみ発火**
   — ADX 18-25 + |slope|>0 + Hurst 0.40-0.55 (実測 trend_up_weak 相当)

## v1 → v2 の経緯 (重要)

**v1 (2026-04-29 廃案)**: regime ∈ {trend_up, trend_down} で発火。  
**v2 (2026-04-30, 現行)**: demo_trades.db (N=462) ラベル実測クエリで仮説否定:

| 戦略 × 旧 regime | N | WR% | Wilson_lo |
|---|---|---|---|
| ema_trend_scalp × **trend_up_strong** | 30 | **16.7%** | 7.34% |
| ema_trend_scalp × **trend_up_weak** | 12 | **41.7%** | 19.33% |
| ema_trend_scalp × range_tight | 23 | 26.1% | 12.55% |
| bb_rsi_reversion × range_tight | 8 | 12.5% | 2.24% |
| dt_bb_rsi_mr × **trend_up_weak** | 8 | **62.5%** | 30.57% |

**結論**: 「strong trend で TF が勝つ / range で MR が勝つ」教科書仮説は実測で否定。**唯一勝ちうる cell は trend_up_weak (中庸 ADX + 緩やか slope)**. binary `{moderate_trend, no_go}` に簡素化。

## 設計仕様

### Layer 0: Spread/Friction Hard Gate
[`modules/spread_gate.py:should_block`](../../../modules/spread_gate.py)
- `hour_mult > 0.85` → block (走行 BT の 0.95 より厳しい)
- `spread_pips > 1.2` (静的) AND `adjusted_rt_pips > 2.5` (動的) → block
- 直近15m volume が baseline の 40% 未満 → block (stale market)
- `ATR / adjusted_rt_pips < 3.0` → block (動く幅 vs 摩擦)

### Layer 1: 15m Moderate-Trend Gate (data-driven)
[`modules/regime_classifier.py:classify_15m`](../../../modules/regime_classifier.py)
- `regime == moderate_trend` のみ発火
- ルール: `18 ≤ ADX ≤ 25` AND `|EMA slope| > 0` AND `0.40 ≤ Hurst ≤ 0.55`
- BUY/SELL は `slope_direction(m15)` (ema_slope 符号) で決定

### Layer 2: M5 direction confirmation
- `m5.prev_low ≤ m5.sma21 + atr × 0.3` (BUY) / `m5.prev_high ≥ sma21 - atr × 0.3` (SELL)
- `m5.close > m5.prev_close` (BUY) — bounce 確認

### Layer 3: M1 trigger (ema_pullback v8.3 継承)
- `ema9 > ema21 AND entry ≥ ema21` (BUY) — EMA 順列
- `prev_low ≤ ema9 AND prev_low ≥ ema21 - atr7×0.3` — EMA9 タッチ
- `(entry - ema21) ≥ atr7 × 0.2` — bounce 強度確認 (ema_pullback v8.3 継承)
- `entry > prev_close AND entry > open_price` — 陽線 + 反転
- `macdh > 0 AND macdh > macdh_prev` — MACD-H 上昇
- `stoch_k > stoch_d AND stoch_k < 75` — Stoch GC 未過熱

### SL/TP
- SL = `ema21 - atr7 × 0.3`
- TP = `max(m5.swing_high, entry + SL_dist × 1.3)`
- TP - entry < `ATR7 × 1.0` なら reject

### Confidence (v2 score)
- base = 60
- +10 if `21 ≤ m15.adx ≤ 24` (moderate band center, 実測スイートスポット)
- +5 if `hour_mult ≤ 0.80`
- +5 if `|m15.ema_slope| > 0.5 × atr15/pip_mult`
- `apply_penalty(conf, "trend", ctx.adx, conf_max=85)`
- score = `3.0 + min((m15.adx - 18) × 0.10, 0.7) + bonus × 0.3`

## 検証要件 (Rule 1, CLAUDE.md)

### 1. 365 日 BT
- 対象: USD_JPY + EUR_USD, scalp mode
- 合格: WR ≥ 52%, PF ≥ 1.20, Wilson 95% lower ≥ 50%, N ≥ 50/cell, Kelly > 0

### 2. Bonferroni 補正
- cell = 戦略 1 × ペア 2 × セッション 3 = **6 cell** (regime は単一 moderate_trend)
- α = 0.05/6 = 0.00833

### 3. Walk-Forward
- 365 日を 学習 240d / 評価 60d で 3 分割、評価期間 Wilson_lo ≥ 48% を 3/3

### 4. Pre-reg LOCK 14 日
- shadow only deploy
- N ≥ 15/strata で KPI 評価

## 失敗時継続検証 (closure 短絡禁止)

1. ADX band 感度: 18-25 → {16-22, 20-28, 18-30}
2. Hurst band 感度: 0.40-0.55 → {0.35-0.60, 0.45-0.55}
3. 1m trigger 差替え: ema_pullback → stoch_trend_pullback / engulfing_bb 派生
4. spread_gate 緩和: hour_mult ≤ 0.85 → 0.90

## Files
- `strategies/scalp/mtf_regime_trend_cascade_scalp.py`
- `modules/spread_gate.py`
- `modules/regime_classifier.py` (v2)
- `modules/htf_data_source.py:_compute_m15_features` 拡張 (range_20 / hurst_64 / atr15)

## Pre-reg
365 日 BT 結果は `raw/bt-results/regime_cascade_scalp_{TS}.json` に保存予定。
