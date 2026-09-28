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
    assert t.hold_sec >= K.C5_HALF_HOLD_SEC  # 境界 bar (== 14,400s) から eligible (review P2 4114208143)
    # 含み益側は C5 で切られない
    df2 = _bars(80)
    above = entry + 0.010
    for j in range(22, 80):
        df2.iloc[j, [df2.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [above, above + 0.002, above - 0.002, above]
    t2 = _one(K.simulate(df2, K.StackConfig(exit_mode="tp5", c5=True, canon_cap=False)))
    assert t2.exit_reason == "EOD"


# ── C2 weekend ───────────────────────────────────────────────────────────
def _summer_weekend_frame(signal_at: int = 2, sunday_open: float = 150.0) -> pd.DataFrame:
    """夏時間: 金曜最終 bar 20:45 (閉場 21:00Z)、日曜初 bar 21:00。2025-09-19 は金曜。"""
    fri = pd.date_range("2025-09-19 12:00", "2025-09-19 20:45", freq="15min", tz="UTC")
    sun = pd.date_range("2025-09-21 21:00", periods=40, freq="15min", tz="UTC")
    idx = fri.append(sun)
    df = pd.DataFrame({"Open": 150.0, "High": 150.002, "Low": 149.998, "Close": 150.0, "atr": 0.1,
                       "entry_signal": False, "perfect_up": True, "perfect_dn": False, "in_window": True}, index=idx)
    df.iloc[signal_at, df.columns.get_loc("entry_signal")] = True
    j = len(fri)
    df.iloc[j, [df.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [sunday_open, sunday_open + 0.002, sunday_open - 0.002, sunday_open]
    return df


def test_c2_summer_close_is_deferred_to_sunday_open_with_gap():
    """PR #302 review P2 4114026089: 夏時間は 21:00Z 閉場なので 21:45Z のクローズは執行できず、日曜 open で fill する
    (KB 実例 carry_dip #709598)。金曜 close で決済したことにしてはいけない。"""
    df = _summer_weekend_frame(sunday_open=149.900)   # 週末ギャップ −10p (SL 15p には届かない)
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c2=True)))
    assert t.exit_reason == "WEEKEND_CLOSE_SUNDAY_FILL"
    assert pd.Timestamp(t.exit_time) == pd.Timestamp("2025-09-21 21:00", tz="UTC")
    assert t.exit == pytest.approx(149.900 - K.MINTICK)      # 日曜 open − slippage、ギャップを食う
    assert t.raw_pips == pytest.approx(-10.0, abs=0.01)
    t0 = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c2=False, canon_cap=False)))
    assert t0.exit_reason == "EOD"  # C2 無しなら保持継続 (SL には届かない)
    # ギャップが stop も割る (−30p) 場合は live 同様 SL/TP 判定が週末条件より先 → C2 ではなく SL_HIT に帰属 (review P2 4114113659)
    df2 = _summer_weekend_frame(sunday_open=149.700)
    t2 = _one(K.simulate(df2, K.StackConfig(exit_mode="tp5", c2=True)))
    assert t2.exit_reason == "SL_HIT" and t2.exit == pytest.approx(149.700 - K.MINTICK)
    assert pd.Timestamp(t2.exit_time) == pd.Timestamp("2025-09-21 21:00", tz="UTC")


def test_c2_winter_close_executes_at_friday_2145_bar_open():
    """冬時間 (22:00Z 閉場): 金曜 21:45 bar が存在し、live の 21:45Z クローズはその tick で執行される。"""
    fri = pd.date_range("2025-12-05 12:00", "2025-12-05 21:45", freq="15min", tz="UTC")   # 12-05 は金曜
    sun = pd.date_range("2025-12-07 22:00", periods=20, freq="15min", tz="UTC")
    idx = fri.append(sun)
    df = pd.DataFrame({"Open": 150.0, "High": 150.002, "Low": 149.998, "Close": 150.0, "atr": 0.1,
                       "entry_signal": False, "perfect_up": True, "perfect_dn": False, "in_window": True}, index=idx)
    df.iloc[2, df.columns.get_loc("entry_signal")] = True
    k = list(idx).index(pd.Timestamp("2025-12-05 21:45", tz="UTC"))
    df.iloc[k, df.columns.get_loc("Open")] = 150.120
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c2=True)))
    assert t.exit_reason == "WEEKEND_CLOSE"
    assert pd.Timestamp(t.exit_time) == pd.Timestamp("2025-12-05 21:45", tz="UTC")
    assert t.exit == pytest.approx(150.120 - K.MINTICK)


