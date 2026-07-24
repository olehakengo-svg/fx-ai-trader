"""tools/wayback_outlook_extract.py のオフライン回帰 pin。

fixtures は Wayback Machine の実スナップショット 3 点 (2022×2, 2025 = Era B) +
1 点 (2014 = Era A tooltip レイアウト) を 45KB 以下に切り詰めた縮小コピー
(tests/fixtures/wayback_outlook/)。ネットワークアクセスは一切しない。

pin する値は fixture 生成時に parse_outlook_html で実測した値 (2026-07-16)。
パーサ変更でこのテストが割れたら、値の変化が意図的か必ず確認すること。
"""
from pathlib import Path

import pytest

from tools.wayback_outlook_extract import (
    _parse_number,
    dedupe_daily_first,
    parse_outlook_html,
    sign,
    ts14_to_iso_utc,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "wayback_outlook"


def _load(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _by_symbol(rows):
    return {r["symbol"]: r for r in rows}


# ── Era B (2020+ popover レイアウト) ────────────────────────────────
def test_era_b_2022_january():
    rows = parse_outlook_html(_load("wb_20220105010037_trimmed.html"))
    by = _by_symbol(rows)
    assert len(rows) == 25
    assert by["EURUSD"]["long_pct"] == 70.0
    assert by["EURUSD"]["short_pct"] == 30.0
    assert by["EURUSD"]["total_positions"] == 33165
    assert by["EURUSD"]["long_volume_lots"] == pytest.approx(9119.13)
    assert by["EURUSD"]["short_volume_lots"] == pytest.approx(3866.91)
    # 貪欲マッチ事故の pin: GBPUSD の % が EURUSD/USDJPY と混ざらないこと
    assert by["GBPUSD"]["long_pct"] == 21.0
    assert by["GBPUSD"]["short_pct"] == 79.0
    assert by["USDJPY"]["long_pct"] == 12.0
    assert by["USDJPY"]["short_pct"] == 88.0


def test_era_b_2022_october():
    rows = parse_outlook_html(_load("wb_20221027001500_trimmed.html"))
    by = _by_symbol(rows)
    assert len(rows) == 25
    assert by["EURUSD"]["long_pct"] == 20.0
    assert by["EURUSD"]["short_pct"] == 80.0
    assert by["EURUSD"]["total_positions"] == 58024
    assert by["GBPUSD"]["long_pct"] == 26.0
    assert by["USDJPY"]["short_pct"] == 63.0


def test_era_b_2025_new_css():
    # 2025 は tooltip-bg クラス等 CSS が変わったがテーブル構造は同じ
    rows = parse_outlook_html(_load("wb_20251227201016_trimmed.html"))
    by = _by_symbol(rows)
    assert len(rows) == 15
    assert by["EURUSD"]["long_pct"] == 18.0
    assert by["EURUSD"]["short_pct"] == 82.0
    assert by["EURUSD"]["total_positions"] == 56298
    assert by["GBPUSD"]["long_pct"] == 38.0
    assert by["USDJPY"]["long_pct"] == 43.0


# ── Era A (2011〜2019 tooltip input レイアウト) ─────────────────────
def test_era_a_2014_tooltip_layout():
    rows = parse_outlook_html(_load("wb_20140113155404_trimmed.html"))
    by = _by_symbol(rows)
    assert len(rows) == 18
    # Era A は rowspan='3' + 'Lots' 大文字 + </tr><tr> 区切り
    assert by["EURUSD"]["long_pct"] == 41.0
    assert by["EURUSD"]["short_pct"] == 58.0  # 切り捨て表示で 100% に満たない時代
    assert by["EURUSD"]["total_positions"] == 16557
    assert by["EURUSD"]["long_volume_lots"] == pytest.approx(2382.88)
    assert by["GBPUSD"]["long_pct"] == 52.0
    assert by["USDJPY"]["long_pct"] == 53.0


# ── パーサの単体挙動 ────────────────────────────────────────────────
def test_untraded_symbol_dropped():
    # 0%/0% + positions 0 の未取引 symbol は落とす
    html = (
        "<td rowspan=\"2\">EURCZK</td>"
        "<td>Short</td><td>0%</td><td>0.00 lots</td><td>0</td></tr>"
        "<tr><td>Long</td><td>0%</td><td>0.00 lots</td><td>0</td>"
    )
    assert parse_outlook_html(html) == []


def test_long_first_order_accepted():
    # Long 行が先に来る時代/変種でも順序に依存しない
    html = (
        "<td rowspan=\"2\">EURUSD</td>"
        "<td>Long</td><td>70%</td><td>9119.13 lots</td><td>23922</td></tr>"
        "<tr><td>Short</td><td>30%</td><td>3866.91 lots</td><td>9243</td>"
    )
    rows = parse_outlook_html(html)
    assert len(rows) == 1
    assert rows[0]["long_pct"] == 70.0
    assert rows[0]["short_pct"] == 30.0


def test_localized_volume_unit_accepted():
    # Slovak capture (wb_20110219105439) の 'Loty' 実測に基づく locale 頑健性
    html = (
        "<td rowspan='3'>EURUSD</td></tr><tr>"
        "<td>Short</td><td>56%</td><td>446.94 Loty</td><td>1466</td></tr>"
        "<tr><td>Long</td><td>43%</td><td>344.80 Loty</td><td>885</td>"
    )
    rows = parse_outlook_html(html)
    assert len(rows) == 1
    assert rows[0]["short_pct"] == 56.0
    assert rows[0]["short_volume_lots"] == pytest.approx(446.94)
    assert rows[0]["total_positions"] == 2351


def test_localized_action_words_polish():
    # Polish capture (wb_20110423132414) 実測: Krótka=Short / Pozycja długa=Long
    html = (
        "<td rowspan='3'>EURUSD</td></tr><tr>"
        "<td>Krótka</td><td>90%</td><td>4311.89 Lotów</td><td>1913</td></tr>"
        "<tr><td>Pozycja długa</td><td>9%</td><td>466.58 Lotów</td><td>882</td>"
    )
    rows = parse_outlook_html(html)
    assert len(rows) == 1
    assert rows[0]["short_pct"] == 90.0
    assert rows[0]["long_pct"] == 9.0
    assert rows[0]["long_positions"] == 882


def test_unknown_action_words_skipped_and_recorded():
    html = (
        "<td rowspan='3'>EURUSD</td></tr><tr>"
        "<td>Vente</td><td>90%</td><td>10.0 Lots</td><td>19</td></tr>"
        "<tr><td>Achat</td><td>9%</td><td>1.0 Lots</td><td>8</td>"
    )
    unknown: set = set()
    rows = parse_outlook_html(html, unknown_sink=unknown)
    assert rows == []
    assert unknown == {"Vente", "Achat"}


def test_parse_number_locale_variants():
    assert _parse_number("3866.91 lots") == pytest.approx(3866.91)
    assert _parse_number("446.94 Loty") == pytest.approx(446.94)
    assert _parse_number("1,466") == 1466.0
    assert _parse_number("1,234.56") == pytest.approx(1234.56)
    assert _parse_number("56,5") == pytest.approx(56.5)
    assert _parse_number("no digits") is None


def test_dedupe_daily_first():
    rows = [
        ["k", "20220101120000", "u", "m", "200", "D1", "1"],
        ["k", "20220101130000", "u", "m", "200", "D2", "1"],  # 同日 2 件目 → 落ちる
        ["k", "20220102010000", "u", "m", "200", "D3", "1"],
    ]
    out = dedupe_daily_first(rows)
    assert [r[1] for r in out] == ["20220101120000", "20220102010000"]


def test_ts14_to_iso_utc():
    assert ts14_to_iso_utc("20220105010037") == "2022-01-05T01:00:37Z"


def test_sign():
    assert sign(12.0) == 1
    assert sign(-3.0) == -1
    assert sign(0.0) == 0
