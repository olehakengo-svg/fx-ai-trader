"""E23 pass-0 ハーネスの凍結 pin (rule:R1 手続き / pre-reg 準拠).

守る不変条件
------------
1. 凍結辞書 `tools/e23_lexicon_apel_grimaldi.py` の sha256 が pre-reg の pin と一致
   (語彙の後付け編集 = C5 DoF 再開を機械で止める)。
2. pass-0 の機械 gate 閾値が pre-reg §2/§3 の凍結値と一致。
3. 窓 (explore/OOS) が pre-reg §2 の凍結値と一致。
4. BOE の MPS 節境界語による切り出しが仕様どおり動く (境界語の sed 的改変を止める)。
5. 本文コンテナ抽出がナビだけの空コンテナを機械的に弾く。
6. **pass-0 モジュールが価格データを参照しない** (outcome 非接触の構造 pin)。
"""
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import e23_corpus_census as census_mod  # noqa: E402
import e23_corpus_fetch as fetch_mod  # noqa: E402

PREREG = ROOT / "knowledge-base" / "wiki" / "decisions" / \
    "e23-cb-text-explore-prereg-2026-09-10.md"
LEXICON = ROOT / "tools" / "e23_lexicon_apel_grimaldi.py"
PINNED_SHA = "f49586cad6e40e9c53e24adefeba78dcc5c9b925496c4b5b3808636c84b7bde8"


def test_lexicon_sha_matches_prereg_pin():
    actual = hashlib.sha256(LEXICON.read_bytes()).hexdigest()
    assert actual == PINNED_SHA, (
        "凍結辞書が変更された。pre-reg §0-3 は語彙の追加・削除・重み・否定処理の"
        f"後付けを恒久禁止している (expected {PINNED_SHA}, got {actual})"
    )
    # pre-reg 本文の pin 記載と二重照合 (doc 側の書き換えも検出する)
    assert PINNED_SHA in PREREG.read_text(encoding="utf-8")


def test_frozen_gate_thresholds():
    assert census_mod.MIN_DOCS_PER_YEAR == 6
    assert census_mod.MIN_YEAR_COVERAGE_FRAC == 0.80
    assert census_mod.MIN_SURVIVING_CBS == 2
    assert census_mod.STALENESS_VOID_DAYS == 120


def test_frozen_windows():
    assert fetch_mod.EXPLORE_START.isoformat() == "2014-01-01"
    assert fetch_mod.EXPLORE_END.isoformat() == "2023-12-31"
    assert fetch_mod.OOS_START.isoformat() == "2024-01-01"
    assert fetch_mod.OOS_END.isoformat() == "2026-06-30"
    assert fetch_mod.CBS == ("fed", "ecb", "boe", "boj")


def test_boe_mps_boundary_extraction():
    container = (
        "Monetary Policy Summary and minutes of the Monetary Policy Committee "
        "meeting Published on 21 September 2023 "
        "Monetary Policy Summary, September 2023 "
        "The MPC voted by a majority to maintain Bank Rate at 5.25%. "
        "Minutes of the Monetary Policy Committee meeting ending on 20 September "
        "2023 Before turning to its immediate policy decision..."
    )
    mps = fetch_mod.extract_boe_mps(container)
    assert "voted by a majority" in mps
    assert "Before turning to its immediate policy decision" not in mps, \
        "minutes 本体が MPS 節に混入している (pre-reg §2 は MPS のみに凍結)"


def test_boe_mps_absent_boundary_returns_empty():
    assert fetch_mod.extract_boe_mps("Bank Rate unchanged. No summary heading.") == ""
    # 目次行 ("Monetary Policy Summary  1. Global developments") は節見出しでない
    # = カンマ形でないため start 境界に一致しない (2017-2019 HTML の実形)
    assert fetch_mod.extract_boe_mps(
        "Monetary Policy Summary 1. Global developments and domestic policy") == ""


def test_boe_page_title_is_not_mps_boundary():
    """表題 "Monetary Policy Summary and minutes of ..." を始点に取ってはならない."""
    container = (
        "Monetary Policy Summary and minutes of the Monetary Policy Committee "
        "meeting ending on 20 September 2023 "
        "Monetary Policy Summary, September 2023 Bank Rate maintained at 5.25%. "
        "Minutes of the Monetary Policy Committee meeting Before turning..."
    )
    mps = fetch_mod.extract_boe_mps(container)
    assert mps.startswith("Monetary Policy Summary, September 2023")
    assert "Before turning" not in mps


def test_boe_publication_date_both_containers():
    """HTML は "Published on"、PDF は "Publication date:" — 同一凍結規則で読む."""
    assert fetch_mod._boe_pub_date(
        "... Published on 21 September 2023 ...")[0].isoformat() == "2023-09-21"
    assert fetch_mod._boe_pub_date(
        "... Publication date: 3 November 2016 ...")[0].isoformat() == "2016-11-03"
    assert fetch_mod._boe_pub_date("no date")[0] is None


def test_container_extraction_rejects_nav_only():
    html = "<html><body><main>Home | Search | Menu</main></body></html>"
    assert fetch_mod.extract_container(html, ("main",)) == ""


