---
id: 20260504-1455-tier1-shadow-tracking-v1-narrow-implementation-proposal
title: "Tier 1 LIVE shadow_tracking V1 narrow implementation proposal — daytrade_eur 真因究明 + drift row guard + tier-master refresh + 実装 PR 草案 (R1)"
owner: codex
status: queued
priority: P0
created_at: 2026-05-04T14:55:00+0900
roadmap_gate: "Gate 1 (Kelly Half) 直接路 — Tier1 LIVE route-through 0.5% → 50% で alpha source 多様化を Live で実現"
rule: R1
prereq_artifacts:
  - modules/demo_trader.py  # post_gate_mode_blocked logic (line 4847-4933) の修正対象
  - knowledge-base/wiki/tier-master.json  # stale ELITE_LIVE 認定の refresh 対象
  - knowledge-base/wiki/tier-master.md
  - .ai/runs/20260504-0527-tier1-shadow-tracking-forensic/forensic-report.md
  - .ai/runs/20260504-0527-tier1-shadow-tracking-forensic/adversarial-review.md
  - .ai/runs/20260504-0527-tier1-shadow-tracking-forensic/sub-condition-breakdown.json
  - .ai/runs/20260504-0527-tier1-shadow-tracking-forensic/counterfactual.json
related:
  - .ai/tasks/done/20260504-1410-tier1-shadow-tracking-forensic-relaxation.md  # forensic で V1 ACCEPT 確定
  - .ai/tasks/done/20260504-0215-tier1-routing-anomaly-rca-rerun.md  # routing 0.5% pass-through の発見
  - .ai/tasks/queue/20260504-1450-shadow-tracking-audit-label-fidelity-fix.md  # 並列 R3 (audit fidelity) — 別 task
  - knowledge-base/wiki/lessons/feedback_live_shadow_separation.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

forensic (`20260504-1410-tier1-shadow-tracking-forensic-relaxation`) で V1 = ACCEPT 確定:

- **V1**: `post_gate_mode_blocked:daytrade_eur` の relaxation で Tier1 route-through **0.5% → 50%** (counterfactual)
- Tier 2/3 regression **2.3%** (≤ 5% threshold)
- double-execution 0、data integrity violation 0
- Adversarial 7/7 全 PASS

ただし Codex 自身が **broad relaxation を直接実装することを禁忌**として勧告:

> "do not implement broad `daytrade_eur` mode shield removal directly. The proposal should specifically reconcile why `trendline_sweep / EUR_USD`, `session_time_bias / EUR_USD`, and `xs_momentum / EUR_USD` are being converted to `shadow_tracking` by `OANDA_MODE_BLOCKED`, and should include a guard that excludes any row/cell with existing audit/live drift from resend."

つまり:
1. `daytrade_eur` mode block の **真因が legitimate なら緩和不可**、まず根本原因を理解する必要
2. 既存 production の **drift row 1 件** (`trendline_sweep / GBP_USD demo_trade_id=8b943193-5d4`) を replay すると double-execution → 排除 guard 必須
3. **tier-master が stale** で `gbp_deep_pullback` / `session_time_bias` は既に demoted (current ELITE_LIVE は `trendline_sweep` のみ) → refresh 必要

本タスクは **実装 PR を直接 main に push しない**。実装 patch を **artifact として出力**し、user が review してから別 task で apply 判断する設計。Production safety 第一。

# 1. 仮説

**H0 (worst case)**: `daytrade_eur` mode block は legitimate な OANDA Japan の day-trade rule (例: EUR pair の day-trade が一時的に institutional risk で disabled) に基づいており、緩和すれば broker から rejection / regulatory 指摘で即停止になる。**緩和不可**、Wave 4-5 で別経路設計。

**H1 (本タスク主仮説)**: `daytrade_eur` mode block は **過去の risk 検出時の防御措置として導入され、その後解除されるべきだったが残存**している stale guard。当該 mode を該当 cell でのみ override すれば、Tier1 ELITE_LIVE × EUR cells で正常に Live routing 復活、broker 側で問題なし。

