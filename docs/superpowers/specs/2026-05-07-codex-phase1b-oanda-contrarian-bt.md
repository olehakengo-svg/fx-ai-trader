# Codex Task — Phase 1b: OANDA Contrarian Sentiment BT

- **Repo**: `/Users/jg-n-012/test/fx-ai-trader/`
- **Parent context**: Phase 1a (`get_oanda_labs_sentiment` in dexter) merged at `c82475e`. OANDA labs GraphQL provides 90d × H4 retail sentiment for 16 pairs; this BT validates the contrarian thesis.
- **Scope**: 1 Python BT script + 1 markdown report + 1 results parquet. ~400-600 lines Python. Reuse `bb_squeeze_rescue_bt.py` utilities.
- **Created**: 2026-05-07
- **Style guide**: mirrors `scripts/phase5_d1_bb_mr_tfgrid_bt.py` (PHASE5 BT family)

This file is the **Codex-ready prompt**. Section 11 has the paste-able prompt body.

## 1. Hypothesis

> When OANDA retail sentiment is **extreme** for an FX pair, the next several H4 bars exhibit **mean reversion** in the opposite direction. Specifically, when `short_pct ≥ T_high` we go long; when `short_pct ≤ T_low` we go short.

This is the classic retail-as-contrarian-indicator hypothesis (IG SSI / FXCM SSI 系の文献的下敷き)。Phase 1b validates whether OANDA's pool exhibits the same property at H4 resolution over the most recent 90 days.

## 2. Mirror pattern (read first)

- `scripts/phase5_d1_bb_mr_tfgrid_bt.py` — PHASE5 BT structure (argparse, cell grid, Bonferroni, Wilson, WF, friction)
- `scripts/bb_squeeze_rescue_bt.py` — provides shared utilities: `wilson_lower`, `welch_t_test`, `simulate_pnl`, `PIP_MULT`, `FRICTION_RT`, `synth_null_trades`
- `scripts/phase5_d3_zscore_mom_tfgrid_bt.py` — argparse + report-writing convention

Stay strictly inside this script style. Do NOT introduce a new framework, DataFrame library, or directory.

## 3. Files

### Create

- `scripts/phase1b_oanda_contrarian_bt.py` — the BT
- `data/sentiment/oanda_labs_h4_90d.parquet` — fetched sentiment cache (script writes this on first run, refreshed if older than 12h)
- `bt-results/phase1b/oanda_contrarian_cells.parquet` — full per-cell grid result
- `bt-results/phase1b/oanda_contrarian_report.md` — markdown report

### NOT modify

This task is self-contained. No edits to existing strategies, gates, or DB schema. No env changes.

## 4. Inputs

### 4.1 Sentiment data (fetched at run time)

Endpoint:
```
POST https://labs-api.oanda.com/graphql
Headers:
  Content-Type: application/json
  Origin: https://www.oanda.jp           ← REQUIRED
  Referer: https://www.oanda.jp/lab-education/oanda_lab/oanda_rab/orderbook_history/
  User-Agent: Mozilla/5.0
```

Variables: `{ instrument: "<PAIR>", granularity: "H4", timeSpan: "NINETY_DAYS" }`.

Query (copy verbatim):
```graphql
query GetSentiments($instrument: String!, $granularity: Granularity!, $timeSpan: TimeSpan!) {
  sentiments(instrument: $instrument, granularity: $granularity, timeSpan: $timeSpan) {
    sentiments { sentiment { shortPercent } time }
  }
}
```

Response shape (verified 2026-05-07): see `reference_oanda_labs_api.md` in the user's auto-memory or the dexter `get_oanda_labs_sentiment` reference implementation. List is **most-recent-first**, server returns ~541 points per pair.

Save merged DataFrame to `data/sentiment/oanda_labs_h4_90d.parquet` with columns: `pair, time_utc, short_pct, long_pct`.

### 4.2 OHLC data (MASSIVE)

Read from `data/cache/massive/<PAIR>_1h.parquet`. **MASSIVE has only 1h, not 4h** — resample 1h → 4h:
- 4h bars start at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
- aggregate: open=first, high=max, low=min, close=last
- drop incomplete final bar if not all 4 hours present

### 4.3 Pair set (intersection of OANDA labs 16 ∪ MASSIVE 6)

```python
PAIRS = ["EUR_USD", "USD_JPY", "GBP_USD", "EUR_JPY", "GBP_JPY", "EUR_GBP"]
```

XAU/XAG excluded per `feedback_exclude_xau.md`. AUD/CAD/CHF/NZD pairs not in MASSIVE.

## 5. Cell grid

```python
THRESHOLDS_HIGH = [65, 70, 75, 80, 85, 90]   # short_pct >= T → long
THRESHOLDS_LOW  = [35, 30, 25, 20, 15, 10]   # short_pct <= T → short
HOLDING_BARS_H4 = [1, 2, 4, 12]              # 4h, 8h, 1d, 2d
```

