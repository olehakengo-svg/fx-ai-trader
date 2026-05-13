# Regime-Gate Phase B2.5 司令塔 verdict (2026-05-13)

## 経緯

[Tier A verdict](regime-gate-tier-a-2026-05-12.md) 後、`app.run_daytrade_backtest` 直接呼出 pivot で全 family を 1 BT で網羅する Phase B2.5 を実行。Codex (`task-mp2skutt-hlx4pb`) は並列エージェントの `lib/` 消失で BLOCKED 報告したが、生成済 runner (`tools/regime_gate_full_bt.py`) + tests (`tests/test_regime_gate_full_bt.py`) は持ち越し成功。司令塔が直接実行し artifacts を回収。

| 項目 | 値 |
|---|---|
| BT 設定 | 3 pair (USDJPY/EURUSD/GBPUSD) × 365d × 15m MASSIVE |
| 実行時間 | ~25 min (PID 77171, 2026-05-13 12:03-12:48 JST) |
| pair baseline trades | USDJPY=2,130 / EURUSD=1,520 / GBPUSD=1,967 |
| **tagged_trades** | **5,617** |
| family universe / observed | **66 / 34** (約半数しか BT で発火していない 🚨) |
| **Shadow proposals** | **17** |
| **zero_trade_families** | **32** (BT/Live divergence 候補) |

## Top Shadow Proposals (Phase E 投入候補、優先順位順)

| # | proposal | N | WR | EV (pip) | PF | Wilson_lo | Kelly | 司令塔評価 |
|--:|---|--:|--:|--:|--:|--:|--:|---|
| 1 | **sr_anti_hunt_bounce__regime_CHOP** | 49 | **81.6%** | **+3.92** | **4.32** | 0.69 | **0.63** | 🟢 即 Shadow 投入候補、Phase 2 BH FDR survivor とも整合 |
| 2 | **streak_reversal__regime_TRENDING** | 105 | **75.2%** | +1.23 | **3.16** | 0.66 | **0.51** | 🟢 Phase 0.5 Tier B 90pip outlier の structural edge 確定 |
| 3 | post_news_vol__regime_CHOP | 39 | 71.8% | +1.15 | 2.34 | 0.56 | 0.41 | 🟢 |
| 4 | streak_reversal__regime_RANGING | 94 | 74.5% | +1.00 | 2.32 | 0.65 | 0.42 | 🟢 |
| 5 | vix_carry_unwind__regime_CHOP | 41 | 78.0% | +0.95 | 2.21 | 0.63 | 0.43 | 🟢 |
| 6 | streak_reversal__regime_CHOP | 273 | 67.8% | +0.80 | 2.00 | 0.62 | 0.34 | 🟢 大 N |
| 7 | trendline_sweep__regime_CHOP | 92 | 75.0% | +0.76 | 2.07 | 0.65 | 0.39 | 🟢 Phase 0.5 Tier B から昇格 |
| 8 | vix_carry_unwind__regime_TRENDING | 51 | 68.6% | +0.56 | 1.54 | 0.55 | 0.24 | 🟢 |
| 9 | turtle_soup__regime_CHOP | 31 | 67.7% | +0.33 | 1.43 | 0.50 | 0.20 | 🟡 N 境界、Wilson_lo 境界 |
| 10 | htf_false_breakout__regime_CHOP | 38 | 65.8% | +0.32 | 1.59 | 0.50 | 0.24 | 🟡 同上 |
| 11 | gbp_deep_pullback__regime_CHOP | 52 | 63.5% | +0.27 | 1.16 | 0.50 | 0.09 | 🟡 PF 弱い |
| 12-17 | session_time_bias × 3 / xs_momentum × 2 / trendline_sweep × RANGING | - | - | - | - | - | - | 🟡 large N だが EV 小 (≤+0.27)、shadow 試行価値あり |

→ **🟢 8 proposals が Phase E 直接候補**, **🟡 9 proposals は試行価値あり/慎重投入**。

## 🚨 重大発見 1: Zero-trade families (32 戦略 = 約半数の BT/Live divergence)

| カテゴリ | 戦略例 | 司令塔仮説 |
|---|---|---|
| **Tier A 矛盾** | stoch_trend_pullback (Tier A で N=316 → B2.5 で N=0) | Tier A は `_run` import、B2.5 は `app.run_daytrade_backtest` 直接呼出。**signal logic 差異あり** |
| **既知 MR / MTF** | bb_rsi_reversion / mtf_regime_*_cascade_scalp / mtf_reversal_confluence | MTF features 不在で signal 不発 (`feedback_ma_filter_breaks_mr` 系) |
| **session-specific** | london_breakout / london_close_reversal* / london_session_breakout / ny_close_reversal / gotobi_fix | session-window 内発火、365d BT で trigger 不足? |
| **commodities / cross** | gold_trend_momentum / gold_vol_break / vdr_jpy / eurgbp_daily_mr | XAU 除外影響 + cross pair (EURGBP) BT 範囲外 |
| **その他** | engulfing_bb / asia_range_fade_v1 / cpd_divergence / hmm_regime_filter / london_breakout / ma_regime_switch / pullback_to_liquidity_v1 / rsk_gbpjpy_reversion / sr_liquidity_grab / three_bar_reversal / tokyo_nakane_momentum / trend_rebound / vol_momentum_scalp / vsg_jpy_reversal / vwap_mean_reversion / pd_eurjpy_h20_bbpb3_sell | 個別 root-cause 必要 |

→ **Phase D で 32 戦略の BT/Live divergence RCA を並列 spawn 必要**。優先順位:
- 🔴 P0: stoch_trend_pullback (Tier A 矛盾、method bug 確定の確率最高)
- 🟠 P1: bb_rsi_reversion (memo `project_bb_rsi_bt_live_divergence_2026-05-12` 既出)
- 🟡 P2: その他 30 戦略 (まとめて 1 task、群として診断)

