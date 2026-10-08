"""price_shock_rev live watchdog — in-process DEMOTE reachability + API paging pins.

Registry `ps-watchdog-demotion-state-unreachable` (rule:R3, 2026-10-08):
the Render cron wrote the DEMOTE state file on its own filesystem, so the
trading process never saw it. These tests pin the repaired contract
end-to-end: "N>=10 ∧ (EV<0 ∨ Wilson_lo<0.40) in this process's DB ⇒
`_is_promoted_ex` blocks with cause `price_shock_rev_auto_demoted`" with
NO state file present (known-NG input), plus the counterfactuals
(N=9 / shadow rows / other cells) and the paged fetch.
"""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import pytest

from modules import price_shock_rev_watchdog_core as core
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader, PRICE_SHOCK_REV_TIER1_PAIRS

USD_CAD = ("price_shock_rev_usd_cad_h1_long", "USD_CAD")
EUR_GBP = ("price_shock_rev_eur_gbp_h1_long", "EUR_GBP")


def _insert_closed(db: DemoDB, *, trade_id: str, cell: tuple[str, str], pnl_pips: float,
                   is_shadow: int = 0) -> None:
    ts = datetime(2026, 6, 1, tzinfo=timezone.utc).isoformat()
    with db._safe_conn() as conn:
        conn.execute(
            """INSERT INTO demo_trades
               (trade_id, status, direction, entry_price, entry_time, exit_price,
                exit_time, sl, tp, pnl_pips, pnl_r, outcome, entry_type,
                confidence, is_shadow, oanda_trade_id, instrument)
               VALUES (?, 'CLOSED', 'BUY', 1.0, ?, 1.0, ?, 0.99, 1.01,
                       ?, 0.1, ?, ?, 70, ?, ?, ?)""",
            (trade_id, ts, ts, pnl_pips, "WIN" if pnl_pips > 0 else "LOSS", cell[0],
             is_shadow, "" if is_shadow else f"OANDA-{trade_id}", cell[1]),
        )
        conn.commit()


class _OandaStub:
    status = {}

    @staticmethod
    def get_strategy_mode(_entry_type):
        return ""


@pytest.fixture
def trader(tmp_path, monkeypatch):
    # No state file anywhere: the only way a DEMOTE can reach the gate is in-process.
    monkeypatch.setenv("PRICE_SHOCK_REV_DEMOTION_STATE", str(tmp_path / "absent" / "no-such-state.json"))
    DemoTrader._PS_REV_INPROCESS_DEMOTIONS = set()
    DemoTrader._PS_REV_INPROCESS_REFRESHED_AT = 0.0
    DemoTrader._PS_REV_INPROCESS_LAST_ERROR = ""
    DemoTrader._PS_REV_LATCH_LOADED = False
    DemoTrader._PS_REV_FAIL_CLOSED = False
    DemoTrader._PS_REV_PERSIST_PENDING = False
    db = DemoDB(str(tmp_path / "ps.db"))
    t = DemoTrader.__new__(DemoTrader)
    t._db = db
    t._oanda = _OandaStub()
    t._logs = []
    t._add_log = lambda msg: t._logs.append(msg)
    yield t
    DemoTrader._PS_REV_INPROCESS_DEMOTIONS = set()
    DemoTrader._PS_REV_INPROCESS_REFRESHED_AT = 0.0
    DemoTrader._PS_REV_INPROCESS_LAST_ERROR = ""
    DemoTrader._PS_REV_LATCH_LOADED = False
    DemoTrader._PS_REV_FAIL_CLOSED = False
    DemoTrader._PS_REV_PERSIST_PENDING = False


def test_core_is_the_single_predicate_used_by_the_cron_tool():
    import tools.price_shock_rev_live_watchdog as watchdog

    assert watchdog.run is core.run
    assert watchdog.filter_live_cell is core.filter_live_cell
    assert watchdog.verdict_for is core.verdict_for
    assert set(core.WATCHED_CELLS) == set(PRICE_SHOCK_REV_TIER1_PAIRS)


def test_demote_reaches_order_gate_without_any_state_file(trader):
    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)

    allowed, cause = trader._is_promoted_ex(*USD_CAD)

    assert (allowed, cause) == (False, "price_shock_rev_auto_demoted")
    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == {USD_CAD}
    assert DemoTrader._PS_REV_INPROCESS_LAST_ERROR == ""
    assert any("[PS_WATCHDOG]" in m for m in trader._logs)
    # classmethod readers (final gate / resend gate) see the same verdict
    assert DemoTrader._is_force_demoted_entry(*USD_CAD) is True
    assert DemoTrader._is_price_shock_rev_auto_demoted(*USD_CAD) is True


