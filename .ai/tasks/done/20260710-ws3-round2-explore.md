---
id: 20260710-ws3-round2-explore
title: "[v2.3 WS3/供給ライン] 探索2周目 — 方向分割×未走査ペア×h96 の新軸探索 (純研究)"
owner: claude
status: done  # OOS verdict ❌ FAIL 0/5 (2026-07-10、期日 7 日前倒し) — 外部仮説探索へ転進 (pre-reg §8)
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

## Claude Review

- **執行検証**: OOS 窓 2024-07-07〜2025-07-07 (再利用 2 回目) は切詰め parquet (末尾 2025-07-07T23:45Z、`tools/ws3_round2_oos_prep.py`) で look-ahead 遮断を確認。GBP_JPY 15m は Massive 遡及取得で完全窓。エントリー抽出 → N 凍結 (`ws3_round2_oos_entries.json`) → 判定の順序執行 (stage-2 §3 準拠)。判定器 `tools/ws3_round2_oos_verdict.py` は pre-reg §3 をそのまま実装 (レグA = round-1 判定器 import 流用 B=10,000 seed 固定 BH-FDR m=5 / レグB = §2b 凍結 grid first-touch 再アンカーなし / LOFO gate)。ep 復元不一致 0/428
- **verdict: ❌ FAIL 0/5** — 3 セル ratio 崩壊 (0.56-0.90)、vol_spike×USD_JPY は N=27<30 機械 FAIL、sr_fib×GBP_USD は EV 孤立格子点 + fold 集中 (LOFO −10.8)、最接近 sr_fib×EUR_USD も FDR (p=0.194) + 隣接過半で不通過。探索窓 EV スクリーン通過 5 セル中 4 セルが OOS 崩壊 = 探索窓 EV は選択バイアスの別表現と実証
- **規律**: 結果を見た後の設計変更・grid 調整・再選抜なし。turtle_soup 裁定は §8.3 に明記 (OOS 不進出)。§3 固定分岐に従い shadow 母集団内の軸は枯渇と判定 → 外部仮説 (学術/TV 由来、falsified 6 系統除外) の探索へ転進。詳細 = pre-reg §8
