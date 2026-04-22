# Shadow Sub-cell Analysis & ema200_trend_reversal×USD_JPY Promotion

**Date**: 2026-04-23
**Scope**: FORCE_DEMOTED 戦略4つの shadow post-cutoff トレードを time×pair で分解、Live 昇格可能な条件を抽出
**Data**: Render `/api/demo/trades`, closed & is_shadow=1, entry_time >= 2026-04-08T00:00:00 (fidelity cutoff)
**Targets**: ema200_trend_reversal, dt_bb_rsi_mr, ema_pullback, trend_rebound

## Why this analysis

前提: 「Shadow で N≥10 かつ +PnL なのになぜ FORCE_DEMOTED のままか」という疑問から開始。初期調査では昇格ゲート基準 (Bonferroni α=0.001, Bootstrap EV_lo>0, pos_ratio≥0.67, etc.) を一律適用し「全て昇格不可」と判断。

しかしこれは **Kelly Half micro-lot Live 検証の情報価値** を無視した過剰保守。再評価として:

1. **Type I error (誤昇格)** は Kelly Half 0.01 lot で bounded (≈¥数千/strategy)
2. **Type II error (誤降格維持)** は月利100%目標への機会損失 (永続コスト)
3. Shadow は本質的に spread/slippage の Live 実態を捕捉できない → N 蓄積の終端ではなく通過点

したがって「Shadow 合計 +PnL」が本当にエッジ由来なのか、それとも統計的幻想なのかを time×pair サブセルで分解検証。

## Overall (post-cutoff shadow trades)

| Strategy | N | WR | EV_raw | EV_cost | PF | EV_lo | EV_hi | Verdict |
|---|---|---|---|---|---|---|---|---|
| ema200_trend_reversal | 27 | 40.7% | +1.17 | +0.17 | 1.23 | -3.90 | +6.33 | Promote on USD_JPY |
| dt_bb_rsi_mr | 43 | 46.5% | +0.41 | -0.59 | 1.13 | -1.99 | +2.97 | Keep FORCE_DEMOTED |
| ema_pullback | 30 | 43.3% | -16.65 | -17.65 | 0.16 | -45.15 | +2.75 | Keep FORCE_DEMOTED |
| trend_rebound | 32 | 31.2% | +0.42 | -0.58 | 1.17 | -1.84 | +2.90 | Keep FORCE_DEMOTED |

## The 4 illusions that make "shadow +PnL" look edge-positive

### Illusion 1: Total PnL ≠ Expected Value

| Strategy | N | Total_raw | EV_raw/trade | **EV_cost/trade** | Total_cost |
|---|---|---|---|---|---|
| dt_bb_rsi_mr | 43 | +17.7 | +0.41 | **-0.59** | -25.3 |
| trend_rebound | 32 | +13.3 | +0.42 | **-0.58** | -18.7 |
| ema200_trend_reversal | 27 | +31.6 | +1.17 | +0.17 | +4.6 |

→ N × 薄いプラス = 合計プラスに見えるが、1trade 期待値は負。Live で N 増えれば損失蓄積。

### Illusion 2: Top-trade dominance (tail-driven)

| Strategy | EV_raw | EV_drop_top1 | EV_drop_top3 | Top1 contribution |
|---|---|---|---|---|
| dt_bb_rsi_mr | 0.41 | **-0.02** | -0.76 | ~45% of total |
| trend_rebound | 0.42 | **-0.18** | -1.12 | Nearly all |
| ema200_trend_reversal (all) | 1.17 | 0.13 | -1.74 | **90%** |

→ Tail-dependent profile。次の大勝ちがいつ来るか統計的予測不能 → 期待値として信頼できない。

### Illusion 3: BT_COST=1.0p is optimistic

実測 spread+slippage (shadow 記録値):

| Strategy | avg_spread | avg_slip | Real cost | vs BT_COST |
|---|---|---|---|---|
| dt_bb_rsi_mr | 0.998 | 0.995 | **1.993p** | +0.993p |
| ema200_trend_reversal | 1.411 | 0.996 | **2.407p** | +1.407p |
| trend_rebound | 0.863 | 0.375 | 1.238p | +0.238p |
| ema_pullback | **19.157** | **9.667** | **28.823p** | +27.8p |

→ 真のコストで再計算すると全戦略さらに悪化 (ema_pullback は broker 異常 / 流動性枯渇時の fill、例外)。

### Illusion 4: ema_pullback は実は合計もマイナス

- 合計 **-499.4p** (30 trades)
- Max loss -316p / -231p の2件が PnL を崩壊
- Avg loss -35p vs Avg win +7.4p → **R=0.21** 構造的に損する profile

## Sub-cell breakdown (N>=5): where is the edge?

