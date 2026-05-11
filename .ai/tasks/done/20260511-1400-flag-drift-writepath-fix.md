---
id: 20260511-1400-flag-drift-writepath-fix
title: "[FLAG-DRIFT-FIX] is_shadow=0 で書かれる SCALP_SENTINEL/PAIR_DEMOTED trade を遮断、N=140 metric pollution 解消"
owner: codex
status: queued
priority: P0
created_at: 2026-05-11T14:00:00+0900
roadmap_gate: "Live metric clean 化 (Aggregate Kelly / WR / EV / DSR / volume_watchdog の信頼性回復)。FLAG_DRIFT N=140 PnL=-132.4pip が live signal を歪め、すべての tier 判定の前提を破壊している"
rule: R3
related:
  - modules/demo_trader.py
  - modules/demo_db.py
  - modules/oanda_bridge.py
  - modules/shadow_demote_registry.py
  - knowledge-base/raw/audits/oanda-passthrough-gap-2026-05-03.md
---

# 0. 背景

`is_shadow` write-path drift bug (2026-05-03 audit, 2026-05-07 wiki-daily-update で N=140 / PnL=-132.4pip 確認):

| 集計 (post-cutoff 2026-04-08〜) | N | WR | PnL |
|---|---:|---:|---:|
| Total gross (live+shadow 混合) | 530 | 38.5% | -414.2pip |
| **TRUE_LIVE** (`is_shadow=0 ∧ oanda_trade_id != ''`) | 371 | 39.89% | -254.6pip |
| **FLAG_DRIFT** (`is_shadow=0 ∧ oanda_trade_id = ''`) | **140** | 32.86% | **-132.4pip** |
| SHADOW (`is_shadow=1`) | 3,819 | 23.72% | -4,985.6pip |

audit verdict `FLAG_DRIFT_BUG`:
- 39 行 (snapshot 時点) 全 `bb_rsi_reversion × scalp` の SCALP_SENTINEL/PAIR_DEMOTED cell
- これらは **意図的に shadow tier** であるべきだが `is_shadow=0` で書かれて live aggregate を汚染
- OANDA bridge は正常 (bridge_status='blocked' or 'skipped' で OANDA に送らない)、データ層の write が誤って `is_shadow=0` をセット

影響:
- Aggregate Kelly raw=-0.69 (TRUE_LIVE only) → -1.x (FLAG_DRIFT 含む)
- `/api/risk/dashboard` の WR/edge/PF 全 cell で過小評価
- `volume_live_promotion_watchdog.py` の Live N 判定が信頼できない (post-promotion N count にも紛れる可能性)
- `tier_live_drift.py` 等の監査ツールも歪み

# 1. 仕様

## 1.1 Schema reference (Codex hallucination 防止、貼り付け必須)

`demo_trades` table (`modules/demo_db.py` 参照):

```sql
CREATE TABLE IF NOT EXISTS demo_trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id        TEXT NOT NULL UNIQUE,
    entry_time      TEXT,
    exit_time       TEXT,
    entry_price     REAL,
    exit_price      REAL,
    entry_type      TEXT,
    direction       TEXT,
    instrument      TEXT,
    confidence      REAL,
    regime          TEXT,
    pnl_pips        REAL,
    outcome         TEXT,
    mode            TEXT,
    is_shadow       INTEGER DEFAULT 1,  -- ← 問題の列
    oanda_trade_id  TEXT DEFAULT '',
    ...
    created_at      TEXT DEFAULT (datetime('now'))
);
```

`oanda_audit` table (commit 364027e で SR 5 列追加済):

```sql
CREATE TABLE IF NOT EXISTS oanda_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    demo_trade_id   TEXT,
    entry_type      TEXT,         -- bridge_status='sent'=戦略名, 'filled'=MODE 名 (memory: oanda_audit.entry_type 二義性)
    direction       TEXT,
    instrument      TEXT,
    units           INTEGER DEFAULT 0,
    is_live         INTEGER DEFAULT 0,
    bridge_status   TEXT,         -- 'sent' / 'filled' / 'blocked' / 'skipped'
    block_reason    TEXT DEFAULT '',
    oanda_trade_id  TEXT DEFAULT '',
    created_at      TEXT,
    sr_strength     REAL,
    sr_touches      INTEGER,
    sr_days_span    REAL,
    sr_is_strong    INTEGER,
    sr_distance_atr REAL
);
```

