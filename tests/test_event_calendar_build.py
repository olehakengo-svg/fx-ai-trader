"""イベントカレンダー構築 (E15/E7 §3.2 + §3.2b AMENDMENT) のパーサ回帰 pin.

pre-reg: knowledge-base/wiki/decisions/e15-e7-event-modality-prereg-2026-07-18.md
オフライン fixture (実ページの書式を切り出した縮約 HTML) のみ使用 — ネット不要。

pin する契約:
  - BLS archive リンク (empsit/cpi_MMDDYYYY) = actual release date + ref month 抽出
  - PDF 重複 dedup / ref month 不明は fail-loud
  - NFP 検証: explore 窓の非金曜 = fail (7月4日連休木曜のみ許容) / OOS = フラグ
  - cadence 12±1/年・reference month 欠月ゼロ (explore fail-loud / OOS フラグ)
  - FOMC calendar 行: Statement: ラベル直下リンク + 月/日レンジ突合
    (monetary20250822a 型の非会合プレスリリースの構造排除)
  - FOMC historical panel: unscheduled/cancelled/notation vote 除外 + 記録
  - validate_fomc: scheduled+cancelled = 8/年
"""
from datetime import date

import pytest

from tools import event_calendar_build as C

# ─── 縮約 fixture (実ページ書式) ────────────────────────────────────────────
BLS_ARCHIVE_FIXTURE = """
<ul>
<li><a href="/news.release/archives/empsit_06052026.htm">May 2026 Employment Situation</a>
 (<a href="/news.release/archives/empsit_06052026.pdf">PDF</a>)</li>
<li><a href="/news.release/archives/empsit_05082026.htm">April 2026 Employment Situation</a>
 (<a href="/news.release/archives/empsit_05082026.pdf">PDF</a>)</li>
<li><a href="/news.release/history/empsit_07021999.txt">July 1999 (txt, 対象外)</a></li>
</ul>
"""

FOMC_CAL_FIXTURE = """
<div class="row fomc-meeting" ">
  <div class="fomc-meeting__month col-xs-5"><strong>January</strong></div>
  <div class="fomc-meeting__date col-xs-4">30-31</div>
  <div><strong>Statement:</strong><br>
    <a href="/monetarypolicy/files/monetary20240131a1.pdf">PDF</a> |
    <a href="/newsevents/pressreleases/monetary20240131a.htm">HTML</a><br>
    <a href="/newsevents/pressreleases/monetary20240131b.htm">Statement on Longer-Run Goals</a>
  </div>
</div>
<div class="fomc-meeting--shaded row fomc-meeting" ">
  <div class="fomc-meeting__month col-xs-5"><strong>Jan/Feb</strong></div>
  <div class="fomc-meeting__date col-xs-4">31-1</div>
  <div><strong>Statement:</strong><br>
    <a href="/newsevents/pressreleases/monetary20230201a.htm">HTML</a>
  </div>
</div>
<div class="row fomc-meeting" ">
  <div class="fomc-meeting__month col-xs-5"><strong>September</strong></div>
  <div class="fomc-meeting__date col-xs-4">28-29</div>
</div>
"""

# 非会合プレスリリース (monetary20250822a 型) が Statement: 直下に混入した場合
FOMC_CAL_CONTAMINATED = """
<div class="row fomc-meeting" ">
  <div class="fomc-meeting__month col-xs-5"><strong>September</strong></div>
  <div class="fomc-meeting__date col-xs-4">16-17</div>
  <div><strong>Statement:</strong><br>
    <a href="/newsevents/pressreleases/monetary20250822a.htm">HTML</a>
  </div>
</div>
"""

FOMC_HIST_FIXTURE = """
<div class="panel panel-default panel-padded">
<h5 class="panel-heading panel-heading--shaded">January 28-29 Meeting - 2020</h5>
<p><a href="/newsevents/pressreleases/monetary20200129a.htm">Statement</a></p>
</div>
<div class="panel panel-default panel-padded">
<h5 class="panel-heading panel-heading--shaded">March 15 (unscheduled) Meeting - 2020</h5>
<p><a href="/newsevents/pressreleases/monetary20200315a.htm">Statement</a></p>
</div>
<div class="panel panel-default panel-padded">
<h5 class="panel-heading panel-heading--shaded">March 17-18 (cancelled) Meeting - 2020</h5>
</div>
<div class="panel panel-default panel-padded">
<h5 class="panel-heading panel-heading--shaded">March 23 (notation vote) - 2020</h5>
<p><a href="/newsevents/pressreleases/monetary20200323a.htm">Statement</a></p>
</div>
"""


# ─── BLS archive パーサ ─────────────────────────────────────────────────────
def test_parse_bls_archive_dates_and_ref_months():
    recs = C.parse_bls_archive(BLS_ARCHIVE_FIXTURE, "empsit")
    assert [(r["date"], r["ref_year"], r["ref_month"]) for r in recs] == [
        (date(2026, 5, 8), 2026, 4),
        (date(2026, 6, 5), 2026, 5),
    ]  # PDF dedup 済み・.txt (history) は非対象・日付昇順


def test_parse_bls_archive_ref_month_missing_fails_loud():
    bad = '<a href="/news.release/archives/empsit_06052026.htm">???</a>'
    with pytest.raises(C.CalendarValidationError):
        C.parse_bls_archive(bad, "empsit")


# ─── NFP/CPI 検証 (explore fail-loud / OOS フラグ) ──────────────────────────
def _monthly_records(y0, y1, weekday_target=4):
    """ref month = 前月、release = 当月の第 weekday_target 曜日、の合成カレンダー。"""
    recs = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            d = date(y, m, 1)
            while d.weekday() != weekday_target:
                d = d.replace(day=d.day + 1)
            ry, rm = (y - 1, 12) if m == 1 else (y, m - 1)
            recs.append({"date": d, "ref_year": ry, "ref_month": rm})
    return recs


