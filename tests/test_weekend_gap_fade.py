"""weekend_gap_fade — pre-reg LOCKED 2026-07-24 execution contract tests.

Pre-reg: knowledge-base/wiki/decisions/weekend-gap-stage2-execution-prereg-2026-07-24.md
Covers:
  - signal detection on fixture data (qualifying / non-qualifying gap, direction,
    Friday-close guard, entry window, frozen per-pair thresholds)
  - spread-cap (10.0p) scoping: applies to this entry_type only
  - per-pair per-weekend system_kv latch (dedup + fail-closed on DB error)
  - G1/G2 R2 gates: firing, boundaries, and NO re-arm once fired
  - fixed 1000u sizing pins, +4h horizon time-exit mapping, disaster SL 150p
  - all 4 registration points + guard exemption pins (code-pin style)
"""
import inspect
import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from strategies.daytrade.weekend_gap_fade import (
    FRI_CLOSE_GUARD_H,
    WEEKEND_GAP_DISASTER_SL_PIPS,
    WEEKEND_GAP_ENTRY_WINDOW_BARS,
    WEEKEND_GAP_FADE_ENTRY_TYPE,
    WEEKEND_GAP_FADE_PAIRS,
    WEEKEND_GAP_PIP_SIZE,
    WEEKEND_GAP_QUALIFY_PIPS,
    WEEKEND_GAP_SPREAD_CAP_PIPS,
    WEEKEND_GAP_TP_SENTINEL_PIPS,
    WeekendGapFade,
    build_weekend_gap_sig,
    detect_weekend_gap_signal,
    symbol_to_instrument,
    weekend_gap_spread_cap_skip,
    weekend_key_for,
)

# 2026-07-26 (Sunday) 21:00 UTC boundary weekend used across fixtures
_FRI = pd.Timestamp("2026-07-24 21:00", tz="UTC")   # Friday 21:00 UTC cut
_SUN = _FRI + timedelta(hours=48)                    # Sunday 21:00 UTC cut


def _mk_df(instrument: str, fri_close: float, gap_pips: float,
           include_sunday_bar: bool = True,
           last_friday_bar: str = "2026-07-24 20:45") -> pd.DataFrame:
    """15m fixture: Thu 00:00 .. Fri close, then (optionally) Sun 21:00 bar."""
    pip = WEEKEND_GAP_PIP_SIZE[instrument]
    idx = pd.date_range("2026-07-23 00:00", last_friday_bar, freq="15min", tz="UTC")
    n = len(idx)
    df = pd.DataFrame(
        {
            "Open": np.full(n, fri_close),
            "High": np.full(n, fri_close + pip),
            "Low": np.full(n, fri_close - pip),
            "Close": np.full(n, fri_close),
        },
        index=idx,
    )
    if include_sunday_bar:
        sun_open = fri_close + gap_pips * pip
        sun_row = pd.DataFrame(
            {
                "Open": [sun_open],
                "High": [sun_open + pip],
                "Low": [sun_open - pip],
                "Close": [sun_open],
            },
            index=[_SUN],
        )
        df = pd.concat([df, sun_row])
    return df


# ── Frozen constants (pre-reg — any change here must be R1) ──────────────


def test_frozen_qualify_thresholds():
    assert WEEKEND_GAP_QUALIFY_PIPS == {
        "EUR_USD": 20.0,
        "USD_JPY": 21.4,
        "AUD_USD": 25.0,
    }
    assert WEEKEND_GAP_FADE_PAIRS == frozenset({"EUR_USD", "USD_JPY", "AUD_USD"})
    assert "GBP_USD" not in WEEKEND_GAP_FADE_PAIRS  # 永久対象外 (pre-reg §2.1)


def test_frozen_execution_constants():
    import modules.demo_trader as dt

    assert WEEKEND_GAP_SPREAD_CAP_PIPS == 10.0
    assert WEEKEND_GAP_DISASTER_SL_PIPS == 150.0
    assert dt.WEEKEND_GAP_MAX_HOLD_SEC == 4 * 3600
    assert dt.WEEKEND_GAP_FADE_UNITS == 1000
    assert dt.WEEKEND_GAP_G1_MIN_N == 6
    assert dt.WEEKEND_GAP_G1_SLIPPAGE_PIPS == 2.0
    assert dt.WEEKEND_GAP_G2_MIN_N == 12
    assert dt.WEEKEND_GAP_G2_CUM_NET_PIPS == -60.0


