#!/usr/bin/env python3
"""T11 LDN morning counter-USD MR 12y MASSIVE grid.

Read-only research runner for:
  LDN morning (UTC07-09) x counter-USD mean-reversion class.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

os.environ["BT_MODE"] = "1"
os.environ["BT_REQUIRE_MASSIVE_CACHE"] = "1"
os.environ["NO_AUTOSTART"] = "1"

ROOT = Path(__file__).resolve().parents[1]
PARENT_ROOT = ROOT.parents[1] if ".worktrees" in ROOT.parts else ROOT

PAIRS = ("USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY")
INTERVAL = "15m"
DATE = "2026-07-06"
OUT_STEM = f"t11-ldn-morning-counter-usd-mr-12y-{DATE}"
OUT_JSON = ROOT / "bt-results" / f"{OUT_STEM}.json"
OUT_MD = ROOT / "bt-results" / f"{OUT_STEM}.md"
REPORT_MD = ROOT / "knowledge-base" / "wiki" / "learning" / f"{OUT_STEM}.md"

FRICTION_PIPS = {
    "USD_JPY": 2.14,
    "EUR_USD": 2.00,
    "GBP_USD": 4.53,
    "EUR_JPY": 2.50,
}

PIP_MULT = {
    "USD_JPY": 100.0,
    "EUR_USD": 10000.0,
    "GBP_USD": 10000.0,
    "EUR_JPY": 100.0,
}

SIGNAL_HOLD_BARS = 48  # 12h on 15m bars.
USD_TREND_BARS = 20 * 24 * 4
MR_WARMUP_BARS = max(USD_TREND_BARS, 200)


@dataclass(frozen=True)
class CacheSource:
    pair: str
    path: Path
    source: str


def _cache_candidates(pair: str) -> list[tuple[Path, str]]:
    names = [f"{pair}_{INTERVAL}_2014_2026.parquet", f"{pair}_{INTERVAL}.parquet"]
    roots = [ROOT, PARENT_ROOT]
    out: list[tuple[Path, str]] = []
    for base in roots:
        for name in names:
            p = base / "data" / "cache" / "massive" / name
            label = "worktree" if base == ROOT else "parent_checkout_readonly"
            out.append((p, label))
    return out


def _find_cache(pair: str) -> CacheSource:
    for path, source in _cache_candidates(pair):
        if path.exists():
            return CacheSource(pair=pair, path=path, source=source)
    tried = ", ".join(str(p) for p, _ in _cache_candidates(pair))
    raise FileNotFoundError(f"missing MASSIVE cache for {pair}: {tried}")


def _load_pair(pair: str) -> tuple[pd.DataFrame, CacheSource]:
    src = _find_cache(pair)
    df = pd.read_parquet(src.path).sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df = df[["Open", "High", "Low", "Close", "Volume", "vwap"]].copy()
    df = df[~df.index.duplicated(keep="last")]
    return df, src


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def _pair_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["Close"]
    out["rsi14"] = _rsi(close)
    mid = close.rolling(20, min_periods=20).mean()
    sd = close.rolling(20, min_periods=20).std(ddof=0)
    out["bb_mid"] = mid
    out["bb_upper"] = mid + 2.0 * sd
    out["bb_lower"] = mid - 2.0 * sd
    out["ema20"] = close.ewm(span=20, adjust=False, min_periods=20).mean()
    out["atr14"] = _atr(out)
    out["ret3"] = close.pct_change(3)
    return out


def _usd_proxy(close_by_pair: dict[str, pd.Series]) -> pd.DataFrame:
    idx = close_by_pair["USD_JPY"].index
    for pair in ("EUR_USD", "GBP_USD"):
        idx = idx.intersection(close_by_pair[pair].index)
    usd_rets = pd.DataFrame(index=idx)
    usd_rets["USD_JPY"] = np.log(close_by_pair["USD_JPY"].reindex(idx)).diff()
    usd_rets["EUR_USD"] = -np.log(close_by_pair["EUR_USD"].reindex(idx)).diff()
    usd_rets["GBP_USD"] = -np.log(close_by_pair["GBP_USD"].reindex(idx)).diff()
    proxy_ret = usd_rets.mean(axis=1, skipna=False)
    trend_20d = proxy_ret.rolling(USD_TREND_BARS, min_periods=USD_TREND_BARS).sum()
    threshold = float(trend_20d.abs().dropna().median())
    out = pd.DataFrame(index=idx)
    out["usd_proxy_ret"] = proxy_ret
    out["usd_proxy_20d_logret"] = trend_20d
    out["usd_direction"] = np.where(trend_20d >= 0.0, "USD_UP", "USD_DOWN")
    out["usd_regime"] = np.where(trend_20d.abs() >= threshold, "TREND", "RANGE")
    out.attrs["trend_abs_median_threshold"] = threshold
    return out


def _is_counter_usd(pair: str, side: str, usd_direction: str) -> bool:
    # BUY USD_JPY and SELL EUR/USD or GBP/USD are USD-long.
    if pair == "USD_JPY":
        trade_usd = "USD_UP" if side == "BUY" else "USD_DOWN"
    elif pair in {"EUR_USD", "GBP_USD"}:
        trade_usd = "USD_DOWN" if side == "BUY" else "USD_UP"
    elif pair == "EUR_JPY":
        # EUR/JPY has no USD leg. Use EUR/USD direction as USD exposure proxy:
        # BUY EUR/JPY is EUR-long/USD-short relative to the USD proxy.
        trade_usd = "USD_DOWN" if side == "BUY" else "USD_UP"
    else:
        raise ValueError(pair)
    return trade_usd != usd_direction


def _mr_signals(pair: str, df: pd.DataFrame, usd: pd.DataFrame) -> list[dict[str, Any]]:
    joined = df.join(usd[["usd_direction", "usd_regime", "usd_proxy_20d_logret"]], how="inner")
    rows: list[dict[str, Any]] = []
    pos = pd.Series(np.arange(len(joined)), index=joined.index)
    valid = (
        pos.ge(MR_WARMUP_BARS)
        & pos.lt(len(joined) - SIGNAL_HOLD_BARS - 1)
        & joined["usd_proxy_20d_logret"].notna()
    )
    buy_family_masks = {
        "bb20_2sigma": joined["Close"].le(joined["bb_lower"]),
        "rsi14_extreme": joined["rsi14"].le(30.0),
        "ema20_atr_pullback": joined["Close"].le(joined["ema20"] - 0.75 * joined["atr14"]) & joined["ret3"].lt(0.0),
    }
    sell_family_masks = {
        "bb20_2sigma": joined["Close"].ge(joined["bb_upper"]),
        "rsi14_extreme": joined["rsi14"].ge(70.0),
        "ema20_atr_pullback": joined["Close"].ge(joined["ema20"] + 0.75 * joined["atr14"]) & joined["ret3"].gt(0.0),
    }
    entry_s = joined["Open"].shift(-1)
    exit_s = joined["Close"].shift(-(1 + SIGNAL_HOLD_BARS))

    for side, family_masks in (("BUY", buy_family_masks), ("SELL", sell_family_masks)):
        any_signal = valid.copy()
        side_signal = pd.Series(False, index=joined.index)
        for mask in family_masks.values():
            side_signal |= mask.fillna(False)
        any_signal &= side_signal
        idx = joined.index[any_signal]
        for ts in idx:
            row = joined.loc[ts]
            usd_direction = str(row["usd_direction"])
            if not _is_counter_usd(pair, side, usd_direction):
                continue
            families = sorted(name for name, mask in family_masks.items() if bool(mask.loc[ts]))
            entry = float(entry_s.loc[ts])
            exit_ = float(exit_s.loc[ts])
            gross = (exit_ - entry) * PIP_MULT[pair]
            if side == "SELL":
                gross = -gross
            net = gross - FRICTION_PIPS[pair]
            rows.append(
                {
                    "pair": pair,
                    "entry_time": ts.isoformat(),
                    "side": side,
                    "families": sorted(families),
                    "hour_utc": int(ts.hour),
                    "time_bucket": "LDN_UTC07_09" if 7 <= int(ts.hour) <= 9 else "OTHER",
                    "usd_regime": str(row["usd_regime"]),
                    "usd_direction": usd_direction,
                    "usd_proxy_20d_logret": float(row["usd_proxy_20d_logret"]),
                    "gross_pips": float(gross),
                    "friction_pips": FRICTION_PIPS[pair],
                    "net_pips": float(net),
                    "win": bool(net > 0.0),
                }
            )
    return rows


def _wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float | None:
    if n <= 0:
        return None
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - spread) / denom)


def _profit_factor(values: list[float]) -> float | None:
    if not values:
        return None
    gross_profit = sum(v for v in values if v > 0)
    gross_loss = -sum(v for v in values if v < 0)
    if gross_loss <= 0.0:
        return math.inf if gross_profit > 0.0 else 0.0
    return gross_profit / gross_loss


def _finite(value: Any, ndigits: int = 6) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float, int)):
        v = float(value)
        if math.isfinite(v):
            return round(v, ndigits)
        return "inf" if v > 0 else "-inf"
    return value


def _welch_less(a: list[float], b: list[float]) -> float | None:
    if len(a) < 2 or len(b) < 2:
        return None
    from scipy import stats

    res = stats.ttest_ind(a, b, equal_var=False, alternative="less")
    p = float(res.pvalue)
    return p if math.isfinite(p) else None


def _metrics(rows: list[dict[str, Any]], comparator: list[dict[str, Any]] | None, m_tests: int) -> dict[str, Any]:
    vals = [float(r["net_pips"]) for r in rows]
    wins = sum(1 for v in vals if v > 0.0)
    n = len(vals)
    p = _welch_less(vals, [float(r["net_pips"]) for r in comparator]) if comparator is not None else None
    return {
        "N": n,
        "wins": wins,
        "WR": _finite(wins / n if n else None),
        "Wilson95_lower": _finite(_wilson_lower(wins, n)),
        "EV_pips": _finite(sum(vals) / n if n else None),
        "PnL_pips": _finite(sum(vals) if vals else None),
        "PF": _finite(_profit_factor(vals)),
        "p_vs_other_time_one_sided": _finite(p),
        "bonferroni_p": _finite(min(1.0, p * m_tests) if p is not None else None),
        "bonferroni_negative_ev": bool(p is not None and p * m_tests < 0.05 and n > 0 and sum(vals) / n < 0.0),
    }


def _summarize(trades: list[dict[str, Any]], sources: dict[str, CacheSource], usd: pd.DataFrame) -> dict[str, Any]:
    m_tests = 2 * 2 * len(PAIRS)
    cells: dict[str, dict[str, Any]] = {}
    for pair in PAIRS:
        for regime in ("TREND", "RANGE"):
            for bucket in ("LDN_UTC07_09", "OTHER"):
                key = f"{pair}|{regime}|{bucket}"
                rows = [r for r in trades if r["pair"] == pair and r["usd_regime"] == regime and r["time_bucket"] == bucket]
                comp = None
                if bucket == "LDN_UTC07_09":
                    comp = [
                        r
                        for r in trades
                        if r["pair"] == pair and r["usd_regime"] == regime and r["time_bucket"] == "OTHER"
                    ]
                cells[key] = _metrics(rows, comp, m_tests)

    target = [r for r in trades if r["time_bucket"] == "LDN_UTC07_09" and r["usd_regime"] == "TREND"]
    target_comp = [r for r in trades if r["time_bucket"] == "OTHER" and r["usd_regime"] == "TREND"]
    target_metrics = _metrics(target, target_comp, m_tests)
    pass_cells = [k for k, v in cells.items() if k.endswith("|LDN_UTC07_09") and v["bonferroni_negative_ev"]]
    verdict = "PASS" if target_metrics["EV_pips"] is not None and target_metrics["EV_pips"] < 0 and pass_cells else "FAIL"

    return {
        "id": "20260706-1250-t11-ldn-morning-counter-usd-mr-12y-grid",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "verdict_reason": (
            "LDN morning x counter-USD MR has Bonferroni-significant negative EV cells."
            if verdict == "PASS"
            else "LDN morning x counter-USD MR did not show a robust Bonferroni-significant negative EV structure."
        ),
        "design": {
            "interval": INTERVAL,
            "pairs": list(PAIRS),
            "time_bucket": "LDN_UTC07_09 means entry signal timestamp hour in {7,8,9} UTC",
            "usd_proxy": "equal-weight USD log-return proxy from USD_JPY, inverse EUR_USD, inverse GBP_USD",
            "usd_trend": "20d rolling log-return sign; TREND when abs(20d log-return) >= sample median",
            "mr_class": "deduped same-bar/side union of BB20 2sigma, RSI14 30/70, EMA20 +/-0.75 ATR pullback",
            "entry_exit": "next-bar open entry, 48-bar/12h close exit, per-pair round-trip friction subtracted",
            "friction_pips": FRICTION_PIPS,
            "bonferroni_m": m_tests,
        },
        "data_sources": {
            pair: {
                "path": str(src.path),
                "source": src.source,
            }
            for pair, src in sources.items()
        },
        "data_window": {
            "start": min(pd.Timestamp(r["entry_time"]) for r in trades).isoformat() if trades else None,
            "end": max(pd.Timestamp(r["entry_time"]) for r in trades).isoformat() if trades else None,
            "trade_count": len(trades),
            "usd_trend_abs_median_threshold": _finite(usd.attrs.get("trend_abs_median_threshold")),
        },
        "target": target_metrics,
        "cells": cells,
        "family_counts": {
            fam: sum(1 for r in trades if fam in r["families"])
            for fam in ("bb20_2sigma", "rsi14_extreme", "ema20_atr_pullback")
        },
        "pass_cells": pass_cells,
    }


def _md_table(result: dict[str, Any]) -> str:
    lines = [
        "| Pair | USD regime | Time | N | EV | PF | WR | Wilson | p | Bonf-p | Neg sig |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for key, m in result["cells"].items():
        pair, regime, bucket = key.split("|")
        lines.append(
            "| {pair} | {regime} | {bucket} | {N} | {EV} | {PF} | {WR} | {Wilson} | {p} | {bp} | {sig} |".format(
                pair=pair,
                regime=regime,
                bucket=bucket,
                N=m["N"],
                EV=m["EV_pips"],
                PF=m["PF"],
                WR=m["WR"],
                Wilson=m["Wilson95_lower"],
                p=m["p_vs_other_time_one_sided"],
                bp=m["bonferroni_p"],
                sig="YES" if m["bonferroni_negative_ev"] else "NO",
            )
        )
    return "\n".join(lines)


def _write_outputs(result: dict[str, Any]) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    target = result["target"]
    md = f"""# T11 LDN morning counter-USD MR 12y grid ({DATE})