def test_n_below_10_does_not_demote(trader):
    for i in range(9):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)

    trader._refresh_price_shock_rev_in_process_demotions(force=True)

    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == set()
    assert DemoTrader._is_price_shock_rev_auto_demoted(*USD_CAD) is False


def test_shadow_rows_are_not_counted(trader):
    for i in range(12):
        _insert_closed(trader._db, trade_id=f"s{i}", cell=USD_CAD, pnl_pips=-5.0, is_shadow=1)

    trader._refresh_price_shock_rev_in_process_demotions(force=True)

    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == set()


def test_demote_is_cell_scoped_and_hold_cell_stays_live(trader):
    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    for i in range(10):  # EUR_GBP: WR 90% / EV>0 → HOLD
        _insert_closed(trader._db, trade_id=f"w{i}", cell=EUR_GBP, pnl_pips=2.0 if i < 9 else -1.0)

    trader._refresh_price_shock_rev_in_process_demotions(force=True)

    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == {USD_CAD}
    assert DemoTrader._is_price_shock_rev_auto_demoted(*EUR_GBP) is False
    allowed, cause = trader._is_promoted_ex(*EUR_GBP)
    assert cause != "price_shock_rev_auto_demoted"


def test_ttl_caches_and_force_refreshes(trader, monkeypatch):
    import modules.demo_trader as dt

    clock = {"t": 1_000_000.0}
    monkeypatch.setattr(dt.time, "time", lambda: clock["t"])
    trader._refresh_price_shock_rev_in_process_demotions(force=True)
    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == set()

    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    # within TTL: cached (no DB read)
    assert trader._refresh_price_shock_rev_in_process_demotions() == set()
    # after TTL: re-evaluated
    clock["t"] += DemoTrader.PRICE_SHOCK_REV_INPROCESS_TTL_SEC + 1
    assert trader._refresh_price_shock_rev_in_process_demotions() == {USD_CAD}


def test_db_failure_keeps_last_verdict_and_records_error(trader):
    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    trader._refresh_price_shock_rev_in_process_demotions(force=True)
    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == {USD_CAD}

    class _Broken:
        def _safe_conn(self):
            raise RuntimeError("database is locked")

    trader._db = _Broken()
    trader._refresh_price_shock_rev_in_process_demotions(force=True)

    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == {USD_CAD}  # fail-closed: keep block
    assert "RuntimeError" in DemoTrader._PS_REV_INPROCESS_LAST_ERROR
    assert DemoTrader._is_price_shock_rev_auto_demoted(*USD_CAD) is True


def test_state_file_remains_a_secondary_source(trader, tmp_path, monkeypatch):
    state = tmp_path / "manual.json"
    state.write_text(json.dumps({"demotions": [
        {"entry_type": EUR_GBP[0], "instrument": EUR_GBP[1]},
        {"entry_type": "not_a_ps_cell", "instrument": "USD_JPY"},
    ]}), encoding="utf-8")
    monkeypatch.setenv("PRICE_SHOCK_REV_DEMOTION_STATE", str(state))
    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    trader._refresh_price_shock_rev_in_process_demotions(force=True)

    assert DemoTrader._read_price_shock_rev_auto_demotions() == {USD_CAD, EUR_GBP}


def test_status_payload_exposes_in_process_verdict(trader):
    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    trader._refresh_price_shock_rev_in_process_demotions(force=True)
    # mirror of the get_status() block (the full payload needs a running engine)
    payload = {
        "in_process": sorted(list(c) for c in DemoTrader._PS_REV_INPROCESS_DEMOTIONS),
        "effective": sorted(list(c) for c in trader._read_price_shock_rev_auto_demotions()),
    }
    assert payload == {"in_process": [list(USD_CAD)], "effective": [list(USD_CAD)]}
    src = open("modules/demo_trader.py", encoding="utf-8").read()
    assert '"price_shock_rev_auto_demotions": {' in src  # key wired into get_status()


