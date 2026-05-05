---
id: 20260505-1810-w4-meta-C-15m-usd_jpy-retry
title: "[W4-Meta C-mini retry] USD_JPY_15m parquet 生成"
owner: codex
status: queued
priority: P0
created_at: 2026-05-05T18:10:00+0900
roadmap_gate: "前回 USD_JPY 1600 が container restart で orphan、retry"
rule: R3
prereq_artifacts:
  - tools/bt_data_cache.py
  - modules/data.py
related:
  - .ai/tasks/done/20260505-1602-w4-meta-C-15m-eur_usd.md
  - .ai/tasks/done/20260505-1603-w4-meta-C-15m-gbp_usd.md
---

# 0. 重要前提 (前回失敗から学習)

- 前回 USD_JPY task は 30+ 分 running 後 orphan
- 期間中に他 pair (GBP_USD/EUR_USD/EUR_GBP) agents が `modules/data.py` の `max_pages` bug を **既に修正** (動的計算化)
- 現状 `fetch_ohlcv_massive("USD_JPY", "15m", days=4500)` は API 経路で完走可能なはず

このタスクでは **modules/data.py を変更しない** こと。既存修正を信頼してそのまま使う。

# 1. 仕様 (高速最小実装)

```python
import os
from modules.data import fetch_ohlcv_massive
import pandas as pd
from pathlib import Path

target = Path("data/cache/massive/USD_JPY_15m.parquet")

# Step 1: 既存 parquet 確認
if target.exists():
    df_existing = pd.read_parquet(target)
    n = len(df_existing)
    if n > 200000 and df_existing.index.min().year < 2015:
        print(f"既存 USD_JPY_15m が full 12 年 ({n} rows) → 何もしない")
        exit(0)

# Step 2: API 直接 fetch
df = fetch_ohlcv_massive("USD_JPY", "15m", days=4500)

# Step 3: 期間検証
assert df.index.max() > pd.Timestamp("2026-04-01", tz="UTC")
assert df.index.min() < pd.Timestamp("2014-12-31", tz="UTC")
assert len(df) > 200000

# Step 4: 保存 + commit
df.to_parquet(target)
print(f"USD_JPY_15m saved: {len(df)} rows")
```

# 2. Implementation Steps (一発完結)

## Step 1: 既存 USD_JPY_15m.parquet check

サイズ + 期間で既に十分なら STOP (no-op で完了)。

## Step 2: API 直接 fetch (modules/data.py 修正不要)

current `fetch_ohlcv_massive` で 4500 日 fetch。既存の max_pages 動的計算が有効。

## Step 3: 検証 + 保存

rows >= 200k, end >= 2026-04-01, start <= 2014-12-31。

## Step 4: commit

`feat(cache): add USD_JPY_15m parquet via Massive API`

# 3. Acceptance

- `data/cache/massive/USD_JPY_15m.parquet` が full 12 年 (>= 200k rows)
- API 経由の旨を commit message に明記
- 5 分以内に完結 (container restart 前)

# 4. Out of Scope

- modules/data.py 修正 (前回 agent が既に修正済、変更禁止)
- pagination logic 改修
- 他 pair 生成
- BT 実行

# 5. Notes

- **5 分以内完結を最優先**: 余計な work (test 追加、refactor 等) 禁止
- 既存 parquet が old 1 年版なら overwrite OK
- API 経路で fail なら resample fallback (5m parquet → 15m) で OK
