---
id: 20260504-1410-tier1-shadow-tracking-forensic-relaxation
title: "Tier 1 shadow_tracking gate forensic + 3 pre-registered relaxation variants + Codex adversarial review (R3)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-04T14:10:00+0900
roadmap_gate: "Gate 1 (Kelly Half) への直接道 — Tier 1 LIVE pass-through を 0.5% から ≥10% に回復し alpha 多様化を Live で実現する"
rule: R3
prereq_artifacts:
  - knowledge-base/wiki/decisions/tier1-routing-rca-2026-05-04.md  # Tier1 RCA verdict + shadow_tracking 96.10% block
  - tools/tier1_routing_rca.py  # 既存 RCA query 実装
  - .ai/runs/20260504-tier1-routing-rca/final.md  # production audit 結果
related:
  - .ai/tasks/done/20260504-0215-tier1-routing-anomaly-rca-rerun.md  # 親 task (本タスクの根拠)
  - knowledge-base/wiki/lessons/feedback_live_shadow_separation.md  # is_shadow=0 分離必須
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md  # 部分検定の罠
---

# 0. なぜこのタスクか

Tier1 RCA (parent task) で以下が確定:

- shadow_tracking が **shadow/reference 側で 74/77 block (96.10%)** = 圧倒的支配
- LIVE-only gate (spread/SL/phase/MC ruin) blocks: **0 件**
- sent → filled 経路は **15/15 = 100% pass-through** (届けば OANDA 100% 受理)
- audit route-through: **15/92 = 16.30%** (= 92 個のうち 77 個が shadow 側に diverted)

つまり Tier1 LIVE EV -4〜-5 vs BT EV +0.6〜+1.0 乖離の真因は **friction や spread ではなく routing layer の shadow_tracking gate**。これを relaxation できれば Tier1 ELITE_LIVE の Live 占有率が大幅増加し、Gate 1 (Kelly Half) 方向に直接前進する。

ただし shadow_tracking がそもそも **何を** 防いでいるのか不明。安全に緩めるには:
1. Source code level でゲートのロジックを特定
2. Production audit で実際にどの条件が firing しているか確認
3. counterfactual で「緩めた場合」の Tier1 改善 vs 他 strategy 副作用を計測
4. Pre-registered LOCK 緩和案 3 つを A/B 比較
5. Codex adversarial self-review で safety check

実装変更は **本タスクで行わない** (forensic + recommendation のみ)。緩和の実装は別タスクで pre-reg LOCK の上で行う。

# 1. 仮説

**H0**: shadow_tracking は legitimate な dedup/coordination 機能で、緩和すると double-execution / data integrity violation が発生する。Tier1 LIVE 0.5% pass-through は仕様上の正しい動作。**緩和不可**。

**H1 (本タスク主仮説)**: shadow_tracking の特定 sub-condition が overly conservative で、Tier1 ELITE_LIVE を不必要に block している。当該 sub-condition のみ ELITE_LIVE bypass / 条件緩和で Tier1 pass-through を ≥10% に改善でき、他 strategy への regression は ≤ 5%。

**H2**: Sub-condition は legitimate だが、Tier1 ELITE_LIVE の demote/promote 履歴 cache が stale で誤 block。cache refresh だけで解決。

**H3 (反証)**: いかなる緩和案でも data integrity リスクが致命的で、別アプローチ (例: ELITE_LIVE 専用 routing pipeline) が必要。

これら 4 仮説を **Phase A-E の forensic + counterfactual + adversarial review** で切り分ける。

# 2. Phase A — Source code forensic (実行必須)

1. `grep -rn "shadow_tracking" --include="*.py"` で全出現箇所特定 (modules/, app.py, tools/, strategies/)
2. shadow_tracking gate 定義箇所を読み、以下を抽出:
   - ゲートが受け取る入力 (signal context, trade state, etc.)
   - ゲートが check する sub-conditions の列挙
   - 各 sub-condition の return value (block / pass / skip)
   - block 時の log message format
