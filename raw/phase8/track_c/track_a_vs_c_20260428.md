# Track A (固定 threshold) vs Track C (rolling 30d decile) — Boundary 比較

**Date**: 2026-04-28
**Stage 1 input**: `stage1_decile_20260428_0504.json` (1200 cells, 0 survivors)
**Stage 2 input**: `stage2_decile_pair_20260428_0515.json` (8604 cells, 0 survivors)

## 目的

Track C の rolling 30d decile boundary が Track A (Phase 7 / pattern_discovery.py)
の固定 threshold と「実質的に違うか」を診断する。違いがなければ Track C 結果は
Track A の de-dup 候補となる。

## Track A 固定 threshold (Phase 7 / pattern_discovery.py L186-200)

| Feature | Bucket 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| `bbpb_15m_b` | ≤ 0.20 | (0.20, 0.40] | (0.40, 0.60] | (0.60, 0.80] | > 0.80 |
| `rsi_15m_b` | ≤ 30 | (30, 50] | (50, 70] | > 70 | — |
| `atr_pct_60d_b` | ≤ 0.333 | (0.333, 0.667] | > 0.667 | — | — |

## Track C 全期間 quantile (per pair) — rolling 30d 平均値の proxy

### bbpb_15m

| Pair | P10 (D0 上限) | P20 (D1 上限) | P50 (D4/D5 境界) | P80 (D7 上限) | P90 (D8 上限) |
|---|---|---|---|---|---|
| USD_JPY | 0.088 | 0.217 | 0.536 | 0.815 | 0.926 |
| EUR_USD | 0.083 | 0.198 | 0.503 | 0.809 | 0.929 |
| GBP_USD | 0.081 | 0.201 | 0.508 | 0.809 | 0.921 |
| EUR_JPY | 0.096 | 0.227 | 0.554 | 0.821 | 0.926 |
| GBP_JPY | 0.092 | 0.217 | 0.543 | 0.816 | 0.923 |

**所見**:
- Track A `bucket=0` (≤ 0.20) ≈ Track C `D0+D1` (P0-P20、boundary ~0.20)
- Track A `bucket=4` (> 0.80) ≈ Track C `D7-D9` (P70-P100、boundary ~0.80)
- 両者の境界は実質的に一致 — Track C で「中央値 vs 0.5」の違いは
  USD_JPY +0.036, EUR_USD +0.003 程度で、市場 regime 起因の adaptation 効果は
  全期間平均では弱い

### rsi_15m

| Pair | P10 | P20 | P50 | P80 | P90 |
|---|---|---|---|---|---|
| USD_JPY | 29.3 | 36.7 | 51.3 | 65.8 | 73.5 |
| EUR_USD | 29.0 | 36.2 | 50.1 | 64.6 | 71.5 |
| GBP_USD | 29.0 | 36.5 | 50.2 | 64.3 | 71.3 |
| EUR_JPY | 30.4 | 37.8 | 51.8 | 65.1 | 71.9 |
| GBP_JPY | 29.8 | 37.6 | 51.2 | 64.9 | 71.8 |

**所見**:
- Track A `RSI ≤ 30` (oversold) ≈ Track C `D0` (P0-P10, ~29-30)
- Track A `RSI > 70` (overbought) ≈ Track C `D8-D9` (P80-P100, P80=~65 is much
  lower than 70 — pair 全期間で extreme RSI > 70 が出る頻度が低い)
- 注目: 全 pair で P80 (= D7/D8 境界) が 64-66 → 固定 RSI=70 threshold は
  D8 上限 (P90=72) に近い。**RSI overbought の adaptive bucket は固定値
  より厳しい** (= overbought が頻発する regime では D9 = top 10% のみが真の
  extreme)

### atr_pct_60d

| Pair | P10 | P20 | P50 | P80 | P90 |
|---|---|---|---|---|---|
| USD_JPY | 0.068 | 0.136 | 0.404 | 0.745 | 0.876 |
| EUR_USD | 0.049 | 0.120 | 0.391 | 0.735 | 0.854 |
| GBP_USD | 0.066 | 0.152 | 0.447 | 0.777 | 0.885 |
| EUR_JPY | 0.080 | 0.169 | 0.466 | 0.792 | 0.903 |
| GBP_JPY | 0.075 | 0.158 | 0.449 | 0.802 | 0.908 |

**所見**:
- Track A `atr_pct ≤ 0.333` (low vol) ≈ Track C `D0-D3` (P0-P40, boundary 0.30-0.35)
- Track A `atr_pct > 0.667` (high vol) ≈ Track C `D7-D9` (P70-P100, boundary
  0.62-0.69)
- ATR percentile 自身が rolling rank なので decile boundary も同じく
  pair-specific volatility を反映 — adaptive 効果は限定的

### recent_3bar_ret

| Pair | P10 | P20 | P50 | P80 | P90 |
|---|---|---|---|---|---|
| USD_JPY | -0.0009 | -0.0005 | 0.0000 | +0.0006 | +0.0009 |
| EUR_USD | -0.0007 | -0.0004 | 0.0000 | +0.0004 | +0.0007 |
| GBP_USD | -0.0007 | -0.0004 | 0.0000 | +0.0004 | +0.0008 |
| EUR_JPY | -0.0007 | -0.0004 | 0.0000 | +0.0005 | +0.0008 |
| GBP_JPY | -0.0008 | -0.0005 | 0.0000 | +0.0005 | +0.0008 |

