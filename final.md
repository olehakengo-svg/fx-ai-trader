# live_tier_exempt path audit - 2026-06-12

## Verdict

Bug.

`mtf_gate_action='live_tier_exempt'` is an intentional MTF A/B gate exemption for eligible LIVE tiers, but the implementation did not explicitly exclude demoted tiers from that exemption path. A PAIR_DEMOTED strategy-pair could therefore retain the `live_tier_exempt` label and, if a later live path re-promoted it, reach OANDA without a PAIR_DEMOTED depth-in-defense gate.

## Code Derivation

1. `modules/demo_trader.py::_tick_entry` computes `_is_live_tier_exempt` before the MTF gate.
   - Before this patch it was only:
     - `self._is_elite_live(entry_type, instrument)`
     - or `(entry_type, instrument) in self._PAIR_PROMOTED`
   - There was no explicit `PAIR_DEMOTED` / `FORCE_DEMOTED` exclusion in that variable.

2. The only assignment of `mtf_gate_action='live_tier_exempt'` is the MTF A/B gate branch:
   - `elif _gate_group == "mtf_gated" and _is_live_tier_exempt:`
   - `_mtf_gate_action = "live_tier_exempt"`

3. `_resolve_tier()` already used PAIR_DEMOTED before PAIR_PROMOTED, but `_is_live_tier_exempt` did not share that tier precedence. That made the MTF exempt label inconsistent with the tier resolver.

4. The OANDA-send depth-in-defense gate was FORCE_DEMOTED-only:
   - `_apply_force_demoted_final_gate(...)`
   - `_resend_pending_oanda_trades(...)`
   PAIR_DEMOTED was not covered there.

## Fix

- Added `_is_pair_demoted_entry(entry_type, instrument)` and reused it in:
  - `_is_live_tier_exempt` demoted exclusion
  - `_resolve_tier`
  - `_is_promoted`
  - final OANDA-send guard
  - pending OANDA resend guard
- Expanded the final send guard so PAIR_DEMOTED is forced to shadow with `[PAIR_DEMOTED_GATE]`.
- Added `entry_type` to `DemoDB.get_open_trades_without_oanda()` so resend can evaluate pair demotion correctly.
- Kept Shadow emission intact. The change only blocks demoted tiers from LIVE transfer / resend.

## force_demoted_live_leak Blind Spot

`force_demoted_live_leak=0` for `xs_momentum` is expected under the old detector because that detector only checks `entry_type IN FORCE_DEMOTED`. `xs_momentum×GBP_USD` is PAIR_DEMOTED, not FORCE_DEMOTED.

I updated `scripts/check_force_demoted_leak_safety.py` to also report `q5_pair_demoted_live` and mark the verdict `UNSAFE` when any PAIR_DEMOTED live rows exist.

## Render 90d Measurement

Source: Render production `/api/demo/trades?limit=100000`, fetched 2026-06-12. Returned 9,798 rows, covering `2026-04-02T08:17:17.329000+00:00` through `2026-06-12T07:46:21.268631+00:00`. Filter: `entry_time >= 2026-03-14T00:00:00`, `mtf_gate_action='live_tier_exempt'`, `is_shadow=0`.

| entry_type | instrument | current tier | n | pnl_pips | avg_pips | first | last | edge_n | edge_ids |
|---|---|---:|---:|---:|---:|---|---|---:|---|
| doji_breakout | GBP_USD | PAIR_PROMOTED | 1 | 1.3 | 1.3 | 2026-05-18T16:01:42.450681+00:00 | 2026-05-18T16:01:42.450681+00:00 | 0 |  |
| doji_breakout | USD_JPY | PAIR_PROMOTED | 1 | 7.8 | 7.8 | 2026-05-20T13:38:28.358678+00:00 | 2026-05-20T13:38:28.358678+00:00 | 0 |  |
| dt_sr_channel_reversal | EUR_JPY | PAIR_PROMOTED | 4 | 2.8 | 0.7 | 2026-05-13T15:39:24.152045+00:00 | 2026-06-09T14:25:35.145334+00:00 | 0 |  |
| ema200_trend_reversal | USD_JPY | PAIR_PROMOTED | 2 | -12.7 | -6.35 | 2026-05-26T01:58:10.544710+00:00 | 2026-06-12T06:34:40.374090+00:00 | 0 |  |
| session_time_bias | EUR_USD | PAIR_PROMOTED | 12 | 3.1 | 0.2583 | 2026-06-01T10:50:59.930458+00:00 | 2026-06-04T10:48:41.387199+00:00 | 12 | E2 |
| session_time_bias | GBP_USD | UNIVERSAL_SENTINEL | 2 | -16.9 | -8.45 | 2026-06-03T08:40:00.120494+00:00 | 2026-06-04T11:31:54.492860+00:00 | 0 |  |
| trendline_sweep | GBP_USD | ELITE_LIVE | 10 | -11.3 | -1.13 | 2026-05-07T06:26:12.817014+00:00 | 2026-06-11T15:52:18.221413+00:00 | 0 |  |
| vix_carry_unwind | USD_JPY | PAIR_PROMOTED | 1 | 30.1 | 30.1 | 2026-05-20T15:08:12.291277+00:00 | 2026-05-20T15:08:12.291277+00:00 | 0 |  |
| vsg_jpy_reversal | EUR_JPY | PAIR_PROMOTED | 2 | 3.4 | 1.7 | 2026-05-14T04:30:02.195465+00:00 | 2026-05-20T14:36:37.095352+00:00 | 0 |  |
| wick_imbalance_reversion | GBP_USD | PAIR_PROMOTED | 2 | -14.5 | -7.25 | 2026-06-01T11:31:35.628154+00:00 | 2026-06-11T07:31:17.777321+00:00 | 2 | E10 |
| xs_momentum | GBP_USD | PAIR_DEMOTED | 5 | -19.6 | -3.92 | 2026-05-08T12:46:31.893747+00:00 | 2026-05-20T15:31:06.915446+00:00 | 0 |  |
| zz_pivot_v60_sr | EUR_USD | PAIR_PROMOTED | 2 | -17.3 | -8.65 | 2026-06-05T08:29:16.347068+00:00 | 2026-06-08T12:03:05.828470+00:00 | 0 |  |

`xs_momentum×GBP_USD` is the invalid non-edge PAIR_DEMOTED live leak under this path.

## Verification

- `git diff` verified changed files:
  - `modules/demo_trader.py`
  - `modules/demo_db.py`
  - `scripts/check_force_demoted_leak_safety.py`
  - `tests/test_force_demoted_leak_backfill.py`
  - `final.md`
- Targeted tests passed:
  - `.venv/bin/pytest tests/test_force_demoted_leak_backfill.py tests/test_shadow_emit_skip_demoted.py tests/test_flag_drift_writepath.py -q`
  - `17 passed`
- Full acceptance checks passed:
  - `.venv/bin/pytest tests/ -x -q`
  - `1845 passed, 1 skipped, 1 xfailed in 282.73s`
  - `.venv/bin/python scripts/check.py`
  - exit 0, `全6チェック通過`
