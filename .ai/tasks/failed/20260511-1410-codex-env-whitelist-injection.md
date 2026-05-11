---
id: 20260511-1410-codex-env-whitelist-injection
title: "[Infra-CodexEnv] Codex companion に .env からの whitelist env injection を実装"
owner: codex
status: queued
priority: P0
created_at: 2026-05-11T14:10:00+0900
roadmap_gate: "Gate 1 (Aggregate Kelly > 0) 前提条件。Wave 1 BT (session-mr-cross) 等の MASSIVE 経由 BT を Codex 単独で完走可能にし、データ整備サイクルを継続的に Codex 側に閉じる"
rule: R3
related:
  - tools/ai_run_codex_companion.sh
  - tools/fetch_massive_data.py
  - modules/data.py
  - .env (read only, never log)
  - .ai/tasks/queue/20260511-1330-session-mr-cross-wave1.md  (前提を解放する対象)
---

# 0. 背景

## 0.1 直前の Codex run (`task-mp0plvo3-nuhv6p`) の結論
- W6-MR-Cross Wave 1 BT は `BLOCKED_PRECONDITION` で停止
- 原因: Codex sandbox に `MASSIVE_API_KEY` が無く、`tools/fetch_massive_data.py` が `ValueError: MASSIVE_API_KEY not set` で fail
- `MASSIVE_API_KEY` は `/Users/jg-n-012/test/fx-ai-trader/.env` に**実在する** (司令塔 2026-05-11 13:57 確認)
- `.env` は `.gitignore` 済 (`.env / .env.* / !.env.example`)

## 0.2 構造的 gap
Codex companion 経由のタスクは **完全に sandbox env で動く**ため、外部 API key を要するタスク (MASSIVE / 将来の他データ API / Sentry write) が一切完走できない。

これは「クオンツが Codex に渡すデータ系タスクが恒久的に部分失敗する」構造欠陥 (R3)。`.env` を丸ごと export するのは security disaster (OANDA Live token / Render API key 等が同居)。

→ **whitelist 方式の env injection** で「Codex に渡してよい env だけ明示的に通す」仕組みを構築する。

---

# 1. 仮説 (Hypothesis)

**H1**: `tools/ai_run_codex_companion.sh` で `.env` から whitelist (`tools/codex-env-whitelist.txt`) に列挙された key のみを export することで、(a) MASSIVE_API_KEY が Codex sandbox に届く、(b) 非 whitelist env (OANDA_API_TOKEN, RENDER_API_KEY, GITHUB_PAT 等) は絶対に届かない、(c) 既存タスク実行が regression しない、の 3 条件を同時に満たせる。

**Null**: whitelist 経由 export しても Codex sandbox は env を見ない / または非 whitelist env が leak する。

---

# 2. 対象データ・分離

| 種別 | 用途 |
|---|---|
| **ローカル `.env`** | 読み取り専用。値はログに**絶対に**出力しない |
| **`tools/codex-env-whitelist.txt`** | リポジトリにコミット (gitignore しない)。key 名のみ列挙 |
| **Codex sandbox subprocess** | export された whitelist env だけ受け取る |

BT / Shadow / Live / OANDA データには一切触らない (infra task)。

---

# 3. 仕様

## 3.1 新規ファイル: `tools/codex-env-whitelist.txt`

key 名 1 行 1 個、コメント `#` 許容:

```
# Codex companion が .env から sandbox に inject してよい env key 列挙
# 追加時は司令塔 (Claude) のレビュー必須。OANDA Live / Render / GitHub secret は絶対追加禁止。
MASSIVE_API_KEY
```

初版は `MASSIVE_API_KEY` のみ。Wave 1 BT が走ることを最優先。

## 3.2 `tools/ai_run_codex_companion.sh` 改修

冒頭 (`cd "$ROOT"` 直後、`export CLAUDE_PLUGIN_DATA=…` の**前**) に env injection ブロックを追加:

```bash
inject_codex_whitelist_env() {
  local whitelist_file="$ROOT/tools/codex-env-whitelist.txt"
  local env_file="$ROOT/.env"
  if [[ ! -f "$whitelist_file" ]]; then return 0; fi
  if [[ ! -f "$env_file" ]]; then return 0; fi

  local key val
  while IFS= read -r line || [[ -n "$line" ]]; do
    # 空行・コメント除去
    line="${line%%#*}"
    key="$(echo "$line" | tr -d '[:space:]')"
    [[ -z "$key" ]] && continue
    # whitelist key 形式 check (英大文字+数字+_ のみ)
    if ! [[ "$key" =~ ^[A-Z_][A-Z0-9_]*$ ]]; then
      echo "[codex-env] WARN: ignoring malformed whitelist key '$key'" >&2
      continue
    fi
    # .env から該当 key の値を抽出 (最後の定義を採用、quote 削除)
    val="$(grep -E "^${key}=" "$env_file" | tail -1 | cut -d= -f2- | sed -e 's/^"//;s/"$//' -e "s/^'//;s/'\$//")"
    if [[ -n "$val" ]]; then
      export "$key=$val"
      # 値は絶対にログに出さない。存在のみ報告
      echo "[codex-env] injected: $key (len=${#val})" >&2
    fi
  done < "$whitelist_file"
}

inject_codex_whitelist_env
```

実装規律:
- **API key 値はログ・stdout に絶対出力しない** (`len=N` の長さ報告までは許容)
- whitelist にない key は無視 (`.env` に書いてあっても export しない)
- key 名フォーマット (`^[A-Z_][A-Z0-9_]*$`) で injection を防御
- `set -euo pipefail` 環境で動作すること

## 3.3 テスト (`tests/test_codex_env_whitelist.py`)

最低 7 ケース:

1. **whitelist key が `.env` にある場合 → export される** (subprocess で `bash -c 'source tools/ai_run_codex_companion.sh.injector; echo $MASSIVE_API_KEY'` で確認 / または injector を別関数化して直接 sourceable に)
2. **whitelist にない key が `.env` にある場合 → export されない** (例: `OANDA_API_TOKEN` が `.env` にあっても sandbox env に出ない)
3. **whitelist にある key が `.env` に無い場合 → export されない & error なし**
4. **whitelist ファイル不在 → no-op で正常終了**
5. **`.env` ファイル不在 → no-op で正常終了**
6. **malformed whitelist line (例: `SOME-KEY` / `1KEY`) → warning + skip** (export されない)
7. **API key 値が log に出ない** (subprocess stderr capture、whitelist key の値が出現しないことを assert)

テスト実装方針:
- `pytest tmp_path` で隔離 `.env` / whitelist を作成
- shell script を test subprocess で実行
- production `.env` は触らない (テストは tmp 環境のみ)

オプション (推奨): `tools/codex_env_inject.sh` として injector ロジックを **別ファイル化** し、`ai_run_codex_companion.sh` から `source` する。これでテスト容易性↑。

## 3.4 Documentation 更新

- `AGENTS.md` (リポ root) に 1 セクション追加:
  - 「Codex に外部 secret を渡す手順」
  - whitelist に追記する際の司令塔承認プロセス
  - 値は絶対に commit しない / log 出力しない / Codex 出力に echo しない
- 該当 commit に `feat(codex): add whitelist env injection for companion [rule:R3]` 形式

## 3.5 Regression 確認

`tools/ai_run_codex_companion.sh --list` が改修前後で**同じ出力**になること (env injection は launch 時のみ動き、`--list` は影響なし)。

実行: 改修前後の `--list` を diff、差分が空であることを report に記載。

---

# 4. ACCEPT / NEEDS_MORE_EVIDENCE / REJECT

## ACCEPT
**すべて満たす**:
1. `tests/test_codex_env_whitelist.py` の 7 ケース全 pass
2. `python3 -m pytest tests/ -x -q` regression なし (既存 1391 passed を維持)
3. `tools/ai_run_codex_companion.sh --list` の出力が改修前後で identical
4. 改修後の launcher で本タスクと**全く別の dry-run 確認**: `MASSIVE_API_KEY` のみ subprocess の env に届き、`OANDA_API_TOKEN` 等は届かないことを runtime ログ (subprocess の `printenv | sort` 出力) で確認
5. API key 値が**いかなる log / stdout / stderr にも出現しない** (test 7 で担保)
6. `scripts/check.py` PASS

## NEEDS_MORE_EVIDENCE
- 上記 1-3 PASS、4 が**部分的**: MASSIVE 届くが他 env の leak テストが弱い → leak テスト追加で再確認