**H2 (代替)**: H1 部分支持だが、**ELITE_LIVE 認定の cell のみ** override すべきで、demoted/sentinel cells には適用してはならない (V3 が REJECT になった drift row の教訓)。tier-master refresh + ELITE_LIVE-only override が正解。

**H3 (反証)**: いかなる narrow override も double-execution / data integrity リスクが残り、安全な実装が不可能。Wave 4-5 で dedicated routing pipeline を新設するのが正解。

# 2. Phase 1 — `daytrade_eur` mode block 真因究明 (Source code archaeology)

Codex は以下を実行:

1. `modules/demo_trader.py` の post_gate mode/SHIELD/Kelly/MC escalation logic (`:4847-4933`) を読み、`daytrade_eur` mode block の判定ロジックを抽出
2. **どの env var / config / DB state が "daytrade_eur is blocked" を triggered したか**を特定
3. git log でその logic の変更履歴を辿り、**いつ / なぜ追加されたか**を確認 (commit message + 関連 PR/issue)
4. `knowledge-base/wiki/decisions/` 配下で関連 decision document を grep (`grep -rn "daytrade_eur" knowledge-base/`)
5. 出力: `phase1-daytrade-eur-rationale.md` に以下を記述
   - 当該 mode block の発動条件 (env / state)
   - 導入時期と背景 (commit history より)
   - 発動の risk model (何を防いでいるのか)
   - 現在も有効かどうかの判定 (legitimate / stale)

**ACCEPT 条件**: 真因が "stale guard" と判定できれば Phase 2 に進む。"legitimate / 現在も必要" なら H0 支持で本タスクは NEEDS_MORE_EVIDENCE で停止 (実装提案を出さない)。

# 3. Phase 2 — Drift row exclusion guard 設計 (Production safety)

forensic で発見された drift row:
- `demo_trade_id=8b943193-5d4`
- audit: `skipped/shadow_tracking`
- joined trade: `is_shadow=0` AND OANDA trade id 存在

これを replay すると **double-execution** (= 既に OANDA で約定している trade を再送)。

設計するガード (LOCK):

```python
def is_drift_row_for_replay(audit_row, trade_row) -> bool:
    """Return True if this row should be EXCLUDED from any replay/bypass logic.

    Drift = audit が shadow と記録しているが trade table では Live (is_shadow=0)
    かつ OANDA trade id が既に発行されている状態。これを replay すると double-exec。
    """
    if audit_row.get("status") not in ("skipped", "blocked"):
        return False  # 元から live、replay 対象でない
    if audit_row.get("block_reason") != "shadow_tracking":
        return False
    if trade_row is None:
        return False  # 結合できない、安全に skip
    if trade_row.get("is_shadow") == 0 and trade_row.get("oanda_trade_id"):
        return True  # DRIFT: skip replay
    return False
```

検証手順:
1. このガードを `tools/tier1_shadow_tracking_drift_guard.py` で実装
2. 既存 production audit + trade DB で全 drift row を enumerate (期待: 1+ 件、最低 `8b943193-5d4` を含む)
3. counterfactual: V1 適用時に drift row が replay されないことを確認

**ACCEPT 条件**: drift row 全件が guard で排除される + false-negative (本来 replay すべき non-drift row まで排除) 0 件。

# 4. Phase 3 — Tier-master refresh (stale ELITE_LIVE 認定更新)

forensic で判明:
> "Current tier-master ELITE_LIVE is only `trendline_sweep`; `gbp_deep_pullback` and `session_time_bias` are not current ELITE_LIVE"

Phase 3 で実行:
1. `knowledge-base/wiki/tier-master.json` を読み、現在の ELITE_LIVE / PAIR_PROMOTED / ELITE_PRIME 認定を列挙
2. `tools/sync_kb_index.py` / `tools/tier_integrity_check.py` を **dry-run** で実行 (production 書き込みなし)
3. tier_integrity_check で ERROR=0 を確認 (pre-reg LOCK)
4. 出力: `phase3-tier-master-snapshot.md` に現在の Tier1 ELITE_LIVE 認定 cell list を pin (V1 implementation の対象範囲を確定)