# ── Signal detection (explore-tool definitions) ──────────────────────────


def test_qualifying_gap_up_fades_sell():
    now = _SUN + timedelta(minutes=5)
    df = _mk_df("EUR_USD", 1.1000, +30.0)
    det = detect_weekend_gap_signal(df, "EUR_USD", now)
    assert det is not None
    assert det["direction"] == "SELL"          # gap up -> fade SELL
    assert det["gap_pips"] == pytest.approx(30.0, abs=0.2)
    assert det["weekend_key"] == "2026-07-26"
    assert det["first_bar_ts"] == _SUN


def test_qualifying_gap_down_fades_buy():
    now = _SUN + timedelta(minutes=5)
    df = _mk_df("USD_JPY", 150.00, -25.0)
    det = detect_weekend_gap_signal(df, "USD_JPY", now)
    assert det is not None
    assert det["direction"] == "BUY"           # gap down -> fade BUY
    assert det["gap_pips"] == pytest.approx(-25.0, abs=0.2)


def test_non_qualifying_gap_returns_none():
    now = _SUN + timedelta(minutes=5)
    assert detect_weekend_gap_signal(_mk_df("EUR_USD", 1.1000, 19.9), "EUR_USD", now) is None
    # USD_JPY: 21.0p is >= EUR threshold but < frozen 21.4p — per-pair scoping
    assert detect_weekend_gap_signal(_mk_df("USD_JPY", 150.00, 21.0), "USD_JPY", now) is None
    assert detect_weekend_gap_signal(_mk_df("USD_JPY", 150.00, 21.5), "USD_JPY", now) is not None
    # AUD_USD: 24p < 25.0p frozen
    assert detect_weekend_gap_signal(_mk_df("AUD_USD", 0.6600, 24.0), "AUD_USD", now) is None
    assert detect_weekend_gap_signal(_mk_df("AUD_USD", 0.6600, 26.0), "AUD_USD", now) is not None


def test_pair_allowlist_enforced_in_detector():
    now = _SUN + timedelta(minutes=5)
    df = _mk_df("EUR_USD", 1.3000, 50.0)
    assert detect_weekend_gap_signal(df, "GBP_USD", now) is None


def test_friday_close_guard_6h():
    now = _SUN + timedelta(minutes=5)
    # last bar Thursday 12:00 → 33h before Friday cut > 6h guard → no event
    df = _mk_df("EUR_USD", 1.1000, 30.0, last_friday_bar="2026-07-23 12:00")
    assert detect_weekend_gap_signal(df, "EUR_USD", now) is None
    assert FRI_CLOSE_GUARD_H == 6


def test_no_sunday_bar_returns_none():
    now = _SUN + timedelta(minutes=5)
    df = _mk_df("EUR_USD", 1.1000, 30.0, include_sunday_bar=False)
    assert detect_weekend_gap_signal(df, "EUR_USD", now) is None


def test_entry_window_is_bar_length_scoped():
    df = _mk_df("EUR_USD", 1.1000, 30.0)
    window = timedelta(minutes=15 * WEEKEND_GAP_ENTRY_WINDOW_BARS)
    # inside the window
    assert detect_weekend_gap_signal(df, "EUR_USD", _SUN + window - timedelta(minutes=1)) is not None
    # after the window (no late chasing — estimand preservation)
    assert detect_weekend_gap_signal(df, "EUR_USD", _SUN + window + timedelta(minutes=1)) is None
    # before the first bar exists
    assert detect_weekend_gap_signal(df, "EUR_USD", _SUN - timedelta(minutes=1)) is None


def test_winter_open_22utc_within_guard():
    """Winter: first bar appears at 22:00 UTC — must still qualify (<=24h guard)."""
    pip = WEEKEND_GAP_PIP_SIZE["EUR_USD"]
    df = _mk_df("EUR_USD", 1.1000, 30.0, include_sunday_bar=False)
    sun_open = 1.1000 + 30.0 * pip
    winter_bar = pd.DataFrame(
        {"Open": [sun_open], "High": [sun_open], "Low": [sun_open], "Close": [sun_open]},
        index=[_SUN + timedelta(hours=1)],
    )
    df = pd.concat([df, winter_bar])
    det = detect_weekend_gap_signal(df, "EUR_USD", _SUN + timedelta(hours=1, minutes=5))
    assert det is not None
    assert det["first_bar_ts"] == _SUN + timedelta(hours=1)


