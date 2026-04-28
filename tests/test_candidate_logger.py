"""Tests for modules/candidate_logger.py — Phase 10 C1."""
import os
import sqlite3
import sys
import tempfile
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from modules.candidate_logger import (
    init_candidates_table,
    log_candidates,
    query_candidate_summary,
)


@dataclass
class _FakeCandidate:
    entry_type: str
    signal: str
    confidence: int
    score: float


@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    os.unlink(path)


class TestInitCandidatesTable:
    def test_creates_table_idempotent(self, tmp_db):
        assert init_candidates_table(tmp_db) is True
        # Second call: still True, no error
        assert init_candidates_table(tmp_db) is True
        # Verify table exists
        conn = sqlite3.connect(tmp_db)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='evaluated_candidates'"
        ).fetchall()
        conn.close()
        assert len(rows) == 1

    def test_creates_indexes(self, tmp_db):
        init_candidates_table(tmp_db)
        conn = sqlite3.connect(tmp_db)
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='evaluated_candidates'"
        ).fetchall()
        conn.close()
        names = {r[0] for r in rows}
        assert "idx_evcand_strategy" in names
        assert "idx_evcand_selected" in names

    def test_returns_false_on_invalid_path(self):
        # Non-existent directory
        assert init_candidates_table("/no/such/dir/x.db") is False


class TestLogCandidates:
    def test_records_all_with_winner_marked(self, tmp_db):
        init_candidates_table(tmp_db)
        c1 = _FakeCandidate("strat_a", "BUY", 60, 3.5)
        c2 = _FakeCandidate("strat_b", "SELL", 50, 4.2)
        c3 = _FakeCandidate("strat_c", "BUY", 70, 2.8)
        # Winner is c2 (highest score)
        ok = log_candidates(
            tmp_db, [c1, c2, c3], c2,
            instrument="USD_JPY", tf="15m", bar_time="2026-04-28 12:00:00",
        )
        assert ok is True
        conn = sqlite3.connect(tmp_db)
        rows = conn.execute(
            "SELECT strategy_name, signal, score, selected, selected_strategy "
            "FROM evaluated_candidates ORDER BY id"
        ).fetchall()
        conn.close()
        assert len(rows) == 3
        assert {r[0] for r in rows} == {"strat_a", "strat_b", "strat_c"}
        # Exactly one row marked selected
        selected = [r for r in rows if r[3] == 1]
        assert len(selected) == 1
        assert selected[0][0] == "strat_b"
        # All rows record the winner name
        for r in rows:
            assert r[4] == "strat_b"

    def test_empty_candidates_returns_true(self, tmp_db):
        init_candidates_table(tmp_db)
        ok = log_candidates(tmp_db, [], None, instrument="USD_JPY")
        assert ok is True
        conn = sqlite3.connect(tmp_db)
        n = conn.execute("SELECT COUNT(*) FROM evaluated_candidates").fetchone()[0]
        conn.close()
        assert n == 0

    def test_handles_missing_attrs_defensively(self, tmp_db):
        init_candidates_table(tmp_db)

        class _Broken:
            entry_type = "broken_strat"
            # missing signal/confidence/score

        # Should not raise, should still insert with defaults
        ok = log_candidates(
            tmp_db, [_Broken()], None,
            instrument="EUR_USD", tf="15m",
        )
        assert ok is True

    def test_no_table_returns_false_without_raising(self):
        # Path with no init
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            c = _FakeCandidate("x", "BUY", 50, 1.0)
            ok = log_candidates(path, [c], c, instrument="USD_JPY")
            # Without init, table doesn't exist; function returns False
            assert ok is False
        finally:
            os.unlink(path)

    def test_winner_none_marks_no_selected(self, tmp_db):
        init_candidates_table(tmp_db)
        c1 = _FakeCandidate("strat_a", "BUY", 50, 3.0)
        log_candidates(tmp_db, [c1], None, instrument="GBP_JPY")
        conn = sqlite3.connect(tmp_db)
        row = conn.execute(
            "SELECT selected, selected_strategy FROM evaluated_candidates"
        ).fetchone()
        conn.close()
        assert row[0] == 0
        assert row[1] is None


class TestQueryCandidateSummary:
    def test_summary_counts(self, tmp_db):
        init_candidates_table(tmp_db)
        # Bar 1: 3 candidates, strat_b wins
        cands1 = [
            _FakeCandidate("strat_a", "BUY", 50, 3.0),
            _FakeCandidate("strat_b", "SELL", 60, 4.0),
            _FakeCandidate("strat_c", "BUY", 50, 2.0),
        ]
        log_candidates(tmp_db, cands1, cands1[1], instrument="USD_JPY")
        # Bar 2: 2 candidates, strat_a wins
        cands2 = [
            _FakeCandidate("strat_a", "BUY", 50, 5.0),
            _FakeCandidate("strat_b", "SELL", 60, 3.5),
        ]
        log_candidates(tmp_db, cands2, cands2[0], instrument="USD_JPY")
        summary = query_candidate_summary(tmp_db, days=0)
        assert summary["strat_a"]["total_candidates"] == 2
        assert summary["strat_a"]["n_selected"] == 1
        assert summary["strat_b"]["total_candidates"] == 2
        assert summary["strat_b"]["n_selected"] == 1
        assert summary["strat_c"]["total_candidates"] == 1
        assert summary["strat_c"]["n_selected"] == 0  # never won — bottleneck case
