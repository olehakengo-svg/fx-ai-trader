# Codex Task — Phase 1a: dexter `get_oanda_labs_sentiment`

- **Repo**: `/Users/jg-n-012/test/dexter/`
- **Parent context**: Wave 6 closed → Phase B (Outlook contrarian) → OANDA Japan labs API discovered as historical retail sentiment source
- **Scope**: 1 LangChain tool that hits OANDA's public GraphQL labs API. ~150-180 lines TypeScript + tests.
- **Created**: 2026-05-07
- **Verified**: Live API empirically tested 2026-05-07 19:00-21:10

This file is the **Codex-ready prompt**. Section 10 has the paste-able prompt body.

## 1. Goal

Add `get_oanda_labs_sentiment` to dexter. It returns retail-trader long/short sentiment **time series** for 16 instruments, sourced from OANDA's public labs GraphQL endpoint that powers their public widget. This unlocks Phase 1b BT (contrarian filter research against MASSIVE OHLC).

## 2. Mirror pattern (read first)

- `src/tools/finance/get_cot_report.ts` — cache + TTL + zod + DynamicStructuredTool + formatToolResult
- `src/tools/finance/get_myfxbook_outlook.ts` — JSON API + retry + maskSession (just merged commit 014f531) — closest analog
- `src/tools/finance/types.ts` — `formatToolResult` lives here (NOT in `src/tools/finance/types.ts`)
- `tests/tools/get_myfxbook_outlook.test.ts` — bun:test mock pattern

Mirror these exactly. Do NOT introduce a new HTTP client or test runner.

## 3. Files

### Create

- `src/tools/finance/get_oanda_labs_sentiment.ts` — the tool
- `tests/tools/get_oanda_labs_sentiment.test.ts` — unit tests with mocked fetch
- `tests/tools/get_oanda_labs_sentiment.e2e.test.ts` — E2E against the real API (NO env required, public endpoint)

### Modify

- `src/tools/finance/index.ts` — add `export { getOandaLabsSentiment, GET_OANDA_LABS_SENTIMENT_DESCRIPTION } from './get_oanda_labs_sentiment.js';`
- `README.md` — one-paragraph entry under finance tools

## 4. API contract — verified 2026-05-07 against live endpoint

### 4.1 Endpoint

```
POST https://labs-api.oanda.com/graphql
Headers:
  Content-Type: application/json
  Origin: https://www.oanda.jp           (REQUIRED — without this the API can return INTERNAL_ERROR)
  Referer: https://www.oanda.jp/lab-education/oanda_lab/oanda_rab/orderbook_history/
  User-Agent: Mozilla/5.0
```

**No auth token needed.** This is a public widget-backing API. CORS-protected via Origin check, so set the OANDA Japan origin header.

### 4.2 GraphQL query

```graphql
query GetSentiments(
  $instrument: String!
  $granularity: Granularity!
  $timeSpan: TimeSpan!
) {
  sentiments(
    instrument: $instrument
    granularity: $granularity
    timeSpan: $timeSpan
  ) {
    sentiments {
      sentiment {
        shortPercent
      }
      time
    }
  }
}
```

### 4.3 Variables — only 2 valid combos (empirically tested)

| `granularity` | `timeSpan` | Points returned | Coverage |
|---|---|---:|---|
| `H1` | `TWENTY_DAYS` | ~480 | 20 days, hourly |
| `H4` | `NINETY_DAYS` | ~541 | 90 days, 4-hour |

All other combinations return `INTERNAL_ERROR`. The tool MUST accept only these two presets and reject any other granularity/timeSpan combination at the Zod validation layer.

### 4.4 Valid `instrument` values (16 total)

```
EUR_USD, USD_JPY, GBP_USD, AUD_USD, USD_CAD, USD_CHF, NZD_USD,
EUR_JPY, GBP_JPY, AUD_JPY, EUR_AUD, EUR_GBP, EUR_CHF, GBP_CHF,
XAU_USD, XAG_USD
```

Note user feedback `feedback_exclude_xau.md` excludes XAU from analysis BUT this is a generic data tool, so include both XAU_USD and XAG_USD in the enum (downstream code handles exclusion).

### 4.5 Response shape (verified)

```json
{
  "data": {
    "sentiments": {
      "sentiments": [
        { "sentiment": { "shortPercent": 67.1753 }, "time": "2026-05-07T09:00:00Z" },
        { "sentiment": { "shortPercent": 67.25 },   "time": "2026-05-07T05:00:00Z" },
        { "sentiment": { "shortPercent": 66.5113 }, "time": "2026-05-07T01:00:00Z" }
      ]
    }
  }
}
```

Times are ISO 8601 UTC. The list is **most-recent-first**.

### 4.6 Error shape

```json
{
  "errors": [
    { "message": "INTERNAL_ERROR", "extensions": { "classification": "INTERNAL_ERROR" } }
  ],
  "data": null
}
```

