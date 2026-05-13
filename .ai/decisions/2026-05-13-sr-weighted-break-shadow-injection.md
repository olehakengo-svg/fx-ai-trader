---
id: 2026-05-13-sr-weighted-break-shadow-injection
title: SR Weighted Break Shadow Injection — break family pair to sr_weighted_bounce
verdict: APPROVE
rule: R1
related_task: 20260513-2300-sr-weighted-break-shadow-strategy-new
audit_at: 2026-05-13T23:00:00+0900
auditor: Claude (司令塔)
---

# 監査 input
- sr_weighted_bounce Shadow 投入済 (commit 25a1617)
- Family 分離思想 (memory: feedback_sr_weight_is_essence): bounce と break を別戦略に
- 既存 sr_break_retest の smoking gun (MIN_CLUSTERS=1) は是正せず、新戦略で並走

# 規律 checklist
| 規律 | 状態 |
|---|---|
| 既存 SR 戦略を破壊しない | ✅ 新規ファイルのみ |
| Shadow-first (BT に頼らない) | ✅ memory feedback_shadow_first_quant_architecture 準拠 |
| Wave 1 でパラメータ sweep しない | ✅ 全 param 固定 |
| Family 分離 | ✅ break only (bounce は sr_weighted_bounce) |
| Live PnL 影響 | ✅ ゼロ (env=0 デフォルト) |
| KB sync | ✅ wiki + decision 同コミット |
| Composite weight 係数整合 | ✅ bounce と同式 (1:3:5:2:1.5) |

# Shadow → Live promotion gate (pre-reg)
N>=30 + Wilson_lo>=0.40 (Bonferroni m=2 補正、family-wise) + WF 3+ folds pos_ratio>=0.8

# 残懸念
- bounce と break で同一 heavy level が両方発火する可能性
  (例: 突破直後の retest BUY と、retest 失敗で反発 SELL が連続する)
  → cell stats で per-pair-direction observable、Phase 2 で family interaction 分析
- ADX>=20 が緩い可能性、Shadow 蓄積後に閾値 audit
- EUR/USD / EUR/GBP 除外は sr_break_retest 経験則の引継ぎ、Shadow 蓄積後に re-evaluate
