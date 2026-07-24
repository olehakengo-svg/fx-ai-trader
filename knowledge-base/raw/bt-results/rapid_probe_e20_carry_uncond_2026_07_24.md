# rapid_edge_probe S2 診断 — e20_carry_uncond

> **⚠️ 規律 (自動印字)**: 本レポートは S2 探索診断であり**判定ではない**。
> この出力から live/tier 判断・昇格・lot 変更を行うことは**禁止** (Rule 1 は 365日BT or
> Live N≥30 + Bonferroni + Pre-reg LOCK を要求する)。次ステージは S3 pre-reg 起案のみ。
> 探索窓のみ使用 — OOS 窓 (2024-01-01〜) は構造遮断済み。

- 生成: 2026-07-24T05:44:33.243417+00:00 / tool seed=20260722 / spec_hash=`a2b77cf9e1be6a7a`
- 仮説: E20 variant (a) carry-level: sign(政策金利差 BIS) 無条件バイアス (trigger なし、bars hold — §7 計測 1/2 の IC/EV)
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

skip 理由 (silent except 禁止 — 全件カウント): `{"AUD_JPY": {"censored_horizon": 2}, "AUD_USD": {"censored_horizon": 1}, "EUR_AUD": {"censored_horizon": 1}, "EUR_GBP": {"censored_horizon": 2}, "EUR_JPY": {"censored_horizon": 1}, "EUR_USD": {"censored_horizon": 1}, "GBP_JPY": {"censored_horizon": 96}, "GBP_USD": {"censored_horizon": 1}, "NZD_JPY": {"censored_horizon": 1}, "NZD_USD": {"censored_horizon": 1}, "USD_CAD": {"censored_horizon": 2}, "USD_CHF": {"censored_horizon": 1}, "USD_JPY": {"censored_horizon": 2}}`

## ペア × horizon 診断

