# mtf_trend_follow_scalp

## Status: NEW (2026-04-29) — Pre-reg LOCK pending Rule 1 BT

新規追加戦略。教科書的 MTF (Multi-TimeFrame) 階層 15m→5m→1m を厳密に
踏む scalp 順張り戦略。既存 22 個の scalp 戦略は 1m 単独評価のため、
3 段カスケードで誤シグナルを削減して WR を上げることを狙う。

## 設計仕様

### 通貨ペアガード (低スプレッド限定)
- 許可: `USD_JPY`, `EUR_USD` のみ (friction_model_v2 で 0.7pip 最低)
- それ以外は即 `return None`

### 時間帯ガード (動的、低スプレッド時間帯のみ)
- `friction_model_v2.hour_mult_for(hour_utc) <= 0.95` で発火許可
- 該当時間帯 (UTC): 3-7 (Tokyo full), 9-15 (London + overlap), 16, 20-21
- それ以外 (Sydney 22-0, NY late 17-19) は発火しない
- CLAUDE.md 4 原則「静的時間ブロック禁止」との両立: 動的に friction 計算

### M15 トレンドゲート (hard)
- `m15.adx >= 22` (明確なトレンド)
- `m15.ema9 > m15.ema21` (uptrend) / `<` (downtrend)
- `m15.ema_slope` (3-bar EMA21 差) の符号がトレンド方向と一致

### M5 プルバック確認 (hard)
- 直前 5m bar が `m5.sma21 ± atr5×0.3` にタッチ
- 当 5m bar が直前 close を上抜け (BUY) / 下抜け (SELL) ＝ bounce-back
- `m5.bbpb` が 0.20-0.65 (BUY) / 0.35-0.80 (SELL) ＝ 過熱でない中間帯

### M1 micro pivot break + 確認 (hard, 全要求)
- `ctx.entry > max(直前3本 1m High)` (BUY) — micro pivot break
- `ctx.macdh > 0 AND macdh > macdh_prev` — MACD-H 上昇
- `ctx.stoch_k > stoch_d AND stoch_k < 75` — Stoch GC 未過熱
- `ctx.entry > ctx.open_price` — 陽線確認

### SL/TP
- SL = `min(直前3本 1m Low) - 1pip` (BUY) — micro structure tight
- TP = `max(m5.swing_high, entry + SL_dist × 1.3)` (RR floor 1.3)
- TP - entry < `ATR7 × 1.0` なら弱すぎ → reject

### Confidence
- base = 60
- +10 if `m15.adx >= 28` (strong trend)
- +5 if `hour_mult <= 0.85` (London-NY overlap peak)
- +5 if `|m15.ema_slope| > 0.5 × ATR5/pip_mult`
- `apply_penalty(conf, "trend", ctx.adx, conf_max=85)`

### Score
`score = m15.adx × 0.4 + conf × 0.06 + bonus`

## 検証要件 (Rule 1, CLAUDE.md)

### 1. 365 日 BT
- ツール: 既存 BT engine + 新規 `_bt_mtf_cascade_scalp.py` 必要
- 対象: USD_JPY + EUR_USD, scalp mode
- 合格: WR ≥ 52%, PF ≥ 1.20, Wilson 95%下限 ≥ 50%, N ≥ 50/戦略

### 2. Bonferroni 補正
- cell: 戦略 × ペア × セッション (2 × 2 × 3 = 12 cell)
- α = 0.05/12 = 0.0042 で WR > BEV を有意検出する cell ≥ 1

### 3. Pre-reg LOCK 14 日
- shadow only deploy
- N ≥ 15 / strata 達成後に KPI 評価

## 既存戦略との違い (whitespace 分析)

| 既存戦略 | 不足部分 |
|---|---|
| ema_pullback / ema_trend_scalp / stoch_pullback | 1m only、M15 trend pre-validation なし |
| mtf_confluence | H1/H4 のみ、M15→M5→M1 cascade ではない |
| trend_rebound | ADX 高 + 反発で逆張り、順張り pullback ではない |

**新規性**: M15 trend slope + M5 SMA21 bounce + M1 micro pivot break の
3 段カスケード + 動的低スプレッド時間ガード。

## Files
- `strategies/scalp/mtf_trend_follow_scalp.py`
- `modules/htf_data_source.py:compute_mtf_features` (新規 helper)
- `modules/friction_model_v2.py:hour_mult_for` (新規 getter)
- `app.py:get_htf_bias` (m15/m5 キー populate)
- 登録: `strategies/scalp/__init__.py`

## Related
- [[friction-analysis]]
- [[claude-harness-design]]
- [[lesson-asymmetric-agility-2026-04-25]] (Rule 1 適用)
