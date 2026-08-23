# price_shock_rev_aud_jpy_h1_long

## Status: PAIR_PROMOTED (AUD_JPY)

**Tier**: Tier 2 — Live MIN lot 1000u 固定 (Kelly half / DD multiplier / lot ramp bypass) | **Activation**: 2026-05-18 [[price-shock-rev-live-activation-2026-05-18]]

## 概要
H1 AUD_JPY で 252-bar log return 1%-tile 以下の negative shock が発生した場合に、vol bucket を無視して 12 bars 保有の LONG mean reversion。

## BT 結果 (commit 63c7cf18)
- N = 426, WR = 63.8%, Wilson_lo (95%) = 0.592, PF = 2.54, EV ≈ 32.25 pip
- 期間: data/cache/massive/AUD_JPY_1h.parquet 全期間 (12.3y MASSIVE)
- Cell ID: AUD_JPY_H1_LONG_SHOCK_1_12_ALL
- Family 品質: Wilson_lo >= 0.58 が 5/5 strategy、Bonferroni passing cells 9-28/family (Shadow-first 緩和の根拠)
- 方法論検証: Qiita 原典 AUDJPY WR=60.06% を WR=60.00% で再現

## 🔴 現況 (2026-08-20 wiki-daily) — **初の live closed fill が BT と正面衝突**

| | BT (12.3y MASSIVE, N=426) | Live (N=2, 直近 30d) |
|---|---|---|
| WR | 63.8% | 50.0% (1W/1L) |
| EV / trade | **+32.25 pip** | **−61.3 pip** |
| PnL | PF 2.54 | **−122.6 pip** |

- この 2 本が **2026-07-27→08-20 窓のポートフォリオ損失 −107.6 pip の全て**（他を合わせると +15.0 pip）。VaR95 を 13.58 → **81.31**、CVaR95 を 19.0 → **123.2** に吹き飛ばし、book の DD を **+201.1 pip の新高値 (1209.1 pip)** に押し上げた張本人。
- **demote は執行していない** — 本ページの LOCK 基準を満たしていないため:
  - 「N=15 で Wilson_lo<0.40 → deactivate」→ **N=2、未達**
  - watchdog auto-demote 「Live N≥10 で EV<0 または Wilson_lo<0.40」→ **N=2、未達**
  - ただし「**2 週連続 EV<0 → 緊急 review**」は**該当**。
- ⚠️ **判断上の論点**: N=2 は統計的に何も言えない (rare-event 設計なので当然)。しかし *1 トレードあたり −61.3 pip* という規模は、N=10 の watchdog ゲートに到達するまでに **−600 pip 規模の追加出血**を許容することを意味する。「N を貯めるコスト」がテール規模に対して見合っているかは、閾値待ちではなく **user 決裁**の対象。BT の catastrophic SL (−2×ATR) が live で意図通り効いているかの実測も併せて必要。
- 次アクション候補: (1) 2 本の per-trade forensic (entry/exit/SL 実値、horizon exit か SL_HIT か) (2) user への early-demote 提起（vix_carry_unwind 2026-08-03 と同型の手続き）。

## 現況 (2026-06-08 再監査)
- HourlyEngine 登録済、`daytrade_1h_*` モード経由で毎 H1 バー評価中 — 正常稼働 ([[price-shock-promote-readiness-2026-06-08]])
- 1%-tile shock は bar の ~0.33% でしか発火しない rare-event 設計。N>=30/cell 到達には数ヶ月の Shadow 蓄積が必要 (quick revival lever なし)
- Shadow 実績 (sentinel by_type all-time, 2026-06-08 時点): N=1 (+6.9p)
- 運用は強制 Shadow track。promote evaluator (`tools/price_shock_rev_promote_evaluator.py`) は Live track (is_shadow=0) 専用のため N=0 表示は正常
- Watchdog: `tools/price_shock_rev_live_watchdog.py` (4h 毎; Live N>=10 で EV<0 または Wilson_lo<0.40 → auto demote → `data/price_shock_rev_auto_demotions.json` 記録 + runtime gate 遮断)

## 思想
Qiita「予測を捨て、分布を読め」(tikeda123) の方法論。
極端な負 shock は overshoot しやすく、短期 mean reversion edge を持つ。

## エントリー
- Bar 確定時に log_return <= 252-bar rolling 1%-tile (当該 bar 除外)
- 次 bar open で BUY

## Exit
- 12 bars 経過後の close で必ず close (horizon exit)
- または -2 x ATR近似 SL hit (catastrophic stop)

## Promote / Demote 基準 (LOCK)
- Lot ramp 提案 (全 pass 必須、司令塔承認まで MIN lot 維持): Live N>=30 + Wilson_lo>=0.50 + Bonferroni m=5 p<0.01 + 6 週連続 EV>0 ([[price-shock-rev-promote-criteria-2026-05-18]])
- 棄却: N=15 で Wilson_lo<0.40 → deactivate / 2 週連続 EV<0 → 緊急 review / catastrophic SL 比率 >30% → 構造再検討
- Post-hoc tune 禁止: percentile / horizon / vol_q は Tier 1 確定時 literal から変更不可 (変更は新 family として別 task)

## 関連
- 実装: `strategies/hourly/price_shock_rev_aud_jpy_h1_long.py` (base: `price_shock_reversion_base.py`, percentile=0.01 / horizon=12 / vol_q=ALL)
- BT runner: tools/price_shock_reversion_bt.py
- Grid report: reports/price_shock_reversion_grid/shadow_promote_shortlist.md
- TradingView Pine overlay: `bt-results/tv-overlays/price_shock_rev_aud_jpy_h1_long.pine` (Pine v6; signal-equivalent to BT runner via `tests/test_pine_overlay_equivalence.py`)
