#!/usr/bin/env python3
"""Event-modality (E15/E7) の estimand コア — pre-reg §3.5/§4/§5a の忠実な転記 (rule:R1 手続き).

pre-reg SSOT: knowledge-base/wiki/decisions/e15-e7-event-modality-prereg-2026-07-18.md
タスク票    : .ai/tasks/queue/20260718-e15-e7-event-phase0.md

**このモジュールは「設計自由度ゼロ — 執行のみ」の pre-reg §3.5 を関数化したもの。**
探索ハーネス (event_modality_explore.py) と判定器 (event_modality_oos_verdict.py) の
両方が本 lib を共有し、estimand を 1 箇所に正規化する (SSOT)。

pre-reg §3.5 執行 estimand の要点 (round-3 crossasset harness との差分を明示):
  - entry     = 指定バーの **open** (mid)。round-3 は close entry — 別物。
  - 前方リターン終端 = 指定 horizon バーの **open** (round-3 は close) — §3.5 に忠実。
  - horizon   = market-time bar count (h4=16 / h12=48 / h24=96 M15 bars。E7 は h1=4 追加)。
  - first-touch レグ: TP = SL = 1.0 × σ_h。**同一バー内 TP+SL 両ヒットは SL 優先**
    (round-3 は TP 優先 — ハウス保守規約に反するので**再利用禁止**、本 lib で SL 優先を実装)。
  - σ_h = ATR14d × √(h/24h)。ATR14d = t より厳密に前に完結した直近 14 本の daily bar
    (NY 17:00 roll、M15 から構築) の TR 平均。
  - 摩擦 = §3.5 凍結テーブル (往復 pips)。
  - censoring: horizon 完結が cache 末尾を超えるイベントは不算入 (事後裁量処理の構造排除)。

**副作用禁止**: 本モジュールは import 時に I/O も argparse も実行しない (tools 二重存在の教訓)。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date as _date
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

# ─── §4 ペア族 ──────────────────────────────────────────────────────────────
# Primary block = USD-leg 7 ペア (US マクロイベントの機構が直接通るペアのみで判定)。
PRIMARY_PAIRS = [
    "USD_JPY", "EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD", "USD_CAD", "USD_CHF",
]
# Cross block = 6 ペア (confirmatory/記述のみ、判定に不使用)。
CROSS_PAIRS = ["EUR_JPY", "GBP_JPY", "AUD_JPY", "NZD_JPY", "EUR_GBP", "EUR_AUD"]
ALL_PAIRS = PRIMARY_PAIRS + CROSS_PAIRS

# ─── §3.5 摩擦 (判定値、往復 pips、E1 §3.4 凍結テーブルの再利用 — 今固定) ─────────
FRICTION = {
    "USD_JPY": 2.14, "EUR_USD": 2.00, "GBP_USD": 4.53, "EUR_JPY": 2.50,
    "GBP_JPY": 4.50, "AUD_JPY": 3.125, "EUR_GBP": 3.00, "AUD_USD": 2.50,
    "NZD_USD": 3.00, "USD_CAD": 3.00, "USD_CHF": 3.00, "NZD_JPY": 4.50,
    "EUR_AUD": 4.50,
}


def pip_size(pair: str) -> float:
    """JPY クロス = 0.01、それ以外 = 0.0001 (§3.1)。"""
    return 0.01 if pair.endswith("JPY") else 0.0001


# ─── §3.5 horizon → M15 bar count ────────────────────────────────────────────
# market-time bar count (週末ギャップは経過時間に数えない = bar count で表現)。
BARS_PER_HOUR = 4  # M15
HORIZON_BARS = {"h1": 4, "h4": 16, "h12": 48, "h24": 96}
HORIZON_HOURS = {"h1": 1, "h4": 4, "h12": 12, "h24": 24}
E15_HORIZONS = ["h4", "h12", "h24"]  # §5a primary
E7_HORIZONS = ["h1", "h4", "h24"]    # §6

# ─── §3.2 イベント時刻 (ET 固定) ────────────────────────────────────────────
_NY = ZoneInfo("America/New_York")
_UTC = ZoneInfo("UTC")
EVENT_TIME_ET = {
    "FOMC": (14, 0),   # 14:00 ET (2013 以降固定)
    "NFP": (8, 30),    # 08:30 ET
    "CPI": (8, 30),    # 08:30 ET
}


def et_to_utc(day: _date, hh: int, mm: int) -> pd.Timestamp:
    """America/New_York の per-date 変換で ET 時刻を UTC Timestamp へ (DST 追随)。

    固定 UTC オフセットは spec バグ (E1 レビュー M11 の教訓) — zoneinfo で per-date 変換。
    14:00 ET / 08:30 ET はいずれも M15 バー境界 (:00/:30) に整列する。
    """
    naive = datetime(day.year, day.month, day.day, hh, mm)
    aware_ny = naive.replace(tzinfo=_NY)
    return pd.Timestamp(aware_ny.astimezone(_UTC))


def event_time_utc(event_type: str, day: _date) -> pd.Timestamp:
    hh, mm = EVENT_TIME_ET[event_type]
    return et_to_utc(day, hh, mm)


# ─── §4 USD-leg 方向変換 ────────────────────────────────────────────────────
def usd_leg_dir(pair: str, usd_long: bool) -> int:
    """USD 軸 (uncond / E7 sign-follow) を per-pair の発注方向へ機械変換 (§4)。

    USD_JPY BUY = USD long、EUR_USD SELL = USD long。
    クロス (USD 露出なし) は 0 を返す = uncond/E7 は定義されない (§4)。
    """
    base, quote = pair.split("_")
    if base == "USD":       # USD が base: BUY = USD long
        return 1 if usd_long else -1
    if quote == "USD":      # USD が quote: SELL = USD long
        return -1 if usd_long else 1
    return 0                # cross: USD-uncond 未定義


# ─── §3.5 daily bar (NY 17:00 roll) + ATR14d ────────────────────────────────
def build_daily_from_m15(m15: pd.DataFrame) -> pd.DataFrame:
    """M15 (UTC index) から NY 17:00 roll の daily OHLC を構築 (§3.5)。

    FX trading day = 前営業日 17:00 NY → 当日 17:00 NY。各 M15 バーを
    (ny_time − 17h) の暦日でグループ化する。
    """
    if not isinstance(m15.index, pd.DatetimeIndex):
        raise ValueError("m15 index must be DatetimeIndex")
    idx_utc = m15.index if m15.index.tz is not None else m15.index.tz_localize("UTC")
    ny = idx_utc.tz_convert(_NY)
    trade_day = (ny - pd.Timedelta(hours=17)).normalize().date
    g = pd.DataFrame(
        {"Open": m15["Open"].values, "High": m15["High"].values,
         "Low": m15["Low"].values, "Close": m15["Close"].values},
        index=pd.Index(trade_day, name="trade_day"),
    )
    daily = g.groupby(level=0).agg(
        Open=("Open", "first"), High=("High", "max"),
        Low=("Low", "min"), Close=("Close", "last"),
    )
    daily.index = pd.to_datetime(daily.index)
    return daily.sort_index()


def _true_range(daily: pd.DataFrame) -> pd.Series:
    prev_close = daily["Close"].shift(1)
    tr = pd.concat([
        daily["High"] - daily["Low"],
        (daily["High"] - prev_close).abs(),
        (daily["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def atr14d_before(daily: pd.DataFrame, t: pd.Timestamp) -> float:
    """t より厳密に前に完結した直近 14 本の daily bar の TR 平均 (§3.5)。

    「厳密に前に完結」= daily bar の trade_day (= NY 17:00 roll 起点日) が t の
    trade_day より前。look-ahead を構造排除する。
    """
    t_utc = pd.Timestamp(t).tz_convert(_UTC) if pd.Timestamp(t).tz is not None else pd.Timestamp(t, tz=_UTC)
    t_ny = t_utc.tz_convert(_NY)
    t_trade_day = pd.Timestamp((t_ny - pd.Timedelta(hours=17)).normalize().date())
    tr = _true_range(daily)
    completed = tr[daily.index < t_trade_day].dropna()
    if len(completed) < 14:
        return float("nan")
    return float(completed.iloc[-14:].mean())


def sigma_h(atr14d: float, horizon: str) -> float:
    """σ_h = ATR14d × √(h/24h) (§3.5)。"""
    return atr14d * math.sqrt(HORIZON_HOURS[horizon] / 24.0)


# ─── §5a 初期反応 R0 ────────────────────────────────────────────────────────
def _bar_pos(index: pd.DatetimeIndex, ts: pd.Timestamp) -> int | None:
    """ts に開くバーの整数位置 (完全一致のみ)。無ければ None。"""
    try:
        return int(index.get_loc(ts))
    except KeyError:
        return None


def compute_r0(m15: pd.DataFrame, t_e: pd.Timestamp, w0_min: int) -> float | None:
    """P0 = t_e に開くバーの open。R0(W0) = close(t_e+W0 に終わるバー) − P0 (§5a)。

    look-ahead なし: t_e と t_e+W0 のバーのみ参照 (どちらも entry ≥ t_e+W0 より前)。
    """
    idx = m15.index
    p0_pos = _bar_pos(idx, t_e)
    if p0_pos is None:
        return None
    # t_e+W0 に「終わる」バー = [t_e+W0-15m, t_e+W0) の open が t_e+W0-15m のバー
    end_bar_open = pd.Timestamp(t_e) + pd.Timedelta(minutes=w0_min - 15)
    end_pos = _bar_pos(idx, end_bar_open)
    if end_pos is None or end_pos >= len(m15):
        return None
    p0 = float(m15["Open"].iloc[p0_pos])
    close_w0 = float(m15["Close"].iloc[end_pos])
    return close_w0 - p0


# ─── §5a rule → 方向 ────────────────────────────────────────────────────────
def rule_direction(rule: str, pair: str, r0: float | None) -> int:
    """§5a の 4 ルールを方向 (+1 BUY / −1 SELL / 0 no-trade) へ。

    fade = −sign(R0) / follow = +sign(R0) / uncond-USD-long / uncond-USD-short。
    """
    if rule == "fade":
        return 0 if r0 is None or r0 == 0 else int(-np.sign(r0))
    if rule == "follow":
        return 0 if r0 is None or r0 == 0 else int(np.sign(r0))
    if rule == "uncond_usd_long":
        return usd_leg_dir(pair, True)
    if rule == "uncond_usd_short":
        return usd_leg_dir(pair, False)
    raise ValueError(f"unknown rule: {rule}")


# ─── §3.5 トレード結果 (time-exit + first-touch、SL 優先) ─────────────────────
@dataclass
class TradeOutcome:
    time_exit_pip: float   # friction 調整後
    first_touch_pip: float  # friction 調整後
    direction: int
    entry_pos: int
    censored: bool
    weekend_span: bool
    atr: float = float("nan")  # entry 時 ATR14d (price 単位) — §5c レグA の正規化用に露出


def event_trade(
    m15: pd.DataFrame,
    daily: pd.DataFrame,
    t_e: pd.Timestamp,
    pair: str,
    rule: str,
    w0_min: int,
    horizon: str,
    friction: float | None = None,
    entry_delay_bars: int = 0,
) -> TradeOutcome | None:
    """1 イベント × pair × rule × W0 × horizon の estimand (§3.5 執行契約)。

    entry = t_e+W0 の直後の M15 バー open。terminal = entry_pos + h_bars の open。
    first-touch: TP=SL=1.0σ_h、scan は entry バー〜terminal 直前バー、SL 優先。
    censoring: terminal が cache 末尾を超えるイベントは None (不算入)。
    entry_delay_bars: §5c ナイフエッジ#3 (遅延 canary) 専用 — entry のみ +N バー遅延、
    R0 の定義 (W0 窓) は不変。default 0 = estimand 本体 (挙動不変)。
    """
    if friction is None:
        friction = FRICTION[pair]
    pip = pip_size(pair)
    idx = m15.index

    r0 = compute_r0(m15, t_e, w0_min) if rule in ("fade", "follow") else 0.0
    d = rule_direction(rule, pair, r0)
    if d == 0:
        return None

    # entry バー = t_e+W0 に開くバー。uncond は W0=30m に固定 (§5a)。
    entry_open_ts = (pd.Timestamp(t_e)
                     + pd.Timedelta(minutes=w0_min + 15 * entry_delay_bars))
    e = _bar_pos(idx, entry_open_ts)
    if e is None:
        return None
    h_bars = HORIZON_BARS[horizon]
    term = e + h_bars
    if term >= len(m15):
        return None  # censoring — horizon 完結が cache 末尾超え (§3.4)

    atr = atr14d_before(daily, entry_open_ts)
    if not np.isfinite(atr) or atr <= 0:
        return None
    barrier = sigma_h(atr, horizon)  # price 単位 (TP=SL=1.0σ_h)

    o = m15["Open"].values
    hi = m15["High"].values
    lo = m15["Low"].values
    entry = float(o[e])
    tp = entry + d * barrier
    sl = entry - d * barrier

    # first-touch scan: entry バー e 〜 terminal 直前バー (term-1)。
    # 保有窓 = [open[e], open[term]] → バー e..term-1 の range が窓内。
    # 同一バー内 TP+SL 両ヒット = SL 優先 (§3.5 ハウス保守規約)。
    ft_pip = None
    for j in range(e, term):
        hit_tp = (hi[j] >= tp) if d > 0 else (lo[j] <= tp)
        hit_sl = (lo[j] <= sl) if d > 0 else (hi[j] >= sl)
        if hit_sl:            # SL 優先
            ft_pip = -barrier / pip
            break
        if hit_tp:
            ft_pip = barrier / pip
            break
    if ft_pip is None:
        ft_pip = d * (float(o[term]) - entry) / pip  # timeout = open[term]

    time_exit_pip = d * (float(o[term]) - entry) / pip

    # 週末跨ぎフラグ (§3.5、除外せず記録)
    weekend_span = bool((idx[term] - idx[e]) > pd.Timedelta(hours=h_bars / BARS_PER_HOUR + 24))

    return TradeOutcome(
        time_exit_pip=time_exit_pip - friction,
        first_touch_pip=ft_pip - friction,
        direction=d,
        entry_pos=e,
        censored=False,
        weekend_span=weekend_span,
        atr=atr,
    )


# ─── §5c-3 リーク / 遅延 canary ──────────────────────────────────────────────
def leak_canary(m15: pd.DataFrame, daily: pd.DataFrame, t_e: pd.Timestamp,
                pair: str, rule: str, w0_min: int, horizon: str) -> bool:
    """未来リターンを注入しても estimand が変化しないことを検出する canary (§5c-3)。

    entry バー以降 (t_e+W0 以降) の bar を破壊しても R0/ATR/方向は不変であるべき
    (R0 は t_e..t_e+W0、ATR は entry 前 daily のみ参照)。変化したら look-ahead を疑う。
    R0 経路と **ATR 経路の両方** を比較する (§5c-3 明文「R0 / ATR 経路」)。
    True = リークなし (canary OK)。
    """
    entry_open_ts = pd.Timestamp(t_e) + pd.Timedelta(minutes=w0_min)
    r0_a = compute_r0(m15, t_e, w0_min)
    atr_a = atr14d_before(daily, entry_open_ts)
    d_a = rule_direction(rule, pair, r0_a if rule in ("fade", "follow") else 0.0)

    # entry バー以降の値を NaN 化した frame で再計算
    poison = m15.copy()
    e = _bar_pos(m15.index, entry_open_ts)
    if e is not None:
        for col in ("Open", "High", "Low", "Close"):
            poison.iloc[e:, poison.columns.get_loc(col)] = np.nan
    try:
        r0_b = compute_r0(poison, t_e, w0_min)
        atr_b = atr14d_before(build_daily_from_m15(poison.dropna()), entry_open_ts) if not poison.dropna().empty else atr_a
        d_b = rule_direction(rule, pair, r0_b if rule in ("fade", "follow") else 0.0)
    except (ValueError, TypeError):
        # 破壊 frame で再計算が壊れる = 未来バー依存が確実 → リーク検出 (False)
        return False

    def _eq(a, b):
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        if isinstance(a, float) and isinstance(b, float) \
                and math.isnan(a) and math.isnan(b):
            return True  # 両方 NaN (履歴不足) = 同一状態
        return abs(a - b) < 1e-9

    return _eq(r0_a, r0_b) and d_a == d_b and _eq(float(atr_a), float(atr_b))


# ─── §3.1 coverage gate ─────────────────────────────────────────────────────
def market_time_coverage(m15: pd.DataFrame, start: str, end: str) -> float:
    """discovery 窓の market-time M15 スロット被覆率 (§3.1 coverage gate 用)。

    分母 = 期間内の Mon-Fri 営業日 × 96 slot (24h)。分子 = 実バー数。
    < 0.90 のペアは family から機械除外 (呼び出し側で判定)。
    """
    sub = m15.loc[(m15.index >= pd.Timestamp(start, tz=_UTC)) & (m15.index <= pd.Timestamp(end, tz=_UTC))]
    if sub.empty:
        return 0.0
    bdays = int(len(pd.bdate_range(sub.index[0].normalize(), sub.index[-1].normalize())))
    expected = max(1, bdays * 96)
    return min(1.0, len(sub) / expected)


COVERAGE_GATE = 0.90
