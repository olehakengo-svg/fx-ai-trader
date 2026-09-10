# RNB USD/JPY — Round Number Barrier

## Overview
- **Entry Type**: `rnb_usdjpy`
- **Category**: Round Number / Barrier
- **Pair**: USD_JPY
- **Mode**: rnb_usdjpy (auto_start=True, v9.0)
- **Status**: SHADOW (data collection)

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
**行ゼロは仕様ではなくバグ由来**: `rnb_support_bounce` が QUALIFIED_TYPES 未登録のため 2026-04-05 以来 shadow 1 行も出せない ([[../analyses/rnb-dead-mode-and-block-estimand-2026-09-05]])。
登録の可否は R1 パケット [[../decisions/rnb-support-bounce-r1-packet-2026-09-10]] で user 決裁待ち (stage-1 = 構造的 shadow-only 案)。

## Related
- [[index]] — Tier classification
- [[system-reference]] — Mode details
- [[../decisions/rnb-support-bounce-r1-packet-2026-09-10]] — 登録 R1 パケット (2026-09-10)
- [[../analyses/rnb-dead-mode-and-block-estimand-2026-09-05]] — 153 日 dead mode の経緯
