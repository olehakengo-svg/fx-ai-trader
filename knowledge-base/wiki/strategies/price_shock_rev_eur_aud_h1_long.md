# price_shock_rev_eur_aud_h1_long

- **Status**: FORCE_DEMOTED / Phase B-1 Shadow-only (2026-05-18)

## 概要
H1 EUR_AUD で 252-bar log return 1%-tile 以下の negative shock が発生し、vol20 が top quintile (Q5) の場合に 12 bars 保有の LONG mean reversion。

## BT 結果 (commit 63c7cf18)
- N = 262, WR = 67.6%, Wilson_lo (95%) = 0.617, PF = 4.05, EV ≈ 58.77 pip
- 期間: data/cache/massive/EUR_AUD_1h.parquet 全期間
- Cell ID: EUR_AUD_H1_LONG_SHOCK_1_12_Q5

## 思想
Qiita「予測を捨て、分布を読め」(tikeda123) の方法論。
極端な負 shock + 高 vol regime は overshoot しやすく、短期 mean reversion edge を持つ。

## エントリー
- Bar 確定時に log_return <= 252-bar rolling 1%-tile (当該 bar 除外) AND vol_quintile == Q5
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
- TradingView Pine overlay: `bt-results/tv-overlays/price_shock_rev_eur_aud_h1_long.pine` (Pine v6; signal-equivalent to BT runner via `tests/test_pine_overlay_equivalence.py`)
