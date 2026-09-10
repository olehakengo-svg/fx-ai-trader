"""weekend_gap 執行契約 (B) — pre-reg §2.2 AMENDMENT (user 承認 2026-09-10, rule:R1).

決裁: knowledge-base/wiki/decisions/weekend-gap-execution-contract-r1-packet-2026-09-10.md §4
機構: エンジン発火 21:01 UTC < OANDA 実開場 21:04-21:05 (48/48 実測) →
旧契約 (即時 FOK 1 回) は MARKET_HALTED cancel が決定論的 = live fill 0%。

Covers:
  (a) 繰り下げロジックの境界 — tradeable 直後 SEND / +15 分打ち切り
      (strictly after) / drift +8.0p 放棄 (strictly greater) / 符号規約
  (b) counterfactual pin — 繰り下げ配線 (_weekend_gap_tick の前置条件) を
      殺すと落ちる functional テスト (halt 中に _tick_entry が呼ばれないこと)
  (c) G1 基準 quote = 「実際に fill した送信 attempt の直前 quote」 pin —
      halt-race 再送時に基準が再送直前 quote へ差し替わり、繰下げドリフトが
      G1 に混入しないこと (packet §3 の案 A 棄却理由)
  (d) 限定再送は 1 回のみ / MARKET_HALTED 以外は再送なし / flag なしは再送なし
"""
import inspect
import json
import sys
import types
from datetime import datetime as real_datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
import modules.oanda_bridge as ob
from strategies.daytrade.weekend_gap_fade import (
    WEEKEND_GAP_DRIFT_ABANDON_PIPS,
    WEEKEND_GAP_FADE_ENTRY_TYPE,
    WEEKEND_GAP_HALT_ABANDON_MIN,
    WEEKEND_GAP_HALT_RACE_RESEND_DELAY_SEC,
    WEEKEND_GAP_LATCH_ABANDONED_DRIFT,
    WEEKEND_GAP_LATCH_ABANDONED_HALT,
    WEEKEND_GAP_PIP_SIZE,
    WEEKEND_GAP_QUOTE_MAX_AGE_SEC,
    WEEKEND_GAP_TRADEABLE_POLL_MAX_SEC,
    weekend_gap_adverse_drift_pips,
    weekend_gap_entry_send_decision,
)

# 2026-07-26 (Sunday) 21:00 UTC weekend fixture (test_weekend_gap_fade と同一)
_FRI = pd.Timestamp("2026-07-24 21:00", tz="UTC")
_SUN = _FRI + timedelta(hours=48)


# ══════════════════════════════════════════════════════════════════════
# Frozen constants — AMENDMENT §4 凍結値。変更は R1 (user 承認) のみ。
# ══════════════════════════════════════════════════════════════════════


def test_frozen_contract_b_constants():
    assert WEEKEND_GAP_HALT_ABANDON_MIN == 15                 # §4.2
    assert WEEKEND_GAP_DRIFT_ABANDON_PIPS == 8.0              # §4.3
    assert WEEKEND_GAP_TRADEABLE_POLL_MAX_SEC == 60.0         # §4.1
    assert WEEKEND_GAP_QUOTE_MAX_AGE_SEC == 10.0              # §4.1
    assert WEEKEND_GAP_HALT_RACE_RESEND_DELAY_SEC == 30.0     # §4.4
    assert WEEKEND_GAP_LATCH_ABANDONED_HALT == "ABANDONED_HALT"
    assert WEEKEND_GAP_LATCH_ABANDONED_DRIFT == "ABANDONED_DRIFT"
    # bridge 側の再送待機はモジュール定数 (tests が monkeypatch する契約)
    assert ob.HALT_RACE_RESEND_DELAY_SEC == 30.0


