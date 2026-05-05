---
id: 20260505-1100-w4-meta-A-bt-massive-first-patch
title: "[W4-Meta A] BT_MODE=1 で MASSIVE parquet を first source にする structural patch"
owner: codex
status: queued
priority: P0
created_at: 2026-05-05T11:00:00+0900
roadmap_gate: "W4-Redesign 72 件 mass batch を再開する前に production BT path bug を修正"
rule: R3
prereq_artifacts:
  - knowledge-base/wiki/decisions/bt-massive-default-2026-05-05.md
  - modules/data.py
  - app.py
related:
  - knowledge-base/wiki/lessons/feedback_partial_quant_trap.md
---

# 0. なぜこのタスクか

W4-Meta investigation で **構造バグ** が確定:
`fetch_ohlcv()` の試行順序 (`modules/data.py:740,752`) が:

```
1. live Massive API (要 API key)
2. OANDA
3. TwelveData
4. Yahoo Finance ← 60日制限
5. local MASSIVE parquet ← ここに到達しない
```

**Rule 3 (Immediate / 構造バグ)** 該当: 365d BT が Yahoo 60d 制限で完走不可になる。これが W4P1 で焦点リサンプル代替を強いられた原因。

仕様 spec: `knowledge-base/wiki/decisions/bt-massive-default-2026-05-05.md` (W4-Meta task で作成済み)。

# 1. 仕様

環境変数 `BT_MODE=1` のとき、`fetch_ohlcv()` の試行順序を:

```
1. local MASSIVE parquet (data/cache/massive/{PAIR}_{TF}.parquet)
2. live Massive API
3. OANDA
4. TwelveData
5. Yahoo Finance (最終 fallback)
```

`BT_MODE=0` または unset のとき: 現行通り (live 経路優先)。

理由:
- BT は再現性が必須 (毎回 cache から読む)
- live 経路は他システムと同じ window 制限を受ける
- Yahoo は 60d 制限で 365d BT に不適

# 2. Implementation Steps (TDD)

## Step 1: 失敗テスト追加

`tests/test_fetch_ohlcv_bt_mode.py`:
```python
def test_bt_mode_uses_local_massive_parquet_first(monkeypatch, tmp_cache):
    # BT_MODE=1 のとき local parquet が先に試される
    # live Massive API mock が呼ばれないことを assert

def test_bt_mode_off_uses_live_first():
    # BT_MODE=0 のとき従来順序

def test_bt_mode_yahoo_fallback_only_last():
    # BT_MODE=1 で local parquet 無 → live → ... → Yahoo の順
```

## Step 2: 実装

`modules/data.py` の `fetch_ohlcv()`:
- `BT_MODE = os.environ.get("BT_MODE", "0") == "1"` を取得
- `BT_MODE=True` のとき local parquet (現 line ~752) を最初に試す分岐を追加
- 既存 fallback chain は維持

最小差分で実装 (既存ロジック re-use)。

## Step 3: テスト緑

`pytest tests/test_fetch_ohlcv_bt_mode.py -v`

## Step 4: production BT 経路検証

`BT_MODE=1 python3 -c "from app import run_daytrade_backtest; ..."` で:
- USD_JPY 365d 5m / 15m が Yahoo を経由せず MASSIVE parquet から取得されること
- 既存テスト suite が緑のまま

## Step 5: documentation 更新

- `CLAUDE.md` の「セッション開始プロトコル」または「BT 運用」セクションに `BT_MODE=1` 必須を追記
- `knowledge-base/wiki/analyses/system-reference.md` に BT_MODE 説明追加

## Step 6: Codex self-review

- BT_MODE=0 (production live) で regression なし確認
- BT_MODE=1 で意図通りの順序になっているか
- Yahoo fallback 経路が完全削除されていないか (最終 fallback として残す)

# 3. Acceptance

- 失敗テスト → 緑 (3 件)
- BT_MODE=1 で `run_daytrade_backtest` が MASSIVE 経路を使う
- Documentation 更新
- 既存テスト suite 全緑

# 4. Out of Scope

- USD_JPY_15m parquet 生成 (別 task C)
- W4P1 再 BT (別 task B)
- W4-Redesign 72 件 re-dispatch (本 task 完了後 Claude が実行)

# 5. Notes

- Rule 3 (構造バグ) なので 365d BT スキップ可。修正の数学的正当性は spec で正当化済み
- BT_MODE=1 を default にしない理由: live trading 中に誤って parquet が先に読まれると stale data 問題が発生
- Codex タスクでも今後 BT 系は `BT_MODE=1` を環境変数で明示すること


## Error (2026-05-05T01:28:43Z)

```
orphaned: container restarted while task was running
```
