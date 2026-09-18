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


# --- Codex P2 (PR #270 第14波): ラベルは基数ではなく実体で pin ------------------
def test_label_population_is_pinned_by_identity_not_cardinality():
    """順序つき介入日リストの指紋が凍結時と一致すること。

    日数 10 / block 数 4 だけの照合では、**同じ block 内で介入日が 1 日
    入れ替わっても通る** — 陽性マスクも J も p も secondary も変わるのに
    ABORT しない。「一度限りの凍結測定」を名乗る以上、母集団は実体で pin する。
    """
    days = p2.load_intervention_days()
    assert p2._sha16_dates(days) == p2.EXPECTED_IV_SHA16, [str(d) for d in days]


def test_abort_when_an_intervention_date_is_swapped_within_its_block(monkeypatch):
    """基数を保ったまま介入日を 1 日ずらしたら ABORT すること (counterfactual)。

    この入れ替えは 10 日 / 4 block を保つので、第13波までのガードは素通りした。
    """
    real = p2.load_intervention_days

    def shifted():
        days = list(real())
        days[4] = days[4] + dt.timedelta(days=1)   # 2024-05-01 -> 05-02 (同 block 内)
        return days

    monkeypatch.setattr(p2, "load_intervention_days", shifted)
    moved = shifted()
    assert len(moved) == p2.EXPECTED_INTERVENTION_DAYS
    assert len(p2.episode_blocks(moved)) == p2.EXPECTED_EPISODE_BLOCKS
    with pytest.raises(SystemExit) as ei:
        p2.run()
    assert "ABORT" in str(ei.value)
    assert "sha" in str(ei.value), str(ei.value)


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
    """FAIL を『分離が無い』と読ませないための pin (Codex P2 第4-6波)。

    効果量の軸は armed に掛かる **episode block** 数 ([3,1,2,1] の 4 block)。
    hit/miss は生成位置の**全日**で強制する。
    """
    import json
    art = pathlib.Path("knowledge-base/raw/analysis/family-a-pass2-verdict-2026-09-18.json")
    pa = json.loads(art.read_text(encoding="utf-8"))["power_analysis_post_hoc"]
    assert pa["block_sizes_business_days"] == [3, 1, 2, 1]
    curve = {r["hit_blocks"]: r["power"] for r in pa["curve"]}
    assert pa["observed_hit_blocks"] == 2
    assert pa["power_at_observed_effect"] == curve[2]
    assert 0.05 < curve[2] < 0.30, curve          # 観測効果量は実用域に遠い
    # 各行が名乗った反復数を実際に集めていること (attempts != kept で誤魔化さない)
    for r in pa["curve"]:
        assert r["reached_target_reps"] is True, r
        assert r["reps_kept"] == 600 and r["attempts"] >= r["reps_kept"], r
    assert curve[0] < 0.02 and curve[1] < 0.05    # 弱い効果は検出不能
    assert curve[3] < 0.80, curve                 # 3/4 でもまだ実用域未満
    assert curve[4] > 0.90, curve                 # 全 block hit なら実用域
    assert all(curve[k] <= curve[k + 1] + 1e-9 for k in range(4))


def test_power_sim_enforces_hit_status_on_every_block_day():
    """先頭日だけの判定だと miss 指定 block が armed に掛かる (Codex P2 第6波)。

    hit = block のいずれかの日が armed / miss = 全日が非 armed、を全日検査で強制。
    """
    from tools import family_a_ladder_detector as det
    from tools.family_a_pass1 import EXPLORE_END, EXPLORE_START
    out = det.build(EXPLORE_START, EXPLORE_END)
    armed = [d in out.armed for d in out.days]
    # 内部間隔の広い block (span 20bd) を含む構成で 0 hit を要求すると、
    # 先頭日だけの判定では armed に掛かる配置が混ざる。全日強制なら混ざらない。
    curve = p2.power_curve(armed, [[0, 19, 20], [0], [0, 1], [0]], reps=40, seed=7)
    zero = next(r for r in curve if r["hit_blocks"] == 0)
    assert zero["power"] == 0.0, zero
    assert zero["mean_j"] < 0, zero   # 全 miss なら J は必ず負


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


