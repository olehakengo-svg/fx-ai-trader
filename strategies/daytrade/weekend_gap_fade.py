"""weekend_gap_fade — 週末ギャップ・フェード (pre-reg LOCKED 2026-07-24, rule:R1).

Pre-reg (user 承認済み・凍結):
  knowledge-base/wiki/decisions/weekend-gap-stage2-execution-prereg-2026-07-24.md
OOS verdict (arm B PASS):
  knowledge-base/wiki/decisions/weekend-gap-oos-prereg-2026-07-24.md
実測スプレッド (R1 step①):
  reports/sunday_open_spread-2026-07-24.md

Signal definition — tools/weekend_gap_fill_explore.py の定義を厳密に複製:
  - Friday close = Close of last 15m bar with ts <  Friday 21:00 UTC
                   (guard: bar within 6h before the cutoff)
  - Sunday open  = Open  of first 15m bar with ts >= Sunday 21:00 UTC
                   (guard: bar within 24h after the cutoff; winter open 22:0x
                   はこのガード内に自然に入る)
  - gap          = sunday_open - friday_close (mid price)
  - Qualify      : |gap_pips| >= frozen per-pair threshold (下記)
  - Direction    : fade toward Friday close (gap up -> SELL / gap down -> BUY)
  - Entry window : first bar open ts から 4 bars (bar-length terms; 15m -> 60min)。
                   bar の Open は bar 開始時点で確定するため、初バー出現直後の
                   評価 tick (目標 21:05±2 / 冬 22:05±2, pre-reg §2.2) で発火できる。
                   lookahead なし (Open のみ参照)。

Execution contract (pre-reg §2 — 変更禁止):
  - 成行 1 回のみ、リトライなし (bridge max_attempts=1)
  - 発注時 quoted spread > 10.0p -> live 送信スキップ、shadow row として記録
    (block_cause=weekend_gap_spread_cap — 分母保存)
  - exit = entry +4h time-exit のみ (close_reason="horizon")。
    TP/BE/Trail/SIGNAL_REVERSE/C1 なし。disaster SL 150p のみ。
  - サイジング = 固定 1000u sentinel (lot chain / agg-Kelly / DD lever 非適用)
  - per-pair per-weekend latch は system_kv 永続 (エンジン毎 tick 再構築のため
    instance-state dedup は live で死んでいる — MEMORY
    project_engine_reconstruction_live_dedup_dead)

NOTE: shadow rows use the SAME signal path (this module) — live/shadow の分岐は
demo_trader の共通ガードチェーンのみが行う。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from strategies.base import StrategyBase, Candidate

WEEKEND_GAP_FADE_ENTRY_TYPE = "weekend_gap_fade"

# ── Frozen qualify thresholds (pips) — pre-reg LOCK 2026-07-24 §2.1 ──
# 10x normal round-turn friction, derived in stage-1. FROZEN BY PRE-REG:
# do NOT tune, do NOT recompute from 2026 measured spreads (定義ドリフト禁止).
WEEKEND_GAP_QUALIFY_PIPS = {
    "EUR_USD": 20.0,
    "USD_JPY": 21.4,
    "AUD_USD": 25.0,
}

# Pair allowlist — GBP_USD は永久対象外 (逆符号 family 用に OOS 清浄維持, §2.1)。
WEEKEND_GAP_FADE_PAIRS = frozenset(WEEKEND_GAP_QUALIFY_PIPS.keys())

WEEKEND_GAP_PIP_SIZE = {
    "EUR_USD": 1e-4,
    "USD_JPY": 1e-2,
    "AUD_USD": 1e-4,
}

# ── Frozen execution constants (pre-reg §2.2 / §2.3) ──
WEEKEND_GAP_SPREAD_CAP_PIPS = 10.0      # order-time quoted-spread cap (live skip)
WEEKEND_GAP_DISASTER_SL_PIPS = 150.0    # disaster SL only (発火期待 ~0, tail 防御)
WEEKEND_GAP_MAX_HOLD_SEC = 4 * 3600     # +4h time-exit (close_reason="horizon")
# Engine placeholder TP: the Candidate/DB schema requires a TP float, but the
# pre-reg forbids any TP. 500p is unreachable within the 4h horizon (OOS |gap|
# p90 ~90-100p, 4h MFE p50 9.9p); the OANDA order carries NO takeProfit and the
# monitor loop skips TP-hit for this entry_type.
WEEKEND_GAP_TP_SENTINEL_PIPS = 500.0

# Entry window measured in bar lengths (multi-TF safe): 4 bars of the signal TF
# (15m -> 60 min from the first Sunday bar's open timestamp).
WEEKEND_GAP_ENTRY_WINDOW_BARS = 4

# Explore-definition guards (estimand definition — hours, not TF windows).
FRI_CLOSE_GUARD_H = 6
SUN_OPEN_GUARD_H = 24

_SYMBOL_TO_INSTRUMENT = {
    "USDJPY": "USD_JPY",
    "EURUSD": "EUR_USD",
    "AUDUSD": "AUD_USD",
}


def symbol_to_instrument(symbol: str) -> str:
    """Normalize 'USDJPY=X' / 'USD_JPY' style symbols to OANDA instrument."""
    s = (symbol or "").upper().replace("=X", "").replace("/", "").replace("_", "")
    return _SYMBOL_TO_INSTRUMENT.get(s, "")


def weekend_key_for(now_utc: datetime) -> Optional[str]:
    """Latch key date component for the current weekend window.

    Returns the Sunday date (ISO) when inside the Sunday >=21:00 UTC window,
    else None. The entry window never crosses midnight (first bar 21:00/22:00
    + 4 bars <= 23:15 UTC), so Sunday-only is sufficient.
    """
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    if now_utc.weekday() == 6 and now_utc.hour >= 21:
        return now_utc.date().isoformat()
    return None


def weekend_gap_spread_cap_skip(spread_pips: float) -> bool:
    """True when the quoted spread exceeds the frozen 10.0p live cap.

    Entry_type-scoped E1 replacement (pre-reg §2.2): this cap applies ONLY to
    weekend_gap_fade; all other entry_types keep the standard E1 spread filter.
    """
    return float(spread_pips) > WEEKEND_GAP_SPREAD_CAP_PIPS


def _last_friday_cut(now_utc: datetime) -> datetime:
    """Most recent Friday 21:00 UTC boundary at/before now."""
    d = now_utc
    # step back to Friday
    days_back = (d.weekday() - 4) % 7
    fri = (d - timedelta(days=days_back)).replace(
        hour=21, minute=0, second=0, microsecond=0)
    if fri > now_utc:
        fri -= timedelta(days=7)
    return fri


def detect_weekend_gap_signal(df: pd.DataFrame, instrument: str,
                              now_utc: datetime) -> Optional[dict]:
    """Detect the weekend-gap fade signal (explore-tool definitions, exactly).

    Pure function (no I/O) shared by the live scoped runner, the
    DaytradeEngine strategy path and BT — BT/live unification.

    Returns None when no qualifying event is active, else a dict:
      {direction, gap_pips, fri_close, sunday_open, first_bar_ts,
       weekend_key, qualify_pips}
    """
    if instrument not in WEEKEND_GAP_FADE_PAIRS:
        return None
    if df is None or len(df) < 3:
        return None
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    idx = df.index
    if getattr(idx, "tz", None) is None:
        idx = idx.tz_localize("UTC")

    fri_cut = _last_friday_cut(now_utc)
    sun_cut = fri_cut + timedelta(hours=48)
    if now_utc < sun_cut:
        return None

    # Friday close: last bar strictly < fri_cut, within 6h guard
    i_fri = idx.searchsorted(fri_cut) - 1
    if i_fri < 0 or (fri_cut - idx[i_fri]) > timedelta(hours=FRI_CLOSE_GUARD_H):
        return None
    # Sunday open: first bar >= sun_cut, within 24h guard
    i_sun = idx.searchsorted(sun_cut)
    if i_sun >= len(idx) or (idx[i_sun] - sun_cut) > timedelta(hours=SUN_OPEN_GUARD_H):
        return None

    first_bar_ts = idx[i_sun]

    # Entry window: WEEKEND_GAP_ENTRY_WINDOW_BARS bar-lengths from the first
    # bar's open ts. Bar length inferred from the data (multi-TF safe).
    if len(idx) >= 2:
        diffs = (idx[1:] - idx[:-1]).to_numpy()
        bar_len = pd.Series(diffs).median()
    else:
        bar_len = timedelta(minutes=15)
    window = bar_len * WEEKEND_GAP_ENTRY_WINDOW_BARS
    if now_utc < first_bar_ts or (now_utc - first_bar_ts) > window:
        return None

    pip = WEEKEND_GAP_PIP_SIZE[instrument]
    fri_close = float(df["Close"].iloc[i_fri])
    sunday_open = float(df["Open"].iloc[i_sun])
    gap = sunday_open - fri_close
    gap_pips = gap / pip

    qualify = WEEKEND_GAP_QUALIFY_PIPS[instrument]
    if abs(gap_pips) < qualify:
        return None

    # fade toward Friday close
    direction = "SELL" if gap > 0 else "BUY"
    return {
        "direction": direction,
        "gap_pips": round(gap_pips, 1),
        "fri_close": fri_close,
        "sunday_open": sunday_open,
        "first_bar_ts": first_bar_ts,
        "weekend_key": (sun_cut.date().isoformat()),
        "qualify_pips": qualify,
    }


def build_weekend_gap_sig(det: dict, instrument: str, current_mid: float,
                          atr: float) -> dict:
    """Build the demo_trader-compatible sig dict from a detection result.

    Used by the scoped Sunday runner in demo_trader (single source of truth
    with the DaytradeEngine strategy path below). The sig feeds the NORMAL
    _tick_entry guard chain — this is not a separate send path.
    """
    pip = WEEKEND_GAP_PIP_SIZE[instrument]
    direction = det["direction"]
    if direction == "BUY":
        sl = current_mid - WEEKEND_GAP_DISASTER_SL_PIPS * pip
        tp = current_mid + WEEKEND_GAP_TP_SENTINEL_PIPS * pip
        score = 8.0
    else:
        sl = current_mid + WEEKEND_GAP_DISASTER_SL_PIPS * pip
        tp = current_mid - WEEKEND_GAP_TP_SENTINEL_PIPS * pip
        score = -8.0  # daytrade pipeline convention: SELL carries negative score
    reasons = [
        (f"✅ [WEEKEND_GAP] gap={det['gap_pips']:+.1f}p >= qualify "
         f"{det['qualify_pips']:.1f}p ({instrument}) → fade {direction} "
         f"toward Fri close {det['fri_close']:.5f} "
         f"(pre-reg LOCK 2026-07-24, exit=+4h horizon, disaster SL 150p)"),
    ]
    return {
        "signal": direction,
        "entry": float(current_mid),
        "confidence": 70,
        "sl": float(sl),
        "tp": float(tp),
        "entry_type": WEEKEND_GAP_FADE_ENTRY_TYPE,
        "reasons": reasons,
        "score": score,
        "atr": float(atr),
        "sr_meta": None,
        "sr_entry_map": {},
        "regime": {},
        "layer_status": {},
        "indicators": {},
        "max_hold_bars": None,
        "lot_multiplier": 1.0,
        # G1 gate 入力 (pre-reg §5): slippage は「fill vs signal_price、spread
        # とは独立」が凍結定義。entry_fill basis → demo_trader 側で
        # _signal_price = 発注判定時の同サイド OANDA quote (BUY=ask/SELL=bid)
        # となり、quoted half-spread が slippage に混入しない。
        # "signal_entry" (yfinance mid) だと日曜 open の実測 4〜10p spread の
        # 約半分 (+2〜5p) が構造的に乗り、真の slippage ゼロでも G1 (+2.0p)
        # がほぼ確定的に誤発火して live が N=6 で恒久停止する (review blocker
        # fix 2026-07-25)。
        "slippage_signal_price_basis": "entry_fill",
        "_closed_bar_ts": det["first_bar_ts"],
        "_weekend_gap": dict(det),
    }


class WeekendGapFade(StrategyBase):
    """DaytradeEngine 登録用の戦略クラス (redundant path).

    Primary execution は demo_trader._weekend_gap_tick の scoped runner
    (夏時間の日曜 21:0x は market-closed gate で通常 tick が走らないため)。
    このクラスは通常エンジン経路 (冬 22:00+ 等) の冗長系で、system_kv latch が
    二重発注を防ぐ。どちらの経路も同一の detect_weekend_gap_signal を使う。
    """

    name = "weekend_gap_fade"  # == WEEKEND_GAP_FADE_ENTRY_TYPE (literal for tier_integrity_check discovery)
    mode = "daytrade"
    enabled = True
    strategy_type = "MR"

    def evaluate(self, ctx) -> Optional[Candidate]:
        instrument = symbol_to_instrument(getattr(ctx, "symbol", ""))
        if instrument not in WEEKEND_GAP_FADE_PAIRS:
            return None
        if getattr(ctx, "backtest_mode", False) and ctx.bar_time is not None:
            now_utc = ctx.bar_time
            if getattr(now_utc, "tzinfo", None) is None:
                now_utc = now_utc.replace(tzinfo=timezone.utc)
        else:
            now_utc = datetime.now(timezone.utc)
        det = detect_weekend_gap_signal(ctx.df, instrument, now_utc)
        if det is None:
            return None
        sig = build_weekend_gap_sig(det, instrument, float(ctx.entry),
                                    float(ctx.atr))
        return Candidate(
            signal=sig["signal"],
            confidence=sig["confidence"],
            sl=sig["sl"],
            tp=sig["tp"],
            reasons=list(sig["reasons"]),
            entry_type=self.name,
            score=abs(sig["score"]),  # Candidate.score is magnitude; sign is applied downstream
        )
