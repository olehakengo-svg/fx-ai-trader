# vwap_session_revert — Pre-Registration Spec v1.0

**Date locked**: 2026-05-01
**Author**: Claude (quant analyst mode) + user direction
**Status**: SPEC LOCKED — modifications require restart of validation from scratch

## Lineage

Successor to `vwap_mean_reversion`, which was rejected after 5 rounds of adversarial analysis (see `lesson-vwap-mean-reversion-rejected-2026-05-01.md`):
- Per-bar Massive `vw` column at 1H is degenerate (loses microstructure info)
- v2 sublimation filters block 100% of signals (0 trades / 60d BT)
- v2 OFF: best cell BUY × LDN-NY overlap had p=0.07 NS, OOS H1/H2 fully reversed (+5.98p → -6.26p)
- Codex round-1 audit: REJECT
- 1 sample artifact (April JPY-strong / USD-weak regime)

## Alpha source — theoretical foundation

**Mechanism**: Institutional execution VWAP-reversion (Almgren-Chriss 2000, Bertsimas-Lo 1998)

Large institutional orders use TWAP/VWAP execution algorithms to minimize market impact. When intraday price drifts far from session-cumulative VWAP, **unfilled institutional orders create directional pressure back toward VWAP**. This is a real microstructure mechanism documented in equity markets (Madhavan 2002) and replicated in FX during liquid sessions (Krohn 2024).

