---
date: 2026-05-03
task: 20260503-1900-s6-chart-pattern-detector-w1p0
verdict: ACCEPT
rule: R2 (新戦略族 S6 Wave 1 Phase 0、検出器のみ無 LIVE 露出)
gate: 新戦略族 S6 Wave 1 Phase 0 (LIVE 影響なし)
---

# S6 Chart Pattern Detector W1P0 — ACCEPT

## Status

検出器+ラベル化のみ完了、LIVE/Shadow 影響なし。

## Deliverables

- `tools/s6_chart_pattern_detector.py` — 12 patterns 検出器 (順張り 6 + 逆張り 6)
- `tools/s6_run_w1p0.py` — runner
- `tests/test_s6_chart_pattern_detector.py` — 20 unit tests pass
- `tests/fixtures/manual_chart_pattern_labels.csv` — regression fixtures
- `wiki/strategies/s6-chart-pattern.md` — strategy doc
- `wiki/decisions/s6-w1p0-detector-2026-05-03.md` — Codex decision doc
- `data/chart_patterns.db` — SQLite store (gitignored)

## Quant evidence (Phase 0 = detector counts only)

USDJPY M5 12年 (~903K bars) で **22,094 signals 総計**:

| Pattern | N | Median duration | P95 height ATR |
|---|---:|---:|---:|
| double_top | 4,869 | 8 | 3.61 |
| double_bottom | 4,666 | 8 | 3.60 |
| ascending_triangle | 3,772 | 15 | 6.69 |
| descending_triangle | 2,839 | 14 | 6.34 |
| rising_wedge | 1,747 | 16 | 7.81 |
| falling_wedge | 1,251 | 16 | 7.08 |
| head_shoulders | 1,017 | 17 | 4.64 |
| inverse_head_shoulders | 999 | 17 | 4.77 |
| bull_flag | 376 | 12 | 4.09 |
| bear_flag | 261 | 12 | 4.15 |
| triple_bottom | 155 | 14 | 2.94 |
| triple_top | 142 | 13 | 3.04 |

**注**: 本 Phase 0 は **検出頻度のみ**。EV / WR / PF / Kelly は未計測 (Wave 2 BT で算出予定)。

## Verification

- `python3 tools/s6_chart_pattern_detector.py --self-test`: 12/12 HIT
- `python3 -m pytest -q tests/test_s6_chart_pattern_detector.py`: 20 passed
- runtime: 50.369s (USDJPY M5 12yr)
- SQLite duplicate pivot tuple query: 0 rows (clean)

## Scope adherence

LIVE 影響なし confirmed:
- `app.py`, `modules/`, `strategies/` 編集 0件
- `tier-master.json` 不変
- OANDA bridge / `live_ng_cells` / Render API 触れず
- `data/chart_patterns.db` は gitignored

## Roadmap impact

新戦略族 S6 Wave 1 Phase 0 = **インフラ完成**。Wave 2 BT で edge 評価可能な状態。月利100% ロードマップへの寄与は Wave 4 で LIVE 露出判定後に確定 (現状ゼロ)。

## Next task

**`20260503-2300-s6-w2-bt-usdjpy-m5`** (既に user が queue に追加): 12 patterns × USDJPY M5 で BT、cell 単位 verdict 算出 (Bonferroni m=12 で K 補正)。`feedback_partial_quant_trap` 通り N/WR/EV/PF/Kelly/Wilson/Bonferroni/WF 全評価必須。
