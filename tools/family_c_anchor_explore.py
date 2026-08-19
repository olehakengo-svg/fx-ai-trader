#!/usr/bin/env python3
"""family_c_anchor_explore.py — 台帳 #26 rate-anchor 乖離リバージョン explore (two-pass).

Spec: knowledge-base/wiki/decisions/family-c-rate-anchor-explore-prereg-2026-08-19.md (凍結)
規律: 測定は凍結コミット後のみ / pass-1 は per-date forward 値を一切出力しない (firewall) /
      OOS は 4 点機械ロック (§4-4)。モジュールトップ副作用なし / silent except なし。

CLI:
  python3 tools/family_c_anchor_explore.py freeze            # data_freeze コピー + manifest 生成
  python3 tools/family_c_anchor_explore.py pass1             # イベント列挙 + census (outcome 非接触)
  python3 tools/family_c_anchor_explore.py pass2             # primary + gates + verdict
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
Z_GRID = (1.5, 2.0, 2.5)       # pass-1 機械選定 grid
N_EV_RANGE = (30, 150)         # 選定レンジ
N_EV_TARGET = 60
MIN_SEP = 5                    # onset 最小間隔 (valid D1)
H_PRIMARY = 21                 # PRIMARY horizon (valid D1)
H_SECONDARY = 5                # 診断のみ
SPAN_MAX_CAL_H21 = 45          # fwd21 の暦日 span 上限
EXPLORE = ("2014-01-01", "2021-12-31")
OOS = ("2022-01-01", "2026-05-31")
MIN_BARS_DAY = 24              # UTC-day valid 条件 (15m バー数)
RET_SPAN_MAX_CAL = 7           # 日次 return の暦日 span 上限
RET_ABS_MAX = 0.05             # |r| > 5%/日 → assert 停止
YIELD_STALE_MAX_CAL = 5        # ffill staleness 上限 (暦日)
RT_POINT = 2.14                # pips (gate C)
RT_STRESSED = 4.3              # pips (gate D binding)
RT_3X = 6.4                    # pips (非拘束感度)
M_POINT = 1.0                  # %/yr financing markup (gate C)
M_ADVERSE = 1.65               # %/yr (gate D binding)
GATE_A_MIN_MEDIAN_ABS_FWD21 = 43.0   # pips = 10 × stressed_RT
GATE_B_MIN_NEV = 30
GATE_E_MAX_SHARE = 0.50
GATE_F_MIN_YEAR_SHARE = 0.60
GATE_F_MIN_EVENTS_PER_YEAR = 3
B_PERM = 10_000
SEED_PASS2 = 20260819
SEED_BLOCKFLIP = 20260820
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


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ─── data layer ──────────────────────────────────────────────────────────────
def load_bars_close(parquet_path: str) -> pd.DataFrame:
    """15m bars — Close 列のみロード (E12 P-10 firewall: Volume/H/L 非読取を assert)。"""
    df = pd.read_parquet(parquet_path, columns=["Close"])
    assert list(df.columns) == ["Close"], "E12 firewall: Close 以外を読んだ"
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df.sort_index()


def build_d1(bars: pd.DataFrame) -> pd.DataFrame:
    """UTC-day D1 (§2): weekday<5、n_bars>=MIN_BARS_DAY valid、close=最終バー close。"""
    g = bars.groupby(bars.index.date)
    d1 = pd.DataFrame({"close": g["Close"].last(), "n_bars": g.size()})
    d1 = d1[[d.weekday() < 5 for d in d1.index]]
    d1["valid"] = d1["n_bars"] >= MIN_BARS_DAY
    d1 = d1[d1["valid"]].copy()
    d1.index = pd.Index(d1.index, name="date")
    # 日次 log return: 連続 valid D1 間のみ、span>7暦日 void、|r|>5% assert
    dates = list(d1.index)
    closes = d1["close"].to_numpy()
    rets = [np.nan]
    for i in range(1, len(dates)):
        span = (dates[i] - dates[i - 1]).days
        if span > RET_SPAN_MAX_CAL:
            rets.append(np.nan)
            continue
        r = float(np.log(closes[i] / closes[i - 1]))
        assert abs(r) <= RET_ABS_MAX, f"|r|>{RET_ABS_MAX} @ {dates[i]} — 手動検分 (§2)"
        rets.append(r)
    d1["ret"] = rets
    return d1[["close", "n_bars", "ret"]]


def load_yield_2y(frz_jgb: str = FRZ_JGB, frz_ust: str = FRZ_UST,
                  tenor_jgb: str = "2y", tenor_ust: str = "DGS2") -> pd.DataFrame:
    """凍結コピーから diff (UST − JGB) を calendar-date で構成。"""
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
    """§2 join: D1 day d には label ≤ d−1 暦日の diff を割当 (lag 1 営業日の実装形 —
    暦日 d−1 の ffill 値は『d−1 までに公表された最新値』なので公表時刻 knife-edge を排除)。"""
    lag_dates = pd.DatetimeIndex([pd.Timestamp(d) - pd.Timedelta(days=1) for d in d1.index])
    diff = yields["diff"].reindex(lag_dates)
    out = d1.copy()
    out["diff2y"] = diff.to_numpy()
    return out


def compute_z(d1a: pd.DataFrame, w: int = W_ANCHOR) -> pd.DataFrame:
    """rolling OLS log(close) ~ diff2y (§3): z = resid/std_resid、縮退 void。"""
    df = d1a.copy()
    y = np.log(df["close"])
    x = df["diff2y"]
    # 完全窓必須: 窓内に diff NaN が 1 つでもあれば z void
    ok = x.notna()
    cnt = ok.rolling(w).sum()
    var_x = x.rolling(w).var(ddof=1)
    var_y = y.rolling(w).var(ddof=1)
    cov = x.rolling(w).cov(y)
    b = cov / var_x
    a = y.rolling(w).mean() - b * x.rolling(w).mean()
    resid = y - (a + b * x)
    resid_var = var_y - cov ** 2 / var_x
    std_resid = np.sqrt(resid_var.clip(lower=0))
    z = resid / std_resid
    std_x = x.rolling(w).std(ddof=1)
    df["z"] = z
    df["void_reason"] = ""
    df.loc[cnt < w, "z"] = np.nan
    df.loc[cnt < w, "void_reason"] = "warmup_or_stale"
    degen = (cnt >= w) & (std_x < DEGEN_STD_MIN)
    df.loc[degen, "z"] = np.nan
    df.loc[degen, "void_reason"] = "degenerate_anchor"
    df.loc[df["z"].notna(), "void_reason"] = ""
    return df


def detect_onsets(zs: pd.Series, z_th: float) -> tuple[list, list]:
    """onset (§3): 下方 = z が −Z_th を上から下へクロス、min-sep 5 valid D1。上方は記録用。"""
    valid = zs.dropna()
    dates, vals = list(valid.index), valid.to_numpy()
    lows, highs = [], []
    last_low_i, last_high_i = -(10 ** 9), -(10 ** 9)
    for i in range(1, len(vals)):
        if vals[i - 1] >= -z_th and vals[i] < -z_th:
            if i - last_low_i >= MIN_SEP:
                lows.append(dates[i])
                last_low_i = i
        if vals[i - 1] <= z_th and vals[i] > z_th:
            if i - last_high_i >= MIN_SEP:
                highs.append(dates[i])
                last_high_i = i
    return lows, highs


def select_zth(counts: dict) -> float | None:
    """§3 機械選定: N_ev∈[30,150] で |N−60| 最小、tie は大 Z_th。全<30→None、全>150→2.5。"""
    lo, hi = N_EV_RANGE
    in_range = [(abs(counts[z] - N_EV_TARGET), -z, z) for z in Z_GRID
                if lo <= counts[z] <= hi]
    if in_range:
        return sorted(in_range)[0][2]
    if all(counts[z] < lo for z in Z_GRID):
        return None
    if all(counts[z] > hi for z in Z_GRID):
        return max(Z_GRID)
    # 一部 <30 / 一部 >150 で range 内ゼロ: より保守側 (大 Z_th のうち >150 の最小超過) を採用
    over = [z for z in Z_GRID if counts[z] > hi]
    return max(over) if over else None


def fwd_move(d1: pd.DataFrame, t0, h: int, span_max_cal: int) -> float:
    """t0 (valid D1) から +h valid D1 の close-to-close move (pips)。span 超過/データ端は NaN。"""
    dates = list(d1.index)
    i = dates.index(t0)
    j = i + h
    if j >= len(dates):
        return np.nan
    if (dates[j] - dates[i]).days > span_max_cal:
        return np.nan
    return float((d1["close"].iloc[j] - d1["close"].iloc[i]) / PIP)


def load_swap_rate() -> pd.Series:
    df = pd.read_csv(SWAP_CSV, parse_dates=["date"], index_col="date")
    return df["USD_JPY"]


def swap_pips(rate_panel: pd.Series, t0, entry: float, h_cal_days: int, markup: float) -> float:
    """§7: swap = (d − m)/100 × H_cal/365 × S/PIP (LONG earn 側)。"""
    d = rate_panel.reindex([pd.Timestamp(t0)], method="ffill").iloc[0]
    if pd.isna(d):
        raise RuntimeError(f"swap panel 欠損 @ {t0}")
    return (float(d) - markup) / 100.0 * (h_cal_days / 365.0) * entry / PIP


# ─── git 状態 assert (機械ロック) ─────────────────────────────────────────────
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


def assert_manifest() -> dict:
    with open(MANIFEST, encoding="utf-8") as fh:
        m = json.load(fh)
    for name, rec in m["files"].items():
        p = rec["path"] if os.path.isabs(rec["path"]) else os.path.join(_REPO, rec["path"])
        assert os.path.exists(p), f"凍結ファイル不在: {p}"
        assert _sha256(p) == rec["sha256"], f"sha256 不一致 (drift): {name}"
    return m


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


def _build_frame(parquet_path: str) -> pd.DataFrame:
    d1 = build_d1(load_bars_close(parquet_path))
    yields = load_yield_2y()
    return compute_z(attach_anchor_inputs(d1, yields))


def _explore_mask(idx) -> np.ndarray:
    lo, hi = pd.Timestamp(EXPLORE[0]).date(), pd.Timestamp(EXPLORE[1]).date()
    return np.array([(lo <= d <= hi) for d in idx])


def run_pass1(parquet_path: str) -> dict:
    m = assert_manifest()
    frame = _build_frame(parquet_path)
    exp = frame[_explore_mask(frame.index)]

    counts, onset_map = {}, {}
    for z_th in Z_GRID:
        lows, highs = detect_onsets(frame["z"], z_th)
        lows_e = [d for d in lows if _explore_mask([d])[0]]
        highs_e = [d for d in highs if _explore_mask([d])[0]]
        counts[z_th] = len(lows_e)
        onset_map[z_th] = (lows_e, highs_e)
    z_sel = select_zth(counts)

    # 無条件 |fwd21| (シグナル非依存、aggregate のみ — firewall §4)
    dates = list(frame.index)
    abs_fwd = []
    for i, d in enumerate(dates):
        if not _explore_mask([d])[0]:
            continue
        mv = fwd_move(frame, d, H_PRIMARY, SPAN_MAX_CAL_H21)
        if not np.isnan(mv):
            abs_fwd.append(abs(mv))
    abs_fwd = np.array(abs_fwd)
    uncond = {"n": int(abs_fwd.size), "median": float(np.median(abs_fwd)),
              "sd": float(np.std(abs_fwd, ddof=1)),
              "p25": float(np.percentile(abs_fwd, 25)),
              "p75": float(np.percentile(abs_fwd, 75))}

    zs = frame["z"].dropna()
    acf = {f"lag{k}": float(zs.autocorr(k)) for k in (5, 10, 21, 42)}

    n_ev = counts.get(z_sel, 0) if z_sel else max(counts.values())
    sigma21 = uncond["sd"]
    mde = 2.49 * sigma21 / np.sqrt(max(n_ev, 1)) * 1.35  # (1.645+0.84)、重複 inflation 1.35 事前固定
    gate_a = uncond["median"] >= GATE_A_MIN_MEDIAN_ABS_FWD21
    gate_b = z_sel is not None and counts[z_sel] >= GATE_B_MIN_NEV

    void_census = frame.loc[_explore_mask(frame.index), "void_reason"].value_counts().to_dict()
    year_counts = {}
    if z_sel:
        for d in onset_map[z_sel][0]:
            year_counts[d.year] = year_counts.get(d.year, 0) + 1

    result = {
        "mode": "pass1", "manifest_ok": True, "z_grid_counts": {str(k): v for k, v in counts.items()},
        "z_selected": z_sel, "n_events_low": counts.get(z_sel) if z_sel else None,
        "n_events_high_descriptive": len(onset_map[z_sel][1]) if z_sel else None,
        "events_by_year": year_counts, "void_census": void_census,
        "uncond_abs_fwd21_pips": uncond, "z_acf": acf,
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
        # firewall (§4): シグナル列 (date|z|diff2y|side|z_th) のみ — forward 値は一切出力しない
        ev.to_csv(os.path.join(OUT_DIR, "family-c-pass1-events-2026-08-19.csv"), index=False)
    with open(os.path.join(OUT_DIR, "family-c-pass1-2026-08-19.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def _event_nets(frame: pd.DataFrame, rate_panel: pd.Series, onsets: list,
                rt: float, markup: float, h: int = H_PRIMARY,
                log_ret: bool = False) -> pd.DataFrame:
    rows = []
    dates = list(frame.index)
    for d in onsets:
        i = dates.index(d)
        if i + h >= len(dates):
            continue
        t_end = dates[i + h]
        if (t_end - d).days > SPAN_MAX_CAL_H21:
            continue
        entry, exitp = float(frame["close"].iloc[i]), float(frame["close"].iloc[i + h])
        mv = (np.log(exitp / entry) * entry / PIP) if log_ret else ((exitp - entry) / PIP)
        sp = swap_pips(rate_panel, d, entry, (t_end - d).days, markup)
        rows.append({"date": d, "year": d.year, "move": mv, "swap": sp,
                     "net": mv + sp - rt})
    return pd.DataFrame(rows)


def _placebo_pool(frame: pd.DataFrame, onsets: list, h: int) -> dict:
    """year → 有効候補日 (fwd 有効 ∧ onset±5 valid D1 除外) の index 位置リスト。"""
    dates = list(frame.index)
    pos = {d: i for i, d in enumerate(dates)}
    excl = set()
    for d in onsets:
        i = pos[d]
        excl.update(range(i - MIN_SEP, i + MIN_SEP + 1))
    pool = {}
    for i, d in enumerate(dates):
        if not _explore_mask([d])[0] or i in excl or i + h >= len(dates):
            continue
        if (dates[i + h] - d).days > SPAN_MAX_CAL_H21:
            continue
        pool.setdefault(d.year, []).append(i)
    return pool


def run_pass2(parquet_path: str) -> dict:
    assert_manifest()
    p1_json = os.path.join(OUT_DIR, "family-c-pass1-2026-08-19.json")
    _assert_committed(p1_json)  # pass-1 コミット後にのみ解錠 (§4)
    with open(p1_json, encoding="utf-8") as fh:
        p1 = json.load(fh)
    assert p1["gate_A_headroom"] and p1["gate_B_power"], "gate A/B 不通過 — pass-2 非解錠 (§4)"
    z_sel = float(p1["z_selected"])

    frame = _build_frame(parquet_path)
    rate_panel = load_swap_rate()
    lows_all, highs_all = detect_onsets(frame["z"], z_sel)
    lows = [d for d in lows_all if _explore_mask([d])[0]]
    assert len(lows) == p1["n_events_low"], "pass-1 イベント数と不一致 (再現性破れ)"

    nets = _event_nets(frame, rate_panel, lows, RT_POINT, M_POINT)
    mean_obs = float(nets["net"].mean())

    # Gate C: year-matched placebo permutation (§6)
    rng = np.random.default_rng(SEED_PASS2)
    pool = _placebo_pool(frame, lows, H_PRIMARY)
    dates = list(frame.index)
    year_counts = nets["year"].value_counts().to_dict()
    for y, k in year_counts.items():
        assert len(pool.get(y, [])) >= k * 3, f"placebo pool 薄すぎ year={y}"
    perm_means = np.empty(B_PERM)
    for b in range(B_PERM):
        tot, cnt = 0.0, 0
        for y, k in year_counts.items():
            cand = pool[y]
            chosen: list[int] = []
            for i in rng.permutation(len(cand)):
                ci = cand[i]
                if all(abs(ci - c) >= MIN_SEP for c in chosen):
                    chosen.append(ci)
                    if len(chosen) == k:
                        break
            assert len(chosen) == k, f"placebo 抽選不足 year={y}"
            for ci in chosen:
                d = dates[ci]
                t_end = dates[ci + H_PRIMARY]
                entry = float(frame["close"].iloc[ci])
                mv = (float(frame["close"].iloc[ci + H_PRIMARY]) - entry) / PIP
                sp = swap_pips(rate_panel, d, entry, (t_end - d).days, M_POINT)
                tot += mv + sp - RT_POINT
                cnt += 1
        perm_means[b] = tot / cnt
    p_one = float((1 + np.sum(perm_means >= mean_obs)) / (1 + B_PERM))
    gate_c = p_one <= 0.05

    # Gate D: adverse 端 + 3x 感度
    nets_adv = _event_nets(frame, rate_panel, lows, RT_STRESSED, M_ADVERSE)
    gate_d = float(nets_adv["net"].mean()) > 0
    nets_3x = _event_nets(frame, rate_panel, lows, RT_3X, M_ADVERSE)

    # Gate E: 年次集中
    s_y = nets.groupby("year")["net"].sum()
    gate_e = float(s_y.abs().max() / s_y.abs().sum()) <= GATE_E_MAX_SHARE

    # Gate F: 年次符号 (>=3 events 年のみ) + LOYO
    ymeans = nets.groupby("year").agg(n=("net", "size"), m=("net", "mean"))
    dense = ymeans[ymeans["n"] >= GATE_F_MIN_EVENTS_PER_YEAR]
    year_share = float((dense["m"] > 0).mean()) if len(dense) else 0.0
    loyo_ok = all(np.sign(nets[nets["year"] != y]["net"].mean()) == np.sign(mean_obs)
                  for y in ymeans.index)
    gate_f = (year_share >= GATE_F_MIN_YEAR_SHARE) and loyo_ok

    # Gate G: |z| 深さ tercile T3−T1 (onset 日の z を frame から取得)
    zvals = frame["z"].reindex(nets["date"]).abs().to_numpy()
    q1, q2 = np.percentile(zvals, [33.34, 66.67])
    t1 = nets["net"].to_numpy()[zvals <= q1]
    t3 = nets["net"].to_numpy()[zvals >= q2]
    gate_g = float(np.mean(t3) - np.mean(t1)) > 0

    binding = {"A": True, "C": gate_c, "D": gate_d, "E": gate_e, "F": gate_f, "G": gate_g}
    verdict = "explore PASS" if all(binding.values()) else "FAIL"

    result = {
        "mode": "pass2", "z_th": z_sel, "n_events": int(len(nets)),
        "mean_net_point_pips": round(mean_obs, 2),
        "median_net_point_pips": round(float(nets["net"].median()), 2),
        "wr": round(float((nets["net"] > 0).mean()), 3),
        "swap_mean_pips": round(float(nets["swap"].mean()), 2),
        "p_one_placebo": p_one,
        "placebo_mean_of_means": round(float(perm_means.mean()), 2),
        "mean_net_adverse_pips": round(float(nets_adv["net"].mean()), 2),
        "mean_net_rt3x_nonbinding_pips": round(float(nets_3x["net"].mean()), 2),
        "gate_E_max_share": round(float(s_y.abs().max() / s_y.abs().sum()), 3),
        "gate_F_year_share": round(year_share, 3), "gate_F_loyo_ok": bool(loyo_ok),
        "gate_G_t3_minus_t1": round(float(np.mean(t3) - np.mean(t1)), 2),
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
                       ("log_fwd", {"log_ret": True})]
        for zv, tag in ((z_sel - 0.5, "Zth_lo"), (z_sel + 0.5, "Zth_hi")):
            if zv in Z_GRID:  # 選定値の隣接 grid 内のみ (§5 knife-edge ii)
                ke_variants.append((tag, {"zth": zv}))
        for tag, kw in ke_variants:
            fr = frame
            if "w" in kw:
                d1 = build_d1(load_bars_close(parquet_path))
                fr = compute_z(attach_anchor_inputs(d1, load_yield_2y()), w=kw["w"])
            if "tenor" in kw:
                d1 = build_d1(load_bars_close(parquet_path))
                yl = load_yield_2y(tenor_jgb=kw["tenor"][0], tenor_ust=kw["tenor"][1])
                fr = compute_z(attach_anchor_inputs(d1, yl))
            zt = kw.get("zth", z_sel)
            lw = [d for d in detect_onsets(fr["z"], zt)[0] if _explore_mask([d])[0]]
            if not lw:
                ke[tag] = {"n": 0, "mean": None, "sign_flip": False}
                continue
            nn = _event_nets(fr, rate_panel, lw, RT_POINT, M_POINT,
                             log_ret=kw.get("log_ret", False))
            mnet = float(nn["net"].mean())
            ke[tag] = {"n": int(len(nn)), "mean": round(mnet, 2),
                       "sign_flip": bool(np.sign(mnet) != np.sign(mean_obs))}
        # (v) block sign-flip 代替 null (診断併記)
        rng2 = np.random.default_rng(SEED_BLOCKFLIP)
        iso = nets["date"].map(lambda d: (d.isocalendar()[0], d.isocalendar()[1] // 2))
        blocks = {}
        for bkey, sub in nets.groupby(iso):
            blocks[bkey] = sub["net"].to_numpy()
        flips = np.empty(B_PERM)
        for b in range(B_PERM):
            tot = sum(float(arr.sum()) * (1 if rng2.random() < 0.5 else -1)
                      for arr in blocks.values())
            flips[b] = tot / len(nets)
        ke["blockflip_p_one"] = float((1 + np.sum(flips >= mean_obs)) / (1 + B_PERM))
        result["knife_edge"] = ke
        if any(v.get("sign_flip") for v in ke.values() if isinstance(v, dict)):
            result["verdict"] = "FAIL"

    with open(os.path.join(OUT_DIR, "family-c-pass2-2026-08-19.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False, default=str)
        fh.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "yearly"},
                     indent=2, ensure_ascii=False, default=str))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode")
    for name in ("freeze", "pass1", "pass2"):
        sp = sub.add_parser(name)
        sp.add_argument("--parquet", default=PARQUET_DEFAULT)
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
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
