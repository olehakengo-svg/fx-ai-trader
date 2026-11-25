# Post-London Report: 2026-11-25

## Analyst Report
# Post-London Report — 2026-11-25 16:58 UTC

---

## 1. ロンドンセッション結果

| 項目 | 値 |
|---|---|
| セッション内トレード数 | **0** |
| PnL | **¥0** |
| WR | **N/A** |
| 対象時間帯 | UTC 07:00–16:00 |

ロンドンセッション全体を通じてトレードゼロ。システムは全モード稼働中（daytrade_xau / scalp_xau / scalp_eurjpy はOFF）だが、一件も約定なし。

---

## 2. What Worked

**該当なし**（トレード0件のため評価対象なし）

---

## 3. What Didn't Work

**該当なし**（約定失敗ではなく、シグナル自体が不発）

ただし、ブロック構造からロンドン時間帯の「不発要因」を推定できる：

| ブロック要因 | 件数 | 影響モード |
|---|---|---|
| `r2_shadow_demoted_cell` | 2,346件（scalp系4モード合計） | scalp全般 |
| `order_bar_dedup` | 1,234件（daytrade系） | daytrade全般 |
| `gbp_asia_flash_crash` | 190件 | daytrade_gbpjpy |
| `score_gate` | 109件 | daytrade |
| `rnb_usdjpy:no_signal` | 1,519件 | rnb_usdjpy |

**主因**: scalp系は `r2_shadow_demoted_cell` によるデモ側降格セルからの遮断が支配的。daytrade系は重複バー排除（`order_bar_dedup`）が主因。シグナルは存在するが、品質フィルタが全て通過できていない状態。

---

## 4. 東京との比較

| 項目 | 東京セッション | ロンドンセッション |
|---|---|---|
| トレード数 | 0 | 0 |
| PnL | ¥0 | ¥0 |
| WR | N/A | N/A |
| レジーム変化 | — | — |

東京・ロンドン両セッションとも約定ゼロ。セッション間での質的差異は観測できないが、ロンドン時間帯に活発化する GBP/EUR ペアでも約定が発生しなかった点は注目に値する。現在のレジーム状況（GBP_JPY・GBP_USD = **VOLATILE**、EUR_USD = **TRENDING_DOWN**、ATR%ile 55–69%）はスプレッドガードが厳しく機能する条件であり、ロンドン時間のボラティリティ拡大が逆にスプレッド過大として排除された可能性が高い。

---

## 5. NYセッション準備

### ATR/レジーム変化予測

| ペア | 現状レジーム | ATR%ile | NYへの見通し |
|---|---|---|---|
| EUR_USD | TRENDING_DOWN | 67% | USD指標次第でトレンド継続。scalp不利、DT有利環境 |
| GBP_USD | VOLATILE | 69% | ボラ継続。スプレッドガード超えリスク高 |
| GBP_JPY | VOLATILE | 67% | 同上。`gbp_asia_flash_crash`ガードもNYで残存 |
| USD_JPY | RANGING | 43% | ATR低位。rnb戦略の条件だが`no_signal`で全ブロック中 |
| EUR_JPY | RANGING | 55% | 中程度。シグナル発生余地あり |

### 推奨戦略配分

| 優先度 | 戦略 | ペア | 根拠 |
|---|---|---|---|
| 注視 | `daytrade_eur` / `daytrade_1h_eur` | EUR_USD | TRENDING_DOWN × ATR67% → DTシグナル発生条件に最も近い |
| 注視 | `daytrade_eurjpy` | EUR_JPY | RANGING中位、`order_bar_dedup`解消後にシグナル余地 |
| 警戒 | `daytrade_gbpjpy` / `daytrade_gbpusd` | GBP系 | VOLATILE × `gbp_asia_flash_crash` 190件は継続的阻害要因 |
| **NO ACTION推奨** | scalp系全般 | 全ペア | `r2_shadow_demoted_cell`が2,346件累積 — 降格セル状態が解消されるまでスキャルプ約定は構造的に困難 |
| **NO ACTION推奨** | `rnb_usdjpy` | USD_JPY | 1,519件 `no_signal` — RANGING環境でもシグナル条件未充足が継続 |

> **総合**: NYセッションでの期待値は低い。`r2_shadow_demoted_cell` によるscalp系の完全封鎖が継続する限り、約定件数は限定的。daytrade系のみ様子見。

---

## 6. 本日暫定結果

| 項目 | 値 |
|---|---|
| 東京+ロンドン累計トレード数 | **0** |
| 累計PnL | **¥0** |
| DD状況 | **10.01% / defensive mode 0.2x稼働中** |
| 実口座 NAV | **¥271,770.41** |
| EQ Peak | **¥359,288 → Current ¥323,346**（DD ¥35,942） |

---

## 7. クオンツ見解

**最重要シグナル**: **システムが「稼働しているが機能していない」状態に入っている**

本日の東京・ロンドン両セッションでトレードゼロ。ブロック件数は累計5,000件超と高水準であり、とりわけ `r2_shadow_demoted_cell`（scalp系2,346件）と `order_bar_dedup`（daytrade系1,234件）が「シグナルが発生してもフィルタで全量排除」という構造を形成している。

DD 10.01%で defensive mode（0.2x）が作動中。これは意図通りの防御として評価できるが、**「防御により約定ゼロ」ではなく「フィルタにより約定ゼロ」**である点が重要な区別だ。lot multiplier 0.2xはリスク低減に機能しているが、EV正の案件すら到達できていない可能性がある。

OANDA転送率は50件中0件（0%）——全トレードが `shadow_tracking` ブロック（shadow_tracking 16件 + pair_demoted 3件 + shadow_emit_no_lot 1件）で本番に到達できていない。N蓄積も進まないため、昇格判断に必要なN≥30の達成が遠のいている。**NYセッションも同様の構造が継続すると予測され、本日の累計約定ゼロで終わる可能性が高い。フィルタ群の状態を確認し、shadow_demoted_cellとpair_demotedの解消条件を把握することが最優先課題。**

## SL replacement storm guard（決定的出力 — LLM 非経由、読み方: storm-guard-design-2026-09-22 §3）
### SL replacement storm guard
| enforce | max_tx/h | max_tx/day | deadband | evaluated | sent | failed | breaker_trips | detected (brk/idem/mono/dead/ser) | skipped (brk/idem/mono/dead/ser) |
|---|---|---|---|---|---|---|---|---|---|
| ON | 50 | 200 | 1.0p | 0 | 0 | 0 | 0 | 0/0/0/0/0 | 0/0/0/0/0 |

(guard 登録建玉なし)

