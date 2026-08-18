#!/usr/bin/env python3
"""rate_anchor_ingest.py — family C (金利観測アンカー) の日次データ蓄積パイプライン.

位置づけ (intervention-history-anatomy-2026-08-18 追記 family C / user「水平線理論」最終形):
  日米金利差フェアバリュー帯の「材料」を毎日自動収集して data/external/rate_anchor/ に
  蓄積する。**材料収集のみ — シグナル/乖離/フェアバリュー帯の計算は一切しない**
  (family C は pre-reg 前。signal×outcome への接触はここでは構造的に不可能な設計)。

ソース (全て keyless、e20_rates_ingest の配管様式を踏襲):
  - JGB 全テナー: MoF jgbcm_all.csv (歴史、Shift-JIS + 和暦、月次ラグあり)
                + MoF 英語版 jgbcme.csv (当月分、日次更新) — 両者 union で日次鮮度を確保
  - US Treasury: FRED fredgraph.csv (DGS1/DGS2/DGS5/DGS10、日次)
  - ZN=F 日足:  data/cache/yield/ZN_F_1h.parquet (zn-cache-refresh / 本ジョブが延伸) を
                UTC-day に集計 (US10y の intraday proxy — modules/yield_data.py 参照)

蓄積規約 (lesson-rolling-window-cache-overwrite-2026-08-14):
  全出力 CSV は date キーの union-merge (重複日は fresh 採用 = ベンダー訂正反映)。
  不変条件 = 行数単調非減少 / 既存日付の欠落なし / 左端保持。違反は即例外 (silent 破壊禁止)。
  MoF 歴史ファイルの月次ラグで生じうる穴は、日次蓄積 + 歴史ファイル再取得で自己修復する。

規律: モジュールトップ副作用なし / silent except なし / manifest にタイムスタンプを
      含めない (データ不変なら再実行しても diff ゼロ = workflow の空コミット回避)。

CLI:
  python3 tools/rate_anchor_ingest.py fetch                # MoF + FRED 取得 + 蓄積更新
  python3 tools/rate_anchor_ingest.py fetch --refresh-zn   # ZN=F 1h cache も延伸してから
  python3 tools/rate_anchor_ingest.py build-only           # 取得なし (ZN 日足 + manifest 再生成)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

OUT_DIR = os.path.join(_REPO, "data", "external", "rate_anchor")
ZN_CACHE = os.path.join(_REPO, "data", "cache", "yield", "ZN_F_1h.parquet")

START = "2013-01-01"  # e20 GRID_START と同一 (family C explore 想定窓 2014-2021 を被覆)

# JGB テナー: MoF 列名 (日本語歴史版 / 英語当月版) → 正準列名
_TENORS = ("1y", "2y", "3y", "4y", "5y", "6y", "7y", "8y", "9y", "10y",
           "15y", "20y", "25y", "30y", "40y")
_MOF_JA_COLS = {f"{t[:-1]}年": t for t in _TENORS}
_MOF_EN_COLS = {t.upper(): t for t in _TENORS}

_FRED_SERIES = ("DGS1", "DGS2", "DGS5", "DGS10")

URLS = {
    "mof_jgb_all": "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv",
    "mof_jgb_current": ("https://www.mof.go.jp/english/policy/jgbs/reference/"
                        "interest_rate/jgbcme.csv"),
    "fred_dgs": ("https://fred.stlouisfed.org/graph/fredgraph.csv?id="
                 + ",".join(_FRED_SERIES)),
}

_ALLOWED_PREFIXES = ("https://www.mof.go.jp/", "https://fred.stlouisfed.org/")


def _http_get(url: str, timeout: int = 180) -> bytes:
    """https + 許可ホスト限定 (e20_rates_ingest._http_get と同型)。"""
    import requests

    if not url.startswith(_ALLOWED_PREFIXES):
        raise ValueError(f"URL not allowed (https + 台帳ホスト限定): {url[:80]}")
    resp = requests.get(url, headers={"User-Agent": "fx-ai-trader-rate-anchor/1.0"},
                        timeout=timeout, allow_redirects=True)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {url[:80]}")
    return resp.content


# ─── パース (pure — offline テスト対象) ──────────────────────────────────────
def parse_mof_all(raw: bytes) -> pd.DataFrame:
    """MoF jgbcm_all.csv (Shift-JIS、1 行目タイトル、和暦日付) → 全テナー frame。

    '-' (未発行テナー) は NaN。index = DatetimeIndex、columns = 正準テナー名。
    """
    from tools.e20_rates_ingest import parse_wareki

    text = raw.decode("shift-jis")
    df = pd.read_csv(io.StringIO(text), skiprows=1)
    missing = [c for c in _MOF_JA_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"MOF csv に想定列が無い: {missing[:3]} / 実列 {list(df.columns)[:6]}")
    out = pd.DataFrame(
        {canon: pd.to_numeric(df[ja], errors="coerce").values
         for ja, canon in _MOF_JA_COLS.items()},
        index=pd.DatetimeIndex(df.iloc[:, 0].map(parse_wareki), name="date"),
    )
    return out.sort_index()


def parse_mof_current(raw: bytes) -> pd.DataFrame:
    """MoF 英語版 jgbcme.csv (当月分、西暦日付、末尾に注記行) → 全テナー frame。

    日付にパースできない行 (末尾の空行/注記) は落とす。'-' は NaN。
    """
    text = raw.decode("utf-8", errors="replace")
    df = pd.read_csv(io.StringIO(text), skiprows=1)
    missing = [c for c in _MOF_EN_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"MOF 英語 csv に想定列が無い: {missing[:3]} / 実列 {list(df.columns)[:6]}")
    dates = pd.to_datetime(df.iloc[:, 0], format="%Y/%m/%d", errors="coerce")
    keep = dates.notna()
    out = pd.DataFrame(
        {canon: pd.to_numeric(df[en], errors="coerce")[keep].values
         for en, canon in _MOF_EN_COLS.items()},
        index=pd.DatetimeIndex(dates[keep], name="date"),
    )
    return out.sort_index()


def parse_fred(text: str) -> pd.DataFrame:
    """FRED fredgraph.csv (observation_date + series 列、欠損は空/'.') → frame。"""
    df = pd.read_csv(io.StringIO(text))
    date_col = df.columns[0]  # observation_date
    missing = [s for s in _FRED_SERIES if s not in df.columns]
    if missing:
        raise ValueError(f"FRED csv に想定系列が無い: {missing} / 実列 {list(df.columns)}")
    out = pd.DataFrame(
        {s: pd.to_numeric(df[s], errors="coerce").values for s in _FRED_SERIES},
        index=pd.DatetimeIndex(pd.to_datetime(df[date_col]), name="date"),
    )
    return out.sort_index()


def zn_daily_from_cache(cache_path: str = ZN_CACHE) -> pd.DataFrame:
    """ZN=F 1h cache → UTC-day OHLCV。cache 不在は例外 (silent 空返し禁止)。"""
    if not os.path.exists(cache_path):
        raise FileNotFoundError(f"ZN cache 不在: {cache_path} (zn-cache-refresh を先に)")
    bars = pd.read_parquet(cache_path)
    if bars.index.tz is None:
        bars.index = bars.index.tz_localize("UTC")
    else:
        bars.index = bars.index.tz_convert("UTC")
    bars = bars.sort_index()
    g = bars.groupby(bars.index.date)
    daily = pd.DataFrame({
        "open": g["Open"].first(),
        "high": g["High"].max(),
        "low": g["Low"].min(),
        "close": g["Close"].last(),
        "volume": g["Volume"].sum(),
        "n_bars": g.size(),
    })
    daily.index = pd.DatetimeIndex(pd.to_datetime(daily.index), name="date")
    return daily.sort_index()


# ─── union-merge 蓄積 (pure invariant 部) ────────────────────────────────────
def union_merge(old: pd.DataFrame | None, fresh: pd.DataFrame) -> pd.DataFrame:
    """date-index frame の union-merge。重複日は fresh 採用。

    不変条件 (違反は AssertionError — 破壊的上書きの構造排除):
      行数単調非減少 / 既存日付の欠落なし / 左端保持。
    """
    if old is None or old.empty:
        return fresh.sort_index()
    old = old.reindex(columns=fresh.columns)
    merged = pd.concat([old, fresh])
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    assert len(merged) >= len(old), "行数が減った = 破壊的上書き (merge 退行)"
    assert old.index.isin(merged.index).all(), "既存日付の欠落"
    assert merged.index.min() <= old.index.min(), "左端の歴史が失われた"
    return merged


def _read_store(path: str) -> pd.DataFrame | None:
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, parse_dates=["date"], index_col="date")
    return df


def update_store(path: str, fresh: pd.DataFrame) -> pd.DataFrame:
    """既存 CSV と fresh を union-merge して書き戻す。"""
    merged = union_merge(_read_store(path), fresh)
    merged.to_csv(path, float_format="%.6g", date_format="%Y-%m-%d")
    return merged


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(out_dir: str, files: dict) -> dict:
    """決定的 manifest (タイムスタンプなし — データ不変なら diff ゼロ)。"""
    manifest = {
        "tool": "rate_anchor_ingest",
        "purpose": ("family C 金利アンカー材料の日次蓄積 (材料のみ — シグナル/乖離計算は"
                    "行わない。family C は pre-reg 前)"),
        "start": START,
        "sources": dict(URLS),
        "zn_source": "data/cache/yield/ZN_F_1h.parquet (union-merge cache) の UTC-day 集計",
        "files": {},
    }
    for name, path in files.items():
        df = pd.read_csv(path)
        manifest["files"][name] = {
            "path": os.path.relpath(path, _REPO),
            "rows": int(df.shape[0]),
            "date_min": str(df["date"].iloc[0]),
            "date_max": str(df["date"].iloc[-1]),
            "sha256": _sha256(path),
        }
    mpath = os.path.join(out_dir, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return manifest


# ─── 実行フロー ──────────────────────────────────────────────────────────────
def refresh_zn_cache() -> None:
    """ZN=F 1h cache を union-merge で延伸 (zn-cache-refresh.yml と同一の不変条件)。"""
    from modules.yield_data import fetch_zn_intraday

    before = pd.read_parquet(ZN_CACHE) if os.path.exists(ZN_CACHE) else None
    n0 = len(before) if before is not None else 0
    fetch_zn_intraday(interval="1h", days=3650, use_cache=True, cache_max_age_hours=0)
    after = pd.read_parquet(ZN_CACHE)
    print(f"ZN cache: rows {n0} -> {len(after)} | right edge {after.index.max()}")
    assert len(after) >= n0, "ZN cache 行数が減った = 破壊的上書き (merge 退行)"
    if before is not None and n0:
        assert before.index.isin(after.index).all(), "ZN cache 既存バーの欠落"


def run(out_dir: str = OUT_DIR, fetch: bool = True, refresh_zn: bool = False) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    files = {}

    if refresh_zn:
        refresh_zn_cache()

    if fetch:
        jgb_all = parse_mof_all(_http_get(URLS["mof_jgb_all"]))
        jgb_cur = parse_mof_current(_http_get(URLS["mof_jgb_current"]))
        # 歴史 + 当月を結合 (重複日は当月版採用) → START で切って蓄積
        jgb = pd.concat([jgb_all, jgb_cur])
        jgb = jgb[~jgb.index.duplicated(keep="last")].sort_index()
        jgb = jgb[jgb.index >= START]
        p = os.path.join(out_dir, "jgb_yields.csv")
        merged = update_store(p, jgb)
        files["jgb_yields"] = p
        print(f"jgb_yields: {len(merged)} rows | {merged.index.min().date()}"
              f" -> {merged.index.max().date()}")

        us = parse_fred(_http_get(URLS["fred_dgs"]).decode("utf-8"))
        us = us[us.index >= START]
        p = os.path.join(out_dir, "us_treasury_yields.csv")
        merged = update_store(p, us)
        files["us_treasury_yields"] = p
        print(f"us_treasury_yields: {len(merged)} rows | {merged.index.min().date()}"
              f" -> {merged.index.max().date()}")

    zn = zn_daily_from_cache()
    p = os.path.join(out_dir, "zn_f_daily.csv")
    merged = update_store(p, zn)
    files["zn_f_daily"] = p
    print(f"zn_f_daily: {len(merged)} rows | {merged.index.min().date()}"
          f" -> {merged.index.max().date()}")

    # manifest は out_dir の実在ファイル全部で決定的に再生成
    all_files = {n: os.path.join(out_dir, f"{n}.csv")
                 for n in ("jgb_yields", "us_treasury_yields", "zn_f_daily")
                 if os.path.exists(os.path.join(out_dir, f"{n}.csv"))}
    manifest = write_manifest(out_dir, all_files)
    print(f"manifest: {os.path.join(out_dir, 'manifest.json')}")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode")
    for name in ("fetch", "build-only"):
        sp = sub.add_parser(name)
        sp.add_argument("--out-dir", default=OUT_DIR)
        sp.add_argument("--refresh-zn", action="store_true",
                        help="ZN=F 1h cache を yfinance で延伸してから日足を再生成")
    args = parser.parse_args(argv)
    if args.mode == "fetch":
        run(args.out_dir, fetch=True, refresh_zn=args.refresh_zn)
        return 0
    if args.mode == "build-only":
        run(args.out_dir, fetch=False, refresh_zn=args.refresh_zn)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