# ── sig / Candidate construction ─────────────────────────────────────────


def test_build_sig_disaster_sl_and_sentinel_tp():
    det = detect_weekend_gap_signal(
        _mk_df("EUR_USD", 1.1000, 30.0), "EUR_USD", _SUN + timedelta(minutes=5))
    mid = det["sunday_open"]
    sig = build_weekend_gap_sig(det, "EUR_USD", mid, atr=0.0007)
    pip = WEEKEND_GAP_PIP_SIZE["EUR_USD"]
    assert sig["signal"] == "SELL"
    assert sig["entry_type"] == WEEKEND_GAP_FADE_ENTRY_TYPE
    # disaster SL: entry +150p for SELL
    assert sig["sl"] == pytest.approx(mid + WEEKEND_GAP_DISASTER_SL_PIPS * pip)
    # sentinel TP far away (engine placeholder; OANDA order carries no TP)
    assert abs(sig["tp"] - mid) == pytest.approx(WEEKEND_GAP_TP_SENTINEL_PIPS * pip)
    # daytrade pipeline sign convention: SELL -> negative score (score gate alignment)
    assert sig["score"] < 0
    # QUALIFIED_TYPES gate needs at least one confirmed reason
    assert any("✅" in r for r in sig["reasons"])
    assert sig["_closed_bar_ts"] == det["first_bar_ts"]


def test_strategy_evaluate_returns_candidate():
    from types import SimpleNamespace

    df = _mk_df("USD_JPY", 150.00, +25.0)
    ctx = SimpleNamespace(
        symbol="USDJPY=X", df=df, entry=float(df["Close"].iloc[-1]),
        atr=0.07, backtest_mode=True, bar_time=_SUN + timedelta(minutes=5),
    )
    cand = WeekendGapFade().evaluate(ctx)
    assert cand is not None
    assert cand.entry_type == "weekend_gap_fade"
    assert cand.signal == "SELL"
    pip = WEEKEND_GAP_PIP_SIZE["USD_JPY"]
    assert cand.sl == pytest.approx(ctx.entry + 150.0 * pip)


def test_strategy_evaluate_none_off_window_and_off_pair():
    from types import SimpleNamespace

    df = _mk_df("USD_JPY", 150.00, +25.0)
    ctx = SimpleNamespace(
        symbol="USDJPY=X", df=df, entry=150.25, atr=0.07,
        backtest_mode=True, bar_time=_SUN + timedelta(hours=3),
    )
    assert WeekendGapFade().evaluate(ctx) is None
    ctx2 = SimpleNamespace(
        symbol="GBPUSD=X", df=df, entry=150.25, atr=0.07,
        backtest_mode=True, bar_time=_SUN + timedelta(minutes=5),
    )
    assert WeekendGapFade().evaluate(ctx2) is None


def test_symbol_to_instrument_and_weekend_key():
    assert symbol_to_instrument("USDJPY=X") == "USD_JPY"
    assert symbol_to_instrument("EURUSD=X") == "EUR_USD"
    assert symbol_to_instrument("AUDUSD=X") == "AUD_USD"
    assert symbol_to_instrument("GBPUSD=X") == ""
    assert weekend_key_for(datetime(2026, 7, 26, 21, 4, tzinfo=timezone.utc)) == "2026-07-26"
    assert weekend_key_for(datetime(2026, 7, 26, 20, 59, tzinfo=timezone.utc)) is None
    assert weekend_key_for(datetime(2026, 7, 25, 22, 0, tzinfo=timezone.utc)) is None  # Saturday


# ── Spread cap scoping ────────────────────────────────────────────────────


def test_spread_cap_boundary():
    assert weekend_gap_spread_cap_skip(10.01) is True
    assert weekend_gap_spread_cap_skip(10.0) is False   # cap 境界は執行 (pre-reg §2.2)
    assert weekend_gap_spread_cap_skip(4.0) is False


def test_e1_cap_is_entry_type_scoped_not_blanket():
    """E1 replacement must be scoped to weekend_gap_fade only."""
    import modules.demo_trader as dt

    src = inspect.getsource(dt.DemoTrader._tick_entry)
    # scoped cap branch exists ...
    assert "weekend_gap_spread_cap" in src
    # ... and the standard E1 block for all other entry_types survives,
    # scoped away from wg only via `not _wg_entry`
    assert "_spread_pips > _spread_limit and not _is_shadow_eligible and not _wg_entry" in src
    # standard per-pair limits untouched
    assert '"USD_JPY": 1.0,' in src
    assert '"EUR_USD": 1.2,' in src
    assert '"AUD_USD": 1.5,' in src
    # spread-skip records a shadow row with the pre-reg block cause
    assert "WEEKEND_GAP_SPREAD_SKIP" in src


