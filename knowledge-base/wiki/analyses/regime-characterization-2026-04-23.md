# Regime Characterization: Pre vs Post Cutoff (2026-04-23)

**Scope**: shadow / XAU除外 / 5 pairs
**Pre-cutoff**: 2026-03-01 → 2026-04-07 (N=114)
**Post-cutoff**: 2026-04-08 → 2026-04-23 (N=2076)
**Script**: `/tmp/regime_characterization.py`
**Raw**: `/tmp/regime_characterization_output.txt`

## TL;DR

**Current regime = 高 volatility + chop + directional edge消失**
- Realized |pnl| p50: +40–70% 上昇
- SL hit rate: 23% → **54% (+31pp)**
- TP hit rate: 11% → 21% (+10pp)
- avg_win: +4.5p 増加 (良い trades はより大きい)
- avg_loss: -0.8p 悪化
- BUY/SELL edge 消失 (-12.9pp gap → +0.7pp gap)

→ **固定 SL 幅が新 volatility regime に不適合**。TP に届く前に
  chop で SL を踏む確率が高い。設計方針 = **volatility-adaptive risk**
  + **directional persistence filter**。

## 1. Overall shift

| Metric | PRE (N=114) | POST (N=2076) | Δ |
|--------|-------------|---------------|---|
| WR | 31.6% | 23.7% | **-7.8pp** |
| EV/trade | -1.19p | -1.35p | -0.16p |
| TP hit % | 11% | 21% | +10pp |
| SL hit % | **23%** | **54%** | **+31pp** |
| OTHER close (TTL/manual) | 67% | 26% | -42pp |
| tp_dist p50 | 5.1p | 7.7p | +2.6p |
| sl_dist p50 | 3.3p | 4.3p | +1.0p |
| R (tp/sl) | 1.55 | 1.79 | +0.24 |
| avg_win | +4.0p | +8.5p | **+4.47p** |
| avg_loss | -3.6p | -4.4p | -0.82p |
| duration p50 | 7 min | 11 min | +4 min |

**解釈**:
- SL 踏む確率が 2.3× に増加、しかし win 時の獲得幅は 2× 強に拡大
  → 戦略選択が不適 (または SL 幅不足) で、volatility 上昇の恩恵を取れてない
- TTL/manual close が大幅減 (67% → 26%) = **動きが速い** (より早く TP or SL に届く)

## 2. Per-instrument shift (N≥20 両側)

| Instrument | PRE N | PRE WR | POST N | POST WR | Δ |
|------------|-------|--------|--------|---------|---|
| EUR_USD | 65 | 35.4% | 484 | 23.1% | **-12.2pp** |
| USD_JPY | 35 | 28.6% | 1144 | 25.2% | -3.4pp |

GBP_USD / EUR_JPY / GBP_JPY は pre N < 20 で比較不能。EUR_USD 劣化が最も顕著。

## 3. Per-session shift

| Session | PRE N | PRE WR | POST N | POST WR | Δ |
|---------|-------|--------|--------|---------|---|
| asia | 39 | 23.1% | 604 | 22.7% | -0.4pp |
| ny | 57 | 29.8% | 864 | 25.0% | -4.8pp |

**asia** は pre/post でほぼ同じ (22–23% 低空飛行). **ny** は以前から最良だったが
4.8pp 劣化。**london** は pre N 不足で比較不能。

## 4. Per-strategy shift (N≥30 両側)

| Strategy | N_pre | WR_pre | N_post | WR_post | Δ |
|----------|-------|--------|--------|---------|---|
| macdh_reversal | 30 | 40.0% | 46 | 13.0% | **-27.0pp** |
| fib_reversal | 45 | 31.1% | 152 | 27.6% | -3.5pp |

他 15 戦略は pre N < 30 で per-strategy compare 不能。macdh_reversal の崩壊は顕著。

**ΔWR > 0 の戦略**: **0 件** — どの戦略も current regime で改善なし。

## 5. Volatility proxy: |pnl_pips| 分布シフト

