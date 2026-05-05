# asia_range_fade_v1 Shadow Redesign Pre-reg LOCK (2026-05-05)

## LOCK

- LOCK datetime: 2026-05-05T00:00:00Z
- Strategy: `asia_range_fade_v1`
- Scope: implementation + lightweight BT catastrophic-regression filter + shadow promote recommendation.
- Out of scope: live promotion and live ramp. BT is not a live promotion gate.

## Current vs Proposed

Current implementation forms the Asia range from `df.iloc[-RANGE_LOOKBACK:]`, which includes the same bar used for touch, rejection candle, RSI confirmation, and close-entry. This lets the touch/rejection bar create the range boundary it is supposed to fade.

Proposed V2 is a single-axis timing hardening, default-off behind `ASIA_RANGE_FADE_V1_REDESIGN_V2=1`:

- form the range from the closed prior window `df.iloc[-(RANGE_LOOKBACK + 1):-1]`
- keep touch/rejection/RSI on `df.iloc[-1]`, the confirmed signal bar used by the existing backtest path
- keep session, ATR, range size, bars-in-range, touch tolerance, rejection candle, RSI, TP/SL geometry, scoring, and confidence unchanged
- no post-hoc pair or threshold adjustment is allowed in this task

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

Absolute Kelly criteria are intentionally excluded. Kelly/Bonferroni/Wilson promotion analysis is reserved for the later shadow-data evaluation after production-path samples accumulate.

## BT Protocol

- Source: `data/cache/massive/{PAIR}_{TF}.parquet` via `BT_MODE=1`.
- Function: production `run_daytrade_backtest()` only; no resample substitute.
- Period: 365d if cache is sufficient; minimum 90d.
- Compare default current path vs `ASIA_RANGE_FADE_V1_REDESIGN_V2=1`.
- Current MASSIVE targets: available FX `15m` caches, with strategy-only engine patching to isolate `asia_range_fade_v1` while still calling `app.run_daytrade_backtest()`.

## Shadow Accumulation Target

If the LOCK criteria pass, route V2 to shadow observation only and accumulate 60-90 calendar days or `N>=30`, whichever comes first. A separate task will evaluate shadow data with Bonferroni/Wilson/Kelly before any live ramp decision.

## BT Result and Verdict

- Result file: `knowledge-base/raw/bt-results/asia_range_fade_v1-shadow-bt-2026-05-05.json`
- Verdict: `REJECT`
- Reason: every evaluated MASSIVE 15m target returned `サンプル数不足（20トレード未満）` from production `run_daytrade_backtest()`. Because the function does not return a usable trade log below 20 trades, the relative catastrophic checks, positive-direction check, and sanity floor cannot be passed.
- Lookback: 90d. The available 15m MASSIVE caches were below full 365d coverage, so the pre-registered minimum 90d path was used.

| Cell | Current N | Proposed N | Current error | Proposed error | Verdict |
| --- | ---: | ---: | --- | --- | --- |
| `USD_JPY` 15m 90d | 0 | 0 | `<20 trades` | `<20 trades` | FAIL |
| `EUR_USD` 15m 90d | 0 | 0 | `<20 trades` | `<20 trades` | FAIL |
| `GBP_USD` 15m 90d | 0 | 0 | `<20 trades` | `<20 trades` | FAIL |
| `EUR_JPY` 15m 90d | 0 | 0 | `<20 trades` | `<20 trades` | FAIL |
| `GBP_JPY` 15m 90d | 0 | 0 | `<20 trades` | `<20 trades` | FAIL |

No shadow promote setting is applied. Re-run only after a separately pre-registered firing-rate repair or target-policy change:

```bash
NO_AUTOSTART=1 .venv/bin/python tools/asia_range_fade_v1_shadow_bt.py
```

## Codex Self-review

- Relative check only: PASS. Verdict uses the registered relative criteria and fails because BT produced no valid comparable sample; no absolute Kelly gate is used.
- Production live safety: PASS. V2 behavior is default-off unless `ASIA_RANGE_FADE_V1_REDESIGN_V2=1`.
- Shadow/live isolation: PASS. No shadow route or demo-trader setting is applied because LOCK rejected.
- Post-hoc adjustment: PASS. Only the pre-registered closed-prior-range V2 was evaluated; no threshold or pair tuning was added after seeing results.
- BT source guard: PASS. Runner sets `BT_MODE=1` and `BT_REQUIRE_MASSIVE_CACHE=1`; target OHLCV loads showed `massive-parquet/15m`.
