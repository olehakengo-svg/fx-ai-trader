"""tools/live_roster_attrition.py の pin。

本テストが守る不変条件:
  1. 分類の**優先順位** — 停止機構に載っているセルが未帰属へ化けない
  2. 走査の**分母** — 停止集合が実在し空でない (常に E に落ちて緑、を防ぐ)
  3. **fetch 失敗を空に畳まない** (2026-08-30 監視 blind と同型の予防)
  4. estimand — clean LIVE 判定が oanda_trade_id ベースであること

⚠️ counterfactual を必ず併設する。「検知器を書いても呼ばれなければ全テスト
green のまま無音」(PR #208 教訓) / 「counterfactual が初回に通ったら
"安全" でなく "pin が無い" の証拠」(PR #210 教訓)。
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

import pytest

from tools import live_roster_attrition as lra


ANCHOR = "2026-05-01"
NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


def _stops(**overrides):
    base = {
        "force_demoted": {"ema_cross"},
        "pair_demoted": {("xs_momentum", "USD_JPY")},
        "pair_promoted": {("doji_breakout", "USD_JPY")},
        "universal_sentinel": {"session_time_bias"},
        "htf_mixed_stop": {("trendline_sweep", "GBP_USD")},
        "shadow_always": {"macd_rsi_pullback"},
        "shadow_demoted": {("vol_momentum_scalp", "GBP_USD")},
        "shadow_retired": {"sr_fib_confluence"},
    }
    base.update(overrides)
    return base


def _row(entry_type, instrument, direction, when, *, live=True, pnl=1.0):
    return {
        "entry_type": entry_type,
        "instrument": instrument,
        "direction": direction,
        "created_at": when.isoformat(),
        "oanda_trade_id": "12345" if live else "",
        "is_shadow": 0 if live else 1,
        "dedup_violation": 0,
        "pnl_pips": pnl,
    }


ANCHOR_TIME = datetime(2026, 4, 20, tzinfo=timezone.utc)
CURRENT_TIME = datetime(2026, 8, 25, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("entry_type", "instrument", "expected"),
    [
        ("ema_cross", "EUR_USD", "B_LIVE_STOPPED"),          # strategy live stop
        ("xs_momentum", "USD_JPY", "B_LIVE_STOPPED"),        # cell live stop
        ("trendline_sweep", "GBP_USD", "B_LIVE_STOPPED"),    # HTF mixed cell stop
        ("sr_fib_confluence", "EUR_USD", "C_SHADOW_DEMOTED"),
        ("vol_momentum_scalp", "GBP_USD", "C_SHADOW_DEMOTED"),
        ("macd_rsi_pullback", "EUR_USD", "C_SHADOW_DEMOTED"),
        ("some_unpromoted", "EUR_USD", "D_NEVER_PROMOTED"),
        ("doji_breakout", "USD_JPY", "E_PROMOTED_UNATTRIBUTED"),
        ("session_time_bias", "GBP_USD", "E_PROMOTED_UNATTRIBUTED"),
    ],
)
def test_classification_precedence(entry_type, instrument, expected):
    assert lra.classify((entry_type, instrument, "BUY"), still_live=False, stops=_stops()) == expected


def test_still_live_wins_over_every_stop_set():
    """A は最優先 — 停止集合に載っていても現に LIVE 約定があるなら A。"""
    assert lra.classify(("ema_cross", "EUR_USD", "BUY"), still_live=True, stops=_stops()) == "A_STILL_LIVE"


def test_e_subclass_splits_on_current_supply():
    rows = [
        _row("doji_breakout", "USD_JPY", "BUY", ANCHOR_TIME),
        # 供給あり (shadow 行が現在窓に出ている) → E1
        _row("doji_breakout", "USD_JPY", "BUY", CURRENT_TIME, live=False),
        # 完全沈黙 → E2
        _row("session_time_bias", "GBP_USD", "SELL", ANCHOR_TIME),
    ]
    report = lra.build_report(rows, anchor=ANCHOR, now=NOW, stops=_stops())
    sub = {(c["entry_type"], c["subclass"]) for c in report["cells"]}
    assert ("doji_breakout", "E1_SUPPLY_PRESENT") in sub
    assert ("session_time_bias", "E2_SILENT") in sub


def test_counterfactual_removing_a_stop_set_moves_cells_into_unattributed():
    """停止集合を 1 つ落とすと、そのセルは必ず未帰属側へ動く。

    これが落ちない = classify が停止集合を実際には読んでいない証拠になる。
    """
    rows = [_row("ema_cross", "EUR_USD", "BUY", ANCHOR_TIME)]
    intact = lra.build_report(rows, anchor=ANCHOR, now=NOW, stops=_stops())
    assert intact["counts"] == {"B_LIVE_STOPPED": 1}

    broken = lra.build_report(rows, anchor=ANCHOR, now=NOW, stops=_stops(force_demoted=set()))
    assert "B_LIVE_STOPPED" not in broken["counts"], "停止集合を空にしても分類が変わらない = 集合が読まれていない"
    assert broken["counts"] == {"D_NEVER_PROMOTED": 1}


def test_counterfactual_promotion_set_is_load_bearing():
    """昇格集合を空にすると E は消えて D になる — E の定義が昇格集合に依存する pin。"""
    rows = [_row("doji_breakout", "USD_JPY", "BUY", ANCHOR_TIME)]
    assert lra.build_report(rows, anchor=ANCHOR, now=NOW, stops=_stops())["counts"] == {
        "E_PROMOTED_UNATTRIBUTED": 1
    }
    stripped = _stops(pair_promoted=set(), universal_sentinel=set())
    assert lra.build_report(rows, anchor=ANCHOR, now=NOW, stops=stripped)["counts"] == {
        "D_NEVER_PROMOTED": 1
    }


def test_shadow_rows_never_enter_the_baseline():
    """estimand pin — baseline は clean LIVE のみ。shadow 行で母集団が膨らまない。"""
    rows = [_row("ema_cross", "EUR_USD", "BUY", ANCHOR_TIME, live=False)]
    assert lra.build_report(rows, anchor=ANCHOR, now=NOW, stops=_stops())["baseline_cells"] == 0


def test_is_shadow_zero_alone_is_not_treated_as_live():
    """FLAG_DRIFT 行 (is_shadow=0 だが oanda_trade_id 空) を LIVE と数えない。"""
    row = _row("ema_cross", "EUR_USD", "BUY", ANCHOR_TIME, live=False)
    row["is_shadow"] = 0
    assert lra.is_clean_live(row) is False


def test_dedup_and_xau_are_excluded_from_live():
    dup = _row("ema_cross", "EUR_USD", "BUY", ANCHOR_TIME)
    dup["dedup_violation"] = 1
    assert lra.is_clean_live(dup) is False
    xau = _row("ema_cross", "XAU_USD", "BUY", ANCHOR_TIME)
    assert lra.is_clean_live(xau) is False


def test_fetch_rejects_non_https_instead_of_returning_empty():
    """失敗を空に畳まない — 「取りに行けなかった」と「空だった」を分ける。"""
    with pytest.raises(ValueError):
        lra.fetch_trades("http://fx-ai-trader.onrender.com")


def test_load_stop_sets_reaches_real_non_empty_sets():
    """分母 pin — 実コードの停止/昇格集合が実在し、空でないこと。

    どれかが空になると、その機構で止めたセルが未帰属へ化けて
    「未帰属が増えた」と誤読される。
    """
    stops = lra.load_stop_sets()
    for name in ("force_demoted", "pair_demoted", "pair_promoted", "universal_sentinel",
                 "htf_mixed_stop", "shadow_always", "shadow_demoted", "shadow_retired"):
        assert stops[name], f"{name} が空 — 抽出経路が壊れている"
    assert len(stops["force_demoted"]) >= 15
    assert len(stops["pair_demoted"]) >= 30
    assert ("trendline_sweep", "GBP_USD") in stops["htf_mixed_stop"]


def test_window_boundaries_are_inclusive_and_days_scoped():
    """窓は anchor から days 日。範囲外の行は baseline に入らない。"""
    inside = datetime.fromisoformat(ANCHOR).replace(tzinfo=timezone.utc) - timedelta(days=29)
    outside = datetime.fromisoformat(ANCHOR).replace(tzinfo=timezone.utc) - timedelta(days=31)
    rows = [
        _row("ema_cross", "EUR_USD", "BUY", inside),
        _row("some_other", "EUR_USD", "BUY", outside),
    ]
    report = lra.build_report(rows, anchor=ANCHOR, now=NOW, stops=_stops())
    assert report["baseline_cells"] == 1
    assert report["cells"][0]["entry_type"] == "ema_cross"


def test_report_is_not_mutated_by_markdown_rendering():
    rows = [_row("ema_cross", "EUR_USD", "BUY", ANCHOR_TIME)]
    report = lra.build_report(rows, anchor=ANCHOR, now=NOW, stops=_stops())
    before = copy.deepcopy(report)
    lra.to_markdown(report)
    assert report == before
