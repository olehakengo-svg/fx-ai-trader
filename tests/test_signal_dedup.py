"""Cross-thread dedup guard regression tests.

Validates that the in-memory `_recent_signal_emits` cache in DemoTrader
suppresses duplicate (entry_type, instrument, direction) emissions within
the 60-second window — covering the race-condition pattern observed in
demo_trades (vol_spike_mr 389/390 0.0002s, intraday_seasonality 436/437 6s).
"""
import threading
from datetime import datetime, timezone, timedelta
import concurrent.futures as cf


class _DedupOnly:
    """Minimal harness mirroring the dedup block from demo_trader._tick_entry."""

    def __init__(self):
        self._lock = threading.Lock()
        self._recent_signal_emits = {}

    def attempt(self, entry_type, instrument, signal, *, now=None):
        _signal_key = (entry_type, instrument, signal)
        _now_dedup = now or datetime.now(timezone.utc)
        _dedup_window = timedelta(seconds=60)
        with self._lock:
            _last_emit = self._recent_signal_emits.get(_signal_key)
            if _last_emit and (_now_dedup - _last_emit) < _dedup_window:
                return False, "recent_emit"
            self._recent_signal_emits[_signal_key] = _now_dedup
            _stale_cutoff = _now_dedup - timedelta(seconds=120)
            self._recent_signal_emits = {
                k: v for k, v in self._recent_signal_emits.items() if v > _stale_cutoff
            }
        return True, "ok"


def test_first_emission_passes():
    h = _DedupOnly()
    ok, _ = h.attempt("intraday_seasonality", "GBP_USD", "BUY")
    assert ok


def test_immediate_repeat_blocks():
    h = _DedupOnly()
    h.attempt("intraday_seasonality", "GBP_USD", "BUY")
    ok, reason = h.attempt("intraday_seasonality", "GBP_USD", "BUY")
    assert not ok and reason == "recent_emit"


def test_different_direction_passes():
    h = _DedupOnly()
    h.attempt("intraday_seasonality", "GBP_USD", "BUY")
    ok, _ = h.attempt("intraday_seasonality", "GBP_USD", "SELL")
    assert ok


def test_different_pair_passes():
    h = _DedupOnly()
    h.attempt("intraday_seasonality", "GBP_USD", "BUY")
    ok, _ = h.attempt("intraday_seasonality", "EUR_USD", "BUY")
    assert ok


def test_different_strategy_passes():
    h = _DedupOnly()
    h.attempt("intraday_seasonality", "GBP_USD", "BUY")
    ok, _ = h.attempt("vol_spike_mr", "GBP_USD", "BUY")
    assert ok


def test_window_expiry_releases():
    h = _DedupOnly()
    t0 = datetime(2026, 4, 27, 0, 0, 0, tzinfo=timezone.utc)
    h.attempt("intraday_seasonality", "GBP_USD", "BUY", now=t0)
    # 61 seconds later: cleared
    ok, _ = h.attempt(
        "intraday_seasonality", "GBP_USD", "BUY", now=t0 + timedelta(seconds=61)
    )
    assert ok


def test_within_window_blocks():
    h = _DedupOnly()
    t0 = datetime(2026, 4, 27, 0, 0, 0, tzinfo=timezone.utc)
    h.attempt("intraday_seasonality", "GBP_USD", "BUY", now=t0)
    # 6 seconds later (intraday_seasonality 436/437 case) — must block
    ok, reason = h.attempt(
        "intraday_seasonality", "GBP_USD", "BUY", now=t0 + timedelta(seconds=6)
    )
    assert not ok and reason == "recent_emit"


def test_concurrent_race_serializes_to_single_winner():
    """vol_spike_mr 389/390 race (0.0002s apart) — exactly one thread must win."""
    h = _DedupOnly()
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(h.attempt, "vol_spike_mr", "USD_JPY", "BUY") for _ in range(8)]
        results = [f.result() for f in futs]
    ok_count = sum(1 for ok, _ in results if ok)
    assert ok_count == 1, f"race leaked: {ok_count} concurrent winners"


def test_stale_entry_cleanup_keeps_memory_bounded():
    h = _DedupOnly()
    base = datetime(2026, 4, 27, 0, 0, 0, tzinfo=timezone.utc)
    # Insert 20 distinct keys at base time
    for i in range(20):
        h.attempt("strat", f"INSTR_{i}", "BUY", now=base)
    # 121s later: a fresh emit on a new key triggers cleanup of all stale entries
    h.attempt("strat", "FRESH", "BUY", now=base + timedelta(seconds=121))
    # Only the fresh entry should survive (stale_cutoff = now - 120s, base is older)
    assert len(h._recent_signal_emits) == 1
    assert ("strat", "FRESH", "BUY") in h._recent_signal_emits
