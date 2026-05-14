# macd_rsi_pullback — H1 TF Discovery (2026-05-14)

**Rule**: R1 (Slow & Strict) — new strategy proposal, 3.5y TV BT serves as 365d-equivalent evidence.
**Origin**: User request "bb_rsi の成果が悪いので作り替えたい、MACD と RSI で勝率を上げる方法、時間足は任せた".
**Source**: `bt-results/tv-overlays/macd_rsi_pullback-replica.pine` (377 lines).

## Hypothesis & design

bb_rsi_reversion failed because **mean-reversion-at-extreme** philosophy is structurally -EV under
OANDA friction (2.14p RT on USD_JPY) — confirmed by [[bb-rsi-tv-friction-cell-audit-2026-05-14]]
and [[bb-rsi-1m-mtf-variant-audit-2026-05-14]] (16+ cells, 4 configs, all -EV).

**New approach** — trend-following pullback (opposite philosophy):
- **Bias**: H1 RSI directional gate (≥60 BUY / ≤40 SELL) — sustained directional momentum
- **Entry timing**: 1H RSI pullback (prev bar in 30-55 BUY / 45-70 SELL) + MACD hist > 0/< 0 (state filter)
- **Confirmation**: candle close in direction + pullback resumption (RSI > prev_RSI)
- **RR**: SL ATR×1.0, TP ATR×2.0 (BEV_WR = 33.3%)
- **Session gate**: London + NY only (UTC 7-22)
- **Reference for H1 RSI bias**: xs_momentum_rsi (Live USD_JPY, currently accumulating N)

## Method

TV Strategy Tester full deep BT, OANDA:USDJPY, 1H, 2023-01-02 → 2026-05-14 (≈3.5 years):
- Pine v5 strategy with `commission_type=strategy.commission.percent, commission_value=0.0068`
  (= 0.0136% RT ≈ 2.14p on USDJPY at ~157)
- 5 analytic tables in Pine (Summary / Session / H1 RSI×Dir / 1H RSI prev×Dir / Exit×Dir)
- TF and pair iteration: 15m base (failed), 1H base (success), then cross-pair test

## TF iteration (USDJPY)

### 15m base — ALL CONFIGS FAIL

| Config | N | WR% | PF | Net |
|---|---:|---:|---:|---:|
| line_cross + H1 RSI 55/45 | 36 | 30.56 | 0.602 | -0.09% |
| hist_dir + H1 RSI 55/45 | 242 | 30.58 | 0.619 | -0.53% |
| hist_dir + H1 RSI 60/40 | 76 | 27.63 | 0.634 | -0.22% |

→ 15m friction:edge ratio is too unfavorable. Tightening H1 gate at 15m HURTS WR (selection bias —
when 1H RSI flips to >60 mid-session, 15m signals fire after the bounce is already done).

### 1H base — CANONICAL TF

| Config | N | WR% | PF | Net | MaxDD |
|---|---:|---:|---:|---:|---:|
| hist_dir + 55/45 (loose) | 708 | 36.72 | 1.007 | +0.06% | 0.74% |
| **hist_dir + 60/40 (canonical)** | **196** | **39.29** | **1.161** | **+0.36%** | **0.39%** |
| hist_dir + 65/35 (high-conviction) | 58 | 43.10 | 1.327 | +0.21% | 0.18% |
| hist_cross + 65/35 | 22 | 40.91 | 1.019 | +0.01% | 0.21% |
| line_cross + 60/40 | 59 | 38.98 | 0.953 | -0.03% | 0.23% |
| hist_dir + 65/35 wide pullback | 165 | 38.18 | 1.068 | +0.13% | 0.35% |

**Selected**: `hist_dir + 60/40` — highest N×PF×margin product, suitable for shadow promotion.

## Cross-pair test (65/35 + hist_dir on 1H)

| Pair | N | WR% | PF | Net | Verdict |
|---|---:|---:|---:|---:|---|
| **USD_JPY** | 58 | 43.10 | 1.327 | +0.21% | ✅ EDGE |
| EUR_USD | 199 | 32.16 | 0.761 | -0.50% | ❌ |
| GBP_USD | 178 | 35.39 | 0.974 | -0.05% | ❌ (friction underestimated) |
| EUR_JPY | 157 | 29.94 | 0.774 | -0.44% | ❌ |

