---
id: 20260526-1542-api-oanda-audit-502-fix
priority: P0
gate: R3
rule: R3
status: queued
created: 2026-05-26
owner: claude
---

# Fix /api/oanda/audit 502 (all limit values fail)

priority: P0
rule: R3 (immediate — audit observability blocked; sibling endpoint /api/oanda/stats also has range-ignored bug, memory: project_oanda_stats_range_ignored_2026_05_18.md)
gate: N/A (correctness fix, validated by HTTP 200 + valid JSON)

## Why this is P0

`/api/oanda/audit` returns HTTP 502 for all observed `limit` values (10, 20, 200) — tested
2026-05-27 00:13 UTC on production `https://fx-ai-trader.onrender.com`:

```
$ curl -s 'https://fx-ai-trader.onrender.com/api/oanda/audit?limit=10' -w '%{http_code}'
HTTP 502 size=223038  (Render 502 page)

$ curl -s 'https://fx-ai-trader.onrender.com/api/oanda/audit?limit=20' -w '%{http_code}'
HTTP 502 size=223038

$ curl -s 'https://fx-ai-trader.onrender.com/api/oanda/audit?limit=200' -w '%{http_code}'
HTTP 502 size=223038
```

Default `limit` is 20 (from handler), so the no-arg case also fails.

This endpoint is the primary read-side of OANDA audit visibility. While
`/api/strategies/status` aggregates separately and is not affected, the manual debug /
forensic flow relies on `/api/oanda/audit` to inspect bridge_status='sent'/'filled'/'skipped'
rows. Currently this is unavailable, which blocks any human-driven post-mortem.

## Handler

`app.py:13823-13830`:

```python
@app.route("/api/oanda/audit")
def api_oanda_audit():
    """OANDA実行監査ログ — トレードごとの連携成否と理由を返す。"""
    limit = request.args.get("limit", 20, type=int)
    bridge = _demo_trader._oanda
    return jsonify({
        "audit": bridge.get_execution_audit(limit=limit),
        "total": bridge.get_execution_audit_count(),
    })
```

The handler is trivial. Failure is somewhere inside
`OandaBridge.get_execution_audit(limit=limit)` or `get_execution_audit_count()` (likely the
former, since limit varies).

## Investigation steps

1. **Locate `get_execution_audit`** in `modules/oanda_bridge.py` (or wherever
   `_demo_trader._oanda` is instantiated). Inspect:
   - SQL query used
   - JSON serialization (timestamps? `Decimal`? `bytes`?)
   - Any per-row transformation that may raise

2. **Check Render logs for traceback**: Sentry integration is active per memory
   `reference_mcp_servers.md` ("fx-ai-trader 側の Sentry 統合"). Pull the latest
   `/api/oanda/audit` exception from Sentry — likely the smoking gun.
   - Render service ID: `srv-d6va1of5r7bs73en10vg`
   - Try also `mcp__sentry__authenticate` if Sentry MCP available

3. **Reproduce locally** with a copy of production-ish data:
   ```bash
   cd /Users/jg-n-012/test/fx-ai-trader
   python -c "from modules.demo_trader import _demo_trader; print(_demo_trader._oanda.get_execution_audit(limit=20))"
   ```
   If this raises locally, capture the traceback. If it succeeds locally, the issue is
   environment-specific (e.g. memory pressure on Render pro plan with current row count).

## Likely root causes (Codex must verify, not assume)

- **JSON serialization failure** on a column type (Decimal, datetime, NaN) — most common
  Flask 502 cause when handler returns successfully but Werkzeug fails to encode
- **SQL query returning huge BLOB** (sr_meta JSON has grown unbounded?) — Render
  pro plan has 2GB worker mem, gunicorn timeout 120s
- **gunicorn worker timeout** — `app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1
  --threads 8 --worker-class gthread` — single worker; one slow audit call blocks it
- **Schema drift** — recent migration added a column that the SELECT doesn't handle
- **Memory OOM** on `get_execution_audit_count()` if it does a COUNT(*) over a now-huge
  audit table

## Files & line refs

- `app.py:13823-13830` — endpoint handler (likely no change needed)
- `modules/oanda_bridge.py` — `get_execution_audit` / `get_execution_audit_count` (PRIMARY
  investigation target)
- `modules/demo_db.py` — underlying SQL (oanda_audit table schema)

## Validation

1. **Local reproduction**: with a representative sample of production audit rows
   (or anonymized export via Render shell), confirm the failure mode.

2. **Unit test (must add)**: `tests/test_api_oanda_audit_endpoint.py` covering:
   - `limit=20` returns HTTP 200 + valid JSON with `audit` and `total` keys
   - `limit=200` returns HTTP 200 (no timeout/memory failure)
   - Audit rows containing `sr_meta` JSON / Decimal pnl values serialize correctly
   - Empty audit table returns `{"audit": [], "total": 0}` not 500

3. **Production verification (post-deploy)**:
   ```bash
   for L in 10 20 100 200; do
     curl -s "https://fx-ai-trader.onrender.com/api/oanda/audit?limit=$L" \
       -o /tmp/a.json -w "limit=$L HTTP %{http_code} size=%{size_download}\n"
   done
   ```
   All four must return 200 with valid JSON. Document p95 latency.

## Out of scope (do NOT do)

- Do NOT add caching / Redis (premature optimization).
- Do NOT change the audit table schema.
- Do NOT touch the `/api/oanda/stats` range-ignored bug (memory
  `project_oanda_stats_range_ignored_2026_05_18.md`) — that's a separate task.
- Do NOT migrate to Postgres — fx-ai-trader is SQLite-only per memory.

## Commit message template

```
fix(api): /api/oanda/audit returning 502 at all limit values

get_execution_audit() was raising during <ROOT_CAUSE> for production audit
rows. <ONE-LINE FIX DESCRIPTION>. Add regression test covering serialization
and empty-table edge cases.

Refs: ai/tasks queue 20260526-1542
```

## Acceptance

Codex returns:
- root cause diagnosis (one of the candidates above OR a new finding, with evidence)
- diff of the offending function in `modules/oanda_bridge.py` (or wherever)
- new test file at `tests/test_api_oanda_audit_endpoint.py` with 3+ assertions
- proof of local reproduction and fix (pytest run output)
- pre-flight deploy plan with rollback procedure (single function edit, should be trivial)
