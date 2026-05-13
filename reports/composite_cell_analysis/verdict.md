# Composite Cell Retrospective Verdict

VERDICT: HOLD_GAP5_COMPOSITE

feedback_label_empirical_audit: HOLD_GAP5_COMPOSITE

## Scope

- Source: `reports/regime_gate_phase_b2/trade_log_tagged.csv`
- Trades evaluated: 5617
- Analysis type: retrospective observation only; not a Live promotion decision and not Shadow admission proof.
- Classifier changes: none. Existing `modules.regime_classifier.classify_15m` was used with local MASSIVE 15m cache features.
- Production guard: no production code, classifier threshold, DB, `.env`, OANDA, Render, or GitHub credential changes.

## Q1: 17 proposals are structurally decomposed?

Verdict: STRUCTURED_NO_GO_DOMINANT.

The 17 proposals expand into 34 proposal x v2 rows; 21 rows have N>=30 after the composite split. The actionable structure is mostly concentration inside `no_go`, not confirmation that `moderate_trend` improves the B2.5 proposals.

Top proposal composite rows:

| proposal | entry_type | dow_regime | v2_regime | proposal_N | proposal_WR | proposal_EV_pip | proposal_PF | proposal_Wilson_lo | share_of_proposal_N | N | wins | WR | EV_pip | PF | Wilson_lo | Kelly |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vix_carry_unwind__regime_CHOP | vix_carry_unwind | CHOP | moderate_trend | 41 | 0.780488 | 0.954238 | 2.20825 | 0.632947 | 0.146341 | 6 | 6 | 1 | 2.09037 | inf | 0.609657 | 1 |
| htf_false_breakout__regime_CHOP | htf_false_breakout | CHOP | moderate_trend | 38 | 0.657895 | 0.321725 | 1.59212 | 0.498918 | 0.026316 | 1 | 1 | 1 | 1.0912 | inf | 0.206543 | 1 |
| trendline_sweep__regime_CHOP | trendline_sweep | CHOP | moderate_trend | 92 | 0.75 | 0.762137 | 2.07079 | 0.65271 | 0.152174 | 14 | 13 | 0.928571 | 1.45081 | 8.61663 | 0.685307 | 0.820806 |
| sr_anti_hunt_bounce__regime_CHOP | sr_anti_hunt_bounce | CHOP | no_go | 49 | 0.816327 | 3.91514 | 4.32026 | 0.686421 | 0.877551 | 43 | 36 | 0.837209 | 4.38407 | 5.49858 | 0.700273 | 0.68495 |
| vix_carry_unwind__regime_TRENDING | vix_carry_unwind | TRENDING | moderate_trend | 51 | 0.686275 | 0.561288 | 1.53597 | 0.549727 | 0.117647 | 6 | 5 | 0.833333 | 1.34505 | 3.46142 | 0.436491 | 0.592585 |
| streak_reversal__regime_TRENDING | streak_reversal | TRENDING | no_go | 105 | 0.752381 | 1.22741 | 3.15991 | 0.661895 | 0.92381 | 97 | 73 | 0.752577 | 1.31234 | 3.46509 | 0.658184 | 0.535389 |
| post_news_vol__regime_CHOP | post_news_vol | CHOP | moderate_trend | 39 | 0.717949 | 1.14558 | 2.33523 | 0.562244 | 0.179487 | 7 | 5 | 0.714286 | 1.34077 | 3.84531 | 0.358929 | 0.528531 |
| streak_reversal__regime_RANGING | streak_reversal | RANGING | no_go | 94 | 0.744681 | 1.00324 | 2.31625 | 0.64814 | 0.808511 | 76 | 57 | 0.75 | 1.07412 | 2.4719 | 0.64223 | 0.44659 |
| streak_reversal__regime_CHOP | streak_reversal | CHOP | no_go | 273 | 0.677656 | 0.795716 | 1.99513 | 0.620079 | 0.886447 | 242 | 170 | 0.702479 | 0.96445 | 2.36896 | 0.642079 | 0.405945 |
| post_news_vol__regime_CHOP | post_news_vol | CHOP | no_go | 39 | 0.717949 | 1.14558 | 2.33523 | 0.562244 | 0.820513 | 32 | 23 | 0.71875 | 1.10289 | 2.17009 | 0.546252 | 0.387542 |
| vix_carry_unwind__regime_CHOP | vix_carry_unwind | CHOP | no_go | 41 | 0.780488 | 0.954238 | 2.20825 | 0.632947 | 0.853659 | 35 | 26 | 0.742857 | 0.759473 | 1.82091 | 0.579304 | 0.334898 |
| trendline_sweep__regime_CHOP | trendline_sweep | CHOP | no_go | 92 | 0.75 | 0.762137 | 2.07079 | 0.65271 | 0.847826 | 78 | 56 | 0.717949 | 0.63853 | 1.7929 | 0.609689 | 0.317509 |

