---
id: 20260608-edge-cell-filter-massive-12y-bt
priority: P1
gate: R1
rule: R1
status: queued
created: 2026-06-08
owner: codex
spec: docs/superpowers/specs/2026-06-08-session-time-bias-bb-rsi-edge-cell-redesign-design.md
---

# Edge Cell Filter — MASSIVE 12y BT (Stage B)

**Purpose**: validate session_time_bias + bb_rsi_reversion edge cell filter
on 12y MASSIVE cache. Avoid TV-favorable trap (Kalman D7 / sr_fib V3 pattern).

## Deliverables

1. `bt-results/session-time-bias-cell-filter-12y.json`
   - pairs: [EUR_USD, GBP_USD, USD_JPY]
   - baseline (no filter) vs proposed (LDN × ADX[15,30] × dist<0.5%)
   - WFO 3-fold per pair
   - Bonferroni m=12 (cells × pairs × directions)

2. `bt-results/bb-rsi-reversion-pair-whitelist-12y.json`
   - pairs: 6 pair coverage
   - verify USD_JPY positive PF, USD_CHF / GBP_USD catastrophic
   - WFO 3-fold

3. `final.md` with promote/reject verdict per gate:
   - PROMOTE_SHADOW: PF>=1.05, WFO>=2/3 PF>1, Wilson_lo Bonf-corrected>=0.30
   - REJECT: PF<1.0 → strategy stays LIVE OFF, shadow observation only

## Constraints

- MUST use MASSIVE 12y native parquets only (no resample, no Yahoo fallback)
- BT_REQUIRE_MASSIVE_CACHE=1
- Apply env flag SESSION_TIME_BIAS_CELL_FILTER_V1=1 / BB_RSI_REVERSION_PAIR_WHITELIST_V1=1
  during BT
- Compare against in-sample 40-day production data (spec §2.3)
