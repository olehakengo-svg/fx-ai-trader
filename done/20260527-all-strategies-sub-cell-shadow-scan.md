# All-Strategies Sub-Cell Shadow Scan

Date: 2026-05-27  
Task: find pre-reg-able `WR >= 50%` and `+EV` cells across all current strategy registry entries.  
Decision: **NO PRE-REG_LOCKED_SHADOW_PROMOTE_CANDIDATE in the scanned DB snapshot**.

## Section 1: scan meta

### Data source and filters

Requested DB: `/var/data/demo_trades.db`  
Available DB scanned: `/data/repo/fx-ai-trader/demo_trades.db`

The requested `/var/data/demo_trades.db` was not present in this Codex workspace. The only non-empty `demo_trades.db` located by filesystem scan was `/data/repo/fx-ai-trader/demo_trades.db`; it was opened read-only with `file:/data/repo/fx-ai-trader/demo_trades.db?mode=ro`.

Mandatory production filter used:

```sql
WHERE is_shadow = 1
  AND status = 'CLOSED'
  AND created_at >= '2026-05-27 04:53'
```

This explicit `created_at` cutoff prevents mixing pre-fix rows with post `shadow_emit` gap fix rows.

### DB coverage result

| metric | value |
|---|---:|
| total rows in scanned `demo_trades` | 18 |
| all-time `is_shadow=1 AND status='CLOSED'` rows | 6 |
| post-fix `is_shadow=1 AND status='CLOSED'` rows | 0 |
| all-time max `created_at` in shadow CLOSED rows | 2026-04-02 10:31:03 |
| post-fix cutoff | 2026-05-27 04:53 |

The scanned DB therefore contains **no eligible post-fix observations**. The statistical scan below is valid for this DB snapshot, but it is not a definitive statement about a production DB that may exist outside this workspace.

### Strategies scanned

The current code registry contains 81 unique strategy names from `DaytradeEngine().strategies` and `ScalperEngine().strategies`. This differs from the expected `~76`, likely because the current branch has added Kalman/Pivot/SR-weighted variants since the earlier 76-strategy audit.

Strategies with `shadow_n >= 20` under the mandatory post-fix filter: **none**.

Strategies with `shadow_n < 20`: all 81 registry strategies. Verdict note: `INSUFFICIENT_N (post-fix shadow CLOSED N=0 in scanned DB; cannot estimate cell edge)`.

## Section 2: Stage-by-stage counts

| stage | description | count |
|---|---|---:|
| 0 | design ceiling cells: 81 strategies x 9 pairs x 2 directions x 4 sessions x <=5 regimes | <= 29,160 |
| 0 observed | observed post-fix candidate cells after mandatory DB filter | 0 |
| 1 | descriptive shortlist: `N>=20 AND WR>=0.5 AND EV>=0.5` | 0 |
| 2 | BH FDR q=0.10 across Stage 1 candidates | 0 |
| 3 | Bonferroni-extended `Wilson_bf_lo >= 0.50`, `m_extended=K_stage1` | 0 |
| 4 | time-cohort split passes, both halves `WR>=0.5 AND EV>0` | 0 |
| 5 | redundancy / diversification check passes | 0 |

FDR sanity check: `K_stage1=0`, `K_stage2=0`, and `K_stage2 <= K_stage1 * 0.10` is `0 <= 0`, so the q=0.10 sanity condition holds vacuously.

## Section 3: PRE-REG_LOCKED_SHADOW_PROMOTE_CANDIDATEs

No candidates.

| strategy | pair | dir | session | regime | N | wins | WR | EV | total | Wilson_lo | Wilson_bf_lo | half-WR front/back | half-EV front/back |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| none | n/a | n/a | n/a | n/a | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

Candidate-level spread / MFE / MAE: n/a because Stage 3 produced zero cells.

Candidate-level Live ramp plan: n/a because there are no candidate cells to promote. Future candidate implementation points, after a separate PR and commander review:

- Daytrade shadow ramp control is in `strategies/daytrade/__init__.py:306` via `split_shadow_always(...)`; existing env-gated cell hooks are defined around `strategies/daytrade/__init__.py:316`.
- Scalp shadow ramp control is in `strategies/scalp/__init__.py:149` via `split_shadow_always(...)`; scalp env-gated hooks start around `strategies/scalp/__init__.py:163`.
- Live tier routing is in `modules/demo_trader.py:6847` for `_PAIR_PROMOTED`, `modules/demo_trader.py:7158` for `_ELITE_LIVE`, and `modules/demo_trader.py:7237` for `_resolve_tier(...)`.

Pre-reg ramp template for any future candidate cell: keep it shadow-only for `N+15` additional post-lock CLOSED trades, require no withdrawal trigger (`WR<50%` or `EV<=0` on added sample), then open a separate PR to add the exact `(strategy, pair, dir, session, regime)` gate with small-lot live routing. No `.env`, OANDA, Render, GitHub, or production-write credential changes are part of this task.

## Section 4: per-strategy summary

