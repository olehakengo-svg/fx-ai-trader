"""kalman_d7 R2 live stop (2026-10-30、registry t9-kalman-d7-live-n10-ev-check) の契約固定。

対象: knowledge-base/wiki/decisions/kalman-d7-r2-live-stop-2026-10-30.md
- pre-reg LOCK 2026-09-01 §R2「LIVE N>=10 到達で EV<0 → live 停止」が成立
  (clean live N=12、demo EV -1.71p / broker ≈ -3.0p、両基準とも負)。
- LOCK の撤退経路 = env KALMAN_D7_LIVE_ENABLE=0。Render env は autopilot から
  変更できないため、同じ gate (`_kalman_d7_live_eligible`) を code pin
  `_KALMAN_D7_R2_LIVE_STOP` で閉じる。
固定する性質:
  ① pin は True (R2 執行状態)
  ② pin が True の間は env lever が立っていても 3 variant × USD_JPY は live 不適格
  ③ pin を False に戻せば従来の env gate がそのまま生きる (再 live 化 R1 の到達性)
  ④ `_resolve_tier` が KALMAN_D7_LIVE を返さない (shadow 経路へ落ちる = 原則 3)
  ⑤ /api/demo/live-enable-flags の code_pins に観測面がある
  ⑥ LOCK 09-01 の 1000u 契約 / bypass set は不変 (lot 側は触らない)
"""

import inspect
import json

import pytest

import modules.demo_trader as dt
from modules.demo_trader import DemoTrader, KALMAN_D7_MIN_UNITS

KALMAN_TYPES = [
    "kalman_d7_po_dn_flip",
    "kalman_d7_ema75_break",
    "kalman_d7_trail_atr",
]


def test_r2_live_stop_pin_is_true():
    assert DemoTrader._KALMAN_D7_R2_LIVE_STOP is True


@pytest.mark.parametrize("et", KALMAN_TYPES)
def test_live_eligible_false_even_with_env_lever_on(et, monkeypatch):
    """R2 停止中は env lever (import 時 class attr) が True でも live 不適格。"""
    monkeypatch.setattr(DemoTrader, "_KALMAN_D7_LIVE_ENABLE", True)
    assert DemoTrader._kalman_d7_live_eligible(et, "USD_JPY") is False
    assert DemoTrader._kalman_d7_live_eligible(et) is False


@pytest.mark.parametrize("et", KALMAN_TYPES)
def test_env_gate_survives_when_pin_lifted(et, monkeypatch):
    """再 live 化 (R1) は pin を False に戻すだけで従来 gate に復帰する到達性 pin。
    pin を外しても env が立っていなければ live にならない (二重 gate)。"""
    monkeypatch.setattr(DemoTrader, "_KALMAN_D7_R2_LIVE_STOP", False)
    monkeypatch.setattr(DemoTrader, "_KALMAN_D7_LIVE_ENABLE", True)
    assert DemoTrader._kalman_d7_live_eligible(et, "USD_JPY") is True
    assert DemoTrader._kalman_d7_live_eligible(et, "EUR_JPY") is False
    monkeypatch.setattr(DemoTrader, "_KALMAN_D7_LIVE_ENABLE", False)
    assert DemoTrader._kalman_d7_live_eligible(et, "USD_JPY") is False


def test_pin_checked_before_env_in_source():
    """gate の先頭で pin を読む (env 評価より前) — 順序が逆転すると env=1 の
    Render 上で pin が効かない構造に戻り得るため source で固定する。"""
    src = inspect.getsource(DemoTrader._kalman_d7_live_eligible)
    i_pin = src.index("_KALMAN_D7_R2_LIVE_STOP")
    i_env = src.index("_KALMAN_D7_LIVE_ENABLE")
    assert i_pin < i_env


@pytest.mark.parametrize("et", KALMAN_TYPES)
def test_resolve_tier_does_not_return_kalman_live(et, monkeypatch):
    """shadow 蓄積は継続 (原則 3): tier 解決が KALMAN_D7_LIVE に行かない。"""
    monkeypatch.setattr(DemoTrader, "_KALMAN_D7_LIVE_ENABLE", True)
    trader = DemoTrader.__new__(DemoTrader)
    tier = DemoTrader._resolve_tier(trader, et, "USD_JPY", "daytrade")
    assert tier != "KALMAN_D7_LIVE"


def test_flags_endpoint_exposes_r2_pin(flask_client):
    body = json.loads(flask_client.get("/api/demo/live-enable-flags").data)
    assert body["code_pins"]["KALMAN_D7_R2_LIVE_STOP"] is True
    # 既存契約 (env lever の形) は不変
    assert set(body["env_levers"]["KALMAN_D7_LIVE_ENABLE"].keys()) == {
        "effective", "env_now", "drift"}


def test_lock_0901_lot_contract_untouched():
    """LOCK 09-01 の 1000u 契約と bypass set 所属は本 R2 で変更しない
    (撤退は gate 閉鎖のみ、lot 側の凍結値は非接触)。"""
    assert KALMAN_D7_MIN_UNITS == 1000
    assert set(KALMAN_TYPES) <= set(DemoTrader._AGG_KELLY_GATE_MINLOT_BYPASS_TYPES)
    assert set(KALMAN_TYPES) == set(DemoTrader._KALMAN_D7_LIVE_OVERRIDE)
    src = inspect.getsource(dt.DemoTrader._tick_entry)
    assert "KALMAN_D7_MIN_LOT" in src
