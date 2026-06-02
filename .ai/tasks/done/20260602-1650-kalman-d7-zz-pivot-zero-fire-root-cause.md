---
id: 20260602-1650-kalman-d7-zz-pivot-zero-fire-root-cause
priority: P0
gate: R3
rule: R3
status: queued
created: 2026-06-02
owner: claude
---

# Kalman D7 / ZZ Pivot v60 SR — Zero-Fire Root Cause Investigation

**Rule classification**: R3 (Immediate — silent zero-fire suspected on two LIVE-promoted intentional exceptions, 5 days post-deploy)

## Why this task

User complaint 2026-06-02 16:45 JST: "kalman と zz pivot が全然発火しない。原因を確認して欲しい".

Claude side has confirmed the following from Render web logs + production `/api/oanda/stats`:

- **0 fires** for `kalman_d7_trail_atr` / `zz_pivot_v60_sr` / `zz_pivot_v60_sr_lo`
  in the 30-day `/api/oanda/stats` rolling window (total N=65, none of the three).
- **0 Render log lines** mention `kalman_d7` in 24h+ (`text=["kalman_d7"]` filter).
- **0 evaluation log lines** mention `zz_pivot` outside `[migration/dedup_backfill]`
  targets-list spam.
- MainLoop scheduler **is healthy**: `daytrade` thread tick #434, `daytrade_eur`
  thread tick #427 — both poll their strategies on every iteration.
- Both strategies **are correctly registered** in `modules/demo_trader.py`:
  - `_PAIR_PROMOTED` lines 7196-7197 (zz_pivot_v60_sr & _lo on EUR_USD)
  - `_PAIR_LOT_BOOST` lines 7311-7325 (kalman 0.5x, zz_pivot 1.0x/0.5x)
  - `_SHIELD_EUR_DT_WHITELIST` line 7630-7631 (added 2026-05-31 in 8a069d9d
    to bypass `_OANDA_MODE_BLOCKED("daytrade_eur")`)
- Render env `KALMAN_D7_LIVE_ENABLE=1` was set 2026-05-28 17:46 JST per
  `knowledge-base/wiki/decisions/pre-reg-kalman-d7-shadow-fire-recovery-2026-05-28.md`.

Given the scheduler is alive and the strategies are registered, the remaining
hypotheses are:

- **H_FILTER** strategies are polled but their per-bar filters reject every single
  bar over the last 5 days (silent `return None` — by design, no log).
- **H_SILENT_DROP_V2** another silent drop downstream of the filter, similar to
  the 2026-05-28 5-gate silent drop fix (29ec95cb) and 2026-05-31 OANDA-mode-block
  fix (8a069d9d). A third uninstrumented block point still exists.
- **H_ENV_REVERT** `KALMAN_D7_LIVE_ENABLE` env var was reverted/lost on a later
  deploy. Without it, kalman is shadow-only and OANDA-skipped → may not even
  generate a shadow row depending on tier path.

## Required investigation (run on Render runner, Codex CLI + SSH)

Use the fx-codex-runner SSH (srv-d7rjnfn7f7vs73d1e6ig) OR a Render shell on the
web service (srv-d6va1of5r7bs73en10vg) — the SQLite audit DB lives on the
attached disk at `/var/data/`.

### Step 1: oanda_audit / shadow_audit DB enumeration

On fx-ai-trader web service shell, locate the audit SQLite DB
(`find /var/data -name '*.db' 2>/dev/null`) and run:

```sql
-- Full count by entry_type since 2026-05-28
SELECT entry_type, bridge_status, is_shadow, COUNT(*) AS n,
       MIN(entry_time), MAX(entry_time)
FROM oanda_audit
WHERE entry_time >= '2026-05-28T00:00:00'
  AND (entry_type LIKE '%kalman%'
       OR entry_type LIKE '%zz_pivot%'
       OR strategy LIKE '%kalman%'
       OR strategy LIKE '%zz_pivot%')
GROUP BY entry_type, bridge_status, is_shadow
ORDER BY n DESC;
```

Also enumerate ANY parallel shadow/sentinel tables (`shadow_signals`,
`shadow_audit`, `sentinel_log`, `block_log`, `_block_counts`) and dump the same
slice.

If the SQL returns zero rows, run the same query without the date filter to
confirm whether these entry_types have **ever** appeared.

### Step 2: Verify Render env vars on the web service

```bash
# Inside the running container (SSH or `render shell`):
env | grep -iE 'kalman|zz|d7|live_enable|oanda|shadow'
```

Confirm `KALMAN_D7_LIVE_ENABLE=1` is set. If not, that is the answer for kalman.

### Step 3: Filter-rejection probe (the real diagnostic)

Run a standalone Python probe against the on-disk MASSIVE parquet
(`data/cache/massive/USD_JPY_15m.parquet`, `EUR_USD_15m.parquet`) for the
last 7 days (2026-05-26 → 2026-06-02). For every M15 bar, invoke the actual
strategy's filter functions and tally **which filter fails first**.

```python
# Kalman: import _kalman_d7_passes_filters from strategies/daytrade/kalman_d7_trend.py
# ZZ Pivot: instantiate ZzPivotV60Sr and inspect why evaluate() returns None.
```

For Kalman, the expected histogram keys are:
`po_up_not_started`, `dist_out_of_range(>3 or <=0)`, `gap_too_wide(>=3)`,
`atr_outside_q2q4`, `rsi_overbought(>=70)`, `session_excluded(OVL/DEAD)`.

