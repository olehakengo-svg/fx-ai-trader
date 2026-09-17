---
title: Holdout Physical Isolation Protocol (HIP-1)
date: 2026-05-04
status: PROPOSED → READY_FOR_VALIDATION
owner: claude-司令塔
implementer: codex
trigger: Wave 4 holdout が宣言運用にとどまり物理ロックされていない
related:
  - knowledge-base/wiki/decisions/neighborhood-stability-gate-2026-05-04.md
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
  - knowledge-base/wiki/lessons/feedback_codex_schema_hallucination.md
roadmap_gate: meta-discipline (cross-Wave)
---

# 1. Why this protocol exists

Wave 4 で「holdout 期間」を確保する旨は spec で要求しているが、**実装上 holdout は claude/codex のどちらからも自由にアクセスできるファイル**になっている。これは:

1. 開発中に holdout 期間を覗き見て暗黙に over-fit するリスク (data leakage)。
2. Codex schema hallucination (記憶) のように、**claude が参照を渡し損ねた場合に Codex が holdout データを推測で使う**リスク。
3. 多人数/多 worktree 並走時、誤って holdout を学習側に流入させる事故リスク。

HIP-1 は **holdout を物理的に閉鎖**して、開発期間中はロード経路自体が拒否する仕組みを敷く。

# 2. Mechanism

## 2.1 ロック対象 (initial scope)

- **時間範囲**: `2025-11-04 .. 2026-05-04` (本日から 6 ヶ月遡る期間。Wave 4 holdout の標準窓)
- **対象データ**: `data/cache/` 配下の OHLCV parquet (M5/M15/H1/D1 全 timeframe / 全 pair)
- **対象戦略開発**: Wave 1〜4 の全 Codex タスクと claude の手動 BT 解析
- **適用条件 (v2 amendment 2026-05-05, fail-safe 設計)**:
  - **BT runners が `FX_HOLDOUT_GUARD=1` を明示的にセットした時のみ guard active**
  - LIVE プロセス (`app.py` / `live_*.py` / `demo_trader.py` の通常起動) は env 未設定 → **guard 無効化 (passthrough)**
  - `FX_HOLDOUT_VALIDATION=1` も加えてセットすれば、`FX_HOLDOUT_GUARD=1` 下でも passthrough (Wave 4 final validation 専用)
  - これは v1 の「常時 active + LIVE 影響リスク」設計を、Codex の HIP-1 v1 escalation (`app.py:171` / `demo_trader.py:700` が `fetch_ohlcv` 経由で fallback 到達可) に応じて修正したもの

### v1 → v2 変更理由 (Codex HIP-1 v1 run 由来)

Codex が `_load_parquet_cache_fallback` の LIVE-adjacent reachability を grep で検出 (`app.py:171 fetch_ohlcv import` / `demo_trader.py:700 fetch_ohlcv_massive, fetch_ohlcv import`) し、HOLD escalation を発行。spec §4.4 R2 stop rule が機能した。

claude (司令塔) 判断: **option 2 (BT/offline-only scope に限定)** を採用。理由:
1. LIVE は OANDA 一次ソースで動き、parquet fallback は cold-degraded 経路 (primary 障害時のみ)。LIVE がそこを踏むのは emergency mode で、その時に holdout cut すると診断を一層難しくする。
2. fail-safe 原則: LIVE のデフォルト挙動を変えない。BT runners だけが opt-in する。
3. opt-in 設計は Codex タスクが BT runner 起動時に env を立てる規律と整合 (既存 PYTHONPYCACHEPREFIX 等と同様の設計パターン)。

## 2.2 物理ロック層 (defense in depth, 3 段)

### Layer 1 — Lock manifest

`data/_holdout_locked/MANIFEST.json` (新規):

```json
{
  "version": 1,
  "lock_window_utc": ["2025-11-04T00:00:00Z", "2026-05-04T00:00:00Z"],
  "issued_at": "2026-05-04T18:30:00+0900",
  "issuer": "claude-司令塔",
  "expires_at": "2026-08-04T00:00:00Z",
  "rationale": "Wave 4 6-month holdout window (HIP-1)",
  "covered_paths": ["data/cache/**/*.parquet"],
  "validation_env": "FX_HOLDOUT_VALIDATION"
}
```

Manifest が存在する間、後段 Layer がアクティブになる。Manifest 削除/更新は **claude のみ可** (Codex タスクからの編集は pre-commit hook で拒否)。

### Layer 2 — Loader guard

`modules/data.py:_load_parquet_cache_fallback` の出口に guard を挿入:

```python
df = _apply_holdout_guard(df, source_path=path)
```

`_apply_holdout_guard` の挙動 (v2):

- **fail-safe 既定**: `os.environ.get("FX_HOLDOUT_GUARD") != "1"` → no-op (LIVE / app.py / demo_trader.py はここで止まる)
- Manifest がなければ no-op (legacy 互換)
- `FX_HOLDOUT_GUARD=1` AND `FX_HOLDOUT_VALIDATION=1` → no-op + ログ警告 ("HOLDOUT VALIDATION MODE — exposing locked window")
- `FX_HOLDOUT_GUARD=1` AND `FX_HOLDOUT_VALIDATION` 未設定: lock_window 内の行を `df` から **静かに切り捨て**、cut 件数を `_HOLDOUT_CUT_COUNTER` (process-level) に記録

