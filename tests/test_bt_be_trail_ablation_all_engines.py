"""BE/Trail ablation default = TV-aligned in ALL BT engines (rule:R3).

audit P1-2/P1-2b (fable5-system-audit-2026-07-02) / roadmap v2.3 T14.

BE/Trail simulation assumes favorable->adverse ordering within the same bar
and inflates Python BT WR by ~+20pp vs TV Pine (MEMORY
project_be_trail_inflates_python_bt_wr, divergence-ablation 2026-05-14).
The daytrade engine was guarded on 2026-05-15; this pins the same contract
for the remaining engines:

  * run_backtest (1H standard), run_scalp_backtest, run_1h_backtest
    - default            -> BE/Trail OFF (ablated, TV-aligned)
    - BT_OPTIMISTIC=1    -> legacy optimistic behaviour restored
    - BT_ABLATE_BE_TRAIL=1 wins over BT_OPTIMISTIC=1
  * BT cache keys reflect the flags (stale-cache prevention)
  * same-bar TP+SL fut_close tie-break present in all 4 intraday engines
    (P1-2b) and run_swing_backtest keeps its stricter SL-priority tie-break
"""
import inspect
import re

import pytest

import app


# ── 1. env-flag semantics (shared helper) ──────────────────────────


def test_default_is_ablated_tv_aligned(monkeypatch):
    monkeypatch.delenv("BT_OPTIMISTIC", raising=False)
    monkeypatch.delenv("BT_ABLATE_BE_TRAIL", raising=False)
    bt_optimistic, ablate = app._bt_exit_optimism_flags()
    assert bt_optimistic is False
    assert ablate is True  # BE/Trail OFF by default


def test_bt_optimistic_restores_be_trail(monkeypatch):
    monkeypatch.setenv("BT_OPTIMISTIC", "1")
    monkeypatch.delenv("BT_ABLATE_BE_TRAIL", raising=False)
    bt_optimistic, ablate = app._bt_exit_optimism_flags()
    assert bt_optimistic is True
    assert ablate is False  # legacy optimistic behaviour restored


def test_explicit_ablation_wins_over_optimistic(monkeypatch):
    monkeypatch.setenv("BT_OPTIMISTIC", "1")
    monkeypatch.setenv("BT_ABLATE_BE_TRAIL", "1")
    bt_optimistic, ablate = app._bt_exit_optimism_flags()
    assert bt_optimistic is True
    assert ablate is True


def test_helper_matches_daytrade_reference_semantics(monkeypatch):
    """The shared helper must reproduce the daytrade inline expression
    (app.py `_BT_ABLATE_BE_TRAIL = (not _BT_OPTIMISTIC) or (...)`) for
    every env combination."""
    for opt in ("", "1"):
        for abl in ("", "1"):
            if opt:
                monkeypatch.setenv("BT_OPTIMISTIC", opt)
            else:
                monkeypatch.delenv("BT_OPTIMISTIC", raising=False)
            if abl:
                monkeypatch.setenv("BT_ABLATE_BE_TRAIL", abl)
            else:
                monkeypatch.delenv("BT_ABLATE_BE_TRAIL", raising=False)
            expected_opt = opt == "1"
            expected_abl = (not expected_opt) or (abl == "1")
            assert app._bt_exit_optimism_flags() == (expected_opt, expected_abl)


# ── 2. per-engine guard pins (source-level) ────────────────────────

_GUARDED_ENGINES = [
    app.run_backtest,        # 1H standard (audit: app.py run_backtest)
    app.run_scalp_backtest,  # scalp (audit: run_scalp_backtest)
    app.run_1h_backtest,     # 1H zone (audit: run_1h_backtest)
]


@pytest.mark.parametrize("engine", _GUARDED_ENGINES,
                         ids=lambda f: f.__name__)
def test_engine_reads_shared_ablation_flags(engine):
    src = inspect.getsource(engine)
    assert "_bt_exit_optimism_flags()" in src, (
        f"{engine.__name__} must derive _BT_ABLATE_BE_TRAIL from the "
        "shared helper (default = BE/Trail OFF, BT_OPTIMISTIC=1 restores)")


@pytest.mark.parametrize("engine", _GUARDED_ENGINES,
                         ids=lambda f: f.__name__)
