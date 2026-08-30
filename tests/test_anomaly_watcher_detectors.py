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


class TestCandidateStagnation:
    """候補行 (バー評価ごと) の鮮度検知 (rule:R3, 2026-08-27).

    埋める穴: write_probe は「書込み経路」の生死しか見ず、評価スレッドが
    死んで候補が出なくなっても ok を返す。live_n_stagnation は約定ベースで
    閾値 24h。watcher はスレッド生存を一切見ていない。
    """

    @staticmethod
    def _status(at, st="ok"):
        return {"last_candidate_row_at": at, "last_candidate_row_status": st}

    def test_fresh_candidates_are_quiet(self):
        now = datetime(2026, 8, 27, 3, 0, tzinfo=timezone.utc)
        s = self._status((now - timedelta(minutes=4)).isoformat())
        assert aw.check_candidate_stagnation(s, now=now) == []

    def test_natural_two_hour_lull_does_not_fire(self):
        """実測された自然な最大無風 (NY クローズ〜アジア early の 2.0h)
        で鳴ってはいけない — 誤発火は検知器を無視させる。"""
        now = datetime(2026, 8, 27, 0, 0, tzinfo=timezone.utc)  # 木
        s = self._status((now - timedelta(hours=2)).isoformat())
        assert aw.check_candidate_stagnation(s, now=now) == []

    def test_fires_past_threshold_on_open_market(self):
        now = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)  # 木 = 開場
        s = self._status((now - timedelta(hours=7)).isoformat())
        ev = aw.check_candidate_stagnation(s, now=now)
        assert len(ev) == 1
        assert ev[0]["type"] == "candidate_stagnation"
        assert ev[0]["market_open_hours_since"] >= aw.CANDIDATE_STAGNATION_HOURS

    def test_weekend_close_does_not_false_fire(self):
        """金 21:00 UTC 閉場 → 日曜まで候補ゼロは正常。実時間で数えると
        毎週末必ず誤発火する (live_n_stagnation で踏んだ罠と同型)。"""
        friday_close = datetime(2026, 8, 28, 20, 30, tzinfo=timezone.utc)
        saturday = datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc)
        assert friday_close.weekday() == 4 and saturday.weekday() == 5
        s = self._status(friday_close.isoformat())
        assert aw.check_candidate_stagnation(s, now=saturday) == []

    def test_missing_field_is_recorded_but_never_notified(self):
        """契約欠落は黙って skip しない。ただしデプロイ直後の version skew
        で必ず起きるので Discord には流さない。"""
        ev = aw.check_candidate_stagnation({"running": True}, now=None)
        assert len(ev) == 1
        assert ev[0]["type"] == "candidate_freshness_missing"
        assert "candidate_freshness_missing" in aw.NOTIFY_NEVER

    def test_error_status_is_surfaced(self):
        s = {"last_candidate_row_status": "error", "row_freshness_error": "disk I/O"}
        ev = aw.check_candidate_stagnation(s, now=None)
        assert ev and ev[0]["type"] == "candidate_freshness_error"

    def test_no_rows_is_not_an_anomaly(self):
        """初期状態 (テーブル空) を異常にすると本物が埋もれる。"""
        assert aw.check_candidate_stagnation(
            {"last_candidate_row_status": "no_rows"}, now=None
        ) == []

    def test_unparseable_timestamp_is_surfaced_not_swallowed(self):
        s = self._status("not-a-date")
        ev = aw.check_candidate_stagnation(s, now=None)
        assert ev and ev[0]["type"] == "candidate_freshness_error"

    def test_empty_status_is_silent(self):
        """fetch 失敗 ({}) で false alarm を作らない (既存方針と一致)。"""
        assert aw.check_candidate_stagnation({}, now=None) == []

    def test_event_line_renders(self):
        now = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
        s = self._status((now - timedelta(hours=7)).isoformat())
        ev = aw.check_candidate_stagnation(s, now=now)
        line = aw._event_line(ev[0])
        assert "candidate_stagnation" in line
        # 汎用 fallback (json ダンプ) に落ちていないこと
        assert not line.startswith("- candidate_stagnation: {")