**所見**:
- Track A `recent_3bar_b` は -1/0/+1 の sign-based 3 buckets
- Track C は decile で連続 momentum を細分化 — 但し対称分布なので Track A と
  異なる粒度: D0 = 強 down momentum, D9 = 強 up momentum, D4-D5 = flat
- 注目: USD_JPY の P90 = 0.0009 = log return → ~9 pips の連続上昇/3bar = strong
  momentum signal。pair 別の magnitude 差異 (USD_JPY: ±0.0009 vs EUR_USD:
  ±0.0007) は ATR-normalize していないので vol 違い由来

## De-dup 判定

| Track A bucket | 対応 Track C decile | 重複度 | 判定 |
|---|---|---|---|
| `bbpb_15m_b=0` (≤ 0.20) | `bbpb_15m_decile=D0+D1` (~P0-P20) | 高 (>90%) | redundant |
| `bbpb_15m_b=4` (> 0.80) | `bbpb_15m_decile=D8+D9` (~P80-P100) | 高 (>90%) | redundant |
| `rsi_15m_b=0` (≤ 30) | `rsi_15m_decile=D0` (~P0-P10) | 高 (~95%) | redundant |
| `rsi_15m_b=3` (> 70) | `rsi_15m_decile=D9` (~P90-P100) | 中 (~70%) | partial |
| `atr_pct_60d_b=0` (≤ 1/3) | `atr_pct_60d_decile=D0-D2` | 高 | redundant |
| `recent_3bar_b=-1/0/+1` | `recent_3bar_ret_decile=D0..D9` | 中 (粒度差) | C novel granularity |

**redundancy 全体評価**: Track C の単純な decile boundary は Track A の固定
threshold と本質的に重複している。ただし:
1. Track C は bucket 数が増える (5 → 10) ので **粒度** で発見できる edge は novel
2. RSI overbought (>70) は Track A では bucket=3 で雑、Track C は D8/D9 分離
3. recent_3bar は Track A の sign-based vs Track C decile で粒度が大きく違う

## Stage 2 Top cells (Wilson_lower 上位 10)

```
USD_JPY  BUY   atr_pct_60d=D9 × recent_3bar=D9    fw=8   n=155 WR=0.535 Wlo=0.457 EV=+0.58p  ← high-vol momentum continuation (extreme tail)
GBP_JPY  SELL  rsi_15m=D5     × recent_3bar=D5    fw=12  n=137 WR=0.540 Wlo=0.457 EV=+1.85p  ← MID-RANGE cell (novel!)
GBP_USD  SELL  rsi_15m=D6     × atr_pct_60d=D4    fw=12  n=108 WR=0.546 Wlo=0.452 EV=-1.29p  ← negative EV despite high WR
USD_JPY  BUY   atr_pct_60d=D9 × recent_3bar=D9    fw=4   n=161 WR=0.528 Wlo=0.451 EV=+0.57p
USD_JPY  BUY   bbpb_15m=D4    × rsi_15m=D2        fw=4   n=139 WR=0.532 Wlo=0.450 EV=-0.30p
```

**観察**:
- 唯一の真 tail edge: USD_JPY BUY ATR_pct=D9 × recent_3bar=D9 fw=8
  (P=0.40 → Bonferroni p=3461 — 桁違いに足りない)
- **GBP_JPY SELL RSI=D5 × recent_3bar=D5 が surprise**: Track A の固定 bucket
  では「RSI 50付近 × momentum 0付近」は noise として捨てられるが、Track C で
  Wilson_lo=0.457, EV=+1.85p。但し p=0.39 で Bonferroni 通過せず

## 結論

1. **Track C 単独で Bonferroni 通過 cell: 0**
2. **boundary 比較**: Track C の rolling 30d decile は Track A の固定 threshold
   と境界がほぼ一致 (ペア全期間平均で)。adaptive 効果は弱く、**新規 edge
   発掘の主要 driver にならない**。
3. **粒度** が違いの本質: Track C は 5→10 bucket で edge を細かく見るが、
   それでも Bonferroni 通過しない (n_tests=8604 で α/n=5.8e-6 必要)
4. **唯一の novel observation**: tail × tail combo (ATR_pct=D9 × momentum=D9)
   は positive EV を示すが N 不足

## Master plan への提言

- Track C の **adaptive bucketing 仮説は弱い**: 鉄則として Track A 結果と
  redundant
- **粒度効果** を検証するなら quintile (5) でなく **percentile (100)** scan が
  必要だが N が完全に足りない
- 期待 1-2 cells の予測に対し **0 cell**: master plan の cell 集計から Track C
  を除外して問題なし
- Stage 3/4 への持ち込み候補: **無し** (best Bonferroni p = 3461)

## Follow-up 候補 (本セッションでは実装せず)

1. tail × tail combo 専用 scan (D0/D9 のみ × 全 feature combo) で N 集約
2. atr_pct_60d=D9 (high vol) を condition として Track A の他 feature 再走査
3. recent_3bar の decile を **ATR-normalized** にして magnitude bias 除去
