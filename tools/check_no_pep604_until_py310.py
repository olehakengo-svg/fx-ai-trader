#!/usr/bin/env python3
"""Guard Python 3.9 from runtime-evaluated PEP 604 annotations."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = (ROOT / "modules" / "demo_trader.py",)

PEP604_RE = re.compile(
    r"\b(str|int|float|bool|dict|list|tuple|set)\s*\|\s*"
    r"(None|str|int|float|bool|dict|list|tuple|set)\b"
)


def has_future_annotations(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return False

    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                continue
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            return any(alias.name == "annotations" for alias in node.names)
        return False
    return False


def iter_python_files(paths: list[str]) -> list[Path]:
    if not paths:
        return list(DEFAULT_TARGETS)

    files: list[Path] = []
    for raw in paths:
        path = (ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.exists() and path.suffix == ".py":
            files.append(path)
    return files


def code_part(line: str) -> str:
    no_comment = line.split("#", 1)[0]
    return re.sub(r"(['\"]).*?\1", "", no_comment)


def main(argv: list[str]) -> int:
    violations: list[str] = []
    for path in iter_python_files(argv):
        text = path.read_text(encoding="utf-8")
        if has_future_annotations(path):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if PEP604_RE.search(code_part(line)):
                rel = path.relative_to(ROOT)
                violations.append(f"{rel}:{lineno}: {line.strip()}")

    if violations:
        print(
            "PEP 604 builtin unions require 'from __future__ import annotations' "
            "while Python 3.9 is supported.",
            file=sys.stderr,
        )
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
