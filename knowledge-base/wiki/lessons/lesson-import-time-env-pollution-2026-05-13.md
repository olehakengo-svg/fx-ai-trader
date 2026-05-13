# 2026-05-13 — Import-time env pollution leaks BT_MODE into pytest

## TL;DR
CLI ツール `tools/regime_gate_full_bt.py` がモジュールトップで
`os.environ.setdefault("BT_MODE", "1")` を実行していた。
`tests/test_regime_gate_full_bt.py` がこのモジュールを import した瞬間に
`BT_MODE=1` が pytest プロセス全体に漏れ、`tests/test_bt_data_loader_parquet_fallback.py` と
`tests/test_fetch_ohlcv_bt_mode.py` の online-first フェイルオーバ順序を検証する 3 テストを破壊した。

→ pre-commit (`pytest tests/ -x -q`) が無関係な commit を全部ブロックする状態に。

## Why this is dangerous
1. **テスト失敗の表面と原因が完全に分離する** — Pine overlay 用の commit が、
   1 ヶ月前にマージされた regime ツールの env-setup で落ちる。
2. **pytest の収集順序に依存する** — `pytest tests/X.py tests/Y.py` のように
   ファイルを明示すれば通り、`pytest tests/` だと落ちる。原因特定が極めて難しい。
3. **`--no-verify` への誘惑が生まれる** — 「自分の変更と関係ないテストが落ちてる」と
   判断して hook をバイパスする習慣が育つ（lesson-2026-05-07-stale-test-cleanup と同型）。
4. **monkeypatch.setenv では救えない** — テスト関数内で setenv/delenv しても、
   コレクション時 import が既に環境を汚した後。

## Root cause pattern
```python
# tools/regime_gate_full_bt.py (module top)
os.environ.setdefault("BT_MODE", "1")             # ← 副作用
os.environ.setdefault("BT_REQUIRE_MASSIVE_CACHE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

def main(): ...
```
`if __name__ == "__main__":` ガードが無いので、ライブラリとして import された場合も実行される。

## Fix
副作用を `if __name__ == "__main__":` ブロックに退避（commit `8dc7502e`）:
```python
if __name__ == "__main__":
    # Script-only env setup: do not pollute env when imported as a library
    os.environ.setdefault("BT_MODE", "1")
    os.environ.setdefault("BT_REQUIRE_MASSIVE_CACHE", "1")
    os.environ.setdefault("NO_AUTOSTART", "1")
    raise SystemExit(main())
```
検証: `pytest tests/ -q` → **1442 passed, 1 xfailed, 0 failed**（3 件回復）。

## Generalization: `tools/` script discipline
`tools/*.py` は CLI として実行されるだけでなく、テストや他ツールから import されうる。
モジュールトップで以下を**やってはいけない**:

| Anti-pattern | 影響 |
|---|---|
| `os.environ.setdefault(...)` | プロセス全体に漏れる |
| `os.chdir(...)` | 他のテストの相対パスを破壊 |
| `logging.basicConfig(...)` | root logger を pytest と取り合う |
| `argparse.parse_args()` | import 時に sys.argv を解釈して即死 |
| DB/API クライアントの auto-connect | テストがネットワーク依存に |
| `threading.Thread(...).start()` | テスト終了後もスレッド残留 |

すべて `if __name__ == "__main__":` または `def main():` に閉じ込める。

## Detection technique (bisection)
症状: `pytest tests/` で X が落ちるが、`pytest tests/X.py` 単独では通る。
- 半分に分割 → 落ちる側を更に半分 → どの test_*.py の import が汚染源かを特定。
- 汚染候補が見つかったら `python3 -c "import target_module"` の前後で `os.environ` を diff。

## Prevention（運用ルール）
1. **`tools/` の新規スクリプトは `if __name__ == "__main__":` ガードを必須**にする。
   - `lib/` / `modules/` と違い、`tools/` はスクリプト前提だが import もされうる二重性がある。
2. **PR レビュー**: `tools/*.py` 差分にモジュールトップの `os.environ`, `os.chdir`, `argparse.parse_args`,
   `Thread.start` があれば指摘。
3. **将来的**: pre-commit に「`tools/*.py` のモジュールトップで `os.environ` がある」を検出する
   小型 linter を追加検討（過剰対応の懸念があるので必要時のみ）。

## Related lessons
- `2026-05-07-stale-test-cleanup.md` — 同じく pre-commit ブロック → `--no-verify` 習慣化を防ぐ動機
- `lesson-reactive-changes.md` 系列 — 表面症状 (テスト失敗) と根本原因 (import 時副作用) の分離

## Evidence
- 失敗: `tests/test_bt_data_loader_parquet_fallback.py::test_fetch_ohlcv_uses_parquet_after_online_failures` 他 2 件
- 根本原因 commit: 既存（`tools/regime_gate_full_bt.py` 初版から存在）
- 修正 commit: `8dc7502e fix(tools): regime_gate_full_bt env-setup leaks BT_MODE into pytest [rule:R3]`
- 修正前: 1439 passed + 3 failed → 修正後: 1442 passed + 1 xfailed
