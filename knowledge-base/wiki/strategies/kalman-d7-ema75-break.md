# Kalman D7 EMA75 Break (v18f)

## Overview
- **Entry Type**: `kalman_d7_ema75_break`
- **Category**: TF (Trend Following)
- **Timeframe**: DT 15m
- **Status**: SHADOW by default; LIVE via `KALMAN_D7_LIVE_ENABLE=1` env var (rule:R1 例外, 2026-05-20)
- **Active Pairs**: USDJPY only

## BT Performance (TV Pine, 10.5mo M15)
- **N**: 68
- **WR**: 30.88%
- **PF**: 2.087
- **Net P&L**: +567.64 JPY (+0.57%)
- **Max DD**: 0.10%
- **Avg Win**: 52 JPY / **Avg Loss**: 11 JPY
- **W/L ratio**: 4.67×
- **Avg bars in winners**: 102 (~25h)

⚠️ BT 期間 = USDJPY uptrend (2025-07-01 → 2026-05-19)。Regime-bound edge。

## Signal Logic
Same entry as v17 (kalman_d7_po_dn_flip):
- Perfect Order UP transition + DIST < 3 ATR + GAP < 3 ATR + ATR Q2-Q4 + RSI < 70 + ASN/LDN/NY session

## Exit Logic
- **TP**: 2.5×ATR (EMA75 close break approximation, balanced)
- **SL**: 2.5×ATR
- **Max hold**: 120 bars (~30h)
- 1:1 RR with wider SL = more breathing room, balanced timing

## Current Configuration
- Lot Boost: default (1.0x)
- Mode: enabled, evaluated by DaytradeEngine
- Live promotion: depends on tier system

## Risk Notes
- Same as v17 sibling (regime-bound, post-hoc, single sample)

## Related
- [[kalman-d7-po-dn-flip]] — sibling (v17 variant, max-ride)
- [[kalman-d7-trail-atr]] — sibling (v18e variant, tight trail)
- [[index]] — Tier classification

## 🔴🔴 LIVE 実測 (wiki-daily-update, 2026-10-05 初計上)

### 初 LIVE fill — #957198: demo `WEEKEND_CLOSE` +3.0 ↔ broker **週末 `MARKET_HALTED` リトライ storm → 日曜オープン SL −14.7p / −¥147** (符号反転)

| 項目 | 実測 (broker tx 957197〜1022846、全数) |
|---|---|
| entry | 10-02 (金) **19:09:13Z** USD_JPY BUY 1,000u @**157.824** (demo 157.827、slippage −0.2)。emit 経路 `[LIVE_PROMOTE_EMIT] kalman_d7_ema75_break score=4.00 (primary=kalman_d7_po_dn_flip won)` + `[HOURBLOCK_CLASS_EXEMPT] H19_USD_JPY` (min-lot carve-out、R1 2026-09-02) |
| ON_FILL bracket | SL **157.689** (−13.5p) / TP **158.074** (+25.0p)。`[SLTP_CONSTRUCT] sl=atr_rrlow clamp=none lowliq=1 fastsl=0 ct=0 rn=0 mtf_tp=1.0 range_tp=0 decl_sl_p=28.8 sl_p=13.8 decl_tp_p=28.8 tp_p=29.0 entry_drift_p=0.2` ⇒ 宣言 2.5×ATR (SL 157.541) が RR<1 で棄却され ATR×1.0 + lowliq、broker TP = demo 158.117 × 0.85 ⇒ as-placed R:R 1.85 |
| demo exit | 10-02 **21:45:00Z `WEEKEND_CLOSE`** @157.857 = **+3.0 WIN** (hold 2h36m、MAFE favorable 4.9 / adverse 3.2) — **市場クローズ (≈21:00Z) 後の判断** |
| broker | 21:45:03Z から `MARKET_ORDER TRADE_CLOSE` (units ALL、FOK) → `ORDER_CANCEL MARKET_HALTED` を **32,821 回 / 47.33 時間** (10-04 21:04:50Z まで、median 5.18 s 間隔、毎時 693〜696 回、backoff / breaker なし) = **65,642 tx** (957202→1022844)。storm 自体の PnL ¥0 |
| 実際の決済 | 10-04 (日) **21:04:55Z** オープン直後 `STOP_LOSS_ORDER` @**157.677** (bid 157.677 / ask 157.763 = spread 8.6p、`halfSpreadCost` ¥43) = **−14.7p / −¥147.00**。金曜終値 157.857 → 日曜初値が SL を 1.2p 下抜け |
| demo 累計 | **N 1 / 1W / +3.0 / `promo_ev` 3.0 / `promotion: pending`** — ⚠️ **broker 真値は −14.7p**。昇格判断にこの +3.0 を使わない |

- 🔑 09-07 の `usdjpy_carry_dip_accumulator` #709598 (64,170 回 / 47h / 2.66 s 間隔) と**同一機構の 2 例目**。間隔が倍化 (5.18 s) した以外は不変 — 「金曜クローズ時に建玉があれば再発する」の予測が的中 (09-09 に「部分的に外れた」と記録したのは別族の SL storm だった)。[[project_weekend_market_halted_retry_storm_2026_09_07]]
- 🔑 demo↔broker 符号反転も 2 例目 (#709598 demo +11.6 / broker −14.1、本件 +3.0 / −14.7)。判別軸「halt 中に demo が閉じたことにした建玉」で一致 ⇒ **`WEEKEND_CLOSE` ラベルは broker 真値として使用不可** (close_reason 不信の 2 経路目、1 経路目 = SL_HIT ラベル欠陥)。[[project_demo_broker_sign_inversion_halted_exit_2026_09_07]]
- 🔴 10-02 wiki-daily は本建玉を見落とした (audit 行の書き込み遅延 + heartbeat `open_trade_count` 0)。`/api/demo/status.oanda.open_trades` の 1 が正しかった — [[2026-10-02]] 発見 6 の「カウンタの残骸」は誤り
- ⚪ 本戦略は secondary emit (primary = po_dn が勝った bar) で LIVE に出る。金曜 19Z entry × 8h cap 不発 × `WEEKEND_CLOSE` 21:45Z という経路は**構造的に halt を踏む** ⇒ 再発防止 (金曜クローズ前 flat 化 or halt 検出で retry 停止) は user 決裁待ち ([[2026-10-05]] 未決 8)

詳細: [[2026-10-05]] 発見 1 / [[kalman-d7-po-dn-flip]]
