#!/usr/bin/env python3
"""E23 pass-0: 中銀政策声明コーパス取得ハーネス (outcome 非接触).

位置づけ
--------
pre-reg 🔒 `knowledge-base/wiki/decisions/e23-cb-text-explore-prereg-2026-09-10.md`
§9-2 の pass-0 成果物。**価格データを一切読まない** = outcome 非接触
(two-pass 規律: pass-0 コーパス census → pass-1 イベント列挙 → pass-2 測定)。

凍結仕様 (pre-reg §2 転記、ここでの逸脱は verdict 無効)
-------------------------------------------------------
1 中銀 = 1 文書種:
  - Fed : FOMC statement           (federalreserve.gov, public domain)
  - ECB : monetary policy decisions press release (ecb.europa.eu)
  - BOE : Monetary Policy Summary  (bankofengland.co.uk、MPS 節のみ)
  - BoJ : Statement on Monetary Policy (boj.or.jp、**英語公式版のみ**)
minutes / speeches / press-conference Q&A は全 CB で対象外 (DoF 封鎖)。

本文抽出は「公式ページの本文コンテナ」= 構造セレクタで固定する。語句ベースの
切り出しは境界の選び方が自由度になるため、BOE のみ MPS 節の境界が構造でなく
見出し語で与えられる (公式ページが MPS + minutes を 1 ページに載せるため)。
BOE の境界語は本モジュールで凍結し、テストで pin する。

タイムスタンプ規約 (pre-reg §2): 公表日。Fed = URL 日付 (14:00 ET 固定 2013+)、
ECB = URL 日付、BoJ = 日付のみ使用、BOE = ページの "Published on" 日付。
D1 設計なので時刻は使わない。

使い方
------
    python3 tools/e23_corpus_fetch.py                  # 全 CB・全窓 (差分のみ取得)
    python3 tools/e23_corpus_fetch.py --cb fed boj
    python3 tools/e23_corpus_fetch.py --years 2014 2015
    python3 tools/e23_corpus_fetch.py --offline        # 取得せず manifest 再生成のみ

出力: data/external/cb_statements/{cb}/{YYYY-MM-DD}.json + manifest.json
既存ファイルは再取得しない (idempotent)。--refetch で上書き。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "data" / "external" / "cb_statements"

# pre-reg §2 凍結窓 (explore + OOS)。pass-0 census は explore 窓のみを判定に使う。
EXPLORE_START, EXPLORE_END = date(2014, 1, 1), date(2023, 12, 31)
OOS_START, OOS_END = date(2024, 1, 1), date(2026, 6, 30)

CBS = ("fed", "ecb", "boe", "boj")

UA = "Mozilla/5.0 (compatible; fx-ai-trader E23 research harness; contact via repo)"
SLEEP_SEC = 0.4
MONTHS = (
    "january february march april may june "
    "july august september october november december"
).split()

# BOE のみ: 公式ページが MPS + minutes を 1 ページに含むため、MPS 節の境界を凍結。
# 節見出しは HTML/PDF とも "Monetary Policy Summary, <Month> <Year>" のカンマ形。
# ページ表題 "Monetary Policy Summary and minutes of ..." とはカンマで機械的に分離できる。
BOE_MPS_START_RE = re.compile(r"Monetary Policy Summary,\s+\w+\s+\d{4}")
BOE_MPS_END_RE = re.compile(r"Minutes of the Monetary Policy Committee", re.I)
BOE_PUBLISHED_RE = re.compile(
    r"(?:Published on|Publication date:)\s+(\d{1,2}\s+\w+\s+\d{4})", re.I)
BOE_PDF_TMPL = ("https://www.bankofengland.co.uk/-/media/boe/files/"
                "monetary-policy-summary-and-minutes/{year}/{month}-{year}.pdf")


# ---------------------------------------------------------------- http / text


class NotFound(Exception):
    """4xx: 当該 URL に文書が存在しない (機械的欠測)."""


def _fetch(url: str, *, timeout: int = 40, tries: int = 3) -> str:
    import requests

    last: Exception | None = None
    for attempt in range(tries):
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
            if resp.status_code in (403, 404, 410):
                raise NotFound(f"HTTP {resp.status_code}: {url}")
            resp.raise_for_status()
            resp.encoding = resp.encoding or "utf-8"
            return resp.text
        except NotFound:
            raise
        except Exception as exc:  # noqa: BLE001 - network flake
            last = exc
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last}")


def _exists(url: str) -> bool:
    import requests

    try:
        resp = requests.head(url, headers={"User-Agent": UA}, timeout=25,
                             allow_redirects=False)
        return 200 <= resp.status_code < 300
    except Exception:
        return False


def _norm(text: str) -> str:
    return re.sub(r"[ \t ]+", " ", text.replace("\r", "")).strip()


def extract_container(html_text: str, selectors: tuple[str, ...]) -> str:
    """公式ページの本文コンテナを構造セレクタで抽出 (最初にヒットしたもの)."""
    from bs4 import BeautifulSoup  # 遅延 import (テストの軽量化)

    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for sel in selectors:
        el = soup.select_one(sel)
        if el is not None:
            txt = _norm(el.get_text("\n"))
            if len(txt) >= 400:  # ナビだけの空コンテナを弾く機械規則
                return txt
    return ""


def extract_boe_mps(container_text: str) -> str:
    """BOE ページ本文から MPS 節のみを凍結境界語で切り出す."""
    m_start = BOE_MPS_START_RE.search(container_text)
    if not m_start:
        return ""
    tail = container_text[m_start.start():]
    m_end = BOE_MPS_END_RE.search(tail, m_start.end() - m_start.start())
    return _norm(tail[: m_end.start()] if m_end else tail)


# ---------------------------------------------------------------- discovery


def discover_fed(year: int) -> list[tuple[date, str]]:
    """FOMC statement URL を年次インデックスから列挙."""
    index = (
        "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
        if year >= 2021
        else f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
    )
    html_text = _fetch(index)
    out: dict[date, str] = {}
    for slug in sorted(set(re.findall(r"monetary(\d{8})a\.htm", html_text))):
        d = datetime.strptime(slug, "%Y%m%d").date()
        if d.year != year:
            continue
        out[d] = (
            "https://www.federalreserve.gov/newsevents/pressreleases/"
            f"monetary{slug}a.htm"
        )
    return sorted(out.items())


def discover_ecb(year: int) -> list[tuple[date, str]]:
    """"Monetary policy decisions" のアンカー語でプレスリリースを列挙.

    URL 形式は年代で変わる (2016: pr161208.en.html / 2023: ecb.mp230914~hash.en.html)
    ためパターン依存にせず、アンカーテキストで拾う。
    """
    from bs4 import BeautifulSoup

    index = (
        f"https://www.ecb.europa.eu/press/pr/date/{year}/html/index_include.en.html"
    )
    soup = BeautifulSoup(_fetch(index), "html.parser")
    out: dict[date, str] = {}
    for a in soup.find_all("a", href=True):
        title = _norm(a.get_text(" ")).lower()
        if "monetary policy decision" not in title:
            continue
        href = a["href"]
        if not href.endswith(".en.html"):
            continue
        m = re.search(r"/(?:ecb\.mp|pr)(\d{6})[~.]", href)
        if not m:
            continue
        d = datetime.strptime(m.group(1), "%y%m%d").date()
        if d.year != year:
            continue
        out[d] = "https://www.ecb.europa.eu" + href
    return sorted(out.items())


_BOJ_DOC_RE = re.compile(r"/k(\d{6})([a-z])?\.(htm|pdf)$")
BOJ_STATEMENT_TITLE = "statement on monetary policy"


def discover_boj(year: int) -> list[tuple[date, str]]:
    """BoJ MPM 決定文書 (英語版) を年次インデックスから列挙。

    **文書種の同定規則 (pass-0 で凍結、census §「BoJ 同定」に記録)**:
    BoJ は会合ごとに `k{YYMMDD}a` を主文書スロットとして公開するが、**政策変更が
    あった回だけ表題を変える** ("Expansion of the Quantitative and Qualitative
    Monetary Easing" 2014-10-31 / "Introduction of QQE with a Negative Interest
    Rate" 2016-01-29 等)。表題文字列だけで拾うと **政策ニュースが最大の回だけが
    機械的に落ちる = 内容条件付きの選択バイアス**になるため、同定は
      (1) 同日文書のうち表題が "Statement on Monetary Policy" で始まるもの、
      (2) 無ければ主文書スロット `a`、
      (3) それも無ければ同日先頭
    の順とする ("(Reference)" 系は除外)。ECB の "Monetary policy decisions" は
    政策変更の有無で表題が変わらないため同じ問題を持たない (表題 = 文書種名)。
    配布形式は 2017 年以前が PDF、2018 年以降が HTML。
    """
    from bs4 import BeautifulSoup

    index = f"https://www.boj.or.jp/en/mopo/mpmdeci/mpr_{year}/index.htm"
    soup = BeautifulSoup(_fetch(index), "html.parser")
    by_date: dict[date, list[tuple[str, str, str]]] = {}
    for a in soup.find_all("a", href=True):
        m = _BOJ_DOC_RE.search(a["href"])
        if not m:
            continue
        title = _norm(a.get_text(" "))
        if title.lower().startswith("(reference)"):
            continue
        try:
            d = datetime.strptime(m.group(1), "%y%m%d").date()
        except ValueError:
            continue
        if d.year != year:
            continue
        href = a["href"]
        url = href if href.startswith("http") else "https://www.boj.or.jp" + href
        by_date.setdefault(d, []).append((m.group(2) or "", url, title.lower()))

    out: dict[date, str] = {}
    for d, cands in by_date.items():
        named = [c for c in cands if c[2].startswith(BOJ_STATEMENT_TITLE)]
        slot_a = [c for c in cands if c[0] == "a"]
        chosen = (named or slot_a or cands)[0]
        out[d] = chosen[1]
    return sorted(out.items())


def discover_boe(year: int) -> list[tuple[str, str]]:
    """MPS ページ候補 (月次スラッグ) を存在確認で列挙.

    BOE はアーカイブ一覧が JS 駆動でスクレイプ不能なため、公式の月次スラッグを
    総当たりし HTTP 200 のみ採る (欠測月 = 会合なし or 文書種未存在)。
    日付はページの "Published on" から取るため、ここでは月スラッグを返す。
    """
    out: list[tuple[str, str]] = []
    for month in MONTHS:
        url = (
            "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/"
            f"{year}/{month}-{year}"
        )
        # HTML ページ / 公式 PDF のどちらかが在れば当該月に MPS が存在する。
        # HTML だけで判定すると 2020 年以前 (PDF 配布のみ) を丸ごと取りこぼす。
        if _exists(url) or _exists(BOE_PDF_TMPL.format(year=year, month=month)):
            out.append((month, url))
        time.sleep(SLEEP_SEC)
    return out


# ---------------------------------------------------------------- per-CB fetch

FED_SELECTORS = ("div#article", "div#content")
ECB_SELECTORS = ("main", "div#main-wrapper")
BOJ_SELECTORS = ("main", "div#contents")
BOE_SELECTORS = ("main", "div#main-content", "body")


def _cached_date(cb: str, d: date) -> bool:
    return _doc_path(cb, d.isoformat()).exists()


def _cached_urls() -> set[str]:
    return {r.get("url", "") for r in load_corpus()}


def _record(cb: str, d: date, url: str, text: str, *, source_format: str,
            published_raw: str, extra: dict | None = None) -> dict:
    return {
        "cb": cb,
        "date": d.isoformat(),
        "doc_type": {
            "fed": "FOMC statement",
            "ecb": "monetary policy decisions press release",
            "boe": "Monetary Policy Summary",
            "boj": "Statement on Monetary Policy (English)",
        }[cb],
        "url": url,
        "published_raw": published_raw,
        "source_format": source_format,
        "text": text,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "n_chars": len(text),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **(extra or {}),
    }


def fetch_fed(year: int) -> list[dict]:
    recs = []
    for d, url in discover_fed(year):
        if _cached_date("fed", d):      # 既取得は再取得しない (idempotent)
            continue
        text = extract_container(_fetch(url), FED_SELECTORS)
        recs.append(_record("fed", d, url, text, source_format="html",
                            published_raw=d.isoformat()))
        time.sleep(SLEEP_SEC)
    return recs


def fetch_ecb(year: int) -> list[dict]:
    recs = []
    for d, url in discover_ecb(year):
        if _cached_date("ecb", d):      # 既取得は再取得しない (idempotent)
            continue
        text = extract_container(_fetch(url), ECB_SELECTORS)
        recs.append(_record("ecb", d, url, text, source_format="html",
                            published_raw=d.isoformat()))
        time.sleep(SLEEP_SEC)
    return recs


def fetch_boj(year: int) -> list[dict]:
    recs = []
    for d, url in discover_boj(year):
        if _cached_date("boj", d):       # 既取得は再取得しない (idempotent)
            continue
        if url.lower().endswith(".pdf"):
            container, fmt = _fetch_pdf_text(url), "pdf"
        else:
            container, fmt = extract_container(_fetch(url), BOJ_SELECTORS), "html"
        # V3 (lookahead): 英語版に印字された日付が会合日 (URL 日付) と一致するか
        # を機械確認する。不一致は same_day_attested=False として census が数える。
        printed = _boj_printed_date(container)
        recs.append(_record(
            "boj", d, url, container, source_format=fmt,
            published_raw=printed.isoformat() if printed else "",
            extra={"same_day_attested": bool(printed and printed == d)},
        ))
        time.sleep(SLEEP_SEC)
    return recs


_BOJ_DATE_RE = re.compile(r"(January|February|March|April|May|June|July|August|"
                          r"September|October|November|December)\s+(\d{1,2}),\s+(\d{4})")


def _boj_printed_date(text: str) -> date | None:
    m = _BOJ_DATE_RE.search(text[:600])
    if not m:
        return None
    try:
        return datetime.strptime(" ".join(m.groups()), "%B %d %Y").date()
    except ValueError:
        return None


def _boe_pub_date(text: str) -> tuple[date | None, str]:
    m = BOE_PUBLISHED_RE.search(text)
    if not m:
        return None, ""
    try:
        return datetime.strptime(m.group(1), "%d %B %Y").date(), m.group(1)
    except ValueError:
        return None, m.group(1)


def _fetch_pdf_text(url: str) -> str:
    """BOE MPS の PDF 版本文 (公式サイトの同一文書種の別コンテナ)."""
    import io

    import pdfplumber
    import requests

    resp = requests.get(url, headers={"User-Agent": UA}, timeout=90)
    if resp.status_code != 200 or "pdf" not in (
            resp.headers.get("content-type") or "").lower():
        raise NotFound(f"no pdf: {url} (HTTP {resp.status_code})")
    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
        pages = [(page.extract_text() or "") for page in pdf.pages]
    return _norm("\n".join(pages))


def fetch_boe(year: int) -> list[dict]:
    """BOE MPS: 公式 HTML ページを一次、同月の公式 PDF を二次 (同一文書種).

    2020 年以前の公式ページは MPS 本文を HTML に載せず PDF のみで配布するため、
    HTML で MPS 節境界が取れない月は PDF へフォールバックする。**文書種は同じ
    (MPS)**、境界語も同一 — 変えているのはコンテナだけで、シグナル DoF ではない。
    """
    recs = []
    seen = _cached_urls()
    for month, url in discover_boe(year):
        if url in seen or BOE_PDF_TMPL.format(year=year, month=month) in seen:
            continue                      # 既取得は再取得しない (idempotent)
        mps, pub, pub_raw, fmt, src = "", None, "", "html", url
        try:
            container = extract_container(_fetch(url), BOE_SELECTORS)
            mps = extract_boe_mps(container)
            pub, pub_raw = _boe_pub_date(container)
        except NotFound:
            container = ""
        if not mps or pub is None:
            pdf_url = BOE_PDF_TMPL.format(year=year, month=month)
            try:
                text = _fetch_pdf_text(pdf_url)
                mps_pdf = extract_boe_mps(text)
                pub_pdf, raw_pdf = _boe_pub_date(text)
                if mps_pdf and pub_pdf is not None:
                    mps, pub, pub_raw, fmt, src = (
                        mps_pdf, pub_pdf, raw_pdf, "pdf", pdf_url)
            except (NotFound, Exception):  # noqa: B014 - 取得不能は機械的欠測
                pass
            time.sleep(SLEEP_SEC)
        if not mps or pub is None:
            recs.append(_record(
                "boe", date(year, MONTHS.index(month) + 1, 1), url, "",
                source_format=fmt, published_raw=pub_raw,
                extra={"missing_reason": "no_mps_boundary_html_or_pdf"}))
        else:
            recs.append(_record("boe", pub, src, mps, source_format=fmt,
                                published_raw=pub_raw))
        time.sleep(SLEEP_SEC)
    return recs


FETCHERS = {"fed": fetch_fed, "ecb": fetch_ecb, "boe": fetch_boe, "boj": fetch_boj}


# ---------------------------------------------------------------- storage


def _doc_path(cb: str, d: str) -> Path:
    return CORPUS_DIR / cb / f"{d}.json"


def save(rec: dict, *, refetch: bool) -> bool:
    path = _doc_path(rec["cb"], rec["date"])
    if path.exists() and not refetch:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")
    return True


def load_corpus() -> list[dict]:
    out: list[dict] = []
    for cb in CBS:
        for path in sorted((CORPUS_DIR / cb).glob("*.json")):
            out.append(json.loads(path.read_text(encoding="utf-8")))
    return out


def write_manifest() -> dict:
    """pre-reg §2「sha256 + 行数 manifest pin」の コーパス側 manifest."""
    docs = load_corpus()
    per_cb: dict[str, dict] = {}
    for rec in docs:
        entry = per_cb.setdefault(rec["cb"], {"n_docs": 0, "docs": {}})
        entry["n_docs"] += 1
        entry["docs"][rec["date"]] = {
            "sha256": rec["text_sha256"],
            "n_chars": rec["n_chars"],
            "url": rec["url"],
        }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prereg": "knowledge-base/wiki/decisions/"
                  "e23-cb-text-explore-prereg-2026-09-10.md",
        "pass": "pass-0 (outcome 非接触)",
        "explore_window": [EXPLORE_START.isoformat(), EXPLORE_END.isoformat()],
        "oos_window": [OOS_START.isoformat(), OOS_END.isoformat()],
        "n_docs_total": len(docs),
        "per_cb": per_cb,
    }
    path = CORPUS_DIR / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")
    return payload


# ---------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cb", nargs="*", default=list(CBS), choices=list(CBS))
    ap.add_argument("--years", nargs="*", type=int, default=None)
    ap.add_argument("--refetch", action="store_true")
    ap.add_argument("--offline", action="store_true",
                    help="取得せず manifest のみ再生成")
    args = ap.parse_args(argv)

    if args.offline:
        payload = write_manifest()
        print(f"manifest: {payload['n_docs_total']} docs")
        return 0

    years = args.years or list(range(EXPLORE_START.year, OOS_END.year + 1))
    total_new = 0
    for cb in args.cb:
        for year in years:
            try:
                recs = FETCHERS[cb](year)
            except NotFound as exc:
                print(f"[{cb} {year}] index absent ({exc}) — skip", file=sys.stderr)
                continue
            except Exception as exc:  # noqa: BLE001
                print(f"[{cb} {year}] ERROR {exc}", file=sys.stderr)
                continue
            new = sum(save(r, refetch=args.refetch) for r in recs)
            total_new += new
            print(f"[{cb} {year}] discovered={len(recs)} new={new}")
    payload = write_manifest()
    print(f"done: new={total_new} corpus_total={payload['n_docs_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
