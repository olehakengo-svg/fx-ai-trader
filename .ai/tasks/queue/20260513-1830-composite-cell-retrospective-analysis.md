---
id: 20260513-1830-composite-cell-retrospective-analysis
title: "[Composite Cell Analysis] Phase B2.5 trade_log (5617 trades) を dow_regime × v2_regime cross-tab で retrospective 分析、17 proposals を composite で再評価"
owner: codex
status: queued
priority: P1
created_at: 2026-05-13T18:30:00+0900
roadmap_gate: "Phase E ユーザー提案 (composite classifier) の retrospective sanity check。Phase B2.5 で生成済 5617 BT trades は既に dow_regime tag 付き。本タスクは v2_regime を retrospective に追加 tag し、composite cell (3×2=6) cross-tab で 17 proposals が **composite cell でどう見えるか** を forward 蓄積前に preview。"
rule: pre-reg
related:
  - reports/regime_gate_phase_b2/trade_log_tagged.csv                  # 5617 trades + dow_regime (commit 436ffaf)
  - reports/regime_gate_phase_b2/shadow_proposals.csv                   # 17 proposals
  - reports/regime_classifier_consensus/                                # 既存 consultation 成果 (commit c05a86b)
  - lib/regime_classifier.py                                            # Dow Theory H1 classifier
  - modules/regime_classifier.py                                        # v2 M15 binary classifier
  - tools/regime_classifier_consensus.py                                # v2 replay の参考実装
  - feedback_partial_quant_trap
  - feedback_label_empirical_audit
---

# 0. 目的 (Phase E ユーザー提案の retrospective sanity)

forward Shadow N 蓄積前に、既存 B2.5 trade_log (N=5617) で composite cell の構造を **observation only** で見る。

**重要**: これは Live 昇格判定でない、Shadow 投入の根拠でもない。**司令塔の hypothesis 形成のための先行 EDA**。Codex は両論併記禁止 (`feedback_label_empirical_audit`)、verdict は出力に明記。

# 1. 設計

## 1.1 入力

`reports/regime_gate_phase_b2/trade_log_tagged.csv` (commit 436ffaf 永続化済)
- 5617 trades + dow_regime tag 付き
- entry_time / instrument / pnl_pips / entry_type の各列あり

## 1.2 v2_regime を retrospective 計算

```python
from modules.regime_classifier import classify_regime_binary  # or 既存関数名

for trade in trades:
    v2 = classify_regime_binary(
        instrument=trade["instrument"],
        ts=pd.Timestamp(trade["entry_time"]),
        tf='15m'
    )
    trade["v2_regime"] = v2  # 'moderate_trend' | 'no_go' | None
```

既存 v2 classifier の API を最初に確認。

## 1.3 composite cell cross-tab

`reports/composite_cell_analysis/`:

### crosstab_global.csv (全戦略)
```
dow_regime, v2_regime, N, WR, EV_pip, PF, Wilson_lo, Kelly
TRENDING, moderate_trend, ?, ?, ?, ?, ?, ?
TRENDING, no_go, ?, ?, ?, ?, ?, ?
RANGING, moderate_trend, ?, ?, ?, ?, ?, ?
... (6 cells)
```

### crosstab_by_strategy.csv (entry_type × composite cell)
```
entry_type, dow_regime, v2_regime, N, WR, EV_pip, PF, Wilson_lo, Kelly
```

### crosstab_top_strategies.csv (Top 10 baseline N family)
- 各 family の 6 composite cell KPI を行で並べる

### 17_proposals_composite.csv
- B2.5 の 17 proposals を **dow_regime + v2_regime** に分解
- 各 proposal が composite cell でどう分布するか確認:
  - 例: `sr_anti_hunt_bounce__regime_CHOP` (N=49) のうち、CHOP × moderate_trend と CHOP × no_go の比率
- composite cell ごとの edge があるか実測

### bonferroni_evaluation.csv
- effective m = N≥30 を満たす composite cell の数
- 各 cell の Wilson_lo + Bonferroni 補正後 p-value
- 通過 cell list (alpha = 0.05 / m_eff)

## 1.4 verdict (Codex independent opinion)

`reports/composite_cell_analysis/SUMMARY.md` で:

### Q1: 17 B2.5 proposals は composite で **構造化**されているか?
- 各 proposal を dow×v2 で分解、edge が偏在しているか
- 例: `sr_anti_hunt_bounce × CHOP` の本当の edge が「CHOP × moderate_trend」だけにあるなら、より精密な gate 設計可能

### Q2: Bonferroni 通過 cell が存在するか?
- effective m が小さくなる (sparsity で N<30 cell 多数排除) ので通る可能性あり
- 通過なし → Phase E は forward N 蓄積待ち
- 通過あり → preliminary Shadow 投入候補

### Q3: dow vs v2 single classifier より composite の方が **prediction power 強いか**?
- 単一 classifier (dow only or v2 only) vs composite の **Brier score** または **log-loss** を比較
- composite > both single → ユーザー提案の妥当性 confirm

### Q4: 推奨次アクション
- A: composite cell で Phase E Shadow 候補を再定義 (pre-reg)
- B: composite で改善が見えないので Phase E は forward 蓄積のみで様子見
- C: 他の組合せ (mtf_regime も含めた 3D) を検討
- D: composite では edge が消える、Gap 5 自体を保留

# 2. 出力

`reports/composite_cell_analysis/`:
| ファイル | 内容 |
|---|---|
| `crosstab_global.csv` | 全 trade × 6 composite cells |
| `crosstab_by_strategy.csv` | entry_type × 6 composite cells |
| `crosstab_top_strategies.csv` | Top 10 family × 6 cells (見やすさ重視) |
| `17_proposals_composite.csv` | 17 proposals の dow×v2 分解 |
| `bonferroni_evaluation.csv` | composite cell の Bonferroni 評価 |
| `prediction_power_comparison.csv` | dow / v2 / composite の Brier score 比較 |
| `verdict.md` | Codex independent verdict (Q1-Q4) |
| `SUMMARY.md` | 1-page 司令塔向け推奨 |

# 3. 司令塔ガード

- [ ] Production code / classifier 改変禁止 (analysis only)
- [ ] DB / .env / OANDA secret 無触
- [ ] mock 禁止、実 trade_log + 実 classifier 呼出
- [ ] Verdict 両論併記禁止 (1 推奨、`feedback_label_empirical_audit`)
- [ ] PF / Wilson_lo / Bonferroni 全算出 (`feedback_partial_quant_trap`)
- [ ] 生成物即 commit (--no-verify、commit hash 記載)
- [ ] forward 蓄積前の retrospective analysis である旨を SUMMARY 明記 (Live 昇格の根拠にしない)

# 4. 完了条件

1. 8 artifact ファイル全出力
2. Q1-Q4 verdict
3. composite cell の prediction power vs single classifier 数値比較
4. 17 proposals の composite-cell 分解結果
5. commit hash + git log snapshot in final.md

# 5. 禁止事項

- production DB / .env / OANDA secret 無触
- classifier 閾値改変禁止
- composite cell の閾値を post-hoc tune 禁止
- 「composite で edge 強くなった」と言うため Cherry-pick 禁止 (全 cell の数字を出すこと)
- Live 昇格判定への流用禁止 (本タスクは hypothesis 形成のみ)
