# Post-Tokyo Report: 2026-04-15

## Analyst Report
# Post-Tokyo Report — 2026-04-15 06:20 UTC（JST 15:20）

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| セッション時間 | UTC 00:00–06:00 |
| N（件数） | 13 |
| WR | 38.5% |
| PnL | **−1.5 pips** |
| 主要ペア | USD_JPY（11件）、EUR_JPY（1件） |

> **N=13（統計的には「傾向」域）。セッション全体は軽微なマイナスで着地。**

---

## 2. What Worked ✅

| 戦略 | ペア | 結果 | PnL | 成功要因 |
|---|---|---|---|---|
| **bb_rsi_reversion** | USD_JPY | 4勝0敗 | +14.1 pips | RANGING（ATR%ile 36%）局面でのBB+RSI平均回帰が機能、TP_HIT主体で方向感一致 |
| **sr_channel_reversal** | USD_JPY | 1勝1敗 | +3.1 pips | 1件のTP_HIT（+6.1pips）が損失を上回る、S/Rレベルの精度が奏功 |

**bb_rsi_reversion が唯一EV正（+3.53）かつ高WR（100%）を記録**。ただし N=4 のため過信禁物。

---

## 3. What Didn't Work ❌

| 戦略 | ペア | 結果 | PnL | 失敗要因 |
|---|---|---|---|---|
| **bb_squeeze_breakout** | USD_JPY | 0勝2敗 | −6.6 pips | SL_HIT×2 — RANGINGレジームでブレイクアウト系はフォルスブレイク多発 |
| **vol_surge_detector** | USD_JPY | 0勝1敗 | −3.6 pips | SL_HIT — 低ATR局面（36%ile）でボラ急騰検知が機能しない |
| **engulfing_bb** | USD_JPY | 0勝2敗 | −3.9 pips | TIME_DECAY_EXIT + SL_HIT — RANGING内でのパターン失敗 |
| **dual_sr_bounce** | EUR_JPY | 0勝1敗 | −3.3 pips | TIME_DECAY_EXIT — EUR_JPY スプレッド1.3pipと相まって時間切れ損失 |
| **ema_trend_scalp** | USD_JPY | 0勝1敗 | −1.3 pips | TIME_DECAY_EXIT — トレンドなし（SMA20 slope ≈ −0.00031）で趨勢方向が不定 |

**共通失敗テーマ：全ペアがRANGINGレジームにもかかわらず、ブレイクアウト・トレンド追随系を複数エントリーしていること。**

---

## 4. 戦略調整判断

### 判断: **NO（コード変更なし）**

根拠：

| 観点 | 判断 |
|---|---|
| N=13 | 統計的判断域（N≥30）未達 — パラメータ変更の根拠として不十分 |
| BT vs Live 乖離 | session_time_bias/GBP_USD が N_Live=3, WR=0%（🔴アラート）— ただしN=3で確定判断不可 |
| bb_squeeze_breakout | RANGING局面での失敗は構造的だが、N=2では降格根拠にならない |
| vol_surge_detector | N=1 — データなしと同義 |

**監視強化対象として記録するに留める。N≥10到達後に再評価。**

---

## 5. ロンドンセッション準備（UTC 07:00–）

### レジーム現況と移行予測

| ペア | 現レジーム | ATR%ile | 移行予測 |
|---|---|---|---|
| EUR_USD | RANGING | 53% | ロンドン開始でボラ拡大→ TRENDING移行の可能性あり |
| GBP_USD | RANGING | 57% | 同上、gbp_asia_flash_crash ブロック（88件）が示す通り急騰リスク内包 |
| USD_JPY | RANGING | 36% | 低ATRのまま推移する可能性高 — 平均回帰系有利継続 |
| EUR_JPY | RANGING | 34% | 低ボラ — スプレッドコスト比率が高いためスキャルプは不利 |
| GBP_JPY | RANGING | 34% | 同上 |

**ロンドン移行では EUR/GBP 系でボラ拡大が典型パターン。ただし全ペア現在RANGINGであり、ブレイクアウト系は「確認後エントリー」が原則。**

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| 🟢 高 | **bb_rsi_reversion** | USD_JPY | 本日東京でEV+3.53、RANGINGで機能実証（N=4 / 参考値だが整合） |
| 🟢 高 | **sr_channel_reversal** | USD_JPY | EV+1.55、TP_HIT実績あり |
| 🟡 中 | **session_time_bias** | EUR_USD, USD_JPY | ELITE_LIVE戦略、ロンドン時間帯は本来の得意セッション — ただし GBP_USD は WR=0%（N=3）で警戒 |
| 🟡 中 | **trendline_sweep** | EUR_USD, GBP_USD | ELITE_LIVE、ロンドンブレイクに強いがRANGING確認後エントリー推奨 |
| 🔴 低 | **bb_squeeze_breakout** | 全ペア | RANGING継続中はフォルスブレイクリスク高、積極配分は避ける |
| 🔴 低 | **vol_surge_detector** | USD_JPY | 低ATR局面では構造的不利 |
| 🔴 低 | **dual_sr_bounce** | EUR_JPY | スプレッドコスト（1.3pip）がEVを圧迫、低ATR局面でコスパ悪化 |

### ブロック状況の確認事項

- **rnb_usdjpy:direction_filter** が 640件（断トツ1位）→ rnb戦略がほぼ機能停止状態。これはシステム設計通りの動作だが、本戦略への依存度が実質ゼロであることを確認
- **USD net exposure 30,000u > 20,000u limit** が scalp/daytrade 双方でブロック多発 → ロンドン入りでUSD系ポジション複数発火時は露出制限に当たりやすい。意図的制限として許容

### OANDA転送率

| 指標 | 値 | 評価 |
|---|---|---|
| Live Rate | 8%（4/50件） | shadow_tracking フィルターが 18件ブロック — システム正常動作 |
| Bridge Status | sent=1, filled=1, skipped=18 | ほぼ全量がデモ/シャドウ追跡中 |

**→ OANDA本番転送は極めて限定的。現状はデモ蓄積フェーズとして適正動作。**

### Sentinel N蓄積進捗（代表例）

Cutoff（2026-04-08〜）以降の蓄積状況：現在N=13/日。**N=30 昇格基準まで、現在のトレード頻度（約2件/hr）では推定 10〜15時間のセッション稼働が必要。** 週次での昇格判断を目標とした継続的蓄積を確認。

---

## 6. クオンツ見解

### 最重要シグナル — **「レジームと戦略ミスマッチ」の構造的損失**

本日東京セッションの損失（−1.5 pips）は数値上は軽微だが、**失敗パターンが一貫している点が重要**。

- **全5ペアがRANGING判定（ATR%ile 34〜57%）** にもかかわらず、bb_squeeze_breakout・vol_surge_detector・ema_trend
