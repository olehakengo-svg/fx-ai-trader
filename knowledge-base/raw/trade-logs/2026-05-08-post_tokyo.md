# Post-Tokyo Report: 2026-05-08

## Analyst Report
# Post-Tokyo Session Report — 2026-05-08 07:48 UTC (JST 15:48)

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| セッション (UTC 00:00–06:00) | **N=2, WR=100.0%, PnL=+9.0 pips** |
| 有効トレード戦略 | bb_rsi_reversion / USD_JPY |
| Spread 水準 | 0.8 pips（×2件、正常範囲） |

⚠️ **統計的扱い**: N=2 は「データなし」扱い。WR 100%・PnL+9.0 は参考値に留める。

---

## 2. What Worked

| 戦略 | ペア | 方向 | PnL | 成功要因 |
|---|---|---|---|---|
| bb_rsi_reversion | USD_JPY | SELL | +3.3 pips | ATR%ile 76%のVolatileレジームでBBバンド幅が十分確保され、平均回帰シグナルが機能した |
| bb_rsi_reversion | USD_JPY | BUY | +5.7 pips | 同上。逆方向TP_HITは市場の双方向性を示しており、レジーム整合性は高い |

---

## 3. What Didn't Work

**失敗トレード: なし（N=2, 全TP_HIT）**

ただし「機能しなかった」観点をブロック統計から補足する：

| ブロック主因 | Count | 示唆 |
|---|---|---|
| rnb_usdjpy: direction_filter | 31 | 方向フィルターが過剰抑制している可能性 |
| daytrade / daytrade_gbpusd: hedge_block | 30+30 | ヘッジブロックが東京セッション中の主要DT戦略を大量抑制 |
| daytrade_eurjpy: recent_emit | 18 | クールダウンが主な抑制源（過熱ではなくタイマー起因） |
| scalp_eur / scalp_5m: r2_shadow_demoted_cell | 15+10 | Shadow降格セルがScalpシグナルの25件を無効化 |

→ セッション全体の**実効シグナル発生率は著しく低い**。今朝の2件成立は"漏れ通った"案件。

---

## 4. 戦略調整判断

**→ NO（コード変更なし）**

根拠：
- N=2 は判断に必要な統計量を満たしていない（判断閾値 N≥30）
- 現在 DD=28.01%（DD防御 0.2x モード）。この局面での戦略変更は追加リスクを招く
- ブロック多発はシステムが意図通りリスクを制限している証拠であり、異常ではない
- Fidelity Cutoff 後の蓄積データが極めて少量（本日 N=2）。クリーンデータの蓄積優先

---

## 5. ロンドンセッション準備（UTC 07:00–12:00）

### レジーム変化予測

| ペア | 現レジーム | ATR%ile | ロンドン移行予測 |
|---|---|---|---|
| EUR_JPY | VOLATILE | 76% | ロンドン初動でボラ維持・拡大の可能性。SMA20 Slope=-0.00104（軟調） |
| EUR_USD | RANGING | 40% | 欧州指標次第でレンジ継続。Slope+0.00236で緩やかな上昇バイアス |
| GBP_JPY | VOLATILE | 72% | Volatile継続。Slope+0.00107で方向性あり |
| GBP_USD | RANGING | 40% | EUR_USD同様レンジ。Slope+0.00453は強め |
| USD_JPY | VOLATILE | 76% | Slope-0.00345（JPY強い）。ロンドン時間に円買い継続リスク |

### 推奨戦略配分

**基本方針: NO ACTION推奨**

**根拠（優先順）：**
1. **DD防御発動中（DD=28.01%, 0.2x モード）** — ロンドン高ボラ環境での新規拡張は方針に反する
2. **OANDA Live Rate = 2%（50件中1件のみ本番転送）** — shadow_tracking が20件抑制中。システム自体がシャドー学習フェーズにある
3. **Hedge_blockが連続60件（daytrade系）** — 既存ポジションとの相反シグナルが多発している構造的状況
4. **クリーンデータ不足** — Cutoff後有効N=2。昇格基準（N≥30）到達まで判断保留が原則

| 戦略 | 対応 |
|---|---|
| bb_rsi_reversion / USD_JPY | 継続監視。東京での2件成功はVolatileレジーム整合。ロンドンでも条件合致なら自然発動を待つ |
| daytrade系 | hedge_block継続抑制中。無理に介入しない |
| rnb_usdjpy | direction_filter 31件ブロック。レジーム(USD_JPY Slope=-0.00345)との整合性を静観 |
| scalp_eur / scalp_5m | r2_shadow_demoted_cell による抑制継続。Shadow学習完了まで待機 |

---

## 6. クオンツ見解

### 最重要シグナル

**① Shadow/Hedge blockによるシグナル枯渇の深刻度**

本日東京セッションで稼働中モードは12個あるが、実成立は **N=2（bb_rsi_reversion のみ）**。ブロック合計では hedge_block 60件・shadow_demoted 25件・direction_filter 31件が主因であり、システムは「動いているが打っていない」状態にある。これ自体はリスク管理として正常動作だが、**クリーンデータの蓄積速度が極端に遅く、昇格基準N=30到達の見通しが立たない**点は構造的問題である。

**② OANDA Live Rate 2% — デモ検証フェーズの長期化リスク**

50件中49件がSKIP（shadow_tracking 20件が主因）。本番資金（NAV 435,313 JPY）は待機状態を継続しており、Kelly Half移行（月利594%目標）への時間軸が不明確なまま伸長している。DD防御モードでの保守的運用は合理的だが、**デモでの正常蓄積が進まない限り昇格条件が満たされず、機会コストが積み上がるジレンマ**がある。現時点での推奨アクションは「静観・クリーンデータ蓄積を最優先」であり、ロンドンセッションへの積極介入は行わない。
