# Sub 1c: app.py Web/API Path

## Scope
- `app.py:1-31`
- `app.py:100-230`
- `app.py:9450-9516`
- `app.py:9517-9639`
- `app.py:9640-9919`
- `app.py:9919-10078`
- `app.py:10079-10293`
- `app.py:10493-11102`
- `app.py:11321-11434`
- `app.py:11906-12330`
- `app.py:12334-12500`
- `app.py:12504-13189`
- `app.py:13190-13580`
- `app.py:13580-13620`
- `app.py:13621-13863`
- `app.py:13855-14024`

## 1. Bugs Found
| # | Severity | File:Line | Description | Root Cause | Suggested Fix |
|---|----------|-----------|-------------|-----------|--------------|
| 1 | Sev1 | `app.py:118-145`, `app.py:11906-11918`, `app.py:11093-11101`, `app.py:12334-12340`, `app.py:11965-11993`, `app.py:13526-13533`, `app.py:13554-13563` | `_require_auth()` is allowlist-based and skips all `GET`, so several state-changing endpoints are unauthenticated: `POST /api/strategy-mode`, `GET /api/ml-train`, `GET /healthz` (`request_tick()`), `GET /api/cron` (BT cache clear), `GET /api/demo/learning?run=true`, `GET /api/demo/daily-review?run=true`. `POST /api/strategy-mode` changes live signal behavior immediately. | Auth is keyed to `_PROTECTED_PREFIXES` plus `request.method != "GET"` instead of “all mutating routes must authenticate”. | Invert policy: explicitly mark mutating routes as protected, or enforce auth for all non-idempotent routes regardless of verb. Convert `ml-train`, `learning run`, `daily-review run`, `cron refresh`, `healthz tick` into authenticated `POST`. |
| 2 | Sev1 | `app.py:10693-11070`, `app.py:10493-10499` | `/api/pattern-analysis` and `/api/evaluation` are unauthenticated heavy GET jobs with no rate limiting and unbounded `days` input. `pattern-analysis` also appends to analyst memory on every request (`app.py:11024-11045`), so a caller can force repeated long BT-like scans plus disk writes. | No input caps, no auth, no rate limiting, and side effects on GET. | Cap `days`, whitelist intervals, make these endpoints authenticated `POST`, add per-IP/token rate limits, and remove file writes from read-only analysis endpoints. |
| 3 | Sev2 | `app.py:9849-9916` | `POST /api/admin/regenerate-tier-master` bypasses the global Bearer auth entirely because its path is absent from `_PROTECTED_PREFIXES`. If `ADMIN_API_TOKEN` is unset, anyone can rewrite `tier-master.json`; if set, the fallback `?token=` path leaks admin secrets into logs/referers (`app.py:9871`). | Separate ad hoc auth scheme was added, but not integrated with `_require_auth`; query-string secret is accepted. | Add this route to the main auth policy, require header-only admin auth, and fail closed when `ADMIN_API_TOKEN` is missing. |
| 4 | Sev2 | `app.py:9975-10000`, `app.py:279-370`, `app.py:9937-9951` | `/api/performance/record` accepts arbitrary `signal/mode/tf/outcome` strings and unchecked numeric ranges (`rr_ratio`, `confidence`, prices). Those rows directly feed `compute_kpi()` and `/api/performance`, so a caller can silently poison monitoring KPIs. | Presence checks exist, but no enum/range validation before persistence. | Validate enums, bound numeric ranges, reject nonsensical prices/RR, and store source/audit metadata so manual records are separable from production telemetry. |
| 5 | Sev2 | `app.py:13665-13679` | `api_risk_dashboard` reports `dd_pct = dd / 1000`, not drawdown relative to equity peak/current. This makes the reported drawdown percentage structurally wrong and can mislead risk decisions. | Hardcoded denominator `max(1000.0, 1.0)` instead of equity base. | Compute `dd_pct` from `eq_peak` (or agreed capital baseline) and return both absolute and relative DD with definition in payload. |
| 6 | Sev3 | `app.py:196-201` | `_bounded_cache_set()` is not actually LRU. Reassigning an existing key does not refresh insertion order, so a hot key can still be evicted next. It is also not TTL-aware, despite being used in a cache subsystem with TTL semantics elsewhere. | Plain dict insertion-order deletion is being treated as LRU. | Use `OrderedDict.move_to_end()`/`functools.lru_cache`-style logic, or store `(value, ts)` and evict by recency plus TTL consistently. |