**ACCEPT 条件**: tier-master ERROR=0 + 現在の ELITE_LIVE Tier1 cells 確定 (snapshot で V1 適用範囲を LOCK)。

# 5. Phase 4 — V1 narrow implementation patch 草案 (LOCK)

**実装は本タスクで行わない (NO production code edit)**。patch を artifact として出力するのみ。

patch 仕様 (LOCK):
- 対象ファイル: `modules/demo_trader.py` の post_gate mode escalation logic 周辺 (`:4847-4933` 範囲)
- 変更内容:
  1. `daytrade_eur` mode block の判定ロジック直前に **conditional override** を挿入
  2. override 条件:
     - 対象 cell が tier-master JSON で **`ELITE_LIVE` 認定済**
     - かつ pair が EUR_USD (現在 forensic で判明している EUR cell に限定)
     - かつ `is_drift_row_for_replay()` が False (Phase 2 ガード)
  3. override 時の動作: `daytrade_eur` mode block を **skip** (= 元の `_is_promoted=True` を維持)
  4. **新規 audit reason**: override 発動時は audit log に `mode_block_overridden_for_elite_eur` を残す (transparency)
- 修正されない要素 (LOCK):
  - 他 11 sub-conditions (slot bypass / MTF downgrade / pair_demoted_safety_net 等) は **一切変更しない**
  - 他 mode block (`scalp_5m`, `daytrade_jpy` 等) も **一切変更しない**
  - shadow_tracking literal の audit log 表記は backward compat で残す (並列 R3 task で別途対応)
  - tier-master のデータ自体の編集はしない (Phase 3 は read-only verify のみ)

patch 出力先: `.ai/runs/<run_id>/v1-narrow-impl-patch.diff` (apply 可能な unified diff format)

# 6. Phase 5 — Codex Adversarial Self-Review (LOCK 8 軸)

Phase 1-4 完了後に self-review:

1. **Pre-registration violation**: 本ファイルの Phase 仕様 / patch 構造を後付けで変更していないか
2. **Cherry-pick 検出**: Phase 1 真因が "stale" だと早期判定して Phase 2-4 を強行していないか
3. **Live/Shadow data leak**: PnL aggregation で混入 0 件 (`feedback_live_shadow_separation`)
4. **Drift row exhaustiveness**: Phase 2 で drift row enumeration が完全網羅か (`8b943193-5d4` 以外にも存在するかも)
5. **Production safety scenarios**: V1 patch deploy 時に発生しうる double-execution / regression / OANDA rejection / tier-master state mismatch を全列挙
6. **Override scope creep**: V1 patch が `daytrade_eur` 以外の mode block にも漏れて影響していないか
7. **Tier-master integrity**: Phase 3 dry-run で ERROR が出た場合の影響評価が含まれるか
8. **Reversibility**: V1 patch を deploy 後に問題発覚 → revert する手順が明示されているか

violation 1 つでも → verdict 強制 NEEDS_MORE_EVIDENCE で patch 提案を保留。

# 7. 採用 / 保留 / 棄却基準 (overall)

| 条件 | ACCEPT | NEEDS_MORE_EVIDENCE | REJECT |
|---|---|---|---|
| Phase 1 真因が "stale guard" 判定 | ✓ | (該当なし、H0 なら REJECT) | "legitimate / 現在も必要" |
| Phase 2 drift guard で全 drift row 排除 | ✓ + false-negative 0 | 1-2 false-negative | ≥ 3 false-negative |
| Phase 3 tier-master ERROR | 0 | (該当なし) | ≥ 1 |
| Phase 4 patch unified diff format で apply 可能 | ✓ | partial | invalid diff |
| Phase 5 Adversarial 8/8 PASS | 8/8 | 6-7/8 | ≤ 5/8 |
| 推定 Tier1 route-through (Phase 4 patch 適用後 counterfactual) | ≥ 50% | 30-49% | < 30% |
| 推定 Tier 2/3 regression | ≤ 5% | 5-10% | > 10% |
| Double-execution risk in patch | 0 | (該当なし) | ≥ 1 |

