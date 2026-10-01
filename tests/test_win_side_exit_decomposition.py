"""Pin the shadow exit regime break and the win-side decomposition estimand.

背景: knowledge-base/wiki/analyses/win-side-exit-regime-break-2026-06-03.md
shadow trade の SL 変更は commit ab7a4931 (2026-06-03T07:58Z) まで dead code
だったため、この時刻の前後で shadow の payoff 統計は別 estimand になる。

pin は「性質」で書く (lesson_validity_check_pins_proxy_2026_09_02):
時変の実測値ではなく、(a) 境界定数、(b) SL_HIT ラベル衝突への対処
(close_reason は必ず outcome と組で集計する)、(c) 境界で分割されること、を固定する。
"""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

_TOOL = Path(__file__).resolve().parents[1] / "tools" / "win_side_exit_decomposition.py"


def _load():
    spec = importlib.util.spec_from_file_location("win_side_exit_decomposition", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def wsed():
    return _load()


_COMMIT_AB7A4931_UTC = datetime(2026, 6, 3, 7, 58, 28, tzinfo=timezone.utc)


def test_regime_window_start_is_not_before_the_commit_object(wsed):
    """遷移窓 START は commit ab7a4931 の object 時刻 (07:58:28Z) 以後。

    旧定数 "07:58" (分切り捨て) は 07:58:00–07:58:27 を commit 前なのに post へ
    入れていた (PR #253 review 4002255783)。fix はコードが存在する前に稼働し得ない。
    """
    start = wsed.parse_ts(wsed.SHADOW_EXIT_REGIME_BREAK)
    assert start >= _COMMIT_AB7A4931_UTC
    assert start.date().isoformat() == "2026-06-03"


def test_regime_window_end_covers_the_behavioral_activation_evidence(wsed):
    """END ≥ 挙動上の稼働確認時刻 ≥ START。窓が潰れて 1 点境界へ戻っていないこと。"""
    start = wsed.parse_ts(wsed.SHADOW_EXIT_REGIME_BREAK)
    sig = wsed.parse_ts(wsed.SHADOW_EXIT_REGIME_FIRST_SIGNATURE)
    end = wsed.parse_ts(wsed.SHADOW_EXIT_REGIME_TRANSITION_END)
    assert start < sig <= end


def test_default_split_is_the_regime_window(wsed):
    """既定の分割点が月境界などの恣意的な値へ戻っていないこと。"""
    src = _TOOL.read_text()
    assert '"--split-at", default=SHADOW_EXIT_REGIME_BREAK' in src
    assert '"--transition-end", default=SHADOW_EXIT_REGIME_TRANSITION_END' in src


def _payload(trades):
    return {"count": len(trades), "trades": trades}


def _t(entry, outcome, pnl, reason, **kw):
    d = {
        "entry_type": "s", "instrument": "EUR_JPY", "direction": "BUY",
        "entry_time": entry, "exit_time": entry, "outcome": outcome,
        "pnl_pips": pnl, "close_reason": reason, "dedup_violation": 0,
        "is_shadow": 1, "mafe_favorable_pips": abs(pnl or 0.0), "mafe_adverse_pips": 0.0,
    }
    d.update(kw)
    return d


def test_load_clean_applies_the_declared_filters(wsed, tmp_path):
    """XAU 除外 / dedup_violation=1 除外 / outcome∈{WIN,LOSS} の 3 条件。"""
    p = tmp_path / "t.json"
    p.write_text(json.dumps(_payload([
        _t("2026-07-01T00:00:00+00:00", "WIN", 3.0, "SL_HIT"),
        _t("2026-07-02T00:00:00+00:00", "WIN", 3.0, "SL_HIT", instrument="XAU_USD"),
        _t("2026-07-03T00:00:00+00:00", "WIN", 3.0, "SL_HIT", dedup_violation=1),
        _t("2026-07-04T00:00:00+00:00", None, None, None),
        _t("2026-07-05T00:00:00+00:00", "BREAKEVEN", 0.0, "SL_HIT"),
    ])))
    rows = wsed.load_clean(str(p), "s")
    assert len(rows) == 1, "XAU / dedup / non-WIN,LOSS のいずれかが素通りしている"


def test_close_reason_is_never_aggregated_without_outcome(wsed, tmp_path):
    """SL_HIT は BE/trail 利確を含む混成ラベル。outcome 分割なしの集計は禁止。

    同一 close_reason に WIN と LOSS を混ぜた入力で、WIN 側平均が LOSS に
    汚染されないことを確認する (project_sl_hit_label_collision)。
    """
    p = tmp_path / "t.json"
    p.write_text(json.dumps(_payload([
        _t("2026-07-01T00:00:00+00:00", "WIN", 4.0, "SL_HIT"),
        _t("2026-07-02T00:00:00+00:00", "LOSS", -20.0, "SL_HIT"),
    ])))
    rows = wsed.load_clean(str(p), "s")
    table = wsed.reason_outcome_table(rows, "t")
    assert "| SL_HIT | 1 | 4.00 | 1 | 20.00 |" in table


def _rows(wsed, tmp_path, trades, stream="shadow"):
    p = tmp_path / "t.json"
    p.write_text(json.dumps(_payload(trades)))
    return wsed.load_clean(str(p), "s", stream)


def test_split_separates_pre_and_post_regime_rows(wsed, tmp_path):
    """境界直前に閉じた行は pre、窓明け後に建った行は post (日付ではなく時刻まで効く)。"""
    rows = _rows(wsed, tmp_path, [
        _t("2026-06-03T07:50:00+00:00", "WIN", 20.0, "MAX_HOLD_TIME",
           exit_time="2026-06-03T07:57:00+00:00"),
        _t("2026-06-03T09:01:00+00:00", "WIN", 4.0, "SL_HIT",
           exit_time="2026-06-03T09:30:00+00:00"),
    ])
    pre, post, excl = wsed.split_cohorts(
        rows, wsed.SHADOW_EXIT_REGIME_BREAK, wsed.SHADOW_EXIT_REGIME_TRANSITION_END)
    assert [r["reason"] for r in pre] == ["MAX_HOLD_TIME"]
    assert [r["reason"] for r in post] == ["SL_HIT"]
    assert excl == []


def test_trade_open_across_the_boundary_is_excluded_not_pre(wsed, tmp_path):
    """fix 前に建って fix 後に閉じた建玉は pre に入れない (PR #253 review 4002219368)。

    既知 NG: entry_time だけで振ると、この行 (fix 後の BE/trail で刈られ得る) が pre へ入る。
    """
    rows = _rows(wsed, tmp_path, [
        _t("2026-06-03T07:30:00+00:00", "WIN", 1.4, "SL_HIT",
           exit_time="2026-06-03T08:01:26+00:00"),
    ])
    pre, post, excl = wsed.split_cohorts(
        rows, wsed.SHADOW_EXIT_REGIME_BREAK, wsed.SHADOW_EXIT_REGIME_TRANSITION_END)
    assert pre == [] and post == []
    assert len(excl) == 1


def test_trade_entered_inside_the_transition_window_is_excluded(wsed, tmp_path):
    """窓内 (旧定数の 07:58:00–07:58:27 を含む) に建った行は post に入れない。"""
    rows = _rows(wsed, tmp_path, [
        _t("2026-06-03T07:58:10+00:00", "WIN", 2.0, "SL_HIT",
           exit_time="2026-06-03T08:20:00+00:00"),
        _t("2026-06-03T08:30:00+00:00", "LOSS", -5.0, "SL_HIT",
           exit_time="2026-06-03T08:40:00+00:00"),
    ])
    pre, post, excl = wsed.split_cohorts(
        rows, wsed.SHADOW_EXIT_REGIME_BREAK, wsed.SHADOW_EXIT_REGIME_TRANSITION_END)
    assert pre == [] and post == []
    assert len(excl) == 2


def test_default_stream_is_shadow_only_and_live_needs_oanda_id(wsed, tmp_path):
    """ab7a4931 が変えたのは shadow 執行のみ → 既定は shadow 限定 (PR #253 review 4002219365)。

    live = oanda_trade_id != '' (is_shadow=0 単独では live にしない)。
    is_shadow=0 ∧ oanda_trade_id 無し は ambiguous でどちらにも入れない。
    """
    trades = [
        _t("2026-07-01T00:00:00+00:00", "WIN", 3.0, "SL_HIT", is_shadow=1, oanda_trade_id=""),
        _t("2026-07-02T00:00:00+00:00", "WIN", 25.7, "MAX_HOLD_TIME",
           is_shadow=0, oanda_trade_id="549250"),
        _t("2026-07-03T00:00:00+00:00", "LOSS", -9.0, "SL_HIT", is_shadow=0, oanda_trade_id=""),
    ]
    sh = _rows(wsed, tmp_path, trades)
    lv = _rows(wsed, tmp_path, trades, stream="live")
    assert [r["pnl"] for r in sh] == [3.0], "live / ambiguous 行が shadow 集計に混入している"
    assert [r["pnl"] for r in lv] == [25.7], "is_shadow=0 単独で live 判定している"
    with pytest.raises(ValueError):
        _rows(wsed, tmp_path, trades, stream="all")


def test_hold_time_median_is_the_true_median_for_even_cohorts(wsed, tmp_path):
    """偶数件の中央値は中央 2 値の平均 (PR #253 review 4002219370)。既知 NG: 上側中央値 3.00。"""
    rows = _rows(wsed, tmp_path, [
        _t("2026-07-01T00:00:00+00:00", "WIN", 3.0, "SL_HIT", exit_time="2026-07-01T01:00:00+00:00"),
        _t("2026-07-02T00:00:00+00:00", "WIN", 3.0, "SL_HIT", exit_time="2026-07-02T03:00:00+00:00"),
    ])
    table = wsed.hold_hours(rows)
    assert "| 2026-07 | 2 | 2.00 | 2.00 |" in table


def _bars(start, highs, lows):
    import pandas as pd
    idx = pd.date_range(start, periods=len(highs), freq="15min", tz="UTC")
    return pd.DataFrame({"Open": highs, "High": highs, "Low": lows, "Close": lows}, index=idx)


def test_fixed_horizon_excursion_is_exit_independent(wsed, tmp_path):
    """固定ホライズン excursion は exit 機構に依存しない (PR #253 review 4002255778)。

    exit_time / close_reason / mafe_* を変えても値が変わらないこと、
    BUY/SELL の符号が正しいことを pin。既知 NG: mafe_favorable_pips を対照に使う実装。
    """
    bars = _bars("2026-07-01T00:15:00+00:00",
                 highs=[150.10, 150.30, 150.05, 150.20, 151.00],
                 lows=[149.90, 149.95, 149.80, 149.85, 149.00])
    base = dict(entry_type="s", instrument="USD_JPY", direction="BUY",
                entry_time="2026-07-01T00:05:00+00:00", entry_price="150.00")
    r1 = _rows(wsed, tmp_path, [_t(base["entry_time"], "WIN", 2.0, "SL_HIT",
                                   exit_time="2026-07-01T00:20:00+00:00",
                                   mafe_favorable_pips=2.0, entry_price=150.00)])[0]
    r2 = _rows(wsed, tmp_path, [_t(base["entry_time"], "WIN", 30.0, "MAX_HOLD_TIME",
                                   exit_time="2026-07-01T08:00:00+00:00",
                                   mafe_favorable_pips=99.0, entry_price=150.00)])[0]
    for r in (r1, r2):
        r["instrument"] = "USD_JPY"
    x1 = wsed.fixed_horizon_excursion(r1, bars, 4)
    x2 = wsed.fixed_horizon_excursion(r2, bars, 4)
    assert x1 == x2
    assert x1 == pytest.approx((30.0, 20.0))  # max High 150.30 / min Low 149.80 (5 本目は窓外)
    r1["direction"] = "SELL"
    assert wsed.fixed_horizon_excursion(r1, bars, 4) == pytest.approx((20.0, 30.0))


def test_fixed_horizon_excursion_rejects_gapped_or_late_windows(wsed, tmp_path):
    """バー不足 / entry から 1 本超遅れた最初のバー は None (週末跨ぎ等を黙って混ぜない)。"""
    r = _rows(wsed, tmp_path, [_t("2026-07-01T00:00:00+00:00", "WIN", 2.0, "SL_HIT",
                                  entry_price=150.00, instrument="USD_JPY")])[0]
    short = _bars("2026-07-01T00:15:00+00:00", [150.1, 150.2], [149.9, 149.8])
    late = _bars("2026-07-01T03:00:00+00:00", [150.1] * 4, [149.9] * 4)
    assert wsed.fixed_horizon_excursion(r, short, 4) is None
    assert wsed.fixed_horizon_excursion(r, late, 4) is None


def test_fixed_horizon_excursion_rejects_internal_gaps(wsed, tmp_path):
    """窓の内部に 1 本でも欠落があれば None (PR #310 review 4151253825)。

    既知 NG: 00:15/00:30/01:00/01:15 (00:45 欠落) は総 span 60 分で span 判定を通ってしまう。
    """
    import pandas as pd
    r = _rows(wsed, tmp_path, [_t("2026-07-01T00:05:00+00:00", "WIN", 2.0, "SL_HIT",
                                  entry_price=150.00, instrument="USD_JPY")])[0]
    idx = pd.DatetimeIndex(["2026-07-01T00:15", "2026-07-01T00:30",
                            "2026-07-01T01:00", "2026-07-01T01:15"], tz="UTC")
    gapped = pd.DataFrame({"Open": [150.1] * 4, "High": [150.2] * 4,
                           "Low": [149.9] * 4, "Close": [150.0] * 4}, index=idx)
    assert wsed.fixed_horizon_excursion(r, gapped, 4) is None


def test_common_coverage_drops_stale_instruments_from_both_cohorts(wsed):
    """キャッシュ終端が古い pair は pre/post の **両方** から外し、時間も共通終端で切る
    (PR #310 review 4151253820)。既知 NG: post だけ黙って落ちて instrument 構成が非対称になる。
    """
    from datetime import datetime, timezone

    def row(inst, iso):
        return {"instrument": inst, "entry_dt": datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)}

    pre = [row("USD_JPY", "2026-05-01T00:00:00"), row("EUR_JPY", "2026-05-01T00:00:00")]
    post = [row("USD_JPY", "2026-07-01T00:00:00"), row("EUR_JPY", "2026-07-01T00:00:00"),
            row("USD_JPY", "2026-09-21T23:30:00")]
    ends = {"USD_JPY": datetime(2026, 9, 22, 6, 0, tzinfo=timezone.utc),
            "EUR_JPY": datetime(2026, 7, 21, 10, 45, tzinfo=timezone.utc)}
    cpre, cpost, S, cutoff = wsed.common_coverage(pre, post, ends, horizon_bars=16)
    assert S == {"USD_JPY"}
    assert [r["instrument"] for r in cpre] == ["USD_JPY"]
    assert [r["instrument"] for r in cpost] == ["USD_JPY", "USD_JPY"]
    assert cutoff == datetime(2026, 9, 22, 2, 0, tzinfo=timezone.utc)
    late = [row("USD_JPY", "2026-09-22T03:00:00")]
    assert wsed.common_coverage([], late, ends, horizon_bars=16)[1] == []


