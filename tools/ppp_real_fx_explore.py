#!/usr/bin/env python3
"""ppp_real_fx_gap_reversion — 凍結 explore 測定ハーネス (観測前凍結 2026-07-29).

Frozen spec : knowledge-base/wiki/analyses/ppp-real-fx-explore-prereg-2026-07-29.md
Data spec   : data/external/ppp/README.md
Output      : knowledge-base/raw/bt-results/ppp-real-fx-explore-2026-07-29.json

役割は測定のみ。判定 (5 合格条件の適用) は行わない — 条件 i-v の入力数値を
明示的に出力し、verdict は親セッションが凍結ルールを機械適用する。

── Spec resolution note (orientation) ─────────────────────────────────────────
凍結 doc は q = log(S) + log(CPI_foreign/CPI_US) と書きつつ、同時に
  (a) S は「1 USD あたり外貨」(FC per USD) に正規化
  (b) 「q 上昇 = USD 実質高」
  (c) 予測: 高 z (USD 実質割高) → USD 減価 = 対 USD 外貨リターン正
  (d) IC = Spearman(−z_usd_adjusted, fwd return)
を宣言している。S = FC/USD のとき、literal な +log(CPI_f/CPI_US) は (b)/(c) と
PPP アンカー (S* = CPI_f/CPI_US ⇒ 乖離 = log S − log(CPI_f/CPI_US)) の両方に矛盾する。
内部整合的な読み — 凍結式を S = USD/FC (「USD 建て」) 向きで verbatim に取り、
(d) の −z で符号反転したものと数値的に同一 — を primary として実装する:
    q_usd = log(S_fc_per_usd) − log(CPI_f/CPI_US)   (= USD 実質価値の log)
    z_usd = q_usd の rolling 1260bd z-score (完全窓のみ, ddof=1)
    IC    = Spearman(z_usd, fwd FC return vs USD)    (回帰方向 ⇒ IC > 0)
literal-mix 変種 (S = FC/USD のまま +log(CPI_f/CPI_US)) は
diagnostics_not_for_selection にのみ記録する (選択には使わない)。
──────────────────────────────────────────────────────────────────────────────

CPI vintage: 利用可能日 = 参照期間末 (月次=月末 / AU・NZ 四半期=四半期末) + 45 暦日。
FRED の期間初日スタンプは期間末に変換してから 45d を加える (look-ahead 罠回避)。
シグナル日には利用可能な最新値を前方埋め (月内/四半期内 step、補間なし)。

Bootstrap null: 6 ヶ月時間ブロック (半期 × 16) × 全ペア同時リサンプル。
シグナル側ブロック列とリターン側ブロック列を独立に復元抽出し、ブロック内
スロット ((月位置, ペア) 順) で対にする — dollar factor と系列構造を保存したまま
z→r リンクだけを破壊した帰無分布 (10,000×, seed 20260729)。
si==ri の一致スロット (期待 1/16) は帰無を観測側に寄せる = 保守的。
"""

import argparse
import hashlib
import json
import os

import numpy as np
import pandas as pd
from scipy import stats

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(_REPO, "data", "external", "ppp")
RATES_CSV = os.path.join(_REPO, "knowledge-base", "raw", "bt-results", "e20",
                         "e20_carry_level.csv")
OUT_JSON = os.path.join(_REPO, "knowledge-base", "raw", "bt-results",
                        "ppp-real-fx-explore-2026-07-29.json")

SEED = 20260729
N_BOOT = 10_000
Z_WINDOW = 1260                      # rolling 営業日、完全窓のみ
HORIZONS = (21, 42, 63)
PRIMARY_H = 42
EXPLORE_START = "2014-01-31"         # シグナル日 explore 窓 (凍結)
EXPLORE_END = "2021-12-31"
GRID_START = "2008-01-02"            # H.10 有効開始
GRID_END = "2022-04-30"              # 2021-12-31 + 63bd を確実にカバー (OOS シグナルは生成しない)
VINTAGE_LAG_DAYS = 45