def test_demotion_is_latched_and_persisted_across_restart(trader, tmp_path):
    """Codex P1 4214808052: a later profitable close must not un-demote a cell,
    and a process restart (empty class set) must not either."""
    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    trader._refresh_price_shock_rev_in_process_demotions(force=True)
    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == {USD_CAD}
    assert trader._load_persisted_price_shock_rev_demotions() == {USD_CAD}

    # aggregate flips back to HOLD (a run of winners: N=40, WR 0.75, Wilson_lo>0.40,
    # EV>0) → predicate no longer true
    for i in range(30):
        _insert_closed(trader._db, trade_id=f"win-{i}", cell=USD_CAD, pnl_pips=+1.0)
    assert core.demoted_cells(core.filter_live_cell(
        [dict(r) for r in trader._db._safe_conn().__enter__().execute(
            "SELECT entry_type, instrument, is_shadow, status, pnl_pips FROM demo_trades").fetchall()],
        *USD_CAD)) == set()
    trader._refresh_price_shock_rev_in_process_demotions(force=True)
    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == {USD_CAD}  # latched

    # restart: fresh class set, same DB → restored from system_kv even though
    # the live predicate is now HOLD
    DemoTrader._PS_REV_INPROCESS_DEMOTIONS = set()
    DemoTrader._PS_REV_INPROCESS_REFRESHED_AT = 0.0
    DemoTrader._PS_REV_LATCH_LOADED = False
    t2 = DemoTrader.__new__(DemoTrader)
    t2._db = trader._db
    t2._add_log = lambda m: None
    t2._refresh_price_shock_rev_in_process_demotions(force=True)
    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == {USD_CAD}
    assert DemoTrader._is_force_demoted_entry(*USD_CAD) is True

    # explicit operator reset is the only release
    t2._reset_price_shock_rev_in_process_demotions()
    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == set()
    assert t2._load_persisted_price_shock_rev_demotions() == set()


def test_startup_resend_path_refreshes_before_its_gate(trader):
    """Codex P1 4214808057: _resend_pending_oanda_trades consults
    _is_force_demoted_entry (classmethod) directly; after a restart the class set
    is empty, so the resend path must refresh first."""
    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    DemoTrader._PS_REV_INPROCESS_DEMOTIONS = set()
    DemoTrader._PS_REV_INPROCESS_REFRESHED_AT = 0.0
    assert DemoTrader._is_force_demoted_entry(*USD_CAD) is False  # restart state

    class _InactiveOanda(_OandaStub):
        active = False

    trader._oanda = _InactiveOanda()
    trader._resend_pending_oanda_trades()
    assert DemoTrader._is_force_demoted_entry(*USD_CAD) is True


def test_unreadable_latch_on_restart_fails_closed_then_recovers(trader, monkeypatch):
    """Codex P1 4214970031: after a restart (empty class set) with the aggregate
    back at HOLD, an unreadable / malformed persisted latch must block every
    watched cell (not be read as 'no demotions'), retry soon, and release only
    once the latch is readable again."""
    import modules.demo_trader as dt
    # 1) demote + persist, then aggregate returns to HOLD
    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    trader._refresh_price_shock_rev_in_process_demotions(force=True)
    for i in range(30):
        _insert_closed(trader._db, trade_id=f"w{i}", cell=USD_CAD, pnl_pips=+1.0)
    assert trader._load_persisted_price_shock_rev_demotions() == {USD_CAD}

    # 2) restart: class set empty, kv read fails
    DemoTrader._PS_REV_INPROCESS_DEMOTIONS = set()
    DemoTrader._PS_REV_INPROCESS_REFRESHED_AT = 0.0
    DemoTrader._PS_REV_LATCH_LOADED = False
    real_get = trader._db.get_system_kv
    monkeypatch.setattr(trader._db, "get_system_kv", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("database is locked")))
    clock = {"t": 5_000_000.0}
    monkeypatch.setattr(dt.time, "time", lambda: clock["t"])
    trader._refresh_price_shock_rev_in_process_demotions(force=True)
    assert DemoTrader._PS_REV_FAIL_CLOSED is True
    assert DemoTrader._PS_REV_LATCH_LOADED is False
    assert "RuntimeError" in DemoTrader._PS_REV_INPROCESS_LAST_ERROR
    assert DemoTrader._is_price_shock_rev_auto_demoted(*USD_CAD) is True
    assert DemoTrader._is_price_shock_rev_auto_demoted(*EUR_GBP) is True  # every watched cell
    assert DemoTrader._is_price_shock_rev_auto_demoted("usdjpy_carry_dip_accumulator", "USD_JPY") is False
    assert trader._is_promoted_ex(*EUR_GBP) == (False, "price_shock_rev_auto_demoted")
    assert any("fail-closed" in m for m in trader._logs)

    # 3) malformed JSON is also unreadable (not an empty latch)
    monkeypatch.setattr(trader._db, "get_system_kv", lambda *a, **k: "{not json")
    clock["t"] += DemoTrader.PRICE_SHOCK_REV_INPROCESS_RETRY_SEC + 1
    trader._refresh_price_shock_rev_in_process_demotions()  # retry fires (not a full TTL)
    assert DemoTrader._PS_REV_FAIL_CLOSED is True

    # 4) latch readable again → latched cell restored, others released
    monkeypatch.setattr(trader._db, "get_system_kv", real_get)
    clock["t"] += DemoTrader.PRICE_SHOCK_REV_INPROCESS_RETRY_SEC + 1
    trader._refresh_price_shock_rev_in_process_demotions()
    assert DemoTrader._PS_REV_FAIL_CLOSED is False
    assert DemoTrader._PS_REV_LATCH_LOADED is True
    assert DemoTrader._is_price_shock_rev_auto_demoted(*USD_CAD) is True   # latched
    assert DemoTrader._is_price_shock_rev_auto_demoted(*EUR_GBP) is False  # released


