# EDGE.md — Cell-aware Routing Manifest (v0.1)

**Spec**: [[manifests/SPEC]]

```yaml
---
version: "0.1"
classifier: "v6"
classifier_source: "[[phase4c-v6-classifier-stability-result-2026-04-24]]"
edges_updated_at: "2026-04-26T00:00:00Z"
edges: []
---
```

## Overview

Cell-aware routing manifest. `(strategy, cell3d)` 単位で entry を許可・ブロック・
Kelly fraction 適用. cell3d は v6 classifier の Regime × Vol × Session 3D 空間.

初期状態は `edges: []` (no-op). Phase 4d / Track D2 で SURVIVOR / REJECT が
Bonferroni 通過した時点で entry を追加する.

## Routing values

| value | semantic |
|---|---|
| NONE | 情報のみ。本番ロジック不変 |
| BLOCK | `_is_promoted()` が False を返す。OANDA 送信せず demo 継続 |
| KELLY_HALF | OANDA 送信、lot × 0.5 |
| KELLY_FULL | OANDA 送信、full Kelly |

## Status

| value | 数学的条件 |
|---|---|
| SURVIVOR | N≥30, Wilson_lo>BEV+0.03, Fisher<α_cell, Kelly>0.05, WF same-sign |
| CANDIDATE | N≥30, Wilson_lo>BEV+0.03, Kelly>0.05 |
| REJECT | N≥30, Wilson_hi<BEV-0.03, Fisher<α_cell, Kelly<-0.05 |
| REJECT_CANDIDATE | direction negative だが Bonferroni 未通過 |

## Why cell × strategy

既存 `_FORCE_DEMOTED` / `_PAIR_PROMOTED` は `(strategy, pair)` の 2 軸. v6 classifier
で得た 3D cell (regime × vol × session) の負 edge を反映するには (strategy, cell3d)
の 3 軸が必要. EDGE.md は **DESIGN.md スタイル** で機械可読 routing と人間可読
rationale を 1 ファイルに集約し、source pre-reg と直結.

## Operational notes

- Linter (`tools/edge_md_lint.py --check`) は pre-commit hook で自動実行.
- Routing は static list (`_FORCE_DEMOTED` 等) の **後** に評価される. 既存 list が
  先勝ち = 既存挙動は変わらない.
- `routing_table.json` は EDGE.md から `edge_md_export.py` で生成. 手動編集禁止.
- `expires_at` 切れの edge は linter エラーになる (90 日 TTL 推奨). 再検定が要る.

## References

- [[manifests/SPEC]] (本 manifest の schema)
- [[phase4c-v6-classifier-stability-result-2026-04-24]] (v6 classifier 15 PHASE_D_CELLS)
- [[phase4d-v6-cell-edge-test-result-2026-04-24]] (live 16d edge test, all INSUFFICIENT)
- [[phase4b-cell-edge-test-result-2026-04-24]] (v5 cell edge test, 2 REJECT)