3. forensic-report.md に以下を出力:
   - Sub-conditions 列挙 (順番、論理結合 AND/OR、early return の有無)
   - 各 sub-condition の意図 (コメント or 文脈から推定)
   - shadow_tracking が何を防ごうとしているか (= 緩和した場合のリスク仮説)

# 3. Phase B — Production audit drill-down (実行必須)

`tools/tier1_routing_rca.py` を拡張 or 新 script で以下を query:

1. **Sub-condition firing breakdown**: shadow_tracking 74 blocks のうち、どの sub-condition が firing したか。block reason の log message から regex 抽出。
2. **Per-cell × per-sub-condition matrix**: Tier1 5 cells × 各 sub-condition の block counts
3. **Pre-cutoff (2026-04-08 以前) vs post-cutoff comparison**: gate 挙動が gate chain v9.3 投入で変わったか
4. **Non-Tier1 cells の影響**: xs_momentum / doji_breakout / squeeze_release_momentum 等 (RCA decision doc で観測された他 cell) の shadow_tracking firing 比率
5. **Time clustering**: 同一 timestamp/bar に複数 signals が来た場合の shadow_tracking 動作 (= dedup 役割の検証)

forensic-report.md に sub-condition firing table を追記。

# 4. Phase C — Counterfactual analysis (実行必須)

各 sub-condition について:
1. **Tier1 ELITE_LIVE 5 cells 対象に counterfactual route-through**: もしこの sub-condition が常に pass を返したら、route-through 率は何%になるか
2. **他 strategies regression**: 同じ relaxation を適用した場合、Tier 2/3 strategies で問題ある routing が発生するか (= unintended pass-through count)
3. **Data integrity check**: relaxation で同一 demo_trade_id の重複 OANDA 約定 / shadow 集計 ミス / parent-child 結合不整合 が発生する経路があるか

# 5. Phase D — 3 Pre-registered Relaxation Variants (LOCK)

Phase C 結果に **依存させない** (cherry-pick 防止)。以下 3 variants を **本ファイル時点で pre-register**:

## V1 — Top sub-condition single removal
- Phase B で identified された **block 寄与最大の sub-condition** を block 判定から除外
- 他 sub-conditions は不変
- Tier1 ELITE_LIVE のみでなく **全 strategy** に適用 (= broad relaxation)

## V2 — Top sub-condition + ELITE_LIVE bypass
- V1 と同じ top sub-condition 緩和
- 加えて、`tier_master.py` で `ELITE_LIVE` 認定された entry_type × pair × mode 組み合わせは shadow_tracking 全体を bypass
- Tier 2/3 への副作用を ELITE_LIVE 限定で回避

## V3 — ELITE_LIVE only bypass (no sub-condition change)
- shadow_tracking の sub-condition は**一切変更せず**
- ELITE_LIVE 認定 cell のみ shadow_tracking gate を完全 bypass
- Tier 2/3 はそのまま

各 variant について:
- Tier1 5 cells の route-through 率 expected
- Tier 2/3 strategies の route-through 変化 (regression risk)
- データ整合性影響の有無

# 6. Phase E — Codex Adversarial Self-Review (LOCK)

3 variants の counterfactual 完了後、以下 7 軸を Codex 自身が check し `adversarial-review.md` に出力:

1. **Pre-registration violation**: Phase D の 3 variants 仕様を後付け修正していないか
2. **Cherry-pick 検出**: Phase C 結果を見て variants 仕様を変えていないか
3. **Data leak**: Live trade pnl と shadow trade pnl を集計時に混同していないか (`feedback_live_shadow_separation` lesson 厳守)
4. **Cohort-time bias**: Pre/post cutoff の境界が arbitrary でないか
5. **Survivorship bias**: 既に Demote されたが過去には ACTIVE だった cell を集計から除外していないか
6. **Production safety**: relaxation を実装した場合に発生しうる **double-execution** scenarios の列挙
7. **Statistical multiplicity**: 3 variants × 5 cells = 15 検定で Bonferroni m=15 を適用しているか (もし統計検定が含まれる場合)

