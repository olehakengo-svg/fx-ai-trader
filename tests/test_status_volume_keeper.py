"""status_volume_keeper — OANDA ステータス維持キーパーの契約固定。

固定する性質 (構文でなく性質で pin する原則):
  1. default OFF: env 不在では worker は絶対に起動せず、発注経路も呼ばれない
  2. guard chain: 口座に open trade があれば発注しない / NAV floor / spread /
     週末 / 時間窓 / 月次 target 到達 / 日次上限
  3. 出来高は「新規+決済の双方」= units×2 で計上される (OANDA の定義)
  4. crash-safe: close 失敗玉は state に残り、次 cycle で回収される
  5. 読み手併設: /api/demo/status に telemetry が出る + heartbeat が
     ensure_worker_running に到達する (write-only 検知器の教訓)
  6. clientExtensions tag が order/trade 両方に付く (監査の機械識別)
"""

import json
from datetime import datetime, timezone

import pytest

from modules.status_volume_keeper import StatusVolumeKeeper


WEDNESDAY_TOKYO = datetime(2026, 9, 2, 1, 30, tzinfo=timezone.utc)


class FakeClient:
    def __init__(self, nav=278000.0, margin=278000.0, open_count=0,
                 bid=159.800, ask=159.806, tradeable=True):
        self.nav = nav
        self.margin = margin
        self.open_count = open_count
        self.bid = bid
        self.ask = ask
        self.tradeable = tradeable
        self.orders = []
        self.closes = []
        self.fail_close = False

    def get_account(self):
        return True, {"account": {
            "NAV": str(self.nav), "marginAvailable": str(self.margin),
            "openTradeCount": self.open_count}}

    def get_price(self, instrument="USD_JPY"):
        return True, {"prices": [{
            "bids": [{"price": f"{self.bid:.3f}"}],
            "asks": [{"price": f"{self.ask:.3f}"}],
            "tradeable": self.tradeable}]}

    def market_order(self, side, units, instrument="USD_JPY",
                     client_tag=None, client_comment=None, **kw):
        self.orders.append({"side": side, "units": units,
                            "tag": client_tag})
        return True, {"orderFillTransaction": {
            "tradeOpened": {"tradeID": f"T{len(self.orders)}"}}}

    def close_trade(self, trade_id):
        self.closes.append(trade_id)
        if self.fail_close:
            return False, {"errorMessage": "boom"}
        return True, {"orderFillTransaction": {"pl": "-7.0"}}


def _keeper(tmp_path, monkeypatch, client=None, now=WEDNESDAY_TOKYO, **env):
    monkeypatch.setenv("STATUS_VOLUME_KEEPER_ENABLE", "1")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return StatusVolumeKeeper(
        client=client or FakeClient(),
        state_path=str(tmp_path / "svk.json"),
        now_fn=lambda: now)


def test_disabled_by_default_no_worker_no_orders(tmp_path, monkeypatch):
    monkeypatch.delenv("STATUS_VOLUME_KEEPER_ENABLE", raising=False)
    from modules import status_volume_keeper as svk
    assert svk.ensure_worker_running() is None
    fake = FakeClient()
    k = StatusVolumeKeeper(client=fake, state_path=str(tmp_path / "s.json"),
                           now_fn=lambda: WEDNESDAY_TOKYO)
    assert k.maybe_execute() is False
    assert k.last_skip_reason == "disabled"
    assert fake.orders == []


def test_happy_path_round_trip_counts_both_sides(tmp_path, monkeypatch):
    fake = FakeClient()
    k = _keeper(tmp_path, monkeypatch, client=fake)
    assert k.maybe_execute() is True
    assert len(fake.orders) == 1
    assert fake.orders[0]["tag"] == "SVK"
    assert fake.closes == ["T1"]
    # 出来高 = 新規+決済の双方 (OANDA の取引量定義)
    assert k.state["volume_usd"] == k.units * 2
    assert k.state["open_trade_ids"] == []
    # state が永続化されている
    persisted = json.loads((tmp_path / "svk.json").read_text())
    assert persisted["volume_usd"] == k.units * 2


@pytest.mark.parametrize("mutate,reason_prefix", [
    (lambda c: setattr(c, "open_count", 1), "account_not_flat"),
    (lambda c: setattr(c, "nav", 250001.0), "nav_floor"),
    (lambda c: setattr(c, "ask", 159.830), "spread"),
    (lambda c: setattr(c, "tradeable", False), "not_tradeable"),
])
def test_account_guards_block_order(tmp_path, monkeypatch, mutate,
                                    reason_prefix):
    fake = FakeClient()
    mutate(fake)
    k = _keeper(tmp_path, monkeypatch, client=fake)
    assert k.maybe_execute() is False
    assert k.last_skip_reason.startswith(reason_prefix)
    assert fake.orders == []


