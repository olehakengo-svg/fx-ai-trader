#!/usr/bin/env python3
"""KSFT Filter Efficacy — vwap_mean_reversion × KSFT quartile 分析 (read-only)

目的:
  alpha_factor_zoo で Bonferroni 有意だった KSFT factor を既存 vwap_mean_reversion
  signal と合成したときの conditional WR/EV/PF を測定する。

非侵襲:
  - 既存 `app.run_daytrade_backtest` を流して trade_log を取得するだけ
  - live path / BT signal は無変更
  - KSFT は BTDataCache の OHLC から post-hoc で再計算

判断プロトコル (CLAUDE.md):
  - 観測のみ。filter 実装は Shadow 検証 (Live N≥30) を経て別セッションで判断
  - vwap_mean_reversion の edge が KSFT quartile で条件付き強化されるかを確認

Usage:
    BT_MODE=1 python3 tools/ksft_filter_efficacy.py \
        [--pairs USD_JPY,GBP_JPY,GBP_USD] \
        [--strategy vwap_mean_reversion] \
        [--lookback 365]
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

from tools.bt_data_cache import BTDataCache


PAIR_TO_YF = {
    "USD_JPY": "USDJPY=X",
    "EUR_USD": "EURUSD=X",
    "GBP_USD": "GBPUSD=X",
    "EUR_JPY": "EURJPY=X",
    "GBP_JPY": "GBPJPY=X",
}


def compute_ksft_series(df: pd.DataFrame) -> pd.Series:
    """KSFT = (2*close - high - low) / (high - low + eps) — normalized variant (KSFT2)."""
    eps = 1e-12
    o, c, h, l = df["Open"], df["Close"], df["High"], df["Low"]
    # Use KSFT2 (normalized) — matches alpha_factor_zoo top cells
    return (2 * c - h - l) / (h - l + eps)


def parse_entry_time(et_str: str):
    try:
        ts = datetime.fromisoformat(et_str.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts
    except Exception:
        try:
            return datetime.strptime(et_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except Exception:
            return None


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


def quartile_stats(trades: list[dict]) -> dict:
    n = len(trades)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for t in trades if t.get("outcome") == "WIN")
    pnls = [compute_pnl_pip(t) for t in trades]
    pos = sum(p for p in pnls if p > 0)
    neg = sum(-p for p in pnls if p < 0)
    pf = (pos / neg) if neg > 0.0 else None
    return {
        "n": n,
        "wr": round(wins / n * 100, 1),
        "ev": round(sum(pnls) / n, 3),
        "pnl": round(sum(pnls), 2),
        "pf": round(pf, 2) if pf is not None else None,
    }


def attach_ksft(trades: list[dict], ksft_series: pd.Series, direction: str = "bias") -> list[dict]:
    """Find the bar at entry_time and attach KSFT value.

    direction:
      - "bias": raw KSFT value at entry bar (positive=bull imbalance)
      - "signed": flip sign for SHORT entries so filter is direction-aware
    """
    enriched = []
    for t in trades:
        ts = parse_entry_time(t.get("entry_time", ""))
        if ts is None:
            continue
        # Find nearest bar (<=) in ksft_series
        idx = ksft_series.index.get_indexer([ts], method="pad")
        if idx[0] < 0:
            continue
        k = ksft_series.iloc[idx[0]]
        if np.isnan(k):
            continue
        if direction == "signed":
            if (t.get("direction") or "").upper().startswith("S"):
                k = -k
        t2 = dict(t)
        t2["_ksft"] = float(k)
        enriched.append(t2)
    return enriched


def run_pair(yf_symbol: str, pair: str, strategy: str,
             lookback: int, interval: str) -> dict:
    print(f"\n[bt] {pair} ({yf_symbol}) × {lookback}d {interval}...")
    import app
    if hasattr(app, "_dt_bt_cache"):
        app._dt_bt_cache.clear()

    try:
        result = app.run_daytrade_backtest(yf_symbol, lookback_days=lookback,
                                            interval=interval)
    except Exception as e:
        return {"pair": pair, "error": f"BT failed: {e}"}

    if result.get("error"):
        return {"pair": pair, "error": result["error"]}

    trades = result.get("trade_log", [])
    matched = [t for t in trades if (t.get("entry_type") or "") == strategy]
    if not matched:
        return {"pair": pair, "error": f"no {strategy} trades"}

    # Fetch OHLC and compute KSFT
    cache = BTDataCache()
    df = cache.get(pair, interval, days=lookback)
    if df is None or len(df) < 200:
        return {"pair": pair, "error": "OHLC unavailable for KSFT"}
    if "Close" not in df.columns:
        df = df.rename(columns={c: c.capitalize() for c in df.columns})
    ksft = compute_ksft_series(df)

    # Attach raw (unsigned) KSFT and direction-signed KSFT
    raw = attach_ksft(matched, ksft, direction="bias")
    signed = attach_ksft(matched, ksft, direction="signed")

    def split_quartile(enriched: list[dict]) -> list[dict]:
        if len(enriched) < 8:
            return []
        ks = [t["_ksft"] for t in enriched]
        qs = np.quantile(ks, [0.25, 0.5, 0.75])
        buckets = [[], [], [], []]
        for t in enriched:
            k = t["_ksft"]
            if k <= qs[0]:
                buckets[0].append(t)
            elif k <= qs[1]:
                buckets[1].append(t)
            elif k <= qs[2]:
                buckets[2].append(t)
            else:
                buckets[3].append(t)
        out = []
        for qi, bucket in enumerate(buckets):
            stats = quartile_stats(bucket)
            stats["quartile"] = f"Q{qi+1}"
            stats["ksft_range"] = (
                f"<= {qs[0]:.3f}" if qi == 0 else
                f"{qs[qi-1]:.3f}..{qs[qi]:.3f}" if qi in (1, 2) else
                f"> {qs[2]:.3f}"
            )
            out.append(stats)
        return out

    overall = quartile_stats(matched)
    raw_q = split_quartile(raw)
    signed_q = split_quartile(signed)

    return {
        "pair": pair,
        "strategy": strategy,
        "n": len(matched),
        "overall": overall,
        "raw_quartiles": raw_q,         # unsigned KSFT (mean-reversion bias at bar)
        "signed_quartiles": signed_q,   # direction-signed KSFT (filter-mode)
    }


def render_markdown(results: list[dict], strategy: str, lookback: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# KSFT × {} — Conditional Efficacy Analysis".format(strategy),
        "",
        f"- **Generated**: {now}",
        f"- **Strategy**: {strategy}",
        f"- **Lookback**: {lookback} days",
        f"- **Factor**: KSFT2 = (2*C - H - L) / (H - L + eps) — Bonferroni-sig in alpha_factor_zoo",
        "",
        "## 読み方",
        "- **Raw quartiles**: entry bar の生 KSFT (正=高値寄り / 負=安値寄り)",
        "  - 仮説: vwap_mean_reversion は mean-reversion なので low-KSFT (-) bar で LONG は相性◎",
        "- **Signed quartiles**: direction-signed KSFT = LONG そのまま / SHORT 符号反転",
        "  - 仮説: signed KSFT が負の bar は「エントリー方向と逆の intra-bar imbalance」→ 期待値が高い",
        "",
    ]

    for r in results:
        lines.append(f"## {r['pair']} × {strategy}")
        lines.append("")
        if "error" in r:
            lines.append(f"- ❌ {r['error']}")
            lines.append("")
            continue

        ov = r["overall"]
        lines.append(f"- **Overall**: N={ov['n']} WR={ov['wr']}% EV={ov['ev']:+.3f}p PF={ov['pf']}")
        lines.append("")

        def render_table(label: str, qs: list[dict]):
            if not qs:
                lines.append(f"### {label}")
                lines.append("- N<8 (quartile化不能)")
                lines.append("")
                return
            lines.append(f"### {label}")
            lines.append("| Q | KSFT range | N | WR% | EV (pip) | PnL | PF |")
            lines.append("|---|-----------|--:|----:|---------:|----:|---:|")
            for q in qs:
                pf_str = f"{q['pf']}" if q['pf'] is not None else "—"
                lines.append(
                    f"| {q['quartile']} | {q['ksft_range']} | {q['n']} | "
                    f"{q['wr']}% | {q['ev']:+.3f} | {q['pnl']:+.2f} | {pf_str} |"
                )
            lines.append("")

        render_table("Raw KSFT quartiles", r["raw_quartiles"])
        render_table("Signed KSFT quartiles (direction-adjusted)", r["signed_quartiles"])

    lines += [
        "## 判断プロトコル遵守 (CLAUDE.md)",
        "- 観測のみ。KSFT filter 実装前に Shadow live N≥30 まで観察必要",
        "- 1 quartile 優位 ≠ 本番優位。730d × walk-forward で再検証推奨",
        "- **GO 条件**: (a) 最良 quartile と最悪 quartile の EV 差 ≥ 0.3pip AND (b) 全 pair で同方向の傾き",
        "",
        "## Source",
        "- Raw IC: `raw/bt-results/alpha-factor-zoo-2026-04-22.md` (KSFT2 IC<0 for all 5 pairs)",
        "- Generated by: `tools/ksft_filter_efficacy.py`",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="KSFT × strategy conditional efficacy")
    parser.add_argument("--pairs", default="USD_JPY,GBP_JPY,GBP_USD,EUR_USD",
                        help="Comma-separated pairs")
    parser.add_argument("--strategy", default="vwap_mean_reversion")
    parser.add_argument("--lookback", type=int, default=365)
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]

    print("=" * 60)
    print(f"  KSFT × {args.strategy}")
    print(f"  Pairs: {pairs}")
    print(f"  Lookback: {args.lookback}d {args.interval}")
    print("=" * 60)

    results = []
    for pair in pairs:
        yf = PAIR_TO_YF.get(pair)
        if yf is None:
            print(f"  ⚠️ unknown pair: {pair}")
            continue
        r = run_pair(yf, pair, args.strategy, args.lookback, args.interval)
        results.append(r)

    md = render_markdown(results, args.strategy, args.lookback)
    if args.output is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out = _PROJECT_ROOT / "knowledge-base" / "raw" / "bt-results" / f"ksft-{args.strategy}-{date_str}.md"
    else:
        out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"\n✅ Report: {out}")


if __name__ == "__main__":
    main()
