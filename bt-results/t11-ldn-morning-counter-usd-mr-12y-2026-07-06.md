# T11 LDN morning counter-USD MR 12y grid (2026-07-06)

- verdict: **PASS**
- generated_at: 2026-07-06T05:59:25.112592+00:00
- data_window: 2014-02-03T02:30:00+00:00 .. 2026-06-05T00:00:00+00:00
- trade_count: 266055
- source_guard: `BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`, MASSIVE parquet only

## Pre-reg Target

LDN morning (`UTC07-09`) x counter-USD MR x USD `TREND`:

| N | EV_pips | PF | WR | Wilson95_lower | p_vs_other_time | Bonferroni_p |
|---:|---:|---:|---:|---:|---:|---:|
| 20290 | -3.998378 | 0.832639 | 0.458699 | 0.451851 | 0.003109 | 0.049738 |

## Grid

| Pair | USD regime | Time | N | EV | PF | WR | Wilson | p | Bonf-p | Neg sig |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| USD_JPY | TREND | LDN_UTC07_09 | 4888 | -4.345115 | 0.808493 | 0.452332 | 0.438422 | 0.622211 | 1.0 | NO |
| USD_JPY | TREND | OTHER | 32568 | -4.626327 | 0.795244 | 0.464781 | 0.459369 | None | None | NO |
| USD_JPY | RANGE | LDN_UTC07_09 | 4876 | -4.690532 | 0.741791 | 0.457137 | 0.443194 | 0.004608 | 0.073727 | NO |
| USD_JPY | RANGE | OTHER | 28977 | -2.799043 | 0.828294 | 0.468889 | 0.463148 | None | None | NO |
| EUR_USD | TREND | LDN_UTC07_09 | 5186 | -2.236174 | 0.886482 | 0.456807 | 0.443286 | 0.162457 | 1.0 | NO |
| EUR_USD | TREND | OTHER | 29868 | -1.482272 | 0.904569 | 0.481887 | 0.476223 | None | None | NO |
| EUR_USD | RANGE | LDN_UTC07_09 | 5336 | -1.762931 | 0.892286 | 0.469078 | 0.455715 | 0.03468 | 0.554874 | NO |
| EUR_USD | RANGE | OTHER | 27181 | -0.643898 | 0.951047 | 0.485302 | 0.479363 | None | None | NO |
| GBP_USD | TREND | LDN_UTC07_09 | 5596 | -4.057716 | 0.84653 | 0.46569 | 0.452648 | 0.366524 | 1.0 | NO |
| GBP_USD | TREND | OTHER | 29856 | -3.724554 | 0.825511 | 0.461247 | 0.455598 | None | None | NO |
| GBP_USD | RANGE | LDN_UTC07_09 | 5460 | -5.303956 | 0.787944 | 0.461172 | 0.447982 | 0.120385 | 1.0 | NO |
| GBP_USD | RANGE | OTHER | 26807 | -4.258922 | 0.77923 | 0.461708 | 0.455746 | None | None | NO |
| EUR_JPY | TREND | LDN_UTC07_09 | 4620 | -5.537746 | 0.793211 | 0.459091 | 0.444761 | 1e-06 | 1.8e-05 | YES |
| EUR_JPY | TREND | OTHER | 25317 | -0.591831 | 0.972208 | 0.488762 | 0.482607 | None | None | NO |
| EUR_JPY | RANGE | LDN_UTC07_09 | 4539 | -1.270252 | 0.935582 | 0.498127 | 0.483589 | 0.046215 | 0.739438 | NO |
| EUR_JPY | RANGE | OTHER | 24980 | 0.163266 | 1.009315 | 0.492754 | 0.486556 | None | None | NO |

## Method

- USD proxy: equal-weight USD return from `USD_JPY`, inverse `EUR_USD`, inverse `GBP_USD`; `EUR_JPY` uses this external USD proxy.
- Counter-USD: entry direction is opposite the 20d USD proxy sign.
- USD regime: `TREND` if absolute 20d USD proxy log-return is above the sample median threshold (`0.011718`), else `RANGE`.
- MR class: same-bar/side deduped union of `BB20 2sigma`, `RSI14 30/70`, and `EMA20 +/-0.75 ATR pullback`.
- PnL: next-bar open entry, 48-bar/12h close exit, per-pair round-trip friction from `friction-analysis.md`.
- Bonferroni: m=16 cells (`time x regime x pair`); one-sided Welch test compares LDN vs OTHER within same pair/regime on net EV.

## Data Sources

- USD_JPY: `/Users/jg-n-012/test/fx-ai-trader/data/cache/massive/USD_JPY_15m_2014_2026.parquet` (parent_checkout_readonly)
- EUR_USD: `/Users/jg-n-012/test/fx-ai-trader/.worktrees/t11-ldn-grid/data/cache/massive/EUR_USD_15m.parquet` (worktree)
- GBP_USD: `/Users/jg-n-012/test/fx-ai-trader/.worktrees/t11-ldn-grid/data/cache/massive/GBP_USD_15m.parquet` (worktree)
- EUR_JPY: `/Users/jg-n-012/test/fx-ai-trader/.worktrees/t11-ldn-grid/data/cache/massive/EUR_JPY_15m.parquet` (worktree)

## Verdict

LDN morning x counter-USD MR has Bonferroni-significant negative EV cells.

Pass cells: `EUR_JPY|TREND|LDN_UTC07_09`.
