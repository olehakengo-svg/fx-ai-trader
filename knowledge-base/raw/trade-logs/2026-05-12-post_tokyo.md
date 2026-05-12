# Post-Tokyo Report: 2026-05-12

## Analyst Report
# Post-Tokyo Report — 2026-05-12 08:47 UTC (JST 15:47)

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| セッション (UTC 00:00–06:00) | **トレードなし** |
| PnL | ¥0 |
| トレード数 | 0 |
| 勝率 (WR) | N/A |

**東京セッション: トレードなし**（全モード合計 Trades=0）

---

## 2. What Worked

**該当なし** — 東京セッション中、執行トレードが存在しないため評価不可。

---

## 3. What Didn't Work

**該当なし** — 同上。ただし、以下のブロック事象が「実質的な機会損失」として記録されている。

### 主要ブロック事象（Block Counts TOP 15より）

| 優先度 | 理由 | Count | 戦略 | 解釈 |
|---|---|---|---|---|
| 🔴 | `direction_filter` | 13 | rnb_usdjpy | USD/JPY: ATR%ile=74%, SMA Slope=-0.340 → 下降トレンド中のレンジ戦略がフィルタで全ブロック |
| 🔴 | `hedge_block` | 10 | daytrade_gbpusd | GBP/USD方向が相殺ポジションと衝突、ヘッジ規制発動 |
| 🟡 | `recent_emit` | 9+3 | daytrade_eur / daytrade | 短時間内の重複エミット防止フィルタが連続作動 |
| 🟡 | `r2_shadow_demoted_cell` | 8+8+5+3+1 | scalp/scalp_5m/scalp_5m_eur/scalp_eur/daytrade_eurjpy | シャドウ降格セルへのエントリーが複数戦略で阻止（計25件） |
| 🟠 | `score_gate` | 7+3 | daytrade / daytrade_gbpusd | スコア閾値未達で10件ブロック |

**r2_shadow_demoted_cellが合計25件**と本日最大のブロック源であり、Scalp系全体の執行能力を実質的に制限している。

---

## 4. 戦略調整判断

**→ NO（コード変更なし）**

根拠:
- Fidelity Cutoff後のクリーンN蓄積中。全戦略で本日N=0であり、統計的判断の根拠がない
- OANDA転送率0%（SENT=0/50、全SKIP）はshadow_tracking=20件が示す通り、意図的シャドウ監視期間の継続であり、異常ではない
- BT vs Live乖離の`xs_momentum GBP_USD`（ΔWR=−30.2pp、N_Live=3）はN<10のため「データなし」扱い — 過剰反応禁止
- レジーム判断（EUR/JPY・GBP/JPYがVOLATILE、USD/JPYがRANGING高ATR）でパラメータ変更の必要性を示す構造的証拠は現時点で不十分

---

## 5. ロンドンセッション準備 (UTC 07:00–)

### レジーム変化予測

| ペア | 現在 | ロンドン開幕予測 | 根拠 |
|---|---|---|---|
| EUR/JPY | VOLATILE (ATR 81%ile) | **VOLATILE継続** | SMA Slope −0.00217、下降圧力残存 |
| GBP/JPY | VOLATILE (ATR 78%ile) | **VOLATILE継続** | Slope ≈ 0、方向感なし・高ボラティリティ |
| USD/JPY | RANGING (ATR 74%ile) | **高ATR RANGING** | SMA Slope −0.340は強め → ブレイク警戒 |
| EUR/USD | RANGING (ATR 34%ile) | **RANGING→軽ブレイク候補** | ATR低位 × Slope +0.00124、ロンドン流動性増で上抜け試験の可能性 |
| GBP/USD | RANGING (ATR 45%ile) | **RANGING** | Slope +0.00307、緩やかな上昇バイアス |

### 推奨戦略配分

```
【優先度 HIGH】
- trendline-sweep (ELITE_LIVE): EUR_USD / GBP_USD
  → RANGING低ATRペア × ロンドン流動性増のブレイクアウトに最適
  → BT EV: EUR_USD=+0.927 / GBP_USD=+0.599 — 最高確度

【優先度 MEDIUM】
- session-time-bias: EUR_USD
  → ロンドン時間バイアスが最も効く戦略。EV=+0.215、WR=69.6%
- squeeze-release-momentum: EUR_USD
  → ATR低位(34%ile)からのスクイーズ解放シナリオに合致。EV=+0.656

【優先度 LOW — 監視のみ】
- daytrade_eurjpy / daytrade_gbpjpy
  → VOLATILE環境でDTはブロック多発リスク。r2_shadow_demoted_cell継続に注意
- rnb_usdjpy
  → direction_filterが13件ブロック済み。USD/JPY SMA Slope=−0.340の下降バイアス中はRANGE戦略を抑制

【NO ACTION推奨】
- scalp_xau / daytrade_xau (OFF)
- rnb_usdjpy (direction_filter発動継続中 — 強制的に機会なし)
- xs_momentum GBP_USD (N_Live=3、BT乖離−30.2pp — N=10到達まで判断保留)
```

### DD防御状況
- **DD=28.01%、防御0.2x継続** → サイズ縮小状態でロンドンに入る。これは正当な防御であり、変更不要

---

## 6. クオンツ見解

### 最重要シグナル

**「r2_shadow_demoted_cell 25件」がシステム全体のスループットボトルネック**

Scalp系4戦略（scalp, scalp_5m, scalp_5m_eur, scalp_eur）で合計25件のエントリーがシャドウ降格セルによりブロックされた。これはシグナル生成能力はあるが執行への到達を体系的に阻まれている状態を示す。

OANDA転送率0%（shadow_tracking起因）と合わせると、本日の東京セッションは「シグナル生成→ブロック→未執行」のサイクルが完結しており、クリーンデータの蓄積が進んでいない。N蓄積ペースが想定を下回っている可能性が高く、**昇格基準N≥30への到達タイムラインが延伸するリスク**がある。

ロンドンセッションで注視すべきは、trendline-sweepがEUR/USD・GBP/USDのRANGING環境で実際にエントリーを通すか否か。これが本日唯一の「N蓄積の実績機会」である。

---

*Report generated: 2026-05-12 08:47 UTC | Fidelity Cutoff: 2026-04-08T00:00:00Z | DD Mode: Defensive 0.2x*
