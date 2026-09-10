# price_shock_rev_eur_gbp_h1_long

## Status: PAIR_PROMOTED (EUR_GBP)

**Tier**: Tier 2 — Live MIN lot 1000u 固定 (Kelly half / DD multiplier / lot ramp bypass) | **Activation**: 2026-05-18 [[price-shock-rev-live-activation-2026-05-18]]

## 🔴 Live 実績 (post-cutoff 2026-04-08〜, is_shadow=0) — 2026-08-23 初計上
| N | W/L | WR | PnL | Mean/trade | Wilson_lo | DSR |
|---|---|---|---|---|---|---|
| **3** | **0W/3L** | **0.0%** | **−9.8 pip** | −3.27 | 0.0 | insufficient (n<閾値) |

**live デビューで 0勝3敗。** 確認済み OANDA fill (audit limit=800、いずれも EUR_GBP BUY 1000u、real trade id 付き = false-sent ではない):
- **#681143** — 2026-08-20 07:41:37 UTC
- **#700421** — 2026-08-20 12:59:23 UTC
- **#709529** — 2026-08-21 11:39:53 UTC

`sent` 行は戦略名、`filled` 行は mode 名 `daytrade_1h_eurgbp` (twin-meaning)。

### BT との乖離
| | BT (12.3y MASSIVE, commit 63c7cf18) | Live (2026-08-23) |
|---|---|---|
| N | 239 | 3 |
| WR | 72.8% | **0.0%** |
| EV/trade | **+55.81 pip** | **−3.27 pip** |
| PF | 14.75 | n/a (0 wins) |

N=3 は統計的に何も否定しない (WR 0/3 は WR 72.8% 下でも p≈0.02 で起こりうる) が、**方向は sibling の [[price-shock-rev-aud-jpy-h1-long]] (N=2, −122.6 pip, mean −61.3, BT EV +32.25) と一致している** — Price-Shock family の 2 セルが同時に「BT で大きく正、live で負」を示している。

### LOCK 基準に対する現在地
- 棄却基準「N=15 で Wilson_lo<0.40 → deactivate」: **N=3/15 — 未達、自動発火なし**
- 棄却基準「2 週連続 EV<0 → 緊急 review」: live 履歴が 2 日しかなく **未評価**
- watchdog (`tools/price_shock_rev_live_watchdog.py`) の auto-demote は **Live N>=10 かつ EV<0** — **N=3 で未発火**
- ⇒ **本 run では demote を執行していない。** ただし AUD_JPY sibling と合わせ、セル単位ではなく **family 単位の判断** を user 決裁に上げている ([[2026-08-23]])

> ⚠️ 下記「現況 (2026-06-08 再監査)」の「運用は強制 Shadow track」「Live track N=0 表示は正常」の記述は **2026-08-20 以降 stale** — 本セルは実際に live fill を出している (Tier 2 / MIN lot 1000u、2026-05-18 activation の通り)。

## 概要
H1 EUR_GBP で 252-bar log return 1%-tile 以下の negative shock が発生し、vol20 が top quintile (Q5) の場合に 3 bars 保有の LONG mean reversion。

## BT 結果 (commit 63c7cf18)
- N = 239, WR = 72.8%, Wilson_lo (95%) = 0.668, PF = 14.75, EV ≈ 55.81 pip
- 期間: data/cache/massive/EUR_GBP_1h.parquet 全期間 (12.3y MASSIVE)
- Cell ID: EUR_GBP_H1_LONG_SHOCK_1_3_Q5
- Family 品質: Wilson_lo >= 0.58 が 5/5 strategy、Bonferroni passing cells 9-28/family (Shadow-first 緩和の根拠)

## 現況 (2026-06-08 再監査)
- HourlyEngine 登録済、`daytrade_1h_*` モード経由で毎 H1 バー評価中 — 正常稼働 ([[price-shock-promote-readiness-2026-06-08]])
- 1%-tile shock は bar の ~0.33% でしか発火しない rare-event 設計。N>=30/cell 到達には数ヶ月の Shadow 蓄積が必要 (quick revival lever なし)
- Shadow 実績 (sentinel by_type all-time, 2026-06-08 時点): N=1 (-4.5p)
- 運用は強制 Shadow track。promote evaluator (`tools/price_shock_rev_promote_evaluator.py`) は Live track (is_shadow=0) 専用のため N=0 表示は正常
- Watchdog: `tools/price_shock_rev_live_watchdog.py` (4h 毎; Live N>=10 で EV<0 または Wilson_lo<0.40 → auto demote → `data/price_shock_rev_auto_demotions.json` 記録 + runtime gate 遮断)

## 思想
Qiita「予測を捨て、分布を読め」(tikeda123) の方法論。
極端な負 shock + 高 vol regime は overshoot しやすく、短期 mean reversion edge を持つ。
EUR_GBP は range-bound major で reversion 効きが強い。

## エントリー
- Bar 確定時に log_return <= 252-bar rolling 1%-tile (当該 bar 除外) AND vol_quintile == Q5
- 次 bar open で BUY

## Exit
- 3 bars 経過後の close で必ず close (horizon exit)
- または -2 x ATR近似 SL hit (catastrophic stop)

## Promote / Demote 基準 (LOCK)
- Lot ramp 提案 (全 pass 必須、司令塔承認まで MIN lot 維持): Live N>=30 + Wilson_lo>=0.50 + Bonferroni m=5 p<0.01 + 6 週連続 EV>0 ([[price-shock-rev-promote-criteria-2026-05-18]])
- 棄却: N=15 で Wilson_lo<0.40 → deactivate / 2 週連続 EV<0 → 緊急 review / catastrophic SL 比率 >30% → 構造再検討
- Post-hoc tune 禁止: percentile / horizon / vol_q は Tier 1 確定時 literal から変更不可 (変更は新 family として別 task)
- **Cross-pair 制約**: EUR_AUD ([[price-shock-rev-eur-aud-h1-long]]) と shared lock — 同時 active position 1 個まで

## 関連
- 実装: `strategies/hourly/price_shock_rev_eur_gbp_h1_long.py` (base: `price_shock_reversion_base.py`, percentile=0.01 / horizon=3 / vol_q=Q5)
- BT runner: tools/price_shock_reversion_bt.py
- Grid report: reports/price_shock_reversion_grid/shadow_promote_shortlist.md
- TradingView Pine overlay: `bt-results/tv-overlays/price_shock_rev_eur_gbp_h1_long.pine` (Pine v6; signal-equivalent to BT runner via `tests/test_pine_overlay_equivalence.py`)
