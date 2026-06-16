# Edge Factor Audit 2026-06-12 — #4 sr_channel_reversal (+ SR family 横断)

Edge 別 N 降順要因解析シリーズ第 4 弾。母集団は
[[edge-factor-audit-2026-06-12-ema-trend-scalp]] と同一 (clean 7,875、データ vintage 2026-06-12)。

## Verdict: 🔴 KILL (恒久退役) — rule:R2

`SHADOW_RETIRED_STRATEGIES` 追加。#1/#3 と同型 (friction 算数 + 救済セルなし + 統合先なし)。

## 対象 N

| population | N | WR | net EV | PF | gross EV |
|---|---|---|---|---|---|
| clean 全体 | 584 | 25.0% | −1.13 | 0.57 | +0.58 |
| LIVE (〜04-20 停止済) | 34 | 26.5% | −0.71 | 0.64 | +0.61 |
| SHADOW | 550 | 24.9% | −1.16 | 0.57 | +0.57 |
| 直近 30d | 159 | 33.3% | −0.85 | 0.66 | — |

## 要因分解

### 🔴 1. friction 算数 (#1/#3 と同型)
median SL 4.0p / TP 7.2p / 保有 11 分。friction 1.71p = **TP の 23.7%**。
BE-WR 35.7% vs 実測 25.0% で 11pp 不足。SL_HIT 率 **56.2%** はシリーズ最悪。

### 🔴 2. 全 8 セル net 負け
| pair × dir | N | net EV | gross EV |
|---|---|---|---|
| USD_JPY SELL | 163 | −1.34 | +0.06 |
| USD_JPY BUY | 119 | −1.44 | −0.01 |
| GBP_USD SELL | 95 | −0.62 | +1.50 |
| GBP_USD BUY | 92 | −0.98 | +1.25 |
| EUR_USD BUY | 40 | −1.09 | +0.29 |
| EUR_USD SELL | 35 | −1.14 | +0.20 |
| USD_CHF SELL | 28 | −1.52 | +0.60 |
| USD_CHF BUY | 12 | +0.35 | +2.87 |

唯一の net 正は USD_CHF BUY (+0.35) だが N=12 / Wilson_lo 0.138 のノイズ。SIZE lever 対象なし。

### 🔴 3. エントリーに予測力なし
敗者 438 件の MAFE favorable **中央値 0.2p** (#1/#3 と一致)。

### 🔴 4. 統合先が存在しない (#2 との差分)
SR 思想の生存者は **異なる thesis** (anti-hunt = stop-hunt fade):
[[sr-anti-hunt-bounce]] が SR-weight Phase 2 BH-FDR 唯一の survivor (30d net +0.40)。
channel-reversal の DT 版 [[dt-sr-channel-reversal]] は net **−1.07** で survivor ではない
(下記 §副次発見)。よって channel-reversal 思想を継ぐ +EV 戦略が現存しない → KILL。

### 🟠 5. 封じ込め漏れ (#1-#3 と同パターン)
per-cell registry は EUR_USD/USD_JPY のみ列挙 → GBP_USD/USD_CHF が漏れ、直近 30d
N=159 (GBP_USD 119 / USD_CHF 40) が Shadow 蓄積継続。strategy-level retire で封鎖。

## SR family 横断 (clean, データ vintage 2026-06-12)

| entry_type | N | net | gross | fric (%TP) | 30d net | 分類 |
|---|---|---|---|---|---|---|
| sr_channel_reversal (#4) | 584 | −1.13 | +0.58 | 1.71 (24%) | −0.85 | A→KILL |
| sr_fib_confluence (#5予定) | 428 | −3.34 | **−1.02** | 2.32 (12%) | −1.33 | B (gross負) |
| sr_break_retest | 298 | −2.89 | **−0.31** | 2.58 (14%) | −2.81 | B (gross負) |
| dt_sr_channel_reversal | 202 | −1.07 | **+2.25** | 3.32 (22%) | −1.24 | A (friction-killed, 下記) |
| dual_sr_bounce | 153 | −2.92 | +0.21 | 3.13 (10%) | −0.52 | A |
| sr_anti_hunt_bounce | 82 | −1.24 | +0.21 | 1.44 | **+0.40** | C (survivor, redesign) |
| sr_weighted_break | 20 | −1.76 | −0.92 | 0.84 | −1.76 | B (redesign 失敗) |
| sr_weighted_bounce | 11 | −5.16 | −2.77 | 2.39 | −5.16 | B (redesign 失敗) |

**SR family の総括**: 6/8 が gross 負 or friction-killed。唯一の生存は anti-hunt 思想
(sr_anti_hunt_bounce)。SR-weight redesign の明示的 weighted 系 (bounce/break) は N 不足
ながら gross 負で、touch_count 重み付け仮説の再検証が必要 ([[feedback-sr-weight-is-essence]])。

## 🟠 副次発見 (follow-up 候補、本 kill とは別件)
**dt_sr_channel_reversal: gross +2.25 と SR family 最高の gross edge** を持つが
friction 3.32p (GBP 主体で spread 広) に食われ net −1.07。これは「思想は正、pair/friction
選択が誤」型 = sr_channel_reversal 思想を **DT geometry + tight-spread pair に限定**すれば
edge が表に出る可能性。ただし現状は net 負け = 昇格不可。fib (#3, DT版も gross 負) と異なり
**channel-reversal 思想自体は DT で gross 生存**している点が重要。
→ シリーズ完了後に「dt_sr_channel_reversal pair-restriction 仮説」を別途 pre-reg 検証推奨。

## 実装 (同コミット)
- `SHADOW_RETIRED_STRATEGIES` に `sr_channel_reversal` 追加 (Shadow 全ペア恒久停止)
- LIVE 側は FORCE_DEMOTED 済みのため変更なし

## シリーズ進捗

| # | edge | N | verdict |
|---|---|---|---|
| 1 | ema_trend_scalp | 1,117 | 🔴 KILL |
| 2 | bb_rsi_reversion | 780 | 🟠 統合退役 → dt_bb_rsi_mr |
| 3 | fib_reversal | 638 | 🔴 KILL |
| 4 | sr_channel_reversal | 584 | 🔴 KILL (統合先なし、dt版は follow-up) |
| 次 | sr_fib_confluence | 428 | — (pattern B, fib/SR 思想の最終判定) |

以降: session_time_bias 399。横断則「friction ≤ TP の 10%」は継続検証中
(dt_sr_channel_reversal 22% は friction-killed で則を支持)。