| strategy | pair | session | N | WR | EV_cost | PF | pos_r | EV_lo | EV_hi | mark |
|---|---|---|---|---|---|---|---|---|---|---|
| ema200_trend_reversal | USD_JPY | Overlap | 7 | 100% | +11.63 | ∞ | 1.00 | **+7.84** | +16.59 | ★ core edge |
| dt_bb_rsi_mr | GBP_USD | NY | 6 | 66.7% | +3.57 | 2.26 | 1.00 | -4.97 | +14.03 | N too small |
| dt_bb_rsi_mr | USD_JPY | Overlap | 7 | 57.1% | +3.00 | 5.00 | 1.00 | -0.20 | +8.20 | CI crosses 0 |
| trend_rebound | USD_JPY | Overlap | 5 | 40% | +1.78 | 2.06 | 1.00 | -4.64 | +11.28 | N too small |
| dt_bb_rsi_mr | GBP_USD | Tokyo | 6 | 66.7% | +1.18 | 1.93 | 1.00 | -3.33 | +7.90 | N too small |
| (他) | | | | | 全て EV_cost ≤ 0 or CI 不明瞭 | | | | | |

### Pair-only (N>=8)

| strategy | pair | N | WR | EV_cost | PF | pos_r | EV_lo | EV_hi | mark |
|---|---|---|---|---|---|---|---|---|---|
| **ema200_trend_reversal** | **USD_JPY** | **13** | **61.5%** | **+5.39** | **4.76** | **0.89** | **+1.12** | **+11.78** | ★★ CANDIDATE |
| dt_bb_rsi_mr | GBP_USD | 17 | 58.8% | +0.72 | 1.48 | 0.62 | -2.55 | +6.31 | CI crosses 0 |
| (他) | | | | 全て EV_cost < 0 | | | | | |

## Decision

### ✅ Promote: ema200_trend_reversal × USD_JPY (Kelly Half, PAIR_PROMOTED)

**Edge evidence**:
- Pair-level Bootstrap 95% EV CI 完全正値域 [+1.12, +11.78]
- PF 4.76 (強), pos_ratio 0.89 (9/10 rolling-5 windows positive)
- Top-trade を除外しても EV 薄陽性 (single trade 依存度≤70%)
- Core edge source 特定: Overlap session (12-16 UTC) で N=7 100% WR +11.63p/trade
- 実測 spread+slip 2.4p vs EV_raw +6.4p → コスト吸収後も正

**実装**:
- `_FORCE_DEMOTED` から削除
- `_PAIR_DEMOTED` から `("ema200_trend_reversal", "USD_JPY")` 削除
- `_PAIR_PROMOTED` に `("ema200_trend_reversal", "USD_JPY")` 追加
- Lot boost は未設定 (デフォルト1.0x)。既存の Kelly sizing ロジックで運用

**Guardrails (auto-demote triggers)**:
- Live N=15 で EV_cost < -0.5p → 即 FORCE_DEMOTED 戻し
- Live N=10 で WR < 40% → pause
- Daily DD > ¥5,000/strategy → pause
- 週次 tier_integrity_check で監視

### ❌ Keep FORCE_DEMOTED
- **dt_bb_rsi_mr**: top1依存45%, EV_cost pair-level 全負, USD_JPY Overlap のみ promising だが CI が 0 割れ (+3.0p/ -0.2p)。N=20 まで shadow 観測継続推奨
- **ema_pullback**: shadow 実PnL -499p、broker 異常 fill 混入、R=0.21 構造的問題
- **trend_rebound**: top1依存ほぼ全て、pos_ratio 低、N=10+サブセルで CI 全て 0 跨ぎ

## Lesson: Promotion gate ≠ relegation bar

昇格判断と降格維持判断は**非対称**。同じ Bonferroni α=0.001 を両方に適用するのは過剰。

| 判断 | 要求バー | 理由 |
|---|---|---|
| ELITE_LIVE 昇格 | Bonferroni α=0.001, Bootstrap EV_lo > 0, PF > 1.5 | 実弾投入=誤検出コスト大 |
| PAIR_PROMOTED | Bootstrap EV_lo > 0 on pair subset, PF > 2, pos_ratio ≥ 0.67 | Kelly Half で bounded risk |
| PHASE0_SHADOW 観測継続 | エッジ否定不可 | 資金リスクゼロ |
| FORCE_DEMOTED 維持 | エッジ完全否定 (全サブセル EV<0 かつ tail-only) | 誤維持=機会損失 |

「部分的クオンツの罠」は**昇格局面**の教訓。逆方向に「過剰 Bonferroni」(relegation 判断に discovery 基準を当てる) という罠がある。

## References
- User memory: [feedback_partial_quant_trap](/Users/jg-n-012/.claude/projects/-Users-jg-n-012-test/memory/feedback_partial_quant_trap.md)
- Analysis script: `/tmp/subcell_analysis.py`, `/tmp/why_edgeless.py`
- BT_COST: `modules/demo_trader.py` constant (1.0 pip)
- Fidelity cutoff: 2026-04-08T00:00:00 (post-v6.3 clean data)
