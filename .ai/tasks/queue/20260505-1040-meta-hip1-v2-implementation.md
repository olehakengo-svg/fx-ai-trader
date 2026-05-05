---
id: 20260505-1040-meta-hip1-v2-implementation
title: "[META] HIP-1 v2 implementation — fail-safe BT/offline-only guard"
owner: codex
status: queued
priority: P2
created_at: 2026-05-05T10:40:00+0900
roadmap_gate: meta-discipline (Top 5 of post-Qiita-article gap analysis, retry of v1 HOLD)
rule: R1
prereq_artifacts:
  - knowledge-base/wiki/decisions/holdout-isolation-protocol-2026-05-04.md  # v2 amendment 適用済
  - .ai/runs/20260504-182301-20260504-1835-meta-hip1-implementation/final.md  # v1 HOLD report
  - modules/data.py
related:
  - knowledge-base/wiki/lessons/feedback_codex_schema_hallucination.md
---

# 0. Why this task

HIP-1 v1 (`.ai/runs/20260504-182301-...`) は LIVE pipeline reachability (`app.py:171` / `demo_trader.py:700` が `fetch_ohlcv` 経由で `_load_parquet_cache_fallback` 到達可) を理由に Codex が正しく HOLD escalate。

司令塔 Claude が **option 2 (BT/offline-only scope に限定)** を選択し、spec doc §2.1 / §2.2 を v2 に amendment 済。本タスクはその v2 spec の実装。

**v1 → v2 主要変更**: guard はデフォルト OFF。BT runners が `FX_HOLDOUT_GUARD=1` を opt-in した時のみ active。LIVE プロセスは env 未設定 → 無影響。

# 1. Inputs

1. **Spec v2** (必読): `knowledge-base/wiki/decisions/holdout-isolation-protocol-2026-05-04.md` §2.1 (適用条件 v2) / §2.2 Layer 2 (`_apply_holdout_guard` v2 挙動) / §4 implementation
2. **v1 HOLD report**: `.ai/runs/20260504-182301-20260504-1835-meta-hip1-implementation/final.md` (LIVE-adjacent reachability の grep 結果)
3. **既存 loader**: `modules/data.py:_load_parquet_cache_fallback` (line ~118)

# 2. Scope

Codex may change:

- `data/_holdout_locked/MANIFEST.json` (新規)
- `modules/data.py` (`_apply_holdout_guard` v2 追加 + 呼び出し 1 行)
- `tests/test_holdout_guard.py` (新規)
- `.pre-commit-config.yaml` (なければ新規。既存 hook script 様式があれば踏襲)
- `tools/precommit/check_holdout_manifest.py` (新規 hook script)
- `tools/audit/holdout_validation_runner.py` (新規スケルトン)
- `knowledge-base/raw/audits/hip1-v2-installation-2026-05-05.md` (新規 installation report)

Codex must not change:

- production secrets / .env / render.yaml
- 既存戦略 `strategies/**`
- `app.py`, `live_*.py`, `demo_trader.py` のロード経路 (LIVE は env 未設定で no-op が保証されるため触る必要なし)
- spec doc (claude 編集領域)

# 3. Required Reading

- `CLAUDE.md`
- spec v2 (`knowledge-base/wiki/decisions/holdout-isolation-protocol-2026-05-04.md`)
- v1 HOLD report (上記)
- `modules/data.py` 全体

# 4. Implementation contract (v2 fail-safe)

## 4.1 `_apply_holdout_guard()` 挙動 (spec §2.2 v2)

```python
def _apply_holdout_guard(df: pd.DataFrame, source_path: str) -> pd.DataFrame:
    """v2 fail-safe: opt-in via FX_HOLDOUT_GUARD=1 only.

    Behavior:
    - FX_HOLDOUT_GUARD != "1" → return df unchanged (LIVE default; no logging)
    - manifest absent → return df unchanged (legacy compat; no logging)
    - FX_HOLDOUT_GUARD == "1" AND FX_HOLDOUT_VALIDATION == "1"
      → return df unchanged + log warning "HOLDOUT VALIDATION MODE..."
    - FX_HOLDOUT_GUARD == "1" AND FX_HOLDOUT_VALIDATION != "1"
      → cut rows in lock_window, increment _HOLDOUT_CUT_COUNTER, log debug
    """
```

LIVE / app.py / demo_trader.py が `fetch_ohlcv` 経由で到達しても、env 未設定なので **挙動は完全に変わらない**。

## 4.2 BT runner side

本タスクでは BT runner 側の改修は **しない** (将来別タスク)。代わりに:
- spec §2.3 `tools/audit/holdout_validation_runner.py` スケルトンに `os.environ["FX_HOLDOUT_GUARD"] = "1"` を実行直後に必ずセット
- README の note: 既存 BT runners が holdout を踏みたくない場合は、CLI 起動時に `FX_HOLDOUT_GUARD=1 python3 tools/bt/...` で opt-in する旨を `knowledge-base/raw/audits/hip1-v2-installation-2026-05-05.md` に明記

## 4.3 Manifest (spec §2.2 Layer 1)

`data/_holdout_locked/MANIFEST.json`:

