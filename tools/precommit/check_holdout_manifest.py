#!/usr/bin/env python3
"""Pre-commit checks for HIP-1 holdout isolation files."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


MANIFEST_PATH = Path("data/_holdout_locked/MANIFEST.json")
VALIDATION_MARKER = "HOLDOUT VALIDATION MODE"


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def _staged_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _recent_final_reports(repo_root: Path) -> list[Path]:
    runs_dir = repo_root / ".ai" / "runs"
    if not runs_dir.exists():
        return []
    return sorted(
        runs_dir.glob("*/final.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:5]


def _has_validation_marker(path: Path) -> bool:
    try:
        return VALIDATION_MARKER in path.read_text(encoding="utf-8")
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reject unapproved HIP-1 holdout manifest and validation edits."
    )
    parser.add_argument("files", nargs="*", help="Files supplied by pre-commit.")
    parser.add_argument(
        "--allow-holdout-edit",
        action="store_true",
        help="Allow deliberate edits to data/_holdout_locked/MANIFEST.json.",
    )
    parser.add_argument(
        "--allow-validation-mode",
        action="store_true",
        help="Allow committing a recent run report containing validation-mode output.",
    )
    args = parser.parse_args()

    repo_root = _repo_root()
    files = [Path(f) for f in args.files] if args.files else _staged_files()
    normalized = {Path(os.path.normpath(str(path))) for path in files}

    failed = False
    if MANIFEST_PATH in normalized and not args.allow_holdout_edit:
        print(
            "HOLDOUT manifest edit rejected: rerun with --allow-holdout-edit "
            "after Claude manual approval.",
            file=sys.stderr,
        )
        failed = True

    if not args.allow_validation_mode:
        marked_reports = [
            path for path in _recent_final_reports(repo_root) if _has_validation_marker(path)
        ]
        if marked_reports:
            print(
                "HOLDOUT validation-mode report detected; Claude manual approval "
                "is required before commit.",
                file=sys.stderr,
            )
            for path in marked_reports:
                print(f"  - {path.relative_to(repo_root)}", file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
