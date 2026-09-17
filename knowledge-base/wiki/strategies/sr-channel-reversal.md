# SR Channel Reversal

## Overview
- **Entry Type**: `sr_channel_reversal`
- **Category**: MR (Mean Reversion)
- **Timeframe**: Scalp/DT
- **Status**: FORCE_DEMOTED + 🔴 RETIRED (2026-06-12, rule:R2 — `SHADOW_RETIRED_STRATEGIES` で Shadow 含め全ペア恒久停止) — v8.9: Post-cut N=17 WR=11.8% instant death 87.5%; v9.1 PAIR_PROMOTED 死コード削除; v9.x (2026-04-20) demo_db legacy override も削除
- **Active Pairs**: none (shadow only)

## BT Performance (365d, 15m)
BT data not available for this entry_type in comprehensive scan.

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| sr_channel | USD_JPY | 10 | 1 | 9 | 10% | -25.3p |

## Signal Logic
Support/resistance channel reversal. Identifies price channels bounded by SR levels and enters reversal trades when price reaches channel boundaries. Expects price to oscillate within the channel, fading moves to the extremes.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED globally
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: **なし** (v9.1 で EUR_USD 削除, v9.x 2026-04-20 で demo_db legacy override も削除。Historical: EUR_USD 5m EV=+0.231 N=17 WR=70.6%)

## 2026-04-20 判断履歴 (Priority 2 PAIR_PROMOTED 監査)
EUR_USD BT は 365d DT 15m で発火 0, 180d Scalp も GBP_JPY 5m (N=70 EV=+0.122) のみ正EV で
Gate1 (EV≥+0.2) 未通過。

**Live 実績 (EUR_USD, post 2026-04-07):**
- N=26 (shadow=18, live=8) WR=19.2% EV=-1.196 PnL=-31.1p — **壊滅的**

全 Gate 不通過 → demo_db legacy override 削除。参照: [[pair-promoted-candidates-2026-04-20]], [[shadow-baseline-2026-04-20]]

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy

## 2026-06-12 Edge Factor Audit #4 — 🔴 KILL 確定 (恒久退役)

clean N=584 の要因解析で退役確定。詳細: [[edge-factor-audit-2026-06-12-sr-channel-reversal]]

- friction 1.71p = TP 7.2p の **23.7%**、BE-WR 35.7% vs 実測 25.0%、SL_HIT 56.2% (シリーズ最悪)
- **全 8 pair×dir セル net 負け** (USD_CHF BUY +0.35 は N=12 Wilson 0.138 のノイズ)、SIZE lever 対象なし
- 敗者 MAFE favorable 中央値 0.2p — エントリーに予測力なし
- 統合先なし: SR 生存者 [[sr-anti-hunt-bounce]] は別思想 (anti-hunt)、DT 版 [[dt-sr-channel-reversal]] は net −1.07
- per-cell registry が EUR_USD/USD_JPY のみ列挙 → GBP_USD/USD_CHF 漏れ (30d N=159) を strategy-level で封鎖
- 🟠 副次: dt_sr_channel_reversal は gross +2.25 (SR family 最高) が friction 3.32p に食われ net 負け → tight-spread pair 限定の follow-up 仮説 (本 kill とは別件)

---

## 🔴 2026-09-16: learner の除外が **131 日・13 回**発行されても適用されない — かつ本戦略は現在**発火していない**

`/api/demo/learning` に **adjustment id 94 / 2026-09-15 13:18:14** (pull の **22.6 時間前**) が入った。内容は `sr_channel_reversal: WR 25.0%, EV -0.98 → 除外` で、**2026-05-07 以降 13 回目の同一再発行** (05-07 / 05-08 ×2 / 05-18 / 06-01 / 06-10 / 06-11 / 06-19 / 06-30 / 07-01 / 07-06 / 08-19 / **09-15** = **131 日間**)。

🔑 **にもかかわらず `current_params.entry_type_blacklist` は `[]`、`blacklisted: true` は 100 戦略中 0 件、本戦略は `enabled: true`。**
⇒ **「learner が stale だから反映されない」という従来の説明は本 run で消滅した。** learner は 22.6 時間前に走り、除外を発行し、それでも反映されていない ⇒ **欠陥は適用経路 (apply path) にある**。KB の当該項目を ⚪ から **🔴 に昇格**。

⚠️ **reason 文字列が 13 回すべてバイト一致** (`WR 25.0%, EV -0.98`) なのに `sample_size` は 230→180→184→185→**190** と動いている ⇒ **reason は現サンプルから再計算されていない**。この文言を本戦略の現況統計として引用してはいけない。

⚪ **現時点の実害はゼロ**: `/api/oanda/audit?limit=500` (09-09T12:16Z〜09-16T11:32Z = 7 日) で本戦略の発火は **0 件**。`promo_n` **4** / WR **50.0%** / EV **+1.73** は**その前の窓の残骸**であり、lifetime (N=34 / WR 26.5% / PnL −24.2 / Wilson BF 9.7) と**符号が逆** ⇒ N=4 では結論不可 ([[feedback_cohort_time_check]])。
⚠️ 兄弟 [[dt-sr-channel-reversal]] は `promo_n` **15** / EV **−2.95** で**依然 blacklist 候補に入らない** (不変)。直近 2 日は audit 窓で最多発火 (09-15 に 16 件 / 09-16 に 12 件) = **除外されているのは発火していない方だけ**という倒錯した状態。

詳細: [[2026-09-16]]
