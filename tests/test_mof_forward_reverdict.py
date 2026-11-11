"""mof_forward_reverdict のオフライン pin (network / parquet 不要)。

目的: 再判定 (§5.5 PARTIAL → 1 回限り同一仕様) が 2026-07-24 LOCK 値から漂流していないことを
構造的に固定する。凍結値を変える PR は pre-reg 違反。
"""
import datetime as dt

import pandas as pd
import pytest

from tools import mof_forward_reverdict as R


def test_frozen_params_identical_to_lock():
    # §2.2 / §5.2 / §5.3 / §5.4 凍結値 (2026-07-24 LOCK、tools/mof_forward_verdict.py と同値)
    assert (R.X_FROZEN, R.Y_FROZEN, R.RANGE_MED_LOOKBACK) == (2.0, 0.25, 20)
    assert R.ALPHA == 0.10 and R.S_CAP == 5
    assert R.H_STAR == 10 and R.HORIZONS == (1, 2, 5, 10)
    assert R.PRED_SIGN < 0 and R.BAND == (-319.8, -43.6)
    assert R.ED_K_RANGE == (2, 5) and R.ED_MAX_SINGLE_BN == 3000.0


def test_episode_inputs_pinned_to_primary_sources():
    # 窓 = 月次開示 20260828.html (公表 08-28、D 観測前に KB 記録済み)
    assert R.WIN == (dt.date(2026, 7, 30), dt.date(2026, 8, 26))
    # D = 四半期開示 2026_3Q.html (公表 2026-11-09)、十億円
    assert R.D_DISCLOSED == {dt.date(2026, 7, 30): 7975.6, dt.date(2026, 7, 31): 5552.3,
                             dt.date(2026, 8, 3): 1871.4}
    assert sum(R.D_DISCLOSED.values()) == pytest.approx(15399.3)
    assert (R.D_PAIR, R.D_DIRECTION) == ("USD/JPY", "sell_USD_buy_JPY")


def test_hypergeometric_matches_2026_08_18_verdict_table():
    # §5.2 凍結閾値表 (M=21, |S|=2): k_eff=1 ov≥1 → 0.0952 / k_eff=2..5 ov≥2 → 0.0048/0.0143/0.0286/0.0476
    assert R.hyper_p_ge(1, 21, 2, 1) == pytest.approx(0.0952, abs=1e-4)
    assert R.hyper_p_ge(2, 21, 2, 2) == pytest.approx(0.0048, abs=1e-4)
    assert R.hyper_p_ge(2, 21, 2, 3) == pytest.approx(0.0143, abs=1e-4)   # 08-18 verdict 実値
    assert R.hyper_p_ge(2, 21, 2, 4) == pytest.approx(0.0286, abs=1e-4)
    assert R.hyper_p_ge(2, 21, 2, 5) == pytest.approx(0.0476, abs=1e-4)
    assert R.hyper_p_ge(0, 21, 2, 3) == 1.0


def test_ea_pass_rule():
    assert R.ea_pass(1, 1, 0.0952) is True
    assert R.ea_pass(1, 3, 0.26) is False          # k_eff≥2 は overlap≥2 必須
    assert R.ea_pass(2, 3, 0.0143) is True
    assert R.ea_pass(2, 8, 0.12) is False          # p>α (構造的 PASS 不能域)
    assert R.ea_pass(0, 0, 1.0) is False


def test_rule_candidate_boundary_inclusive():
    assert R.rule_candidate(-0.25, 2.0) is True
    assert R.rule_candidate(-0.24, 5.0) is False
    assert R.rule_candidate(-2.0, 1.99) is False
    assert R.rule_candidate(0.3, 7.0) is False      # 上昇日 (covert 型) は構造的捕捉不能


def test_verdict_branch_fixed_table():
    assert R.verdict_branch(True, True, True, True) == "PASS"
    assert R.verdict_branch(True, True, True, False) == "PARTIAL"
    assert R.verdict_branch(True, True, False, True) == "PARTIAL"
    assert R.verdict_branch(True, True, False, False) == "FAIL"
    assert R.verdict_branch(False, True, True, True) == "NO-TEST"
    assert R.verdict_branch(True, False, True, True) == "NO-TEST"


def _bars(days, opens, highs, lows, closes, n=4):
    idx, rows = [], []
    for d, o, h, l, c in zip(days, opens, highs, lows, closes):
        for i in range(n):
            idx.append(pd.Timestamp(f"{d} {i * 6:02d}:00", tz="UTC"))
            rows.append((o, h, l, c))
    return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=pd.DatetimeIndex(idx))


def test_daily_from_15m_utc_day_and_weekend_filter():
    days = [dt.date(2026, 7, 24) + dt.timedelta(days=i) for i in range(5)]   # 金土日月火
    df = _bars(days, [100] * 5, [101] * 5, [99] * 5, [100.5] * 5)
    day = R.daily_from_15m(df)
    assert [d.weekday() for d in day.index] == [4, 0, 1]                    # 土日除外
    assert day.loc[dt.date(2026, 7, 24), "range"] == pytest.approx(2.0)
    assert day.loc[dt.date(2026, 7, 24), "co_ret"] == pytest.approx(0.005)


def test_candidates_applies_frozen_rule_once():
    # 21 営業日: 20 日は静か (range 1, close=open)、21 日目に −1% / range 5 (ratio 5 ≥ 2.0) → candidate
    days, cur = [], dt.date(2026, 6, 1)
    while len(days) < 21:
        if cur.weekday() < 5:
            days.append(cur)
        cur += dt.timedelta(days=1)
    opens = [100.0] * 21
    highs = [100.5] * 20 + [102.5]
    lows = [99.5] * 20 + [97.5]
    closes = [100.0] * 20 + [99.0]
    day = R.daily_from_15m(_bars(days, opens, highs, lows, closes))
    assert R.candidates(day, days, R.X_FROZEN, R.Y_FROZEN) == [days[-1]]
    assert R.candidates(day, days, 6.0, R.Y_FROZEN) == []                   # ratio 5 < 6
