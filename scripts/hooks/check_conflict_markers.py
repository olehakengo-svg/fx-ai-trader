#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Staged ファイルの行頭 git conflict マーカー検査 (pre-commit 用、rule:R3 2026-10-22)。

背景: 2026-10-20 PR #338 で conflict 解決スクリプトが本文中の `<<<<<<<` (過去事故の記述)
に部分文字列 assert で誤反応して停止 → マーカー入りの changelog を `git add` → pre-commit
を素通り → push。検査は **行頭アンカー** (`^<<<<<<< ` / `^=======$` / `^>>>>>>> `) で行い、
本文中の引用 (「`<<<<<<<` を含む記述」) には反応しない。

使い方:
    git diff --cached --name-only -z --diff-filter=ACMR | python3 scripts/hooks/check_conflict_markers.py --stdin0 --index
    printf '%s\n' path1 path2 | python3 scripts/hooks/check_conflict_markers.py --stdin
    python3 scripts/hooks/check_conflict_markers.py path1 path2
    (--stdin0 = NUL 区切り: 非 ASCII / 空白を含むパスを quotePath エスケープなしで受ける。
     --index を付けると working tree でなく index の内容 `git show :path` を検査する)

終了コード: 0 = マーカーなし / 1 = 1 件以上 (stdout に `path:line: marker` を列挙) /
2 = 引数エラー。読めないファイル (binary / 不在) は skip (stderr に 1 行)。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

MARKER_RE = re.compile(r"^(<<<<<<< |=======$|>>>>>>> )")
#: 検査対象外 (バイナリ・生成物)。拡張子で粗く除外し、decode 失敗は個別 skip。
SKIP_SUFFIXES = frozenset({
    ".parquet", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".pyc",
    ".sqlite", ".db", ".pkl", ".npy", ".npz", ".ico", ".woff", ".woff2",
})


def find_markers(text: str) -> list[tuple[int, str]]:
    """テキスト中の行頭 conflict マーカーを (1-origin 行番号, 行頭 7 文字) で返す (純関数)。"""
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(text.split("\n"), start=1):
        if MARKER_RE.match(line):
            hits.append((i, line[:7]))
    return hits


def read_source(path: str, use_index: bool) -> str | None:
    """検査対象テキスト。index モードは `git show :path`、それ以外は working tree。"""
    if Path(path).suffix.lower() in SKIP_SUFFIXES:
        return None
    try:
        if use_index:
            out = subprocess.run(["git", "show", f":{path}"], capture_output=True, check=True)
            raw = out.stdout
        else:
            raw = Path(path).read_bytes()
    except (OSError, subprocess.CalledProcessError):
        return None
    if b"\x00" in raw[:8192]:
        return None  # binary
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def scan(paths: Iterable[str], use_index: bool = False) -> list[str]:
    """`path:line: marker` 形式の違反一覧 (空 = clean)。"""
    violations: list[str] = []
    for p in paths:
        if not p or not p.strip():
            continue
        # パスは字義どおりに扱う (strip しない — 空白を含むファイル名を壊さない)
        text = read_source(p, use_index)
        if text is None:
            print(f"[conflict-markers] skip (binary/unreadable): {p}", file=sys.stderr)
            continue
        for lineno, marker in find_markers(text):
            violations.append(f"{p}:{lineno}: {marker}")
    return violations


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="行頭 git conflict マーカー検査")
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--stdin", action="store_true", help="検査パスを stdin から 1 行 1 つで受ける")
    ap.add_argument("--stdin0", action="store_true",
                    help="検査パスを stdin から NUL 区切りで受ける (git diff -z、非 ASCII パス安全)")
    ap.add_argument("--index", action="store_true", help="working tree でなく index (git show :path) を検査")
    args = ap.parse_args(argv)
    paths = list(args.paths)
    if args.stdin0:
        raw = sys.stdin.buffer.read()
        paths.extend(part.decode("utf-8", "surrogateescape") for part in raw.split(b"\0"))
    elif args.stdin:
        paths.extend(sys.stdin.read().split("\n"))
    if not paths:
        return 2
    violations = scan(paths, use_index=args.index)
    if violations:
        print("[conflict-markers] 行頭 conflict マーカーが残っています (commit blocked):")
        for v in violations:
            print(f"  {v}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
