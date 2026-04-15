# RNB USD/JPY — Round Number Barrier

## Overview
- **Entry Type**: `rnb_usdjpy`
- **Category**: Round Number / Barrier
- **Pair**: USD_JPY
- **Mode**: rnb_usdjpy (auto_start=True, v9.0)
- **Status**: SHADOW (data collection)

## Hypothesis
USD/JPY is heavily influenced by round number levels (e.g., 150.000, 151.000). These levels act as psychological barriers where institutional order flow clusters, creating predictable bounce/break patterns.

## Signal Logic
Detects proximity to round number barriers on USD_JPY and generates signals based on price behavior at these levels. Evaluates whether price is likely to bounce off or break through the round number, using order flow indicators and recent price action.

## Configuration
- **auto_start**: True
- **Pair**: USD_JPY only
- **Lot**: default (sentinel)

## BT Performance
BT data not yet available. Data collection phase.

## Live Performance
No live trades recorded yet. Monitoring for initial signal generation.

## Related
- [[index]] — Tier classification
- [[system-reference]] — Mode details