class TestEngineTickStall:
    """エンジン本体 (main loop) の停止検知 — rule:R3, 2026-08-28.

    2026-08-27 に「cron は状態を持てない」として見送られた項目。差分を
    サーバ側で取ることで解決した。既存の ``candidate_stagnation`` は HTF
    Hard Block 後の行を数えるため benign な全ブロックと区別できないが、
    tick 前進はゲートにも市場の開閉にも依存しないので、発火 = 異常。
    """

    def _status(self, **kw) -> dict:
        base = {
            "running": True,
            "engine_tick_status": "ok",
            "engine_tick_age_sec": 18.0,
            "engine_tick_running_modes": 24,
            "engine_tick_stalest_mode": "daytrade_1h",
            "engine_tick_stalest_age_sec": 55.0,
        }
        base.update(kw)
        return base

    def test_healthy_engine_is_silent(self):
        assert aw.check_engine_tick_stall(self._status()) == []

    def test_production_cadence_is_far_below_threshold(self):
        """本番実測 (2026-08-28): engine レベルの前進間隔は 20 秒未満、
        モード別 max でも 81.2 秒。閾値 15 分はそのどちらからも桁で遠い。"""
        assert aw.check_engine_tick_stall(self._status(engine_tick_age_sec=81.2)) == []

    def test_stalled_engine_fires(self):
        ev = aw.check_engine_tick_stall(self._status(engine_tick_age_sec=20 * 60))
        assert len(ev) == 1
        assert ev[0]["type"] == "engine_tick_stall"
        assert ev[0]["minutes_since_last_tick"] == 20.0
        assert ev[0]["stalest_mode"] == "daytrade_1h"

    def test_threshold_boundary_is_inclusive(self):
        below = aw.check_engine_tick_stall(
            self._status(engine_tick_age_sec=aw.ENGINE_TICK_STALL_MINUTES * 60 - 1)
        )
        at = aw.check_engine_tick_stall(
            self._status(engine_tick_age_sec=aw.ENGINE_TICK_STALL_MINUTES * 60)
        )
        assert below == []
        assert len(at) == 1

    def test_deploy_ramp_does_not_false_alarm(self):
        """PR #199 実測: デプロイは無 tick 59.5s + ramp 2m39s ≈ 3.6 分。
        閾値 15 分はその約 4 倍で、通常のデプロイでは鳴らない。"""
        assert aw.check_engine_tick_stall(self._status(engine_tick_age_sec=3.6 * 60)) == []

    def test_never_ticked_is_its_own_event(self):
        """起動したが一度も tick していない = 起動失敗。停止とは原因が違う
        ので type を分ける (no_rows と error を折り畳むなの同型)。"""
        ev = aw.check_engine_tick_stall(
            self._status(engine_tick_status="never_ticked", engine_tick_age_sec=30 * 60)
        )
        assert len(ev) == 1
        assert ev[0]["type"] == "engine_tick_never"

    def test_never_ticked_is_silent_during_startup(self):
        ev = aw.check_engine_tick_stall(
            self._status(engine_tick_status="never_ticked", engine_tick_age_sec=60.0)
        )
        assert ev == []

    def test_user_stopped_engine_is_not_an_outage(self):
        """全モード停止中は「止まっている」ではなく「止められている」。
        資格 (eligible) と実状態 (effective) を混同しない。"""
        ev = aw.check_engine_tick_stall(
            {"running": False, "engine_tick_status": "not_running",
             "engine_tick_age_sec": None, "engine_tick_running_modes": 0}
        )
        assert ev == []

    def test_weekend_is_not_excluded(self):
        """tick は市場が閉まっていても前進する。ここで市場オープン時間に
        換算すると、本物の週末停止を毎回見逃す (live_n_stagnation とは
        estimand が違う)。"""
        saturday = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
        ev = aw.check_engine_tick_stall(
            self._status(engine_tick_age_sec=60 * 60), now=saturday
        )
        assert len(ev) == 1
        assert ev[0]["type"] == "engine_tick_stall"

    def test_missing_field_is_recorded_not_skipped(self):
        """web が旧版でも黙って skip しない — 沈黙が 126 日 no-op の原因。"""
        ev = aw.check_engine_tick_stall({"running": True})
        assert len(ev) == 1
        assert ev[0]["type"] == "engine_tick_missing"

    def test_missing_field_is_never_notified(self):
        """デプロイ直後のバージョン不一致で必ず一度は起きるので Discord に
        は流さない (write_probe_missing と同じ扱い)。"""
        assert "engine_tick_missing" in aw.NOTIFY_NEVER
        now = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
        assert aw._should_notify({"type": "engine_tick_missing"}, now) is False

    def test_unparseable_age_is_reported(self):
        ev = aw.check_engine_tick_stall(self._status(engine_tick_age_sec="soon"))
        assert len(ev) == 1
        assert ev[0]["type"] == "engine_tick_missing"

    def test_none_age_with_ok_status_is_reported(self):
        ev = aw.check_engine_tick_stall(self._status(engine_tick_age_sec=None))
        assert len(ev) == 1
        assert ev[0]["type"] == "engine_tick_missing"

    def test_unreachable_api_is_silent(self):
        assert aw.check_engine_tick_stall({}) == []

    def test_stall_notifies_hourly(self):
        assert aw.NOTIFY_EVERY_HOURS["engine_tick_stall"] == 1
        assert aw.NOTIFY_EVERY_HOURS["engine_tick_never"] == 1

    def test_alert_line_is_actionable(self):
        ev = aw.check_engine_tick_stall(self._status(engine_tick_age_sec=20 * 60))
        line = aw._event_line(ev[0])
        assert "エンジン停止" in line
        assert "benign な説明は無い" in line
        assert not line.startswith("- engine_tick_stall: {")


    def test_detector_is_wired_into_main(self):
        """**配線 pin**: 検知器を書いても main() から呼ばれなければ意味が
        無い。C1 テーブルが 4 ヶ月 write-only だったのと同型の失敗を、
        検知器側でも防ぐ (counterfactual CF6 で実際に素通りしたため追加)。"""
        from pathlib import Path

        src = (Path(aw.__file__).read_text(encoding="utf-8")
               if getattr(aw, "__file__", None) else
               (ROOT / "scripts" / "anomaly_watcher.py").read_text(encoding="utf-8"))
        assert "all_events.extend(check_engine_tick_stall(status" in src

    def test_never_ticked_without_age_alerts_instead_of_silent(self):
        """**最悪ケースを沈黙させない** (rule:R3, 2026-08-28 実測で発見)。

        「モードは running なのに tick ゼロ」= この検知器が存在する理由その
        もの。初版はこの payload を `engine_tick_missing` (NOTIFY_NEVER =
        web 旧版と同じ袋) に分類して完全に沈黙していた。契約が破れた場合も
        **鳴らす側に倒す**。
        """
        ev = aw.check_engine_tick_stall(
            {"running": True, "engine_tick_status": "never_ticked",
             "engine_tick_age_sec": None, "engine_tick_running_modes": 24}
        )
        assert len(ev) == 1
        assert ev[0]["type"] == "engine_tick_never"
        assert ev[0]["type"] not in aw.NOTIFY_NEVER
        assert aw.NOTIFY_EVERY_HOURS["engine_tick_never"] == 1

    def test_ok_status_without_age_is_still_version_skew(self):
        """逆に status=ok で age だけ欠けるのは契約破れ = 記録のみ。"""
        ev = aw.check_engine_tick_stall(
            {"running": True, "engine_tick_status": "ok",
             "engine_tick_age_sec": None}
        )
        assert ev[0]["type"] == "engine_tick_missing"


