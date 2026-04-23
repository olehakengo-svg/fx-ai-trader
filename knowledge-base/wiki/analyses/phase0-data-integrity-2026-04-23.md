# Phase 0: Shadow Data Integrity Audit (2026-04-23)

**Scope**: shadow post-cutoff 2026-04-08 / XAU除外 / N=2075
**Script**: `/tmp/data_integrity_audit.py`
**Trigger**: [[quant-validation-label-audit-2026-04-23]] で全カテゴリ Kelly≤0 判明
→ データ生成 bug (仮説 b) を排除してから regime mismatch (仮説 a) を確定

## Result: ✅ Data integrity OK

| Check | Result | Tolerance |
|-------|--------|-----------|
| pnl_pips vs raw price calc | **0 discrepancy** (2075/2075 perfect) | <1.5p |
| pnl sign mismatches | **0** | hard bug |
| outcome ↔ pnl sign | **0 contradictions** | hard bug |
| TP_HIT exit = tp | 12/426 off (2.8%) | <3pip |
| SL_HIT exit = sl | 3/1113 off (0.3%) | <3pip |
| exit_time > entry_time | **0 violations** | hard bug |
| Duplicate trade_id | **0** | hard bug |
| BUY vs SELL WR | 24.1% vs 23.4% | gap 0.6pp (<10pp OK) |

## Key findings

### 1. pnl_pips is RAW price movement (no spread deducted)

`pnl_pips = (exit_price − entry_price) × pip_factor` で **完全一致** (mean diff = 0.000p)。
つまり **報告 pnl_pips は friction 未控除**。実現 P&L は `pnl_pips − spread` になる。

**Implication**: BT_COST=1.0 の使用は簡便だが instrument-dependent。

### 2. Per-instrument median spread

| Instrument | N | p50 spread | BT_COST=1.0 との差 |
|------------|---|-----------|-------------------|
| USD_JPY | 1144 | 0.8 | +0.2p (reported EV より実 EV が良い) |
| EUR_USD | 484 | 0.8 | +0.2p |
| GBP_USD | 363 | 1.3 | **-0.3p** (実 EV が悪い) |
| EUR_JPY | 66 | 1.9 | **-0.9p** |
| GBP_JPY | 17 | 2.8 | **-1.8p** |

weighted avg spread ≈ 0.92p (全体では BT_COST=1.0 は若干保守)。
ただし **GBP_JPY / EUR_JPY / GBP_USD の EV は過大評価**されている可能性。

### 3. TP_HIT / SL_HIT の精度

- TP_HIT 426件中 12件 (2.8%) が tp 価格から >3pip ズレ → 一部で slippage 大
- SL_HIT 1113件中 3件 (0.3%) — 非常に良好
- 非対称性 (TP の方が mismatch 率高い) は一般的 (TP は limit order で深く切れる可能性)

### 4. No systematic directional bias

BUY WR 24.1% vs SELL WR 23.4%、gap 0.6pp。
→ 方向固有の bug はなし。

## Conclusion

データ生成は健全。全カテゴリ Kelly≤0 / WR 22-26% (BEV 50% から 24-28pp 乖離) は
**genuine regime mismatch** による。

[[quant-validation-label-audit-2026-04-23]] の Phase 0 仮説判定:
- ❌ **(b) shadow P&L 計算 bug** — 排除
- ⚠ **(c) BT_COST underestimate** — GBP/JPY 系で若干 underestimate だが主因ではない
  (weighted avg で 1.0 に近い)
- ✅ **(a) regime mismatch** — 確定。システム全体が current 市場で broken

## Next actions

### Immediate (本セッション)
- [[pre-registration-phase2-cell-level-2026-04-23]] を作成
- Cell-level observational scan (コード変更なし、observational only)

### 次セッション以降
- Phase 1 holdout (2026-05-07): [[pre-registration-label-holdout-2026-05-07]]
- Phase 2 cell-level decision (holdout 後)
- Phase 3 stopping rule

### BT_COST の revisit (推奨)
現 `BT_COST=1.0` を per-instrument spread 中央値に置き換え可能。
- USD_JPY / EUR_USD: 0.8
- GBP_USD: 1.3
- EUR_JPY: 1.9
- GBP_JPY: 2.8

これは分析精度の向上のみ、取引意思決定への直接影響なし。

## References

- Raw output: `/tmp/data_integrity_output.txt`
- Script: `/tmp/data_integrity_audit.py`
- [[quant-validation-label-audit-2026-04-23]]
