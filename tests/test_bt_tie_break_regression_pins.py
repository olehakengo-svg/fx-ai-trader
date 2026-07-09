"""P1-2b + P1-2 補完回帰 pin — superseded PR #64 からのテスト移植 (rule:R3).

audit P1-2/P1-2b (fable5-system-audit-2026-07-02) / roadmap v2.3 T14。
実装本体は PR #65 (fix/p1-2-be-trail-ablation-scalp-1h、autopilot) で main に
マージ済み。本ファイルは PR #64 (同一実装、二重実装レースで close) にあった
テストのうち **main の `tests/test_be_trail_ablation_all_engines.py` (AST 構造
pin ×2) に無いもの**だけを、main の inline 実装形に適合させて移植する:

  1. env フラグの canonical 式 pin — 各エンジンの inline 定義式を AST で厳密
     照合。main の既存 pin は「式が _BT_OPTIMISTIC を参照する」ことしか見ない
     ため、真偽の向きが逆でも通る。canonical 式が固定されれば semantics は
     真理値表で一意:
       default                              -> opt=False, ablate=True  (TV-aligned)
       BT_OPTIMISTIC=1                      -> opt=True,  ablate=False (旧挙動復元)
       BT_OPTIMISTIC=1 + BT_ABLATE_BE_TRAIL=1 -> opt=True, ablate=True (ablation 優先)
  2. cache 無効化 pin — 4 エンジン全てで BE/Trail フラグが cache
     key/フラグ照合に反映されていること (stale cache = A/B 比較汚染の防止)。
  3. P1-2b: 同一バー TP+SL 同時ヒットの fut_close tie-break が 4 エンジン全てに
     既装であることの検証 pin (2026-07-09 検証で追加実装不要と確定)。無条件
     TP 優先への退行を封鎖。swing は保守的 SL 優先 (両ヒット=LOSS) を維持。
"""
import ast
import inspect
import re

import pytest

import app

_ENGINE_NAMES = [
    "run_backtest",           # 1H standard
    "run_scalp_backtest",     # scalp 1m/5m
    "run_daytrade_backtest",  # daytrade 15m (参照実装)
    "run_1h_backtest",        # 1H zone
]


@pytest.fixture(scope="module")
def _engine_nodes():
    app_py = inspect.getsourcefile(app)
    with open(app_py, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=app_py)
    funcs = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in _ENGINE_NAMES
    }
    missing = set(_ENGINE_NAMES) - set(funcs)
    assert not missing, f"engine functions not found in app.py: {missing}"
    return funcs


def _find_flag_exprs(fn_node):
    """エンジン内の _BT_OPTIMISTIC / _BT_ABLATE_BE_TRAIL 定義式 (AST) を返す。"""
    opt_expr = abl_expr = None
    for node in ast.walk(fn_node):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "_BT_OPTIMISTIC" in names:
                opt_expr = node.value
            if "_BT_ABLATE_BE_TRAIL" in names:
                abl_expr = node.value
    assert opt_expr is not None, f"{fn_node.name}: _BT_OPTIMISTIC 定義なし"
    assert abl_expr is not None, f"{fn_node.name}: _BT_ABLATE_BE_TRAIL 定義なし"
    return opt_expr, abl_expr


def _is_env_eq_one(node, env_name):
    """node が `os.environ.get(env_name) == "1"` (str.strip 等の変形なし) か。"""
    return (
        isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Call)
        and isinstance(node.left.func, ast.Attribute)
        and node.left.func.attr == "get"
        and node.left.args
        and isinstance(node.left.args[0], ast.Constant)
        and node.left.args[0].value == env_name
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.Eq)
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Constant)
        and node.comparators[0].value == "1"
    )


# ── 1. env フラグの canonical 式 pin (全エンジン) ────────────────────


@pytest.mark.parametrize("engine", _ENGINE_NAMES)
def test_inline_flag_exprs_are_canonical(_engine_nodes, engine):
    """`_BT_OPTIMISTIC = os.environ.get("BT_OPTIMISTIC") == "1"` と
    `_BT_ABLATE_BE_TRAIL = (not _BT_OPTIMISTIC) or
     (os.environ.get("BT_ABLATE_BE_TRAIL") == "1")` の canonical 形を厳密 pin。

    この式が固定なら docstring の真理値表が成立する (default = TV-aligned
    ablated / BT_OPTIMISTIC=1 で復元 / BT_ABLATE_BE_TRAIL=1 が優先)。
    等価でない式への差し替え (真偽逆転・env 名 typo・default "1" 化) を検出。"""
    opt_expr, abl_expr = _find_flag_exprs(_engine_nodes[engine])

    assert _is_env_eq_one(opt_expr, "BT_OPTIMISTIC"), (
        f"{engine}: _BT_OPTIMISTIC が canonical 形 "
        f'`os.environ.get("BT_OPTIMISTIC") == "1"` でない')

    assert (
        isinstance(abl_expr, ast.BoolOp)
        and isinstance(abl_expr.op, ast.Or)
        and len(abl_expr.values) == 2
        and isinstance(abl_expr.values[0], ast.UnaryOp)
        and isinstance(abl_expr.values[0].op, ast.Not)
        and isinstance(abl_expr.values[0].operand, ast.Name)
        and abl_expr.values[0].operand.id == "_BT_OPTIMISTIC"
        and _is_env_eq_one(abl_expr.values[1], "BT_ABLATE_BE_TRAIL")
    ), (
        f"{engine}: _BT_ABLATE_BE_TRAIL が canonical 形 "
        f"`(not _BT_OPTIMISTIC) or (env == \"1\")` でない — "
        f"default ablated / ablation 優先の保証が崩れる")


