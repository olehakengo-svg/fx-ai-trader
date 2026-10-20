"""storm_guard の読み手 2 本 (daily_report / anomaly_watcher) の pin (rule:R3, 2026-10-17).

PR #287 (2026-09-22) の SL replacement storm guard は `status["storm_guard"]` を
書くが、読む consumer が 25 日間存在しなかった (design doc §6-5 「読み手は
未作成」)。registry `storm-guard-enforce-decision` は有効化判断の前提に
「読み手の配線」を置いている。固定する性質:

  A. daily_report の OANDA 節は本番形の payload から totals / per-trade を表に
     出し、storm 署名 (breaker trip) に注意書きを付ける
  B. キー自体が無い場合は黙って省略しない (write-only への逆戻りを文面で露出)
  C. anomaly_watcher は tripped 建玉で `sl_replacement_storm` を出し、健全な
     trail (数件・未 trip) や空の run (fetch 失敗) では黙る
  D. 新 event type は通知バケット表と _event_line の両方に載っている
     (表に無い type は「一過性」扱いで毎 15 分通知される — 継続性イベントの
     storm をそこに落とさない)

fixture は 2026-10-16 12:00Z の本番 `/api/oanda/status.storm_guard` (carry_dip
#1254229 純族 A storm 269 回、全数捕捉) をそのまま使う。
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dr = _load("daily_report_storm_reader", "scripts/daily_report.py")
aw = _load("anomaly_watcher_storm_reader", "scripts/anomaly_watcher.py")


# 本番 2026-10-16 12:00Z (carry_dip #1254229、REPLACEMENT 269 回 = broker と 1:1)
PROD_STORM_GUARD = {
    "allow_loosen": False,
    "config": {"deadband_pips": 1.0, "max_tx_per_day": 200, "max_tx_per_hour": 50},
    "enforce": False,
    "totals": {
        "ambiguous_failures": 0, "breaker_trips": 1, "coalesced": 0, "deferred": 0,
        "detected": {"breaker": 219, "deadband": 0, "idempotent": 49,
                     "monotonic": 0, "serialize": 0},
        "evaluated": 269, "failed": 0, "local_backoff": 0, "observed_changed": 0,
        "reconcile_discarded": 0, "reconciled": 0, "sent": 269,
        "skipped": {"breaker": 0, "deadband": 0, "idempotent": 0,
                    "monotonic": 0, "serialize": 0},
        "unknown_direction": 0, "unresolved": 0,
    },
    "trades": {
        "349affe7-c3a": {
            "confirmed_sl": 157.926, "counts": {"breaker": 219, "idempotent": 49},
            "direction": "BUY", "failed_total": 0, "last_sl": 157.926,
            "pending": [], "seed_source": "broker", "sent_total": 269,
            "tripped": True, "unresolved_sl": None,
        }
    },
}


def _healthy_guard() -> dict:
    """平常 trail (#893161 型、3 送信・未 trip)。"""
    g = copy.deepcopy(PROD_STORM_GUARD)
    g["totals"]["breaker_trips"] = 0
    g["totals"]["evaluated"] = g["totals"]["sent"] = 3
    g["totals"]["detected"] = {k: 0 for k in g["totals"]["detected"]}
    g["trades"] = {
        "abc-123": {"confirmed_sl": 154.260, "counts": {}, "direction": "BUY",
                    "failed_total": 0, "last_sl": 154.260, "pending": [],
                    "seed_source": "broker", "sent_total": 3, "tripped": False,
                    "unresolved_sl": None}
    }
    return g


# ── A/B: daily_report ──────────────────────────────────────────

def test_daily_report_renders_totals_and_per_trade_from_production_shape():
    out = dr.preprocess_oanda({"oanda": {"active": True, "heartbeat": {},
                                         "storm_guard": PROD_STORM_GUARD}})
    assert "### SL replacement storm guard" in out
    # totals 行: detect-only / 50 / 200 / evaluated 269 / sent 269 / trips 1
    assert "| detect-only | 50 | 200 | 1.0p | 269 | 269 | 0 | 1 | 219/49/0/0/0 | 0/0/0/0/0 |" in out
    # per-trade 行
    assert "| 349affe7-c3a | BUY | 269 | 0 | **YES** | broker | 157.926 | breaker=219 idempotent=49 |" in out
    # storm 署名の注意書き (検知のみ = 送信は止めていない)
    assert "storm 署名あり" in out and "送信は止めていない" in out


def test_daily_report_enforce_on_reads_skipped_as_blocked_count():
    g = copy.deepcopy(PROD_STORM_GUARD)
    g["enforce"] = True
    g["totals"]["skipped"]["idempotent"] = 268
    g["totals"]["sent"] = 1
    out = dr.preprocess_oanda({"oanda": {"active": True, "storm_guard": g}})
    assert "| ON | 50 | 200 | 1.0p | 269 | 1 | 0 | 1 | 219/49/0/0/0 | 0/268/0/0/0 |" in out
    assert "enforce ON: `skipped` が実際に止めた件数" in out


def test_daily_report_healthy_trail_has_no_storm_warning():
    out = dr.preprocess_oanda({"oanda": {"active": True, "storm_guard": _healthy_guard()}})
    assert "### SL replacement storm guard" in out
    assert "| abc-123 | BUY | 3 | 0 | no | broker | 154.26 | - |" in out
    assert "storm 署名あり" not in out


def test_daily_report_successful_empty_payload_reports_missing_guard():
    """PR #337 Codex P2 (2 巡目): HTTP 200 で {} が返った成功 run は「取得不可」
    ではなく「契約が無い」。fetch 失敗 (ok False) のときだけ省略する。"""
    ok = dr.FetchResult("u", True, {}, "", "")
    out = dr.preprocess_oanda({"oanda": {}}, fetch_results={"oanda": ok})
    assert "### SL replacement storm guard" in out and "`storm_guard` キー無し" in out
    ng = dr.FetchResult("u", False, {}, "FAIL_X", "URLError: x")
    out = dr.preprocess_oanda({"oanda": {}}, fetch_results={"oanda": ng})
    assert "SL replacement storm guard" not in out
    # fetch_results 無し (後方互換) は従来どおり payload の真偽値
    assert "SL replacement storm guard" not in dr.preprocess_oanda({"oanda": {}})


def test_daily_report_storm_section_is_deterministic_and_wired_outside_llm():
    """PR #337 Codex P2 (3 巡目): 表を LLM 入力に入れるだけでは本文に残らない。
    storm_guard_report_section が保存・送信される本文へ LLM 非経由で付く。"""
    ok = dr.FetchResult("u", True, {"active": True, "storm_guard": PROD_STORM_GUARD}, "", "")
    sec = dr.storm_guard_report_section({"oanda": ok.payload}, fetch_results={"oanda": ok})
    assert sec.startswith("\n\n## SL replacement storm guard") and "| 349affe7-c3a | BUY | 269 |" in sec
    empty_ok = dr.FetchResult("u", True, {}, "", "")
    assert "`storm_guard` キー無し" in dr.storm_guard_report_section({"oanda": {}}, fetch_results={"oanda": empty_ok})
    ng = dr.FetchResult("u", False, {}, "FAIL_X", "URLError: x")
    assert dr.storm_guard_report_section({"oanda": {}}, fetch_results={"oanda": ng}) == ""
    # main() が finalize 後・保存前に本文へ連結している (AST pin)
    import ast
    src = (ROOT / "scripts/daily_report.py").read_text()
    calls = [n for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "storm_guard_report_section"]
    assert len(calls) == 1
    assert "analyst_report = analyst_report + storm_guard_report_section(data, fetch_results)" in src


def test_daily_report_missing_key_is_said_not_skipped():
    """B: キー無しを黙って省略すると write-only に戻る。文面で露出する。"""
    out = dr.preprocess_oanda({"oanda": {"active": True, "heartbeat": {"nav": 1}}})
    assert "### SL replacement storm guard" in out
    assert "`storm_guard` キー無し" in out and "盲目" in out


def test_daily_report_no_registered_trades_is_explicit():
    g = copy.deepcopy(PROD_STORM_GUARD)
    g["trades"] = {}
    g["totals"]["breaker_trips"] = 0
    out = dr.preprocess_oanda({"oanda": {"active": True, "storm_guard": g}})
    assert "(guard 登録建玉なし)" in out


# ── C/D: anomaly_watcher ───────────────────────────────────────

def test_watcher_fires_on_production_storm_shape():
    events = aw.check_storm_guard({"storm_guard": PROD_STORM_GUARD})
    assert [e["type"] for e in events] == ["sl_replacement_storm"]
    e = events[0]
    assert e["demo_trade_id"] == "349affe7-c3a"
    assert e["sent_total"] == 269 and e["breaker_trips"] == 1
    assert e["enforce"] is False and e["skipped_total"] == 0
    assert e["counts"] == {"breaker": 219, "idempotent": 49}
    assert e["max_tx_per_hour"] == 50


def test_watcher_silent_on_healthy_trail():
    assert aw.check_storm_guard({"storm_guard": _healthy_guard()}) == []


def test_watcher_reports_storm_that_completed_between_runs():
    """PR #337 Codex P2 (2 巡目): trip 後に建玉が閉じると _storm_forget が trades から
    消すが totals.breaker_trips は残る。open tripped だけ見ると 15 分 cron の隙間で
    完結した storm を一度も報告できない。"""
    g = copy.deepcopy(PROD_STORM_GUARD)
    g["trades"] = {}           # 決済済み → forget 済み
    events = aw.check_storm_guard({"storm_guard": g})
    assert [e["type"] for e in events] == ["sl_replacement_storm"]
    e = events[0]
    assert e["scope"] == "closed_before_run" and e["demo_trade_id"] is None
    assert e["closed_trips"] == 1 and e["open_tripped"] == 0 and e["breaker_trips"] == 1
    line = aw._event_line(e)
    assert "決済済み" in line and "検知のみ" in line
    # open な tripped 建玉 1 本 + 累計 2 → 決済済み 1 本分も併記 (本番 10-19 02:18Z の形)
    g2 = copy.deepcopy(PROD_STORM_GUARD)
    g2["totals"]["breaker_trips"] = 2
    events = aw.check_storm_guard({"storm_guard": g2})
    assert [(e["type"], e.get("scope")) for e in events] == [
        ("sl_replacement_storm", None), ("sl_replacement_storm", "closed_before_run")]
    assert events[1]["closed_trips"] == 1
    # 累計 = open tripped なら決済済み分は無い
    assert all(e.get("scope") is None for e in aw.check_storm_guard({"storm_guard": PROD_STORM_GUARD}))


def test_watcher_silent_on_blind_run_but_loud_on_successful_empty_payload():
    """fetch 失敗 (FetchOutcome.ok False) は「契約破れ」と混同しない。
    逆に HTTP 200 で {} が返った成功 run は契約が無い = missing を出す
    (PR #337 Codex P2: 成功した空 payload を fetch 失敗に折り畳まない)。"""
    assert aw.check_storm_guard({}, fetched_ok=False) == []
    assert aw.check_storm_guard(None, fetched_ok=False) == []  # type: ignore[arg-type]
    assert aw.check_storm_guard(PROD_STORM_GUARD and {"storm_guard": PROD_STORM_GUARD},
                                fetched_ok=False) == []
    assert [e["type"] for e in aw.check_storm_guard({}, fetched_ok=True)] == ["storm_guard_missing"]
    assert [e["type"] for e in aw.check_storm_guard(None, fetched_ok=True)] == ["storm_guard_missing"]  # type: ignore[arg-type]


def test_watcher_main_wires_fetch_ok_into_storm_check():
    """main() が FetchOutcome.ok を渡している (AST pin: 既定 True のまま呼ぶと
    502 run の {} が missing と誤報される)。"""
    import ast
    src = (ROOT / "scripts/anomaly_watcher.py").read_text()
    calls = [n for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "check_storm_guard"]
    assert len(calls) == 1
    kw = {k.arg for k in calls[0].keywords}
    assert "fetched_ok" in kw


def test_watcher_reports_missing_key_without_notifying():
    events = aw.check_storm_guard({"active": True, "heartbeat": {}})
    assert [e["type"] for e in events] == ["storm_guard_missing"]
    assert "storm_guard_missing" in aw.NOTIFY_NEVER
    assert aw._event_line(events[0]).startswith("- storm_guard_missing:")


def test_watcher_seed_fallback_for_any_restored_trade_without_broker_baseline():
    """restored trade で broker から baseline を取れなかった建玉は、方向が DB から
    分かっても confirmed_sl None のまま最初の送信を通す (= 単調性は効かない、
    oanda_bridge._storm_check_monotonic は last None で即 return)。従って
    db_direction_only も通知 (PR #337 Codex P2)。新規 fill (seed None + direction
    あり) は restored ではないので通知しない。"""
    g = _healthy_guard()
    t = g["trades"]["abc-123"]
    # 新規 fill の形 (本番 10-19 #1254773: seed None / direction BUY) → 通知しない
    t["seed_source"] = None
    assert aw.check_storm_guard({"storm_guard": g}) == []
    # broker_no_sl: broker に trade はあったが stopLossOrder なし = baseline なし → 通知
    # (3 巡目 P2: 最初の送信で confirmed_sl が立つと "broker" から区別できないので
    # bridge 側で provenance を分けた)
    t["seed_source"] = "broker_no_sl"
    t["confirmed_sl"] = 154.260
    events = aw.check_storm_guard({"storm_guard": g})
    assert [e["type"] for e in events] == ["storm_guard_seed_fallback"]
    assert events[0]["seed_source"] == "broker_no_sl"
    # broker (baseline あり) は通知しない
    t["seed_source"] = "broker"
    assert aw.check_storm_guard({"storm_guard": g}) == []
    # db_direction_only: 方向はあるが baseline なし → fail-open 窓 → 通知
    t["seed_source"] = "db_direction_only"
    t["confirmed_sl"] = None
    events = aw.check_storm_guard({"storm_guard": g})
    assert [e["type"] for e in events] == ["storm_guard_seed_fallback"]
    assert events[0]["seed_source"] == "db_direction_only" and events[0]["direction"] == "BUY"
    assert "単調性 fail-open" in aw._event_line(events[0])
    # seed None + 方向不明 + 送信あり = 何も取れなかった restored trade → 通知
    t["seed_source"] = None
    t["direction"] = None
    events = aw.check_storm_guard({"storm_guard": g})
    assert [e["type"] for e in events] == ["storm_guard_seed_fallback"]
    assert events[0]["sent_total"] == 3
    # 送信 0 なら fail-open は未発動 → 通知しない
    t["sent_total"] = 0
    assert aw.check_storm_guard({"storm_guard": g}) == []


def test_watcher_enforce_event_line_says_how_many_were_blocked():
    g = copy.deepcopy(PROD_STORM_GUARD)
    g["enforce"] = True
    g["totals"]["skipped"]["idempotent"] = 268
    events = aw.check_storm_guard({"storm_guard": g})
    line = aw._event_line(events[0])
    assert "sl_replacement_storm" in line and "enforce ON" in line and "268" in line
    off = aw._event_line(aw.check_storm_guard({"storm_guard": PROD_STORM_GUARD})[0])
    assert "検知のみ" in off and "STORM_GUARD_ENFORCE" in off


def test_new_event_types_are_in_notify_cadence_table():
    """D: 表に無い type は一過性扱い (毎 15 分通知)。継続性イベントの storm を
    そこに落とさない。"""
    assert aw.NOTIFY_EVERY_HOURS["sl_replacement_storm"] == 6
    assert aw.NOTIFY_EVERY_HOURS["storm_guard_seed_fallback"] == 6
    from datetime import datetime, timezone
    head = datetime(2026, 10, 21, 6, 3, tzinfo=timezone.utc)
    mid = datetime(2026, 10, 21, 7, 3, tzinfo=timezone.utc)
    ev = {"type": "sl_replacement_storm"}
    assert aw._should_notify(ev, head) is True
    assert aw._should_notify(ev, mid) is False
