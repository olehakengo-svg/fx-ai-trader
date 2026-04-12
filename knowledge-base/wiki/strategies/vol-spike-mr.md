# Vol Spike MR — ボラティリティスパイク平均回帰

## Stage: BACKTESTED → SENTINEL

## Hypothesis
直近5本平均レンジの3倍以上の急拡大バー（Vol Spike）は、ストップハンティングによる
一時的な過剰反応であり、3-4bar（45-60min）で平均回帰する。USD_JPYでのみ有効。

## BT Results (60d, 15m, SL/TP/friction込み)
| Pair | N | WR | PnL | PF | Sharpe | EV/t |
|------|---|-----|-----|-----|--------|------|
| **USD_JPY** | **53** | **62.3%** | **+242.2pip** | **1.92** | **0.274** | **+4.57pip** |
| EUR_USD | 92 | 47.8% | -19.8pip | 0.95 | -0.023 | -0.22 |
| GBP_USD | 84 | 42.9% | -140.4pip | 0.69 | -0.158 | -1.67 |

**PF=1.92は本システム全戦略中最高。**

## Logic
```python
# spike detection: current bar range > 3x 5-bar average
avg_range = mean(High-Low for last 5 bars)
if current_range > avg_range * 3.0:
    spike_dir = "UP" if Close > Open else "DOWN"
    # FADE the spike (enter opposite)
    signal = "BUY" if spike_dir == "DOWN" else "SELL"
    # SL: spike extreme + ATR * 0.3
    # TP: ATR * 1.5
```

## Why JPY Only
BOJ/日銀の介入示唆とキャリートレードのストップハンティングが大足を作り、
SL約定後に急速に回帰する構造。EUR/GBPでは大足がトレンド継続の「本物のブレイク」
である確率が高い。

## Academic Backing
- Osler (2003): SL注文の流動性プール利用 → sweep後の回帰
- Lo & MacKinlay (1988): 短期リバーサル効果

## 月利100%目標への寄与
+4pip/日 → DD防御0.5x到達を数日加速

## Related
- [[microstructure-stop-hunting]]
- [[bb-rsi-reversion]] (MR戦略同士の相関確認要)
- [[roadmap-to-100pct]]