7 条件全て ACCEPT で **patch 提案 GO** (= 別 task で実装 + 本番 deploy 検討)。
1 条件以上 REJECT、または 3 条件以上 NEEDS_MORE_EVIDENCE で **patch 提案 NO_GO** (= 本タスク 棄却、再設計)。

# 8. データ分離 (`feedback_live_shadow_separation` 厳守)

- 入力: Production OANDA audit DB / trade DB (Render fx-ai-trader main, **read-only**)
- 出力: `.ai/runs/<run_id>/` 配下のレポート + diff のみ
- modules/, app.py, strategies/, knowledge-base/wiki/tier-master.json への **編集禁止** (本タスクは proposal only)
- demo.db / 本番 DB write 禁止

# 9. 検証コマンド (Codex 必須実行)

```bash
cd /data/repo/fx-ai-trader

# Phase 1: source archaeology
grep -rn "daytrade_eur" modules/ app.py strategies/ knowledge-base/ --include="*.py" --include="*.md" 2>&1 | head -30
git log -p --all -S "daytrade_eur" -- modules/demo_trader.py 2>&1 | head -100

# Phase 2: drift guard 実装 + 検証
python3 tools/tier1_shadow_tracking_drift_guard.py \
  --audit /tmp/oanda-audit-tier1-rca.json \
  --trades /tmp/live-trades-tier1-rca.json \
  --output .ai/runs/<run_id>/drift-rows.json

# Phase 3: tier-master 整合性 (dry-run only)
python3 tools/tier_integrity_check.py --check 2>&1 | tail -30
# ↑ ERROR=0 を確認、--write は使わない

# Phase 4: patch 草案
# Codex が unified diff で .ai/runs/<run_id>/v1-narrow-impl-patch.diff を生成
# 検証: diff が apply 可能か dry-run
git apply --check .ai/runs/<run_id>/v1-narrow-impl-patch.diff 2>&1
# 期待: clean apply 可、ただし実際の git apply は実行しない

# Phase 5: counterfactual re-run with V1 patch logic
python3 tools/tier1_shadow_tracking_counterfactual.py \
  --audit /tmp/oanda-audit-tier1-rca.json \
  --variant v1-narrow \
  --output .ai/runs/<run_id>/counterfactual-narrow.json
```

# 10. 出力すべきレポート (codex `--output-last-message`)

1. **Phase 1 真因 verdict**: stale guard / legitimate / unclear のいずれか + 根拠
2. **Phase 2 drift row 列挙**: 件数 + 各 row の demo_trade_id / pair / cell
3. **Phase 3 tier-master snapshot**: 現在 ELITE_LIVE Tier1 cells (V1 適用範囲)
4. **Phase 4 patch summary**: 変更行数 / 新規 audit reason / unified diff path
5. **Phase 5 adversarial review 8 軸 pass/fail**
6. **Counterfactual narrow estimate**: V1 patch 適用後の Tier1 route-through / regression / risk
7. **Overall verdict**: ACCEPT_PROPOSAL_GO / NEEDS_MORE_EVIDENCE / REJECT_PROPOSAL_NO_GO
8. **次のタスク提案**:
   - GO: 「V1 patch を main に PR として apply する task」spec を書け
   - NO_GO: 「Wave 4-5 で dedicated Tier1 routing layer 設計」task spec を書け

# 11. 禁止事項

