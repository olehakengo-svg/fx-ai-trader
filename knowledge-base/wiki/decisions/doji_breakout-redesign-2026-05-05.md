# doji_breakout Redesign Pre-reg LOCK (2026-05-05)

## LOCK

- LOCK datetime: 2026-05-05T00:31:02Z
- Evaluation deadline: 2026-05-05T23:59:59Z
- Scope: shadow-stage implementation and 365d backtest only.
- No live promote: live routing/tier-master promotion is out of scope. Any promotion is limited to a shadow promote proposal after criteria pass.

## Current Design Problem

W4-EDA audit Axis 8 states that `doji_breakout` is Tier 1 (LIVE), but GBP_USD degraded from BT 20/65.0%/+0.143 to live 3/0.0%/-8.800, and USD_JPY fell to N=7/`insufficient` in Audit B. The broken axes are Axis 2 and Axis 5.

The primary trigger defect is that the strategy detects Doji range compression but does not require a close outside the Doji range. Current Step 2 uses `bo_body > ATR * 0.5` and candle direction (`bo_close > bo_open` / `< bo_open`), so a large body candle still inside the compressed range can be misclassified as a breakout.

## Proposed Variant

Variant name: `range_close_buffer`

Implementation is opt-in for shadow BT:

- Keep the current 3-Doji compression detection.
- Keep current breakout body threshold: `bo_body > ctx.atr * BREAK_SIZE_MIN`.
- Add range-close breakout confirmation:
  - BUY requires `bo_close > doji_high + breakout_buffer`.
  - SELL requires `bo_close < doji_low - breakout_buffer`.
- `breakout_buffer = max(estimated_spread, 0.1 * ctx.atr)`.
- Keep current SL/TP/RR geometry unchanged for this task.
- Do not add trailing stop or partial take-profit in this variant.

Concrete code delta target:

```python
breakout_buffer = self._breakout_buffer(ctx)
if bo_close > bo_open:
    if self.require_range_close and bo_close <= doji_high + breakout_buffer:
        return None
    signal = "BUY"
elif bo_close < bo_open:
    if self.require_range_close and bo_close >= doji_low - breakout_buffer:
        return None
    signal = "SELL"
```

## Evaluation Axes

Run 365d 15m BT for current vs proposed on pair-promoted cells:

- `doji_breakout × GBP_USD`
- `doji_breakout × USD_JPY`

Metrics:

- N, WR, EV, PnL, PF
- Wilson lower bound for WR
- one-sided binomial p-value vs current WR
- Bonferroni-adjusted p-value over tested cells
- Kelly fraction
- 3-fold walk-forward positive ratio

Pass criteria:

- WF folds >= 3 and positive_ratio >= 0.67.
- Bonferroni-adjusted p < 0.05, or proposed Wilson lower >= current Wilson lower + 0.05.
- Kelly >= 0.40 is desired, but lower can be acceptable only if the redesign is a defensive narrowing with materially improved downside metrics.
- No post-hoc parameter search. Only `range_close_buffer` is evaluated.

Fail criteria:

- N collapses to insufficient evidence without a compensating defensive improvement.
- WF positive_ratio < 0.67.
- Neither Bonferroni nor Wilson improvement gate passes.
- Evidence of look-ahead, data leakage, or post-hoc selection.
