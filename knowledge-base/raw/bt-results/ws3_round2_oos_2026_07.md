# WS3 round-2 OOS verdict (機械判定、pre-reg §3)

- 生成: 2026-07-10T07:55:03.433014+00:00 / verdict(機械): **FAIL** / OOS 窓: 2024-07-07..2025-07-07 (truncated-parquet, lookback 365d) (再利用 2 回目)
- PASS = レグA (BH-FDR q=0.1 m=5 ∧ ratio≥1.2 ∧ N≥30) ∧ レグB (best 3×3 近傍平均 ≥ +0.5 p/t ∧ 隣接過半 EV>0) ∧ ナイフエッジ (LOFO>0)
- ep 復元検証不一致: 0 (許容 0.02p)

| cell | H | N | OOS ratio (探索) | p | FDR | ratio≥1.2 | best EV | 近傍平均 | 隣接正 | LOFO | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sr_fib_confluence×GBP_USD×SELL | h96 | 123 | **1.2054** (1.656) | 0.130687 | ✗ | ✓ | 0.843 (tp111_sl81) | -0.925 | 0/2 | -10.814 | FAIL |
| vol_spike_mr×USD_JPY×BUY | h24 | 27 | **0.5629** (1.49) | 0.858914 | ✗ | ✗ | -4.821 (tp71_sl32) | -8.555 | 0/3 | -8.407 | FAIL |
| sr_fib_confluence×EUR_USD×SELL | h96 | 86 | **1.2492** (1.487) | 0.194281 | ✗ | ✓ | 5.674 (tp34_sl74) | 1.444 | 1/2 | 3.782 | FAIL |
| vsg_jpy_reversal×GBP_JPY×SELL | h24 | 117 | **0.8827** (1.482) | 0.716928 | ✗ | ✗ | -5.413 (tp86_sl64) | -8.143 | 0/2 | -11.481 | FAIL |
| dt_sr_channel_reversal×GBP_JPY×BUY | h96 | 75 | **0.897** (1.327) | 0.605539 | ✗ | ✗ | 4.367 (tp67_sl83) | -4.691 | 1/3 | -12.684 | FAIL |

config 別 EV・fold・EV'・lag-1 ρ は JSON 参照。
