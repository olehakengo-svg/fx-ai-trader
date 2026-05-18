# HourlyEngine Shadow Ramp Activation (2026-05-18)

## 背景
- v2.1 で daytrade_1h_* modes が auto_start: False 化 (KSB+DMB 500日BT 全戦略 AVOID 由来)
- Phase B-1 (commit 35961351) で Price-Shock Rev 5 戦略を HourlyEngine 追加
- 司令塔監査 2026-05-18T16:25 JST で「直近 509 trades 中 H1 戦略 0 件発火」を実測

## Decision
1. 全 10 modes (`daytrade_1h*`) を `auto_start: True` 化
2. `_shadow_always` に KSB+DMB+5 PriceShockRev (合計 7 戦略) を frozenset で固定
3. Live emission は構造的に禁止 (HourlyEngine が必ず shadow path に routing)
4. v2.1 α 不在判定は 2 年経過データで再評価する含意も込める

## Rationale
- Shadow ramp 中は Live 流出なし → リスク 0
- KSB+DMB の 2026-04 以降データで再評価可能
- Phase B-1 Live shadow ramp の前提条件 (HourlyEngine 起動)
- クリーンデータ蓄積を最大化 (feedback_shadow_first_quant_architecture)

## Live promote 条件
本 task は **Shadow ramp 起動のみ**、Live promote 判定は別 task:
- Price-Shock Rev: decisions/price-shock-rev-promote-criteria-2026-05-18.md (Bonferroni m=5)
- KSB+DMB: 再評価結果に応じ別途 pre-reg LOCK 作成 (本 task 範囲外)

## Verification (deploy 後)
- Render 本番 /api/demo/trades で 24h 以内に H1 戦略から **is_shadow=1 trade が観測される**
- Live emission (is_shadow=0) は **0 件継続**
