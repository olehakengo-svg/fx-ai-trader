# Scalp Alt Simple-Structure Pre-registration (LOCKED)

- Date: 2026-05-03
- Engine: `run_scalp_backtest` standard BT only
- Lookback: 180d
- Lineage: direct simple-first execution of `knowledge-base/wiki/decisions/complex-gate-edge-destruction-pattern-2026-05-03.md`.
- Registration to OANDA bridge is out of scope and gated on this verdict.

## LOCKED Thresholds

- Bonferroni K=4; alpha/K=0.0125. Candidate pool is fixed ex ante.
- Promote: N>=30, PF>=1.30, Wilson_lo > BEV_WR + 5pp, WF IS/OOS PF>=1.20, Bonferroni p < 0.0125, max DD <=30%.
- Shadow: N>=30, PF>=1.10, Wilson_lo > BEV_WR, WF IS/OOS PF>=1.00, max DD <=30%.
- Reject: any other configuration.
- Insufficient: N<30 with explicit gap-to-30.
- OVERFIT_SUSPECTED: OOS PF < IS PF * 0.85; downgrade Promote->Shadow or Shadow->Reject.
- BEV_WR: USD_JPY=34.4%, EUR_USD=39.7%.
- Metric note: if `run_scalp_backtest` trade_log lacks literal `pnl_pips`, EV/PF/DD use reconstructed sign-adjusted engine PnL units from `tp_m/sl_m/actual_sl_m`; raw engine output is retained in JSON.

## Verdict Summary

| # | Strategy | Pair | TF | Verdict | N | WR | EV | PF | Bonf p | Overfit | Gap |
|---|---|---|---|---|---:|---:|---:|---:|---:|---|---:|
| 1 | `bb_squeeze_breakout` | USD_JPY | 5m | BT_PENDING | NA | NA | NA | NA | NA | False | 30 |
| 2 | `engulfing_bb` | USD_JPY | 5m | BT_PENDING | NA | NA | NA | NA | NA | False | 30 |
| 3 | `fib_reversal` | EUR_USD | 1m | BT_PENDING | NA | NA | NA | NA | NA | False | 30 |
| 4 | `sr_channel_reversal` | EUR_USD | 5m | BT_PENDING | NA | NA | NA | NA | NA | False | 30 |

## Per-candidate Quant Table

| Strategy | N | Wins/Losses | WR | EV | PF | Wilson 95% CI | max DD pip | max DD % | WF IS PF/OOS PF | WF IS WR/OOS WR | Bonf p | Half-Kelly |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `bb_squeeze_breakout` | NA | NA/NA | NA | NA | NA | [NA, NA] | NA | NA | NA/NA | NA/NA | NA | NA |
| `engulfing_bb` | NA | NA/NA | NA | NA | NA | [NA, NA] | NA | NA | NA/NA | NA/NA | NA | NA |
| `fib_reversal` | NA | NA/NA | NA | NA | NA | [NA, NA] | NA | NA | NA/NA | NA/NA | NA | NA |
| `sr_channel_reversal` | NA | NA/NA | NA | NA | NA | [NA, NA] | NA | NA | NA/NA | NA/NA | NA | NA |

## Candidate Notes

- `bb_squeeze_breakout`: BT_PENDING. missing parent-run JSON: /data/repo/fx-ai-trader/knowledge-base/raw/bt-results/scalp-alt-bb_squeeze-2026-05-03.json.
- `engulfing_bb`: BT_PENDING. missing parent-run JSON: /data/repo/fx-ai-trader/knowledge-base/raw/bt-results/scalp-alt-engulfing-2026-05-03.json.
- `fib_reversal`: BT_PENDING. missing parent-run JSON: /data/repo/fx-ai-trader/knowledge-base/raw/bt-results/scalp-alt-fib-2026-05-03.json.
- `sr_channel_reversal`: BT_PENDING. missing parent-run JSON: /data/repo/fx-ai-trader/knowledge-base/raw/bt-results/scalp-alt-sr-2026-05-03.json.

## Next Task

Parent Claude — execute the four pre-registered --candidate runs, then rerun --aggregate
