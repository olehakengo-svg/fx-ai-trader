# Kalman D7 PO-DN Flip (v17)

## Overview
- **Entry Type**: `kalman_d7_po_dn_flip`
- **Category**: TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: SHADOW by default; LIVE via `KALMAN_D7_LIVE_ENABLE=1` env var (rule:R1 例外, 2026-05-20)
- **Active Pairs**: USDJPY only

## BT Performance (TV Pine, 10.5mo M15)
- **N**: 46
- **WR**: 23.91%
- **PF**: 3.866
- **Net P&L**: +997.28 JPY (+1.00%)
- **Max DD**: 0.11%
- **Avg Win**: 122 JPY / **Avg Loss**: 9.94 JPY
- **W/L ratio**: 12.30×
- **Avg bars in winners**: 458 (~115h)

⚠️ BT 期間 = USDJPY uptrend (2025-07-01 → 2026-05-19)。Regime-bound edge。

## Signal Logic
Perfect Order UP (close > EMA25 > EMA75 > EMA200) の **transition (start)** で LONG。
Entry filters (v16 forensic 導出):
- DIST(close-ema200)/ATR < 3.0
- GAP(ema25-ema200)/ATR < 3.0
- ATR Q2-Q4 (P20 ≤ ATR < P80)
- RSI < 70
- Session ∈ {ASN, LDN, NY} UTC (OVL/DEAD除外)

## Exit Logic
- **TP**: 5.0×ATR (PO-DN regime flip approximation, hold for max winner ride)
- **SL**: 1.5×ATR
- **Max hold**: 480 bars (~120h) — ⚠️ **live 未同期**: `daytrade` mode の 8h cap + 金曜 21:45Z クローズが優先 (2026-09-25 確定、下記 09-24 節)

## Current Configuration
- Lot Boost: default (1.0x)
- Mode: enabled, evaluated by DaytradeEngine
- Live promotion: depends on tier system

## Risk Notes
- **Regime-bound**: USDJPY uptrend continuation 前提
- **Strategy 間相関**: 同 entry の v18f / v18e と高相関 (3 spec 同時 entry 多)
- **Post-hoc selection bias**: v16 forensic で 35 cells から選択 (m=35 補正未実施)
- **Single sample bias**: 10.5ヶ月 single period

## Emergency stops
- USDJPY close < D1 EMA200 → entry 停止検討
- Aggregate (3 spec) DD > 5% → 全停止
- PF < 0.8 over N≥30 → 該当 spec 単独停止

## Related
- [[kalman-d7-ema75-break]] — sibling (v18f variant)
- [[kalman-d7-trail-atr]] — sibling (v18e variant)
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy

---

## LIVE 実測 (wiki-daily-update, 2026-09-14 更新)

### 初 LIVE fill — #859468
| 項目 | 実測 |
|---|---|
| entry | 2026-09-10T17:00:51Z / USD_JPY BUY 1,000u |
| bracket (ON_FILL) | SL **154.115** |
| exit | 2026-09-10T21:04:55Z `STOP_LOSS_ORDER` @154.344 |
| hold | **4h04m** (宣言 max 480 bars ≈ 120h に対し 3.4%) |
| broker realized | **+¥91.00 = +9.1 pip** |
| demo 記録 | **+8.2 pip** ⇒ 差 **0.9p** (原因未判定: 丸め or 推定器) |
| demo 累計 | **N=1 / WR 100% / PnL +8.2 / EV +8.2** |

⚠️ **N=1。`promo_wr` 100% / `promo_ev` +8.2 を根拠に何も判断してはいけない。** BT WR は 23.91% (PF 3.866 = 少数の大勝ち依存) で、**この 1 本は BT のペイオフ形状と真逆の「小さい勝ち」**。BT の edge は winner を 458 bars (~115h) 保持することに依存しているが、実走は **4h で SL 決済** ⇒ **BT の前提 (long hold で trend を取り切る) が実行側で成立していない**可能性。N 蓄積まで保留。

