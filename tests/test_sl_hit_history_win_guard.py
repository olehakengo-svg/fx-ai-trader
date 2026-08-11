"""Regression pin (rule:R3 2026-08-07): the SL-hunt history feed must not
record winning exits.

Bug (structural, live-behaviour): `close_reason == "SL_HIT"` only means
"price touched the CURRENT stop". BE-lock / trailing / Profit Extender move
that stop to the profit side of entry, so a profit-taking exit carries the
very same label. Production measurement (N=3308 closed rows, 2026-08-07):

    SL on profit side of entry : 1894 rows -> 1848 (97.6%) closed POSITIVE
    SL on risk   side of entry : 1414 rows -> 1408 (99.6%) closed NEGATIVE
    outcome=WIN among SL_HIT   : 1792 = 54.2%

`_sl_hit_history` feeds two *defensive* consumers that assume "we just got
stopped out":

  * cascade cooldown: blocks EVERY strategy on that instrument for 45-600s
    after an SL_HIT
  * Fast-SL adaptive defence: widens the next trade's SL by ATR*0.3 when a
    sub-120s SL_HIT happened on that instrument in the last 5 minutes

Feeding wins into them suppresses attack after a WIN, violating 4原則 #1
(攻める) / #4 (攻撃は最大の防御). 54.2% of all trigger events were spurious;
of the sub-120s "fast SL" triggers, 57.1% were wins.

The immediately preceding block in the same close path
(`if outcome != "WIN":` -> `self._last_exit` / `_total_losses_window`)
already excludes wins for the identical "don't re-enter after a stop"
purpose, with an explicit comment. The asymmetry between the two blocks WAS
the bug.

Analysis: knowledge-base/wiki/analyses/sl-hit-label-collision-2026-08-07.md

Design notes:
  - Pinned at the AST level rather than by driving `_check_sltp_realtime`,
    because the append site sits deep inside the live close path (OANDA
    close + DB write + equity ledger). The structural property we must
    never lose is narrow and statable: *the branch that writes to
    `_sl_hit_history` is conditioned on `outcome` as well as on
    `close_reason`*.
  - Sources are read from DISK, not via `inspect.getsource(module)`.
    Other tests in this suite monkeypatch `modules.demo_trader.DemoTrader`
    with a stub at module scope, which leaks across tests and made an
    import-based version of this pin pass alone but fail in a full run.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _source(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def _append_guard_test() -> ast.expr:
    """Return the `test` expression of the innermost `if` whose body writes
    to `self._sl_hit_history`, inside `_check_sltp_realtime`."""
    tree = ast.parse(_source("modules/demo_trader.py"))
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef)
               and n.name == "_check_sltp_realtime"), None)
    assert fn is not None, (
        "_check_sltp_realtime not found in modules/demo_trader.py — the "
        "close path moved; re-pin this test rather than deleting it")

    def writes_history(node: ast.AST) -> bool:
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call)
                    and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr == "append"
                    and isinstance(sub.func.value, ast.Attribute)
                    and sub.func.value.attr == "_sl_hit_history"):
                return True
        return False

    candidates = [n for n in ast.walk(fn)
                  if isinstance(n, ast.If)
                  and any(writes_history(b) for b in n.body)]
    assert candidates, (
        "no `if` block writes to self._sl_hit_history in "
        "_check_sltp_realtime — the append site moved; re-pin this test "
        "rather than deleting it")
    # innermost = the one with the smallest body span
    candidates.sort(key=lambda n: (n.end_lineno or 0) - n.lineno)
    return candidates[0].test


def _names_and_strings(node: ast.expr):
    names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    strings = {n.value for n in ast.walk(node)
               if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return names, strings


def test_sl_hit_history_append_is_guarded_by_outcome():
    """The SL-hunt feed must exclude winning exits (54.2% of SL_HIT rows)."""
    guard = _append_guard_test()
    names, strings = _names_and_strings(guard)

    assert "close_reason" in names, (
        "guard no longer inspects close_reason: %s" % ast.dump(guard))
    assert "SL_HIT" in strings, (
        "guard no longer pins the SL_HIT label: %s" % ast.dump(guard))
    assert "outcome" in names, (
        "REGRESSION: self._sl_hit_history is fed without checking `outcome`. "
        "close_reason=='SL_HIT' includes BE-lock/trailing profit exits "
        "(production: 54.2% are outcome=WIN), and this history drives the "
        "cascade cooldown + Fast-SL widening. Feeding wins into it blocks "
        "entries and widens stops after a WIN. See "
        "knowledge-base/wiki/analyses/sl-hit-label-collision-2026-08-07.md")
    assert "WIN" in strings, (
        "guard checks `outcome` but no longer against 'WIN': %s"
        % ast.dump(guard))


def test_sl_hit_history_guard_excludes_only_wins():
    """Losses and break-evens must still reach the SL-hunt feed.

    A stop taken out at BE is still evidence of an adverse sweep, so the
    guard must be `!= "WIN"` (exclude wins only), not `== "LOSS"`
    (which would silently drop the 75 BREAKEVEN rows measured in
    production).
    """
    guard = _append_guard_test()
    compares = [n for n in ast.walk(guard)
                if isinstance(n, ast.Compare)
                and any(isinstance(o, (ast.NotEq, ast.Eq)) for o in n.ops)
                and isinstance(n.left, ast.Name)
                and n.left.id == "outcome"]
    assert compares, "no direct `outcome` comparison found in guard"
    assert isinstance(compares[0].ops[0], ast.NotEq), (
        "outcome guard must be `outcome != \"WIN\"` (exclude wins only). "
        "`outcome == \"LOSS\"` would also drop BREAKEVEN stop-outs, which "
        "ARE valid SL-hunt evidence (75 such rows in the 2026-08-07 "
        "production sample).")


@pytest.mark.parametrize("rel_path,symbol", [
    ("modules/learning_engine.py", "sl_losses"),
    ("modules/daily_review.py", "sl_hits"),
])
def test_advisory_sl_rate_consumers_filter_on_outcome(rel_path, symbol):
    """`SLヒット率` advisories must count losses, not trailing profit exits.

    Both consumers gate a "widen the SL" recommendation on an SL-hit rate.
    Counting raw close_reason made that rate 82.7% in production while the
    true stop-out rate was 36.0% (1441/4000) — i.e. the advisory fired on a
    book whose stops were mostly *profit* exits.
    """
    src = _source(rel_path)
    idx = src.index(symbol + " =")
    window = src[idx:idx + 400]
    assert "SL_HIT" in window, (
        f"{symbol} no longer references SL_HIT — re-pin this test")
    assert "outcome" in window, (
        f"REGRESSION: {rel_path}:{symbol} counts close_reason=='SL_HIT' "
        "without filtering on outcome, so BE-lock/trailing profit exits "
        "inflate the SL-hit rate (production: 82.7% raw vs 36.0% true). "
        "See knowledge-base/wiki/analyses/"
        "sl-hit-label-collision-2026-08-07.md")
