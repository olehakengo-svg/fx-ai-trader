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
FIX_MODE = "--fix" in sys.argv


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
    """__init__.py の from ... import X が実ファイルとして存在するか確認。

    Cross-directory imports (e.g. strategies.intraday.X imported from
    strategies.daytrade.__init__.py) are resolved using the captured subdir,
    not the strategy_dir passed in. 2026-06-07 fix for false positive on
    kalman_d7_v18e_jpy_cross imported across daytrade/intraday boundary.
    """
    text = init_file.read_text(encoding="utf-8")
    # Capture both subdir and module name: "strategies.<subdir>.<module>"
    pattern = r'from\s+strategies\.(\w+)\.(\w+)\s+import\s+(\w+)'
    errors = []
    strategies_root = strategy_dir.parent
    for subdir, module_name, class_name in re.findall(pattern, text):
        filepath = strategies_root / subdir / f"{module_name}.py"
        if not filepath.exists():
            errors.append(f"  ❌ 未存在: {subdir}/{module_name}.py  (import {class_name} in {init_file.parent.name}/__init__.py)")
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
            # コードブロック内のwikilinkを除外
            text_no_code = re.sub(r'```[\s\S]*?```', '', text)
            links = re.findall(r'\[\[([^\]|#]+)', text_no_code)
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

    # ── 6d. Edge Stage不整合: edge-pipeline.md vs 各strategy/*.md ──
    pipeline_file = KB_WIKI / "strategies" / "edge-pipeline.md"
    edges_dir = KB_WIKI / "strategies"
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
        # edge-pipeline.mdに記載されたエッジのみチェック（戦略ファイルはスキップ）
        edge_stems = set(pipeline_stages.keys())
        for edge_file in sorted(edges_dir.glob("*.md")):
            if edge_file.stem not in edge_stems:
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

    # ── 6f. Audit staleness: 最終audit > 14日前 ──
    audits_dir = KB_ROOT / "raw" / "audits"
    if audits_dir.exists():
        audit_files = sorted(audits_dir.glob("*.md"), reverse=True)
        if audit_files:
            # ファイル名から日付を抽出 (e.g. 2026-04-20-weekly.md)
            newest_audit_m = re.match(r'(\d{4}-\d{2}-\d{2})', audit_files[0].stem)
            if newest_audit_m:
                from datetime import timedelta
                audit_date = date.fromisoformat(newest_audit_m.group(1))
                days_since = (date.today() - audit_date).days
                if days_since > 14:
                    warns.append(
                        f"  ⚠️  KB: 最終audit {audit_files[0].name}"
                        f" ({days_since}日前) — 週次監査が遅延"
                    )
        else:
            warns.append("  ℹ️  KB: raw/audits/ にauditファイルなし（初回監査待ち）")

    # ── 6g. index.md Session History に最新セッションのリンクがあるか ──
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


AI_TASKS = ROOT / ".ai" / "tasks"
AI_RUNS = ROOT / ".ai" / "runs"

# Codexタスクのレビューゲート強制開始日 (decisions/claude-codex-division-of-labor-2026-07-02.md)
# これ以前の done 278 件は grandfather (エラーにしない)。
REVIEW_GATE_CUTOFF = "20260702"
# queue 内 R3/止血タスクの SLA (日)。超過で WARN → Claude 直接実行フォールバック。
QUEUE_SLA_DAYS = 3


def check_env_gate_declarations() -> tuple[list[str], list[str]]:
    """LIVE 例外 env gate の render.yaml 宣言整合 (rule:R3, 2026-07-06)。

    「決定はしたが provisioning されず誰も気づかない」クラスの再発防止:
      watchdog API_AUTH_TOKEN / carry dip env gate / T5 トリガー未執行の 3 例。
    modules/demo_trader.py が読む *_LIVE_ENABLE 系 env キーは render.yaml の
    envVars に宣言されていなければ WARN (値は dashboard 管理で可、宣言が必須)。
    """
    errors: list[str] = []
    warns: list[str] = []
    demo = ROOT / "modules" / "demo_trader.py"
    render_yaml = ROOT / "render.yaml"
    if not demo.exists() or not render_yaml.exists():
        return errors, ["  ⚠️  env gate check: 対象ファイル欠落 (skip)"]
    used = set(re.findall(
        r'environ\.get\(\s*"([A-Z0-9_]+_LIVE_ENABLE)"', demo.read_text()))
    declared = set(re.findall(r'-\s*key:\s*([A-Z0-9_]+)', render_yaml.read_text()))
    for key in sorted(used - declared):
        warns.append(
            f"  ⚠️  env gate '{key}' は demo_trader.py が読むが render.yaml 未宣言 "
            f"(decision-without-provisioning リスク — envVars に sync:false で宣言せよ)")
    return errors, warns


