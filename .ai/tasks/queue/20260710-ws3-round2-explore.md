---
id: 20260710-ws3-round2-explore
title: "[v2.3 WS3/供給ライン] 探索2周目 — 方向分割×未走査ペア×h96 の新軸探索 (純研究)"
owner: claude
status: in_progress  # 診断+EVスクリーン+LOCK 完了 (2026-07-10)、残 = OOS verdict (期日 07-17)
priority: P2
created_at: 2026-07-10T15:00:00+0900
roadmap_gate: "トラックB 供給ライン (decision memo 2026-07-10)。live/shadow 変更なし。stage-2 と独立、その結果に依存しない"
rule: R1
executor_note: "claude 直接実行 (本セッション、排他 claim — autopilot / 並行セッション / zen-mahavira は触れないこと)。stage-2 成果物 (tools/ws3_stage2_barrier_sim.py, raw/bt-results/ws3_stage2_*) には接触しない"
prereq_artifacts:
  - knowledge-base/wiki/decisions/ws3-round2-explore-prereg-2026-07-10.md   # DRAFT — 診断後に候補固定して self-LOCK
  - knowledge-base/wiki/decisions/shortest-path-decision-memo-2026-07-10.md # user 承認決裁 (2026-07-10)
related:
  - knowledge-base/wiki/decisions/ws3-asymmetry-oos-prereg-2026-07-09.md
---

# 要求仕様 (pre-reg DRAFT §2 の手続き実行)

1. **診断 (R3、探索窓のみ)**: `tools/ws3_mfe_scan.py` 系を方向分割対応に拡張し、探索窓 (2025-07-08〜2026-06-07、診断窓除外) で新軸 (方向分割 / 未走査ペア / h96) をスキャン。OOS 窓 (2024-25) に接触しない
2. **候補固定**: 選抜規則 (ratio≥1.3 h24 ∪ 持続型 h96、N≥30、m≤10、判定済み8セル+方向分割サブセル/falsified 6系統/trendline_sweep×EUR_USD 除外) で列挙 → pre-reg §2b に追記 → self-LOCK (Status 🔒)
3. **OOS 検証**: 2024-07-07〜2025-07-07、round-1 と同一判定 (block bootstrap B=10,000 + BH-FDR q=0.10 ∧ ratio≥1.2 ∧ N≥30 + ナイフエッジ3点)
4. **期日**: 診断+LOCK 2026-07-14 / verdict 2026-07-17。LOCK 時に registry へ期日エントリ追加
5. PASS≥1 → stage-2 型 pre-reg 起案 (user LOCK) / PASS=0 → 外部仮説探索へ転進 (事前定義済み)