# pair → (H.10 file, FRED series, H.10 が USD per FC か, 外貨 CPI file, CPI 頻度,
#          pip size, per-pair RT friction pips, FC が base 側か)
PAIRS = {
    "EUR_USD": ("fred_h10_EURUSD.csv", "DEXUSEU", True,
                "fred_cpi_EA_CP0000EZ19M086NEST.csv", "M", 0.0001, 2.00, True),
    "USD_JPY": ("fred_h10_USDJPY.csv", "DEXJPUS", False,
                "bis_cpi_JP_WS_LONG_CPI_M_JP_628.csv", "BIS_M", 0.01, 2.14, False),
    "GBP_USD": ("fred_h10_GBPUSD.csv", "DEXUSUK", True,
                "fred_cpi_GB_GBRCPIALLMINMEI.csv", "M", 0.0001, 4.53, True),
    "AUD_USD": ("fred_h10_AUDUSD.csv", "DEXUSAL", True,
                "fred_cpi_AU_AUSCPIALLQINMEI.csv", "Q", 0.0001, 2.50, True),
    "NZD_USD": ("fred_h10_NZDUSD.csv", "DEXUSNZ", True,
                "fred_cpi_NZ_NZLCPIALLQINMEI.csv", "Q", 0.0001, 3.00, True),
    "USD_CAD": ("fred_h10_USDCAD.csv", "DEXCAUS", False,
                "fred_cpi_CA_CANCPIALLMINMEI.csv", "M", 0.0001, 2.80, False),
    "USD_CHF": ("fred_h10_USDCHF.csv", "DEXSZUS", False,
                "fred_cpi_CH_CHECPIALLMINMEI.csv", "M", 0.0001, 3.00, False),
}
US_CPI_FILE = "fred_cpi_US_CPIAUCNS.csv"

# e20_carry_level.csv は carry[BASE_QUOTE] = policy[BASE] − policy[QUOTE] (%pt)。
# rd_fc = policy[FC] − policy[US] へ向きを揃える符号。
RD_FC_SIGN = {"EUR_USD": +1, "GBP_USD": +1, "AUD_USD": +1, "NZD_USD": +1,
              "USD_JPY": -1, "USD_CAD": -1, "USD_CHF": -1}


# ── loaders ──────────────────────────────────────────────────────────────────
def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_fx(path: str) -> pd.Series:
    """H.10 csv → 日次 Series (欠測 '.' は NaN のまま返す — ffill は grid 上で)。"""
    df = pd.read_csv(path, na_values=".")
    df.columns = ["date", "rate"]
    s = pd.Series(df["rate"].astype(float).values,
                  index=pd.to_datetime(df["date"]))
    return s.sort_index()


def load_cpi(path: str, freq: str) -> pd.DataFrame:
    """CPI csv → DataFrame(period_end, avail, value)。

    freq: 'M' = FRED 月次 (観測日 = 月初) / 'Q' = FRED 四半期 (観測日 = 四半期初月 1 日)
          / 'BIS_M' = BIS SDMX 月次 (TIME_PERIOD = 'YYYY-MM')。
    利用可能日 avail = 参照期間末 + VINTAGE_LAG_DAYS 暦日 (凍結 §条件 5)。
    """
    if freq == "BIS_M":
        df = pd.read_csv(path)
        df = df[["TIME_PERIOD", "OBS_VALUE"]].dropna()
        d = pd.to_datetime(df["TIME_PERIOD"], format="%Y-%m")
        val = df["OBS_VALUE"].astype(float).values
        period_end = d + pd.offsets.MonthEnd(0)
    else:
        df = pd.read_csv(path)
        df.columns = ["date", "value"]
        df = df.dropna(subset=["value"])
        d = pd.to_datetime(df["date"])
        val = df["value"].astype(float).values
        if freq == "M":
            period_end = d + pd.offsets.MonthEnd(0)
        elif freq == "Q":
            # FRED 四半期スタンプは四半期初月 1 日 → 期間末 (3 月末等) に変換
            period_end = d + pd.offsets.QuarterEnd(0)
        else:
            raise ValueError(f"unknown freq {freq!r}")
    out = pd.DataFrame({
        "period_end": pd.DatetimeIndex(period_end),
        "avail": pd.DatetimeIndex(period_end) + pd.Timedelta(days=VINTAGE_LAG_DAYS),
        "value": val,
    }).sort_values("avail").reset_index(drop=True)
    assert out["avail"].is_monotonic_increasing and out["period_end"].is_monotonic_increasing
    return out


