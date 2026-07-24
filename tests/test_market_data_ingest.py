"""R3 market-data ingest — offline/deterministic tests (network なし)。

対象: modules/market_data_ingest.py (2026-07-18, rule:R3 データ基盤)
  (a) FF event parse (UTC 正規化 / 必須キー / naive date 拒否)
  (b) upsert: insert → 発表前 revision 反映 → 発表後 forecast 凍結
  (c) actual reconcile (翌期 previous 逆引き — NULL のみ・過去のみ・冪等)
  (d) feed snapshot content dedup
  (e) CME bars: 形成中 bar 除外 / UNIQUE dedup
  (f) worker: job due 管理 / 失敗カウント fail-loud / health 記録
  (g) self-heal: ensure_running の条件 (positioning 準拠)
  (h) 検証 API 契約 (/api/marketdata/status, /api/marketdata/export)
  (i) tools/ff_calendar_import.py の合流経路 (来歴タグ / 非上書き)
"""
import json
import sqlite3

import pytest

from modules.market_data_ingest import (
    DEFAULT_CME_SYMBOLS,
    JOB_CME,
    JOB_FF,
    MIN_CME_POLL_SEC,
    MIN_FF_POLL_SEC,
    MarketDataIngestWorker,
    THREAD_NAME,
    db_health,
    db_market_stats,
    ensure_market_data_schema,
    ensure_worker_running,
    export_cme_bars,
    export_ff_events,
    export_health_log,
    feed_content_key,
    filter_closed_bars,
    parse_ff_event,
    reconcile_actuals,
    save_bars,
    save_feed_snapshot,
    start_market_data_ingest,
    upsert_ff_event,
)
import modules.market_data_ingest as mdi

NOW = "2026-07-18T12:00:00Z"
PAST = "2026-07-18T08:30:00Z"
FUTURE = "2026-07-20T08:30:00Z"


@pytest.fixture
def db_path(tmp_path):
    p = str(tmp_path / "test_market.db")
    ensure_market_data_schema(p)
    return p


@pytest.fixture(autouse=True)
def _reset_singleton(monkeypatch):
    monkeypatch.setattr(mdi, "_worker", None)


def make_ff_event(**over):
    ev = {
        "title": "CPI y/y",
        "country": "USD",
        "date": "2026-07-15T08:30:00-04:00",
        "impact": "High",
        "forecast": "2.5%",
        "previous": "2.4%",
    }
    ev.update(over)
    return ev


def make_worker(db_path, ff_events=None, bars=None, **kw):
    """fake fetcher 注入済み worker (thread は起動しない)。"""
    ff_events = [] if ff_events is None else ff_events
    bars = {} if bars is None else bars

    def ff_fetch():
        return True, {"events": ff_events}

    def bars_fetch(symbol):
        if isinstance(bars.get(symbol), Exception):
            raise bars[symbol]
        return bars.get(symbol, [])

    kw.setdefault("symbols", ["6E=F"])
    return MarketDataIngestWorker(db_path, ff_fetch=ff_fetch,
                                  bars_fetch=bars_fetch, **kw)


# ── (a) parse ────────────────────────────────────────────────────────

def test_parse_ff_event_utc_normalization():
    parsed = parse_ff_event(make_ff_event())
    # -04:00 → UTC
    assert parsed["event_time_utc"] == "2026-07-15T12:30:00Z"
    assert parsed["country"] == "USD"
    assert parsed["title"] == "CPI y/y"
    assert parsed["forecast"] == "2.5%"


def test_parse_ff_event_missing_key_raises():
    for key in ("title", "country", "date"):
        ev = make_ff_event()
        ev[key] = ""
        with pytest.raises(ValueError):
            parse_ff_event(ev)
    with pytest.raises(ValueError):
        parse_ff_event("not a dict")


def test_parse_ff_event_naive_date_raises():
    with pytest.raises(ValueError):
        parse_ff_event(make_ff_event(date="2026-07-15T08:30:00"))


def test_parse_ff_event_z_suffix_accepted():
    parsed = parse_ff_event(make_ff_event(date="2026-07-15T12:30:00Z"))
    assert parsed["event_time_utc"] == "2026-07-15T12:30:00Z"


def test_parse_ff_event_empty_optional_fields():
    parsed = parse_ff_event(make_ff_event(forecast=None, previous="",
                                          impact="Holiday"))
    assert parsed["forecast"] == ""
    assert parsed["previous"] == ""


