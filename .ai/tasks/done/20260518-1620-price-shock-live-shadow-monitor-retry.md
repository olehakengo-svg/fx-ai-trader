---
id: 20260518-1620-price-shock-live-shadow-monitor-retry
title: "[Price-Shock Live Shadow Monitor RETRY] 5 戦略の Live shadow trade を週次集計し promote/demote 基準を自動判定する CLI"
owner: codex
status: queued
priority: P2
created_at: 2026-05-18T14:57:00+0900
roadmap_gate: "Phase B-1 (commit 35961351) で Tier 1 family 5 戦略 (price_shock_rev_*_h1_long) を Shadow 投入。Live promote 基準は decisions/price-shock-rev-promote-criteria-2026-05-18.md に LOCK 済 (N>=30 / Wilson_lo>=0.50 / Bonferroni m=5 p<0.01 / 6 週連続 EV>0 / EUR_GBP×EUR_AUD shared lock)。手動チェックでは 5 戦略 × 4-8 週 = 20-40 個の判断ポイントが発生するため自動化必須。本 task は demo_db (or production demo DB) から is_shadow=1 trade を集計し、5 戦略別の 5 基準達成状況を一覧表示する CLI を実装する。Live promote / demote の最終判断は司令塔が手動で行うが、判定材料を 1 コマンドで揃える。"
rule: implementation
related:
  - knowledge-base/wiki/decisions/price-shock-rev-promote-criteria-2026-05-18.md
  - strategies/hourly/price_shock_reversion_base.py
  - strategies/hourly/__init__.py
  - modules/demo_db.py
  - modules/demo_trader.py
  - tools/sync_kb_index.py
  - feedback_label_empirical_audit
  - feedback_live_shadow_separation
  - feedback_partial_quant_trap
  - feedback_codex_mock_test_trap
  - feedback_codex_stash_leak
  - feedback_cohort_time_check
  - project_w3_1_h1_gate_done_2026_05_03
---

# 0. 背景

Phase B-1 で 5 戦略 (`price_shock_rev_{eur_gbp,eur_aud,usd_cad,nzd_jpy,aud_jpy}_h1_long`) を Shadow 投入。pre-reg LOCK で **Live promote/demote 基準** が確定:

## Promote (全項目満たして司令塔提案)
1. Live shadow N >= 30 (closed trades)
2. Shadow Wilson_lo(95%) >= 0.50
3. Bonferroni m=5 で raw p < 0.05/5 = 0.01
4. 6 週連続 EV > 0 (週次集計)
5. EUR_GBP × EUR_AUD shared lock 違反 0 (`eur_base_shock_lock` block ログ確認)

## Demote (即降格)
- N=15 時点で Wilson_lo < 0.40 → Shadow 内 deactivate 提案
- 2 週連続 EV < 0 (週次) → 緊急 review
- catastrophic SL hit (`sl_2atr`) 比率 > 30% → 戦略構造再検討

# 1. 実装仕様

## 1.1 出力ツール: `tools/price_shock_live_shadow_monitor.py`

CLI 仕様:

```bash
python3 tools/price_shock_live_shadow_monitor.py [--weeks N] [--db PATH] [--strategy NAME] [--json]
```

オプション:
- `--weeks N`: 集計対象週数 (default 6、最低 1 / 最大 26)
- `--db PATH`: demo DB path (default `demo_data.db` or 本番 mirror)
- `--strategy NAME`: 1 戦略のみフィルタ (default 全 5 戦略)
- `--json`: JSON 出力 (default は table 形式)

## 1.2 集計クエリ (LIVE/Shadow 分離必須、feedback_live_shadow_separation)

```sql
-- 各戦略について
SELECT
  entry_type AS strategy,
  COUNT(*) AS n_total,
  SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) AS n_closed,
  SUM(CASE WHEN status='closed' AND pnl_pips > 0 THEN 1 ELSE 0 END) AS wins,
  AVG(CASE WHEN status='closed' THEN pnl_pips END) AS avg_pnl,
  SUM(CASE WHEN close_reason='sl_2atr' THEN 1 ELSE 0 END) AS sl_hits,
  SUM(CASE WHEN close_reason='horizon' THEN 1 ELSE 0 END) AS horizon_exits
FROM trades
WHERE
  is_shadow = 1                          -- ← 重要: Shadow only
  AND entry_type LIKE 'price_shock_rev_%_h1_long'
  AND opened_at >= datetime('now', '-{weeks * 7} days')
GROUP BY entry_type;
```