# ── system_kv latch (per-pair per-weekend, deploy-safe) ──────────────────


class _FakeDB:
    def __init__(self, fail=False):
        self.kv = {}
        self.fail = fail

    def get_system_kv(self, key, default=""):
        if self.fail:
            raise RuntimeError("db down")
        return self.kv.get(key, default)

    def set_system_kv(self, key, value):
        if self.fail:
            raise RuntimeError("db down")
        self.kv[key] = value


class _FakeAlerts:
    def __init__(self):
        self.sent = []

    def alert_custom(self, title, body):
        self.sent.append((title, body))


def _harness(db=None, live_rows=None):
    import modules.demo_trader as dt

    class _WgHarness(dt.DemoTrader):
        def __init__(self):
            self._db = db if db is not None else _FakeDB()
            self._alert_mgr = _FakeAlerts()
            self.logs = []
            self._live_rows = live_rows if live_rows is not None else []

        def _add_log(self, msg):
            self.logs.append(msg)

        def _weekend_gap_live_rows(self):
            return list(self._live_rows)

    return _WgHarness()


def test_latch_set_then_get_blocks_same_weekend():
    h = _harness()
    assert h._weekend_gap_latch_get("EUR_USD", "2026-07-26") == ""
    h._weekend_gap_latch_set("EUR_USD", "2026-07-26", state="EXECUTED",
                             trade_id="T1", spread_pips=4.2)
    latched = h._weekend_gap_latch_get("EUR_USD", "2026-07-26")
    assert latched
    payload = json.loads(latched)
    assert payload["state"] == "EXECUTED"
    assert payload["trade_id"] == "T1"
    # per-pair per-weekend scoping: other pair / other weekend unaffected
    assert h._weekend_gap_latch_get("USD_JPY", "2026-07-26") == ""
    assert h._weekend_gap_latch_get("EUR_USD", "2026-08-02") == ""


def test_latch_key_includes_pair_and_weekend():
    import modules.demo_trader as dt

    key = dt.DemoTrader._weekend_gap_latch_kv_key("USD_JPY", "2026-07-26")
    assert key == "weekend_gap_fade:USD_JPY:2026-07-26"


def test_latch_read_fails_closed_on_db_error():
    h = _harness(db=_FakeDB(fail=True))
    # DB error must read as LATCHED (no double market order on a broken DB)
    assert h._weekend_gap_latch_get("EUR_USD", "2026-07-26") != ""


# ── G1/G2 R2 gates ────────────────────────────────────────────────────────


def _rows(slips=(), pnls=()):
    n = max(len(slips), len(pnls))
    return [
        {"slippage_pips": (slips[i] if i < len(slips) else 0.0),
         "pnl_pips": (pnls[i] if i < len(pnls) else 0.0)}
        for i in range(n)
    ]


def test_g1_fires_on_rolling_mean_slippage():
    import modules.demo_trader as dt

    verdict = dt.DemoTrader._weekend_gap_r2_gate_verdict
    stop, reason = verdict(_rows(slips=[2.5] * 6))
    assert stop and reason.startswith("G1_slippage")
    # boundary: mean exactly +2.0p does NOT fire (strict >)
    stop, _ = verdict(_rows(slips=[2.0] * 6))
    assert not stop
    # N<6: never fires
    stop, _ = verdict(_rows(slips=[9.9] * 5))
    assert not stop
    # rolling = last 6 only: early bad fills do not permanently poison the gate
    stop, _ = verdict(_rows(slips=[5.0, 5.0] + [1.0] * 6))
    assert not stop


def test_g2_fires_on_cumulative_net():
    import modules.demo_trader as dt

    verdict = dt.DemoTrader._weekend_gap_r2_gate_verdict
    stop, reason = verdict(_rows(pnls=[-5.1] * 12))
    assert stop and reason.startswith("G2_first_look")
    stop, _ = verdict(_rows(pnls=[-4.9] * 12))   # cum -58.8 > -60
    assert not stop
    stop, _ = verdict(_rows(pnls=[-10.0] * 11))  # N=11 < 12
    assert not stop


