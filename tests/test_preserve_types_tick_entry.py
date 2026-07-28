"""Regression pin (rule:R3 2026-07-28): _1H_PRESERVE_SLTP entry types must
traverse _tick_entry to the OANDA send decision without UnboundLocalError.

Chronic bug (2026-04-10 .. 2026-07-28, forensic-confirmed): `_is_xau_inst`
was assigned INSIDE the `if entry_type not in _1H_PRESERVE_SLTP:` SL-recompute
block. Every preserve-type signal (weekend_gap_fade / hull_donchian_fade /
keltner_squeeze_breakout / donchian_momentum_breakout / price_shock_rev
tier-1 / sweep_reversion_eurgbp_late) skipped that block, then crashed with
UnboundLocalError at the unconditional lot-sizing references
(`_adjusted_units = 1 if _is_xau_inst else 1000` etc.) — AFTER the DB row
insert and the weekend_gap latch, BEFORE the OANDA bridge send. Result:
3.5 months of silent live-kill producing untagged shadow-like rows.

Lesson: knowledge-base/wiki/lessons/lesson-preserve-sltp-unboundlocal-2026-07-28.md

Test design:
  - The preserve set is extracted from the _tick_entry source via ast and
    evaluated against module globals, so any NEW preserve type is
    automatically parametrized. A new type without a config entry below
    fails loudly (KeyError) — add a config, do not skip: pure-function
    tests alone cannot guarantee the send path (that is how this bug
    survived 3.5 months).
  - Each synthetic sig is driven through the REAL _tick_entry (same mock
    pattern as tests/test_bridge_send_accept_contract.py) and must reach
    the DB row insert; there is no early `return` between the insert and
    the formerly-crashing lot-sizing reference, so
    "row inserted AND no exception" == the reference executed.
  - rnb_support_bounce is in the preserve set but NOT in QUALIFIED_TYPES:
    it is blocked at unknown_type upstream of the bug site. The test pins
    that current behavior instead of asserting a row.
"""
from __future__ import annotations

import ast
import inspect
import textwrap
import uuid
from datetime import datetime as real_datetime, timezone
from unittest.mock import MagicMock

import pytest

import modules.data as data_mod
import modules.demo_trader as demo_trader_mod
from modules.demo_db import DemoDB
from modules.demo_trader import DemoTrader


# ── Extract _1H_PRESERVE_SLTP from the _tick_entry source ─────────────────


def _resolve_set_node(node: ast.Set) -> frozenset:
    """Resolve an ast.Set of string constants / starred module-level names /
    module-level name references without eval()."""
    resolved: set = set()
    for elt in node.elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            resolved.add(elt.value)
        elif isinstance(elt, ast.Starred) and isinstance(elt.value, ast.Name):
            resolved.update(getattr(demo_trader_mod, elt.value.id))
        elif isinstance(elt, ast.Name):
            resolved.add(getattr(demo_trader_mod, elt.id))
        else:
            raise AssertionError(
                f"unsupported element in _1H_PRESERVE_SLTP: {ast.dump(elt)}")
    return frozenset(resolved)


def _extract_preserve_types() -> frozenset:
    src = textwrap.dedent(inspect.getsource(DemoTrader._tick_entry))
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Name)
                        and target.id == "_1H_PRESERVE_SLTP"
                        and isinstance(node.value, ast.Set)):
                    return _resolve_set_node(node.value)
    raise AssertionError("_1H_PRESERVE_SLTP assignment not found in _tick_entry")


PRESERVE_TYPES = _extract_preserve_types()

# London-session Thursday (matches test_bridge_send_accept_contract.py) for
# all types except weekend_gap_fade, which requires the Sunday >=21:00 UTC
# entry window (weekend_key_for).
_LONDON_THU = real_datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
_SUNDAY_OPEN = real_datetime(2026, 7, 26, 21, 6, tzinfo=timezone.utc)

