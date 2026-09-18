# -*- coding: utf-8 -*-
"""KB 内の数値主張が「自分の分子・分母」と整合するかを検査する。

動機 (2026-09-18, PR #270 第12波): レビュー指摘に応じて検出力曲線の数値を
更新する際、**スコープを絞らない全文 find-replace** を KB ファイル全体に当てた。
`"0.132" -> "0.130"` が Gate A の **0.1327** に、`"4.2%" -> "4.7%"` が
歴史的 SL_HIT 記録の **54.2%** に食い込み、**無関係な過去の記録 2 件を改竄**した。
どちらも「置換対象の数値の部分文字列」であり、置換自体は成功するので静かに壊れる。

ここでの pin は**構文**ではなく**性質**で書く (lesson_validity_check_pins_proxy_2026_09_02):
文言がどう変わっても、「割合の主張はその場に書かれた件数と一致する」は不変。
語句 grep 型の pin は本セッションで 2 度誤爆しているので採らない。
"""
import io
import re
from pathlib import Path

import pytest

WIKI = Path(__file__).resolve().parents[1] / "knowledge-base" / "wiki"

# 「**0.1327** (147 / 1,108 bd)」型 — 割合とその分子/分母が同一箇所にある主張
_RATE = re.compile(r"\*\*(0\.\d{3,4})\*\*\s*\((\d[\d,]*)\s*/\s*(\d[\d,]*)\s*bd\)")
# 「WIN 1792 (54.2%)** / LOSS 1441 / BE 75」型 — 内訳と百分率が同一行にある主張
_TALLY = re.compile(
    r"WIN\s+(\d+)\s*\((\d+\.\d)%\)\*\*\s*/\s*LOSS\s+(\d+)\s*/\s*BE\s+(\d+)"
)
# 件数を伴わない素の引用「Gate A 0.1327≤0.25」
_GATE_A_CITE = re.compile(r"Gate A\s*(0\.\d{3,4})")


def _wiki_docs():
    return sorted(WIKI.rglob("*.md"))


def _read(path):
    with io.open(str(path), encoding="utf-8") as fh:
        return fh.read()


def _int(s):
    return int(s.replace(",", ""))


def test_rate_claims_match_their_own_counts():
    """割合 **p** (a / b bd) は a/b と一致しなければならない。"""
    seen = 0
    bad = []
    for doc in _wiki_docs():
        for m in _RATE.finditer(_read(doc)):
            seen += 1
            truth = _int(m.group(2)) / _int(m.group(3))
            if abs(float(m.group(1)) - truth) > 5e-5:
                bad.append("%s: %s (真値 %.4f)" % (doc.name, m.group(0), truth))
    assert seen >= 2, "検査対象の主張が消えた — 正規表現が estimand を見失っている"
    assert not bad, "件数と一致しない割合主張:\n" + "\n".join(bad)


def test_outcome_tally_matches_its_percentage():
    """WIN/LOSS/BE 内訳と WIN 率の百分率は同一行内で整合しなければならない。"""
    seen = 0
    bad = []
    for doc in _wiki_docs():
        for m in _TALLY.finditer(_read(doc)):
            seen += 1
            win, loss, be = int(m.group(1)), int(m.group(3)), int(m.group(4))
            truth = 100.0 * win / (win + loss + be)
            if abs(float(m.group(2)) - truth) > 0.05:
                bad.append("%s: %s (真値 %.1f%%)" % (doc.name, m.group(0), truth))
    assert seen >= 1, "検査対象の内訳主張が消えた"
    assert not bad, "内訳と一致しない百分率:\n" + "\n".join(bad)


def test_gate_a_citations_agree_with_the_count_bearing_claim():
    """件数を持たない「Gate A 0.xxxx」引用は、件数付きの正本と一致すること。

    同じ量が複数ドキュメントに転記される場合、全文置換は一部だけを書き換える。
    正本 (分子・分母を持つ主張) を単一の出所として、引用側の一致を要求する。
    """
    authoritative = set()
    for doc in _wiki_docs():
        for m in _RATE.finditer(_read(doc)):
            authoritative.add(round(_int(m.group(2)) / _int(m.group(3)), 4))
    if not authoritative:
        pytest.skip("件数付きの正本が KB に存在しない")

    bad = []
    for doc in _wiki_docs():
        for m in _GATE_A_CITE.finditer(_read(doc)):
            if not any(abs(float(m.group(1)) - a) <= 5e-5 for a in authoritative):
                bad.append(
                    "%s: '%s' — 正本 %s のいずれとも不一致"
                    % (doc.name, m.group(0), sorted(authoritative))
                )
    assert not bad, "正本と乖離した引用:\n" + "\n".join(bad)
