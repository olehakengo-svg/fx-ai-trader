# W0-3 weekend_gap_fill_multiday — EXPLORE report (2026-07-24)

**Hypothesis (NEW)**: large weekend gaps (Monday open vs Friday close) fill back toward the Friday close — fade the gap.

- **Explore window**: 2014-01-01 .. 2021-12-31 only. **2022+ never loaded** (hard date filter + `assert max(index) < 2022-01-01` per pair in `tools/weekend_gap_fill_explore.py`). 2022+ remains locked OOS.
- **Data**: 15m 12y parquet (`data/cache/massive/{PAIR}_15m_2014_2026.parquet`), ~197k bars/pair in-window.
- **Pairs**: EUR_USD, USD_JPY, GBP_USD, **AUD_USD** — AUD_JPY has **no 12y parquet** (history starts 2021-12-24), so the 4th USD major was substituted. AUD_USD RT is **not in the KB friction table**; 2.5p theoretical assumed.
- **Definitions**: Friday close = Close of last 15m bar < Fri 21:00 UTC (≤6h guard); Monday open = Open of first 15m bar ≥ Sun 21:00 UTC (≤24h guard). Gap = Monday open − Friday close.
- **Qualification (primary)**: |gap| ≥ 10× pair RT (EUR_USD 20.0p / USD_JPY 21.4p / GBP_USD 45.3p / AUD_USD 25.0p). 5× RT band kept as diagnostic only.
- **Measurement**: exit-free. Toward-fill MFE/MAE/net at h ∈ {4, 12, 24, 72, 120}h from the Monday-open reference price. **Event bar excluded from every forward window (asserted — no lookahead)**. No BE/Trail/TP/SL.
- **Stats**: one-sided event-block bootstrap (10,000 resamples, seed 20260724; H1: mean net toward-fill > 0). Pooled bootstrap blocks by **weekend date** (same-weekend cross-pair correlation). Headroom = MFE_p50 / RT.

## 1. Event counts (validation)

| pair | weekends measured | holiday skips | \|gap\| p50 | \|gap\| p90 | 10×RT thr | **N qualifying (10×)** | N (5× diag) |
|---|---|---|---|---|---|---|---|
| EUR_USD | 408 | 10 | 6.5p | 23.6p | 20.0p | **57** | 138 |
| USD_JPY | 400 | 18 | 6.9p | 31.0p | 21.4p | **68** | 144 |
| GBP_USD | 407 | 11 | 9.5p | 32.3p | 45.3p | **18** | 81 |
| AUD_USD | 412 | 6 | 6.8p | 25.5p | 25.0p | **44** | 115 |

Qualifying gaps are rare by construction: ~5.5–8.5/yr for EUR/JPY/AUD; **GBP_USD N=18 (~2/yr) is tiny — its per-pair stats are indicative only.** Face validity of top events confirmed: 2017-04-23 French election (EUR +178.5p), 2015-06-28 Greek capital controls (EUR −152.6p), 2020-03-08 COVID/oil crash (JPY −130.2p), 2016-11-06 FBI/Clinton (JPY +94.8p), 2017-01-15 May hard-Brexit speech (GBP −185.8p). One event hand-verified bar-by-bar (EUR 2015-06-26: gap −152.6p, net24 +232.5p, full fill 17.0h — matches script output exactly).

## 2. Toward-fill forward stats — primary 10×RT (pips, exit-free)

MAE p25 < 0 means price never moved against the fade in that window for ≥25% of events.

### EUR_USD (N=57, RT 2.0p)

| h | MFE p25/p50/p75 | MAE p25/p50/p75 | net mean | net med | boot p | headroom |
|---|---|---|---|---|---|---|
| 4h | 15.8 / **23.7** / 35.7 | −2.7 / 2.6 / 16.8 | **+12.3** | +10.7 | **0.0001** | 11.8× |
| 12h | 23.4 / 34.6 / 54.5 | 2.7 / 17.9 / 30.3 | **+15.6** | +11.7 | **0.0001** | 17.3× |
| 24h | 26.7 / 52.2 / 78.1 | 8.1 / 30.7 / 51.0 | +14.2 | +15.4 | 0.033 | 26.1× |
| 72h | 40.1 / 77.2 / 140.1 | 41.2 / 56.8 / 91.3 | +8.2 | +3.0 | 0.259 | 38.6× |
| 120h | 55.8 / 102.6 / 180.8 | 47.7 / 73.0 / 128.8 | +25.4 | +28.3 | 0.096 | 51.3× |

### USD_JPY (N=68, RT 2.14p)