## 🚨 重大発見 2: Tier A 再現失敗 (methodology issue)

Phase B2.5 SUMMARY の Tier A Reproduction Benchmark:

| condition | Tier A 実測 | B2.5 実測 |
|---|---|---|
| baseline (stoch_trend_pullback) | N=316 / WR 60.4% / EV +0.01 | **N=0** |
| gated_TRENDING | N=104 / WR 64.4% / EV +0.11 | N=0 |
| gated_RANGING | N=51 / WR 47.1% / EV -0.39 | N=0 |
| gated_CHOP | N=161 / WR 62.1% / EV +0.07 | N=0 |

**両 BT path で signal 数が完全に違う**。Tier A `tools/bb_rsi_shadow_bt.py::_run` は app に monkey patch を当てて signal logic を限定する。本 B2.5 は `app.run_daytrade_backtest` 素呼びで、monkey patch なしで multi-strategy BT。stoch_trend_pullback が一方で発火し他方で発火しない = **default BT path に stoch_trend_pullback の signal が含まれていない** 疑い濃厚。

司令塔次アクション: stoch_pullback BT path 監査タスクを Codex に投入。

## ✅ ダウ理論 Gap 5 仮説: 強くサポート

- 17 Shadow proposals (NOT_CATASTROPHIC)
- **Top 8 が PF>1.5 + Wilson_lo>0.50 + Kelly>0.20** = ガッツリ edge
- 設計仮説と実測が一致:
  - streak_reversal (逆張り MR) が TRENDING で **WR 75.2% / PF 3.16** = 「思想は正、設計が誤」91% 戦略の **正しい運用環境** がついに判明
  - sr_anti_hunt_bounce が CHOP で edge 集中 = SR-weight Phase 2 BH FDR survivor の regime-specific 化
  - vix_carry_unwind が CHOP で edge = VIX carry 戦略の vol regime 整合

## Phase E 投入計画 (司令塔)

### Wave 1 (即投入 8 proposals, 🟢 Top 1-8)

1. sr_anti_hunt_bounce__regime_CHOP
2. streak_reversal__regime_TRENDING
3. post_news_vol__regime_CHOP
4. streak_reversal__regime_RANGING
5. vix_carry_unwind__regime_CHOP
6. streak_reversal__regime_CHOP
7. trendline_sweep__regime_CHOP
8. vix_carry_unwind__regime_TRENDING

→ Shadow runner 登録、Live runner 無触、H1 Gate (N≥30 / Wilson_lo≥0.40 / Bonferroni 通過) で Live 昇格判定。
→ 蓄積期間: ~30-60 日想定 (15m bar interval, regime-CHOP=半分の時間が valid window)。

### Wave 2 (慎重 9 proposals, 🟡 Top 9-17)

- N 境界 / Wilson_lo 境界の戦略
- Wave 1 結果次第で投入判断

### Wave 3 (BT/Live divergence 解消後)

- 32 zero-trade families の RCA 完了後、production live で動いている戦略を BT に乗せて regime gate を当てる
- 特に Tier A で動いた stoch_trend_pullback の復活が最優先

## Phase D Task Spawn 計画

| Task | Priority | 内容 |
|---|---|---|
| `bb-rsi-bt-live-divergence-rca` | P0 | (既存) bb_rsi BT 0 件 RCA |
| `stoch-pullback-tier-a-vs-b25-method-diff` | P0 | Tier A vs B2.5 で stoch_pullback signal 経路差分特定 |
| `zero-trade-bulk-rca` | P1 | 残り 30 戦略を群として診断、production live で動いているか確認 |

## Catastrophic ルール反省 (Phase B2.5 で確認)

実装:
1. `baseline_negative_no_edge`: baseline PnL≤0 → 全 gate REJECT (Tier A engulfing_bb 教訓、Phase B2.5 で 32 zero-trade family を救済) ✅
2. `pnl_sign_flip` ✅
3. `gate_N_lt_30` ✅
4. `pf_extreme_drop` ❌ **到達不能** (PF<0.5 ⇒ PnL<0 で sign_flip に必ず先取される、unit test で発見)

司令塔判定: `pf_extreme_drop` は次タスクで削除 or 統合。本 Phase B2.5 結果には影響なし。

## Verdict

**Gap 5 (regime gate) は Phase B2.5 で**:
- ✅ **17 Shadow 投入候補確定** (8 即投入級 + 9 慎重投入)
- ✅ **ダウ理論「regime 判定なしに戦略を回すのは設計欠陥」仮説の強い corroboration**
- 🔴 **32 戦略の BT/Live divergence が表面化** = Gap 5 検証の上位課題

Phase E (Shadow 投入) と Phase D (BT/Live RCA) を並走。Phase F (Gap 1 cross-pair) は Phase D 進捗待ち。

## 参照

- [Tier A verdict](regime-gate-tier-a-2026-05-12.md)
- Memory: `feedback_shadow_first_quant_architecture`
- Memory: `project_sr_weight_phase2_accept_2026_05_11` (sr_anti_hunt_bounce との整合性)
- Memory: `project_fxai_stale_test_backlog_2026_05_07` (pre-commit blocker)
- Phase B2.5 artifacts: `reports/regime_gate_phase_b2/` (kpi_per_family_gate.csv / sanity_verdict.csv / shadow_proposals.csv / zero_trade_families.csv / trade_log_baseline_{USDJPY,EURUSD,GBPUSD}.csv / trade_log_tagged.csv / SUMMARY.md)
