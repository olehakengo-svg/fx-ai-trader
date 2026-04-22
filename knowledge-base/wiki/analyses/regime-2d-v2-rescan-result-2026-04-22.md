# Regime 2D v2 Rescan Result (2026-04-22)

**Companion to**: [[regime-2d-v2-preregister-2026-04-20]]
**Data**: post-backfill Render snapshot (2026-04-22 08:18 UTC), 2,583 non-XAU trades, 全件 mtf_regime labeled (639 既存 + 1,944 backfill)
**Raw outputs**: `raw/analysis/regime-2d-v2-rescan-2026-04-22/{matrix_all,asymmetry_strict,hypothesis_check,gate_candidates,sanity_check,summary}.{csv,json}`

---

## 結論

**Pre-registered gate を通過する asymmetry cell = 0件**。Decision Rules §4 に従い **NO-OP（新規実装提案なし）**。

これは pre-registration 時点で事前予測した結果と整合する:
- 258 cells (43戦略 × 6 regime × direction) の多重検定枠で Bonferroni 補正後 α=1.94e-4 を要求
- post-cutoff N=1,236 を 133 observed cells に分解 → cell 中央値 N ≈ 9
- 本日の `tp-hit-quant-analysis-2026-04-20` で 107 条件 Bonferroni 通過 5 件が DSR null FP=5.4 と family-wise random 相当と判明していたのと同じ罠

---

## 数値サマリ

| 指標 | 値 |
|---|---|
| trades (post-cutoff, FX, closed, labeled) | **1,236** |
| observed cells | **133** / 258 pre-registered |
| strategies observed | **35** / 43 pre-registered |
| regimes observed | **4** (range_tight / range_wide / trend_up_strong / trend_up_weak) |
| **K_effective (独立 Fisher tests)** | **2** |
| α_strict (Bonferroni K=2) | 2.50e-02 |
| min cell N gate | 50 |
| min \|ΔWR\| gate | 10pp |
| **Gate-passing candidates** | **0** |

### K_effective = 2 の意味
Pre-register §3 は「独立 Fisher test 数に応じた Bonferroni」を採用。N≥50 を満たす cell pair が 2 組しかなかったため、K=2。これは **cell-coverage gap** が構造的であることを示す — `trend_down_*` (217件) も `range_wide` (520件) も、strategy-level に切ると N≥50 を満たす組み合わせがほぼ存在しない。

---

## Hypothesis Check サマリ (7 cells evaluated)

| strategy | regime | N_buy | N_sell | ΔWR (pp) | predicted sign | observed sign | match |
|---|---|---|---|---|---|---|---|
| bb_rsi_reversion | range_tight | 48 | 56 | +6.5 | 0 | +1 | — (0予測) |
| ema_trend_scalp | trend_up_strong | 56 | 58 | +0.6 | +1 | +1 | ✅ |
| ema_trend_scalp | range_tight | 86 | 91 | +0.05 | 0 | +1 | — (0予測, 事実上 flat) |
| engulfing_bb | range_tight | 35 | 22 | −3.2 | 0 | −1 | — (0予測) |
| fib_reversal | range_tight | 23 | 26 | +27.6 | 0 | +1 | — (0予測, 小-N fluke疑) |
| sr_channel_reversal | range_tight | 26 | 34 | −15.2 | 0 | −1 | — (0予測) |
| stoch_trend_pullback | range_tight | 34 | 40 | +14.0 | 0 | +1 | — (0予測) |

**非ゼロ予測 (N=1) のうち sign 一致 1/1**. ただし単一 cell では意味のある検定にならない。

---

## Sanity Check: 既存 REGIME_ADAPTIVE 設定

| strategy | verdict | 詳細 |
|---|---|---|
| **bb_rsi_reversion** | ✅ PASS | trend_up_strong で BUY WR=62.5% (N=8) > SELL WR=15.4% (N=26)、符号一致 (+1 vs expected +1) |
| **fib_reversal** | ❌ FAIL | trend_up_strong で BUY WR=20.0% (N=10) vs SELL WR=11.1% (N=9)、observed +1 vs expected **−1** (家族マップは RA: tu=MR fade → SELL>BUY を期待) |

### fib_reversal FAIL の解釈
- N=10/9 は小-N （Wilson 95%CI: BUY [5.7, 51.0], SELL [2.0, 43.5] — CI 完全重複）
- 符号反転は **noise 範囲内**と判定
- ただし [[lesson-partial-quant-trap]] と整合的: 小-N BT を ground truth と誤認する危険
- **アクション**: 現状の REGIME_ADAPTIVE 設定（fib_reversal: tu=MR, td=TF）は変更しない。post-cutoff N が各 regime で ≥30 に蓄積した時点で Audit B パターンで再検証

---

## Decision Rules §4 適用

| Pre-register §4 branch | 本実行結果 |
|---|---|
| Any cell passes N≥50 + \|ΔWR\|≥10pp + p<α_strict | **0 件 → NO-OP branch 選択** |
| Additional candidates found | N/A |
| Sanity check全PASS | NO (fib FAIL) — ただし小-N noise 内 |

**決定**: REGIME_ADAPTIVE 拡張・新規 regime-routed gate の実装提案は**しない**。

---

## クオンツ所感（月利100%目標との整合）

1. **記事「2027年要件 = レジーム適応」は理論的に魅力だが、現データ量では統計的にサポートされない**
   - pre-register 時の私のクオンツ判断 (ln(258)×√(1/7.5) → max 5-8pp の見せかけ) と一致
   - 真のエッジを検出するには cell N ≥ 100 / N_strategies × N_regimes × 2 の蓄積が必要 → 各戦略で post-cutoff N ≥ 4,800 相当

2. **真の P1 は [[spread-entry-gate-preregister-2026-04-22]] (Path B)**
   - p=1.94e-05 は Bonferroni α の 2桁下 — 検出力が Regime 2D v2 と桁違い
   - 全戦略横断エッジなので N 希釈が発生しない
   - 4原則②「スプレッド異常=デスゾーン」と理論的整合 (non-data-snoop prior)

3. **Regime 2D v2 方針は当面凍結が妥当**
   - Data shortage が解消するまで ( ≥ 数ヶ月の post-cutoff 蓄積) 同じ rescan で再評価可能
   - 本文書を再実行のチェックポイントとして使用

4. **fib_reversal の REGIME_ADAPTIVE は据え置き**（N<30 の FAIL は reactive change の格好の材料だが lesson-reactive-changes 回避）

---

## Related

- Preregister: [[regime-2d-v2-preregister-2026-04-20]]
- Parallel track: [[spread-entry-gate-preregister-2026-04-22]]
- Backfill prerequisite: [[../raw/mtf-backfill-guide-2026-04-20|mtf-backfill-guide]]
- Lesson: [[lesson-partial-quant-trap]], [[lesson-reactive-changes]]
- TP-hit analysis (same-day): [[tp-hit-quant-analysis-2026-04-20]]

---

## Reproduction

```bash
# On Render Shell:
curl -s "https://fx-ai-trader.onrender.com/api/demo/trades?limit=5000" > /tmp/trades.json
python3 scripts/regime_2d_v2_rescan.py --trades-json /tmp/trades.json --output-dir /tmp/fx-regime-2d-v2

# Local (if prod data mirror available):
python3 scripts/regime_2d_v2_rescan.py --trades-json /tmp/trades_post_backfill.json --output-dir /tmp/fx-regime-2d-v2
```
