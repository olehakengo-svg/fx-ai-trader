"""Event-modality estimand lib の契約 pin (rule:R1 手続き、pre-reg §10-6).

pre-reg: knowledge-base/wiki/decisions/e15-e7-event-modality-prereg-2026-07-18.md
「canary/leak/join 契約を tests/ に pin してから OOS データに触れる」(§10-6) の履行。
合成データ (ground-truth 既知) で estimand の忠実性を検証する — 実 OOS データ不使用。

pin する契約:
  - ET→UTC per-date DST (§3.2)、M15 境界整列
  - USD-leg 方向変換 (§4)
  - fade/follow/uncond 方向 (§5a)
  - first-touch **SL 優先** (§3.5 — round-3 の TP 優先からの逸脱を封鎖)
  - entry=open / terminal=open の time-exit (§3.5)
  - σ_h = ATR14d × √(h/24h) (§3.5)
  - censoring (§3.4)
  - R0 look-ahead 無し (§5c-3 canary)
  - ATR14d の「厳密に前に完結」(§3.5)
"""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from tools import event_modality_lib as L


# ─── 合成 M15 frame ビルダ ───────────────────────────────────────────────────
def _make_m15(n, start="2024-06-01 00:00", base=1.1000, step_min=15):
    idx = pd.date_range(start=pd.Timestamp(start, tz="UTC"), periods=n,
                        freq=f"{step_min}min")
    o = np.full(n, base)
    return pd.DataFrame({"Open": o, "High": o + 0.0002, "Low": o - 0.0002,
                         "Close": o.copy()}, index=idx)


# ─── §3.2 ET→UTC DST ────────────────────────────────────────────────────────
def test_et_to_utc_dst_fomc():
    # FOMC 14:00 ET: 冬 (EST=UTC-5) → 19:00 UTC / 夏 (EDT=UTC-4) → 18:00 UTC
    winter = L.et_to_utc(date(2024, 1, 31), 14, 0)
    summer = L.et_to_utc(date(2024, 7, 31), 14, 0)
    assert winter.hour == 19 and winter.minute == 0
    assert summer.hour == 18 and summer.minute == 0


def test_et_to_utc_dst_nfp_and_m15_alignment():
    # NFP/CPI 08:30 ET: 冬 → 13:30 UTC / 夏 → 12:30 UTC
    winter = L.et_to_utc(date(2024, 1, 5), 8, 30)
    summer = L.et_to_utc(date(2024, 7, 5), 8, 30)
    assert (winter.hour, winter.minute) == (13, 30)
    assert (summer.hour, summer.minute) == (12, 30)
    # M15 境界整列 (:00/:15/:30/:45)
    for ts in (winter, summer, L.et_to_utc(date(2024, 3, 20), 14, 0)):
        assert ts.minute in (0, 15, 30, 45)


# ─── §4 USD-leg 方向 ────────────────────────────────────────────────────────
def test_usd_leg_dir():
    assert L.usd_leg_dir("USD_JPY", True) == 1     # USD base, long → BUY
    assert L.usd_leg_dir("USD_CAD", True) == 1
    assert L.usd_leg_dir("EUR_USD", True) == -1    # USD quote, long → SELL
    assert L.usd_leg_dir("EUR_USD", False) == 1    # short-USD → BUY EUR_USD
    assert L.usd_leg_dir("GBP_USD", True) == -1
    assert L.usd_leg_dir("EUR_JPY", True) == 0     # cross: 未定義


# ─── §5a fade/follow 方向 ───────────────────────────────────────────────────
def test_rule_direction_fade_follow():
    assert L.rule_direction("fade", "EUR_USD", 0.0015) == -1
    assert L.rule_direction("fade", "EUR_USD", -0.0015) == 1
    assert L.rule_direction("follow", "EUR_USD", 0.0015) == 1
    assert L.rule_direction("follow", "EUR_USD", -0.0015) == 1 * -1  # follow neg → -1
    assert L.rule_direction("fade", "EUR_USD", 0.0) == 0            # no-trade


# ─── §3.5 σ_h スケーリング ──────────────────────────────────────────────────
def test_sigma_h_scaling():
    atr = 0.0060
    assert L.sigma_h(atr, "h24") == pytest.approx(atr)              # √(24/24)=1
    assert L.sigma_h(atr, "h4") == pytest.approx(atr * np.sqrt(4 / 24))
    assert L.sigma_h(atr, "h12") == pytest.approx(atr * np.sqrt(0.5))


