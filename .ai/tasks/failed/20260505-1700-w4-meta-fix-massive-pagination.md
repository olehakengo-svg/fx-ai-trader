---
id: 20260505-1700-w4-meta-fix-massive-pagination
title: "[W4-Meta] fetch_ohlcv_massive pagination bug fix (2018-01 で止まる)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T17:00:00+0900
roadmap_gate: "MASSIVE API direct fetch を全期間 (2014-2026) に対応 — 現状 ~4年で止まる"
rule: R3
prereq_artifacts:
  - modules/data.py
related:
  - .ai/tasks/done/20260505-1601-w4-meta-C-15m-gbp_jpy.md
---

# 0. なぜこのタスクか

`fetch_ohlcv_massive("GBP_JPY", "15m", days=4500)` (12 年要求) で API pagination が **2018-01-18 で停止**。User より「API は有料プラン、plan 制限ではない」と確認 (2026-05-05)。

つまり `modules/data.py` の pagination logic に bug。単一 base_url + next_url の loop だと、**一定範囲で next_url が None** になり打ち切られている。

MASSIVE API (Polygon 互換) の典型的な挙動:
- 単一 GET request の **date range には実質的な cap** (e.g., 2-3 年)
- range を超えると `next_url=None` で paginated continuation 不可
- 解: **caller side で date range を chunk に分割 + 個別 fetch + concat**

# 1. 仕様

`fetch_ohlcv_massive(symbol, interval, days)` を以下に修正:

```python
def fetch_ohlcv_massive(symbol, interval, days):
    # ... existing setup ...

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days + 3)

    # Window the request into N-year chunks (e.g., 2 year)
    CHUNK_YEARS = 2
    chunks = []
    cursor = start_dt
    while cursor < end_dt:
        chunk_end = min(cursor + timedelta(days=365 * CHUNK_YEARS), end_dt)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end

    all_rows = []
    for chunk_start, chunk_end in chunks:
        # Existing per-chunk fetch + next_url pagination
        chunk_rows = _fetch_chunk(massive_ticker, mult, timespan,
                                  chunk_start, chunk_end, api_key)
        all_rows.extend(chunk_rows)
        time.sleep(0.5)  # rate limit between chunks

    # Convert to DataFrame as before
    ...
```

`_fetch_chunk` は既存の per-request + next_url loop logic を抽出した helper。

# 2. Implementation Steps (TDD)

## Step 1: 失敗テスト追加

`tests/test_fetch_ohlcv_massive_pagination.py`:
```python
def test_chunked_fetch_full_12_years(monkeypatch):
    # mock _fetch_chunk to return small rows
    # verify chunks are made for 2014-2026 (6 chunks of 2 yr each)
    # verify concat preserves order
def test_chunk_rate_limit_sleep_called():
    # verify time.sleep between chunks
def test_chunk_dedup_overlapping_boundaries():
    # adjacent chunk windows may overlap by 1 bar — dedup by timestamp
```

## Step 2: 実装

`modules/data.py` の `fetch_ohlcv_massive` をリファクタ。
既存 fall-through の logic を helper に抽出 + chunk loop wrapper を追加。

## Step 3: テスト緑

## Step 4: USD_JPY_15m で実 API 試行 (network avail なら)

```python
df = fetch_ohlcv_massive("USD_JPY", "15m", days=4500)
assert df.index.min() < pd.Timestamp("2014-12-31", tz="UTC")
assert df.index.max() > pd.Timestamp("2026-04-01", tz="UTC")
```

API key 不在 or rate limit エラーなら skip + warning log。

## Step 5: Codex self-review

- chunk overlap (時間重複) の dedup 確認
- timezone 混在なし
- rate limit 守る
- 既存 unit テスト regression なし

# 3. Acceptance

- 失敗テスト → 緑 (3 件)
- 実 API で 12 年 fetch 通る (network 利用可能時)
- 既存 BT テスト suite 緑
- C mini tasks (USD_JPY/EUR_USD 等) が API 経路で完成可能になる

# 4. Out of Scope

- 既存 cache の再生成 (本 task では実行しない、別 task で実行)
- 他 API path (OANDA/TwelveData) 改修
- shadow-redesign batch 開始

# 5. Notes

- User 報告: API plan は paid なので permission 制限ではない
- このバグが直ると C mini tasks (現 resample fallback) が API 経路で動く → broker bar 境界完全一致
- 既存 resample fallback は keep (network 不可時用)


## Error (2026-05-05T06:23:00Z)

```
orphaned: container restarted while task was running
```
