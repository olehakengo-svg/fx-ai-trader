# Post-London Report: 2026-04-23

## Analyst Report
# ロンドンセッション総括レポート
**2026-04-23 | UTC 07:00–16:00 | JST 01:00**

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| トレード数 | 7件 |
| 勝率 | 42.9%（3勝4敗） |
| PnL | **−26.2 pips** |
| 平均EV/トレード | −3.73 |

セッション全体として明確なネガティブ結果。損失は2件のvwap_mean_reversionが主因（合計−30.2 pips）。

---

## 2. What Worked ✅

| 戦略 | ペア | PnL | 成功要因 |
|---|---|---|---|
| **gbp_deep_pullback** | GBP_USD | **+8.1 pips** | OANDA経由でTP到達、GBP_USDのRANGING相場での押し目戻りが精度良く機能 |
| **trendline_sweep** | GBP_USD | **+1.4 pips** | エントリー方向一致でSL_HIT前に小幅利確 |
| **vwap_mean_reversion** | GBP_USD | **+1.2 pips** | OANDA_SL_TP経由でTP到達、spread1.3pipsと低コスト環境で機能 |

**共通パターン**: 3勝すべてがGBP_USD。spread 1.3 pipsという一貫した低コスト環境が寄与。

---

## 3. What Didn't Work ❌

| 戦略 | ペア | PnL | 失敗要因 |
|---|---|---|---|
| **vwap_mean_reversion** | GBP_JPY | **−20.1 pips** | spread 2.8 pipsかつRANGING低ATR環境（ATR%ile 33%）でSL_HIT、リスクリワード比が摩擦に負けた |
| **vwap_mean_reversion** | EUR_JPY | **−10.1 pips** | spread 2.0 pipsでSL_HIT、ATR%ile 36%のRANGING環境でMeanReversionの射程距離が不足 |
| **trendline_sweep** | GBP_USD | **−2.4 / −4.3 pips** | SIGNAL_REVERSE×2件、ロンドン後半の方向感喪失局面でのシグナル品質低下 |

**構造的問題**: vwap_mean_reversionのJPY通貨ペア（EUR_JPY, GBP_JPY）はspreaddが高く、かつATR%ile 33-36%の低ボラ環境では摩擦調整EVが著しく悪化する。

---

## 4. 東京との比較

本日の東京セッション単体データは提供されていないため、**本日累計 N=8 / WR=37.5% / PnL=−33.0**からロンドン分を逆算：

| セッション | N | WR% | PnL |
|---|---|---|---|
| 東京（推定） | 1 | 0.0% | **−6.8 pips** |
| ロンドン | 7 | 42.9% | **−26.2 pips** |
| 累計 | 8 | 37.5% | **−33.0 pips** |

- ロンドンセッションで**トレード頻度が急増**（東京1件→ロンドン7件）
- レジームは終日RANGINGで変化なし。全ペアATR%ile 33-48%と中低位帯
- WRはロンドンで若干改善するも、vwap_mean_reversionの大損が全体をドラッグ

---

## 5. NYセッション準備

### レジーム・ATR変化予測

| 観点 | 予測 |
|---|---|
| レジーム | 全ペアRANGING継続の可能性高。全SMA20 Slopeが+0.001〜+0.004と弱トレンド |
| ATR | NYオープン前後に一時的ボラ拡大の可能性あるが、現状ATR%ile低位のため構造的変化は限定的 |
| JPYペア | USD_JPY ATR%ile 36%、傾きほぼゼロ（+0.00061）— 方向感欠如 |

### 推奨戦略配分

| 戦略 | ペア | 判断 | 根拠 |
|---|---|---|---|
| **gbp_deep_pullback** | GBP_USD | ✅ **継続** | ELITE_LIVE、本日+8.1でRANGING環境でも機能実証済み、spread低コスト |
| **trendline_sweep** | GBP_USD | ⚠️ **条件付き** | SIGNAL_REVERSEが2件→方向感があるシグナルのみ、NYオープン直後の高ボラ局面に限定 |
| **vwap_mean_reversion** | EUR_JPY / GBP_JPY | 🚫 **回避推奨** | 本日spread+低ATRのダブルパンチ、摩擦調整EVが明確にマイナス |
| **vwap_mean_reversion** | GBP_USD | ⚠️ **小ロット監視** | spread 1.3 pipsなら辛うじて機能、N蓄積フェーズとして許容 |
| **session_time_bias** | GBP_USD / USD_JPY | ✅ **ELITE_LIVEとして優先** | NYセッション時間バイアス戦略として適合度高い |

> **補足**: rnb_usdjpy は本日160件のdirection_filterブロックが発生。USD_JPYが方向感のない環境（slope +0.00061）であることと整合しており、**NYでも同様のブロック継続を想定**。

---

## 6. 本日暫定結果（東京+ロンドン累計）

| 指標 | 値 |
|---|---|
| 総トレード数 | **8件** |
| 勝率 | **37.5%** |
| 累計PnL | **−33.0 pips** |
| OANDA転送率 | 4%（50件中2件SENT） |
| NAV | 437,523.5675 |

---

## 7. クオンツ見解

### 最重要シグナル

**vwap_mean_reversionのJPYペア集中損失は即時処置シグナル**

本日EUR_JPY(−10.1)とGBP_JPY(−20.1)の合計**−30.2 pips**がセッション損失の115%を占める（GBP_USDの利益で一部相殺）。両者のspreaddはそれぞれ2.0・2.8 pipsで、システムのspread_guard閾値（Scalp=30%）との比較でもギリギリの水準。かつ本日のATR%ile 33-36%（低ボラRANGING）は、平均回帰戦略が「射程が短く摩擦だけ取られる」最悪の組み合わせ。

> **判断**: vwap_mean_reversionのEUR_JPY・GBP_JPYは、**ATR%ile≥50%の環境条件が満たされるまで実質的にEVがマイナス**とみなすべき。N蓄積データでもこのパターンは繰り返し現れており、KBの「no BT data」状態のまま本番環境で損失を重ねているのは構造的問題。

**推奨アクション（判断のみ）**: vwap_mean_reversionのJPYペアについて、RANGING+ATR低位レジーム時のエントリー停止基準を設けることを**意思決定者として判断すべき**。コード変更ではなく「何を止めるか」の運用判断として。

---
*レポート生成: 2026-04-23 17:11 UTC | データ: Fidelity Cutoff 2026-04-08以降*
