---
date: 2026-05-04
task: 20260503-2340-w3-6-b3-turtle-soup-bt
verdict: REJECT (Scenario C)
rule: R1
gate: Wave 3 Tier 2 — 新 alpha source 棄却
---

# W3-6 B3 Turtle Soup BT — Scenario C / REJECT

## Verdict

**REJECT (Scenario C)** — Codex deliverable は ACCEPT (data-driven, scope 遵守)、Wave 3 Tier 2 候補としては棄却。

## Reason

- Primary cell (`failure_window=12, exit_method=100_trailing, session_boundary=London_close_16UTC`): FAIL
- **Null bootstrap two-sided p = 0.902** (高すぎ、有意性なし)
- **max_year_share = 1.4457** (≥ 0.70 threshold) — 単年集中の overfit pattern

## Roadmap impact

Wave 3 Tier 2 新 alpha source 補充 candidate pool:
- S4 Connors-Raschke 80-20: BLOCKED (intervention catalog 待ち)
- C-1 London Breakout GBPJPY: REJECT (N=0 / N=662 旧版 Scenario C)
- S3 COT Pair-Pool FDR: 完全棄却 (W3-5)
- **B3 Turtle Soup**: 本 task で REJECT 確定
- 残候補極めて限定的 → Wave 3 Tier 2 補充は実質枯渇

S6 strategy 族 (chart pattern detector) も並行で W2b BT で PARK 確定 (別 decision)。

## Next

Wave 3 Tier 2 候補枯渇により、Gate 1 unlock 経路は **A2-alt の sr_channel_reversal × EUR_USD 5m Promote 候補** に集約。Gate 0 ACCEPT 反映後の SHADOW register が論理的次層。
