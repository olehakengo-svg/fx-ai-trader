"""Pins for the hunt_events reader (2026-09-19, rule:R3).

MEMORY `project_review_gate_vacuous_2026_09_11` の教訓:
**検知器には「NG を返す既知の入力」を同じコミットで pin せよ** — でないと
「問題なし」が恒真命題になっていても気づけない。そこで本ファイルは
PASS 側だけでなく、5 層の欠陥それぞれについて**落ちるべき入力**を固定する。
"""
from __future__ import annotations

import json

import pytest

from tools import hunt_event_dataset as hed


REAL_DATASET = "knowledge-base/raw/hunt_events"


def _row(**over):
    base = dict(
        entry_time="2026-09-01T00:00:00+00:00",
        strategy="sr_anti_hunt_bounce",
        instrument="USDJPY=X",
        direction="BUY",
        entry_price=150.0,
        hunt_extreme=149.5,
        opposite_sr=151.0,
        sl=149.5,
        tp=151.0,
        atr_pips=8.0,
        atr_price=0.08,
        side="support",
        level=149.9,
        reversal=None,
        actual_outcome=None,
        actual_pnl_pips=None,
        adx=22.5,
        bbpb=0.4,
        rr=2.0,
        score=3.5,
    )
    base.update(over)
    return base


def _write(tmp_path, rows, name="2026-09-01.jsonl"):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


# --------------------------------------------------------------------------
# D1 — 形式: 旧実装が読めなかった JSONL を読む
# --------------------------------------------------------------------------

def test_d1_reads_jsonl_that_json_loads_rejects(tmp_path):
    """NG 入力の再現: 旧 sr_audit の `json.loads(whole_file)` は 2 行目で落ちる。"""
    path = _write(tmp_path, [_row(), _row(entry_price=150.1)])
    with pytest.raises(json.JSONDecodeError):
        json.loads(path.read_text(encoding="utf-8"))
    assert len(hed.load_rows(path)) == 2


def test_d1_accepts_directory_and_glob(tmp_path):
    _write(tmp_path, [_row()], "2026-09-01.jsonl")
    _write(tmp_path, [_row(entry_price=151.0)], "2026-09-02.jsonl")
    assert len(hed.load_rows(tmp_path)) == 2
    assert len(hed.load_rows(str(tmp_path / "*.jsonl"))) == 2


def test_d1_corrupt_line_is_loud_not_silent(tmp_path):
    p = tmp_path / "2026-09-01.jsonl"
    p.write_text(json.dumps(_row()) + "\n<<<<<<< HEAD\n", encoding="utf-8")
    with pytest.raises(ValueError, match="is not valid JSON"):
        hed.load_rows(p)


# --------------------------------------------------------------------------
# D2 — provenance: feed-symbol 不変条件
# --------------------------------------------------------------------------

def test_d2_quarantines_the_synthetic_row_the_old_signature_missed(tmp_path):
    """NG 入力: 2026-04-28.jsonl に実在する合成行そのもの。

    旧署名 (`adx` 整数 ∧ `atr_price == 0.001`) はこの行を**通してしまう**
    — adx=18.5 は整数でなく atr_price=0.12 なので。feed-symbol なら落ちる。
    """
    synthetic = _row(instrument="USD_JPY", adx=18.5, atr_price=0.12,
                     entry_price=153.5, level=153.42)
    old_signature_catches = (
        float(synthetic["adx"]).is_integer() and synthetic["atr_price"] == 0.001)
    assert old_signature_catches is False, "旧署名がこの行を捕まえるなら前提が変わった"

    collected, quarantined = hed.split_provenance([_row(), synthetic])
    assert len(collected) == 1
    assert quarantined == [synthetic]


@pytest.mark.parametrize("inst", ["USD_JPY", "usdjpy=x", "USDJPY", "", None, 150.0])
def test_d2_rejects_every_non_feed_symbol(inst):
    _, quarantined = hed.split_provenance([_row(instrument=inst)])
    assert len(quarantined) == 1


@pytest.mark.parametrize("inst", ["USDJPY=X", "EURJPY=X", "GBPUSD=X", "EURUSD=X", "GBPJPY=X"])
def test_d2_keeps_every_symbol_the_real_collector_writes(inst):
    collected, _ = hed.split_provenance([_row(instrument=inst)])
    assert len(collected) == 1


# --------------------------------------------------------------------------
# D3 — 独立観測の単位
# --------------------------------------------------------------------------

def test_d3_collapses_repeat_evaluations_of_the_same_bar():
    """NG 入力: entry_time だけ違う同一 payload — engine の tick 再評価。"""
    rows = [_row(entry_time=f"2026-09-01T00:0{i}:00+00:00") for i in range(5)]
    deduped, repeats, conflicts = hed.collapse_repeats(rows)
    assert len(deduped) == 1
    assert repeats == 4
    assert conflicts == []
    # 代表は最初の書込み時刻
    assert deduped[0]["entry_time"] == "2026-09-01T00:00:00+00:00"


def test_d3_does_not_collapse_genuinely_distinct_signals():
    """誤爆しないこと: market/signal フィールドが違えば別観測。"""
    rows = [_row(), _row(entry_price=150.001), _row(side="resistance")]
    deduped, repeats, conflicts = hed.collapse_repeats(rows)
    assert len(deduped) == 3
    assert repeats == 0
    assert conflicts == []


