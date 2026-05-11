---
id: 2026-05-11-1400-flag-drift-codex-stash-leak
title: FLAG-DRIFT-FIX Codex run ACCEPT verdict が persist 欠落、stash@{0} に埋没
verdict: CHANGES_REQUESTED
recovery: possible
rule: R3
related_task: 20260511-1400-flag-drift-writepath-fix
codex_job: task-mp0q4wq8-bc51q2
codex_session: 019e1560-08e3-7e32-b117-d36bc6e94a57
created_at: 2026-05-11T14:00:00+0900
---

# 経緯

1. 司令塔が FLAG_DRIFT write-path fix task を起票 (`20260511-1400-flag-drift-writepath-fix.md`)
2. Codex companion が task-mp0q4wq8-bc51q2 として実行 (6m 0s)
3. final.md: `ACCEPT` (1403 passed) と報告
4. 司令塔 review で発覚: コード変更が repo に persist されていない

# 根本原因

- Codex companion は実行前に user の wip を `stash@{0} wip-unrelated-2026-05-11` として stash
- Codex は FLAG_DRIFT 修正を実装し sandbox 内 test pass
- Codex は commit せず session 終了
- 終了時の stash restore でユーザー wip + Codex 変更が混在 stash として stash@{0} に保持される結果に

# stash@{0} 内容 (7 files)

| File | 変更 | 由来 |
|---|---|---|
| AGENTS.md | memory context timestamp | user wip |
| data/sentiment/oanda_labs_h4_history.parquet | binary update | user wip |
| knowledge-base/raw/hunt_events/2026-05-11.jsonl | +12 events | user wip |
| knowledge-base/wiki/sessions/2026-05-11-session.md | +1 line | user wip |
| modules/data.py | +12 lines (EURNZD/AUDNZD/AUDCAD/NZDCAD pair extension) | user wip (Phase 1c 14-pair 関連?) |
| **modules/demo_db.py** | +14 lines (`oanda_trade_id`+`enforce_oanda_live_invariant` 引数) | **Codex FLAG-DRIFT** |
| **modules/demo_trader.py** | +39 lines (`_resolve_tier()`, invariant call) | **Codex FLAG-DRIFT** |

# 失われた artifact

- `tests/test_flag_drift_writepath.py` source (新規 6 tests) — 未追跡なので stash に含まれず
- `.pyc` のみ `/private/tmp/pycache-codex/Users/jg-n-012/test/fx-ai-trader/tests/test_flag_drift_writepath.cpython-39-pytest-8.4.2.pyc` に残存
- → source 復元不可、再記述要

# Recovery plan

1. 新 feature branch `fix/flag-drift-writepath-2026-05-11` を origin/main から作成
2. stash@{0} から FLAG_DRIFT 関連 file のみ抽出 (`modules/demo_db.py` / `modules/demo_trader.py`) し新 branch へ apply
3. user wip files (AGENTS.md / hunt_events / session.md / oanda_labs parquet / modules/data.py) は別 stash 化して保持 (誤コミット防止)
4. `tests/test_flag_drift_writepath.py` は元 task spec §1.6 から司令塔が再記述 → 司令塔 or Codex 再走で生成
5. pytest tests/ green 確認後 PR
6. main に merge → Render auto-deploy 確認

# 教訓 (新 memory 必要)

- Codex companion の stash 挙動: 実行前 stash + 終了時 restore で、Codex 自身の変更が混在 stash に化けるパターンが存在
- 対策: Codex task spec で「最終 step として **必ず git commit + git push、stash しない**」を明示するか、Codex 走行前に user wip を別 branch に commit しておく
- memory `feedback_codex_mock_test_trap` 拡張: "Codex sandbox の `1403 passed` は repo に persist しなければ無意味"

# 司令塔判定

`CHANGES_REQUESTED` — 設計 (R3 invariant) は妥当だが verify 不能。Recovery 後に再判定。
