# Edge Factor Audit 2026-06-12 — #5 sr_fib_confluence

Edge 別 N 降順要因解析シリーズ第 5 弾。母集団は本番 `/api/demo/trades`
(re-fetch 2026-06-18, clean = XAU + dedup_violation 除外後)。

## Verdict: 🔴 KILL (恒久退役) — rule:R2

`SHADOW_RETIRED_STRATEGIES` 追加。**シリーズ初の aggregate gross 負 (pattern B)** だが、
#1/#3/#4 の「均一 friction 死」とは敗因が質的に異なる (下記分解)。

## 対象 N

| population | N | WR | net EV | PF | gross EV |
|---|---|---|---|---|---|
| clean 全体 | 453 | 28.7% | −2.95 | 0.55 | −0.86 |
| LIVE (停止済) | 43 | 41.9% | −1.55 | 0.71 | +0.27 |
| SHADOW | 410 | 27.3% | −3.30 | 0.54 | −0.98 |
| 直近 30d (majors only) | 157 | 38.9% | −1.07 | 0.74 | −0.50 |

15m / median SL 9.4p / TP 19.6p / 保有 54 分。friction 2.28p = TP の **11.6%**
(scalp 系の 25-30% と違い survival line 近傍)。

## 要因分解 — 「JPY 摩擦カタストロフ + 壊れた SELL + 限界的 BUY」

### 🔴 1. 出血の 96% は JPY 4 セル (既に停止済み)
| cell | N | net | gross | friction |
|---|---|---|---|---|
| GBP_JPY SELL | 45 | −10.12 | −4.97 | **5.15** |
| USD_JPY SELL | 39 | −9.57 | −7.52 | 2.05 |
| EUR_JPY SELL | 23 | −9.67 | −5.21 | 4.47 |
| EUR_JPY BUY | 27 | −9.07 | −3.91 | 5.17 |

合計 −1296p = 全 shadow 損失 −1354p の **96%**。JPY cross は gross 負 **かつ** 4-5p の
広 friction。per-cell registry (EUR_JPY/GBP_JPY/USD_JPY) が 2026-05-06〜08 に停止済み、
last fire も同日で**漏れていない** (clean stop)。

### 🟠 2. major pair は BUY/SELL で非対称
| cell | N | net | gross |
|---|---|---|---|
| EUR_USD BUY | 63 | **+0.54** | +1.96 |
| GBP_USD BUY | 90 | −0.10 | +1.78 |
| EUR_USD SELL | 64 | −1.07 | −0.55 |
| GBP_USD SELL | 61 | −3.46 | −2.23 |

**BUY 側 majors は gross +1.8〜2.0 で edge の痕跡**、friction で net ~breakeven に圧縮。
**SELL 側は gross からして負** = シグナルが逆。

### 🔴 3. しかし promotable cell はゼロ
最良の EUR_USD BUY (net +0.54, N=63) でも Wilson_lo 0.285 < BE-WR 0.324 で有意でない。
全体 net −2.95 / 直近 30d (majors only) も gross −0.50 で依然負け。

### 🔴 4. 反転 (inverse) も不成立
mean gross −0.86 → inverse gross +0.86 − friction 2.28 = **inverse net −1.42**。
SELL の gross 負を反転しても friction (特に JPY 4-5p) に沈む。

### 🔴 5. 敗者に予測力なし
losers N=323 の MAFE favorable 中央値 **0.0p**。SIGNAL_REVERSE 17% (N=77, net −3.14) =
MR が trend に轢かれる典型。

## 退役判断
net 負け + promotable cell なし (Wilson_lo < BE-WR) + FORCE_DEMOTED 済み + 直近 30d も
gross 負 → retire。shadow-first 原則 (breakeven は蓄積継続) を覆す根拠 = (a) 既に N=453
蓄積して BUY-major cell が依然非有意、(b) majors も直近 gross 負、(c) JPY/SELL が aggregate
を汚染。majors はまだ発火中 (30d shadow N=157) で retire により停止。

## 🟠 follow-up 候補 (本 kill とは別件、#4 dt_sr_channel と同型)
**「sr_fib_confluence BUY-major-only」redesign 仮説**: EUR_USD/GBP_USD の BUY のみ
gross +1.85、15m で friction 比 8.7% (survival line 内)。fib-confluence 思想は
**BUY 方向 × major × 15m に限定すれば** edge が表に出る可能性。ただし現状 net ~breakeven
かつ非有意 = 昇格不可。シリーズ完了後に dt_sr_channel_reversal と合わせて pre-reg 検証推奨。

## fib 思想の最終判定 (#3 + #5 統合)
- fib_reversal (#3, scalp 1m/5m): friction 死、gross +0.59
- sr_fib_confluence (#5, 15m): JPY 壊滅 + SELL 逆 + BUY-major 限界的
→ **fib レベル反発は「BUY × major × 中期 TF」の狭い窓でのみ gross 生存**。JPY cross と
SELL 方向は構造的に負け。両者とも現行実装は retire、BUY-major-only redesign のみ将来余地。

## 実装 (同コミット)
- `SHADOW_RETIRED_STRATEGIES` に `sr_fib_confluence` 追加 (per-cell は JPY 3 つのみ→majors 封鎖)
- LIVE 側は FORCE_DEMOTED 済み

## シリーズ進捗

| # | edge | N | verdict |
|---|---|---|---|
| 1 | ema_trend_scalp | 1,117 | 🔴 KILL |
| 2 | bb_rsi_reversion | 780 | 🟠 統合退役 → dt_bb_rsi_mr |
| 3 | fib_reversal | 638 | 🔴 KILL |
| 4 | sr_channel_reversal | 584 | 🔴 KILL (dt版 follow-up) |
| 5 | sr_fib_confluence | 453 | 🔴 KILL (BUY-major follow-up) |
| 次 | session_time_bias | ~399 | — (ELITE 由来、LIVE 履歴あり) |
