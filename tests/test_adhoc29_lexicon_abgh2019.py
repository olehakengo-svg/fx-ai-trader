"""#29 step 1 — ABGH-2019 凍結辞書 (WP 381 Appendix 逐語転記) の test pin (network 不要).

語彙・照合規則・式 (1) は凍結仕様 — 語彙の追加/削除/並べ替え/綴り変更はここが検知する (C5 封鎖)。
価格・リターンとの結合は一切テストしない (スコアラーは text→score のみ)。
"""
import pytest

from tools import adhoc29_lexicon_abgh2019 as L

DICT_SHA256 = "37a76f5392a5694b6e209e5aef86df183c3884a84b37cfc7b5b507b59b833caf"


def test_frozen_dictionary_sha256_pin():
    """凍結語彙の完全 pin (canonical JSON の sha256)。"""
    assert L.dictionary_sha256() == DICT_SHA256


def test_frozen_dictionary_shape_pin():
    """表構造の pin: 8 エントリ / 10 TERM / modifier 件数 (印字どおり、誤植含む)。"""
    assert len(L.DICTIONARY) == 8
    terms = [t for _tab, ts, _h, _d in L.DICTIONARY for t in ts]
    assert terms == ["consumer prices", "inflation", "inflation pressure", "consumer spending",
                     "economic activity", "economic growth", "resource utilization",
                     "employment", "labor market", "unemployment"]
    counts = [(len(h), len(d)) for _tab, _ts, h, d in L.DICTIONARY]
    assert counts == [(15, 15), (18, 16), (10, 9), (15, 14), (6, 5), (12, 12), (2, 5), (5, 5)]
    # 印字どおり転記の pin: Table 5 consumer spending の HAWKISH 列に soft* / weak*
    assert ("soft*" in L.DICTIONARY[2][2]) and ("weak*" in L.DICTIONARY[2][2])
    assert "soft*" in L.DICTIONARY[2][3]
    assert L.WINDOW_WORDS == 7
    assert L.NEUTRAL_NH == 1.0


def test_adjacent_and_window_matching_both_orders():
    assert L.count_combinations("lower inflation")["dove"] == 1
    assert L.count_combinations("we expect inflation to be lower")["dove"] == 1
    # 7 語離れは可、8 語は不可
    seven = "inflation a b c d e f g rising"
    eight = "inflation a b c d e f g h rising"
    assert L.count_combinations(seven)["hawk"] == 1
    assert L.count_combinations(eight)["hawk"] == 0


def test_sentence_boundary_blocks_window():
    assert L.count_combinations("Inflation was discussed. Growth is rising.")["hawk"] == 0
    # `;` は文境界ではない (WP は "same sentence" のみ指定) — inflation…rising は 4 語離れで窓内
    assert L.count_combinations("Inflation was discussed; growth is rising.")["hawk"] == 1
    assert L.count_combinations("economic growth is rising")["hawk"] == 1


def test_stem_wildcard_exact_and_two_word_modifiers():
    assert L.count_combinations("inflation accelerated")["hawk"] == 1        # accelerat*
    assert L.count_combinations("inflation rose")["hawk"] == 1               # 完全一致
    assert L.count_combinations("inflation rosebud")["hawk"] == 0            # rose は `*` なし
    assert L.count_combinations("unemployment is high")["dove"] == 1         # `high` 完全一致
    assert L.count_combinations("unemployment is higher")["dove"] == 0       # `high` に `*` なし
    assert L.count_combinations("consumer spending edged up")["hawk"] == 1   # edg* up
    assert L.count_combinations("consumer spending edged")["hawk"] == 0
    assert L.count_combinations("a run-up in inflation")["hawk"] == 1        # run-up/runup
    assert L.count_combinations("a runup in inflation")["hawk"] == 1


def test_substring_terms_count_single_instance():
    # "inflation pressure" が一致した位置で "inflation" は数えない
    c = L.count_combinations("inflation pressure abated")
    assert (c["hawk"], c["dove"]) == (0, 1)
    assert c["matches"][0][1] == "inflation pressure"
    # unemployment は employment と別トークン (declining unemployment = hawkish)
    c = L.count_combinations("declining unemployment")
    assert (c["hawk"], c["dove"]) == (1, 0)
    # Table 4 Notes: core inflation / inflation expectations は unigram inflation で拾う
    assert L.count_combinations("core inflation accelerated")["hawk"] == 1
    assert L.count_combinations("accelerating inflation expectations")["hawk"] == 1


def test_combination_counting_rule_is_term_x_modifier():
    # TERM 2 出現 × 窓内 MODIFIER 2 出現 = 4 件 (字義読み、凍結)
    assert L.count_combinations("high inflation and rising inflation")["hawk"] == 4


def test_net_hawkishness_equation_one_and_neutral_fill():
    assert L.net_hawkishness("no dictionary words here") == 1.0
    assert L.net_hawkishness("higher inflation") == pytest.approx(2.0)
    assert L.net_hawkishness("lower inflation") == pytest.approx(0.0)
    assert L.net_hawkishness("higher inflation and lower inflation") == pytest.approx(1.0)
    # 全 hawk で 1 ヒット→2 ヒットは公刊式で 2→2 (Δ=0) — E23 形への置換禁止の pin
    assert L.delta_net_hawkishness("higher inflation and rising inflation",
                                   "higher inflation") == pytest.approx(0.0)


def test_no_price_or_return_coupling_in_module():
    import inspect
    src = inspect.getsource(L)
    for banned in ("pandas", "read_parquet", "sqlite", "requests", "yfinance",
                   "pnl", "return_", "fwd", "oanda"):
        assert banned not in src, f"ABGH lexicon module に {banned} が混入"
