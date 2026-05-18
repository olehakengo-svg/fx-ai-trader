# Price-Shock Live Shadow Monitor Final

## Implemented files
- `tools/price_shock_live_shadow_monitor.py`
- `tests/test_price_shock_live_shadow_monitor.py`
- `README.md`
- `knowledge-base/wiki/index.md`
- `.ai/tasks/queue/20260518-1457-price-shock-live-shadow-monitor-final.md`

## git diff --stat HEAD~1
```text
 ...8-1457-price-shock-live-shadow-monitor-final.md |  79 +++
 README.md                                          |   6 +
 knowledge-base/wiki/index.md                       |   1 +
 tests/test_price_shock_live_shadow_monitor.py      | 223 +++++++++
 tools/price_shock_live_shadow_monitor.py           | 540 +++++++++++++++++++++
 5 files changed, 849 insertions(+)
```

## Test result
Command:
```bash
PATH="$PWD/.venv/bin:$PATH" python3 -m pytest tests/test_price_shock_live_shadow_monitor.py -v
```

Output:
```text
============================= test session starts ==============================
platform linux -- Python 3.11.2, pytest-9.0.3, pluggy-1.6.0 -- /data/repo/fx-ai-trader/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /data/repo/fx-ai-trader
collecting ... collected 9 items

tests/test_price_shock_live_shadow_monitor.py::test_empty_db_outputs_no_data PASSED [ 11%]
tests/test_price_shock_live_shadow_monitor.py::test_n10_wr50_collecting PASSED [ 22%]
tests/test_price_shock_live_shadow_monitor.py::test_n35_wr60_promote_pending_one_or_two_criteria_unmet PASSED [ 33%]
tests/test_price_shock_live_shadow_monitor.py::test_n35_high_wr_promote_ready PASSED [ 44%]
tests/test_price_shock_live_shadow_monitor.py::test_n20_low_wilson_demote_deactivate PASSED [ 55%]
tests/test_price_shock_live_shadow_monitor.py::test_live_is_shadow_zero_is_excluded PASSED [ 66%]
tests/test_price_shock_live_shadow_monitor.py::test_price_shock_like_filter_excludes_other_strategy PASSED [ 77%]
tests/test_price_shock_live_shadow_monitor.py::test_eur_gbp_eur_aud_simultaneous_open_counts_lock_violation PASSED [ 88%]
tests/test_price_shock_live_shadow_monitor.py::test_table_and_json_cli_outputs PASSED [100%]

============================== 9 passed in 2.71s ===============================
```

## Sample output: empty DB
```text
================================================================
Price-Shock Reversion Tier 1 - Live Shadow Monitor
集計期間: 2026-05-18 <- 6 週 (2026-04-06 ~ 2026-05-18)
DB table: demo_trades (entry_time), Shadow only: is_shadow = 1
================================================================

No data: no shadow price_shock_rev_*_h1_long trades in this period.
```

## Sample output: synthetic N=35 PROMOTE_READY
```text
Strategy                                  N      WR  Wilson_lo      PF    Kelly    EV(p)     Raw_p    Bonf_p   SL_hit             Status
price_shock_rev_eur_gbp_h1_long          35   71.4%      0.549    5.00    0.571     +5.7    0.0083    0.0417     0.0%      PROMOTE_READY

[Promote criteria status]
- N >= 30: 1/1 strategies
- Wilson_lo >= 0.50: 1/1 strategies
- Bonferroni m=5 raw p < 0.01: 1/1 strategies
- 6 weeks EV > 0: 1/1 strategies
- Shared lock violations = 0: 1/1 strategies
```

## Render shell
```bash
python3 tools/price_shock_live_shadow_monitor.py --weeks 6
```

## Known limitations
- EV percent is omitted because account equity is not available in `demo_trades`; pip EV is always reported.
- `eur_base_shock_lock` block counts are read from `events` when available, otherwise `demo_logs`; if neither contains persisted block events, the block count is reported as unavailable while simultaneous-open violations are still audited from open trades.
- If Render cannot expose the production SQLite mirror directly, run this monitor against a read-only copied DB or add a read-only API/export path rather than giving the tool production write credentials.