def cpi_on_grid(cpi: pd.DataFrame, grid: pd.DatetimeIndex):
    """各 grid 日に「利用可能日 ≤ 当日」の最新 CPI 値を割当 (前方埋め step)。

    戻り値: (values Series, avail_used Series, period_end_used Series)。
    """
    idx = np.searchsorted(cpi["avail"].values, grid.values, side="right") - 1
    assert (idx >= 0).all(), "grid 先頭で利用可能な CPI が無い"
    return (pd.Series(cpi["value"].values[idx], index=grid),
            pd.Series(cpi["avail"].values[idx], index=grid),
            pd.Series(cpi["period_end"].values[idx], index=grid))


# ── statistics ───────────────────────────────────────────────────────────────
def spearman(x: np.ndarray, y: np.ndarray) -> float:
    return float(stats.spearmanr(x, y).statistic)


def block_bootstrap_p(z: np.ndarray, r: np.ndarray, block_ids: np.ndarray,
                      n_boot: int = N_BOOT, seed: int = SEED):
    """時間ブロック × 全ペア同時リサンプルの帰無分布による両側 p。

    前提: (z, r, block_ids) は (block, slot) 順に整列済みで、全ブロックが
    同一スロット構成 (月位置 × ペア)。シグナル側とリターン側のブロック列を
    独立に復元抽出し、スロット位置で対にして pooled Spearman を計算する。
    """
    ublocks, counts = np.unique(block_ids, return_counts=True)
    assert len(set(counts.tolist())) == 1, f"ブロックサイズ不均一: {counts}"
    nb, k = len(ublocks), int(counts[0])
    Z = z.reshape(nb, k)
    R = r.reshape(nb, k)
    ic_obs = spearman(z, r)
    rng = np.random.default_rng(seed)
    null = np.empty(n_boot)
    for i in range(n_boot):
        si = rng.integers(0, nb, nb)
        ri = rng.integers(0, nb, nb)
        null[i] = spearman(Z[si].ravel(), R[ri].ravel())
    p = (1 + int(np.count_nonzero(np.abs(null) >= abs(ic_obs)))) / (n_boot + 1)
    return ic_obs, float(p), null


