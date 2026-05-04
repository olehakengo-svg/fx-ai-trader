---
date: 2026-05-03
task: 20260503-2310-r2-15cell-modules-lock-pr
verdict: ACCEPT (Codex 規律遵守) / BLOCKED (実装) — `_QUICK_HARVEST_EXEMPT` SSOT coupling
rule: R2
gate: Gate 0 ACCEPT 達成 — scope 拡張 task で完成必要
---

# R2 15-cell LOCK 実装 — 3rd blocker (`_QUICK_HARVEST_EXEMPT` SSOT coupling)

## Verdict

**ACCEPT (Codex deliverable)** — 仕様通り 3 set (`_PAIR_DEMOTED`, `_PAIR_PROMOTED`, `_ELITE_LIVE`) 編集 + `tier-master.{md,json}` regenerate を実行、`tier_integrity_check.py --check` を走らせて WARN=2 を検出、partial commit を拒否。

**BLOCKED (実装完成)** — `_QUICK_HARVEST_EXEMPT` set に残った 2 cell が integrity WARN を発生。

## Working tree 状態

```
modules/demo_trader.py      (uncommitted, 3 set edited)
knowledge-base/wiki/tier-master.md   (uncommitted, auto-regen)
knowledge-base/wiki/tier-master.json (uncommitted, auto-regen)
```

commit 未作成。Codex は WARN=2 で deploy-ready でないと判断。

## Integrity check 出力

```
ELITE_LIVE:       1 strategy
PAIR_PROMOTED:    9 entries
PAIR_DEMOTED:     32 entries
ERROR:            0
WARN:             2
  - QUICK_HARVEST_EXEMPT (gbp_deep_pullback, GBP_USD) not in ELITE/PAIR_PROMOTED
  - QUICK_HARVEST_EXEMPT (vix_carry_unwind, USD_JPY) not in ELITE/PAIR_PROMOTED
```

`modules/demo_trader.py:6451-6459` に `_QUICK_HARVEST_EXEMPT` 残置。

## Counterfactual 確認

Codex は `r2_tier1_hour_bucket_extension --dry-run` を再実行:
- Verdict: ACCEPT
- raw Kelly: -0.1326 → -0.0028 → **+0.0094** (Gate 0 ACCEPT 達成)
- MC60d: 0.8650 → 0.0090 → **0.0030**

→ counterfactual 評価は健全、coupling 問題のみ。

## 真の SSOT 構造 (3 段の blocker から判明)

`modules/demo_trader.py` 内 tier-related sets:

| # | Set | Line | Purpose |
|---|---|---|---|
| 1 | `_PAIR_DEMOTED` | 6158 | runtime gate |
| 2 | `_PAIR_PROMOTED` | 6209 | promote tier |
| 3 | `_ELITE_LIVE` | unknown | elite tier |
| 4 | `_QUICK_HARVEST_EXEMPT` | 6451- | QH exemption (TP quick-harvest skip) |
| 5 | `_STRATEGY_LOT_BOOST` | unknown | lot boost (`gbp_deep_pullback` 含む、integrity 非ブロック) |

tier downgrade は **複数 set の atomic alignment** が必要。

## 次の必要 scope

scope を `_QUICK_HARVEST_EXEMPT` に拡張、2 cell を削除:

```python
# modules/demo_trader.py:6451 削除
- ("gbp_deep_pullback", "GBP_USD"),

# modules/demo_trader.py:6459 削除
- ("vix_carry_unwind", "USD_JPY"),
```

`_STRATEGY_LOT_BOOST` の `gbp_deep_pullback` は integrity 非ブロックだが、tier 整合性のため同 commit で削除するか別 task で扱うか判断。

## Roadmap impact

Gate 0 ACCEPT 経路は **counterfactual 上完成**、**実装は scope 拡張 1 task で完了見込み**。最小 path:

1. **`r2-15cell-qh-exempt-scope-extension`** (next task) — `_QUICK_HARVEST_EXEMPT` 削除 + 既存 working tree 変更を継承して commit
2. Claude/user review → push → Render auto-deploy
3. 7d post-merge audit (`r2-postmerge-audit-2026-05-10`)

## Next task

scope 拡張 task を起草し、Codex は (a) 既存 working tree 変更を継承するか (b) クリーンスタートで全 4 set 編集するか選択肢付き。

clean start 推奨 (再現性確保)。
