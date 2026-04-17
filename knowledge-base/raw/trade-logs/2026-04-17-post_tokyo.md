# Post-Tokyo Report: 2026-04-17

## Analyst Report
# Post-Tokyo Report — 2026-04-17 JST 15:00 (UTC 06:00)

---

## 1. 東京セッション結果

**東京セッション: トレードなし**

| 項目 | 値 |
|---|---|
| セッション期間 | UTC 00:00–06:00 |
| トレード数 | 0 |
| PnL | ±0 |
| WR | N/A |

全稼働モード（daytrade系・scalp系・rnb_usdjpy）でシグナル発火ゼロ。ブロック機構が実質的にエントリーを吸収した形。

---

## 2. What Worked

**該当なし**（トレードゼロのため評価不能）

---

## 3. What Didn't Work

**該当なし**（損失も発生していないが、以下のブロック分析が「機会損失」の文脈で重要）

### ブロック主因分析（Block Counts TOP 11）

| 順位 | Reason | Count | 分類 | 判定 |
|---|---|---|---|---|
| 1 | scalp_eur: session_pair | 16 | 設計上の制御 | 正常 |
| 2 | scalp: spread_guard | 13 | スプレッド過大 | 要注目 |
| 3 | rnb_usdjpy: direction_filter | 11 | トレンドフィルタ | 正常 |
| 4 | daytrade_eur: score_gate | 8 | スコア不足 | 正常 |
| 5 | daytrade: same_price_5pip | 6 | 重複防止 | 正常 |
| 6 | daytrade_gbpusd: score_gate | 6 | スコア不足 | 正常 |
| 7 | scalp_5m_eur: session_pair | 6 | 設計上の制御 | 正常 |
| 8 | daytrade_gbpusd: same_price_0pip | 5 | 重複防止 | 正常 |
| 9 | daytrade_eurgbp: regime_trend_bull_dt_tf | 3 | レジーム非適合 | 正常 |
| 10 | scalp_5m: same_price_3pip | 3 | 重複防止 | 正常 |
| 11 | scalp_5m: sl_cluster | 1 | SLクラスタ回避 | 正常 |

**主因**: `scalp: spread_guard`（13件）が最大の「能動的ブロック」。東京セッションのスプレッド拡大が閾値（Scalp=30%）を超えており、東京時間のsalp系エントリー機会を実質封鎖している。`session_pair`ブロック（16+6=22件）は設計通りの時間帯制限。

---

## 4. 戦略調整判断

**NO — パラメータ変更不要**

根拠：
- トレードゼロはシステム異常ではなく、スプレッドガードと時間帯フィルタが機能した結果
- spread_guard閾値（Scalp30%）は東京セッションの流動性低下に対し適切に機能している
- N=0では統計的判断の根拠なし。Fidelity Cutoff（2026-04-08）以降の累積データで判断すべき

---

## 5. ロンドンセッション準備（UTC 07:00–12:00）

### ATR/レジーム変化予測

| ペア | 現在レジーム | ATR%ile | ロンドン開始予測 | 根拠 |
|---|---|---|---|---|
| EUR_USD | TRENDING_UP | 57% | ATR拡大・トレンド継続 | SMA20 Slope +0.00585が最強。ロンドン流入でモメンタム加速しやすい |
| EUR_JPY | TRENDING_UP | 38% | ATR中程度・上方バイアス | Slope +0.00593だがATR%ileは38%と低め。急激な拡大は限定的 |
| GBP_USD | RANGING | 53% | レンジブレイク警戒 | ATR53%でエネルギー蓄積。ロンドンで方向性確定する可能性 |
| GBP_JPY | RANGING | 38% | レンジ継続 | Slope+ATRともに低位。方向感薄い |
| USD_JPY | RANGING | 38% | レンジ継続 | SMA20 Slope≈ゼロ（+0.00009）。最も方向性なし |

### 推奨戦略配分

**優先度A（積極稼働）**

| 戦略 | ペア | 根拠 |
|---|---|---|
| `trendline-sweep` (ELITE) | EUR_USD | TRENDING_UP + ATR57%。BT EV=+0.927/WR=80.8%。ロンドン開始のブレイクアウトに適合 |
| `session-time-bias` (ELITE) | EUR_USD, GBP_USD | ロンドンセッションはこの戦略のコアタイム。USD_JPY EV=+0.580も有効 |
| `gbp-deep-pullback` (ELITE) | GBP_USD | レンジ中のディープ押し目は本戦略の得意形。ATR53%でエントリー価格帯が確保しやすい |

**優先度B（レジーム確認後）**

| 戦略 | ペア | 根拠 |
|---|---|---|
| `post-news-vol` (SENTINEL) | EUR_USD, GBP_USD | ロンドン経済指標（GBP/EUR系）発表後に適合。GBP_USD BT EV=+1.762は要注目だがSENTINEL中 |
| `doji-breakout` (SENTINEL) | GBP_USD | レンジ→ブレイク転換時に有効。GBP_USDがレンジ解消した場合 |
| `squeeze-release-momentum` (SENTINEL) | EUR_USD | TRENDING_UP環境で適合。ただしN蓄積優先 |

**優先度C（不適合・非推奨）**

| 戦略 | ペア | 理由 |
|---|---|---|
| `rnb_usdjpy` | USD_JPY | direction_filter 11件ブロック。USD_JPYレジームRANGING+Slope≈ゼロで機会なし |
| `daytrade_eurgbp` | EUR_GBP | regime_trend_bull_dt_tf ブロック継続中。現状レジームで適合せず |
| `london-fix-reversal` | GBP_USD | BT EV=−0.150（GBP_USD）。SENTINEL昇格済みだが本ペアのEV負値は留意 |

### OANDA転送率への留意

現在のLive Rate **4%**（50件中2件SENT）は極めて低い。`shadow_tracking`による19件スキップが支配的。ロンドンセッションで実際にエントリーシグナルが発火した場合、OANDA到達率の実態を確認すること。

---

## 6. クオンツ見解

### 最重要シグナル

**東京セッション完全不発 + Live Rate 4%という二重の"不活性"が本日の構造的問題。**

トレードゼロ自体はフィルタ正常動作だが、OANDA転送率4%（shadow_trackingが19/19件をスキップ）は、仮にロンドンでシグナルが発火しても**本番執行に到達しない確率が高い**ことを示唆している。スプレッドガードとshadow_trackingの二段フィルタにより、現在のシステムはデモ観察モードに近い稼働実態にある。

月利100%目標（DD防御0.2x下でBT推定47%）に対し、**エントリー機会の創出よりも機会の消滅**が先行している状態。ロンドンセッションでELITE戦略（trendline-sweep/session-time-bias）がシグナル発火した際、それが実際にOANDA執行まで到達するかを最優先でモニタリングすべき。N蓄積もゼロのまま推移しており、Sentinel→OANDA昇格への道筋が全く前進していない点は構造的懸念として記録する。
