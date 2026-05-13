#!/usr/bin/env python3
"""Phase B2.5 composite dow_regime x v2_regime retrospective analysis.

This script is analysis-only. It reads the frozen Phase B2.5 trade log and
local MASSIVE parquet caches, calls the existing v2 classifier, and writes
summary artifacts under reports/composite_cell_analysis.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.regime_classifier import (  # noqa: E402
    REGIME_MODERATE_TREND,
    REGIME_NO_GO,
    classify_15m,
    hurst_rs,
)

B2_DIR = ROOT / "reports" / "regime_gate_phase_b2"
TRADE_LOG = B2_DIR / "trade_log_tagged.csv"
PROPOSALS = B2_DIR / "shadow_proposals.csv"
CACHE_DIR = ROOT / "data" / "cache" / "massive"
OUT_DIR = ROOT / "reports" / "composite_cell_analysis"

DOW_REGIMES = ("TRENDING", "RANGING", "CHOP")
V2_REGIMES = (REGIME_MODERATE_TREND, REGIME_NO_GO)
MIN_CELL_N = 30
ALPHA = 0.05


def _pair_cache_key(pair: str) -> str:
    value = str(pair).upper().replace("/", "_").replace("-", "_")
    if value.endswith("=X"):
        value = value[:-2]
    value = value.replace("_", "")
    if len(value) == 6:
        return f"{value[:3]}_{value[3:]}"
    return value


def _parse_time(value: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={c: c.lower() for c in df.columns})
    required = {"high", "low", "close"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"missing OHLC columns: {','.join(sorted(missing))}")
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, utc=True)
    elif out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def _wilder_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_smoothed = plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    minus_smoothed = minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_smoothed / atr.replace(0, pd.NA)
    minus_di = 100 * minus_smoothed / atr.replace(0, pd.NA)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _prepare_m15(pair: str) -> pd.DataFrame:
    path = CACHE_DIR / f"{_pair_cache_key(pair)}_15m.parquet"
    if not path.exists():
        raise FileNotFoundError(f"missing MASSIVE 15m cache: {path}")
    df = _normalize_ohlc(pd.read_parquet(path))
    close = df["close"].astype(float)
    df["adx"] = _wilder_adx(df, 14)
    df["ema21"] = close.ewm(span=21, adjust=False).mean()
    df["ema_slope"] = df["ema21"] - df["ema21"].shift(3)
    df["hurst_64"] = close.rolling(64).apply(lambda x: hurst_rs(x.tolist()), raw=False)
    return df


def _feature_at(cache: dict[str, pd.DataFrame], pair: str, ts: pd.Timestamp) -> dict | None:
    if pair not in cache:
        cache[pair] = _prepare_m15(pair)
    window = cache[pair][cache[pair].index <= ts]
    if window.empty:
        return None
    row = window.iloc[-1]
    return {
        "adx": float(row.get("adx", 0.0) or 0.0),
        "ema_slope": float(row.get("ema_slope", 0.0) or 0.0),
        "hurst_64": float(row.get("hurst_64", 0.5) or 0.5),
    }


def _pf(pnls: Iterable[float]) -> float:
    values = [float(v) for v in pnls]
    gross_win = sum(v for v in values if v > 0)
    gross_loss = -sum(v for v in values if v < 0)
    if gross_loss == 0:
        return float("inf") if gross_win > 0 else 0.0
    return gross_win / gross_loss


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return (centre - margin) / den


def _kelly(pnls: Iterable[float]) -> float:
    values = [float(v) for v in pnls]
    n = len(values)
    if n == 0:
        return 0.0
    wins = [v for v in values if v > 0]
    losses = [-v for v in values if v < 0]
    if not wins:
        return -1.0
    if not losses:
        return 1.0
    p = len(wins) / n
    q = 1.0 - p
    b = (sum(wins) / len(wins)) / (sum(losses) / len(losses))
    if b <= 0:
        return 0.0
    return p - q / b


def _stats(rows: pd.DataFrame) -> dict[str, int | float | str]:
    pnls = [float(v) for v in rows["pnl_m"].tolist()]
    n = len(pnls)
    wins = sum(1 for v in pnls if v > 0)
    pf = _pf(pnls)
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 6) if n else 0.0,
        "EV_pip": round(sum(pnls) / n, 6) if n else 0.0,
        "PF": "inf" if math.isinf(pf) else round(pf, 6),
        "Wilson_lo": round(_wilson_lower(wins, n), 6),
        "Kelly": round(_kelly(pnls), 6),
    }


def _cell_stats(df: pd.DataFrame, group_cols: list[str], full_grid: list[tuple] | None = None) -> pd.DataFrame:
    rows: list[dict] = []
    if full_grid:
        for key in full_grid:
            mask = pd.Series(True, index=df.index)
            for col, value in zip(group_cols, key):
                mask &= df[col] == value
            record = dict(zip(group_cols, key))
            record.update(_stats(df[mask]))
            rows.append(record)
    else:
        for key, group in df.groupby(group_cols, dropna=False):
            if not isinstance(key, tuple):
                key = (key,)
            record = dict(zip(group_cols, key))
            record.update(_stats(group))
            rows.append(record)
    return pd.DataFrame(rows)


def tag_trades() -> pd.DataFrame:
    df = pd.read_csv(TRADE_LOG)
    if "regime" not in df.columns:
        raise ValueError("trade_log_tagged.csv must contain regime column")
    cache: dict[str, pd.DataFrame] = {}
    rows: list[dict] = []
    for row in df.to_dict("records"):
        pair = str(row["pair"])
        ts = _parse_time(str(row["entry_time"]))
        features = _feature_at(cache, pair, ts)
        out = dict(row)
        out["dow_regime"] = out.pop("regime")
        out["v2_regime"] = classify_15m(features)
        rows.append(out)
    return pd.DataFrame(rows)


def write_crosstabs(tagged: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    full_grid = [(dow, v2) for dow in DOW_REGIMES for v2 in V2_REGIMES]
    global_df = _cell_stats(tagged, ["dow_regime", "v2_regime"], full_grid)
    global_df.to_csv(OUT_DIR / "crosstab_global.csv", index=False)

    by_strategy = _cell_stats(tagged, ["entry_type", "dow_regime", "v2_regime"])
    by_strategy = by_strategy.sort_values(["entry_type", "dow_regime", "v2_regime"])
    by_strategy.to_csv(OUT_DIR / "crosstab_by_strategy.csv", index=False)

    top_entries = tagged["entry_type"].value_counts().head(10).index.tolist()
    top_rows: list[dict] = []
    for entry_type in top_entries:
        subset = tagged[tagged["entry_type"] == entry_type]
        for dow, v2 in full_grid:
            cell = subset[(subset["dow_regime"] == dow) & (subset["v2_regime"] == v2)]
            record = {"entry_type": entry_type, "baseline_N": len(subset), "dow_regime": dow, "v2_regime": v2}
            record.update(_stats(cell))
            top_rows.append(record)
    top_df = pd.DataFrame(top_rows)
    top_df.to_csv(OUT_DIR / "crosstab_top_strategies.csv", index=False)
    return global_df, by_strategy, top_df


def write_proposal_composite(tagged: pd.DataFrame) -> pd.DataFrame:
    proposals = pd.read_csv(PROPOSALS)
    rows: list[dict] = []
    for prop in proposals.to_dict("records"):
        subset = tagged[
            (tagged["entry_type"] == prop["entry_type"])
            & (tagged["dow_regime"] == prop["gate"])
        ]
        for v2 in V2_REGIMES:
            cell = subset[subset["v2_regime"] == v2]
            stats = _stats(cell)
            rows.append(
                {
                    "proposal": prop["proposal"],
                    "entry_type": prop["entry_type"],
                    "dow_regime": prop["gate"],
                    "v2_regime": v2,
                    "proposal_N": int(prop["N"]),
                    "proposal_WR": round(float(prop["WR"]), 6),
                    "proposal_EV_pip": round(float(prop["EV_pip"]), 6),
                    "proposal_PF": round(float(prop["PF"]), 6),
                    "proposal_Wilson_lo": round(float(prop["Wilson_lo"]), 6),
                    "share_of_proposal_N": round(stats["N"] / int(prop["N"]), 6) if int(prop["N"]) else 0.0,
                    **stats,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "17_proposals_composite.csv", index=False)
    return out


def write_bonferroni(by_strategy: pd.DataFrame) -> pd.DataFrame:
    eligible = by_strategy[by_strategy["N"] >= MIN_CELL_N].copy()
    m_eff = len(eligible)
    alpha_prime = ALPHA / m_eff if m_eff else 0.0
    rows: list[dict] = []
    for row in eligible.to_dict("records"):
        p_value = binomtest(int(row["wins"]), int(row["N"]), p=0.5, alternative="greater").pvalue
        rows.append(
            {
                "entry_type": row["entry_type"],
                "dow_regime": row["dow_regime"],
                "v2_regime": row["v2_regime"],
                "N": int(row["N"]),
                "wins": int(row["wins"]),
                "WR": row["WR"],
                "EV_pip": row["EV_pip"],
                "PF": row["PF"],
                "Wilson_lo": row["Wilson_lo"],
                "Kelly": row["Kelly"],
                "m_eff": m_eff,
                "alpha_prime": alpha_prime,
                "p_value": p_value,
                "bonferroni_pass": bool(p_value <= alpha_prime and float(row["EV_pip"]) > 0),
            }
        )
    out = pd.DataFrame(rows).sort_values(["bonferroni_pass", "p_value"], ascending=[False, True])
    out.to_csv(OUT_DIR / "bonferroni_evaluation.csv", index=False)
    return out


def _loo_group_prediction(df: pd.DataFrame, group_cols: list[str]) -> pd.Series:
    y = (df["pnl_m"].astype(float) > 0).astype(int)
    grouped = pd.DataFrame({"y": y}).join(df[group_cols])
    group_sum = grouped.groupby(group_cols, dropna=False)["y"].transform("sum")
    group_n = grouped.groupby(group_cols, dropna=False)["y"].transform("count")
    global_sum = y.sum()
    global_n = len(y)
    pred = (group_sum - y + 1.0) / (group_n - 1.0 + 2.0)
    fallback = (global_sum - y + 1.0) / (global_n - 1.0 + 2.0)
    return pred.where(group_n > 1, fallback).clip(1e-6, 1 - 1e-6)


def write_prediction_power(tagged: pd.DataFrame) -> pd.DataFrame:
    y = (tagged["pnl_m"].astype(float) > 0).astype(int)
    specs = [
        ("dow_only", ["dow_regime"]),
        ("v2_only", ["v2_regime"]),
        ("composite", ["dow_regime", "v2_regime"]),
    ]
    rows: list[dict] = []
    for model, cols in specs:
        pred = _loo_group_prediction(tagged, cols)
        brier = float(((pred - y) ** 2).mean())
        log_loss = float((-(y * pred.apply(math.log) + (1 - y) * (1 - pred).apply(math.log))).mean())
        rows.append(
            {
                "model": model,
                "features": "+".join(cols),
                "N": len(tagged),
                "brier_score": round(brier, 9),
                "log_loss": round(log_loss, 9),
            }
        )
    out = pd.DataFrame(rows).sort_values("brier_score")
    out.to_csv(OUT_DIR / "prediction_power_comparison.csv", index=False)
    return out


def _markdown_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    show = df.head(max_rows).copy()
    if show.empty:
        return "_No rows._"
    headers = [str(c) for c in show.columns]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for record in show.to_dict("records"):
        values = []
        for header in headers:
            value = record[header]
            if isinstance(value, float):
                if math.isfinite(value):
                    values.append(f"{value:.6g}")
                else:
                    values.append(str(value))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_markdown(
    tagged: pd.DataFrame,
    global_df: pd.DataFrame,
    proposals: pd.DataFrame,
    bonf: pd.DataFrame,
    pred: pd.DataFrame,
) -> None:
    pass_cells = bonf[bonf["bonferroni_pass"] == True]  # noqa: E712
    best_model = str(pred.iloc[0]["model"])
    composite_row = pred[pred["model"] == "composite"].iloc[0]
    dow_row = pred[pred["model"] == "dow_only"].iloc[0]
    v2_row = pred[pred["model"] == "v2_only"].iloc[0]
    proposal_splits = proposals.sort_values(["proposal", "N"], ascending=[True, False])
    structured = int((proposal_splits["N"] >= MIN_CELL_N).sum())
    total_prop_rows = len(proposal_splits)

    if len(pass_cells) > 0 and best_model == "composite":
        recommendation = "A"
        verdict = "CONDITIONAL_PRE_REG_CANDIDATE"
        next_action = "Bonferroni通過cellだけをPhase E Shadow候補としてpre-reg再定義する。Live昇格には使わない。"
    elif best_model == "composite":
        recommendation = "B"
        verdict = "FORWARD_ACCUMULATION_ONLY"
        next_action = "compositeは単一classifierより予測力があるが、補正後のcell証拠が弱いためforward N蓄積のみ。"
    else:
        recommendation = "D"
        verdict = "HOLD_GAP5_COMPOSITE"
        next_action = "compositeではedgeが強化されていないため、Gap 5 / Phase Eの再定義は保留する。"

    verdict_md = f"""# Composite Cell Retrospective Verdict

