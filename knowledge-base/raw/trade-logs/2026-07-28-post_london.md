# Post-London Report: 2026-07-28

## Analyst Report
# ロンドンセッション総括レポート
**2026-07-28 17:19 UTC（JST 02:19）**

---

## 1. ロンドンセッション結果

| 項目 | 値 |
|---|---|
| セッション対象時間 | UTC 07:00–16:00 |
| トレード数 | **0** |
| PnL | **0.0 pips** |
| 勝率（WR） | **N/A** |

ロンドンセッション中、全モードが稼働状態（daytrade_xau・scalp_eurjpy・scalp_xau除く）にもかかわらず、**約定ゼロ**。

---

## 2. What Worked

**該当なし**（トレード発生ゼロのため評価不可）

---

## 3. What Didn't Work

**直接的な失敗トレードは存在しないが**、以下のブロック構造がロンドン時間帯の執行機会を実質的に封鎖したと推定される：

| ブロック要因 | 件数 | 影響戦略 |
|---|---|---|
| `rnb_usdjpy:direction_filter` | 340 | rnb_usdjpy |
| `daytrade:hedge_block` | 190 | daytrade |
| `daytrade_eurgbp:order_bar_dedup` | 164 | daytrade_eurgbp |
| `daytrade_eur:hedge_block` | 128 | daytrade_eur |
| `daytrade_gbpusd:order_bar_dedup` | 128 | daytrade_gbpusd |
| `scalp:r2_shadow_demoted_cell` | 98 | scalp |

**主因分析：**
- `direction_filter`（340件）が最大ブロック源。`rnb_usdjpy`はUSD_JPY=RANGING（ATR%ile 67%）にもかかわらず方向性フィルターが全シグナルを棄却 — **レンジ環境でトレンドフォロー系フィルターが機能不全に陥っている可能性**。
- `hedge_block`（daytrade系合計 432件超）は同時間帯のオープンポジション保護として作動。ただし本日はOpen Trades=0のため、**ポジション解消後の再エントリー機会も逸している**可能性がある。
- `r2_shadow_demoted_cell`（scalp系合計 230件）はシャドウ降格セルが依然として大量のシグナルをフィルター中。

---

## 4. 東京セッションとの比較

| 比較項目 | 東京セッション | ロンドンセッション |
|---|---|---|
| トレード数 | 0 | 0 |
| PnL | 0 | 0 |
| WR | N/A | N/A |
| 主ブロック源 | 不明（データなし） | direction_filter / hedge_block |
| レジーム環境 | — | EUR_JPY RANGING / GBP_JPY TRENDING_UP |

両セッションともトレードゼロ。レジーム面では**GBP_JPY（TRENDING_UP、ATR%ile 55%）がロンドン時間帯に最も有利な環境**であったが、`daytrade_gbpjpy`でのブロック状況が不明確であり機会捕捉できなかった。

---

## 5. NYセッション準備

### レジーム・ATR変化予測

| ペア | 現状 | NY移行予測 |
|---|---|---|
| GBP_JPY | TRENDING_UP（55%） | NY初動でトレンド継続の可能性あり、ただし反転リスク増 |
| USD_JPY | RANGING（67%） | 米経済指標次第でボラ上昇 → ATR%ile上昇の可能性 |
| GBP_USD | RANGING（62%） | 方向性不明確、レンジ継続 |
| EUR_USD | RANGING（36%） | 低ボラ継続の可能性高い |
| EUR_JPY | RANGING（33%） | 最低ボラ — scalp不向き |

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| 高 | `daytrade_gbpjpy` | GBP_JPY | 唯一のTRENDING_UP、ATR中程度 |
| 中 | `daytrade_gbpusd` | GBP_USD | RANGING高ボラ、order_bar_dedupが緩和されれば機会あり |
| 観察 | `daytrade_1h_usdchf` | USD_CHF | NY時間のUSD主導ムーブに備えた待機 |
| 低 | `rnb_usdjpy` | USD_JPY | direction_filter 340件 — 根本的なレジーム不整合。**シグナル枯渇状態** |

### ❗ NO ACTION推奨対象

- `rnb_usdjpy`：direction_filter 340件が示す通り、**現行レンジ環境では構造的にシグナル枯渇**。NYでも米指標でトレンド化しない限り状況不変。
- `scalp_eur` / `scalp` / `scalp_5m_gbp`：r2_shadow_demoted_cellが大量ブロック継続中。シャドウ昇格待ちの状態。

---

## 6. 本日暫定結果

| 項目 | 値 |
|---|---|
| 東京+ロンドン累計トレード数 | **0** |
| 東京+ロンドン累計PnL | **0.0 pips** |
| OANDA NAV | 279,009.31 |
| OANDA Live Rate | **0%**（50件全SKIP） |
| 稼働モード数 | 24/27（3モードOFF） |

---

## 7. クオンツ見解

### 最重要シグナル：**「システム全体が約定ゼロを2セッション連続で記録」**

ブロック総件数は1,900件超に達しており、シグナルは生成されているが**執行に至る経路が全面的に封鎖されている**。特に`direction_filter`（340件）が示す`rnb_usdjpy`の機能不全と、`r2_shadow_demoted_cell`（230件超）によるscalpセル全降格は、**シグナル生成エンジンと執行フィルターの間で構造的な不整合が固定化している**ことを示す。

OANDA転送率0%（50件全SKIP）はOANDA連携ではなく**上流での約定ゼロに起因**。NAV=279,009円でシステムは生存しているが、**資本は一切働いていない状態が本日全日にわたり継続中**。

NYセッションでGBP_JPYのトレンド継続が約定トリガーとなるか否かが、本日唯一の実質的な注目点。ただし現行のhedge_block・dedup連打を見る限り、**NYでも約定ゼロの確率が高い**と判断する。
