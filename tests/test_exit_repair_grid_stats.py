"""Exit-repair grid BT harness — statistics unit tests (rule:R1 pre-reg exec).

Covers the pure statistical layer of tools/exit_repair_grid_bt.py (block
bootstrap SE/p, chronological WF folds, BH-FDR) with synthetic data — no BT run,
so this stays fast for pre-commit. The app.py EXIT_REPAIR_MODE engine path is
env-gated (default byte-identical) and validated separately by a full BT run.

ref: knowledge-base/wiki/decisions/exit-repair-tp-sl-prereg-2026-07-07.md
"""
import importlib.util
import os

import pandas as pd

_HARNESS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tools", "exit_repair_grid_bt.py")


def _load():
    spec = importlib.util.spec_from_file_location("erg_bt", _HARNESS)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _rows(ev_mean, n=200, seed=0):
    import numpy as np
    rng = np.random.default_rng(seed)
    base = pd.Timestamp("2025-06-01", tz="UTC")
    out = []
    for i in range(n):
        v = float(rng.normal(ev_mean, 6.0))
        ts = base + pd.Timedelta(hours=i * 3)
        out.append({"pair": "USD_JPY", "entry_type": "trendline_sweep",
                    "sig": "BUY", "outcome": "WIN" if v > 0 else "LOSS",
                    "net_pips": v, "net_pips_floor": v + 0.7,
                    "_ts": ts, "_date": ts.normalize()})
    return out


def test_block_bootstrap_positive_edge_significant():
    m = _load()
    ev, se, p = m.block_bootstrap(_rows(1.5, seed=1), "net_pips", b=3000)
    assert ev > 0 and se > 0 and p < 0.05


def test_block_bootstrap_zero_and_negative_edge_not_significant():
    m = _load()
    _, _, p0 = m.block_bootstrap(_rows(0.02, seed=2), "net_pips", b=3000)
    _, _, pneg = m.block_bootstrap(_rows(-1.2, seed=3), "net_pips", b=3000)
    assert p0 > 0.10
    assert pneg > 0.90


def test_wf_folds_sign_ratio():
    m = _load()
    _, pos_hi = m.wf_folds(_rows(1.5, seed=1), "net_pips")
    _, pos_lo = m.wf_folds(_rows(-1.2, seed=3), "net_pips")
    assert pos_hi == 1.0   # all 3 folds positive
    assert pos_lo == 0.0   # none positive


def test_bh_fdr_monotone_selection():
    m = _load()
    # p0..p8; only the smallest few should pass at q=0.10, m=9
    pv = [0.001, 0.02, 0.04, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9]
    passed = m.bh_fdr(pv, 0.10)
    assert 0 in passed and 1 in passed
    assert 3 not in passed and 8 not in passed


def test_bh_fdr_all_null_selects_none():
    m = _load()
    assert m.bh_fdr([0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0], 0.10) == set()


def test_empty_rows_safe():
    m = _load()
    ev, se, p = m.block_bootstrap([], "net_pips", b=100)
    assert ev == 0.0 and se == 0.0 and p == 1.0
    assert m.wf_folds([], "net_pips") == ([], 0.0)
