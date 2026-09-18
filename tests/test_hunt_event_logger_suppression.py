"""Pins for hunt_event_logger write suppression (2026-09-18).

`knowledge-base/raw/hunt_events/*.jsonl` is an observation dataset that
tools/sr_audit.py counts into N. Synthetic rows written by the test suite
corrupt that N, and the documented post-hoc signature (integer ADX and
atr_price == 0.001) only catches the subset of fixtures that use round
numbers — so the write itself must not happen under pytest.
"""
import json
import os

import pytest

from modules import hunt_event_logger as hel


EVENT = dict(
    strategy="sr_anti_hunt_bounce",
    instrument="USD_JPY",
    direction="BUY",
    entry_price=153.50,
    sl=153.30,
    tp=154.20,
    level=153.42,
    side="support",
    atr_price=0.12,
    extra={"adx": 20.0},
)


def test_suppressed_by_default_under_pytest():
    """The whole point: a plain call from inside the suite writes nothing."""
    assert hel.writes_suppressed() is True
    assert hel.log_hunt_event(**EVENT) is False


def test_real_log_dir_untouched_by_a_suppressed_call(monkeypatch):
    before = sorted(p.name for p in hel._LOG_DIR.glob("*.jsonl")) if hel._LOG_DIR.exists() else []
    hel.log_hunt_event(**EVENT)
    after = sorted(p.name for p in hel._LOG_DIR.glob("*.jsonl")) if hel._LOG_DIR.exists() else []
    assert before == after


@pytest.mark.parametrize(
    "mode,expected",
    [("on", False), ("off", True), ("auto", True), ("ON", False), (" off ", True)],
)
def test_mode_env_overrides(monkeypatch, mode, expected):
    monkeypatch.setenv(hel.MODE_ENV, mode)
    assert hel.writes_suppressed() is expected


def test_mode_on_writes_to_overridden_dir(monkeypatch, tmp_path):
    """mode=on + dir override is how the logger itself stays testable."""
    monkeypatch.setenv(hel.MODE_ENV, "on")
    monkeypatch.setenv(hel.DIR_ENV, str(tmp_path))
    assert hel.log_hunt_event(**EVENT) is True
    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    rows = [json.loads(ln) for ln in files[0].read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["strategy"] == "sr_anti_hunt_bounce"
    assert rows[0]["instrument"] == "USD_JPY"
    assert rows[0]["atr_pips"] == 12.0           # 0.12 / 0.01
    assert rows[0]["reversal"] is None
    assert rows[0]["adx"] == 20.0                # extra merged


def test_log_dir_override_is_read_per_call(monkeypatch, tmp_path):
    monkeypatch.delenv(hel.DIR_ENV, raising=False)
    assert hel.log_dir() == hel._LOG_DIR
    monkeypatch.setenv(hel.DIR_ENV, str(tmp_path))
    assert hel.log_dir() == tmp_path


def test_failure_still_never_raises(monkeypatch, tmp_path):
    monkeypatch.setenv(hel.MODE_ENV, "on")
    # point the log dir at a path that cannot be created (a file, not a dir)
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setenv(hel.DIR_ENV, str(blocker / "nested"))
    assert hel.log_hunt_event(**EVENT) is False


def test_strategy_call_sites_go_through_the_guard(monkeypatch, tmp_path):
    """sr_anti_hunt_bounce / sr_liquidity_grab must not bypass the logger."""
    import pathlib
    for mod in ("strategies/daytrade/sr_anti_hunt_bounce.py",
                "strategies/daytrade/sr_liquidity_grab.py"):
        src = pathlib.Path(mod).read_text(encoding="utf-8")
        assert "from modules.hunt_event_logger import log_hunt_event" in src
        assert "hunt_events" not in src, f"{mod} writes the dataset directly"
