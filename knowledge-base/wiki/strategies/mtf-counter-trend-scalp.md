# mtf_counter_trend_scalp

## Status: NEW (2026-04-29) — Pre-reg LOCK pending Rule 1 BT

新規追加戦略。教科書的 MTF 階層 15m→5m→1m を厳密に踏む scalp 逆張り戦略。
M15 でトレンドが存在することを確認した上で、M5 で BB%B 過熱 + RSI ダイバージェンス、
M1 で engulfing/pin bar 反転を引き金に短命の exhaustion swing を狙う。

## 設計仕様

### 通貨ペアガード
- 許可: `USD_JPY`, `EUR_USD` のみ

### 時間帯ガード
- `friction_model_v2.hour_mult_for(hour_utc) <= 0.95` のみ発火
- 動的判定 — CLAUDE.md 4 原則 (静的時間ブロック禁止) に準拠

### M15 トレンドゲート (hard, トレンド存在を要求)
- `m15.adx >= 25` (明確なトレンド)
- `m15.ema9 > m15.ema21` ＝ uptrend → 逆張り SELL を狙う
- `m15.ema9 < m15.ema21` ＝ downtrend → 逆張り BUY を狙う

### M5 過熱検出 (hard)
- BB%B: SELL は `m5.bbpb >= 0.92`、BUY は `m5.bbpb <= 0.08`
- RSI ダイバージェンス: 直近 5 本で close 新高値だが RSI 新高値でない (bear div)
  / close 新安値だが RSI 新安値でない (bull div)
- 両方を要求 (strict gate)

### M1 反転トリガ (hard)
- Bearish/Bullish engulfing OR pin bar (上下ヒゲ > range×0.65, 実体 < range×0.30)
- Stoch K cross (SELL: K<D, BUY: K>D)
- 陰線/陽線確認

### SL/TP
- SL = 5m exhaustion wick (high/low) ± 1pip buffer
- SL distance > 12pip なら exhaustion 失敗 → reject
- TP = `min/max(固定 5-6pip, entry ± SL_dist × 1.2)` (RR 1.2 floor)
  - USD_JPY: 6pip / EUR_USD: 5pip 固定小幅

### Confidence
- base = 55 (counter-trend なので低め start)
- +10 if M5 RSI extreme (≥70 SELL / ≤30 BUY)
- +5 if `hour_mult <= 0.85`
- `apply_penalty(conf, "MR", ctx.adx, conf_max=80)`
- 1m ADX > 35 で reject (MR が機能しない strong trend)

### Score
`score = (100 - ctx.adx) × 0.2 + conf × 0.06 + bonus`

## 検証要件 (Rule 1)

### 1. 365 日 BT
- 合格: WR ≥ 52%, PF ≥ 1.15 (counter-trend は順張りより RR 制約厳しい),
  Wilson 95%下限 ≥ 48%, N ≥ 30/戦略

### 2. Bonferroni 補正 + Pre-reg LOCK
- 戦略 A と同じプロトコル

## 既存戦略との違い (whitespace 分析)

| 既存戦略 | 不足部分 |
|---|---|
| bb_rsi_reversion | 1m BB+RSI 過熱、M5 div なし、M15 trend gate なし |
| v_reversal | 10-bar momentum 逆転、5m exhaustion structure なし |
| mtf_confluence | H1/H4 のみ、M5 BB tag + RSI div なし |
| three_bar_reversal | パターン only、過熱 detection なし |

**新規性**:
1. M15 trend 存在を **要求** した上での counter-trend
2. M5 BB%B + RSI divergence の dual gate
3. 1m engulfing/pin bar pattern + 固定小幅 TP (短命 exhaustion 専用)

## Files
- `strategies/scalp/mtf_counter_trend_scalp.py`
- `modules/htf_data_source.py:compute_mtf_features` (m5.rsi_div_bear/bull)
- 登録: `strategies/scalp/__init__.py`

## Related
- [[friction-analysis]]
- [[claude-harness-design]]
- [[mtf-trend-follow-scalp]] (姉妹戦略)
