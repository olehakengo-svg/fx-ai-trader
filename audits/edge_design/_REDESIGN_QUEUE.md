<!-- audits/edge_design/_REDESIGN_QUEUE.md -->
# Edge Design Audit — REDESIGN QUEUE

Wave 4 取り組み順（Recommendation S→A、Tier 1→4 優先）。
全 86 戦略 (Tier 1: 8, Tier 2: 45, Tier 3: 17, Tier 4: 8) 監査完了 + 8 alias は元 Tier 2 audit に紐付け。

| # | Strategy | Tier | Verdict | Rec | Single-line Fix Summary |
|---|---|---|---|---|---|
| 1 | doji_breakout | Tier 1 (LIVE) | DESIGN | A | 最優先の修正は trigger 1 系統 |
| 2 | squeeze_release_momentum | Tier 1 (LIVE) | TIMING | A | 最小修正は timing 1 系統 |
| 3 | streak_reversal | Tier 1 (LIVE) | DESIGN | A | 最小修正は filter 1 系統 |
| 4 | vol_momentum_scalp | Tier 1 (LIVE) | TIMING | A | 最小修正は trigger の思想を変えず、timing だけを固めること |
| 5 | xs_momentum | Tier 1 (LIVE) | TIMING | A | 思想と trigger の方向性は維持する |
| 6 | alpha_intraday_seasonality | Tier 2 (Shadow) | DESIGN | A | 思想と trigger 中核は有効候補 |
| 7 | asia_range_fade_v1 | Tier 2 (Shadow) | TIMING | A | Trigger/filter/stop は維持候補にする |
| 8 | confluence_scalp | Tier 2 (Shadow) | TIMING | A | 思想は維持する |
| 9 | cpd_divergence | Tier 2 (Shadow) | TIMING | A | 思想と trigger は維持する |
| 10 | ema200_reversal | Tier 2 (Shadow) | TIMING | A | 最小再設計は timing と routing の 1 系統修正 |
| 11 | gold_trend_momentum | Tier 2 (Shadow) | TIMING | A | 思想は維持する |
| 12 | htf_false_breakout | Tier 2 (Shadow) | DESIGN | A | Trigger/timing の 1 系統修正で復活余地がある |
| 13 | london_ny_swing | Tier 2 (Shadow) | TIMING | A | Trigger の思想自体は維持する |
| 14 | mqe_gbpusd_fix | Tier 2 (Shadow) | DESIGN | A | 思想と trigger は有効候補 |
| 15 | mtf_confluence | Tier 2 (Shadow) | DESIGN | A | 思想は明確で、trigger も MR と整合しているため棄却しない |
| 16 | pullback_to_liquidity_v1 | Tier 2 (Shadow) | DESIGN | A | 思想は維持する |
| 17 | rsk_gbpjpy_reversion | Tier 2 (Shadow) | DESIGN | A | Trigger と pair gate は維持する |
| 18 | squeeze | Tier 2 (Shadow) | DESIGN | A | 思想は明確で、squeeze から volatility expansion を取る方向性自体は有効候補として残せる |
| 19 | sr_anti_hunt_bounce | Tier 2 (Shadow) | TIMING | A | 思想は維持する |
| 20 | sr_liquidity_grab | Tier 2 (Shadow) | TIMING | A | 思想は維持する |
| 21 | stoch_pullback | Tier 2 (Shadow) | TIMING | A | 思想は有効候補として残す |
| 22 | three_bar_reversal | Tier 2 (Shadow) | TIMING | A | Trigger の思想自体は残す |
| 23 | tokyo_nakane_momentum | Tier 2 (Shadow) | DESIGN | A | 思想と中核 trigger は復活 candidate として残す価値がある |
| 24 | turtle_soup | Tier 2 (Shadow) | TIMING | A | 思想と trigger は明確で、旧 GBPUSD BT/WF には復活候補として見るだけの参考値があるため棄却しない |
| 25 | vbp | Tier 2 (Shadow) | DESIGN | A | Trigger の核は維持するが、range 計算の基準時点を修正する |
| 26 | vol_momentum | Tier 2 (Shadow) | TIMING | A | 思想と trigger/filter/stop geometry は概ね維持し、timing 契約だけを固める |
| 27 | vsg_jpy_reversal | Tier 2 (Shadow) | DESIGN | A | 思想と trigger/timing/filter は成立しているため、復活候補としては高い |
| 28 | ema_cross | Tier 3 (FORCE_DEMOTED) | TIMING | A | 思想は有効候補として残す |
| 29 | ema_pullback | Tier 3 (FORCE_DEMOTED) | DESIGN | A | 思想と trigger 骨格は維持する |
| 30 | inducement_ob | Tier 3 (FORCE_DEMOTED) | DESIGN | A | 思想は捨てない |
| 31 | lin_reg_channel | Tier 3 (FORCE_DEMOTED) | DESIGN | A | Trigger の思想は維持し、timing と stop/TP geometry を 1 系統ずつ直す |
| 32 | orb_trap | Tier 3 (FORCE_DEMOTED) | DESIGN | A | 修正対象は主に stop/TP geometry の 1 系統 |
| 33 | post_news_vol | Tier 3 (FORCE_DEMOTED) | DESIGN | A | 思想は明確で、volatility spike + follow-through という trigger 骨格も momentum continuation を捕捉している |
| 34 | trend_rebound | Tier 3 (FORCE_DEMOTED) | DESIGN | A | 修正優先は trigger の `momentum_limit` 条件である |
| 35 | bb_rsi_ema_aligned | Tier 4 (SCALP_SENTINEL) | DESIGN | A | 思想はコードから明確に導けるため棄却しない |
| 36 | ma_mr_hybrid | Tier 4 (SCALP_SENTINEL) | DESIGN | A | 思想はコードから十分に導けるため `THESIS_INVALID` ではない |
| 37 | ma_regime_switch | Tier 4 (SCALP_SENTINEL) | DESIGN | A | 思想はコードから十分に導けるため `THESIS_INVALID` ではない |
| 38 | ma_trend_perfect | Tier 4 (SCALP_SENTINEL) | TIMING | A | 思想と trigger/filter/stop の骨格は維持する |
| 39 | mtf_counter_trend_scalp | Tier 4 (SCALP_SENTINEL) | TIMING | A | 思想は明確で、trigger/filter/stop の設計は大きく崩れていない |
| 40 | mtf_regime_trend_cascade_scalp | Tier 4 (SCALP_SENTINEL) | DESIGN | A | 思想は有効候補として残す |
