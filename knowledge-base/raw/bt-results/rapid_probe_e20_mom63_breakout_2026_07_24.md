# rapid_edge_probe S2 診断 — e20_mom63_breakout

> **⚠️ 規律 (自動印字)**: 本レポートは S2 探索診断であり**判定ではない**。
> この出力から live/tier 判断・昇格・lot 変更を行うことは**禁止** (Rule 1 は 365日BT or
> Live N≥30 + Bonferroni + Pre-reg LOCK を要求する)。次ステージは S3 pre-reg 起案のみ。
> 探索窓のみ使用 — OOS 窓 (2024-01-01〜) は構造遮断済み。

- 生成: 2026-07-24T05:45:34.833202+00:00 / tool seed=20260722 / spec_hash=`91fbb4ab316ad3c9`
- 仮説: E20 variant (b) rates-momentum: sign(Δ63bd 2y 差) × 20-bar breakout entry、first_touch σ_h barrier
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

skip 理由 (silent except 禁止 — 全件カウント): `{"EUR_GBP": {"atr_nan": 279, "censored_horizon": 1}, "EUR_JPY": {"atr_nan": 201, "censored_horizon": 9}, "EUR_USD": {"atr_nan": 174, "censored_horizon": 1}, "GBP_JPY": {"atr_nan": 210, "censored_horizon": 1}, "GBP_USD": {"atr_nan": 234, "censored_horizon": 1}, "USD_CAD": {"atr_nan": 120, "censored_horizon": 2}, "USD_JPY": {"atr_nan": 180, "censored_horizon": 1}}`

## ペア × horizon 診断

| cell | N | EV_fric(pips) | median | WR | IC | IC_p | fold符号 | 発火/年 |
|---|---|---|---|---|---|---|---|---|
| EUR_GBP:h96 | 213 | -1.11 | -3.30 | 0.46 | -0.037 | 0.5949 | [1, -1, -1] | 24.8 |
| EUR_GBP:h480 | 213 | -5.76 | 2.50 | 0.52 | -0.031 | 0.6530 | [-1, -1, 1] | 24.8 |
| EUR_GBP:h960 | 212 | -8.89 | -9.60 | 0.48 | -0.043 | 0.5314 | [-1, -1, 1] | 24.7 |
| EUR_JPY:h96 | 218 | -8.03 | -3.65 | 0.48 | -0.089 | 0.1928 | [-1, -1, -1] | 25.4 |
| EUR_JPY:h480 | 218 | 2.40 | 8.30 | 0.52 | -0.017 | 0.8067 | [1, 1, -1] | 25.4 |
| EUR_JPY:h960 | 218 | -7.06 | -11.40 | 0.49 | -0.043 | 0.5243 | [-1, 1, 1] | 25.4 |
| EUR_USD:h96 | 213 | 2.79 | -3.30 | 0.49 | 0.133 | 0.0534 | [1, -1, 1] | 24.8 |
| EUR_USD:h480 | 213 | -2.62 | -12.30 | 0.46 | 0.037 | 0.5897 | [-1, -1, -1] | 24.8 |
| EUR_USD:h960 | 212 | -2.63 | -3.00 | 0.50 | 0.061 | 0.3746 | [-1, 1, 1] | 24.7 |
| GBP_JPY:h96 | 220 | 0.55 | 5.45 | 0.52 | 0.048 | 0.4788 | [-1, -1, 1] | 25.6 |
| GBP_JPY:h480 | 220 | 13.22 | 15.40 | 0.54 | 0.086 | 0.2027 | [1, -1, 1] | 25.6 |
| GBP_JPY:h960 | 219 | 10.37 | 11.60 | 0.52 | 0.038 | 0.5776 | [1, -1, 1] | 25.5 |
| GBP_USD:h96 | 213 | -2.10 | -9.53 | 0.46 | 0.027 | 0.6966 | [1, -1, -1] | 24.8 |
| GBP_USD:h480 | 213 | -6.49 | -14.33 | 0.48 | -0.011 | 0.8732 | [1, -1, -1] | 24.8 |
| GBP_USD:h960 | 212 | 23.25 | 32.32 | 0.54 | 0.139 | 0.0425 | [1, -1, 1] | 24.7 |
| USD_CAD:h96 | 211 | -2.76 | -6.40 | 0.45 | -0.010 | 0.8857 | [-1, -1, -1] | 24.6 |
| USD_CAD:h480 | 210 | 2.05 | -3.40 | 0.49 | 0.039 | 0.5784 | [1, -1, -1] | 24.5 |
| USD_CAD:h960 | 210 | 8.05 | 3.25 | 0.50 | 0.038 | 0.5842 | [1, -1, -1] | 24.5 |
| USD_JPY:h96 | 211 | 3.70 | 6.96 | 0.54 | 0.151 | 0.0281 | [-1, 1, 1] | 24.6 |
| USD_JPY:h480 | 211 | -0.78 | 1.66 | 0.50 | 0.099 | 0.1502 | [-1, 1, 1] | 24.6 |
| USD_JPY:h960 | 210 | 4.85 | 1.56 | 0.50 | 0.062 | 0.3735 | [1, -1, 1] | 24.5 |

## Pooled (全ペア) + 次ステージ判定の目安

| horizon | N | EV_fric(pips) | WR | fold符号 | EV>0 ペア | 発火/年 | S3 起案検討の目安 |
|---|---|---|---|---|---|---|---|
| h96 | 1499 | -1.01 | 0.48 | [-1, -1, 1] | 3/7 | 174.6 | ⬜ 目安未達 |
| h480 | 1498 | 0.35 | 0.50 | [1, -1, 1] | 3/7 | 174.5 | ⬜ 目安未達 |
| h960 | 1493 | 3.97 | 0.50 | [1, -1, 1] | 4/7 | 173.9 | ⬜ 目安未達 |

**目安の定義** (判定ではない): pooled EV_fric>0 ∧ N≥60 ∧ fold 3 分割全符号一致 ∧ EV>0 ペア比率 ≥50%。目安を満たしても **S3 pre-reg (候補固定 → OOS 窓 → BH-FDR 判定) を通るまで何も確定しない**。

---
*rapid_edge_probe.py (S2 共通ハーネス) による自動生成。使い方: knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md*
