# Knowledge Base Change Log

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
