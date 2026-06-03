---
title: Shadow SL rollback bug — all in-flight SL modifications were silently neutered for shadow trades
date: 2026-06-03
discovered_via: live verification of MFE BE-lock A/B
severity: structural / high — affects every SL-trail and BE on shadow stream historically
status: fixed in modules/demo_trader.py (commit pending)
related:
  - knowledge-base/wiki/analyses/mfe-be-lock-design-2026-06-03.md
  - knowledge-base/wiki/lessons/lesson-snapshot-survivorship-bias-2026-06-03.md
---

# Lesson: shadow trades' SL changes were silently rolled back

## Discovery

After shipping the MFE BE-lock A/B (env `SHADOW_BE_LOCK_ENABLE=1`,
`SHADOW_BE_LOCK_AB_FRACTION=0.5`) and confirming the deploy went live,
2 group-B trades had `unrealized_pips ≥ trigger` but their SLs were
**unchanged from the original entry-time placement**. BE-lock should
have moved SL to `entry ± (spread + floor)` but did not.

Trade-level evidence (pulled from `/api/demo/status` ~02:51 UTC):

| trade_id | grp | entry_type | inst | dir | unrealized | SL distance from entry |
|---|---|---|---|---|---|---|
| 7f033ec2 | B | sr_channel_reversal | USD_CHF | SELL | +2.6 p | −6.6 p (original) |
| 558fc1be | B | trendline_sweep | EUR_USD | SELL | +3.2 p | −8.4 p (original) |

Both should have shown SL at roughly `entry − (spread + 1 pip)`. They did not.

## Root cause

`modules/demo_trader.py::_sltp_loop`, in the shared "mirror SL change to
OANDA" block (around line 2416 of the post-commit `5ae7081a` source):

```python
if sl != _original_sl:
    if not self._oanda.modify_sl_sync(trade_id, sl, instrument=_inst):
        sl = _original_sl   # OANDA失敗時はSLを元に戻す
```

`modules/oanda_bridge.py::modify_sl_sync` returns `False` when no
`oanda_trade_id` mapping exists (line 877–879):

```python
oanda_id = self._trade_map.get(demo_trade_id)
if not oanda_id:
    return False
```

Shadow trades carry `is_shadow=1` and are deliberately **never placed on
OANDA**, so they have no mapping → `modify_sl_sync` returns False → the
local `sl` is rolled back to `_original_sl` every iteration. **No
SL-modifying logic — BE-lock, SMC BE+0.1, ATR×0.8 BE, ATR×1.5 trail, v6.4
TP extender — has ever taken effect on shadow trades**, despite the code
appearing to support them.

This explains a chunk of the giveback observed in the 2026-06-03 audit:
even when the existing ATR-based BE *would* have fired (rare at the +8-15
pip class), shadow trades never received the locked SL — they all rode
to original SL_HIT.

## Fix

For shadow trades, persist the new SL to DB directly (no OANDA mirror
needed) and stop rolling back:

```python
if sl != _original_sl:
    _is_shadow_t = trade.get("is_shadow", 0) == 1
    if _is_shadow_t:
        try:
            self._db.update_sl_tp(trade_id, sl, tp)
        except Exception:
            pass  # best-effort; never crash the SL loop
    else:
        if not self._oanda.modify_sl_sync(trade_id, sl, instrument=_inst):
            sl = _original_sl
```

The SL loop reads `sl = trade["sl"]` from DB at the top of each iteration,
so persisting via `update_sl_tp` makes the new SL stick across iterations
and survive process restarts. The local `sl` variable is also retained for
the SL_HIT check later in the same iteration.

## Implications

1. **MFE BE-lock A/B is now actually live for shadow.** Group-B trades
   will see their SL move to `entry ± (spread + 1 pip)` when MFE ≥ +2 pips
   (or +3 pips for `vix_carry_unwind` / `mqe_gbpusd_fix` / `dt_bb_rsi_mr` /
   `sr_anti_hunt_bounce` / `orb_trap` / `wick_imbalance_reversion`).
2. **Group A also changes.** Existing ATR-BE / ATR-trail / SMC-BE /
   v6.4-TP-extender will now actually fire on shadow trades. So group A is
   no longer "naked shadow" — it now matches the production logic intent.
3. **The pre-fix audit's giveback numbers (avg 6.39 pips, EV −1.49)** are
   the **lower bound** of what the system could give back when no SL
   protection was applied at all. The realistic post-fix baseline (group
   A with ATR-BE/trail working) will give back less than that.
4. **A/B comparison still works.** The marginal effect of the +2 pip
   BE-lock vs ATR-only is what we'll measure — and that's the right
   question for promotion.

## Discipline reminder

> Always verify the deploy by observing live behavior, not just the
> deploy status. "Deploy live" ≠ "feature works." For SL-modifying
> features, check actual SL on currently-open positions vs entry +
> expected lock floor. The 2 group-B trades with stuck SL caught this
> bug in 8 minutes post-deploy — without that check it would have hidden
> for the entire 30-day A/B window and silently corrupted the verdict.