## Q2: Bonferroni passing cells exist?

Effective m = 47; alpha' = 0.00106383. Passing cells = 10. Pass requires Bonferroni-adjusted p<=0.05, Wilson_lo>0.5, and EV_pip>0.

| entry_type | dow_regime | v2_regime | N | wins | WR | EV_pip | PF | Wilson_lo | Kelly | m_eff | alpha_prime | p_value | p_bonferroni | bonferroni_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| streak_reversal | CHOP | no_go | 242 | 170 | 0.702479 | 0.96445 | 2.36896 | 0.642079 | 0.405945 | 47 | 0.00106383 | 1.29203e-10 | 6.07254e-09 | True |
| session_time_bias | CHOP | no_go | 645 | 397 | 0.615504 | 0.072149 | 1.09864 | 0.577381 | 0.05526 | 47 | 0.00106383 | 2.41691e-09 | 1.13595e-07 | True |
| xs_momentum | TRENDING | no_go | 315 | 205 | 0.650794 | 0.183492 | 1.29387 | 0.596618 | 0.147813 | 47 | 0.00106383 | 4.76462e-08 | 2.23937e-06 | True |
| streak_reversal | TRENDING | no_go | 97 | 73 | 0.752577 | 1.31234 | 3.46509 | 0.658184 | 0.535389 | 47 | 0.00106383 | 3.20237e-07 | 1.50511e-05 | True |
| session_time_bias | TRENDING | no_go | 176 | 118 | 0.670455 | 0.270797 | 1.44365 | 0.598018 | 0.206039 | 47 | 0.00106383 | 3.58568e-06 | 0.000168527 | True |
| sr_anti_hunt_bounce | CHOP | no_go | 43 | 36 | 0.837209 | 4.38407 | 5.49858 | 0.700273 | 0.68495 | 47 | 0.00106383 | 4.48152e-06 | 0.000210631 | True |
| streak_reversal | RANGING | no_go | 76 | 57 | 0.75 | 1.07412 | 2.4719 | 0.64223 | 0.44659 | 47 | 0.00106383 | 7.41845e-06 | 0.000348667 | True |
| xs_momentum | CHOP | no_go | 374 | 227 | 0.606952 | 0.004114 | 1.00551 | 0.556603 | 0.003325 | 47 | 0.00106383 | 2.07016e-05 | 0.000972975 | True |
| trendline_sweep | CHOP | no_go | 78 | 56 | 0.717949 | 0.63853 | 1.7929 | 0.609689 | 0.317509 | 47 | 0.00106383 | 7.47408e-05 | 0.00351282 | True |
| session_time_bias | RANGING | no_go | 200 | 123 | 0.615 | 0.067483 | 1.0902 | 0.545997 | 0.050885 | 47 | 0.00106383 | 0.000700845 | 0.0329397 | True |

## Q3: Prediction power vs single classifiers

Lower is better. The comparison uses leave-one-out empirical win-rate predictions per bucket, with Laplace smoothing.

| model | features | N | brier_score | log_loss |
| --- | --- | --- | --- | --- |
| v2_only | v2_regime | 5617 | 0.2403 | 0.673625 |
| dow_only | dow_regime | 5617 | 0.240328 | 0.673684 |
| composite | dow_regime+v2_regime | 5617 | 0.240512 | 0.674062 |

Composite Brier delta vs dow_only = +0.000184656; vs v2_only = +0.000211889.

## Q4: Recommended next action

Recommendation: D

compositeではedgeが強化されていないため、Gap 5 / Phase Eの再定義は保留する。
