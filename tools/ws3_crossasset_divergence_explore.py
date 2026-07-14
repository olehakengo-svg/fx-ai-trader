#!/usr/bin/env python3
"""WS3 round-3 外部仮説 — cross-asset divergence-reversion 探索/OOS harness (rule:R1, read-only)

pre-reg: knowledge-base/wiki/decisions/ws3-round3-crossasset-divergence-prereg-2026-07-13.md
起点タスク: .ai/tasks/queue/20260713-ws3-round3-crossasset-divergence.md

仮説 (H1): FX (金利感応ペア) が rates (ZN=10y T-note fut) との contemporaneous linkage から
短期乖離 (rolling-β residual z-score) したとき、次 H バーで方向性を持って回帰する (divergence-reversion)。
H0: 乖離 z は次 H バーの符号付き超過リターンを予測しない (friction 調整後 EV ≤ 0)。

**乖離定義** (pre-reg §2b): rolling-β の rate-implied FX return からの残差の累積を z-score 化。
  β_t = rolling OLS slope of FX_logret on ZN_logret over trailing W bars
  resid_t = FX_logret_t − β_t · ZN_logret_t           (FX の rates 直交成分)
  S_t = cumsum(resid)                                   (rate-orthogonal drift、確率ウォーク様)
  z_t = (S_t − rollmean(S, W)) / rollstd(S, W)          (乖離 z-score)
  signal: |z_t| ≥ zthr → divergence event, reversion 方向 = −sign(z) を FX に適用

**EV primitive** (pre-reg §2c leg B に忠実): first-touch (±barrier=b·σ_pip, symmetric) を
horizon H バー以内で判定、未着なら close_{t+H} で time-exit。friction = per-pair round-trip pip 控除。
horizon-exit EV も併記 (barrier-free robustness、stage-2 の first-touch sequencing 感度を監視)。

**IC** (leg A): reversion IC = corr(z_t, fwd_H_ret)。機構整合は **負** (z 高 → 将来 FX 下落)。

窓 (data-availability amendment 2026-07-14 — pre-reg §2a の 2021-01-01〜 は intraday rates 不在で
falsified: yfinance 1h floor 2024-02-18 / Massive ZN futures aggs floor ~2024-07 / Massive equities
aggs floor ~2024-mid。日次のみ 2021+。結果観測前の data-driven 再指定 = look-ahead なし):
  EXPLORE : 2024-02-18 〜 2025-06-30  (~16.4mo)
  OOS     : 2025-07-01 〜 2026-05-15  (~10.5mo、FX cache 末尾)

read-only。live/shadow 一切不変更。BE/Trail は EV に関与させない (forward scan)。

実行:
  python3 tools/ws3_crossasset_divergence_explore.py discovery
  python3 tools/ws3_crossasset_divergence_explore.py oos
"""
import json
import os
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASSIVE = os.path.join(REPO, "data", "cache", "massive")
YIELD = os.path.join(REPO, "data", "cache", "yield")
OUTDIR = os.path.join(REPO, "knowledge-base", "raw", "bt-results")

DISC_START, DISC_END = "2024-02-18", "2025-06-30"
OOS_START, OOS_END = "2025-07-01", "2026-05-15"

# JPY 感応ペア優先 + 対照 (pre-reg §2a)
PAIRS = ["USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY", "EUR_USD", "GBP_USD"]

# 探索 grid (pre-reg §2b: 窓×z閾×horizon。探索窓で最適化可、選択バイアスは OOS で除去)
WINDOWS = [60, 120, 240]
ZTHR = [1.5, 2.0, 2.5]
HORIZONS = [6, 12, 24, 48]
BARRIER_MULT = 1.5  # first-touch symmetric barrier = 1.5 * rolling σ(pip)

# per-pair round-trip friction (pip)。KB friction-analysis + 保守推定 (GBP_JPY/AUD_JPY)
FRICTION = {
    "USD_JPY": 2.14, "EUR_USD": 2.00, "GBP_USD": 4.53,
    "EUR_JPY": 2.50, "GBP_JPY": 3.50, "AUD_JPY": 2.50,
}
PIP = {p: (0.01 if p.endswith("JPY") else 0.0001) for p in PAIRS}


def _load_fx(pair):
    f = os.path.join(MASSIVE, f"{pair}_1h.parquet")
    return pd.read_parquet(f) if os.path.exists(f) else None