# ── (b) upsert + forecast 凍結 ──────────────────────────────────────

def test_upsert_insert_revise_freeze(db_path):
    conn = sqlite3.connect(db_path)
    try:
        future_ev = parse_ff_event(make_ff_event(date=FUTURE))
        assert upsert_ff_event(conn, future_ev, NOW) == "inserted"
        # 発表前: forecast 改定は反映される
        revised = dict(future_ev, forecast="2.7%")
        assert upsert_ff_event(conn, revised, NOW) == "revised"
        row = conn.execute("SELECT forecast FROM ff_calendar_events"
                           " WHERE event_time_utc = ?",
                           (future_ev["event_time_utc"],)).fetchone()
        assert row[0] == "2.7%"
        # 発表後 (event_time < now): forecast は凍結される
        past_ev = parse_ff_event(make_ff_event(date=PAST))
        assert upsert_ff_event(conn, past_ev, NOW) == "inserted"
        tampered = dict(past_ev, forecast="9.9%")
        assert upsert_ff_event(conn, tampered, NOW) == "seen"
        row = conn.execute("SELECT forecast FROM ff_calendar_events"
                           " WHERE event_time_utc = ?",
                           (past_ev["event_time_utc"],)).fetchone()
        assert row[0] == "2.5%"  # 事後改変は反映されない
    finally:
        conn.close()


def test_upsert_unchanged_updates_last_seen_only(db_path):
    conn = sqlite3.connect(db_path)
    try:
        ev = parse_ff_event(make_ff_event(date=FUTURE))
        upsert_ff_event(conn, ev, "2026-07-18T00:00:00Z")
        assert upsert_ff_event(conn, ev, NOW) == "seen"
        first, last = conn.execute(
            "SELECT first_seen_at, last_seen_at FROM ff_calendar_events"
        ).fetchone()
        assert first == "2026-07-18T00:00:00Z"
        assert last == NOW
    finally:
        conn.close()


# ── (c) reconcile (翌期 previous 逆引き) ────────────────────────────

def test_reconcile_fills_predecessor_from_next_previous(db_path):
    conn = sqlite3.connect(db_path)
    try:
        # 6月分 (発表済み、actual 未取得) → 7月分の previous=2.4% が actual になる
        jun = parse_ff_event(make_ff_event(date="2026-06-15T08:30:00-04:00",
                                           forecast="2.3%", previous="2.2%"))
        jul = parse_ff_event(make_ff_event(previous="2.4%"))
        upsert_ff_event(conn, jun, NOW)
        upsert_ff_event(conn, jul, NOW)
        assert reconcile_actuals(conn, NOW) == 1
        actual, source = conn.execute(
            "SELECT actual, actual_source FROM ff_calendar_events"
            " WHERE event_time_utc = ?",
            (jun["event_time_utc"],)).fetchone()
        assert actual == "2.4%"
        assert source == "next_previous"
        # 冪等: 2 回目は何も埋めない
        assert reconcile_actuals(conn, NOW) == 0
    finally:
        conn.close()


def test_reconcile_skips_future_empty_and_existing(db_path):
    conn = sqlite3.connect(db_path)
    try:
        # (1) 未発表の行は埋めない
        fut = parse_ff_event(make_ff_event(date=FUTURE))
        nxt = parse_ff_event(make_ff_event(date="2026-08-20T08:30:00Z",
                                           previous="3.0%"))
        upsert_ff_event(conn, fut, NOW)
        upsert_ff_event(conn, nxt, NOW)
        assert reconcile_actuals(conn, NOW) == 0
        # (2) 次回行の previous が空なら埋めない
        e1 = parse_ff_event(make_ff_event(title="GDP q/q",
                                          date="2026-06-01T08:30:00Z"))
        e2 = parse_ff_event(make_ff_event(title="GDP q/q",
                                          date="2026-07-01T08:30:00Z",
                                          previous=""))
        upsert_ff_event(conn, e1, NOW)
        upsert_ff_event(conn, e2, NOW)
        assert reconcile_actuals(conn, NOW) == 0
        # (3) import 済み actual は上書きしない
        conn.execute("UPDATE ff_calendar_events SET actual = '1.1%',"
                     " actual_source = 'import:test'"
                     " WHERE title = 'GDP q/q' AND event_time_utc"
                     " = '2026-06-01T08:30:00Z'")
        e2b = dict(e2, previous="9.9%")
        # 発表前なので revision として反映される
        upsert_ff_event(conn, e2b, NOW)
        reconcile_actuals(conn, NOW)
        actual, source = conn.execute(
            "SELECT actual, actual_source FROM ff_calendar_events"
            " WHERE title = 'GDP q/q' AND event_time_utc"
            " = '2026-06-01T08:30:00Z'").fetchone()
        assert (actual, source) == ("1.1%", "import:test")
    finally:
        conn.close()