# ── panel construction ───────────────────────────────────────────────────────
def build_panel():
    """全ペアの (シグナル日 × ペア) long panel と品質メタを構築。"""
    grid = pd.bdate_range(GRID_START, GRID_END)
    sig_dates = pd.date_range(EXPLORE_START, EXPLORE_END, freq="BME")

    # assert: explore 窓外のシグナル日ゼロ
    assert sig_dates.min() >= pd.Timestamp(EXPLORE_START)
    assert sig_dates.max() <= pd.Timestamp(EXPLORE_END)
    assert len(sig_dates) == 96, f"月末シグナル日 96 期待: {len(sig_dates)}"
    pos = grid.get_indexer(sig_dates)
    assert (pos >= 0).all(), "シグナル日が営業日 grid に無い"

    cpi_us = load_cpi(os.path.join(DATA_DIR, US_CPI_FILE), "M")
    us_val, us_avail, us_pend = cpi_on_grid(cpi_us, grid)

    rates = pd.read_csv(RATES_CSV, parse_dates=["date"]).set_index("date")
    rates = rates.reindex(rates.index.union(grid)).ffill().reindex(grid)

    rows = []
    quality = {}
    for pair, (fx_file, series_id, usd_per_fc, cpi_file, cpi_freq,
               pip, rt, fc_is_base) in PAIRS.items():
        fx_raw = load_fx(os.path.join(DATA_DIR, fx_file))
        fx = fx_raw.reindex(grid)
        n_missing_sig = int(fx.loc[sig_dates].isna().sum())
        fx = fx.ffill()
        assert fx.notna().all(), f"{pair}: grid 先頭に FX 欠損"

        # S = FC per 1 USD へ正規化 (DEXUSxx = USD per FC → 逆数化)
        s_fc_per_usd = (1.0 / fx) if usd_per_fc else fx
        # OANDA 建値 (README: 7 ペアとも H.10 の向き = OANDA ペア名) — headroom pips 用
        price = fx

        cpi_f = load_cpi(os.path.join(DATA_DIR, cpi_file),
                         "BIS_M" if cpi_freq == "BIS_M" else cpi_freq)
        f_val, f_avail, f_pend = cpi_on_grid(cpi_f, grid)

        # ── q / z (primary: USD 実質価値の向き。resolution note 参照) ──
        log_ratio_f_us = np.log(f_val.values) - np.log(us_val.values)
        q_usd = pd.Series(np.log(s_fc_per_usd.values) - log_ratio_f_us, index=grid)
        # literal-mix 変種 (diagnostics のみ)
        q_lit = pd.Series(np.log(s_fc_per_usd.values) + log_ratio_f_us, index=grid)

        def _z(q):
            m = q.rolling(Z_WINDOW, min_periods=Z_WINDOW).mean()
            sd = q.rolling(Z_WINDOW, min_periods=Z_WINDOW).std()  # ddof=1
            return (q - m) / sd

        z_usd, z_lit = _z(q_usd), _z(q_lit)

        # fwd returns: r_fc = FC の対 USD リターン (USD 減価 = 正) = −Δlog S
        fwd = {h: pd.Series(np.log(s_fc_per_usd.values)
                            - np.log(s_fc_per_usd.shift(-h).values), index=grid)
               for h in HORIZONS}
        d_price_63 = price.shift(-63) - price

        rd_fc = RD_FC_SIGN[pair] * rates[pair]  # %pt, FC − US

        # ── assertions (凍結 §実装検証) ──
        # lookahead: シグナル日の CPI 利用可能日 ≤ シグナル日 (両脚)
        assert (f_avail.loc[sig_dates] <= sig_dates).all(), f"{pair}: 外貨 CPI look-ahead"
        assert (us_avail.loc[sig_dates] <= sig_dates).all(), f"{pair}: US CPI look-ahead"
        # z 完全窓: シグナル日 z が非 NaN かつ grid 位置 ≥ Z_WINDOW−1
        assert z_usd.loc[sig_dates].notna().all(), f"{pair}: z 不完全窓"
        assert (pos >= Z_WINDOW - 1).all()
        for h in HORIZONS:
            assert fwd[h].loc[sig_dates].notna().all(), f"{pair}: fwd{h} NaN"
        assert rd_fc.loc[sig_dates].notna().all(), f"{pair}: 金利差 NaN"

        stale_f = (sig_dates - pd.DatetimeIndex(f_pend.loc[sig_dates].values)).days
        quality[pair] = {
            "fx_missing_on_signal_dates_ffilled": n_missing_sig,
            "foreign_cpi_staleness_days_at_signal": {
                "max": int(stale_f.max()), "median": float(np.median(stale_f))},
        }

        for t in sig_dates:
            rows.append({
                "date": t, "pair": pair,
                "z": float(z_usd.loc[t]), "z_lit": float(z_lit.loc[t]),
                "r21": float(fwd[21].loc[t]), "r42": float(fwd[42].loc[t]),
                "r63": float(fwd[63].loc[t]),
                "rd_fc_pct": float(rd_fc.loc[t]),
                "price": float(price.loc[t]),
                "d_price_63": float(d_price_63.loc[t]),
                "pip": pip, "rt": rt, "fc_is_base": fc_is_base,
            })

    panel = pd.DataFrame(rows)
    panel["year"] = panel["date"].dt.year
    panel["block"] = (panel["date"].dt.year.astype(str) + "H"
                      + np.where(panel["date"].dt.month <= 6, "1", "2"))
    panel = panel.sort_values(["block", "date", "pair"]).reset_index(drop=True)
    assert len(panel) == 672, f"672 obs 期待: {len(panel)}"
    assert panel[["z", "z_lit", "r21", "r42", "r63", "rd_fc_pct"]].notna().all().all()
    bc = panel.groupby("block").size()
    assert len(bc) == 16 and (bc == 42).all(), f"6m ブロック構成異常: {bc.to_dict()}"
    return panel, quality


