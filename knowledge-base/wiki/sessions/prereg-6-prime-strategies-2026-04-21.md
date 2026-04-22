# Binding Pre-Registration — 6 PRIME Strategies LIVE Trial

**Registered**: 2026-04-21 (UTC ~10:30)
**Status**: **BINDING** — 閾値・lot・roll-back 基準は 2026-05-15 まで変更禁止
**Based on**: [[task1-win-dna-2026-04-21]] + [[virtual-sim-6-primes-2026-04-21]]
**Re-evaluation**: **2026-05-15** (post-Cutoff N 倍増想定)

---

## 0. Data snapshot (binding)

| Field | Value |
|---|---|
| Source | `/api/demo/trades?limit=2500` |
| Filter | `is_shadow=1 ∧ outcome∈{WIN,LOSS} ∧ instrument≠XAU_USD` |
| N | 1711 (WIN=474, LOSS=1237) |
| Baseline WR | 27.70% |
| Cutoff | 2026-04-16 |

## 1. Global quartile edges (binding — 変更禁止)

```python
EDGES = {
    "confidence":      [53.0, 61.0, 69.0],    # Q1/Q2/Q3/Q4 boundaries
    "spread_at_entry": [0.8, 0.8, 0.8],       # 縮退 — 分析不可
    "rj_adx":          [20.3, 25.3, 31.7],
    "rj_atr_ratio":    [0.95, 1.01, 1.09],
    "rj_close_vs_ema200": [-0.019, 0.001, 0.034],
}
```

Quartile 付与規則: `v ≤ edge[0] → Q1`, `≤ edge[1] → Q2`, `≤ edge[2] → Q3`, `> edge[2] → Q4`.

## 2. 6 PRIME 戦略仕様 (binding fire conditions)

| # | 新戦略名 | Base | Fire condition (すべて AND) | Shadow 実績 |
|---|---|---|---|---|
| 1 | `stoch_trend_pullback_PRIME` | stoch_trend_pullback | `atr_ratio ≤ 0.95` AND `direction=BUY` | N=24, WR=58.3%, PF=2.10, EV=+1.51p |
| 2 | `stoch_trend_pullback_LONDON_LOWVOL` | stoch_trend_pullback | `atr_ratio ≤ 0.95` AND `session=london` (UTC 8-13) | N=11, WR=63.6%, PF=2.43, EV=+2.06p |
| 3 | `fib_reversal_PRIME` | fib_reversal | `61 < confidence ≤ 69` AND `0.001 < close_vs_ema200 ≤ 0.034` | N=12, WR=75.0%, PF=4.99, EV=+2.96p |
| 4 | `bb_rsi_reversion_NY_ATRQ2` | bb_rsi_reversion | `hour∈{12,13,14,15}` (UTC) AND `0.95 < atr_ratio ≤ 1.01` | N=18, WR=55.6%, PF=1.30, EV=+0.82p |
| 5 | `engulfing_bb_TOKYO_EARLY` | engulfing_bb | `session=tokyo` (UTC 0-8) AND `hour∈{0,1,2,3}` | N=9, WR=55.6%, PF=2.73, EV=+2.18p |
| 6 | `sr_fib_confluence_GBP_ADXQ2` | sr_fib_confluence | `instrument=GBP_USD` AND `20.3 < adx ≤ 25.3` | N=13, WR=53.8%, PF=1.46, EV=+1.75p |

## 3. Evidence Tier 分類 (binding)

| Tier | 基準 | 戦略 | 初期 lot multiplier |
|---|---|---|---|
| **A** | Bonferroni-6有意 (p<α/6=0.0083) + WF再現 + EV+PF>1 | (1) stoch_trend_pullback_PRIME, (3) fib_reversal_PRIME | **0.3x** (small-lot LIVE trial) |
| **B** | raw p<0.05 + WF再現 + EV+PF>1, Bonferroni-6非有意 | (2) stoch_trend_pullback_LONDON_LOWVOL, (4) bb_rsi_reversion_NY_ATRQ2, (6) sr_fib_confluence_GBP_ADXQ2 | **0.1x** (Sentinel lot) |
| **C** | N<10 or raw p>0.10 | (5) engulfing_bb_TOKYO_EARLY | **Shadow 継続のみ** (LIVE 化せず) |

**Tier C は LIVE 化しない** — Fisher p=0.1374 で偶然域. N≥15 蓄積後 2026-05-15 再判定.

## 4. Roll-back / Stop 条件 (binding — 自動発火)

**各 PRIME 戦略で以下のいずれかに該当した時点で即時 SENTINEL 縮退 or 停止**:

| 条件 | 発火時 action |
|---|---|
| LIVE N ≥ 15 時点で WR < 40% | Tier 降格 (A→B, B→stop) |
| LIVE N ≥ 15 時点で PF < 0.8 | 即停止 |
| LIVE N ≥ 15 時点で EV < -0.5 pips/trade | 即停止 |
| 連続 6 連敗 (WR=0/6) | 即停止 + audit |
| Wilson 95% 下限 < 30% at N=20+ | Tier 降格 |
| 2026-05-15 到達 | 再評価 (N & WR を gate 基準で判定) |

## 5. Re-evaluation 基準 (2026-05-15, binding)

### LIVE 本昇格 (lot 1.0x) 条件 (全 AND)
1. LIVE N ≥ 30
2. LIVE WR ≥ 50%
3. Wilson 95% 下限 > 35%
4. PF ≥ 1.3
5. EV ≥ +0.5 pips/trade
6. Shadow+Live 合算で Bonferroni (M=6) p < 0.0083

### Tier 維持 (lot そのまま) 条件
- LIVE N ≥ 15
- LIVE WR ≥ 45%
- PF ≥ 1.0
- EV ≥ 0

### Rollback (FORCE_DEMOTED) 条件
- 上記 Stop 条件のいずれか該当

## 6. 実装方針 (Path A — gate-layer filter)

**既存 signal 関数は変更しない**. OANDA 送信 gate (`modules/demo_trader.py::_should_send_to_oanda`) に condition check を追加.

具体的:
- 新規 module `modules/prime_gate.py` 作成 (pure function)
- `classify_prime(entry_type, trade_ctx) -> Optional[str]` が PRIME 名を返す
- `_should_send_to_oanda(entry_type, instrument, trade_ctx=None)` を拡張し、PRIME 該当時は lot_multiplier を返す
- PRIME に該当しない base 戦略の trade は 従来通り (FORCE_DEMOTED なら Shadow 継続)

**コード変更最小化**: signal 関数・ロジックに一切触れない. gate 層で filter のみ.

## 7. 期待 fire rate & 月間 trade 数試算

Shadow N=1711 (期間 28 日 ≈ 7 日 post-Cutoff 含む) から base 戦略 fire rate × condition match rate:

| 戦略 | Base月間fire推定 | Condition match率 | PRIME月間fire推定 |
|---|---:|---:|---:|
| stoch_trend_pullback_PRIME | 150 | 16.9% | **~25** |
| fib_reversal_PRIME | 200 | 6.4% | **~13** |
| stoch_trend_pullback_LONDON_LOWVOL | 150 | 7.7% | **~12** |
| bb_rsi_reversion_NY_ATRQ2 | 135 | 14.1% | **~19** |
| sr_fib_confluence_GBP_ADXQ2 | 110 | 12.7% | **~14** |

合計 ~83 trades/月 の新 LIVE 機会. Tier A (2戦略) で ~38 trades/月.

## 8. 多重検定補正の明示

- Family size M (今回の PRIME promotion 範囲) = **6**
- Bonferroni α/M = 0.05/6 = **0.0083**
- Pass: 戦略 (1) stoch_trend_pullback_PRIME (p=0.0010), 戦略 (3) fib_reversal_PRIME (p=0.0046)
- **注記**: Task 1 の 2112-cells 探索空間で Bonferroni を取ると全て非有意. 本 pre-reg は "PRIME 候補を事前確定" した上で small family (M=6) で有意性を再計算する **2段階探索 (post-hoc → pre-registered validation)** の設計.

## 9. 停止済み項目 (明示)

- 本 pre-reg は **Shadow continuation も並行**. LIVE 化しても Shadow 側の base 戦略 trade は記録続行 (base vs PRIME 比較用).
- XAU_USD は引き続き全面除外.
- 条件境界 (quartile edges) は **観測後再計算禁止** (今回の edges で binding).

## 10. 2026-05-15 提出物 (binding)

1. 各 PRIME の LIVE 実績 (N, WR, PF, EV, Wilson)
2. Shadow 側 base 戦略の同期間実績 (比較 baseline)
3. Bonferroni p 再計算
4. Tier 維持 / 昇格 / rollback の判定
5. 次 PRIME 候補 (post-Cutoff N 倍増で出現するなら)

---

**Status**: BINDING as of 2026-04-21 (UTC). 全 binding 項目は 2026-05-15 まで変更禁止.
**実装承認待ち**: `modules/prime_gate.py` + `demo_trader.py` diff はユーザー確認後に commit.
