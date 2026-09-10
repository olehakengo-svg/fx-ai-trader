"""tools/rnb_shadow_demote_gate.py の counterfactual テスト。

packet: knowledge-base/wiki/decisions/rnb-support-bounce-r1-packet-2026-09-10.md
(§5 stage-1 R2 gate: shadow N>=30 dedup_violation=0 ∧ Wilson_hi < 42.9%
→ auto_start=False の R2 起案。rule:R1 user 承認 2026-09-10)

設計方針 (counterfactual 必須 — 「guard を触ったら counterfactual で落ちる
ことを確認」「検知器も write-only になりうる — 読み手が呼ばれているかまで
pin」):
  - 発火すべき合成データで **実際に発火する** ことを検査する (green のまま
    何も検知しない write-only 検知器を作らない)
  - 境界の反対側 (N=29 / Wilson_hi >= 境界) では発火しないことを検査する
  - 母集団フィルタの各除外条件が **1 行の汚染でも判定を変えうる** 形で
    効いていることを検査する
  - 読み手 (r2-alert-scheduled.yml) がツールを実際に呼んでいることを pin
"""
from __future__ import annotations

import importlib.util
import os

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOL_PATH = os.path.join(_ROOT, "tools", "rnb_shadow_demote_gate.py")
_WORKFLOW_PATH = os.path.join(_ROOT, ".github", "workflows",
                              "r2-alert-scheduled.yml")


def _load_tool():
    spec = importlib.util.spec_from_file_location("rnb_shadow_demote_gate",
                                                  _TOOL_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def tool():
    return _load_tool()


def _row(tool, pnl: float, **over) -> dict:
    base = {
        "entry_type": tool.ENTRY_TYPE,
        "instrument": tool.INSTRUMENT,
        "direction": tool.DIRECTION,
        "status": "CLOSED",
        "is_shadow": 1,
        "oanda_trade_id": "",
        "dedup_violation": 0,
        "pnl_pips": pnl,
    }
    base.update(over)
    return base


def _bad_30(tool):
    """N=30, wins=6 (WR20%) — Wilson_hi ≈ 0.373 < 0.429 = 発火母集団。"""
    return ([_row(tool, 1.0) for _ in range(6)]
            + [_row(tool, -1.0) for _ in range(24)])


# ── 凍結パラメータ pin (packet §5/§6 — 変更は LOCK 改定 = user 決裁) ──────


def test_gate_parameters_match_packet(tool):
    assert tool.ENTRY_TYPE == "rnb_support_bounce"
    assert tool.MODE == "rnb_usdjpy"
    assert tool.INSTRUMENT == "USD_JPY"
    assert tool.DIRECTION == "BUY"
    assert tool.SINCE == "2026-09-10"      # LOCK forward 母集団起点
    assert tool.N_MIN == 30                # packet §5 stage-1 gate
    assert tool.WILSON_HI_REJECT == 0.429  # gross BEV 棄却境界


# ── counterfactual: 発火すべきデータで発火する ─────────────────────────


def test_gate_fires_on_rejection_boundary(tool):
    res = tool.run(_bad_30(tool))
    assert res["state"] == "DEMOTE_PROPOSED", res
    assert res["n"] == 30 and res["wins"] == 6
    assert res["wilson_hi"] < 0.429
    assert "auto_start=False" in res["detail"]


def test_gate_exit_code_is_1_on_trigger(tool, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv",
                        ["rnb_shadow_demote_gate", "--json",
                         "--no-report", "--no-discord"])
    rc = tool.cli(fetcher=lambda _api: _bad_30(tool))
    assert rc == 1, capsys.readouterr().out


# ── 境界の反対側では発火しない ────────────────────────────────────────


def test_gate_watches_below_n_min(tool):
    res = tool.run(_bad_30(tool)[:29])
    assert res["state"] == "WATCHING", res


def test_gate_does_not_fire_when_wilson_hi_clears_bev(tool):
    ok = ([_row(tool, 1.0) for _ in range(12)]
          + [_row(tool, -1.0) for _ in range(18)])  # WR40%, hi≈0.577
    res = tool.run(ok)
    assert res["state"] == "PASS_WATCH", res
    assert res["wilson_hi"] >= 0.429


def test_rejection_is_strict_less_than(tool):
    """境界は「未満」— ちょうど境界値では発火しない (decide_gate 純関数)。"""
    hi = tool.wilson_hi(6, 30)
    res = tool.decide_gate(30, 6, wilson_hi_reject=hi)
    assert res["state"] == "PASS_WATCH", res


# ── 母集団フィルタ: 1 行の汚染が判定を変えうる形で counterfactual ─────────


def test_dedup_rows_cannot_reach_n_min(tool):
    """dedup_violation=1 の重複行で N>=30 に到達させない (幻の N 到達防止)。
    counterfactual: 除外を外せば N=30 で発火してしまうデータ構成。"""
    rows = _bad_30(tool)[:29] + [_row(tool, -1.0, dedup_violation=1)]
    res = tool.run(rows)
    assert res["state"] == "WATCHING", res
    assert res["n"] == 29
    assert res["excluded"]["dedup_violation"] == 1


def test_live_fill_rows_are_excluded_as_ambiguous(tool):
    """厳格 shadow 分離: is_shadow=1 でも oanda_trade_id を持つ行は
    ambiguous として除外・計数 (Live vs Shadow 恒久指示 + shadow_only
    構造保証の破れ検知)。"""
    rows = _bad_30(tool)[:29] + [_row(tool, -1.0, oanda_trade_id="OANDA-1")]
    res = tool.run(rows)
    assert res["n"] == 29
    assert res["excluded"]["ambiguous_shadow_with_fill"] == 1


def test_open_and_foreign_rows_are_excluded(tool):
    rows = _bad_30(tool) + [
        _row(tool, -1.0, status="OPEN"),
        _row(tool, -1.0, entry_type="bb_rsi_reversion"),
        _row(tool, -1.0, instrument="EUR_USD"),
        _row(tool, -1.0, direction="SELL"),
        _row(tool, -1.0, is_shadow=0),
        _row(tool, None),
    ]
    res = tool.run(rows)
    assert res["n"] == 30, res
    exc = res["excluded"]
    assert exc["not_closed"] == 1
    assert exc["other_entry_type"] == 1
    assert exc["other_instrument"] == 1
    assert exc["other_direction"] == 1
    assert exc["not_shadow"] == 1
    assert exc["pnl_missing"] == 1


# ── P-10 境界: 採用側 estimand を出力しない ───────────────────────────


def test_output_carries_no_adoption_estimand(tool):
    """LOCK first look まで Wilson_lo / net EV は計算・出力しない (P-10)。
    棄却境界の評価に必要な n / wins / wilson_hi のみ。"""
    res = tool.run(_bad_30(tool))
    assert "wilson_lo" not in res
    assert "ev" not in res
    assert not any("wilson_lo" in k or k == "ev" for k in res), sorted(res)


# ── 読み手の配線 pin (write-only 検知器の再発防止) ────────────────────


def test_gate_is_wired_into_scheduled_reader():
    """r2-alert-scheduled.yml が本ツールを実際に呼んでいることを pin。
    検知器は読み手が呼んで初めて検知器になる (engine_tick_liveness 教訓)。"""
    with open(_WORKFLOW_PATH, encoding="utf-8") as f:
        wf = f.read()
    assert "tools/rnb_shadow_demote_gate.py" in wf, (
        "R2 gate が scheduled workflow から呼ばれていない — "
        "write-only 検知器になっている")


def test_smoke_fixture_passes(tool):
    assert tool._smoke_test() == 0
