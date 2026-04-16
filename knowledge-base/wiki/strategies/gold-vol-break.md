# Gold Vol Break

## Overview
- **Entry Type**: `gold_vol_break`
- **Mode**: daytrade
- **Status**: See [[index]] for current tier
- **Module**: `strategies/daytrade/gold_vol_break.py`

## Logic
XAU/USD専用デイトレード戦略。15分足でBB(2.5σ)をATR急増を伴って突破した瞬間に追随する。ADX>=20と実体サイズフィルターで偽ブレイクを排除し、TP=ATR7x3.0 / SL=ATR7x1.0の高RR(1:3)で金のボラティリティクラスタリングを捕捉する。

## Performance
- BT/Live data TBD — pending clean data accumulation from 2026-04-16

## Related
- [[index]] — Tier classification
