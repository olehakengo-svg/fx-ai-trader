"""family_c_anchor_explore のオフライン test pin (network 不要、実データ非接触)。

pre-reg (family-c-rate-anchor-explore-prereg-2026-08-19.md) の凍結 DoF と
日付境界規約 (ベンダー日足 lesson) を構造固定する。
"""
import datetime as dt
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tools import family_c_anchor_explore as F


# ─── 凍結パラメータのドリフト防止 pin ────────────────────────────────────────
def test_frozen_params_pinned():
    assert F.W_ANCHOR == 252
    assert F.Z_GRID == (1.5, 2.0, 2.5)
    assert F.MIN_SEP == 5
    assert F.H_PRIMARY == 21
    assert F.DEGEN_STD_MIN == 0.10
    assert (F.RT_POINT, F.RT_STRESSED) == (2.14, 4.3)
    assert (F.M_POINT, F.M_ADVERSE) == (1.0, 1.65)
    assert F.EXPLORE == ("2014-01-01", "2021-12-31")
    assert F.OOS == ("2022-01-01", "2026-05-31")
    assert (F.SEED_PASS2, F.SEED_BLOCKFLIP, F.SEED_OOS) == (20260819, 20260820, 20260821)
    assert F.B_PERM == 10_000


# ─── D1 構築 (§2) ────────────────────────────────────────────────────────────
def _bars(day: str, n: int, base: float = 150.0):
    idx = pd.DatetimeIndex([f"{day} {h:02d}:{m:02d}" for h in range(24)
                            for m in (0, 15, 30, 45)][:n], tz="UTC")
    return pd.DataFrame({"Close": np.linspace(base, base + 0.1, n)}, index=idx)


def test_build_d1_weekday_and_minbars_filter():
    bars = pd.concat([
        _bars("2026-08-14", 96),          # 金曜 full
        _bars("2026-08-15", 96),          # 土曜 → 除外
        _bars("2026-08-17", 10),          # 月曜 thin → void (n_bars<24)
        _bars("2026-08-18", 96),          # 火曜 full
    ])
    d1 = F.build_d1(bars)
    days = list(d1.index)
    assert dt.date(2026, 8, 15) not in days
    assert dt.date(2026, 8, 17) not in days
    assert dt.date(2026, 8, 14) in days and dt.date(2026, 8, 18) in days


def test_build_d1_return_span_void_and_bigmove_assert():
    bars = pd.concat([_bars("2026-08-03", 96), _bars("2026-08-14", 96)])  # span 11 日
    d1 = F.build_d1(bars)
    assert np.isnan(d1["ret"].iloc[1])                 # span>7 暦日 → void
    bars2 = pd.concat([_bars("2026-08-13", 96, 150.0), _bars("2026-08-14", 96, 165.0)])
    with pytest.raises(AssertionError):                # |r|>5% → 停止
        F.build_d1(bars2)


# ─── 金利 join 境界 (§2 — ベンダー日足 lesson の必須 pin) ────────────────────
def test_yield_lag_one_day_boundary(tmp_path):
    jgb = tmp_path / "jgb.csv"
    ust = tmp_path / "ust.csv"
    jgb.write_text("date,2y,10y\n2026-08-13,1.00,2.00\n2026-08-14,1.10,2.10\n")
    ust.write_text("date,DGS2,DGS10\n2026-08-13,4.00,4.50\n2026-08-14,4.20,4.60\n")
    yields = F.load_yield_2y(str(jgb), str(ust))
    d1 = pd.DataFrame({"close": [150.0], "n_bars": [96], "ret": [np.nan]},
                      index=pd.Index([dt.date(2026, 8, 14)], name="date"))
    out = F.attach_anchor_inputs(d1, yields)
    # D1 day 08-14 は label ≤ 08-13 の値 (4.00−1.00=3.00) を使う — 当日値 3.10 ではない
    assert out["diff2y"].iloc[0] == pytest.approx(3.00)


def test_yield_staleness_void(tmp_path):
    jgb = tmp_path / "jgb.csv"
    ust = tmp_path / "ust.csv"
    jgb.write_text("date,2y\n2026-08-03,1.00\n2026-08-20,1.10\n")
    ust.write_text("date,DGS2\n2026-08-03,4.00\n2026-08-20,4.20\n")
    yields = F.load_yield_2y(str(jgb), str(ust))
    assert not np.isnan(yields.loc["2026-08-08", "diff"])   # stale 5 日 = OK
    assert np.isnan(yields.loc["2026-08-12", "diff"])       # stale 9 日 > 5 → void