When this comes back, surface as a structured tool error (do not throw), so the agent can see it.

## 5. Implementation requirements

### 5.1 Zod input schema

```ts
const InstrumentSchema = z.enum([
  'EUR_USD','USD_JPY','GBP_USD','AUD_USD','USD_CAD','USD_CHF','NZD_USD',
  'EUR_JPY','GBP_JPY','AUD_JPY','EUR_AUD','EUR_GBP','EUR_CHF','GBP_CHF',
  'XAU_USD','XAG_USD',
]);

const PresetSchema = z.enum(['h1_20d', 'h4_90d']).describe(
  'Resolution preset. h1_20d = hourly, last 20 days (~480 points). h4_90d = 4-hour, last 90 days (~541 points).'
);

const Input = z.object({
  instrument: InstrumentSchema,
  preset: PresetSchema.default('h4_90d'),
});
```

### 5.2 Tool description (used by LLM agent)

> Returns OANDA retail trader sentiment (short %) time series for a major FX pair. Sourced from OANDA's public labs API (no authentication). Two presets: h1_20d (hourly, 20-day) for short-term tactical research, h4_90d (4-hour, 90-day) for longer baseline. Times are UTC ISO-8601, list returned most-recent-first.

### 5.3 Output (via `formatToolResult`)

```ts
{
  fetched_at: string,                    // ISO 8601, when this fetch ran
  instrument: string,                    // echoed input
  granularity: 'H1' | 'H4',
  time_span: 'TWENTY_DAYS' | 'NINETY_DAYS',
  point_count: number,
  points: Array<{
    time: string,                        // ISO 8601 UTC, server-provided
    short_pct: number,                   // 0–100
    long_pct: number,                    // 100 - short_pct, computed
  }>,
}
```

`sourceUrls`: include the GraphQL endpoint URL (no query params; everything is in POST body, so just the bare URL).

### 5.4 Cache

