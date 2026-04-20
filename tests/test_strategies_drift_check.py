"""Unit tests for tools/strategies_drift_check.py.

These tests exercise the core detection logic against synthetic markdown pages
and a synthetic tier-master snapshot, so they run fast and stay independent
from the real knowledge base contents.

They also run the checker once against the live tier-master.json to guarantee
the committed strategy pages stay integrity-clean (regression test).
"""

import json
import os
import sys
import importlib.util
import textwrap

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOL_PATH = os.path.join(_ROOT, "tools", "strategies_drift_check.py")


def _load_tool():
    """Load the script as a module for in-process unit testing."""
    spec = importlib.util.spec_from_file_location(
        "strategies_drift_check", _TOOL_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tool():
    return _load_tool()


@pytest.fixture
def synth_truth():
    return {
        "elite_live": {"trendline_sweep"},
        "force_demoted": {"ema_cross", "orb_trap"},
        "scalp_sentinel": {"bb_rsi_reversion"},
        "universal_sentinel": {"post_news_vol"},
        "pair_promoted": {
            ("post_news_vol", "GBP_USD"),
            ("post_news_vol", "EUR_USD"),
            ("doji_breakout", "USD_JPY"),
        },
        "pair_demoted": {
            ("bb_rsi_reversion", "USD_JPY"),
            ("post_news_vol", "USD_JPY"),
        },
    }


def _write_page(tmp_path, filename, body):
    p = tmp_path / filename
    p.write_text(textwrap.dedent(body).lstrip("\n"))
    return str(p)


# ── Core detection tests ────────────────────────────────────────────────


def test_clean_page_has_no_issues(tool, synth_truth, tmp_path):
    path = _write_page(tmp_path, "bb-rsi-reversion.md", """
        # bb_rsi_reversion

        ## Status: SCALP_SENTINEL + PAIR_DEMOTED (USD_JPY)
        some body
    """)
    issues = tool._check_strategy("bb_rsi_reversion", path, synth_truth)
    assert issues == []


def test_detects_stale_pair_promoted_claim(tool, synth_truth, tmp_path):
    """The bb_rsi_reversion regression case: claims PP x USD_JPY after demotion."""
    path = _write_page(tmp_path, "bb-rsi-reversion.md", """
        # bb_rsi_reversion

        ## Status: Tier 1 (PAIR_PROMOTED x USD_JPY)
        body
    """)
    issues = tool._check_strategy("bb_rsi_reversion", path, synth_truth)
    # Should flag PP x USD_JPY (not in truth) AND PAIR_DEMOTED conflict
    assert any("PAIR_PROMOTED" in i and "USD_JPY" in i for i in issues), issues
    assert any("PAIR_DEMOTED in truth" in i for i in issues), issues


def test_detects_elite_on_non_elite(tool, synth_truth, tmp_path):
    path = _write_page(tmp_path, "ema-cross.md", """
        # ema_cross

        ## Status: ELITE_LIVE
    """)
    issues = tool._check_strategy("ema_cross", path, synth_truth)
    assert any("ELITE_LIVE" in i and "not in truth.elite_live" in i for i in issues)


def test_detects_force_demoted_on_non_fd(tool, synth_truth, tmp_path):
    path = _write_page(tmp_path, "post-news-vol.md", """
        # post_news_vol

        ## Status: FORCE_DEMOTED
    """)
    issues = tool._check_strategy("post_news_vol", path, synth_truth)
    assert any("FORCE_DEMOTED" in i and "not in truth.force_demoted" in i for i in issues)


def test_ignores_negative_context_mentions(tool, synth_truth, tmp_path):
    """'SHADOW (not in ELITE_LIVE, PAIR_PROMOTED, or FORCE_DEMOTED)' is a description,
    not a tier claim."""
    path = _write_page(tmp_path, "stub.md", """
        # stub_strategy

        - **Status**: SHADOW (not in ELITE_LIVE, PAIR_PROMOTED, or FORCE_DEMOTED)
    """)
    # stub_strategy isn't in truth at all; the only check that could fire is the
    # "claims ELITE_LIVE/FORCE_DEMOTED" one, which must be suppressed by _NEG_RE.
    issues = tool._check_strategy("stub_strategy", path, synth_truth)
    assert all("claims ELITE_LIVE" not in i for i in issues), issues
    assert all("claims FORCE_DEMOTED" not in i for i in issues), issues


def test_accepts_pair_promoted_pair_in_truth(tool, synth_truth, tmp_path):
    path = _write_page(tmp_path, "post-news-vol.md", """
        # post_news_vol

        - **Status**: UNIVERSAL_SENTINEL + PAIR_PROMOTED (GBP_USD, EUR_USD) + PAIR_DEMOTED (USD_JPY)
    """)
    issues = tool._check_strategy("post_news_vol", path, synth_truth)
    # GBP_USD, EUR_USD are in truth PP; USD_JPY is in PAIR_DEMOTED scope (not PP scope).
    assert issues == [], issues


def test_force_demoted_truth_requires_label_in_header(tool, synth_truth, tmp_path):
    """If a strategy IS in force_demoted but the page header doesn't say so → drift."""
    path = _write_page(tmp_path, "orb-trap.md", """
        # orb_trap

        ## Status: Tier 1 (PAIR_PROMOTED x USD_JPY, EUR_USD, GBP_USD)
    """)
    issues = tool._check_strategy("orb_trap", path, synth_truth)
    assert any("truth says FORCE_DEMOTED" in i for i in issues), issues


def test_missing_status_header_is_an_issue(tool, synth_truth, tmp_path):
    path = _write_page(tmp_path, "x.md", """
        # some_strategy

        No status section here at all.
    """)
    issues = tool._check_strategy("bb_rsi_reversion", path, synth_truth)
    assert any("no Status/Stage header" in i for i in issues)


def test_pairs_in_scope_respects_keyword_boundaries(tool):
    line = (
        "UNIVERSAL_SENTINEL + PAIR_PROMOTED (GBP_USD, EUR_USD) + "
        "PAIR_DEMOTED (USD_JPY)"
    )
    pp = tool._pairs_in_scope(line, "PAIR_PROMOTED")
    pd = tool._pairs_in_scope(line, "PAIR_DEMOTED")
    assert pp == {"GBP_USD", "EUR_USD"}
    assert pd == {"USD_JPY"}


def test_canonical_name_from_filename(tool):
    assert tool._canonical_name("bb-rsi-reversion.md") == "bb_rsi_reversion"
    assert tool._canonical_name("vwap-mean-reversion.md") == "vwap_mean_reversion"
    assert tool._canonical_name("rnb-usdjpy.md") == "rnb_usdjpy"


# ── Regression test: the real KB must stay clean ─────────────────────────


def test_live_kb_passes_drift_check():
    """Running the tool against the committed KB + tier-master.json must exit 0."""
    import subprocess
    result = subprocess.run(
        [sys.executable, _TOOL_PATH],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Drift check failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert "integrity-clean" in result.stdout
