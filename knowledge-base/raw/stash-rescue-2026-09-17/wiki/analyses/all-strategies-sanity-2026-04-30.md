---
date: 2026-04-30
phase: bt-serialized-willow Level 2 sanity sweep
status: report
source: all_strategies_sanity_20260430_155544.json
related:
  - "[[bt-vec-harness-level3-2026-04-30]]"
  - master plan: `~/.claude/plans/bt-serialized-willow.md`
---

# Level 2 — All-Strategies Sanity Sweep (raw harness edge)

## Run config

- run_at: 2026-04-30T15:55:44.268525
- days: 90
- symbols: ['USDJPY=X', 'EURUSD=X']
- total_wall_secs: 7741.83

## Summary

| metric | value |
|---|---|
| total cells | 152 |
| fired (N>0) | 69 |
| zero-fire | 83 |
| errored | 0 |
| Bonferroni α | 0.0007 (69 active cells) |
| BEV floor | 40.0% |
| Bonferroni-pass cells | **7** |

## ✅ Bonferroni-pass cells

| symbol | strategy | N | WR | Wlo | EV | PF | Kelly |
|---|---|---|---|---|---|---|---|
| USDJPY=X | trend_rebound | 148 | 49.32% | 41.39% | 0.52p | 1.231 | 9.242% |
| USDJPY=X | dt_bb_rsi_mr | 1029 | 43.25% | 40.25% | -0.257p | 0.902 | 0.0% |
| USDJPY=X | gotobi_fix | 50 | 56.0% | 42.31% | -1.378p | 0.83 | 0.0% |
| USDJPY=X | htf_false_breakout | 574 | 44.25% | 40.24% | -0.043p | 0.982 | 0.0% |
| EURUSD=X | dt_bb_rsi_mr | 1068 | 46.16% | 43.19% | 0.154p | 1.071 | 3.061% |
| EURUSD=X | htf_false_breakout | 549 | 47.54% | 43.4% | 0.087p | 1.038 | 1.576% |
| EURUSD=X | session_time_bias | 504 | 45.24% | 40.95% | 0.17p | 1.058 | 2.483% |

## Top 20 by Wilson_lo (N≥15)

| # | symbol | strategy | N | WR | Wlo | EV | PF | Kelly |
|---|---|---|---|---|---|---|---|---|
| 1 | EURUSD=X | htf_false_breakout | 549 | 47.54% | 43.4% | 0.087p | 1.038 | 1.576% |
| 2 | EURUSD=X | dt_bb_rsi_mr | 1068 | 46.16% | 43.19% | 0.154p | 1.071 | 3.061% |
| 3 | USDJPY=X | gotobi_fix | 50 | 56.0% | 42.31% | -1.378p | 0.83 | 0.0% |
| 4 | USDJPY=X | trend_rebound | 148 | 49.32% | 41.39% | 0.52p | 1.231 | 9.242% |
| 5 | EURUSD=X | session_time_bias | 504 | 45.24% | 40.95% | 0.17p | 1.058 | 2.483% |
| 6 | USDJPY=X | dt_bb_rsi_mr | 1029 | 43.25% | 40.25% | -0.257p | 0.902 | 0.0% |
| 7 | USDJPY=X | htf_false_breakout | 574 | 44.25% | 40.24% | -0.043p | 0.982 | 0.0% |
| 8 | USDJPY=X | engulfing_bb | 809 | 40.67% | 37.33% | 0.014p | 1.006 | 0.239% |
| 9 | EURUSD=X | xs_momentum | 400 | 41.75% | 37.02% | -0.379p | 0.895 | 0.0% |
| 10 | USDJPY=X | macdh_reversal | 228 | 42.11% | 35.88% | 0.394p | 1.203 | 7.094% |
| 11 | EURUSD=X | trend_rebound | 81 | 45.68% | 35.27% | 0.289p | 1.13 | 5.249% |
| 12 | USDJPY=X | three_bar_reversal | 200 | 41.5% | 34.89% | -0.307p | 0.885 | 0.0% |
| 13 | USDJPY=X | orb_trap | 38 | 50.0% | 34.85% | 1.27p | 1.273 | 10.718% |
| 14 | USDJPY=X | ema_trend_scalp | 1713 | 36.89% | 34.64% | 0.014p | 1.005 | 0.2% |
| 15 | USDJPY=X | session_time_bias | 435 | 38.85% | 34.39% | -0.446p | 0.851 | 0.0% |
| 16 | EURUSD=X | engulfing_bb | 732 | 37.7% | 34.27% | -0.092p | 0.957 | 0.0% |
| 17 | USDJPY=X | xs_momentum | 473 | 38.27% | 34.0% | -0.728p | 0.815 | 0.0% |
| 18 | EURUSD=X | macdh_reversal | 227 | 39.65% | 33.51% | 0.047p | 1.026 | 0.99% |
| 19 | USDJPY=X | wick_imbalance_reversion | 723 | 36.51% | 33.08% | -0.57p | 0.855 | 0.0% |
| 20 | EURUSD=X | wick_imbalance_reversion | 1132 | 35.25% | 32.52% | -0.444p | 0.86 | 0.0% |

