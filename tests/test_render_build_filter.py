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


def test_decisions_markdown_ignored_but_registry_json_still_deploys():
    """decisions/ は **md だけ** ignore し、registry JSON はデプロイを起こすこと.

    2026-09-01 (rule:R3)。`knowledge-base/wiki/decisions/**` が ignoredPaths に
    無かったため、**KB ドキュメント専用の commit が web service を再デプロイして
    いた** — 実測で直近 60 日に 23 commit (~0.38 deploy/日)。PR #199/#201 が
    churn を would-deploy 0 まで落とした後に残っていた取りこぼしである。

    ただし同ディレクトリの ``prereg-trigger-registry.json`` は
    ``TRADING_PATH_READ_PATHS`` が「cron が読む load-bearing な状態なので
    保守的にデプロイを起こさせる」と明示している。したがって
    **`decisions/**` を丸ごと ignore してはならない**。

    ここは**性質**を pin する (構文ではない, PR #209 教訓):
      性質 A: decisions 直下および入れ子の .md は ignore される
      性質 B: registry JSON は ignore され「ない」
    B は ``test_trading_path_read_paths_are_not_ignored`` でも守られているが、
    A と B は**対で意味を持つ** (片方だけだと「全部 ignore」か「全部 deploy」に
    倒れても気づけない) ので、同じ test で並べて固定する。
    """
    ignored = _ignored_paths()

    # 性質 A — 実在のパス形状で確認する (直下 + 入れ子)
    md_paths = [
        "knowledge-base/wiki/decisions/candidate-stagnation-threshold-verdict-2026-09-01.md",
        "knowledge-base/wiki/decisions/shadow-audit-2026-04-30/any-report.md",
    ]
    for p in md_paths:
        assert any(_matches(p, pat) for pat in ignored), (
            f"decisions の markdown が ignore されていない (ドキュメント commit が"
            f" 取引エンジンを再起動する): {p}"
        )

    # 性質 B — registry JSON は必ずデプロイを起こす
    registry = "knowledge-base/wiki/decisions/prereg-trigger-registry.json"
    assert not any(_matches(registry, pat) for pat in ignored), (
        "prereg-trigger-registry.json が ignoredPaths に巻き込まれた。"
        " cron が読む load-bearing な状態なのでデプロイを起こさせること"
    )


def test_nightly_ingest_data_paths_are_ignored():
    """2026-09-22 (rule:R3): 夜間 ingest の commit が取引エンジンを毎晩再起動していた.

    `auto: rate anchor daily ingest` (21:15Z 平日) と `data(mof-statements): daily
    collect` (21:30Z 毎日) は研究用データのみを触る (app.py / modules/ からの参照
    ゼロ、全数 grep 2026-09-22)。ignoredPaths に無かったため、この 2 commit が
    **毎晩 2 回**の web service 再デプロイ = 無 tick ~60s + ramp 2.5-3 分を払わせ、
    しかも 2026-09-22 は 2 回目のデプロイ (00:12:50) の直後に HTTP 全盲事故が起きた
    (knowledge-base/wiki/analyses/http-blind-fork-poisoning-2026-09-22.md)。

    性質 A: 3 パス (rate_anchor/**, mof_statements/**, ZN_F_1h.parquet) は ignore される
    性質 B: 取引パスは今もそれらを読まない — `fetch_zn_intraday` の呼び手が
            app.py / modules/ / strategies/ に存在しないこと (読み始めたら ignore を外す)
    """
    ignored = _ignored_paths()
    nightly = [
        "data/external/rate_anchor/manifest.json",
        "data/external/rate_anchor/zn_f_daily.csv",
        "data/external/mof_statements/gdelt/yen_intervention.csv",
        "data/external/mof_statements/conferences/202609.jsonl",
        "data/cache/yield/ZN_F_1h.parquet",
    ]
    for p in nightly:
        assert any(_matches(p, pat) for pat in ignored), (
            f"夜間 ingest パスが ignore されていない (毎晩の取引エンジン再起動): {p}"
        )
    # 性質 B — runtime 側に読み手が居ないこと
    callers = []
    for src in [ROOT / "app.py"] + sorted((ROOT / "modules").glob("*.py")) \
            + sorted((ROOT / "strategies").rglob("*.py")):
        if not src.exists():
            continue
        text = src.read_text(encoding="utf-8")
        if src.name == "yield_data.py":
            continue  # 定義元 (docstring の使用例のみ)
        if "fetch_zn_intraday(" in text or "rate_anchor" in text or "mof_statements" in text:
            callers.append(str(src.relative_to(ROOT)))
    assert not callers, (
        "取引パスが夜間 ingest データを読み始めている。ignoredPaths から外すこと: "
        f"{callers}"
    )
    # ⚠️ ZN の json キャッシュ (data/cache/yield/*.json) は取引パス read のまま。
    # parquet 1 ファイルだけを ignore し、ディレクトリ全体は ignore しない。
    assert not any(_matches("data/cache/yield/any.json", pat) for pat in ignored)


