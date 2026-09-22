# SL replacement storm guard 4 点 — 設計・code derivation・CF pin 一覧 (2026-09-22)

**Status**: 実装済み・**既定は検知のみ** (rule:R3 — 構造バグ修理、live 経路 PR-1、エッジ主張/lot/tier 不変更)
**Scope**: `modules/oanda_bridge.py` `OandaBridge.modify_sl` / `modify_sl_sync` の入口。呼び出し側 (`modules/demo_trader.py` の BE/trail/pyramid/TP-extender ロジック) は不変更。
**Tests**: `tests/test_oanda_bridge_storm_guard.py` (48 件、うち CF pin 12 件)
**Review 消化 (PR #287, 2026-09-22)**: 1 巡目 P1 ×2 (再起動後 seed の `id`/`trade_id` 取り違え、stale DB sl を baseline に採用) + P2 ×1 (fire-and-forget 競合) / 2 巡目 P1 ×1 (未確認予約を冪等 True で返す) + P2 ×1 (連鎖失敗で未確認値が baseline に残る) / 3 巡目 P1 ×1 (重なった A,B で B 先行確認 → pending A が baseline に残る・broker 側発行順逆転) — §2.1 / §2.2 / §2.6 / §4 に反映
**関連**: [[kalman-d7-carveout-postfill-packet-2026-09-17]] §1–3 (拡張凍結条件 = 本 guard の main 着地 + test pin) / [[kalman-d7-po-dn-flip]] 09-11/09-14/09-16 節 / [[usdjpy_carry_dip_accumulator]] §(3) storm / [[path-to-win-decision-memo-2026-09-20]] Rank 2-1 / 再評価 2026-09-22 §3 Rank 7

---

## TL;DR

| # | guard | 止める形状 | 実測根拠 | 実装 |
|---|---|---|---|---|
| 1 | 累積 tx breaker (窓あたり累積送信数、既定 50/h・200/日) | 継続時間で判別。storm と平常 trail は瞬間レートが同帯 (~1.5–3 cycle/s) なので**レート閾値では分離不能** | storm 4 = 16,837 replacement / 2h51m、#893161 平常 = 3 replacement ([[usdjpy_carry_dip_accumulator]] 09-14 節 (1)) | `_storm_check_breaker` `oanda_bridge.py:1150` |
| 2 | 冪等 (直前送信 SL と同値 → skip) | family A: 同一価格 loop | #837978 4,791 回 / #847578 5,936 回 同一価格再送 (card L55, L63) | `_storm_check_idempotent` `:1171` |
| 3 | 単調性 (BUY で SL↓ / SELL で SL↑ → reject) | storm と独立の **risk-increasing 欠陥**。振動が価格を追い越して自己約定 = storm の「終息機構」 | storm 4: 154.350→154.270 (BUY で 8 pip 下)、#893161 3 回目 154.260→154.248 (1.2 pip 下) → 同一秒自己約定 (card L31, L131, L141) | `_storm_check_monotonic` `:1180` |
| 4 | dead-band (\|new − last\| < 1.0 pip → skip、ちょうど 1.0 pip は通す) | family B: 0.001 刻み振動。**等値では止まらない** | storm 4: 154.349⇄154.350 / 154.385⇄154.386 が秒間数回 (index 09-11 「機構は same price ではない」) | `_storm_check_deadband` `:1198` |

順序 = [[kalman-d7-po-dn-flip]] 09-16 訂正版の直交セット: breaker → 冪等 → 単調性 → dead-band (`_storm_evaluate` `:1224`)。

**既定 = 検知のみ**: 4 check は評価されカウンタ + 抑制付き WARN ログ (`_storm_record` `:1243`) が動くが、送信は止めない。`STORM_GUARD_ENFORCE=1` で guard 本体が有効 (`_storm_gate` `:1348`)。

---

## 1. なぜ bridge 入口か (code derivation)

呼び出し側 `modules/demo_trader.py` の SL ループ (0.5 s 周期) には既に `if new_sl > sl: sl = new_sl` 型の片側比較がある (L3170–3176, L3278–3283 等)。それでも storm が起きる機構は code から 2 つ読める:

- **family A (同一価格 loop)**: LIVE 経路 L3188–3199 は `modify_sl_sync` 成功後に **DB (`update_sl_tp`) を更新しない** (shadow 分岐 L3193 のみ更新)。ループは毎 tick DB 行から `sl` を読み直すので、同じ trail 目標を毎 tick 再計算 → 同じ SL を毎 tick再送する。broker はこれを毎回 `STOP_LOSS_ORDER(REPLACEMENT)` + `ORDER_CANCEL` として受理 (0 error) → 1 tick ≈ 2 tx。これは `_original_sl` との比較 (`if sl != _original_sl`) では検出できない (原 SL ≠ 新 SL が恒真)。
- **family B (0.001 振動)**: trail 目標は `round(price − k·ATR, _pip_decimals)` で `_pip_decimals = 3` (JPY、L2989) = **1/10 pip 分解能**。price の tick 変動がそのまま目標に乗り、同一 bar 内で 154.349⇄154.350 を往復する。呼び出し側の `new_sl > sl` は 0.001 の上昇を「有利側の trail」として正当に通す。

⇒ 修理の正しい層は **戦略・呼び出し側ではなく、broker への送信を一元化している `OandaBridge.modify_sl*`** (storm 4 が kalman、storm 1–3/5 が carry_dip で、戦略横断 = 共有層と確定済み、index 09-11 (a))。呼び出し側の DB 未更新 (family A の根) は別 PR の候補として needs_orchestrator に返す (本 PR は呼び出し側非接触)。

### 1.1 なぜ既存 breaker は効かないか
`daily_loss_limit_pips` / `max_drawdown_pips` は pip/PnL 建て。storm の直接 PnL は **¥0** (index 09-11 broker ledger 残差ゼロ) ⇒ 原理的に発火しない。tx 数建ての breaker が必要 (index 09-11 「still no guard of the right shape」)。

### 1.2 なぜ「窓あたり累積」か
#893161 の全数トレース (card 09-14 節 (1)): 平常 trail も ~1.5–3 cycle/s で storm 4 の 3.28 tx/s (≈1.64 cycle/s) と同帯。⇒ 瞬間レート閾値は偽陽性/偽陰性が同時に出る。**累積送信数** (50/h、200/日) は #893161 (3 回) と storm (数千〜16,837 回) を 1 桁以上の余裕で分離する。

---

## 2. 状態と契約

### 2.1 per-trade state (in-memory)
`{direction, confirmed_sl, confirmed_seq, pending[token], seq, sent_ts[], sent_total, failed_total, tripped, warned, counts{reason: n}, seeded, seed_source}` — **`confirmed_sl` = broker が受理した最後の SL** (open / seed / 成功確認のみ更新)、**`pending` = 飛行中 (未確認) 予約 token 列**。各 check が比較する baseline = `pending[-1].new_sl` があればそれ、なければ `confirmed_sl` (`_storm_baseline`)。status の `last_sl` は互換のためこの baseline を返す — `open_trade` 成功時に `direction` / 初期 `sl` を登録、`close_trade` 成功/404 で破棄。再起動後 (`restore_mappings` 経路、open_trade を経ていない) は最初の `modify_sl*` 時に lazy seed (`_storm_seed_restored`):

| 出所 | 何を取る | 理由 |
|---|---|---|
| **broker** (`OandaClient.get_open_trades()` → `id == oanda_id` の行) | `direction` (currentUnits 符号) + **`last_sl` (stopLossOrder.price)** | 唯一 authoritative。`demo_trades.sl` は LIVE 経路で trail 後も更新されない (`demo_trader.py` L3188–3199 の LIVE 分岐は `update_sl_tp` を呼ばない) ので **stale** — それを baseline にすると broker 154.350 / DB 154.115 で 154.270 (broker から 8 pip 不利側) を「有利側」と誤判定して送る = guard が守るべき形状の素通し (PR #287 review P1-b) |
| DB fallback (`demo_trades` 行、**`trade_id` で照合** — `id` は INTEGER PK で別物、PR #287 review P1-a) | `direction` のみ | sl は stale なので使わない。broker 不達時は `last_sl=None` のまま = 最初の成功送信が baseline (fail-open) |

`seed_source ∈ {broker, db_direction_only, None}` を status に露出。broker 以外で seed した場合は WARN 1 行。**永続化はしない**: storm 自体が process 内の trail 状態に依存し、再起動で消える (index 09-11: 4 回再起動は storm を止めも起こしもしない)。

### 2.2 `modify_sl_sync` の戻り値 (enforce 時)
| 判定 | 送信 | 戻り値 | 理由 |
|---|---|---|---|
| 通過 | する | broker 結果 | 従来通り |
| 冪等 skip (一致相手 = **確認済み** `confirmed_sl`) | しない | **True** | broker は既にその SL。False を返すと L3199 の rollback (`sl = _original_sl`) が走り、毎 tick「再送→skip→rollback」の空ループになる (tx は 0 なので無害だが意味論として誤り) |
| 冪等 skip (一致相手 = **飛行中の未確認予約**) | しない | **worker の結果を待って返す** (`_storm_sync_result`: `token.done` を最大 `STORM_PENDING_WAIT_SEC`=15 s 待ち、成功 True / 失敗 False / timeout False) | 未確認を True で返すと pyramiding 経路 (`modify_sl_sync` 成功 = 元建玉保護済み) が失敗する飛行中要求を保護と誤認して追加 exposure を開く (review 2 巡目 P1)。sync 側は broker を叩かない (tx 増なし) |
| dead-band skip | しない | False | broker SL は未変更 (< 1 pip 差)。caller は原 SL に戻す = demo 簿と broker の乖離を作らない |
| 単調性 reject | しない | False | 契約違反の要求。caller 側 SL は原値に戻る |
| breaker | しない | False | 以後その trade の SL は broker 側で凍結。1 回だけ WARN |

`modify_sl` (fire-and-forget) は gate で `return` するだけ。

### 2.3 方向不明 (fail-open)
DB seed もできず `direction` 不明の場合、単調性は判定不能 → 通す + `unknown_direction` カウンタ。冪等/dead-band は最初の成功送信で baseline を得るまで通す。**guard は fail-open** (取引機会を殺さない — 4原則#1)。

### 2.4 env
| env | 既定 | 意味 |
|---|---|---|
| `STORM_GUARD_ENFORCE` | 未設定 = 検知のみ | `1/true/yes/on` で guard 本体有効 |
| `STORM_GUARD_DEADBAND_PIPS` | 1.0 | dead-band 幅 (pip)。0 で無効 |
| `STORM_GUARD_MAX_TX_PER_HOUR` | 50 | 0 で無効 |
| `STORM_GUARD_MAX_TX_PER_DAY` | 200 | 0 で無効 |
| `STORM_GUARD_ALLOW_SL_LOOSEN` | 未設定 = reject | 明示 opt-in で単調性 reject を解除 (検知は継続) |

pip 単位 = `0.01` (JPY/XAU) / `0.0001` (それ以外) — demo_trader の `100 if JPY/XAU else 10000` 換算と同一規約 (`_storm_pip_size` `:82`)。

### 2.5 観測
`OandaBridge.status["storm_guard"]` (`:514`) = `{enforce, allow_loosen, config, totals{evaluated, sent, failed, detected{4}, skipped{4}, unknown_direction, breaker_trips}, trades{direction, last_sl (=baseline), confirmed_sl, pending[], sent_total, failed_total, tripped, seed_source, counts}}`。`/api/demo/status` 系の bridge status 経由で読める。ログ: `[OandaBridge][STORM_GUARD] DETECT(would_skip)|SKIP reason=... n=...` (trade × reason ごと最初の 3 件 + 100 件ごと) と `BREAKER TRIPPED` (trade ごと 1 回)。

### 2.6 fire-and-forget 競合と予約 (PR #287 review P2 → 2 巡目 P1/P2 で確認済み/未確認を分離)
`modify_sl` は worker thread で送信する。「成功後に baseline を更新」だと worker 完了前に到達した N 件が同じ古い baseline を見て全部通り、同一/sub-pip 要求の burst が冪等・dead-band を、大量 queue が breaker を、それぞれ素通しする。⇒ **評価と予約 (`_storm_reserve`: `pending` に token 追加 / `sent_ts` / `sent_total` 更新) を `_storm_gate` の 1 つの `RLock` 区間で行う** (sync / async 対称)。

1 巡目の実装は予約で `last_sl` を直接書き換え、失敗時に `prev_sl` を復元していた。2 巡目 review が 2 つの穴を指摘: (P1) 飛行中の同値予約に対する `modify_sl_sync` が未確認のまま冪等 True を返す / (P2) A,B 予約 → A,B 連鎖失敗で B の rollback が未確認の A を baseline に残す。⇒ **状態を `confirmed_sl` (broker 受理済み) と `pending` (飛行中) に分離**:

| event | 操作 |
|---|---|
| 予約 (`_storm_reserve`) | `pending.append(token{seq, new_sl, done: Event, ok})`。`confirmed_sl` は触らない |
| 成功 (`_storm_confirm`) | token を pending から外し、`seq > confirmed_seq` なら `confirmed_sl = new_sl` (worker 完了順が発行順と逆でも後発が勝つ) |
| 失敗 (`_storm_rollback`: `ok=False` / 例外) | token を pending から外すだけ — 「戻す」操作は不要で、連鎖失敗でも baseline は自然に `confirmed_sl` へ戻る。**要求数は戻さない** (breaker は broker への要求数 = 失敗要求も tx)。`totals.failed` / `trades[*].failed_total` |
| 冪等一致が pending (enforce, sync) | 送信せず、その token の `done` を待って `ok` を返す (§2.2) |
| 送信直前 (`_storm_wait_turn`、3 巡目 P1) | **`pending[0]` が自分になるまで待つ** (前の要求が confirm/rollback で決着するまで次を送らない = trade ごとに同時飛行 1 件、発行順直列化)。上限 `STORM_TURN_WAIT_SEC`=20 s、timeout は rollback + drop (順序不明のまま送る方が危険; sync は False) |

直列化の理由 (3 巡目 P1): A,B が重なって B が先に確認されると baseline は pending A を返し続け、A<X<B の BUY 要求が「A より tight」として送られて確認済み B を緩める。さらに broker 側で A が B の後に処理される発行順逆転も起きる。同時飛行を 1 件に絞ると「B 確認済み ∧ A pending」の窓そのものが存在しない (`test_serialization_no_window_where_confirmed_b_coexists_with_pending_a`)。平常 trail (0.5 s tick、HTTP ~100–300 ms) では順番待ちは実質発生しない。

検知のみモードでも予約/確認/直列化は同じ機構で動く (送信は止めない)。

---

## 3. 検知のみモードでの読み方 (有効化判断の材料)
検知のみでは送信が続くため `last_sl` は毎回更新され、**family B の振動は 上=deadband / 下=monotonic (BUY) に交互分類される** (test `test_default_is_detect_only_storm_passes_but_is_counted`)。⇒ 検知のみモードで `detected.monotonic` が大きく出ても、その大半は「振動の下向き半分」であって 8 pip 級の単調性違反とは別。有効化前の読み手は `detected.breaker` (≥1 = storm 署名) と `trades[*].counts` を見る。enforce 後は `last_sl` が固定されるので分類は idempotent/deadband に収束する (test `test_a_all_four_enabled_stops_storm4_shape`: deadband 50 / idempotent 49 / monotonic 100)。

---

## 4. CF pin 一覧 (同一 commit、`tests/test_oanda_bridge_storm_guard.py`)

pycache purge (`find ~/Library/Caches/com.apple.python -path '*fx-ai-trader*' -name '*.pyc' -delete`) → `python3 -B` で実行 (MEMORY `feedback_pycache_prefix_stale_bytecode_verification`)。

| pin | 殺す対象 (monkeypatch) | 期待 | test |
|---|---|---|---|
| (b)-1 | `_storm_check_deadband` → None | 振動 storm 400 本が 400 回送信される | `test_b_cf_kill_deadband_lets_oscillation_storm_through` |
| (b)-2 | `_storm_check_idempotent` → None | 同一価格 storm 400 本が 400 回 | `test_b_cf_kill_idempotent_lets_same_price_storm_through` |
| (b)-3 | `_storm_check_monotonic` → None | BUY SL↓ 400 本が 400 回 | `test_b_cf_kill_monotonic_lets_loosening_through` |
| (b)-4 | `_storm_check_breaker` → None | 400 回 (50/h 閾値が効かない) | `test_b_cf_kill_breaker_lets_storm_through` |
| (b)-5 | enforce flag のみ反転 | 1 送信 ⇄ 400 送信 | `test_b_cf_enforce_flag_off_is_the_only_difference` |
| (c) | `_storm_record` → no-op | 検知カウンタが 0 のまま (送信数は不変) | `test_c_cf_kill_detector_zeroes_counters` |
| (e)-1 | `_storm_seed_restored` → 旧挙動 (DB sl 154.115 を baseline) | broker 154.350 の BUY で 154.270 が送られる (8 pip 緩め素通し) | `test_restore_path_cf_seeding_stale_db_sl_lets_loosening_through` |
| (e)-2 | DB 行が `id` のみ (旧 `row.get("id")` 照合の形) | direction 不明のまま = 単調性が永久 fail-open | `test_restore_path_cf_db_row_keyed_only_by_id_never_seeds` |
| (f) | `_storm_reserve` → pending に積まない (成功後更新の旧形) | 同一 SL 5 件 burst が 5 件 queue される | `test_p2_cf_reserve_after_success_lets_burst_through` |
| (g)-1 | `_storm_sync_result` → 未確認予約一致で即 True (旧形) | worker 失敗前に sync が True を返し、confirmed_sl は原値のまま (保護未確認) | `test_p1_cf_treating_pending_as_confirmed_returns_true_before_failure` |
| (g)-2 | 予約時 prev_sl 記録 + rollback で復元 (1 巡目の形) | A,B 連鎖失敗後に未確認 A が confirmed_sl に残り、正当な A 再送が冪等 skip される (broker 未到達) | `test_p2_cf_prev_sl_rollback_leaves_unconfirmed_baseline` |
| (h) | `_storm_wait_turn` → 常に True (順番待ちなし、2 巡目の形) | B の worker が A より先に broker へ届き、「B 確認済み ∧ A pending」の窓が生じる | `test_serialization_cf_without_turnstile_b_can_confirm_before_a` |
| 全体 CF (手動、2026-09-22、review 前の 28 件時点) | `_storm_gate` → `(True, None)` | 28 件中 **17 件 fail / 11 pass** (pass 11 = (b) 素通り pin・pip 規約・inactive 等、guard 非依存) | 一時 conftest で実測、commit には含めない |

(a) 群: 各 guard 単独 (他 3 つを kill) で storm が 1 送信 (breaker は閾値 50 ちょうど) で止まる。(d) 群: 有利側 trail (BUY +2 pip ×10 / SELL −1.5 pip ×10)、BE 移動 +18 pip、ちょうど 1.0 pip、EUR_USD 0.0001 規約 — skip/detect **0** (偽陽性ゼロ)。

---

## 5. 不変更 (明示)
- **wg (weekend_gap_fade)**: trail なし・4h exit・disaster SL 150p ([[weekend-gap-fade]] L42 「不変更」行)。本 guard は `modify_sl*` の入口のみで、wg は `modify_sl*` を呼ばない (SL は ON_FILL 固定) ⇒ 凍結値に非接触。
- carry_dip SL 150p 復元 / ps_aud_jpy 降格 / M2 estimand — autopilot 禁止 3 件、本 PR は非接触。
- kalman 契約 (1000u, bypass set) — 非接触。本 guard の main 着地 + test pin は [[kalman-d7-carveout-postfill-packet-2026-09-17]] §3 拡張凍結の解除**条件**であって解除そのものではない (L1/variant/pair の R1 起案は別)。
- 呼び出し側 (`demo_trader.py`) の trail/BE/pyramid/TP-extender ロジック、`_pip_decimals`、`update_sl_tp` 経路 — 非接触。

## 6. 既知の限界・フォローアップ (needs_orchestrator)
1. **有効化は別判断**: 検知のみで ≥1 live fill の trail を観測 (`detected.*` と `sent` の比、`breaker_trips`) してから `STORM_GUARD_ENFORCE=1` (Render env + 再起動)。有効化は Rule 2 監視付き。
2. **family A の根 (L3188–3199 LIVE 経路の DB 未更新)** は本 PR では直していない — 冪等 guard で broker tx は止まるが、caller は毎 tick 再計算→skip を続ける (CPU/ログのみ、tx 0)。別 PR (R3) 候補。
3. enforce 時、TP-extender 経路 (L3285, L3411, L3444) は `modify_sl_sync` False で TP 延伸も DB に載らない (SL 成功と結合)。dead-band に当たる確率は低い (trail SL は原 SL から遠い) が、enforce 前に該当ログが出ないか確認。
4. per-trade counter は in-memory。再起動で消えるが storm も消えるので一致。評価・予約・prune・rollback は全て `_storm_lock` (RLock) 内 (PR #287 review P2 で lock 外更新を廃止)。
6. **再起動後 seed の残余リスク**: broker 不達 ∧ DB から direction のみ seed の場合、最初の 1 送信は baseline なしで通る (fail-open、4原則#1)。broker が stopLossOrder を持たない trade (SL なし) も同様。seed は trade ごと 1 回 (`OandaClient.get_open_trades()` 1 call) で、enforce 前に `seed_source != broker` の WARN が出ていないか確認。
5. 検知器の読み手: `status["storm_guard"]` を daily report / anomaly_watcher で読む consumer は**未作成** (write-only 化を避けるため、hot file 所有セッション側で追加要)。
