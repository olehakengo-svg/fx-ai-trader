# PYR backfill dry-run and verify final

## Deploy verification

- Requested deploy: `dep-d8ak99p9rddc73bac060` on `srv-d6va1of5r7bs73en10vg`.
- Render REST status could not be verified from this worker: unauthenticated REST calls returned `401 Unauthorized`, and no `RENDER_API_KEY` was available.
- Available liveness gate: `https://fx-ai-trader.onrender.com/healthz` returned `200` at `2026-05-26T09:42:24Z` before execution.
- Temporary route deploy was callable at `2026-05-26T09:53:54Z`. Cleanup deploy removed it; `GET /api/internal/pyr-backfill-dry-run-20260526` returned `404` at `2026-05-26T09:58:43Z`.

## Execution path

- Chosen path: temporary internal Flask route, because this worker had no SSH client/key and no Render API credential for shell/cron creation.
- Route gate: `X-PYR-Backfill-Token-SHA256`, matched against hashes of existing environment secrets; no secret value was committed or printed.
- Temporary route commits were pushed and then reverted. Current `main` cleanup head observed locally: `484ee265`.
- Important error: the first route implementation invoked the script via subprocess. Even with `--dry-run`, `DemoDB(...)` initialization emitted migration/backfill side-effect messages before JSON (`[SHADOW_MIGRATION] Fixed 406 FORCE_DEMOTED trades`, `[SHADOW_DRIFT_BACKFILL] Fixed 406 OANDA-filled trades`) and polluted stdout. The successful capture below used the already-initialized production `_demo_db` with `apply=False` to avoid another initialization.

## Dry-run summary

- `would_update_count`: `316`
- `updated_count`: `0`
- `scanned_missing`: `760`
- `distinct_strategies`: `36`
- `total_realized_pl_reattributed`: `-8286.3381`

| strategy | old N | new N | old EV | new EV | delta PnL |
|---|---:|---:|---:|---:|---:|
| `vix_carry_unwind` | 0 | 16 | 0.000000 | 21.812500 | 349.000000 |
| `trendline_sweep` | 0 | 13 | 0.000000 | -95.508838 | -1241.614900 |
| `doji_breakout` | 0 | 4 | 0.000000 | 168.404475 | 673.617900 |
| `gbp_deep_pullback` | 0 | 4 | 0.000000 | -108.484625 | -433.938500 |
| `session_time_bias` | 0 | 7 | 0.000000 | -111.337114 | -779.359800 |

## Cohort safety

- Requested audit cohort: `2026-04-19 -> 2026-05-19`.
- Dry-run tool scope: all-time, not date-filtered. Update open-time range from public trade mapping: `2026-04-07T13:03:07.485068181Z` -> `2026-05-26T01:58:15.227243571Z`.
- Updates inside requested cohort: `83` rows, `-3022.6292` JPY. This does not match the earlier pre-fix checkpoint of 15 rows, so apply must not be queued automatically without commander review.

## Verdict

- `ERROR`
- Reason: the official script subprocess path produced non-JSON stdout and emitted migration/backfill side-effect messages despite `--dry-run`; additionally, exact Render deploy status could not be verified through the required Render API from this worker.
- No `--apply` was run. Successful captured payload reports `apply=false` and `updated_count=0`.

## Discord

- Discord summary notification posted successfully via webhook retry: HTTP `204`.

## Proposed next task

Queue a P0 commander review task before any apply:

```bash
# Do not run until reviewed
DEMO_DB_PATH=/var/data/demo_trades.db python3 tools/backfill_oanda_strategy_2026_05_19.py --apply --db /var/data/demo_trades.db
```

Review requirements: fix or account for `DemoDB` initialization side effects in the dry-run path; decide whether apply scope should be all-time (`316` rows) or restricted to the audit cohort (`83` mapped rows). Do not close `.ai/tasks/queue/20260519-1832-fix-pyr-strategy-attribution-and-dedup.md` because this is not a no-op.

## Full JSON output

