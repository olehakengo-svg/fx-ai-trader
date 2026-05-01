# Post-Tokyo Report: 2026-05-01

## Analyst Report
# Post-Tokyo Report — 2026-05-01 JST 15:00

---

## 1. 東京セッション結果

| 指標 | 値 |
|---|---|
| 対象時間 | UTC 00:00–06:00 |
| N（セッション内） | 6 |
| WR | 50.0% |
| PnL | **+1.6 pips** |
| 本日累計N | 10 / WR 50.0% / +10.8 pips |

戦略: `bb_rsi_reversion` / ペア: USD_JPY のみ稼働。全トレードBUY方向に偏重（6件中5件）。

---

## 2. What Worked

| # | Strategy | Pair | Dir | PnL | Reason |
|---|---|---|---|---|---|
| ✅ | bb_rsi_reversion | USD_JPY | BUY | +7.1 | 最大勝ちトレード — BB+RSI逆張りがUSD_JPYボラタイル環境（ATR%ile 64%）でTP到達 |
| ✅ | bb_rsi_reversion | USD_JPY | BUY | +4.2 | スプレッド0.8pipと低摩擦を維持しつつTP_HIT達成 |
| ✅ | bb_rsi_reversion | USD_JPY | BUY | +3.6 | 同上、3連続TP_HIT局面でEV貢献 |

**成功要因（共通）**: USD_JPY VOLATILE（64%ile）レジームにおいて、BB逆張りの価格伸長が逆方向に走る局面でTPへ到達。スプレッド0.8pipは同ペアとして許容範囲内。

---

## 3. What Didn't Work

| # | Strategy | Pair | Dir | PnL | Reason |
|---|---|---|---|---|---|
| ❌ | bb_rsi_reversion | USD_JPY | SELL | **-9.1** | 最大損失 — SELLエントリーがSL_HITで被弾 |
| ❌ | bb_rsi_reversion | USD_JPY | BUY | -3.2 | SL_HIT — BB反発失敗 |
| ❌ | bb_rsi_reversion | USD_JPY | BUY | -1.0 | TIME_DECAY_EXIT — TP未到達で時間切れ |

**失敗要因**: 
- SELL側の-9.1pipが全体PnLを圧迫。USD_JPYはSMA20 Slope=-0.00054（ほぼフラット）だが、VOLATILE環境ではモメンタム継続リスクが高い。方向バイアスなしの逆張りでSELLエントリーが下降加速に捕まった可能性。
- TIME_DECAY_EXIT（-1.0）は戦略上許容範囲だが、ボラ高環境でのTP設定が狭い可能性も示唆。

---

## 4. 戦略調整判断

**判断: NO（コード変更なし）**

根拠:
- セッション内N=6は統計的有意性なし（N<10は「データなし」扱い）
- EV=+0.27は正だが、N=6での判断は確率誤差が大きすぎる
- Fidelity Cutoff後の`bb_rsi_reversion` USD_JPY累計Nが不明だが、本日累計N=10でもまだ「傾向」段階
- **N=30到達まで現状維持が原則**

---

## 5. ロンドンセッション準備（UTC 07:00–12:00）

### レジーム変化予測

| Pair | 現在レジーム | 東京→ロンドン予測 | 注目点 |
|---|---|---|---|
| USD_JPY | VOLATILE (64%ile) | ボラ維持〜拡張 | 欧州勢参入でSMA Slope変化に注意 |
| EUR_USD | RANGING (43%ile) | レンジ継続またはブレイク | GBP_USD TRENDING_UPに引きずられてブレイクアウト示唆 |
| GBP_USD | TRENDING_UP (45%ile) | トレンド継続の可能性 | Slope+0.00540が最強、ロンドン開始でモメンタム加速リスク |
| EUR_JPY | VOLATILE (62%ile) | ボラ継続 | JPY勢のクロス変動に注意 |
| GBP_JPY | VOLATILE (52%ile) | ボラ継続 | GBP強+JPY軟のクロス上昇圧力 |

### 推奨戦略配分

**稼働継続（現状どおり）:**
- `scalp`/`scalp_5m`系: GBP_USD TRENDING_UPはScalpの順張りに有利。hedge_block（65件）が多いが、これはリスク制御が機能している証左
- `daytrade_gbpusd`: TRENDING_UP環境で有利。ただし`max_per_mode_pair`ブロック32件は既にポジション集中の懸念あり
- `daytrade_eurjpy`/`daytrade_gbpjpy`: VOLATILE環境継続でDT系は引き続き適性あり

**注意:**
- `rnb_usdjpy`: direction_filter 32件ブロック。USD_JPYはSMA Slope≈0でフラット、direction_filterが正常機能している
- `scalp_eur`: max_open 54件ブロック — EUR_USD RANGING環境でScalpが頻繁にエントリー試行も上限到達。レンジ相場ではScalpのEV低下に注意

### OANDA転送率への注目

現在Live Rate **8%**（50件中4件のみSENT）。shadow_trackingブロック17件。これはデモ検証フェーズが主因だが、ロンドンセッションでN蓄積が加速する可能性あり。

---

## 6. クオンツ見解

---

### 🔴 最重要シグナル

**`vix_carry_unwind` USD_JPY — BT乖離が危険水域**

BT WR=100%（N=0、サンプルなし）に対してLive WR=33.3%（N=3）。ΔWR=-66.7ppで🔴アラート。ただしN=3はほぼ統計的意味なし。しかしBT N=0という点が問題の本質——**バックテストデータが存在しない状態でPAIR_PROMOTEDに昇格している**。この戦略はN=30到達まで判断保留が適切だが、現状EV不明のまま本番稼働している点は構造リスク。

---

### 構造的観察

1. **ブロック偏重**: TOP15ブロック計346件のほとんどが`hedge_block`と`max_open`に集中。これはリスク管理が機能している証拠だが、裏返すとエントリー機会の消化効率が低い。有効エントリーが少ない（本日累計N=10）のに対し、ブロック数が圧倒的に多い構造。
2. **方向偏重**: 東京セッション6件中5件がBUY。USD_JPY Slopeがほぼフラット（-0.00054）な中でのBUY偏重は、戦略パラメータまたは直近レジームバイアスの可能性。
3. **OANDA転送8%の低さ**: 本番稼働戦略（ELITE_LIVE/PAIR_PROMOTED）のN蓄積が遅く、KBに掲載の上位戦略（gbp-deep-pullback、trendline-sweep等）のLive Nがほぼ蓄積されていない状態が続いている。N=30昇格基準に対して現在の蓄積ペースでは到達時期が見通せない。

---

### 推奨アクション

1. **`vix_carry_unwind` USD_JPY**: N=30到達まで統計判断を保留。BT N=0という異常値を記録しておき、N=10時点で中間レビューを実施すること
2. **OANDA転送率8%の構造**: 現在の低転送率はDD=28.01%によるDD防御モード（0.2x）が原因と推定。DDが回復基準に達した時点で転送率の引き上げ可否を検討
3. **東京セッションは現状維持**: N=6/EV=+0.27は正のEVを示しているが判断不可能域
