---
title: _rt_patch クロスペア価格汚染 — 12件の SL_HIT が USD/JPY 価格で誤決済 (2026-05-11)
date: 2026-05-11
type: lesson
severity: CRITICAL
related: [[lesson-data-source-production-first-2026-04-28]], [[lesson-bt-endpoint-hardcoded]]
---

# _rt_patch クロスペア価格汚染 (2026-05-11)

## 何が起きたか

`/demo-analysis` の Trade Log タブで「pip 表示がおかしい」とユーザー報告。production DB を調べたところ、本日 (2026-05-11) 4:38–4:57 UTC に GBP_USD / GBP_JPY / EUR_JPY の 12 件の SL_HIT が記録され、いずれも `exit_price ≈ 157.147` (USD/JPY 現在値) で決済されていた。

例:
- GBP_USD trade `d76740e5-abe`: entry=1.36xx → exit=157.147 → pnl_pips が桁外れ
- GBP_JPY trade `6e485d7e-110`: entry=205.xx → exit=157.147 → pnl_pips≈-5000 相当
- EUR_JPY trade `fe977117-46e`: entry=170.xx → exit=157.147 → 同様

12 件すべて同一の USD/JPY スポット値で決済され、Equity / DD / Kelly 学習が大幅汚染。`defensive_mode` が誤発動するレベル。

## 根本原因

`modules/data.py:_rt_patch` (line 780-) は 1m/5m DataFrame の最終足 Close/High/Low を `_price_cache` から差し替える設計だが、**`_price_cache` は USD/JPY 専用** (`/api/price?symbol=USD/JPY` endpoint で TwelveData から USD/JPY のみ取得・格納)。にもかかわらず `_rt_patch` は `symbol in _OANDA_SYMBOLS` (= USD/JPY, EUR/USD, GBP/USD, GBP/JPY, EUR/JPY, EUR/GBP, XAU/USD すべて) 全てで `_price_cache` の値を Close に書き込んでいた。

通常時は (2) の OANDA bid/ask が成功するため price が上書きされ顕在化しない。しかし**本日 4:38–4:57 UTC に OANDA 401 (auth 障害) が発生**し、OANDA 経路が全失敗 → (1) の汚染された `_price_cache` 値 (= USD/JPY 157.147) が Close として残り、SLTP-Checker が SL_HIT 判定して 12 件まとめて誤決済した。

時系列:
1. SLTP-Checker (`_check_sltp_realtime`) が `_get_price_for_instrument(GBP_USD)` を呼ぶ
2. 内部で 1m DataFrame を取得 → `_rt_patch(df, "GBPUSD=X", "1m")`
3. (1) で `_price_cache` (USD/JPY=157.147) が 10s 以内 → Close を 157.147 に書換
4. (2) OANDA 401 → スキップ
5. SL ≈ 1.36 < 157.147 → 全部 SL_HIT
6. `close_trade(trade_id, 157.147, "SL_HIT", ...)` が DB に書込み

## 修正

**modules/data.py:_rt_patch** — (1) の `_price_cache` 参照を `symbol in ("USDJPY=X", "JPY=X")` でガード。
他ペアは (2) OANDA → (3) yfinance → (4) parquet の fallback のみを使用する。

```python
# Before
with _cache_lock:
    pc = dict(_price_cache)
if pc.get("ts"):
    ...
    price = float(pc["data"]["price"])

# After
if symbol in ("USDJPY=X", "JPY=X"):
    with _cache_lock:
        pc = dict(_price_cache)
    if pc.get("ts"):
        ...
        price = float(pc["data"]["price"])
```

`_price_cache` がそもそも USD/JPY 専用であるという**前提条件**を symbol guard で明示。

## 失敗モード分析

1. **共有キャッシュの暗黙前提**: `_price_cache` のキーは price (symbol情報なし)。「これは USD/JPY 値」という不変条件がコード内に書かれていなかった
2. **fallback が悪化方向に働いた**: 通常は OANDA→TwelveData の順で安全側に見えるが、OANDA 障害時は逆に「汚染データ→正規データ」順となり、bug が顕在化
3. **テストの盲点**: `_rt_patch` の unit test はあったが「OANDA 障害時の cross-pair 経路」をカバーしていなかった
4. **alerting 不在**: pnl_pips が abnormal な値 (>500p) で SL_HIT したことを検知する gate がなかった

## 再発防止

### 短期 (本コミットで完了)
- [x] symbol guard 追加 (USD/JPY 専用化)
- [x] CHANGELOG + KB 同コミット
- [x] DB cleanup script: `scripts/cleanup_rt_patch_contamination_2026_05_11.py`
- [ ] production DB cleanup 実行 + Equity / DD state reset (post-deploy)

### 中期 (要 follow-up task)
- `_price_cache` を dict 化して symbol を明示 (`{"USDJPY=X": {...}}`)、`_rt_patch` 側で `pc.get(symbol)` を取り出す
- `close_trade` 直前に `|pnl_pips| > 500p` (XAU 除く) の sanity gate を入れ alert + skip persist
- OANDA 401 / 5xx 時の SLTP-Checker 動作を unit test で固定化

### 長期
- production DB に「汚染検知 view」を追加し、同一 exit_price が複数 instrument で連発するパターンを定期チェック

## 教訓

- **共有キャッシュは必ず key に symbol を含める**。スカラの「現在価格」を symbol 抜きで持つと、利用側で必ず混線する
- **fallback 順は障害時の挙動でも検証**。通常時の動作だけ見ていると、障害時に逆順となって bug が顕在化するケースを見逃す
- **abnormal pnl_pips は close_trade 直前で gate**。下流の Kelly / DD / equity が汚染されると影響範囲が広く、復旧コストが膨らむ

## 関連教訓
- [[lesson-data-source-production-first-2026-04-28]] — production data 優先 (本件も production DB を見て初めて発覚)
- [[lesson-bt-endpoint-hardcoded]] — ハードコードされた USD/JPY 前提が他ペアで破綻したシリーズの先行例