def test_reconcile_series_isolation(db_path):
    """別系列 (country/title 違い) の previous を混線させない。"""
    conn = sqlite3.connect(db_path)
    try:
        a = parse_ff_event(make_ff_event(title="CPI y/y", country="USD",
                                         date="2026-06-15T08:30:00Z"))
        b = parse_ff_event(make_ff_event(title="CPI y/y", country="GBP",
                                         date="2026-07-15T06:00:00Z",
                                         previous="8.8%"))
        upsert_ff_event(conn, a, NOW)
        upsert_ff_event(conn, b, NOW)
        assert reconcile_actuals(conn, NOW) == 0
    finally:
        conn.close()


# ── (d) feed snapshot dedup ──────────────────────────────────────────

def test_feed_snapshot_content_dedup(db_path):
    conn = sqlite3.connect(db_path)
    try:
        events = [make_ff_event()]
        assert save_feed_snapshot(conn, events, NOW) is True
        assert save_feed_snapshot(conn, events, "2026-07-18T13:00:00Z") is False
        changed = [make_ff_event(forecast="2.6%")]
        assert save_feed_snapshot(conn, changed, "2026-07-18T14:00:00Z") is True
        n = conn.execute("SELECT COUNT(*) FROM ff_feed_snapshots").fetchone()[0]
        assert n == 2
        assert feed_content_key(events) != feed_content_key(changed)
    finally:
        conn.close()


# ── (e) CME bars ─────────────────────────────────────────────────────

def make_bar(t, vol=100):
    return {"bar_time_utc": t, "open": 1.1, "high": 1.2, "low": 1.0,
            "close": 1.15, "volume": vol}


def test_filter_closed_bars_excludes_forming_bar():
    rows = [
        make_bar("2026-07-18T10:00:00Z"),   # 閉じた bar (11:00 close < now)
        make_bar("2026-07-18T11:00:00Z"),   # ちょうど閉じた bar (12:00 = now)
        make_bar("2026-07-18T11:30:00Z"),   # 形成中 → 除外
    ]
    out = filter_closed_bars(rows, NOW)
    assert [r["bar_time_utc"] for r in out] == [
        "2026-07-18T10:00:00Z", "2026-07-18T11:00:00Z"]


def test_save_bars_unique_dedup_freezes_first_capture(db_path):
    rows = [make_bar("2026-07-18T10:00:00Z", vol=100)]
    assert save_bars(db_path, "6E=F", rows) == (1, 0)
    # 同一 bar の再 fetch (yfinance 事後補正) は初回値を凍結
    rows2 = [make_bar("2026-07-18T10:00:00Z", vol=999)]
    assert save_bars(db_path, "6E=F", rows2) == (0, 1)
    out = export_cme_bars(db_path, symbol="6E=F")
    assert len(out) == 1 and out[0]["volume"] == 100


# ── (f) worker ───────────────────────────────────────────────────────

def test_worker_ff_cycle_saves_events_and_health(db_path):
    w = make_worker(db_path, ff_events=[
        make_ff_event(),
        make_ff_event(title="Retail Sales m/m", date=FUTURE),
    ])
    result = w.poll_once(force=True)
    assert result[JOB_FF]["saved"] == 2
    assert result[JOB_FF]["failed"] == 0
    events = export_ff_events(db_path)
    assert len(events) == 2
    health = db_health(db_path)
    assert "verified:ff_calendar" in health
    assert "last_cycle_at" in health
    # 生 feed snapshot も保存されている
    stats = db_market_stats(db_path)
    assert stats["ff_feed_snapshots"]["rows"] == 1


