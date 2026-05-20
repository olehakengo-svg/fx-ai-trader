# Price-Shock Reversion Phase B-1 Final

## 実装ファイルリスト
- `strategies/hourly/price_shock_reversion_base.py`
- `strategies/hourly/price_shock_rev_eur_gbp_h1_long.py`
- `strategies/hourly/price_shock_rev_eur_aud_h1_long.py`
- `strategies/hourly/price_shock_rev_usd_cad_h1_long.py`
- `strategies/hourly/price_shock_rev_nzd_jpy_h1_long.py`
- `strategies/hourly/price_shock_rev_aud_jpy_h1_long.py`
- `strategies/hourly/__init__.py`
- `modules/demo_trader.py`
- `app.py`
- `tests/test_price_shock_rev_strategies.py`
- `knowledge-base/wiki/strategies/price_shock_rev_*.md`
- `knowledge-base/wiki/decisions/price-shock-rev-promote-criteria-2026-05-18.md`
- `knowledge-base/wiki/tier-master.md`
- `knowledge-base/wiki/tier-master.json`
- `knowledge-base/wiki/index.md`
- `knowledge-base/wiki/changelog.md`
- `CHANGELOG.md`

## git diff --stat HEAD~1
```text
 ...20260518-1352-price-shock-rev-phase-b1-final.md |  92 +++++++++
 CHANGELOG.md                                       |  15 ++
 app.py                                             |  11 +-
 knowledge-base/wiki/changelog.md                   |   7 +
 .../price-shock-rev-promote-criteria-2026-05-18.md |  30 +++
 knowledge-base/wiki/index.md                       |   5 +
 .../strategies/price_shock_rev_aud_jpy_h1_long.md  |  29 +++
 .../strategies/price_shock_rev_eur_aud_h1_long.md  |  29 +++
 .../strategies/price_shock_rev_eur_gbp_h1_long.md  |  30 +++
 .../strategies/price_shock_rev_nzd_jpy_h1_long.md  |  29 +++
 .../strategies/price_shock_rev_usd_cad_h1_long.md  |  29 +++
 knowledge-base/wiki/tier-master.json               |   7 +-
 knowledge-base/wiki/tier-master.md                 |  44 +++--
 modules/demo_trader.py                             |  88 ++++++++-
 strategies/hourly/__init__.py                      |  18 +-
 .../hourly/price_shock_rev_aud_jpy_h1_long.py      |  11 ++
 .../hourly/price_shock_rev_eur_aud_h1_long.py      |  11 ++
 .../hourly/price_shock_rev_eur_gbp_h1_long.py      |  11 ++
 .../hourly/price_shock_rev_nzd_jpy_h1_long.py      |  11 ++
 .../hourly/price_shock_rev_usd_cad_h1_long.py      |  11 ++
 strategies/hourly/price_shock_reversion_base.py    | 211 +++++++++++++++++++++
 tests/test_price_shock_rev_strategies.py           | 101 ++++++++++
 22 files changed, 799 insertions(+), 31 deletions(-)
```

## git log --oneline -3
```text
794392a1 feat(price_shock_rev): Tier 1 family 5 戦略を Phase B-1 Shadow 投入 (rule:R1)
792bd83f chore(codex): claim 20260518-1352-price-shock-rev-phase-b1
6e234989 chore(codex): recover 1 orphaned running task(s)
```

## pytest
Command: `PATH=.venv/bin:$PATH python3 -m pytest tests/test_price_shock_rev_strategies.py -v`

```text
tests/test_price_shock_rev_strategies.py::test_lower_percentile_excludes_current_bar PASSED [ 14%]
tests/test_price_shock_rev_strategies.py::test_strategy_matches_bt_runner_bar_by_bar[EUR_GBP-PriceShockRevEurGbpH1Long-Q5] PASSED [ 28%]
tests/test_price_shock_rev_strategies.py::test_strategy_matches_bt_runner_bar_by_bar[EUR_AUD-PriceShockRevEurAudH1Long-Q5] PASSED [ 42%]
tests/test_price_shock_rev_strategies.py::test_strategy_matches_bt_runner_bar_by_bar[USD_CAD-PriceShockRevUsdCadH1Long-Q5] PASSED [ 57%]
tests/test_price_shock_rev_strategies.py::test_strategy_matches_bt_runner_bar_by_bar[NZD_JPY-PriceShockRevNzdJpyH1Long-Q5] PASSED [ 71%]
tests/test_price_shock_rev_strategies.py::test_strategy_matches_bt_runner_bar_by_bar[AUD_JPY-PriceShockRevAudJpyH1Long-ALL] PASSED [ 85%]
tests/test_price_shock_rev_strategies.py::test_catastrophic_sl_distance_is_finite_and_positive PASSED [100%]

============================== 7 passed in 4.11s ===============================
```

## tier_integrity_check
Command: `PATH=.venv/bin:$PATH python3 tools/tier_integrity_check.py --check`

```text
✅ All checks passed — no inconsistencies detected
```

## Full Test Note
Command: `PATH=.venv/bin:$PATH python3 -m pytest tests/ -x -q`

```text
1 failed, 72 passed, 1 skipped
FAILED tests/test_bt_data_loader_parquet_fallback.py::test_fetch_ohlcv_uses_parquet_after_online_failures
```

This is outside the Price-Shock implementation path and matches the known stale-test backlog pattern.

## Known Gaps
- 対応未完了 pair: none. `MODE_CONFIG` now has 1H slots for EUR_GBP, EUR_AUD, USD_CAD, NZD_JPY, AUD_JPY.
- `git status` is not clean because unrelated untracked prime-gate files are present and were not touched by this task.

## Shadow 起動確認手順
Render API or local `app.py`: enable one `daytrade_1h_*` mode, wait for a Price-Shock signal, then confirm `/api/demo/trades` shows `entry_type=price_shock_rev_*` and `is_shadow=1`.
