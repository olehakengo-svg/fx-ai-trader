from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

from modules import data as data_mod


def _sample_ohlcv(start: str = "2025-11-03", periods: int = 6) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="12h", tz="UTC")
    base = pd.Series(range(periods), dtype=float) + 150.0
    return pd.DataFrame(
        {
            "Open": base.values,
            "High": (base + 0.1).values,
            "Low": (base - 0.1).values,
            "Close": (base + 0.01).values,
            "Volume": 100.0,
        },
        index=idx,
    )


def _write_manifest(path, content: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        content
        or """{
  "version": 2,
  "lock_window_utc": ["2025-11-04T00:00:00Z", "2026-05-04T00:00:00Z"],
  "issued_at": "2026-05-05T10:40:00+0900",
  "issuer": "claude-司令塔",
  "expires_at": "2026-08-05T00:00:00Z",
  "rationale": "Wave 4 6-month holdout window (HIP-1 v2 fail-safe scoped)",
  "covered_paths": ["data/cache/**/*.parquet"],
  "guard_env": "FX_HOLDOUT_GUARD",
  "validation_env": "FX_HOLDOUT_VALIDATION"
}
""",
        encoding="utf-8",
    )


def test_guard_env_unset_passthrough_live_default(monkeypatch, tmp_path):
    manifest = tmp_path / "MANIFEST.json"
    _write_manifest(manifest)
    df = _sample_ohlcv()

    monkeypatch.setattr(data_mod, "_HOLDOUT_MANIFEST_PATH", str(manifest))
    monkeypatch.delenv("FX_HOLDOUT_GUARD", raising=False)
    monkeypatch.delenv("FX_HOLDOUT_VALIDATION", raising=False)

    got = data_mod._apply_holdout_guard(df, "data/cache/massive/USD_JPY_5m.parquet")

    pd.testing.assert_frame_equal(got, df)


def test_fetch_ohlcv_like_live_path_passthrough_when_guard_unset(monkeypatch, tmp_path):
    manifest = tmp_path / "MANIFEST.json"
    _write_manifest(manifest)
    parquet_df = _sample_ohlcv(periods=10)

    data_mod._data_cache.clear()
    monkeypatch.setattr(data_mod, "_HOLDOUT_MANIFEST_PATH", str(manifest))
    monkeypatch.delenv("FX_HOLDOUT_GUARD", raising=False)
    monkeypatch.delenv("FX_HOLDOUT_VALIDATION", raising=False)
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.delenv("OANDA_TOKEN", raising=False)
    monkeypatch.delenv("TWELVEDATA_API_KEY", raising=False)
    monkeypatch.setattr(
        data_mod,
        "_fetch_raw",
        lambda symbol, period, interval: (_ for _ in ()).throw(RuntimeError("yf down")),
    )
    monkeypatch.setattr(
        data_mod,
        "_load_parquet_cache_fallback",
        lambda symbol, interval, days, min_bars: (
            data_mod._apply_holdout_guard(
                parquet_df,
                "data/cache/massive/USD_JPY_5m.parquet",
            ),
            datetime(2026, 5, 3, tzinfo=timezone.utc),
        ),
    )

    got = data_mod.fetch_ohlcv("USDJPY=X", period="10d", interval="5m")

    pd.testing.assert_frame_equal(got, parquet_df)


def test_manifest_absent_passthrough(monkeypatch, tmp_path):
    df = _sample_ohlcv()

    monkeypatch.setattr(data_mod, "_HOLDOUT_MANIFEST_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setenv("FX_HOLDOUT_GUARD", "1")
    monkeypatch.delenv("FX_HOLDOUT_VALIDATION", raising=False)

    got = data_mod._apply_holdout_guard(df, "data/cache/massive/USD_JPY_5m.parquet")

    pd.testing.assert_frame_equal(got, df)


def test_inside_lock_window_cut_when_opted_in(monkeypatch, tmp_path):
    manifest = tmp_path / "MANIFEST.json"
    _write_manifest(manifest)
    df = _sample_ohlcv()
    before_counter = data_mod._HOLDOUT_CUT_COUNTER

    monkeypatch.setattr(data_mod, "_HOLDOUT_MANIFEST_PATH", str(manifest))
    monkeypatch.setenv("FX_HOLDOUT_GUARD", "1")
    monkeypatch.delenv("FX_HOLDOUT_VALIDATION", raising=False)

    got = data_mod._apply_holdout_guard(df, "data/cache/massive/USD_JPY_5m.parquet")

    assert len(got) == 2
    assert got.index.max() < pd.Timestamp("2025-11-04T00:00:00Z")
    assert data_mod._HOLDOUT_CUT_COUNTER == before_counter + 4


def test_outside_lock_window_passthrough_when_opted_in(monkeypatch, tmp_path):
    manifest = tmp_path / "MANIFEST.json"
    _write_manifest(manifest)
    df = _sample_ohlcv(start="2025-11-01", periods=4)

    monkeypatch.setattr(data_mod, "_HOLDOUT_MANIFEST_PATH", str(manifest))
    monkeypatch.setenv("FX_HOLDOUT_GUARD", "1")
    monkeypatch.delenv("FX_HOLDOUT_VALIDATION", raising=False)

    got = data_mod._apply_holdout_guard(df, "data/cache/massive/USD_JPY_5m.parquet")

    pd.testing.assert_frame_equal(got, df)


def test_validation_env_passthrough_with_warning(monkeypatch, tmp_path, caplog):
    manifest = tmp_path / "MANIFEST.json"
    _write_manifest(manifest)
    df = _sample_ohlcv()

    monkeypatch.setattr(data_mod, "_HOLDOUT_MANIFEST_PATH", str(manifest))
    monkeypatch.setenv("FX_HOLDOUT_GUARD", "1")
    monkeypatch.setenv("FX_HOLDOUT_VALIDATION", "1")

    got = data_mod._apply_holdout_guard(df, "data/cache/massive/USD_JPY_5m.parquet")

    pd.testing.assert_frame_equal(got, df)
    assert "HOLDOUT VALIDATION MODE" in caplog.text


@pytest.mark.parametrize("content", ["{not-json", '{"version": 2}'])
def test_manifest_schema_validation_only_when_guard_active(monkeypatch, tmp_path, content):
    manifest = tmp_path / "MANIFEST.json"
    _write_manifest(manifest, content)
    df = _sample_ohlcv()

    monkeypatch.setattr(data_mod, "_HOLDOUT_MANIFEST_PATH", str(manifest))
    monkeypatch.delenv("FX_HOLDOUT_GUARD", raising=False)
    pd.testing.assert_frame_equal(
        data_mod._apply_holdout_guard(df, "data/cache/massive/USD_JPY_5m.parquet"),
        df,
    )

    monkeypatch.setenv("FX_HOLDOUT_GUARD", "1")
    with pytest.raises(RuntimeError):
        data_mod._apply_holdout_guard(df, "data/cache/massive/USD_JPY_5m.parquet")
