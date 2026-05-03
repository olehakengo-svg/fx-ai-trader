from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest


def _load_cli():
    return importlib.import_module("tools.vec_harness_chunked_cli")


def _compact(trades):
    return [
        (
            t["ts"],
            t["side"],
            round(float(t["pnl_pip"]), 6),
        )
        for t in trades
    ]


def _patch_fast_chunk_runner(monkeypatch, cli, chunk_trades):
    merged = pd.DataFrame(
        {"Close": [150.0] * 10},
        index=pd.date_range("2026-01-01", periods=10, freq="min", tz="UTC"),
    )
    monkeypatch.setattr(cli, "cache_status", lambda cfg: {"ok": True, "rows": 10, "start": str(merged.index[0]), "end": str(merged.index[-1])})
    monkeypatch.setattr(cli, "_prepare_frames", lambda cfg: (merged, merged, False))
    monkeypatch.setattr(cli, "_chunk_end_indices", lambda merged_arg, lookback, chunk_days: list(range(1, len(cli.chunk_plan(lookback, chunk_days)) + 1)))

    def fake_run_index_range(cfg, df_1m, merged_arg, has_h1, start_idx, stop_idx, last_exit_idx):
        idx = max(0, min(stop_idx - 1, len(chunk_trades) - 1))
        return list(chunk_trades[idx]), stop_idx, stop_idx

    monkeypatch.setattr(cli, "_run_index_range", fake_run_index_range)


def test_chunked_equals_single_shot_30d(tmp_path, monkeypatch):
    cli = _load_cli()
    window = 30
    reference = [
        {"ts": "2026-01-01T00:00:00+00:00", "side": "long", "pnl_pip": 1.25},
        {"ts": "2026-01-11T00:00:00+00:00", "side": "short", "pnl_pip": -0.5},
        {"ts": "2026-01-21T00:00:00+00:00", "side": "long", "pnl_pip": 2.0},
    ]
    monkeypatch.setattr(cli, "run_single_shot", lambda **_: list(reference))
    _patch_fast_chunk_runner(monkeypatch, cli, [[t] for t in reference])

    output = tmp_path / "chunked.json"
    result = cli.run_chunked(
        cli.RunConfig(
            pair="USD_JPY",
            strategy="mtf_regime_trend_cascade_scalp",
            interval="5m",
            lookback=window,
            chunk_days=min(10, window),
            state_dir=tmp_path / "state",
            output=output,
        )
    )
    assert result["n"] == len(reference)
    assert _compact(result["trades"]) == _compact(reference)


def test_resume_idempotence(tmp_path, monkeypatch):
    cli = _load_cli()
    fake_trades = [
        {"ts": "2026-01-01T00:00:00+00:00", "side": "long", "pnl_pip": 1.25},
        {"ts": "2026-01-11T00:00:00+00:00", "side": "short", "pnl_pip": -0.5},
        {"ts": "2026-01-21T00:00:00+00:00", "side": "long", "pnl_pip": 2.0},
    ]
    monkeypatch.setattr(cli, "run_single_shot", lambda **_: list(fake_trades))
    _patch_fast_chunk_runner(monkeypatch, cli, [[t] for t in fake_trades])

    cfg = cli.RunConfig(
        pair="USD_JPY",
        strategy="mtf_regime_trend_cascade_scalp",
        interval="5m",
        lookback=30,
        chunk_days=10,
        state_dir=tmp_path / "state",
        output=tmp_path / "resume.json",
    )
    first = cli.run_chunked(cfg, max_chunks=1)
    assert first["chunks_completed"] == 1
    resumed = cli.run_chunked(cfg)
    full = cli.run_chunked(
        cli.RunConfig(
            pair=cfg.pair,
            strategy=cfg.strategy,
            interval=cfg.interval,
            lookback=cfg.lookback,
            chunk_days=cfg.chunk_days,
            state_dir=tmp_path / "state_full",
            output=tmp_path / "full.json",
        )
    )

    def stable_bytes(path: Path) -> bytes:
        data = json.loads(path.read_text())
        data["wall_clock_seconds_total"] = 0.0
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()

    assert resumed["resumed_from_checkpoint"] is True
    assert stable_bytes(cfg.output) == stable_bytes(tmp_path / "full.json")


def test_state_dir_hash_mismatch_aborts(tmp_path, monkeypatch):
    cli = _load_cli()
    monkeypatch.setattr(cli, "run_single_shot", lambda **_: [])
    _patch_fast_chunk_runner(monkeypatch, cli, [[] for _ in range(3)])
    state_dir = tmp_path / "state"
    output = tmp_path / "out.json"
    cli.run_chunked(
        cli.RunConfig(
            pair="USD_JPY",
            strategy="mtf_regime_trend_cascade_scalp",
            interval="5m",
            lookback=30,
            chunk_days=10,
            state_dir=state_dir,
            output=output,
        ),
        max_chunks=1,
    )
    with pytest.raises(SystemExit):
        cli.run_chunked(
            cli.RunConfig(
                pair="USD_JPY",
                strategy="mtf_regime_trend_cascade_scalp",
                interval="5m",
                lookback=30,
                chunk_days=15,
                state_dir=state_dir,
                output=output,
            )
        )


def test_data_source_tag_is_parquet_only(tmp_path, monkeypatch):
    before = set(sys.modules)
    cli = _load_cli()
    monkeypatch.setattr(cli, "run_single_shot", lambda **_: [])
    _patch_fast_chunk_runner(monkeypatch, cli, [[]])
    result = cli.run_chunked(
        cli.RunConfig(
            pair="USD_JPY",
            strategy="mtf_regime_trend_cascade_scalp",
            interval="5m",
            lookback=7,
            chunk_days=7,
            state_dir=tmp_path / "state",
            output=tmp_path / "out.json",
        )
    )
    assert result["data_source"] == "parquet_cache"
    assert result["live_separation"] == "bt_only"
    loaded_now = set(sys.modules) - before
    assert "app" not in loaded_now
    assert "modules.demo_trader" not in loaded_now
    assert not any("oanda_audit" in name or "is_shadow" in name for name in loaded_now)