def test_worker_ff_fetch_failure_counts_and_short_retry(db_path):
    def ff_fail():
        return False, {"error": 503, "message": "upstream down"}
    w = MarketDataIngestWorker(db_path, ff_fetch=ff_fail,
                               bars_fetch=lambda s: [], symbols=["6E=F"])
    import time as _time
    before = _time.time()
    result = w.poll_once(force=True)
    assert result[JOB_FF]["failed"] == 1
    assert w._consec_fail[JOB_FF] == 1
    assert "503" in w._last_error
    # 失敗時は RETRY_SEC (< ff_poll_sec) で再試行
    assert w._next_due[JOB_FF] - before <= mdi.RETRY_SEC + 5
    # verified は更新されない (LOCF 汚染防止)
    assert "verified:ff_calendar" not in db_health(db_path)


def test_worker_ff_parse_failure_is_loud_but_cycle_verifies(db_path):
    w = make_worker(db_path, ff_events=[
        make_ff_event(),
        {"title": "broken", "country": "USD"},   # date 欠落
    ])
    result = w.poll_once(force=True)
    assert result[JOB_FF]["saved"] == 1
    assert result[JOB_FF]["failed"] == 1
    assert "ff parse" in w._last_error
    # feed 自体は取得できている — verified は更新される
    assert "verified:ff_calendar" in db_health(db_path)


def test_worker_cme_cycle_saves_bars_and_partial_failure(db_path):
    bars = {
        "6E=F": [make_bar("2026-07-17T10:00:00Z")],
        "6J=F": RuntimeError("yahoo down"),
    }
    w = make_worker(db_path, bars=bars, symbols=["6E=F", "6J=F"])
    result = w.poll_once(force=True)
    assert result[JOB_CME]["saved"] == 1
    assert result[JOB_CME]["failed"] == 1
    assert w._consec_fail[f"{JOB_CME}:6J=F"] == 1
    health = db_health(db_path)
    assert "verified:cme_bars:6E=F" in health
    assert "verified:cme_bars:6J=F" not in health
    # 部分失敗 → 短い retry
    status = w.status()
    assert status["next_due_in_sec"][JOB_CME] <= mdi.RETRY_SEC + 5


def test_worker_due_scheduling_skips_after_success(db_path):
    w = make_worker(db_path, ff_events=[make_ff_event()],
                    bars={"6E=F": [make_bar("2026-07-17T10:00:00Z")]})
    first = w.poll_once(force=True)
    assert set(first["ran"]) == {JOB_FF, JOB_CME}
    second = w.poll_once()   # 直後 — どの job も due でない
    assert second["ran"] == []
    assert w._poll_cycles == 2


def test_worker_reconciles_actuals_across_cycles(db_path):
    """cycle 1 で 6 月分を保存 → cycle 2 の feed に 7 月分が現れ actual 補完。"""
    events = [make_ff_event(date="2026-06-15T08:30:00-04:00",
                            forecast="2.3%", previous="2.2%")]
    w = make_worker(db_path, ff_events=events)
    w.poll_once(force=True)
    events.append(make_ff_event(previous="2.4%"))
    result = w.poll_once(force=True)
    assert result[JOB_FF]["actual_filled"] == 1
    rows = export_ff_events(db_path, until="2026-06-30T00:00:00Z")
    assert rows[0]["actual"] == "2.4%"
    assert rows[0]["actual_source"] == "next_previous"


def test_seed_next_due_from_health(db_path):
    """直近 verified があれば restart 直後に外部 API を叩き直さない。"""
    mdi.record_health(db_path, {
        "verified:ff_calendar": mdi._utcnow_iso(),
        "verified:cme_bars:6E=F": mdi._utcnow_iso(),
    })
    w = make_worker(db_path)
    w._seed_next_due()
    result = w.poll_once()
    assert result["ran"] == []
    status = w.status()
    assert status["next_due_in_sec"][JOB_FF] > 0
    assert status["next_due_in_sec"][JOB_CME] > 0


def test_poll_sec_clamps():
    w = make_worker(":memory:", ff_poll_sec=1, cme_poll_sec=1)
    assert w.ff_poll_sec == MIN_FF_POLL_SEC
    assert w.cme_poll_sec == MIN_CME_POLL_SEC


def test_default_symbols_contract():
    assert DEFAULT_CME_SYMBOLS == (
        "6E=F", "6J=F", "6B=F", "6A=F", "6C=F", "6S=F", "6N=F")


# ── env gate / singleton ─────────────────────────────────────────────

