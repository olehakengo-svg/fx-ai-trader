# DD 台帳が broker 側決済 (`OANDA_SL_TP`) を計上しない — 消費者棚卸しと R3 修理の code derivation (2026-11-04)

**分類**: rule:R3 (構造バグ、365d BT スキップ、code derivation のみ)。発見: [[2026-10-20]] 発見 3 (wiki-daily)。registry `dd-ledger-nonbooking-consumer-audit` (11-07、[[sprint-0922-close-review-2026-10-21]] §4 #6(a))。修理 PR: autopilot 2026-11-04 (`_book_equity_close` 一本化)。

## 0. 結論

- **(a) 修理** を採る。close review §4 #6 の両レンズ反証「ledger は 0.2x 判定の入力ではない → (b) 注記で足りる」は **code 事実で反証**: DD lot multiplier (`_dd_lot_mult`、live lot の 0.2x lever) の SSOT は JPY 台帳 (`eq_peak_jpy` / `eq_current_jpy`) であり、起動時 (`modules/demo_trader.py` Track C D-b 復元節) と決済時 (台帳 writer) の両方で `get_dd_lot_multiplier(JPY DD)` から再計算される。台帳は lever の入力そのもの
- 欠陥の向き (実測): 未計上集合は **net +212.7 pip (17 件、snapshot 窓)** = 台帳 DD が真の strategy DD より**大きく**出る (悲観側)。lever は安全側 (締まり過ぎ) に歪み、KPI 読み手 (index Defensive 行 / risk dashboard `dd_pips`) は 155〜213 pip 悪い側に偏る。ただし 10-20 の −10.7p のように損失側の未計上も起きる = 向きは構造的に不定 → 注記では済まない
- 修理は writer の一本化のみ。lot / シグナル / tier 閾値 (`DD_LOT_TIERS`) / 凍結値 / 母集団 (D-b: broker 実約定 ∧ 非 shadow ∧ 非 XAU) は不変。過去分の遡及計上は**しない** (§6 残余)

## 1. 欠陥 (code 事実)

決済の DB write は 2 経路ある:

| 経路 | 場所 | close_reason | 台帳 writer (PR 前) |
|---|---|---|---|
| engine 側 (SL/TP/BE/trail/horizon/halt を engine が判定して close) | `_main_loop` の `self._db.close_trade(trade_id, price, close_reason, …)` 直後 | `SL_HIT` / `TP_HIT` / `horizon` / `WEEKEND_CLOSE` / … | **あり** (`_is_eq_eligible` ブロック: pip 台帳 + JPY 台帳 + `get_dd_lot_multiplier` + KV 永続化) |
| broker 側 (OANDA が SL/TP 注文で先に決済、engine は `get_trades(state=CLOSED)` で同期) | `_sync_oanda_closures` の `self._db.close_trade(trade_id, close_price, "OANDA_SL_TP", …)` | `OANDA_SL_TP` | **なし** — DB close + MAFE + `_trade_map.pop` のみ |

Track C D-b (2026-07-28) は writer を engine 側にだけ置いた。carry_dip / kalman の TP はほぼ全て broker 側 `TAKE_PROFIT_ORDER` で約定するため ([[2026-10-29-session]] exit 棚卸し: TP 2 / ON_FILL SL 12 / BE 8 / trail 7 / halt 1 のうち broker 先行分)、**勝ち側の決済が系統的に台帳から抜ける**構造だった。

## 2. 消費者棚卸し (registry condition 前半)

| # | 消費者 | 読む値 | 台帳依存 | 影響 | 判定 |
|---|---|---|---|---|---|
| 1 | **DD lot multiplier (`_dd_lot_mult`)** = live lot の 0.2x lever、pyramiding stage gate (`_dd_lot_mult` 参照)、edge-cell lot (`_edge_cell_lot × _dd_lot_mult`) | JPY 台帳 DD% → `DD_LOT_TIERS` | **直接 (SSOT)** | 未計上 +212.7p ≈ ¥2.1k (¥10/pip 慣行) ≈ 0.59pt。本番台帳 DD 10.08% → 修正後 ≈9.5%、tier 0.20 (≥8%) は不変。境界 8% まで 1.5〜2.1pt = 次の数 fill で跨ぎ得る帯 | **(a)** |
| 2 | `/api/risk/dashboard` `dd_status` (`dd_pips` / `dd_pct` / `jpy_ledger` / `lot_multiplier` / `defensive_mode`) + `compute_risk_dashboard(lot_multiplier=dd_lot_mult)` (Kelly 推奨の lever 倍率) | KV `eq_*` / `dd_lot_mult` | 直接 | 表示値が 155〜213 pip 悪い側 | (a) |
| 3 | wiki-daily → `index.md` Defensive 行 (「only SL_HIT is booked」rule の計数を 17 例目まで追跡中) | #2 | 間接 | 読み手は既に非計上を知っており **real DD (broker NAV)** を併記している | (a) 後は計数終了 |
| 4 | `scripts/daily_report.py` 「DD防御」節 | `status["dd"]` (`/api/demo/status`) | — | **dead code**: `/api/demo/status` に `dd` / `drawdown` キーは存在しない (2026-11-04 実測 keys 40 個に無し) → 節は一度も描画されない | 消費者ではない (別 R3 候補: 節を `risk/dashboard` に付け替えるか削除) |
| 5 | `scripts/weekly_audit.py` (LLM prompt に risk JSON を 2,000 字で dump) | #2 | 弱 | `dd_status` は JSON 末尾 (offset 1,772 / 4,238 字) → 先頭 2,000 字に `dd_pct` まで入るが大半は切断 | 消費者 (弱) |
| 6 | `scripts/anomaly_watcher.py` (monitor alert) | — | なし | DD 参照ゼロ (grep 実測) | 消費者ではない |
| 7 | `tools/edge_cell_watchdog.py` (ACCOUNT_DD_GT_8 / rolling 5d DD) | **broker NAV** (`lock_nav` vs `current_nav`) | なし | 台帳非依存 | 消費者ではない |
| 8 | `tools/check_live_source.py` | `n_total_trades` のみ | なし | — | 消費者ではない |
| 9 | F4 NAV floor 資金時計 (`tools/nav_floor_projection.py`) / Defensive 行の real DD | broker NAV | なし | — | 消費者ではない |
| 10 | MC ruin gate (`_get_ruin_probability`) | closed trades (台帳ではない) | なし | — | 消費者ではない |

→ 台帳の消費者は **#1 (lever) と #2 (dashboard)** に集約され、#1 が live lot に直結するため「注記して KPI から外す」(b) は成立しない。

## 3. 実測 (estimand 宣言)

- 母集団: PROD `/api/demo/trades?limit=4000&include_shadow=false` (2026-11-04 02:30Z、snapshot 下限 entry_time 2026-08-21T12:20Z) の `status=CLOSED` ∧ `is_shadow=0` ∧ `oanda_trade_id≠''` ∧ 非 XAU ∧ `exit_time ≥ 2026-07-28` (JPY 台帳アンカー日) = **42 行**。計数 = close_reason 別の件数と pnl_pips 合計 (demo pnl、broker realized は読まない)
- `OANDA_SL_TP` **17 件 / +212.7p** (carry_dip 12 / kalman 5、全て USD_JPY BUY; 最大 +61.0 (10-19 #1254773 TP)、最小 −10.7 (10-20 #1346961)) / `SL_HIT` 12 / −172.7p / `horizon` 9 / −57.1p / `WEEKEND_CLOSE` 2 / +14.6p / `MAX_HOLD_TIME` 1 / +5.1p / `SIGNAL_REVERSE` 1 / −4.5p
- wiki-daily 10-20 の「14 例 / 155.0 pip」は別窓 (同 rule の計数、snapshot 上限 800 行) — 本棚卸しは 17 / +212.7p を採る。両者の差 (3 件 / +57.7p) は窓の違いで、符号・桁は一致
- 台帳 (11-04 02:30Z `/api/risk/dashboard`): `eq_peak_jpy` ¥359,288.47 / `eq_current_jpy` ¥323,074.23 / `dd_jpy` ¥36,214.24 / `dd_pct` **10.08%** / `lot_multiplier` 0.2。broker NAV ¥272,822.16 (real DD −24.0%) との差 ¥50,252 は SVK 固定費・financing・アンカー前残差を含み、台帳の設計上の対象外 (台帳 = strategy fill のみ)

## 4. 修理 (PR 後)

- `DemoTrader._book_equity_close(trade, pnl) -> bool` を新設 (engine 側 writer ブロックを**そのまま**メソッド化: 母集団判定 → pip 台帳 → JPY 台帳 → `get_dd_lot_multiplier` → REDUCTION/RECOVERY ログ → KV 永続化 best effort)
- engine 側 close 経路は同ブロックを `self._book_equity_close(trade, pnl)` に置換 (挙動不変)
- `_sync_oanda_closures` は `if "error" not in result:` 分岐の末尾 (`_trade_map.pop` 直後) で `self._book_equity_close(demo_trade, pnl)` を呼ぶ
- 冪等性: `close_trade` は `status='OPEN'` の行だけ CLOSED に更新し、二重 close は error dict → writer は成功分岐からしか呼ばれない。両経路が同じ建玉を競合しても計上は 1 回
- CF pin: `tests/test_dd_ledger_books_broker_closes_r3.py` 8 本 (CF 2: broker 決済で台帳 / lever / KV が動く (7.99% → 8%+ で 0.40 → 0.20) / 対称 4: shadow・id 空・XAU は不変、eligible は計上 / 冪等 2: 二重 sync・error 経路 / AST 1: 両経路が同一 writer、`_eq_current_jpy +=` は writer 内に 1 箇所)

## 5. 読み手 (deploy 後)

registry `dd-ledger-broker-close-first-booking-readout` (11-20): deploy 後最初の live 建玉が broker 側で決済 (`close_reason = OANDA_SL_TP`) された時、`/api/risk/dashboard` `jpy_ledger.eq_current_jpy` が **同 tick で** demo pnl × ¥10/pip (¥10/pip 慣行、§6) だけ動くこと (wiki-daily の「only SL_HIT is booked」計数が増えないこと)。価格のみ、outcome 非結合。

## 6. 残余 (本 PR で触らない)

1. **過去分 17 件 / +212.7p は遡及計上しない** — 台帳の一回限り再アンカー (D-a 型: broker 実測から `eq_current_jpy` を再基準化) は KV データ移行 = 別 R3 (起動時 flag `eq_jpy_ledger_v2` 方式)。現状の歪みは悲観側 (lever 締まり過ぎ) で原則 1 には反するが tier 0.20 は不変のため緊急性なし
2. **`demo_trades` に `units` 列が無い** → `pip_value_jpy(instrument, trade.get("units", 0), …)` は常に 1,000 units 既定 (= ¥10/pip 慣行、index Defensive 行が既に明記)。defensive 0.2x 期の live fill は min-lot 1,000 のため現状は一致するが、lot↑ 時に JPY 台帳が lot-blind に戻る。D-b の「pnl_pips × units」宣言と code が不一致 = 別 R3 候補 (units は `oanda_trades` / audit 行から取得可能)
3. `scripts/daily_report.py` 「DD防御」節の dead code (§2 #4)

## 7. 参照

- [[sprint-0922-close-review-2026-10-21]] §4 #6(a) / [[2026-10-20]] 発見 3 / [[track-c-plumbing-audit-2026-07-28]] (D-b) / [[mc-ruin-dashboard-artifact-2026-08-05]] / [[daily-observations-2026-11]] O-2026-11-04-1 / [[2026-11-04-session]]
