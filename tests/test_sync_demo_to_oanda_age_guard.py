"""P0-2 (fable5 audit 2026-07-03, rule:R3): _sync_demo_to_oanda 孤児クローズの
openTime 年齢ガード回帰テスト。

修正前は fire-and-forget fill → DB write-back 完了前に再起動/デプロイが挟まる
と、正規 live ポジションが「孤児」に見えて起動 ~5 秒で強制クローズされ得た
(監査 P0-2、テストカバレッジゼロ)。修正後は openTime が
_ORPHAN_MIN_AGE_SEC (600s) 未満、または openTime が読めない trade は fail-safe
でスキップし次周期に再判定する。

ref: knowledge-base/wiki/decisions/fable5-phase-a-p0-fixes-2026-07-03.md
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from modules.demo_trader import DemoTrader


class _Client:
    def __init__(self, trades):
        self._trades = trades
        self.closed = []

    def get_open_trades(self):
        return True, {"trades": self._trades}

    def close_trade(self, oid):
        self.closed.append(oid)
        return True, {}


class _Oanda:
    active = True

    def __init__(self, trades, trade_map=None):
        self._client = _Client(trades)
        self._trade_map = dict(trade_map or {})
        self._lock = threading.Lock()


class _Db:
    def __init__(self, open_trades=None):
        self._open_trades = list(open_trades or [])

    def get_open_trades(self):
        return self._open_trades


def _oanda_time(age_sec: float) -> str:
    """OANDA v20 のナノ秒精度 RFC3339 形式で age_sec 前の openTime を返す。"""
    dt = datetime.now(timezone.utc) - timedelta(seconds=age_sec)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + ".123456789Z"


def _make_trader(trades, *, db_open=None, trade_map=None):
    trader = DemoTrader.__new__(DemoTrader)
    trader._oanda = _Oanda(trades, trade_map=trade_map)
    trader._db = _Db(db_open)
    trader._logs = []
    trader._add_log = trader._logs.append
    return trader


def test_old_orphan_is_closed():
    """年齢 >= 600s の真の孤児は従来どおりクローズされる。"""
    trader = _make_trader([
        {"id": "111", "instrument": "EUR_USD", "currentUnits": "5000",
         "openTime": _oanda_time(3600)},
    ])
    trader._sync_demo_to_oanda()
    assert trader._oanda._client.closed == ["111"]


def test_young_orphan_is_skipped():
    """年齢 < 600s の trade は fill write-back 競合の可能性 → スキップ。"""
    trader = _make_trader([
        {"id": "222", "instrument": "EUR_USD", "currentUnits": "5000",
         "openTime": _oanda_time(60)},
    ])
    trader._sync_demo_to_oanda()
    assert trader._oanda._client.closed == []


def test_missing_or_garbage_open_time_is_skipped():
    """openTime 欠落/parse 不能は fail-safe スキップ (誤クローズ > 遅延クローズ)。"""
    trader = _make_trader([
        {"id": "333", "instrument": "EUR_USD", "currentUnits": "5000"},
        {"id": "444", "instrument": "GBP_USD", "currentUnits": "5000",
         "openTime": "not-a-timestamp"},
    ])
    trader._sync_demo_to_oanda()
    assert trader._oanda._client.closed == []


def test_mapped_trades_are_never_closed():
    """DB / bridge trade_map に載っている trade は年齢に関係なくクローズ対象外。"""
    trader = _make_trader(
        [
            {"id": "555", "instrument": "EUR_USD", "currentUnits": "5000",
             "openTime": _oanda_time(7200)},
            {"id": "666", "instrument": "GBP_USD", "currentUnits": "5000",
             "openTime": _oanda_time(7200)},
        ],
        db_open=[{"oanda_trade_id": "555"}],
        trade_map={"demo-1": "666"},
    )
    trader._sync_demo_to_oanda()
    assert trader._oanda._client.closed == []


def test_boundary_age_just_over_threshold_closes():
    """閾値直上 (600s + margin) はクローズされる — ガードが過剰防御でないこと。"""
    trader = _make_trader([
        {"id": "777", "instrument": "EUR_USD", "currentUnits": "5000",
         "openTime": _oanda_time(DemoTrader._ORPHAN_MIN_AGE_SEC + 30)},
    ])
    trader._sync_demo_to_oanda()
    assert trader._oanda._client.closed == ["777"]