**🔴 Critical (`feedback_live_shadow_separation`)**: `is_shadow=1` を **必ず WHERE 句に入れる**。混入で景色が反転する (2026-04-30 監査参照)。

## 1.3 統計指標計算 (feedback_partial_quant_trap)

各戦略について以下を **すべて** 計算 (部分的 quant 禁止):

| 指標 | 定義 |
|---|---|
| N | closed shadow trade 数 |
| WR | wins / N |
| Wilson lower (95%) | scipy.stats.binom or scratch (k=wins, n=N, alpha=0.05) |
| EV pips | mean(pnl_pips for closed) |
| EV % | mean(pnl_pips * pip_value / equity) — equity 不明なら省略可、ただし pip ベース必須 |
| PF | sum(positive pnl) / abs(sum(negative pnl)) |
| Kelly | (WR - (1-WR)/avg_win/avg_loss) — closed_form |
| Bonferroni p | binomial test p-value × 5 (family-wise) |
| SL hit ratio | `close_reason='sl_2atr'` count / N |
| Horizon exit ratio | `close_reason='horizon'` count / N |
| 6 週連続 EV>0 | 週次 EV を計算し直近 6 週連続 >0 判定 |

## 1.4 Promote/Demote 判定

各戦略について 5 promote 基準と 3 demote 基準を **個別評価** し以下 status を出す:

| Status | 条件 |
|---|---|
| `PROMOTE_READY` | 5 promote 基準全 PASS |
| `PROMOTE_PENDING` | 1-2 基準未達 (収集継続) |
| `DEMOTE_DEACTIVATE` | N>=15 で Wilson_lo<0.40 |
| `DEMOTE_REVIEW` | 2 週連続 EV<0 |
| `DEMOTE_STRUCTURE` | SL hit ratio > 30% |
| `COLLECTING` | N < 15 で他基準も未達 |

複数 demote 条件 hit なら最も severe を選ぶ (DEACTIVATE > STRUCTURE > REVIEW)。

## 1.5 EUR_GBP × EUR_AUD shared lock 違反監査

```sql
-- eur_base_shock_lock 違反ログを demo_db.events or audit table から拾う
SELECT COUNT(*) FROM events
WHERE event_type='trade_blocked'
  AND reason LIKE 'eur_base_shock_lock%'
  AND created_at >= datetime('now', '-{weeks * 7} days');
```

block 回数 (正常動作の証拠) と、もし両戦略が同時 open している (lock 失敗) なら critical alert を出す。

## 1.6 時間コホート整合監査 (`feedback_cohort_time_check`)

集計が「歴史値」か「現在値」かを混同しない。週次集計テーブルでは:
- 各週の `(N_week, WR_week, EV_week)` を計算
- 「現状」table は最新 N週 cumulative
- 「履歴」table は週ごと breakdown

両方を出力し、コホート時系列を明示する。

## 1.7 出力例 (Table 形式)

