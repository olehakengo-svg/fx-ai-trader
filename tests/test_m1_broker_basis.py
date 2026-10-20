"""D11 両基準併記 (tools/m1_clean_live_monitor.py --strong の broker 列)。

2026-10-19 rule:R3 — registry integrated-decision-packet-d11-both-basis-impl。
性質で pin する: (1) broker pips は価格差 × 方向 / pip_size、(2) 未突合は unavailable で
0 埋めしない、(3) 2 基準 × 2 predicate は同一母集団で並記し基準を選ばない、
(4) 取得失敗は status.ok=False、(5) markdown は unavailable を unavailable と書く。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from tools import m1_clean_live_monitor as m1

ANCHOR = datetime(2026, 10, 19, 9, 0, 0)


def _trade(tid, units, open_px, close_px, pl, instrument="USD_JPY", state="CLOSED", fin="0"):
    return {"id": str(tid), "instrument": instrument, "price": str(open_px),
            "initialUnits": str(units), "state": state, "realizedPL": str(pl),
            "financing": fin, "averageClosePrice": str(close_px),
            "closeTime": "2026-10-16T07:22:36.000000000Z"}


def _row(tid, pnl, entry_type="cellA", instrument="USD_JPY", direction="BUY", days_ago=5):
    ts = (ANCHOR - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
    return {"oanda_trade_id": str(tid), "pnl_pips": pnl, "entry_type": entry_type,
            "instrument": instrument, "direction": direction, "status": "CLOSED",
            "created_at": ts, "is_shadow": 0, "dedup_violation": 0}


# ── (1) broker pips / pl 純関数 ──────────────────────────────────────────

def test_broker_pips_sign_and_pip_size_long_short_jpy_nonjpy():
    long_jpy = m1.broker_trade_metrics(_trade(1, 1000, 157.918, 157.926, 8.0))
    assert long_jpy["pips"] == 0.8 and long_jpy["pl_jpy"] == 8.0 and long_jpy["units"] == 1000
    short_jpy = m1.broker_trade_metrics(_trade(2, -1000, 158.000, 157.800, 200.0))
    assert short_jpy["pips"] == 20.0  # SELL: 下落が利益
    long_eur = m1.broker_trade_metrics(_trade(3, 1000, 1.14680, 1.14830, 236.0, instrument="EUR_USD"))
    assert long_eur["pips"] == 15.0  # 0.0001 刻み
    assert m1.pip_size("USD_JPY") == 0.01 and m1.pip_size("EUR_USD") == 0.0001


def test_broker_metrics_rejects_open_malformed_or_zero_units():
    assert m1.broker_trade_metrics(_trade(1, 1000, 157.9, 158.0, 10.0, state="OPEN")) is None
    assert m1.broker_trade_metrics({"id": "1", "state": "CLOSED"}) is None
    assert m1.broker_trade_metrics(_trade(1, 0, 157.9, 158.0, 0.0)) is None
    assert m1.broker_trade_metrics({}) is None


def test_broker_net_includes_financing_separately():
    m = m1.broker_trade_metrics(_trade(1, 1000, 157.9, 158.0, 100.0, fin="9.15"))
    assert m["pl_jpy"] == 100.0 and m["financing_jpy"] == 9.15 and m["net_jpy"] == 109.15


# ── (2) 未突合は unavailable (0 埋め禁止) ───────────────────────────────

def test_cell_stats_broker_unmatched_rows_are_counted_not_zero_filled():
    rows = [_row(1, 5.0), _row(2, -3.0), _row(3, 1.0)]
    bmap = {"1": _trade(1, 1000, 157.900, 157.950, 50.0), "2": _trade(2, 1000, 158.0, 157.97, -30.0)}
    cells = m1.cumulative_cell_stats_broker(rows, ANCHOR, bmap)
    assert len(cells) == 1
    c = cells[0]
    assert c["n"] == 3 and c["n_matched"] == 2 and c["n_unmatched"] == 1
    assert c["sum_pl_jpy"] == 20.0 and c["sum_pips"] == 2.0 and c["wins"] == 1
    assert c["basis_complete"] is False  # 1 本欠けたら predicate 評価不能
    assert c["ev_pips"] == 1.0  # matched 2 本の平均であって 3 本で割っていない


def test_cell_stats_broker_population_is_identical_to_demo_population():
    rows = [_row(1, 5.0), _row(2, -3.0, days_ago=400)]  # 2 本目は cutoff 前
    rows[1]["created_at"] = "2026-01-01 00:00:00"
    bmap = {"1": _trade(1, 1000, 157.9, 157.95, 50.0), "2": _trade(2, 1000, 157.9, 157.95, 50.0)}
    demo = m1.cumulative_cell_stats(rows, ANCHOR)
    broker = m1.cumulative_cell_stats_broker(rows, ANCHOR, bmap)
    assert demo[0]["n"] == broker[0]["n"] == 1  # cutoff 前の行はどちらにも入らない


# ── (3) 2 基準 × 2 predicate の並記 ─────────────────────────────────────

def _cells_at(n, demo_pnl, broker_pl, broker_pips):
    rows = [_row(i, demo_pnl) for i in range(1, n + 1)]
    bmap = {str(i): _trade(i, 1000, 157.000, 157.000 + broker_pips / 100.0, broker_pl)
            for i in range(1, n + 1)}
    return m1.cumulative_cell_stats(rows, ANCHOR), m1.cumulative_cell_stats_broker(rows, ANCHOR, bmap)


def test_basis_table_reg_literal_is_n30_and_sum_positive_on_each_basis():
    d29, b29 = _cells_at(29, 0.5, 5.0, 0.5)
    t29 = m1.basis_table(d29, b29)["rows"][0]
    assert t29["demo"]["reg_literal"] is False and t29["broker"]["reg_literal"] is False
    d30, b30 = _cells_at(30, 0.5, 5.0, 0.5)
    t30 = m1.basis_table(d30, b30)["rows"][0]
    assert t30["demo"]["reg_literal"] is True and t30["broker"]["reg_literal"] is True
    # REG 字義は PnL>0 のみ — EV 0.5 < 1.0 なので STRONG は両基準とも False
    assert t30["demo"]["strong"] is False and t30["broker"]["strong"] is False


def test_basis_table_can_disagree_between_bases_without_choosing():
    # demo は正 (pips +2)、broker は負 (realizedPL −20、pips −2) — 片寄せせず両方出す
    rows = [_row(i, 2.0) for i in range(1, 31)]
    bmap = {str(i): _trade(i, 1000, 157.00, 156.98, -20.0) for i in range(1, 31)}
    table = m1.basis_table(m1.cumulative_cell_stats(rows, ANCHOR),
                           m1.cumulative_cell_stats_broker(rows, ANCHOR, bmap))
    r = table["rows"][0]
    assert r["demo"]["reg_literal"] is True and r["demo"]["strong"] is True
    assert r["broker"]["reg_literal"] is False and r["broker"]["strong"] is False
    assert table["disagreements"] == [r["cell"]]
    assert table["counts"] == {"reg_literal_demo": 1, "strong_demo": 1,
                               "reg_literal_broker": 0, "strong_broker": 0,
                               "broker_unavailable_cells": 0}


def test_basis_table_marks_incomplete_broker_cell_unavailable_not_false():
    rows = [_row(i, 2.0) for i in range(1, 31)]
    bmap = {str(i): _trade(i, 1000, 157.00, 157.02, 20.0) for i in range(1, 30)}  # 1 本欠け
    table = m1.basis_table(m1.cumulative_cell_stats(rows, ANCHOR),
                           m1.cumulative_cell_stats_broker(rows, ANCHOR, bmap))
    r = table["rows"][0]
    assert r["broker"]["status"] == "unavailable" and "reg_literal" not in r["broker"]
    assert table["counts"]["broker_unavailable_cells"] == 1
    assert table["disagreements"] == []  # unavailable は不一致に数えない


# ── (4) 取得: pagination / 失敗 ────────────────────────────────────────

def test_fetch_pagination_stops_once_oldest_needed_is_covered():
    pages = {
        None: (True, {"trades": [_trade(1300, 1000, 1, 1, 0), _trade(1200, 1000, 1, 1, 0)]}),
        1200: (True, {"trades": [_trade(1100, 1000, 1, 1, 0), _trade(1000, 1000, 1, 1, 0)]}),
        1000: (True, {"trades": [_trade(900, 1000, 1, 1, 0)]}),
    }
    calls = []

    def fetcher(before):
        calls.append(before)
        return pages[before]

    found, st = m1.fetch_broker_closed_trades({"1300", "1100"}, fetcher=fetcher)
    assert set(found) == {"1300", "1100"} and st["ok"] is True
    assert calls == [None, 1200]  # 1100 を拾った時点で停止、3 ページ目は呼ばない
    assert st["missing"] == 0 and st["covered"] == 2


def test_fetch_failure_is_unavailable_not_empty_success():
    found, st = m1.fetch_broker_closed_trades({"1"}, fetcher=lambda b: (False, "HTTP 500"))
    assert found == {} and st["ok"] is False and "fetch failed" in st["reason"]


def test_fetch_reports_missing_when_pages_run_dry_before_oldest_needed():
    def fetcher(before):
        return (True, {"trades": [_trade(500, 1000, 1, 1, 0)]}) if before is None else (True, {"trades": []})

    found, st = m1.fetch_broker_closed_trades({"500", "100"}, fetcher=fetcher)
    assert set(found) == {"500"} and st["ok"] is False and st["missing"] == 1


def test_fetch_marks_unavailable_when_an_id_is_absent_even_if_range_is_covered():
    # ページは最古必要 id (100) より下まで届いたが、id 200 が broker 側に無い → ok=False
    def fetcher(before):
        return (True, {"trades": [_trade(500, 1000, 1, 1, 0), _trade(100, 1000, 1, 1, 0), _trade(50, 1000, 1, 1, 0)]})

    found, st = m1.fetch_broker_closed_trades({"500", "200", "100"}, fetcher=fetcher)
    assert set(found) == {"500", "100"}
    assert st["ok"] is False and st["missing"] == 1 and "absent" in st["reason"]


def test_fetch_first_page_empty_is_unavailable_not_ok():
    found, st = m1.fetch_broker_closed_trades({"1"}, fetcher=lambda b: (True, {"trades": []}))
    assert found == {} and st["ok"] is False and st["missing"] == 1


def test_fetch_empty_needed_is_ok_without_calls():
    found, st = m1.fetch_broker_closed_trades(set(), fetcher=lambda b: (_ for _ in ()).throw(AssertionError("called")))
    assert found == {} and st["ok"] is True and st["pages"] == 0


# ── (5) strong_summary 統合 / markdown ─────────────────────────────────

def test_strong_summary_without_broker_is_skipped_and_shape_kept():
    rows = [_row(i, 2.0) for i in range(1, 5)]
    s = m1.strong_summary(rows, ANCHOR)
    assert s["broker_basis"]["status"] == "skipped"
    assert "n_cells_strong" in s and "definition_conflict" in s  # 既存キー不変
    md = m1.to_markdown_strong(s)
    assert "broker 列 skipped" in md


def test_strong_summary_broker_unavailable_renders_warning_not_zero():
    rows = [_row(i, 2.0) for i in range(1, 31)]
    s = m1.strong_summary(rows, ANCHOR, broker={"map": {}, "status": {
        "ok": False, "reason": "fetch failed: HTTP 500", "pages": 1, "covered": 0, "missing": 30}})
    assert s["broker_basis"]["status"] == "unavailable"
    md = m1.to_markdown_strong(s)
    assert "unavailable" in md and "0 として読まないこと" in md
    assert "両基準 (D11)" in md


def test_strong_summary_broker_ok_renders_both_bases():
    rows = [_row(i, 2.0) for i in range(1, 31)]
    bmap = {str(i): _trade(i, 1000, 157.00, 157.02, 20.0) for i in range(1, 31)}
    s = m1.strong_summary(rows, ANCHOR, broker={"map": bmap, "status": {"ok": True, "pages": 1, "covered": 30, "missing": 0}})
    bb = s["broker_basis"]
    assert bb["status"] == "ok" and bb["table"]["counts"]["reg_literal_broker"] == 1
    assert s["n_cells_reg_literal_demo"] == 1
    md = m1.to_markdown_strong(s)
    assert "demo=1 / broker=1" in md and "最接近セル broker" in md
