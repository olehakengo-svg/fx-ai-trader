---
id: 2026-05-13-sr-weighted-bounce-shadow-injection
title: SR Weighted Bounce Shadow Injection — Wave 1 (audit_only)
verdict: APPROVE
rule: R1
related_task: 20260513-2200-sr-weighted-bounce-shadow-strategy-new
audit_at: 2026-05-13T22:00:00+0900
auditor: Claude (司令塔)
---

# 監査 input
- Phase 2 BT survivor: sr_anti_hunt_bounce (N=594, p=0.0034)
- v2 audit forensic: BT pipeline と production pipeline は trade Jaccard ≈ 0
- OANDA 公式 Dow theory horizon 記事の thesis 支持
- 既存 5 SR 戦略の実装監査: 誰も touch_count を gate に使っていない

# 規律 checklist
| 規律 | 状態 |
|---|---|
| 既存 5 SR 戦略を破壊しない | ✅ 新規ファイルのみ |
| Shadow-first (BT に頼らない) | ✅ memory feedback_shadow_first_quant_architecture 準拠 |
| Wave 1 でパラメータ sweep しない | ✅ K=3.0 / percentile=30% 固定 |
| Family 分離 | ✅ bounce only (break は後続 task) |
| Live PnL 影響 | ✅ ゼロ (env=0 デフォルト、SHADOW_ALWAYS 経由 audit_only) |
| KB sync | ✅ wiki/strategies/sr-weighted-bounce.md 同コミット |

# Shadow → Live promotion gate (pre-reg)
N>=30 + Wilson_lo>=0.40 (Bonferroni m=2 補正) + WF 3+ folds pos_ratio>=0.8

# 残懸念
- audit v2 で composite weight quintile が WR を discriminate しなかった
  (synthetic universe での結果)。Shadow 実取引で再現するか観察
- P90 excursion pip table が 2026-Q1 calibration。Shadow N>=30 後に再 audit 必須
- detector 依存 (KDE vs PIVOT で trade Jaccard 0) は別 backlog