### 🔴🔴🔴 本建玉は **4 度目の runaway loop (storm 4) を引き起こした** — 本戦略が storm を出した初の非 `carry_dip` 戦略
- trail が SL を **16,837 回** replacement (tx **859471→893145 = 33,675 tx**)、**2h51m @ 3.28 tx/s**、broker エラー **0 件**
- storm 開始は entry **+1h13m** (18:13:55Z)。それ以前の 15 回は ~5 分間隔 = 正常な trail
- **直接 PnL ¥0** (replacement は無料)。深刻さは broker 側 = OANDA Japan **Gold status → REST アクセス**
- 🔑 **これにより「storm は `carry_dip` 固有」という 3 storm 分の絞り込みが破棄された** ⇒ 欠陥は戦略実装ではなく**戦略間で共有される trail / bracket 管理層**にある
- 🔑 機構は「同一価格の再発行」ではなく **(a) dead-band 不在** (SL が `154.349⇄154.350` と 1/10 pip 単位で秒間数回振動 ⇒ 等値ガードでは止まらない) **+ (b) trailing 単調性違反** (`154.350 → 154.270` = BUY の SL が 8 pip 下へ = 緩む方向、risk-increasing の独立欠陥)
- ⚠️ **本戦略の SL は宣言 1.5×ATR だが、実走の trail 挙動は宣言に存在しない** — exit 仕様の実装監査が必要

詳細: [[2026-09-11]] / [[project_weekend_market_halted_retry_storm_2026_09_07]]

### 🔑 2026-09-14 更新: storm 4 の終わり方が**別戦略の建玉で再現され、停止機構が特定された**

`usdjpy_carry_dip_accumulator` の **#893161** (09-11T11:02:36Z fill) の全数トレースで、storm 4 の終端と**同型の事象が 3 cycle だけ**観測された:
- replacement 3 回が **12:30:03→12:30:04 の約 1 秒**に収まる (154.243 → 154.260 → **154.248**) ⇒ **瞬間レートは storm 4 の 3.28 tx/s (≈1.64 cycle/s) と同じ帯**
- **3 回目の SL がその場で自己約定** ⇒ storm 4 の「最終 replacement (893145 @21:04:54) → SL 約定 (893146 @21:04:55) が **1 秒差**」と完全に同型

🔑 **⇒ storm の停止機構が確定した: 振動する trail 目標が市場を追い越し、SL が自分を撃ち抜いた時に終わる。** 本頁が 09-11 に「storm 開始は entry +1h13m」と記録した通り**開始条件**は別問題だが、**終了はガードでも目標の凍結でもない**。09-10 log の「決済の 7–11 分前に止まる = 別の停止条件がある」説はこれで最終的に破棄。

🔑 **⇒ storm と平常 trail を分けているのはレートではなく継続時間。** #893161 は 1 秒で自己約定して終わり、storm 4 は 2h51m 続いた。**同じループが同じ速さで回っている** ⇒ breaker は瞬間レート閾値ではなく **窓あたり累積 tx** で設計しなければならない。

🔴 **⇒ (b) trailing 単調性違反は 2/2 で戦略非依存に再現した。** 本建玉 #859468 の `154.350 → 154.270` (−8 pip) に加え、#893161 で `154.260 → 154.248` (−1.2 pip)。**そして #893161 ではその単調性違反の replacement こそが建玉を閉じた** ⇒ 09-11 に本頁が (a) dead-band を先に挙げた優先順位は**訂正が必要**: #893161 の段差は 1.7p / 1.2p で **1 pip dead-band を通過する**が、**単調性アサートなら止まる**。
**正しい順 = (1) 累積 tx breaker → (2) 単調性アサート → (3) dead-band** (2 と 3 は直交、両方必要)。

詳細: [[2026-09-14]] / [[usdjpy_carry_dip_accumulator]]

---

## 🔴 2026-09-16 訂正: **storm は 2 族あり、本頁 09-14 節の「停止機構が確定した」は族 B 限定だった**

