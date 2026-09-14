---
title: Shadow SL rollback bug — all in-flight SL modifications were silently neutered for shadow trades
date: 2026-06-03
discovered_via: live verification of MFE BE-lock A/B
severity: structural / high — affects every SL-trail and BE on shadow stream historically
status: fixed in modules/demo_trader.py (commit pending)
related:
  - knowledge-base/wiki/analyses/mfe-be-lock-design-2026-06-03.md
  - knowledge-base/wiki/lessons/lesson-snapshot-survivorship-bias-2026-06-03.md
  - knowledge-base/wiki/analyses/win-side-exit-regime-break-2026-06-03.md
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

---

## 追記 (2026-09-14): 本 fix は shadow の estimand を切り替えていた

修理は正しかったが、**「修理前後の shadow 統計が比較不能になる」という帰結が
どこにも書かれておらず、下流の分析が 3 ヶ月半その境界をまたいで集計し続けた。**
2026-09-13 の cell deepdive が `sr_anti_hunt_bounce` の R:R 反転 (2.30 → 0.25) を
「継続中の構造的劣化」と読み、その原因調査を最優先アクションに指定したのが顕在化事例。
実際には劣化ではなく、本 fix による**計測体制の一度きりの付け替え**だった。

実測 (全戦略 shadow / XAU 除外 / dedup 除外、fix 時刻 = **2026-06-03T07:58Z**):

| 期間 | N | WR | avg_win | R:R | EV | WIN 行の `close_reason=SL_HIT` 率 |
|---|---|---|---|---|---|---|
| pre-fix | 5,377 | 26.3% | 11.72p | 1.90 | −1.45 | 0.3% |
| post-fix | 7,200 | **51.5%** | 4.35p | **0.55** | −1.61 | **88.3%** |

- WR **+25.2pp** は MEMORY `project_be_trail_inflates_python_bt_wr` が Python BT の
  ablation で示した +20pp 水増しの、**本番 shadow での再現**。
- EV はほぼ不変 (−1.45 → −1.61)。WR だけ見れば大改善・R:R だけ見れば崩壊・
  EV は一貫して負 — MEMORY `feedback_partial_quant_trap` の典型。
- pre-fix の shadow R:R 1.90 に対し同期間 live は 1.01。post-fix は shadow 0.55 /
  live 0.42。**異常だったのは pre-fix shadow の方**で、fix は live 忠実度を上げた。

### 恒久ルール

**shadow の payoff 系統計 (`avg_win` / `avg_loss` / `R:R` / `WR` / 保有時間) を
2026-06-03T07:58Z をまたいで集計しない。** 境界前後は別 estimand。
定数の SSOT = `tools/win_side_exit_decomposition.py::SHADOW_EXIT_REGIME_BREAK`、
pin = `tests/test_win_side_exit_decomposition.py`。
全文と決定への影響: [[win-side-exit-regime-break-2026-06-03]]

### 教訓 (§Discipline reminder への追加)

> 「デプロイを実挙動で検証せよ」に加えて — **挙動を変える修理は、その修理が
> 過去データとの比較可能性を壊していないかを同時に宣言せよ。**
> 修理ページに「この時刻をまたぐ集計は不可」の 1 行と、読み手側の pin が無ければ、
> 下流は境界を知らないまま集計を続ける。本件は 103 日間そうなった。
