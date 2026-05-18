---
id: 20260518-1730-prime-v2-shadow-audit-w4eda
title: "[PRIME v2 discovery] W4-EDA 風 8 軸 audit: shadow EV+ 6 戦略 → 設計駆動 hypothesis 抽出 (m ≤ 30)"
owner: codex
status: queued
priority: P1
depends_on: 20260518-1700-prime-gate-v2-apply-verdicts
created_at: 2026-05-18T17:30:00+0900
roadmap_gate: "P1 (20260518-1530) の Task B 結果: 6 戦略 × 768 cell = 4608 hypothesis Bonferroni grid で **survivor=0**, FDR BH q=0.10 でも **survivor=0**。司令塔分析: 4608 hypothesis space は多重検定で殆ど検出不可能、α=1.085e-5 は実質的に N=20+ かつ WR=70%+ 級の極端な edge しか通さない。Bonferroni 罠 (memory [W3-3 S4 REJECT](memory/project_w3_3_s4_connors_raschke_queued.md): post-hoc selection で B 帯 cell が見つかっても採用不可) を回避するには `hypothesis space を design-driven で削減` する必要あり。Wave 6 風 pivot に該当 (memory [feedback_success_until_achieved](memory/feedback_success_until_achieved.md))。新方法論: W4-EDA-style 8 軸 audit (memory [W4-EDA 監査レポート形式](memory/feedback_w4_eda_audit_report_format.md)) を 6 EV+ shadow 戦略に適用し、各戦略について **設計駆動の 3-5 cell** を pre-register → m=18-30 (4608 ではなく) で Bonferroni を再評価する。"
rule: R1
related:
  - knowledge-base/wiki/sessions/prime-reeval-2026-05-18.md
  - knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md
  - research/prime_gate_v2_proposal.py
  - research/prime_reeval_task_b_cells.csv
  - modules/prime_gate.py
  - feedback_w4_eda_audit_report_format
  - feedback_audit_purpose_design_not_n
  - feedback_partial_quant_trap
  - feedback_label_empirical_audit
  - feedback_success_until_achieved
  - feedback_shadow_first_quant_architecture
  - feedback_spread_basis_for_mafe
  - feedback_exclude_xau
  - feedback_bt_must_use_massive
  - feedback_codex_schema_hallucination
  - feedback_codex_mock_test_trap
  - project_w4_eda_complete_2026_05_05
  - project_w3_3_s4_connors_raschke_queued
---

# 0. 背景 (Claude 司令塔 audit)

## 0.1 P1 観察

Task B (768 cell × 6 = 4608 hypothesis Bonferroni grid) は **完全 NULL**:

| strategy | best cell | N | WR | Bonf p×4608 | FDR q10 | uncorrected note |
|---|---|---:|---:|---:|:---:|---|
| ob_retest | OVERLAP_ATRQ1_ADXQ4_USD_JPY_BUY | 11 | 63.6% | 51 | N | Fisher p=0.0111 (uncorrected ◎) |
| orb_trap | OVERLAP_ATRQ3_ADXQ1_GBP_USD_SELL | 11 | 54.5% | 1.00 | N | Fisher p=0.0466 |
| dt_sr_channel_reversal | LONDON_ATRQ3_ADXQ4_USD_JPY_BUY | 4 | 75.0% | 1.00 | N | N<20, Wlo=0.301 |
| trend_rebound | TOKYO_ATRQ1_ADXQ1_USD_JPY_BUY | 1 | 100% | 1.00 | N | N=1 (noise) |
| wick_imbalance_reversion | TOKYO_ATRQ3_ADXQ1_GBP_USD_BUY | 5 | 100% | 1.00 | N | N=5 (noise) |
| gbp_deep_pullback | TOKYO_ATRQ4_ADXQ3_GBP_USD_BUY | 1 | 100% | 1.00 | N | N=1 (noise) |

## 0.2 司令塔の解釈

**Bonferroni 4608 hypothesis space は過剰補正の罠**。例えば `ob_retest` の uncorrected Fisher p=0.0111 は十分有意だが、4608 補正で p≈51 → 自動失格。

これは [W3-3 S4 REJECT](memory/project_w3_3_s4_connors_raschke_queued.md) の post-hoc selection 罠とは逆方向の罠: **多重検定補正で本物の edge も埋もれる**。

両罠を同時回避する古典的方法:
1. **Design-driven hypothesis 削減** — 768 cell から 3-5 cell に絞る
2. 絞り方は **設計の思想** に基づく (例: ob_retest は OB の retest を想定 → session 限定すれば overlap/london のみ、direction は BOTH ではなく Fade のみ等)
3. m を 18-30 に削減すれば Bonferroni α=0.05/30 = 0.00167、ob_retest uncorrected p=0.0111 は依然失格だが、ハードルが現実的になる
4. NULL でも「設計が誤」「N 不足」「思想が誤」の 3 分類で次アクション提示 ([feedback_w4_eda_audit_report_format](memory/feedback_w4_eda_audit_report_format.md))