def test_type_matched_means_restrict_both_sides_to_common_types(wsed):
    """片側にしか無い entry_type は pre/post の両方から外す。

    既知 NG: pre 全体平均 vs post の再重み付け平均 — pre-only type "x" (値 100) が
    pre 側だけに乗って差が水増しされる。
    """
    pre = [("a", 10.0), ("a", 10.0), ("x", 100.0)]
    post = [("a", 8.0), ("b", 50.0)]
    pm, qm, k, cov = wsed.type_matched_means(pre, post)
    assert (pm, qm, k) == (10.0, 8.0, 1)
    assert cov == pytest.approx(2 / 3)


def test_shift_share_is_reported_as_non_identified_when_groups_are_disjoint(wsed, tmp_path):
    """群が前後で交わらない場合、mix/within の分解は補完値に過ぎない。

    分解自体は走るが、合計が実際の Δavg_win と一致することだけを保証する
    (数字を「群内劣化 100%」と読ませないための健全性チェック)。
    """
    p = tmp_path / "t.json"
    p.write_text(json.dumps(_payload([
        _t("2026-05-01T00:00:00+00:00", "WIN", 20.0, "MAX_HOLD_TIME"),
        _t("2026-07-01T00:00:00+00:00", "WIN", 4.0, "SL_HIT"),
    ])))
    rows = wsed.load_clean(str(p), "s")
    a, b, _ = wsed.split_cohorts(
        rows, wsed.SHADOW_EXIT_REGIME_BREAK, wsed.SHADOW_EXIT_REGIME_TRANSITION_END)
    _, mix, within = wsed.shift_share(a, b, "reason")
    assert mix + within == pytest.approx(4.0 - 20.0, abs=1e-6)


