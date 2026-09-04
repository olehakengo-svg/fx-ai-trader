# Knowledge Base Change Log

## 2026-07-27 (wiki-daily-update 自動実行 — flat book 5窓連続 + roll-ease edge/MC tail)
- **Daily trade log**: `raw/trade-logs/2026-07-27.md` 生成。✅ **通常の月曜再開** (07-24 Fri → 07-27 Mon、FX 週末 07-25/07-26 を跨ぐ、異常 gap なし)。realized book は **flat (0 closed fills、5窓連続 07-16=07-21=07-23=07-24=07-27)**。N=**563** 不変 (245W/284L/34BE、全 decided 指標が 07-16 と bit-for-bit 同一: WR 43.5%/decided 46.3%/EV −0.98/PnL −552.7/Wilson 42.1・BF 39.3/avg R 0.12)。shadow_count 10,345→**10,456 (+111、shadow のみ)**。
- **Risk state**: 🔴🔴🔴 **DD 100.8% held** (07-13 breach からバリア超え継続、NEW HIGH なし・deepening なし、eq −$991.1/peak +$16.9 flat)。ruin 0.0% (0.2× lot cap のみによる)。30d overall edge (risk dash) **−33.03%→−25.69%** (🟢 eased +7.34pp)。**window-roll のみ** — n 47→38 (effective_date_from → 2026-06-27、週末跨ぎで 9 件が窓外へ)、0 new fills で **net-negative な 9-trade cohort が脱落** → net −129.2→**−75.6**、per-trade −2.75→−1.99、Sharpe −0.4385→**−0.3258**、MC tail **narrowed** (worst DD99 215.72→**170.0**、median max DD 165.52→**120.88**、median final eq 835.84→**881.0**)。**07-21 と同型の mechanical roll で新エッジ gain ではない**。原エッジは不変で依然深く負。
- **OANDA audit** (07:46→11:22 UTC): **0 LIVE / 30 shadow_tracking skipped / 0 blocked / 0 false-sent** (07-02 contract fix 持続、偽sent なし)。⚪ 0 blocks — 本 pull では agg-kelly gate に到達した signal なし (07-13/07-16/07-24 の all-shadow パターン)。firing: session_time_bias(8)/london_breakout(8)/eurgbp_daily_mr(3)/dt_bb_rsi_mr(2)/dt_sr_channel_reversal(2)/ob_retest(2)。instruments: GBP_USD(14) most active/EUR_USD(5)/USD_JPY(5)/EUR_GBP(3)/GBP_JPY(3)。units: 1000u×25 / 0u×5。
- **Learning API**: 新規 adjustment なし (最新 id=92, 07-06 sr_channel_reversal scalp blacklist re-affirm)。current_params 不変 (confidence_threshold 30 / max_open_trades 8 / max_consecutive_losses 3 / learn_every_n 10 / blacklist 空)。daytrade WR 41.9%/EV −2.31/N93 (**by_conf high +0.19/WR48.4/n31 = 唯一の非負 conf tier**、RANGE のみ regime +0.4)、scalp WR 40.8%/EV −0.27/N388。per-strategy Kelly は bb_rsi_reversion のみ +edge (+0.1584/WR 72.7%/odds 0.5927)。
- **Strategy pages**: 更新なし (0 fills、by_type table 不変、tier 変更なし)。best cum: orb_trap +23.2 / post_news_vol +19.0 / ema_pullback +17.8。worst cum: session_time_bias −67.8 / vwap_mean_reversion −63.1 / wick_imbalance_reversion −63.0 / trendline_sweep −49.7。
- **index.md**: Session History 先頭に 07-27 エントリ prepend + "Last updated:" 行を 07-27 現状態へ更新 (563/−552.7/DD 100.8%/edge −25.69%/[[2026-07-27]])。
- **Lint**: (1) 現状態の数値は本 commit の変更箇所 (trade-log / log.md / index.md Session History top + last-updated) で 563 / −552.7 / DD 100.8% / edge −25.69% / 0-fills-0-blocks が一致 ✅。⚠️ **index.md の System State 本文は 07-08 (N=558/−540.7/DD 100.01%) のまま stale** — これは複数の直近 run で「別件」として繰越されている既知の narrative reconciliation item (last-updated 行に明記追加)。現状態の正は last-updated 行 + Session History top エントリ。(2) [[2026-07-27]]→raw/trade-logs/2026-07-27.md 解決 ✅、[[monthly-target-rederivation-2026-07-10]]/[[shortest-path-decision-memo-2026-07-10]]/[[weekend-gap-oos-prereg-2026-07-24]]/[[mof-intervention-forward-prereg-2026-07-24]] 全解決 ✅、本 commit 新規破損リンク 0件。(3) stale なし (本日データ、Render API 一次ソース) — cadence は 07-24→07-27 の週末跨ぎ通常再開。
- ⚠️ 未解決（継続）: `API_AUTH_TOKEN` watchdog gap (agg-kelly gate が現行の稼働中セーフティネット) / sr_anti_hunt_bounce shadow data corruption / index.md System State 本文の 07-08 stale (narrative reconciliation は別件、v2.3 は実 NAV(JPY) 基準へ移行予定)。

## 2026-07-25 (weekend_gap_fade live 実装 — R1 step③ user 承認 (option b: 直接 live MIN lot) 執行, rule:R1)
- **user 最終承認 2026-07-24 取得** → [[weekend-gap-stage2-execution-prereg-2026-07-24]] 🔒 LOCKED 化 (DRAFT 改名)。registry に G1/G2 監視 2 本追加
- **実装** (workflow: implement → 敵対的レビュー 2 周 → fix → verify、blocker/major 残ゼロ): 新 entry_type `weekend_gap_fade` — [[weekend-gap-fade]] 戦略カード新設
  - シグナル: strategies/daytrade/weekend_gap_fade.py (explore 定義完全複製、凍結 qualify 20.0/21.4/25.0p、BT/live 統一)
  - 執行: Sunday runner (`_weekend_gap_tick`、市場 closed gate 前に 3 ペアのみ評価 → 通常 _tick_entry ガードチェーンに合流 = 別送信経路なし) + 新 MODE_CONFIG daytrade_audusd。成行 1 回 (bridge max_attempts=1 — 旧コードの timeout 3 回黙示リトライ = 二重約定リスクを封鎖)、spread cap 10.0p 超過/取得不能は fail-closed shadow ([WEEKEND_GAP_SPREAD_SKIP]、分母保存)
  - exit: +4h horizon (exact override)、TP-hit 両方向 skip、BE/trail/C1/SIGNAL_REVERSE 全非適用、disaster SL 150p (stopLossOnFill)
  - サイジング: 1000u 固定 sentinel (lot chain/LDN/JPY-cap/Kelly/DD lever 非乗算を検証済)
  - dedup: system_kv per-pair per-weekend latch (fail-closed)。G1 (slippage rolling6 > +2.0p) / G2 (N=12 cum < −60p) = 恒久 kv flag WEEKEND_GAP_LIVE_STOPPED、再武装経路なし (watchdog 教訓)、AlertManager 通知付き。実 fill slippage を bridge → demo_trades.slippage_pips に記録 (G1 は broker 実測)
  - 登録 4 点 + 補助 6 点 (SHIELD whitelist / QUICK_HARVEST 免除 / agg-Kelly min-lot bypass / MODE_CONFIG 等) を test pin で固定
- **レビュー minor 2 件も修正済み**: app.py slippage basis (weekend_gap は entry_fill、TP rebase は非連動) / 早期 _ba None も fail-closed に拡張。tests/test_weekend_gap_fade.py 33 本 green、全 suite green、check.py 9/9
- **初回 live イベント候補 = 2026-07-26 (日) 21:00 UTC**。PR → CI → main マージ → Render auto-deploy で執行

## 2026-07-24 (gap R1 step② 完了: stage-2 執行 pre-reg DRAFT — user 最終承認待ち, rule:R1)
- **新規**: [[weekend-gap-stage2-execution-prereg-2026-07-24]] (当時 DRAFT、07-25 承認後に LOCKED 改名) (decisions/) — 執行仕様凍結案 (Sunday open 初バー成行 1 回 + **spread cap 10.0p** 超過 skip / exit = +4h time-exit のみ、TP/BE/Trail 非適用で estimand 保存 / disaster SL 150p) + 全メカニズムに PRICE_SHOCK_REV 本番前例の実在確認済み
- **要実装注意**: E1 スプレッドフィルター (L5134) が日曜 open を必ずブロック → 本 entry_type 限定の専用 cap 置換が必要 (全面バイパスではない、R2 gate 併設)。dedup = per-pair per-weekend latch (system_kv 永続)
- **サイジング**: 1000u 固定 sentinel。月次期待 +22〜26p / σ≈63p (単月負確率 34%)。M1 寄与 ~11% と正直に明記 — 価値は初 OOS-PASS セルの live 検証 + lot ladder 土台
- **前向きゲート**: G1 slippage>+2.0p→R2 停止 / G2 N=12<−60p→R2 demote / G3 N=30 で BT/live 乖離判定 → lot 増額は別 R1
- **user 決裁オプション**: (a) shadow-first / (b) 直接 live MIN lot (起案推奨) / (c) 追加実測待ち / (d) 見送り — **R1 step③ = user 最終承認待ち、live 変更なし**

## 2026-07-24 (gap R1 step① 完了: 日曜 open 実スプレッド遡及実測 12 週末 — PASS 方向保存, rule:R3=分析のみ)
- **OANDA 歴史 BA candle で 12 週末 × 3 ペア = 36/36 遡及取得** (前向き蓄積不要、≥8 週末要件充足)。tools/sunday_open_spread_measure.py + bt-results/reports
- **3× RT 仮定は一様に保守的ではなかった**: USD_JPY 初バー実測 RT p50 7.55p > 仮定 6.42p (10/12 週超過、OANDA 週明け cap 10p 張り付き)。EUR_USD/AUD_USD は概ね仮定内。ただし**実測 RT で arm B EV 再計算 → +7.90p (mean) / +3.26p (p90 tail) — PASS 方向保存** (verdict +9.04p 比 ~1.1p 劣化)
- **執行設計の核心 (stage-2 入力)**: spread は減衰でなく **22:01 UTC (Sydney 開始) で段差崩落する二値構造** (初 1h 4-8p 高原 → 即 1.5-2p)。中間遅延は無価値。推奨 primary = 成行 @ 初バー + 発注時 spread cap (~10p) forward ルール、exit (+4h) は通常スプレッド域で stress 不要。AUD_USD 理論 RT 2.5p は保守的 (実測 1.8p)
- 留保: 12 週末は平穏期 — news-weekend は p90 行 (+3.26p) を参照。slippage 0.5p は通常市場仮定

## 2026-07-24 (COT extreme explore: ❌ 全滅 FAIL — healthy kill、pre-reg 起案せず, rule:R3=分析のみ)
- **台帳 family #5 クローズ**: net_pct_oi 3y percentile 極値 × 週次ホライズン、release-lag +3営業日凍結、lookahead assert 全通過。**BH-FDR 生存 0/36 (primary) + 0/6 (pooled)**。pooled 1w reversion +22.0p は SNB 2015 単一イベントが 63% — 除外で median +0.9p。tercile 単調性 0/6、年次符号振動 = 点推定 incoherent (underpowered ではない)
- **ban 範囲限定**: 「レベル極値×週次」のみ再試行禁止。Δnet/flow 系・commercial 側は別 estimand として新 family + pre-2022 explore からのみ可
- 成果物: tools/cot_extreme_explore.py + bt-results/reports。OOS (2022+) の COT×価格ジョイント接触ゼロ (assert ×2)

## 2026-07-24 (weekend_gap OOS verdict: ✅ family PASS 候補 — プロジェクト初の OOS 確定正セル候補, rule:R1 stage-1)
- **verdict (期日 7 日前倒し、単一実行)**: [[weekend-gap-oos-prereg-2026-07-24]] §11 — **arm B (pooled exGBP 4h fade) 全ゲート PASS**: N=177/112wk、gross +15.60p (weekend-block p<1e-4)、**stressed-net (3×RT=6.56p) +9.04p**、headroom 24.8≥21.9p、knife-edge 4/4 反転なし (DST 再anchor N=197 +12.53/+5.97、8×/12×RT 摂動、spike-revert flag 2 件除外再計算 +15.20/+8.64)。❌ arm A (EUR_USD IUT 4h+12h) は 12h p=0.1189 で BH 落ち → arm クローズ (4h 単独再採点は禁止 rescue)
- **shrinkage 予測と逆転**: 事前予測「現実的 PASS 経路 = arm A、arm B は FAIL 圏 (−2.10p)」→ 実際は arm B +75% 増幅・arm A 12h 53% 減衰。効果構成が USD_JPY/AUD_USD へシフト (§6 宣言済み構成シフト範囲内、estimand 不変)
- **手続き**: 実装 → explore 窓 dry-run 再現 → 敵対的スクリプト監査 CLEAN → OOS 単一接触。完全性監査 232/234 週末、GBP 非ロード assert
- **次段 (即 live 禁止)**: §9 R1 — (i) 日曜 open 実スプレッド ≥8 週末実測 (AUD_USD RT 2.5p 理論仮置きの置換必須) → (ii) stage-2 執行 pre-reg → (iii) user 最終承認。registry `weekend-gap-oos-verdict-deadline` resolved

## 2026-07-24 (wiki-daily-update 自動実行 — flat book 4窓連続 + roll-worsen edge)
- **Daily trade log**: `raw/trade-logs/2026-07-24.md` 生成。✅ **cadence 復帰** (07-23 Thu → 07-24 Fri、1-day window、gap なし)。realized book は **flat (0 closed fills、4窓連続 07-16=07-21=07-23=07-24)**。N=**563** 不変 (245W/284L/34BE、全 decided 指標が 07-16 と bit-for-bit 同一: WR 43.5%/decided 46.3%/EV −0.98/PnL −552.7/Wilson 42.1・BF 39.3/avg R 0.12)。shadow_count 10,226→**10,345 (+119、shadow のみ)**。
- **Risk state**: 🔴🔴🔴 **DD 100.8% held** (07-13 breach からバリア超え継続、NEW HIGH なし・deepening なし、eq −$991.1/peak +$16.9 flat)。ruin 0.0% (0.2× lot cap のみによる)。30d overall edge (risk dash) **−31.7%→−33.03%** (⚠️ worse −1.3pp)。**window-roll のみ** — n 48→47 (effective_date_from → 2026-06-24)、0 new fills で **1件の slightly-positive EUR_JPY (≈+2.4) が窓から脱落** → net −126.8→**−129.2**、Sharpe −0.423→−0.4385、MC tail widened again (worst DD99 209.06→**215.72**、median final eq 841.18→**835.84**、median max DD 160.26→**165.52**)。**07-21/07-23 の mechanical roll の継続で新エッジ損失ではない**。
- **30d by-instrument (n=47、全4 negative)**: GBP_USD **#1 abs drag −47.1** (mean −3.36, n=14) / USD_JPY −36.2 (n=19) / EUR_JPY −31.1 (n=9、**worst mean −3.46**) / EUR_USD −14.8 (n=5)。per-strategy Kelly は bb_rsi_reversion のみ +edge (+0.158/half-Kelly 0.134)。correlation flags: bb_rsi_reversion↔zz_pivot_v60_sr −0.795 / dt_sr_channel_reversal↔trendline_sweep +0.521。
- **OANDA audit** (08:02→11:40 UTC): **0 LIVE / 30 shadow_tracking skipped / 0 blocked / 0 false-sent**。⚪ 0 blocks — 本 pull では gate に到達した signal なし (07-23 の 2 blocks と対照、07-13/07-16 の all-shadow パターンに復帰)。firing: session_time_bias(9)/london_breakout(5)/sr_break_retest(5)/wick_imbalance_reversion(3)。instruments: GBP_USD(12) most active/EUR_USD(9)/EUR_GBP(4)。
- **Learning API**: 新規 adjustment なし (最新 id=92, 07-06 sr_channel_reversal scalp blacklist re-affirm)。current_params 不変。daytrade WR 41.9%/EV −2.31/N93 (RANGE のみ +0.4)、scalp WR 40.4%/EV −0.18/N388。
- **Strategy pages**: 更新なし (0 fills、by_type table 不変、tier 変更なし)。
- **index.md 更新**: 目標行 (4窓連続 flat)、System State block (DD/edge/ruin/agg-Kelly/Last-updated)、Session History に 07-24 narrative 追加、Trade Logs リンクに **07-21/07-23/07-24 を backfill** (既存ファイルが未リンクだった orphan を解消)。
- **Lint**: ✅ WR/PnL/DD 数値は trade-log↔index↔log 間で一貫 (N=563/WR43.5%/PnL−552.7/DD100.8%/edge−33.03%/net−129.2/n47/shadow10,345)。✅ 本 run で追加した wikilink 全て解決 ([[2026-07-21]]/[[2026-07-23]]/[[2026-07-24]] + 2 pre-reg + 2 memo)。✅ データ当日取得、陳腐化なし。⚠️ 既存の破損 wikilink backlog (~170件) は本 run で件数不変 (新規破損なし)、別タスク継続。⚠️ API_AUTH_TOKEN watchdog gap (agg-kelly gate が active safety net)・sr_anti_hunt_bounce corruption・index.md DD-line divergence (v2.3 real-NAV JPY basis 移行) は未解決継続。

## 2026-07-24 (MoF 介入 forward pre-reg 🔒 LOCK — 期限 12 日前倒し, rule:R1 stage-1)
- **LOCK 執行**: [[mof-intervention-forward-prereg-2026-07-24]] — explore 実行 (7日/3エピソード、h*=10d SELL 6/7、band [−319.8,−43.6]p) + 識別 rule (X,Y)=(2.0, 0.25%) 裁量ゼロ校正 (git タイムラインで事前宣言を客観確認) → 敵対的レビュー (必須3+任意5、コア規律・算術は全検算一致) → 全反映 → **即日 LOCK (08-05 期限の 12 日前倒し — LOCK 任意期間の file-drawer 裁量窓を閉鎖)**
- **凍結の要点**: candidate S={2026-04-30, 05-06} / M=21 / k_eff 規約 (= |D∩母集団|) / anchor はデータ存在営業日 roll / **P-10 attestation: 2026 candidate 日の forward net は誰も未計算、開示前計算禁止**。E-D 予測 (k∈[2,5]) 下の E-A PASS ≒「両候補日とも開示介入日」
- **訂正 (レビュー)**: FP 除外版 36/717=5.02% (旧 5.06% 転記誤り)、「05-07 欠損は PASS に不利」主張を撤回 (方向不定)、エピソード規約 = gap≥30d で 3 (2022-09↔10 は 29 日差 knife-edge)
- registry: `mof-forward-prereg-lock-deadline` resolved → `mof-q2-2026-disclosure-verdict` (backstop 09-30) に置換

