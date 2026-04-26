# Strategy Mechanism Thesis Audit (2026-04-26)

**Date**: 2026-04-26
**Phase**: Edge Reset Phase 2 着手 (Phase 1.7 内)
**Status**: 枠組み + 代表 5 戦略の判定。残り 30 戦略は次セッションで継続。

## 1. 目的と背景

`lesson-label-neutralization-was-symptom-treatment-2026-04-26.md` で記録した教訓:

> 「ラベルが正しく付与されているか」と「ラベルが指す戦略に edge があるか」は独立した 2 命題。
> 前者だけ完璧にしても、後者がなければ Live で勝てない。

Live N=259 で WR 39.0%, Kelly **-17.97%** の根因の 1 つは「mechanism thesis なき戦略」が
shadow / live に大量に存在することと推定される (Phase 5 6/9 DEAD と整合)。

本 audit は全 35 戦略について **mechanism thesis の有無** を 3 段階で判定し、
thesis なし戦略を Phase 1.5 完了後に shadow から除外する。

## 2. 判定基準

### VALID (採用継続候補)
- **1-2 行で価格メカニズムを説明可能**
- TAP-1/2/3 (中間帯 AND, N-bar pattern, 直前 candle) を**含まない**
- 学術的引用または市場マイクロストラクチャーへの言及がある
- 因果の方向が明示的 (X が起きる→Y が反応)

例: `orb_trap` — "セッション境界の流動性遷移で価格 dislocation 発生 → 範囲外 break 後の範囲回帰を捕捉"

### WEAK (要 mechanism 補強 or 改造)
- thesis が指標ベースで因果不明 (例: "BB タッチ + RSI<30 → 反転")
- TAP-1 を含む (中間帯 RSI/Stoch + AND フィルタ)
- 学術根拠あるが、Live と乖離する仮定 (例: 365日 BT 基準のみ)

例: `bb_rsi_reversion` — "BB %b<0.20 + RSI<35 → 反発" (機械的、流動性メカニズム不在)

### NONE (除外候補)
- thesis なし、indicator combination のみ
- TAP-2/3 を含む (N-bar pattern, 直前 candle)
- median MFE = 0 など、時系列的に予測力ゼロが実証

例: `macdh_reversal` — MACD-H 反転 (Phase 5 で median MFE = 0 と実証)

### 評価メソッド

各戦略について以下を抽出:
1. `__doc__` の thesis 主張 (上位 3-5 行)
2. evaluate() のコア entry condition (3-5 行)
3. mechanism thesis を 1-2 行で言語化 (できなければ NONE 寄り)
4. TAP-1/2/3 の含有チェック
5. 既知 Live 結果 (tier-master.md / strategies/<name>.md)

## 3. 代表 5 戦略の判定 (本セッション)

### 3.1 `ema_pullback` (Scalp / TF)

**thesis 抽出**:
- Time Series Momentum (Moskowitz et al 2012) ≈ トレンド継続性
- EMA21 がトレンド中の動的 S/R として機能 (Murphy 1999)
- 健全トレンドは浅い押し目→EMA 反発→高値更新

**Entry**: ADX≥20, RSI 30-62 (BUY) / 38-70 (SELL), BB%b 0.12-0.70 (BUY)

**判定: WEAK**

理由:
- 学術引用は強いが、entry condition の RSI/BB 帯が広く (TAP-1 中間帯 AND の典型)
- 「EMA21 動的 S/R」の thesis は妥当だが、entry trigger が「pullback 完了」を捉えていない (条件成立瞬間に発火)
- 改造方向: EMA21 touch + rejection candle の 2 段階確認を追加すれば VALID 化候補

### 3.2 `bb_rsi_reversion` (Scalp / MR)

**thesis 抽出**:
- BB バンド極端タッチでの mean reversion 期待
- RSI 過熱/過冷状態の補強

**Entry**: BB%b < 0.20 (BUY), RSI < 35 (BUY), inverse for SELL

**判定: WEAK**

理由:
- 「BB タッチ → 反発」は流動性メカニズム不在 (なぜ反発するのか?)
- TAP-1 (BB AND RSI) パターン
- BT vs Live divergence -16pp (摩擦+SR+TP短縮、bt-live-divergence.md)
- 改造方向: liquidity sweep wick (高値外 fake → 即帰還) を MR trigger にすれば mechanism 明確化

### 3.3 `orb_trap` (DT / BR)

**thesis 抽出**:
- セッション境界 (London 07:00-07:30 / NY 13:30-14:00) で流動性遷移
- 流動性遷移 → 価格 dislocation (Corcoran 2002)
- False breakout 後のチャネル回帰勝率 70-80% (Bulkowski 2005)
- 短期リバーサル効果 (Lo & MacKinlay 1988)

**Entry**: OR break 後、Close が再度 OR 内に戻り (Trap Confirmation 2 条件)

**判定: VALID**

