# FX AI Trader Knowledge Base

## 🎯 最重要目標: 月利21.6% (数学的上限) への段階接近 — 2026-06-12 再設定
**全施策の判断基準。これに寄与しない施策は後回し。**
- 現在: **DD防御0.2x** (DD=**90.55%** NEW HIGH再開, defensive mode — 2026-06-25 evening) → 月利47%（BT推定、クリーンデータ蓄積中）
- 旧目標「月利100%」「Phase 3 月利594%」は TP-HIT 12-cell 検証で数学的不可能と確定、user 承認で再設定 (roadmap v2.2 T12)
- 詳細: **[[roadmap-v2.2-win-conversion]]** (LIVE負け→勝ち転換、2026-06-12) / 旧: [[roadmap-v2.1]]
- 旧: [[roadmap-v2]] (v2.0) / [[roadmap-to-100pct]] (v1)
- **最優先: クリーンデータ蓄積 → Kelly Half到達**

## 🔗 Cross-KB Navigation
- **[[audit-index]]** — `learning/` 18 audit ノード + MEMORY `project_*.md` 双方向マップ（次セッション Claude 必読、KB↔MEMORY 棲み分けルール記載）

<!-- KB_PORTFOLIO_START -->
## Current Portfolio (auto-synced, 2026-06-12)

### ELITE_LIVE (never shadowed)
| Strategy | BT Data | Status |
|----------|---------|--------|
| [[trendline-sweep]] | EUR_USD: EV=+0.927 WR=80.8%; GBP_USD: EV=+0.599 WR=73.1% | ELITE_LIVE |

### PAIR_PROMOTED (SENTINEL)
| Strategy | Pairs | BT Data | Status |
|----------|-------|---------|--------|
| [[bb-squeeze-breakout]] | EUR_USD | no BT data | PAIR_PROMOTED |
| [[doji-breakout]] | GBP_USD, USD_JPY | GBP_USD: EV=+0.724 WR=78.3%; USD_JPY: EV=+0.338 WR=61.9% | PAIR_PROMOTED |
| [[donchian-momentum-breakout]] | NZD_JPY, NZD_USD | no BT data | PAIR_PROMOTED |
| [[dt-bb-rsi-mr]] | USD_JPY | EUR_USD: EV=-0.077 WR=52.0%; GBP_USD: EV=-0.135 WR=51.3%; USD_JPY: EV=-0.023 WR=54.2% | PAIR_PROMOTED |
| [[dt-sr-channel-reversal]] | EUR_JPY | EUR_JPY: EV=+0.178 WR=63.8% | PAIR_PROMOTED |
| [[ema200-trend-reversal]] | USD_JPY | EUR_USD: EV=+0.410 WR=75.0%; USD_JPY: EV=-0.183 WR=56.2% | PAIR_PROMOTED |
| [[mqe-gbpusd-fix]] | GBP_USD | no BT data | PAIR_PROMOTED |
| [[pivot-detector-v2-5]] | EUR_USD | no BT data | PAIR_PROMOTED |
| [[price-shock-rev-aud-jpy-h1-long]] | AUD_JPY | no BT data | PAIR_PROMOTED |
| [[price-shock-rev-eur-aud-h1-long]] | EUR_AUD | no BT data | PAIR_PROMOTED |
| [[price-shock-rev-eur-gbp-h1-long]] | EUR_GBP | no BT data | PAIR_PROMOTED |
| [[price-shock-rev-nzd-jpy-h1-long]] | NZD_JPY | no BT data | PAIR_PROMOTED |
| [[price-shock-rev-usd-cad-h1-long]] | USD_CAD | no BT data | PAIR_PROMOTED |
| [[session-time-bias]] | EUR_USD | EUR_USD: EV=+0.215 WR=69.6%; GBP_USD: EV=+0.113 WR=67.1%; USD_JPY: EV=+0.580 WR=79.0% | PAIR_PROMOTED |
| [[squeeze-release-momentum]] | EUR_USD | EUR_USD: EV=+0.656 WR=73.3% | PAIR_PROMOTED |
| [[sr-fib-confluence]] | GBP_USD | EUR_USD: EV=+0.103 WR=64.9%; USD_JPY: EV=+0.252 WR=67.7% | PAIR_PROMOTED |
| [[vix-carry-unwind]] | USD_JPY | USD_JPY: EV=+0.212 WR=67.3% | PAIR_PROMOTED |
| [[vol-momentum-scalp]] | EUR_JPY | no BT data | PAIR_PROMOTED |
| [[vsg-jpy-reversal]] | EUR_JPY | no BT data | PAIR_PROMOTED |
| [[wick-imbalance-reversion]] | GBP_USD | no BT data | PAIR_PROMOTED |
| [[xs-momentum-rsi]] | USD_JPY | no BT data | PAIR_PROMOTED |
| [[zz-pivot-v60-sr]] | EUR_USD | no BT data | PAIR_PROMOTED |
| [[zz-pivot-v60-sr-lo]] | EUR_USD | no BT data | PAIR_PROMOTED |

