# price_shock_rev_eur_gbp_h1_long

## Status: PAIR_DEMOTED (EUR_GBP) — 2026-10-10 rule:R2 (shadow 蓄積継続、再 live 化は R1)

## 🔻 2026-10-10 R2 demote (autopilot): registry `ps-carveout-regate-post-172` の pool 条件 (prefix price_shock_rev × since 08-11 × clean live closed) **N=11 / EV −6.08p / WR 36.4% / Wilson_lo 0.152** が成立 → ps ×5 carve-out を `_PAIR_DEMOTED` へ。本セルの live 実績 (since 08-11): N 9 / 3W / WR 33.3% / −9.5p (EV −1.06p、最新 10-05 +12.9)。決裁記録 [[ps-carveout-pool-r2-demote-2026-10-10]]。MIN lot 1000u 契約・family 識別子は不変 (再 live 化時の契約)。

**Tier**: Tier 2 — Live MIN lot 1000u 固定 (Kelly half / DD multiplier / lot ramp bypass) | **Activation**: 2026-05-18 [[price-shock-rev-live-activation-2026-05-18]]

## 🟢 2026-10-05 更新 (wiki-daily): **Live N 9 / 3W / WR 33.3% / −9.5 pip** — #1062621 が +12.9 で決済、watchdog auto-demote まで**あと 1 fill**
- #1062621 (10-05 06:36:23 entry 0.84615、signal 0.84575 = drift 4.0p) → 09:36:22 horizon @0.84744 = **+12.9 pip (demo) / +¥268.98 (broker)**、符号一致 (¥20.9/pip)。MAFE favorable 14.8 / adverse 3.0
- ON_FILL bracket: SL 0.83972 (−64.3p) / broker TP 0.89490 (+487.5p) = demo TP 0.90358 × 0.85。`[SLTP_CONSTRUCT] sl=preserve clamp=none lowliq=0 fastsl=0 ct=0 rn=1 mtf_tp=1.0 range_tp=0 decl_sl_p=57.8 sl_p=64.3 decl_tp_p=578.3 tp_p=574.3 entry_drift_p=4.0` — `rn=1` (丸め分岐) が初出、SL が宣言より 6.5p 広い (10-01 fill は +1.0p) のは drift 4.0 + 丸め。storm なし、`storm_guard` 未登録 (replacement 0 本 = guard 経路を一度も通らない)
- Wilson 12.1 / BF 6.4、wf_h1 −1.7 / wf_h2 −0.54、`promo_ev` −1.06。LOCK 棄却 (N=15 ∧ Wilson_lo<0.40) まで **9/15**、watchdog auto-demote (N≥10 ∧ EV<0) まで **9/10 — 次の 1 fill が +9.5 未満なら自動発火**。family 判断 (AUD_JPY sibling N 4 / −180.0 / `enabled: true`) は未決のまま
- 30d risk の EUR_GBP n=5 / **−2.7** (−12.6 から改善 = +12.9 入 / +3.0 窓落ち)、相関 flag EUR_GBP↔carry_dip −0.6567 (n 5×10)
- 詳細 [[2026-10-05]] 発見 3

## 🔴 2026-10-02 更新 (wiki-daily): **Live N 8 / 2W / WR 25.0% / −22.4 pip** — #950030 (10-01 fill) が −12.5 で決済
- #950030 (10-01 14:49:51 entry 0.85224 broker / 0.85227 demo、slippage 1.0p) → 17:49:55 horizon @0.85102 = **−12.5 pip (demo) / −¥254.52 (broker)**、符号一致 (¥20.4/pip)。MAFE favorable 5.0 / adverse 17.1 ⇒ 3 bar 中ほぼ一方向に逆行
- ON_FILL bracket: SL 0.84729 (−49.5p) / broker TP 0.89367 (+414p) = demo TP 0.90100 (+487p) × 0.85 quick-harvest。`[SLTP_CONSTRUCT] sl=preserve clamp=none lowliq=0 fastsl=0 ct=0 rn=0 mtf_tp=1.0 range_tp=0 decl_sl_p=48.8 sl_p=49.8 decl_tp_p=488.3 tp_p=487.3 entry_drift_p=1.0` + `[BROKER_TP] basis=qh mult=0.85 tp_p=414.0` = 09-26 計装の初 live 読み出し、宣言 SL/TP が `_1H_PRESERVE_SLTP` で保持されている (差分は entry drift 1.0p のみ)。storm なし (SL order 1 本のみ)、`storm_guard.trades` に `b92eed57-1b0` として登録 (sent_total 0)
- Wilson 7.1 / BF 3.5、wf_h1 −1.7 / wf_h2 −3.9、`promo_ev` −2.8。LOCK 棄却 (N=15 で Wilson_lo<0.40) まで **8/15**、watchdog auto-demote (N≥10 ∧ EV<0) まで **8/10** — あと 2 fill で自動発火圏。09-29→10-01 の 3 日で 4 fill (1W/3L)
- 30d risk の EUR_GBP は n=5 / −12.6 (10-01 の −0.1 から悪化)、strategy DSR n=5 Sharpe −0.343。10-02 は新規 fill なし
- 詳細 [[2026-10-02]]

## 🟡 2026-10-01 更新 (wiki-daily): **Live N 7 / 2W / WR 28.6% / −9.9 pip** — #950010 が +5.5 で決済
- #950010 (09-30 10:33:28 entry 0.85416) → 13:33:27 horizon @0.85471 = **+5.5 pip / +¥114.43** (demo↔broker 符号一致)
- Wilson 8.2 / BF 4.1、wf_h1 −3.27 / wf_h2 −0.02。LOCK 棄却 (N=15 で Wilson_lo<0.40) まで **7/15**。watchdog auto-demote (N≥10 ∧ EV<0) 未到達
- 30d risk の EUR_GBP は n=4 / −0.1 (ほぼ均衡)。10-01 は新規 fill なし
- 詳細 [[2026-10-01]]

## 🔴 2026-09-30 更新 (wiki-daily): **Live N 6 / 1W / WR 16.7% / −15.4 pip** — 1 日で 3 fill

| broker id | entry (UTC) | entry | exit | demo | broker |
|---|---|---|---|---|---|
| #948643 | 09-29 16:48:23 | 0.85715 | 19:48:28 horizon @0.85699 | −1.6 | −¥33.36 |
| #950002 | 09-30 07:24:47 | 0.85508 | 10:24:47 horizon @0.85438 | −7.0 | −¥146.34 |
| #950010 | 09-30 10:33:28 | 0.85416 | **OPEN** (12:01Z 時点) | — | — |

- demo↔broker 符号一致 (¥20.9/pip)。両決済とも 3-bar horizon exit (catastrophic SL 未到達) ⇒ **catastrophic SL 比率 0%** (棄却基準 >30% に非該当)
- stats: N **6** / Wilson_lo 3.0 / wf_h1 −3.27 → wf_h2 −1.87。LOCK 棄却基準「N=15 で Wilson_lo<0.40」は **6/15**、watchdog (N≥10 ∧ EV<0) 未発火。BT EV +55.81 に対し live mean −2.57
- #950002 決済 9 分後に #950010 を再エントリー (同方向、7.0p 下)。shared lock (同時 1 position) の範囲内
- 詳細 [[2026-09-30]]

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
