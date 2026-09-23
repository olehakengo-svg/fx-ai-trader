"""heartbeat.nav_at — NAV と同時にだけ更新される採取時刻 (2026-09-23、PR #295 review P2)。

`run_heartbeat()` は失敗時も `last_check` を進めるが `nav` は前回値のまま残す。
F4 資金時計 (tools/nav_floor_projection.py) が入出金の窓境界に `last_check` を使うと、
障害中は「失敗時刻 = 古い NAV の採取時刻」と誤読し、直前の成功〜失敗の間の入出金を
「NAV に反映済み」として除外する。pin: nav_at は成功 heartbeat でのみ nav と一緒に動く。
"""
from __future__ import annotations

from modules.oanda_bridge import OandaBridge


class _Client:
    configured = True

    def __init__(self, responses):
        self._responses = list(responses)

    def get_account(self):
        return self._responses.pop(0)


def _bridge(responses):
    b = OandaBridge(db=None)
    b._enabled = True
    b._client = _Client(responses)
    return b


def test_nav_at_moves_only_with_nav_and_stays_on_failed_heartbeat():
    b = _bridge([(True, {"account": {"NAV": "275472.0000", "balance": "275472.0000"}}),
                 (False, {"message": "timeout"})])
    assert b._heartbeat["nav_at"] is None
    hb1 = dict(b.run_heartbeat())
    assert hb1["status"] == "ok" and hb1["nav"] == "275472.0000"
    assert hb1["nav_at"] == hb1["last_check"]  # 同じ更新で同じ時刻
    hb2 = dict(b.run_heartbeat())
    assert hb2["status"] == "error"
    assert hb2["last_check"] > hb1["last_check"]  # 失敗時刻は進む
    assert hb2["nav"] == hb1["nav"] and hb2["nav_at"] == hb1["nav_at"]  # NAV とその採取時刻は動かない
    assert hb2["nav_at"] != hb2["last_check"]


def test_nav_at_stays_none_when_first_heartbeat_fails():
    b = _bridge([(False, {"message": "401"})])
    hb = dict(b.run_heartbeat())
    assert hb["status"] == "error" and hb["nav"] is None and hb["nav_at"] is None
    assert hb["last_check"] is not None
