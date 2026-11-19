# JPY 台帳 writer の units 解決 + daily_report「DD防御」節の dead code 修理 (rule:R3, 2026-11-19)

**分類**: rule:R3 (構造バグ — 宣言と code の不一致、365d BT 不要、code derivation で文書化)
**出所**: [[dd-ledger-broker-close-booking-r3-2026-11-04]] §6 残余 2 / 3 (autopilot 11-04 で「別 R3 候補」として記録、11-18 まで未起票)
**動機**: データ駆動 (11-04 の code 事実 + 11-19 本番 audit 実読)。感情的動機なし
**触らないもの**: lot / シグナル / tier 閾値 (`DD_LOT_TIERS`) / 凍結値 / 母集団 (D-b: broker 実約定 ∧ 非 shadow ∧ 非 XAU) / KV 既存値 / 過去分の遡及計上 (§6-1 は本 PR でも触らない)

## 0. 結論

1. **JPY 台帳 (lot lever 0.2x の SSOT) は lot-blind だった**: `demo_trades` に `units` 列が無いため、writer `_book_equity_close` の `pip_value_jpy(instrument, trade.get("units", 0), …)` は常に 1,000 units 既定 (= ¥10/pip 慣行) で計上していた。Track C D-b (2026-07-28) の宣言「pnl_pips × units × pip価値(JPY)」と code が不一致。
2. **現行運用では計上値は変わらない** — 本番 `oanda_audit` の live fill は全て 1,000u (本日 01:10Z 実読: 直近 400 行中 `oanda_trade_id` 付き 1 行 = #1347135 carry_dip USD_JPY 1,000u filled)。min-lot carve-out (carry_dip / price_shock / kalman / weekend_gap / vix / sweep) は code で 1,000u 固定。
3. **lot↑ の瞬間に歪む構造**: `hull_donchian_fade` は code で **5,000u 固定** (2026-06-12 user 指示)、FLAT 経路は `OANDA_UNITS` 10,000 × lot_ratio。これらが live fill した時点で台帳は真の JPY 損益の 1/5〜1/10 しか動かず、DD lever が **緩み過ぎる側** (危険側) に歪む。T5 1.0x 復帰 (R1、user 専権) の前提条件として修理する。
4. 修理 = **writer が永続化済みの units を読む** だけ。送信 units は `oanda_audit` (sent / filled 行、`units` 列)、broker 約定 units は `oanda_trades.initial_units` に既にある。未解決時のみ従来の 1,000 既定で、出所を `[LEDGER_UNITS]` marker に残す (観測面を同時に作る、[[pre-send-guard-observability-r3-2026-09-23]] と同型)。
5. 同 PR で `scripts/daily_report.py`「DD防御」節の dead code (§6-3) を `/api/risk/dashboard` `dd_status` 読みに付け替え。旧 code は `/api/demo/status` に存在しない `dd` キーを読んでおり一度も描画されていなかった。

## 1. 欠陥 (code 事実)

| 層 | 場所 | 事実 |
|---|---|---|
| schema | `modules/demo_db.py` `demo_trades` | `units` 列なし (`oanda_audit.units` / `oanda_trades.initial_units` / `pending_oanda_ops.units` にはある) |
| writer | `modules/demo_trader.py` `_book_equity_close` | `trade.get("units", 0)` → 常に 0 → `pip_value_jpy` の `u = abs(float(units or 0)) or 1000.0` で 1,000 既定 |
| 宣言 | [[track-c-plumbing-audit-2026-07-28]] D-b | 「JPY 台帳: pnl_pips × units × pip価値(JPY)」 |
| 送信 units の決定 | `demo_trader.py` 送信節 (`_base_units = OANDA_UNITS (10,000)` × `_lot_ratio`、carve-out は固定値で上書き) | `_adjusted_units` は `_add_oanda_audit(units=_adjusted_units)` で sent 行に永続化、fill callback が `OandaBridge._add_audit(bridge_status="filled", units=_lot, oanda_trade_id=…)` を書く |
| 既存の読み手 | `/api/risk/dashboard` `dd_status.jpy_ledger` / `_dd_lot_mult` | 影響を受ける消費者 = lever (#1) と dashboard (#2)、11-04 §2 と同じ |

## 2. 修理

- `DemoDB.get_live_units(demo_trade_id, oanda_trade_id="") -> int | None`: `oanda_audit` の `is_live=1 ∧ units>0 ∧ bridge_status ∈ {filled, sent}` を filled 優先・id 降順で 1 行 → 無ければ `oanda_trades.initial_units` (符号は捨てる) → 無ければ None。blocked 行 (`is_live=0`) と units=0 行は読まない。
- `DemoTrader._resolve_ledger_units(trade) -> (units, source)`: row に `units` があればそれ (`row`) → DB (`audit_or_oanda`) → `(0, "default")`。DB 例外は握って default (決済処理をブロックしない、writer と同じ契約)。
- `_book_equity_close`: `pip_value_jpy(instrument, _units, …)` + `[LEDGER_UNITS] trade=… oanda=… units=… source=… pnl_jpy=…` marker 1 行 (eligible 行のみ)。
- `scripts/daily_report.py`: `build_dd_defense_section(data)` 新設 — `data["risk"]["dd_status"]` から DD% (百分率) / lot_multiplier / defensive / JPY 台帳 3 値 / pip 台帳 DD を描く。risk 取得失敗 ({} / None) は節なし、`status["dd"]` は読まない。 **PR #382 Codex P2**: app.py は DD 状態を構築できない時 `dd_status: {"error": "unavailable"}` を 200 で返す → 非空 dict が guard を通り 0.00% / off を描いていた → error 付き / `lot_multiplier` 欠落は「unavailable」と明示し数値を既定値で埋めない (fetch 失敗の扱いと同じ原則、pin 2 本追加 = 6 pin)。

## 3. 陽性対照 / tests

`tests/test_dd_ledger_units_resolution_r3.py` (8 pin): audit 5,000u → ¥500/10p (1,000 既定の ¥100 ではない) / 未記録 → 1,000 既定 `source=default` / 1,000u audit → 旧実装と同値 (現行運用 byte 不変) / `oanda_trades.initial_units=-3000` → 3,000 / filled > sent、blocked・0 は無視 / sent のみでも読める / row units 最優先 / 非 eligible 行は marker なし。
`tests/test_daily_report_dd_section.py` (4 pin): 本番 dd_status 実値 (11-19 01:10Z: dd_pct 0.1002 / lot 0.2 / peak ¥359,288.47 / current ¥323,293.23 / dd ¥35,995.24 / pip 1,322.6) で描画 / preprocess_status に含まれる / risk 不在で空 / 旧 `status["dd"]` を読まない。
既存 `test_dd_ledger_books_broker_closes_r3.py` / `test_track_c_plumbing.py` / `test_daily_report_fetch_status.py` は不変で green (62 passed)。

## 4. 本番観測 (2026-11-19 01:10Z、価格のみ・outcome 非結合)

- open live 1 = **#1347135** `usdjpy_carry_dip_accumulator` USD_JPY BUY 159.22 (11-18 15:03:59Z fill、**live fill 0 の 9.3 d が終了**)、audit `units=1000 filled`、DB sl 159.229 (BE+0.9p 移行済み) / tp 159.97、OANDA NAV ¥271,922 / unrealized +¥205。storm_guard `enforce=true`、`evaluated 1 / sent 1 / skipped 0` = PR #380 再起動 (14 例目) 後の初 live 送信。
- `/api/risk/dashboard` `dd_status`: dd_pct 0.1002 / lot 0.2 / `eq_peak_jpy` 359,288.47 / `eq_current_jpy` 323,293.23 / `dd_jpy` 35,995.24 / `dd_pips` 1,322.6 / defensive true。
- registry `dd-ledger-broker-close-first-booking-readout` (11-20): #1347135 が TP 159.97 で broker 決済されれば `OANDA_SL_TP` 初例 = 読み取り条件の前半が初めて観測可能 (units 1,000 なので「pnl × ¥10/pip」の条件文は不変)。11-20 run で判定、0 件なら +14 日の規則。

## 5. 残余 (本 PR で触らない)

1. §6-1 過去分の遡及再アンカー (KV データ移行 = 別 R3、tier 0.20 不変で緊急性なし) — 不変。
2. 部分約定 (OANDA FX の 1,000u で未観測) は filled 行の `units` = 要求 units。約定 units と差が出る lot で live 化する時は `oanda_trades.currentUnits` 読みを追加する (R1 lot↑ packet の同梱要件として記録)。
3. `[LEDGER_UNITS]` marker の読み手は本番ログ grep のみ (wiki-daily への転記は未実装)。初回 live 決済で `source=audit_or_oanda units=1000` が出ることを 11-20 readout に併記する。

## 6. 参照

[[dd-ledger-broker-close-booking-r3-2026-11-04]] / [[track-c-plumbing-audit-2026-07-28]] / [[sprint-0922-close-review-2026-10-21]] §4 #6 / [[2026-11-19-session]]