def test_fixed_horizon_excursion_is_clamped_at_zero(wsed, tmp_path):
    """窓全体が entry の片側にあっても excursion は負にならない (PR #310 review 4151271136)。

    既知 NG: BUY で全バーが entry より上 → 不利幅が負 (例 −10p) になり平均・比を歪める。
    """
    r = _rows(wsed, tmp_path, [_t("2026-07-01T00:05:00+00:00", "WIN", 2.0, "SL_HIT",
                                  entry_price=150.00, instrument="USD_JPY")])[0]
    above = _bars("2026-07-01T00:15:00+00:00", [150.30] * 4, [150.10] * 4)
    assert wsed.fixed_horizon_excursion(r, above, 4) == pytest.approx((30.0, 0.0))
    r["direction"] = "SELL"
    assert wsed.fixed_horizon_excursion(r, above, 4) == pytest.approx((0.0, 30.0))


def test_control_cohort_is_not_selected_by_outcome_or_exit_time(wsed, tmp_path):
    """§6 の母集団は outcome (BREAKEVEN 含む) でも exit_time でも選ばない (PR #310 review 4151271131)。

    BE/trail は ±0.5p の決済 = BREAKEVEN を生むので、WIN/LOSS 限定は exit 機構による選別。
    既知 NG: load_clean の既定 (WIN/LOSS) をそのまま対照に流す / exit_time で pre を切る。
    """
    trades = [
        _t("2026-06-03T07:30:00+00:00", "BREAKEVEN", 0.2, "SL_HIT",
           exit_time="2026-06-03T08:30:00+00:00"),
        _t("2026-06-03T10:00:00+00:00", None, None, None, exit_time=None),
        _t("2026-06-03T06:00:00+00:00", "WIN", 5.0, "TP_HIT",
           exit_time="2026-06-03T07:00:00+00:00"),
    ]
    assert len(_rows(wsed, tmp_path, trades)) == 1  # payoff 用は WIN/LOSS のみ (不変)
    p = tmp_path / "t.json"
    p.write_text(json.dumps(_payload(trades)))
    ent = wsed.load_clean(str(p), "s", outcomes=None)
    assert len(ent) == 3
    pre, post = wsed.split_entries(ent, wsed.SHADOW_EXIT_REGIME_BREAK,
                                   wsed.SHADOW_EXIT_REGIME_TRANSITION_END)
    assert sorted(r["entry_time"][11:16] for r in pre) == ["06:00", "07:30"]
    assert [r["entry_time"][11:16] for r in post] == ["10:00"]
