"""FF gap 整形 (R4F tz 正規化 / BLS first-print 抽出) のオフライン test pin。"""
import pytest

from tools import ff_gap_prepare_r4f as R
from tools import ff_gap_bls_first_prints as P


# ─── R4F: tz 正規化 (anchor pin — 2026-07-24 実測特性) ──────────────────────
def test_normalize_time_london_bst_era():
    # 2023-08-07 より前は Europe/London 現地。BST 期は UTC−1h
    assert R.normalize_time("2023-04-07", "13:30") == "2023-04-07T12:30:00Z"


def test_normalize_time_london_winter_era():
    # 冬期 (GMT) は UTC 一致
    assert R.normalize_time("2023-01-06", "13:30") == "2023-01-06T13:30:00Z"


def test_normalize_time_utc_era_and_boundary():
    assert R.normalize_time("2023-08-10", "12:30") == "2023-08-10T12:30:00Z"
    # 境界日 2023-08-07 当日から UTC 扱い
    assert R.normalize_time("2023-08-07", "12:15") == "2023-08-07T12:15:00Z"
    # 境界前日は London (BST −1h)
    assert R.normalize_time("2023-08-04", "13:30") == "2023-08-04T12:30:00Z"


def test_normalize_time_accepts_slash_dates():
    assert R.normalize_time("2023/04/07", "13:30") == "2023-04-07T12:30:00Z"


# ─── R4F: パース ─────────────────────────────────────────────────────────────
_ROW = '2023/04/07,13:30,USD,H,"Non-Farm Employment Change",,,236K,228K,326K\n'


def test_parse_r4f_maps_columns():
    rows = R.parse_r4f(_ROW)
    assert rows[0]["actual"] == "236K"
    assert rows[0]["forecast"] == "228K"
    assert rows[0]["previous"] == "326K"
    assert rows[0]["impact_raw"] == "H"


def test_parse_r4f_rejects_wrong_column_count():
    with pytest.raises(ValueError):
        R.parse_r4f("2023/04/07,13:30,USD,H\n")


def test_parse_r4f_rejects_nonempty_reserved_cols():
    bad = '2023/04/07,13:30,USD,H,"NFP",x,,236K,228K,326K\n'
    with pytest.raises(ValueError):
        R.parse_r4f(bad)


def test_build_import_rows_window_impact_dup():
    rows = R.parse_r4f(
        '2013/12/31,13:30,USD,H,"Old",,,1,2,3\n'          # 窓外 (< 2014-01-01)
        '2023/04/07,13:30,USD,H,"NFP",,,236K,228K,326K\n'
        '2023/04/07,13:30,USD,H,"NFP",,,237K,228K,326K\n'  # 同一 key → 後勝ち
        '2024/01/01,00:01,JPY,N,"Bank Holiday",,,,,\n'
    )
    out, stats = R.build_import_rows(rows)
    assert stats["in_window"] == 3 and stats["dup_key"] == 1
    by_title = {r["title"]: r for r in out}
    assert by_title["NFP"]["actual"] == "237K"
    assert by_title["NFP"]["event_time_utc"] == "2023-04-07T12:30:00Z"
    assert by_title["Bank Holiday"]["impact"] == "Holiday"


def test_build_import_rows_unknown_impact_fails_loud():
    rows = [{"date": "2024-01-05", "time": "13:30", "currency": "USD",
             "impact_raw": "X", "title": "T", "actual": "", "forecast": "",
             "previous": ""}]
    with pytest.raises(ValueError):
        R.build_import_rows(rows)


# ─── BLS: NFP 抽出 ───────────────────────────────────────────────────────────
def test_extract_nfp_increased_by():
    v, _ = P.extract_nfp("Total nonfarm payroll employment increased by "
                         "187,000 in July, and the unemployment rate ...")
    assert v == "187K"


def test_extract_nfp_parenthetical():
    v, _ = P.extract_nfp("Total nonfarm payroll employment was essentially "
                         "unchanged in October (+12,000), ...")
    assert v == "12K"


def test_extract_nfp_declined_by():
    v, _ = P.extract_nfp("Total nonfarm payroll employment declined by "
                         "33,000 in June ...")
    assert v == "-33K"


def test_extract_nfp_paren_unicode_minus():
    v, _ = P.extract_nfp("Total nonfarm payroll employment changed little "
                         "in October (−105,000) ...")
    assert v == "-105K"


def test_extract_nfp_by_verb_beats_later_paren():
    # 2026-03-06 リリース実文型: headline は "edged down by 92,000"、後方に改定値括弧。
    # パターン種類順の先勝ちだと (+126,000) を誤採用する (実バグの regression pin)
    v, _ = P.extract_nfp(
        "Total nonfarm payroll employment edged down by 92,000 in February, "
        "following a revised gain in January (+126,000)")
    assert v == "-92K"


def test_extract_nfp_increase_beats_later_negative_paren():
    v, _ = P.extract_nfp(
        "Total nonfarm payroll employment increased by 178,000 in March, "
        "following a revised decline in February (-133,000)")
    assert v == "178K"


def test_extract_nfp_non_thousand_fails_loud():
    with pytest.raises(ValueError):
        P.extract_nfp("Total nonfarm payroll employment increased by 187,500 ...")


def test_extract_nfp_no_match_fails_loud():
    with pytest.raises(ValueError):
        P.extract_nfp("The unemployment rate held at 4.1 percent.")


# ─── BLS: CPI 抽出 ───────────────────────────────────────────────────────────
def test_extract_cpi_rose():
    v, _ = P.extract_cpi("The Consumer Price Index for All Urban Consumers "
                         "(CPI-U) rose 0.2 percent on a seasonally adjusted basis")
    assert v == "0.2%"


def test_extract_cpi_declined():
    v, _ = P.extract_cpi("... (CPI-U) declined 0.1 percent on a seasonally "
                         "adjusted basis ...")
    assert v == "-0.1%"


def test_extract_cpi_unchanged():
    v, _ = P.extract_cpi("... (CPI-U) was unchanged in May on a seasonally "
                         "adjusted basis ...")
    assert v == "0.0%"


def test_extract_cpi_headline_beats_later_yoy():
    # 2023-11-14 リリース実文型: headline は unchanged、本文後方に y/y 3.2% (regression pin)
    v, _ = P.extract_cpi(
        "The Consumer Price Index for All Urban Consumers (CPI-U) was unchanged "
        "in October on a seasonally adjusted basis. Elsewhere the report notes the "
        "(CPI-U) increased 3.2 percent over the last 12 months")
    assert v == "0.0%"


def test_extract_cpi_declined_beats_later_yoy():
    v, _ = P.extract_cpi(
        "The Consumer Price Index for All Urban Consumers (CPI-U) declined 0.1 "
        "percent in June. Over the last 12 months the (CPI-U) increased 3.0 percent")
    assert v == "-0.1%"


def test_strip_html_removes_tags_and_scripts():
    text = P.strip_html(b"<html><script>var x=1;</script><p>rose\n0.2&nbsp;"
                        b"percent</p></html>")
    assert "rose 0.2" in text and "var x" not in text
