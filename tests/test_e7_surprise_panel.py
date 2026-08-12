"""E7 phase-1 サプライズパネルの test pin (pre-reg §6/§3.3b/§3.4 の機械化)。

pin の目的:
  1. 単位規約 (§3.3b-5) と欠損の扱いを固定する
  2. σ_trailing が **strictly trailing** (当該 release を含まない・未来を見ない) こと
     — look-ahead canary。ここが壊れると z が事後情報で汚染される
  3. block ゲート (§5b(iii) 40 / §5c B(d) 15) の判定ロジックを固定する
  4. 2026-08-12 pre-flight で実測した block 数を回帰 pin する (データ drift 検知)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "tools"))

import e7_surprise_panel as e7  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_parse_value_units():
    assert e7.parse_value("196K", "K") == 196.0
    assert e7.parse_value("-3K", "K") == -3.0
    assert e7.parse_value("1,024K", "K") == 1024.0
    assert e7.parse_value("0.3%", "%") == 0.3
    assert e7.parse_value("-0.1%", "%") == -0.1
    assert e7.parse_value("", "K") is None
    assert e7.parse_value(None, "%") is None
    with pytest.raises(ValueError):
        e7.parse_value("196", "K")          # 単位記号なしは較正で弾く
    with pytest.raises(ValueError):
        e7.parse_value("0.3%", "K")


def test_trailing_sigma_warmup_and_window():
    assert e7.trailing_sigma([1.0] * 23) is None          # 24 件未満 = warm-up
    assert e7.trailing_sigma([0.0] * 24) is None          # SD=0 は使えない
    # 直近 24 件のみを使う: 古い巨大値は σ に効かない
    prior = [1000.0] + [0.0, 1.0] * 12
    assert e7.trailing_sigma(prior) == pytest.approx(
        e7.trailing_sigma([0.0, 1.0] * 12))


def _synthetic(series="NFP", surprises=None):
    """forecast=0 固定で actual=surprise となる合成イベント列。"""
    evs = []
    for i, s in enumerate(surprises):
        evs.append({"event_time": "20%02d-01-01T13:30:00Z" % (14 + i),
                    "forecast": 0.0, "actual": s})
    return {series: evs}


def test_z_is_strictly_trailing_and_excludes_self():
    # 24 件の warm-up (交互 0/1 → SD 既知) + 25 件目
    surprises = [0.0, 1.0] * 12 + [10.0]
    rows = e7.build_panel(_synthetic(surprises=surprises))
    assert [r["z"] for r in rows[:24]] == [None] * 24
    assert all(r["exclude_reason"] == "warmup_lt_24_prior" for r in rows[:24])
    last = rows[24]
    sigma_expected = e7.trailing_sigma([0.0, 1.0] * 12)
    assert last["sigma_trailing"] == pytest.approx(sigma_expected)
    # 当該 release 自身 (10.0) が σ に混ざっていないこと
    assert last["z"] == pytest.approx(10.0 / sigma_expected)


def test_look_ahead_canary_future_surprise_does_not_change_z():
    """未来の release を差し替えても過去の z は不変 (look-ahead 注入 canary)。"""
    base = [0.0, 1.0] * 12 + [10.0, 2.0]
    injected = [0.0, 1.0] * 12 + [10.0, 9999.0]
    z_base = [r["z"] for r in e7.build_panel(_synthetic(surprises=base))]
    z_inj = [r["z"] for r in e7.build_panel(_synthetic(surprises=injected))]
    assert z_base[:25] == z_inj[:25]
    assert z_base[25] != z_inj[25]      # 差し替えた当該行だけが動く


def test_missing_forecast_or_actual_is_excluded_not_imputed():
    evs = {"CPI": [{"event_time": "2025-12-18T13:30:00Z",
                    "forecast": None, "actual": 0.3},
                   {"event_time": "2025-12-19T13:30:00Z",
                    "forecast": 0.2, "actual": None}]}
    rows = e7.build_panel(evs)
    assert [r["exclude_reason"] for r in rows] == ["missing_forecast",
                                                   "missing_actual"]
    assert all(r["surprise"] is None and r["z"] is None for r in rows)


def test_coverage_block_gates():
    # z が 24 件 warm-up 後に生成される合成列で gate ロジックを確認
    rows = e7.build_panel(_synthetic(surprises=[0.0, 1.0] * 12 + [10.0]))
    for r in rows:
        r["event_time_utc"] = "2020-06-01T13:30:00Z"     # discovery 窓へ寄せる
    cov = e7.coverage(rows)
    entry = cov["NFP/discovery"]["by_theta"]["0.5"]
    assert entry["blocks"] == 1
    assert entry["block_gate"] == e7.DISCOVERY_BLOCK_GATE == 40
    assert entry["gate_pass"] is False
    assert entry["n_pooled_est"] == 1 * e7.PRIMARY_PAIRS
    assert e7.OOS_BLOCK_GATE == 15


def test_preflight_coverage_regression_pin():
    """2026-08-12 pre-flight の実測値 pin。凍結 artifact が drift したら落ちる。

    θ=1.0 は discovery (40) / OOS (15) の両ゲートに構造的に届かない = 12 combo が
    事前に脱落する、が phase-1 の中核的 power 事実。
    """
    events, prov = e7.load_inputs(_ROOT)
    cov = e7.coverage(e7.build_panel(events))
    expected = {
        "NFP/discovery": {"0.5": 41, "1.0": 22},
        "CPI/discovery": {"0.5": 62, "1.0": 31},
        "NFP/oos": {"0.5": 19, "1.0": 8},
        "CPI/oos": {"0.5": 16, "1.0": 5},
    }
    for key, by_th in expected.items():
        for th, blocks in by_th.items():
            assert cov[key]["by_theta"][th]["blocks"] == blocks, key + "/" + th
    # θ=1.0 は全 4 セルで gate 落ち / θ=0.5 は全 4 セルで gate 通過
    for key in expected:
        assert cov[key]["by_theta"]["1.0"]["gate_pass"] is False
        assert cov[key]["by_theta"]["0.5"]["gate_pass"] is True
    # actual の来歴 (§3.3b-4): R4F 231 + BLS first print 66、欠落ゼロ
    assert prov == {"r4f_actual": 231, "bls_actual": 66, "no_actual": 0,
                    "no_r4f_row": 1}
