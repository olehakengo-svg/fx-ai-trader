# OANDA Passthrough Gap Audit — 2026-05-03

Source DB: `knowledge-base/raw/snapshots/render-demo-trades-20260503.db`
Effective cutoff (snapshot-derived): `2026-04-27T03:46:04.293796+00:00`

## Aggregate sanity check

- Cleaned legacy Live (`is_shadow=0`): N=67 (target 68, tolerance +/-5)
- Cleaned strict Live (`oanda_trade_id != ''`): N=28 (target 29, tolerance +/-3)
- Gap cohort: N=39 legacy-live rows with blank `oanda_trade_id`
- Legacy decided stats: WR=41.94%, PnL=-57.7pip, mean=-0.93
- Filled decided stats: N=24, WR=54.17%, Wilson 95%=[35.1%, 72.1%], PnL=-28.7pip

## Classification table

| trade_id | entry_time | entry_type | instrument | direction | confidence | regime | pnl_pips | outcome | mode | gate_group | mtf_alignment | mtf_gate_action | classification | evidence |
|---|---|---|---|---|---:|---|---:|---|---|---|---|---|---|---|
| f30b8514-82f | 2026-05-01T00:00:11.655297+00:00 | bb_rsi_reversion | USD_JPY | SELL | 69.0 | range_tight | -9.1 | LOSS | scalp_5m | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=mtf_gated; mtf_gate_action=kept |
| 9af83299-09b | 2026-05-01T13:51:47.309699+00:00 | bb_rsi_reversion | EUR_USD | BUY | 67.0 | trend_up_weak | +7.9 | WIN | scalp_5m_eur | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel+pair_demoted; gate_group=mtf_gated; mtf_gate_action=kept |
| 9c70d68d-b5d | 2026-05-01T16:02:18.686920+00:00 | bb_rsi_reversion | EUR_USD | BUY | 78.0 | trend_up_weak | -7.8 | LOSS | scalp_5m_eur | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel+pair_demoted; gate_group=label_only; mtf_gate_action=none |
| 40603621-eca | 2026-04-27T15:20:01.821845+00:00 | bb_rsi_reversion | USD_JPY | BUY | 56.0 | range_tight | +7.4 | WIN | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| a35e1858-f2b | 2026-05-01T00:58:57.024500+00:00 | bb_rsi_reversion | USD_JPY | BUY | 53.0 | range_tight | +7.1 | WIN | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| f6a636dd-1d6 | 2026-04-30T07:21:20.458380+00:00 | bb_rsi_reversion | USD_JPY | BUY | 71.0 | range_tight | +6.9 | WIN | scalp_5m | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 91939e4a-898 | 2026-04-27T14:00:30.990028+00:00 | bb_rsi_reversion | USD_JPY | SELL | 76.0 | range_tight | +6.5 | WIN | scalp_5m | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 6d03b188-e2f | 2026-05-01T14:52:16.734901+00:00 | bb_rsi_reversion | USD_JPY | SELL | 74.0 | range_tight | -6.1 | LOSS | scalp_5m | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 91cb5987-58d | 2026-04-30T09:02:57.635430+00:00 | bb_rsi_reversion | GBP_USD | BUY | 66.0 | range_wide | -6.0 | LOSS | scalp_5m_gbp | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel+pair_demoted; gate_group=mtf_gated; mtf_gate_action=kept |
| d6bdf81d-ad3 | 2026-04-27T14:51:19.698071+00:00 | bb_rsi_reversion | USD_JPY | BUY | 60.0 | range_tight | +6.0 | WIN | scalp_5m | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 2aea7b17-5b5 | 2026-04-27T07:02:39.618488+00:00 | bb_rsi_reversion | USD_JPY | BUY | 57.0 | range_tight | -5.2 | LOSS | scalp_5m | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| d7917af1-c83 | 2026-04-27T13:46:46.916935+00:00 | bb_rsi_reversion | EUR_USD | BUY | 71.0 | uncertain | -5.0 | LOSS | scalp_5m_eur | label_only | neutral | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel+pair_demoted; gate_group=label_only; mtf_gate_action=none |
| ec08c6e9-f2d | 2026-04-28T05:19:06.443132+00:00 | bb_rsi_reversion | USD_JPY | SELL | 36.0 | range_tight | -4.6 | LOSS | scalp_5m | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 15569815-fef | 2026-04-28T00:01:40.135418+00:00 | bb_rsi_reversion | USD_JPY | BUY | 50.0 | range_tight | -4.4 | LOSS | scalp_5m | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| c1e198b8-ff0 | 2026-04-30T13:26:02.102983+00:00 | bb_rsi_reversion | EUR_USD | BUY | 72.0 | uncertain | +4.3 | WIN | scalp_eur | mtf_gated | neutral | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel+pair_demoted; gate_group=mtf_gated; mtf_gate_action=kept |
| 6f137d8f-be4 | 2026-05-01T03:24:41.134896+00:00 | bb_rsi_reversion | USD_JPY | BUY | 62.0 | range_tight | +4.2 | WIN | scalp | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=mtf_gated; mtf_gate_action=kept |
| a7789c75-394 | 2026-04-27T06:35:08.882882+00:00 | bb_rsi_reversion | USD_JPY | BUY | 63.0 | range_tight | -4.1 | LOSS | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 0f423839-092 | 2026-05-01T05:43:21.197998+00:00 | bb_rsi_reversion | USD_JPY | BUY | 68.0 | range_tight | +3.6 | WIN | scalp | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=mtf_gated; mtf_gate_action=kept |
| 736c564b-3f5 | 2026-04-30T06:35:57.742470+00:00 | bb_rsi_reversion | USD_JPY | BUY | 77.0 | range_tight | +3.6 | WIN | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 9284481a-0d4 | 2026-04-27T13:00:43.152012+00:00 | bb_rsi_reversion | EUR_USD | BUY | 57.0 | uncertain | +3.6 | WIN | scalp_eur | label_only | neutral | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel+pair_demoted; gate_group=label_only; mtf_gate_action=none |
| 59b95a90-dc0 | 2026-04-28T06:34:21.271043+00:00 | bb_rsi_reversion | USD_JPY | BUY | 51.0 | range_tight | -3.4 | LOSS | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| bffbd2bf-9e6 | 2026-04-27T05:23:47.480712+00:00 | bb_rsi_reversion | USD_JPY | SELL | 69.0 | range_tight | -3.4 | LOSS | scalp_5m | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=mtf_gated; mtf_gate_action=kept |
| c18939b7-f57 | 2026-04-29T01:27:33.617028+00:00 | bb_rsi_reversion | USD_JPY | BUY | 66.0 | range_tight | -3.4 | LOSS | scalp | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=mtf_gated; mtf_gate_action=kept |
| 0481e3e1-c29 | 2026-04-29T06:29:38.835395+00:00 | bb_rsi_reversion | USD_JPY | BUY | 73.0 | range_tight | -3.2 | LOSS | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 794b81a8-bc2 | 2026-04-27T06:34:25.668073+00:00 | bb_rsi_reversion | USD_JPY | BUY | 63.0 | range_tight | -3.2 | LOSS | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 87d0eea4-5ea | 2026-05-01T03:19:42.486222+00:00 | bb_rsi_reversion | USD_JPY | BUY | 66.0 | range_tight | -3.2 | LOSS | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 9033e2ff-c2a | 2026-04-28T06:39:13.192451+00:00 | bb_rsi_reversion | USD_JPY | BUY | 66.0 | range_tight | -3.2 | LOSS | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| c459f08a-40e | 2026-04-27T06:32:13.822957+00:00 | bb_rsi_reversion | USD_JPY | BUY | 59.0 | range_tight | -3.2 | LOSS | scalp | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=mtf_gated; mtf_gate_action=kept |
| 727267ea-1c7 | 2026-04-28T05:38:09.620441+00:00 | bb_rsi_reversion | USD_JPY | SELL | 74.0 | range_tight | -3.1 | LOSS | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 8b9f732f-113 | 2026-04-28T05:23:33.039000+00:00 | bb_rsi_reversion | USD_JPY | BUY | 56.0 | range_tight | +3.1 | WIN | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 257e0143-0c2 | 2026-04-29T06:41:33.315937+00:00 | bb_rsi_reversion | USD_JPY | BUY | 73.0 | range_tight | -3.0 | LOSS | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 503fd8c4-dc7 | 2026-04-27T03:45:12.763647+00:00 | bb_rsi_reversion | USD_JPY | BUY | 66.0 | range_tight | -3.0 | LOSS | scalp | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=mtf_gated; mtf_gate_action=kept |
| 86fdab6f-3b9 | 2026-04-27T15:38:14.627277+00:00 | bb_rsi_reversion | USD_JPY | SELL | 68.0 | range_tight | +3.0 | WIN | scalp | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=mtf_gated; mtf_gate_action=kept |
| d7141872-11b | 2026-04-28T05:10:05.052618+00:00 | bb_rsi_reversion | USD_JPY | SELL | 68.0 | range_tight | -3.0 | LOSS | scalp | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=mtf_gated; mtf_gate_action=kept |
| e5eb8079-8e9 | 2026-04-30T06:29:18.589884+00:00 | bb_rsi_reversion | USD_JPY | BUY | 79.0 | range_tight | -3.0 | LOSS | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 726a60f5-7f5 | 2026-04-27T13:59:36.735941+00:00 | bb_rsi_reversion | EUR_USD | BUY | 73.0 | uncertain | -1.0 | LOSS | scalp_5m_eur | label_only | neutral | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel+pair_demoted; gate_group=label_only; mtf_gate_action=none |
| 9c23cc48-0a6 | 2026-05-01T03:01:39.922717+00:00 | bb_rsi_reversion | USD_JPY | BUY | 58.0 | range_tight | -1.0 | LOSS | scalp | label_only | aligned | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=label_only; mtf_gate_action=none |
| 7e06fb3d-18a | 2026-04-28T04:19:31.757800+00:00 | bb_rsi_reversion | USD_JPY | SELL | 67.0 | range_tight | -0.6 | LOSS | scalp | mtf_gated | aligned | kept | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel; gate_group=mtf_gated; mtf_gate_action=kept |
| 7d12d687-c44 | 2026-04-27T10:19:07.305319+00:00 | bb_rsi_reversion | EUR_USD | BUY | 68.0 | uncertain | -0.3 | BREAKEVEN | scalp_5m_eur | label_only | neutral | none | H3_FLAG_DRIFT | is_shadow=0 but oanda_trade_id blank; tier=scalp_sentinel+pair_demoted; gate_group=label_only; mtf_gate_action=none |

