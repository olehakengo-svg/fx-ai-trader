# rapid_edge_probe S2 診断 — e20_carry_uncond_2022

> **⚠️ 規律 (自動印字)**: 本レポートは S2 探索診断であり**判定ではない**。
> この出力から live/tier 判断・昇格・lot 変更を行うことは**禁止** (Rule 1 は 365日BT or
> Live N≥30 + Bonferroni + Pre-reg LOCK を要求する)。次ステージは S3 pre-reg 起案のみ。
> 探索窓のみ使用 — OOS 窓 (2024-01-01〜) は構造遮断済み。

- 生成: 2026-07-24T05:46:06.316648+00:00 / tool seed=20260722 / spec_hash=`13356685aca68e27`
- 仮説: E20 (a) regime slice: 発散期 2022 (§6-3 ガード)
- notes: E20 S1 feasibility (e20-rate-differential-feasibility-2026-07-22) §6 凍結 variant。GBP 2y レグは BOE IADB に 2y ZC が無く IUDSNZC (5y ZC) 代用 (mom variant のみ影響)。lag_days=1 (営業日) で公表 look-ahead を構造排除。診断であり判定ではない。
- 実効窓: 2022-01-01 〜 2022-12-31 (OOS 境界 2024-01-01 で構造遮断済み)

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
| AUD_USD | 1.0000 | True |
| EUR_AUD | 1.0000 | True |
| EUR_GBP | 1.0000 | True |
| EUR_JPY | 1.0000 | True |
| EUR_USD | 1.0000 | True |
| GBP_JPY | 1.0000 | True |
| GBP_USD | 1.0000 | True |
| NZD_JPY | 1.0000 | True |
| NZD_USD | 1.0000 | True |
| USD_CAD | 1.0000 | True |
| USD_CHF | 1.0000 | True |
| USD_JPY | 1.0000 | True |

skip 理由 (silent except 禁止 — 全件カウント): `{"AUD_JPY": {"censored_horizon": 2}, "AUD_USD": {"censored_horizon": 2}, "EUR_AUD": {"censored_horizon": 2}, "EUR_GBP": {"censored_horizon": 2}, "EUR_JPY": {"censored_horizon": 2}, "EUR_USD": {"censored_horizon": 2}, "GBP_JPY": {"censored_horizon": 2}, "GBP_USD": {"censored_horizon": 2}, "NZD_JPY": {"censored_horizon": 1}, "NZD_USD": {"censored_horizon": 2}, "USD_CAD": {"censored_horizon": 2}, "USD_CHF": {"censored_horizon": 1}, "USD_JPY": {"censored_horizon": 2}}`

## ペア × horizon 診断

