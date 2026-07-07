# price_shock_rev_nzd_jpy_h1_long

## Status: PAIR_PROMOTED (NZD_JPY)

**Tier**: Tier 2 — Live MIN lot 1000u 固定 (Kelly half / DD multiplier / lot ramp bypass) | **Activation**: 2026-05-18 [[price-shock-rev-live-activation-2026-05-18]]

## 概要
H1 NZD_JPY で 252-bar log return 1%-tile 以下の negative shock が発生し、vol20 が top quintile (Q5) の場合に 12 bars 保有の LONG mean reversion。

## BT 結果 (commit 63c7cf18)
- N = 303, WR = 64.0%, Wilson_lo (95%) = 0.585, PF = 5.02, EV ≈ 58.88 pip
- 期間: data/cache/massive/NZD_JPY_1h.parquet 全期間 (12.3y MASSIVE)
- Cell ID: NZD_JPY_H1_LONG_SHOCK_1_12_Q5
- Family 品質: Wilson_lo >= 0.58 が 5/5 strategy、Bonferroni passing cells 9-28/family (Shadow-first 緩和の根拠)

## 現況 (2026-06-08 再監査)
- HourlyEngine 登録済、`daytrade_1h_*` モード経由で毎 H1 バー評価中 — 正常稼働 ([[price-shock-promote-readiness-2026-06-08]])
- 1%-tile shock は bar の ~0.33% でしか発火しない rare-event 設計。N>=30/cell 到達には数ヶ月の Shadow 蓄積が必要 (quick revival lever なし)
- Shadow 実績 (sentinel by_type all-time, 2026-06-08 時点): N=1 (+54.0p)
- 運用は強制 Shadow track。promote evaluator (`tools/price_shock_rev_promote_evaluator.py`) は Live track (is_shadow=0) 専用のため N=0 表示は正常
- Watchdog: `tools/price_shock_rev_live_watchdog.py` (4h 毎; Live N>=10 で EV<0 または Wilson_lo<0.40 → auto demote → `data/price_shock_rev_auto_demotions.json` 記録 + runtime gate 遮断)

## 思想
Qiita「予測を捨て、分布を読め」(tikeda123) の方法論。
極端な負 shock + 高 vol regime は overshoot しやすく、短期 mean reversion edge を持つ。

## エントリー
- Bar 確定時に log_return <= 252-bar rolling 1%-tile (当該 bar 除外) AND vol_quintile == Q5
- 次 bar open で BUY

## Exit
- 12 bars 経過後の close で必ず close (horizon exit)
- または -2 x ATR近似 SL hit (catastrophic stop)

## Promote / Demote 基準 (LOCK)
- Lot ramp 提案 (全 pass 必須、司令塔承認まで MIN lot 維持): Live N>=30 + Wilson_lo>=0.50 + Bonferroni m=5 p<0.01 + 6 週連続 EV>0 ([[price-shock-rev-promote-criteria-2026-05-18]])
- 棄却: N=15 で Wilson_lo<0.40 → deactivate / 2 週連続 EV<0 → 緊急 review / catastrophic SL 比率 >30% → 構造再検討
- Post-hoc tune 禁止: percentile / horizon / vol_q は Tier 1 確定時 literal から変更不可 (変更は新 family として別 task)

## 関連
- 実装: `strategies/hourly/price_shock_rev_nzd_jpy_h1_long.py` (base: `price_shock_reversion_base.py`, percentile=0.01 / horizon=12 / vol_q=Q5)
- BT runner: tools/price_shock_reversion_bt.py
- Grid report: reports/price_shock_reversion_grid/shadow_promote_shortlist.md
- TradingView Pine overlay: `bt-results/tv-overlays/price_shock_rev_nzd_jpy_h1_long.pine` (Pine v6; signal-equivalent to BT runner via `tests/test_pine_overlay_equivalence.py`)
