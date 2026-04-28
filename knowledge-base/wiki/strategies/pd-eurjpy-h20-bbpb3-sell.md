# pd_eurjpy_h20_bbpb3_sell — Phase 8 Track A discovered cell (Sentinel override)

## Status: SHADOW (Sentinel 0.01 lot, universal_sentinel)

Adopted 2026-04-28 from Phase 8 multi-track Pattern Discovery, Track A
(3-way feature interaction).

## Cell specification (LOCK source)

- Pre-reg: [pre-reg-phase8-track-a-2026-04-28](../decisions/pre-reg-phase8-track-a-2026-04-28.md)
- Aggregation: `raw/phase8/aggregation_2026-04-28.md`
- Pair: `EUR_JPY`
- TF: 15m
- Hour: `hour_utc=20` (UTC 20:00-20:59)
- Feature: `bbpb_15m_b=3` ⇔ `bbpb_15m ∈ (0.6, 0.8]`
- Direction: SELL only
- Trade rules: SL=1.0×ATR (above entry), TP=1.5×ATR (below entry), MIN_RR=1.5

## Backtest metrics

### Stage 1 (BH-FDR LOCK pass) — 275d training (365d − 90d holdout)

| metric | value |
|---|---|
| n_trades | 102 |
| WR | 0.618 |
| Wilson_lower (95%) | 0.521 |
| EV_net_pip | +3.17 |
| PF | 1.596 |
| Kelly | 0.231 |
| Sharpe_per_event | 0.231 |
| trades/month | 11.1 |
| BH-FDR p | 0.022 |

### Stage 2 (90d OOS holdout)

| metric | value |
|---|---|
| n_trades | 40 |
| WR | 0.600 |
| Wilson_lower (95%) | 0.446 |
| EV_net_pip | +2.142 |
| PF | 1.330 |

## Master gate decision

Pre-registered master gates from `phase8-master-2026-04-28.md`:

| Gate | Threshold | Value | Pass |
|---|---|---|---|
| WR_holdout | > 0.50 | 0.600 | ✓ |
| EV_holdout_pip | > 0 | +2.142 | ✓ |
| Wilson_lower_holdout | > 0.48 | 0.446 | ✗ (0.034 miss) |
| N_holdout | ≥ 10 | 40 | ✓ |
| Orthogonality (corr < 0.5 vs 7 strategies) | — | ✓ | ✓ |

**Strict pass: 4/5.** Wilson_lower_holdout fails by 0.034 due to small
holdout n (90d × 11 trades/mo ≈ 33 trades — Wilson_lower can't exceed
~0.45 at this n unless WR ≥ 0.625).

**Aggressive Shadow exploration override applied** per master plan §
「迷ったら採用側に倒す」. Override criteria:
- Other 4 gates pass cleanly (not marginal)
- Miss is sample-size-limited, not edge-limited
- Orthogonal to existing 7 daytrade Sentinel strategies
- Training cell is BH-FDR significant (Wilson_lo_train=0.521)
- Sentinel 0.01 lot deploy → Live cost ≈ $0.50/trade adverse

## Orthogonality to existing 7 strategies

| Strategy | Pair × hour conflict | Verdict |
|---|---|---|
| `london_close_reversal_v2` | GBP_JPY/USD/EUR_USD × 20:30-21:00 SELL | ✗ different pair (EUR_JPY rejected by LCR-v2 BT) |
| `gotobi_fix` | USD_JPY × 00:45-01:15 BUY | ✗ |
| `gbp_deep_pullback` | GBP × no hour | ✗ |
| Other 4 | various | ✗ |

EUR_JPY × hour_utc=20 SELL was a Phase 7 single-feature **reject** —
the 3rd feature `bbpb_15m_b=3` (price upper-mid Bollinger band) unlocks
the positive subset. Orthogonal mechanism: Phase 7 finding said
"hour=20 × JPY × SELL" works on GBP_JPY only; this cell shows EUR_JPY's
positive subset is conditioned on bbpb proximity to upper band.

## Promotion criteria (future)

- 30 Live shadow trades + cell_edge_audit re-validation
- Wilson_lower_live > 0.50 (no override)
- EV_net_pip ≥ +1.5
- → PAIR_PROMOTED candidate (still 0.05 lot until Mode B gate)

## Implementation

- File: `strategies/daytrade/pd_eurjpy_h20_bbpb3_sell.py`
- Class: `PdEurJpyH20Bbpb3Sell`
- Wired into:
  - `strategies/daytrade/__init__.py` (DaytradeEngine list)
  - `app.py` `DT_QUALIFIED`
  - `modules/demo_trader.py` `QUALIFIED_TYPES` and `_UNIVERSAL_SENTINEL`
  - `knowledge-base/wiki/tier-master.json` `universal_sentinel`

## Risk

- Pure single-cell deployment, no breadth
- 11 trades/month → low signal frequency, slow validation
- bbpb=3 condition is monotonic on price-vs-BB → no friction filter
- Friday block applied (consistent with LCR-v2 to avoid weekend gap risk)

## Related

- [[phase8-master-2026-04-28]]
- [[pre-reg-phase8-track-a-2026-04-28]]
- [[lesson-shadow-vs-live-confusion-2026-04-28]] — Shadow override discipline
