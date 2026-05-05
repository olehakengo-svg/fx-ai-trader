# vol_momentum_scalp Shadow Redesign Pre-reg LOCK (2026-05-05)

## LOCK

- LOCK datetime: 2026-05-05T00:00:00Z
- Strategy: `vol_momentum_scalp`
- Scope: implementation + lightweight BT catastrophic-regression filter + shadow promote recommendation.
- Out of scope: live promotion and live ramp. BT is not a live promotion gate.

## Current vs Proposed

Current implementation evaluates the breakout trigger on the current `SignalContext` values:

- `ctx.bbpb >= 0.90` or `<= 0.10`
- `ctx.entry > ctx.open_price` for BUY, `<` for SELL
- current-bar ADX/DI/RSI/BB-width filter values
- no strategy-local same-bar emit guard

Proposed V2 is a single-axis timing hardening, default-off behind `VOL_MOMENTUM_SCALP_REDESIGN_V2=1`:

- use `df.iloc[-2]` as the closed signal bar for trigger/filter values
- use signal-bar `%B`, candle color, ADX/DI, RSI, MACD, EMA200 direction, and BB-width percentile
- keep `ctx.entry` as the execution reference used by the production path
- dedup `(ctx.symbol, self.name, signal, ctx.bar_time or ctx.df.index[-1])` inside the strategy
- keep pair filter, session filter, SL/TP geometry, scoring scale, and routing unchanged

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
- Function: production `run_scalp_backtest()` only. `vol_momentum_scalp` is registered in the Scalp engine, not the Daytrade engine, so `run_daytrade_backtest()` would not evaluate this strategy.
- Period: 365d if runtime/cache allow; minimum 90d.
- Compare default current path vs `VOL_MOMENTUM_SCALP_REDESIGN_V2=1`.
- Current MASSIVE target: `USD_JPY` at `5m`, because it is the available cache for an enabled `vol_momentum_scalp` pair.

## Shadow Accumulation Target

If the LOCK criteria pass, route V2 to shadow observation only and accumulate 60-90 calendar days or `N>=30`, whichever comes first. A separate task will evaluate shadow data with Bonferroni/Wilson/Kelly before any live ramp decision.

## BT Result and Verdict

- Result file: `knowledge-base/raw/bt-results/vol_momentum_scalp-shadow-bt-2026-05-05.json`
- Verdict: `REJECT`
- Reason: `USD_JPY` 365d MASSIVE BT passed positive direction and sanity floor, but failed the non-catastrophic Wilson lower-bound guard.

| Cell | Current N | Proposed N | PF Δ | Wilson lo Δ | EV Δ% | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `USD_JPY` 5m 365d | 80 | 83 | +0.0196 | -0.0218 | +5.5996 | FAIL |

LOCK breakdown:

- `pf_change >= -0.05`: PASS
- `wilson_lo_change >= -0.02`: FAIL (`-0.0218`)
- `n_change_pct >= -20`: PASS (`+3.75`)
- `pnl_sign_preserved`: PASS
- `positive_direction`: PASS (`ev_change_pct=+5.5996`)
- `sanity_floor`: PASS (`wilson_lo_proposed=0.519`, `pf_proposed=1.4809`)

No shadow promote setting is applied. Re-run after a separately pre-registered variant or after broader enabled-pair MASSIVE caches are available:

```bash
NO_AUTOSTART=1 .venv/bin/python tools/vol_momentum_scalp_shadow_bt.py
```
