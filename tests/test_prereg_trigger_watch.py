"""prereg_trigger_watch の判定純関数テスト (network なし、データ注入)。

背景: T5 pre-reg トリガーが監視主体不在で 18 日間未執行 (2026-07-06 発見)。
本ツールはその構造防止であり、判定ロジック自体の回帰をここで固定する。
"""
import json
from pathlib import Path

from tools.prereg_trigger_watch import (
    REGISTRY_PATH,
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