def test_enable_flag_off_no_worker(db_path, monkeypatch):
    monkeypatch.setenv("MARKET_INGEST_ENABLE", "0")
    assert start_market_data_ingest(db_path) is None
    assert mdi.get_worker() is None
    assert ensure_worker_running() is None


def test_env_overrides(db_path, monkeypatch):
    monkeypatch.setenv("MARKET_INGEST_ENABLE", "1")
    monkeypatch.setenv("CME_BARS_SYMBOLS", "6E=F , 6J=F")
    monkeypatch.setenv("FF_CALENDAR_POLL_SEC", "7200")
    monkeypatch.setenv("CME_BARS_POLL_SEC", "not-a-number")
    w = start_market_data_ingest(db_path, start_thread=False)
    assert w.symbols == ["6E=F", "6J=F"]
    assert w.ff_poll_sec == 7200
    assert w.cme_poll_sec == mdi.DEFAULT_CME_POLL_SEC
    assert w._thread is None


def test_start_reuses_existing_worker(db_path, monkeypatch):
    w1 = start_market_data_ingest(db_path, start_thread=False)
    w2 = start_market_data_ingest(db_path, start_thread=False)
    assert w1 is w2


# ── (g) self-heal ────────────────────────────────────────────────────

def test_ensure_running_restarts_dead_thread(db_path):
    w = make_worker(db_path)
    w.start()
    w._thread.join(timeout=0.1)
    # thread を強制的に「死んだ」状態にする (fork コピー相当)
    import threading
    dead = threading.Thread(target=lambda: None)
    dead.start()
    dead.join()
    w._thread = dead
    out = w.ensure_running()
    assert out["healed"] is True
    assert w._thread.is_alive()
    assert w._thread.name == THREAD_NAME
    w.stop()


def test_ensure_running_respects_stop_and_never_started(db_path):
    w = make_worker(db_path)
    assert w.ensure_running() == {"healed": False, "reason": "never started"}
    w.start()
    w.stop()
    assert w.ensure_running()["reason"] == "stopped"
    w2 = make_worker(db_path)
    w2.start()
    assert w2.ensure_running()["reason"] == "alive"
    w2.stop()


def test_defer_thread_arms_heal_without_spawning(db_path, monkeypatch):
    monkeypatch.setenv("MARKET_INGEST_ENABLE", "1")
    w = start_market_data_ingest(db_path, defer_thread=True,
                                 ff_fetch=lambda: (True, {"events": []}),
                                 bars_fetch=lambda s: [])
    assert w._thread is None
    assert w._started_at is not None
    out = ensure_worker_running()
    assert out["healed"] is True
    assert w._thread.is_alive()
    w.stop()


def test_status_self_heals_and_exposes_tables(db_path):
    w = make_worker(db_path, ff_events=[make_ff_event()])
    w.poll_once(force=True)
    status = w.status()
    assert status["enabled"] is True
    assert status["tables"]["ff_calendar_events"]["rows"] == 1
    assert status["counters"]["ff_saved"] == 1
    assert status["current_phase"] == "idle"
    assert "health" in status


# ── stats / export fail-loud ─────────────────────────────────────────

def test_db_market_stats_fail_loud_on_missing_table(tmp_path):
    empty = str(tmp_path / "empty.db")
    sqlite3.connect(empty).close()
    out = db_market_stats(empty)
    assert "_error" in out


def test_export_health_log_incremental(db_path):
    mdi.record_health(db_path, {"verified:ff_calendar": NOW})
    mdi.record_health(db_path, {"verified:ff_calendar": "2026-07-18T13:00:00Z"})
    rows = export_health_log(db_path, key="verified:ff_calendar")
    assert [r["value"] for r in rows] == [NOW, "2026-07-18T13:00:00Z"]
    rows2 = export_health_log(db_path, since_id=rows[0]["id"])
    assert len(rows2) == 1


def test_export_ff_events_filters(db_path):
    conn = sqlite3.connect(db_path)
    try:
        upsert_ff_event(conn, parse_ff_event(make_ff_event()), NOW)
        upsert_ff_event(conn, parse_ff_event(
            make_ff_event(country="GBP", impact="Low",
                          date="2026-07-16T06:00:00Z")), NOW)
        conn.commit()
    finally:
        conn.close()
    assert len(export_ff_events(db_path, country="usd")) == 1
    assert len(export_ff_events(db_path, impact="Low")) == 1
    assert len(export_ff_events(db_path, since="2026-07-16T00:00:00Z",
                                until="2026-07-17T00:00:00Z")) == 1