# ── API 到達不能 (rule:R3, 2026-08-30) ────────────────────────────────
#
# 実測が動機: 2026-08-29T23:31Z のデプロイ再起動で 4 エンドポイント全てが
# 502 を返した run で、8 検知器のうち 7 個が完全に沈黙し、残る 1 個が
# 「/api/demo/trades に読める時刻フィールドが無い」という**事実と異なる
# 診断**を上げた (真因は 502)。つまり本番が死んでいる間、監視スタックは
# 死んでいることを報告できなかった。


def _ok(path: str, payload: dict | None = None) -> "aw.FetchOutcome":
    return aw.FetchOutcome(path, True, payload or {}, "")


def _fail(path: str, reason: str = "HTTPError: 502 Server Error") -> "aw.FetchOutcome":
    return aw.FetchOutcome(path, False, {}, reason)


class TestApiReachability:
    def test_healthy_fetches_are_silent(self):
        outcomes = {p: _ok(p) for p in aw.WATCHED_PATHS}
        assert aw.check_api_reachability(outcomes) == []

    def test_total_outage_fires_with_the_real_reason(self):
        """502 は 502 として報告される。旧経路は 502 を「契約破綻」と誤診した。"""
        outcomes = {p: _fail(p) for p in aw.WATCHED_PATHS}
        ev = aw.check_api_reachability(outcomes, attempts=4, waited_sec=210.0)
        assert len(ev) == 1
        assert ev[0]["type"] == "api_unreachable"
        assert ev[0]["n_failed"] == ev[0]["n_watched"] == len(aw.WATCHED_PATHS)
        assert "502" in ev[0]["reasons"]["/api/demo/status"]
        # ramp を跨いだのか 1 回で諦めたのかが読み手に見えること
        assert ev[0]["attempts"] == 4
        assert ev[0]["waited_sec"] == 210.0

    def test_partial_failure_is_a_different_event(self):
        """1 本だけの失敗は「サービスの死」ではない。畳むと切り分けが消える。"""
        outcomes = {p: _ok(p) for p in aw.WATCHED_PATHS}
        outcomes["/api/admin/disk_status"] = _fail("/api/admin/disk_status")
        ev = aw.check_api_reachability(outcomes)
        assert ev[0]["type"] == "api_endpoint_failed"
        assert ev[0]["failed"] == ["/api/admin/disk_status"]

    def test_outage_is_notified_not_silenced(self):
        """NOTIFY_NEVER に落ちていたら検知器を書いた意味が無い。"""
        assert "api_unreachable" not in aw.NOTIFY_NEVER
        assert aw.NOTIFY_EVERY_HOURS["api_unreachable"] == 1
        assert aw.NOTIFY_EVERY_HOURS["api_endpoint_failed"] == 6

    @pytest.mark.parametrize(
        "outcomes_fn, must_contain",
        [
            (lambda: {p: _fail(p) for p in aw.WATCHED_PATHS},
             "他の全検知器は盲目である"),
            (lambda: {**{p: _ok(p) for p in aw.WATCHED_PATHS},
                      "/api/oanda/status": _fail("/api/oanda/status")},
             "エンドポイント固有の異常"),
        ],
    )
    def test_both_event_types_render_a_human_line(self, outcomes_fn, must_contain):
        """汎用 fallback (`- {type}: {json 抜粋}`) に落ちていないこと。

        初版の assertion は「長さ > 60」「'json.dumps' を含まない」だった
        が、fallback 行もその両方を満たすので **counterfactual が素通り
        した**。専用行にしか現れない文言で pin し直している。
        """
        line = aw._event_line(aw.check_api_reachability(outcomes_fn())[0])
        assert line.startswith("- ")
        assert must_contain in line


