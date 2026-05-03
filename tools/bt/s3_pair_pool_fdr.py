#!/usr/bin/env python3
"""S3 COT Dealer pair-pool backtest with BH-FDR.

Offline execution is the primary path for Codex: pass --use-cache-only and
provide COT/price JSON caches prepared by cot_socrata_fetcher.py.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Any, Iterable

import numpy as np
import pandas as pd

try:
    from scipy import stats
except Exception:  # pragma: no cover - scipy is available in the target env
    stats = None


PAIR_POOL = ("USDJPY", "USDCAD", "USDCHF", "GBPUSD", "EURUSD", "NZDUSD")
MARKETS = {
    "USDJPY": "JAPANESE YEN",
    "USDCAD": "CANADIAN DOLLAR",
    "USDCHF": "SWISS FRANC",
    "GBPUSD": "BRITISH POUND",
    "EURUSD": "EURO FX",
    "NZDUSD": "NZ DOLLAR",
}
YFINANCE_TICKERS = {pair: f"{pair}=X" for pair in PAIR_POOL}
PIP_SIZE = {
    "USDJPY": 0.01,
    "USDCAD": 0.0001,
    "USDCHF": 0.0001,
    "GBPUSD": 0.0001,
    "EURUSD": 0.0001,
    "NZDUSD": 0.0001,
}
ROUND_TRIP_COST_PIPS = 2.0
WAVE1_BASELINE = {"pf": 1.205, "wilson_lo": 0.470}


EVENT_DATES = {
    "USDJPY": [
        "2022-09-22",
        "2022-10-21",
        "2024-04-29",
        "2024-05-01",
        "2024-07-11",
        "2024-07-12",
    ],
    "USDCHF": ["2015-01-15"],
    "GBPUSD": ["2016-06-23"],
}


@dataclass(frozen=True)
class CachePaths:
    cot_cache: Path
    price_cache: Path


def parse_pairs(raw: str | Iterable[str]) -> list[str]:
    if isinstance(raw, str):
        pairs = [part.strip().upper() for part in raw.split(",") if part.strip()]
    else:
        pairs = [str(part).strip().upper() for part in raw if str(part).strip()]
    unknown = sorted(set(pairs) - set(PAIR_POOL))
    if unknown:
        raise ValueError(f"Unsupported S3 pair(s): {', '.join(unknown)}")
    return pairs


def cache_file(cache_dir: Path, pair: str) -> Path:
    return cache_dir / f"{pair}.json"


def missing_caches(pairs: list[str], paths: CachePaths) -> dict[str, list[str]]:
    missing = {"cot": [], "price": []}
    for pair in pairs:
        if not cache_file(paths.cot_cache, pair).exists():
            missing["cot"].append(pair)
        if not cache_file(paths.price_cache, pair).exists():
            missing["price"].append(pair)
    return missing


def load_cot(path: Path) -> pd.DataFrame:
    rows = json.loads(path.read_text())
    df = pd.DataFrame(rows)
    required = {"report_date", "change_in_dealer_long_all", "change_in_dealer_short_all"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} missing COT columns: {sorted(missing)}")
    df = df.copy()
    df["report_date"] = pd.to_datetime(df["report_date"]).dt.tz_localize(None)
    for col in ["change_in_dealer_long_all", "change_in_dealer_short_all"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["report_date"]).sort_values("report_date")


def load_prices(path: Path) -> pd.DataFrame:
    rows = json.loads(path.read_text())
    df = pd.DataFrame(rows)
    if "date" not in df.columns:
        raise ValueError(f"{path} missing date column")
    close_col = "close" if "close" in df.columns else "Close"
    if close_col not in df.columns:
        raise ValueError(f"{path} missing close column")
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(df["date"]).dt.tz_localize(None),
            "close": pd.to_numeric(df[close_col], errors="coerce"),
        }
    )
    return out.dropna().sort_values("date")


def signal_side(row: pd.Series) -> int:
    long_delta = row["change_in_dealer_long_all"]
    short_delta = row["change_in_dealer_short_all"]
    if long_delta > 0 and short_delta < 0:
        return 1
    if long_delta < 0 and short_delta > 0:
        return -1
    return 0


def next_friday(date: pd.Timestamp) -> pd.Timestamp:
    date = pd.Timestamp(date)
    days = (4 - date.weekday()) % 7
    return (date + pd.Timedelta(days=days)).normalize()


def _event_window(pair: str, start: pd.Timestamp, end: pd.Timestamp) -> bool:
    for raw in EVENT_DATES.get(pair, []):
        event = pd.Timestamp(raw)
        if pair in {"USDCHF", "GBPUSD"}:
            lo = event - pd.tseries.offsets.BDay(5)
            hi = event + pd.tseries.offsets.BDay(5)
        else:
            lo = hi = event
        if start <= hi and end >= lo:
            return True
    return False


def build_trades(
    pair: str,
    cot: pd.DataFrame,
    prices: pd.DataFrame,
    *,
    exclude_events: bool = True,
) -> pd.DataFrame:
    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"]).dt.tz_localize(None)
    price_series = prices.drop_duplicates("date").set_index("date")["close"].sort_index()
    rows: list[dict[str, Any]] = []
    pip = PIP_SIZE[pair]
    for _, cot_row in cot.iterrows():
        side = signal_side(cot_row)
        if side == 0:
            continue
        entry_date = next_friday(cot_row["report_date"])
        exit_date = entry_date + pd.Timedelta(days=7)
        entry_idx = price_series.index.searchsorted(entry_date)
        exit_idx = price_series.index.searchsorted(exit_date)
        if entry_idx >= len(price_series) or exit_idx >= len(price_series):
            continue
        actual_entry = price_series.index[entry_idx]
        actual_exit = price_series.index[exit_idx]
        if exclude_events and _event_window(pair, actual_entry, actual_exit):
            continue
        entry_price = float(price_series.iloc[entry_idx])
        exit_price = float(price_series.iloc[exit_idx])
        raw_pips = side * (exit_price - entry_price) / pip
        return_pips = raw_pips - ROUND_TRIP_COST_PIPS
        ret = return_pips * pip / entry_price
        report_date = pd.Timestamp(cot_row["report_date"])
        rows.append(
            {
                "pair": pair,
                "report_date": report_date,
                "side": "BUY" if side > 0 else "SELL",
                "entry_date": actual_entry,
                "exit_date": actual_exit,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return_pips": float(return_pips),
                "return": float(ret),
                "win": bool(return_pips > 0),
            }
        )
    return pd.DataFrame(rows)


def wilson_lower_bound(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return float("nan")
    phat = wins / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return (centre - margin) / denom


def profit_factor(returns: pd.Series) -> float:
    gains = float(returns[returns > 0].sum())
    losses = abs(float(returns[returns < 0].sum()))
    if losses == 0:
        return float("inf") if gains > 0 else float("nan")
    return gains / losses


def one_sided_t_pvalue(returns: pd.Series) -> tuple[float, float]:
    arr = pd.to_numeric(returns, errors="coerce").dropna().to_numpy(dtype=float)
    if len(arr) < 2 or np.std(arr, ddof=1) == 0:
        return float("nan"), float("nan")
    t_stat = float(np.mean(arr) / (np.std(arr, ddof=1) / math.sqrt(len(arr))))
    if stats is not None:
        p_value = float(stats.t.sf(t_stat, df=len(arr) - 1))
    else:
        p_value = 1 - NormalDist().cdf(t_stat)
    return t_stat, p_value


def oos_is_pf(trades: pd.DataFrame) -> tuple[float, float]:
    split = pd.Timestamp("2022-09-01")
    is_pf = profit_factor(trades.loc[trades["entry_date"] < split, "return"])
    oos_pf = profit_factor(trades.loc[trades["entry_date"] >= split, "return"])
    return is_pf, oos_pf


def kelly_fraction(returns: pd.Series) -> float:
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    if wins.empty or losses.empty:
        return 0.0
    wr = len(wins) / len(returns)
    avg_win = float(wins.mean())
    avg_loss = abs(float(losses.mean()))
    if avg_win <= 0:
        return 0.0
    return min(0.25, (wr * avg_win - (1 - wr) * avg_loss) / avg_win)


def classify_band(metrics: dict[str, Any]) -> str:
    if (
        metrics["pf"] >= 1.30
        and metrics["wilson_lo"] >= 0.55
        and metrics["sharpe"] > 1.0
        and metrics["kelly"] > 0.05
    ):
        return "A"
    if (
        metrics["pf"] >= 1.10
        and metrics["wilson_lo"] >= 0.50
        and metrics["sharpe"] > 0.5
        and metrics["kelly"] > 0
    ):
        return "B"
    return "C/Reject"


def pair_metrics(pair: str, trades: pd.DataFrame) -> dict[str, Any]:
    returns = trades["return"] if not trades.empty else pd.Series(dtype=float)
    n = int(len(returns))
    wins = int((returns > 0).sum())
    wr = wins / n if n else float("nan")
    pf = profit_factor(returns)
    wilson = wilson_lower_bound(wins, n)
    sharpe = float(returns.mean() / returns.std(ddof=1) * math.sqrt(52)) if n > 1 and returns.std(ddof=1) else float("nan")
    kelly = kelly_fraction(returns) if n else 0.0
    t_stat, p_value = one_sided_t_pvalue(returns)
    is_pf, oos_pf = oos_is_pf(trades) if not trades.empty else (float("nan"), float("nan"))
    metrics = {
        "pair": pair,
        "n": n,
        "wr": wr,
        "wins": wins,
        "pf": pf,
        "wilson_lo": wilson,
        "is_pf": is_pf,
        "oos_pf": oos_pf,
        "oos_pf_ratio_ok": bool(oos_pf >= 0.7 * is_pf) if math.isfinite(is_pf) and math.isfinite(oos_pf) else False,
        "sharpe": sharpe,
        "kelly": kelly,
        "t_stat": t_stat,
        "p_value": p_value,
        "sum_return": float(returns.sum()) if n else 0.0,
        "mean_return": float(returns.mean()) if n else float("nan"),
    }
    metrics["band"] = classify_band(metrics)
    return metrics


def benjamini_hochberg(rows: list[dict[str, Any]], q: float = 0.10) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: row.get("p_value", float("inf")))
    m = len(ordered)
    passing_rank = 0
    for i, row in enumerate(ordered, start=1):
        p_value = row.get("p_value", float("inf"))
        row["bh_rank"] = i
        row["bh_q_value"] = p_value * m / i if math.isfinite(p_value) else float("inf")
        if p_value <= (i / m) * q:
            passing_rank = i
    cutoff = ordered[passing_rank - 1]["p_value"] if passing_rank else -1
    for row in ordered:
        row["bh_significant"] = bool(row.get("p_value", float("inf")) <= cutoff)
    return ordered


def year_by_year(trades: pd.DataFrame) -> list[dict[str, Any]]:
    if trades.empty:
        return []
    out = []
    for year, part in trades.assign(year=trades["entry_date"].dt.year).groupby("year"):
        returns = part["return"]
        out.append(
            {
                "year": int(year),
                "n": int(len(part)),
                "wr": float((returns > 0).mean()),
                "pf": profit_factor(returns),
                "sum_return": float(returns.sum()),
            }
        )
    return out


def regime_flags(years: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total_positive = sum(max(0.0, row["sum_return"]) for row in years)
    flags = []
    if total_positive <= 0:
        return flags
    for row in years:
        share = max(0.0, row["sum_return"]) / total_positive
        if share > 0.50:
            flags.append({"year": row["year"], "positive_pnl_share": share})
    return flags


def null_bootstrap(trades: pd.DataFrame, iterations: int, seed: int = 20260503) -> dict[str, float | bool]:
    returns = trades["return"].to_numpy(dtype=float) if not trades.empty else np.array([])
    if len(returns) < 3:
        return {"null_p95_t_stat": float("nan"), "actual_t_stat": float("nan"), "pass": False}
    actual, _ = one_sided_t_pvalue(pd.Series(returns))
    rng = np.random.default_rng(seed)
    null_stats = []
    for _ in range(iterations):
        shuffled = rng.permutation(returns)
        t_stat, _ = one_sided_t_pvalue(pd.Series(shuffled))
        if math.isfinite(t_stat):
            null_stats.append(t_stat)
    p95 = float(np.percentile(null_stats, 95)) if null_stats else float("nan")
    return {"null_p95_t_stat": p95, "actual_t_stat": actual, "pass": bool(actual > p95)}


def wave1_regression_status(metrics: dict[str, float]) -> dict[str, Any]:
    pf_dev = abs(metrics["pf"] - WAVE1_BASELINE["pf"]) / WAVE1_BASELINE["pf"]
    wilson_dev = abs(metrics["wilson_lo"] - WAVE1_BASELINE["wilson_lo"]) / WAVE1_BASELINE["wilson_lo"]
    return {
        "pass": bool(pf_dev <= 0.05 and wilson_dev <= 0.05),
        "pf_deviation_pct": pf_dev * 100,
        "wilson_deviation_pct": wilson_dev * 100,
        "baseline": WAVE1_BASELINE,
    }


def portfolio_metrics(significant_pairs: list[str], trade_map: dict[str, pd.DataFrame]) -> dict[str, Any]:
    if not significant_pairs:
        return {"portfolio_sharpe": float("nan"), "diversification_ratio": float("nan")}
    series = []
    individual_sharpes = []
    for pair in significant_pairs:
        trades = trade_map[pair]
        s = trades.set_index("entry_date")["return"].rename(pair)
        series.append(s)
        individual_sharpes.append(pair_metrics(pair, trades)["sharpe"])
    frame = pd.concat(series, axis=1).fillna(0.0)
    portfolio = frame.mean(axis=1)
    p_sharpe = float(portfolio.mean() / portfolio.std(ddof=1) * math.sqrt(52)) if len(portfolio) > 1 and portfolio.std(ddof=1) else float("nan")
    max_ind = max([x for x in individual_sharpes if math.isfinite(x)], default=float("nan"))
    ratio = p_sharpe / max_ind if math.isfinite(p_sharpe) and math.isfinite(max_ind) and max_ind != 0 else float("nan")
    return {"portfolio_sharpe": p_sharpe, "diversification_ratio": ratio}


def correlation_matrix(trade_map: dict[str, pd.DataFrame]) -> dict[str, dict[str, float]]:
    series = [trades.set_index("entry_date")["return"].rename(pair) for pair, trades in trade_map.items()]
    if not series:
        return {}
    corr = pd.concat(series, axis=1).corr()
    return {
        idx: {col: (None if pd.isna(value) else float(value)) for col, value in row.items()}
        for idx, row in corr.iterrows()
    }


def extreme_decile_sanity(pair: str, cot: pd.DataFrame, prices: pd.DataFrame) -> dict[str, Any]:
    cot = cot.copy()
    cot["dealer_delta_abs"] = (
        cot["change_in_dealer_long_all"].abs() + cot["change_in_dealer_short_all"].abs()
    )
    threshold = float(cot["dealer_delta_abs"].quantile(0.90))
    trades = build_trades(pair, cot[cot["dealer_delta_abs"] >= threshold], prices, exclude_events=True)
    return {"pair": pair, "threshold": threshold, "metrics": pair_metrics(pair, trades)}


def run_backtest(
    *,
    pairs: list[str],
    cot_cache: Path,
    price_cache: Path,
    use_cache_only: bool,
    bootstrap_iterations: int = 1000,
) -> dict[str, Any]:
    paths = CachePaths(cot_cache=Path(cot_cache), price_cache=Path(price_cache))
    missing = missing_caches(pairs, paths)
    if missing["cot"] or missing["price"]:
        return {
            "status": "Insufficient(cache_missing)",
            "scenario": "Insufficient(cache_missing)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pairs": pairs,
            "missing_cache": missing,
            "phase1_commands": phase1_commands(),
        }
    if not use_cache_only:
        # The main BT intentionally consumes local cache only. Fetching lives in
        # cot_socrata_fetcher.py so verdict runs are reproducible.
        raise ValueError("s3_pair_pool_fdr.py reads cache only; run cot_socrata_fetcher.py first")

    trade_map: dict[str, pd.DataFrame] = {}
    cot_map: dict[str, pd.DataFrame] = {}
    price_map: dict[str, pd.DataFrame] = {}
    pair_rows: list[dict[str, Any]] = []
    yearly: dict[str, list[dict[str, Any]]] = {}
    boot: dict[str, dict[str, Any]] = {}
    sanity: dict[str, list[dict[str, Any]]] = {}
    sensitivity_off: dict[str, dict[str, Any]] = {}
    flags: dict[str, list[dict[str, Any]]] = {}

    for pair in pairs:
        cot = load_cot(cache_file(paths.cot_cache, pair))
        prices = load_prices(cache_file(paths.price_cache, pair))
        cot_map[pair] = cot
        price_map[pair] = prices
        trades = build_trades(pair, cot, prices, exclude_events=True)
        trade_map[pair] = trades
        pair_rows.append(pair_metrics(pair, trades))
        yearly[pair] = year_by_year(trades)
        flags[pair] = regime_flags(yearly[pair])
        boot[pair] = null_bootstrap(trades, bootstrap_iterations)
        sanity[pair] = _json_records(trades.tail(10))
        sensitivity_off[pair] = pair_metrics(pair, build_trades(pair, cot, prices, exclude_events=False))

    bh_rows = benjamini_hochberg(pair_rows, q=0.10)
    bh_sig = [row["pair"] for row in bh_rows if row["bh_significant"]]
    b_band = [row["pair"] for row in bh_rows if row["band"] in {"A", "B"}]
    portfolio = portfolio_metrics(bh_sig, trade_map)
    usd_metrics = next((row for row in pair_rows if row["pair"] == "USDJPY"), None)
    wave1 = wave1_regression_status(usd_metrics) if usd_metrics else {"pass": False}
    boot_ok = all(boot[pair]["pass"] for pair in bh_sig) if bh_sig else False
    scenario = decide_scenario(bh_sig, b_band)

    result: dict[str, Any] = {
        "status": "ok",
        "scenario": scenario,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pairs": pairs,
        "pair_metrics": bh_rows,
        "bh_fdr_significant_pairs": bh_sig,
        "matrix_b_or_better_pairs": b_band,
        "portfolio": portfolio,
        "correlation_matrix": correlation_matrix(trade_map),
        "year_by_year": yearly,
        "regime_concentration_flags": flags,
        "null_bootstrap": boot,
        "null_bootstrap_pass": boot_ok,
        "wave1_usdjpy_regression": wave1,
        "sanity_samples": sanity,
        "sensitivity_exclude_events_off": sensitivity_off,
    }
    if scenario == "C" and "USDJPY" in cot_map:
        result["alternative_extreme_decile"] = extreme_decile_sanity("USDJPY", cot_map["USDJPY"], price_map["USDJPY"])
    return result


def decide_scenario(bh_sig: list[str], b_band: list[str]) -> str:
    passing = sorted(set(bh_sig).intersection(b_band))
    if len(passing) >= 2:
        return "A"
    if passing == ["USDJPY"]:
        return "A'"
    if passing or bh_sig or b_band:
        return "B"
    return "C"


def _json_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    clean = df.copy()
    for col in clean.columns:
        if pd.api.types.is_datetime64_any_dtype(clean[col]):
            clean[col] = clean[col].dt.strftime("%Y-%m-%d")
    return clean.to_dict(orient="records")


def phase1_commands() -> list[str]:
    return [
        "python3 tools/bt/cot_socrata_fetcher.py --pairs USDJPY,USDCAD,USDCHF,GBPUSD,EURUSD,NZDUSD --since 2014-01-07 --until 2026-04-28 --out tools/bt/cot_cache/",
        "python3 tools/bt/cot_socrata_fetcher.py --download-yfinance --pairs USDJPY,USDCAD,USDCHF,GBPUSD,EURUSD,NZDUSD --since 2014-01-01 --until 2026-05-01 --out tools/bt/price_cache/",
    ]


def write_outputs(result: dict[str, Any], *, json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(_json_safe(result), indent=2, sort_keys=True) + "\n")
    md_path.write_text(render_markdown(result))


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, float):
        return None if not math.isfinite(value) else value
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# S3 Pair-Pool FDR BT 2026-05-03",
        "",
        "## Verdict",
        f"- Scenario: {result.get('scenario')}",
        f"- Status: {result.get('status')}",
    ]
    if result.get("status") == "Insufficient(cache_missing)":
        lines += [
            f"- Missing COT cache: {', '.join(result['missing_cache'].get('cot', [])) or 'none'}",
            f"- Missing price cache: {', '.join(result['missing_cache'].get('price', [])) or 'none'}",
            "- Recommendation: Phase 1 cache preparation required before statistical verdict.",
            "",
            "## Phase 1 Commands",
        ]
        lines += [f"```bash\n{cmd}\n```" for cmd in result.get("phase1_commands", [])]
        return "\n".join(lines) + "\n"

    portfolio = result["portfolio"]
    lines += [
        f"- BH FDR-significant pairs: {', '.join(result['bh_fdr_significant_pairs']) or 'none'}",
        f"- Matrix v1 B 帯通過 pairs: {', '.join(result['matrix_b_or_better_pairs']) or 'none'}",
        f"- Portfolio Sharpe: {_fmt(portfolio.get('portfolio_sharpe'))}",
        f"- Diversification ratio: {_fmt(portfolio.get('diversification_ratio'))}",
        f"- Wave 1 USDJPY regression: {'PASS' if result['wave1_usdjpy_regression'].get('pass') else 'FAIL'}",
        f"- Null bootstrap: {'PASS' if result.get('null_bootstrap_pass') else 'FAIL'}",
        "",
        "## Pair Matrix",
        "| Pair | N | WR | Wilson lo | PF | IS PF | OOS PF | Sharpe | Kelly | p | BH q | BH sig | Band |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---|",
    ]
    for row in result["pair_metrics"]:
        lines.append(
            "| {pair} | {n} | {wr} | {wilson_lo} | {pf} | {is_pf} | {oos_pf} | {sharpe} | {kelly} | {p_value} | {bh_q_value} | {sig} | {band} |".format(
                pair=row["pair"],
                n=row["n"],
                wr=_fmt(row["wr"]),
                wilson_lo=_fmt(row["wilson_lo"]),
                pf=_fmt(row["pf"]),
                is_pf=_fmt(row["is_pf"]),
                oos_pf=_fmt(row["oos_pf"]),
                sharpe=_fmt(row["sharpe"]),
                kelly=_fmt(row["kelly"]),
                p_value=_fmt(row["p_value"]),
                bh_q_value=_fmt(row["bh_q_value"]),
                sig="Y" if row["bh_significant"] else "N",
                band=row["band"],
            )
        )
    lines += ["", "## Correlation Matrix", "```json", json.dumps(_json_safe(result["correlation_matrix"]), indent=2, sort_keys=True), "```"]
    lines += ["", "## Null Bootstrap", "```json", json.dumps(_json_safe(result["null_bootstrap"]), indent=2, sort_keys=True), "```"]
    lines += ["", "## Year By Year / Regime Flags", "```json", json.dumps(_json_safe({"year_by_year": result["year_by_year"], "flags": result["regime_concentration_flags"]}), indent=2, sort_keys=True), "```"]
    lines += ["", "## Sanity Samples", "```json", json.dumps(_json_safe(result["sanity_samples"]), indent=2, sort_keys=True), "```"]
    if "alternative_extreme_decile" in result:
        lines += ["", "## Alternative Extreme Decile Sanity", "```json", json.dumps(_json_safe(result["alternative_extreme_decile"]), indent=2, sort_keys=True), "```"]
    return "\n".join(lines) + "\n"


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "NA"
    return f"{number:.3f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", default=",".join(PAIR_POOL))
    parser.add_argument("--cot-cache", default="tools/bt/cot_cache")
    parser.add_argument("--price-cache", default="tools/bt/price_cache")
    parser.add_argument("--use-cache-only", action="store_true")
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    parser.add_argument("--json-out", default="knowledge-base/raw/bt-results/s3-pair-pool-fdr-2026-05-03.json")
    parser.add_argument("--md-out", default="knowledge-base/raw/bt-results/s3-pair-pool-fdr-2026-05-03.md")
    args = parser.parse_args()

    result = run_backtest(
        pairs=parse_pairs(args.pairs),
        cot_cache=Path(args.cot_cache),
        price_cache=Path(args.price_cache),
        use_cache_only=args.use_cache_only,
        bootstrap_iterations=args.bootstrap_iterations,
    )
    write_outputs(result, json_path=Path(args.json_out), md_path=Path(args.md_out))
    print(render_markdown(result))
    return 2 if result.get("status") == "Insufficient(cache_missing)" else 0


if __name__ == "__main__":
    raise SystemExit(main())
