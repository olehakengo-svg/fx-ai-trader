# rapid_edge_probe S2 診断 — nfp_usd_24h

> **⚠️ 規律 (自動印字)**: 本レポートは S2 探索診断であり**判定ではない**。
> この出力から live/tier 判断・昇格・lot 変更を行うことは**禁止** (Rule 1 は 365日BT or
> Live N≥30 + Bonferroni + Pre-reg LOCK を要求する)。次ステージは S3 pre-reg 起案のみ。
> 探索窓のみ使用 — OOS 窓 (2024-01-01〜) は構造遮断済み。

- 生成: 2026-07-22T08:24:51.862308+00:00 / tool seed=20260722 / spec_hash=`3f4bb00d917ed870`
- 仮説: 実例 (a) 単純系: NFP 後 24h の USD 方向 (uncond USD long、t_e+30m entry)。S2 探索診断の動作実証 — これ自体は診断であり判定ではない。
- notes: E15 pre-reg の uncond 系 combo と同型の最小仮説。E15 discovery で NFP uncond は凍結候補 0 (2026-07-22) — 本 spec はハーネス実証用であり、S3 起案対象ではない。
- 実効窓: 2014-01-01 〜 2023-12-31 (OOS 境界 2024-01-01 で構造遮断済み)

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
| USD_JPY | 0.9786 | True |
| EUR_USD | 0.9902 | True |
| GBP_USD | 0.9874 | True |
| AUD_USD | 0.9972 | True |
| NZD_USD | 0.9738 | True |
| USD_CAD | 0.9813 | True |
| USD_CHF | 1.0000 | True |

skip 理由 (silent except 禁止 — 全件カウント): `{"USD_JPY": {"missing_anchor_bar": 4}, "EUR_USD": {"missing_anchor_bar": 3}, "GBP_USD": {"missing_anchor_bar": 3}, "AUD_USD": {"missing_anchor_bar": 2}, "NZD_USD": {"missing_anchor_bar": 5}, "USD_CAD": {"missing_anchor_bar": 4}, "USD_CHF": {"missing_anchor_bar": 6}}`

イベント件数 (窓内): 120

## ペア × horizon 診断

| cell | N | EV_fric(pips) | median | WR | IC | IC_p | fold符号 | 発火/年 |
|---|---|---|---|---|---|---|---|---|
| USD_JPY:h16 | 116 | -6.94 | -6.24 | 0.46 | — | — | [-1, -1, -1] | 11.6 |
| USD_JPY:h96 | 116 | -0.86 | -0.49 | 0.50 | — | — | [-1, -1, 1] | 11.6 |
| EUR_USD:h16 | 117 | -7.23 | -7.80 | 0.42 | — | — | [-1, 1, -1] | 11.7 |
| EUR_USD:h96 | 117 | -2.81 | -0.40 | 0.50 | — | — | [1, -1, -1] | 11.7 |
| GBP_USD:h16 | 117 | -8.05 | -3.83 | 0.44 | — | — | [-1, -1, -1] | 11.7 |
| GBP_USD:h96 | 117 | -5.54 | -6.43 | 0.44 | — | — | [1, -1, -1] | 11.7 |
| AUD_USD:h16 | 118 | -5.54 | -7.00 | 0.42 | — | — | [-1, -1, -1] | 11.8 |
| AUD_USD:h96 | 118 | -5.48 | 0.70 | 0.51 | — | — | [1, -1, -1] | 11.8 |
| NZD_USD:h16 | 115 | -6.16 | -5.70 | 0.41 | — | — | [-1, -1, -1] | 11.5 |
| NZD_USD:h96 | 115 | -2.52 | -2.00 | 0.49 | — | — | [1, -1, -1] | 11.5 |
| USD_CAD:h16 | 116 | -8.26 | -8.30 | 0.41 | — | — | [1, -1, -1] | 11.6 |
| USD_CAD:h96 | 116 | -4.85 | -5.20 | 0.42 | — | — | [1, 1, -1] | 11.6 |
| USD_CHF:h16 | 114 | -9.97 | -8.25 | 0.35 | — | — | [-1, -1, -1] | 11.4 |
| USD_CHF:h96 | 114 | -3.61 | -4.30 | 0.48 | — | — | [-1, -1, -1] | 11.4 |

## Pooled (全ペア) + 次ステージ判定の目安

| horizon | N | EV_fric(pips) | WR | fold符号 | EV>0 ペア | 発火/年 | S3 起案検討の目安 |
|---|---|---|---|---|---|---|---|
| h16 | 813 | -7.44 | 0.42 | [-1, -1, -1] | 0/7 | 81.3 | ⬜ 目安未達 |
| h96 | 813 | -3.67 | 0.48 | [1, -1, -1] | 0/7 | 81.3 | ⬜ 目安未達 |

**目安の定義** (判定ではない): pooled EV_fric>0 ∧ N≥60 ∧ fold 3 分割全符号一致 ∧ EV>0 ペア比率 ≥50%。目安を満たしても **S3 pre-reg (候補固定 → OOS 窓 → BH-FDR 判定) を通るまで何も確定しない**。

---
*rapid_edge_probe.py (S2 共通ハーネス) による自動生成。使い方: knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md*