```json
{
  "db": "/var/data/demo_trades.db",
  "mode": "dry-run",
  "strategy_old_vs_new": [
    {
      "delta_n": 16,
      "delta_pnl": 349.0,
      "new_ev": 21.8125,
      "new_n": 16,
      "old_ev": 0.0,
      "old_n": 0,
      "strategy": "vix_carry_unwind"
    },
    {
      "delta_n": 13,
      "delta_pnl": -1241.6149,
      "new_ev": -95.508838,
      "new_n": 13,
      "old_ev": 0.0,
      "old_n": 0,
      "strategy": "trendline_sweep"
    },
    {
      "delta_n": 4,
      "delta_pnl": 673.6179,
      "new_ev": 168.404475,
      "new_n": 4,
      "old_ev": 0.0,
      "old_n": 0,
      "strategy": "doji_breakout"
    },
    {
      "delta_n": 4,
      "delta_pnl": -433.9385,
      "new_ev": -108.484625,
      "new_n": 4,
      "old_ev": 0.0,
      "old_n": 0,
      "strategy": "gbp_deep_pullback"
    },
    {
      "delta_n": 7,
      "delta_pnl": -779.3598,
      "new_ev": -111.337114,
      "new_n": 7,
      "old_ev": 0.0,
      "old_n": 0,
      "strategy": "session_time_bias"
    }
  ],
  "summary": {
    "apply": false,
    "by_strategy": {
      "bb_rsi_reversion": {
        "count": 54,
        "realized_pl": -1075.2022
      },
      "bb_squeeze_breakout": {
        "count": 9,
        "realized_pl": 28.378
      },
      "doji_breakout": {
        "count": 4,
        "realized_pl": 673.6179
      },
      "donchian_momentum_breakout": {
        "count": 1,
        "realized_pl": 272.3941
      },
      "dt_bb_rsi_mr": {
        "count": 10,
        "realized_pl": 20.196
      },
      "dt_sr_channel_reversal": {
        "count": 7,
        "realized_pl": -408.0891
      },
      "ema200_trend_reversal": {
        "count": 1,
        "realized_pl": -225.0
      },
      "ema_pullback": {
        "count": 1,
        "realized_pl": 288.0
      },
      "ema_trend_scalp": {
        "count": 5,
        "realized_pl": -207.109
      },
      "engulfing_bb": {
        "count": 6,
        "realized_pl": -209.945
      },
      "fib_reversal": {
        "count": 28,
        "realized_pl": -64.7106
      },
      "gbp_deep_pullback": {
        "count": 4,
        "realized_pl": -433.9385
      },
      "htf_false_breakout": {
        "count": 1,
        "realized_pl": 41.4831
      },
      "macdh_reversal": {
        "count": 2,
        "realized_pl": 19.0
      },
      "mtf_reversal_confluence": {
        "count": 2,
        "realized_pl": -6.0377
      },
      "ny_close_reversal": {
        "count": 1,
        "realized_pl": 8.0
      },
      "orb_trap": {
        "count": 4,
        "realized_pl": -905.8729
      },
      "post_news_vol": {
        "count": 2,
        "realized_pl": 238.8245
      },
      "session_time_bias": {
        "count": 7,
        "realized_pl": -779.3598
      },
      "squeeze_release_momentum": {
        "count": 1,
        "realized_pl": -89.6137
      },
      "sr_break_retest": {
        "count": 1,
        "realized_pl": -202.0
      },
      "sr_channel_reversal": {
        "count": 17,
        "realized_pl": -1214.8235
      },
      "sr_fib_confluence": {
        "count": 3,
        "realized_pl": 1174.0024
      },
      "stoch_trend_pullback": {
        "count": 21,
        "realized_pl": -584.5084
      },
      "streak_reversal": {
        "count": 5,
        "realized_pl": -699.0
      },
      "three_bar_reversal": {
        "count": 2,
        "realized_pl": -33.0
      },
      "trend_rebound": {
        "count": 13,
        "realized_pl": -221.8066
      },
      "trendline_sweep": {
        "count": 13,
        "realized_pl": -1241.6149
      },
      "v_reversal": {
        "count": 4,
        "realized_pl": -384.0
      },
      "vix_carry_unwind": {
        "count": 16,
        "realized_pl": 349.0
      },
      "vol_momentum_scalp": {
        "count": 19,
        "realized_pl": -383.7721
      },
      "vol_surge_detector": {
        "count": 32,
        "realized_pl": 280.7111
      },
      "vsg_jpy_reversal": {
        "count": 2,
        "realized_pl": 108.0
      },
      "vwap_mean_reversion": {
        "count": 10,
        "realized_pl": -2100.8446
      },
      "wick_imbalance_reversion": {
        "count": 1,
        "realized_pl": -456.0313
      },
      "xs_momentum": {
        "count": 7,
        "realized_pl": 138.3347
      }
    },
    "distinct_strategies": 36,
    "scanned_missing": 760,
    "total_realized_pl_reattributed": -8286.3381,
    "updated_count": 0,
    "updates": [
      {
        "oanda_trade_id": "87908",
        "realized_pl": -30.0,
        "strategy": "macdh_reversal"
      },
      {
        "oanda_trade_id": "87915",
        "realized_pl": -31.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "87925",
        "realized_pl": 12.7595,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "88123",
        "realized_pl": 12.7678,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "88847",
        "realized_pl": -48.0744,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "88853",
        "realized_pl": 49.0,
        "strategy": "macdh_reversal"
      },
      {
        "oanda_trade_id": "88951",
        "realized_pl": -150.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "88957",
        "realized_pl": 272.3941,
        "strategy": "donchian_momentum_breakout"
      },
      {
        "oanda_trade_id": "88961",
        "realized_pl": -48.0377,
        "strategy": "mtf_reversal_confluence"
      },
      {
        "oanda_trade_id": "88972",
        "realized_pl": 41.4831,
        "strategy": "htf_false_breakout"
      },
      {
        "oanda_trade_id": "88980",
        "realized_pl": -48.0464,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "88987",
        "realized_pl": -150.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150360",
        "realized_pl": 52.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "150461",
        "realized_pl": 64.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150491",
        "realized_pl": -220.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150498",
        "realized_pl": -150.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150504",
        "realized_pl": -150.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150511",
        "realized_pl": 230.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150573",
        "realized_pl": 170.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150663",
        "realized_pl": 160.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150669",
        "realized_pl": -150.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150676",
        "realized_pl": 175.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150744",
        "realized_pl": -155.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "150750",
        "realized_pl": -150.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150763",
        "realized_pl": 8.0,
        "strategy": "bb_squeeze_breakout"
      },
      {
        "oanda_trade_id": "150849",
        "realized_pl": -85.6308,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "150855",
        "realized_pl": 104.2427,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "150859",
        "realized_pl": 126.3484,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "150971",
        "realized_pl": 145.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "150979",
        "realized_pl": -92.0505,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "150985",
        "realized_pl": 42.6765,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "150997",
        "realized_pl": -90.4286,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "151001",
        "realized_pl": 480.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "151027",
        "realized_pl": -47.603,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "151055",
        "realized_pl": 12.6451,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "154119",
        "realized_pl": -65.0792,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "154126",
        "realized_pl": -202.0,
        "strategy": "sr_break_retest"
      },
      {
        "oanda_trade_id": "154133",
        "realized_pl": 5.0,
        "strategy": "dt_sr_channel_reversal"
      },
      {
        "oanda_trade_id": "154149",
        "realized_pl": -57.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "154155",
        "realized_pl": -90.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "154165",
        "realized_pl": 78.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "154195",
        "realized_pl": -2.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "154199",
        "realized_pl": -47.7918,
        "strategy": "engulfing_bb"
      },
      {
        "oanda_trade_id": "154209",
        "realized_pl": -13.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "154217",
        "realized_pl": -30.0,
        "strategy": "engulfing_bb"
      },
      {
        "oanda_trade_id": "154223",
        "realized_pl": -39.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "154231",
        "realized_pl": 21.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "154235",
        "realized_pl": -47.8158,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "154358",
        "realized_pl": -47.805,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "154428",
        "realized_pl": -30.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "154436",
        "realized_pl": -47.7966,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "154440",
        "realized_pl": 42.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "154446",
        "realized_pl": 42.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "154482",
        "realized_pl": -60.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "154492",
        "realized_pl": -47.7861,
        "strategy": "engulfing_bb"
      },
      {
        "oanda_trade_id": "154571",
        "realized_pl": -80.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "154579",
        "realized_pl": 42.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "154585",
        "realized_pl": -49.3671,
        "strategy": "engulfing_bb"
      },
      {
        "oanda_trade_id": "154589",
        "realized_pl": 42.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "154603",
        "realized_pl": -90.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "154671",
        "realized_pl": -108.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "154677",
        "realized_pl": -1.592,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "154681",
        "realized_pl": -108.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "154688",
        "realized_pl": 126.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "154886",
        "realized_pl": 126.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "154948",
        "realized_pl": 120.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "155228",
        "realized_pl": -47.8766,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "155234",
        "realized_pl": 129.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "155238",
        "realized_pl": 126.0,
        "strategy": "dt_bb_rsi_mr"
      },
      {
        "oanda_trade_id": "155281",
        "realized_pl": -93.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "155287",
        "realized_pl": 44.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "155321",
        "realized_pl": 290.1945,
        "strategy": "orb_trap"
      },
      {
        "oanda_trade_id": "155872",
        "realized_pl": -398.6808,
        "strategy": "orb_trap"
      },
      {
        "oanda_trade_id": "155878",
        "realized_pl": -398.6908,
        "strategy": "orb_trap"
      },
      {
        "oanda_trade_id": "155882",
        "realized_pl": -398.6958,
        "strategy": "orb_trap"
      },
      {
        "oanda_trade_id": "159829",
        "realized_pl": 8.0,
        "strategy": "engulfing_bb"
      },
      {
        "oanda_trade_id": "159833",
        "realized_pl": 163.0,
        "strategy": "dt_sr_channel_reversal"
      },
      {
        "oanda_trade_id": "159837",
        "realized_pl": -157.8121,
        "strategy": "dt_bb_rsi_mr"
      },
      {
        "oanda_trade_id": "160044",
        "realized_pl": 15.8675,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "160458",
        "realized_pl": 7.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "160956",
        "realized_pl": 62.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "161068",
        "realized_pl": 9.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "161948",
        "realized_pl": -102.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "162652",
        "realized_pl": 27.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "162880",
        "realized_pl": -147.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "163694",
        "realized_pl": 5.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "163810",
        "realized_pl": -34.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "166019",
        "realized_pl": -124.168,
        "strategy": "dt_bb_rsi_mr"
      },
      {
        "oanda_trade_id": "168037",
        "realized_pl": 99.8169,
        "strategy": "bb_squeeze_breakout"
      },
      {
        "oanda_trade_id": "171025",
        "realized_pl": -90.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "171029",
        "realized_pl": -90.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "171033",
        "realized_pl": -176.496,
        "strategy": "dt_bb_rsi_mr"
      },
      {
        "oanda_trade_id": "171040",
        "realized_pl": 71.2865,
        "strategy": "bb_squeeze_breakout"
      },
      {
        "oanda_trade_id": "171046",
        "realized_pl": -90.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "171091",
        "realized_pl": 24.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "171111",
        "realized_pl": -43.0,
        "strategy": "engulfing_bb"
      },
      {
        "oanda_trade_id": "171325",
        "realized_pl": -47.7254,
        "strategy": "bb_squeeze_breakout"
      },
      {
        "oanda_trade_id": "171660",
        "realized_pl": -90.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "171667",
        "realized_pl": 68.0977,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "171822",
        "realized_pl": 19.0131,
        "strategy": "dt_bb_rsi_mr"
      },
      {
        "oanda_trade_id": "171826",
        "realized_pl": -87.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "171832",
        "realized_pl": 75.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "171838",
        "realized_pl": -93.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "171851",
        "realized_pl": 293.4158,
        "strategy": "dt_bb_rsi_mr"
      },
      {
        "oanda_trade_id": "171855",
        "realized_pl": -30.0,
        "strategy": "bb_squeeze_breakout"
      },
      {
        "oanda_trade_id": "171861",
        "realized_pl": 78.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "171871",
        "realized_pl": -90.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "171879",
        "realized_pl": 44.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "172721",
        "realized_pl": 140.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "179935",
        "realized_pl": -105.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "181072",
        "realized_pl": -32.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "181079",
        "realized_pl": 144.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "181311",
        "realized_pl": 126.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "181875",
        "realized_pl": 0.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "181879",
        "realized_pl": 177.0,
        "strategy": "post_news_vol"
      },
      {
        "oanda_trade_id": "181887",
        "realized_pl": -31.0,
        "strategy": "bb_squeeze_breakout"
      },
      {
        "oanda_trade_id": "181894",
        "realized_pl": -105.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "181900",
        "realized_pl": -6.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "181928",
        "realized_pl": 42.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "181994",
        "realized_pl": 42.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "191798",
        "realized_pl": -6.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "213136",
        "realized_pl": -93.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "219009",
        "realized_pl": -62.0,
        "strategy": "dt_bb_rsi_mr"
      },
      {
        "oanda_trade_id": "219013",
        "realized_pl": 57.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "219027",
        "realized_pl": 41.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "219087",
        "realized_pl": -30.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "219094",
        "realized_pl": -32.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "219100",
        "realized_pl": 69.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "219107",
        "realized_pl": 78.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "219127",
        "realized_pl": 10.0,
        "strategy": "dt_bb_rsi_mr"
      },
      {
        "oanda_trade_id": "219131",
        "realized_pl": 84.2432,
        "strategy": "dt_bb_rsi_mr"
      },
      {
        "oanda_trade_id": "219137",
        "realized_pl": -90.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "220027",
        "realized_pl": 66.7588,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "220031",
        "realized_pl": 8.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "223135",
        "realized_pl": -31.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "223143",
        "realized_pl": -30.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "223149",
        "realized_pl": -47.8609,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "223156",
        "realized_pl": -11.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "223164",
        "realized_pl": -87.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "223170",
        "realized_pl": 8.0,
        "strategy": "dt_bb_rsi_mr"
      },
      {
        "oanda_trade_id": "226334",
        "realized_pl": -33.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "226340",
        "realized_pl": -34.0,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "226347",
        "realized_pl": 6.0,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "226357",
        "realized_pl": 8.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "226375",
        "realized_pl": -33.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "226382",
        "realized_pl": 24.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "226462",
        "realized_pl": -175.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "226468",
        "realized_pl": 8.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "226818",
        "realized_pl": 0.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "226834",
        "realized_pl": -11.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "226842",
        "realized_pl": -30.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "226848",
        "realized_pl": 42.0,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "227082",
        "realized_pl": -1.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "227090",
        "realized_pl": -30.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "227096",
        "realized_pl": -4.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "227104",
        "realized_pl": 38.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "227132",
        "realized_pl": 44.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "227228",
        "realized_pl": -30.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "227500",
        "realized_pl": -120.0,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "227507",
        "realized_pl": -89.6137,
        "strategy": "squeeze_release_momentum"
      },
      {
        "oanda_trade_id": "227511",
        "realized_pl": -30.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "227521",
        "realized_pl": -31.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "227525",
        "realized_pl": -47.989,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "227529",
        "realized_pl": -911.9564,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "227535",
        "realized_pl": -8.0015,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "227542",
        "realized_pl": 580.0836,
        "strategy": "ema_trend_scalp"
      },
      {
        "oanda_trade_id": "227550",
        "realized_pl": -33.0,
        "strategy": "sr_channel_reversal"
      },
      {
        "oanda_trade_id": "227563",
        "realized_pl": 42.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "227567",
        "realized_pl": -49.593,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "227574",
        "realized_pl": -47.9908,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "227581",
        "realized_pl": -335.8261,
        "strategy": "ema_trend_scalp"
      },
      {
        "oanda_trade_id": "228572",
        "realized_pl": -30.0,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "229542",
        "realized_pl": 44.0,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "230040",
        "realized_pl": -187.1055,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "231611",
        "realized_pl": -47.992,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "231615",
        "realized_pl": -479.8839,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "231619",
        "realized_pl": -33.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "231630",
        "realized_pl": -143.9579,
        "strategy": "ema_trend_scalp"
      },
      {
        "oanda_trade_id": "231640",
        "realized_pl": -48.0025,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "231647",
        "realized_pl": 1.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "231817",
        "realized_pl": -2.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "231864",
        "realized_pl": -30.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "231872",
        "realized_pl": -47.998,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "231882",
        "realized_pl": 12.7515,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "231886",
        "realized_pl": -30.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "232293",
        "realized_pl": 124.0,
        "strategy": "doji_breakout"
      },
      {
        "oanda_trade_id": "232297",
        "realized_pl": 66.9826,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "232301",
        "realized_pl": 42.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "235024",
        "realized_pl": -249.8272,
        "strategy": "session_time_bias"
      },
      {
        "oanda_trade_id": "235030",
        "realized_pl": -244.9738,
        "strategy": "session_time_bias"
      },
      {
        "oanda_trade_id": "235037",
        "realized_pl": -144.104,
        "strategy": "ema_trend_scalp"
      },
      {
        "oanda_trade_id": "235050",
        "realized_pl": -163.3046,
        "strategy": "ema_trend_scalp"
      },
      {
        "oanda_trade_id": "235056",
        "realized_pl": -30.0,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "235066",
        "realized_pl": -96.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "244672",
        "realized_pl": 59.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "244676",
        "realized_pl": 52.5653,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "244692",
        "realized_pl": 8.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "244862",
        "realized_pl": -32.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "244903",
        "realized_pl": -30.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "246011",
        "realized_pl": 425.1039,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "247727",
        "realized_pl": 42.0,
        "strategy": "mtf_reversal_confluence"
      },
      {
        "oanda_trade_id": "247825",
        "realized_pl": -33.0,
        "strategy": "v_reversal"
      },
      {
        "oanda_trade_id": "247831",
        "realized_pl": 8.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "247851",
        "realized_pl": -30.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "247857",
        "realized_pl": -110.2488,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "247874",
        "realized_pl": -31.0,
        "strategy": "v_reversal"
      },
      {
        "oanda_trade_id": "247883",
        "realized_pl": -99.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "247906",
        "realized_pl": -142.0891,
        "strategy": "dt_sr_channel_reversal"
      },
      {
        "oanda_trade_id": "247910",
        "realized_pl": -2.0,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "247914",
        "realized_pl": -3.0,
        "strategy": "three_bar_reversal"
      },
      {
        "oanda_trade_id": "247929",
        "realized_pl": 8.0,
        "strategy": "dt_sr_channel_reversal"
      },
      {
        "oanda_trade_id": "247933",
        "realized_pl": -35.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "248986",
        "realized_pl": -76.0,
        "strategy": "dt_sr_channel_reversal"
      },
      {
        "oanda_trade_id": "248993",
        "realized_pl": -47.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "248999",
        "realized_pl": 33.0,
        "strategy": "vol_surge_detector"
      },
      {
        "oanda_trade_id": "249008",
        "realized_pl": -30.0,
        "strategy": "three_bar_reversal"
      },
      {
        "oanda_trade_id": "249022",
        "realized_pl": -32.0,
        "strategy": "trend_rebound"
      },
      {
        "oanda_trade_id": "249029",
        "realized_pl": -290.0,
        "strategy": "v_reversal"
      },
      {
        "oanda_trade_id": "249036",
        "realized_pl": -30.0,
        "strategy": "v_reversal"
      },
      {
        "oanda_trade_id": "249049",
        "realized_pl": -78.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "249278",
        "realized_pl": 288.0,
        "strategy": "ema_pullback"
      },
      {
        "oanda_trade_id": "253108",
        "realized_pl": -4.7721,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "253112",
        "realized_pl": -210.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "253116",
        "realized_pl": -96.0,
        "strategy": "vol_momentum_scalp"
      },
      {
        "oanda_trade_id": "257995",
        "realized_pl": -105.0,
        "strategy": "bb_squeeze_breakout"
      },
      {
        "oanda_trade_id": "258001",
        "realized_pl": -93.0,
        "strategy": "bb_squeeze_breakout"
      },
      {
        "oanda_trade_id": "259190",
        "realized_pl": -681.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "269772",
        "realized_pl": 1326.0,
        "strategy": "vwap_mean_reversion"
      },
      {
        "oanda_trade_id": "269776",
        "realized_pl": -305.7905,
        "strategy": "vwap_mean_reversion"
      },
      {
        "oanda_trade_id": "346805",
        "realized_pl": 61.8245,
        "strategy": "post_news_vol"
      },
      {
        "oanda_trade_id": "348323",
        "realized_pl": 45.0,
        "strategy": "vwap_mean_reversion"
      },
      {
        "oanda_trade_id": "350735",
        "realized_pl": 78.0,
        "strategy": "vwap_mean_reversion"
      },
      {
        "oanda_trade_id": "350899",
        "realized_pl": 156.0,
        "strategy": "bb_squeeze_breakout"
      },
      {
        "oanda_trade_id": "350905",
        "realized_pl": -1076.9994,
        "strategy": "vwap_mean_reversion"
      },
      {
        "oanda_trade_id": "350909",
        "realized_pl": -678.0,
        "strategy": "vwap_mean_reversion"
      },
      {
        "oanda_trade_id": "350919",
        "realized_pl": -650.6388,
        "strategy": "vwap_mean_reversion"
      },
      {
        "oanda_trade_id": "350927",
        "realized_pl": 228.0,
        "strategy": "doji_breakout"
      },
      {
        "oanda_trade_id": "378299",
        "realized_pl": 52.5841,
        "strategy": "vwap_mean_reversion"
      },
      {
        "oanda_trade_id": "378381",
        "realized_pl": -70.3865,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "378389",
        "realized_pl": -35.1906,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "378397",
        "realized_pl": 31.8681,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "378407",
        "realized_pl": -1119.7921,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "378418",
        "realized_pl": 129.1161,
        "strategy": "gbp_deep_pullback"
      },
      {
        "oanda_trade_id": "378428",
        "realized_pl": -223.9781,
        "strategy": "gbp_deep_pullback"
      },
      {
        "oanda_trade_id": "378514",
        "realized_pl": -621.0,
        "strategy": "vwap_mean_reversion"
      },
      {
        "oanda_trade_id": "378521",
        "realized_pl": -270.0,
        "strategy": "vwap_mean_reversion"
      },
      {
        "oanda_trade_id": "378528",
        "realized_pl": -107.0492,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "378534",
        "realized_pl": -78.3624,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "378541",
        "realized_pl": -4.7906,
        "strategy": "bb_rsi_reversion"
      },
      {
        "oanda_trade_id": "378557",
        "realized_pl": 303.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "379705",
        "realized_pl": -63.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "379712",
        "realized_pl": 11.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "379720",
        "realized_pl": 23.883,
        "strategy": "session_time_bias"
      },
      {
        "oanda_trade_id": "380025",
        "realized_pl": -1.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "380033",
        "realized_pl": -17.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "380041",
        "realized_pl": -2.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "380049",
        "realized_pl": 40.0,
        "strategy": "stoch_trend_pullback"
      },
      {
        "oanda_trade_id": "380115",
        "realized_pl": -144.1112,
        "strategy": "session_time_bias"
      },
      {
        "oanda_trade_id": "380159",
        "realized_pl": 64.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "380455",
        "realized_pl": -85.2882,
        "strategy": "session_time_bias"
      },
      {
        "oanda_trade_id": "380461",
        "realized_pl": -94.9908,
        "strategy": "session_time_bias"
      },
      {
        "oanda_trade_id": "380467",
        "realized_pl": -600.0,
        "strategy": "streak_reversal"
      },
      {
        "oanda_trade_id": "380471",
        "realized_pl": 15.9484,
        "strategy": "session_time_bias"
      },
      {
        "oanda_trade_id": "380532",
        "realized_pl": 12.5617,
        "strategy": "gbp_deep_pullback"
      },
      {
        "oanda_trade_id": "380599",
        "realized_pl": 1037.4982,
        "strategy": "xs_momentum"
      },
      {
        "oanda_trade_id": "380987",
        "realized_pl": 34.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "381023",
        "realized_pl": -33.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "381027",
        "realized_pl": 55.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "381967",
        "realized_pl": -32.0,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "381974",
        "realized_pl": 597.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "381992",
        "realized_pl": -710.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "382052",
        "realized_pl": -612.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "382056",
        "realized_pl": -351.6382,
        "strategy": "gbp_deep_pullback"
      },
      {
        "oanda_trade_id": "382062",
        "realized_pl": -194.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "382068",
        "realized_pl": -3.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "382072",
        "realized_pl": 1090.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "382082",
        "realized_pl": -570.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "382563",
        "realized_pl": 109.3253,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "382569",
        "realized_pl": 18.0,
        "strategy": "streak_reversal"
      },
      {
        "oanda_trade_id": "382579",
        "realized_pl": 6.0,
        "strategy": "streak_reversal"
      },
      {
        "oanda_trade_id": "382639",
        "realized_pl": -201.4312,
        "strategy": "sr_fib_confluence"
      },
      {
        "oanda_trade_id": "382647",
        "realized_pl": 7.8369,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "382801",
        "realized_pl": -147.0,
        "strategy": "streak_reversal"
      },
      {
        "oanda_trade_id": "382915",
        "realized_pl": -101.8568,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "382922",
        "realized_pl": 20.2771,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "383024",
        "realized_pl": 27.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "383031",
        "realized_pl": 21.8185,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "383039",
        "realized_pl": 21.8139,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "383597",
        "realized_pl": 17.1529,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "383721",
        "realized_pl": -456.0313,
        "strategy": "wick_imbalance_reversion"
      },
      {
        "oanda_trade_id": "383728",
        "realized_pl": 240.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "383744",
        "realized_pl": 350.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "384010",
        "realized_pl": -400.2411,
        "strategy": "xs_momentum"
      },
      {
        "oanda_trade_id": "384014",
        "realized_pl": 18.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "384031",
        "realized_pl": 270.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "384723",
        "realized_pl": 60.902,
        "strategy": "xs_momentum"
      },
      {
        "oanda_trade_id": "386613",
        "realized_pl": -447.1112,
        "strategy": "xs_momentum"
      },
      {
        "oanda_trade_id": "388499",
        "realized_pl": -216.6094,
        "strategy": "fib_reversal"
      },
      {
        "oanda_trade_id": "388506",
        "realized_pl": -273.0,
        "strategy": "dt_sr_channel_reversal"
      },
      {
        "oanda_trade_id": "388513",
        "realized_pl": 24.0,
        "strategy": "streak_reversal"
      },
      {
        "oanda_trade_id": "392869",
        "realized_pl": 8.0,
        "strategy": "ny_close_reversal"
      },
      {
        "oanda_trade_id": "392882",
        "realized_pl": 66.1577,
        "strategy": "sr_fib_confluence"
      },
      {
        "oanda_trade_id": "392976",
        "realized_pl": 1309.2759,
        "strategy": "sr_fib_confluence"
      },
      {
        "oanda_trade_id": "398898",
        "realized_pl": -673.581,
        "strategy": "xs_momentum"
      },
      {
        "oanda_trade_id": "398905",
        "realized_pl": -93.0,
        "strategy": "dt_sr_channel_reversal"
      },
      {
        "oanda_trade_id": "398913",
        "realized_pl": 57.0,
        "strategy": "vsg_jpy_reversal"
      },
      {
        "oanda_trade_id": "403721",
        "realized_pl": 632.4563,
        "strategy": "xs_momentum"
      },
      {
        "oanda_trade_id": "403889",
        "realized_pl": 66.6179,
        "strategy": "doji_breakout"
      },
      {
        "oanda_trade_id": "412715",
        "realized_pl": -23.9021,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "412719",
        "realized_pl": 22.223,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "412915",
        "realized_pl": 255.0,
        "strategy": "doji_breakout"
      },
      {
        "oanda_trade_id": "413221",
        "realized_pl": 51.0,
        "strategy": "vsg_jpy_reversal"
      },
      {
        "oanda_trade_id": "413231",
        "realized_pl": 302.0,
        "strategy": "vix_carry_unwind"
      },
      {
        "oanda_trade_id": "413331",
        "realized_pl": -71.5885,
        "strategy": "xs_momentum"
      },
      {
        "oanda_trade_id": "413339",
        "realized_pl": -33.4772,
        "strategy": "trendline_sweep"
      },
      {
        "oanda_trade_id": "413347",
        "realized_pl": -225.0,
        "strategy": "ema200_trend_reversal"
      }
    ],
    "window_minutes": 5,
    "would_update_count": 316
  }
}
```
