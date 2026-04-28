# Phase 8 Track B — Micro-Sequence Pattern Discovery: Summary (2026-04-28)

## TL;DR

- **Formal Stage 1 LOCK survivors: 0**
- **Stage 2 holdout: skipped (no Stage 1 survivors)**
- **Exploratory near-survivors with holdout consistency**: 1 cluster (USD_JPY mom_exhaust_5=DN5 BUY, all 3 fw)
- **Per master plan discipline**: Track B contributes **0 formal candidates** to Phase 8 deployment shortlist; 1 cluster flagged for **audit only**.

---

## Scan Configuration (LOCK 準拠)

- Pre-reg: `wiki/decisions/pre-reg-phase8-track-b-2026-04-28.md`
- Pattern kinds: 5 families (dir_seq_3, engulf_seq, wick_dom_seq, mom_exhaust_5, in_out_3)
- Pairs: 5 majors (USDJPY, EURUSD, GBPUSD, EURJPY, GBPJPY)
- Directions: BUY, SELL
- Forward bars: 4, 8, 12
- Training: 275d (cutoff to last-90d holdout)
- Trade sim: SL=1.0×ATR, TP=1.5×ATR, RR=1.5, friction_for cell-conditioned
- Stage 1 gates (LOCK): N≥50, BH-FDR(q=0.10), Wilson_lower(95%) > 0.50, EV_pip_net > 0

---

## Cell counts by pattern_kind

| pattern_kind | n_cells generated | survivors |
|---|---|---|
| dir_seq_3 | 712 | 0 |
| wick_dom_seq | 805 | 0 |
| in_out_3 | 270 | 0 |
| engulf_seq | 240 | 0 |
| mom_exhaust_5 | 60 | 0 |
| **TOTAL** | **2,087** | **0** |

---

## Why 0 formal survivors?

最大 Wilson_lower (training): **0.458** (USD_JPY mom_exhaust_5=DN5 BUY fw=4)。
LOCK gate (Wilson_lower > 0.50) を満たす cell は存在しなかった。

これは meaningful な結果:
- RR=1.5 setup の BEV (gross) は約 40%、friction 込み実 BEV は約 42-43%
- Sequence patterns は 42-46% WR レンジに集中 (= friction を稼げない random)
- Wilson_lower > 0.50 は意図的に保守的 (Phase 7 と同 LOCK)、edge が真に存在するなら
  N が大きい cell でもこの bar は超える

Implication: **micro-sequence patterns alone は USDJPY/EURUSD/GBPUSD/EURJPY/GBPJPY
の 15m timeframe では positive expectancy edge を持たない**(本 LOCK のもとで)。

---

## Top 15 by EV (training, no LOCK pass)

| Pair | Dir | Pattern | fw | n | WR | Wilson_lo | EV (pip) |
|---|---|---|---|---|---|---|---|
| EUR_JPY | BUY | wick_dom_seq=U\|U\|U | 12 | 56 | 0.554 | 0.424 | +3.03 |
| EUR_JPY | SELL | dir_seq_3=0\|0\|-1 | 12 | 50 | 0.540 | 0.404 | +2.30 |
| EUR_JPY | BUY | wick_dom_seq=U\|U\|U | 8 | 57 | 0.526 | 0.399 | +1.93 |
| EUR_JPY | BUY | wick_dom_seq=U\|U\|U | 4 | 58 | 0.517 | 0.392 | +1.32 |
| EUR_JPY | SELL | dir_seq_3=0\|0\|-1 | 4 | 50 | 0.520 | 0.385 | +1.20 |
| EUR_JPY | SELL | dir_seq_3=0\|0\|-1 | 8 | 50 | 0.540 | 0.404 | +1.14 |
| USD_JPY | BUY | mom_exhaust_5=DN5 | 12 | 178 | 0.528 | 0.455 | +0.96 |
| GBP_JPY | SELL | mom_exhaust_5=UP5 | 12 | 221 | 0.498 | 0.432 | +0.39 |
| USD_JPY | BUY | mom_exhaust_5=DN5 | 8 | 178 | 0.494 | 0.422 | +0.39 |
| USD_JPY | BUY | mom_exhaust_5=DN5 | 4 | 179 | 0.531 | 0.458 | +0.26 |

---

## Exploratory Holdout Audit (NON-LOCK, top 8 EV>0)

LOCK は 0 survivor だが、master plan のクロストラック比較のため **EV>0 ∧
Wilson_lower>0.40** の near-survivor を holdout で再検証 (audit only):