### SHADOW (Data Collection)
| Strategy | BT Data | Notes |
|----------|---------|-------|
| [[bb-rsi-reversion]] | no BT data | SCALP_SENTINEL |
| [[dt-fib-reversal]] | EUR_JPY: EV=-0.199 WR=54.3%; EUR_USD: EV=+0.407 WR=80.0%; GBP_USD: EV=+0.374 WR=76.2% | UNIVERSAL_SENTINEL |
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
| [[sr-weighted-bounce]] | no BT data | UNIVERSAL_SENTINEL |
| [[sr-weighted-break]] | no BT data | UNIVERSAL_SENTINEL |
| [[streak-reversal]] | no BT data | shadow only |
| [[tokyo-range-breakout-up]] | no BT data | LOT_BOOST (not sentinel/elite) |
| [[turtle-soup]] | GBP_USD: EV=+0.386 WR=69.7% | LOT_BOOST (not sentinel/elite) |
| [[vol-spike-mr]] | USD_JPY: EV=+0.148 WR=64.6% | UNIVERSAL_SENTINEL |
| [[vol-surge-detector]] | no BT data | SCALP_SENTINEL |
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
- Defensive mode: **0.2x** (DD=**90.55%** / 905.5pip — ⚠️ **NEW HIGH resumed** (+0.43pp vs morning's 90.12% flat), eq_current=−$888.6 — Render API 2026-06-25 wiki-daily-update **evening re-run**; 30d Kelly=0.0% edge=**-27.77%** (eased +1.05pp from morning's -28.82% as window rolled forward; still ⚠️ vs 06-19 -24.75%); prev snapshot 06-19 DD 90.12% / edge -24.75%)
- **CB RECOVERY 2026-06-04**: CB auto-triggered at 04:34 UTC (-30.4pip daily loss) → E1/E4/E8 (bb_rsi_reversion + session_time_bias cells) disabled (stage=0) + modes restarted at 06:24 UTC. Post-recovery: all signals shadow_tracking (confirmed). EDGE_CELL_ADMIN_TOKEN watchdog Bearer bug still pending Codex fix.
- HourlyEngine: **Activated 2026-05-18** — all H1 strategies (KSB+DMB+5 PriceShockRev) are Shadow-only via `_shadow_always`.
- XAU: **Stopped** (v8.4) -- post-cutoff XAU loss = -2,280pip (102% of total loss)
- FX-only post-cutoff (2026-04-08〜) — **2026-06-25 wiki-daily-update (evening re-run)** (demo/stats live only, is_shadow=false):
  - Live only (is_shadow=0): **N=519** (+3 intraday vs morning's N=516: **2W/1L/0BE**), WR=43.0% (decided 45.8%), EV=-0.82, PnL=**-426.3pip** (−2.8pip intraday; **+3.2pip vs 2026-06-19**, ~6-day window — 06-20/21 weekend, no log 06-22/23/24); Wilson lower=41.4%, BF lower=38.5%
  - 🟢 **1 LIVE filled 2026-06-24 17:27 UTC** (trendline_sweep → daytrade_gbpusd GBP_USD SELL 5000u, **oanda#541666** — first *confirmed* fill since 06-16/17/19 awaiting-fill sends; ELITE_LIVE pipeline executed). Evening audit window (09:38→11:47 UTC) = **0 LIVE, all 30 shadow_tracking** (#541666 aged out)
  - 30d rolling (risk API): Kelly=**0.0%** ⚠️⚠️ (edge=**-27.77%** NEGATIVE, WR=48.62%, odds 0.485 — eased +1.05pp from morning's -28.82% as window rolled forward; still worse than 06-19 -24.75%); 30d attribution: **gross=net=-207.2pip** (n=109, friction 408.4pip/3.75 per-trade) — eased +4.3pip from morning's -211.5 as window advanced; directional edge still dominant. **Every 30d instrument negative — GBP_USD #1 drag -106.7 (mean -3.23); USD_JPY eased -39.3→-32.2 (#2 drag)**. MC tail eased: worst DD99 172.62→**170.42%**, median max DD(MC) 122.13→**118.30%**
  - **TRUE_LIVE** (`is_shadow=0 AND oanda_trade_id != ''`) SSOT — 2026-05-03 実測: **N=371** (incl BE) / **346** (WIN/LOSS), WR=39.89%, EV=-0.686, PnL=-254.6pip (see [[aggregate-kelly-decomposition-2026-05-03-corrigendum]])
  - FLAG_DRIFT (`is_shadow=0` だが OANDA未送信): N=140, WR=32.86%, PnL=-132.4pip (`raw/audits/oanda-passthrough-gap-2026-05-03.md` 由来 write-path bug)
  - SHADOW (`is_shadow=1`): N≈7,935 (2026-06-25 evening demo/stats; prev 7,861 morning, +~74) — **Live 判断には混入禁止** (memory `feedback_live_vs_shadow_strict_separation`)
  - 旧記載 "N=29 (`oanda_trade_id != ''`)" は **誤り** — 実態は `mode='daytrade'` only サブセット、SUPERSEDED by [[aggregate-kelly-decomposition-2026-05-03-corrigendum]]
- Ruin probability: **0.0%** ✅ (MC sims — Render API 2026-06-25; ⚠️ median max DD(MC)=**122.13%** (>100%) from 103.74%, worst-case DD99=**172.62%** from 161.02% — MC tail kept widening; median final eq=881.0/init 1000)
- Aggregate Kelly: **0.0%** ⚠️⚠️ (30d edge=-28.82%, WR=47.66% — ⚠️⚠️⚠️ deteriorating 6th window; TRUE_LIVE SSOT: N=371 raw=-0.69)
- Aggregate Kelly decomposition 2026-05-03: 旧 doc は SUPERSEDED。新 SSOT: [[aggregate-kelly-decomposition-2026-05-03-corrigendum]] (TRUE_LIVE Strategy × Pair 出血ランキング、ELITE_LIVE `session_time_bias × GBP_USD` 出血特定)
- ⚠️ Portfolio warnings: session_time_bias #1 PnL drag (N=30, WR=40%, -67.8pip); vwap_mean_reversion (N=11, WR=36.4%, -63.1pip ⚠️ high per-trade loss); bb_rsi_reversion (N=97, WR=38.1%, -43.5pip). All DSR 0.0 (haircut 100%).
- ⚠️ Monitor anomaly 2026-06-11 02:13 UTC: rnb_usdjpy direction_filter=300 + daytrade hedge_block=209 + spike bypass 16049.8pip (price data artifact) — see `raw/trade-logs/2026-06-11-monitor.md`
- ⚠️ EDGE_CELL_ADMIN_TOKEN unset on watchdog cron — Bearer bug, safety net silently inactive (Codex task pending)
- ⚠️ sr_anti_hunt_bounce shadow data corruption: 100% null alpha_snapshot/edge_cell_id, 85% null sr_basis, pyarrow ImportError at 61% (regression 05-22→05-25)
- Last updated: 2026-06-25 (wiki-daily-update auto — **evening re-run**, N=519/DD 90.55%; morning capture N=516/DD 90.12%); prev: 2026-06-19
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