# ─── §3.5 first-touch SL 優先 (round-3 TP 優先からの逸脱封鎖) ─────────────────
def test_first_touch_sl_priority(monkeypatch):
    monkeypatch.setattr(L, "atr14d_before", lambda daily, t: 0.0050)  # barrier(h24)=50pip
    m = _make_m15(300)
    t_e = m.index[100]
    e = 100 + 2  # entry = t_e + 30m (2 M15 バー後)
    # entry バーで TP(1.1050) と SL(1.0950) を同一バーで両ヒット → SL 優先で LOSS
    m.iloc[e, m.columns.get_loc("Open")] = 1.1000
    m.iloc[e, m.columns.get_loc("High")] = 1.1060   # ≥ TP
    m.iloc[e, m.columns.get_loc("Low")] = 1.0940    # ≤ SL
    out = L.event_trade(m, m, t_e, "EUR_USD", "uncond_usd_short", 30, "h24")
    assert out is not None and out.direction == 1
    # LOSS = -barrier/pip - friction = -50 - 2.00
    assert out.first_touch_pip == pytest.approx(-50.0 - 2.00)


# ─── §3.5 entry=open / terminal=open time-exit ──────────────────────────────
def test_time_exit_open_to_open(monkeypatch):
    monkeypatch.setattr(L, "atr14d_before", lambda daily, t: 0.0050)
    m = _make_m15(300)
    t_e = m.index[100]
    e = 102
    term = e + L.HORIZON_BARS["h24"]  # 96 バー後
    # barrier に触れないよう range を狭く保ち、terminal open を +30pip に設定
    m.iloc[e, m.columns.get_loc("Open")] = 1.1000
    m.iloc[term, m.columns.get_loc("Open")] = 1.1030
    out = L.event_trade(m, m, t_e, "EUR_USD", "uncond_usd_short", 30, "h24")
    assert out is not None
    # d=+1: time_exit = (1.1030-1.1000)/0.0001 - 2.00 = 30 - 2 = 28
    assert out.time_exit_pip == pytest.approx(28.0)
    # 無ヒット → first-touch も timeout = 同値
    assert out.first_touch_pip == pytest.approx(28.0)


# ─── §3.4 censoring ─────────────────────────────────────────────────────────
def test_censoring_beyond_cache_end(monkeypatch):
    monkeypatch.setattr(L, "atr14d_before", lambda daily, t: 0.0050)
    m = _make_m15(150)          # entry(102) + 96 = 198 > 150 → censored
    t_e = m.index[100]
    out = L.event_trade(m, m, t_e, "EUR_USD", "uncond_usd_short", 30, "h24")
    assert out is None


# ─── §5a compute_r0 look-ahead 無し (canary) ────────────────────────────────
def test_compute_r0_no_lookahead():
    m = _make_m15(300)
    t_e = m.index[100]
    m.iloc[100, m.columns.get_loc("Open")] = 1.1000   # P0
    m.iloc[101, m.columns.get_loc("Close")] = 1.1010  # close(t_e+30m に終わるバー)
    r0_clean = L.compute_r0(m, t_e, 30)
    assert r0_clean == pytest.approx(0.0010)
    # entry (t_e+30m = idx 102) 以降を破壊しても R0 は不変であるべき
    poison = m.copy()
    poison.iloc[102:, :] = np.nan
    assert L.compute_r0(poison, t_e, 30) == pytest.approx(0.0010)


# ─── §3.5 ATR14d の「厳密に前に完結」+ daily 構築 ───────────────────────────
def test_atr14d_uses_only_prior_days():
    # 20 日分の M15 (96 bar/日、連続)。各日 range を一定にして ATR を既知化する
    n = 96 * 20
    idx = pd.date_range("2024-06-01 00:00", periods=n, freq="15min", tz="UTC")
    # 日ごとに base をずらし、High-Low は毎日 0.0100 一定 (TR≈0.0100)
    day_idx = np.arange(n) // 96
    base = 1.1000 + day_idx * 0.0001
    df = pd.DataFrame({"Open": base, "High": base + 0.0050,
                       "Low": base - 0.0050, "Close": base}, index=idx)
    daily = L.build_daily_from_m15(df)
    assert len(daily) >= 15
    # 15 日目時点の ATR は約 0.0100 (TR = High-Low = 0.0100 が支配)
    t = idx[96 * 16]
    atr = L.atr14d_before(daily, t)
    assert atr == pytest.approx(0.0100, abs=0.002)
    # 履歴不足 (先頭付近) は NaN
    assert np.isnan(L.atr14d_before(daily, idx[96 * 2]))


# ─── §5c-3 leak canary (uncond 経路) ────────────────────────────────────────
def test_leak_canary_clean(monkeypatch):
    monkeypatch.setattr(L, "atr14d_before", lambda daily, t: 0.0050)
    m = _make_m15(300)
    t_e = m.index[100]
    assert L.leak_canary(m, m, t_e, "EUR_USD", "uncond_usd_short", 30, "h24") is True


# ─── §3.1 coverage ─────────────────────────────────────────────────────────
def test_market_time_coverage_full():
    # 連続 M15 (週末含む) → bdate 分母より実バーが多く 1.0 にクリップ
    m = _make_m15(96 * 30)
    cov = L.market_time_coverage(m, "2024-06-01", "2024-06-20")
    assert 0.9 <= cov <= 1.0
