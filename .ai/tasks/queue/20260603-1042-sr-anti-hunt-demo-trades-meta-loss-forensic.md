---
id: 20260603-1042-sr-anti-hunt-demo-trades-meta-loss-forensic
priority: P0
gate: R3
rule: R3
status: queued
created: 2026-06-03
owner: claude
---

# sr_anti_hunt_bounce demo_trades メタデータ消失 — 原因特定と修復

**Rule classification**: R3 (Immediate — 構造バグ。SR-weight Phase 2 promotion の前提となる
cell/SR/MTF/spread axis が demo_trades 上で 85〜100% 欠損しており、`fx-ai-edge-cell-watchdog`
(15min cron) は cell_id 不明のまま動作中。production の `pyarrow/fastparquet` ImportError も
shadow 61% で発生しており、confluence engine が `"MIXED"` 固定で機能していない。
[[wiki/lessons/lesson-cell-audit-bt-required-2026-04-27]] に従い数学/code derivation を伴う
即時修正対象。)

## Context — 2026-06-03 audit findings (claude session)

`/api/demo/trades?status=closed&limit=10000` から `entry_type='sr_anti_hunt_bounce'` を抽出して
LIVE/SHADOW 分離集計した結果:

- Total closed: 154 (LIVE is_shadow=0: 3, SHADOW is_shadow=1: 151)
- LIVE 3 件は全て EUR_JPY BUY (2 loss / 1 win, 統計的無意味)
- Shadow N=151: WR 17.9%, Wilson_lo 12.6%, EV −3.81 pip, PF 0.46 — 明確な負け

**Metadata loss on shadow N=151:**

| field | empty rate | symptom |
|---|---:|---|
| `alpha_snapshot` | 151/151 (100%) | UPDATE path が走っていない |
| `edge_cell_id` | 151/151 (100%) | INSERT 時に "" のまま、後段 UPDATE もなし |
| `sr_basis = 0.0` | 128/151 (84.8%) | `sig.get("sr_entry_map", {}).get("recommended", {})` が空 |
| `spread_at_entry = 0.0` | 128/151 (84.8%) | spread 取得 path 切断 |
| `confluence_details` に `pyarrow/fastparquet ImportError` | 92/151 (61%) | production の parquet engine 欠損 |
| `mtf_alignment/h4_label/d1_label/gate_action/vol_state/regime/layer1_dir` 空 | 128/151 (84.8%) | MTF 情報の伝播切断 |
| `dedup_violation = 1` | 63/151 (42%) | per-bar dedup 欠落の継続 |

**Timeline:**

- 2026-04-28 〜 2026-05-22: full-meta cohort N=23 (sr_basis 非ゼロ)
- **2026-05-22 → 2026-05-25 境界: 以降 full-meta=0**, blind-fire のみに切替
- 05-25 単日 27 件、05-21 単日 20 件、05-29 8 件 と blind-fire 加速

## Candidate commits (regression window 2026-05-20 〜 2026-05-25)

```
e8e707f4 fix(audit): restore SR shadow emit OANDA audit rows [rule:R3]
b3efa69a feat(codex): complete 20260521-0556-sr-family-audit-pipeline-bypass
79600126 refactor(regime): extract Perfect Order EMA classifier to shared module
747398af fix(daytrade): route Kalman D7 trio through LIVE_PROMOTE_LOSERS side-channel
a7b18453 fix(daytrade): LIVE_PROMOTE_LOSERS side-channel for prod 0-fire bug [rule:R3]
```

特に注目: `e8e707f4` は SR family の OANDA audit 復旧 fix だが、demo_trades 側の meta 伝播
ロジックを一緒に切り替えた可能性。`a7b18453` / `747398af` の LIVE_PROMOTE_LOSERS side-channel が
`sig` dict の構造を変更したか、SR family を別 path に routing して `sr_entry_map` / `regime` /
`mtf_*` の埋め込みを skip した可能性。

## Canonical schema (verbatim — `modules/demo_db.py:106`)

```sql
CREATE TABLE IF NOT EXISTS demo_trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id        TEXT UNIQUE,
    status          TEXT DEFAULT 'OPEN',
    direction       TEXT,
    entry_price     REAL,
    entry_time      TEXT,
    exit_price      REAL,
    exit_time       TEXT,
    sl              REAL,
    tp              REAL,
    pnl_pips        REAL,
    pnl_r           REAL,
    outcome         TEXT,
    entry_type      TEXT,
    confidence      INTEGER,
    tf              TEXT DEFAULT '15m',
    reasons         TEXT,
    regime          TEXT,
    dow_regime      TEXT,
    v2_regime       TEXT,
    edge_cell_id    TEXT DEFAULT '',
    confluence_score TEXT,
    confluence_details TEXT,
    layer1_dir      TEXT,
    score           REAL,
    close_reason    TEXT,
    ema_conf        INTEGER,
    sr_basis        REAL,
    created_at      TEXT DEFAULT (datetime('now'))
);
-- ALTER で追加された列: alpha_snapshot TEXT DEFAULT '' (demo_trader.py:695)
-- ALTER で追加された列: is_shadow INTEGER DEFAULT 0
-- ALTER で追加された列: oanda_trade_id TEXT DEFAULT ''
-- 他: mtf_*, spread_at_entry/exit, slippage_pips, mafe_*_pips, dedup_violation,
--    flag_drift_backfilled, force_demoted_live_leak, cooldown_elapsed
```

## Canonical write paths (verbatim — `modules/demo_trader.py`)

