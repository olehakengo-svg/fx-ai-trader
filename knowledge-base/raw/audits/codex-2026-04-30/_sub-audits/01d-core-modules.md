# Sub 1d: コア取引モジュール

## Scope
- `modules/demo_trader.py` — 主に `1301-2209`, `2211-2307`, `3039-3050`, `4231-4763`, `4906-5136`, `571-613`
- `modules/demo_db.py` — 主に `77-80`, `103-127`, `205-287`, `512-611`, `689-837`, `848-874`, `1199-1375`
- `modules/oanda_bridge.py` — 主に `372-525`, `550-573`
- `modules/oanda_client.py` — 主に `57-147`, `151-183`
- `modules/exposure_manager.py` — 全体
- `modules/learning_engine.py` — 主に `46-320`
- `modules/alert_manager.py` — 主に `153-170`
- `modules/candidate_logger.py` — 全体確認
- `modules/hunt_event_logger.py` — 全体確認
- `modules/shadow_variants.py` — 全体確認

## 1. Bugs Found
| # | Severity | File:Line | Description | Root Cause | Suggested Fix |
|---|----------|-----------|-------------|-----------|--------------|
| 1 | Sev1 | `modules/oanda_client.py:129`, `modules/oanda_bridge.py:400`, `modules/demo_trader.py:571`, `modules/demo_db.py:866` | OANDA 発注が冪等でない。`market_order()` に `client_order_id` / `clientExtensions` がなく、bridge は `429/503/timeout/network` で再送し、起動時 `_resend_pending_oanda_trades()` も `oanda_trade_id=''` の OPEN 行を再送する。最初の POST が約定済みで応答だけ落ちたケースで二重発注が起きうる。 | 発注一意性を「応答で返る tradeID」に依存しており、送信前に永続化された注文キーが存在しない。 | `demo_trade_id` ベースの決定的 `client_order_id` を DB に先書きし、OANDA 注文に埋め込む。再試行/再送前はその ID で照会し、既存約定があれば再送しない。 |
| 2 | Sev1 | `modules/demo_trader.py:4437`, `modules/demo_trader.py:4632`, `modules/demo_trader.py:571`, `modules/demo_db.py:103`, `modules/exposure_manager.py:123` | 実際のロット数が永続化されず、リスク判定と再送が基準ロットで歪む。`_adjusted_units` を計算して OANDA 送信している一方、ExposureManager 登録は常に `OANDA_UNITS` を使い、DB schema に `units` 列もない。再起動後の `_resend_pending_oanda_trades()` も元ロットを復元できず default units で再送する。 | 注文サイズが `demo_trades` に保存されていない。entry 前チェックも post-open 登録も fixed units 前提。 | `demo_trades` に `units` を追加し、entry 判定・ExposureManager・resend の全経路で `actual_units` を単一ソース化する。 |
| 3 | Sev1 | `modules/demo_trader.py:4231`, `modules/demo_trader.py:4617`, `modules/demo_trader.py:4710`, `modules/demo_trader.py:571`, `modules/demo_db.py:866` | OPEN 挿入後に shadow/live 判定を後追い更新しており、途中クラッシュで gate bypass が起きる。DB には先に `is_shadow=_is_shadow` で OPEN 行が書かれ、その後に Q4/Phase0/Kelly/MC gate で shadow 化される。更新前にプロセスが落ちると、再起動時 resend が `is_shadow=0 and oanda_trade_id=''` をそのまま実弾送信する。 | DB 書き込み境界と OANDA 送信可否判定が分離している。 | 最終 gate 判定後に初回 INSERT するか、少なくとも `pending_live_decision` 状態を導入して resend 対象から除外する。 |
| 4 | Sev2 | `modules/learning_engine.py:177`, `modules/demo_db.py:1199` | mode 別 learning が全体データで汚染される。`evaluate(mode=...)` の母集団は `get_trades_for_learning()` で mode/cutoff/filter 済みなのに、SL hit rate・TP前反転率・MAFE・decay EV・bootstrap CI・risk metrics は `self._db.get_all_closed()` を再取得して全モード/全期間で再計算している。 | advisory 指標側だけ mode / fidelity cutoff / pair filter を引き継いでいない。 | `get_trades_for_learning()` の filtered `closed` をそのまま渡すか、`get_all_closed()` に同じ filter 条件を適用する。 |
| 5 | Sev2 | `modules/demo_trader.py:2053`, `modules/demo_trader.py:2069`, `modules/demo_trader.py:5051`, `modules/demo_trader.py:5073`, `modules/demo_trader.py:1439`, `modules/demo_db.py:590` | CLOSE 競合時に MAFE/リスク状態が先に破壊される。各 close path は `self._mafe_tracker.pop()` / `_entry_atr.pop()` / `remove_position()` を `DemoDB.close_trade()` の atomic `UPDATE ... WHERE status='OPEN'` より前に実行している。別 path が先に `CLOSED` 化すると、勝った path が 0 excursion で記録したり、負けた path が exposure を先に消す。 | メモリ側副作用が DB の OPEN→CLOSED 成否と同一トランザクションに乗っていない。 | 先に DB close を試し、成功した path だけが tracker/exposure を破棄する順序に変更する。 |
| 6 | Sev2 | `modules/demo_trader.py:1981`, `modules/demo_trader.py:2088`, `modules/demo_trader.py:1409` | SL/TP 同時到達・ギャップ時の扱いが常に SL 優先。`_check_sltp_realtime()` は単一 bid/ask snapshot で `SL_HIT` を `TP_HIT` より先に判定するため、両水準を跨いだ tick では broker 実約定と乖離しうる。ローカルで先に CLOSED 化すると後段の OANDA closure sync は補正できない。 | path information を持たない snapshot 判定で、broker truth より先に demo truth を確定している。 | OANDA 連携ポジションは broker close sync を優先し、ローカル SL/TP 判定は demo-only に限定するか、少なくとも gap case を `OANDA_PENDING_RESOLUTION` にする。 |
| 7 | Sev2 | `modules/demo_trader.py:4266`, `modules/demo_trader.py:4274`, `modules/demo_db.py:104` | `alpha_snapshot` が永続化されない。`open_trade()` が返すのは `trade_id` 文字列なのに、UPDATE は `WHERE id = ?` で integer PK を更新している。 | `id` と `trade_id` を取り違えている。 | `WHERE trade_id = ?` に修正するか、`open_trade()` が rowid を返す API に変更する。 |

