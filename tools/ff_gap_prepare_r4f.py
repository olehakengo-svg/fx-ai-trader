#!/usr/bin/env python3
"""ff_gap_prepare_r4f.py — FF カレンダー歴史パネル+gap の R4F dump → import CSV 整形.

位置づけ (market-data-ingest-2026-07-18 §3 / e15-e7-event-modality-prereg §3.3):
  FF カレンダー歴史の正規 dump として Robots4Forex 公開 CSV
  (https://robots4forex.com/news/news.php、2007〜現在、keyless、日次更新) を採用。
  EPSOFT (github.com/EPSOFT/dataset-forexfactory) は 2023-03 で更新停止 = 延長なし
  (2026-07-24 確認)。値整合は EPSOFT と突合済み — 歴史 sample (2016-06/2019-03/2021-09)
  **279/279 完全一致**、2023 Q1 overlap 114/120 (差分は全て EPSOFT 側 end-of-panel の
  actual 未充填/凍結前 forecast)。→ **歴史パネル (2014-01〜) と gap (2023-04〜) を
  R4F 一本で一括 import する** (EPSOFT 別 import は不要、cross-check 用に温存)。
  本ツールは dump を検査・正規化し、`tools/ff_calendar_import.py` 互換の CSV を生成する。

dump の実測特性 (2026-07-24、E15 canonical カレンダー 149 NFP + 135 CPI anchor で特定):
  - 列: date,time,currency,impact(H/M/L/N),title,_,_,actual,forecast,previous
    (列 6/7 は全行空 — 非空が現れたら fail-loud)
  - **時刻規約が 2023-08-07 で切替**: それ以前 = Europe/London 現地時刻
    (BST 期 +60min、冬期 UTC 一致)、以後 = 純 UTC。
    anchor 証跡: 2023-08-04 NFP 13:30 (London) / 2023-08-08 Harker 12:15 (=8:15 ET, UTC) /
    2023-08-10 CPI 12:30 (=8:30 ET, UTC)。2024 年以降の NFP/CPI 全 anchor offset 0。
  - **actual 列は 2023-08 で充填停止** (2023-09 以降 0/月) — 判定対象系列 (NFP/CPI) の
    actual first print は tools/ff_gap_bls_first_prints.py が BLS 一次リリースから補完。
  - impact 文字は faireconomy feed 表記へ写像: H→High / M→Medium / L→Low / N→Holiday。

規律: モジュールトップ副作用なし / silent except なし / 乱数なし。

CLI:
  python3 tools/ff_gap_prepare_r4f.py fetch       # dump 取得 + 整形 (network)
  python3 tools/ff_gap_prepare_r4f.py build-only  # 既存 snapshot から整形 (offline)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

R4F_URL = "https://robots4forex.com/news/news.php"
RAW_PATH = os.path.join(_REPO, "data", "cache", "rates", "raw", "r4f_news.csv")
OUT_DIR = os.path.join(_REPO, "knowledge-base", "raw", "bt-results", "e7")

GAP_START = "2014-01-01"      # §3.4 discovery 窓 per-pair floor (歴史パネル込み一括)
GAP_END = "2026-07-20"        # go-forward capture 開始 (2026-07-21) の前日
TZ_SWITCH = "2023-08-07"      # この日以降は UTC、前日以前は Europe/London 現地時刻
_LONDON = ZoneInfo("Europe/London")

IMPACT_MAP = {"H": "High", "M": "Medium", "L": "Low", "N": "Holiday"}


def _http_get(url: str, timeout: int = 300) -> bytes:
    if not url.startswith("https://robots4forex.com/"):
        raise ValueError(f"URL not allowed: {url[:80]}")
    resp = requests.get(url, headers={"User-Agent": "fx-ai-trader-e7/1.0"},
                        timeout=timeout, allow_redirects=True)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {url[:80]}")
    return resp.content


def normalize_time(date_str: str, time_str: str) -> str:
    """R4F の (date, time) → ISO8601 UTC。2023-08-07 切替規約を適用。"""
    d = date_str.replace("/", "-")
    dt = datetime.strptime(f"{d} {time_str}", "%Y-%m-%d %H:%M")
    if d < TZ_SWITCH:
        dt = dt.replace(tzinfo=_LONDON)   # fold=0: BST/GMT は日付で一意 (深夜重複は 10-11月の 01:00-02:00 のみ、カレンダー実害なし)
    else:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_r4f(text: str) -> list:
    """R4F CSV (ヘッダなし 10 列) → 行 dict list。列 6/7 非空は fail-loud。"""
    rows = []
    unexpected = 0
    for i, row in enumerate(csv.reader(io.StringIO(text))):
        if not row or len(row) != 10:
            raise ValueError(f"R4F row {i}: expected 10 cols, got {len(row)}: {row[:5]}")
        if row[5].strip() or row[6].strip():
            unexpected += 1
            if unexpected <= 3:
                print(f"WARN: col6/7 non-empty at row {i}: {row}", file=sys.stderr)
        rows.append({
            "date": row[0].replace("/", "-"), "time": row[1],
            "currency": row[2].strip().upper(), "impact_raw": row[3].strip(),
            "title": row[4].strip(),
            "actual": row[7].strip(), "forecast": row[8].strip(),
            "previous": row[9].strip(),
        })
    if unexpected:
        raise ValueError(f"R4F 列 6/7 に非空 {unexpected} 行 — 列仕様が変わった。整形規則を再検証すること")
    return rows


def build_import_rows(rows: list, start: str = GAP_START, end: str = GAP_END) -> tuple:
    """gap 窓の行を import 互換 dict へ。(rows, stats) を返す。key 重複は後勝ちで数える。"""
    out = {}
    stats = {"in_window": 0, "dup_key": 0, "by_year": {}, "actual_filled": 0,
             "impact_unknown": 0}
    for r in rows:
        if not (start <= r["date"] <= end):
            continue
        stats["in_window"] += 1
        impact = IMPACT_MAP.get(r["impact_raw"])
        if impact is None:
            stats["impact_unknown"] += 1
            raise ValueError(f"unknown impact letter {r['impact_raw']!r}: {r}")
        key = (r["currency"], r["title"], normalize_time(r["date"], r["time"]))
        if key in out:
            stats["dup_key"] += 1
        y = r["date"][:4]
        stats["by_year"][y] = stats["by_year"].get(y, 0) + 1
        if r["actual"]:
            stats["actual_filled"] += 1
        out[key] = {
            "country": key[0], "title": key[1], "event_time_utc": key[2],
            "impact": impact, "forecast": r["forecast"],
            "previous": r["previous"], "actual": r["actual"],
        }
    return list(out.values()), stats


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_from_raw(raw_path: str = RAW_PATH, out_dir: str = OUT_DIR) -> dict:
    with open(raw_path, encoding="utf-8") as fh:
        rows = parse_r4f(fh.read())
    import_rows, stats = build_import_rows(rows)
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, "ff_calendar_r4f_2014_2026.csv")
    cols = ["country", "title", "event_time_utc", "impact",
            "forecast", "previous", "actual"]
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in sorted(import_rows, key=lambda x: (x["event_time_utc"],
                                                    x["country"], x["title"])):
            w.writerow(r)
    manifest = {
        "tool": "ff_gap_prepare_r4f",
        "source_url": R4F_URL,
        "gap_window": [GAP_START, GAP_END],
        "tz_rule": f"date < {TZ_SWITCH}: Europe/London local → UTC / それ以降: UTC そのまま",
        "impact_map": IMPACT_MAP,
        "raw_sha256": _sha256(raw_path),
        "raw_rows_total": len(rows),
        "stats": stats,
        "out_csv": {"path": os.path.relpath(out_csv, _REPO),
                    "sha256": _sha256(out_csv),
                    "rows": len(import_rows)},
    }
    mpath = os.path.join(out_dir, "ff_calendar_r4f_manifest.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print(f"import CSV: {out_csv} ({len(import_rows):,} rows)")
    print(f"manifest: {mpath}")
    print(f"stats: {json.dumps(stats, ensure_ascii=False)}")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode")
    for name in ("fetch", "build-only"):
        sp = sub.add_parser(name)
        sp.add_argument("--raw-path", default=RAW_PATH)
        sp.add_argument("--out-dir", default=OUT_DIR)
    args = parser.parse_args(argv)
    if args.mode == "fetch":
        os.makedirs(os.path.dirname(args.raw_path), exist_ok=True)
        data = _http_get(R4F_URL)
        with open(args.raw_path, "wb") as fh:
            fh.write(data)
        print(f"fetched: {len(data):,} bytes → {args.raw_path}")
        build_from_raw(args.raw_path, args.out_dir)
        return 0
    if args.mode == "build-only":
        build_from_raw(args.raw_path, args.out_dir)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