# ─── anchor z (§3) ───────────────────────────────────────────────────────────
def _frame_for_z(n=300, degen=False, seed=7):
    rng = np.random.default_rng(seed)
    days = [d.date() for d in pd.bdate_range("2020-01-01", periods=n)]
    diff = np.full(n, 2.0) if degen else np.linspace(0.5, 2.5, n) + rng.normal(0, 0.05, n)
    close = 100.0 * np.exp(0.05 * diff + rng.normal(0, 0.002, n))
    return pd.DataFrame({"close": close, "n_bars": 96, "ret": np.nan, "diff2y": diff},
                        index=pd.Index(days, name="date"))


def test_compute_z_tracks_relationship_and_degenerate_void():
    df = F.compute_z(_frame_for_z())
    tail = df["z"].iloc[F.W_ANCHOR:]
    assert tail.notna().all()
    assert tail.abs().mean() < 3.0                          # 残差正規化が機能
    dfd = F.compute_z(_frame_for_z(degen=True))
    assert dfd["z"].iloc[F.W_ANCHOR:].isna().all()          # std(diff)<0.10 → 全 void
    assert (dfd["void_reason"].iloc[F.W_ANCHOR:] == "degenerate_anchor").all()


def test_detect_onsets_crossing_minsep_and_sides():
    days = [d.date() for d in pd.bdate_range("2020-01-01", periods=20)]
    z = pd.Series([0, -1, -2.1, -1, -2.2, -1, 0, 1, 2.2, 1, 0, -2.5, 0, 0, 0, 0, 0, 0, 0, 0],
                  index=pd.Index(days), dtype=float)
    lows, highs = F.detect_onsets(z, 2.0)
    # idx2 で下方クロス、idx4 は min-sep 5 未満で無視、idx11 は採用
    assert lows == [days[2], days[11]]
    assert highs == [days[8]]


def test_select_zth_mechanical_rule():
    assert F.select_zth({1.5: 200, 2.0: 80, 2.5: 20}) == 2.0
    assert F.select_zth({1.5: 90, 2.0: 40, 2.5: 10}) == 2.0     # |90-60|=30 vs |40-60|=20
    assert F.select_zth({1.5: 70, 2.0: 50, 2.5: 5}) == 2.0      # tie |10| → 大きい方
    assert F.select_zth({1.5: 20, 2.0: 10, 2.5: 3}) is None     # 全<30 → UNDERPOWERED
    assert F.select_zth({1.5: 500, 2.0: 300, 2.5: 200}) == 2.5  # 全>150 → 最タイト


# ─── swap (§7) ───────────────────────────────────────────────────────────────
def test_swap_pips_arithmetic():
    panel = pd.Series([2.5], index=pd.DatetimeIndex(["2019-01-01"]))
    # (2.5−1.0)/100 × 30/365 × 110/0.01 = 13.56p (LONG earn)
    sp = F.swap_pips(panel, dt.date(2019, 6, 1), 110.0, 30, F.M_POINT)
    assert sp == pytest.approx(1.5 / 100 * 30 / 365 * 110 / 0.01, rel=1e-9)
    sp_adv = F.swap_pips(panel, dt.date(2019, 6, 1), 110.0, 30, F.M_ADVERSE)
    assert sp_adv < sp                                       # adverse markup は必ず小さい


# ─── placebo pool (§6) ───────────────────────────────────────────────────────
def test_placebo_pool_excludes_onsets_and_tail():
    n = 120
    days = [d.date() for d in pd.bdate_range("2021-01-04", periods=n)]
    frame = pd.DataFrame({"close": 100.0, "n_bars": 96, "ret": np.nan,
                          "diff2y": 1.0, "z": 0.0},
                         index=pd.Index(days, name="date"))
    onsets = [days[50]]
    pool = F._placebo_pool(frame, onsets, F.H_PRIMARY)
    flat = [i for v in pool.values() for i in v]
    assert all(abs(i - 50) > F.MIN_SEP for i in flat)        # onset±5 除外
    assert max(flat) + F.H_PRIMARY < n                       # horizon 不成立 tail 除外


# ─── firewall 構造 pin (§4) ──────────────────────────────────────────────────
def test_pass1_events_csv_has_no_forward_columns():
    src = Path(F.__file__).read_text(encoding="utf-8")
    m = re.search(r"rows = \(\[\{(.*?)family-c-pass1-events", src, re.S)
    assert m, "pass-1 イベント CSV 構築部が見つからない"
    block = m.group(1)
    for banned in ("move", "fwd", "net", "swap"):
        assert banned not in block, f"pass-1 firewall 違反の疑い: {banned} が CSV 構築部に出現"


def test_frozen_paths_pin():
    assert "USD_JPY_15m_2014_2026.parquet" in F.PARQUET_DEFAULT   # bare 版の使用禁止 (§2)
    assert "data_freeze_manifest_2026-08-19" in F.MANIFEST
