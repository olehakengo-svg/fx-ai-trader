# BT vs Live Divergence Analysis

## 25pp乖離の根本原因（bb_rsi: BT 61.3% → Live 36.4%）

| 原因 | 推定寄与 | 方向 |
|------|---------|------|
| SIGNAL_REVERSE再計算間隔 (BT 3bar vs Live 30s) | **-5pp** | BT楽観 |
| BB_mid TP override (RANGE, Live実装済みBT未実装) | **-4pp** | BT楽観 |
| Spread variability (BT固定 vs Live変動) | **-4pp** | BT楽観 |
| Entry friction (BT next-bar-open vs Live real-time ask) | **-3pp** | BT楽観 |
| OANDA Quick-Harvest TP×0.85 | **-2pp** | BT楽観 |
| HTF/Layer1 hard filter | **-2pp** | BT楽観 |
| **合計推定** | **-20pp** | |
| **未説明** | **-5pp** | Execution spikes / SL hunting |

## 摩擦比率の決定的差異

```
Scalp 1m: friction/ATR = 36.3% (USD_JPY) → Live 5.4倍
DT 15m:   friction/ATR = 6.7%  (USD_JPY)
```

## BT改善の優先順位
1. **Dynamic Spread Model** — 時間帯別spread (Asia 0.8pip, London 0.3pip)
2. **SIGNAL_REVERSE 1bar周期化** — BT 3bar→1bar (Live 30s相当)
3. **Instant Death Detection** — bar-level MFE=0判定強化
4. **RANGE TP Override移植** — v6.5 BB_mid TPをBTに反映

## Related
- [[bb-rsi-reversion]]
- [[friction-analysis]]
- [[lessons/index]]