# Per-type driving config. `expect` values:
#   "row"     — must insert a demo_trades row (reaches/passes the bug site)
#   "blocked" — currently blocked upstream of the bug site (pin the cause)
_JPY = dict(entry=150.000, sl=149.600, tp=150.800, atr=0.05)
_FX = dict(entry=1.20000, sl=1.19600, tp=1.20800, atr=0.0005)

TYPE_CONFIG = {
    "keltner_squeeze_breakout": dict(instrument="EUR_USD", now=_LONDON_THU,
                                     expect="row", **_FX),
    "donchian_momentum_breakout": dict(instrument="USD_JPY", now=_LONDON_THU,
                                       expect="row", **_JPY),
    # NOT in QUALIFIED_TYPES — blocked at unknown_type before the bug site.
    "rnb_support_bounce": dict(instrument="USD_JPY", now=_LONDON_THU,
                               expect="blocked", block_key="unknown_type",
                               **_JPY),
    "price_shock_rev_eur_gbp_h1_long": dict(instrument="EUR_GBP",
                                            now=_LONDON_THU, expect="row",
                                            **_FX),
    "price_shock_rev_eur_aud_h1_long": dict(instrument="EUR_AUD",
                                            now=_LONDON_THU, expect="row",
                                            entry=1.65000, sl=1.64600,
                                            tp=1.65800, atr=0.0008),
    "price_shock_rev_usd_cad_h1_long": dict(instrument="USD_CAD",
                                            now=_LONDON_THU, expect="row",
                                            entry=1.36000, sl=1.35600,
                                            tp=1.36800, atr=0.0006),
    "price_shock_rev_nzd_jpy_h1_long": dict(instrument="NZD_JPY",
                                            now=_LONDON_THU, expect="row",
                                            entry=95.000, sl=94.600,
                                            tp=95.800, atr=0.05),
    "price_shock_rev_aud_jpy_h1_long": dict(instrument="AUD_JPY",
                                            now=_LONDON_THU, expect="row",
                                            entry=105.000, sl=104.600,
                                            tp=105.800, atr=0.05),
    "sweep_reversion_eurgbp_late": dict(instrument="EUR_GBP", now=_LONDON_THU,
                                        expect="row", entry=0.85000,
                                        sl=0.84700, tp=0.85500, atr=0.0004),
    # High-WR/low-RR contract — exempt from both RR floors by design.
    "hull_donchian_fade": dict(instrument="EUR_USD", now=_LONDON_THU,
                               expect="row", entry=1.20000, sl=1.18800,
                               tp=1.20100, atr=0.0005),
    # Sunday-open entry window + pair allowlist (EUR_USD/USD_JPY/AUD_USD).
    "weekend_gap_fade": dict(instrument="USD_JPY", now=_SUNDAY_OPEN,
                             expect="row", entry=147.500, sl=146.000,
                             tp=152.500, atr=0.10),
}


