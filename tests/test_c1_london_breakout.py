import math

import pandas as pd

from tools.bt import c1_london_breakout as c1
from tools.bt import c1_validity_checks as validity


def _bars(rows):
    idx = pd.to_datetime([r[0] for r in rows], utc=True)
    return pd.DataFrame(
        {
            "Open": [r[1] for r in rows],
            "High": [r[2] for r in rows],
            "Low": [r[3] for r in rows],
            "Close": [r[4] for r in rows],
            "Volume": 100,
        },
        index=idx,
    )


def test_asian_range_uses_utc_window_and_excludes_end_bar():
    df = _bars(
        [
            ("2026-01-05 00:00", 190.0, 190.3, 189.9, 190.1),
            ("2026-01-05 06:55", 190.1, 191.2, 189.7, 190.9),
            ("2026-01-05 07:00", 190.9, 195.0, 188.0, 194.0),
        ]
    )

    rng = c1.compute_asian_range(df, pd.Timestamp("2026-01-05", tz="UTC"), 7)

    assert rng.high == 191.2
    assert rng.low == 189.7
    assert math.isclose(rng.width_pips, 150.0)


def test_close_breakout_only_enters_inside_london_open_gate():
    df = _bars(
        [
            ("2026-01-05 00:00", 190.0, 190.3, 189.9, 190.1),
            ("2026-01-05 06:55", 190.1, 191.2, 189.7, 190.9),
            ("2026-01-05 07:05", 190.9, 191.4, 191.0, 191.3),
            ("2026-01-05 08:00", 191.3, 192.0, 191.2, 191.8),
            ("2026-01-05 12:00", 191.8, 192.5, 191.7, 192.2),
        ]
    )
    asian = c1.AsianRange(high=191.2, low=189.7, width=1.5, width_pips=150.0)

    entry = c1.find_breakout_entry(
        df, pd.Timestamp("2026-01-05", tz="UTC"), asian, "close"
    )

    assert entry is not None
    assert entry.side == "LONG"
    assert entry.timestamp == pd.Timestamp("2026-01-05 07:05", tz="UTC")
    assert entry.price == 191.3


def test_high_breakout_can_enter_when_close_has_not_broken():
    df = _bars(
        [
            ("2026-01-05 07:00", 190.0, 191.25, 190.0, 191.1),
            ("2026-01-05 07:05", 191.1, 191.15, 190.8, 191.0),
        ]
    )
    asian = c1.AsianRange(high=191.2, low=189.7, width=1.5, width_pips=150.0)

    entry = c1.find_breakout_entry(
        df, pd.Timestamp("2026-01-05", tz="UTC"), asian, "high_break"
    )

    assert entry is not None
    assert entry.side == "LONG"
    assert entry.price == 191.2


def test_bonferroni_threshold_is_fixed_to_81_cells():
    assert c1.BONFERRONI_M == 81
    assert math.isclose(c1.bonferroni_alpha(), 0.05 / 81)


def test_null_bootstrap_is_deterministic_and_uses_actual_pnl_shape():
    pnls = [10.0, -4.0, 8.0, -3.0, 7.0, -2.0]

    first = validity.null_bootstrap_pf(pnls, n=50, seed=123)
    second = validity.null_bootstrap_pf(pnls, n=50, seed=123)

    assert first == second
    assert first["iterations"] == 50
    assert first["p95_pf"] >= 0


def test_validity_cli_accepts_run_specific_orphan_log(tmp_path):
    bt_path = tmp_path / "bt.json"
    out_path = tmp_path / "validity.json"
    orphan_log = ".ai/runs/example/orphan_check.log"
    bt_path.write_text(
        """
        {
          "header": {
            "data_source": "unit",
            "git_sha": "test",
            "interval": "M5",
            "limitations": ["LOCAL_CACHE_INCOMPLETE_FOR_2014_2026_REQUEST"],
            "pair": "GBP_JPY",
            "time_window": {"start": "2014-01-01", "end": "2026-04-30"}
          },
          "primary": {"trades": []},
          "scenario_verdict": {"scenario": "BLOCKED_DATA"}
        }
        """,
        encoding="utf-8",
    )

    rc = validity.main_args_for_test(
        [
            "--bt-result",
            str(bt_path),
            "--output",
            str(out_path),
            "--rsk-source",
            "none",
            "--broker-cross",
            "none",
            "--bootstrap-n",
            "1",
            "--orphan-log",
            orphan_log,
        ]
    )

    assert rc == 0
    assert f'"path": "{orphan_log}"' in out_path.read_text(encoding="utf-8")