## 0.3 入力データ

- **Shadow trades**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=10000` の `is_shadow=1` × `instrument != XAU_USD` × `outcome IN (WIN,LOSS)` ([feedback_exclude_xau](memory/feedback_exclude_xau.md))
- **MASSIVE parquet**: cell 切り直しに使う場合は `data/cache/massive/*.parquet` 必須 ([feedback_bt_must_use_massive](memory/feedback_bt_must_use_massive.md))
- **Regime features**: `regime` JSON 内の adx / atr_ratio / close_vs_ema200 / confidence

# 1. Pre-registered scope (LOCKED)

## 1.1 対象 6 戦略 (30 日 EV+ shadow から確定)

```
gbp_deep_pullback         N=11  WR=27.3%  Wlo=9.7%   EV=+7.75p   PF=1.93
orb_trap                  N=14  WR=50.0%  Wlo=26.8%  EV=+5.83p   PF=3.59
ob_retest                 N=40  WR=42.5%  Wlo=28.5%  EV=+2.68p   PF=1.40
trend_rebound             N=13  WR=46.2%  Wlo=23.2%  EV=+2.28p   PF=2.10
dt_sr_channel_reversal    N=38  WR=34.2%  Wlo=21.2%  EV=+1.13p   PF=1.18
wick_imbalance_reversion  N=32  WR=37.5%  Wlo=22.9%  EV=+0.23p   PF=1.04
```

## 1.2 各戦略 8 軸 audit テンプレート

[feedback_w4_eda_audit_report_format](memory/feedback_w4_eda_audit_report_format.md): per-strategy 8 軸結果を `Verdict / Rec / 思想 / 設計欠陥 / 再設計案` で構造化。

```markdown
### Strategy: <name>

**Verdict**: THESIS_VALID + DESIGN_VALID_NEEDS_N | THESIS_VALID + DESIGN_BROKEN | THESIS_INVALID

**1. 思想 (Thesis)**: <この戦略は何を狙うか? (例: ob_retest = Order Block の retest をエッジとして使う)>

**2. 8 軸監査**:
| 軸 | 値 | 評価 |
|---|---|:---:|
| 1. 全期間 shadow N / WR / Wilson_lo | <N>/<WR%>/<Wlo> | 🟢/🟠/🔴 |
| 2. spread-adjusted EV (entry_price 基準) | <EV>p | 🟢/🟠/🔴 |
| 3. Profit Factor | <PF> | 🟢/🟠/🔴 |
| 4. Kelly fraction | <K> | 🟢/🟠/🔴 |
| 5. 直近 30d vs 全期間 (drift detection) | <delta> | 🟢/🟠/🔴 |
| 6. session × direction WR matrix | best cell stats | 🟢/🟠/🔴 |
| 7. regime (ADX/ATR quartile) WR matrix | best cell stats | 🟢/🟠/🔴 |
| 8. Walk-Forward (3-fold) EV+ count | x/3 | 🟢/🟠/🔴 |

**3. 設計欠陥候補** (可能なら code path も特定):
- <bullet>

**4. 再設計案 (新 PRIME 候補 cell)**:
- **Cell 1**: <session=X, direction=Y, regime=Z>, predicate=<lambda condition>, expected_N>=20
- (最大 5 cell まで)
- Bonferroni α: 0.05 / (6 strategies × ≤5 cells) = 0.05 / 30 = 0.00167

**5. 候補 cell 実測**:
| cell | N | WR | Wlo | Fisher p | Bonf p×30 | FDR q10 | WF | Kelly | spread-adj EV | verdict |
|---|---:|---:|---:|---:|---:|:---:|---|---:|---:|:---:|
| ... | | | | | | | | | | SELECT / REJECT |

**6. PRIME v2 への組込み推奨**:
- SELECTED cell があれば `Tier A`/`Tier B` 判定 (Bonf p×30 < 0.0083 → A, < 0.05 → B)
- 推奨 lot_multiplier
- 元の `_PRIMES` 形式の lambda predicate
```

## 1.3 全体出力フォーマット

```markdown
# PRIME v2 Shadow Audit Report (2026-05-18)

## Total hypothesis space
- 6 strategies × <m_per_strategy> cells = m_total = <total ≤ 30>
- Bonferroni α = 0.05 / m_total

## Per-strategy audits
(6 sections, 1 per strategy)

## Aggregate verdict
| strategy | thesis | design | shadow N | best cell | verdict | proposed tier |
|---|---|---|---|---|---|---|
| ob_retest | VALID | ? | 40 | ? | ? | A/B/REJECT |
| ... |

## PRIME v2 candidate proposal
(deltas to apply to `modules/prime_gate.py` _PRIMES list, beyond P0 hot-fix v2 apply)

## Next steps
- If 0 candidates: enumerate "near miss" cells with N>=10 + uncorrected p<0.05 for further shadow N accumulation (future re-eval)
- If 1+ candidates: queue separate apply task `20260518-XXXX-prime-v2-add-candidates`
```

## 1.4 Hypothesis space LOCK (post-hoc bias 回避)

各戦略について **5 cell 以内** を **報告書で先に列挙してから** 統計を計算。
全 30 cell を超える grid 探索は NULL 上で誘導されたとしても禁止 (Task B で既に exhausted)。

Per strategy cell selection 原則:
- Cell 1: aggregate best (現状の overall stats)
- Cell 2-3: session × direction で WR≥50% かつ N≥10 を満たす上位 2 cell
- Cell 4-5: regime quartile (ADX or ATR) で WR≥50% かつ N≥10 を満たす上位 2 cell

合計 m ≤ 5 / strategy × 6 = 30 (Bonferroni α=0.05/30=0.00167)

# 2. テスト要件

## 2.1 Sanity

`tools/prime_v2_shadow_audit.py` を新規作成 (再現可能性のため):
- Render API fetch + filtering + 8-axis stats + Bonferroni
- m_per_strategy / m_total / α 自動算出
- 出力: stdout に report + `research/prime_v2_audit_2026_05_18.md` + `research/prime_v2_audit_cells.csv`

## 2.2 既存テスト

```bash
python3 -m pytest tests/ -x -q   # regression 確認
```

## 2.3 監査ロジックの内部一貫性

Sanity test (`tests/test_prime_v2_audit_invariants.py`):
1. `test_total_hypothesis_count_at_most_30` — 全戦略の cell 合計が ≤30
2. `test_each_strategy_at_most_5_cells` — 個別戦略の cell 数が ≤5
3. `test_bonferroni_alpha_matches_m_total` — α = 0.05 / m_total

# 3. KB 更新 (同一 commit)

- `knowledge-base/wiki/sessions/prime-v2-shadow-audit-2026-05-18.md` (新規) — 8-axis audit 全結果
- `knowledge-base/wiki/decisions/prime-gate-promotion-path-bug-2026-05-18.md` に "v2 shadow audit 完了 ✓" 追記
- 採用候補が 0 件でも (NULL) 完了報告として記録

# 4. 完了条件 (DoD)

- [ ] `tools/prime_v2_shadow_audit.py` 作成
- [ ] 6 戦略 × ≤5 cell の 8 軸 audit 完了、verdict 出力
- [ ] `research/prime_v2_audit_2026_05_18.md` 生成
- [ ] `research/prime_v2_audit_cells.csv` 生成
- [ ] sanity test 3 件 PASS
- [ ] 既存 test suite regression なし
- [ ] verdict:
  - 採用候補 ≥1: 別 apply task (`20260518-XXXX-prime-v2-add-candidates`) の queue 提案
  - 採用候補 0: NULL 報告 + "future re-eval @ shadow N+30d" の near-miss リスト
- [ ] git commit + push

# 5. Out of scope

- `modules/prime_gate.py` の修正 (採用候補確定後に別 task)
- 新 EDGES の再計算 (P1 で更新済 EDGES を使用)
- demo_trader.py の変更
- 4608 grid の再実行

# 6. 注意 (Codex)

- [feedback_audit_purpose_design_not_n](memory/feedback_audit_purpose_design_not_n.md): 設計監査で N 不足を理由に「redesign 除外」は inverted logic。設計欠陥あれば N に関係なく修正→shadow で N 蓄積が正順
- [feedback_label_empirical_audit](memory/feedback_label_empirical_audit.md): 「ロジック問題ない?」演繹禁止、shadow data × cell 実測クエリで答える
- [feedback_partial_quant_trap](memory/feedback_partial_quant_trap.md): N/WR/EV だけで結論禁止。8 軸全列必須
- [feedback_spread_basis_for_mafe](memory/feedback_spread_basis_for_mafe.md): EV 計算は **entry_price 基準** で spread 考慮 (signal_price ではない)
- [feedback_w4_eda_audit_report_format](memory/feedback_w4_eda_audit_report_format.md): 🔴🟠🟢 emoji + 太字 evidence ハイライト + Gate 状態テーブル
- [feedback_success_until_achieved](memory/feedback_success_until_achieved.md): 採用候補 0 でも near-miss list + 「shadow N+30d で再評価」schedule 提案で完了
- [feedback_shadow_first_quant_architecture](memory/feedback_shadow_first_quant_architecture.md): BT による「絶対 Kelly>=0.40」要求は禁止。shadow が estimator
- [feedback_codex_schema_hallucination](memory/feedback_codex_schema_hallucination.md): EDGES 再計算するなら必ず実 shadow data から、推測禁止
- 各戦略の **思想 (thesis)** は戦略本体のコメントから引用 (推測禁止)。判明しない場合は `THESIS_UNKNOWN` でマーク
