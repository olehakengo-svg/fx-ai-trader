# wick_imbalance_reversion

## Status: PAIR_DEMOTED (GBP_USD, 2026-07-07 rule:R2) / Shadow 継続 (全ペア)

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

## Significance (2026-04-17, 6-cell multi-correction)
| Pair | p (WR>50, 1-sided) | Bonferroni α'=0.0083 | BH q=0.10 |
|------|--------------------|----------------------|-----------|
| GBP_USD | 0.0089 | ·（ギリギリ落ち） | **✓ 生存** |
| USD_JPY | 0.649 | · | · |
| EUR_USD | 0.500 | · | · |

GBP_USD は BH-FDR を通過 — 本BTスキャン9セル中で唯一の生存セル。ただし Bonferroni は p=0.0089 vs 0.0083 でほぼ境界、Live N≥30 での再確認が必須。

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

## 2026-07-02 E10 code-level DISABLE (rule:R2)
Edge cell E10 (GBP_USD force-live) を `DISABLED_CELLS` に追加。30d live via E10: N=9 WR=22.2% **-52.5pip**。pre-reg forensic 2026-06-22 が同セルを dominant loser と特定済み (9/9負けが d1∈{0,-1} = knife-catch)。非セルの PAIR_PROMOTED fill (30d n=3 +5.6p) は維持。後継は D1-gated continuation 変種 ([[wick-imbalance-gbpusd-continuation-pre-reg-2026-06-22]]) が R1 パイプラインで別途。詳細: [[live-bleeder-demotions-2026-07-02]]

## 2026-07-07 GBP_USD PAIR_PROMOTED 除去 → _PAIR_DEMOTED (rule:R2, v2.3 WS1 T1)
`(wick_imbalance_reversion, GBP_USD)` を `_PAIR_PROMOTED` から除去し `_PAIR_DEMOTED` へ。30d clean live **N=12 WR=41.7% EV=-3.91 -46.9pip** (Wilson_lo 19.3% < BEV 37.9%、all-time live N=14 -63.0p)。07-02 の E10 DISABLE 時点で維持した非セル PAIR_PROMOTED 経路 (当時 n=3 +5.6p) がその後 -46.9p まで出血拡大。live 発火は全期間 100% BUY のため pair 粒度 demote = BUY セル閉鎖と等価。負け 7 件中 6 件が MFE≈0 の premise 即死型。昇格根拠 365d BT (N=40 WR=70.0% EV=+0.123) を live が反証 — [[bt-live-divergence]] 型。Shadow 継続 (原則3)。再昇格は R1 のみ。詳細: [[payoff-asymmetry-diagnosis-2026-07-07]] §7、pin: `tests/test_t1_wick_gbpusd_demote_pin.py`