## Top 20 by PF (N≥15)

| # | symbol | strategy | N | WR | Wlo | EV | PF | Kelly |
|---|---|---|---|---|---|---|---|---|
| 1 | USDJPY=X | mtf_reversal_confluence | 136 | 31.62% | 24.4% | 0.469p | 1.39 | 8.864% |
| 2 | EURUSD=X | mtf_regime_trend_cascade_scalp | 20 | 40.0% | 21.88% | 1.112p | 1.368 | 10.769% |
| 3 | EURUSD=X | london_ny_swing | 37 | 37.84% | 24.06% | 0.823p | 1.275 | 8.156% |
| 4 | USDJPY=X | orb_trap | 38 | 50.0% | 34.85% | 1.27p | 1.273 | 10.718% |
| 5 | USDJPY=X | tokyo_nakane_momentum | 36 | 44.44% | 29.54% | 0.474p | 1.238 | 8.557% |
| 6 | USDJPY=X | trend_rebound | 148 | 49.32% | 41.39% | 0.52p | 1.231 | 9.242% |
| 7 | USDJPY=X | macdh_reversal | 228 | 42.11% | 35.88% | 0.394p | 1.203 | 7.094% |
| 8 | EURUSD=X | london_close_reversal_v2 | 18 | 44.44% | 24.56% | 0.273p | 1.155 | 5.95% |
| 9 | EURUSD=X | trend_rebound | 81 | 45.68% | 35.27% | 0.289p | 1.13 | 5.249% |
| 10 | USDJPY=X | vol_spike_mr | 783 | 32.06% | 28.88% | 0.168p | 1.104 | 3.634% |
| 11 | EURUSD=X | post_news_vol | 87 | 33.33% | 24.32% | 0.631p | 1.098 | 0.0% |
| 12 | EURUSD=X | dt_bb_rsi_mr | 1068 | 46.16% | 43.19% | 0.154p | 1.071 | 3.061% |
| 13 | EURUSD=X | session_time_bias | 504 | 45.24% | 40.95% | 0.17p | 1.058 | 2.483% |
| 14 | EURUSD=X | htf_false_breakout | 549 | 47.54% | 43.4% | 0.087p | 1.038 | 1.576% |
| 15 | EURUSD=X | macdh_reversal | 227 | 39.65% | 33.51% | 0.047p | 1.026 | 0.99% |
| 16 | USDJPY=X | engulfing_bb | 809 | 40.67% | 37.33% | 0.014p | 1.006 | 0.239% |
| 17 | USDJPY=X | ema_trend_scalp | 1713 | 36.89% | 34.64% | 0.014p | 1.005 | 0.2% |
| 18 | USDJPY=X | fib_reversal | 988 | 26.82% | 24.15% | 0.002p | 1.001 | 0.034% |
| 19 | USDJPY=X | mtf_regime_trend_cascade_scalp | 24 | 37.5% | 21.16% | -0.039p | 0.99 | 0.0% |
| 20 | USDJPY=X | htf_false_breakout | 574 | 44.25% | 40.24% | -0.043p | 0.982 | 0.0% |

