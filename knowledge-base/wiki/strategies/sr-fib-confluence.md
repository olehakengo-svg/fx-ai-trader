# SR Fib Confluence

## Overview
- **Entry Type**: `sr_fib_confluence`
- **Category**: MR (Mean Reversion)
- **Timeframe**: DT 15m
- **Status**: 🔴 RETIRED (2026-06-12, rule:R2 — `SHADOW_RETIRED_STRATEGIES` + `_PAIR_PROMOTED`×GBP_USD 削除)。旧 PAIR_PROMOTED×GBP_USD (shadow N=39 EV+1.35) は N=132 で −1.66 に反転、LIVE breakeven (N=19 −0.07) で完全 demote
- **Active Pairs**: GBP_USD (PROMOTED)

## Previously
- ~2026-05-06: FORCE_DEMOTED (v6.8 PAIR_PROMOTED 全削除: 本番 N=40 WR=28.9% -92.8pip, BT 乖離確定)

## BT Performance (365d, 15m)
| Pair | N | WR | EV | PF | PnL |
|---|---|---|---|---|---|
| USD_JPY | 220 | 67.7% | +0.252 | 1.44 | +55.4p |
| EUR_USD | 262 | 64.9% | +0.103 | 1.16 | +27.0p |

## Live Performance (post-cutoff)
N=40 WR=28.9% PnL=-92.8pip (BT divergence confirmed, PAIR_PROMOTED removed in v6.8)

## Signal Logic
Support/resistance + Fibonacci level confluence strategy. Enters reversal trades at zones where horizontal SR levels coincide with Fibonacci retracement levels (38.2%, 50%, 61.8%). The confluence of two independent methods provides higher-confidence reversal zones.

## Current Configuration
- Lot Boost: default (1.0x) — FORCE_DEMOTED
- PAIR_DEMOTED: none explicit (globally demoted)
- PAIR_PROMOTED: none (all removed in v6.8)


## 2026-06-12 Edge Factor Audit #5 — 🔴 KILL 確定 (恒久退役)

clean N=453、シリーズ初の aggregate gross 負。詳細: [[edge-factor-audit-2026-06-12-sr-fib-confluence]]

- 出血の **96%** は JPY 4 セル (GBP_JPY/USD_JPY/EUR_JPY、gross −4〜−7.5p + friction 4-5p) で**既に停止済** (per-cell registry 2026-05-08、漏れなし)
- major pair は BUY/SELL 非対称: BUY (EUR_USD +0.54 / GBP_USD gross +1.78) vs SELL (gross 負=逆シグナル)
- promotable cell ゼロ (最良 EUR_USD BUY Wilson 0.285 < BE-WR 0.324)、反転も net −1.42
- 敗者 MAFE favorable 中央値 0.0p、SIGNAL_REVERSE 17%
- 🟠 follow-up: 「BUY × major × 15m」限定なら gross +1.85 (friction 比 8.7%) — redesign 仮説 (本 kill とは別件)
- strategy-level retire で majors (まだ 30d N=157 発火中) を封鎖

## Related
- [[index]] — Tier classification
- [[roadmap-v2.1]] — Portfolio strategy
