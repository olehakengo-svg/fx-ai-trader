# Lesson: Pooled Metrics で観測される "edge" は交絡を疑え (2026-04-23)

## 原則
**プール集計で得られる significance (p値、effect size) は、group identifier との交絡チェックを通過しない限り意味を持たない。** 特に以下の 2 条件が揃ったら赤信号:

1. 特徴量 X が group 内で低分散 (CoV < 20%)
2. outcome Y も group 間で既知の差 (= group 識別力) を持つ

→ aggregate の X-Y 相関は **group 識別子 → X かつ group 識別子 → Y** の confounding 構造そのもの。

## 実例 (2026-04-23 — spread_at_entry)
| 指標 | Aggregate | Per-pair |
|---|---|---|
| WIN-LOSS spread 差 | -0.079p (p=1.9e-5) | USD_JPY -0.005, EUR_USD -0.000, GBP_USD -0.004 |
| 解釈 | 「低 spread entry ほど TP-hit 率高い」 | **ペア内では 0** |

`spread_at_entry` は BT/本番で摩擦定数をそのまま書き込んでおり、EUR_USD 100% が 0.8, GBP_USD 99.6% が 1.3 という pair-constant。aggregate で見える相関はペア識別子の proxy でしかない。

詳細: [[spread-at-entry-confounding-2026-04-23]]

## 判定プロトコル (新規採用)
特徴量 F を filter 候補として検討する前に以下を実行:

```python
# Step 1: within-group CoV
for group in groups:
    vals = [f for f in data if f.group == group]
    cov = std(vals) / mean(vals)
    if cov < 0.2:
        flag_constant_per_group(F, group)

# Step 2: segment significance test
for group in groups:
    within_p = test(F, Y, conditioned_on=group)

# Step 3: if aggregate p < 0.001 but all within_p > 0.05 → CONFOUNDED
```

## 本ケースから学んだこと
1. **handover の Research 候補も鵜呑みにしない** — prior analysis の segmentation 不足を検出した
2. **Simpson's paradox は p=1.9e-5 でも発生する** — low p-value は truthful signal の保証ではない
3. **特徴量の origin を確認する** — "market spread at entry time" という命名だが、実装は "pair-level constant lookup" だった

## 関連教訓
- [[lesson-all-time-vs-post-cutoff-confusion]] — window 分解の重要性
- [[lesson-tier-classification-data-mixing]] — shadow/live 混在で集計が歪む
- [[lesson-wr-only-fd-flag]] — 一指標の significance で判断しない

## 適用ルール
CLAUDE.md 判断プロトコルに追加:
> 特徴量 F による filter 提案は **within-pair / within-strategy での significance** を必須とする。aggregate p-value は参考値のみ。
