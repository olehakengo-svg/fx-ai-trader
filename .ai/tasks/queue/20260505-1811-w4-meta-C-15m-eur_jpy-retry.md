---
id: 20260505-1811-w4-meta-C-15m-eur_jpy-retry
title: "[W4-Meta C-mini retry] EUR_JPY_15m parquet 生成"
owner: codex
status: queued
priority: P0
created_at: 2026-05-05T18:11:00+0900
roadmap_gate: "前回 EUR_JPY 1604 が container restart で orphan、retry"
rule: R3
prereq_artifacts:
  - tools/bt_data_cache.py
  - modules/data.py
related:
  - .ai/tasks/done/20260505-1602-w4-meta-C-15m-eur_usd.md
---

# 0. 重要前提

- 前回 EUR_JPY task が container restart で orphan
- `modules/data.py` の `max_pages` bug は他 pair tasks で **既に修正済**
- このタスクでは `modules/data.py` を変更しない

# 1. 仕様 (高速最小実装)

```python
import os
from modules.data import fetch_ohlcv_massive
import pandas as pd
from pathlib import Path

target = Path("data/cache/massive/EUR_JPY_15m.parquet")

# 既存 check
if target.exists():
    df_existing = pd.read_parquet(target)
    if len(df_existing) > 200000 and df_existing.index.min().year < 2015:
        print(f"既存 EUR_JPY_15m が full 12 年 → 何もしない")
        exit(0)

# API fetch
df = fetch_ohlcv_massive("EUR_JPY", "15m", days=4500)
assert df.index.max() > pd.Timestamp("2026-04-01", tz="UTC")
assert df.index.min() < pd.Timestamp("2014-12-31", tz="UTC")
assert len(df) > 200000

df.to_parquet(target)
```

# 2. Steps

1. 既存 parquet check
2. API fetch (modules/data.py 既存実装利用、修正禁止)
3. 検証
4. 保存 + commit

# 3. Acceptance

- `data/cache/massive/EUR_JPY_15m.parquet` が full 12 年 (>= 200k rows)
- 5 分以内に完結

# 4. Out of Scope

- modules/data.py 修正
- 他 pair
- BT

# 5. Notes

- **5 分以内完結を最優先**
- API 経路で fail なら resample fallback (5m parquet → 15m)
