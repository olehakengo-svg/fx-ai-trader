# carry-dip 2026-08-27 shadow 落ち — 完全因果チェーン一次証拠保全

**保全日**: 2026-09-10 (rule:R3 — Render ログ retention 30 日により原本は ~2026-09-26 に消滅するため即日保全)
**対象イベント**: 2026-08-27T16:02Z の `usdjpy_carry_dip_accumulator` (live 資格セル、T8 min-lot carve-out 契約) が `is_shadow=1` で記録された件
**registry**: `carry-dip-live-to-shadow-drop-cause` (prereg-trigger-registry.json #49) — 本ファイルで RESOLVED
**関連**: [[lesson-live-fill-estimand-shadow-conflation-2026-09-03]] / [[hourblock-class-exemption-prereg-2026-09-02]] / [[blocker-refutation-2026-09-10]] kb-03

---

## 1. 取得方法 (再現手順)

- **ソース**: Render MCP `list_logs` / workspaceId=`tea-d6va0dia214c7386glv0` / resource=`srv-d6va1of5r7bs73en10vg` (web service, fx-ai-trader.onrender.com)
- **窓**: `2026-08-27T15:45:00Z` 〜 `2026-08-27T16:20:00Z`、text filter=`carry_dip`、direction=forward
- **結果**: hasMore=false = 窓内の carry_dip 該当行は下記が**全件**。15:45〜16:02:10 に carry_dip 行は存在しない (最初の発火が 16:02:10)
- **instance**: `srv-d6va1of5r7bs73en10vg-hj8f9` (全行同一 instance、level=info, type=app)
- **取得日時**: 2026-09-10 (retention 期限内)

## 2. 因果チェーン原文 (ログ ID 付き、時系列)

イベント本体 — QUALBAR emit → H16 静的 block で shadow 化 → OANDA SKIP → shadow 行として記録:

| # | timestamp (UTC) | log ID | message (原文) |
|---|---|---|---|
| 1 | 2026-08-27T16:02:10.131169405Z | `0bb2f73c-f349-4150-9113-5149872f2cd6` | `[usdjpy_carry_dip_accumulator] QUALBAR bar=2026-08-27 15:00:00+00:00 rsi=44.0 close=159.255 ceiling_pass=True blackout_pass=True dedup_pass=True cooldown_pass=True emit=True` |
| 2 | 2026-08-27T16:02:11.017229782Z | `b0c52366-6e51-414c-a4d6-a043083582b2` | `[DemoTrader] [SHADOW] H16 USD_JPY block: usdjpy_carry_dip_accumulator → shadow` |
| 3 | 2026-08-27T16:02:11.017258513Z | `bd1f4b3e-edfa-4905-a5d8-8110d7f2348e` | `[DemoTrader] [MTF_MONITOR] USD_JPY entry=usdjpy_carry_dip_accumulator signal=BUY mtf=range_wide d1=0 h4=0 vol=normal` |
| 4 | 2026-08-27T16:02:11.017267013Z | `4365b795-502d-449a-97b1-81e07da7f5e6` | `[DemoTrader] [SENTINEL_BLOCK_DIAG] usdjpy_carry_dip_accumulator candidate built but shadow-downgraded before OANDA promotion (mode=daytrade_1h, instrument=USD_JPY)` |
| 5 | 2026-08-27T16:02:11.017271463Z | `3560c0e2-a6f1-47af-9c8e-5f81ffde0ad2` | `[DemoTrader] [SENTINEL_BLOCK_DIAG] usdjpy_carry_dip_accumulator OANDA skipped after candidate build: shadow_tracking (mode=daytrade_1h, instrument=USD_JPY, shadow=True)` |
| 6 | 2026-08-27T16:02:11.017276133Z | `7ddc53d8-0f74-46e1-ab03-d6758a338885` | `[DemoTrader] 🔗 OANDA: [SKIP] usdjpy_carry_dip_accumulator — Reason: shadow_tracking` |
| 7 | 2026-08-27T16:02:11.017282624Z | `c2379481-3244-4980-9905-e6e53895177b` | `[DemoTrader] 🕐 📥 IN [1Hブレイクアウト(KSB+DMB)]: BUY @ 159.266 \| SL 159.179(8.7p) TP 160.061(79.5p) RR1:9.2 \| Type: usdjpy_carry_dip_accumulator \| Conf: 65% \| 理由: ✅ Carry+cost-push UP drift 順張りロング / ✅ 押し目 RSI(14)=44.0 < 45 / ✅ 壁直下回避 close 159.255 < 159.5 \| ID: 923768bd-2dc \| 📊 slip=+0.50p spread=0.8p 📐 1.50R×1.3E×0.20B=SEN → 1000u [N=9 edge=14 DD20% USDJPY_CARRY_DIP_MIN_LOT] CD=0s` |

### 窓内の後続行 (再発火は全て dedup で遮断 — drop 原因とは無関係だが原文保全)

同一 bar (15:00 UTC bar) の QUALBAR emit=True が 16:03〜16:19 に毎 tick 繰り返され、全て `[ORDER_BAR_DEDUP] blocked usdjpy_carry_dip_accumulator USD_JPY BUY: bar_ts=2026-08-27T16:00:00+00:00` で遮断 (計 21 回)。例外 1 件のみ:

| timestamp (UTC) | log ID | message (原文) |
|---|---|---|
| 2026-08-27T16:04:16.791468753Z | `193f2c3a-30b0-47d5-b259-ca6bdde8ffa2` | `[DemoTrader] [SENTINEL_BLOCK_DIAG] usdjpy_carry_dip_accumulator blocked at: same_price_3pip` |

代表 dedup 行 (初回): 2026-08-27T16:03:20.420693971Z `b8902bdf-d14b-4a57-b813-4db73480a8b4` `[DemoTrader] [ORDER_BAR_DEDUP] blocked usdjpy_carry_dip_accumulator USD_JPY BUY: bar_ts=2026-08-27T16:00:00+00:00`
(残り 20 件の log ID: 88072dde / f234fd9e〔16:05:27.732〕 / 6f17d6d3〔16:05:27.781〕 / dbdad8da / 59ff7797 / 3288e283 / dfcd10c9 / 104bd21d / 03b7ed33 / 0de2ee0c / 6ab90588 / f2f968ca / e7276a0f / 0772de4c / 95212eb6 / c2ae870f / aa696dbb / 32ac8159 / c75ee118 / fd7dbce5 / 5da2d73a / 912f0333 / 8d8dfb15 / 6e372aa5 — timestamp 順、原本消滅後も ID で本取得の再検証可能)

## 3. DB 行との突合 (本番 API、2026-09-10 取得)

`GET https://fx-ai-trader.onrender.com/api/demo/trades?status=closed&date_from=2026-08-27&date_to=2026-08-28&mode=daytrade_1h`:

```json
{
 "id": 16624,
 "entry_time": "2026-08-27T16:02:10.959846+00:00",
 "instrument": "USD_JPY",
 "direction": "BUY",
 "entry_price": 159.266,
 "pnl_pips": 15.5,
 "outcome": "WIN",
 "close_reason": "SL_HIT",
 "is_shadow": 1,
 "oanda_trade_id": "",
 "mode": "daytrade_1h",
 "entry_type": "usdjpy_carry_dip_accumulator",
 "dedup_violation": 0
}
```

- entry_time はログ #1〜#7 (16:02:10.13〜16:02:11.02) と一致。entry_price 159.266 = ログ #7 と一致
- `is_shadow=1` ∧ `oanda_trade_id=""` = 厳格分離基準でも shadow 確定
- `close_reason="SL_HIT"` ∧ `outcome="WIN"` +15.5p は既知のラベル衝突 (BE/トレール利確も SL_HIT を名乗る — MEMORY `project_sl_hit_label_collision_2026_08_07`、2026-08-07 PR #167)。勝敗判定は outcome/pnl_pips 側が正

## 4. 確定原因

**alpha_scan H16-20_USD_JPY 静的 hour block** (`modules/demo_trader.py` の `_tick_entry` 内 USD_JPY H16-20 gate — 現行 commit `1edd2ce2` で L5975-5983。block ラベルは `alpha_scan(H16-20_USD_JPY,EV=-2.4)`、shadow-eligible セルは `[SHADOW] H{hour} USD_JPY block` 経由で shadow 化)。

- 16:02 UTC = H16。QUALBAR (戦略内部 gate) は全通過 (`emit=True`) → `_tick_entry` の静的 hour block だけが live→shadow 降格の**唯一の**分岐
- registry #49 が仮説列挙していた spread / HTF / DD defensive / cooldown / lot floor / carve-out は**いずれも発火していない** (ログ窓内に該当行なし。spread=0.8p 正常、cooldown CD=0s、MTF は monitor のみで block せず)
- 4原則 #3 と整合: 静的時間ブロックは LIVE 転送側の winning-location フィルタとして機能し、shadow データは削られず記録された (設計どおりの挙動であって障害ではない — ただし live 資格セルの機会損失 +15.5p 相当が実測された)

## 5. 再発性: ゼロ確定

commit `0268ad09` (2026-09-04、rule:R1 user 承認 2026-09-02「どちらも進めて」) で `_STATIC_HOURBLOCK_CLASS_EXEMPT = _AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` が導入され、`usdjpy_carry_dip_accumulator` は同 frozenset の所属メンバー (min-lot 1000u 契約、2026-06-12)。H16-20 gate は現行コードで `_hourblock_class_exempt` 分岐 (L5975-5977) により本セルを免除し `[HOURBLOCK_CLASS_EXEMPT]` marker 付きで通過させる — **同一原因による shadow 落ちの再現経路は存在しない**。免除の巻き戻しは registry `hourblock-class-exempt-r2-rollback` (marker 付き live N≥10 ∧ pooled EV<0 → R2 撤去) が管理。

## 6. 消滅リスクの記録

Render ログ retention 30 日 → 本イベントの原本ログは **~2026-09-26 に恒久消滅**。以後、§2 の log ID・timestamp・原文が一次証拠の代替 SSOT となる。