「切り捨て」を選んだ理由: 例外で stop すると BT runner の堅牢性が下がる。**データが見えない** という形で表面化させ、cell 統計で N が想定より少ない時点で気付ける設計にする。

### Layer 3 — pre-commit hook

`.pre-commit-config.yaml` に hook 追加 (新規 fail-only check):

- `data/_holdout_locked/MANIFEST.json` が触られた commit は claude 手動 OK 以外で reject (具体: hook script が `--allow-holdout-edit` flag をコマンド行に要求)。
- `FX_HOLDOUT_VALIDATION=1` で動かしたとおぼしき log/run report が `.ai/runs/` に残っていれば、claude セッション以外はマージ前に reject (hook が `.ai/runs/*/final.md` で `HOLDOUT VALIDATION MODE` 文字列を検出)。

## 2.3 検証専用呼び出し

Wave 4 の最終 holdout 検証は **専用 CLI** から起動:

```bash
FX_HOLDOUT_VALIDATION=1 python3 tools/audit/holdout_validation_runner.py \
    --strategy <name> --output knowledge-base/raw/audits/holdout-...
```

Runner は実行直後に `_HOLDOUT_CUT_COUNTER == 0` を assert (guard が抑止していないこと)。

# 3. Lifecycle

- **Lock 開始 (本決定)**: 2026-05-04
- **Lock 期限**: 2026-08-04 (3 ヶ月。Wave 4 完遂までの想定窓)
- **Lock 更新**: 期限到達後、claude が新 manifest を発行 (1-2 ヶ月分ずらすなど)。一度 unlock した期間を再ロックしないこと (data leakage の自己欺瞞回避)
- **緊急 unlock**: claude が manifest を削除 + decision doc に削除理由を記録

# 4. Implementation contract (Codex 担当)

## 4.1 Files to create / modify

- `data/_holdout_locked/MANIFEST.json` (新規、上記 §2.2 Layer 1 のスキーマで)
- `modules/data.py` 末尾近くに `_apply_holdout_guard()` 追加、`_load_parquet_cache_fallback` から呼び出し (1 行 patch)
- `tests/test_holdout_guard.py` (新規)
- `.pre-commit-config.yaml` に新規 hook (本リポの既存 hook 様式に準拠)
- `tools/precommit/check_holdout_manifest.py` (新規 hook script)
- `tools/audit/holdout_validation_runner.py` (新規スケルトン、実 BT 結合は本タスク外)
- `knowledge-base/raw/audits/hip1-installation-2026-05-04.md` (実装後の動作確認レポート)

## 4.2 Tests `tests/test_holdout_guard.py` (最低 5 テスト)

1. **manifest absent**: ガードが no-op で全行返ること。
2. **inside lock window cut**: Manifest あり / `FX_HOLDOUT_VALIDATION` 未設定 → lock 期間の行が落ち、`_HOLDOUT_CUT_COUNTER` が増えること。
3. **outside lock window passthrough**: lock 期間外のみの df は無傷で通る。
4. **validation env passthrough**: `FX_HOLDOUT_VALIDATION=1` で全行残り、ログに警告が出ていること (caplog)。
5. **manifest schema validation**: 不正 JSON / 必須キー欠落の manifest は `RuntimeError` で拒否。

## 4.3 Acceptance Criteria

- [ ] `pytest tests/test_holdout_guard.py -v` 5 テスト PASS
- [ ] `pre-commit run --files data/_holdout_locked/MANIFEST.json` が hook で reject される (claude 手動 flag なし時)
- [ ] `python3 tools/audit/holdout_validation_runner.py --help` が成立 (実 BT は未結合で OK)
- [ ] 既存 BT runner (`tools/bt/s4_connors_raschke.py --dry-run` など読み取り専用 path) を 1 本走らせて、ガード適用後も既存テストが PASS することを確認
- [ ] installation report `knowledge-base/raw/audits/hip1-installation-2026-05-04.md` 出力

## 4.4 Risks

- **R1 — silent cut**: ガードが静かに行を切ると BT 結果が劣化したように見える。緩和: BT runner ログに必ず `HOLDOUT_CUT={count}` を出す。
- **R2 — production bypass**: live trading は `data/cache/` を読まずに OANDA API から直接取るため影響なし。LIVE pipeline が cache parquet を **間接的に** 読む経路がないことを `grep -r "data/cache" modules/ live_*.py` で確認すること (本タスクのチェック項目)。

# 5. Sibling task

これは Top 4 (NSG-1) と独立。並列 dispatch 可。

# 6. Verification commands

```bash
pytest tests/test_holdout_guard.py -v
ruff check modules/data.py tools/audit/holdout_validation_runner.py
pre-commit run --all-files
python3 tools/audit/holdout_validation_runner.py --help
grep -rn "data/cache" modules/ live_*.py 2>/dev/null  # LIVE pipeline 影響評価
```