def test_d3_identity_uses_signal_time_fields_only():
    """identity = 書込み時刻と post-hoc outcome を除く全フィールド。"""
    a, b = _row(), _row(entry_time="2027-01-01T00:00:00+00:00")
    assert hed.identity(a) == hed.identity(b)
    assert hed.identity(a) != hed.identity(_row(adx=22.6))
    # outcome 列は identity に入らない (PR #272 Codex P2)
    for field, value in (("reversal", True), ("actual_outcome", "WIN"),
                         ("actual_pnl_pips", 12.5)):
        assert hed.identity(a) == hed.identity(_row(**{field: value})), field


# --------------------------------------------------------------------------
# D4 — ラベル付き行のみが母集団
# --------------------------------------------------------------------------

def test_d4_unlabeled_rows_are_not_losses():
    labeled, unlabeled = hed.split_labels(
        [_row(reversal=True), _row(reversal=False), _row(reversal=None)])
    assert len(labeled) == 2
    assert len(unlabeled) == 1


def test_d4_gate_blocks_when_nothing_is_labeled(tmp_path):
    """NG 入力: 全行 `reversal is None` = 実データセットの現状。"""
    _write(tmp_path, [_row(entry_price=150 + i * 0.01) for i in range(200)])
    result = hed.prepare(tmp_path)
    assert result["ok"] is False
    assert result["events"] == []
    assert any("labeled rows 0" in r for r in result["blocked_reasons"])


def test_d4_gate_passes_once_labels_exist(tmp_path):
    """反対側: labeler が動けば同じ入力が通る (恒真 NG でないことの pin)。"""
    _write(tmp_path, [_row(entry_price=150 + i * 0.01, reversal=(i % 2 == 0))
                      for i in range(40)])
    result = hed.prepare(tmp_path)
    assert result["ok"] is True
    assert len(result["events"]) == 40


def test_d4_gate_blocks_just_below_the_floor(tmp_path):
    _write(tmp_path, [_row(entry_price=150 + i * 0.01, reversal=True)
                      for i in range(hed.LABELED_N_FLOOR - 1)])
    assert hed.prepare(tmp_path)["ok"] is False


# --------------------------------------------------------------------------
# D5 — cell 選択が実際に母集団を絞る (旧実装はラベルだけ付けていた)
# --------------------------------------------------------------------------

def test_d5_pair_filter_actually_filters():
    rows = [_row(instrument="USDJPY=X"), _row(instrument="EURJPY=X")]
    assert len(hed.select_cell(rows, pair="USD_JPY")) == 1
    assert len(hed.select_cell(rows, pair="USDJPY=X")) == 1
    assert len(hed.select_cell(rows, pair="EUR_JPY")) == 1
    assert len(hed.select_cell(rows)) == 2


def test_d5_side_filter_maps_bull_to_support():
    rows = [_row(side="support"), _row(side="resistance")]
    assert hed.select_cell(rows, side="bull")[0]["side"] == "support"
    assert hed.select_cell(rows, side="bear")[0]["side"] == "resistance"
    assert len(hed.select_cell(rows, side="both")) == 2


def test_d5_unknown_side_is_loud():
    with pytest.raises(ValueError, match="unknown side"):
        hed.select_cell([_row()], side="sideways")


# --------------------------------------------------------------------------
# 実データセットに対する pin — labeler が入った日に落ちて気づけるように
# --------------------------------------------------------------------------

def test_real_dataset_is_currently_data_blocked():
    """committed な観測データセットを実測で pin する。

    ここが落ちたときの読み方:
      - `labeled > 0` になった → labeler が実装された。readout
        (`wiki/analyses/hunt-events-dataset-readout-2026-09-19.md`) を更新し、
        registry `hunt-events-labeler-disposition` を resolve せよ。
      - `quarantined == 0` になった → 誰かが raw の合成行を消した。raw は
        観測記録なので書き換えない規約 (D2) を確認せよ。
    """
    result = hed.prepare(REAL_DATASET)
    acc = result["accounting"]
    assert acc["rows_read"] > 60000, "データセットが縮んでいる — 取り違えを疑え"
    assert acc["quarantined_provenance"] == 1, "合成行は 1 行 (2026-04-28)"
    assert acc["labeled"] == 0, "labeler が実装されたなら readout を更新せよ"
    assert result["ok"] is False


def test_real_dataset_repeat_share_is_material():
    """N 膨張が「無視できる程度」ではないことの pin。

    ⚠️ **膨張率は dedup 窓に強く依存する** — 既定 1h で約 3.4 倍、無制限なら
    約 7.0 倍 (PR #272 Codex P2、5 巡目)。点推定として引用しないこと。
    """
    acc = hed.prepare(REAL_DATASET)["accounting"]
    assert acc["dedup_window_sec"] == hed.DEDUP_WINDOW_SEC
    distinct = acc["distinct_observations"]
    collected = distinct + acc["collapsed_repeats"]
    assert collected / distinct > 3.0, f"inflation factor = {collected / distinct:.2f}"


def test_real_dataset_inflation_is_window_dependent():
    """窓を変えると膨張率が大きく動くこと自体を pin する。

    単一の点推定 (旧 readout の「7.0 倍」) を publish した誤りの再発防止。
    """
    tight = hed.prepare(REAL_DATASET, window_sec=900.0)["accounting"]
    loose = hed.prepare(REAL_DATASET, window_sec=None)["accounting"]
    assert tight["distinct_observations"] > 2 * loose["distinct_observations"]


# --------------------------------------------------------------------------
# 統計関数側の fail-closed — 呼び出し元が prepare() を飛ばしても再発しない
# --------------------------------------------------------------------------

