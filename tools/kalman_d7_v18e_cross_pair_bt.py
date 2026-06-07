#!/usr/bin/env python3
"""Kalman D7 v18e JPY cross-pair MASSIVE BT orchestration."""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.kalman_d7_v18e_python_port import load_ohlc, run_v18e_backtest


REPORT_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
OUT_STEM = f"kalman-d7-v18e-jpy-cross-pair-12y-bt-{REPORT_DATE}"
OUT_JSON = ROOT / "raw" / "bt-results" / f"{OUT_STEM}.json"
OUT_MD = ROOT / "raw" / "bt-results" / f"{OUT_STEM}.md"
TARGET_YEARS = 12.0
MIN_ADMISSIBLE_YEARS = 10.8
ALPHA_FAMILY = 0.05
PRE_REG_M = 4
STAGE0 = {
    "AUDJPY": {"n": 72, "wr": 0.6806, "pf": 1.606, "net_positive": True},
    "GBPJPY": {"n": 128, "wr": 0.6719, "pf": 1.235, "net_positive": True},
    "USDJPY": {"n": 58, "wr": 0.5345, "pf": 1.184, "net_positive": True},
    "EURJPY": {"n": 106, "wr": 0.6509, "pf": 1.039, "net_positive": True},
}


PAIR_INVENTORY = {
    "USDJPY": [
        {"path": "data/cache/massive/USDJPY_M15.parquet", "kind": "requested_native_m15", "resample_5m": False},
        {"path": "data/cache/massive/USD_JPY_15m.parquet", "kind": "alias_native_m15", "resample_5m": False},
        {"path": "data/cache/massive/USD_JPY_5m_2014_2026.parquet", "kind": "massive_5m_resampled_to_m15", "resample_5m": True},
        {"path": "data/cache/massive/USD_JPY_5m.parquet", "kind": "massive_5m_resampled_to_m15", "resample_5m": True},
    ],
    "EURJPY": [
        {"path": "data/cache/massive/EURJPY_M15.parquet", "kind": "requested_native_m15", "resample_5m": False},
        {"path": "data/cache/massive/EUR_JPY_15m.parquet", "kind": "alias_native_m15", "resample_5m": False},
    ],
    "GBPJPY": [
        {"path": "data/cache/massive/GBPJPY_M15.parquet", "kind": "requested_native_m15", "resample_5m": False},
        {"path": "data/cache/massive/GBP_JPY_15m.parquet", "kind": "alias_native_m15", "resample_5m": False},
        {"path": "data/cache/massive/GBP_JPY_5m.parquet", "kind": "massive_5m_resampled_to_m15", "resample_5m": True},
    ],
    "AUDJPY": [
        {"path": "data/cache/massive/AUDJPY_M15.parquet", "kind": "requested_native_m15", "resample_5m": False},
        {"path": "data/cache/massive/AUD_JPY_15m.parquet", "kind": "alias_native_m15", "resample_5m": False},
    ],
}


def _select_source(pair: str) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    checked: list[str] = []
    requested_exists = False
    loaded: list[tuple[pd.DataFrame, dict[str, Any]]] = []
    for candidate in PAIR_INVENTORY[pair]:
        path = ROOT / candidate["path"]
        checked.append(candidate["path"])
        if candidate["kind"] == "requested_native_m15" and path.exists():
            requested_exists = True
        if not path.exists():
            continue
        df = load_ohlc(path, resample_from_5m=bool(candidate["resample_5m"]))
        info = {
            "pair": pair,
            "selected_path": candidate["path"],
            "selected_kind": candidate["kind"],
            "requested_path_exists": requested_exists,
            "checked_paths": checked,
            "rows": int(len(df)),
            "start": df.index[0].isoformat() if len(df) else None,
            "end": df.index[-1].isoformat() if len(df) else None,
            "years": float((df.index[-1] - df.index[0]).days / 365.25) if len(df) > 1 else 0.0,
            "source_note": _source_note(candidate["kind"], requested_exists),
        }
        loaded.append((df, info))
    if loaded:
        def rank(item: tuple[pd.DataFrame, dict[str, Any]]) -> tuple[int, int, float]:
            _, info = item
            coverage_ok = int(info["years"] >= MIN_ADMISSIBLE_YEARS)
            kind_rank = {
                "requested_native_m15": 3,
                "alias_native_m15": 2,
                "massive_5m_resampled_to_m15": 1,
            }.get(info["selected_kind"], 0)
            return (coverage_ok, kind_rank if coverage_ok else 0, info["years"])

        df, info = max(loaded, key=rank)
        info["checked_paths"] = checked
        if info["years"] < MIN_ADMISSIBLE_YEARS:
            info["source_note"] += " Coverage is below the 12y target; pre-reg coverage gate fails."
        return df, info
    return None, {
        "pair": pair,
        "selected_path": None,
        "selected_kind": "missing",
        "requested_path_exists": False,
        "checked_paths": checked,
        "rows": 0,
        "start": None,
        "end": None,
        "years": 0.0,
        "source_note": "No MASSIVE parquet candidate found; pair rejected without substitution.",
    }


