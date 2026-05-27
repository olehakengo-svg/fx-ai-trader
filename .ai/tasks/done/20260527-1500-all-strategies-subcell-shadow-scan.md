---
id: 20260527-1500-all-strategies-subcell-shadow-scan
priority: P1
gate: R1
rule: R1
status: queued
created: 2026-05-27
owner: claude
---

# All-strategies sub-cell shadow scan — find pre-reg-able WR≥50%/+EV cells

## 背景 & 目的

ユーザー仮説:
> 「特定条件では勝てる cell がある。それを抽出して WR≥50% & +EV で再 shadow → 月利100%に寄与」

sr_break_retest 単独監査 (Codex `done/20260527-sr-break-retest-cell-forensic-audit.md`) の Phase B で発見:

- **USD_JPY/BUY TP_HIT cohort: N=15 WR=100% EV=+16.07 Wilson_bf_lo=0.581 (m=8)** ← m=8 Bonferroni 後でも > 0.50
- ただし close_reason での分割は **ex-post selection (勝ったから TP_HIT を選ぶ)** で、entry 時点では予測不能

→ **entry 時点で観測可能な特徴のみで sub-cell を組み、TP_HIT 偏在する cell を発見する** のが本タスク。

これを **76 戦略全体** に適用してポートフォリオ規模で「条件付き勝てる cell」を抽出。月利100%目標への寄与は単一戦略でなく cell の集合体である前提。

## Scope

`demo_trades` (production `/var/data/demo_trades.db`) の **`is_shadow=1 AND status='CLOSED'`** 行のみ対象。

shadow_emit gap fix (commit `15bf768f` / done task `20260526-1540-shadow-emit-audit-gap-fix`) 完了後の **post-fix** データなので、~20 SENTINEL/Phase B-1 戦略は N が小さい/0 のはず。それらは「N<20 で除外」として scan に含めるが結果には現れない (これは Bonferroni m の inflation を避けるため intentional)。

## Pre-registered cell structure (LOCK BEFORE LOOKING AT DATA)

各戦略について以下の dim で sub-cell を構築:

| dim | bins | source col |
|---|---|---|
| pair | 8 majors (USD_JPY, EUR_JPY, GBP_JPY, GBP_USD, EUR_USD, AUD_USD, NZD_USD, USD_CHF, EUR_GBP) | `instrument` |
| direction | BUY / SELL | `direction` |
| session | Asia(0-7h UTC), London(7-13), NY(13-21), Off(21-24) | derived from `entry_time` |
| regime | 既存ラベル使用 (NULL は "unknown" cell) | `regime` OR `v2_regime` (どちらか populated 度高い方を選択) |

**LOCK**: spread / confluence_score / sr_basis 等は **本タスクでは使わない** (post-hoc dim 追加禁止)。後続タスクで extend する場合は新規 pre-reg。

Cell count per strategy: 9 pair × 2 dir × 4 session × ≤5 regime = max 360. 全 76 戦略で max ~27k cells。

## Statistical decision rules (3-stage pre-reg)

### Stage 1: descriptive shortlist (per strategy)

各 cell について算出:
- `N` (shadow CLOSED trades のみ)
- `wins` (pnl_pips > 0 が定義 — TP_HIT に限定しない)
- `WR = wins / N`
- `EV = mean(pnl_pips)`
- `total_pips`
- `PF = sum(positive pnl) / |sum(negative pnl)|`
- `Wilson_lo (95%, z=1.96)`

Stage 1 通過条件 (descriptive):
- `N >= 20` (small-N noise 除外)
- `WR >= 50%`
- `EV >= +0.5 pip`

→ Stage 1 通過 cell の合計を `K_stage1` とする。

### Stage 2: BH FDR (across all stage-1 candidates)

`K_stage1` cells で p-value 算出 (one-sided Wilson exact: H0=WR=0.5):
- BH FDR with q=0.10
- 通過 cell = `K_stage2`

→ FDR は Bonferroni より powerful、cell 探索向き ([W3-5 S3 棄却](memory/project_w3_5_s3_pair_pool_fdr_queued.md) と同手法)。

### Stage 3: Bonferroni-extended Wilson (final lock)

`K_stage2` cells に対し `m_extended = K_stage1` (Stage 1 で見た cell 数) で:
- `Wilson_bf_lo (z=3.29 ≈ α/K_stage1)`
- 通過条件: `Wilson_bf_lo >= 0.50`

→ Stage 3 通過 = 最終候補 cell。

### Stage 4 (mandatory verification): time cohort split

各 Stage 3 候補 cell について:
- 前半 (entry_time ソート上位 50%) と後半で WR / EV を分割
- **両方とも WR >= 50% かつ EV > 0** が条件 (片方失格なら REJECT)

