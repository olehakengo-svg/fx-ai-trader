# Post-Tokyo Report: 2026-10-09

## Analyst Report
# Post-Tokyo Report — 2026-10-09 04:26 UTC（JST 13:26）

---

## 1. 東京セッション結果

**東京セッション: トレードなし**

| 項目 | 値 |
|---|---|
| PnL | ¥0 |
| トレード数 | 0 |
| WR | N/A |

UTC 00:00–06:00 の実行トレードはゼロ。全モード ON であるにもかかわらず、シグナル未発生またはブロックにより約定に至らなかった。

---

## 2. What Worked

**該当なし**（トレードゼロのため）

---

## 3. What Didn't Work

**該当なし**（ただし、以下のブロック構造が事実上「執行抑制」として機能）

| ブロック主因 | 件数 | 影響戦略 |
|---|---|---|
| `r2_shadow_demoted_cell` | 3,188件（scalp系合計） | scalp / scalp_eur / scalp_5m / scalp_5m_gbp / scalp_5m_eur |
| `order_bar_dedup` | 2,218件 | daytrade_eurjpy / eur / gbpjpy / gbpusd / eurgbp / daytrade |
| `rnb_usdjpy:no_signal` | 2,293件 | rnb_usdjpy |
| `hedge_block` + `USD exposure超過` | 337件 | daytrade_gbpusd |

**構造的観察**: scalp系は `r2_shadow_demoted_cell` が支配的ブロック要因（セル降格によりシグナル生成自体が無効化）。daytrade系は `order_bar_dedup` が主因（同バー内重複排除）。執行ゼロは「システムが意図的に止めている」状態であり、誤作動ではない。

---

## 4. 戦略調整判断

**NO — パラメータ変更不要**

- ブロック要因はすべてルール通りの正常動作（降格セル・重複排除・エクスポージャー制限）
- トレードゼロはシグナル環境の問題であり、パラメータ調整で解決する性質ではない
- `daytrade_xau`・`scalp_xau`・`scalp_eurjpy` はOFF継続が適切（現状維持）
- DD防御 0.2x モード中につき、パラメータ感度を上げる方向の変更は禁止

---

## 5. ロンドンセッション準備（UTC 07:00–）

### ATR / レジーム変化予測

| ペア | 現レジーム | ATR%ile | ロンドン移行後の予測 |
|---|---|---|---|
| EUR_USD | VOLATILE | 78% | ボラ継続。方向性バイアスなし（SMA Slope -0.00861、下押し継続リスク） |
| GBP_USD | TRENDING_DOWN | 69% | トレンド継続可能性あり。Slope -0.00553 で下降バイアス維持 |
| GBP_JPY | RANGING | 71% | レンジだがATR高め。ブレイクアウト型には注意 |
| EUR_JPY | RANGING | 71% | Slope -0.00304 で弱下降。scalp系には不利な収束環境 |
| USD_JPY | TRENDING_UP | 57% | 上昇トレンドだがATR中位。rnb系の唯一の候補だが `no_signal` 多発中 |

### 推奨戦略配分

| 戦略 | 推奨 | 根拠 |
|---|---|---|
| daytrade_gbpusd | 待機優先 | USD net exposure 既に上限超過履歴あり（161件ブロック）。ロンドン早期の急騰に注意 |
| daytrade_1h系 | 条件付き待機 | `r2_shadow_demoted_cell` ブロックが解消されない限り執行不可。daytrade_1h_usdchf 260件ブロック |
| scalp系全般 | **NO ACTION** | 全scalp系がshadow demoted cellで封鎖中。ロンドン移行でATR上昇しても構造的に到達不可 |
| rnb_usdjpy | 待機 | no_signal 2,293件。USD_JPY TRENDING_UPだが、rnbシグナル条件を満たす局面未到来 |

**ロンドンセッション推奨: NO ACTION（系統的待機）**

> 根拠: ①scalp系は降格セルによる構造的ブロックが解消されていない ②daytrade_gbpusdはUSDエクスポージャー上限に近接 ③EUR_USD VOLATILE + GBP_USD TRENDING_DOWN はDD防御0.2xモードと相性が悪い ④OANDA転送率4%（50件中2件のみ）が示す通り、本番執行の閾値は非常に厳格に設定されている

---

## 6. クオンツ見解

### 最重要シグナル: **scalp系の構造的停止とOANDA転送率4%の乖離**

`r2_shadow_demoted_cell` ブロックが scalp 4系統合計で **3,188件** に達している。これはシグナルが出ても執行に至らない「見えない無効化」が東京セッション全体を通じて作動していることを意味する。同時に、OANDA転送率は **4%（50件中2件）** と極端に低く、デモ側でさえ約定しているトレードのほぼ全量がOANDA本番に届いていない。

**構造的観察（良い面）**: システムは設計通りに動作している。DD防御・降格ルール・エクスポージャー制限がすべて正常に機能しており、NAV ¥273,921は安定圏（floor ¥262,000 まで約¥11,921の余裕）。

**構造的観察（懸念面）**: ただし、scalp系の降格セル支配が長期化すると「システムは稼働しているがPnL貢献がゼロ」という状態が固定化するリスクがある。block_countsの蓄積がこの数週間で解消されていないのであれば、当該戦略の有効稼働期間の再評価が必要。

**推奨アクション**: 今セッションは執行を強制する判断は不要。ロンドン・NY両セッション通じて `r2_shadow_demoted_cell` のブロック率が高止まりする場合、scalp系の昇格候補セルへのN蓄積が実質的に停止していないかを次回レポートで確認すること。Sentinel N=30到達の進捗が本質的なKPIである。