| Instrument | PRE p50 | PRE mean | POST p50 | POST mean | Δ p50 |
|------------|---------|----------|----------|-----------|-------|
| EUR_USD | 2.0p | 2.6p | 3.4p | 4.3p | **+1.4p (+70%)** |
| USD_JPY | 3.0p | 3.8p | 3.9p | 5.0p | **+0.9p (+30%)** |

**realized movement が 30–70% 拡大** している。
- SL p50=4.3p に対して realized |pnl| p50=3.4–3.9p が拮抗
- → ほとんどの trades で SL が先に引かれる構造

## 6. Spread shift

| Instrument | PRE p50 | POST p50 |
|------------|---------|----------|
| EUR_USD | 0.80 | 0.80 |
| USD_JPY | 0.80 | 0.80 |

Spread 変化なし → **コスト構造 (friction) は不変**、WR 劣化は純粋に
**price action の regime shift** による。

## 7. Direction bias shift

| Window | BUY WR | SELL WR | gap |
|--------|--------|---------|-----|
| PRE | 25.0% | 37.9% | **-12.9pp** (SELL優勢) |
| POST | 24.1% | 23.4% | +0.7pp (neutral) |

**SELL edge 消失**. pre-cutoff では SELL が +12.9pp 優位だったが、
post-cutoff では direction 無差別。→ 以前の bearish regime が消えて
choppy/sideways に近づいた可能性。

## 8. 現 regime の構造的特徴 (hypothesis)

上記観察から current regime の profile:

1. **Volatility +40–70%**: 短期 realized movement 拡大
2. **SL hit rate 2.3×**: 固定 SL 幅が狭すぎる
3. **TP hit rate 2×**: 届く時は届くが、そこまで生き残れない
4. **Direction bias 消失**: trend following / directional filter が機能しない
5. **Duration 変化少**: 動きが速いが、時間軸は維持

典型的な **high-vol / range-bound (or noisy trend)** regime。既存戦略の多くは
trend-follow または mean-reversion で、current chop に対してどちらも脆弱。

## 9. Phase 4 設計への含意

以下の design direction が data-driven に正当化される (ただし
pre-registration で実装前に criteria を lock する必要あり):

### D1: Volatility-adaptive risk sizing
- ATR-based SL/TP (固定 pips 廃止)
- 現 SL p50=4.3p は realized |pnl| p50≈3.4p に対して薄い → ATR×k (k>1) で拡大

### D2: Entry filter (directional persistence)
- BUY/SELL edge 消失 = 既存の trend-follow ロジックが false positive 多
- 連続 bar の方向一致 (例: 3本連続 same close direction) を必須化候補

### D3: Regime detector → stand-down gate
- vol spike 時に entry 停止 (chop 帯を回避)
- 既存 Spread/SL Gate と同 layer で動的判定

### D4: Mean-reversion 専用 strategy
- TP が大きい (+8.5p) = price action は振れている
- Bollinger ±2σ touch → mean-reversion entry with wide SL (vol-scaled)

### NOT justified by this data
- **新 label の直接追加** (Phase 1 holdout 前は code change しない)
- **既存戦略の threshold fine-tuning** (overfitting lesson)
- **PAIR_PROMOTED の個別 override** (cell-level scan で 0 survivor)

## Limitations

1. **PRE N=114 は小さい** (38 日 × ~3/日) — baseline として不安定
2. **2 instrument のみ** (EUR_USD / USD_JPY) 比較可能 — GBP 系 / JPY-cross は
   pre データ不足
3. **Regime change の因果は未特定** — macro (DXY/VIX) データとの突合は未実施
   (次回 hypothesis として記録)
4. **Shadow-only** — live 側の比較はここではしない (contamination 回避)

## References

- [[phase0-data-integrity-2026-04-23]]
- [[cell-level-scan-2026-04-23]]
- [[pre-registration-label-holdout-2026-05-07]]
- Next: [[pre-registration-phase4-regime-native-2026-04-23]]
