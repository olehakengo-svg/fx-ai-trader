"""family_c_anchor_explore のオフライン test pin (network 不要、実データ非接触)。

pre-reg (family-c-rate-anchor-explore-prereg-2026-08-19.md) の凍結 DoF、
日付境界規約 (ベンダー日足 lesson)、敵対的検証 blocking 条件の修正を構造固定する。
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
    assert F.H_PRIMARY == 21 and F.EPISODE_GAP == 21
    assert F.DEGEN_STD_MIN == 0.10
    assert F.YIELD_STALE_MAX_CAL == 12          # 敵対的検証: JGB GW 2019 gap 11 日を被覆
    assert F.GATE_C_P_MAX == 0.02               # 敵対的検証: episode-block null の probe 較正
    assert (F.RT_POINT, F.RT_STRESSED) == (2.14, 4.3)
    assert (F.M_POINT, F.M_ADVERSE) == (1.0, 1.65)
    assert F.EXPLORE == ("2014-01-01", "2021-12-31")
    assert F.OOS == ("2022-01-01", "2026-05-31")
    assert (F.SEED_PASS2, F.SEED_PLACEBO, F.SEED_OOS) == (20260819, 20260820, 20260821)
    assert F.B_PERM == 10_000
    assert (F.ABLATION_JACCARD_MAX, F.ABLATION_NET_RATIO) == (0.5, 0.8)


# ─── D1 構築 (§2) ────────────────────────────────────────────────────────────
def _bars(day: str, n: int, base: float = 150.0):
    idx = pd.DatetimeIndex([f"{day} {h:02d}:{m:02d}" for h in range(24)
                            for m in (0, 15, 30, 45)][:n], tz="UTC")
    return pd.DataFrame({"Close": np.linspace(base, base + 0.1, n)}, index=idx)


def test_build_d1_filters_and_census():
    bars = pd.concat([
        _bars("2026-08-14", 96),          # 金曜 full
        _bars("2026-08-15", 96),          # 土曜 → 除外
        _bars("2026-08-17", 10),          # 月曜 thin → void
        _bars("2026-08-18", 96),          # 火曜 full
    ])
    d1 = F.build_d1(bars)
    days = list(d1.index)
    assert dt.date(2026, 8, 15) not in days and dt.date(2026, 8, 17) not in days
    assert d1.attrs["census"]["n_thin_void"] == 1   # 件数報告義務 (敵対的検証 C8)


def test_build_d1_return_span_void_and_bigmove_assert():
    bars = pd.concat([_bars("2026-08-03", 96), _bars("2026-08-14", 96)])
    d1 = F.build_d1(bars)
    assert np.isnan(d1["ret"].iloc[1])
    assert d1.attrs["census"]["n_ret_void"] == 1
    bars2 = pd.concat([_bars("2026-08-13", 96, 150.0), _bars("2026-08-14", 96, 165.0)])
    with pytest.raises(AssertionError):
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
    assert out["diff2y"].iloc[0] == pytest.approx(3.00)   # label ≤ d−1 のみ使用


def test_yield_staleness_12d_covers_golden_week(tmp_path):
    """敵対的検証 blocking: JGB GW 2019 (gap 11 暦日) を staleness 12 で被覆、13 日超は void。"""
    jgb = tmp_path / "jgb.csv"
    ust = tmp_path / "ust.csv"
    jgb.write_text("date,2y\n2026-08-01,1.00\n2026-08-12,1.10\n2026-09-01,1.20\n")
    ust.write_text("date,DGS2\n2026-08-01,4.00\n2026-08-12,4.20\n2026-09-01,4.30\n")
    yields = F.load_yield_2y(str(jgb), str(ust))
    assert not np.isnan(yields.loc["2026-08-11", "diff"])   # stale 10 日 = OK (GW 型)
    assert not np.isnan(yields.loc["2026-08-13", "diff"])   # stale 1 日
    assert np.isnan(yields.loc["2026-08-26", "diff"])       # stale 14 日 > 12 → void


# ─── anchor z (§3) ───────────────────────────────────────────────────────────
def _frame_for_z(n=300, degen=False, seed=7):
    rng = np.random.default_rng(seed)
    days = [d.date() for d in pd.bdate_range("2020-01-01", periods=n)]
    diff = np.full(n, 2.0) if degen else np.linspace(0.5, 2.5, n) + rng.normal(0, 0.05, n)
    close = 100.0 * np.exp(0.05 * diff + rng.normal(0, 0.002, n))
    return pd.DataFrame({"close": close, "n_bars": 96, "ret": np.nan, "diff2y": diff},
                        index=pd.Index(days, name="date"))


def test_compute_z_tracks_relationship_and_void_labels():
    df = F.compute_z(_frame_for_z())
    tail = df["z"].iloc[F.W_ANCHOR:]
    assert tail.notna().all()
    assert (df["void_reason"].iloc[:F.W_ANCHOR - 1] == "warmup").all()
    assert (df["anchor_share"].iloc[F.W_ANCHOR:] > 0).all()   # 寄与 census (L2-7)
    dfd = F.compute_z(_frame_for_z(degen=True))
    assert dfd["z"].iloc[F.W_ANCHOR:].isna().all()
    assert (dfd["void_reason"].iloc[F.W_ANCHOR:] == "degenerate_anchor").all()


def test_compute_z_perfect_fit_inf_guard():
    """敵対的検証 C10: 完全 fit (std_resid≈0) は z=inf でなく void。"""
    n = 300
    days = [d.date() for d in pd.bdate_range("2020-01-01", periods=n)]
    diff = np.linspace(0.5, 2.5, n)
    close = 100.0 * np.exp(0.05 * diff)          # ノイズゼロ = 完全線形
    df = F.compute_z(pd.DataFrame({"close": close, "n_bars": 96, "ret": np.nan,
                                   "diff2y": diff}, index=pd.Index(days, name="date")))
    assert not np.isinf(df["z"].dropna()).any()


def test_compute_z_price_only_ablation_mode():
    df = F.compute_z(_frame_for_z(), price_only=True)
    assert df["z"].iloc[F.W_ANCHOR:].notna().all()
    assert (df["anchor_share"] == 0.0).all()


def test_detect_onsets_framepos_minsep_across_voids():
    """敵対的検証 C3: min-sep は frame position 基準 (z-void 圧縮ではない)。"""
    n = 20
    days = [d.date() for d in pd.bdate_range("2020-01-01", periods=n)]
    z = [0, -2.1] + [np.nan] * 5 + [0, -2.2] + [0, 1.0, 2.2, 0, -2.5] + [0] * 6
    frame = pd.DataFrame({"z": pd.array(z, dtype=float)}, index=pd.Index(days))
    lows, highs = F.detect_onsets(frame, 2.0)
    # idx1 onset。idx8 は直前 valid (idx7=0)→クロスだが frame 距離 7 ≥ 5 → 採用。
    # idx13 は idx8 から frame 距離 5 → 採用境界。上方クロス完了は idx11 (2.2)。
    assert lows == [days[1], days[8], days[13]]
    assert highs == [days[11]]


def test_detect_onsets_minsep_suppression():
    days = [d.date() for d in pd.bdate_range("2020-01-01", periods=10)]
    z = [0, -2.1, -1.0, -2.2, -1.0, -2.3, 0, 0, 0, 0]   # idx3/idx5 は近すぎ
    frame = pd.DataFrame({"z": pd.array(z, dtype=float)}, index=pd.Index(days))
    lows, _ = F.detect_onsets(frame, 2.0)
    assert lows == [days[1]]


def test_select_zth_mechanical_rule():
    assert F.select_zth({1.5: 200, 2.0: 80, 2.5: 20}) == 2.0
    assert F.select_zth({1.5: 90, 2.0: 40, 2.5: 10}) == 2.0
    assert F.select_zth({1.5: 70, 2.0: 50, 2.5: 5}) == 2.0
    assert F.select_zth({1.5: 20, 2.0: 10, 2.5: 3}) is None      # 全<30
    assert F.select_zth({1.5: 500, 2.0: 300, 2.5: 200}) == 2.5   # 全>150
    # 敵対的検証 C3/C5: 混在で range 内ゼロ → UNDERPOWERED (多イベント側の採用禁止)
    assert F.select_zth({1.5: 200, 2.0: 20, 2.5: 5}) is None


# ─── gate C null (§6 — 敵対的検証 C1 の probe 較正形) ────────────────────────
def test_episode_blocks_merge_rule():
    nets = pd.DataFrame({"pos": [10, 20, 60, 65, 120], "dnet": [1.0, 2.0, 3.0, 4.0, 5.0]})
    blocks = F._episode_blocks(nets)
    # gap<21 で連結: {10,20}, {60,65}, {120} → 和 = [3, 7, 5]
    assert blocks == [3.0, 7.0, 5.0]


def test_gate_c_demeaned_blockflip():
    rng = np.random.default_rng(0)
    nets = pd.DataFrame({
        "pos": np.arange(0, 40 * 30, 30),          # 全て独立 block (gap 30 ≥ 21)
        "year": [2015 + (i % 7) for i in range(40)],
        "net": rng.normal(100.0, 10.0, 40),        # 年平均 0 に対し +100p の明確な効果
    })
    year_means = {y: 0.0 for y in range(2015, 2022)}
    gc = F.gate_c_test(nets, year_means, seed=1)
    assert gc["pass"] and gc["p_one"] <= 0.001
    # 効果ゼロ (対称) なら不通過
    nets2 = nets.copy()
    nets2["net"] = rng.normal(0.0, 100.0, 40)
    gc2 = F.gate_c_test(nets2, year_means, seed=1)
    assert gc2["p_one"] > 0.02 or abs(gc2["stat_demeaned_mean"]) < 60


# ─── swap (§7) ───────────────────────────────────────────────────────────────
def test_swap_pips_arithmetic():
    panel = pd.Series([2.5], index=pd.DatetimeIndex(["2019-01-01"]))
    sp = F.swap_pips(panel, dt.date(2019, 6, 1), 110.0, 30, F.M_POINT)
    assert sp == pytest.approx(1.5 / 100 * 30 / 365 * 110 / 0.01, rel=1e-9)
    assert F.swap_pips(panel, dt.date(2019, 6, 1), 110.0, 30, F.M_ADVERSE) < sp


# ─── event nets / placebo pool ───────────────────────────────────────────────
def _flat_frame(n=120, z_void_at=()):
    days = [d.date() for d in pd.bdate_range("2021-01-04", periods=n)]
    z = np.zeros(n)
    frame = pd.DataFrame({"close": 100.0, "n_bars": 96, "ret": np.nan,
                          "diff2y": 1.0, "z": z},
                         index=pd.Index(days, name="date"))
    for i in z_void_at:
        frame.iloc[i, frame.columns.get_loc("z")] = np.nan
    return frame


def test_event_nets_entry_lag_and_drop_count():
    frame = _flat_frame(30)
    panel = pd.Series([1.0], index=pd.DatetimeIndex(["2020-01-01"]))
    nets, dropped = F._event_nets(frame, panel, [frame.index[2], frame.index[25]],
                                  F.RT_POINT, F.M_POINT)
    assert len(nets) == 1 and dropped == 1          # 25+21 は末尾超過 → drop 計上 (C11)
    nets_lag, _ = F._event_nets(frame, panel, [frame.index[2]], F.RT_POINT, F.M_POINT,
                                entry_lag=1)
    assert len(nets_lag) == 1                        # knife-edge (iv) entry_lag 経路


def test_placebo_pool_excludes_onsets_tail_and_zvoid():
    frame = _flat_frame(120, z_void_at=(30, 31, 32))
    pool = F._placebo_pool(frame, [frame.index[50]], F.H_PRIMARY)
    flat = [i for v in pool.values() for i in v]
    assert all(abs(i - 50) > F.MIN_SEP for i in flat)
    assert max(flat) + F.H_PRIMARY < 120
    assert not any(i in (30, 31, 32) for i in flat)  # z-void 日は候補外 (敵対的検証 C4)


# ─── firewall / lock 構造 pin (§4) ───────────────────────────────────────────
def test_pass1_events_csv_has_no_forward_columns():
    src = Path(F.__file__).read_text(encoding="utf-8")
    m = re.search(r"rows = \(\[\{(.*?)P1_EVENTS", src, re.S)
    assert m, "pass-1 イベント CSV 構築部が見つからない"
    for banned in ("move", "fwd", "net", "swap"):
        assert banned not in m.group(1), f"pass-1 firewall 違反の疑い: {banned}"


def test_oos_machine_locks():
    with pytest.raises(RuntimeError, match="unlock-oos"):
        F.run_oos("/nonexistent.parquet", unlock=False)   # (i) flag なしで即拒否
    src = Path(F.__file__).read_text(encoding="utf-8")
    for token in ("_assert_committed(P2_JSON)", "os.path.exists(OOS_JSON)",
                  "_assert_committed(SWAP_EXT_MANIFEST)"):
        assert token in src, f"OOS 機械ロック欠落: {token}"


def test_frozen_paths_pin():
    assert "USD_JPY_15m_2014_2026.parquet" in F.PARQUET_DEFAULT
    assert "data_freeze_manifest_2026-08-19" in F.MANIFEST