violation 1 つでも → verdict 強制 NEEDS_MORE_EVIDENCE で実装提案を保留。

# 7. 採用 / 保留 / 棄却基準 (per variant)

| 条件 | ACCEPT | NEEDS_MORE_EVIDENCE | REJECT |
|---|---|---|---|
| Tier1 ELITE_LIVE 5 cells 平均 route-through | ≥ 50% | 20-49% | < 20% |
| Tier 2/3 regression (route-through 増加で false-positive 化する trades) | ≤ 5% | 5-10% | > 10% |
| Double-execution risk (counterfactual で発見) | 0 件 | (該当なし) | ≥ 1 件 |
| Data integrity violation (parent-child mismatch / pnl 二重計上 / cell 帰属混乱) | 0 件 | (該当なし) | ≥ 1 件 |
| Adversarial review 7-axis | 7/7 pass | 5-6/7 pass | ≤ 4/7 pass |

全 ACCEPT で **per-variant ACCEPT (= 別タスクで実装提案 GO)**。
Risk 軸 (Double-execution / Data integrity / Adversarial) のいずれかが REJECT で **per-variant REJECT (実装禁止)**。

# 8. Overall verdict (3 variants aggregate)

- **3/3 ACCEPT**: 最も保守的な V3 から実装する別タスクを起こす
- **1-2/3 ACCEPT**: ACCEPT した最保守 variant から実装
- **0/3 ACCEPT**: H0 / H3 が支持 — shadow_tracking 緩和は Tier1 LIVE 救済の道ではない、別アプローチ (例: dedicated Tier1 routing layer 設計) を Wave 4-5 で検討

# 9. データ分離 (重要、`feedback_live_shadow_separation` 厳守)

- 入力: Production OANDA audit DB (Render fx-ai-trader main `/var/data/oanda_audit.db` または同等)
  - **read-only access only** — 一切の UPDATE/INSERT/DELETE 禁止
- `is_live=true` の sent/blocked = Live bucket
- `is_live=false` の skipped = Shadow/reference bucket
- 集計時に **必ず separate** (混入は forbidden)
- bridge_status='sent' = strategy 名 / bridge_status='filled' = OANDA mode 名 として GROUP BY 前に分離 (`reference_oanda_audit_twin_meaning` lesson)
- 出力: `.ai/runs/<run_id>/forensic-report.md` + `adversarial-review.md` + counterfactual table

# 10. 検証コマンド (Codex 必須実行)

```bash
cd /data/repo/fx-ai-trader

# Phase A: source code grep
grep -rn "shadow_tracking" --include="*.py" modules/ app.py tools/ strategies/ 2>&1 | head -20

# Phase B-C: 既存 RCA tool を流用 + sub-condition breakdown 追加
#   tools/tier1_shadow_tracking_breakdown.py (新規) を実装
python3 tools/tier1_shadow_tracking_breakdown.py \
  --audit /tmp/oanda-audit-tier1-rca.json \
  --output .ai/runs/<run_id>/sub-condition-breakdown.json

# Phase D: counterfactual BT (3 variants)
python3 tools/tier1_shadow_tracking_counterfactual.py \
  --audit /tmp/oanda-audit-tier1-rca.json \
  --variants V1,V2,V3 \
  --output .ai/runs/<run_id>/counterfactual.json

# Phase E: adversarial self-review (Codex 自身の生成)
# → adversarial-review.md に 7 軸 check 結果を書く
```

# 11. 出力すべきレポート (codex `--output-last-message`)

