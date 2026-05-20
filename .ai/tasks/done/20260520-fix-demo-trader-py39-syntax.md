---
id: 20260520-fix-demo-trader-py39-syntax
title: "[pre-commit hygiene] modules/demo_trader.py:3253 `str | None` (PEP 604) を py3.9 互換に修正、--no-verify 常態化を解消"
owner: codex
status: queued
priority: P2
created_at: 2026-05-20T12:35:00+0900
roadmap_gate: "2026-05-07 stale-test cleanup の lesson (`knowledge-base/wiki/lessons/2026-05-07-stale-test-cleanup.md`) は 10 件全て 2026-05-08 closure 済だったが、その後の編集 (545f6b5e Demote trend_rebound thesis invalid 等) で `modules/demo_trader.py:3253` に **新規 PEP 604 union 構文 (`str | None`)** が混入。ローカル py3.9 で `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'` を起こし pre-commit hook (`pytest tests/ -x -q`) を全 commit で blocked にしている。本 task では当該 line と類似箇所を `Optional[str]` ベースに置換し、`--no-verify` muscle-memory を retire する。"
rule: hygiene
related:
  - modules/demo_trader.py
  - tests/test_api_oanda_stats_range.py        # 失敗 collect 元
  - knowledge-base/wiki/lessons/2026-05-07-stale-test-cleanup.md   # 2026-05-08 closure 同等の作業を再度実施
  - feedback_codex_stash_leak
  - feedback_codex_mock_test_trap
---

# 1. 問題の正確な再現

```bash
.venv/bin/pytest tests/test_api_oanda_stats_range.py
```

エラー:
```
modules/demo_trader.py:457: in <module>
    class DemoTrader:
modules/demo_trader.py:3253: in DemoTrader
    def _eur_base_shock_lock_reason(entry_type: str, open_trades: list[dict]) -> str | None:
E   TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

ローカル Python は 3.9 で、PEP 604 (`X | Y`) は **3.10+ 必須**。`from __future__ import annotations` が file 先頭にあれば runtime 評価を回避できるが、本 file には未導入のため class body 直下で評価されて落ちる。

# 2. 完了条件

## 2.1 必須修正

1. `modules/demo_trader.py` 全行 grep:
   ```bash
   grep -nE '\b(str|int|float|bool|dict|list|tuple|set)\s*\|\s*(None|str|int|float|bool)' modules/demo_trader.py
   ```
   ヒット箇所をすべて `Optional[X]` / `Union[X, Y]` に置換。`from typing import Optional, Union` を import に追加。
2. **代替案**: file 先頭 (line 1) に `from __future__ import annotations` を追加し、PEP 604 を string annotation 化。**こちらを優先** (1 行追加で全行救済、可読性維持)。
3. pre-commit hook がローカル py3.9 で通ることを確認 (`.venv/bin/pytest tests/test_api_oanda_stats_range.py` が collect error なしで走る — テスト自体は別問題で fail 可)。

## 2.2 追加 sanity (regression 防止)

4. `tools/check_no_pep604_until_py310.py` 新規 (簡単な regex grep)。`.git/hooks/pre-commit` または `tests/test_no_pep604_in_class_body.py` に組み込み、本 file の class body で PEP 604 が再混入したら fail。
5. **他の同種 file もスキャン**:
   ```bash
   grep -rnE 'class\s+\w+.*:.*$' --include='*.py' modules/ strategies/ tools/ app.py | wc -l
   ```
   全 .py file で同様の grep を流し、別 file に潜在的に同じ罠があるなら一覧化して final.md に記載 (修正は本 task では行わない、別 task に分割)。

## 2.3 検証

6. `.venv/bin/pytest tests/test_api_oanda_stats_range.py` が **collect error なし** で実行 (テスト pass/fail は問わない)
7. `.venv/bin/pytest tests/ -x -q --co` (collect-only) が clean
8. `git commit` で pre-commit hook が走り、PASS (or 別 test 失敗で blocked なら final.md にその一覧)

# 3. 司令塔ガード

- [ ] **`from __future__ import annotations` 優先**: 1 行で全行救済、minimal diff
- [ ] **runtime check が必要な箇所** (isinstance / dataclass / pydantic) は要警戒、置換でロジックが壊れないこと確認
- [ ] **stash 漏れ禁止**、git status clean で終了 (feedback_codex_stash_leak)
- [ ] **mock-only テスト禁止**: 検証 §2.3 step 6/7 は **実 pytest 実行**で確認 (feedback_codex_mock_test_trap)
- [ ] `--no-verify` で commit してよいのは **pre-existing 別 hook 失敗** がある場合のみ (本 task 主旨である PEP 604 fix 自体は --no-verify なしで commit できる状態を目指す)
- [ ] tests/ 配下の他 test (drift checker / v2 redesign / r2 14cell lock) には触れない、本 task は **demo_trader.py syntax 単体**にスコープ限定

# 4. 期待される副次効果

- `--no-verify` の muscle-memory 解消 (lesson 2026-05-07 の趣旨)
- 今後の Codex Cloud worker task で commit が pre-commit hook により validate される
- 別の py3.10+ syntax 罠が同 file 内に潜在しても regression test で fail

# 5. 想定実行時間

- §2.1 修正 + import 追加: 15 分
- §2.2 regression test: 20 分
- §2.3 検証: 10 分
- **総計**: 45 分以内


## Result (2026-05-20T04:24:42Z)

exit=0 · 175s

```
完了しました。commit 済みです。

Commit: `104c635e Fix demo_trader py39 annotations guard`

変更内容:
- [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py:9) に `from __future__ import annotations` を追加
- [tools/check_no_pep604_until_py310.py](/data/repo/fx-ai-trader/tools/check_no_pep604_until_py310.py:1) を追加
- [tests/test_no_pep604_in_class_body.py](/data/repo/fx-ai-trader/tests/test_no_pep604_in_class_body.py:1) を追加
- [.pre-commit-config.yaml](/data/repo/fx-ai-trader/.pre-commit-config.yaml:10) に local hook を追加

検証:
- `.venv/bin/pytest tests/test_api_oanda_stats_range.py` → `1 passed`
- `.venv/bin/pytest tests/test_no_pep604_in_class_body.py -q` → `1 passed`
- `.venv/bin/pytest tests/ -x -q --co` → `1575 tests collected`
- `.venv/bin/pre-commit run` → existing hook + new hook both `Passed`
- `git commit` 時の pre-commit hook → `Passed`
- `git status --short` → clean

補足:
- この環境では `python3.9` binary は見つからず、`.venv` は Python 3.11.2 でした。
- 指定 class grep count は `204`。
- `modules/ strategies/ tools/ app.py` の py3.9-unsafe PEP 604 スキャンは、future import 済み・quoted annotation を除外した結果、追加修正が必要な別ファイルはありませんでした。
- `.venv/bin/pre-commit run --all-files` は既存の `hip1-holdout-manifest` が all-files 入力を拒否しましたが、通常の staged-file pre-commit と commit hook は pass しています。
```
