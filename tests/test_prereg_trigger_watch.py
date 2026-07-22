"""prereg_trigger_watch の判定純関数テスト (network なし、データ注入)。

背景: T5 pre-reg トリガーが監視主体不在で 18 日間未執行 (2026-07-06 発見)。
本ツールはその構造防止であり、判定ロジック自体の回帰をここで固定する。
"""
import json
from pathlib import Path

from tools.prereg_trigger_watch import (
    REGISTRY_PATH,
    evaluate_ingest_freshness,
    evaluate_price_below,
    evaluate_shadow_count_decision,
    evaluate_shadow_count_info,
    load_registry,
    to_markdown,
)


def test_price_below_triggers_only_under_threshold():
    assert evaluate_price_below(159.49, 159.50)["state"] == "TRIGGERED"
    assert evaluate_price_below(159.50, 159.50)["state"] == "WATCHING"
    assert evaluate_price_below(161.20, 159.50)["state"] == "WATCHING"
    assert evaluate_price_below(None, 159.50)["state"] == "DATA_UNAVAILABLE"


def test_shadow_decision_states():
    # N 到達 → 判定期日
    r = evaluate_shadow_count_decision(10, 10, 5, "2026-09-30", "2026-08-01")
    assert r["state"] == "TRIGGERED" and "R1" in r["detail"]
    # deadline 超過 + floor 未達 → retire 期日
    r = evaluate_shadow_count_decision(3, 10, 5, "2026-09-30", "2026-10-01")
    assert r["state"] == "TRIGGERED" and "retire" in r["detail"]
    # deadline 前 + N 未達 → watching
    r = evaluate_shadow_count_decision(3, 10, 5, "2026-09-30", "2026-08-01")
    assert r["state"] == "WATCHING"
    # deadline 超過でも floor 以上なら watching (N>=10 待ち)
    r = evaluate_shadow_count_decision(6, 10, 5, "2026-09-30", "2026-10-01")
    assert r["state"] == "WATCHING"
    assert evaluate_shadow_count_decision(None, 10, 5, "2026-09-30", "2026-08-01")[
        "state"] == "DATA_UNAVAILABLE"


def test_shadow_info_rate():
    r = evaluate_shadow_count_info(4, "2026-07-03", 13.3, "2026-07-17")
    assert r["state"] == "WATCHING"
    assert "2.00/週" in r["detail"]


def test_registry_is_valid_and_docs_exist():
    triggers = load_registry()
    assert len(triggers) >= 2
    root = REGISTRY_PATH.parents[3]
    for t in triggers:
        assert t["id"] and t["type"]
        if t.get("doc"):
            assert (root / t["doc"]).exists(), f"doc not found: {t['doc']}"


def test_markdown_renders_all_states():
    report = {
        "triggered": [{"id": "a", "detail": "d", "message": "m", "doc": "x.md"}],
        "watching": [{"id": "b", "detail": "d2"}],
        "unavailable": [{"id": "c", "detail": "d3"}],
    }
    md = to_markdown(report)
    assert "TRIGGERED" in md and "watching" in md and "unavailable" in md


def test_count_matching_prefix_for_multivariant():
    from tools.prereg_trigger_watch import count_matching
    trades = [
        {"entry_type": "kalman_d7_po_dn_flip"},
        {"entry_type": "kalman_d7_ema75_break"},
        {"entry_type": "kalman_d7_trail_atr"},
        {"entry_type": "vix_carry_unwind"},
        {"entry_type": None},
    ]
    assert count_matching(trades, "kalman_d7", prefix=True) == 3
    assert count_matching(trades, "kalman_d7", prefix=False) == 0
    assert count_matching(trades, "vix_carry_unwind") == 1

def test_live_count_decision_states():
    from tools.prereg_trigger_watch import evaluate_live_count_decision
    # N 到達 → 再評価期日
    r = evaluate_live_count_decision(20, 20, "2026-08-31", "2026-07-20")
    assert r["state"] == "TRIGGERED" and "再評価" in r["detail"]
    # deadline 到達 (N 未達でも) → 再評価期日
    r = evaluate_live_count_decision(12, 20, "2026-08-31", "2026-08-31")
    assert r["state"] == "TRIGGERED"
    # どちらも未達 → watching
    r = evaluate_live_count_decision(12, 20, "2026-08-31", "2026-07-20")
    assert r["state"] == "WATCHING"
    assert evaluate_live_count_decision(None, 20, "2026-08-31", "2026-07-20")[
        "state"] == "DATA_UNAVAILABLE"


def test_deadline_info_states():
    from tools.prereg_trigger_watch import evaluate_deadline_info
    assert evaluate_deadline_info("2026-07-21", "2026-07-22")["state"] == "TRIGGERED"
    assert evaluate_deadline_info("2026-07-21", "2026-07-21")["state"] == "WATCHING"
    assert evaluate_deadline_info("2026-07-21", "2026-07-07")["state"] == "WATCHING"


