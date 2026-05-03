#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("BT_MODE", "1")
os.environ.setdefault("NO_AUTOSTART", "1")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import modules.bt_vec_harness as vec_harness
from modules.bt_vec_harness import HtfFeatureSpec, VecBacktestRunner, _load_local_cache
from tools.bt_common import compute_wrapper_fingerprint


SCHEMA_VERSION = 1
DATA_SOURCE = "parquet_cache"
LIVE_SEPARATION = "bt_only"
HARNESS_NAME = "vec_harness_chunked_cli_v2"
SUPPORTED_LOOKBACKS = {7, 14, 30, 60, 90, 180}
SUPPORTED_INTERVALS = {"1m", "5m", "15m", "M15"}
DEFAULT_STATE_ROOT = ROOT / "tools" / "vec_harness_chunked_state"


@dataclass(frozen=True)
class RunConfig:
    pair: str
    strategy: str
    interval: str
    lookback: int
    chunk_days: int
    state_dir: Path
    output: Path


def normalize_pair(pair: str) -> str:
    value = (pair or "").upper().replace("=X", "").replace("/", "_")
    if "_" in value:
        return value
    if len(value) == 6:
        return f"{value[:3]}_{value[3:]}"
    return value


def yahoo_symbol(pair: str) -> str:
    return normalize_pair(pair).replace("_", "") + "=X"


def parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def harness_version() -> str:
    try:
        self_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    except Exception:
        self_hash = "unknown"
    return f"{HARNESS_NAME}-{self_hash}"