`carry_dip` の 11 fill 全数トレースで、**同一価格を秒間 1 回前後で再発行し続けるだけの storm (族 A)** が 5 例見つかった。全数確定できた **#677402 (2026-08-14)** は **251 cycle / 502 tx をすべて価格 159.241 で回し、07:31:50 にループが自分で止まり、建玉はそのまま開いたまま、SL 約定は 13 分 29 秒後の 07:45:19** だった。

⇒ 🔑 **自己約定は族 B (目標が振動する型 = 本建玉 #859468 と #893161) の終了機構であり、普遍則ではない。** 09-14 に本頁が「09-10 log の『決済の 7–11 分前に止まる = 別の停止条件がある』説はこれで最終的に破棄」と書いたのは誤りで、**族 A については 09-10 の説が正しい** — 別の停止条件が実在する。破棄を撤回し、**族 A の停止条件の同定**を未着手項目として立てる。

⇒ 🔴 **ガード優先順位も再訂正。** 族 A (観測 5/7) は **同一価格の再発行**なので、09-11 に「storm 4 型を防げない」として格下げした**冪等ガードが単独で完全に止める**。本頁 09-14 節の「正しい順 = (1) 累積 tx breaker → (2) 単調性アサート → (3) dead-band」は、**冪等ガードを落としている点で不完全**。
**正しいセット = (1) 累積 tx breaker → (2) 冪等ガード (族 A、5/7) → (3) 単調性アサート (族 B の risk-increasing step、2/7) → (4) dead-band (#859468 の 0.001 単位微振動、1/7)** — 4 つすべて直交。

⚪ 本戦略の live 実績は 09-10 の #859468 以降 **fill 0 本** (システム全体で最終 live fill は 09-11 の #893161 = **5.03 日前**)。`promo_n` **1** / EV +8.2 / `enabled: true` で不変。

詳細: [[2026-09-16]] / [[usdjpy_carry_dip_accumulator]]


## 🔴 2026-09-24 更新: **LIVE fill #2・#3 — 11.37 日の途絶を破って 2 本、いずれも負け、demo = broker 0.0p 差**

| # | oanda tradeID | entry (UTC) | 価格 | ON_FILL bracket | exit | broker realized | demo 記録 | hold |
|---|---|---|---|---|---|---|---|---|
| 2 | **#893181** | 09-22 19:59:19 USD_JPY BUY 1,000u | 157.425 | TP 157.986 (+56.1p) / SL 157.254 (−17.1p) | 09-22 20:53:29 `MARKET_ORDER_TRADE_CLOSE` @157.380 | **−¥45 = −4.5p** | **−4.5** `SIGNAL_REVERSE` | 54m10s |
| 3 | **#893189** | 09-24 03:37:22 USD_JPY BUY 1,000u | 158.092 | TP 158.595 (+50.3p) / SL 157.892 (−20.0p) | 09-24 04:35:28 `STOP_LOSS_ORDER` @157.892 (slippage 0) | **−¥200 = −20.0p** | **−20.0** `SL_HIT` | 58m06s |

- **demo 累計: N=3 / 1W-2L / WR 33.3% / PnL −16.3 / EV −5.43** (`strategy_status.promo_ev` −5.43 と一致、`promotion: pending`)
- ✅ 2 本とも demo と broker が完全一致 (09-10 の #859468 は 0.9p 差) ⇒ 本戦略の `daytrade` モード推定器は汚染なし。tx 893180〜893193 に `REPLACEMENT` 0 本 = **storm なし** (09-11 節の storm 4 は再発せず)。`storm_guard` (detect-only、[[storm-guard-design-2026-09-22]]) は `evaluated` 0 — `modify_sl` が呼ばれていないので整合
- 🔴 **3 本すべて BT の前提に到達せず決済**: BT WR 23.91% / PF 3.866 は winner を ~458 bars (~115h) 保持することで成立するが、実走 hold は **4h04m / 54m / 58m**。#2 は SL 距離の 26% で `SIGNAL_REVERSE` 自主撤退、#3 は SL タッチ。~~N=3 で edge 判定は不可、ただし「長く持てない」は 3/3~~ → **09-25 訂正 (PR #299 review P1)**: 「長く持てない」は標本の問題ではなく**決定論的な live⇄BT 設定不一致** (下記)。また 3 本のうち 2 本は負け (早期 SL は BT でも想定内の経路) なので「3/3 保持不能」の証拠にならない — 保持上限を試されるのは**勝ち側**だけで、その勝ち側の観測は #1 (+8.2p、4h SL 決済) の 1 本のみ。⚠️ SL 距離 17.1p / 20.0p、TP 56.1p / 50.3p (R:R 2.5–3.3) — ~~宣言値との突合は未実施~~ → **09-25 (PR #299 review 7 巡目) 判明: 宣言 SL 1.5×ATR / TP 5×ATR は entry 時に書き換えられている** (下記 4.)
- 🔴🔑 **DD ledger は #3 の −¥200 だけを計上し #2 の −¥45 を取りこぼした** (`dd_jpy` +¥200 / broker −¥245) ⇒ [[2026-09-24]] 発見 2。`SIGNAL_REVERSE` 経路の決済が ledger に載らない仮説 (N=1)
- 🔴🔑 **2026-09-25 確定 (rule:R3、PR #299 review P1 4100250627): live は宣言 max hold 480 bars (~120h) を構造的に再現できない — 2 つの決定論的上限**
  1. **`MAX_HOLD_SEC["daytrade"] = 28800` (8h)** — `modules/demo_trader.py` の保持上限辞書に `kalman_d7_po_dn_flip` の `_ENTRY_TYPE_MAX_HOLD` override が**存在しない** (override があるのは vwap_mean_reversion / price_shock_rev_* / sweep_reversion_eurgbp_late / hull_donchian_fade / weekend_gap_fade のみ)。8h 超の建玉は `MAX_HOLD_TIME` で強制決済 ⇒ BT の winner ride (~115h) は **live で発生し得ない**。~~負け側は 8h 以内に決着するので影響なし = 片側 censoring~~ → **09-25 3 巡目訂正**: C5 (下記 3.) が **含み損の建玉を 4h で強制決済**するので負け側も打ち切られる。**どちら側がどれだけ削られるかは制約付き BT が winner / loser 別の hold・exit 分布を出すまで不明** (観測 2 敗が 1h 以内に決着したことは「BT の全 loser が 8h 内に SL に達する」ことを示さない)。確定しているのは「live の exit 分布は BT と別物」であって、劣化の向き・大きさではない
  2. **金曜 21:45Z 全建玉クローズ** (`_is_pre_weekend`、全戦略共通) — BT は bar 連続で週末を跨いで保持するが live は跨げない。480 bars@15m ≈ 5 営業日なので**上限 1 を外しても** 週内エントリの大半が金曜に打ち切られる
  4. **entry 時点で宣言 SL/TP そのものが書き換えられる** (PR #299 review 7 巡目): 本戦略は `_1H_PRESERVE_SLTP` に無いため **SL は SR ベース (nearest_support − margin、RR≥1.0 なら優先) か ATR×1.0 に置換** (宣言 1.5×ATR は捨てられる)、`_QUICK_HARVEST_EXEMPT` に無いため **OANDA へ送る TP は 85% に短縮** (demo 側 TP は宣言値のまま = demo⇄broker で TP が異なる)。 さらに `_15m_tactical_bias` が strong で entry 方向と一致すると **C0b の前に TP 距離が ×1.3** されるため、broker TP は一致時 ≈5.525×ATR / 不一致時 ≈4.25×ATR の 2 値 (PR #299 review 9 巡目)。観測 R:R 2.5–3.3 (宣言 3.33) のズレの正体はこれ。⇒ live は「保持上限 + overlay 4」の前に **entry 時点で別の SL/TP を持つ戦略**として走っている。制約付き BT は C0 (走 0′) を土台にする / 決裁肢 (a) には両 exempt 集合への登録を含める
  3. **さらに live には BT に無い exit overlay が 4 つ重なる** (PR #299 review P1 2 巡目): ATR×0.8 到達で BE (SL→建値) / ATR×1.5 到達後 ATR×0.5 幅の trail / **hold 4h 超で含み損なら `TIME_DECAY_EXIT`** (8h cap の半分時点、kalman は免除リストに無い) / 反対シグナル conf ≥ threshold+10 で `SIGNAL_REVERSE` (#893181 はこれで決済)。BT の exit は TP 5.0×ATR / SL 1.5×ATR のみなので、**live の exit 分布は 6 経路の合成で、BT とは別物**。制約付き BT はこの 6 経路を全部入れる (Codex queue 参照)
  - ⇒ **N=10 の監視計画では BT の保持仮説は検証できない** (エンジンが産めない結果を測る計画だった)。09-17 packet 6. の「exit 実装監査 (別タスク)」はこれで**結論が出た**: 不一致は実装バグではなく **BT (TV Pine、hold 無制限) ⇄ live (8h + 金曜) の仕様非同期** (CLAUDE.md「本番⇄BT 同期必須」違反)
  - **処置 (registry `kalman-d7-live-exit-spec-mismatch-disposition`、期日 2026-10-08、3 巡目改訂)**: 制約付き BT (Codex queue `20260925-0300-kalman-d7-live-constrained-bt`、C1〜C5 累積 = ルール忠実・intrabar 順序は近似 (M15 OHLC は bid/ask 0.5s 評価の BE/trail vs SL/TP 順序を決められない、順序仮定 2 方向で感度走) / C6 は近似参考値) は**診断** — どの overlay が edge を削るか・winner/loser 別の hold・exit 分布・8h 内完結 winner 比率 を出す。**C6 (SIGNAL_REVERSE) は同 mode 全戦略の signal stream + conf/score/ADX>20/含み益 ATR×0.3 保護の合成で BT 再現不能**なので、BT 単独では keep/demote を決めない (早期合成 exit は EV を上げも下げもする — 下限にならない)。期日に **user 決裁 packet**: (a) live exit を宣言仕様に合わせる (max hold を **市場 bar 数 480 本 / 市場オープン時間ベース**で実装 — 現行 L3708-3724 は wall-clock 秒なので「120h」だと週末の ~48h 休場を消費し 480 bars に届かない、休場・祝日込みで数える + 週末保持 + C3〜C6 免除 (BE / trail も宣言 BT に無い overlay なので外す) + C0 免除 = `_1H_PRESERVE_SLTP` / `_QUICK_HARVEST_EXEMPT` への登録 **+ 下流 SL 調整 (低流動性時間 +0.2×ATR / fast-SL 拡幅 / ラウンドナンバー nudge、共有経路で exempt 集合ではスキップされない。カウンタートレンド +0.25×ATR は mean-reversion 5 戦略限定で本戦略には掛からない) の免除フラグ新設 + MTF TP ×1.3 の対象外化** = **Rule 1**、週末ギャップ露出) (b) 現状維持 (BT の無い戦略と認識して執行 QA 継続) (c) shadow 降格。autopilot 単独で取れるのは通常の live 損失停止 (Rule 2、realized N ベース) のみ。~~前版「full stack EV≤0 → R2 降格」~~ は撤回
  - 分岐が出るまで: **live carve-out は維持** (原則 1、1,000u × SL ~20p = ¥200/敗 で資金時計への影響は小さい) が、**この間の fill を BT 検証の N に数えない** (estimand が違う)
- 📋 次: 毎 fill で hold 時間・exit 種別・demo↔broker 差を本節に追記 (**保持仮説の検証としてではなく執行 QA として**)。Kelly `agg_kelly` は 2 敗を受け −0.329→−0.340

詳細: [[2026-09-24]] 発見 1・2
