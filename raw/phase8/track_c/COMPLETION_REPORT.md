# Phase 8 Track C — Completion Report

**Date**: 2026-04-28
**Track**: C (Quantile-bucketed continuous features, rolling 30d decile)
**Pre-reg LOCK**: [pre-reg-phase8-track-c-2026-04-28.md](../../knowledge-base/wiki/decisions/pre-reg-phase8-track-c-2026-04-28.md)
**Master plan**: [phase8-master-2026-04-28.md](../../knowledge-base/wiki/decisions/phase8-master-2026-04-28.md)
**Tool**: `tools/phase8_track_c.py`
**Status**: 完了 — 0 survivors

## TL;DR

Track C (rolling 30d decile bucketing) は Stage 1 / Stage 2 共に **gate 通過
cell ゼロ**。decile 境界は Track A の固定 threshold と全期間平均で実質一致し、
adaptive bucketing 仮説 (H1-H3) は **棄却**。

## Stages 実行サマリ

| Stage | Cells | Survivors | Gate | Notes |
|---|---|---|---|---|
| 1 (single) | 1,200 | **0** | BH-FDR q=0.10 + Wilson>0.50 + EV>0 + N≥100 + cap≥5 + Sharpe>0.05 | 全 cell EV<0 |
| 2 (pairwise) | 8,604 | **0** | Bonferroni α=0.05 + 同上 | best p=0.40 (Bonferroni 必要 5.8e-6) |

## 仮説検証

| 仮説 | 結果 | 根拠 |
|---|---|---|
| H1: Tail buckets (D0/D9) に edge 集中 | **棄却** | top 10 EV cell に D5 mid-range が含まれる |
| H2: 固定 threshold bias 回避 | **棄却** (回避できない) | boundary 比較で実質同一 (P10≈0.20, P80≈0.80 等) |
| H3: Pair-specific quantile で characteristic 反映 | **部分採択** | RSI overbought など pair 差はあるが edge 化せず |

## Output 一覧

- `tools/phase8_track_c.py` — 新規実装 (487 行)
- `knowledge-base/wiki/decisions/pre-reg-phase8-track-c-2026-04-28.md` — Pre-reg LOCK
- `raw/phase8/track_c/stage1_decile_20260428_0504.json` — Stage 1 raw (1200 cells)
- `raw/phase8/track_c/stage2_decile_pair_20260428_0515.json` — Stage 2 raw (8604 cells)
- `raw/phase8/track_c/track_a_vs_c_20260428.md` — boundary 比較レポート
- `raw/phase8/track_c/COMPLETION_REPORT.md` — 本レポート

## Top 5 cells (Stage 2, Wilson_lower 上位)

```
USD_JPY  BUY  atr_pct_60d=D9 × recent_3bar=D9   fw=8  n=155 WR=0.535 Wlo=0.457 EV=+0.58p p=0.398
GBP_JPY  SELL rsi_15m=D5     × recent_3bar=D5   fw=12 n=137 WR=0.540 Wlo=0.457 EV=+1.85p p=0.393
GBP_USD  SELL rsi_15m=D6     × atr_pct_60d=D4   fw=12 n=108 WR=0.546 Wlo=0.452 EV=-1.29p p=0.351
USD_JPY  BUY  atr_pct_60d=D9 × recent_3bar=D9   fw=4  n=161 WR=0.528 Wlo=0.451 EV=+0.57p
USD_JPY  BUY  bbpb_15m=D4    × rsi_15m=D2       fw=4  n=139 WR=0.532 Wlo=0.450 EV=-0.30p
```

**最強候補**: USD_JPY BUY atr_pct=D9 × recent_3bar=D9 (high-vol × strong-up momentum
continuation buy fw=8) — Wilson_lo=0.457, EV=+0.58p。Bonferroni 後 p=3,461、
通過する余地なし。

## Cross-track 結論

- Track A の固定 threshold は適切に設計されており、decile への置換で **新規
  edge 発掘の追加価値はない**
- Phase 8 master plan の cross-track aggregation で Track C は **0 cell 寄与**
- de-dup ロジックでも、Track C の最有力候補は Track A bucket と redundant な
  boundary を持つため、独立 vote しない

## Master へ通知 (master plan 「次のアクション」3 に対応)

- Track C 完了 / survivors 0
- 期待値 (1-2 cells) 下回り、master plan 内の expected total survivors を
  下方修正すべき (3-11 → 2-10)
- 次のアクション: Track A/B/D/E の結果集約を待ち、top 3 採用を判断

## Lessons (lessons/ には書かない、本レポートに留める)

- Rolling 30d decile boundary は majors の static distribution が安定しすぎて
  ほぼ全期間 quantile に収束する。短期 30d window でも長期 boundary とほぼ
  同じ。decile bucketing で「bias 回避」を狙うなら **regime-conditional**
  (=Track E) との組合せが必要
- 「粒度を細かくすれば edge が出る」の素朴な期待は **多重検定で完全に潰される**:
  bucket 数 5→10 で n_tests が 4-8 倍、Bonferroni 閾値が同比で厳しくなる
- 唯一光った tail × tail combo (D9 × D9) の N が 155 のみ — これを follow-up
  するなら **N 集約のためのデータ拡張** (multi-pair pooling 等) が必須
