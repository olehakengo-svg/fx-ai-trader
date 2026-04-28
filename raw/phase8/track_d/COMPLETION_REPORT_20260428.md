# Phase 8 Track D — Session Boundary Transitions: Completion Report

**Date**: 2026-04-28 05:06 UTC
**Author**: Claude (quant analyst mode)
**Pre-reg LOCK**: [pre-reg-phase8-track-d-2026-04-28.md](../../../knowledge-base/wiki/decisions/pre-reg-phase8-track-d-2026-04-28.md)
**Master plan**: [phase8-master-2026-04-28.md](../../../knowledge-base/wiki/decisions/phase8-master-2026-04-28.md)
**Tool**: `tools/phase8_track_d.py`

## Verdict: **0 survivors** (both Stage 1 and Stage 2)

| Stage | Cells generated | Survivors | Gate |
|---|---|---|---|
| 1 (boundary) | 180 | **0** | BH-FDR(0.10) + Wilson>0.50 + N≥50 + EV>0 + cap≥5 + Sharpe>0.05 |
| 2 (sub-window 15m) | 1,200 | **0** | Bonferroni(0.05) + Wilson>0.50 + N≥50 + EV>0 + cap≥3 + Sharpe>0.05 |

Master cross-track adoption: **Track D contributes 0 candidates**.

## Boundary-level summary (Stage 1, no survivors)

180 cells = 6 boundaries × 5 pairs × 2 dir × 3 fw. After 275-day training
(holdout reserved):

- Best EV by boundary cell: USD_JPY `ny_to_asia` SELL fw=8 → **EV +0.15 pip,
  WR 49.5%, p=0.94** — not statistically distinguishable from coin flip.
- Most cells had EV strongly negative (friction-bleeding). Cells lacking BH-FDR
  significance + EV>0 + WR>50% combined → no survivor.

**Conclusion**: Boundary-level (1-2h aggregated window) does NOT carry a
detectable directional edge after friction. Hypothesis H1 (institutional
handover ⇒ directional drift) **rejected at boundary granularity**.

## Sub-window summary (Stage 2, no survivors)

1,200 cells = 40 sub-windows × 5 pairs × 2 dir × 3 fw. Of 1,200 cells:

| Single gate | Pass count |
|---|---|
| Wilson_lower > 0.50 | **1** |
| EV_net_pip > 0 | 27 |
| Sharpe_per_event > 0.05 | 13 |
| N ≥ 50 | 1,200 |

Bonferroni cutoff p × 1200 < 0.05 ⇒ p < 4.2 × 10⁻⁵ — none pass.

### Directional pattern noted (not a survivor — informational only)

The 7 best-WR cells (WR>0.55, N≥80) cluster in **one boundary, one direction,
two pairs**:

| pair | sub_window UTC | dir | fw | N | WR | Wilson_lo | EV_pip | p_Bonf |
|---|---|---|---|---|---|---|---|---|
| GBP_JPY | 21:30-21:45 | SELL | 12 | 116 | 0.586 | 0.495 | +2.88 | 92.7 |
| GBP_JPY | 21:30-21:45 | SELL | 8 | 116 | 0.578 | 0.487 | +2.52 | 136.9 |
| GBP_JPY | 21:30-21:45 | SELL | 4 | 116 | 0.552 | 0.461 | +2.43 | 368.5 |
| USD_JPY | 21:00-21:15 | SELL | 8 | 116 | 0.578 | 0.487 | +2.35 | 136.9 |
| USD_JPY | 21:00-21:15 | SELL | 12 | 116 | **0.595** | **0.504** | +1.93 | 60.9 |
| GBP_JPY | 21:00-21:15 | SELL | 12 | 116 | 0.552 | 0.461 | +1.63 | 368.5 |
| USD_JPY | 21:30-21:45 | SELL | 4 | 116 | 0.569 | 0.478 | +1.13 | 196.1 |

All seven point to **NY→Asia first 45min, JPY-cross SELL** with WR 55-60%.
Only **USD_JPY 21:00-21:15 SELL fw=12** (Wilson_lo 0.504) passes Wilson alone.

## Cross-strategy overlap analysis

`london_close_reversal_v2` (LCR-v2) deploys SELL on JPY at UTC 20:30-21:00.
The Track D directional cluster starts at **UTC 21:00** — i.e. immediately
after LCR-v2's window. Pair × direction match (JPY SELL) is exact.

**Interpretation**: NY-close JPY weakening pressure that LCR-v2 captures
(20:30-21:00) appears to **bleed into the first 45 min of NY→Asia**, but
the residual signal is not strong enough to clear Bonferroni or Wilson
when treated as an independent edge. This is consistent with LCR-v2 being
the "primary" capture and Track D viewing the tail.

| Existing strategy | UTC | Track D nearest | Verdict |
|---|---|---|---|
| `london_close_reversal_v2` (JPY SELL) | 20:30-21:00 | NY→Asia 21:00-21:45 JPY SELL (cluster, no survivor) | Same underlying phenomenon — LCR-v2 captures the meat, Track D sees the tail |
| `gotobi_fix` | 00:45-01:15 | `pre_tokyo` 22:00-00:00 | No directional cluster found |
| `london_fix_reversal` | 16:00 fix | (no boundary nearby) | N/A |

## Novel transition pattern: **none confirmed**

- No boundary edge survives Bonferroni at 15-min granularity.
- The strongest directional hint is **redundant with LCR-v2**.
- Track D's H2 (NY→Asia / London→NY transition has EV) — **rejected** at
  Bonferroni level.
- Track D's H3 (sub-window granularity matters) — partially supported (top
  cluster is concentrated in 21:00-21:45 vs flat across 21:00-23:00), but
  not enough to survive multiple comparison correction.

## Computational notes

- Stage 1 + Stage 2: ~30 sec end-to-end. Well under 20-30 min budget.
- 275-day training × 5 pairs × 12,200 bars/pair (after holdout + weekday
  filter) = sufficient sample for Stage 1; sub-windows had N=80-120 typical.
- `friction_for(pair, mode="DT", session=...)` cell-conditioning applied via
  `tools/lib/trade_sim.py`.

## Files produced

| File | Purpose |
|---|---|
| `tools/phase8_track_d.py` | Audit tool (Stage 1 + Stage 2) |
| `knowledge-base/wiki/decisions/pre-reg-phase8-track-d-2026-04-28.md` | LOCK |
| `raw/phase8/track_d/stage1_boundary_20260428_0506.json` | Stage 1 raw |
| `raw/phase8/track_d/stage2_subwindow_20260428_0506.json` | Stage 2 raw |
| `raw/phase8/track_d/overlap_with_existing_20260428_0506.md` | Overlap table |
| `raw/phase8/track_d/COMPLETION_REPORT_20260428.md` | This report |

## Recommendation to master

- **Do not adopt** any Track D cell into the top-3 cross-track survivor pool.
- The NY→Asia 21:00-21:45 JPY SELL cluster is **not novel** — it is a tail
  of `london_close_reversal_v2`. Master de-dup should classify any Track D
  cell with `boundary == ny_to_asia AND pair contains JPY AND dir == SELL`
  as redundant with LCR-v2.
- Track D session resources may be reallocated to deepening Track A/C or
  to running Stage 3-4 on Track A's existing survivors.

## Stage 3-4 not run (per LOCK Non-goals)

Stage 3 (quarterly stability) and Stage 4 (90-day holdout OOS) were
explicitly out-of-scope for this session. Since 0 cells survived Stage 2,
running Stage 3-4 would have nothing to test.