VERDICT: {verdict}

## Scope

- Source: `reports/regime_gate_phase_b2/trade_log_tagged.csv`
- Trades evaluated: {len(tagged)}
- Analysis type: retrospective observation only; not a Live promotion decision and not Shadow admission proof.
- Classifier changes: none. Existing `modules.regime_classifier.classify_15m` was used with local MASSIVE 15m cache features.

## Q1: 17 proposals are structurally decomposed?

Yes, but this is still retrospective EDA. The 17 proposals expand into {total_prop_rows} proposal x v2 rows; {structured} rows have N>=30 after the composite split.

Top proposal composite rows:

{_markdown_table(proposal_splits.sort_values(["Kelly", "N"], ascending=[False, False]), 12)}

## Q2: Bonferroni passing cells exist?

Effective m = {int(bonf["m_eff"].iloc[0]) if len(bonf) else 0}; alpha' = {float(bonf["alpha_prime"].iloc[0]) if len(bonf) else 0:.8f}. Passing cells = {len(pass_cells)}.

{_markdown_table(pass_cells if len(pass_cells) else bonf.head(10), 10)}

## Q3: Prediction power vs single classifiers

Lower is better. The comparison uses leave-one-out empirical win-rate predictions per bucket, with Laplace smoothing.

{_markdown_table(pred, 10)}