```json
{
  "version": 2,
  "lock_window_utc": ["2025-11-04T00:00:00Z", "2026-05-04T00:00:00Z"],
  "issued_at": "2026-05-05T10:40:00+0900",
  "issuer": "claude-司令塔",
  "expires_at": "2026-08-05T00:00:00Z",
  "rationale": "Wave 4 6-month holdout window (HIP-1 v2 fail-safe scoped)",
  "covered_paths": ["data/cache/**/*.parquet"],
  "guard_env": "FX_HOLDOUT_GUARD",
  "validation_env": "FX_HOLDOUT_VALIDATION"
}
```

## 4.4 Tests `tests/test_holdout_guard.py` (最低 7 テスト, v2 で +2)

1. **manifest absent**: ガードが no-op で全行返ること
2. **guard env unset**: `FX_HOLDOUT_GUARD` 未設定 → 全行通過 (LIVE default 検証) **[v2 追加]**
3. **inside lock window cut (opt-in)**: `FX_HOLDOUT_GUARD=1`, `FX_HOLDOUT_VALIDATION` 未設定 → lock 期間の行が落ち、`_HOLDOUT_CUT_COUNTER` が増える
4. **outside lock window passthrough**: `FX_HOLDOUT_GUARD=1` でも lock 期間外のみの df は無傷
5. **validation env passthrough**: `FX_HOLDOUT_GUARD=1` AND `FX_HOLDOUT_VALIDATION=1` で全行残り、ログ警告
6. **manifest schema validation**: 不正 JSON / 必須キー欠落の manifest は `RuntimeError` (guard active 時のみ)
7. **LIVE simulation**: `FX_HOLDOUT_GUARD` 未設定で `fetch_ohlcv` 様の経路を模した呼び出しが完全 passthrough であること **[v2 追加]**

## 4.5 pre-commit hook (spec §2.2 Layer 3)

- `data/_holdout_locked/MANIFEST.json` への触り → `--allow-holdout-edit` flag なしで reject
- `.ai/runs/<recent>/final.md` に `HOLDOUT VALIDATION MODE` 文字列を含む場合 → claude 手動 OK 以外 reject

# 5. Acceptance Criteria

- [ ] `pytest tests/test_holdout_guard.py -v` 7 テスト PASS (v2 で +2)
- [ ] **LIVE 影響ゼロ regression**: `FX_HOLDOUT_GUARD=""` (env 未設定) で `tools/bt/s4_connors_raschke.py --dry-run` 既存挙動と完全同値 (numerical regression test)
- [ ] `FX_HOLDOUT_GUARD=1` を opt-in した状態で BT runner が holdout 期間の bar を見ないことを 1 ケース確認
- [ ] `pre-commit run --files data/_holdout_locked/MANIFEST.json` が hook で reject される (claude 手動 flag なし時)
- [ ] `python3 tools/audit/holdout_validation_runner.py --help` が成立
- [ ] installation report `knowledge-base/raw/audits/hip1-v2-installation-2026-05-05.md` 出力 (LIVE 影響ゼロ確認結果を明記)
- [ ] Run report `.ai/runs/<timestamp>-meta-hip1-v2-implementation/final.md`

# 6. Verification Commands

```bash
pytest tests/test_holdout_guard.py -v
python3 -m ruff check modules/data.py tools/audit/holdout_validation_runner.py tools/precommit/check_holdout_manifest.py
pre-commit run --all-files
python3 tools/audit/holdout_validation_runner.py --help

# LIVE 影響ゼロ regression:
unset FX_HOLDOUT_GUARD
python3 tools/bt/s4_connors_raschke.py --dry-run > /tmp/pre-hip1.txt 2>&1
# (After implementation, the same command must produce identical output)
diff /tmp/pre-hip1.txt /tmp/post-hip1.txt  # 期待: 空 diff

# Opt-in BT verification:
FX_HOLDOUT_GUARD=1 python3 -c "from modules.data import fetch_ohlcv; df = fetch_ohlcv('USD_JPY', 'M5', days=400); print(f'rows={len(df)}, max_date={df.index.max()}')"
# 期待: max_date が 2025-11-04 より前 (lock_window 内 cut 済)
```

# 7. Codex Instructions

Work in this repository. Respect existing uncommitted changes. Do not revert user changes.

実装手順:

1. spec v2 を熟読。**fail-safe 既定 (env 未設定 → no-op)** を厳守。
2. RED first: tests を先に書いて FAIL → GREEN へ。tests #2 (LIVE default unset) と #7 (LIVE simulation) を必ず先頭に書く (fail-safe 既定の明示的検証)。
3. **LIVE 影響ゼロ regression test を必ず走らせる** (acceptance #1)。これが fail したら spec 違反、stop & escalate。
4. ruff / mypy / pytest / pre-commit すべて PASS でコミット (sandbox 制約あれば v1 同様 git commit は claude が後で行うので問題なし、ただしファイルは worktree に残す)。
5. installation report に **「LIVE 影響ゼロ確認: env 未設定で `fetch_ohlcv` 経路の挙動が pre-implementation と完全同値」** を grep + diff 結果と共に明記。

In the final report, include status, files changed, verification output summary, **LIVE 影響ゼロ regression test 結果**, opt-in BT cut verification 結果, remaining risks, next recommended task。
