---
id: 20260713-ws3-round3-crossasset-divergence
title: "[v2.3 WS3/供給ライン] 探索3周目 — cross-asset divergence-reversion (外部仮説, 純研究)"
owner: claude
status: done
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


---

## VERDICT (2026-07-14, autopilot — 期日 07-24 の 10 日前倒し)

❌ **PASS=0 / H0 採択.** 全 5 手続き完遂:
1. **データ準備**: intraday rates の全ソース実測フロア (yfinance 1h=2024-02-18 / Massive futures aggs=2024-07 / equities aggs=2024-mid) が pre-reg §2a の 2021-01-01 前提を falsify。日次のみ 2021+ だが intraday reversion 仮説は日次で検定不能 → 結果観測前に窓を data-driven 再指定 (§2b AMENDMENT、look-ahead なし)。`data/cache/yield/ZN_F_1h.parquet` (N=12,760)。
2. **discovery** (2024-02-18〜2025-06-30): 216 cells → 選抜 47 → top-8 凍結。
3. **候補固定**: §2b-FROZEN に凍結 + self-LOCK + registry deadline 確定。
4. **OOS** (2025-07-01〜2026-05-15): 8/8 反転 (leg A BH-FDR 0/8、leg B EV 0/8)。探索の正 EV は選択バイアス + carry-unwind regime artifact。
5. **分岐**: §4 固定どおり cross-asset 価格モダリティ枯渇 → **E1 positioning 格上げ** (user 決定)。post-hoc の EUR ペア残余は claimable 不可 → 条件付き round-4 トリガ登録。

詳細: [[ws3-round3-crossasset-divergence-prereg-2026-07-13]] §8 / 教訓: [[lesson-freeze-rule-topEV-selects-overfit-2026-07-14]]

## Claude Review

**レビュー実施**: 2026-07-14 (autopilot、Claude 直接実行 = 実行者と同一だが敵対的自己検証を明記)。

- **手続きの pre-reg 忠実性**: 窓再指定は discovery 実行前・結果観測前に確定 (§2b AMENDMENT) → look-ahead bias なし。判定 2 レグ・閾値・ナイフエッジ3点は pre-reg 不変。✅
- **凍結の監査可能性**: `ws3_round3_frozen_candidates.json` を discovery 出力で決定論的に生成 (top-8 by EV rule はコードに事前記述) → OOS 前 LOCK が auditable。✅
- **独立再計算**: best-per-pair robustness を harness 関数の外側から再ロードして OOS 符号を独立検証 (GBP_JPY 撃沈 / EUR ペア post-hoc 生存) → 主結論 (frozen 8/8 反転) と整合。✅
- **弱点の明示**: (a) OOS ~10.5mo は短く、power は限定的 (ただし N≥30 は全 frozen cell で充足、UNDERPOWERED ではなく明確な符号反転)。(b) leg B の 3×3 近傍評価を best-cell 基準で代替 (全 cell 負のため結論不変)。(c) 凍結規則の欠陥 (top-by-EV) を lesson 化し、EUR ペアの post-hoc 生存を claimable 不可として厳格に扱った。
- **結論の妥当性**: PASS=0 は frozen set に対して頑健。§4 固定分岐 (E1 格上げ) は price-modality 3周 FAIL の一貫した帰結。live/shadow 不変更、read-only。✅

**判定**: 実装・統計・KB 反映は pre-reg と整合。マージ可。
