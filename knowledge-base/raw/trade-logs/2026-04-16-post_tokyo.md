# Post-Tokyo Report: 2026-04-16

## Analyst Report
# Post-Tokyo Report (JST 15:00 / UTC 06:00) — 2026-04-16

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| セッション時間 | UTC 00:00–06:00 |
| トレード数 (N) | 20 |
| 勝率 (WR) | 20.0% (4W / 16L+BE) |
| PnL | **−62.0 pips** |
| 平均EV/トレード | −3.10 |

**判定: 明確なアンダーパフォーマンス。勝率20%はランダムウォーク以下。**

---

## 2. What Worked ✅

| 戦略 | ペア | N | WR | PnL | 成功要因 |
|---|---|---|---|---|---|
| **bb_rsi_reversion** | USD_JPY | 4 | 75.0% | +6.1 pips | RANGING相場(ATR%ile 34%)でのBBタッチ逆張りが機能、TP_HIT×3でEV+1.52 |
| **sr_channel_reversal** | USD_JPY | 1 | 100.0% | +5.0 pips | チャネル上限でのSELL、TP_HIT — ただしN=1は統計的参考値のみ |

**唯一の構造的ポジティブシグナル: bb_rsi_reversionのEV+1.52（N=4, 参考値水準）**

---

## 3. What Didn't Work ❌

| 戦略 | ペア | N | WR | PnL | 失敗要因 |
|---|---|---|---|---|---|
| **vix_carry_unwind** | USD_JPY | 1 | 0% | −22.7 pips | 単一トレードで最大損失、SL_HIT — VIX系はRANGING相場で機能しない |
| **stoch_trend_pullback** | USD_JPY | 3 | 0% | −13.0 pips | USD_JPYはRANGING(SMA slope≈−0.00047)でトレンドフォローが逆機能 |
| **fib_reversal** | USD_JPY | 3 | 0% | −10.3 pips | 方向性なし相場でのフィボFibターゲットが機能せず、SL_HIT×2 |
| **sr_fib_confluence** | USD_JPY | 1 | 0% | −10.8 pips | SL_HIT — N=1のため統計評価不可、損失インパクトは大 |
| **vol_surge_detector** | USD_JPY | 3 | 0% | −5.2 pips | ATR%ile=34%（低ボラ）でのボラティリティ系戦略は構造的ミスマッチ |

**構造的問題: USD/JPYのRANGINGレジームに対し、トレンド系・ボラ系戦略が集中（N=20のうち18件がUSD_JPY）**

---

## 4. 戦略調整判断

**→ コードパラメータ変更: NO**
**→ 運用判断レベルの見直し: YES — 以下の観点で**

| 判断事項 | 根拠 |
|---|---|
| **stoch_trend_pullback の一時停止を検討** | N=3, WR=0%, EV=−4.33。USD_JPYがRANGINGである限り、トレンドフォロー系の期待値は構造的にマイナス |
| **vix_carry_unwind の単発リスク監視強化** | 1トレードで−22.7pipsは全体PnLの36%を占める。ロットサイズまたは出動条件の再評価が必要 |
| **vol_surge_detector の出動条件確認** | ATR%ile=34%（低ボラ）下でのボラ系戦略の発動は設計意図と乖離している可能性 |
| **bb_rsi_reversion は継続** | EV+1.52、WR=75%（N=4）— RANGINGレジームとの相性◎。N=30到達を優先して蓄積継続 |

---

## 5. ロンドンセッション準備

### レジーム予測（UTC 07:00–12:00移行）

| ペア | 現レジーム | ロンドン移行予測 | 根拠 |
|---|---|---|---|
| USD_JPY | RANGING | **RANGING継続 → 若干ブレイク試行** | SMA slope=−0.00047、ATR%ile=34%で低エネルギー。ロンドンOpen時に一時的ボラ拡大の可能性 |
| EUR_USD | TRENDING_UP | **TRENDING_UP強化** | ATR%ile=53%、SMA slope=+0.00583。ロンドン主要ペアとして活発化予想 |
| GBP_USD | RANGING | **RANGING→軽度TRENDING_UP移行** | ATR%ile=53%は高め。GBPロンドン参入でボラ拡大可能性 |
| EUR_JPY | TRENDING_UP | **TRENDING_UP継続** | ATR%ile=36%は低めだが方向性明確 |
| GBP_JPY | RANGING | **RANGING継続** | ATR%ile=36%、SMA slope低水準 |

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| ◎ 最優先 | **bb_rsi_reversion** | USD_JPY | 東京で実証済み(WR=75%)、RANGINGレジーム継続中 |
| ◎ 最優先 | **session_time_bias** (KB: ELITE_LIVE) | EUR_USD, GBP_USD, USD_JPY | ELITE_LIVE、ロンドンセッションとの相性が設計上最高 |
| ○ 推奨 | **trendline_sweep** (KB: ELITE_LIVE) | EUR_USD, GBP_USD | TRENDING_UP継続ペア、BT EV+0.927(EUR)/+0.599(GBP) |
| ○ 推奨 | **orb_trap** (KB: PAIR_PROMOTED) | EUR_USD, GBP_USD | ORB=ロンドンオープンと構造的相性良好、USD_JPY EV+0.866 |
| △ 条件付き | **post_news_vol** (KB: PAIR_PROMOTED) | GBP_USD | GBP_USD EV+1.762(BT)。ただしニュース有無を確認してから |
| ✗ 停止推奨 | **stoch_trend_pullback** | USD_JPY | RANGINGで構造的ミスマッチ継続見込み |
| ✗ 停止推奨 | **vix_carry_unwind** | USD_JPY | 低ボラ環境下での単発大損リスク高 |
| ✗ 停止推奨 | **vol_surge_detector** | USD_JPY | ATR%ile=34%で設計前提と乖離 |

### エクスポージャー管理

- **USD net exposure超過ブロックが多発** (scalp/scalp_5m_gbp: 各14件, scalp_5m: 4件) → ロンドンでも同様の制限継続予想。USDペア集中を避けEUR系に分散を意識
- **OANDA転送率16%** (50件中8件SENT) — shadow_tracking=17件が主因。本番ポジションは限定的

---

## 6. クオンツ見解

### 最重要シグナル

**① 本日のUSD_JPY集中リスク（構造的問題）**
N=20のうち18件がUSD_JPY、しかも同ペアはRANGINGレジーム(ATR%ile=34%, SMAフラット)。トレンド系・ボラ系戦略が一斉に発動してすべてSL_HITまたはTIME_DECAY_EXIT — これはシグナル品質の問題ではなく**レジームとのミスマッチ**が主因。WR=20%はノイズではなく構造的な必然。

**② vix_carry_unwindの単発損失集中リスク**
1トレードで−22.7pips（セッション損失の約37%）。N=1のため統計評価不能だが、リスクあたりリターンの非対称性が極めて不利。低ボラ・RANGINGレジームでのV
