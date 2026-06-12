# Edge Factor Audit 2026-06-12 — #3 fib_reversal

Edge 別 N 降順要因解析シリーズ第 3 弾。母集団は
[[edge-factor-audit-2026-06-12-ema-trend-scalp]] と同一 (clean 7,875)。

## Verdict: 🔴 KILL (恒久退役) — rule:R2

`SHADOW_RETIRED_STRATEGIES` 追加。#1 型 (救済セルなし) + **現役最大の Shadow 出血源**
(直近 30d N=251 / −321.7p、全 edge 中ワースト) のため停止の限界効用が最大。

## 対象 N

| population | N | WR | EV/t | PF | gross EV |
|---|---|---|---|---|---|
| clean 全体 | 638 | 29.5% | −0.91 | 0.59 | +0.59 |
| LIVE (〜05-08 で停止済) | 98 | 36.7% | −0.49 | 0.70 | +0.54 |
| SHADOW | 540 | 28.1% | −0.98 | 0.57 | +0.59 |
| 直近 30d (全 shadow) | 251 | 27.5% | −1.28 | 0.44 | +0.33 |

## 要因分解

### 🔴 1. friction 算数 (#2 と同型)
1m/5m scalp、median SL 3.6p / TP 5.1p / 保有 10 分。friction 1.49p = **TP の 29.2%**。
BE-WR 41.7% vs 実測 29.5% — 12pp 不足。gross +0.59 は friction の 4 割しかない。

### 🔴 2. 全 7 セル net 負け — LIVE も全ペア負け
| pair × dir | N | net EV | gross EV |
|---|---|---|---|
| EUR_USD BUY | 166 | −0.69 | +0.65 |
| USD_JPY SELL | 157 | −1.07 | +0.31 |
| USD_JPY BUY | 134 | −0.42 | +0.99 |
| EUR_USD SELL | 101 | −0.78 | +0.51 |
| GBP_USD BUY | 33 | −1.58 | +0.75 |
| GBP_USD SELL | 27 | −2.76 | **−0.42** |
| USD_CHF BUY | 12 | −1.27 | +1.29 |

LIVE 側も全ペア負け (EUR_USD BUY −0.35 / USD_JPY SELL −0.48 / 他)。
「LIVE since 04-08 = +0.08」は N=28 / Wilson 0.265 << BE-WR のノイズで、
かつ LIVE 発火は 05-08 に停止済み。SIZE lever 対象セルなし。

### 🔴 3. エントリーに予測力なし
敗者 450 件の MAFE favorable **中央値 0.2p** (+2p 到達 19%)。#1 と同じく
エントリー直後に逆行する。TP_HIT 率 17.9%、TIME_DECAY_EXIT 26.2% (EV −1.22) —
4 分の 1 が「行き先なく時間切れ」。

### 🔴 4. 統合先が存在しない (#2 との決定的差分)
fib 思想の DT 版 [[sr-fib-confluence]] (15m, N=428) は **gross −1.18 と gross から負け**
(パターン B、シリーズ #5 で監査予定)。TF を上げても fib レベル反発思想は救えない
見込みが既にデータにある。

### 🟠 5. 劣化トレンド + Recovery Path の失効
月次 net: −0.56 → −1.36 → −1.11 (gross も +0.75 → +0.35 → +0.50 で改善なし)。
カードの v8.2 復活パス (Post-cut N=20 WR55% 由来) は本監査 N=638 で完全に上書き —
当時の好数字は small-sample であった。

## 実装 (同コミット)
- `SHADOW_RETIRED_STRATEGIES` に `fib_reversal` 追加 (Shadow 全ペア恒久停止)
- LIVE 側は FORCE_DEMOTED 済みのため変更なし。カードの Recovery Path 文言を失効化

## シリーズ進捗

| # | edge | N | verdict |
|---|---|---|---|
| 1 | ema_trend_scalp | 1,117 | 🔴 KILL (ノイズ) |
| 2 | bb_rsi_reversion | 780 | 🟠 統合退役 → dt_bb_rsi_mr |
| 3 | fib_reversal | 638 | 🔴 KILL (friction 算数 + 統合先なし) |
| 次 | sr_channel_reversal | 584 | — |

以降: sr_fib_confluence 428 → session_time_bias 399。

## 横断観察 (シリーズ #1-#3 共通)
3 戦略とも **1m/5m × SL≈4p × friction≈1.5p** 構成。friction が TP の 25-30% を占める
scalp はシグナル品質と無関係に算数で死ぬ。**新 scalp 戦略の事前チェックとして
「friction ≤ TP の 10%」を設計時必須条件にすべき** (dt_bb_rsi_mr 10.8% は生存、
25%+ は全滅) — シリーズ完了時に lessons 化予定。