→ [時間コホート整合](memory/feedback_cohort_time_check.md) 遵守。

### Stage 5 (sanity): pair × direction redundancy check

同一戦略の Stage 4 通過 cell が複数あった場合、pair/direction が完全に重複しない (= 異なる session/regime に集中) ことを確認。

全 5 段通過 = **PRE-REG_LOCKED_SHADOW_PROMOTE_CANDIDATE**。

## DB schema (paste-in)

```sql
-- demo_trades (production /var/data/demo_trades.db, modules/demo_db.py 408-)
-- 関連列のみ:
CREATE TABLE demo_trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id        TEXT UNIQUE,
    status          TEXT,                 -- 'CLOSED' のみ抽出
    direction       TEXT,                 -- 'BUY' / 'SELL'
    entry_price     REAL,
    entry_time      TEXT,                 -- ISO datetime
    pnl_pips        REAL,
    outcome         TEXT,
    entry_type      TEXT,                 -- strategy name (key for grouping)
    instrument      TEXT,                 -- pair
    is_shadow       INTEGER,              -- 1 のみ抽出
    regime          TEXT,                 -- 既存 regime ラベル
    v2_regime       TEXT,                 -- v2 regime ラベル
    close_reason    TEXT,                 -- 参考のみ、cell dim に使わない
    spread_at_entry REAL,                 -- 参考のみ
    mafe_favorable_pips REAL,
    mafe_adverse_pips REAL,
    created_at      TEXT
);
CREATE INDEX idx_trades_entry_type ON demo_trades(entry_type);
CREATE INDEX idx_trades_status ON demo_trades(status);
```

## Query template (sketch)

```sql
-- per strategy descriptive (Stage 1)
WITH cells AS (
  SELECT
    entry_type,
    instrument AS pair,
    direction AS dir,
    CASE
      WHEN CAST(strftime('%H', entry_time) AS INTEGER) BETWEEN 0 AND 6 THEN 'Asia'
      WHEN CAST(strftime('%H', entry_time) AS INTEGER) BETWEEN 7 AND 12 THEN 'London'
      WHEN CAST(strftime('%H', entry_time) AS INTEGER) BETWEEN 13 AND 20 THEN 'NY'
      ELSE 'Off'
    END AS session,
    COALESCE(v2_regime, regime, 'unknown') AS reg,
    COUNT(*) AS n,
    SUM(CASE WHEN pnl_pips > 0 THEN 1 ELSE 0 END) AS wins,
    AVG(pnl_pips) AS ev,
    SUM(pnl_pips) AS tot
  FROM demo_trades
  WHERE is_shadow=1 AND status='CLOSED'
  GROUP BY entry_type, pair, dir, session, reg
)
SELECT *, 1.0*wins/n AS wr
FROM cells
WHERE n >= 20 AND 1.0*wins/n >= 0.5 AND ev >= 0.5
ORDER BY ev DESC;
```

Python (per-cell Wilson_lo + BH FDR + Bonferroni-extended) は `scipy.stats.binomtest` + `statsmodels.stats.multitest.multipletests`。

## Output (in done/ markdown)

### Section 1: scan meta

- Total strategies scanned (expected: ~76)
- Strategies with `shadow_n >= 20`: list (those that pass minimum gate)
- Strategies with `shadow_n < 20`: list with note "INSUFFICIENT_N (likely shadow_emit gap residual or low signal frequency)"

### Section 2: Stage-by-stage counts

| stage | description | count |
|---|---|---|
| 0 | total candidate cells (all pair×dir×session×regime) | ~27,000 |
| 1 | descriptive shortlist (N≥20 ∧ WR≥0.5 ∧ EV≥0.5) | ? |
| 2 | BH FDR q=0.10 | ? |
| 3 | Bonferroni Wilson_bf_lo ≥ 0.50 | ? |
| 4 | time-cohort split passes | ? |
| 5 | redundancy check passes | ? |

### Section 3: PRE-REG_LOCKED_SHADOW_PROMOTE_CANDIDATEs

各候補について:

| strategy | pair | dir | session | regime | N | wins | WR | EV | total | Wilson_lo | Wilson_bf_lo | half-WR (前/後) | half-EV (前/後) |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|

候補ごとに最小 cell サイズ N、典型 spread、典型 MFE/MAE も付記。

### Section 4: per-strategy summary

全 76 戦略について 1 行:

| strategy | shadow_N | overall_WR | overall_EV | stage1_cells | stage5_cells | verdict |
|---|---:|---:|---:|---:|---:|---|

verdict ∈ {`HAS_PROMOTE_CANDIDATE`, `STAGE3_ONLY (no time-cohort)`, `STAGE1_ONLY (descriptive only)`, `INSUFFICIENT_N`, `REJECT`}.