def check_ai_task_governance() -> tuple[list[str], list[str]]:
    """Codexタスク運用の機械的整合チェック (rule:R3, 2026-07-02)。

    幽霊タスク事故の再発防止:
      watchdog Bearer 修正が KB 上「Codex pending」のまま queue に実体が
      無く ~1ヶ月放置 → DD 81%→98% 悪化に寄与。「記録上やったことに
      なっている」と「実際にやった」の整合を CI で固定する。

    1. done レビューゲート: REVIEW_GATE_CUTOFF 以降の done タスクは
       .ai/runs/<run>/review.md または task md 内 `## Claude Review`
       セクション (verdict + git diff 実 verify) を必須とする → ERROR
    2. queue SLA: queue 直下のタスクがファイル名日付で QUEUE_SLA_DAYS
       日超え滞留 → WARN (Claude 直接実行にフォールバックすべき)
    3. 幽霊 pending: KB index.md が Codex pending に言及しているのに
       queue にアクティブタスクが 1 件も無い → WARN
    """
    errors: list[str] = []
    warns: list[str] = []

    done_dir = AI_TASKS / "done"
    queue_dir = AI_TASKS / "queue"

    # ── 1. done レビューゲート (cutoff 以降のみ強制) ──
    if done_dir.exists():
        run_dirs = [d.name for d in AI_RUNS.iterdir() if d.is_dir()] if AI_RUNS.exists() else []
        for task_file in sorted(done_dir.glob("*.md")):
            stem = task_file.stem
            date_m = re.match(r"(\d{8})", stem)
            if not date_m or date_m.group(1) < REVIEW_GATE_CUTOFF:
                continue  # grandfathered
            has_inline = "## Claude Review" in task_file.read_text(encoding="utf-8")
            has_run_review = any(
                stem in rd and (AI_RUNS / rd / "review.md").exists()
                for rd in run_dirs
            )
            if not (has_inline or has_run_review):
                errors.append(
                    f"  ❌ done/{task_file.name}: Claude レビュー記録なし "
                    f"(review.md か '## Claude Review' 必須 — "
                    f"decisions/claude-codex-division-of-labor-2026-07-02.md)"
                )

    # ── 2. queue SLA 滞留検出 ──
    if queue_dir.exists():
        today = date.today().strftime("%Y%m%d")
        for task_file in sorted(queue_dir.glob("*.md")):
            date_m = re.match(r"(\d{8})", task_file.stem)
            if not date_m:
                continue
            age_days = (
                date.fromisoformat(f"{today[:4]}-{today[4:6]}-{today[6:]}")
                - date.fromisoformat(
                    f"{date_m.group(1)[:4]}-{date_m.group(1)[4:6]}-{date_m.group(1)[6:]}"
                )
            ).days
            if age_days > QUEUE_SLA_DAYS:
                warns.append(
                    f"  ⚠️  queue/{task_file.name}: {age_days}日滞留 "
                    f"(SLA {QUEUE_SLA_DAYS}日超 — Claude 直接実行フォールバック検討)"
                )

    # ── 3. 幽霊 pending 検出 ──
    index = KB_WIKI / "index.md"
    if index.exists() and queue_dir.exists():
        idx_text = index.read_text(encoding="utf-8")
        pending_lines = [
            ln.strip()[:100] for ln in idx_text.splitlines()
            if re.search(r"Codex.{0,40}pending|pending.{0,40}Codex", ln, re.IGNORECASE)
        ]
        active_queue = list(queue_dir.glob("*.md"))
        if pending_lines and not active_queue:
            for ln in pending_lines[:5]:
                warns.append(
                    f"  ⚠️  幽霊タスク疑い: index.md「{ln}…」— queue にアクティブタスク 0 件 "
                    f"(実体を queue に作るか、記述を解消すること)"
                )

    return errors, warns


