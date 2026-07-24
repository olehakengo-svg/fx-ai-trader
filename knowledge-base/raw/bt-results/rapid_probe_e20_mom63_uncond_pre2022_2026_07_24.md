# rapid_edge_probe S2 診断 — e20_mom63_uncond_pre2022

> **⚠️ 規律 (自動印字)**: 本レポートは S2 探索診断であり**判定ではない**。
> この出力から live/tier 判断・昇格・lot 変更を行うことは**禁止** (Rule 1 は 365日BT or
> Live N≥30 + Bonferroni + Pre-reg LOCK を要求する)。次ステージは S3 pre-reg 起案のみ。
> 探索窓のみ使用 — OOS 窓 (2024-01-01〜) は構造遮断済み。

- 生成: 2026-07-24T05:46:19.699905+00:00 / tool seed=20260722 / spec_hash=`9cc13ab560f2aa42`
- 仮説: E20 (b) regime slice: 収斂期 2014-06〜2021-12 (§6-3 ガード)
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
| EUR_GBP | 0.9845 | True |
| EUR_JPY | 1.0000 | True |
| EUR_USD | 0.9832 | True |
| GBP_JPY | 1.0000 | True |
| GBP_USD | 0.9832 | True |
| USD_CAD | 0.9747 | True |
| USD_JPY | 0.9705 | True |

skip 理由 (silent except 禁止 — 全件カウント): `{"EUR_GBP": {"censored_horizon": 1}, "EUR_JPY": {"censored_horizon": 2}, "EUR_USD": {"censored_horizon": 1}, "GBP_JPY": {"censored_horizon": 1}, "GBP_USD": {"censored_horizon": 1}, "USD_CAD": {"censored_horizon": 2}, "USD_JPY": {"censored_horizon": 1}}`

## ペア × horizon 診断

| cell | N | EV_fric(pips) | median | WR | IC | IC_p | fold符号 | 発火/年 |
|---|---|---|---|---|---|---|---|---|
| EUR_GBP:h96 | 195 | -6.77 | -7.50 | 0.41 | -0.124 | 0.0844 | [-1, -1, -1] | 25.7 |
| EUR_GBP:h480 | 195 | -5.94 | -14.80 | 0.44 | -0.091 | 0.2078 | [1, -1, -1] | 25.7 |
| EUR_GBP:h960 | 194 | -6.43 | -32.35 | 0.44 | -0.054 | 0.4580 | [1, -1, -1] | 25.6 |
| EUR_JPY:h96 | 199 | -3.66 | -4.10 | 0.48 | -0.007 | 0.9199 | [-1, 1, -1] | 26.2 |
| EUR_JPY:h480 | 198 | -13.84 | -1.15 | 0.50 | -0.059 | 0.4116 | [-1, 1, 1] | 26.1 |
| EUR_JPY:h960 | 198 | -27.94 | -12.35 | 0.48 | -0.112 | 0.1153 | [-1, -1, 1] | 26.1 |
| EUR_USD:h96 | 195 | -2.10 | -1.90 | 0.48 | -0.044 | 0.5383 | [1, -1, 1] | 25.7 |
| EUR_USD:h480 | 195 | -8.86 | -5.00 | 0.49 | -0.005 | 0.9433 | [-1, -1, 1] | 25.7 |
| EUR_USD:h960 | 194 | -1.29 | -9.40 | 0.48 | 0.004 | 0.9585 | [1, -1, 1] | 25.6 |
| GBP_JPY:h96 | 199 | 0.68 | 5.20 | 0.55 | 0.131 | 0.0661 | [-1, -1, 1] | 26.2 |
| GBP_JPY:h480 | 199 | 14.03 | -6.60 | 0.48 | 0.058 | 0.4142 | [1, -1, 1] | 26.2 |
| GBP_JPY:h960 | 198 | 26.68 | 41.85 | 0.55 | 0.060 | 0.4024 | [1, 1, 1] | 26.1 |
| GBP_USD:h96 | 195 | 4.02 | 1.17 | 0.51 | 0.050 | 0.4833 | [1, -1, 1] | 25.7 |
| GBP_USD:h480 | 195 | 5.82 | 8.67 | 0.52 | 0.061 | 0.3982 | [-1, 1, 1] | 25.7 |
| GBP_USD:h960 | 194 | 5.26 | 18.77 | 0.56 | 0.074 | 0.3055 | [1, -1, -1] | 25.6 |
| USD_CAD:h96 | 193 | -3.08 | -1.20 | 0.49 | -0.057 | 0.4335 | [-1, -1, 1] | 25.4 |
| USD_CAD:h480 | 192 | 4.71 | -0.65 | 0.50 | -0.061 | 0.4039 | [1, -1, 1] | 25.3 |
| USD_CAD:h960 | 192 | 13.73 | -5.45 | 0.49 | 0.017 | 0.8145 | [1, 1, -1] | 25.3 |
| USD_JPY:h96 | 192 | 0.21 | -4.39 | 0.46 | -0.069 | 0.3424 | [1, -1, -1] | 25.3 |
| USD_JPY:h480 | 192 | 6.60 | 9.31 | 0.54 | 0.036 | 0.6232 | [1, -1, 1] | 25.3 |
| USD_JPY:h960 | 191 | 1.60 | -2.84 | 0.49 | -0.023 | 0.7492 | [1, -1, 1] | 25.2 |

## Pooled (全ペア) + 次ステージ判定の目安

| horizon | N | EV_fric(pips) | WR | fold符号 | EV>0 ペア | 発火/年 | S3 起案検討の目安 |
|---|---|---|---|---|---|---|---|
| h96 | 1368 | -1.53 | 0.48 | [-1, -1, 1] | 3/7 | 180.4 | ⬜ 目安未達 |
| h480 | 1366 | 0.35 | 0.50 | [1, -1, 1] | 4/7 | 180.1 | ⬜ 目安未達 |
| h960 | 1361 | 1.63 | 0.50 | [1, -1, 1] | 4/7 | 179.5 | ⬜ 目安未達 |

**目安の定義** (判定ではない): pooled EV_fric>0 ∧ N≥60 ∧ fold 3 分割全符号一致 ∧ EV>0 ペア比率 ≥50%。目安を満たしても **S3 pre-reg (候補固定 → OOS 窓 → BH-FDR 判定) を通るまで何も確定しない**。

---
*rapid_edge_probe.py (S2 共通ハーネス) による自動生成。使い方: knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md*
