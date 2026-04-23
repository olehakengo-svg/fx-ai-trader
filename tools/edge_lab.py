#!/usr/bin/env python3
"""Edge Lab — Post-hoc multi-feature trade analysis

目的:
  BT trade_log を entry_time で raw 15m bars と join し、以下の特徴量を計算:
    T1: prior 5-bar return 符号 × direction (AR(1) momentum alignment)
    T2: day-of-month in {5,10,15,20,25,月末} (Gotobi)
    D1: realized vol z-score quintile (σ_20bar vs σ_60bar baseline)
    R1: Hurst exponent R/S on 50 prior bars
    S3: round-number distance (最寄 .00/.50 への pip 距離)

各 trade を feature × session で bin し、WR/EV を算出。
Tokyo/London/NY × feature quintile の cross-tabulation を出力。

非侵襲:
  - 既存 BT/live path 非改変
  - `app.run_daytrade_backtest` を呼んで trade_log を post-hoc 分析

判断プロトコル (CLAUDE.md):
  - 観測のみ。実装判断は walk-forward 730d 再検証後 (lesson-reactive-changes)
  - Shadow N≥30 蓄積まで feature filter の live 実装なし

Usage:
    python3 tools/edge_lab.py [--pairs USD_JPY,EUR_USD]
                               [--lookback 365]
                               [--min-n 20]
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import math

import numpy as np
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

DEFAULT_PAIRS = [
    ("USDJPY=X", "USD_JPY"),
    ("EURUSD=X", "EUR_USD"),
    ("GBPUSD=X", "GBP_USD"),
    ("EURJPY=X", "EUR_JPY"),
    ("GBPJPY=X", "GBP_JPY"),
]

SESSION_BOUNDS = [
    ("Tokyo",  0,  7),
    ("London", 7,  13),
    ("NY",     13, 21),
    ("Off",    21, 24),
]

GOTOBI_DAYS = {5, 10, 15, 20, 25}  # month-end は別判定


def parse_entry_time(et_str: str):
    try:
        ts = datetime.fromisoformat(et_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.strptime(et_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            return None


def classify_session(ts: datetime) -> str:
    h = ts.hour
    for name, start, end in SESSION_BOUNDS:
        if start <= h < end:
            return name
    return "Off"


def is_gotobi(ts: datetime) -> bool:
    if ts.day in GOTOBI_DAYS:
        return True
    # month-end = 末日 (simple heuristic: next day would be month 1)
    try:
        next_day = ts.replace(day=ts.day + 1)
        return False  # not last day
    except ValueError:
        return True  # ts.day+1 overflows → last day


def compute_pnl_pip(trade: dict) -> float:
    outcome = trade.get("outcome")
    tp_m = float(trade.get("tp_m") or 0.0)
    sl_m = float(trade.get("sl_m") or 0.0)
    friction = float(trade.get("exit_friction_m") or 0.0)
    if outcome == "WIN":
        return tp_m - friction
    actual_sl = trade.get("actual_sl_m")
    base = float(actual_sl) if actual_sl is not None else sl_m
    return -(base + friction)


def hurst_rs(series: np.ndarray) -> float:
    """R/S Hurst exponent estimator. 短系列 (50 bars) 向け簡易版."""
    n = len(series)
    if n < 20:
        return 0.5
    rets = np.diff(np.log(series + 1e-12))
    if len(rets) < 10:
        return 0.5
    # Multiple lag sizes
    lags = [8, 16, 24, 32] if n >= 50 else [4, 8, 12]
    rs_vals = []
    for lag in lags:
        if lag >= len(rets):
            continue
        chunks = len(rets) // lag
        if chunks < 1:
            continue
        rs_chunk = []
        for i in range(chunks):
            chunk = rets[i*lag:(i+1)*lag]
            mean = chunk.mean()
            Y = np.cumsum(chunk - mean)
            R = Y.max() - Y.min()
            S = chunk.std()
            if S > 0:
                rs_chunk.append(R / S)
        if rs_chunk:
            rs_vals.append((math.log(lag), math.log(np.mean(rs_chunk) + 1e-12)))
    if len(rs_vals) < 2:
        return 0.5
    xs = np.array([v[0] for v in rs_vals])
    ys = np.array([v[1] for v in rs_vals])
    slope = np.polyfit(xs, ys, 1)[0]
    return float(np.clip(slope, 0.0, 1.0))


def round_number_distance_pips(price: float, pair: str) -> float:
    """最寄 .00/.50 value への距離 (pips)."""
    if "JPY" in pair:
        # JPY pair: round at 0.50 (i.e., .00/.50 yen levels)
        fractional = price - math.floor(price)
        near = min(fractional, abs(fractional - 0.5), abs(fractional - 1.0))
        return near * 100  # 1 pip = 0.01 for JPY
    else:
        # Non-JPY: round at 0.0050 (i.e., .0000/.0050)
        scaled = price * 10000
        fractional = scaled - math.floor(scaled)
        near = min(fractional, abs(fractional - 50), abs(fractional - 100))
        return near  # already in pips


def compute_features(trade: dict, df: pd.DataFrame, pair: str) -> dict:
    """Trade と 15m bars から feature dict を返す."""
    ts = parse_entry_time(trade.get("entry_time", ""))
    if ts is None or df is None or df.empty:
        return {}
    # Align to bar
    df_idx = df.index
    if df_idx.tz is None:
        df_idx = df_idx.tz_localize("UTC")
    try:
        entry_loc = df_idx.searchsorted(ts)
    except Exception:
        return {}
    if entry_loc < 55:
        return {}  # not enough prior bars

    closes = df["Close"].values
    if entry_loc >= len(closes):
        return {}

    out = {}

    # T1: prior 5-bar return sign × direction
    try:
        r5 = (closes[entry_loc - 1] - closes[entry_loc - 6]) / closes[entry_loc - 6]
        direction = trade.get("direction") or trade.get("type") or "BUY"
        is_buy = direction.upper() in ("BUY", "LONG")
        # aligned = prior 5-bar return and direction have same sign
        aligned = (r5 > 0 and is_buy) or (r5 < 0 and not is_buy)
        out["t1_r5"] = r5
        out["t1_aligned"] = bool(aligned)
    except Exception:
        pass

    # T2: Gotobi flag
    try:
        out["t2_gotobi"] = bool(is_gotobi(ts))
    except Exception:
        pass

    # D1: realized vol z-score
    try:
        rets = np.diff(np.log(closes[entry_loc - 60:entry_loc] + 1e-12))
        sig20 = rets[-20:].std()
        sig60 = rets.std()
        sig60_of_20 = np.std([rets[i:i+20].std() for i in range(0, 40, 5) if i+20 <= 60])
        if sig60_of_20 > 0:
            z = (sig20 - sig60) / sig60_of_20
            out["d1_vol_z"] = float(z)
    except Exception:
        pass

    # R1: Hurst exponent
    try:
        series = closes[entry_loc - 50:entry_loc].astype(float)
        out["r1_hurst"] = hurst_rs(series)
    except Exception:
        pass

    # S3: round-number distance
    try:
        entry_price = float(trade.get("entry_price") or closes[entry_loc - 1])
        out["s3_rn_dist_p"] = round_number_distance_pips(entry_price, pair)
    except Exception:
        pass

    return out


def quintile_bin(value: float, cuts: list) -> int:
    """Return quintile index 0..4 given sorted cut points (4 cut → 5 bins)."""
    for i, c in enumerate(cuts):
        if value <= c:
            return i
    return len(cuts)


def analyze_pair(yf_symbol: str, pair: str, lookback: int) -> dict:
    print(f"\n[edge-lab] {pair} ({yf_symbol}) × {lookback}d 15m")
    from modules.data import fetch_ohlcv
    import app
    app._dt_bt_cache.clear()

    # 1. Fetch 15m data
    try:
        df = fetch_ohlcv(yf_symbol, period=f"{lookback}d", interval="15m")
        print(f"  bars: {len(df)}")
    except Exception as e:
        return {"pair": pair, "error": f"fetch failed: {e}"}

    # 2. Run BT
    try:
        result = app.run_daytrade_backtest(yf_symbol, lookback_days=lookback, interval="15m")
    except Exception as e:
        return {"pair": pair, "error": f"BT failed: {e}"}

    trades = result.get("trade_log", [])
    if not trades:
        return {"pair": pair, "error": "no trades"}
    print(f"  trades: {len(trades)}")

    # 3. Compute features per trade
    enriched = []
    for t in trades:
        feats = compute_features(t, df, pair)
        if not feats:
            continue
        ts = parse_entry_time(t.get("entry_time", ""))
        if ts is None:
            continue
        pnl = compute_pnl_pip(t)
        is_win = t.get("outcome") == "WIN"
        enriched.append({
            "strategy": t.get("entry_type") or "unknown",
            "session": classify_session(ts),
            "entry_time": ts.isoformat(),
            "pnl": pnl,
            "win": is_win,
            **feats,
        })

    print(f"  enriched: {len(enriched)}")
    return {"pair": pair, "trades": enriched}


def bin_stats(subset: list[dict]) -> dict:
    n = len(subset)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for t in subset if t["win"])
    pnls = [t["pnl"] for t in subset]
    pos = sum(p for p in pnls if p > 0)
    neg = sum(-p for p in pnls if p < 0)
    pf = (pos / neg) if neg > 0 else None
    return {
        "n": n,
        "wr": round(wins / n * 100, 1),
        "ev": round(sum(pnls) / n, 3),
        "pf": round(pf, 2) if pf else None,
    }


def render_report(all_results: list[dict], lookback: int, min_n: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = [
        "# Edge Lab — Post-hoc Multi-Feature Analysis",
        "",
        f"- **Generated**: {now}",
        f"- **Lookback**: {lookback}d / 15m",
        f"- **Min N per bin**: {min_n}",
        "",
        "## 特徴量定義",
        "- **T1** (AR(1) momentum): sign(prior 5-bar return) × entry direction",
        "  - `aligned=True`: entry 方向 = 直近 5 本の value 方向 (momentum)",
        "  - `aligned=False`: entry 方向 ≠ 直近 5 本 (counter-trend / MR)",
        "- **T2** (Gotobi): day-of-month ∈ {5,10,15,20,25,月末}",
        "- **D1** (Vol Z-score): σ_20bar の σ_60bar 分布内 z-score、quintile 分け",
        "- **R1** (Hurst): R/S 法による 50 bar Hurst 指数。H<0.45=MR regime / H>0.55=trend regime",
        "- **S3** (Round-number distance): entry price の最寄 .00/.50 レベルへの pip 距離、quintile",
        "",
    ]

    # Pool all trades across pairs for cross-sectional view
    pooled = []
    for r in all_results:
        if "error" in r:
            continue
        for t in r["trades"]:
            t = dict(t)
            t["pair"] = r["pair"]
            pooled.append(t)

    if not pooled:
        out.append("**No enriched trades** — check data fetch / BT output.")
        return "\n".join(out) + "\n"

    out.append(f"**Pooled enriched trades**: {len(pooled)}")
    out.append("")

    # --- T1: AR(1) momentum alignment × session ---
    out += ["## T1 — AR(1) Momentum Alignment × Session", ""]
    out.append("| Pair | Session | Aligned (momentum) N/WR/EV | Counter (MR) N/WR/EV |")
    out.append("|------|---------|----------------------------|----------------------|")
    for r in all_results:
        if "error" in r:
            continue
        for sess in ["Tokyo", "London", "NY"]:
            aligned = [t for t in r["trades"] if t.get("session") == sess and t.get("t1_aligned") is True]
            counter = [t for t in r["trades"] if t.get("session") == sess and t.get("t1_aligned") is False]
            if len(aligned) < min_n and len(counter) < min_n:
                continue
            a = bin_stats(aligned)
            c = bin_stats(counter)
            af = f"{a['n']}/{a['wr']}%/{a['ev']:+.2f}" if a["n"] else "—"
            cf = f"{c['n']}/{c['wr']}%/{c['ev']:+.2f}" if c["n"] else "—"
            out.append(f"| {r['pair']} | {sess} | {af} | {cf} |")
    out.append("")

    # --- T2: Gotobi effect (Tokyo only, JPY pairs only)
    out += ["## T2 — Gotobi Effect (JPY pair × Tokyo session)", ""]
    out.append("| Pair | Session | Gotobi N/WR/EV | Non-Gotobi N/WR/EV | Edge (pip) |")
    out.append("|------|---------|-----------------|--------------------|-----------:|")
    for r in all_results:
        if "error" in r or "JPY" not in r["pair"]:
            continue
        for sess in ["Tokyo", "London", "NY"]:
            goto = [t for t in r["trades"] if t.get("session") == sess and t.get("t2_gotobi") is True]
            nongoto = [t for t in r["trades"] if t.get("session") == sess and t.get("t2_gotobi") is False]
            if len(goto) < min_n and len(nongoto) < min_n:
                continue
            g = bin_stats(goto)
            ng = bin_stats(nongoto)
            gf = f"{g['n']}/{g['wr']}%/{g['ev']:+.2f}" if g["n"] else "—"
            nf = f"{ng['n']}/{ng['wr']}%/{ng['ev']:+.2f}" if ng["n"] else "—"
            edge = (g["ev"] - ng["ev"]) if (g["n"] and ng["n"]) else None
            ef = f"{edge:+.2f}" if edge is not None else "—"
            out.append(f"| {r['pair']} | {sess} | {gf} | {nf} | {ef} |")
    out.append("")

    # --- D1: Vol z-score quintile
    out += ["## D1 — Realized Vol Z-score Quintile (all strategies)", ""]
    out.append("| Pair | Vol Q1 (low) | Q2 | Q3 | Q4 (high) | Q5 (extreme) |")
    out.append("|------|-------------|----|----|----------|---------------|")
    for r in all_results:
        if "error" in r:
            continue
        vals = [t["d1_vol_z"] for t in r["trades"] if t.get("d1_vol_z") is not None]
        if len(vals) < 50:
            out.append(f"| {r['pair']} | (N<50 insufficient) | | | | |")
            continue
        cuts = np.quantile(vals, [0.2, 0.4, 0.6, 0.8]).tolist()
        bins = [[] for _ in range(5)]
        for t in r["trades"]:
            z = t.get("d1_vol_z")
            if z is None:
                continue
            q = quintile_bin(z, cuts)
            bins[q].append(t)
        cells = []
        for b in bins:
            s = bin_stats(b)
            if s["n"] == 0:
                cells.append("—")
            else:
                cells.append(f"{s['n']}/{s['wr']}%/{s['ev']:+.2f}")
        out.append(f"| {r['pair']} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[4]} |")
    out.append("")

    # --- R1: Hurst regime
    out += ["## R1 — Hurst Regime (H<0.45 MR / 0.45-0.55 neutral / H>0.55 trend)", ""]
    out.append("| Pair | MR (H<0.45) | Neutral | Trend (H>0.55) |")
    out.append("|------|-------------|---------|----------------|")
    for r in all_results:
        if "error" in r:
            continue
        mr = [t for t in r["trades"] if t.get("r1_hurst") is not None and t["r1_hurst"] < 0.45]
        nu = [t for t in r["trades"] if t.get("r1_hurst") is not None and 0.45 <= t["r1_hurst"] <= 0.55]
        tr = [t for t in r["trades"] if t.get("r1_hurst") is not None and t["r1_hurst"] > 0.55]
        def _f(s):
            if s["n"] == 0:
                return "—"
            return f"{s['n']}/{s['wr']}%/{s['ev']:+.2f}"
        out.append(f"| {r['pair']} | {_f(bin_stats(mr))} | {_f(bin_stats(nu))} | {_f(bin_stats(tr))} |")
    out.append("")

    # --- S3: Round-number distance quintile
    out += ["## S3 — Round-Number Distance Quintile (pips from nearest .00/.50)", ""]
    out.append("| Pair | Q1 (closest) | Q2 | Q3 | Q4 | Q5 (furthest) |")
    out.append("|------|--------------|----|----|----|---------------|")
    for r in all_results:
        if "error" in r:
            continue
        vals = [t["s3_rn_dist_p"] for t in r["trades"] if t.get("s3_rn_dist_p") is not None]
        if len(vals) < 50:
            continue
        cuts = np.quantile(vals, [0.2, 0.4, 0.6, 0.8]).tolist()
        bins = [[] for _ in range(5)]
        for t in r["trades"]:
            v = t.get("s3_rn_dist_p")
            if v is None:
                continue
            q = quintile_bin(v, cuts)
            bins[q].append(t)
        cells = []
        for b in bins:
            s = bin_stats(b)
            cells.append(f"{s['n']}/{s['wr']}%/{s['ev']:+.2f}" if s["n"] else "—")
        out.append(f"| {r['pair']} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[4]} |")
    out.append("")

    # --- Cross: Hurst × Strategy (vwap_mean_reversion should prefer H<0.45)
    out += ["## Cross: vwap_mean_reversion × Hurst regime (hypothesis: MR works in H<0.45)", ""]
    out.append("| Pair | H<0.45 (MR regime) | Neutral | H>0.55 (trend regime) |")
    out.append("|------|---------------------|---------|-----------------------|")
    for r in all_results:
        if "error" in r:
            continue
        vwap = [t for t in r["trades"] if t.get("strategy") == "vwap_mean_reversion"]
        mr = [t for t in vwap if t.get("r1_hurst") is not None and t["r1_hurst"] < 0.45]
        nu = [t for t in vwap if t.get("r1_hurst") is not None and 0.45 <= t["r1_hurst"] <= 0.55]
        tr = [t for t in vwap if t.get("r1_hurst") is not None and t["r1_hurst"] > 0.55]
        def _f(s):
            if s["n"] == 0:
                return "—"
            return f"{s['n']}/{s['wr']}%/{s['ev']:+.2f}"
        out.append(f"| {r['pair']} | {_f(bin_stats(mr))} | {_f(bin_stats(nu))} | {_f(bin_stats(tr))} |")
    out.append("")

    out += [
        "## 判断プロトコル (CLAUDE.md)",
        "- **観測のみ**. 実装判断は別期間 walk-forward で再検証後。",
        "- 1 回 BT の feature binning 発見 → Shadow N≥30 で確証取得まで filter 実装なし (lesson-reactive-changes)",
        "- 各 feature は pair 毎に逆方向の傾きが出ることがある (ksft-vwap 教訓)",
        "",
        "## Source",
        "- `tools/edge_lab.py` (post-hoc feature extraction + binning)",
        "- Based on `app.run_daytrade_backtest` trade_log",
    ]

    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default="")
    ap.add_argument("--lookback", type=int, default=365)
    ap.add_argument("--min-n", type=int, default=20)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    if args.pairs:
        wanted = {p.strip().upper() for p in args.pairs.split(",")}
        pairs = [(yf, pair) for yf, pair in DEFAULT_PAIRS if pair in wanted]
    else:
        pairs = DEFAULT_PAIRS

    all_results = []
    for yf, pair in pairs:
        res = analyze_pair(yf, pair, args.lookback)
        all_results.append(res)

    md = render_report(all_results, args.lookback, args.min_n)

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = _PROJECT_ROOT / "knowledge-base" / "raw" / "bt-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = Path(args.out_md) if args.out_md else out_dir / f"edge-lab-{date}.md"
    json_path = Path(args.out_json) if args.out_json else out_dir / f"edge-lab-{date}.json"

    md_path.write_text(md, encoding="utf-8")
    with json_path.open("w", encoding="utf-8") as f:
        # strip non-serializable
        def _clean(o):
            return [{k: v for k, v in t.items() if k != "df"} for t in o.get("trades", [])] if "trades" in o else o
        json.dump([{**r, "trades": _clean(r)} if "trades" in r else r for r in all_results],
                  f, default=str, ensure_ascii=False, indent=2)

    print(f"\n✅ Report: {md_path}")
    print(f"   JSON:   {json_path}")


if __name__ == "__main__":
    main()
