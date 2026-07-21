# Post-Tokyo Report: 2026-07-21

## Analyst Report
# Post-Tokyo Session Report — 2026-07-21 08:36 UTC

---

## 1. 東京セッション結果

**東京セッション: トレードなし**

| 指標 | 値 |
|---|---|
| PnL | 0.0p |
| トレード数 | 0 |
| WR | N/A |
| 稼働モード数 | 24/26（daytrade_xau・scalp_xau・scalp_eurjpy OFF） |

UTC 00:00-06:00（JST 09:00-15:00）において、全26モードのうち稼働中24モードが0件エントリー。**完全不稼働セッション**。

---

## 2. What Worked

**該当なし** — 東京セッション中にクローズされたトレードは存在しない。

---

## 3. What Didn't Work

**該当なし** — 損失トレードも存在しない。

ただし、ブロックログから実質的な「失注」として注目すべき事象を記録：

| ブロック事由 | 件数 | 主な影響モード |
|---|---|---|
| hedge_block | 18件 | daytrade / scalp_5m |
| direction_filter | 8件 | rnb_usdjpy |
| order_bar_dedup | 11件 | daytrade_gbpusd / daytrade_eur / daytrade_1h |
| r2_shadow_demoted_cell | 11件 | scalp / scalp_eur / scalp_5m_eur / daytrade_gbpjpy |
| regime_range_dt_tf | 1件 | daytrade_gbpusd |

**実質的な主因**: hedge_block（daytrade+scalp_5m合計18件）が最多。次いでorder_bar_dedup（11件）、shadow demotionによるシグナル棄却（11件）が続く。エントリー候補は複数発生していたが、**フィルター群が全件遮断**した構図。

---

## 4. 戦略調整判断

**NO — パラメータ変更不要**

根拠：
- 東京セッションN=0は「フィルターが機能した結果」であり、「見逃し損失」の証拠がない
- hedge_blockはポジション方向集中リスク回避の正常動作
- order_bar_dedupはエントリー重複防止の正常動作
- r2_shadow_demoted_cellはシグナル品質管理の正常動作
- **DD=100.01%のDD防御0.2x発動中** — この水準でのパラメータ緩和は禁止

---

## 5. ロンドンセッション準備

### ATR/レジーム変化予測

現在のレジーム状況を踏まえた移行予測：

| ペア | 現在レジーム | ATR%ile | ロンドン開始時の予測変化 |
|---|---|---|---|
| GBP_JPY | TRENDING_UP | 60% | **ボラ拡大警戒** — 既に高ATR。ロンドン勢参入でさらに拡大の可能性 |
| GBP_USD | VOLATILE | 59% | **継続ボラ高** — VOLATILEレジームがロンドンで増幅されやすい |
| USD_JPY | RANGING | 71% | ATR高水準なのにRANGING — レジーム分類とATRの乖離に注意 |
| EUR_JPY | RANGING | 43% | 中位ATR、ロンドン開始でトレンド発現の可能性 |
| EUR_USD | RANGING | 43% | 中位ATR、方向感弱め — rnb候補 |

### 推奨戦略配分

**⚠️ NO ACTION推奨（積極エントリーは控え）**

**根拠1 — DD防御モード継続**：NAV=279,009円、DD=100.01%バリア突破後のheld状態。防御0.2xスケール下では期待値優位セルを狙う意味が薄れる。

**根拠2 — GBP系のVOLATILE/高ATR状況**：GBP_USD（VOLATILE, 59%ile）・GBP_JPY（TRENDING_UP, 60%ile）はともにspread_guard抵触リスクが高い。スキャルプ戦略（閾値30%）はATR%ile超過でブロックされる可能性が高く、エントリーが発生しても摩擦コストが増大する。

**根拠3 — シグナル品質**：shadow demoted cell（11件）がこの時間帯に集中していることは、現在のシグナルセル品質が低位にあることを示唆。

**限定的に有効な可能性がある戦略（ウォッチのみ）**：
- `rnb_usdjpy` — EUR_USDのRANGING 43%ile環境はrange-boundアプローチに適合。ただしdirection_filter8件の抑制があるため、過度な期待は禁物。
- `daytrade_1h_eur` — EUR_USD RANGING＋低ATRでdaytrade_1hの条件に近い。regime_range_dt_tfが解除されれば候補になる。

---

## 6. クオンツ見解

### 🔴 最重要シグナル：「エントリー候補は存在するがフィルター群が完全遮断」という構図の常態化

東京セッションN=0の表面上の静けさの背後に、**計49件のブロックイベント**が記録されている。hedge_block18件・order_bar_dedup 11件・shadow demotion 11件が三重に重なり、**シグナル→エントリーへの転換率はゼロ**。

この構図が問題なのは、「フィルターが正しく機能している」のか「過剰遮断によりEVプラスのシグナルまで棄却している」のかが、現状のデータでは判別不能な点である。

**OANDA転送率0%（SENT=0/50）・shadow_trackingによるskip 20件**も合わせると、システム全体の実効稼働率は形式上「24モードON」だが実質はほぼゼロに近い。DD=100.01%の防御モードがこの状態を合理化している間は問題が顕在化しないが、**DDが回復してもエントリー転換率が改善しなければ月次目標M1（符号転換）すら達成できない**。

現時点で推奨するアクションは**静観（NO ACTION）**。ただし、ロンドン・ニューヨークセッションでもブロック件数が同水準で推移し続ける場合、「エントリー機会の構造的消失」として別途診断を要する。