class TestFetchOutcomeSeparation:
    def test_fetch_failure_is_not_reported_as_a_broken_contract(self):
        """2026-08-29T23:31Z の誤診そのもの。fetch 失敗なら黙る
        (api_unreachable が真の理由で報告するため)。"""
        assert aw.check_live_n_stagnation({}, [], now=WEDNESDAY_NOON,
                                          trades_ok=False) == []

    def test_real_contract_break_still_fires(self):
        """取得に成功したのに時刻が読めない = 本物の契約破綻。沈黙させない。"""
        ev = aw.check_live_n_stagnation(
            {}, [{"instrument": "USD_JPY"}], now=WEDNESDAY_NOON, trades_ok=True
        )
        assert ev[0]["type"] == "stagnation_check_broken"
        assert "no parseable timestamp field" in ev[0]["detail"]

    def test_zero_rows_says_zero_rows(self):
        """「0 行だった」と「行はあるが時刻が読めない」を同じ文言に畳むと、
        次に読む人が存在しない契約破綻を追いかけることになる。"""
        ev = aw.check_live_n_stagnation({}, [], now=WEDNESDAY_NOON, trades_ok=True)
        assert ev[0]["detail"] == "/api/demo/trades returned 0 rows"

    def test_default_stays_backwards_compatible(self):
        """trades_ok の既定は True — 既存の呼び出しと同じ意味であること。"""
        ev = aw.check_live_n_stagnation({}, [{"instrument": "USD_JPY"}])
        assert ev and ev[0]["type"] == "stagnation_check_broken"