def test_container_extraction_takes_main_body():
    body = "Recent indicators suggest that economic activity has expanded. " * 12
    html = f"<html><body><nav>skip</nav><main><p>{body}</p></main></body></html>"
    out = fetch_mod.extract_container(html, ("main",))
    assert out.startswith("Recent indicators")
    assert "skip" not in out


def test_boj_doc_selection_rule_is_not_title_conditional():
    """BoJ の文書同定が「表題一致」に退行していないことを pin.

    BoJ は政策変更があった回だけ表題を変えるため、表題文字列で拾うと
    政策ニュース最大の回だけが落ちる (内容条件付き選択)。同定規則は
    表題一致 → 主スロット `a` → 同日先頭 の順でなければならない。
    """
    src = (ROOT / "tools" / "e23_corpus_fetch.py").read_text(encoding="utf-8")
    assert "named or slot_a or cands" in src
    assert fetch_mod.BOJ_STATEMENT_TITLE == "statement on monetary policy"
    # 2014-10-31 (QQE 拡大) の実表題は "Statement on..." で始まらない = 主スロット採用
    assert not "Expansion of the Quantitative and Qualitative Monetary Easing".lower(
    ).startswith(fetch_mod.BOJ_STATEMENT_TITLE)


def test_boj_printed_date_parse():
    assert fetch_mod._boj_printed_date(
        "Statement on Monetary Policy September 22, 2023 Bank of Japan"
    ).isoformat() == "2023-09-22"
    assert fetch_mod._boj_printed_date("no date here") is None


def _synthetic(cb: str, dates: list[str]) -> list[dict]:
    text = "Inflation remains high. High inflation persists." * 2
    return [{"cb": cb, "date": d, "text": text, "n_chars": len(text),
             "same_day_attested": True} for d in dates]


def _year_dates(year: int, n: int) -> list[str]:
    return [f"{year}-{m:02d}-15" for m in range(1, n + 1)]


def test_census_coverage_gate_and_data_blocked():
    # fed/ecb は 10 年すべて 8 本 → PASS。boe/boj は 1 年だけ → 除外。
    docs: list[dict] = []
    for cb in ("fed", "ecb"):
        for y in range(2014, 2024):
            docs += _synthetic(cb, _year_dates(y, 8))
    for cb in ("boe", "boj"):
        docs += _synthetic(cb, _year_dates(2023, 8))

    c = census_mod.census(docs)
    assert c["per_cb"]["fed"]["coverage_gate_pass"] is True
    assert c["per_cb"]["boe"]["coverage_gate_pass"] is False
    assert c["surviving_cbs"] == ["fed", "ecb"]
    assert c["verdict"] == "PASS_TO_PASS1"

    # 生存 1 CB → DATA-BLOCKED (pre-reg §2)
    only_fed = [r for r in docs if r["cb"] == "fed"]
    assert census_mod.census(only_fed)["verdict"] == "DATA-BLOCKED"


def test_census_eighty_percent_boundary_is_inclusive():
    """8/10 年 = 80% は PASS (pre-reg 「80% 以上」)、7/10 年は除外。"""
    docs: list[dict] = []
    for y in range(2016, 2024):          # 8 年ぶん
        docs += _synthetic("fed", _year_dates(y, 8))
    for y in range(2017, 2024):          # 7 年ぶん
        docs += _synthetic("ecb", _year_dates(y, 8))
    c = census_mod.census(docs)
    assert c["per_cb"]["fed"]["coverage_gate_pass"] is True
    assert c["per_cb"]["ecb"]["coverage_gate_pass"] is False


def test_census_boj_excluded_when_same_day_not_attested():
    docs: list[dict] = []
    for cb in ("fed", "boj"):
        for y in range(2014, 2024):
            docs += _synthetic(cb, _year_dates(y, 8))
    docs[-1]["same_day_attested"] = False  # V3 機械規則の発火
    c = census_mod.census(docs)
    assert "boj" not in c["surviving_cbs"]
    assert c["boj_same_day_attested"]["attested"] < c["boj_same_day_attested"]["n"]


def test_census_counts_staleness_void():
    docs = _synthetic("fed", ["2014-01-15", "2014-02-15", "2014-09-15"])
    c = census_mod.census(docs)
    assert c["per_cb"]["fed"]["gap_days"]["gt_120d_void"] == 1


def test_pass0_modules_do_not_touch_price_data():
    """outcome 非接触の構造 pin: 価格・リターン系の参照がソースに無いこと."""
    banned = re.compile(
        r"data/cache|_holdout_locked|parquet|fwd5|forward_return|demo\.db", re.I)
    for mod in (ROOT / "tools" / "e23_corpus_fetch.py",
                ROOT / "tools" / "e23_corpus_census.py"):
        src = mod.read_text(encoding="utf-8")
        body = "\n".join(
            ln for ln in src.splitlines()
            if not ln.lstrip().startswith("#")
        )
        hit = banned.search(body)
        assert hit is None, f"{mod.name} が価格系を参照している: {hit.group(0)}"
