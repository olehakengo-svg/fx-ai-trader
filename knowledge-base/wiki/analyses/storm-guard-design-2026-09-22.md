# SL replacement storm guard 4 点 — 設計・code derivation・CF pin 一覧 (2026-09-22)

**Status**: 実装済み・**既定は検知のみ** (rule:R3 — 構造バグ修理、live 経路 PR-1、エッジ主張/lot/tier 不変更)
**Scope**: `modules/oanda_bridge.py` `OandaBridge.modify_sl` / `modify_sl_sync` の入口。呼び出し側 (`modules/demo_trader.py` の BE/trail/pyramid/TP-extender ロジック) は不変更。
**Tests**: `tests/test_oanda_bridge_storm_guard.py` (104 件、うち CF pin 27 件)
**Review 消化 (PR #287, 2026-09-22)**: 1 巡目 P1 ×2 (再起動後 seed の `id`/`trade_id` 取り違え、stale DB sl を baseline に採用) + P2 ×1 (fire-and-forget 競合) / 2 巡目 P1 ×1 (未確認予約を冪等 True で返す) + P2 ×1 (連鎖失敗で未確認値が baseline に残る) / 3 巡目 P1 ×1 (重なった A,B で B 先行確認 → pending A が baseline に残る・broker 側発行順逆転) / 4 巡目 P2 ×1 (検知のみモードでも順番待ち timeout が送信を drop していた) / 5 巡目 P2 ×1 (未確認 baseline に対する reject を最終判定していた → 先行失敗時に正当な保護更新を永久に落とす) / 6 巡目 P2 ×1 (順番待ち timeout の drop が要求数を保持し、未送信 burst が breaker 窓を埋めて trip) / 7 巡目 P1 ×1 (暫定予約が breaker 窓を埋めて偽 trip、取り消し後も tripped が残る) / 8 巡目 P1 ×1 (未送信の非暫定予約が窓を埋めている間に保護更新 D を breaker で最終 reject) / 9 巡目 P1 ×1 (暫定 baseline に対して gate を通った要求が、その暫定の reject 後に確認済み stop を緩める) / 10 巡目 P1 ×1 (timeout/network 等の応答曖昧な失敗を確定失敗として旧 baseline に戻し、適用済みかもしれない stop を緩める) / 11 巡目 P1 ×1 (broker 照会の snapshot を版チェックなしで適用し、照会中に進んだ新しい確認を古い stop で上書き) / 12 巡目 P1 ×1 (timeout 直後の旧値 snapshot 1 回を「未適用」の証拠にしていた) + P2 ×1 (fire-and-forget の caller で broker 照会が同期実行され SL ループを最大 10 s 塞ぐ) / 13 巡目 P1 ×1 (順番待ち 20 s 絶対 deadline が先頭の PUT timeout 10 s + 照会 GET 10 s を覆えず one-shot 保護更新が drop) + P2 ×1 (未 seed の restored trade への burst で worker ごとに GET が飛ぶ) / 14 巡目 P1 ×1 (5 s 安定観測で「未適用」と推定していた — timeout した PUT の server 側完了に上限はない) / 15 巡目 P1 ×3 (enforce の fire-and-forget で予約ごとに thread が増殖 / client のローカル 429 backoff 中の未送信呼び出しを breaker 窓に数えていた / 第三の値の観測で曖昧さを消していた) — §2.1 / §2.2 / §2.6 / §2.7 / §2.8 / §2.9 / §2.10 / §2.11 / §2.12 / §4 に反映
**関連**: [[kalman-d7-carveout-postfill-packet-2026-09-17]] §1–3 (拡張凍結条件 = 本 guard の main 着地 + test pin) / [[kalman-d7-po-dn-flip]] 09-11/09-14/09-16 節 / [[usdjpy_carry_dip_accumulator]] §(3) storm / [[path-to-win-decision-memo-2026-09-20]] Rank 2-1 / 再評価 2026-09-22 §3 Rank 7

---

## TL;DR

| # | guard | 止める形状 | 実測根拠 | 実装 |
|---|---|---|---|---|
| 1 | 累積 tx breaker (窓あたり累積送信数、既定 50/h・200/日) | 継続時間で判別。storm と平常 trail は瞬間レートが同帯 (~1.5–3 cycle/s) なので**レート閾値では分離不能** | storm 4 = 16,837 replacement / 2h51m、#893161 平常 = 3 replacement ([[usdjpy_carry_dip_accumulator]] 09-14 節 (1)) | `_storm_check_breaker` `oanda_bridge.py:1172` |
| 2 | 冪等 (直前送信 SL と同値 → skip) | family A: 同一価格 loop | #837978 4,791 回 / #847578 5,936 回 同一価格再送 (card L55, L63) | `_storm_check_idempotent` `:1193` |
| 3 | 単調性 (BUY で SL↓ / SELL で SL↑ → reject) | storm と独立の **risk-increasing 欠陥**。振動が価格を追い越して自己約定 = storm の「終息機構」 | storm 4: 154.350→154.270 (BUY で 8 pip 下)、#893161 3 回目 154.260→154.248 (1.2 pip 下) → 同一秒自己約定 (card L31, L131, L141) | `_storm_check_monotonic` `:1204` |
| 4 | dead-band (\|new − last\| < 1.0 pip → skip、ちょうど 1.0 pip は通す) | family B: 0.001 刻み振動。**等値では止まらない** | storm 4: 154.349⇄154.350 / 154.385⇄154.386 が秒間数回 (index 09-11 「機構は same price ではない」) | `_storm_check_deadband` `:1225` |

順序 = [[kalman-d7-po-dn-flip]] 09-16 訂正版の直交セット: breaker → 冪等 → 単調性 → dead-band (`_storm_evaluate` `:1271`)。

**既定 = 検知のみ**: 4 check は評価されカウンタ + 抑制付き WARN ログ (`_storm_record` `:1299`) が動くが、送信は止めない。`STORM_GUARD_ENFORCE=1` で guard 本体が有効 (`_storm_gate` `:1671`)。

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
| reject 理由が出たが baseline が**飛行中の未確認予約** (冪等 / dead-band / 単調性) | **暫定予約** → 送信順到来時 (先行が全て決着) に確認済み値で再評価 (§2.7) | 再評価の結果: 通れば自分で送って broker 結果 / 冪等 (確認済みに一致) なら True / それ以外 False。順番待ち timeout は False | 未確認値に対する最終判定は両方向に誤る — True で返せば pyramiding が未保護を保護と誤認 (2 巡目 P1)、False/drop なら先行失敗時に正当な保護更新を永久に落とす (5 巡目 P2)。**True は常に「broker が受理済み」を意味する** |
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

class 定数 (env ではない): `STORM_TURN_WAIT_SEC`=25 s (送信順番待ち上限、先頭ごと) / `STORM_RECONCILE_MIN_INTERVAL_SEC`=1 s (unresolved 再照会の最短間隔)。

pip 単位 = `0.01` (JPY/XAU) / `0.0001` (それ以外) — demo_trader の `100 if JPY/XAU else 10000` 換算と同一規約 (`_storm_pip_size` `:82`)。

### 2.5 観測
`OandaBridge.status["storm_guard"]` (`:514`) = `{enforce, allow_loosen, config, totals{evaluated, sent (=送信直前に窓入りした要求数), failed, ambiguous_failures, reconciled, unresolved, reconcile_discarded, observed_changed, coalesced, local_backoff, deferred, detected{4 + serialize}, skipped{4 + serialize}, unknown_direction, breaker_trips}, trades{direction, last_sl (=baseline), confirmed_sl, unresolved_sl, pending[], sent_total, failed_total, tripped, seed_source, counts}}`。`/api/demo/status` 系の bridge status 経由で読める。ログ: `[OandaBridge][STORM_GUARD] DETECT(would_skip)|SKIP reason=... n=...` (trade × reason ごと最初の 3 件 + 100 件ごと) と `BREAKER TRIPPED` (trade ごと 1 回)。

### 2.6 fire-and-forget 競合と予約 (PR #287 review P2 → 2 巡目 P1/P2 で確認済み/未確認を分離)
`modify_sl` は worker thread で送信する。「成功後に baseline を更新」だと worker 完了前に到達した N 件が同じ古い baseline を見て全部通り、同一/sub-pip 要求の burst が冪等・dead-band を、大量 queue が breaker を、それぞれ素通しする。⇒ **評価と予約 (`_storm_reserve`: `pending` に token 追加 / `sent_ts` / `sent_total` 更新) を `_storm_gate` の 1 つの `RLock` 区間で行う** (sync / async 対称)。

1 巡目の実装は予約で `last_sl` を直接書き換え、失敗時に `prev_sl` を復元していた。2 巡目 review が 2 つの穴を指摘: (P1) 飛行中の同値予約に対する `modify_sl_sync` が未確認のまま冪等 True を返す / (P2) A,B 予約 → A,B 連鎖失敗で B の rollback が未確認の A を baseline に残す。⇒ **状態を `confirmed_sl` (broker 受理済み) と `pending` (飛行中) に分離**:

| event | 操作 |
|---|---|
| 予約 (`_storm_reserve`) | `pending.append(token{seq, new_sl, done: Event, ok})`。`confirmed_sl` は触らない |
| 成功 (`_storm_confirm`) | token を pending から外し、`seq > confirmed_seq` なら `confirmed_sl = new_sl` (worker 完了順が発行順と逆でも後発が勝つ) |
| 失敗 (`_storm_rollback`: `ok=False` / 例外) | token を pending から外すだけ — 「戻す」操作は不要で、連鎖失敗でも baseline は自然に `confirmed_sl` へ戻る。**要求数は戻さない** (breaker は broker への要求数 = 失敗要求も tx)。`totals.failed` / `trades[*].failed_total` |
| 冪等一致が pending (enforce, sync) | 送信せず、その token の `done` を待って `ok` を返す (§2.2) |
| 送信直前 (`_storm_wait_turn`、3 巡目 P1) | **`pending[0]` が自分になるまで待つ** (前の要求が confirm/rollback で決着するまで次を送らない = trade ごとに同時飛行 1 件、発行順直列化)。上限 `STORM_TURN_WAIT_SEC`=25 s は**先頭 token 1 件あたり** — 先頭が入れ替わる (= 前が決着した) たびにリセットし、進捗している限り後続の one-shot 保護更新は落とさない。25 s = 先頭の決着に要し得る PUT timeout 10 s + 曖昧時の照会 GET 10 s + 余裕 (13 巡目 P1: 絶対 20 s だと A の決着直前に B が drop)。停滞 (先頭が変わらない) だけが timeout。timeout は **unreserve** + drop (broker 未到達なので要求数 `sent_ts`/`sent_total` を戻す — rollback だと停滞 1 件の後ろの未送信 burst が breaker 窓を埋めて `tripped` が立つ、6 巡目 P2; 順序不明のまま送る方が危険; sync は False)、`skipped.serialize` に計数。**検知のみモード (既定) では待たない・落とさない** — 待つはずだった件数を `detected.serialize` に数えるだけ (4 巡目 P2: 既定契約「送信は従来通り、観測だけ」を直列化にも適用) |

直列化の理由 (3 巡目 P1): A,B が重なって B が先に確認されると baseline は pending A を返し続け、A<X<B の BUY 要求が「A より tight」として送られて確認済み B を緩める。さらに broker 側で A が B の後に処理される発行順逆転も起きる。同時飛行を 1 件に絞ると「B 確認済み ∧ A pending」の窓そのものが存在しない (`test_serialization_no_window_where_confirmed_b_coexists_with_pending_a`)。平常 trail (0.5 s tick、HTTP ~100–300 ms) では順番待ちは実質発生しない。

検知のみモードでも予約/確認は同じ機構で動く (送信は止めない)。直列化 (順番待ち・timeout drop) は enforce のみ — 検知のみでは従来通り並行送信し、`detected.serialize` で「待つはずだった」件数を観測する (`test_detect_only_turn_wait_never_drops_or_delays_but_counts`)。

### 2.7 未確認 baseline に対する reject は暫定 (PR #287 review 5 巡目 P2)
enforce で confirmed 154.115 / pending A=154.350 のとき B=154.349 は A 基準では単調性違反だが、確認済み基準では 23.4 pip の正当な tightening。A が失敗したら B を落としてはいけない (「未確認値への最終 reject」は 2 巡目 P1 の鏡像)。⇒ `_storm_gate` は **reject 理由が出ても baseline が未確認 (pending 非空) なら最終判定せず暫定予約** (`token.reeval=True`、`totals.deferred` +1) として pending に積む。送信順が来た時 (= 先行が全て決着、`pending[0]` が自分) に `_storm_send_decision` が **確認済み値で再評価** (`_storm_baseline(st, before_seq=自分)` = 先行予約ゼロ = `confirmed_sl`): 通れば送る、reject なら `_storm_unreserve` (broker 未到達なので要求数 `sent_ts`/`sent_total` も戻す — 失敗 rollback とは別) して skipped に計数。**breaker は計数ベースで baseline 非依存なので暫定にしない** (最終 reject)。暫定予約も pending 末尾として後続の baseline になる — 後続もまた暫定になり、順に決着する。

### 2.8 breaker 窓に入るのは「broker に実際に送信した要求」だけ (PR #287 review 7/8 巡目 P1)
予約時点で窓に数えると 2 種の偽判定が出る: (7 巡目) 暫定予約が窓を埋めて上限 3 で A + 重複 2 → 4 件目が trip し、重複が冪等で取り消されても `tripped` が残る / (8 巡目) 停滞 A + 未送信 B,C で窓 3/3 の間に来た保護更新 D が gate で最終 reject され、B,C が後で timeout drop されても D (one-shot の BE/pyramiding 更新) は既に失われている。7 巡目版の「取り消し時に trip を再計算」は D の喪失を救えない (最終 reject は既に caller へ返っている) ので不完全だった。⇒ **窓入り (`_storm_count_tx`) は送信直前 `_storm_send_decision` でのみ行う** (`_storm_reserve` は暫定・非暫定とも `token.ts=None`)。従って gate 時点の breaker 判定が見るのは**送信済み要求だけ**で、未送信予約が原因の reject は構造的に起きない。送信直前には (enforce で) 暫定 token は 4 check 再評価、非暫定 token は breaker のみ再評価 (`breaker_at_send`) し、通れば窓に入れて送る。予約の取り消し (`_storm_unreserve`) は pending から外すだけで窓には触らない (入っていない)。実送信で立った trip は最終 (`test_real_trip_from_submitted_requests_is_final`)。検知のみモードでは送信直前の判定はせず窓に入れて送るだけ。

### 2.9 送信直前の再評価が唯一の最終判定 (PR #287 review 9 巡目 P1)
gate 時点の評価は未確認の pending 値に対する **pre-filter** に過ぎない。「暫定でなく」gate を通った要求も、その baseline が暫定 (後で reject され得る) なら送信時に無効になり得る: 確認済み 154.115 / P=154.350 / 暫定 A=154.270 (P 基準 monotonic) / B=154.280 (A 基準 +1 pip で通過) → P 確認 → A reject → B を breaker だけ見て送ると確認済み 154.350 を 154.280 に**緩める**。⇒ enforce では **全 token を送信直前 (`_storm_send_decision`) に確認済み baseline で 4 check 再評価**する (`_storm_evaluate(before_seq=自分, observe=False)`; observe=False で unknown_direction / allow_loosen の観測カウンタを二重計数しない)。gate は早期 reject (baseline が確認済みで reason あり / breaker) と検知ログの場所、送信直前が最終判定。P が失敗した対称ケースでは A, B とも確認済み 154.115 基準で正当と再評価され順に送られる (`test_p1_request_passing_against_provisional_baseline_survives_if_predecessor_fails`)。実装上の注意: check に渡す `last` は `_UNSET` sentinel で「自分で計算せよ」を表し、`None` は「baseline なし」の実値 (`None` を sentinel に使うと再評価時に pending 末尾 = 自分自身と比較して冪等に化ける)。

### 2.10 応答曖昧な失敗は旧 baseline に戻さない (PR #287 review 10 巡目 P1)
`OandaClient._request` は timeout / network / unknown / 5xx / 例外でも `ok=False` を返すが、PUT は broker に届いて**適用済みかもしれない**。これを確定失敗として `confirmed_sl` を旧値 (154.115) のままにし後続を起こすと、適用済み 154.400 に対して queued 154.350 が「tightening」と判定されて live stop を緩める。⇒ `_storm_failure_is_ambiguous`: **HTTP 4xx (`{"error": <int 4xx>}` — broker が応答して拒否、429 のローカル backoff も未送信) だけが確定失敗**、それ以外は曖昧。曖昧な失敗の `_storm_rollback(ambiguous=True)` は token を pending に残したまま (後続は待つ) `_storm_query_broker_sl` で broker の現 SL (openTrades.stopLossOrder.price) を照会し、取れれば `confirmed_sl` をそれに合わせる (`totals.reconciled`)。取れなければ `unresolved_sl` に記録 (`totals.unresolved`) し、(a) 以後の gate ごとに `_storm_try_reconcile` で再照会、(b) 解消まで**単調性だけ保守的 baseline** `_storm_conservative` = BUY: max(confirmed, unresolved) / SELL: min (方向不明なら confirmed) — 冪等 / dead-band は confirmed (or pending) と比較するので、unresolved 値と同値の再送は「再適用」として送られる、(c) より新しい確認 (`_storm_confirm`) で unresolved は消える。status に `trades[*].unresolved_sl` と `totals.ambiguous_failures / reconciled / unresolved / reconcile_discarded` を露出。

**版チェック (11 巡目 P1)**: broker 照会は lock 外で走るので、その間に別の確認 (queued B が tighter な stop を確認) が進み得る。照会が古い stop を捕まえて B の確認後に返ると、B の新しい `confirmed_sl` を古い値で上書きし曖昧さも消してしまい、古い値と B の間の BUY 更新が単調性を通って live stop を緩める。⇒ 照会開始時の `confirmed_seq` を `gen` として記録し、適用時 (`_storm_apply_reconcile` / rollback 側) に `confirmed_seq != gen` なら snapshot を捨てる (`totals.reconcile_discarded`)。rollback 側で進んだ確認が A より新しい (seq 大) なら A の曖昧さは上書きされて消え、A より古い (検知のみモードの並行送信でのみ起こる) なら `unresolved_sl` は残す。版チェックは unresolved の有無より先に行う (確認が unresolved を消していても discard を計数する)。

**観測の判定 (12/14 巡目 P1)**: timeout した PUT は broker 側でまだ処理中かもしれず、GET は**旧 SL を返し得る**。旧値の snapshot を「拒否された」証拠にして unresolved を消し後続を起こすと、旧値と送った値の間の BUY 更新が送られ、その後に元の PUT が着地して stop が緩む。12 巡目版は「同じ旧値が 5 s 以上安定して観測されたら `not_applied`」としたが、**timeout した PUT の server 側完了に上限はない** (14 巡目 P1: 最後の GET の後に A が着地すれば B が緩める) ので経過時間からの推定は撤回。⇒ `_storm_reconcile_verdict`: broker が**送った値**を持つ = `applied` / **送った値でも直前値でもない** = `changed` (別 actor が動かした — **現値 `confirmed_sl` はそれに更新するが、timeout した PUT の帰結は不明のままなので曖昧さは消さない**、15 巡目 P1: 直前 154.115 / A=154.400 / 外部 154.300 で 154.350 を通すと A 着地後に緩む) / **直前値のまま** = `inconclusive` (何度・何秒観測しても非決定) / 照会不能 = `unknown`。**解消は authoritative な事象のみ**: `applied` / 自分の**より新しい確認済み replacement** (`_storm_confirm` で seq が進む — 保守的 baseline を満たす ≥ unresolved の tightening が確認されれば、その後に A が着地しても A ≤ 新値なので緩まない)。それまで緩め得る replacement (旧値〜unresolved の間) は保守的 baseline でブロックし続ける = 「tightening の機会を一部失う」を「stop を緩める」より優先する。再観測は gate ごと (`_storm_try_reconcile`、最短間隔 1 s)。

### 2.12 enforce の fire-and-forget queue は有界 / ローカル backoff は窓に数えない (PR #287 review 15 巡目 P1)
**有界 queue**: 直列化下で先頭 1 件の決着に最大 ~20 s (PUT timeout + 照会 GET) かかり、予算は先頭ごとにリセットされるので、OANDA timeout 中の 3 req/s storm は予約ごとに thread を 1 本ずつ積み上げて数千 thread に達し得る。⇒ enforce では **queue = 先頭 (飛行中) + 待機 1 件**: 待機中の async token があれば新しい値を**そこへ畳み込む** (`tail.new_sl` を更新、`reeval=True`、`totals.coalesced`) — trail は最新値だけが意味を持ち、送信直前の再評価が確認済み baseline で最終判定する。sync token (caller がその値の結果を待っている) と `sending` 中の token には畳み込まない。thread は trade ごと最大 2 本。検知のみモードでは従来通り (thread/送信を変えない — fire-and-forget が元々 1 呼び出し 1 thread なのは本 PR 以前からの性質)。`STORM_COALESCE_ASYNC` class flag (CF 用)。

**ローカル backoff**: `OandaClient._request` は本物の 429 の後 5 s 間、HTTP を出さずに `{"error": 429, "message": "Rate limited, retry in Ns"}` を返す。送信直前に窓入り (`_storm_count_tx`) してから PUT を呼ぶと、この未送信呼び出しが窓を埋めて trip する。⇒ (a) 送信直前に `_storm_client_backoff_active()` (`_rate_limit_until`) を見て backoff 中なら送らず窓から外して取り消す (`totals.local_backoff`)、(b) それでも応答がローカル backoff の形なら `_storm_uncount_tx` で窓から外す (確定失敗として rollback)。本物の HTTP 429 (broker に届いた) は数える。

### 2.11 fire-and-forget の caller は network を触らない (PR #287 review 12 巡目 P2)
`_storm_get_state(network=True)` は restored trade の seed と unresolved の再照会で `get_open_trades()` を同期実行する。`modify_sl` (fire-and-forget) の caller は 0.5 s 周期の SL ループなので、broker timeout 10 s で塞ぐわけにいかない (検知のみモードでも)。⇒ `modify_sl` は `_storm_gate(network=False)` で予約だけ行い、worker `_do` の先頭で `_storm_get_state(network=True)` を呼ぶ (送信直前の再評価が seed / 再照会後の状態を使う)。gate 時点で未 seed なら baseline なし = fail-open の pre-filter、最終判定は worker 側。`modify_sl_sync` は元々 blocking なので caller で network を行う (従来通り)。

**single-flight (13 巡目 P2)**: worker が順番待ちの前に network を行うと、未 seed の restored trade への burst で worker ごとに `get_open_trades()` が飛ぶ (replacement storm が GET burst に化ける)。⇒ worker は**先頭になってから** (`_storm_wait_turn` 通過後) `_storm_get_state(network=True)` を呼び、network 部分 `_storm_network_refresh` は trade ごとの `net_lock` で single-flight (後続は lock 取得後に `seeded` / `unresolved_sl` を見て不要なら何もしない)。検知のみモード (直列化なし) でも `net_lock` で GET は 1 回。unresolved の再照会は `STORM_RECONCILE_MIN_INTERVAL_SEC`=1 s の最短間隔付き。

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
| (g)-2 | 予約時 prev_sl 記録 + rollback で復元 (1 巡目の形) | A,B 連鎖失敗後に未確認 A が confirmed_sl に残り、正当な A 再送が冪等 skip される (broker 未到達) | `test_p2_cf_prev_sl_rollback_leaves_unconfirmed_baseline` |
| (h) | `_storm_wait_turn` → 常に True (順番待ちなし、2 巡目の形) | B の worker が A より先に broker へ届き、「B 確認済み ∧ A pending」の窓が生じる | `test_serialization_cf_without_turnstile_b_can_confirm_before_a` |
| (i) | enforce flag のみ反転 (順番待ち timeout fixture) | 検知のみ = 送信 1 / drop 0 / detected.serialize 1 ⇄ enforce = 送信 0 / drop 1 | `test_detect_only_cf_enforce_is_the_only_difference_for_turn_drop` |
| (j) | 暫定化を外す (未確認 baseline でも gate で最終 reject、4 巡目までの形) | A 失敗後に正当な B (確認済み基準 +23.4 pip) が永久に失われる | `test_p2_cf_final_reject_against_pending_drops_valid_update` |
| (k) | 予約時点で窓に数える + timeout drop を rollback (要求数保持、5 巡目までの形) | 未送信 B,C が窓 3 を埋め、A 決着後の正当な更新が breaker で止まる (`tripped=True`、broker 到達 0 件) | `test_cf_turn_timeout_as_rollback_trips_breaker_with_unsent_requests` |
| (l)-1 | 予約時点で窓に数える (`_count_at_reservation`、7 巡目までの形) | broker 到達 0 件で 4 件目が trip (`sent_total=3`, `tripped=True`) | `test_p1_cf_counting_provisional_in_window_trips_before_any_send` |
| (l)-2 | 同上 + 停滞 A / 未送信 B,C の後ろに one-shot 保護更新 D (sync) | D が gate で最終 reject (False) — B,C が落ちても D は戻らない | `test_p1_cf_counting_at_reservation_rejects_protective_update_permanently` |
| (m) | 非暫定 token を送信直前に breaker だけ見る (8 巡目の形) | P 確認 → A reject の後に B=154.280 が送られ、確認済み 154.350 の stop が緩む | `test_p1_cf_breaker_only_at_send_for_non_provisional_loosens_confirmed_stop` |
| (n) | `_storm_failure_is_ambiguous` → 常に False (timeout を確定失敗扱い、9 巡目までの形) | broker が適用済みの 154.400 の後に 154.350 が送られ live stop が緩む | `test_p1_cf_treating_timeout_as_definitive_loosens_applied_stop` |
| (o) | `_storm_apply_reconcile` → 版チェックなしで適用 (10 巡目の形) | 照会中に確認された B=154.450 が古い 154.115 で上書きされ、X=154.300 が「tightening」として届く | `test_p1_cf_unversioned_reconcile_overwrites_newer_confirmation` |
| (p) | `_storm_reconcile_verdict` → 旧値の単発観測を解消扱い (11 巡目の形) | A=154.400 が後で適用されるケースで B=154.350 が届き stop が緩む | `test_p1_cf_single_old_snapshot_treated_as_rejection_loosens_stop` |
| (p)-2 | `_storm_reconcile_verdict` → 旧値 2 回目の観測で解消扱い (13 巡目の時間安定形) | 最後の GET の後に A が着地するケースで B=154.350 が届き stop が緩む | `test_p1_cf_time_based_not_applied_lets_late_landing_put_be_loosened` |
| (p)-3 | `_storm_apply_reconcile` → 第三の値で曖昧さを消す (14 巡目の形) | 外部 154.300 観測後に 154.350 が届き、A=154.400 着地後の stop が緩む | `test_p1_cf_third_value_treated_as_authoritative_loosens_stop` |
| (t) | `STORM_COALESCE_ASYNC=False` (14 巡目の形) | 停滞先頭の後ろに 30 呼び出しで 31 worker | `test_p1_cf_no_coalescing_spawns_one_worker_per_call` |
| (u) | backoff pre-check と応答形判別を外す (14 巡目の形) | HTTP ゼロのローカル 429 ×5 で `sent_total=3`, `tripped=True` | `test_p1_cf_counting_local_backoff_trips_breaker_without_http` |
| (r) | `_storm_wait_turn` → 絶対 deadline (12 巡目までの形) | 進捗している先行 3 件 (各 0.25 s) の後ろの D が予算 0.4 s で drop | `test_p1_cf_absolute_deadline_drops_protective_update_behind_progressing_chain` |
| (s) | `_storm_network_refresh` → lock なし (12 巡目の形) | 未 seed trade への 5 worker burst で GET が 5 回 | `test_p2_cf_lockless_refresh_fires_get_per_worker` |
| (g)-1 改 | 順番待ちなし + 再評価が常に冪等 True (未確認一致を即 True、2 巡目までの形) | worker 失敗前に sync が True を返し、confirmed_sl は原値のまま | `test_p1_cf_treating_pending_as_confirmed_returns_true_before_failure` |
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