class TestFetchAllRetry:
    """全滅時のみ ramp (実測 3.6 分, PR #199) を跨いで再試行する。"""

    def test_success_does_not_retry_or_sleep(self):
        slept: list[float] = []
        outcomes, attempts, waited = fetch_all_probe(
            lambda p: _ok(p), slept
        )
        assert attempts == 1 and waited == 0.0 and slept == []
        assert all(o.ok for o in outcomes.values())

    def test_partial_failure_does_not_retry(self):
        """ramp では 4 本とも落ちる。1 本だけの失敗を待っても意味が無い。"""
        slept: list[float] = []
        outcomes, attempts, _ = fetch_all_probe(
            lambda p: _fail(p) if "disk" in p else _ok(p), slept
        )
        assert attempts == 1 and slept == []

    def test_total_failure_retries_across_the_ramp(self):
        slept: list[float] = []
        _, attempts, waited = fetch_all_probe(lambda p: _fail(p), slept)
        assert attempts == 1 + len(aw.API_RETRY_BACKOFF_SEC)
        assert slept == list(aw.API_RETRY_BACKOFF_SEC)
        assert waited == float(sum(aw.API_RETRY_BACKOFF_SEC))

    def test_recovery_mid_ramp_stops_early(self):
        """デプロイ blip は途中で回復する = 誤って api_unreachable を上げない。"""
        slept: list[float] = []
        calls = {"n": 0}

        def flaky(path: str):
            calls["n"] += 1
            # 1 巡目 (4 本) は全滅、2 巡目から回復
            return _fail(path) if calls["n"] <= len(aw.WATCHED_PATHS) else _ok(path)

        outcomes, attempts, _ = fetch_all_probe(flaky, slept)
        assert attempts == 2
        assert aw.check_api_reachability(outcomes, attempts) == []

    def test_retry_budget_fits_inside_the_cron_interval(self):
        """待機総和が cron 間隔を超えると run が重なる。"""
        assert sum(aw.API_RETRY_BACKOFF_SEC) < aw.CRON_INTERVAL_MIN * 60


def fetch_all_probe(fetcher, slept: list):
    return aw.fetch_all(fetcher=fetcher, sleeper=slept.append)


class TestMainWiring:
    """検知器を書いても main() から呼ばれなければ、全テスト green のまま無音。

    PR #208 でこの型を実際に踏んでいる (配線削除の counterfactual が初回に
    素通りした)。pin は **main() 本体にスコープを絞る** — ファイル全体への
    文字列一致は、同じ字面がコメントや別関数にあるだけで通ってしまう
    (PR #209 で同型の過剰結合を是正済み)。
    """

    @staticmethod
    def _main_source() -> str:
        import inspect

        return inspect.getsource(aw.main)

    def test_reachability_check_is_called_from_main(self):
        assert "check_api_reachability(" in self._main_source()

    def test_stagnation_is_told_whether_the_fetch_succeeded(self):
        """trades_ok を渡さないと既定 True に戻り、502 の誤診が復活する。"""
        assert "trades_ok=" in self._main_source()

    def test_main_fetches_through_the_retrying_path(self):
        src = self._main_source()
        assert "fetch_all(" in src
        # 生の fetch_json に戻すと outcome (ok/理由) が {} に潰れる
        assert "fetch_json(" not in src

    def test_every_watched_path_is_consumed(self):
        """WATCHED_PATHS と main の読み出し先がずれると、監視しているつもりの
        エンドポイントが誰にも使われないまま残る。"""
        src = self._main_source()
        for path in aw.WATCHED_PATHS:
            assert f'"{path}"' in src, path


