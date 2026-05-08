from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tools import shadow_promote_r2_alert as spr2


NOW = datetime(2026, 5, 7, 0, 0, tzinfo=timezone.utc)


def _promoted(*strategies: str) -> list[dict[str, str]]:
    return [
        {
            "strategy": strategy,
            "env_key": f"{strategy.upper()}_REDESIGN_V2_SHADOW_PROMOTE",
        }
        for strategy in strategies
    ]


def _trades(strategy: str, n: int, pnl: float, *, instrument: str = "USD_JPY") -> list[dict]:
    return [
        {
            "entry_type": strategy,
            "instrument": instrument,
            "is_shadow": 1,
            "pnl_pips": pnl,
            "created_at": (NOW - timedelta(minutes=i)).isoformat(),
        }
        for i in range(n)
    ]


def _cell(result: dict, strategy: str, instrument: str = "USD_JPY") -> dict:
    for cell in result["cells"]:
        if cell["strategy"] == strategy and cell["instrument"] == instrument:
            return cell
    raise AssertionError(f"missing cell {strategy} x {instrument}")


def test_n9_negative_ev_no_alert(tmp_path):
    result, exit_code = spr2.run(
        _trades("n9", 9, -1.0),
        _promoted("n9"),
        now=NOW,
        report_dir=tmp_path,
        write_md=False,
    )

    assert _cell(result, "n9")["severity"] == "OK"
    assert exit_code == 0


def test_n10_negative_ev_warn(tmp_path):
    result, exit_code = spr2.run(
        _trades("n10", 10, -1.0),
        _promoted("n10"),
        now=NOW,
        report_dir=tmp_path,
        write_md=False,
    )

    cell = _cell(result, "n10")
    assert cell["severity"] == "WARN"
    assert cell["n"] == 10
    assert cell["ev"] == -1.0
    assert exit_code == 0


def test_n30_negative_ev_critical(tmp_path):
    result, exit_code = spr2.run(
        _trades("n30_bad", 30, -0.5),
        _promoted("n30_bad"),
        now=NOW,
        report_dir=tmp_path,
        write_md=False,
    )

    cell = _cell(result, "n30_bad")
    assert cell["severity"] == "CRITICAL"
    assert cell["n"] == 30
    assert cell["ev"] == -0.5
    assert exit_code == 1


def test_apply_demote_suggestion_is_read_only_and_excludes_existing_registry_cells(tmp_path):
    result, exit_code = spr2.run(
        _trades("new_bad_cell", 30, -0.5, instrument="EUR_USD")
        + _trades("bb_rsi_reversion", 30, -0.5, instrument="EUR_USD"),
        _promoted("new_bad_cell", "bb_rsi_reversion"),
        now=NOW,
        report_dir=tmp_path,
        write_md=False,
        apply_demote=True,
    )

    suggestion = result["apply_demote_suggestion"]
    assert suggestion["mode"] == "read_only"
    assert ("new_bad_cell", "EUR_USD") in suggestion["missing_cells"]
    assert ("bb_rsi_reversion", "EUR_USD") not in suggestion["missing_cells"]
    assert exit_code == 1


def test_n30_positive_ev_no_alert(tmp_path):
    result, exit_code = spr2.run(
        _trades("n30_good", 30, 0.5),
        _promoted("n30_good"),
        now=NOW,
        report_dir=tmp_path,
        write_md=False,
    )

    cell = _cell(result, "n30_good")
    assert cell["severity"] == "OK"
    assert cell["n"] == 30
    assert cell["ev"] == 0.5
    assert exit_code == 0


def test_network_error_maps_to_exit_2(monkeypatch):
    def fail_fetcher(api: str, limit: int) -> list[dict]:
        raise spr2.ApiError("boom")

    monkeypatch.setattr("sys.argv", ["shadow_promote_r2_alert.py", "--no-report"])

    assert spr2.cli(fetcher=fail_fetcher) == 2


def test_empty_trades_exit_0(tmp_path):
    result, exit_code = spr2.run(
        [],
        _promoted("empty_strategy"),
        now=NOW,
        report_dir=tmp_path,
        write_md=False,
    )

    assert result["summary"]["critical_count"] == 0
    assert result["summary"]["warn_count"] == 0
    assert result["summary"]["ok_count"] == 1
    assert exit_code == 0


def test_xau_and_live_rows_are_excluded(tmp_path):
    trades = (
        _trades("critical_without_filters", 30, -10.0, instrument="XAU_USD")
        + [
            {
                "entry_type": "critical_without_filters",
                "instrument": "USD_JPY",
                "is_shadow": 0,
                "pnl_pips": -10.0,
                "created_at": NOW.isoformat(),
            }
            for _ in range(30)
        ]
    )

    result, exit_code = spr2.run(
        trades,
        _promoted("critical_without_filters"),
        now=NOW,
        report_dir=tmp_path,
        write_md=False,
    )

    only_cell = result["cells"][0]
    assert only_cell["instrument"] is None
    assert only_cell["n"] == 0
    assert only_cell["severity"] == "OK"
    assert exit_code == 0
