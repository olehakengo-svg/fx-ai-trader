# DESIGN_BROKEN Redesign Proposal (2026-05-18)

Source: Render `/api/demo/trades?limit=10000`, fetched 2026-05-18. Clean slice = `is_shadow=1`, `status=CLOSED`, `outcome in (WIN, LOSS)`, `dedup_violation=0`, non-XAU. MAFE/MFE are computed from `entry_price`, not `signal_price`.

## Strategy 1: dt_sr_channel_reversal

### Code path summary
- TP/SL: legacy path uses **TP=2.0 ATR7 / SL=1.0 ATR7** for both BUY and SELL, then Daytrade execution can enforce a 5.0p minimum SL. Observed clean shadow geometry: avg SL **10.8p**, avg TP **21.9p**, median RR **1.73**, median BE_WR **36.6%**.
- Direction filter: both BUY and SELL. BUY requires SR/channel lower-side proximity, `RSI<45`, and `MACD-H > prev`; SELL requires upper-side proximity, `RSI>55`, and `MACD-H < prev`. HTF hard block prevents BUY in bear and SELL in bull.
- Session: strategy code has no hard session filter. Daytrade modes are effectively 24h for FX; runtime only applies `active_hours_utc` where the specific mode defines it. The signal function gives overlap a score bonus and off-session a score haircut, not a hard block.
- Entry: legacy path reads `ctx.entry` / latest `df.iloc[-1]` from `compute_daytrade_signal`, so production legacy signals are intrabar/current-bar. A gated redesign path exists behind `DT_SR_CHANNEL_REDESIGN_V2=1` and uses closed signal bar `df.iloc[-2]` with next-bar execution, but this task does not enable it.
- Exit: normal SL/TP in `_sltp_loop`, plus `SIGNAL_REVERSE`, `MAX_HOLD_TIME` at 8h for daytrade modes, `TIME_DECAY_EXIT` after half max-hold if in loss, and `WEEKEND_CLOSE`.

### Shadow dissection (N=106)
- TP hit: **N=18** (17.0% of trades, 51.4% of wins), avg raw P/L **+16.4p**, avg spread-adj P/L **+13.1p**.
- SL hit: **N=42** (39.6% of trades), avg raw P/L **-10.6p**, avg spread-adj P/L **-14.3p**.
- Other exits: `SIGNAL_REVERSE` **N=41 WR=31.7% avg adj=-4.6p**; `MAX_HOLD_TIME` N=3 all wins avg adj=+35.4p; `TIME_DECAY_EXIT` N=1 loss; `WEEKEND_CLOSE` N=1 win.
- BUY: **N=65 WR=32.3% raw EV=-1.14p spread-adj EV=-4.74p PF=0.39**.
- SELL: **N=41 WR=34.1% raw EV=-0.60p spread-adj EV=-3.54p PF=0.52**.
- avg MAFE: **6.7p** / avg MFE: **6.5p**. SL-hit trades have avg MAFE **10.6p** vs avg SL **10.2p**; TP-hit trades have avg MFE **16.4p** vs avg TP **16.0p**.
- Spread-adj contribution: raw EV **-0.93p** -> spread-adj EV **-4.28p**, contribution **-3.35p/trade**. Avg entry spread **1.48p**, avg abs slippage **1.87p**, contribution/spread occupancy **2.26x**.
- Session asymmetry: overlap **N=36 WR=38.9% adj EV=-0.09p PF=0.99**; london **N=37 WR=29.7% adj EV=-7.06p**; tokyo **N=22 WR=36.4% adj EV=-3.91p**; ny **N=11 WR=18.2% adj EV=-9.33p**.
- Regime near-miss: ADXQ2 **N=10 WR=60.0% adj EV=+2.32p**, but Bonferroni reject and small N.

### Gate state
| Gate | Evidence | State |
|---|---|:---:|
| N | **106** clean shadow trades | 🟢 |
| WR / Wilson | **33.0% / 0.248** | 🟠 |
| spread-adj EV | **-4.28p** | 🔴 |
| PF | **0.44** | 🔴 |
| Direction asymmetry | SELL **-3.54p** vs BUY **-4.74p** | 🔴 |
| Exit geometry | TP **18** vs SL **42**, BE_WR median **36.6%** vs WR **33.0%** | 🔴 |
| WF | **0/3** | 🔴 |

