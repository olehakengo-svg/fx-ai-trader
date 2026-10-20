"""Pins for `_fetch_bracketed` membership evidence (PR #326 round 8 deferrals,
registry review-backlog-326-p2-deferrals-2026-10-13, rule:R3 tools-only).

(a) comment 4254831598 — superset mode (clock probe failed / no Date header)
    keeps rows that may have opened after `as_of` while `_fetch_meta.complete`
    stays true.  The reader used to accept such a snapshot as proven.  Now the
    artifact states `membership_proven=false` and `main()` refuses it unless
    `--allow-superset-snapshot` is passed.
(b) comment 4254831605 — an `open_before` row with a missing / malformed
    `entry_time` is kept but was neither counted nor marked ambiguous, so the
    artifact showed zero uncertainty.  Now it is counted as
    `open_before_unjudged`.
"""
import json

import pytest

import tools.cell_deepdive_audit as cda


def _row(i, entry_time, closed=False):
    r = {"id": i, "trade_id": f"t{i}", "entry_time": entry_time, "instrument": "USD_JPY",
         "entry_type": "x", "direction": "BUY", "is_shadow": 1, "oanda_trade_id": "",
         "outcome": None, "pnl_pips": None}
    if closed:
        r.update({"exit_time": "2026-10-19T00:00:00+00:00", "outcome": "WIN", "pnl_pips": 1.0})
    return r


def _wire(monkeypatch, *, clock, open_before, open_after):
    """Stub the four network reads: open → closed → closed(confirm) → open."""
    opens = iter([open_before, open_after])
    monkeypatch.setattr(cda, "_server_clock_offset", lambda: clock)
    monkeypatch.setattr(cda, "_http_fetch_open", lambda limit=100000: list(next(opens)))
    monkeypatch.setattr(cda, "_http_fetch_closed_page", lambda limit, offset: [])   # short page → complete


def test_superset_mode_is_stated_as_unproven_membership(monkeypatch):
    before = [_row(1, "2026-10-01T00:00:00+00:00")]
    _wire(monkeypatch, clock=None, open_before=before, open_after=before)
    rows, payload, ev = cda._fetch_bracketed()
    m = payload["_fetch_meta"]
    assert m["complete"] is True                       # pagination is still complete …
    assert m["membership_proven"] is False             # … but membership is not
    assert m["membership_basis"].startswith("superset")
    assert len(rows) == 1 and ev["open_before_unjudged"] == 0


def test_measured_clock_marks_membership_proven(monkeypatch):
    before = [_row(1, "2026-10-01T00:00:00+00:00")]
    _wire(monkeypatch, clock=(0.0, 0.05), open_before=before, open_after=before)
    _, payload, _ = cda._fetch_bracketed()
    assert payload["_fetch_meta"]["membership_proven"] is True


def test_open_before_row_without_entry_time_is_kept_and_counted(monkeypatch):
    """(b) the unjudgeable row from the FIRST open read: kept, and visible in the artifact."""
    before = [_row(1, None), _row(2, "not-a-timestamp"), _row(3, "2026-10-01T00:00:00+00:00")]
    _wire(monkeypatch, clock=(0.0, 0.05), open_before=before, open_after=before)
    rows, payload, ev = cda._fetch_bracketed()
    assert {r["id"] for r in rows} == {1, 2, 3}                 # never dropped silently
    assert ev["open_before_unjudged"] == 2
    assert ev["open_after_only_unjudged"] == 0                  # the trailing loop cannot see them
    assert payload["_fetch_meta"]["closed_entries_unjudged"] == 0


def _write_snapshot(tmp_path, monkeypatch, *, clock):
    before = [_row(1, "2026-10-01T00:00:00+00:00")]
    _wire(monkeypatch, clock=clock, open_before=before, open_after=before)
    snap = tmp_path / "snap.json"
    assert cda.main(["--fetch-to", str(snap)]) == 0
    return snap


def test_fetch_to_persists_the_new_counters(tmp_path, monkeypatch, capsys):
    snap = _write_snapshot(tmp_path, monkeypatch, clock=None)
    m = json.loads(snap.read_text())["_fetch_meta"]
    assert m["membership_proven"] is False and m["open_before_unjudged"] == 0
    assert "SUPERSET" in capsys.readouterr().out


def test_reader_refuses_a_superset_snapshot_without_opt_in(tmp_path, monkeypatch):
    snap = _write_snapshot(tmp_path, monkeypatch, clock=None)
    monkeypatch.setattr(cda, "run_audit", lambda trades, **kw: {"stub": len(trades)})
    with pytest.raises(SystemExit, match="membership_proven is false"):
        cda.main([str(snap), "--no-write", "--min-rows", "0"])
    # explicit opt-in audits it, loudly
    assert cda.main([str(snap), "--no-write", "--min-rows", "0", "--allow-superset-snapshot"]) == 0


def test_reader_accepts_a_proven_snapshot_and_a_legacy_one(tmp_path, monkeypatch):
    snap = _write_snapshot(tmp_path, monkeypatch, clock=(0.0, 0.05))
    monkeypatch.setattr(cda, "run_audit", lambda trades, **kw: {"stub": len(trades)})
    assert cda.main([str(snap), "--no-write", "--min-rows", "0"]) == 0
    # legacy artifact: predates the flag, states no superset basis → unchanged behaviour
    payload = json.loads(snap.read_text())
    payload["_fetch_meta"].pop("membership_proven")
    payload["_fetch_meta"].pop("membership_basis")
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps(payload))
    assert cda.main([str(legacy), "--no-write", "--min-rows", "0"]) == 0
    # legacy artifact that STATES a superset basis is treated like the flag
    payload["_fetch_meta"]["membership_basis"] = "superset: server clock unmeasured, nothing excluded"
    legacy.write_text(json.dumps(payload))
    with pytest.raises(SystemExit, match="membership_proven is false"):
        cda.main([str(legacy), "--no-write", "--min-rows", "0"])