## Zero-fire strategies (need Level 3 toggles to evaluate)

| strategy | symbols 0-fire |
|---|---|
| adx_trend_continuation | USDJPY=X |
| asia_range_fade_v1 | USDJPY=X, EURUSD=X |
| atr_regime_break | EURUSD=X |
| cpd_divergence | USDJPY=X, EURUSD=X |
| dt_sr_channel_reversal | USDJPY=X, EURUSD=X |
| ema_cross | USDJPY=X, EURUSD=X |
| ema_ribbon_ride | USDJPY=X, EURUSD=X |
| eurgbp_daily_mr | USDJPY=X, EURUSD=X |
| gbp_deep_pullback | USDJPY=X, EURUSD=X |
| gold_pips_hunter | USDJPY=X, EURUSD=X |
| gold_trend_momentum | USDJPY=X, EURUSD=X |
| gold_vol_break | USDJPY=X, EURUSD=X |
| gotobi_fix | EURUSD=X |
| hmm_regime_filter | USDJPY=X, EURUSD=X |
| inducement_ob | USDJPY=X, EURUSD=X |
| intraday_seasonality | USDJPY=X, EURUSD=X |
| jpy_basket_trend | USDJPY=X, EURUSD=X |
| keltner_squeeze_breakout | USDJPY=X |
| lin_reg_channel | USDJPY=X |
| liquidity_sweep | USDJPY=X, EURUSD=X |
| london_breakout | USDJPY=X, EURUSD=X |
| london_close_reversal | USDJPY=X, EURUSD=X |
| london_fix_reversal | USDJPY=X, EURUSD=X |
| london_ny_swing | USDJPY=X |
| london_session_breakout | USDJPY=X, EURUSD=X |
| london_shrapnel | USDJPY=X, EURUSD=X |
| mqe_gbpusd_fix | USDJPY=X, EURUSD=X |
| mtf_regime_range_cascade_scalp | USDJPY=X, EURUSD=X |
| pd_eurjpy_h20_bbpb3_sell | USDJPY=X, EURUSD=X |
| pullback_to_liquidity_v1 | USDJPY=X, EURUSD=X |
| rsk_gbpjpy_reversion | USDJPY=X, EURUSD=X |
| session_vol_expansion | USDJPY=X, EURUSD=X |
| squeeze_release_momentum | USDJPY=X, EURUSD=X |
| sr_anti_hunt_bounce | USDJPY=X, EURUSD=X |
| sr_break_retest | EURUSD=X |
| sr_channel_reversal | USDJPY=X, EURUSD=X |
| sr_fib_confluence | USDJPY=X, EURUSD=X |
| sr_liquidity_grab | USDJPY=X, EURUSD=X |
| tokyo_nakane_momentum | EURUSD=X |
| tokyo_range_breakout_up | USDJPY=X, EURUSD=X |
| trendline_sweep | USDJPY=X, EURUSD=X |
| turtle_soup | USDJPY=X, EURUSD=X |
| v_reversal | EURUSD=X |
| vdr_jpy | EURUSD=X |
| vix_carry_unwind | EURUSD=X |
| vol_momentum_scalp | EURUSD=X |
| vol_spike_mr | EURUSD=X |
| vsg_jpy_reversal | USDJPY=X, EURUSD=X |

**Interpretation**: These strategies likely depend on `ctx.sr_levels`, 
`ctx.layer3`, `ctx.regime`, or `ctx.session` — all empty in raw harness. 
Re-run with Level 3 toggles (`inject_sr_levels`, `inject_layer_scores`, 
`inject_regime`, `inject_session`) to get real edge for these.

## クオンツ的解釈

⚠️ **これは raw harness の数字** (production の score gate / friction model 抜き)。
以下の前提で解釈すること:

- harness EV は **live EV より楽観的**(スプレッド/friction 未適用)
- 単独評価のため production の **candidate ranking 競合は反映されない**
- N≥30 + Wilson_lo>BEV floor は**最低条件**であって live promotion 判定ではない
- 0-fire 戦略は **戦略の問題ではなく ctx 不足**の可能性大 → Level 3 toggle on で再走

## 主要発見と production との乖離