- ❌ `.env`, OANDA / OPENAI / Render / GitHub PAT を読む / 書く / log に出す
- ❌ `modules/`, `app.py`, `strategies/`, `knowledge-base/wiki/tier-master.json` を **編集** (本タスクは proposal only)
- ❌ 本番 DB / Render `/var/data/*.db` への書き込み
- ❌ ローカル DB (`demo.db` 等) への書き込み
- ❌ Pre-registration LOCK 違反: Phase 仕様 / patch 構造 / verdict matrix の post-hoc 修正
- ❌ Phase 1 真因が legitimate と判定されたのに Phase 2-4 を続行 (= cherry-pick disguise)
- ❌ V1 patch スコープ creep (`daytrade_eur` 以外の mode block / 他 sub-conditions / shadow_tracking literal 削除)
- ❌ Drift row guard を skip して patch を出す
- ❌ tier_integrity_check `--write` 実行 (`--check` のみ)
- ❌ Live bucket と Shadow bucket の混在集計 (`feedback_live_shadow_separation`)
- ❌ `git push` / `git rebase --onto` history rewrite

# 12. Rule R1 verification

- Live trading routing logic への変更を提案する R1 task
- pre-registration LOCK: 本ファイルの Phase 1-5 仕様 + verdict matrix + patch スコープ全て LOCK
- post-hoc に上記 LOCK を変更した場合、verdict 強制 INVALID で全 phases NEEDS_MORE_EVIDENCE 扱い
- 365日 BT スキップ可 (本タスクは proposal forensic、BT は別 task で V1 deploy 後の Live N≥30 で実施)

# 13. 期待される所要時間

- Phase 1 source archaeology: ~10 min
- Phase 2 drift guard 実装: ~10 min
- Phase 3 tier-master integrity: ~5 min
- Phase 4 patch 草案: ~10 min
- Phase 5 adversarial review: ~5 min
- 合計: **40-60 min**

# 14. 月利 100% ロードマップへの寄与 (最大寄与候補)

- Tier1 ELITE_LIVE 5 cells は BT EV +0.6 ~ +1.0 だが Live で 0.5% pass-through に縮退していた
- V1 narrow patch で **route-through 50%** に回復すれば、Tier1 LIVE が **本来の EV 領域**に収束 (predicted by RCA)
- Gate 1 (Kelly Half) alpha source 多様化を **新規 family 開発でなく既存 strategies の Live 流路修正**で達成
- Chart pattern family 真死 (W1P3 で確定) の代替として、月利 100% への **最短経路**

ACCEPT_PROPOSAL_GO 後の sequence:
1. 別 task で V1 patch を branch/PR として作成
2. PR review (user / code-reviewer agent)
3. Render shadow deploy で 1 週間 A/B (`is_shadow=0` Live route-through 計測)
4. Live N≥30 + Wilson_lo > 0.5 + Bonferroni m=5 (5 cells) で promote 判定
5. promote → 月利 100% への大きな前進

# 15. 並列タスクとの関係

- 並列: `20260504-1450-shadow-tracking-audit-label-fidelity-fix.md` (R3 audit label 修正)
  - 11 sub-conditions の specific block_reason を audit log に保存 (= shadow_tracking literal の上に追加情報)
  - 本 V1 narrow implementation とは **独立**: 並列 R3 が完了しなくても V1 narrow は実装可能
  - ただし R3 完了後は forensic 効率が大幅に上がるので、V1 narrow patch deploy 前に R3 を済ませるのが望ましい

# 16. 参考: 引き継ぎ

forensic (`20260504-1410-tier1-shadow-tracking-forensic-relaxation`) で確定:
- shadow_tracking sub-condition 5 種類 (locked 10-cell N=74)
- top sub-condition: `post_gate_mode_blocked:daytrade_eur` (40.5%)
- V1 verdict: ACCEPT (50% route-through, 2.3% regression, 0 risk, 7/7 adversarial)
- V2/V3 verdict: REJECT (drift row `8b943193-5d4` で double-execution risk)
- tier-master stale: ELITE_LIVE は `trendline_sweep` のみ (gbp_deep_pullback / session_time_bias は demoted)

本タスクは V1 ACCEPT を起点に、**実装に至る前に必須の forensic 3 phase + patch 草案 + adversarial review** を pre-reg LOCK で進め、Production safety を担保した上で実装提案を出すのが目的。