All rows use the mandatory post-fix filter. Since the scanned DB has zero eligible rows, all strategies are `INSUFFICIENT_N`; this is not a design rejection.

| strategy | shadow_N | overall_WR | overall_EV | stage1_cells | stage5_cells | verdict |
|---|---:|---:|---:|---:|---:|---|
| adx_trend_continuation | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| atr_regime_break | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| bb_rsi_reversion | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| bb_squeeze_breakout | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| confluence_scalp | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| cpd_divergence | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| doji_breakout | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| dt_bb_rsi_mr | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| dt_fib_reversal | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| dt_sr_channel_reversal | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| ema200_trend_reversal | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| ema_cross | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| ema_pullback | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| ema_ribbon_ride | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| ema_trend_scalp | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| engulfing_bb | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| eurgbp_daily_mr | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| fib_reversal | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| gbp_deep_pullback | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| gold_pips_hunter | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| gold_trend_momentum | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| gold_vol_break | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| gotobi_fix | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| hmm_regime_filter | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| htf_false_breakout | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| inducement_ob | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| intraday_seasonality | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| jpy_basket_trend | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| kalman_d7_ema75_break | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| kalman_d7_po_dn_flip | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| kalman_d7_trail_atr | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| lin_reg_channel | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| liquidity_sweep | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| london_breakout | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| london_close_reversal | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| london_close_reversal_v2 | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| london_fix_reversal | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| london_ny_swing | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| london_session_breakout | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| london_shrapnel | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| ma_trend_perfect | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| macd_rsi_pullback | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| macdh_reversal | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| mqe_gbpusd_fix | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| mtf_counter_trend_scalp | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| mtf_regime_range_cascade_scalp | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| mtf_regime_trend_cascade_scalp | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| mtf_reversal_confluence | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| mtf_trend_follow_scalp | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| orb_trap | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| pd_eurjpy_h20_bbpb3_sell | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| pivot_detector_v2_5 | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| post_news_vol | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| rsk_gbpjpy_reversion | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| session_time_bias | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| session_vol_expansion | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| squeeze_release_momentum | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| sr_anti_hunt_bounce | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| sr_break_retest | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| sr_channel_reversal | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| sr_fib_confluence | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| sr_liquidity_grab | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| sr_weighted_bounce | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| sr_weighted_break | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| stoch_trend_pullback | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| three_bar_reversal | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| tokyo_nakane_momentum | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| tokyo_range_breakout_up | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| trend_rebound | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| trendline_sweep | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| turtle_soup | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| v_reversal | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| vdr_jpy | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| vix_carry_unwind | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| vol_momentum_scalp | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| vol_spike_mr | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| vol_surge_detector | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| vsg_jpy_reversal | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| wick_imbalance_reversion | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| xs_momentum | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |
| xs_momentum_rsi | 0 | n/a | n/a | 0 | 0 | INSUFFICIENT_N |

Legacy pre-fix diagnostic only: the scanned DB has 6 all-time shadow CLOSED rows from 2026-04-02 across `ema_cross`, `fib_reversal`, `macdh_reversal`, and `stoch_trend_pullback`. These rows were intentionally excluded from the formal scan because they predate the post-fix cutoff.

## Section 5: portfolio-level recommendation

Estimated monthly contribution from the candidate cell set: **0 pips/month** in the scanned post-fix DB, because no candidate cells exist.

Contribution to the roadmap monthly 100% target: **0% from this scan result**. `roadmap-v2.1.md` frames the 100% target as Gate 2, after aggregate Kelly and PnL conditions; this scan adds no locked cells to that path.

Correlation / diversification check: n/a. There are no Stage 4 or Stage 5 cells to test for concentration by pair, direction, session, or regime.

Interpretation:

- For the scanned DB snapshot, **76/81 current shadow strategies have no usable post-fix CLOSED rows, and the remaining registry entries also have zero post-fix CLOSED rows**. This is an N problem, not an edge rejection.
- Therefore the proper quant conclusion is not "all 81 designs failed"; it is "the available DB snapshot cannot support a pre-reg sub-cell promotion decision."
- If this zero-row result is also true in the real production `/var/data/demo_trades.db`, then no strategy currently has a pre-reg-able entry-time sub-cell after the shadow_emit fix, and the next action is data accumulation / shadow routing verification rather than Live promotion.
- If the real production DB contains post-fix rows outside this workspace, rerun this exact scan against that DB path with the same locked dimensions and cutoff.

Pre-reg LOCK:

- Cell dimensions used: `instrument`, `direction`, UTC session derived from `entry_time`, and `COALESCE(v2_regime, regime, 'unknown')`.
- Explicitly unused: `close_reason`, `spread_at_entry`, `confluence_score`, `sr_basis`, MFE/MAE gates, and any other post-hoc dimensions.
- Stage thresholds were not relaxed after observing zero Stage 1 candidates.
- No production DB writes, `.env` reads, OANDA/Render/GitHub credential access, live config changes, or tier changes were performed.

