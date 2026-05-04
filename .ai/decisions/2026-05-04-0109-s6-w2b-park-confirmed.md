---
date: 2026-05-04
tasks:
  - 20260504-0050-s6-w1p0-production-rerun (REJECT, contract mismatch)
  - 20260504-0000-s6-w2b-pre-reg-bt (DONE, all REJECT/INSUFFICIENT)
verdict: 🛑 **S6 strategy 族 PARK 確定**
rule: R1
gate: 新戦略族 S6 — LIVE 露出なし、edge ゼロ確定
---

# S6 Chart Pattern Strategy 族 — PARK 確定

## Verdict

**S6 PARK** — W2b pre-reg BT で 24 verdict 全 REJECT/INSUFFICIENT。Promote 候補ゼロ。

## W2b verdict 内訳

| Candidate | Splits 評価 | 結果 |
|---|---|---|
| C1 (`ascending_triangle` etc.) | 4 splits (OOS_1, WF_1-3) | 全 INSUFFICIENT (N=3-13、OOS sample size 不足) |
| C2 (`bull_flag` etc.) | 4 splits | 全 INSUFFICIENT (N=1-5) |
| C3 (`double_bottom`/`double_top`) | 4 splits | OOS_1/WF_3 REJECT (N=58, PF=1.18, weak), WF_2 REJECT (N=38, PF=0.57), WF_1 INSUFFICIENT |

合計: **PROMOTE 0 / SHADOW 0 / REJECT 6 / INSUFFICIENT 18**

intrabar resolve sensitivity: SL_FIRST/TP_FIRST identical → favorable interpretation の余地なし。

## Quant 観察 — bb_squeeze 関連教訓と類似

C3 (double_bottom/top) が N=58 で REJECT された pattern は、A2-alt の bb_squeeze_breakout が N=24 で Insufficient だった「数字は良いが N 不足」とは対照的:
- C3: N=58 充分だが PF=1.18 弱く WF_2 で reverse (PF=0.57) → 真の reject
- bb_squeeze: N=24 不足だが WR=75% PF=4.87 → 365日延長余地

→ **chart pattern geometry 自体に edge なし** (W2 全 12 patterns REJECT, W2b top 3 candidates も REJECT) が確定。

## S6 W1P0 Production Rerun — REJECT (contract mismatch)

production run 自体は exit 0, 45.5s で成功だが task verification contract に不整合:
- 20 tests collected (期待 29)
- `test_fixture_replay` 関数不在
- fixture 13 行 (期待 30 行)

infra タスクの contract 違反であり、S6 PARK 結論には影響しない。低優先度 cleanup。

## Roadmap impact

S6 strategy 族の月利100% 寄与は **ゼロ確定**。Wave 3 sweep 不要、Wave 4 LIVE 露出 不可。

PARK 状態で:
- 検出器コード (`tools/s6_chart_pattern_detector.py`) は research artifact として保持
- BT 結果 DB (`data/chart_patterns.db`) は historical reference
- Wave 2c regime deepdive はオプション (VIX/DXY data sourcing 条件下のみ)

## Next

S6 関連の能動 task 終了。月利100% ロードマップへの寄与は他 strategy 族 (sr_channel_reversal Promote 候補, Tier 1 LIVE 構造修正等) に集中。
