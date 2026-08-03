"""P-S1(a) 執行条件判定器の凍結文言 pin テスト。

fixture は決裁パケット §1.3 の実測 rescued shadow (2026-07-24 時点、
unique 8 / row 14) を再現し、三基準の数値がパケット §1.1 と一致することを
固定する。判定分岐 (§6-2 + T8 DEFER retire 期日) も全て pin。
根拠: knowledge-base/wiki/decisions/sweep-reversion-ps1a-decision-packet-DRAFT.md
"""
import pytest

from tools.ps1a_execution_check import (
    ENTRY_TYPE,
    SPACING_SEC,
    VERDICT_OPTION_B,
    VERDICT_OPTION_C,
    VERDICT_RETIRE_DEADLINE,
    VERDICT_USER_REDECISION,
    VERDICT_WAITING,
    evaluate,
    select_rows,
    spaced_rows,
    unique_rows,
)


def _row(id_, entry_time, pnl, dedup=0, entry_type=ENTRY_TYPE):
    return {"id": id_, "entry_time": entry_time, "pnl_pips": pnl,
            "dedup_violation": dedup, "entry_type": entry_type}


def packet_fixture():
    """§1.3 の unique 8 行 + 2-mode スレッド重複 6 行 (row 14)。"""
    uniques = [
        _row(12359, "2026-07-06T21:16:31+00:00", -1.9),
        _row(12361, "2026-07-06T21:32:09+00:00", 2.0),
        _row(12480, "2026-07-07T21:16:22+00:00", 2.6),
        _row(12486, "2026-07-07T21:47:02+00:00", 8.3),
        _row(12625, "2026-07-08T21:16:13+00:00", -1.5),
        _row(12747, "2026-07-09T21:16:55+00:00", 5.3),
        _row(13025, "2026-07-13T21:16:38+00:00", 2.5),
        _row(13273, "2026-07-15T21:46:21+00:00", 7.8),
    ]
    dups = [
        _row(12360, "2026-07-06T21:16:34+00:00", -1.9, dedup=1),
        _row(12481, "2026-07-07T21:16:44+00:00", 2.6, dedup=1),
        _row(12487, "2026-07-07T21:47:04+00:00", 2.1, dedup=1),
        _row(12626, "2026-07-08T21:17:04+00:00", -1.5, dedup=1),
        _row(12748, "2026-07-09T21:16:56+00:00", 2.0, dedup=1),
        _row(13026, "2026-07-13T21:17:02+00:00", 1.4, dedup=1),
    ]
    noise = [_row(99999, "2026-07-10T10:00:00+00:00", 5.0,
                  entry_type="other_strategy")]
    return uniques + dups + noise


def test_three_basis_counts_match_packet():
    res = evaluate(packet_fixture(), today="2026-07-31")
    assert res["stats"]["row"]["n"] == 14
    assert res["stats"]["unique"]["n"] == 8
    assert res["stats"]["spaced"]["n"] == 6


def test_three_basis_ev_match_packet():
    """§1.1: row +2.13 / unique +3.14 / spaced +2.47 (丸め 2 桁)。"""
    res = evaluate(packet_fixture(), today="2026-07-31")
    assert res["stats"]["row"]["ev_pips"] == pytest.approx(2.13, abs=0.005)
    assert res["stats"]["unique"]["ev_pips"] == pytest.approx(3.14, abs=0.005)
    assert res["stats"]["spaced"]["ev_pips"] == pytest.approx(2.47, abs=0.005)
    assert res["stats"]["spaced"]["sum_pnl_pips"] == pytest.approx(14.8)


def test_spacing_drops_exactly_the_two_known_bars():
    """§1.1 注記: unique→spaced で落ちるのは 07-06 21:32 と 07-07 21:47 の 2 バー。"""
    rows = select_rows(packet_fixture())
    spaced = spaced_rows(unique_rows(rows))
    dropped = {12361, 12486}
    assert {t["id"] for t in spaced} == {12359, 12480, 12625, 12747, 13025, 13273}
    assert dropped.isdisjoint({t["id"] for t in spaced})


