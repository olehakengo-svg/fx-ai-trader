#!/usr/bin/env python3
"""Cross-pair confluence observation helper.

Implements the pre-registered Dow Theory principle #4 proxy for FX:
correlated markets should confirm the primary signal direction. This module is
monitor-only; callers must not use it as a universal entry gate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "cache" / "massive"

DXY_WEIGHTS: Mapping[str, float] = {
    "USD_JPY": 0.136,
    "EUR_USD": -0.576,
    "GBP_USD": -0.119,
    "USD_CHF": 0.036,
    "USD_CAD": 0.091,
    "AUD_USD": -0.042,
}

# relation is from primary pair movement to confluence component movement.
CONFLUENCE_REQUIREMENTS: Mapping[str, tuple[tuple[str, str], ...]] = {
    "USD_JPY": (("DXY", "same"), ("EUR_USD", "inverse"), ("USD_CHF", "same")),
    "EUR_USD": (("DXY", "inverse"), ("EUR_JPY", "same"), ("USD_CHF", "inverse")),
    "GBP_USD": (("DXY", "inverse"), ("GBP_JPY", "same"), ("USD_CHF", "inverse")),
    "EUR_JPY": (("EUR_USD", "same"), ("USD_JPY", "same")),
    "GBP_JPY": (("GBP_USD", "same"), ("USD_JPY", "same")),
    "AUD_USD": (("DXY", "inverse"), ("NZD_USD", "same"), ("USD_CAD", "inverse")),
}


@dataclass(frozen=True)
class ConfluenceResult:
    score: str
    confirmations: int
    required: int
    details: dict

    def details_json(self) -> str:
        return json.dumps(self.details, sort_keys=True, ensure_ascii=False)


def normalize_pair(pair: str) -> str:
    value = str(pair or "").upper().replace("/", "_").replace("-", "_")
    if value.endswith("=X"):
        value = value[:-2]
    value = value.replace("_", "")
    if len(value) == 6:
        return f"{value[:3]}_{value[3:]}"
    return value


def normalize_signal_direction(direction: str) -> str | None:
    value = str(direction or "").upper()
    if value in {"BUY", "LONG", "UP"}:
        return "up"
    if value in {"SELL", "SHORT", "DOWN"}:
        return "down"
    return None


def expected_component_direction(primary_expected: str, relation: str) -> str:
    if relation == "same":
        return primary_expected
    if primary_expected == "up":
        return "down"
    return "up"


def _cache_path(pair: str, cache_dir: Path = CACHE_DIR) -> Path:
    return Path(cache_dir) / f"{normalize_pair(pair)}_1h.parquet"


def _normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={c: c.lower() for c in df.columns}).copy()
    if "close" not in out.columns:
        raise ValueError("MASSIVE cache is missing close column")
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, utc=True)
    elif out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def load_massive_1h(pair: str, cache_dir: Path = CACHE_DIR) -> pd.DataFrame:
    path = _cache_path(pair, cache_dir)
    if not path.exists():
        raise FileNotFoundError(f"missing MASSIVE 1h cache: {path}")
    return _normalize_ohlc(pd.read_parquet(path))


def _parse_ts(ts) -> pd.Timestamp:
    parsed = pd.Timestamp(ts)
    if parsed.tzinfo is None:
        return parsed.tz_localize("UTC")
    return parsed.tz_convert("UTC")


def direction_from_close(close: pd.Series) -> str:
    values = close.dropna().astype(float)
    if len(values) < 2:
        return "flat"
    delta = float(values.iloc[-1] - values.iloc[0])
    threshold = float(values.std() * 0.5)
    if delta > threshold:
        return "up"
    if delta < -threshold:
        return "down"
    return "flat"


def get_h1_direction(
    pair: str,
    ts,
    lookback: int = 5,
    cache_dir: Path = CACHE_DIR,
    cache: dict[str, pd.DataFrame] | None = None,
) -> str:
    pair_key = normalize_pair(pair)
    if cache is not None and pair_key in cache:
        df = cache[pair_key]
    else:
        df = load_massive_1h(pair_key, cache_dir)
        if cache is not None:
            cache[pair_key] = df
    end = _parse_ts(ts)
    window = df.loc[df.index <= end].tail(int(lookback) + 1)
    return direction_from_close(window["close"])


def get_dxy_direction(
    ts,
    lookback: int = 5,
    cache_dir: Path = CACHE_DIR,
    cache: dict[str, pd.DataFrame] | None = None,
) -> tuple[str, str]:
    dxy_path = _cache_path("DXY", cache_dir)
    if dxy_path.exists():
        return get_h1_direction("DXY", ts, lookback, cache_dir, cache), "DXY"

    end = _parse_ts(ts)
    series = []
    used: list[str] = []
    for pair, weight in DXY_WEIGHTS.items():
        try:
            pair_key = normalize_pair(pair)
            if cache is not None and pair_key in cache:
                df = cache[pair_key]
            else:
                df = load_massive_1h(pair_key, cache_dir)
                if cache is not None:
                    cache[pair_key] = df
            close = df.loc[df.index <= end, "close"].tail(int(lookback) + 1).astype(float)
            if len(close) < 2:
                continue
            ret = close / float(close.iloc[0]) - 1.0
            series.append(ret.rename(pair) * float(weight))
            used.append(pair)
        except Exception:
            continue
    if not series:
        return "flat", "DXY_proxy_empty"
    proxy = pd.concat(series, axis=1).sum(axis=1)
    return direction_from_close(proxy), "DXY_proxy:" + ",".join(used)


def compute_confluence(
    primary_pair: str,
    primary_dir: str,
    entry_time,
    lookback: int = 5,
    cache_dir: Path = CACHE_DIR,
    cache: dict[str, pd.DataFrame] | None = None,
) -> ConfluenceResult:
    pair = normalize_pair(primary_pair)
    expected = normalize_signal_direction(primary_dir)
    requirements = CONFLUENCE_REQUIREMENTS.get(pair)
    if expected is None or not requirements or pair == "XAU_USD":
        return ConfluenceResult(
            score="NULL",
            confirmations=0,
            required=0,
            details={
                "primary_pair": pair,
                "primary_dir": primary_dir,
                "reason": "unsupported_pair_or_direction",
            },
        )

    details: dict = {
        "primary_pair": pair,
        "primary_dir": str(primary_dir).upper(),
        "expected_primary_direction": expected,
        "lookback_h1_bars": int(lookback),
        "components": [],
    }
    confirmations = 0
    for component, relation in requirements:
        try:
            if component == "DXY":
                observed, source = get_dxy_direction(entry_time, lookback, cache_dir, cache)
            else:
                observed = get_h1_direction(component, entry_time, lookback, cache_dir, cache)
                source = normalize_pair(component)
            expected_component = expected_component_direction(expected, relation)
            confirms = observed == expected_component and observed != "flat"
            confirmations += 1 if confirms else 0
            details["components"].append(
                {
                    "component": component,
                    "source": source,
                    "relation": relation,
                    "observed": observed,
                    "expected": expected_component,
                    "confirms": confirms,
                }
            )
        except Exception as exc:
            details["components"].append(
                {
                    "component": component,
                    "relation": relation,
                    "observed": "NULL",
                    "expected": expected_component_direction(expected, relation),
                    "confirms": False,
                    "error": str(exc),
                }
            )

    if confirmations >= 3:
        score = "STRONG"
    elif confirmations == 2:
        score = "WEAK"
    else:
        score = "MIXED"
    return ConfluenceResult(score=score, confirmations=confirmations, required=len(requirements), details=details)


__all__ = [
    "CACHE_DIR",
    "CONFLUENCE_REQUIREMENTS",
    "ConfluenceResult",
    "compute_confluence",
    "get_h1_direction",
    "normalize_pair",
]
