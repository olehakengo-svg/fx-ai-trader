# Session Vol Expansion

## Overview
- **Entry Type**: `session_vol_expansion`
- **Mode**: scalp
- **Status**: See [[index]] for current tier
- **Module**: `strategies/scalp/session_vol_expansion.py`

## Logic
EUR/USD専用ロンドンオープン圧縮ブレイクアウト戦略。アジアセッション中のボラティリティ圧縮(直近30本/基準60本<=0.6)を検出し、ロンドンオープン直後(UTC 07:00-08:30)のレンジブレイクにエントリーする。15分足EMA方向確認、OANDAリアルスプレッド<=0.5pipハードフィルター適用。TP=ATR14x3.0。

## Performance
- BT/Live data TBD — pending clean data accumulation from 2026-04-16

## Related
- [[index]] — Tier classification