def _load_zn():
    f = os.path.join(YIELD, "ZN_F_1h.parquet")
    return pd.read_parquet(f) if os.path.exists(f) else None


def _align(pair, zn):
    """共通 UTC 1h index に整合した FX/ZN logret を返す。"""
    fx = _load_fx(pair)
    if fx is None or zn is None:
        return None
    fr = np.log(fx["Close"]).diff()
    zr = np.log(zn["Close"]).diff()
    df = pd.DataFrame({"fx_close": fx["Close"], "fx_high": fx["High"],
                       "fx_low": fx["Low"], "fr": fr, "zr": zr}).dropna()
    return df


def _divergence_z(df, W):
    """rolling-β residual の累積 z-score。"""
    cov = df["fr"].rolling(W).cov(df["zr"])
    var = df["zr"].rolling(W).var()
    beta = cov / var
    resid = df["fr"] - beta * df["zr"]
    S = resid.cumsum()
    z = (S - S.rolling(W).mean()) / S.rolling(W).std()
    return z, beta


def _events(z, zthr, H):
    """|z|>=zthr の非重複イベント (min-spacing = H bars)。返り値 = 整数位置 list。"""
    hits = np.where(np.abs(z.values) >= zthr)[0]
    hits = hits[np.isfinite(z.values[hits])]
    ev, last = [], -10**9
    for i in hits:
        if i - last >= H:
            ev.append(i)
            last = i
    return ev


def _trade_outcomes(df, z, ev, H, pair):
    """各イベントの reversion 方向トレードの pip 損益 (first-touch と horizon-exit)。"""
    close = df["fx_close"].values
    high = df["fx_high"].values
    low = df["fx_low"].values
    n = len(close)
    pip = PIP[pair]
    # rolling σ(pip): 過去 24 バーの |close 変化| pip
    sig_pip = (df["fx_close"].diff().abs() / pip).rolling(24).mean().values
    ft, hz, zval, fwdret = [], [], [], []
    for i in ev:
        if i + H >= n or not np.isfinite(sig_pip[i]) or sig_pip[i] <= 0:
            continue
        d = -np.sign(z.values[i])  # reversion 方向 (+1 BUY / -1 SELL)
        if d == 0:
            continue
        entry = close[i]
        bar = BARRIER_MULT * sig_pip[i] * pip  # barrier (price)
        tp = entry + d * bar
        sl = entry - d * bar
        # first-touch within (i, i+H]
        out_ft = None
        for j in range(i + 1, i + H + 1):
            if d > 0:
                if high[j] >= tp:
                    out_ft = bar / pip; break
                if low[j] <= sl:
                    out_ft = -bar / pip; break
            else:
                if low[j] <= tp:
                    out_ft = bar / pip; break
                if high[j] >= sl:
                    out_ft = -bar / pip; break
        if out_ft is None:
            out_ft = d * (close[i + H] - entry) / pip  # time-exit
        ft.append(out_ft - FRICTION[pair])
        hz.append(d * (close[i + H] - entry) / pip - FRICTION[pair])
        zval.append(z.values[i])
        # forward raw return for IC (符号: reversion なら corr(z, fwd) < 0)
        fwdret.append((close[i + H] - entry) / entry)
    return np.array(ft), np.array(hz), np.array(zval), np.array(fwdret)


def _cell(df, z, zthr, H, pair):
    ev = _events(z, zthr, H)
    ft, hz, zval, fwd = _trade_outcomes(df, z, ev, H, pair)
    N = len(ft)
    if N == 0:
        return None
    ic = float(np.corrcoef(zval, fwd)[0, 1]) if N >= 3 and np.std(zval) > 0 and np.std(fwd) > 0 else float("nan")
    return {
        "pair": pair, "W": None, "zthr": zthr, "H": H, "N": int(N),
        "ev_firsttouch": float(np.mean(ft)), "ev_horizon": float(np.mean(hz)),
        "reversion_ic": ic,
        "ft_std": float(np.std(ft, ddof=1)) if N > 1 else float("nan"),
    }