def state_hash(cfg: RunConfig) -> str:
    payload = {
        "pair": cfg.pair,
        "interval": cfg.interval,
        "strategy": cfg.strategy,
        "lookback": cfg.lookback,
        "chunk_days": cfg.chunk_days,
        "harness_version": harness_version(),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def default_state_dir(pair: str, strategy: str, interval: str, lookback: int, chunk_days: int) -> Path:
    raw = json.dumps(
        {
            "pair": normalize_pair(pair),
            "strategy": strategy,
            "interval": interval,
            "lookback": lookback,
            "chunk_days": chunk_days,
            "harness": HARNESS_NAME,
        },
        sort_keys=True,
    )
    run_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return DEFAULT_STATE_ROOT / run_id


def validate_args(cfg: RunConfig) -> None:
    if cfg.interval not in SUPPORTED_INTERVALS:
        raise SystemExit(f"unsupported --interval {cfg.interval}; expected one of {sorted(SUPPORTED_INTERVALS)}")
    if cfg.lookback not in SUPPORTED_LOOKBACKS:
        raise SystemExit(f"unsupported --lookback {cfg.lookback}; expected one of {sorted(SUPPORTED_LOOKBACKS)}")
    if cfg.chunk_days < 7 or cfg.chunk_days > 60:
        raise SystemExit("--chunk-days must be in 7..60")
    if cfg.chunk_days > cfg.lookback:
        raise SystemExit("--chunk-days must be <= --lookback")
    if _load_local_cache(yahoo_symbol(cfg.pair), cfg.interval, cfg.lookback) is None:
        raise SystemExit(
            f"local parquet cache missing or too small for pair={cfg.pair} "
            f"interval={cfg.interval} lookback={cfg.lookback}"
        )
    resolve_strategy_class(cfg.strategy)


def resolve_strategy_class(strategy_name: str):
    from strategies.scalp import ScalperEngine

    strategy = ScalperEngine().get_strategy(strategy_name)
    if strategy is None:
        raise SystemExit(f"strategy not found in ScalperEngine registry: {strategy_name}")
    return strategy.__class__


def make_spec(strategy_name: str) -> HtfFeatureSpec:
    if strategy_name == "mtf_regime_trend_cascade_scalp":
        return HtfFeatureSpec(
            include_hurst_m15=True,
            include_range_20_m15=True,
            include_h1=True,
            inject_spread=2.14,
        )
    return HtfFeatureSpec()


def normalize_trade(trade: dict[str, Any]) -> dict[str, Any]:
    ts = parse_ts(trade.get("ts"))
    signal = str(trade.get("signal", trade.get("side", ""))).upper()
    return {
        "ts": ts.isoformat(),
        "side": "long" if signal in {"BUY", "LONG"} else "short",
        "pnl_pip": round(float(trade.get("pnl_pips", trade.get("pnl_pip", 0.0))), 6),
    }


def run_single_shot(pair: str, strategy_name: str, interval: str, lookback_days: int) -> list[dict[str, Any]]:
    if interval not in {"1m", "5m"}:
        raise RuntimeError(f"VecBacktestRunner base bar is 1m; unsupported wrapper interval={interval}")
    strategy_cls = resolve_strategy_class(strategy_name)
    runner = VecBacktestRunner(
        spec=make_spec(strategy_name),
        strategy_factory=strategy_cls,
    )
    result = runner.run(symbol=yahoo_symbol(pair), days=lookback_days, verbose=False)
    return [normalize_trade(t) for t in result.get("trades_full", [])]


def _prepare_frames(cfg: RunConfig) -> tuple[Any, Any, bool]:
    symbol = yahoo_symbol(cfg.pair)
    if cfg.interval not in {"1m", "5m"}:
        raise RuntimeError(f"VecBacktestRunner base bar is 1m; unsupported wrapper interval={cfg.interval}")

    df_1m = vec_harness.load_1m(symbol, cfg.lookback, verbose=False)
    df_15 = vec_harness.load_htf(symbol, "M15", verbose=False)
    df_5 = vec_harness.load_htf(symbol, "M5", verbose=False)
    spec = make_spec(cfg.strategy)
    df_1h = _load_local_cache(symbol, "1h", days=0) if spec.include_h1 else None
    df_1m.attrs["symbol"] = symbol

    feat_15 = vec_harness.compute_m15_features(df_15, spec)
    feat_5 = vec_harness.compute_m5_features(df_5, spec)
    feat_1h = vec_harness.compute_h1_features(df_1h, spec) if df_1h is not None else None

    from modules.indicators import add_indicators

    df_1m = add_indicators(df_1m)
    feat_15_re = feat_15.reset_index().rename(columns={feat_15.index.name or "index": "ts"})
    feat_5_re = feat_5.reset_index().rename(columns={feat_5.index.name or "index": "ts"})
    df_1m_re = df_1m.reset_index().rename(columns={df_1m.index.name or "index": "ts"})
    for frame in (df_1m_re, feat_15_re, feat_5_re):
        frame["ts"] = vec_harness.pd.to_datetime(frame["ts"])
        frame.sort_values("ts", inplace=True)
    merged = vec_harness.pd.merge_asof(
        df_1m_re,
        feat_15_re.add_prefix("m15_").rename(columns={"m15_ts": "ts"}),
        on="ts",
        direction="backward",
    )
    merged = vec_harness.pd.merge_asof(
        merged,
        feat_5_re.add_prefix("m5_").rename(columns={"m5_ts": "ts"}),
        on="ts",
        direction="backward",
    )
    if feat_1h is not None:
        feat_1h_re = feat_1h.reset_index().rename(columns={feat_1h.index.name or "index": "ts"})
        feat_1h_re["ts"] = vec_harness.pd.to_datetime(feat_1h_re["ts"])
        feat_1h_re.sort_values("ts", inplace=True)
        merged = vec_harness.pd.merge_asof(
            merged,
            feat_1h_re.add_prefix("h1_").rename(columns={"h1_ts": "ts"}),
            on="ts",
            direction="backward",
        )
    return df_1m, merged.set_index("ts"), feat_1h is not None


def _chunk_end_indices(merged: Any, lookback: int, chunk_days: int) -> list[int]:
    plan = chunk_plan(lookback, chunk_days)
    start_ts = merged.index[0]
    ends: list[int] = []
    for chunk in plan:
        end_ts = start_ts + vec_harness.pd.Timedelta(days=chunk["end_day"])
        ends.append(int(merged.index.searchsorted(end_ts, side="left")))
    return [min(max(0, i), len(merged) - 60) for i in ends]


def _run_index_range(
    cfg: RunConfig,
    df_1m: Any,
    merged: Any,
    has_h1: bool,
    start_idx: int,
    stop_idx: int,
    last_exit_idx: int,
) -> tuple[list[dict[str, Any]], int, int]:
    spec = make_spec(cfg.strategy)
    strategy_cls = resolve_strategy_class(cfg.strategy)
    runner = VecBacktestRunner(spec=spec, strategy_factory=strategy_cls)
    runner._has_h1 = has_h1
    strat = runner.strategy_factory()
    if not getattr(strat, "enabled", True):
        return [], start_idx, last_exit_idx

    from strategies.context import SignalContext

    symbol = yahoo_symbol(cfg.pair)
    pip_mult = 100 if ("JPY" in symbol or "XAU" in symbol) else 10000
    trades: list[dict[str, Any]] = []
    i = max(runner.burn_in_bars, start_idx)
    hard_stop = min(stop_idx, len(merged) - 60)
    while i < hard_stop:
        if i <= last_exit_idx + runner.cooldown_bars:
            i += 1
            continue
        row = merged.iloc[i]
        m15_dict = {k: runner._coerce(row.get(f"m15_{k}"), k) for k in spec.m15_fields}
        m5_dict = {k: runner._coerce(row.get(f"m5_{k}"), k) for k in spec.m5_fields}
        h1_dict = (
            {k: runner._coerce(row.get(f"h1_{k}"), k) for k in spec.h1_fields}
            if has_h1 else {}
        )
        try:
            window = df_1m.iloc[max(0, i - runner.window_bars): i + 1]
            bar_time = window.index[-1]
            ctx = SignalContext.from_df(
                df=window,
                row=window.iloc[-1],
                symbol=symbol,
                tf="1m",
                sr_levels=[],
                layer0={},
                layer1={},
                regime={},
                layer2={},
                layer3={},
                htf={"m15": m15_dict, "m5": m5_dict, "h1": h1_dict, "h4": {}},
                session={},
                backtest_mode=True,
                bar_time=bar_time,
            )
            cand = strat.evaluate(ctx)
        except Exception:
            i += 1
            continue
        if cand is None:
            i += 1
            continue
        outcome, pnl_pips, exit_off = vec_harness.simulate_outcome(
            df_1m=df_1m,
            entry_idx=i,
            signal=cand.signal,
            entry_px=ctx.entry,
            sl=cand.sl,
            tp=cand.tp,
            pip_mult=pip_mult,
            max_bars=runner.max_hold_bars,
        )
        if spec.inject_spread > 0:
            pnl_pips -= spec.inject_spread
        trades.append(normalize_trade({
            "ts": str(window.index[-1]),
            "signal": cand.signal,
            "pnl_pips": pnl_pips,
            "outcome": outcome,
        }))
        last_exit_idx = i + exit_off
        i += 1
    return trades, hard_stop, last_exit_idx


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def load_or_create_manifest(cfg: RunConfig) -> tuple[dict[str, Any], bool]:
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cfg.state_dir / "manifest.json"
    expected = state_hash(cfg)
    if manifest_path.exists():
        manifest = read_json(manifest_path, {})
        if manifest.get("state_hash") != expected:
            raise SystemExit(
                f"state-dir hash mismatch: {cfg.state_dir} has {manifest.get('state_hash')} expected {expected}"
            )
        return manifest, True
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "state_hash": expected,
        "pair": cfg.pair,
        "strategy": cfg.strategy,
        "interval": cfg.interval,
        "lookback_days": cfg.lookback,
        "chunk_days": cfg.chunk_days,
        "harness_version": harness_version(),
        "data_source": DATA_SOURCE,
        "live_separation": LIVE_SEPARATION,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(manifest_path, manifest)
    return manifest, False


def cache_status(cfg: RunConfig) -> dict[str, Any]:
    df = _load_local_cache(yahoo_symbol(cfg.pair), cfg.interval, cfg.lookback)
    if df is None:
        return {"ok": False, "rows": 0, "start": None, "end": None}
    return {
        "ok": True,
        "rows": int(len(df)),
        "start": str(df.index.min()),
        "end": str(df.index.max()),
    }


def chunk_plan(lookback: int, chunk_days: int) -> list[dict[str, int]]:
    chunks = []
    start = 0
    idx = 1
    while start < lookback:
        end = min(lookback, start + chunk_days)
        chunks.append({"chunk": idx, "start_day": start, "end_day": end})
        start = end
        idx += 1
    return chunks


def _trade_chunk_index(trade: dict[str, Any], trades: list[dict[str, Any]], chunks: list[dict[str, int]]) -> int:
    if not trades:
        return 1
    first = parse_ts(trades[0]["ts"]).timestamp()
    last = parse_ts(trades[-1]["ts"]).timestamp()
    span = max(1.0, last - first)
    pos = (parse_ts(trade["ts"]).timestamp() - first) / span
    idx = int(pos * len(chunks)) + 1
    return max(1, min(len(chunks), idx))


def pf_from_pnls(pnls: list[float]) -> float | None:
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss <= 0:
        return None if gross_profit <= 0 else math.inf
    return gross_profit / gross_loss


def wilson_interval(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    p = wins / n
    den = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / den), min(1.0, (centre + margin) / den)


def max_drawdown(pnls: list[float]) -> tuple[float, float]:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    dd_pct = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            dd_pct = (dd / peak * 100.0) if peak > 0 else 0.0
    return round(max_dd, 6), round(dd_pct, 6)


def small_stats(trades: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [float(t["pnl_pip"]) for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    pf = pf_from_pnls(pnls)
    return {
        "n": n,
        "pf": None if pf is None else ("inf" if pf == math.inf else round(pf, 6)),
        "wr": round(wins / n, 6) if n else 0.0,
    }


def build_payload(
    cfg: RunConfig,
    trades: list[dict[str, Any]],
    chunks_completed: int,
    resumed: bool,
    wall_clock: float,
    data_status: str = "ok",
) -> dict[str, Any]:
    pnls = [float(t["pnl_pip"]) for t in trades]
    n = len(trades)
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    pf = pf_from_pnls(pnls)
    wlo, whi = wilson_interval(wins, n)
    dd_pip, dd_pct = max_drawdown(pnls)
    split = n // 2
    return {
        "schema_version": SCHEMA_VERSION,
        "wrapper_fingerprint": compute_wrapper_fingerprint(__file__),
        "data_source": DATA_SOURCE,
        "live_separation": LIVE_SEPARATION,
        "data_status": data_status,
        "pair": cfg.pair,
        "strategy": cfg.strategy,
        "interval": cfg.interval,
        "lookback_days": cfg.lookback,
        "chunk_days": cfg.chunk_days,
        "n": n,
        "wins": wins,
        "losses": losses,
        "wr": round(wins / n, 6) if n else 0.0,
        "ev_pip": round(sum(pnls) / n, 6) if n else 0.0,
        "pf": None if pf is None else ("inf" if pf == math.inf else round(pf, 6)),
        "wilson_lo": round(wlo, 6),
        "wilson_hi": round(whi, 6),
        "max_dd_pip": dd_pip,
        "max_dd_pct": dd_pct,
        "wf_50_50": {
            "is": small_stats(trades[:split]),
            "oos": small_stats(trades[split:]),
        },
        "trades": trades,
        "harness_version": harness_version(),
        "wall_clock_seconds_total": round(wall_clock, 6),
        "chunks_completed": chunks_completed,
        "resumed_from_checkpoint": resumed,
    }


def run_chunked(cfg: RunConfig, max_chunks: int | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    validate_args(cfg)
    manifest, resumed = load_or_create_manifest(cfg)
    status = cache_status(cfg)
    if not status["ok"]:
        payload = build_payload(cfg, [], 0, resumed, time.perf_counter() - started, data_status="cache_short")
        payload["cache_status"] = status
        write_json(cfg.output, payload)
        return payload

    chunks = chunk_plan(cfg.lookback, cfg.chunk_days)
    checkpoint_path = cfg.state_dir / "checkpoint.json"
    checkpoint = read_json(
        checkpoint_path,
        {
            "chunks_completed": 0,
            "next_index": 240,
            "last_exit_idx": -30,
            "wall_clock_seconds_total": 0.0,
        },
    )
    completed = int(checkpoint.get("chunks_completed", 0))
    completed_before = completed
    existing_trades = read_json(cfg.state_dir / "trades_so_far.json", [])
    if completed >= len(chunks):
        elapsed = time.perf_counter() - started
        wall_total = float(checkpoint.get("wall_clock_seconds_total", 0.0)) + elapsed
        payload = build_payload(cfg, existing_trades, completed, True, wall_total)
        payload["cache_status"] = status
        write_json(cfg.output, payload)
        print(
            f"chunked vec harness: chunks_completed={completed}/{len(chunks)} "
            f"n={payload['n']} state_dir={cfg.state_dir} output={cfg.output}",
            flush=True,
        )
        return payload

    df_1m, merged, has_h1 = _prepare_frames(cfg)
    end_indices = _chunk_end_indices(merged, cfg.lookback, cfg.chunk_days)
    chunks_to_run = len(chunks) - completed if max_chunks is None else max(0, min(max_chunks, len(chunks) - completed))
    next_index = int(checkpoint.get("next_index", 240))
    last_exit_idx = int(checkpoint.get("last_exit_idx", -30))
    new_trades: list[dict[str, Any]] = []
    for _ in range(chunks_to_run):
        stop_idx = end_indices[completed]
        chunk_trades, next_index, last_exit_idx = _run_index_range(
            cfg, df_1m, merged, has_h1, next_index, stop_idx, last_exit_idx
        )
        new_trades.extend(chunk_trades)
        completed += 1

    visible = sorted(existing_trades + new_trades, key=lambda t: t["ts"])
    last_ts = str(merged.index[min(max(next_index - 1, 0), len(merged) - 1)]) if len(merged) else None
    write_json(cfg.state_dir / "trades_so_far.json", visible)
    write_jsonl(cfg.state_dir / "trades_so_far.jsonl", visible)
    elapsed = time.perf_counter() - started
    wall_total = float(checkpoint.get("wall_clock_seconds_total", 0.0)) + elapsed
    write_json(
        checkpoint_path,
        {
            "chunks_completed": completed,
            "next_index": next_index,
            "last_exit_idx": last_exit_idx,
            "last_processed_bar_timestamp": last_ts,
            "state_hash": manifest["state_hash"],
            "wall_clock_seconds_total": wall_total,
        },
    )
    effective_resumed = resumed or completed_before > 0 or (max_chunks is None and chunks_to_run > 1)
    payload = build_payload(cfg, visible, completed, effective_resumed, wall_total)
    payload["cache_status"] = status
    write_json(cfg.output, payload)
    print(
        f"chunked vec harness: chunks_completed={completed}/{len(chunks)} "
        f"n={payload['n']} state_dir={cfg.state_dir} output={cfg.output}",
        flush=True,
    )
    return payload


def compare_trades(reference: list[dict[str, Any]], chunked: list[dict[str, Any]]) -> dict[str, Any]:
    if len(reference) != len(chunked):
        return {"verdict": "REJECT", "max_abs_pnl_diff": None, "reason": "N mismatch"}
    max_diff = 0.0
    timestamps_identical = True
    for a, b in zip(reference, chunked):
        max_diff = max(max_diff, abs(float(a["pnl_pip"]) - float(b["pnl_pip"])))
        if a["ts"] != b["ts"] or a["side"] != b["side"]:
            timestamps_identical = False
    if timestamps_identical and max_diff <= 1e-6:
        verdict = "ACCEPT"
    elif max_diff <= 1e-3:
        verdict = "NEEDS_MORE_EVIDENCE"
    else:
        verdict = "REJECT"
    return {"verdict": verdict, "max_abs_pnl_diff": max_diff, "reason": "ok"}


def run_equivalence(window: int, output: Path | None = None) -> dict[str, Any]:
    reference = run_single_shot(
        pair="USD_JPY",
        strategy_name="mtf_regime_trend_cascade_scalp",
        interval="5m",
        lookback_days=window,
    )
    out = output or ROOT / "knowledge-base/raw/bt-results/vec-harness-chunked-validation-2026-05-03.json"
    cfg = RunConfig(
        pair="USD_JPY",
        strategy="mtf_regime_trend_cascade_scalp",
        interval="5m",
        lookback=window,
        chunk_days=min(10, window),
        state_dir=DEFAULT_STATE_ROOT / f"validation-{window}d-{harness_version()}",
        output=out,
    )
    chunked = run_chunked(cfg)["trades"]
    cmp = compare_trades(reference, chunked)
    report = {
        "schema_version": SCHEMA_VERSION,
        "wrapper_fingerprint": compute_wrapper_fingerprint(__file__),
        "reference_window_days": window,
        "n_reference": len(reference),
        "n_chunked": len(chunked),
        **cmp,
    }
    write_json(out, report)
    md = out.with_suffix(".md")
    md.write_text(
        "\n".join(
            [
                "# Vec Harness Chunked Validation — 2026-05-03",
                "",
                f"- Reference window: `{window}d`",
                f"- N reference: `{len(reference)}`",
                f"- N chunked: `{len(chunked)}`",
                f"- max |pnl| diff: `{cmp['max_abs_pnl_diff']}` pip",
                f"- Verdict: `{cmp['verdict']}`",
                f"- Data source: `{DATA_SOURCE}`",
                f"- Live separation: `{LIVE_SEPARATION}`",
                "",
            ]
        )
    )
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chunked/resumable VecBacktestRunner CLI")
    parser.add_argument("--pair", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--interval", required=True)
    parser.add_argument("--lookback", required=True, type=int)
    parser.add_argument("--chunk-days", type=int, default=30)
    parser.add_argument("--state-dir")
    parser.add_argument("--output", required=True)
    parser.add_argument("--validate-equivalence-window", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    state_dir = Path(args.state_dir) if args.state_dir else default_state_dir(
        args.pair, args.strategy, args.interval, args.lookback, args.chunk_days
    )
    cfg = RunConfig(
        pair=normalize_pair(args.pair),
        strategy=args.strategy,
        interval=args.interval,
        lookback=args.lookback,
        chunk_days=args.chunk_days,
        state_dir=state_dir,
        output=Path(args.output),
    )
    validate_args(cfg)
    if args.dry_run:
        print(f"state_dir={cfg.state_dir}")
        print(f"chunks={chunk_plan(cfg.lookback, cfg.chunk_days)}")
        return 0
    if args.validate_equivalence_window:
        report = run_equivalence(args.validate_equivalence_window, cfg.output)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["verdict"] == "ACCEPT" else 2
    run_chunked(cfg, max_chunks=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
