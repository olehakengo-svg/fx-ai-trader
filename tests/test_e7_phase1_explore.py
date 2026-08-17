"""E7 phase-1 discovery ハーネスの pin (pre-reg §6/§10-6).

pin 対象:
- combo 空間 = 24 (§6 grid、§3.3c 後も不変)
- 凍結パネル join の counts が §3.3c pre-flight 実測と一致 (再現性の機械固定)
- 合成データ self-test の end-to-end 結線
- discovery 成果物 (コミット済み artifact) の整合: m1=0 / 24 combos / OOS 非接触
"""
import json
import os
import subprocess
import sys

import pandas as pd

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)

from tools.event_modality_explore import (  # noqa: E402
    E7_PANEL_CSV, EXPLORE_END, build_combos_e7, load_e7_panel,
)


def test_combo_space_is_24():
    combos = build_combos_e7()
    assert len(combos) == 24
    # grid 構成の pin: 2 series x 2 theta x 2 entry x 3 h
    assert {c["event"] for c in combos} == {"NFP", "CPI"}
    assert {c["theta"] for c in combos} == {0.5, 1.0}
    assert {c["entry_off"] for c in combos} == {1, 2}
    assert {c["h"] for c in combos} == {"h1", "h4", "h24"}


def test_panel_census_matches_preflight_3_3c():
    """§3.3c pre-flight の block 実測の機械再現 (counts のみ、価格非接触)。"""
    full = load_e7_panel(explore_only=False)
    exp_end = pd.Timestamp(EXPLORE_END, tz="UTC")
    disc = {s: [e for e in full[s] if e[0] <= exp_end] for s in full}
    oos = {s: [e for e in full[s] if e[0] > exp_end] for s in full}
    # z 有効数 (warm-up 24 脱落後)
    assert len(disc["NFP"]) == 96 and len(disc["CPI"]) == 96
    # discovery blocks (§3.3c 表)
    assert sum(1 for _, z in disc["NFP"] if abs(z) > 0.5) == 41
    assert sum(1 for _, z in disc["CPI"] if abs(z) > 0.5) == 62
    assert sum(1 for _, z in disc["NFP"] if abs(z) > 1.0) == 22
    assert sum(1 for _, z in disc["CPI"] if abs(z) > 1.0) == 31
    # OOS blocks (§3.3c 表 — counts のみ、リターン非接触)
    assert sum(1 for _, z in oos["NFP"] if abs(z) > 0.5) == 19
    assert sum(1 for _, z in oos["CPI"] if abs(z) > 0.5) == 16


def test_self_test_e7_runs_green():
    r = subprocess.run(
        [sys.executable, os.path.join(_REPO, "tools", "event_modality_explore.py"),
         "self-test-e7"], capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr
    assert "self-test-e7 OK" in r.stdout


def test_discovery_artifact_frozen_m1_zero():
    """2026-08-17 discovery 実行の成果物 pin — m1=0 (選抜通過ゼロ) と OOS 非接触。"""
    fro = json.load(open(os.path.join(
        _REPO, "knowledge-base", "raw", "bt-results", "e7_frozen_candidates.json")))
    dis = json.load(open(os.path.join(
        _REPO, "knowledge-base", "raw", "bt-results", "e7_discovery.json")))
    assert fro["m1"] == 0 and fro["candidates"] == []
    assert fro["explore_end"] == "2023-12-31"
    assert dis["n_combos"] == 24
    # 実効空間 (theta=0.5) の全 combo が EV_te <= 0 だったことの pin
    eff = [c for c in dis["cells"] if c["theta"] == 0.5]
    assert len(eff) == 12
    assert all(c["ev_time_exit"] < 0 for c in eff)
