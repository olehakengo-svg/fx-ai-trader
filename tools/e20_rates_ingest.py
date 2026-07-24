#!/usr/bin/env python3
"""e20_rates_ingest.py — E20 (金利差方向バイアス) の rates パネル取得 + シグナル CSV 生成.

位置づけ (e20-rate-differential-feasibility-2026-07-22 §7 データ準備):
  S1 台帳 (§3, 実 fetch 証跡付き) の keyless ソースから日次金利パネルを取得し、
  rapid_edge_probe の series spec が読む「date + per-pair 列」CSV を生成する。
  variant は S1 §6-2 で事前凍結された 2 本のみ:
    (a) carry-level    = 政策金利差 (BIS WS_CBPOL、8/8 通貨)
    (b) rates-momentum = 2y 国債利回り差の Δ63 営業日 (US/EUR/JPY/GBP/CAD レグ限定)

ソース台帳 (§3 D1–D9、全 keyless。FRED はキー不在で不使用):
  - 政策金利 8 通貨: BIS SDMX WS_CBPOL 日次 (D9)
  - 2y 利回り: US = MASSIVE /fed/v1/treasury-yields (D1、要 MASSIVE_API_KEY)
               EUR = ECB Data Portal YC SR_2Y (D2)
               JPY = MOF jgbcm_all.csv (D3、Shift-JIS + 和暦)
               GBP = BOE IADB IUDSNZC (D4) — **2y 系列は IADB に無く 5y ZC で代用
                     (2026-07-24 probe: IUDZNZC 等は HTML error)。テナー乖離は
                     診断レポートに caveat 明記、S3 で扱いを固定すること**
               CAD = BoC Valet BD.CDN.2YR.DQ.YLD (D5)
  - CHF 2y (D6: 2025-07 凍結) / AUD/NZD 2y (D7/D8: WAF 403) は momentum variant から
    構造的に除外 — 政策金利 variant は 8/8 でカバー。

出力:
  - 生 snapshot: data/cache/rates/raw/ (gitignore 域 — 遡及再取得可能、sha256 は manifest に)
  - シグナル CSV + manifest: knowledge-base/raw/bt-results/e20/ (コミット対象 — S2 再現性)
    CSV は探索窓保護のため SIGNAL_END (2022-12-31) で切断して書き出す
    (S3/S4 で OOS 窓が必要になったら本ツールを再実行して再生成する設計)。

規律: モジュールトップ副作用なし / silent except なし / 乱数なし (決定的)。

CLI:
  python3 tools/e20_rates_ingest.py fetch          # 取得 + CSV 生成 (network)
  python3 tools/e20_rates_ingest.py build-only     # 生 snapshot から CSV 再生成 (offline)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys

import pandas as pd
import requests

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

RAW_DIR = os.path.join(_REPO, "data", "cache", "rates", "raw")
OUT_DIR = os.path.join(_REPO, "knowledge-base", "raw", "bt-results", "e20")

GRID_START = "2013-01-01"      # mom63 warmup (探索窓 2014-06 の 1 年前から)
SIGNAL_END = "2022-12-31"      # 探索窓終端で CSV を物理切断 (S2 は探索窓のみ)
MOM_WINDOW_BDAYS = 63          # §6-2 (b) 凍結: Δ63 営業日 (≈3 か月)

# 政策金利 variant: FRICTION 13 ペア全部 (BIS 8/8 通貨カバー)
CARRY_PAIRS = (
    "AUD_JPY", "AUD_USD", "EUR_AUD", "EUR_GBP", "EUR_JPY", "EUR_USD",
    "GBP_JPY", "GBP_USD", "NZD_JPY", "NZD_USD", "USD_CAD", "USD_CHF", "USD_JPY",
)
# 2y momentum variant: 両レグが現行 2y ソース確認済み通貨 (§3) のペアのみ
MOM_CURRENCIES = ("USD", "EUR", "JPY", "GBP", "CAD")
MOM_PAIRS = tuple(
    p for p in CARRY_PAIRS
    if p.split("_")[0] in MOM_CURRENCIES and p.split("_")[1] in MOM_CURRENCIES
)

BIS_REF_AREA = {"US": "USD", "XM": "EUR", "JP": "JPY", "GB": "GBP",
                "AU": "AUD", "NZ": "NZD", "CA": "CAD", "CH": "CHF"}
_WAREKI_BASE = {"S": 1925, "H": 1988, "R": 2018}

URLS = {
    "bis_cbpol": ("https://stats.bis.org/api/v1/data/WS_CBPOL/"
                  "D.US+XM+JP+GB+AU+NZ+CA+CH/all?format=csv&startPeriod=2013-01-01"),
    "ecb_2y": ("https://data-api.ecb.europa.eu/service/data/YC/"
               "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y?format=csvdata&startPeriod=2013-01-01"),
    "mof_jgb": "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv",
    "boe_5y": ("https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp"
               "?csv.x=yes&Datefrom=01/Jan/2013&Dateto=01/Jul/2026"
               "&SeriesCodes=IUDSNZC&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N"),
    "boc_2y": ("https://www.bankofcanada.ca/valet/observations/"
               "BD.CDN.2YR.DQ.YLD/json?start_date=2013-01-01"),
    "massive_us_2y": ("https://api.massive.com/fed/v1/treasury-yields"
                      "?date.gte=2013-01-01&limit=5000&sort=date.asc"),
}


# ─── 取得 (network) ─────────────────────────────────────────────────────────
_ALLOWED_PREFIXES = ("https://stats.bis.org/", "https://data-api.ecb.europa.eu/",
                     "https://www.mof.go.jp/", "https://www.bankofengland.co.uk/",
                     "https://www.bankofcanada.ca/", "https://api.massive.com/")


def _http_get(url: str, timeout: int = 180) -> bytes:
    """https + 許可ホスト限定 (file:// 等のスキーム混入を構造排除)。"""
    if not url.startswith(_ALLOWED_PREFIXES):
        raise ValueError(f"URL not allowed (https + 台帳ホスト限定): {url[:80]}")
    resp = requests.get(url, headers={"User-Agent": "fx-ai-trader-e20/1.0"},
                        timeout=timeout, allow_redirects=True)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {url[:80]}")
    return resp.content


def fetch_raw_snapshots(raw_dir: str) -> dict:
    """全ソースを取得して生 snapshot を保存。MASSIVE は next_url ページング。"""
    os.makedirs(raw_dir, exist_ok=True)
    paths = {}
    for key in ("bis_cbpol", "ecb_2y", "mof_jgb", "boe_5y", "boc_2y"):
        ext = "json" if key == "boc_2y" else "csv"
        p = os.path.join(raw_dir, f"{key}.{ext}")
        data = _http_get(URLS[key])
        with open(p, "wb") as fh:
            fh.write(data)
        paths[key] = p
        print(f"fetched {key}: {len(data):,} bytes")

    api_key = os.environ.get("MASSIVE_API_KEY", "")
    if not api_key:
        raise RuntimeError("MASSIVE_API_KEY not set (US 2y に必須 — .env を確認)")
    rows, url = [], URLS["massive_us_2y"] + f"&apiKey={api_key}"
    while url:
        d = json.loads(_http_get(url))
        if d.get("status") not in ("OK", "DELAYED"):
            raise RuntimeError(f"MASSIVE status={d.get('status')!r}")
        rows.extend(d.get("results", []))
        nxt = d.get("next_url")
        url = (nxt + f"&apiKey={api_key}") if nxt else None
    p = os.path.join(raw_dir, "massive_us_2y.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"results": rows}, fh)
    paths["massive_us_2y"] = p
    print(f"fetched massive_us_2y: {len(rows):,} rows")
    return paths


# ─── パース (pure — offline テスト対象) ──────────────────────────────────────
def parse_wareki(s: str):
    """和暦 'S49.9.24' → Timestamp。未知 era / 形式不正は ValueError。"""
    era, rest = s[0], s[1:]
    if era not in _WAREKI_BASE:
        raise ValueError(f"unknown wareki era: {s!r}")
    y, m, d = (int(x) for x in rest.split("."))
    return pd.Timestamp(year=_WAREKI_BASE[era] + y, month=m, day=d)


def parse_bis_policy(text: str) -> pd.DataFrame:
    """BIS WS_CBPOL csv → 日次パネル (columns=通貨コード)。"""
    df = pd.read_csv(io.StringIO(text))
    df = df[df["REF_AREA"].isin(BIS_REF_AREA)]
    df = df.assign(ccy=df["REF_AREA"].map(BIS_REF_AREA),
                   date=pd.to_datetime(df["TIME_PERIOD"]))
    panel = df.pivot_table(index="date", columns="ccy", values="OBS_VALUE",
                           aggfunc="last")
    return panel.sort_index()


def parse_ecb_2y(text: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text))
    s = pd.Series(df["OBS_VALUE"].values,
                  index=pd.to_datetime(df["TIME_PERIOD"]), name="EUR")
    return s.sort_index()


def parse_mof_2y(raw: bytes) -> pd.Series:
    """MOF jgbcm_all.csv (Shift-JIS、1 行目タイトル、和暦日付) → 2年 series。"""
    text = raw.decode("shift-jis")
    df = pd.read_csv(io.StringIO(text), skiprows=1)
    col = "2年"
    if col not in df.columns:
        raise ValueError(f"MOF csv に {col!r} 列が無い: {list(df.columns)[:6]}")
    dates = df.iloc[:, 0].map(parse_wareki)
    vals = pd.to_numeric(df[col], errors="coerce")  # '-' (未発行テナー) は NaN
    s = pd.Series(vals.values, index=pd.DatetimeIndex(dates), name="JPY")
    return s.dropna().sort_index()


def parse_boe_5y(text: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text))
    s = pd.Series(df["IUDSNZC"].values,
                  index=pd.to_datetime(df["DATE"], format="%d %b %Y"), name="GBP")
    return s.sort_index()