## Per-classification summary

| classification | N | mean_pnl | win_rate | total_pnl |
|---|---:|---:|---:|---:|
| H3_FLAG_DRIFT | 39 | -0.75 | 33.3% | -29.3 |

## Edge-suppression test (CRITICAL)

- No H1 classification reached N>=10 in the cleaned snapshot slice, so a Wilson separation claim about gate-suppressed winners is not supported.

## Verdict

- Verdict: `FLAG_DRIFT_BUG`
- Dominant classification: `H3_FLAG_DRIFT` (N=39, total_pnl=-29.3pip)
- Interpretation: the cleaned gap slice is entirely bb_rsi_reversion scalp traffic with blank `oanda_trade_id`, and repo tier metadata marks those cells as SCALP_SENTINEL / PAIR_DEMOTED intentional shadow candidates. That is consistent with `is_shadow` write-path drift rather than a positive-edge OANDA bridge outage.

## Limitations

- The workspace snapshot does not include an `oanda_audit` table, so `bridge_status` and per-send failure codes could not be joined.
- `/api/risk/dashboard` could not be fetched live in this sandbox; the cutoff was selected deterministically from the supplied snapshot to match the documented 68/29/39 target as closely as possible.
- This audit does not prove that no H2 bridge errors ever occurred; it only shows that the reviewed 39-row gap cohort is better explained by shadow/tier drift evidence than by bridge evidence.
