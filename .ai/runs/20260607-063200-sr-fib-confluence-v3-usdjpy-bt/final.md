# sr_fib_confluence V3 USD_JPY BT final

Status: R3_CATASTROPHIC_GATE_PASS / TV_EDGE_REPLICATION_FAIL

## Run

- Command: `SR_FIB_CONFLUENCE_BT_TARGETS=USD_JPY SR_FIB_CONFLUENCE_BT_OUTFILE=bt-results/sr_fib_confluence-redesign-v3-usdjpy-2026-06-03.json .venv/bin/python tools/sr_fib_confluence_redesign_v3_bt.py`
- Output: `bt-results/sr_fib_confluence-redesign-v3-usdjpy-2026-06-03.json`
- Data source: `data/cache/massive/USD_JPY_15m.parquet`
- Guard: `BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`, no Yahoo fallback
- Bars fetched: 6025

## USD_JPY A/B result

| Cell | N | WR | PF | PnL | EV | Verdict |
|---|---:|---:|---:|---:|---:|---|
| current legacy | 74 | 41.89% | 0.6835 | -25.1123 | -0.3394 | baseline |
| proposed V3 | 101 | 34.65% | 0.6463 | -31.4131 | -0.3110 | PASS by catastrophic-only gate |

R3 v2.1 gate result: PASS. The only reject condition is baseline PnL > 0 and proposed PnL < 0. Baseline PnL was already negative, so `pnl_sign_preserved=true`.

## TV vs Codex proposed

| Metric | TV USD_JPY M15 365d | Codex prod BT USD_JPY | Delta | Within +/-20% |
|---|---:|---:|---:|---|
| N | 467 | 101 | -78.37% | NO |
| WR | 40.69% | 34.65% | -6.04 pp | YES |
| PF | 1.29 | 0.6463 | -49.90% | NO |
| PnL | +6.26 | -31.4131 | sign mismatch | NO |

Conclusion: the catastrophic shadow-first gate passes, but Codex prod BT did not reproduce the TradingView USD_JPY edge. This is not sufficient evidence for Live promotion.

## EUR_USD vs USD_JPY

| Source | Pair | N | WR | PF | PnL | Read |
|---|---|---:|---:|---:|---:|---|
| TV | EUR_USD | 529 | 37.62% | 1.194 | +4.12 | good |
| TV | USD_JPY | 467 | 40.69% | 1.29 | +6.26 | strongest TV candidate |
| Codex prior full V3 BT | EUR_USD | 341 | 37.54% | 0.7603 | -64.3325 | negative prod-path BT |
| Codex prior full V3 BT | USD_JPY | 406 | 37.44% | 0.7595 | -78.3724 | negative prod-path BT |
| Codex current USD_JPY-only BT | USD_JPY | 101 | 34.65% | 0.6463 | -31.4131 | negative shorter cache window |

TV supports USD_JPY over EUR_USD. Codex prod-path BT does not support either pair for Live promotion. If shadow-first work continues, USD_JPY is still the better investigation target because TV ranked it highest, but it should remain shadow-only until the TV/Codex discrepancy is explained.

## Shadow ramp plan

1. Keep `SR_FIB_CONFLUENCE_REDESIGN_V3` and `SR_FIB_CONFLUENCE_REDESIGN_V3_SHADOW_PROMOTE` default-off.
2. Run USD_JPY V3 in shadow only for 60-90 days or until N>=30 live-shadow observations.
3. Before Live promotion, reconcile the data-window mismatch: current MASSIVE cache produced 6025 fetched bars, while the earlier full V3 BT file recorded about 24508 bars for USD_JPY.
4. Require live-shadow evidence to show positive PnL/PF direction before any execution promotion, even though the formal R3 gate is catastrophic-only.

## Self-review

- V3 path is selected through `SR_FIB_CONFLUENCE_REDESIGN_V3=1`.
- USD_JPY MASSIVE parquet exists and was used.
- `BT_REQUIRE_MASSIVE_CACHE=1` is forced by the runner.
- v2.1 catastrophic check only was applied; PF and Wilson changes are warn-only.
- `bt-results/sr_fib_confluence-redesign-v3-usdjpy-2026-06-03.json` was generated.
