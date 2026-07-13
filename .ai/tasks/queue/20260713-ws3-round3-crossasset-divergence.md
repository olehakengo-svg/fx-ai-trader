---
id: 20260713-ws3-round3-crossasset-divergence
title: "[v2.3 WS3/供給ライン] 探索3周目 — cross-asset divergence-reversion (外部仮説, 純研究)"
owner: claude
status: queued
priority: P2
created_at: 2026-07-13T19:40:00+0900
roadmap_gate: "トラックB 供給ライン (decision memo 2026-07-10)。内部 2 周 FAIL → 外部仮説転進の第1候補。live/shadow 変更なし"
rule: R1
executor_note: "claude 直接実行可 (autopilot 自走)。データ到達済 (Massive FX cache) + net 到達可 (ZN=F/yfinance)。stage-2/round-2 成果物には接触しない"
prereq_artifacts:
  - knowledge-base/wiki/decisions/ws3-round3-crossasset-divergence-prereg-2026-07-13.md  # DESIGN self-LOCK 済、候補は discovery 後に凍結
  - knowledge-base/wiki/research/external-hypothesis-scan-2026-07-13.md                  # 起案根拠 + lead-lag 閉鎖の実証
  - tools/ws3_leadlag_ic_explore.py                                                       # 流用可 (IC/adversarial check ハーネス)
related:
  - knowledge-base/wiki/decisions/ws3-round2-explore-prereg-2026-07-10.md
---

# 要求仕様 (pre-reg §2 の手続き実行)

1. **データ準備**: ZN=F を 15m/1h で 2021-01-01〜 まで拡張取得 → `data/cache/yield/`、tz を UTC 整合。
2. **discovery diagnostic (2021-01-01〜2024-06-30)**: rolling-β rate-implied residual z-score の乖離定義 (窓×z閾 grid) × JPY 感応ペア × horizon で first-touch 摩擦調整 EV / reversion IC を計測。`tools/ws3_crossasset_divergence_explore.py` を新設 (ws3_leadlag_ic_explore.py の IC/adversarial ハーネス流用)。
3. **候補固定**: 選抜規則 (探索窓 EV>0 ∧ IC 符号機構整合、N≥30, m≤8) → pre-reg §2b に凍結・self-LOCK (🔒) + registry deadline 確定。
4. **OOS verdict (2024-07-01〜2026-05-15)**: 2 レグ (BH-FDR IC + first-touch EV) + ナイフエッジ3点。verdict を pre-reg §8 へ。
5. 分岐: PASS≥1 → D4 準拠の実装 pre-reg 起案 (user LOCK) / PASS=0 → E1 positioning infra 決定を主戦線へ格上げ。
