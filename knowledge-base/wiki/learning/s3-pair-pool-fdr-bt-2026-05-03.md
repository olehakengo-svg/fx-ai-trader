# S3 Pair-Pool FDR BT 2026-05-03

## Verdict

- Scenario: `Insufficient(cache_missing)`
- BH FDR-significant pairs: 未計算
- Matrix v1 B 帯通過 pairs: 未計算
- Portfolio Sharpe: 未計算
- Diversification ratio: 未計算
- Wave 1 USDJPY regression: 未計算
- Null bootstrap: 未計算
- Regime concentration flags: 未計算
- Recommendation: Phase 1 cache preparation required before statistical verdict.

## 実行結果

Codex sandbox では外部 DNS / process inspection が制限される前提のため、BT は `--use-cache-only` で実行した。現時点では以下の必須キャッシュが存在せず、事前定義どおり `Insufficient(cache_missing)` で停止した。

| Cache | Missing pairs |
|---|---|
| COT | USDJPY, USDCAD, USDCHF, GBPUSD, EURUSD, NZDUSD |
| Price | USDJPY, USDCAD, USDCHF, GBPUSD, EURUSD, NZDUSD |

Raw artifact:
- `knowledge-base/raw/bt-results/s3-pair-pool-fdr-2026-05-03.json`
- `knowledge-base/raw/bt-results/s3-pair-pool-fdr-2026-05-03.md`

## Phase 1 commands

ネットワーク可能な環境で以下を実行して cache を作成する。

```bash
python3 tools/bt/cot_socrata_fetcher.py --pairs USDJPY,USDCAD,USDCHF,GBPUSD,EURUSD,NZDUSD --since 2014-01-07 --until 2026-04-28 --out tools/bt/cot_cache/
python3 tools/bt/cot_socrata_fetcher.py --download-yfinance --pairs USDJPY,USDCAD,USDCHF,GBPUSD,EURUSD,NZDUSD --since 2014-01-01 --until 2026-05-01 --out tools/bt/price_cache/
```

## 実装済み BT surface

- `tools/bt/s3_pair_pool_fdr.py`
  - literal signal mapping: Dealer long change > 0 and short change < 0 = BUY; long < 0 and short > 0 = SELL.
  - next-Friday close to following-Friday close entry/exit.
  - 2 pip round-trip cost.
  - intervention exclusion on/off sensitivity hooks.
  - pair-level matrix v1 metrics: N, WR, PF, Wilson lower bound, IS/OOS PF, Sharpe, Kelly.
  - one-sided t p-value and BH FDR q=0.10, m=6.
  - portfolio Sharpe, diversification ratio, pairwise correlation.
  - null bootstrap, year-by-year WR/PF, regime concentration flags.
  - Scenario C path includes USDJPY extreme-decile sanity.
- `tools/bt/cot_socrata_fetcher.py`
  - CFTC Socrata TFF dataset `gpe5-46if` fetcher.
  - yfinance daily close cache fetcher.
  - Writes one JSON file per pair for offline BT.
- `tests/test_s3_pair_pool_fdr.py`
  - BH rank behavior.
  - literal mapping and next-Friday entry/exit.
  - cache-missing stop.
  - Wave 1 regression tolerance helper.
  - insufficient-cache report writing.

## Verification

```bash
python3 -m pytest -q tests/test_s3_pair_pool_fdr.py
# 5 passed in 1.59s
```

```bash
python3 tools/bt/cot_socrata_fetcher.py --help
# PASS: direct task command import path works and CLI help renders
```

```bash
PYTHONPYCACHEPREFIX=/tmp/fx-ai-trader-pycache python3 -m py_compile tools/bt/s3_pair_pool_fdr.py tools/bt/cot_socrata_fetcher.py
# PASS
```

```bash
python3 tools/bt/s3_pair_pool_fdr.py --use-cache-only --bootstrap-iterations 100 --json-out knowledge-base/raw/bt-results/s3-pair-pool-fdr-2026-05-03.json --md-out knowledge-base/raw/bt-results/s3-pair-pool-fdr-2026-05-03.md
# exit 2, expected: Insufficient(cache_missing)
```

## Notes / risks

- Required Wave 1 reference docs were found under `/Users/jg-n-012/test/wiki/learning/`, not under this repo's `knowledge-base/wiki/learning/`.
- `pgrep -f app.py` failed with `sysmond service not found`; `/bin/ps` also failed with `Operation not permitted`. No Live/Shadow/OANDA data was consulted.
- Statistical verdict remains blocked until Phase 1 caches are generated.
