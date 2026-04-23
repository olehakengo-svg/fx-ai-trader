# Post-Tokyo Report: 2026-04-23

## Analyst Report
# Post-Tokyo Report｜2026-04-23 JST 15:00 (UTC 06:00)

---

## 1. 東京セッション結果

**東京セッション: トレードなし**

| 項目 | 値 |
|---|---|
| セッション内トレード数 | 0 |
| PnL (pips) | — |
| WR | — |
| 本日累計 (参考) | N=2, WR=50.0%, PnL=-3.1 pips |

UTC 00:00–06:00 の東京セッション中、全モードにおいてトレード執行はゼロ。本日累計2件（セッション外）は参考値として保持。

---

## 2. What Worked

**該当なし**（東京セッション中の執行トレードなし）

---

## 3. What Didn't Work

**直接的な損失トレードはなし。ただし「機会損失」を記録する。**

| ブロック理由 | 発生戦略 | 件数 | 主因解釈 |
|---|---|---|---|
| `regime_trend_bull_dt_tf` | daytrade | 4 | 全通貨がRANGINGレジームのため、トレンドフォロー系DTがタイムフレーム判定で弾かれた |
| `score_gate` | daytrade_eur / daytrade_gbpusd | 各4 | スコア閾値未達：ATR%ile 36–48%はエネルギー不足 |
| `same_price_3pip / 0pip` | scalp_5m / scalp_5m_gbp | 各4 | 値動きが僅少。レンジ相場での価格停滞が同一価格フィルタに抵触 |
| `sl_cluster` | daytrade_eurjpy | 3 | ストップ密集回避ロジックが発動：EUR_JPY RANGING+ATR36%は典型的なSLクラスター環境 |
| `direction_filter` | rnb_usdjpy | 3 | USD_JPY: SMA20 slope=+0.00061（ほぼフラット）→ 方向性不明でR&Bフィルタが遮断 |
| `spread_guard` | daytrade_gbpjpy / scalp | 計3 | GBP_JPY ATR33%（20日パーセンタイル低位）にもかかわらずスプレッド拡大圧力 |

**東京セッション不発の構造的原因：全5通貨ペアがRANGINGレジームに整列しており、DT系・Scalp系双方のエントリー条件を同時に満たせない状態。**

---

## 4. 戦略調整判断

**NO — パラメータ変更不要**

| 根拠 | 詳細 |
|---|---|
| Fidelity Cutoff後データ不足 | 本日累計N=2（参考値のみ）。判断基準N≥30に遠く及ばず |
| レジームは一時的 | 全ペアRANGING＋ATR%ile 33–48%は東京クローズ～ロンドンオープン前の典型的な低ボラ帯 |
| ブロック機能は正常動作 | block_countsは「誤動作」ではなく「設計通りの非執行」。フィルタの誤検知ではない |
| DD防御発動中 | DD=25.9%（defensive mode / 0.2x）→ 追加リスクテイクの根拠なし |

---

## 5. ロンドンセッション準備

### ATR/レジーム変化予測

```
現在（UTC 06:00）
  全ペア: RANGING / ATR%ile 33–48%（低位）
  SMA20 slope: 全ペア正値だが微小（最大EUR_JPY +0.00423）

ロンドンオープン（UTC 07:00–08:00）予測
  ・EUR_USD / GBP_USD: ロンドンフィックス/ブレイクアウト試行が期待される
  ・GBP_JPY: ATR33%は直近最低水準 → ロンドン初動でのATR急上昇余地あり
  ・USD_JPY: slope+0.00061はほぼフラット → 方向性確立まで待機推奨
```

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| 🔴 高 | `trendline-sweep` (ELITE_LIVE) | EUR_USD, GBP_USD | BT EV=+0.927/+0.599。ロンドン初動のブレイクアウトと相性最良 |
| 🔴 高 | `post-news-vol` (PAIR_PROMOTED) | GBP_USD | BT EV=+1.762 WR=88.5%。ロンドン時間の報道後ボラ拡張に直結 |
| 🟡 中 | `doji-breakout` (PAIR_PROMOTED) | GBP_USD | BT EV=+0.724。レンジ→ブレイク移行局面で発火条件が整いやすい |
| 🟡 中 | `session-time-bias` (ELITE_LIVE) | EUR_USD, GBP_USD, USD_JPY | BT EV=+0.215/+0.113/+0.580。時間帯バイアスはレジーム依存度が低い |
| ⚪ 低 | DT系全般 | EUR_JPY, GBP_JPY | sl_cluster / regime_gateが東京同様に発動する可能性が高い。ATR回復を確認してから |

**NO ACTION推奨の条件：** ロンドンオープン後30分でATR%ile≥55%に上昇しない場合、全DT系は引き続き非執行が合理的。

### DD防御継続確認

NAV=439,739 / DD=25.9% → defensive mode継続中。Kelly Half移行（Phase 3）は現状NG。クリーンデータ蓄積が最優先。

---

## 6. OANDA転送率・Sentinel進捗（補足）

| 指標 | 値 | 評価 |
|---|---|---|
| OANDA Live Rate | 8%（4/50件） | `shadow_tracking`による18件SKIP が主因。設計通り |
| Bridge: sent/filled | 1/1 | 執行精度100%（N=1のためサンプル不十分） |
| Bridge: skipped | 18件 | 全件 shadow_tracking → デモ蓄積フェーズとして正常 |
| Sentinel N進捗 | 本日N=2 | 昇格基準N≥30まで28件以上必要。週次ペースで見ると数日単位 |

---

## クオンツ見解

### 最重要シグナル1点

**「全ペアRANGING同時整列」は構造的非執行日の典型パターンであり、システムの正常動作である。介入不要。**

東京セッションゼロ執行の原因はシステム障害でも過剰フィルタでもない。ATR%ile 33–48%、SMA20 slope 微小正値という「方向感なき横這い」環境では、DT/Scalp双方の入口条件が設計通りに機能して遮断している。これは **損失を回避した正の貢献** として評価すべきだ。

1. **最重要シグナル**
   - `daytrade_gbpjpy`の`spread_guard`発動（ATR33%最低水準）と`daytrade_eurjpy`の`sl_cluster`発動（ATR36%）は、ロンドンオープン後のATR急回復時に最初に「解除→発火」する可能性が高いペアとして注目。ただし現時点での先行エントリーは不要。

2. **構造的観察**
   - OANDA Live Rate 8%（4/50件）は過去データの`shadow_tracking`優位が続いているが、**Bridge sent/filled比率1/1**は本番執行インフラとして問題なし。デモ蓄積フェーズの完了速度（N蓄積）がボトルネックであり、市場の取引機会頻度に依存する。
   - 本日累計N=2は**Fidelity Cutoff後の統計汚染ゼロ**という点では正しいが、月利100%目標に対してペース不足が顕在化している。これはレジーム環境の問題であ