def test_time_and_budget_guards(tmp_path, monkeypatch):
    fake = FakeClient()
    # 週末 (2026-09-05 = 土曜)
    k = _keeper(tmp_path, monkeypatch, client=fake,
                now=datetime(2026, 9, 5, 1, 0, tzinfo=timezone.utc))
    assert k.maybe_execute() is False and k.last_skip_reason == "weekend"
    # 時間窓外 (UTC 12 時)
    k = _keeper(tmp_path, monkeypatch, client=fake,
                now=datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc))
    assert k.maybe_execute() is False
    assert k.last_skip_reason.startswith("outside_window")
    # 月次 target 到達済み
    k = _keeper(tmp_path, monkeypatch, client=fake)
    k.state["volume_usd"] = k.target_usd
    assert k.maybe_execute() is False
    assert k.last_skip_reason == "target_reached"
    # 日次上限
    k = _keeper(tmp_path, monkeypatch, client=fake)
    k.state["last_day"] = "2026-09-02"
    k.state["rt_today"] = k.max_rt_per_day
    assert k.maybe_execute() is False
    assert k.last_skip_reason == "daily_cap"
    assert fake.orders == []


def test_crash_recovery_closes_stale_before_new_order(tmp_path, monkeypatch):
    fake = FakeClient()
    fake.fail_close = True
    k = _keeper(tmp_path, monkeypatch, client=fake)
    # close 失敗 → 玉が state に残る (crash-safe 永続化)
    assert k.maybe_execute() is False
    assert k.state["open_trade_ids"] == ["T1"]
    persisted = json.loads((tmp_path / "svk.json").read_text())
    assert persisted["open_trade_ids"] == ["T1"]
    # 次 cycle: 回収のみ行い、新規発注はしない
    fake.fail_close = False
    orders_before = len(fake.orders)
    assert k.maybe_execute() is False
    assert len(fake.orders) == orders_before  # 新規なし
    assert "T1" in fake.closes
    assert k.state["open_trade_ids"] == []
    # 回収時に出来高が計上される
    assert k.state["volume_usd"] == k.units * 2


def test_month_rollover_resets_counters(tmp_path, monkeypatch):
    fake = FakeClient()
    k = _keeper(tmp_path, monkeypatch, client=fake)
    k.state.update({"month": "2026-08", "volume_usd": 999999.0,
                    "rt_count": 40})
    k._save_state()
    assert k.maybe_execute() is True  # 8月の target_reached を持ち越さない
    assert k.state["month"] == "2026-09"
    assert k.state["rt_count"] == 1


def test_market_order_client_extensions_payload(monkeypatch):
    from modules.oanda_client import OandaClient
    captured = {}

    def fake_request(self, method, path, data=None, **kw):
        captured.update(data or {})
        return True, {}

    monkeypatch.setattr(OandaClient, "_request", fake_request)
    c = OandaClient(token="t", account_id="a")
    c.market_order("buy", 10000, client_tag="SVK", client_comment="x")
    order = captured["order"]
    assert order["clientExtensions"]["tag"] == "SVK"
    assert order["tradeClientExtensions"]["tag"] == "SVK"
    # tag 未指定なら clientExtensions を一切送らない (既存挙動の不変)
    captured.clear()
    c.market_order("buy", 10000)
    assert "clientExtensions" not in captured["order"]
    assert "tradeClientExtensions" not in captured["order"]


def test_status_endpoint_exposes_keeper_telemetry(flask_client):
    """読み手併設 pin: /api/demo/status に SVK telemetry が出る。"""
    body = json.loads(flask_client.get("/api/demo/status").data)
    assert "status_volume_keeper" in body
    svk = body["status_volume_keeper"]
    assert "enabled" in svk


def test_heartbeat_reaches_keeper_ensure(flask_client, monkeypatch):
    """到達性 pin: before_request heartbeat が ensure_worker_running を呼ぶ
    (呼び手のいない検知器 = write-only の教訓)。heartbeat は 60s throttle
    されるため、throttle 時計を巻き戻してから叩く。"""
    import app as app_module
    from modules import status_volume_keeper as svk
    called = []
    monkeypatch.setattr(svk, "ensure_worker_running",
                        lambda *a, **kw: called.append(1))
    app_module._positioning_heartbeat_last[0] = 0.0
    flask_client.get("/healthz")
    assert called, "heartbeat が status_volume_keeper.ensure_worker_running に到達していない"