def test_engine_neutralizes_be_trail_thresholds_under_ablation(engine):
    """Under ablation the BE/Trail thresholds are pushed to +inf so
    _be_activated can never fire (same pattern as the daytrade engine)."""
    src = inspect.getsource(engine)
    guard = re.search(
        r"if _BT_ABLATE_BE_TRAIL:\n(?:\s*#.*\n)*"
        r"(?P<body>(?:\s+_\w+ = float\(\"inf\"\)\n)+)",
        src)
    assert guard is not None, (
        f"{engine.__name__}: missing `if _BT_ABLATE_BE_TRAIL:` guard that "
        "sets BE/Trail thresholds to float(\"inf\")")


def test_daytrade_reference_guard_unchanged():
    """Reference implementation (guarded 2026-05-15) must keep its
    contract: ablation on by default, BT_OPTIMISTIC=1 opt-out."""
    src = inspect.getsource(app.run_daytrade_backtest)
    assert '_BT_OPTIMISTIC = os.environ.get("BT_OPTIMISTIC") == "1"' in src
    assert ('_BT_ABLATE_BE_TRAIL = (not _BT_OPTIMISTIC) or '
            '(os.environ.get("BT_ABLATE_BE_TRAIL") == "1")') in src
    assert "if _BT_ABLATE_BE_TRAIL:" in src


# ── 3. cache keys reflect the flags (stale-cache prevention) ───────


def test_cache_suffix_changes_with_flags(monkeypatch):
    monkeypatch.delenv("BT_OPTIMISTIC", raising=False)
    monkeypatch.delenv("BT_ABLATE_BE_TRAIL", raising=False)
    default_suffix = app._bt_exit_optimism_cache_suffix()
    assert default_suffix == "_abl0_opt0"

    monkeypatch.setenv("BT_OPTIMISTIC", "1")
    assert app._bt_exit_optimism_cache_suffix() == "_abl0_opt1"
    monkeypatch.setenv("BT_ABLATE_BE_TRAIL", "1")
    assert app._bt_exit_optimism_cache_suffix() == "_abl1_opt1"


@pytest.mark.parametrize("engine", [app.run_scalp_backtest,
                                    app.run_1h_backtest],
                         ids=lambda f: f.__name__)
def test_keyed_caches_embed_ablation_suffix(engine):
    src = inspect.getsource(engine)
    cache_key_stmt = src.split("cache_key = ", 1)[1].split("now = ", 1)[0]
    assert "_bt_exit_optimism_cache_suffix()" in cache_key_stmt, (
        f"{engine.__name__}: cache_key must embed the ablation suffix, "
        "otherwise flipping BT_OPTIMISTIC serves stale results")


def test_run_backtest_unkeyed_cache_checks_flags():
    """run_backtest uses a single global dict cache; it must store and
    compare the flag suffix before serving a cached result."""
    src = inspect.getsource(app.run_backtest)
    assert '_bt_cache.get("flags") == _bt_flags' in src
    assert '_bt_cache["flags"]' in src


# ── 4. P1-2b: same-bar TP+SL tie-break coverage ────────────────────

_ALL_INTRADAY_ENGINES = [
    app.run_backtest,
    app.run_scalp_backtest,
    app.run_daytrade_backtest,
    app.run_1h_backtest,
]


@pytest.mark.parametrize("engine", _ALL_INTRADAY_ENGINES,
                         ids=lambda f: f.__name__)
def test_same_bar_tp_sl_tie_break_uses_fut_close(engine):
    """Every same-bar TP+SL collision must be resolved via fut_close
    (daytrade reference pattern), never by unconditional TP-priority."""
    src_lines = inspect.getsource(engine).splitlines()
    tie_break_sites = [i for i, line in enumerate(src_lines)
                       if "if hit_tp and hit_sl:" in line]
    assert len(tie_break_sites) == 2, (
        f"{engine.__name__}: expected BUY+SELL tie-break sites")
    for i in tie_break_sites:
        window = "\n".join(src_lines[i + 1:i + 3])
        assert "fut_close" in window, (
            f"{engine.__name__}: same-bar TP+SL tie-break must reference "
            f"fut_close, got:\n{window}")


def test_swing_engine_keeps_conservative_sl_priority_tie_break():
    """run_swing_backtest resolves same-bar TP+SL as LOSS (SL priority),
    which is stricter than fut_close — must not regress to TP-priority."""
    src = inspect.getsource(app.run_swing_backtest)
    assert re.search(
        r"if hit_tp and hit_sl:\s*\n\s+outcome = \"LOSS\"", src), (
        "run_swing_backtest same-bar tie-break must stay SL-priority (LOSS)")
