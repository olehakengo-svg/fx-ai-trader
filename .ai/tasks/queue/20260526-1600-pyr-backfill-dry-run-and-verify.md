# PYR backfill dry-run and verify

priority: P0
rule: R3 (continuation of structural bug fix from 20260519-1832)
gate: N/A (correctness verification, no model promote)
status: queued

## Context

Commit `4cd44956` (`fix(pyr): wire entry_type kwarg through oanda_bridge.open_trade`) was pushed
to `main` at 2026-05-26 06:58 UTC, triggering Render auto-deploy `dep-d8ak99p9rddc73bac060` on
`srv-d6va1of5r7bs73en10vg` (fx-ai-trader web service).

The fix completes the work that previously stalled mid-way:
- `modules/demo_trader.py` PYR open call site (added `entry_type=_pyr_entry_type`) was committed
  earlier in `a7b18453` (2026-05-20).
- `modules/oanda_bridge.py` was missing the `entry_type` kwarg — this commit adds it.
- `modules/demo_db.py` now has `oanda_trades.strategy` column + `resolve_oanda_strategy_from_audit()`
  and `backfill_oanda_trade_strategy_from_audit()` helpers.
- `tools/backfill_oanda_strategy_2026_05_19.py` supports `--dry-run` / `--apply` against any DB path
  (env: `DEMO_DB_PATH`).

Pre-fix live audit (2026-04-19 → 2026-05-19) showed **15 closed OANDA trades with
`oanda_trades.strategy = NULL`** totaling **-4,379 JPY (47% of 30d net loss)**, which biased
`tier_live_drift.py` and `volume_live_promotion_watchdog.py` to **promote losers and demote
winners** (e.g., `vix_carry_unwind` apparently +646 JPY but truly -214 JPY after backfill).

## Task

Run `tools/backfill_oanda_strategy_2026_05_19.py --dry-run` against **production**
`demo_trades.db` on Render fx-ai-trader, capture the strategy attribution old-vs-new table,
and post a verdict to Discord. **Do NOT run `--apply` automatically** in this task.

## Constraints

- **Deploy gate**: Before invoking anything, wait for deploy `dep-d8ak99p9rddc73bac060` to be
  in `live` status. Poll Render API (`mcp__render__list_deploys` or REST) every 30 s up to 10 min.
  Abort with a clear error if deploy fails.
- **Production DB path**: `/var/data/demo_trades.db` (set `DEMO_DB_PATH=/var/data/demo_trades.db`
  on the host that runs the script).
- **No DB writes**: `--dry-run` only. The script reads `oanda_trades` + `oanda_audit`, computes
  proposed attribution, and writes JSON output to stdout only.
- **Execution path** (pick whichever is simplest given Render permissions):
  1. SSH into `srv-d6va1of5r7bs73en10vg@ssh.oregon.render.com` and run the command directly.
  2. Add a **temporary one-shot Render cron job** that runs the dry-run and posts to Discord, then
     delete the cron after capture (must be reversible).
  3. Add a temporary `/api/admin/pyr-backfill-dry-run` Flask route (gated by an env-only token)
     that runs the script and returns JSON. Revert in the same task before exit.
- **Data isolation**: Touch only `/var/data/demo_trades.db` (read), `oanda_audit` (read),
  `oanda_trades` (read). Do NOT touch `.env`, OANDA credentials, or any production env vars.

## Verification criteria

Define the next step based on dry-run output:

| Condition | Action |
|---|---|
| ≥10 rows reattributed AND any of {vix_carry_unwind, trendline_sweep} PnL flips sign vs current | Flag P0 follow-up: claude review → queue `--apply` task |
| 1–9 rows reattributed with no sign flips | Flag P1 follow-up: claude reviews → queue `--apply` task |
| 0 rows reattributed | Strategy attribution already healthy. Close `.ai/tasks/queue/20260519-1832-fix-pyr-strategy-attribution-and-dedup.md` (move to `done/`) |
| Errors (DB missing, permissions, tool fails) | Abort with full traceback in final.md, do not invent a "PASS" verdict |

## Output expectations

1. **`final.md`** with:
   - Deploy verification (status + finished_at timestamp).
   - Execution path chosen (SSH / cron / API route) and rationale.
   - Full JSON output from `--dry-run` (rows_updated, distinct_strategies, total_reattributed_pnl,
     per-strategy old-vs-new table).
   - Verdict: `APPLY_RECOMMENDED` / `NEEDS_REVIEW` / `NO_OP` / `ERROR`.
   - Proposed next task spec (either: "queue `--apply` task" with the script invocation, or
     "close queue file 20260519-1832-fix-pyr-strategy-attribution-and-dedup.md").

2. **Discord notification** with summary table for the 5 target strategies:
   - vix_carry_unwind, trendline_sweep, doji_breakout, gbp_deep_pullback, session_time_bias
   - Columns: old N, new N, old EV, new EV, delta (PnL).

## Forbidden actions

- Do NOT run `--apply` (no DB writes).
- Do NOT modify `oanda_credentials.json`, OANDA API keys, or any LIVE strategy config.
- Do NOT push secrets to git (API keys, SSH keys, OANDA token).
- Do NOT alter `modules/demo_trader.py` PYR call site (`a7b18453` already committed).
- Do NOT alter `modules/oanda_bridge.py` `open_trade` signature (`4cd44956` already committed).
- If introducing a temporary cron/API route, REVERT it in the same commit chain before finishing.

## Quant checkpoints (verdict matrix anchors)

- N (number of reattributed rows) — must be reported.
- Per-strategy PnL old vs new (no Wilson/Bonferroni required for a correctness backfill).
- Direction of sign flip on the two most-impacted strategies (vix_carry_unwind, trendline_sweep).
- Cohort safety: confirm 30-day window matches the audit cohort (2026-04-19 → 2026-05-19) before
  proposing apply.
