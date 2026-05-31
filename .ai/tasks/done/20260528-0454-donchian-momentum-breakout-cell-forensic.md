# donchian_momentum_breakout cell-level Win/Loss forensic audit

Task: `.ai/tasks/queue/20260528-0454-donchian-momentum-breakout-cell-forensic.md`  
Status: **BLOCKED_DATA**  
Date: 2026-05-28

## Result

The requested authoritative DB path is unavailable in this Codex workspace:

```text
/var/data/demo_trades.db
```

Verification command:

```bash
python3 tools/dmb_cell_forensic_audit.py \
  --db /var/data/demo_trades.db \
  --output done/20260528-0454-donchian-momentum-breakout-cell-forensic.md
```

Observed result:

```text
BLOCKED: DB not found: /var/data/demo_trades.db
Required evidence: read-only access to /var/data/demo_trades.db or an explicit production snapshot path.
```

No production DB write, `.env` read, credential access, live tier/config change, or Shadow/Live mixed aggregation was performed.

## Phase A reconciliation matrix

**BLOCKED_DATA**: cannot compute Shadow N / Live N / recent 30d / 7d / 24h counts without read-only access to the authoritative production SQLite DB.

The audit script opens SQLite with `file:<db>?mode=ro` and is ready to run once the DB is available:

```bash
python3 tools/dmb_cell_forensic_audit.py \
  --db /var/data/demo_trades.db \
  --output done/20260528-0454-donchian-momentum-breakout-cell-forensic.md
```

## Phase B per-cell stats table

**BLOCKED_DATA**: cannot compute `instrument × direction × close_reason`, PF, Kelly, Wilson lower, or Bonferroni-adjusted Wilson lower without the production rows.

## Phase C top-winning cell deep-dive

**BLOCKED_DATA**: cannot select top cell by EV×N or compute ledger/hour/cohort split without production Shadow rows.

## Phase D top-losing cell deep-dive

**BLOCKED_DATA**: cannot compute entry-price-based TP/SL distance vs MAFE without production Shadow rows.

## Phase E Shadow vs Live divergence

**SKIP/BLOCKED_DATA**: Live N per cell cannot be evaluated. No Shadow/Live mixing was attempted.

## Phase F reasons/regime label split

**SKIP/BLOCKED_DATA**: `reasons` JSON/regime breakdown cannot be evaluated without production rows.

## Recommend

- Do not promote any DMB cell from this run; estimator evidence is missing.
- Keep `donchian_momentum_breakout` FORCE_DEMOTED until the authoritative DB is available and the audit script completes.
- Exact evidence needed next: read-only access to `/var/data/demo_trades.db`, or an explicit production snapshot path approved as equivalent for this task.
- After access is available, rerun the command above and review the generated Phase A-F sections.

## MEMORY 更新提案 draft

`project_donchian_momentum_breakout_cell_audit_2026_05_28.md`:

- DMB cell forensic audit was blocked in Codex because `/var/data/demo_trades.db` was not mounted in the workspace.
- A read-only audit helper was added at `tools/dmb_cell_forensic_audit.py`; it computes Shadow/Live separation, per-cell Wilson/BF Wilson/PF/Kelly, top win/loss deep dives, MAFE vs entry-price TP/SL distance, Live divergence, and reasons JSON scan.
- Re-run requirement: mount `/var/data/demo_trades.db` read-only or provide an explicit production snapshot path.