### ⭐ USDJPY × trend_rebound — KB-defy 候補

raw harness 数字:
- **N=148, Wilson_lo=41.39%, EV=+0.52p, PF=1.231, Kelly=9.24%**
- Bonferroni-pass (Wilson_lo > 40%) かつ EV > 0 を**両方**満たす

production tier:
- `trend_rebound` は **UNIVERSAL_SENTINEL + PAIR_DEMOTED EUR_USD** ([[tier-master]])
- すなわち全ペアで sentinel 扱い + EUR_USD で明示的に demote

**矛盾点**:
- EUR_USD demotion は harness でも裏付け (Wilson_lo=35% < 40% BEV floor)
- ただし **USDJPY の raw edge は強い**にもかかわらず universal sentinel 状態
- production score gate / friction model が edge を消している可能性

**仮説 (要 Level 3 検証)**:
1. `inject_sr_levels=True` 等の toggle で再走 → harness 側でも raw edge が消えたら、SR/layer 依存で実は edge がなかったということ
2. toggle on でも edge が残るなら、それは **production の friction model が過剰にカット**している
3. ペア別評価が機能していない可能性 (universal sentinel の判定基準を見直すべき)

CLAUDE.md「KB は更新するもの、絶対のルールではない」原則に従い、**少なくとも Level 3 toggle on での再走 + 365日延長**で検証する価値がある候補。

### Bonferroni-pass + EV positive (3 cells)

| 戦略 × ペア | N | EV | PF | Kelly | production tier |
|---|---|---|---|---|---|
| USDJPY × trend_rebound | 148 | +0.52p | 1.23 | 9.24% | **UNIVERSAL_SENTINEL** ⚠️ |
| EURUSD × dt_bb_rsi_mr | 1068 | +0.15p | 1.07 | 3.06% | (要確認) |
| EURUSD × htf_false_breakout | 549 | +0.09p | 1.04 | 1.58% | (要確認) |
| EURUSD × session_time_bias | 504 | +0.17p | 1.06 | 2.48% | (要確認) |

### 高 PF / 小 N 候補 (Phase D 戦略チューニング元)

| 戦略 × ペア | N | EV | PF | Kelly |
|---|---|---|---|---|
| USDJPY × mtf_reversal_confluence | 136 | +0.47p | **1.39** | 8.86% |
| EURUSD × london_ny_swing | 37 | +0.82p | 1.28 | 8.16% |
| USDJPY × orb_trap | 38 | +1.27p | 1.27 | 10.72% |
| USDJPY × tokyo_nakane_momentum | 36 | +0.47p | 1.24 | 8.56% |

これらは N が Bonferroni 不足だが、raw EV / PF / Kelly が強く 365日延長で N≥30 に届く可能性あり。

### 0-fire 83 戦略の含意

半数 (54%) の cells が N=0 で発火しなかった。raw harness は ctx.layer/sr/regime が空辞書のため、これらに依存する戦略 (sr_channel_reversal, fib, ml_*, layer3-conditional 等) は評価不能で本来の edge が見えていない。

**Level 3 toggle on (`inject_sr_levels=True`, `inject_layer_scores=True`, `inject_regime=True`) で再走必須**。Level 3 検証時 sr_channel_reversal が 0→81 に増えたのは直接の実証。

## 次のステップ

1. **トリアージ Phase D**: USDJPY × trend_rebound を 365日 BT (raw + toggle on の両方) で再検証
2. **Level 3 sweep**: 全 152 cells を toggle ON で再走 → 0-fire 解消 + production parity 数字
3. **Production tier 整合性**: trend_rebound USDJPY の universal sentinel 判定の根拠 wiki/strategies/trend-rebound.md を再評価
4. **friction model gap**: spread/friction が raw EV をどれだけ削るか定量化 ([[friction-analysis]] 既存知見と並置)

## ファイル

- 結果 JSON: `raw/bt-results/all_strategies_sanity_20260430_155544.json`
- ハーネス: `modules/bt_vec_harness.py` (commit 51225f8)
- runner: `_bt_all_strategies_sanity.py` (gitignored)
- analyzer: `_bt_all_strategies_analyze.py` (gitignored)