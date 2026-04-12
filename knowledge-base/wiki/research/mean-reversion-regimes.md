# Mean-Reversion Regimes — 研究テーマ

## 研究課題
レジーム（RANGE/TREND/HIGH_VOL）によるMR戦略の有効性変化。

## 知見
- RANGE regime = 47.5% of trades, WR = 31.2%（最悪レジーム）
- WIDE_RANGE (bb_width_pct>=10, ADX<20) がMR最適環境
- SQUEEZE (bb_width_pct<10) ではMR逆張りは自殺行為

## 実装
- Range Sub-classification: SQUEEZE/WIDE_RANGE/TRANSITION
- SQUEEZE → MRブロック, WIDE_RANGE → スコアブースト
- 詳細: [[system-reference]]

## Related
- [[session-effects]]
- [[microstructure-stop-hunting]]
