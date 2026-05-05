# alpha_intraday_seasonality Shadow Redesign Pre-reg LOCK (2026-05-05)

## LOCK

- LOCK datetime: 2026-05-05T00:00:00Z
- Strategy: `intraday_seasonality` / audit label `alpha_intraday_seasonality`
- Scope: implementation + lightweight BT catastrophic-regression filter + shadow promote recommendation.
- Out of scope: live promotion and live ramp. BT is not a live promotion gate.

## Current vs Proposed

Current implementation:

- trigger estimates same `weekday × hour` historical `Open→Close` returns
- minimum bucket N is 8
- `abs(t_stat) >= 2.0` and `cohens_d >= 0.3`
- HTF agreement hard-blocks contrary seasonality signals
- exit geometry is ATR bracket: `SL=1.5ATR`, `TP=min(2.5, 1.5+d)ATR`

Proposed V2 is the minimum audit-aligned redesign, default-off behind `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2=1`:

- keep the existing same `weekday × hour` trigger and statistics
- raise same-bucket minimum N to 30
- use Bonferroni-aware trigger strength, approximated by `abs(t_stat) >= 3.5` for 5 weekdays × 24 hours
- soften HTF agreement from hard block to metadata/score context for this strategy
- replace ATR bracket intent with distribution geometry: protective SL from bucket adverse quantile / `std_ret`, TP reference from bucket favorable quantile
- in DT BT, evaluate the V2 exit thesis as a 1-bar time exit with protective SL for `intraday_seasonality` only

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
- Function: production `run_daytrade_backtest()` only, with strategy-isolation matching `strategies=['alpha_intraday_seasonality']`.
- Period: 365d if cache is sufficient; minimum 90d.
- Compare default current path vs `ALPHA_INTRADAY_SEASONALITY_REDESIGN_V2=1`.
- If MASSIVE cache is missing for any locked pair, record the BT failure and do not recommend shadow promotion from BT.

## Shadow Accumulation Target

If the LOCK criteria pass, route V2 to shadow observation only and accumulate 60-90 calendar days or `N>=30`, whichever comes first. A separate task will evaluate shadow data with Bonferroni/Wilson/Kelly before any live ramp decision.

## BT Result and Verdict

- Result file: `knowledge-base/raw/bt-results/alpha_intraday_seasonality-shadow-bt-2026-05-05.json`
- Verdict: `REJECT`
- Reason: V2 under-fired under the pre-registered Bonferroni-aware `N>=30` / `abs(t_stat)>=3.5` design. Proposed path produced fewer than 20 total BT trades per pair, so `run_daytrade_backtest()` returned `サンプル数不足（20トレード未満）` and LOCK criteria could not pass.

## LOCK Criteria Outcome

All six locked MASSIVE 15m caches were present and read via `BT_MODE=1`:

- `EUR_USD`: current `N=191`, proposed BT error with only 1 total trade
- `GBP_USD`: current `N=249`, proposed BT error with only 2 total trades
- `USD_JPY`: current `N=238`, proposed BT error with only 3 total trades
- `EUR_JPY`: current `N=226`, proposed BT error with only 1 total trade
- `GBP_JPY`: current `N=284`, proposed BT error with only 2 total trades
- `EUR_GBP`: current/proposed BT error with 0 trades

Because proposed could not satisfy the non-catastrophic `n_change_pct >= -20` check and did not meet the sanity floor (`wilson_lo_proposed >= 0.30`, `pf_proposed >= 0.95`), no positive-direction check is considered sufficient.

## Shadow Decision

Shadow promote recommendation: `REJECT`.

No shadow routing/config change is applied. A follow-up redesign would need to be pre-registered separately rather than relaxing thresholds post hoc in this task.
