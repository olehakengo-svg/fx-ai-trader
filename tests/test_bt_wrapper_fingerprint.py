import json
import re
from pathlib import Path

import pytest


def _write_wrapper(path: Path, *, pnl_body: str = "return float(trade.get('pnl_pips', 0.0))", threshold: float = 1.3, candidates: str = "'a': {'pair': 'USD_JPY'}", private_body: str = "return 'ignored'") -> None:
    path.write_text(
        f"""
BONFERRONI_ALPHA = 0.05
BONFERRONI_K = 4
VERDICT_THRESHOLDS = {{'promote': {{'min_pf': {threshold}}}}}
CANDIDATES = {{{candidates}}}


def extract_trade_pnl(trade):
    {pnl_body}


def _private_helper():
    {private_body}
""",
    )


def test_wrapper_fingerprint_is_deterministic_and_ignores_whitespace_and_private_helpers(tmp_path):
    from tools.bt_common import compute_wrapper_fingerprint

    wrapper = tmp_path / "wrapper.py"
    _write_wrapper(wrapper)
    first = compute_wrapper_fingerprint(wrapper)

    wrapper.write_text(
        """
# comments and whitespace should not matter
BONFERRONI_ALPHA    =    0.05
BONFERRONI_K = 4
VERDICT_THRESHOLDS = {'promote': {'min_pf': 1.3}}
CANDIDATES = {'a': {'pair': 'USD_JPY'}}


def extract_trade_pnl(trade):

    return float(trade.get('pnl_pips', 0.0))


def _private_helper():
    return 'changed but irrelevant'
"""
    )
    second = compute_wrapper_fingerprint(wrapper)

    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert first == second


def test_wrapper_fingerprint_changes_when_pnl_logic_changes(tmp_path):
    from tools.bt_common import compute_wrapper_fingerprint

    wrapper = tmp_path / "wrapper.py"
    _write_wrapper(wrapper)
    before = compute_wrapper_fingerprint(wrapper)

    _write_wrapper(wrapper, pnl_body="return float(trade.get('pnl_pips', 0.0)) - 0.1")
    after = compute_wrapper_fingerprint(wrapper)

    assert before != after


def test_wrapper_fingerprint_changes_when_locked_threshold_changes(tmp_path):
    from tools.bt_common import compute_wrapper_fingerprint

    wrapper = tmp_path / "wrapper.py"
    _write_wrapper(wrapper)
    before = compute_wrapper_fingerprint(wrapper)

    _write_wrapper(wrapper, threshold=1.31)
    after = compute_wrapper_fingerprint(wrapper)

    assert before != after


def test_wrapper_fingerprint_changes_when_candidates_change(tmp_path):
    from tools.bt_common import compute_wrapper_fingerprint

    wrapper = tmp_path / "wrapper.py"
    _write_wrapper(wrapper)
    before = compute_wrapper_fingerprint(wrapper)

    _write_wrapper(wrapper, candidates="'a': {'pair': 'USD_JPY'}, 'b': {'pair': 'EUR_USD'}")
    after = compute_wrapper_fingerprint(wrapper)

    assert before != after


def test_scalp_alt_aggregate_refuses_missing_or_mismatched_wrapper_fingerprint(monkeypatch, tmp_path, capsys):
    import tools.scalp_alt_pre_reg_bt as mod

    stale = {
        "candidate": mod.metadata_for_candidate("bb_squeeze_breakout"),
        "stats": {"ev_pips": 0.0},
        "verdict": "Reject",
        "reasons": [],
        "flags": [],
        "overfit": {},
        "gate_blocked_likely_gates": [],
    }
    stale_path = tmp_path / "scalp-alt-bb_squeeze-2026-05-03.json"
    stale_path.write_text(json.dumps(stale))

    monkeypatch.setattr(mod, "CANDIDATES", {"bb_squeeze_breakout": mod.CANDIDATES["bb_squeeze_breakout"]})
    monkeypatch.setattr(mod, "default_candidate_output_path", lambda strategy: stale_path)

    assert mod.run_aggregate(str(tmp_path / "aggregate.md")) == 2
    assert "wrapper_fingerprint mismatch" in capsys.readouterr().err


@pytest.mark.parametrize(
    "module_path",
    [
        "tools/scalp_alt_pre_reg_bt.py",
        "tools/scalp_re_enable_bt.py",
        "tools/vec_harness_chunked_cli.py",
    ],
)
def test_real_bt_wrappers_have_nonempty_fingerprint(module_path):
    from tools.bt_common import compute_wrapper_fingerprint

    fingerprint = compute_wrapper_fingerprint(module_path)

    assert re.fullmatch(r"[0-9a-f]{64}", fingerprint)
