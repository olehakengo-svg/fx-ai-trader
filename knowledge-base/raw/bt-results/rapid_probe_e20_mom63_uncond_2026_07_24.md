# rapid_edge_probe S2 診断 — e20_mom63_uncond

> **⚠️ 規律 (自動印字)**: 本レポートは S2 探索診断であり**判定ではない**。
> この出力から live/tier 判断・昇格・lot 変更を行うことは**禁止** (Rule 1 は 365日BT or
> Live N≥30 + Bonferroni + Pre-reg LOCK を要求する)。次ステージは S3 pre-reg 起案のみ。
> 探索窓のみ使用 — OOS 窓 (2024-01-01〜) は構造遮断済み。

- 生成: 2026-07-24T05:45:19.366633+00:00 / tool seed=20260722 / spec_hash=`d85336f855deeeb4`
- 仮説: E20 variant (b) rates-momentum: sign(Δ63bd 2y 差) 無条件バイアス (trigger なし、bars hold)
- notes: E20 S1 feasibility (e20-rate-differential-feasibility-2026-07-22) §6 凍結 variant。GBP 2y レグは BOE IADB に 2y ZC が無く IUDSNZC (5y ZC) 代用 (mom variant のみ影響)。lag_days=1 (営業日) で公表 look-ahead を構造排除。診断であり判定ではない。
- 実効窓: 2014-06-01 〜 2022-12-31 (OOS 境界 2024-01-01 で構造遮断済み)

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
| EUR_GBP | 0.9885 | True |
| EUR_JPY | 1.0000 | True |
| EUR_USD | 0.9869 | True |
| GBP_JPY | 1.0000 | True |
| GBP_USD | 0.9866 | True |
| USD_CAD | 0.9796 | True |
| USD_JPY | 0.9754 | True |

skip 理由 (silent except 禁止 — 全件カウント): `{"EUR_GBP": {"censored_horizon": 2}, "EUR_JPY": {"censored_horizon": 1}, "EUR_USD": {"censored_horizon": 1}, "GBP_JPY": {"censored_horizon": 96}, "GBP_USD": {"censored_horizon": 1}, "USD_CAD": {"censored_horizon": 1}, "USD_JPY": {"censored_horizon": 2}}`

## ペア × horizon 診断

| cell | N | EV_fric(pips) | median | WR | IC | IC_p | fold符号 | 発火/年 |
|---|---|---|---|---|---|---|---|---|
| EUR_GBP:h96 | 222 | -6.53 | -7.30 | 0.41 | -0.106 | 0.1164 | [-1, -1, -1] | 25.9 |
| EUR_GBP:h480 | 221 | -4.73 | -10.00 | 0.45 | -0.050 | 0.4578 | [1, -1, -1] | 25.7 |
| EUR_GBP:h960 | 221 | -5.20 | -15.90 | 0.46 | -0.047 | 0.4884 | [1, -1, 1] | 25.7 |
| EUR_JPY:h96 | 229 | -1.29 | -3.90 | 0.49 | 0.055 | 0.4047 | [-1, 1, -1] | 26.7 |
| EUR_JPY:h480 | 229 | -9.91 | -3.70 | 0.49 | -0.010 | 0.8859 | [-1, 1, 1] | 26.7 |
| EUR_JPY:h960 | 228 | -21.04 | -9.60 | 0.49 | -0.064 | 0.3385 | [-1, -1, -1] | 26.6 |
| EUR_USD:h96 | 221 | -0.03 | -0.40 | 0.50 | -0.014 | 0.8415 | [-1, -1, 1] | 25.7 |
| EUR_USD:h480 | 221 | -3.94 | 2.20 | 0.51 | 0.026 | 0.7046 | [-1, -1, 1] | 25.7 |
| EUR_USD:h960 | 220 | 7.10 | 3.90 | 0.51 | 0.059 | 0.3867 | [1, -1, 1] | 25.6 |
| GBP_JPY:h96 | 229 | 4.49 | 6.40 | 0.55 | 0.148 | 0.0251 | [-1, 1, 1] | 26.7 |
| GBP_JPY:h480 | 229 | 26.76 | 2.50 | 0.51 | 0.153 | 0.0209 | [1, -1, 1] | 26.7 |
| GBP_JPY:h960 | 229 | 24.62 | 37.40 | 0.53 | 0.076 | 0.2544 | [1, -1, 1] | 26.7 |
| GBP_USD:h96 | 221 | 7.64 | 0.67 | 0.50 | 0.059 | 0.3817 | [1, 1, 1] | 25.7 |
| GBP_USD:h480 | 221 | 11.78 | 12.57 | 0.53 | 0.072 | 0.2842 | [-1, 1, 1] | 25.7 |
| GBP_USD:h960 | 220 | 14.77 | 20.57 | 0.56 | 0.105 | 0.1195 | [1, -1, 1] | 25.6 |
| USD_CAD:h96 | 219 | -3.52 | -2.80 | 0.48 | -0.070 | 0.2999 | [-1, -1, 1] | 25.5 |
| USD_CAD:h480 | 219 | 5.54 | 1.90 | 0.51 | -0.044 | 0.5191 | [1, -1, 1] | 25.5 |
| USD_CAD:h960 | 218 | 14.80 | -5.45 | 0.50 | 0.012 | 0.8638 | [1, 1, 1] | 25.4 |
| USD_JPY:h96 | 219 | -1.52 | -4.24 | 0.47 | -0.015 | 0.8219 | [1, -1, -1] | 25.5 |
| USD_JPY:h480 | 218 | 7.73 | 9.31 | 0.54 | 0.048 | 0.4777 | [1, 1, 1] | 25.4 |
| USD_JPY:h960 | 218 | 10.57 | 1.56 | 0.50 | 0.056 | 0.4108 | [-1, -1, 1] | 25.4 |

## Pooled (全ペア) + 次ステージ判定の目安

| horizon | N | EV_fric(pips) | WR | fold符号 | EV>0 ペア | 発火/年 | S3 起案検討の目安 |
|---|---|---|---|---|---|---|---|
| h96 | 1560 | -0.09 | 0.49 | [-1, 1, 1] | 2/7 | 181.8 | ⬜ 目安未達 |
| h480 | 1558 | 4.78 | 0.51 | [-1, -1, 1] | 4/7 | 181.5 | ⬜ 目安未達 |
| h960 | 1554 | 6.46 | 0.51 | [1, -1, 1] | 5/7 | 181.1 | ⬜ 目安未達 |

**目安の定義** (判定ではない): pooled EV_fric>0 ∧ N≥60 ∧ fold 3 分割全符号一致 ∧ EV>0 ペア比率 ≥50%。目安を満たしても **S3 pre-reg (候補固定 → OOS 窓 → BH-FDR 判定) を通るまで何も確定しない**。

---
*rapid_edge_probe.py (S2 共通ハーネス) による自動生成。使い方: knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md*