```python
# 5124-5127:
sr_map = sig.get("sr_entry_map", {})
rec = sr_map.get("recommended", {})
ema_conf = rec.get("ema_confidence", confidence) if rec else confidence
sr_basis = rec.get("sr_basis", 0) if rec else 0

# 5317-5333: edge_cell_id resolution
_edge_cell_id = ""
# ... edge cell lookup using regime/instrument/entry_type ...
    _edge_cell_id = _edge_cell.cell_id

# 5350-5361: insert call
INSERT carries: sr_basis, edge_cell_id, mode, instrument, ...

# 5394-5399: alpha_snapshot UPDATE
"UPDATE demo_trades SET alpha_snapshot = ? WHERE id = ?"
```

## Pre-registration (LOCK before investigation run)

### Investigation deliverables (ALL required)

1. **Regression commit identification** —
   `git log --since=2026-05-20 --until=2026-05-26 --diff-filter=M modules/demo_trader.py modules/demo_db.py strategies/daytrade/`
   と各 commit の diff 確認で、以下のいずれが SR family の `sig` dict から `sr_entry_map` /
   `regime` / `mtf_*` を脱落させたかを特定する。
   候補は上記 5 commits + その間の他コミット。

2. **`sr_entry_map` producer location** — `sig["sr_entry_map"]["recommended"]` を埋める箇所
   (grep `sr_entry_map\[`, `sig\["sr_entry_map"\]\s*=`, `sig.update.*sr_entry_map`) を全て列挙し、
   sr_anti_hunt_bounce が通る path で本当に呼ばれているかを実機 (Render shell or local
   reproduction) で確認。

3. **`pyarrow/fastparquet` missing root cause** — production の `requirements.txt` /
   `requirements-prod.txt` / Dockerfile を確認し、parquet engine が build に含まれていない
   ことを確認 → `pip install pyarrow` で `confluence_details` の ImportError が消える
   ことを local で smoke test 検証 (`python -c "import pyarrow; import pandas as pd;
   pd.read_parquet('data/cache/massive/USDJPY_M15.parquet').shape"`)。

4. **Repro test** — `tests/` に **NEW** unit test を追加して、`sr_anti_hunt_bounce` の
   signal を mock した上で `demo_trader._record_trade(...)` (or 相当の挿入 API) を呼んだ際に
   `sr_basis`, `edge_cell_id`, `alpha_snapshot`, `spread_at_entry`, `mtf_alignment` の各列に
   非空値が書かれることを assert する。**この test が現在 main で失敗することを必ず最初に確認**
   (failing-first TDD)。

5. **Fix application** — 上記 1〜4 を踏まえ、最小限の修正で `sr_anti_hunt_bounce` (および
   同 path を共有する SR family / 影響範囲ある他戦略) で meta が再び書き込まれる状態に戻す。
   ただし以下を **絶対に** 行わない:
   - 既に稼働中の Kalman D7 / vix_carry / ZZ pivot v60 SR 等の LIVE 路径 (LIVE_PROMOTE_LOSERS
     side-channel 含む) の変更
   - `dedup_violation` を 0 に書き換える等の表面的修正

### Acceptance criteria

- failing-first test が修正後 PASS (`pytest tests/test_<new>.py -v`)
- 既存 92 tests 全 pass (`python3 -m pytest tests/ -x -q`)
- `python3 scripts/check.py` PASS
- local で sr_anti_hunt_bounce shadow signal を emulate して record 投入し、
  `sr_basis != 0.0`, `edge_cell_id != ''`, `alpha_snapshot != ''`,
  `spread_at_entry != 0.0`, `mtf_alignment != ''` を SQL で直接確認
- `pyarrow` を requirements に追加 + import smoke test が pass
- forensic レポート markdown を `wiki/lessons/2026-06-03-sr-meta-loss-forensic.md` に追記
  (regression commit / 影響範囲 / 修正内容 / 再発防止策)

### Out of scope (別タスクに切り出す)

- meta 復旧後の 1〜2 週間 shadow 再観測 (cell-attributable な edge 再評価)
- USD_JPY / EUR_USD / SELL 即時停止判断 (claude 司令塔で R2 判断、本タスクとは独立)
- 他戦略 (`sr_fib_confluence`, `sr_channel_reversal` 等) で同種 meta loss が起きているか
  の横断監査 (本タスクで原因 commit が特定でき次第、後続タスクとして派生)
- BT vs Shadow の edge transfer diagnostic ([[project_sr_weight_phase2_accept_2026_05_11]]
  の cohort 比較)

## Anti-patterns to avoid

- [[feedback_codex_mock_test_trap]]: mock-only test で PASS にしない。実 SQLite に書いて
  実 SELECT で検証すること
- [[feedback_codex_schema_hallucination]]: CREATE TABLE は上記 verbatim を使い、推測 schema
  での修正禁止
- [[feedback_codex_stash_leak]]: stash@{N} に変更を埋没させない。git status / git diff /
  git stash list を最終 verification で必ず確認し、変更が working tree に commit されている
  ことを確認

## Reference

- claude session 2026-06-03 10:20 JST audit (Render `/api/demo/trades` 経由実測)
- [[project_sr_anti_hunt_demo_trades_meta_loss_2026_06_03]] (claude memory)
- [[project_sr_family_audit_gap_2026_05_21]] (前回の SR family bypass 修正 task)
- [[project_sr_weight_phase2_accept_2026_05_11]] (BT で edge 検出した promotion 元データ)
- [[feedback_shadow_first_quant_architecture]] (BT は sanity filter、Shadow が真の estimator)
