# TradingView Pine Overlays

Pine Script overlays that visualize fx-ai-trader strategy signals on a live
TradingView chart. Each `.pine` file mirrors the production signal logic of a
specific strategy so traders can validate signals visually on real-time
candles.

## Price-Shock Reversion (Phase B-1, Shadow, 2026-05-18)

Tier 1 family of 5 strategies (commit 35961351) deployed under Shadow with
a pre-reg LOCK on the Live promote criteria
(`knowledge-base/wiki/decisions/price-shock-rev-promote-criteria-2026-05-18.md`).

| Pair    | TF | Horizon | Vol Q | BT N | WR     | Wilson_lo | PF    | EV (pip) | Overlay |
|---------|----|---------|-------|------|--------|-----------|-------|----------|---------|
| EUR_GBP | H1 | 3       | Q5    | 239  | 72.8 % | 0.668     | 14.75 | +55.81   | [price_shock_rev_eur_gbp_h1_long.pine](price_shock_rev_eur_gbp_h1_long.pine) |
| EUR_AUD | H1 | 12      | Q5    | 262  | 67.6 % | 0.617     | 4.05  | +58.77   | [price_shock_rev_eur_aud_h1_long.pine](price_shock_rev_eur_aud_h1_long.pine) |
| USD_CAD | H1 | 3       | Q5    | 247  | 66.4 % | 0.603     | 5.30  | +28.66   | [price_shock_rev_usd_cad_h1_long.pine](price_shock_rev_usd_cad_h1_long.pine) |
| NZD_JPY | H1 | 12      | Q5    | 303  | 64.0 % | 0.585     | 5.02  | +58.88   | [price_shock_rev_nzd_jpy_h1_long.pine](price_shock_rev_nzd_jpy_h1_long.pine) |
| AUD_JPY | H1 | 12      | ALL   | 426  | 63.8 % | 0.592     | 2.54  | +32.25   | [price_shock_rev_aud_jpy_h1_long.pine](price_shock_rev_aud_jpy_h1_long.pine) |

> BT source: commit 63c7cf18 (`tools/price_shock_reversion_bt.py` against the
> full history of each MASSIVE H1 parquet under `data/cache/massive/`).
> EUR_GBP and EUR_AUD additionally share a portfolio sizing lock — only one
> live position at a time across the two strategies.

### Visual elements

Each overlay plots, on the host pair's H1 chart:

- **Red dotted line** — the next-bar close price equivalent of the rolling
  1 % log-return threshold (i.e. the price at which the closing log-return
  would equal the lower 1 % percentile of the previous 252 H1 bars).
- **Yellow background band** — bars where `vol20` falls in the rolling Q5
  bucket (top 20 % of the previous 252 bars). Suppressed for `AUD_JPY`
  because that pair runs with `vol_q="ALL"` (no vol filter).
- **Green ▲ "SHOCK"** — the bar that fires the shock-reversion signal.
  Production enters at the next bar's open (visually indicated by a smaller
  lime arrow on the next bar).
- **Grey "EXIT h=N" label** — N bars after the signal, illustrating the
  horizon time-stop (3 or 12 H1 bars depending on the strategy).
  The catastrophic `−2 × ATR-proxy` SL exit is not drawn on the chart; the
  overlay is a signal/timing visualizer, not a full P&L simulator.
- **Stats table (top-right)** — pre-reg constants and BT results from the
  table above, plus the source commit.

### How to load on TradingView

1. Open TradingView Desktop and switch the active chart to the relevant
   `OANDA:<PAIR>` symbol on the H1 (60 min) timeframe.
2. Open the Pine Editor, choose **Open → New** and paste the contents of
   the corresponding `.pine` file from this directory.
3. Click **Save** then **Add to chart**.
4. The shock markers, threshold line, and Q5 background appear on the
   active chart. Hover over a SHOCK triangle to inspect the H1 bar.

> ⚠️ **Known TV MCP limitation:** as of 2026-05 the Pine Editor's
> "Add to chart" button is not exposed to the MCP `pine_smart_compile`
> tool (script saves cleanly, but `study_added` returns `false`). The
> overlays must be added to the chart manually via the steps above.
> This affects the screenshot pipeline only — it does not affect the
> overlay logic.

### Equivalence vs. the production strategy base

The Pine logic in every `.pine` file is asserted to be exactly equivalent
to the Python signal mask of the production strategy class:

- Python side: `strategies.hourly.price_shock_reversion_base
  .PriceShockReversionBase.signal_mask_from_dataframe`.
- Equivalence: `tests/test_pine_overlay_equivalence.py`. The test
  re-implements the Pine logic line-for-line in pandas (mirroring
  `ta.percentile_linear_interpolation` with `series.shift(1).rolling(N)
  .quantile(...)` and `ta.stdev(_, _, biased=false)` with `std(ddof=1)`)
  and compares against the production mask on the **real MASSIVE H1
  parquet** for each pair across the full history (no mock data).

To run the equivalence checks alone:

```sh
python3 -m pytest tests/test_pine_overlay_equivalence.py -x -q
```

12 tests must pass (5 last-1000-bar checks + 5 full-history checks +
2 structural checks).

### Pre-reg LOCK guarantee

`PERCENTILE`, `HORIZON_BARS`, and `VOL_Q` are pre-reg LOCK constants —
they must not be tuned post-hoc. The test
`test_overlay_files_declare_locked_constants` enforces that the literal
values in each `.pine` file match the corresponding production strategy
config. If you need to explore a different parameter cell, queue a new
BT task and treat it as a new family (per
`feedback_partial_quant_trap.md` and
`feedback_label_empirical_audit.md`).

## Other overlays

| File | Strategy |
|------|----------|
| [macd_rsi_pullback-replica.pine](macd_rsi_pullback-replica.pine) | macd_rsi_pullback (1H + H1 RSI bias, OANDA-friction) |
| [macd_1m_scalp-london.pine](macd_1m_scalp-london.pine), [-ny.pine](macd_1m_scalp-ny.pine), [-tokyoBuy.pine](macd_1m_scalp-tokyoBuy.pine) | macd_1m_scalp session-specific replicas |
| [xs_momentum-replica.pine](xs_momentum-replica.pine) | xs_momentum-replica |
| [trendline_sweep-EURUSD-15m-365d-2026-05-13.pine](trendline_sweep-EURUSD-15m-365d-2026-05-13.pine) | trendline_sweep |

## Screenshots

Captured TradingView screenshots are kept under
[screenshots/](screenshots/). The Price-Shock overlays currently have a
**baseline** (no-overlay) capture only, because of the TV MCP
"Add to chart" limitation noted above. Overlay screenshots will be
added once the indicators are manually loaded onto each pair's H1 chart.
