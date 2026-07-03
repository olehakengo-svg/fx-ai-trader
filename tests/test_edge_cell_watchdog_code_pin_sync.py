"""Watchdog CODE_PIN_SYNC の回帰テスト (rule:R3, 2026-07-03).

modules.edge_cell_promote.DISABLED_CELLS (code pin = SSOT) と Render KV
`edge_cell_stage:E*` の乖離は「eligible と effective を区別する」教訓に反する
認知負債。E4 は 2026-07-02 zombie incident の再武装 (0→1) が KV に残置され、
床バグ修正後の watchdog は DECREMENT を stage>=2 にしか発行しないため自然回復
しない。watchdog は pin セルの KV!=0 を検出したら new_stage=0 を発行して同期し、
同期済みなら何も発行しない (self-quiescing)。
ref: knowledge-base/wiki/decisions/edge-cell-e1-e4-code-disable-2026-07-02.md
"""
from __future__ import annotations

from modules.edge_cell_promote import DISABLED_CELLS
from tools.edge_cell_watchdog import CODE_PINNED_CELLS, evaluate

_SYNC_REASON = "code-pin sync (zombie incident 2026-07-02)"


def _closed_live_trade(cell_id: str, pnl_pips: float, day: int) -> dict:
    return {
        "edge_cell_id": cell_id,
        "is_shadow": 0,
        "status": "CLOSED",
        "pnl_pips": pnl_pips,
        "exit_time": f"2026-06-{day:02d}T12:00:00+00:00",
    }


def _decrement_pocket_trades(cell_id: str) -> list[dict]:
    """N=12, WR=41.7% (>28%), EV=-0.75 (>-1.0), PF≈0.36 (<1) — E4 incident と
    同じ「両 DISABLE ゲートをすり抜けて DECREMENT に落ちる」ポケット。"""
    pnls = [+1.0] * 5 + [-2.0] * 7
    return [_closed_live_trade(cell_id, p, day=1 + i) for i, p in enumerate(pnls)]


def _state(stages: dict[str, int], *, current_nav: float = 3_000_000.0) -> dict:
    return {
        "stages": stages,
        "lock_nav_jpy": 3_000_000.0,
        "current_nav_jpy": current_nav,
        "global_disabled": False,
    }


def test_mirror_matches_code_pin_ssot():
    """CODE_PINNED_CELLS は DISABLED_CELLS のミラー。乖離は CI で必ず落とす
    (watchdog は cron で stdlib-only 実行のため modules/ を import できない)。"""
    assert CODE_PINNED_CELLS == DISABLED_CELLS


def test_pinned_cell_kv_mismatch_emits_sync_to_zero():
    """pin セルの KV stage=1 → new_stage=0 を発行 (E4 残置の解消経路)。"""
    payload = evaluate([], _state({"E4": 1}), cell_ids=["E4"])
    assert payload["cells"]["E4"]["verdict"] == "CODE_PIN_SYNC"
    assert payload["actions"] == [
        {"cell_id": "E4", "new_stage": 0, "reason": _SYNC_REASON}
    ]


def test_pinned_cell_synced_emits_nothing():
    """KV=0 に同期済みの pin セルは action ゼロ (self-quiescing)。"""
    payload = evaluate([], _state({"E4": 0}), cell_ids=["E4"])
    assert payload["cells"]["E4"]["verdict"] == "HOLD"
    assert payload["cells"]["E4"]["reasons"] == ["CODE_PINNED"]
    assert payload["actions"] == []


def test_pinned_cell_metric_verdicts_do_not_override_sync():
    """DECREMENT ポケットの成績でも pin セルは stage-1 でなく 0 へ同期する
    (metric 判定が sync と喧嘩して 2→1 等を出してはならない)。"""
    trades = _decrement_pocket_trades("E4")
    payload = evaluate(trades, _state({"E4": 2}), cell_ids=["E4"])
    assert payload["actions"] == [
        {"cell_id": "E4", "new_stage": 0, "reason": _SYNC_REASON}
    ]


def test_pinned_cell_global_disable_emits_single_action():
    """global kill (DD>8%) 時は global 経路が new_stage=0 を出すので、
    CODE_PIN_SYNC は重複 action を出さない。"""
    payload = evaluate(
        [], _state({"E4": 1}, current_nav=2_700_000.0), cell_ids=["E4"]
    )
    assert len(payload["actions"]) == 1
    action = payload["actions"][0]
    assert action["cell_id"] == "E4"
    assert action["new_stage"] == 0
    assert action["reason"].startswith("ACCOUNT_DD_GT_8_FROM_LOCK")
