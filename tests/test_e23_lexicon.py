"""E23 Apel–Blix Grimaldi 凍結辞書スコアラーの test pin (network 不要)。

語彙・照合規則・netting 式は WP 261 転記の凍結仕様 — 変更はここが検知する。
イベント×リターン結合は一切テストしない (S2 規律: スコアラーは text→score のみ)。
"""
import pytest

from tools import e23_lexicon_apel_grimaldi as L


def test_frozen_vocabulary_pin():
    """凍結語彙の完全 pin — 追加・削除・並べ替えは fail させる (C5 封鎖)。"""
    assert L.NOUN_STEMS_2 == (("oil", "price"), ("cyclical", "position"))
    assert L.NOUN_STEMS_1 == ("inflation", "price", "wage", "growth", "development",
                              "unemployment", "employment", "recovery", "cost")
    assert L.INVERTED_NOUNS == ("unemployment",)
    assert L.HAWKISH_ADJ_STEMS == ("high", "strong", "increas", "fast")
    assert L.DOVISH_ADJ_STEMS == ("low", "weak", "decreas", "slow")


def test_basic_hawkish_and_dovish_bigrams():
    c = L.count_bigrams("The committee noted higher inflation and stronger growth.")
    assert (c["hawk"], c["dove"]) == (2, 0)
    c = L.count_bigrams("Members expect weaker growth and lower inflation expectations.")
    assert (c["hawk"], c["dove"]) == (0, 2)


def test_unemployment_polarity_inversion():
    assert L.count_bigrams("increasing unemployment")["dove"] == 1
    assert L.count_bigrams("decreasing unemployment")["hawk"] == 1
    # 非反転名詞の対照
    assert L.count_bigrams("increasing employment")["hawk"] == 1


def test_wildcard_compound_nouns_and_two_token_nouns():
    # 名詞 wildcard: "inflationary" は inflation* に一致
    assert L.count_bigrams("higher inflationary pressures")["hawk"] == 1
    # 2 トークン名詞は longest-match: "higher oil prices" は oil price* 1 件
    c = L.count_bigrams("higher oil prices")
    assert c["hawk"] == 1
    assert c["matches"][0][2] == "oil price"


def test_sentence_boundary_blocks_false_pairs():
    # "low. Price" の文跨ぎ隣接をペアにしない
    c = L.count_bigrams("Growth was low. Price stability remains the objective.")
    assert (c["hawk"], c["dove"]) == (0, 0)


def test_net_hawkishness_formula():
    # H=2, D=0 → (2-0)/(2+0+1) = 2/3
    nh = L.net_hawkishness("higher inflation and stronger growth")
    assert nh == pytest.approx(2 / 3)
    assert L.net_hawkishness("no relevant phrases here") == 0.0
    # 範囲 (−1, 1) と符号
    assert -1 < L.net_hawkishness("weaker growth") < 0


def test_delta_net_hawkishness_between_statements():
    prev = "lower growth and weaker wage development"          # dovish
    curr = "higher inflation and increasing cost pressures"    # hawkish
    d = L.delta_net_hawkishness(curr, prev)
    assert d > 0
    assert d == pytest.approx(L.net_hawkishness(curr) - L.net_hawkishness(prev))


def test_no_price_or_return_coupling_in_module():
    """S2 規律の構造 pin: スコアラーは価格・リターン・DB へ一切依存しない。"""
    import inspect
    src = inspect.getsource(L)
    for banned in ("pandas", "read_parquet", "sqlite", "requests", "yfinance",
                   "pnl", "return_", "fwd"):
        assert banned not in src, f"E23 lexicon module に {banned} が混入"