def test_validate_nfp_clean_calendar_passes():
    recs = _monthly_records(2014, 2025)
    v = C.validate_bls(recs, "NFP")
    assert v["oos_flags"] == []
    assert v["per_year"]["2014"] == 12


def test_validate_nfp_explore_saturday_fails_loud():
    recs = _monthly_records(2014, 2025)
    recs[13]["date"] = date(2015, 2, 7)  # 2015-02-07 = 土曜
    assert recs[13]["date"].weekday() == 5
    with pytest.raises(C.CalendarValidationError, match="EXPLORE"):
        C.validate_bls(recs, "NFP")


def test_validate_nfp_july4_thursday_allowed_in_explore():
    recs = _monthly_records(2014, 2025)
    # 2014-07-03 (木、7月4日連休前倒し — 実カレンダーに存在する唯一の explore 例外型)
    for r in recs:
        if r["date"].year == 2014 and r["date"].month == 7:
            r["date"] = date(2014, 7, 3)
    v = C.validate_bls(recs, "NFP")
    assert "2014-07-03" in (v["non_standard_weekday"] or [])


def test_validate_nfp_oos_thursday_flags_not_fails():
    recs = _monthly_records(2014, 2025)
    for r in recs:
        if r["date"].year == 2025 and r["date"].month == 11:
            r["date"] = date(2025, 11, 20)  # 木曜 (OOS 窓、2025 shutdown 実例)
    v = C.validate_bls(recs, "NFP")
    assert any("2025-11-20" in f for f in v["oos_flags"])


def test_validate_explore_missing_month_fails_loud():
    recs = [r for r in _monthly_records(2014, 2025)
            if not (r["ref_year"] == 2019 and r["ref_month"] == 6)]
    with pytest.raises(C.CalendarValidationError, match="EXPLORE"):
        C.validate_bls(recs, "CPI")


def test_validate_oos_missing_month_flags_not_fails():
    recs = [r for r in _monthly_records(2014, 2025)
            if not (r["ref_year"] == 2025 and r["ref_month"] == 10)]
    v = C.validate_bls(recs, "CPI")
    assert any("gap" in f for f in v["oos_flags"])


# ─── FOMC calendar (2021+) ─────────────────────────────────────────────────
def test_parse_fomc_calendar_rows_and_cross_month():
    out = C.parse_fomc_calendar(FOMC_CAL_FIXTURE)
    assert out["scheduled"] == [date(2023, 2, 1), date(2024, 1, 31)]
    # statement 無し行 (未来会合) は除外記録
    assert sum(1 for e in out["excluded"]
               if e["reason"] == "no_statement (future/none)") == 1


def test_parse_fomc_calendar_non_meeting_release_fails_loud():
    # monetary20250822a (枠組み改定、会合日レンジと不一致) は突合で構造排除
    with pytest.raises(C.CalendarValidationError, match="mismatch"):
        C.parse_fomc_calendar(FOMC_CAL_CONTAMINATED)


# ─── FOMC historical (2014-2020) ────────────────────────────────────────────
def test_parse_fomc_historical_classification():
    out = C.parse_fomc_historical(FOMC_HIST_FIXTURE, 2020)
    assert out["scheduled"] == [date(2020, 1, 29)]
    reasons = sorted(e["reason"] for e in out["excluded"])
    assert reasons == ["cancelled", "notation vote", "unscheduled"]
    unsch = next(e for e in out["excluded"] if e["reason"] == "unscheduled")
    assert unsch["statement_date"] == "2020-03-15"


def test_parse_fomc_historical_wrong_year_fails_loud():
    with pytest.raises(C.CalendarValidationError):
        C.parse_fomc_historical(FOMC_HIST_FIXTURE, 2019)


# ─── validate_fomc (8/年、cancelled 会計) ────────────────────────────────────
def _fomc_8_per_year():
    days = [(1, 29), (3, 18), (4, 29), (6, 17), (7, 29), (9, 16), (11, 4), (12, 15)]
    sched = [date(y, m, d) for y in range(2014, 2026) for m, d in days]
    sched += [date(2026, 1, 28), date(2026, 3, 18), date(2026, 4, 29), date(2026, 6, 17)]
    return sched


def test_validate_fomc_clean_passes():
    v = C.validate_fomc(_fomc_8_per_year(), [])
    assert v["per_year"]["2014"] == 8 and v["per_year"]["2026"] == 4


def test_validate_fomc_cancelled_accounting():
    sched = [d for d in _fomc_8_per_year() if d != date(2020, 3, 18)]
    # cancelled 記録なし → 2020 が 7 で fail-loud
    with pytest.raises(C.CalendarValidationError, match="2020"):
        C.validate_fomc(sched, [])
    # cancelled 記録あり → scheduled+cancelled = 8 で pass
    v = C.validate_fomc(sched, [{"row": "March 17-18 (cancelled) Meeting - 2020",
                                 "reason": "cancelled", "statement_date": None}])
    assert v["per_year"]["2020"] == 7


# ─── 会合最終日パース (cross-month / 略記) ──────────────────────────────────
def test_last_month_day_variants():
    assert C._last_month_day("January 28-29 Meeting - 2020") == (1, 29)
    assert C._last_month_day("April 30-May 1 Meeting - 2019") == (5, 1)
    assert C._last_month_day("Jan/Feb 31-1") == (2, 1)
    assert C._last_month_day("March  4 (unscheduled) - 2014") == (3, 4)