def fix_kb_drift() -> list[str]:
    """機械的に修正可能なKBドリフトを自動修正。修正内容のリストを返す。"""
    fixed: list[str] = []

    changelog = KB_WIKI / "changelog.md"
    index = KB_WIKI / "index.md"

    if not (changelog.exists() and index.exists()):
        return fixed

    cl_text = changelog.read_text(encoding="utf-8")
    idx_text = index.read_text(encoding="utf-8")

    # ── バージョン番号の自動修正 ──
    cl_versions = re.findall(r'v(\d+\.\d+)', cl_text)
    latest_cl = max(cl_versions, key=lambda v: float(v)) if cl_versions else None
    if latest_cl:
        new_text = idx_text
        # Portfolio 見出し
        portfolio_m = re.search(r'(## Current Portfolio \(v)([\d.]+)', new_text)
        if portfolio_m and float(portfolio_m.group(2)) < float(latest_cl):
            old_heading = portfolio_m.group(0)
            new_heading = f"{portfolio_m.group(1)}{latest_cl}"
            new_text = new_text.replace(old_heading, new_heading, 1)
            fixed.append(f"index.md Portfolio v{portfolio_m.group(2)}→v{latest_cl}")

        # System State 見出し
        state_m = re.search(r'(## System State \(v)([\d.]+)', new_text)
        if state_m and float(state_m.group(2)) < float(latest_cl):
            old_heading = state_m.group(0)
            new_heading = f"{state_m.group(1)}{latest_cl}"
            new_text = new_text.replace(old_heading, new_heading, 1)
            fixed.append(f"index.md System State v{state_m.group(2)}→v{latest_cl}")

        if new_text != idx_text:
            index.write_text(new_text, encoding="utf-8")
            idx_text = new_text

    # ── Session History 欠落リンクの自動追加 ──
    sessions_dir = KB_WIKI / "sessions"
    if sessions_dir.exists():
        session_files = sorted(sessions_dir.glob("*.md"), reverse=True)
        if session_files:
            newest = session_files[0].stem
            history_m = re.search(
                r'(## Session History\s*\n)', idx_text
            )
            if history_m and newest not in idx_text:
                insert_pos = history_m.end()
                link_line = f"- [[sessions/{newest}]]\n"
                idx_text = idx_text[:insert_pos] + link_line + idx_text[insert_pos:]
                index.write_text(idx_text, encoding="utf-8")
                fixed.append(f"index.md Session History に [[{newest}]] 追加")

    return fixed


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
    if FIX_MODE:
        fixed = fix_kb_drift()
        for f in fixed:
            print(f"  🔧 自動修正: {f}")
    kb_errors, kb_warns = check_kb_consistency()
    errors.extend(kb_errors)
    warnings.extend(kb_warns)
    if not kb_errors:
        ok("KB整合性OK")
        ok_count += 1

    # ── 7. AIタスク・ガバナンス (レビューゲート + 幽霊タスク) ──
    section("AIタスク・ガバナンス (Codex review gate / queue SLA / 幽霊 pending)")
    gov_errors, gov_warns = check_ai_task_governance()
    errors.extend(gov_errors)
    warnings.extend(gov_warns)
    if not gov_errors:
        ok("AIタスク・ガバナンスOK")
        ok_count += 1

    # ── 8. env gate 宣言整合 (decision-without-provisioning 防止) ──
    section("env gate ⇄ render.yaml 宣言整合 (*_LIVE_ENABLE)")
    env_errors, env_warns = check_env_gate_declarations()
    errors.extend(env_errors)
    warnings.extend(env_warns)
    if not env_errors:
        ok("env gate 宣言OK")
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

    # 警告は --quiet でも常に出力（ドリフト検知の閉ループに必須）
    for w in warnings:
        print(w)

    msg = f"✅ 全{ok_count}チェック通過 — 整合性OK"
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
