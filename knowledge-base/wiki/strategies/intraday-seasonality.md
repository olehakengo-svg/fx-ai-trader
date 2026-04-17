# intraday_seasonality

## Status: FORCE_DEMOTED (Shadow only)

曜日×時間帯ごとのリターン分布にt検定と効果量フィルタを掛け、統計的に有意な日中季節性の方向にエントリーする戦略。

## Hypothesis
FX各1時間バーのリターンは曜日×時刻に固有の偏りを持ち（LP在庫管理＋機関フロー集中）、少なくとも短期的に持続する。

## Academic Backing
- Breedon & Ranaldo (2013) "Intraday patterns in FX returns and order flow"
- Cornett et al. (2007) "Seasonality in stock returns and volatility"

## Signal logic
```python
# 1. 現在バーの weekday / hour を取得（週末除外）
# 2. 過去 hist (iloc[:-1]) から同一 dow × hour のバーを抽出
#    → 直近 lookback_days サンプルに限定、最低 N=8
# 3. returns = (Close - Open) / Open
# 4. t = mean / (std / sqrt(n));  |t| >= 2.0 (~ p<0.05)
# 5. Cohen's d = |mean| / std;    d >= min_effect_size
# 6. HTF agreement と方向が矛盾しない
# → signal = BUY if mean > 0 else SELL
```

## Parameters
| Name | Default | Role |
|------|---------|------|
| lookback_days | 60 | 季節性計算の遡及日数（サンプル数上限） |
| min_effect_size | 0.3 | Cohen's d 最低閾値 |

閾値 `|t| >= 2.0` と最低 N=8 はハードコード。

## Risk / Exit
- SL: `entry ± 1.5 × ATR`
- TP: `1.5 + cohens_d` ATR、上限 2.5 ATR

## 365d BT (2026-04-17, 15m, daytrade)
| Pair | N | WR | EV | PF |
|------|---|----|----|----|
| USD_JPY | 80 | 57.5% | -0.109 | 0.99 |
| EUR_USD | 47 | 53.2% | -0.144 | 0.94 |
| GBP_USD | 61 | 62.3% | +0.037 | 1.25 |

USD_JPY/EUR_USD は負EV、GBP_USD のみ正だがマージナル。Shadow継続でサンプル蓄積が必要。

## Significance (2026-04-17, 6-cell multi-correction)
| Pair | p (WR>50, 1-sided) | Bonferroni α'=0.0083 | BH q=0.10 |
|------|--------------------|----------------------|-----------|
| GBP_USD | 0.037 | · | · |
| USD_JPY | 0.109 | · | · |
| EUR_USD | 0.385 | · | · |

全ペアが Bonferroni/BH を通過しない。GBP_USD の単純 p=0.037 は 5% 閾値を通るが、3ペア多重補正で消失。FORCE_DEMOTED妥当。Live観測でサンプル積み増し後に再評価。

## Filters / Guards
- `len(df) >= 200`、`hist >= 100`
- `ctx.atr > 0`、週末 (`dow > 4`) 除外
- look-ahead防止: 現バー (iloc[-1]) のリターンは分布計算に含めない
- HTF Hard Block (v9.1)

## Scoring
`base=5.0` + t統計量ボーナス + 効果量ボーナス + サンプル数ボーナス、confidence = min(85, 50+score×3)

## Related
- [[session-time-bias]] — 時刻ベースの姉妹戦略（ELITE_LIVE）
- [[gotobi-fix]]
- [[tier-master]]