def test_transient_failure_after_successful_load_keeps_set_without_global_block(trader, monkeypatch):
    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    trader._refresh_price_shock_rev_in_process_demotions(force=True)
    assert DemoTrader._PS_REV_LATCH_LOADED is True
    monkeypatch.setattr(trader._db, "get_system_kv", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("locked")))
    trader._refresh_price_shock_rev_in_process_demotions(force=True)
    assert DemoTrader._PS_REV_FAIL_CLOSED is False          # already loaded once
    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == {USD_CAD}  # known set kept
    assert DemoTrader._is_price_shock_rev_auto_demoted(*EUR_GBP) is False


def test_failed_latch_write_keeps_block_and_retries(trader, monkeypatch):
    """Codex P1 4215037466: when the first DEMOTE's system_kv write fails, the
    cell must stay blocked in memory, the failure must be visible (last_error,
    persist_pending) and the write must be retried — not cached as done for 600s."""
    import modules.demo_trader as dt
    clock = {"t": 7_000_000.0}
    monkeypatch.setattr(dt.time, "time", lambda: clock["t"])
    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    real_set = trader._db.set_system_kv
    monkeypatch.setattr(trader._db, "set_system_kv", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("database is locked")))

    trader._refresh_price_shock_rev_in_process_demotions(force=True)
    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == {USD_CAD}      # in-memory block holds
    assert DemoTrader._is_price_shock_rev_auto_demoted(*USD_CAD) is True
    assert DemoTrader._PS_REV_PERSIST_PENDING is True
    assert "persist" in DemoTrader._PS_REV_INPROCESS_LAST_ERROR
    assert trader._load_persisted_price_shock_rev_demotions() == set()  # not written yet

    # within the retry window nothing happens; after it the write is retried
    assert trader._refresh_price_shock_rev_in_process_demotions() == {USD_CAD}
    assert DemoTrader._PS_REV_PERSIST_PENDING is True
    monkeypatch.setattr(trader._db, "set_system_kv", real_set)
    clock["t"] += DemoTrader.PRICE_SHOCK_REV_INPROCESS_RETRY_SEC + 1
    trader._refresh_price_shock_rev_in_process_demotions()
    assert DemoTrader._PS_REV_PERSIST_PENDING is False
    assert DemoTrader._PS_REV_INPROCESS_LAST_ERROR == ""
    assert trader._load_persisted_price_shock_rev_demotions() == {USD_CAD}


def test_refresh_is_serialized_across_threads(trader, monkeypatch):
    """Codex P1 4215106664: two runner threads passing the TTL check together must
    not interleave read/union/persist/publish — the second waits for the first."""
    import threading
    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    gate = threading.Event()
    entered = threading.Event()
    real_load = trader._load_persisted_price_shock_rev_demotions
    calls = {"n": 0}

    def slow_load():
        calls["n"] += 1
        if calls["n"] == 1:
            entered.set()
            gate.wait(5)  # hold the lock mid-sequence
        return real_load()

    monkeypatch.setattr(trader, "_load_persisted_price_shock_rev_demotions", slow_load)
    a = threading.Thread(target=lambda: trader._refresh_price_shock_rev_in_process_demotions(force=True))
    b = threading.Thread(target=lambda: trader._refresh_price_shock_rev_in_process_demotions(force=True))
    a.start(); assert entered.wait(5)
    b.start(); b.join(0.3)
    assert b.is_alive(), "second refresh ran concurrently instead of waiting on the lock"
    assert calls["n"] == 1
    gate.set(); a.join(5); b.join(5)
    assert not a.is_alive() and not b.is_alive()
    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == {USD_CAD}
    assert trader._load_persisted_price_shock_rev_demotions() == {USD_CAD}