def test_frozen_gates_untouched_by_amendment():
    """AMENDMENT の「不変更 (絶対)」: G1/G2 閾値・cap・1000u・4h exit。"""
    import modules.demo_trader as dt
    from strategies.daytrade.weekend_gap_fade import (
        WEEKEND_GAP_DISASTER_SL_PIPS,
        WEEKEND_GAP_SPREAD_CAP_PIPS,
    )

    assert WEEKEND_GAP_SPREAD_CAP_PIPS == 10.0
    assert WEEKEND_GAP_DISASTER_SL_PIPS == 150.0
    assert dt.WEEKEND_GAP_FADE_UNITS == 1000
    assert dt.WEEKEND_GAP_MAX_HOLD_SEC == 4 * 3600
    assert dt.WEEKEND_GAP_G1_MIN_N == 6
    assert dt.WEEKEND_GAP_G1_SLIPPAGE_PIPS == 2.0
    assert dt.WEEKEND_GAP_G2_MIN_N == 12
    assert dt.WEEKEND_GAP_G2_CUM_NET_PIPS == -60.0


# ══════════════════════════════════════════════════════════════════════
# (a) send decision — 境界 (pure function)
# ══════════════════════════════════════════════════════════════════════


def _decide(*, direction="BUY", instrument="USD_JPY", now=None,
            first_bar=None, tradeable=True, age=1.0,
            sunday_open=150.00, mid=150.00):
    return weekend_gap_entry_send_decision(
        direction=direction, instrument=instrument,
        now_utc=(now if now is not None else _SUN + timedelta(minutes=6)),
        first_bar_ts=(first_bar if first_bar is not None else _SUN),
        tradeable=tradeable, quote_age_sec=age,
        sunday_open=sunday_open, current_mid=mid,
    )


def test_send_on_first_tick_after_tradeable():
    """tradeable 確認直後の最初の評価 tick で SEND (§4.1)。"""
    decision, drift = _decide(tradeable=True, age=0.5)
    assert decision == "SEND"
    assert drift == pytest.approx(0.0)


def test_hold_while_halted_before_cutoff():
    """halt 中 (tradeable=False / pricing 不能 / stale quote) は打ち切り前なら
    HOLD — latch を立てず次 tick で再判定 (§4.1)。"""
    at_14m59 = _SUN + timedelta(minutes=14, seconds=59)
    assert _decide(tradeable=False, now=at_14m59)[0] == "HOLD"
    # pricing 取得不能 (None) = 未確認 → fail-closed で HOLD
    assert _decide(tradeable=None, age=None, now=at_14m59)[0] == "HOLD"
    # stale quote (age >= 10s) では開場確認と認めない (§4.1 quote age <10s)
    assert _decide(tradeable=True, age=10.0, now=at_14m59)[0] == "HOLD"
    assert _decide(tradeable=True, age=None, now=at_14m59)[0] == "HOLD"


def test_halt_abandon_cutoff_strictly_after_15min():
    """打ち切り境界 (§4.2): 初バー ts +15 分「を過ぎても」= strictly after。"""
    exactly = _SUN + timedelta(minutes=WEEKEND_GAP_HALT_ABANDON_MIN)
    assert _decide(tradeable=False, now=exactly)[0] == "HOLD"
    just_after = exactly + timedelta(seconds=1)
    assert _decide(tradeable=False, now=just_after)[0] == \
        WEEKEND_GAP_LATCH_ABANDONED_HALT
    # pricing 不能のまま打ち切り時刻超過も ABANDONED_HALT (未確認は halt 扱い)
    assert _decide(tradeable=None, age=None, now=just_after)[0] == \
        WEEKEND_GAP_LATCH_ABANDONED_HALT


