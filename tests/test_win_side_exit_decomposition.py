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


def _bars(start, highs, lows, freq="1min"):
    import pandas as pd
    idx = pd.date_range(start, periods=len(highs), freq=freq, tz="UTC")
    return pd.DataFrame({"Open": highs, "High": highs, "Low": lows, "Close": lows}, index=idx)


def _minute_bars(start, n, spikes=None, base_hi=150.01, base_lo=149.99):
    """n 本の 1m 足。spikes = {分 offset: (high, low)} で特定の分だけ値を変える。"""
    hi = [base_hi] * n
    lo = [base_lo] * n
    for k, (h, l) in (spikes or {}).items():
        hi[k], lo[k] = h, l
    return _bars(start, hi, lo)


def test_fixed_horizon_excursion_is_exit_independent(wsed, tmp_path):
    """固定ホライズン excursion は exit 機構に依存しない (PR #253 review 4002255778)。

    exit_time / close_reason / mafe_* を変えても値が変わらないこと、
    BUY/SELL の符号が正しいことを pin。既知 NG: mafe_favorable_pips を対照に使う実装。
    """
    bars = _minute_bars("2026-07-01T00:00:00+00:00", 120, {10: (150.30, 149.99), 30: (150.01, 149.80)})
    r1 = _rows(wsed, tmp_path, [_t("2026-07-01T00:05:00+00:00", "WIN", 2.0, "SL_HIT",
                                   exit_time="2026-07-01T00:20:00+00:00",
                                   mafe_favorable_pips=2.0, entry_price=150.00)])[0]
    r2 = _rows(wsed, tmp_path, [_t("2026-07-01T00:05:00+00:00", "WIN", 30.0, "MAX_HOLD_TIME",
                                   exit_time="2026-07-01T08:00:00+00:00",
                                   mafe_favorable_pips=99.0, entry_price=150.00)])[0]
    for r in (r1, r2):
        r["instrument"] = "USD_JPY"
    x1 = wsed.fixed_horizon_excursion(r1, bars, 60)
    x2 = wsed.fixed_horizon_excursion(r2, bars, 60)
    assert x1 == x2
    assert x1 == pytest.approx((30.0, 20.0))
    r1["direction"] = "SELL"
    assert wsed.fixed_horizon_excursion(r1, bars, 60) == pytest.approx((20.0, 30.0))


def test_fixed_horizon_excursion_clips_to_the_advertised_horizon(wsed, tmp_path):
    """窓は [entry, entry + horizon] にクリップする (PR #310 review 4151347679)。

    entry 00:05 / horizon 60 分 → 00:05〜01:04 開始の 1m 足のみ。
    既知 NG (旧実装): 「entry 以後の最初の 15m バーから 4 本」= 00:15〜01:15 を測り、
    先頭 10 分 (00:05〜00:15) を落とし、01:05〜01:15 を足していた。
    """
    r = _rows(wsed, tmp_path, [_t("2026-07-01T00:05:00+00:00", "WIN", 2.0, "SL_HIT",
                                  entry_price=150.00, instrument="USD_JPY")])[0]
    # 00:07 (窓内・旧実装では落ちる) に +50p、01:10 (窓外・旧実装では入る) に −70p
    bars = _minute_bars("2026-07-01T00:00:00+00:00", 120, {7: (150.50, 149.99), 70: (150.01, 149.30)})
    fav, adv = wsed.fixed_horizon_excursion(r, bars, 60)
    assert fav == pytest.approx(50.0)
    assert adv == pytest.approx(1.0)
    # 01:04 開始の足は窓内 (終了 01:05 = entry + 60 分)、01:05 開始の足は窓外
    edge_in = _minute_bars("2026-07-01T00:00:00+00:00", 120, {64: (150.40, 149.99)})
    edge_out = _minute_bars("2026-07-01T00:00:00+00:00", 120, {65: (150.40, 149.99)})
    assert wsed.fixed_horizon_excursion(r, edge_in, 60)[0] == pytest.approx(40.0)
    assert wsed.fixed_horizon_excursion(r, edge_out, 60)[0] == pytest.approx(1.0)
    # 秒単位の entry: 00:05:30 → 最初の足は 00:06 (00:05 開始の足は entry 前を含むので入れない)
    r2 = _rows(wsed, tmp_path, [_t("2026-07-01T00:05:30+00:00", "WIN", 2.0, "SL_HIT",
                                   entry_price=150.00, instrument="USD_JPY")])[0]
    pre_entry = _minute_bars("2026-07-01T00:00:00+00:00", 120, {5: (150.60, 149.99)})
    assert wsed.fixed_horizon_excursion(r2, pre_entry, 60)[0] == pytest.approx(1.0)


