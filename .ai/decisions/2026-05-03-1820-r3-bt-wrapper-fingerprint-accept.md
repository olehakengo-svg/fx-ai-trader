---
date: 2026-05-03T18:20:00+0900
verdict: ACCEPT
rule: R3
roadmap_gate: Gate 0 (生存 — BT decision pipeline integrity)
task: 20260503-1745-r3-bt-wrapper-fingerprint-aggregate-gate
codex_job: task-mopjhtis-h3wdkp
codex_session: 019ded10-df80-7bf0-9ddc-67efa393223e
run_dir: .ai/runs/20260503-175942-20260503-1745-r3-bt-wrapper-fingerprint-aggregate-gate
---

# 判定: ACCEPT

## 理由

R3 構造ゲートの受入条件をすべて満たした。

| 観点 | 結果 |
|---|---|
| 仕様準拠 | `tools/bt_common.py` に `compute_wrapper_fingerprint()` 新設、3 wrapper (scalp_alt_pre_reg, scalp_re_enable, vec_harness_chunked_cli) に `wrapper_fingerprint` 書込追加、aggregate refusal gate は `scalp_alt_pre_reg_bt.py` のみに集約 (SRP遵守)。 |
| ユニットテスト | 8/8 pass (`tests/test_bt_wrapper_fingerprint.py`): determinism / whitespace 不変 / PnL ロジック変化 / LOCKED threshold 変化 / CANDIDATES 変化 / stale aggregate refusal / 実 wrapper 3本のスモーク。|
| 既存回帰 | `tests/test_scalp_alt_pre_reg_bt.py` 13/13 pass (verdict logic 副作用なし)。|
| 再現コマンド | `python3 tools/scalp_alt_pre_reg_bt.py --aggregate` を実 stale `scalp-alt-bb_squeeze-2026-05-03.json` がある状態で実行 → **stderr 「wrapper_fingerprint mismatch: ... was produced by wrapper missing, current wrapper is b6d738...」+ exit=2** を直接確認。A2-alt trap が機械的に閉じている。|
| Backward compat | 単一候補 `--candidate <name>` JSON に `wrapper_fingerprint` フィールド追加のみ。既存フィールド型/意味の変更なし。|
| Scope guard | `app.py` / `modules/` / `strategies/` / `wiki/decisions/` / `wiki/index.md` / `wiki/strategies/` / `wiki/tier-master.md` 編集 0件 (final.md の Scope guard 節 + 現 git status で確認)。Codex は既存 stale JSON の delete/編集も行っていない (parent Claude のスコープ)。|
| データ混在 | R3 infra タスクのため BT/Shadow/Live/OANDA データに触れていない。fingerprint は wrapper の AST + LOCKED constants + CANDIDATES の SHA-256 のみ。|
| 本番危険操作 | `.env` / 本番 DB / OANDA secret / Render API いずれも未参照。|

## ロードマップ寄与

Gate 0 (生存) の決定パイプライン integrity が 1 段強化された。直接的な月利寄与はないが、queue に積まれている wrapper-driven BT タスク (A2-alt 再走、W3-3 rerun、W3-4 rerun) で **wrapper bug 修正後に古い JSON が混入する class の汚染** が機械的にブロックされる。Gate 1 unlock 試行を**安全に**回せるインフラとして必須。

## 残課題 (このタスクの範囲外)

1. **stale `scalp-alt-*.json` の再生成** — fingerprint 不一致で aggregate が止まる現状を、post-fix wrapper で再生成して exit 0 にできることを実 E2E で確認する。queue のタスク #1 (A2-alt simple-structure scalp pre-reg) と一体で動く。
2. `vec_harness_chunked_cli.py` 側の aggregate gate は本タスクで意図的にスコープ外。fingerprint 書込のみ実装済み。将来 vec_harness が aggregate verdict を出す経路を持つなら追加検討。
3. `scalp_re_enable_bt.py` には `CANDIDATES` 定数が無いため fingerprint は PnL helpers + LOCKED constants のみで決まる (final.md Risks 節)。今のところ問題ないが、将来 candidate set を導入する場合は同様にハッシュ対象に含める。

## 教訓化

- 「stale data with the right schema」は silent contamination の主因。wrapper-side ハッシュ + aggregate-side 比較 という構造ゲートが既存戦略の verdict logic に副作用 0 で導入できた事例として、今後の BT インフラに横展開できる。
