"""family A pass-2 — 凍結統計設計の pin + 既知答え検証 (2026-09-18)。

pass-2 は explore の唯一の look を消費するので、統計コアが「既知の答えを返す」
ことをテストで固定しておく。特に **positive control** (強い効果なら α を通せる)
は、FAIL を「検出力不足」と取り違えないための前提。
"""
import datetime as dt
import json
import pathlib

import pytest

from tools import family_a_pass2 as p2


# --- 凍結定数 ---------------------------------------------------------------
def test_frozen_design_constants():
    assert p2.B_SHIFTS == 10_000
    assert p2.ALPHA == 0.05
    assert p2.DIRECTION == "sell_USD_buy_JPY"
    assert p2.EPISODE_GAP_DAYS == 30
    assert (p2.EXPECTED_INTERVENTION_DAYS, p2.EXPECTED_EPISODE_BLOCKS) == (10, 4)


# --- 統計コア: 既知の答え -----------------------------------------------------
def test_youden_j_extremes():
    armed = [True, True, False, False]
    assert p2.youden_j(armed, [True, True, False, False]) == 1.0
    assert p2.youden_j(armed, [False, False, True, True]) == -1.0


def test_youden_j_is_nan_when_a_class_is_empty():
    """陽性ゼロを 0.0 に潰さない (『測れない』と『効果なし』の区別)。"""
    j = p2.youden_j([True, False], [False, False])
    assert j != j


def test_circular_shift_preserves_length_and_positives():
    lab = [True, False, False, True, False]
    for k in (1, 3, 4):
        s = p2.circular_shift(lab, k)
        assert len(s) == len(lab) and sum(s) == sum(lab)
    assert p2.circular_shift(lab, 0) == lab


def test_perfect_detector_reaches_minimum_p():
    n = 300
    armed = [i % 37 < 11 for i in range(n)]
    r = p2.permutation_p(armed, list(armed))
    assert r["j_obs"] == 1.0
    assert r["n_shifts"] == n - 1


def test_positive_control_uses_the_production_armed_series():
    """検出力の pin は**凍結検出器の実 armed 系列**の上で取る (Codex P2 / PR #270)。

    circular-shift の有意性は armed 窓の位置と間隔に依存するので、
    合成マスクで取った pin は verdict doc が主張する p=0.0027 を保証しない。
    これが落ちたら FAIL は『効果なし』ではなく『検出力ゼロ』を意味する。
    """
    from tools import family_a_ladder_detector as det
    from tools.family_a_pass1 import EXPLORE_END, EXPLORE_START

    out = det.build(EXPLORE_START, EXPLORE_END)
    days = out.days
    armed = [d in out.armed for d in days]
    assert sum(armed) == 147 and len(days) == 1108, (sum(armed), len(days))

    # 各 event 窓の内側に合成陽性を 1 つずつ置く (実ラベルは使わない)
    idx = {d: i for i, d in enumerate(days)}
    pos = {idx[e] + 5 for e in out.events}
    assert all(armed[i] for i in pos)
    lab = [i in pos for i in range(len(days))]
    r = p2.permutation_p(armed, lab)
    assert r["p_one_sided"] <= p2.ALPHA, r
    # verdict doc §2 が主張する値そのものを pin (実 armed 系列上の 0.0190)
    assert abs(r["p_one_sided"] - 0.0190) < 0.0005, r["p_one_sided"]


def test_null_is_centred_on_zero():
    n = 400
    armed = [i % 23 < 5 for i in range(n)]
    lab = [i % 71 == 0 for i in range(n)]
    r = p2.permutation_p(armed, lab)
    assert abs(r["null_mean"]) < 0.05


# --- episode 個別化 ----------------------------------------------------------
def test_episode_blocks_split_on_30_day_gap():
    d = dt.date
    days = [d(2022, 9, 22), d(2022, 10, 21), d(2024, 4, 29), d(2024, 5, 1)]
    blocks = p2.episode_blocks(days)
    assert [len(b) for b in blocks] == [2, 2]


# --- 凍結ラベル母集団 --------------------------------------------------------
def test_label_population_matches_the_prereg_declaration():
    """§3 の「4 blocks / 10 介入日」が今も成り立つこと。"""
    days = p2.load_intervention_days()
    assert len(days) == p2.EXPECTED_INTERVENTION_DAYS, [str(d) for d in days]
    assert len(p2.episode_blocks(days)) == p2.EXPECTED_EPISODE_BLOCKS


def test_verdict_artifact_records_the_calendar_defect():
    """凍結カレンダーが陽性を 3 日落とした事実が成果物に残っていること。

    この欠陥を伏せた引用を防ぐための pin (verdict doc §3 / pre-reg §11.3)。
    """
    art = pathlib.Path("knowledge-base/raw/analysis/family-a-pass2-verdict-2026-09-18.json")
    res = json.loads(art.read_text(encoding="utf-8"))
    off = res["intervention_days_off_business_calendar"]
    assert set(off) == {"2024-04-29", "2026-05-04", "2026-05-06"}
    assert res["contingency"]["n_pos"] == len(res["intervention_days"]) - len(off) == 7
    assert res["verdict"] == "FAIL"


