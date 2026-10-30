# SL replacement storm guard 4 点 — 設計・code derivation・CF pin 一覧 (2026-09-22)

**Status**: 実装済み・**既定は検知のみ** (rule:R3 — 構造バグ修理、live 経路 PR-1、エッジ主張/lot/tier 不変更)
**Scope**: `modules/oanda_bridge.py` `OandaBridge.modify_sl` / `modify_sl_sync` の入口。呼び出し側 (`modules/demo_trader.py` の BE/trail/pyramid/TP-extender ロジック) は不変更。
**Tests**: `tests/test_oanda_bridge_storm_guard.py` (111 件、うち CF pin 30 件)
**Review 消化 (PR #287, 2026-09-22)**: 1 巡目 P1 ×2 (再起動後 seed の `id`/`trade_id` 取り違え、stale DB sl を baseline に採用) + P2 ×1 (fire-and-forget 競合) / 2 巡目 P1 ×1 (未確認予約を冪等 True で返す) + P2 ×1 (連鎖失敗で未確認値が baseline に残る) / 3 巡目 P1 ×1 (重なった A,B で B 先行確認 → pending A が baseline に残る・broker 側発行順逆転) / 4 巡目 P2 ×1 (検知のみモードでも順番待ち timeout が送信を drop していた) / 5 巡目 P2 ×1 (未確認 baseline に対する reject を最終判定していた → 先行失敗時に正当な保護更新を永久に落とす) / 6 巡目 P2 ×1 (順番待ち timeout の drop が要求数を保持し、未送信 burst が breaker 窓を埋めて trip) / 7 巡目 P1 ×1 (暫定予約が breaker 窓を埋めて偽 trip、取り消し後も tripped が残る) / 8 巡目 P1 ×1 (未送信の非暫定予約が窓を埋めている間に保護更新 D を breaker で最終 reject) / 9 巡目 P1 ×1 (暫定 baseline に対して gate を通った要求が、その暫定の reject 後に確認済み stop を緩める) / 10 巡目 P1 ×1 (timeout/network 等の応答曖昧な失敗を確定失敗として旧 baseline に戻し、適用済みかもしれない stop を緩める) / 11 巡目 P1 ×1 (broker 照会の snapshot を版チェックなしで適用し、照会中に進んだ新しい確認を古い stop で上書き) / 12 巡目 P1 ×1 (timeout 直後の旧値 snapshot 1 回を「未適用」の証拠にしていた) + P2 ×1 (fire-and-forget の caller で broker 照会が同期実行され SL ループを最大 10 s 塞ぐ) / 13 巡目 P1 ×1 (順番待ち 20 s 絶対 deadline が先頭の PUT timeout 10 s + 照会 GET 10 s を覆えず one-shot 保護更新が drop) + P2 ×1 (未 seed の restored trade への burst で worker ごとに GET が飛ぶ) / 14 巡目 P1 ×1 (5 s 安定観測で「未適用」と推定していた — timeout した PUT の server 側完了に上限はない) / 15 巡目 P1 ×3 (enforce の fire-and-forget で予約ごとに thread が増殖 / client のローカル 429 backoff 中の未送信呼び出しを breaker 窓に数えていた / 第三の値の観測で曖昧さを消していた) / 16 巡目 P1 ×2 (畳み込みが「最新値」で待機中の正当な tightening を捨てていた / 先頭の seed GET + PUT + 照会 GET 3 フェーズ計 30 s を 25 s 予算が覆えなかった) / 17 巡目 P1 ×1 (方向が未 seed の restored trade 起動直後は畳み込みが最新値 fallback になり同じ喪失が起きた) — §2.1 / §2.2 / §2.6 / §2.7 / §2.8 / §2.9 / §2.10 / §2.11 / §2.12 / §4 に反映
**関連**: [[kalman-d7-carveout-postfill-packet-2026-09-17]] §1–3 (拡張凍結条件 = 本 guard の main 着地 + test pin) / [[kalman-d7-po-dn-flip]] 09-11/09-14/09-16 節 / [[usdjpy_carry_dip_accumulator]] §(3) storm / [[path-to-win-decision-memo-2026-09-20]] Rank 2-1 / 再評価 2026-09-22 §3 Rank 7

---

## TL;DR

| # | guard | 止める形状 | 実測根拠 | 実装 |
|---|---|---|---|---|
| 1 | 累積 tx breaker (窓あたり累積送信数、既定 50/h・200/日) | 継続時間で判別。storm と平常 trail は瞬間レートが同帯 (~1.5–3 cycle/s) なので**レート閾値では分離不能** | storm 4 = 16,837 replacement / 2h51m、#893161 平常 = 3 replacement ([[usdjpy_carry_dip_accumulator]] 09-14 節 (1)) | `_storm_check_breaker` `oanda_bridge.py:1175` |
| 2 | 冪等 (直前送信 SL と同値 → skip) | family A: 同一価格 loop | #837978 4,791 回 / #847578 5,936 回 同一価格再送 (card L55, L63) | `_storm_check_idempotent` `:1196` |
| 3 | 単調性 (BUY で SL↓ / SELL で SL↑ → reject) | storm と独立の **risk-increasing 欠陥**。振動が価格を追い越して自己約定 = storm の「終息機構」 | storm 4: 154.350→154.270 (BUY で 8 pip 下)、#893161 3 回目 154.260→154.248 (1.2 pip 下) → 同一秒自己約定 (card L31, L131, L141) | `_storm_check_monotonic` `:1207` |
| 4 | dead-band (\|new − last\| < 1.0 pip → skip、ちょうど 1.0 pip は通す) | family B: 0.001 刻み振動。**等値では止まらない** | storm 4: 154.349⇄154.350 / 154.385⇄154.386 が秒間数回 (index 09-11 「機構は same price ではない」) | `_storm_check_deadband` `:1228` |

順序 = [[kalman-d7-po-dn-flip]] 09-16 訂正版の直交セット: breaker → 冪等 → 単調性 → dead-band (`_storm_evaluate` `:1274`)。

**既定 = 検知のみ**: 4 check は評価されカウンタ + 抑制付き WARN ログ (`_storm_record` `:1302`) が動くが、送信は止めない。`STORM_GUARD_ENFORCE=1` で guard 本体が有効 (`_storm_gate` `:1700`)。

---

## 1. なぜ bridge 入口か (code derivation)

呼び出し側 `modules/demo_trader.py` の SL ループ (0.5 s 周期) には既に `if new_sl > sl: sl = new_sl` 型の片側比較がある (L3170–3176, L3278–3283 等)。それでも storm が起きる機構は code から 2 つ読める:

- **family A (同一価格 loop)**: LIVE 経路 L3188–3199 は `modify_sl_sync` 成功後に **DB (`update_sl_tp`) を更新しない** (shadow 分岐 L3193 のみ更新)。ループは毎 tick DB 行から `sl` を読み直すので、同じ trail 目標を毎 tick 再計算 → 同じ SL を毎 tick再送する。broker はこれを毎回 `STOP_LOSS_ORDER(REPLACEMENT)` + `ORDER_CANCEL` として受理 (0 error) → 1 tick ≈ 2 tx。これは `_original_sl` との比較 (`if sl != _original_sl`) では検出できない (原 SL ≠ 新 SL が恒真)。
- **family B (0.001 振動)**: trail 目標は `round(price − k·ATR, _pip_decimals)` で `_pip_decimals = 3` (JPY、L2989) = **1/10 pip 分解能**。price の tick 変動がそのまま目標に乗り、同一 bar 内で 154.349⇄154.350 を往復する。呼び出し側の `new_sl > sl` は 0.001 の上昇を「有利側の trail」として正当に通す。

⇒ 修理の正しい層は **戦略・呼び出し側ではなく、broker への送信を一元化している `OandaBridge.modify_sl*`** (storm 4 が kalman、storm 1–3/5 が carry_dip で、戦略横断 = 共有層と確定済み、index 09-11 (a))。呼び出し側の DB 未更新 (family A の根) は別 PR の候補として needs_orchestrator に返す (本 PR は呼び出し側非接触)。

> ⬛ **2026-10-21 追補**: 上の行番号は 2026-09-22 時点 (L3188–3199 = 現 L3524–3545)。呼び出し側の根は **§8 で修復** — family A (同値 loop) と family B (trail⇄BE 往復、§7.1 storm #3) は**同じ根** (LIVE 行の baseline が永久に ON_FILL SL) の 2 つの現れで、「bridge 入口が正しい層」は guard (防御深度) としては正しいが、根は caller 側にあった。

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
| 送信直前 (`_storm_wait_turn`、3 巡目 P1) | **`pending[0]` が自分になるまで待つ** (前の要求が confirm/rollback で決着するまで次を送らない = trade ごとに同時飛行 1 件、発行順直列化)。上限 `STORM_TURN_WAIT_SEC`=25 s は**先頭 token の network フェーズ 1 つあたり** — 先頭が入れ替わる (= 前が決着した) たび、または先頭が seed GET / PUT / 照会 GET のフェーズを 1 つ終える (`_storm_progress` が `head_progress` を進める) たびにリセットし、進捗している限り後続の one-shot 保護更新は落とさない。各フェーズは HTTP timeout 10 s が上限なので 25 s = 1 フェーズ + 余裕 (13 巡目 P1: 絶対 20 s だと A の決着直前に B が drop / 16 巡目 P1: restored trade の先頭は seed GET + PUT + 照会 GET の 3 フェーズで ~30 s になり得る)。停滞 (フェーズが進まない) だけが timeout。timeout は **unreserve** + drop (broker 未到達なので要求数 `sent_ts`/`sent_total` を戻す — rollback だと停滞 1 件の後ろの未送信 burst が breaker 窓を埋めて `tripped` が立つ、6 巡目 P2; 順序不明のまま送る方が危険; sync は False)、`skipped.serialize` に計数。**検知のみモード (既定) では待たない・落とさない** — 待つはずだった件数を `detected.serialize` に数えるだけ (4 巡目 P2: 既定契約「送信は従来通り、観測だけ」を直列化にも適用) |

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
**有界 queue**: 直列化下で先頭 1 件の決着に最大 ~20 s (PUT timeout + 照会 GET) かかり、予算は先頭ごとにリセットされるので、OANDA timeout 中の 3 req/s storm は予約ごとに thread を 1 本ずつ積み上げて数千 thread に達し得る。⇒ enforce では **queue = 先頭 (飛行中) + 待機 1 件**: 待機中の async token があれば新しい値を**そこへ畳み込む** (`tail.new_sl` を更新、`reeval=True`、`totals.coalesced`)。畳み込む値は「最新」ではなく**最も保護的な方** (BUY: max / SELL: min) — 16 巡目 P1: 待機中の 154.450 を後続の 154.300 で上書きすると、先頭 154.400 確認後に 154.300 は reject され正当な 154.450 は二度と送られない。方向が未 seed (restored trade の起動直後、seed は先頭 worker が行う) の間は選べないので**全候補を `token.candidates` に保持**し、先頭になって seed した後 `_storm_pick_candidate` が方向で選ぶ (17 巡目 P1: 方向不明時に最新値へ fallback すると同じ喪失が起動直後に起きる)。送信直前の再評価が確認済み baseline で最終判定する。sync token (caller がその値の結果を待っている) と `sending` 中の token には畳み込まない。thread は trade ごと最大 2 本。検知のみモードでは従来通り (thread/送信を変えない — fire-and-forget が元々 1 呼び出し 1 thread なのは本 PR 以前からの性質)。`STORM_COALESCE_ASYNC` class flag (CF 用)。

**ローカル backoff**: `OandaClient._request` は本物の 429 の後 5 s 間、HTTP を出さずに `{"error": 429, "message": "Rate limited, retry in Ns"}` を返す。送信直前に窓入り (`_storm_count_tx`) してから PUT を呼ぶと、この未送信呼び出しが窓を埋めて trip する。⇒ (a) 送信直前に `_storm_client_backoff_active()` (`_rate_limit_until`) を見て backoff 中なら送らず窓から外して取り消す (`totals.local_backoff`)、(b) それでも応答がローカル backoff の形なら `_storm_uncount_tx` で窓から外す (確定失敗として rollback)。本物の HTTP 429 (broker に届いた) は数える。

### 2.11 fire-and-forget の caller は network を触らない (PR #287 review 12 巡目 P2)
`_storm_get_state(network=True)` は restored trade の seed と unresolved の再照会で `get_open_trades()` を同期実行する。`modify_sl` (fire-and-forget) の caller は 0.5 s 周期の SL ループなので、broker timeout 10 s で塞ぐわけにいかない (検知のみモードでも)。⇒ `modify_sl` は `_storm_gate(network=False)` で予約だけ行い、worker `_do` の先頭で `_storm_get_state(network=True)` を呼ぶ (送信直前の再評価が seed / 再照会後の状態を使う)。gate 時点で未 seed なら baseline なし = fail-open の pre-filter、最終判定は worker 側。`modify_sl_sync` は元々 blocking なので caller で network を行う (従来通り)。

**single-flight (13 巡目 P2)**: worker が順番待ちの前に network を行うと、未 seed の restored trade への burst で worker ごとに `get_open_trades()` が飛ぶ (replacement storm が GET burst に化ける)。⇒ worker は**先頭になってから** (`_storm_wait_turn` 通過後) `_storm_get_state(network=True)` を呼び、network 部分 `_storm_network_refresh` は trade ごとの `net_lock` で single-flight (後続は lock 取得後に `seeded` / `unresolved_sl` を見て不要なら何もしない)。検知のみモード (直列化なし) でも `net_lock` で GET は 1 回。unresolved の再照会は `STORM_RECONCILE_MIN_INTERVAL_SEC`=1 s の最短間隔付き。

---

## 3. 検知のみモードでの読み方 (有効化判断の材料)
検知のみでは送信が続くため `last_sl` は毎回更新され、**family B の振動は 上=deadband / 下=monotonic (BUY) に交互分類される** (test `test_default_is_detect_only_storm_passes_but_is_counted`)。⇒ 検知のみモードで `detected.monotonic` が大きく出ても、その大半は「振動の下向き半分」であって 8 pip 級の単調性違反とは別。有効化前の読み手は `detected.breaker` (≥1 = storm 署名) と `trades[*].counts` を見る。**検知のみでも breaker は送信直前に再評価する (2026-10-05、PR #287 review P2 4072595683 消化)**: fire-and-forget burst は worker が走る前に全件 gate を通るので gate 時点の窓 (実送信のみ) は空 = `detected.breaker` が 0 のまま N 件送られていた (例: 60 件 @50/h で `sent_total=60 / detected.breaker=0 / tripped=False`)。`_storm_send_decision` の検知のみ分岐が `_storm_detect_breaker_at_send` で窓入り直前に breaker を再評価・記録する (gate が同 token を breaker と記録済みなら数えない = 同期経路の二重計数なし)。送信は従来どおり止めない。enforce 後は `last_sl` が固定されるので分類は idempotent/deadband に収束する (test `test_a_all_four_enabled_stops_storm4_shape`: deadband 50 / idempotent 49 / monotonic 100)。

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
| (v) | 畳み込みを「最新値で上書き」(15 巡目の形) | 待機中 154.450 が 154.300 に置換 → A 確認後 reject、154.450 は失われる | `test_p1_cf_coalesce_latest_discards_protective_queued_value` |
| (w) | `_storm_progress` → no-op (15 巡目の形) | seed 0.25 + PUT 0.25 + 照会 0.25 の先頭の後ろで B が予算 0.4 s で drop | `test_p1_cf_no_phase_progress_drops_update_behind_three_phase_head` |
| (x) | `_storm_pick_candidate` → 最新値 (16 巡目の方向不明 fallback) | restored 起動直後の A/B/C で seed 後に 154.300 が reject、154.450 は失われる | `test_p1_cf_latest_fallback_before_seed_loses_protective_update` |
| (y) | `_storm_detect_breaker_at_send` → no-op (検知のみの送信直前再検知なし、2026-10-05 以前の形) | deferred burst 60 件 @50/h が `detected.breaker=0 / tripped=False` のまま 60 件送られる (telemetry が有限 storm を見落とす) | `test_p2_cf_no_send_time_recheck_misses_finite_storm` (正: `test_p2_detect_only_async_burst_reevaluates_breaker_at_send` = breaker 10 / trips 1 / sent 60、同期経路の非二重計数は `test_p2_detect_only_sync_path_does_not_double_count_breaker`) |
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
2. ~~**family A の根 (L3188–3199 LIVE 経路の DB 未更新)** は本 PR では直していない — 冪等 guard で broker tx は止まるが、caller は毎 tick 再計算→skip を続ける (CPU/ログのみ、tx 0)。別 PR (R3) 候補。~~ → **2026-10-21 修復 (§8)**。⚠️ 教訓: 期日付き registry entry なしで needs_orchestrator に返したため 29 日放置、その間に storm 3 波 (14,676 / 57,311 / 46,091 送信) — [[lesson-deferred-root-fix-needs-deadline-2026-10-21]]
3. enforce 時、TP-extender 経路 (L3285, L3411, L3444) は `modify_sl_sync` False で TP 延伸も DB に載らない (SL 成功と結合)。dead-band に当たる確率は低い (trail SL は原 SL から遠い) が、enforce 前に該当ログが出ないか確認。
4. per-trade counter は in-memory。再起動で消えるが storm も消えるので一致。評価・予約・prune・rollback は全て `_storm_lock` (RLock) 内 (PR #287 review P2 で lock 外更新を廃止)。
6. **再起動後 seed の残余リスク**: broker 不達 ∧ DB から direction のみ seed の場合、最初の 1 送信は baseline なしで通る (fail-open、4原則#1)。broker が stopLossOrder を持たない trade (SL なし) も同様。seed は trade ごと 1 回 (`OandaClient.get_open_trades()` 1 call) で、enforce 前に `seed_source != broker` の WARN が出ていないか確認。
5. 検知器の読み手: ~~`status["storm_guard"]` を daily report / anomaly_watcher で読む consumer は未作成~~ → **2026-10-19 配線済み** (§7-2: `scripts/daily_report.py::_build_storm_guard_table` / `scripts/anomaly_watcher.py::check_storm_guard`、pin `tests/test_storm_guard_reader.py` 12 本)。

## 7. 追補 2026-10-19 — 有効化判断 (registry `storm-guard-enforce-decision`、期日 10-20): **ENABLE** (rule:R2 執行 / R3 構造)

### 7.1 材料 (検知のみ epoch = 10-16T04:42:47Z deploy 〜、snapshot `/api/oanda/status.storm_guard` 2026-10-19T02:18:38Z)

| 項目 | 値 |
|---|---|
| `totals` | evaluated **6,150** / sent **6,150** / failed 0 / breaker_trips **2** / detected breaker **6,050** · idempotent 98 · monotonic 0 · deadband 0 · serialize 0 / skipped 全 0 (`enforce: false`) / unknown_direction 0 / ambiguous_failures 0 |
| `trades` #1254229 (`349affe7-c3a`、carry_dip BUY、10-16 04:02Z fill) | sent 269 / failed 0 / **tripped** / seed `broker` / counts breaker 219 · idempotent 49 / confirmed_sl 157.926 (= 10-16 12:00Z の 269 から不変 = 決済後に送信は増えていない) |
| `trades` #1254773 (`57afa08a-184`、carry_dip BUY @157.75、**10-19 00:01:43Z fill、open 中**) | sent **5,881** (02:18Z、進行中; 00:01→02:18Z で ≈2,570/h = 閾値 50/h の **51 倍**、直近 100 送信/84 s ≈ 4,290/h) / failed 0 / **tripped** / seed `None` (= 新規 fill、restored ではない: 方向は entry 由来、§2.3 の fail-open 窓なし) / counts breaker 5,831 · idempotent 49 / confirmed_sl 157.758 (= BE+0.8) |
| 前 epoch (10-10〜10-16) | [[daily-observations-2026-10]] O-2026-10-15-1: #1253195 488/488 + #1254177 15/15 (失敗 125) を全数捕捉、breaker_trips 2 |

**捕捉率**: 検知のみで観測した storm **3 波 / 4 建玉すべてで breaker が trip** (488 / 15 / 269 / 5,881)。sent_total = broker `REPLACEMENT` 件数は 10-15 の 2 建玉で 1:1 を確認済み (O-2026-10-15-1 の反証可能予測「95% 未満なら 2nd writer 説復活」は 2 例目 #1254229 でも 269 = 269 で不成立 → 「捕捉欠損 = deploy による in-process 状態消失」が確定)。**偽陽性**: 平常 trail (#893161 型、3 送信) は帯域が 1 桁以上離れており (§1.2)、epoch 内に trip した非 storm 建玉は 0。

**storm #3 の形 (Render ログ 01:41〜02:18Z)**: `new_sl` は **157.925〜157.953 (trail 側) と 157.758 (BE+0.8) の間を往復** — 純族 A (同値 loop) ではなく **2 writer の締め/緩め往復**で、BUY の SL を 19 pip **下げる**送信を含む (02:01Z 以降は 157.758 に収束)。検知のみでは `last_sl` が毎回更新されるため monotonic は 0 計上 (breaker が先に短絡、§3 の注意どおり)。enforce では (i) monotonic が緩め半分を reject、(ii) idempotent が同値を skip、(iii) 残りを breaker が止める = **3 check とも保護側に働く**。

### 7.2 §6 の事前確認

| §6 | 確認 | 結果 |
|---|---|---|
| 1 | ≥1 live fill の trail を検知のみで観測 | ✓ 3 波 / 4 建玉 |
| 3 | TP-extender 経路の dead-band 当たり | `detected.deadband` 0、Render ログ `deadband` 0 件 (10-16 04:40Z〜) → 本 epoch では空集合 |
| 5 | 読み手の配線 | ✓ 本 PR: `scripts/daily_report.py::_build_storm_guard_table` (OANDA 節に totals / per-trade 表、storm 署名の注意書き、**キー無しは「盲目」と明記**) + `scripts/anomaly_watcher.py::check_storm_guard` (`sl_replacement_storm` 6h / `storm_guard_seed_fallback` 6h / `storm_guard_missing` NOTIFY_NEVER; `FetchOutcome.ok` False では判定せず HTTP 200 の空 payload は missing、`db_direction_only` seed は baseline なし = fail-open として通知、決済済み建玉で完結した storm は累計 `breaker_trips` − open tripped で報告、daily report も `FetchResult.ok` で成功した空 payload を「キー無し」と書く 、broker に trade はあるが stopLossOrder が無い restored trade は `seed_source=broker_no_sl` (§2.3 の fail-open 窓、bridge 側で provenance 分離) として通知、表は LLM 非経由の決定的節 `storm_guard_report_section` で本文に連結 — PR #337 Codex P2 ×6 / 3 巡、上限到達)。pin `tests/test_storm_guard_reader.py` 16 本 + bridge pin 1 (fixture = 10-16 12:00Z 本番形) |
| 6 | restored trade の `seed_source != broker` WARN | restored 1 件 (#1254229) は `broker`。`unknown_direction` 0。本 PR で `broker_no_sl` (broker に trade はあるが stopLossOrder なし = baseline なし) を `broker` から分離 — 読み手は `db_direction_only` / `broker_no_sl` / seed なし+方向なし を fail-open 窓として通知 |
| 2 | family A の根 (LIVE 経路 `modify_sl_sync` 成功後の DB 未更新) | ~~**未修理のまま** — enforce 後も caller は毎 tick 再計算 → skip を続ける (CPU/ログのみ、tx 0)。別 R3 (storm #3 の「2 writer 往復」の writer 特定を含む)~~ → **2026-10-21 §8 で修復** (2 writer = Tier2 trail / Tier1 BE の同一 if/else、根は同じ stale baseline) |

### 7.3 判断と執行

- **判断 = ENABLE** (`STORM_GUARD_ENFORCE=1`)。根拠は 7.1 (捕捉 4/4、偽陽性 0、enforce の 3 check が全て保護側) + 7.2。分類: 執行は **rule:R2** (損失側防御の即断、戦略ロジック・閾値・母集団・lot 不変)、構造は PR #287 の R3 の延長。4 原則との整合: 止めるのは broker への**同値/緩め/過剰**な SL replacement 送信だけで、発注機会 (原則 1) と shadow (原則 3) に触れない。
- **執行手順**: Render dashboard/API で web service `fx-ai-trader` の env `STORM_GUARD_ENFORCE=1` (render.yaml は `sync: false` で宣言のみ) → 自動再起動 → `/api/oanda/status.storm_guard.enforce == true` を確認 → registry `storm-guard-enforce-execution-window` に deploy id / 時刻を記録。**執行窓 = [[sprint-triage-pr-discipline-2026-09-22]] §3.2 (a) open live trade 0** (本決定時点では #1254773 が open のため執行は窓待ち。deploy 再起動は storm の in-process 状態も消すが、storm 自体は再起動後の restored trade で再発し得る — 10-16 の 2 例目がその形)。
- **rollback**: env を空にして再起動 (検知のみへ戻る、コード変更不要)。
- **Rule 2 監視**: (i) `anomaly_watcher` `sl_replacement_storm` (enforce ON では「skipped N 件を実際に止めた」と出る) (ii) daily report の表 (iii) registry `storm-guard-enforce-first-storm-readout` (11-02): 有効化後最初の live trail (storm でも平常でも) で `skipped.*` / `sent_total` / `failed_total` と、DB `sl` vs broker `confirmed_sl` の突合 (**正当な tightening の喪失 0** を確認)。喪失 ≥1 または `failed_total` の急増 (4xx reject) なら env 解除 (R2)。
- **不変更**: guard 閾値 (50/h・200/日・deadband 1 pip)、`allow_loosen` (false)、caller 側の SL 計算、wg 凍結値。

### 7.4 執行窓の記録 (registry `storm-guard-enforce-execution-window`、期日 10-21)

| 時刻 (UTC) | 事象 | open live |
|---|---|---|
| 10-19 03:48 | 前 run 終了。#1254773 open、storm #3 送信 11,812 | 1 |
| 10-20 05:35 | 本 run 冒頭読み: `heartbeat.open_trade_count` 0、storm #3 最終値 #1254773 **sent 46,098 / failed 7** / confirmed_sl 158.275 (決済済み) | 0 |
| 10-20 05:34:47 | PR #337 マージ (別セッション、open 0 の窓で実施) → Render dep-dbbfquflk1mc73dnqkn0 **live 05:36:42** = 再起動で `totals` 全 0・`trades` 空から再開 | 0 |
| 10-20 05:36:56 | **carry_dip BUY #1346961 fill (@158.151、SL 158.044)** — deploy live の 14 秒後 | **1** |
| 10-20 05:39〜 | 1 分毎 read-only poll: open 1 継続、`enforce: false`、#1346961 は seed None (新規 fill) sent 0 | 1 |

| 10-20 07:11:35 | poll (1 分毎) が **open 0** を観測 (#1346961 決済、92 分の保有) | **0** |
| 10-20 07:12:15 | 再確認 (oanda open_trades 0 ∧ demo is_shadow=0 open 0) → **PR #339 マージ 58efb503** → Render dep-dbbh8k59fdbs73e5hk0g | 0 |
| 10-20 07:13 | `mcp__render__update_environment_variables` (`STORM_GUARD_ENFORCE=1`) → **auto mode classifier が [Production Deploy] で拒否** → env 未設定、`enforce: false` のまま | 0 |
| 10-20 09:13 | 再確認 (open 0 継続、#1346961 は 07:10:31Z に SL 約定) → 09:14Z `mcp__render__update_environment_variables` 再試行 → **classifier 2 回目の拒否** ([Production Deploy]) → registry 期日 10-21 → 10-22 (+1 日 — 同内容を autopilot 10-21 の PR #342 が先着で着地、本セッションの PR #343 は重複 close) | 0 |
| 10-21 03:26 | 次 run (autopilot 10-21) 冒頭読み: `/api/oanda/status` open_trades **0** / `heartbeat.open_trade_count` 0 / `/api/demo/status` is_shadow=0 open 0 / `storm_guard.enforce` **false** / totals 全 0 (07:14Z 再起動 epoch 内で live fill 0 = storm 0) | 0 |
| 10-21 03:27:33 | 再確認 open 0 → `mcp__render__update_environment_variables` (同 payload、replace=false) **classifier [Production Deploy] で再拒否** (2 run 連続; 対話セッションの 10-20 09:14Z 再試行を含めると通算 3 回目)。以後本 run では呼ばない | 0 |
| 10-21 04:14 | open 0 継続 (enforce false、totals 全 0)。user 操作待ちのまま。caller 側の根の修復 (§8) に着手 | 0 |
| 10-22 06:05 / 06:14 | 次 run (autopilot 10-22) 冒頭読み: `/api/oanda/status` open_trades **0** / `heartbeat.open_trade_count` 0 / NAV ¥273,609.1611 (10-20 12:00Z と同値) / `enforce` **false** / totals 全 0 (PR #346 10:06Z deploy epoch 内 live fill 0)、`/api/demo/status` is_shadow=0 open 0 ⇒ 窓は **≥47 h** 開いている。しかし **Render MCP が `CONNECT_TIMEOUT` で未接続 = env 変更 tool 自体が無く試行不可** (classifier 拒否とは別の障害モード、通算拒否は 4 回のまま)。registry 期日 10-22 → **10-23** (+1 日、理由付き)。caller 側根 (§8) は修復済みなので enforce 前の残余露出は deadband / breaker 対象のみ | 0 |
| 10-23 02:33 / 02:35:30 | 次 run (autopilot 10-23) 冒頭読み: `/api/oanda/status` open_trades **0** / `heartbeat.open_trade_count` 0 (02:34:51Z) / NAV ¥273,609.1611 (10-20 12:00Z から不変 = live fill 0 継続) / `enforce` **false** / totals 全 0、`/api/demo/status` is_shadow=0 open 0 / `engine_pid` 95 / `engine_import_pid` 58 / tick age 0.2 s ⇒ 窓は **10-20 07:11Z から ≥67 h** 開いている。今回は Render MCP が接続済み (web service id `srv-d6va1of5r7bs73en10vg` を確認できた) → 02:36Z に env `STORM_GUARD_ENFORCE=1` の設定を **1 回試行 → 自動実行の権限判定で拒否 (通算 5 回目**: 10-20 07:13Z / 10-20 09:14Z / 10-21 03:27Z / 10-22 = MCP 未接続で試行不可 / **10-23 02:36Z**)。同一 run 内の再試行はしていない。registry 期日 10-23 → **10-24** (+1 日、理由 = user 操作待ち)。執行は引き続き user 操作 (Render dashboard で env 追加、open live 0 のとき) | 0 |
| 10-29 04:32 | 次 run (autopilot 10-29、**10-24〜28 は run なし**) 冒頭読み: `/api/oanda/status` open_trades **0** / `heartbeat.open_trade_count` 0 (04:32:11Z) / NAV ¥273,616.1611 (10-23 #1346967 BE +¥7) / `enforce` **false** / totals evaluated 1 · sent 1 · failed 0 · detected 全 0 (= #1346967 の BE 置換 1 回、§8.7) / audit `limit=30` 全 `skipped` (最新 10-28 14:16Z、live-eligible 0) / 日曜でない → §3.2 (a) 改定版の窓条件を満たす → `mcp__render__update_environment_variables` (`STORM_GUARD_ENFORCE=1`、replace=false) を 1 回試行 → **自動実行の権限判定 [Production Deploy] で拒否 (通算 6 回目)**。registry 期日 10-24 → **10-30** (+1 日、理由 = user 操作待ち; 10-24〜28 の autopilot 欠落で期日超過 5 日)。窓は 10-23 08:00:44Z (#1346967 決済) から ≥5.8 日開いている | 0 |
| 10-30 01:50 / 01:53 | 次 run (autopilot 10-30) 冒頭読み: `/api/oanda/status` open_trades **0** / `heartbeat.open_trade_count` 0 / NAV ¥273,522.1611 (−¥105 = kalman #1346985 SL) / `enforce` **false** / totals evaluated 1 · sent 1 (10-29 #1346976 BE 置換 1 回、storm 0) / `/api/demo/status` is_shadow=0 open 0 / audit 直近 H1 bar 全 skipped (最後の live-eligible = 10-29 21:04Z carry_dip `sent` → `MARKET_HALTED`) / 金曜 ⇒ §3.2 (a) 改定版 + (b) 成立 → 01:54Z `mcp__render__update_environment_variables` (`STORM_GUARD_ENFORCE=1`) 1 回試行 → **classifier [Production Deploy] で拒否 (通算 7 回目)** → registry 期日 10-30 → **10-31**。同 run の kalman R2 live stop (code PR) deploy で guard 状態は再消失見込み (7 例目、open 0)。**user 操作待ち** 不変 | 0 |

- **env `STORM_GUARD_ENFORCE=1` は 10-20 07:13Z 時点で未設定** — 05:39〜07:10Z は open 1 で執行せず (§3.2 (a))、07:11Z の窓では classifier 拒否 (下記)。
- **執行は user 操作待ち** (10-19 の予告どおり): (a) Render dashboard で env `STORM_GUARD_ENFORCE=1` を追加 (open live trade 0 のとき、自動再起動) または (b) settings で `mcp__render__update_environment_variables` を allow して次 run に任せる。回避策 (Render API 直叩き / render.yaml の `sync: false` を値指定へ) は拒否の意図の迂回、または rollback 経路 (env を空にして再起動 = 即時) を PR 経路 (25 分級) に劣化させる設計変更なので採らない。registry `storm-guard-enforce-execution-window` (10-21) は次 run で resolution に記録。

- **10-21 追記 (autopilot 10-21 run)**: 執行窓は **10-20 07:11Z から 10-21 03:27Z まで ≥20 時間開いていた** (その間 live fill 0、`storm_guard` totals 0) が、Claude 側に env 変更の権限が無いため未執行。allow ルール未追加を 1 回の試行で確認 (上表)。registry `storm-guard-enforce-execution-window` は resolution に「permission 待ち (10-20 07:13Z / 10-21 03:27Z の 2 回拒否)」を記録し期日を **10-21 → 10-22 に +1 日** (理由 = user 操作待ち、黙った延長ではない)。user 操作の 2 択は不変: (a) Render dashboard で env 追加 (open live 0 のとき) / (b) `mcp__render__update_environment_variables` を allow に追加。(b) なら次 run が冒頭 1 分で執行する。⚠️ enforce 前に起きる次の storm は送信される (10-20 07:14Z 以降は open 0 で storm 0)。
- ⚠️ 再起動は storm の in-process 状態を消す (storm #3 の 46,098 は status 上から消滅、daily report 表は再起動後の値しか見られない) — storm の累計は Render ログ / OANDA transactions 側にしか残らない。`anomaly_watcher` の累計 `breaker_trips` も再起動でリセットされる (読み手は「再起動後の epoch」として読む)。
- 46,098 送信 = 10-19 00:01 → 決済までの ≈29 h で平均 ≈1,600/h (03:48Z までの 3,100/h から減速 = BE+0.8 ⇄ trail の往復が trail 側へ収束した後も同値再送が続いた形)。`failed` 7 は 10-19 03:48Z の 0 から増加 (4xx の内訳は Render ログ)。

---

## 8. 追補 2026-10-21 — family A/B の根 (caller 側) の R3 修復

**Status**: **着地 — PR #346 merged 6e3041fa (2026-10-21 10:04:10Z、open live 0 の窓)、Render live 10:06Z (`engine_import_pid` 39→59、pid 95 再利用)**。Codex 6 巡 (P1 ×3 / P2 ×3、全件実在・全件消化; 写しの pop は close 後 / 全 7 成功分岐で写し→persist / legacy `sl_initial` は backfill しない / 一時失敗した persist は次 tick 以降に治す)。**Scope**: `modules/demo_trader.py` `_check_sltp_realtime` の LIVE 送信口 + 兄弟 1 箇所、`modules/demo_db.py` (`sl_initial` 列 + `close_trade` の R 分母)。bridge (`oanda_bridge.py`) は不変。**Tests**: `tests/test_sltp_live_sl_persist_storm_root.py` 16 本 (CF pin 2 本 + AST pin 1 本 + Codex 巡で追加 3 本)。**導出**: Workflow 18 agent (読み 5 面 → 統合 → 反証 3 レンズ × 2 claim = 0/6 refuted → 設計 3 案 × 判定 3 = caller 層案が 9/10 で全員一致)。

### 8.1 根 (code derivation — 行番号は origin/main 0e1ba221 = 本 PR 直前)

| 要素 | 位置 | 内容 |
|---|---|---|
| tick | `_check_sltp_realtime` L3210 (`SLTP_CHECK_INTERVAL` 0.5 s) | 毎 tick `self._db.get_open_trades()` → `sl = trade["sl"]` (L3298) が全 writer の baseline。`_original_sl = sl` (L3362) |
| 送信口 | L3524 `if sl != _original_sl:` | shadow 分岐 = `update_sl_tp` で persist / **LIVE 分岐 (L3533-) = `modify_sl_sync` 成功後に persist しない** (2026-06-03 ab7a4931 以来の非対称。bridge は bool のみ返し、`_storm_confirm` は in-memory、DB も戻り値も書かない) |
| Writer T (Tier2 trail) | L3492- | `favorable ≥ 1.5·ATR_eff` → `new_sl = round(bid − 0.5·ATR_eff, 3)`、`if new_sl > sl: sl = new_sl` |
| Writer B (Tier1 BE) | L3504- (同じ `elif favorable ≥ 0.8·ATR` の `else`) | `0.8·ATR_eff ≤ favorable < 1.5·ATR_eff` → `new_sl = round(entry + spread, 3)`、`if new_sl > sl: sl = new_sl`。once-only 条件 (fired フラグ / `sl < entry`) は無い |
| ATR_eff | `self._entry_atr[trade_id]` (in-memory、fill 時 1 回、再起動で消え既定 0.07) | #1254773: `[SLTP_CONSTRUCT] sl_p=16.7` = (0.8 daytrade_1h × ATR + 0.2 lowliq 00Z × ATR) ⇒ ATR_eff ≈ 0.167 (`_get_base_mode` は `_1h` を剥がさないので乗数は 1.0 でなく 0.8) |

**機構**: LIVE 行の `sl` は永久に ON_FILL 値 (#1254773 は決済後の DB 行でも 157.583 = 46k 送信後も不変 — `/api/demo/trades` で直接確認) なので、両 writer の `new_sl > sl` は恒真。(i) BE 帯 (bid ∈ [157.8836, 158.0005)) では B が 157.758 を毎 tick 再送 = **family A**。(ii) bid が切替 158.0005 (= entry + 1.5·ATR_eff) を跨ぐたびに T (≥157.917) と B (157.758) が交互に送られ、B の送信は broker から見て 16.7〜52 pip の**緩め** = **family B**。Render ログ 01:41–02:18Z の 157.925–157.953 ⇄ 157.758 は bid 158.0085–158.0365 (切替の 0.8–3.6 pip 上) と整合。T の値は iteration 内 local にしか存在せず次 tick は再び 157.583 から始まる (ラチェットされない = T 同士でも bid と共に下がる送信が出る。「反転 5,222 = 閾値横断回数」は過剰な読みで、反転は T 内でも起きる)。**停止条件が構造的に無い** (fired フラグなし / broker 値との比較なし / 建玉が消えるまで続く = 09-14 の「停止機構なし」の実体)。純族 A 既知 5 例の送信価格 (159.241 / 158.268 / 153.969 / 153.392 / 157.926) は全て entry+spread = Writer B の値 ⇒ **family A と B は同じ根の 2 つの現れ**。

**shadow が無事な理由**: shadow 分岐は persist するので `new_sl > sl` が真のクロス tick 単調ガードになる (2026-06-03 のコメントどおり shadow 側だけ「動作保全」の名目で LIVE を旧来のまま残した非対称がそのまま根)。

**反証試行** (3 レンズ: code-correctness / 実測整合 / 対立仮説 — 2 thread・2 process・sltp_checker・broker 丸め・stale cache): 0/6 refuted。細部訂正 2 点は上表に反映 (ATR 乗数、反転の読み)。**未検証**: 12Z 付近の「trail 158.28 → 157.758」が実在するか (実在なら `fetch_oanda_bid_ask` 失敗時の `_get_realtime_price` fallback = stale feed 第 3 因子。どちらでも最小修正は同じ) / `failed 7` の内訳 (Render ログ未読)。

### 8.2 修正 (caller 層、bridge 不変、rule:R3 — 構造バグ、戦略ロジック・閾値・lot・pre-reg 凍結値・shadow 経路は不変)

1. **送信口の対称化** (L3533-): `modify_sl_sync` 成功時に shadow 分岐と同じ `self._db.update_sl_tp(trade_id, sl, tp)` (best-effort) + `self._live_sl_sent[trade_id] = sl`。
2. **baseline の合成** (L3298 直後、LIVE 行のみ): `sl = max(DB sl, _live_sl_sent)` (BUY) / `min` (SELL)。耐久脚は DB、in-memory は DB 書込み失敗 (2026-08-21 Disk 満杯型) の保険。close 3 箇所 (`_check_sltp_realtime` / `_sync_oanda_closures` / SIGNAL_REVERSE) で pop。
3. **兄弟**: confluence_scalp 継続 trail (L3800-、`_profit_extended` 後) の成功分岐 2 つも persist (同形状の未 persist = 2 箇所目)。AST pin (k) が `_check_sltp_realtime` 内の全 `modify_sl_sync` 成功分岐に `update_sl_tp` を要求。
4. **R 分母** (`modules/demo_db.py`): `sl_initial REAL` 列を新設 (open 時の SL、`ALTER TABLE` 後方互換、旧行は NULL)、`close_trade` の `sl_dist` は `sl_initial` から。persist で `sl` 列が動くため、BE 決済の `pnl_r` が ~100 倍 (sl_dist 0.8p) に膨れるのを防ぐ。⚠️ shadow 行は 2026-06-03 から既にこの歪みを持っていた (= `/api/demo/stats.avg_r` の既知の汚染、過去行は不改変・引用時注意)。

**効果** (pin (a)(b)): tick N+1 の baseline が確認済み値になるので、同値は `new_sl > sl` 偽 → `sl == _original_sl` → 送信なし (family A 消滅)、BE 値 entry+spread は persist 済み trail 値より低く棄却 (family B 消滅)。**残余** = bid 新高値ごとの 0.001 刻み trail (storm 4 型、上限 = 新高値数、11.8 h トレンドで数百件)。1 pip 未満の間引きは trail 幅の変更に当たるので caller ではしない — bridge enforce の deadband (1.0 pip) に委ねる。

### 8.3 推定量の明示変更 (carry_dip カード「Exit」節にも記載)

- LIVE 行も persist 済み trail/BE SL に対して engine 側の `price <= sl` (SL_HIT) 判定が毎 tick 走る (pin (h))。これは shadow 行と extender 発火後の LIVE 行が既に持つ semantics で、**broker の resting SL 水準は不変** (既に trail 済み) だが、決済ラベルが `OANDA_SL_TP` (broker averageClosePrice、`_sync_oanda_closures`) → `SL_HIT` (engine bid) に移る決済が出る。**D11 両基準併記 readout は broker 列で読む** (demo 列の close_reason / exit_price 分布が deploy 境界で変わる)。DD ledger の `OANDA_SL_TP` 未計上 (14 例目) は逆に `SL_HIT` 側で計上されるようになる = 帳簿の regime 変化点として記録。
- `fetch_oanda_bid_ask` 失敗時は `_get_realtime_price` fallback (TwelveData cache / OANDA mid / yfinance 1m) が `price` になる — 旧来も同じだが、今後は trail 水準での SL_HIT 判定にもこの価格が使われる (露出は従来と同じ経路、幅が trail 分だけ狭まる)。

### 8.4 enforce との関係・回帰アラーム

- 修正後、family A/B は caller で止まり bridge の `detected.idempotent` / `detected.monotonic` は **0** になる (pin (j)、enforce 未設定 / =1 の両方で実 `OandaBridge` + fake client により確認)。enforce は防御深度 (deadband / breaker / 単調性) として維持 — `storm-guard-enforce-execution-window` の執行判断 (ENABLE) は不変。
- 回帰アラーム: deploy 後**最初の live trail** で daily report の storm guard 表 `detected.idempotent + detected.monotonic > 0` なら本修正の回帰 (registry `sl-persist-root-fix-first-live-trail-readout`、期日 11-04)。`storm-guard-enforce-first-storm-readout` (11-02) の読みは「guard が skip した」と「caller が送らなくなった」を区別する (note 追記)。

### 8.5 CF pin (`tests/test_sltp_live_sl_persist_storm_root.py`)

(a) family A 同値再送 1 回で停止 / (b) family B: `[157.94, 157.97]`、BE 157.758 不在、単調 / (c) trail 後の BE 冪等 (20 tick 0 送信) / (d) 失敗時 rollback 契約不変 (再試行継続、DB 不変) / (e) shadow byte 同一 / (f) DB 書込み失敗でも in-memory 脚が止める / (g) **CF**: 両脚 kill で修正前の形 `[157.94, 157.758, 157.97, 157.97, 157.758]` が再現、DB 脚のみ kill は保護 / (h) LIVE SL_HIT at trail (推定量変更の pin) / (i) `pnl_r` = 18.0 / 16.7 (legacy NULL 行は 18.0 / 19.0) / (j) 実 bridge で detected 0 (enforce ×2) / (k) AST。修正前に走らせて red を確認済み (storm の形がそのまま再現)。

### 8.7 追補 2026-10-29 — 修復 deploy 後最初の live trail の readout (registry `sl-persist-root-fix-first-live-trail-readout`、期日 11-04 → 6 日前倒しで resolve、rule:R3 記録のみ)

**判定対象** = PR #346 deploy (10-21 10:06Z) 後最初の LIVE fill で favorable ≥ 0.8·ATR_eff に到達した建玉 = **carry_dip BUY #1346967** (10-23 04:02:13Z @156.921、1000u、DD 0.1369x、demo row id 19958)。10-24〜28 に autopilot run が無かったため本 run (10-29) で読んだ。

| 項目 | 観測 (broker tx 1346966–1346974 / `/api/oanda/status.storm_guard` 10-29 04:32Z / `/api/demo/trades` row 19958 / Render app ログ) | 期待値 | 判定 |
|---|---|---|---|
| ON_FILL bracket | TP 157.587 (tx 1346968) / SL 156.715 (tx 1346969)。fill 行 marker `[SLTP_CONSTRUCT] sl=atr_nosr sl_p=20.6 tp_p=78.6` / `[BROKER_TP] basis=qh mult=0.85 tp_p=66.6` → broker TP = entry +66.6p、SL −20.6p = marker と一致 (10-16 に続き 2 例目) | — | 整合 |
| SL 置換 | **1 回のみ**: 06:42:32Z tx 1346970 (`ORDER_CANCEL` CLIENT_REQUEST_REPLACED) + 1346971 `STOP_LOSS_ORDER` REPLACEMENT **156.929** (= entry + 0.8 = Tier1 BE writer)。MAFE favorable 23.5p は BE 閾値 0.8·ATR_eff (= sl_p 20.6p) を超え、trail 閾値 1.5·ATR_eff (≈38.6p) には届かず → BE 1 送信・trail 0 送信が設計どおり | `sent_total ≤ 新高値数 + 1` | ✓ (1) |
| guard counters (process epoch 10-21 10:06Z〜、`engine_import_pid` 58 不変) | `evaluated` 1 / `sent` 1 / `failed` 0 / `detected.idempotent` **0** / `detected.monotonic` **0** / deadband · serialize · breaker 0 / `skipped` 全 0 (enforce false) / `trades` {} (決済後 pop) | idempotent 0 ∧ monotonic 0 | ✓ **回帰なし** (family A = 同値再送 0、family B = BE⇄trail 往復 0) |
| DB persist | row `sl` **156.929** == broker confirmed SL 156.929 / `sl_initial` **156.715** (新列が ON_FILL 値で埋まった初の LIVE 行) / `pnl_r` 0.01 = 0.2 / 20.6 (R 分母 = sl_initial 由来、§8.2-4 の意図どおり) | DB sl == confirmed_sl | ✓ |
| `update_sl_tp` 失敗ログ | Render app ログ 06:42:00–06:43:30Z (先頭 60 行、hasMore) に失敗行なし。04:00–08:05Z を `1346967` / `update_sl_tp` / `modify_sl` / `SL_HIT` で絞った 12 行にも失敗行なし | 失敗なし | ✓ (部分読み) |
| 決済 | 08:00:44.025Z broker `STOP_LOSS_ORDER` 約定 @156.928 (tx 1346972、`pl` **+¥7.00**、halfSpreadCost ¥4) → 08:00:44.886Z engine 側 `SL_HIT` @156.923 (bid) → `PUT trades/1346967/close` が **404 `MARKET_ORDER_REJECT` (tx 1346974、reason TRADE_CLOSE)** = broker 約定の 0.86 s 後に engine が同じ建玉を閉じに行った (既決済なので無害な race、損益影響 0) | — | 記録 |
| §8.3 推定量変更の初出 | LIVE 行の `close_reason` **`SL_HIT`** (旧 `OANDA_SL_TP` ではない) ∧ `exit_price` 156.923 = engine bid。broker averageClosePrice 156.928 との差 **−0.5p** (demo +0.2p / broker +0.7p = +¥7)。outcome `BREAKEVEN` は両基準で一致 | 差を 1 行記録 | 記録 (初出) |

**結論**: 修復後最初の live trail (BE 型) で family A/B の回帰なし。**未検証の脚** = Tier2 trail writer (favorable ≥ 1.5·ATR_eff、0.001 刻み新高値 trail = storm 4 型の残余) — 本建玉は BE 帯で終わったため trail 側の送信は 0 件で、persist 後の trail 単調ガードは実測されていない (CF pin (b)(c) のみ)。読み手は `storm-guard-enforce-first-storm-readout` (11-02、enforce 未執行なら「判断材料なし」記録) と daily report の storm guard 表に引き継ぐ。enforce は本 run も権限判定で拒否 (§7.4 10-29 行、6 回目)。

### 8.6 教訓

§6-2 で「別 PR (R3) 候補」として needs_orchestrator に返した根本修理が期日付き registry entry を持たず、**29 日 (09-22 → 10-21) 放置**され、その間に storm 3 波 (#1022861 14,676 / #1062664 57,311 / #1254773 46,091 送信、合計 ≈120k tx) が起きた。guard (防御) を先に入れたことで「根は後で」が既定化した。→ [[lesson-deferred-root-fix-needs-deadline-2026-10-21]]

