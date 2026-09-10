"""nav_floor_projection (F4 資金時計) の性質 pin。

pin する性質 (構文でなく性質で — freshness pin 教訓):
1. 射影の算術 (境界: floor 到達済み / burn<=0 sentinel)
2. 同日再実行の冪等性 (日次 4 回 cron で行が増殖しない)
3. fit は減少系列で正の burn を返し、少数行ではフォールバックへ落ちる
4. 配線: 読み手 (daily-report.yml) が本ツールを呼び、書き先を commit 対象に含み、
   registry F4 エントリが同じ CSV を同じ述語で読む — 「収集済み ≠ 監視済み」教訓
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from tools import nav_floor_projection as nfp

ROOT = Path(__file__).resolve().parent.parent


def test_project_basic_math():
    days, est = nfp.project(nav_jpy=nfp.FLOOR_JPY + 820.0, burn_per_day=82.0,
                            asof=date(2026, 9, 10))
    assert days == 10
    assert est == "2026-09-20"


def test_project_floor_already_breached_is_zero_days():
    days, est = nfp.project(nav_jpy=nfp.FLOOR_JPY - 1, burn_per_day=82.0,
                            asof=date(2026, 9, 10))
    assert days == 0
    assert est == "2026-09-10"


def test_project_growing_nav_uses_sentinel_not_silence():
    days, est = nfp.project(nav_jpy=300_000.0, burn_per_day=-5.0,
                            asof=date(2026, 9, 10))
    assert days == nfp.DAYS_SENTINEL_NO_BURN
    assert est == "n/a"


def test_fit_burn_declining_series_positive_burn():
    rows = [{"date": date(2026, 9, d).isoformat(), "nav_jpy": str(280_000 - 100 * d)}
            for d in range(1, 11)]
    burn = nfp.fit_burn_per_day(rows)
    assert burn is not None
    assert burn == pytest.approx(100.0, rel=1e-6)


def test_fit_burn_too_few_rows_falls_back():
    rows = [{"date": "2026-09-01", "nav_jpy": "280000"},
            {"date": "2026-09-02", "nav_jpy": "279000"}]
    assert nfp.fit_burn_per_day(rows) is None


def test_append_row_same_day_idempotent(tmp_path):
    csv_path = tmp_path / "nav.csv"
    asof = date(2026, 9, 10)
    nfp.append_row(275_000.0, asof=asof, path=csv_path)
    nfp.append_row(275_100.0, asof=asof, path=csv_path)  # 同日 2 回目 = 上書き
    rows = nfp.read_rows(csv_path)
    assert len(rows) == 1
    assert rows[0]["nav_jpy"] == "275100"
    assert rows[0]["method"] == "audit_default"  # 行不足時のフォールバック明示


def test_reader_wiring_daily_report_calls_tool_and_commits_csv():
    """読み手 pin: daily-report.yml が本ツールを実行し、CSV パスを commit に含める。

    これが無いと本ツールは write-only (C1 教訓 / 検知器の main() 配線削除が
    counterfactual を素通りした教訓) — 呼び手の存在そのものを pin する。
    """
    wf = (ROOT / ".github" / "workflows" / "daily-report.yml").read_text(
        encoding="utf-8")
    assert "tools/nav_floor_projection.py" in wf
    assert "data/monitoring" in wf


def test_registry_f4_reads_same_csv_with_90d_predicate():
    """registry F4 が同じ CSV を days_to_floor<=90 で読む (書き手と読み手の対)。"""
    reg = json.loads((ROOT / "knowledge-base" / "wiki" / "decisions" /
                      "prereg-trigger-registry.json").read_text(encoding="utf-8"))
    entries = [t for t in reg["triggers"]
               if t.get("id") == "project-falsification-f4-nav-floor-clock"]
    assert len(entries) == 1, "F4 資金時計エントリが registry に無い"
    e = entries[0]
    assert e["type"] == "csv_row_match"
    assert e["source"]["path"] == "data/monitoring/nav_floor_projection.csv"
    conds = {(c["column"], c["op"]) for c in e["source"]["match"]}
    assert ("days_to_floor", "<=") in conds
    vals = {c["column"]: c["value"] for c in e["source"]["match"]}
    assert float(vals["days_to_floor"]) == 90
