# Phase 8 Track A — 3-Way Feature Interaction Audit Summary

- Run: 2026-04-28 05:15 UTC
- LOCK: `pre-reg-phase8-track-a-2026-04-28.md`
- Triplets scanned: 4
- Pairs: 5 (USD_JPY, EUR_USD, GBP_USD, EUR_JPY, GBP_JPY)

## Verdict

| metric | value |
|---|---|
| Stage 1 cells (all) | 720 |
| Stage 1 survivors (BH+gates) | 5 |
| Stage 2 tested on holdout | 5 |
| Stage 2 final survivors | 4 |

## Top 5 Final Survivors (by EV_net_pip)

### #1 — `GBP_JPY SELL fw=8` × hour_utc=20 × bbpb_15m_b=3

- **Training**: n=104 WR=0.712 Wilson_lo=0.618 EV=+7.14p PF=2.496 Sharpe_pe=0.450 trades/mo=11.3
- **Holdout (90d OOS)**: n=37 WR=0.595 Wilson_lo=0.435 EV=+2.88p PF=1.363

### #2 — `GBP_JPY SELL fw=12` × hour_utc=20 × bbpb_15m_b=3

- **Training**: n=104 WR=0.712 Wilson_lo=0.618 EV=+7.06p PF=2.418 Sharpe_pe=0.437 trades/mo=11.3
- **Holdout (90d OOS)**: n=37 WR=0.595 Wilson_lo=0.435 EV=+2.77p PF=1.341

### #3 — `EUR_JPY SELL fw=12` × hour_utc=20 × bbpb_15m_b=3

- **Training**: n=102 WR=0.618 Wilson_lo=0.521 EV=+3.17p PF=1.596 Sharpe_pe=0.231 trades/mo=11.1
- **Holdout (90d OOS)**: n=40 WR=0.600 Wilson_lo=0.446 EV=+2.14p PF=1.33

### #4 — `EUR_JPY SELL fw=8` × hour_utc=20 × bbpb_15m_b=3

- **Training**: n=102 WR=0.608 Wilson_lo=0.511 EV=+2.89p PF=1.552 Sharpe_pe=0.213 trades/mo=11.1
- **Holdout (90d OOS)**: n=40 WR=0.600 Wilson_lo=0.446 EV=+2.10p PF=1.324

## Honest Negative Findings

- Stage 1 survivors that failed Stage 2: 1

Top 5 Stage-1 cells that failed holdout (highest training EV):

- `GBP_JPY SELL fw=4` × hour_utc=20 × bbpb_15m_b=3: train n=104 EV=+4.48p WR=0.615 → holdout n=37 WR=0.4865 EV=-0.116

## Cross-track Redundancy Check Hints

Phase 7 単発 survivor: `GBP_JPY × hour_utc=20 × SELL` (LCR-v2 redundant)。
- ⚠️ `GBP_JPY SELL × hour=20 × ...` は Phase 7 と重複の可能性。 3rd feature が真に selectivity を加えているか master が判定。
- ⚠️ `GBP_JPY SELL × hour=20 × ...` は Phase 7 と重複の可能性。 3rd feature が真に selectivity を加えているか master が判定。
