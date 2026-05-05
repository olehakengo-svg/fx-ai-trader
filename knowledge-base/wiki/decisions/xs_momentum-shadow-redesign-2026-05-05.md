# xs_momentum Shadow Redesign Pre-reg LOCK (2026-05-05)

## LOCK

- LOCK datetime: 2026-05-05T00:00:00Z
- Strategy: `xs_momentum`
- Scope: implementation + lightweight BT catastrophic-regression filter + shadow promote recommendation.
- Out of scope: live promotion and live ramp. BT is not a live promotion gate.

## Current vs Proposed

Current implementation evaluates the momentum trigger on the current `SignalContext` values:

- `mom = (Close[-1] - Close[-21]) / ATR`
- `ctx.ema9 > ctx.ema21` for BUY, `<` for SELL
- `ctx.entry > ctx.open_price` for BUY, `<` for SELL
- `ctx.adx >= 20`
- no strategy-local same-bar emit guard

Proposed V2 is a single-axis timing hardening, default-off behind `XS_MOMENTUM_REDESIGN_V2=1`:

- use the most recent closed signal bar for momentum, EMA, ADX, ATR, and candle-color confirmation
- in BT, `df.iloc[-1]` is the closed signal bar
- in live, `df.iloc[-1]` may be in-progress, so evaluate `df.iloc[-2]`
- keep the existing pair filter, London-NY session filter, trigger thresholds, SL/TP geometry, scoring, and routing unchanged
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
- Function: production `run_daytrade_backtest()` only.
- Period: 365d if cache is sufficient; minimum 90d.
- Compare default current path vs `XS_MOMENTUM_REDESIGN_V2=1`.
- Current MASSIVE targets: `EUR_USD`, `GBP_USD`, and `USD_JPY` at `15m`, matching the strategy's enabled pair filter and available cache.

## Shadow Accumulation Target

If the LOCK criteria pass, route V2 to shadow observation only and accumulate 60-90 calendar days or `N>=30`, whichever comes first. A separate task will evaluate shadow data with Bonferroni/Wilson/Kelly before any live ramp decision.

## BT Result and Verdict

- Result file: `knowledge-base/raw/bt-results/xs_momentum-shadow-bt-2026-05-05.json`
- Verdict: `REJECT`
- Reason: `GBP_USD` passes the relative non-catastrophic and positive-direction checks, but fails the sanity floor (`PF=0.7722 < 0.95`). Because the audit concern was specifically anchored on `GBP_USD` deterioration, V2 is not recommended for shadow promotion.

| Cell | Current N | Proposed N | PF Δ | Wilson lo Δ | EV Δ% | Proposed PF | Proposed Wilson lo | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `EUR_USD` 15m 365d | 566 | 557 | +0.0293 | +0.0064 | +44.9173 | 1.0910 | 0.5930 | PASS |
| `GBP_USD` 15m 365d | 637 | 626 | +0.0117 | +0.0032 | +5.5753 | 0.7722 | 0.5280 | FAIL |
| `USD_JPY` 15m 365d | 608 | 596 | +0.0232 | +0.0051 | +253.0303 | 1.0141 | 0.5693 | PASS |

LOCK breakdown for failing cell `GBP_USD`:

- `pf_change >= -0.05`: PASS (`+0.0117`)
- `wilson_lo_change >= -0.02`: PASS (`+0.0032`)
- `n_change_pct >= -20`: PASS (`-1.7268%`)
- `pnl_sign_preserved`: PASS
- `positive_direction`: PASS (`ev_change_pct=+5.5753`)
- `sanity_floor`: FAIL (`PF=0.7722 < 0.95`; Wilson floor passes at `0.5280`)

No shadow promote setting is applied. Re-run after a separately pre-registered variant or a narrower pre-registered target policy:

```bash
NO_AUTOSTART=1 .venv/bin/python tools/xs_momentum_shadow_bt.py
```

## Codex Self-review

- Relative check only: PASS. Verdict uses relative PF/Wilson/N/PnL checks plus sanity floors; no absolute Kelly gate is used.
- Production live safety: PASS. V2 behavior is default-off unless `XS_MOMENTUM_REDESIGN_V2=1`.
- Shadow/live isolation: PASS. No shadow route or demo-trader setting is applied because LOCK rejected.
- Post-hoc adjustment: PASS. Only the pre-registered closed-bar + per-bar dedup V2 was evaluated.
- BT source guard: PASS. Runner sets `BT_MODE=1` and `BT_REQUIRE_MASSIVE_CACHE=1`; all target cells report `data_source=massive-parquet`.
