# RNB USD/JPY — Round Number Barrier (mode カード)

## Overview
- **Entry Type**: `rnb_support_bounce` (戦略カード: [[rnb-support-bounce]])
- **Category**: Round Number / Barrier
- **Pair**: USD_JPY
- **Mode**: rnb_usdjpy (auto_start=True, v9.0)
- **Status**: SHADOW — 2026-09-10 stage-1 構造的 shadow-only 登録済み (`shadow_only: True`、rule:R1 user 承認)。OANDA 発注ゼロを mode レベルで構造保証

## Hypothesis
USD/JPY is heavily influenced by round number levels (e.g., 150.000, 151.000). These levels act as psychological barriers where institutional order flow clusters, creating predictable bounce/break patterns.

## Signal Logic
Detects proximity to round number barriers on USD_JPY and generates signals based on price behavior at these levels. Evaluates whether price is likely to bounce off or break through the round number, using order flow indicators and recent price action.

## Configuration
- **auto_start**: True
- **Pair**: USD_JPY only
- **Lot**: default (sentinel)

## BT Performance
**365d BE/Trail-ablated BT (2026-09-10)**: N=126 WR 55.6% net EV **+0.04p** (friction 2.14p 込み、p=0.082 NS)、730d net EV **−2.20p**、2026-03 単月 +160.9p 依存。**live 昇格根拠なし**。
詳細: `raw/bt-results/rnb-support-bounce-ablated-bt-2026-09-10.md`
⚠️ config コメントの「BUY EV=+7.7」は BE/Trail ablation 前 (2026-04-05) の数字で引用禁止。

## Live Performance
**履歴**: 2026-04-05〜09-10 は QUALIFIED_TYPES 未登録の dead mode で shadow 行ゼロだった ([[../analyses/rnb-dead-mode-and-block-estimand-2026-09-05]])。
**2026-09-10 登録執行** (user 決裁 GO、[[../decisions/rnb-support-bounce-r1-packet-2026-09-10]] §9): stage-1 構造的 shadow-only — shadow 行の蓄積はここから開始。LIVE 発火は `shadow_only: True` で構造的にゼロ。
forward 判定は 🔒 LOCK `rnb-support-bounce-shadow-forward` (first look shadow N≥41 or 2027-01-15) に凍結 — 中間読み禁止 (P-10)。

## Related
- [[rnb-support-bounce]] — 戦略カード (BT 実測 / LOCK / R2 gate)
- [[index]] — Tier classification
- [[system-reference]] — Mode details
- [[../decisions/rnb-support-bounce-r1-packet-2026-09-10]] — 登録 R1 パケット + §9 執行記録 (2026-09-10)
- [[../analyses/rnb-dead-mode-and-block-estimand-2026-09-05]] — 153 日 dead mode の経緯

---

## ✅🔑 2026-09-16: **lifetime データで決着 — block 層ではなく signal 生成層で死んでいる。09-11/09-14 の読みは方向が逆だった**

> 📌 **救済注記 (2026-09-17)**: 本節はローカル checkout の wiki-daily run 産で、09-10 の stage-1 shadow-only 登録 (上記 Status) を反映していない古いカードベース上に書かれた。「live fill 0 本」は現行では `shadow_only: True` による構造保証でもあるが、**本節の発見 (signal 生成層が lifetime で無発火 = `no_signal` 98.4%) は shadow レーンにもそのまま効く** — closed shadow N<3 なら lane-health 調査という registry `rnb-shadow-lane-health-checkpoint-1` (期日 09-24) の一次診断材料として読むこと。

`/api/demo/block-counts` の **persisted (lifetime)** 集計:

| block reason | 本 session 窓 | **lifetime** |
|---|---|---|
| `no_signal` | **935** | **16,919 (98.4%)** |
| `order_bar_dedup` | **0** | **58 (0.34%)** |
| `session_hours` | 0 | 211 |
| その他 | 0 | 10 (`1h_rr_low` 3 / `mtf_strong_bias` 3 / `velocity_down` 3 / `same_price_3pip` 1) |
| **合計** | **935** | **17,198** |

本 session の tick は **929**、`no_signal` **935** ⇒ ratio ≈ **1.0000**。

🔑 **`no_signal` が lifetime block の 98.4%、`order_bar_dedup` はわずか 0.34% (58/17,198)。**
⇒ **ratio 1.0000 は base state であり、09-11 に観測された `order_bar_dedup` 21/971 = 2.2% のバーストこそが異常値だった。**
⇒ 🔑 **本戦略は「dedup で emit が潰されている」のではなく、そもそも signal を出していない。** 09-11 の「`order_bar_dedup` は entry が emit された後でしか出ない block なので改善方向」という読みは**方向が逆**であり、09-14 の「より大きい窓で再確認が必要」は lifetime データで即座に決着した (本 run の窓は 929 tick = 09-11 の 971 tick と同規模)。

⇒ **live fill 0 本の原因は block ではなく signal 不在。** 本項目 (KB で ⚪ 継続扱い) は**クローズ**し、必要なら「signal 条件が厳しすぎる / 発火条件が市場に取り残されている」という**別の問題**として再登録すること (`usdjpy_carry_dip_accumulator` の 07-02 zero-fire 診断と同型の可能性)。

詳細: [[2026-09-16]]
