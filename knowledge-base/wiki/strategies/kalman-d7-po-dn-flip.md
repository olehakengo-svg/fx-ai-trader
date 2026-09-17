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
- **Max hold**: 480 bars (~120h)

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
