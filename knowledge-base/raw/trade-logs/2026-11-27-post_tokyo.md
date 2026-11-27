# Post-Tokyo Report: 2026-11-27

## Analyst Report
# Post-Tokyo Report — 2026-11-27 06:34 UTC (JST 15:34)

---

## 1. 東京セッション結果

**東京セッション: トレードなし**

| 項目 | 値 |
|---|---|
| セッション (UTC 00:00–06:00) トレード数 | 0 |
| PnL | ¥0 |
| WR | N/A |

全モードON（daytrade_xau / scalp_eurjpy / scalp_xau を除く）にもかかわらず、約定ゼロ。ブロック機構が全エントリーを捕捉した状態。

---

## 2. What Worked

**該当なし** — 約定ゼロのため評価不能。

---

## 3. What Didn't Work

**約定阻害の主因分析（Block Counts TOP 15より）**

| 主因カテゴリ | 代表例 | 累積件数 | 解釈 |
|---|---|---|---|
| `r2_shadow_demoted_cell` | scalp_5m_gbp(48)、scalp_5m_eur(41)、scalp(38)、scalp_eur(34) | **計200件超** | Shadow層でのR2降格判定が連鎖しており、Scalp系全体がデモ内部での自己ブロック状態 |
| `order_bar_dedup` | daytrade_eur(52)、daytrade_1h_audjpy(20)、daytrade_gbpjpy(13) | **計94件** | 同一バーへの重複注文生成 → Daytrade系がシグナル生成は活発だが全dedup捕捉 |
| `no_signal` | rnb_usdjpy(98) | **98件** | RnB戦略がシグナル条件を一件も満たさず。RANGING 34%ile(USD_JPY)との整合性あり |
| `score_gate` | daytrade_eurjpy(12) | 12件 | スコア閾値未達 |

**構造的失敗の焦点:** `r2_shadow_demoted_cell`が東京セッション中最大の抑制要因。Shadow降格セルが広範に展開しており、Scalp系は事実上機能停止に近い。

---

## 4. 戦略調整判断

**NO — パラメータ変更不要**

根拠:
- 東京セッションN=0、判断に足る統計的基盤なし（N<10は「データなし」扱い）
- DD防御 **10.01% / Lot Mult 0.2x / Defensive ON** が発動中。この状態での戦略変更はリスク管理の観点から禁忌
- `r2_shadow_demoted_cell`の多発はコード水準の問題であり、パラメータ調整で解決する性質ではない
- OANDA転送率 **0%（50/50がすべてSKIP）**：本番への影響ゼロ。現状の問題はデモ内部に閉じている

---

## 5. ロンドンセッション準備

### ATR/レジーム変化予測

| ペア | 現レジーム | ATR%ile | SMA20 Slope | ロンドン移行予測 |
|---|---|---|---|---|
| EUR_JPY | RANGING | 57% | −0.00241 | 下降傾向+中ATR → ロンドン初動で方向感が出る可能性あるが弱い |
| EUR_USD | RANGING | 66% | −0.00477 | 下降傾向やや強め → ショート方向バイアス継続可能性 |
| GBP_JPY | **VOLATILE** | 59% | −0.00247 | 唯一VOLATILE → Daytrade系に最もレジーム適合、ただしDD防御下では過大ロット禁止 |
| GBP_USD | RANGING | 66% | −0.00481 | EUR_USDと相関高く同方向リスク集中に注意 |
| USD_JPY | RANGING | 34% | +0.00234 | ATR最低位 → rnb_usdjpyのno_signal継続を予測 |

**全体所見:** SMA20 Slopeが4ペアで陰転（USD_JPYのみ+）。EUR/GBP系は下降バイアスが構造的に継続中。ロンドン開始でのボラティリティ拡大は GBP_JPY に限定的に期待できるが、RANGING支配が大勢。

### 推奨戦略配分

**NO ACTION推奨**

| 推奨根拠 | 詳細 |
|---|---|
| DD防御発動中 | 10.01% DD / 0.2x Lot。ロンドンでの積極的配分拡大は現在の防御方針に反する |
| OANDA転送率0% | Shadow層での検証が継続中。Liveへの昇格候補が存在しない（全50件SKIP） |
| r2_shadow_demoted_cell大量発生 | Scalp系がロンドンで約定可能な状態にない |
| agg_kelly=−0.223 | ケリー基準が負値。期待値計算上、追加ポジションを推奨しない水準 |
| GBP_JPY VOLATILE唯一の適合 | Daytrade_gbpjpyはorder_bar_dedup(13件)が発生済み。新規配分追加の根拠薄い |

システムを現状のまま稼働させ、ロンドンセッションのシグナル・ブロック動向を観察することが最適。

---

## 6. クオンツ見解

### 最重要シグナル

**DD防御 10.01% 到達 + OANDA転送0% の複合停滞が最大の構造リスク**

DDが10%の閾値に達してLot 0.2x防御が継続中であり、shadow降格連鎖（`r2_shadow_demoted_cell`計200件超）によってScalp系は事実上の機能停止状態にある。同時にagg_kelly=−0.223が示す通り、現在のポートフォリオEVは負方向に傾いており、**ロンドン以降でのエントリー積極化は統計的に支持されない**。

ミッションM3（+2〜3%/月複利）達成に向け、今必要なのは「何かを動かすこと」ではなく、**shadowシステムがN≥30・EV≥1.0の昇格基準を通過する戦略を産出するまで現状を維持すること**である。現時点で昇格候補ゼロ、降格検討対象の判断根拠となるN≥30データも今セッションでは蓄積なし。次の判断ポイントはNY/翌東京での蓄積量確認。

## SL replacement storm guard（決定的出力 — LLM 非経由、読み方: storm-guard-design-2026-09-22 §3）
### SL replacement storm guard
| enforce | max_tx/h | max_tx/day | deadband | evaluated | sent | failed | breaker_trips | detected (brk/idem/mono/dead/ser) | skipped (brk/idem/mono/dead/ser) |
|---|---|---|---|---|---|---|---|---|---|
| ON | 50 | 200 | 1.0p | 0 | 0 | 0 | 0 | 0/0/0/0/0 | 0/0/0/0/0 |

(guard 登録建玉なし)