def parse_boc_2y(text: str) -> pd.Series:
    d = json.loads(text)
    code = "BD.CDN.2YR.DQ.YLD"
    obs = [(o["d"], o[code]["v"]) for o in d["observations"] if code in o]
    s = pd.Series([float(v) for _, v in obs],
                  index=pd.to_datetime([dt for dt, _ in obs]), name="CAD")
    return s.sort_index()


def parse_massive_us_2y(text: str) -> pd.Series:
    rows = json.loads(text)["results"]
    pairs = [(r["date"], r["yield_2_year"]) for r in rows
             if r.get("yield_2_year") is not None]
    s = pd.Series([float(v) for _, v in pairs],
                  index=pd.to_datetime([dt for dt, _ in pairs]), name="USD")
    return s[~s.index.duplicated(keep="last")].sort_index()


# ─── シグナル生成 (pure) ─────────────────────────────────────────────────────
def build_signals(policy: pd.DataFrame, y2: pd.DataFrame,
                  grid_start: str = GRID_START, signal_end: str = SIGNAL_END,
                  mom_window: int = MOM_WINDOW_BDAYS) -> tuple:
    """(carry_df, mom_df): date 列 + per-pair 列。営業日グリッド、ffill、末尾切断。

    carry[BASE_QUOTE] = policy[BASE] − policy[QUOTE]  (%pt、連続値 — IC 用)
    mom[BASE_QUOTE]   = d2y − d2y.shift(63bd)、d2y = y2[BASE] − y2[QUOTE]
    look-ahead 排除の lag は spec 側 (rapid_edge_probe series.lag_days) が担う。
    """
    grid = pd.bdate_range(grid_start, signal_end)
    pol = policy.reindex(policy.index.union(grid)).ffill().reindex(grid)
    yy = y2.reindex(y2.index.union(grid)).ffill().reindex(grid)

    carry = pd.DataFrame(index=grid)
    for pair in CARRY_PAIRS:
        b, q = pair.split("_")
        carry[pair] = pol[b] - pol[q]

    mom = pd.DataFrame(index=grid)
    for pair in MOM_PAIRS:
        b, q = pair.split("_")
        d2 = yy[b] - yy[q]
        mom[pair] = d2 - d2.shift(mom_window)

    for df in (carry, mom):
        df.index.name = "date"
    return carry.reset_index(), mom.reset_index()


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_from_raw(raw_dir: str, out_dir: str) -> dict:
    """生 snapshot → パネル → シグナル CSV + manifest (sha256 台帳)。"""
    with open(os.path.join(raw_dir, "bis_cbpol.csv"), encoding="utf-8") as fh:
        policy = parse_bis_policy(fh.read())
    y2 = pd.concat([
        parse_massive_us_2y(open(os.path.join(raw_dir, "massive_us_2y.json"),
                                 encoding="utf-8").read()),
        parse_ecb_2y(open(os.path.join(raw_dir, "ecb_2y.csv"), encoding="utf-8").read()),
        parse_mof_2y(open(os.path.join(raw_dir, "mof_jgb.csv"), "rb").read()),
        parse_boe_5y(open(os.path.join(raw_dir, "boe_5y.csv"), encoding="utf-8").read()),
        parse_boc_2y(open(os.path.join(raw_dir, "boc_2y.json"), encoding="utf-8").read()),
    ], axis=1)

    carry, mom = build_signals(policy, y2)
    os.makedirs(out_dir, exist_ok=True)
    paths = {"carry": os.path.join(out_dir, "e20_carry_level.csv"),
             "mom": os.path.join(out_dir, "e20_mom63_2y.csv")}
    carry.to_csv(paths["carry"], index=False, float_format="%.6f")
    mom.to_csv(paths["mom"], index=False, float_format="%.6f")

    manifest = {
        "tool": "e20_rates_ingest",
        "signal_end": SIGNAL_END, "grid_start": GRID_START,
        "mom_window_bdays": MOM_WINDOW_BDAYS,
        "gbp_leg_note": "BOE IADB に 2y ZC 系列が無いため IUDSNZC (5y nominal ZC) で代用",
        "policy_coverage": {c: [str(policy[c].dropna().index.min().date()),
                                str(policy[c].dropna().index.max().date())]
                            for c in policy.columns},
        "y2_coverage": {c: [str(y2[c].dropna().index.min().date()),
                            str(y2[c].dropna().index.max().date())]
                        for c in y2.columns},
        "signals": {k: {"path": os.path.relpath(p, _REPO), "sha256": _sha256(p),
                        "rows": int(pd.read_csv(p).shape[0])}
                    for k, p in paths.items()},
        "raw_sha256": {f: _sha256(os.path.join(raw_dir, f))
                       for f in sorted(os.listdir(raw_dir))
                       if f.endswith((".csv", ".json"))},
    }
    mpath = os.path.join(out_dir, "e20_ingest_manifest.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print(f"signals written: {paths['carry']} / {paths['mom']}")
    print(f"manifest: {mpath}")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode")
    for name in ("fetch", "build-only"):
        sp = sub.add_parser(name)
        sp.add_argument("--raw-dir", default=RAW_DIR)
        sp.add_argument("--out-dir", default=OUT_DIR)
    args = parser.parse_args(argv)
    if args.mode == "fetch":
        fetch_raw_snapshots(args.raw_dir)
        build_from_raw(args.raw_dir, args.out_dir)
        return 0
    if args.mode == "build-only":
        build_from_raw(args.raw_dir, args.out_dir)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