Total cells: `6 pairs × (6 high + 6 low) × 4 holdings = 288` → `α_cell = 0.05 / 288 = 1.74e-4`.

For each cell:
- entry: at H4 close where condition triggers
- exit: at close of the N-th H4 bar after entry (no SL/TP, simple bar-count exit for sanity BT)
- friction: apply `FRICTION_RT` from `bb_squeeze_rescue_bt.py` per round-trip
- pnl: in pips (use `PIP_MULT[pair]`)
- min N for inclusion: **20 trades**; cells with fewer dropped from Bonferroni denominator (m_used = #cells with N ≥ 20)

## 6. Statistical evaluation per cell

| Metric | Formula |
|---|---|
| N | trade count (after min filter) |
| WR | wins / N |
| Wilson 95% lo | `wilson_lower(wins, N, 0.95)` from bb_squeeze_rescue_bt |
| EV | mean pnl_pips per trade |
| PF | sum(positive pnl) / abs(sum(negative pnl)) |
| Kelly | Wilson_lo × payoff − (1 − Wilson_lo). Bound to [-1, 1]. |
| MaxDD | running max - cum equity, % of starting |
| t-stat vs null=0 | Welch t-test pnl_pips vs zero, two-sided p |
| Bonferroni pass | `p < α_cell` AND `Wilson_lo > 0.50` (long signals win-rate) |

Survivor criteria (ALL must hold):
- N ≥ 20
- p < α_cell (Bonferroni)
- Wilson_lo ≥ 0.50 for long signals (sym for short)
- PF ≥ 1.10
- Kelly > 0
- friction-adjusted EV > 0

## 7. Walk-forward (cell robustness)

Split 90 days into:
- **In-sample**: first 60 days
- **OOS**: last 30 days

For each cell:
- Compute in-sample stats (Bonferroni gate)
- Compute OOS stats (nominal Wilson + sign-agreement)
- WF pass: in-sample is survivor AND OOS WR > 0.50 AND OOS PF > 1.0

## 8. Regime split (additional sanity)

Split 90 days into 3 chunks of 30 days.
For each cell:
- Compute PF in each chunk
- Sign agreement: 3/3 chunks PF > 1.0 = strong, 2/3 = weak, ≤1/3 = noise

## 9. Output: `bt-results/phase1b/oanda_contrarian_report.md`

### Required sections

1. **Header** — run timestamp, pair set, cell grid summary, total cells, m_used (after min N filter), α_cell
2. **Top-level verdict** — one of:
   - `SURVIVOR(s) FOUND` — N cells passed all gates
   - `NULL` — 0 cells passed Bonferroni; honest hypothesis-rejection report
3. **Survivor table** (if any) — sorted by Wilson_lo desc:
   - pair / direction / threshold / holding / N / WR / Wilson_lo / EV(p) / PF / Kelly / MaxDD / WF status / regime sign-agreement
4. **Per-pair best cell** — best non-passing cell per pair to surface near-misses
5. **Failure mode analysis** (if NULL) — narrative covering:
   - Median Wilson_lo across all cells
   - Median PF across all cells
   - Whether direction was right but N too low (Type II) vs direction wrong (rejection)
   - Whether regime split shows any consistent direction even if statistical power is missing
6. **Honest caveats** — 90d window is short, sentiment data not available before 2026-02-06, will need cron polling to extend. Document per `feedback_partial_quant_trap.md`.

If 0 cells survive, **do NOT close out the hypothesis**. Per `feedback_success_until_achieved.md`, write a "where to look next" section: try longer holdings, try thresholds beyond 90, try different pair-of-pairs cross signals, etc.

## 10. Commands the BT must support

```bash
# Default run (fetches sentiment, runs grid, writes report)
python scripts/phase1b_oanda_contrarian_bt.py

# Use cached sentiment (skip fetch)
python scripts/phase1b_oanda_contrarian_bt.py --no-fetch

# Re-fetch sentiment regardless of cache age
python scripts/phase1b_oanda_contrarian_bt.py --force-fetch

# Limit to one pair for debugging
python scripts/phase1b_oanda_contrarian_bt.py --pair EUR_USD
```

## 11. Codex prompt (paste this)

```
Repo: fx-ai-trader (current working directory)
Working dir: /Users/jg-n-012/test/fx-ai-trader/

Task: Implement a Phase 5-style BT script `scripts/phase1b_oanda_contrarian_bt.py` that tests the OANDA retail-contrarian hypothesis on the most recent 90 days of H4 data.

Read these files first to learn the project's BT conventions:
- scripts/phase5_d1_bb_mr_tfgrid_bt.py (cell grid + Bonferroni + Wilson + WF)
- scripts/phase5_d3_zscore_mom_tfgrid_bt.py (argparse + report writing)
- scripts/bb_squeeze_rescue_bt.py (provides utilities you must reuse: wilson_lower, welch_t_test, simulate_pnl, PIP_MULT, FRICTION_RT, synth_null_trades)

Then implement per spec:
docs/superpowers/specs/2026-05-07-codex-phase1b-oanda-contrarian-bt.md

Critical points (also in spec):

1. Sentiment data source: POST https://labs-api.oanda.com/graphql, no auth, REQUIRED header `Origin: https://www.oanda.jp` (without it the API returns INTERNAL_ERROR). Use Python `requests`. Save to data/sentiment/oanda_labs_h4_90d.parquet, refresh if older than 12h.

2. Pair set is the intersection of OANDA labs 16 and MASSIVE 6: EUR_USD, USD_JPY, GBP_USD, EUR_JPY, GBP_JPY, EUR_GBP. Exclude XAU per project rule.

3. MASSIVE has only 1h bars at data/cache/massive/<PAIR>_1h.parquet. You MUST resample 1h → 4h aligned to 00/04/08/12/16/20 UTC. Drop trailing incomplete 4h bars.

4. Cell grid: 6 pairs × (6 high thresholds + 6 low thresholds) × 4 holding periods = 288 cells. α_Bonferroni = 0.05 / 288. Min N=20 per cell for inclusion (denominator becomes m_used = cells with N ≥ 20).

5. Survivor criteria (ALL must hold): p < α_Bonferroni AND Wilson_lo > 0.50 AND PF ≥ 1.10 AND Kelly > 0 AND friction-adjusted EV > 0.

6. Walk-forward: 60-day in-sample / 30-day OOS. WF pass = in-sample survivor + OOS WR > 0.50 + OOS PF > 1.0.

7. Regime split: 3×30d chunks, sign-agreement {3/3, 2/3, ≤1/3}.

8. Outputs:
   - data/sentiment/oanda_labs_h4_90d.parquet (sentiment cache)
   - bt-results/phase1b/oanda_contrarian_cells.parquet (full grid)
   - bt-results/phase1b/oanda_contrarian_report.md (markdown report per spec §9)

9. Friction must use FRICTION_RT from bb_squeeze_rescue_bt.py (do not invent your own).

10. CLI flags: default run, --no-fetch, --force-fetch, --pair <PAIR>.

11. NULL case: if 0 cells survive, do NOT short-circuit closure. Write a structured failure-mode analysis section per spec §9.5 (per project rule feedback_success_until_achieved.md).

12. Honor feedback_bt_must_use_massive.md: only data/cache/massive/*.parquet for OHLC. Do NOT use Yahoo or any other source.

Done conditions:
- Script runs end-to-end with default flags from a clean state on this repo
- Outputs all 3 files listed above
- Markdown report renders cleanly (no broken table syntax)
- typecheck/lint as appropriate to repo (this is Python; just don't add new dependencies)

Stop and ask if anything is ambiguous. The Origin header, pair set, cell grid, and survivor criteria are non-negotiable.

When done, report: list of created files with sizes, the verdict (SURVIVORS / NULL), and if SURVIVORS the count and best cell summary.
```

## 12. Out of scope (explicit non-goals)

- Live shadow integration into fx-ai-trader's promotion engine — Phase 1d
- Cron polling to extend sentiment history beyond 90 days — Phase 1c
- Cross-validation against Myfxbook Outlook or COT data — Phase 1e (optional)
- Plugging the survivor cells into existing MR strategies as a filter — Phase 2
- New external dependencies — keep the script self-contained on `requests`, `pandas`, `numpy`, `pyarrow`/`fastparquet` already in the project

## 13. Risks & mitigations

| Risk | Mitigation |
|---|---|
| 90d window covers only 2 regime states | Regime split + WF on 60/30 + honest report on coverage limits |
| 288 cells × Bonferroni is harsh, possible 0 survivors | Survivor=0 is acceptable per shadow-first paradigm. Failure-mode section makes it productive even when null. |
| Sentiment timestamp ≠ MASSIVE timestamp | Forward-fill sentiment to next H4 close, document the join logic |
| API rate limit (1 fetch per pair) | 6 pairs × 1 call = trivial. Add 1s sleep between calls anyway. |
| Sentiment server-clock skew | Server returns ISO 8601 UTC, we trust it |
| MASSIVE 1h not covering full 90d | Detect and shorten BT window to MASSIVE coverage; don't pad with NaNs |

## 14. Why this is the right next step

`feedback_shadow_first_quant_architecture.md` — BT is sanity-filter first, then shadow. Phase 1a delivered the data tap; Phase 1b is the sanity filter. Cells that survive go to shadow (Phase 1d), cells that don't are honestly reported and dropped.

`feedback_partial_quant_trap.md` — full PF/Wilson/Bonferroni/WF battery is built in by design. No N/WR-only shortcuts.

`feedback_success_until_achieved.md` — null result is not closure; failure-mode section channels next-step inquiry.