def test_fresh_demote_is_published_even_if_latch_read_fails_after_first_load(trader, monkeypatch):
    """Codex P1 4215165224: after a successful first load, a cell that newly
    crosses DEMOTE while the system_kv read transiently fails must block
    immediately (not after the 30s retry), and be persisted on recovery."""
    import modules.demo_trader as dt
    clock = {"t": 9_000_000.0}
    monkeypatch.setattr(dt.time, "time", lambda: clock["t"])
    trader._refresh_price_shock_rev_in_process_demotions(force=True)
    assert DemoTrader._PS_REV_LATCH_LOADED is True and DemoTrader._PS_REV_INPROCESS_DEMOTIONS == set()

    for i in range(10):
        _insert_closed(trader._db, trade_id=f"l{i}", cell=USD_CAD, pnl_pips=-1.0)
    real_get = trader._db.get_system_kv
    monkeypatch.setattr(trader._db, "get_system_kv", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("database is locked")))
    trader._refresh_price_shock_rev_in_process_demotions(force=True)

    assert DemoTrader._PS_REV_INPROCESS_DEMOTIONS == {USD_CAD}          # published immediately
    assert trader._is_promoted_ex(*USD_CAD) == (False, "price_shock_rev_auto_demoted")
    assert DemoTrader._PS_REV_FAIL_CLOSED is False                       # loaded earlier → no global block
    assert DemoTrader._is_price_shock_rev_auto_demoted(*EUR_GBP) is False
    assert DemoTrader._PS_REV_PERSIST_PENDING is True
    assert "RuntimeError" in DemoTrader._PS_REV_INPROCESS_LAST_ERROR

    monkeypatch.setattr(trader._db, "get_system_kv", real_get)
    clock["t"] += DemoTrader.PRICE_SHOCK_REV_INPROCESS_RETRY_SEC + 1
    trader._refresh_price_shock_rev_in_process_demotions()
    assert DemoTrader._PS_REV_PERSIST_PENDING is False
    assert trader._load_persisted_price_shock_rev_demotions() == {USD_CAD}


# ---------------- API paging ----------------

class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_opener(pages: list[list[dict]], calls: list[str]):
    def opener(req, timeout):
        calls.append(req.full_url)
        from urllib.parse import parse_qs, urlparse
        q = parse_qs(urlparse(req.full_url).query)
        offset = int(q["offset"][0]); limit = int(q["limit"][0])
        idx = offset // limit
        rows = pages[idx] if idx < len(pages) else []
        return _Resp(json.dumps({"trades": rows, "count": len(rows)}).encode())
    return opener


def test_fetch_closed_trades_paged_walks_all_pages_and_dedups():
    pages = [
        [{"trade_id": f"t{i}"} for i in range(3)],
        [{"trade_id": "t2"}, {"trade_id": "t3"}, {"trade_id": "t4"}],  # t2 shifted by a mid-fetch close
        [{"trade_id": "t5"}],  # short page → stop
    ]
    calls: list[str] = []
    rows = core.fetch_closed_trades_paged(
        "https://example.test", opener=_fake_opener(pages, calls), user_agent="ua", page_size=3
    )
    assert [r["trade_id"] for r in rows] == ["t0", "t1", "t2", "t3", "t4", "t5"]
    assert len(calls) == 3
    assert "status=closed&limit=3&offset=0" in calls[0]
    assert "offset=6" in calls[2]


def test_fetch_closed_trades_paged_stops_at_max_pages():
    pages = [[{"trade_id": f"p{p}-{i}"} for i in range(2)] for p in range(10)]
    calls: list[str] = []
    rows = core.fetch_closed_trades_paged(
        "https://example.test", opener=_fake_opener(pages, calls), user_agent="ua",
        page_size=2, max_pages=4,
    )
    assert len(rows) == 8 and len(calls) == 4


def test_tool_fetch_trades_uses_paging(monkeypatch):
    import tools.price_shock_rev_live_watchdog as watchdog
    import tools.price_shock_rev_promote_evaluator as evaluator

    pages = [[{"trade_id": f"t{i}"} for i in range(2)], [{"trade_id": "t9"}]]
    for mod in (watchdog, evaluator):
        calls: list[str] = []
        monkeypatch.setattr(mod._SAFE_OPENER, "open",
                            lambda req, timeout, _f=_fake_opener(pages, calls): _f(req, timeout))
        rows = mod.fetch_trades("https://example.test", limit=2)
        assert [r["trade_id"] for r in rows] == ["t0", "t1", "t9"]
        assert len(calls) == 2 and "offset=2" in calls[1]
