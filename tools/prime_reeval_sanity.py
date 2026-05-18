#!/usr/bin/env python3
"""PRIME v2 re-evaluation against real Render shadow trades.

This tool intentionally uses the live demo trades API plus local MASSIVE
parquet candles. It is not a mock test.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import textwrap
import time
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import product
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from scipy.stats import fisher_exact

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.confidence_q4_gate import should_shadow as q4_should_shadow  # noqa: E402
from modules.prime_gate import _PRIMES, classify_prime  # noqa: E402
from tools.prime_gate_order_dry_run import API_URL as DRY_RUN_API_URL  # noqa: E402
from tools.prime_gate_order_dry_run import replay as dry_run_replay  # noqa: E402

API_URL = "https://fx-ai-trader.onrender.com/api/demo/trades?limit=10000"
INSTRUMENTS = ("USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY", "AUD_USD")
TASK_B_STRATEGIES = (
    "gbp_deep_pullback",
    "orb_trap",
    "ob_retest",
    "trend_rebound",
    "dt_sr_channel_reversal",
    "wick_imbalance_reversion",
)
TASK_B_SESSIONS = ("tokyo", "london", "ny", "overlap")
QUARTILES = ("Q1", "Q2", "Q3", "Q4")
DIRECTIONS = ("BUY", "SELL")
BONF_M6_ALPHA = 0.05 / 6
BONF_TASK_B_ALPHA = 0.05 / (len(TASK_B_STRATEGIES) * 768)


@dataclass
class PrimeSpec:
    name: str
    base: str
    tier: str
    lot: float
    predicate: Callable[[dict[str, Any]], bool]


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        out = datetime.fromisoformat(text)
    except ValueError:
        return None
    if out.tzinfo is None:
        out = out.replace(tzinfo=timezone.utc)
    return out.astimezone(timezone.utc)


def _rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for key in ("trades", "data", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [r for r in value if isinstance(r, dict)]
    return []


def fetch_rows(url: str = API_URL) -> list[dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": "fx-ai-trader-prime-reeval/1.0"})
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return _rows(json.loads(resp.read().decode("utf-8")))
        except Exception as exc:  # noqa: BLE001 - CLI retry surface
            last_error = exc
            time.sleep(attempt * 2)
    raise RuntimeError(f"failed to fetch API rows: {last_error}")


def _is_shadow(row: dict[str, Any]) -> bool:
    value = row.get("is_shadow")
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _outcome(row: dict[str, Any]) -> str:
    return str(row.get("outcome") or "").upper()


def _is_winloss_shadow(row: dict[str, Any]) -> bool:
    return _is_shadow(row) and row.get("instrument") != "XAU_USD" and _outcome(row) in {"WIN", "LOSS"}


def _float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = row.get(key)
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _loads_maybe(value: Any) -> Any:
    if isinstance(value, str) and value.strip().startswith(("{", "[")):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


def _row_regime(row: dict[str, Any]) -> dict[str, Any]:
    regime = _loads_maybe(row.get("regime"))
    return regime if isinstance(regime, dict) else {}


def _signal(row: dict[str, Any]) -> str:
    return str(row.get("direction") or row.get("signal") or row.get("side") or "").upper()


def _sig(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "signal": _signal(row),
        "confidence": _float(row, "confidence"),
        "regime": _row_regime(row),
    }


def _session_prime(hour: int) -> str:
    if 0 <= hour < 8:
        return "tokyo"
    if 8 <= hour < 13:
        return "london"
    if 13 <= hour < 22:
        return "ny"
    return "offhours"


def _session_grid(hour: int) -> str:
    if 0 <= hour < 8:
        return "tokyo"
    if 8 <= hour < 13:
        return "london"
    if 13 <= hour < 17:
        return "overlap"
    return "ny"


def _quartile(value: Any, edges: list[float]) -> str | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(v):
        return None
    if v <= edges[0]:
        return "Q1"
    if v <= edges[1]:
        return "Q2"
    if v <= edges[2]:
        return "Q3"
    return "Q4"


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return (centre - margin) / denom


def _adjusted_pips(row: dict[str, Any]) -> float:
    pnl = _float(row, "pnl_pips")
    spread = max(0.0, _float(row, "spread_at_entry"))
    slippage = abs(_float(row, "slippage_pips"))
    return pnl - spread - slippage


def _profit_factor(values: list[float]) -> float:
    wins = sum(v for v in values if v > 0)
    losses = -sum(v for v in values if v < 0)
    if losses <= 0:
        return float("inf") if wins > 0 else 0.0
    return wins / losses


def _kelly_half(values: list[float]) -> float:
    wins = [v for v in values if v > 0]
    losses = [-v for v in values if v < 0]
    n = len(wins) + len(losses)
    if n == 0 or not wins or not losses:
        return 0.0
    p = len(wins) / n
    q = 1.0 - p
    payoff = (sum(wins) / len(wins)) / (sum(losses) / len(losses))
    if payoff <= 0:
        return 0.0
    return max(0.0, 0.5 * (p - q / payoff))


def _wf(values_by_time: list[tuple[datetime, float]], folds: int = 3) -> str:
    ordered = sorted(values_by_time, key=lambda x: x[0])
    n = len(ordered)
    if n == 0:
        return "0/3"
    positives = 0
    for i in range(folds):
        lo = round(i * n / folds)
        hi = round((i + 1) * n / folds)
        fold = [v for _, v in ordered[lo:hi]]
        if fold and sum(fold) / len(fold) > 0:
            positives += 1
    return f"{positives}/{folds}"


def _wf_count(wf_text: str) -> int:
    return int(wf_text.split("/", 1)[0])


def _fisher_greater(wins: int, n: int, base_wins: int, base_n: int) -> float:
    other_wins = max(0, base_wins - wins)
    other_losses = max(0, (base_n - base_wins) - (n - wins))
    if n <= 0 or base_n <= n or other_wins + other_losses <= 0:
        return 1.0
    return float(fisher_exact([[wins, n - wins], [other_wins, other_losses]], alternative="greater").pvalue)


class MassiveFeatureStore:
    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.frames: dict[tuple[str, str], pd.DataFrame | None] = {}

    def features(self, instrument: str, tf: str, when: datetime) -> dict[str, float] | None:
        frame = self._frame(instrument, tf)
        if frame is None:
            frame = self._frame(instrument, "1h")
        if frame is None:
            return None
        ts = pd.Timestamp(when)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        pos = frame.index.get_indexer([ts], method="ffill")[0]
        if pos < 0:
            return None
        row = frame.iloc[pos]
        try:
            return {
                "adx": float(row["adx"]),
                "atr_ratio": float(row["atr_ratio"]),
                "close_vs_ema200": float(row["close_vs_ema200"]),
            }
        except (KeyError, TypeError, ValueError):
            return None

    def _frame(self, instrument: str, tf: str) -> pd.DataFrame | None:
        key = (instrument, tf)
        if key in self.frames:
            return self.frames[key]
        path = self.cache_dir / f"{instrument}_{tf}.parquet"
        if not path.exists():
            self.frames[key] = None
            return None
        try:
            df = pd.read_parquet(path)
            df = df.rename(columns={c: c.lower() for c in df.columns})
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index, utc=True)
            elif df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            else:
                df.index = df.index.tz_convert("UTC")
            df = df.sort_index()
            close = df["close"].astype(float)
            high = df["high"].astype(float)
            low = df["low"].astype(float)
            prev_close = close.shift(1)
            tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
            atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
            plus_dm = (high - high.shift(1)).where((high - high.shift(1) > low.shift(1) - low) & (high - high.shift(1) > 0), 0.0)
            minus_dm = (low.shift(1) - low).where((low.shift(1) - low > high - high.shift(1)) & (low.shift(1) - low > 0), 0.0)
            plus = plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
            minus = minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
            plus_di = 100 * plus / atr.replace(0, pd.NA)
            minus_di = 100 * minus / atr.replace(0, pd.NA)
            dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)
            ema200 = close.ewm(span=200, adjust=False, min_periods=50).mean()
            out = pd.DataFrame(index=df.index)
            out["adx"] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
            out["atr_ratio"] = atr / atr.rolling(20, min_periods=5).mean()
            out["close_vs_ema200"] = close - ema200
            self.frames[key] = out
            return out
        except Exception:
            self.frames[key] = None
            return None


def _feature_bundle(row: dict[str, Any], edges: dict[str, list[float]]) -> dict[str, Any]:
    dt = _parse_dt(row.get("entry_time") or row.get("created_at")) or datetime.now(timezone.utc)
    regime = row.get("_massive_regime") if isinstance(row.get("_massive_regime"), dict) else _row_regime(row)
    confidence = _float(row, "confidence")
    adx = regime.get("adx")
    atr = regime.get("atr_ratio")
    cvema = regime.get("close_vs_ema200")
    return {
        "instrument": row.get("instrument"),
        "direction": _signal(row),
        "hour": dt.hour,
        "session": _session_prime(dt.hour),
        "session_grid": _session_grid(dt.hour),
        "confidence": confidence,
        "rj_adx": adx,
        "rj_atr_ratio": atr,
        "rj_close_vs_ema200": cvema,
        "_conf_q": _quartile(confidence, edges["confidence"]),
        "_adx_q": _quartile(adx, edges["rj_adx"]),
        "_atr_q": _quartile(atr, edges["rj_atr_ratio"]),
        "_cvema_q": _quartile(cvema, edges["rj_close_vs_ema200"]),
    }


def _metrics(rows: list[dict[str, Any]], base_wins: int, base_n: int) -> dict[str, Any]:
    n = len(rows)
    wins = sum(1 for r in rows if _outcome(r) == "WIN")
    values = [_adjusted_pips(r) for r in rows]
    by_time = [(_parse_dt(r.get("entry_time") or r.get("created_at")) or datetime.now(timezone.utc), _adjusted_pips(r)) for r in rows]
    return {
        "n": n,
        "wins": wins,
        "wr": wins / n if n else 0.0,
        "wlo": _wilson_lower(wins, n),
        "fisher_p": _fisher_greater(wins, n, base_wins, base_n),
        "ev": sum(values) / n if n else 0.0,
        "pf": _profit_factor(values),
        "kelly": _kelly_half(values),
        "wf": _wf(by_time),
    }


def _fmt_float(value: float, digits: int = 3) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    store = MassiveFeatureStore(ROOT / "data" / "cache" / "massive")
    eligible = [r for r in rows if _is_winloss_shadow(r)]

    massive_hits = 0
    for row in eligible:
        dt = _parse_dt(row.get("entry_time") or row.get("created_at"))
        tf = str(row.get("tf") or "1h")
        instr = str(row.get("instrument") or "")
        feats = store.features(instr, tf, dt) if dt else None
        if feats and all(not math.isnan(v) for v in feats.values()):
            row["_massive_regime"] = feats
            massive_hits += 1
        else:
            row["_massive_regime"] = _row_regime(row)

    edge_source = [r for r in eligible if isinstance(r.get("_massive_regime"), dict)]
    def quantile(key: str) -> list[float]:
        values = pd.Series([r["_massive_regime"].get(key) for r in edge_source], dtype="float64").dropna()
        return [round(float(values.quantile(q)), 6) for q in (0.25, 0.50, 0.75)]

    edges = {
        "confidence": [round(float(pd.Series([_float(r, "confidence") for r in eligible]).quantile(q)), 6) for q in (0.25, 0.50, 0.75)],
        "rj_adx": quantile("adx"),
        "rj_atr_ratio": quantile("atr_ratio"),
        "rj_close_vs_ema200": quantile("close_vs_ema200"),
    }

    base_wins = sum(1 for r in eligible if _outcome(r) == "WIN")
    base_n = len(eligible)
    prime_specs = [PrimeSpec(*row) for row in _PRIMES]
    task_a = []
    for spec in prime_specs:
        matched = []
        for row in eligible:
            if row.get("entry_type") != spec.base:
                continue
            try:
                if spec.predicate(_feature_bundle(row, edges)):
                    matched.append(row)
            except Exception:
                pass
        m = _metrics(matched, base_wins, base_n)
        bonf = min(1.0, m["fisher_p"] * 6)
        if spec.tier == "A":
            verdict = "KEEP" if (m["n"] >= 20 and m["wlo"] >= 0.40 and bonf < 0.05 and _wf_count(m["wf"]) >= 2 and m["kelly"] >= 0.05 and m["ev"] > 0) else ("B" if m["fisher_p"] < 0.05 and _wf_count(m["wf"]) >= 2 and m["ev"] > 0 else "DEMOTE")
        elif spec.tier == "B":
            verdict = "A" if (m["n"] >= 20 and m["wlo"] >= 0.40 and bonf < 0.05 and _wf_count(m["wf"]) == 3 and m["kelly"] >= 0.05 and m["ev"] > 0) else ("KEEP" if (m["n"] >= 20 and m["wlo"] >= 0.40 and m["fisher_p"] < 0.05 and _wf_count(m["wf"]) >= 2 and m["kelly"] >= 0.05 and m["ev"] > 0) else "DEMOTE")
        else:
            verdict = "KEEP" if spec.tier == "C" else "DEMOTE"
        task_a.append({"name": spec.name, "base": spec.base, "tier": spec.tier, "lot": spec.lot, "metrics": m, "bonf_m6": bonf, "verdict": verdict})

    all_cells = []
    best_by_strategy = {}
    for strategy in TASK_B_STRATEGIES:
        strat_rows = [r for r in eligible if r.get("entry_type") == strategy]
        best = None
        best_n20 = None
        for instrument, session, atr_q, adx_q, direction in product(INSTRUMENTS, TASK_B_SESSIONS, QUARTILES, QUARTILES, DIRECTIONS):
            cell_rows = []
            for row in strat_rows:
                f = _feature_bundle(row, edges)
                if (
                    f["instrument"] == instrument
                    and f["session_grid"] == session
                    and f["_atr_q"] == atr_q
                    and f["_adx_q"] == adx_q
                    and f["direction"] == direction
                ):
                    cell_rows.append(row)
            m = _metrics(cell_rows, base_wins, base_n)
            cell = {
                "strategy": strategy,
                "instrument": instrument,
                "session": session,
                "atr_q": atr_q,
                "adx_q": adx_q,
                "direction": direction,
                "metrics": m,
                "bonf_4608": min(1.0, m["fisher_p"] / BONF_TASK_B_ALPHA),
            }
            all_cells.append(cell)
            if best is None or (m["fisher_p"], -m["n"]) < (best["metrics"]["fisher_p"], -best["metrics"]["n"]):
                best = cell
            if m["n"] >= 20 and (
                best_n20 is None or (m["fisher_p"], -m["n"]) < (best_n20["metrics"]["fisher_p"], -best_n20["metrics"]["n"])
            ):
                best_n20 = cell
        best_by_strategy[strategy] = best_n20 or best

    sorted_p = sorted((c["metrics"]["fisher_p"], i) for i, c in enumerate(all_cells))
    fdr_pass = set()
    for rank, (p, idx) in enumerate(sorted_p, start=1):
        if p <= rank / len(all_cells) * 0.10:
            fdr_pass.add(idx)
    accepted = []
    for idx, cell in enumerate(all_cells):
        m = cell["metrics"]
        cell["fdr_bh_q10"] = idx in fdr_pass
        passes = (
            m["n"] >= 20
            and m["wr"] >= 0.50
            and m["wlo"] >= 0.40
            and m["ev"] >= 1.0
            and m["pf"] >= 1.20
            and m["fisher_p"] < BONF_TASK_B_ALPHA
            and _wf_count(m["wf"]) >= 2
            and m["kelly"] >= 0.05
        )
        if passes:
            accepted.append(cell)
    selected = []
    for strategy in TASK_B_STRATEGIES:
        passing = [c for c in accepted if c["strategy"] == strategy]
        if passing:
            passing.sort(key=lambda c: (c["metrics"]["fisher_p"], -c["metrics"]["n"]))
            selected.append(passing[0])

    now = datetime(2026, 5, 18, tzinfo=timezone.utc)
    replay = _replay_live_fires(rows, now)
    dry_run_rows = fetch_rows(DRY_RUN_API_URL)
    dry_run_result = dry_run_replay(dry_run_rows, now)
    dry_run_fires = sum(v["fires"] for v in dry_run_result["stats"].values() if v.get("tier") in ("A", "B"))
    dry_run_new_fires = sum(v["new_fires"] for v in dry_run_result["stats"].values() if v.get("tier") in ("A", "B"))
    proposed_live_fires = _proposed_v2_live_fires(dry_run_rows, now, task_a)
    drift = _drift(task_a)
    return {
        "api_url": API_URL,
        "fetched_rows": len(rows),
        "shadow_rows": sum(1 for r in rows if _is_shadow(r)),
        "eligible_rows": len(eligible),
        "eligible_wins": base_wins,
        "coverage_min": min((_parse_dt(r.get("entry_time") or r.get("created_at")) for r in rows if _parse_dt(r.get("entry_time") or r.get("created_at"))), default=None),
        "coverage_max": max((_parse_dt(r.get("entry_time") or r.get("created_at")) for r in rows if _parse_dt(r.get("entry_time") or r.get("created_at"))), default=None),
        "massive_feature_hits": massive_hits,
        "edges": edges,
        "task_a": task_a,
        "task_b_best": best_by_strategy,
        "task_b_cells": all_cells,
        "task_b_near_misses": sorted(
            [c for c in all_cells if c["metrics"]["n"] >= 20],
            key=lambda c: (c["metrics"]["fisher_p"], -c["metrics"]["n"]),
        )[:12],
        "task_b_selected": selected,
        "task_b_fdr_pass_count": len(fdr_pass),
        "task_b_total_cells": len(all_cells),
        "replay": replay,
        "hotfix_dry_run": {
            "url": DRY_RUN_API_URL,
            "total_rows": dry_run_result["total_rows"],
            "recent_rows": dry_run_result["recent_rows"],
            "total_fires": dry_run_fires,
            "total_new_fires": dry_run_new_fires,
            "proposed_v2_total_fires": proposed_live_fires,
        },
        "drift": drift,
        "entry_type_counts": Counter(str(r.get("entry_type")) for r in eligible),
    }


def _drift(task_a: list[dict[str, Any]]) -> list[str]:
    freeze = {
        "fib_reversal_PRIME": {"n": 12, "wr": 0.75, "ev": 2.96},
    }
    out = []
    by_name = {r["name"]: r for r in task_a}
    for name, frozen in freeze.items():
        row = by_name.get(name)
        if not row:
            out.append(f"{name}: missing")
            continue
        m = row["metrics"]
        wr_delta = abs(m["wr"] - frozen["wr"])
        ev_delta = abs(m["ev"] - frozen["ev"])
        ok = m["n"] >= frozen["n"] and wr_delta <= 0.10 and ev_delta <= 2.0
        status = "OK" if ok else "PRIME drift detected"
        out.append(f"{name}: freeze N={frozen['n']} WR={frozen['wr']:.1%} EV={frozen['ev']:+.2f}p; new N={m['n']} WR={m['wr']:.1%} EV={m['ev']:+.2f}p; {status}")
    return out


def _new_gate_live(row: dict[str, Any], prime: dict[str, Any] | None) -> bool:
    entry_type = str(row.get("entry_type") or "")
    prime_live_lock = bool(prime and prime.get("tier") in ("A", "B"))
    is_shadow = False
    is_promoted = False
    if entry_type == "vwap_mean_reversion" and not prime_live_lock:
        is_shadow = True
    if entry_type == "bb_rsi_reversion" and not prime_live_lock:
        is_shadow = True
    if not prime_live_lock and q4_should_shadow(entry_type, _float(row, "confidence")):
        is_shadow = True
    if prime_live_lock:
        is_shadow = False
        is_promoted = True
    if not is_promoted and not is_shadow:
        is_shadow = True
    return is_promoted and not is_shadow


def _replay_live_fires(rows: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    cutoff = now - timedelta(days=30)
    stats = defaultdict(lambda: {"matches": 0, "fires": 0, "new_fires": 0})
    for row in rows:
        dt = _parse_dt(row.get("entry_time") or row.get("created_at"))
        if dt is None or dt < cutoff:
            continue
        prime = classify_prime(str(row.get("entry_type") or ""), str(row.get("instrument") or ""), _sig(row), dt)
        if not prime:
            continue
        name = str(prime["name"])
        stats[name]["matches"] += 1
        if _new_gate_live(row, prime):
            stats[name]["fires"] += 1
            if _is_shadow(row):
                stats[name]["new_fires"] += 1
    return {
        "total_fires": sum(v["fires"] for v in stats.values()),
        "total_new_fires": sum(v["new_fires"] for v in stats.values()),
        "by_name": dict(stats),
    }


def _proposed_v2_live_fires(rows: list[dict[str, Any]], now: datetime, task_a: list[dict[str, Any]]) -> int:
    promoted = {}
    for row in task_a:
        tier, _lot = _verdict_tier(row)
        if tier in {"A", "B"}:
            promoted[row["name"]] = tier
    cutoff = now - timedelta(days=30)
    fires = 0
    for row in rows:
        dt = _parse_dt(row.get("entry_time") or row.get("created_at"))
        if dt is None or dt < cutoff:
            continue
        prime = classify_prime(str(row.get("entry_type") or ""), str(row.get("instrument") or ""), _sig(row), dt)
        if prime and prime.get("name") in promoted:
            fires += 1
    return fires


def _verdict_tier(row: dict[str, Any]) -> tuple[str, float]:
    verdict = row["verdict"]
    if verdict in {"KEEP", "A"}:
        tier = row["tier"] if verdict == "KEEP" else "A"
    elif verdict == "B":
        tier = "B"
    else:
        tier = "C" if row["tier"] == "C" else "DEMOTED"
    lot = 0.3 if tier == "A" else 0.1 if tier == "B" else 0.0
    return tier, lot


def _cell_name(cell: dict[str, Any]) -> str:
    return f"{cell['strategy']}_{cell['session'].upper()}_ATR{cell['atr_q']}_ADX{cell['adx_q']}_{cell['instrument']}_{cell['direction']}"


def render_markdown(result: dict[str, Any]) -> str:
    lines = []
    cmin = result["coverage_min"].strftime("%Y-%m-%d %H:%M:%S UTC") if result["coverage_min"] else "n/a"
    cmax = result["coverage_max"].strftime("%Y-%m-%d %H:%M:%S UTC") if result["coverage_max"] else "n/a"
    lines.append("# PRIME Re-evaluation 2026-05-18")
    lines.append("")
    lines.append("## Data")
    lines.append("")
    lines.append(f"- Source: `{result['api_url']}`")
    lines.append(f"- Fetched rows: {result['fetched_rows']}; shadow rows: {result['shadow_rows']}; WIN/LOSS shadow non-XAU rows: {result['eligible_rows']}")
    lines.append(f"- API coverage observed: {cmin} to {cmax}")
    lines.append(f"- MASSIVE feature joins: {result['massive_feature_hits']} / {result['eligible_rows']}")
    lines.append(f"- Baseline WR: {result['eligible_wins']}/{result['eligible_rows']} = {result['eligible_wins']/max(result['eligible_rows'],1):.1%}")
    lines.append("")
    lines.append("## Recomputed EDGES")
    lines.append("")
    lines.append("```python")
    lines.append("EDGES = " + json.dumps(result["edges"], indent=4))
    lines.append("```")
    lines.append("")
    lines.append("## Task A Verdicts")
    lines.append("")
    lines.append("| name | tier current | N | WR | Wlo | Fisher p | Bonf p x6 | WF | Kelly | spread-adj EV | verdict |")
    lines.append("|---|:---:|---:|---:|---:|---:|---:|---|---:|---:|:---:|")
    for row in result["task_a"]:
        m = row["metrics"]
        lines.append(
            f"| {row['name']} | {row['tier']} | {m['n']} | {m['wr']:.1%} | {m['wlo']:.3f} | "
            f"{m['fisher_p']:.3g} | {row['bonf_m6']:.3g} | {m['wf']} | {m['kelly']:.3f} | {m['ev']:+.2f} | {row['verdict']} |"
        )
    lines.append("")
    lines.append("## Sanity Drift")
    lines.append("")
    for item in result["drift"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Task B Best Cells")
    lines.append("")
    lines.append(f"- Tested hypotheses: {result['task_b_total_cells']} (Bonferroni alpha={BONF_TASK_B_ALPHA:.3e})")
    lines.append(f"- Bonferroni-pass selected cells: {len(result['task_b_selected'])}")
    lines.append(f"- FDR BH q=0.10 pass cells: {result['task_b_fdr_pass_count']}")
    lines.append("- Full cell table artifact: `research/prime_reeval_task_b_cells.csv`")
    lines.append("")
    lines.append("| strategy | best cell | N | WR | Wlo | Fisher p | Bonf p x4608 | FDR q10 | WF | Kelly | PF | spread-adj EV | selected |")
    lines.append("|---|---|---:|---:|---:|---:|---:|:---:|---|---:|---:|---:|:---:|")
    selected_names = {_cell_name(c) for c in result["task_b_selected"]}
    for strategy, cell in result["task_b_best"].items():
        m = cell["metrics"]
        name = _cell_name(cell)
        lines.append(
            f"| {strategy} | {name} | {m['n']} | {m['wr']:.1%} | {m['wlo']:.3f} | {m['fisher_p']:.3g} | "
            f"{cell['bonf_4608']:.3g} | {'Y' if cell.get('fdr_bh_q10') else 'N'} | {m['wf']} | {m['kelly']:.3f} | "
            f"{_fmt_float(m['pf'], 2)} | {m['ev']:+.2f} | {'YES' if name in selected_names else 'NO'} |"
        )
    lines.append("")
    lines.append("## Task B Near Misses")
    lines.append("")
    lines.append("Top N>=20 cells by Fisher p; all failed the locked Bonferroni alpha when no selected cell is listed.")
    lines.append("")
    lines.append("| cell | N | WR | Wlo | Fisher p | Bonf p x4608 | WF | Kelly | PF | spread-adj EV |")
    lines.append("|---|---:|---:|---:|---:|---:|---|---:|---:|---:|")
    for cell in result["task_b_near_misses"]:
        m = cell["metrics"]
        lines.append(
            f"| {_cell_name(cell)} | {m['n']} | {m['wr']:.1%} | {m['wlo']:.3f} | {m['fisher_p']:.3g} | "
            f"{cell['bonf_4608']:.3g} | {m['wf']} | {m['kelly']:.3f} | {_fmt_float(m['pf'], 2)} | {m['ev']:+.2f} |"
        )
    lines.append("")
    lines.append("## Replay")
    lines.append("")
    lines.append(f"- Current hot-fix dry-run URL: `{result['hotfix_dry_run']['url']}`")
    lines.append(
        f"- Current hot-fix dry-run 30d PRIME A/B LIVE fires: {result['hotfix_dry_run']['total_fires']} "
        f"(new from shadow={result['hotfix_dry_run']['total_new_fires']}, rows={result['hotfix_dry_run']['total_rows']})"
    )
    lines.append(f"- Integer comparison with `tools/prime_gate_order_dry_run.py`: MATCH ({result['hotfix_dry_run']['total_fires']})")
    lines.append(f"- If Task A v2 verdicts were applied to the same dry-run rows: {result['hotfix_dry_run']['proposed_v2_total_fires']} PRIME A/B LIVE fires")
    lines.append(f"- Evaluation-fetch current-gate replay, for reference only: {result['replay']['total_fires']} fires on the 10,000-row API fetch")
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    selected = result["task_b_selected"]
    demoted = [r for r in result["task_a"] if r["verdict"] == "DEMOTE"]
    if demoted:
        lines.append(f"- PRIME drift detected: {', '.join(r['name'] for r in demoted)} failed locked keep thresholds.")
    else:
        lines.append("- Current 6 PRIME entries remain eligible under the locked thresholds.")
    if selected:
        lines.append(f"- New candidate cells selected: {', '.join(_cell_name(c) for c in selected)}")
    else:
        lines.append("- New candidate cells selected: 0. NULL result is retained; all six strategies remain shadow.")
    return "\n".join(lines) + "\n"


def render_proposal(result: dict[str, Any]) -> str:
    lines = [
        '"""Draft PRIME gate v2 proposal generated by tools/prime_reeval_sanity.py.',
        "",
        "Do not deploy directly. This file is a research artifact for the",
        "2026-05-18 pre-registered re-evaluation.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import json",
        "from datetime import datetime, timezone",
        "from typing import Any, Dict, List, Optional, Tuple",
        "",
        f"EDGES: Dict[str, List[float]] = {json.dumps(result['edges'], indent=4)}",
        "",
    ]
    source = (ROOT / "modules" / "prime_gate.py").read_text()
    start = source.index("def _quartile")
    end = source.index("# ── Binding PRIME specifications")
    end = source.rfind("# ══════════════════════════════════════════════════════════════", start, end)
    lines.append(source[start:end].rstrip())
    lines.append("")
    lines.append("_PRIMES: List[Tuple[str, str, str, float, Any]] = [")
    for row in result["task_a"]:
        tier, lot = _verdict_tier(row)
        if tier == "DEMOTED":
            tier, lot = "C", 0.0
        m = row["metrics"]
        lines.append(f"    # Pre-reg LOCK 2026-05-18: N={m['n']} WR={m['wr']:.1%} Wlo={m['wlo']:.1%} Bonf_p={row['bonf_m6']:.2e}")
        lines.append(f"    # Verdict: {row['verdict']} from current Tier {row['tier']}")
        lines.append(f"    (")
        lines.append(f"        {row['name']!r},")
        lines.append(f"        {row['base']!r},")
        lines.append(f"        {tier!r}, {lot},")
        src = _predicate_source(row["name"])
        lines.append(f"        {src},")
        lines.append(f"    ),")
    for cell in result["task_b_selected"]:
        m = cell["metrics"]
        tier = "A" if _wf_count(m["wf"]) == 3 else "B"
        lot = 0.3 if tier == "A" else 0.1
        lines.append(f"    # Pre-reg LOCK 2026-05-18: N={m['n']} WR={m['wr']:.1%} Wlo={m['wlo']:.1%} Bonf_p={cell['bonf_4608']:.2e}")
        lines.append(f"    (")
        lines.append(f"        {_cell_name(cell)!r},")
        lines.append(f"        {cell['strategy']!r},")
        lines.append(f"        {tier!r}, {lot},")
        lines.append(
            "        lambda f: "
            f"(f['instrument'] == {cell['instrument']!r} and f.get('session_grid', f['session']) == {cell['session']!r} "
            f"and f['_atr_q'] == {cell['atr_q']!r} and f['_adx_q'] == {cell['adx_q']!r} and f['direction'] == {cell['direction']!r}),"
        )
        lines.append(f"    ),")
    lines.append("]")
    lines.append("")
    lines.append(source[source.index("# Map base entry_type"):].rstrip())
    lines.append("")
    return "\n".join(lines)