Composite Brier delta vs dow_only = {float(composite_row["brier_score"]) - float(dow_row["brier_score"]):+.9f}; vs v2_only = {float(composite_row["brier_score"]) - float(v2_row["brier_score"]):+.9f}.

## Q4: Recommended next action

Recommendation: {recommendation}

{next_action}
"""

    summary_md = f"""# Composite Cell Analysis Summary

VERDICT: {verdict}

This is a retrospective hypothesis-forming analysis on the frozen Phase B2.5 BT trade log. It must not be reused as Live promotion evidence or as proof that a Shadow gate is production-safe.

## Main Results

- Trades evaluated: {len(tagged)}
- Composite global cells: {len(global_df)} fixed dow_regime x v2_regime cells
- Bonferroni effective m: {int(bonf["m_eff"].iloc[0]) if len(bonf) else 0}
- Bonferroni passing strategy composite cells: {len(pass_cells)}
- Best prediction model by Brier score: `{best_model}`

## Global Composite Crosstab

{_markdown_table(global_df, 10)}

## Prediction Power

{_markdown_table(pred, 10)}

## Recommendation

{recommendation}: {next_action}
"""

    (OUT_DIR / "verdict.md").write_text(verdict_md.strip() + "\n", encoding="utf-8")
    (OUT_DIR / "SUMMARY.md").write_text(summary_md.strip() + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tagged = tag_trades()
    global_df, by_strategy, _top_df = write_crosstabs(tagged)
    proposals = write_proposal_composite(tagged)
    bonf = write_bonferroni(by_strategy)
    pred = write_prediction_power(tagged)
    write_markdown(tagged, global_df, proposals, bonf, pred)
    print(f"wrote composite analysis artifacts to {OUT_DIR}")


if __name__ == "__main__":
    main()