def test_cron_only_kb_state_paths_are_ignored():
    """2026-09-22 (rule:R3, sprint 0922 follow-up): 残余 deploy churn 2 源を ignore する.

    `auto: KB session-end save` (b53fd5cd, 06:24Z) が `knowledge-base/raw/alpha_budget/
    2026-09.json` **1 ファイル**で web service を再デプロイした。同ファイルの読み書きは
    cron service (tools/alpha_budget_tracker.py 月初 reset / tools/quant_gate_status.py
    Tier A / scripts/daily_hypothesis_scan.py Tier B) だけで、web プロセス (app.py /
    modules/) からの参照はゼロ (全数 grep 2026-09-22)。cron service は buildFilter を
    持たないため毎 push で再デプロイされ、cron 側が古い状態を掴むことはない。
    `knowledge-base/wiki/research/**` (研究文書) も同様に web 非参照 (読み手は手動
    ingest の tools/qdrant_ingest_kb.py のみ)。

    性質 A: 2 パス (raw/alpha_budget/**, wiki/research/**) は ignore される
    性質 B: web プロセスに読み手が居ない — app.py / modules/** / strategies/** に `alpha_budget` /
            `wiki/research` / `"wiki", "research"` 形リテラルが出現しないこと
            (読み始めたら ignore を外す。cron が読むだけなら外さない)
    """
    ignored = _ignored_paths()
    for p in [
        "knowledge-base/raw/alpha_budget/2026-09.json",
        "knowledge-base/raw/alpha_budget/2026-10.json",
        "knowledge-base/wiki/research/adhoc-scan-29-step0-2026-09-22.md",
        "knowledge-base/wiki/research/index.md",
    ]:
        assert any(_matches(p, pat) for pat in ignored), (
            f"cron 専用 KB 状態 / 研究文書が ignore されていない (KB commit が取引エンジンを"
            f" 再起動する): {p}"
        )
    # 性質 B — web プロセス側に読み手が居ないこと
    readers = []
    # Path("wiki", "research") / Path('wiki') / 'research' / 'wiki', 'research' の両クォートに一致
    pat = re.compile(r"alpha_budget|wiki/research|[\"']wiki[\"']\)?\s*[,/]\s*[\"']research[\"']")
    runtime_dirs = [ROOT / "modules", ROOT / "strategies"]  # web プロセスが import する全 runtime モジュール
    srcs = [ROOT / "app.py"] + sorted(
        p for d in runtime_dirs if d.exists() for p in d.rglob("*.py")
    )
    for src in srcs:
        if src.exists() and pat.search(src.read_text(encoding="utf-8")):
            readers.append(str(src.relative_to(ROOT)))
    assert not readers, (
        "web プロセスが alpha_budget / wiki/research を読み始めている。ignoredPaths から"
        f" 外すこと (cron 専用なら外さない): {readers}"
    )


# web プロセス (`gunicorn app:app`) が import しうる**全**ローカル package を走査対象にする。
# `modules/` + `strategies/` だけだと app.py が直接 import する cfd_trader.web.app /
# scripts.cfd_phase2_shadow_catchup / tools.* の読み手を見逃す (PR #297 review P2 ×2)。
# 「どの package が web に import されるか」を列挙で追うと必ず漏れるので、リポジトリ内の
# .py を**全部**読み、web と無関係と確定しているディレクトリだけを除く (fail-closed の向き)。
_NON_WEB_DIRS = {
    "tests", "cfd_tests",            # テスト
    ".worktrees", ".claude", ".git",  # 作業ツリー / エージェント
    "knowledge-base", "docs", "wiki", "reports", "research", "audit", "audits",
    "bt-results", "raw", "done", "templates", "migrations", "monitoring",
    "node_modules", ".venv", "venv", "services",  # discord bot (別 service)
}
# web プロセス外で `data/monitoring` を**書く**ことが確定している writer (GitHub Actions
# daily-report.yml が起動、web からの import なしを下で pin)。
_MONITORING_WRITERS_OUTSIDE_WEB = {"tools/nav_floor_projection.py"}