# ── condition inputs ─────────────────────────────────────────────────────────
def quintile_stats(panel: pd.DataFrame):
    """pooled z quintile (Q1 = z 最小 = USD 実質割安 … Q5 = 最大 = USD 実質割高)。"""
    labels = pd.qcut(panel["z"], 5, labels=False)
    panel = panel.assign(quintile=labels + 1)
    means = panel.groupby("quintile")["r42"].mean()
    counts = panel.groupby("quintile").size()
    m = means.values
    violations = int(sum(1 for i in range(4) if m[i + 1] < m[i]))  # 予測 = z 増加方向に単調増加
    return panel, {
        "orientation": "Q1=lowest z_usd (USD real cheap) → Q5=highest (USD real rich); "
                       "prediction = mean fwd FC return increases with quintile",
        "means_r42": [round(float(v), 6) for v in m],
        "counts": [int(c) for c in counts.values],
        "adjacent_violations_vs_increasing": violations,
        "spread_q5_minus_q1": round(float(m[4] - m[0]), 6),
        "spread_q1_minus_q5": round(float(m[0] - m[4]), 6),
    }


def carry_neutralized_ic(panel: pd.DataFrame, ic_primary: float):
    """z を政策金利差 (FC−US, %pt) に pooled OLS 回帰した残差 z⊥ の IC (h=42)。"""
    x = np.ascontiguousarray(panel["rd_fc_pct"].values, dtype=float)
    y = np.ascontiguousarray(panel["z"].values, dtype=float)
    b = float(np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1))
    a = float(y.mean() - b * x.mean())
    resid = y - (a + b * x)
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    ic_resid = spearman(resid, panel["r42"].values)
    beta = (a, b)
    return {
        "rates_source": "knowledge-base/raw/bt-results/e20/e20_carry_level.csv "
                        "(e20_rates_ingest 残置パネル: BIS CBPOL 政策金利差, %pt, 日次 ffill)",
        "regression": "pooled OLS (クロスセクション+時系列一括, 672 obs): z ~ a + b*rd_fc",
        "alpha": round(float(beta[0]), 6), "beta": round(float(beta[1]), 6),
        "r2": round(1 - ss_res / ss_tot, 6),
        "ic_resid_h42": round(ic_resid, 6),
        "ratio_to_primary_ic": round(ic_resid / ic_primary, 6) if ic_primary else None,
        "sign_unchanged": bool(np.sign(ic_resid) == np.sign(ic_primary)),
    }


def headroom_stats(panel: pd.DataFrame, haircut: bool):
    """上位/下位 quintile の |fwd 63bd 純移動 (スワップ純額込み)| vs 10×RT。

    トレード: Q5 = FC ロング (USD ショート) / Q1 = FC ショート。
    move_pips  = 建値 63bd 変化をトレード方向で符号化 (FC=quote ペアはペア売り)。
    swap_pips  = rd_fc/100 × 63/252 × price / pip (FC ロングの受払、Q1 は符号反転)。
    haircut=True: swap 受取側 (earn>0) を 25% 減額 (凍結 §診断)。
    """
    sub = panel[panel["quintile"].isin([1, 5])].copy()
    long_fc = sub["quintile"] == 5
    pair_side = np.where(sub["fc_is_base"], 1.0, -1.0)      # FC ロング時のペア方向
    trade_sign = np.where(long_fc, pair_side, -pair_side)
    move_pips = trade_sign * sub["d_price_63"].values / sub["pip"].values
    swap_long_fc = (sub["rd_fc_pct"].values / 100.0) * (63.0 / 252.0) \
        * sub["price"].values / sub["pip"].values
    swap_pips = np.where(long_fc, swap_long_fc, -swap_long_fc)
    if haircut:
        swap_pips = np.where(swap_pips > 0, swap_pips * 0.75, swap_pips)
    net = move_pips + swap_pips
    sub = sub.assign(abs_net_pips=np.abs(net),
                     ratio=np.abs(net) / sub["rt"].values)

    def med(df, col):
        return round(float(df[col].median()), 4)

    per_pair = {}
    for pair, g in sub.groupby("pair"):
        g5, g1 = g[g["quintile"] == 5], g[g["quintile"] == 1]
        per_pair[pair] = {
            "n_q5": int(len(g5)), "n_q1": int(len(g1)),
            "median_abs_net_pips_q5": med(g5, "abs_net_pips") if len(g5) else None,
            "median_abs_net_pips_q1": med(g1, "abs_net_pips") if len(g1) else None,
            "median_abs_net_pips_combined": med(g, "abs_net_pips"),
            "rt_pips": float(g["rt"].iloc[0]),
            "threshold_10x_rt_pips": round(10 * float(g["rt"].iloc[0]), 3),
        }
    return {
        "swap_haircut_25pct_on_earn": haircut,
        "pooled_median_abs_net_pips_over_rt": {
            "q5_long_fc": med(sub[sub["quintile"] == 5], "ratio"),
            "q1_short_fc": med(sub[sub["quintile"] == 1], "ratio"),
            "combined": med(sub, "ratio"),
        },
        "threshold_ratio": 10.0,
        "per_pair": per_pair,
    }


