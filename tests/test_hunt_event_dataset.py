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
    deduped, repeats = hed.collapse_repeats(rows)
    assert len(deduped) == 1
    assert repeats == 4
    # 代表は最初の書込み時刻
    assert deduped[0]["entry_time"] == "2026-09-01T00:00:00+00:00"


def test_d3_does_not_collapse_genuinely_distinct_signals():
    """誤爆しないこと: market/signal フィールドが違えば別観測。"""
    rows = [_row(), _row(entry_price=150.001), _row(side="resistance")]
    deduped, repeats = hed.collapse_repeats(rows)
    assert len(deduped) == 3
    assert repeats == 0


def test_d3_identity_ignores_only_entry_time():
    a, b = _row(), _row(entry_time="2027-01-01T00:00:00+00:00")
    assert hed.identity(a) == hed.identity(b)
    assert hed.identity(a) != hed.identity(_row(adx=22.6))


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
    """N 膨張が「無視できる程度」ではないことの pin (約 7.0 倍)。"""
    acc = hed.prepare(REAL_DATASET)["accounting"]
    distinct = acc["distinct_observations"]
    collected = distinct + acc["collapsed_repeats"]
    assert collected / distinct > 5.0, f"inflation factor = {collected / distinct:.2f}"


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
