# Post-Tokyo Report: 2026-11-26

## Analyst Report
# Post-Tokyo Report — 2026-11-26 04:01 UTC（JST 13:01）

---

## 1. 東京セッション結果

**東京セッション: トレードなし**

| 項目 | 値 |
|---|---|
| セッション内トレード数 | 0 |
| PnL | ¥0 |
| WR | N/A |
| 稼働モード数 | 25/27（daytrade_xau・scalp_xau・scalp_eurjpy = OFF） |

東京セッション（UTC 00:00–06:00）中、全27モードにわたって約定ゼロ。ブロック件数は継続積算中。

---

## 2. What Worked

**該当なし**（約定ゼロのため評価不能）

---

## 3. What Didn't Work

**該当なし**（約定ゼロのため損失評価不能）

ただし、ブロック構造から**執行障壁**を確認：

| ブロック要因 | 戦略 | 件数 | 解釈 |
|---|---|---|---|
| `r2_shadow_demoted_cell` | scalp系4戦略 | 2,282件 | Shadowセル降格がscalp系を広範に封鎖 |
| `order_bar_dedup` | daytrade系4戦略 | 1,449件 | 重複シグナル排除が主なバルブ |
| `no_signal` | rnb_usdjpy | 2,721件 | エントリー条件未達（シグナルドライ） |
| `gbp_asia_flash_crash` | daytrade_gbpjpy | 297件 | GBP_JPY VOLATILE判定→アジア時間ガード発動 |

---

## 4. 戦略調整判断

**NO — パラメータ変更不要**

根拠：
- 東京セッションN=0。統計的判断の最低ラインN=10に遠く届かない
- DD防御中（DD 10.01% / Lot Mult 0.2x / Defensive ON）：現状はシステムが設計通り抑制動作中
- `r2_shadow_demoted_cell`の大量ブロックはShadow評価の正常機能であり、外部介入で解除すべきでない
- GBP_JPY VOLATILEレジーム下での`gbp_asia_flash_crash`ガード発動も設計通り

---

## 5. ロンドンセッション準備

### ATR/レジーム変化予測

| ペア | 現在レジーム | ATR%ile | ロンドン移行時の予測変化 |
|---|---|---|---|
| GBP_JPY | VOLATILE | 66% | ロンドン開始でボラ拡大継続の可能性高。フラッシュクラッシュガード継続有効 |
| GBP_USD | VOLATILE | 71% | 最高ATR帯。ロンドン勢参入でさらに伸びる可能性 |
| EUR_JPY | RANGING | 55% | スカルプ系には好環境だが、shadow降格が実行を制限 |
| EUR_USD | RANGING | 67% | RANGINGだがATR中高水準。ブレイク方向次第 |
| USD_JPY | RANGING | 45% | 最も穏やか。rnb_usdjpyのシグナル出現余地あり |

**SMA20 Slope全ペアがフラット〜微陰転**（最大 −0.00494、+0.00276）：強トレンドなし。RangingペアはDTよりscalpに有利な環境だが、Shadow降格ブロックが制約。

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| **Watch** | rnb_usdjpy | USD_JPY | ATR 45%・RANGING。唯一`no_signal`待ち状態で約定余地あり |
| **Watch** | daytrade_1h系 | EUR_JPY / EUR_USD | RANGINGレジームで1h足のデデュプが解消されればエントリー可能性 |
| **抑制継続** | scalp系全般 | 全般 | Shadow降格ブロック2,282件。ロンドン時間でも即座の改善は見込みにくい |
| **警戒** | daytrade_gbpjpy / daytrade_gbpusd | GBP系 | VOLATILEかつATR 66-71%。ガード発動継続を前提に過大期待しない |

**DD防御0.2x継続中** — ロンドン時間であっても全戦略のLot Multは0.2x。エントリーが発生しても損益インパクトは限定的。

**NO ACTION推奨（システム設定変更の観点で）**
- DD 10.01%でDefensive Mode継続中。手動介入よりも自然回復を待つフェーズ
- OANDA転送率0%（SKIP 50/50）：Shadowがまだ本番昇格要件を満たしていない状態が継続

---

## 6. クオンツ見解

### 最重要シグナル：**scalp系の全面Shadow封鎖 — 構造的執行停止が継続中**

東京セッション6時間でscalp系4戦略合計**2,282件**のブロックが`r2_shadow_demoted_cell`によって発生している。これはシグナルが出ているにもかかわらず執行層で全遮断されている状態であり、「戦略が機能していない」のではなく「Shadow評価がすでに降格判定を下した戦略が大量のシグナルを出し続けている」という構図である。

**構造的に読み取れること：**
- scalp系はシグナル生成は活発だが、Shadow層での実績評価が現行では昇格水準に達していない
- DD 10.01%でDefensive Mode継続かつOANDA転送率0%という二重制約下では、ロンドン時間にシグナル環境が改善しても実PnLへの貢献は最小限に留まる
- `rnb_usdjpy`の`no_signal` 2,721件は戦略設計通りの待機であり、異常ではない。USD_JPY RANGING 45%という現在の静穏環境でシグナルが出れば最も「クリーンな」エントリー候補となる

**推奨アクション（判断のみ）：**
1. scalp系のShadow昇格状況をN蓄積の観点で次回レポートで追跡 — 昇格再評価のタイミングを見極めること
2. DD回復（10%未満でDefensive解除）が最優先。ロンドンセッションでの約定増加よりもDD指標の推移を監視の軸に置くこと
3. GBP系のVOLATILEレジームが今後も継続するなら、`gbp_asia_flash_crash`ガード件数の増加は**正常防衛コスト**として許容する判断を維持すること

## SL replacement storm guard（決定的出力 — LLM 非経由、読み方: storm-guard-design-2026-09-22 §3）
### SL replacement storm guard
| enforce | max_tx/h | max_tx/day | deadband | evaluated | sent | failed | breaker_trips | detected (brk/idem/mono/dead/ser) | skipped (brk/idem/mono/dead/ser) |
|---|---|---|---|---|---|---|---|---|---|
| ON | 50 | 200 | 1.0p | 0 | 0 | 0 | 0 | 0/0/0/0/0 | 0/0/0/0/0 |

(guard 登録建玉なし)

