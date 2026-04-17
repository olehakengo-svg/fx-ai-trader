# wick_imbalance_reversion

## Status: PAIR_PROMOTED (GBP_USD) / Shadow on other pairs

直近N本のヒゲ長不均衡が極端な場合、流動性プール枯渇側への反発を取る平均回帰戦略。確認バーのbody符号で反転方向を検証してからエントリーする。

## Hypothesis
ヒゲは「拒絶された価格領域」を表す。上ヒゲが過度に蓄積した状態は、その方向のストップ／アイスバーグが消化されきった合図で、反対方向への反発（MR）が起こりやすい。

## Academic Backing
- Osler (2003) "Currency orders and exchange rate dynamics" (stop-loss clustering)
- Mandelbrot (1963) "The variation of certain speculative prices"

## Signal logic
```python
# 1. 直前 window 本のヒゲ合計:
#    upper_wick = High - max(Open, Close)
#    lower_wick = min(Open, Close) - Low
# 2. WIR = (Σ upper - Σ lower) / (Σ upper + Σ lower)  # [-1, +1]
# 3. 現バー body で方向確認:
#    WIR >  threshold AND body < 0 → SELL
#    WIR < -threshold AND body > 0 → BUY
# 4. |body| >= 0.05 ATR、bb_width_pct >= 0.15
# 5. HTF agreement と矛盾しない
```

## Parameters
| Name | Default | Role |
|------|---------|------|
| window | 8 | ヒゲ集計本数 |
| threshold | 0.45 | WIR絶対値閾値 |

## Risk / Exit
- SL: `entry ± 1.5 × ATR`
- TP: `1.2 + |WIR| × 2.0` ATR、上限 2.5 ATR

## 365d BT (2026-04-17, 15m, daytrade)
| Pair | N | WR | EV | PF |
|------|---|----|----|----|
| USD_JPY | 27 | 48.1% | -0.370 | 0.67 |
| EUR_USD | 29 | 51.7% | -0.082 | 0.99 |
| GBP_USD | 40 | 70.0% | +0.123 | 1.44 |

GBP_USD のみ明確に正エッジ → tier-master で PAIR_PROMOTED。他ペアは負EVで Shadow。

## Filters / Guards
- `len(df) >= window + 2`、`ctx.atr > 0`
- 圧縮相場除外: `bb_width_pct >= 0.15`
- 負ヒゲガード (データ異常): `max(0.0, wick)`
- look-ahead防止: WIR は `iloc[-(w+1):-1]`、現バーは確認専用
- HTF Hard Block (v9.1)

## Scoring
`base=5.0` + WIR強度ボーナス + 確認バーbody強度、confidence = min(85, 50+score×3)

## Related
- [[fib-reversal]] — MR系、instant-death比較
- [[bb-rsi-reversion]]
- [[tier-master]]