| Pair | Dir | Pattern | fw | Train EV | Holdout n | Holdout WR | Holdout EV | Verdict |
|---|---|---|---|---|---|---|---|---|
| EUR_JPY | BUY | wick_dom_seq=U\|U\|U | 12 | +3.03 | 45 | 0.422 | -1.08 | ❌ |
| EUR_JPY | SELL | dir_seq_3=0\|0\|-1 | 12 | +2.30 | 43 | 0.419 | -1.31 | ❌ |
| EUR_JPY | SELL | dir_seq_3=0\|0\|-1 | 8 | +1.14 | 43 | 0.395 | -2.32 | ❌ |
| **USD_JPY** | **BUY** | **mom_exhaust_5=DN5** | **12** | **+0.96** | **79** | **0.544** | **+0.98** | **✅** |
| GBP_JPY | SELL | mom_exhaust_5=UP5 | 12 | +0.39 | 112 | 0.384 | -4.73 | ❌ |
| **USD_JPY** | **BUY** | **mom_exhaust_5=DN5** | **8** | **+0.39** | **79** | **0.557** | **+0.93** | **✅** |
| **USD_JPY** | **BUY** | **mom_exhaust_5=DN5** | **4** | **+0.26** | **79** | **0.544** | **+0.68** | **✅** |
| GBP_JPY | SELL | mom_exhaust_5=UP5 | 8 | +0.39 | 113 | 0.345 | -5.18 | ❌ |

### Notable: USD_JPY mom_exhaust_5=DN5 BUY は 3/3 forward bars で training/holdout 両方が positive EV

- 5 連続 bear bar 後 → bullish reversal の predictor
- Training WR: 49.4-53.1% / Holdout WR: 54.4-55.7% (上振れ)
- 全 3 fw で holdout ev > 0、direction-stable
- ただし **Wilson_lower (train) = 0.422-0.458 < 0.50** で LOCK 未通過

GBP_JPY mom_exhaust_5=UP5 SELL は holdout で大幅 fail (WR 0.34-0.38)。USD_JPY との
asymmetry は session/volatility 差由来の可能性あり (USDJPY は overnight thin
liquidity で reversion 強)。

---

## Cross-Track Overlap Check

| 既存戦略 | Track B encoding | 重複可能性 |
|---|---|---|
| **wick_imbalance_reversion** (Osler 2003) | wick_dom_seq | EUR_JPY U\|U\|U BUY が同概念 (3連続 upper-wick dominant → 売り圧力減衰 → 上抜け) — ただし holdout fail |
| **liquidity_sweep** | wick_dom_seq U/L | sweep の wick spike を 3-bar 連続条件で encode したが、liquidity sweep は単発 wick を狙う |
| **doji_breakout** | dir_seq_3 with sign=0 | dir_seq_3=0\|0\|-1 (連続 doji → break) が概念重複、ただし holdout fail |
| **turtle_soup** | mom_exhaust_5 | turtle_soup は failed breakout reversal、mom_exhaust_5 は count-based reversal — mechanism は異なる |

USD_JPY mom_exhaust_5=DN5 BUY は **turtle_soup と概念近接** だが、Track B では
no S/R level 依存で純粋な count-based predictor。Sentinel deploy する場合は
turtle_soup との signal correlation 測定が必要。

---

## Master Plan Aggregation Submission

| Item | Value |
|---|---|
| Track | B (Micro-Sequence Patterns) |
| Cells generated | 2,087 |
| Stage 1 formal survivors | **0** |
| Stage 2 holdout survivors | **0** |
| Exploratory near-survivors | 1 cluster (USD_JPY mom_exhaust_5=DN5 BUY × {4, 8, 12}) |
| Recommendation | **audit only** — LOCK 未通過のため deployment 不可。USD_JPY DN5 BUY は次 quarter に N 蓄積後 re-audit 候補 |
| Risk for cross-track de-dup | mom_exhaust_5 と turtle_soup の signal correlation 要測定 |

---

## Output Files

- `raw/phase8/track_b/stage1_seqscan_20260428_0504.json` — Stage 1 raw (2087 cells)
- `raw/phase8/track_b/stage2_holdout_20260428_0512.json` — Stage 2 (empty, 0 survivors)
- `raw/phase8/track_b/explore_holdout_20260428_0513.json` — Exploratory holdout audit (8 cells)
- `tools/phase8_track_b.py` — Stage 1/2 main scanner
- `tools/phase8_track_b_explore_holdout.py` — Non-LOCK exploratory audit
- `wiki/decisions/pre-reg-phase8-track-b-2026-04-28.md` — Pre-reg LOCK
- `raw/phase8/track_b/track_b_summary_2026-04-28.md` — This document

---

## Limitations

- Encoding choice (5 patterns) は LOCK 時点の judgment、別 encoding (e.g. 4-bar や
  ATR-conditioned wick) で別の結果が出る可能性あり (post-hoc 変更は禁止)
- 15m timeframe のみ評価、5m / 1h は未検証
- N≥50 の rare-pattern 配慮で Phase 7 (N≥100) より緩和、それでも mom_exhaust_5 等の
  rare patterns は単一 pair で N=50-220 程度
- 既存戦略 signal との correlation 未測定 (cross-track aggregation 時に必要)

---

## Related

- [[phase8-master-2026-04-28]] — master plan、cross-track aggregation
- [[pre-reg-phase8-track-b-2026-04-28]] — Track B LOCK
- [[pre-reg-pattern-discovery-2026-04-28]] — Phase 7 (parent)