def test_c2_entry_on_final_summer_friday_bar_is_closed_at_sunday_open():
    """PR #302 review P2 4113998538 / 4114026089: 夏時間の金曜 20:45 bar signal (entry 21:00) は live では 21:45Z の
    クローズ指示が閉場後 → 日曜 open で fill。日曜 bar 内の TP は取れない (open で先に閉じる)。"""
    df = _summer_weekend_frame(signal_at=35, sunday_open=150.050)   # 20:45 bar が index 35 (12:00 起点)
    assert df.index[35] == pd.Timestamp("2025-09-19 20:45", tz="UTC")
    entry = 150.000 + K.MINTICK
    df.iloc[38, df.columns.get_loc("High")] = entry + 0.6           # 日曜 3 本目に TP 水準
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c2=True)))
    assert t.exit_reason == "WEEKEND_CLOSE_SUNDAY_FILL" and t.bars_held == 1
    assert pd.Timestamp(t.exit_time) == pd.Timestamp("2025-09-21 21:00", tz="UTC")
    assert t.exit == pytest.approx(150.050 - K.MINTICK)
    t0 = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c2=False)))
    assert t0.exit_reason == "TP_HIT"  # C2 無しなら週末を跨いで TP


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
    df.iloc[11, df.columns.get_loc("Open")] = entry + 0.180   # open は trail SL の上 (下ならギャップ fill 経路)
    df.iloc[11, df.columns.get_loc("High")] = entry + 0.185
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


def test_friction_is_subtracted_from_unslipped_levels_once():
    """PR #302 review P2 4114026093: RT 摩擦 2.14p は slippage 込みなので、slipped gross からではなく
    slippage 無しの水準差 (raw) から引く。TV 側 gross は slippage 込みのまま。"""
    df = _bars(40)
    entry = 150.000 + K.MINTICK
    df.iloc[10, df.columns.get_loc("High")] = entry + 0.501
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5")))
    assert t.gross_pips == pytest.approx(50.0, abs=0.01)     # slipped: entry +1 tick、TP は指値で slippage 無し
    assert t.raw_pips == pytest.approx(50.1, abs=0.01)       # 水準差: tp − signal close
    assert t.net_pips == pytest.approx(t.raw_pips - K.FRICTION_PIPS, abs=1e-6)
    # 成行 exit (flip) は exit 側にも slippage → raw と gross の差は 2 tick
    df2 = _bars(40)
    df2.iloc[10:, df2.columns.get_loc("perfect_dn")] = True
    t2 = _one(K.simulate(df2, K.StackConfig(exit_mode="flip")))
    assert t2.raw_pips - t2.gross_pips == pytest.approx(0.2, abs=1e-6)


def test_tv_pf_is_cash_based_with_sequential_equity_sizing():
    """PR #302 review P2 4114026095: TV の PF は 10% equity 逐次サイジングの cash PnL — entry 価格が違う trade は
    pips 合計 PF と一致しない。"""
    def mk(entry, exit_px, when):
        return K.SimTrade(signal_time=when, entry_time=when, exit_time=when, entry=entry, exit=exit_px, atr=0.1,
                          decl_sl=0, decl_tp=0, sl0=0, tp0=0, sl_branch="atr", c0_flags={}, bars_held=5, hold_sec=4500,
                          exit_reason="TP_HIT", gross_pips=(exit_px - entry) / K.PIP, raw_pips=(exit_px - entry) / K.PIP,
                          net_pips=0.0, tv_net_pips=(exit_px - entry) / K.PIP - K.tv_commission_pips(entry, exit_px),
                          mfe_pips=0.0, mae_pips=0.0)
    trades = [mk(100.001, 100.501, "2025-09-16T09:00:00+00:00"),   # +50p @100 → qty 100 → +50 JPY
              mk(200.001, 199.751, "2025-09-16T12:00:00+00:00")]   # −25p @200 → qty 5.025 → −1.3 JPY
    s = K.tv_stats(trades)
    assert s["pf_tv_pips"] == pytest.approx(50.0 / 25.0, rel=0.05)
    # cash: A qty≈100 → +49.6 JPY (commission 0.4) / B qty≈50 (equity 10% / 200) → −12.9 JPY ⇒ PF ≈ 3.84 ≠ 2.0
    assert s["pf_tv"] == pytest.approx(49.6 / 12.9, rel=0.02)
    assert abs(s["pf_tv"] - s["pf_tv_pips"]) > 1.0
    assert s["wr_tv"] == 0.5 and s["ending_equity_tv"] > K.TV_INITIAL_EQUITY