# ── (h) API 契約 ─────────────────────────────────────────────────────

def test_api_marketdata_status_worker_not_started(flask_client):
    resp = flask_client.get("/api/marketdata/status")
    assert resp.status_code == 200
    data = resp.get_json()
    # singleton は autouse fixture でリセット済み → 未起動経路
    assert data["enabled"] is False
    assert "tables" in data


def test_api_marketdata_export_contract(flask_client):
    resp = flask_client.get("/api/marketdata/export?table=nope")
    assert resp.status_code == 400
    for table in ("ff_events", "cme_bars", "health_log"):
        resp = flask_client.get(f"/api/marketdata/export?table={table}")
        # 本番 DB 側にテーブルが無い場合は 500 (fail-loud)、あれば 200
        assert resp.status_code in (200, 500)
        data = resp.get_json()
        assert ("rows" in data) or ("error" in data)
    resp = flask_client.get("/api/marketdata/export?limit=abc")
    assert resp.status_code == 400


# ── (i) import 経路 (tools/ff_calendar_import.py) ────────────────────

def test_import_tool_roundtrip(db_path):
    from tools.ff_calendar_import import import_rows
    rows = [
        {"country": "usd", "title": "CPI y/y",
         "event_time_utc": "2026-06-15T12:30:00Z",
         "impact": "High", "forecast": "2.3%", "previous": "2.2%",
         "actual": "2.4%"},
        {"country": "USD", "title": "CPI y/y",
         "event_time_utc": "2023-05-10T12:30:00Z", "actual": "4.9%"},
        {"country": "", "title": "broken", "event_time_utc": ""},
    ]
    out = import_rows(db_path, rows, "epsoft-test")
    assert out["inserted"] == 2
    assert out["invalid"] == 1
    got = export_ff_events(db_path, country="USD")
    assert got[0]["actual"] == "4.9%"
    assert got[0]["actual_source"] == "import:epsoft-test"
    # 再 import: 既存 actual は上書きしない
    rows[1]["actual"] = "9.9%"
    out2 = import_rows(db_path, rows[:2], "epsoft-test2")
    assert out2["inserted"] == 0
    assert out2["kept"] == 2
    got2 = export_ff_events(db_path, until="2024-01-01T00:00:00Z")
    assert got2[0]["actual"] == "4.9%"


def test_import_tool_fills_null_actual_on_existing_row(db_path):
    from tools.ff_calendar_import import import_rows
    # go-forward capture 済み (actual なし) の行に import が actual を補完
    conn = sqlite3.connect(db_path)
    try:
        upsert_ff_event(conn, parse_ff_event(
            make_ff_event(date="2026-06-15T08:30:00-04:00")), NOW)
        conn.commit()
    finally:
        conn.close()
    out = import_rows(db_path, [
        {"country": "USD", "title": "CPI y/y",
         "event_time_utc": "2026-06-15T12:30:00Z", "actual": "2.4%"},
    ], "backfill")
    assert out["actual_filled"] == 1
    got = export_ff_events(db_path)
    assert got[0]["actual"] == "2.4%"
    assert got[0]["actual_source"] == "import:backfill"


def test_import_tool_dry_run_writes_nothing(db_path):
    from tools.ff_calendar_import import import_rows
    out = import_rows(db_path, [
        {"country": "USD", "title": "NFP",
         "event_time_utc": "2026-06-05T12:30:00Z", "actual": "150K"},
    ], "test", dry_run=True)
    assert out["inserted"] == 1
    assert export_ff_events(db_path) == []


def test_import_tool_load_input_formats(tmp_path):
    from tools.ff_calendar_import import load_input
    csv_p = tmp_path / "in.csv"
    csv_p.write_text("country,title,event_time_utc,actual\n"
                     "USD,NFP,2026-06-05T12:30:00Z,150K\n")
    assert load_input(str(csv_p))[0]["title"] == "NFP"
    jsonl_p = tmp_path / "in.jsonl"
    jsonl_p.write_text(json.dumps({"country": "USD", "title": "NFP"}) + "\n")
    assert load_input(str(jsonl_p))[0]["country"] == "USD"
    arr_p = tmp_path / "in.json"
    arr_p.write_text(json.dumps([{"title": "x"}]))
    assert load_input(str(arr_p)) == [{"title": "x"}]
