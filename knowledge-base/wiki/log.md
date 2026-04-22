# Knowledge Base Change Log

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
