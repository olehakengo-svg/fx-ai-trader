#!/usr/bin/env python3
"""
FX AI Trader 開発ハーネス — 整合性チェッカー v1.0

実行: python3 scripts/check.py [--quiet]

検証内容:
  1. strategies/daytrade/__init__.py インポート → ファイル存在確認
  2. strategies/scalp/__init__.py インポート → ファイル存在確認
  3. 全DT戦略ファイルの name → QUALIFIED_TYPES (demo_trader.py) 同期
  4. 全DT戦略ファイルの name → DT_QUALIFIED (app.py) 同期
  5. 全Scalp戦略ファイルの name → QUALIFIED_TYPES 同期

新しい戦略を追加したら以下の4箇所を必ず更新すること:
  1. strategies/daytrade/__init__.py  (import + DaytradeEngine.strategies)
  2. modules/demo_trader.py QUALIFIED_TYPES
  3. modules/demo_trader.py _UNIVERSAL_SENTINEL  (Sentinel戦略の場合)
  4. app.py DT_QUALIFIED
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_TRADER = ROOT / "modules" / "demo_trader.py"
APP_PY = ROOT / "app.py"
DT_INIT = ROOT / "strategies" / "daytrade" / "__init__.py"
DT_DIR = ROOT / "strategies" / "daytrade"
SCALP_INIT = ROOT / "strategies" / "scalp" / "__init__.py"
SCALP_DIR = ROOT / "strategies" / "scalp"

QUIET = "--quiet" in sys.argv or "-q" in sys.argv


def extract_set(filepath: Path, var_name: str) -> tuple[set, str | None]:
    """変数名 = { "a", "b", ... } を正規表現で抽出。"""
    text = filepath.read_text(encoding="utf-8")
    # Handle multiline sets — capture everything between the first { and its matching }
    pattern = rf'{re.escape(var_name)}\s*=\s*\{{'
    m = re.search(pattern, text)
    if not m:
        return set(), f"{var_name} not found in {filepath.name}"
    start = m.end() - 1  # position of '{'
    depth = 0
    i = start
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                break
    block = text[start:i + 1]
    names = set(re.findall(r'"([^"]+)"', block))
    return names, None


def check_imports(init_file: Path, strategy_dir: Path) -> list[str]:
    """__init__.py の from ... import X が実ファイルとして存在するか確認。"""
    text = init_file.read_text(encoding="utf-8")
    pattern = r'from\s+strategies\.\w+\.(\w+)\s+import\s+(\w+)'
    errors = []
    for module_name, class_name in re.findall(pattern, text):
        filepath = strategy_dir / f"{module_name}.py"
        if not filepath.exists():
            errors.append(f"  ❌ 未存在: {strategy_dir.name}/{module_name}.py  (import {class_name} in __init__.py)")
    return errors


def get_strategy_attrs(strategy_dir: Path) -> list[dict]:
    """戦略ファイルから name / enabled を抽出。"""
    results = []
    for py_file in sorted(strategy_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        text = py_file.read_text(encoding="utf-8")
        name_m = re.search(r'^\s+name\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
        if not name_m:
            continue
        enabled_m = re.search(r'^\s+enabled\s*=\s*(True|False)', text, re.MULTILINE)
        enabled = enabled_m.group(1) == "True" if enabled_m else True
        results.append({
            "file": py_file.name,
            "name": name_m.group(1),
            "enabled": enabled,
        })
    return results


def section(title: str):
    if not QUIET:
        print(f"\n[{'●'}] {title}")


def ok(msg: str):
    if not QUIET:
        print(f"  ✅ {msg}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    ok_count = 0

    if not QUIET:
        print("🔍 FX AI Trader 整合性チェッカー")
        print("=" * 58)

    # ── 1. DT __init__.py インポート解決 ──
    section("DT strategies/__init__.py インポート解決")
    if DT_INIT.exists():
        imp_errors = check_imports(DT_INIT, DT_DIR)
        if imp_errors:
            errors.extend(imp_errors)
        else:
            n = len(re.findall(r'from strategies\.daytrade\.\w+ import', DT_INIT.read_text()))
            ok(f"{n} imports 全て解決済み")
            ok_count += 1
    else:
        warnings.append(f"  ⚠️  {DT_INIT} が見つかりません")

    # ── 2. Scalp __init__.py インポート解決 ──
    section("Scalp strategies/__init__.py インポート解決")
    if SCALP_INIT.exists():
        imp_errors = check_imports(SCALP_INIT, SCALP_DIR)
        if imp_errors:
            errors.extend(imp_errors)
        else:
            n = len(re.findall(r'from strategies\.scalp\.\w+ import', SCALP_INIT.read_text()))
            ok(f"{n} imports 全て解決済み")
            ok_count += 1
    else:
        warnings.append("  ⚠️  strategies/scalp/__init__.py が見つかりません")

    # ── 3. DT戦略名 → QUALIFIED_TYPES ──
    section("DT戦略名 → demo_trader.py QUALIFIED_TYPES")
    qualified, qt_err = extract_set(DEMO_TRADER, "QUALIFIED_TYPES")
    if qt_err:
        errors.append(f"  ❌ {qt_err}")
    else:
        dt_attrs = get_strategy_attrs(DT_DIR)
        missing_enabled = []
        missing_disabled = []
        for attr in dt_attrs:
            if attr["name"] not in qualified:
                if attr["enabled"]:
                    missing_enabled.append(attr)
                else:
                    missing_disabled.append(attr)
        if missing_enabled:
            for a in missing_enabled:
                errors.append(f"  ❌ '{a['name']}' ({a['file']}) → QUALIFIED_TYPES 未登録 (enabled=True)")
        if missing_disabled:
            for a in missing_disabled:
                warnings.append(f"  ⚠️  '{a['name']}' ({a['file']}) → QUALIFIED_TYPES 未登録 (enabled=False — 有効化時に要追加)")
        if not missing_enabled:
            ok(f"{len(dt_attrs)} DT戦略 全て登録済み")
            ok_count += 1

    # ── 4. DT戦略名 → app.py DT_QUALIFIED ──
    section("DT戦略名 → app.py DT_QUALIFIED (BT同期)")
    dt_qualified, dq_err = extract_set(APP_PY, "DT_QUALIFIED")
    if dq_err:
        warnings.append(f"  ⚠️  {dq_err}")
    else:
        dt_attrs = get_strategy_attrs(DT_DIR)
        missing_enabled = []
        for attr in dt_attrs:
            if attr["enabled"] and attr["name"] not in dt_qualified:
                missing_enabled.append(attr)
        if missing_enabled:
            for a in missing_enabled:
                errors.append(f"  ❌ '{a['name']}' ({a['file']}) → DT_QUALIFIED 未登録 (app.py BT同期漏れ)")
        else:
            ok(f"{len(dt_qualified)} エントリー, 全有効戦略を包含")
            ok_count += 1

    # ── 5. Scalp戦略名 → QUALIFIED_TYPES ──
    section("Scalp戦略名 → demo_trader.py QUALIFIED_TYPES")
    if SCALP_DIR.exists() and qualified:
        scalp_attrs = get_strategy_attrs(SCALP_DIR)
        missing_enabled = []
        for attr in scalp_attrs:
            if attr["enabled"] and attr["name"] not in qualified:
                missing_enabled.append(attr)
        if missing_enabled:
            for a in missing_enabled:
                errors.append(f"  ❌ '{a['name']}' ({a['file']}) → QUALIFIED_TYPES 未登録 (enabled=True)")
        else:
            ok(f"{len(scalp_attrs)} Scalp戦略 全て登録済み")
            ok_count += 1

    # ── Summary ──
    if not QUIET:
        print("\n" + "=" * 58)

    if errors:
        if QUIET:
            print(f"❌ {len(errors)} 整合性エラー:")
        else:
            print(f"❌ {len(errors)} エラー検出:")
        for e in errors:
            print(e)
        for w in warnings:
            print(w)
        return 1

    if warnings and not QUIET:
        for w in warnings:
            print(w)

    msg = f"✅ 全{ok_count}チェック通過 — 整合性OK"
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
