# trend_rebound THESIS_INVALID — 2026-05-18

## Decision

`trend_rebound` を FORCE_DEMOTED に固定する。`trend_rebound` x `USD_JPY`
の PAIR_PROMOTED は削除し、`trend_rebound` x `EUR_USD` の PAIR_DEMOTED
も FORCE_DEMOTED への一括化により削除する。

戦略ファイル本体 (`strategies/scalp/trend_rebound.py`) は削除しない。
Shadow 観測と将来の別 thesis 検証用に保持するが、現行設計の OANDA Live
転送は全ペア停止する。

## C Audit Verdict

Source: [[../sessions/prime-v2-shadow-audit-2026-05-18]] §trend_rebound

| Axis | Value | Verdict |
|---|---:|---|
| Shadow N (21d) | 60 | PASS N |
| WR | 33.3% | FAIL |
| spread-adj EV | -1.29p | FAIL |
| PF | 0.66 | FAIL |
| Kelly | 0.000 | FAIL |
| WF (3-fold) | 0/3 | FAIL |
| best cell (ATRQ2) | N=12 WR=50% EV=+0.05p | no edge |
| last emit | 2026-05-12 14:14 | 6d no fire |

Verdict: **THESIS_INVALID**. 設計の核である「強トレンド時の
Stoch/RSI/BB%B 極端値 + 反転足」は、21d shadow N=60 で edge 不在。
WF 3-fold が 0/3 のため時間軸 reproducibility もない。

## Implementation

- `DemoTrader._FORCE_DEMOTED` に `trend_rebound` を追加。
- `DemoTrader._PAIR_PROMOTED` から `("trend_rebound", "USD_JPY")` を削除。
- `DemoTrader._PAIR_DEMOTED` から `("trend_rebound", "EUR_USD")` を削除。
- `tests/test_trend_rebound_demote.py` で FORCE_DEMOTED 収容と pair-level
  指定撤去を固定。

## Rationale

2026-05-07 の USD_JPY PAIR_PROMOTED は shadow N=17 EV=+1.14 PF=1.52
に基づく small-N exception だった。2026-05-18 時点の C audit では
N=60 まで増えた結果 EV=-1.29p、PF=0.66、Kelly=0.000 に decay しており、
small-N curve-fit と判断する。

EUR_USD の PAIR_DEMOTED は FORCE_DEMOTED と重複し、優先順位の読み違いを
生むため撤去する。

## Scope Lock

Out of scope:
- `strategies/scalp/trend_rebound.py` の削除
- 他戦略への demote / promote 波及
- 現行 thesis の redesign
