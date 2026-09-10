---
title: 静的 hour block class exemption — min-lot carve-out 契約群 (rule:R1)
date: 2026-09-02
type: decision
status: 🔒 LOCKED (user 承認 2026-09-02、同日実装)
related: [[../analyses/hourblock-recal-and-ema200-verdict-2026-09-02]], [[alpha-scan-static-block-recalibration-prereg-2026-09-02]], [[kalman-d7-minlot-carveout-prereg-2026-09-01]], [[prereg-trigger-registry]]
---

# 静的 hour block class exemption (rule:R1、2026-09-02)

## 決裁記録

- **提示**: 2026-09-02 セッションで Claude が「class exemption R1 (live 資格セルの静的 hour block 免除、+3 イベント/月) — 昨日の verdict で推奨済み、パケット化して出せます」と提示 (根拠・期待効果を明示)
- **user 承認**: 2026-09-02「どちらも進めて」— 前例 = sweep gbp_asia 免除 (user 承認 2026-08-03「進めて」) と同形式
- **推奨元**: [[../analyses/hourblock-recal-and-ema200-verdict-2026-09-02]] Study 1 推奨経路「個別撤去ではなく live 資格セルの class exemption 1 本の R1」

## 内容

**min-lot carve-out 契約群** (`_STATIC_HOURBLOCK_CLASS_EXEMPT` = `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` と同一実体、12 戦略: carry_dip / kalman_d7×3 / wg / ps×5 / sweep_late / vix_carry_unwind) について、以下 **6 つの静的 hour/session block の live 抑止を免除**する:

| block | gate | 一般母集団への扱い |
|---|---|---|
| EUR_USD Tokyo (H0-6) | session_pair | **維持** |
| EUR_USD Late NY (H17+) | session_pair | **維持** |
| H7-8 × EUR_USD | alpha_scan | **維持** |
| H11 × EUR_USD | alpha_scan | **維持** |
| H13 × USD_JPY | alpha_scan | **維持** |
| H16-20 × USD_JPY | alpha_scan | **維持** |

- **免除は demoted tier (静的 + runtime) を除外** (fail-closed)。demoted なメンバー (現時点で vix_carry_unwind) は免除されない
- 免除発火時は `[HOURBLOCK_CLASS_EXEMPT]` marker を reasons に永続 (読み手 = rollback registry、下記)
- **regime/方向系 block (EUR_USD SELL / RANGE SELL / TREND_BULL BUY / BUY TREND_BEAR) はスコープ外・不変更**
- Shadow 蓄積への影響: 免除された event は shadow 行ではなく live 行として記録される (データは失われない、原則 3 と整合)

## 根拠 (これは edge claim ではない)

1. **相対毒性の不在 (parity)**: 2026-09-02 再較正 (N=73〜352/block、独立窓 04-14〜06-02 でも複製) で「block 帯が非 block 帯より悪い」は名目有意ですら 0/6。較正時毒性 (WR 9.5〜28.6%) は全 block で再現しない
2. **per-cell リスクの有界性**: class 全員が 1000u 固定契約 (`_AGG_KELLY_GATE_MINLOT_MAX_UNITS`) + 各自の binding R2 registry (t9-kalman / carry-dip-v3-revival-watch / wg G1/G2 / ps LOCK watchdog) を持つ — hour-of-day は追加の防御情報を持たない
3. **期待効果**: +3 イベント/月 (Study 1 layer_c: carry_dip の in-window 3 イベント/月が主)。小さいが、live N 蓄積が全 registry の律速である現状 (直近 30d live 13 件) では衛生価値が高い

**先取りしないこと**: PR #219 (alpha_scan recal) の「B7/B8 live 層 gross EV 正 (+1.27/+1.09)」は N=17/26<30 の post-hoc 観察であり、本免除の根拠に**使っていない**。その edge claim の裁定は registry `alpha-scan-b7-b8-livecell-recheck` (期日 2026-11-30、N≥30 + 新 pre-reg) に凍結されたまま。本免除は「勝てるから開ける」ではなく「防御情報ゼロ + リスク有界だから開ける」

## Binding gates (R2 rollback)

- **registry `hourblock-class-exempt-r2-rollback`** (機械評価、live_count_decision + reasons_marker):
  - 母集団 = `[HOURBLOCK_CLASS_EXEMPT]` marker 付き clean live (oanda_trade_id 非空 ∧ dedup_violation≠1) — **免除で通過した行のみ** (block 帯外のトレードは混入しない)
  - **N≥10 到達 → pooled EV 判定: EV<0 なら免除撤去 (R2、即断可)**
  - 連続 3 SL → 期日前でも即 user review
  - 期日 2026-12-01 に N<10 → stale review (免除の実効性 = live 到達性を再監査)
- 第 2 層: per-cell binding registry (既存) が個別セルの退避を担う

## 実装 (同日、同 PR)

- `modules/demo_trader.py`: `_STATIC_HOURBLOCK_CLASS_EXEMPT` (alias、identity を test pin) + 6 gate に `_hourblock_class_exempt` 分岐 + `_hourblock_exempt_pass()` (marker 永続 + ログ)
- `tools/prereg_trigger_watch.py`: `live_count_decision` に `reasons_marker` フィルタ拡張 (estimand 忠実の計数)
- counterfactual テスト: class 非メンバーは従来どおり block/shadow、demoted メンバーは免除無効、marker は免除発火時のみ付与 — `tests/test_hourblock_class_exemption.py`

## 撤去条件 (pre-commit)

以下のいずれかで免除を撤去する (R2、user 追認事後で可):
1. rollback registry の EV<0 判定成立
2. class メンバーの連続 3 SL が exempted window に集中
3. per-cell binding registry のいずれかが exempted window 起因で発火

再導入は改めて R1。