# ── 2. cache 無効化 pin (stale cache 防止) ────────────────────────────


@pytest.mark.parametrize("engine", [app.run_scalp_backtest,
                                    app.run_daytrade_backtest,
                                    app.run_1h_backtest],
                         ids=lambda f: f.__name__)
def test_keyed_caches_embed_ablation_flags(engine):
    """keyed cache の cache_key 構築部が BE/Trail 両フラグを含むこと。
    落とすと BT_OPTIMISTIC 切替時に stale 結果が返る (A/B 比較汚染)。"""
    src = inspect.getsource(engine)
    # cache-key 構築 preamble (= 最初の cache lookup より前) を対象にする。
    # scalp/1h は `_abl_flag = f"...{env}..."` を挟んで cache_key が参照する形、
    # daytrade は cache_key f-string に直接 env を埋める形 — どちらも許容。
    key_region = src.split("cached = ", 1)[0]
    assert "cache_key = " in key_region, (
        f"{engine.__name__}: cache_key 構築が cache lookup より前にない")
    key_stmt = key_region.split("cache_key = ", 1)[1]
    assert "_abl" in key_stmt, (
        f"{engine.__name__}: cache_key に ablation フラグ成分 (_abl…) がない")
    for env_name in ("BT_OPTIMISTIC", "BT_ABLATE_BE_TRAIL"):
        assert env_name in key_region, (
            f"{engine.__name__}: cache_key が {env_name} を反映していない")


def test_run_backtest_unkeyed_cache_checks_ablation_flags():
    """run_backtest の keyless `_bt_cache` はフラグ照合 + 保存の両方が必要。"""
    src = inspect.getsource(app.run_backtest)
    assert '_bt_cache.get("abl")' in src, (
        "run_backtest: cache hit 判定に ablation フラグ照合がない")
    assert re.search(r'_bt_cache\["abl"\]\s*=', src), (
        "run_backtest: cache 保存時に ablation フラグを tag していない")
    # 照合値の構築が両 env を見ていること
    flag_region = src.split("_abl_flag = ", 1)[1].split("\n", 1)[0]
    assert "BT_OPTIMISTIC" in flag_region
    assert "BT_ABLATE_BE_TRAIL" in flag_region


# ── 3. P1-2b: 同一バー TP+SL 同時ヒット tie-break pin ────────────────

_ALL_INTRADAY_ENGINES = [
    app.run_backtest,
    app.run_scalp_backtest,
    app.run_daytrade_backtest,
    app.run_1h_backtest,
]


@pytest.mark.parametrize("engine", _ALL_INTRADAY_ENGINES,
                         ids=lambda f: f.__name__)
def test_same_bar_tp_sl_tie_break_uses_fut_close(engine):
    """同一バー TP+SL 同時ヒットは fut_close で解決する (daytrade 参照
    パターン、2026-07-09 検証で 4 エンジン既装を確認)。無条件 TP 優先
    (さらに楽観) への退行を封鎖する。"""
    src_lines = inspect.getsource(engine).splitlines()
    tie_break_sites = [i for i, line in enumerate(src_lines)
                       if "if hit_tp and hit_sl:" in line]
    assert len(tie_break_sites) == 2, (
        f"{engine.__name__}: BUY+SELL の tie-break 2 箇所が前提 "
        f"(found {len(tie_break_sites)})")
    for i in tie_break_sites:
        window = "\n".join(src_lines[i + 1:i + 3])
        assert "fut_close" in window, (
            f"{engine.__name__}: 同一バー TP+SL tie-break が fut_close を"
            f"参照していない:\n{window}")


def test_swing_engine_keeps_conservative_sl_priority_tie_break():
    """run_swing_backtest は両ヒット=LOSS (保守的 SL 優先) — fut_close より
    さらに厳格。TP 優先への退行を封鎖。"""
    src = inspect.getsource(app.run_swing_backtest)
    assert re.search(
        r"if hit_tp and hit_sl:\s*\n\s+outcome = \"LOSS\"", src), (
        "run_swing_backtest の同一バー tie-break は SL 優先 (LOSS) を維持すべき")