def _scan(window_slice, phase_name):
    """全 (pair × W × zthr × H) セルを計測。df は phase 窓に slice 済み前提。"""
    zn = _load_zn()
    rows = []
    zn_range = None
    if zn is not None:
        zn_range = [str(zn.index.min()), str(zn.index.max())]
    for pair in PAIRS:
        dff = _align(pair, zn)
        if dff is None:
            continue
        for W in WINDOWS:
            z_full, _ = _divergence_z(dff, W)
            # slice to phase window AFTER computing z (rolling uses pre-window warmup)
            s, e = window_slice
            mask = (dff.index >= s) & (dff.index <= e)
            dfw = dff[mask]
            zw = z_full[mask]
            zw.index = dfw.index
            dfw = dfw.reset_index(drop=True)
            zw = zw.reset_index(drop=True)
            for zt in ZTHR:
                for H in HORIZONS:
                    c = _cell(dfw, zw, zt, H, pair)
                    if c is not None:
                        c["W"] = W
                        rows.append(c)
    return rows, zn_range


def _block_bootstrap_ic(zval, fwd, block=24, B=10000, seed=42):
    """日次ブロックブートストラップで reversion IC の 2-sided p (H0: IC=0)。"""
    rng = np.random.RandomState(seed)
    n = len(zval)
    if n < 10:
        return float("nan"), float("nan")
    obs = np.corrcoef(zval, fwd)[0, 1]
    nblk = int(np.ceil(n / block))
    boot = np.empty(B)
    idx_base = np.arange(n)
    for b in range(B):
        starts = rng.randint(0, n, size=nblk)
        idx = np.concatenate([np.arange(s, s + block) % n for s in starts])[:n]
        zb = zval[idx]
        # break dependence between z and fwd by resampling fwd independently → null dist
        fb = fwd[rng.permutation(n)]
        boot[b] = np.corrcoef(zb, fb)[0, 1] if np.std(zb) > 0 else 0.0
    p = float((np.abs(boot) >= abs(obs)).mean())
    return float(obs), p


def _bh_fdr(pvals, q=0.10):
    """Benjamini-Hochberg。返り値 = pass mask (同順)。"""
    p = np.asarray(pvals, float)
    m = np.isfinite(p).sum()
    if m == 0:
        return np.zeros(len(p), bool)
    order = np.argsort(np.where(np.isfinite(p), p, 2.0))
    passed = np.zeros(len(p), bool)
    thresh_rank = 0
    for rank, idx in enumerate(order, start=1):
        if not np.isfinite(p[idx]):
            continue
        if p[idx] <= q * rank / m:
            thresh_rank = rank
    for rank, idx in enumerate(order, start=1):
        if rank <= thresh_rank and np.isfinite(p[idx]):
            passed[idx] = True
    return passed


def discovery():
    rows, zn_range = _scan((DISC_START, DISC_END), "discovery")
    # 選抜規則 (pre-reg §2b): EV_firsttouch>0 ∧ reversion_ic 符号機構整合 (<0) ∧ N≥30
    cands = [r for r in rows
             if r["N"] >= 30 and np.isfinite(r["reversion_ic"])
             and r["reversion_ic"] < 0 and r["ev_firsttouch"] > 0]
    # rank: EV_firsttouch 降順 → IC 絶対値降順
    cands.sort(key=lambda r: (-r["ev_firsttouch"], r["reversion_ic"]))
    frozen = cands[:8]  # m≤8
    out = {
        "phase": "discovery", "window": [DISC_START, DISC_END],
        "zn_cache_range": zn_range, "n_cells_scanned": len(rows),
        "n_cells_selected": len(cands),
        "all_cells": sorted(rows, key=lambda r: -r["ev_firsttouch"]),
        "frozen_candidates": frozen,
    }
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "ws3_crossasset_divergence_discovery.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUTDIR, "ws3_round3_frozen_candidates.json"), "w") as f:
        json.dump({"window": [DISC_START, DISC_END], "frozen": frozen}, f, indent=2, ensure_ascii=False)
    print(f"[discovery] scanned={len(rows)} selected(EV>0∧IC<0∧N>=30)={len(cands)} frozen={len(frozen)}")
    for r in frozen:
        print(f"  {r['pair']:8s} W={r['W']:3d} z={r['zthr']} H={r['H']:2d} "
              f"N={r['N']:4d} EV_ft={r['ev_firsttouch']:+.3f} EV_hz={r['ev_horizon']:+.3f} IC={r['reversion_ic']:+.4f}")
    if not frozen:
        # 診断: EV>0 だけ / IC<0 だけの内訳
        ev_pos = [r for r in rows if r["N"] >= 30 and r["ev_firsttouch"] > 0]
        ic_neg = [r for r in rows if r["N"] >= 30 and np.isfinite(r["reversion_ic"]) and r["reversion_ic"] < 0]
        print(f"  [diag] N>=30 cells: EV_ft>0 alone={len(ev_pos)}, IC<0 alone={len(ic_neg)}")
        top_ev = sorted([r for r in rows if r['N']>=30], key=lambda r:-r['ev_firsttouch'])[:5]
        for r in top_ev:
            print(f"    top-EV {r['pair']:8s} W={r['W']:3d} z={r['zthr']} H={r['H']:2d} N={r['N']:4d} "
                  f"EV_ft={r['ev_firsttouch']:+.3f} IC={r['reversion_ic']:+.4f}")
    return out