### Redesign hypotheses
1. **Closed-bar boundary reversion + ADXQ2 gate**: enable the existing closed-bar boundary design as the candidate spec (`DT_SR_CHANNEL_REDESIGN_V2` semantics), and gate to ADX quartile Q2 only. Keep both directions initially. | Reason: aggregate is broken, but ADXQ2 is the only data-backed pocket (**N=10 WR=60.0% EV=+2.32p WF=2/3**); legacy intrabar/current-bar entry is a schema-level timing risk. | Expected impact: lower N, WR target **45-55%**, spread-adj EV target **+1 to +3p**, PF target **>=1.20** if closed-bar timing removes false bounces. | BT spec: 365d x 5 FX pairs, grid `adx_q in {Q1,Q2,Q3,Q4}` x `closed_bar in {0,1}` x `boundary_sl_buffer in {1.0,1.3,1.6}` x `tp_mean_atr in {0.8,1.0,1.3}`; Bonferroni **m=72**.
2. **Overlap-only friction gate**: keep legacy thesis but restrict new samples to London/NY overlap and require projected spread-cost/TP <= 15% at signal time. | Reason: overlap is nearly break-even after spread (**N=36 EV=-0.09p PF=0.99**) while London/NY non-overlap bleeds; friction contribution is **3.35p/trade**. | Expected impact: N roughly one-third of current, WR target **40-45%**, spread-adj EV target **0 to +1.5p**, PF target **1.0-1.2**. | BT spec: grid `session in {tokyo,london,overlap,ny}` x `spread_tp_cap in {0.10,0.15,0.20}` x `direction in {BUY,SELL,BOTH}`; Bonferroni **m=36**.
3. **Early invalidation instead of full SL**: add a post-entry invalidation rule: if price fails to produce **0.3R MFE within 4 bars** or closes back through the touched boundary, exit before full SL. | Reason: `SIGNAL_REVERSE` is **N=41 avg adj=-4.6p**, and SL hits average full adverse excursion; MFE average **6.5p** is far below avg TP **21.9p**, so failed bounces should be cut earlier. | Expected impact: WR may fall or stay flat, but loss size should shrink; target spread-adj EV improvement **+2 to +4p/trade**, PF target **>=1.0**. | BT spec: grid `mfe_required_R in {0.2,0.3,0.4}` x `bars in {3,4,6}` x `boundary_close_exit in {on,off}` x `adx_gate in {none,Q2}`; Bonferroni **m=36**.

## Strategy 2: wick_imbalance_reversion

### Code path summary
- TP/SL: **SL=1.5 ATR**, TP=`min(2.5, 1.2 + abs(WIR)*2.0) ATR`. Observed clean shadow geometry: avg SL **13.5p**, avg TP **26.6p**, median RR **1.71**, median BE_WR **36.9%**.
- Direction filter: code supports both directions. `WIR>threshold` plus bearish confirmation => SELL; `WIR<-threshold` plus bullish confirmation => BUY. In the clean shadow data, all **70/70** trades were BUY, so there is no empirical SELL wing yet.
- Session: no hard strategy-level session filter. Production scoring can add off-session penalties, but the strategy itself does not restrict sessions.
- Entry: legacy uses current/latest bar; redesign v2, if enabled, fixes confirmation to `df.iloc[-2]` and treats `ctx.entry` as next-bar execution. Current shadow data contains v2 closed-bar reasons for a subset of rows, but execution-level evidence is still mixed across runtime paths.
- Exit: normal SL/TP, plus `SIGNAL_REVERSE`, `MAX_HOLD_TIME` at 8h for daytrade modes, `TIME_DECAY_EXIT` after half max-hold if in loss, `MANUAL_CLOSE`, and `WEEKEND_CLOSE`.

### Shadow dissection (N=70)
- TP hit: **N=23** (32.9% of trades, 85.2% of wins), avg raw P/L **+18.5p**, avg spread-adj P/L **+17.0p**.
- SL hit: **N=24** (34.3% of trades), avg raw P/L **-15.6p**, avg spread-adj P/L **-19.6p**.
- Other exits: `SIGNAL_REVERSE` **N=13 WR=23.1% avg adj=-6.1p**; `TIME_DECAY_EXIT` **N=9 all losses avg adj=-5.5p**; `MANUAL_CLOSE` N=1 win.
- BUY: **N=70 WR=38.6% raw EV=-0.12p spread-adj EV=-2.88p PF=0.66**.
- SELL: **N=0**, no empirical wing evidence.
- avg MAFE: **8.2p** / avg MFE: **10.0p**. SL-hit trades have avg MAFE **15.6p** vs avg SL **14.3p**; TP-hit trades have avg MFE **18.5p** vs avg TP **18.3p**.
- Spread-adj contribution: raw EV **-0.12p** -> spread-adj EV **-2.88p**, contribution **-2.76p/trade**. Avg entry spread **1.26p**, avg abs slippage **1.50p**, contribution/spread occupancy **2.19x**.
- Instrument/session asymmetry: GBP_USD **N=17 WR=58.8% EV=+5.95p PF=3.29**; USD_JPY **N=13 WR=46.2% EV=+0.38p PF=1.06**; GBP_JPY **N=18 EV=-10.40p**; EUR_JPY **N=10 EV=-13.19p**. Tokyo **N=27 EV=+0.55p PF=1.10**, overlap **N=10 WR=0% EV=-11.70p**.