def regime_decomposition(panel: pd.DataFrame, ic_primary: float):
    annual, loyo, share = {}, {}, {}
    for y in sorted(panel["year"].unique()):
        g = panel[panel["year"] == y]
        annual[str(y)] = round(spearman(g["z"].values, g["r42"].values), 6)
        rest = panel[panel["year"] != y]
        ic_l = spearman(rest["z"].values, rest["r42"].values)
        loyo[str(y)] = round(ic_l, 6)
        share[str(y)] = round((ic_primary - ic_l) / ic_primary, 6) if ic_primary else None
    return {
        "annual_ic_h42": annual,
        "annual_n": int(len(panel) / len(annual)),
        "leave_one_year_out_ic_h42": loyo,
        "loyo_share_of_pooled_ic": share,
        "loyo_share_definition": "(IC_pooled − IC_without_year) / IC_pooled",
    }


# ── main ─────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    args = ap.parse_args(argv)

    panel, quality = build_panel()
    panel, quint = quintile_stats(panel)

    # pooled IC + block bootstrap p (primary 42bd, supporting 21/63bd)
    ic_by_h = {}
    for h in HORIZONS:
        ic, p, _ = block_bootstrap_p(panel["z"].values, panel[f"r{h}"].values,
                                     panel["block"].values, n_boot=args.n_boot)
        ic_by_h[str(h)] = {"ic": round(ic, 6), "p_two_sided": round(p, 6), "n": len(panel)}
    ic_primary = ic_by_h[str(PRIMARY_H)]["ic"]

    carry = carry_neutralized_ic(panel, ic_primary)
    headroom = headroom_stats(panel, haircut=False)
    headroom_hc = headroom_stats(panel, haircut=True)
    regime = regime_decomposition(panel, ic_primary)

    per_pair_ic = {
        pair: {"ic_h42": round(spearman(g["z"].values, g["r42"].values), 6),
               "ic_h63": round(spearman(g["z"].values, g["r63"].values), 6),
               "n": int(len(g))}
        for pair, g in panel.groupby("pair")}

    # 非重複 confirmatory: 四半期末シグナルのみ × h=63bd
    conf = panel[panel["date"].dt.month.isin([3, 6, 9, 12])].copy()
    conf = conf.sort_values(["block", "date", "pair"]).reset_index(drop=True)
    ic_c, p_c, _ = block_bootstrap_p(conf["z"].values, conf["r63"].values,
                                     conf["block"].values, n_boot=args.n_boot)
    confirmatory = {"n": int(len(conf)), "ic_h63": round(ic_c, 6),
                    "p_two_sided": round(p_c, 6),
                    "note": "四半期末 × 63bd = 実質非重複窓 (診断、選択に使わない)"}

    # |z|>2 記述パネル (secondary descriptive のみ)
    hi, lo = panel[panel["z"] > 2], panel[panel["z"] < -2]
    z2 = {"n_z_gt_2": int(len(hi)), "n_z_lt_-2": int(len(lo)),
          "mean_r42_z_gt_2": round(float(hi["r42"].mean()), 6) if len(hi) else None,
          "mean_r42_z_lt_-2": round(float(lo["r42"].mean()), 6) if len(lo) else None,
          "mean_r63_z_gt_2": round(float(hi["r63"].mean()), 6) if len(hi) else None,
          "mean_r63_z_lt_-2": round(float(lo["r63"].mean()), 6) if len(lo) else None}

    # literal-mix 変種 (diagnostics_not_for_selection)
    ic_lit, p_lit, _ = block_bootstrap_p(panel["z_lit"].values, panel["r42"].values,
                                         panel["block"].values, n_boot=args.n_boot)

    data_files = {}
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith(".csv"):
            p_ = os.path.join(DATA_DIR, f)
            data_files[f"data/external/ppp/{f}"] = {"sha256": _sha256(p_)}
    data_files["knowledge-base/raw/bt-results/e20/e20_carry_level.csv"] = {
        "sha256": _sha256(RATES_CSV)}

    result = {
        "meta": {
            "family": "ppp_real_fx_gap_reversion",
            "stage": "explore (frozen pre-reg 2026-07-29) — measurement only, no verdict",
            "frozen_spec": "knowledge-base/wiki/analyses/ppp-real-fx-explore-prereg-2026-07-29.md",
            "generated_by": "tools/ppp_real_fx_explore.py",
            "seed": SEED, "n_boot": args.n_boot, "z_window_bd": Z_WINDOW,
            "explore_signal_window": [EXPLORE_START, EXPLORE_END],
            "oos_touched": False,
            "signal_orientation_resolution": (
                "凍結式 q=log(S)+log(CPI_f/CPI_US) は S=FC/USD 宣言と『q 上昇=USD 実質高』"
                "『高 z→USD 減価』『IC=Spearman(−z,fwd)』に対し価格比の向きが不整合 (PPP アンカー "
                "S*=CPI_f/CPI_US)。内部整合読み q_usd=log(S_fc/USD)−log(CPI_f/CPI_US) "
                "(= 凍結式を S=USD/FC 向きで verbatim に取り (d) の −z を適用したものと同値) を "
                "primary に採用。IC=Spearman(z_usd, fwd FC return vs USD)、回帰方向 ⇒ IC>0。"
                "literal-mix は diagnostics_not_for_selection のみ。"),
            "fwd_return_definition": "r_fc(t,h) = log(S_t/S_{t+h}), S=FC per USD ffilled "
                                     "(= 外貨の対 USD log リターン、USD 減価 = 正)",
            "cpi_vintage_rule": "利用可能日 = 参照期間末 (月次=月末 / AU・NZ 四半期=四半期末) "
                                "+45 暦日、以後前方埋め step (FRED 期間初日スタンプは期間末に変換)",
            "bootstrap_null": "半期 (6m) ブロック 16 × 全ペア同時。シグナル側/リターン側ブロック列を"
                              "独立復元抽出しスロット対合 → z-r リンクのみ破壊 (si==ri 一致は保守側)",
            "assertions_passed": ["lookahead (CPI avail ≤ signal date, 両脚, 全 672 obs)",
                                   "z 完全窓 1260bd (全シグナル日 non-NaN, grid 位置 ≥ 1259)",
                                   "explore 窓外シグナル日ゼロ (2014-01-31〜2021-12-31)",
                                   "n=672 (96 月末 × 7 ペア), 6m ブロック 16 × 42"],
            "data_files": data_files,
            "data_quality": quality,
        },
        "pass_condition_inputs": {
            "i_primary_ic": {
                "horizon_bd": PRIMARY_H,
                "ic": ic_by_h[str(PRIMARY_H)]["ic"],
                "p_two_sided_block_bootstrap": ic_by_h[str(PRIMARY_H)]["p_two_sided"],
                "n_obs": 672,
                "reversion_direction_sign": "+1 (z_usd 向き: 高 z=USD 実質割高 → FC return 正)",
                "sign_matches_reversion": bool(ic_primary > 0),
            },
            "ii_quintile_monotonicity": quint,
            "iii_carry_neutralization": carry,
            "iv_headroom": headroom,
            "v_regime_concentration": regime,
        },
        "supporting_diagnostics": {
            "ic_by_horizon": ic_by_h,
            "per_pair_ic": per_pair_ic,
            "confirmatory_nonoverlapping": confirmatory,
            "z_abs_gt_2_descriptive": z2,
            "headroom_swap_sensitivity_haircut25": headroom_hc,
        },
        "diagnostics_not_for_selection": {
            "literal_mix_variant": {
                "definition": "q_lit = log(S_fc/USD) + log(CPI_f/CPI_US) — 凍結式の字面を "
                              "S=FC/USD のまま適用した内部不整合構成 (spec 監査用)",
                "ic_h42": round(ic_lit, 6), "p_two_sided": round(p_lit, 6),
            },
        },
        "per_obs": [
            {"date": t.strftime("%Y-%m-%d"), "pair": pr, "z": round(z, 4),
             "quintile": int(q), "r21": round(r1, 6), "r42": round(r2, 6),
             "r63": round(r3, 6), "rd_fc_pct": round(rd, 4)}
            for t, pr, z, q, r1, r2, r3, rd in zip(
                panel["date"], panel["pair"], panel["z"], panel["quintile"],
                panel["r21"], panel["r42"], panel["r63"], panel["rd_fc_pct"])
        ],
    }

    # 出力に explore 窓外の日付が含まれないことを最終 assert
    dts = [row["date"] for row in result["per_obs"]]
    assert min(dts) >= EXPLORE_START and max(dts) <= EXPLORE_END

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)

    # ── stdout summary ──
    print("ppp_real_fx_gap_reversion explore — measurement summary (NO verdict)")
    print(f"n=672 (96 month-ends 2014-01-31..2021-12-31 x 7 pairs), seed={SEED}, "
          f"boot={args.n_boot}x half-year-block x all-pair")
    print(f"[i]   primary IC (42bd) = {ic_primary:+.4f}   p(two-sided) = "
          f"{ic_by_h['42']['p_two_sided']:.4f}   (reversion sign = +)")
    print(f"      supporting IC: 21bd {ic_by_h['21']['ic']:+.4f} (p={ic_by_h['21']['p_two_sided']:.4f})"
          f" / 63bd {ic_by_h['63']['ic']:+.4f} (p={ic_by_h['63']['p_two_sided']:.4f})")
    print(f"[ii]  quintile mean r42 (Q1..Q5 by z_usd): "
          + " ".join(f"{v:+.5f}" for v in quint["means_r42"])
          + f"   adj-violations={quint['adjacent_violations_vs_increasing']}"
          + f"   Q5-Q1={quint['spread_q5_minus_q1']:+.5f}")
    print(f"[iii] carry-neutralized IC = {carry['ic_resid_h42']:+.4f}   "
          f"ratio={carry['ratio_to_primary_ic']}   sign_unchanged={carry['sign_unchanged']}")
    hr = headroom["pooled_median_abs_net_pips_over_rt"]
    print(f"[iv]  headroom median |net63|/RT: Q5={hr['q5_long_fc']:.2f} Q1={hr['q1_short_fc']:.2f} "
          f"combined={hr['combined']:.2f} (threshold 10.0)")
    for pair, d in headroom["per_pair"].items():
        print(f"        {pair}: med|net| {d['median_abs_net_pips_combined']:.1f}p "
              f"vs 10xRT {d['threshold_10x_rt_pips']:.1f}p")
    print(f"[v]   annual IC: " + " ".join(f"{y}:{v:+.3f}" for y, v in
                                          regime["annual_ic_h42"].items()))
    print(f"      LOYO share: " + " ".join(f"{y}:{v:+.3f}" for y, v in
                                           regime["loyo_share_of_pooled_ic"].items()))
    print(f"      per-pair IC42: " + " ".join(f"{p_}:{d['ic_h42']:+.3f}"
                                              for p_, d in per_pair_ic.items()))
    print(f"      confirmatory non-overlap (qtr-end x 63bd, n={confirmatory['n']}): "
          f"IC={confirmatory['ic_h63']:+.4f} p={confirmatory['p_two_sided']:.4f}")
    print(f"      literal-mix variant (not for selection): IC42={ic_lit:+.4f} p={p_lit:.4f}")
    print(f"JSON -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
