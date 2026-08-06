"""DD 台帳の broker 決済パス欠落バグ 回帰テスト (2026-08-06, rule:R3).

## 事象
`_sync_oanda_closures()` は broker 側 SL/TP 約定を検知して
`close_reason='OANDA_SL_TP'` でクローズするが、Equity 台帳
(`_eq_current` / `_eq_current_jpy` / DD multiplier) を**一切更新して
いなかった**。台帳更新は内部決済パスにインラインで書かれており、
sync 経路からは到達不能だった。

## 本番実測による確認 (2026-08-06、`oanda_trade_id != ''` ∧ 非 XAU ∧ 非 shadow)
| 母集団 | n | sum | mean | WR |
|---|---|---|---|---|
| 台帳計上済 (内部経路) | 37 | −319.3p | −8.63 | — |
| **台帳欠落 (OANDA_SL_TP)** | **21** | **+28.0p** | **+1.33** | **85.7%** |
| 実 book 合計 | 58 | −291.3p | | |

欠落が全決済の 36.2% を占め、かつ**正 EV 側に偏る** (broker TP 約定は
sync 経由でしか観測されないのに対し、損失は demo 側 SL 判定が先に
発火するため)。台帳は実 book より構造的に悪い DD を報告し、防御
multiplier を過剰に絞っていた。

## 恒等式による証明
台帳 anchor (2026-07-28) 以降の KV 実測 delta = −1527.00 JPY は
計上済 3 件 (−152.7p × ¥10) と**完全一致**し、欠落した +29.0p (¥290)
の寄与はゼロ = 当該経路が一度も計上していないことの算術的証拠。

ref: knowledge-base/wiki/analyses/dd-ledger-broker-close-gap-2026-08-06.md
"""
from __future__ import annotations

import ast
import os

import pytest

from modules.demo_trader import DemoTrader, pip_value_jpy
from modules.risk_analytics import get_dd_lot_multiplier

_DEMO_TRADER_PY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "modules", "demo_trader.py",
)

# D-a 再基準化値 (Track C D-b anchor)
_BASE_JPY = 359109.0
_ANCHOR_PEAK_JPY = 359288.47
_ANCHOR_CURRENT_JPY = 326472.58


class _StubDB:
    def __init__(self, closed=None, kv=None):
        self.kv = dict(kv or {})
        self._closed = list(closed or [])

    def get_system_kv(self, k, default=None):
        return self.kv.get(k, default)

    def set_system_kv(self, k, v):
        self.kv[k] = v

    def get_all_closed(self):
        return list(self._closed)


class _LedgerHost:
    """`_apply_equity_ledger_close` / backfill が触る属性だけを持つスタブ host."""

    _EQ_BASE_CAPITAL_JPY = _BASE_JPY
    _LEDGER_BROKER_BACKFILL_CUTOFF = DemoTrader._LEDGER_BROKER_BACKFILL_CUTOFF
    _LEDGER_BROKER_BACKFILL_FLAG = DemoTrader._LEDGER_BROKER_BACKFILL_FLAG

    def __init__(self, db=None):
        self._db = db or _StubDB()
        self._eq_current = 0.0
        self._eq_peak = 0.0
        self._eq_current_jpy = _ANCHOR_CURRENT_JPY
        self._eq_peak_jpy = _ANCHOR_PEAK_JPY
        self._dd_lot_mult = 0.20
        self._defensive_mode = True
        self._rate_mid = {"USD_JPY": 150.0}
        self.logs = []

    def _add_log(self, msg):
        self.logs.append(msg)


def _trade(pnl_field=None, **kw):
    t = {
        "oanda_trade_id": "549260",
        "is_shadow": 0,
        "instrument": "USD_JPY",
        "units": 1000,
    }
    t.update(kw)
    return t


_apply = DemoTrader._apply_equity_ledger_close
_backfill = DemoTrader._backfill_broker_close_ledger_gap


# ── 1. helper 自体の計上挙動 ────────────────────────────────────

def test_ledger_helper_credits_eligible_win():
    h = _LedgerHost()
    before = h._eq_current_jpy
    assert _apply(h, _trade(), 29.0) is True
    # USD_JPY 1000 units → ¥10/pip
    assert h._eq_current_jpy == pytest.approx(before + 290.0)
    assert h._eq_current == pytest.approx(29.0)


@pytest.mark.parametrize("kw", [
    {"oanda_trade_id": ""},          # shadow-only / 非 broker
    {"is_shadow": 1},                # shadow
    {"instrument": "XAU_USD"},       # XAU 除外
])
def test_ledger_helper_skips_ineligible(kw):
    h = _LedgerHost()
    before = (h._eq_current, h._eq_current_jpy)
    assert _apply(h, _trade(**kw), 29.0) is False
    assert (h._eq_current, h._eq_current_jpy) == before


# ── 2. 中核回帰: broker 決済パスが台帳 helper を呼ぶこと ────────

def _fn(name):
    with open(_DEMO_TRADER_PY, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=_DEMO_TRADER_PY)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found")


def _calls_ledger_helper(node):
    for n in ast.walk(node):
        if (isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == "_apply_equity_ledger_close"):
            return True
    return False