def test_count_live_matching_filters_cell_and_dedup():
    from tools.prereg_trigger_watch import count_live_matching
    trades = [
        {"entry_type": "vix_carry_unwind", "instrument": "USD_JPY",
         "direction": "SELL", "oanda_trade_id": "1", "dedup_violation": 0},
        # shadow (oanda_trade_id 空) は数えない
        {"entry_type": "vix_carry_unwind", "instrument": "USD_JPY",
         "direction": "SELL", "oanda_trade_id": "", "dedup_violation": 0},
        # dedup 汚染行は数えない
        {"entry_type": "vix_carry_unwind", "instrument": "USD_JPY",
         "direction": "SELL", "oanda_trade_id": "2", "dedup_violation": 1},
        # 方向違いは数えない
        {"entry_type": "vix_carry_unwind", "instrument": "USD_JPY",
         "direction": "BUY", "oanda_trade_id": "3", "dedup_violation": 0},
        # pair 違いは数えない
        {"entry_type": "vix_carry_unwind", "instrument": "EUR_USD",
         "direction": "SELL", "oanda_trade_id": "4", "dedup_violation": 0},
    ]
    assert count_live_matching(trades, "vix_carry_unwind", "USD_JPY", "SELL") == 1


def test_count_matching_instrument_filter_for_cell_granularity():
    """ws3-stage2-underpowered-recheck (2026-07-10): instrument 指定でセル
    (戦略×ペア) 粒度に絞れること — 無指定だと全ペア合算で過大計上する。"""
    from tools.prereg_trigger_watch import count_matching
    trades = [
        {"entry_type": "htf_false_breakout", "instrument": "AUD_JPY"},
        {"entry_type": "htf_false_breakout", "instrument": "EUR_JPY"},
        {"entry_type": "htf_false_breakout", "instrument": "AUD_JPY"},
        {"entry_type": "london_fix_reversal", "instrument": "AUD_JPY"},
    ]
    assert count_matching(trades, "htf_false_breakout") == 3
    assert count_matching(trades, "htf_false_breakout", instrument="AUD_JPY") == 2
    assert count_matching(trades, "htf_false_breakout", instrument="USD_JPY") == 0


def test_info_and_conditional_info_are_watching_not_unavailable():
    """e1-positioning-ingest-freshness (2026-07-14): type=info / conditional_info
    は機械評価なしの常時 watching。unknown type (UNAVAILABLE) に落ちて daily
    report のノイズにならないことを固定。"""
    from tools.prereg_trigger_watch import evaluate_trigger, STATE_WATCHING

    info = evaluate_trigger(
        {"id": "e1-positioning-ingest-freshness", "type": "info",
         "message": "2h 超 stale なら要調査", "doc": "kb/page.md"},
        today="2026-07-14", app_base="http://unused.invalid")
    assert info["state"] == STATE_WATCHING
    assert info["id"] == "e1-positioning-ingest-freshness"

    cond = evaluate_trigger(
        {"id": "x-conditional", "type": "conditional_info",
         "condition": "cache が 2026-11-15+ まで延伸したら発火",
         "message": "m"}, today="2026-07-14", app_base="http://unused.invalid")
    assert cond["state"] == STATE_WATCHING
    assert "2026-11-15" in cond["detail"]


def test_unknown_type_still_unavailable():
    from tools.prereg_trigger_watch import evaluate_trigger, STATE_UNAVAILABLE
    res = evaluate_trigger({"id": "z", "type": "no_such_type"},
                           today="2026-07-14", app_base="http://unused.invalid")
    assert res["state"] == STATE_UNAVAILABLE


# ── ingest_freshness (r3-market-data-ingest-freshness, 2026-07-21) ──────
# /api/marketdata/status の health verified:* を機械評価する。
# 基準は market-data-ingest-2026-07-18.md §7 宣言: ff 24h / cme 72h
# (週末市場閉鎖 ~2.5d を跨いでも誤警報しない)。

_FRESHNESS_NOW = "2026-07-21T12:00:00Z"
_FRESHNESS_CHECKS = [
    {"key": "verified:ff_calendar", "max_age_hours": 24},
    {"prefix": "verified:cme_bars:", "max_age_hours": 72, "min_keys": 2},
]


def _freshness_health(ff="2026-07-21T06:00:00Z",
                      cme1="2026-07-20T12:00:00Z",
                      cme2="2026-07-19T12:00:00Z"):
    h = {"last_cycle_at": "2026-07-21T11:30:00Z"}
    if ff is not None:
        h["verified:ff_calendar"] = ff
    if cme1 is not None:
        h["verified:cme_bars:6E=F"] = cme1
    if cme2 is not None:
        h["verified:cme_bars:6J=F"] = cme2
    return h


def test_ingest_freshness_all_fresh_is_watching():
    # ff 6h / cme 24h+48h — 全て閾値内
    r = evaluate_ingest_freshness(
        _freshness_health(), _FRESHNESS_CHECKS, _FRESHNESS_NOW)
    assert r["state"] == "WATCHING"


