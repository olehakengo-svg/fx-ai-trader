# G1: NEVER_LOGGED 7 戦略 BT 発火診断 (2026-04-28)

- 365d 履歴, 15m, 5 majors, sample_every=4
- Plan: Phase 10 G1

## サマリー

| Strategy | n_evals | n_signals | rate% | n_BUY | n_SELL | 判定 |
|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 30592 | 0 | 0.000 | 0 | 0 | 🔴 真に 0 firing — 廃止 or G2 緩和必須 |
| sr_liquidity_grab | 30592 | 0 | 0.000 | 0 | 0 | 🔴 真に 0 firing — 廃止 or G2 緩和必須 |
| cpd_divergence | 30592 | 0 | 0.000 | 0 | 0 | 🔴 真に 0 firing — 廃止 or G2 緩和必須 |
| vdr_jpy | 30592 | 0 | 0.000 | 0 | 0 | 🔴 真に 0 firing — 廃止 or G2 緩和必須 |
| vsg_jpy_reversal | 30592 | 331 | 1.082 | 169 | 162 | ✅ BT で頻発 — 別要因 |
| rsk_gbpjpy_reversion | 30592 | 182 | 0.595 | 91 | 91 | ✅ BT で頻発 — 別要因 |
| mqe_gbpusd_fix | 30592 | 20 | 0.065 | 14 | 6 | 🟢 BT で動く — production 配線/data 問題 |

## Pair 別

| Strategy | EUR_JPY | EUR_USD | GBP_JPY | GBP_USD | USD_JPY | total |
|---|---|---|---|---|---|---|
| sr_anti_hunt_bounce | 0/6103 | 0/6147 | 0/6059 | 0/6140 | 0/6143 | 0/30592 |
| sr_liquidity_grab | 0/6103 | 0/6147 | 0/6059 | 0/6140 | 0/6143 | 0/30592 |
| cpd_divergence | 0/6103 | 0/6147 | 0/6059 | 0/6140 | 0/6143 | 0/30592 |
| vdr_jpy | 0/6103 | 0/6147 | 0/6059 | 0/6140 | 0/6143 | 0/30592 |
| vsg_jpy_reversal | 145/6103 | 0/6147 | 186/6059 | 0/6140 | 0/6143 | 331/30592 |
| rsk_gbpjpy_reversion | 0/6103 | 0/6147 | 182/6059 | 0/6140 | 0/6143 | 182/30592 |
| mqe_gbpusd_fix | 0/6103 | 0/6147 | 0/6059 | 20/6140 | 0/6143 | 20/30592 |

## 解釈ガイド

- **0 signals**: BT も発火しない → entry 真に困難。G2 で sub-clause 緩和。
- **n>0 だが production NEVER_LOGGED**: BT で動くが Live で動かない。
  SignalContext 組み立て差 (sr_levels / regime), or DT_QUALIFIED / pair scope 不整合。
- **rate% < 0.05**: 稀すぎ → 廃止候補。

## 注意 (本診断の限界)

- SR levels / layer dicts は **empty** で渡している。これに依存する戦略
  (sr_anti_hunt_bounce, sr_liquidity_grab) は本 audit で過小評価される。
- sample_every で sub-sample しているため絶対数は近似値、比較用のみ。