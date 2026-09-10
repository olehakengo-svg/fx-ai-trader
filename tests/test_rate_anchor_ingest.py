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


# ─── Treasury fallback パーサ ────────────────────────────────────────────────
_TREASURY_HEADER = ('Date,"1 Mo","1.5 Month","2 Mo","3 Mo","4 Mo","6 Mo",'
                    '"1 Yr","2 Yr","3 Yr","5 Yr","7 Yr","10 Yr","20 Yr","30 Yr"')


def test_parse_treasury_maps_to_fred_series():
    text = "\n".join([
        _TREASURY_HEADER,
        "09/09/2026,3.81,3.88,3.93,3.95,4.06,4.01,4.17,4.43,4.49,4.61,4.71,4.83,5.28,5.28",
        "08/14/2026,3.79,3.80,3.81,3.86,3.88,3.95,3.98,4.17,4.24,4.36,4.51,4.68,5.25,",
    ])
    df = R.parse_treasury(text)
    assert list(df.columns) == list(R._FRED_SERIES)
    assert df.index.is_monotonic_increasing
    # 2026-08-14 実測: FRED DGS 系列と同一値 (FRED は Treasury の再配布)
    assert df.loc["2026-08-14", "DGS1"] == pytest.approx(3.98)
    assert df.loc["2026-08-14", "DGS2"] == pytest.approx(4.17)
    assert df.loc["2026-08-14", "DGS5"] == pytest.approx(4.36)
    assert df.loc["2026-08-14", "DGS10"] == pytest.approx(4.68)
    assert df.loc["2026-09-09", "DGS10"] == pytest.approx(4.83)


def test_parse_treasury_missing_column_raises():
    with pytest.raises(ValueError):
        R.parse_treasury('Date,"1 Mo"\n09/09/2026,3.81')


def test_fetch_us_yields_falls_back_to_treasury(monkeypatch):
    """FRED がハング (GH runner 実測 17/17) しても Treasury 当年+前年で自己修復する。"""
    calls = []

    def fake_get(url, timeout=180):
        calls.append(url)
        if "fred.stlouisfed.org" in url:
            raise RuntimeError("Read timed out (WAF)")
        year = "2025" if "2025" in url else "2026"
        rows = {"2025": "12/31/2025,3.7,3.7,3.7,3.7,3.7,3.6,3.5,3.5,3.5,3.7,3.9,4.2,4.8,4.9",
                "2026": "09/09/2026,3.81,3.88,3.93,3.95,4.06,4.01,4.17,4.43,4.49,4.61,4.71,4.83,5.28,5.28"}
        return ("\n".join([_TREASURY_HEADER, rows[year]])).encode("utf-8")

    monkeypatch.setattr(R, "_http_get", fake_get)
    df, source = R.fetch_us_yields(today=pd.Timestamp("2026-09-10"))
    assert source == "treasury"
    assert len(calls) == 3                              # FRED 1 + Treasury 2 (前年+当年)
    assert len(df) == 2                                 # 前年末 + 当年、union 済み
    assert df.loc["2026-09-09", "DGS2"] == pytest.approx(4.43)
    assert df.loc["2025-12-31", "DGS10"] == pytest.approx(4.2)


def test_fetch_us_yields_fred_primary(monkeypatch):
    def fake_get(url, timeout=180):
        assert "fred.stlouisfed.org" in url             # primary は FRED のみ叩く
        return b"observation_date,DGS1,DGS2,DGS5,DGS10\n2026-09-08,4.15,4.39,4.57,4.80\n"

    monkeypatch.setattr(R, "_http_get", fake_get)
    df, source = R.fetch_us_yields(today=pd.Timestamp("2026-09-10"))
    assert source == "fred"
    assert df.loc["2026-09-08", "DGS10"] == pytest.approx(4.80)


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


def test_treasury_url_is_allowlisted():
    url = R.URLS["treasury_par"].format(year=2026)
    assert url.startswith(R._ALLOWED_PREFIXES)


# ─── run() の per-source 隔離 (部分失敗でも成功分は蓄積 + 終端で loud) ─────────
def test_run_partial_failure_accumulates_then_raises(tmp_path, monkeypatch):
    def fake_get(url, timeout=180):
        raise RuntimeError("network down")              # MoF/FRED/Treasury 全滅

    monkeypatch.setattr(R, "_http_get", fake_get)
    # ZN cache だけは生きている状況を再現
    idx = pd.DatetimeIndex(["2026-09-09 10:00"], tz="UTC")
    bars = pd.DataFrame({"Open": [110.0], "High": [110.5], "Low": [109.9],
                         "Close": [110.2], "Volume": [10]}, index=idx)
    zn_path = str(tmp_path / "zn.parquet")
    bars.to_parquet(zn_path)
    monkeypatch.setattr(R, "ZN_CACHE", zn_path)

    out_dir = str(tmp_path / "out")
    with pytest.raises(RuntimeError, match="partial ingest failure"):
        R.run(out_dir=out_dir, fetch=True, refresh_zn=False)
    # 失敗ソースがあっても ZN 日足と manifest は書かれている (write 経路の保全)
    zn_df = pd.read_csv(f"{out_dir}/zn_f_daily.csv")
    assert len(zn_df) == 1
    manifest = json.loads(open(f"{out_dir}/manifest.json").read())
    assert "zn_f_daily" in manifest["files"]
    assert "jgb_yields" not in manifest["files"]
