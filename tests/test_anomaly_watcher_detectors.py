"""Regression pins for the Tier-C anomaly detectors (rule:R3, 2026-08-26).

``check_live_n_stagnation`` was a **no-op for 126 days** (2026-04-22 →
2026-08-26): it read ``status["last_trade_time"]``, a key that no code path
in the repo ever produced, and returned ``[]`` unconditionally. The cost was
measured — the 2026-08-21 disk-full outage stopped every DB write for 5 days
and this detector, whose entire job is "no new trades", stayed silent.

These tests pin the two properties that were missing: the detector fires on
realistically shaped input, and a broken field contract is *reported* rather
than silently skipped.
"""
from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "anomaly_watcher", ROOT / "scripts" / "anomaly_watcher.py"
)
aw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aw)


def _trade(dt: datetime) -> dict:
    """Shaped like a real /api/demo/trades row (verified against production
    2026-08-26: open_time is null, entry_time carries the ISO timestamp)."""
    return {
        "open_time": None,
        "entry_time": dt.isoformat(),
        "created_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "instrument": "USD_JPY",
    }


def test_stagnation_fires_on_production_shaped_rows():
    stale = datetime.now(timezone.utc) - timedelta(hours=aw.N_STAGNATION_HOURS + 12)
    events = aw.check_live_n_stagnation({}, [_trade(stale)])
    assert [e["type"] for e in events] == ["live_n_stagnation"]
    assert events[0]["hours_since_last_trade"] >= aw.N_STAGNATION_HOURS


def test_stagnation_silent_when_trades_are_recent():
    fresh = datetime.now(timezone.utc) - timedelta(hours=1)
    assert aw.check_live_n_stagnation({}, [_trade(fresh)]) == []


def test_stagnation_uses_newest_row_regardless_of_order():
    now = datetime.now(timezone.utc)
    trades = [_trade(now - timedelta(hours=200)), _trade(now - timedelta(hours=1))]
    assert aw.check_live_n_stagnation({}, trades) == []


def test_broken_timestamp_contract_is_reported_not_skipped():
    """The original defect: an unmet field assumption produced silence. A
    detector that cannot measure must say so."""
    events = aw.check_live_n_stagnation({}, [{"instrument": "USD_JPY"}])
    assert [e["type"] for e in events] == ["stagnation_check_broken"]


def test_the_dead_field_alone_no_longer_satisfies_the_detector():
    """`last_trade_time` never existed in the API; relying on it must not be
    the path that keeps the detector quiet."""
    stale = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    events = aw.check_live_n_stagnation({"last_trade_time": stale}, [])
    assert [e["type"] for e in events] == ["stagnation_check_broken"]


# ── disk capacity ────────────────────────────────────────────────────


def _disk_payload(used_pct: float, preflight_ok: bool = True) -> dict:
    return {
        "disk": {"used_pct": used_pct, "free_bytes": 100, "total_bytes": 1000},
        "footprint": {"main_bytes": 500, "backups_total_bytes": 300},
        "backup_preflight": {"ok": preflight_ok, "need_bytes": 600, "free_bytes": 100},
        "warn_pct": 75.0,
        "critical_pct": 90.0,
    }


def test_disk_alert_silent_below_warn():
    assert aw.check_disk_capacity(_disk_payload(40.0)) == []


@pytest.mark.parametrize("pct,severity", [(80.0, "warn"), (97.0, "critical")])
def test_disk_alert_severity_ladder(pct, severity):
    events = aw.check_disk_capacity(_disk_payload(pct))
    disk_events = [e for e in events if e["type"] == "disk_capacity"]
    assert len(disk_events) == 1
    assert disk_events[0]["severity"] == severity


def test_blocked_backup_is_its_own_alert():
    events = aw.check_disk_capacity(_disk_payload(99.0, preflight_ok=False))
    assert "backup_blocked_low_disk" in [e["type"] for e in events]


def test_disk_alert_silent_when_endpoint_unreachable():
    """A failed fetch must not manufacture a false alarm."""
    assert aw.check_disk_capacity({}) == []


def test_thresholds_come_from_the_api_payload_not_local_constants():
    """Judgement must stay single-sourced with modules/disk_guard.py."""
    payload = _disk_payload(50.0)
    payload["warn_pct"] = 40.0
    events = aw.check_disk_capacity(payload)
    assert [e["type"] for e in events] == ["disk_capacity"]
