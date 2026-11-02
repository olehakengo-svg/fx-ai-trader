"""tools/wg_gap_drift_measure.py — winter (US DST end) anchor pins (rule:R3, 2026-11-02).

Registry `wg-winter-first-weekend-open-time-check`: the 2026-11-01 monthly
re-run produced drift 0.0 for every offset and no OANDA first-M1 row because
the tool anchored drift offsets, the OANDA search window and the open-delay
base on a nominal Sunday 21:00 UTC. In winter the MASSIVE first bar is 22:00,
so every `bar_at_or_after(21:00 + k)` resolved to that same 22:00 bar
(drift = 0.0, a write-only artifact) and the 20:55-21:30 OANDA window held no
complete bar. The gap anchors (Fri/Sun 21:00 cuts) replicate the detector's
frozen DST-blind definition and are deliberately NOT touched.
"""
from datetime import datetime, timezone

from tools.wg_gap_drift_measure import (
    bar_at_or_after,
    drift_anchor_ms,
    oanda_open_window,
    open_delay_min,
)


def _ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp() * 1000)


def _bars(start_iso: str, n: int) -> list:
    t0 = _ms(start_iso)
    return [{"t": t0 + i * 60_000, "o": 100.0 + i} for i in range(n)]


def test_summer_anchor_is_unchanged_at_2100():
    bars = _bars("2026-09-13T21:00:00+00:00", 30)
    sb = bar_at_or_after(bars, _ms("2026-09-13T21:00:00+00:00"))
    assert drift_anchor_ms(sb["t"]) == _ms("2026-09-13T21:00:00+00:00")
    b5 = bar_at_or_after(bars, drift_anchor_ms(sb["t"]) + 5 * 60_000)
    assert b5["o"] == 105.0  # +5m resolves to a different bar in summer


def test_winter_anchor_follows_the_2200_first_bar():
    # Winter MASSIVE structure (measured 2026-11-01): first Sunday bar 22:00.
    bars = _bars("2026-11-01T22:00:00+00:00", 30)
    sun_2100 = _ms("2026-11-01T21:00:00+00:00")
    sb = bar_at_or_after(bars, sun_2100)          # detector-style cut -> 22:00 bar
    assert sb["t"] == _ms("2026-11-01T22:00:00+00:00")
    # Old behaviour (nominal 21:00 + k) collapses every offset onto the same bar.
    assert bar_at_or_after(bars, sun_2100 + 5 * 60_000)["t"] == sb["t"]
    assert bar_at_or_after(bars, sun_2100 + 15 * 60_000)["t"] == sb["t"]
    # New behaviour: offsets walk forward from the actual first bar.
    base = drift_anchor_ms(sb["t"])
    assert bar_at_or_after(bars, base + 5 * 60_000)["o"] == 105.0
    assert bar_at_or_after(bars, base + 15 * 60_000)["o"] == 115.0


def test_oanda_window_tracks_first_bar_in_both_seasons():
    summer = datetime(2026, 9, 13, 21, 0, tzinfo=timezone.utc)
    t0, t1 = oanda_open_window(summer)
    assert (t0.hour, t0.minute) == (20, 55) and (t1.hour, t1.minute) == (21, 30)
    winter = datetime(2026, 11, 1, 22, 0, tzinfo=timezone.utc)
    t0, t1 = oanda_open_window(winter)
    assert (t0.hour, t0.minute) == (21, 55) and (t1.hour, t1.minute) == (22, 30)
    # The measured 2026-11-01 OANDA first complete M1 (22:04) is inside the window.
    assert t0 <= datetime(2026, 11, 1, 22, 4, tzinfo=timezone.utc) <= t1


def test_open_delay_is_relative_to_massive_first_bar():
    # summer: 21:04 - 21:00 = 4 min (unchanged)
    assert open_delay_min("2026-10-25T21:04:00Z", "2026-10-25T21:00:00+00:00") == 4.0
    # winter: 22:04 - 22:00 = 4 min (old hour=21 base would have said 64)
    assert open_delay_min("2026-11-01T22:04:00Z", "2026-11-01T22:00:00+00:00") == 4.0
    assert open_delay_min("2026-11-01T22:04:00Z", None) is None
    assert open_delay_min("", "2026-11-01T22:00:00+00:00") is None
