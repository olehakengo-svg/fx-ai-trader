# BT trade_log → TradingView overlay verification — 2026-05-13

## 目的
「BT が主張するエッジは TV チャート上で実際に正しい構造で発火しているか」を**視覚的に検証**する汎用ツール。Pine 完全再現は戦略毎にコストが高すぎたため、Python BT の trade_log を Pine の `var int[] T_TS` 等にハードコードしてラベル＋SL/TP 線として描画する方式を採用。

## 構成
- 生成器: `tools/tv_overlay_gen.py`
  - 入力: `entry_type` / `symbol` / `lookback_days` / `interval`
  - 動作: `app.run_daytrade_backtest()` を実行 → `trade_log` を `entry_type` でフィルタ → Pine v5 indicator として出力
  - 出力先: `bt-results/tv-overlays/{entry_type}-{PAIR}-{INTERVAL}-{N}d-{date}.pine` と `.trades.json`
- 注入: TV MCP で `pine_new` → `pine_set_source` → `pine_smart_compile` → `Add to chart` (DOM click)

## 初回ケース: trendline_sweep × EUR_USD (365d / 15m)
- BT 集計: N=59, WIN=47, **WR=79.7%, EV=+0.824**, PF (推定) ≒ 1.84
- 全 trades が SELL（`SELL_ONLY_PAIRS = {"EURUSD","EURGBP","XAUUSD"}` 仕様通り）
- 視覚確認 (2026-02-02 〜 02-07 ウィンドウ): SELL WIN h=2/4/5 + SELL LOSS h=19 が swing-high リバーサル点に正しく描画
- TV 側データ feed: `FX:EURUSD (FXCM)` — BT は OANDA / massive-parquet ベースだが、15m bar 境界は両 feed で揃っており timestamp 一致

## 旧 Pine v1 簡略版との対比
- 前セッションで作った "Trendline Sweep Replica + Stats" は Pine 上で WR=32.1%（vs BT 80.8%）と乖離
- 乖離原因: Pine v1 が「最新 2 swing-high pair」しか追わない一方、本番ロジックは「全 swing-high pair × respect_count 上位 5」を評価
- 今回の overlay 方式では、Pine ロジックを真似ず BT の出した trade をそのまま重ねるため、再現精度問題が消える

## 運用フロー（今後の各戦略検証）
1. `tools/tv_overlay_gen.py <entry_type> <SYM>=X` で BT 実行 + Pine 生成（〜10分 / pair）
2. TV を該当 symbol / TF に設定
3. `pine_new` → `pine_set_source(生成 Pine)` → `pine_smart_compile` → DOM click "Add to chart"
4. `chart_set_visible_range` で複数ウィンドウを巡回しスクリーンショットで構造確認
5. 視覚異常があれば「fire 位置がランダム」「SL 設定が市場ノイズ域内」等を発見でき、その戦略のみ Pine 完全再現で深掘り

## 次のターゲット候補（scalp エッジ検証）
- `xs_momentum × USD_JPY` (旧 KB BT N=342 EV=+0.270 ※ 2026-04-14 古い数字、最新 2026-05-05 では N=608 EV=-0.007 break-even — [[python-bt-vs-tv-reconciliation-2026-05-14]] 参照) — 高頻度・短期、視覚で見やすい
- `session_time_bias × USD_JPY` (BT N=157 EV=+0.580) — 時間帯依存ロジックの validate に最適
- `gbp_deep_pullback × GBP_USD` (BT N=77 EV=+1.064) — RR高い戦略の SL/TP 妥当性確認

## 制限事項
- TV が読み込んだ bar 数のみラベル描画される（バック側を見るには `chart_set_visible_range` で誘導が必要）
- `time` 比較は ms 単位完全一致を要求。TV 側が異なる feed（broker）で bar 開始時刻がずれている場合、何も描画されない可能性 → trendline_sweep × EUR_USD では問題なし、他通貨で要確認
- `max_labels_count=500` / `max_lines_count=500` 上限。N>500 trades の場合は分割か filter 必要

## 関連
- 旧 Pine v1 簡略版実験: 同セッション内 TV editor (`Trendline Sweep Replica + Stats (EURUSD 15m SELL-only)`)
- `wiki/strategies/trendline-sweep.md` — 戦略仕様
- `bt-results/tv-overlays/` — 生成物保存先
