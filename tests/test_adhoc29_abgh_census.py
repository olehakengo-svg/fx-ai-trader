"""#29 step 1 — 価格非接触 census 列挙器の pin (合成コーパス、network/価格不要).

ペア規則 (E23 継承: 各 CB 初回は分母外 / staleness >120d void / Fed×ECB 同日 void、
void は分母からも除外)、τ = 0、過半は厳密不等号、を pin する。
"""
import inspect

from tools import adhoc29_abgh_census as C
from tools import adhoc29_lexicon_abgh2019 as L


def _doc(cb, d, text):
    return {"cb": cb, "date": d, "text": text, "n_chars": len(text)}


HAWK = "inflation is rising"            # NH = 2
DOVE = "inflation is declining"         # NH = 0
NONE = "the committee met"              # NH = 1 (無ヒット → 中立代入)


def test_constants_pin_and_consistency_with_e23():
    from tools import e23_pass1_events as P
    assert C.STALENESS_VOID_DAYS == P.STALENESS_VOID_DAYS == 120
    assert C.TAU == 0.0
    assert C.DENSE_THRESHOLD == 0.5
    assert C.SURVIVING_CBS == ("fed", "ecb", "boe")
    assert C.REFERENCE_VALUES["abg2012_post_audit_pass1_2026_10_01"]["n"] == 228
    assert C.REFERENCE_VALUES["abg2012_post_audit_pass1_2026_10_01"]["k"] == 40


def test_first_doc_excluded_and_drift_counted():
    docs = [_doc("fed", "2015-01-28", HAWK), _doc("fed", "2015-03-18", HAWK),
            _doc("fed", "2015-04-29", DOVE), _doc("fed", "2015-06-17", NONE)]
    e = C.enumerate_pairs(docs, cbs=("fed",))
    assert e["per_cb"]["fed"]["first_excluded"] == 1
    assert e["n_eligible_pairs"] == 3
    assert e["k_drift_pairs"] == 2           # 2→2 (0), 2→0 (drift), 0→1 (drift)
    assert e["share_drift"] == 2 / 3
    assert e["docs_with_hits"] == 3 and e["docs_nh_ne_neutral"] == 3


def test_staleness_void_removed_from_denominator():
    docs = [_doc("boe", "2015-01-08", HAWK), _doc("boe", "2015-06-04", DOVE),  # 147 d > 120
            _doc("boe", "2015-07-09", HAWK)]
    e = C.enumerate_pairs(docs, cbs=("boe",))
    assert e["voids"] == {"boe:staleness_gt_120d": 1}
    assert e["n_eligible_pairs"] == 1 and e["k_drift_pairs"] == 1


def test_fed_ecb_same_day_void_uses_all_usable_docs():
    # ecb が生存 CB に無くても、Fed と同日なら fed 側のペアは void (pass-1 と同じ)
    docs = [_doc("fed", "2016-01-27", HAWK), _doc("fed", "2016-03-16", DOVE),
            _doc("ecb", "2016-03-16", NONE), _doc("ecb", "2016-01-21", NONE)]
    e = C.enumerate_pairs(docs, cbs=("fed",))
    assert e["collision_days"] == ["2016-03-16"]
    assert e["voids"] == {"fed:fed_ecb_same_day": 1}
    assert e["n_eligible_pairs"] == 0 and e["share_drift"] is None
    assert C.verdict(e["share_drift"]) == "NO_ELIGIBLE_PAIRS"


def test_verdict_strict_majority():
    assert C.verdict(0.5) == "NOT_DENSE_CLOSE"      # 丁度半数は不通過
    assert C.verdict(0.5000001) == "DENSE_PASS"
    assert C.verdict(0.175) == "NOT_DENSE_CLOSE"


def test_delta_uses_published_formula_not_e23_form():
    # 全 hawk 1 ヒット→2 ヒット: 公刊式 2→2 = Δ 0 (drift に数えない)
    docs = [_doc("ecb", "2017-01-19", HAWK), _doc("ecb", "2017-03-09", HAWK + " and " + HAWK)]
    e = C.enumerate_pairs(docs, cbs=("ecb",))
    assert e["n_eligible_pairs"] == 1 and e["k_drift_pairs"] == 0
    assert L.net_hawkishness(HAWK + " and " + HAWK) == 2.0


def test_census_module_is_price_free():
    src = inspect.getsource(C)
    for banned in ("read_parquet", "build_d1", "fwd", "pnl", "oanda", "sqlite", "yfinance",
                   "CB_MAP", "HORIZON"):
        assert banned not in src, f"census module に {banned} が混入 (価格非接触違反)"
