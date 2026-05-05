# Streak Reversal HTF Soft Penalty Pre-reg LOCK

- LOCK datetime: 2026-05-05T00:13:17Z
- Evaluation deadline: 2026-05-12T23:59:59Z
- Scope: `streak_reversal` daytrade variant only (`app.py`); scalp variant is out of scope because it has no streak-specific HTF block.
- Status before evaluation: LOCKED, no post-hoc threshold changes.

## Hypothesis

`streak_reversal` is a mean-reversion tail-event strategy. The current daytrade HTF hard block rejects SELL reversal signals during HTF bull agreement and BUY reversal signals during HTF bear agreement, removing the trend-tail reversal events that the strategy is designed to harvest.

Changing this strategy-local HTF handling from hard reject to soft penalty should preserve or improve 365d aggregate edge metrics without weakening the pre-registered statistical validation bar.

## Variant Specification

Current hard-reject behavior:

- HTF bull + `streak_reversal` SELL => no new streak signal.
- HTF bear + `streak_reversal` BUY => no new streak signal.

Proposed soft-penalty behavior:

- HTF bull + `streak_reversal` SELL => emit SELL with `entry_type="streak_reversal"` and apply a fixed HTF penalty equivalent to `conf = max(25, conf - 25)`.
- HTF bear + `streak_reversal` BUY => emit BUY with `entry_type="streak_reversal"` and apply the same fixed HTF penalty.
- Existing opposite primary signals remain confidence-penalized and are not force-overridden by streak reversal.
- SL/TP geometry is unchanged and continues to use `calc_sl_tp_v3`.
- A/B switch: unset/default `0` keeps baseline hard-reject behavior; `STREAK_REVERSAL_HTF_SOFT_PENALTY=1` enables the proposed variant for BT/shadow experiments only.

## Evaluation Axes

Required A/B:

- Baseline: current hard reject.
- Proposed: soft penalty.
- Window: 365d.
- Pair/TF: USD_JPY, 15m daytrade.
- Engine: existing `run_daytrade_backtest` / modules BT path with `backtest_mode=True`.

Required metrics:

- N
- WR
- EV
- PF
- Wilson lower 95%
- Kelly
- Bonferroni-adjusted p
- WF folds >= 3 with positive_ratio

## LOCK Criteria

PASS only if all are true for proposed `streak_reversal`:

- 365d `streak_reversal` N is sufficient for inference.
- Aggregate WR / EV / PF do not degrade versus hard-reject baseline.
- WF folds >= 3 and positive_ratio is acceptable for promotion review.
- Bonferroni-adjusted p remains significant.
- Wilson lower 95% >= current + 0.05.
- Kelly >= 0.40.

If any criterion fails, this variant is rejected for live promotion and the next Wave 4 candidate should be evaluated instead.

## Promotion Boundary

This LOCK authorizes implementation, tests, and shadow proposal only. Live promotion is out of scope and requires a separate approval after shadow N >= 30.
