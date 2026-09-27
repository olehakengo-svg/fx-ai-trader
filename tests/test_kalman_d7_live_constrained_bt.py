"""Pins for tools/kalman_d7_live_constrained_bt.py (rule:R3 診断ツール).

各 overlay は「通る入力 → 発火 / 通らない入力 → 不発」の両側を pin する。
合成 bar で simulate() を直接叩く (indicator 計算は tools/kalman_d7_v18e_python_port の既存 pin に委ねる)。
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from tools import kalman_d7_live_constrained_bt as K


def _bars(n: int, start: str = "2025-09-16 08:00", price: float = 150.000, atr: float = 0.100,
          signal_at: int = 5) -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="15min", tz="UTC")
    df = pd.DataFrame({
        "Open": price, "High": price + 0.002, "Low": price - 0.002, "Close": price,
        "atr": atr, "entry_signal": False, "perfect_up": True, "perfect_dn": False,
        "in_window": True,
    }, index=idx)
    df.iloc[signal_at, df.columns.get_loc("entry_signal")] = True
    return df


def _one(trades):
    assert len(trades) == 1, [t.exit_reason for t in trades]
    return trades[0]


# ── walk 0 / canon exits ───────────────────────────────────────────────────
def test_flip_exit_fires_on_perfect_dn_close():
    df = _bars(60)
    df.iloc[20, df.columns.get_loc("perfect_dn")] = True
    t = _one(K.simulate(df, K.StackConfig(exit_mode="flip")))
    assert t.exit_reason == "PO_DN_FLIP"
    assert t.bars_held == 15  # signal bar 5 → exit bar 20


def test_canon_cap_480_bars_when_nothing_else_fires():
    df = _bars(520, atr=0.100)
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5")))
    assert t.exit_reason == "CANON_CAP_480"
    assert t.bars_held == 480


def test_tp5_exit_at_declared_tp_and_sl_at_declared_sl():
    df = _bars(40)
    entry = 150.000 + K.MINTICK
    df.iloc[10, df.columns.get_loc("High")] = entry + 5.0 * 0.100 + 0.001
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5")))
    assert t.exit_reason == "TP_HIT" and t.exit == pytest.approx(round(entry + 0.5, 3), abs=1e-6)

    df = _bars(40)
    df.iloc[10, df.columns.get_loc("Low")] = entry - 1.5 * 0.100 - 0.001
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5")))
    assert t.exit_reason == "SL_HIT" and t.decl_sl == pytest.approx(round(entry - 0.15, 3))


# ── C1 / C5 (tick-based at bar open) ─────────────────────────────────────
def test_c1_max_hold_fires_at_8h_and_not_without_flag():
    df = _bars(80)
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c1=True)))
    assert t.exit_reason == "MAX_HOLD_TIME"
    assert t.hold_sec == pytest.approx(K.C1_MAX_HOLD_SEC)
    t0 = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c1=False, canon_cap=False)))
    assert t0.exit_reason == "EOD"


def test_c5_time_decay_only_when_in_loss_after_4h():
    entry = 150.000 + K.MINTICK
    df = _bars(80)
    # 4h 経過後は entry より僅かに下 (SL 1.5×ATR=15p には届かない)
    below = entry - 0.010
    for j in range(22, 80):
        df.iloc[j, [df.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [below, below + 0.002, below - 0.002, below]
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c5=True)))
    assert t.exit_reason == "TIME_DECAY_EXIT"
    assert t.hold_sec > K.C5_HALF_HOLD_SEC
    # 含み益側は C5 で切られない
    df2 = _bars(80)
    above = entry + 0.010
    for j in range(22, 80):
        df2.iloc[j, [df2.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [above, above + 0.002, above - 0.002, above]
    t2 = _one(K.simulate(df2, K.StackConfig(exit_mode="tp5", c5=True, canon_cap=False)))
    assert t2.exit_reason == "EOD"


# ── C2 weekend ───────────────────────────────────────────────────────────
def test_c2_weekend_close_on_last_friday_bar_before_gap():
    # 2025-09-19 は金曜。金曜 20:45 の後に 日曜 21:00 まで gap
    fri = pd.date_range("2025-09-19 12:00", "2025-09-19 20:45", freq="15min", tz="UTC")
    sun = pd.date_range("2025-09-21 21:00", periods=40, freq="15min", tz="UTC")
    idx = fri.append(sun)
    df = pd.DataFrame({"Open": 150.0, "High": 150.002, "Low": 149.998, "Close": 150.0, "atr": 0.1,
                       "entry_signal": False, "perfect_up": True, "perfect_dn": False, "in_window": True}, index=idx)
    df.iloc[2, df.columns.get_loc("entry_signal")] = True
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c2=True)))
    assert t.exit_reason == "WEEKEND_CLOSE"
    assert pd.Timestamp(t.exit_time) == pd.Timestamp("2025-09-19 21:00", tz="UTC")
    t0 = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c2=False, canon_cap=False)))
    assert t0.exit_reason == "EOD"


# ── C3/C4 と bar 内順序仮定 ───────────────────────────────────────────────
def test_be_trail_ordering_assumption_changes_same_bar_outcome():
    entry = 150.000 + K.MINTICK
    df = _bars(40, atr=0.100)
    # bar 12: 高値で BE 到達 (0.8×ATR=8p) かつ 安値で原 SL (15p) 到達
    df.iloc[12, df.columns.get_loc("High")] = entry + 0.090
    df.iloc[12, df.columns.get_loc("Low")] = entry - 0.160
    adv = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c3c4=True, order="adverse_first")))
    fav = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c3c4=True, order="favorable_first")))
    assert adv.exit_reason == "SL_HIT"
    assert fav.exit_reason == "BE"
    assert fav.exit == pytest.approx(round(entry + K.C3_BE_SPREAD, 3) - K.MINTICK, abs=1e-6)


def test_trail_exit_after_1p5_atr_mfe():
    entry = 150.000 + K.MINTICK
    df = _bars(40, atr=0.100)
    df.iloc[10, df.columns.get_loc("High")] = entry + 0.200   # MFE 20p ≥ 1.5×ATR → trail SL = 20p − 5p = +15p
    df.iloc[11, df.columns.get_loc("Low")] = entry + 0.100    # trail SL に触る
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c3c4=True)))
    assert t.exit_reason == "TRAIL"
    assert t.exit == pytest.approx(round(entry + 0.150, 3) - K.MINTICK, abs=1e-6)


# ── C6 近似 ──────────────────────────────────────────────────────────────
def test_c6_approx_requires_po_collapse_and_no_profit_guard():
    entry = 150.000 + K.MINTICK
    df = _bars(40)
    df.iloc[10:, df.columns.get_loc("perfect_up")] = False
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c6=True)))
    assert t.exit_reason == "SIGNAL_REVERSE_APPROX"
    # 含み益 > 0.3×ATR は保護 (切らない)
    df2 = _bars(40)
    df2.iloc[10:, df2.columns.get_loc("perfect_up")] = False
    up = entry + 0.050
    for j in range(8, 40):
        df2.iloc[j, [df2.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [up, up + 0.002, up - 0.002, up]
    t2 = _one(K.simulate(df2, K.StackConfig(exit_mode="tp5", c6=True, canon_cap=False)))
    assert t2.exit_reason == "EOD"


# ── C0 entry-time transform ─────────────────────────────────────────────
def _ts(hour: int) -> pd.Timestamp:
    return pd.Timestamp(f"2025-09-16 {hour:02d}:15", tz="UTC")


def test_c0_disabled_keeps_declared_sl_tp():
    sl, tp, br, fl = K.apply_c0(150.001, 0.100, _ts(12), pd.DataFrame(), K.StackConfig(c0=False))
    assert br == "preserve" and sl == pytest.approx(149.851) and tp == pytest.approx(150.501)


def test_c0_atr_mode_replaces_sl_with_1x_atr_and_broker_tp_085():
    cfg = K.StackConfig(c0=True, c0_sl_mode="atr", c0_lowliq=True, c0_rn=True)
    sl, tp, br, fl = K.apply_c0(150.123, 0.100, _ts(12), pd.DataFrame(), cfg)
    assert br == "atr" and sl == pytest.approx(150.023) and fl["lowliq"] == 0 and fl["rn"] == 0
    assert tp == pytest.approx(round(150.123 + 0.5 * 0.85, 3))
    sl2, tp2, _, fl2 = K.apply_c0(150.123, 0.100, _ts(12), pd.DataFrame(), replace(cfg, c0_broker_tp=False, c0_mtf=1.3))
    assert tp2 == pytest.approx(round(150.123 + 0.5 * 1.3, 3)) and fl2["mtf"] == 1.3


def test_c0_clamp_min_and_max():
    cfg = K.StackConfig(c0=True, c0_sl_mode="atr", c0_lowliq=False, c0_rn=False)
    sl, _, _, fl = K.apply_c0(150.123, 0.030, _ts(12), pd.DataFrame(), cfg)   # 3p → 5p
    assert fl["clamp"] == "min" and sl == pytest.approx(150.073)
    sl, _, _, fl = K.apply_c0(150.123, 0.300, _ts(12), pd.DataFrame(), cfg)   # 30p → 20p
    assert fl["clamp"] == "max" and sl == pytest.approx(149.923)
    sl, _, _, fl = K.apply_c0(150.123, 0.300, _ts(12), pd.DataFrame(), replace(cfg, c0_clamp=False))
    assert fl["clamp"] == "none" and sl == pytest.approx(149.823)


def test_c0_lowliq_hours_and_round_number_nudge():
    cfg = K.StackConfig(c0=True, c0_sl_mode="atr", c0_rn=False)
    sl20, _, _, fl20 = K.apply_c0(150.123, 0.100, _ts(20), pd.DataFrame(), cfg)
    sl12, _, _, fl12 = K.apply_c0(150.123, 0.100, _ts(12), pd.DataFrame(), cfg)
    assert fl20["lowliq"] == 1 and fl12["lowliq"] == 0
    assert sl20 == pytest.approx(sl12 - 0.020)
    # rn: SL がちょうど 150.000 に落ちる → 2.5p 外側へ
    cfg_rn = K.StackConfig(c0=True, c0_sl_mode="atr", c0_lowliq=False, c0_rn=True)
    sl, _, _, fl = K.apply_c0(150.100, 0.100, _ts(12), pd.DataFrame(), cfg_rn)
    assert fl["rn"] == 1 and sl == pytest.approx(149.975)
    sl, _, _, fl = K.apply_c0(150.300, 0.100, _ts(12), pd.DataFrame(), cfg_rn)  # 150.200 は帯外
    assert fl["rn"] == 0 and sl == pytest.approx(150.200)


def test_c0_sr_mode_prefers_support_cluster_when_rr_ok():
    # 149.700 付近に明瞭な安値クラスタ (6 タッチ) を持つ履歴
    idx = pd.date_range("2025-09-10", periods=300, freq="15min", tz="UTC")
    base = 150.2 + 0.05 * np.sin(np.arange(300) / 7.0)
    hist = pd.DataFrame({"High": base + 0.03, "Low": base - 0.03}, index=idx)
    for k in range(30, 300, 45):
        hist.iloc[k, hist.columns.get_loc("Low")] = 149.700
    cfg = K.StackConfig(c0=True, c0_sl_mode="sr", c0_lowliq=False, c0_rn=False, c0_clamp=False)
    sl, tp, br, _ = K.apply_c0(150.100, 0.100, _ts(12), hist, cfg)
    assert br == "sr"
    assert sl == pytest.approx(149.700 - 0.030, abs=0.02)
    # 履歴なし → ATR fallback (atr_nosr)
    _, _, br2, _ = K.apply_c0(150.100, 0.100, _ts(12), pd.DataFrame(), cfg)
    assert br2 == "atr_nosr"


# ── harness / stats ───────────────────────────────────────────────────────
def test_winner_within_8h_share_uses_wall_clock_not_bar_count():
    """PR #302 review P2 4113955120: 週末跨ぎの 20 bars は 8h 内ではない / ちょうど 8h (33 bars 目) は 8h 内。"""
    entry = 150.000 + K.MINTICK
    # (a) 金曜 19:00 signal → 週末を跨いで月曜に TP: bars は少ないが壁時計は 8h を大きく超える
    fri = pd.date_range("2025-09-19 17:00", "2025-09-19 20:45", freq="15min", tz="UTC")
    mon = pd.date_range("2025-09-21 21:00", periods=12, freq="15min", tz="UTC")
    idx = fri.append(mon)
    df = pd.DataFrame({"Open": 150.0, "High": 150.002, "Low": 149.998, "Close": 150.0, "atr": 0.1,
                       "entry_signal": False, "perfect_up": True, "perfect_dn": False, "in_window": True}, index=idx)
    df.iloc[8, df.columns.get_loc("entry_signal")] = True          # 19:00 signal
    df.iloc[len(fri) + 3, df.columns.get_loc("High")] = entry + 0.6  # 月曜 21:45 bar で TP
    cfg = K.StackConfig(exit_mode="tp5")
    tr = K.simulate(df, cfg)
    t = _one(tr)
    assert t.exit_reason == "TP_HIT" and t.bars_held < 32 and t.hold_sec > K.C1_MAX_HOLD_SEC
    assert K.summarize(tr, cfg)["winners_within_8h_share"] == 0.0
    # (b) 連続 bar で 8h ちょうど (32 bars = 28,800s) → 8h 内 / 1 bar 後 (33 bars = 8h15m) → 8h 外
    df2 = _bars(60)
    df2.iloc[5 + 32, df2.columns.get_loc("High")] = entry + 0.6
    tr2 = K.simulate(df2, cfg)
    t2 = _one(tr2)
    assert t2.bars_held == 32 and t2.hold_sec == pytest.approx(K.C1_MAX_HOLD_SEC)
    assert K.summarize(tr2, cfg)["winners_within_8h_share"] == 1.0
    df3 = _bars(60)
    df3.iloc[5 + 33, df3.columns.get_loc("High")] = entry + 0.6
    tr3 = K.simulate(df3, cfg)
    t3 = _one(tr3)
    assert t3.bars_held == 33 and t3.hold_sec == pytest.approx(K.C1_MAX_HOLD_SEC + 900)
    assert K.summarize(tr3, cfg)["winners_within_8h_share"] == 0.0


