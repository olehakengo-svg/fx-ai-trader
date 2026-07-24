"""E20 rates ingest / S2 guards のオフライン test pin (network 不要)。"""
import json

import numpy as np
import pandas as pd
import pytest

from tools import e20_rates_ingest as I
from tools import e20_s2_guards as G


# ─── 和暦パース ──────────────────────────────────────────────────────────────
def test_wareki_showa():
    assert I.parse_wareki("S49.9.24") == pd.Timestamp("1974-09-24")


def test_wareki_heisei_and_reiwa():
    assert I.parse_wareki("H1.1.8") == pd.Timestamp("1989-01-08")
    assert I.parse_wareki("R8.6.30") == pd.Timestamp("2026-06-30")


def test_wareki_unknown_era_raises():
    with pytest.raises(ValueError):
        I.parse_wareki("X5.1.1")


# ─── ソースパーサ (固定 fixture) ─────────────────────────────────────────────
def test_parse_bis_policy_pivots_currencies():
    csv = (
        "FREQ,REF_AREA,TIME_PERIOD,OBS_VALUE\n"
        "D,US,2022-11-01,3.125\nD,JP,2022-11-01,-0.1\n"
        "D,US,2022-11-02,3.875\nD,JP,2022-11-02,-0.1\n"
        "D,ZZ,2022-11-01,9.9\n"  # 未知 REF_AREA は無視
    )
    panel = I.parse_bis_policy(csv)
    assert list(panel.columns) == ["JPY", "USD"]
    assert panel.loc["2022-11-01", "USD"] == 3.125
    assert "ZZ" not in panel.columns


def test_parse_mof_2y_skips_missing_tenor():
    raw = (
        "国債金利情報,,,,(単位 : %)\n"
        "基準日,1年,2年,3年\n"
        "S49.9.24,10.327,9.362,8.83\n"
        "H1.1.9,4.0,-,4.2\n"
    ).encode("shift-jis")
    s = I.parse_mof_2y(raw)
    assert s.loc["1974-09-24"] == 9.362
    assert pd.Timestamp("1989-01-09") not in s.index  # '-' は dropna


def test_parse_massive_us_2y_dedups_and_skips_null():
    text = json.dumps({"results": [
        {"date": "2013-01-02", "yield_2_year": 0.27},
        {"date": "2013-01-02", "yield_2_year": 0.28},
        {"date": "2013-01-03", "yield_2_year": None},
    ]})
    s = I.parse_massive_us_2y(text)
    assert len(s) == 1 and s.iloc[0] == 0.28  # keep=last、null は除外


def test_parse_boc_2y():
    text = json.dumps({"observations": [
        {"d": "2013-01-02", "BD.CDN.2YR.DQ.YLD": {"v": "1.17"}},
        {"d": "2013-01-03", "OTHER": {"v": "9"}},
    ]})
    s = I.parse_boc_2y(text)
    assert len(s) == 1 and s.loc["2013-01-02"] == 1.17


# ─── URL allowlist (file:// 混入の構造排除) ──────────────────────────────────
def test_http_get_rejects_non_allowlisted():
    for bad in ("file:///etc/passwd", "http://stats.bis.org/x",
                "https://evil.example.com/x"):
        with pytest.raises(ValueError):
            I._http_get(bad)


# ─── シグナル生成 ────────────────────────────────────────────────────────────
def _synth_panels():
    idx = pd.date_range("2013-01-01", "2023-06-30", freq="D")
    policy = pd.DataFrame(
        {c: np.linspace(0, 3, len(idx)) for c in
         ("USD", "EUR", "JPY", "GBP", "AUD", "NZD", "CAD", "CHF")}, index=idx)
    policy["JPY"] = -0.1  # 固定 → USD_JPY diff は正で単調増加
    y2 = pd.DataFrame(
        {c: np.linspace(0, 4, len(idx)) for c in ("USD", "EUR", "JPY", "GBP", "CAD")},
        index=idx)
    y2["JPY"] = 0.0
    return policy, y2


def test_build_signals_columns_and_cut():
    policy, y2 = _synth_panels()
    carry, mom = I.build_signals(policy, y2)
    assert set(I.CARRY_PAIRS) <= set(carry.columns)
    assert set(I.MOM_PAIRS) <= set(mom.columns)
    # SIGNAL_END で物理切断 (探索窓保護) — 2023 行が存在しない
    assert carry["date"].max() <= pd.Timestamp(I.SIGNAL_END)
    assert mom["date"].max() <= pd.Timestamp(I.SIGNAL_END)


def test_build_signals_diff_sign_and_mom_shift():
    policy, y2 = _synth_panels()
    carry, mom = I.build_signals(policy, y2)
    c = carry.set_index("date")
    # USD_JPY = policy[USD] − policy[JPY] > 0 (JPY 固定 −0.1)
    assert (c["USD_JPY"].dropna() > 0).all()
    # 同一系列同士の差はゼロ → mom も 0
    m = mom.set_index("date")
    assert np.allclose(m["EUR_USD"].dropna(), 0.0)  # EUR と USD は同一 linspace
    # USD_JPY 2y 差は単調増加 → Δ63bd は正
    tail = m["USD_JPY"].dropna()
    assert (tail > 0).all()


def test_mom_pairs_limited_to_current_2y_sources():
    for p in I.MOM_PAIRS:
        b, q = p.split("_")
        assert b in I.MOM_CURRENCIES and q in I.MOM_CURRENCIES
    assert "USD_CHF" not in I.MOM_PAIRS  # CHF cube 凍結 (D6)
    assert "AUD_USD" not in I.MOM_PAIRS  # AUD WAF 403 (D7)


# ─── guards 純関数 ───────────────────────────────────────────────────────────
def test_usd_neutrality_all_usd_pairs_is_1():
    idx = pd.date_range("2020-01-01", periods=50, freq="B")
    frames = {"USD_JPY": pd.DataFrame({"sig": 1.0, "fwd": 0.0}, index=idx),
              "EUR_USD": pd.DataFrame({"sig": -1.0, "fwd": 0.0}, index=idx)}
    g = G.usd_neutrality(frames)
    # long USD_JPY (+USD) と short EUR_USD (+USD) → net=2, gross=2 → 1.0
    assert g["mean_abs_net_usd_over_gross"] == 1.0
    assert g["n_cross_pairs"] == 0


def test_usd_neutrality_cross_pair_counts():
    idx = pd.date_range("2020-01-01", periods=10, freq="B")
    frames = {"EUR_JPY": pd.DataFrame({"sig": 1.0, "fwd": 0.0}, index=idx)}
    g = G.usd_neutrality(frames)
    assert g["n_cross_pairs"] == 1


def test_quintile_table_monotone_detection():
    idx = pd.date_range("2018-01-01", periods=600, freq="B")
    rng = np.random.default_rng(7)
    sig = pd.Series(np.linspace(-1, 1, len(idx)), index=idx)
    fwd = sig * 10 + rng.normal(0, 0.1, len(idx))  # ほぼ完全な正関係
    frames = {"USD_JPY": pd.DataFrame({"sig": sig, "fwd": fwd})}
    q = G.quintile_table(frames)
    assert q["monotone_increasing"] is True
    assert q["pooled_spearman_ic"] > 0.9
