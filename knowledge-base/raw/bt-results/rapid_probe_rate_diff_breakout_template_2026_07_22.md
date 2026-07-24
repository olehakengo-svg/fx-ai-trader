# rapid_edge_probe S2 診断 — rate_diff_breakout_template

> **⚠️ 規律 (自動印字)**: 本レポートは S2 探索診断であり**判定ではない**。
> この出力から live/tier 判断・昇格・lot 変更を行うことは**禁止** (Rule 1 は 365日BT or
> Live N≥30 + Bonferroni + Pre-reg LOCK を要求する)。次ステージは S3 pre-reg 起案のみ。
> 探索窓のみ使用 — OOS 窓 (2024-01-01〜) は構造遮断済み。

- 生成: 2026-07-22T08:25:07.177268+00:00 / tool seed=20260722 / spec_hash=`d80a13112bfd8c2e`
- 仮説: 実例 (b) user 仮説の雛形: 金利差方向 × テクニカル breakout entry。外部 series (金利差) は E20 feasibility (別 agent) の結果待ちのため __dummy_e20__ (決定的ダミー ±1、エッジ期待ゼロ) で配管の構造のみ検証する。診断であり判定ではない。
- notes: E20 通過後の差し替え手順: direction_source.column を実列名に、file に csv パス (date + per-pair 列) を設定するだけで同一配管が動く。lag_days=1 は公表遅延 (look-ahead 構造排除) — 実 series の公表タイミングに合わせて要再設定。
- 実効窓: 2016-01-01 〜 2023-12-31 (OOS 境界 2024-01-01 で構造遮断済み)
- **⚠️ DUMMY series 実行**: direction_source はダミー列 (決定的 ±1、エッジ期待ゼロ)。外部 series 接続は E20 feasibility (別 agent) の結果待ち。本レポートは配管の構造検証のみに使うこと。

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
| USD_JPY | 0.9773 | True |
| EUR_USD | 0.9908 | True |
| GBP_USD | 0.9868 | True |

skip 理由 (silent except 禁止 — 全件カウント): `{"USD_JPY": {"atr_nan": 122, "censored_horizon": 1}, "EUR_USD": {"atr_nan": 180, "censored_horizon": 1}, "GBP_USD": {"atr_nan": 122, "censored_horizon": 1}}`

## ペア × horizon 診断

| cell | N | EV_fric(pips) | median | WR | IC | IC_p | fold符号 | 発火/年 |
|---|---|---|---|---|---|---|---|---|
| USD_JPY:h16 | 1495 | -1.83 | -3.14 | 0.43 | -0.022 | 0.4041 | [-1, -1, -1] | 186.9 |
| USD_JPY:h96 | 1494 | -1.39 | -3.09 | 0.48 | 0.011 | 0.6668 | [1, -1, -1] | 186.8 |
| EUR_USD:h16 | 1531 | -2.51 | -2.60 | 0.43 | -0.031 | 0.2261 | [-1, -1, -1] | 191.4 |
| EUR_USD:h96 | 1530 | -1.89 | -1.60 | 0.49 | 0.005 | 0.8495 | [-1, -1, -1] | 191.3 |
| GBP_USD:h16 | 1533 | -6.16 | -7.13 | 0.40 | -0.063 | 0.0142 | [-1, -1, -1] | 191.7 |
| GBP_USD:h96 | 1532 | -7.12 | -8.83 | 0.46 | -0.033 | 0.1984 | [-1, -1, -1] | 191.6 |

## Pooled (全ペア) + 次ステージ判定の目安

| horizon | N | EV_fric(pips) | WR | fold符号 | EV>0 ペア | 発火/年 | S3 起案検討の目安 |
|---|---|---|---|---|---|---|---|
| h16 | 4559 | -3.52 | 0.42 | [-1, -1, -1] | 0/3 | 570.1 | ⬜ 目安未達 |
| h96 | 4556 | -3.49 | 0.47 | [-1, -1, -1] | 0/3 | 569.7 | ⬜ 目安未達 |

**目安の定義** (判定ではない): pooled EV_fric>0 ∧ N≥60 ∧ fold 3 分割全符号一致 ∧ EV>0 ペア比率 ≥50%。目安を満たしても **S3 pre-reg (候補固定 → OOS 窓 → BH-FDR 判定) を通るまで何も確定しない**。

---
*rapid_edge_probe.py (S2 共通ハーネス) による自動生成。使い方: knowledge-base/wiki/analyses/rapid-edge-probe-2026-07-22.md*