# --- Codex P2 (PR #270 第7波): 生成ラベルが 4 block を保つこと ------------------
def test_power_sim_keeps_the_four_episode_blocks_distinct():
    """配置が episode-gap 内に重なると `episode_blocks` で 4 未満に潰れる。

    潰れたサンプルを数えていると「4-block 設計の検出力」ではなくなる。
    """
    from tools import family_a_ladder_detector as det
    from tools.family_a_pass1 import EXPLORE_END, EXPLORE_START
    out = det.build(EXPLORE_START, EXPLORE_END)
    days = out.days
    armed = [d in out.armed for d in days]
    offsets = [[0, 19, 20], [0], [0, 1], [0]]
    curve = p2.power_curve(armed, offsets, days=days, reps=60, seed=11)
    for row in curve:
        assert row["reps_kept"] > 0, row
        # 検証を通ったサンプルしか数えていないので、棄却分だけ reps を下回る
        assert row["reps_kept"] <= 60, row
    # days を渡さないと 4-block 検証が働かず、通る本数が増える (= 潰れた分が混ざる)
    loose = p2.power_curve(armed, offsets, reps=60, seed=11)
    assert sum(r["reps_kept"] for r in loose) >= sum(r["reps_kept"] for r in curve)


# --- Codex P2 (PR #270 第8波): 凍結 null の構造診断 -----------------------------
def test_frozen_null_structure_defect_is_disclosed():
    """凍結 null が 4 block を厳密には保たない事実を成果物に残す。

    直さない代わりに**開示する**という判断そのものを pin する。
    これを消して verdict だけ残すと、読み手は混合 null の上の p を額面で受け取る。
    """
    import json
    art = pathlib.Path("knowledge-base/raw/analysis/family-a-pass2-verdict-2026-09-18.json")
    d = json.loads(art.read_text(encoding="utf-8"))
    nd = d["frozen_null_structure_diagnostic"]
    assert nd["observed_blocks"] == 4
    assert nd["n_shifts"] == 1107
    # 4 block を保たないシフトが実在する (= 開示すべき欠陥がある)
    assert nd["non_preserving_shifts"] > 0
    assert 0.10 < nd["non_preserving_fraction"] < 0.35, nd
    assert set(nd["block_count_distribution"]) == {"4", "5"}
    # 直さない判断が文章として残っていること
    assert "10.5" in nd["note"] and "禁止" in nd["note"]
    # verdict は凍結規則のまま
    assert d["verdict"] == "FAIL"


def test_null_diagnostic_never_touches_the_signal():
    """診断は signal (armed) を参照しない = look を消費しない。

    構文 grep ではなく **性質** で pin する — docstring が "armed" に言及するのは
    正当なので、文字列検索だと誤検出する (本セッションで実際に踏んだ)。
    ここでは「signal を受け取る引数が無い」= 構造的に参照不能、を固定する。
    """
    import inspect
    params = list(inspect.signature(p2.null_structure_diagnostic).parameters)
    assert params == ["days", "iv_days"], params
    # armed を渡す余地が無い = 診断は signal から独立
    assert "armed" not in params


# --- Codex P2 (PR #270 第9波): 凍結構成の全項目照合 ----------------------------
def test_abort_when_frozen_configuration_drifts(monkeypatch):
    """events が同じでも H / カレンダーが変われば別の J になる。

    events だけの照合では『凍結された測定』を名乗ったまま値が変わりうる。
    """
    from tools import family_a_ladder_detector as det
    monkeypatch.setattr(det, "H_HORIZON_BD", det.H_HORIZON_BD + 5)
    with pytest.raises(SystemExit) as ei:
        p2.run()
    msg = str(ei.value)
    assert "ABORT" in msg
    assert "params" in msg or "armed" in msg, msg


# --- Codex P2 (PR #270 第10波): 日付の同一性まで照合 ----------------------------
def test_abort_when_business_day_identity_changes(monkeypatch):
    """営業日を 1 日入れ替えても長さと armed 率は変わりうる。

    日数と率だけの照合では通ってしまうので、凍結 events から armed を
    独立再構成して**日付の同一性**まで見る。
    """
    from tools import family_a_ladder_detector as det
    import datetime as _d
    real = det.is_business_day

    def swapped(day: _d.date) -> bool:
        # 平日 1 日を非営業日に、直後の土曜を営業日に入れ替える (総数は保つ)
        if day == _d.date(2023, 3, 15):
            return False
        if day == _d.date(2023, 3, 18):
            return True
        return real(day)

    monkeypatch.setattr(det, "is_business_day", swapped)
    with pytest.raises(SystemExit) as ei:
        p2.run()
    assert "ABORT" in str(ei.value)


def test_series_fingerprint_is_recorded():
    """days / armed の指紋を成果物に残す (pass-1 が保存していなかった穴の補い)。"""
    import json
    art = pathlib.Path("knowledge-base/raw/analysis/family-a-pass2-verdict-2026-09-18.json")
    fp = json.loads(art.read_text(encoding="utf-8"))["series_fingerprint"]
    assert len(fp["days_sha256_16"]) == 16 and len(fp["armed_sha256_16"]) == 16
    assert fp["days_sha256_16"] != fp["armed_sha256_16"]
    assert "pass-1" in fp["note"]