| h | MFE p25/p50/p75 | MAE p25/p50/p75 | net mean | net med | boot p | headroom |
|---|---|---|---|---|---|---|
| 4h | 17.4 / **28.1** / 38.7 | 0.7 / 12.5 / 28.7 | +9.3 | +11.8 | 0.0087 | 13.1× |
| 12h | 23.2 / 35.0 / 59.1 | 3.6 / 20.3 / 38.0 | +12.2 | +10.4 | 0.019 | 16.4× |
| 24h | 24.7 / 45.2 / 80.6 | 11.2 / 27.5 / 56.6 | +4.2 | +12.5 | 0.298 | 21.1× |
| 72h | 43.1 / 85.0 / 137.3 | 25.6 / 57.2 / 136.6 | +6.0 | +14.4 | 0.306 | 39.7× |
| 120h | 60.1 / 110.2 / 186.6 | 28.9 / 76.7 / 168.0 | +37.5 | +25.9 | 0.025 | 51.5× |

### GBP_USD (N=18 — TINY, RT 4.53p)

| h | MFE p25/p50/p75 | MAE p25/p50/p75 | net mean | net med | boot p | headroom |
|---|---|---|---|---|---|---|
| 4h | 28.2 / 32.3 / 43.8 | −6.1 / 6.3 / 34.8 | +2.6 | +13.8 | 0.366 | 7.1× |
| 12h | 31.0 / 51.6 / 58.5 | 9.6 / 61.0 / 119.2 | **−27.3** | −29.7 | 0.971 | 11.4× |
| 24h | 32.2 / 56.1 / 80.1 | 25.7 / 77.0 / 122.2 | −25.4 | −20.9 | 0.876 | 12.4× |
| 72h | 51.3 / 95.9 / 156.5 | 89.8 / 117.1 / 219.6 | −22.8 | −18.8 | 0.711 | 21.2× |
| 120h | 65.5 / 107.1 / 216.3 | 107.9 / 169.8 / 297.4 | −3.5 | −59.6 | 0.544 | 23.7× |

### AUD_USD (N=44, RT 2.5p assumed)

| h | MFE p25/p50/p75 | MAE p25/p50/p75 | net mean | net med | boot p | headroom |
|---|---|---|---|---|---|---|
| 4h | 13.0 / 20.9 / 29.4 | 1.5 / 11.3 / 20.0 | +4.0 | +4.3 | 0.083 | 8.3× |
| 12h | 16.1 / 27.6 / 42.1 | 5.5 / 15.9 / 31.7 | **+11.9** | +11.7 | **0.0039** | 11.0× |
| 24h | 20.4 / 35.0 / 74.6 | 6.9 / 19.6 / 47.3 | +11.8 | +10.3 | 0.038 | 14.0× |
| 72h | 41.0 / 78.1 / 110.2 | 18.7 / 41.3 / 83.7 | +0.8 | +8.4 | 0.465 | 31.2× |
| 120h | 53.8 / 103.5 / 136.2 | 22.9 / 66.1 / 118.9 | −1.9 | −0.4 | 0.529 | 41.4× |

### Pooled (N=187 events over 126 distinct weekends; weekend-block bootstrap)

| h | MFE p50 | MAE p50 | net mean | net med | boot p (weekend-block) |
|---|---|---|---|---|---|
| 4h | 26.4 | 6.4 | **+8.3** | +10.7 | **0.0002** |
| 12h | 34.0 | 18.8 | +9.4 | +10.7 | **0.0055** |
| 24h | 44.8 | 29.5 | +6.2 | +8.8 | 0.114 |
| 72h | 80.2 | 56.8 | +2.7 | +10.4 | 0.374 |
| 120h | 104.7 | 78.2 | +20.6 | +17.5 | 0.039 |

## 3. Fill timing (within 120h window)

| pair | half-fill rate 120h | full-fill 24h / 72h / 120h | t-half p25/p50/p75 (h) | t-full p25/p50/p75 (h) |
|---|---|---|---|---|
| EUR_USD | 96% | 67% / 79% / 82% | 0.25 / **1.25** / 4.1 | 4.8 / **10.5** / 17.3 |
| USD_JPY | 93% | 62% / 81% / 84% | 0.25 / **1.0** / 4.5 | 2.0 / **9.3** / 27.0 |
| GBP_USD | 83% | 28% / 56% / 67% | 2.0 / 4.25 / 24.0 | 11.9 / 33.3 / 55.6 |
| AUD_USD | 95% | 52% / 70% / 82% | 1.0 / **2.0** / 27.0 | 5.0 / 15.4 / 40.9 |

