# TV Pine Edge Discovery Framework

## Purpose
戦略エッジの視覚検証 + セグメント分解 + TV 内蔵 BT メトリクスの照合を **Pine strategy 単独で完結** させる枠組み。Python BT は必須ゲートではない。

## Why this exists
- TV の Strategy Tester は OANDA 過去全期間を一気に backtest するので N=500+ が Pine 内で取れる
- 「N が少ない理由」「どのセグメントで負けているか」を Pine 内で分解可能（Python BT を待つ必要がない）
- Tokyo / London / NY の有効性は戦略ごとに別物（aggregate WR は嘘をつく）→ 必ずセッション別に出す
- TV の Strategy Tester の数値を Pine のテーブルに mirror すれば、Strategy Report を開き直さなくても overall + segment を同一画面で比較できる

## File template
`bt-results/tv-overlays/{strategy}-replica.pine` — 1 戦略 = 1 ファイル。

### Required elements (チェックリスト)
1. `//@version=5` + `strategy(... overlay=true, pyramiding=0, process_orders_on_close=true)`
2. 戦略本体ロジックを Pine で **そのまま** 翻訳（gate / momentum / EMA / ADX / RSI 等）
3. `strategy.entry()` + `strategy.exit(stop=..., limit=...)` で SL/TP 発注
4. **Closed-trade 可視化**: `strategy.closedtrades.*()` を `for` ループで読み、`line.new` (WIN=green / LOSS=red) + `label.new` で W/L マーカー
5. **MTF オシレーター**: `request.security(syminfo.tickerid, "60"|"240", ta.rsi(close, 14), lookahead=barmerge.lookahead_off)` で 1h / H4 を取得 — lookahead は必ず off
6. **エントリー時の context 配列保存**: `var int[] trade_session / var float[] trade_rsi_h1 ... ` に entry bar の値を `array.push`
7. **3 種類の table**（`barstate.islast` で描画）:
    - **Summary** (`position.top_left`) — TV Strategy Tester mirror: `strategy.closedtrades / wintrades / losstrades / eventrades / netprofit / grossprofit / grossloss / max_drawdown / initial_capital` を表示
    - **Session** (`position.top_right`) — Tokyo / London / NY / Off × N / WR% / PF / NetP
    - **MTF bin** (`position.bottom_right`) — H1 RSI bucket (`<30 / 30-50 / 50-70 / >=70`) × direction (BUY / SELL) × N / WR%
8. **Optional session tint**: `bgcolor(in_session ? color.new(color.blue, 95) : na)` で gate 窓を視覚化

## Session classification (UTC, non-overlapping primary tag)
```
h < 7  → Tokyo
7 ≤ h < 13 → London
13 ≤ h < 22 → NY (London-NY overlap is NY)
h ≥ 22 → Off
```
重なり時間帯は主導セッションに片寄せ（double-count しない）。

## H1 RSI bucket convention
| Slot | Direction | RSI range |
|---|---|---|
| 0 | BUY | <30 |
| 1 | BUY | 30-50 |
| 2 | BUY | 50-70 |
| 3 | BUY | ≥70 |
| 4 | SELL | <30 |
| 5 | SELL | 30-50 |
| 6 | SELL | 50-70 |
| 7 | SELL | ≥70 |

N<10 のセルはグレー表示（統計的に意味なしマーカー）。

## How to use (loop)
1. Pine strategy を TV にロード → 全期間 BT → Summary / Session / MTF table を見る
2. **aggregate と各セグメントを比較**:
    - Tokyo は WR=20% でも London/NY が WR=70% なら、戦略は時間帯フィルタで救える
    - H1 RSI<30 BUY だけ N=3 で死んでいるなら、そのセルだけ deny
3. 仮説フィルタを Pine 内で追加（input.bool toggle 推奨）→ Strategy Tester で N / PF / WR を再計測 → go/no-go を Pine 内で判断
4. **Python BT は本番転送（`strategies/daytrade/`）の直前にクロスソース確認 1 回**。必須ゲートではない

## Known pitfalls
- `pyramiding=0` だと同方向シグナルが捨てられる → 「シグナル数」と「実エントリー数」を別カウントするなら別の累積カウンターを足す
- `request.security` の `lookahead` を必ず off
- `max_lines_count` / `max_labels_count` 上限 500 → 古いオブジェクトから LRU で消える前提
- `ta.dmi(14, 14)` は tuple を返すので `request.security` に直接渡せない（必要なら ADX を本足 TF だけで使うか、別の構造で MTF 化）
- `calc_on_every_tick=false` のとき realtime 最終バーで `barstate.islast` が false になることがある — テーブル描画はバー確定後
- **`strategy.grossloss` は TV で正値を返す** — PF = `grossprofit / math.abs(grossloss)` で計算しないと `gl > 0 ? gp/gl : 999` のような分岐で常に 999 が出る（v1 xs_momentum-replica の既知バグ）
- **post-save の on-chart instance は自動再コンパイルされない** — `pine_set_source` + `pine_smart_compile` (or Save) でライブラリ側は更新されるが、チャートに乗っている古いインスタンスは旧コードで動き続ける。MCP では現状 "Add to Chart" を確実に押す手段がない → ユーザに手動再追加を依頼するか、Indicator 設定→Remove → Indicator search → 再追加で対応

## Reference implementation
- `bt-results/tv-overlays/xs_momentum-replica.pine` — xs_momentum (v8.9: London-NY gate, ADX≥20, mom>1.0 ATR, SL=1.5 ATR, TP=2.0 ATR)

## Related
- `wiki/lessons/lesson-bt-segment-decomposition.md` — aggregate を信じない原則
- `wiki/analyses/friction-analysis.md` — ペア別摩擦
