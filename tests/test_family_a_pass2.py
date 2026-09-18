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


def test_positive_control_has_power():
    """陽性が全て armed 内なら α=0.05 を通せること。

    これが落ちたら FAIL は『効果なし』ではなく『検出力ゼロ』を意味する。
    """
    n = 1108
    armed = [False] * n
    for e in (30, 200, 520, 700, 800, 900, 1000):
        for k in range(21):
            if e + k < n:
                armed[e + k] = True
    pos = {e + 5 for e in (30, 200, 520, 700, 800, 900, 1000)}
    lab = [i in pos for i in range(n)]
    r = p2.permutation_p(armed, lab)
    assert r["p_one_sided"] <= p2.ALPHA, r


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
        assert {"n_events", "events_with_hit", "hit_days", "j"} <= set(d), (yr, d)
        assert d["events_with_hit"] <= d["n_events"]
    # 2022: 1 event (09-29) が 10-21 と 10-24 を覆う = event 1 / 日 2
    assert per_year["2022"]["events_with_hit"] == 1
    assert per_year["2022"]["hit_days"] == 2
    # 全 7 event のうち当てたのは 2 本だけ
    assert sum(d["events_with_hit"] for d in per_year.values()) == 2


def test_hits_field_name_is_gone():
    """曖昧な `hits` に戻ったら落ちる (命名が estimand を運ぶ)。"""
    src = pathlib.Path("tools/family_a_pass2.py").read_text(encoding="utf-8")
    assert '"hits"' not in src
