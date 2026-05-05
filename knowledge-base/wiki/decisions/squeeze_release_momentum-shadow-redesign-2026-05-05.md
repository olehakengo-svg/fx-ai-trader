# squeeze_release_momentum Shadow Redesign Pre-reg LOCK (2026-05-05)

## LOCK

- LOCK datetime: 2026-05-05T00:00:00Z
- Strategy: `squeeze_release_momentum`
- Scope: implementation + lightweight BT catastrophic-regression filter + shadow promote recommendation.
- Out of scope: live promotion and live ramp. BT is not a live promotion gate.

## Current vs Proposed

Current implementation evaluates the release trigger on the current `SignalContext` values:

- `ctx.bb_width >= df.iloc[-2].bb_width`
- `ctx.bbpb > 0.75` or `< 0.25`
- `ctx.entry > ctx.open_price` for BUY, `<` for SELL
- no strategy-local same-bar emit guard

Proposed V2 is a single-axis timing hardening, default-off behind `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2=1`:

- use `df.iloc[-2]` as the closed signal bar
- compare signal-bar `bb_width` against `df.iloc[-3].bb_width`
- use signal-bar `bb_pband` and candle color for direction confirmation
- keep `ctx.entry` as the execution reference used by the production path
- dedup `(ctx.symbol, signal, ctx.bar_time or ctx.df.index[-1])` inside the strategy
- keep pair filter, session filter, squeeze threshold, SL/TP geometry, scoring, and routing unchanged

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
- Function: production `run_daytrade_backtest()` only.
- Period: 365d if cache is sufficient; minimum 90d.
- Compare default current path vs `SQUEEZE_RELEASE_MOMENTUM_REDESIGN_V2=1`.
- If MASSIVE cache is missing for the locked SRM pairs, record the BT failure and do not recommend shadow promotion from BT.

## Shadow Accumulation Target

If the LOCK criteria pass, route V2 to shadow observation only and accumulate 60-90 calendar days or `N>=30`, whichever comes first. A separate task will evaluate shadow data with Bonferroni/Wilson/Kelly before any live ramp decision.

## BT Result and Verdict

- Result file: `knowledge-base/raw/bt-results/squeeze_release_momentum-shadow-bt-2026-05-05.json`
- Verdict: `REJECT`
- Reason: required MASSIVE parquet caches are absent for the locked SRM pairs:
  - `data/cache/massive/EUR_USD_15m.parquet`
  - `data/cache/massive/GBP_USD_15m.parquet`

Because the task requires MASSIVE cache data and forbids Yahoo fallback, the BT comparison was stopped before production `run_daytrade_backtest()` could be run on the target cells. No shadow promote setting is applied. Re-run the locked script after the required parquet caches are generated:

```bash
NO_AUTOSTART=1 .venv/bin/python tools/squeeze_release_momentum_shadow_bt.py
```
