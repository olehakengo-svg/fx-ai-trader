#!/usr/bin/env python3
from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path


PNL_FUNCTION_NAMES = {
    "extract_trade_pnl",
    "_pnl",
    "normalize_trade",
    "pf_from_pnls",
    "small_stats",
}
LOCKED_CONSTANT_PREFIXES = (
    "BONFERRONI_",
    "VERDICT_THRESHOLDS",
    "CANDIDATES",
    "PAIR_BEV_WR",
)


def _normalized_function_text(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    normalized = copy.deepcopy(node)
    if (
        normalized.body
        and isinstance(normalized.body[0], ast.Expr)
        and isinstance(normalized.body[0].value, ast.Constant)
        and isinstance(normalized.body[0].value.value, str)
    ):
        normalized.body = normalized.body[1:]
    return ast.unparse(normalized)


def _assignment_names(node: ast.Assign | ast.AnnAssign) -> list[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return [target.id for target in targets if isinstance(target, ast.Name)]


def _is_locked_constant(name: str) -> bool:
    return name.startswith(LOCKED_CONSTANT_PREFIXES)


def compute_wrapper_fingerprint(module_path: str | Path) -> str:
    path = Path(module_path)
    tree = ast.parse(path.read_text(), filename=str(path))
    parts: list[str] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in PNL_FUNCTION_NAMES:
            parts.append(f"func:{node.name}={_normalized_function_text(node)}")

    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if value is None:
                continue
            for name in _assignment_names(node):
                if _is_locked_constant(name):
                    parts.append(f"const:{name}={repr(ast.unparse(value))}")

    if not parts:
        raise ValueError(f"no fingerprintable BT wrapper logic found in {path}")

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
