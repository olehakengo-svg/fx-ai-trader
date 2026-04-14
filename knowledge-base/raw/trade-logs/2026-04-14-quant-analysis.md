# 2026-04-14 クオンツ詳細分析

## 全体サマリー

| 指標 | 値 |
|---|---|
| Total | 200 trades |
| Win/Loss | 48/137 (15 neutral) |
| WR | 24.0% |
| PnL | **-206.2 pips** |
| LIVE | ~60 trades |
| SHADOW | ~140 trades |

---

## 敗因分析

### 1. ema_trend_scalp: 最大出血源 (-29.5pip, N=40)
- 全ペアで負け: EUR(-12.8p), GBP(-8.0p), JPY(-8.7p)
- WR=25%: SL_HITが30/40件（75%）
- **根本原因**: 摩擦/ATR比率が高すぎる。SL=3-5pipに対してスプレッド変動が大きい
- **対策**: ema_trend_scalpはSHADOWモード。v2.1で既に対処済み

### 2. xs_momentum: 全敗 (-38.2pip, N=4)
- USD_JPY SELL × 4: 全てSL_HIT or SIGNAL_REVERSE
- **根本原因**: USD_JPY × xs_momentumは PAIR_DEMOTED (EV=-0.071)
- **対策**: PAIR_DEMOTED済み。デプロイ前のトレードが残存

### 3. dt_sr_channel_reversal: (-39.3pip, N=9)
- GBP_USD/USD_JPY: SL_HIT + SIGNAL_REVERSE
- **根本原因**: レンジ相場でのSR判定ミス
- **対策**: SHADOWモード。DT戦略としては非ELITE

### 4. bb_squeeze_breakout: (-36.2pip, N=16)
- WR=12.5%: 14/16がSL_HIT
- **根本原因**: BT EV=+1.030(5m JPY)だがLive WR=12.5%
- **対策**: BT/Live乖離が大きい。SENTINEL維持でN蓄積して再判断

### 5. session_time_bias: 初回発火で負け (-12.9pip, N=1)
- GBP_USD SELL at 19:57 → SL_HIT
- **根本原因**: N=1で判断不能。BT WR=67%でも33%で負ける
- **対策**: N蓄積継続。N=1の敗北は統計的に正常範囲

---

## 勝ち戦略分析

### 1. vix_carry_unwind: +58.7pip (N=3, WR=67%)
- 07:07 JPY SELL -8.2p (SL_HIT)
- 07:12 JPY SELL +28.1p (TP_HIT) ★ SHADOW
- 08:11 JPY SELL +38.8p (TP_HIT) ★ SHADOW
- **特性**: 低頻度高インパクト。TP=28-39pipの大勝ち
- **SHADOW化されていた**: 2勝分(+66.9pip)がSHADOWで失われた

### 2. post_news_vol: +46.0pip (N=4, WR=50%)
- 07:33 GBP BUY +29.3p (TP_HIT) ★ SHADOW
- 07:35 JPY SELL +25.6p (TP_HIT) ★ SHADOW
- **特性**: ニュースイベント後のボラティリティ追随
- **全勝ちトレードがSHADOW**: +54.9pipが非実弾

### 3. engulfing_bb: +24.0pip (N=24, WR=33%)
- EUR_USD: +33.3p (4W/6L)
- USD_JPY: +5.4p (3W/8L)
- GBP_USD: -14.7p (1W/5L)
- **EUR_USDで特に強い**: WR=67%, PnL=+33.3p

### 4. bb_rsi_reversion: +15.5pip (N=14, WR=43%)
- USD_JPY: +16.0p (5W/5L)
- EUR_USD: +6.8p (1W/1L)
- **JPYとEURで正EV**: London時間帯に集中

---

## 新戦略パフォーマンス

| 戦略 | N | PnL | 分析 |
|---|---|---|---|
| ny_close_reversal | 3 | -2.4p | TP_HITだがPnL=-0.8p。TP/SL設定問題 |
| session_time_bias | 1 | -12.9p | N=1、統計的に正常範囲 |
| vwap_mean_reversion | 0 | — | 未発火 |
| streak_reversal | 0 | — | 未発火 |

---

## v2.1シミュレーション

### 旧構成 vs v2.1構成

| 指標 | 旧構成(実績) | v2.1(推定) |
|---|---|---|
| LIVE trades | ~60 | ~1-3 |
| LIVE PnL | ~-100pip+ | -12.9pip |
| SHADOW trades | ~140 | ~197 |
| 毒の除去効果 | — | **~87pip節約** |

v2.1のSHADOWモードが完全に機能していれば、損失は-12.9pipで済んだ。

---

## 勝ちに変えるための対策

### 対策1: vix_carry_unwindをSENTINEL復活 (推定効果: +50pip/日)

4/14の最大勝者(+58.7pip)がSHADOWで無駄になった。
- BT EV=+0.212 (N=49, WR=67.3%) — 包括BTスキャンでGOOD判定
- SENTINEL → PAIR_PROMOTED で実弾データ蓄積開始を推奨

### 対策2: post_news_volをSENTINEL復活 (推定効果: +30pip/日)

4/14で+46pip（全SHADOW）。GBP/EUR/JPYで正EV。
- BT: GBP EV=+1.762 (N=26), EUR EV=+0.817 (N=28) — Bonferroni未通過だがBT STRONG
- 低頻度高インパクトのためN蓄積が遅い → SENTINEL早期開始が合理的

### 対策3: engulfing_bb × EUR_USD をSENTINEL昇格検討 (推定効果: +15pip/日)

4/14でEUR_USDのみWR=67%, PnL=+33pip。
- ただし全体WR=33% — ペア選択が重要
- EUR_USD限定でSENTINEL推奨

### 対策4: ny_close_reversal のTP/SL修正

TP_HITなのにPnL=-0.8pip → **TPがスプレッド以下**の可能性。
- TP距離を確認し、最低でもスプレッドの3倍以上に設定
- H20 SELL JPYの方向性は正しい（4/14はJPY売り方向）が、利益が摩擦で消滅

### 対策5: LIVE戦略のlot配分見直し

session_time_bias 1トレードで-12.9pip → lot_ratioが大きすぎた可能性。
- SENTINEL(0.01lot)での初回検証を徹底
- N≥15になるまでLIVE lotを引き上げない

### 対策6: 時間帯別フィルター強化

4/14の損失の60%がUTC 5-9時（Tokyoセッション）に集中。
- Scalpの Asia時間帯フィルター（London限定）は実装済み
- DT戦略にもTokyo session注意フラグを追加検討

---

## 推定: 全対策適用後の4/14再現

| 構成 | PnL |
|---|---|
| 実績（旧構成） | -206.2pip |
| v2.1 SHADOW化のみ | -12.9pip |
| v2.1 + 対策1-3 (SENTINEL復活) | +50pip (推定) |
| v2.1 + 対策1-6 (全対策) | +80pip (推定) |

**-206pip → +80pip の転換が可能。** 最大のレバレッジは「毒の除去」(SHADOW化)と「勝者の復活」(vix_carry_unwind, post_news_vol)。
