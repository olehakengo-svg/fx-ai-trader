# SR Weight Phase2 Bin BH-FDR

- generated_at: 2026-05-11T08:42:04.534946+00:00
- overall_verdict: ACCEPT
- data_source_guard: BT_MODE=1 BT_REQUIRE_MASSIVE_CACHE=1; local data/cache/massive parquet only

## Per Strategy

| strategy | N | min N/bin | trend p | BH survivor | MW p | verdict |
|---|---:|---:|---:|---|---:|---|
| `dual_sr_bounce` | 175 | 19 | 0.04103610608834472 | False | 0.09900629200907411 | NULL |
| `sr_anti_hunt_bounce` | 594 | 72 | 0.0033864610063342906 | True | 0.02708439413374966 | BIN_DISCRIMINATION_VALID |
| `dt_sr_channel_reversal` | 1851 | 190 | 0.8754998084797179 | False | 0.5790542778690699 | NULL |
| `strong_sr_breakout` | 566 | 25 | 0.6555715902055437 | False | 0.5030213862485993 | NULL |
| `sr_channel_reversal` | 0 | 0 | None | False | None | INSUFFICIENT_BT_N |
| `sr_fib_confluence` | 1756 | 165 | 0.2854482208763022 | False | 0.8145538055647641 | NULL |

## Survivors

- BH FDR q=0.10: ['sr_anti_hunt_bounce']
- Bonferroni alpha=0.10: []
