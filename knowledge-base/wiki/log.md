# Knowledge Base Change Log

## 2026-04-12: Changelog + Production Snapshot
- Created [[changelog]]: バージョン別タイムライン + 評価基準日マトリクス
- First production snapshot: `raw/trade-logs/snapshot-2026-04-12.md` (250t post-cutoff)
- Updated /wiki-quant-eval: Phase 0で[[changelog]]参照 → 最適なdate_from自動判定
- PnL分解: XAU=-1,657pip, FX=+59.8pip（FXは黒字方向）
- index.mdにData & Evaluationセクション追加

## 2026-04-12: Research Layer + Harness
- Added research pipeline: wiki/research/ (2 themes), wiki/edges/ (pipeline), templates/
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
- [ ] raw/ にBT結果JSONを保存
- [ ] Version history (v7.0 - v8.4) as separate pages
- [ ] /wiki-quant-eval の初回実行でベースライン確立
