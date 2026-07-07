"""Watchdog DECREMENT 床バグの回帰テスト (rule:R3, 2026-07-02).

旧実装 `new_stage = max(1, stage - 1)` は床が 1 のため、stage=0 (disabled) の
セルが DECREMENT ポケット (N>=10, PF<1, ただし WR>=28% かつ EV>=-1.0 で両
DISABLE ゲートをすり抜ける) に入ると毎実行 0→1 に「再武装」された。

Incident: E4 (bb_rsi_reversion NY SELL, T10 KILL 済み) が 2026-07-02 10:18Z の
API_AUTH_TOKEN 投入直後の watchdog 実行で 0→1 に再武装され、13:08-19:55 UTC に
live 11 発。手動/CB の stage=0 が 15 分も持たない構造だった。
ref: knowledge-base/wiki/decisions/edge-cell-e1-e4-code-disable-2026-07-02.md
"""
from __future__ import annotations

from tools.edge_cell_watchdog import evaluate


def _closed_live_trade(cell_id: str, pnl_pips: float, day: int) -> dict:
    return {
        "edge_cell_id": cell_id,
        "is_shadow": 0,
        "status": "CLOSED",
        "pnl_pips": pnl_pips,
        "exit_time": f"2026-06-{day:02d}T12:00:00+00:00",
    }


def _decrement_pocket_trades(cell_id: str) -> list[dict]:
    """N=12, WR=5/12=41.7% (>28%), EV=-0.75 (>-1.0), PF=5/14≈0.36 (<1)
    → 旧コードで DECREMENT 判定になる組合せ (E4 incident と同じポケット)。"""
    pnls = [+1.0] * 5 + [-2.0] * 7
    return [_closed_live_trade(cell_id, p, day=1 + i) for i, p in enumerate(pnls)]


def _state(stages: dict[str, int]) -> dict:
    return {
        "stages": stages,
        "lock_nav_jpy": 3_000_000.0,
        "current_nav_jpy": 3_000_000.0,
        "global_disabled": False,
    }


def test_decrement_never_rearms_stage0_cell():
    """stage=0 + DECREMENT ポケット → action ゼロ (0→1 再武装の禁止)。

    incident cell E4 は 2026-07-03 の CODE_PIN_SYNC で metric 判定より前に
    short-circuit するようになった (test_edge_cell_watchdog_code_pin_sync.py
    で固定) ため、この性質は非 pin セル E5 で検証する — バグは cell 非依存。"""
    trades = _decrement_pocket_trades("E5")
    payload = evaluate(trades, _state({"E5": 0}), cell_ids=["E5"])
    assert payload["cells"]["E5"]["verdict"] == "DECREMENT"
    assert payload["actions"] == []


def test_decrement_lowers_ladder_from_stage_3_and_2():
    for stage, expected in ((3, 2), (2, 1)):
        trades = _decrement_pocket_trades("E5")
        payload = evaluate(trades, _state({"E5": stage}), cell_ids=["E5"])
        assert payload["actions"] == [
            {"cell_id": "E5", "new_stage": expected, "reason": "PF_BELOW_1"}
        ], stage


def test_decrement_at_stage_1_emits_no_action():
    """stage=1 は旧コードでも実質 no-op (max(1,0)=1) — action 自体を出さない。"""
    trades = _decrement_pocket_trades("E5")
    payload = evaluate(trades, _state({"E5": 1}), cell_ids=["E5"])
    assert payload["actions"] == []


def test_disable_verdict_still_forces_stage_0():
    """DISABLE ゲート (EV<-1.0) は従来どおり stage=0 を発行する。"""
    pnls = [-3.0] * 10  # WR=0%<28%, EV=-3.0<-1.0
    trades = [_closed_live_trade("E9", p, day=1 + i) for i, p in enumerate(pnls)]
    payload = evaluate(trades, _state({"E9": 1}), cell_ids=["E9"])
    assert payload["actions"] == [
        {"cell_id": "E9", "new_stage": 0, "reason": "WR_BELOW_28"}
    ]
