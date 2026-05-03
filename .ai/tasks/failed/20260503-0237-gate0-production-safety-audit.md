---
id: 20260503-0237-gate0-production-safety-audit
title: Gate 0 production safety audit for OANDA/statistics integrity
owner: codex
status: queued
priority: P0
created_at: 2026-05-03T02:37:36+0900
roadmap_gate: Gate 0
rule: R3
---

# Objective

Verify that the recent production-safety fixes around OANDA/statistics integrity are coherent, tested, and ready for Claude Code roadmap review.

# Context

The roadmap cannot advance while live-trade statistics are polluted or OANDA transfer state can drift. Recent work touched is_shadow drift handling, pending OANDA ops recovery, Daily Loss Gate, OANDA Transactions API support, live-source drift checks, and dedup auditing. This task is a focused verification pass, not a new strategy implementation.

# Scope

Codex may inspect and, only if necessary for failing tests, minimally change:

- `modules/demo_db.py`
- `modules/demo_trader.py`
- `modules/oanda_bridge.py`
- `modules/oanda_client.py`
- `tools/check_live_source.py`
- `tools/transactions_shadow_drift_audit.py`
- `tools/per_bar_dedup_audit.py`
- `tests/test_daily_loss_gate.py`
- `tests/test_pending_oanda_ops.py`
- `tests/test_oanda_audit_join_invariant.py`

Codex must not change:

- `.env` or any production credentials
- strategy parameters unrelated to this audit
- roadmap/KB files unless explicitly needed for a run report
- local production-like DB files except read-only audit queries

# Required Reading

- `CLAUDE.md`
- `knowledge-base/wiki/syntheses/roadmap-v2.1.md`
- `knowledge-base/wiki/analyses/system-reference.md`
- `knowledge-base/wiki/index.md`

# Acceptance Criteria

- [ ] Identify whether any listed tests fail before changing code.
- [ ] If failures exist, fix only the narrow production-safety issue causing them.
- [ ] Run the verification commands below and summarize pass/fail evidence.
- [ ] Check that queued local DB confusion does not affect the audit tools' default DB selection.
- [ ] Write a final report for Claude Code under `.ai/runs/` via Codex final output.

# Verification Commands

```bash
python3 -m pytest tests/test_daily_loss_gate.py tests/test_pending_oanda_ops.py tests/test_oanda_audit_join_invariant.py
python3 tools/transactions_shadow_drift_audit.py --help
python3 tools/check_live_source.py --help
```

# Codex Instructions

Work in this repository. Respect existing uncommitted changes. Do not revert user changes. Investigate first, then implement the smallest safe change only if verification fails. In the final report, include status, files changed, verification output summary, remaining risks, and the next recommended roadmap task.


## Error (2026-05-03T12:15:05Z)

```
Reading prompt from stdin...
OpenAI Codex v0.128.0 (research preview)
--------
workdir: /data/repo/fx-ai-trader
model: gpt-5.5
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: none
reasoning summaries: none
session id: 019dedc3-4055-7ed2-a750-81fefc29d7cf
--------
user
# Objective

Verify that the recent production-safety fixes around OANDA/statistics integrity are coherent, tested, and ready for Claude Code roadmap review.

# Context

The roadmap cannot advance while live-trade statistics are polluted or OANDA transfer state can drift. Recent work touched is_shadow drift handling, pending OANDA ops recovery, Daily Loss Gate, OANDA Transactions API support, live-source drift checks, and dedup auditing. This task is a focused verification pass, not a new strategy implementation.

# Scope

Codex may inspect and, only if necessary for failing tests, minimally change:

- `modules/demo_db.py`
- `modules/demo_trader.py`
- `modules/oanda_bridge.py`
- `modules/oanda_client.py`
- `tools/check_live_source.py`
- `tools/transactions_shadow_drift_audit.py`
- `tools/per_bar_dedup_audit.py`
- `tests/test_daily_loss_gate.py`
- `tests/test_pending_oanda_ops.py`
- `tests/test_oanda_audit_join_invariant.py`

Codex must not change:

- `.env` or any production credentials
- strategy parameters unrelated to this audit
- roadmap/KB files unless explicitly needed for a run report
- local production-like DB files except read-only audit queries

# Required Reading

- `CLAUDE.md`
- `knowledge-base/wiki/syntheses/roadmap-v2.1.md`
- `knowledge-base/wiki/analyses/system-reference.md`
- `knowledge-base/wiki/index.md`

# Acceptance Criteria

- [ ] Identify whether any listed tests fail before changing code.
- [ ] If failures exist, fix only the narrow production-safety issue causing them.
- [ ] Run the verification commands below and summarize pass/fail evidence.
- [ ] Check that queued local DB confusion does not affect the audit tools' default DB selection.
- [ ] Write a final report for Claude Code under `.ai/runs/` via Codex final output.

# Verification Commands

```bash
python3 -m pytest tests/test_daily_loss_gate.py tests/test_pending_oanda_ops.py tests/test_oanda_audit_join_invariant.py
python3 tools/transactions_shadow_drift_audit.py --help
python3 tools/check_live_source.py --help
```

# Codex Instructions

Work in this repository. Respect existing uncommitted changes. Do not revert user changes. Investigate first, then implement the smallest safe change only if verification fails. In the final report, include status, files changed, verification output summary, remaining risks, and the next recommended roadmap task.

2026-05-03T12:14:50.314684Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
2026-05-03T12:14:50.778295Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
2026-05-03T12:14:51.515236Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
ERROR: Reconnecting... 2/5
2026-05-03T12:14:52.375017Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
ERROR: Reconnecting... 3/5
2026-05-03T12:14:53.442109Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
ERROR: Reconnecting... 4/5
2026-05-03T12:14:55.319029Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
ERROR: Reconnecting... 5/5
2026-05-03T12:14:58.574729Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 401 Unauthorized, url: wss://api.openai.com/v1/responses
ERROR: Reconnecting... 1/5
ERROR: Reconnecting... 2/5
ERROR: Reconnecting... 3/5
ERROR: Reconnecting... 4/5
ERROR: Reconnecting... 5/5
ERROR: unexpected status 401 Unauthorized: Missing bearer or basic authentication in header, url: https://api.openai.com/v1/responses, cf-ray: 9f5f306a7f009694-PDX, request id: req_d80e563a8c5745138a98958b6d691706
ERROR: unexpected status 401 Unauthorized: Missing bearer or basic authentication in header, url: https://api.openai.com/v1/responses, cf-ray: 9f5f306a7f009694-PDX, request id: req_d80e563a8c5745138a98958b6d691706

```
