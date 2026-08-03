# vix_carry_unwind × USD_JPY Overlap pilot 早期 demote (rule:R2, user 決裁 2026-08-03)

## Status
**EXECUTED** — `_PAIR_PROMOTED` から除外 + `_PAIR_DEMOTED` 復帰 + `_PAIR_SESSION_FILTER` / `_PAIR_LOT_BOOST` 撤去。
Regression pin: `tests/test_vix_pilot_demote_pin.py`

## 決裁経緯
1. **2026-07-07**: R2 基準に形式的抵触も pilot 継続を user 裁定 — 根拠は (a) shadow 正 EV
   (+0.96, N=60)、(b) 負 EV の主因は exit 執行、(c) 1000u で実損軽微。
   checkpoint = live SELL N≥20 or 2026-08-31 (registry `vix-sell-pilot-recheck`)、
   「demote する場合は user 決裁」と明記
2. **2026-07-31**: quant-eval 全数監査 ([[quant-eval-2026-07-31]]) で継続根拠 (a) の崩壊を検出、
   早期 demote を推奨として提示
3. **2026-08-03**: **user「進めて」承認 → 本執行**

## 分類: Rule 2 (Fast & Reactive — 損失停止 / pair demotion)
数トレード〜N=10 で即断可の類型。live N=26 は判定閾値を大きく超過。

## 証拠 (production 実測、quant-eval-2026-07-31 + 2026-08-03 追記)

### Live (oanda_trade_id ≠ '', post-cutoff)
| 指標 | 値 |
|---|---|
| N | 26 |
| WR | 58.3% (Wilson lo 38.8%) |
| EV | **−1.80 p/t** |
| PnL | **−46.9p** |
| PF | **0.66** |
| 月次 | 04: −21.3 / 05: +27.7 / 06: −19.0 / 07: **−34.3** (3/4 負) |

直近: 07-30 13:48 UTC に −30.1p (SL_HIT、Overlap 窓内 = pilot 経路として合法な発火)。

### Shadow (エッジ減衰の系列 — 07-07 継続根拠の崩壊)
| 月 | n | PnL |
|---|---|---|
| 2026-04 | 40 | **+537p** |
| 2026-05 | 35 | −98p |
| 2026-06 | 20 | +5p |
| 2026-07 | 84 | **−123p** |
| 08-01〜03 (追記) | 7 | −17p |

**05 月以降の累計 −233p / n=146** — 全期間集計 +320p は April regime の遺産であり、
現行 regime に正エッジは存在しないと判断。

### BT との整合 (hook 要件: BT WR/EV の引用)
- 365d BT anchor: EV=+0.506 (tier-master) / cell-conditional BT (2026-05-13 run):
  aggregate N=107 WR=72.9% EV=+0.74、Overlap cell N=22 WR=81.8% EV=+1.297
- **BT 正値を forward 実測が反証した構図** — BT 窓は April 型 regime を含み、その OOS に
  相当する forward shadow (05 月以降) が符号反転。判断プロトコル (Live > TV > Python BT、
  止血判定は EV 軸 / 「停止は安価、放置は致命的」) に従い、demotion に新規 BT は要求しない
  (BT 再走が必要なのは再昇格 = R1 側)

## 執行内容 (code)
| 箇所 | 変更 |
|---|---|
| `_PAIR_PROMOTED` | `("vix_carry_unwind","USD_JPY")` 除外 (22→21 entries) |
| `_PAIR_DEMOTED` | 同 tuple 復帰 (2026-05-11 demote 位置) |
| `_PAIR_SESSION_FILTER` | Overlap 窓エントリ撤去 (inert だが code consistency、session_time_bias 前例と同型) |
| `_PAIR_LOT_BOOST` | 1.0x エントリ撤去 (同上) |
| 残置 | `_AGG_KELLY_GATE_MINLOT_BYPASS_TYPES` / FLAT 除外 / MIN-lot 契約 code — demote 中は inert、再昇格時の 1000u 固定契約を保持 (eligible vs effective 教訓) |
| shadow emit | **不変更** (原則3 — UNIVERSAL_SENTINEL 維持、N 蓄積継続) |
| registry | `vix-sell-pilot-recheck` resolved 化 (checkpoint は本決裁で消化) |

## 再昇格条件 (R1)
forward shadow の regime 回復を要確認: 直近 90d shadow N≥30 ∧ EV>0 ∧ Wilson_lo > BEV 34.4%
∧ Bonferroni ∧ 365d cell-conditional BT 再走 ∧ pre-reg LOCK + user 承認。

## Related
- [[vix-overlap-pilot-prereg-2026-05-13]] (pilot 起点) / [[vix-1x-intentional-exception-2026-05-21]]
- [[vix-carry-grail-removal-overlap-1000u-2026-06-15]] (Grail #2 撤去)
- [[quant-eval-2026-07-31]] / [[grail19-ny-close-removal-2026-07-31]] (同系列の R2)
- [[vix-carry-unwind]] (戦略カード)
