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


# 決定的な基準時刻。stagnation は市場オープン時間で数えるため、real now を
# 使うとテストの成否が実行する曜日に依存してしまう (月曜朝に走らせると
# 36h 前は週末の中になり発火しない)。週末と重ならない水曜正午に固定する。
WEDNESDAY_NOON = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)


def test_stagnation_fires_on_production_shaped_rows():
    stale = WEDNESDAY_NOON - timedelta(hours=aw.N_STAGNATION_HOURS + 12)
    events = aw.check_live_n_stagnation({}, [_trade(stale)], now=WEDNESDAY_NOON)
    assert [e["type"] for e in events] == ["live_n_stagnation"]
    assert events[0]["hours_since_last_trade"] >= aw.N_STAGNATION_HOURS
    assert events[0]["market_open_hours_since"] >= aw.N_STAGNATION_HOURS


def test_stagnation_silent_when_trades_are_recent():
    fresh = WEDNESDAY_NOON - timedelta(hours=1)
    assert aw.check_live_n_stagnation({}, [_trade(fresh)], now=WEDNESDAY_NOON) == []


def test_stagnation_uses_newest_row_regardless_of_order():
    trades = [
        _trade(WEDNESDAY_NOON - timedelta(hours=200)),
        _trade(WEDNESDAY_NOON - timedelta(hours=1)),
    ]
    assert aw.check_live_n_stagnation({}, trades, now=WEDNESDAY_NOON) == []


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


# ── FX weekend close: no false positive (rule:R3, 2026-08-26) ─────────
# 実時間 24h 閾値は金曜夕方の最終取引を毎週末必ず誤発火させた。
# 2026-08-28 は金曜、08-30 は日曜、08-31 は月曜。


def test_weekend_close_does_not_fire():
    """金 20:00 の最終取引を日 23:00 に評価 — 実時間 51h だが市場が開いて
    いたのは 3h (金 20-21 + 日 21-23) なので沈黙する。"""
    friday_trade = datetime(2026, 8, 28, 20, 0, tzinfo=timezone.utc)
    sunday_night = datetime(2026, 8, 30, 23, 0, tzinfo=timezone.utc)
    assert aw.check_live_n_stagnation({}, [_trade(friday_trade)], now=sunday_night) == []


def test_fires_after_weekend_once_open_hours_exceed_threshold():
    """同じ金曜の取引でも月 22:00 なら市場オープン 26h — 発火する。"""
    friday_trade = datetime(2026, 8, 28, 20, 0, tzinfo=timezone.utc)
    monday_night = datetime(2026, 8, 31, 22, 0, tzinfo=timezone.utc)
    events = aw.check_live_n_stagnation({}, [_trade(friday_trade)], now=monday_night)
    assert [e["type"] for e in events] == ["live_n_stagnation"]
    assert events[0]["market_open_hours_since"] == pytest.approx(26.0)
    assert events[0]["hours_since_last_trade"] == pytest.approx(74.0)


def test_market_open_hours_arithmetic():
    mon = datetime(2026, 8, 31, 0, 0, tzinfo=timezone.utc)
    # 丸一週間 = 168h − 週末閉場 48h
    assert aw._market_open_hours(mon, mon + timedelta(days=7)) == pytest.approx(120.0)
    # 閉場のただ中 (土 00:00 → 日 00:00) は 0h
    sat = datetime(2026, 8, 29, 0, 0, tzinfo=timezone.utc)
    assert aw._market_open_hours(sat, sat + timedelta(days=1)) == pytest.approx(0.0)
    # 週央の 24h は素通し
    tue = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
    assert aw._market_open_hours(tue, tue + timedelta(days=1)) == pytest.approx(24.0)


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


# ── DB write health: 満杯事故の直接検知 (rule:R3, 2026-08-26) ──────────
# 観測点はファイル mtime ではなく write_probe (実 INSERT の成否)。mtime は
# 再起動の checkpoint でリセットされ、ENOSPC 下でも確保済み WAL ブロック
# への再書込みで前進するため、満杯型停止で偽陰性になる (レビューで再現)。


def _probe_payload(probe) -> dict:
    return {"disk": {"used_pct": 25.0}, "write_probe": probe}


def test_write_failure_fires_immediately():
    """2026-08-21 事故の形: commit が「今」失敗している事実をそのまま報告。"""
    probe = {"ok": False, "error": "database or disk is full", "last_ok_at": "2026-08-21T18:46:00+00:00"}
    events = aw.check_db_write_health(_probe_payload(probe))
    assert [e["type"] for e in events] == ["db_write_failed"]
    assert "disk is full" in events[0]["error"]
    assert events[0]["last_ok_at"] == "2026-08-21T18:46:00+00:00"


def test_write_health_silent_when_probe_succeeds():
    assert aw.check_db_write_health(_probe_payload({"ok": True, "last_ok_at": "x"})) == []


def test_write_health_silent_when_endpoint_unreachable():
    """A failed fetch must not manufacture a false alarm (既存方針と同じ)。"""
    assert aw.check_db_write_health({}) == []


def test_missing_probe_is_recorded_not_skipped():
    """126 日 no-op の教訓: 測れない検知器は黙らず「測れない」と言う。
    ただしデプロイ直後のバージョン不一致で必ず一度は起きるため、記録は
    されるが Discord には流れない (NOTIFY_NEVER)。"""
    events = aw.check_db_write_health({"disk": {"used_pct": 25.0}})
    assert [e["type"] for e in events] == ["write_probe_missing"]
    assert aw._should_notify(events[0], WEDNESDAY_NOON) is False


# ── notification throttle (rule:R3, 2026-08-26) ──────────────────────
# cron は状態を持てないので決定的な時間バケットで通知量を抑える。
# 検知 (JSONL 記録) は毎回全件、抑制されるのは Discord 通知だけ。


def _at(hour: int, minute: int) -> datetime:
    return datetime(2026, 9, 2, hour, minute, tzinfo=timezone.utc)


def test_transient_events_always_notify():
    spike = {"type": "spread_spike", "instrument": "USD_JPY"}
    assert aw._should_notify(spike, _at(13, 30)) is True


def test_warn_notifies_only_at_six_hour_bucket_heads():
    warn = {"type": "disk_capacity", "severity": "warn"}
    assert aw._should_notify(warn, _at(12, 0)) is True
    assert aw._should_notify(warn, _at(12, 5)) is True  # cron 起動の遅延を許容
    assert aw._should_notify(warn, _at(12, 30)) is False
    assert aw._should_notify(warn, _at(13, 0)) is False
    assert aw._should_notify(warn, _at(18, 0)) is True


def test_critical_notifies_hourly():
    crit = {"type": "disk_capacity", "severity": "critical"}
    assert aw._should_notify(crit, _at(13, 0)) is True
    assert aw._should_notify(crit, _at(13, 20)) is False
    assert aw._should_notify(crit, _at(14, 10)) is True


def test_write_failure_notifies_hourly():
    ev = {"type": "db_write_failed", "error": "database or disk is full"}
    assert aw._should_notify(ev, _at(9, 0)) is True
    assert aw._should_notify(ev, _at(9, 45)) is False
