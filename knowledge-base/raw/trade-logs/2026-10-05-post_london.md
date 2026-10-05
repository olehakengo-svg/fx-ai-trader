# Post-London Report: 2026-10-05

## Analyst Report
# ロンドンセッション総括レポート
**2026-10-05 | UTC 07:00–16:00 | Post-London Report**

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| トレード数（N） | 1 |
| 勝率（WR） | 100.0% |
| セッションPnL | **+12.9 pips** |
| 平均EV/trade | +12.90 |

極めて低出来高のセッション。1件のみのサンプルであり、統計的判断は不可能（N<10）。

---

## 2. What Worked

| 戦略 | ペア | 方向 | PnL | 成功要因 |
|---|---|---|---|---|
| price_shock_rev_eur_gbp_h1_long | EUR_GBP | BUY | **+12.9 pips** | horizon（時間軸TP到達）により決済、スプレッド1.4pipsに対し十分な粗利を確保 |

**補足：** スプレッド比率 = 1.4 / 12.9 = **10.9%**（scalp基準30%を大幅に下回り、摩擦は許容範囲内）。

---

## 3. What Didn't Work

| 評価 |
|---|
| セッション内に敗退トレードは**ゼロ**。ただしN=1のため「うまくいった」という評価自体が統計的に無意味。 |

真の問題は「失敗トレードがなかった」ことではなく、**ロンドン時間帯を通じてシステムが1件しか発火しなかった**ことにある。

---

## 4. 東京セッションとの比較

データ上、本日累計N=3・WR=66.7%・PnL=+42.3 pipsから逆算すると：

| セッション | 推定N | 推定PnL | WR |
|---|---|---|---|
| 東京（推定） | 2 | 約+29.4 pips | 推定50–100% |
| ロンドン | 1 | +12.9 pips | 100% |
| **本日累計** | **3** | **+42.3 pips** | **66.7%** |

- **レジーム面：** EUR_JPY（VOLATILE 74%ile）・GBP_JPY（TRENDING_DOWN 71%ile）はロンドン終盤にかけてATRが高水準を維持。Trending/Volatile混在環境はDaytradeに有利な一方、Scalpのr2_shadow_demoted_cellによるブロックが大量発生しており（scalp系で計1,615件超）、スキャル戦略はロンドン帯でも実質的に発火抑制状態。
- **USD_JPY（RANGING 67%ile）：** rnb_usdjpyが1,060件のno_signalを記録—レンジ認定ながらシグナル発火には至らない閾値未達状態が続いている。

---

## 5. NYセッション準備（UTC 13:00–22:00、現在移行期）

### ATR/レジーム変化予測

| ペア | 現レジーム | NY移行後の見立て |
|---|---|---|
| GBP_USD | TRENDING_DOWN | 米指標次第でトレンド継続 or 急反転リスク。SMAスロープ−0.00526はまだ緩い |
| EUR_USD | VOLATILE | NY Open後の経済指標でATR拡大の可能性。Volatile維持見込み |
| USD_JPY | RANGING | 157.8近辺でのレンジ継続。rnb_usdjpyのno_signal状態が続く可能性が高い |
| GBP_JPY | TRENDING_DOWN | 209付近、スロープ−0.00618が最急。トレンドフォロー系に有利 |
| EUR_JPY | VOLATILE | SMAスロープ−0.00748が最急（下落方向）。Volatileのまま推移見込み |

### 推奨戦略配分

| 評価 | 戦略カテゴリ | 対象ペア | 根拠 |
|---|---|---|---|
| ✅ 発火期待 | daytrade_gbpjpy / daytrade_gbpusd | GBP_JPY, GBP_USD | TRENDING_DOWN × ATR高水準 = DT有利環境。order_bar_dedupによるブロックが多いが戦略自体は生きている |
| ✅ 発火期待 | daytrade_eur / daytrade_1h_eur | EUR_USD, EUR_JPY | VOLATILE環境継続見込み |
| ⚠️ 期待薄 | scalp系（scalp, scalp_5m, scalp_eur等） | 全ペア | r2_shadow_demoted_cellによるブロックが累計1,600件超、実質発火抑制中 |
| ❌ NO ACTION | rnb_usdjpy | USD_JPY | no_signal 1,060件——RANGING認定だがシグナル条件未充足。待機継続 |
| ❌ OFF状態 | daytrade_xau, scalp_xau, scalp_eurjpy | - | システムOFF。介入不要 |

> **scalp系については、r2_shadow_demoted_cellブロックが解消されない限りNYセッションでも実質NO ACTIONと同義。**

---

## 6. 本日暫定結果

| 指標 | 値 |
|---|---|
| 本日累計 N | **3** |
| 本日累計 WR | **66.7%** |
| 本日累計 PnL | **+42.3 pips** |
| OANDA NAV | **¥274,246.16** |
| Open Trades | **0**（クリーンポジション） |

---

## 7. クオンツ見解

### 最重要シグナル：**「発火抑制の慢性化」が本日最大のリスク**

ロンドン帯N=1・本日N=3という数字は、戦略が「機能している」のではなく**システムが大量ブロックにより機能不全に近い状態**であることを示している。Block分析を見ると、scalp系4戦略合計で**r2_shadow_demoted_cell 1,615件**が発生しており、これはシャドウ降格済みセルが大多数の機会を消去していることを意味する。さらにdaytrade系の**order_bar_dedup（計1,007件）**も並行して発火を抑制。

一方、唯一発火した `price_shock_rev_eur_gbp_h1_long`（+12.9 pips）はN=1のため昇格・降格どちらの判断材料にもならない（「データなし」扱い）。

**OANDAライブ転送率12%（50件中6件のみSENT）は、本番稼働の観点では過剰なデモ偏重状態。** shadow_trackingブロックが20件（うちauto_demoted・pair_demotedが各1件）であり、大半の機会がシャドウ評価段階でフィルタされている構造は、M3ミッション（月利+2〜3%）達成のための実口座N蓄積を根本的に妨げている。NYセッションにおいても、この構造的制約が解消されない限り有意なトレード発火は期待しにくい。
