# price_shock_rev_aud_jpy_h1_long

## 概要
H1 AUD_JPY で 252-bar log return 1%-tile 以下の negative shock が発生した場合に、vol bucket を無視して 12 bars 保有の LONG mean reversion。

## BT 結果 (commit 63c7cf18)
- N = 426, WR = 63.8%, Wilson_lo (95%) = 0.592, PF = 2.54, EV ≈ 32.25 pip
- 期間: data/cache/massive/AUD_JPY_1h.parquet 全期間
- Cell ID: AUD_JPY_H1_LONG_SHOCK_1_12_ALL

## 思想
Qiita「予測を捨て、分布を読め」(tikeda123) の方法論。
極端な負 shock は overshoot しやすく、短期 mean reversion edge を持つ。

## エントリー
- Bar 確定時に log_return <= 252-bar rolling 1%-tile (当該 bar 除外)
- 次 bar open で BUY

## Exit
- 12 bars 経過後の close で必ず close (horizon exit)
- または -2 x ATR近似 SL hit (catastrophic stop)

## Tier 状態
- 2026-05-18 から Phase B-1 Shadow (is_shadow=True 固定)
- Live promote 基準: `wiki/decisions/price-shock-rev-promote-criteria-2026-05-18.md`

## 関連
- BT runner: tools/price_shock_reversion_bt.py
- Grid report: reports/price_shock_reversion_grid/shadow_promote_shortlist.md
