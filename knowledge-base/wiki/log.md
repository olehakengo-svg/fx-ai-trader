# Knowledge Base Change Log

## 2026-04-22: JPY cross + Scalp fresh BT + divergence v3 full-stack
- **BT 完了**: EUR_JPY/GBP_JPY/EUR_GBP 365d × 15m DT (5862s) / 6 pairs × 180d × {1m,5m} Scalp (7744s)
- **BT 結果 JSON**: `raw/bt-results/bt-365d-jpy-2026-04-22.json` / `raw/bt-results/bt-scalp-180d-2026-04-22.json` 作成
- **強エッジ発見**: `vwap_mean_reversion × GBP_JPY` N=267 EV=+1.025 PnL=+273.7pip ★最強/ `× EUR_JPY` N=223 EV=+0.672 PnL=+149.9pip — いずれも現在 PAIR_PROMOTED 未登録
- **Scalp scope 構造**: DT_15m EV=+0.217 vs Scalp_1m EV=-0.288 / Scalp_5m EV=-0.115 (GBPJPY 5m のみ正 EV +0.034)
- **構造バグ発見**: `app.py:8276` `htf_agreement` 未定義 → `_compute_scalp_signal_v2` で NameError → Scalp vwap_mr trades=0 (即修正 GO 候補、lesson-reactive-changes 下で次セッションに委譲)
- **divergence v3**: is_shadow=0 Kelly-clean baseline (Live N=412) で Bonferroni 有意なし — v2 (mixed Live N=2505) で有意だった sr_fib_confluence/sr_break_retest × USD_JPY は power loss で再現せず
- **wiki 更新**: `sessions/bt-live-divergence-scan-2026-04-22.md` §8 appendix 追加 / `sessions/bt-live-divergence-v3-full-stack-2026-04-22.md` 新規 / `index.md` BT Results link 追加
- **Lint**: `[[bt-live-divergence]]` → `analyses/bt-live-divergence.md` 既存 OK、新規 2 session page を index.md BT Results に追加して孤立解消、破損リンクなし
- **Next**: (1) htf_agreement バグ修正 → Scalp BT 再実行、(2) `vwap_mean_reversion × EUR_JPY/GBP_JPY` audit-c 発議、(3) Live N≥20 到達後に v3 Bonferroni 再計算

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