- Dir: `.dexter/cache/oanda-labs-sentiment/`
- Filename: `${instrument}-${preset}.json` after regex validation (mirror the `get_cot_report.ts` pattern at L75-88)
- TTL: **5 minutes** (matches Myfxbook outlook tool, sentiment doesn't change faster)
- Both presets share the same cache dir but different filenames

### 5.5 Preset → variables mapping (in code)

```ts
const PRESET_TO_VARS = {
  h1_20d: { granularity: 'H1', timeSpan: 'TWENTY_DAYS' },
  h4_90d: { granularity: 'H4', timeSpan: 'NINETY_DAYS' },
} as const;
```

### 5.6 HTTP rules

- POST with the headers from §4.1 — **Origin header is required**, do not skip it
- Timeout: 30s
- Retry: only on 5xx, max 2 retries with exponential backoff
- No rate limit token bucket needed for one-shot calls; the cache handles repeat traffic

### 5.7 Error handling

- HTTP error (non-2xx): return `formatToolResult({ error: 'OANDA labs request failed', status })`
- GraphQL `errors` array: return `formatToolResult({ error: 'OANDA labs query rejected', graphql_errors: [...] })`
- Empty `sentiments.sentiments` list (rare but possible): return success with `point_count: 0` and empty `points` (don't error)

### 5.8 Security checklist

- [ ] No auth token used (this is a public API), but ensure the tool does NOT pass through any header from the environment that might leak credentials
- [ ] Cache filename built from regex-validated instrument and preset
- [ ] No `console.log` of full response bodies
- [ ] Cache writes only the parsed structured output (not raw GraphQL response)

## 6. Tests

### 6.1 Unit tests (`tests/tools/get_oanda_labs_sentiment.test.ts`)

Mock `globalThis.fetch` with bun:test mock. Cover:

1. Happy path h4_90d: returns parsed structured data with 541 points
2. Happy path h1_20d: returns parsed structured data with 480 points
3. Cache hit within 5min: second call uses cache, no second fetch
4. Cache TTL expiry: file mtime > 5min triggers re-fetch
5. Invalid instrument (not in enum): zod rejection
6. Invalid preset (e.g., 'm5_2d'): zod rejection
7. GraphQL `errors` response: returns structured error
8. HTTP 500: returns structured error after 2 retries
9. Empty sentiment list: returns success with point_count: 0
10. Verifies `Origin` header is set on the fetch call
11. `long_pct = 100 - short_pct` correctly computed

Use a small inline fixture in the test file. No fixtures dir.

### 6.2 E2E test (`tests/tools/get_oanda_labs_sentiment.e2e.test.ts`)

```ts
import { describe, expect, test } from 'bun:test';

// Public API, no env needed
describe('get_oanda_labs_sentiment (e2e)', () => {
  test('fetches real EUR_USD h4_90d data', async () => {
    const { getOandaLabsSentiment } = await import('../../src/tools/finance/get_oanda_labs_sentiment.js');
    const raw = await getOandaLabsSentiment.invoke({ instrument: 'EUR_USD', preset: 'h4_90d' });
    const result = JSON.parse(String(raw));
    expect(result.data.point_count).toBeGreaterThan(400);
    expect(result.data.points[0].short_pct).toBeGreaterThan(0);
    expect(result.data.points[0].short_pct).toBeLessThan(100);
    // Within 95-105 (data sometimes rounds)
    const sum = result.data.points[0].short_pct + result.data.points[0].long_pct;
    expect(sum).toBeGreaterThan(95);
    expect(sum).toBeLessThan(105);
    // Verify time format
    expect(result.data.points[0].time).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  }, 30_000);

  test('h1_20d returns ~480 points', async () => {
    const { getOandaLabsSentiment } = await import('../../src/tools/finance/get_oanda_labs_sentiment.js');
    const raw = await getOandaLabsSentiment.invoke({ instrument: 'USD_JPY', preset: 'h1_20d' });
    const result = JSON.parse(String(raw));
    expect(result.data.point_count).toBeGreaterThan(400);
    expect(result.data.granularity).toBe('H1');
  }, 30_000);
});
```

E2E **must** pass against the real `labs-api.oanda.com` endpoint. No auth needed.

`feedback_codex_mock_test_trap.md` — both unit AND E2E must pass.

## 7. Done conditions

```bash
cd /Users/jg-n-012/test/dexter
bun run typecheck                                            # type-clean
bun test tests/tools/get_oanda_labs_sentiment.test.ts        # unit pass
bun test tests/tools/get_oanda_labs_sentiment.e2e.test.ts    # E2E pass
```

All three must pass. Then surface to Claude Code with:
- diff of created/modified files
- E2E test stdout showing real point counts
- typecheck output

## 8. Out of scope (explicit non-goals)

- `GetOrderPositionBooks` query (Phase 1a-2, separate task) — focus solely on `GetSentiments` for now
- `GetPriceCandles` query (we use MASSIVE for OHLC, not OANDA labs)
- Cron polling / time-series accumulation (Phase 1c, separate task)
- Strategy back-test (Phase 1b, separate task after this tool is in place)
- New test fixture directory — keep fixtures inline in test files

## 9. Why this is the right scope

Per `feedback_shadow_first_quant_architecture.md`: build the data tap first, then evaluate cell-by-cell whether contrarian filtering improves Wilson lo / Bonferroni-survival. The tool must exist before any BT can run. This task is the data tap.

Per `feedback_partial_quant_trap.md`: implementing the tool does NOT commit to the strategy. Strategy approval requires N + Wilson + WF + Bonferroni + cell audit, which is downstream Phase 1b work and explicitly NOT this task.

---

## 10. Codex prompt (paste this)

```
Repo: dexter (current working directory)

Task: Add a new LangChain MCP tool `get_oanda_labs_sentiment` to dexter, fetching retail trader sentiment time series from OANDA's public labs GraphQL API. No authentication required — this is a public widget-backing endpoint.

Read these files first to learn the exact patterns to mirror:
- src/tools/finance/get_cot_report.ts
- src/tools/finance/get_myfxbook_outlook.ts (just-merged similar API tool)
- src/tools/types.ts (formatToolResult helper — note: in src/tools/types.ts, NOT src/tools/finance/types.ts)
- src/tools/finance/index.ts
- tests/tools/get_myfxbook_outlook.test.ts

Then implement per spec:
/Users/jg-n-012/test/fx-ai-trader/docs/superpowers/specs/2026-05-07-codex-phase1a-oanda-labs-sentiment.md

Critical points (also in spec §4 and §5):
1. Endpoint: POST https://labs-api.oanda.com/graphql (no auth)
2. Required header: Origin: https://www.oanda.jp (without this, API returns INTERNAL_ERROR)
3. Only 2 valid (granularity, timeSpan) combos:
   - h1_20d -> { granularity: 'H1', timeSpan: 'TWENTY_DAYS' }
   - h4_90d -> { granularity: 'H4', timeSpan: 'NINETY_DAYS' }
   Reject all others at Zod layer.
4. 16 valid instruments — see spec §4.4.
5. Cache to .dexter/cache/oanda-labs-sentiment/ with 5min TTL, regex-validated filename.
6. Output: { fetched_at, instrument, granularity, time_span, point_count, points: [{ time, short_pct, long_pct }] }, list most-recent-first.

Done criteria:
- bun run typecheck clean
- unit tests pass: bun test tests/tools/get_oanda_labs_sentiment.test.ts
- E2E pass against real labs-api.oanda.com: bun test tests/tools/get_oanda_labs_sentiment.e2e.test.ts (no env required)

Stop and ask if anything in the spec is ambiguous. Do NOT invent additional GraphQL fields or attempt unsupported granularity/timeSpan combos. The Origin header is non-negotiable.
```
