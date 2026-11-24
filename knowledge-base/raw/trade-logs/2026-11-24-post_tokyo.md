# Post-Tokyo Report: 2026-11-24

## Analyst Report
# Post-Tokyo Report — 2026-11-24 05:46 UTC (JST 14:46)

---

## 1. 東京セッション結果

| 項目 | 値 |
|---|---|
| セッション (UTC 00:00-06:00) | **N=1** |
| PnL | **-18.2 pips** |
| WR | **0.0%** (1/1 LOSS) |
| 有効判定 | N<5 → **参考値**（単独統計として判断不可） |

> 東京セッション中の約定は `usdjpy_carry_dip_accumulator` USD_JPY BUY 1件のみ。SL_HIT、スプレッド0.8p（guard閾値内）。

---

## 2. What Worked

**なし。** 東京セッション内に正PnLトレードは存在しない。

---

## 3. What Didn't Work

| 戦略 | ペア | PnL | 失敗要因 |
|---|---|---|---|
| `usdjpy_carry_dip_accumulator` | USD_JPY | **-18.2p** | USD_JPY はRANGING(ATR%ile 45%)・SMA20 Slope +0.00269（上昇バイアス微弱）の局面でのBUY積み増し試みが逆行し、SL到達。 |

**補足:** USD_JPY ATR%ile 45%はレンジ中位圏。carry_dip戦略の「押し目買い」ロジックに対し、東京時間は方向性が出にくい環境であった。

---

## 4. 戦略調整判断

**NO**

**根拠:**
- N=1は統計的に「データなし」（閾値N≥10）。1件のSL_HITから調整根拠を導出できない。
- `usdjpy_carry_dip_accumulator`のCutoff後累積N、EV提供なし → 判断に必要なサンプルが蓄積されていない。
- DD防御が**0.2x (10.01% DD、Defensive ON)** で発動中。この状態でのパラメータ変更はノイズに対する反応であり、ミッション（M3: +2〜3%/月複利）に逆行する。

---

## 5. ロンドンセッション準備

### ATR/レジーム変化予測

| ペア | 現レジーム | 変化予測 |
|---|---|---|
| EUR_USD | TRENDING_DOWN (ATR%ile 69%) | ロンドン入りでボラティリティ拡大、トレンド継続または加速の可能性 |
| GBP_USD | TRENDING_DOWN (ATR%ile 71%) | 同上。GBP系はロンドン時間に流動性が最も高く、スプレッド縮小 |
| GBP_JPY | VOLATILE (ATR%ile 64%) | ロンドン-東京オーバーラップ消滅後にボラ継続。フラッシュ方向が出やすい |
| EUR_JPY | RANGING (ATR%ile 53%) | レンジ継続の可能性高い。ブレイクがあれば乗れる |
| USD_JPY | RANGING (ATR%ile 45%) | 東京値幅が狭く、ロンドン移行で多少拡大するが低ボラ継続を想定 |

### 推奨戦略配分

**NO ACTION推奨（現行稼働継続のみ）**

**根拠:**
1. **DD防御 10.01% / Lot 0.2x 継続中** — DD閾値を超過しており、積極的なポジション追加は口座保全上不適切。
2. **OANDA転送率 4%（SENT 2/50）** — スコアゲート・shadow_tracking・auto_demotedによるブロックが支配的。ロンドン向けに戦略を「追加」できる状態ではない。
3. **block_counts主因**:
   - `rnb_usdjpy:no_signal` 8,092件 — シグナル枯渇が顕著
   - `scalp*:r2_shadow_demoted_cell` 累計9,844件 — Scalp系がshadowトラッキング段階で大量ブロック。ロンドン時間でもこの構造は変わらない
   - `daytrade*:order_bar_dedup` 累計6,197件 — dedup作動はレジームに対するオーバーシグナルの証拠
4. **GBP系戦略**: `daytrade_eurgbp:gbp_asia_flash_crash` 342件のブロックは東京内。ロンドンではGBP_JPY VOLATILE + GBP_USD TRENDING_DOWNで流動性が出るが、フラッシュガードの作動頻度がむしろ増える可能性がある。
5. OANDA bridge側 `shadow_tracking(promo_block:pair_demoted/auto_demoted)` が4件確認 — 自動降格ペアへの発注は既にシステム側でブロック済み。

> **既存稼働モード（DT/Scalp系 ON）をそのまま維持し、ロンドン時間のシグナル自然発生を待つのが最適。**

---

## 6. クオンツ見解

### 最重要シグナル（1点）

**DD防御継続 × OANDA転送率4%：実質的なシステム停止状態**

現在、全27モード稼働中であるにもかかわらず、本日累計N=1・OANDA LIVE SENT=2件（うち本日1件）という状況は、**システムがアクティブに取引できる環境にない**ことを示す。DD 10.01%で0.2xロット制約、Scalp系9,000件超のshadow_demoteブロック、daytrade系6,000件超のdedup作動という3重の制約が同時に発動している。

ロンドンセッションでEUR/GBP系のボラが拡大しても、**signal→execution→OANDAの経路のどこかで詰まる構造は変わらない**。N=1の東京結果は「戦略の失敗」ではなく「システムが機能できていない環境」として読むべきである。

**推奨アクション（判断のみ）:**
- **DD回復を最優先** — NAV ¥323,346（ピーク¥359,288比 -10.01%）が10%台前半にある限り、積極的な昇格・新規配分判断は凍結。DDが8%台以下に回復するまで現状維持が合理的。
- **Scalp系のshadow_demoteブロック件数を監視継続** — `r2_shadow_demoted_cell`が東京セッションだけで累計9,844件は異常に高い。これはロンドンでも継続するため、Scalp系のEV蓄積はほぼ進まない（N≥30到達が遠のく）。
- **carry_dip_accumulatorのN蓄積確認** — Cutoff後の累積N不明。次回レポートでN数を必ず取得し、N≥10に達しているかを確認すること。

## SL replacement storm guard（決定的出力 — LLM 非経由、読み方: storm-guard-design-2026-09-22 §3）
### SL replacement storm guard
| enforce | max_tx/h | max_tx/day | deadband | evaluated | sent | failed | breaker_trips | detected (brk/idem/mono/dead/ser) | skipped (brk/idem/mono/dead/ser) |
|---|---|---|---|---|---|---|---|---|---|
| ON | 50 | 200 | 1.0p | 0 | 0 | 0 | 0 | 0/0/0/0/0 | 0/0/0/0/0 |

(guard 登録建玉なし)

