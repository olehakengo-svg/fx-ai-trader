# PRIME Re-evaluation 2026-05-18

## Data

- Source: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=10000`
- Fetched rows: 6449; shadow rows: 5637; WIN/LOSS shadow non-XAU rows: 5115
- API coverage observed: 2026-04-02 08:17:17 UTC to 2026-05-18 07:24:20 UTC
- MASSIVE feature joins: 5115 / 5115
- Baseline WR: 1367/5115 = 26.7%

## Recomputed EDGES

```python
EDGES = {
    "confidence": [
        54.0,
        64.0,
        71.0
    ],
    "rj_adx": [
        18.525844,
        24.084449,
        31.282508
    ],
    "rj_atr_ratio": [
        0.926959,
        0.983332,
        1.091413
    ],
    "rj_close_vs_ema200": [
        -0.281692,
        -0.00188,
        0.009222
    ]
}
```

## Task A Verdicts

| name | tier current | N | WR | Wlo | Fisher p | Bonf p x6 | WF | Kelly | spread-adj EV | verdict |
|---|:---:|---:|---:|---:|---:|---:|---|---:|---:|:---:|
| stoch_trend_pullback_PRIME | A | 22 | 31.8% | 0.164 | 0.37 | 1 | 2/3 | 0.000 | -1.13 | DEMOTE |
| stoch_trend_pullback_LONDON_LOWVOL | B | 18 | 27.8% | 0.125 | 0.549 | 1 | 1/3 | 0.000 | -1.82 | DEMOTE |
| fib_reversal_PRIME | A | 28 | 42.9% | 0.265 | 0.0472 | 0.283 | 1/3 | 0.000 | -1.53 | DEMOTE |
| bb_rsi_reversion_NY_ATRQ2 | B | 48 | 33.3% | 0.217 | 0.189 | 1 | 0/3 | 0.000 | -2.96 | DEMOTE |
| engulfing_bb_TOKYO_EARLY | C | 23 | 30.4% | 0.156 | 0.42 | 1 | 1/3 | 0.000 | -2.53 | KEEP |
| sr_fib_confluence_GBP_ADXQ2 | B | 19 | 42.1% | 0.231 | 0.107 | 0.642 | 2/3 | 0.003 | +0.12 | DEMOTE |

## Sanity Drift

- fib_reversal_PRIME: freeze N=12 WR=75.0% EV=+2.96p; new N=28 WR=42.9% EV=-1.53p; PRIME drift detected

## Task B Best Cells

- Tested hypotheses: 4608 (Bonferroni alpha=1.085e-05)
- Bonferroni-pass selected cells: 0
- FDR BH q=0.10 pass cells: 0
- Full cell table artifact: `research/prime_reeval_task_b_cells.csv`

| strategy | best cell | N | WR | Wlo | Fisher p | Bonf p x4608 | FDR q10 | WF | Kelly | PF | spread-adj EV | selected |
|---|---|---:|---:|---:|---:|---:|:---:|---|---:|---:|---:|:---:|
| gbp_deep_pullback | gbp_deep_pullback_TOKYO_ATRQ4_ADXQ3_GBP_USD_BUY | 1 | 100.0% | 0.207 | 0.267 | 1 | N | 1/3 | 0.000 | inf | +39.10 | NO |
| orb_trap | orb_trap_OVERLAP_ATRQ3_ADXQ1_GBP_USD_SELL | 11 | 54.5% | 0.280 | 0.0466 | 1 | N | 2/3 | 0.230 | 6.36 | +8.44 | NO |
| ob_retest | ob_retest_OVERLAP_ATRQ1_ADXQ4_USD_JPY_BUY | 11 | 63.6% | 0.354 | 0.0111 | 1 | N | 2/3 | 0.263 | 5.72 | +13.73 | NO |
| trend_rebound | trend_rebound_TOKYO_ATRQ1_ADXQ1_USD_JPY_BUY | 1 | 100.0% | 0.207 | 0.267 | 1 | N | 1/3 | 0.000 | inf | +1.30 | NO |
| dt_sr_channel_reversal | dt_sr_channel_reversal_LONDON_ATRQ3_ADXQ4_USD_JPY_BUY | 4 | 75.0% | 0.301 | 0.061 | 1 | N | 2/3 | 0.153 | 2.57 | +3.50 | NO |
| wick_imbalance_reversion | wick_imbalance_reversion_TOKYO_ATRQ3_ADXQ1_GBP_USD_BUY | 5 | 100.0% | 0.566 | 0.00136 | 1 | N | 3/3 | 0.000 | inf | +15.80 | NO |

## Task B Near Misses

Top N>=20 cells by Fisher p; all failed the locked Bonferroni alpha when no selected cell is listed.

| cell | N | WR | Wlo | Fisher p | Bonf p x4608 | WF | Kelly | PF | spread-adj EV |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|

## Replay

- Current hot-fix dry-run URL: `https://fx-ai-trader.onrender.com/api/demo/trades?limit=3000`
- Current hot-fix dry-run 30d PRIME A/B LIVE fires: 71 (new from shadow=66, rows=3009)
- Integer comparison with `tools/prime_gate_order_dry_run.py`: MATCH (71)
- If Task A v2 verdicts were applied to the same dry-run rows: 0 PRIME A/B LIVE fires
- Evaluation-fetch current-gate replay, for reference only: 100 fires on the 10,000-row API fetch

## Verdict

- PRIME drift detected: stoch_trend_pullback_PRIME, stoch_trend_pullback_LONDON_LOWVOL, fib_reversal_PRIME, bb_rsi_reversion_NY_ATRQ2, sr_fib_confluence_GBP_ADXQ2 failed locked keep thresholds.
- New candidate cells selected: 0. NULL result is retained; all six strategies remain shadow.
