# Regime Classifier Consensus Summary

**Recommendation: A**

現行 `dow_regime` tagging は継続。ただし 17 proposals は未検証 hypothesis として Shadow 観測に限定し、Dow classifier を v2 の代替 SSOT にしない。

## Evidence

- B2.5 trade log: N=5617, proposals=17
- v2 recalibration N>=30 cells: 7
- B2.5 trades retagged by M15 v2: moderate_trend=805, no_go=4812
- v2 replay candidate rows: 24 / 34

## Decision

A が最も損失関数に合う。Dow の探索価値は残し、v2 の実測 prior も捨てない。B/C/D は現時点ではいずれも過剰反応。

## Next Task

Phase E を `Shadow-only competing-classifier validation` として再定義し、`entry_type × dow_regime × v2_regime` の同一 forward window 比較を pre-register する。