class TestFetchOutcomeBoundary:
    """ok/payload の分離が**実際に生まれる場所**を pin する.

    上の検知器テストは ``_fail()`` で手組みした outcome を使うので、
    ``fetch_outcome`` 自身が失敗を握り潰しても素通りする — 実際に
    counterfactual (失敗を ok=True に潰す) が初回に 69 passed で通過した。
    PR #208 と同じ「検知器を書いても呼ばれなければ無音」の境界版。
    """

    class _Resp:
        def __init__(self, exc=None, payload=None):
            self._exc = exc
            self._payload = payload or {}

        def raise_for_status(self):
            if self._exc:
                raise self._exc

        def json(self):
            return self._payload

    def _patched(self, monkeypatch, resp):
        monkeypatch.setattr(aw.requests, "get", lambda *a, **k: resp)
        return aw.fetch_outcome("/api/demo/status")

    def test_http_error_is_not_ok_and_keeps_the_reason(self, monkeypatch):
        import requests as _rq

        out = self._patched(
            monkeypatch,
            self._Resp(exc=_rq.HTTPError("502 Server Error: Bad Gateway")),
        )
        assert out.ok is False
        assert out.payload == {}
        assert "502" in out.reason

    def test_transport_error_is_not_ok(self, monkeypatch):
        import requests as _rq

        def boom(*a, **k):
            raise _rq.ConnectionError("connection reset by peer")

        monkeypatch.setattr(aw.requests, "get", boom)
        out = aw.fetch_outcome("/api/demo/status")
        assert out.ok is False
        assert "ConnectionError" in out.reason

    def test_success_carries_the_payload(self, monkeypatch):
        out = self._patched(monkeypatch, self._Resp(payload={"running": True}))
        assert out.ok is True
        assert out.payload == {"running": True}
        assert out.reason == ""

    def test_legacy_wrapper_still_returns_a_plain_dict(self, monkeypatch):
        """fetch_json の後方互換。失敗時は従来どおり {} だが、新規経路は
        fetch_outcome を使う (main の pin が それを強制している)。"""
        import requests as _rq

        monkeypatch.setattr(
            aw.requests, "get", lambda *a, **k: self._Resp(exc=_rq.HTTPError("500"))
        )
        assert aw.fetch_json("/api/demo/status") == {}


class TestIncidentReplay20260829:
    """2026-08-29T23:31Z の実インシデントをそのまま再生する.

    Render ログの実測: デプロイ再起動中に 4 エンドポイント全てが 502 を返し、
    watcher は ``stagnation_check_broken``「no parseable timestamp field in
    /api/demo/trades」1 件だけを出した。**真因は 502 であってペイロード契約
    ではない** — 誤診であり、しかも「本番が落ちている」という肝心の事実は
    どの検知器も報告しなかった。
    """

    def test_total_502_now_reports_the_outage_not_a_fake_contract_break(
        self, monkeypatch
    ):
        seen: list[dict] = []
        monkeypatch.setattr(aw, "fetch_outcome",
                            lambda p, timeout=15: _fail(p, "HTTPError: 502 Server Error"))
        monkeypatch.setattr(aw.time, "sleep", lambda *_: None)
        monkeypatch.setattr(aw, "save_events", lambda evs: seen.extend(evs) or "(x)")
        monkeypatch.setattr(aw, "notify_discord", lambda evs, now=None: None)
        monkeypatch.setattr(aw.sys, "argv", ["anomaly_watcher.py"])

        assert aw.main() == 0

        types = [e["type"] for e in seen]
        assert "api_unreachable" in types, "本番の死が報告されていない"
        assert "stagnation_check_broken" not in types, "502 を契約破綻と誤診している"
        # ramp を跨ぐまで粘ったことが記録に残る
        outage = next(e for e in seen if e["type"] == "api_unreachable")
        assert outage["attempts"] == 1 + len(aw.API_RETRY_BACKOFF_SEC)

    def test_healthy_production_stays_quiet(self, monkeypatch):
        """健全時に api_unreachable が出るなら、この検知器は使い物にならない。"""
        seen: list[dict] = []
        payloads = {
            "/api/demo/trades?limit=500": {
                "trades": [_trade(WEDNESDAY_NOON - timedelta(hours=1))]
            },
        }
        monkeypatch.setattr(
            aw, "fetch_outcome",
            lambda p, timeout=15: _ok(p, payloads.get(p, {})),
        )
        monkeypatch.setattr(aw, "save_events", lambda evs: seen.extend(evs) or "(x)")
        monkeypatch.setattr(aw, "notify_discord", lambda evs, now=None: None)
        monkeypatch.setattr(aw.sys, "argv", ["anomaly_watcher.py"])

        assert aw.main() == 0
        assert [e["type"] for e in seen if e["type"].startswith("api_")] == []
