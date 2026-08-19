#!/usr/bin/env python3
"""family_c_anchor_explore.py — 台帳 #26 rate-anchor 乖離リバージョン explore (two-pass + OOS).

Spec: knowledge-base/wiki/decisions/family-c-rate-anchor-explore-prereg-2026-08-19.md (凍結)
敵対的検証: knowledge-base/raw/analysis/family-c-adversarial-verification-2026-08-19.md
  (GO-WITH-CONDITIONS — blocking 条件は全て本ハーネス/pre-reg に凍結前反映済み。
   特に gate C null は合成 probe で反保守 (type-I 20-29%) と実証され、
   「年内 demean + episode-block sign-flip、p<=0.02」に差し替え)

規律: 測定は凍結コミット後のみ / pass-1 は per-date forward 値を一切出力しない (firewall) /
      OOS は 4 点機械ロック + 介入隣接 partition (§4-4/§5)。モジュールトップ副作用なし。

CLI:
  python3 tools/family_c_anchor_explore.py freeze
  python3 tools/family_c_anchor_explore.py pass1
  python3 tools/family_c_anchor_explore.py pass2
  python3 tools/family_c_anchor_explore.py oos --unlock-oos   # explore 全 gate PASS 時のみ
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# ─── 凍結パラメータ (§3/§5/§6/§7 — 変更禁止) ─────────────────────────────────
W_ANCHOR = 252                 # rolling OLS 窓 (valid D1)
DEGEN_STD_MIN = 0.10           # 窓内 std(diff2y) < 0.10%pt → z void
RESID_STD_MIN = 1e-12          # 完全 fit 縮退 (z=inf) ガード → void
Z_GRID = (1.5, 2.0, 2.5)       # pass-1 機械選定 grid
N_EV_RANGE = (30, 150)
N_EV_TARGET = 60
MIN_SEP = 5                    # onset 最小間隔 — frame (valid D1) position で計測
H_PRIMARY = 21                 # PRIMARY horizon (valid D1)
SPAN_MAX_CAL_H21 = 45
EXPLORE = ("2014-01-01", "2021-12-31")
OOS = ("2022-01-01", "2026-05-31")
MIN_BARS_DAY = 24
RET_SPAN_MAX_CAL = 7
RET_ABS_MAX = 0.05
YIELD_STALE_MAX_CAL = 12       # JGB 実測最大 gap 11 暦日 (2019 GW) を被覆 (敵対的検証 blocking)
RT_POINT = 2.14
RT_STRESSED = 4.3
RT_3X = 6.4                    # 非拘束感度 (m_adverse 併用)
M_POINT = 1.0
M_ADVERSE = 1.65
GATE_A_MIN_MEDIAN_ABS_FWD21 = 43.0
GATE_B_MIN_NEV = 30
GATE_C_P_MAX = 0.02            # probe 較正: episode-block null の実測 size ≈ 名目の ~2x
GATE_E_MAX_SHARE = 0.50
GATE_F_MIN_YEAR_SHARE = 0.60
GATE_F_MIN_EVENTS_PER_YEAR = 3
EPISODE_GAP = H_PRIMARY        # イベント間 gap < 21 valid D1 → 同一 episode block
ABLATION_JACCARD_MAX = 0.5     # 対照 (価格のみ z) との重複がこれ以上 → rates-content 未識別 caveat
ABLATION_NET_RATIO = 0.8
OOS_MIN_NEV = 15
OOS_MIN_NET = 10.0
B_PERM = 10_000
SEED_PASS2 = 20260819
SEED_PLACEBO = 20260820        # knife-edge 診断 (year-matched placebo、選択不使用)
SEED_OOS = 20260821
PIP = 0.01

FREEZE_DIR = os.path.join(_REPO, "knowledge-base", "raw", "bt-results", "family-c")
DATA_FREEZE = os.path.join(FREEZE_DIR, "data_freeze")
MANIFEST = os.path.join(FREEZE_DIR, "data_freeze_manifest_2026-08-19.json")
OUT_DIR = FREEZE_DIR
PARQUET_DEFAULT = "/Users/jg-n-012/test/fx-ai-trader/data/cache/massive/USD_JPY_15m_2014_2026.parquet"
SRC_JGB = os.path.join(_REPO, "data", "external", "rate_anchor", "jgb_yields.csv")
SRC_UST = os.path.join(_REPO, "data", "external", "rate_anchor", "us_treasury_yields.csv")
FRZ_JGB = os.path.join(DATA_FREEZE, "jgb_yields_2026-08-19.csv")
FRZ_UST = os.path.join(DATA_FREEZE, "us_treasury_yields_2026-08-19.csv")
SWAP_CSV = os.path.join(_REPO, "knowledge-base", "raw", "bt-results", "e20", "e20_carry_level.csv")
SWAP_EXT_CSV = os.path.join(_REPO, "knowledge-base", "raw", "bt-results", "e20",
                            "e20_carry_level_ext_2026-08.csv")
SWAP_EXT_MANIFEST = os.path.join(_REPO, "knowledge-base", "raw", "bt-results", "e20",
                                 "oos_swap_manifest_addendum.json")
MOF_CSV = os.path.join(_REPO, "data", "external", "mof_interventions.csv")
P1_JSON = os.path.join(OUT_DIR, "family-c-pass1-2026-08-19.json")
P1_EVENTS = os.path.join(OUT_DIR, "family-c-pass1-events-2026-08-19.csv")
P2_JSON = os.path.join(OUT_DIR, "family-c-pass2-2026-08-19.json")
OOS_JSON = os.path.join(OUT_DIR, "family-c-oos-2026-08-19.json")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ─── data layer ──────────────────────────────────────────────────────────────
def load_bars_close(parquet_path: str) -> pd.DataFrame:
    """15m bars — Close 列のみロード (E12 P-10 firewall)。"""
    df = pd.read_parquet(parquet_path, columns=["Close"])
    assert list(df.columns) == ["Close"], "E12 firewall: Close 以外を読んだ"
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df.sort_index()


def build_d1(bars: pd.DataFrame) -> pd.DataFrame:
    """UTC-day D1 (§2)。void 件数は .attrs['census'] に記録 (件数報告義務)。"""
    g = bars.groupby(bars.index.date)
    d1 = pd.DataFrame({"close": g["Close"].last(), "n_bars": g.size()})
    d1 = d1[[d.weekday() < 5 for d in d1.index]]
    n_thin = int((d1["n_bars"] < MIN_BARS_DAY).sum())
    d1 = d1[d1["n_bars"] >= MIN_BARS_DAY].copy()
    d1.index = pd.Index(d1.index, name="date")
    dates = list(d1.index)
    closes = d1["close"].to_numpy()
    rets, n_ret_void = [np.nan], 0
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days > RET_SPAN_MAX_CAL:
            rets.append(np.nan)
            n_ret_void += 1
            continue
        r = float(np.log(closes[i] / closes[i - 1]))
        assert abs(r) <= RET_ABS_MAX, f"|r|>{RET_ABS_MAX} @ {dates[i]} — 手動検分 (§2)"
        rets.append(r)
    d1["ret"] = rets
    d1.attrs["census"] = {"n_thin_void": n_thin, "n_ret_void": n_ret_void}
    return d1[["close", "n_bars", "ret"]]


def load_yield_2y(frz_jgb: str = FRZ_JGB, frz_ust: str = FRZ_UST,
                  tenor_jgb: str = "2y", tenor_ust: str = "DGS2") -> pd.DataFrame:
    """凍結コピーから diff (UST − JGB) を calendar-date で構成。staleness は使用日基準
    lag date で計測 (§2 凍結 wording: 値の使用時 age ≤ STALE_MAX+1 暦日)。"""
    jgb = pd.read_csv(frz_jgb, parse_dates=["date"], index_col="date")[tenor_jgb]
    ust = pd.read_csv(frz_ust, parse_dates=["date"], index_col="date")[tenor_ust]
    cal = pd.date_range(min(jgb.index.min(), ust.index.min()),
                        max(jgb.index.max(), ust.index.max()), freq="D")

    def _ffill_stale(s: pd.Series) -> pd.DataFrame:
        obs = s.dropna()
        f = obs.reindex(cal).ffill()
        last_obs = pd.Series(obs.index, index=obs.index).reindex(cal).ffill()
        stale = (cal - pd.DatetimeIndex(last_obs)).days
        return pd.DataFrame({"v": f.values, "stale": stale}, index=cal)

    j, u = _ffill_stale(jgb), _ffill_stale(ust)
    out = pd.DataFrame({
        "diff": u["v"] - j["v"],
        "stale": np.maximum(j["stale"], u["stale"]),
    }, index=cal)
    out.loc[out["stale"] > YIELD_STALE_MAX_CAL, "diff"] = np.nan
    return out


def attach_anchor_inputs(d1: pd.DataFrame, yields: pd.DataFrame) -> pd.DataFrame:
    """§2 join: D1 day d には label ≤ d−1 暦日の diff を割当 (公表時刻 knife-edge 排除)。"""
    lag_dates = pd.DatetimeIndex([pd.Timestamp(d) - pd.Timedelta(days=1) for d in d1.index])
    out = d1.copy()
    out["diff2y"] = yields["diff"].reindex(lag_dates).to_numpy()
    return out


def compute_z(d1a: pd.DataFrame, w: int = W_ANCHOR, price_only: bool = False) -> pd.DataFrame:
    """rolling OLS log(close) ~ diff2y (§3)。price_only=True は ablation 対照 (b≡0、
    z = (logC − rolling mean)/rolling std — 診断・選択不使用)。"""
    df = d1a.copy()
    y = np.log(df["close"])
    x = df["diff2y"]
    ok = x.notna()
    cnt = ok.rolling(w).sum()
    if price_only:
        mu = y.rolling(w).mean()
        sd = y.rolling(w).std(ddof=1)
        z = (y - mu) / sd
        std_resid = sd
        anchor_share = pd.Series(0.0, index=df.index)
    else:
        var_x = x.rolling(w).var(ddof=1)
        var_y = y.rolling(w).var(ddof=1)
        cov = x.rolling(w).cov(y)
        b = cov / var_x
        a = y.rolling(w).mean() - b * x.rolling(w).mean()
        resid = y - (a + b * x)
        std_resid = np.sqrt((var_y - cov ** 2 / var_x).clip(lower=0))
        z = resid / std_resid
        std_x = x.rolling(w).std(ddof=1)
        # anchor 寄与 census (敵対的検証 L2-7/C4): fitted 変動のうち b·diff2y 由来の share
        anchor_share = (b.abs() * std_x) / np.sqrt((b.abs() * std_x) ** 2 + std_resid ** 2)
    df["z"] = z
    df["anchor_share"] = anchor_share
    df["void_reason"] = ""
    pos = np.arange(len(df))
    warmup = pos < w - 1
    incomplete = (cnt < w).to_numpy()
    stale_gap = incomplete & ~warmup
    df.loc[incomplete, "z"] = np.nan
    df.loc[stale_gap, "void_reason"] = "stale_anchor"
    df.loc[warmup, "void_reason"] = "warmup"
    if not price_only:
        degen = (~incomplete) & ((std_x < DEGEN_STD_MIN) | (std_resid < RESID_STD_MIN)).to_numpy()
        df.loc[degen, "z"] = np.nan
        df.loc[degen, "void_reason"] = "degenerate_anchor"
    df.loc[df["z"].notna(), "void_reason"] = ""
    return df


def detect_onsets(frame: pd.DataFrame, z_th: float) -> tuple[list, list]:
    """onset (§3): 直前 valid z 観測 ≥ −Z_th ∧ 当日 z < −Z_th。
    min-sep は **frame (valid D1) position** で計測 (placebo/null と同一単位 — 敵対的検証 C3)。"""
    zs = frame["z"]
    dates = list(frame.index)
    lows, highs = [], []
    last_low_p, last_high_p = -(10 ** 9), -(10 ** 9)
    prev_val, prev_pos = None, None
    for p in range(len(dates)):
        v = zs.iloc[p]
        if pd.isna(v):
            continue
        if prev_val is not None:
            if prev_val >= -z_th and v < -z_th and p - last_low_p >= MIN_SEP:
                lows.append(dates[p])
                last_low_p = p
            if prev_val <= z_th and v > z_th and p - last_high_p >= MIN_SEP:
                highs.append(dates[p])
                last_high_p = p
        prev_val, prev_pos = v, p
    return lows, highs


def select_zth(counts: dict) -> float | None:
    """§3 機械選定 (凍結): range 内 → |N−60| 最小 (tie 大)、全<30 → UNDERPOWERED、
    全>150 → 2.5、**混在で range 内ゼロ → UNDERPOWERED** (敵対的検証 C3/C5 — 反保守側の
    多イベント採用を禁止)。"""
    lo, hi = N_EV_RANGE
    in_range = [(abs(counts[z] - N_EV_TARGET), -z, z) for z in Z_GRID
                if lo <= counts[z] <= hi]
    if in_range:
        return sorted(in_range)[0][2]
    if all(counts[z] > hi for z in Z_GRID):
        return max(Z_GRID)
    return None


def load_swap_rate(oos: bool = False) -> pd.Series:
    if not oos:
        df = pd.read_csv(SWAP_CSV, parse_dates=["date"], index_col="date")
        return df["USD_JPY"]
    # OOS: 延伸ファイル (§7) — フル被覆 + 凍結 csv との重複等値 assert
    df_ext = pd.read_csv(SWAP_EXT_CSV, parse_dates=["date"], index_col="date")
    df_frz = pd.read_csv(SWAP_CSV, parse_dates=["date"], index_col="date")
    s_ext, s_frz = df_ext["USD_JPY"], df_frz["USD_JPY"]
    assert s_ext.index.min() <= pd.Timestamp("2013-01-02"), "OOS swap 延伸: 左端不足"
    assert s_ext.index.max() >= pd.Timestamp("2026-06-30"), "OOS swap 延伸: 右端不足"
    common = s_frz.index.intersection(s_ext.index)
    assert len(common) > 2000, "OOS swap 延伸: 重複域が薄い"
    assert np.allclose(s_frz.reindex(common), s_ext.reindex(common), atol=1e-9), \
        "OOS swap 延伸: 凍結 csv と不等値 (§7 違反)"
    return s_ext


def swap_pips(rate_panel: pd.Series, t0, entry: float, h_cal_days: int, markup: float) -> float:
    d = rate_panel.reindex([pd.Timestamp(t0)], method="ffill").iloc[0]
    if pd.isna(d):
        raise RuntimeError(f"swap panel 欠損 @ {t0}")
    return (float(d) - markup) / 100.0 * (h_cal_days / 365.0) * entry / PIP


# ─── git / manifest asserts ──────────────────────────────────────────────────
def _assert_committed(path: str) -> None:
    rel = os.path.relpath(path, _REPO)
    r = subprocess.run(["git", "-C", _REPO, "status", "--porcelain", "--", rel],
                       capture_output=True, text=True, check=True)
    if r.stdout.strip():
        raise RuntimeError(f"機械ロック: {rel} が未コミット — pass 順序違反")
    r2 = subprocess.run(["git", "-C", _REPO, "ls-files", "--", rel],
                        capture_output=True, text=True, check=True)
    if not r2.stdout.strip():
        raise RuntimeError(f"機械ロック: {rel} が git 追跡外")


def assert_manifest(parquet_path: str | None = None) -> dict:
    with open(MANIFEST, encoding="utf-8") as fh:
        m = json.load(fh)
    for name, rec in m["files"].items():
        p = rec["path"] if os.path.isabs(rec["path"]) else os.path.join(_REPO, rec["path"])
        assert os.path.exists(p), f"凍結ファイル不在: {p}"
        assert _sha256(p) == rec["sha256"], f"sha256 不一致 (drift): {name}"
        rows = int(pd.read_parquet(p, columns=["Close"]).shape[0]) if p.endswith(".parquet") \
            else int(pd.read_csv(p).shape[0])
        assert rows == rec["rows"], f"行数不一致 (drift): {name}"
    if parquet_path is not None:
        # 実ロード対象 = manifest pin の同一物であることを直接 assert (敵対的検証 C2)
        rec = m["files"]["usdjpy_15m_parquet"]
        assert _sha256(parquet_path) == rec["sha256"], \
            "--parquet が manifest pin と別物 (bare/部分 parquet 罠)"
    return m


# ─── 共通計算 ────────────────────────────────────────────────────────────────
def _window_mask(idx, win) -> np.ndarray:
    lo, hi = pd.Timestamp(win[0]).date(), pd.Timestamp(win[1]).date()
    return np.array([(lo <= d <= hi) for d in idx])


def _event_nets(frame: pd.DataFrame, rate_panel: pd.Series, onsets: list,
                rt: float, markup: float, h: int = H_PRIMARY,
                entry_lag: int = 0) -> tuple[pd.DataFrame, int]:
    """per-event net (move + swap − rt)。戻り値 = (nets, n_dropped_fwd_invalid)。"""
    rows, dropped = [], 0
    dates = list(frame.index)
    pos = {d: i for i, d in enumerate(dates)}
    for d in onsets:
        i = pos[d] + entry_lag
        if i + h >= len(dates):
            dropped += 1
            continue
        t_in, t_end = dates[i], dates[i + h]
        if (t_end - t_in).days > SPAN_MAX_CAL_H21:
            dropped += 1
            continue
        entry, exitp = float(frame["close"].iloc[i]), float(frame["close"].iloc[i + h])
        mv = (exitp - entry) / PIP
        sp = swap_pips(rate_panel, t_in, entry, (t_end - t_in).days, markup)
        rows.append({"date": d, "year": d.year, "pos": pos[d], "move": mv, "swap": sp,
                     "net": mv + sp - rt})
    return pd.DataFrame(rows), dropped


def _uncond_year_means(frame: pd.DataFrame, rate_panel: pd.Series, win,
                       rt: float, markup: float) -> dict:
    """全 valid D1 日を LONG entry とみなした無条件 net_21 の年次平均 (§6 demean 基準)。"""
    dates = list(frame.index)
    sums, cnts = {}, {}
    for i, d in enumerate(dates):
        if not _window_mask([d], win)[0] or i + H_PRIMARY >= len(dates):
            continue
        t_end = dates[i + H_PRIMARY]
        if (t_end - d).days > SPAN_MAX_CAL_H21:
            continue
        entry = float(frame["close"].iloc[i])
        mv = (float(frame["close"].iloc[i + H_PRIMARY]) - entry) / PIP
        sp = swap_pips(rate_panel, d, entry, (t_end - d).days, markup)
        net = mv + sp - rt
        sums[d.year] = sums.get(d.year, 0.0) + net
        cnts[d.year] = cnts.get(d.year, 0) + 1
    return {y: sums[y] / cnts[y] for y in sums}


def _episode_blocks(nets: pd.DataFrame) -> list:
    """frame-position gap < EPISODE_GAP で連結した episode block ごとの demeaned-net 和のリスト。
    (§6 primary null: episode-block sign-flip — イベント間相関を保存する)"""
    blocks, cur = [], []
    last_pos = None
    for _, row in nets.sort_values("pos").iterrows():
        if last_pos is not None and row["pos"] - last_pos >= EPISODE_GAP:
            blocks.append(cur)
            cur = []
        cur.append(float(row["dnet"]))
        last_pos = row["pos"]
    if cur:
        blocks.append(cur)
    return [float(np.sum(b)) for b in blocks]


def gate_c_test(nets: pd.DataFrame, year_means: dict, seed: int) -> dict:
    """§5 Gate C (敵対的検証 C1 反映): stat = mean(net − μ_year)、
    null = episode-block sign-flip、片側 p。"""
    nets = nets.copy()
    nets["dnet"] = nets.apply(lambda r: r["net"] - year_means[r["year"]], axis=1)
    stat_obs = float(nets["dnet"].mean())
    block_sums = _episode_blocks(nets)
    rng = np.random.default_rng(seed)
    n = len(nets)
    flips = rng.choice([-1.0, 1.0], size=(B_PERM, len(block_sums)))
    # 要素積和 (matmul は macOS Accelerate BLAS の spurious FP 警告を出すため回避)
    perm = (flips * np.asarray(block_sums)).sum(axis=1) / n
    p_one = float((1 + np.sum(perm >= stat_obs)) / (1 + B_PERM))
    return {"stat_demeaned_mean": round(stat_obs, 2), "n_episode_blocks": len(block_sums),
            "p_one": p_one, "pass": p_one <= GATE_C_P_MAX}


# ─── modes ───────────────────────────────────────────────────────────────────
def run_freeze(parquet_path: str) -> None:
    os.makedirs(DATA_FREEZE, exist_ok=True)
    shutil.copy2(SRC_JGB, FRZ_JGB)
    shutil.copy2(SRC_UST, FRZ_UST)
    files = {
        "jgb_frozen": FRZ_JGB, "ust_frozen": FRZ_UST,
        "usdjpy_15m_parquet": parquet_path, "swap_panel": SWAP_CSV,
    }
    manifest = {"spec": "family-c-rate-anchor-explore-prereg-2026-08-19.md", "files": {}}
    for name, p in files.items():
        rows = int(pd.read_parquet(p, columns=["Close"]).shape[0]) if p.endswith(".parquet") \
            else int(pd.read_csv(p).shape[0])
        rel = p if os.path.isabs(p) and not p.startswith(_REPO) else os.path.relpath(p, _REPO)
        manifest["files"][name] = {"path": rel, "sha256": _sha256(p), "rows": rows}
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"frozen: {MANIFEST}")
    for name, rec in manifest["files"].items():
        print(f"  {name}: rows={rec['rows']} sha256={rec['sha256'][:12]}…")


def _build_frame(parquet_path: str, w: int = W_ANCHOR,
                 tenor: tuple = ("2y", "DGS2"), price_only: bool = False) -> pd.DataFrame:
    d1 = build_d1(load_bars_close(parquet_path))
    yields = load_yield_2y(tenor_jgb=tenor[0], tenor_ust=tenor[1])
    frame = compute_z(attach_anchor_inputs(d1, yields), w=w, price_only=price_only)
    frame.attrs["census"] = d1.attrs.get("census", {})
    return frame


def run_pass1(parquet_path: str) -> dict:
    assert_manifest(parquet_path)
    frame = _build_frame(parquet_path)
    emask = _window_mask(frame.index, EXPLORE)

    counts, onset_map = {}, {}
    for z_th in Z_GRID:
        lows, highs = detect_onsets(frame, z_th)
        lows_e = [d for d in lows if _window_mask([d], EXPLORE)[0]]
        highs_e = [d for d in highs if _window_mask([d], EXPLORE)[0]]
        counts[z_th] = len(lows_e)
        onset_map[z_th] = (lows_e, highs_e)
    z_sel = select_zth(counts)

    # 無条件 fwd21 (シグナル非依存、aggregate のみ — firewall §4)。
    # |move| 分位 = gate A 用 / signed sd = MDE 用 (敵対的検証 C2: sd(|X|) は MDE を過小報告)
    dates = list(frame.index)
    fwd = []
    for i, d in enumerate(dates):
        if not emask[i] or i + H_PRIMARY >= len(dates):
            continue
        if (dates[i + H_PRIMARY] - d).days > SPAN_MAX_CAL_H21:
            continue
        fwd.append((float(frame["close"].iloc[i + H_PRIMARY]) - float(frame["close"].iloc[i])) / PIP)
    fwd = np.array(fwd)
    abs_fwd = np.abs(fwd)
    uncond = {"n": int(fwd.size), "median_abs": float(np.median(abs_fwd)),
              "sd_abs": float(np.std(abs_fwd, ddof=1)),
              "sd_signed": float(np.std(fwd, ddof=1)),
              "p25_abs": float(np.percentile(abs_fwd, 25)),
              "p75_abs": float(np.percentile(abs_fwd, 75))}

    zs = frame["z"].dropna()
    acf = {f"lag{k}": float(zs.autocorr(k)) for k in (5, 10, 21, 42)}
    share = frame.loc[emask & frame["z"].notna().to_numpy(), "anchor_share"]
    anchor_census = {"p25": float(share.quantile(0.25)), "p50": float(share.quantile(0.5)),
                     "p75": float(share.quantile(0.75))} if len(share) else {}

    n_ev = counts.get(z_sel, 0) if z_sel else max(counts.values())
    mde = 2.485 * uncond["sd_signed"] / np.sqrt(max(n_ev, 1)) * 1.35
    gate_a = uncond["median_abs"] >= GATE_A_MIN_MEDIAN_ABS_FWD21
    gate_b = z_sel is not None and counts[z_sel] >= GATE_B_MIN_NEV

    void_census = frame.loc[emask, "void_reason"].value_counts().to_dict()
    void_census.pop("", None)
    void_census.update(frame.attrs.get("census", {}))
    year_counts = {}
    if z_sel:
        for d in onset_map[z_sel][0]:
            year_counts[d.year] = year_counts.get(d.year, 0) + 1

    result = {
        "mode": "pass1",
        "versions": {"numpy": np.__version__, "pandas": pd.__version__},
        "z_grid_counts": {str(k): v for k, v in counts.items()},
        "z_selected": z_sel, "n_events_low": counts.get(z_sel) if z_sel else None,
        "n_events_high_descriptive": len(onset_map[z_sel][1]) if z_sel else None,
        "events_by_year": year_counts, "void_census": void_census,
        "uncond_fwd21_pips": uncond, "z_acf": acf,
        "anchor_share_census": anchor_census,
        "mde_mean_net_pips": round(float(mde), 1),
        "gate_A_headroom": bool(gate_a), "gate_B_power": bool(gate_b),
        "verdict_if_stopped": None if (gate_a and gate_b) else ("KILL" if not gate_a else "UNDERPOWERED"),
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    if z_sel:
        rows = ([{"date": str(d), "z": round(float(frame["z"].loc[d]), 3),
                  "diff2y": round(float(frame["diff2y"].loc[d]), 4), "side": "low"}
                 for d in onset_map[z_sel][0]]
                + [{"date": str(d), "z": round(float(frame["z"].loc[d]), 3),
                    "diff2y": round(float(frame["diff2y"].loc[d]), 4),
                    "side": "high_descriptive"}
                   for d in onset_map[z_sel][1]])
        ev = pd.DataFrame(rows).sort_values("date")
        ev["z_th"] = z_sel
        # firewall (§4): シグナル列のみ — forward 値は一切出力しない
        ev.to_csv(P1_EVENTS, index=False)
    with open(P1_JSON, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def run_pass2(parquet_path: str) -> dict:
    assert_manifest(parquet_path)
    _assert_committed(P1_JSON)
    _assert_committed(P1_EVENTS)
    _assert_committed(os.path.abspath(__file__))  # ハーネス自己整合 (敵対的検証 C12)
    with open(P1_JSON, encoding="utf-8") as fh:
        p1 = json.load(fh)
    assert p1["gate_A_headroom"] and p1["gate_B_power"], "gate A/B 不通過 — pass-2 非解錠 (§4)"
    z_sel = float(p1["z_selected"])

    frame = _build_frame(parquet_path)
    rate_panel = load_swap_rate()
    lows = [d for d in detect_onsets(frame, z_sel)[0] if _window_mask([d], EXPLORE)[0]]
    assert len(lows) == p1["n_events_low"], "pass-1 イベント数と不一致 (再現性破れ)"

    nets, n_dropped = _event_nets(frame, rate_panel, lows, RT_POINT, M_POINT)
    if len(nets) < GATE_B_MIN_NEV:
        result = {"mode": "pass2", "z_th": z_sel, "n_onsets": len(lows),
                  "n_measured": int(len(nets)), "n_dropped_fwd_invalid": n_dropped,
                  "verdict": "UNDERPOWERED (measured N < 30)"}
        with open(P2_JSON, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False, default=str)
            fh.write("\n")
        print(json.dumps(result, ensure_ascii=False))
        return result
    mean_obs = float(nets["net"].mean())

    # Gate C: 年内 demean + episode-block sign-flip (§6 — probe 較正済み null)
    year_means = _uncond_year_means(frame, rate_panel, EXPLORE, RT_POINT, M_POINT)
    gc = gate_c_test(nets, year_means, SEED_PASS2)

    nets_adv, _ = _event_nets(frame, rate_panel, lows, RT_STRESSED, M_ADVERSE)
    gate_d = float(nets_adv["net"].mean()) > 0
    nets_3x, _ = _event_nets(frame, rate_panel, lows, RT_3X, M_ADVERSE)

    s_y = nets.groupby("year")["net"].sum()
    gate_e = float(s_y.abs().max() / s_y.abs().sum()) <= GATE_E_MAX_SHARE

    ymeans = nets.groupby("year").agg(n=("net", "size"), m=("net", "mean"))
    dense = ymeans[ymeans["n"] >= GATE_F_MIN_EVENTS_PER_YEAR]
    if len(dense):
        year_share = float((dense["m"] > 0).mean())
    else:  # 全年 sparse → 全年符号 share に fallback (§5 凍結)
        year_share = float((ymeans["m"] > 0).mean())
    loyo_ok = all(np.sign(nets[nets["year"] != y]["net"].mean()) == np.sign(mean_obs)
                  for y in ymeans.index)
    gate_f = (year_share >= GATE_F_MIN_YEAR_SHARE) and loyo_ok

    zvals = frame["z"].reindex(nets["date"]).abs().to_numpy()
    q1, q2 = np.percentile(zvals, [33.34, 66.67])
    t1 = nets["net"].to_numpy()[zvals <= q1]
    t3 = nets["net"].to_numpy()[zvals >= q2]
    gate_g = float(np.mean(t3) - np.mean(t1)) > 0

    # ablation 対照 (診断・選択不使用 — 敵対的検証 C4): b≡0 の価格のみ z
    frame_po = _build_frame(parquet_path, price_only=True)
    lows_po = [d for d in detect_onsets(frame_po, z_sel)[0] if _window_mask([d], EXPLORE)[0]]
    set_a, set_b = set(lows), set(lows_po)
    jac = len(set_a & set_b) / len(set_a | set_b) if (set_a | set_b) else 0.0
    nets_po, _ = _event_nets(frame_po, rate_panel, lows_po, RT_POINT, M_POINT)
    po_mean = float(nets_po["net"].mean()) if len(nets_po) else None
    rates_unidentified = bool(jac >= ABLATION_JACCARD_MAX and po_mean is not None
                              and mean_obs > 0 and po_mean >= ABLATION_NET_RATIO * mean_obs)

    binding = {"A": True, "C": gc["pass"], "D": gate_d, "E": gate_e, "F": gate_f, "G": gate_g}
    verdict = "explore PASS" if all(binding.values()) else "FAIL"

    result = {
        "mode": "pass2",
        "versions": {"numpy": np.__version__, "pandas": pd.__version__},
        "z_th": z_sel, "n_onsets": len(lows), "n_measured": int(len(nets)),
        "n_dropped_fwd_invalid": n_dropped,
        "mean_move_gross_pips": round(float(nets["move"].mean()), 2),
        "swap_mean_pips": round(float(nets["swap"].mean()), 2),
        "mean_net_point_pips": round(mean_obs, 2),
        "median_net_point_pips": round(float(nets["net"].median()), 2),
        "wr": round(float((nets["net"] > 0).mean()), 3),
        "gate_C": gc,
        "uncond_year_means": {str(y): round(v, 1) for y, v in sorted(year_means.items())},
        "mean_net_adverse_pips": round(float(nets_adv["net"].mean()), 2),
        "mean_net_rt3x_nonbinding_pips": round(float(nets_3x["net"].mean()), 2),
        "gate_E_max_share": round(float(s_y.abs().max() / s_y.abs().sum()), 3),
        "gate_F_year_share": round(year_share, 3), "gate_F_loyo_ok": bool(loyo_ok),
        "gate_F_dense_years": int(len(dense)),
        "gate_G_t3_minus_t1": round(float(np.mean(t3) - np.mean(t1)), 2),
        "ablation_control": {"jaccard": round(jac, 3), "control_mean_net": po_mean,
                             "n_control_events": int(len(nets_po)),
                             "rates_content_unidentified": rates_unidentified},
        "gates": {k: bool(v) for k, v in binding.items()},
        "yearly": {str(y): {"n": int(r["n"]), "mean": round(float(r["m"]), 1)}
                   for y, r in ymeans.iterrows()},
        "verdict": verdict,
        "knife_edge": None,
    }

    if verdict == "explore PASS":
        ke = {}
        ke_variants = [("W189", {"w": 189}), ("W378", {"w": 378}),
                       ("anchor10y", {"tenor": ("10y", "DGS10")}),
                       ("entry_lag1", {"entry_lag": 1})]
        for zv, tag in ((z_sel - 0.5, "Zth_lo"), (z_sel + 0.5, "Zth_hi")):
            if zv in Z_GRID:
                ke_variants.append((tag, {"zth": zv}))
        for tag, kw in ke_variants:
            fr = frame
            if "w" in kw:
                fr = _build_frame(parquet_path, w=kw["w"])
            if "tenor" in kw:
                fr = _build_frame(parquet_path, tenor=kw["tenor"])
            zt = kw.get("zth", z_sel)
            lw = [d for d in detect_onsets(fr, zt)[0] if _window_mask([d], EXPLORE)[0]]
            if not lw:
                ke[tag] = {"n": 0, "mean": None, "sign_flip": False}
                continue
            nn, _ = _event_nets(fr, rate_panel, lw, RT_POINT, M_POINT,
                                entry_lag=kw.get("entry_lag", 0))
            mnet = float(nn["net"].mean())
            ke[tag] = {"n": int(len(nn)), "mean": round(mnet, 2),
                       "sign_flip": bool(np.sign(mnet) != np.sign(mean_obs))}
        # (v) 代替 null 診断 = year-matched placebo (選択不使用、旧 primary — 反保守側の参考値)
        rng = np.random.default_rng(SEED_PLACEBO)
        pool = _placebo_pool(frame, lows, H_PRIMARY)
        dates_l = list(frame.index)
        year_counts = dict(sorted(nets["year"].value_counts().items()))
        perm_means = np.empty(B_PERM)
        for b in range(B_PERM):
            tot, cnt = 0.0, 0
            for y, k in year_counts.items():
                cand = pool[y]
                chosen: list[int] = []
                for j in rng.permutation(len(cand)):
                    ci = cand[j]
                    if all(abs(ci - c) >= MIN_SEP for c in chosen):
                        chosen.append(ci)
                        if len(chosen) == k:
                            break
                assert len(chosen) == k, f"placebo 抽選不足 year={y}"
                for ci in chosen:
                    d = dates_l[ci]
                    t_end = dates_l[ci + H_PRIMARY]
                    entry = float(frame["close"].iloc[ci])
                    mv = (float(frame["close"].iloc[ci + H_PRIMARY]) - entry) / PIP
                    tot += mv + swap_pips(rate_panel, d, entry, (t_end - d).days, M_POINT) - RT_POINT
                    cnt += 1
            perm_means[b] = tot / cnt
        ke["placebo_diag_p_one"] = float((1 + np.sum(perm_means >= mean_obs)) / (1 + B_PERM))
        result["knife_edge"] = ke
        if any(v.get("sign_flip") for v in ke.values() if isinstance(v, dict)):
            result["verdict"] = "FAIL"

    with open(P2_JSON, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)
        fh.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "yearly"},
                     indent=2, ensure_ascii=False, default=str))
    return result


def _placebo_pool(frame: pd.DataFrame, onsets: list, h: int) -> dict:
    """year → 候補日 (valid-z ∧ fwd 有効 ∧ onset±5 valid D1 除外) の frame position リスト。
    (敵対的検証 C4: z-void 日は除外 — イベントが構造的に不可能な日を null に入れない)"""
    dates = list(frame.index)
    pos = {d: i for i, d in enumerate(dates)}
    excl = set()
    for d in onsets:
        i = pos[d]
        excl.update(range(i - MIN_SEP, i + MIN_SEP + 1))
    pool = {}
    zna = frame["z"].notna().to_numpy()
    for i, d in enumerate(dates):
        if not _window_mask([d], EXPLORE)[0] or i in excl or i + h >= len(dates) or not zna[i]:
            continue
        if (dates[i + h] - d).days > SPAN_MAX_CAL_H21:
            continue
        pool.setdefault(d.year, []).append(i)
    return pool


def run_oos(parquet_path: str, unlock: bool) -> dict:
    """OOS pass (§4-4 4 点機械ロック + §5 OOS gates + 介入隣接 partition)。"""
    if not unlock:
        raise RuntimeError("機械ロック: --unlock-oos が必要 (§4-4 i)")
    assert_manifest(parquet_path)
    _assert_committed(P2_JSON)                       # (ii)
    _assert_committed(os.path.abspath(__file__))
    if os.path.exists(OOS_JSON):                      # (iii)
        raise RuntimeError("機械ロック: OOS 成果物が既存 — 再走は恒久禁止 (§4-4 iii)")
    _assert_committed(SWAP_EXT_MANIFEST)              # (iv)
    with open(P2_JSON, encoding="utf-8") as fh:
        p2 = json.load(fh)
    assert p2["verdict"] == "explore PASS", "OOS は explore 全 gate PASS 時のみ (§4)"
    z_sel = float(p2["z_th"])

    frame = _build_frame(parquet_path)
    rate_panel = load_swap_rate(oos=True)
    lows = [d for d in detect_onsets(frame, z_sel)[0] if _window_mask([d], OOS)[0]]

    # 介入隣接 partition (§5 — 敵対的検証 L2-1): 開示介入日の +21 valid D1 以内の onset は
    # binding から除外し記述併記。ラベルは signal に一切入らない (partition のみ)。
    mof = pd.read_csv(MOF_CSV, parse_dates=["date"])
    iv_days = [d.date() for d in mof.loc[mof["currency_pair"].str.contains("JPY", na=False),
                                          "date"]]
    dates = list(frame.index)
    pos = {d: i for i, d in enumerate(dates)}
    iv_pos = []
    for v in iv_days:
        nxt = [i for i, d in enumerate(dates) if d >= v]
        if nxt:
            iv_pos.append(nxt[0])
    def _adjacent(d) -> bool:
        p = pos[d]
        return any(0 <= p - ip <= H_PRIMARY for ip in iv_pos)
    lows_bind = [d for d in lows if not _adjacent(d)]
    lows_adj = [d for d in lows if _adjacent(d)]

    nets, n_dropped = _event_nets(frame, rate_panel, lows_bind, RT_POINT, M_POINT)
    result = {"mode": "oos", "z_th": z_sel, "n_onsets": len(lows),
              "n_binding": int(len(nets)), "n_intervention_adjacent": len(lows_adj),
              "n_dropped_fwd_invalid": n_dropped}
    if len(nets) < OOS_MIN_NEV:
        result["verdict"] = "OOS UNDERPOWERED (binding N < 15)"
    else:
        year_means = _uncond_year_means(frame, rate_panel, OOS, RT_POINT, M_POINT)
        gc = gate_c_test(nets, year_means, SEED_OOS)
        nets_adv, _ = _event_nets(frame, rate_panel, lows_bind, RT_STRESSED, M_ADVERSE)
        mean_net = float(nets["net"].mean())
        gates = {"i_p": gc["pass"], "ii_adverse": float(nets_adv["net"].mean()) > 0,
                 "iii_power": True, "iv_floor": mean_net >= OOS_MIN_NET}
        result.update({
            "gate_C_oos": gc,
            "mean_move_gross_pips": round(float(nets["move"].mean()), 2),
            "swap_mean_pips": round(float(nets["swap"].mean()), 2),
            "mean_net_point_pips": round(mean_net, 2),
            "mean_net_adverse_pips": round(float(nets_adv["net"].mean()), 2),
            "gates": gates,
            "verdict": "family PASS" if all(gates.values()) else "OOS FAIL",
        })
        if lows_adj:
            nets_all, _ = _event_nets(frame, rate_panel, lows, RT_POINT, M_POINT)
            result["with_adjacent_sensitivity_nonbinding"] = {
                "n": int(len(nets_all)), "mean_net": round(float(nets_all["net"].mean()), 2)}
    with open(OOS_JSON, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)
        fh.write("\n")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode")
    for name in ("freeze", "pass1", "pass2", "oos"):
        sp = sub.add_parser(name)
        sp.add_argument("--parquet", default=PARQUET_DEFAULT)
        if name == "oos":
            sp.add_argument("--unlock-oos", action="store_true")
    args = parser.parse_args(argv)
    if args.mode == "freeze":
        run_freeze(args.parquet)
        return 0
    if args.mode == "pass1":
        run_pass1(args.parquet)
        return 0
    if args.mode == "pass2":
        run_pass2(args.parquet)
        return 0
    if args.mode == "oos":
        run_oos(args.parquet, args.unlock_oos)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
