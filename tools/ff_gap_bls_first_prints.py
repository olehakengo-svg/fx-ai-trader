#!/usr/bin/env python3
"""ff_gap_bls_first_prints.py — NFP/CPI の first print actual を BLS 一次リリースから抽出.

位置づけ (e15-e7-event-modality-prereg §3.3 phase-1 データ付録):
  R4F dump の actual 列は 2023-08 で充填停止 (ff_gap_prepare_r4f.py 実測)。E7 の
  判定対象系列 (NFP headline / CPI headline m/m) の actual は、翌期 previous 逆引き
  (= 改定値) ではなく **BLS 一次リリースの first print** をここで抽出して補完する。
  アクセス経路は §3.2b AMENDMENT の前例どおり Wayback (`id_` raw モード) 経由の
  BLS アーカイブページ (`bls.gov/news.release/archives/{empsit,cpi}_MMDDYYYY.htm`)。
  release date と event_time_utc は E15 canonical カレンダー
  (`e15_e7_event_calendar.json` — 一次ソース由来、per-date DST 変換済み) を使う。

パーサ較正 (組み込み):
  R4F に actual が残っている重複区間 (2023-04〜08) では、抽出 first print と
  R4F actual (= FF 表示値) の**完全一致を要求** (mismatch は fail-loud で報告)。

出力:
  - knowledge-base/raw/bt-results/e7/ff_gap_bls_first_prints.csv (import 互換)
  - 同 dir に ledger json (URL / wayback ts / sha256 / 抽出文 / 突合結果)

規律: モジュールトップ副作用なし / silent except なし / politeness 2s。

CLI:
  python3 tools/ff_gap_bls_first_prints.py fetch      # Wayback 取得 + 抽出 (network)
  python3 tools/ff_gap_bls_first_prints.py rebuild    # 取得済み snapshot から再抽出 (offline)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html as html_mod
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from tools import event_calendar_build as B  # noqa: E402  (_http_get / WB / politeness)

CAL_JSON = os.path.join(_REPO, "knowledge-base", "raw", "bt-results",
                        "e15_e7_event_calendar.json")
R4F_CSV = os.path.join(_REPO, "knowledge-base", "raw", "bt-results", "e7",
                       "ff_calendar_r4f_2014_2026.csv")
OUT_DIR = os.path.join(_REPO, "knowledge-base", "raw", "bt-results", "e7")
SNAP_DIR = os.path.join(_REPO, "data", "cache", "rates", "raw", "bls_releases")

RANGE_START = "2023-04-01"    # R4F 重複区間を含めてパーサ較正
RANGE_END = "2026-06-30"      # OOS 窓終端 (§3.4)
CDX = ("http://web.archive.org/cdx/search/cdx?url={url}"
       "&output=json&filter=statuscode:200&limit=-1")

SERIES = {
    "NFP": {"prefix": "empsit", "ff_title": "Non-Farm Employment Change"},
    "CPI": {"prefix": "cpi", "ff_title": "CPI m/m"},
}

_TAG_RE = re.compile(r"<[^>]+>")

# 2025 年秋の政府閉鎖で BLS が複数月合算の headline を出した月がある
# (例: CPI 2025-12-18 「increased 0.2 percent … over the 2 months from September
# 2025 to November 2025」)。合算値は m/m first print ではないため import から除外する。
_MULTI_MONTH_RE = re.compile(r"over the \d+\s*months", re.IGNORECASE)

# NFP: 最初の headline 数値 (千人単位カンマ区切り)。順に試す (先勝ち)。
_NFP_PATTERNS = (
    ("paren", re.compile(
        r"nonfarm payroll employment[^.]{0,260}?\(\s*([+−-]?\s?[\d,]{2,9})\s*\)",
        re.IGNORECASE | re.DOTALL)),
    ("by_up", re.compile(
        r"nonfarm payroll employment[^.]{0,260}?"
        r"(?:increased|rose|grew|expanded|edged up)\s+by\s+([\d,]{2,9})",
        re.IGNORECASE | re.DOTALL)),
    ("by_down", re.compile(
        r"nonfarm payroll employment[^.]{0,260}?"
        r"(?:declined|decreased|fell|edged down)\s+by\s+([\d,]{2,9})",
        re.IGNORECASE | re.DOTALL)),
    ("unchanged", re.compile(
        r"nonfarm payroll employment\s+was\s+unchanged", re.IGNORECASE)),
)

# CPI: headline m/m (seasonally adjusted)。
_CPI_PATTERNS = (
    ("pct_up", re.compile(
        r"\(CPI-U\)\s+(?:rose|increased|advanced)\s+([\d.]+)\s+percent",
        re.IGNORECASE)),
    ("pct_down", re.compile(
        r"\(CPI-U\)\s+(?:declined|decreased|fell)\s+([\d.]+)\s+percent",
        re.IGNORECASE)),
    ("unchanged", re.compile(
        r"\(CPI-U\)\s+was\s+(?:unchanged|virtually unchanged)", re.IGNORECASE)),
)


def strip_html(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text,
                  flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"\s+", " ", html_mod.unescape(_TAG_RE.sub(" ", text)))


def extract_nfp(text: str) -> tuple:
    """(FF 形式値 '187K'/'-33K'/'0K', 抽出根拠文の断片)。抽出不能は ValueError。

    **出現位置が最も早い**パターンを採用する (先勝ちを「パターン種類順」にすると、
    「edged down by 92,000 …, following (+126,000)」型の文で後方の改定値括弧を
    誤採用する — 2026-03-06 リリースで実確認したバグ)。
    """
    hits = []
    for kind, pat in _NFP_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append((m.end(), kind, m))
    if not hits:
        raise ValueError("NFP headline が抽出不能 — パターン追加を検討 (fail-loud)")
    _, kind, m = min(hits, key=lambda h: h[0])
    ctx = text[max(0, m.start() - 40): m.end() + 200]
    if kind == "unchanged":
        return "0K", ctx
    num = m.group(1).replace(" ", "").replace("−", "-")
    val = int(num.replace(",", ""))
    if kind == "by_down":
        val = -abs(val)
    if abs(val) % 1000 != 0 or abs(val) > 2_000_000:
        raise ValueError(f"NFP 値が千人単位でない: {num!r} ({ctx!r})")
    return f"{val // 1000}K", ctx


def extract_cpi(text: str) -> tuple:
    """NFP と同じく**出現位置が最も早い**パターンを採用 (kind 順優先だと
    「was unchanged in October … increased 3.2 percent over the last 12 months」型の
    文書で後方の y/y 値を誤採用 — 2023-11-14 等 4 リリースで実確認したバグ)。"""
    hits = []
    for kind, pat in _CPI_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append((m.end(), kind, m))
    if not hits:
        raise ValueError("CPI headline が抽出不能 — パターン追加を検討 (fail-loud)")
    _, kind, m = min(hits, key=lambda h: h[0])
    ctx = text[max(0, m.start() - 40): m.end() + 200]
    if kind == "unchanged":
        return "0.0%", ctx
    sign = "-" if kind == "pct_down" else ""
    return f"{sign}{float(m.group(1)):.1f}%", ctx


def load_canonical() -> dict:
    """{series: [(release_date 'YYYY-MM-DD', event_time_utc ISO)]} (RANGE 内)。"""
    ev = json.load(open(CAL_JSON, encoding="utf-8"))
    ev = ev.get("events", ev)
    out = {}
    for series in SERIES:
        rows = []
        for iso in sorted(ev[series]):
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)
            d = dt.strftime("%Y-%m-%d")
            if RANGE_START <= d <= RANGE_END:
                rows.append((d, dt.strftime("%Y-%m-%dT%H:%M:%SZ")))
        out[series] = rows
    return out


def load_r4f_actuals() -> dict:
    """{(title, event_time_utc): actual} — 較正用 (actual 非空のみ)。"""
    out = {}
    with open(R4F_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["country"] == "USD" and row["actual"]:
                out[(row["title"], row["event_time_utc"])] = row["actual"]
    return out


def snap_path(prefix: str, release_date: str) -> str:
    return os.path.join(SNAP_DIR, f"{prefix}_{release_date}.html")


def fetch_release(prefix: str, release_date: str) -> tuple:
    """(bytes, wayback_ts, source_url)。CDX で最新 snapshot を選び id_ raw で取得。"""
    mmddyyyy = f"{release_date[5:7]}{release_date[8:10]}{release_date[:4]}"
    url = f"https://www.bls.gov/news.release/archives/{prefix}_{mmddyyyy}.htm"
    cdx_raw = B._http_get(CDX.format(url=url))
    rows = json.loads(cdx_raw or b"[]")
    if len(rows) < 2:
        raise RuntimeError(f"Wayback snapshot なし: {url}")
    ts = rows[-1][1]  # 最新 snapshot
    time.sleep(B.POLITENESS_S)
    body = B._http_get(B.WB.format(ts=ts, url=url))
    time.sleep(B.POLITENESS_S)
    return body, ts, url


def run(fetch: bool = True) -> dict:
    canonical = load_canonical()
    r4f = load_r4f_actuals()
    os.makedirs(SNAP_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    ledger, import_rows = [], []
    mismatches, failures = [], []
    for series, meta in SERIES.items():
        extractor = extract_nfp if series == "NFP" else extract_cpi
        for release_date, event_iso in canonical[series]:
            sp = snap_path(meta["prefix"], release_date)
            entry = {"series": series, "release_date": release_date,
                     "event_time_utc": event_iso}
            try:
                if os.path.exists(sp):
                    body = open(sp, "rb").read()
                    entry["snapshot"] = os.path.relpath(sp, _REPO) + " (cached)"
                elif fetch:
                    body, ts, url = fetch_release(meta["prefix"], release_date)
                    with open(sp, "wb") as fh:
                        fh.write(body)
                    entry["wayback_ts"] = ts
                    entry["source_url"] = url
                else:
                    raise RuntimeError(f"snapshot なし (offline rebuild): {sp}")
                entry["sha256"] = hashlib.sha256(body).hexdigest()
                value, ctx = extractor(strip_html(body))
                entry["first_print"] = value
                entry["evidence"] = ctx.strip()
            except (RuntimeError, ValueError) as exc:
                entry["error"] = str(exc)
                failures.append(f"{series} {release_date}: {exc}")
                ledger.append(entry)
                continue
            if _MULTI_MONTH_RE.search(entry["evidence"]):
                entry["excluded"] = ("multi-month combined figure (shutdown gap) — "
                                     "m/m first print ではないため import 除外")
                ledger.append(entry)
                continue
            ref = r4f.get((meta["ff_title"], event_iso))
            if ref is not None:
                entry["r4f_actual"] = ref
                entry["calibration_match"] = (ref == value)
                if ref != value:
                    mismatches.append(f"{series} {release_date}: BLS={value} R4F={ref}")
            import_rows.append({
                "country": "USD", "title": meta["ff_title"],
                "event_time_utc": event_iso, "impact": "High",
                "forecast": "", "previous": "", "actual": value,
            })
            ledger.append(entry)

    out_csv = os.path.join(OUT_DIR, "ff_gap_bls_first_prints.csv")
    cols = ["country", "title", "event_time_utc", "impact",
            "forecast", "previous", "actual"]
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(import_rows)
    excluded = [f"{e['series']} {e['release_date']}: {e['excluded']}"
                for e in ledger if e.get("excluded")]
    summary = {
        "tool": "ff_gap_bls_first_prints",
        "range": [RANGE_START, RANGE_END],
        "extracted": len(import_rows),
        "excluded_multi_month": excluded,
        "calibration_checked": sum(1 for e in ledger if "calibration_match" in e),
        "calibration_mismatches": mismatches,
        "failures": failures,
        "out_csv": {"path": os.path.relpath(out_csv, _REPO),
                    "sha256": hashlib.sha256(open(out_csv, "rb").read()).hexdigest()},
        "ledger": ledger,
    }
    lpath = os.path.join(OUT_DIR, "ff_gap_bls_ledger.json")
    with open(lpath, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    print(f"extracted {len(import_rows)} first prints → {out_csv}")
    print(f"calibration: {summary['calibration_checked']} checked, "
          f"{len(mismatches)} mismatches")
    for m in mismatches:
        print(f"  MISMATCH: {m}")
    for x in excluded:
        print(f"  EXCLUDED: {x}")
    for f_ in failures:
        print(f"  FAIL: {f_}")
    print(f"ledger: {lpath}")
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode")
    sub.add_parser("fetch")
    sub.add_parser("rebuild")
    args = parser.parse_args(argv)
    if args.mode not in ("fetch", "rebuild"):
        parser.print_help()
        return 1
    summary = run(fetch=(args.mode == "fetch"))
    return 1 if (summary["failures"] or summary["calibration_mismatches"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
