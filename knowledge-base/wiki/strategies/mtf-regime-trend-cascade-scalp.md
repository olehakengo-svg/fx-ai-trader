# mtf_regime_trend_cascade_scalp

## Status: v2.1 (2026-04-30) — Shadow 蓄積中 / Rule 1 BT は N≥50 達成待ち

データ駆動 regime gate を持つ別軸 cascade scalp 戦略。走行中 `mtf_trend_follow_scalp` との差別化 3 軸:

1. **spread_gate を最上位に昇格** (`hour_mult ≤ 0.85` + 4 重ハードゲート)
2. **既存 `ema_pullback` の 1m bounce トリガーを継承 (L3 slim 化済)**
3. **15m regime classifier v2.1: `moderate_trend` (binary) のみ発火**
   — ADX 18-25 + |slope|>0 + **Hurst 0.75-0.95** (実測 R/S 分布に合わせた閾値)

### v2 → v2.1 変更点 (2026-04-30, rule:R3)
- **L3 ema_order 削除**: 15m slope_dir が方向確定済みのため冗長 (32件ブロックしていた)
- **L3 ema9_touch 削除**: 5m pullback が近接確認済みのため冗長 (17件ブロックしていた)
- **SL floor修正**: `max(atr7×0.3, 5pip)` — EUR_USD で sl_dist < spread になるバグ修正
- **Hurst閾値キャリブレーション**: [0.65,0.85] → [0.75,0.95]
  — 実測 R/S 分布 (USD_JPY L0通過バー N=475): P5=0.858, P25=0.905, P50=0.932
  — 旧設定は実測分布の完全下方に外れており N≈0 を引き起こしていた (理論値との混同)

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

## vec BT 実績 (v2.1, 180d, ローカル Massive キャッシュ 2025-10-14〜2026-04-15)

| ペア | N | WR% | Wilson_lo | EV(p) | PF | Kelly% | Rule 1 判定 |
|---|---|---|---|---|---|---|---|
| USD_JPY | 13 | 46.2% | 23.2% | +5.6 | 2.99 | 30.7% | N不足 (目標≥50) |
| EUR_USD | 26 | 61.5% | 42.5% | +2.7 | 2.36 | 35.5% | N不足 (目標≥50) |

**現状**: N不足で Rule 1 判定不可。EUR_USD は WR/PF が強い正のedge を示す。  
**次アクション**: Shadow で live データ蓄積 → N≥50 到達時に再評価。

### N が低い原因分析
- L0 spread gate が 84.6% をブロック (有効時間: 12-15 UTC / 20-21 UTC = 6h/day)
- L1 Hurst[0.75,0.95] + ADX[18,25] 同時通過率 37.9%
- L3 4条件 (bounce/bullish-bar/MACD-H/Stoch) がさらにフィルタリング

### 失敗時継続検証 (closure 短絡禁止)
1. **ADX band 感度**: 18-25 → {16-27, 18-30}
2. **Hurst band 感度**: 0.75-0.95 → {0.70-0.97}
3. **hour_mult 緩和**: ≤0.85 → ≤0.90 (9-11 UTC を追加)
4. **L3 Stoch/MACD-H 片方削除** (N vs Quality トレードオフ検証)
5. **1m trigger 差替え**: ema_pullback → stoch_trend_pullback

## Files
- `strategies/scalp/mtf_regime_trend_cascade_scalp.py` (v2.1)
- `modules/spread_gate.py`
- `modules/regime_classifier.py` (v2.1: Hurst 閾値修正)
- `modules/htf_data_source.py:_compute_m15_features` 拡張 (range_20 / hurst_64 / atr15)
- `_bt_regime_cascade_scalp_vec.py` (vectorized BT runner with local cache)

## BT 履歴
- `raw/bt-results/regime_cascade_scalp_vec_20260430_121212.json` — 180d USD_JPY+EUR_USD v2.1