def test_tv_stats_apply_tv_commission_not_live_friction():
    """PR #302 review P2 4113955123: harness 比較は TV コスト (commission 0.002%×2) 基準。"""
    df = _bars(40)
    entry = 150.000 + K.MINTICK
    df.iloc[10, df.columns.get_loc("High")] = entry + 0.501
    tr = K.simulate(df, K.StackConfig(exit_mode="tp5"))
    t = _one(tr)
    expected_comm = (t.entry + t.exit) * K.TV_COMMISSION_RATE / K.PIP
    assert expected_comm == pytest.approx(0.6, abs=0.01)
    assert t.tv_net_pips == pytest.approx(t.gross_pips - expected_comm, abs=0.01)  # 2 桁丸め
    assert t.tv_net_pips != pytest.approx(t.net_pips)  # live 摩擦 2.14p とは別物
    s = K.tv_stats(tr)
    assert s["wr_tv"] == 1.0 and s["ev_tv_pips"] == pytest.approx(t.tv_net_pips)
    # 極小の gross winner は TV では loser: gross +0.3p → tv −0.3p
    df3 = _bars(40)
    df3.iloc[10:, df3.columns.get_loc("perfect_dn")] = True
    for c in ("Open", "High", "Low", "Close"):
        df3.iloc[10, df3.columns.get_loc(c)] = entry + 0.004
    tr3 = K.simulate(df3, K.StackConfig(exit_mode="flip"))
    t3 = _one(tr3)
    assert t3.gross_pips > 0 and t3.tv_net_pips < 0
    assert K.tv_stats(tr3)["wr_tv"] == 0.0


def test_harness_check_flags_mismatch_and_passes_canon():
    good = {"n": 46, "wr_tv": 0.2391, "pf_tv": 3.866, "hold_bars_winners_tv": {"mean": 458.0}}
    bad = {"n": 60, "wr_tv": 0.1833, "pf_tv": 2.27, "hold_bars_winners_tv": {"mean": 372.8}}
    assert K.harness_check(good)["all_ok"] is True
    chk = K.harness_check(bad)
    assert chk["all_ok"] is False and not chk["n"]["ok"] and not chk["pf"]["ok"]


def test_friction_is_subtracted_once_per_trade():
    df = _bars(40)
    entry = 150.000 + K.MINTICK
    df.iloc[10, df.columns.get_loc("High")] = entry + 0.501
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5")))
    assert t.net_pips == pytest.approx(t.gross_pips - K.FRICTION_PIPS, abs=1e-6)
    assert t.gross_pips == pytest.approx(50.0, abs=0.01)


def test_wilson_lower_matches_known_value():
    assert K.wilson_lower(11, 46) == pytest.approx(0.1394, abs=0.002)
