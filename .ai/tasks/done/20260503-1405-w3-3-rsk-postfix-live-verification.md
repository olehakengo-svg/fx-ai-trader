---
id: 20260503-1405-w3-3-rsk-postfix-live-verification
title: W3-3 — rsk_gbpjpy_reversion Post-Fix Live Verification + Memory Closure (Rule R3)
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T14:05:00+0900
roadmap_gate: Gate 0 (生存 — runaway 損失再発防止の実弾エビデンス)
rule: R3
---

# Objective

`strategies/daytrade/rsk_gbpjpy_reversion.py` に 2026-04-30 commit で投入された
**per-bar dedup gate (rule:R3)** が、**Render 本番の Shadow 流路で実際に runaway 発火を止めているか**を
実測データで確定する。memory `project_rsk_gbpjpy_bar_close_gate_pending` を「fixed + verified」に
更新するための **forensic evidence** を生成する。

実装変更は **行わない** (verification only)。新たな構造バグが発見された場合のみ Rule R3 patch を提案。

# Context

- 2026-04-30 shadow-audit-2026-04-30.md: 単日 76 件発火 / 中央値 35.7s 間隔 / 76/76 全敗 / -813.7p
- 同日 commit でテンプレ修正 (closed_idx = -2 for live, `_last_emit_bar_ts` per-bar dedup, `(symbol, direction)` キー)
- regression test `tests/test_phase5_strategies.py::TestRskGbpjpyReversion::test_per_bar_dedup_blocks_repeat` は green
- ただし **Live polling × in-progress bar 環境での実挙動は未測定**
- memory は 2日 stale で「未修正 R3 pending」のまま — 司令塔の判断材料を歪めている
- Rule 3: 構造バグ verification は 365日BT スキップ可。実弾エビデンスベース

# Hypothesis

**H0**: 修正 commit 投入後 (2026-04-30 22:00 UTC 以降と仮定、git log で確定する)、
rsk_gbpjpy_reversion は **同一 closed bar 内の重複 emit を 0 件に抑制している**。
- Per-bar dedup violation rate (90秒未満間隔の同方向連発) が修正前 vs 修正後で統計的に有意に減少
- runaway cluster (n≥5/15min) が消滅
- Shadow PnL 寄与が改善 (or 少なくとも phantom losses が混入していない)

**H1 (alternative)**: 修正後も 90秒未満間隔の連発が残存している場合、
- (a) demo_trader レイヤで dedup gate がバイパスされている
- (b) `(ctx.symbol, signal)` の symbol 表記揺れ (例 `GBPJPY=X` vs `GBP_JPY`) で dedup_key が分裂
- (c) `bar_id` が None になる経路がある (df.index が DatetimeIndex でない等)
のいずれか → 追加 Rule R3 patch 提案

# 対象データ

- **Render 本番 API** が一次ソース ([feedback_check_orphan_local_app] 準拠、ローカル DB は二次)
  - エンドポイント: `https://fx-ai-trader.onrender.com/api/demo/trades?strategy=rsk_gbpjpy_reversion`
  - 期間: 2026-04-25 ～ 2026-05-03 (修正前後で対称的に各 5日以上)
- **commit log**: `git log --oneline --all -- strategies/daytrade/rsk_gbpjpy_reversion.py`
  で per-bar dedup commit の正確な merge 時刻を確定 (cutoff として使用)
- ローカル parquet キャッシュ (`data/cache/massive/`) は不可 — Live 流路は本番のみ

# データ分離 (混入禁止)

- **is_shadow=1 のみ集計** (rsk_gbpjpy_reversion は Phase0 Auto-Shadow): `oanda_trade_id` は空のはず。
  もし空でない行があれば即時警告 (PAIR_PROMOTED 想定外昇格の検知)
- **is_shadow=0 / Live 本流** とは絶対に混ぜない ([feedback_live_shadow_separation] 準拠)
- BT データ・OANDA 実弾データとは別軸で集計 (cross-contamination 検出)
- pair は `GBP_JPY` のみ (戦略の `_ALLOWED_SYMBOLS = {"GBPJPY"}`)

# 統計条件

| 指標 | 定義 | ACCEPT 閾値 (post-fix) |
|---|---|---|
| **inter-entry gap median** | 同方向連発の中央値秒数 | ≥ 900s (= 1 closed 15m bar) |
| **<90s gap rate** | 同方向連発のうち間隔 90秒未満の比率 | ≤ 5% (修正前 ≥ 80%) |
| **cluster size p95** | 15分窓内の最大連続発火数 p95 | ≤ 1.0 (= dedup 完全動作) |
| **N (post-fix)** | 修正後の総発火数 | 比較可能になる程度: 任意 (主指標は rate) |
| **Wilson lower 95%** | <90s gap rate の Wilson 下限 | < 10% (修正前 60% 超を想定) |
| **runtime** | スクリプト実行時間 | ≤ 5 min (Render API のみ叩く) |

# ACCEPT / NEEDS_MORE_EVIDENCE / REJECT

