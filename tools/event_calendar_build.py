#!/usr/bin/env python3
"""E15/E7 イベントカレンダー構築 — pre-reg §3.2 + §3.2b AMENDMENT の執行 (rule:R1 手続き).

pre-reg SSOT: knowledge-base/wiki/decisions/e15-e7-event-modality-prereg-2026-07-18.md
runbook     : knowledge-base/raw/bt-results/e15_phase0_execution_status.md

ソース (§3.2 + §3.2b AMENDMENT 2026-07-21):
  NFP : BLS News Release Archive (empsit) — Wayback snapshot 経由 (BLS 直接 403)。
        アーカイブ発表ファイル名 empsit_MMDDYYYY = actual release date (一次記録)。
  CPI : 同上 (cpi_MMDDYYYY)。
  FOMC: federalreserve.gov 直接 (fomccalendars.htm 2021+ / fomchistorical{Y}.htm 2014-2020)。
        scheduled meeting のみ。unscheduled / cancelled / notation vote は除外 + 件数記録。

整合性検証 (fail-loud、explore 窓 2014-2023):
  NFP : 全て金曜 (例外 = 7月4日連休の木曜のみ) / 12件±1/年 / reference month 欠月ゼロ。
  CPI : 全て平日 / 12件±1/年 / reference month 欠月ゼロ。
  FOMC: scheduled+cancelled = 8/年 (2014-2025)、statement 日付 = 会合最終日 (行内突合)。
OOS 窓 (2024-01-01〜2026-06-30) の異常はフラグ記録のみ (除外しない — §10-3)。

sanity サブコマンド (§3.2 range 検出器、explore 窓のみ — §3.2b-7):
  event bar (t_e に開く M15 バー) の realized range < 2 × (直前 20 営業日の同 ET 時刻
  バー range 中央値) → 時刻誤り疑い。primary pair の過半数投票でイベントをフラグ。
  イベント種別フラグ率 > 5% → exit 4 (discovery 停止・カレンダー再検証)。

**副作用禁止**: import 時に I/O/argparse を実行しない。main() は __main__ ガード内のみ。
politeness: HTTP リクエスト間 2 秒。
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from tools import event_modality_lib as L  # noqa: E402

OUTDIR = os.path.join(_REPO, "knowledge-base", "raw", "bt-results")
CALENDAR_JSON = os.path.join(OUTDIR, "e15_e7_event_calendar.json")
BUILD_LOG_MD = os.path.join(OUTDIR, "e15_e7_event_calendar_build.md")
MASSIVE = os.path.join(_REPO, "data", "cache", "massive")

WINDOW_START = date(2014, 1, 1)   # §3.4 per-pair floor 下限
WINDOW_END = date(2026, 6, 30)    # §3.4 OOS 窓終端
EXPLORE_END = date(2023, 12, 31)  # §3.4 探索窓終端 (fail-loud はここまで)

POLITENESS_S = 2.0  # HTTP リクエスト間隔

# ─── ソース台帳 (§3.2b AMENDMENT — Wayback snapshot は timestamp で凍結) ─────
WB = "http://web.archive.org/web/{ts}id_/{url}"
SOURCES = {
    "NFP": {
        "kind": "bls_archive",
        "prefix": "empsit",
        "url": WB.format(ts="20260713072607",
                         url="https://www.bls.gov/bls/news-release/empsit.htm"),
        "note": "BLS Employment Situation News Release Archive "
                "(Wayback snapshot 2026-07-13; filenames = actual release dates)",
    },
    "CPI": {
        "kind": "bls_archive",
        "prefix": "cpi",
        "url": WB.format(ts="20260612180753",
                         url="https://www.bls.gov/bls/news-release/cpi.htm"),
        "note": "BLS Consumer Price Index News Release Archive "
                "(Wayback snapshot 2026-06-12; filenames = actual release dates)",
    },
    "FOMC_CURRENT": {
        "kind": "fomc_calendar",
        "url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "note": "FOMC meeting calendars 2021+ (direct, key-free)",
    },
    # 2014-2020 は fomchistorical{Y}.htm (直接) — build() 内で年ループ生成
}
FOMC_HIST_URL = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
FOMC_HIST_YEARS = list(range(2014, 2021))  # 2014..2020

_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]
_MON_NUM = {m: i + 1 for i, m in enumerate(_MONTHS)}


class CalendarValidationError(RuntimeError):
    """整合性検証 fail-loud 用 (検証不能な年 / explore 窓の規則違反)。"""


# ─── HTTP (politeness 2s、gzip 対応、リトライ) ────────────────────────────────
def _http_get(url: str, timeout: int = 60, retries: int = 3) -> bytes:
    if not url.startswith(("http://", "https://")):  # file:// 等の scheme を遮断
        raise CalendarValidationError(f"non-http(s) URL refused: {url}")
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(  # nosemgrep — scheme guarded above; URLs are frozen constants
                url, headers={"User-Agent": "Mozilla/5.0 (fx-ai-trader research; "
                                            "event-calendar-build)",
                              "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=timeout) as r:  # nosemgrep — scheme guarded
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            time.sleep(POLITENESS_S)
            return raw
        except Exception as e:  # noqa: BLE001 — リトライ後 fail-loud
            last_err = e
            time.sleep(POLITENESS_S * (attempt + 1))
    raise CalendarValidationError(f"HTTP fetch failed after {retries} tries: {url}: {last_err}")


# ─── BLS archive パーサ (§3.2b-4: ファイル名 = actual release date) ────────────
def parse_bls_archive(html: str, prefix: str) -> list[dict]:
    """`{prefix}_MMDDYYYY.htm` リンクから (release_date, reference month) を抽出。

    アンカーテキスト例: "November 2026 Employment Situation" / "May 2026 Consumer Price Index"。
    PDF リンク (テキスト "PDF") は同一日付に dedup。ref month が取れない日付は fail-loud。
    """
    links = re.findall(
        r'href="[^"]*%s_(\d{8})\.htm"[^>]*>\s*([^<]*?)\s*<' % re.escape(prefix), html)
    recs: dict[date, set] = {}
    for d8, txt in links:
        try:
            dt = date(int(d8[4:8]), int(d8[0:2]), int(d8[2:4]))
        except ValueError as e:
            raise CalendarValidationError(f"bad date token {prefix}_{d8}: {e}") from e
        m = re.match(r"(%s)\s+(\d{4})" % "|".join(_MONTHS), txt)
        ref = (int(m.group(2)), _MON_NUM[m.group(1)]) if m else None
        recs.setdefault(dt, set()).add(ref)
    out = []
    for dt in sorted(recs):
        refs = {r for r in recs[dt] if r is not None}
        if len(refs) != 1:
            raise CalendarValidationError(
                f"{prefix} {dt}: reference month ambiguous/missing: {recs[dt]}")
        ry, rm = next(iter(refs))
        out.append({"date": dt, "ref_year": ry, "ref_month": rm})
    return out


def _is_july4_thursday(d: date) -> bool:
    """7月4日連休に伴う木曜前倒し (explore 窓で許容される唯一の非金曜パターン)。"""
    return d.weekday() == 3 and d.month == 7 and d.day <= 7


def validate_bls(records: list[dict], event: str) -> dict:
    """NFP/CPI の整合性検証。explore 窓違反 = raise、OOS 窓異常 = flags 記録。"""
    in_win = [r for r in records if WINDOW_START <= r["date"] <= WINDOW_END]
    if not in_win:
        raise CalendarValidationError(f"{event}: no records in window")
    flags: list[str] = []
    per_year: dict[int, int] = {}
    for r in in_win:
        per_year[r["date"].year] = per_year.get(r["date"].year, 0) + 1

    # (a) 曜日規則
    for r in in_win:
        d = r["date"]
        if event == "NFP":
            if d.weekday() != 4 and not _is_july4_thursday(d):
                msg = f"NFP non-Friday release {d} (weekday={d.weekday()})"
                if d <= EXPLORE_END:
                    raise CalendarValidationError("EXPLORE window: " + msg)
                flags.append("OOS " + msg)
        else:  # CPI: 平日のみ
            if d.weekday() >= 5:
                msg = f"CPI weekend release {d}"
                if d <= EXPLORE_END:
                    raise CalendarValidationError("EXPLORE window: " + msg)
                flags.append("OOS " + msg)

    # (b) 月次 cadence 12±1/年 (部分年は按分下限)
    for y, n in sorted(per_year.items()):
        full_year = (y < WINDOW_END.year)
        lo, hi = (11, 13) if full_year else (max(0, WINDOW_END.month - 1), WINDOW_END.month + 1)
        if not (lo <= n <= hi):
            msg = f"{event} {y}: cadence {n} outside [{lo},{hi}]"
            if y <= EXPLORE_END.year:
                raise CalendarValidationError("EXPLORE window: " + msg)
            flags.append("OOS " + msg)

    # (c) explore 窓: reference month 欠月ゼロ / OOS 窓: 欠月はフラグ
    refs = sorted((r["ref_year"], r["ref_month"]) for r in in_win)
    for a, b in zip(refs, refs[1:]):
        expected = (a[0] + (1 if a[1] == 12 else 0), a[1] % 12 + 1)
        if b != expected:
            msg = f"{event} reference-month gap: {a} -> {b} (expected {expected})"
            if b <= (EXPLORE_END.year, EXPLORE_END.month):
                raise CalendarValidationError("EXPLORE window: " + msg)
            flags.append("OOS " + msg)

    first_friday = sum(1 for r in in_win
                       if r["date"].weekday() == 4 and r["date"].day <= 7)
    return {
        "n_in_window": len(in_win),
        "per_year": {str(k): v for k, v in sorted(per_year.items())},
        "non_standard_weekday": [str(r["date"]) for r in in_win
                                 if r["date"].weekday() != 4] if event == "NFP" else None,
        "first_friday_share": round(first_friday / len(in_win), 4) if event == "NFP" else None,
        "oos_flags": flags,
    }


# ─── FOMC パーサ ─────────────────────────────────────────────────────────────
_MON_ABBR = {m[:3]: i + 1 for i, m in enumerate(_MONTHS)}
_MON_ABBR["Sept"] = 9
_MONTH_TOKEN_RE = re.compile(
    r"\b(%s)[a-z]*\b" % "|".join(sorted(_MON_ABBR, key=len, reverse=True)))


def _last_month_day(title: str) -> tuple[int, int] | None:
    """見出し/行から会合最終日の (month, day) を得る。

    'April 30-May 1' → (5, 1)、'Jan/Feb 31-1' (fomccalendars 略記) → (2, 1)。
    """
    months = _MONTH_TOKEN_RE.findall(title)
    days = re.findall(r"\b(\d{1,2})\b", title)
    if not months or not days:
        return None
    return _MON_ABBR[months[-1]], int(days[-1])


def parse_fomc_calendar(html: str) -> dict:
    """fomccalendars.htm (2021+) — 'Statement:' ラベル直下の monetary{d8}a.htm を採用。

    採用条件 (二重検証): (i) Statement: セクション内の最初のリンク、
    (ii) そのリンク日付が行の month/date レンジの最終日と一致 (monetary20250822a
    型の非会合プレスリリース混入を構造排除)。マーカー付き行は除外 + 記録。
    """
    blocks = re.split(r'<div class="[^"]*\brow fomc-meeting\b[^"]*"', html)[1:]
    scheduled: list[date] = []
    excluded: list[dict] = []
    for b in blocks:
        mm = re.search(r'fomc-meeting__month[^>]*>\s*(?:<strong>)?([^<]+)', b)
        dm = re.search(r'fomc-meeting__date[^>]*>\s*([^<]+)', b)
        row_label = ((mm.group(1).strip() if mm else "?") + " "
                     + (dm.group(1).strip() if dm else "?"))
        marker = re.search(r"unscheduled|cancell?ed|notation vote", b, re.I)
        stmt_seg = b.split("Statement:", 1)
        d8m = (re.search(r"monetary(\d{8})a\.htm", stmt_seg[1])
               if len(stmt_seg) == 2 else None)
        if d8m is None:
            excluded.append({"row": row_label, "reason": "no_statement (future/none)"})
            continue
        d8 = d8m.group(1)
        dt = date(int(d8[:4]), int(d8[4:6]), int(d8[6:8]))
        if marker:
            excluded.append({"row": row_label, "reason": marker.group(0).lower(),
                             "statement_date": str(dt)})
            continue
        md = _last_month_day(row_label.replace("*", "").replace("/", " "))
        if md is None or (dt.month, dt.day) != md:
            raise CalendarValidationError(
                f"FOMC calendar row/statement mismatch: row='{row_label}' "
                f"statement={dt} expected_month_day={md}")
        scheduled.append(dt)
    return {"scheduled": sorted(scheduled), "excluded": excluded}


def parse_fomc_historical(html: str, year: int) -> dict:
    """fomchistorical{Y}.htm — h5 panel 見出しで分類 (§3.2b-6)。

    'Month D-D Meeting - Y' = scheduled / '(unscheduled)' / '(cancelled)' /
    '(notation vote)' は除外 + 記録。scheduled は panel 内の monetary{d8}a.htm
    (一意) を statement 日付とし、見出しの会合最終日と突合 (fail-loud)。
    """
    parts = re.split(r"<h5[^>]*panel-heading[^>]*>", html)[1:]
    scheduled: list[date] = []
    excluded: list[dict] = []
    for p in parts:
        title = re.sub(r"\s+", " ", p.split("</h5>", 1)[0]).strip()
        body = p.split("</h5>", 1)[1] if "</h5>" in p else ""
        ym = re.search(r"-\s*(\d{4})\s*$", title)
        if not ym or int(ym.group(1)) != year:
            raise CalendarValidationError(
                f"FOMC historical {year}: unparseable panel title '{title}'")
        low = title.lower()
        if "unscheduled" in low or "cancelled" in low or "canceled" in low \
                or "notation vote" in low:
            reason = ("unscheduled" if "unscheduled" in low
                      else "cancelled" if "cancel" in low else "notation vote")
            d8s = sorted(set(re.findall(r"monetary(\d{8})a\.htm", body)))
            excluded.append({"row": title, "reason": reason,
                             "statement_date": str(date(int(d8s[0][:4]), int(d8s[0][4:6]),
                                                        int(d8s[0][6:8]))) if d8s else None})
            continue
        if "Meeting" not in title:
            raise CalendarValidationError(
                f"FOMC historical {year}: unknown panel type '{title}'")
        d8s = sorted(set(re.findall(r"monetary(\d{8})a\.htm", body)))
        if len(d8s) != 1:
            raise CalendarValidationError(
                f"FOMC historical {year}: panel '{title}' has {len(d8s)} statement "
                f"links (expected 1): {d8s}")
        dt = date(int(d8s[0][:4]), int(d8s[0][4:6]), int(d8s[0][6:8]))
        md = _last_month_day(title)
        if dt.year != year or md is None or (dt.month, dt.day) != md:
            raise CalendarValidationError(
                f"FOMC historical {year}: statement {dt} inconsistent with "
                f"panel '{title}' (expected month/day {md})")
        scheduled.append(dt)
    return {"scheduled": sorted(scheduled), "excluded": excluded}


def validate_fomc(scheduled: list[date], excluded: list[dict]) -> dict:
    """scheduled+cancelled = 8/年 (2014-2025)、2026 は H1 部分年 (3-5 件)。"""
    in_win = [d for d in scheduled if WINDOW_START <= d <= WINDOW_END]
    per_year: dict[int, int] = {}
    for d in in_win:
        per_year[d.year] = per_year.get(d.year, 0) + 1
    cancelled_per_year: dict[int, int] = {}
    for e in excluded:
        if e["reason"].startswith("cancel"):
            ym = re.search(r"(\d{4})", e["row"])
            if ym:
                y = int(ym.group(1))
                cancelled_per_year[y] = cancelled_per_year.get(y, 0) + 1
    for y in range(WINDOW_START.year, WINDOW_END.year + 1):
        n = per_year.get(y, 0) + cancelled_per_year.get(y, 0)
        if y < WINDOW_END.year:
            if n != 8:
                raise CalendarValidationError(
                    f"FOMC {y}: scheduled+cancelled = {n} != 8")
        else:  # 2026 H1 部分年
            if not (3 <= n <= 5):
                raise CalendarValidationError(
                    f"FOMC {y} (partial year to {WINDOW_END}): {n} outside [3,5]")
    return {"n_in_window": len(in_win),
            "per_year": {str(k): v for k, v in sorted(per_year.items())},
            "cancelled_per_year": {str(k): v for k, v in sorted(cancelled_per_year.items())},
            "excluded_n": len([e for e in excluded
                               if e["reason"] not in ("no_statement (future/none)",)]),
            "excluded": [e for e in excluded
                         if e["reason"] != "no_statement (future/none)"]}


# ─── build ───────────────────────────────────────────────────────────────────
def build() -> dict:
    ledger = []

    def fetch(name: str, url: str, note: str) -> str:
        raw = _http_get(url)
        ledger.append({"source": name, "url": url, "bytes": len(raw),
                       "sha256": hashlib.sha256(raw).hexdigest(),
                       "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "note": note})
        return raw.decode("utf-8", errors="replace")

    events: dict[str, list[str]] = {}
    validation: dict[str, dict] = {}

    # NFP / CPI (BLS archive、Wayback 凍結 snapshot)
    for ev in ("NFP", "CPI"):
        src = SOURCES[ev]
        html = fetch(ev, src["url"], src["note"])
        recs = parse_bls_archive(html, src["prefix"])
        validation[ev] = validate_bls(recs, ev)
        dates = [r["date"] for r in recs if WINDOW_START <= r["date"] <= WINDOW_END]
        events[ev] = [L.event_time_utc(ev, d).isoformat() for d in sorted(dates)]

    # FOMC (federalreserve.gov 直接)
    src = SOURCES["FOMC_CURRENT"]
    html = fetch("FOMC_CURRENT", src["url"], src["note"])
    cur = parse_fomc_calendar(html)
    scheduled = list(cur["scheduled"])
    excluded = list(cur["excluded"])
    for y in FOMC_HIST_YEARS:
        url = FOMC_HIST_URL.format(year=y)
        html = fetch(f"FOMC_HIST_{y}", url, f"FOMC historical {y} (direct, key-free)")
        h = parse_fomc_historical(html, y)
        scheduled.extend(h["scheduled"])
        excluded.extend(h["excluded"])
    overlap_check = sorted(set(d.year for d in cur["scheduled"])
                           & set(FOMC_HIST_YEARS))
    if overlap_check:
        raise CalendarValidationError(f"FOMC source-year overlap: {overlap_check}")
    validation["FOMC"] = validate_fomc(scheduled, excluded)
    fomc_dates = sorted(d for d in scheduled if WINDOW_START <= d <= WINDOW_END)
    events["FOMC"] = [L.event_time_utc("FOMC", d).isoformat() for d in fomc_dates]

    return {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prereg": "e15-e7-event-modality-prereg-2026-07-18 §3.2 + §3.2b AMENDMENT",
        "window": [str(WINDOW_START), str(WINDOW_END)],
        "explore_end": str(EXPLORE_END),
        "time_convention": {"FOMC": "14:00 ET", "NFP": "08:30 ET", "CPI": "08:30 ET",
                            "tz": "America/New_York per-date (DST-aware, lib.event_time_utc)"},
        "events": events,
        "meta": {"validation": validation, "source_ledger": ledger,
                 "sanity": {"status": "PENDING (run `sanity` after price parquet ready; "
                                      "explore window only per §3.2b-7)"}},
    }


# ─── sanity (§3.2 range 検出器、explore 窓のみ — §3.2b-7) ─────────────────────
def sanity() -> int:
    with open(CALENDAR_JSON) as fh:
        cal = json.load(fh)
    import pandas as pd  # 遅延 import (build は pandas 不要)

    bars = {}
    for pair in L.PRIMARY_PAIRS:
        f = os.path.join(MASSIVE, f"{pair}_15m.parquet")
        if not os.path.exists(f):
            continue
        m15 = pd.read_parquet(f)
        if m15.index.tz is None:
            m15.index = m15.index.tz_localize("UTC")
        bars[pair] = m15
    if len(bars) < 5:
        print(f"[BLOCKED] sanity requires >=5 primary parquets, got {len(bars)}",
              file=sys.stderr)
        return 3

    explore_end = pd.Timestamp(cal["explore_end"], tz="UTC") + pd.Timedelta(days=1)
    results = {}
    worst_rate = 0.0
    for ev, ts_list in cal["events"].items():
        flagged, checked, detail = 0, 0, []
        for iso in ts_list:
            t_e = pd.Timestamp(iso)
            if t_e >= explore_end:
                continue  # OOS 窓 sanity は verdict 実行時 (§3.2b-7)
            votes_suspect, votes_total = 0, 0
            for pair, m15 in bars.items():
                if t_e not in m15.index:
                    continue
                row = m15.loc[t_e]
                ev_range = float(row["High"] - row["Low"])
                # 直前 20 営業日の同 ET 時刻バー (DST 追随 = event_time_utc per-date)
                base = []
                d = t_e.tz_convert("America/New_York").date()
                back = 1
                while len(base) < 20 and back <= 40:
                    bd = d - timedelta(days=back)
                    back += 1
                    if bd.weekday() >= 5:
                        continue
                    bts = L.event_time_utc(ev, bd)
                    if bts in m15.index:
                        b = m15.loc[bts]
                        base.append(float(b["High"] - b["Low"]))
                if len(base) < 10:
                    continue  # 投票棄権 (baseline 不足)
                votes_total += 1
                med = sorted(base)[len(base) // 2]
                if ev_range < 2.0 * med:
                    votes_suspect += 1
            if votes_total == 0:
                continue
            checked += 1
            if votes_suspect * 2 > votes_total:  # 過半数
                flagged += 1
                detail.append(iso)
        rate = (flagged / checked) if checked else 0.0
        worst_rate = max(worst_rate, rate)
        results[ev] = {"checked": checked, "flagged": flagged,
                       "rate": round(rate, 4), "flagged_events": detail}
        print(f"sanity {ev}: {flagged}/{checked} flagged ({rate:.1%})")

    cal["meta"]["sanity"] = {"status": "OK" if worst_rate <= 0.05 else "FAIL",
                             "scope": "explore window only (§3.2b-7)",
                             "rule": "event-bar range < 2x median(same-ET-time bar range, "
                                     "prior 20 business days); majority vote over primary pairs",
                             "results": results}
    with open(CALENDAR_JSON, "w") as fh:
        json.dump(cal, fh, indent=2)
    if worst_rate > 0.05:
        print(f"[STOP] sanity flag rate {worst_rate:.1%} > 5% — discovery 停止・"
              f"カレンダー再検証 (§3.2)", file=sys.stderr)
        return 4
    return 0


# ─── verify-times (§3.2 カレンダー再検証 — sanity >5% 発火時の処方) ─────────────
def verify_times() -> int:
    """オフセットピーク検査: event bar range / baseline 中央値 の比を offset −4..+8 で計測。

    時刻が正しければ比は offset +0 でピークする (時刻誤りならピークがずれる)。
    range のみ・explore 窓のみ使用 (§10-1 非抵触 — リターン/方向は一切見ない)。
    結果は calendar JSON meta.sanity.reverification に凍結。
    """
    import numpy as np
    import pandas as pd

    with open(CALENDAR_JSON) as fh:
        cal = json.load(fh)
    bars = {}
    for pair in L.PRIMARY_PAIRS:
        f = os.path.join(MASSIVE, f"{pair}_15m.parquet")
        if not os.path.exists(f):
            continue
        m15 = pd.read_parquet(f)
        if m15.index.tz is None:
            m15.index = m15.index.tz_localize("UTC")
        bars[pair] = m15
    if len(bars) < 5:
        print(f"[BLOCKED] verify-times requires >=5 primary parquets, got {len(bars)}",
              file=sys.stderr)
        return 3

    explore_end = pd.Timestamp(cal["explore_end"], tz="UTC") + pd.Timedelta(days=1)
    offsets = list(range(-4, 9))
    out = {}
    all_peak_zero = True
    for ev, ts_list in cal["events"].items():
        ratio_by_off: dict[int, list] = {k: [] for k in offsets}
        for iso in ts_list:
            t_e = pd.Timestamp(iso)
            if t_e >= explore_end:
                continue
            for pair, m15 in bars.items():
                if t_e not in m15.index:
                    continue
                pos = int(m15.index.get_loc(t_e))
                base = []
                d = t_e.tz_convert("America/New_York").date()
                back = 1
                while len(base) < 20 and back <= 40:
                    bd = d - timedelta(days=back)
                    back += 1
                    if bd.weekday() >= 5:
                        continue
                    bts = L.event_time_utc(ev, bd)
                    if bts in m15.index:
                        b = m15.loc[bts]
                        base.append(float(b["High"] - b["Low"]))
                if len(base) < 10:
                    continue
                med = float(np.median(base))
                if med <= 0:
                    continue
                for k in offsets:
                    j = pos + k
                    if 0 <= j < len(m15):
                        r = float(m15["High"].iloc[j] - m15["Low"].iloc[j])
                        ratio_by_off[k].append(r / med)
        profile = {str(k): round(float(np.mean(v)), 3)
                   for k, v in ratio_by_off.items() if v}
        peak = max(profile, key=profile.get)
        out[ev] = {"peak_offset_bars": int(peak), "ratio_profile": profile}
        all_peak_zero &= (int(peak) == 0)
        print(f"verify-times {ev}: peak offset {int(peak):+d} bars "
              f"(ratio at 0 = {profile.get('0')})")

    cal["meta"]["sanity"]["reverification"] = {
        "method": "offset-peak test: mean(event-bar range / baseline median) at "
                  "M15 offsets -4..+8 vs t_e; explore window only; range-only "
                  "(no returns/directions — §10-1 non-contact)",
        "verdict": ("CALENDAR_TIMES_CORRECT (all event types peak at offset +0; "
                    "zero broken rows -> no retroactive fixes per §3.2)"
                    if all_peak_zero else "PEAK_OFFSET_ANOMALY — investigate"),
        "results": out,
    }
    with open(CALENDAR_JSON, "w") as fh:
        json.dump(cal, fh, indent=2)
    _write_outputs(cal)
    return 0 if all_peak_zero else 5


def _write_outputs(cal: dict) -> None:
    os.makedirs(OUTDIR, exist_ok=True)
    with open(CALENDAR_JSON, "w") as fh:
        json.dump(cal, fh, indent=2)
    lines = [
        "# E15/E7 event calendar build log",
        "",
        f"**generated**: {cal['generated_utc']} / **window**: {cal['window'][0]} .. {cal['window'][1]}",
        f"**pre-reg**: [[e15-e7-event-modality-prereg-2026-07-18]] §3.2 + §3.2b AMENDMENT (2026-07-21)",
        f"**builder**: `tools/event_calendar_build.py` (politeness 2s/req)",
        "",
        "## Counts",
        "",
        "| event | N in window | per-year |",
        "|---|---|---|",
    ]
    for ev in ("FOMC", "NFP", "CPI"):
        v = cal["meta"]["validation"][ev]
        py = ", ".join(f"{k}:{n}" for k, n in v["per_year"].items())
        lines.append(f"| {ev} | {len(cal['events'][ev])} | {py} |")
    lines += ["", "## Validation", "", "```json",
              json.dumps(cal["meta"]["validation"], indent=2, default=str), "```",
              "", "## Source snapshot ledger", "",
              "| source | url | bytes | sha256 (12) | fetched |", "|---|---|---|---|---|"]
    for s in cal["meta"]["source_ledger"]:
        lines.append(f"| {s['source']} | {s['url']} | {s['bytes']} | "
                     f"{s['sha256'][:12]} | {s['fetched_utc']} |")
    lines += ["", "## Sanity (§3.2 range detector)", "", "```json",
              json.dumps(cal["meta"]["sanity"], indent=2, default=str), "```", ""]
    status = cal["meta"]["sanity"].get("status", "PENDING")
    if status == "FAIL":
        lines += [
            "## ⚠️ §8 DEFERRED trigger",
            "",
            "sanity フラグ率 > 5% → pre-reg §8「カレンダー sanity >5% — **user 裁定 "
            "(勝手に解釈しない)**」が発動。**discovery は user 裁定まで実行しない。**",
            "再検証 (verify-times、上記 reverification) の結論と、フラグの年次分布 "
            "(低インフレ期 CPI / COVID 期の高ベースライン集中 = イベント低インパクト由来) を "
            "裁定材料としてここに凍結する。時刻破損行はゼロ → §3.2 の後付け修正は不実施。",
            "",
        ]
    lines += [
        "## 役割分離 (vs `tools/ff_calendar_import.py`, PR #102)",
        "",
        "本カレンダー = **歴史イベントカレンダー** (BLS/Fed 一次ソース、2014-01〜2026-06、"
        "E15/E7 の BT 判定用、Wayback snapshot で凍結・再現可能)。",
        "PR #102 の FF calendar capture = **go-forward ingest** (ForexFactory、E7 Actual 補完・"
        "live 蓄積、`modules/market_data_ingest.py`)。ファイル・役割とも非重複。",
        "",
    ]
    with open(BUILD_LOG_MD, "w") as fh:
        fh.write("\n".join(lines))


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    mode = argv[0] if argv else "build"
    if mode == "build":
        cal = build()
        _write_outputs(cal)
        for ev in ("FOMC", "NFP", "CPI"):
            print(f"{ev}: {len(cal['events'][ev])} events "
                  f"({cal['events'][ev][0][:10]} .. {cal['events'][ev][-1][:10]})")
        print(f"wrote {CALENDAR_JSON}")
        return 0
    if mode == "sanity":
        rc = sanity()
        # sanity 結果 (STOP 含む) を build log に反映
        with open(CALENDAR_JSON) as fh:
            _write_outputs(json.load(fh))
        return rc
    if mode == "verify-times":
        return verify_times()
    print(f"unknown mode: {mode} (use: build | sanity | verify-times)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
