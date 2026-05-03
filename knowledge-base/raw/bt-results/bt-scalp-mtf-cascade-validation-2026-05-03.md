# BT Scalp MTF Cascade Validation - 2026-05-03

Status: blocked.

## Verdict

The M15/M5 inject fix is not observable end-to-end in the current checkout because the prescribed standard BT command fails before trade evaluation. The immediate blocker is the standard `run_scalp_backtest` data loader path, not the strategy logic: `fetch_ohlcv()` never falls back to the existing local parquet cache, so `run_scalp_backtest("USDJPY=X", lookback_days=180, interval="5m")` exits with `All data sources failed for USDJPY=X/5m`.

## Required Command Results

### 1. Regression test rerun

Command:

```bash
python3 -m pytest tests/test_bt_htf_m15_m5_inject.py -v
```

Result:

```text
collected 0 items
ERROR: file or directory not found: tests/test_bt_htf_m15_m5_inject.py
```

Finding: the task's required regression file is not present in the current worktree. Earlier run evidence exists under `.ai/runs/20260503-024932-20260503-0240-bt-scalp-htf-m15-m5-inject/events.jsonl`, but this rerun could not be executed from the current repo state.

### 2. Standard BT invocation

Command:

```bash
python3 -c "
from app import run_scalp_backtest
r = run_scalp_backtest('USDJPY=X', lookback_days=180, interval='5m')
trades = r.get('trades') or r.get('records') or []
n = sum(1 for t in trades if t.get('entry_type') == 'mtf_regime_trend_cascade_scalp')
print('standard_bt_n_for_mtf_regime_trend_cascade_scalp:', n)
"
```

Observed result:

```text
ValueError: All data sources failed for USDJPY=X/5m
```

Returned payload summary:

```text
{'error': 'All data sources failed for USDJPY=X/5m', 'all_trades': 0, 'mtf_n': 0, 'mtf_wr_pct': 0.0, 'mtf_ev_pips': 0.0, 'mtf_pf': 0.0}
```

ROOT CAUSE: standard BT data load failed before any strategy could be counted. Source evidence:

- `run_scalp_backtest()` calls `fetch_ohlcv(symbol, period=fetch_period, interval=interval)` at [app.py](/Users/jg-n-012/test/fx-ai-trader/app.py:5363).
- `fetch_ohlcv()` only tries Massive when `MASSIVE_API_KEY` is set, then OANDA when `OANDA_TOKEN` is set, then yfinance; on total failure it raises at [modules/data.py](/Users/jg-n-012/test/fx-ai-trader/modules/data.py:587) and [modules/data.py](/Users/jg-n-012/test/fx-ai-trader/modules/data.py:667).
- The repo does contain local parquet cache files, including `data/cache/massive/USD_JPY_5m.parquet`, but the standard loader path does not consult them.

### 3. Vectorized harness oracle

The direct current-turn rerun could not be completed to a fresh numeric result within this sandboxed turn, but the repo contains prior local-cache oracle evidence for the same strategy/window family:

- `mtf_regime_trend_cascade_scalp` strategy note records vec BT on local Massive cache at [knowledge-base/wiki/strategies/mtf-regime-trend-cascade-scalp.md](/Users/jg-n-012/test/fx-ai-trader/knowledge-base/wiki/strategies/mtf-regime-trend-cascade-scalp.md:92):

| Pair | N | WR | EV | PF |
|---|---:|---:|---:|---:|
| USD_JPY | 13 | 46.2% | +5.6p | 2.99 |

- The later v2.3 audit records improved USD_JPY 180d vec-side results with H1 macro gate at [knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md](/Users/jg-n-012/test/fx-ai-trader/knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md:172):

| Version | USD_JPY 180d N | EV | PF |
|---|---:|---:|---:|
| v2.3 + h1 macro gate | 57 | +2.93p | 1.88 |

These are prior in-repo oracle records, not fresh recomputation from this turn.

## Residual Standard-BT Gate Gap

Even after the data-load blocker is fixed, the standard scalp BT still has a second likely blocker: `mtf_regime_trend_cascade_scalp` is not listed in the `QUALIFIED_TYPES` set at [app.py](/Users/jg-n-012/test/fx-ai-trader/app.py:5537). `modules/demo_trader.py` does register it for production routing according to the prior analysis at [knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md](/Users/jg-n-012/test/fx-ai-trader/knowledge-base/wiki/analyses/mtf-regime-trend-cascade-null-finding-2026-04-30.md:212), so standard BT and production routing are currently out of sync.

Because the prescribed standard BT command never reached trade evaluation, I cannot prove in this turn that the missing `QUALIFIED_TYPES` entry is the runtime cause of `N=0`. I can prove it is a source-level gap that would suppress this strategy even if the loader succeeded.

## Gap Analysis

- Standard BT (fresh current-turn run): N=0, WR=0.0%, EV=0.0p, PF=0.0 because the command failed before producing trades.
- Vec harness (fresh current-turn rerun): unavailable in this sandboxed turn.
- Vec oracle (prior in-repo evidence): USD_JPY local-cache runs previously showed positive N and positive EV/PF.

Conclusion: the M15/M5 inject fix cannot be signed off as end-to-end observable from the standard BT path in the current checkout. The immediate failure is the standard data-loading path; the next likely failure after that is the missing `QUALIFIED_TYPES` registration in `run_scalp_backtest`.

## Exact Evidence Needed Next

1. Restore or re-add `tests/test_bt_htf_m15_m5_inject.py` so the required regression can be rerun from the current worktree.
2. Run the standard BT in an environment where at least one of these is true:
   - `MASSIVE_API_KEY` is available, or
   - OANDA/yfinance network access is available, or
   - `fetch_ohlcv()` is intentionally updated in a separate task to read the existing local parquet cache.
3. After the loader issue is resolved, rerun the exact standard BT command and confirm whether `mtf_regime_trend_cascade_scalp` still stays at N=0 due to omission from `QUALIFIED_TYPES` at [app.py](/Users/jg-n-012/test/fx-ai-trader/app.py:5537).
