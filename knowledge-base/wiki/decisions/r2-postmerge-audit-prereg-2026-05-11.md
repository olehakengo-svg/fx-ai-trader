# Pre-Registration: R2 Post-Merge Gate 0 Audit - 2026-05-11

Status: **LOCKED at commit time; post-hoc cutoff changes are forbidden.**

## Scope

- Primary source: Render API `/api/demo/trades?limit=100000` JSON export only.
- Local DB, `.env`, OANDA credentials, and local `app.py` are out of scope.
- TRUE_LIVE: `is_shadow=0 AND oanda_trade_id != ''`.
- FLAG_DRIFT: `is_shadow=0 AND (oanda_trade_id IS NULL OR oanda_trade_id='')`; excluded.
- SHADOW: `is_shadow=1`; excluded and must not mix into TRUE_LIVE.
- TRUE_LIVE XAU rows are forbidden for this audit; non-target XAU rows are excluded before metrics.
- LOCK deploy timestamp: `TODO_AFTER_C52D8E3_PUSH`.

## Hypotheses

- H1: post-LOCK TRUE_LIVE new N has aggregate raw Kelly >= 0 / EV >= 0 enough to ACCEPT Gate 0.
- H0: post-LOCK TRUE_LIVE new N remains raw Kelly < 0, requiring additional cell-level demotion.

## Frozen Cutoffs

| metric | ACCEPT | NEEDS_MORE_EVIDENCE | REJECT |
|---|---|---|---|
| N_post_lock TRUE_LIVE | >= 30 | 15 <= N < 30 | < 15 |
| Aggregate raw Kelly | >= +0.005 | -0.010 <= K < +0.005 | < -0.010 |
| Aggregate EV pip | >= -0.10 | -0.30 <= EV < -0.10 | < -0.30 |
| Wilson 95% lower WR | >= BEV_WR | BEV_WR-3pp <= Wilson < BEV_WR | < BEV_WR-3pp |
| Cell-level Bonferroni | all 15 cells improve vs pre-LOCK | partial/no post-N | any cell regresses vs pre-LOCK |

- Bonferroni family K: **15** locked cells; alpha' = 0.05 / 15 = **0.003333**.
- LOCKED_BEV_WR: **0.3658** from pair-weighted TRUE_LIVE snapshot using `friction-analysis.md` BEV_WR table.
- Final verdict rule: all registered criteria ACCEPT => ACCEPT; any registered criterion REJECT => REJECT; otherwise NEEDS_MORE_EVIDENCE.

## Pre-LOCK Snapshot

- Snapshot source: `/tmp/render-trades-prelock-snapshot.json`
- TRUE_LIVE snapshot N: 740
- Snapshot aggregate raw Kelly: -0.1889
- Snapshot aggregate EV: -0.82 pip
- Snapshot Wilson lower: 35.60%

| # | strategy | instrument | hour_bucket | N | WR | EV pip | Wilson lo | raw Kelly |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | ema_cross | USD_JPY | 16 | 5 | 0.00% | -8.40 | 0.00% | +0.0000 |
| 2 | vol_surge_detector | USD_JPY | 00 | 4 | 0.00% | -3.40 | 0.00% | +0.0000 |
| 3 | bb_rsi_reversion | USD_JPY | 13 | 4 | 25.00% | -4.42 | 4.56% | -11.0625 |
| 4 | bb_rsi_reversion | EUR_USD | 06 | 5 | 0.00% | -2.68 | 0.00% | +0.0000 |
| 5 | bb_rsi_reversion | USD_JPY | 18 | 10 | 40.00% | -0.70 | 16.82% | -0.1892 |
| 6 | fib_reversal | EUR_USD | 15 | 5 | 0.00% | -1.68 | 0.00% | +0.0000 |
| 7 | macdh_reversal | EUR_USD | 07 | 5 | 40.00% | -1.52 | 11.76% | -1.1259 |
| 8 | bb_rsi_reversion | USD_JPY | 10 | 2 | 0.00% | -2.45 | 0.00% | +0.0000 |
| 9 | bb_rsi_reversion | USD_JPY | 11 | 6 | 50.00% | -0.25 | 18.76% | -0.0824 |
| 10 | macdh_reversal | EUR_USD | 14 | 8 | 25.00% | -0.86 | 7.15% | -0.2240 |
| 11 | bb_rsi_reversion | USD_JPY | 17 | 5 | 60.00% | -0.22 | 23.07% | -0.1347 |
| 12 | bb_rsi_reversion | EUR_USD | 12 | 1 | 100.00% | +2.00 | 20.65% | +0.0000 |
| 13 | bb_rsi_reversion | USD_JPY | 02 | 9 | 55.56% | +0.03 | 26.66% | +0.0165 |
| 14 | fib_reversal | USD_JPY | 04 | 7 | 42.86% | -0.21 | 15.82% | -0.0765 |
| 15 | bb_rsi_reversion | EUR_USD | 09 | 5 | 40.00% | -0.50 | 11.76% | -0.2273 |

## Audit Commands

```bash
curl -sS 'https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000' \
  -o /tmp/render-trades-20260511.json
python3 tools/r2_postmerge_audit.py \
  --trades /tmp/render-trades-20260511.json \
  --lock-deploy-ts TODO_AFTER_C52D8E3_PUSH \
  --output knowledge-base/wiki/decisions/r2-postmerge-audit-2026-05-11.md
```

## Locked Actions

- ACCEPT: unlock only the approval path for A3-simple dispatch and Gate 1 0.3x lot; do not apply those actions in this audit script.
- NEEDS_MORE_EVIDENCE: extend the audit window by +7 days under the same criteria.
- REJECT: keep A3-simple blocked and open a separate cell-level demotion RCA.
