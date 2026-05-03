# Global Retail FX Edges 2026-05-03

> Note: original catalog file was absent in this checkout; this file records the required C-1 status update proposal for W3-4.
## 2026-05-03 C-1 London Open Breakout status update proposal

- Status proposal: **BLOCKED_DATA / 判定保留**
- Internal BT runner/artifact: `knowledge-base/raw/bt-results/c1-london-breakout.json`
- Reason: requested GBPJPY M5 2014-01-01〜2026-04-30 coverage was not available in this checkout; local cache covers only 2025-10-14〜2026-04-15 (184 days, 4.09%).
- Primary partial result: N=29, WR=44.83%, Wilson lo=28.41%, PF=1.110, Bonferroni fail, null bootstrap fail. This partial window is not valid for Rule 1 accept/reject.
- Required next evidence: full 12-year M5 cache + Render rsk_gbpjpy_reversion PnL series + independent broker M5 cross-check.
