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
import subprocess
import sys
from datetime import date
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


KB_WIKI = ROOT / "knowledge-base" / "wiki"
KB_ROOT = ROOT / "knowledge-base"


def check_kb_consistency() -> tuple[list[str], list[str]]:
    """KBの整合性を軽量チェック（バージョン/Edge Stage/セッション同期）。"""
    errors: list[str] = []
    warns: list[str] = []

    changelog = KB_WIKI / "changelog.md"
    index = KB_WIKI / "index.md"

    # ── 6a. changelog最新バージョン vs index.md 見出しバージョン ──
    if changelog.exists() and index.exists():
        cl_text = changelog.read_text(encoding="utf-8")
        idx_text = index.read_text(encoding="utf-8")
        # changelogの最新バージョンをパース
        cl_versions = re.findall(r'v(\d+\.\d+)', cl_text)
        latest_cl = max(cl_versions, key=lambda v: float(v)) if cl_versions else None
        if latest_cl:
            # index.mdの見出し行からバージョンを個別チェック
            portfolio_m = re.search(r'## Current Portfolio \(v([\d.]+)', idx_text)
            state_m = re.search(r'## System State \(v([\d.]+)', idx_text)
            if portfolio_m and float(portfolio_m.group(1)) < float(latest_cl):
                warns.append(
                    f"  ⚠️  KB: index.md Portfolio=v{portfolio_m.group(1)}"
                    f" < changelog=v{latest_cl} — 見出し更新漏れ"
                )
            if state_m and float(state_m.group(1)) < float(latest_cl):
                warns.append(
                    f"  ⚠️  KB: index.md System State=v{state_m.group(1)}"
                    f" < changelog=v{latest_cl} — 見出し更新漏れ"
                )

    # ── 6b. 破損wikilinkチェック ──
    broken_links: list[str] = []
    if KB_ROOT.exists():
        all_md_stems = set()
        all_md_paths = set()
        for md_file in KB_ROOT.rglob("*.md"):
            all_md_stems.add(md_file.stem)
            rel = str(md_file.relative_to(KB_ROOT).with_suffix("")).replace("\\", "/")
            all_md_paths.add(rel)

        def link_resolves(link: str) -> bool:
            """Obsidian互換: ファイル名一致 or パス末尾一致で解決。"""
            if link in all_md_stems:
                return True
            return any(p == link or p.endswith("/" + link) for p in all_md_paths)

        for md_file in KB_ROOT.rglob("*.md"):
            text = md_file.read_text(encoding="utf-8")
            links = re.findall(r'\[\[([^\]|#]+)', text)
            for link in links:
                link_clean = link.strip()
                if not link_resolves(link_clean):
                    broken_links.append(f"{md_file.relative_to(KB_ROOT)}→[[{link_clean}]]")

    if broken_links:
        sample = broken_links[:5]
        warns.append(
            f"  ⚠️  KB: 破損wikilink {len(broken_links)}件"
            f" (例: {', '.join(sample)})"
        )

    # ── 6c. セッションログの未解決事項数 ──
    sessions_dir = KB_WIKI / "sessions"
    if sessions_dir.exists():
        session_files = sorted(sessions_dir.glob("*.md"), reverse=True)
        if session_files:
            latest = session_files[0]
            text = latest.read_text(encoding="utf-8")
            open_items = len(re.findall(r'^- \[ \]', text, re.MULTILINE))
            if open_items > 0 and not QUIET:
                warns.append(
                    f"  ℹ️  KB: {latest.name} に未解決事項 {open_items}件"
                )

    # ── 6d. Edge Stage不整合: edge-pipeline.md vs 各edge/*.md ──
    pipeline_file = KB_WIKI / "edges" / "edge-pipeline.md"
    edges_dir = KB_WIKI / "edges"
    if pipeline_file.exists() and edges_dir.exists():
        pl_text = pipeline_file.read_text(encoding="utf-8")
        # edge-pipeline.mdのテーブルからエッジ名→Stageを抽出
        # Stage 6: PROMOTED テーブル、Stage 4: SENTINEL テーブルを解析
        pipeline_stages: dict[str, str] = {}
        # "Stage 6: PROMOTED" セクション
        s6_block = re.search(
            r'### Stage 6: PROMOTED\s*\n\|.*\n\|[-|]+\n((?:\|.*\n)*)', pl_text
        )
        if s6_block:
            for row in re.findall(r'\[\[([^\]]+)\]\]', s6_block.group(1)):
                pipeline_stages[row] = "PROMOTED"
        # "Stage 4: SENTINEL" セクション
        s4_block = re.search(
            r'### Stage 4: SENTINEL\s*\n\|.*\n\|[-|]+\n((?:\|.*\n)*)', pl_text
        )
        if s4_block:
            for row in re.findall(r'\[\[([^\]]+)\]\]', s4_block.group(1)):
                if row not in pipeline_stages:
                    pipeline_stages[row] = "SENTINEL"

        # 各edge/*.mdのStage行と突合
        stage_mismatches: list[str] = []
        for edge_file in sorted(edges_dir.glob("*.md")):
            if edge_file.name in ("edge-pipeline.md", "raw-alpha-mining-2026-04-12.md"):
                continue
            stem = edge_file.stem
            edge_text = edge_file.read_text(encoding="utf-8")
            # "## Stage: XXX" 行を探す
            stage_m = re.search(r'^## Stage:\s*(.+)', edge_text, re.MULTILINE)
            if not stage_m:
                # "**Stage**: N (XXX)" 形式も試行
                stage_m = re.search(r'\*\*Stage\*\*:\s*\d+\s*\((\w+)\)', edge_text)
            if not stage_m:
                continue
            file_stage = stage_m.group(1).strip().upper()
            # edge-pipeline.mdでの期待Stage
            expected = pipeline_stages.get(stem)
            if expected and expected not in file_stage:
                stage_mismatches.append(f"{stem}: file={file_stage} vs pipeline={expected}")

        if stage_mismatches:
            sample = stage_mismatches[:5]
            warns.append(
                f"  ⚠️  KB: Edge Stage不整合 {len(stage_mismatches)}件"
                f" ({', '.join(sample)})"
            )

    # ── 6e. Session log完成度: git commit数 vs session logコミット一覧 ──
    today_str = date.today().isoformat()
    session_today = sessions_dir / f"{today_str}-session.md" if sessions_dir.exists() else None
    if session_today and session_today.exists():
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", f"--since={today_str}"],
                capture_output=True, text=True, timeout=10, cwd=ROOT,
            )
            git_count = len(result.stdout.strip().splitlines()) if result.stdout.strip() else 0
            # session logから最後の「コミット一覧」セクションを探す
            s_text = session_today.read_text(encoding="utf-8")
            commit_sections = list(re.finditer(r'##\s*コミット一覧', s_text))
            if commit_sections and git_count > 0:
                last_section = s_text[commit_sections[-1].end():]
                # 次の ## までのテキストを取得
                next_h2 = re.search(r'\n## ', last_section)
                if next_h2:
                    last_section = last_section[:next_h2.start()]
                log_count = len(re.findall(r'^\d+\.', last_section, re.MULTILINE))
                if git_count > log_count:
                    warns.append(
                        f"  ⚠️  KB: session log コミット漏れ"
                        f" (git={git_count} vs log={log_count})"
                    )
        except Exception:
            pass  # git実行失敗時はスキップ

    # ── 6f. index.md Session History に最新セッションのリンクがあるか ──
    if index.exists() and sessions_dir and sessions_dir.exists():
        session_files = sorted(sessions_dir.glob("*.md"), reverse=True)
        if session_files:
            newest_session = session_files[0].stem  # e.g. "2026-04-13-session"
            idx_text = index.read_text(encoding="utf-8")
            history_m = re.search(r'## Session History\s*\n(.*?)(?:\n## |\Z)',
                                  idx_text, re.DOTALL)
            if history_m:
                if newest_session not in history_m.group(1):
                    warns.append(
                        f"  ⚠️  KB: index.md Session History に"
                        f" [[{newest_session}]] が未リンク"
                    )

    return errors, warns


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

    # ── 6. KB整合性チェック ──
    section("KB整合性チェック")
    kb_errors, kb_warns = check_kb_consistency()
    errors.extend(kb_errors)
    warnings.extend(kb_warns)
    if not kb_errors:
        ok("KB整合性OK")
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
