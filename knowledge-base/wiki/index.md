# FX AI Trader Knowledge Base

## 🎯 最重要目標: 段階目標 M1→M2→M3 (月次符号転換 → +0.5%/月 → +2〜3%/月) — 2026-07-10 段階化 (user 承認)
**全施策の判断基準。これに寄与しない施策は後回し。**
- **21.6% は aspirational anchor に格下げ** — 導出母体 12-cell は live 経路残存 1〜2/12 でほぼ消滅、現行制約 (lot chain/agg-Kelly gate) 下で構造的到達不能。再導出: [[monthly-target-rederivation-2026-07-10]] / 決裁: [[shortest-path-decision-memo-2026-07-10]] (最短経路 = トラックA stage-2 / B 供給ライン / C 資本配管)
- 現在: **DD防御0.2x** (DD=🔴🔴🔴**100.01%** — **100%バリア突破後 held (no new high)**, defensive mode — 2026-07-08) → 月利47%（BT推定、クリーンデータ蓄積中）
- 旧目標「月利100%」「Phase 3 月利594%」は TP-HIT 12-cell 検証で数学的不可能と確定、user 承認で再設定 (roadmap v2.2 T12)
- 詳細: **[[roadmap-v2.3-payoff-friction-repair]]** (✅ 正式版 2026-07-07 — 決済非対称/摩擦の是正。T3 診断確定 [[payoff-asymmetry-diagnosis-2026-07-07]]) / 前版: [[roadmap-v2.2-win-conversion]] (全12項目クローズ済) / 旧: [[roadmap-v2.1]]
- 旧: [[roadmap-v2]] (v2.0) / [[roadmap-to-100pct]] (v1)
- **v2.3 確定 (2026-07-07)**: clean live 30d N=93/−245.0p/payoff 0.274。ボトルネック =「正の摩擦調整 EV セルの不在」(確定)。主因 = 勝ち側 exit 執行の崩壊 (設計TP が実走 MFE の5倍 + trail 返上 142.5p/30d)
- **T2 exit-repair verdict: ❌ FAIL / H0 採択 (2026-07-08、期日 07-21 の13日前倒し)** — grid 9構成全て BH-FDR 不通過 (p=1.0) / WF 0/3 / 摩擦調整EV負 (最良 tp0.4×sl0.6 で −2.96 p/t)。メカニズムは診断通り作動した上での構造的 FAIL (ナイフエッジ3点検査済、感度 run も同結論)。**§4 固定分岐発動 → v2.3 の主戦線は WS3 シグナル張り替え (20p 走る場所への entry 再設計)**。詳細: [[exit-repair-tp-sl-prereg-2026-07-07]] §8
- **WS3 stage-1 verdict: ✅ PASS 2/8 (2026-07-09、期日 07-16 の7日前倒し)** — 方向性非対称の OOS 検証 ([[ws3-asymmetry-oos-prereg-2026-07-09]] §8) で **london_fix_reversal×EUR_USD (ratio 1.43, p=0.0115)** + **htf_false_breakout×AUD_JPY (1.82, p=0.0118)** が BH-FDR 通過 + ナイフエッジ3点全通過。「探索→OOS」2段スクリーン survivor は本プロジェクト初。**次 = stage-2 (barrier/EV 設計 pre-reg + TV Pine canon 再現 + user 最終承認) — live 実装はそこまで禁止**
- **WS3 → 外部仮説転進 (2026-07-13、[[external-hypothesis-scan-2026-07-13]])** — 内部母集団探索は **2 周 FAIL** (stage-2 barrier/EV FAIL 07-10 PR #75 + round-2 OOS 0/5 07-10 PR #79) + T10/T11 診断 CLOSE (07-11 PR #80) で供給枯渇を三重確認。外部仮説スクリーン + 実証 probe で **価格ベース lead-lag を閉鎖** (OHLCV 内部 + cross-asset とも ≥1h 裁定消滅、naive の有意 50 pairs は Lo-MacKinlay 非同期取引 artifact)。外部の同型 falsification (Mesfin 2026) が内部 FAIL と一致。→ **律速をデータモダリティへ更新**。survivor = **cross-asset divergence-reversion** ([[ws3-round3-crossasset-divergence-prereg-2026-07-13]] self-LOCK、verdict 07-24)。E1 retail-positioning は user infra 決定待ち

## 🔗 Cross-KB Navigation
- **[[audit-index]]** — `learning/` 18 audit ノード + MEMORY `project_*.md` 双方向マップ（次セッション Claude 必読、KB↔MEMORY 棲み分けルール記載）

<!-- KB_PORTFOLIO_START -->
## Current Portfolio (auto-synced, 2026-08-26)

### ELITE_LIVE (never shadowed)
| Strategy | BT Data | Status |
|----------|---------|--------|

### PAIR_PROMOTED (SENTINEL)
| Strategy | Pairs | BT Data | Status |
|----------|-------|---------|--------|
| [[bb-squeeze-breakout]] | EUR_USD | no BT data | PAIR_PROMOTED |
| [[doji-breakout]] | GBP_USD, USD_JPY | GBP_USD: EV=+0.724 WR=78.3%; USD_JPY: EV=+0.338 WR=61.9% | PAIR_PROMOTED |
| [[donchian-momentum-breakout]] | NZD_JPY, NZD_USD | no BT data | PAIR_PROMOTED |
| [[dt-bb-rsi-mr]] | USD_JPY | EUR_USD: EV=-0.077 WR=52.0%; GBP_USD: EV=-0.135 WR=51.3%; USD_JPY: EV=-0.023 WR=54.2% | PAIR_PROMOTED |
| [[ema200-trend-reversal]] | USD_JPY | EUR_USD: EV=+0.410 WR=75.0%; USD_JPY: EV=-0.183 WR=56.2% | PAIR_PROMOTED |
| [[mqe-gbpusd-fix]] | GBP_USD | no BT data | PAIR_PROMOTED |
| [[pivot-detector-v2-5]] | EUR_USD | no BT data | PAIR_PROMOTED |
| [[price-shock-rev-aud-jpy-h1-long]] | AUD_JPY | no BT data | PAIR_PROMOTED |
| [[price-shock-rev-eur-aud-h1-long]] | EUR_AUD | no BT data | PAIR_PROMOTED |
| [[price-shock-rev-eur-gbp-h1-long]] | EUR_GBP | no BT data | PAIR_PROMOTED |
| [[price-shock-rev-nzd-jpy-h1-long]] | NZD_JPY | no BT data | PAIR_PROMOTED |
| [[price-shock-rev-usd-cad-h1-long]] | USD_CAD | no BT data | PAIR_PROMOTED |
| [[squeeze-release-momentum]] | EUR_USD | EUR_USD: EV=+0.656 WR=73.3% | PAIR_PROMOTED |
| [[vol-momentum-scalp]] | EUR_JPY | no BT data | PAIR_PROMOTED |
| [[vsg-jpy-reversal]] | EUR_JPY | no BT data | PAIR_PROMOTED |
| [[weekend-gap-fade]] | AUD_USD, EUR_USD, USD_JPY | no BT data | PAIR_PROMOTED |
| [[xs-momentum-rsi]] | USD_JPY | no BT data | PAIR_PROMOTED |

### SHADOW (Data Collection)
| Strategy | BT Data | Notes |
|----------|---------|-------|
| [[bb-rsi-reversion]] | no BT data | SCALP_SENTINEL |
| [[dt-fib-reversal]] | EUR_JPY: EV=-0.199 WR=54.3%; EUR_USD: EV=+0.407 WR=80.0%; GBP_USD: EV=+0.374 WR=76.2% | UNIVERSAL_SENTINEL |
| [[dt-sr-channel-reversal]] | EUR_JPY: EV=+0.178 WR=63.8% | UNIVERSAL_SENTINEL |
| [[eurgbp-daily-mr]] | no BT data | UNIVERSAL_SENTINEL |
| [[gbp-deep-pullback]] | GBP_USD: EV=+1.064 WR=75.3% | LOT_BOOST (not sentinel/elite) |
| [[gotobi-fix]] | no BT data | UNIVERSAL_SENTINEL |
| [[htf-false-breakout]] | EUR_USD: EV=+0.352 WR=80.0%; GBP_USD: EV=+0.552 WR=75.0%; USD_JPY: EV=+0.660 WR=80.0% | LOT_BOOST (not sentinel/elite) |
| [[kalman-d7-ema75-break]] | no BT data | UNIVERSAL_SENTINEL |
| [[kalman-d7-po-dn-flip]] | no BT data | UNIVERSAL_SENTINEL |
| [[kalman-d7-trail-atr]] | no BT data | UNIVERSAL_SENTINEL |
| [[liquidity-sweep]] | no BT data | UNIVERSAL_SENTINEL |
| [[london-close-reversal]] | no BT data | UNIVERSAL_SENTINEL |
| [[london-close-reversal-v2]] | no BT data | UNIVERSAL_SENTINEL |
| [[london-fix-reversal]] | EUR_USD: EV=+0.161 WR=66.7%; GBP_USD: EV=-0.150 WR=56.8%; USD_JPY: EV=+0.079 WR=60.9% | LOT_BOOST (not sentinel/elite) |
| [[london-ny-swing]] | GBP_USD: EV=+0.362 WR=72.7% | LOT_BOOST (not sentinel/elite) |
| [[ma-regime-switch]] | no BT data | SCALP_SENTINEL |
| [[ma-trend-perfect]] | no BT data | SCALP_SENTINEL |
| [[macd-rsi-pullback]] | no BT data | UNIVERSAL_SENTINEL |
| [[mtf-counter-trend-scalp]] | no BT data | SCALP_SENTINEL |
| [[mtf-regime-range-cascade-scalp]] | no BT data | SCALP_SENTINEL |
| [[mtf-regime-trend-cascade-scalp]] | no BT data | SCALP_SENTINEL |
| [[mtf-reversal-confluence]] | no BT data | LOT_BOOST (not sentinel/elite) |
| [[mtf-trend-follow-scalp]] | no BT data | SCALP_SENTINEL |
| [[pd-eurjpy-h20-bbpb3-sell]] | no BT data | UNIVERSAL_SENTINEL |
| [[price-shock-reversion]] | no BT data | UNIVERSAL_SENTINEL |
| [[session-time-bias]] | EUR_USD: EV=+0.215 WR=69.6%; GBP_USD: EV=+0.113 WR=67.1%; USD_JPY: EV=+0.580 WR=79.0% | UNIVERSAL_SENTINEL |
| [[sr-weighted-bounce]] | no BT data | UNIVERSAL_SENTINEL |
| [[sr-weighted-break]] | no BT data | UNIVERSAL_SENTINEL |
| [[streak-reversal]] | no BT data | shadow only |
| [[tokyo-range-breakout-up]] | no BT data | LOT_BOOST (not sentinel/elite) |
| [[trendline-sweep]] | EUR_USD: EV=+0.927 WR=80.8%; GBP_USD: EV=+0.599 WR=73.1% | shadow only |
| [[turtle-soup]] | GBP_USD: EV=+0.386 WR=69.7% | LOT_BOOST (not sentinel/elite) |
| [[vix-carry-unwind]] | USD_JPY: EV=+0.212 WR=67.3% | UNIVERSAL_SENTINEL |
| [[vol-spike-mr]] | USD_JPY: EV=+0.148 WR=64.6% | UNIVERSAL_SENTINEL |
| [[vol-surge-detector]] | no BT data | SCALP_SENTINEL |
| [[wick-imbalance-reversion]] | no BT data | shadow only |
| [[xs-momentum]] | EUR_USD: EV=+0.225 WR=68.0%; USD_JPY: EV=+0.270 WR=68.7% | shadow only |

### FORCE_DEMOTED (stopped)
| Strategy | BT Data | Status |
|----------|---------|--------|
| [[atr-regime-break]] | no BT data | FORCE_DEMOTED |
| [[ema-cross]] | no BT data | FORCE_DEMOTED |
| [[ema-pullback]] | no BT data | FORCE_DEMOTED |
| [[ema-ribbon-ride]] | no BT data | FORCE_DEMOTED |
| [[ema-trend-scalp]] | no BT data | FORCE_DEMOTED |
| [[engulfing-bb]] | no BT data | FORCE_DEMOTED |
| [[fib-reversal]] | no BT data | FORCE_DEMOTED |
| [[inducement-ob]] | no BT data | FORCE_DEMOTED |
| [[intraday-seasonality]] | no BT data | FORCE_DEMOTED |
| [[lin-reg-channel]] | no BT data | FORCE_DEMOTED |
| [[macdh-reversal]] | no BT data | FORCE_DEMOTED |
| [[ob-retest]] | no BT data | FORCE_DEMOTED |
| [[orb-trap]] | USD_JPY: EV=+0.866 WR=84.2% | FORCE_DEMOTED |
| [[post-news-vol]] | EUR_USD: EV=+0.817 WR=71.4%; GBP_USD: EV=+1.762 WR=88.5% | FORCE_DEMOTED |
| [[sr-break-retest]] | no BT data | FORCE_DEMOTED |
| [[sr-channel-reversal]] | no BT data | FORCE_DEMOTED |
| [[stoch-trend-pullback]] | no BT data | FORCE_DEMOTED |
| [[trend-rebound]] | no BT data | FORCE_DEMOTED |
| [[v-reversal]] | no BT data | FORCE_DEMOTED |
| [[vwap-mean-reversion]] | no BT data | FORCE_DEMOTED |

<!-- KB_PORTFOLIO_END -->

## System State (v9.5 / v2.1)
- Defensive mode: **0.2x** (DD=🔴🔴🔴**1218.9pip = 121.9%** on the legacy $1000 pip basis — **flat, no new high** vs 08-23, eq_current=−$1202.0 vs peak +$16.9 — Render API 2026-08-26. 30d Kelly=0.0%, overall-edge (risk dash)=**−26.46%** (**flat** — the risk window's `effective_date_from` rolled 07-24→07-26 but `n` stayed 15 and every derived metric is bit-identical, because there were no trades in the rolled slice; risk-window WR flat at 40.0%); prev snapshot 08-23 DD 1218.9pip / edge −26.46%)
  - 🔴 **2026-08-26: the whole pull is frozen, and the engine is not.** N / PnL / EV / Wilson / DD / edge / Kelly / DSR / MC **and `shadow_count` (12,386) and `oanda_audit.total` (15,756)** are all bit-for-bit identical to 08-23, while `/api/demo/status` reports `running`/`main_loop_alive`/`watchdog_alive` = true, **62,472 ticks**, **11,172 upstream blocks**, and OANDA `ok` at 130ms. **`oanda_audit` last row = 2026-08-21 18:46 UTC (~4 days) spanning 2 ordinary trading days (08-24 Mon, 08-25 Tue).** A flat realized book is routine here; a **flat `shadow_count` is not** — every prior flat window still advanced shadow (+111/+138/+145/+1,785). Under shadow-first the estimator has been blind for 2 trading days. Block census: `r2_shadow_demoted_cell` **4,301 (38.5%)** — this is what freezes shadow, since the gate rejects *before* a shadow row is written; `order_bar_dedup` 2,970; `direction_filter` **2,841**. 🔴 **`rnb_usdjpy` blocks exactly once per tick — 2,841 blocks / 2,841 ticks = ratio 1.00**, i.e. `direction_filter` is unconditional, not selective (consistent with the known `compute_rnb_signal` WAIT-path `entry: 0` bug below). **Not root-caused in this run** — counter observation only, code read is the top follow-up. See [[2026-08-26]]
  - 🔴 **2026-08-26: JPY NAV ledger has drifted ¥46,125.86 from the broker.** Live heartbeat NAV = **¥278,123.64**; `jpy_ledger.eq_current_jpy` = **¥324,249.50**. `/api/oanda/equity` cross-check reconciles with the *broker* (cum realized −¥80,686; ¥359,109 − ¥80,686 = ¥278,423 ≈ NAV, residual ¥299) — not with the ledger. Per `modules/demo_trader.py` L1058-1078 the ledger is **synthetic**: anchored once on 2026-07-28 at `OANDA_EQ_JPY_CURRENT_INIT = 326,472.58` and incremented per close, and the equity curve implies ≈¥279,017 on 07-29 ⇒ **the anchor itself was ~¥47k high** and the offset has been carried forward for a month. **Sizing impact: none today** — `DD_LOT_TIERS` tops out at `DD≥8% → 0.20×`, and both the ledger (9.76%) and the broker-measured DD from the same peak (¥81,164.83 = **22.6%** of base) exceed 8%, so both map to 0.20×; the tier is **saturated**, so the SSOT is correct only by luck. **Reporting impact: material** — headline DD understates broker-measured DD by **~12.8pp**
  - ⚠️ **2026-08-26: `/api/oanda/equity` is 15 days stale** — last curve point 2026-08-10 07:20 UTC (928 pts) despite **8 live fills closing 08-14→08-21** and `open_trade_count=0`. A **second, independent** ingestion gap (audit stops 08-21, equity stops 08-10)
  - ⚠️ **2026-08-26: clock skew** — Render heartbeat `last_check` 2026-08-26T00:59:54Z vs runner clock 2026-08-25 19:20Z (**server ~5h40m ahead**). Staleness conclusions unaffected (~4 days either way), but do not compare timestamps across the two sources
  - ⚠️ **`dd_pct` basis changed (v2.3 実 NAV(JPY) 移行)**: the API field returns **0.0976 = 9.76% against the JPY NAV ledger** (`jpy_ledger.active=true`, 2026-08-23: base ¥359,109 / peak ¥359,288.47 / current ¥324,249.50 / DD ¥35,038.97), **not** the legacy pip/$1000 basis. The historical wiki series (98.2 → 99.33 → 100.01 → 100.8%) is the pip basis; its continuation is **121.9%**. **100.8% → 9.7% was a unit change, NOT a recovery.**
  - ⚠️ MC `initial_capital` rebased **1000 → 5801.44** in the same pull — MC absolutes shifted accordingly; normalized as % of init the forward model is ≈unchanged (worst DD99 17.0%→**17.9%**, median max DD 12.1%→**11.45%**)
- **CB RECOVERY 2026-06-04**: CB auto-triggered at 04:34 UTC (-30.4pip daily loss) → E1/E4/E8 (bb_rsi_reversion + session_time_bias cells) disabled (stage=0) + modes restarted at 06:24 UTC. Post-recovery: all signals shadow_tracking (confirmed). watchdog は 2026-07-06 稼働確認済み (下記)。
- HourlyEngine: **Activated 2026-05-18** — all H1 strategies (KSB+DMB+5 PriceShockRev) are Shadow-only via `_shadow_always`.
- XAU: **Stopped** (v8.4) -- post-cutoff XAU loss = -2,280pip (102% of total loss)
- FX-only post-cutoff (2026-04-08〜) — **2026-07-02 wiki-daily-update** (demo/stats live only, is_shadow=false):
  - Live only (is_shadow=0): **N=542** (+23 fills vs 06-25 evening N=519: **11W/11L/1BE**, ~7-day window — no log 06-26〜07-01), WR=43.2% (+0.2pp, decided 46.0%), EV=**-0.96** (−0.14 ⚠️), PnL=**-521.1pip** (**−94.8pip ⚠️⚠️⚠️ steepest single-window drop in log** — even 11W/11L split but sized losses dominate); Wilson lower=41.7%, BF lower=38.9%
  - 🔴 **2026-07-01 20:16 UTC "1 LIVE sent" は偽記録と判明（2026-07-02 forensic, rule:R3 修正済み）**: wick_imbalance_reversion GBP_USD BUY 5000u の `bridge_status=sent` 行は、bridge 内 daily_loss gate (−23.3pip) が**正しくブロックした後に呼び出し側 (demo_trader L6324) が無条件で書いた偽 'sent'**。実弾は出ていない（oanda_trade_id empty はそのため）。「sent+blocked twin」(06-16/17/19 同型) はこの二重書込みが正体。修正: open_trade() が受理/拒否を返す契約に変更、拒否時は 'sent' を書かず shadow へ降格（FLAG_DRIFT 汚染と gate-bypass resend を遮断）。tests/test_bridge_send_accept_contract.py で回帰固定。Audit window (07-01 18:12→07-02 05:02 UTC) = 偽sent 1 + blocked 1 + **28 shadow_tracking skipped**
  - 30d rolling (risk API): morning n=112 → **evening re-run n=109** (window rolled ~hours, 3 EUR_USD trades aged out). Kelly=**0.0%** ⚠️⚠️⚠️ (edge morning -37.03% → **evening -35.72%** NEGATIVE, WR 47.32%→48.62%, odds 0.322 — eased +1.31pp on window-roll, **not a real edge gain**; still 7th deteriorating window vs 06-25); 30d attribution: **gross=net -321.7 → -310.0pip** (evening n=109, friction 462.3→456.3pip/4.19 per-trade). **All 5 instruments negative — GBP_USD #1 drag -139.9 (mean -3.33, n=42, flat); EUR_USD -84.4→-72.7 (eased on roll); EUR_JPY -46.0; USD_JPY -40.4; USD_CHF -11.0**. MC tail eased slightly on roll: worst DD99 227.92→**224.82%**, median max DD(MC) 175.08→**172.26%** (still >100%)
  - **TRUE_LIVE** (`is_shadow=0 AND oanda_trade_id != ''`) SSOT — 2026-05-03 実測: **N=371** (incl BE) / **346** (WIN/LOSS), WR=39.89%, EV=-0.686, PnL=-254.6pip (see [[aggregate-kelly-decomposition-2026-05-03-corrigendum]])
  - FLAG_DRIFT (`is_shadow=0` だが OANDA未送信): N=140, WR=32.86%, PnL=-132.4pip (`raw/audits/oanda-passthrough-gap-2026-05-03.md` 由来 write-path bug)
  - SHADOW (`is_shadow=1`): N≈8,482 (2026-07-02 demo/stats; prev 7,935 06-25 evening, +~547) — **Live 判断には混入禁止** (memory `feedback_live_vs_shadow_strict_separation`)
  - 旧記載 "N=29 (`oanda_trade_id != ''`)" は **誤り** — 実態は `mode='daytrade'` only サブセット、SUPERSEDED by [[aggregate-kelly-decomposition-2026-05-03-corrigendum]]
- Ruin probability: **0.0%** ✅ (MC sims — Render API 2026-08-23; init 5801.44 unchanged: worst-case DD99=**654.84 (11.29% of init)**, median max DD=**353.21 (6.09%)**, median final eq=**5488.42 (−5.4%)**; the MC tail narrowed sharply vs 08-20 (17.9%→11.29%) but that is the same n=10→15 window-roll — 2 favorable carry-dip draws entered the resample) — 実現 ruin が 0% なのは 0.2× lot cap のみによる (原エッジは負のまま)
- Aggregate Kelly: **0.0%** ⚠️⚠️⚠️ (overall edge (risk dash)=**−26.46%** — 🟢 eased +5.55pp vs 08-20's −32.01%, but this is **window-roll arithmetic, not a real edge gain**: risk window n=10→**15**, WR flat **40.0%**, odds 0.6998→0.8385; DSR=0.0/haircut 100%/Sharpe −0.1301/n_trials 4; net **−78.5 (n=15)**, per-trade **−5.23** (halved from −10.76 by the denominator, not by the numerator), friction 4.43 per-trade; **AUD_JPY still #1 30d drag −122.6 on n=2 (mean −61.3)**, USD_JPY **+53.9 n=10**, 🆕 EUR_GBP **−9.8 n=3**; ex-AUD_JPY the 30d book is **+44.1 on n=13**; TRUE_LIVE SSOT: N=371 raw=-0.69. 🟢 agg-kelly gate still load-bearing — **5 live fills passed / 13 blocked** (`agg_kelly` −0.331…−0.374<0) in the 08-20→08-21 slice)
- Aggregate Kelly decomposition 2026-05-03: 旧 doc は SUPERSEDED。新 SSOT: [[aggregate-kelly-decomposition-2026-05-03-corrigendum]] (TRUE_LIVE Strategy × Pair 出血ランキング、ELITE_LIVE `session_time_bias × GBP_USD` 出血特定)
- ⚠️ Portfolio warnings (cumulative post-cutoff, 2026-08-23): 🔴 **price_shock_rev_aud_jpy_h1_long — worst per-trade cell in the book (N=2, −122.6pip, mean −61.3)** vs a BT EV of **+32.25pip**; 🆕🔴 **price_shock_rev_eur_gbp_h1_long — its Phase B-1 sibling, live debut 0W/3L, N=3 −9.8pip (mean −3.27), no BT data on file** (same family, same failure direction ⇒ decide as a family, not cell-by-cell); session_time_bias #1 cumulative drag (N=30, WR=40%, −67.8pip); vwap_mean_reversion (N=11, WR=36.4%, −63.1pip); wick_imbalance_reversion (N=14, WR=35.7%, −63.0pip); trendline_sweep (N=32, WR=62.5%, −49.7pip — high WR, negative PnL = payoff asymmetry); vix_carry_unwind (N=26, −46.9pip, PAIR_DEMOTED 08-03); sr_break_retest (N=4, WR=0%, −44.2pip); bb_rsi_reversion (N=108, WR=41.7%, −34.5pip). All DSR 0.0 (haircut 100%). 🟢 Only positive live cells of size: **usdjpy_carry_dip_accumulator (N=9, +84.0 ⬆ from N=7/+45.1)**, orb_trap (N=4, +23.2), post_news_vol (N=2, +19.0), ema_pullback (N=2, +17.8), vol_momentum_scalp (N=17, +11.1). Carry-dip is the only cell the risk API can score and it is **still not significant** (DSR 0.424, Sharpe 0.3363 < threshold 0.4059, z=−0.192).
- ⚠️ Monitor anomaly 2026-06-11 02:13 UTC: rnb_usdjpy direction_filter=300 + daytrade hedge_block=209 + spike bypass 16049.8pip (price data artifact) — see `raw/trade-logs/2026-06-11-monitor.md`
- ✅ watchdog safety net **稼働確認 2026-07-06**: cron `fx-ai-edge-cell-watchdog` が 02:18 UTC に SUCCESS、実出力 (E1/E4 CODE_PINNED, E9 HOLD, re-arm ゼロ) をログ実測。API_AUTH_TOKEN 投入済み。旧記載 (Bearer bug / 値未投入) は解消済み
- ⚠️ rnb_usdjpy 構造バグ特定 2026-07-06: `compute_rnb_signal` の WAIT dict が `entry: 0` を返す設計 (2026-04-05 db5e3e4c 起源) → USD_JPY `_price_history` を 30秒周期で 0 汚染。2026-07-04 以降は PRICE_HISTORY_GUARD (PR #38) が drop 中 (~2,880件/日) だが、04-05〜07-04 の間 spike/velocity gate は汚染下で動作。07-02 vix Overlap 14/14 shadow 事故の支配的原因の可能性大。修正 = WAIT に実 Close を埋める最小 diff (fix PR 提出)
- ⚠️ sr_anti_hunt_bounce shadow data corruption: 100% null alpha_snapshot/edge_cell_id, 85% null sr_basis, pyarrow ImportError at 61% (regression 05-22→05-25)
- Last updated: 2026-08-23 (wiki-daily-update auto; cadence gap 3d, of which 08-22 Sat + 08-23 Sun are market-closed — last engine activity **2026-08-21 18:46 UTC**, not stale; N 573→**578 (+5 closed fills, 2W/2L/1BE)**; PnL −660.3→**−631.2 (+29.1 🟢 — first positive wiki-daily window since 07-16)**; EV −1.15→**−1.09**; WR 43.4% / decided 46.2%; Wilson 42.1 / BF 39.3; avg R 0.12; shadow_count 12,241→**12,386 (+145)**; ruin 0.0%. 🔴 **DD 1218.9pip = 121.9% pip basis — NEW HIGH again (+9.8)** (`dd_pct` field 0.0976 = 9.76% JPY-NAV, basis unchanged since 08-20). ⚠️ **The green is arithmetic**: edge −32.01→**−26.46%**, per-trade −10.76→**−5.23**, MC tail 17.9%→**11.29%** all come from the 30d risk window going **n=10→15** (same 2 AUD_JPY disasters averaged over 5 more trades) plus 2 favorable draws — **risk-window WR flat 40.0%, Kelly still 0.0, DSR still 0.0/haircut 100%, DD at a new high**. 🟢 **5 confirmed live fills, 0 false-sent** (5 sent / 5 filled, all real ids): **2× usdjpy_carry_dip_accumulator** USD_JPY BUY 1000u (#677931 08-20 07:03, #681149 08-20 10:19 — both wins, cell N 7→**9**, +45.1→**+84.0**) and 🆕 **3× price_shock_rev_eur_gbp_h1_long** EUR_GBP BUY 1000u (#681143, #700421, #709529 — **0W/3L, −9.8 on debut**). Net of carry-dip the window is −9.8 on 3. **13 agg-kelly blocks.** 🔴 **Corrected finding — the zero-unit anomaly is system-wide, not `ob_retest`-specific**: **184/800 audit rows (23%) carry `units: 0`** across **16 strategies / 7 instruments / every trading day**; 100% for vdr_jpy, rsk_gbpjpy_reversion, ema200_trend_reversal, sweep_reversion_eurgbp_late, ob_retest, turtle_soup; 83% sr_anti_hunt_bounce, 53% sr_break_retest; JPY-cross skew (GBP_JPY 70%, EUR_JPY 45%). **All are shadow_tracking ⇒ zero live exposure**, but the SR-family dominance overlaps the known `sr_anti_hunt_bounce` metadata corruption and shadow is the estimator. Root cause not yet diagnosed. Learner: **no new adjustment** — still id=93, blacklist still `[]` (no-op unresolved); daytrade EV −2.60 / scalp EV −0.15 / swing not ready ⚠️ **all 5 live fills routed through `daytrade_1h*`, the mode whose own analysis is EV −2.60 across every band and regime**. **No tier change executed.** Audit pulled at **limit=800** (2026-08-12 05:46 → 08-21 18:46 UTC, total 15,756) — `limit=30` would again have shown **0 live fills** (`feedback_audit_limit30_hides_live_fills`, 3rd consecutive confirmation). See [[2026-08-23]]); prev: 2026-08-20. ⚠️ **The System State body below remains partly stale at 2026-07-08 (N=558/−540.7)** for the deep narrative lines — the current-state figures are the ones in this line + Defensive mode / Ruin / Aggregate Kelly / Portfolio-warnings lines above + Session History top entry.
- scalp_eurjpy: **Stopped** (v8.6) -- friction/ATR=43.6%, 構造的不可能
- scalp_5m_eur / scalp_5m_gbp: **Active** (v8.6) -- 5m摩擦改善モード
- New modes (v9.0): **daytrade_eurjpy**, **daytrade_gbpjpy**, **[[rnb-usdjpy]]** (all auto_start)
- Phase B-1 Shadow candidate pair slots: **USD_CAD** (Tier 1 #3 / Phase B Wave 1 candidate), **USD_CHF** (Tier 3 WATCH / Phase B Wave 1 candidate), **AUD_JPY**, **NZD_JPY**, **AUD_USD**, **NZD_USD**, **EUR_AUD** (`price_shock_reversion`, surface-only; Live promotion disabled in this task)
- ELITE_LIVE tier: **trendline_sweep** only (per tier-master.md 2026-05-07; session_time_bias=PAIR_PROMOTED EUR_USD, gbp_deep_pullback=PAIR_DEMOTED GBP_USD)
- SHADOW_MODE: **active** (env SHADOW_MODE=true)
- Massive API: **primary data source** (全6ペア×全TF)
- New strategies (v2.1): ny_close_reversal, streak_reversal, vwap_mean_reversion
- Aggregate Kelly gate: **実装済み** (v9.0) -- Kelly<0で自動ブロック
- MC ruin gate: **実装済み** (v9.0) -- 取引前に破産確率チェック
- Phase Gate API: `/api/phase-gate` (Gate 1-4条件をエンドポイントで公開)
- DSR: **実装済み** (v8.6) -- Bailey & Lopez de Prado (2014)
- BT Friction Model: **v3** (v8.7) -- Spread/SL Gate + RANGE TP + Quick-Harvest反映
- 金曜/月曜ブロック: **撤去済み** (v8.6) -- 原則#1「攻める」準拠
- GBPアジア除外: **実装済み** (v8.6)
- **MTF Regime Engine**: **active** (v9.2.1) — D1×H4×H1 階層 labeler, shadow monitor
- **Strategy-aware MTF alignment**: **active** (v9.3 P0) — 4 family (TF/MR/BO/SE) × regime
- **REGIME_ADAPTIVE_FAMILY**: **active** (v9.3 P2) — bb_rsi/fib の regime 別 family override
- **A/B Gate Routing**: **active** (v9.3 Phase D) — hash-based 50/50 (mtf_gated / label_only)
- Price-Shock Live Shadow Monitor: `tools/price_shock_live_shadow_monitor.py` (Phase B-1 promote/demote evidence, Shadow-only `is_shadow=1`)
  - Group A conflict → LIVE→SHADOW downgrade (soft gate)
  - 5-7日で N≥500/group, 30日で p<0.05 検出想定

## Key Decisions
- [[complex-gate-edge-destruction-pattern-2026-05-03]] -- **🎯 最新 (2026-05-03)** Complex gate edge-destruction pattern — MTF cascade / HMM / multi-condition gate は BT で映えても Live/OOS で edge 破壊 (4例再現)、Wave 設計に simple-first 原則導入 (rule:R3)
- [[aggregate-kelly-decomposition-2026-05-03-corrigendum]] -- **🎯 SSOT (rev2)** TRUE_LIVE bucket only N=371、Strategy×Pair 出血ランキング再特定、ELITE_LIVE `session_time_bias × GBP_USD` 出血特定、surgical demote 経路は **再開可能**
- [[aggregate-kelly-decomposition-2026-05-03]] -- (2026-05-03 旧) 数値部分は corrigendum で SUPERSEDED (N=29 は mode='daytrade' subset 誤集計)
- [[regime-cascade-empirical-redesign-2026-04-30]] -- Regime Cascade 実測再設計 — v1 教科書仮説を否定、binary moderate_trend gate 採用、range cascade 停止 (rule:R1+R3)
- [[strategies-page-audit-followup-2026-04-30]] -- B1/B3 訂正: ELITE bypass 不要・FORCE_DEMOTED Live発火0件確認。direction_cells API 追加
- [[shadow-deep-mining-2026-04-24]] -- Shadow 7次元診断 → Scenario A 追認 / bb_rsi・ema・sr_channel の MR 系は現行 regime で dead (friction>edge)
- [[pre-registration-mafe-dynamic-exit-2026-04-24]] -- MAFE-based Time-Decay Exit の forward-usable pre-reg (target: bb_rsi_reversion, 48 param cells, Bonferroni α=1.04e-3)
- [[external-audit-2026-04-24]] -- **🎯 最新監査** Gap/Over-eng/Resource/Must-Do-Don't + surgery 結果 (§5 Action Items tracked)
- [[audit-completion-protocol]] -- 監査後の completion 追跡フロー (session-start で §5 確認必須)
- [[independent-audit-2026-04-10]] -- 2 audits, binding recommendations
- [[xau-stop-rationale]] -- FX profitable without XAU
- [[mfe-zero-analysis]] -- 90.6% of losses never go favorable
- [[defensive-mode-unwind-rule]] -- DD防御 0.2x 解除条件（段階A自動/B品質ゲート/C手動）
- [[negative-strategy-stopping-rule]] -- Shadow 止血ルール Level A/B/C（Bayesian 基準）

## Session History
- **2026-08-23 wiki-daily-update** — 🟢 **first positive wiki-daily window since 07-16**, and it is **one cell wide**. N=**578** (**+5 closed fills** vs 08-20's 573; 249W/290L/34BE → **251W/292L/35BE** = +2W/+2L/+1BE), WR=43.4% (−0.1pp), decided 46.2% (flat), EV=**−1.09** (+0.06), PnL=**−631.2pip** (**+29.1**), Wilson 42.1 / BF 39.3, avg R 0.12, ruin 0.0% ✅. shadow_count 12,241→**12,386 (+145)**. Cadence gap 3d but **08-22 Sat / 08-23 Sun are market-closed** — last engine activity **2026-08-21 18:46 UTC**, so the series is current, not stale. 🔴 **DD still made a new high: 1218.9pip = 121.9%** on the legacy $1000 pip basis (+9.8, eq −$1202.0 vs peak +$16.9 flat); `dd_pct` field 0.0976 = 9.76% on the JPY-NAV ledger (basis unchanged since 08-20; ¥35,038.97 DD on a ¥359,288.47 peak). ⚠️ **Everything green in the risk dashboard is denominator arithmetic, not evidence**: the 30d window went **n=10→15** (`effective_date_from` 2026-07-24), so the same two AUD_JPY disasters (−122.6) now average over 5 more trades, two of which are large carry-dip wins. That alone produces edge −32.01→**−26.46% (+5.55pp)**, per-trade net −10.76→**−5.23**, Sharpe −0.2259→**−0.1301**, and MC tail 17.9%→**11.29%** / median max DD 11.45%→**6.09%**. **Risk-window WR is flat at 40.0%, Kelly still 0.0, DSR still 0.0 with a 100% haircut, and the drawdown is at a fresh high.** Read as window-roll, exactly like 07-21/07-27. 🟢 **5 confirmed LIVE fills, 5 sent / 5 filled, 0 false-sent** (07-02 accept/reject contract holding): **2× `usdjpy_carry_dip_accumulator`** USD_JPY BUY 1000u — oanda **#677931** (08-20 07:03), **#681149** (08-20 10:19), **both wins** ⇒ cell N 7→**9**, WR 42.9→**55.6%**, +45.1→**+84.0**, EV/trade **+9.33**; DSR 0.3591→0.424 but **still not significant** (Sharpe 0.3363 < threshold 0.4059, z=−0.192). 🆕🔴 **3× `price_shock_rev_eur_gbp_h1_long`** EUR_GBP BUY 1000u — **#681143** (08-20 07:41), **#700421** (08-20 12:59), **#709529** (08-21 11:39) — **live debut 0W/3L, −9.8pip (mean −3.27)** against a 12.3y MASSIVE BT of N=239 / WR 72.8% / PF 14.75 / **EV +55.81pip**. **Net of carry-dip the window is −9.8 on 3 trades.** This is the second Price-Shock cell to invert BT sign in live (sibling `price_shock_rev_aud_jpy_h1_long` n=2 −122.6, BT EV +32.25) ⇒ escalated as a **family** question, not another per-cell threshold wait. **13 agg-kelly blocks** (−0.331…−0.374<0) in the 08-20→08-21 slice. 🔴 **Corrected finding — the 08-20 `ob_retest` zero-unit anomaly is actually system-wide**: **184 of 800 audit rows (23%) carry `units: 0`**, across **16 strategies / 7 instruments / every trading day** in the pull. 100% for `vdr_jpy`, `rsk_gbpjpy_reversion`, `ema200_trend_reversal`, `sweep_reversion_eurgbp_late`, `ob_retest`, `turtle_soup`; 83% `sr_anti_hunt_bounce` (57/69), 53% `sr_break_retest` (34/64), 39% `wick_imbalance_reversion` (36/92). JPY-cross skew: GBP_JPY **70%** (49/70), EUR_JPY 45%, AUD_JPY 22%, USD_JPY 18%, EUR_USD/EUR_GBP 6%, NZD_USD/AUD_USD 0%. **All 184 are `bridge_status=skipped` ⇒ zero live exposure**, but shadow is the estimator under shadow-first and the SR-family dominance overlaps the known `sr_anti_hunt_bounce` metadata corruption. Root cause not diagnosed in this run — distribution recorded so it can be traced against real code. Learner: **no new adjustment** (still id=93 from 08-19), `entry_type_blacklist` still **`[]`** ⇒ the no-op is unresolved and will keep re-firing; daytrade EV **−2.60** (n=94), scalp **−0.15** (n=388), swing `ready=false`. ⚠️ **All 5 live fills routed through `daytrade_1h` / `daytrade_1h_eurgbp` — the mode whose own learner analysis is negative in every confidence band and every regime.** **No tier change executed.** Lint: `tier_integrity_check --check` PASS (2 warnings, both pre-existing: `hull_donchian_fade` QUICK_HARVEST_EXEMPT, no strategy file for `ob_retest` — and its "no production firing in 30+ days" claim is again contradicted by 12 `ob_retest` rows in today's audit); `sync_kb_index --check` failed on the **date stamp only** (2026-08-20 → 08-23), cleared with `--write`; broken wikilinks **7 in index.md** (the same 5 auto-generated portfolio-block refs + 2 trade-log refs) / **1 in strategies/** / 76 KB-wide under a stricter path-resolving check than prior runs used — **0 new from this run**. Audit pulled at **limit=800** (2026-08-12 05:46 → 08-21 18:46 UTC, total 15,756); `limit=30` would again have reported **0 live fills** — 3rd consecutive confirmation of `feedback_audit_limit30_hides_live_fills`. See [[2026-08-23]]. Still-open: `API_AUTH_TOKEN` watchdog gap / `sr_anti_hunt_bounce` corruption / learner blacklist no-op / 🔴 **carry-dip declared 150p SL vs observed 18.8p substitution — now the highest-value open item, since 9 live fills have closed on the only positive cell in the book** / zero-unit emissions (reclassified, above) / Price-Shock family demote decision.
- **2026-08-20 wiki-daily-update** — ⚠️⚠️ **24-day cadence gap (07-28 → 08-19), the longest in this log, and unlike every recent gap the book moved through it.** N=**573** (**+10 closed fills** vs 07-27's 563 — the 5-snapshot flat run 07-16=07-21=07-23=07-24=07-27 is broken; 245W/284L/34BE → **249W/290L/34BE** = +4W/+6L, new-cohort decided WR **40.0%**), WR=43.5% (flat), decided 46.2% (−0.1pp), EV=**−1.15** (−0.17), PnL=**−660.3pip** (**−107.6**), Wilson 42.0 / BF 39.3, avg R 0.11, ruin=0.0% ✅. shadow_count 10,456→**12,241 (+1,785)**. 🔴🔴🔴 **DD=1209.1pip = 120.9%** on the legacy $1000 pip basis (**NEW HIGH, +201.1pip**; eq −$1192.2 vs peak +$16.9 flat). ⚠️ **Two representation changes in this pull, neither is movement**: (a) the API's `dd_pct` field switched to the **JPY NAV ledger** and now reads **0.097 = 9.7%** (base ¥359,109 / peak ¥359,288.47 / current ¥324,461.58 / DD ¥34,826.89) — the v2.3 "実 NAV(JPY) 基準へ移行" item landing; **100.8% → 9.7% is a unit change, not a recovery**, and the like-for-like pip series continues at 120.9%; (b) MC `initial_capital` rebased **1000 → 5801.44**, so worst DD99 170.0→**1037.72** and median final eq 881.0→**5159.73** are scale artifacts — normalized, the forward model is ≈unchanged (tail 17.0%→**17.9%**, median max DD 12.1%→**11.45%**). Overall edge (risk dash) **−32.01%** (⚠️ **worsened −6.32pp vs −25.69% — real deterioration, not the usual window-roll easing**: risk-window WR 57.89%→40.0%, odds 0.2835→0.6998); 30d net **−107.6 (n=10)**, per-trade **−10.76** (5.4× worse than −1.99), friction 4.82/trade; Sharpe −0.2259, DSR 0.0/haircut 100%/n_trials 3; VaR95/VaR99/CVaR95 blew out 13.58/19.26/19.0 → **81.31/114.82/123.2**. 🔴 **The entire window loss is one cell**: `price_shock_rev_aud_jpy_h1_long` **n=2, −122.6pip, mean −61.3/trade** — against its 12.3y MASSIVE BT of N=426/WR 63.8%/PF 2.54/**EV +32.25pip**. Strip those 2 AUD_JPY trades and the 30d book is **+15.0 on n=8**. Its own LOCK criteria are unmet (deactivate at N=15 w/ Wilson_lo<0.40; watchdog auto-demote at N≥10 w/ EV<0) so **no demote was executed** — flagged for user decision rather than waiting for N=10 at −61 pip/trade. 🟢 **4 confirmed LIVE fills, all `usdjpy_carry_dip_accumulator` USD_JPY BUY 1000u** — oanda **#677402** (08-14 06:02), **#677910** (08-16 23:02), **#677917** (08-17 06:52), **#677924** (08-19 01:05); all with real trade ids ⇒ **0 false-sent** (07-02 accept/reject contract holding). Its 07-02 zero-fire dormancy (CEILING 159.5 stranded under a 161–162.8 market) **resolved exogenously** — USD_JPY traded back to ~159.47–159.62, re-arming the `close < 159.50` gate; cumulative live N=7, WR 42.9%, **+45.1pip**, but DSR says not significant (Sharpe 0.2189 < threshold 0.368, z=−0.361). Audit pulled at **limit=500** (2026-08-13 00:17 → 08-20 06:11 UTC, total 15,584): 466 shadow / **26 agg-kelly blocks** (−0.349…−0.371<0, gate genuinely load-bearing this window) / 8 live rows. ⚠️ **limit=30 would have shown 0 live fills** — it covers only ~6h and misses all four (`feedback_audit_limit30_hides_live_fills` confirmed again). Firing 08-19→08-20: dual_sr_bounce(19)/xs_momentum_rsi(18)/wick_imbalance_reversion(16)/sr_break_retest(14); USD_JPY(47) most active. 🔴 **New anomaly: `ob_retest` emitted 5 GBP_JPY BUY signals with `units: 0`** on 08-20 (shadow only, no exposure) — and `tier_integrity_check` both lacks a strategy file for it and calls it a "legacy dead inline, no firing in 30+ days", which today's audit contradicts. Learner: 🆕 **new adjustment id=93 (08-19 14:25 UTC)**, first since id=92 (07-06) — but it is the **4th byte-identical** `sr_channel_reversal` blacklist re-affirm (WR 25.0%/EV −0.98/n=190, unchanged since 06-30) while `current_params.entry_type_blacklist` is still **`[]`** ⇒ **the blacklist write is a no-op and the learner re-fires it forever**. daytrade EV −2.60 (n=94, all conf bands and all regimes negative, TREND_BEAR −5.66); scalp EV −0.15 (n=388, only low-conf +0.48 positive). **No tier change executed.** Lint: `tier_integrity_check --check` PASS; `sync_kb_index --check` failed on the date stamp only (content in sync — the 07-18 portfolio drift is resolved), cleared with `--write`; 14 broken wikilinks, all pre-existing (7 in index.md incl. the 5 auto-generated portfolio-block refs to non-existent strategy pages; 7 in strategies/), **0 new**. See [[2026-08-20]]. Still-open: `API_AUTH_TOKEN` watchdog gap / `sr_anti_hunt_bounce` corruption / learner blacklist no-op / **carry-dip declared 150p SL vs observed 18.8p substitution** (now material — 7 live fills closed on the only positive cell) / `ob_retest` zero-unit emissions.
- **2026-07-27 wiki-daily-update** — N=**563** (**flat — 0 closed fills, 5th consecutive snapshot** 07-16=07-21=07-23=07-24=07-27; 245W/284L/34BE unchanged), WR=43.5% (flat), decided 46.3% (flat), EV=**−0.98** (flat), PnL=**−552.7pip** (flat), ruin=0.0% ✅. **Every portfolio-level number identical since 07-16** — no realized book movement. shadow_count 10,345→**10,456 (+111)** (shadow-side firing continues; live/closed book static). 🔴🔴🔴 **DD=100.8%** held (**no new high, no deepening** — book static; eq=−$991.1 vs peak +$16.9 flat; ruin 0% pinned by 0.2× lot cap). Overall edge (risk dash) **−25.69%** (🟢 eased +7.34pp vs 07-24's −33.03% — **window-roll only**: 0 fills, 30d window rolled n 47→38, a net-negative 9-trade cohort aged out, NOT a real edge gain); net **−75.6pip** (n=38, eased), per-trade −1.99, friction 4.24/trade; Sharpe −0.3258 (eased), DSR 0.0/haircut 100%/n_trials 11. MC tail **narrowed** (worst DD99 215.72→**170.0**, median max DD 165.52→**120.88**, median final eq 835.84→**881.0**). ⚪ **0 live fills / 0 agg-kelly blocks / 0 false-sent** — all 30 audit records (07:46→11:22 UTC) shadow_tracking; firing session_time_bias(8)/london_breakout(8); GBP_USD most active(14). Learner: **no new adjustment** (latest still id=92, 07-06 sr_channel_reversal scalp blacklist re-affirm); current_params unchanged. Per-strategy Kelly: only bb_rsi_reversion +edge (+0.1584, WR 72.7%, n≈11). No tier change (flat window). ✅ Normal Monday resume (07-24→07-27 crosses FX weekend, no anomalous gap). See [[2026-07-27]]. Still-open: API_AUTH_TOKEN watchdog gap (agg-kelly gate is active safety net) + sr_anti_hunt_bounce corruption + index.md narrative-section (System State) still stale at 07-08 on this working copy (separate reconciliation item).
- **2026-07-08 wiki-daily-update** — N=**558** (**flat — 0 closed fills vs 07-07**; 243W/282L/33BE unchanged), WR=43.5% (flat), decided 46.3% (flat), EV=**-0.97** (flat), PnL=**-540.7pip** (flat), ruin=0.0% ✅. **Every portfolio-level number identical to 07-07** — no realized book movement. shadow_count 8,832→**8,970 (+138)** (shadow-side firing continues; live/closed book static). 🔴🔴🔴 **DD=100.01%** held (**no new high** — 07-07's 100%-barrier breach was not extended because the book didn't move; eq=−$983.2 vs peak +$16.9 flat; ruin 0% pinned by 0.2× lot cap). Overall edge (risk dash) **-30.1%** (EASED +0.69pp vs 07-07's -30.79% — **window-roll only**, one EUR_JPY loser aged out, NOT a real edge gain); net **-244.3pip** (+7.5 eased), friction 4.01/trade; Sharpe -0.399, DSR 0.0/haircut 100%. **30d by-instrument (n=93, all 4 negative)**: **GBP_USD #1 drag -136.7 (mean -3.51, n=39, flat)** / USD_JPY -51.8 (flat) / EUR_JPY -30.5 (n=17→16, eased +7.5) / EUR_USD -25.3 (flat). MC tail narrowed (worst DD99 215.76→**213.16**, median final eq 838.83→**842.39**). ⚪ **0 live fills / 1 agg-kelly block** — `vsg_jpy_reversal` EUR_JPY blocked `agg_kelly=-0.333<0` @ 09:16 UTC (aggregate-Kelly gate = active safety net, contrast 07-07 which had 1 fill pass); 07-07's #549086 still **open** (N flat). Audit (08:36→11:46 UTC) = **0 LIVE / 29 shadow / 1 blocked / 0 false-sent**; firing session_time_bias(7)/london_breakout(6); GBP_USD most active(16). audit total=11,730 (+145). Learner: **no new adjustment** (latest still id=92, 07-06 sr_channel_reversal scalp blacklist re-affirm); current_params unchanged. No tier change (flat window). 📋 Separately: **T2 exit-repair verdict FAIL/H0** landed 07-08 (grid 9/9 BH-FDR fail p=1.0, WF 0/3) → v2.3 main line pivots to WS3 signal re-authoring ([[exit-repair-tp-sl-prereg-2026-07-07]] §8). Still-open: API_AUTH_TOKEN watchdog gap (agg-kelly gate is active safety net) + sr_anti_hunt_bounce corruption.
- **2026-07-07 wiki-daily-update** — N=**558** (+2 fills vs 07-06, **0W/2L** = −9.2pip aggregate ≈−4.6pip each; exact cell not pinned, GBP_USD most active live-side), WR=43.5% (−0.2pp), decided 46.3% (−0.2pp), EV=**-0.97** (−0.01), PnL=**-540.7pip** (−9.2pip), ruin=0.0% ✅. 🔴🔴🔴 **DD=100.01%** (+0.68pp vs 99.33% — **100% BARRIER BREACHED for the first time**; the −$1000/100% line that all of June/July ground toward is now through; eq=−$983.2 vs peak +$16.9, slow grind not spike — reached on a modest 2-loss window; realized ruin held at 0% by the 0.2× lot cap only). Overall edge (risk dash) **-30.79%** (⚠️ **WORSENED −1.16pp vs 07-06's -29.63%** — breaks the multi-window "eased on roll" pattern: the 2 fresh losses exceeded what aged out); net **-251.8pip** (−9.2), friction 4.02/trade; Sharpe -0.408, DSR 0.0/haircut 100%. **30d by-instrument (n=94, all 4 negative)**: **GBP_USD #1 drag -136.7 (mean -3.51, n=39)** / USD_JPY -51.8 / EUR_JPY -38.0 / EUR_USD -25.3. MC tail widened (worst DD99 212.58→**215.76**, median final eq 841→**838.83**). 🟢 **1 CONFIRMED LIVE FILL** — dt_bb_rsi_mr/daytrade_gbpusd GBP_USD 1000u **oanda#549086** filled @ 06:41 UTC (pnl null, **open**); **first confirmed live fill since 06-24 (#541666)**; the paired `sent`/`filled` rows are the twin-meaning dual-record of the same real order (NOT a false-sent — real trade id present). Audit (06:17→11:52 UTC) = **1 LIVE / 28 shadow / 0 blocked / 0 false-sent**; firing dual_sr_bounce(9)/USD_JPY most active(12). Learner: new adj id=92 (07-06, sr_channel_reversal scalp blacklist re-affirm WR25%/EV-0.98/n190); daytrade all-conf EV-negative (high WR44.8/EV-0.33 least-bad); bb_rsi_reversion sole +Kelly (+0.158, n=11). shadow_count≈8,832 (+95). No tier change. Still-open: API_AUTH_TOKEN watchdog gap (agg-kelly gate is active safety net) + sr_anti_hunt_bounce corruption.
- **2026-07-06 wiki-daily-update** — N=**556** (+1 fill vs 07-03; **07-04/05 weekend market closed** → effectively 1-fill window), WR=43.7% (−0.1pp), decided 46.5% (−0.1pp), EV=**-0.96** (−0.01), PnL=**-531.5pip** (−3.6pip), ruin=0.0% ✅. The single fill reconciles to **orb_trap** (N=3→4, PnL +26.8→+23.2, WR 66.7%→50% = one **−3.6pip loss**, 0W/1L) — the entire book move; notable as `orb_trap` is the standing #1 LIVE-promotion candidate (aggregate now WR 50% N=4). DD=**99.33%** (+0.36pp ⚠️⚠️⚠️ **NEW HIGH — <$24 from −$1000/100%**, slow grind, eq=−$976.4 vs peak +$16.9) — one small loss set a fresh high because the book trough is that close to the mark. Overall edge (risk dash) **-29.63%** (eased vs 07-03's -32.3% on window-roll as early-June trades aged out, NOT real edge gain); net **-242.6pip** (+40.1 eased), friction 3.98/trade; Sharpe -0.398, DSR 0.0/haircut 100%. MC tail eased (worst DD99 226.36→**212.58**, median final eq 829→**841**). Per-instrument attribution not in this fetch; prior read stands (GBP_USD #1 drag). Audit (06:37→12:01 UTC) = **0 LIVE / 30 shadow / 0 `sent` / 0 blocked** — bridge clean, no false-`sent` (07-02 contract fix holding); firing session_time_bias(6)/vol_momentum_scalp(6)/trendline_sweep(5). Learner stable (sr_channel_reversal scalp blacklist re-affirmed, WR25%/EV-0.98). shadow_count≈8,737 (+82). No tier change. Still-open: API_AUTH_TOKEN watchdog gap (agg-kelly gate is active safety net) + sr_anti_hunt_bounce corruption.
- **2026-07-03 wiki-daily-update** — N=**555** (+13 fills vs 07-02: **9W/4L/0BE ≈69% decided WR** — best W/L mix in recent log, breaks the 07-02 blowout), WR=43.8% (+0.6pp ✅), decided 46.6% (+0.6pp), EV=**-0.95** (+0.01 ✅), PnL=**-527.9pip** (−6.8pip — mildest single-window change since the recovery run; sized-loss asymmetry keeps net ~flat despite 9-4 wins), DD=**98.97%** (+0.77pp ⚠️⚠️⚠️ **NEW HIGH — <$28 from −$1000/100%**, slow grind not spike, eq=−$972.8 vs peak +$16.9), ruin=0.0% ✅. 30d Kelly edge **-32.3%** (eased +3.42pp from 07-02 evening's -35.72% — **window-roll only**, n 109→99 as USD_CHF + early-June trades aged out, NOT real edge gain; WR 53.54%, odds 0.265). **30d gross=net=-282.7pip** (eased +27.3 on roll; friction 388.8/3.93 per-trade). All 4 remaining instruments negative: **GBP_USD #1 drag -134.4 (mean -3.54, n=38)**; USD_JPY -49.4; EUR_JPY -51.1; EUR_USD -47.8 (eased on roll); USD_CHF rolled out of window. MC tail ≈flat (worst DD99 226.36%, median max DD 172.3%). 🟢 **Aggregate Kelly gate correctly blocked 1 live entry** (`agg_kelly=-0.326<0`) — primary active safety net functioning while watchdog cron stays silent. **0 LIVE / 29 shadow / 0 `sent`** (no false-`sent` — 07-02 accept/reject contract fix holding). No new Learning adjustment since id=91 (07-01, sr_channel_reversal blacklist). shadow_count≈8,655 (+173). Still-open: API_AUTH_TOKEN watchdog gap + sr_anti_hunt_bounce corruption.
- **2026-07-02 wiki-daily-update** — N=**542** (+23 fills vs 06-25 evening: **11W/11L/1BE** even split; ~7-day window, no log 06-26〜07-01), WR=43.2% (+0.2pp), decided 46.0%, EV=**-0.96** (−0.14 ⚠️), PnL=**-521.1pip** (**−94.8pip ⚠️⚠️⚠️ steepest single-window drop in log** — even W/L but sized losses dominate), DD=**98.2%** (+7.65pp ⚠️⚠️⚠️ **NEW HIGH — 100%接近**, eq=-$965.1 vs peak +$16.9), ruin=0.0% ✅. 30d Kelly edge **-37.03%** (from -27.77%, −9.26pp — **7th straight deteriorating window**, WR=47.32%, odds 0.331). **30d gross=net=-321.7pip** (from -207.2, **−114.5 steepest single-window gross drop**; n=112, friction 462.3pip/4.13, friction also rose). **All 5 instruments negative & all worsened**: GBP_USD #1 drag -139.9 (mean -3.33, n=42); EUR_USD #2 -84.4; EUR_JPY blew out -9.2→-46.0; USD_JPY -40.4; USD_CHF -11.0 flat. MC tail blew out: worst-case DD99=**227.92%**, median max DD(MC)=**175.08%**. 🟡 **1 false `sent` 07-01 20:16 UTC (NO real order — forensic-corrected)**: wick_imbalance_reversion GBP_USD BUY 5000u logged `bridge_status=sent` with oanda_trade_id empty; a same-day forensic session (rule:R3) proved the bridge `daily_loss` gate (−23.3pip) **correctly blocked** it and the caller wrote a bogus `'sent'` — **no live order was placed**. The earlier "live bridge fired anyway" reading was wrong (fix: accept/reject contract, `tests/test_bridge_send_accept_contract.py`). Audit (07-01 18:12→07-02 05:02) = 1 false-sent + 1 blocked + 28 shadow_tracking. Learning: 2 new adjustments id=90(06-30)/id=91(07-01) re-affirming sr_channel_reversal scalp blacklist (WR25%/EV-0.98). strategy_kelly: no positive-edge strategy. shadow_count≈8,482 (+547). EDGE_CELL_ADMIN_TOKEN/API_AUTH_TOKEN watchdog gap + sr_anti_hunt_bounce corruption still unresolved. **[Evening re-run 2026-07-02]**: 0 new fills; 30d window rolled n=112→109, edge -37.03→-35.72% / gross -321.7→-310.0 eased (EUR_USD -84.4→-72.7 rolled out); DD 98.2%/eq -$965.1 unchanged; fresh audit 07:52→11:12 UTC = 0 LIVE / all 30 shadow (dt_sr_channel_reversal 16 dominates).
- **2026-06-25 wiki-daily-update (EOD / evening re-run)** — N=**519** (+3 intraday: **2W/1L/0BE**; +6 vs 06-19), WR=43.0% (+0.2pp), decided 45.8%, EV=-0.82, PnL=**-426.3pip** (−2.8pip vs morning's N=516 capture; **+3.2pip vs 06-19**), DD=**90.55%** (+0.43pp ⚠️ **NEW HIGH resumed** — morning's flat pause was one-window-only, eq=-$888.6), ruin=0.0% ✅. 30d Kelly edge **-27.77%** (eased +1.05pp from morning's -28.82%, WR=48.62%, odds 0.485 — window rolled past worse stretch; still worse than 06-19 -24.75%). **30d gross=net=-207.2pip** (n=109, friction 408.4pip/3.75; eased +4.3 from morning's -211.5). By-instrument 30d: GBP_USD #1 drag -106.7 (mean -3.23); USD_JPY eased -39.3→-32.2 (#2). MC tail eased: worst DD99=**170.42%**, median max DD(MC)=**118.30%**. Evening audit (09:38→11:47 UTC) = **0 LIVE, all 30 shadow_tracking** (#541666 aged out); session_time_bias dominates shadow firing 14/30 despite being #1 cumulative loser (-67.8). strategy_kelly: no positive-edge strategy. Morning capture (same day): N=516/-423.5pip/DD 90.12% flat/edge -28.82%; 1 LIVE filled 06-24 (trendline_sweep #541666). shadow_count≈7,935.
- **2026-06-25 wiki-daily-update** — N=**516** (+3 fills: **3W/0L/0BE — all winners, breaks the 5-loss run**; ~6-day window vs 06-19, 06-20/21 weekend + no log 06-22/23/24), WR=42.8% (+0.3pp ✅), decided 45.7%, EV=-0.82 (+0.02 ✅), PnL=**-423.5pip** (**+6.0pip ✅ first cumulative improvement in recent log**), DD=**90.12%** (flat — **first non-NEW-HIGH in 5 snapshots** ✅, eq=-$884.3 unchanged), ruin=0.0% ✅. 30d Kelly edge **-28.82%** ⚠️⚠️⚠️ (from -24.75% — 6th straight deteriorating window, WR=47.66%, odds 0.493). **30d gross PnL -211.5pip** (-42.7→-70.1→-96.1→-113.8→-179.2→-211.5 over 6 windows) — gross/directional edge dominant, friction flat-to-down (397.7pip). ⚠️⚠️ **USD_JPY 30d blew out -1.4→-39.3pip** (#2 drag); GBP_USD eased -113.4→-108.7 but stays #1 (mean -3.40); all 5 instruments negative. 🟢 **1 LIVE filled 06-24 17:27 UTC**: trendline_sweep → daytrade_gbpusd GBP_USD SELL 5000u **oanda#541666** (first *confirmed* fill since the 06-16/17/19 awaiting-fill sends). MC tail kept widening: worst-case DD99=**172.62%**, median max DD(MC)=**122.13%**. The +3 wins landed on recovering losers (trendline_sweep -19.0→-17.0, wick_imbalance -59.3→-57.0, vsg_jpy_reversal -18.2→-15.8); strategy_kelly shows no positive-edge strategy this window (vix_carry_unwind dropped off). No new Learning adjustment since id=89 (06-19). shadow_count=7,861 (+346).
- **2026-06-19 wiki-daily-update** — N=**513** (+5 fills: 0W/5L/0BE — all losing; 2-day window vs 06-17 evening, 06-18 was Month-End-fix pre-reg/REJECT), WR=42.5% (−0.4pp), decided 45.3%, EV=-0.84, PnL=**-429.5pip** (−51.7pip ⚠️⚠️ steepest cumulative drop in recent log), DD=**90.12%** (+3.48pp ⚠️⚠️ NEW HIGH — **90% barrier breached**, eq=-$884.3), ruin=0.0% ✅. 30d Kelly edge **-24.75%** ⚠️⚠️⚠️ (from -16.95% — 5th straight deteriorating window, WR=46.79%, odds 0.608). **30d gross PnL -179.2pip** (-42.7→-70.1→-96.1→-113.8→-179.2 over 5 windows, -65.4 steepest single-window drop) — gross/directional edge dominant & accelerating, friction now flat. ⚠️⚠️ **Every 30d instrument negative**: JPY crosses flipped (EUR_JPY +19.1→-5.3, USD_JPY +16.3→-1.4) — book's only positive anchors gone; GBP_USD blew out to **-113.4pip** (#1 drag, mean -3.54). MC tail blew out: worst-case DD99=**161.02%**, median max DD(MC)=**103.74%** (>100%). 🔴 3 LIVE sent 06-19 (dt_sr_channel_reversal EUR_JPY SELL 5000u + zz_pivot_v60_sr EUR_USD SELL 5000u ×2; demo gate blocked, live bridge sent). vix_carry_unwind +5.1→-12.6 & vsg_jpy_reversal +6.2→-18.2 flipped to losers; wick_imbalance -39.3→-59.3. Learning id=89 (06-19): sr_channel_reversal promoted to top-level blacklist. shadow_count=7,515 (+313).
- **2026-06-17 wiki-daily-update (EOD / evening re-run)** — N=**508** (+3 intraday fills: 0W/2L/1BE, no winners; +8 vs 06-16), WR=42.9% (−0.3pp), decided 45.8%, EV=-0.74, PnL=**-377.8pip** (−43.7pip vs 06-16 / −17.7pip vs morning's N=505 capture ⚠️⚠️ steepest two-stage daily decline in recent log), DD=**86.64%** (+1.82pp ⚠️⚠️ NEW HIGH again, eq=-$849.5), ruin=0.0% ✅. 30d Kelly edge **-16.95%** ⚠️⚠️⚠️ (from -14.99% — 4th straight deteriorating window, WR=50.0%, odds 0.661). **30d gross PnL -113.8pip** (-42.7→-70.1→-96.1→-113.8 over 4 windows) — gross/directional edge dominant & still growing; "friction is primary" no longer holds. Median max DD(MC)=**71.4%** (from 63.94%), VaR95/CVaR95=11.68/14.65pip. Evening audit (ids 9389-9418) = **0 LIVE, all 28 shadow_tracking** (the 3 06-16 LIVE sends aged out). Morning capture (same day): N=505/-360.1pip/DD 84.82%/edge -14.99%; 3 LIVE sent 06-16 (zz_pivot_v60_sr EUR_USD SELL 5000u + sr_fib_confluence GBP_USD BUY ×2, demo gate blocked, live bridge sent), sr_fib_confluence flipped +12.6→-0.5pip after its GBP_USD LIVE fills lost. shadow_count=7,202.
- **2026-06-16 wiki-daily-update** — N=500 (+7 fills: 5W/2L/0BE ≈71% WR, 3rd positive-WR session), WR=43.2% (+0.4pp ✅), EV=-0.67, PnL=-334.1pip (-15.0pip ⚠️ — favorable WR ≠ PnL, sized losses dominate), DD=**83.77%** (+2.35pp ⚠️⚠️ NEW HIGH, eq=-$820.80), ruin=0.0% ✅. 30d Kelly edge **-11.94%** ⚠️⚠️⚠️ (from -7.66% — deteriorating, WR=51.0%, odds 0.727). **30d gross PnL -70.1pip (from -42.7)** — ⚠️ loss source shifted: no longer friction-only, gross/directional edge now also negative. Worst-case DD(99%)=**106.84%** (>100% first time), median max DD=53.28%. GBP_USD now #1 30d drag (-50.2pip > EUR_USD -44.3). 2 LIVE fills 06-15 (doji_breakout GBP_USD + zz_pivot_v60_sr EUR_USD, both 5000u). First full log since 06-12 (06-13/14 weekend). shadow_count=7,059.
- **2026-06-12 wiki-daily-update** — N=493 (+16 fills: 12W/4L/0BE ≈75% WR), WR=42.8% (+1.1pp ✅), EV=-0.65, PnL=-319.1pip (-0.3pip ✅ near-flat), DD=**81.42%** (+1.86pp ⚠️⚠️ NEW HIGH, eq=-$797.30), ruin=0.0% ✅. 30d Kelly edge **-7.66%** ✅ (from -8.4%, WR=49.48%). 🔴 2 LIVE fills (zz_pivot_v60_sr EUR_USD SELL + vix_carry_unwind USD_JPY SELL) — roadmap v2.2 LIVE pipeline confirmed executing. friction=366.8pip dominates, gross≈net=-42.7pip.
- **2026-06-11 wiki-daily-update** — N=477 (+7 fills: 4W/2L/1BE ✅ first day with wins), WR=41.7% (+0.2pp ✅), EV=-0.67, PnL=-318.8pip (-2.4pip ✅ minimal), DD=**79.56%** (−0.47pp ✅ first improvement in 7 sessions), ruin=0.0% ✅. 30d Kelly edge **-8.4%** ✅ (from -10.18% — recovering, WR=45.78%). All 27 audit records shadow_tracking (0 live fills). Monitor anomaly 02:13 UTC: rnb_usdjpy direction_filter=300 + hedge_block=209 + price spike 16049pip artifact.
- **2026-06-10 wiki-daily-update** — N=470 (+5 fills, all losing), WR=41.5%, EV=-0.67, PnL=-316.4pip ⚠️⚠️ (-20.0pip), DD=**80.03%** (+3.03pp ⚠️⚠️⚠️ NEW HIGH — 80% barrier breached for first time, eq=-$783.4), ruin=0.0% ✅. 30d Kelly edge **-10.18%** ⚠️⚠️⚠️ (from -6.52% — deepening rapidly, WR=43.59%, Kelly=0.0%). shadow_count=7,460. All 30 audit records shadow_tracking (0 live fills). EUR_USD 30d -$49.7 (dominant drag). USD_JPY 30d +$26.7 (sole positive anchor weakening).
- **2026-06-08 wiki-daily-update** — N=465 (+1 fill), WR=41.7%, EV=-0.64, PnL=-296.4pip ⚠️ (-7.5pip), DD=**~77.0%** (+0.77pp ⚠️ new high), ruin=0.0% ✅. 30d Kelly edge **-6.52%** ⚠️⚠️⚠️ (from -6.61% — marginal improvement, structurally unchanged). All 30 audit records shadow_tracking (0 live fills). EDGE_CELL_ADMIN_TOKEN Bearer bug pending.
- **2026-06-06 wiki-daily-update** — N=464 (+2 fills, EV=-9.65pip/trade), WR=41.8%, EV=-0.62, PnL=-288.9pip ⚠️ (-19.3pip), DD=**76.23%** (+1.41pp ⚠️ new high), ruin=0.0% ✅. 30d Kelly edge -1.32%→**-6.61%** ⚠️⚠️⚠️ (odds_ratio 0.9736→0.9123, WR 50%→48.84% — below 50%). EUR_JPY 30d +$8.9→**-$5.2** (LIVE fill dt_sr_channel_reversal OANDA#504420). All DSR=0.0 haircut 100%. EDGE_CELL_ADMIN_TOKEN Bearer bug pending.
- **2026-06-05 wiki-daily-update** — N=462 (+6 fills, all losing, EV=-4.07pip), WR=42.0%, EV=-0.58, PnL=-269.6pip ⚠️ (-24.4pip), DD=**74.82%** (+2.25pp ⚠️ new high), ruin=0.0% ✅. 30d Kelly edge turned negative: +1.75%→**-1.32%** ⚠️⚠️ (fraction 0.0%). CB recovery 2026-06-04: E1/E4/E8 stage=0 disabled, all post-recovery signals shadow_tracking ✅. session_time_bias now #1 drag: N=30, WR=40.0%, -67.8pip. EDGE_CELL_ADMIN_TOKEN Bearer bug still pending.
- **2026-06-03 wiki-daily-update** — N=456 (+23 fills, all losing, EV=-1.48pip), WR=42.1%, EV=-0.54, PnL=-245.2pip ⚠️ (-34.1pip), DD=**72.57%** (+4.62pp ⚠️⚠️ LARGEST SINGLE-DAY INCREASE — new high), ruin=0.0% ✅. 30d Kelly collapsed: 6.71%→**0.91%** ⚠️ (WR 61.02%→51.81%). Daily_loss_limit circuit breaker triggered (4 signals blocked). EUR_USD SELL 30d: +$16.5→-$20.10 (reversal). Loss concentrated in E2/E4/E8 cells. EDGE_CELL_ADMIN_TOKEN unset (watchdog silent).
- **2026-05-27 wiki-daily-update** — N=411 (+1 live fill, losing), WR=41.8%, EV=-0.55, PnL=-225.9pip ⚠️ (-6.8pip), DD=66.46% (+0.68pp ⚠️ new high), ruin=0.0% ✅. 30d Kelly=0.0% ⚠️ (regressed from brief 0.8% yesterday — WR 56.72%→55.88%, window effect reversed). USD_JPY 30d +39.6pip (anchor). GBP_USD 30d -27.8pip (drag). OANDA audit: 0 live fills (27 shadow signals).
- **2026-05-26 wiki-daily-update** — N=410 (+2 new live fills ✅), WR=42.0%, EV=-0.53, PnL=-219.1pip ⚠️ (-7.6pip), DD=65.78% (+0.71pp ⚠️), ruin=0.0% ✅. 30d Kelly turned positive: Half-Kelly=0.8%, WR=56.72%, Edge=+1.25% ✅ (window shift). OANDA audit: 0 live fills today (28 shadow signals). trendline_sweep Sharpe=-0.05 (monitor). session_time_bias Sharpe=-0.77.
- **2026-05-21 wiki-daily-update** — N=408 (+4 new live fills ✅), WR=42.2%, EV=-0.52, PnL=-211.5pip ✅ (+38.8pip), DD=65.07% (unchanged), ruin=0.0%, 30d=-66.8pip ✅ (was -104.3pip). vix_carry_unwind 1.0x lot exception active (edge=0.2743). shadow_count=5,857. 30d Sharpe=-0.080. USD_JPY +61.1pip (30d anchor), GBP_USD -73.1pip (main drag).
- **2026-05-07 wiki-daily-update** — N=530 total (shadow+live, post-2026-04-08), WR=38.5%, PnL=-414.2pip (gross), DD=42.21%⚠️ (+1.56pp from 2026-05-03), ruin=2.08%, live fills=4 (GBP_USD×3 + USD_JPY×1 daytrade, OANDA#383016-383039), total system=5,295. bb_rsi N=187 -52.7pip, session_time_bias N=9 WR=22.2% -43.4pip⚠️, vix_carry_unwind N=8 -41.5pip⚠️
- **2026-04-30 session** — Regime Cascade v2.1 実装+commit (binary moderate_trend, L3 slim, SL floor). direction_cells API 追加. B1/B3 監査訂正. 2コミット push
- **2026-04-29 wiki-daily-update** — N=286, WR=38.1%, PnL=-228.6pip, DD=34.76% ⚠️ (from 32.32%), ruin=1.72% (from 2.72%), vol_momentum_scalp唯一正Kelly (+7.78%), live fills=0 (全shadow_tracking), latest OANDA ID=3590
- **2026-04-24 wiki-daily-update** — N=259, WR=39.0%, PnL=-215.0pip, DD=32.32% ⚠️ (from 28.01%), ruin=2.72% ⚠️ (from 0.78%), vwap_mr N=10 -47.7pip OANDA kill-switch適用, live fills=1 (GBP_USD bb_rsi #378534)
- **2026-04-23 wiki-daily-update** — N=255, WR=39.6%, PnL=-171.9pip, DD=28.01%, ruin=0.78% ⚠️ (from 0.04%), vwap_mr N=8 -17.5pip継続悪化, live fills=0
- [[sessions/quant-edge-scan-2026-04-23]] — **🎯 最新** Session/Horizon/Regime 3軸エッジスキャン (T3 Tokyo Range Breakout 確認 / L1 OFI MR / edge_lab T1-T2-D1-R1-S3 実行)
- [[sessions/handover-2026-04-22]] — **🎯 次セッション引き継ぎ** 2026-04-22 総括: TP-hit 分析 + Scalp vwap_mr バグ修正 + Exposure/Resend fix + OSS 横断調査/qlib/pybroker 転用
- [[sessions/handover-tp-hit-quant-analysis-2026-04-21]] — **🎯 次セッション引き継ぎ #2** TP-hit 698件 quant 分析 (family-wise noise 結論、3副次発見: score 予測力ゼロ / confidence 負相関 / spread edge 有意)
- [[sessions/2026-04-22-session]] — TP-hit quant 分析 (research only, 実装なし) + KB ドキュメンテーション強化
- [[vwap-mr-live-analysis-2026-04-22]] — vwap_mr Live 分析 (Scalp vwap_mr バグ修正・kill-switch 判断の根拠データ)
- [[sessions/handover-shadow-deep-analysis-2026-04-21]] — **🎯 次セッション引き継ぎ** Shadow 全戦略 TP/SL 分析 + 戦略分割
- [[sessions/2026-04-21-session]] — Attack A (bb_squeeze×USD_JPY PAIR_PROMOTED) + Attack B (negative戦略止血条件) + Tier1 BT validation + Quant深部検証
- [[sessions/2026-04-20-session]] — Sentinel score_gate bypass (P1) + N measurement fix (P3) + KB drift fix (P4) + shadow baseline analysis + resend-shadow-leak fix
- [[sessions/2026-04-17-session]] — conditional edge estimand framework + KB整合修正
- [[sessions/2026-04-15-session]] — KB broken-link修正+orphanファイル統合
- [[sessions/2026-04-14-session]] — H15検証+SENTINEL矛盾修正+QHシミュレーション+漏れ分析
- [[sessions/2026-04-13-session]] — v8.9 Equity Reset + KB全面改修(25 Phase) + 4セッションレポート + パイプライン修復
- [[sessions/2026-04-12-session]] — 6新エッジ実装+学術監査+KB構築

## Lessons Learned (間違いと教訓)
- [[lessons/index]] — **過去の間違い・修正・教訓の蓄積** (Shadow汚染, XAU歪み, BT hardcode等)
- 次のセッション開始時に必ず参照すること

## Research & Edge Discovery
- [[research/index]] -- 学術文献インデックス、研究テーマ一覧
- [[edge-pipeline]] -- エッジ仮説の評価パイプライン (6 stages)
- Active themes: [[microstructure-stop-hunting]], [[session-effects]], [[mean-reversion-regimes]]

## Data & Evaluation
- [[changelog]] -- **バージョン別変更+評価基準日タイムライン** (どの期間で評価すべきか)
- Latest snapshot: [[snapshot-2026-04-12]] (250t post-cutoff)
- Friday analysis: [[2026-04-10-friday]] (74t, FX黒字+143pip)

### Friday 4/10 Key Finding
- FX-only: **+143.4 pip (黒字)** / XAU込み: -386.6 pip
- bb_rsi instant death: **60%** (pre-v8.3: 77.6% → v8.3効果の兆候)
- stoch_trend_pullback instant death: **50%** (pre: 83% → 改善)
- fib_reversal instant death: 71% (pre: 75.9% → ほぼ変化なし)

## Links
- [[friction-analysis]] -- Per-pair friction, BEV_WR
- [[changelog]] -- Fidelity Cutoff timeline + version impact matrix
- [[leaked-items]] -- KB漏れ項目トラッキング
- [[log]] -- 作業ログ

## Other Strategies (not in portfolio)
- [[adx-trend-continuation]] / [[donchian-momentum-breakout]] / [[ema-trend-scalp]] / [[ema200-trend-reversal]]
- [[htf-false-breakout]] / [[jpy-basket-trend]] / [[london-breakout]] / [[london-ny-swing]]
- [[london-session-breakout]] / [[london-shrapnel]] / [[mtf-reversal-confluence]] / [[ny-close-reversal]]
- [[streak-reversal]] / [[tokyo-bb]] / [[tokyo-nakane-momentum]] / [[turtle-soup]]
- [[force-demoted-strategies]] -- 降格戦略の一覧と理由

## Data & Archives

### BT Results
- [[bt-120d-v3-all-pairs-2026-04-12]] / [[bt-full-audit-2026-04-12]] / [[bt-grand-audit-2026-04-12]]
- [[bt-scalp-5m-55d-2026-04-12]] / [[bt-v3-friction-model-2026-04-12]]
- [[bt-v85-all-pairs-2026-04-12]] / [[bt-v85-new-edges-2026-04-12]] / [[bt-v86-time-expansion-2026-04-12]]
- [[comprehensive-bt-scan-2026-04-14]] / [[massive-alpha-scan-2026-04-14]] / [[shadow-bt-reeval-2026-04-14]]
- [[bt-live-divergence-scan-2026-04-22]] / [[bt-live-divergence-v3-full-stack-2026-04-22]] — 365d JPY DT + 180d Scalp fresh BT

### Trade Logs
- [[2026-07-08]] — daily summary (auto-generated 2026-07-08) — ⚪ **flat day: 0 closed fills** (all portfolio numbers = 07-07); DD **100.01% held, no new high**; edge EASED -30.1% (window-roll only); 0 live fills / 1 agg-kelly block (vsg_jpy_reversal EUR_JPY); 📋 T2 exit-repair FAIL landed
- [[2026-07-07]] — daily summary (auto-generated 2026-07-07) — 🔴🔴🔴 DD **100.01% — 100% BARRIER BREACHED**; edge WORSENED -30.79%; 🟢 1 confirmed live fill #549086 (open), first since 06-24; +2 fills 0W/2L
- [[2026-07-06]] — daily summary (auto-generated 2026-07-06) — ⚠️⚠️⚠️ DD 99.33% NEW HIGH (<$24 from 100%); 🟡 1 fill (orb_trap −3.6pip loss), weekend closed; ✅ 0 live/0 blocked/0 false-sent
- [[2026-07-03]] — daily summary (auto-generated 2026-07-03) — ⚠️⚠️⚠️ DD 98.97% NEW HIGH (<$28 from 100%); ✅ 9W/4L window, agg-kelly gate blocked 1 live
- [[2026-07-02]] — daily summary (auto-generated 2026-07-02) — ⚠️⚠️⚠️ DD 98.2% NEW HIGH, PnL −94.8pip steepest drop
- [[2026-06-25]] — daily summary (auto-generated 2026-06-25)
- [[2026-06-19]] — daily summary (auto-generated 2026-06-19)
- [[2026-06-17]] — daily summary (auto-generated 2026-06-17)
- [[2026-06-16]] — daily summary (auto-generated 2026-06-16)
- [[2026-06-12]] — daily summary (auto-generated 2026-06-12)
- [[2026-06-11]] — daily summary (auto-generated 2026-06-11)
- [[2026-06-10]] — daily summary (auto-generated 2026-06-10)
- [[2026-06-06]] — daily summary (auto-generated 2026-06-06)
- [[2026-06-05]] — daily summary (auto-generated 2026-06-05)
- [[2026-06-03]] — daily summary (auto-generated 2026-06-03)
- [[2026-05-27]] — daily summary (auto-generated 2026-05-27)
- [[2026-05-26]] — daily summary (auto-generated 2026-05-26)
- [[2026-05-21]] — daily summary (auto-generated 2026-05-21)
- [[2026-05-07]] — daily summary (auto-generated 2026-05-07)
- [[2026-04-29]] — daily summary (auto-generated 2026-04-29)
- ~~[[2026-04-27]]~~ — daily summary (auto-generated 2026-04-27)
- [[2026-04-27-monitor]] / [[2026-04-27-pre_tokyo]] / [[2026-04-27-post_tokyo]]
- [[2026-04-24]] — daily summary (auto-generated 2026-04-24)
- [[2026-04-23]] — daily summary (auto-generated 2026-04-23)
- [[2026-04-22]] — daily summary (auto-generated 2026-04-22)
- [[2026-04-21]] — daily summary (auto-generated 2026-04-21)
- [[2026-04-21-monitor]] / [[2026-04-21-pre_tokyo]] / [[2026-04-21-post_tokyo]]
- [[2026-04-20]] — daily summary (auto-generated 2026-04-20)
- [[2026-04-20-monitor]] / [[2026-04-20-post_tokyo]]
- [[2026-04-15-pre_tokyo]]
- [[2026-04-14-monitor]] / [[2026-04-14-pre_tokyo]] / [[2026-04-14-post_tokyo]]
- [[2026-04-14-quant-analysis]] / [[2026-04-14-detailed-quant-analysis]]
- [[2026-04-13-monitor]] / [[2026-04-13-pre_tokyo]] / [[2026-04-13-post_tokyo]] / [[2026-04-13-post_ny]]
- [[2026-04-10-friday]]
- [[analyst-memory]] / [[analyst-memory-archive]]

### Market Analysis
- [[2026-04-14-regime]] / [[2026-04-13-regime]]

### Audits
- [[2026-04-13-weekly]] / [[2026-04-13-ev-decomposition]]
- [[alpha-scan-2026-04-13]] / [[alpha-scan-2026-04-14]] / [[alpha-scan-2026-04-15]]

### Analyses
- [[auto-improvement-pipeline]] / [[bt-live-divergence]] / [[claude-harness-design]]
- [[friction-analysis]] / [[mfe-zero-analysis]] / [[system-reference]]
- [[conditional-edge-estimand-2026-04-17]] / [[portfolio-balance-audit-2026-04-17]] / [[regime-tag-validation-2026-04-17]]
- [[mtf-regime-validation-2026-04-17]] — MTF engine + Phase A-E (strategy-aware alignment, P0 forensics, A/B gate, REGIME_ADAPTIVE)
- [[edge-matrix-2026-04-23]] — Session × Horizon × Regime quant edge hypothesis map (T1-T4/L1-L3/N1-N3/S1-S4/D1-D3/R1-R3/TR1-TR4)
- [[spread-at-entry-confounding-2026-04-23]] — handover p=1.9e-5 edge が Simpson's paradox 由来と判定 (INVALIDATED)
- [[score-predictive-power-2026-04-23]] — score aggregate p=0.55 noise 確認 + bb_rsi_reversion で inverse 傾向 (N>=200 で再検証)
- [[phase2a-deploy-status-2026-04-23]] — Phase 2a 3 commit deploy 確認 + Phase 2a.1 未配線 (registry 定義のみ、MTF gate 未変更). holdout 2026-05-07 まで保留

### Syntheses
- [[profit-projection-2026-04-12]] / [[roadmap-to-100pct]] / [[roadmap-v2]] / [[roadmap-v2.1]]
