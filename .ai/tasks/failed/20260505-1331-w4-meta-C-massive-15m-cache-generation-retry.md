---
id: 20260505-1331-w4-meta-C-massive-15m-cache-generation-retry
title: "[W4-Meta C] MASSIVE 15m parquet cache 生成 (USD_JPY, GBP_JPY 他)"
owner: codex
status: queued
priority: P1
created_at: 2026-05-05T11:01:00+0900
roadmap_gate: "W4-Redesign 72 件のうち 15m TF を使う戦略 (streak_reversal 等) の strict BT 必須前提"
rule: R3
prereq_artifacts:
  - knowledge-base/wiki/analyses/w4-redesign-bt-spec-2026-05-05.md
  - tools/bt_data_cache.py
  - data/cache/massive/
related:
  - modules/data.py
---

# 0. なぜこのタスクか

W4-Meta investigation で発覚: 現 MASSIVE cache は **5m と 1h のみ完備、15m は欠落** している pair が多い。

```
data/cache/massive/USD_JPY_5m.parquet  ✓ 2014-2026
data/cache/massive/USD_JPY_15m.parquet ✗ 欠落
data/cache/massive/USD_JPY_1h.parquet  ✓
data/cache/massive/GBP_JPY_5m.parquet  ✓
data/cache/massive/GBP_JPY_15m.parquet ?
```

15m TF は many strategies の primary TF (streak_reversal, doji_breakout, ema200_reversal 等)。BT を strict に再現するためには 15m parquet が必要。

# 1. 仕様

`tools/bt_data_cache.py` の経路で生成:

## オプション A: MASSIVE API から直接取得 (推奨)

```python
from modules.data import fetch_ohlcv_massive
df = fetch_ohlcv_massive("USD_JPY", "15m", days=4500)  # ~12 年
df.to_parquet("data/cache/massive/USD_JPY_15m.parquet")
```

## オプション B: 5m から resample (fallback)

MASSIVE API key 不在時のみ:
```python
df_5m = pd.read_parquet("data/cache/massive/USD_JPY_5m.parquet")
df_15m = df_5m.resample("15min", label="right", closed="right").agg({
    "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
}).dropna()
df_15m.to_parquet("data/cache/massive/USD_JPY_15m.parquet")
```

ただし resample は production の 15m bar と完全等価でない可能性 (broker tick の境界が異なる)。MASSIVE API 経由を強く推奨。

## 対象 pair

W4-Redesign で 15m を使う pair (audit から推定):
- USD_JPY, GBP_JPY, EUR_USD, GBP_USD, EUR_JPY, EUR_GBP, AUD_USD

# 2. Implementation Steps

## Step 1: 既存 cache 状態確認

```bash
ls -la data/cache/massive/*_15m.parquet
```

各 pair の 15m parquet 有無 + 期間 (2014-2026 が必要、365d なら最低 3 年以上欲しい)。

## Step 2: API 経路確認

`MASSIVE_API_KEY` 環境変数が利用可能か。Codex 環境で setup されている前提だが、不在なら resample fallback。

## Step 3: 不足 pair の 15m parquet 生成

存在しない pair について:
- API 経由で 4500 日分 (12 年) 取得
- `data/cache/massive/{pair}_15m.parquet` に保存
- 期間検証: start_date < 2014-12-31, end_date > 2026-04-01

## Step 4: resample との等価性検証 (sanity check)

5m → resample 15m と直接 API 取得 15m を比較:
- N (bar count) が ±5% 以内
- OHLC 各 bar の値が一致 (or 小数点誤差以内)

差分が大きい場合は API 経路を採用、resample を warning 付きで記録。

## Step 5: 検証 BT サンプル

`BT_MODE=1` で USD_JPY 15m を読み、`run_daytrade_backtest` が完走することを確認 (Task A 完了後)。

## Step 6: Codex self-review

- API rate limit 配慮 (per-pair sleep 1-3 秒)
- Parquet schema が既存 5m / 1h と整合
- 既存 tests に regression なし

# 3. Acceptance

- USD_JPY_15m, GBP_JPY_15m, EUR_USD_15m, GBP_USD_15m, EUR_JPY_15m, EUR_GBP_15m, AUD_USD_15m の parquet が存在
- 各期間 >= 1095 日 (3 年)、ideally 4000+ 日
- API 経由 vs resample のいずれを使ったか `knowledge-base/raw/bt-results/massive-15m-cache-generation-2026-05-05.md` に記録
- 既存 BT テスト緑

# 4. Out of Scope

- 1m parquet 生成 (本 task は 15m 限定)
- 他 TF (1h, 4h, D1) 補完
- production BT path patch (Task A)
- W4P1 再 BT (Task B)

# 5. Notes

- API 経路 fail なら resample で代替可だが、warning 付きで記録
- MASSIVE_API_KEY が Codex 環境にない場合は env 確認 + 設定方法を記録 (Render secret 必要)
- Task A が完了していなくても本 task は実行可 (cache 生成は独立)


## Error (2026-05-05T01:38:09Z)

```
orphaned: container restarted while task was running
```


## Error (2026-05-05T02:37:21Z)

```
orphaned: container restarted while task was running
```