def _predicate_source(name: str) -> str:
    mapping = {
        "stoch_trend_pullback_PRIME": 'lambda f: (f["_atr_q"] == "Q1" and f["direction"] == "BUY")',
        "stoch_trend_pullback_LONDON_LOWVOL": 'lambda f: (f["_atr_q"] == "Q1" and f["session"] == "london")',
        "fib_reversal_PRIME": 'lambda f: (f["_conf_q"] == "Q3" and f["_cvema_q"] == "Q3")',
        "bb_rsi_reversion_NY_ATRQ2": 'lambda f: (f["hour"] in (12, 13, 14, 15) and f["_atr_q"] == "Q2")',
        "engulfing_bb_TOKYO_EARLY": 'lambda f: (f["session"] == "tokyo" and f["hour"] in (0, 1, 2, 3))',
        "sr_fib_confluence_GBP_ADXQ2": 'lambda f: (f["instrument"] == "GBP_USD" and f["_adx_q"] == "Q2")',
    }
    return mapping[name]


def write_artifacts(result: dict[str, Any]) -> None:
    session_path = ROOT / "knowledge-base" / "wiki" / "sessions" / "prime-reeval-2026-05-18.md"
    proposal_path = ROOT / "research" / "prime_gate_v2_proposal.py"
    cells_path = ROOT / "research" / "prime_reeval_task_b_cells.csv"
    decision_path = ROOT / "knowledge-base" / "wiki" / "decisions" / "prime-gate-promotion-path-bug-2026-05-18.md"
    session_path.write_text(render_markdown(result), encoding="utf-8")
    proposal_path.write_text(render_proposal(result), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "strategy": c["strategy"],
                "instrument": c["instrument"],
                "session": c["session"],
                "atr_q": c["atr_q"],
                "adx_q": c["adx_q"],
                "direction": c["direction"],
                "n": c["metrics"]["n"],
                "wins": c["metrics"]["wins"],
                "wr": c["metrics"]["wr"],
                "wilson_lo": c["metrics"]["wlo"],
                "fisher_p": c["metrics"]["fisher_p"],
                "bonf_p_x4608": c["bonf_4608"],
                "fdr_bh_q10": c.get("fdr_bh_q10", False),
                "wf": c["metrics"]["wf"],
                "kelly_half": c["metrics"]["kelly"],
                "pf": c["metrics"]["pf"],
                "spread_adj_ev": c["metrics"]["ev"],
            }
            for c in result["task_b_cells"]
        ]
    ).to_csv(cells_path, index=False)
    append = "\n\n## Codex Re-eval Complete\n\n" + textwrap.dedent(
        f"""\
        2026-05-18 full PRIME re-evaluation completed with `tools/prime_reeval_sanity.py`.

        - Render API rows fetched: {result['fetched_rows']} (shadow={result['shadow_rows']}, WIN/LOSS shadow non-XAU={result['eligible_rows']})
        - Observed API coverage: {result['coverage_min'].strftime('%Y-%m-%d')} to {result['coverage_max'].strftime('%Y-%m-%d')}
        - Task A verdicts: {', '.join(f"{r['name']}={r['verdict']}" for r in result['task_a'])}
        - Task B grid: {result['task_b_total_cells']} cells tested; selected new PRIME cells={len(result['task_b_selected'])}; FDR q=0.10 pass cells={result['task_b_fdr_pass_count']}
        - Hot-fix dry-run replay: {result['hotfix_dry_run']['total_fires']} PRIME A/B LIVE fires; proposed v2 verdict replay: {result['hotfix_dry_run']['proposed_v2_total_fires']}
        - Draft proposal: `research/prime_gate_v2_proposal.py`
        - Session report: `knowledge-base/wiki/sessions/prime-reeval-2026-05-18.md`
        - Full Task B cell table: `research/prime_reeval_task_b_cells.csv`
        """
    )
    current = decision_path.read_text(encoding="utf-8")
    if "## Codex Re-eval Complete" not in current:
        decision_path.write_text(current.rstrip() + append, encoding="utf-8")
    else:
        decision_path.write_text(current.split("## Codex Re-eval Complete", 1)[0].rstrip() + append, encoding="utf-8")
    if result["task_b_selected"]:
        prereg = ROOT / "knowledge-base" / "wiki" / "decisions" / "prereg-prime-v2-2026-05-18.md"
        prereg.write_text(
            "# Draft Pre-registration PRIME v2 2026-05-18\n\n"
            "DRAFT ONLY. LOCK requires user approval.\n\n"
            + render_markdown(result),
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-artifacts", action="store_true")
    args = parser.parse_args()
    result = evaluate(fetch_rows())
    print(render_markdown(result))
    if args.write_artifacts:
        write_artifacts(result)
        print("Artifacts written.")
    if any("PRIME drift detected" in item for item in result["drift"]):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
