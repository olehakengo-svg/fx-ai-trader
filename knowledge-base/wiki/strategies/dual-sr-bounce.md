# Dual SR Bounce

## Overview
- **Entry Type**: `dual_sr_bounce`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: 🔴 **ACTIVE (inline) — 2026-09-17 訂正**。旧記載「REMOVED (v9.1 dead-code cleanup)」は**誤り**
- **Active Pairs**: EUR_JPY / USD_JPY / GBP_USD ほか (直近 7 日で 6 ペアに発火)
- **実装形態**: 独立した戦略ファイルは**存在しない** (`find -iname "*dual_sr*"` → 0 件) が、**`app.py` インラインのシグナル経路として稼働中** — `app.py:2422` / `app.py:2433` が `_dt_entry_type = "dual_sr_bounce"` を設定、分岐は `app.py:3051` / `3616` / `6824` / `14485`。`tools/sr_weight_phase2_bin_bhfdr.py:70` が実装形態を `production_daytrade_inline` と明記
- **履歴**: Previously FORCE_DEMOTED (v6.8+)。v9.1 の死コード一斉削除 (dual_sr_bounce / h1_fib_reversal / pivot_breakout) で**消えたのは「ファイル」であって「シグナル経路」ではなかった** — この取り違えが 2026-09-17 まで KB に残った

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| USD_JPY | 118 | 70.3% | +0.280 | 1.50 | +33.0p |

## Live Performance (post-cutoff)
| Strategy | Pair | N | W | L | WR | PnL |
|---|---|---|---|---|---|---|
| dual_sr_bounce | USD_JPY | 1 | 1 | 0 | 100% | +21.4p |
| dual_sr_bounce | EUR_JPY | 2 | 0 | 2 | 0% | -32.7p |

## Signal Logic
Dual support/resistance bounce strategy. Enters when price bounces off a confluence of two independent SR levels (e.g., horizontal SR + Fibonacci level, or pivot + previous day high/low). Requires both levels to align within a tight zone for high-confidence reversal.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: none

## 2026-09-17 実測 (wiki-daily-update)

| ソース | 実測値 |
|---|---|
| `/api/oanda/audit?limit=500` (09-10T13:51Z〜09-17T21:00Z) | **79 行 = 15.8%、全 entry_type 中 1 位** |
| 同、09-17 当日 | **28 行、当日も 1 位** |
| `/api/demo/status` `strategy_status` | `enabled: **true**` / `category: **daytrade_inline**` / `promo_n: **0**` / `promo_ev: **0**` |
| `/api/demo/stats` `by_type` | **エントリ自体が存在しない** |
| `raw/trade-logs/2026-09-17-monitor.md` (08:58Z) | `ORDER_BAR_DEDUP` の集中先が `dual_sr_bounce EUR_JPY SELL` |

🔑 **79 発火して decided trade 0 本** — 全量 shadow に落ちており、promotion ledger にも 1 件も積まれていない。⇒ 「最多発火なのに評価母数ゼロ」という状態。

⚠️ この乖離は [[project_w4_eda_complete_2026_05_05]] の「思想は正・設計が誤」型ではなく、**KB の tier 記述と production 実態の乖離**型。`ob_retest` の「30+ 日 dead」INFO 矛盾 (7 run 連続) と同 family ⇒ 単発修正では閉じず、**tier 記述の出所を Render API に一本化する**課題として扱う。

⚠️ **上の BT / Live Performance / Current Configuration の 3 節は v9.1 以前の旧記述**で、この inline 稼働分は反映されていない (「FORCE_DEMOTED」表記も同様に未検証)。再計測するまで現況として引用しないこと。

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
- [[2026-09-17]] — inline 稼働の実測と Status 訂正
