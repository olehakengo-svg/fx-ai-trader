# Post-Tokyo Report: 2026-04-14

## Analyst Report
# Post-Tokyo Session Report — 2026-04-14 JST 15:00

---

## 1. 東京セッション結果

| 指標 | 値 |
|---|---|
| 対象期間 | UTC 00:00–06:00 |
| トレード数 (N) | 16 |
| 勝率 (WR) | 37.5%（6勝/10敗） |
| PnL | **−12.8 pips** |
| 主要ペア | USD_JPY（全16件） |
| 平均スプレッド | 0.8 pips（全件均一） |

**注意**: 本日累計N=20・PnL=−23.7pipsとの差分（N+4, PnL−10.9pips）は東京セッション外（UTC −06:00以前）の4件に帰属。

---

## 2. What Worked ✅

| 戦略 | Pair | PnL | 成功要因 |
|---|---|---|---|
| **bb_squeeze_breakout** | USD_JPY | +8.6 | スプレッド0.8pipの低摩擦環境下でボラタイル局面のブレイクアウトを的確に捉えた。 |
| **stoch_trend_pullback** | USD_JPY | +8.0 | TP_HIT達成（WR=100%、N=1）。ただし単発のためv8.9のFORCE_DEMOTED処分と矛盾する点は後述。 |
| **ema_trend_scalp** | USD_JPY | +6.3 | 方向性のある局面でトレンド順張りが機能し、TP_HIT。 |

---

## 3. What Didn't Work ❌

| 戦略 | Pair | PnL | 失敗要因 |
|---|---|---|---|
| **vol_surge_detector** | USD_JPY | −16.2（N=5, WR=20%） | 最大ドローダウン源。ボラリティスパイク後の方向性を誤読し4連続SL_HIT。本セッションのネガティブ主因。 |
| **dt_sr_channel_reversal** | USD_JPY | −6.9（N=2） | 逆張りがRANGINGレジームで2連続SL_HIT（−7.7pips）。BUYサイド連続発火はトレンド方向の見誤り。 |
| **sr_channel_reversal** | USD_JPY | −5.5（N=2） | TIME_DECAY_EXIT含む2連敗。レジームRANGINGでのSR逆張りだが、インプライドレンジを貫通。 |
| **bb_rsi_reversion** | USD_JPY | −3.9（N=3） | v8.9でPAIR_DEMOTED確定（EV=−0.28）済みにもかかわらず3件発火。KB判断との整合性を要確認。 |
| **three_bar_reversal** | USD_JPY | −3.2（N=1） | SL_HIT。N=1のためデータ不足だが、東京時間の薄い流動性での逆張りパターン。 |

---

## 4. 戦略調整判断

**パラメータ変更の要否: NO**（コード変更禁止原則に従い、判断のみ提示）

ただし以下の**運用判断**を記録する：

| 戦略 | 現在ステータス | 判断 |
|---|---|---|
| **stoch_trend_pullback** | v8.9でFORCE_DEMOTED (Tier 3, EV=−0.97) | 本日+8.0pip WIN（N=1）は平均回帰範囲内。KB判断を維持。累積N=19+1=20、EV依然負。**降格継続。** |
| **vol_surge_detector** | Tier 2 Sentinel（N=15→20, WR=46.7%→?) | 本日5件WR=20%。累積WR低下継続中（N=11時63.6% → 劣化傾向）。**N=30到達後に判断。** |
| **bb_rsi_reversion** | v8.9でPAIR_DEMOTED | 本日3件発火は意図通りか確認要。KB判断（Tier 3）維持。 |
| **bb_squeeze_breakout / ema_trend_scalp** | N不足（単発） | 好成績だが統計不足。監視継続。 |

---

## 5. ロンドンセッション準備（UTC 07:00–11:00）

### レジーム・ATR変化予測

| 観察点 | 現状 | ロンドン移行時の予測 |
|---|---|---|
| 全ペアレジーム | RANGING（5/5ペア） | ロンドンOpen（UTC 07:00）で方向性ブレイクの可能性。EUR/GBP系でボラ上昇が先行する傾向。 |
| USD_JPY ATR%ile | 38%（中程度） | ロンドン参入でドル円ボラ増加の可能性。ただしSMA slope=+0.00023と方向性は不明瞭。 |
| EUR_USD ATR%ile | 52% | 全ペア中最も「動きやすい」状態。ロンドンではEUR系に優位性。 |
| GBP_USD ATR%ile | 55% | 同上、GBP系も動きやすい状態。 |

### 推奨戦略配分

**⚠️ 方針: 防御的運用 / USD_JPY集中リスク回避**

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| **High** | session_time_bias | EUR_USD, GBP_USD | BT WR=69-77%、ロンドン時間bias有効、ATR%ile 52-55%で発火条件良好 |
| **High** | london_fix_reversal | GBP_USD | ロンドンFix（UTC 11:00前後）に向け本戦略の主舞台。ATR=55%で動きあり |
| **Medium** | orb_trap | EUR_USD, GBP_USD | N=2と不足だがBT WR=79%。ロンドンOpen直後のORB環境 |
| **Low** | vol_momentum_scalp | — | WR=80%（N=10）だが昇格基準N=30未達。慎重に |
| **❌ 停止推奨** | vol_surge_detector | USD_JPY | 本日WR=20%、東京セッションでの失敗主因 |
| **❌ 停止推奨** | bb_rsi_reversion | USD_JPY | PAIR_DEMOTED確定 |

### NO ACTION推奨ケース

**USD_JPY全般への過集中を回避すること。** 本日16件全件USD_JPYという集中リスクは構造的問題。ロンドンセッションではEUR/GBP系へのシフトを意識する。RANGINGレジームでの逆張り戦略（sr_channel_reversal, dt_sr_channel_reversal）は**「何もしない」が最適**。

---

## 6. クオンツ見解

### 最重要シグナル: **vol_surge_detector の劣化加速と USD_JPY 集中リスクの複合問題**

本セッションの最大損失源はvol_surge_detector（−16.2pips、WR=20%）だが、より構造的な問題は**全16件がUSD_JPYに集中**したことである。KB記録上この戦略はN=11時点でWR=63.6%→N=15時点46.7%→本日N=5中WR=20%と**単調劣化**しており、東京時間のRANGINGレジームとの相性悪化が示唆される。

OANDA転送率48%（24/50 SENT）かつBridge Statusで`shadow_tracking`が12件ブロックの主因であることは、本番資金リスクとしては抑制されているが、**デモ段階でこの劣化トレンドを放置すると昇格判断時に汚染データとなる**。N=30到達前に`vol_surge_detector`の東京セッション限定でのWR分析を別途実施し、セッション別EV分解を行うことを推奨する（コード変更なし、データ観察のみ）。

XAU（N=11、PnL=−1,496pips）はピップスケール換算で深刻だが、OFFステータスのため本番への影響は限定的。再起動判
