from __future__ import annotations

import csv
from pathlib import Path

from tools import price_shock_dedup_analysis as dedup


def test_price_shock_dedup_real_db_counts_and_representative_rule():
    assert dedup.DB_PATH.exists(), "real price shock grid DB is required; mock-only test is forbidden"
    cells = dedup.fetch_shadow_cells(dedup.DB_PATH)
    rows = dedup.build_family_rows(cells)

    assert len(cells) == 227
    assert len(rows) == 23

    by_key = {row.family_key: row for row in rows}
    eur_gbp = by_key["EUR_GBP_H1_LONG_SHOCK"]
    assert eur_gbp.rep["cell_id"] == "EUR_GBP_H1_LONG_SHOCK_1_3_Q5"
    assert eur_gbp.bonf_pass_count == 28
    assert eur_gbp.family_cell_count == 35
    assert eur_gbp.tier == "Tier 1"


def test_price_shock_dedup_tier_caps_use_literal_limits():
    cells = dedup.fetch_shadow_cells(dedup.DB_PATH)
    rows = dedup.build_family_rows(cells)
    counts = dedup.tier_counts(rows)

    assert counts == {"Tier 1": 5, "Tier 2": 0, "Tier 3": 5, "Tier 4": 13}
    assert counts["Tier 1"] + counts["Tier 2"] + counts["Tier 3"] <= 15
    assert all(row.tier == "Tier 4" for row in rows if "exceeded max family cap" in row.tier_reason)


def test_price_shock_dedup_report_generation_with_real_db(tmp_path: Path):
    rows = dedup.run(dedup.DB_PATH, tmp_path)

    csv_path = tmp_path / "dedup_families.csv"
    shortlist_path = tmp_path / "shadow_promote_shortlist.md"
    audit_path = tmp_path / "dedup_audit.md"
    assert csv_path.exists()
    assert shortlist_path.exists()
    assert audit_path.exists()

    with csv_path.open(newline="", encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    assert len(records) == 23
    assert records[0]["family_key"] == "EUR_GBP_H1_LONG_SHOCK"
    assert records[0]["tier"] == "Tier 1"
    assert records[0]["rep_cell_id"] == "EUR_GBP_H1_LONG_SHOCK_1_3_Q5"
    assert len(rows) == len(records)

    shortlist = shortlist_path.read_text(encoding="utf-8")
    assert "**Tier 1 5 family / Tier 2 0 family / Tier 3 5 family / Tier 4 13 family**" in shortlist
    assert "## Tier 4 (REJECT)" in shortlist

    audit = audit_path.read_text(encoding="utf-8")
    assert "- Count match: PASS" in audit
    assert "- Family count match: PASS" in audit
    assert "- Tier cap check: PASS" in audit
