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
