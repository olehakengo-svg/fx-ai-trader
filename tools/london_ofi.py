#!/usr/bin/env python3
"""London Open OFI Proxy — Order Flow Imbalance analysis

理論 (Cont-Kukanov-Stoikov 2014):
  Order Flow Imbalance (OFI) は次 bar return と正の相関を持つ。
  tick データ無しでも bar の wick structure から OFI proxy が計算できる:

    OFI_proxy(bar) = (close - low) / (high - low + ε) - 0.5
                   ∈ [-0.5, +0.5]

  正値: 買い優位 (close が high 寄り)
  負値: 売り優位 (close が low 寄り)

London open (UTC 7:00-8:30) は liquidity 流入が最大の時間帯。
この期間の OFI が後続 bars の return 方向を予測するか検定する。

Math:
  H0: ρ(OFI_t, return_{t+1}) = 0
  H1: ρ > 0.05 (Bonferroni 後)

検定:
  - pair × session で bar 単位 cross-correlation
  - quintile binning による WR 検定

非侵襲:
  - BT trade_log を使わない (raw bar-level 統計)
  - 既存 fetch_ohlcv のみ使用

判断プロトコル (CLAUDE.md):
  - 観測のみ。live 実装は walk-forward 730d 後
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

try:
    from dotenv import load_dotenv
    load_dotenv(_PROJECT_ROOT / ".env")
except Exception:
    pass

from modules.data import fetch_ohlcv

DEFAULT_PAIRS = [
    ("USDJPY=X", "USD_JPY"),
    ("EURUSD=X", "EUR_USD"),
    ("GBPUSD=X", "GBP_USD"),
    ("EURJPY=X", "EUR_JPY"),
    ("GBPJPY=X", "GBP_JPY"),
]

SESSION_BOUNDS = {
    "Tokyo":  (0, 7),
    "London": (7, 13),
    "NY":     (13, 21),
    "Off":    (21, 24),
}

LONDON_OPEN_WINDOW = (7, 10)  # UTC 7:00-10:00: london open + first 3h


def classify_session(h: int) -> str:
    for name, (s, e) in SESSION_BOUNDS.items():
        if s <= h < e:
            return name
    return "Off"


def pip_mult(pair: str) -> float:
    return 0.01 if "JPY" in pair else 0.0001


def compute_ofi_proxy(df: pd.DataFrame) -> pd.Series:
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    ofi = (df["close"] - df["low"]) / rng - 0.5
    return ofi.fillna(0.0)


def next_bar_return(df: pd.DataFrame, pair: str) -> pd.Series:
    p = pip_mult(pair)
    return (df["close"].shift(-1) - df["close"]) / p  # pip


def quintile_stats(x: np.ndarray, y: np.ndarray, n_bins: int = 5):
    """Return list of dicts: {bin, lo, hi, n, mean_y, wr_positive}"""
    if len(x) < n_bins * 10:
        return []
    cuts = np.quantile(x, np.linspace(0, 1, n_bins + 1))
    cuts[0] -= 1e-9
    cuts[-1] += 1e-9
    out = []
    for i in range(n_bins):
        mask = (x > cuts[i]) & (x <= cuts[i + 1])
        if mask.sum() < 10:
            continue
        ys = y[mask]
        out.append({
            "bin": i + 1,
            "lo": float(cuts[i]),
            "hi": float(cuts[i + 1]),
            "n": int(mask.sum()),
            "mean_y": float(np.nanmean(ys)),
            "wr_positive": float(np.mean(ys > 0)),
        })
    return out


def analyze_pair(yf_symbol: str, pair: str, lookback_days: int = 365):
    print(f"\n[london-ofi] {pair} ({yf_symbol}) × {lookback_days}d")
    period = f"{lookback_days}d"
    df = fetch_ohlcv(yf_symbol, period=period, interval="15m")
    if df is None or df.empty or len(df) < 200:
        print(f"[SKIP] insufficient data: {0 if df is None else len(df)}")
        return None

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    if "datetime" in df.columns:
        df["ts"] = pd.to_datetime(df["datetime"], utc=True)
    else:
        df["ts"] = pd.to_datetime(df.index, utc=True)
    df["hour"] = df["ts"].dt.hour
    df["session"] = df["hour"].apply(classify_session)
    df["ofi"] = compute_ofi_proxy(df)
    df["next_return_pip"] = next_bar_return(df, pair)
    df = df.dropna(subset=["ofi", "next_return_pip"])

    result = {"pair": pair, "sessions": {}, "london_open_window": {}}

    # Per-session OFI × next return correlation + quintile
    for sess in ["Tokyo", "London", "NY"]:
        sub = df[df["session"] == sess]
        if len(sub) < 100:
            continue
        rho = float(np.corrcoef(sub["ofi"], sub["next_return_pip"])[0, 1])
        qs = quintile_stats(sub["ofi"].values, sub["next_return_pip"].values)
        result["sessions"][sess] = {
            "n": len(sub),
            "rho": rho,
            "mean_return_pip": float(sub["next_return_pip"].mean()),
            "quintiles": qs,
        }

    # London open window (UTC 7-10) — focused analysis
    lo, hi = LONDON_OPEN_WINDOW
    sub_lo = df[(df["hour"] >= lo) & (df["hour"] < hi)]
    if len(sub_lo) >= 100:
        rho = float(np.corrcoef(sub_lo["ofi"], sub_lo["next_return_pip"])[0, 1])
        qs = quintile_stats(sub_lo["ofi"].values, sub_lo["next_return_pip"].values)
        result["london_open_window"] = {
            "window_utc": f"{lo:02d}:00-{hi:02d}:00",
            "n": len(sub_lo),
            "rho": rho,
            "mean_return_pip": float(sub_lo["next_return_pip"].mean()),
            "quintiles": qs,
        }

    return result


def render_report(results, out_md: Path, out_json: Path):
    lines = [
        "# London Open OFI Proxy — Order Flow Imbalance Analysis",
        "",
        f"- **Generated**: {datetime.now(timezone.utc).isoformat()}",
        "- **Theory**: Cont-Kukanov-Stoikov (2014)",
        "- **OFI proxy**: (close - low) / (high - low) - 0.5  ∈ [-0.5, +0.5]",
        "- **Target**: next-bar return (pip)",
        "",
        "## 読み方",
        "- **rho**: Pearson 相関 (OFI, next return). |rho| > 0.05 なら信号価値あり。",
        "- **Q1 (low OFI = sell pressure)**: 次 bar の期待 return が負なら OFI signal 有効。",
        "- **Q5 (high OFI = buy pressure)**: 次 bar の期待 return が正なら OFI signal 有効。",
        "- **London Open Window (UTC 7-10)**: liquidity 流入期。最も信号が強いはず。",
        "",
    ]

    for res in results:
        pair = res["pair"]
        lines.append(f"## {pair}")
        lines.append("")
        lines.append("### Session-level")
        lines.append("| Session | N | ρ(OFI, next_ret) | mean next_ret (pip) |")
        lines.append("|---------|--:|-----------------:|--------------------:|")
        for sess in ["Tokyo", "London", "NY"]:
            s = res["sessions"].get(sess)
            if s:
                lines.append(f"| {sess} | {s['n']} | {s['rho']:+.4f} | {s['mean_return_pip']:+.4f} |")
        lines.append("")

        for sess in ["Tokyo", "London", "NY"]:
            s = res["sessions"].get(sess)
            if not s or not s["quintiles"]:
                continue
            lines.append(f"#### {sess} — OFI quintile")
            lines.append("| Q | OFI range | N | mean next_ret (pip) | WR% next>0 |")
            lines.append("|---|-----------|--:|--------------------:|-----------:|")
            for q in s["quintiles"]:
                lines.append(f"| Q{q['bin']} | {q['lo']:+.3f}..{q['hi']:+.3f} | {q['n']} | {q['mean_y']:+.4f} | {q['wr_positive']*100:.1f}% |")
            lines.append("")

        low = res.get("london_open_window")
        if low:
            lines.append(f"### London Open Window (UTC {low['window_utc']})")
            lines.append(f"- N={low['n']}, ρ={low['rho']:+.4f}, mean={low['mean_return_pip']:+.4f} pip")
            lines.append("")
            lines.append("| Q | OFI range | N | mean next_ret (pip) | WR% next>0 |")
            lines.append("|---|-----------|--:|--------------------:|-----------:|")
            for q in low["quintiles"]:
                lines.append(f"| Q{q['bin']} | {q['lo']:+.3f}..{q['hi']:+.3f} | {q['n']} | {q['mean_y']:+.4f} | {q['wr_positive']*100:.1f}% |")
            lines.append("")

    lines.extend([
        "## 判断プロトコル (CLAUDE.md)",
        "- 観測のみ。Bonferroni 後 rho > 0.05 かつ Q1 vs Q5 mean_y 差 > 0.1 pip が成立条件。",
        "- 成立しても Shadow N≥30 + walk-forward 730d 必須。",
        "",
        "## Source",
        f"- Generated by: tools/london_ofi.py",
        f"- Related: knowledge-base/wiki/analyses/edge-matrix-2026-04-23.md L1 仮説",
    ])

    out_md.write_text("\n".join(lines))
    out_json.write_text(json.dumps(results, indent=2, default=str))
    print(f"[done] {out_md}")
    print(f"[done] {out_json}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default=",".join([p[1] for p in DEFAULT_PAIRS]))
    ap.add_argument("--lookback", type=int, default=365)
    args = ap.parse_args()

    wanted = set(s.strip() for s in args.pairs.split(","))
    pairs = [(yf, p) for yf, p in DEFAULT_PAIRS if p in wanted]

    results = []
    for yf_symbol, pair in pairs:
        try:
            r = analyze_pair(yf_symbol, pair, args.lookback)
            if r:
                results.append(r)
        except Exception as e:
            print(f"[ERROR] {pair}: {e}")
            import traceback
            traceback.print_exc()

    out_dir = _PROJECT_ROOT / "knowledge-base" / "raw" / "bt-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_md = out_dir / f"london-ofi-{today}.md"
    out_json = out_dir / f"london-ofi-{today}.json"
    render_report(results, out_md, out_json)


if __name__ == "__main__":
    main()
