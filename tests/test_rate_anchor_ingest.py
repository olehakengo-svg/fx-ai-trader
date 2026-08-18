"""rate_anchor_ingest のオフライン test pin (network 不要)。

family C 材料蓄積の不変条件 (union-merge 単調性 / パーサ / manifest 決定性) を固定する。
"""
import json

import pandas as pd
import pytest

from tools import rate_anchor_ingest as R


# ─── MoF パーサ ──────────────────────────────────────────────────────────────
_MOF_JA_HEADER = "基準日," + ",".join(f"{t[:-1]}年" for t in R._TENORS)
_MOF_EN_HEADER = "Date," + ",".join(t.upper() for t in R._TENORS)


def _row(first: str, vals):
    return first + "," + ",".join(str(v) for v in vals)


def test_parse_mof_all_wareki_and_missing_tenor():
    vals_a = ["10.3"] + ["-"] * 14          # 未発行テナーは '-'
    vals_b = [f"{0.1 * i:.2f}" for i in range(1, 16)]
    text = "\n".join([
        "国債金利情報,,,,,,,,,,,,,,,(単位 : %)",
        _MOF_JA_HEADER,
        _row("S49.9.24", vals_a),
        _row("R8.7.31", vals_b),
    ])
    df = R.parse_mof_all(text.encode("shift-jis"))
    assert list(df.columns) == list(R._TENORS)
    assert df.index[0] == pd.Timestamp("1974-09-24")
    assert df.index[-1] == pd.Timestamp("2026-07-31")
    assert df.loc["1974-09-24", "1y"] == pytest.approx(10.3)
    assert pd.isna(df.loc["1974-09-24", "2y"])          # '-' → NaN
    assert df.loc["2026-07-31", "10y"] == pytest.approx(1.0)


def test_parse_mof_current_drops_trailing_junk():
    vals = [f"{1.0 + 0.1 * i:.2f}" for i in range(15)]
    text = "\n".join([
        "Interest Rate (August 2026),,,,,,,,,,,,,,,(Unit : %)",
        _MOF_EN_HEADER,
        _row("2026/8/3", vals),
        _row("2026/8/17", vals),
        "," * 15,
        '"  If you cannot download the latest csv data...",' + "," * 14,
    ])
    df = R.parse_mof_current(text.encode("utf-8"))
    assert len(df) == 2                                 # 注記/空行は落ちる
    assert df.index[-1] == pd.Timestamp("2026-08-17")
    assert df.loc["2026-08-03", "1y"] == pytest.approx(1.0)


def test_parse_mof_all_missing_column_raises():
    text = "title\n基準日,1年\nR8.1.5,1.0"
    with pytest.raises(ValueError):
        R.parse_mof_all(text.encode("shift-jis"))


# ─── FRED パーサ ─────────────────────────────────────────────────────────────
def test_parse_fred_blank_is_nan():
    text = (
        "observation_date,DGS1,DGS2,DGS5,DGS10\n"
        "2026-08-13,4.0,4.15,,4.63\n"
        "2026-08-14,4.01,4.17,4.4,4.68\n"
    )
    df = R.parse_fred(text)
    assert list(df.columns) == list(R._FRED_SERIES)
    assert pd.isna(df.loc["2026-08-13", "DGS5"])
    assert df.loc["2026-08-14", "DGS10"] == pytest.approx(4.68)


# ─── union-merge 不変条件 ────────────────────────────────────────────────────
def _frame(dates, val):
    return pd.DataFrame({"a": [val] * len(dates)},
                        index=pd.DatetimeIndex(pd.to_datetime(dates), name="date"))


def test_union_merge_grows_and_fresh_wins():
    old = _frame(["2026-08-01", "2026-08-04"], 1.0)
    fresh = _frame(["2026-08-04", "2026-08-05"], 2.0)
    merged = R.union_merge(old, fresh)
    assert len(merged) == 3                             # 単調非減少
    assert merged.loc["2026-08-01", "a"] == 1.0         # 窓外の歴史は保持
    assert merged.loc["2026-08-04", "a"] == 2.0         # 重複日は fresh (訂正反映)
    assert merged.index.is_monotonic_increasing


def test_union_merge_none_old_passthrough():
    fresh = _frame(["2026-08-05", "2026-08-04"], 2.0)
    merged = R.union_merge(None, fresh)
    assert list(merged.index) == list(pd.to_datetime(["2026-08-04", "2026-08-05"]))


def test_update_store_roundtrip_monotone(tmp_path):
    p = str(tmp_path / "s.csv")
    R.update_store(p, _frame(["2026-08-01", "2026-08-04"], 1.0))
    merged = R.update_store(p, _frame(["2026-08-05"], 3.0))
    assert len(merged) == 3
    again = R.update_store(p, _frame(["2026-08-05"], 3.0))  # 再実行は冪等
    assert len(again) == 3


# ─── ZN 日足集計 ─────────────────────────────────────────────────────────────
def test_zn_daily_from_cache_utc_day_agg(tmp_path):
    idx = pd.DatetimeIndex(
        ["2026-08-13 00:00", "2026-08-13 10:00", "2026-08-13 23:00",
         "2026-08-14 05:00"], tz="UTC")
    bars = pd.DataFrame({
        "Open": [110.0, 110.5, 110.2, 111.0],
        "High": [110.6, 111.2, 110.4, 111.3],
        "Low": [109.8, 110.4, 110.0, 110.9],
        "Close": [110.5, 110.3, 110.1, 111.2],
        "Volume": [100, 200, 50, 80],
    }, index=idx)
    p = str(tmp_path / "zn.parquet")
    bars.to_parquet(p)
    daily = R.zn_daily_from_cache(p)
    assert len(daily) == 2
    d = daily.loc["2026-08-13"]
    assert d["open"] == 110.0 and d["close"] == 110.1
    assert d["high"] == 111.2 and d["low"] == 109.8
    assert d["volume"] == 350 and d["n_bars"] == 3


def test_zn_daily_missing_cache_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        R.zn_daily_from_cache(str(tmp_path / "nope.parquet"))


# ─── manifest 決定性 ─────────────────────────────────────────────────────────
def test_manifest_deterministic_no_timestamp(tmp_path):
    p = str(tmp_path / "jgb_yields.csv")
    R.update_store(p, _frame(["2026-08-01"], 1.0))
    m1 = R.write_manifest(str(tmp_path), {"jgb_yields": p})
    raw1 = (tmp_path / "manifest.json").read_bytes()
    m2 = R.write_manifest(str(tmp_path), {"jgb_yields": p})
    raw2 = (tmp_path / "manifest.json").read_bytes()
    assert raw1 == raw2                                 # データ不変 → diff ゼロ
    assert m1 == m2
    assert "fetched_at" not in json.dumps(m1)


# ─── URL allowlist ───────────────────────────────────────────────────────────
def test_http_get_rejects_non_allowlisted():
    with pytest.raises(ValueError):
        R._http_get("https://evil.example.com/x.csv")
    with pytest.raises(ValueError):
        R._http_get("file:///etc/passwd")