def test_drift_abandon_boundary_strictly_greater_than_8p():
    """放棄境界 (§4.3): fade 方向 adverse drift > +8.0p (ちょうど 8.0p は送信)。"""
    pip = WEEKEND_GAP_PIP_SIZE["USD_JPY"]
    # BUY fade (gap down): mid 上昇 = adverse
    d, drift = _decide(direction="BUY", sunday_open=150.00,
                       mid=150.00 + 8.0 * pip)
    assert d == "SEND" and drift == pytest.approx(8.0)
    d, drift = _decide(direction="BUY", sunday_open=150.00,
                       mid=150.00 + 8.01 * pip)
    assert d == WEEKEND_GAP_LATCH_ABANDONED_DRIFT
    assert drift == pytest.approx(8.01)
    # SELL fade (gap up): mid 下落 = adverse
    d, drift = _decide(direction="SELL", sunday_open=150.00,
                       mid=150.00 - 8.1 * pip)
    assert d == WEEKEND_GAP_LATCH_ABANDONED_DRIFT
    assert drift == pytest.approx(8.1)
    # favorable 方向 (gap がさらに走った) は境界なし — 大きくても SEND
    d, drift = _decide(direction="SELL", sunday_open=150.00,
                       mid=150.00 + 30.0 * pip)
    assert d == "SEND" and drift == pytest.approx(-30.0)


def test_adverse_drift_sign_convention_both_pip_scales():
    """符号規約: fade 方向 (Friday close へ戻る向き) の既往ドリフトが正。"""
    # USD_JPY (pip 0.01)
    assert weekend_gap_adverse_drift_pips(
        "BUY", 150.00, 150.05, "USD_JPY") == pytest.approx(5.0)
    assert weekend_gap_adverse_drift_pips(
        "SELL", 150.00, 150.05, "USD_JPY") == pytest.approx(-5.0)
    # EUR_USD (pip 0.0001)
    assert weekend_gap_adverse_drift_pips(
        "SELL", 1.1030, 1.1025, "EUR_USD") == pytest.approx(5.0)
    assert weekend_gap_adverse_drift_pips(
        "BUY", 1.0970, 1.0965, "EUR_USD") == pytest.approx(-5.0)


# ══════════════════════════════════════════════════════════════════════
# (b) counterfactual pin — scoped runner の繰り下げ配線
#     この配線 (_weekend_gap_tick 内の前置条件) を削除すると、halt 中の
#     21:06 tick で _tick_entry が呼ばれてしまい ↓ のテストが落ちる。
# ══════════════════════════════════════════════════════════════════════


def _mk_wg_df(instrument="USD_JPY", fri_close=150.00, gap_pips=-25.0):
    pip = WEEKEND_GAP_PIP_SIZE[instrument]
    idx = pd.date_range("2026-07-23 00:00", "2026-07-24 20:45",
                        freq="15min", tz="UTC")
    n = len(idx)
    df = pd.DataFrame(
        {"Open": np.full(n, fri_close), "High": np.full(n, fri_close + pip),
         "Low": np.full(n, fri_close - pip), "Close": np.full(n, fri_close)},
        index=idx)
    sun_open = fri_close + gap_pips * pip
    sun_row = pd.DataFrame(
        {"Open": [sun_open], "High": [sun_open + pip],
         "Low": [sun_open - pip], "Close": [sun_open]}, index=[_SUN])
    return pd.concat([df, sun_row]), sun_open


class _FakeKvDB:
    def __init__(self):
        self.kv = {}

    def get_system_kv(self, key, default=""):
        return self.kv.get(key, default)

    def set_system_kv(self, key, value):
        self.kv[key] = value


def _runner_harness():
    class _RunnerHarness(demo_trader_mod.DemoTrader):
        def __init__(self):
            self._db = _FakeKvDB()
            self.logs = []
            self.tick_entry_calls = []

        def _add_log(self, msg):
            self.logs.append(msg)

        def _tick_entry(self, mode, cfg, sig, tf, instrument):
            self.tick_entry_calls.append(
                {"mode": mode, "sig": sig, "instrument": instrument})

    return _RunnerHarness()


