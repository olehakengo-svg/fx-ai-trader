"""R3 回帰: BT LOSS 記帳は実効ストップ (_current_sl 系) 基準 (2026-08-05, rule:R3).

phantom-loss バグ (sr_anti_hunt×EUR_JPY BT WR 84.9%→0.0% 反転の増幅因):
time-decay SL tightening が stop を entry 付近へ引き上げた後の退出 (実損≈0) を、
`actual_sl_m` 未設定 → planned `sl_m` fallback でフル損失として記帳していた。
anti-hunt 系は sl_m が 6-11 ATR (TP≈10ATR × MIN_RR 1.2 逆算) のため、
break-even 退出 1 件が −8.3R の架空損失になる。

本テストは daytrade / scalp 両エンジンで以下を構造的に pin する:
  1. LOSS 記帳の gap-through 判定が実効ストップ変数
     (_dt_current_sl / _current_sl) を参照する — planned `sl` ではなく。
  2. else 分岐 (gap なし = ストップ水準で fill) でも actual_sl_m が必ず
     設定される — planned sl_m への silent fallback を許さない。
ref: knowledge-base/wiki/analyses/bt-harness-effective-stop-booking-2026-08-05.md
"""
from __future__ import annotations

import ast
import os

import pytest

_APP_PY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py"
)

# (エンジン名, 実効ストップ変数名)。run_backtest(1H) は default ablated で
# _current_sl が不動 (BE/decay なし) のため対象外、run_1h_backtest は既に
# close-based 記帳で phantom-loss なし。
_TARGETS = [
    ("run_daytrade_backtest", "_dt_current_sl"),
    ("run_scalp_backtest", "_current_sl"),
]


@pytest.fixture(scope="module")
def _engine_funcs():
    with open(_APP_PY, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=_APP_PY)
    funcs = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name in {name for name, _ in _TARGETS}
    }
    missing = {name for name, _ in _TARGETS} - set(funcs)
    assert not missing, f"engine functions not found in app.py: {missing}"
    return funcs


def _is_actual_sl_m_assign(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Subscript)
        and isinstance(getattr(node.targets[0].slice, "value", None), str)
        and node.targets[0].slice.value == "actual_sl_m"
    )


def _booking_ifs(fn: ast.FunctionDef) -> list[ast.If]:
    """actual_sl_m 代入を body に含む If ノード (= gap-through 分岐) を収集。"""
    found = []
    for node in ast.walk(fn):
        if isinstance(node, ast.If) and any(
            _is_actual_sl_m_assign(child) for child in ast.walk(node)
        ):
            found.append(node)
    return found


@pytest.mark.parametrize("engine,stop_var", _TARGETS)
def test_gap_check_uses_effective_stop(_engine_funcs, engine, stop_var):
    """gap-through 判定 (fut_close vs stop) は実効ストップ変数を参照する。"""
    fn = _engine_funcs[engine]
    ifs = _booking_ifs(fn)
    assert ifs, f"{engine}: actual_sl_m 記帳 If が見つからない (構造前提崩れ)"
    gap_ifs = [n for n in ifs if "fut_close" in ast.dump(n.test)]
    assert gap_ifs, f"{engine}: fut_close gap-through 判定が見つからない"
    for node in gap_ifs:
        assert stop_var in ast.dump(node.test), (
            f"{engine}: gap-through 判定が {stop_var} (実効ストップ) ではなく "
            f"planned sl を参照 — phantom-loss 再発 (decay/BE 後の退出が "
            f"フル sl_m 損失として記帳される)"
        )


@pytest.mark.parametrize("engine,stop_var", _TARGETS)
def test_actual_sl_m_always_set_on_tp_sl_loss(_engine_funcs, engine, stop_var):
    """gap なし分岐 (orelse) でも actual_sl_m を実効ストップ距離で必ず設定。"""
    fn = _engine_funcs[engine]
    gap_ifs = [n for n in _booking_ifs(fn) if "fut_close" in ast.dump(n.test)]
    assert gap_ifs, f"{engine}: fut_close gap-through 判定が見つからない"
    node = gap_ifs[-1]
    else_assigns = [
        child for child in node.orelse for c in [child]
        if _is_actual_sl_m_assign(child)
    ] or [
        c for child in node.orelse for c in ast.walk(child)
        if _is_actual_sl_m_assign(c)
    ]
    assert else_assigns, (
        f"{engine}: gap なし分岐で actual_sl_m 未設定 — planned sl_m fallback "
        f"が復活する (tightened stop の退出がフル損失で記帳)"
    )
    for assign in else_assigns:
        assert stop_var in ast.dump(assign.value), (
            f"{engine}: else 分岐の actual_sl_m が {stop_var} 基準でない"
        )
