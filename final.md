# SENTINEL Silent Block Diagnosis Report

Generated: 2026-05-29

## Instrumentation Status

Commit `57d1570d` is present in this checkout and deployed endpoint probing confirms:

- `GET /api/demo/block-counts` returns mode-level `_block_counts`.
- `GET /api/demo/block-counts?strategy=<entry_type>` filters `_block_counts_per_strategy`.
- `_block()` force-logs `[SENTINEL_BLOCK_DIAG] <entry_type> blocked at: <reason>` for `_UNIVERSAL_SENTINEL` and `_SCALP_SENTINEL` strategies.

Rollback doc: `knowledge-base/wiki/analyses/sentinel-block-diag-instrumentation-2026-05-27.md`.

## Production Endpoint Snapshot

Probe:

```bash
curl -s 'https://fx-ai-trader.onrender.com/api/demo/block-counts'
curl -s 'https://fx-ai-trader.onrender.com/api/demo/block-counts?strategy=eurgbp_daily_mr'
```

Observed totals:

| Scope | total | per_strategy_total |
|---|---:|---:|
| all strategies | 15 | 15 |
| eurgbp_daily_mr filter | 15 | 0 |

Current `eurgbp_daily_mr` endpoint evidence is inconclusive: no per-strategy block count has been recorded for that strategy in the current process lifetime.

## Per-Strategy Gate Diagnosis

Render service logs are required to complete the requested 30-60 minute diagnosis window. They were not accessible from this Codex environment: no `render` CLI is installed, no Render API token is exposed, and `/api/demo/logs` returned no `[SENTINEL_BLOCK_DIAG]` entries.

| Strategy | Current evidence | Diagnosed blocking gate |
|---|---|---|
| eurgbp_daily_mr | `/api/demo/block-counts?strategy=eurgbp_daily_mr` returns `per_strategy_total=0` | Pending Render log capture |
| liquidity_sweep | Current endpoint shows `liquidity_sweep:max_open = 1` | `max_open` in current process snapshot, not enough to explain Cluster A pattern |
| bb_rsi_ema_aligned | No current endpoint count | Pending Render log capture |

## Root Cause Hypothesis

The instrumentation confirms the right observation point is installed. The original hypothesis remains unproven from this environment: Cluster A SENTINEL signals may be blocked by a silent `_block(reason)` between the Sentinel score bypass and `MTF_MONITOR`, but the current production process has not recorded `eurgbp_daily_mr` in `_block_counts_per_strategy`.

If Render logs show `[SENTINEL_BLOCK_DIAG] eurgbp_daily_mr blocked at: <reason>`, that reason is the P0-4 fix target. If no such log appears after 50+ Sentinel bypass messages, the signal is dying outside `_block()` and the next investigation should trace returns or exceptions between the bypass log and the first `_block()` call reached in that path.

## Monitoring Protocol

Run for 30-60 minutes after deploy/restart:

```bash
curl -s 'https://fx-ai-trader.onrender.com/api/demo/block-counts' | jq .
curl -s 'https://fx-ai-trader.onrender.com/api/demo/block-counts?strategy=eurgbp_daily_mr' | jq .
```

Render log filters:

```text
[SCORE_GATE] Sentinel bypass: eurgbp_daily_mr
[SENTINEL_BLOCK_DIAG] eurgbp_daily_mr blocked at:
[SENTINEL_BLOCK_DIAG] liquidity_sweep blocked at:
[SENTINEL_BLOCK_DIAG] bb_rsi_ema_aligned blocked at:
```

Record at least:

- First 50 `eurgbp_daily_mr` `[SENTINEL_BLOCK_DIAG]` reasons, grouped by reason.
- Two other Cluster A strategy reason distributions.
- Whether each reason aligns with intended shadow bypass behavior or an unintended pre-shadow gate.

## P0-4 Follow-Up Draft

Title: Fix SENTINEL pre-shadow block identified by `[SENTINEL_BLOCK_DIAG]`

Scope:

- Remove or downgrade temporary `[SENTINEL_BLOCK_DIAG]` logging after the fix is verified.
- Preserve `/api/demo/block-counts` only if still useful; otherwise remove endpoint and test.
- For the diagnosed gate reason, add a SENTINEL shadow bypass path that sets `_is_shadow = True` and continues toward `_open_shadow_emit_trade()` without changing LIVE eligibility.
- Do not change `_UNIVERSAL_SENTINEL` or `_SCALP_SENTINEL` membership.
- Add a focused regression test for the exact diagnosed reason and at least one affected Cluster A strategy.

Acceptance:

- `eurgbp_daily_mr` reaches `MTF_MONITOR` or shadow emit path under the previously blocked condition.
- No OANDA LIVE send is enabled by the bypass.
- `/api/demo/block-counts?strategy=eurgbp_daily_mr` no longer accumulates the diagnosed reason after deploy.
- Existing gate tests and the new SENTINEL regression test pass.
