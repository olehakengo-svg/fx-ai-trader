"""Backfill for the MoF communication-modality corpus (data/external/mof_statements/).

Collects, with polite rate limiting (>= 1.2s between requests to mof.go.jp /
warp.ndl.go.jp, >= 6s to GDELT):

  1. interventions  — official FX intervention daily history CSV (1991-04 ..
     latest disclosed quarter) from the MoF quarter page, normalized to
     interventions_daily.csv + interventions_monthly_pending.csv, plus a
     consistency check against the frozen data/external/mof_interventions.csv
     (383 events, fetched 2026-07-24 for MoF #4 pre-reg W1-F1).
  2. conferences    — finance-minister press-conference transcripts:
     online months (2023-04 .. current) from mof.go.jp, purged months
     (2022-01 .. 2023-03) via NDL WARP raw captures (`id_` modifier).
     Stored as conferences/{YYYYMM}.jsonl (one JSON per conference, full
     role-tagged text blocks) — MoF purges old pages, so the corpus is the
     archival copy.
  3. score          — lexicon ladder scores (tools/mof_statements_lexicon.py)
     regenerated over the whole corpus into lexicon_scores.csv.
  4. gdelt          — GDELT DOC 2.0 timelinevol series for yen-intervention
     news intensity (2017-01-01 .. now), gdelt/*.csv.
  5. report         — escalation eyeball-check tables for the 2022-09/10 and
     2024-04/05 windows (lexicon scores x official intervention dates; the
     2022/2024 labels are explore-domain, already-disclosed data).

Discipline (MoF #4 pre-reg cross-LOCK, knowledge-base/wiki/decisions/
mof-intervention-forward-prereg-2026-07-24.md): this tool performs COLLECTION
ONLY. It never reads price data and never computes any statement x
intervention x price joint quantity. The 2026 window rows that the official
CSV now contains are stored verbatim; verdict execution for pre-reg #4 is a
separate task and MUST NOT be improvised here.

Usage:
  python3 tools/mof_statements_ingest.py --all
  python3 tools/mof_statements_ingest.py --interventions --check
  python3 tools/mof_statements_ingest.py --conferences --warp --score
  python3 tools/mof_statements_ingest.py --gdelt --report
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

try:
    from tools import mof_statements_lexicon as lex
except ImportError:  # executed as a script from inside tools/
    import mof_statements_lexicon as lex

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "data", "external", "mof_statements")
CONF_DIR = os.path.join(OUT_DIR, "conferences")
GDELT_DIR = os.path.join(OUT_DIR, "gdelt")
LEGACY_CSV = os.path.join(REPO, "data", "external", "mof_interventions.csv")

UA = "fx-ai-trader-research/1.0 (contact: goto@tctangle.co.jp)"
MOF_BASE = "https://www.mof.go.jp"
CONF_INDEX = f"{MOF_BASE}/public_relations/conference/index.html"
CONF_PAGE = f"{MOF_BASE}/public_relations/conference/{{name}}"
FEIO_CSV = f"{MOF_BASE}/policy/international_policy/reference/feio/foreign_exchange_intervention_operations.csv"
NEWS_RSS = f"{MOF_BASE}/news.rss"
WARP_SHELL = "https://warp.ndl.go.jp/web/{ts}/www.mof.go.jp/public_relations/conference/{name}"
WARP_CONTENT = "https://warp.ndl.go.jp/{collection}/{capture}id_/www.mof.go.jp/public_relations/conference/{name}"

ONLINE_FIRST_MONTH = "202304"   # mof.go.jp retention boundary (older months purged to WARP)
WARP_FIRST_MONTH = "202201"     # backfill start (2022-01, per task scope)

SLEEP_MOF = 1.2
SLEEP_GDELT = 6.0

GDELT_QUERIES = {
    # slug -> GDELT DOC query (timelinevol = % of global coverage volume)
    "yen_intervention": '"yen intervention"',
    "currency_intervention_japan": '"currency intervention" sourcecountry:japan',
}
GDELT_START = "20170101000000"  # DOC 2.0 API coverage floor

FX_TITLE = re.compile(r"為替|介入|平衡操作|円相場|円安|円高|レートチェック")


# ---------------------------------------------------------------- fetch -----

def fetch(url: str, retries: int = 3, timeout: int = 60, backoff: float = 2.0) -> bytes:
    """curl-based fetch with UA, redirects followed, fail on non-2xx."""
    last_err = None
    for attempt in range(retries):
        proc = subprocess.run(
            ["curl", "-sS", "-L", "--fail", "--max-time", str(timeout), "-A", UA, url],
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
        last_err = proc.stderr.decode("utf-8", "replace")[:300]
        time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries} tries: {url}: {last_err}")


def fetch_optional(url: str, timeout: int = 30):
    """Fetch that returns None on HTTP 404 (for existence probes)."""
    proc = subprocess.run(
        ["curl", "-sS", "-L", "--max-time", str(timeout), "-A", UA,
         "-w", "\n__HTTP_CODE__%{http_code}", url],
        capture_output=True,
    )
    body, _, tail = proc.stdout.rpartition(b"\n__HTTP_CODE__")
    code = tail.decode("ascii", "replace").strip()
    if code == "404":
        return None
    if proc.returncode != 0 or code not in ("200",) or not body:
        raise RuntimeError(f"fetch_optional failed: {url}: http={code}")
    return body


def fetch_effective(url: str, timeout: int = 60):
    """Like fetch() but also returns the post-redirect effective URL."""
    proc = subprocess.run(
        ["curl", "-sS", "-L", "--fail", "--max-time", str(timeout), "-A", UA,
         "-w", "\n__EFFECTIVE_URL__%{url_effective}", url],
        capture_output=True,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise RuntimeError(f"fetch failed: {url}: {proc.stderr.decode('utf-8', 'replace')[:300]}")
    body, _, tail = proc.stdout.rpartition(b"\n__EFFECTIVE_URL__")
    return body, tail.decode("utf-8", "replace").strip()


def decode_mof(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp932")


# ---------------------------------------------------------- pure helpers ----

def extract_month_links(index_html: str) -> list:
    """All {YYYYMM} stamps linked from a conference index page.

    Live pages use .html; pre-2023-04 originals (WARP captures) use .htm.
    """
    return sorted(set(re.findall(r'href="(?:\./)?(\d{6})\.html?"', index_html)))


def extract_conf_links(month_html: str) -> list:
    """All my{YYYYMMDD}.htm(l) conference-page names linked from a month page."""
    return sorted(set(re.findall(r'href="(?:\./)?(my\d{8}\.html?)"', month_html)))


def parse_rss_items(xml_text: str) -> list:
    """Minimal RSS 2.0 item parser (title/link/pubDate)."""
    items = []
    for m in re.finditer(r"<item>(.*?)</item>", xml_text, re.S):
        chunk = m.group(1)

        def tag(name):
            t = re.search(rf"<{name}>(.*?)</{name}>", chunk, re.S)
            return t.group(1).strip() if t else ""

        items.append({"title": tag("title"), "link": tag("link"), "pub_date": tag("pubDate")})
    return items


def filter_fx_items(items: list) -> list:
    return [it for it in items if FX_TITLE.search(it.get("title", ""))]


# ------------------------------------------------------- interventions ------

def run_interventions(check: bool = True) -> dict:
    """Fetch + normalize the official daily intervention history; optionally
    cross-check against the frozen legacy CSV."""
    try:
        from tools.mof_interventions_fetch import parse_daily_csv, fetch_monthly_aggregates
    except ImportError:
        from mof_interventions_fetch import parse_daily_csv, fetch_monthly_aggregates

    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"[interventions] fetch {FEIO_CSV}")
    text = decode_mof(fetch(FEIO_CSV))
    events, quarter_totals, last_q_end = parse_daily_csv(text)
    if not events:
        raise RuntimeError("0 daily events parsed")
    sum_daily = sum(e["amount_oku"] for e in events)
    sum_q = sum(t for _, t in quarter_totals)
    if abs(sum_daily - sum_q) > 0.001 * max(sum_daily, sum_q):
        raise RuntimeError("daily vs quarterly totals diverge by >0.1% — parsing bug")
    print(f"[interventions] {len(events)} daily events through {last_q_end}; totals cross-check OK")

    daily_path = os.path.join(OUT_DIR, "interventions_daily.csv")
    with open(daily_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "currency_pair", "direction", "amount_yen_billions", "source_url"])
        for e in events:
            w.writerow([e["date"].isoformat(), e["currency_pair"], e["direction"],
                        round(e["amount_oku"] * 0.1, 1), FEIO_CSV])

    time.sleep(SLEEP_MOF)
    monthly = fetch_monthly_aggregates(after=last_q_end)
    monthly_path = os.path.join(OUT_DIR, "interventions_monthly_pending.csv")
    with open(monthly_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["window_start", "window_end", "amount_yen_billions", "source_url"])
        for m in monthly:
            w.writerow([m["window_start"].isoformat(), m["window_end"].isoformat(),
                        round(m["amount_oku"] * 0.1, 1), m["source_url"]])
    print(f"[interventions] wrote {daily_path} ({len(events)} rows), "
          f"{monthly_path} ({len(monthly)} pending-window rows)")

    summary = {
        "n_daily": len(events),
        "last_quarter_end": last_q_end.isoformat(),
        "n_monthly_pending": len(monthly),
    }
    if check:
        summary["consistency"] = _consistency_check(events)
    return summary


def _consistency_check(events: list) -> dict:
    """Compare new daily rows against the frozen legacy mof_interventions.csv.

    Label data only (dates/pairs/amounts) — no price quantities are computed.
    """
    from collections import Counter
    legacy_rows = []
    legacy_monthly = 0
    with open(LEGACY_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row["currency_pair"] == "UNDISCLOSED":
                legacy_monthly += 1
                continue
            legacy_rows.append((row["date"], row["currency_pair"], row["direction"],
                                float(row["amount_yen_billions"])))
    # row-level multiset comparison — several dates carry TWO rows (multi-pair
    # days, e.g. USD/DEM + USD/JPY), so keying by date alone would collapse them
    new_rows = [(e["date"].isoformat(), e["currency_pair"], e["direction"],
                 round(e["amount_oku"] * 0.1, 1)) for e in events]
    cl, cn = Counter(legacy_rows), Counter(new_rows)
    only_legacy = sorted((cl - cn).elements())
    only_new = sorted((cn - cl).elements())
    result = {
        "legacy_daily_rows": len(legacy_rows),
        "legacy_monthly_aggregate_rows": legacy_monthly,
        "new_daily_rows": len(new_rows),
        "matched": sum((cl & cn).values()),
        "only_in_legacy": [r[0] for r in only_legacy],
        "only_in_new": [r[0] for r in only_new],
    }
    print(f"[check] legacy daily={len(legacy_rows)} new daily={len(new_rows)} "
          f"matched={result['matched']} only_legacy={result['only_in_legacy']} "
          f"only_new={result['only_in_new']}")
    return result


# --------------------------------------------------------- conferences ------

def _existing_conf_names(month: str) -> set:
    path = os.path.join(CONF_DIR, f"{month}.jsonl")
    names = set()
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                if line.strip():
                    names.add(json.loads(line)["name"])
    return names


def _append_conf(month: str, entry: dict):
    os.makedirs(CONF_DIR, exist_ok=True)
    with open(os.path.join(CONF_DIR, f"{month}.jsonl"), "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _store_conference(month: str, name: str, html: str, source: str, source_url: str) -> bool:
    doc = lex.parse_conference_html(html, url=CONF_PAGE.format(name=name))
    unparsed = ""
    if not doc["blocks"]:
        # keep the stripped text so the corpus retains content even when the
        # 問/答 structure is absent (e.g. statement-only pages)
        unparsed = "\n".join(lex._html_to_lines(html))[:20000]
        print(f"[conf]   WARN no 問/答 blocks parsed: {name} ({source}) — stored unparsed text")
    entry = {
        "name": name,
        "date": doc["date"],
        "title": doc["title"],
        "minister": doc["minister"],
        "url": CONF_PAGE.format(name=name),
        "source": source,
        "source_url": source_url,
        "fetched_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "blocks": doc["blocks"],
    }
    if unparsed:
        entry["unparsed_text"] = unparsed
    _append_conf(month, entry)
    return bool(doc["blocks"])


def _month_range(first_month: str, last_month: str) -> list:
    months = []
    y, mo = int(first_month[:4]), int(first_month[4:])
    while f"{y:04d}{mo:02d}" <= last_month:
        months.append(f"{y:04d}{mo:02d}")
        mo += 1
        if mo == 13:
            y, mo = y + 1, 1
    return months


def probe_month_days(month: str) -> int:
    """Day-probe my{YYYYMMDD}.html for a month whose index page is missing.

    MoF has real index gaps (2023-10..12 and 2026-01..04 month pages were
    never created) while the individual transcripts exist as unlinked
    orphans — discovered 2026-08-18, see the KB doc. 404s are expected.
    """
    have = _existing_conf_names(month)
    y, mo = int(month[:4]), int(month[4:])
    ndays = (dt.date(y + (mo == 12), mo % 12 + 1, 1) - dt.date(y, mo, 1)).days
    today = dt.date.today()
    n_new = 0
    for day in range(1, ndays + 1):
        if dt.date(y, mo, day) > today:
            break
        name = f"my{month}{day:02d}.html"
        if name in have:
            continue
        time.sleep(SLEEP_MOF)
        body = fetch_optional(CONF_PAGE.format(name=name))
        if body is None:
            continue
        _store_conference(month, name, decode_mof(body), source="online",
                          source_url=CONF_PAGE.format(name=name))
        n_new += 1
    return n_new


def run_conferences_online(first_month: str = ONLINE_FIRST_MONTH) -> dict:
    """Crawl mof.go.jp months first_month..current (index months + gap months)."""
    print(f"[conf] fetch index {CONF_INDEX}")
    index_html = decode_mof(fetch(CONF_INDEX))
    listed = [m for m in extract_month_links(index_html) if m >= first_month]
    expected = _month_range(first_month, dt.date.today().strftime("%Y%m"))
    gaps = [m for m in expected if m not in listed]
    print(f"[conf] online listed months: {len(listed)}; index gaps to day-probe: {gaps}")
    n_new = n_pages = 0
    for month in listed:
        time.sleep(SLEEP_MOF)
        month_html = decode_mof(fetch(CONF_PAGE.format(name=f"{month}.html")))
        names = extract_conf_links(month_html)
        have = _existing_conf_names(month)
        todo = [n for n in names if n not in have]
        n_pages += 1
        if not todo:
            continue
        print(f"[conf] {month}: {len(todo)} new / {len(names)} listed")
        for name in todo:
            time.sleep(SLEEP_MOF)
            url = CONF_PAGE.format(name=name)
            html = decode_mof(fetch(url))
            _store_conference(month, name, html, source="online", source_url=url)
            n_new += 1
    n_gap = 0
    for month in gaps:
        found = probe_month_days(month)
        print(f"[conf] gap month {month}: day-probe found {found}")
        n_gap += found
    print(f"[conf] online done: {n_new} listed + {n_gap} gap-probed new conferences "
          f"over {n_pages} month pages")
    return {"months": len(listed), "gap_months": gaps, "new": n_new + n_gap}


def _warp_resolve(ts: str, name: str):
    """Resolve a WARP shell URL to (collection, capture_ts) via the pywb iframe."""
    html = decode_mof(fetch(WARP_SHELL.format(ts=ts, name=name)))
    m = re.search(r'id="pywb-frame"[^>]*src="/(\d{8})/(\d{14})/', html)
    if not m:
        raise RuntimeError(f"cannot resolve WARP shell for ts={ts} name={name}")
    return m.group(1), m.group(2)


def run_conferences_warp(first_month: str = WARP_FIRST_MONTH, last_month: str = "202303") -> dict:
    """Backfill purged months from NDL WARP monthly crawls (raw `id_` captures).

    Collections are resolved via the archived index.html (always captured);
    month/conference pages are then fetched inside the same collection. The
    original site used .htm until the 2023-04 refresh renamed pages to .html,
    so both extensions are tried (WARP captures straddle the rename).
    """
    months = _month_range(first_month, last_month)
    n_new = 0
    for month in months:
        have = _existing_conf_names(month)
        # resolve via a crawl ~2 months after the target month (page complete);
        # fall back to +3/+4 months if that crawl lacks the page
        stored = False
        for lag in (2, 3, 4):
            yy, mm = int(month[:4]), int(month[4:]) + lag
            yy, mm = yy + (mm - 1) // 12, (mm - 1) % 12 + 1
            ts = f"{yy:04d}{mm:02d}01000000"
            try:
                time.sleep(SLEEP_MOF)
                collection, capture = _warp_resolve(ts, "index.html")
                month_html = names = None
                for ext in ("htm", "html"):
                    time.sleep(SLEEP_MOF)
                    body = fetch_optional(WARP_CONTENT.format(
                        collection=collection, capture=capture, name=f"{month}.{ext}"))
                    if body is None:
                        continue
                    month_html = decode_mof(body)
                    names = extract_conf_links(month_html)
                    if names:
                        break
                if not names:
                    raise RuntimeError("month page missing or no conference links in this collection")
            except Exception as e:
                print(f"[warp] {month} via lag+{lag} failed: {e}")
                continue
            todo = [n for n in names if n not in have]
            print(f"[warp] {month} (collection {collection}): {len(todo)} new / {len(names)} listed")
            for name in todo:
                time.sleep(SLEEP_MOF)
                url = WARP_CONTENT.format(collection=collection, capture=capture, name=name)
                body, effective = fetch_effective(url)
                _store_conference(month, name, decode_mof(body), source="warp", source_url=effective)
                n_new += 1
            stored = True
            break
        if not stored:
            raise RuntimeError(f"WARP backfill failed for month {month} (all lags exhausted)")
    print(f"[warp] done: {n_new} new conferences over {len(months)} months")
    return {"months": len(months), "new": n_new}


# --------------------------------------------------------------- scores -----

def run_score() -> dict:
    """Regenerate lexicon_scores.csv from the full corpus (deterministic)."""
    rows = []
    for fname in sorted(os.listdir(CONF_DIR)):
        if not fname.endswith(".jsonl"):
            continue
        with open(os.path.join(CONF_DIR, fname)) as f:
            for line in f:
                if not line.strip():
                    continue
                e = json.loads(line)
                r = lex.score_conference(e["blocks"])
                phrases = ";".join(
                    f"L{lv}:{'/'.join(hits)}" for lv, hits in sorted(r["matches"].items()))
                rows.append({
                    "date": e["date"] or "",
                    "minister": e["minister"],
                    "source": e["source"],
                    "max_level": r["max_level"],
                    "n_fx_blocks": r["n_fx_blocks"],
                    "no_comment": int(r["no_comment"]),
                    "matched_phrases": phrases,
                    "url": e["url"],
                })
    rows.sort(key=lambda r: (r["date"], r["url"]))
    path = os.path.join(OUT_DIR, "lexicon_scores.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else
                           ["date", "minister", "source", "max_level", "n_fx_blocks",
                            "no_comment", "matched_phrases", "url"])
        w.writeheader()
        w.writerows(rows)
    n_fx = sum(1 for r in rows if r["max_level"] > 0)
    print(f"[score] wrote {path}: {len(rows)} conferences, {n_fx} with ladder language")
    return {"n_conferences": len(rows), "n_scored_gt0": n_fx}


# ---------------------------------------------------------------- gdelt -----

def run_gdelt() -> dict:
    """Fetch GDELT DOC timelinevol series (full range, overwrite = self-healing)."""
    os.makedirs(GDELT_DIR, exist_ok=True)
    end = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S")
    out = {}
    for slug, query in GDELT_QUERIES.items():
        from urllib.parse import quote
        url = ("https://api.gdeltproject.org/api/v2/doc/doc?query=" + quote(query)
               + f"&mode=timelinevol&format=CSV&STARTDATETIME={GDELT_START}&ENDDATETIME={end}")
        print(f"[gdelt] {slug}: {url}")
        raw = fetch(url, retries=4, timeout=120, backoff=15.0)  # GDELT: 1 req / 5s min
        text = raw.decode("utf-8", "replace")
        if "Date" not in text.splitlines()[0]:
            raise RuntimeError(f"unexpected GDELT response for {slug}: {text[:200]}")
        path = os.path.join(GDELT_DIR, f"{slug}.csv")
        with open(path, "w") as f:
            f.write(f"# query: {query}\n# mode: timelinevol (% of monitored coverage)\n")
            f.write(text if text.endswith("\n") else text + "\n")
        n = max(0, len(text.strip().splitlines()) - 1)
        print(f"[gdelt] wrote {path}: {n} datapoints")
        out[slug] = n
        time.sleep(SLEEP_GDELT)
    return out


# --------------------------------------------------------------- report -----

ESCALATION_WINDOWS = [
    ("2022-08-01", "2022-11-15", "2022-09 レートチェック→09-22/10-21/10-24 円買い介入"),
    ("2024-03-01", "2024-05-31", "2024-04-29/05-01 円買い介入"),
]


def build_escalation_tables() -> str:
    """Markdown eyeball-check tables: lexicon scores x official intervention
    dates for the 2022/2024 explore-domain windows. No price data."""
    scores = []
    with open(os.path.join(OUT_DIR, "lexicon_scores.csv"), newline="") as f:
        scores = [r for r in csv.DictReader(f)]
    interventions = set()
    with open(os.path.join(OUT_DIR, "interventions_daily.csv"), newline="") as f:
        for r in csv.DictReader(f):
            interventions.add(r["date"])
    lines = []
    for start, end, label in ESCALATION_WINDOWS:
        lines.append(f"\n### {label} ({start} .. {end})\n")
        lines.append("| date | minister | level | no-cmt | matched | 介入日(公式) |")
        lines.append("|---|---|---|---|---|---|")
        window = [r for r in scores if r["date"] and start <= r["date"] <= end]
        for r in window:
            iv = "**介入**" if r["date"] in interventions else ""
            nc = "○" if r["no_comment"] == "1" else ""
            lines.append(f"| {r['date']} | {r['minister']} | {r['max_level']} | {nc} "
                         f"| {r['matched_phrases'][:80]} | {iv} |")
        # intervention days with no conference that day
        conf_dates = {r["date"] for r in window}
        for d in sorted(interventions):
            if start <= d <= end and d not in conf_dates:
                lines.append(f"| {d} | — | — | — | (会見なし) | **介入** |")
    return "\n".join(lines)


# ----------------------------------------------------------------- main -----

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--interventions", action="store_true")
    ap.add_argument("--check", action="store_true", help="consistency check vs legacy CSV")
    ap.add_argument("--conferences", action="store_true", help="online months (2023-04..)")
    ap.add_argument("--warp", action="store_true", help="WARP months (2022-01..2023-03)")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--gdelt", action="store_true")
    ap.add_argument("--report", action="store_true", help="print escalation eyeball tables")
    args = ap.parse_args(argv)

    summary = {}
    if args.all or args.interventions:
        summary["interventions"] = run_interventions(check=args.check or args.all)
    if args.all or args.conferences:
        summary["conferences_online"] = run_conferences_online()
    if args.all or args.warp:
        summary["conferences_warp"] = run_conferences_warp()
    if args.all or args.score:
        summary["score"] = run_score()
    if args.all or args.gdelt:
        summary["gdelt"] = run_gdelt()
    if args.all or args.report:
        print(build_escalation_tables())
    print("[summary]", json.dumps(summary, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    main()
