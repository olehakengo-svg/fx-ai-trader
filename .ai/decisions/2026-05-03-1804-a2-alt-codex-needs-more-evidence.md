---
date: 2026-05-03T18:04:00+0900
task: 20260503-1700-a2-alt-simple-structure-scalp-pre-reg
codex_job: task-mopjfwyp-g5iymv
codex_session: 019ded0f-788a-7980-8ee7-1bf8d254be8d
run_dir: .ai/runs/20260503-175813-20260503-1700-a2-alt-simple-structure-scalp-pre-reg
rule: R1
verdict: NEEDS_MORE_EVIDENCE
roadmap_gate: Gate 1 (Scalp 枝 N-acceleration, simple-first principle)
---

# A2-alt Codex Result Review — 2026-05-03 18:04

## 判定: NEEDS_MORE_EVIDENCE

Codex が請け負った範囲（wrapper + tests + dry-run + schema/fingerprint validation）は完了しているが、**4 候補の Promote / Shadow / Reject 最終 verdict が未生成**。Rule 1 タスクの Acceptance Criteria の半分が未達。

## Codex 完了範囲（ACCEPT 相当）

- `tools/scalp_alt_pre_reg_bt.py`: LOCKED 閾値（Promote / Shadow）と K=4 Bonferroni をモジュール定数で固定。`--dry-run` で 4 候補・閾値・BEV_WR・verdict カテゴリが完全表示される（実機確認済み）。
- `tests/test_scalp_alt_pre_reg_bt.py`: 13 tests PASS。OVERFIT_SUSPECTED の Shadow→Reject 降格、Bonferroni K=4 計算、aggregate cap-to-one Promote、stale candidate JSON rejection を含む。
- 追加で `schema_version` と `wrapper_fingerprint` を candidate JSON に埋め込み、`--aggregate` 段で fingerprint mismatch / schema 不整合を拒否する gate を実装。これは task scope 外だが Rule 3（pollution prevention）として正しい構造防御。

## 未達（NEEDS_MORE_EVIDENCE の根拠）

| Acceptance Criterion | 状態 |
|---|---|
| `tools/scalp_alt_pre_reg_bt.py` LOCKED & dry-run | ✅ |
| `tests/test_scalp_alt_pre_reg_bt.py` PASS | ✅ (13 passed) |
| 4 candidate JSON (`scalp-alt-{bb_squeeze, engulfing, fib, sr}-2026-05-03.json`) | ❌ 未生成（bb_squeeze は旧 wrapper artifact のみ） |
| Aggregate verdict doc `wiki/learning/scalp-alt-pre-registration-2026-05-03.md` | ❌ 未生成 |
| 各候補の N / WR / EV / PF / Wilson lower / Bonferroni p / WF IS-OOS PF | ❌ 未生成 |
| Promote/Shadow/Reject 結論 | ❌ 未確定 |

## 既存 bb_squeeze JSON の問題（重要発見）

`knowledge-base/raw/bt-results/scalp-alt-bb_squeeze-2026-05-03.json` は:

- `wrapper_fingerprint` フィールド欠如 → 現行 wrapper の `--aggregate` で拒否
- `stats { n=23, wins=0, losses=0 }` という算数破綻（n>0 なのに wins+losses=0）
- `entry_breakdown wins=18` と `stats wins=0` の不整合

→ verdict 材料として使えない。**現行 wrapper で再生成必須**。Codex の fingerprint/schema gate がこの汚染を阻止した。これは `lesson-silent-except` / `lesson-stats-segment-decomposition` 系の防御として価値ある実装。

## データ混入確認

- BT 4 候補のみ（USD_JPY 5m × 2、EUR_USD 1m/5m × 2）
- Live / Shadow / OANDA / 本番DB / `.env` / OANDA 秘密情報への接触なし
- `app.py` `QUALIFIED_TYPES` 変更なし（task scope どおり）

## ロードマップ進捗

- **Gate 1 (Scalp 枝 N-acceleration)**: 進まず。verdict が無いので OANDA bridge への登録判断不可。
- **Gate 0 (生存・aggregate Kelly < 0 復帰)**: 別系統（R2 cell demotion lock、R3 BT wrapper fingerprint gate）が並行進行中。本タスクは Gate 0 に直接寄与しない。

## 次の一手（推奨タスク）

**A2-alt foreground BT completion** — Parent Claude が以下を foreground で順次実行:

```bash
python3 tools/scalp_alt_pre_reg_bt.py --candidate bb_squeeze_breakout --engine-timeout 600 \
  --output knowledge-base/raw/bt-results/scalp-alt-bb_squeeze-2026-05-03.json
python3 tools/scalp_alt_pre_reg_bt.py --candidate engulfing_bb --engine-timeout 600 \
  --output knowledge-base/raw/bt-results/scalp-alt-engulfing-2026-05-03.json
python3 tools/scalp_alt_pre_reg_bt.py --candidate fib_reversal --engine-timeout 600 \
  --output knowledge-base/raw/bt-results/scalp-alt-fib-2026-05-03.json
python3 tools/scalp_alt_pre_reg_bt.py --candidate sr_channel_reversal --engine-timeout 600 \
  --output knowledge-base/raw/bt-results/scalp-alt-sr-2026-05-03.json
python3 tools/scalp_alt_pre_reg_bt.py --aggregate \
  --output knowledge-base/wiki/learning/scalp-alt-pre-registration-2026-05-03.md
```

verdict 確定後の分岐:

- **少なくとも 1 候補が Promote / Shadow** → A3-simple（OANDA bridge 登録 + monitoring）
- **全 Reject / Insufficient / BT_GATE_BLOCKED** → A2-alt2（次の simple 候補を pre-register）

## ステータス遷移

- タスクは `.ai/tasks/queue/` に保留（Codex の wrapper 構築フェーズは完了したが、Acceptance Criteria 未達のため queue に残す）
- 実 BT 実行は Codex sandbox では完了不可（タスク仕様で foreground 実行を明示）
