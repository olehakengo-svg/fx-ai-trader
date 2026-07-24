# rapid_edge_probe S2 診断 — e20_carry_uncond_pre2022

> **⚠️ 規律 (自動印字)**: 本レポートは S2 探索診断であり**判定ではない**。
> この出力から live/tier 判断・昇格・lot 変更を行うことは**禁止** (Rule 1 は 365日BT or
> Live N≥30 + Bonferroni + Pre-reg LOCK を要求する)。次ステージは S3 pre-reg 起案のみ。
> 探索窓のみ使用 — OOS 窓 (2024-01-01〜) は構造遮断済み。

- 生成: 2026-07-24T05:46:00.027579+00:00 / tool seed=20260722 / spec_hash=`0635dfd3c4830c54`
- 仮説: E20 (a) regime slice: 収斂期 2014-06〜2021-12 (§6-3 ガード)
- notes: E20 S1 feasibility (e20-rate-differential-feasibility-2026-07-22) §6 凍結 variant。GBP 2y レグは BOE IADB に 2y ZC が無く IUDSNZC (5y ZC) 代用 (mom variant のみ影響)。lag_days=1 (営業日) で公表 look-ahead を構造排除。診断であり判定ではない。
- 実効窓: 2014-06-01 〜 2021-12-31 (OOS 境界 2024-01-01 で構造遮断済み)

## 再試行禁止チェックリスト (falsified 6 系統 + 価格モダリティ 3 周)

本仮説が以下の再試行に該当しないことを S1 で確認済みであること (該当時は即中止):

