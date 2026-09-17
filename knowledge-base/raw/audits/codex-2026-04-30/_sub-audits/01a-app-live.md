# Sub 1a: app.py ライブ取引パス

## Scope
- `app.py`: L32-100, 235-413, 414-499, 500-635, 636-792, 793-906, 907-1176, 1177-1378, 1379-1506, 1507-1898, 1899-2054
- `app.py`: L2055-3458, 3459-4308, 4364-4610, 7496-7618, 7619-8221, 8222-9449, 14025-14112
- `modules/demo_trader.py`
- `modules/oanda_bridge.py`
- `modules/learning_engine.py`

## 1. Bugs Found
| # | Severity | File:Line | Description | Root Cause | Suggested Fix |
|---|----------|-----------|-------------|-----------|--------------|
| 1 | Sev1 | `modules/oanda_bridge.py:323-327`, `modules/demo_trader.py:2369-2383`, `4647-4725` | OANDA停止系が実弾停止になっていない。`_oanda_kill()`/`emergency_kill()` は `_allowed_modes` を空にするが、`is_mode_allowed()` が常に `True` を返すため、その後も `open_trade()` が通る。 | 停止状態の権威ソースを `_allowed_modes` に置いたまま、判定関数だけ無効化した。 | `open_trade()` 冒頭で kill/allowed state を強制確認し、`is_mode_allowed()` を実際の停止フラグに戻す。 |
| 2 | Sev1 | `app.py:14025-14105`, `modules/demo_trader.py:700-727` | 自動起動がプロセス単位でしか抑止されず、複数 worker import 時に複数の `DemoTrader` ループが同時起動しうる。ライブで二重発注経路になる。 | `_auto_start_done` はプロセスローカル。DB/OS レベルの leader election がない。 | DB ロックや PID/lease で単一起動を保証し、非リーダー worker は autostart しない。 |
| 3 | Sev1 | `modules/demo_trader.py:2267-2276`, `2384-2390`, `2780-2855` | `_main_loop()` は 30 秒 timeout 後も旧 `_tick` スレッドを殺さずに放置する。次周期で同モードの新 `_tick` を起動するため、同一モードが並走して重複エントリーしうる。 | timeout を「skip」にしているだけで、実行中 worker のキャンセル機構がない。 | mode ごとに単一 worker を保証し、timeout 時は次 tick を禁止するか cooperative cancel を入れる。 |
| 4 | Sev1 | `modules/demo_trader.py:3200-3203`, `4140-4179`, `2632-2686` | 指値遅延エントリーが自己ブロックする。`_tick_entry()` は dedup を予約してから `pending_limits` に保存するため、60 秒以内に指値到達しても再入場が `recent_emit` で落ちる。 | dedup と pending-limit state machine の順序が逆。 | reserve は実約定直前に移すか、pending key は dedup 対象外にする。 |
| 5 | Sev1 | `modules/oanda_bridge.py:400-419`, `421-431`, `modules/demo_trader.py:571-607`, `4752-4758` | OANDA 発注が非冪等。timeout/network/503 後に同一 market order を再送し、さらに deploy 後の resend も `oanda_trade_id` 未記録なら再送する。ブローカー側約定済みでも重複建玉になりうる。 | client order id / idempotency key / 既存注文照合がない fire-and-forget retry。 | client extensions で一意キーを付与し、retry/resend 前に注文照会で重複を除去する。 |
| 6 | Sev2 | `modules/demo_trader.py:2456-2483`, `app.py:2078-2080`, `3491-3493`, `4085-4105`, `4220-4230`, `4369-4378`, `8266-8289` | ライブ判定が常に `df.iloc[-1]` の最新足を使っており、未確定足ベースでシグナルが発火する。BT は確定バー基準なので BT-Live 乖離を作る。 | live path に closed-candle guard がない。resample 後バーも確定確認なし。 | ライブでは最後の未確定バーを明示的に捨て、確定足のみで `compute_*` を呼ぶ。 |
| 7 | Sev2 | `app.py:8186-8196`, `modules/demo_trader.py:2477-2483` | `compute_layer3_score()` の S/R 近接ボーナスは `sr_levels` が float list のとき `sr_type==""` になり、近接時に常に `-0.15` を加算する。live path の `find_sr_levels(df)` 出力に対しショート方向バイアスが混入する。 | dict/float 混在 API なのに `support` 以外を一律 bearish 扱いしている。 | raw float S/R では符号を付けず 0 にするか、support/resistance を先に明示分類する。 |
| 8 | Sev2 | `app.py:3943-4008` | `compute_1h_zone_signal()` の R2-A suppress / A3 / A4 は `session` と `regime` を参照するが、この関数内で未定義。`try/except` に潰され、ゲートが fail-open で無効。 | スコープミス。daytrade path の補助ロジックを移植したが前段変数を持ってこなかった。 | `session = get_session_info()` と `regime = detect_market_regime(df)` を関数先頭で定義し、except で握り潰さない。 |

## 2. Structural Issues
1. ML 推論は cross-pair 汚染がある。`train_ml_model()` は `USDJPY=X` 固定で学習する (`app.py:7818-7819`) 一方、`get_ml_confidence()` は全 scalp result に埋め込まれる (`app.py:8359`, `9381`)。現状は表示値でも、将来 gate 化すると pair drift をそのまま実弾化する。
2. シグナル層の重複が大きい。Layer0/1/2/3、EMA200 逆行ペナルティ、session 調整、HTF 調整が `compute_daytrade_signal` (`app.py:2064-2338`), `compute_1h_zone_signal` (`3459-4019`), `compute_scalp_signal` (`8250-9340`), `compute_signal` (`1627-1893`) に分散し、同名 gate の意味が揃っていない。
3. OANDA 実行状態機械が薄い。`open_trade()` は `tradeOpened.tradeID` 1 本だけを保持し (`modules/oanda_bridge.py:421-431`)、`_sync_oanda_closures()` は CLOSED 50件だけを見る (`modules/demo_trader.py:1419-1423`)。部分約定・複数 fill・長時間停止後の取りこぼしに弱い。
4. スコープミスを `except: pass` で隠す箇所が多い。`compute_signal()` の未定義 `bar_time` 参照 (`app.py:1745-1751`) や 1H zone の未定義 `session/regime` は、S333 系の再発パターン。

## 4. Roadmap Alignment
- 現状の最大阻害要因は、実弾停止不能・二重起動・非冪等再送で「クリーンな live N」を壊している点。これは DD と Kelly を直接悪化させ、Gate 1 以降の評価母集団も汚染する。
- 次点は未確定足使用。BT で正に見える edge を live で再現できず、bb_rsi/session_time_bias の評価をさらに不明瞭にする。
- 加速施策は、まず execution state machine を固めて live データの真正性を回復し、その後に closed-candle 化で BT-Live 乖離を縮めること。

## 5. Top 3 Action Items (impact 順)
1. OANDA 停止系を強制化し、`open_trade()` に冪等キーを追加する — Impact: 重複発注・停止不能を即時除去 — Confidence: high
2. autostart と tick 実行を single-owner 化する — Impact: 二重ループ/レース起因の phantom trade を除去 — Confidence: high
3. live signal を確定足限定にし、Layer3 S/R 符号バグと 1H zone fail-open を修正する — Impact: BT-Live 乖離と score 汚染を縮小 — Confidence: high

## 6. Out-of-Scope Findings
- `compute_signal()` の `bar_time` 参照 (`app.py:1745`) は swing/shared path のスコープバグで、同種の Optional/NameError 再発として横展開点検対象。