# --- Codex P2 (PR #270): event 数と介入「日」数を混同しない --------------------
def test_secondary_separates_hit_events_from_hit_days():
    """1 event が複数の介入日を覆うので、両者は別フィールドでなければならない。

    初版は `hits` (= 介入日数) を「hit した event 数」として表に書き、
    2022 を「2 event / 2 hit」と誤記していた (実際は 1/2 event)。
    """
    import json
    art = pathlib.Path("knowledge-base/raw/analysis/family-a-pass2-verdict-2026-09-18.json")
    per_year = json.loads(art.read_text(encoding="utf-8"))["secondary_descriptive"]["per_event_year"]
    for yr, d in per_year.items():
        assert {"n_events", "events_with_hit", "hit_days"} <= set(d), (yr, d)
        assert d["events_with_hit"] <= d["n_events"]
    # 2022: 1 event (09-29) が 10-21 と 10-24 を覆う = event 1 / 日 2
    assert per_year["2022"]["events_with_hit"] == 1
    assert per_year["2022"]["hit_days"] == 2
    # 全 7 event のうち当てたのは 2 本だけ
    assert sum(d["events_with_hit"] for d in per_year.values()) == 2


def test_per_year_never_uses_the_ambiguous_hits_field():
    """per-year の曖昧な `hits` に戻ったら落ちる (命名が estimand を運ぶ)。

    power_curve 側の `"hits"` (効果量の刀み) は別概念なので対象外 —
    pin は **per_year のキー集合** で見る (文字列 grep ではなく性質で見る)。
    """
    import json
    art = pathlib.Path("knowledge-base/raw/analysis/family-a-pass2-verdict-2026-09-18.json")
    per_year = json.loads(art.read_text(encoding="utf-8"))["secondary_descriptive"]["per_event_year"]
    for yr, d in per_year.items():
        assert "hits" not in d, (yr, sorted(d))
        assert "events_with_hit" in d and "hit_days" in d


# --- Codex P2 (PR #270): 寄与 J と層別 J を分けて持つ -------------------------
def test_contribution_and_stratified_j_are_separate_fields():
    """寄与 J (ラベル全年) と層別 J (年内) は別物。混同すると話者性能を誤読する。

    初版は寄与 J を「片山期の検出器性能」として読み、「ほぼゼロ」と書いていた。
    """
    import json
    art = pathlib.Path("knowledge-base/raw/analysis/family-a-pass2-verdict-2026-09-18.json")
    per_year = json.loads(art.read_text(encoding="utf-8"))["secondary_descriptive"]["per_event_year"]
    for yr, d in per_year.items():
        assert "contribution_j_labels_all_years" in d
        assert "stratified_j_within_year" in d
    # 2026 は寄与 J だと ~0.048 だが層別では ~0.246 — 「ほぼゼロ」ではない
    assert per_year["2026"]["contribution_j_labels_all_years"] < 0.10
    assert per_year["2026"]["stratified_j_within_year"] > 0.20
    # 2024 は介入があるのに event ゼロ = 検出器がまる 1 年沈黙した年
    assert per_year["2024"]["n_events"] == 0
    assert per_year["2024"]["n_intervention_days_in_year"] > 0
    assert per_year["2024"]["stratified_j_within_year"] == 0.0


# --- Codex P2 (PR #270): 成果物は strict JSON でなければならない ---------------
def test_artifact_is_strict_json_without_nan():
    """空の層 (2023/2025) を `NaN` で書くと JSON 仕様外になり厳格パーサが落ちる。"""
    import json
    art = pathlib.Path("knowledge-base/raw/analysis/family-a-pass2-verdict-2026-09-18.json")
    raw = art.read_text(encoding="utf-8")
    assert "NaN" not in raw and "Infinity" not in raw
    def _boom(x):
        raise AssertionError(f"strict JSON violation: {x}")
    d = json.loads(raw, parse_constant=_boom)
    per_year = d["secondary_descriptive"]["per_event_year"]
    # event も介入日も無い年は null (0.0 に潰さない — 「測れない」と「効果ゼロ」は別)
    assert per_year["2023"]["stratified_j_within_year"] is None
    assert per_year["2024"]["stratified_j_within_year"] == 0.0


# --- Codex P2 (PR #270 第4波): perfect-effect control は power analysis ではない --
def test_power_curve_preserves_episode_blocks_and_shows_low_power():
    """FAIL を『分離が無い』と読ませないための pin (Codex P2 第4-5波)。

    効果量の軸は armed に入る **episode block** 数。実ラベルは営業日系列上で
    [3,1,2,1] の 4 block に集中しており、一様散布は独立試行を仮定して
    検出力を過大評価する (day 基準だと 0.338、block 保存だと 0.145)。
    """
    import json
    art = pathlib.Path("knowledge-base/raw/analysis/family-a-pass2-verdict-2026-09-18.json")
    pa = json.loads(art.read_text(encoding="utf-8"))["power_analysis_post_hoc"]
    assert pa["block_sizes_business_days"] == [3, 1, 2, 1]
    curve = {r["hit_blocks"]: r["power"] for r in pa["curve"]}
    assert pa["observed_hit_blocks"] == 2
    assert pa["power_at_observed_effect"] == curve[2]
    # 観測効果量では実用域に遠く届かない
    assert 0.05 < curve[2] < 0.30, curve
    # 単調 + 弱い効果は検出不能
    assert curve[0] < 0.02 and curve[1] < 0.05
    assert all(curve[k] <= curve[k + 1] + 1e-9 for k in range(4))
    # 完全な検出器ですら 0.9 に届かない = 設計そのものに無理があった
    assert 0.75 < curve[4] < 0.90, curve


def test_power_analysis_is_flagged_post_hoc_and_unused_for_verdict():
    """post-hoc であること・判定に使っていないことが成果物に明記されていること。"""
    import json
    art = pathlib.Path("knowledge-base/raw/analysis/family-a-pass2-verdict-2026-09-18.json")
    d = json.loads(art.read_text(encoding="utf-8"))
    note = d["power_analysis_post_hoc"]["note"]
    assert "post-hoc" in note and "verdict" in note
    # verdict は凍結 α 規則だけで決まる (検出力曲線に依存しない)
    assert d["verdict"] == "FAIL"
    assert d["statistic"]["p_one_sided"] > d["alpha"]