def test_wilson_lower_matches_known_value():
    assert K.wilson_lower(11, 46) == pytest.approx(0.1394, abs=0.002)


# ── 4 巡目 (PR #302 review P1 4114077247 / P1 4114077249 / P2 4114077250) ───
def test_gap_through_stop_fills_at_open_not_at_stop_level():
    """open が既に SL を割っていれば fill は open − tick (sl − tick ではない)。TP 側は open で fill (有利側)。"""
    entry = 150.000 + K.MINTICK
    df = _bars(40, atr=0.100)
    gap_open = entry - 0.700          # SL (−15p) を 55p 飛び越える open
    df.iloc[12, [df.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [gap_open, gap_open + 0.002, gap_open - 0.002, gap_open]
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5")))
    assert t.exit_reason == "SL_HIT"
    assert t.exit == pytest.approx(gap_open - K.MINTICK) and t.raw_pips == pytest.approx(-69.9, abs=0.01)  # raw = open − signal close
    assert pd.Timestamp(t.exit_time) == df.index[12]                      # open 時刻で fill
    df2 = _bars(40, atr=0.100)
    gap_up = entry + 0.700            # TP (+50p) を飛び越える open → open で fill (+70p)
    df2.iloc[12, [df2.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [gap_up, gap_up + 0.002, gap_up - 0.002, gap_up]
    t2 = _one(K.simulate(df2, K.StackConfig(exit_mode="tp5")))
    assert t2.exit_reason == "TP_HIT" and t2.raw_pips == pytest.approx(70.1, abs=0.01)


def test_intrabar_exit_bar_can_reenter_at_its_close_but_close_time_exit_cannot():
    """bar 内 exit (SL/TP) した bar の close に signal があれば再エントリする。close 時点 exit (flip) の bar は次 bar から。"""
    entry = 150.000 + K.MINTICK
    df = _bars(60)
    df.iloc[10, df.columns.get_loc("High")] = entry + 0.501     # bar 10 で TP
    df.iloc[10, df.columns.get_loc("entry_signal")] = True      # 同 bar close に再 signal
    tr = K.simulate(df, K.StackConfig(exit_mode="tp5", canon_cap=False))
    assert len(tr) == 2 and tr[0].exit_reason == "TP_HIT" and tr[1].signal_time == df.index[10].isoformat()
    df2 = _bars(60)
    df2.iloc[10, df2.columns.get_loc("perfect_dn")] = True       # bar 10 close で flip exit
    df2.iloc[10, df2.columns.get_loc("entry_signal")] = True
    tr2 = K.simulate(df2, K.StackConfig(exit_mode="flip", canon_cap=False))
    assert len(tr2) == 1 and tr2[0].exit_reason == "PO_DN_FLIP"


def test_c5_entry_crossing_precedes_a_later_stop_when_sl_is_below_entry():
    """4h 超で open ≥ entry の bar が entry と SL を両方割る → 連続パスでは entry 割れ (C5) が先。SL が entry 以上 (BE 後) なら SL 経路。"""
    entry = 150.000 + K.MINTICK
    df = _bars(80, atr=0.100)
    j = 5 + 20   # hold 5h の bar
    for b in range(6, j):   # 保持中は entry の上で推移 (flat 150.0 だと Low 149.998 < entry で 4h 後に C5 が即発火)
        df.iloc[b, [df.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [entry + 0.010, entry + 0.012, entry + 0.008, entry + 0.010]
    df.iloc[j, [df.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [entry + 0.010, entry + 0.012, entry - 0.300, entry - 0.250]
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c5=True)))
    assert t.exit_reason == "TIME_DECAY_EXIT" and t.exit == pytest.approx(entry - K.MINTICK)
    t0 = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c5=False)))
    assert t0.exit_reason == "SL_HIT"
    # BE 済み (SL = entry + spread > entry) なら SL/BE 経路が先
    df3 = _bars(80, atr=0.100)
    for b in range(6, j):
        df3.iloc[b, [df3.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [entry + 0.010, entry + 0.012, entry + 0.008, entry + 0.010]
    df3.iloc[8, df3.columns.get_loc("High")] = entry + 0.090     # MFE 9p ≥ 0.8×ATR → BE
    df3.iloc[j, [df3.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [entry + 0.010, entry + 0.012, entry - 0.300, entry - 0.250]
    t3 = _one(K.simulate(df3, K.StackConfig(exit_mode="tp5", c5=True, c3c4=True)))
    assert t3.exit_reason == "BE"


def test_harness_unverified_counts_identification_candidate_passes():
    """PR #302 review P2 4114113668: 既定 2 変種が ❌ でも識別候補が ±10% を満たせば「検証済み」扱い。"""
    fail = {"a": {"all_ok": False}, "b": {"all_ok": False}}
    assert K.harness_unverified(fail, [{"harness_ok": False}, {"harness_ok": False}]) is True
    assert K.harness_unverified(fail, [{"harness_ok": False}, {"harness_ok": True}]) is False
    assert K.harness_unverified({"a": {"all_ok": True}}, []) is False


# ── 6 巡目 (PR #302 review P2 4114143809 / P2 4114143815) ───
def test_c5_vs_tp_same_bar_follows_ordering_assumption():
    """4h 超で open ≥ entry、bar 内で TP と entry 割れの両方 → adverse_first は C5 (entry 割れ先)、favorable_first は TP 先。"""
    entry = 150.000 + K.MINTICK
    def frame():
        df = _bars(80, atr=0.100)
        j = 5 + 20
        for b in range(6, j):
            df.iloc[b, [df.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [entry + 0.010, entry + 0.012, entry + 0.008, entry + 0.010]
        df.iloc[j, [df.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [entry + 0.010, entry + 0.600, entry - 0.050, entry + 0.100]
        return df
    adv = _one(K.simulate(frame(), K.StackConfig(exit_mode="tp5", c5=True, order="adverse_first")))
    fav = _one(K.simulate(frame(), K.StackConfig(exit_mode="tp5", c5=True, order="favorable_first")))
    assert adv.exit_reason == "TIME_DECAY_EXIT"
    assert fav.exit_reason == "TP_HIT"


def test_harness_check_emits_plain_python_bools_even_from_numpy_inputs():
    s = {"n": np.int64(60), "wr_tv": np.float64(0.1833), "pf_tv": np.float64(1.99), "hold_bars_winners_tv": {"mean": np.float64(372.8)}}
    chk = K.harness_check(s)
    for key in ("n", "wr", "pf", "avg_win_bars"):
        assert type(chk[key]["ok"]) is bool
    assert type(chk["all_ok"]) is bool
    import json
    assert json.loads(json.dumps(chk, default=str))["pf"]["ok"] is False   # 文字列 "False" ではなく JSON false


# ── 7 巡目 (PR #302 review P1 4114171432 / P2 excursions) ───
def test_adverse_first_recheck_raised_stop_against_close_in_same_bar():
    """adverse_first: 同 bar で low は旧 SL に届かず、high で BE (0.8×ATR) 発動、close が新 stop (entry+spread) を割る
    → open→low→high→close の連続パスで新 stop に触れるので同 bar で BE 決済 (次 bar 持ち越しは誤り)。"""
    entry = 150.000 + K.MINTICK
    df = _bars(40, atr=0.100)
    j = 12
    df.iloc[j, [df.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [entry + 0.010, entry + 0.090, entry - 0.050, entry - 0.040]
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c3c4=True, order="adverse_first")))
    assert t.exit_reason == "BE" and t.bars_held == j - 5
    assert t.exit == pytest.approx(round(entry + K.C3_BE_SPREAD, 3) - K.MINTICK, abs=1e-6)
    # close が新 stop の上なら持ち越し (次 bar で判定)
    df2 = _bars(40, atr=0.100)
    df2.iloc[j, [df2.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [entry + 0.010, entry + 0.090, entry - 0.050, entry + 0.030]
    t2 = _one(K.simulate(df2, K.StackConfig(exit_mode="tp5", c3c4=True, order="adverse_first", canon_cap=False)))
    assert t2.bars_held > j - 5


def test_gap_exit_excursions_exclude_post_exit_bar_range():
    """ギャップで open 決済した bar の high/low は MFE/MAE に含めない (exit は open 時点)。"""
    entry = 150.000 + K.MINTICK
    df = _bars(40, atr=0.100)
    gap_open = entry - 0.700
    df.iloc[12, [df.columns.get_loc(c) for c in ("Open", "High", "Low", "Close")]] = [gap_open, entry + 0.900, gap_open - 0.500, gap_open]
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5")))
    assert t.exit_reason == "SL_HIT"
    assert t.mfe_pips == pytest.approx(0.1, abs=0.05)        # 保持中の High 150.002 − entry 150.001 のみ (bar high +90p は含めない)
    assert t.mae_pips == pytest.approx(70.0, abs=0.05)       # open までの逆行 (bar low −120p は含めない)


# ── PR #302 繰延 P2 (registry review-backlog-pr302-p2-deferrals、2026-09-28) ──────────
def _set_bar(df, j, o, h, l, c):
    df.iloc[j, [df.columns.get_loc(x) for x in ("Open", "High", "Low", "Close")]] = [o, h, l, c]


def test_c5_boundary_bar_exactly_4h_is_eligible_and_3h45_is_not():
    """entry bar 6 (09:30) → bar 22 open = 13:30 = hold_open 14,400s ちょうど。live は 4h 到達直後の tick で eligible なので
    この bar から C5 (review P2 4114208143: `>` だと 15 分足整列で毎回 1 bar 遅れていた)。bar 21 (3h45m) は eligible ではない。"""
    entry = 150.000 + K.MINTICK
    below = entry - 0.010
    df = _bars(80)
    _set_bar(df, 22, below, below + 0.002, below - 0.002, below)      # 境界 bar だけ含み損
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c5=True, canon_cap=False)))
    assert t.exit_reason == "TIME_DECAY_EXIT"
    assert t.hold_sec == pytest.approx(K.C5_HALF_HOLD_SEC)             # exit は境界 bar の open 時点
    assert t.bars_held == 22 - 5
    df2 = _bars(80)
    above = entry + 0.010
    for j in range(22, 80):                                            # 4h 以降は含み益側 (既定の 150.000 は entry より 1 tick 下で C5 が即発火する)
        _set_bar(df2, j, above, above + 0.002, above - 0.002, above)
    _set_bar(df2, 21, below, below + 0.002, below - 0.002, below)     # 3h45m の bar だけ含み損 → C5 不発
    t2 = _one(K.simulate(df2, K.StackConfig(exit_mode="tp5", c5=True, canon_cap=False)))
    assert t2.exit_reason == "EOD"


def test_c5_intrabar_predicate_eligible_on_boundary_bar():
    """bar 内交差の述語も同じ境界 (hold_open == 14,400s で open ≥ entry ∧ low < entry → entry 割れで決済)。"""
    entry = 150.000 + K.MINTICK
    df = _bars(80)
    _set_bar(df, 22, entry + 0.010, entry + 0.040, entry - 0.010, entry - 0.005)   # SL (−15p) には届かない
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c5=True, canon_cap=False, order="adverse_first")))
    assert t.exit_reason == "TIME_DECAY_EXIT" and t.exit == pytest.approx(entry - K.MINTICK)
    assert t.hold_sec == pytest.approx(K.C5_HALF_HOLD_SEC + 900)     # bar 内 exit は bar close 時刻
    # 同 bar の high (+4p) は adverse_first (open→low の脚で entry に触れる) では exit 後 → MFE は open (+1.0p) まで
    assert t.mfe_pips == pytest.approx(1.0, abs=0.05)
    assert t.mae_pips == pytest.approx(0.3, abs=0.05)                # 保持中の Low 149.998 のみ (entry 割れ点 = entry は 0p)
    t2 = _one(K.simulate(df.copy(), K.StackConfig(exit_mode="tp5", c5=True, canon_cap=False, order="favorable_first")))
    assert t2.exit_reason == "TIME_DECAY_EXIT"
    assert t2.mfe_pips == pytest.approx(4.0, abs=0.05)               # favorable_first は open→high→low なので high は exit 前


def test_excursions_truncate_at_intrabar_sl_adverse_first():
    """adverse_first の SL は open→low の脚 → 同 bar の high (+90p) は exit 後で MFE に入れない。MAE は stop まで。"""
    entry = 150.000 + K.MINTICK
    df = _bars(40, atr=0.100)                                        # SL = entry − 0.150
    _set_bar(df, 12, entry + 0.010, entry + 0.900, entry - 0.300, entry - 0.100)
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", order="adverse_first")))
    assert t.exit_reason == "SL_HIT"
    assert t.mfe_pips == pytest.approx(1.0, abs=0.05)                # open (+1.0p) まで — bar high +90p は含めない
    assert t.mae_pips == pytest.approx(15.0, abs=0.05)               # stop (−15p) まで — bar low −30p は含めない


def test_excursions_truncate_at_intrabar_tp_favorable_first():
    """favorable_first の TP は open→high の脚 → 同 bar の low (−30p) は exit 後で MAE に入れない。MFE は TP まで。"""
    entry = 150.000 + K.MINTICK
    df = _bars(40, atr=0.100)                                        # TP = entry + 0.500
    _set_bar(df, 12, entry + 0.010, entry + 0.900, entry - 0.300, entry + 0.200)
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", order="favorable_first")))
    assert t.exit_reason == "TP_HIT"
    assert t.mfe_pips == pytest.approx(50.0, abs=0.05)               # TP (+50p) まで — bar high +90p は含めない
    assert t.mae_pips == pytest.approx(0.3, abs=0.05)                # 保持中の Low 149.998 のみ — bar low −30p は含めない


def test_excursions_tp_adverse_first_includes_prior_low_and_sl_favorable_first_includes_prior_high():
    """adverse_first の TP は low→high の脚 (low は exit 前 → MAE に入る、high の残りは exit 後)。
    favorable_first の SL は high→low の脚 (high は exit 前 → MFE に入る、low の残りは exit 後)。"""
    entry = 150.000 + K.MINTICK
    df = _bars(40, atr=0.100)
    _set_bar(df, 12, entry + 0.010, entry + 0.900, entry - 0.050, entry + 0.200)     # low は SL (−15p) の手前
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", order="adverse_first")))
    assert t.exit_reason == "TP_HIT"
    assert t.mae_pips == pytest.approx(5.0, abs=0.05)                # bar low (−5p) は TP 前
    assert t.mfe_pips == pytest.approx(50.0, abs=0.05)               # TP まで (bar high +90p は exit 後)
    df2 = _bars(40, atr=0.100)
    _set_bar(df2, 12, entry + 0.010, entry + 0.200, entry - 0.300, entry - 0.100)    # high は TP (+50p) の手前
    t2 = _one(K.simulate(df2, K.StackConfig(exit_mode="tp5", order="favorable_first")))
    assert t2.exit_reason == "SL_HIT"
    assert t2.mfe_pips == pytest.approx(20.0, abs=0.05)              # bar high (+20p) は SL 前
    assert t2.mae_pips == pytest.approx(15.0, abs=0.05)              # stop まで (bar low −30p は exit 後)


def test_excursions_same_bar_be_after_high_keeps_full_bar_range():
    """adverse_first で high が BE を発動し close が新 stop を割る bar (review P1 4114171432) は、low → high → close の全脚が
    exit 前 → MFE/MAE は bar 全体 (打ち切りはこの脚では起きない)。"""
    entry = 150.000 + K.MINTICK
    df = _bars(40, atr=0.100)
    _set_bar(df, 12, entry + 0.010, entry + 0.090, entry - 0.050, entry - 0.040)
    t = _one(K.simulate(df, K.StackConfig(exit_mode="tp5", c3c4=True, order="adverse_first")))
    assert t.exit_reason == "BE"
    assert t.mfe_pips == pytest.approx(9.0, abs=0.05)
    assert t.mae_pips == pytest.approx(5.0, abs=0.05)
