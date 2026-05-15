#!/usr/bin/env python3
"""Pre-registered price shock mean reversion grid BT.

Uses repo-local MASSIVE parquet only. No Yahoo fallback.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.price_shock_grid_db import connect, replace_cells  # noqa: E402


PAIRS_LITERAL = [
    "USD_JPY",
    "EUR_USD",
    "GBP_USD",
    "AUD_USD",
    "NZD_USD",
    "USD_CAD",
    "USD_CHF",
    "EUR_JPY",
    "GBP_JPY",
    "AUD_JPY",
    "NZD_JPY",
    "EUR_GBP",
    "EUR_AUD",
    "GBP_JPY",
]
TFS = ["H4", "H1"]
PERCENTILES = [0.01, 0.025, 0.05]
DIRECTIONS = ["LONG_SHOCK", "SHORT_SHOCK"]
HORIZONS = [1, 3, 6, 12]
VOL_BUCKETS = ["ALL", "Q1", "Q2", "Q3", "Q4", "Q5"]
PRE_REG_M = 4032
FDR_Q = 0.10
BONFERRONI_ALPHA = 0.05 / PRE_REG_M
DATA_SOURCE = "MASSIVE_parquet"

ROLLING_WINDOW = {
    "H1": 252,
    "H4": 1512,
}
ANNUAL_BARS = {
    "H1": 252 * 24,
    "H4": 252 * 6,
}
TYPICAL_SPREAD_PIP = {
    "USD_JPY": 0.2,
    "EUR_USD": 0.1,
    "GBP_USD": 0.2,
    "AUD_USD": 0.2,
    "NZD_USD": 0.3,
    "USD_CAD": 0.2,
    "USD_CHF": 0.2,
    "EUR_JPY": 0.3,
    "GBP_JPY": 0.5,
    "AUD_JPY": 0.4,
    "NZD_JPY": 0.5,
    "EUR_GBP": 0.2,
    "EUR_AUD": 0.5,
}


@dataclass(frozen=True)
class LoadedFrame:
    pair: str
    tf: str
    df: pd.DataFrame
    source_path: Path
    derived_from: Path | None = None


def unique_ordered(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def pip_multiplier(pair: str) -> float:
    return 100.0 if "JPY" in pair else 10000.0


def parquet_path(cache_dir: Path, pair: str, tf: str) -> Path:
    suffix = "4h" if tf == "H4" else "1h"
    return cache_dir / f"{pair}_{suffix}.parquet"


def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    rename = {col: col.capitalize() for col in df.columns if col.lower() in {"open", "high", "low", "close", "volume"}}
    out = df.rename(columns=rename).copy()
    required = ["Open", "High", "Low", "Close"]
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"missing OHLC columns: {missing}")
    if not isinstance(out.index, pd.DatetimeIndex):
        for candidate in ("time", "timestamp", "datetime", "Date", "date"):
            if candidate in out.columns:
                out.index = pd.to_datetime(out[candidate], utc=True)
                break
    if not isinstance(out.index, pd.DatetimeIndex):
        raise ValueError("parquet must have a DatetimeIndex or timestamp column")
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    out = out.sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out[required].astype(float).dropna()


def resample_h1_to_h4(df: pd.DataFrame) -> pd.DataFrame:
    agg = {
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
    }
    return df.resample("4h", label="right", closed="right").agg(agg).dropna()


def load_frame(cache_dir: Path, pair: str, tf: str, allow_h4_from_h1: bool = False) -> LoadedFrame | None:
    path = parquet_path(cache_dir, pair, tf)
    if path.exists():
        return LoadedFrame(pair=pair, tf=tf, df=normalize_ohlc(pd.read_parquet(path)), source_path=path)
    if tf == "H4" and allow_h4_from_h1:
        h1_path = parquet_path(cache_dir, pair, "H1")
        if h1_path.exists():
            h1 = normalize_ohlc(pd.read_parquet(h1_path))
            return LoadedFrame(pair=pair, tf=tf, df=resample_h1_to_h4(h1), source_path=path, derived_from=h1_path)
    return None


def add_precomputed_columns(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    out = df.copy()
    out["log_return"] = np.log(out["Close"] / out["Close"].shift(1))
    out["vol20"] = out["log_return"].rolling(20, min_periods=20).std()
    window = ROLLING_WINDOW[tf]
    shifted_ret = out["log_return"].shift(1)
    shifted_vol = out["vol20"].shift(1)
    for pct in PERCENTILES:
        key = pct_key(pct)
        out[f"lower_{key}"] = shifted_ret.rolling(window, min_periods=window).quantile(pct)
        out[f"upper_{key}"] = shifted_ret.rolling(window, min_periods=window).quantile(1.0 - pct)
    for q, quantile in (("q20", 0.2), ("q40", 0.4), ("q60", 0.6), ("q80", 0.8)):
        out[f"vol_{q}"] = shifted_vol.rolling(window, min_periods=window).quantile(quantile)
    conditions = [
        out["vol20"] <= out["vol_q20"],
        out["vol20"] <= out["vol_q40"],
        out["vol20"] <= out["vol_q60"],
        out["vol20"] <= out["vol_q80"],
        out["vol20"] > out["vol_q80"],
    ]
    out["vol_quintile_calc"] = np.select(conditions, ["Q1", "Q2", "Q3", "Q4", "Q5"], default=None)
    return out


def pct_key(pct: float) -> str:
    return str(pct).replace(".", "p")


def wilson_lower(wins: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / denom)


def profit_factor(pip_returns: np.ndarray) -> float:
    gross_profit = float(pip_returns[pip_returns > 0].sum())
    gross_loss = float(-pip_returns[pip_returns < 0].sum())
    if gross_loss <= 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def p_value_mean_positive(returns: np.ndarray) -> float:
    clean = returns[np.isfinite(returns)]
    n = len(clean)
    if n < 2:
        return 1.0
    mean = float(clean.mean())
    std = float(clean.std(ddof=1))
    if std <= 0:
        return 0.0 if mean > 0 else 1.0
    t_stat = mean / (std / math.sqrt(n))
    try:
        from scipy import stats

        return float(stats.t.sf(t_stat, n - 1))
    except Exception:
        return float(0.5 * math.erfc(t_stat / math.sqrt(2.0)))


def max_drawdown_pct(returns_pct: np.ndarray) -> float:
    if len(returns_pct) == 0:
        return 0.0
    equity = np.cumsum(returns_pct)
    peaks = np.maximum.accumulate(equity)
    dd = equity - peaks
    return float(dd.min()) if len(dd) else 0.0


def year_flip_count(years: np.ndarray, returns_pct: np.ndarray) -> int:
    if len(returns_pct) == 0:
        return 0
    aggregate = float(np.nanmean(returns_pct))
    if aggregate == 0 or not math.isfinite(aggregate):
        return 0
    agg_sign = 1 if aggregate > 0 else -1
    flips = 0
    for year in sorted(set(int(y) for y in years)):
        yr_returns = returns_pct[years == year]
        if len(yr_returns) == 0:
            continue
        yr_mean = float(np.nanmean(yr_returns))
        if yr_mean == 0 or not math.isfinite(yr_mean):
            continue
        if (1 if yr_mean > 0 else -1) != agg_sign:
            flips += 1
    return flips


def classify_verdict(row: dict) -> str:
    g1 = row["n_trades"] >= 30
    g2 = (row["wilson_lower_95"] or 0.0) >= 0.50
    g3 = (row["profit_factor"] or 0.0) >= 1.20
    g4 = bool(row["bh_fdr_pass"])
    g5 = row["year_flip_count"] <= 1
    spread = TYPICAL_SPREAD_PIP.get(row["pair"], 0.5)
    g6 = (row["ev_pip"] or 0.0) >= 1.5 * spread
    if g1 and g2 and g3 and g4 and g5 and g6:
        return "SHADOW_CANDIDATE"
    if g1 and g2 and g3 and g4:
        return "CONDITIONAL"
    return "REJECT"


def cell_id(pair: str, tf: str, direction: str, percentile: float, horizon: int, vol_q: str) -> str:
    pct = {0.01: "1", 0.025: "2p5", 0.05: "5"}[percentile]
    return f"{pair}_{tf}_{direction}_{pct}_{horizon}_{vol_q}"


def compute_grid_for_frame(loaded: LoadedFrame, generated_at: str) -> list[dict]:
    pair = loaded.pair
    tf = loaded.tf
    df = add_precomputed_columns(loaded.df, tf)
    period_start = df.index.min().isoformat()
    period_end = df.index.max().isoformat()
    rows: list[dict] = []
    pips = pip_multiplier(pair)
    annual_scale = math.sqrt(ANNUAL_BARS[tf])

    for pct in PERCENTILES:
        key = pct_key(pct)
        signal_masks = {
            "LONG_SHOCK": df["log_return"] <= df[f"lower_{key}"],
            "SHORT_SHOCK": df["log_return"] >= df[f"upper_{key}"],
        }
        for direction in DIRECTIONS:
            base_mask = signal_masks[direction].fillna(False)
            for horizon in HORIZONS:
                entry = df["Open"].shift(-1)
                exit_ = df["Close"].shift(-horizon)
                if direction == "LONG_SHOCK":
                    pct_ret = (exit_ / entry - 1.0) * 100.0
                    pip_ret = (exit_ - entry) * pips
                else:
                    pct_ret = (entry / exit_ - 1.0) * 100.0
                    pip_ret = (entry - exit_) * pips
                valid = base_mask & entry.notna() & exit_.notna()
                for vol_q in VOL_BUCKETS:
                    mask = valid if vol_q == "ALL" else (valid & (df["vol_quintile_calc"] == vol_q))
                    idx = np.flatnonzero(mask.to_numpy())
                    rows.append(
                        stats_for_cell(
                            df=df,
                            idx=idx,
                            pair=pair,
                            tf=tf,
                            direction=direction,
                            pct=pct,
                            horizon=horizon,
                            vol_q=vol_q,
                            pct_ret=pct_ret.to_numpy(dtype=float),
                            pip_ret=pip_ret.to_numpy(dtype=float),
                            annual_scale=annual_scale,
                            period_start=period_start,
                            period_end=period_end,
                            generated_at=generated_at,
                        )
                    )
    return rows


def stats_for_cell(
    df: pd.DataFrame,
    idx: np.ndarray,
    pair: str,
    tf: str,
    direction: str,
    pct: float,
    horizon: int,
    vol_q: str,
    pct_ret: np.ndarray,
    pip_ret: np.ndarray,
    annual_scale: float,
    period_start: str,
    period_end: str,
    generated_at: str,
) -> dict:
    n = int(len(idx))
    if n == 0:
        return empty_cell(pair, tf, direction, pct, horizon, vol_q, period_start, period_end, generated_at)

    r_pct = pct_ret[idx]
    r_pip = pip_ret[idx]
    wins = int((r_pct > 0).sum())
    wr = wins / n
    pf = profit_factor(r_pip)
    std = float(np.nanstd(r_pct, ddof=1)) if n > 1 else 0.0
    sharpe = float(np.nanmean(r_pct) / std * annual_scale) if std > 0 else 0.0
    gains = r_pct[r_pct > 0]
    losses = r_pct[r_pct < 0]
    rr = float(np.nanmean(gains) / -np.nanmean(losses)) if len(gains) and len(losses) else None
    kelly = wr - (1.0 - wr) / rr if rr and rr > 0 else (1.0 if len(gains) and not len(losses) else 0.0)
    mae, mfe = mae_mfe(df, idx, horizon, direction)
    years = df.index[idx].year.to_numpy()
    p_value = p_value_mean_positive(r_pct)

    return {
        "cell_id": cell_id(pair, tf, direction, pct, horizon, vol_q),
        "pair": pair,
        "tf": tf,
        "direction": direction,
        "percentile": pct,
        "horizon_bars": horizon,
        "vol_quintile": vol_q,
        "n_trades": n,
        "win_rate": wr,
        "ev_pip": float(np.nanmean(r_pip)),
        "ev_pct": float(np.nanmean(r_pct)),
        "profit_factor": pf,
        "wilson_lower_95": wilson_lower(wins, n),
        "sharpe_annual": sharpe,
        "kelly_fraction": float(kelly),
        "max_dd_pct": max_drawdown_pct(r_pct),
        "mae_mean_pct": float(np.nanmean(mae)) if len(mae) else 0.0,
        "mae_p5_pct": float(np.nanpercentile(mae, 5)) if len(mae) else 0.0,
        "mfe_mean_pct": float(np.nanmean(mfe)) if len(mfe) else 0.0,
        "year_flip_count": year_flip_count(years, r_pct),
        "p_value": p_value,
        "bonferroni_pass": int(p_value < BONFERRONI_ALPHA),
        "bh_fdr_pass": 0,
        "verdict": "REJECT",
        "period_start": period_start,
        "period_end": period_end,
        "bt_data_source": DATA_SOURCE,
        "generated_at": generated_at,
    }


def empty_cell(
    pair: str,
    tf: str,
    direction: str,
    pct: float,
    horizon: int,
    vol_q: str,
    period_start: str,
    period_end: str,
    generated_at: str,
) -> dict:
    return {
        "cell_id": cell_id(pair, tf, direction, pct, horizon, vol_q),
        "pair": pair,
        "tf": tf,
        "direction": direction,
        "percentile": pct,
        "horizon_bars": horizon,
        "vol_quintile": vol_q,
        "n_trades": 0,
        "win_rate": 0.0,
        "ev_pip": 0.0,
        "ev_pct": 0.0,
        "profit_factor": 0.0,
        "wilson_lower_95": 0.0,
        "sharpe_annual": 0.0,
        "kelly_fraction": 0.0,
        "max_dd_pct": 0.0,
        "mae_mean_pct": 0.0,
        "mae_p5_pct": 0.0,
        "mfe_mean_pct": 0.0,
        "year_flip_count": 0,
        "p_value": 1.0,
        "bonferroni_pass": 0,
        "bh_fdr_pass": 0,
        "verdict": "REJECT",
        "period_start": period_start,
        "period_end": period_end,
        "bt_data_source": DATA_SOURCE,
        "generated_at": generated_at,
    }


def mae_mfe(df: pd.DataFrame, idx: np.ndarray, horizon: int, direction: str) -> tuple[np.ndarray, np.ndarray]:
    open_values = df["Open"].to_numpy(dtype=float)
    high_values = df["High"].to_numpy(dtype=float)
    low_values = df["Low"].to_numpy(dtype=float)
    mae: list[float] = []
    mfe: list[float] = []
    for i in idx:
        entry_i = i + 1
        exit_i = i + horizon
        if entry_i >= len(df) or exit_i >= len(df):
            continue
        entry = open_values[entry_i]
        lows = low_values[entry_i : exit_i + 1]
        highs = high_values[entry_i : exit_i + 1]
        if direction == "LONG_SHOCK":
            mae.append((float(np.nanmin(lows)) / entry - 1.0) * 100.0)
            mfe.append((float(np.nanmax(highs)) / entry - 1.0) * 100.0)
        else:
            mae.append((entry / float(np.nanmax(highs)) - 1.0) * 100.0)
            mfe.append((entry / float(np.nanmin(lows)) - 1.0) * 100.0)
    return np.asarray(mae, dtype=float), np.asarray(mfe, dtype=float)


def apply_multiple_testing(rows: list[dict]) -> None:
    ordered = sorted((row for row in rows if math.isfinite(float(row["p_value"]))), key=lambda r: r["p_value"])
    max_pass_rank = 0
    for rank, row in enumerate(ordered, start=1):
        if row["p_value"] <= (rank / PRE_REG_M) * FDR_Q:
            max_pass_rank = rank
    pass_ids = {row["cell_id"] for row in ordered[:max_pass_rank]}
    for row in rows:
        row["bh_fdr_pass"] = int(row["cell_id"] in pass_ids)
        row["bonferroni_pass"] = int(row["p_value"] < BONFERRONI_ALPHA)
        row["verdict"] = classify_verdict(row)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fmt_num(value: float | int | None, digits: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float) and not math.isfinite(value):
        return "inf" if value > 0 else "-inf"
    return f"{float(value):.{digits}f}"


def evidence_line(row: dict) -> str:
    return (
        f"{row['cell_id']}: N={row['n_trades']} WR={fmt_num(row['win_rate'], 3)} "
        f"Wilson={fmt_num(row['wilson_lower_95'], 3)} PF={fmt_num(row['profit_factor'], 2)} "
        f"EV={fmt_num(row['ev_pip'], 2)}pip/{fmt_num(row['ev_pct'], 4)}% "
        f"p={fmt_num(row['p_value'], 6)} flips={row['year_flip_count']} "
        f"BH={row['bh_fdr_pass']} Bonf={row['bonferroni_pass']}"
    )


def write_reports(out_dir: Path, rows: list[dict], loaded: list[LoadedFrame], skipped: list[dict], generated_at: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "grid_full.csv", rows)
    shadow = [r for r in rows if r["verdict"] == "SHADOW_CANDIDATE"]
    conditional = [r for r in rows if r["verdict"] == "CONDITIONAL"]
    reject = [r for r in rows if r["verdict"] == "REJECT"]
    top = sorted(rows, key=lambda r: (r["verdict"] == "SHADOW_CANDIDATE", r["ev_pip"], r["profit_factor"]), reverse=True)[:10]

    (out_dir / "survivors.md").write_text(build_survivors(shadow, generated_at), encoding="utf-8")
    (out_dir / "conditional.md").write_text(build_conditional(conditional, generated_at), encoding="utf-8")
    (out_dir / "null_summary.md").write_text(build_null_summary(rows, reject, skipped, generated_at), encoding="utf-8")
    (out_dir / "SUMMARY.md").write_text(build_summary(rows, shadow, conditional, reject, loaded, skipped, top, generated_at), encoding="utf-8")
    (out_dir / "verdict.md").write_text(build_verdict(rows, shadow, conditional, top, skipped, generated_at), encoding="utf-8")
    root_final = ROOT / "final.md"
    root_final.write_text(build_final_md(rows, shadow, conditional, reject, top, skipped, generated_at), encoding="utf-8")


def build_survivors(rows: list[dict], generated_at: str) -> str:
    lines = [f"# Price Shock Reversion Survivors\n\nGenerated: {generated_at}\n"]
    if not rows:
        lines.append("\nNo SHADOW_CANDIDATE cells passed G1-G6.\n")
    else:
        for row in sorted(rows, key=lambda r: r["ev_pip"], reverse=True):
            lines.append(f"- {evidence_line(row)}")
        lines.append("")
    lines.append("\n## Thesis\nPrice-shock percentiles test whether extreme own-price returns revert over fixed short horizons.\n")
    lines.append("\n## Design Defects To Audit\nPrimary risk is sample truncation when MASSIVE history is shorter than the rolling lookback, especially H4.\n")
    lines.append("\n## Redesign Ideas\nOnly commander-reviewed future work should consider wider extreme-decile screens or longer source history.\n")
    return "\n".join(lines)


def build_conditional(rows: list[dict], generated_at: str) -> str:
    lines = [f"# Conditional Cells\n\nGenerated: {generated_at}\n"]
    if not rows:
        lines.append("\nNo CONDITIONAL cells. No cell passed G1-G4 while failing G5 or G6.\n")
    else:
        for row in sorted(rows, key=lambda r: r["ev_pip"], reverse=True):
            spread_gate = 1.5 * TYPICAL_SPREAD_PIP.get(row["pair"], 0.5)
            lines.append(f"- {evidence_line(row)} cost_gate={fmt_num(spread_gate, 2)}pip")
    return "\n".join(lines) + "\n"


def build_null_summary(rows: list[dict], reject: list[dict], skipped: list[dict], generated_at: str) -> str:
    fail_counts = {
        "N_lt_30": sum(1 for r in reject if r["n_trades"] < 30),
        "Wilson_lt_0p50": sum(1 for r in reject if r["wilson_lower_95"] < 0.50),
        "PF_lt_1p20": sum(1 for r in reject if r["profit_factor"] < 1.20),
        "BH_FDR_fail": sum(1 for r in reject if not r["bh_fdr_pass"]),
        "year_flip_gt_1": sum(1 for r in reject if r["year_flip_count"] > 1),
        "cost_fail": sum(1 for r in reject if r["ev_pip"] < 1.5 * TYPICAL_SPREAD_PIP.get(r["pair"], 0.5)),
    }
    by_direction = {
        direction: sum(1 for r in reject if r["direction"] == direction)
        for direction in DIRECTIONS
    }
    lines = [
        "# Null Summary",
        "",
        f"Generated: {generated_at}",
        f"Generated cells: {len(rows)}",
        f"Reject cells: {len(reject)}",
        "",
        "## Failure Pattern Counts",
    ]
    for key, value in fail_counts.items():
        lines.append(f"- {key}: {value}")
    lines.append("\n## Direction-Led Reject Counts")
    for key, value in by_direction.items():
        lines.append(f"- {key}: {value}")
    lines.append("\n## Skipped Pair/TF")
    if skipped:
        for item in skipped:
            lines.append(f"- {item['pair']} {item['tf']}: {item['reason']}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def build_summary(
    rows: list[dict],
    shadow: list[dict],
    conditional: list[dict],
    reject: list[dict],
    loaded: list[LoadedFrame],
    skipped: list[dict],
    top: list[dict],
    generated_at: str,
) -> str:
    verdict = "GO shadow audit" if shadow else "NO-GO / hypothesis kill pending commander review"
    lines = [
        "# Price Shock Reversion Grid SUMMARY",
        "",
        f"Generated: {generated_at}",
        "",
        f"## Verdict",
        f"🔴 **{verdict}**",
        "",
        "## Rec",
        f"- **Generated cells**: {len(rows)}",
        f"- **SHADOW_CANDIDATE**: {len(shadow)}",
        f"- **CONDITIONAL**: {len(conditional)}",
        f"- **REJECT**: {len(reject)}",
        f"- **Loaded pair/TF**: {len(loaded)}",
        f"- **Skipped pair/TF**: {len(skipped)}",
        "",
        "## Evidence",
    ]
    if top:
        for row in top:
            lines.append(f"- **{evidence_line(row)}**")
    else:
        lines.append("- No generated cells.")
    lines.extend(
        [
            "",
            "## 思想",
            "価格予測ではなく、価格自身の極値分位後の固定horizon平均回帰を検定した。",
            "",
            "## 設計欠陥",
            "現ローカルMASSIVE cacheは指定14 pair x 2 TFを満たしていないため、未存在pair/TFはskipされた。",
            "",
            "## 再設計案",
            "post-hoc gate緩和はせず、必要ならMASSIVE H4/欠損pair履歴を補完して同一pre-reg gridを再実行する。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_verdict(rows: list[dict], shadow: list[dict], conditional: list[dict], top: list[dict], skipped: list[dict], generated_at: str) -> str:
    lines = [
        "# Price Shock Reversion Verdict",
        "",
        f"Generated: {generated_at}",
        "",
        f"Overall: {'GO' if shadow else 'NO-GO'}",
        f"SHADOW_CANDIDATE: {len(shadow)}",
        f"CONDITIONAL: {len(conditional)}",
        f"REJECT: {sum(1 for r in rows if r['verdict'] == 'REJECT')}",
        "",
        "## Shadow Promote Recommendations",
    ]
    if shadow:
        for row in sorted(shadow, key=lambda r: r["ev_pip"], reverse=True)[:10]:
            lines.append(f"- {evidence_line(row)}")
    else:
        lines.append("- none")
    lines.append("\n## Top 10 Evidence")
    for row in top:
        lines.append(f"- {evidence_line(row)}")
    lines.append("\n## Skip Notes")
    for item in skipped:
        lines.append(f"- {item['pair']} {item['tf']}: {item['reason']}")
    if not skipped:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def build_final_md(rows: list[dict], shadow: list[dict], conditional: list[dict], reject: list[dict], top: list[dict], skipped: list[dict], generated_at: str) -> str:
    lines = [
        "# final.md",
        "",
        f"Generated: {generated_at}",
        "",
        f"投入 cell 数: {len(rows)}",
        f"SHADOW_CANDIDATE 数: {len(shadow)}",
        f"CONDITIONAL 数: {len(conditional)}",
        f"REJECT 数: {len(reject)}",
        "",
        "## Top 10 Survivors / Evidence",
    ]
    if shadow:
        for row in sorted(shadow, key=lambda r: r["ev_pip"], reverse=True)[:10]:
            lines.append(f"- {evidence_line(row)}")
    elif top:
        lines.append("No SHADOW_CANDIDATE cells. Top 10 raw evidence rows are listed for audit context:")
        for row in top:
            lines.append(f"- {evidence_line(row)}")
    else:
        lines.append("- none")
    lines.append("\n## Skips")
    if skipped:
        for item in skipped:
            lines.append(f"- {item['pair']} {item['tf']}: {item['reason']}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", default=str(ROOT / "data" / "cache" / "massive"))
    parser.add_argument("--out-dir", default=str(ROOT / "reports" / "price_shock_reversion_grid"))
    parser.add_argument("--db", default=str(ROOT / "data" / "price_shock_grid_cells.db"))
    parser.add_argument("--allow-h4-from-h1", action="store_true", help="derive H4 bars from MASSIVE H1 parquet when *_4h.parquet is absent")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cache_dir = Path(args.cache_dir)
    generated_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []
    loaded_frames: list[LoadedFrame] = []
    skipped: list[dict] = []

    duplicate_pairs = [p for p in PAIRS_LITERAL if PAIRS_LITERAL.count(p) > 1]
    if duplicate_pairs:
        skipped.append({"pair": "GBP_JPY", "tf": "DUPLICATE_SPEC_ENTRY", "reason": "pair list contains duplicate GBP_JPY; deduped to preserve DDL primary key cell_id"})

    for pair in unique_ordered(PAIRS_LITERAL):
        for tf in TFS:
            loaded = load_frame(cache_dir, pair, tf, allow_h4_from_h1=args.allow_h4_from_h1)
            if loaded is None:
                skipped.append({"pair": pair, "tf": tf, "reason": f"missing {parquet_path(cache_dir, pair, tf)}"})
                continue
            if len(loaded.df) <= ROLLING_WINDOW[tf] + max(HORIZONS) + 1:
                skipped.append({"pair": pair, "tf": tf, "reason": f"insufficient bars {len(loaded.df)} <= lookback {ROLLING_WINDOW[tf]} + horizon"})
                continue
            loaded_frames.append(loaded)
            rows.extend(compute_grid_for_frame(loaded, generated_at))

    apply_multiple_testing(rows)
    out_dir = Path(args.out_dir)
    write_reports(out_dir, rows, loaded_frames, skipped, generated_at)
    with connect(args.db) as conn:
        replace_cells(conn, rows)

    print(f"generated_cells={len(rows)}")
    print(f"shadow={sum(1 for r in rows if r['verdict'] == 'SHADOW_CANDIDATE')}")
    print(f"conditional={sum(1 for r in rows if r['verdict'] == 'CONDITIONAL')}")
    print(f"reject={sum(1 for r in rows if r['verdict'] == 'REJECT')}")
    print(f"reports={out_dir}")
    print(f"db={args.db}")
    if skipped:
        print(f"skipped={len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