def test_fixed_horizon_excursion_unaligned_entry_on_15m_grid_is_covered(wsed, tmp_path):
    """非整列 entry × 15m 足でも、窓内に完結する足が揃っていれば有効 (PR #310 review 4152127036)。

    entry 00:05 / horizon 60 分 / 15m 足 → 窓内に完結する足は 00:15, 00:30, 00:45 開始。
    既知 NG: 末尾の期待開始を非整列の entry+H−15m = 00:50 で取り、00:45 との差 5 分 > edge 0 で None にしていた。
    """
    r = _rows(wsed, tmp_path, [_t("2026-07-01T00:05:00+00:00", "WIN", 2.0, "SL_HIT",
                                  entry_price=150.00, instrument="USD_JPY")])[0]
    bars = _bars("2026-07-01T00:00:00+00:00", [150.01, 150.20, 150.01, 150.01, 150.50, 150.01],
                 [149.99] * 6, freq="15min")
    fav, adv = wsed.fixed_horizon_excursion(r, bars, 60, bar_minutes=15, max_gap_min=15)
    # 00:15 開始の +20p は窓内、01:00 開始の +50p (終了 01:15 > 01:05) は窓外
    assert fav == pytest.approx(20.0)
    assert adv == pytest.approx(1.0)


def test_fixed_horizon_excursion_rejects_gapped_or_late_windows(wsed, tmp_path):
    """バー不足 / 窓の先頭・末尾が欠ける は None (週末跨ぎ等を黙って混ぜない)。"""
    r = _rows(wsed, tmp_path, [_t("2026-07-01T00:00:00+00:00", "WIN", 2.0, "SL_HIT",
                                  entry_price=150.00, instrument="USD_JPY")])[0]
    short = _minute_bars("2026-07-01T00:00:00+00:00", 30)
    late = _minute_bars("2026-07-01T00:20:00+00:00", 120)
    assert wsed.fixed_horizon_excursion(r, short, 60) is None
    assert wsed.fixed_horizon_excursion(r, late, 60) is None


def test_fixed_horizon_excursion_rejects_internal_gaps(wsed, tmp_path):
    """窓の内部に max_gap_min を超える欠落があれば None (PR #310 review 4151253825)。

    既知 NG: 総 span だけ見る判定 — 15m 足 00:15/00:30/01:00/01:15 (00:45 欠落) を通す。
    1m 足では 4 分以内の無約定分は許容し、6 分の欠落は落とす。
    """
    import pandas as pd
    r = _rows(wsed, tmp_path, [_t("2026-07-01T00:15:00+00:00", "WIN", 2.0, "SL_HIT",
                                  entry_price=150.00, instrument="USD_JPY")])[0]
    idx = pd.DatetimeIndex(["2026-07-01T00:15", "2026-07-01T00:30",
                            "2026-07-01T01:00", "2026-07-01T01:15"], tz="UTC")
    gapped = pd.DataFrame({"Open": [150.1] * 4, "High": [150.2] * 4,
                           "Low": [149.9] * 4, "Close": [150.0] * 4}, index=idx)
    assert wsed.fixed_horizon_excursion(r, gapped, 60, bar_minutes=15, max_gap_min=15) is None
    full = _bars("2026-07-01T00:15:00+00:00", [150.2] * 4, [149.9] * 4, freq="15min")
    assert wsed.fixed_horizon_excursion(r, full, 60, bar_minutes=15, max_gap_min=15) == pytest.approx((20.0, 10.0))
    m = _minute_bars("2026-07-01T00:00:00+00:00", 120)
    small_gap = m.drop(m.index[30:34])   # 4 分欠落 → 許容
    big_gap = m.drop(m.index[30:36])     # 6 分欠落 → 却下
    assert wsed.fixed_horizon_excursion(r, small_gap, 60) is not None
    assert wsed.fixed_horizon_excursion(r, big_gap, 60) is None


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
    cpre, cpost, S, cutoff = wsed.common_coverage(pre, post, ends, horizon_min=240)
    assert S == {"USD_JPY"}
    assert [r["instrument"] for r in cpre] == ["USD_JPY"]
    assert [r["instrument"] for r in cpost] == ["USD_JPY", "USD_JPY"]
    assert cutoff == datetime(2026, 9, 22, 2, 0, tzinfo=timezone.utc)
    late = [row("USD_JPY", "2026-09-22T03:00:00")]
    assert wsed.common_coverage([], late, ends, horizon_min=240)[1] == []


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
    above = _minute_bars("2026-07-01T00:00:00+00:00", 120, base_hi=150.30, base_lo=150.10)
    assert wsed.fixed_horizon_excursion(r, above, 60) == pytest.approx((30.0, 0.0))
    r["direction"] = "SELL"
    assert wsed.fixed_horizon_excursion(r, above, 60) == pytest.approx((0.0, 30.0))


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