| 系統 | 結論 | 参照 |
|---|---|---|
| H4 水平線 level | 3-way IC null (N=10k-15k)、再試行禁止 | `project_h4_level_edge_falsified` |
| チャネル (回帰±2σ/平行) | 6-pair IC null 2026-06-25、再試行禁止 | `project_channel_edge_falsified` |
| 水平 sweep&reclaim | 負EV (6-pair) 2026-06-25、再試行禁止 | `project_sweep_reclaim_horizontal_falsified` |
| mtf_regime_switch SELL 非対称 | sub-friction、摩擦込み REJECT | `project_mtf_regime_switch_falsified` |
| bb_rsi_reversion | T10 KILL N=495 friction>edge、セル分割/フィルタ再生の再試行禁止 | `project_bb_rsi_reversion_falsified` |
| T11 LDN朝×counter-USD MR | 敵対的検証で REJECT (擬似反復/閾値リーク) | `project_t11_ldn_counter_usd_mr_falsified` |
| 価格モダリティ round-1 | WS3 stage-2 barrier/EV 化 FAIL | `ws3-stage2-barrier-ev-prereg-2026-07-09 §8` |
| 価格モダリティ round-2 | OOS FAIL 0/5 (PR #79) | `ws3-round2-explore-prereg-2026-07-10 §8` |
| 価格モダリティ round-3 | crossasset divergence FAIL → 外部仮説転進 | `ws3-round3-crossasset-divergence-prereg-2026-07-13` |

(参考) month-end WMR fix も REJECT 済み (2026-06-18)。

## Coverage / skip

| pair | coverage | included |
|---|---|---|
| AUD_JPY | 1.0000 | True |
| AUD_USD | 0.9917 | True |
| EUR_AUD | 1.0000 | True |
| EUR_GBP | 0.9845 | True |
| EUR_JPY | 1.0000 | True |
| EUR_USD | 0.9832 | True |
| GBP_JPY | 1.0000 | True |
| GBP_USD | 0.9832 | True |
| NZD_JPY | 1.0000 | True |
| NZD_USD | 0.9630 | True |
| USD_CAD | 0.9747 | True |
| USD_CHF | 0.9770 | True |
| USD_JPY | 0.9705 | True |

skip 理由 (silent except 禁止 — 全件カウント): `{"AUD_JPY": {"censored_horizon": 1}, "AUD_USD": {"censored_horizon": 2}, "EUR_AUD": {"censored_horizon": 249}, "EUR_GBP": {"censored_horizon": 1}, "EUR_JPY": {"censored_horizon": 2}, "EUR_USD": {"censored_horizon": 1}, "GBP_JPY": {"censored_horizon": 1}, "GBP_USD": {"censored_horizon": 1}, "NZD_JPY": {"censored_horizon": 1}, "NZD_USD": {"censored_horizon": 1}, "USD_CAD": {"censored_horizon": 1}, "USD_CHF": {"censored_horizon": 1}, "USD_JPY": {"censored_horizon": 96}}`

## ペア × horizon 診断

| cell | N | EV_fric(pips) | median | WR | IC | IC_p | fold符号 | 発火/年 |
|---|---|---|---|---|---|---|---|---|
| AUD_JPY:h96 | 200 | -5.41 | -3.05 | 0.47 | -0.091 | 0.1992 | [-1, -1, 1] | 26.4 |
| AUD_JPY:h480 | 200 | -7.48 | 2.47 | 0.53 | -0.144 | 0.0417 | [-1, -1, 1] | 26.4 |
| AUD_JPY:h960 | 199 | -9.86 | 4.27 | 0.52 | -0.102 | 0.1501 | [-1, -1, 1] | 26.2 |
| AUD_USD:h96 | 197 | -2.98 | -5.80 | 0.46 | -0.123 | 0.0851 | [-1, 1, 1] | 26.0 |
| AUD_USD:h480 | 196 | 10.54 | 15.75 | 0.57 | 0.002 | 0.9749 | [-1, 1, 1] | 25.8 |
| AUD_USD:h960 | 196 | 4.87 | 13.00 | 0.54 | -0.014 | 0.8468 | [-1, 1, 1] | 25.8 |
| EUR_AUD:h96 | 198 | 2.45 | -6.95 | 0.48 | 0.051 | 0.4737 | [1, -1, -1] | 26.1 |
| EUR_AUD:h480 | 198 | 18.63 | 22.30 | 0.58 | -0.042 | 0.5547 | [1, -1, 1] | 26.1 |
| EUR_AUD:h960 | 198 | -9.79 | -5.75 | 0.49 | -0.016 | 0.8213 | [-1, -1, 1] | 26.1 |
| EUR_GBP:h96 | 195 | -1.40 | 3.00 | 0.54 | -0.070 | 0.3293 | [-1, -1, 1] | 25.7 |
| EUR_GBP:h480 | 195 | -7.82 | -2.80 | 0.48 | -0.143 | 0.0460 | [-1, -1, 1] | 25.7 |
| EUR_GBP:h960 | 194 | -4.75 | 26.35 | 0.53 | -0.045 | 0.5334 | [-1, -1, 1] | 25.6 |
| EUR_JPY:h96 | 161 | 2.45 | 0.50 | 0.50 | 0.096 | 0.2275 | [1, -1, -1] | 21.2 |
| EUR_JPY:h480 | 160 | 8.75 | -1.35 | 0.49 | 0.192 | 0.0151 | [1, 1, -1] | 21.1 |
| EUR_JPY:h960 | 160 | 15.31 | 19.40 | 0.54 | 0.100 | 0.2084 | [1, -1, 1] | 21.1 |
| EUR_USD:h96 | 195 | 2.53 | -1.70 | 0.47 | -0.061 | 0.3996 | [1, 1, -1] | 25.7 |
| EUR_USD:h480 | 195 | -3.94 | 4.90 | 0.52 | 0.042 | 0.5559 | [1, -1, -1] | 25.7 |
| EUR_USD:h960 | 194 | 1.82 | -7.50 | 0.48 | -0.062 | 0.3887 | [1, -1, -1] | 25.6 |
| GBP_JPY:h96 | 199 | -2.70 | -6.50 | 0.47 | -0.082 | 0.2496 | [1, -1, -1] | 26.2 |
| GBP_JPY:h480 | 199 | -31.38 | 0.20 | 0.50 | -0.126 | 0.0763 | [-1, -1, -1] | 26.2 |
| GBP_JPY:h960 | 198 | -14.84 | -15.85 | 0.47 | -0.110 | 0.1236 | [-1, -1, 1] | 26.1 |
| GBP_USD:h96 | 195 | -4.63 | -6.13 | 0.47 | 0.018 | 0.7989 | [1, -1, -1] | 25.7 |
| GBP_USD:h480 | 195 | -17.47 | -4.63 | 0.49 | 0.055 | 0.4412 | [-1, 1, -1] | 25.7 |
| GBP_USD:h960 | 194 | -28.44 | -30.83 | 0.44 | -0.052 | 0.4741 | [-1, -1, -1] | 25.6 |
| NZD_JPY:h96 | 199 | -0.10 | -1.00 | 0.49 | -0.070 | 0.3234 | [-1, -1, 1] | 26.2 |
| NZD_JPY:h480 | 199 | -4.76 | 7.00 | 0.53 | 0.005 | 0.9479 | [-1, -1, -1] | 26.2 |
| NZD_JPY:h960 | 198 | -8.81 | -4.90 | 0.47 | -0.057 | 0.4228 | [-1, -1, 1] | 26.1 |
| NZD_USD:h96 | 191 | -3.18 | -3.00 | 0.49 | 0.072 | 0.3240 | [1, -1, -1] | 25.2 |
| NZD_USD:h480 | 191 | 2.00 | 15.00 | 0.55 | 0.013 | 0.8582 | [-1, 1, 1] | 25.2 |
| NZD_USD:h960 | 190 | -0.25 | 14.55 | 0.51 | -0.053 | 0.4669 | [-1, -1, 1] | 25.1 |
| USD_CAD:h96 | 193 | -5.70 | -8.50 | 0.44 | -0.091 | 0.2083 | [-1, 1, -1] | 25.4 |
| USD_CAD:h480 | 193 | -0.83 | 10.90 | 0.53 | -0.011 | 0.8804 | [-1, -1, 1] | 25.4 |
| USD_CAD:h960 | 192 | -15.74 | -27.60 | 0.45 | -0.114 | 0.1147 | [-1, -1, 1] | 25.3 |
| USD_CHF:h96 | 179 | -10.50 | -9.50 | 0.46 | -0.020 | 0.7952 | [-1, -1, -1] | 23.6 |
| USD_CHF:h480 | 179 | -8.62 | -5.40 | 0.47 | -0.049 | 0.5161 | [-1, -1, 1] | 23.6 |
| USD_CHF:h960 | 178 | -6.09 | 1.25 | 0.51 | -0.042 | 0.5765 | [1, -1, -1] | 23.5 |
| USD_JPY:h96 | 192 | -3.61 | -2.79 | 0.46 | -0.092 | 0.2027 | [1, -1, -1] | 25.3 |
| USD_JPY:h480 | 192 | 1.05 | 16.66 | 0.56 | -0.097 | 0.1801 | [1, -1, 1] | 25.3 |
| USD_JPY:h960 | 192 | 5.44 | 14.36 | 0.54 | -0.073 | 0.3133 | [1, -1, 1] | 25.3 |

## Pooled (全ペア) + 次ステージ判定の目安

| horizon | N | EV_fric(pips) | WR | fold符号 | EV>0 ペア | 発火/年 | S3 起案検討の目安 |
|---|---|---|---|---|---|---|---|
| h96 | 2494 | -2.53 | 0.48 | [-1, -1, -1] | 3/13 | 328.9 | ⬜ 目安未達 |
| h480 | 2492 | -3.35 | 0.52 | [-1, -1, 1] | 5/13 | 328.6 | ⬜ 目安未達 |
| h960 | 2483 | -5.79 | 0.50 | [-1, -1, 1] | 4/13 | 327.4 | ⬜ 目安未達 |

**目安の定義** (判定ではない): pooled EV_fric>0 ∧ N≥60 ∧ fold 3 分割全符号一致 ∧ EV>0 ペア比率 ≥50%。目安を満たしても **S3 pre-reg (候補固定 → OOS 窓 → BH-FDR 判定) を通るまで何も確定しない**。

---
*rapid_edge_probe.py (S2 共通ハーネス) による自動生成。使い方: knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md*