- verdict: **{result['verdict']}**
- generated_at: {result['generated_at']}
- data_window: {result['data_window']['start']} .. {result['data_window']['end']}
- trade_count: {result['data_window']['trade_count']}
- source_guard: `BT_MODE=1`, `BT_REQUIRE_MASSIVE_CACHE=1`, MASSIVE parquet only

## Pre-reg Target

LDN morning (`UTC07-09`) x counter-USD MR x USD `TREND`:

| N | EV_pips | PF | WR | Wilson95_lower | p_vs_other_time | Bonferroni_p |
|---:|---:|---:|---:|---:|---:|---:|
| {target['N']} | {target['EV_pips']} | {target['PF']} | {target['WR']} | {target['Wilson95_lower']} | {target['p_vs_other_time_one_sided']} | {target['bonferroni_p']} |

## Grid

{_md_table(result)}

## Method

- USD proxy: equal-weight USD return from `USD_JPY`, inverse `EUR_USD`, inverse `GBP_USD`; `EUR_JPY` uses this external USD proxy.
- Counter-USD: entry direction is opposite the 20d USD proxy sign.
- USD regime: `TREND` if absolute 20d USD proxy log-return is above the sample median threshold (`{result['data_window']['usd_trend_abs_median_threshold']}`), else `RANGE`.
- MR class: same-bar/side deduped union of `BB20 2sigma`, `RSI14 30/70`, and `EMA20 +/-0.75 ATR pullback`.
- PnL: next-bar open entry, 48-bar/12h close exit, per-pair round-trip friction from `friction-analysis.md`.
- Bonferroni: m={result['design']['bonferroni_m']} cells (`time x regime x pair`); one-sided Welch test compares LDN vs OTHER within same pair/regime on net EV.

## Data Sources

{chr(10).join(f'- {p}: `{v["path"]}` ({v["source"]})' for p, v in result['data_sources'].items())}

## Verdict

{result['verdict_reason']}

Pass cells: `{', '.join(result['pass_cells']) or 'none'}`.
"""
    OUT_MD.write_text(md, encoding="utf-8")
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    data: dict[str, pd.DataFrame] = {}
    sources: dict[str, CacheSource] = {}
    for pair in PAIRS:
        df, src = _load_pair(pair)
        data[pair] = _pair_indicators(df)
        sources[pair] = src
    usd = _usd_proxy({pair: data[pair]["Close"] for pair in PAIRS})
    trades: list[dict[str, Any]] = []
    for pair in PAIRS:
        trades.extend(_mr_signals(pair, data[pair], usd))
    result = _summarize(trades, sources, usd)
    _write_outputs(result)
    print(json.dumps({"verdict": result["verdict"], "target": result["target"], "json": str(OUT_JSON), "report": str(REPORT_MD)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
