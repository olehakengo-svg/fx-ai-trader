# atr_regime_break

## Status: FORCE_DEMOTED (Shadow only)

ATRの自己相関（ボラティリティ・クラスタリング）を利用した、静穏期→急伸レジーム転換のブレイクアウト戦略。BB Squeezeとは異なり、バンド幅ではなくATRのCVパーセンタイルで「圧縮」を定義する。

## Hypothesis
低ボラ期（ATR-CVが下位25%）が続いた後にATRが前バーの `surge_mult` 倍以上に急伸した瞬間は、新レジーム開始の1本目。その方向に短期モメンタムが継続しやすい。

## Academic Backing
- Engle (1982) "Autoregressive conditional heteroscedasticity" (ARCH)
- Mandelbrot (1963) "The variation of certain speculative prices"
- Corsi (2009) HAR-RV

## Signal logic
```python
# 1. 直前 quiet_window 本のATR-CV = std/mean
# 2. 全履歴CV分布に対する現在CVのパーセンタイル <= 0.25 (静穏期)
# 3. 現バーATR / 前バーATR >= surge_mult (急伸)
# 4. |bar_body| >= 0.10 ATR かつ bar_range >= 0.8 ATR
# 5. HTF agreement と方向が矛盾しない
# → バー方向 (body符号) にエントリー
```

## Parameters
| Name | Default | Role |
|------|---------|------|
| quiet_window | 12 | 静穏期判定ウィンドウ（バー数） |
| surge_mult | 1.5 | ATR急伸倍率 |
| quiet_pctl | 0.25 (hardcoded) | CV下位パーセンタイル閾値 |

## Risk / Exit
- SL: `entry ± 1.2 × ATR`（ブレイク後はタイト）
- TP: `1.5 + (surge_ratio - surge_mult) × 1.5`、上限 3.0 ATR（急伸強度に応じて拡大）

## 365d BT (2026-04-17, 15m, daytrade)
| Pair | N | WR | EV | PF |
|------|---|----|----|----|
| USD_JPY | 0 | — | — | — |
| EUR_USD | 0 | — | — | — |
| GBP_USD | 1 | 0.0% | -1.95 | 0.0 |

N=0〜1 — ゲートが非常に狭く、365日で事実上発火していない。Shadow維持で発火頻度の観測が先。

## Significance
N<5 により検定不能。5段合流ゲート（quiet_pctl≤0.25 AND surge_mult≥1.5 AND body/range閾値 AND HTF一致）が発火率を事実上ゼロに絞っている。エッジの有無を判定するには、先に発火率を年間 N≥30〜50 に上げる必要がある。

**クオンツ判断:** パラメータ変更扱い → CLAUDE.md「パラメータ調整完了・データ蓄積フェーズ」原則との衝突あり。ゲート緩和BTを実行するかはユーザー判断を仰ぐ。

## Filters / Guards
- `ctx.atr > 0`
- 最低バー数: `max(quiet_window × 5, 100)`
- HTF Hard Block (v9.1): bull × SELL / bear × BUY は棄却
- パーセンタイル計算は現在バー除外、CV計算ウィンドウも `iloc[-(w+1):-1]`（look-ahead防止）

## Scoring
`base=5.5` + surge強度ボーナス + 静穏度ボーナス + body明瞭ボーナス、confidence = min(85, 50+score×3)

## Related
- [[bb-squeeze-breakout]] — 類似コンセプト（バンド幅ベース）
- [[vol-surge-detector]] — 別ATRベース発火戦略
- [[tier-master]]
