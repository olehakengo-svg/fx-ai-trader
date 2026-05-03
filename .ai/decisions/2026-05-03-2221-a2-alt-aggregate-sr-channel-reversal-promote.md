---
date: 2026-05-03
task: 20260503-1700-a2-alt-simple-structure-scalp-pre-reg (aggregate)
verdict: ACCEPT — `sr_channel_reversal × EUR_USD 5m` Promote 確定
rule: R1
gate: Gate 1 (Scalp 枝 N-acceleration) — 1 Promote 候補確定
---

# A2-alt Simple-Structure Scalp Aggregate — 4 候補 verdict 確定

## Aggregate verdict

**Promote 1 件確定**: `sr_channel_reversal × EUR_USD 5m`

Bonferroni K=4 / α/K=0.0125 LOCK 下で唯一の Promote 候補 (memory `feedback_partial_quant_trap` 規律遵守、PF/Wilson/WF/Bonferroni/max DD 全 LOCKED 条件 pass)。

## Final 4 候補 verdict table

| # | Strategy | Pair | TF | Verdict | N | WR | EV | PF | Wilson_lo | max DD% | WF IS/OOS PF | Bonf p | half-Kelly |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 1 | **sr_channel_reversal** | EUR_USD | 5m | **Promote** 🎯 | 52 | 61.54% | +0.373 | 2.724 | 47.96% | 14.84% | 2.56/2.89 | 0.00418 | 0.195 |
| 2 | fib_reversal | EUR_USD | 1m | Reject (max DD%) | 101 | 59.41% | +0.388 | 3.150 | 49.66% | **220.96%** | 2.16/4.96 | 0.00016 | 0.203 |
| 3 | engulfing_bb | USD_JPY | 5m | Reject (Bonf+DD%) | 30 | 53.33% | +0.212 | 1.557 | 36.14% | 188.21% | 1.16/1.95 | 0.093 | 0.095 |
| 4 | bb_squeeze_breakout | USD_JPY | 5m | Insufficient (N) | 24 | 75.00% | +0.913 | 4.872 | 55.10% | 26.73% | 2.44/inf | 0.000232 | 0.298 |

## sr_channel_reversal 詳細評価

全 Promote 条件 pass:
- N=52 ≥ 30 ✓
- WR 61.54%, Wilson 95% [47.96%, 73.53%] → Wilson_lo > BEV_WR+5pp = 44.7% ✓
- PF 2.724 ≥ 1.30 ✓
- WF IS/OOS PF: 2.557 / 2.889 (両方 ≥1.20, OOS が IS より高い = stable) ✓
- WF WR IS/OOS: 61.54% / 61.54% (完全一致 = 安定) ✓
- Bonferroni p = 0.00418 < α/K=0.0125 ✓
- max DD: 3.022 pip / **14.84%** ≤ 30% ✓

OVERFIT_SUSPECTED flag: not triggered (OOS PF / IS PF = 1.13 ≥ 0.85)

## 議論を呼ぶ Reject — fib_reversal max DD% アーティファクト疑念

`fib_reversal × EUR_USD 1m` は統計的には **極めて強い**:
- N=101 (≥3x sr_channel_reversal)
- PF=3.150 (highest among 4)
- Bonferroni p=0.000159 (most significant)
- OOS PF=4.956 (huge improvement over IS=2.157)

しかし **max DD% = 220.96%** で Reject。max DD pip は **2.98 pip だけ** (sr_channel_reversal と同等)。比率は max DD / running peak で計算され、1m TF の peak (~1.35p) が小さくアーティファクト的に高くなっている可能性。

memory `feedback_label_empirical_audit` 規律で pre-reg LOCK は変更不可、観測 BT 数値で緩めることはしない。ただし **max DD% metric 定義レビュー** の Rule 3 task の余地あり (将来検討)。

## bb_squeeze_breakout 注目

WR 75% / PF 4.87 / EV +0.91 だが N=24 (gap_to_30=6)。Bonferroni p=0.000232 で K=4 でも有意。**365日延長 で N≥30 達成すれば Promote 候補化**見込。次の A2-alt2 task で再評価可能。

## Roadmap impact

Gate 1 unlock 候補 1 件確定 → 月利100% ロードマップの Scalp 枝が**初めて statistical evidence を伴って候補化**。

ただし重要な caveat:
- **Gate 0 が崩壊状態** (R2 TRUE_LIVE で raw Kelly -0.003, MC60d=86.5%)
- sr_channel_reversal の Live 追加で aggregate Kelly が **微改善** expected (positive EV +0.373p) だが、Gate 0 危機を直接解消はしない
- 安全な順序: Gate 0 救済 (R2 TRUE_LIVE 14-cell demote PR) → sr_channel_reversal A3-simple register (lot=0.1)

## Next task

`A3-simple-sr-channel-reversal-shadow-register-2026-05-03`:
- `app.py` の `QUALIFIED_TYPES` に `sr_channel_reversal` × EUR_USD 5m の cell 単位許可を追加 (lot=0.1 SHADOW 段階)
- `tier-master.md` を更新 (PAIR_PROMOTED 表記)
- monitoring 設計 (N≥30 Live で Wilson_lo 検査、failure 時 SHADOW 降格)
- **Gate 0 救済 PR 後に merge** (順序を spec に明記)

## OOS が IS より良い 1m fib に関する追加メモ

`fib_reversal × EUR_USD 1m` で OOS PF (4.956) > IS PF (2.157) は **逆転 overfit パターンの否定**として強い。直近 2026-01-21 以降の 51 trades で WR 68.6% / EV +0.502p — 最近のレジームに適合した edge を持っている。max DD% 規定は守りつつ、別 cell (例: 同戦略 5m TF 検証) で再評価する価値あり。