1. **shadow_tracking sub-conditions 列挙** (Phase A 結果)
2. **Sub-condition firing breakdown table** (Phase B 結果, top conditions sorted by N)
3. **Counterfactual table per variant × per cell** (Phase C 結果)
4. **Pre-registered V1/V2/V3 verdict** (per-variant ACCEPT/NEEDS_MORE_EVIDENCE/REJECT)
5. **Adversarial review 7-axis pass/fail summary**
6. **Overall verdict**: 3/3 / 2-3/3 / 1/3 / 0/3 ACCEPT
7. **Recommended next task**:
   - ACCEPT path: 「最保守 variant の実装提案 task をこの spec で書け」
   - REJECT path: 「shadow_tracking 緩和は Tier1 救済の道でない、Wave 4-5 で別 routing layer 設計」

# 12. 禁止事項

- ❌ `.env`, OANDA / OPENAI / Render API key を読む / 書く / log に出す
- ❌ `modules/`, `app.py`, `strategies/` を **編集** (本タスクは forensic only)
- ❌ 本番 DB (`/var/data/*.db`) への **書き込み**
- ❌ ローカル DB (`demo.db` 等) への書き込み
- ❌ Pre-registration LOCK 違反: Phase D の 3 variants 仕様を Phase B/C 結果に応じて変える (cherry-pick disguise)
- ❌ Phase D に 4 つ目以降の variant 追加 (post-hoc selection 罠)
- ❌ V1/V2/V3 の境界条件 (top sub-condition の決定基準、ELITE_LIVE 認定基準) の post-hoc 調整
- ❌ Acceptance criteria 境界値 (route-through 50%, regression 5%, double-execution 0) の post-hoc 調整
- ❌ Live bucket と Shadow bucket の混在集計 (`feedback_live_shadow_separation` 違反)
- ❌ `git push --force` / `git rebase --onto` history rewrite

# 13. Rule R3 verification

- 構造的 BT-Live divergence の真因解明と緩和案検定 = R3 (構造バグ forensic)
- 365日 BT スキップ可 (本タスクは BT でなく audit forensic + counterfactual)
- pre-registration LOCK: §5 (3 variants) + §7 (verdict matrix) + §6 (adversarial 7-axis) 全て LOCK
- post-hoc に上記 LOCK を変更した場合、verdict 強制 INVALID で全 variants NEEDS_MORE_EVIDENCE 扱い

# 14. 期待される所要時間

- Phase A (source grep + 解読): ~5 min
- Phase B (sub-condition breakdown query): ~5-10 min
- Phase C (counterfactual): ~5-10 min
- Phase D (3 variants 集計): ~5 min
- Phase E (adversarial review): ~5 min
- 合計: **25-40 min**

# 15. 月利 100% ロードマップへの寄与

W1P3 で chart pattern family が真死した代わりに、**Tier1 LIVE 蘇生**が Gate 1 (Kelly Half) 進捗の最有力候補となった。

- Tier1 ELITE_LIVE 5 cells は BT EV +0.6 ~ +1.0 → Live で本来 +0.6 ~ +1.0 のはず
- 現状 0.5% pass-through で Live 損失 EV -4 ~ -5 に見えていたが、これは**サンプル不足の見かけの損失**
- shadow_tracking 緩和で route-through が 50%+ に増えれば Tier1 LIVE が **本来の** EV 領域に収束 (predicted by RCA)
- Gate 1 alpha source 多様化を **新規 family 開発でなく既存 strategies の Live 流路修正**で達成できる可能性

これが ACCEPT すれば月利 100% への最短経路。REJECT なら別アプローチ (Wave 4-5 で dedicated Tier1 routing pipeline 設計) を検討。

# 16. 参考: Tier1 RCA → 本タスクの引き継ぎ

Tier1 RCA (`.ai/tasks/done/20260504-0215-tier1-routing-anomaly-rca-rerun.md`) で確定:
- shadow_tracking が 74/77 block (96.10%) で支配
- LIVE-only gate blocks 0
- 15 sent / 15 filled = 100% (届けば OANDA 受理)
- audit route-through 15/92 = 16.30%

本タスクは shadow_tracking の **内部** に踏み込み、緩和可能な sub-condition を identify + 安全に緩める設計を pre-reg LOCK で検証する。実装変更は別タスク。
