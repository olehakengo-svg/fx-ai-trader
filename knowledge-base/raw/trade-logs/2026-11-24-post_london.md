# Post-London Report: 2026-11-24

## Analyst Report
# Post-London Report — 2026-11-24 17:18 UTC (JST 02:18)

---

## 1. ロンドンセッション結果

| 指標 | 値 |
|---|---|
| セッション内トレード数 | **0** |
| PnL (pips) | **0.0** |
| 勝率 (WR) | **N/A** |

ロンドンセッション（UTC 07:00–16:00）は**完全不活性**。エントリーゼロ。

---

## 2. What Worked

**該当なし** — トレードゼロのため評価対象なし。

---

## 3. What Didn't Work

**該当なし** — ただし、以下がエントリー抑制の主因として読み取れる：

| 抑制要因 | 規模感 | 影響モード |
|---|---|---|
| `r2_shadow_demoted_cell` | scalp_eur: 348、scalp: 346、scalp_5m: 143 | Scalp系全般 |
| `order_bar_dedup` | daytrade_eurgbp: 238、daytrade: 236、daytrade_gbpusd: 160 | DT系全般 |
| `rnb_usdjpy:no_signal` | 702 | rnb_usdjpy |

Scalp系は**セル降格**により構造的にブロック。DT系は**重複除去フィルター**がシグナル集中を吸収。いずれもセッション中のエントリーを実質的にゼロに抑えた。

---

## 4. 東京との比較

| 指標 | 東京セッション | ロンドンセッション |
|---|---|---|
| トレード数 | 1 | 0 |
| PnL (pips) | −18.2 | 0.0 |
| WR | 0.0% | N/A |
| 主要レジーム | — | EUR_USD: TRENDING_DOWN / GBP_USD: TRENDING_DOWN / GBP_JPY: VOLATILE |

東京で **carry_dip (#1347157) が −18.2p** のSLヒットを記録したが、ロンドンはゼロエントリー。損失拡大は防いだが、TRENDING_DOWNが継続するEUR/GBP系でのDT機会を`order_bar_dedup`・`r2_shadow_demoted_cell`が遮断した格好。**パッシブ防衛の一日**と位置づけられる。

---

## 5. NYセッション準備

### レジーム変化予測（ロンドン→NY移行）

| ペア | 現在レジーム | NY移行後の予測 |
|---|---|---|
| EUR_USD | TRENDING_DOWN (ATR%ile 69%) | ドル関連指標次第でトレンド継続か反発。高ATR警戒 |
| GBP_USD | TRENDING_DOWN (ATR%ile 71%) | 同上。ボラティリティ高止まりの可能性 |
| GBP_JPY | VOLATILE (ATR%ile 64%) | NY序盤にスパイク発生リスク大 |
| EUR_JPY | RANGING (ATR%ile 53%) | レンジ継続の可能性。Scalp系に理論上有利だが降格中 |
| USD_JPY | RANGING (ATR%ile 45%) | 低ATR。carry_dipには慎重材料 |

### 推奨戦略配分

**NO ACTION推奨（主要戦略）**

根拠：

1. **DD防御 10.01% / Lot Mult 0.2x** — Defensive Mode継続中。リスクテイクの余地は構造的に限定されている
2. **OANDA転送率 0%（SENT 0/50）** — 本番へのライブフィル実績がゼロ。shadow_trackingによるブロックが支配的であり、現状は**完全デモ運用**
3. **carry_dip N=35 / EV +5.34** — 唯一の有効戦略だが、今日の−18.2pヒットを含む**直近パフォーマンスは確認要**。USD_JPYがRANGING (ATR%ile 45%)でシグナル発生が低調
4. **Scalp系はr2_shadow_demoted_cellにより構造的封鎖** — NYで突発的な高ボラが来てもエントリー不可

**例外的注視点：** rnb_usdjpy が `no_signal` 702件と大量ブロックしているが、USD_JPYがRANGINGであること自体がこの戦略の設計想定外レジームである可能性がある。

---

## 6. 本日暫定結果

| 指標 | 値 |
|---|---|
| 本日累計トレード数 (N) | **1** |
| 本日累計 PnL (pips) | **−18.2** |
| 本日 WR | **0.0%** |
| 参照元 | 本日累計（参考）テーブル |

---

## 7. クオンツ見解

### 最重要シグナル：**ゼロエントリー常態化とDD防御の複合ロック**

ロンドンセッション不活性の直接原因は `r2_shadow_demoted_cell`（Scalp系を構造的封鎖）と `order_bar_dedup`（DT系の重複除去）の2大ブロックであるが、**根底にあるのはDD 10.01% / 0.2x Defensive Modeという資本制約**だ。たとえシグナルが発生してもLot Multが0.2xに抑圧されており、OANDA転送率もゼロ（全50件がSKIP）という状態は、**システムが実質的に「監視モード」に移行していることを意味する**。

現在有効な戦略は carry_dip（N=35、EV +5.34）のみだが、USD_JPY RANGINGレジーム（ATR%ile 45%）はこの戦略のシグナル発生を抑制する。**NYセッションで無理にポジションを取りにいく理由はなく、DD回復を最優先する現在の受動的姿勢は合理的**と判断する。次の判断ポイントはDD%が防御閾値を下回るタイミングまたはcarry_dip追加エントリーによるN蓄積の進展。

## SL replacement storm guard（決定的出力 — LLM 非経由、読み方: storm-guard-design-2026-09-22 §3）
### SL replacement storm guard
| enforce | max_tx/h | max_tx/day | deadband | evaluated | sent | failed | breaker_trips | detected (brk/idem/mono/dead/ser) | skipped (brk/idem/mono/dead/ser) |
|---|---|---|---|---|---|---|---|---|---|
| ON | 50 | 200 | 1.0p | 0 | 0 | 0 | 0 | 0/0/0/0/0 | 0/0/0/0/0 |

(guard 登録建玉なし)