## REJECT
- 非 whitelist env が leak (security incident、即 abort)
- 既存 launcher の `--list` / `--help` / 既存 job 起動が壊れた (regression)
- API key 値が log に出る

REJECT 時は commit せず `changes_requested` で司令塔へ。

---

# 5. 月利100%ロードマップへの寄与

**進める Gate**: Gate 1 (Aggregate Kelly > 0) の**前提インフラ**。

直接的な edge 寄与ではないが、

- W6-MR-Cross Wave 1 BT を Codex 単独で完走可能にする (本タスク完了後すぐ session-mr-cross Wave 1 を re-trigger)
- 今後の MASSIVE 経由データ取得タスクが全て Codex 自己完結化 (司令塔のローカル fetch 介入が不要に)
- security 規律を保持したまま外部 API 連携 (Sentry / Render / 他 data provider) を後から拡張する基盤を提供

これは Codex companion インフラの構造欠陥 (R3) 修正であり、データ駆動ワークフローの bottleneck 解消。

---

# 6. 検証コマンド (Codex が実行)

```bash
# 1. 新規テスト
python3 -m pytest tests/test_codex_env_whitelist.py -x -v

# 2. 既存テスト regression
python3 -m pytest tests/ -x -q

# 3. 改修前後の --list 差分 (改修前 = git stash 状態 / 改修後 = unstaged 状態)
# Codex は適宜 git worktree or compare with main HEAD で確認

# 4. ランタイム leak test (Codex が手動で確認)
#    一時 .env を作成し、whitelist + 非whitelist の値を入れて
#    bash -c 'source tools/codex_env_inject.sh; printenv | sort' で
#    whitelist key のみ存在、非 whitelist key 不在を assert
python3 - <<'PY'
import os, subprocess, tempfile, pathlib
# spec の test 7 と同じ仕組みを inline で再現し、leak がないこと確認
# 詳細実装は tests/test_codex_env_whitelist.py を参照
PY

# 5. scripts/check.py
python3 scripts/check.py
```

---

# 7. 受け入れ条件 (Codex 完了報告に必須)

1. 新規 `tools/codex-env-whitelist.txt` (`MASSIVE_API_KEY` のみ列挙、コメント付)
2. `tools/ai_run_codex_companion.sh` 改修 (injection ブロック追加)
3. (オプション、推奨) `tools/codex_env_inject.sh` への分離
4. `tests/test_codex_env_whitelist.py` 新規 7 ケース 全 pass
5. `AGENTS.md` への運用 doc 追記
6. 既存 1391 tests + 1 xfailed regression 無し
7. `--list` 出力が改修前後で identical
8. API key 値が一切ログに出ない (test 7 で証明)
9. **commit するが push しない**。司令塔のレビュー後に手動 push

---

# 8. 禁止事項

- **`.env` の内容を log / commit / Codex 出力に echo 禁止**
- **OANDA_API_TOKEN / OANDA_ACCOUNT_ID / RENDER_API_KEY / GITHUB_PAT / SENTRY_AUTH_TOKEN 等を whitelist に追加禁止** (本タスクは MASSIVE_API_KEY のみ)
- **`tools/codex-env-whitelist.txt` に値を書かない** (key 名のみ)
- **既存 `.env` ファイルの編集・上書き禁止**
- **本番 OANDA / Live DB への接続禁止**
- **`modules/demo_trader.py` 変更禁止**
- **既存未コミット変更を上書きしない** (`git status` で確認)
- **`/Users/jg-n-012/.claude/plugins/cache/openai-codex/codex/1.0.3/scripts/codex-companion.mjs` の改変禁止** (プラグイン側ファイル、fx-ai-trader リポ外)
- **CI 経由で `.env` を git に commit しない** (`.gitignore` を維持)

---

# 9. 完了後の司令塔アクション

1. diff レビュー (security 観点で重点的に)
2. ローカルで `tools/ai_run_codex_companion.sh 4` (session-mr-cross-wave1) を**再キック**
3. Codex が今度は MASSIVE fetch を完走できることを確認
4. push を承認

---

**司令塔承認**: 2026-05-11 14:10 JST (Claude as Quant)
**Codex 着手承認待ち**: queued


## Error (2026-05-11T07:22:31Z)

```
orphaned: container restarted while task was running
```
