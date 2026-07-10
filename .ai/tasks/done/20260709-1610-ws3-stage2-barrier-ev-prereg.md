---
id: 20260709-1610-ws3-stage2-barrier-ev-prereg
title: "[v2.3 WS3/R1 stage-2] barrier/EV 設計 pre-reg 起案 — PASS 2 セル限定 (london_fix_reversal×EUR_USD / htf_false_breakout×AUD_JPY)"
owner: claude
status: done
priority: P1
created_at: 2026-07-09T16:10:00+0900
roadmap_gate: "v2.3 WS3 stage-2。stage-1 OOS verdict PASS (PR #69) の §4 固定分岐。起案は DRAFT — LOCK は user 最終承認後。live 変更なし"
rule: R1
executor_note: "claude 直接実行 (zen-mahavira) — LOCK 2026-07-09 user 承認 → verdict 2026-07-10 完了"
completed_at: 2026-07-10T14:30:00+0900
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

## 実行結果

- LOCK (2026-07-09 user 承認「進めて」、PR #73) → verdict 2026-07-10 (期日 9 日前倒し)
- OOS-2 (2022-07-07〜2024-07-06): AUD_JPY 15m を Massive 遡及取得 (重複区間 byte 一致)、切詰め worktree。§3 執行順序遵守 (抽出 → N 凍結 59/46 → sim)
- **verdict: PASS ゼロ / 全体 UNDERPOWERED** — lfr×EUR_USD 全 9 構成負 (クローズ) / htf_fb×AUD_JPY 1 構成 +1.15・p_cell 0.594 (shadow N≥100 再判定枠)。詳細 = pre-reg §8

## Claude Review

**Verdict: PASS (執行手続きの検収)** — 2026-07-10、zen-mahavira

- **pre-reg 準拠**: grid/窓/セル/検定は LOCK 版から変更ゼロ。§3 執行順序 (抽出→N凍結→sim) をツールの 2 モード分離で構造的に強制。§4 3 分岐を機械適用 (REJECT 条件不成立を確認の上 UNDERPOWERED 採択)
- **出力検証**: 独立実装で 2 構成 (lfr tp18_sl10 / htf_fb tp36_sl30) を再計算し sim と完全一致 (−6.510 / +1.151)。ep はシグナルバー close 乖離 p50 0.6-0.7p = spread 込み fill として妥当
- **git diff verify**: 対象 = 判定器 tools/ws3_stage2_barrier_sim.py (新規) + raw 成果物 3 点 + pre-reg §8 + registry 入替 + roadmap/changelog/session log。live コード変更ゼロ
- **ナイフエッジ記録**: fold 集中 [+10.8/+2.9/−10.9]・孤立格子点 0/2・LOFO −4.0 を §8.3 に明記 — 再判定時の判断材料として保全
