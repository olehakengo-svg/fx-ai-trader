---
id: 20260505-1331-w4-meta-C-massive-15m-cache-generation-retry
title: "[W4-Meta C retry] 15m parquet cache 生成 (API 優先 + resample fallback)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T13:31:00+0900
roadmap_gate: "W4-Redesign 70 件 (shadow-redesign) 再開の前提条件"
rule: R3
prereq_artifacts:
  - knowledge-base/wiki/analyses/w4-redesign-bt-spec-2026-05-05.md
  - tools/bt_data_cache.py
  - data/cache/massive/
related:
  - modules/data.py
---

# 0. なぜこのタスクか

worker side の `data/cache/massive/` に 15m parquet が無い (gitignore で push されない、env-local cache)。
shadow-redesign の strict BT (`BT_REQUIRE_MASSIVE_CACHE=1`) で REJECT 多発の根本原因。

W4P1 task が orphan で fail、retry。

# 1. 戦略 (二段階 fallback)

## Step 1: MASSIVE API 経由生成 (推奨)

`MASSIVE_API_KEY` 環境変数 が利用可能なら:
```python
from modules.data import fetch_ohlcv_massive
df = fetch_ohlcv_massive("USD_JPY", "15m", days=4500)  # ~12 年
df.to_parquet("data/cache/massive/USD_JPY_15m.parquet")
```

API rate limit 配慮 (per-pair 1-3 秒 sleep)。

## Step 2: 5m → 15m resample fallback

`MASSIVE_API_KEY` 未設定 or API エラー時:

```python
df_5m = pd.read_parquet("data/cache/massive/USD_JPY_5m.parquet")
df_15m = (df_5m.resample("15min", label="right", closed="right")
                .agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"})
                .dropna())
df_15m.to_parquet("data/cache/massive/USD_JPY_15m.parquet")
```

ただし **broker bar 境界とのズレ可能性** を warning として `knowledge-base/raw/bt-results/massive-15m-cache-generation-2026-05-05.md` に明記。

## Step 3: 5m parquet も無い場合

REPORT_BLOCKED — user に `MASSIVE_API_KEY` を Render dashboard で設定要請。

# 2. 対象 pair

W4-Redesign で 15m を使う pair:
- USD_JPY, GBP_JPY, EUR_USD, GBP_USD, EUR_JPY, EUR_GBP

(AUD_USD は cache 状態確認後に追加判断)

# 3. Implementation Steps

## Step 1: 既存 cache 状態確認

```bash
ls -la data/cache/massive/*_15m.parquet
ls -la data/cache/massive/*_5m.parquet
```

各 pair の 15m, 5m 有無 + 期間 (start/end date) を確認。

## Step 2: MASSIVE_API_KEY 確認

```python
import os
has_key = bool(os.environ.get("MASSIVE_API_KEY"))
```

True → Step 3a (API)、False → Step 3b (resample)、5m もない → Step 4 (REPORT_BLOCKED)

## Step 3a: API 経由生成 (各不足 pair)

`fetch_ohlcv_massive()` で 4500 日分取得 → Parquet 保存。
schema: Datetime, Open, High, Low, Close, Volume (既存 5m / 1h と整合)

## Step 3b: 5m → resample fallback

5m parquet → 15m に集約 → Parquet 保存。
warning として generation report に「resample-derived, broker-tick boundary may differ ±1 bar」を記録。

## Step 4: 検証

各生成 parquet について:
- N (bar count) 妥当性 (15m なら ~35040 bars/年)
- start/end date 期待範囲
- OHLC 値が NaN でない
- pandas で読み込めるか

## Step 5: BT 軽量サンプル

`BT_MODE=1 BT_REQUIRE_MASSIVE_CACHE=1` で USD_JPY 15m を読み、Yahoo 経路に逃げないことを確認。

## Step 6: Codex self-review

- API rate limit 守ったか
- resample fallback の場合 warning 適切か
- 既存 BT テスト regression なし

# 4. Acceptance

- USD_JPY_15m, GBP_JPY_15m, EUR_USD_15m, GBP_USD_15m, EUR_JPY_15m, EUR_GBP_15m の parquet が `data/cache/massive/` に存在
- 各期間 >= 1095 日 (3 年) ideally 4000+ 日
- API 経由 vs resample のいずれを使ったか + warning を `massive-15m-cache-generation-2026-05-05.md` に記録
- 既存 BT テスト緑

# 5. Out of Scope

- 1m parquet, 4h, D1 補完
- BT 経路 path patch (Task A)
- Shadow promote 判定

# 6. Notes

- `data/cache/` は .gitignore 範囲なので生成した parquet は git に含まれない (worker のローカル fs に保持)
- worker container restart で消える可能性 — 各 shadow-redesign task が generate-if-missing する責任を負う設計を別途検討 (本 task の Out of Scope だが提案として記録 OK)
- 長期解: `MASSIVE_API_KEY` を Render `fx-ai-trader-codex-runner` service の secret に追加 (user dashboard 操作)
