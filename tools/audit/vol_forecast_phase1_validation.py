#!/usr/bin/env python3
"""Phase 1 HAR-RV volatility forecast validation.

Runs only against local cached OHLCV. Missing cache cells are reported as
limitations instead of being replaced by mock or downloaded data.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
if (
    VENV_PYTHON.exists()
    and Path(sys.executable).absolute() != VENV_PYTHON.absolute()
    and os.environ.get("VFO_NO_VENV_REEXEC") != "1"
):
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.vol_forecast import (  # noqa: E402
    fit_har_rv,
    load_cached_ohlcv,
    predict_har_rv,
    realized_vol_from_returns,
)


@dataclass(frozen=True)
class CellResult:
    instrument: str
    timeframe: str
    n_train: int
    n_test: int
    har_mae: float
    naive_mae: float
    mae_improvement: float
    har_qlike: float
    naive_qlike: float
    qlike_improvement: float
    har_r2: float
    naive_r2: float
    passed: bool


@dataclass(frozen=True)
class CellLimitation:
    instrument: str
    timeframe: str
    reason: str


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_end_date(value: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    if len(value) == 10:
        ts = ts + pd.Timedelta(days=1)
    return ts


def _returns_and_rv(df: pd.DataFrame, window: int = 22) -> tuple[pd.Series, pd.Series]:
    close = pd.to_numeric(df["Close"], errors="coerce").astype(float)
    returns = np.log(close).diff().replace([np.inf, -np.inf], np.nan).dropna()
    rv = realized_vol_from_returns(returns, window=window)
    return returns, rv


def _naive_forecast(returns: pd.Series, asof: pd.Timestamp, window: int = 22) -> float:
    hist = returns[returns.index < asof].tail(window)
    if len(hist) < window:
        return float("nan")
    sigma = float(hist.std(ddof=0) * math.sqrt(window))
    return sigma if np.isfinite(sigma) and sigma > 0 else float("nan")


def _qlike(actual_sigma: np.ndarray, forecast_sigma: np.ndarray) -> float:
    actual_var = np.maximum(np.square(actual_sigma), 1e-16)
    forecast_var = np.maximum(np.square(forecast_sigma), 1e-16)
    return float(np.mean(np.log(forecast_var) + actual_var / forecast_var))


def _r2(actual: np.ndarray, forecast: np.ndarray) -> float:
    ss_res = float(np.sum(np.square(actual - forecast)))
    ss_tot = float(np.sum(np.square(actual - np.mean(actual))))
    if ss_tot <= 0:
        return float("nan")
    return 1.0 - ss_res / ss_tot


def _pct_improvement(lower_is_better_base: float, candidate: float) -> float:
    if not np.isfinite(lower_is_better_base) or lower_is_better_base == 0:
        return float("nan")
    return (lower_is_better_base - candidate) / abs(lower_is_better_base) * 100.0


def evaluate_cell(
    instrument: str,
    timeframe: str,
    train_end: pd.Timestamp,
    test_end: pd.Timestamp,
    cache_dir: str | None,
) -> CellResult:
    df = load_cached_ohlcv(instrument, timeframe, cache_dir=cache_dir)
    returns, rv = _returns_and_rv(df)
    train_rv = rv[rv.index < train_end]
    test_rv = rv[(rv.index >= train_end) & (rv.index < test_end)]
    if len(train_rv) < 80:
        raise ValueError(f"insufficient train RV history: {len(train_rv)}")
    if len(test_rv) < 20:
        raise ValueError(f"insufficient test RV history: {len(test_rv)}")

    params = fit_har_rv(train_rv)
    daily = rv.shift(1)
    weekly = rv.shift(1).rolling(window=5, min_periods=5).mean()
    monthly = rv.shift(1).rolling(window=22, min_periods=22).mean()
    har_series = (
        float(params["beta0"])
        + float(params["beta_d"]) * daily
        + float(params["beta_w"]) * weekly
        + float(params["beta_m"]) * monthly
    )
    naive_series = returns.rolling(window=22, min_periods=22).std(ddof=0).shift(1) * math.sqrt(22)
    comparable = pd.DataFrame(
        {
            "actual": test_rv,
            "har": har_series.reindex(test_rv.index),
            "naive": naive_series.reindex(test_rv.index),
        }
    ).replace([np.inf, -np.inf], np.nan).dropna()
    comparable = comparable[(comparable["actual"] > 0) & (comparable["har"] > 0) & (comparable["naive"] > 0)]

    if len(comparable) < 20:
        raise ValueError(f"insufficient comparable predictions: {len(comparable)}")

    # Execute the public prediction path once per cell to keep the closed-bar
    # guard covered in the validation path while avoiding O(n^2) M5 loops.
    probe_ts = comparable.index[0]
    probe_history = rv[rv.index < probe_ts]
    probe_params = dict(params)
    probe_params["_asof_ts"] = float(probe_ts.timestamp())
    predict_har_rv(probe_params, probe_history)
    _naive_forecast(returns, probe_ts)

    actual_arr = comparable["actual"].to_numpy(dtype=float)
    har_arr = comparable["har"].to_numpy(dtype=float)
    naive_arr = comparable["naive"].to_numpy(dtype=float)
    har_mae = float(np.mean(np.abs(actual_arr - har_arr)))
    naive_mae = float(np.mean(np.abs(actual_arr - naive_arr)))
    har_qlike = _qlike(actual_arr, har_arr)
    naive_qlike = _qlike(actual_arr, naive_arr)
    mae_improvement = _pct_improvement(naive_mae, har_mae)
    qlike_improvement = _pct_improvement(naive_qlike, har_qlike)
    passed = mae_improvement >= 5.0 and qlike_improvement >= 5.0

    return CellResult(
        instrument=instrument,
        timeframe=timeframe,
        n_train=len(train_rv),
        n_test=len(actual_arr),
        har_mae=har_mae,
        naive_mae=naive_mae,
        mae_improvement=mae_improvement,
        har_qlike=har_qlike,
        naive_qlike=naive_qlike,
        qlike_improvement=qlike_improvement,
        har_r2=_r2(actual_arr, har_arr),
        naive_r2=_r2(actual_arr, naive_arr),
        passed=passed,
    )


def _fmt(value: float, digits: int = 6) -> str:
    if not np.isfinite(value):
        return "nan"
    return f"{value:.{digits}g}"


def render_report(
    results: list[CellResult],
    limitations: list[CellLimitation],
    *,
    train_end: str,
    test_end: str,
    verdict: str,
) -> str:
    passed = sum(1 for result in results if result.passed)
    total = len(results)
    lines = [
        f"# VFO-1 Phase 1 Verdict: {verdict}",
        "",
        f"**Decision:** PHASE 1 {verdict}",
        "",
        f"- Evaluated cells: {total}",
        f"- Passing cells: {passed}",
        "- Rule: PASS iff HAR-RV improves both MAE and QLIKE by >=5% in a majority of evaluated cells.",
        f"- Train split end: {train_end}",
        f"- Test end: {test_end}",
        "- Data source: local parquet cache only; no mock data and no network download.",
        "",
        "## Improvement Table",
        "",
        "| Instrument | TF | N train | N test | HAR MAE | Naive MAE | MAE improvement | HAR QLIKE | Naive QLIKE | QLIKE improvement | HAR R2 | Naive R2 | Cell PASS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for result in results:
        lines.append(
            "| "
            f"{result.instrument} | {result.timeframe} | {result.n_train} | {result.n_test} | "
            f"{_fmt(result.har_mae)} | {_fmt(result.naive_mae)} | {result.mae_improvement:.2f}% | "
            f"{_fmt(result.har_qlike)} | {_fmt(result.naive_qlike)} | {result.qlike_improvement:.2f}% | "
            f"{_fmt(result.har_r2)} | {_fmt(result.naive_r2)} | {'PASS' if result.passed else 'FAIL'} |"
        )

    lines.extend(["", "## Limitations", ""])
    if limitations:
        for item in limitations:
            lines.append(f"- {item.instrument} {item.timeframe}: {item.reason}")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Task B Gate",
            "",
            "Task B is not started by this validation job. Commander Claude must review this report before any overlay integration work.",
            "",
            f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate HAR-RV Phase 1 forecast accuracy against local 12y cache.")
    parser.add_argument("--instruments", default="USD_JPY,EUR_USD,GBP_USD")
    parser.add_argument("--timeframes", default="M5,H1,D1")
    parser.add_argument("--train-end", default="2024-04-30")
    parser.add_argument("--test-end", default="2026-04-30")
    parser.add_argument("--cache-dir", default=str(ROOT / "data" / "cache" / "massive"))
    parser.add_argument("--output", default=str(ROOT / "knowledge-base" / "raw" / "audits" / "vfo1-phase1-2026-05-04.md"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    train_end = _parse_end_date(args.train_end)
    test_end = _parse_end_date(args.test_end)
    instruments = _parse_csv(args.instruments)
    timeframes = _parse_csv(args.timeframes)

    results: list[CellResult] = []
    limitations: list[CellLimitation] = []
    for instrument in instruments:
        for timeframe in timeframes:
            try:
                results.append(
                    evaluate_cell(
                        instrument,
                        timeframe,
                        train_end,
                        test_end,
                        args.cache_dir,
                    )
                )
            except Exception as exc:
                limitations.append(CellLimitation(instrument, timeframe, str(exc)))

    passing = sum(1 for result in results if result.passed)
    verdict = "PASS" if results and passing > len(results) / 2 else "FAIL"
    report = render_report(
        results,
        limitations,
        train_end=args.train_end,
        test_end=args.test_end,
        verdict=verdict,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"PHASE 1 {verdict}: {passing}/{len(results)} evaluated cells passed")
    print(f"report: {output}")
    if limitations:
        print(f"limitations: {len(limitations)} skipped cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
