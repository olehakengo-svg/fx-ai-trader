---
id: 20260709-1610-ws3-stage2-barrier-ev-prereg
title: "[v2.3 WS3/R1 stage-2] barrier/EV 設計 pre-reg 起案 — PASS 2 セル限定 (london_fix_reversal×EUR_USD / htf_false_breakout×AUD_JPY)"
owner: claude
status: in_progress
priority: P1
created_at: 2026-07-09T16:10:00+0900
roadmap_gate: "v2.3 WS3 stage-2。stage-1 OOS verdict PASS (PR #69) の §4 固定分岐。起案は DRAFT — LOCK は user 最終承認後。live 変更なし"
rule: R1
executor_note: "claude 直接実行 (zen-mahavira セッション、排他 claim — autopilot / 並行セッションは触れないこと)"
prereq_artifacts:
  - knowledge-base/wiki/decisions/ws3-asymmetry-oos-prereg-2026-07-09.md   # stage-1 verdict §8 (PASS 2/8)
  - knowledge-base/raw/bt-results/ws3_asymmetry_oos_2026_07.json           # 機械判定の数値根拠
related:
  - knowledge-base/wiki/syntheses/roadmap-v2.3-payoff-friction-repair.md
---

# 要求仕様 (stage-1 §8.3 の固定分岐の執行)

1. **対象は PASS 2 セルのみ** — london_fix_reversal×EUR_USD (h24, OOS ratio 1.43) / htf_false_breakout×AUD_JPY (h24, 1.82)。fail 6 セル (trendline_sweep×EUR_USD 含む) の追加・入れ替え禁止
2. **barrier/EV 設計**: MFE/MAE 分布 (探索 + OOS 両標本) から TP/SL barrier 候補を設計、摩擦控除後 EV をエンドポイント化。pre-reg の binding gate は機構の作用方向と同軸の指標を選ぶ (lesson 準拠)
3. **TV Pine canon 再現**: Python BT エントリー母集団の TV 再現を必須ゲートに組み込む (MEMORY `feedback_tv_edge_discovery_loop` — Live > TV > Python BT)
4. **成果物 = DRAFT pre-reg 文書** (decisions/)。**LOCK・実走は user 最終承認後** — 承認前のスキャン実行禁止 (結果を見た後の設計変更を構造的に排除するため)
5. london-fix-reversal の戦略カード整合 (index の Edge Stage 不整合 warn: PAIR_DEMOTED×USD_JPY vs pipeline=PROMOTED) を起案時に棚卸し