def test_block_bootstrap_keeps_dependent_observations_together(wsed):
    """同ブロック (同じ日) の観測はまとめて復元抽出する (PR #310 review 4151311925)。

    既知 NG: 行単位 i.i.d. resample — 1 日 20 本が日次効果で同値 (= 実質 20 日分の情報) なのに
    400 観測として扱い CI を不当に狭くする。
    """
    a = [float(d) for d in range(20) for _ in range(20)]
    b = [float(d) for d in range(20) for _ in range(20)]
    ka = [f"a{d}" for d in range(20) for _ in range(20)]
    kb = [f"b{d}" for d in range(20) for _ in range(20)]
    lo_b, hi_b = wsed.boot_median_diff(a, b, n=400, a_blocks=ka, b_blocks=kb)
    lo_i, hi_i = wsed.boot_median_diff(a, b, n=400)
    assert (hi_b - lo_b) > 1.5 * (hi_i - lo_i)


def test_overlap_blocks_keep_cross_midnight_overlapping_windows_together(wsed):
    """窓が重なる観測は日付を跨いでも同じブロック (PR #310 review 4152000632)。

    既知 NG: UTC 日でブロックを切る — 23:30 と 00:30 の 240 分窓は 3 時間重なるのに別ブロック。
    窓が重ならない観測 (前の窓終了後) は新しいブロックになる。連鎖的な重なりも 1 ブロック。
    """
    from datetime import datetime, timezone

    def t(iso):
        return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)

    dts = [t("2026-07-01T23:30:00"), t("2026-07-02T00:30:00"), t("2026-07-02T04:00:00"),
           t("2026-07-02T09:00:00")]
    b = wsed.overlap_blocks(dts, 240)
    assert b[0] == b[1] == b[2]          # 23:30〜03:30 と 00:30〜04:30 に 04:00 が連鎖
    assert b[3] != b[0]                  # 09:00 は 08:00 の最遅終端より後
    # 入力順に依存しない
    assert wsed.overlap_blocks(list(reversed(dts)), 240) == list(reversed(b))


def test_pre_windows_crossing_the_transition_start_are_dropped(wsed):
    """窓 [entry, entry+H] が START を越える pre 行は落とす (PR #310 review 4152047567)。

    既知 NG: START 直前の pre 窓 (240 分) が遷移窓直後の post 窓と同じ価格バーを共有し、
    群ごとに作ったブロックで独立に resample される。
    """
    from datetime import datetime, timezone

    def row(iso):
        return {"entry_dt": datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)}

    pre = [row("2026-06-03T03:00:00"), row("2026-06-03T03:58:28"), row("2026-06-03T05:00:00")]
    kept = wsed.drop_boundary_crossing(pre, wsed.SHADOW_EXIT_REGIME_BREAK, 240)
    assert [r["entry_dt"].strftime("%H:%M:%S") for r in kept] == ["03:00:00", "03:58:28"]
    kept60 = wsed.drop_boundary_crossing(pre, wsed.SHADOW_EXIT_REGIME_BREAK, 60)
    assert len(kept60) == 3


def test_block_bootstrap_refuses_degenerate_single_block_cohorts(wsed):
    """ブロック数が足りない群があれば CI を出さない (PR #310 review 4151937674)。

    既知 NG: 片群が 1 日に集中 → 全 resample が同一になり、幅ゼロの「95% CI」を報告する。
    """
    a = [1.0, 2.0, 3.0, 4.0]
    b = [float(d) for d in range(20)]
    one_day = ["d1"] * 4
    many = [f"b{d}" for d in range(20)]
    assert wsed.boot_median_diff(a, b, n=200, a_blocks=one_day, b_blocks=many) is None
    assert wsed.boot_median_diff(b, b, n=200, a_blocks=many, b_blocks=many) is not None


def test_common_coverage_drops_instruments_whose_cache_starts_late(wsed):
    """キャッシュ始端が最早 entry より後の pair も両群から外す (pre だけ落ちる型の非対称を防ぐ)。"""
    from datetime import datetime, timezone

    def row(inst, iso):
        return {"instrument": inst, "entry_dt": datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)}

    pre = [row("USD_JPY", "2026-04-02T00:00:00"), row("EUR_JPY", "2026-04-02T00:00:00")]
    post = [row("USD_JPY", "2026-07-01T00:00:00"), row("EUR_JPY", "2026-07-01T00:00:00")]
    end = datetime(2026, 10, 1, tzinfo=timezone.utc)
    ends = {"USD_JPY": end, "EUR_JPY": end}
    starts = {"USD_JPY": datetime(2026, 3, 27, tzinfo=timezone.utc),
              "EUR_JPY": datetime(2026, 4, 15, tzinfo=timezone.utc)}
    cpre, cpost, S, _ = wsed.common_coverage(pre, post, ends, horizon_min=60, bar_start=starts)
    assert S == {"USD_JPY"}
    assert [r["instrument"] for r in cpre + cpost] == ["USD_JPY", "USD_JPY"]