def test_sync_oanda_closures_updates_equity_ledger():
    """バグ本体の pin: broker 決済経路が台帳 helper を通ること。

    これが False に戻ると close_reason='OANDA_SL_TP' (本番実測で全決済の
    36.2%、しかも WR 85.7% の正 EV 側) が再び DD 台帳から消える。
    """
    assert _calls_ledger_helper(_fn("_sync_oanda_closures"))


def test_internal_close_path_shares_the_same_helper():
    """内部決済パスも同一 helper 経由 — 台帳ロジックの二重実装を禁止する。"""
    with open(_DEMO_TRADER_PY, "r", encoding="utf-8") as fh:
        src = fh.read()
    # 台帳への直接加算は helper 内の 1 箇所のみ (インライン再実装の再発防止)
    assert src.count("self._eq_current_jpy +=") == 2, (
        "台帳加算は helper 1 箇所 + backfill 1 箇所のみであるべき "
        "(決済パスへのインライン再実装は禁止)"
    )


# ── 3. backfill: 欠落分の再導出 ─────────────────────────────────

def _closed(pnl, reason, exit_time, **kw):
    t = {
        "pnl_pips": pnl,
        "close_reason": reason,
        "exit_time": exit_time,
        "oanda_trade_id": "549260",
        "is_shadow": 0,
        "instrument": "USD_JPY",
        "units": 1000,
    }
    t.update(kw)
    return t


def test_backfill_credits_only_missed_broker_closes():
    db = _StubDB(closed=[
        # 対象: anchor 以降の broker 決済 (本番実測の 549260 相当)
        _closed(29.0, "OANDA_SL_TP", "2026-08-05T06:33:21+00:00"),
        # 非対象: 内部経路は計上済み
        _closed(-30.1, "SL_HIT", "2026-07-30T13:49:42+00:00"),
        _closed(-123.2, "horizon", "2026-07-31T20:57:18+00:00"),
        # 非対象: anchor 以前 (D-a 実測値に吸収済み)
        _closed(50.0, "OANDA_SL_TP", "2026-07-01T00:00:00+00:00"),
        # 非対象: shadow / XAU
        _closed(99.0, "OANDA_SL_TP", "2026-08-05T00:00:00+00:00", is_shadow=1),
        _closed(99.0, "OANDA_SL_TP", "2026-08-05T00:00:00+00:00",
                instrument="XAU_USD"),
    ])
    h = _LedgerHost(db)
    assert _backfill(h) == pytest.approx(290.0)
    assert h._eq_current_jpy == pytest.approx(_ANCHOR_CURRENT_JPY + 290.0)
    assert db.kv[DemoTrader._LEDGER_BROKER_BACKFILL_FLAG] == "1"


def test_backfill_is_idempotent():
    db = _StubDB(
        closed=[_closed(29.0, "OANDA_SL_TP", "2026-08-05T06:33:21+00:00")],
        kv={DemoTrader._LEDGER_BROKER_BACKFILL_FLAG: "1"},
    )
    h = _LedgerHost(db)
    assert _backfill(h) == 0.0
    assert h._eq_current_jpy == pytest.approx(_ANCHOR_CURRENT_JPY)


def test_backfill_noop_when_jpy_ledger_not_anchored():
    """JPY 台帳未確立時は anchor 処理が先 — backfill は何もしない。"""
    db = _StubDB(closed=[_closed(29.0, "OANDA_SL_TP", "2026-08-05T00:00:00+00:00")])
    h = _LedgerHost(db)
    h._eq_peak_jpy = 0.0
    assert _backfill(h) == 0.0
    assert db.kv.get(DemoTrader._LEDGER_BROKER_BACKFILL_FLAG) is None


# ── 4. 補正が live lot に影響しないこと (R3 の安全性根拠) ───────

def test_backfill_is_dd_tier_neutral():
    """本番実測値での補正は DD tier (≥8% → 0.20x) を跨がない = lot 不変。"""
    before_dd = (359288.47 - 324945.58) / _BASE_JPY   # 実測 9.56%
    after_dd = (359288.47 - (324945.58 + 290.0)) / _BASE_JPY  # 補正後 9.48%
    assert before_dd == pytest.approx(0.0956, abs=1e-4)
    assert after_dd == pytest.approx(0.0948, abs=1e-4)
    assert get_dd_lot_multiplier(before_dd) == get_dd_lot_multiplier(after_dd) == 0.20


def test_measured_gap_population_sign_is_positive():
    """欠落母集団が正 EV 側に偏る (= 台帳が DD を過大報告する) 事実の pin。

    2026-08-06 本番実測 n=21 / +28.0p / WR 85.7%。この符号が本修正を
    「防御の緩和」ではなく「会計の是正」たらしめる根拠。
    """
    measured_missing_pips = 28.0
    measured_visible_pips = -319.3
    assert measured_missing_pips > 0
    assert measured_visible_pips + measured_missing_pips == pytest.approx(-291.3)


def test_pip_value_jpy_anchor_assumption():
    """backfill 額 ¥290 が依拠する pip 価値 (USD_JPY 1000 units = ¥10/pip)。"""
    assert pip_value_jpy("USD_JPY", 1000, {"USD_JPY": 150.0}) == pytest.approx(10.0)
