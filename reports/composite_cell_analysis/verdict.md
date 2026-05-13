# Composite Cell Retrospective Verdict

VERDICT: HOLD_GAP5_COMPOSITE

## Scope

- Source: `reports/regime_gate_phase_b2/trade_log_tagged.csv`
- Trades evaluated: 5617
- Analysis type: retrospective observation only; not a Live promotion decision and not Shadow admission proof.
- Classifier changes: none. Existing `modules.regime_classifier.classify_15m` was used with local MASSIVE 15m cache features.

## Q1: 17 proposals are structurally decomposed?

Yes, but this is still retrospective EDA. The 17 proposals expand into 34 proposal x v2 rows; 20 rows have N>=30 after the composite split.

Top proposal composite rows:

| proposal | entry_type | dow_regime | v2_regime | proposal_N | proposal_WR | proposal_EV_pip | proposal_PF | proposal_Wilson_lo | share_of_proposal_N | N | wins | WR | EV_pip | PF | Wilson_lo | Kelly |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| htf_false_breakout__regime_CHOP | htf_false_breakout | CHOP | moderate_trend | 38 | 0.657895 | 0.321725 | 1.59212 | 0.498918 | 0.052632 | 2 | 2 | 1 | 1.9156 | inf | 0.342372 | 1 |
| trendline_sweep__regime_CHOP | trendline_sweep | CHOP | moderate_trend | 92 | 0.75 | 0.762137 | 2.07079 | 0.65271 | 0.152174 | 14 | 13 | 0.928571 | 1.45081 | 8.61663 | 0.685307 | 0.820806 |
| sr_anti_hunt_bounce__regime_CHOP | sr_anti_hunt_bounce | CHOP | no_go | 49 | 0.816327 | 3.91514 | 4.32026 | 0.686421 | 0.877551 | 43 | 36 | 0.837209 | 4.44116 | 5.61546 | 0.700273 | 0.688119 |
| vix_carry_unwind__regime_TRENDING | vix_carry_unwind | TRENDING | moderate_trend | 51 | 0.686275 | 0.561288 | 1.53597 | 0.549727 | 0.117647 | 6 | 5 | 0.833333 | 1.34343 | 3.45846 | 0.436491 | 0.592379 |
| streak_reversal__regime_TRENDING | streak_reversal | TRENDING | no_go | 105 | 0.752381 | 1.22741 | 3.15991 | 0.661895 | 0.933333 | 98 | 75 | 0.765306 | 1.30753 | 3.53667 | 0.672381 | 0.548914 |
| vix_carry_unwind__regime_CHOP | vix_carry_unwind | CHOP | no_go | 41 | 0.780488 | 0.954238 | 2.20825 | 0.632947 | 0.780488 | 32 | 25 | 0.78125 | 0.971268 | 2.25755 | 0.612447 | 0.43519 |
| streak_reversal__regime_RANGING | streak_reversal | RANGING | no_go | 94 | 0.744681 | 1.00324 | 2.31625 | 0.64814 | 0.851064 | 80 | 60 | 0.75 | 1.02585 | 2.32219 | 0.645151 | 0.427029 |
| post_news_vol__regime_CHOP | post_news_vol | CHOP | no_go | 39 | 0.717949 | 1.14558 | 2.33523 | 0.562244 | 0.769231 | 30 | 22 | 0.733333 | 1.19062 | 2.33335 | 0.555517 | 0.419049 |
| streak_reversal__regime_RANGING | streak_reversal | RANGING | moderate_trend | 94 | 0.744681 | 1.00324 | 2.31625 | 0.64814 | 0.148936 | 14 | 10 | 0.714286 | 0.874029 | 2.27775 | 0.453505 | 0.400694 |
| vix_carry_unwind__regime_CHOP | vix_carry_unwind | CHOP | moderate_trend | 41 | 0.780488 | 0.954238 | 2.20825 | 0.632947 | 0.219512 | 9 | 7 | 0.777778 | 0.893683 | 2.04927 | 0.452583 | 0.398239 |
| streak_reversal__regime_CHOP | streak_reversal | CHOP | no_go | 273 | 0.677656 | 0.795716 | 1.99513 | 0.620079 | 0.897436 | 245 | 172 | 0.702041 | 0.932018 | 2.25185 | 0.642009 | 0.390279 |
| post_news_vol__regime_CHOP | post_news_vol | CHOP | moderate_trend | 39 | 0.717949 | 1.14558 | 2.33523 | 0.562244 | 0.230769 | 9 | 6 | 0.666667 | 0.995458 | 2.3428 | 0.354197 | 0.382107 |

