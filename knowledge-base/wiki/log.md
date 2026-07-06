# Knowledge Base Change Log

## 2026-07-02 (wiki-daily-update 🌙 evening re-run): 同日2回目の自動スケジュールタスク
- **背景**: 本日2回目の wiki-daily 実行 (夕方 ~UTC 11–12 窓)。朝の実行以降、当日データは進行せず (**新規 fill 0件**)。以下 delta は **朝キャプチャ比** (同日)。2つ変化: ① 朝の「1 LIVE sent」は **forensic で偽 `sent` と確定** (実弾未送信) → その framing を trade-log / index line 170 に伝播訂正 (line 116 は既訂正済); ② 30d rolling window が数時間ロール (n=112→109) で rolling 指標が微減 (window-roll ease、真のエッジ改善ではない)
- **Daily trade log**: `raw/trade-logs/2026-07-02.md` に「🌙 EOD / Evening Re-run」セクション追記 + 偽sent framing を3箇所訂正 (OANDA Audit / Strategy Movers / Key Observations)。cumulative は flat (N=**542** 不変, WR 43.2%, EV -0.96, PnL -521.1pip), shadow 8,482→**8,530** (+48, shadow only)
- **30d rolling (risk API, n=112→109)**: Kelly edge -37.03→**-35.72%** (+1.31pp eased, WR 47.32→48.62%, odds 0.322); gross=net -321.7→**-310.0pip** (friction 462.3→456.3pip/4.19); worst DD99 227.92→**224.82%**, median max DD(MC) 175.08→**172.26%** (共に roll で微減、still >100%)。by-instrument: GBP_USD -139.9 (n42, **#1 drag flat**) / **EUR_USD -84.4→-72.7** (3 trades rolled out) / EUR_JPY -46.0 / USD_JPY -40.4 / USD_CHF -11.0
- **DD state**: **98.2% / eq -$965.1 / peak +$16.90 / ruin 0.0% — 全て朝と flat** (realized、rolling ではない)。roll-ease は rolling 30d 指標に限定、realized equity trough は不変
- **OANDA audit** (fresh 07-02 07:52→11:12 UTC): **0 LIVE / 全30件 shadow_tracking skipped** (朝の偽sent行は latest-30 window から脱落)。instruments USD_JPY(9)/GBP_JPY(9)/GBP_USD(6)/USD_CHF(3)/EUR_USD(3); strategies **dt_sr_channel_reversal(16)**/vix_carry_unwind(4)/london_breakout(3)/htf_false_breakout(2)/ma_regime_switch(2)+singles; dir SELL16/BUY14
- **Learning API**: 変化なし (最新 id=91 のまま)。**Strategy pages**: 更新なし (新規データ・tier 変更なし)
- **Lint**: WR/PnL/DD は trade-log↔index↔log 間で一貫 (N=542/WR43.2%/PnL-521.1/DD98.2%; 30d rolling は evening 値 n=109/edge-35.72%/gross-310.0 で統一、morning n=112 値は「morning」明示で区別)。**✅ 偽sent 不整合を解消**: trade-log + index line 170 の旧「live bridge fired anyway」を line 116 の forensic 結論 (偽sent・実弾未送信) に整合。⚠️ 既存の破損 wikilink ~182件は本 run で件数不変 (新規破損なし)、別タスク継続。⚠️ london-fix-reversal Edge Stage 不整合・watchdog API_AUTH_TOKEN gap は未解決継続。データ当日取得、陳腐化なし
- **主要観察**: ✅ 新規 fill 0件・実弾 0件 (唯一の live "event" だった偽sent は logging artifact、訂正済); ✅ 30d rolling は window-roll で微減 (真の改善ではない、realized DD 98.2% 不変); 🔴 GBP_USD 依然 #1 drag (-139.9 n42 flat)

## 2026-07-02 (Edge Cell E8 code-level DISABLE 完結, rule:R2)
- **新規**: [[edge-cell-e8-demote-2026-06-25]] (decisions/) — E8 (session_time_bias EUR_USD LDN broad) の code-level kill-switch `DISABLED_CELLS`。判断 2026-06-25 (Live N=8 EV=-3.51p / Shadow N=10 EV=-2.10p 両負) → fable5 audit P1-4 の指摘 (無タグ化 / doc 不在 / テスト7件 red) を反映してコミット完結
- **コード**: `edge_cell_promote.py` DISABLED_CELLS (KV default="1" 再武装の遮断) + `demo_trader.py` edge_cell_id タグを match 適格性基準に変更 (watchdog 可視性 + shadow N 蓄積回復)。E2 は据え置き
- **テスト**: E8 依存 bypass 検証 7 件を active cell (E3/E4) へ付け替え + E8 disabled 挙動の固定テスト 4 件追加。[[session-time-bias]] 戦略カード更新。監査 Phase A-1 完了

## 2026-07-02 (Fable5 大規模監査 + wiki-lint)
- **新規**: [[fable5-system-audit-2026-07-02]] (decisions/) — 全システム監査 P0×2/P1×8/P2×9/P3×6 + Phase A/B/C 改善ロードマップ。session log Phase 2 に要約記録
- **Lint 修正**: index.md Session History に [[vwap-mr-live-analysis-2026-04-22]] リンク追加 (check.py 警告解消)
- ⚠️ **Lint 未修正 (フラグのみ)**: ① 破損 wikilink 182件 (大半が log.md 内の歴史的参照 `zz-pivot-v60-sr` 等 — ページ未作成が原因、一括修正は別タスク) ② Edge Stage 不整合 1件 (london-fix-reversal: file=PHASE0 SHADOW GATE vs pipeline=PROMOTED — tier 判断が必要なため保留) ③ `sync_kb_index --check`: index.md が demo_trader.py 戦略セットと drift (app.py の dead inline 4戦略 reg_channel/sr_bounce/strong_sr_breakout/tokyo_bb 含む — 監査 P3 と合わせて要整理)
- ⚠️ **監査で確認された既知未解決との重複**: EDGE_CELL_ADMIN_TOKEN Bearer bug / sr_anti_hunt_bounce shadow corruption は監査スコープ外の既知バグとして継続 (daily log で追跡中)

## 2026-07-02 (wiki-daily-update): 自動スケジュールタスク — ⚠️⚠️⚠️ DD 98.2% NEW HIGH (100%接近)
- **背景**: 06-25 evening 以来初のフル日次ログ。06-26〜07-01 はログなし (06-27/28 週末 + gap)、**~7日窓**。以下 delta は **06-25 evening キャプチャ比** (N=519 / -426.3pip / DD 90.55% / edge -27.77% / gross -207.2)。OANDA audit window = 2026-07-01 18:12 → 2026-07-02 05:02 UTC。
- **Daily trade log**: `raw/trade-logs/2026-07-02.md` 作成 — post-cutoff live N=519→**542** (+23 fills: **11W/11L/1BE** even split), WR=43.0→**43.2%** (+0.2pp), decided 45.8→**46.0%**, EV=-0.82→**-0.96** (-0.14 ⚠️), PnL=-426.3→**-521.1pip** (**−94.8pip ⚠️⚠️⚠️ recent log 最大の単窓ドロップ** — even W/L だが sized losses が支配), Wilson lower=41.4→41.7%/BF=38.5→38.9%
- **🟡 [訂正済 2026-07-02 evening/forensic] この「1 LIVE sent」は偽 `sent` (実弾未送信)**: `wick_imbalance_reversion` GBP_USD **BUY 5000u** 行は `bridge_status=sent` / oanda_trade_id 空。同日 forensic (rule:R3) で、bridge の daily_loss gate (−23.3pip) が**正しくブロックした後に呼び出し側が無条件で書いた偽 'sent'** と確定 — **実弾は出ていない**。「send/block twin」(06-16/17/19 同型) はこの二重書込み artifact であって gate bypass ではない (修正: accept/reject 契約, `tests/test_bridge_send_accept_contract.py`)。以下の朝キャプチャ記述 (line 29/33 の「1 LIVE sent」「live bridge 発火」) はこの訂正が優先。#1 drag pair GBP_USD × #3 cumulative loser (wick_imbalance_reversion -63.0pip/WR35.7%)
- **wiki/index.md**: System State + Session History 更新 — DD=90.55→**98.2%** ⚠️⚠️⚠️ (+7.65pp **NEW HIGH — 100%接近**, eq=-$888.6→**-$965.1** / -$76.5, peak +$16.90 不変, log 最大の単窓 DD ジャンプ); 30d Kelly edge=-27.77→**-37.03%** (⚠️⚠️⚠️ -9.26pp, **7窓連続悪化**, WR 47.32%, odds 0.331); 30d gross=net=-207.2→**-321.7pip** (**−114.5 単窓最大の gross ドロップ**, n=112, friction 408.4→462.3pip/4.13 per-trade — friction も上昇); worst DD99=170.42→**227.92%**, median max DD(MC)=118.30→**175.08%** (共に blew out); shadow≈7,935→**8,482** (+~547); last_updated→2026-07-02。header (line 5) DD も更新。Trade Logs index に 07-02 リンク追加
- **OANDA audit**: 最新30件 — **1 LIVE sent / 1 blocked / 28 shadow_tracking skipped**。instruments: USD_JPY(10)/GBP_USD(9)/GBP_JPY(5)/EUR_USD(4)/EUR_JPY(2)。strategies: **sr_break_retest(8)**/**squeeze_release_momentum(7)**/ma_regime_switch(3)/vol_spike_mr(3)/dual_sr_bounce(2)/wick_imbalance_reversion(2)/engulfing_bb(2)/sr_anti_hunt_bounce(2)+single。directions BUY 21/SELL 9。daily_loss_limit CB が in-window で発火 (−20pip gate active)
- **30d by-instrument**: **全5ペア negative & 全ペア悪化**。GBP_USD **-139.9pip** (mean -3.33, n=42) #1 drag 継続; EUR_USD -48.1→**-84.4** #2; **EUR_JPY blew out -9.2→-46.0** (最後の near-flat JPY cross も出血入り); USD_JPY -32.2→**-40.4**; USD_CHF -11.0 flat。gross 悪化 (-114.5) は broad-based
- **Learning API**: **2件の新規自動調整** id=90 (2026-06-30 12:29) / id=91 (2026-07-01 12:47) — 共に `sr_channel_reversal` scalp blacklist 再確認 (WR25.0%/EV-0.98/N=185)。id=89(06-19)と同理由、learner が毎サイクル同じ除外を再追加。current_params 不変 (conf_threshold=30, max_consec_losses=3, max_open=8)。by_mode: daytrade 全 conf bucket negative (high EV-0.33/mid -3.61/low -2.18)
- **Strategy pages**: 更新なし (tier 変更なし)。⚠️ LIVE 発火した wick_imbalance_reversion は #3 cumulative loser、confirmed fill でない (awaiting-fill) ため戦略ページ Live 数値は未更新、fill 確定後に反映
- **主要観察**: 🔴🔴🔴 DD 98.2% 過去最悪 (100%接近, eq -$965.1 は -$1000 まで ~$35); 🔴🔴🔴 PnL -94.8pip 単窓最大ドロップ (even 11W/11L だが sized losses 支配); 🔴🔴🔴 30d edge -37.03% + gross -321.7pip 7窓連続悪化 & broad-based; ⚠️ MC tail blew out (worst DD99 227.92%); 🔴 1 LIVE sent (未約定) が #1 drag pair × #3 loser strategy; ⚠️ daily_loss_limit CB 発火中; ✅ ruin 0.0%維持, 0.2× lot holding; ⚠️ EDGE_CELL_ADMIN_TOKEN Bearer bug + sr_anti_hunt_bounce shadow corruption 未修正
- **Lint**: WR/PnL/DD は trade-log↔index↔log 間で一貫 (N=542/WR43.2%/PnL-521.1/DD98.2%/edge-37.03%/gross-321.7)。[[2026-07-02]] trade-log リンク=作成済ファイルに解決。⚠️ **stale gap**: 前回更新 06-25 → 今回 07-02 = 7日 (>3日閾値超過だが週末+ログ無日のため window は連続)。データ当日取得 (2026-07-02)、陳腐化なし。live N=542 は demo/stats live_count、TRUE_LIVE SSOT (N=371) とは別系統 (既存注記の通り)。oanda_audit twin-meaning 参照は plain text 化

## 2026-06-25 (wiki-daily-update 🌙 evening re-run): 同日2回目の自動スケジュールタスク
- **背景**: 本日2回目の wiki-daily 実行 (夜 ~20:46 JST / 11:46 UTC)。朝の実行 (N=516 / -423.5pip / DD 90.12% flat) 以降、当日データが進行。以下 delta は **朝のキャプチャ比**。
- **Daily trade log**: `raw/trade-logs/2026-06-25.md` に「🌙 Evening Re-run」セクション追記 — live N=516→**519** (+3 intraday: **2W/1L/0BE**), WR=42.8→**43.0%** (+0.2pp), decided 45.7→45.8%, EV=-0.82 (flat), PnL=-423.5→**-426.3pip** (-2.8pip intraday / **+3.2pip vs 06-19**), Wilson lower=41.3→41.4%/BF=38.4→38.5%
- **wiki/index.md**: System State + Session History (EOD化) — DD=90.12→**90.55%** ⚠️ (+0.43pp **NEW HIGH resumed** — 朝の flat pause は1窓限り, eq=-$884.3→**-$888.6** / -$4.3, peak +$16.90 不変); 30d Kelly edge=-28.82→**-27.77%** (window roll で +1.05pp eased, WR 48.62%, odds 0.485 — ただし 06-19 -24.75% よりは悪い); 30d gross=net=-211.5→**-207.2pip** (n=107→109, friction 397.7→408.4pip/3.75 per-trade, +4.3 eased); worst DD99=172.62→**170.42%**, median max DD(MC)=122.13→**118.30%** (共に eased); shadow≈7,861→**7,935** (+~74); last_updated に evening re-run 注記
- **OANDA audit**: 最新30件 (2026-06-25 09:38 → 11:47 UTC) — **0 LIVE / 全件 bridge_status=skipped / block_reason=shadow_tracking**。朝の confirmed live fill (trendline_sweep #541666, 06-24 17:27 UTC) は latest-30 window から脱落。instruments: GBP_USD(11)/EUR_USD(10)/GBP_JPY(6)/EUR_JPY(1)/EUR_GBP(1)/USD_JPY(1)。strategies: **session_time_bias(14)**/dt_sr_channel_reversal(4)/trendline_sweep(3)/sr_break_retest(2)/engulfing_bb(2)+singles
- **30d by-instrument**: GBP_USD **-106.7pip** (mean -3.23) #1 drag 継続; USD_JPY -39.3→**-32.2** (#2, window roll で eased); EUR_USD -48.1 / EUR_JPY -9.2 / USD_CHF -11.0。全5ペア negative 継続
- **Learning API**: 朝と変化なし。最新自動調整=2026-06-19 (id=89) `sr_channel_reversal` top-level blacklist。新規調整なし
- **Strategy pages**: 更新なし (tier 変更なし; top-mover 表は朝から ~flat)
- **主要観察**: ⚠️ DD NEW HIGH 90.55% 再開 (朝の flat pause は崩れた、実現損失 process 再開); ⚠️ PnL -2.8pip intraday (+3 fills 2W/1L); ✅ 30d rolling-risk は window roll で全面 eased (edge/gross/MC tail); ✅ USD_JPY 30d -39.3→-32.2 eased; 🔴 0 LIVE this window, session_time_bias が shadow firing を支配 (14/30) も #1 cumulative loser; ⚠️ strategy_kelly positive-edge 戦略ゼロ継続; ✅ ruin 0.0%維持; ⚠️ EDGE_CELL_ADMIN_TOKEN Bearer bug + sr_anti_hunt_bounce shadow corruption 未修正
- **Lint**: WR/PnL/DD は trade-log↔index↔log 間で EOD 値 (N=519/WR43.0%/PnL-426.3/DD90.55%) で一貫。朝の中間値 (N=516) は各所で「morning capture」と明示し区別。[[2026-06-25]] trade-log リンク=既存 (line 248)。oanda_audit twin-meaning 参照は plain text 化。データ当日取得 (2026-06-25 夜)、陳腐化なし。live N=519 は demo/stats live_count、TRUE_LIVE SSOT (N=371) とは別系統 (既存注記の通り)

## 2026-06-25 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-06-25.md` 作成 — 06-19 以来初のフル日次ログ (06-20/21 週末、06-22/23/24 ログなし、~6日窓)。post-cutoff live N=**516** (+3 fills: **3W/0L/0BE — 全勝、5連敗 run を解消** ✅), WR=42.8% (+0.3pp ✅, decided 45.7%), EV=-0.82 (+0.02 ✅), PnL=**-423.5pip** (**+6.0pip ✅ recent log 初の累積改善**), Wilson lower=41.3%/BF=38.4% (+0.4pp)
- **🟢 1 LIVE filled (06-24 17:27 UTC)**: `trendline_sweep`→daytrade_gbpusd GBP_USD SELL 5000u, **oanda#541666** (`bridge_status=filled`, oanda_trade_id 非空) — 06-16/17/19 の awaiting-fill sends 以来初の *確定* live fill。ELITE_LIVE pipeline 実執行。GBP_USD (book 最悪 30d drag pair) に着弾
- **wiki/index.md**: System State更新 — live N=513→**516** (+3 fills 全勝), WR=42.5→**42.8%** (+0.3pp ✅), EV=-0.84→**-0.82** (+0.02 ✅), PnL=-429.5→**-423.5pip** (+6.0pip ✅); DD=**90.12% flat** (eq=-$884.3/peak +$16.90 共に不変 — **5連騰後初の non-NEW-HIGH** ✅); 30d Kelly edge=-24.75→**-28.82%** ⚠️⚠️⚠️ (6窓連続悪化, WR 47.66%, odds 0.493); 30d gross=net=-179.2→**-211.5pip** (-42.7→-70.1→-96.1→-113.8→-179.2→-211.5 の6窓連続悪化, friction 397.7pip flat-to-down); worst DD99=161.02→**172.62%**, median max DD(MC)=103.74→**122.13%**; shadow=7,515→**7,861** (+346); last_updated→2026-06-25。Trade Logs index に 06-25 リンク追加
- **Strategy pages**: [[trendline-sweep]] の Live Performance 更新 (stale N=2→**N=24/WR66.7%/-17.0pip** + 確定 live fill oanda#541666 追記)
- **OANDA audit**: 最新30件 (2026-06-24 14:32 → 18:58 UTC) — **1 LIVE filled** (trendline_sweep GBP_USD SELL, twin row sent+filled) + 28 shadow skipped。unique live signal=1。instruments: GBP_USD(10)/EUR_USD(10)/GBP_JPY(5)/EUR_GBP(2)/EUR_JPY(2)/USD_JPY(1)。strategies: ob_retest(5)/engulfing_bb(5)/trendline_sweep(4)/london_fix_reversal(3)/eurgbp_daily_mr(2)/dt_sr_channel_reversal(2)/wick_imbalance_reversion(2)+singles
- **30d attribution**: **gross=net=-211.5pip** (n=107, friction 397.7pip/3.72 per-trade) — gross-edge 悪化が6窓連続。⚠️⚠️ by-instrument: **USD_JPY が -1.4→-39.3pip に blew out** (#2 drag); GBP_USD は -113.4→-108.7 にやや緩和も #1 drag (mean -3.40); 全5ペア negative 継続
- **Learning API**: 最新自動調整=2026-06-19 12:53 (id=89) `sr_channel_reversal` top-level blacklist。**新規調整なし**。current_params: confidence_threshold=30, max_consecutive_losses=3, max_open_trades=8, learn_every_n=10
- **Risk state**: DD=**90.12% flat** (lot=0.2x, 5連騰後初の non-new-high), 30d Kelly edge=-28.82% (⚠️⚠️⚠️ 6窓連続悪化), MC ruin=0.0%✅, worst DD99=172.62%, median max DD(MC)=122.13% (>100%), DSR=0.0 (haircut 100%, Sharpe -0.287, trials 14, n=107)
- **主要観察**: 🟢 1 LIVE filled (trendline_sweep #541666 — 初の確定 fill); ✅ PnL +6.0pip (recent log 初の改善), +3 fills 全勝で5連敗解消; ✅ DD flat (5連騰後初の non-new-high), 実現損失 process 一時停止; ⚠️⚠️⚠️ 30d Kelly edge -28.82% + gross -211.5pip = 共に6窓連続悪化、rolling window が直近の勝ち fill を trail; ⚠️⚠️ USD_JPY 30d -39.3 blew out, 全ペア negative; ⚠️ strategy_kelly 今窓は positive-edge 戦略ゼロ (vix_carry_unwind 脱落); ✅ ruin 0.0%維持; +3勝は recovering losers (trendline_sweep/wick_imbalance/vsg_jpy_reversal) に着弾; ⚠️ session_time_bias -67.8 / vwap_mean_reversion -63.1 / bb_rsi_reversion N97 継続; ⚠️ EDGE_CELL_ADMIN_TOKEN Bearer bug + sr_anti_hunt_bounce shadow corruption 未修正
- **Lint**: WR/PnL/DD は trade-log↔index↔log 間で一貫 (N=516/WR42.8%/PnL-423.5/DD90.12%)。[[trendline-sweep]]/[[wick-imbalance-reversion]] 戦略ページ存在確認。[[2026-06-25]] trade-log リンク=作成済ファイルに解決。oanda_audit twin-meaning 参照は plain text 化 (broken link 回避)。データ当日取得 (2026-06-25、audit window=06-24 NY)、陳腐化なし。live N=516 は demo/stats live_count、TRUE_LIVE SSOT (N=371) とは別系統 (既存注記の通り)

## 2026-06-18: Month-End WMR Fix pre-reg → VERDICT NULL (REJECT 両脚)
- **対象**: CMA research agent 提案 (Melvin & Prins 2015, 月末 16:00 London WMR fix への hedge-rebalancing flow)。[[monthend-fix-pre-reg-2026-06-18]] に H1 drift / H2 reversion を **BT前に LOCK** (commit 5a151229, m=2 BH-FDR q=0.10, rule:R1)
- **Phase 0 データ**: EUR_USD H1/D1 12y を MASSIVE で取得 (既存 H1 cache は 4.4y のみ→12y拡張)、^GSPC/^STOXX50E daily を yfinance で取得 (146mo, 0 NA)。`tools/monthend_fix_fetch.py`
- **結果 (N=144/142, 12.05y)**: H1 net **−566.8pip** (gross も負) p=0.867 WF1/4 both-legs負; H2 net +141.7pip だが p=**0.378** (BH-FDR 0.05 を大幅未達) かつ **both-legs net+ = False** (SHORT脚 +458 / LONG脚 −316 の片側 artifact)。両脚とも複数 gate fail → **REJECT, shadow も不可**
- **R3 bug fix (mid-BT, 整合性のため記録)**: 初回 run は FX H1 の Sunday-session bar (22:00-23:00 UTC) が "business day" に混入し月末の44%を silent drop。weekday-only に修正 → 修正で結果は**より null 化** (H2 p 0.19→0.38) = drop が H2 を偽陽性方向に膨らませていた。locked spec ("business day") への忠実化であり仮説変更ではない
- **独立 adversarial review (default-to-reject): PASS** — byte一致再現/look-ahead無/DST正/side-sanity 0発火/spec忠実。NULL は本物
- **教訓**: silent な非ランダム drop は edge を偽陽性方向に膨らませ得る。正脚を信じる前に N を理論最大に reconcile せよ。[[d1-tsmom-basket-pre-reg-2026-06-08]] と同じく risk-premia でなく flow 仮説でも単サンプルでは出ず

## 2026-06-17 (wiki-daily-update 🌙 evening re-run): 同日2回目の自動スケジュールタスク
- **背景**: 本日2回目の wiki-daily 実行 (夜 ~21:00 JST)。朝の実行 (N=505 / -360.1pip / DD 84.82%) 以降、当日データが進行。以下 delta は **朝のキャプチャ比**。
- **Daily trade log**: `raw/trade-logs/2026-06-17.md` に「🌙 Evening Re-run」セクション追記 (朝の LIVE send 詳細は保全 — 既に audit window から脱落したため) — live N=505→**508** (+3 intraday: **0W/2L/1BE** 勝ちなし), WR=43.2→**42.9%** (-0.3pp), decided 46.0→45.8%, EV=-0.71→**-0.74** (-0.03 ⚠️), PnL=-360.1→**-377.8pip** (-17.7pip intraday / -43.7pip vs 06-16 ⚠️⚠️), Wilson lower=41.6→41.4%
- **wiki/index.md**: System State + Session History (EOD化) — DD=84.82→**86.64%** ⚠️⚠️ (+1.82pp NEW HIGH再更新, eq=-$831.30→**-$849.5** / -$18.20); 30d Kelly edge=-14.99→**-16.95%** ⚠️⚠️⚠️ (4窓連続悪化, WR 50.0%, odds 0.661); 30d gross=net=-96.1→**-113.8pip** (-42.7→-70.1→-96.1→-113.8 の4窓連続悪化, friction 391.9→404.8pip/n=105→108); median max DD(MC)=63.94→**71.4%** ⚠️; VaR95/CVaR95=10.9/13.89→**11.68/14.65pip**。last_updated に evening re-run 注記
- **OANDA audit**: 最新28件 (ids 9389-9418) — **全件 is_live=false / bridge_status=skipped / block_reason=shadow_tracking = 0 LIVE**。朝の 3 LIVE send (zz_pivot_v60_sr + sr_fib_confluence×2, 06-16) は latest-28 window から脱落
- **Learning API**: 朝と変化なし。最新自動調整=2026-06-11 (id=88) `sr_channel_reversal` scalp blacklist。by_mode: daytrade overall EV **-1.99** (n=85, WR43.5%; high-conf +0.12/n=28 — 前日 +0.84 から劣化); scalp overall EV -0.16 (n=383, WR40.5%; low-conf +0.48/n=127 が唯一の正 bucket)
- **Strategy pages**: 更新なし (tier 変更なし)
- **主要観察**: ⚠️⚠️ PnL -377.8pip (新規3件 0W/2L/1BE 勝ちなし); ⚠️⚠️ DD 86.64% NEW HIGH 再更新 (0.2x lot でも loss process 継続); ⚠️⚠️⚠️ 30d Kelly edge -16.95% + 30d gross -113.8pip = 共に4窓連続悪化、negative directional edge が支配 (friction でない); ✅ ruin 0.0% 維持; daytrade high-conf bucket は正だが薄く (+0.12, n=28) 劣化中 — 残る構造的分離は脆弱
- **Lint**: WR/PnL/DD は trade-log↔index↔log 間で EOD 値 (N=508/WR42.9%/PnL-377.8/DD86.64%) で一貫。朝の中間値 (N=505) は各所で「morning capture」と明示し区別。データ当日取得 (2026-06-17 夜)、陳腐化なし。注: worst-case DD(99%) は本 evening risk API レスポンスに明示フィールドが無かったため median max DD(MC) 71.4% を採用 (朝の 117.72% は別フィールド由来、混同回避のため非継承)

## 2026-06-17 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-06-17.md` 作成 — post-cutoff live N=505 (+5 fills: 2W/3L/0BE 40% WR — 3連続好WR streak **崩壊**), WR=43.2% (flat, decided 46.0%), EV=-0.71, PnL=**-360.1pip** (-26.0pip ⚠️⚠️ — 1週間超で最大の単日下落), Wilson lower=41.6%/BF=38.6%
- **🔴 3 LIVE sent (06-16 16:00–18:40 UTC, awaiting fill / oanda_trade_id empty)**: `zz_pivot_v60_sr`→daytrade_eur EUR_USD SELL 5000u (id 9328) + `sr_fib_confluence`→daytrade_gbpusd GBP_USD BUY 5000u (id 9336) + GBP_USD BUY 1000u (id 9341)。demo 側 daily-loss gate (-26pip<=-20pip) が 3件全てを block したが live bridge は送信 — live 経路は daily-loss circuit breaker の対象外。GBP_USD 2件は sr_touches 119/120・strength 0.80・is_strong=1 の強 SR context
- **wiki/index.md**: System State更新 — live N=500→**505** (+5 fills), WR=43.2%(flat), EV=-0.67→**-0.71** (-0.04 ⚠️), PnL=-334.1→**-360.1pip** (-26.0pip ⚠️⚠️); DD=83.77%→**84.82%** ⚠️⚠️ (+1.05pp NEW HIGH, 4連続上昇, eq=-$820.80→**-$831.30** / -$10.50); 30d Kelly edge=-11.94%→**-14.99%** ⚠️⚠️⚠️ (-3.05pp 3窓連続悪化, WR 50.5%, odds 0.684); worst DD99=106.84%→**117.72%** ⚠️⚠️; median max DD 53.28→63.94%; shadow=7,059→**7,202** (+143); last_updated→2026-06-17。Trade Logs index に 06-12/06-16/06-17 リンク追加 (欠落補修)
- **Strategy pages**: 更新なし (tier変更なし)
- **OANDA audit**: 最新30件 (06-16 15:57 → 06-17 01:45 UTC) — 3 LIVE sent + 3 daily_loss_limit blocked (各 live send の demo 側 pre-image, twin-meaning) + 24 shadow skipped。instruments: EUR_USD(13)/GBP_USD(10)/USD_JPY(5)/EUR_JPY(2)。strategies: sr_fib_confluence(4)/engulfing_bb(4)/squeeze_release_momentum(3)/zz_pivot_v60_sr(2)/vol_surge_detector(2)/ma_regime_switch(2)/dt_bb_rsi_mr(2)/sr_anti_hunt_bounce(2)+singles
- **30d attribution**: **gross=net=-96.1pip** (n=105, friction 391.9pip/3.73 per-trade) — ⚠️⚠️ gross-edge 悪化が継続確認: -42.7→-70.1→**-96.1** の3窓連続悪化。directional/gross edge が今や支配的かつ拡大中の損失源で、cell-edge audit「friction が一次」結論は現窓では成立せず
- **By-instrument 30d**: GBP_USD **-72.4pip** (n=33, mean -2.19 = book 最悪) が #1 drag を拡大 (EUR_USD -48.1 を引き離す)。LIVE sr_fib_confluence が撃った GBP_USD と一致。JPY crosses のみ正 (EUR_JPY +19.1 / USD_JPY +16.3)
- **Learning API**: 最新自動調整=2026-06-11 13:28 (id=88) `sr_channel_reversal` scalp blacklist 再確認。**新規調整なし**。current_params: confidence_threshold=30, max_consecutive_losses=3, max_open_trades=8, learn_every_n=10。top-level entry_type_blacklist=空 (sr_channel_reversal blacklist は scalp mode-scoped)
- **Risk state**: DD=**84.82%** (⚠️⚠️ NEW HIGH, lot=0.2x), 30d Kelly edge=-14.99% (⚠️⚠️⚠️ 3窓連続悪化), MC ruin=0.0%✅, worst DD99=117.72% (>100%), median max DD=63.94%, DSR=0.0 (haircut 100%, Sharpe -0.123, trials 15), VaR95=10.9pip, CVaR95=13.89pip
- **主要観察**: 🔴 3 LIVE sent (zz_pivot_v60_sr + sr_fib_confluence ×2, demo gate block も live 送信); ⚠️⚠️ PnL -26.0pip (>1週で最大下落, 新規2W/3L 40% — 好WR streak 崩壊); ⚠️⚠️ DD 84.82% NEW HIGH (4連続上昇), worst DD99 117.72%; ⚠️⚠️⚠️ 30d Kelly edge -14.99% (3窓連続悪化); ⚠️⚠️ **30d gross -96.1pip (gross edge 負転が拡大、friction-only でなくなった)**; ⚠️ GBP_USD #1 drag -72.4pip 拡大 + sr_fib_confluence が +12.6→-0.5pip flip (LIVE GBP_USD fills が負け); ✅ ruin 0.0%維持, Wilson 41.6%/BF 38.6% ほぼ flat; ⚠️ session_time_bias -67.8 / vwap_mean_reversion -63.1 / bb_rsi_reversion N97 WR38.1% / trendline_sweep(ELITE) -19.0 継続; ⚠️ EDGE_CELL_ADMIN_TOKEN Bearer bug + sr_anti_hunt_bounce shadow corruption 未修正
- **Lint**: [[sr-fib-confluence]]/[[vix-carry-unwind]]/[[doji-breakout]] 戦略ページ存在確認。[[zz-pivot-v60-sr]] は dangling だが auto-synced portfolio block が既に同名参照する repo 慣例と一貫 (戦略ページ未作成)。oanda_audit twin-meaning 参照は broken link 回避のため plain text 化 (MEMORY `reference_oanda_audit_twin_meaning`)。WR/PnL/DD は trade-log↔index↔log 間で一貫 (N=505/WR43.2%/PnL-360.1/DD84.82%)。データ当日取得 (2026-06-17、audit window=06-16 NY→06-17 Tokyo)、陳腐化なし。live N=505 は demo/stats live_count、TRUE_LIVE SSOT (N=371) とは別系統 (既存注記の通り)

## 2026-06-16 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-06-16.md` 作成 — 06-12 以来の初フル日次ログ (06-13/14 週末、06-15 は pre_tokyo/monitor サブログのみ)。post-cutoff live N=500 (+7 fills: 5W/2L/0BE ≈71% WR), WR=43.2% (decided 46.1%), EV=-0.67, PnL=**-334.1pip** (-15.0pip ⚠️), Wilson lower=41.6%/BF=38.7%
- **🔴 2 LIVE fills (06-15 15:01–15:45 UTC)**: `doji_breakout`→daytrade_gbpusd GBP_USD BUY 5000u (oanda#531940) + `zz_pivot_v60_sr`→daytrade_eur EUR_USD BUY 5000u (oanda#531946)。2セッション連続 LIVE pipeline 稼働
- **wiki/index.md**: System State更新 — live N=493→**500** (+7 fills), WR=42.8→**43.2%** (+0.4pp ✅), EV=-0.65→**-0.67** (-0.02 ⚠️), PnL=-319.1→**-334.1pip** (-15.0pip ⚠️ — WR好転がPnL転換せず、sized losses 優勢); DD=81.42%→**83.77%** ⚠️⚠️ (+2.35pp NEW HIGH, eq=-$797.30→**-$820.80** / -$23.50); 30d Kelly edge=-7.66%→**-11.94%** ⚠️⚠️⚠️ (-4.28pp 悪化, WR 51.0%, odds 0.727); worst DD99=95.36%→**106.84%** ⚠️⚠️ (>100% 初); median max DD 43.64→53.28%; shadow=6,941→**7,059** (+118); last_updated→2026-06-16
- **Strategy pages**: 更新なし (tier変更なし)
- **OANDA audit**: 最新30件 (2026-06-15 13:23–17:31 UTC) — 2 LIVE filled + 2 sent(live) + 26 shadow skipped。instruments: GBP_USD(9)/USD_JPY(8)/EUR_USD(7)/EUR_GBP(3)/USD_CHF(2)/EUR_JPY(1)。strategies: sr_channel_reversal(7)/ma_regime_switch(5)/engulfing_bb(2)/sr_fib_confluence(2)/ema200_trend_reversal(2)+singles
- **30d attribution**: **gross=net=-70.1pip** (n=100, friction 372.8pip/3.73 per-trade) — ⚠️ **loss source 転換**: 06-12 まで gross≈flat (-42.7) で friction 主因だったが、本窓で gross が -70.1 に悪化 = directional/gross edge も負転。cell-edge audit「friction が一次」結論の再検証が必要
- **By-instrument 30d**: GBP_USD **-50.2pip** (n=29) が #1 drag に (EUR_USD -44.3 を抜く)、USD_CHF -11.0。JPY crosses のみ正 (EUR_JPY +19.1 / USD_JPY +16.3)
- **Learning API**: 最新自動調整=2026-06-11 13:28 (id=88) `sr_channel_reversal` scalp blacklist 再確認。新規 regime 変更なし。daytrade high-conf EV=+0.84 (N=25, WR52%) ✅ で confidence gate は依然分離機能
- **Risk state**: DD=**83.77%** (⚠️⚠️ NEW HIGH, lot=0.2x), 30d Kelly edge=-11.94% (⚠️⚠️⚠️ 悪化), MC ruin=0.0%✅, worst DD99=106.84% (>100%), median max DD=53.28%, DSR=0.0 (haircut 100%, Sharpe -0.095, trials 15), VaR95=10.9pip, CVaR95=13.63pip
- **主要観察**: 🔴 2 LIVE fills (doji_breakout + zz_pivot_v60_sr, 共 5000u); ✅ WR 43.2% (+0.4pp), 新規 5W/2L 3連続好WR; ⚠️ PnL -15.0pip (好WR≠PnL); ⚠️⚠️ DD 83.77% NEW HIGH; ⚠️⚠️⚠️ 30d Kelly edge -11.94% 悪化; ⚠️⚠️ **30d gross -70.1pip (friction-only でなくなった = gross edge 負転)**; ⚠️ GBP_USD #1 drag; ⚠️ session_time_bias -67.8pip / vwap_mean_reversion -63.1pip / bb_rsi_reversion N97 WR38.1% 継続; ⚠️ EDGE_CELL_ADMIN_TOKEN Bearer bug + sr_anti_hunt_bounce shadow corruption 未修正
- **Lint**: [[doji-breakout]]/[[zz-pivot-v60-sr]]/[[vix-carry-unwind]] 参照確認。WR/PnL は trade-log↔index↔log 間で一貫 (N=500/WR43.2%/PnL-334.1)。DD 83.77% 過去最高更新。データ当日取得 (2026-06-16、audit window=06-15 が最新 broker 活動)、陳腐化なし。live N=500 は demo/stats live_count、TRUE_LIVE SSOT (N=371) とは別系統 (既存注記の通り)

## 2026-06-12 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-06-12.md` 作成 — post-cutoff live N=493 (+16 fills: 12W/4L/0BE ≈75% WR), WR=42.8% (decided 45.7%), EV=-0.65, PnL=-319.1pip (-0.3pip ✅ near-flat), Wilson lower=41.2%/BF=38.2%
- **🔴 2 LIVE fills (roadmap v2.2 pipeline confirmed active)**: `zz_pivot_v60_sr`→daytrade_eur EUR_USD SELL 5000u (oanda#515655, 09:18 UTC) + `vix_carry_unwind`→daytrade USD_JPY SELL 1000u (oanda#517497, 09:23 UTC)。多数セッションぶりに audit window 内で live fills を観測 — shadow_tracking 一辺倒からの転換
- **wiki/index.md**: System State更新 — live N=477→**493** (+16 fills), WR=41.7→**42.8%** (+1.1pp ✅), EV=-0.67→**-0.65** (+0.02 ✅), PnL=-318.8→**-319.1pip** (-0.3pip ✅ near-flat); DD=79.56%→**81.42%** ⚠️⚠️ (+1.86pp NEW HIGH, eq=-$778.70→**-$797.30** / -$18.60); 30d Kelly edge=-8.4%→**-7.66%** (+0.74pp ✅), 30d WR=45.78→**49.48%** (+3.7pp ✅); worst DD99=101.7→**95.36%** (✅ -6.34pp); shadow=6,746→**6,941** (+195); last_updated→2026-06-12
- **Strategy pages**: 更新なし (tier変更なし)
- **OANDA audit**: 最新30件 (09:17–10:51 UTC) — 2 LIVE filled + 2 sent(live) + 26 shadow skipped。instruments: EUR_USD(14)/USD_JPY(7)/GBP_USD(6)/EUR_JPY(2)/USD_CHF(1)。strategies: london_breakout(10)/dt_bb_rsi_mr(6)/ob_retest(4)/dual_sr_bounce(3)/trendline_sweep(2)/zz_pivot_v60_sr/vix_carry_unwind/daytrade variants/ma_regime_switch
- **30d attribution**: gross=net=-42.7pip, friction=**366.8pip** (3.78/trade) — friction が依然 net 損失の主因 (cell-edge audit パターン継続、gross EV≈flat)
- **Learning API**: 最新自動調整=2026-06-11 13:28 (id=88) `sr_channel_reversal` scalp blacklist 再確認 (WR 25.0%, EV -0.98, N=185)。ids 82–88 同一 blacklist の反復。新規 regime 変更なし
- **Risk state**: DD=**81.42%** (⚠️⚠️ NEW HIGH, lot=0.2x), 30d Kelly edge=-7.66% (改善継続), MC ruin=0.0%✅, worst DD99=95.36%✅, median max DD=43.64%, DSR=0.0 (haircut 100%, Sharpe -0.055, trials 15), VaR=10.9pip, CVaR=13.42pip
- **主要観察**: 🔴 2 LIVE fills 実行 (zz_pivot_v60_sr + vix_carry_unwind) — roadmap v2.2 LIVE 稼働確認; ✅ WR 42.8% (+1.1pp, 新規12W/4L); ✅ PnL -0.3pip near-flat; ✅ 30d Kelly edge/WR 改善継続; ✅ worst DD99 改善; ✅ ruin 0.0%維持; ⚠️⚠️ DD 81.42% NEW HIGH — 昨日の反転は続かず equity bleed 継続 (-$18.60, friction 経由); ⚠️ session_time_bias #1 loss継続 (-67.8pip); ⚠️ bb_rsi_reversion N=97 WR38.1% 構造的負EV; ⚠️ EDGE_CELL_ADMIN_TOKEN Bearer bug未修正
- **Lint**: [[vix-carry-unwind]] ページ存在確認。[[zz-pivot-v60-sr]] は dangling だが auto-synced portfolio block が既に同名参照しており repo 慣例と一貫 (戦略ページ未作成、既存条件)。cell-edge audit 参照は broken link 回避のため plain text 化。WR/PnL は trade-log↔index↔log 間で一貫 (N=493/WR42.8%/PnL-319.1)。DD 81.42% は過去最高更新。データ当日取得 (2026-06-12)、陳腐化なし。注意: live N=493 は demo/stats live_count、TRUE_LIVE SSOT (N=371) とは別系統 (既存注記の通り)

## 2026-06-11 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-06-11.md` 作成 — post-cutoff live N=477 (+7 fills: 4W/2L/1BE), WR=41.7%, EV=-0.67, PnL=-318.8pip (-2.4pip)
- **wiki/index.md**: System State更新 — live N=470→**477** (+7 fills), WR=41.5→**41.7%** (+0.2pp ✅), PnL=-316.4→**-318.8pip** (-2.4pip ✅ minimal); DD=80.03%→**79.56%** (-0.47pp ✅ first improvement in 7 sessions); eq=-$783.4→**-$778.70** (+$4.70 ✅); 30d edge=-10.18%→**-8.4%** (+1.78pp ✅ improving); 30d WR=43.59%→**45.78%** (+2.19pp ✅); shadow_count=**6,746**; last_updated→2026-06-11
- **Strategy pages**: 更新なし (tier変更なし)
- **OANDA audit**: 最新27件 — 全件shadow_tracking skipped (07:41–11:45 UTC)。live fills=0。instruments: GBP_USD/EUR_USD/EUR_JPY/USD_CHF/GBP_JPY/USD_JPY。strategies: session_time_bias(7), sr_channel_reversal variants(5), fib_reversal(3), vol_momentum_scalp(2), london_breakout(2)
- **Monitor anomaly**: 2026-06-11 02:13 UTC — rnb_usdjpy direction_filter=300 + daytrade hedge_block=209 + spike bypass 16049.8pip (price data artifact). See `raw/trade-logs/2026-06-11-monitor.md` for full diagnosis.
- **Risk state**: DD=**79.56%** (−0.47pp ✅ first improvement), lot=0.2x, 30d Kelly edge=**-8.4%** ✅ (improving from -10.18%), WR(30d)=45.78%, MC ruin=0.0%, eq=-$778.70. Worst case DD(99%)=101.7%
- **Learning API**: scalp EV=-0.16 WR=40.5% N=383 (変化なし)。daytrade EV=-2.0 WR=42.3% N=71 (変化なし)。RANGE regime WR=57.1% EV=+2.39 best。TREND_BEAR WR=46.2% EV=-4.88 worst。最終自動調整=2026-06-01 変化なし
- **主要観察**: ✅ DD **79.56%** — 7セッション連続悪化が初反転 (-0.47pp); ✅ 30d Kelly edge **-8.4%** 回復傾向 (+1.78pp from -10.18%); ✅ 新規fill 4W/2L/1BE — 最近で初めて勝ちfillあり; ✅ PnL regression 最小 (-2.4pip vs 前回-20pip); ✅ ruin=0.0%維持; ⚠️ 全27件shadow_tracking (0 live fills); ⚠️ Monitor anomaly 02:13 UTC (rnb_usdjpy loop overrun + price spike artifact); ⚠️ session_time_bias #1 loss source 継続; ⚠️ EDGE_CELL_ADMIN_TOKEN Bearer bug未修正
- **Lint**: wikilink問題なし。DD 79.56%は80.03%の新高値から微回復。30d Kelly edgeの改善は30d窓効果の可能性あり、post-cutoff EV=-0.67は変化なし。Monitor 02:13 UTCの異常は要追跡 (rnb_usdjpy direction_filterループ問題が懸念点)。陳腐化なし

## 2026-06-10 Run 2 (wiki-daily-update): London session OANDA window update
- **Trade log update**: `raw/trade-logs/2026-06-10.md` — OANDA audit Run 2追加 (IDs 8481-8510, 07:26-11:46 UTC, 0 live fills, 30 shadow). DB total 8,510
- **New strategy activity**: `ma_regime_switch` (SCALP_SENTINEL/SHADOW) — USD_JPY SELL ×2 (08:16, 10:38 UTC) — shadow確認。`session_time_bias` ×9 records London session (EUR_USD中心)
- **Correlation window shift**: bb_rsi×dt_sr_channel_reversal r=0.9476 ⚠️ (新フラグ), vix_carry×xs_momentum は今回30d窓から外れた
- **Core metrics**: 変更なし (N=470, DD=80.03%, Kelly edge=-10.18% — Run 1より変化なし、新live fillsゼロ)
- **Lint**: 問題なし

## 2026-06-10 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-06-10.md` 作成 — post-cutoff live N=470 (+5 fills), WR=41.5%, EV=-0.67, PnL=-316.4pip ⚠️⚠️ (-20.0pip vs 2026-06-08)
- **wiki/index.md**: System State更新 — live N=465→**470** (+5 fills), WR=41.7→**41.5%**, EV=-0.64→**-0.67**, PnL=-296.4→**-316.4pip** ⚠️⚠️; DD=~77.0%→**80.03%** (800.3pip ⚠️⚠️⚠️ 新高値 80%突破); eq=-$752.9→**-$783.4** (-$30.5); shadow_count →**7,460**; last_updated→2026-06-10
- **Strategy pages**: 更新なし (tier変更なし)
- **OANDA audit**: 最新30件 — 全件shadow_tracking skipped (IDs 8412-8441, 2026-06-09 17:22–2026-06-10 01:30 UTC)。live fills=0。Top instruments: USD_CHF (9), EUR_USD (8), GBP_USD (6)。Top entry strategies: sr_channel_reversal (7), fib_reversal (6), engulfing_bb (4)
- **Risk state**: DD=**80.03%** (⚠️⚠️⚠️ 80%ライン突破 — 新高値, eq=-$783.4 / −$30.5), lot=0.2x, 30d Kelly edge=**-10.18%** ⚠️⚠️⚠️ (前回-6.52%から大幅悪化, WR=43.59%), Kelly fractions=0.0全, MC ruin=0.0%✅, VaR=11.08pip, CVaR=14.68pip, DSR=0.0 (haircut 100%)
- **Learning API**: last adj=2026-06-01 (変化なし)。scalp/scalp_5m/daytrade_gbpusd 計30件ログ済み
- **主要観察**: ⚠️⚠️⚠️ DD **80.03%** — 80%ライン突破・新高値 (前回~77.0%から+3.03pp); ⚠️⚠️⚠️ 30d Kelly edge **-10.18%** (前回-6.52%から急悪化、WR 45.21%→43.59%); ⚠️⚠️ PnL -20.0pip regression (前回-7.5pip); ⚠️ +5 new live fills 全敗 (vs +1 前回); ✅ ruin=0.0%維持 (0.2x lot保護有効); ✅ 全30件shadow_tracking (0 live fills in audit window); ⚠️ session_time_bias #1 loss source継続 (N=30, WR=40%, -67.8pip); ⚠️ vwap_mean_reversion -63.1pip (N=11) per-trade最大損失; ⚠️ bb_rsi_reversion N=97 WR=38.1% 構造的負EV; ⚠️ EDGE_CELL_ADMIN_TOKEN Bearer bug未修正
- **Lint**: wikilink問題なし。DD 80.03%は過去最高かつ80%ライン突破(心理的節目)。30d Kelly edge -10.18%はセッション開始以来の最低値。5連敗fillは单日最大。shadow_count 7,460は蓄積継続中。陳腐化なし

## 2026-06-08 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-06-08.md` 作成 — post-cutoff live N=465 (+1 fill), WR=41.7%, EV=-0.64, PnL=-296.4pip ⚠️ (-7.5pip vs 2026-06-06)
- **wiki/index.md**: System State更新 — live N=464→**465** (+1 fill), WR=41.8→**41.7%**, EV=-0.62→**-0.64**, PnL=-288.9→**-296.4pip** ⚠️; DD=76.23%→**~77.0%** (est. from eq_current -$752.9, +$7.5 drop ⚠️ 新高値); 30d Kelly edge **persistent negative**: -6.61%→**-6.52%** ⚠️⚠️⚠️ (slight improvement but still deeply negative, WR 45.21%); DB total ~8,155 (+125 in 2 days); last_updated→2026-06-08
- **Strategy pages**: 更新なし (tier変更なし)
- **OANDA audit**: 最新30件 — 全件shadow_tracking skipped (IDs 8126-8155, 09:21-11:48 UTC 2026-06-08)。live fills=0。Top instruments: GBP_USD (11), EUR_USD (7), USD_JPY (2)。Top entry strategies: session_time_bias (10), engulfing_bb (4), sr_channel_reversal (3)
- **Risk state**: DD=~77.0% (新高値, eq=-$752.9 / −$7.5), lot=0.2x, 30d Kelly edge=-6.52% ⚠️⚠️⚠️ (fractionally improved from -6.61% but structurally unchanged), Kelly WR=45.21%, MC ruin=0.0%, VaR=8.8pip, CVaR=12.84pip. All Kelly fractions = 0.0
- **Learning API**: scalp EV=-0.16 WR=40.5% N=383 (変化なし)。daytrade EV=-2.0 WR=42.3% N=71 (変化なし)。RANGE regime WR=54.5% EV=+1.95 ✅; TREND_BULL WR=66.7% EV=+2.47 ✅; TREND_BEAR WR=46.2% EV=-4.88 ⚠️。最終自動調整=2026-06-01 変化なし
- **主要観察**: ⚠️⚠️⚠️ DD ~77.0% — 新高値 (prev 76.23%); ⚠️ PnL -7.5pip regression (+1 losing fill); ⚠️ 30d Kelly edge -6.52% 依然深刻 (persistent negative zone, 7日連続Kelly=0.0%); ✅ ruin=0.0%維持 (0.2x lot); ✅ 全30件shadow_tracking (0 live fills in audit window); ⚠️ session_time_bias #1 loss source (N=30 WR=40% -67.8pip); ⚠️ vwap_mean_reversion WR=36.4% -63.1pip (N=11 high per-trade loss); ⚠️ bb_rsi_reversion N=97 最大サンプルで38.1% WR 構造的負EV; ⚠️ EDGE_CELL_ADMIN_TOKEN Bearer bug未修正
- **Lint**: wikilink問題なし。DD ~77.0% 新高値。30d Kelly edge 7日連続0.0% (2026-06-01以降)。vwap_mean_reversion の -63.1pip (N=11) はper-trade損失として最大級 — 要注視。陳腐化なし

## 2026-06-06 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-06-06.md` 作成 — post-cutoff live N=464 (+2 fills), WR=41.8%, EV=-0.62, PnL=-288.9pip ⚠️ (-19.3pip vs 2026-06-05)
- **wiki/index.md**: System State更新 — live N=462→**464** (+2 fills), WR=42.0→**41.8%**, EV=-0.58→**-0.62**, PnL=-269.6→**-288.9pip** ⚠️; DD=74.82%→**76.23%** (+1.41pp ⚠️ 新高値); 30d Kelly edge **further deteriorated**: -1.32%→**-6.61%** ⚠️⚠️⚠️ (odds_ratio 0.9736→0.9123, WR 50%→48.84%); shadow_count 6,889→**7,090**; EUR_JPY 30d +$8.9→**-$5.2** (LIVE fill reversal); last_updated→2026-06-06
- **Strategy pages**: 更新なし (tier変更なし)
- **OANDA audit**: 最新30件 — 28件shadow_tracking skipped, 2件LIVE (IDs 8026/8027): dt_sr_channel_reversal EUR_JPY BUY → daytrade_eurjpy filled (OANDA#504420, 5000u, 17:21 UTC 2026-06-05)。DB total=8,030 (2026-06-05比+242件)。xs_momentum/dt_sr_channel_reversal/wick_imbalance_reversion/htf_false_breakout がshadow主流
- **Risk state**: DD=76.23% (+1.41pp 新高値), lot=0.2x, 30d Kelly edge=-6.61% (⚠️⚠️⚠️ -6.61%に急悪化), odds_ratio=0.9123 (0.9736から大幅悪化), WR(30d)=48.84% (50%割れ), MC ruin=0.0%, eq_current=-$745.4 (-$14.1). USD_JPY 30d +$46.1 (弱化 from +$52.3), EUR_JPY 30d -$5.2 (⚠️ reversal from +$8.9), EUR_USD 30d -$42.6 (継続悪化)
- **Learning API**: scalp EV=-0.16 WR=40.5% N=383 (変化なし)。daytrade EV=-2.0 WR=42.3% N=71 (変化なし)。daytrade high-conf EV=+0.83 WR=47.6% N=21 ✅。最終自動調整=2026-06-01 変化なし
- **主要観察**: ⚠️⚠️⚠️ DD 76.23% — 新高値 (+1.41pp); ⚠️⚠️⚠️ 30d Kelly edge -6.61%に急悪化 (odds_ratio 0.9736→0.9123 — 最も深刻な単日変化); ⚠️ EUR_JPY 30d +$8.9→-$5.2 (LIVE fill dt_sr_channel_reversal loss); ⚠️ USD_JPY 30d +$52.3→+$46.1 (唯一の正ペアも弱化); ✅ ruin=0.0%維持 (0.2x lot); ✅ CB recovery 2026-06-04継続確認 (LIVE fill後もshading_tracking比率高); ⚠️ EDGE_CELL_ADMIN_TOKEN Bearer bug未修正; ⚠️ All DSR=0.0 (haircut 100%)
- **Lint**: wikilink問題なし。DD 76.23%は過去最高。odds_ratio 0.9123は悪化トレンドで過去最低水準。30d WR 48.84%が50%割れは心理的節目。EUR_JPY LIVE fillが貢献度を測る今後の観察ポイント。陳腐化なし

## 2026-06-05 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-06-05.md` 作成 — post-cutoff live N=462 (+6 fills, all losing), WR=42.0%, EV=-0.58, PnL=-269.6pip ⚠️ (-24.4pip vs 2026-06-03)
- **wiki/index.md**: System State更新 — live N=456→**462** (+6 fills), WR=42.1→**42.0%**, EV=-0.54→**-0.58**, PnL=-245.2→**-269.6pip** ⚠️; DD=72.57%→**74.82%** (+2.25pp ⚠️ 新高値); 30d Kelly edge **turned negative**: +1.75%→**-1.32%** ⚠️⚠️ (fraction 0.0%); CB recovery 2026-06-04記録; shadow_count 6,645→**6,889**; last_updated→2026-06-05
- **Strategy pages**: 更新なし (tier変更なし)
- **OANDA audit**: 最新30件 — 全件shadow_tracking skipped (block_reason=shadow_tracking, 2026-06-04 11:46–13:54 UTC)。DB total=7,788 (2026-06-03比+309件)。post-CB recovery後の全シグナルがshadow_trackingで正常動作確認
- **Risk state**: DD=74.82% (+2.25pp 新高値), lot=0.2x, 30d Kelly edge=-1.32% (負転換 ⚠️⚠️), odds_ratio=0.9736, MC ruin=0.0%, eq_current=-$731.3 (-$22.5). USD_JPY 30d +$52.3 (anchor), EUR_USD 30d -$37.4 (最大損失源、更に悪化)
- **Learning API**: scalp EV=-0.16 WR=40.5% N=383 (変化なし)。daytrade EV=-2.0 WR=42.3% N=71 (変化なし)。最終自動調整=2026-06-01変化なし
- **主要観察**: ⚠️⚠️⚠️ DD 74.82% — 新高値 (+2.25pp); ⚠️⚠️ 30d Kelly edge マイナス転換 (-1.32% / fraction 0.0% — 最も深刻なシグナル); ⚠️ PnL -24.4pip regression; ✅ CB recovery 2026-06-04 確認 (E1/E4/E8 stage=0 disable); ✅ post-CB 全シグナルshadow_tracking (設計通り); ✅ ruin=0.0%維持 (0.2x lot); ⚠️ session_time_bias が単独最大損失源に (N=30, -67.8pip); ⚠️ EDGE_CELL_ADMIN_TOKEN Bearer bug未修正
- **Lint**: wikilink問題なし。DD 74.82%は過去最高。30d Kelly edge負転換は2026-04-08以降初。EUR_USD 30d -$37.4が主要損失源。CB recovery後の全shadow_trackingは設計通りの正常動作。陳腐化なし

## 2026-06-03 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-06-03.md` 作成 — post-cutoff live N=456 (+23 fills, all losing), WR=42.1%, EV=-0.54, PnL=-245.2pip ⚠️ (-34.1pip vs 2026-06-02 evening)
- **wiki/index.md**: System State更新 — live N=433→**456** (+23 fills), WR=42.3→**42.1%**, EV=-0.49→**-0.54**, PnL=-211.1→**-245.2pip** ⚠️; DD=67.95%→**72.57%** (+4.62pp ⚠️⚠️ 最大単日増加 / 新高値); 30d Kelly=6.71%→**Half-Kelly 0.91%** ⚠️ (WR 61.02%→51.81%、大幅退行); daily_loss_limit alert追加; EDGE_CELL_ADMIN_TOKEN gap記録; last_updated→2026-06-03
- **Strategy pages**: 更新なし (tier変更なし)
- **OANDA audit**: 最新27件 — 17件shadow_tracking skipped, 6件sent/filled (EUR_USD+GBP_USD SELL、5,000units), 4件blocked (daily_loss_limit ⚠️)。DB total=7,479。時間帯09:20–11:17 UTC。IDs 7454/7457/7465/7471/7479
- **Risk state**: DD=72.57% (+4.62pp 単日最大増加 / 新高値), lot=0.2x, 30d Kelly=Half-Kelly 0.91% ⚠️ (WR=51.81%, Edge=+1.75%), MC ruin=0.0%, eq_current=-$708.80 (-$46.2). USD_JPY 30d +$53.10 (anchor), EUR_USD 30d -$20.10 (反転 — 昨日+$16.5から), GBP_USD 30d -$22.00
- **Learning API**: scalp EV=-0.16 WR=40.5% N=383 (変化なし)。daytrade EV=-2.0 WR=42.3% N=71 (変化なし)。最終自動調整=2026-06-01 (sr_channel_reversal blacklist 3回目)。mtf_reversal_confluence WR=66.7% EV=2.33 (N=6小)
- **主要観察**: ⚠️⚠️⚠️ DD 72.57% — 単日+4.62pp 最大増加 (新高値); ⚠️ daily_loss_limit circuit breaker TRIGGERED (4 signals blocked, -20.0pip threshold); ⚠️ PnL -34.1pip regression; ⚠️ 30d Kelly 6.71%→0.91%に崩壊 (先週の改善が全消); ⚠️ EUR_USD SELL 30d +$16.5→-$20.10 (directional exposure集中が裏目); ⚠️ E2/E4/E8 loss surge — 7d損失の87%がbb_rsi_reversion+session_time_biasに集中; ⚠️ EDGE_CELL_ADMIN_TOKEN未設定でwatchdog safety net silent; ✅ ruin=0.0%維持 (0.2x lot有効)
- **Lint**: wikilink問題なし。DD 72.57%は過去最高。daily_loss_limit初トリガー記録。30d Kelly崩壊はwindow効果でなく実質的な直近損失による。陳腐化なし。Phase 4.5 architectural signal (13+ bypass/revival commits in 2 weeks) を記録

## 2026-05-27 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-05-27.md` 作成 — post-cutoff live N=411 (+1 fill), WR=41.8%, EV=-0.55, PnL=-225.9pip ⚠️ (-6.8pip vs 2026-05-26)
- **wiki/index.md**: System State更新 — live N=410→**411** (+1 fill), WR=42.0→**41.8%**, EV=-0.53→**-0.55**, PnL=-219.1→**-225.9pip** ⚠️; DD=65.78%→**66.46%** (+0.68pp ⚠️ 新高値); 30d Kelly=Half-Kelly 0.8%→**0.0%** ⚠️ (WR 56.72%→55.88%で逆転); last_updated→2026-05-27
- **Strategy pages**: 更新なし (tier変更なし、今日のaudit全件shadow_tracking)
- **OANDA audit**: 今日の27件全件 bridge_status=skipped, block_reason=shadow_tracking。live fills=0。DB total=6,617。主要instruments: USD_CHF/EUR_USD/GBP_USD/USD_JPY/EUR_JPY。entry strategies: ema_trend_scalp, london_breakout, sr_break_retest
- **Risk state**: DD=66.46% (+0.68pp 連続新高値), lot=0.2x, 30d Kelly=0.0% ⚠️ (Full Kelly fraction=0.0%), MC ruin=0.0%, eq_current=-647.7. USD_JPY 30d +39.6pip (唯一のプラス), GBP_USD 30d -27.8pip (最大損失源)
- **Learning API**: scalp EV=-0.15 WR=40.5% N=378 (変化なし)。daytrade EV=-2.0 WR=42.3% N=71 (変化なし)。最終自動調整=2026-05-18 変化なし
- **主要観察**: ⚠️ PnL -225.9pip (-6.8pip悪化); ⚠️ DD 66.46% 3日連続新高値 (65.07%→65.78%→66.46%); ⚠️ 30d Kelly 0.8%→0.0%に逆戻り (昨日の改善はwindow効果の一時的揺り戻しと確認); ✅ ruin=0.0%維持; ⚠️ SR-family audit gap継続 (Codex c47e943e pending); ⚠️ live fill rate依然低迷 (1 fill/day程度)
- **Lint**: wikilink問題なし。DD 3連続日悪化 (合計+1.39pp/3日)。0.2x防御で破産確率0%は維持。30d windowの揺らぎはpost-cutoff EV=-0.55という真の指標を隠蔽している点に注意。陳腐化なし

## 2026-05-26 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-05-26.md` 作成 — post-cutoff live N=410 (+2 fills), WR=42.0%, EV=-0.53, PnL=-219.1pip ⚠️ (-7.6pip vs 2026-05-21)
- **wiki/index.md**: System State更新 — live N=408→**410** (+2 fills), WR=42.2→**42.0%**, EV=-0.52→**-0.53**, PnL=-211.5→**-219.1pip** ⚠️; DD=65.07%→**65.78%** (+0.71pp ⚠️); 30d Kelly=0.0→**Half-Kelly 0.8%** ✅ (Edge +1.25%, WR 56.72% — window improvement); portfolio warnings追加; last_updated→2026-05-26
- **Strategy pages**: 更新なし (tier変更なし、今日のaudit全件shadow_tracking)
- **OANDA audit**: 今日の28件全件 bridge_status=skipped, block_reason=shadow_tracking。live fills=0。USD_CHF 12件・EUR_USD 11件・GBP_USD 2件・USD_JPY 1件。SR-family data gap (~60%でsr_strength欠損)
- **Risk state**: DD=65.78% (+0.71pp), lot=0.2x, 30d Kelly=Half-Kelly 0.8% ✅ (Edge+1.25%, WR 56.72%), MC ruin=0.0%, eq_current=-640.9
- **Learning API**: scalp EV=-0.15 WR=40.5% N=378 (変化なし)。daytrade EV=-2.0 WR=42.3% N=71 (微悪化: EV -1.93→-2.0)。最終自動調整=2026-05-18 変化なし
- **主要観察**: ⚠️ PnL -219.1pip (-7.6pip悪化); ⚠️ DD 65.78% (+0.71pp新高値); ✅ 30d Kelly半ケリー0.8%に初回転換 (window shift、overall post-cutoff EV依然負); ⚠️ trendline_sweep ELITE_LIVE Sharpe=-0.05 (要監視); ⚠️ session_time_bias Sharpe=-0.77; ✅ ruin=0.0%維持; ⚠️ SR-family audit gap継続 (Codex c47e943e pending)
- **Lint**: wikilink問題なし。DD継続悪化中だが0.2x防御で破産確率0%維持。30d窓效果による改善は実態EV悪化と乖離しており要注意。陳腐化なし

## 2026-05-21 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-05-21.md` 作成 — post-cutoff live N=408 (+4 new fills ✅), WR=42.2%, EV=-0.52, PnL=-211.5pip ✅ (+38.8pip)
- **wiki/index.md**: System State更新 — live N=404→**408** ✅, WR=41.8→**42.2%**, EV=-0.62→**-0.52**, PnL=-250.3→**-211.5pip** ✅; 30d N=79→**82**, PnL=-104.3→**-66.8pip** ✅; shadow_count=5,598→**5,857**; last_updated→2026-05-21
- **Strategy pages**: 更新なし (tier変更なし、今日のaudit上位strategyはshadow_trackingのみ)
- **OANDA audit**: 最新30件全件 bridge_status=skipped, block_reason=shadow_tracking。live fills 4件は早い時間帯/Kalman D7 LIVEによる可能性高い
- **Risk state**: DD=65.07% (変化なし), lot=0.2x, Kelly=0.0 (EV<0), MC ruin=0.0%, eq_current=-633.8 (変化なし)
- **Learning API**: scalp EV=-0.15 WR=40.5% N=378 (変化なし)。daytrade EV=-1.93 WR=42.9% N=70 ✅ (改善 from -2.54/41.2%/68)。最終自動調整=2026-05-18 (sr_channel_reversal blacklist)
- **主要観察**: ✅ N=408 (+4 live fills) — 取引実行確認。✅ PnL -211.5pip (前日-250.3からの+38.8pip改善)。✅ 30d -66.8pip (前日-104.3pip から+37.5pip回復)。✅ USD_JPY 30d +61.1pip が引き続きシステム唯一の正PnL通貨ペア。⚠️ GBP_USD 30d -73.1pip が最大損失源継続。⚠️ vix_carry_unwind 1.0x lot例外 (edge=+0.2743, watchdog active)。⚠️ SR-family audit gap (codex c47e943e pending)。✅ Ruin=0.0% 維持
- **Lint**: wikilink問題なし。DD unchanged (equity peak未達)。live fills 4件とaudit last-30 records不一致 (timing offset — Kalman D7 LIVEによる可能性)。陳腐化なし

## 2026-05-20 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-05-20.md` 作成 — post-cutoff live N=404 (変化なし), WR=41.8%, PnL=-250.3pip, OANDA live fills=0
- **wiki/index.md**: System State更新 — 30d rolling N=91→**79** (window shift), PnL=-63.1→**-104.3pip** ⚠️, Kelly edge=-8.29%→**-15.05%** ⚠️, avg_friction=4.05pip; last_updated→2026-05-20
- **Strategy pages**: 更新なし (新規live fillsゼロ、数値変動なし)
- **OANDA今日**: live fills=0, shadow=32 (全件shadow_tracking), 全戦略シグナル=shadow_onlyモード継続
- **Risk state**: DD=65.07% (変化なし), lot=0.2x, Kelly=0.0 (edge=-15.05%), MC ruin=0.0%, eq_current=-633.8
- **Learning API**: scalp EV=-0.15 WR=40.5% N=378, daytrade EV=-2.54 WR=41.2% N=68 (変化なし)。最終自動調整=2026-05-18 (sr_channel_reversal blacklist)
- **主要観察**: ✅ N=404 live total 変化なし (new fills=0). ⚠️ 30d rolling window drift — profitable old trades fell out, Kelly edge -8.29%→-15.05%は構造的悪化ではなく窓効果。⚠️ GBP_USD 30d -71.2pip が引き続き最大損失源。✅ USD_JPY +23.2pip 唯一の正PnL通貨ペア (30d). 📋 Kalman D7 v17/v18f/v18e LIVE投入後初の観測日 (memory: project_kalman_d7)
- **Lint**: wikilink問題なし. 30d rolling数値は窓シフト起因の正常変動（live total N=404変化なしで確認）. 陳腐化なし

## 2026-05-15 (wiki-lint): ema_trend_scalp redesign audit pages 追加 + 整合性確認
- **新規 page (2)**:
  - `analyses/ema-trend-scalp-redesign-2026-05-14.md` — Phase 0-5 audit (TV harness regression / Live shadow N=75 cell breakdown / `aligned×BUY×GBP_USD` N=10 WR=50% EV=+2.16 発見)
  - `analyses/ema-trend-scalp-redesign-prereg-2026-05-15.md` — Pre-reg LOCK (gate spec hash 固定、Bonferroni 補正、Recovery Path sequence)
- **戦略カード更新**: `strategies/ema-trend-scalp.md` — 新 audit セクション追加 (Status / Active Pairs / Lot Boost / PAIR_DEMOTED は変更なし、operational 変更なし、documentation のみ)
- **整合性チェック** (passed):
  - tier 分類: `index.md` line 79 (FORCE_DEMOTED) と `strategies/ema-trend-scalp.md` line 7 (FORCE_DEMOTED v9.2) 一致
  - wikilink 全て resolve: [[ema-trend-scalp-redesign-2026-05-14]], [[ema-trend-scalp-redesign-prereg-2026-05-15]], [[lesson-cell-audit-bt-required-2026-04-27]], [[sell-bias-forensics-2026-04-17]], [[ema-tr-live-breakdown-2026-04-20]], [[tv-bt-overlay-verification-2026-05-13]], [[trendline-sweep-tv-replica-2026-05-14]], [[ema-trend-scalp]], [[roadmap-v2.1]], [[index]]
  - 旧 v9.5 pair-level 実測 (戦略カード上段、pre-cutoff Live 39件) と新 Live shadow N=75 (post-cutoff) は時系列で並列、矛盾なし
- **新 TV MCP regression (cumulative)**: `data_get_pine_labels` / `data_get_pine_tables` / `data_get_trades` がすべて strategy script で blind (study_count=0 / "No strategy found")。screenshot だけが working な data 取得経路 — `trendline-sweep-tv-replica-2026-05-14.md` に precedent あり、本 redesign で 3 件追加
- **Pivot 記録**: Python BT 17h cell ablation 計画 → 30-40pp optimistic bias 発見 → Live shadow DB primary harness に切替。本日の発見は memory `feedback_tv_edge_discovery_loop` ("Live > TV > Python BT") を実証
- **stale 候補なし**: 戦略カード上段 (v9.2 FORCE_DEMOTE / v9.5 Live pair breakdown) は historical record として保持価値あり、新 audit セクションと並列共存

## 2026-05-07 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-05-07.md` 作成 — post-cutoff total N=530 (gross incl shadow), WR=38.5%, PnL=-414.2pip
- **wiki/index.md**: System State更新 — DD 40.65%→**42.21%** ⚠️⚠️ (422.1pip), risk API PnL=-414.2, N=530 (gross), ruin **1.88%→2.08%** ↑, Kelly edge -17.06%, last_updated→2026-05-07; Session History + Trade Logs セクション追加
- **Strategy pages** (2ページ更新):
  - `bb-rsi-reversion.md` — 2026-05-07 観測追記: N=187 (was 126 on 2026-04-24), WR=38.0%, PnL=-52.7pip. 止血条件モニタリング注意
  - `vwap-mean-reversion.md` — Live更新: N=10→11, WR=40.0%→36.4%, PnL=-47.7→**-63.1pip** (+1 shadow trade, -15.4pip)
- **OANDA今日**: live fills=4 (GBP_USD BUY×3 + USD_JPY SELL×1, daytrade, OANDA#383016/383024/383031/383039, London 06-07 UTC), shadow=25, 総system=5,295
- **Risk state**: DD=42.21%, lot=0.2x, Kelly=0.0 (edge=-17.06%), MC ruin=2.08%, eq_current=-405.2, VaR95=10.1, CVaR95=16.09
- **Learning API**: scalp EV=-0.05 WR=40.5%, daytrade EV=-3.46 WR=34.8% (Underperforming ⚠️). scalp_5m confidence_threshold 30→35 (2026-05-04 auto-adj). 12:00 UTC blacklisted. SL multiplier 1.3x.
- **主要観察**: ⚠️ DD 42.21% new high (+1.56pp from 2026-05-03). ⚠️ bb_rsi N=187 -52.7pip 継続悪化. ⚠️ session_time_bias N=9 WR=22.2% -43.4pip (Rule 2 評価推奨). ⚠️ vix_carry_unwind N=8 -41.5pip (PAIR_PROMOTED 要監視). ✅ daytrade live fills 4件 (London 06-07 UTC, system is executing). ORB Trap FORCE_DEMOTED shadow N=2 +34.3pip.
- **Lint**: wikilink 問題なし. 陳腐化: session_time_bias ELITE_LIVE表記は stale text (tier-master では PAIR_PROMOTED, System State旧テキストに残存). TRUE_LIVE N=371 (2026-05-03 SSOT) は手動 audit 要; risk API N=530 は gross.
- **Stale data flag**: System State の `- ELITE_LIVE tier (v2.1): session_time_bias, trendline_sweep, gbp_deep_pullback` は stale (tier-master では trendline_sweep のみ ELITE_LIVE)

## 2026-04-29 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-04-29.md` 作成 — post-cutoff FX-only N=286, WR=38.1%, PnL=-228.6pip
- **wiki/index.md**: System State更新 — DD 32.32%→**34.76%** ⚠️ (347.6pip), PnL -240.7→**-228.6pip**, N 268→286, WR 37.7%→38.1%, EV -0.90→-0.80, Kelly edge -17.97%→-18.04%, Ruin **2.72%→1.72%** (改善), last_updated 2026-04-27→2026-04-29; Trade Logs セクション + Session History に2026-04-29追加
- **Strategy pages**: 更新なし (vwap_mean_reversion N=10 PnL=-47.7pip 前回2026-04-24から変化なし)
- **OANDA今日**: live fill=0 (全30件shadow_tracking, IDs 3561-3590), 総system audit count=3,590
- **Learning API**: ConnectionRefused (endpoint unavailable)
- **Risk state**: DD=34.76%, lot=0.2x, Kelly=0.0 (edge=-18.04%), MC ruin=1.72%, median equity=758.1, VaR95=8.72, CVaR95=15.05
- **主要観察**: ⚠️ DD 34.76% (+2.44pp from 2026-04-27). ✅ MC ruin 2.72%→1.72% (改善). 🎯 vol_momentum_scalp 唯一正Kelly edge (+7.78%, half-Kelly=3.37%). ⚠️ trend_rebound N=17 WR=23.5% (止血閾値域). ⚠️ session_time_bias (ELITE_LIVE) N=5 WR=20% (小N注意). ⚠️ DSR overall=0.0 全戦略で有意な正Sharpeなし.
- **Lint**: vwap_mean_reversion更新なし (同一数値), bb_rsi_reversion N=151 最大volume継続, wikilink問題なし
- **陳腐化**: Session History 前回 2026-04-27 → 今回 2026-04-29 更新済み

## 2026-04-25 (rule:R3): Asymmetric Agility 規律改定 + bb_rsi RR=2.5 即時適用
- **規律改定**: `wiki/lessons/lesson-asymmetric-agility-2026-04-25.md` 新規 — 3層非対称ルール (Rule 1 Slow & Strict / Rule 2 Fast & Reactive / Rule 3 Immediate)
- **CLAUDE.md**: 判断プロトコルを Rule 1/2/3 分類に書き換え、コミットメッセージに `rule:R[1|2|3]` 明示要求
- **lesson-reactive-changes**: §改定で Rule 1 領域に限定する追記
- **lessons/index.md**: 新 lesson のエントリ追加
- **Rule 3 第1適用 — bb_rsi_reversion**:
  - `strategies/scalp/bb_rsi.py` に `rr_floor_tier1=3.0` / `rr_floor_tier2=2.5` を追加
  - TP 計算を `max(ATR×tp_mult, SL_dist × RR_floor)` に変更 (BUY/SELL 対称, 後方互換 max 並走)
  - 数学根拠: WR=32.3% で BEV_WR=48.1% 必要 vs 観測 RR=1.17 → 構造的負 EV. RR≥2.10 で BEV、Wilson_lo (26.4%) で 2.79、TP-extension WR drop 補正後 ≈ 2.66
- **新規 doc**: `wiki/analyses/bb-rsi-fix-rr-2.5-2026-04-25.md` (修正記録 + 数学 derivation + 影響範囲 + Rule 2 警報閾値)
- **撤回**: `wiki/analyses/bb-rsi-rr15-rescue-2026-04-25.md` を Rule 3 即時適用により撤回マーク (削除はせず証跡保管)
- **bb-rsi-reversion strategy KB**: v11.1 RR floor セクション追加、Status に OANDA_TRIP 明記、Rule 2 監視閾値記載
- **dt_bb_rsi_mr 適用見送り**: WR データ不在 + 0.01 lot Sentinel + MIN_RR=1.2 既存ガード → Rule 1 経路で順次対応
- **OANDA TRIP 維持**: `BB_RSI_OANDA_TRIP=1` 解除しない. Live PnL 直接影響ゼロ
- **Lint 結果**: 7 target files / 119 actual wikilinks 全 resolved (broken=0). 唯一の "broken" は `[[lesson-名前]]` テンプレートプレースホルダ (既存)
- **問題なし**: ⚠️ フラグ無し

## 2026-04-25 (wiki-lint): TP-hit grid 分析 + stale unresolved 整理
- **新規 doc**: `wiki/analyses/tp-hit-pair-session-grid-2026-04-25.md` (Universe N=2,494, 36-cell grid, BEV-gap 数学分析)
- **修正 doc**: `wiki/sessions/2026-04-25-session.md` (Phase 2 narrative 追加、stale 4 件 [x] 化)、`wiki/strategies/bb-squeeze-breakout.md` (USD_JPY direction-asymmetric Shadow split 追記)
- **Lint 結果**: 全 wikilinks resolved (新規 doc 12 / session 10 / bb-squeeze 4)、broken=0
- **整合性 cross-check**: bb_squeeze_breakout × USD_JPY = PAIR_PROMOTED が strategies/index/tier-master の 3 箇所で一致
- **発見ハイライト**: 全 16 cell (N≥50) で BEV gap < 0、Bonferroni 通過は USD_JPY×NY-overlap×SELL のみ (EV=-0.35p で BEV 未達)、唯一の正 EV hour cell は USD_JPY×hr19×BUY (N=29 EV=+3.29p)
- **問題なし**: ⚠️ フラグ無し

## 2026-04-24 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-04-24.md` 作成 — post-cutoff FX-only N=259, WR=39.0%, PnL=-215.0pip
- **wiki/index.md**: System State更新 — DD 28.01%→**32.32%** ⚠️ (323.2pip), PnL -171.9→**-215.0pip**, N 255→259, WR 39.6%→39.0%, EV -0.67→-0.83, Kelly edge -15.11%→-17.97%, Ruin **0.78%→2.72%** ⚠️, last_updated 2026-04-23→2026-04-24; Trade Logs セクションに2026-04-24追加
- **Strategy pages** (1ページ更新):
  - `vwap-mean-reversion.md` — Live更新: N=8→10, PnL=-17.5→**-47.7pip** (2新規トレードで-30.2pip追加、OANDA kill-switch適用確認, WR 50%→40%)
- **OANDA今日**: live fill=1 (GBP_USD BUY bb_rsi_reversion → scalp_5m_gbp OANDA#378534, 12:39 UTC), shadow=29 (IDs 3056-3085), 総system trades=3,085
- **Risk state**: DD=32.32%, lot=0.2x, Kelly=0.0 (edge=-17.97%), MC ruin=2.72%, median equity=747.4, VaR95=9.01, CVaR95=15.98
- **Learning API**: scalp WR=48.2% EV=+0.25 (Ready, N=245), daytrade WR=40.0% EV=-1.91 (N=15, Underperforming); Auto-adj 2026-04-23: daytrade_gbpusd threshold 30→35, scalp_5m threshold 30→35, bb_rsi blacklisted
- **主要観察**: ⚠️ DD 32.32% (前日+4.31pp、最大1日増加). ⚠️ MC ruin 0.78%→2.72% (3.5x悪化). ⚠️ vwap_mr N=10 -47.7pip (kill-switch確認済み). bb_rsi_reversion -12.9pip today (N=126, WR=40.5%). trend_rebound N=17 WR=23.5% stop threshold到達 — 手動評価要.
- **Lint**: 参照ファイル確認済み / wikilink問題なし (elite-freeing-patch-2026-04-24.md は wiki/analyses/ に存在) / WR/PnL整合性問題なし / 陳腐化: 前回から変化なし (多数のstaleページあるが今日のデータ変化なし)

## 2026-04-23 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-04-23.md` 作成 — post-cutoff FX-only N=255, WR=39.6%, PnL=-171.9pip
- **wiki/index.md**: System State更新 — DD 28.15%→**28.01%** (280.1pip), PnL -171.0→**-171.9pip**, N 248→255, WR 39.1%→39.6%, EV -0.69→-0.67, Kelly edge -13.56%→-15.11%, Ruin **0.04%→0.78%** ⚠️, last_updated 2026-04-22→2026-04-23; Trade Logs セクションに2026-04-23追加
- **Strategy pages** (1ページ更新):
  - `vwap-mean-reversion.md` — Live更新: N=6→8, PnL=-4.6→**-17.5pip** (2新規トレードで-12.9pip追加、avg_loss>>avg_win パターン継続)
- **OANDA今日**: live fills=0 (全30件shadow_tracking, IDs 2755-2784), 総system trades=2,784
- **Risk state**: DD=28.01%, lot=0.2x, Kelly=0.0 (edge=-15.11%), MC ruin=0.78%, median equity=797.35, VaR95=8.41
- **Learning API**: scalp WR=48.2% EV=+0.25 (Ready, N=245), daytrade WR=40.0% EV=-1.91 (N=15)
- **主要観察**: ⚠️ MC ruin 0.04%→0.78% (20x悪化、Kelly edge悪化が主因). ⚠️ vwap_mean_reversion 3日連続悪化 (+36.9→-4.6→-17.5). trend_rebound N=17 WR=23.5%で止血閾値に接近. session_time_bias WR=0% N=4 (ELITE_LIVE tier、小N注意). bb_rsi_reversion が scalp_5m で blacklist/restore ループを繰り返し中.
- **Lint**: 参照ファイル確認済み / wikilink破損なし / 陳腐化: vwap-mean-reversion更新済み, 他は前回同様多数あるがデータ変化なし

## 2026-04-23: 5-Proposal 並列分析 (A/C/D/E 完了、B running)
- **新規 session doc**: `wiki/sessions/five-proposal-parallel-2026-04-22.md` 作成
- **A (KSFT × vwap_mr)**: 4 pair で quartile 分析 — pair 毎に逆方向の quartile 優位、統一 filter は不可。GBP_JPY × KSFT≤-0.818 (N=68 WR=83.8% PF=4.63) のみ standout
- **C (horizon deepening h=1..32)**: 975 tests, 180 Bonferroni sig — **すべて h=1**。15m TF intraday edge は 1-bar pattern のみ
- **D (BY-FDR)**: 780 tests, Bonferroni 178 = BY-FDR 178 (完全一致)。`tools/alpha_factor_zoo.py` に `by_fdr_threshold()` 追加
- **E (window sensitivity)**: w7/w60/w90 全完了 — **Window-Invariant Stable subset**: USD_JPY × streak_reversal, GBP_JPY × vwap_mr, GBP_USD × vwap_mr, GBP_USD × wick_imbalance_reversion, GBP_JPY × htf_false_breakout
- **B (730d health audit)**: 🕐 running (2時間経過、4-way並列→solo移行で加速中、残り30-60分見込み)
- **lint 結果**: 参照 9 file 全て存在 / wikilink なし (Markdown相対パス) / stats source 一致 (180/178/975/780)
- **判断**: すべて観測のみ、lesson-reactive-changes 遵守。実装判断保留。

## 2026-04-22 (wiki-daily-update): 自動スケジュールタスク
- **Daily trade log**: `raw/trade-logs/2026-04-22.md` 作成 — post-cutoff FX-only N=248, WR=39.1%, PnL=-171.0pip
- **wiki/index.md**: System State更新 — DD 25.9%→**28.15%** (281.5pip), PnL -129.5→**-171.0pip**, N 244→248, EV -0.53→-0.69, Kelly edge -11.65%→-13.56%, Ruin 0.0%→0.04%, last_updated 2026-04-21→2026-04-22; Trade Logs セクションに2026-04-22追加
- **Strategy pages** (1ページ更新):
  - `vwap-mean-reversion.md` — Live更新: N=2→6, PnL=+36.9→-4.6pip (⚠️ 4新規トレードで-41.5pip反転, GBP_USD+EUR_JPY live fill確認)
- **OANDA今日**: live fill=2 (vwap_mr GBP_USD OANDA#350905 + EUR_JPY OANDA#350909, 09:59 UTC), shadow=26 (London 10:05–12:21 UTC), total system=2,508
- **Risk state**: DD=28.15%, lot=0.2x, Kelly=0.0 (edge=-13.56%), MC ruin=0.04%, median equity=845.7
- **Learning API**: 応答サイズ超過でスキップ。前回値: scalp WR=48.2% EV=+0.27 (Ready), daytrade EV=-2.7 (Underperforming)
- **主要観察**: ⚠️ vwap_mean_reversion がトップパフォーマーから反転 (+36.9→-4.6pip)。DD 28.15%で30%閾値に接近中。全戦略とも live N小さく統計判断保留継続

## 2026-04-22: JPY cross + Scalp fresh BT + divergence v3 full-stack + htf_agreement bug fix
- **BT 完了**: EUR_JPY/GBP_JPY/EUR_GBP 365d × 15m DT (5862s) / 6 pairs × 180d × {1m,5m} Scalp (7744s)
- **BT 結果 JSON**: `raw/bt-results/bt-365d-jpy-2026-04-22.json` / `raw/bt-results/bt-scalp-180d-2026-04-22.json` 作成
- **既存 PAIR_PROMOTED 再確証**: `vwap_mean_reversion × GBP_JPY` N=267 EV=+1.025 PnL=+273.7pip / `× EUR_JPY` N=223 EV=+0.672 PnL=+149.9pip — walk-forward 全窓正 EV、demo_trader.py:5168-5170 の PAIR_PROMOTED を fresh BT で再確証（前回書いた "未登録" は誤認、訂正済み）
- **Scalp scope 構造**: DT_15m EV=+0.217 vs Scalp_1m EV=-0.288 / Scalp_5m EV=-0.115 (GBPJPY 5m のみ正 EV +0.034)
- **構造バグ修正**: `app.py:L7992` に `htf_agreement = htf.get("agreement", "mixed")` 追加。L7965 で取得した htf の agreement が未抽出で L8276 NameError → `_compute_scalp_signal_v2` 内 vwap_mean_reversion が silent except で発火せず（Scalp BT 10 cell 全ゼロで確認）。バグ修正は即 GO (CLAUDE.md 判断プロトコル #4)。
- **Scalp BT 再実行完了** (`bt-scalp-180d-jpy-postfix-2026-04-22.json`, 2665s): vwap_mr 4 cells で発火確認 — EURJPY 1m N=17 EV=-0.272, EURJPY 5m N=2 EV=+0.874, GBPJPY 1m N=14 EV=-0.114, GBPJPY 5m N=3 EV=+0.132。Overall Scalp EV は不変 (1m GBP -0.042→-0.043, 5m GBP +0.034→+0.019) — vwap_mr の発火追加では Scalp 構造的負 EV は救えない。5m 版が小 N で正 EV の兆候あり、365d 延長 BT 候補（1日データで実装禁止）
- **divergence v3**: is_shadow=0 Kelly-clean baseline (Live N=412) で Bonferroni 有意なし — v2 (mixed Live N=2505) で有意だった sr_fib_confluence/sr_break_retest × USD_JPY は power loss で再現せず
- **wiki 更新**: `sessions/bt-live-divergence-scan-2026-04-22.md` §8 appendix / `sessions/bt-live-divergence-v3-full-stack-2026-04-22.md` 新規 / `index.md` BT Results link / `strategies/vwap-mean-reversion.md` fresh BT + bug note / `sessions/2026-04-22-session.md` Addendum + 訂正
- **KB 整合**: `sync_kb_index.py --write` で auto-synced portfolio block 再生成、vwap-mean-reversion が PAIR_PROMOTED に正しく表示されるよう整合
- **Next**: (1) Scalp BT 完了待ち → vwap_mr 発火確認、(2) Scalp 全体負 EV は monthly re-evaluate、(3) Live N≥20 到達後に v3 Bonferroni 再計算

## 2026-04-22 (追記2): OSS 横断調査 + qlib/pybroker 転用ツール実装
- **横断調査** (`wiki/analyses/oss-transfer-2026-04-22.md`): 英語圏・中国圏・日本圏の FX/量化 OSS を star / commit / 収益実績 / 成熟度の 4 軸で評価
- **最重要所見**: 3 圏いずれでも「FX 特化で verified record を公開している成熟 OSS はゼロ」。FX AI Trader は OSS FX bot の空白地帯に位置
- **qlib Alpha158 サブセット 転用** (`tools/alpha_factor_zoo.py` 新規): kbar 9 + rolling [5,10,20,30,60] × [MA,STD,ROC,QTLU,QTLD,RSV] = 39 features × horizons [1,5,10,16] で IC scan (bootstrap + Bonferroni)。初回 USD_JPY 15m 90d: **5 cells が Bonferroni 有意** (KSFT/KSFT2/RSV10/ROC10 h=1)
- **pybroker walk-forward 転用** (`tools/bt_walkforward.py` 新規): 既存 `run_daytrade_backtest` を流用 (BT ロジック無変更)、trade_log を 30d rolling window で bin、戦略×ペア別 CV(EV) で stability 判定 (stable / borderline / unstable)
- **非侵襲設計**: 両ツールとも live/BT logic 無変更、新規ファイルのみ、結果は `raw/bt-results/alpha-factor-zoo-{date}.md` / `walkforward-{date}.md` に出力
- **不採用**: freqtrade Hyperopt (カーブフィッティング禁止違反) / vectorbt BT 置換 (BT/本番統一原則違反) / vnpy EventEngine 即導入 (live 影響で高リスク) / OandaClient 拡張 (別セッションで独立判断)
- **次ステップ**: Bonferroni 有意 factor は 365d walk-forward で再検証、unstable 判定戦略は Live N≥30 到達後に demote 判断

## 2026-04-22 (追記): Scalp EV breakdown + silent-except lesson + vwap_mr 5m 365d 延長 BT
- **Scalp 180d BT 戦略別分解** (`raw/bt-results/scalp-180d-strategy-breakdown-2026-04-22.md`): ema_trend_scalp が単独で損失 37.6% (N=5726 EV=-0.242)、上位 3 戦略で 70.4%。N≥100 の全 10 戦略が負 EV
- **反直感的発見**: FORCE_DEMOTED 除外後の Live-proxy で 1m Scalp EV=-0.289→**-0.338 悪化** (WR 55.1%→51.0%)。FORCE_DEMOTED は "損は出すが高 WR" 群、除外すると残存戦略の WR 50% ノイズが支配的 → Live filter は流出を止めるが Scalp +EV にはならない
- **BT/Live 乖離 #7 (候補)**: `_compute_scalp_signal_v2` (app.py L7941-8330) は FORCE_DEMOTED を respect しない — QUALIFIED_TYPES フィルタ (L5266-L5297) のみ。BT Overall EV は Live demote 前の raw aggregate
- **Scalp vwap_mr 5m × 365d 延長 BT** (`bt-scalp-5m-365d-jpy-2026-04-22.json`, 1180s): 180d 小 N signal (N=5) を 365d で再検証 → N=9 WR=77.8% EV=+0.427 で signal 持続、方向一致。Gate N≥20 未達で Live 実装は引き続き保留
- **付随発見**: **GBPJPY 5m Overall N=1300 EV=+0.026** — Scalp scope で貴重な構造的正 EV cell (180d postfix +0.019 → 365d +0.026 で persistence)。GBPJPY 5m で ema_trend_scalp が N=464 EV=+0.087 と正 EV (global では FORCE_DEMOTED、pair-specific audit 候補)
- **KB 更新**: `lessons/lesson-silent-except-hides-nameerror.md` 新規 / `decisions/vwap-mr-jpy-reconfirmation-2026-04-22.md` 新規 / `strategies/vwap-mean-reversion.md` に 365d × 5m 結果追加 / `sessions/2026-04-22-session.md` Addendum 2 & 3 追加 / `lessons/index.md` + `decisions/index.md` リンク追加
- **Next**: (1) ema_trend_scalp × GBPJPY 5m の global demote vs pair-specific +EV 精査、(2) 5m Scalp walk-forward validation、(3) Live N≥20 (現 16/20) 到達後に Kelly aggregate 初回計算

## 2026-04-21: wiki-daily-update (自動スケジュールタスク)
- **Daily trade log**: `raw/trade-logs/2026-04-21.md` 作成 — post-cutoff FX-only N=244, WR=38.9%, PnL=-129.5pip
- **wiki/index.md**: System State更新 — PnL -174.4→**-129.5pip**, N 282→244, WR 36.5%→38.9%, EV -0.62→-0.53, Ruin 0.04%→**0.0%**, Kelly edge -13.48%→-11.65%, N 448→410, last_updated 2026-04-20→2026-04-21; Trade Logs セクションに2026-04-21追加
- **Strategy pages** (2ページ更新):
  - `post-news-vol.md` — Live追加: N=3→4, WR=33.3%→50%, PnL +9.5→+10.8pip (+1 win)
  - `vwap-mean-reversion.md` — データソース日付を2026-04-21に更新 (新規トレードなし)
- **Lint結果**: 破損リンクなし(sessions/lessons/research は subdirで正常); 陳腐化ページ多数(20+)だがデータ更新なし; WR/PnL整合性問題なし
- **OANDA今日**: 全30件shadow_tracking (London 09:26–11:49 UTC), live fills=0, total system=2,203
- **Risk state**: DD=25.9%, lot=0.2x, Kelly=0.0, MC ruin=0.0%, median equity=871.75
- **Learning API**: 応答サイズ超過でスキップ。前回値: scalp WR=48.2% EV=+0.27 (Ready), daytrade EV=-2.7 (Underperforming)
- **主要観察**: ema_trend_scalp FORCE_DEMOTED後の除外でN/PnL見た目が改善。実質エッジはまだ負 (edge=-11.65%)

## 2026-04-20: wiki-daily-update (自動スケジュールタスク)
- **Daily trade log**: `raw/trade-logs/2026-04-20.md` 作成 — post-cutoff N=282, WR=36.5%, PnL=-174.4pip
- **wiki/index.md**: System State更新 — DD 12.39%→**25.9%**, Ruin prob ~100%→**0.04%**, aggregate Kelly=-0.18→edge=-0.1348, v9.3→v9.4, session history追加
- **Strategy pages** (6ページ更新):
  - `vwap-mean-reversion.md` — Live追加: N=2, WR=50%, +36.9pip (top performer)
  - `vol-momentum-scalp.md` — Live更新: N=10→N=16, WR=80%→50%
  - `vix-carry-unwind.md` — Live追加: N=2, WR=0%, -30.9pip
  - `session-time-bias.md` — Live追加: N=4, WR=0%, -25.8pip ⚠️ BT乖離要注意
  - `donchian-momentum-breakout.md` — Live更新: aggregate N=3, WR=33.3%, -32.1pip
- **Lint結果**: 破損リンク1件(lesson-bt-live-divergence in shadow-baseline-2026-04-20.md、既存バグ), 陳腐化ページなし, WR整合性問題なし
- **Risk state**: DD=25.9%, lot=0.2x, Kelly=0.0, Sharpe=-0.087, MC ruin=0.04%
- **Learning**: scalp WR=48.2% EV=+0.27 (Ready), daytrade EV=-2.7 (underperforming), 49 auto-adjustments

## 2026-04-13: 監査 + レジーム自動化パイプライン (Plan A + Plan B)
- **Plan A: weekly_audit.py**: 週次/月次ストラテジー監査 → raw/audits/ 自動保存 + Discord
- **Plan B: /api/market/regime**: OANDA日足→ATR percentile+SMA slope→レジーム分類
- **daily_report.py拡張**: regime取得→analyst promptに注入→regime KB保存
- **check.py**: audit staleness検知（>14日で警告）
- **GitHub Actions**: weekly-audit.yml（日曜JST 11:00、月初は月次）

## 2026-04-13: KB構造最終整備 (I1-I7)
- **I1: strategies/edges統合**: edges/全10ファイルをstrategies/に移動、Stage更新
- **I6: BT自動KB保存**: _save_bt_to_kb()をapp.py /api/backtestに追加
- **I4/I5: YAGNI空フォルダ削除**: hypotheses/audits/market-analysis/session-transcripts
- **I2: concepts→analyses改名**: wiki/concepts/→wiki/analyses/、CLAUDE.md参照3箇所更新
- **I3: decisions充実**: index.md新設、[DECISION:]タグ形式定義、PreCompact候補検出
- **I7: lessons基準構造化**: 追加基準5項目+テンプレート定義、PreCompact候補検出

## 2026-04-13: KB信頼性強化 (読み書きフロー + ドリフト検知)
- **CLAUDE.md Diet**: 760行→98行、詳細を[[system-reference]]に移行
- **フック分離**: .claude/settings.json埋め込み → scripts/hooks/ に4本抽出
- **KB書き込みパイプライン**: daily-report.yml/trade-monitor.yml に git auto-commit 追加
- **analyst-memory移行**: ルート直下 → knowledge-base/raw/trade-logs/ + `update_analyst_memory()` (F2)
- **KB読み込みフロー修正**: memory[:3000]→[-3000:]バグ修正、ローテーション、SessionStartフック5セクション化
- **analyst-memory v8.9刷新**: 旧v8.3データをarchive退避、v8.9現状で全面書き換え
- **graph view断絶修正**: 17孤立ファイルに双方向wikilink追加
- **ドリフト検知自動化**: check.py に4件追加 (バージョン/Edge Stage/session log/Session History)
- **全ファイル監査**: 80ファイル精査、10件の問題を検出・一括修正

## 2026-04-12: Academic Research Sweep (25 papers → 6 new edges)
- 3 parallel research agents: Microstructure / Anomalies / Advanced
- 25 papers reviewed, stored in [[research-sweep-2026-04-12]]
- 6 new edge hypotheses added to wiki/strategies/:
  - [[session-time-bias]] ★★★★★ (complexity 1/5, highest priority)
  - [[gotobi-fix]] ★★★★★ (complexity 1/5, integrate with tokyo_nakane)
  - [[london-fix-reversal]] ★★★★★ (complexity 2/5)
  - [[vix-carry-unwind]] ★★★★ (low frequency, vol_momentum boost)
  - [[xs-momentum-dispersion]] ★★★★ (monthly rebalance, GitHub code available)
  - [[hmm-regime-overlay]] ★★★ (defensive overlay, not alpha)
- 2 edges REJECTED: vol smile forecasting, NLP news spillover
- research/index.md fully updated: 32 papers total, 3 unexplored territories remaining

## 2026-04-12: Changelog + Production Snapshot
- Created [[changelog]]: バージョン別タイムライン + 評価基準日マトリクス
- First production snapshot: [[snapshot-2026-04-12]] (250t post-cutoff)
- Updated /wiki-quant-eval: Phase 0で[[changelog]]参照 → 最適なdate_from自動判定
- PnL分解: XAU=-1,657pip, FX=+59.8pip（FXは黒字方向）
- index.mdにData & Evaluationセクション追加

## 2026-04-12: Research Layer + Harness
- Added research pipeline: wiki/research/ (2 themes), wiki/strategies/ (pipeline), templates/
- Added /wiki-research, /wiki-edge-eval commands
- Added /wiki-quant-eval command (本番ログ→定量評価→KB更新の完全フロー)
- Added harness hooks: SessionStart (index.md注入), PreCompact (KB保持), PostToolUse (Lint remind)
- Added wiki-daily-update scheduled task (平日UTC 20:47)
- Completed strategy pages: [[vol-momentum-scalp]], [[fib-reversal]], [[liquidity-sweep]], [[force-demoted-strategies]]

## 2026-04-12: Initial Setup
- Created 3-layer structure (raw/wiki/CLAUDE.md schema)
- Migrated key knowledge from CLAUDE.md (743 lines) to structured wiki
- Created strategy pages: [[bb-rsi-reversion]], [[orb-trap]]
- Created concept pages: [[friction-analysis]], [[mfe-zero-analysis]]
- Created decision page: [[independent-audit-2026-04-10]]

## Remaining
- [x] raw/ にBT結果JSONを保存 → raw/bt-results/ に9ファイル格納済み (md形式)
- [ ] Version history (v7.0 - v8.4) as separate pages — 優先度低
- [ ] /wiki-quant-eval の初回実行でベースライン確立

## 2026-07-02 wiki-lint (session: 止血+ガバナンス)
- ✅ 本日の変更整合確認: session_time_bias EUR_USD demote が code (_PAIR_PROMOTED) / tier-master (auto-regen) / index.md portfolio / strategies/session-time-bias.md / pin tests の5点で一致
- ✅ decisions/claude-codex-division-of-labor-2026-07-02.md の wikilink ([[claude-harness-design]], [[audit-completion-protocol]], [[sessions/2026-07-02-session]]) 全て解決
- ✅ index.md 07-01 インシデント記述を forensic 結果で訂正（偽sent、実弾未送信）— 旧記述「live bridge fired anyway」は誤り
- ⚠️ 既存: 破損wikilink 182件（本日編集前後で件数不変=新規破損なし、大半は log.md の [[zz-pivot-v60-sr]] 系と自動生成リンク）— 別タスクで一括修正候補
- ⚠️ 既存: Edge Stage不整合 1件 (london-fix-reversal: file=PAIR_DEMOTED vs pipeline=PROMOTED) — 未解決のまま

## 2026-07-03 wiki-daily-update (scheduled task)
- ✅ APIフェッチ完了 (demo/stats date_from=2026-04-08, demo/learning, risk/dashboard, oanda/audit limit=30) — 全て Render 本番一次ソース
- ✅ Trade log 作成: `raw/trade-logs/2026-07-03.md`
- **本日のスナップショット (is_shadow=false)**: N=**555** (+13 fills vs 07-02: **9W/4L/0BE ≈69% decided WR** — 直近ログで最良のW/Lミックス、07-02ブローアウトを打ち切り)、WR=43.8% (+0.6pp ✅)、EV=-0.95 (+0.01 ✅)、PnL=**-527.9pip** (−6.8pip — 直近リカバリ以降で最も穏やかな単一窓変化。9-4勝ちでも net ほぼ横ばい=sized-loss 非対称が残存)
- **リスク**: DD=**98.97%** (+0.77pp ⚠️⚠️⚠️ **NEW HIGH — −$1000/100%まで<$28**、eq=−$972.8、spike ではなく slow grind)、ruin=0.0% ✅、defensive 0.2× 維持。MC tail ≈flat (worst DD99 226.36% / median max DD 172.3%)
- **30d rolling**: edge=**-32.3%** (07-02 evening -35.72% から +3.42pp — **window-roll のみ** n 109→99、USD_CHF + 6月上旬 trade が窓から脱落、real edge gain ではない)。gross=net=-282.7pip (+27.3 eased)、friction 388.8/3.93。4ペア全て負: **GBP_USD #1 drag -134.4 (mean -3.54, n=38)** / EUR_JPY -51.1 / USD_JPY -49.4 / EUR_USD -47.8 (roll で eased)
- 🟢 **Aggregate Kelly ゲートが LIVE 1件を正しくブロック** (`agg_kelly=-0.326<0`) — watchdog cron が silent の間、現行の稼働中セーフティネットが機能していることを実証
- OANDA audit (07:38→11:38 UTC): **0 LIVE / 29 shadow_tracking skipped / 1 blocked(agg-kelly) / 0 sent** — 偽sent なし (07-02 の accept/reject contract fix が持続)。firing: dt_sr_channel_reversal(8) / session_time_bias(7) / sr_break_retest(5)
- Learning: id=91 (07-01 sr_channel_reversal blacklist) 以降 新規調整なし。current_params 不変
- Tier 変更なし → portfolio auto-sync / strategy pages 編集不要（良性窓、閾値クロスなし）
- **Lint**: (1) WR/PnL/DD/edge 数値は index.md 全6箇所 (header/System State/ruin/kelly/last-updated/session-history/trade-log link) で 98.97%/-527.9/N=555/-32.3% 一致 ✅ (2) [[2026-07-03]] リンク解決 ✅、新規破損リンク 0件 (top-level 未解決14件は既存) (3) stale なし — データ 07-03 当日
- ⚠️ 未解決（継続）: `API_AUTH_TOKEN` watchdog gap (user が Render dashboard で値投入待ち) / sr_anti_hunt_bounce shadow data corruption

## 2026-07-06 wiki-daily-update (scheduled task)
- ✅ APIフェッチ完了 (demo/stats date_from=2026-04-08, demo/learning, risk/dashboard, oanda/audit limit=30) — 全て Render 本番一次ソース
- ✅ Trade log 作成: `raw/trade-logs/2026-07-06.md`
- **本日のスナップショット (is_shadow=false)**: N=**556** (+1 fill vs 07-03。**07-04/05 は週末で市場クローズ** → 実質1-fill窓)。その1件は **orb_trap に完全一致** (N=3→4, PnL +26.8→+23.2, WR 66.7%→50% = **−3.6pip の負け 1本**, 0W/1L) — book の全変動量。WR=43.7% (−0.1pp), decided 46.5% (−0.1pp), EV=-0.96 (−0.01), PnL=**-531.5pip** (−3.6pip)。orb_trap は #1 LIVE昇格候補のため小N記録に傷 (aggregate は WR50% N4)
- **リスク**: DD=**99.33%** (+0.36pp ⚠️⚠️⚠️ **NEW HIGH — −$1000/100%まで<$24**、eq=−$976.4、spike ではなく slow grind — わずか1本の負けでも high-water DD が更新されるほど book trough が100%線に接近)、ruin=0.0% ✅、defensive 0.2× 維持。MC tail は微減 (worst DD99 226.36→**212.58**、median final eq 829→**841**)
- **30d / overall edge**: risk dashboard の overall edge=**-29.63%** (07-03 の 30d -32.3% から window-roll で ease — 6月上旬 trade が窓外へ、real edge gain ではない)。net=**-242.6pip** (+40.1 eased)、friction 3.98/trade、Sharpe -0.398、DSR 0.0/haircut 100%。by-instrument 内訳は今回の fetch (risk dashboard summary) には非露出 → 前窓の read を定性的に継承 (GBP_USD #1 drag)
- OANDA audit (06:37→12:01 UTC): **0 LIVE / 30 shadow_tracking skipped / 0 blocked / 0 sent** — 偽sent なし (07-02 accept/reject contract fix 持続)、今窓は agg-kelly gate に到達した signal なし (07-03 は1件ブロック)。firing: session_time_bias(6) / vol_momentum_scalp(6) / trendline_sweep(5) / sr_break_retest(4)
- Learning: daytrade WR42.5%/EV-2.3/n87, scalp WR40.7%/EV-0.15/n388。sr_channel_reversal scalp blacklist 再確認 (WR25%/EV-0.98/n20)。current_params 不変、新規構造変更なし
- Tier 変更なし → portfolio auto-sync / strategy pages 編集不要（良性窓、閾値クロスなし）
- **Lint**: (1) 現状態の数値は index.md 全5箇所 (header/System State/last-updated/session-history/trade-log link) で 99.33%/-531.5/N=556/-29.63% 一致 ✅ (残る 98.97/-527.9/555 参照は line171/251 の 07-03 履歴記述=正) (2) [[2026-07-06]] リンク解決 ✅、新規破損リンク 0件 (3) stale なし — データ 07-06 当日 (run は 07-07 JST 早朝)
- ⚠️ 未解決（継続）: `API_AUTH_TOKEN` watchdog gap (user が Render dashboard で値投入待ち、agg-kelly gate が現行の稼働中セーフティネット) / sr_anti_hunt_bounce shadow data corruption

## 2026-07-07 fx-roadmap-v23-handoff 完遂 + lint
- ✅ ゲート④(改) LOCKED 化 = PR #51 マージ (main 0cf4e01a) / roadmap v2.3 DRAFT 起案 = PR #52 マージ (main 5212b5c7、[[roadmap-v2.3-payoff-friction-repair]] + index.md/CLAUDE.md 参照更新 + 検証ログ節)
- ✅ 独立再計測 (snapshot 12,325行): clean live 30d N=92/−242.6p/WR55.4%/payoff 0.27 完全再現。draft の shadow N=2,466 は dedup キー未照合 (raw 3,281) — v2.3 T4 着手時に estimand 確定要
- ✅ Lint: v2.3 draft の wikilink 4/4 解決 (main 上)。ローカル (research/h4-level-edge) の index.md/CLAUDE.md 参照も v2.3 へ同期、draft ファイルをローカルへ複製
- ⚠️ **main の index.md DD 行が stale (80.03%/2026-06-10)** — monitor 系の index 更新が research/h4-level-edge 側にのみ蓄積 (53 commits 未 push 乖離の症状、MEMORY project_main_divergence_resolved 参照)。v2.3 は表示 DD% を監視 KPI から除外し実 NAV(JPY) 基準へ統一予定のため、main 側 DD 行の単発修正はせず乖離解消 (別件) に委ねる
