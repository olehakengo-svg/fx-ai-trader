---
date: 2026-05-03
task: 20260503-1830-w3-4-rerun-c1-london-breakout-gbpjpy-12yr
verdict: ACCEPT (Codex deliverable) / **REJECT** (C-1 London Breakout strategic edge)
rule: R1
gate: Wave 3 Tier 2
---

# W3-4 C-1 London Breakout GBPJPY 12yr — Scenario C (Academic only)

## Verdict

**ACCEPT** (Codex 仕様通り) / **REJECT (Scenario C)** (戦略 edge ≒ noise レベル)

## Pre-registered primary cell metrics

cell: (Asian 7h / M5 close break / range × 1.0 exit / range >= median × 1.0)

| 指標 | 値 | 閾値 | 判定 |
|---|---:|---:|---|
| N | 662 | ≥ 30 | pass |
| WR | 45.62% | — | — |
| Wilson lo | 41.86% | ≥ 50% | **fail** |
| PF | 1.013 | ≥ 1.10 | **fail** |
| OOS/IS Kelly ratio | 0.97 | ≥ 0.85 | pass |
| Bonferroni p (m=81) | 1.0 | < α/m | **fail** |
| Sharpe | 0.08 | ≥ 0.5 | **fail** |
| Kelly | 0.0057 | — | — |
| Raw pip | +734.15 | — | — |
| Net pip | +164.83 | — | — |
| Max DD | -1453.14p | — | — |

**fail axis 4軸 (Wilson_lo / PF / Bonferroni / Sharpe)** で primary cell 落選。

## Validity

- V1 null bootstrap: **REJECT** — actual PF 1.013 < null p95 PF 1.174 (actual_gt_p95=False)
- V4 cohort: **REJECT** — max_abs_share=2.83、集中 cohort で edge 発生
- V2 rsk correlation: SKIP_NETWORK
- V3 broker cross-check: SKIP_NETWORK
- V5 orphan: BLOCKED_BY_SANDBOX
- V6 spread: RECORDED (London FX-only 0.86p subtracted)

## 結論

12年 925k bars / 662 trades あって PF=1.013 (≒ random) かつ null bootstrap で actual < p95 → **strategic edge は noise レベル**。Scenario C (academic only) 確定。

## Roadmap impact

C-1 London Breakout は GBPJPY M5 12yr primary pre-reg で REJECT → Wave 3 Tier 2 候補から外す。`global-retail-fx-edges-2026-05-03.md` §C-1 を **academic only / rejected** にダウングレード。

W3-4 関連の追加 BT (V2/V3 SKIP_NETWORK 網羅化) は不要。primary cell が REJECT した時点で V2-V6 の救済 path は閉じている。

## Next task

**`global-retail-fx-edges-c1-academic-only-update-2026-05-03`**: `wiki/learning/global-retail-fx-edges-2026-05-03.md` §C-1 セクションを REJECT/Scenario C 表記に更新する小規模 housekeeping task。

または優先度低 (housekeeping 後回し)、Gate 0 救済が同時並行で進行中なので scheduling 判断は司令塔。
