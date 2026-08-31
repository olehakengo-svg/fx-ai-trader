"""prereg_trigger_watch の判定純関数テスト (network なし、データ注入)。

背景: T5 pre-reg トリガーが監視主体不在で 18 日間未執行 (2026-07-06 発見)。
本ツールはその構造防止であり、判定ロジック自体の回帰をここで固定する。
"""
import json
from pathlib import Path

from tools.prereg_trigger_watch import (
    MACHINE_EVALUABLE_TYPES,
    REGISTRY_PATH,
    evaluate_artifact_presence,
    evaluate_csv_row_match,
    evaluate_data_coverage,
    evaluate_trigger,
    read_csv_rows,
    evaluate_ingest_freshness,
    evaluate_manual_info,
    lint_reachability,
    scan_artifacts,
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


def test_count_live_matching_prefix_for_multi_variant_cell():
    """t9-kalman-d7-live-n10-ev-check (2026-08-09): live 側も match=prefix を
    honor すること。

    kalman D7 は 1 セル = 3 entry_type (po_dn_flip / ema75_break / trail_atr)。
    prefix 非対応のままだと entry_type=="kalman_d7" に完全一致する行が存在せず
    count が恒久的に 0 になり、監視エントリが**沈黙して**退避条件が発火しない
    (T5 の 18 日執行ギャップと同型の失敗モード)。
    """
    from tools.prereg_trigger_watch import count_live_matching
    trades = [
        {"entry_type": "kalman_d7_po_dn_flip", "instrument": "USD_JPY",
         "oanda_trade_id": "1", "dedup_violation": 0},
        {"entry_type": "kalman_d7_ema75_break", "instrument": "USD_JPY",
         "oanda_trade_id": "2", "dedup_violation": 0},
        # shadow / dedup 汚染 / 別戦略 は prefix でも除外される
        {"entry_type": "kalman_d7_trail_atr", "instrument": "USD_JPY",
         "oanda_trade_id": "", "dedup_violation": 0},
        {"entry_type": "kalman_d7_trail_atr", "instrument": "USD_JPY",
         "oanda_trade_id": "3", "dedup_violation": 1},
        {"entry_type": "trendline_sweep", "instrument": "USD_JPY",
         "oanda_trade_id": "4", "dedup_violation": 0},
    ]
    assert count_live_matching(trades, "kalman_d7", "USD_JPY", "",
                               prefix=True) == 2
    # 既定 (prefix=False) は完全一致のまま — 既存エントリの契約を壊さない
    assert count_live_matching(trades, "kalman_d7", "USD_JPY", "") == 0
    assert count_live_matching(trades, "trendline_sweep", "USD_JPY", "") == 1


def test_registry_kalman_live_check_entry_is_wired():
    """registry の t9-kalman-d7-live-n10-ev-check が実際に評価経路へ届くこと。

    entry_type が prefix 前提で書かれているのに type 側が prefix を渡さない、
    という配線ミス (2026-08-09 に実際に踏んだ) を固定する。
    """
    import json
    from pathlib import Path
    p = (Path(__file__).resolve().parents[1]
         / "knowledge-base/wiki/decisions/prereg-trigger-registry.json")
    reg = json.loads(p.read_text())
    hit = [t for t in reg["triggers"]
           if t["id"] == "t9-kalman-d7-live-n10-ev-check"]
    assert hit, "kalman live 退避条件の監視エントリが registry から消えている"
    trig = hit[0]
    assert trig["active"] is True
    assert trig["match"] == "prefix", "3 variant 合算には prefix 必須"
    assert trig["type"] == "live_count_decision"

    import inspect
    from tools import prereg_trigger_watch as w
    src = inspect.getsource(w.evaluate_trigger)
    live_branch = src.split('ttype == "live_count_decision"')[1].split("elif")[0]
    assert 'prefix=trig.get("match")' in live_branch, (
        "live_count_decision が match=prefix を fetch_live_count へ渡していない "
        "— 監視が沈黙する"
    )


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


def test_count_matching_unique_basis_excludes_dedup_violation():
    """sweep P-S1(a) パケット §1.4 (user 決裁 2026-07-24): shadow_count_decision
    の計数は unique バー基準 = dedup_violation=1 の 2-mode スレッド重複行を除外。
    row 基準 (既定) は他 trigger の意味論を変えないため opt-in。"""
    from tools.prereg_trigger_watch import count_matching
    trades = [
        {"entry_type": "sweep_reversion_eurgbp_late", "dedup_violation": 0},
        {"entry_type": "sweep_reversion_eurgbp_late", "dedup_violation": 1},
        {"entry_type": "sweep_reversion_eurgbp_late", "dedup_violation": 0},
        {"entry_type": "sweep_reversion_eurgbp_late"},  # 列欠落 = 0 扱い
        {"entry_type": "other", "dedup_violation": 0},
    ]
    assert count_matching(trades, "sweep_reversion_eurgbp_late") == 4
    assert count_matching(trades, "sweep_reversion_eurgbp_late",
                          exclude_dedup_violation=True) == 3


def test_paginate_closed_trades_full_walk_and_fail_loud():
    """2026-07-24 undercount バグの構造修正: 単発 limit は全 mode 合算下で
    希少戦略の N を 0 に向けて過小計上 (sweep 実測 row N=14 が N=0 報告 →
    09-30 retire 分岐の誤発動リスク)。pagination は短ページまで全量取得し、
    max_pages 到達 (全量保証なし) は None = DATA_UNAVAILABLE で fail-loud。"""
    from tools.prereg_trigger_watch import paginate_closed_trades

    # 3 ページ (500+500+120) を全量取得
    store = [{"id": i} for i in range(1120)]

    def page(off):
        return store[off:off + 500]

    rows = paginate_closed_trades(page, page_size=500)
    assert rows is not None and len(rows) == 1120

    # ちょうどページ境界 (最終ページ = 空) も全量
    store2 = [{"id": i} for i in range(1000)]
    rows2 = paginate_closed_trades(lambda off: store2[off:off + 500],
                                   page_size=500)
    assert rows2 is not None and len(rows2) == 1000

    # max_pages 到達 = silent truncation にせず None
    assert paginate_closed_trades(lambda off: [{"id": off}] * 500,
                                  page_size=500, max_pages=3) is None

    # fetch_page が list 以外 (API 異常) を返したら None
    assert paginate_closed_trades(lambda off: None, page_size=500) is None


def test_registry_t8_sweep_uses_unique_basis_and_mode():
    """t8-sweep-defer-decision の計数意味論 pin: unique バー基準 + mode 絞り込み
    (packet §1.4 決裁の registry 反映)。"""
    from tools.prereg_trigger_watch import load_registry
    trig = next(t for t in load_registry() if t["id"] == "t8-sweep-defer-decision")
    assert trig["count_basis"] == "unique"
    assert trig["mode"] == "daytrade_eurgbp"
    assert trig["n_decide"] == 10 and trig["n_floor"] == 5
    # 2026-08-17 user 決裁 (zero-fire forensic §4-2): 計数器故障 28 日分の繰り延べ
    assert trig["deadline"] == "2026-10-28"


def test_fetch_trades_window_fail_loud_and_dedup(monkeypatch):
    """Codex review 2026-07-24: open 取得失敗は None (fail-loud、closed だけ
    数える過小計上を防ぐ)。open/closed 重複は id で 1 回だけ数える。"""
    import requests as _requests
    from tools import prereg_trigger_watch as w

    class _Resp:
        def __init__(self, rows):
            self._rows = rows

        def raise_for_status(self):
            if self._rows is None:
                raise RuntimeError("boom")

        def json(self):
            return {"trades": self._rows}

    def make_get(closed_rows, open_rows):
        def _get(url, params=None, timeout=None):
            if params.get("status") == "open":
                return _Resp(open_rows)
            off = params.get("offset", 0)
            return _Resp(closed_rows[off:off + params["limit"]])
        return _get

    closed = [{"id": 1, "entry_type": "x"}, {"id": 2, "entry_type": "x"}]
    # open 取得失敗 → 全体 None
    monkeypatch.setattr(_requests, "get", make_get(closed, None))
    assert w.fetch_trades_window("2026-07-03", "http://t") is None

    # open/closed に同一 id → 1 回だけ
    monkeypatch.setattr(_requests, "get",
                        make_get(closed, [{"id": 2, "entry_type": "x"},
                                          {"id": 3, "entry_type": "x"}]))
    rows = w.fetch_trades_window("2026-07-03", "http://t")
    assert rows is not None and sorted(r["id"] for r in rows) == [1, 2, 3]


def test_evaluate_trigger_wires_mode_and_count_basis(monkeypatch):
    """Codex review 2026-07-24: registry の mode / count_basis が
    fetch_shadow_count まで配線されること (t8 = unique + mode、ws3 系 = 既定)。"""
    from tools import prereg_trigger_watch as w

    seen = {}

    def fake_fetch(entry_type, since, app_base, prefix=False, instrument="",
                   mode="", exclude_dedup_violation=False, direction="",
                   closed_only=False):
        seen[entry_type] = {"mode": mode, "uniq": exclude_dedup_violation,
                            "dir": direction, "closed": closed_only}
        return 3

    monkeypatch.setattr(w, "fetch_shadow_count", fake_fetch)
    w.evaluate_trigger(
        {"id": "t8-sweep-defer-decision", "type": "shadow_count_decision",
         "entry_type": "sweep_reversion_eurgbp_late", "since": "2026-07-03",
         "mode": "daytrade_eurgbp", "count_basis": "unique",
         "n_decide": 10, "n_floor": 5, "deadline": "2026-09-30"},
        today="2026-07-24", app_base="http://t")
    w.evaluate_trigger(
        {"id": "ws3-recheck", "type": "shadow_count_decision",
         "entry_type": "htf_false_breakout", "since": "2026-07-10",
         "instrument": "AUD_JPY",
         "n_decide": 100, "n_floor": 100, "deadline": "2027-01-31"},
        today="2026-07-24", app_base="http://t")
    # 2026-08-18: sr-anti-hunt 偽発火の回帰 pin — direction / dedup_violation:0 /
    # closed_only が entry からそのまま配線されること (無視すると凍結母集団の
    # 過大計上で単発 look を早期 burn する)
    w.evaluate_trigger(
        {"id": "sr-anti-hunt-eurjpy-buy-forward-confirm",
         "type": "shadow_count_decision",
         "entry_type": "sr_anti_hunt_bounce", "since": "2026-08-05",
         "instrument": "EUR_JPY", "direction": "BUY", "dedup_violation": 0,
         "closed_only": True,
         "n_decide": 40, "n_floor": 40, "deadline": "2027-02-28"},
        today="2026-08-18", app_base="http://t")
    assert seen["sweep_reversion_eurgbp_late"] == {
        "mode": "daytrade_eurgbp", "uniq": True, "dir": "", "closed": False}
    assert seen["htf_false_breakout"] == {
        "mode": "", "uniq": False, "dir": "", "closed": False}
    assert seen["sr_anti_hunt_bounce"] == {
        "mode": "", "uniq": True, "dir": "BUY", "closed": True}


def test_count_matching_direction_and_closed_only():
    """2026-08-18 偽発火バグの単体 pin: 実測形 (40 → 22 相当) の縮約再現。"""
    from tools.prereg_trigger_watch import count_matching

    rows = [
        {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
         "direction": "BUY", "status": "CLOSED", "dedup_violation": 0},
        {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
         "direction": "BUY", "status": "CLOSED", "dedup_violation": 1},
        {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
         "direction": "SELL", "status": "CLOSED", "dedup_violation": 0},
        {"entry_type": "sr_anti_hunt_bounce", "instrument": "EUR_JPY",
         "direction": "BUY", "status": "OPEN", "dedup_violation": 0},
    ]
    # 旧計数 (フィルタなし) = 4 — 偽発火の形
    assert count_matching(rows, "sr_anti_hunt_bounce",
                          instrument="EUR_JPY") == 4
    # 凍結母集団 = closed ∧ BUY ∧ dedup0 = 1
    assert count_matching(rows, "sr_anti_hunt_bounce", instrument="EUR_JPY",
                          direction="BUY", closed_only=True,
                          exclude_dedup_violation=True) == 1


def test_registry_automation_packet_triggers_wired():
    """2026-08-18 自動化パケットのトリガ 3 点 pin — 到達経路明記 (ZN 教訓) 込み。"""
    triggers = {t["id"]: t for t in load_registry()}

    # mof-monthly-total-2026-08-29-check は 2026-08-31 に resolve 済み
    # (active=false なので load_registry() には出ない)。旧 pin は
    # 「type == deadline_info かつ deadline == 2026-08-31」という**構文**を
    # 固定していたが、これは誤った設計 (期日待ち + 人手 URL 推測) をそのまま
    # 固定してしまっていた。是正として、後継エントリが**機械評価可能である
    # という性質**を pin する (PR #209 教訓: 構文でなく性質を pin せよ)。
    succ = triggers["mof-monthly-disclosure-new-window"]
    assert succ["type"] in MACHINE_EVALUABLE_TYPES, (
        "MoF 月次開示の監視は機械評価可能でなければならない — "
        "人手 URL 推測に戻すと 2026-08-28 の 404 誤読が再発する")
    assert succ["type"] == "csv_row_match"
    # 収集済み CSV を読む経路であること (write-only の再発防止の本体)
    assert succ["source"]["path"] == (
        "data/external/mof_statements/interventions_monthly_pending.csv")
    assert (Path(__file__).resolve().parent.parent
            / succ["source"]["path"]).exists()
    # 日次帰属の禁止 (MoF #4 の 2026 窓 OOS burn 防止) を手順に残すこと
    assert "価格シグネチャからの介入日推定は禁止" in succ["message"]

    # 2026-08-19: 条件成立 (PR #194 着地) 後も発火できなかったため
    # conditional_info -> artifact_presence へ移行。旧 pin (type と
    # 並行セッション ID) は現行設計と整合しないので、より強い
    # 「機械評価可能であること」の pin に置き換える。
    t = next(x for x in json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["triggers"]
             if x["id"] == "statement-ladder-foundation-readiness")
    assert t["type"] == "artifact_presence"
    assert t["requirements"], "artifact_presence は requirements 必須"
    assert "569dbe3f" in t["message"], "着地 commit を根拠として残すこと"

    # 09-18 スキャンには A/B/C 統合裁定と各材料の到達経路が明記されていること
    t = triggers["edge-supply-scan-monthly"]
    assert "rate-anchor-daily" in t["message"]
    assert "intervention-watch" in t["message"]
    assert "statement-ladder-foundation-readiness" in t["message"]


# ── 到達経路 (reachability) — 2026-08-19 ────────────────────────────
# 背景: info/conditional_info が「常時 WATCHING」ハードコードで、条件が
# 成立しても永久に発火しなかった (statement-ladder-foundation-readiness は
# PR #194 の main 着地で成立済みだったのに watching のまま滞留)。
# ZN 教訓「条件を書く」と「条件が起こりうる」は別物 の評価器レベル再発。

def test_artifact_presence_triggers_only_when_all_requirements_met():
    reqs = [
        {"path": "a/*.jsonl", "min_files": 24, "label": "corpus"},
        {"path": "b.csv", "min_files": 1, "label": "scores"},
    ]
    assert evaluate_artifact_presence(
        {"a/*.jsonl": 56, "b.csv": 1}, reqs)["state"] == "TRIGGERED"
    # 1 つでも不足なら watching、かつ不足分を detail に出す
    part = evaluate_artifact_presence({"a/*.jsonl": 23, "b.csv": 1}, reqs)
    assert part["state"] == "WATCHING"
    assert "corpus (23/24)" in part["detail"]
    assert evaluate_artifact_presence({}, reqs)["state"] == "WATCHING"
    assert evaluate_artifact_presence(None, reqs)["state"] == "DATA_UNAVAILABLE"


def test_data_coverage_triggers_strictly_past_threshold():
    assert evaluate_data_coverage(
        "2026-11-16", "2026-11-15")["state"] == "TRIGGERED"
    assert evaluate_data_coverage(
        "2026-11-15", "2026-11-15")["state"] == "WATCHING"
    # datetime 文字列でも先頭 10 文字で日付比較できる
    assert evaluate_data_coverage(
        "2026-08-18 07:00:00", "2026-11-15")["state"] == "WATCHING"
    assert evaluate_data_coverage(None, "2026-11-15")["state"] == "DATA_UNAVAILABLE"


def test_manual_info_honors_deadline():
    # 期日内は watching、超過で TRIGGERED (旧実装は deadline を無視していた)
    assert evaluate_manual_info(
        "", "2026-12-31", "2026-08-19", "")["state"] == "WATCHING"
    over = evaluate_manual_info("", "2026-12-31", "2027-01-01", "shadow 蓄積")
    assert over["state"] == "TRIGGERED"
    assert "shadow 蓄積" in over["detail"]
    # no-deadline は無期限 watching のまま (回帰防止)
    assert evaluate_manual_info(
        "cond", "no-deadline", "2099-01-01", "")["state"] == "WATCHING"


def test_registry_every_manual_entry_declares_reachability():
    """人手判定エントリは前進経路の明記を必須にする (再発防止の本体)。"""
    assert lint_reachability(load_registry()) == []


def test_lint_catches_manual_entry_without_reachability():
    assert lint_reachability(
        [{"id": "x", "type": "conditional_info", "condition": "何か"}])
    assert lint_reachability(
        [{"id": "x", "type": "conditional_info", "reachability": "  "}])
    assert lint_reachability(
        [{"id": "x", "type": "conditional_info", "reachability": "cron が進める"}]) == []
    assert lint_reachability([{"id": "x", "type": "deadline_info"}]) == []


def test_statement_ladder_entry_is_machine_evaluable_and_satisfied():
    """PR #194 着地済み = 実ファイルで TRIGGERED になること。

    2026-08-19 に発火 → resolve 済み (active=false) なので registry 全体を読む。
    resolve 後も「機械評価可能かつ条件成立」であることを固定し、基盤ファイルが
    消えたら気付けるようにする。
    """
    all_triggers = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["triggers"]
    trig = next(t for t in all_triggers
                if t["id"] == "statement-ladder-foundation-readiness")
    assert trig["active"] is False and trig["resolved_at"] == "2026-08-19"
    assert trig["type"] == "artifact_presence"
    reqs = trig["requirements"]
    res = evaluate_artifact_presence(scan_artifacts(reqs), reqs)
    assert res["state"] == "TRIGGERED", res["detail"]


# ── csv_row_match — 2026-08-31 ──────────────────────────────────────
# 背景: MoF 月次開示 (2026-07-30〜08-26 = 15兆3,993億円) を日次 cron が
# 08-29 に CSV へ収集していたのに、その CSV を読む検知器が無く 2 日間
# 誰も気付かなかった (write-only 6 例目)。書き手と読み手を対にする。

MOF_PENDING_CSV = "data/external/mof_statements/interventions_monthly_pending.csv"


def test_csv_row_match_separates_unavailable_from_no_match():
    """取得不能と『一致ゼロ』を折り畳まない (PR #207 no_rows vs error 教訓)。"""
    match = [{"column": "amount_yen_billions", "op": ">", "value": 0}]
    # 一致ゼロ = WATCHING (正常な監視中)
    assert evaluate_csv_row_match(
        [{"amount_yen_billions": "0.0"}], match)["state"] == "WATCHING"
    # 行ゼロも WATCHING (ファイルは読めている)
    assert evaluate_csv_row_match([], match)["state"] == "WATCHING"
    # 取得不能 = DATA_UNAVAILABLE
    assert evaluate_csv_row_match(None, match)["state"] == "DATA_UNAVAILABLE"
    # 列欠落 (schema 変化) を「一致ゼロ」に折り畳まない — 折り畳むと
    # schema が壊れた瞬間から永久に「健全に監視中」を表示し続ける
    broken = evaluate_csv_row_match([{"other_col": "1"}], match)
    assert broken["state"] == "DATA_UNAVAILABLE"
    assert "列欠落" in broken["detail"]


def test_read_csv_rows_returns_none_for_missing_file():
    """ファイル欠落は None (= DATA_UNAVAILABLE)。

    空リストに折り畳むと「収集が止まってファイルが消えた」が永久に
    「一致ゼロ = 健全に監視中」へ化ける。evaluate 側だけ分離しても
    fetcher 側で折り畳んだら意味がないので、fetcher 単体で固定する。
    """
    assert read_csv_rows({"path": "data/external/__does_not_exist__.csv"}) is None
    rows = read_csv_rows({"path": MOF_PENDING_CSV})
    assert isinstance(rows, list) and rows, "実ファイルは非空で読めること"


def test_csv_row_match_refuses_degenerate_predicates():
    """述語不正を『一致ゼロ』にしない — 設定ミスが恒久 WATCHING に化ける。"""
    rows = [{"a": "1"}]
    # 空 match は全行一致 = 偽発火。評価しない
    assert evaluate_csv_row_match(rows, [])["state"] == "DATA_UNAVAILABLE"
    # 未知の op も同様 (typo が黙って無害化されない)
    bad = evaluate_csv_row_match(
        rows, [{"column": "a", "op": "=>", "value": 1}])
    assert bad["state"] == "DATA_UNAVAILABLE" and "未知の op" in bad["detail"]


def test_csv_row_match_numeric_vs_string_and_missing_values():
    # 数値 value は数値比較 ("9" < "10" の文字列比較にならないこと)
    rows = [{"amt": "9"}, {"amt": "10"}]
    res = evaluate_csv_row_match(rows, [{"column": "amt", "op": ">", "value": 9.5}])
    assert res["state"] == "TRIGGERED" and "amt=10" in res["detail"]
    # 欠測/非数値は「一致」ではない
    assert evaluate_csv_row_match(
        [{"amt": ""}, {"amt": "n/a"}],
        [{"column": "amt", "op": ">", "value": 0}])["state"] == "WATCHING"
    # 文字列 value は ISO 日付の辞書順比較として機能する
    rows = [{"window_end": "2026-08-26"}, {"window_end": "2026-07-29"}]
    res = evaluate_csv_row_match(
        rows, [{"column": "window_end", "op": ">", "value": "2026-07-29"}])
    assert res["state"] == "TRIGGERED" and "2026-08-26" in res["detail"]


def test_csv_row_match_would_have_caught_the_2026_08_26_disclosure():
    """回帰の本体: 実データで『08-29 時点の正しい閾値』なら発火すること。

    08-29 に cron が書き込んだ 2026-07-30〜08-26 窓 (15,399.3 十億円) は、
    当時の baseline (直前窓末 = 2026-07-29) を閾値にした検知器があれば
    その日のうちに TRIGGERED になっていた。実ファイルで固定する。
    """
    rows = read_csv_rows({"path": MOF_PENDING_CSV})
    assert rows is not None, f"{MOF_PENDING_CSV} が読めない"
    res = evaluate_csv_row_match(
        rows,
        [{"column": "window_end", "op": ">", "value": "2026-07-29"},
         {"column": "amount_yen_billions", "op": ">", "value": 0}],
        ["window_start", "window_end", "amount_yen_billions"])
    assert res["state"] == "TRIGGERED", res["detail"]
    assert "2026-08-26" in res["detail"] and "15399.3" in res["detail"]


def test_mof_successor_entry_is_wired_into_the_dispatch():
    """反実仮想: registry エントリが実際に評価器へ到達しているか。

    MEMORY 教訓 (PR #208): 検知器を書いても呼ばれなければ全テスト green の
    まま無音になる。evaluate_trigger() 経由で評価し、dispatch から
    csv_row_match の分岐を外したら落ちることを確認済み
    (外すと state が DATA_UNAVAILABLE / "unknown type" になる)。
    """
    trig = next(t for t in load_registry()
                if t["id"] == "mof-monthly-disclosure-new-window")
    res = evaluate_trigger(trig, today="2026-08-31", app_base="http://unused")
    # 現閾値 (window_end > 2026-08-26) では次窓待ち = WATCHING。
    # 重要なのは「unknown type で素通りしていない」こと。
    assert res["state"] == "WATCHING", res
    assert "unknown type" not in res["detail"]
    assert "該当行なし" in res["detail"]


def test_ws3_round4_entry_is_machine_evaluable():
    trig = next(t for t in load_registry()
                if t["id"] == "ws3-round4-eur-divergence-conditional")
    assert trig["type"] == "data_coverage"
    assert trig["threshold_date"] == "2026-11-15"
    assert (Path(__file__).resolve().parent.parent
            / trig["source"]["path"]).exists()
