# FORCE_DEMOTED 12戦略 因数分解レビュー (2026-04-15)

## 失敗カテゴリ分布

| カテゴリ | 件数 | 戦略 |
|---|---|---|
| **FRICTION_KILL** | 5 | ema_ribbon_ride, ema_pullback, macdh_reversal, sr_channel_reversal, bb_squeeze_breakout |
| **NO_EDGE** | 2 | lin_reg_channel, dt_bb_rsi_mr |
| **REGIME_DEPENDENT** | 3 | fib_reversal, stoch_trend_pullback, engulfing_bb |
| **OVERFITTED** | 1 | sr_fib_confluence |
| **Insufficient N** | 1 | sr_break_retest |

## ELITE/SENTINEL戦略への汎用教訓

### 教訓1: 摩擦/TP比率が支配的な失敗要因（5/12件）
TP < 3× round-trip friction のScalp戦略は構造的に死亡。
→ **全SENTINEL戦略に適用**: 摩擦/TP比率を計算し、3倍未満なら警告

### 教訓2: BT-Live WR乖離は平均-20〜-36pp
FORCE_DEMOTED全体の平均乖離。ELITE戦略はLive WR推定時に-10pp以上のヘアカットを適用すべき。

### 教訓3: ペア別分析が戦略を救う（5/12件が部分復活）
全ペア集計で負EVでも、特定ペアでは正EV。PAIR_PROMOTEDティアの正しさが実証された。

### 教訓4: 即死率>80%は「TFが違う」サイン（3/12件）
理論は正しいが実装TFが1m（摩擦に対してATRが小さすぎる）。5m/15mに移動するだけで正EVになるケースが多い。

### 教訓5: N<15でのFORCE_DEMOTEは時期尚早（1件）
sr_break_retest (N=5) は統計的に判断不能。SHADOWに戻してデータ蓄積すべき。

### 教訓6: TFポーティングには再検証必須（2件）
dt_bb_rsi_mr (1m→15m)、ema_ribbon_ride (15m→1m) — エッジのメカニズムがTF特有の場合、ポーティングは失敗する。

## 各戦略サマリー

| # | Strategy | Type | 失敗分類 | 根本原因 | 復活可能性 |
|---|---|---|---|---|---|
| 1 | sr_fib_confluence | MR | OVERFITTED | 理由文字列パースに依存（実装の構造的欠陥） | ✗ 不可能（再設計必要） |
| 2 | ema_ribbon_ride | TF | FRICTION_KILL | TP=2-4pip vs 摩擦=2-4pip（TFが1mで小さすぎ） | △ 15mに移動すれば可能 |
| 3 | ema_pullback | TF | FRICTION+REGIME | 1mでのプルバック検出がノイズ | ○ JPY PAIR_PROMOTED済み |
| 4 | lin_reg_channel | MR | NO_EDGE | 回帰チャネルのルックアヘッドバイアス | ✗ 不可能（構造的問題） |
| 5 | fib_reversal | MR | REGIME_DEP | 60d→180dでEV反転。rawエッジは存在（WR=56%） | ○ 実装改善で回復可能 |
| 6 | macdh_reversal | MR | FRICTION_KILL | MACD-Hが遅行→エントリー1-3pip遅延 | △ 5m TFで検討可能 |
| 7 | sr_break_retest | TF | N不足 | N=5で判断不能。コード自体は健全 | ○ SHADOWに戻すべき |
| 8 | engulfing_bb | MR | REGIME_DEP | 全体負EVだがEUR_USD Live WR=67% | ○ EUR PAIR_PROMOTED済み |
| 9 | bb_squeeze_breakout | Breakout | FRICTION_KILL | ブレイクアウト初動のスプレッド拡大 | ○ JPY 5m PAIR_PROMOTED済み |
| 10 | sr_channel_reversal | MR | FRICTION+BUG | SL=ATR×0.5 ≈ 摩擦コスト（SL狭すぎ） | △ SL拡大+5m移動で可能 |
| 11 | stoch_trend_pullback | TF | REGIME_DEP | RR>2:1でWR33%でも正PnL。GBP_JPY BT正EV | ○ GBP_JPY PAIR_PROMOTED済み |
| 12 | dt_bb_rsi_mr | MR | NO_EDGE | 1m MRの15mポーティングが無効（N=608で確定） | ✗ 不可能（TF特有エッジ） |

## Related
- [[lesson-reactive-changes]] — 判断プロトコル
- [[eur-scalp-regime-analysis]] — raw edgeと実装の分離
- [[bt-live-divergence]] — 6つのBTバイアス
- [[friction-analysis]] — ペア別摩擦