- **ACCEPT (= memory closure)**:
  - <90s gap rate ≤ 5% かつ Wilson lower < 10%
  - cluster size p95 ≤ 1.0
  - is_shadow=0 への混入 0 件
  - → memory `project_rsk_gbpjpy_bar_close_gate_pending` を「FIXED & VERIFIED 2026-05-03」に書き換え提案 (実書き換えは Claude 司令塔)
- **NEEDS_MORE_EVIDENCE**:
  - 修正後 N が 7日間で 10 未満 (signal が単に出ていないだけかも)
  - → 観測期間延長の提案。memory 更新は保留
- **REJECT (= 追加修正必要)**:
  - <90s gap rate > 5% or cluster p95 > 1.0
  - → H1 (a/b/c) のどれが原因か forensic で特定 (demo_trader レイヤ / symbol 揺れ / bar_id None)
  - → Rule R3 follow-up task の素案を `final.md` に書く (実装はしない)

# 受入条件

1. `final.md` に以下を含む:
   - 修正 commit の merge 時刻 (UTC)
   - pre-fix vs post-fix の <90s gap rate / cluster p95 / inter-entry gap median 比較表
   - is_shadow=0 への混入チェック結果
   - ACCEPT/NEEDS_MORE_EVIDENCE/REJECT 判定とその根拠
2. forensic スクリプトを `.ai/runs/<this-run>/rsk_postfix_audit.py` に保存 (再現可能)
3. memory 更新提案文 (Claude 司令塔がそのまま貼り付けられる Markdown)
4. REJECT の場合は H1 原因仮説 1〜複数 + 次の Rule R3 task 素案

# 検証コマンド

```bash
# 1. commit log で per-bar dedup 投入時刻を確定
cd /Users/jg-n-012/test/fx-ai-trader
git log --oneline --all --follow -- strategies/daytrade/rsk_gbpjpy_reversion.py | head -10

# 2. 既存 regression test green 確認 (改変していないこと)
python3 -m pytest tests/test_phase5_strategies.py::TestRskGbpjpyReversion -v

# 3. forensic スクリプト実行 (Render API 直叩き)
python3 .ai/runs/<this-run>/rsk_postfix_audit.py \
  --start 2026-04-25 --end 2026-05-03 \
  --cutoff "<commit merge time UTC>" \
  --out .ai/runs/<this-run>/rsk_postfix_metrics.json

# 4. final.md 整形
ls .ai/runs/<this-run>/final.md
```

# 禁止事項

- **本番 DB へ書き込みクエリ発行禁止** (read-only)
- **`.env` / OANDA API キー / Render API キーの export, echo, 出力ファイルへの書き込み禁止**
- 既存の **未コミット変更を破壊しない** (git stash 等で必ず保存してから作業)
- `strategies/`, `modules/`, `app.py` への **コード変更禁止** (verification only タスク)
- `knowledge-base/wiki/**` への **書き込み禁止** (Claude 司令塔が更新する)
- ローカル `app.py` プロセスの kill 禁止 (`pgrep -f app.py` で確認のみ。orphan 検出時は警告のみ)

# 月利100%ロードマップへの寄与

- **Gate 0 (生存)**: -813.7p phantom losses の **再発防止が実証済みであることを確定**。
  Defensive 0.2x 解除条件 ([defensive-mode-unwind-rule]) の前提条件のうち
  「構造バグ起因の Live 損失が止まっていること」を裏取り。
- **Gate 1 への波及**: rsk_gbpjpy_reversion は Bonferroni 13通過の Phase 5 戦略 (`__init__.py:203`)。
  per-bar dedup が機能していれば Shadow 経由で Pre-reg LOCK → Shadow promote の検討に進める。
  逆に REJECT なら Phase 5 全体の Live 露出は Rule R2 で抑制継続。
- 司令塔の判断遅延コスト削減: stale memory による誤判 (cf. observation 1062 USDJPY 全 fail と同種の罠) を解消。

# Required Reading

- `strategies/daytrade/rsk_gbpjpy_reversion.py` (per-bar dedup 実装本体)
- `tests/test_phase5_strategies.py` (regression test 構造)
- `knowledge-base/wiki/decisions/shadow-audit-2026-04-30.md` (pre-fix エビデンス)
- `modules/demo_trader.py:2780-2860` 付近 (runner レイヤ dedup の有無)
- `modules/demo_db.py:485-510` 付近 (60s dedup gate の戦略リスト)
- `CLAUDE.md` クオンツ判断プロトコル (Rule 3 の 365d BT スキップ条件)

# Notes

- このタスクは **memory 更新の前提エビデンスを作る** ことが目的。
  Codex は memory を直接書き換えない (Claude 司令塔の責務)。
- ACCEPT 後の follow-up: `[rsk_gbpjpy_bar_close_gate_pending]` memory を closure に書き換え、
  Phase 5 全戦略の per-bar dedup 整合スキャンを Rule R3 で別タスク化。