| cell | N | EV_fric(pips) | median | WR | IC | IC_p | fold符号 | 発火/年 |
|---|---|---|---|---|---|---|---|---|
| AUD_JPY:h96 | 231 | -4.02 | -2.52 | 0.48 | -0.077 | 0.2468 | [-1, -1, 1] | 26.9 |
| AUD_JPY:h480 | 230 | -8.36 | 1.37 | 0.51 | -0.119 | 0.0722 | [-1, -1, 1] | 26.8 |
| AUD_JPY:h960 | 230 | -4.82 | 4.52 | 0.52 | -0.111 | 0.0916 | [-1, -1, 1] | 26.8 |
| AUD_USD:h96 | 223 | -2.65 | -5.80 | 0.47 | -0.098 | 0.1434 | [-1, -1, 1] | 26.0 |
| AUD_USD:h480 | 223 | 9.76 | 10.90 | 0.54 | 0.005 | 0.9425 | [-1, 1, 1] | 26.0 |
| AUD_USD:h960 | 222 | 6.72 | 13.00 | 0.54 | 0.016 | 0.8164 | [-1, 1, 1] | 25.9 |
| EUR_AUD:h96 | 225 | 0.95 | -7.20 | 0.48 | 0.066 | 0.3222 | [1, -1, -1] | 26.2 |
| EUR_AUD:h480 | 225 | 10.28 | 13.60 | 0.54 | 0.002 | 0.9813 | [1, -1, 1] | 26.2 |
| EUR_AUD:h960 | 224 | -10.44 | -11.65 | 0.48 | -0.021 | 0.7499 | [1, -1, 1] | 26.1 |
| EUR_GBP:h96 | 222 | -2.10 | 1.70 | 0.53 | -0.077 | 0.2562 | [-1, -1, -1] | 25.9 |
| EUR_GBP:h480 | 221 | -5.72 | -3.40 | 0.48 | -0.091 | 0.1796 | [-1, -1, 1] | 25.7 |
| EUR_GBP:h960 | 221 | -5.66 | 12.30 | 0.52 | -0.060 | 0.3712 | [-1, -1, -1] | 25.7 |
| EUR_JPY:h96 | 191 | 0.86 | 0.60 | 0.51 | 0.017 | 0.8188 | [1, -1, -1] | 22.3 |
| EUR_JPY:h480 | 191 | 10.82 | -1.80 | 0.49 | 0.110 | 0.1303 | [1, 1, -1] | 22.3 |
| EUR_JPY:h960 | 190 | 18.30 | 21.00 | 0.55 | 0.068 | 0.3485 | [1, 1, 1] | 22.1 |
| EUR_USD:h96 | 221 | 3.58 | -0.80 | 0.48 | -0.060 | 0.3784 | [1, 1, 1] | 25.7 |
| EUR_USD:h480 | 221 | -2.32 | 4.90 | 0.52 | 0.025 | 0.7090 | [-1, 1, -1] | 25.7 |
| EUR_USD:h960 | 220 | 4.89 | -4.20 | 0.49 | -0.067 | 0.3242 | [1, -1, 1] | 25.6 |
| GBP_JPY:h96 | 229 | 0.45 | -3.99 | 0.48 | -0.038 | 0.5666 | [1, -1, 1] | 26.7 |
| GBP_JPY:h480 | 229 | -13.47 | 4.30 | 0.52 | -0.010 | 0.8822 | [-1, -1, 1] | 26.7 |
| GBP_JPY:h960 | 229 | -11.43 | -13.90 | 0.47 | -0.081 | 0.2239 | [-1, 1, 1] | 26.7 |
| GBP_USD:h96 | 221 | -10.69 | -7.23 | 0.46 | -0.035 | 0.6015 | [1, -1, -1] | 25.7 |
| GBP_USD:h480 | 221 | -22.37 | -7.43 | 0.48 | 0.006 | 0.9317 | [-1, 1, -1] | 25.7 |
| GBP_USD:h960 | 220 | -30.14 | -27.83 | 0.44 | -0.082 | 0.2262 | [-1, -1, -1] | 25.6 |
| NZD_JPY:h96 | 234 | 1.26 | 0.00 | 0.50 | -0.076 | 0.2484 | [-1, 1, 1] | 27.3 |
| NZD_JPY:h480 | 234 | -7.08 | 4.62 | 0.51 | -0.001 | 0.9837 | [-1, -1, -1] | 27.3 |
| NZD_JPY:h960 | 233 | -6.31 | -3.40 | 0.48 | -0.041 | 0.5326 | [-1, -1, 1] | 27.1 |
| NZD_USD:h96 | 217 | -2.50 | -2.10 | 0.48 | 0.064 | 0.3515 | [1, -1, -1] | 25.3 |
| NZD_USD:h480 | 217 | 1.02 | 14.00 | 0.54 | -0.007 | 0.9229 | [-1, -1, 1] | 25.3 |
| NZD_USD:h960 | 216 | -5.60 | 8.15 | 0.50 | -0.069 | 0.3137 | [-1, 1, 1] | 25.2 |
| USD_CAD:h96 | 220 | -7.24 | -8.65 | 0.44 | -0.094 | 0.1644 | [-1, 1, -1] | 25.6 |
| USD_CAD:h480 | 219 | -5.18 | 8.10 | 0.53 | -0.028 | 0.6786 | [-1, -1, -1] | 25.5 |
| USD_CAD:h960 | 219 | -18.46 | -25.30 | 0.46 | -0.114 | 0.0920 | [-1, -1, -1] | 25.5 |
| USD_CHF:h96 | 208 | -7.32 | -5.85 | 0.48 | 0.011 | 0.8792 | [-1, -1, 1] | 24.2 |
| USD_CHF:h480 | 208 | -7.58 | -5.80 | 0.47 | -0.081 | 0.2442 | [-1, -1, -1] | 24.2 |
| USD_CHF:h960 | 207 | -5.70 | 0.10 | 0.50 | -0.062 | 0.3755 | [1, -1, -1] | 24.1 |
| USD_JPY:h96 | 219 | -3.37 | -2.24 | 0.48 | -0.070 | 0.3052 | [-1, -1, -1] | 25.5 |
| USD_JPY:h480 | 218 | 2.91 | 14.61 | 0.55 | -0.113 | 0.0957 | [-1, -1, 1] | 25.4 |
| USD_JPY:h960 | 218 | 13.14 | 15.86 | 0.54 | -0.077 | 0.2586 | [1, 1, 1] | 25.4 |

## Pooled (全ペア) + 次ステージ判定の目安

| horizon | N | EV_fric(pips) | WR | fold符号 | EV>0 ペア | 発火/年 | S3 起案検討の目安 |
|---|---|---|---|---|---|---|---|
| h96 | 2861 | -2.51 | 0.48 | [-1, -1, -1] | 5/13 | 333.3 | ⬜ 目安未達 |
| h480 | 2857 | -3.04 | 0.51 | [-1, -1, 1] | 5/13 | 332.9 | ⬜ 目安未達 |
| h960 | 2849 | -4.54 | 0.50 | [-1, -1, 1] | 4/13 | 331.9 | ⬜ 目安未達 |

**目安の定義** (判定ではない): pooled EV_fric>0 ∧ N≥60 ∧ fold 3 分割全符号一致 ∧ EV>0 ペア比率 ≥50%。目安を満たしても **S3 pre-reg (候補固定 → OOS 窓 → BH-FDR 判定) を通るまで何も確定しない**。

---
*rapid_edge_probe.py (S2 共通ハーネス) による自動生成。使い方: knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md*