def test_stage_a_refuses_unlabeled_population():
    """NG 入力: 未ラベル行をそのまま渡す = 修正前の実データ経路。

    修正前はここで n=100 / wins=0 / WR=0.00% / z=-10 の
    「有意に負のエッジ」が返り、仮説が虚偽の根拠で棄却されていた。
    """
    from tools.sr_audit import stage_a_audit

    out = stage_a_audit([_row() for _ in range(100)])
    assert out["verdict"] == "data_blocked"
    assert out["n"] == 0
    assert out["n_supplied"] == 100
    assert out["n_unlabeled"] == 100
    assert "reversal is None" in out["blocked_reason"]


def test_stage_a_refuses_even_a_single_unlabeled_row():
    """部分ラベルも拒否 — 未ラベル 1 行でも分母が汚れる。"""
    from tools.sr_audit import stage_a_audit

    events = [_row(reversal=True) for _ in range(99)] + [_row(reversal=None)]
    assert stage_a_audit(events)["verdict"] == "data_blocked"


def test_stage_a_computes_normally_on_a_fully_labeled_population():
    """反対側: 全行ラベル付きなら従来どおり統計を返す。"""
    from tools.sr_audit import stage_a_audit

    events = ([_row(reversal=True) for _ in range(60)]
              + [_row(reversal=False) for _ in range(40)])
    out = stage_a_audit(events)
    assert out["n"] == 100
    assert out["wins"] == 60
    assert out["wr"] == 60.0
    assert "blocked_reason" not in out


# --------------------------------------------------------------------------
# PR #272 レビュー指摘 3 件の回帰 pin
# 教訓: 片側 (primary) だけ fail-closed にして **対称な反対側 (benchmark) を
# 自分で確認しなかった** — 2026-09-18 に自分で書いた
# 「レビューが片側の穴を指摘したら対称な反対側を自分で確認する」の再発。
# --------------------------------------------------------------------------

def test_load_rows_accepts_the_event_wrapper_object(tmp_path):
    """旧 sr_audit CLI が受けていた `{"events": [...]}` を落とさない。"""
    p = tmp_path / "wrapped.json"
    p.write_text(json.dumps({"events": [_row(), _row(entry_price=150.5)]}),
                 encoding="utf-8")
    assert len(hed.load_rows(p)) == 2


def test_load_rows_accepts_a_pretty_printed_wrapper(tmp_path):
    """整形済み wrapper は 1 行目が部分 JSON なので JSONL 解釈では落ちる。"""
    p = tmp_path / "wrapped_pretty.json"
    p.write_text(json.dumps({"events": [_row()]}, indent=2), encoding="utf-8")
    assert len(hed.load_rows(p)) == 1


def test_load_rows_still_reads_a_single_row_jsonl(tmp_path):
    """wrapper 判定が 1 行 JSONL を壊さないこと (fall-through の pin)。"""
    p = tmp_path / "one.jsonl"
    p.write_text(json.dumps(_row()) + "\n", encoding="utf-8")
    assert len(hed.load_rows(p)) == 1


