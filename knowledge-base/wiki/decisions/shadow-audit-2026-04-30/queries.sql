-- Shadow audit 2026-04-30 — re-runnable queries
-- Source of truth: Render production postgres (fx-ai-trader)
-- Local sqlite mirror is dev-only and lags production (CLAUDE.md rule)

-- 0) Day-level shadow vs live counts and PnL
SELECT
  is_shadow,
  COUNT(*) AS n,
  SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) AS losses,
  SUM(CASE WHEN outcome='BREAKEVEN' THEN 1 ELSE 0 END) AS bes,
  ROUND(SUM(pnl_pips)::numeric, 1) AS sum_pips,
  ROUND(AVG(pnl_pips)::numeric, 2) AS ev_pips,
  SUM(CASE WHEN dedup_violation=1 THEN 1 ELSE 0 END) AS dedup_v,
  SUM(CASE WHEN instrument LIKE '%XAU%' THEN 1 ELSE 0 END) AS xau_n
FROM demo_trades
WHERE status='CLOSED'
  AND entry_time::date = '2026-04-30'
GROUP BY is_shadow
ORDER BY is_shadow;

-- 1) Strategy-level shadow metrics (4/30)
SELECT
  entry_type,
  COUNT(*) AS n,
  ROUND(AVG(CASE WHEN outcome='WIN' THEN 100.0 ELSE 0 END)::numeric, 1) AS wr_pct,
  SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) AS losses,
  ROUND(SUM(pnl_pips)::numeric, 1) AS sum_pips,
  ROUND(AVG(pnl_pips)::numeric, 2) AS ev_pips,
  ROUND(SUM(CASE WHEN pnl_pips>0 THEN pnl_pips ELSE 0 END)::numeric, 1) AS gross_win,
  ROUND(SUM(CASE WHEN pnl_pips<0 THEN -pnl_pips ELSE 0 END)::numeric, 1) AS gross_loss
FROM demo_trades
WHERE status='CLOSED'
  AND entry_time::date = '2026-04-30'
  AND is_shadow=1
GROUP BY entry_type
ORDER BY sum_pips DESC;

-- 2) rsk_gbpjpy_reversion firing pattern (per-bar dedup gate diagnostic)
WITH rsk AS (
  SELECT trade_id, entry_time, direction, sl, tp, pnl_pips, outcome, dedup_violation,
    LAG(entry_time) OVER (ORDER BY entry_time) AS prev_entry_time
  FROM demo_trades
  WHERE status='CLOSED'
    AND entry_time::date = '2026-04-30'
    AND is_shadow=1
    AND entry_type='rsk_gbpjpy_reversion'
)
SELECT
  COUNT(*) AS n,
  SUM(CASE WHEN EXTRACT(EPOCH FROM (entry_time - prev_entry_time)) < 60 THEN 1 ELSE 0 END) AS gap_lt_60s,
  SUM(CASE WHEN EXTRACT(EPOCH FROM (entry_time - prev_entry_time)) < 90 THEN 1 ELSE 0 END) AS gap_lt_90s,
  ROUND(EXTRACT(EPOCH FROM AVG(entry_time - prev_entry_time))::numeric, 1) AS avg_gap_sec,
  COUNT(DISTINCT (direction, ROUND(sl::numeric, 3), ROUND(tp::numeric, 3))) AS unique_signatures
FROM rsk;

-- 3) Hour-of-day shadow distribution (runaway detection)
SELECT
  EXTRACT(HOUR FROM entry_time AT TIME ZONE 'UTC') AS utc_hour,
  COUNT(*) AS n,
  ROUND(SUM(pnl_pips)::numeric, 1) AS sum_pips
FROM demo_trades
WHERE status='CLOSED'
  AND entry_time::date = '2026-04-30'
  AND is_shadow=1
GROUP BY utc_hour
ORDER BY utc_hour;

-- 4) Close reason cross-tab × shadow flag (BE/Trail effect detection)
SELECT
  close_reason,
  is_shadow,
  COUNT(*) AS n,
  ROUND(SUM(pnl_pips)::numeric, 1) AS sum_pips
FROM demo_trades
WHERE status='CLOSED'
  AND entry_time::date = '2026-04-30'
GROUP BY close_reason, is_shadow
ORDER BY n DESC;

-- 5) Top10 winners + Bottom10 losers (right-tail concentration)
(SELECT trade_id, entry_type, instrument, direction, is_shadow, pnl_pips, close_reason
 FROM demo_trades
 WHERE status='CLOSED' AND entry_time::date = '2026-04-30' AND is_shadow=1
 ORDER BY pnl_pips DESC LIMIT 10)
UNION ALL
(SELECT trade_id, entry_type, instrument, direction, is_shadow, pnl_pips, close_reason
 FROM demo_trades
 WHERE status='CLOSED' AND entry_time::date = '2026-04-30' AND is_shadow=1
 ORDER BY pnl_pips ASC LIMIT 10);

-- 6) Shadow ⇄ OANDA misroute check (must return 0)
SELECT COUNT(*) AS misroute_count
FROM demo_trades dt
JOIN oanda_audit oa ON oa.demo_trade_id = dt.trade_id
WHERE dt.status='CLOSED'
  AND dt.entry_time::date = '2026-04-30'
  AND dt.is_shadow=1
  AND oa.bridge_status IN ('sent','filled');

-- 7) PnL reconciliation diagnostic (must return 0 mismatches)
SELECT trade_id, entry_type, instrument, direction, pnl_pips,
  ROUND(((exit_price - entry_price) *
    CASE WHEN instrument LIKE '%JPY%' THEN 100.0 ELSE 10000.0 END *
    CASE WHEN direction='BUY' THEN 1 ELSE -1 END)::numeric, 2) AS computed_pips,
  ROUND((pnl_pips - ((exit_price - entry_price) *
    CASE WHEN instrument LIKE '%JPY%' THEN 100.0 ELSE 10000.0 END *
    CASE WHEN direction='BUY' THEN 1 ELSE -1 END))::numeric, 2) AS diff
FROM demo_trades
WHERE status='CLOSED'
  AND entry_time::date = '2026-04-30'
  AND is_shadow=1
  AND ABS(pnl_pips - ((exit_price - entry_price) *
        CASE WHEN instrument LIKE '%JPY%' THEN 100.0 ELSE 10000.0 END *
        CASE WHEN direction='BUY' THEN 1 ELSE -1 END)) > 1.0;

-- 8) Counterfactual: PnL excluding rsk + vsg runaway
SELECT
  COUNT(*) AS n,
  ROUND(SUM(pnl_pips)::numeric, 1) AS sum_pips
FROM demo_trades
WHERE status='CLOSED'
  AND entry_time::date = '2026-04-30'
  AND is_shadow=1
  AND entry_type NOT IN ('rsk_gbpjpy_reversion','vsg_jpy_reversal');