| cell | N | EV_fric(pips) | median | WR | IC | IC_p | fold符号 | 発火/年 |
|---|---|---|---|---|---|---|---|---|
| AUD_JPY:h96 | 31 | -6.98 | -9.10 | 0.45 | 0.138 | 0.4582 | [-1, -1, -1] | 31.1 |
| AUD_JPY:h480 | 30 | -13.04 | -9.58 | 0.43 | 0.026 | 0.8922 | [1, 1, -1] | 30.1 |
| AUD_JPY:h960 | 30 | 18.28 | 19.17 | 0.57 | -0.120 | 0.5283 | [1, 1, -1] | 30.1 |
| AUD_USD:h96 | 27 | 7.96 | 8.10 | 0.59 | 0.085 | 0.6719 | [1, 1, -1] | 27.1 |
| AUD_USD:h480 | 26 | 26.00 | 48.40 | 0.62 | 0.374 | 0.0600 | [-1, 1, 1] | 26.1 |
| AUD_USD:h960 | 26 | 17.98 | 57.25 | 0.62 | 0.081 | 0.6949 | [1, 1, -1] | 26.1 |
| EUR_AUD:h96 | 27 | -25.60 | -3.90 | 0.44 | 0.170 | 0.3970 | [-1, -1, -1] | 27.1 |
| EUR_AUD:h480 | 26 | -42.60 | -73.60 | 0.35 | -0.189 | 0.3549 | [1, -1, -1] | 26.1 |
| EUR_AUD:h960 | 26 | -8.72 | -41.00 | 0.42 | -0.148 | 0.4698 | [1, 1, -1] | 26.1 |
| EUR_GBP:h96 | 27 | -17.22 | -14.70 | 0.37 | -0.037 | 0.8558 | [-1, -1, -1] | 27.1 |
| EUR_GBP:h480 | 26 | -22.31 | -12.25 | 0.46 | -0.012 | 0.9523 | [-1, -1, -1] | 26.1 |
| EUR_GBP:h960 | 26 | -20.17 | -3.75 | 0.46 | -0.004 | 0.9863 | [-1, -1, -1] | 26.1 |
| EUR_JPY:h96 | 31 | 8.66 | 12.90 | 0.61 | -0.123 | 0.5107 | [-1, 1, -1] | 31.1 |
| EUR_JPY:h480 | 30 | 22.77 | 41.07 | 0.60 | 0.194 | 0.3050 | [-1, -1, 1] | 30.1 |
| EUR_JPY:h960 | 30 | 33.96 | -25.20 | 0.47 | 0.014 | 0.9430 | [1, 1, 1] | 30.1 |
| EUR_USD:h96 | 27 | 5.02 | 4.70 | 0.59 | 0.163 | 0.4174 | [1, -1, 1] | 27.1 |
| EUR_USD:h480 | 26 | 11.29 | 1.50 | 0.50 | -0.005 | 0.9797 | [1, 1, -1] | 26.1 |
| EUR_USD:h960 | 26 | 26.52 | 16.85 | 0.58 | -0.075 | 0.7161 | [1, 1, -1] | 26.1 |
| GBP_JPY:h96 | 31 | -32.78 | -24.20 | 0.35 | -0.037 | 0.8419 | [-1, -1, -1] | 31.1 |
| GBP_JPY:h480 | 30 | -70.16 | -110.81 | 0.33 | -0.162 | 0.3928 | [1, -1, -1] | 30.1 |
| GBP_JPY:h960 | 30 | 9.67 | 0.71 | 0.50 | -0.009 | 0.9606 | [1, 1, -1] | 30.1 |
| GBP_USD:h96 | 27 | 14.58 | -12.43 | 0.48 | 0.093 | 0.6457 | [-1, 1, 1] | 27.1 |
| GBP_USD:h480 | 26 | -17.04 | 29.52 | 0.54 | -0.090 | 0.6621 | [-1, 1, -1] | 26.1 |
| GBP_USD:h960 | 26 | -47.45 | 10.07 | 0.54 | -0.222 | 0.2760 | [-1, 1, -1] | 26.1 |
| NZD_JPY:h96 | 35 | -1.53 | 2.60 | 0.54 | 0.329 | 0.0532 | [-1, -1, 1] | 35.1 |
| NZD_JPY:h480 | 35 | 11.45 | 26.79 | 0.57 | 0.153 | 0.3793 | [1, 1, -1] | 35.1 |
| NZD_JPY:h960 | 34 | 10.46 | 3.89 | 0.56 | -0.018 | 0.9200 | [1, 1, -1] | 34.1 |
| NZD_USD:h96 | 27 | -10.90 | -19.70 | 0.41 | 0.046 | 0.8199 | [-1, -1, 1] | 27.1 |
| NZD_USD:h480 | 26 | -15.22 | -47.70 | 0.42 | -0.070 | 0.7323 | [-1, -1, 1] | 26.1 |
| NZD_USD:h960 | 26 | -20.47 | -61.00 | 0.42 | -0.087 | 0.6725 | [-1, -1, 1] | 26.1 |
| USD_CAD:h96 | 27 | -19.76 | -30.90 | 0.41 | -0.161 | 0.4233 | [-1, -1, -1] | 27.1 |
| USD_CAD:h480 | 26 | -27.53 | -35.35 | 0.42 | -0.113 | 0.5827 | [-1, -1, 1] | 26.1 |
| USD_CAD:h960 | 26 | -29.59 | -20.15 | 0.50 | 0.018 | 0.9306 | [-1, -1, 1] | 26.1 |
| USD_CHF:h96 | 29 | 4.32 | 8.30 | 0.55 | -0.038 | 0.8436 | [1, 1, -1] | 29.1 |
| USD_CHF:h480 | 29 | 5.25 | -17.20 | 0.45 | -0.303 | 0.1096 | [1, 1, -1] | 29.1 |
| USD_CHF:h960 | 28 | 2.97 | 20.35 | 0.54 | -0.225 | 0.2501 | [1, -1, -1] | 28.1 |
| USD_JPY:h96 | 27 | 9.45 | 18.06 | 0.59 | -0.056 | 0.7807 | [1, 1, -1] | 27.1 |
| USD_JPY:h480 | 26 | 17.98 | -0.29 | 0.50 | -0.165 | 0.4219 | [1, 1, -1] | 26.1 |
| USD_JPY:h960 | 26 | 70.40 | 70.21 | 0.58 | -0.281 | 0.1645 | [1, 1, -1] | 26.1 |

## Pooled (全ペア) + 次ステージ判定の目安

| horizon | N | EV_fric(pips) | WR | fold符号 | EV>0 ペア | 発火/年 | S3 起案検討の目安 |
|---|---|---|---|---|---|---|---|
| h96 | 373 | -5.03 | 0.49 | [-1, -1, -1] | 6/13 | 374.3 | ⬜ 目安未達 |
| h480 | 362 | -8.47 | 0.48 | [1, -1, -1] | 6/13 | 363.2 | ⬜ 目安未達 |
| h960 | 360 | 5.55 | 0.52 | [1, 1, -1] | 8/13 | 361.2 | ⬜ 目安未達 |

**目安の定義** (判定ではない): pooled EV_fric>0 ∧ N≥60 ∧ fold 3 分割全符号一致 ∧ EV>0 ペア比率 ≥50%。目安を満たしても **S3 pre-reg (候補固定 → OOS 窓 → BH-FDR 判定) を通るまで何も確定しない**。

---
*rapid_edge_probe.py (S2 共通ハーネス) による自動生成。使い方: knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md*