def oos():
    frozen_path = os.path.join(OUTDIR, "ws3_round3_frozen_candidates.json")
    if not os.path.exists(frozen_path):
        print("[oos] frozen candidates not found — run discovery first")
        return None
    frozen = json.load(open(frozen_path))["frozen"]
    if not frozen:
        print("[oos] no frozen candidates (discovery selected 0) — OOS vacuous, verdict=PASS0")
        json.dump({"phase": "oos", "verdict": "PASS=0 (no candidate survived discovery)"},
                  open(os.path.join(OUTDIR, "ws3_crossasset_divergence_oos.json"), "w"),
                  indent=2, ensure_ascii=False)
        return None
    zn = _load_zn()
    results = []
    for fc in frozen:
        pair, W, zt, H = fc["pair"], fc["W"], fc["zthr"], fc["H"]
        dff = _align(pair, zn)
        z_full, _ = _divergence_z(dff, W)
        mask = (dff.index >= OOS_START) & (dff.index <= OOS_END)
        dfw = dff[mask].reset_index(drop=True)
        zw = z_full[mask].reset_index(drop=True)
        ev = _events(zw, zt, H)
        ft, hz, zval, fwd = _trade_outcomes(dfw, zw, ev, H, pair)
        N = len(ft)
        obs_ic, p_ic = (_block_bootstrap_ic(zval, fwd) if N >= 10 else (float("nan"), float("nan")))
        results.append({
            **fc, "oos_N": int(N),
            "oos_ev_firsttouch": float(np.mean(ft)) if N else float("nan"),
            "oos_ev_horizon": float(np.mean(hz)) if N else float("nan"),
            "oos_reversion_ic": obs_ic, "oos_ic_p": p_ic,
        })
    # leg A: BH-FDR on IC p-values ∧ |IC|>=0.05 ∧ N>=30
    pvals = [r["oos_ic_p"] for r in results]
    fdr_pass = _bh_fdr(pvals, q=0.10)
    for r, fp in zip(results, fdr_pass):
        r["legA_ic_pass"] = bool(fp and np.isfinite(r["oos_reversion_ic"])
                                 and abs(r["oos_reversion_ic"]) >= 0.05
                                 and r["oos_reversion_ic"] < 0 and r["oos_N"] >= 30)
        # leg B: first-touch EV OOS >= +0.5 p/t (簡略: セル単位。3x3 近傍は grid 密度不足のため best-cell 基準)
        r["legB_ev_pass"] = bool(np.isfinite(r["oos_ev_firsttouch"]) and r["oos_ev_firsttouch"] >= 0.5)
        r["PASS"] = bool(r["legA_ic_pass"] and r["legB_ev_pass"])
    n_pass = sum(r["PASS"] for r in results)
    out = {
        "phase": "oos", "window": [OOS_START, OOS_END],
        "n_frozen": len(frozen), "n_pass": n_pass, "results": results,
        "verdict": ("PASS>=1" if n_pass >= 1 else "PASS=0 (H0 採択)"),
    }
    json.dump(out, open(os.path.join(OUTDIR, "ws3_crossasset_divergence_oos.json"), "w"),
              indent=2, ensure_ascii=False)
    print(f"[oos] frozen={len(frozen)} PASS={n_pass} verdict={out['verdict']}")
    for r in results:
        print(f"  {r['pair']:8s} W={r['W']:3d} z={r['zthr']} H={r['H']:2d} "
              f"oosN={r['oos_N']:4d} EV_ft={r['oos_ev_firsttouch']:+.3f} "
              f"IC={r['oos_reversion_ic']:+.4f} p={r['oos_ic_p']:.4f} "
              f"legA={r['legA_ic_pass']} legB={r['legB_ev_pass']} PASS={r['PASS']}")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "discovery"
    if cmd == "discovery":
        discovery()
    elif cmd == "oos":
        oos()
    else:
        print("usage: ws3_crossasset_divergence_explore.py [discovery|oos]")
        sys.exit(1)
