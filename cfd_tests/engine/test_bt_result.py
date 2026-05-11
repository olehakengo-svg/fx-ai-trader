"""BTResult dataclass: 7-axis fields + serialization."""
from __future__ import annotations

import dataclasses
import sqlite3
from pathlib import Path

import pandas as pd

from cfd_trader.engine.bt_result import BTResult, init_bt_results_table


def make_result() -> BTResult:
    return BTResult(
        strategy_name="dummy",
        instrument="SPX500_USD",
        tf="M5",
        start_iso="2026-02-11T00:00:00Z",
        end_iso="2026-05-11T00:00:00Z",
        n=42,
        wr=0.55,
        ev_point=0.8,
        pf=1.4,
        wilson_lo=0.41,
        kelly_fraction=0.12,
        max_dd_point=18.5,
        single_year_concentration=0.71,
        data_source="oanda",
        metadata_json='{"bonferroni_m": 1}',
    )


def test_bt_result_is_frozen_dataclass() -> None:
    r = make_result()
    assert dataclasses.is_dataclass(r)
    assert r.__class__ is BTResult


def test_bt_result_to_dict_round_trip() -> None:
    r = make_result()
    d = r.to_dict()
    assert d["strategy_name"] == "dummy"
    assert d["n"] == 42
    assert d["wr"] == 0.55
    assert d["wilson_lo"] == 0.41


def test_init_bt_results_table_creates_schema(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    init_bt_results_table(str(db))
    conn = sqlite3.connect(str(db))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(bt_results)").fetchall()}
    expected = {
        "id", "strategy_name", "instrument", "tf", "start_iso", "end_iso",
        "n", "wr", "ev_point", "pf", "wilson_lo", "kelly_fraction",
        "max_dd_point", "single_year_concentration", "data_source",
        "metadata_json", "created_at",
    }
    assert expected.issubset(cols)


def test_bt_result_insert_round_trip(tmp_path: Path) -> None:
    from cfd_trader.engine.bt_result import insert_bt_result, fetch_bt_results
    db = tmp_path / "t.db"
    init_bt_results_table(str(db))
    insert_bt_result(str(db), make_result())
    rows = fetch_bt_results(str(db), strategy_name="dummy")
    assert len(rows) == 1
    assert rows[0].n == 42
    assert rows[0].instrument == "SPX500_USD"