### Section 5: portfolio-level recommendation

候補 cell 群を combined するときの:
- 推定 monthly contribution (mean EV × estimated frequency per month)
- 月利100%目標への寄与 % (per memory `roadmap-v2.1.md`)
- 相関考察 (同一 session/regime に集中していないか — diversification check)
- pre-reg LOCK 文言 (each candidate cell をどう Live ramp するかの ramp plan, e.g. shadow N+15→live small lot)

## 禁止事項

- 本番 DB への書き込み (SELECT only / `?mode=ro`)
- `.env` / OANDA secret アクセス
- Live 戦略 config / tier 変更 (本タスクは観測 + spec 出力のみ。実装は別 PR)
- post-hoc dim 追加 (例: 「spread を入れたら更に絞れる」と発見しても本タスクでは使わない。新規 pre-reg task で extend)
- Stage 1 通過数を見てから WR/EV 閾値を下げる (これは p-hacking)
- shadow_emit gap fix (commit 15bf768f) 完了前の pre-fix データを区別せず混合 (cell 解析は post-fix のみが本来の対象。Codex は `created_at >= '2026-05-27 04:53'` などのフィルタを明示)

## クオンツチェック (verdict matrix)

- [x] is_shadow=1 / status='CLOSED' フィルタ明示
- [x] Pre-registered cell dim (post-hoc 追加禁止)
- [x] Stage 1 descriptive thresholds (N=20, WR=0.5, EV=0.5)
- [x] BH FDR q=0.10
- [x] Bonferroni Wilson_bf_lo ≥ 0.50
- [x] Time cohort split (前後半とも WR≥0.5)
- [x] Redundancy / diversification check
- [x] Per-strategy + portfolio-level output
- [x] Live ramp plan は別 PR (本タスクは spec のみ)
- [x] 本番 DB 破壊禁止
- [x] post-hoc dim 追加禁止

## 関連 memory

- [部分的クオンツの罠](feedback_partial_quant_trap.md) — N/WR/EV のみで判断する罠
- [W3-3 S4 post-hoc selection 罠](project_w3_3_s4_connors_raschke_queued.md) — grid 上の cell 選別罠
- [W3-5 S3 pair pool BH FDR](project_w3_5_s3_pair_pool_fdr_queued.md) — FDR の使い方
- [時間コホート整合](feedback_cohort_time_check.md) — Stage 4 の根拠
- [W4-EDA 全戦略監査完了](project_w4_eda_complete_2026_05_05.md) — 同じ 76 戦略を 8 軸で監査済、結果との関係は本タスクで言及するべき
- [shadow-first quant architecture](feedback_shadow_first_quant_architecture.md) — shadow が真の estimator
- [監査=設計の正誤、N不足は別問題](feedback_audit_purpose_design_not_n.md) — N<20 戦略を REJECT しない
- [SR-weight Phase 2 ACCEPT](project_sr_weight_phase2_accept_2026_05_11.md) — `sr_anti_hunt_bounce` のみ survivor の前例
- 月利100%目標: `knowledge-base/wiki/syntheses/roadmap-v2.1.md`

## Acceptance

Codex が `done/` に出力する Result section に以下が含まれること:

1. Section 1-5 が全て埋まっている
2. 各 PRE-REG_LOCKED 候補に対する Live ramp plan (env var or config 変更点を file:line で示す)
3. False discovery rate のサニティチェック (q=0.10 で見つかった K_stage2 が K_stage1 × 0.10 以下であることの確認)
4. 候補ゼロの場合、その意味の議論 ("76 戦略どの shadow にも pre-reg 可能な sub-cell が存在しない → 戦略設計の根本見直しが必要")


## Result (2026-05-27T05:49:02Z)

exit=0 · 138s

```
Created the report at [done/20260527-all-strategies-sub-cell-shadow-scan.md](/data/repo/fx-ai-trader/done/20260527-all-strategies-sub-cell-shadow-scan.md).

Key result: **0 PRE-REG_LOCKED_SHADOW_PROMOTE_CANDIDATEs** in the scanned DB snapshot.

Important caveat: `/var/data/demo_trades.db` was not present in this workspace, so I scanned the only non-empty available DB, `/data/repo/fx-ai-trader/demo_trades.db`, read-only. That DB has **0 post-fix eligible rows** for `is_shadow=1 AND status='CLOSED' AND created_at >= '2026-05-27 04:53'`, so all stages are zero and all 81 current registry strategies are marked `INSUFFICIENT_N`, not rejected.

The report includes Sections 1-5, FDR sanity check, per-strategy summary, zero-candidate interpretation, and future ramp implementation references with file/line pointers.
```
