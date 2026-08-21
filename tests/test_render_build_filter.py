"""render.yaml buildFilter の安全性を CI で固定する (rule:R3, 2026-08-21).

背景
----
main への全 commit が web service を再デプロイし、取引エンジン
(demo_trader.py の per-mode background threads) を再起動していた。
実測 16.8 deploy/日・うち 78% は KB ドキュメント専用 commit、1 回あたり
実測 ~60s の完全無 tick + ~2.5-3 分の 24 モード ramp-up。
導出: knowledge-base/wiki/analyses/deploy-churn-trading-gap-2026-08-21.md

このテストが守る不変条件
------------------------
buildFilter.ignoredPaths は「ランタイムが読まない」パスだけを含む。
ignoredPaths を広げてランタイム read を巻き込むと、本番が古い KB を
掴んだまま何日も気づかれない (= サイレント汚染) ため、機械で止める。
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER_YAML = ROOT / "render.yaml"

# app.py / modules/ が実際に **読む** KB パス (2026-08-21 全数 grep で確定)。
# ignoredPaths に巻き込んだら ERROR。追加時は必ずここにも足すこと。
RUNTIME_READ_PATHS = [
    "knowledge-base/wiki/tier-master.json",          # app.py:27 / :11010
    "knowledge-base/wiki/snapshots/any-snapshot.json",  # app.py:28
    "knowledge-base/raw/trade-logs/analyst-memory.md",          # app.py:11645
    "knowledge-base/raw/trade-logs/analyst-memory-archive.md",  # app.py:11646
    # cron (tools/prereg_trigger_watch.py 等) が読む。web は読まないが、
    # 意味的に load-bearing なので保守的にデプロイを起こさせる。
    "knowledge-base/wiki/decisions/prereg-trigger-registry.json",
]

# ランタイムが **書くだけ** で読まない KB パス (ignore して安全)。
RUNTIME_WRITE_ONLY_PREFIXES = [
    "knowledge-base/raw/hunt_events",   # modules/hunt_event_logger.py:40
    "knowledge-base/raw/bt-results",    # app.py:12309 (makedirs + write)
]


def _ignored_paths() -> list[str]:
    """web service の buildFilter.ignoredPaths を regex 抽出 (pyyaml 非依存)。"""
    text = RENDER_YAML.read_text(encoding="utf-8")
    m = re.search(r"^\s*buildFilter:\s*\n\s*ignoredPaths:\s*\n((?:\s*-\s*.+\n)+)",
                  text, re.MULTILINE)
    assert m, "render.yaml に buildFilter.ignoredPaths が無い"
    return [re.sub(r'^\s*-\s*"?|"?\s*$', "", ln)
            for ln in m.group(1).splitlines() if ln.strip()]


def _matches(path: str, pattern: str) -> bool:
    from fnmatch import fnmatch
    return fnmatch(path, pattern) or fnmatch(path, pattern.replace("/**", "/*"))


def test_build_filter_present_and_nonempty():
    paths = _ignored_paths()
    assert len(paths) >= 10, f"ignoredPaths が縮小している: {paths}"


def test_runtime_read_paths_are_not_ignored():
    """ランタイム read パスが ignore されていないこと (本体不変条件)。"""
    ignored = _ignored_paths()
    violations = [(p, pat) for p in RUNTIME_READ_PATHS
                  for pat in ignored if _matches(p, pat)]
    assert not violations, (
        "ランタイムが読む KB パスが ignoredPaths に巻き込まれている "
        f"(本番が古い KB を掴む): {violations}"
    )


def test_no_new_runtime_kb_path_silently_ignored():
    """drift guard: 新たに KB を読み始めたコードを検出する。

    app.py / modules/ に現れる KB パスのうち、ignoredPaths に match する
    ものは write-only allowlist に載っていなければならない。新規 read が
    追加されたのに ignore され続ける事故を機械で止める。
    """
    ignored = _ignored_paths()
    srcs = [ROOT / "app.py"] + sorted((ROOT / "modules").glob("*.py"))
    # os.path.join("knowledge-base", "wiki", ...) / Path / "knowledge-base" / ...
    seg = re.compile(r'"knowledge-base"((?:\s*[,/]\s*"[A-Za-z0-9_.\-]+")+)')
    found: set[str] = set()
    for src in srcs:
        if not src.exists():
            continue
        for m in seg.finditer(src.read_text(encoding="utf-8")):
            parts = re.findall(r'"([A-Za-z0-9_.\-]+)"', m.group(1))
            found.add("knowledge-base/" + "/".join(parts))

    offenders = []
    for path in sorted(found):
        if not any(_matches(path, pat) for pat in ignored):
            continue
        if any(path.startswith(pfx) for pfx in RUNTIME_WRITE_ONLY_PREFIXES):
            continue
        offenders.append(path)
    assert not offenders, (
        "ランタイムコードが触る KB パスが ignoredPaths に match している。"
        " read なら ignoredPaths から外す / write-only なら "
        f"RUNTIME_WRITE_ONLY_PREFIXES に理由付きで追加せよ: {offenders}"
    )