**Why session-cumulative (not per-bar) VWAP**: Per-bar `vw` (Massive's column) at 1H ≈ bar typical price (degenerate). Session-cumulative VWAP from session open is the actual reference institutional execution algos target.

**Why 15m (not 1H, not 1m)**: 
- 1H: signal is too coarse, 50-bar window = ~1 week (no session-VWAP meaning)
- 1m: bid-ask noise dominates, no institutional signature
- **15m**: matches institutional VWAP-tracking horizon and real Live Live timeframe (per Render API: 87.5% of vwap_mr trades were 15m)

## Required preconditions (BEV — Break Even Variance)

For any 2σ session-VWAP deviation to have positive expected value:

```
E[reversion in N bars] > round_trip_friction
|deviation| × P(revert) × decay_factor(N) > spread + slip + commission
```

Empirically derived thresholds (locked):
- ADX < 25 (avoid trending regime where institutional VWAP is overruled)
- min_bars_into_session ≥ 8 (session VWAP needs to stabilize)
- spread_at_signal < 1.5 × spread_median_50 (avoid info shock conditions)

## LOCKED parameters (no post-hoc adjustment)

```yaml
strategy_name: vwap_session_revert
version: pre-reg-v1.0

# Sessions (UTC hours)
sessions:
  tokyo:        {start: 0, end: 9,  min_bars: 12}
  london_ny:    {start: 7, end: 16, min_bars: 8}  # primary, LDN-NY overlap
  ny:           {start: 13, end: 21, min_bars: 8}

# Timeframe
interval: 15m

# Session VWAP calculation
session_vwap:
  formula: cumsum(typical_price * volume) / cumsum(volume) since session_start
  typical_price: (high + low + close) / 3
  volume_proxy: Volume column (quote count for FX)
  reset: at session boundary
  fallback: typical_price (no volume weighting) if Volume = 0

# Deviation Z-score
deviation:
  numerator: (close - session_vwap)
  denominator: rolling_std((close - session_vwap), window=12, min_periods=8) within session
  
# Entry triggers (BOTH directions, NO post-hoc filtering)
entry_buy: deviation_z < -2.0 AND adx_14 < 25
entry_sell: deviation_z > +2.0 AND adx_14 < 25

# Exit (adaptive, but formula locked)
tp_target: revert by 0.6 × |entry_deviation_pip|  # asymmetric: small TP, large SL
sl: 1.0 × |entry_deviation_pip|
max_hold_bars: 16  # 4h
expected_RR: 0.6:1 with WR > 62.5% required for break-even

# Gates (PRE-LOCKED, not negotiable)
htf_block: true  # bull-trend HTF blocks SELL, bear blocks BUY
news_block: ±15min around scheduled high-impact economic data
spread_cap: spread_at_signal < 1.5 × spread_median_50
cooldown_bars: 4 per pair
session_end_block: do not enter in last 4 bars of session

# Universe
pairs: [USDJPY=X, GBPJPY=X, EURJPY=X, EURUSD=X, GBPUSD=X]
excluded: [EURGBP=X]  # documented low-liquidity Bonferroni-fail elsewhere
```

## Validation protocol (data split LOCKED before any BT)

### Phase 1: Train period
- **Period**: 2025-08-01 to 2025-12-31 (5 months) — assuming Massive availability
- **Use**: Initial sanity check with locked parameters
- **Purpose**: NO parameter tuning; just confirm strategy fires and produces sensible distributions

### Phase 2: Dev period
- **Period**: 2026-01-01 to 2026-03-31 (3 months)
- **Use**: Walk-forward 3-fold validation
- **Purpose**: Test parameter stability across folds

### Phase 3: Test period (HOLDOUT — single evaluation)
- **Period**: 2026-04-01 to 2026-04-30 (1 month)
- **Use**: ONCE, no peeking
- **Purpose**: Final out-of-sample evaluation

### Pass gates (HARD)

```yaml
train_phase:
  n_total: ">= 100 trades"
  net_ev: "> +0.5p (after BT friction model)"
  pair_consistency: ">= 3 / 5 pairs with EV > 0"
  direction_asymmetry: "abs(buy_ev - sell_ev) / max(abs(buy_ev), abs(sell_ev)) < 0.5"

dev_phase:
  n_total: ">= 50 trades"
  net_ev: "> +0.3p"
  walk_forward_consistency: ">= 2 / 3 folds with EV > 0"
  
test_phase:
  n_total: ">= 20 trades"
  net_ev: "> +0.3p (after BT friction)"
  net_ev_realistic_friction: "> 0p (after Live friction estimates per session)"
  wilson_lower_wr: "> 50%"
  binomial_p_one_sided: "< 0.05 (Bonferroni: this analysis only)"
  block_bootstrap_ci_lower: "> 0"
```

### Failure protocol

- ANY gate failure = strategy fails validation
- NO post-hoc adjustment of parameters
- Failed strategy → KB lessons; do NOT retry with relaxed gates
- If overall failure: try `liquidation_cascade_revert` next (pre-registered separately)

## External audit requirement

- **Mandatory** Codex review before any Live recommendation (after May 7, 2026 reset)
- Codex task: "try to break this claim"
- Must approve before Phase 4 (Shadow N=30)

## Implementation plan

1. Standalone BT script (no production code modification yet)
2. Run all 3 phases with hard splits
3. If pass: integrate as new entry_type into `app.py` (do NOT modify or remove `vwap_mean_reversion` block)
4. Run production-faithful BT for cross-verification
5. Submit to Codex for round-1 audit (post May 7)
6. If approved: enable in Shadow mode only

## Anti-curve-fit commitments

I commit (Claude, the analyst) to:
1. NOT change parameters after seeing any BT result on test data
2. NOT add new gates if test fails
3. Report failures honestly even if it kills the strategy
4. Apply Bonferroni correction including all rounds of past hypothesis testing
5. NOT cherry-pick favorable cells without Bonferroni adjustment

Any violation of the above constitutes a discipline failure and the lesson must be added to KB.

## Status

- [x] Spec locked: 2026-05-01
- [ ] Phase 1 BT (train)
- [ ] Phase 2 BT (dev)
- [ ] Phase 3 BT (test, holdout)
- [ ] Codex round-1 audit (post May 7)
- [ ] Shadow N=30 (if all above pass)
