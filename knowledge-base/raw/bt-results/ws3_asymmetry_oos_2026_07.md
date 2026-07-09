# WS3 方向性非対称 OOS 検証 (機械判定、pre-reg §4)

- 生成: 2026-07-09T06:42:57.656319+00:00 / verdict(機械): **PASS** / OOS 窓: 2024-07-07..2025-07-07 (truncated-parquet worktree, lookback 365d)
- PASS = BH-FDR q=0.1 (m=8) ∧ ratio≥1.2 ∧ N≥30

| cell | H | N | OOS ratio | 探索 ratio | p | FDR | CI5% | PASS |
|---|---|---|---|---|---|---|---|---|
| htf_false_breakout__EUR_JPY | h24 | 32 | **0.99** | 1.81 | 0.442456 | ✗ | 0.661 | fail |
| trendline_sweep__EUR_USD | h24 | 44 | **1.6951** | 1.65 | 0.116488 | ✗ | 0.853 | fail |
| dt_sr_channel_reversal__EUR_USD | h24 | 34 | **0.6191** | 1.55 | 0.833017 | ✗ | 0.287 | fail |
| london_fix_reversal__EUR_USD | h24 | 41 | **1.4286** | 1.51 | 0.011499 | ✓ | 1.14 | **PASS** |
| htf_false_breakout__AUD_JPY | h24 | 39 | **1.8243** | 1.39 | 0.011799 | ✓ | 1.2 | **PASS** |
| lin_reg_channel__EUR_USD | h96 | 26 | **1.129** | 1.94 | 0.363064 | ✗ | 0.707 | fail |
| hull_donchian_fade__EUR_USD | h24 | 46 | **1.1149** | 1.3 | 0.406059 | ✗ | 0.623 | fail |
| dt_fib_reversal__USD_JPY | h96 | 20 | **1.2502** | 2.05 | 0.275372 | ✗ | 0.472 | fail |

隣接 horizon ratio・lag-1 ρ は JSON 参照。