def test_r2_gate_sets_permanent_flag_and_alerts():
    import modules.demo_trader as dt

    h = _harness(live_rows=_rows(slips=[3.0] * 6))
    assert h._weekend_gap_check_r2_gates() is True
    flag = h._db.kv.get(dt.WEEKEND_GAP_LIVE_STOP_KV_KEY)
    assert flag
    assert "G1_slippage" in json.loads(flag)["reason"]
    assert h._alert_mgr.sent, "AlertManager alert_custom must fire on stop"
    assert any("R2 auto-stop" in m for m in h.logs)


def test_r2_gate_never_re_arms():
    """Once stopped, healthy stats must NOT re-enable live (watchdog
    DECREMENT re-arm bug precedent)."""
    import modules.demo_trader as dt

    h = _harness(live_rows=_rows(slips=[3.0] * 6))
    assert h._weekend_gap_check_r2_gates() is True
    original_flag = h._db.kv[dt.WEEKEND_GAP_LIVE_STOP_KV_KEY]
    # history becomes healthy → still stopped, flag preserved verbatim
    h._live_rows = _rows(slips=[0.1] * 6, pnls=[10.0] * 12)
    assert h._weekend_gap_check_r2_gates() is True
    assert h._db.kv[dt.WEEKEND_GAP_LIVE_STOP_KV_KEY] == original_flag
    # a second breach must not overwrite the original evidence either
    h._weekend_gap_set_live_stop("G2_first_look(fake)")
    assert h._db.kv[dt.WEEKEND_GAP_LIVE_STOP_KV_KEY] == original_flag


def test_live_stop_flag_read_fails_closed():
    h = _harness(db=_FakeDB(fail=True))
    assert h._weekend_gap_live_stopped() is True


# ── Sizing / exit mapping / guard-chain pins (code-pin style) ─────────────


def test_fixed_1000u_sentinel_pins():
    import modules.demo_trader as dt

    assert dt.WEEKEND_GAP_FADE_UNITS == 1000
    src = inspect.getsource(dt.DemoTrader._tick_entry)
    # fixed-units override present (lot chain must not multiply it)
    assert "_adjusted_units = WEEKEND_GAP_FADE_UNITS" in src
    assert '"WEEKEND_GAP_FADE_MIN_LOT"' in src
    # FLAT_UNITS env must not rewrite the 1000u contract
    assert "entry_type != WEEKEND_GAP_FADE_ENTRY_TYPE" in src
    # agg-Kelly permanent-negative gate: min-lot bypass membership required
    assert "weekend_gap_fade" in dt.DemoTrader._AGG_KELLY_GATE_MINLOT_BYPASS_TYPES
    assert dt.DemoTrader._AGG_KELLY_GATE_MINLOT_MAX_UNITS == 1000


def test_horizon_exit_and_no_tp_no_be_no_c1_pins():
    import modules.demo_trader as dt

    src = inspect.getsource(dt.DemoTrader._check_sltp_realtime)
    # +4h exact hold mapping with close_reason="horizon"
    assert "WEEKEND_GAP_FADE_ENTRY_TYPE: WEEKEND_GAP_MAX_HOLD_SEC" in src
    assert dt.WEEKEND_GAP_MAX_HOLD_SEC == 4 * 3600
    # TP-hit skipped in BOTH directions + disaster SL flagging
    assert '"disaster_sl" if _is_weekend_gap else "SL_HIT"' in src
    assert "not _is_weekend_gap and price >= tp" in src
    assert "not _is_weekend_gap and price <= tp" in src
    # BE/trail block skipped
    assert "tp_dist > 0 and not _is_weekend_gap" in src
    # C1 (half-time exit) exemption
    assert "not close_reason and not _is_weekend_gap" in src
    # MFE BE-lock disabled via per-strategy trigger 0.0
    assert dt.MFE_BE_LOCK_STRATEGY_TRIGGERS.get("weekend_gap_fade") == 0.0
    # SIGNAL_REVERSE exemption
    sr_src = inspect.getsource(dt.DemoTrader._check_signal_reverse)
    assert "WEEKEND_GAP_FADE_ENTRY_TYPE" in sr_src