def test_ingest_freshness_ff_stale_over_24h_triggers():
    r = evaluate_ingest_freshness(
        _freshness_health(ff="2026-07-20T11:00:00Z"),  # 25h
        _FRESHNESS_CHECKS, _FRESHNESS_NOW)
    assert r["state"] == "TRIGGERED"
    assert "verified:ff_calendar" in r["detail"]


def test_ingest_freshness_any_cme_stale_over_72h_triggers():
    r = evaluate_ingest_freshness(
        _freshness_health(cme2="2026-07-18T11:00:00Z"),  # 73h
        _FRESHNESS_CHECKS, _FRESHNESS_NOW)
    assert r["state"] == "TRIGGERED"
    assert "verified:cme_bars:6J=F" in r["detail"]


def test_ingest_freshness_cme_weekend_gap_71h_not_stale():
    # 週末市場閉鎖 (~2.5d=60h) を跨いだ直後でも 72h 以内なら誤警報しない
    r = evaluate_ingest_freshness(
        _freshness_health(cme2="2026-07-18T13:00:00Z"),  # 71h
        _FRESHNESS_CHECKS, _FRESHNESS_NOW)
    assert r["state"] == "WATCHING"


def test_ingest_freshness_missing_key_triggers_fail_loud():
    # verified 記録なし = worker 未稼働/thread 死の可能性 — silent pass 禁止
    r = evaluate_ingest_freshness(
        _freshness_health(ff=None), _FRESHNESS_CHECKS, _FRESHNESS_NOW)
    assert r["state"] == "TRIGGERED"
    assert "verified:ff_calendar" in r["detail"]


def test_ingest_freshness_zero_prefix_keys_triggers():
    r = evaluate_ingest_freshness(
        _freshness_health(cme1=None, cme2=None),
        _FRESHNESS_CHECKS, _FRESHNESS_NOW)
    assert r["state"] == "TRIGGERED"
    assert "verified:cme_bars:" in r["detail"]


def test_ingest_freshness_min_keys_shortfall_triggers():
    # 7 契約中 1 契約だけ verified が立たない類の欠落を fail-loud に拾う
    r = evaluate_ingest_freshness(
        _freshness_health(cme2=None), _FRESHNESS_CHECKS, _FRESHNESS_NOW)
    assert r["state"] == "TRIGGERED"
    assert "min_keys" in r["detail"] or "1/2" in r["detail"]


def test_ingest_freshness_unavailable_states():
    # API 不達 (None) と health DB エラー (_error) は TRIGGERED ではなく
    # DATA_UNAVAILABLE (鮮度が「不明」なのと「stale 確定」は区別する)
    r = evaluate_ingest_freshness(None, _FRESHNESS_CHECKS, _FRESHNESS_NOW)
    assert r["state"] == "DATA_UNAVAILABLE"
    r = evaluate_ingest_freshness({"_error": "OperationalError: locked"},
                                  _FRESHNESS_CHECKS, _FRESHNESS_NOW)
    assert r["state"] == "DATA_UNAVAILABLE"


def test_ingest_freshness_registry_matches_module_constants():
    """registry の閾値と modules/market_data_ingest.py の STALE_ALERT_*_SEC /
    DEFAULT_CME_SYMBOLS が乖離したら fail する整合 pin (自動生成 KB と手書き KB の
    機械的整合チェックと同じ ethos)。"""
    from modules.market_data_ingest import (
        DEFAULT_CME_SYMBOLS,
        STALE_ALERT_CME_SEC,
        STALE_ALERT_FF_SEC,
    )
    trig = next(t for t in load_registry()
                if t["id"] == "r3-market-data-ingest-freshness")
    assert trig["type"] == "ingest_freshness"
    by_key = {c.get("key") or c.get("prefix"): c for c in trig["checks"]}
    assert by_key["verified:ff_calendar"]["max_age_hours"] * 3600 == STALE_ALERT_FF_SEC
    cme = by_key["verified:cme_bars:"]
    assert cme["max_age_hours"] * 3600 == STALE_ALERT_CME_SEC
    assert cme["min_keys"] == len(DEFAULT_CME_SYMBOLS)


def test_ingest_freshness_trigger_wiring(monkeypatch):
    """evaluate_trigger の配線: fetch を注入し、health が fresh なら WATCHING。"""
    from datetime import datetime, timedelta, timezone

    import tools.prereg_trigger_watch as w

    now = datetime.now(timezone.utc)
    fresh = {
        "verified:ff_calendar": (now - timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "verified:cme_bars:6E=F": (now - timedelta(hours=2)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
    }
    monkeypatch.setattr(w, "fetch_ingest_health", lambda app_base, endpoint: fresh)
    res = w.evaluate_trigger(
        {"id": "r3-market-data-ingest-freshness", "type": "ingest_freshness",
         "endpoint": "/api/marketdata/status",
         "checks": [
             {"key": "verified:ff_calendar", "max_age_hours": 24},
             {"prefix": "verified:cme_bars:", "max_age_hours": 72, "min_keys": 1},
         ],
         "message": "m", "doc": "x.md"},
        today="2026-07-21", app_base="http://unused.invalid")
    assert res["state"] == w.STATE_WATCHING