理由:
- mechanism (流動性遷移、dislocation) が明示的かつ学術裏付け
- 因果方向が明確: break → trap → 範囲回帰
- TAP-1/2/3 のいずれも含まない
- Trap Confirmation の 2 段階確認は構造的
- Live 実績: BT WR=100%/Live WR=50% (N=2、判断不能、要 N≥30)

⚠️ **注意**: Live N=2 で promotion 判断不可。Phase 1.5 後に shadow N≥30 確認必要。

### 3.4 `ema_trend_scalp` (Scalp / TF)

**thesis 抽出**:
- bb_rsi (MR) と vol_momentum (TF) の GAP を埋める「中間帯」攻略
- ADX 20-40, BB%b 0.25-0.80 でのトレンド継続 pullback
- EMA21 動的 S/R + bounce 確認

**Entry**: ADX 20-40, BB%b 中間帯, EMA21 付近 pullback

**判定: NONE**

理由:
- thesis 自体が「中間帯を狙う」= TAP-1 (中間帯 AND) の自認
- ADX 20-40 + BB%b 0.25-0.80 は random sample of trending market
- Phase 5 (cbbbc8b) で 5m Pure Edge BT 6/9 DEAD の結果に整合
- Phase 4d 監査で 27 cell すべて EV<0 (ema_trend_scalp_high-conf-zone WR 14.7% など)
- bounce 確認は EMA21 touch 後の N-bar pattern (TAP-2 寄り)

→ Phase 1.5 完了後に shadow 除外候補。

### 3.5 `engulfing_bb` (Scalp / MR)

**thesis 抽出**:
- 包み足パターン at BB 極端
- BB%b < 0.30 (BUY) + 包み倍率 1.3× + RSI<45

**Entry**: BB 極端 + 包み足 (前足を覆う) + RSI 補強

**判定: NONE**

理由:
- 包み足 = 直前 candle pattern matching (TAP-3)
- 「BB 極端 → 包み足 → 反転」の因果が薄い (なぜ包み足で反転するのか?)
- Live N=6 WR=16.7% (壊滅、bt-live-divergence.md)
- BT WR=72.7% から Live -55pp 急降下 = 構造的に成立しない pattern

→ Phase 1.5 完了後に shadow 除外候補。

## 4. 集計 (代表 5 戦略のみ)

| 戦略 | カテゴリ | 判定 | Action (Phase 1.5 後) |
|---|---|---|---|
| ema_pullback | TF | WEAK | mechanism 補強案を策定 (EMA21 touch + rejection 2段階) |
| bb_rsi_reversion | MR | WEAK | liquidity sweep wick triggered MR への改造案 |
| orb_trap | BR | VALID | shadow N≥30 確認後 promote 検討 |
| ema_trend_scalp | TF | NONE | shadow 除外 |
| engulfing_bb | MR | NONE | shadow 除外 |

## 5. 次セッション (Phase 2 継続) 残タスク

残り 30 戦略の判定:

### TF (残 7 個)
- ema_pullback_v2, ema200_trend_reversal, trend_rebound, trend_break, london_breakout
- adx_trend_continuation, gold_trend_momentum, jpy_basket_trend

### MR (残 14 個)
- bb_rsi_mr, dt_bb_rsi_mr, sr_channel_reversal, sr_touch
- engulfing_bb_lvn_london_ny, fib_reversal, dt_fib_reversal
- stoch_trend_pullback, sr_fib_confluence, sr_fib_confluence_tight_sl
- london_fix_reversal, london_close_reversal, london_close_reversal_v2
- eurgbp_daily_mr, gbp_deep_pullback

### BR (残 5 個)
- london_session_breakout, htf_false_breakout
- alpha_atr_regime_break, doji_breakout, liquidity_sweep

### 棚卸し作業手順 (次セッション)
1. 各戦略の `__doc__` + evaluate() 主要 entry condition を grep で抽出
2. 上記 4 評価基準で VALID/WEAK/NONE 判定
3. tier-master.md と strategies/<name>.md で Live 実績を相互参照
4. 本ドキュメントの「3. 代表 N 戦略の判定」セクションを拡張

### Phase 1.5 完了後の Action
- NONE 判定戦略 → `modules/demo_trader.py` の `QUALIFIED_TYPES` から除外 (Rule 2 Fast)
- WEAK 判定戦略 → `wiki/strategies/<name>.md` に mechanism 補強案を追記、Phase 3 で改造または除外
- VALID 判定戦略 → 維持、ただし shadow N≥30 + Wilson lower bound > 50% を再検証

## 6. References

- [[edge-reset-direction-2026-04-26]] — Phase 0 方向転換
- [[lesson-label-neutralization-was-symptom-treatment-2026-04-26]] — 誤りの教訓
- [[lesson-toxic-anti-patterns-2026-04-25]] — TAP-1/2/3 の定義 (FORCE_DEMOTED 17 戦略)
- [[bt-live-divergence]] — BT 楽観バイアス 6 因子
- [[friction-analysis]] — 実測 friction 数値
- Phase 5 lesson (cbbbc8b): 5m Pure Edge 6/9 DEAD = 多くの戦略は thesis 不在
- `modules/strategy_category.py` — TF/MR/BR registry
