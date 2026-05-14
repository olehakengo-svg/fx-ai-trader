# macd_1m_scalp v3.1 — Session Variants (Tokyo / London / NY)

**Date**: 2026-05-14
**Pair / TF**: USDJPY / 1m
**Method**: TradingView Pine v5 strategy, Strategy Tester native results
**Status**: 3 variants Pine-verified, each documenting a distinct session-specific edge profile

---

## Summary Table

| Variant | Filter | Geometry | N | WR | PF | Net | Avg trade |
|---|---|---|---|---|---|---|---|
| **TokyoBuy** | Tokyo + BUY-only + H1<70 | hist-TP ±0.015/±0.005 | 24 | 50.0% | 1.56 | +0.75 | +0.0314 |
| **London** ⭐ | London + dual + SELL-H1<50 | hist-TP ±0.015/±0.005 | 54 | 53.7% | **1.85** | +2.04 | +0.0378 |
| **NY** | NY + dual + no RSI | ATR-TP 1:2 | 48 | 41.67% | 1.33 | +0.47 | +0.0097 |

(`Net` and `Avg trade` are in TV's internal currency units with default_qty_value=1; relative comparison only.)

**Key takeaway**: One strategy family, three distinct session edge profiles. London is the
strongest cell; Tokyo and NY each require a different geometry/filter to capture +EV.

---

## Cell-Level Diagnostics (Pre-filter)

### Tokyo (hist-TP, both directions, no RSI filter)

| Dir | H1 RSI | N | WR% | PF | NetP |
|---|---|---|---|---|---|
| BUY | <30 | 1 | 100.0 | 999 | +0.9 |
| BUY | 30-50 | 8 | 75.0 | **3.88** | **+3.6** ★★★ |
| BUY | 50-70 | 16 | 31.3 | 1.01 | +0.1 |
| BUY | ≥70 | 1 | 0.0 | 0.00 | -0.8 |
| SELL | <30 | 3 | 33.3 | 0.06 | -2.4 |
| SELL | 30-50 | 8 | 12.5 | **0.05** | **-2.9** ★ KILLER |
| SELL | 50-70 | 6 | 33.3 | 1.29 | +0.4 |
| SELL | ≥70 | 0 | – | – | – |

**Pattern**: BUY × H1 30-50 is the lone strong +EV cell. SELL × H1 30-50 is the symmetric killer.
**Hypothesis**: Tokyo has a mild bullish drift bias — BUY reversals from MACD hist troughs
continue; SELL reversals fade against the drift.
**Fix**: BUY-only filter cuts the killer, but loses signal density. N=24 is thin.

### NY (hist-TP, both directions, no RSI filter — diagnostic)

| Dir | H1 RSI | N | WR% | PF | NetP |
|---|---|---|---|---|---|
| BUY | <30 | 7 | 57.1 | 2.16 | +0.2 ★ |
| BUY | 30-50 | 10 | 20.0 | 0.33 | -0.2 |
| BUY | 50-70 | 6 | 33.3 | 0.43 | -0.1 |
| BUY | ≥70 | 0 | – | – | – |
| SELL | <30 | 7 | 85.7 | **18.03** | **+0.6** ★★★ |
| SELL | 30-50 | 7 | 14.3 | 0.11 | -0.4 |
| SELL | 50-70 | 5 | 0.0 | 0.00 | -0.2 |
| SELL | ≥70 | 0 | – | – | – |

**Pattern**: NY +EV concentrated at H1 RSI <30 (extreme oversold context). H1 30-70 cells lose.
**Why hist-TP fails on NY**: NY runs trending moves that don't round-trip the MACD hist
quickly. Hist-TP exits at +0.005 catches too little of the trend.
**Fix**: Switch to ATR-TP 1:2 — captures the trending continuation NY actually offers.

---

## Path to Production

Each variant follows the [tv-pine-edge-discovery-framework](tv-pine-edge-discovery-framework.md) path:

1. **Pine 内追加検証** (current) — TV strategy tester on USDJPY 1m, native equity curve
2. **Cross-pair Pine 検証** — apply variants to EURUSD/GBPUSD on TV (does the edge generalize?)
3. **Live shadow → promotion gate** — Sentinel mode in production, accumulate N≥30 per variant
4. **Cross-source confirmation (final)** — Python BT vs live Sentinel; only at promotion decision

**Live shadow priority order**:
1. London variant (PF 1.85, robust) — Sentinel-ready
2. NY variant (PF 1.33) — Sentinel with H1 RSI <30 strict filter exploration
3. Tokyo BUY-only (PF 1.56, N=24) — defer until London/NY stabilize; N too thin

---

## Pine Files

- `bt-results/tv-overlays/macd_1m_scalp-london.pine` ⭐ strongest
- `bt-results/tv-overlays/macd_1m_scalp-tokyoBuy.pine`
- `bt-results/tv-overlays/macd_1m_scalp-ny.pine` (ATR-TP geometry)

## Screenshots

- `screenshots/macd_1m_scalp_tokyo_diagnostic.png` — pre-filter Tokyo cell breakdown
- `screenshots/macd_1m_scalp_tokyo_buy_only.png` — TokyoBuy result
- `screenshots/macd_1m_scalp_london_variant.png` — London result
- `screenshots/macd_1m_scalp_ny_atr_variant.png` — NY ATR-TP result

---

## Notes & Caveats

- **Avg trade in TV units, not pips**: Relative comparison only. Friction (USDJPY 1.2pip RT)
  needs to be modeled in the next step before lot sizing.
- **N for Tokyo is thin** (24): single-session filter cuts signal density harshly.
  Cross-pair test will materially affect promotion timing.
- **NY ATR-TP geometry is preliminary**: not yet swept for optimal TP multiplier.
- **Cell tracking in Pine has minor under-count bug** (entry_bucket reset edge case).
  Summary table (TV native) is authoritative; cell tables are diagnostic-only.
