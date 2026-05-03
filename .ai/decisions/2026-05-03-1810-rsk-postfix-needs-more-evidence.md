---
date: 2026-05-03
task: 20260503-1405-w3-3-rsk-postfix-live-verification
verdict: NEEDS_MORE_EVIDENCE (両義的: post-fix N=0)
rule: R3
gate: Gate 0 (生存 — runaway 損失再発防止 forensic)
---

# W3-3 RSK Postfix Live Verification — N=0 両義性

## Verdict

**NEEDS_MORE_EVIDENCE** — Codex sandbox DNS 失敗で初回 BLOCKED、parent (DNS可) で再走済。結果は両義的。

## Codex deliverables

- `rsk_postfix_audit.py` (run dir 内)
- 5 regression tests pass (per-bar dedup logic 健全)
- Cutoff 確定: merge commit `caec0e8` at 2026-05-01T07:59:15Z

## Re-run from parent (DNS解決可)

| period | N | short_gap_rate | cluster_p95 | gap_min | pnl avg | total |
|---|---:|---:|---:|---:|---:|---:|
| **pre-fix** | 85 | **85.5%** | 26 | 14.6s | -7.39p | -628.2p |
| **post-fix** | **0** | — | — | — | — | 0 |
| contamination | 0 / 0 / 0 | — | — | — | — | — |

`fetched_count=1576` で全 trades 取得済、`shadow_target_count=85` (rsk_gbpjpy_reversion shadow 全件)。post-fix N=0 は API データの確定値。

## 両義的解釈

**(a) Fix が完璧に機能** — per-bar dedup gate が runaway 76件/24h パターンを完全防止。vacuously acceptance pass。
**(b) Gate 過剰 or 別 bug** — gate が too tight で本来発火すべき trades もブロック。false negative。

期間 cutoff 5/01 → 現在 5/03 = 2日 + 週末は短すぎる。Pre-fix で 85 trades / 5日間 = 17/day pace なら post-fix 期間で fix が緩めても 5-15 trades 発火するはず。**ゼロは異常側**寄り。

## acceptance gates 数値判定

| gate | 閾値 | 結果 | 判定 |
|---|---|---|---|
| `<90s gap rate` | ≤ 5% | n/a (N=0) | vacuously pass |
| Wilson_lo 95% | < 10% | n/a (N=0) | vacuously pass |
| cluster_p95 | ≤ 1.0 | 0 | pass |
| shadow → OANDA contamination | 0 | 0 | pass |
| `is_shadow=1` with `oanda_trade_id` | 0 | 0 | pass |

数値的には全 acceptance pass、ただし vacuously。

## Memory update — 結論

memory `project_rsk_gbpjpy_bar_close_gate_pending` を **FIXED** に閉じるのは早計。両義的データでは「fixed verified」の確証なし。

**保留 (OPEN)** ステータス継続、観察期間延長して再判定:

```
project_rsk_gbpjpy_bar_close_gate_pending — STILL OPEN as of 2026-05-03 18:10 JST.
Per-bar dedup regression test green; cutoff caec0e8 (2026-05-01 07:59:15Z) confirmed.
Post-fix N=0 over 2026-05-01..2026-05-03 (2 days + weekend) is ambiguous:
either (a) gate completely contained the runaway, or (b) gate over-tight blocking all entries.
Required next evidence: extend observation to 2026-05-10+, OR cross-check with same-strategy
in EUR_JPY/USD_JPY pair shadow (different instruments to isolate strategy vs instrument-specific gate).
```

## Roadmap impact

Gate 0 (生存) 防衛上、rsk_gbpjpy_reversion の runaway 再発はとりあえず止まっている (post-fix N=0)。短期的には safety positive。中期的に gate 過剰の確認が必要。

## Next task

**`rsk-extended-observation-2026-05-10`** — 5/10 まで観察期間延長して post-fix N を再測定。同時に rsk のテンプレートを使う他戦略 (rsk_eurjpy 等が存在すれば) の shadow 行を対照群として収集。N≥10 達成または 5/10 まで N=0 継続なら gate 過剰確認 (R3 forensic)。
