# Session MR Cross Wave 1 BT

- wave1_verdict: BLOCKED_PRECONDITION
- generated_at: 2026-05-11T04:40:56.566804+00:00
- data_source: MASSIVE local parquet only

| Cell | Pair | Window | Status | N | WR | EV | PF | Wilson | Bonf-p | WF EV+ | Verdict |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| C1 | EUR_NZD | NY_LATE | BLOCKED_DATA | 0 | 0.0 | 0.0 | None | 0.0 | None | 0/4 | BLOCKED_DATA |
| C2 | EUR_NZD | TOKYO_OPEN | BLOCKED_DATA | 0 | 0.0 | 0.0 | None | 0.0 | None | 0/4 | BLOCKED_DATA |
| C3 | AUD_NZD | NY_LATE | BLOCKED_DATA | 0 | 0.0 | 0.0 | None | 0.0 | None | 0/4 | BLOCKED_DATA |
| C4 | AUD_NZD | TOKYO_OPEN | BLOCKED_DATA | 0 | 0.0 | 0.0 | None | 0.0 | None | 0/4 | BLOCKED_DATA |
| C5 | AUD_CAD | NY_LATE | BLOCKED_DATA | 0 | 0.0 | 0.0 | None | 0.0 | None | 0/4 | BLOCKED_DATA |
| C6 | AUD_CAD | TOKYO_OPEN | BLOCKED_DATA | 0 | 0.0 | 0.0 | None | 0.0 | None | 0/4 | BLOCKED_DATA |
| C7 | NZD_CAD | NY_LATE | BLOCKED_DATA | 0 | 0.0 | 0.0 | None | 0.0 | None | 0/4 | BLOCKED_DATA |
| C8 | NZD_CAD | TOKYO_OPEN | BLOCKED_DATA | 0 | 0.0 | 0.0 | None | 0.0 | None | 0/4 | BLOCKED_DATA |
| C9 | EUR_GBP | NY_LATE | BLOCKED_DATA | 0 | 0.0 | 0.0 | None | 0.0 | None | 0/4 | BLOCKED_DATA |
| C10 | EUR_GBP | TOKYO_OPEN | BLOCKED_DATA | 0 | 0.0 | 0.0 | None | 0.0 | None | 0/4 | BLOCKED_DATA |

## Blockers

- C1 EUR_NZD NY_LATE: missing_cache (data/cache/massive/EUR_NZD_5m.parquet)
- C2 EUR_NZD TOKYO_OPEN: missing_cache (data/cache/massive/EUR_NZD_5m.parquet)
- C3 AUD_NZD NY_LATE: missing_cache (data/cache/massive/AUD_NZD_5m.parquet)
- C4 AUD_NZD TOKYO_OPEN: missing_cache (data/cache/massive/AUD_NZD_5m.parquet)
- C5 AUD_CAD NY_LATE: missing_cache (data/cache/massive/AUD_CAD_5m.parquet)
- C6 AUD_CAD TOKYO_OPEN: missing_cache (data/cache/massive/AUD_CAD_5m.parquet)
- C7 NZD_CAD NY_LATE: missing_cache (data/cache/massive/NZD_CAD_5m.parquet)
- C8 NZD_CAD TOKYO_OPEN: missing_cache (data/cache/massive/NZD_CAD_5m.parquet)
- C9 EUR_GBP NY_LATE: insufficient_span (data/cache/massive/EUR_GBP_5m.parquet)
- C10 EUR_GBP TOKYO_OPEN: insufficient_span (data/cache/massive/EUR_GBP_5m.parquet)
