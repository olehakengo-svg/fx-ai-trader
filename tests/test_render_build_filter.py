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

# **取引パス**が読むパス (2026-08-21 全数 grep、2026-08-23 phase-2 で再分類)。
# ignoredPaths に巻き込んだら ERROR = 本番が古い状態を掴んだまま売買する。
TRADING_PATH_READ_PATHS = [
    "knowledge-base/wiki/tier-master.json",          # app.py:27 / :11010
    "knowledge-base/wiki/snapshots/any-snapshot.json",  # app.py:28
    # cron (tools/prereg_trigger_watch.py 等) が読む。web は読まないが、
    # 意味的に load-bearing なので保守的にデプロイを起こさせる。
    "knowledge-base/wiki/decisions/prereg-trigger-registry.json",
    # ランタイムの価格/BT データ (modules/data.py:33 / bt_vec_harness.py:85 /
    # yield_data.py:23 / data.py:39)。data/** を丸ごと ignore する誤りを止める。
    "data/cache/massive/USD_JPY_15m.parquet",
    "data/cache/yield/any.json",
    "data/_holdout_locked/MANIFEST.json",
]

# **助言専用**の read (取引判断に非関与)。ignore 可 = デプロイを起こさせない。
# 代償の陳腐化はサイレントにせず、鮮度テレメトリで観測可能にすること。
# analyst-memory.md: app.py:11651 `_read_analyst_memory` ← :11749
# `get_analyst_opinion` ← :12229 `/api/analyst-opinion` (人手起動) のみ。
ADVISORY_ONLY_READ_PATHS = [
    "knowledge-base/raw/trade-logs/analyst-memory.md",
    "knowledge-base/raw/trade-logs/analyst-memory-archive.md",
]

# ランタイムが **書くだけ** で読まない KB パス (ignore して安全)。
RUNTIME_WRITE_ONLY_PREFIXES = [
    "knowledge-base/raw/hunt_events",   # modules/hunt_event_logger.py:40
    "knowledge-base/raw/bt-results",    # app.py:12309 (makedirs + write)
]


def _ignored_paths() -> list[str]:
    """web service の buildFilter.ignoredPaths を regex 抽出 (pyyaml 非依存)。

    ⚠️ リスト内のコメント行 (`# ...`) も本体として読み進めること。2026-08-23 に
    リスト途中へ注記を入れた際、コメント行で抽出が打ち切られて以降の entry が
    guard の視界から消える (= 検査が黙って無力化する) 事故を実測した。
    """
    text = RENDER_YAML.read_text(encoding="utf-8")
    m = re.search(
        r"^\s*buildFilter:\s*\n\s*ignoredPaths:\s*\n"
        r"((?:[ \t]*(?:-\s*.+|#.*)\n)+)",
        text, re.MULTILINE)
    assert m, "render.yaml に buildFilter.ignoredPaths が無い"
    out = []
    for ln in m.group(1).splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        out.append(re.sub(r'^\s*-\s*"?|"?\s*$', "", ln))
    return out


def test_ignored_paths_parser_sees_entries_after_inline_comments():
    """抽出器がコメント行で打ち切られていないこと (2026-08-23 の実測事故を pin)。"""
    paths = _ignored_paths()
    assert "data/sentiment/**" in paths and "bt-results/**" in paths, (
        "リスト内コメント以降の entry が抽出できていない "
        f"(guard が黙って無力化する): {paths}"
    )


def _matches(path: str, pattern: str) -> bool:
    from fnmatch import fnmatch
    return fnmatch(path, pattern) or fnmatch(path, pattern.replace("/**", "/*"))


def test_build_filter_present_and_nonempty():
    paths = _ignored_paths()
    assert len(paths) >= 10, f"ignoredPaths が縮小している: {paths}"


def test_trading_path_read_paths_are_not_ignored():
    """取引パスの read が ignore されていないこと (本体不変条件)。"""
    ignored = _ignored_paths()
    violations = [(p, pat) for p in TRADING_PATH_READ_PATHS
                  for pat in ignored if _matches(p, pat)]
    assert not violations, (
        "取引パスが読むパスが ignoredPaths に巻き込まれている "
        f"(本番が古い状態を掴んだまま売買する): {violations}"
    )


def test_advisory_only_reads_expose_staleness():
    """助言専用 read を ignore するなら、鮮度が応答で観測可能であること。

    2026-08-23 phase-2: analyst-memory.md を ignore に移した代償として、
    本番の memo は最後のコード系デプロイ時点で固定される。サイレント陳腐化を
    防ぐ鮮度テレメトリ (`memory_stale_days`) が消えたら CI で落とす。
    """
    ignored = _ignored_paths()
    if not any(_matches(ADVISORY_ONLY_READ_PATHS[0], pat) for pat in ignored):
        return  # ignore していないなら鮮度は毎デプロイで自明
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "_analyst_memory_stale_days" in src, (
        "analyst-memory.md を ignore しているのに鮮度テレメトリが無い "
        "(サイレント陳腐化)。app.py の _analyst_memory_stale_days を復活させよ"
    )
    assert '"memory_stale_days"' in src, (
        "鮮度が /api/analyst-opinion 応答に載っていない"
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
        # 助言専用 read は明示的に免除 (phase-2)。代償の陳腐化は
        # test_advisory_only_reads_expose_staleness が鮮度テレメトリで担保する。
        if path in ADVISORY_ONLY_READ_PATHS:
            continue
        offenders.append(path)
    assert not offenders, (
        "ランタイムコードが触る KB パスが ignoredPaths に match している。"
        " read なら ignoredPaths から外す / write-only なら "
        f"RUNTIME_WRITE_ONLY_PREFIXES に理由付きで追加せよ: {offenders}"
    )


def _literal_paths_with_root(root: str) -> set[str]:
    """app.py / modules/ 内の `"<root>", "x", "y"` 形リテラルを path 化する。

    `cached["data"]` / `{"data": ...}` は後続が `]` / `:` のため match しない
    (少なくとも 1 つの `, "seg"` / `/ "seg"` 継続を要求しているため)。
    """
    srcs = [ROOT / "app.py"] + sorted((ROOT / "modules").glob("*.py"))
    seg = re.compile(
        r'"%s"((?:\s*[,/]\s*"[A-Za-z0-9_.\-]+")+)' % re.escape(root)
    )
    found: set[str] = set()
    for src in srcs:
        if not src.exists():
            continue
        for m in seg.finditer(src.read_text(encoding="utf-8")):
            parts = re.findall(r'"([A-Za-z0-9_.\-]+)"', m.group(1))
            found.add(root + "/" + "/".join(parts))
    return found


def test_no_new_runtime_data_path_silently_ignored():
    """drift guard 拡張 (2026-08-23 phase-2).

    phase-1 の guard は `"knowledge-base"` 起点のリテラルしか走査していなかった。
    phase-2 で `bt-results/**` と `data/sentiment/**` を ignore したため、
    ランタイムがこれらを読み始めても検出できない穴が空く → 同じ検査を
    非 KB ルートにも広げる。
    """
    ignored = _ignored_paths()
    offenders = []
    for root in ("data", "bt-results"):
        for path in sorted(_literal_paths_with_root(root)):
            if any(_matches(path, pat) for pat in ignored):
                offenders.append(path)
    assert not offenders, (
        "ランタイムコードが触る非 KB パスが ignoredPaths に match している。"
        " read なら ignoredPaths から外すこと: %s" % offenders
    )