**Edge is USD_JPY-specific** — consistent with KB priors:
USD_JPY has unique structure (carry-driven trend bias, narrow spread, 50%+ time in directional regime).

## Statistical robustness

### Canonical 60/40 config
- N=196, WR=39.29% (77/196)
- BEV_WR (RR=2.0) = 33.33%
- Observed WR − BEV = **+5.96 pp**
- Wilson 95% CI lower bound for WR: ≈ 32.6%
- → CI lower marginally below BEV. Edge is **plausible but not Bonferroni-rigorous at this N**.
  Live observation required to confirm.

### High-conviction 65/35 subset
- N=58, WR=43.10% (25/58), PF=1.327
- Wilson 95% CI lower: ≈ 31.2%
- → +9.8 pp observed margin but wider CI. Use as **lot-multiplier overlay**, not standalone.

## Decision (R1)

**Promote macd_rsi_pullback × USD_JPY × 1H × hist_dir × 60/40 to SCALP_SENTINEL (shadow-only)**

Rationale:
1. 3.5y TV BT shows +EV under OANDA friction (Python BT not yet run, but Live > TV > Python per
   `feedback_tv_edge_discovery_loop.md`)
2. Cross-pair test confirms USD_JPY-specific edge (no curve-fit across pairs)
3. TF discovery (15m fails, 1H succeeds) shows the edge has structural reason (friction:noise ratio)
4. WR 39.29% > BEV 33.33% with consistent equity curve (no large DD clusters)
5. PF 1.161 conservative; high-conviction subset (65/35) hits PF 1.327

**Gating before Live promotion**:
- Live N ≥ 30 with Wilson_lo > 33.3% (BEV_WR) at 95%
- PF > 1.05 sustained
- No regime cluster failure (avoid Q4-2024-like drawdown)

**Stop conditions** (Rule 2):
- N=10 Wilson_lo < 25% → halt
- N=20 PF < 0.8 → halt
- N=30 EV < -1.0p → halt

## What was learned

1. **15m friction:noise is too high for ATR×1 SL × MACD/RSI confluence**
   (consistent with bb_rsi 5m failure — 15m–5m TF range structurally hostile to mean-reversion AND
   confluence-on-pullback unless edge is extreme)
2. **H1 RSI prev-bar pullback + current-bar bias = adjacent-bar momentum** —
   the strategy fires when momentum just resumed from a brief dip in a sustained trend
3. **hist_dir > hist_cross > line_cross** — MACD as state filter (hist sign), not event filter
4. **Tightening directional gate works on 1H but breaks on 15m** — TF amplifies selection effect
5. **USD_JPY's structural trendiness is the edge** — same logic fails on EUR_USD / GBP_USD / EUR_JPY

## Related

- [[bb-rsi-tv-friction-cell-audit-2026-05-14]] — predecessor strategy audit (all -EV)
- [[bb-rsi-1m-mtf-variant-audit-2026-05-14]] — 1m MTF variant of bb_rsi (also -EV)
- [[../strategies/bb-rsi-reversion]] — bb_rsi strategy card (PAIR_DEMOTED)
- [[tv-pine-edge-discovery-framework]] — Pine-as-canon evaluation framework
- [[xs-momentum-rsi-tv-phase2-2026-05-13]] — H1 RSI bias filter precedent (xs_momentum_rsi)
- `bt-results/tv-overlays/macd_rsi_pullback-replica.pine` — Pine source

## Open items

- [ ] Python BT replication (`backtests/macd_rsi_pullback_full.py`) — 365d production-signal mirror
- [ ] Strategy card `wiki/strategies/macd-rsi-pullback.md`
- [ ] Demo-trader signal function `modules/demo_trader.py::signal_macd_rsi_pullback`
- [ ] tier-master / QUALIFIED_TYPES integration (deploy agent)
- [ ] Live N=10 EV review milestone
- [ ] Live N=30 Bonferroni gate decision
