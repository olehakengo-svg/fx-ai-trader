# Post-London Report: 2026-05-01

## Analyst Report
# ロンドンセッション総括レポート
**2026-05-01 16:46 UTC | Post-London Report**

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| セッション内トレード数 | **5件** |
| 勝率（WR） | **40.0%** |
| 純PnL | **-10.6 pips** |
| 最大単発損失 | -22.5 pips（gbp_deep_pullback / GBP_USD） |
| 最大単発利益 | +10.2 pips（bb_rsi_reversion / USD_JPY） |

セッション全体は赤字。gbp_deep_pullbackの1件がセッションPnLを大きく毀損。

---

## 2. What Worked ✅

| 戦略 | ペア | PnL | 成功要因 |
|---|---|---|---|
| **bb_rsi_reversion** | USD_JPY | +10.2 pips | VOLATILE（ATR%ile 64%）な相場でBBバンド反発が明確に機能し、TP到達。 |
| **bb_rsi_reversion** | EUR_USD | +7.9 pips | RANGING環境下でRSI過売から反発、スプレッド0.8pipsに対し+7.9pipsの良好なR:R。 |

bb_rsi_reversionは本日2W1Lで安定。スプレッド負荷（0.8pips）に対してペイオフ比率は十分。

---

## 3. What Didn't Work ❌

| 戦略 | ペア | PnL | 失敗要因 |
|---|---|---|---|
| **gbp_deep_pullback** | GBP_USD | -22.5 pips | TRENDING_UP環境でSL_HIT — ディープ・プルバック狙いが続伸トレンドに逆らい直撃。 |
| **bb_rsi_reversion** | USD_JPY | -6.1 pips | TIME_DECAY_EXITによる強制クローズ — 時間切れ退場でTP未到達。 |
| **vix_carry_unwind** | USD_JPY | -0.1 pips | BREAKEVENでSL_HIT — BT WR=67.3%に対し直近ライブWR=33.3%（🔴乖離アラート）。 |

**最重要損失: gbp_deep_pullback / GBP_USD -22.5pips**
GBP_USDは現在TRENDING_UP（SMA20 Slope=+0.00540）。ディープ・プルバック戦略はトレンドの強い環境では構造的に不利。ELITEステータス（BT EV=+1.064）であっても現レジームとの適合性に疑問符。

---

## 4. 東京セッションとの比較

| 指標 | 東京（推定） | ロンドン |
|---|---|---|
| トレード数 | 9件（14-5=9） | 5件 |
| 累計PnL貢献 | -7.1 pips（推定） | -10.6 pips |
| 主要レジーム | — | VOLATILE（USDJPY/EURJPY/GBPJPY）+ RANGING（EURUSD）+ TRENDING（GBPUSD） |
| セッション特性 | 流動性低・方向感薄 | 流動性高・ただし方向性ブレ |

本日は東京・ロンドン両セッションとも赤字推移。本日累計14件で-17.7 pips（WR 42.9%）は期待値ライン（EV>+1.0目標）を大きく下回っている。gbp_deep_pullbackの単一トレードが-22.5pipsを計上しており、これなければ本日累計は+4.8 pipsで黒字だった計算。

---

## 5. NYセッション準備

### レジーム予測（UTC 16:00-21:00）

| ペア | 現状 | NY移行後予測 |
|---|---|---|
| USD_JPY | VOLATILE（ATR 64%ile） | 雇用指標次第で更にATR拡大リスク — ボラ継続 |
| GBP_USD | TRENDING_UP | トレンド継続の可能性高 — 逆張り系は危険 |
| EUR_USD | RANGING | NY市場でレンジ・ブレイクアウトの可能性 |
| EUR_JPY / GBP_JPY | VOLATILE | 円ボラ続伸の場合、連れ高リスク |

### 推奨戦略配分

| 判定 | 戦略 | ペア | 理由 |
|---|---|---|---|
| ✅ 継続 | **bb_rsi_reversion** | USD_JPY, EUR_USD | 本日実績あり、VOLATILE+RANGINGに有効 |
| ✅ 継続 | **vix_carry_unwind** | USD_JPY | NYでボラ拡大なら機能余地、ただしWR乖離に注意 |
| ⚠️ 慎重 | **gbp_deep_pullback** | GBP_USD | **NO ACTION推奨** — TRENDING_UP環境との戦略ミスマッチが本日実証済み |

> **gbp_deep_pullback / GBP_USD については「何もしない」が最適。** トレンドが反転するシグナル（例：SMA20 Slope反転、ATR急落）が確認されるまでエントリー回避。

---

## 6. 本日暫定結果

| 指標 | 値 |
|---|---|
| 累計トレード数 | **14件** |
| 累計WR | **42.9%** |
| 累計PnL | **-17.7 pips** |
| OANDA転送率 | **0%（全50件SKIP / shadow_tracking）** |
| 主要ブロック | scalp_eur:market_close_30min（3件）、hedge_block系 |

---

## 7. クオンツ見解

### 最重要シグナル：**gbp_deep_pullback のレジーム適合性崩壊**

本日のセッション損失（-10.6pips）の**実質212%**がgbp_deep_pullback単体（-22.5pips）に起因する。同戦略はBTでEV=+1.064、WR=75.3%のELITE_LIVE認定だが、**GBP_USDが現在TRENDING_UP（SMAスロープ最大：+0.00540）**という環境下では、BT時の想定レジームと現実が乖離している可能性が高い。

ELITEステータスはBTの普遍的優位性を保証するものではなく、**現レジーム下でのエッジ有効性は別問題**である。N=1ではノイズだが、TRENDING環境でのディープ・プルバック戦略の構造的不利は理論的にも支持される。GBP_USDのトレンドが継続する間、同戦略のシグナルは見送ることを推奨する。vix_carry_unwindの🔴BT乖離（ライブWR 33.3% vs BT 67.3%）も引き続き監視対象だが、N=3のため判断保留。