def _pinned_datetime(now_utc: real_datetime):
    class _Pinned(real_datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return now_utc.replace(tzinfo=None)
            return now_utc.astimezone(tz)
    return _Pinned


def _make_trader(tmp_path, monkeypatch):
    trader = DemoTrader(DemoDB(str(tmp_path / f"preserve_{uuid.uuid4().hex}.db")))
    logs: list = []
    monkeypatch.setattr(trader, "_add_log", logs.append)
    monkeypatch.setattr(trader, "_check_drawdown", lambda: False)
    monkeypatch.setattr(
        trader._exposure_mgr, "check_new_trade", lambda *_a, **_k: (True, ""),
    )
    monkeypatch.setattr(
        trader, "_get_mtf_regime",
        lambda _inst: {"regime": "uncertain", "d1": 3, "h4": 3, "vol": "normal"},
    )
    monkeypatch.setattr(trader, "_compute_dow_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(trader, "_compute_v2_regime", lambda *_a, **_k: "")
    monkeypatch.setattr(
        trader, "_compute_confluence_tag",
        lambda *_a, **_k: {"score": 0, "details": ""},
    )
    monkeypatch.setattr(trader, "_maybe_reserve_signal_emit", lambda *_a, **_k: None)
    fake_bridge = MagicMock()
    fake_bridge.active = True
    fake_bridge.is_mode_allowed.return_value = True
    fake_bridge.open_trade.return_value = False  # refusal path → shadow escalation
    monkeypatch.setattr(trader, "_oanda", fake_bridge)
    return trader, logs


def _sig(entry_type: str, cfg: dict) -> dict:
    return {
        "signal": "BUY",
        "entry": cfg["entry"],
        "sl": cfg["sl"],
        "tp": cfg["tp"],
        "entry_type": entry_type,
        "confidence": 80,
        "score": 1.0,
        "reasons": ["✅ preserve-sltp regression pin"],
        "atr": cfg["atr"],
        "regime": {"regime": "TRANSITION"},
        "layer_status": {"trade_ok": True, "layer1": {"direction": "neutral"}},
    }


@pytest.mark.parametrize("entry_type", sorted(PRESERVE_TYPES))
def test_preserve_type_reaches_send_decision_without_unboundlocalerror(
        entry_type, tmp_path, monkeypatch):
    cfg = TYPE_CONFIG[entry_type]  # KeyError = new preserve type: add config
    monkeypatch.setattr(data_mod, "fetch_oanda_bid_ask", lambda _inst: None)
    monkeypatch.setattr(demo_trader_mod, "datetime", _pinned_datetime(cfg["now"]))
    trader, _logs = _make_trader(tmp_path, monkeypatch)

    # UnboundLocalError propagates to the caller (per _tick_entry contract) —
    # with the bug present this call raises and the test fails (regression pin).
    trader._tick_entry(
        "daytrade", {"instrument": cfg["instrument"], "icon": "UT",
                     "label": "unit-test"},
        _sig(entry_type, cfg), "1h", cfg["instrument"],
    )

    with trader._db._safe_conn() as conn:
        rows = conn.execute(
            "SELECT trade_id, is_shadow FROM demo_trades"
        ).fetchall()

    if cfg["expect"] == "row":
        # Row insert precedes the (formerly crashing) lot-sizing reference and
        # there is no early return in between: row + normal return proves the
        # send-decision path executed past the bug site.
        assert rows, (
            f"{entry_type}: expected a demo_trades row (send path reached); "
            f"blocked instead: {trader._block_counts_per_strategy}"
        )
    else:
        assert not rows, f"{entry_type}: expected upstream block, got rows"
        block_key = f"{entry_type}:{cfg['block_key']}"
        assert any(k.startswith(block_key)
                   for k in trader._block_counts_per_strategy), (
            f"{entry_type}: expected block at {cfg['block_key']}, "
            f"got {trader._block_counts_per_strategy}"
        )


def test_preserve_set_matches_frozen_membership():
    """Membership pin: alert on silent preserve-set drift so TYPE_CONFIG
    (and the per-type send-path coverage above) stays exhaustive."""
    assert PRESERVE_TYPES == frozenset(TYPE_CONFIG), (
        "Preserve set changed — update TYPE_CONFIG with a send-path config "
        "for each new entry_type (integration test is mandatory for new "
        "preserve types)."
    )


def test_preserve_rearm_pin_reflects_user_decision_2026_07_28():
    """2026-07-28 user 決裁「7 席全部再武装」の pin: frozenset は空 (全解除)。
    再 pin する場合は user 決裁 + 本テスト更新が必須 (無断追加/削除の drift 検知)。"""
    from modules.demo_trader import _PRESERVE_REARM_LIVE_PIN
    assert _PRESERVE_REARM_LIVE_PIN == frozenset(), (
        "_PRESERVE_REARM_LIVE_PIN changed — user 決裁記録と本テストを同時更新すること")


def test_weekend_gap_fade_not_rearm_pinned():
    """weekend_gap_fade は user 承認済み (2026-07-25 option b) のため pin 対象外。"""
    from modules.demo_trader import _PRESERVE_REARM_LIVE_PIN
    assert "weekend_gap_fade" not in _PRESERVE_REARM_LIVE_PIN