## 1.2 Root cause 探索 (Phase A — read-only forensic)

Render production DB 直接アクセス不可ならば、`knowledge-base/raw/snapshots/render-demo-trades-20260503.db` を一次ソースとする。

以下 forensic SQL を実行し、最新 FLAG_DRIFT 群 (post-cutoff 2026-04-08) の全体像を取得:

```sql
-- FLAG_DRIFT cohort breakdown
SELECT entry_type, mode, instrument, COUNT(*) AS n, SUM(pnl_pips) AS pnl
FROM demo_trades
WHERE is_shadow = 0
  AND (oanda_trade_id IS NULL OR oanda_trade_id = '')
  AND entry_time >= '2026-04-08T00:00:00'
GROUP BY entry_type, mode, instrument
ORDER BY n DESC;

-- Bridge status correlation
SELECT
  d.entry_type, d.mode, d.is_shadow,
  CASE WHEN d.oanda_trade_id != '' THEN 'sent' ELSE 'blank' END AS oanda_id_state,
  a.bridge_status, a.block_reason,
  COUNT(*) AS n
FROM demo_trades d
LEFT JOIN oanda_audit a ON a.demo_trade_id = d.trade_id
WHERE d.is_shadow = 0
  AND (d.oanda_trade_id IS NULL OR d.oanda_trade_id = '')
  AND d.entry_time >= '2026-04-08T00:00:00'
GROUP BY d.entry_type, d.mode, d.is_shadow, oanda_id_state, a.bridge_status, a.block_reason
ORDER BY n DESC
LIMIT 50;
```

期待結果: bridge_status は 'blocked' / 'skipped' 系が多いはず。**OANDA bridge 自体は正常に弾いている、demo_trade insert path が誤って is_shadow=0 を書いている**ことを実測確認。

## 1.3 Write-path 監査 (Phase B — code trace)

`modules/demo_trader.py` の **demo_trade INSERT 経路全て** を列挙し、`is_shadow` 値の決定ロジックを追跡:

候補:
- `_tick_entry()` (signal -> trade insert path)
- `_shadow_emit_signals()` (shadow tracking insert path)
- `shadow_demote_registry.is_shadow_demoted()` の呼び出し位置 (commit 0208ba8 で導入)
- tier 判定 (`_FORCE_DEMOTED`, `_PAIR_DEMOTED`, `_SCALP_SENTINEL`, `_PHASE0_SHADOW`) と `is_shadow` 紐付け箇所

期待される正解:
- SCALP_SENTINEL / PAIR_DEMOTED / FORCE_DEMOTED / PHASE0_SHADOW のいずれかに該当する cell の trade は **必ず `is_shadow=1`** で書く
- ELITE_LIVE / PAIR_PROMOTED かつ OANDA bridge_status='filled' のもののみ `is_shadow=0`

判明 bug の修正:
1. write 前の tier 判定 path (どの分岐で `is_shadow=0` が誤設定されるか) を特定
2. defensive guard を追加: `oanda_trade_id == ''` の場合は強制的に `is_shadow=1` で書く (R3 algebraic safeguard)

## 1.4 修正実装 (Phase C — fix)

最小変更で:
- `modules/demo_trader.py` の `is_shadow` 決定 path に対し:
  1. tier resolution (`_resolve_tier(entry_type, instrument, mode)`) helper を作成 (既存ロジックを集約)
  2. SHADOW tier 群の場合は `is_shadow=1`、それ以外は OANDA bridge 結果 (`bridge_status='filled' ∧ oanda_trade_id != ''`) で `is_shadow=0`
  3. ambiguous (bridge='sent'だがまだ filled 未確認) の場合は `is_shadow=1` で書き、後段 reconciler で更新する設計が安全
- `modules/demo_db.py` の `insert_demo_trade()` (または相当関数) に invariant assertion: `is_shadow==0 → oanda_trade_id != ''`

