---
id: YYYYMMDD-HHMM-short-slug
title: Short task title
owner: codex
status: queued
priority: P0
created_at: YYYY-MM-DDTHH:MM:SS+09:00
roadmap_gate: Gate 0
rule: R3
---

# Objective

Describe the single outcome Codex must achieve.

# Context

- Why this matters for the monthly 100% roadmap.
- Relevant prior observations, KB pages, and known risks.
- Current production/local evidence.

# Scope

Codex may change:

- `path/to/file.py`
- `tests/test_name.py`

Codex must not change:

- production secrets
- unrelated strategy parameters
- unrelated KB/changelog files

# Required Reading

- `CLAUDE.md`
- `knowledge-base/wiki/syntheses/roadmap-v2.1.md`
- Add task-specific KB pages here.

# Acceptance Criteria

- [ ] Concrete condition 1
- [ ] Concrete condition 2
- [ ] Tests or audit command passes
- [ ] Run report is written under `.ai/runs/`

# Verification Commands

```bash
python3 -m pytest tests/test_target.py
```

# Codex Instructions

Work in this repository. Respect existing uncommitted changes. Do not revert user changes.
Investigate first, then implement the smallest safe change. Run the listed verification commands.
In the final report, include status, files changed, verification output summary, remaining risks, and next recommended task.
