"""Tests for the MoF verbal-intervention lexicon ladder + conference parser.

Scope: pure text processing only (no network, no price data).
The ladder encodes the escalation structure documented in
knowledge-base/wiki/analyses/mof-communication-data-infrastructure.md
(Gnabo-style talk/act discretization; ordered levels 1..5).
"""
import pathlib

import pytest

from tools import mof_statements_lexicon as lex

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "mof_conference_sample.html"


# ---------------------------------------------------------------- ladder ----

def test_ladder_has_five_ordered_levels():
    levels = [lv for lv, _name, _pats in lex.LADDER]
    assert levels == [1, 2, 3, 4, 5]


def test_score_watch_only_is_level_1():
    r = lex.score_minister_text("為替市場の動向をしっかりと注視してまいります。")
    assert r["level"] == 1
    assert r["no_comment"] is False


def test_score_excessive_volatility_is_level_2():
    r = lex.score_minister_text("為替の過度な変動は望ましくないと考えております。")
    assert r["level"] == 2


def test_score_all_options_is_level_3():
    r = lex.score_minister_text(
        "過度な変動に対しては、あらゆる選択肢を排除せず適切な対応をとります。"
    )
    assert r["level"] == 3


def test_score_resolute_measures_is_level_4():
    r = lex.score_minister_text("投機的な動きに対しては断固たる措置をとります。")
    assert r["level"] == 4


def test_score_action_confirmation_is_level_5():
    r = lex.score_minister_text("本日、為替介入を実施いたしました。")
    assert r["level"] == 5


def test_score_no_fx_content_is_level_0():
    r = lex.score_minister_text("来年度予算の編成方針について議論を行いました。")
    assert r["level"] == 0
    assert r["matches"] == {}


def test_higher_level_wins():
    r = lex.score_minister_text(
        "為替の動向を注視しておりますが、行き過ぎた動きには断固たる対応をとります。"
    )
    assert r["level"] == 4
    # lower-level matches are still recorded
    assert 1 in r["matches"] and 4 in r["matches"]


def test_no_comment_flag_detected():
    r = lex.score_minister_text("介入の有無についてはコメントを差し控えます。")
    assert r["no_comment"] is True


# ---------------------------------------------------------------- parser ----

def test_parse_conference_html_extracts_meta_and_blocks():
    html = FIXTURE.read_text(encoding="utf-8")
    doc = lex.parse_conference_html(html, url="https://www.mof.go.jp/public_relations/conference/my20240426.html")
    assert doc["date"] == "2024-04-26"
    assert doc["minister"] == "鈴木"
    roles = [b["role"] for b in doc["blocks"]]
    assert "opening" in roles and "question" in roles and "answer" in roles
    # the opening statement text is captured
    opening = next(b for b in doc["blocks"] if b["role"] == "opening")
    assert "海外出張" in opening["text"]


def test_parse_conference_html_fullwidth_parens_and_wareki():
    html = FIXTURE.read_text(encoding="utf-8").replace(
        "(令和6年4月26日(金曜日))", "（令和4年9月22日（木曜日））"
    )
    doc = lex.parse_conference_html(html, url="https://example.invalid/no-date-here.html")
    assert doc["date"] == "2022-09-22"


def test_score_conference_ignores_journalist_ladder_words():
    """A journalist quoting 「断固たる措置」 in a question must not raise the score."""
    blocks = [
        {"role": "question", "text": "断固たる措置をとる用意はありますか。為替についてです。"},
        {"role": "answer", "text": "為替市場の動向を注視しております。"},
    ]
    row = lex.score_conference(blocks)
    assert row["max_level"] == 1


def test_score_conference_answer_inherits_fx_context_from_question():
    """Minister answers rarely repeat 「為替」; FX relevance flows from the question."""
    blocks = [
        {"role": "question", "text": "円安への対応についてお伺いします。"},
        {"role": "answer", "text": "政府として、あらゆる選択肢を排除せず適切な対応をとります。"},
    ]
    row = lex.score_conference(blocks)
    assert row["max_level"] == 3
    assert row["n_fx_blocks"] >= 1


def test_score_conference_non_fx_answer_not_scored():
    blocks = [
        {"role": "question", "text": "予算編成についてお伺いします。"},
        {"role": "answer", "text": "歳出改革は断固として進めます。"},
    ]
    row = lex.score_conference(blocks)
    assert row["max_level"] == 0
    assert row["n_fx_blocks"] == 0