## 1.5 Backfill (Phase D — optional, separate commit)

歴史データ (FLAG_DRIFT N=140) の retroactive 補正:

```sql
-- 識別と更新 (production deploy 後に Render shell で手動実行、本タスクでは spec のみ)
UPDATE demo_trades
SET is_shadow = 1
WHERE is_shadow = 0
  AND (oanda_trade_id IS NULL OR oanda_trade_id = '')
  AND entry_time >= '2026-04-08T00:00:00'
  AND id IN (SELECT id FROM demo_trades WHERE ...);
```

**注**: backfill は本タスクの commit に含めない。司令塔判断で別 PR / Render shell で実行。Production DB 直接 UPDATE は dry-run 必須。

## 1.6 テスト (Phase E)

- `tests/test_flag_drift_writepath.py` 新規:
  1. SCALP_SENTINEL cell の signal → `is_shadow=1` で write されることを assert
  2. PAIR_DEMOTED cell の signal → `is_shadow=1` で write されることを assert
  3. FORCE_DEMOTED cell の signal → `is_shadow=1` で write されることを assert
  4. ELITE_LIVE cell の filled OANDA fill → `is_shadow=0 ∧ oanda_trade_id != ''` で write されることを assert
  5. ELITE_LIVE cell の OANDA blocked (sent → blocked) → `is_shadow=1` で write されることを assert (defensive: filled 未確認 = shadow 扱い)
  6. demo_db invariant: `is_shadow==0 ∧ oanda_trade_id==''` の insert は AssertionError or rejected

E2E 確認:
- production-like fixture でフロー全体 (signal emit → bridge call → DB insert) が正しい組合せを書くか mock-free で検証

## 1.7 Acceptance gate

ACCEPT 条件 (Codex 規律):
1. Phase A forensic SQL が `entry_type='bb_rsi_reversion'` (or 該当 cell) で write-path drift を実測確認
2. Phase B で write-path drift の正確な code location を特定 (file:line で報告)
3. Phase C の修正 PR で既存 92+ tests が green
4. Phase E の新規 6 tests が pass
5. integrated regression: `pytest tests/ -x -q` で fail 0

不通過 → commit せず `final.md` に CHANGES_REQUESTED 報告。

## 1.8 Push 判断

- ACCEPT → commit + push origin main (Render auto-deploy)
- 司令塔は post-deploy 24h で `/api/risk/dashboard` の N total が変動しないこと、FLAG_DRIFT 新規発生が止まることを確認

# 2. クオンツチェック (Codex 自己検証)

`feedback_partial_quant_trap` 規律:
- 修正前後で TRUE_LIVE N (is_shadow=0 ∧ oanda_trade_id != '') が変化しないこと
- 修正により FLAG_DRIFT が is_shadow=1 へ流れ、SHADOW N が +140 程度増えること
- Aggregate Kelly raw が **改善方向** (FLAG_DRIFT の -0.93 mean が live 集計から外れる) であること

`feedback_live_shadow_separation` 規律:
- forensic 集計時に is_shadow=0/1/blank 全 cohort を明示分離して報告
- 集計 SQL で `oanda_trade_id != ''` 必須

# 3. 関連 memory / pre-reg

- `feedback_codex_schema_hallucination` — schema 直貼 (本タスク §1.1)
- `feedback_codex_mock_test_trap` — E2E 検証必須 (本タスク §1.6)
- `feedback_check_orphan_local_app` — Render API 一次ソース、ローカル DB は forensic snapshot 限定使用
- `feedback_live_shadow_separation` — is_shadow=0 集計時の shadow 混入禁止
- `oanda_audit.entry_type 二義性` — bridge_status='sent'=戦略名 / 'filled'=MODE 名、GROUP BY 前に分離

# 4. 失敗時 fallback

- Phase A で FLAG_DRIFT cohort が tier-shadow 紐付けで説明できない場合 → write-path 以外の bug (OANDA bridge 障害) の可能性、別 task で深掘り
- Phase C 修正で既存 test が fail → 既存 invariant 違反、Claude 司令塔に上申