def test_sent_log_tp_formatting_handles_none():
    """weekend_gap の _tp_oanda=None 経路: f"{None:.5f}" は TypeError で
    'sent' audit row / PRIME tag が飛ぶ — SENT ログは None セーフ helper
    経由で整形されること (2026-07-25 review blocker)。"""
    import modules.demo_trader as dt

    # the previously-untested branch: None must format without raising
    assert dt.DemoTrader._fmt_tp_for_sent_log(None, 5) == "none(horizon-only)"
    assert dt.DemoTrader._fmt_tp_for_sent_log(1.23456, 5) == "1.23456"
    assert dt.DemoTrader._fmt_tp_for_sent_log(150.123, 3) == "150.123"
    # the _send_accepted success log must go through the None-safe helper —
    # a raw f-format of _tp_oanda would reintroduce the TypeError
    src = inspect.getsource(dt.DemoTrader._tick_entry)
    assert "TP={self._fmt_tp_for_sent_log(_tp_oanda, _price_dec)}" in src
    assert "TP={_tp_oanda:.{_price_dec}f}" not in src


def test_g1_slippage_basis_is_entry_fill_spread_independent():
    """pre-reg §5 G1: slippage は「fill vs signal_price、spread とは独立」。
    entry_fill basis → _signal_price = 同サイド OANDA quote (mid ではない)
    → quoted half-spread (日曜 open 4-10p の半分) が G1 入力に混入しない。"""
    import modules.demo_trader as dt

    det = detect_weekend_gap_signal(
        _mk_df("EUR_USD", 1.1000, 30.0), "EUR_USD", _SUN + timedelta(minutes=5))
    sig = build_weekend_gap_sig(det, "EUR_USD", det["sunday_open"], atr=0.0007)
    assert sig["slippage_signal_price_basis"] == "entry_fill"
    # demo_trader dispatch: entry_fill → current_price (side quote at decision
    # time), NOT sig["entry"] (yfinance mid, which embeds ~half the spread)
    src = inspect.getsource(dt.DemoTrader._tick_entry)
    assert 'slippage_signal_price_basis") == "entry_fill"' in src


def test_resend_pending_excludes_weekend_gap():
    """pre-reg §2.2 単発契約: 補完再送経路 (_resend_pending_oanda_trades) は
    weekend_gap_fade を entry_type ごと除外する (bridge default 10000u /
    sentinel TP の実 TP 化 / retry 3 / cap 再チェックなし / G1 blind 防止)。"""
    import modules.demo_trader as dt

    calls = []

    class _FakeOanda:
        active = True

        def is_mode_allowed(self, mode):
            return True

        def open_trade(self, **kw):
            calls.append(kw)
            return True

    class _FakeResendDB:
        def __init__(self, rows):
            self.rows = rows

        def get_open_trades_without_oanda(self):
            return list(self.rows)

        def set_oanda_trade_id(self, tid, oid):
            pass

    now_iso = datetime.now(timezone.utc).isoformat()
    wg_row = {
        "trade_id": "WG1", "mode": "daytrade_audusd", "entry_time": now_iso,
        "instrument": "AUD_USD", "entry_type": WEEKEND_GAP_FADE_ENTRY_TYPE,
        "direction": "SELL", "sl": 0.6750, "tp": 0.6150, "confidence": 70,
    }
    normal_row = {
        "trade_id": "N1", "mode": "daytrade", "entry_time": now_iso,
        "instrument": "USD_JPY", "entry_type": "ema_cross",
        "direction": "BUY", "sl": 149.50, "tp": 150.80, "confidence": 70,
    }

    class _ResendHarness(dt.DemoTrader):
        def __init__(self):
            self._oanda = _FakeOanda()
            self._db = _FakeResendDB([wg_row, normal_row])
            self.logs = []

        def _add_log(self, msg):
            self.logs.append(msg)

        def _resend_promote_gate_block_reason(self, *a, **kw):
            return None  # exclusion must NOT depend on the promote gate

    h = _ResendHarness()
    h._resend_pending_oanda_trades()
    # wg row never resent; normal row still flows (exclusion is scoped)
    assert [c["demo_trade_id"] for c in calls] == ["N1"]
    assert any("resend excluded" in m for m in h.logs)


def test_exposure_ledger_registers_fixed_units():
    """pre-reg §2.4: 3 ペア同時執行 (broad-USD gap) が 20k currency cap に
    誤衝突しない — check 側と add_position 側の両方が固定 1000u を使う。"""
    import modules.demo_trader as dt

    src = inspect.getsource(dt.DemoTrader._tick_entry)
    # incoming-check side estimate
    assert "_exp_units_est = WEEKEND_GAP_FADE_UNITS" in src
    # ledger registration side (was env OANDA_UNITS 10000u — review major fix)
    assert "WEEKEND_GAP_FADE_UNITS if _wg_entry" in src