### Gate state
| Gate | Evidence | State |
|---|---|:---:|
| N | **70** clean shadow trades | 🟢 |
| WR / Wilson | **38.6% / 0.280** | 🟢 |
| spread-adj EV | **-2.88p** | 🔴 |
| PF | **0.66** | 🔴 |
| Direction asymmetry | BUY **N=70**, SELL **N=0** | 🟠 |
| Exit geometry | TP **23** vs SL **24**, BE_WR median **36.9%** vs WR **38.6%**, but friction flips EV negative | 🔴 |
| WF | **1/3** | 🔴 |

### Redesign hypotheses
1. **Pair-scope friction filter**: restrict shadow candidate to lower-friction/positive observed pairs first: `GBP_USD`, `USD_JPY`, and optionally `EUR_GBP` as a separate small-N cell; exclude `GBP_JPY` and `EUR_JPY` until a separate JPY-cross design exists. | Reason: majors/no-JPY-cross slice is **N=42 WR=52.4% EV=+2.80p PF=1.66**, while JPY crosses are the main loss source. | Expected impact: N down about 40%, WR target **50%+**, spread-adj EV target **+2 to +4p**, PF target **>=1.3**. | BT spec: grid `pair_scope in {all, majors_no_jpy_cross, gbpusd_usdjpy, gbpusd_only}` x `session in {all,tokyo_london,no_overlap}` x `direction in {BUY,SELL,BOTH}`; Bonferroni **m=36**.
2. **Overlap hard block**: block London/NY overlap for this mean-reversion wick thesis. | Reason: overlap is **N=10 WR=0% EV=-11.70p**, while non-overlap is **N=60 WR=45.0% EV=-1.41p** and Tokyo is slightly positive. Overlap liquidity appears to convert wick rejection into continuation rather than reversion. | Expected impact: immediate tail-risk reduction; WR target **43-48%**, spread-adj EV improvement **+1 to +2p/trade** before pair filters. | BT spec: grid `session_block in {none,overlap,ny,overlap+ny}` x `pair_scope in {all,majors_no_jpy_cross}` x `threshold in {0.45,0.55,0.65}`; Bonferroni **m=24**.
3. **Weaker WIR, stronger confirmation**: keep threshold near **0.45-0.55** but require confirmation body **>=0.25 ATR** and next-bar non-reversal; do not chase `abs(WIR)>=0.70`. | Reason: `abs(WIR)>=0.70` is **N=2 WR=0% EV=-13.25p**, while stronger imbalance did not improve outcomes. Failures cluster when TP is not reached and exits decay/reverse. | Expected impact: modest N reduction, fewer stale reversions; WR target **45-52%**, PF target **>=1.1** before pair/session filters. | BT spec: grid `wir_threshold in {0.45,0.55,0.65}` x `confirm_body_atr in {0.10,0.25,0.40}` x `next_bar_non_reversal in {on,off}` x `pair_scope in {all,majors_no_jpy_cross}`; Bonferroni **m=36**.

## Recommended next steps
- 採用候補 N: **5 draft specs** for MASSIVE BT: dt #1, dt #2, dt #3, wick #1, wick #2. Wick #3 is lower priority unless pair/session filters still leave borderline EV.
- 推奨実行順: **wick pair/session filter first** (largest observed positive slice), then **dt ADXQ2 closed-bar**, then **dt early invalidation**.
- BT 起票 task 候補:
  - `20260518-DBR-BT-wick-imbalance-pair-session-filter`
  - `20260518-DBR-BT-dt-sr-channel-closed-adxq2`
  - `20260518-DBR-BT-dt-sr-channel-early-invalidation`