def _web_runtime_sources() -> list[Path]:
    out = []
    for src in sorted(ROOT.rglob("*.py")):
        rel = src.relative_to(ROOT)
        if any(part in _NON_WEB_DIRS for part in rel.parts[:-1]) or rel.parts[0].startswith("."):
            continue
        out.append(src)
    return out


def test_daily_report_monitoring_csv_is_ignored():
    """2026-09-24 (rule:R3): 日報 commit が F4 資金時計 CSV で本番を 1 日 4 回再デプロイしていた.

    `.github/workflows/daily-report.yml` は `tools/nav_floor_projection.py --append` で
    `data/monitoring/nav_floor_projection.csv` に 1 行追記し `docs(KB): daily report` として
    commit する。trade-logs / market-analysis は ignore 済みだったが **この CSV 1 パスが
    ignoredPaths に無く**、Render deploy 一覧 (09-23T05:27 → 09-24T03:02) の 5 件中 4 件が
    日報 commit 起点だった (00:20Z / 03:02Z / 11:12Z / 19:22Z)。00:20Z boot は fork 窓
    hour-0 の再露出 (analyses/http-blind-fork-poisoning-2026-09-22.md §3.3) でもある。
    分析: analyses/dual-engine-dup-rate-readout-2026-09-24.md §7。

    性質 A: `data/monitoring/**` は ignore される (実在パス形状で確認)
    性質 B: web プロセスが import しうる全ローカル .py (`_web_runtime_sources`、
            tests/KB 等の非 web ディレクトリのみ除外) に読み手が居ない —
            連続文字列 `data/monitoring` / `nav_floor_projection.csv` **と**
            分割リテラル (`Path("data") / "monitoring"` / `os.path.join("data", "monitoring", …)`)
            の両形を検査 (読み始めたら ignore を外す)
    性質 B': 既知 writer (`tools/nav_floor_projection.py`) は web から import されていない
    性質 C: sibling の `data/cache/**` は巻き込まない (取引パス read)
    """
    ignored = _ignored_paths()
    for p in ("data/monitoring/nav_floor_projection.csv",
              "data/monitoring/some_future_monitor.csv"):
        assert any(_matches(p, pat) for pat in ignored), (
            f"日報 CSV が ignore されていない (日報 commit が取引エンジンを 1 日 4 回再起動する): {p}"
        )
    srcs = _web_runtime_sources()
    rels = {str(s.relative_to(ROOT)) for s in srcs}
    assert len(srcs) > 200, f"走査対象が縮小している (rglob / 除外集合が壊れた?): {len(srcs)}"
    for must in ("app.py", "modules/demo_trader.py", "strategies/__init__.py",
                 "cfd_trader/web/app.py", "scripts/cfd_phase2_shadow_catchup.py"):
        assert must in rels, f"web が import する package が走査対象から外れている: {must}"

    # `"data", "monitoring"` (os.path.join) と `Path("data") / "monitoring"` の両形。
    # 後者は `"data"` の直後に `)` が入るので省略可能な閉じ括弧を許す
    # (`_literal_paths_with_root` は `)` を許さず Path(...) 形を見逃す — counterfactual 実測)。
    seg = re.compile(r'"data"\)?((?:\s*[,/]\s*"[A-Za-z0-9_.\-]+")+)')
    readers, importers = [], []
    for src in srcs:
        rel = str(src.relative_to(ROOT))
        text = src.read_text(encoding="utf-8", errors="replace")
        if rel not in _MONITORING_WRITERS_OUTSIDE_WEB and re.search(
                r"^\s*(from\s+tools\.nav_floor_projection\s+import|"
                r"from\s+tools\s+import[^\n]*\bnav_floor_projection\b|"
                r"import\s+tools\.nav_floor_projection)", text, re.M):
            importers.append(rel)
        if rel in _MONITORING_WRITERS_OUTSIDE_WEB:
            continue
        contiguous = "data/monitoring" in text or "nav_floor_projection.csv" in text
        segmented = any(
            re.findall(r'"([A-Za-z0-9_.\-]+)"', m.group(1))[:1] == ["monitoring"]
            for m in seg.finditer(text)
        )
        if contiguous or segmented:
            readers.append(rel)
    assert not readers, (
        "web プロセスが import しうるコードが data/monitoring を読み始めている。"
        " ignoredPaths から外すこと: %s" % readers
    )
    assert not importers, (
        "web プロセスが writer (tools/nav_floor_projection.py) を import している —"
        " 読み手になった可能性。ignore を見直すこと: %s" % importers
    )
    assert not any(_matches("data/cache/yield/any.json", pat) for pat in ignored)
