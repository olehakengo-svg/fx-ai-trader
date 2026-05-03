---
id: 20260503-1745-r3-bt-wrapper-fingerprint-aggregate-gate
title: R3 — BT wrapper fingerprint + aggregate stale-artifact refusal gate (prevents Codex's exact stale-bb_squeeze trap)
owner: codex
status: queued
priority: P1
created_at: 2026-05-03T17:45:00+0900
roadmap_gate: Gate 0 (生存 — BT decision pipeline integrity / verdict pollution prevention)
rule: R3
---

# Objective

`tools/scalp_alt_pre_reg_bt.py` `tools/scalp_re_enable_bt.py` `tools/vec_harness_chunked_cli.py` の3 BT wrapperに **wrapper fingerprint** (関連ロジックの内容ハッシュ) を埋め込み、`--aggregate` 時に **全候補JSONのfingerprintが現wrapperと一致** しなければ集約を拒否する R3 構造ゲートを追加する。これにより、A2-alt で実際に発生した「pre-fix wrapperの汚染JSONが post-fix wrapper の集約に混入しかける」trap を機械的に閉じる。**プロモーション判定や戦略パラメータには触らない**。

# 仮説 (検証対象)

H1 — Wrapperが PnL/win-loss 計算ロジックを変更したとき、変更前に書かれたJSONを変更後の集約器が読み込むと、誤った verdict (stale-aggregation) が出る。これは A2-alt 実行で再現済み (`bb_squeeze_breakout` JSON が pre-fix wrapperで生成され、post-fix wrapper の集約 input にまだ残置されている)。

H2 — Wrapperの「PnL抽出関数 + LOCKED constants + Bonferroni K + Verdict thresholds」のSHA-256をJSONに埋め、集約時にcurrentと比較すれば、当該traを exit code != 0 で確実にブロックできる。集約には影響しない他のJSON (例: vec_harness equivalence report) は対象外として明示的にskipできる。

H1+H2 が成立すれば、Gate 0 (BT decision pipeline integrity) の固有risk class (stale wrapper artifact pollution) が永久に閉じる。

# Context — なぜ今このタスクか

- A2-alt run (`task-mopi16mh-62gjsn`) で wrapper PnL bug を pytest で発見 → fix → だが pre-fix で生成された `scalp-alt-bb_squeeze-2026-05-03.json` (191KB, mtime 17:20) が disk に残置。fix 後の wrapper (mtime 17:22) で `--aggregate` を走らせると、汚染データを混ぜたまま verdict を出してしまう経路が存在する。
- 今回は parent Claude の review が手動で stale を発見したが、構造ゲートが無いため**次のセッションでは見逃す可能性が高い**。
- 同じ class のロジック分岐は `scalp_re_enable_bt.py:197 extract_trade_pnl` と `scalp_alt_pre_reg_bt.py:148 extract_trade_pnl` で**実際に divergent** (前者は `pnl_pips` フォールバック、後者は `tp_m` / `actual_sl_m` ベース)。つまり wrapper-vs-wrapper drift も検出可能にすべき。
- 教訓 `feedback_label_empirical_audit` `feedback_partial_quant_trap` の延長線。「stale data with the right schema」は silent contamination の主因。

# Scope

Codex MAY change:

- `tools/bt_common.py` (NEW) — `compute_wrapper_fingerprint(target_module: str | Path) -> str` (SHA-256 hex, ハッシュ対象は次の3要素を `|` 結合した文字列):
  1. wrapper module file の `extract_trade_pnl` / `_pnl` / それ相当の trade-log → PnL 関数の **AST テキスト** (`ast.unparse` 出力)
  2. wrapper module の **LOCKED constants** (定数名 prefix が `BONFERRONI_` または `VERDICT_THRESHOLDS` で始まるもの) を `repr` した文字列
  3. wrapper module の `CANDIDATES` (定義されていれば) を `repr` した文字列
- `tools/scalp_alt_pre_reg_bt.py` — JSON出力に `wrapper_fingerprint: str` (single-candidate 出力時) を追加。 `--aggregate` 時に各候補JSONの fingerprint を `compute_wrapper_fingerprint(__file__)` と比較し、不一致なら **exit 2 + stderr 明示メッセージ** で停止。
- `tools/scalp_re_enable_bt.py` — 同様に JSON出力に `wrapper_fingerprint: str` を追加。
- `tools/vec_harness_chunked_cli.py` — `wrapper_fingerprint` を JSON 出力に追加 (集約 gate は本タスクでは追加しない、書込みのみ)。
- `tests/test_bt_wrapper_fingerprint.py` (NEW) — fingerprint の deterministic 性、AST変更検知、constants変更検知、ハッシュ衝突回避、aggregate refusal の 5 ケース。

Codex MAY NOT change:

- `app.py`、`modules/` 一切、`strategies/` 一切。
- `knowledge-base/wiki/decisions/` `wiki/index.md` `wiki/strategies/` `wiki/learning/` `wiki/tier-master.md` `wiki/syntheses/`。
- 既存のverdict logic、LOCKED thresholds、Bonferroni K、Wilson 計算式。
- `.env` `本番DB` `OANDA secret` `Render API` 一切。
- 既存の uncommitted 変更 (`modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md` 等)。

# Required Reading

- `CLAUDE.md` (Rule 3 protocol)
- `tools/scalp_alt_pre_reg_bt.py:148-200` `extract_trade_pnl` (post-fix版)
- `tools/scalp_re_enable_bt.py:197-208` `extract_trade_pnl` (divergent版 — 注意: 同名関数で分岐)
- `tools/vec_harness_chunked_cli.py:140-180` (trade JSON serialization)
- `app.py:5285-5289` `_pnl` (canonical reference)
- `.ai/runs/20260503-171848-20260503-1700-a2-alt-simple-structure-scalp-pre-reg/final.md` (本traの再現報告)
- `wiki/lessons/index.md` で `feedback_label_empirical_audit` `feedback_partial_quant_trap`

# 対象データ / Data Separation

| 用途 | 出典 | 混入禁止対象 |
|---|---|---|
| wrapper源 | `tools/*.py` ファイル本体 (read-only AST 解析) | 戦略実装、戦略パラメータ |
| ハッシュ計算 | wrapper module の AST + LOCKED constants + CANDIDATES のみ | trade JSON 本体、Live data、Render API |
| 検証対象 | unit test 内の synthetic wrapper モジュール のみ | 既存 BT 結果 JSON の変更 |

本タスクは **既存JSONを変更しない**。fingerprint フィールドは新規wrapper実行の出力にのみ追加される。既存の `bb_squeeze` stale JSON は parent Claude の手で削除/再生成する (これは別タスク)。

# 統計条件

R3 構造タスクのため統計閾値は適用しない。ただし以下を **Codex が自分でテスト** すること:

- AST に空白追加だけ (logically same) → fingerprint 同値 (`ast.unparse` 後比較なので OK)
- `extract_trade_pnl` のロジックを 1 行変更 → fingerprint **必ず** 変化
- LOCKED `VERDICT_THRESHOLDS` の値を 1 つ変更 → fingerprint **必ず** 変化
- `CANDIDATES` の追加/削除 → fingerprint **必ず** 変化
- 関係ない private helper を編集 → fingerprint **不変** (PnL extraction とLOCKED constants のみがハッシュ対象であるべき)

# 採用 / 保留 / 棄却条件

- **ACCEPT**: 5 unit tests 全 pass。`scalp_alt_pre_reg_bt.py --aggregate` を **既存の stale `bb_squeeze` JSON が disk にある状態で実行** → exit 2 + stderr に "wrapper_fingerprint mismatch" 明示。post-fix wrapper で再生成した JSON のみが揃っていれば exit 0 で aggregate 動作。`scalp_re_enable_bt.py` `vec_harness_chunked_cli.py` の出力JSONにも `wrapper_fingerprint` フィールドが含まれる。
- **NEEDS_MORE_EVIDENCE**: fingerprint は実装されたが、stale-aggregation を再現する E2E テストが書けていない。
- **REJECT**: 既存 verdict logic / LOCKED thresholds / Bonferroni K に副作用が出る。`app.py` `modules/` `strategies/` のいずれかが編集されている。

# Roadmap 寄与

Gate 0 (生存) の決定パイプライン integrity 強化。直接的な月利貢献はないが、A2-alt2 / W3-3 rerun / W3-4 rerun など、queue に複数の wrapper-driven BT タスクが積まれている現状で、**1 つの wrapper bug 修正後に他のJSONが古いまま混入する risk を機械的に閉じる**。実質的に Gate 1 unlock の試行回数を安全に増やす infra。

# Acceptance Criteria

- [ ] `tools/bt_common.py` exists, exposes `compute_wrapper_fingerprint(module_path: str | Path) -> str`.
- [ ] 3 wrapper (`scalp_alt_pre_reg_bt.py`, `scalp_re_enable_bt.py`, `vec_harness_chunked_cli.py`) の JSON 出力に `wrapper_fingerprint: str` (16+ hex chars) が含まれる。
- [ ] `tools/scalp_alt_pre_reg_bt.py --aggregate` が **fingerprint 不一致時に exit 2 + stderr 明示メッセージ** で停止する (e.g., `wrapper_fingerprint mismatch: scalp-alt-bb_squeeze-2026-05-03.json was produced by wrapper a1b2c3d4..., current wrapper is e5f6g7h8...`).
- [ ] `tests/test_bt_wrapper_fingerprint.py` の 5 ケース全 pass。
- [ ] `app.py` `modules/` `strategies/` `wiki/decisions/` `wiki/index.md` `wiki/strategies/` 編集 0件。
- [ ] 既存の単一候補BT (`--candidate <name>`) の出力スキーマは backward compat (新フィールド追加のみ、既存フィールドの意味/型変更なし)。
- [ ] `.ai/runs/<run-dir>/final.md` に status / files changed / 5 test 結果 / aggregate refusal の再現コマンド + 出力 / next recommended task を記録。

# Verification Commands

```bash
# 1. Unit tests
python3 -m pytest tests/test_bt_wrapper_fingerprint.py -v

# 2. Wrapper fingerprint determinism (twice → same hash)
python3 -c "from tools.bt_common import compute_wrapper_fingerprint; \
  a = compute_wrapper_fingerprint('tools/scalp_alt_pre_reg_bt.py'); \
  b = compute_wrapper_fingerprint('tools/scalp_alt_pre_reg_bt.py'); \
  assert a == b and len(a) >= 16, (a, b)"

# 3. Stale aggregate refusal (re-creates the A2-alt trap)
#    Pre-condition: scalp-alt-bb_squeeze-2026-05-03.json exists with NO wrapper_fingerprint field
#    or with a fingerprint != current wrapper's hash.
python3 tools/scalp_alt_pre_reg_bt.py --aggregate \
  --output /tmp/_aggregate_should_fail.md
echo "exit=$?"   # 期待: 2

# 4. Single-candidate run produces fingerprint
python3 tools/scalp_alt_pre_reg_bt.py --candidate bb_squeeze_breakout \
  --engine-timeout 600 \
  --output /tmp/_single_candidate.json
python3 -c "import json; d=json.load(open('/tmp/_single_candidate.json')); \
  assert 'wrapper_fingerprint' in d and len(d['wrapper_fingerprint']) >= 16, d.get('wrapper_fingerprint')"

# 5. Existing tests do not regress
python3 -m pytest tests/test_scalp_alt_pre_reg_bt.py -v
```

# Codex Instructions

Work in this repository. **Respect existing uncommitted changes** — do not touch the files listed in **Codex MAY NOT change**, in particular `modules/demo_trader.py`, `knowledge-base/raw/hunt_events/2026-05-02.jsonl`, `knowledge-base/wiki/sessions/2026-05-03-session.md`, and `knowledge-base/raw/cell_deepdive/`.

このタスクは **Rule 3** (構造 / runtime infrastructure) のみ。**戦略 promotion / verdict / threshold / Bonferroni K / wilson 計算 に手を入れない**。

実装ガイダンス:

- `compute_wrapper_fingerprint` は `ast.parse` → `ast.unparse` で AST 正規化してから SHA-256 する。
- ハッシュ対象は `extract_trade_pnl` / `_pnl` / そのwrapperの **PnL → win/loss 変換に関わる関数** の AST に限定する。これにより、コメント追加・空行追加・docstring 修正では fingerprint が変わらず、**ロジック変更でのみ変わる**。
- LOCKED constants は AST 上で `Assign` ノードを検出し、変数名 prefix が `BONFERRONI_` `VERDICT_THRESHOLDS` `CANDIDATES` `PAIR_BEV_WR` のいずれかに該当するものだけを `repr` する。
- 集約 gate は `scalp_alt_pre_reg_bt.py` のみ実装する (他2つは fingerprint **書込み** のみ)。aggregate gate を 3 箇所に分散しない。SRP。
- 既存の単一候補 BT 出力 `--candidate <name>` の JSON スキーマは絶対に変えない (新フィールド追加のみ)。
- `tests/test_bt_wrapper_fingerprint.py` は **synthetic wrapper module** をテストディレクトリに inline 生成して使う。実 wrapper を改造して回るテストは fragile なので避ける。
- 実 wrapper の AST 解析でハッシュ対象が正しく抽出できるかは、`@pytest.mark.parametrize` で 3 wrapper 全てを非空 fingerprint として scan するだけのスモークテスト 1 本で十分。

Do NOT:

- 既存 stale JSON (`scalp-alt-bb_squeeze-2026-05-03.json` 等) を delete / 編集する。本タスクのスコープ外。 parent Claude が別作業で扱う。
- `bonferroni_corrected_p` `wilson_lower` 等の統計計算式に手を入れる。
- `--aggregate` の verdict 集計ロジック自体を変更する (refusal gate のみ追加)。
- LOCKED `VERDICT_THRESHOLDS` の数値を変更する。

最終報告に: status (`ACCEPT|NEEDS_MORE_EVIDENCE|REJECT`)、files changed、5 unit test 結果、stale aggregate refusal の実コマンド + stderr (再現可能性)、 backward compat 確認の証拠、次のタスク推奨。