def _source_note(kind: str, requested_exists: bool) -> str:
    if kind == "requested_native_m15":
        return "Requested native M15 MASSIVE parquet found."
    if kind == "alias_native_m15":
        return "Requested no-underscore M15 parquet missing; used repo-native underscore M15 MASSIVE alias."
    if kind == "massive_5m_resampled_to_m15":
        return "Requested/native M15 parquet missing; used MASSIVE 5m cache resampled to M15, not Yahoo/OANDA."
    return "Unknown source kind."


def _wfo_three_fold(pair: str, df: pd.DataFrame) -> dict[str, Any]:
    if len(df) < 800:
        return {"folds": [], "all_fold_pf_gt_1": False, "note": "insufficient bars for 3-fold WFO"}
    idx = df.index
    cuts = [0, len(df) // 4, len(df) // 2, (3 * len(df)) // 4, len(df)]
    folds = []
    all_ok = True
    for fold in range(1, 4):
        train_start = idx[0]
        train_end = idx[cuts[fold] - 1]
        test_start = idx[cuts[fold]]
        test_end = idx[cuts[fold + 1] - 1]
        test_df = df.loc[(df.index >= test_start) & (df.index <= test_end)]
        result = run_v18e_backtest(pair, test_df)
        summary = result["summary"]
        pf = float(summary["pf"])
        ok = pf > 1.0
        all_ok = all_ok and ok
        folds.append(
            {
                "fold": fold,
                "train_start": train_start.isoformat(),
                "train_end": train_end.isoformat(),
                "test_start": test_start.isoformat(),
                "test_end": test_end.isoformat(),
                "test_n": summary["n"],
                "test_pf": pf if math.isfinite(pf) else "inf",
                "test_net": summary["net"],
                "pass_pf_gt_1": ok,
            }
        )
    return {"folds": folds, "all_fold_pf_gt_1": all_ok, "note": "expanding train / next-quarter test; fixed parameters, no optimization"}


def _daily_pnl_frame(results: dict[str, Any]) -> pd.DataFrame:
    series = {}
    for pair, payload in results.items():
        daily = payload.get("bt", {}).get("daily_pnl", {})
        if daily:
            series[pair] = pd.Series(daily, dtype=float)
    if not series:
        return pd.DataFrame()
    df = pd.DataFrame(series).sort_index().fillna(0.0)
    return df


def _correlation_adjustment(results: dict[str, Any]) -> dict[str, Any]:
    daily = _daily_pnl_frame(results)
    if daily.empty or daily.shape[1] < 2:
        return {
            "daily_pnl_correlation": {},
            "max_pairwise_corr": None,
            "method": "insufficient daily PnL series",
            "effective_m": PRE_REG_M,
            "alpha_eff": ALPHA_FAMILY / PRE_REG_M,
        }
    corr = daily.corr().fillna(0.0)
    vals = corr.where(~np.eye(corr.shape[0], dtype=bool)).stack()
    max_corr = float(vals.max()) if len(vals) else None
    if max_corr is not None and max_corr > 0.50:
        eigvals = np.linalg.eigvalsh(corr.to_numpy())
        effective_m = float(sum(min(max(x, 0.0), 1.0) for x in eigvals))
        effective_m = max(1.0, min(float(PRE_REG_M), effective_m))
        alpha_eff = 1 - (1 - ALPHA_FAMILY) ** (1 / effective_m)
        method = "max corr > 0.50; Li-Ji eigenvalue effective tests with Sidak alpha"
    else:
        effective_m = float(PRE_REG_M)
        alpha_eff = ALPHA_FAMILY / PRE_REG_M
        method = "max corr <= 0.50; pre-registered Bonferroni m=4"
    return {
        "daily_pnl_correlation": json.loads(corr.round(6).to_json()),
        "max_pairwise_corr": max_corr,
        "method": method,
        "effective_m": effective_m,
        "alpha_eff": alpha_eff,
    }


def _criterion_bool(value: Any) -> str:
    return "PASS" if value else "FAIL"


def _verdict(pair: str, result: dict[str, Any], alpha_eff: float) -> dict[str, Any]:
    source = result["source"]
    if not result.get("bt"):
        return {
            "verdict": "REJECT",
            "criteria": {"data_available": False},
            "justification": "No usable MASSIVE parquet was available.",
        }
    summary = result["bt"]["summary"]
    pvalue = summary["pvalue"]["p_one_sided"]
    stage = STAGE0[pair]
    criteria = {
        "data_available": True,
        "coverage_years_ge_10_8": source["years"] >= MIN_ADMISSIBLE_YEARS,
        "pf_ge_1_20": summary["pf"] >= 1.20,
        "wilson_wr_lower_ge_0_50": summary["wilson95_wr_lower"] >= 0.50,
        "n_ge_100": summary["n"] >= 100,
        "max_dd_le_5pct": summary["max_dd_pct"] <= 5.0,
        "wfo_all_fold_pf_gt_1": result["wfo"]["all_fold_pf_gt_1"],
        "pvalue_lt_alpha_eff": pvalue is not None and pvalue < alpha_eff,
        "catastrophic_net_not_negative": summary["net"] > 0 if stage["net_positive"] else True,
        "catastrophic_wr_drop_le_20pp": (stage["wr"] - summary["wr"]) <= 0.20,
        "catastrophic_pf_not_below_1": summary["pf"] >= 1.0,
    }
    catastrophic_fail = not (
        criteria["catastrophic_net_not_negative"]
        and criteria["catastrophic_wr_drop_le_20pp"]
        and criteria["catastrophic_pf_not_below_1"]
    )
    prereg_pass = all(
        criteria[k]
        for k in [
            "coverage_years_ge_10_8",
            "pf_ge_1_20",
            "wilson_wr_lower_ge_0_50",
            "n_ge_100",
            "max_dd_le_5pct",
            "wfo_all_fold_pf_gt_1",
            "pvalue_lt_alpha_eff",
        ]
    )
    if catastrophic_fail:
        verdict = "REJECT"
    elif prereg_pass:
        verdict = "PASS_SHADOW_PROMOTE"
    elif summary["pf"] >= 1.0 and summary["net"] > 0:
        verdict = "MARGINAL_WATCHLIST"
    else:
        verdict = "REJECT"
    failed = [k for k, ok in criteria.items() if not ok]
    return {
        "verdict": verdict,
        "criteria": criteria,
        "failed": failed,
        "justification": "; ".join(failed) if failed else "all pre-registered criteria passed",
    }


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "NA"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    try:
        x = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isinf(x):
        return "inf"
    return f"{x:.{digits}f}"


def _summary_table(results: dict[str, Any]) -> str:
    rows = [
        "| Pair | Source | Years | N | WR | W95 LB | PF | p(logPF) | Net JPY | MaxDD | Sharpe | Avg Win | Avg Loss | Avg Bars |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for pair, result in results.items():
        if not result.get("bt"):
            rows.append(f"| {pair} | missing | 0.00 | 0 | NA | NA | NA | NA | NA | NA | NA | NA | NA | NA |")
            continue
        s = result["bt"]["summary"]
        rows.append(
            "| {pair} | {source} | {years:.2f} | {n} | {wr:.2%} | {wlo:.2%} | {pf} | {pval} | {net:.2f} | {dd:.2f}% | {sharpe:.2f} | {avgw:.2f} | {avgl:.2f} | {avgb:.1f} |".format(
                pair=pair,
                source=result["source"]["selected_kind"],
                years=result["source"]["years"],
                n=s["n"],
                wr=s["wr"],
                wlo=s["wilson95_wr_lower"],
                pf=_fmt(s["pf"], 3),
                pval=_fmt(s["pvalue"]["p_one_sided"], 4),
                net=s["net"],
                dd=s["max_dd_pct"],
                sharpe=s["sharpe_daily"],
                avgw=s["avg_win"],
                avgl=s["avg_loss"],
                avgb=s["avg_bars_in_trade"],
            )
        )
    return "\n".join(rows)


def _wfo_section(results: dict[str, Any]) -> str:
    lines = []
    for pair, result in results.items():
        lines.append(f"### {pair}")
        lines.append("")
        if not result.get("bt"):
            lines.append("No BT: MASSIVE parquet unavailable.")
            lines.append("")
            continue
        lines.append(f"Method: {result['wfo']['note']}")
        lines.append("")
        lines.append("| Fold | Train | Test | N | PF | Net | PF>1 |")
        lines.append("|---:|---|---|---:|---:|---:|---|")
        for f in result["wfo"]["folds"]:
            lines.append(
                f"| {f['fold']} | {f['train_start'][:10]} -> {f['train_end'][:10]} | "
                f"{f['test_start'][:10]} -> {f['test_end'][:10]} | {f['test_n']} | "
                f"{_fmt(f['test_pf'], 3)} | {f['test_net']:.2f} | {_criterion_bool(f['pass_pf_gt_1'])} |"
            )
        lines.append(f"\nAll-fold PF > 1.0: {_criterion_bool(result['wfo']['all_fold_pf_gt_1'])}")
        lines.append("")
    return "\n".join(lines)


def _corr_section(corr: dict[str, Any]) -> str:
    matrix = corr["daily_pnl_correlation"]
    if not matrix:
        return "Insufficient daily PnL series for pairwise correlation."
    pairs = list(matrix.keys())
    lines = ["| Pair | " + " | ".join(pairs) + " |", "|---|" + "|".join(["---:"] * len(pairs)) + "|"]
    for r in pairs:
        vals = []
        for c in pairs:
            vals.append(_fmt(matrix[r].get(c), 3))
        lines.append(f"| {r} | " + " | ".join(vals) + " |")
    lines.append("")
    lines.append(
        f"Max pairwise corr={_fmt(corr['max_pairwise_corr'], 3)}. "
        f"Adjustment: {corr['method']}. effective_m={_fmt(corr['effective_m'], 3)}, "
        f"alpha_eff={_fmt(corr['alpha_eff'], 5)}."
    )
    return "\n".join(lines)


def _verdict_section(results: dict[str, Any]) -> str:
    lines = []
    for pair, result in results.items():
        v = result["verdict"]
        lines.append(f"### {pair}: {v['verdict']}")
        lines.append("")
        lines.append(f"Source: {result['source']['source_note']}")
        if result.get("bt"):
            s = result["bt"]["summary"]
            lines.append(
                f"Core stats: PF={_fmt(s['pf'], 3)}, WR={s['wr']:.2%}, "
                f"Wilson95 LB={s['wilson95_wr_lower']:.2%}, N={s['n']}, "
                f"Net={s['net']:.2f}, MaxDD={s['max_dd_pct']:.2f}%."
            )
        lines.append(f"Failed criteria: {v.get('justification', 'NA')}.")
        lines.append("")
    return "\n".join(lines)


def _recommendation(results: dict[str, Any]) -> str:
    promoted = [p for p, r in results.items() if r["verdict"]["verdict"] == "PASS_SHADOW_PROMOTE"]
    marginal = [p for p, r in results.items() if r["verdict"]["verdict"] == "MARGINAL_WATCHLIST"]
    rejected = [p for p, r in results.items() if r["verdict"]["verdict"] == "REJECT"]
    if promoted:
        lead = f"Shadow promote candidates: {', '.join(promoted)}."
    else:
        lead = "No pair qualifies for PASS_SHADOW_PROMOTE under the locked criteria."
    return (
        f"{lead} Marginal watchlist: {', '.join(marginal) if marginal else 'none'}. "
        f"Rejected: {', '.join(rejected) if rejected else 'none'}. "
        "LIVE pair extension should wait for Stage 1 shadow evidence (N>=30 per pair) and a rerun with native 12y M15 inventory for any pair currently using partial or resampled candles."
    )


def _write_markdown(payload: dict[str, Any]) -> None:
    results = payload["results"]
    corr = payload["correlation_adjustment"]
    text = f"""# Kalman D7 v18e JPY Cross-Pair MASSIVE 12y BT

Generated: {datetime.now(timezone.utc).isoformat()}

## 1. Replication of v18e Pine Logic in Python

Pseudocode:

```text
for each M15 bar:
  ema25 = EMA(close, 25), ema75 = EMA(close, 75), ema200 = EMA(close, 200)
  atr = Wilder RMA(true_range, 14)
  rsi = Wilder RSI(close, 14)
  atr_p20/p80 = rolling percentile(atr, 200, 20/80)
  perfect_up = ema25 > ema75 > ema200 and close > ema25
  po_up_start = perfect_up and not perfect_up[1]
  entry_signal = po_up_start
    and (close - ema200) / atr < 3.0
    and (ema25 - ema200) / atr < 3.0
    and atr_p20 <= atr < atr_p80
    and rsi < 70
    and UTC hour in [0,12) or [16,21)
  enter long on next bar open with 10% equity, 1 tick adverse slippage
  place initial stop entry - 2.0*ATR
  activate trailing after entry + round(1.0*ATR/mintick)
  trailing stop = highest high since activation - round(0.5*ATR/mintick)
```

Key discrepancies vs Pine / TV:

- The canonical Pine file `/Users/jg-n-012/test/kalman_d7_strategies/v18e_05ATR_trail.pine` was not present in this container, so this port uses the locked rule text from the task.
- EMA uses pandas `ewm(span, adjust=False, min_periods=period)`, matching the usual recursive EMA form but not TV warmup bit-for-bit.
- ATR/RSI use Wilder RMA via `ewm(alpha=1/length, adjust=False)`, the closest deterministic match to `ta.atr`/`ta.rsi`.
- ATR percentile uses pandas rolling quantile. Pine percentile interpolation may differ by one tick around the P20/P80 boundary.
- TradingView intrabar trailing path is not observable from OHLC. The simulator checks stops before same-bar new trail activation, then permits same-bar trail activation and hit if high/low both cross.
- TV trade timestamp replication could not be measured because no exported TV trade list was available in the repo.
- Data-source discrepancy: requested no-underscore M15 paths are absent. The runner records whether it used a repo-native underscore M15 alias or a MASSIVE 5m-to-M15 resample.

## 2. Per-Pair BT Summary

{_summary_table(results)}

## 3. WFO 3-Fold Per Pair

{_wfo_section(results)}

## 4. Pairwise PnL Correlation Matrix + Effective Bonferroni

{_corr_section(corr)}

## 5. Per-Pair Pre-Reg Verdict

{_verdict_section(results)}

## 6. Recommendation

{_recommendation(results)}
"""
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(text, encoding="utf-8")


def main() -> int:
    results: dict[str, Any] = {}
    for pair in ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY"]:
        df, source = _select_source(pair)
        result: dict[str, Any] = {"source": source}
        if df is not None and len(df) > 0:
            bt = run_v18e_backtest(pair, df)
            result["bt"] = bt
            result["wfo"] = _wfo_three_fold(pair, df)
        else:
            result["bt"] = None
            result["wfo"] = {"folds": [], "all_fold_pf_gt_1": False, "note": "no data"}
        results[pair] = result

    corr = _correlation_adjustment(results)
    for pair, result in results.items():
        result["verdict"] = _verdict(pair, result, float(corr["alpha_eff"]))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_date": REPORT_DATE,
        "pre_registration": {
            "target_years": TARGET_YEARS,
            "min_admissible_years": MIN_ADMISSIBLE_YEARS,
            "alpha_family": ALPHA_FAMILY,
            "m": PRE_REG_M,
        },
        "results": results,
        "correlation_adjustment": corr,
        "outputs": {"json": str(OUT_JSON.relative_to(ROOT)), "markdown": str(OUT_MD.relative_to(ROOT))},
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    _write_markdown(payload)
    print(json.dumps(payload["outputs"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
