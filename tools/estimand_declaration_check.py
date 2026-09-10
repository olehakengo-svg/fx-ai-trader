#!/usr/bin/env python3
"""estimand 宣言表の schema + 配線チェッカー (rule:R3, 2026-09-10).

対象: ``monitoring/estimand_declarations.yml``
根拠: knowledge-base/wiki/decisions/process-meta-audit-2026-09-07.md §4.2 R3
説明: knowledge-base/wiki/analyses/estimand-declaration-system-2026-09-10.md

検証内容:
    (a) schema — 必須フィールドの存在・型・値域 (clock は wall|market_open)、
        name の一意性、未知キーの拒否 (typo を黙って通さない)
    (b) 配線 — ``reader`` に書かれたファイルが実在し、宣言された検索文字列を
        実際に含むか (grep レベル)。``threshold_source`` / ``detector`` の
        パスとシンボルも同様に検証する
    (c) ``counterfactual_test`` のパスが実在するか。"MISSING" は WARN として
        列挙する (exit 0)。``--strict`` 時のみ WARN でも exit 1

なぜ自前パーサか — PyYAML は requirements.txt に無く、監視チェッカーのために
本番 web service のビルド依存を増やすのは本末転倒 (デプロイ churn 教訓)。
宣言表は本プロジェクトが書式を所有するファイルなので、厳格なサブセット
(タブ禁止 / 1 行スカラーのみ / 固定インデント) を定義し、逸脱は**黙って
読み飛ばさずに ParseError で落とす** — 「読めないものを読めたことにする」のは
本チェッカーが検出しようとしている欠陥そのものである。

設計原則 (lessons 準拠):
    - モジュールトップの副作用なし (os.environ / parse_args / chdir 禁止)
    - 判定は純関数 (check_declarations) — テストはデータ注入で行う
    - ERROR (配線破れ) と WARN (counterfactual 未整備) を折り畳まない

使用:
    python3 tools/estimand_declaration_check.py             # 検証 (WARN は exit 0)
    python3 tools/estimand_declaration_check.py --strict    # WARN も exit 1
    python3 tools/estimand_declaration_check.py --json      # machine-readable
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DECLARATIONS = "monitoring/estimand_declarations.yml"

VALID_CLOCKS = ("wall", "market_open")
READER_SEPARATOR = " :: "
ON_DEMAND = "ON_DEMAND"
MISSING = "MISSING"

REQUIRED_KEYS = (
    "name",
    "claims",
    "population",
    "clock",
    "threshold_source",
    "reader",
    "counterfactual_test",
)
OPTIONAL_KEYS = ("detector", "notes")

_NAME_RE = re.compile(r"^[a-z0-9_]+$")
# "パス:シンボル" の右側として妥当な Python 識別子 (パス断片と区別する)
_SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ParseError(ValueError):
    """宣言表がサブセット文法から逸脱している。黙って読み飛ばさない。"""


# ── restricted YAML パーサ ──────────────────────────────────────────────
#
# 文法 (宣言表ヘッダに同じ定義を記載):
#   indent 0: `key: value` / `series:`
#   indent 2: `- key: value`          … series の新項目
#   indent 4: `key: value` / `key:`   … 項目のフィールド / リスト開始
#   indent 6: `- value`               … リスト要素 (文字列のみ)
# 値は 1 行スカラーのみ。両端が `"` なら剥がす。タブ・行内コメントは禁止。

def _scalar(raw: str, lineno: int) -> str:
    value = raw.strip()
    if value.startswith('"'):
        if not value.endswith('"') or len(value) < 2:
            raise ParseError(f"line {lineno}: 閉じ引用符が無い: {raw!r}")
        return value[1:-1]
    return value


def _split_key(line: str, lineno: int) -> tuple[str, str]:
    if ":" not in line:
        raise ParseError(f"line {lineno}: `key: value` 形式でない: {line!r}")
    key, _, rest = line.partition(":")
    key = key.strip()
    if not key:
        raise ParseError(f"line {lineno}: 空のキー: {line!r}")
    return key, rest


def parse_declarations_text(text: str) -> dict[str, Any]:
    """宣言表テキストを dict に。文法逸脱は ParseError。"""
    doc: dict[str, Any] = {}
    series: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    pending_list_key: str | None = None
    in_series = False

    for lineno, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw:
            raise ParseError(f"line {lineno}: タブ文字は禁止")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw) - len(raw.lstrip(" "))

        if indent == 0:
            in_series = False
            pending_list_key = None
            current = None
            key, rest = _split_key(stripped, lineno)
            if key == "series":
                if rest.strip():
                    raise ParseError(f"line {lineno}: `series:` に行内の値は書けない")
                in_series = True
                doc["series"] = series
            else:
                if not rest.strip():
                    raise ParseError(f"line {lineno}: トップレベル `{key}:` に値が無い")
                doc[key] = _scalar(rest, lineno)
            continue

        if not in_series:
            raise ParseError(f"line {lineno}: series 外のインデント行: {raw!r}")

        if indent == 2:
            if not stripped.startswith("- "):
                raise ParseError(f"line {lineno}: series 項目は `- key: value` で始める")
            pending_list_key = None
            current = {}
            series.append(current)
            key, rest = _split_key(stripped[2:], lineno)
            current[key] = _scalar(rest, lineno)
            continue

        if indent == 4:
            if current is None:
                raise ParseError(f"line {lineno}: 項目開始 (`- `) より前のフィールド")
            pending_list_key = None
            key, rest = _split_key(stripped, lineno)
            if key in current:
                raise ParseError(f"line {lineno}: フィールド重複: {key!r}")
            if rest.strip():
                current[key] = _scalar(rest, lineno)
            else:
                current[key] = []
                pending_list_key = key
            continue

        if indent == 6:
            if current is None or pending_list_key is None:
                raise ParseError(f"line {lineno}: リスト開始 (`key:`) の外のリスト要素")
            if not stripped.startswith("- "):
                raise ParseError(f"line {lineno}: リスト要素は `- value` 形式")
            current[pending_list_key].append(_scalar(stripped[2:], lineno))
            continue

        raise ParseError(f"line {lineno}: 不正なインデント {indent} (0/2/4/6 のみ)")

    return doc


def load_declarations(path: Path) -> dict[str, Any]:
    return parse_declarations_text(path.read_text(encoding="utf-8"))


# ── 検証 (純関数) ───────────────────────────────────────────────────────

def _split_path_symbol(value: str) -> tuple[str, str | None]:
    """"パス[:シンボル]" を分解。右端の要素が識別子形のときだけシンボル扱い。"""
    if ":" in value:
        path_part, _, symbol = value.rpartition(":")
        if path_part and _SYMBOL_RE.match(symbol):
            return path_part, symbol
    return value, None


def _check_source_ref(
    kind: str, name: str, value: Any, root: Path, errors: list[str]
) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{name}: {kind} が空/非文字列")
        return
    path_part, symbol = _split_path_symbol(value)
    target = root / path_part
    if not target.is_file():
        errors.append(f"{name}: {kind} のファイルが実在しない: {path_part}")
        return
    if symbol is not None:
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"{name}: {kind} が読めない: {path_part} ({exc})")
            return
        if symbol not in content:
            errors.append(
                f"{name}: {kind} のシンボル {symbol!r} が {path_part} に見当たらない"
            )


def _check_reader(
    name: str, reader: Any, root: Path, errors: list[str], warns: list[str]
) -> None:
    if reader == ON_DEMAND:
        warns.append(f"{name}: reader=ON_DEMAND — 自動読み手なし (write-only 候補)")
        return
    if not isinstance(reader, list) or not reader:
        errors.append(
            f"{name}: reader は非空リストか {ON_DEMAND!r} でなければならない"
        )
        return
    for entry in reader:
        if not isinstance(entry, str) or READER_SEPARATOR not in entry:
            errors.append(
                f"{name}: reader 要素は 'パス{READER_SEPARATOR}検索文字列' 形式: {entry!r}"
            )
            continue
        file_part, _, expects = entry.partition(READER_SEPARATOR)
        file_part = file_part.strip()
        expects = expects.strip()
        if not file_part or not expects:
            errors.append(f"{name}: reader 要素のパス/検索文字列が空: {entry!r}")
            continue
        target = root / file_part
        if not target.is_file():
            errors.append(f"{name}: reader ファイルが実在しない: {file_part}")
            continue
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"{name}: reader ファイルが読めない: {file_part} ({exc})")
            continue
        if expects not in content:
            errors.append(
                f"{name}: reader {file_part} が {expects!r} を参照していない (配線切れの疑い)"
            )


def _check_counterfactual(
    name: str, value: Any, root: Path, errors: list[str], warns: list[str]
) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{name}: counterfactual_test が空/非文字列")
        return
    if value == MISSING:
        warns.append(f"{name}: counterfactual_test MISSING — 配線 kill で落ちるテスト未整備")
        return
    # pytest セレクタ (path::TestClass::test) を許容 — 実在検証はパス部のみ
    path_part = value.split("::", 1)[0]
    if not (root / path_part).is_file():
        errors.append(f"{name}: counterfactual_test のパスが実在しない: {path_part}")


def check_declarations(
    doc: dict[str, Any], root: Path | None = None
) -> tuple[list[str], list[str]]:
    """(errors, warns) を返す。ERROR = 配線/schema 破れ、WARN = 既知の負債。"""
    root = root or ROOT
    errors: list[str] = []
    warns: list[str] = []

    if str(doc.get("version", "")).strip() == "":
        errors.append("top-level: version が無い")
    series = doc.get("series")
    if not isinstance(series, list) or not series:
        errors.append("top-level: series が空 (宣言ゼロの表は表ではない)")
        return errors, warns

    seen: set[str] = set()
    for i, item in enumerate(series):
        if not isinstance(item, dict):
            errors.append(f"series[{i}]: mapping でない")
            continue
        name = str(item.get("name") or f"series[{i}]")

        for key in REQUIRED_KEYS:
            if key not in item:
                errors.append(f"{name}: 必須フィールド {key!r} が無い")
        for key in item:
            if key not in REQUIRED_KEYS and key not in OPTIONAL_KEYS:
                errors.append(f"{name}: 未知のフィールド {key!r} (typo?)")

        raw_name = item.get("name")
        if not isinstance(raw_name, str) or not _NAME_RE.match(raw_name):
            errors.append(f"{name}: name は [a-z0-9_]+ でなければならない: {raw_name!r}")
        elif raw_name in seen:
            errors.append(f"{name}: name 重複")
        else:
            seen.add(raw_name)

        for key in ("claims", "population"):
            value = item.get(key)
            if key in item and (not isinstance(value, str) or not value.strip()):
                errors.append(f"{name}: {key} が空 — 名乗る量を書かない宣言は無意味")

        clock = item.get("clock")
        if "clock" in item and clock not in VALID_CLOCKS:
            errors.append(
                f"{name}: clock は {VALID_CLOCKS} のどれか (取り違えは PR #207/#209 の実績あり): {clock!r}"
            )

        if "threshold_source" in item:
            _check_source_ref("threshold_source", name, item["threshold_source"], root, errors)
        if "detector" in item:
            _check_source_ref("detector", name, item["detector"], root, errors)
        if "reader" in item:
            _check_reader(name, item["reader"], root, errors, warns)
        if "counterfactual_test" in item:
            _check_counterfactual(name, item["counterfactual_test"], root, errors, warns)

    return errors, warns


# ── CLI ─────────────────────────────────────────────────────────────────

def run_check(
    declarations_path: Path, root: Path, *, strict: bool = False
) -> tuple[int, dict[str, Any]]:
    """チェックを実行し (exit_code, report) を返す。I/O 例外も ERROR に畳む。"""
    try:
        doc = load_declarations(declarations_path)
    except (OSError, ParseError) as exc:
        report = {
            "declarations": str(declarations_path),
            "errors": [f"宣言表が読めない: {type(exc).__name__}: {exc}"],
            "warnings": [],
            "n_series": 0,
        }
        return 1, report

    errors, warns = check_declarations(doc, root)
    report = {
        "declarations": str(declarations_path),
        "n_series": len(doc.get("series") or []),
        "errors": errors,
        "warnings": warns,
    }
    if errors:
        return 1, report
    if strict and warns:
        return 1, report
    return 0, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="estimand 宣言表の schema + 配線チェック")
    parser.add_argument(
        "--file",
        default=None,
        help=f"宣言表のパス (default: <repo>/{DEFAULT_DECLARATIONS})",
    )
    parser.add_argument("--root", default=None, help="リポジトリルート (default: 自動)")
    parser.add_argument(
        "--strict", action="store_true",
        help="WARN (counterfactual MISSING / ON_DEMAND reader) でも exit 1",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable 出力")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else ROOT
    declarations_path = (
        Path(args.file).resolve() if args.file else root / DEFAULT_DECLARATIONS
    )

    code, report = run_check(declarations_path, root, strict=args.strict)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return code

    print(f"estimand declarations: {report['declarations']}")
    print(f"series declared: {report['n_series']}")
    for e in report["errors"]:
        print(f"ERROR: {e}")
    for w in report["warnings"]:
        print(f"WARN:  {w}")
    if not report["errors"]:
        print("wiring: OK" + (" (strict: WARN=fail)" if args.strict else ""))
    print(
        f"result: {len(report['errors'])} error(s), {len(report['warnings'])} warning(s)"
        f" → exit {code}"
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
