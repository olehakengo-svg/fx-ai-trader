# VWAP Mean Reversion — Live 実測深部分析

**Generated**: 2026-04-22
**Scope**: `vwap_mean_reversion` 全 trade (LIVE + Shadow)
**Trigger**: user challenge "リアルタイム見ていると強そう"

---

## 1. 戦略仕様 (code 実体)

- Entry: price < VWAP − 2σ → BUY / price > VWAP + 2σ → SELL
- Pair α boost: EUR_JPY/GBP_JPY +5, USD_JPY +3, EUR_USD/GBP_USD 0, EUR_GBP −5
- HTF hard block: `htf_agreement=bull` の SELL / `bear` の BUY を拒否
- Data source: Massive API VWAP (Polygon 互換, volume-weighted)

## 2. Live 実測 (N=16 W/L, post-Cutoff ほぼ全件)

| 層 | N | WR | Wilson 95% | PF | EV (pip) |
|---|---:|---:|---|---:|---:|
| **LIVE (is_shadow=0)** | **4** | **75.0%** | [30.1%, 95.4%] | **6.55** | **+10.12** |
| SHADOW | 12 | 16.7% | [4.7%, 44.8%] | 0.79 | -1.48 |
| 合計 | 16 | 31.2% | [14.2%, 55.6%] | 1.24 | +1.42 |

LIVE は PF 6.55 / EV +10.12 だが **N=4 で Wilson 下限 30%** — 偶然と edge を判別不可.

## 3. BUY/SELL 非対称 — implementation drift

| Direction | N | WR | PF | EV |
|---|---:|---:|---:|---:|
| **BUY** | **7** | **42.9%** | **4.23** | **+5.21** |
| SELL | 9 | 22.2% | 0.83 | **-1.53** |

BT 表 ([[vwap-mean-reversion]]) は **VW2s BUY のみ Bonferroni 有意**. SELL side は BT 未検証なのに発火 → edge 希釈. BUY-only filter 候補.

## 4. MFE/MAE 因果分解

| 群 | N | MFE median (pip) | MAE median (pip) |
|---|---:|---:|---:|
| WIN | 5 | **33.1** | **0.00** |
| LOSS | 11 | **0.00** | 8.9 |

古典的 MR の asymmetric outcome: 2σ 突破後 reversion が始まれば大きく走る (MAE=0), 始まらねば即 SL 直行 (MFE=0). 中間状態が無い.

## 5. ペア別 (N<6 推論不可、観察記録)

| Pair | N | WR | EV | BT root claim |
|---|---:|---:|---:|---|
| EUR_JPY | 5 | 40% | **-7.74** | BT 最強 (WR 55.8% EV +3.85) ⚠️ BT-Live 乖離 |
| GBP_JPY | 2 | 50% | +14.65 | BT 最強 (WR 56.2% EV +5.17) |
| EUR_USD | 2 | 50% | +13.05 | BT 未カバー |
| GBP_USD | 4 | 25% | +2.10 | BT 未カバー |
| USD_JPY | 3 | 0% | -0.80 | BT 中 (WR 55.0%) |

**Red flag**: EUR_JPY の BT-Live 乖離 (dt_fib_reversal 事例と同構造). Audit B 第二弾で精査必要 (既に [[audit-b-promoted-strategies-2026-04-21]] §6 候補).

## 6. Quant 判断

**+**: BT 365d Bonferroni p<10⁻⁷ / BUY side PF 4.23 Live / MFE-MAE 構造明瞭  
**−**: LIVE N=4 Wilson 広 / SELL side BT 無根拠で発火 / EUR_JPY BT-Live 乖離 / confidence 低 conf で win (scoring との整合性欠)

## 7. 行動推奨

| P | 内容 | 期日 |
|---|---|---|
| **P1** | 小 lot 観察継続 (lot 増 禁止). 2026-05-05 中間判定 | 2 週間 |
| **P2** | `vwap_mean_reversion_BUY` split pre-register (SELL 除外) — 2026-05-15 再評価時 | 3 週間 |
| **P2** | EUR_JPY BT-Live 乖離 Audit B 第二弾で精査 | LIVE N≥15 蓄積後 |
| — | 本日は **何もしない** (今日午前 6 PRIME pre-reg 済, 追加は multiple testing inflation) | — |

## 8. ユーザー体感への honest answer

「リアルタイム見ていると強そう」 = **半分 real, 半分 bias**
- Real: LIVE PF 6.55, BUY PF 4.23 → directional edge 仮説は alive
- Bias: N=4 / 4/21 の 4-in-a-row WIN の recency / SELL 損と EUR_JPY 損は見えにくい

VWAP は **観察継続に値する仮説**. ただし今すぐ tier 昇格や lot 増は multiple testing inflation.