## 2. Structural Issues
1. ALTER ベースの無版管理 migration が silent drift を隠す — `modules/demo_db.py:205-287` は多数の `ALTER TABLE ... ADD COLUMN` を bare `except` で握りつぶしており、`PRAGMA user_version` も schema checksum もない。列追加失敗と「既存列なので正常」を区別できない。推奨: 明示 migration table / `user_version` 化。
2. ExposureManager は「通貨ネット額 + 全体同方向件数」しか見ていない — `modules/exposure_manager.py:139-160`。`USD basket` 相関や pair-level covariance、縮小実行はなく、超過時は拒否のみ。推奨: basket exposure と partial size-down を追加。
3. OANDA 認証失効/権限失効に対する運用ハンドリングが弱い — `modules/oanda_client.py:79-91` は 401/403 を generic error にするだけで、`modules/oanda_bridge.py` 側に kill/disable/escalation がない。推奨: 401/403 専用で `oanda_disconnect` alert + bridge hard-disable。
4. `pip_mult` の JPY/non-JPY 分岐は `demo_trader` / `demo_db` / `oanda_bridge` では一貫しており、`_bt_regime_cascade_scalp_vec.py` と同型の truthy-branch バグは未検出だった。一方、`modules/hunt_event_logger.py:43-44` の `_pip_size()` は XAU を考慮していないため、将来 XAU を記録対象にすると `atr_pips` が 100 倍ずれる。

## 3. Losing Edge Analysis (Sub 6 のみ必須、他は該当時のみ)
- `bb_rsi_reversion` については本モジュール内に「注文サイド反転」や pip 係数ミスは見当たらず、むしろ `modules/demo_trader.py:4492-4500` で戦略全体を OANDA trip 済み。
- 追加で確認した範囲では、コア実装側の共通要因は「SELL side の算術バグ」より、`Spread/SL gate`・`RANGE SELL gate`・`mutual exclusion`・`shadow/live gate` のような routing/risk 層だった。

## 4. Roadmap Alignment
- Gate 0/1 を最も阻害しているのは、発注冪等性欠如とロット永続化欠如。これは DD・破産確率・aggregate Kelly を直接壊す Sev1 で、月利100%以前に「実弾状態が再現不能」になる。
- 次点は learning 汚染。mode 別 online learning が全体 closed で混ざるため、Kelly/EV の更新が遅く、誤学習で Gate 1 の `Aggregate Kelly > 0` 到達を遅らせる。
- CLOSE 競合の MAFE 破損は、SL/TP 最適化や fast-exit 分析を汚し、負けエッジの帰属精度を下げる。これは DD そのものより、改善速度の律速要因。

## 5. Top 3 Action Items (impact 順)
1. 発注 idempotency を導入し、`client_order_id + actual_units` を DB 永続化する — Impact: 二重発注/誤ロット再送を遮断し Sev1 を同時解消 — Confidence: high
2. OPEN 作成を「最終 gate 判定後」に寄せるか、`pending_live_decision` 状態を追加して resend 対象から外す — Impact: crash/redeploy 時の shadow bypass を停止 — Confidence: high
3. close path を `DB close 成功 → tracker/exposure cleanup` の順に組み替え、learning 指標は filtered sample を再利用する — Impact: MAFE/learning 汚染を止めて改善ループの信頼性を上げる — Confidence: high

## 6. Out-of-Scope Findings (オプション)
- `shadow` 分離自体は現状かなり防御されている。`modules/demo_db.py:1211-1215` は learning から `is_shadow=1` を除外し、`modules/demo_db.py:1327-1365` は shadow promotion 専用集計を別経路にしており、`modules/shadow_variants.py:14-15` の設計意図とも整合していた。 aggregate Kelly 汚染の主要経路はこの範囲では見当たらなかった。
