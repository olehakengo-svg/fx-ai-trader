"""Aggregate Kelly Gate raw-fix + min-lot pre-reg bypass (P1, 2026-07-02).

Bug (eligible vs effective): ``DemoTrader._get_aggregate_kelly`` returned
``stats_utils.kelly_criterion()["full_kelly"]`` which is clipped to
``max(0, full_kelly)`` (stats_utils.py) — so the v9.0 SHIELD gate predicate
``_agg_kelly < 0`` (demo_trader.py L6203) could structurally never fire.

Fix (user 決裁 2026-07-02, rule:R3 bug + rule:R2 interplay):
  (a) ``kelly_criterion`` gains an unclipped ``full_kelly_raw`` field;
      ``_get_aggregate_kelly`` returns it (negative-capable). All existing
      consumers keep reading the clipped ``full_kelly`` — non-breaking.
  (b) 1000u fixed-lot pre-reg contract strategies (vix_carry_unwind /
      usdjpy_carry_dip_accumulator / sweep_reversion_eurgbp_late) bypass the
      gate ONLY while their effective units stay at validation size
      (<= 1000u, non-XAU) — the same risk class as the sentinel 1000u lots
      the gate already exempts. Allowlist alone (eligible) or units alone
      (effective) is not enough; both must hold, so a future lot promotion
      auto-expires the bypass.

Diagnosis: knowledge-base/wiki/analyses/zero-fire-diagnosis-carrydip-vix-2026-07-02.md §2.4
Decision: knowledge-base/wiki/decisions/agg-kelly-gate-raw-fix-minlot-bypass-2026-07-02.md
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(str(Path(__file__).resolve().parent))

from modules import data as data_mod
from modules.demo_trader import DemoTrader
from modules.stats_utils import kelly_criterion

from edge_cell_test_helpers import edge_cfg, make_trader


# =====================================================================
#  (a-1) stats_utils.kelly_criterion — unclipped full_kelly_raw field
# =====================================================================

def test_kelly_criterion_raw_field_negative_when_edge_negative():
    """Losing book → full_kelly stays clipped at 0, full_kelly_raw goes negative."""
    # b = 1/3, full = (0.4*(1/3) - 0.6) / (1/3) = -1.4
    r = kelly_criterion(win_rate=0.4, avg_win=1.0, avg_loss=3.0)
    assert r["full_kelly"] == 0.0, "clipped field must keep legacy clamp"
    assert r["full_kelly_raw"] < 0, "raw field must expose the negative Kelly"
    assert abs(r["full_kelly_raw"] - (-1.4)) < 1e-6


def test_kelly_criterion_raw_equals_clipped_when_edge_positive():
    # b = 3, full = (0.7*3 - 0.3) / 3 = 0.6
    r = kelly_criterion(win_rate=0.7, avg_win=3.0, avg_loss=1.0)
    assert r["full_kelly"] > 0
    assert r["full_kelly_raw"] == r["full_kelly"]


def test_kelly_criterion_degenerate_path_includes_raw():
    """wr<=0 / avg_loss=0 early-return dict must also carry the raw field."""
    r = kelly_criterion(win_rate=0.0, avg_win=1.0, avg_loss=1.0)
    assert r["full_kelly_raw"] == 0.0
    r2 = kelly_criterion(win_rate=0.5, avg_win=1.0, avg_loss=0.0)
    assert r2["full_kelly_raw"] == 0.0


# =====================================================================
#  (a-2) _get_aggregate_kelly — negative-capable
# =====================================================================

class _FakeDB:
    def __init__(self, closed_trades):
        self._closed = closed_trades

    def get_all_closed(self):
        return list(self._closed)


class _AggKellyHarness:
    """Bind the production method so the code under test is real."""

    _get_aggregate_kelly = DemoTrader._get_aggregate_kelly

    def __init__(self, trades):
        self._db = _FakeDB(trades)
        self._FIDELITY_CUTOFF = "2026-04-16T08:00:00+00:00"


def _closed(pnl, *, instrument="EUR_USD",
            exit_time="2026-06-20T11:00:00+00:00"):
    return {
        "entry_type": "hist_book",
        "pnl_pips": pnl,
        "is_shadow": 0,
        "instrument": instrument,
        "status": "CLOSED",
        "exit_time": exit_time,
    }


def test_aggregate_kelly_negative_for_losing_book():
    """8 wins +1 / 12 losses -3 → WR=0.4, b=1/3 → full_kelly=-1.4 (< 0)."""
    trades = [_closed(1.0) for _ in range(8)] + [_closed(-3.0) for _ in range(12)]
    h = _AggKellyHarness(trades)
    k = h._get_aggregate_kelly()
    assert k is not None
    assert k < 0, f"aggregate Kelly must be negative for a losing book, got {k}"


def test_aggregate_kelly_positive_book_unchanged():
    """12 wins +3 / 8 losses -1 → positive Kelly, raw == clipped path."""
    trades = [_closed(3.0) for _ in range(12)] + [_closed(-1.0) for _ in range(8)]
    h = _AggKellyHarness(trades)
    k = h._get_aggregate_kelly()
    assert k is not None and k > 0


# =====================================================================
#  (b-1) min-lot bypass predicate — allowlist AND effective units
# =====================================================================

def _bypass(entry_type, units, is_xau=False):
    h = object.__new__(DemoTrader)
    return h._agg_kelly_gate_minlot_bypass(entry_type, units, is_xau)


def test_minlot_bypass_allows_contract_types_at_validation_units():
    assert _bypass("vix_carry_unwind", 1000) is True
    assert _bypass("usdjpy_carry_dip_accumulator", 1000) is True
    assert _bypass("sweep_reversion_eurgbp_late", 1000) is True


def test_minlot_bypass_expires_when_units_exceed_validation_size():
    """Effective guard: a future lot promotion must auto-expire the bypass."""
    assert _bypass("vix_carry_unwind", 5000) is False
    assert _bypass("vix_carry_unwind", 1001) is False


def test_minlot_bypass_rejects_non_contract_types_and_xau():
    assert _bypass("hull_donchian_fade", 1000) is False       # 5000u contract, not 1000u
    assert _bypass("session_time_bias", 1000) is False        # no fixed-lot contract
    assert _bypass("vix_carry_unwind", 1000, is_xau=True) is False
    assert _bypass("vix_carry_unwind", 0) is False


# =====================================================================
#  E2E — gate fires on real negative aggregate Kelly; pilot bypasses
# =====================================================================

def _set_price_feed(monkeypatch, current, spread):
    monkeypatch.setattr(
        data_mod,
        "fetch_oanda_bid_ask",
        lambda _instrument: {
            "bid": current["price"],
            "ask": current["price"] + spread,
        },
    )


def _sell_sig(entry_type, *, entry, pip):
    return {
        "entry": entry,
        "signal": "SELL",
        "entry_type": entry_type,
        "confidence": 70,
        "score": -1.0,
        "sl": entry + 15 * pip,
        "tp": entry - 30 * pip,
        "atr": 10 * pip,
        "reasons": [f"✅ agg-kelly gate test {entry_type}"],
        "regime": {"regime": "TREND_BEAR"},
        "layer_status": {"layer1": {"direction": "neutral"}},
        "sr_entry_map": {},
    }


def _seed_losing_clean_book(db, n_win=8, n_loss=12):
    """Seed >=20 CLOSED clean (non-shadow, non-XAU, post-cutoff, hold>=5s)
    trades with negative aggregate edge so the REAL _get_aggregate_kelly
    computes a negative full Kelly."""
    pnls = [1.0] * n_win + [-3.0] * n_loss
    ids = []
    for i in range(len(pnls)):
        tid = db.open_trade(
            direction="SELL", entry_price=1.2000, sl=1.2015, tp=1.1970,
            entry_type="hist_book", confidence=50, tf="15m",
            reasons=["seed book"], mode="daytrade_eur", instrument="EUR_USD",
            is_shadow=False, oanda_trade_id=f"seed-{i}",
        )
        ids.append(tid)
    with db._safe_conn() as conn:
        for tid, pnl in zip(ids, pnls):
            conn.execute(
                """
                UPDATE demo_trades
                SET status='CLOSED', pnl_pips=?,
                    entry_time='2026-06-20T10:00:00+00:00',
                    exit_time='2026-06-20T11:00:00+00:00'
                WHERE trade_id=?
                """,
                (pnl, tid),
            )
        conn.commit()


def _strategy_rows(db, entry_type):
    with db._safe_conn() as conn:
        return conn.execute(
            """
            SELECT is_shadow, oanda_trade_id FROM demo_trades
            WHERE entry_type = ? ORDER BY id
            """,
            (entry_type,),
        ).fetchall()


def test_gate_blocks_promoted_live_when_real_aggregate_kelly_negative(
        monkeypatch, tmp_path):
    """The dead-gate repro: with a real losing clean book, the production
    _get_aggregate_kelly must return < 0 and the SHIELD gate must shadow the
    fill. Before the fix the clipped 0.0 sails through and the fill goes live."""
    current = {"price": 1.1200}
    _set_price_feed(monkeypatch, current, spread=0.0001)

    trader, logs = make_trader(tmp_path, monkeypatch, hour=14)
    trader._SHADOW_MODE = False
    trader._strategy_n_cache = {"session_time_bias": 20}
    trader._PAIR_PROMOTED = frozenset({("session_time_bias", "EUR_USD")})
    trader._PAIR_SESSION_FILTER = {}
    # helpers stub _get_aggregate_kelly to None — rebind the production method
    trader._get_aggregate_kelly = DemoTrader._get_aggregate_kelly.__get__(trader)
    _seed_losing_clean_book(trader._db)

    trader._tick_entry(
        "daytrade_eur", edge_cfg(),
        _sell_sig("session_time_bias", entry=1.1200, pip=0.0001),
        "15m", "EUR_USD",
    )

    rows = _strategy_rows(trader._db, "session_time_bias")
    assert len(rows) == 1
    assert rows[0]["is_shadow"] == 1, "gate must shadow the fill (agg Kelly < 0)"
    assert not rows[0]["oanda_trade_id"]
    assert not trader._oanda.calls, "OANDA forwarding must be blocked"
    assert any("[SHIELD] Aggregate Kelly gate" in log for log in logs)


def test_vix_overlap_pilot_minlot_bypasses_gate_e2e(monkeypatch, tmp_path):
    """vix_carry_unwind × USD_JPY Overlap pilot (1000u fixed contract) must
    keep filling live while the aggregate Kelly gate is firing."""
    current = {"price": 157.00}
    _set_price_feed(monkeypatch, current, spread=0.002)

    trader, logs = make_trader(tmp_path, monkeypatch, hour=14)
    trader._SHADOW_MODE = False
    trader._strategy_n_cache = {"vix_carry_unwind": 20}
    trader._PAIR_PROMOTED = frozenset({("vix_carry_unwind", "USD_JPY")})
    trader._PAIR_SESSION_FILTER = {}
    trader._get_aggregate_kelly = lambda: -0.25  # gate is firing

    trader._tick_entry(
        "daytrade", _jpy_cfg(),
        _sell_sig("vix_carry_unwind", entry=157.00, pip=0.01),
        "15m", "USD_JPY",
    )

    rows = _strategy_rows(trader._db, "vix_carry_unwind")
    assert len(rows) == 1
    assert rows[0]["is_shadow"] == 0, "pilot must stay live under min-lot bypass"
    assert rows[0]["oanda_trade_id"]
    assert len(trader._oanda.calls) == 1
    assert abs(int(trader._oanda.calls[0]["units"])) == 1000, \
        "bypass is only valid at the 1000u validation lot"
    assert any("Aggregate Kelly gate" in log and "BYPASS" in log for log in logs)


def _jpy_cfg():
    return {
        "label": "Daytrade",
        "icon": "D",
        "symbol": "USDJPY=X",
        "base_sl_pips": 15,
        "active_hours_utc": (0, 23),
    }