For ZZ Pivot, the expected categories are:
`tf_filter_miss`, `df_too_short`, `no_trend`,  `no_peak_no_trough`,
`rr_below_min`, `feature_compute_error`, `<other>`.

Output: **two tables**, one per strategy, showing
`first_filter_failed → bars_count (%)`. Include the worst-bar telemetry
(latest fail per category — entry_price, ema200, atr, dist_atr, gap_atr, rsi,
hour_utc, peak_type_attempts).

### Step 4: Verdict per strategy

Produce a concise table:

| Strategy | Bars in 7d | Filter pass count | First-fail histogram | Audit rows | Verdict |
|---|---|---|---|---|---|

Where **Verdict** is one of:
- `MARKET_WAIT` — filter rejection pattern consistent with design (e.g. USDJPY
  far from EMA200 → kalman DIST always fails). No code change needed; wait.
- `DESIGN_TOO_STRICT` — filter pass count =0 with no obvious market reason.
  Recommend specific threshold relaxation backed by 7d data.
- `SILENT_DROP_V3` — filters DO pass but no audit row exists → uninstrumented
  block downstream. Bisect the post-filter call chain (signal_normalize →
  shadow_eligibility → escalation → oanda_bridge).
- `ENV_FAULT` — `KALMAN_D7_LIVE_ENABLE` missing / mode-block re-triggered.

### Step 5 (only if SILENT_DROP_V3): instrumentation patch

Add a single-line counter at every `return None` site in the kalman / zz_pivot
post-filter flow + an info-level log when a candidate is built but downgraded.
Match the existing `SENTINEL_BLOCK_DIAG` pattern. Do **not** rewrite filter
logic. Submit as `feat(diag): kalman_d7 / zz_pivot v60 sr silent-drop
instrumentation [rule:R3]`.

## Deliverables

1. Markdown report under
   `knowledge-base/raw/audits/kalman-zz-zero-fire-2026-06-02.md` with:
   - Step 1 SQL output (verbatim).
   - Step 2 env-var verification.
   - Step 3 histogram tables (both strategies).
   - Step 4 verdict table + 1-paragraph plain-language summary per strategy.
2. If SILENT_DROP_V3: instrumentation patch + smoke-test log lines.
3. Update memory hub `knowledge-base/wiki/audit-index.md` with a one-line
   pointer.
4. Discord post (1 message) to the user channel summarizing verdict per
   strategy in <500 chars.

## Hard constraints

- **Do NOT modify filter parameters** in this task. The user wants root cause,
  not parameter tuning. Threshold proposals belong to a follow-up task.
- **Do NOT bypass shadow-first**. Even if a third silent drop is found, the
  fix is instrumentation + escalation logging only.
- **Do NOT touch the LIVE 0.5x / 1.0x lot booster values** — those are
  intentional exceptions (rule:R1-EXCEPTION).
- Use real production data (Render SQLite + on-disk parquet). No mocks.
- Reuse existing block-diagnostic infrastructure
  (`SENTINEL_BLOCK_DIAG`, `_block_counts` exposed in 57d1570d) where possible.

## Memory anchors

- [[project_kalman_d7_regime_bound_live_2026_05_20]]
- [[project_kalman_d7_silent_drop_recovery_2026_05_28]]
- [[project_zz_pivot_v60_sr_live_queue_2026_05_28]]
- [[feedback_label_empirical_audit]] — code 演繹禁止、ラベル×WR 実測必須
- [[feedback_codex_stash_leak]] — final.md ACCEPT は信用しない、必ず repo persist 検証


## Result (2026-06-02T15:20:57Z)

exit=0 · 435s

```
完了しました。commit は `d723fecb` です。

Verdict:
- `kalman_d7_*`: `MARKET_WAIT`
  - 2026-05-28以降のプローブで filter pass `0/347`
  - 主因は `po_up_not_started` 331件、次に EMA200 から遠すぎる `dist_out_of_range` 12件
- `zz_pivot_v60_sr*`: `SILENT_DROP_V3`
  - 2026-05-28以降のプローブで candidate pass `6/347`
  - production audit は `zz_pivot_v60_sr` が1件のみ、しかも `skipped / shadow_tracking`
  - `sent/filled` は0件

変更:
- [modules/demo_trader.py](/data/repo/fx-ai-trader/modules/demo_trader.py): Kalman/ZZ の post-filter block / shadow downgrade に `[SENTINEL_BLOCK_DIAG]` ログ追加
- [tools/kalman_zz_zero_fire_probe.py](/data/repo/fx-ai-trader/tools/kalman_zz_zero_fire_probe.py): 実MASSIVEデータ用プローブ追加
- [knowledge-base/raw/audits/kalman-zz-zero-fire-2026-06-02.md](/data/repo/fx-ai-trader/knowledge-base/raw/audits/kalman-zz-zero-fire-2026-06-02.md): 監査レポート
- [knowledge-base/wiki/audit-index.md](/data/repo/fx-ai-trader/knowledge-base/wiki/audit-index.md): pointer追加

Verification:
- `py_compile` pass
- probe rerun: Kalman `0` pass since 2026-05-28, ZZ `6` pass since 2026-05-28
- commit hook pass: HIP-1 guard / Python 3.9 guard

制約:
- この runner には `ssh` がなく、web service の `/var/data/*.db` へ直接SQLite実行はできませんでした。代替で `/api/oanda/audit?limit=10000` から全7283 audit rowsを取得して集計しました。
- Discord投稿は `DISCORD_WEBHOOK_URL` で試行しましたが HTTP 403 で失敗しました。
```
