# Sunday open 実スプレッド実測 — weekend_gap family #3 R1 step (i) (2026-10-31)

**目的**: OOS confirm gate (c) の stressed friction 仮定 (通常 RT x3) を OANDA live feed の歴史 BA candle 実測で検証・置換する ([[weekend-gap-oos-prereg-2026-07-24]] §9 R1 手続き 1)。
**測定**: 直近 12 週末 (2026-08-09 〜 2026-10-25) x EUR_USD/USD_JPY/AUD_USD、M1 price=BA、spread = ask.o − bid.o、RT = spread + slippage 0.5p (KB friction table 準拠)。
**read-only**: GET candles のみ。live 変更ゼロ。

## サマリ表 (spread は pips、p50 = 週末横断中央値)

| pair | 通常RT(凍結) | 火曜実測 spread p50 | 実測通常RT | 3xRT仮定 | 初バー spread p50/p90 | +15m | +30m | +1h | +2h | +4h |
|---|---|---|---|---|---|---|---|---|---|---|
| EUR_USD | 2.0p | 1.6p | 2.1p | 6.0p | 4.95/6.02 | 4.00/5.37 | 3.45/5.40 | 1.85/2.18 | 1.50/1.69 | 1.60/1.60 |
| USD_JPY | 2.14p | 1.5p | 2.0p | 6.42p | 10.00/10.00 | 8.55/10.00 | 8.65/10.00 | 2.05/2.58 | 1.65/1.89 | 1.60/1.79 |
| AUD_USD | 2.5p | 1.3p | 1.8p | 7.5p | 8.80/15.00 | 4.80/10.70 | 6.45/11.61 | 1.48/2.15 | 1.40/1.40 | 1.30/1.39 |

## 3x 仮定の検証 — sustained normalization (open からの分数、p50/p90 across weekends)

| pair | spread ≤ 3xRT−slip 閾値 | ≤ 1.5x通常 | ≤ 2x通常 | ≤ 3x通常 |
|---|---|---|---|---|
| EUR_USD | 0m/1m | 50m/50m | 30m/50m | 0m/10m |
| USD_JPY | 48m/50m | 52m/62m | 50m/52m | 49m/51m |
| AUD_USD | 1m/34m | 50m/59m | 50m/51m | 17m/50m |

詳細な数値 (週末別・バケット別) は JSON 成果物を参照。
