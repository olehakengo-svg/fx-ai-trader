# rapid_edge_probe S2 診断 — e20_carry_breakout

> **⚠️ 規律 (自動印字)**: 本レポートは S2 探索診断であり**判定ではない**。
> この出力から live/tier 判断・昇格・lot 変更を行うことは**禁止** (Rule 1 は 365日BT or
> Live N≥30 + Bonferroni + Pre-reg LOCK を要求する)。次ステージは S3 pre-reg 起案のみ。
> 探索窓のみ使用 — OOS 窓 (2024-01-01〜) は構造遮断済み。

- 生成: 2026-07-24T05:45:06.858531+00:00 / tool seed=20260722 / spec_hash=`eb5e22b13401c535`
- 仮説: E20 variant (a) carry-level: sign(政策金利差 BIS) × 20-bar breakout entry、first_touch σ_h barrier
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
| AUD_JPY | 1.0000 | True |
| AUD_USD | 0.9949 | True |
| EUR_AUD | 1.0000 | True |
| EUR_GBP | 0.9885 | True |
| EUR_JPY | 1.0000 | True |
| EUR_USD | 0.9869 | True |
| GBP_JPY | 1.0000 | True |
| GBP_USD | 0.9866 | True |
| NZD_JPY | 1.0000 | True |
| NZD_USD | 0.9692 | True |
| USD_CAD | 0.9796 | True |
| USD_CHF | 0.9928 | True |
| USD_JPY | 0.9754 | True |

skip 理由 (silent except 禁止 — 全件カウント): `{"AUD_JPY": {"atr_nan": 198, "censored_horizon": 2}, "AUD_USD": {"atr_nan": 204, "censored_horizon": 12}, "EUR_AUD": {"atr_nan": 198, "censored_horizon": 1}, "EUR_GBP": {"atr_nan": 279, "censored_horizon": 2}, "EUR_JPY": {"atr_nan": 147, "censored_horizon": 1}, "EUR_USD": {"atr_nan": 147, "censored_horizon": 1}, "GBP_JPY": {"atr_nan": 210, "censored_horizon": 1}, "GBP_USD": {"atr_nan": 222, "censored_horizon": 2}, "NZD_JPY": {"atr_nan": 204, "censored_horizon": 2}, "NZD_USD": {"atr_nan": 231, "censored_horizon": 2}, "USD_CAD": {"atr_nan": 216}, "USD_CHF": {"censored_horizon": 1}, "USD_JPY": {"atr_nan": 180, "censored_horizon": 1}}`

## ペア × horizon 診断

