# Gold Pips Hunter

## Overview
- **Entry Type**: `gold_pips_hunter`
- **Mode**: scalp
- **Status**: See [[index]] for current tier
- **Module**: `strategies/scalp/gold_pips.py`

## Logic
XAU/USD専用1分足スキャルプ。5分足のトレンド方向を判定し、1分足で包み足パターンが出現した瞬間にトレンド方向へクイックエントリーする。ADX>=18 + EMA21フィルター適用。セッションはTokyo+London(UTC 0-12)限定。TP=ATR7x1.8。

## Performance
- BT/Live data TBD — pending clean data accumulation from 2026-04-16

## Related
- [[index]] — Tier classification
