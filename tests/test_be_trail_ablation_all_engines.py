"""P1-2 回帰: BE/Trail ablation を全 BT エンジンへ展開 (2026-07-09, rule:R3).

MEMORY 確定事実 `project_be_trail_inflates_python_bt_wr`:
BE/Trail 発動後の SL touch を fake-WIN 化するロジックが Python BT WR を
TV 比 +20pp inflate する。daytrade エンジンでは `_BT_ABLATE_BE_TRAIL`
(default True) で既に排除済みだったが、scalp / run_backtest(1H) /
run_1h_backtest の 3 エンジンに残存していた (fable5-system-audit P1-2)。

本テストは 4 エンジン全てで以下を構造的に pin する:
  1. `_BT_OPTIMISTIC` / `_BT_ABLATE_BE_TRAIL` フラグが定義され、
     default が ablated (= not optimistic) である。
  2. BE/Trail 発動 (`_be_activated = True` もしくは閾値設定) が
     `_BT_ABLATE_BE_TRAIL` で gate されている — default では発火しない。

行動証拠 (fixture usd_jpy_m15_2024q1、`_df_override` 経由 scalp BT):
  ablated(default) N=84 WR=46.4%  vs  BT_OPTIMISTIC=1 N=102 WR=56.9%
  → +10.5pp の inflation を default で排除。
ref: knowledge-base/wiki/decisions/fable5-system-audit-2026-07-02.md (P1-2)
"""
from __future__ import annotations

import ast
import os

import pytest

_APP_PY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py"
)

# 4 エンジンのうち、BE/Trail fake-WIN 機構を持つもの。
# scalp/daytrade は閾値=inf 方式、1H系は `if not _BT_ABLATE_BE_TRAIL:` guard 方式。
_ENGINES = [
    "run_backtest",          # 1H (SR構造ベース)
    "run_scalp_backtest",    # scalp 1m/5m
    "run_daytrade_backtest",  # daytrade 15m (先行実装済 — 回帰 pin)
    "run_1h_backtest",       # 1H zone-based
]


@pytest.fixture(scope="module")
def _engine_funcs():
    with open(_APP_PY, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=_APP_PY)
    funcs = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in _ENGINES
    }
    missing = set(_ENGINES) - set(funcs)
    assert not missing, f"engine functions not found in app.py: {missing}"
    return funcs


def _assign_targets(node: ast.Assign) -> list[str]:
    names = []
    for tgt in node.targets:
        if isinstance(tgt, ast.Name):
            names.append(tgt.id)
    return names


@pytest.mark.parametrize("engine", _ENGINES)
def test_flag_defined_and_default_ablated(_engine_funcs, engine):
    """各エンジンで default が ablated (not optimistic) であることを pin。"""
    fn = _engine_funcs[engine]
    saw_optimistic = False
    saw_ablate = False
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            names = _assign_targets(node)
            if "_BT_OPTIMISTIC" in names:
                saw_optimistic = True
            if "_BT_ABLATE_BE_TRAIL" in names:
                saw_ablate = True
                # 定義式に "not _BT_OPTIMISTIC" が含まれる = default ablated
                src = ast.dump(node.value)
                assert "_BT_OPTIMISTIC" in src, (
                    f"{engine}: _BT_ABLATE_BE_TRAIL は _BT_OPTIMISTIC に依存すべき "
                    f"(default ablated 保証)"
                )
    assert saw_optimistic, f"{engine}: _BT_OPTIMISTIC 未定義"
    assert saw_ablate, f"{engine}: _BT_ABLATE_BE_TRAIL 未定義"


def _parent_map(fn: ast.FunctionDef) -> dict[int, ast.AST]:
    parents: dict[int, ast.AST] = {}
    for parent in ast.walk(fn):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent
    return parents


def _guarded_by_ablate(node: ast.AST, parents: dict[int, ast.AST]) -> bool:
    """node の祖先 If の test に _BT_ABLATE_BE_TRAIL 参照があるか。"""
    cur = node
    while id(cur) in parents:
        parent = parents[id(cur)]
        if isinstance(parent, ast.If):
            test_src = ast.dump(parent.test)
            if "_BT_ABLATE_BE_TRAIL" in test_src:
                return True
        cur = parent
    return False


@pytest.mark.parametrize("engine", _ENGINES)
def test_be_activation_gated_by_ablate_flag(_engine_funcs, engine):
    """`_be_activated = True` 代入は必ず _BT_ABLATE_BE_TRAIL guard 配下に置く。

    guard を外すと fake-WIN 機構が復活する (= +20pp inflation 再発)。
    scalp/daytrade は閾値=inf 方式のため `_be_activated=True` は
    `if _BT_ABLATE_BE_TRAIL:` の *外* にあるが、閾値が inf のため到達不能。
    その場合は threshold=inf ablation の存在を代替として要求する。
    """
    fn = _engine_funcs[engine]
    parents = _parent_map(fn)

    # エンジンによって変数名が異なる (_be_activated / _dt_be_activated)
    be_true_nodes = [
        node
        for node in ast.walk(fn)
        if isinstance(node, ast.Assign)
        and any(t.endswith("be_activated") for t in _assign_targets(node))
        and isinstance(node.value, ast.Constant)
        and node.value.value is True
    ]
    assert be_true_nodes, f"{engine}: `_be_activated = True` が見つからない (構造前提崩れ)"

    all_guarded = all(_guarded_by_ablate(n, parents) for n in be_true_nodes)

    # 閾値=inf 方式の検出: `if _BT_ABLATE_BE_TRAIL:` 配下で閾値変数に float("inf") 代入
    threshold_inf_ablation = False
    for node in ast.walk(fn):
        if isinstance(node, ast.If) and "_BT_ABLATE_BE_TRAIL" in ast.dump(node.test):
            body_src = "".join(ast.dump(b) for b in node.body)
            if "inf" in body_src and ("_be_thr" in body_src or "_ts_thr" in body_src):
                threshold_inf_ablation = True

    assert all_guarded or threshold_inf_ablation, (
        f"{engine}: BE/Trail 発動が _BT_ABLATE_BE_TRAIL で gate されていない — "
        f"fake-WIN inflation が default で発火する構造"
    )