| cell | N | EV_fric(pips) | median | WR | IC | IC_p | fold符号 | 発火/年 |
|---|---|---|---|---|---|---|---|---|
| AUD_JPY:h96 | 222 | -13.51 | -10.02 | 0.43 | -0.092 | 0.1729 | [-1, -1, -1] | 25.9 |
| AUD_JPY:h480 | 221 | -11.33 | -0.83 | 0.49 | -0.045 | 0.5050 | [1, -1, -1] | 25.7 |
| AUD_JPY:h960 | 221 | -17.55 | -3.23 | 0.48 | -0.154 | 0.0223 | [-1, -1, -1] | 25.7 |
| AUD_USD:h96 | 213 | -5.82 | -5.50 | 0.47 | -0.047 | 0.4945 | [-1, -1, -1] | 24.8 |
| AUD_USD:h480 | 213 | 1.74 | 9.40 | 0.55 | 0.009 | 0.8963 | [-1, 1, 1] | 24.8 |
| AUD_USD:h960 | 213 | 3.19 | 4.80 | 0.54 | -0.043 | 0.5307 | [-1, 1, 1] | 24.8 |
| EUR_AUD:h96 | 215 | -4.25 | -1.00 | 0.48 | 0.247 | 0.0003 | [1, 1, -1] | 25.0 |
| EUR_AUD:h480 | 215 | -11.80 | -0.40 | 0.50 | 0.077 | 0.2628 | [1, -1, -1] | 25.0 |
| EUR_AUD:h960 | 214 | -19.48 | 14.40 | 0.52 | -0.015 | 0.8240 | [-1, -1, -1] | 24.9 |
| EUR_GBP:h96 | 211 | -5.29 | -6.00 | 0.43 | -0.036 | 0.6003 | [-1, -1, -1] | 24.6 |
| EUR_GBP:h480 | 210 | -9.01 | -13.55 | 0.47 | -0.076 | 0.2758 | [-1, -1, 1] | 24.5 |
| EUR_GBP:h960 | 210 | 8.41 | 9.70 | 0.52 | -0.065 | 0.3482 | [1, 1, 1] | 24.5 |
| EUR_JPY:h96 | 182 | 0.33 | 0.85 | 0.51 | 0.185 | 0.0124 | [1, -1, 1] | 21.2 |
| EUR_JPY:h480 | 182 | -4.95 | -16.60 | 0.48 | 0.217 | 0.0033 | [-1, -1, 1] | 21.2 |
| EUR_JPY:h960 | 181 | 6.63 | 9.20 | 0.51 | 0.097 | 0.1947 | [1, -1, 1] | 21.1 |
| EUR_USD:h96 | 212 | 2.07 | -1.85 | 0.48 | -0.097 | 0.1592 | [1, -1, 1] | 24.7 |
| EUR_USD:h480 | 212 | -11.23 | -15.70 | 0.44 | 0.017 | 0.8061 | [-1, 1, -1] | 24.7 |
| EUR_USD:h960 | 211 | -0.98 | -7.80 | 0.48 | -0.076 | 0.2702 | [1, 1, -1] | 24.6 |
| GBP_JPY:h96 | 220 | 4.62 | 7.15 | 0.53 | -0.011 | 0.8760 | [-1, 1, 1] | 25.6 |
| GBP_JPY:h480 | 220 | 0.98 | 8.65 | 0.52 | -0.082 | 0.2286 | [-1, -1, 1] | 25.6 |
| GBP_JPY:h960 | 219 | 11.47 | 9.80 | 0.51 | -0.087 | 0.2005 | [-1, -1, 1] | 25.5 |
| GBP_USD:h96 | 213 | -8.74 | -7.43 | 0.44 | 0.020 | 0.7688 | [-1, 1, -1] | 24.8 |
| GBP_USD:h480 | 212 | -15.77 | -11.38 | 0.47 | -0.042 | 0.5461 | [-1, -1, -1] | 24.7 |
| GBP_USD:h960 | 212 | -24.92 | -36.43 | 0.44 | -0.123 | 0.0731 | [-1, -1, -1] | 24.7 |
| NZD_JPY:h96 | 224 | -11.41 | -5.10 | 0.45 | 0.052 | 0.4349 | [1, -1, -1] | 26.1 |
| NZD_JPY:h480 | 223 | -17.89 | 0.00 | 0.50 | 0.045 | 0.5068 | [1, -1, -1] | 26.0 |
| NZD_JPY:h960 | 223 | -17.83 | -1.40 | 0.49 | -0.078 | 0.2465 | [-1, -1, -1] | 26.0 |
| NZD_USD:h96 | 210 | -1.23 | -0.85 | 0.50 | 0.060 | 0.3901 | [1, -1, -1] | 24.5 |
| NZD_USD:h480 | 209 | -4.11 | -3.80 | 0.49 | 0.032 | 0.6444 | [1, 1, -1] | 24.3 |
| NZD_USD:h960 | 209 | -13.68 | -11.10 | 0.48 | -0.050 | 0.4686 | [-1, -1, -1] | 24.3 |
| USD_CAD:h96 | 211 | -5.71 | -0.00 | 0.50 | -0.010 | 0.8849 | [1, -1, -1] | 24.6 |
| USD_CAD:h480 | 211 | -6.87 | -12.10 | 0.49 | -0.103 | 0.1363 | [-1, -1, 1] | 24.6 |
| USD_CAD:h960 | 211 | -12.33 | 0.80 | 0.50 | -0.150 | 0.0299 | [-1, -1, 1] | 24.6 |
| USD_CHF:h96 | 200 | -5.80 | -4.55 | 0.45 | -0.009 | 0.9043 | [1, -1, -1] | 23.3 |
| USD_CHF:h480 | 200 | 2.34 | 2.15 | 0.53 | -0.050 | 0.4816 | [1, -1, -1] | 23.3 |
| USD_CHF:h960 | 199 | 1.37 | -0.90 | 0.49 | -0.023 | 0.7492 | [1, -1, 1] | 23.2 |
| USD_JPY:h96 | 211 | 2.15 | 4.76 | 0.57 | 0.059 | 0.3964 | [1, -1, 1] | 24.6 |
| USD_JPY:h480 | 211 | -4.90 | -0.34 | 0.50 | -0.005 | 0.9377 | [-1, -1, 1] | 24.6 |
| USD_JPY:h960 | 210 | 3.79 | 19.01 | 0.53 | -0.040 | 0.5688 | [-1, -1, 1] | 24.5 |

## Pooled (全ペア) + 次ステージ判定の目安

| horizon | N | EV_fric(pips) | WR | fold符号 | EV>0 ペア | 発火/年 | S3 起案検討の目安 |
|---|---|---|---|---|---|---|---|
| h96 | 2744 | -4.13 | 0.48 | [-1, -1, -1] | 4/13 | 319.7 | ⬜ 目安未達 |
| h480 | 2739 | -7.24 | 0.49 | [-1, -1, -1] | 3/13 | 319.1 | ⬜ 目安未達 |
| h960 | 2733 | -5.76 | 0.50 | [-1, -1, 1] | 6/13 | 318.4 | ⬜ 目安未達 |

**目安の定義** (判定ではない): pooled EV_fric>0 ∧ N≥60 ∧ fold 3 分割全符号一致 ∧ EV>0 ペア比率 ≥50%。目安を満たしても **S3 pre-reg (候補固定 → OOS 窓 → BH-FDR 判定) を通るまで何も確定しない**。

---
*rapid_edge_probe.py (S2 共通ハーネス) による自動生成。使い方: knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md*