The fill is **fast**: median time to 50% fill is 1–2h for EUR/JPY/AUD; median full fill ~9–15h. Despite the task name ("multiday"), the exploitable move is front-loaded into the first Asia/London session — the 24–72h horizons add MAE much faster than MFE.

## 4. Monotonicity by gap-size tercile (|gap|/RT, net@24h median)

| pair | T1 (small) | T2 | T3 (large) | monotone? |
|---|---|---|---|---|
| EUR_USD | +7.1 (fill 79%) | +24.5 (95%) | +15.4 (74%) | no (hump) |
| USD_JPY | +9.3 (96%) | +2.5 (86%) | +34.6 (70%) | no |
| GBP_USD | −13.6 (83%) | −20.9 (67%) | −49.7 (50%) | **yes, DECREASING** |
| AUD_USD | +15.3 (93%) | −9.9 (71%) | +11.7 (80%) | no |

No pair shows the "bigger gap → bigger fill" monotone pattern the hypothesis would predict. GBP_USD is monotone in the **wrong** direction: its largest gaps (Brexit-era news shocks) **continue**, not fill — consistent with the full-fill rate falling from 83% to 50% across terciles.

## 5. Diagnostic band (5×RT, NOT the primary test)

Pooled N=478 (264 weekends): net@4h mean +7.2p (p=0.0001), net@12h +4.7p (p=0.0100), net@24h +1.9p (p=0.252). Same shape — effect exists at 4–12h, dies by 24h. Per-pair net@4h means: EUR +6.9 (p=0.0001), JPY +7.2 (p=0.0008), GBP +9.3 (p=0.0006), AUD +5.9 (p=0.0005) — at the looser threshold even GBP fades positively in the first 4h before reversing.

## 6. Honest read

1. **The fade-toward-fill effect is real in-sample but short-lived**: concentrated in the first 4–12h, gone by 24–72h. Multiple-comparison framing: primary family = 4 pairs × 5 horizons = 20 tests, Bonferroni α = 0.05/20 = 0.0025 → survivors are **EUR_USD 4h (p=0.0001) and 12h (p=0.0001)** only; AUD_USD 12h (p=0.0039) narrowly misses; JPY 4h (p=0.0087) misses. The pooled weekend-block 4h result (p=0.0002; family of 5 → α=0.01) also survives.
2. **The 120h upticks (JPY p=0.025, pooled p=0.039) are not credible** — no support at 72h, huge intervening MAE (p50 57–78p), and they vanish under Bonferroni. Treat as drift/noise.
3. **GBP_USD contradicts the hypothesis at the qualifying threshold** (N=18, net negative from 12h on, monotone continuation in gap size). Do not fade large GBP gaps.
4. **N is small for a per-pair strategy**: 44–68 qualifying events per pair over 8 years. GBP's 18 is too small for any conclusion. Any confirm-stage test should be pooled (weekend-blocked) with GBP excluded or down-weighted, pre-registered on 2022+ OOS.
5. **Headroom multiples overstate reality**: entry is at the Sunday open — the most illiquid pricing print of the week. Live weekend-open spreads run several times the theoretical RT used here (EUR 2.0p etc.), and the 10×RT qualification itself was computed with normal-session RT. Exit-free MFE (headroom 8–13× at 4h) is not an EV claim; realistic weekend-open friction plus the MAE p50 of 3–13p at 4h materially compresses it.
6. **Event-driven gaps are regime-dependent**: the qualifying set is dominated by scheduled/news weekends (elections, referenda, crisis Sundays). The 2014–2021 sample includes Brexit and COVID; a 2022+ OOS confirm must expect a different mix.

**Verdict (explore-stage)**: HYPOTHESIS PARTIALLY SUPPORTED — a fast (≤12h) partial gap-fill tendency exists for EUR_USD (Bonferroni-robust) and pooled majors, with median 50%-fill in 1–2h. The "multiday" framing is rejected: no reliable toward-fill edge beyond 12–24h. If pursued, the confirm candidate is a **short-horizon (≤12h) fade on EUR_USD-like liquid USD majors, excluding GBP**, pre-registered against locked 2022+ OOS with realistic weekend-open friction.

## Artifacts

- Script: `tools/weekend_gap_fill_explore.py` (seed 20260724, 10k bootstrap; asserts OOS lock and no-lookahead)
- JSON: `bt-results/weekend_gap_fill_multiday-2026-07-24.json` (per-event lists included for both thresholds)
- This report: `reports/weekend_gap_fill_multiday-2026-07-24.md`
