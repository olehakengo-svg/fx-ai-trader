# spread_at_entry Edge — Confounding Analysis (2026-04-23)

## TL;DR
前 handover (2026-04-21) で特定された `spread_at_entry` × `outcome` の全期間シグナル (p=1.9e-5, WIN μ=0.763p vs LOSS μ=0.842p) は、**ペア識別子による交絡 (Simpson's paradox)** により発生した擬似効果。**フィルター特徴量として採用不可**。タスクは close。

## 背景
[[handover-tp-hit-quant-analysis-2026-04-21]] で `spread_at_entry` が TP-hit 予測に有意 (Mann-Whitney U, p=1.9e-5) と報告。"低スプレッド entry で TP-hit 率高" とのメカニズム仮説。365d BT 検証を next task 候補として保留していた。

## 検証手法
2026-04-23 時点で Render prod trades API から post-cutoff (>=2026-04-16) データ 1,336件を取得し、以下 3 段階で検証:

1. **Post-cutoff overall**: 全期間から cutoff 後の pure sample に絞った WIN/LOSS スプレッド差
2. **Spread quintile binning**: 全データ spread_at_entry を 5 分位分割し、WR の単調性を確認
3. **Per-pair 分解**: ペアごとの WIN/LOSS スプレッド差
4. **Within-pair variability**: 各ペアにおける spread_at_entry の unique 値個数と CoV

## 結果

### 1. Post-cutoff overall で effect size が 70% 縮小

| Window | N | WIN μ | LOSS μ | diff |
|---|---|---|---|---|
| All-time (handover) | 698 WIN / 1569 LOSS | 0.763 | 0.842 | **-0.079p** |
| Post-cutoff (今回) | 341 WIN / 995 LOSS | 0.937 | 0.961 | **-0.024p** |

### 2. Quintile breakpoints が縮退 → binning が意味を成さない

```
Breakpoints (pip): [0.8, 0.8, 0.8, 1.3]
→ Q1-Q3 は全て 0.8 固定（≒ 80% がこの値）
```

### 3. Per-pair で effect が消滅

| Pair | N_win | μ_win | N_loss | μ_loss | diff |
|---|---|---|---|---|---|
| USD_JPY | 211 | 0.800 | 557 | 0.805 | **-0.005** |
| EUR_USD | 64 | 0.800 | 200 | 0.800 | **-0.000** |
| GBP_USD | 53 | 1.300 | 186 | 1.304 | **-0.004** |

ペア内で見ると WIN/LOSS の spread 差は実質 0。

### 4. Within-pair variability — spread_at_entry はペア定数

| Pair | N | Unique values | 最頻値 (frequency) | CoV |
|---|---|---|---|---|
| EUR_USD | 308 | **1** | 0.8 (100%) | 0.0% |
| EUR_GBP | 1 | 1 | 1.3 (100%) | 0.0% |
| GBP_USD | 263 | 2 | 1.3 (99.6%) | **3.3%** |
| GBP_JPY | 16 | 4 | 2.8 (75%) | 3.7% |
| USD_JPY | 842 | 4 | 0.8 (99.5%) | **8.3%** |
| EUR_JPY | 53 | 13 | 1.9 (30%) | 14.4% |

全ペアで CoV < 20% — `spread_at_entry` は本質的に **ペア固定値** (BT/本番で摩擦定数を書き込んでいるだけ、市場の実スプレッド変動ではない)。

## 交絡構造 (Simpson's paradox)

```
        pair
         |
    ┌────┴────┐
    v         v
spread_at   WR
  _entry    
```

**ペア識別子 → spread_at_entry** かつ **ペア識別子 → WR** の共通原因構造。aggregate で spread↔WR 相関が見えるが、ペア固定すると消える = 典型的な confounded signal。

具体的には:
- Low spread pairs: EUR_USD (0.8), USD_JPY (0.8) — friction 小 & BEV_WR 最良 (34.4%)
- High spread pairs: GBP_USD (1.3), GBP_JPY (2.85) — friction 大 & WR 低下

aggregate 分析は「低 spread ペアの方が WR が高い」事実を検出していたに過ぎない。これは既に [[friction-analysis]] で既知の構造。

## 判断

- **実装提案なし**: filter として採用不可 (ペア識別子と完全共線なので情報ゼロ)
- **handover タスク close**: [[handover-tp-hit-quant-analysis-2026-04-21]] の 🟢 Research タスク `spread_at_entry` 365d BT 検証 → **INVALIDATED** (交絡の発見により BT 不要)

## Lesson
- 🔴 **集計統計の significance は segment 分解で必ず検証する**。p=1.9e-5 でも交絡由来なら実装価値ゼロ。
- 🔴 特徴量の **within-group variability (CoV)** を必ず先に確認する。CoV < 10% の特徴量は group identifier の proxy でしかない。
- 🟢 [[lesson-confounding-in-pooled-metrics-2026-04-23]] を本分析から新規作成。

## Related
- [[handover-tp-hit-quant-analysis-2026-04-21]]
- [[friction-analysis]]
- [[lesson-confounding-in-pooled-metrics-2026-04-23]]
- [[lesson-all-time-vs-post-cutoff-confusion]]

## Source
- Ad-hoc analysis: 2026-04-23 07:18 UTC
- Data: `GET /api/demo/trades?status=closed&date_from=2026-04-16` (paginated, N=1,483 raw / 1,336 valid)
- Analysis: inline Python (confounding test: unique values × CoV per pair)