## Q2: Bonferroni passing cells exist?

Effective m = 46; alpha' = 0.00108696. Passing cells = 10.

| entry_type | dow_regime | v2_regime | N | wins | WR | EV_pip | PF | Wilson_lo | Kelly | m_eff | alpha_prime | p_value | bonferroni_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| streak_reversal | CHOP | no_go | 245 | 172 | 0.702041 | 0.932018 | 2.25185 | 0.642009 | 0.390279 | 46 | 0.00108696 | 1.09447e-10 | True |
| session_time_bias | CHOP | no_go | 649 | 400 | 0.616333 | 0.076985 | 1.10548 | 0.57834 | 0.058807 | 46 | 0.00108696 | 1.66975e-09 | True |
| streak_reversal | TRENDING | no_go | 98 | 75 | 0.765306 | 1.30753 | 3.53667 | 0.672381 | 0.548914 | 46 | 0.00108696 | 6.58612e-08 | True |
| xs_momentum | TRENDING | no_go | 312 | 202 | 0.647436 | 0.171357 | 1.27134 | 0.592921 | 0.138179 | 46 | 0.00108696 | 1.06205e-07 | True |
| streak_reversal | RANGING | no_go | 80 | 60 | 0.75 | 1.02585 | 2.32219 | 0.645151 | 0.427029 | 46 | 0.00108696 | 4.29028e-06 | True |
| sr_anti_hunt_bounce | CHOP | no_go | 43 | 36 | 0.837209 | 4.44116 | 5.61546 | 0.700273 | 0.688119 | 46 | 0.00108696 | 4.48152e-06 | True |
| session_time_bias | TRENDING | no_go | 178 | 118 | 0.662921 | 0.254899 | 1.40585 | 0.590685 | 0.191377 | 46 | 0.00108696 | 8.22989e-06 | True |
| trendline_sweep | CHOP | no_go | 78 | 56 | 0.717949 | 0.63853 | 1.7929 | 0.609689 | 0.317509 | 46 | 0.00108696 | 7.47408e-05 | True |
| session_time_bias | RANGING | no_go | 200 | 127 | 0.635 | 0.129028 | 1.18236 | 0.566316 | 0.097939 | 46 | 0.00108696 | 8.20926e-05 | True |
| vix_carry_unwind | CHOP | no_go | 32 | 25 | 0.78125 | 0.971268 | 2.25755 | 0.612447 | 0.43519 | 46 | 0.00108696 | 0.0010512 | True |

## Q3: Prediction power vs single classifiers

Lower is better. The comparison uses leave-one-out empirical win-rate predictions per bucket, with Laplace smoothing.

| model | features | N | brier_score | log_loss |
| --- | --- | --- | --- | --- |
| v2_only | v2_regime | 5617 | 0.240151 | 0.673315 |
| dow_only | dow_regime | 5617 | 0.240328 | 0.673684 |
| composite | dow_regime+v2_regime | 5617 | 0.240401 | 0.673833 |

Composite Brier delta vs dow_only = +0.000073101; vs v2_only = +0.000249826.

## Q4: Recommended next action

Recommendation: D

compositeではedgeが強化されていないため、Gap 5 / Phase Eの再定義は保留する。
