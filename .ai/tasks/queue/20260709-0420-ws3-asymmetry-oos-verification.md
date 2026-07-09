---
id: 20260709-0420-ws3-asymmetry-oos-verification
title: "[v2.3 WS3/R1 stage-1] 方向性非対称の OOS 検証 — pre-reg LOCK 済み (2024-07〜2025-07 窓)"
owner: claude
status: in_progress
priority: P1
created_at: 2026-07-09T04:20:00+0900
roadmap_gate: "v2.3 WS3 主戦線の最初の合否判定。stage-1 純研究 — live 変更なし。stage-2 (barrier/EV + TV canon) と実装は PASS 後に別 pre-reg + user 承認"
rule: R1
executor_note: "claude 直接実行 (exit-repair 方式)。autopilot は本タスクに触れないこと (owner=claude, in_progress = 排他 claim)"
prereq_artifacts:
  - knowledge-base/wiki/decisions/ws3-asymmetry-oos-prereg-2026-07-09.md   # 🔒 LOCKED 仕様 (変更禁止)
  - knowledge-base/wiki/analyses/ws3-mfe-distribution-2026-07-08.md        # 探索診断 (候補 8 cells の出所)
related:
  - knowledge-base/wiki/syntheses/roadmap-v2.3-payoff-friction-repair.md
---

# 要求仕様 (pre-reg の機械的実行 — 設計変更禁止)

1. **データ準備**: USD_JPY / AUD_JPY の 15m 2024-07〜2025-07 を Massive API から取得
   (不能なら短縮 OOS を verdict に明記)。隔離 worktree に末尾 2025-07-07 切詰め parquet を配置
2. **OOS スキャン**: `tools/ws3_mfe_scan.py` 系 (同一エンジン) を OOS 窓 (2024-07-07〜2025-07-07)
   で実行、候補 8 cells の MFE/MAE を primary horizon (pre-reg §2 の型別固定) で計測
3. **判定**: median-ratio 日次ブロックブートストラップ (B=10,000) → BH-FDR q=0.10 (m=8)
   ∧ point ratio ≥1.2 ∧ N≥30。ナイフエッジ3点検査 (pre-reg §5)
4. **verdict**: pre-reg §4 の分岐 — PASS≥1 → stage-2 pre-reg 起案 / PASS=0 → 新シグナル系統探索へ
   roadmap 反映。出力 = `raw/bt-results/ws3_asymmetry_oos_2026_07.{json,md}` + pre-reg 追記
5. **期日**: 2026-07-16
