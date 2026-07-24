# rapid_edge_probe S2 診断 — e20_mom63_uncond_2022

> **⚠️ 規律 (自動印字)**: 本レポートは S2 探索診断であり**判定ではない**。
> この出力から live/tier 判断・昇格・lot 変更を行うことは**禁止** (Rule 1 は 365日BT or
> Live N≥30 + Bonferroni + Pre-reg LOCK を要求する)。次ステージは S3 pre-reg 起案のみ。
> 探索窓のみ使用 — OOS 窓 (2024-01-01〜) は構造遮断済み。

- 生成: 2026-07-24T05:46:23.790182+00:00 / tool seed=20260722 / spec_hash=`0b507540029a866b`
- 仮説: E20 (b) regime slice: 発散期 2022 (§6-3 ガード)
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
| EUR_GBP | 1.0000 | True |
| EUR_JPY | 1.0000 | True |
| EUR_USD | 1.0000 | True |
| GBP_JPY | 1.0000 | True |
| GBP_USD | 1.0000 | True |
| USD_CAD | 1.0000 | True |
| USD_JPY | 1.0000 | True |

skip 理由 (silent except 禁止 — 全件カウント): `{"EUR_GBP": {"censored_horizon": 2}, "EUR_JPY": {"censored_horizon": 2}, "EUR_USD": {"censored_horizon": 2}, "GBP_JPY": {"censored_horizon": 2}, "GBP_USD": {"censored_horizon": 2}, "USD_CAD": {"censored_horizon": 2}, "USD_JPY": {"censored_horizon": 2}}`

## ペア × horizon 診断

| cell | N | EV_fric(pips) | median | WR | IC | IC_p | fold符号 | 発火/年 |
|---|---|---|---|---|---|---|---|---|
| EUR_GBP:h96 | 27 | -15.71 | -14.60 | 0.33 | -0.424 | 0.0276 | [-1, -1, -1] | 27.1 |
| EUR_GBP:h480 | 26 | -29.30 | -16.35 | 0.42 | -0.172 | 0.4009 | [-1, -1, -1] | 26.1 |
| EUR_GBP:h960 | 26 | -17.87 | -0.35 | 0.50 | -0.050 | 0.8099 | [-1, -1, 1] | 26.1 |
| EUR_JPY:h96 | 31 | 12.71 | 15.60 | 0.65 | 0.200 | 0.2817 | [1, 1, -1] | 31.1 |
| EUR_JPY:h480 | 30 | 20.41 | 41.07 | 0.57 | 0.164 | 0.3853 | [-1, -1, 1] | 30.1 |
| EUR_JPY:h960 | 30 | 17.45 | -36.50 | 0.43 | -0.029 | 0.8803 | [1, 1, 1] | 30.1 |
| EUR_USD:h96 | 27 | -13.68 | -6.90 | 0.41 | -0.194 | 0.3334 | [1, -1, -1] | 27.1 |
| EUR_USD:h480 | 26 | 2.25 | -1.35 | 0.50 | 0.105 | 0.6099 | [1, -1, 1] | 26.1 |
| EUR_USD:h960 | 26 | 11.65 | -21.30 | 0.42 | 0.115 | 0.5752 | [1, -1, 1] | 26.1 |
| GBP_JPY:h96 | 31 | -39.60 | -39.00 | 0.32 | -0.319 | 0.0807 | [-1, -1, -1] | 31.1 |
| GBP_JPY:h480 | 30 | -70.16 | -110.81 | 0.33 | 0.017 | 0.9303 | [1, -1, -1] | 30.1 |
| GBP_JPY:h960 | 30 | 9.67 | 0.71 | 0.50 | 0.196 | 0.3004 | [1, 1, -1] | 30.1 |
| GBP_USD:h96 | 27 | -11.33 | 3.37 | 0.52 | -0.021 | 0.9182 | [1, -1, -1] | 27.1 |
| GBP_USD:h480 | 26 | 33.36 | 15.02 | 0.50 | 0.165 | 0.4202 | [1, -1, 1] | 26.1 |
| GBP_USD:h960 | 26 | 39.95 | 0.07 | 0.50 | -0.046 | 0.8228 | [1, -1, 1] | 26.1 |
| USD_CAD:h96 | 27 | 9.63 | 24.90 | 0.63 | -0.097 | 0.6321 | [1, 1, 1] | 27.1 |
| USD_CAD:h480 | 26 | 10.37 | 32.20 | 0.54 | -0.155 | 0.4488 | [-1, -1, 1] | 26.1 |
| USD_CAD:h960 | 26 | 21.09 | 57.95 | 0.58 | -0.152 | 0.4590 | [1, -1, 1] | 26.1 |
| USD_JPY:h96 | 27 | 9.45 | 18.06 | 0.59 | 0.205 | 0.3062 | [1, 1, -1] | 27.1 |
| USD_JPY:h480 | 26 | 17.98 | -0.29 | 0.50 | 0.128 | 0.5347 | [1, 1, -1] | 26.1 |
| USD_JPY:h960 | 26 | 70.40 | 70.21 | 0.58 | 0.105 | 0.6099 | [1, 1, -1] | 26.1 |

## Pooled (全ペア) + 次ステージ判定の目安

| horizon | N | EV_fric(pips) | WR | fold符号 | EV>0 ペア | 発火/年 | S3 起案検討の目安 |
|---|---|---|---|---|---|---|---|
| h96 | 197 | -7.20 | 0.49 | [1, -1, -1] | 3/7 | 197.7 | ⬜ 目安未達 |
| h480 | 190 | -3.11 | 0.48 | [1, -1, 1] | 5/7 | 190.7 | ⬜ 目安未達 |
| h960 | 190 | 21.42 | 0.50 | [1, 1, -1] | 6/7 | 190.7 | ⬜ 目安未達 |

**目安の定義** (判定ではない): pooled EV_fric>0 ∧ N≥60 ∧ fold 3 分割全符号一致 ∧ EV>0 ペア比率 ≥50%。目安を満たしても **S3 pre-reg (候補固定 → OOS 窓 → BH-FDR 判定) を通るまで何も確定しない**。

---
*rapid_edge_probe.py (S2 共通ハーネス) による自動生成。使い方: knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md*
