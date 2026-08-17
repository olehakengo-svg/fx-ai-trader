---
id: 20260817-e7-phase1-discovery-oos
title: "[v2.3 供給ライン] E7 phase-1 — discovery→凍結→OOS verdict 執行 (前倒し: 凍結期日 08-21 / verdict 期日 08-28)"
owner: claude (session sharp-pike-eec3e7)
status: in_progress
claimed_at: 2026-08-17T05:10:00+0000
priority: P1
roadmap_gate: "トラックB 供給ライン最終 2026 マイルストーン。pre-reg = [[e15-e7-event-modality-prereg-2026-07-18]] §6 (🔒 phase-0 FULL LOCK 済み family)。純研究、live/shadow/Kelly 変更なし"
rule: R1 手続き (pre-reg 執行、判定は機械。設計自由度ゼロ)
executor_note: "pre-flight §3.3c 完了済み (panel 凍結、実効 12 combo = θ=0.5 のみ、modal 予想 C3/C5)。phase-0 の 9 日前倒し前例に準拠して前倒し執行。排他 claim = 本 ticket + draft PR"
prereq_artifacts:
  - knowledge-base/wiki/decisions/e15-e7-event-modality-prereg-2026-07-18.md   # SSOT §6/§5b/§5c/§8
  - raw/bt-results/e7/e7_surprise_panel.csv                                     # 凍結サプライズパネル (§3.3c)
  - tools/event_modality_lib.py                                                 # 共有実行機構 (event_trade/ATR/canary)
---

# 要求仕様 (pre-reg §6 の執行 — phase-0 ticket と同型)

1. **ハーネス拡張**: E7 sign-follow (z>+θ→USD long / z<−θ→USD short、fade 禁止)、entry = t_e 後 {+1,+2} 本目 M15 open、h∈{1h,4h,24h}、24 combo (θ=1.0 は §5b(iii) ゲートで機械脱落見込み — grid 定義は変更しない)。z は凍結パネルから join のみ (再計算禁止)。
2. **discovery** (§5a 準拠、探索窓 〜2023-12-31、OOS 接触禁止): 選抜 4 条件 (EV_te>0 ∧ EV_ft>0 ∧ N≥60 ∧ blocks≥40 ∧ fold 2/3) → 凍結規則 (fold → EV-per-vol → イベント種 ≤3) で m₁ ≤ 8。
3. **候補凍結**: pre-reg §6 へ凍結表追記コミット = 🔒 + `raw/bt-results/e7_frozen_candidates.json`。
4. **OOS verdict** (§5c 完全同一: block bootstrap B=10k + IM t / max(p) / BH q=0.05 (m=m₁) / レグ B 経済性 / ナイフエッジ 4 点)。canary/join 契約を tests/ に pin してから OOS 接触 (§10-6)。verdict は pre-reg §13 追記 + registry `e15-e7-event-prereg-phase1-verdict` resolve + changelog。
5. モジュールトップ副作用禁止 / silent except 禁止 / 既存テスト green + check.py。KB 同一コミット。
