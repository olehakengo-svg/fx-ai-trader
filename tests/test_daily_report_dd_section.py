"""daily_report「DD防御」節は /api/risk/dashboard の dd_status を描く (rule:R3, 2026-11-19).

旧実装は `status.get("dd", status.get("drawdown"))` を読んでいたが、/api/demo/status
にそのキーは無く、節は一度も描画されなかった (dead code、
[[dd-ledger-broker-close-booking-r3-2026-11-04]] §2 #4 / §6-3)。DD lot lever の SSOT は
JPY 台帳 (`/api/risk/dashboard` `dd_status.jpy_ledger`) なので、そちらを描く。

固定する性質:
  A. risk.dd_status があれば DD% (百分率表示) / lot_multiplier / JPY 台帳 3 値 / pip 台帳
     DD が表に出る
  B. risk が取得失敗 ({} / None) でも例外にならず節は空 (status の他節は従来どおり)
  C. status に "dd" キーがあっても読まない (旧 dead code の経路を復活させない)
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "daily_report_dd_under_test", ROOT / "scripts" / "daily_report.py"
)
dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dr)

_DD_STATUS = {
    "dd_pct": 0.1002, "dd_pips": 1322.6, "defensive_mode": True,
    "eq_current": -1305.7, "eq_peak": 16.9, "lot_multiplier": 0.2,
    "jpy_ledger": {"active": True, "base_capital_jpy": 359109.0, "dd_jpy": 35995.24,
                   "eq_current_jpy": 323293.23, "eq_peak_jpy": 359288.47},
}


def test_dd_section_renders_from_risk_dashboard():
    out = dr.build_dd_defense_section({"risk": {"dd_status": _DD_STATUS}})
    assert out.startswith("### DD防御")
    assert "10.02%" in out
    assert "0.2x" in out
    assert "¥359,288" in out and "¥323,293" in out and "¥35,995" in out
    assert "1322.6p" in out
    assert "| ON |" in out


def test_dd_section_is_part_of_preprocess_status():
    data = {"status": {"modes": {}, "block_counts": {}}, "risk": {"dd_status": _DD_STATUS}}
    out = dr.preprocess_status(data)
    assert "### DD防御" in out
    assert "10.02%" in out


def test_dd_section_empty_when_risk_unavailable():
    assert dr.build_dd_defense_section({"risk": {}}) == ""
    assert dr.build_dd_defense_section({"risk": None}) == ""
    assert dr.build_dd_defense_section({}) == ""
    out = dr.preprocess_status({"status": {"modes": {}}, "risk": {}})
    assert "DD防御" not in out


def test_dd_section_ignores_legacy_status_dd_key():
    data = {"status": {"dd": {"dd_pct": 99, "lot_mult": 0.1}}, "risk": {}}
    assert "DD防御" not in dr.preprocess_status(data)
