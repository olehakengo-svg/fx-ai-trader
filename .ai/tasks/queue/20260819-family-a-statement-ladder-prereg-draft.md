---
id: 20260819-family-a-statement-ladder-prereg-draft
title: "[供給ライン] family A statement_ladder — explore pre-reg 起草 (DRAFT、09-18 統合裁定の前提材料)"
owner: claude (session magical-cori-706d69)
status: done
claimed_at: 2026-08-19T07:35:00+0000
completed_at: 2026-08-19T07:50:00+0000
priority: P2
roadmap_gate: "トラックB 供給ライン。registry `statement-ladder-foundation-readiness` resolve (PR #195、基盤 = PR #194 main 着地) による起草ゲート解除 + user「進めて」(2026-08-19)。裁定 (台帳採否・explore 枠付与) は 09-18 edge-supply-scan-monthly の A/B/C 統合裁定"
rule: R3 (起草のみ。発言×介入ラベルのジョイント量は一切計算しない — 測定は 裁定→敵対的検証→凍結 の後)
executor_note: "排他 claim = 本 ticket + PR。起草根拠 = intervention-history-anatomy dossier (family A の仕事 = 発言ラダー先行条件の false positive 率測定) + mof-communication-data-infrastructure (基盤・境界) + #4 verdict PARTIAL (E-C 符号逆 prior は family B へ隔離)。lexicon v1 語彙が 2022/2024 目視検証を経ている in-sample 汚染チャネルを peek 会計で正直に固定すること"
prereq_artifacts:
  - knowledge-base/wiki/analyses/mof-communication-data-infrastructure.md
  - knowledge-base/raw/analysis/intervention-history-anatomy-2026-08-18.md
  - knowledge-base/wiki/decisions/mof-intervention-forward-prereg-2026-07-24.md
  - data/external/mof_statements/lexicon_scores.csv
  - data/external/mof_statements/interventions_daily.csv
---

# 要求仕様

1. **explore pre-reg DRAFT** を `knowledge-base/wiki/decisions/family-a-statement-ladder-prereg-2026-08-19.md` に起草 (Status = DRAFT、LOCK しない):
   estimand (検出器較正、価格全面不使用) / 凍結手続き / episode-block null / peek 会計 / 記述級拘束 (有効 N=4 blocks) / forward OOS 設計 / verdict 固定分岐 / 台帳 #26 登録案。
2. **測定禁止の維持**: 本 ticket の成果物に発言×介入のジョイント統計を含めない。
3. 裁定材料として 09-18 スキャン entry から参照可能にする (changelog + KB リンク)。