## 2026-07-24 (weekend_gap OOS pre-reg 🔒 LOCK, rule:R1 stage-1)
- **LOCK 執行**: [[weekend-gap-oos-prereg-2026-07-24]] — 起案 → §10 4 論点 quant 裁定 (headroom=10×通常RT / N floor 25/60 / arm A IUT 維持 / DST 格下げ厳格側) → **敵対的レビュー 1 本 (リーク・設計破綻ゼロ、決定境界曖昧性 6 点)** → 必須 6 + 推奨 6 全反映 → LOCK
- **重要訂正 (レビュー #1)**: arm B の explore 凍結値は GBP 込みプールの誤帰属だった → GBP 除外セット直接再計算 (explore 窓のみ) **+8.92p / weekend-block p<1e-4 / MFE p50 24.6p / N=169**。50% shrinkage 予測 → stressed-net −2.10p (§4.1 の保守的結論は不変)
- **新規凍結規則**: BH step-up 完全決定表 / 混合アウトカム優先順位 (検定済み FAIL ≥1 → 永久 CLOSE) / feed-artifact flag → PASS arm 符号反転で knife-edge FAIL / dry-run 検証プロトコル (explore 再現必須) / 階層多重性宣言
- registry 登録: `weekend-gap-oos-verdict-deadline` (07-31) + `mof-forward-prereg-lock-deadline` (08-05)。verdict 実行は LOCK コミット着地後に開始 (監査整合)

## 2026-07-24 (wave-0 explore 完了 — 5線 verdict + pre-reg 起案 2 本, rule:R3=分析のみ)
- **台帳更新** ([[hypothesis-catalog-2026-07-24]] §wave-0 実行記録): 5 線完了・敵対的レビュー INVALID ゼロ
- **#1 sweep_reversion**: exit-free 12.4y で生存確定 (12h net med +5.10p p<1e-4、11/13 年正) — exit-artifact 説棄却、P-S1(a) 決裁パケットの中核証拠に
- **#2 price_shock**: demotion flag 0/5 だが **MASSIVE feed artifact 発見** (土曜行+不良プリント、grid ev_pip 過大 USD_CAD 97.9→42.4p) + 3 席 regime watch (EUR_AUD/USD_CAD/AUD_JPY pre-2021 OOS 弱)
- **#3 weekend_gap**: multiday 棄却、狭候補凍結 (≤12h fade EUR_USD/pooled) → OOS pre-reg DRAFT 起案中
- **#4 MoF**: 383 events 正規化完了。**時限機会 = 2026 エピソード ¥11.73 兆の日次内訳が Q2 開示前 → LOCK 期限 2026-08-05 の forward pre-reg DRAFT 起案中**
- **#5 COT**: panel 5,178 行完成 (分析は pre-reg 待ち)
- chips: sweep P-S1(a) パケット準備 (exit-free 証拠込みに更新) / MASSIVE feed 品質ガード

## 2026-07-24 (仮説カタログ + 探索最大化起動 — user 指示「爆速・複数本並列・網羅的に」)
- **新規**: [[hypothesis-catalog-2026-07-24]] (syntheses/) — 7 レンズ × 87 本生成 → 再試行禁止フィルタ (BANNED 2) → triage。**台帳 m=12** (新規 7 ファミリ + 既登録 5)、並列アクティブ上限 3 本、凍結探索プロトコル (explore=2014-2021 / OOS=2022-2026 一発、exit-free h∈{4h..120h}、BH-FDR q=0.10)。Raw 全量: `raw/analysis/hypothesis-catalog-2026-07-24.json`
- **wave-0 起動 (本日)**: sweep_reversion 再検証 (72) + price_shock 5席監査 (58) + weekend_gap explore (47、background)。**wave-1 fetch 発火**: MoF 介入リスト (66、S4 の data-block 解除) + COT panel (50、fetch のみ)
- **棚卸し資産確認 (analyst 実測)**: sweep_reversion rescued shadow **unique N=8/10** (EV +2.48p、WR 75%) — P-S1(a) R1 決裁トリガまであと 2 イベント、決裁パケット準備 task 起票。htf_fb recheck は実測ペース 0.14 行/日で n_decide=100 に構造的到達不能 (2028 年) → 受動放置確定。**戦略カード Status stale 訂正** ([[sweep_reversion_eurgbp_late]]: 「LIVE env=1」→ R2 STOP code pin + shadow rescue 稼働中)
- **横断発見**: 同一バー二重記録 (row 14 = unique 8) — shadow_count_decision 型トリガの N は **unique バー基準**で数える規律を標準化提案

## 2026-07-24 (エッジ開発 postmortem — 全数検死 + 敵対的検証)
- **新規**: [[edge-dev-postmortem-2026-07-24]] (syntheses/) — 失敗仮説 54 件 + 生存候補 21 件の全数棚卸し (13-agent workflow、根本原因 4 クレームを敵対的検証×2レンズ)。分析のみ、tier action なし
- **主結論**: ①「勝てていた時期」は不存在 (Era-1 昇格は BT 測定器の幻影、検証済みサブセット内反転率 100%) ② 検証装置は完成済み (Era-3 以降 FP live 到達 0) ③ 真因は sourcing (OHLCV×intraday×リテール摩擦の空間は edge < 摩擦+認定閾値) ④ 実測フロア摩擦 1.30p/t、摩擦 binding は +1〜3p/t の狭帯のみ ⑤ 処方箋 = modality 単位期待値評価 + headroom≥10x 入場条件 + sweep_reversion_eurgbp/htf_fb recheck の棚卸し回収
- **同セッション**: 金利差フェアバリュー仮説 (UIP/CIP/yield-spread) を口頭評価で REJECT/HOLD 低優先 (CIP=乖離<摩擦、UIP=anti-carry 負EV、[[hull-donchian-usdchf-ratediff-prereg-2026-06-15]] の falsification と整合)。edges/ ページ未作成 (実装提案なしのため)
- **T7 CLOSED**: carry dip 0-fire は ceiling 159.50 のレジーム前提崩壊による dormant-by-design (バグ非ず)。QUALBAR print telemetry 本番稼働。[[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §6
- **T8 forensic #2 = 共通挙動**: hull は guard 実装済みだが `compute_daytrade_signal`/`compute_hourly_signal` が **poll 毎に Engine を再構築**するため全戦略の instance-state dedup/cooldown が live で無効。live の dedup 層は recent_emit のみ。order 層 per-bar dedup タスクを queue 投入、ゲート④ order 層補正 + 再 LOCK は user R1 決裁待ち。[[t8-week1-gate-breach-2026-07-06]]
## 2026-07-06 (pre-reg トリガー監視自動化, rule:R3)
- T5 の 18 日執行ギャップ再発防止: prereg_trigger_watch.py + registry + Tier A cron 統合 + check.py env gate 宣言整合チェック。新規 pre-reg LOCK 時は registry への監視エントリ追加が必須運用に
## 2026-07-06 (T5 pre-reg 発動執行: JPYキャップ撤退 SIZE lever 0.5x, rule:R2)
- **発動**: [[jpy-cap-exit-prereg-2026-06-12]] トリガー1「USD_JPY D1 close > 160.80」が **2026-06-18 成立** (161.295、以降14営業日連続超え・max 162.631)。検出は本日 = **18日の執行ギャップ** (監視機構不在が原因、pre-reg 文書に教訓追記)
- **執行**: `_resolve_jpy_cap_exit_size_lever` (demo_trader.py、LDN lever 同型・lot チェーン最後段・LIVE-only) で対象4戦略 (vsg_jpy_reversal / dt_sr_channel_reversal / vix_carry_unwind / ema200_trend_reversal) の LIVE lot **0.5x**。Shadow 無変更 (原則3)。code pin + 回帰テスト5件
- **整合実測**: 06-19 daily で JPY crosses 反転 (EUR_JPY +19.1→-5.3 / USD_JPY +16.3→-1.4)、対象戦略軒並み loser 化 — pre-reg の予言どおり

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

## 2026-07-07 wiki-daily-update (scheduled task)
- ✅ APIフェッチ完了 (demo/stats date_from=2026-04-08, demo/learning, risk/dashboard, oanda/audit limit=30) — 全て Render 本番一次ソース
- ✅ Trade log 作成: `raw/trade-logs/2026-07-07.md`
- **本日のスナップショット (is_shadow=false)**: N=**558** (+2 fills vs 07-06 の 556, **0W/2L** = −9.2pip aggregate ≈−4.6pip each; 243W/282L/33BE — wins 不変, losses +2)。exact cell 未確定 (prior by_type snapshot 未キャッシュ)、GBP_USD が live 側最活性。WR=43.5% (−0.2pp), decided 46.3% (−0.2pp), EV=-0.97 (−0.01), PnL=**-540.7pip** (−9.2pip)
- **リスク**: 🔴🔴🔴 **DD=100.01%** (1000.1pip, eq=−$983.2 vs peak +$16.9) — **100%バリアを初めて突破** (+0.68pp vs 07-06 の 99.33%)。6〜7月を通じて接近し続けた −$1000/100% 線が modest な 2-loss 窓で貫通。spike ではなく slow grind。realized ruin=0.0% は 0.2× lot cap のみによる (原エッジは負)。defensive 0.2× 維持。MC tail widened (worst DD99 212.58→**215.76**、median final eq 841→**838.83**)
- **30d edge**: overall edge=**-30.79%** (⚠️ **WORSENED −1.16pp vs 07-06 の -29.63%**) — 複数窓続いた "window-roll で ease" パターンを打ち切り、今窓は新規2損失が roll-off を上回り悪化。net=**-251.8pip** (−9.2)、friction 4.02/trade、Sharpe -0.408、DSR 0.0/haircut 100%。**by-instrument (n=94, 全4負)**: **GBP_USD #1 drag -136.7 (mean -3.51, n=39)** / USD_JPY -51.8 / EUR_JPY -38.0 / EUR_USD -25.3 (この fetch は by_instrument 露出あり)
- 🟢 **1 CONFIRMED LIVE FILL**: dt_bb_rsi_mr (strategy) → daytrade_gbpusd (mode) GBP_USD 1000u、`bridge_status=filled`、**oanda_trade_id=549086**、is_live=true @ 06:41 UTC。pnl_pips=null (**open**)。**06-24 (#541666) 以来の確定 live fill**。1000u=5000u base × 0.2× defensive。paired `sent`/`filled` 行 (同一 timestamp) は twin-meaning (sent=戦略名 / filled=MODE名) の同一実弾二重記録=**偽sent ではない** (実 trade id 保持、07-01 とは対照)
- OANDA audit (06:17→11:52 UTC): **1 LIVE / 28 shadow_tracking skipped / 0 blocked / 0 false-sent**。firing: dual_sr_bounce(9) 支配 / sr_break_retest(3) / vol_momentum_scalp(3) / session_time_bias(3) / ema200_trend_reversal(3)。instruments: USD_JPY(12) 最活性。audit table total=11,585 行
- Learning: 新規 adj id=92 (2026-07-06 13:13 UTC) = sr_channel_reversal scalp blacklist 再確認 (WR25%/EV-0.98/n190、ids 85→92 全て同一 blacklist の再確認)。daytrade by-conf は全 bucket EV-negative (high WR44.8/EV-0.33 が least-bad、mid EV-3.97、low EV-2.18)。strategy_kelly: bb_rsi_reversion のみ +edge (+0.158, half-K 0.134, WR72.7% n=11)、他は全 0.0/insufficient。current_params 不変
- Tier 変更なし → portfolio auto-sync / strategy pages 編集不要。dt_bb_rsi_mr の live fill #549086 は **open (pnl null)** のため、closed outcome 確定まで strategy page への live-activity 記載は deferred (良性窓+閾値クロス無しの既存 daily 規律に従う)
- **Lint**: (1) 現状態の数値は index.md 全5箇所 (header/System State/Aggregate Kelly/last-updated/trade-log link) で 100.01%/558/-540.7/-30.79% 一致 ✅ (残る 99.33/-531.5/556 参照は 07-06 の session-history 行 + 07-06 trade-log link=履歴として正) (2) [[2026-07-07]] → raw/trade-logs/2026-07-07.md 解決 ✅、新規破損リンク 0件 (既存 182件は log.md 自動リンク系で不変) (3) stale なし — データ 07-07 当日
- ⚠️ 未解決（継続）: `API_AUTH_TOKEN` watchdog gap (agg-kelly gate が現行の稼働中セーフティネット) / sr_anti_hunt_bounce shadow data corruption / main の index.md DD 行 stale (乖離解消は別件、v2.3 は実 NAV(JPY) 基準へ移行予定)

## 2026-07-08 wiki-daily-update (scheduled task)
- ✅ APIフェッチ完了 (demo/stats date_from=2026-04-08, demo/learning, risk/dashboard, oanda/audit limit=30) — 全て Render 本番一次ソース
- ✅ Trade log 作成: `raw/trade-logs/2026-07-08.md`
- **本日のスナップショット (is_shadow=false)**: N=**558** — **フラット (0 closed fills vs 07-07)**。243W/282L/33BE / WR 43.5% / decided 46.3% / EV -0.97 / PnL **-540.7pip** / Wilson 42.1(BF 39.3) / avg R 0.12 は**全て 07-07 と bit-for-bit 同一**。実現 book 移動ゼロ。shadow_count 8,832→**8,970 (+138)** — shadow 側 firing は継続、live/closed book のみ静止。07-07 の open fill #549086 (dt_bb_rsi_mr GBP_USD 1000u) は N 不変 = **open のまま** (closed 未確定)
- **リスク**: 🔴🔴🔴 **DD=100.01%** held (**no new high** — 07-07 の 100% バリア突破は本窓で延伸せず、book が動かなかったため)。eq=−$983.2 vs peak +$16.9 flat。realized ruin=0.0% は 0.2× lot cap のみによる。defensive 0.2× 維持。MC tail は narrowed (worst DD99 215.76→**213.16**、median final eq 838.83→**842.39**)
- **30d edge**: overall edge=**-30.1%** (EASED +0.69pp vs 07-07 の -30.79%) — **window-roll only** (EUR_JPY loser 1件が窓外へ、real edge gain ではない)。net=**-244.3pip** (+7.5 eased、n 94→93)、friction 4.01/trade、Sharpe -0.399、DSR 0.0/haircut 100%。**by-instrument (n=93, 全4負)**: **GBP_USD #1 drag -136.7 (mean -3.51, n=39, flat)** / USD_JPY -51.8 (flat) / EUR_JPY -30.5 (n17→16, eased +7.5) / EUR_USD -25.3 (flat)
- ⚪ **0 LIVE fills / 1 agg-kelly block** — `vsg_jpy_reversal` EUR_JPY が `agg_kelly=-0.333<0` で block @ 09:16:47 UTC。aggregate-Kelly gate = 現行の稼働中セーフティネット (原エッジ負の間 live entry を正しく拒否)。07-07 (1件 fill 通過) と対照
- OANDA audit (08:36→11:46 UTC): **0 LIVE / 29 shadow_tracking skipped / 1 blocked / 0 false-sent** (is_live 全 false、filled 行なし、偽sent なし=07-02 contract fix 持続)。firing: session_time_bias(7) / london_breakout(6) / engulfing_bb(2) / vol_momentum_scalp(2) / vsg_jpy_reversal(2) / trendline_sweep(2) + singles。instruments: GBP_USD(16) 最活性 / EUR_USD(7) / EUR_JPY(3) / USD_JPY(3) / EUR_GBP(1)。audit table total=**11,730** 行 (+145)
- Learning: **新規 adjustment なし** (latest 依然 id=92, 2026-07-06 = sr_channel_reversal scalp blacklist 再確認 WR25%/EV-0.98/n190)。current_params 不変 (confidence_threshold 30 / max_open_trades 8 / max_consecutive_losses 3)。by_mode: daytrade/scalp/swing
- Tier 変更なし → portfolio auto-sync / strategy pages 編集不要 (0 fills のフラット窓、閾値クロス無し)
- 📋 別ワークストリーム: **T2 exit-repair verdict FAIL / H0 採択** が 07-08 に着地 (grid 9/9 BH-FDR 不通過 p=1.0 / WF 0/3 / 摩擦調整EV負)。§4 固定分岐発動 → v2.3 主戦線は **WS3 シグナル張り替え** ([[exit-repair-tp-sl-prereg-2026-07-07]] §8)。これは daily book/tier イベントではないため context として記録のみ
- **Lint**: (1) 現状態の数値は index.md 全 state 箇所 (header/System State/Ruin/Aggregate Kelly/last-updated/session-history/trade-log link) で 100.01%(held)/558(flat)/-540.7/-30.1%/net-244.3/0-fills-1-blocked 一致 ✅ (残る -30.79% 参照は全て "vs 07-07's" 比較文 + 07-07 履歴行=正) (2) [[2026-07-08]] → raw/trade-logs/2026-07-08.md 解決 ✅、[[exit-repair-tp-sl-prereg-2026-07-07]]/[[roadmap-v2.3-payoff-friction-repair]] 解決 ✅、新規破損リンク 0件 (3) stale なし — データ 07-08 当日 (Render API 一次ソース)
- ⚠️ 未解決（継続）: `API_AUTH_TOKEN` watchdog gap (agg-kelly gate が現行の稼働中セーフティネット) / sr_anti_hunt_bounce shadow data corruption / main の index.md DD 行 stale (乖離解消は別件、v2.3 は実 NAV(JPY) 基準へ移行予定)

## 2026-07-13 wiki-daily-update (scheduled task)
- ✅ APIフェッチ完了 (demo/stats date_from=2026-04-08, demo/learning, risk/dashboard, oanda/audit limit=30) — 全て Render 本番一次ソース
- ✅ Trade log 作成: `raw/trade-logs/2026-07-13.md`
- ⚠️ **5日間の cadence gap (07-09→07-12 に scheduled run なし)** — 07-09/07-10 に analyst session log は存在するが daily YYYY-MM-DD.md / log.md エントリ無し。本日の全 delta は**5日累積**であり単一窓ではない。cadence は本日再開
- **本日のスナップショット (is_shadow=false, 5日累積 vs 07-08)**: N=**560** (**+2 fills 0W/2L** = −15.7pip aggregate ≈−7.85pip each; wins 243 flat, losses 282→284, BE 33 flat)。WR=43.4% (−0.1pp), decided 46.1% (−0.2pp), EV=**-0.99** (−0.02), PnL=**-556.4pip** (−15.7pip), Wilson 41.9(BF 39.1), avg R 0.12。5日間で positive live fill ゼロ。shadow_count 8,970→**9,304 (+334)**
- **リスク**: 🔴🔴🔴 **DD=100.8%** (1008.0pip, eq=−$991.1 vs peak +$16.9) — **07-08 に held していた 100% バリアを2損失で突破し NEW HIGH (+0.79pp)**。slow grind 継続、barrier はもはや天井ではない。realized ruin=0.0% は 0.2× lot cap のみによる。MC tail は**拡大** (worst DD99 213.16→**264.3**、median final eq 842.39→**788.65**) — 5日純損失累積で forward 分布が左シフト。defensive 0.2× 維持
- **30d edge**: overall edge=**-40.0%** (⚠️ **WORSENED −9.9pp vs 07-08 の -30.1%**)。**window-roll easing ではない** — per-trade net が −2.63→**−3.52** に悪化、30d 窓が n 93→64 に縮小し古い good cohort が窓外へ・worse recent trades が支配。absolute net の easing (−244.3→**-225.6**) は分母縮小の artifact。friction 4.04/trade、Sharpe -0.553 (悪化)、DSR 0.0/haircut 100%/n_trials 13。**by-instrument (n=64, 全4負)**: **GBP_USD #1 drag -99.9 (mean -4.00, n=25)** / USD_JPY -55.8 (n=20) / EUR_JPY -53.1 (n=12) / EUR_USD -16.8 (n=7)
- OANDA audit (07:50→11:46 UTC): **0 LIVE / 30 shadow_tracking skipped / 0 blocked / 0 false-sent** (is_live 全 false、filled 行なし、偽sent なし=07-02 contract fix 持続)。**今窓は agg-kelly gate に到達した signal なし** (07-08 の1件 block と対照) — 全て upstream で shadow_tracking skip。gate は稼働中セーフティネットのまま。firing: london_breakout(6) / engulfing_bb(4) / dt_sr_channel_reversal(4) / dual_sr_bounce(3) / gbp_deep_pullback(3) + singles。instruments: GBP_USD(13) 最活性 / EUR_USD(9) / USD_JPY(5) / EUR_GBP(2) / GBP_JPY(1)。audit table total=**12,116** 行 (+386 over gap)
- Learning: **新規 adjustment なし** (latest 依然 id=92, 2026-07-06 = sr_channel_reversal scalp blacklist 再確認 WR25%/EV-0.98/n190)。current_params 不変 (confidence_threshold 30 / max_open_trades 8 / max_consecutive_losses 3 / learn_every_n 10 / runtime blacklist 空)。daytrade by_conf 全負 (high EV-0.33/n29 least-bad, mid EV-4.18/n38 worst)、by_regime 全負 (RANGE -1.62/TREND_BEAR -5.16/TREND_BULL -2.17)
- Tier 変更なし → portfolio auto-sync / strategy pages 編集不要 (marginal 2損失累積、閾値クロス無し)。exact cell attribution は 07-08 by_type baseline 未キャッシュのため deferred (GBP_USD が live 最活性=少なくとも1損失の所在濃厚)
- **Lint**: (1) 現状態の数値は index.md 全 state 箇所 (header/System State/Aggregate Kelly/last-updated/session-history/trade-log link) で 100.8%/560/-556.4/-40.0%/0-fills-0-blocked 一致 ✅ (残る 100.01% 参照は全て "vs 07-08's" 比較文 + 07-08/07-07 履歴行 + 07-08/07-07 trade-log link=履歴として正) (2) [[2026-07-13]] → raw/trade-logs/2026-07-13.md 解決 ✅、[[monthly-target-rederivation-2026-07-10]]/[[shortest-path-decision-memo-2026-07-10]]/[[exit-repair-tp-sl-prereg-2026-07-07]]/[[roadmap-v2.3-payoff-friction-repair]] 全て解決 ✅、新規破損リンク 0件 (3) stale なし — データ 07-13 当日 (Render API 一次ソース)。⚠️ ただし **5日 cadence gap** を検出・記録 (data staleness ではなく scheduler の run 欠落)
- ⚠️ 未解決（継続）: `API_AUTH_TOKEN` watchdog gap (agg-kelly gate が現行の稼働中セーフティネット) / sr_anti_hunt_bounce shadow data corruption / main の index.md DD 行 stale (乖離解消は別件、v2.3 は実 NAV(JPY) 基準へ移行予定)

## 2026-07-14 wiki-daily-update (scheduled task)
- ✅ APIフェッチ完了 (demo/stats date_from=2026-04-08, demo/learning, risk/dashboard, oanda/audit limit=30) — 全て Render 本番一次ソース
- ✅ Trade log 作成: `raw/trade-logs/2026-07-14.md`
- ✅ **cadence 再開** — 07-09→07-12 の 5日 gap は 07-13 で回収済み。本日は正常な単一窓 (vs 07-13)
- **本日のスナップショット (is_shadow=false, vs 07-13)**: N=**560** (**FLAT — 0 closed fills**)。243W/284L/33BE / WR 43.4% / decided 46.1% / EV **-0.99** / PnL **-556.4pip** / Wilson 41.9(BF 39.1) / avg R 0.12 は**全て 07-13 と bit-for-bit 同一**。実現 book 移動ゼロ (07-08 と同型のフラット窓)。shadow_count 9,304→**9,441 (+137)** — shadow 側 firing は継続、live/closed book のみ静止
- **リスク**: 🔴🔴🔴 **DD=100.8%** (1008.0pip, eq=−$991.1 vs peak +$16.9) — **07-13 のバリア突破から held flat、NEW HIGH なし** (book が動かず deepening せず)。realized ruin=0.0% は 0.2× lot cap のみによる。MC tail は不変 (worst DD99 264.3、median final eq 788.65、median max DD 212.38)。defensive 0.2× 維持
- **30d edge**: overall edge=**-40.0%** (flat vs 07-13)。per-trade net −3.52、net −225.6、n=64 (unchanged)、friction 4.04/trade、Sharpe -0.553、DSR 0.0/haircut 100%/n_trials 13。**by-instrument (n=64, 全4負, 07-13 と同一)**: **GBP_USD #1 drag -99.9 (mean -4.00, n=25)** / USD_JPY -55.8 (n=20) / EUR_JPY -53.1 (n=12) / EUR_USD -16.8 (n=7)
- OANDA audit (07:32→11:32 UTC): **0 LIVE / 30 shadow_tracking skipped / 0 blocked / 0 false-sent** (is_live 全 false、filled 行なし、偽sent なし=07-02 contract fix 持続)。**今窓は agg-kelly gate に到達した signal なし** — 全て upstream で shadow_tracking skip。gate は稼働中セーフティネットのまま。firing: session_time_bias(4) / sr_break_retest(4) / vol_momentum_scalp(3) / dt_bb_rsi_mr(3) / dual_sr_bounce(3) / london_breakout(2) / trendline_sweep(2) / ema200_trend_reversal(2) / wick_imbalance_reversion(2) + singles。instruments: GBP_USD(10) 最活性 / USD_JPY(7) / EUR_USD(6) / AUD_JPY(3) / EUR_GBP(2) / EUR_JPY(2)。units: 1000u×20 / 5000u×4 (trendline_sweep EUR_GBP) / 0u×6。audit table total=**12,272** 行 (+156)
- Learning: **新規 adjustment なし** (latest 依然 id=92, 2026-07-06 = sr_channel_reversal scalp blacklist 再確認 WR25%/EV-0.98/n190)。current_params 不変 (confidence_threshold 30 / max_open_trades 8 / max_consecutive_losses 3 / learn_every_n 10 / runtime blacklist 空)
- Tier 変更なし → portfolio auto-sync / strategy pages 編集不要 (0 fills のフラット窓、閾値クロス無し)
- **Lint**: (1) 現状態の数値は index.md 全 state 箇所 (header/System State/last-updated/session-history) で 100.8%(held flat)/560(flat)/-556.4/-40.0%/0-fills-0-blocked 一致 ✅ (残る 100.01%/-540.7 等の参照は全て "vs 07-08's" 比較文 + 履歴行 + trade-log link=履歴として正) (2) [[monthly-target-rederivation-2026-07-10]]/[[shortest-path-decision-memo-2026-07-10]]/[[exit-repair-tp-sl-prereg-2026-07-07]] 全て解決 ✅、新規破損リンク 0件。tier_integrity_check --check = ERROR 0 (既存 warn 2 / info 14 のみ、本編集と無関係) (3) stale なし — データ 07-14 当日 (Render API 一次ソース)、cadence 正常
- ⚠️ 未解決（継続）: `API_AUTH_TOKEN` watchdog gap (agg-kelly gate が現行の稼働中セーフティネット) / sr_anti_hunt_bounce shadow data corruption / main の index.md DD 行 stale (乖離解消は別件、v2.3 は実 NAV(JPY) 基準へ移行予定)

## 2026-07-16 wiki-daily-update (scheduled task)
- ✅ APIフェッチ完了 (demo/stats date_from=2026-04-08, demo/learning, risk/dashboard, oanda/audit limit=30) — 全て Render 本番一次ソース
- ✅ Trade log 作成: `raw/trade-logs/2026-07-16.md`
- ⚠️ **1日 cadence gap (07-15 に scheduled run なし)** — `2026-07-15.md` / log.md エントリ不在。本日の delta は **2日累積 (07-15→07-16)**、単一窓ではない。cadence は本日再開。副次発見: **07-14 の trade-log link が index.md の daily-summary リストから欠落**していたため本編集で 07-14/07-16 を両方追補
- **本日のスナップショット (is_shadow=false, 2日累積 vs 07-14)**: N=**563** (**+3 fills 2W/0L/1BE = +3.7pip**; wins 243→245, losses 284 flat, BE 33→34)。WR=43.5% (+0.1pp), decided 46.3% (+0.2pp), EV=**-0.98** (+0.01), PnL=**-552.7pip** (+3.7pip ✅)、Wilson 42.1(BF 39.3), avg R 0.12。**直近で初の net-positive 窓**だが 563-trade book に対し 2勝は marginal (aggregate −552.7pip はほぼ不動)。shadow_count 9,441→**9,656 (+215)**
- **リスク**: 🔴🔴🔴 **DD=100.8%** (1008.0pip, eq=−$991.1 vs peak +$16.9) — **07-13 barrier 突破から held flat、NEW HIGH なし**。+3.7pip の book 微増は 1-dp 解像度で DD を動かさず (deepening も new-high も無し)。realized ruin=0.0% は 0.2× lot cap のみによる。**MC tail は僅かに拡大** (worst DD99 264.3→**272.36**、median final eq 788.65→**781.25**、median max DD 212.38→**219.75**) — realized book は改善したが 30d edge 悪化で forward 分布が左シフト。defensive 0.2× 維持
- **30d edge**: overall edge=**-40.5%** (⚠️ **WORSE −0.5pp vs 07-14 の -40.0%**)。**window-roll easing に騙されない** — per-trade net が −3.52→**−3.64** に悪化、30d 窓は n 64→60 に roll (effective_date_from → 2026-06-16)、absolute net の easing (−225.6→**-218.5**) は分母縮小の artifact。friction 4.15/trade (+0.11)、Sharpe -0.562 (悪化)、DSR 0.0/haircut 100%/n_trials 12。**by-instrument (n=60, 全4負)**: **GBP_USD #1 drag -96.7 (mean -4.60, n=21)** / USD_JPY -53.9 (n=22) / EUR_JPY -53.1 (n=12) / EUR_USD -14.8 (n=5)。per-strategy Kelly は bb_rsi_reversion のみ +edge (+0.158/half-Kelly 0.134/n=11/WR 72.7%)、他は全て 0.0/insufficient
- OANDA audit (07:25→11:30 UTC): **0 LIVE / 30 shadow_tracking skipped / 0 blocked / 0 false-sent** (is_live 全 false、filled 行なし、偽sent なし=07-02 contract fix 持続)。**今窓は agg-kelly gate に到達した signal なし** — 全て upstream で shadow_tracking skip。gate は稼働中セーフティネットのまま。firing: trendline_sweep(4) / sr_anti_hunt_bounce(4) / dt_bb_rsi_mr(3) / london_breakout(2) / vix_carry_unwind(2) / dual_sr_bounce(2) / three_bar_reversal(2) / vol_momentum_scalp(2) + singles。instruments: EUR_USD(9) 最活性 / USD_JPY(8) / GBP_USD(8) / EUR_GBP(3) / GBP_JPY(1) / AUD_JPY(1)。units: 1000u×20 / 5000u×4 (trendline_sweep EUR_GBP) / 0u×6。audit table total=**12,496** 行 (+224 over the 2-day span)
- Learning: **新規 adjustment なし** (latest 依然 id=92, 2026-07-06 = sr_channel_reversal scalp blacklist 再確認 WR25%/EV-0.98/n190)。current_params 不変 (confidence_threshold 30 / max_open_trades 8 / max_consecutive_losses 3 / learn_every_n 10 / runtime blacklist 空)。scalp by_conf は low のみ +EV (+0.48/n127/WR46.5%)、mid -0.39(n207)/high -0.71(n54)。daytrade by_conf 全負、swing は n=0 not ready
- Tier 変更なし → portfolio auto-sync / strategy pages 編集不要 (marginal +3-fill 窓、閾値クロス無し)。exact cell attribution は 07-14 by_type baseline 未キャッシュのため deferred (2勝は per-strategy Kelly の bb_rsi_reversion +edge と整合するが cell-level 未確認)
- **Lint**: (1) 現状態の数値は index.md 全 state 箇所 (header/System State/Ruin/Aggregate Kelly/last-updated/session-history/trade-log link) で 100.8%(held)/563/-552.7/-40.5%/0-fills-0-blocked 一致 ✅ (残る 560/-556.4/-40.0% 参照は全て 07-14/07-13 履歴行 + "vs 07-14's" 比較文=履歴として正) (2) [[2026-07-16]]/[[2026-07-14]]/[[2026-07-13]] → raw/trade-logs/*.md 解決 ✅、[[monthly-target-rederivation-2026-07-10]]/[[shortest-path-decision-memo-2026-07-10]]/[[roadmap-v2.3-payoff-friction-repair]] 全て解決 ✅、新規破損リンク 0件。tier_integrity_check --check = ERROR 0 (既存 warn 2 / info 14 のみ、本編集と無関係) (3) stale なし — データ 07-16 当日 (Render API 一次ソース)。⚠️ ただし **1日 cadence gap (07-15)** を検出・記録
- ⚠️ 未解決（継続）: `API_AUTH_TOKEN` watchdog gap (agg-kelly gate が現行の稼働中セーフティネット) / sr_anti_hunt_bounce shadow data corruption / main の index.md DD 行 stale (乖離解消は別件、v2.3 は実 NAV(JPY) 基準へ移行予定)

## 2026-07-21 wiki-daily-update (scheduled task)
- ✅ APIフェッチ完了 (demo/stats date_from=2026-04-08, demo/learning, risk/dashboard, oanda/audit limit=30) — 全て Render 本番一次ソース
- ✅ Trade log 作成: `raw/trade-logs/2026-07-21.md`
- ⚠️ **cadence gap** — 前回 scheduled run は 2026-07-16 (Thu)。07-17 (Fri) / 07-20 (Mon) に run なし (FX weekend 07-18/07-19)。本日の delta は 07-17→07-21 span 累積だが **realized book は flat (0 closed fills)** のため book 観点では損失なし。cadence は本日再開
- **本日のスナップショット (is_shadow=false, vs 07-16)**: N=**563** (**FLAT — 0 closed fills**)。245W/284L/34BE / WR 43.5% / decided 46.3% / EV **-0.98** / PnL **-552.7pip** / Wilson 42.1(BF 39.3) / avg R 0.12 は**全て 07-16 と bit-for-bit 同一**。実現 book 移動ゼロ (07-08/07-14 と同型のフラット窓)。shadow_count 9,656→**9,932 (+276)** — shadow 側 firing は継続、live/closed book のみ静止
- **リスク**: 🔴🔴🔴 **DD=100.8%** (1008.0pip, eq=−$991.1 vs peak +$16.9) — **07-13 barrier 突破から held flat、NEW HIGH なし・deepening なし** (0 fills で book 不動)。realized ruin=0.0% は 0.2× lot cap のみによる。**MC tail は改善** (worst DD99 272.36→**200.24**、median max DD 219.75→**149.17**、median final eq 781.25→**852.25**) — 30d edge の window-roll 改善が forward 分布に波及。defensive 0.2× 維持
- **30d edge**: overall edge=**-29.6%** (🟢 eased +10.9pp vs 07-16 の -40.5%)。**ただし new-edge gain ではない** — closed fills 0 のまま 30d 窓が n 60→50 に roll (effective_date_from → 2026-06-21)、10件の悪い cohort (≈−9.53/trade) が窓外へ排出されたことによる。per-trade net は −3.64→**-2.46** に改善、absolute net −218.5→**-123.2**、Sharpe -0.562→**-0.399**。friction 4.18/trade、DSR 0.0/haircut 100%/n_trials 11。**by-instrument (n=50, 全4負)**: **GBP_USD #1 abs drag -43.5 (mean -2.72, n=16)** / USD_JPY -36.2 (mean -1.91, n=19) / EUR_JPY -28.7 (mean -2.87, n=10) / EUR_USD -14.8 (mean -2.96, n=5 = worst mean)。per-strategy Kelly は bb_rsi_reversion のみ +edge (+0.158/half-Kelly 0.134/n=11/WR 72.7%)、他は全て 0.0/insufficient
- OANDA audit (07-20 16:31→07-21 04:02 UTC): **0 LIVE / 30 shadow_tracking skipped / 0 blocked / 0 false-sent** (is_shadow None、bridge_status=skipped 全行、filled 行なし、偽sent なし=07-02 contract fix 持続)。**今窓は agg-kelly gate に到達した signal なし** — 全て upstream で shadow_tracking skip。gate は稼働中セーフティネットのまま。firing: squeeze_release_momentum(5) / xs_momentum(4) / lin_reg_channel(4) / wick_imbalance_reversion(3) / dt_sr_channel_reversal(2) / streak_reversal(2) / dt_bb_rsi_mr(2) / engulfing_bb(2) + singles。instruments: GBP_USD(11) 最活性 / EUR_USD(9) / USD_JPY(5) / GBP_JPY(3) / EUR_JPY(1) / AUD_JPY(1)。audit table total=**12,799** 行 (+303 over the 5-day span)
- Learning: **新規 adjustment なし** (latest 依然 id=92, 2026-07-06 = sr_channel_reversal scalp blacklist 再確認 WR25%/EV-0.98/n190)。current_params 不変 (confidence_threshold 30 / max_open_trades 8 / max_consecutive_losses 3 / learn_every_n 10 / entry_type_blacklist 空)。daytrade by_conf 全負 (high -0.19/n31, mid -4.07/n39, low -2.18/n23)、by_regime 全負 (RANGE -1.59/TREND_BEAR -4.50/TREND_BULL -2.17)
- Tier 変更なし → portfolio auto-sync / strategy pages 編集不要 (0 fills のフラット窓、閾値クロス無し)
- **Lint**: (1) 現状態の数値は index.md 全 state 箇所 (header/System State/Ruin/Aggregate Kelly/last-updated) で 100.8%(held flat)/563(flat)/-552.7/-29.6%/0-fills-0-blocked 一致 ✅ (残る -40.5%/-218.5/272.36 等の参照は全て "vs 07-16's" 比較文 + 07-16/07-14/07-13 履歴行 + trade-log link=履歴として正) (2) [[2026-07-21]] → raw/trade-logs/2026-07-21.md 解決 ✅、[[monthly-target-rederivation-2026-07-10]]/[[shortest-path-decision-memo-2026-07-10]] 全て解決 ✅、新規破損リンク 0件 (3) stale なし — データ 07-21 当日 (Render API 一次ソース)。⚠️ ただし **cadence gap (07-17/07-20)** を検出・記録 (realized book flat のため book 損失なし)
- ⚠️ 未解決（継続）: `API_AUTH_TOKEN` watchdog gap (agg-kelly gate が現行の稼働中セーフティネット) / sr_anti_hunt_bounce shadow data corruption / main の index.md DD 行 stale (乖離解消は別件、v2.3 は実 NAV(JPY) 基準へ移行予定)
## 2026-07-06 (T7 クローズ + T8 forensic #2: engine 再構築による live dedup 無効の発見)
- **T7 CLOSED**: carry dip 0-fire は ceiling 159.50 のレジーム前提崩壊による dormant-by-design (バグ非ず)。QUALBAR print telemetry 本番稼働。[[zero-fire-diagnosis-carrydip-vix-2026-07-02]] §6
- **T8 forensic #2 = 共通挙動**: hull は guard 実装済みだが `compute_daytrade_signal`/`compute_hourly_signal` が **poll 毎に Engine を再構築**するため全戦略の instance-state dedup/cooldown が live で無効。live の dedup 層は recent_emit のみ。order 層 per-bar dedup タスクを queue 投入、ゲート④ order 層補正 + 再 LOCK は user R1 決裁待ち。[[t8-week1-gate-breach-2026-07-06]]
## 2026-07-18 wiki-lint (E15+E7 pre-reg 起案セッション)

- **Lint (本コミット変更ファイル限定)**: (1) [[e15-e7-event-modality-prereg-2026-07-18]] / changelog / session log / pipeline 状態表 / queue task の [[wikilink]] 全解決 ✅ (2) prereg-trigger-registry.json valid JSON、active 13 triggers (新規 2: e15-e7-event-prereg-phase{0,1}-verdict) ✅ (3) tier_integrity_check --check pass ✅
- ⚠️ **`sync_kb_index.py --check` FAIL — index.md KB_PORTFOLIO ブロックが demo_trader.py strategy sets と drift** (最終 auto-sync 2026-07-15、本セッションの変更とは無関係の既存事象)。PAIR_PROMOTED/SHADOW の行数が大幅相違。scope 規律により本 PR に混載せず、別タスク chip (`Fix stale KB index portfolio sync`) として起票済み — `sync_kb_index.py --write` + `tier_integrity_check.py --write` の単独コミットで解消すること
- ℹ 既知 (継続): app.py の legacy dead inline `strong_sr_breakout` / `tokyo_bb` (30d+ 発火なし、削除候補)

## 2026-07-29 wiki-lint (massive-gap-backfill 変更分)
- ⚠️ [[holiday-calendar-verification-2026-07-29]] は意図的な前方参照 — 発見元 doc は branch `claude/hopeful-kapitsa-417e40` (未マージ) 上。同 branch land 後に解消。他のリンク・参照ファイルは全て解決済み

## 2026-07-31 EA Landscape Sweep (user 指示「勝てている EA を全力で大規模調査 → エッジ探索」、rule:R3)
- **方法**: 31-agent workflow — 13 ソース並列 Web スイープ (MQL5/Myfxbook/FX Blue/Darwinex/海外フォーラム/Reddit-HN/クオンツ blog/国内 GogoJungle/学術 2020-26/prop firm/GitHub OSS/SMC-ICT/生存率研究) → 113 findings → 上位 18 を敵対的検証 (banned 19 + LOCKED 4 隣接判定 / 生存バイアス・マーチン偽装 / OANDA headroom 10×)。詳細: [[ea-landscape-sweep-2026-07-31]] / raw: `raw/analysis/ea-landscape-sweep-2026-07-31.json`
- **構造的結論**: multi-year verified の勝者は 2 アーキタイプに収斂 — (a) ナイトスキャルパー MR = 機構実在だがブローカーのスプレッド政策で回収済み (cohort 2022-23 フラット化)、OANDA 移植構造的不能 (gotobi #13 同型 + デスゾーン自己矛盾)、(b) コモディティ三角クロス (AUD_NZD/AUD_CAD/NZD_CAD) = グリッド表層は RISK-ILLUSION、per-position 核は内部未検証 (session-mr-cross-wave1 BLOCKED_DATA を supersede)
- **台帳追記**: **#21 commodity_cross_range_mr (queued、G0=OANDA 3 クロス RT 実測が必須事前ゲート)** / **#22 equity_curve_shadow_gating (queued、内部 shadow ログのみで counterfactual 検証可の低 prior・低コスト枠)** (※#20 は並行セッションの composite_weak_signal_portfolio が先取 → renumber 済み)。THA (Darwinex 首位) は LOCKED E7 と同一 estimand → E7 prior 加点として記録のみ
- **副産物**: 生存率ベースレート割引関数 (マーケ BT ≈0-5% / verified 3y+ 非負スキュー ×0.3-0.5 上限 / WR>90% は破産確率評価) を KB 化。weekend gap persistent の外部独立確認 (Robot Wealth) = live wg×3 と整合。トレンドフォロー/news/gold/SMC に 3y+ verified 代表個体ゼロ
- **live/shadow 変更なし**。次アクション = #21 G0 摩擦実測 (シグナル計算ゼロ・pre-reg スロット非消費) + #22 explore pre-reg 起案

## 2026-08-03 wave-6 着手 (#21 G0 実測 + #22 forward pre-reg LOCK、rule:R3)
- **#21 commodity_cross_range_mr G0 = ✅ PASS 3/3** — [[commodity-cross-g0-rt-freeze-2026-08-03]] (🔒 凍結コミット 981ae119 後に測定)。stressed_RT_primary: AUD_NZD 3.80p / AUD_CAD 3.70p / NZD_CAD 3.90p (全て ≤5.0p 閾値)。60 営業日 M5 BA candles、アンカー妥当性 OK。**副次発見 = 21:00 UTC 帯は spread 毒窓 (p75 12-18p) だが 23:00 UTC 以降 2.7-2.9p に正常化 → explore pre-reg は執行 23:00 UTC 凍結必須**。次 = explore pre-reg 起案。`reports/commodity-cross-rt-g0-2026-08-03.md`
- **#22 equity_curve_shadow_gating = forward pre-reg 🔒 LOCKED (v2)** — [[equity-curve-shadow-gating-explore-prereg-2026-08-03]]。遡及 explore 案 (v1) は敵対的検証 3 レンズ (統計/lookahead・衛生/交絡) で **KILL 3 件**: 一度きりの構造ブレークで偽陽性 100% (合成データ実証) + 週層化は真の検出力も殺す = 遡及窓で識別不能 + retired セルの outcome-conditioned truncation + Fidelity Cutoff 前汚染。→ **#4 MoF/#10 E12 前例の forward 化で構造解決**。first look 2026-11-06 (registry `ecg-forward-first-look`)、primary = active 4 セル × K{5,10,20} (m=12)、epoch 層化 permutation、遡及窓は未測定保存 (burn なし)
- **横断教訓**: 敵対的検証は「ハーネスの関数を import して合成データで偽陽性率を実測する」段階まで踏むと、文言レビューでは見えない識別不能性を検出できる (今回の KILL は全てこの型)
- 環境注記: ローカル OANDA token は生存確認 (candles BA HTTP 200) — 07-14 の「失効」記録は book エンドポイント 401 の誤帰属 ([[e1-positioning-ingest-2026-07-14]] §8 と整合)
- **#22 race 追記 (並行セッション sharp-pike)**: 同日独立に在庫調査 (shadow book 全長 4.04mo、§4.2 遡及 eligibility 充足 0 セル) → 別設計 forward pre-reg + 敵対的検証まで進めたが、push 前確認で v2 先着を検出し**競合 LOCK を撤回** (first-to-main)。独立 2 系統が「遡及不成立 → forward 化」に収束 = 判定の corroboration。cross-audit (v2 vs §4.2 凍結 form の差分 on-record、day-block null の K1 脆弱性 = 敗着分析、P-10 整合 attestation) = `raw/analysis/ec-gating-race-cross-audit-2026-08-03.md`、228 セル census = `raw/analysis/ec-gating-cell-inventory-2026-08-03.json`

## 2026-08-07 `SL_HIT` ラベル衝突の解決 (rule:R3、autopilot)
- **08-05 daily 提起 → 2日繰越だった「`SL_HIT` の 46.2% が正 PnL」を決着**: 汚染 (labeller 欠陥) ではなく**ラベル衝突**。`close_reason="SL_HIT"` は「**現在の** SL に触れた」の意味しかなく、BE-lock/トレーリング/Profit Extender が SL を利益側へ動かした後の**利確 exit** も同ラベル。**データは正しい / 名前と下流の解釈が誤っていた**
- **本番実測 N=3308**: SL 利益側 1894 本 → **97.6% が正 PnL** (中央値 +2.00p、MFE 中央値 5.70p) / SL リスク側 1414 本 → **99.6% が負** (中央値 −6.95p、MFE 0.00p)。**誤分類 1.5%** = SL 位置は事実上完全な判別子。`outcome` 内訳 WIN **1792 (54.2%)** — 08-05 の 46.2% (N=106) は過小評価
- 🔴 **実害 = 防御 2 本が勝ちで発火**: cascade cooldown (同ペア**全戦略**を 45–600s ブロック) と Fast-SL 適応防御 (次 SL を ATR×0.3 拡大) がともに `_sl_hit_history` を「ストップ狩りに遭った」前提で消費。**発火の 54.2% が誤発火** (Fast-SL 側は 315 件中 180 = **57.1%**)、誤発火は USD_JPY 494 / GBP_USD 444 / EUR_USD 306 と主力ペア集中。4原則 #1「攻める」/ #4 に反していた
- **Rule 3 の根拠**: 直前の隣接ブロック (`if outcome != "WIN":` → `_last_exit` / `_total_losses_window`) が「SL 後の再エントリー防止」という**同一目的で既に WIN を除外**済み。同一意図の 2 ブロックが非対称 = 設計の内部矛盾ゆえ 365日BT 不要
- **修正**: `demo_trader` 履歴記録に `outcome != "WIN"` (BE 75 本は逆行スイープの証拠として意図的に残す) / `learning_engine.sl_losses` / `daily_review.sl_hits` を `outcome=="LOSS"` 化 (生カウントの SLヒット率 82.7% → 真値 **36.0%**、勝ちの多い book に「SL幅拡大検討」を焚いていた) / 回帰 pin 4 tests
- **やらなかったこと**: `close_reason` の改名は既存 3308 行と全 BT ハーネスの estimand を壊すため見送り (ラベル据え置き・消費者側を正す)。shadow 行混入の是非 (誤発火 1792 件中 1786 が shadow) は継続課題
- **横断教訓**: 「同一目的の隣接ブロックで扱いが非対称」は構造バグの強いシグナル。`_is_xau_inst` (3.5ヶ月 live kill)・DTE mixed gate no-op に続く 3 例目
- **次の作業候補**: cascade_cd / Fast-SL の block 実数は audit に出ない = 本修正の効果 (誤発火 −54%) を実測できない。**block カウンタの輸出**が要る — 08-06 daily の「シグナル供給 5 session 連続半減」の候補要因でもある
- 詳細: [[sl-hit-label-collision-2026-08-07]]

## 2026-08-20 wiki-daily-update (24日ぶりのスナップショット — gap 中に book が動いていた)

- ⚠️⚠️ **cadence gap 07-28 → 08-19 (24日)** = 本 log 最長。しかも直近の gap と違い **realized book は flat ではなかった**: N 563→**573 (+10 closed fills, 4W/6L)**、PnL −552.7→**−660.3 (−107.6p)**、EV −0.98→**−1.15**。07-16 から続いた 5 スナップショット連続 flat は解消。`wiki/sessions/` と session 付き trade-log は毎日走っていた — 落ちていたのは wiki-daily スナップショットだけ
- 🔴 **窓の損失は 1 セルが全部**: `price_shock_rev_aud_jpy_h1_long` **n=2 / −122.6p / mean −61.3** (12.3y BT は N=426 / WR 63.8% / PF 2.54 / **EV +32.25p**)。この 2 本を除くと 30d book は **+15.0p (n=8)**。VaR95 13.58→**81.31**、CVaR95 19.0→**123.2**、DD は **+201.1p の新高値 (1209.1p)**。**demote 未執行** — LOCK 基準 (N=15 で Wilson_lo<0.40 / watchdog N≥10) いずれも未達だが「2週連続 EV<0 → 緊急 review」は該当。**N=10 到達まで待つと −600p 規模の追加出血を許容する**ため、閾値待ちでなく user 決裁として起票
- 🟢 **live fill 4本、全て `usdjpy_carry_dip_accumulator` USD_JPY BUY 1000u** — oanda #677402 (08-14) / #677910 (08-16) / #677917 (08-17) / #677924 (08-19)、全て real trade id 付き = **false-sent 0** (07-02 accept/reject 契約は維持)。**07-02 の zero-fire dormancy は外生的に解消** — USD_JPY が ~159.47-159.62 まで戻り `close < 159.50` ゲートが再武装。当時「ceiling を動かさず hold」と決めたのが結果的に正解。累計 live N=7 / WR 42.9% / **+45.1p** だが DSR は非有意 (Sharpe 0.2189 < 閾値 0.368)、pre-reg の N≥30 に対し **7/30** で判断保留
- ⚠️ **数値の見え方が 2 箇所変わった (実体の動きではない)**: (1) risk API の `dd_pct` が **JPY NAV 台帳基準に切替** (`jpy_ledger.active`、base ¥359,109 / DD ¥34,826.89 = **9.7%**) — v2.3「実 NAV(JPY) 基準へ移行」の着地。**100.8% → 9.7% は単位変更であって回復ではない**、pip 基準の継続値は **120.9% (1209.1p)** (2) MC `initial_capital` が **1000 → 5801.44** にリベース — worst DD99 170.0→1037.72 等は scale artifact、init 比で正規化すると tail 17.0%→**17.9%** / median max DD 12.1%→**11.45%** でほぼ不変
- **edge は本物の悪化**: overall edge (risk dash) −25.69%→**−32.01% (−6.32pp)**。直近数窓の「window-roll による見かけの easing」とは別物 — risk-window WR 57.89%→40.0%、per-trade net −1.99→**−10.76 (5.4倍)**。agg-kelly gate は**空回りしていない**: 本窓 **26 block** (−0.349…−0.371<0) + 4 fill 通過
- ⚠️ **audit limit=30 なら「live fill 0」と誤報告していた** (30件 ≈ 6時間分で 4 fill 全部を取り逃す)。limit=500 で 08-13 00:17 → 08-20 06:11 UTC をカバー。`feedback_audit_limit30_hides_live_fills` の再実証
- 🆕 **learner adj id=93 (08-19 14:25)** = id=92 (07-06) 以来の新規。ただし **4回目のバイト同一 re-affirm** (`sr_channel_reversal` WR25.0%/EV−0.98/n=190、06-30 から不変) で `current_params.entry_type_blacklist` は依然 **`[]`** → **blacklist 書き込みが no-op**、だから同じ調整が永久に再発火する。n=190 が 7 週間凍結 = 当該セルの蓄積も止まっている
- 🔴 **新規 anomaly: `ob_retest` が `units: 0` で 5 発火** (08-20 GBP_JPY BUY、全て shadow なので実害なし)。同時に `tier_integrity_check` は「strategy file なし」かつ「legacy dead inline、30日以上発火なし」と報告 — 今日の audit と真っ向から矛盾 (checker はローカル状態を見ており Render API を見ていない)
- **Tier 変更なし** (promote/demote 閾値いずれも未達)。strategy page 更新 3件: [[usdjpy_carry_dip_accumulator]] (SHADOW/pending → LIVE 稼働中 + live 実績表 + SL 契約不一致の格上げ) / [[price-shock-rev-aud-jpy-h1-long]] (BT vs live 衝突表 + 決裁論点) / [[vix-carry-unwind]] (live perf を N=2 の 04-20 値 → N=26 の実測に更新、demote は意図通り機能中)
- **Lint**: (1) 数値整合 — index.md の header / Defensive mode / Ruin / Aggregate Kelly / Portfolio warnings / last-updated / Session History を全て本 pull (N=573 / −660.3 / 1209.1p / −32.01% / 4 fills / 26 blocks) に統一 ✅。履歴行 (07-27/07-08/07-07…) は as-of 値のまま保持 (2) `tier_integrity_check --check` **PASS** (warning 2 = hull_donchian_fade QUICK_HARVEST_EXEMPT / ob_retest ページ欠落) (3) `sync_kb_index --check` は exit 1 だったが **差分は日付スタンプのみ** (2026-08-19 → 08-20) — 07-18 に起票された portfolio drift は解消済み。`--write` で解消 ✅ (4) 破損 wikilink **14件、全て既存・本 run で新規 0件** (index.md 7件 / strategies/ 7件)。うち 5件 (`ob-retest` / `ma-regime-switch` / `ma-trend-perfect` / `mqe-gbpusd-fix` / `vsg-jpy-reversal`) は `sync_kb_index.py` が自動生成する portfolio ブロック由来 = 実在しない strategy page を指す構造的欠落。残り 7件は strategies/ の `research/index` ハブ未作成 (6箇所) + stale 参照 1件 (5) データ鮮度は当日 (Render API 一次ソース)、ただし **wiki-daily 系列自体が 24日 stale だった**のが本 run 最大の所見
- ⚠️ 未解決（継続）: `API_AUTH_TOKEN` watchdog gap (agg-kelly gate が実働セーフティネット、本窓 26 block) / `sr_anti_hunt_bounce` shadow data corruption / **learner blacklist no-op** / **carry-dip の宣言 150p SL vs 実測 18.8p 置換** (live 7 本が閉じた今、唯一の正セルのテール挙動を実際に支配している) / `ob_retest` zero-unit 発火

## 2026-08-23 wiki-daily-update (1ヶ月ぶりの正の窓 — ただし幅は1セル、DD は新高値更新)

- 🟢 **07-16 以来はじめて realized book が改善した窓**。N 573→**578 (+5 closed fills, 2W/2L/1BE)**、PnL −660.3→**−631.2 (+29.1p)**、EV −1.15→**−1.09**、WR 43.4%/decided 46.2%、Wilson 42.1 / BF 39.3、avg R 0.12、shadow_count 12,241→**12,386 (+145)**。cadence gap は 3日だが **08-22 (土)・08-23 (日) は市場休場**、engine 最終稼働は **2026-08-21 18:46 UTC** = **stale ではない、週末どおりの形**
- 🔴 **それでも DD は新高値を更新**: **1218.9p = 121.9%** (legacy $1000 pip 基準、+9.8p、eq −$1202.0 / peak +$16.9 flat)。`dd_pct` フィールドは 0.0976 = **9.76%** (JPY NAV 台帳、base ¥359,109 / peak ¥359,288.47 / current ¥324,249.50 / DD ¥35,038.97) — 基準は 08-20 から不変、pip 系列との**単位差**であることに注意
- ⚠️⚠️ **risk dashboard の「改善」は全て分母の算術**: 30d 窓が **n=10→15** (`effective_date_from` 2026-07-24) になり、同じ AUD_JPY 2本 (−122.6) が 5本多い母数で平均された。これだけで overall edge −32.01→**−26.46% (+5.55pp)**、per-trade net −10.76→**−5.23**、Sharpe −0.2259→**−0.1301**、MC tail 17.9%→**11.29%**、median max DD 11.45%→**6.09%** が出る。**risk-window WR は 40.0% で不変、Kelly は 0.0 のまま、DSR は 0.0/haircut 100% のまま、DD は新高値**。07-21 / 07-27 と同型の window-roll であり、エッジの回復ではない
- 🟢 **live fill 5本、sent 5 / filled 5 / false-sent 0** (07-02 accept/reject 契約は維持):
  - **`usdjpy_carry_dip_accumulator`** USD_JPY BUY 1000u × 2 — oanda **#677931** (08-20 07:03 UTC) / **#681149** (08-20 10:19)、**2本とも勝ち** → 累計 N 7→**9**、WR 42.9→**55.6%**、+45.1→**+84.0p**、EV/trade **+9.33**。DSR は 0.3591→0.424 と閾値に寄ったが **z=−0.192 で依然として非有意** (Sharpe 0.3363 < 閾値 0.4059)。pre-reg N≥30 に対し **9/30 で判断保留**
  - 🆕🔴 **`price_shock_rev_eur_gbp_h1_long`** EUR_GBP BUY 1000u × 3 — **#681143** (08-20 07:41) / **#700421** (08-20 12:59) / **#709529** (08-21 11:39)、**live デビュー 0勝3敗 −9.8p (mean −3.27)**。12.3y MASSIVE BT は N=239 / WR 72.8% / PF 14.75 / **EV +55.81p**
  - ⇒ **carry-dip を除くと本窓は −9.8p (n=3)**。book 全体の +29.1p は carry-dip の 2本が単独で作った
- 🔴 **Price-Shock family の2セル目が live で BT 符号を反転**: AUD_JPY sibling (n=2 / −122.6 / mean −61.3 / BT EV +32.25) と EUR_GBP (n=3 / −9.8 / BT EV +55.81) が同方向に外れている。N=3 は単体では何も否定しない (WR 72.8% 下でも 0/3 は p≈0.02 で起こる) が、**family 単位の決裁論点として起票** — セルごとに閾値待ちを繰り返す形は 08-20 で既に「N=10 まで待つと追加出血を許容する」と記録済み。自動発火は両セルとも未達 (EUR_GBP: 棄却 N=15 / watchdog N≥10 に対し N=3)
- 🔴 **08-20 の `ob_retest` zero-unit anomaly は誤って狭く記録していた — 実態はシステム全体**: 800行 pull のうち **184行 (23%) が `units: 0`**、**16戦略 / 7通貨ペア / 全営業日**に分布。100%: `vdr_jpy` (4/4) / `rsk_gbpjpy_reversion` (8/8) / `ema200_trend_reversal` (4/4) / `sweep_reversion_eurgbp_late` (2/2) / `ob_retest` (12/12) / `turtle_soup` (1/1)。高率: `sr_anti_hunt_bounce` **83% (57/69)** / `sr_weighted_bounce` 69% / `sr_weighted_break` 67% / `sr_break_retest` **53% (34/64)** / `wick_imbalance_reversion` 39% (36/92)。通貨ペアは **JPY クロス偏り** — GBP_JPY **70% (49/70)** / EUR_JPY 45% / AUD_JPY 22% / USD_JPY 18% / EUR_USD・EUR_GBP 6% / NZD_USD・AUD_USD 0%。**184行すべて `bridge_status=skipped` (shadow_tracking) = live エクスポージャゼロ**。ただし shadow-first では shadow が estimator であり、SR family の支配は既知の `sr_anti_hunt_bounce` メタデータ破損と重なる。**本 run では根因を特定していない** — コード実測でなく分布のみを記録 (`feedback_label_empirical_audit` の趣旨に沿い、演繹で断定しない)
- **Learning API**: 新規 adjustment **なし** (最新は id=93 / 08-19 のまま)。`current_params.entry_type_blacklist` は依然 **`[]`** = **no-op 未解消**、同じ `sr_channel_reversal` 調整が永久に再発火する構図が続く。daytrade EV **−2.60** (n=94、全 conf 帯・全 regime で負)、scalp **−0.15** (n=388、low-conf +0.48 のみ正)、swing は `ready=false`。⚠️ **本窓の live fill 5本は全て `daytrade_1h` / `daytrade_1h_eurgbp` 経由** — 自らの learner 分析が全帯域で負の mode
- **Tier 変更なし**。strategy page 更新 2件: [[usdjpy_carry_dip_accumulator]] (live 実績表を N=7/+45.1 → **N=9/+84.0** に更新、DSR 0.424 も依然非有意と明記、「book の改善はこの2本が単独で作った」を追記) / [[price-shock-rev-eur-gbp-h1-long]] (**live 実績セクションを新設** — 0W/3L、fill 3件の trade id、BT との乖離表、LOCK 基準に対する現在地、および「強制 Shadow track」記述が 08-20 以降 stale である旨)
- **Lint**: (1) 数値整合 — index.md の Defensive mode / Ruin / Aggregate Kelly / Portfolio warnings / last-updated / Session History top を全て本 pull (N=578 / −631.2 / 1218.9p / −26.46% / 5 fills / 13 blocks) に統一 ✅。履歴行は as-of 値のまま保持 (2) `tier_integrity_check --check` **PASS** (warning 2 = `hull_donchian_fade` QUICK_HARVEST_EXEMPT / `ob_retest` ページ欠落 — 後者の「30日以上発火なし」は本日 audit の 12行と**再び矛盾**、checker がローカル状態のみを見る既知の構造) (3) `sync_kb_index --check` は exit 1 だが **差分は日付スタンプのみ** (2026-08-20 → 08-23)、`--write` で解消 ✅ (4) 破損 wikilink: **index.md 7件** (08-20 と同一集合 — 自動生成 portfolio ブロック由来 5件 + trade-log 参照 2件) / **strategies/ 1件** / KB 全体 **76件**。⚠️ 08-20 の「14件」との差は **checker の方法差**であって新規破損ではない (本 run は path 相対解決 + MEMORY 参照除外を行い、`research/index` 系の偽陽性を排除する一方で全ディレクトリを走査)。**本 run の新規破損 0件**、追加した [[2026-08-23]] / [[price-shock-rev-aud-jpy-h1-long]] 等は全て解決 ✅ (5) 鮮度 = 当日 pull、engine 最終稼働 08-21 18:46 UTC (週末休場)、**stale なし**
- ⚠️ **audit limit=30 は今回も誤報告になっていた** — `limit=800` (2026-08-12 05:46 → 08-21 18:46 UTC、total 15,756) に対し 30行では live fill 5本を全て取り逃す。`feedback_audit_limit30_hides_live_fills` **3 run 連続の再実証**。task spec の limit=30 は意図的に上書きした
- ⚠️ 未解決（継続）: `API_AUTH_TOKEN` watchdog gap / `sr_anti_hunt_bounce` shadow data corruption (zero-unit 所見と関連の可能性) / **learner blacklist no-op** / 🔴 **carry-dip の宣言 150p SL vs 実測 18.8p 置換 — live 9本が閉じ、book 唯一の正セルである今、最優先の未決裁項目** / zero-unit 発火 (`ob_retest` 限定から system-wide に再分類) / **Price-Shock family (AUD_JPY + EUR_GBP) の demote 決裁**

## 2026-08-28 wiki-daily-update (08-26 のフリーズ解消 — 105.5h の有界な障害と確定、hedge_block が shadow→live を抑制していることを code 検証)

- 🟢 **08-26 log の中心的 🔴「realized book と audit table が bit-for-bit フリーズ」は自然解消**。N 578→**579 (+1 closed fill)**、PnL −631.2→**−611.1 (+20.1p)**、`shadow_count` 12,386→**12,558 (+172)**、`oanda_audit.total` 15,756→**15,950 (+194)**、最終 audit 行は **2026-08-28 04:31 UTC** (pull 時点で 29分前)。
- 🟢🔴 **障害は有界だった — 500行 pull の gap scan で 6h 超の不連続は「ちょうど1つ」**: **2026-08-21T18:46:24Z → 2026-08-26T04:16:16Z = 105.5h**。内訳は Sat 08-22 / Sun 08-23 (市場クローズ、想定内) **＋ Mon 08-24・Tue 08-25 の通常営業日2日が全種別ゼロ行**。08-26 04:16Z に**無介入で復旧**し以後正常 (08-26/08-27/08-28 = 67/101/26行)。
  - ⚠️ **原因は未特定**。`main_loop_restarts` は 08-26 と同じ **1** のままで、プロセス再起動では説明できない。特定には当該窓の Render ログ読みが要るが、本 run では実施していない。**shadow 観測2営業日分は estimator から恒久的に失われた** — shadow-first 下での実コストは flat な realized book ではなくこちら。
- 🔴 **08-26 log の訂正: `r2_shadow_demoted_cell` は shadow book フリーズの機序では**なかった**。** 同 gate は今回も同等規模で発火 (**4,135**、23.3%) している一方で `shadow_count` は **+172**、`shadow_tracking` 行も 186本書かれている。フル稼働中の gate と健全な shadow book は両立しており、フリーズ原因たり得ない。障害は **pipeline 全体**であって gate 選択的ではなかった。
- 🔴 **新規: `hedge_block` が最大の blocker (6,265 = 17,718 の 35.4%)、かつ *shadow* ポジションを *live* 候補に対してカウントしている。**`feedback_label_empirical_audit` に従い aggregate からの演繹ではなく **code 実測**で確認:
  - `modules/demo_trader.py:4915-4928` が **`_mode_inst_live + _mode_inst_shadow`** を走査し layer を問わず block。`_mode_inst_shadow` (L4877) は `is_shadow == True` を選択。
  - in-line コメントが意図的設計と明記: `# 2026-04-30 (rule:R2 / H2) … ヘッジは Live/Shadow 問わず常に block する。`
  - live 状態も一致: `/api/demo/status` の `open_trades` = **6行すべて `is_shadow: 1`** (`sr_anti_hunt_bounce` EUR_JPY ×4 / `dt_sr_channel_reversal` GBP_USD / `doji_breakout` EUR_USD)、一方 OANDA heartbeat は `open_trade_count: 0` / `margin_used: 0`。
  - ⇒ **08-27 pre-Tokyo 戦略レポートが最優先に挙げた「OANDA↔台帳 desync バグ」仮説は誤り。** desync は存在しない。broker カウントは broker ポジションのみを数え、gate は shadow book も見る設計。
  - **バグではなく「決裁事項」**: R2/H2 の論拠 (同時刻の逆方向 sample が score-max selection を通じて戦略間ランキングを壊す) は実在の懸念。副作用は **shadow ポジションが live 候補を抑制する**ことで、shadow-first 下では逆であり、いま系内で最大の抑制源。**user 決裁に回す。コード未変更。**
- ⚠️ **block counter は 2 pull 間で比較不能** — 総 tick が **62,472 → 57,029** と減少する一方 `main_loop_restarts` は 1 のままで、counter 窓が roll/reset した。よって **block-count の delta は本 run では一切算出していない**。窓内 share のみ有効: `hedge_block` 6,265 (35.4%) / `r2_shadow_demoted_cell` 4,135 (23.3%) / `order_bar_dedup` 3,637 (20.5%) / `direction_filter` 2,624 (14.8%) / `score_gate` 500 / `gbp_asia_flash_crash` 180。
  - 🔴 **`rnb_usdjpy` は 2,624 blocks / 2,622 ticks = ratio 1.0008** — block が tick を僅かに**上回った**。`direction_filter` が selective でなく無条件棄却である **2回連続の確認**（既知の `compute_rnb_signal` WAIT-path `entry: 0` バグと整合）。**code 読みは依然未実施 — 08-26 から変わらず最優先の follow-up。**
- 🟢 **live fill 1本、sent 1 / filled 1 / false-sent 0** (07-02 accept/reject 契約維持、累計 9 fill / 9 実 id):
  - **`price_shock_rev_aud_jpy_h1_long`** AUD_JPY 1000u — oanda **#709537** (08-26 14:59:26 UTC、`filled` 行の entry_type は MODE `daytrade_1h_audjpy` = `reference_oanda_audit_twin_meaning`)、**勝ち +20.1p** → セル N 2→**3**、WR 50.0→**66.7%**、−122.6→**−102.5**。
  - 🔴 **ただしセルは 2勝1敗 N=3 で累計 −102.5p のまま** — 勝ち2本計 ≈+40 に対し負け1本 ≈−143 の極端な payoff 非対称。Wilson_lo 20.8 / BF_lo 9.9、12.3y MASSIVE BT は WR 63.8% / PF 2.54 / **EV +32.25p**。**N=3 の1勝で Price-Shock family の問題は決着しない** — demote 決裁は open のまま。
  - **agg-kelly block 7本** (−0.336 ×4 / −0.315 ×3)。新規スライス 195行の bridge 内訳: `shadow_tracking` skip 186 / blocked 7 / sent 1 / filled 1 ⇒ **live rate 0.5%、本 log 中で最低**。
- ⚠️⚠️ **risk dashboard の「改善」は今回も 1本の trade ＋ 窓 roll の算術** (08-23 と同型): 30d 窓の `effective_date_from` が 07-26T20:48→**07-29T05:00:42**、n 15→**16** に動き、そこに +20.1 の1本が入っただけで edge −26.46→**−20.06% (+6.40pp)**、Sharpe −0.1301→**−0.0927**、MC tail 11.29→**9.91%**、median max DD 6.09→**4.66%**、per-trade net −5.23→**−3.65** が出る。**risk-window WR 40.0→43.75%、Kelly は依然 0.0、DSR も依然 0.0 / haircut 100%。** edge 回復ではなく窓算術として読むこと。
  - 🟢 **DD 1198.8p = 119.9%** (legacy $1000 pip 基準) — **−20.1p、本系列で初めての低下** (eq −$1181.9 / peak +$16.9 flat)。`dd_pct` フィールドは 0.097 = 9.7% (JPY NAV 基準)。
  - ⚠️ `attribution` は今回も **gross = net = −58.4 なのに friction = 71.3** を返す。friction は算出されているが gross から差し引かれていない。既存事象・未解消・本 run では未診断。
- **継続項目の状況**: JPY NAV 台帳は broker 比 **¥46,105.02** 上振れ (NAV ¥278,345.48 vs 台帳 ¥324,450.50) — 実質不変、sizing は 0.20× tier 飽和のため影響なし、報告値は broker 実測 DD を過小表示のまま / 🔴 **`/api/oanda/equity` は 18日 stale で悪化** (最終点は依然 2026-08-10 07:20Z、`count` 928、その間に live fill 9本が close 済) / ✅ **clock skew は再現せず** — heartbeat 05:00:33Z vs runner 05:00:51Z (**18秒**)、08-26 の ~5h40m 所見は今日は成立しない / zero-unit emission **80/500行 (16%)**、全て `shadow_tracking` = live exposure ゼロ、未診断。
- **Learning API**: 新規 adjustment **なし** — 最新は id=93 (2026-08-19 14:25) のままで **4スナップショット連続**。`entry_type_blacklist` は依然 **`[]`** = no-op 未解消 (06-30 以来)。daytrade EV **−2.60** (n=94、全 conf 帯が負)、scalp **−0.15** (n=388)、swing `ready=false` — **すべて 08-26 と bit-identical**。
- **Tier 変更なし** — N=3 の観測1本は promote/demote の根拠にならない。strategy page 更新なし (44戦略中 1セルのみ変動、他は 08-26 と byte-identical)。
- **Lint**: (1) 数値整合 — index.md の Defensive mode / Ruin / Aggregate Kelly / Portfolio warnings / last-updated / Session History top を本 pull (N=579 / −611.1 / DD 1198.8p / edge −20.06% / shadow 12,558 / audit 15,950 / live fill 1) に整合済 ✅、履歴行は as-of 値のまま。(2) `tier_integrity_check --check` **PASS** (exit 0、warning 2件はいずれも既存: `hull_donchian_fade` QUICK_HARVEST_EXEMPT が ELITE/PAIR_PROMOTED 外、`ob_retest` の strategy file 不在)。⚠️ 14本の「legacy dead inline, no production firing in 30+ days」INFO に依然 `ihs_neckbreak` が含まれるが、本日の pull に live block counter がある (`daytrade_eur:unknown_type:ihs_neckbreak` = 1) — checker は Render API ではなくローカル state を読む。**4回連続の同一矛盾報告**（ただし 08-26 より範囲は縮小、`ob_retest` は本窓では未発火）。(3) `sync_kb_index --check` → exit 1、**差分は日付スタンプのみ** (2026-08-26 → 2026-08-28)、`--write` で解消 ✅。(4) broken wikilink (path-aware resolver): `wiki/index.md` **7** = 08-23/08-26 と同一集合 (自動生成の portfolio-block ref 5件 `mqe-gbpusd-fix` / `vsg-jpy-reversal` / `ma-regime-switch` / `ma-trend-perfect` / `ob-retest` ＋ trade-log ref `2026-04-29` / `2026-04-27`)、`wiki/strategies/` は非 MEMORY **1** (`xs-momentum-rsi-tv-phase2-2026-05-13`)、KB 全体 **76** のうち 29 は KB 外で解決する MEMORY 形式 `project_*`/`feedback_*`/`reference_*` ⇒ KB 内 **47**。**本 run 由来の新規はゼロ**、`[[2026-08-28]]` は解決 ✅。(5) staleness — 🟢 大幅改善 (audit は 08-28 04:31Z まで現行、`last_candidate_row_age_sec` 5.8秒、shadow 前進中)、🔴 `/api/oanda/equity` **18日** と learner **9日** は stale のまま。
- 🔴 **プロセス上の欠落を検出: 2026-08-26 の wiki-daily run は trade log と index.md の System State 行は更新したが、index.md の Session History エントリと log.md のセクションを一切書いていない。** 本 run の Session History は 08-23 エントリの直上に挿入した (08-26 分は事後捏造せず未記載のまま残す)。**wiki-daily の Phase 3/6 が部分実行で終わり得ることの実証** — 次 run で完了確認を要する。
- ⚠️ **audit limit=30 は今回も誤報告になっていた** — `limit=500` (2026-08-19 01:05 → 08-28 04:31 UTC、total 15,950) に対し 30行では 08-28 の tail のみを覆い live fill 1本を取り逃す。`feedback_audit_limit30_hides_live_fills` **5回連続の確認**。
- ⚠️ 未解決（継続）: 🔴 **08-21→08-26 障害の原因未特定**（再発すれば estimator が再び盲目化）/ 🔴 `rnb_usdjpy:direction_filter` blocks ≥ ticks、code 読み未実施 / 🔴 **新規 `hedge_block` の shadow→live 抑制 決裁** / 🔴 `/api/oanda/equity` 18日 stale / 🔴 **carry-dip 宣言 150p SL vs 実測 18.8p 置換 — 依然として最高価値の open item、book 唯一の正セルで live fill 9本が close 済** / 🔴 Price-Shock family demote 決裁 / JPY 台帳 ¥46,105 drift / learner blacklist no-op / zero-unit emission / `API_AUTH_TOKEN` watchdog gap / `sr_anti_hunt_bounce` corruption。

## 2026-08-28 (evening, run #2) wiki-daily-update (実現 book は 6h51m で bit-flat — 収穫は block-counter の性質確定)

- ⚪ **realized book は 05:00Z 実行と完全一致**: N=**579** / 252W-292L-35BE / WR 43.5% / decided 46.3% / EV **−1.06** / PnL **−611.1p** / Wilson 42.2 / BF 39.4 / avg R 0.12 / DD **1198.8p (=119.9% legacy $1000 基準)** / `dd_pct` 0.097 / edge **−20.06%** / Kelly 0.0 / DSR 0.0 (haircut 100%) / ruin 0.0%。7時間の日中窓としては当然で、**08-21→08-26 のフリーズの再発ではない** — audit +16行、`engine_tick_age_sec` 2.8s、`last_candidate_row_age_sec` 6.1s、24 mode 稼働、watchdog alive。30d 窓は**ロールしていない** (`effective_date_from` 07-29T11:50:31 のまま n=16) ので、今回は 08-23 / 05:00Z と違い **window arithmetic を差し引く必要がない**
- 🟢 **本実行の唯一の実質的収穫 = 未決の曖昧さの解消**: 08-26 と 05:00Z の両方が「block counter は pull 間で比較不能、窓がロールしたのか reset かは不明」と書かざるを得なかった。**本 pull が決着させた** — 総 block が 6h51m で **17,718 → 3,871 (−78%)** に落ちる一方 `main_loop_restarts` は **1 のまま**でエンジンは停止していない。プロセス再起動では説明できず、実際の blocking 減少でもない。**シェアがほぼ完全に保存されている**から: `hedge_block` 35.4→**33.8%** / `r2_shadow_demoted_cell` 23.3→**25.5%** / `order_bar_dedup` 20.5→**22.4%** / `direction_filter` 14.8→**16.3%**。⇒ **`/api/demo/block-counts` は rolling/windowed counter であり cumulative-since-boot ではない。絶対値を pull 間で差分してはならない、意味があるのは単一 pull 内のシェアのみ。** これは 08-26 の「ticks 62,472→57,029」の奇妙さも reset イベントを仮定せずに遡って説明する (**standing rule として記録**)
- 🔴 **`rnb_usdjpy:direction_filter` = 630 blocks / 630 ticks = 比 ちょうど 1.0000** — 3回連続の確認かつ**初の厳密一致**。独立に再窓化されたサンプルで**全 tick が拒否された**。選択的フィルタが新鮮な窓の 100% を拒否することはあり得ない ⇒ 既知の `compute_rnb_signal` WAIT パス `entry: 0` バグと整合。**コード読みは依然未実施 — 3実行連続で最上位の open follow-up**
  | pull | blocks | ticks | ratio |
  |---|---:|---:|---|
  | 08-26 | 2,624 | 2,622 | 1.0008 |
  | 08-28 05:00Z | 2,624 | 2,622 | 1.0008 |
  | **08-28 11:52Z** | **630** | **630** | **1.0000** |
- 🔴 **`hedge_block` の shadow→live 抑制をコード再読なしに独立再確認**: 依然 #1 blocker (**1,310 = 33.8%**)、`open_trades` = **5行すべて `is_shadow: 1`** (`sr_break_retest` AUD_JPY ×2 / `session_time_bias` EUR_USD / `session_time_bias` GBP_USD / `streak_reversal` USD_JPY) に対し broker `open_trade_count: 0` / `margin_used: ¥0`。**book が入れ替わった (6→5、戦略も別) のに性質が保たれた** = 05:00Z の code-level 検証 (`modules/demo_trader.py:4915-4928`) を実測が裏書き。user 決裁待ち、**コードは触っていない**
- ⚪ **新規 LIVE fill 0**。最終は #9 `price_shock_rev_aud_jpy_h1_long` AUD_JPY oanda **#709537** (08-26 14:59:26Z) のまま。累計 **9 fills / 9 real ids / false-sent 0** で 07-02 accept/reject 契約は維持。新規 16行 slice = **16 `skipped` / 0 `blocked` / 0 `sent` / 0 `filled`**、GBP_USD 6 / AUD_JPY 3 / EUR_JPY 2 / USD_JPY 2 / EUR_USD 2 / EUR_GBP 1、`session_time_bias` 5 / `sr_break_retest` 3
- 🟢 **本 log 初の「agg_kelly block 0」slice** — ただし**ゲートの変更ではない**: live 適格候補が sizing 段階に到達せず、ゲートに拒否すべきものが無かっただけ。直前窓では同じ −0.2006 edge で 7 件 block している。**集約 Kelly ゲートが降りたと読んではいけない**
- ⚠️ 🆕 **`shadow_count` が 12,558 → 12,557 に減少** — append-only であるべきカウンタが逆行した。幅は些少で live book には無関係だが**方向が誤り**で、本 log 初の観測。**記録のみ、診断はしない** (1観測では欠陥か集計境界効果かを区別できない) — 次回実行で2度目の減少があれば本物
- **zero-unit emission 継続**: 全 pull **98/600 行 (16.3%)**、新規 slice では **4/16 (25%)** で全て SR 系 (`sr_anti_hunt_bounce` ×2 / `sr_break_retest` ×2)。全て `bridge_status=skipped` ⇒ **live exposure ゼロ**だが shadow-first では shadow が estimator。08-23 以来 性質不変、**未診断**
- **carried 変化なし**: JPY NAV 台帳が broker より **¥46,105.02** 上振れ (台帳 ¥324,450.50 vs NAV ¥278,345.48、sizing は 0.20× 飽和で影響なし、報告は broker 基準 DD を過小評価); 🔴 `/api/oanda/equity` **18日 stale** (最終 2026-08-10 07:20:34Z、`count` 928); `attribution` は依然 **gross = net = −58.4 に対し friction = 71.3** (算出されているが減算されていない)
- **Learning API**: 新規 adjustment **なし** — id=93 (2026-08-19 14:25) のままで **5スナップショット連続**。`entry_type_blacklist` は依然 **`[]`** = no-op 未解消 (06-30 以来)。**journaled 30件のうち 12件が同一 `sr_channel_reversal` 除外のバイト同一 re-affirm**。daytrade EV **−2.60** (n=94) / scalp **−0.15** (n=388) / swing `ready=false` — **05:00Z および 08-26 と bit-identical**
- **strategy page 更新なし / tier 変更なし** — 本窓で closed trade を得失した cell が無く、いずれの promote/demote 閾値にも影響しない。`usdjpy_carry_dip_accumulator` (N=9 / WR 55.6% / **+84.0**) と `price_shock_rev_aud_jpy_h1_long` (N=3 / WR 66.7% / **−102.5**) は 05:00Z から不変
- **Lint**: `tier_integrity_check --check` **PASS** (exit 0、既知 warning 2件のみ)。ただし「legacy dead inline / 30日以上未発火」INFO に依然 **`ihs_neckbreak`** が含まれ、本 pull に生きたカウンタがある (`daytrade_eurjpy:unknown_type:ihs_neckbreak` = 1) — checker が Render API でなくローカル状態を読むため。**5実行連続の矛盾報告**。`sync_kb_index --check` **PASS「index.md is in sync」** (exit 0) = **`--write` 不要の初のクリーンパス**。WR/PnL の頁間整合 ✅ (index.md / 2026-08-28.md / 本ファイルすべて N=579・WR 43.5%・PnL −611.1・DD 1198.8)。broken wikilink: `wiki/index.md` **7** (08-23/08-26/08-28-05:00Z と同一集合) / `wiki/strategies/` **1** 非MEMORY (`xs-momentum-rsi-tv-phase2-2026-05-13`)、KB全体 125 のうち 55 が MEMORY 系 ⇒ **in-KB 70**。⚠️ **KB全体の数値は 05:00Z の 76/29/47 と比較不能** (より厳格な resolver を使用) — 安定した2指標 (index.md 7 / strategies 1) は完全一致、**本実行由来の新規 broken link 0**
- **staleness**: 🟢 audit は **11:46:50Z** まで最新 (pull 時点で6分)、candidate row 6.1s; 🔴 equity **18日**、learner **9日**
- **audit は `limit=600`** (2026-08-17 15:47 → 08-28 11:46 UTC、total **15,966**)。`limit=30` なら直近3行程度しか覆えず **live fill 0 と誤報**していた — `feedback_audit_limit30_hides_live_fills` の **6回連続確認**

## 2026-08-31 wiki-daily-update (risk dashboard がゼロ取引で正に反転 — 本 log 最大の window-arithmetic 錯覚)

- 🔴🔴 **本 pull 最大の所見 = `/api/risk/dashboard` の全 headline 統計が符号反転したが、新規 trade は 1 本も無い。** Kelly edge 0.0→**+0.6709** (推奨 **half_kelly 0.128**、本 log 初の非ゼロ)、Sharpe −0.0927→**+0.3067**、DSR 0.0 (haircut 100%)→**0.5624 (haircut 15.1%)**、30d net −58.4→**+94.3**。原因は完全に機械的: `effective_date_from` が 07-29T11:50:31→**08-01T13:41:34** にロールし n 16→**13**、**負け 3 本が 30d 窓から抜けた**だけ (+152.7 の全量)。**live fill は 0 本**で最終は依然 `price_shock_rev_aud_jpy_h1_long` AUD_JPY oanda **#709537** (08-26 14:59:26Z)。**08-23 / 08-28 ×2 に続く 4 回連続の window-arithmetic、かつ初めて符号を反転させた事例** — エッジ回復として伝播させてはならない
  - 🔴 **同時刻に本番 sizing gate は反対を読んでいる**: blocked 6 行すべて **`agg_kelly=-0.315<0`**。dashboard (n=13 の rolling-30d live slice) と gate (aggregate book) が**公然と乖離**。**資本を実際に投下するのは gate の数字**であり、それは負のまま。系自身も防御状態を解いていない — `defensive_mode` **true** / `lot_multiplier` **0.2** / DD **1198.8pip (119.9%)** すべて不変
  - 窓内は**統計的に何も有意でない**: `dsr_overall.is_significant` **false**、`small_sample_lowconf` **true**、per-strategy Kelly は **3/3 すべて `insufficient`** (n=9/3/1、carry-dip の n=9 すら)。per-strategy DSR は carry-dip のみ算出 (0.5193 / haircut 5.2% / **not significant**、z=0.048)
  - 窓構成 (n=13): USD_JPY 9本 **+84.0** / AUD_JPY 1本 +20.1 / EUR_GBP 3本 −9.8。correlation は全 cross-pair **null** (overlap 不足)、`flagged_pairs` 空
- ⚠️ **`attribution` の friction 未減算バグが、今度は「正の窓を 45% 過大表示する」向きに作用**: `gross_pnl = net_pnl = alpha = 94.3` に対し `friction = 42.5` (`avg_friction_per_trade` 3.27)。正しく減算すれば 30d net は **+51.8**。従来は負の窓を歪めていた (gross=net=−58.4 / friction 71.3) が、**本 log 唯一の正の窓を、最も過剰投下を誘う方向に歪めている**。既存・未解消・**本 run では未診断**
- ⚪ **realized book は 3 スナップショット連続で bit-flat** — N=**579** / 252W-292L-35BE / WR **43.5%** / decided 46.3% / EV **−1.06** / PnL **−611.1p** / Wilson 42.2 / BF 39.4 / avg R 0.12。約3日間 **closed fill 0 / live fill 0**
  - 🟢 **ただし 08-26 型の freeze ではない — 「outage」ではなく「suppression」**: `shadow_count` 12,557/12,558→**12,655 (+97/98)**、`oanda_audit.total` 15,966→**16,080** (17:14Z 時点 `execution_audit_count` 16,095)、`engine_tick_age_sec` **0.1s**、24 mode 稼働、`main_loop_restarts` **1** のまま、OANDA heartbeat ok @109ms。**shadow estimator は前進しているのに live 経路だけが何も出していない** ⇒ 抑制源は既に決裁待ちの 2 gate (`hedge_block` の shadow 計上、agg-Kelly −0.315)。116行 slice の **live rate 0.0% = 本 log 最低**
  - ⚠️ freshness は健全だが鈍化: `last_candidate_row_age_sec` **775.3s (12.9分)** / `last_trade_row_age_sec` **1616.6s (26.9分)**、いずれも `status: ok`。08-28 の 5.8〜6.1s と比べ明確に遅い (日曜深夜〜月曜 open の UTC 帯、障害としては未計上)
- **audit slice** (08-28T11:46Z→08-31T13:32Z、**116行**): `shadow_tracking` skip **110** / blocked **6** / **sent 0 / filled 0**。instrument = USD_JPY 37 / EUR_USD 27 / GBP_USD 19 / EUR_JPY 14 / AUD_JPY 12 / GBP_JPY 7。entry_type 上位 = `wick_imbalance_reversion` 18 / `dt_sr_channel_reversal` 12 / `dual_sr_bounce` 11 / `london_breakout` 9。累計は **10 sent / 10 filled / 実 id 10 / false-sent 0** で 07-02 accept/reject 契約維持。zero-unit emission **23/116 = 19.8%** (全て skipped ⇒ live exposure ゼロ、08-23 以来 性質不変・**未診断**)
- 🔴 **`rnb_usdjpy:direction_filter` 4回連続確認** — **1,477 blocks / 1,509 ticks = 0.9788**、新鮮な窓の **97.9% を棄却**。selective filter では起こり得ない。既知の `compute_rnb_signal` WAIT-path `entry: 0` バグと整合。**コード読みは依然未実施 — 4 run 連続で最上位の open follow-up**

  | pull | blocks | ticks | ratio |
  |---|---:|---:|---|
  | 08-26 | 2,624 | 2,622 | 1.0008 |
  | 08-28 05:00Z | 2,624 | 2,622 | 1.0008 |
  | 08-28 11:52Z | 630 | 630 | 1.0000 |
  | **08-31 17:14Z** | **1,477** | **1,509** | **0.9788** |

- 🔴 **`hedge_block` の shadow→live 抑制を 3 回目の独立再確認 (実測のみ)**: `open_trades` = **3行すべて `is_shadow: 1`** (`london_fix_reversal` GBP_USD / `gbp_deep_pullback` GBP_USD / `vsg_jpy_reversal` EUR_JPY) に対し broker `open_trade_count: 0` / `margin_used: ¥0`。**open book は 6行→5行→3行と 2 度完全に入れ替わったのに性質は保存** ⇒ 08-28 の code 検証 (`modules/demo_trader.py:4915-4928`) を裏書き。**バグではなく決裁事項 (rule:R2/H2)、user 決裁待ち、コード未変更**
- **block 家族シェア** (単一 pull 内のみ有効 — 08-28 の rolling-counter ルール遵守、**pull 間の絶対値差分は一切算出していない**)、総 **8,821** / **33,473** ticks / 24 mode: `r2_shadow_demoted_cell` **28.8%** (08-28 25.5%) / `hedge_block` **28.4%** (33.8%) / `order_bar_dedup` **23.1%** (22.4%) / `direction_filter` **16.7%** (16.3%) / `score_gate` 2.7% / `conf<30` 0.4%。シェアは再び概ね保存。`hedge_block` は首位を明け渡したが差 0.4pp で、**gate 変更の証拠ではない**
- **Learning API**: 新規 adjustment **なし** — 最新は id=93 (2026-08-19 14:25:37) のままで **6 スナップショット連続 / 12.1日 stale**。`entry_type_blacklist` は依然 **`[]`** = no-op 未解消 (06-30 以来)。journaled 30件のうち id 90-93 は同一 `sr_channel_reversal` 除外の byte 同一 re-affirm。daytrade EV **−2.60** (n=94、WR 41.5%、high/mid/low 全 conf 帯が負) / scalp EV **−0.15** (n=388、WR 40.7%、唯一の非負は **low +0.48**) / swing `ready=false` — **08-28 両 run および 08-26 と bit-identical**
- **strategy page 更新なし / tier 変更なし** — closed fill 0 ⇒ どの cell も trade を得失しておらず、promote/demote 閾値に一切触れない。`usdjpy_carry_dip_accumulator` (N=9 / WR 55.6% / **+84.0**) と `price_shock_rev_aud_jpy_h1_long` (N=3 / WR 66.7% / **−102.5**) は 08-28 から不変。🔴 **carry-dip は book 唯一の実質的な正セルであり、宣言 150p SL vs 実測 18.8p 置換は依然として最高価値の open item**
- ✅ **未決の 2 事象が非事象として close**: (1) 08-28 の `shadow_count` 減少 (12,558→12,557) は **再現せず** (+97/98 前進) — 08-28 の事前登録「2度目の減少があれば本物」に従い **1観測は単独では扱わず、診断は行わない**。(2) **clock skew は 2 run 連続で再現せず** — local UTC 17:14:38 vs server `row_freshness_now` 17:14:38.342 = **0秒**
- **Lint**: (1) 数値整合 ✅ — index.md / `2026-08-31.md` / 本ファイルすべて N=579・WR 43.5%・PnL −611.1・DD 1198.8 で一致。index.md 内の「edge −20.06%」は "prev snapshot 08-28" と明示されており現在値としての誤記ではない。(2) `tier_integrity_check --check` **PASS** (exit 0、warning 2件はいずれも既知: `hull_donchian_fade` QUICK_HARVEST_EXEMPT が ELITE/PAIR_PROMOTED 外、`ob_retest` の strategy file 不在)。🟢 **「legacy dead inline」INFO 14件の矛盾は本 pull では解消** — 14名すべてについて live counter を突合し **該当ゼロ** (08-26 以降 5 run 連続で報告していた `ihs_neckbreak` の生存カウンタが本窓には無い)。⚠️ ただし block/tick counter は rolling のため、**本窓での不在は「削除して安全」の証明ではない**。(3) `sync_kb_index --check` → 差分は**日付スタンプのみ** (2026-08-28 → 2026-09-01)、`--write` で解消し再 check **PASS「index.md is in sync」** ✅。⚠️ tool は JST 基準で 2026-09-01 を刻むが本 run のデータ日は UTC 2026-08-31 — **portfolio ブロックの日付だけ 1 日進んで見える**(既知の tz 差、内容は不変)。(4) broken wikilink (path-aware resolver): `wiki/index.md` **7** = 08-23/08-26/08-28 と**完全同一集合** (自動生成 portfolio-block ref 5件 `mqe-gbpusd-fix` / `vsg-jpy-reversal` / `ma-regime-switch` / `ma-trend-perfect` / `ob-retest` ＋ trade-log ref `2026-04-29` / `2026-04-27`)、`wiki/strategies/` は非 MEMORY **1** (`xs-momentum-rsi-tv-phase2-2026-05-13`)、KB 全体 73 のうち 29 が MEMORY 形式 ⇒ in-KB **44**。**本 run 由来の新規 broken link 0**、`[[2026-08-31]]` は解決 ✅。⚠️ KB 全体値は resolver 厳格度依存で過去 run と非比較 (08-28 は 70、05:00Z は 47) — **安定 2 指標 (index.md 7 / strategies 1) は完全一致**。(5) staleness — 🟢 audit は現行 (`last_candidate_row` 17:01:43Z = 12.9分)、🔴 `/api/oanda/equity` **21日** (最終 2026-08-10T07:20:34Z、`count` 928、**15→18→21日と単調悪化**)、🔴 learner **12.1日**
- ⚠️ **`limit=30` は本日も不十分と実測** — `limit=30` は **5.76時間** (08-31 07:47→13:32Z) / live 行 **0**、`limit=1000` は **18.68日** / live 行 **20**。本日の「新規 fill 0」という結論自体は 30 でも偶然一致するが、**最終 fill がいつか・直近窓に 10 fill があることは limit=1000 でしか確定できない**。`feedback_audit_limit30_hides_live_fills` **7回連続の確認**
- ⚠️ **プロセス上の欠落 (継続)**: `raw/trade-logs/2026-08-29-pre_tokyo.md` が存在する一方 **log.md にも index.md Session History にも 08-29 のエントリが無い**。08-26 で検出した「wiki-daily の Phase 3/6 が部分実行で終わる」事象の **2 例目**。**事後捏造はせず未記載のまま残す** — 記録のみ
- 🔴 未解決（継続）: 08-21→08-26 障害の原因未特定 (本窓では再発なし) / `rnb_usdjpy` code 読み未実施 / `hedge_block` shadow→live 決裁 / `/api/oanda/equity` 21日 stale / **carry-dip 宣言 150p SL vs 実測 18.8p — 最高価値の open item** / Price-Shock family demote 決裁 / JPY 台帳 **¥46,105.02** drift (台帳 ¥324,450.50 vs broker NAV ¥278,345.48、sizing は 0.20× 飽和で影響なし、報告は broker 実測 DD を過小表示) / `attribution` friction 未減算 / learner blacklist no-op / zero-unit emission / `API_AUTH_TOKEN` watchdog gap / `sr_anti_hunt_bounce` corruption

## 2026-09-01 wiki-daily-update (正の dashboard が「凍結」— 窓が回っても同じ 13 trade を再報告しているだけ)

- 🔴🔴 **本 pull の主所見 = 08-31 の正の risk dashboard が「持続」ではなく「凍結」だと確定した。** `effective_date_from` は 08-01T13:41:34→**08-02T11:51:00** と **+22.2h ロールしたのに n は 13 のまま**で、Kelly edge **+0.6709** / half_kelly 0.128 / Sharpe **+0.3067** / DSR **0.5624** @haircut 15.1% / 30d net **+94.3** が **08-31 と bit-identical**。**窓に入った trade も抜けた trade も 0** ⇒ **同じ 13 本を1日後に再報告しているだけ**。08-31 の判定をそのまま維持: **エッジ回復として伝播させてはならない。5回連続の window-arithmetic 読み**
  - 🔴 **本番 sizing gate は同一値で反対を読み続けている**: blocked 3 行すべて **`agg_kelly=-0.315<0`** — 08-31 の 6 行と**同じ数値**。dashboard (n=13 rolling-30d live slice) と gate (aggregate book) の乖離は解消していない。**資本を投下するのは gate の数字**
  - 窓内は依然として統計的に無意味: `is_significant` **false** / `small_sample_lowconf` **true** / per-strategy Kelly **3/3 `insufficient`** (n=9/3/1)。窓構成も不変 (USD_JPY 9 +84.0 / AUD_JPY 1 +20.1 / EUR_GBP 3 −9.8)、correlation 全 null
  - 防御姿勢不変: `defensive_mode` **true** / `lot_multiplier` **0.2** / DD **1198.8pip (`dd_pct` 0.097)** / eq_current −$1181.9 vs peak +$16.9
- ⚪ **実現 book は 4 スナップショット連続で bit-flat** — N=**579** / 252W-292L-35BE / WR **43.5%** / decided 46.3% / EV **−1.06** / PnL **−611.1p** / Wilson 42.2 / BF 39.4 / avg R 0.12。**約4日間 closed fill 0 / live fill 0**
  - 🟢 **08-26 型 freeze ではなく suppression であることを再確認**: `shadow_count` 12,655→**12,719 (+64)**、`oanda_audit.total` 16,080→**16,153 (+73)** (本 pull は `execution_audit_count` と完全一致、08-31 は 15 ずれていた)、`engine_tick_age_sec` **0.3s**、24 mode 稼働、`main_loop_restarts` **1** のまま、OANDA heartbeat ok @103ms
  - 🟢 **freshness が 08-31 の鈍化から回復** — `last_candidate_row_age_sec` **7.8s** (08-31: 775.3s)。`last_trade_row_age_sec` 1037.8s (17.3分)、いずれも `status: ok`
- **audit slice** (08-31T13:32:50Z→09-01T11:35:20Z、**74行 / 21.96h**): `shadow_tracking` skip **71** / blocked **3** (全て `agg_kelly=-0.315<0`) / **sent 0 / filled 0**。**live rate 0.0% = 2 slice 連続**。最終 live fill は依然 `price_shock_rev_aud_jpy_h1_long` AUD_JPY oanda **#709537** (08-26 14:59:26Z) = **6.0日前**。instrument = USD_JPY 19 / GBP_USD 17 / EUR_USD 11 / AUD_JPY 10 / GBP_JPY 9 / EUR_JPY 5 / EUR_GBP 3、entry_type 上位 = `session_time_bias` 10 / `dt_sr_channel_reversal` 5 / `streak_reversal` 5 / `sr_break_retest` 5。15日窓の累計は **7 sent / 7 filled / 実 id 7 / false-sent 0** (窓が 08-17 で切れているため; 全累計 10/10 は 08-31 log 参照) で 07-02 accept/reject 契約維持
- **zero-unit emission**: 新規 slice **10/74 (13.5%)**、全 800 行 **135/800 (16.9%)**。全て `bridge_status=skipped` ⇒ **live exposure ゼロ**だが shadow-first では shadow が estimator。08-23 以来 性質不変・**未診断**
- 🔴 **`hedge_block` の shadow→live 抑制を 4 回目の独立再確認、かつ首位に復帰 (34.2%)**: `open_trades` = **4行すべて `is_shadow: 1`** (`session_time_bias` GBP_USD / `vol_spike_mr` USD_JPY / `session_time_bias` EUR_USD ×2) に対し broker `open_trade_count: 0` / `margin_used: ¥0`。**open book は 6→5→3→4 行と 3 度完全に入れ替わり、繰り越された戦略は一つも無いのに性質は保存**。08-28 の code 検証 (`modules/demo_trader.py:4915-4928`) を再度裏書き。**バグではなく決裁事項 (rule:R2/H2)、user 決裁待ち、コード未変更**
- 🟢⚠️ **open shadow 行の meta が populated だった — ただし `sr_anti_hunt_bounce` 汚染の close ではない**: 4行すべて `alpha_snapshot` 非空 (KSFT/KSFT2/RSV10/ROC10/QTLD5、`stale_bars: 0`)、うち2行が `edge_cell_id="E8"`。`project_sr_anti_hunt_demo_trades_meta_loss_2026-06-03` の「100% 空」と正反対。**スコープ注意: 当該 memo は closed `sr_anti_hunt_bounce` 行の話で、この4行はいずれも別戦略** ⇒ **修正の証拠ではなく、現在の open book が clean というだけ**。対象戦略の再クエリは依然必要
- **block 家族シェア** (単一 pull 内のみ有効): 総 **1,625** / **5,228** ticks / 24 mode — `hedge_block` **34.2%** (08-31 28.4%) / `r2_shadow_demoted_cell` **32.9%** (28.8%) / `order_bar_dedup` 15.8% (23.1%) / `direction_filter` 14.5% (16.7%) / `same_price_0pip` 1.0% / `conf<30` 1.0%。⚠️ **counter 窓が再びロール** (33,473→5,228 ticks、`main_loop_restarts` は 1 のまま) ⇒ 08-28 の rolling-counter ルールに従い **pull 間差分は一切算出していない**
- 🔴 **`rnb_usdjpy:direction_filter` 5回連続確認** — **235 blocks / 235 ticks = 1.0000**。新鮮に再窓化されたカウンタで**全 tick を棄却**。selective filter では起こり得ない。既知の `compute_rnb_signal` WAIT-path `entry: 0` バグと整合。**コード読みは依然未実施 — 5 run 連続で最上位の open follow-up**

  | pull | blocks | ticks | ratio |
  |---|---:|---:|---|
  | 08-26 | 2,624 | 2,622 | 1.0008 |
  | 08-28 05:00Z | 2,624 | 2,622 | 1.0008 |
  | 08-28 11:52Z | 630 | 630 | 1.0000 |
  | 08-31 17:14Z | 1,477 | 1,509 | 0.9788 |
  | **09-01 11:52Z** | **235** | **235** | **1.0000** |

- 🔴 **`/api/oanda/equity` が 22日 stale** — 最終 curve point 依然 **2026-08-10T07:20:34Z**、`count` **928**、`total_pl_jpy` −80,686。**15→18→21→22日** と単調悪化。JPY 台帳 drift は**円単位で不変**: 台帳 ¥324,450.50 vs broker NAV ¥278,345.48 = **¥46,105.02** (sizing は 0.20× 飽和で影響なし、報告は broker 基準 DD を過小評価)
- ⚠️ **`attribution` friction 未減算 継続** — `gross_pnl = net_pnl = alpha = 94.3` に対し `friction = 42.5` (`avg_friction_per_trade` 3.27)。正しく減算すれば 30d net は **+51.8**。既存・未解消・**本 run では未診断**
- **Learning API**: 新規 adjustment **なし** — id=93 (2026-08-19 14:25:37) のままで **7 スナップショット連続 / 13.1日 stale**。`entry_type_blacklist` は依然 **`[]`** = no-op 未解消 (06-30 以来)。journaled 30件のうち id 90-93 は同一 `sr_channel_reversal` 除外の byte 同一 re-affirm。daytrade EV **−2.60** (n=94、WR 41.5%、high/mid/low 全 conf 帯が負) / scalp EV **−0.15** (n=388、WR 40.7%、唯一の非負は **low +0.48**) / swing `ready=false` — **08-31 / 08-28 両 run / 08-26 と bit-identical**
- **strategy page 更新なし / tier 変更なし** — closed fill 0 ⇒ どの cell も trade を得失しておらず、promote/demote 閾値に一切触れない。`usdjpy_carry_dip_accumulator` (N=9 / WR 55.6% / **+84.0**) と `price_shock_rev_aud_jpy_h1_long` (N=3 / WR 66.7% / **−102.5**) は 08-28 から不変。🔴 **carry-dip は book 唯一の実質的な正セルであり、宣言 150p SL vs 実測 18.8p 置換は依然として最高価値の open item**
- **Lint**: (1) 数値整合 ✅ — index.md / `2026-08-31.md` / `2026-09-01.md` すべて N=579・WR 43.5%・PnL −611.1・DD 1198.8 で一致。(2) `tier_integrity_check --check` **PASS** (exit 0、warning 2件はいずれも既知: `hull_donchian_fade` QUICK_HARVEST_EXEMPT、`ob_retest` の strategy file 不在)。⚠️ **「legacy dead inline」INFO の矛盾が別名で再燃** — 14件を live counter と突合し **13件は counter ゼロ (整合) だが `ob_retest` は audit 6行 (全て GBP_JPY BUY / skipped / 2026-08-20 03:16→07:01Z = 12.2日前) を持つ**。30日以上未発火という主張は成立しない。08-26→08-28 の `ihs_neckbreak` と**同一の根因 = checker が Render API でなくローカル状態を読む**。08-31 は「解消」と記録したが、**解消したのは `ihs_neckbreak` という名前であって checker の欠陥ではない**。(3) `sync_kb_index --check` **PASS「index.md is in sync」** (exit 0) = **2 run 連続のクリーンパス、`--write` 不要**。(4) broken wikilink (path-aware resolver): `wiki/index.md` **7** = 08-23/08-26/08-28/08-31 と**完全同一集合** (`mqe-gbpusd-fix` / `vsg-jpy-reversal` / `ma-regime-switch` / `ma-trend-perfect` / `ob-retest` / `2026-04-29` / `2026-04-27`)、`wiki/strategies/` 非MEMORY **1** (`xs-momentum-rsi-tv-phase2-2026-05-13`)、KB全体 77 のうち 29 が MEMORY 系 ⇒ **in-KB 48** (08-31: 44)。⚠️ **新規 in-KB broken link 1件は本 run 由来ではない** — ``[[kalman-d7-minlot-carveout-prereg-2026-09-01]]`(未作成)` (参照元 `wiki/sessions/2026-09-01-session.md`、本日の対話セッションが作成、pre-reg 文書が未作成)。**本 run が導入した broken link は 0**。(5) staleness — 🟢 audit 現行 (`last_candidate_row` 11:52:30Z = 7.8s)、🔴 equity **22日**、🔴 learner **13.1日**
- ✅ **clock skew は 3 run 連続で再現せず** — local UTC 11:52:37 vs server `row_freshness_now` 11:52:37.787 = **0秒**
- ⚠️ **`limit=30` は本日も不十分と実測 — 8回連続確認**: `limit=30` は **5.31時間** (09-01 06:17→11:35Z) / live 行 **0**、`limit=800` は **14.95日** / live 行 **14**。本日の「新規 fill 0」自体は 30 でも一致するが、**最終 fill の時刻と直近窓の 7 fill は limit=800 でしか確定できない**。`feedback_audit_limit30_hides_live_fills` の **8回連続確認**
- ⚠️ **プロセス上の欠落 (継続)**: `raw/trade-logs/2026-08-29-pre_tokyo.md` が存在する一方 **log.md にも index.md Session History にも 08-29 のエントリが無い**。08-26 検出「wiki-daily の Phase 3/6 が部分実行で終わる」事象の **2 例目**。**事後捏造はせず未記載のまま残す** — 記録のみ
- 🔴🆕 **並行 repo プロセスが本 run の成果物を無言で破壊した。** 本 run の書き込み中、別の自動プロセスが **2026-09-03 11:18:15–16 JST** に `git reset` → `git pull --ff-only origin main` を実行 (`git reflog`: `f18c3b0b → 874fb3c8`、17 commits)。影響: `raw/trade-logs/2026-09-02.md` は**削除**され書き直し、`wiki/index.md` は**09-01 状態へ全面 revert** され再適用、`wiki/log.md` は 11:18 以降の append だったため**生存**。**Write は成功を返したのにファイルは消えており、run 内に何の兆候も出なかった** — 書き込み後の検証パスでのみ検出できた。`feedback_concurrent_agent_repo_hazard` の実例。**対策 (本 run で採用)**: 再適用後に全成果物のディスク上存在を検証する。**提言**: wiki-daily は自身の出力を書き込み後に検証すべきであり、他エージェントが未コミット作業を保持している worktree に対して自動ジョブが `reset`/`pull` を行うべきではない
  - 🟢 ただし当該 pull は損失だけではない — **`c41a4bdc` (PR #220) と `lesson-shadow-emit-dedup-writetime-2026-09-02.md` はこの pull で入ってきたものであり、zero-unit emission を 6 度目の持ち越しにせず本日 CLOSE できたのはそのおかげ**
- ✅ **本 run で CLOSE**: zero-unit emission (08-23 以来) = 意図的なロット未割当マーカー、PR #220 で自己記述化
- 🔴 未解決（継続）: **carry-dip 宣言 150p SL vs 実測 18.8p — 最高価値の open item** / `rnb_usdjpy` code 読み未実施 (5 run) / `hedge_block` shadow→live 決裁 (rule:R2/H2) / `/api/oanda/equity` 22日 stale / 08-21→08-26 障害の原因未特定 (本窓では再発なし) / Price-Shock family demote 決裁 / JPY 台帳 **¥46,105.02** drift / `attribution` friction 未減算 / learner blacklist no-op / zero-unit emission / `API_AUTH_TOKEN` watchdog gap / `sr_anti_hunt_bounce` corruption / `tier_integrity_check` のローカル状態参照欠陥

## 2026-09-02 wiki-daily-update (凍結した正 dashboard が 2 度目のロールにも耐えた / zero-unit emission が CLOSE)

- 🔴🔴 **本 pull の主所見 = 08-31 に反転した正の risk dashboard が「2 度目のロール」にも耐え、依然として純粋な窓算術である。** `effective_date_from` は 08-02T11:51:00→**08-03T19:42:06 (+31.9h)** とロールし、**2 回のロール計 +54.1h で窓に入った trade も抜けた trade も 0**。n は **13** のまま、Kelly edge **+0.6709** / half_kelly 0.128 / Sharpe **+0.3067** / DSR **0.5624** @haircut 15.1% (`is_significant` **false**、z=0.157) / 30d net **+94.3** が **3 pull 連続で bit-identical**。**同じ 13 本を 3 日続けて再報告しているだけ** — 08-31 の判定を維持: **エッジ回復として伝播させてはならない。6 回連続の window-arithmetic**
  - 🔴 **本番 sizing gate は 3 pull 連続で同一値の反対を読む**: blocked **13 行すべて `agg_kelly=-0.315<0`** (09-01 は 3 行、08-31 は 6 行、いずれも同値)。dashboard (n=13 rolling-30d live slice) と gate (aggregate book) の乖離は不変。**資本を投下するのは gate の数字**
  - 窓内は統計的に無意味のまま: `small_sample_lowconf` **true**、per-strategy Kelly **3/3 `insufficient`** (n=9/3/1)、per-strategy DSR は carry-dip のみ (0.5193 / haircut 5.2% / not significant)。窓構成不変 (USD_JPY 9 +84.0 / AUD_JPY 1 +20.1 / EUR_GBP 3 −9.8)、correlation 全 null、ruin 0.0% / median max DD 19.34% / 99th 38.66%
  - 防御姿勢不変: `defensive_mode` **true** / `lot_multiplier` **0.2** / DD **1198.8pip (`dd_pct` 0.097 = legacy pip 基準 119.9%)** / eq_current −$1181.9 vs peak +$16.9
  - ⚠️ `attribution` friction 未減算 継続 — `gross_pnl = net_pnl = alpha = 94.3` に対し `friction = 42.5` (`avg_friction_per_trade` 3.27)。正しく減算すれば 30d net は **+51.8**。**本 run でも未診断**
- ⚪ **実現 book は 5 スナップショット連続で bit-flat** — N=**579** / 252W-292L-35BE / WR **43.5%** / decided 46.3% / EV **−1.06** / PnL **−611.1p** / Wilson 42.2 / BF 39.4 / avg R 0.12。**約5日間 closed fill 0 / live fill 0**
  - 🟢 **outage ではなく suppression を再確認**: `shadow_count` 12,719→**12,843 (+124)**、`oanda_audit.total` 16,153→**16,303 (+150)** (`execution_audit_count` 16,307 は 42分後の status pull 由来で整合)、`engine_tick_age_sec` **0.1s**、24 mode 稼働、`main_loop_restarts` **1** のまま、OANDA heartbeat ok @78ms、`emergency_killed` false
  - ⚠️ freshness は再び鈍化するも閾値内: `last_candidate_row_age_sec` **3,165s (52.8分)** (09-01: 7.8s) — endpoint 自身の market-open 換算で **0.9h / 閾値 6h**、`status: ok`。`last_trade_row_age_sec` 525s (8.75分)。⚠️ 20:16:14Z の trade 行は **shadow** の建玉 (下記) であり **live 活動の証拠ではない**
- **audit slice** (09-01T12:33:14Z→09-02T18:31:22Z、**150行 / 29.97h**): skip **137** (`shadow_tracking` 128 + `shadow_tracking(shadow_emit_no_lot)` 9) / blocked **13** (全て `agg_kelly=-0.315<0`) / **sent 0 / filled 0**。**live rate 0.0% = 3 slice 連続**。最終 live fill は依然 `price_shock_rev_aud_jpy_h1_long` AUD_JPY oanda **#709537** (08-26 14:59:26Z) = **7.23日前**。instrument = USD_JPY 60 / GBP_USD 33 / EUR_USD 20 / AUD_JPY 12 / EUR_JPY 12 / GBP_JPY 11 / EUR_GBP 2、entry_type 上位 = `xs_momentum_rsi` 20 / `dt_sr_channel_reversal` 17 / `dual_sr_bounce` 10 / `vix_carry_unwind` 10 / `session_time_bias` 9 / `sr_break_retest` 9 / `trendline_sweep` 9 / `streak_reversal` 9。14.23日窓の累計は **6 sent / 6 filled / 実 id 6 / false-sent 0** (窓が 08-19 で切れているため; 全累計 10/10 は 08-31 log 参照) で 07-02 accept/reject 契約維持。⚠️ `reference_oanda_audit_twin_meaning` の再確認 — `sent` 行は戦略名、`filled` 行は MODE 名 (`daytrade_1h` / `daytrade_1h_eurgbp` / `daytrade_1h_audjpy`) を載せる。**6 trade であって 12 ではない**
- ✅ **zero-unit emission が CLOSE — 08-23 以来「未診断」で持ち越してきた項目が本日決着した。** audit に新 `block_reason` `shadow_tracking(shadow_emit_no_lot)` が出現 (初出 **2026-09-02 08:52:19Z**)。これは **PR #220 (`c41a4bdc`, "fix(dedup): shadow_emit のプロセス境界 dedup 突破を write-time DB flag で塞ぐ (rule:R3)"、commit 09-02 16:21 JST = 07:21Z) が入れた意図的な自己記述**であり (`modules/demo_trader.py:1492`)、**当該行の `units: 0` は「ロット未割当のトラッキングマーカー」で 「サイズ 0 の発注」ではない** — 本 log が問い続けてきた問いの答えそのもの。**読み手はこの `units` をサイズとして使ってはならない**。`shadow_tracking` prefix は維持されており startswith 依存の guard/tool は互換
  - **帰属を推測でなく確定させたのは deploy 境界での完全な分割**: 新 slice の zero-unit 15 行のうち **08:52:19Z 以前 6 行は labelled 0 件、以降 9 行は labelled 9 件** = **deploy 後 100% / deploy 前 0%**。したがって無印の 6 行 (`sr_break_retest` AUD_JPY ×2 09-01 13:31 / `vdr_jpy` EUR_JPY ×2 09-02 06:11 / `inducement_ob` GBP_USD ×2 09-02 07:19) は**単に deploy 前であって、第 2 の未説明経路ではない**。発生率自体は不変 (新 slice **15/150 = 10.0%**、全窓 **120/800 = 15.0%**、全て `bridge_status=skipped` ⇒ live exposure ゼロ)
  - ⚠️ **これで閉じないもの**: 同 PR の実質的変更は「プロセス境界を越える重複 shadow 行に対する write-time DB dedup flag」(`wiki/lessons/lesson-shadow-emit-dedup-writetime-2026-09-02.md`、dedup 系 5 例目)。上記の labelled ペアはいずれも **13〜32 秒差の近接重複** = まさに当該 PR が対象とするパターンであり、修正は **prevent ではなく flag** (`dedup_violation=1` で行は INSERT される設計)。audit endpoint は `dedup_violation` を露出しないため **本 run では flag が実際に立っているか検証できない** — `demo_trades` 直クエリが必要。**より狭い follow-up として新規登録**
- 🔴 **`hedge_block` の shadow→live 抑制を 5 回目の独立再確認**: `open_trades` = **2行とも `is_shadow: 1`** (`ny_close_reversal` USD_JPY SELL 20:16:14Z / `dual_sr_bounce` GBP_USD SELL 19:57:21Z) に対し broker `open_trade_count: 0` / `margin_used: ¥0`。**open book は 6→5→3→4→2 と 4 度完全に入れ替わり、09-01 から繰り越された戦略は一つも無いのに性質は保存**。08-28 の code 検証 (`modules/demo_trader.py:4915-4928`) を再度裏書き。**バグではなく決裁事項 (rule:R2/H2)、user 決裁待ち、コード未変更**
  - ⚠️ **09-01 の meta 記述に対する方向修正**: 2行とも `alpha_snapshot` は非空 (KSFT/KSFT2/RSV10/ROC10/QTLD5) だが **2行とも `edge_cell_id: ""` (空)**。09-01 は 4行中 2行が `"E8"` だった ⇒ **「metadata が populated 化しつつある」という読みは成立しない**。いずれの観測も `project_sr_anti_hunt_demo_trades_meta_loss_2026-06-03` (対象は **closed `sr_anti_hunt_bounce` 行**) には触れておらず、当該戦略の再クエリは依然必要
- 🆕⚠️ **block family share は従来過少計上だった — `/api/demo/status` の `block_counts` は上位 30 キーで切られている** (`modules/demo_trader.py:2061-2063`、`[:30] # 上位30件のみ`)。専用の **`/api/demo/block-counts`** は全 **103** キー / **8,705** blocks / **28,778** ticks / 24 mode を返す。full basis: `r2_shadow_demoted_cell` **32.0%** / `order_bar_dedup` **24.0%** / `hedge_block` **21.3%** / `direction_filter` **14.0%** / `score_gate` 5.8% / `conf<30` 1.0% / `same_price_0pip` 0.5% / `same_price_5pip` 0.3% / `recent_emit` 0.3% / 他 17 family ≤0.2%。⚠️ **08-28→09-01 の share は下限値であり本 run と比較不能** — `hedge_block` 34.2%→21.3% は **truncation 修正の交絡であって gate 変更の証拠ではない**。counter 窓も再ロール (5,228→28,778 ticks、`main_loop_restarts` は 1 のまま) ⇒ **pull 間差分は一切算出していない**。次 run 以降は full endpoint 同士でのみ比較する
- 🔴 **`rnb_usdjpy:direction_filter` 6回連続確認、かつ過去最強の形**: **1,218 blocks / 1,258 ticks = 0.9682**。残る 40 tick は通過ではなく `rnb_usdjpy:conf<30` であり、**1,258 / 1,258 = 当該 mode の全 tick がいずれかの gate で棄却され、候補は 1 本も生き残っていない**。独立に窓化された 6 つの counter が揃ってこうなることは selective filter では起こり得ない。既知の `compute_rnb_signal` WAIT-path `entry: 0` バグと整合。**コード読みは依然未実施 — 6 run 連続で最上位の open follow-up**

  | pull | dir_filter blocks | ticks | ratio |
  |---|---:|---:|---|
  | 08-26 | 2,624 | 2,622 | 1.0008 |
  | 08-28 05:00Z | 2,624 | 2,622 | 1.0008 |
  | 08-28 11:52Z | 630 | 630 | 1.0000 |
  | 08-31 17:14Z | 1,477 | 1,509 | 0.9788 |
  | 09-01 11:52Z | 235 | 235 | 1.0000 |
  | **09-02 20:25Z** | **1,218** | **1,258** | **0.9682** |

- 🔴🆕 **`/api/oanda/equity` が 23.5日 stale、かつ JPY 台帳 drift が本シリーズで初めて拡大 — 幅はちょうど ¥240**。最終 curve point 依然 **2026-08-10T07:20:34Z**、`count` **928**、`total_pl_jpy` −80,686、`total_pl_pips` −942.2。**15→18→21→22→23.5日** と単調悪化。台帳 `eq_current_jpy` は **¥324,450.50** で不動の一方、**broker NAV が ¥278,345.48 → ¥278,105.48 (−¥240.00 ちょうど)** に低下し drift は **¥46,345.02** へ。**`open_trade_count: 0` / `margin_used: ¥0` / `unrealized_pl: 0` かつ当該区間の fill 0 で NAV が動いた** — financing/fee の計上が最も整合的だが **これは仮説であり本 run では未検証** (`/api/oanda/transactions` 未取得)。次 run で再確認、**2 度目の不可解な丸い額の段差があれば診断に値する**。sizing への影響は依然なし (`DD_LOT_TIERS` は 0.20× で飽和)、報告への影響は依然あり (headline DD が broker 実測 DD を過小表示)
- **Learning API**: 新規 adjustment **なし** — id=93 (2026-08-19 14:25:37) のままで **8 スナップショット連続 / 14.25日 stale**。`entry_type_blacklist` は依然 **`[]`** = no-op 未解消 (06-30 以来)。**journaled 30件のうち 12件が同一 `sr_channel_reversal` 除外の byte 同一 re-affirm** = writer が `current_params` に着地しない決定を journal し続けている。`current_params`: conf 30 / `learn_every_n` 10 / `max_consecutive_losses` 3 / `max_open_trades` 8 / daily-loss・max-DD とも **−99999 (無効)**。daytrade EV **−2.60** (n=94、WR 41.5%、high −1.12/n32・mid −4.07/n39・low −2.18/n23 と **全 conf 帯が負**、regime 別 RANGE −1.59/n62・TREND_BEAR −5.66/n22・TREND_BULL −2.17/n10) / scalp EV **−0.15** (n=388、WR 40.7%、唯一の非負は **low +0.48/n127**) / swing `ready=false` — **09-01 / 08-31 / 08-28 両 run / 08-26 と bit-identical**
- **strategy page 更新なし / tier 変更なし** — closed fill 0 ⇒ どの cell も trade を得失しておらず、promote/demote 閾値に一切触れない。`sync_kb_index --write` の差分は**日付スタンプのみ**で portfolio ブロックは byte 同一 = tier 無変化の裏付け。`usdjpy_carry_dip_accumulator` (N=9 / WR 55.6% / **+84.0**) / `price_shock_rev_aud_jpy_h1_long` (N=3 / WR 66.7% / **−102.5**) / `price_shock_rev_eur_gbp_h1_long` (N=3 / 0.0% / −9.8) は 08-28 から不変。🔴 **carry-dip は book 唯一の実質的な正セルであり、宣言 150p SL vs 実測 18.8p 置換は依然として最高価値の open item**
  - book 全体 (44戦略、`include_shadow: false` / `exclude_xau: true` / 2026-04-08 以降): **正 PnL は 44 中 11 のみ**、うち 8 は N≤7。最深の穴は `price_shock_rev_aud_jpy_h1_long` −102.5 (N=3) / `session_time_bias` −67.8 (N=30) / `vwap_mean_reversion` −63.1 (N=11) / `wick_imbalance_reversion` −63.0 (N=14) / `trendline_sweep` −49.7 (**N=32 で WR 62.5%** = 的中率ではなく payoff 非対称の署名)
- **Lint**: (1) 数値整合 ✅ — index.md / log.md / `2026-09-02.md` すべて N=579・WR 43.5%・PnL −611.1・DD 1198.8 で一致。(2) `tier_integrity_check --check` **PASS** (exit 0、warning 2件はいずれも既知: `hull_donchian_fade` QUICK_HARVEST_EXEMPT、`ob_retest` の strategy file 不在)。🔴 **「legacy dead inline / 30日以上未発火」INFO の矛盾が過去最も鋭い形で露呈** — `ob_retest` は **本日 09-02 08:52:19Z / 08:52:32Z に GBP_USD BUY で 2 回発火**しており (上記 `shadow_emit_no_lot` 9 行のうち 2 行)、**pull のわずか ~11.5 時間前**。09-01 は「12.2日前」と報告したが今や**半日前**。`ihs_neckbreak` (08-26→08-28)、`ob_retest` (09-01) に続く 3 例目で、根因は同一 = **checker が Render API でなくローカル状態を読む**。(3) `sync_kb_index --check` は **FAIL (exit 1)** → `--write` → 再 check **PASS「index.md is in sync」** (exit 0)。⚠️ 差分は**日付スタンプのみ** (2026-09-01 → **2026-09-03**) で、tool は JST を刻む一方 本 run のデータ日は UTC **2026-09-02** ⇒ portfolio ブロックだけ 1 日進んで見える (既知 tz 差、内容不変)。08-31・09-01 の「`--write` 不要」連続記録は途切れたが **理由は純粋に cosmetic**。(4) broken wikilink (path-aware resolver、1,988 ファイル走査): `wiki/index.md` **7** = 08-23/08-26/08-28/08-31/09-01 と**完全同一集合** (`2026-04-27` / `2026-04-29` / `ma-regime-switch` / `ma-trend-perfect` / `mqe-gbpusd-fix` / `ob-retest` / `vsg-jpy-reversal`、本 run で 7 件すべてディスク上の不在を再確認)、`wiki/strategies/` 非MEMORY **1** (`xs-momentum-rsi-tv-phase2-2026-05-13`)、KB全体 **76** のうち 29 が MEMORY 形式 ⇒ **in-KB 47** (09-01: 48)。🟢 **09-01 に唯一の新規として挙げた `[[kalman-d7-minlot-carveout-prereg-2026-09-01]]` は解消済** (`wiki/decisions/` に実在) — 48→47 はこの 1 件。**本 run が導入した broken link 0**。⚠️ 自己修正: 本 scan の初回実行は `wiki/index.md` を **0 件**と報告したが、これは **stem をキーにした dict が重複する `index.md` パスを黙って落とし、`wiki/index.md` を一度も読んでいなかった** scan 側の欠陥。明示的なファイル一覧で再実行した上記 7 件が確定値であり、**過去 run の数値が誤っていたのではなく本 run の初回試行が誤っていた**。(5) staleness — 🟡 audit は準現行 (`last_candidate_row` 19:32:14Z = 52.8分、market-open 0.9h / 閾値 6h、`status: ok`)、🔴 equity **23.5日**、🔴 learner **14.25日**
- ✅ **clock skew は 4 run 連続で再現せず** — local UTC 20:24:58 vs server `row_freshness_now` 20:24:58.984 = **0秒**
- ⚠️ **`limit=30` は本日も不十分と実測 — 9回連続確認**: `limit=30` は **4.64時間** (09-02 13:53→18:31Z) / live 行 **0**、`limit=800` は **14.23日** / live 行 **12** (6 trade × sent+filled)。本日の「新規 fill 0」自体は 30 でも一致するが、**最終 fill が 7.23日前だったことは limit=800 でしか確定できない**。`feedback_audit_limit30_hides_live_fills` の **9回連続確認**
- ✅ **orphan check**: `pgrep -f app.py` は**該当なし** — ローカル `app.py` は動いておらず、phantom なローカル DB 汚染はない。本 log の全数値は Render API 由来 (`_db_path: /var/data/demo_trades.db`)。`feedback_check_orphan_local_app` に準拠
- ⚠️ **プロセス上の欠落 (継続)**: `raw/trade-logs/2026-08-29-pre_tokyo.md` が存在する一方 **log.md にも index.md Session History にも 08-29 のエントリが無い**。08-26 検出「wiki-daily の Phase 3/6 が部分実行で終わる」事象の **2 例目**。**事後捏造はせず未記載のまま残す** — 記録のみ。(08-30 は日曜でファイル自体が皆無 = 想定内、事例に数えない)
- 🔴 未解決（継続）: **carry-dip 宣言 150p SL vs 実測 18.8p — 最高価値の open item** / `rnb_usdjpy` code 読み未実施 (**6 run**) / `hedge_block` shadow→live 決裁 (rule:R2/H2) / `/api/oanda/equity` 23.5日 stale / 08-21→08-26 障害の原因未特定 (本窓では再発なし) / Price-Shock family demote 決裁 / 🆕 broker NAV −¥240 の無建玉・無約定変動 (再確認待ち) / 🆕 PR #220 の write-time dedup flag が実際に `dedup_violation=1` を立てているかの検証 (audit 非露出、`demo_trades` 直クエリ要) / 🆕🔴 並行プロセスの `reset`/`pull` が実行中 wiki-daily の成果物を破壊する事象 (本 run で実際に発生、下記) / JPY 台帳 **¥46,345.02** drift / `attribution` friction 未減算 / learner blacklist no-op / `API_AUTH_TOKEN` watchdog gap / `sr_anti_hunt_bounce` corruption / `tier_integrity_check` のローカル状態参照欠陥 (本日 same-day 発火で反証) / 🆕 `/api/demo/status` `block_counts` の top-30 切り捨て (以後は `/api/demo/block-counts` を使う)

## 2026-09-03 wiki-daily-update (7.63日の fill 空白が破れ、同時にその空白の「説明」が実測で崩れた)

- 🟢 **live fill 発火** — **2026-09-03T05:58:04Z**、`price_shock_rev_aud_jpy_h1_long` / `daytrade_1h_audjpy`、**AUD_JPY BUY 1,000u**、OANDA **#709570**、entry **112.776**、現在 **OPEN** (unrealized **−¥472**、margin ¥4,492.48)。直前 fill (#709537、08-26 14:59:26Z) から **7.63日**。broker `openTradeCount: 1` が live DB 行 (`is_shadow: 0`) と一致 — **本 log 初の非ゼロ live/broker 整合**。新 41行 slice = 39 skipped / **1 sent / 1 filled** ⇒ live rate **4.9%**、3連続 0.0% を終了
- 🔴🔴 **CORRECTION: agg-Kelly gate は fill を抑制していなかった** — 08-31 / 09-01 / 09-02 の3エントリが carry していた因果が実測で崩れた。800行窓の `agg_kelly` **45行は 8 `entry_type` にしか着弾しない** (`xs_momentum_rsi` 20 / `donchian_momentum_breakout` 6 / `kalman_d7_po_dn_flip` 6 / `vsg_jpy_reversal` 4 / `doji_breakout` 4 / `dt_bb_rsi_mr` 3 / `mqe_gbpusd_fix` 1 / `ema200_trend_reversal` 1) で、**実際に live fill する2戦略 (`price_shock_rev_aud_jpy_h1_long` / `usdjpy_carry_dip_accumulator`) は 0回**。決定的証拠は 08-26 の timeline — fill (14:59:26) が同一値 `-0.336` の Kelly block (14:46:21 / 17:06:40) に**挟まれている**。今日の fill も gate 値の変化を要さなかった (最終観測は依然 `-0.315` @ 09-02T17:02Z)。⇒ gate は **特定戦略集合への per-candidate filter で book-wide halt ではない**。7.63日の空白は **1%-tile rare-event 設計 (~0.33% of bars) の signal 枯渇**。共起から演繹して未実測だった主張が、1クエリで反証された (`feedback_label_empirical_audit`)。⚠️ **gate が正に転じたとは主張しない** — blocked 行が無い限り値は観測不能
- 🔴🆕 **live bracket が宣言設計と不一致 (新規・最上位 open item)** — #709570 は **TP #709571 @123.662 = +1,088.6 pip** / **SL #709572 @111.474 = −130.2 pip** (共に GTC PENDING) を持つが、[[price-shock-rev-aud-jpy-h1-long]] の宣言 exit は **12-bar horizon exit + −2×ATR catastrophic SL のみで TP は設計に存在しない**。⚠️ **実測のみ、未診断** (戦略ファイル・発注構築パス未読)。**carry-dip の「宣言 150p SL → 実測 18.8p」と同型** = declared SL/TP が live order に伝わらない系。horizon-exit 設計の玉が設計に無い −130.2 pip stop で落ちるなら **strategy の結果ではなく execution 欠陥**
- ⚪ **realized book は 6連続 bit-flat** — N=**579** / 252W-292L-35BE / WR 43.5% / decided 46.3% / EV **−1.06** / PnL **−611.1pip** / Wilson 42.2 / BF 39.4 / avg R 0.12。**closed fill は約6日ゼロ**、今日の fill は OPEN なので何も動かさない。engine 生存: `shadow_count` 12,843→**12,877 (+34)**、`oanda_audit.total` 16,303→**16,344 (+41)** (`execution_audit_count` **16,344** 完全一致)、tick age **0.6s**、24 modes、restarts **1**、heartbeat ok @87.5ms、candidate age **8.9s**。clock skew **0s** (5連続非再現)。DD 不変 (**1198.8pip** / `dd_pct` 0.097 / defensive true / lot 0.2)
- 🔴🔴 **risk dashboard の凍結した正が3度目の roll にも耐えた — 7連続 window-arithmetic** — `effective_date_from` 08-03T19:42:06→**08-04T11:50:14 (+16.1h)**、3 roll 計 **+70.2h** で **窓に入った trade も抜けた trade も無し**: n=**13** / Kelly edge **+0.6709** / half_kelly 0.128 / Sharpe **+0.3067** / DSR **0.5624** @haircut 15.1% (`is_significant` false、z=0.157) / 30d net **+94.3** が **4 pull 連続 bit-identical**。**同じ13本を4日連続で再報告しているだけ — edge recovery として伝播禁止**。per-strategy Kelly **3/3 insufficient**。`attribution` は依然 gross=net=alpha=94.3 で friction=42.5 未減算 (正しい 30d net **+51.8**) — **本 run 未診断**
- 🔴🆕 **説明不能な realized NAV step が反復 — −¥230.00 (09-02 は −¥240.00)** — broker balance ¥278,105.48→**¥277,875.48**、唯一の open trade は `realizedPL: 0.0`、期間内 closed fill ゼロ。ledger `eq_current_jpy` は ¥324,450.50 で不動 ⇒ realized drift ¥46,345.02→**¥46,575.02** (NAV 基準 ¥47,047.02 は今日の unrealized −¥472 で交絡、**realized 列を読む**)。09-02 が「2例目なら診断対象」と pre-register した通りの2例目。account `financing` は **+¥17.8160** (累積・正) で2日 −¥470 を説明せず、累積 `pl` **−¥81,251.34** vs stale curve −¥80,686 = **−¥565.34 未計上**。`/api/oanda/equity` は **24.2日 stale** (15→18→21→22→23.5→**24.2d**)。**次手 = `/api/oanda/transactions`**
- 🔴 **`rnb_usdjpy:direction_filter` 7連続確認、再び厳密 100%** — `direction_filter` **646** + `conf<30` **18** = **664 blocks / 664 ticks = 100.0%**、生存 candidate ゼロ (09-02 の 1,258/1,258 と同じ閉形)。7つの独立窓 counter が selection で揃うことはない。`compute_rnb_signal` WAIT-path `entry: 0` bug と整合。**コード確認は依然未実施 — 7 run 継続。上記 agg-Kelly 訂正が「共起で読むな」の実例として、着手根拠を強めた**
- ⚠️ **`hedge_block` の tell-tale 条件は本 run 非再現** — `open_trades` = **2行 = shadow 1 + LIVE 1** (`session_time_bias` GBP_USD shadow / `price_shock_rev_aud_jpy_h1_long` #709570 `is_shadow: 0`) vs broker `open_trade_count` **1** ⇒ 08-28→09-02 の署名 (「全行 shadow / broker 0」5回確認) は**崩れた**。機構自体は不変 (`hedge_block` は依然 **#2 family 21.1%**) だが **本 run は新規確認を供給しない**。agg-Kelly 訂正を踏まえ「gate が fill を抑制」論全体は **共起でなく counter からの再導出が必要**。rule:R2/H2 の user 決裁待ち、コード無変更。block family (full basis 3,618 blocks / 15,025 ticks / **71** keys、⚠️ counter 窓が再ロール 28,778→15,025 ticks・103→71 keys で restarts は 1 のまま ⇒ **単一 pull share のみ**): `r2_shadow_demoted_cell` **38.4%** / `hedge_block` **21.1%** / `direction_filter` **17.9%** / `order_bar_dedup` **15.7%** / `score_gate` 3.3% / `conf<30` 1.5%
- ⚠️ **Learning API は 9スナップショット連続凍結** — id=**93** (2026-08-19 14:25:37)、**14.89日 stale**、`entry_type_blacklist` 依然 **`[]`** = **06-30 以来 no-op 未解消**。daytrade EV **−2.60** (n=94、WR 41.5%、**全 conf 帯が負**) / scalp EV **−0.15** (n=388、WR 40.7%、非負は `low` **+0.48** のみ) / swing `ready: false` — 09-02 / 09-01 / 08-31 / 08-28 と bit-identical。`daily_loss_limit_pips`・`max_drawdown_pips` は共に **−99999** (実質無効)
- ✅ **strategy page 1件更新 / tier 変更なし** — closed fill ゼロ ⇒ promote/demote 閾値に非接触。[[price-shock-rev-aud-jpy-h1-long]] は 08-20 時点の **N=2 / WR 50.0% / −122.6pip** で凍結していたが、API 実測は **N=3 / WR 66.7% / EV −34.2 / −102.5pip** — 更新済 (+ 4本目 OPEN と bracket 不一致を追記)。`usdjpy_carry_dip_accumulator` (N=9 / WR 55.6% / **+84.0**) は依然 **book 唯一の実質的な正セル**で、宣言 150p SL vs 実測 18.8p が最高価値 open item
- **lint**: WR/PnL 整合 = 🔴 **1件検出・修正** (上記 strategy page の N=2 vs N=3。他 page の `by_type` 突合は一致。`wiki/index.md` System State は1日 stale → 更新済) / broken `[[link]]` = ⚠️ **118 refs / 76 targets**、うち **57 refs / 31 targets は `feedback_*`・`project_*` の MEMORY slug** (意図的な cross-namespace 参照、KB 破損ではない) ⇒ **真の KB 内破損は約 61 refs / 45 targets** (`feedback_tv_edge_discovery_loop` ×7、`lesson-bt-live-divergence` ×6、`../strategies/{vsg_jpy_reversal,rsk_gbpjpy_reversion,mqe_gbpusd_fix}` は underscore/hyphen 不一致)、慢性・規模不変・**本 run 未修正** (100+ page の一括 rename は別タスク) / stale >3日 = 🔴 equity **24.2日**・learning **14.9日**・`wiki/tier-master.json` `generated_at` **2026-08-03 = 31.2日** (index portfolio は「auto-synced 2026-09-03」と自称し**両者が自身の鮮度で矛盾**)、`tier-master.md`・`edge-pipeline.md` も 08-03 止まり / 偽陽性解除 = `changelog.md` 他の **2026-09-30 は正当な将来 backstop 日**
- **process**: `pgrep -f app.py` → なし (全数値 Render API、`_db_path: /var/data/demo_trades.db`)。audit は task 既定の 30 ではなく **limit=800** で取得 (`feedback_audit_limit30_hides_live_fills`) — 本日はこれが効いた: **agg-Kelly 45行の履歴は全窓でしか見えず、上記 CORRECTION はそれ無しには成立しなかった**。task 記載の4 endpoint に加え `demo/status`・`demo/block-counts`・`oanda/equity`・`oanda/status` を継続追跡のため取得 (計8本すべて HTTP 200)。HEAD **`de21f8ca`** (09-02 は `874fb3c8`)、他ジョブ由来の未 commit 変更4件と stash 5件が併存 ⇒ 全書き込みを **書き込み後にディスク検証** (`feedback_concurrent_agent_repo_hazard`)。**commit/push なし** (`project_fxai_stranded_staged_work_2026_09_01` で凍結中)
- 詳細: [[2026-09-03]]