```text
================================================================
Price-Shock Reversion Tier 1 — Live Shadow Monitor
集計期間: 2026-05-18 ← 6 週 (2026-04-06 ~ 2026-05-18)
================================================================

Strategy                              N    WR     Wilson_lo  PF    Kelly  EV(p)   Bonf_p    SL_hit  Status
price_shock_rev_eur_gbp_h1_long       12   58.3%  0.319      1.45  0.21   +2.4    0.412     0.0%    COLLECTING
price_shock_rev_eur_aud_h1_long       8    50.0%  0.215      1.12  0.05   +0.8    0.638     12.5%   COLLECTING
price_shock_rev_usd_cad_h1_long       10   60.0%  0.314      1.32  0.18   +1.9    0.376     10.0%   COLLECTING
price_shock_rev_nzd_jpy_h1_long       6    66.7%  0.299      2.10  0.31   +5.2    0.345     0.0%    COLLECTING
price_shock_rev_aud_jpy_h1_long       14   57.1%  0.330      1.21  0.14   +1.3    0.398     7.1%    COLLECTING

EUR base shock lock blocks: 3 (lock working, no violation)

週次 breakdown (直近 6 週):
Week        eur_gbp_N  eur_gbp_EV  eur_aud_N  ...
2026-05-12  3          +4.2         2          +1.5  ...
2026-05-05  2          +1.8         1          -0.3  ...
...

[Promote criteria status]
- N >= 30: 0/5 strategies
- Wilson_lo >= 0.50: 0/5 strategies
- Bonferroni m=5 p < 0.01: 0/5 strategies
- 6 weeks EV > 0: 5/5 strategies (collecting...)
- Shared lock violations: 0
→ No strategy promote-ready yet (expected: 4-8 weeks shadow ramp).

[Demote criteria check]
All clear (N too low for demote evaluation).
```

# 2. 完了条件

1. `tools/price_shock_live_shadow_monitor.py` 実装 (上記仕様)
2. `tests/test_price_shock_live_shadow_monitor.py` 新規 (real demo_db + synthetic trade insert / mock 禁止)
3. **テスト case (mock 禁止、`feedback_codex_mock_test_trap`)**:
   - Empty DB → "No data" 出力
   - N=10 with WR=50% → COLLECTING 判定
   - N=35 with WR=60% Wilson_lo=0.45 (1 基準未達) → PROMOTE_PENDING
   - N=35 with WR=70% Wilson_lo=0.55 + 6 週 EV>0 + Bonferroni p<0.01 → PROMOTE_READY
   - N=20 with Wilson_lo=0.35 → DEMOTE_DEACTIVATE
   - is_shadow=0 trade 混入 → 集計から除外確認
   - LIKE 'price_shock_rev_%_h1_long' フィルタで他戦略除外確認
   - EUR_GBP / EUR_AUD 同時 open があれば shared_lock_violation count > 0
4. 出力フォーマット 2 種類 (table / JSON) 両方テスト
5. README / docstring に Render shell での実行手順を明記:
   ```bash
   # Render shell で本番 demo_db を mirror して集計
   python3 tools/price_shock_live_shadow_monitor.py --weeks 6
   ```
6. commit + push、`git status` clean、`git stash list` clean (`feedback_codex_stash_leak`)
7. `python3 tools/sync_kb_index.py --write` 不要 (戦略追加なし)、ただし `knowledge-base/wiki/index.md` の System State section に monitor ツール所在を 1 行追記

# 3. 司令塔ガード

- [ ] **`is_shadow=1` WHERE 句必須** (`feedback_live_shadow_separation`): is_shadow=0 (Live) 混入で景色反転 — 2026-04-30 監査の再発を絶対回避
- [ ] **全 quant 指標を出す** (`feedback_partial_quant_trap`): N/WR/EV だけでは不十分、PF/Wilson CI/Bonferroni/Kelly/SL ratio 全て必須
- [ ] **時間コホート整合** (`feedback_cohort_time_check`): cumulative と週次 breakdown 両方出力、混同禁止
- [ ] **ラベル実測** (`feedback_label_empirical_audit`): WR/Wilson_lo は実 SQL 集計、コード演繹禁止
- [ ] **mock 禁止** (`feedback_codex_mock_test_trap`): real DB 接続 / synthetic insert で 8 case 検証
- [ ] **stash 漏れ禁止** (`feedback_codex_stash_leak`): 完了時 `git stash list` 確認
- [ ] **本番 DB 改変禁止**: 本ツールは READ-ONLY (SELECT のみ)、INSERT/UPDATE/DELETE 一切なし
- [ ] **本番 demo_db を破壊しないこと**: Render shell 実行時の DB lock / connection leak 注意、`with sqlite3.connect()` context manager 必須
- [ ] **Promote 自動化禁止**: 本ツールは **判定材料を出すだけ**、tier-master.md / OANDA_EXECUTION_ENABLED / is_shadow flag 自動変更は **絶対禁止**。司令塔が手動 review 後 別 Codex task で promotion を実行する