def test_load_rows_accepts_a_bare_json_array(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text(json.dumps([_row(), _row(entry_price=151.0)]), encoding="utf-8")
    assert len(hed.load_rows(p)) == 2


def test_stage_a_rejects_unlabeled_benchmark_even_when_primary_is_clean():
    """NG 入力: primary は全ラベル付き、benchmark に未ラベル行。

    未ラベル行は bench_n に数えられ bench_wins から落ちるので baseline 側で
    同じバグが再生し net_edge が過大になる = promotion verdict が変わりうる。
    """
    from tools.sr_audit import stage_a_audit

    primary = ([_row(reversal=True) for _ in range(60)]
               + [_row(reversal=False) for _ in range(40)])
    out = stage_a_audit(primary, benchmark_events=[_row(reversal=True),
                                                  _row(reversal=None)])
    assert out["verdict"] == "data_blocked"
    assert out["unlabeled_in"] == "benchmark_events"


def test_stage_a_accepts_a_fully_labeled_benchmark():
    """反対側: benchmark も全ラベル付きなら net_edge を計算する。"""
    from tools.sr_audit import stage_a_audit

    primary = ([_row(reversal=True) for _ in range(60)]
               + [_row(reversal=False) for _ in range(40)])
    bench = ([_row(reversal=True) for _ in range(30)]
             + [_row(reversal=False) for _ in range(70)])
    out = stage_a_audit(primary, benchmark_events=bench)
    assert "verdict" not in out          # 成功経路に verdict キーは無い
    assert "blocked_reason" not in out
    assert out["benchmark"]["n"] == 100
    assert out["benchmark"]["net_edge_pp"] == 30.0


def test_stage_a_reports_which_population_was_unlabeled():
    from tools.sr_audit import stage_a_audit

    out = stage_a_audit([_row(reversal=None)], benchmark_events=None)
    assert out["unlabeled_in"] == "events"


# --------------------------------------------------------------------------
# PR #272 レビュー 2 巡目 — 「対称にする」を 1 段取り違えていた
# ラベル検査と独立観測の単位は両母集団で対称。**provenance 規約は母集団ごとに違う。**
# --------------------------------------------------------------------------

def test_benchmark_prepare_does_not_enforce_hunt_provenance(tmp_path):
    """NG 入力: repo 慣行の `USD_JPY` 表記のラベル完備 baseline。

    D2 を課すと全行隔離されて exit 5 になる (hunt logger 由来とは限らない
    別母集団に logger 固有の規約を課していた)。
    """
    _write(tmp_path, [_row(instrument="USD_JPY", entry_price=150 + i * 0.01,
                           reversal=(i % 3 == 0)) for i in range(40)])
    strict = hed.prepare(tmp_path)
    assert strict["ok"] is False
    assert strict["accounting"]["quarantined_provenance"] == 40

    bench = hed.prepare(tmp_path, enforce_provenance=False)
    assert bench["ok"] is True
    assert bench["accounting"]["quarantined_provenance"] == 0
    assert len(bench["events"]) == 40


def test_benchmark_prepare_still_enforces_labels_and_dedup(tmp_path):
    """provenance を外してもラベル検査と dedup は外れないこと。"""
    _write(tmp_path, [_row(instrument="USD_JPY") for _ in range(200)])
    out = hed.prepare(tmp_path, enforce_provenance=False)
    assert out["ok"] is False                       # 全行未ラベル
    assert out["accounting"]["distinct_observations"] == 1   # dedup は効いている


def test_benchmark_prepare_still_filters_pair_and_side(tmp_path):
    _write(tmp_path, [_row(instrument="USD_JPY", side="support",
                           entry_price=150 + i * 0.01, reversal=True)
                      for i in range(40)]
           + [_row(instrument="EUR_JPY", side="resistance",
                   entry_price=160 + i * 0.01, reversal=True) for i in range(40)])
    out = hed.prepare(tmp_path, pair="USD_JPY", side="bull",
                      enforce_provenance=False)
    assert out["ok"] is True
    assert len(out["events"]) == 40


def test_accounting_records_whether_provenance_was_enforced(tmp_path):
    _write(tmp_path, [_row()])
    assert hed.prepare(tmp_path)["accounting"]["enforce_provenance"] is True
    assert hed.prepare(tmp_path, enforce_provenance=False)[
        "accounting"]["enforce_provenance"] is False


# --------------------------------------------------------------------------
# PR #272 レビュー 3 巡目 — dedup が「意味を持ち始める日」に静かに壊れる形だった
# --------------------------------------------------------------------------

def test_d3_collapses_repeats_even_after_labels_are_attached():
    """NG 入力: labeler が反復発火の 1 本だけにラベルを付けた状態。

    outcome 列が identity に残っていると、この入力で collapse が止まり
    **validity gate が通り始めるのと同じタイミングで** N 膨張が復活する。
    """
    rows = [_row(entry_time=f"2026-09-01T00:0{i}:00+00:00") for i in range(5)]
    rows[2]["reversal"] = True
    rows[2]["actual_outcome"] = "WIN"
    rows[2]["actual_pnl_pips"] = 18.0

    deduped, repeats, conflicts = hed.collapse_repeats(rows)
    assert len(deduped) == 1, "outcome 列が identity に残っている"
    assert repeats == 4
    assert conflicts == []
    # 代表は未ラベル行だが、グループ内のラベルを引き継ぐ (観測を捨てない)
    assert deduped[0]["reversal"] is True
    assert deduped[0]["actual_outcome"] == "WIN"
    assert deduped[0]["actual_pnl_pips"] == 18.0
    assert deduped[0]["entry_time"] == "2026-09-01T00:00:00+00:00"


def test_d3_conflicting_outcomes_on_one_signal_are_loud():
    """NG 入力: 同一 signal に 2 通りの結果 = labeler のバグ。黙って片方を採らない。"""
    rows = [_row(entry_time="2026-09-01T00:00:00+00:00", reversal=True,
                 actual_outcome="WIN", actual_pnl_pips=18.0),
            _row(entry_time="2026-09-01T00:01:00+00:00", reversal=False,
                 actual_outcome="LOSS", actual_pnl_pips=-9.0)]
    deduped, repeats, conflicts = hed.collapse_repeats(rows)
    assert len(deduped) == 1
    assert len(conflicts) == 1
    assert conflicts[0]["n_rows"] == 2


def test_prepare_blocks_on_outcome_conflicts(tmp_path):
    rows = []
    for i in range(40):
        rows.append(_row(entry_price=150 + i * 0.01, reversal=True,
                         actual_outcome="WIN", actual_pnl_pips=10.0))
        rows.append(_row(entry_price=150 + i * 0.01,
                         entry_time="2026-09-01T01:00:00+00:00", reversal=False,
                         actual_outcome="LOSS", actual_pnl_pips=-5.0))
    _write(tmp_path, rows)
    out = hed.prepare(tmp_path)
    assert out["ok"] is False
    assert out["accounting"]["outcome_conflicts"] == 40
    assert any("conflicting outcomes" in r for r in out["blocked_reasons"])


def test_labeled_duplicates_do_not_inflate_n_after_dedup(tmp_path):
    """反対側: ラベル付きの重複を含む入力でも N は distinct signal 数になる。"""
    rows = []
    for i in range(40):
        for rep in range(3):                     # 同一 bar 内で 3 回再評価
            r = _row(entry_price=150 + i * 0.01,
                     entry_time=f"2026-09-01T00:{rep * 5:02d}:00+00:00")
            if rep == 1:                         # うち 1 本にだけラベル
                r.update(reversal=(i % 2 == 0), actual_outcome="WIN",
                         actual_pnl_pips=5.0)
            rows.append(r)
    _write(tmp_path, rows)
    out = hed.prepare(tmp_path)
    assert out["accounting"]["rows_read"] == 120
    assert out["accounting"]["distinct_observations"] == 40
    assert out["accounting"]["outcome_conflicts"] == 0
    assert out["ok"] is True
    assert len(out["events"]) == 40             # 120 ではない


# --------------------------------------------------------------------------
# PR #272 レビュー 4 巡目 — `entry_time` の意味が母集団で違う (同じ根の 3 例目)
#   hunt_events: entry_time = 書込み時刻  → "signal" 粒度で除外
#   benchmark:   entry_time = bar identity → "bar" 粒度で保持
# --------------------------------------------------------------------------

def test_bar_dedup_keeps_distinct_benchmark_bars():
    """NG 入力: 1 bar 1 行の baseline で entry_time と reversal だけが違う 40 行。

    "signal" 粒度を当てると全行が 1 群に潰れ、偽の outcome 衝突が出て
    N が床を割る (= exit 5)。"bar" 粒度なら 40 観測が保たれる。
    """
    # 同一窓 (1h) 内の 15m bar 4 本。payload は同一で entry_time と reversal だけが違う。
    rows = [_row(entry_time=f"2026-09-01T00:{m:02d}:00+00:00", reversal=(m % 30 == 0))
            for m in (0, 15, 30, 45)]

    signal_out, signal_repeats, signal_conflicts = hed.collapse_repeats(rows)
    assert len(signal_out) == 1                       # 潰れてしまう
    assert signal_repeats == 3
    assert len(signal_conflicts) == 1                 # 偽の衝突

    bar_out, bar_repeats, bar_conflicts = hed.collapse_repeats(rows, dedup="bar")
    assert len(bar_out) == 4
    assert bar_repeats == 0
    assert bar_conflicts == []


def test_bar_dedup_still_collapses_true_duplicates_of_one_bar():
    """反対側: 同一 bar が 2 度書かれたら "bar" 粒度でも潰れる。"""
    rows = [_row(entry_time="2026-09-01T00:00:00+00:00", reversal=True),
            _row(entry_time="2026-09-01T00:00:00+00:00", reversal=True)]
    out, repeats, conflicts = hed.collapse_repeats(rows, dedup="bar")
    assert len(out) == 1
    assert repeats == 1
    assert conflicts == []


def test_bar_dedup_still_flags_conflicts_within_one_bar():
    rows = [_row(entry_time="2026-09-01T00:00:00+00:00", reversal=True,
                 actual_outcome="WIN"),
            _row(entry_time="2026-09-01T00:00:00+00:00", reversal=False,
                 actual_outcome="LOSS")]
    _, _, conflicts = hed.collapse_repeats(rows, dedup="bar")
    assert len(conflicts) == 1


def test_benchmark_prepare_passes_with_bar_dedup(tmp_path):
    """documented benchmark 契約 (1 bar 1 行) が exit 5 にならないこと。"""
    # NB: hours must be VALID.  This fixture used to emit
    # `2026-09-01T24:00:00` .. `T39:00:00` for h >= 24, i.e. 16 unparseable
    # timestamps that `prepare()` silently admitted as 16 independent
    # observations — the very inflation Codex flagged (P2, PR #272 第11巡),
    # live inside this test's own data.  Roll over into the next day instead.
    _write(tmp_path, [_row(instrument="USD_JPY", reversal=(h % 3 == 0),
                           entry_time=(f"2026-09-{1 + h // 24:02d}"
                                       f"T{h % 24:02d}:00:00+00:00"))
                      for h in range(40)])
    strict = hed.prepare(tmp_path, enforce_provenance=False)      # "signal" 既定
    assert strict["ok"] is False                                  # 潰れて床割れ

    bench = hed.prepare(tmp_path, enforce_provenance=False, dedup="bar")
    assert bench["ok"] is True
    assert len(bench["events"]) == 40
    assert bench["accounting"]["dedup"] == "bar"
    assert bench["accounting"]["outcome_conflicts"] == 0


def test_unknown_dedup_mode_is_loud():
    with pytest.raises(ValueError, match="unknown dedup mode"):
        hed.identity(_row(), dedup="bogus")


def test_dedup_modes_are_pinned():
    """粒度の追加/変更は estimand の変更なので pin する。"""
    assert set(hed.DEDUP_MODES) == {"signal", "bar"}
    assert hed.DEDUP_MODES["signal"] == hed.IDENTITY_EXCLUDE
    assert hed.DEDUP_MODES["bar"] == frozenset(hed.OUTCOME_FIELDS)
    assert "entry_time" in hed.DEDUP_MODES["signal"]
    assert "entry_time" not in hed.DEDUP_MODES["bar"]


# --------------------------------------------------------------------------
# PR #272 レビュー 5 巡目 — 衝突判定が広すぎた 2 形
# --------------------------------------------------------------------------

def test_partial_outcome_labels_merge_instead_of_conflicting():
    """NG 入力: (True, None, None) と (True, "WIN", 10.0)。

    logger は 3 列を独立に初期化し、反復発火のうち実約定に対応するのは
    1 本だけ — 部分帰属は正常状態であって衝突ではない。
    """
    rows = [_row(entry_time="2026-09-01T00:00:00+00:00", reversal=True),
            _row(entry_time="2026-09-01T00:01:00+00:00", reversal=True,
                 actual_outcome="WIN", actual_pnl_pips=10.0)]
    out, repeats, conflicts = hed.collapse_repeats(rows)
    assert conflicts == []
    assert len(out) == 1
    assert out[0]["reversal"] is True
    assert out[0]["actual_outcome"] == "WIN"
    assert out[0]["actual_pnl_pips"] == 10.0


def test_disagreeing_values_in_one_field_still_conflict():
    """反対側: 同一フィールドに相異なる非 None 値 → 衝突。"""
    rows = [_row(entry_time="2026-09-01T00:00:00+00:00", actual_pnl_pips=10.0),
            _row(entry_time="2026-09-01T00:01:00+00:00", actual_pnl_pips=-5.0)]
    _, _, conflicts = hed.collapse_repeats(rows)
    assert len(conflicts) == 1
    assert set(conflicts[0]["fields"]) == {"actual_pnl_pips"}


def test_merge_outcomes_reports_the_disagreeing_field_only():
    group = [_row(reversal=True, actual_outcome="WIN", actual_pnl_pips=10.0),
             _row(reversal=True, actual_outcome="LOSS", actual_pnl_pips=10.0)]
    merged, disagreements = hed.merge_outcomes(group)
    assert set(disagreements) == {"actual_outcome"}
    assert merged["reversal"] is True
    assert merged["actual_pnl_pips"] == 10.0


def test_conflict_in_another_cell_does_not_block_this_cell(tmp_path):
    """NG 入力: 別ペアの衝突 1 件で、clean な要求セルが DATA-BLOCKED になる。"""
    rows = [_row(instrument="USDJPY=X", side="support", reversal=True,
                 entry_price=150 + i * 0.01) for i in range(40)]
    rows += [_row(instrument="EURJPY=X", side="support", entry_price=160.0,
                  entry_time="2026-09-01T00:00:00+00:00", actual_pnl_pips=10.0),
             _row(instrument="EURJPY=X", side="support", entry_price=160.0,
                  entry_time="2026-09-01T00:01:00+00:00", actual_pnl_pips=-5.0)]
    _write(tmp_path, rows)

    cell = hed.prepare(tmp_path, pair="USD_JPY", side="bull")
    assert cell["accounting"]["outcome_conflicts"] == 0
    assert cell["accounting"]["outcome_conflicts_all_cells"] == 1
    assert cell["ok"] is True, cell["blocked_reasons"]
    assert len(cell["events"]) == 40


def test_conflict_inside_the_requested_cell_does_block(tmp_path):
    """反対側: 要求セル内の衝突はちゃんと止める。"""
    rows = [_row(instrument="USDJPY=X", side="support", reversal=True,
                 entry_price=150 + i * 0.01) for i in range(40)]
    rows += [_row(instrument="USDJPY=X", side="support", entry_price=149.0,
                  entry_time="2026-09-01T00:00:00+00:00", actual_pnl_pips=10.0),
             _row(instrument="USDJPY=X", side="support", entry_price=149.0,
                  entry_time="2026-09-01T00:01:00+00:00", actual_pnl_pips=-5.0)]
    _write(tmp_path, rows)

    cell = hed.prepare(tmp_path, pair="USD_JPY", side="bull")
    assert cell["accounting"]["outcome_conflicts"] == 1
    assert cell["ok"] is False
    assert any("conflicting outcomes" in r for r in cell["blocked_reasons"])


# --------------------------------------------------------------------------
# PR #272 レビュー 6 巡目 — "signal" 粒度は時間窓が無いと全期間で潰れる
# --------------------------------------------------------------------------

def test_signal_dedup_does_not_merge_across_the_window():
    """NG 入力: 同一 payload が窓を跨いで出る (実データに 68.5 日の群が存在)。"""
    rows = [_row(entry_time="2026-05-01T00:00:00+00:00"),
            _row(entry_time="2026-07-08T00:00:00+00:00")]
    out, repeats, conflicts = hed.collapse_repeats(rows)
    assert len(out) == 2, "窓外の同一 payload を別観測として残していない"
    assert repeats == 0
    # 無制限なら潰れる = 修正前の挙動
    assert len(hed.collapse_repeats(rows, window_sec=None)[0]) == 1


def test_signal_dedup_still_collapses_within_the_window():
    rows = [_row(entry_time=f"2026-09-01T00:{m:02d}:00+00:00") for m in (0, 20, 50)]
    out, repeats, _ = hed.collapse_repeats(rows)
    assert len(out) == 1
    assert repeats == 2


def test_window_boundary_is_anchored_not_chained():
    """anchored: 先頭から window_sec を超えたら新しい観測 (chaining しない)。"""
    rows = [_row(entry_time="2026-09-01T00:00:00+00:00"),
            _row(entry_time="2026-09-01T00:50:00+00:00"),   # 窓内
            _row(entry_time="2026-09-01T01:30:00+00:00")]   # 先頭から 90 分 = 窓外
    out, repeats, _ = hed.collapse_repeats(rows)
    assert len(out) == 2
    assert repeats == 1


def test_rows_without_a_parsable_entry_time_are_never_merged():
    """時刻が読めない行は窓を張れない → 潰さない (観測を消す方向に倒れない)。"""
    rows = [_row(entry_time="not-a-timestamp"), _row(entry_time="not-a-timestamp")]
    out, repeats, _ = hed.collapse_repeats(rows)
    assert len(out) == 2
    assert repeats == 0


def test_dedup_window_default_is_pinned():
    """窓を緩める (= 潰しすぎる) 方向の変更を pin する。"""
    assert hed.DEDUP_WINDOW_SEC == 3600.0


def test_documented_window_table_agrees_with_the_readout():
    """The module's sensitivity table must not drift from the readout.

    The table was computed with the CHAINED window implementation and never
    recomputed when round 5 switched to anchored windows, so the shipped
    comment described a different estimator than the shipped code (Codex P2,
    PR #272).  `test_window_boundary_is_anchored_not_chained` pins the
    estimator; nothing pinned the NUMBERS against the readout and registry
    that cite them.

    Both sides are static text, so this pin is stable as the dataset grows —
    it checks mutual consistency, not a live recomputation.
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent
    tool = (root / "tools" / "hunt_event_dataset.py").read_text(encoding="utf-8")
    readout = (root / "knowledge-base" / "wiki" / "analyses"
               / "hunt-events-dataset-readout-2026-09-19.md").read_text(
                   encoding="utf-8")

    # The readout states the inflation factor as basis / distinct_1h.
    mr = re.search(r"膨張係数 = ([\d,]+) / ([\d,]+) = ([\d.]+) 倍", readout)
    assert mr, "the readout must state 膨張係数 = <basis> / <1h distinct>"
    basis_doc, distinct_doc = mr.group(1), mr.group(2)

    mt = re.search(r"1h → ([\d,]+) \(([\d.]+)x\)", tool)
    assert mt, "the module table must state the 1h distinct count"
    assert mt.group(1) == distinct_doc, (
        f"the module's 1h distinct ({mt.group(1)}) disagrees with the readout "
        f"({distinct_doc}) — recompute the table whenever the estimator or "
        f"the basis changes")

    assert f"{basis_doc} 行" in tool, (
        f"the module table must name the same basis as the readout "
        f"({basis_doc} rows), so a reader can tell which population it is")

    # The stated inflation must be the arithmetic of the two stated counts,
    # not a remembered number.
    got = int(basis_doc.replace(",", "")) / int(distinct_doc.replace(",", ""))
    assert abs(got - float(mt.group(2))) < 0.01, (
        f"{basis_doc}/{distinct_doc} = {got:.2f}x, table says {mt.group(2)}x")

    # The D3 CONTRACT paragraph carries the same numbers and drifted
    # independently of the table below it — the table was corrected in 第7巡
    # while the contract still quoted a pre-round-3 estimator (Codex P2,
    # PR #272 第10巡).  That paragraph is what defines the frozen observation
    # unit, so a reader citing it cites an effective N.  Pin them TOGETHER.
    mc = re.search(r"\*\*既定 1h\*\*: collapse \*\*([\d,]+) 行 \(([\d.]+)%\)\*\* "
                   r"→ 相異なる観測 \*\*([\d,]+)\*\*\s*\n?\s*= \*\*([\d.]+) 倍\*\*",
                   tool)
    assert mc, "the D3 contract must state collapse / distinct / inflation for 1h"
    collapsed_c, pct_c, distinct_c, infl_c = mc.groups()
    assert distinct_c == distinct_doc, (
        f"the D3 contract's 1h distinct ({distinct_c}) disagrees with the "
        f"sensitivity table and the readout ({distinct_doc})")
    basis_n = int(basis_doc.replace(",", ""))
    assert int(collapsed_c.replace(",", "")) == basis_n - int(
        distinct_c.replace(",", "")), (
        f"collapse must be basis - distinct: {basis_doc} - {distinct_c} "
        f"!= {collapsed_c}")
    assert abs(int(collapsed_c.replace(",", "")) / basis_n * 100
               - float(pct_c)) < 0.1, (
        f"{collapsed_c}/{basis_doc} is not {pct_c}%")
    assert abs(basis_n / int(distinct_c.replace(",", ""))
               - float(infl_c)) < 0.01, (
        f"{basis_doc}/{distinct_c} is not {infl_c}x")

    # The LOGGER docstring is the third live reader-facing surface carrying
    # this count, and it drifted too (Codex P2, PR #272 第11巡).  Every surface
    # that instructs a reader is pinned; the changelog / session logs are
    # HISTORICAL records of the corrections and are deliberately NOT pinned.
    logger = (root / "modules" / "hunt_event_logger.py").read_text(
        encoding="utf-8")
    ml = re.search(r"([\d,]+) distinct observations under the default 1h "
                   r"dedup window", logger)
    assert ml, "the logger must state the default-window observation count"
    assert ml.group(1) == distinct_doc, (
        f"the logger's distinct count ({ml.group(1)}) disagrees with the "
        f"reader contract and the readout ({distinct_doc}) — a reader "
        f"following its instruction would cite a withdrawn effective N")
    assert f"{basis_doc} provenance-filtered" in logger, (
        "the logger must name the basis too, not just the count")


def test_anchored_window_is_independent_of_input_order():
    """KNOWN-NG INPUT: identical payloads delivered newest-first.

    An anchored window compares `(ts - anchor)`, so an OLDER row arriving
    later yields a negative delta and always joins the current window — two
    observations 24h apart collapsed into one if ordered Jan 2 then Jan 1.
    `load_rows()` preserves input order, and the committed dataset really is
    partly out of order (205 of 9,946 identities, 429 inversions), so this
    silently undercounted N (Codex P2, PR #272).
    """
    from tools.hunt_event_dataset import collapse_repeats

    def row(ts):
        return {"instrument": "USDJPY=X", "side": "support", "level": 150.0,
                "entry_time": ts}

    early, late = row("2026-01-01T00:00:00"), row("2026-01-02T00:00:00")

    kept_fwd, rep_fwd, _ = collapse_repeats([early, late], window_sec=3600.0)
    kept_rev, rep_rev, _ = collapse_repeats([late, early], window_sec=3600.0)

    assert len(kept_fwd) == 2, "24h apart must be two observations"
    assert len(kept_rev) == 2, (
        "reversing the input must not merge two observations 24h apart — "
        "the anchored window has to be applied in chronological order")
    assert rep_fwd == rep_rev == 0

    # The representative is the CHRONOLOGICALLY earliest either way, which is
    # what the docstring promises.
    assert kept_rev[0]["entry_time"] == "2026-01-01T00:00:00"

    # Counter-pin: genuinely inside one window still collapses, in both
    # orders — the fix is ordering, not "never collapse".
    a, b = row("2026-01-01T00:00:00"), row("2026-01-01T00:10:00")
    for pair in ([a, b], [b, a]):
        kept, rep, _ = collapse_repeats(pair, window_sec=3600.0)
        assert len(kept) == 1 and rep == 1, (
            "two evaluations 10 minutes apart are one observation at a 1h "
            f"window regardless of arrival order (got {len(kept)})")

    # Unbounded mode has no anchor, so it is order-independent by construction.
    assert len(collapse_repeats([late, early], window_sec=None)[0]) == 1


def test_mixed_aware_and_naive_timestamps_do_not_abort_the_audit():
    """KNOWN-NG INPUT: one event written with an explicit UTC offset.

    Both the per-identity sort and the window arithmetic subtract these
    values, and Python refuses to compare offset-naive with offset-aware
    datetimes — so a single differently formatted row raised TypeError and
    aborted the entire audit (Codex P2, PR #272 第9巡).
    """
    from tools.hunt_event_dataset import collapse_repeats, _parse_entry_time

    def row(ts, level=150.0):
        return {"instrument": "USDJPY=X", "side": "support", "level": level,
                "entry_time": ts}

    naive = row("2026-01-01T00:00:00")
    aware = row("2026-01-01T09:00:00+09:00", level=151.0)   # == 00:00Z

    # The parser normalizes, so the two forms are directly comparable...
    assert _parse_entry_time(naive) == _parse_entry_time(aware), (
        "+09:00 09:00 is the same instant as naive 00:00 UTC")
    assert _parse_entry_time(aware).tzinfo is None

    # ...and mixing them in one corpus must not raise.
    kept, _, _ = collapse_repeats([aware, naive], window_sec=3600.0)
    assert len(kept) == 2, "different levels are different observations"

    # Offsets must be honoured, not truncated: +09:00 04:00 is 2026-12-31
    # 19:00Z, i.e. MORE than 1h before naive 2026-01-01T00:00:00, so the two
    # identical payloads stay two observations.
    far = row("2026-01-01T04:00:00+09:00")
    kept2, rep2, _ = collapse_repeats([far, naive], window_sec=3600.0)
    assert len(kept2) == 2 and rep2 == 0, (
        "the offset must be applied before the window, not ignored")

    # Counter-pin: the same instant in the two forms IS one observation.
    same = row("2026-01-01T09:00:00+09:00")
    kept3, rep3, _ = collapse_repeats([same, naive], window_sec=3600.0)
    assert len(kept3) == 1 and rep3 == 1


def test_rows_without_a_usable_timestamp_are_excluded_not_counted(tmp_path):
    """KNOWN-NG INPUT: 30 identical labeled repeats with entry_time="bad".

    `collapse_repeats` keeps an undatable row as its own observation — correct
    inside the collapser (never delete an observation silently) and the WRONG
    direction for a promotion gate: without a parseable timestamp the dedup
    window cannot be applied, so each repeat entered the population as an
    independent event and manufactured significance (Codex P2, PR #272
    第11巡).
    """
    rows = [_row(instrument="USDJPY=X", reversal=True, entry_time="bad")
            for _ in range(30)]
    _write(tmp_path, rows)

    res = hed.prepare(tmp_path)
    assert res["ok"] is False, (
        "30 undatable repeats must NOT satisfy the N floor as 30 events")
    assert any("unparseable" in r for r in res["blocked_reasons"])
    assert res["accounting"]["quarantined_undatable"] == 30
    assert res["events"] == []

    # Counter-pin 1: datable rows are unaffected, and the same 30 repeats with
    # a real timestamp collapse to ONE observation (the actual estimand).
    _write(tmp_path, [_row(instrument="USDJPY=X", reversal=True,
                           entry_time="2026-09-01T00:00:00")
                      for _ in range(30)])
    res2 = hed.prepare(tmp_path)
    assert res2["accounting"]["quarantined_undatable"] == 0
    assert res2["accounting"]["distinct_observations"] == 1

    # Counter-pin 2: with the window disabled there IS no window to enforce,
    # so undatable rows are not quarantined on that ground.
    _write(tmp_path, rows)
    res3 = hed.prepare(tmp_path, window_sec=None)
    assert res3["accounting"]["quarantined_undatable"] == 0


def test_an_undatable_row_in_another_cell_does_not_block_this_one(tmp_path):
    """KNOWN-NG INPUT: one malformed EUR_JPY row beside 30 good USD_JPY ones.

    The exclusion is global (an undatable row cannot be deduped anywhere) but
    the BLOCKING REASON must be scoped to the requested cell, or one bad row
    in a pair that cannot influence the statistics rejects a clean audit —
    the same shape as the 4th-round conflict-scoping defect, recurring on the
    guard added one round earlier (Codex P2, PR #272 第12巡).
    """
    # Distinct `level` per row so these are 30 genuinely distinct identities
    # (identical payloads would collapse into windows and trip the conflict
    # gate instead, which is not what this pin is about).
    good = [_row(instrument="USDJPY=X", side="support", level=150.0 + i,
                 reversal=(i % 3 == 0),
                 entry_time=f"2026-09-{1 + i // 24:02d}T{i % 24:02d}:00:00")
            for i in range(30)]
    bad_other_cell = [_row(instrument="EURJPY=X", side="resistance",
                           reversal=True, entry_time="bad")]
    _write(tmp_path, good + bad_other_cell)

    res = hed.prepare(tmp_path, pair="USD_JPY", side="support")
    assert res["ok"] is True, (
        "a malformed row in another pair/side must not block this cell: "
        f"{res['blocked_reasons']}")
    assert len(res["events"]) == 30
    # Both counts are reported: the global exclusion AND the in-cell zero.
    assert res["accounting"]["quarantined_undatable"] == 1
    assert res["accounting"]["quarantined_undatable_in_cell"] == 0

    # Counter-pin: a malformed row IN this cell still blocks it.
    _write(tmp_path, good + [_row(instrument="USDJPY=X", side="support",
                                  level=999.0, reversal=True,
                                  entry_time="bad")])
    res2 = hed.prepare(tmp_path, pair="USD_JPY", side="support")
    assert res2["ok"] is False
    assert res2["accounting"]["quarantined_undatable_in_cell"] == 1
    assert any("in this cell" in r for r in res2["blocked_reasons"])