def test_spacing_boundary_exactly_12_bars_is_kept():
    """研究 grid dedup_indices は `i - keep[-1] >= gap` — ちょうど 3h は keep。"""
    assert SPACING_SEC == 10800
    rows = [
        _row(1, "2026-07-06T21:00:00+00:00", 1.0),
        _row(2, "2026-07-07T00:00:00+00:00", 1.0),      # ちょうど +3h → keep
        _row(3, "2026-07-07T02:59:59+00:00", 1.0),      # +2:59:59 → drop
    ]
    spaced = spaced_rows(unique_rows(select_rows(rows)))
    assert [t["id"] for t in spaced] == [1, 2]


def test_verdict_waiting_below_n_decide():
    res = evaluate(packet_fixture(), today="2026-07-31")
    assert res["verdict"] == VERDICT_WAITING


def _with_extra_uniques(pnls, start_day=20):
    """fixture に unique 行を追加して N>=10 にする。"""
    rows = packet_fixture()
    for i, p in enumerate(pnls):
        rows.append(_row(20000 + i,
                         f"2026-07-{start_day + i:02d}T21:16:00+00:00", p))
    return rows


def test_verdict_option_b_when_triggered_and_spaced_ev_positive():
    res = evaluate(_with_extra_uniques([1.0, 1.0]), today="2026-07-31")
    assert res["stats"]["unique"]["n"] == 10
    assert res["stats"]["spaced"]["ev_pips"] > 0
    assert res["verdict"] == VERDICT_OPTION_B


def test_verdict_option_c_when_triggered_and_spaced_ev_negative():
    # spaced/unique 両方の EV を負に沈める大負け 2 行 (符号割れさせない)
    res = evaluate(_with_extra_uniques([-30.0, -30.0]), today="2026-07-31")
    assert res["stats"]["unique"]["n"] == 10
    assert res["stats"]["spaced"]["ev_pips"] <= 0
    assert res["stats"]["unique"]["ev_pips"] <= 0
    assert res["verdict"] == VERDICT_OPTION_C


def test_verdict_user_redecision_on_sign_split():
    """§6-2: unique と spaced で EV 符号が割れたら機械執行せず user 再決裁。

    spacing で落ちる 2 行 (12361/12486, 計 +10.3p) は unique のみに効くため、
    追加 2 行を「spaced 合計 (+14.8) は殺すが unique 合計 (+25.1) は殺さない」
    帯 (-14.8 < Σ < -25.1 は不可能なので逆向き: spaced を負、unique を正に保つ)
    に置く: Σ=-16.0 → spaced -1.2, unique +9.1。
    """
    res = evaluate(_with_extra_uniques([-8.0, -8.0]), today="2026-07-31")
    assert res["stats"]["unique"]["n"] == 10
    assert res["stats"]["spaced"]["ev_pips"] <= 0
    assert res["stats"]["unique"]["ev_pips"] > 0
    assert res["verdict"] == VERDICT_USER_REDECISION


def test_verdict_retire_r2_after_deadline_with_n_below_floor():
    rows = packet_fixture()[:2] + [t for t in packet_fixture() if t["dedup_violation"] == 1]
    # unique = 2 (<5) のまま期日超過
    res = evaluate(rows, today="2026-10-01")
    assert res["stats"]["unique"]["n"] == 2
    assert res["verdict"] == VERDICT_RETIRE_DEADLINE


def test_verdict_stays_waiting_at_deadline_if_n_at_floor():
    """N>=5 なら期日超過でも retire しない (T8 DEFER: N<5 が retire 条件)。"""
    res = evaluate(packet_fixture(), today="2026-10-01")
    assert res["stats"]["unique"]["n"] == 8
    assert res["verdict"] == VERDICT_WAITING


def test_zero_fire_forensic_alert_after_30_days():
    res = evaluate(packet_fixture(), today="2026-08-15")
    assert res["zero_fire_forensic_alert"] is True
    res2 = evaluate(packet_fixture(), today="2026-08-10")
    assert res2["zero_fire_forensic_alert"] is False


def test_unparseable_entry_time_fails_loud():
    rows = packet_fixture() + [_row(30000, "not-a-date", 1.0)]
    with pytest.raises(ValueError):
        evaluate(rows, today="2026-07-31")
