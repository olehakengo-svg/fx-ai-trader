# rnb_support_bounce — RNB Support Bounce (USD/JPY 15m BUY-only)

## Overview
- **Entry Type**: `rnb_support_bounce`
- **Category**: Round Number / Barrier (support bounce)
- **Pair**: USD_JPY only
- **Mode**: `rnb_usdjpy` (auto_start=True, 30s tick, active hours UTC 7-20, direction_filter=BUY)
- **Status**: SHADOW — stage-1 構造的 shadow-only 登録 (2026-09-10, rule:R1 user 承認)。mode `shadow_only: True` の 3 点 block (送信ガード最終段 / resend gate / write-path) で OANDA 発注ゼロを構造保証。sentinel 非追加 (minlot live 経路は開いていない)

## Hypothesis
USD/JPY のラウンドナンバー (150.000 等) は機関注文が集積する心理的バリアとして
機能し、サポート側への接近 → 反発 (support bounce) に予測可能性がある。
BUY-only (compute_rnb_signal は構造上 SELL を返さない — 12.8y 実測 SELL=0)。

## Registration History (重要)
- **2026-04-05 (db5e3e4c)**: MODE_CONFIG / signal_fn / _1H_PRESERVE_SLTP /
  MAX_HOLD_SEC に配線されたが **QUALIFIED_TYPES だけ未登録** → BUY が全て
  `unknown_type` で落ち、**shadow 1 行も出せない dead mode を 158 日間継続**
  ([[../analyses/rnb-dead-mode-and-block-estimand-2026-09-05]])
- **2026-09-10**: stage-1 構造的 shadow-only 登録 (rule:R1, user 承認
  「進めて」2026-09-10) — [[../decisions/rnb-support-bounce-r1-packet-2026-09-10]]
  §9 執行記録。登録は「勝てる戦略の昇格」ではなく**観測レーンの開通**

## BT Performance (BE/Trail-ablated, 2026-09-10 — 正直な数字)
| 窓 | N | WR | Wilson_lo | net EV (f2.14) | 備考 |
|---|---:|---:|---:|---:|---|
| **365d** | 126 | 55.6% | 46.8% | **+0.04p** | ≈ゼロ、p=0.082 **NS**。2026-03 単月 +160.9p 依存 (他 12 ヶ月計 −155.4p) |
| 730d | 295 | 44.8% | 39.2% | **−2.20p** | 前年は明確に負け |
| 90d | 23 | 52.2% | 33.0% | **−3.95p** | 直近も負け |

- friction 込み BEV_WR = 49.0%。Wilson_lo 46.8% < 49.0% = **昇格 gate 不成立**
- **live 昇格根拠はない** — 登録の正当化は「~3.0 setups/週の無料 shadow N 源」のみ
- ⚠️ config 旧コメントの「BUY EV=+7.7」は BE/Trail ablation 前 (2026-04-05) の数字で**引用禁止**
- 詳細: `raw/bt-results/rnb-support-bounce-ablated-bt-2026-09-10.md`

## Forward LOCK (🔒 rnb-support-bounce-shadow-forward, 2026-09-10)
- estimand: 2026-09-10 以降の forward shadow rows (USD_JPY×BUY, closed,
  dedup_violation=0, 厳格 shadow) の WR / net EV (friction 2.14p)
- first look: shadow **N≥41** or **2027-01-15** の早い方 — それまで
  gate×outcome joint 計算禁止 (P-10)、中間再計算禁止
- 採用境界 (stage-2 R1 起案): Wilson_lo(WR) > 49.0% ∧ net EV > 0
- 棄却境界: Wilson_hi(WR) < 42.9% (gross BEV) → クローズ + auto_start=False 提案
- 監視: registry `rnb-support-bounce-shadow-forward` (prereg_trigger_watch 日次) +
  `tools/rnb_shadow_demote_gate.py` (R2 demote gate, N≥30 から、r2-alert-scheduled 6h 毎)

## Live Performance
- LIVE 発火は構造的にゼロ (shadow_only)。shadow 行の蓄積は 2026-09-10 登録
  デプロイから開始 — first look まで成績の中間読みはしない

## Related
- [[rnb-usdjpy]] — mode カード (エンジン設定)
- [[../decisions/rnb-support-bounce-r1-packet-2026-09-10]] — R1 パケット + §9 LOCK/執行記録
- [[../analyses/rnb-dead-mode-and-block-estimand-2026-09-05]] — 153 日 dead mode の経緯
- [[index]] — Tier classification
