"""OandaClient.list_transactions_full — TransactionList のページを idrange で辿って
tx 本体を集める (2026-09-23、rule:R3、F4 入出金調整の台帳取得)。

pin する性質: (1) 全ページを同じ type フィルタで辿り連結する / (2) ページ無し = 空
(0 件は成功) / (3) 一覧・ページのどちらの失敗も (False, err) で返し、部分結果を
成功と偽らない。
"""
from __future__ import annotations

from modules.oanda_client import OandaClient

ACCT = "001-009-1234567-001"


def _client(monkeypatch, router):
    c = OandaClient(token="t", account_id=ACCT)
    calls: list[str] = []

    def _req(method, path, data=None, timeout=10):
        calls.append(path)
        for key, resp in router:
            if key in path:
                return resp
        raise AssertionError(f"unexpected path {path}")
    monkeypatch.setattr(c, "_request", _req)
    return c, calls


def test_walks_all_pages_with_type_filter_and_concatenates(monkeypatch):
    base = f"https://api-fxtrade.oanda.com/v3/accounts/{ACCT}/transactions/idrange"
    listing = {"from": "2026-09-01T00:00:00Z", "to": "2026-09-23T00:00:00Z", "count": 2,
               "pages": [f"{base}?from=100&to=150&type=TRANSFER_FUNDS",
                         f"{base}?from=151&to=200&type=TRANSFER_FUNDS"]}
    p1 = {"transactions": [{"id": "120", "type": "TRANSFER_FUNDS", "amount": "100000.0000"}]}
    p2 = {"transactions": [{"id": "180", "type": "TRANSFER_FUNDS", "amount": "-5000.0000"}]}
    c, calls = _client(monkeypatch, [("idrange?from=100&to=150", (True, p1)),
                                     ("idrange?from=151&to=200", (True, p2)),
                                     ("/transactions?", (True, listing))])
    ok, body = c.list_transactions_full("2026-09-01T00:00:00Z", "2026-09-23T00:00:00Z",
                                        types=["TRANSFER_FUNDS"])
    assert ok is True
    assert [t["id"] for t in body["transactions"]] == ["120", "180"]
    assert body["pages"] == 2
    assert calls[0] == (f"/v3/accounts/{ACCT}/transactions?pageSize=1000"
                        "&from=2026-09-01T00:00:00Z&to=2026-09-23T00:00:00Z&type=TRANSFER_FUNDS")
    assert all("type=TRANSFER_FUNDS" in p for p in calls[1:])


def test_no_pages_is_success_with_empty_list(monkeypatch):
    c, calls = _client(monkeypatch, [("/transactions?", (True, {"count": 0, "pages": []}))])
    ok, body = c.list_transactions_full("2026-09-01T00:00:00Z", "2026-09-23T00:00:00Z",
                                        types=["TRANSFER_FUNDS"])
    assert ok is True and body["transactions"] == [] and body["pages"] == 0
    assert len(calls) == 1


def test_listing_or_page_failure_is_not_a_partial_success(monkeypatch):
    c, _ = _client(monkeypatch, [("/transactions?", (False, {"error": 401, "message": "x"}))])
    ok, body = c.list_transactions_full("2026-09-01T00:00:00Z", "2026-09-23T00:00:00Z")
    assert ok is False and body["error"] == 401
    base = f"https://api-fxtrade.oanda.com/v3/accounts/{ACCT}/transactions/idrange"
    listing = {"pages": [f"{base}?from=1&to=2", f"{base}?from=3&to=4"]}
    c, _ = _client(monkeypatch, [("idrange?from=1&to=2", (True, {"transactions": [{"id": "1"}]})),
                                 ("idrange?from=3&to=4", (False, {"error": "timeout"})),
                                 ("/transactions?", (True, listing))])
    ok, body = c.list_transactions_full("2026-09-01T00:00:00Z", "2026-09-23T00:00:00Z")
    assert ok is False and body["error"] == "timeout" and "page" in body
