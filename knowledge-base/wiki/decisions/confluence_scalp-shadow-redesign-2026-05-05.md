# confluence_scalp Shadow Redesign Pre-reg LOCK (2026-05-05)

## LOCK

- LOCK datetime: 2026-05-05T00:00:00Z
- Strategy: `confluence_scalp`
- Scope: implementation + lightweight BT catastrophic-regression filter + shadow promote recommendation.
- Out of scope: live promotion and live ramp. BT is a sanity filter only, not a live promotion gate.

## Current vs Proposed

Current implementation evaluates the confluence trigger directly from the current `SignalContext`:

- trend family: `EMA9/EMA21` alignment or cross
- oscillator family: `RSI5` extreme plus `BB%B` extreme
- momentum family: `MACD-H` reversal
- CHoCH/MSB bonus reads the current `ctx.df` tail
- no strategy-local same-bar emit guard

Proposed V2 is a single-axis timing hardening, default-off behind `CONFLUENCE_SCALP_REDESIGN_V2=1`:

- use the most recent closed signal bar for trigger, score bonuses, CHoCH/MSB, and limit-entry wick calculation
- in BT, `df.iloc[-1]` is the closed signal bar
- in live, `df.iloc[-1]` may be in-progress, so evaluate `df.iloc[-2]`
- keep session gate, MFE guard, HTF hard block, 3-family thresholds, SL/TP geometry, scoring, and routing unchanged
- keep execution anchored to existing production context: BT still enters on next bar open in `run_scalp_backtest()`, live still routes through the existing demo-trader execution path
- dedup `(ctx.symbol, signal, bar_id)` inside the strategy, where `bar_id` is `ctx.bar_time` when supplied or the closed signal-bar index

## LOCK Criteria

```yaml
non_catastrophic_check:
  - pf_change >= -0.05
  - wilson_lo_change >= -0.02
  - n_change_pct >= -20
  - pnl_sign_preserved
positive_direction:
  - wilson_lo_change >= +0.01
  - ev_change_pct >= +5
  - pf_change >= +0.02
sanity_floor:
  - wilson_lo_proposed >= 0.30
  - pf_proposed >= 0.95
decision_rule:
  shadow_promote_recommended: all catastrophic checks pass AND at least one positive_direction passes AND sanity_floor passes
```

Absolute Kelly criteria are intentionally excluded. Kelly/Bonferroni/Wilson are reserved for the later shadow-data evaluation after production-path samples accumulate.

## BT Protocol

- Source: `data/cache/massive/{PAIR}_{TF}.parquet` via `BT_MODE=1`.
- Function: production signal path only. `confluence_scalp` is registered in the scalp engine, so the executable BT runner is `run_scalp_backtest()` rather than `run_daytrade_backtest()`.
- Period: 365d if cache is sufficient; minimum 90d.
- Compare default current path vs `CONFLUENCE_SCALP_REDESIGN_V2=1`.
- Current MASSIVE targets: `EUR_USD`, `USD_JPY`, `EUR_JPY`, `GBP_USD`, and `GBP_JPY` at `15m`; `EUR_GBP` is excluded because the strategy disables it explicitly.

## Shadow Accumulation Target

If the LOCK criteria pass, route V2 to shadow observation only and accumulate 60-90 calendar days or `N>=30`, whichever comes first. A separate task will evaluate shadow data with Bonferroni/Wilson/Kelly before any live ramp decision.

## BT Result and Verdict

Result file: `knowledge-base/raw/bt-results/confluence_scalp-shadow-bt-2026-05-05.json`

Verdict: `REJECT`

Reason:

- 4/5 cells returned production BT `<20 trades` errors: `EUR_USD` N=3, `USD_JPY` N=5, `GBP_USD` N=5, `GBP_JPY` N=5. These cells cannot satisfy the non-catastrophic, positive-direction, or sanity-floor checks.
- The only cell with available metrics, `EUR_JPY`, was unchanged by V2: current N=10 / PF=1.5447 / Wilson lo=0.3127 / EV=0.2999; proposed N=10 / PF=1.5447 / Wilson lo=0.3127 / EV=0.2999. It passes non-catastrophic and sanity floor but fails positive_direction because all deltas are zero.
- Overall LOCK verdict is FAIL, so no shadow promote setting is applied.

| Cell | Current N | Proposed N | PF Δ | Wilson lo Δ | EV Δ% | Proposed PF | Proposed Wilson lo | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `EUR_USD` 15m 365d | 3 | 3 | n/a | n/a | n/a | n/a | n/a | FAIL: `<20 trades` |
| `USD_JPY` 15m 365d | 5 | 5 | n/a | n/a | n/a | n/a | n/a | FAIL: `<20 trades` |
| `EUR_JPY` 15m 365d | 10 | 10 | +0.0000 | +0.0000 | +0.0000 | 1.5447 | 0.3127 | FAIL: no positive_direction |
| `GBP_USD` 15m 365d | 5 | 5 | n/a | n/a | n/a | n/a | n/a | FAIL: `<20 trades` |
| `GBP_JPY` 15m 365d | 5 | 5 | n/a | n/a | n/a | n/a | n/a | FAIL: `<20 trades` |

BT source note:

- All five targets had local MASSIVE 15m cache and `missing_caches=[]`.
- Console output showed `massive-parquet/15m` for each target.
- `run_scalp_backtest()` omits `data_source` / `bars_fetched` when it returns the `<20 trades` error, so those JSON fields are `null` for the four error cells.

Re-run command:

```bash
NO_AUTOSTART=1 .venv/bin/python tools/confluence_scalp_shadow_bt.py
```

## Codex Self-review

- Relative check only: PASS. Verdict uses relative PF/Wilson/N/PnL checks plus sanity floors; no absolute Kelly gate is used.
- Production live safety: PASS. V2 behavior is default-off unless `CONFLUENCE_SCALP_REDESIGN_V2=1`.
- Shadow/live isolation: PASS. No shadow route or demo-trader setting is applied because LOCK rejected.
- Post-hoc adjustment: PASS. Only the pre-registered closed-bar + per-bar dedup V2 was evaluated.
- BT source guard: PASS. Runner sets `BT_MODE=1` and `BT_REQUIRE_MASSIVE_CACHE=1`; all target cells used MASSIVE 15m cache.