def _run_weekend_gap_tick(monkeypatch, *, now_utc, pricing,
                          gap_pips=-25.0, pricing_raises=False):
    """_weekend_gap_tick を固定時刻・固定 pricing で 1 tick 実行する。"""
    df, sun_open = _mk_wg_df(gap_pips=gap_pips)

    fake_app = types.ModuleType("app")
    fake_app.fetch_ohlcv = lambda symbol, period="5d", interval="15m": df
    fake_app.add_indicators = lambda d: d
    monkeypatch.setitem(sys.modules, "app", fake_app)

    class _PinnedDT(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return now_utc if tz else now_utc.replace(tzinfo=None)

    monkeypatch.setattr(demo_trader_mod, "datetime", _PinnedDT)

    if pricing_raises:
        def _ps(_inst):
            raise RuntimeError("pricing endpoint down")
    else:
        def _ps(_inst):
            return dict(pricing) if pricing is not None else {}
    monkeypatch.setattr(data_mod, "fetch_oanda_pricing_state", _ps)

    h = _runner_harness()
    cfg = {"instrument": "USD_JPY", "symbol": "USDJPY=X",
           "period": "5d", "tf": "15m"}
    h._weekend_gap_tick("daytrade", cfg)
    return h, sun_open


def _pricing(tradeable=True, age=1.0, mid=149.75):
    return {"tradeable": tradeable, "quote_age_sec": age,
            "bid": mid - 0.01, "ask": mid + 0.01, "mid": mid,
            "time": "2026-07-26T21:05:00.000000000Z"}


def test_counterfactual_halted_tick_does_not_reach_tick_entry(monkeypatch):
    """counterfactual kill pin: 21:06 (halt 中) の評価 tick は _tick_entry に
    到達しない + latch も立てない (§4.1 HOLD)。繰り下げ配線を殺すと、この
    tick は旧契約どおり即時に _tick_entry へ流れて本テストが落ちる。"""
    h, _ = _run_weekend_gap_tick(
        monkeypatch, now_utc=real_datetime(2026, 7, 26, 21, 6, tzinfo=timezone.utc),
        pricing=_pricing(tradeable=False))
    assert h.tick_entry_calls == [], (
        "halt 中の qualifying signal が _tick_entry に到達した — "
        "執行契約(B) の繰り下げ配線が死んでいる")
    assert h._db.kv == {}, "HOLD 中に latch を立ててはならない (§4.1)"


def test_counterfactual_pricing_unavailable_holds(monkeypatch):
    """pricing 取得不能 (例外) も未確認 = HOLD (fail-closed、打ち切り前)。"""
    h, _ = _run_weekend_gap_tick(
        monkeypatch, now_utc=real_datetime(2026, 7, 26, 21, 6, tzinfo=timezone.utc),
        pricing=None, pricing_raises=True)
    assert h.tick_entry_calls == []
    assert h._db.kv == {}


def test_tradeable_confirmed_first_tick_sends(monkeypatch):
    """実開場確認後の最初の評価 tick で送信経路へ (sig marker + 観測 reason)。"""
    h, sun_open = _run_weekend_gap_tick(
        monkeypatch, now_utc=real_datetime(2026, 7, 26, 21, 6, tzinfo=timezone.utc),
        pricing=_pricing(tradeable=True, age=1.0, mid=sun_open_for()))
    assert len(h.tick_entry_calls) == 1
    sig = h.tick_entry_calls[0]["sig"]
    assert sig.get("_wg_exec_send_ok") is True
    assert "_wg_exec_abandon" not in sig
    meta = sig["_wg_exec_contract"]
    assert meta["decision"] == "SEND"
    assert meta["tradeable"] is True
    assert meta["quote_age_sec"] == 1.0
    # §4.6 観測強化: demo row へ reasons 経由で永続化
    assert any(r.startswith("[WG_EXEC_B]") for r in sig["reasons"])


def sun_open_for(fri_close=150.00, gap_pips=-25.0, instrument="USD_JPY"):
    return fri_close + gap_pips * WEEKEND_GAP_PIP_SIZE[instrument]


def test_halt_abandon_after_cutoff_records_shadow_marker(monkeypatch):
    """+15 分超で halt 継続 → ABANDONED_HALT marker 付きで _tick_entry へ
    (shadow row 記録 = 分母保存、§4.2)。"""
    h, _ = _run_weekend_gap_tick(
        monkeypatch,
        now_utc=real_datetime(2026, 7, 26, 21, 16, tzinfo=timezone.utc),
        pricing=_pricing(tradeable=False))
    assert len(h.tick_entry_calls) == 1
    sig = h.tick_entry_calls[0]["sig"]
    assert sig.get("_wg_exec_abandon") == WEEKEND_GAP_LATCH_ABANDONED_HALT
    assert "_wg_exec_send_ok" not in sig


def test_drift_abandon_records_shadow_marker(monkeypatch):
    """tradeable でも fade 方向 adverse drift > +8.0p → ABANDONED_DRIFT (§4.3)。
    BUY fade なので mid が sunday_open より +9p 上 = adverse。"""
    pip = WEEKEND_GAP_PIP_SIZE["USD_JPY"]
    drifted_mid = sun_open_for() + 9.0 * pip
    h, _ = _run_weekend_gap_tick(
        monkeypatch, now_utc=real_datetime(2026, 7, 26, 21, 6, tzinfo=timezone.utc),
        pricing=_pricing(tradeable=True, age=1.0, mid=drifted_mid))
    assert len(h.tick_entry_calls) == 1
    sig = h.tick_entry_calls[0]["sig"]
    assert sig.get("_wg_exec_abandon") == WEEKEND_GAP_LATCH_ABANDONED_DRIFT
    assert sig["_wg_exec_contract"]["drift_pips"] == pytest.approx(9.0, abs=0.1)


# ══════════════════════════════════════════════════════════════════════
# _tick_entry 側の配線 pin (backstop / latch / bridge param) — code-pin
# ══════════════════════════════════════════════════════════════════════


def test_tick_entry_backstop_and_latch_wiring_pins():
    import modules.demo_trader as dt

    src = inspect.getsource(dt.DemoTrader._tick_entry)
    # backstop: tradeable 未確認 sig の live 送信は row/latch なしで block
    assert '_block("weekend_gap_tradeable_unconfirmed")' in src
    assert '_wg_exec_send_ok' in src
    # backstop は OANDA 送信より前に置かれている
    assert (src.index('_block("weekend_gap_tradeable_unconfirmed")')
            < src.index("self._oanda.open_trade"))
    # 放棄 marker → shadow 固定 + 放棄 cause
    assert '_wg_abandon = str(sig.get("_wg_exec_abandon") or "")' in src
    assert "weekend_gap_exec_abandon" in src
    # latch 状態に ABANDONED_* を永続化 (§4.2/§4.3)
    assert "_wg_abandon if _wg_abandon" in src
    # bridge へ halt-race 限定再送 flag を wg のみ配線 (§4.4)
    assert "halt_race_resend=(" in src
    # 既存契約の不変更 pin: max_attempts=1 は維持 (§4.4 の再送は bridge 内
    # の MARKET_HALTED 限定条項であり、transient retry の復活ではない)
    assert "max_attempts=(1 if entry_type == WEEKEND_GAP_FADE_ENTRY_TYPE" in src


def test_runner_precondition_wiring_pins():
    import modules.demo_trader as dt

    src = inspect.getsource(dt.DemoTrader._weekend_gap_tick)
    # 前置条件は build_weekend_gap_sig / _tick_entry より前
    assert "weekend_gap_entry_send_decision" in src
    assert (src.index("weekend_gap_entry_send_decision(")
            < src.index("sig = build_weekend_gap_sig"))
    # HOLD は latch なしで return (§4.1)
    assert 'if _wg_decision == "HOLD":' in src
    # §4.6 観測ログ
    assert "[WEEKEND_GAP][EXEC_B]" in src


def test_latch_docstring_states_include_abandoned():
    import modules.demo_trader as dt

    doc = inspect.getdoc(dt.DemoTrader._weekend_gap_latch_set) or ""
    assert "ABANDONED_HALT" in doc and "ABANDONED_DRIFT" in doc


# ══════════════════════════════════════════════════════════════════════
# (c)(d) bridge halt-race 限定再送 + G1 基準 quote pin (functional)
# ══════════════════════════════════════════════════════════════════════


_HALTED_RESP = (True, {
    "orderCreateTransaction": {"id": "1001", "type": "MARKET_ORDER"},
    "orderCancelTransaction": {"id": "1002", "type": "ORDER_CANCEL",
                               "reason": "MARKET_HALTED"},
})
_OTHER_CANCEL_RESP = (True, {
    "orderCreateTransaction": {"id": "1001", "type": "MARKET_ORDER"},
    "orderCancelTransaction": {"id": "1002", "type": "ORDER_CANCEL",
                               "reason": "INSUFFICIENT_LIQUIDITY"},
})


def _fill_resp(price="150.030", trade_id="90001"):
    return (True, {
        "orderFillTransaction": {"price": price,
                                 "tradeOpened": {"tradeID": trade_id}},
    })


class _FakeClient:
    def __init__(self, order_responses, price_response=None):
        self.order_responses = list(order_responses)
        self.order_calls = []
        self.price_calls = []
        self.price_response = price_response or (True, {"prices": [{
            "time": "2026-07-26T21:05:20.000000000Z", "tradeable": True,
            "bids": [{"price": "150.010"}], "asks": [{"price": "150.020"}],
        }]})

    def market_order(self, **kw):
        self.order_calls.append(kw)
        if self.order_responses:
            return self.order_responses.pop(0)
        raise AssertionError(
            "market_order called more times than the contract allows "
            "(§4.4: max 2 sends)")

    def get_price(self, instrument):
        self.price_calls.append(instrument)
        return self.price_response


class _SlipDB:
    """bridge が触る DB 面のみの fake (pending ops + slippage 記録)。"""

    def __init__(self):
        self.slippage_writes = []
        self.pending = []

    def pending_op_create(self, *a, **kw):
        self.pending.append(("create", a, kw))
        return 1

    def pending_op_mark_done(self, *a, **kw):
        self.pending.append(("done", a, kw))

    def pending_op_mark_failed(self, *a, **kw):
        self.pending.append(("failed", a, kw))

    def update_trade_slippage(self, trade_id, slippage_pips):
        self.slippage_writes.append((trade_id, slippage_pips))

    def add_oanda_audit(self, **kw):
        pass


def _run_bridge_open(monkeypatch, *, order_responses, price_response=None,
                     halt_race_resend=True, signal_price=150.000,
                     max_attempts=1):
    monkeypatch.setenv("OANDA_LIVE", "true")
    monkeypatch.setattr(ob, "HALT_RACE_RESEND_DELAY_SEC", 0.0)
    db = _SlipDB()
    b = ob.OandaBridge(db=db)
    monkeypatch.setattr(type(b), "active", property(lambda self: True))
    monkeypatch.setattr(b, "is_mode_allowed", lambda _m: True)
    monkeypatch.setattr(b, "_check_daily_loss_gate", lambda: (False, 0.0))
    monkeypatch.setattr(b, "_add_audit", lambda **kw: None)
    client = _FakeClient(order_responses, price_response=price_response)
    b._client = client
    fired = []
    monkeypatch.setattr(b, "_fire", lambda fn: fired.append(fn))
    accepted = b.open_trade(
        demo_trade_id="WG-T1", direction="BUY", sl=148.50, tp=None,
        mode="daytrade", instrument="USD_JPY", units=1000,
        signal_price=signal_price,
        entry_type=WEEKEND_GAP_FADE_ENTRY_TYPE, skip_sent_audit=True,
        max_attempts=max_attempts, record_fill_slippage=True,
        halt_race_resend=halt_race_resend,
    )
    assert accepted is True and len(fired) == 1
    fired[0]()  # run the background send synchronously
    return client, db


def test_halt_race_single_resend_then_fill_and_g1_basis_swap(monkeypatch):
    """§4.4/§4.5 の本丸: MARKET_HALTED cancel (race) → 30s 後 1 回だけ再送。
    fill slippage の基準 quote は「実際に fill した送信 attempt (= 再送) の
    直前 quote」へ差し替わる — 初回 21:01 quote (signal_price=150.000) に
    固定したままだと繰下げドリフト +3.0p が G1 に混入する (案 A の欠陥)。"""
    client, db = _run_bridge_open(
        monkeypatch,
        order_responses=[_HALTED_RESP, _fill_resp(price="150.030")],
        signal_price=150.000)
    assert len(client.order_calls) == 2, "再送はちょうど 1 回 (計 2 送信)"
    assert client.price_calls == ["USD_JPY"], "再送直前に基準 quote を再取得"
    assert len(db.slippage_writes) == 1
    trade_id, slip = db.slippage_writes[0]
    assert trade_id == "WG-T1"
    # 基準 = 再送直前 ask 150.020 → slip = (150.030 - 150.020) * 100 = +1.0p。
    # 旧基準 (150.000) なら +3.0p — 差し替えが死ぬとこの assert が落ちる。
    assert slip == pytest.approx(1.0, abs=0.01)
    assert slip != pytest.approx(3.0, abs=0.01)


def test_halt_race_resend_is_once_only(monkeypatch):
    """2 回連続 MARKET_HALTED → 計 2 送信で打ち止め (3 回目なし)。_FakeClient
    は 3 回目の market_order で AssertionError を上げる = 上限の直接 pin。"""
    client, db = _run_bridge_open(
        monkeypatch,
        order_responses=[_HALTED_RESP, _HALTED_RESP])
    assert len(client.order_calls) == 2
    assert db.slippage_writes == []  # fill なし → G1 入力なし


def test_no_resend_without_flag(monkeypatch):
    """halt_race_resend=False (wg 以外の全戦略) は従来どおり再送なし。"""
    client, db = _run_bridge_open(
        monkeypatch,
        order_responses=[_HALTED_RESP],
        halt_race_resend=False)
    assert len(client.order_calls) == 1
    assert client.price_calls == []
    assert db.slippage_writes == []


def test_no_resend_on_other_cancel_reason(monkeypatch):
    """MARKET_HALTED 以外の cancel reason は限定再送の対象外 (§4.4)。"""
    client, db = _run_bridge_open(
        monkeypatch,
        order_responses=[_OTHER_CANCEL_RESP])
    assert len(client.order_calls) == 1
    assert db.slippage_writes == []


def test_no_resend_on_transport_error(monkeypatch):
    """ok=False (transient/network) は §4.4 の対象外 — max_attempts=1 の
    pre-reg §2.2 リトライ禁止が維持される。"""
    client, db = _run_bridge_open(
        monkeypatch,
        order_responses=[(False, {"error": 503, "message": "unavailable"})])
    assert len(client.order_calls) == 1
    assert db.slippage_writes == []


def test_basis_quote_refresh_failure_keeps_original_basis(monkeypatch):
    """再送直前 quote が取れない場合は初回基準 (signal_price) を保持 —
    G1 入力が空 (0) に潰れない。"""
    client, db = _run_bridge_open(
        monkeypatch,
        order_responses=[_HALTED_RESP, _fill_resp(price="150.030")],
        price_response=(False, {"error": "timeout"}),
        signal_price=150.000)
    assert len(client.order_calls) == 2
    assert len(db.slippage_writes) == 1
    _, slip = db.slippage_writes[0]
    assert slip == pytest.approx(3.0, abs=0.01)  # 基準 = 初回 signal_price


def test_no_resend_when_first_send_fills(monkeypatch):
    """正常 fill (halt-race なし) は従来どおり 1 送信、基準 = 送信時 quote
    (signal_price) — 既存 G1 semantics の非回帰 pin。"""
    client, db = _run_bridge_open(
        monkeypatch,
        order_responses=[_fill_resp(price="150.004")],
        signal_price=150.000)
    assert len(client.order_calls) == 1
    assert client.price_calls == []
    _, slip = db.slippage_writes[0]
    assert slip == pytest.approx(0.4, abs=0.01)


def test_bridge_signature_defaults():
    sig = inspect.signature(ob.OandaBridge.open_trade)
    assert sig.parameters["halt_race_resend"].default is False
    assert sig.parameters["max_attempts"].default == 3
    assert sig.parameters["record_fill_slippage"].default is False


# ══════════════════════════════════════════════════════════════════════
# fetch_oanda_pricing_state (read-only 実開場確認, §4.1)
# ══════════════════════════════════════════════════════════════════════


class _FakePricingClient:
    configured = True

    def __init__(self, ok=True, prices=None):
        self._ok = ok
        self._prices = prices

    def get_price(self, instrument):
        if not self._ok:
            return False, {"error": 503}
        return True, {"prices": self._prices}


def test_fetch_oanda_pricing_state_parses_tradeable_and_age(monkeypatch):
    # 2 秒過去の timestamp で決定的な正の age にする (wall-clock の端数に非依存)
    now = real_datetime.now(timezone.utc) - timedelta(seconds=2)
    # OANDA v20 はナノ秒 9 桁を返す — parse できること
    ts = now.strftime("%Y-%m-%dT%H:%M:%S") + ".123456789Z"
    monkeypatch.setattr(
        data_mod, "_get_oanda_client",
        lambda: _FakePricingClient(prices=[{
            "time": ts, "tradeable": True,
            "bids": [{"price": "150.010"}], "asks": [{"price": "150.016"}],
        }]))
    st = data_mod.fetch_oanda_pricing_state("USD_JPY")
    assert st["tradeable"] is True
    assert 0.0 <= st["quote_age_sec"] < 5.0
    assert st["bid"] == pytest.approx(150.010)
    assert st["ask"] == pytest.approx(150.016)
    assert st["mid"] == pytest.approx(150.013)


def test_fetch_oanda_pricing_state_halted_and_failures(monkeypatch):
    now = real_datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%S") + ".000000000Z"
    monkeypatch.setattr(
        data_mod, "_get_oanda_client",
        lambda: _FakePricingClient(prices=[{
            "time": ts, "tradeable": False,
            "bids": [{"price": "150.010"}], "asks": [{"price": "150.016"}],
        }]))
    st = data_mod.fetch_oanda_pricing_state("USD_JPY")
    assert st["tradeable"] is False
    # API 失敗 → 空 dict (呼び出し側は未確認として fail-closed)
    monkeypatch.setattr(
        data_mod, "_get_oanda_client", lambda: _FakePricingClient(ok=False))
    assert data_mod.fetch_oanda_pricing_state("USD_JPY") == {}
    # 壊れた timestamp → 空 dict (鮮度検証不能を「新鮮」と誤認しない)
    monkeypatch.setattr(
        data_mod, "_get_oanda_client",
        lambda: _FakePricingClient(prices=[{
            "time": "not-a-time", "tradeable": True,
            "bids": [{"price": "1"}], "asks": [{"price": "1"}],
        }]))
    assert data_mod.fetch_oanda_pricing_state("USD_JPY") == {}


def test_fetch_oanda_pricing_state_clamps_clock_skew(monkeypatch):
    """OANDA サーバ時刻の微小 skew で quote_ts が「未来」でも age は 0 に
    クランプ (負の age で鮮度判定が恒久 fail-closed しない)。"""
    future = real_datetime.now(timezone.utc) + timedelta(seconds=1)
    ts = future.strftime("%Y-%m-%dT%H:%M:%S") + ".000000000Z"
    monkeypatch.setattr(
        data_mod, "_get_oanda_client",
        lambda: _FakePricingClient(prices=[{
            "time": ts, "tradeable": True,
            "bids": [{"price": "150.010"}], "asks": [{"price": "150.016"}],
        }]))
    st = data_mod.fetch_oanda_pricing_state("USD_JPY")
    assert st["quote_age_sec"] == 0.0
    # 決定関数側の鮮度ガード (0 <= age < 10s) をそのまま通過できる
    d, _ = _decide(tradeable=True, age=st["quote_age_sec"])
    assert d == "SEND"
