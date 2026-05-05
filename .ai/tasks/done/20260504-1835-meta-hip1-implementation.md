---
id: 20260504-1835-meta-hip1-implementation
title: "[META] HIP-1 (Holdout Physical Isolation) 実装"
owner: codex
status: queued
priority: P1
created_at: 2026-05-04T18:35:00+0900
roadmap_gate: meta-discipline (Top 5 of post-Qiita-article gap analysis)
rule: R1
prereq_artifacts:
  - knowledge-base/wiki/decisions/holdout-isolation-protocol-2026-05-04.md
  - modules/data.py
related:
  - knowledge-base/wiki/lessons/feedback_codex_schema_hallucination.md
---

# 0. Why this task

司令塔 Claude の Qiita 記事ギャップ分析 5 提案中 Top 5。Wave 4 holdout を **物理的にロック** して開発期間中の data leakage / 暗黙 over-fit / Codex 推測流入を防ぐ。

詳細仕様は `knowledge-base/wiki/decisions/holdout-isolation-protocol-2026-05-04.md` に確定済み (HIP-1 Protocol)。本タスクはその実装。Top 4 (NSG-1) と独立で並列実行可。

# 1. Inputs

1. **Spec** (必読): `knowledge-base/wiki/decisions/holdout-isolation-protocol-2026-05-04.md`
2. **既存 loader**: `modules/data.py:_load_parquet_cache_fallback` (line ~118)
3. **既存 hook 様式**: `.pre-commit-config.yaml` (本リポの既存 hook を 1 つ模倣する)

# 2. Scope

Codex may change:

- `data/_holdout_locked/MANIFEST.json` (新規)
- `modules/data.py` (`_apply_holdout_guard` 追加 + 呼び出し 1 行)
- `tests/test_holdout_guard.py` (新規)
- `.pre-commit-config.yaml` (hook 追加)
- `tools/precommit/check_holdout_manifest.py` (新規 hook script)
- `tools/audit/holdout_validation_runner.py` (新規スケルトン)
- `knowledge-base/raw/audits/hip1-installation-2026-05-04.md` (実装後レポート)

Codex must not change:

- production secrets / .env / render.yaml
- 既存戦略コード `strategies/**`
- LIVE pipeline (`live_*.py`, `app.py`, `demo_trader.py`) のロード経路
- `knowledge-base/wiki/decisions/holdout-isolation-protocol-2026-05-04.md` (claude の編集領域)

# 3. Required Reading

- `CLAUDE.md`
- spec 文書 (`knowledge-base/wiki/decisions/holdout-isolation-protocol-2026-05-04.md`)
- `modules/data.py` 全体
- `.pre-commit-config.yaml`

# 4. Implementation contract

§4.1〜§4.4 は spec doc §4 をそのまま acceptance とする。**特に R2 (LIVE pipeline 影響) のチェック項目を必ず実行**:

```bash
grep -rn "data/cache\|_load_parquet_cache_fallback" modules/ live_*.py app.py demo_trader.py 2>/dev/null
```

LIVE pipeline が `data/cache/` を間接参照するパスがあれば installation report に「LIVE 影響なし」根拠として明記。あれば本タスクは **HOLD** で claude にエスカレーション (即実装しない)。

# 5. Acceptance Criteria

spec doc §4.3 を満たすこと。加えて:

- [ ] `_HOLDOUT_CUT_COUNTER` が process-level で正しくインクリメントされ、`get_holdout_cut_count()` 公開関数で参照可能
- [ ] BT runner 1 本 (`tools/bt/s4_connors_raschke.py --dry-run` 等) が依然 PASS
- [ ] LIVE pipeline 影響評価結果を installation report に明記
- [ ] Run report `.ai/runs/<timestamp>-meta-hip1-implementation/final.md`

# 6. Verification Commands

```bash
pytest tests/test_holdout_guard.py -v
ruff check modules/data.py tools/audit/holdout_validation_runner.py tools/precommit/check_holdout_manifest.py
pre-commit run --all-files
python3 tools/audit/holdout_validation_runner.py --help
python3 tools/bt/s4_connors_raschke.py --dry-run
grep -rn "data/cache" modules/ app.py demo_trader.py 2>/dev/null
```

# 7. Codex Instructions

Work in this repository. Respect existing uncommitted changes. Do not revert user changes.

実装手順:

1. spec を熟読。Layer 2 ガードの「静かに切る」設計を厳守 (例外で stop は不可)。
2. RED first: `tests/test_holdout_guard.py` を先に書いて FAIL を確認 → GREEN へ。
3. LIVE pipeline 影響を grep で先に評価。HOLD 条件に該当したら spec 通り claude にエスカレーション。
4. ruff / mypy / pytest / pre-commit すべて PASS でコミット。
5. installation report 出力。

In the final report, include status, files changed, verification output summary, LIVE pipeline impact assessment, remaining risks, and next recommended task.


## Result (2026-05-05T00:47:17Z)

exit=0 · 78s

```
Status: `HOLD`. I did not implement HIP-1 because the task’s pre-edit HOLD condition was met.

Files changed:
- [hip1-installation-2026-05-04.md](/data/repo/fx-ai-trader/knowledge-base/raw/audits/hip1-installation-2026-05-04.md)
- [final.md](/data/repo/fx-ai-trader/.ai/runs/20260505-004642-meta-hip1-implementation/final.md) created, but `.ai/runs/*` is git-ignored in this repo.

Key blockers:
- Required spec is missing: `knowledge-base/wiki/decisions/holdout-isolation-protocol-2026-05-04.md`
- Required `.pre-commit-config.yaml` is missing.
- LIVE path is not clean: `app.py` and `modules/demo_trader.py` call/re-export `fetch_ohlcv`, and `modules.data.fetch_ohlcv()` can fall through to `_load_parquet_cache_fallback()`.

Verification summary:
- Ran the required LIVE grep. It found `data/cache` / `_load_parquet_cache_fallback` in `modules/bt_vec_harness.py` and `modules/data.py`.
- Traced live reachability to `fetch_ohlcv` from `app.py` and `modules/demo_trader.py`.
- Did not run pytest/ruff/pre-commit/BT runner because implementation was intentionally stopped before edits.

Remaining risk: adding the guard in `modules/data.py` without a clarified live-safe boundary could change LIVE fallback behavior.

Next recommended task: restore/provide the HIP-1 spec, clarify whether to create `.pre-commit-config.yaml` or use `scripts/hooks/git-pre-commit.sh`, and decide how HIP-1 should isolate holdout data without touching LIVE fallback behavior.
```