## 2. Structural Issues
1. `_wilson_lower` duplication is not in `modules/risk_analytics.py`; the actual duplicate is `app.py:9517-9526` and `modules/demo_db.py:25-34`. This risks silent drift across APIs. Move to one shared stats utility and import it from both call sites.

2. `api_phase_gate` matches roadmap threshold math for Gate 1-4 (`app.py:13690-13773`) and roadmap text (`knowledge-base/wiki/syntheses/roadmap-v2.1.md:24-29`), but it omits Gate 0 entirely and does not emit the required lot-step transitions (`0.2x→0.3x`, `0.3x→0.5x`, `Kelly Half 3.0lot`). As written, the API cannot represent full roadmap readiness.

3. `api_strategies_status` exposes tier labels and per-strategy stats (`app.py:9640-9846`), but not the Gate 0 structure from roadmap-v2.1: DT LIVE + Scalp SENTINEL + AVOID全停止. There is no aggregate DT/Scalp/AVOID readiness summary, so operators must infer gate readiness manually.

4. `api_strategies_status` blindly generates `wiki_slug` via underscore-to-hyphen replacement (`app.py:9731-9773`), and the UI turns that into a GitHub doc URL (`templates/strategies.html:1083-1088`) without existence checks. The repo already has missing strategy docs for known names such as `h1-breakout-retest.md`, `h1-fib-reversal.md`, and `h1-ema200-trend-reversal.md` while those strategy IDs still exist in code (`app.py:12711-12733`). This is a dead-link factory.

5. `api_performance` delegates to `compute_kpi()` (`app.py:9937-9947`), but that KPI model only returns WR/EV/Sharpe/Sortino/Calmar/PF/DD (`app.py:279-370`). It does not expose Kelly, Wilson CI, or DSR, so the monitoring path is not aligned with the roadmap’s gating metrics.

6. No direct `sqlite3` usage exists in the scoped `app.py` paths; DB access is delegated to `DemoDB`. Within this scope I found no direct SQL injection sink in `app.py` itself. Injection risk, if any, is downstream in `modules/demo_db.py` and out of scope here.

7. The Bearer token is injected into rendered pages (`app.py:9506-9514`, `app.py:13190-13192`) and copied into browser-side JS fetch wrappers (`templates/demo_analysis.html:595-606`, `templates/oanda_analysis.html:373-384`). That makes the shared API credential available to any script running in those pages, expanding the blast radius of any future XSS.

## 4. Roadmap Alignment
- The biggest blocker from this scope is control-plane integrity, not alpha math: unauthenticated mode changes, training, learning, and cache-refresh jobs can alter live behavior or starve the process before Gate metrics mean anything.
- Gate reporting is incomplete. `api_phase_gate` covers Gate 1-4 thresholds but not Gate 0 or the lot progression required by `roadmap-v2.1.md:24-29`. `api_strategies_status` likewise does not expose a Gate-0-ready aggregate view.
- The DD percentage bug in `api_risk_dashboard` undermines the roadmap’s DD-based scaling discipline because the returned `%` is not economically meaningful.
- `api_performance` is not a roadmap-grade KPI surface because it omits Kelly/Wilson/DSR, so operators can watch a “green” KPI page while the actual gate metrics remain red.

## 5. Top 3 Action Items (impact 順)
1. Close the auth model around all state-changing routes and eliminate stateful GETs — Impact: prevents unauthorized live-mode flips, background job abuse, and control-plane drift — Confidence: high
2. Put hard caps + rate limits on heavy analysis endpoints (`pattern-analysis`, `evaluation`, similar BT surfaces) — Impact: reduces live-service DoS risk and preserves data-collection uptime needed for Gate progression — Confidence: high
3. Fix metric/reporting integrity in `api_risk_dashboard` and extend gate/performance payloads to include Gate 0, lot-step outputs, Kelly/Wilson/DSR — Impact: restores roadmap-faithful scaling decisions and monitoring — Confidence: medium

## 6. Out-of-Scope Findings (オプション)
- The `_wilson_lower` duplicate the brief asked me to compare against `modules/risk_analytics.py` does not exist there; the real duplicate is in `modules/demo_db.py:25-34`.
- `modules/demo_trader.py` already contains a note that some 1H strategy files are dead code / missing docs, which is consistent with the dead-link issue surfaced from this API layer.
