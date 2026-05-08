# Post-London Report: 2026-05-08

## Analyst Report
# Post-London Report — 2026-05-08 17:04 UTC

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| トレード数 | 7件 |
| 勝率 | 57.1%（4勝3敗） |
| PnL | **−4.1 pips** |
| セッション評価 | 僅少マイナス — 戦略間でパフォーマンスが二極化 |

> ※本日累計（9件、+4.9 pips）との差分から、東京セッション分2件で約+9.0 pips獲得と推算される。ロンドンセッション単体では利益を返す展開。

---

## 2. What Worked ✅

### `vix_carry_unwind` / USD_JPY — +17.8 pips（3戦全勝）

| トレード | 方向 | PnL | クローズ理由 |
|---|---|---|---|
| #1 | SELL | +9.0 | OANDA_SL_TP |
| #2 | SELL | +0.8 | OANDA_SL_TP |
| #3 | SELL | +8.0 | OANDA_SL_TP |

- **成功要因**: USD_JPYが`VOLATILE`レジーム（ATR%ile 76%）かつSMA20スロープが−0.00345（下方向）で、JPY高方向へのモメンタムとアンワインド方向が完全に一致。全3件がSL/TP正常作動（OANDA_SL_TP）でスリッページなく決済。
- **Spread 0.8 pips**は許容範囲内。EV +5.93は本日最高。

---

## 3. What Didn't Work ❌

### `xs_momentum` / GBP_USD — −16.9 pips（1勝2敗）

| トレード | 方向 | PnL | クローズ理由 |
|---|---|---|---|
| #1 | BUY | −9.5 | SL_HIT |
| #2 | BUY | +1.3 | OANDA_SL_TP |
| #3 | BUY | −8.7 | SL_HIT |

- **失敗要因**: GBP_USDは`RANGING`（ATR%ile 40%）で、モメンタム戦略が本来機能しにくいレジームにも関わらず全3件がBUY方向に集中。SL_HITが2件と損切り多発。
- BT乖離アラート🔴: WR_BT 63.5% vs WR_Live 33.3%（ΔWR −30.2pp）— **構造的乖離の可能性あり**。

### `fib_reversal` / EUR_USD — −5.0 pips（0勝1敗）

- **失敗要因**: EUR_USDは`RANGING`（ATR%ile 40%）でSMA20スロープが僅かに上向き（+0.00236）。N=1のため判断材料として不十分だが、レジーム適合性に疑問。

---

## 4. 東京との比較

| 指標 | 東京（推算） | ロンドン | 変化 |
|---|---|---|---|
| N | 2件 | 7件 | +5件（流動性増加） |
| WR% | ~100%（推算） | 57.1% | 大幅低下 |
| PnL | ~+9.0 pips | −4.1 pips | 反転 |
| レジーム | 確認不可 | RANGING中心 | 方向感なし |

- 東京セッションでは少ないトレード数で高いWRを達成（推算）したが、ロンドンではGBP_USD `RANGING`環境下でのモメンタム戦略が足を引っ張った。
- ロンドン後半（Fix前後）のGBP_USD変動は確認できるが、BUY方向への一方向集中が損失を拡大させた。

---

## 5. NYセッション準備

### レジーム予測（UTC 17:00以降）

| ペア | 現状 | NY予測 | 根拠 |
|---|---|---|---|
| USD_JPY | VOLATILE↓ | VOLATILE継続 | 米指標（CPI/雇用）次第でATR上昇余地。JPY高トレンド継続中 |
| GBP_USD | RANGING | 方向感出始め可能性 | NY流動性流入でRanging脱出の可能性あるが、確認前はモメンタム不適 |
| EUR_USD | RANGING | RANGING継続 | スロープ弱く方向転換シグナル薄 |
| JPY系(EUR/GBP) | VOLATILE | VOLATILE継続 | スロープがJPY高方向、NY序盤も継続の可能性 |

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 理由 |
|---|---|---|---|
| **HIGH** | `vix_carry_unwind` | USD_JPY | VOLATILE + 下方向トレンド継続中。本日3戦全勝、EV+5.93と最高水準 |
| **HOLD** | `xs_momentum` | GBP_USD | **RANGING環境が解消されるまで様子見**。BT乖離🔴継続中、N=3のみ |
| **CAUTION** | `fib_reversal` | EUR_USD | N=1、RANGING継続 — NYでは新規エントリー慎重に |

> **`xs_momentum`/GBP_USD については NO ACTION推奨（レジーム解消確認まで）**

---

## 6. 本日暫定結果

| 指標 | 値 |
|---|---|
| 累計トレード数 | 9件 |
| 累計WR% | 66.7% |
| 累計PnL | **+4.9 pips** |
| 最大貢献戦略 | `vix_carry_unwind` / USD_JPY（+17.8 pips） |
| 最大損失戦略 | `xs_momentum` / GBP_USD（−16.9 pips） |

---

## 7. クオンツ見解

### 最重要シグナル — `xs_momentum`/GBP_USDのBT乖離🔴が示す構造的リスク

**ΔWR −30.2pp（BT 63.5% → Live 33.3%）は偶発的ではなく、レジーム不一致に起因する可能性が高い。** GBP_USDが`RANGING`（ATR%ile 40%）である限り、モメンタム系戦略のエッジは失われる。本日の3件すべてがBUY方向に集中しており、通貨方向バイアスも疑われる。

N=3と統計的判断には不十分だが、RANGING環境でのモメンタム戦略投入は**構造的な相性の悪さ**であり、環境が変わるまで引き続き監視対象とすべき。N=30到達前にレジーム変化（GBP_USDのVOLATILE移行）を確認してから評価を再開することを推奨する。

一方、`vix_carry_unwind`/USD_JPYはVOLATILE×下方向トレンドという最適環境で結果を出しており、**現在のレジームにおける最も信頼できるエッジ**として引き続き注目に値する。