# 4. final.md

完了時 `.ai/tasks/queue/20260518-1457-price-shock-live-shadow-monitor-final.md` に出力:
- 実装ファイル一覧
- `git diff --stat HEAD~1`
- `python3 -m pytest tests/test_price_shock_live_shadow_monitor.py -v` 全 PASS 出力
- 空 DB / 仮想 N=35 PROMOTE_READY ケースの実行サンプル出力
- Render shell 実行手順 1 行
- Known limitations (例: 本番 demo_db への直接 SQLite アクセス不可なら API 経由案を提示)

# 5. Verdict matrix

| 結果 | 条件 |
|---|---|
| **ACCEPT** | 1-7 全達成、8 case test 全 PASS、is_shadow フィルタ実 SQL で検証、全 quant 指標出力、Promote 自動化なし、stash clean |
| **PARTIAL** | 一部 case 未テスト or 出力フォーマット片方のみ |
| **REJECT** | is_shadow フィルタなし / mock-only test / tier-master 自動変更 / 部分 quant のみ / stash 漏れ |

# 6. 期待実行時間

1.5-2 時間 (SQL クエリ ~30min + 統計指標 ~30min + test 8 case ~30min + 出力フォーマット ~20min + commit ~10min)

# 7. 関連 commit / memory

- Phase B-1 strategy 実装: commit `35961351`
- Live promote criteria: `knowledge-base/wiki/decisions/price-shock-rev-promote-criteria-2026-05-18.md`
- memory `feedback_live_shadow_separation` (2026-04-30 監査の根拠)
- memory `feedback_partial_quant_trap` (PF/Wilson/Bonferroni/Kelly 要求)
- memory `feedback_label_empirical_audit` (コード演繹禁止)
- memory `feedback_cohort_time_check` (時系列整合)
- memory `feedback_codex_mock_test_trap` (E2E test 必須)
- memory `feedback_codex_stash_leak` (stash 確認必須)
- memory `project_w3_1_h1_gate_done_2026_05_03` (H1 Gate 30/0.40/0.0 数値の参照値)




## Result (2026-05-18T07:44:05Z)

exit=0 · 367s

```
実装、テスト、commit/push まで完了しました。

Commit: `e97e6ce7 feat: add price shock live shadow monitor`

主な変更:
- [tools/price_shock_live_shadow_monitor.py](/data/repo/fx-ai-trader/tools/price_shock_live_shadow_monitor.py)
  - `is_shadow = 1` をSQL WHERE句に固定
  - table / JSON 出力
  - Wilson、PF、Kelly、raw/binomial p、Bonferroni p、SL/horizon ratio、週次EV cohort、shared lock監査
  - Promote/Demote status 判定のみ。promotion自動変更なし
- [tests/test_price_shock_live_shadow_monitor.py](/data/repo/fx-ai-trader/tests/test_price_shock_live_shadow_monitor.py)
  - mockなし、SQLite demo DB + synthetic insert で指定ケース検証
- [README.md](/data/repo/fx-ai-trader/README.md)
  - Render shell 実行手順追記
- [knowledge-base/wiki/index.md](/data/repo/fx-ai-trader/knowledge-base/wiki/index.md)
  - System State に monitor 所在を1行追記
- [.ai/tasks/queue/20260518-1457-price-shock-live-shadow-monitor-final.md](/data/repo/fx-ai-trader/.ai/tasks/queue/20260518-1457-price-shock-live-shadow-monitor-final.md)
  - 実装ファイル、diff stat、pytest結果、サンプル出力、Known limitations を記録

検証:
```text
PATH="$PWD/.venv/bin:$PATH" python3 -m pytest tests/test_price_shock_live_shadow_monitor.py -v
9 passed in 2.71s
```

追加確認:
- `python3 -m py_compile tools/price_shock_live_shadow_monitor.py` 成功
- `git diff --stat HEAD~1` は final.md 記載と一致
- `git status --short` clean
- `git stash list` clean
- `git push` 完了済み main -> main
```
