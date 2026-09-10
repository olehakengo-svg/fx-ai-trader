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
