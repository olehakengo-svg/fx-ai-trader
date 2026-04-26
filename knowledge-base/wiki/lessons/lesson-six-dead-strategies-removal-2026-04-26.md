# Lesson: 6 削除推奨戦略 — 完全削除候補の物理仮説否定 (2026-04-26)

## 背景

[[phase2-mechanism-thesis-inventory-2026-04-26]] で 60 戦略の mechanism thesis を
評価. 以下 6 戦略は本日 4/25 の Phase 5 BT + 過去蓄積データで **物理仮説否定 +
TAP violation** が二重に確認され、`_FORCE_DEMOTED` 維持を超えた**完全削除候補**.

## 削除推奨 6 戦略

### 1. macdh_reversal
- **物理仮説**: MACD Histogram reversal at BB extreme = momentum 消耗 + 価格極端
- **否定根拠**: Live N=134 で **med MFE = 0.00 pip** (中央値!). リアルタイム predictive
  power ゼロ. 3-bar pattern (`macdh_prev ≤ macdh_prev2 < macdh`) は
  ランダムウォーク確率 1/8 で偶発的大量発生 (TAP-2 violation).
- **EV / WR**: -1.13 / 12.7%
- **削除理由**: 物理仮説完全否定. lookback bias overfit. `strategies/scalp/macdh.py` 削除可.

### 2. ema_trend_scalp
- **物理仮説**: Time Series Momentum (Moskowitz 2012) + EMA dynamic S/R (Murphy 1999)
- **否定根拠**: Live N=680 で全 27 cell EV<0, 救済 cell **0個**. 5 つの TAP 重畳:
  TAP-1 (中間帯 BBPB 0.25-0.75 / RSI 30-65), TAP-3 (反転 candle 単独), TAP-4 (摩擦死),
  TAP-5 (Score 膨張), プルバック zone 過大.
- **EV / WR**: -1.47 / 17.8%
- **削除理由**: TAP 5 個重畳, Phase 5 D2 (EMA Pullback TF Grid) でも 5m〜4h 全 REJECT.
  `strategies/scalp/ema_trend_scalp.py` 削除可.

### 3. fib_reversal
- **物理仮説**: Fibonacci retracement 反発
- **否定根拠**: Live N=269 で WR 21.2% EV-0.59. 救済 cell **0個**. med MFE 0.60p
  で必要 RR 3.72 vs 達成可能 RR 0.14 (摩擦死).
- **EV / WR**: -0.59 / 21.2%
- **削除理由**: 物理仮説 (Fib retracement) は日足以上で実証された理論で、5m 適用は
  TAP-6 (学術引用 bias). `strategies/scalp/fib.py` 削除可.

### 4. sr_channel_reversal
- **物理仮説**: SR 水平線・並行チャネル反発 (Osler 2000)
- **否定根拠**: Live N=228 で WR 21.5% EV-0.90. TAP-1 (RSI 中間帯 45/55) +
  TAP-3 (反転 candle 単独).
- **EV / WR**: -0.90 / 21.5%
- **削除理由**: TAP 2 個 violation. `strategies/scalp/sr_channel_reversal.py` 削除可.

### 5. stoch_trend_pullback
- **物理仮説**: Stochastic trend pullback
- **否定根拠**: Live N=204 で WR 21.6% EV-0.96. TAP-1 (Stoch 中間帯
  prev_stoch_buy=48 / prev_stoch_sell=52 = 中央値直近).
- **EV / WR**: -0.96 / 21.6%
- **削除理由**: TAP-1 完全違反. Stoch 中間帯フィルタは構造的にエッジゼロ.
  `strategies/scalp/stoch_pullback.py` 削除可.

### 6. engulfing_bb
- **物理仮説**: 包み足パターン at BB 極端
- **否定根拠**: Live N=177 で WR 24.3% EV-0.49. TAP-2 (2-bar 包み足 pattern, 確率 1/4
  でランダム発生) + TAP-3 (反転 candle 単独).
- **EV / WR**: -0.49 / 24.3%
- **削除理由**: 包み足は visual pattern recognition でランダム偶発が大半.
  `strategies/scalp/engulfing_bb.py` 削除可.

## 削除作業手順 (Phase 2 後の Phase 3 で実施)

各戦略について:
1. **戦略ファイル削除**: `strategies/scalp/{name}.py`
2. **戦略 register 解除**: `strategies/scalp/__init__.py` から import 削除
3. **本番 dispatch 解除**: `app.py` の `_QUALIFIED_TYPES` から削除
4. **`_FORCE_DEMOTED` 集合更新**: tier-master.md + sync_kb_index.py 連動
5. **戦略 KB ページ更新**: `wiki/strategies/{name}.md` に "REMOVED 2026-XX-XX" 注記
6. **lesson 引用**: 本 lesson を strategies KB の参照リンクに追加

## クオンツ的根拠

[[lesson-toxic-anti-patterns-2026-04-25]] で **6 つの TAP** を Gate -1 として制定.
これら 6 戦略は **2 個以上の TAP** を violate しており、Gate -1 スルー時点で
本来 deploy されるべきではなかった戦略.

## 他の `_FORCE_DEMOTED` 戦略との違い

`_FORCE_DEMOTED` 17 戦略のうち、本 lesson の 6 戦略以外 (atr_regime_break,
dt_bb_rsi_mr, ema_cross, ema_pullback, ema_ribbon_ride, inducement_ob,
intraday_seasonality, lin_reg_channel, orb_trap, sr_break_retest, sr_fib_confluence) は:
- TAP violation が 0-1 個
- mechanism thesis 不完全だが **完全否定までは未達**
- → `_FORCE_DEMOTED` 維持で Shadow データ蓄積継続候補

つまり本 6 戦略は:
- 削除候補 (本 lesson 対象, TAP 2+ violation, 完全否定)
- `_FORCE_DEMOTED` 維持 (Shadow 観察継続, 11 戦略)

の 2 層に分離.

## 次セッション (Phase 3) アクション

- 6 戦略の `strategies/{scalp,daytrade}/` ファイル削除
- 連動 register / dispatch / tier-master update
- 削除 commit + 実装後の Live trade DB は影響なし (既に Shadow なので)

## 参照

- [[lesson-toxic-anti-patterns-2026-04-25]] (Gate -1 / TAP)
- [[lesson-dead-strategy-pattern-2026-04-25]] (DEAD パターン定義)
- [[phase2-mechanism-thesis-inventory-2026-04-26]] (60 戦略棚卸し)
- [[edge-reset-direction-2026-04-26]] (方向転換決定)