def test_bridge_single_attempt_and_no_tp_pins():
    import modules.demo_trader as dt
    import modules.oanda_bridge as ob

    sig = inspect.signature(ob.OandaBridge.open_trade)
    assert sig.parameters["max_attempts"].default == 3
    assert sig.parameters["record_fill_slippage"].default is False
    src = inspect.getsource(dt.DemoTrader._tick_entry)
    # no-retry + fill-slippage persistence are wired for this entry_type only
    assert "max_attempts=(1 if entry_type == WEEKEND_GAP_FADE_ENTRY_TYPE" in src
    assert "record_fill_slippage=(" in src
    # OANDA order carries NO takeProfit
    assert "_tp_oanda = None" in src
    # market_order skips takeProfit when None
    mo_src = inspect.getsource(ob.__dict__["OandaBridge"].open_trade)
    assert "take_profit=tp" in mo_src


def test_registration_checklist_all_four_points():
    """Deploy checklist: strategies/daytrade/__init__.py, QUALIFIED_TYPES,
    _UNIVERSAL_SENTINEL, app.py DT_QUALIFIED."""
    import modules.demo_trader as dt
    from strategies.daytrade import DaytradeEngine

    # 1. engine registration
    engine = DaytradeEngine()
    assert engine.get_strategy("weekend_gap_fade") is not None
    # side-channel against the select_best silent-drop bug (7th precedent)
    assert "weekend_gap_fade" in DaytradeEngine.LIVE_PROMOTE_LOSERS
    # 2. QUALIFIED_TYPES (local set inside _tick_entry — source pin)
    src = inspect.getsource(dt.DemoTrader._tick_entry)
    assert '"weekend_gap_fade",' in src
    # 3. _UNIVERSAL_SENTINEL (+ PAIR_PROMOTED precedence for the 3 live pairs)
    assert "weekend_gap_fade" in dt.DemoTrader._UNIVERSAL_SENTINEL
    for pair in ("EUR_USD", "USD_JPY", "AUD_USD"):
        assert ("weekend_gap_fade", pair) in dt.DemoTrader._PAIR_PROMOTED
    assert ("weekend_gap_fade", "GBP_USD") not in dt.DemoTrader._PAIR_PROMOTED
    # 4. app.py DT_QUALIFIED (text pin — compute_daytrade_signal is heavy)
    import os
    app_path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "app.py")
    with open(app_path, encoding="utf-8") as f:
        app_src = f.read()
    dtq = app_src.split("DT_QUALIFIED = {", 1)[1].split("}", 1)[0]
    assert '"weekend_gap_fade"' in dtq


def test_shield_and_quick_harvest_and_mode_registration():
    import modules.demo_trader as dt

    # EUR_USD leg: daytrade_eur is _OANDA_MODE_BLOCKED — whitelist required
    assert "daytrade_eur" in dt.DemoTrader._OANDA_MODE_BLOCKED
    assert "weekend_gap_fade" in dt.DemoTrader._SHIELD_EUR_DT_WHITELIST
    # Quick-Harvest TP shrink exemption for all 3 pairs
    for pair in ("EUR_USD", "USD_JPY", "AUD_USD"):
        assert ("weekend_gap_fade", pair) in dt.DemoTrader._QUICK_HARVEST_EXEMPT
    # AUD_USD 15m slot: weekend_gap-only mode (does not run other strategies)
    cfg = dt.MODE_CONFIG["daytrade_audusd"]
    assert cfg["instrument"] == "AUD_USD"
    assert cfg["tf"] == "15m"
    assert cfg.get("weekend_gap_only") is True
    assert cfg.get("auto_start") is True
    assert dt._get_base_mode("daytrade_audusd") == "daytrade"
    # scoped Sunday runner wired before the market-closed early return
    tick_src = inspect.getsource(dt.DemoTrader._tick)
    assert (tick_src.index("self._weekend_gap_tick(mode, cfg)")
            < tick_src.index("if self._is_fx_market_closed():"))
    # diagnostics-only membership (observability, not a gate bypass)
    assert "weekend_gap_fade" in dt.DemoTrader._SILENT_DROP_DIAG_TYPES
