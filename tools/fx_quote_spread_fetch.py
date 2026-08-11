#!/usr/bin/env python3
"""W3-2 fx_quote_spread_state — sampled BBO spread panel fetcher (台帳 #17).

MASSIVE /v3/quotes (Polygon 互換) から、NY ローカル固定 8 スロット/日 × limit 200
のサンプリングで pair × 日 × スロットのスプレッド統計パネルを構築する。

設計 (敵対的検証 [W3-2] 条件対応):
- グリッドは America/New_York ローカル時刻固定 (条件 4 DST: ローカル時刻基準を採択。
  NY セッション diurnal と 17:00 NY ロールオーバーが年間を通じ同一スロットに揃う)
- 取得はデータ獲得のみ。baseline / イベント判定 / リターン結合は一切行わない
  (条件 1 の「摩擦測定を forward return 接触前に」の分離を fetch 層で保証)
- quote レベル QA (条件 3): クロス/ロック (spread<=0) は spread 統計から除外し
  crossed 件数を保存、負値 bid/ask 除外、サンプル窓 [target, target+30min] 外は不使用
- 土曜行 (条件 3): 市場閉場窓 (金 15:00 NY スロットの後〜日 18:00 NY スロットの前) は
  グリッド自体を生成しない。閉場境界の漏れ quote は窓 tolerance で自然に invalid 化

Usage:
  MASSIVE_API_KEY=... python3 tools/fx_quote_spread_fetch.py \
      --pair EUR_USD --start 2014-01-01 --end 2014-12-31 \
      --out data/external/quote_spread/EUR_USD_2014.parquet
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]

BASE_URL = "https://api.massive.com/v3/quotes"
NY = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

# NY ローカル固定グリッド (FX 営業日 17:00→17:00 NY、境界 17:00 を避ける)
NY_SLOTS = [18, 21, 0, 3, 6, 9, 12, 15]

# サンプル窓: target から 30 分以内の quote のみ採用
WINDOW_SEC = 30 * 60
LIMIT = 200
# 有効サンプルに必要な窓内 quote 最小数
MIN_QUOTES = 30

PIP = {"EUR_USD": 1e4, "GBP_USD": 1e4, "USD_JPY": 1e2}
TICKER = {"EUR_USD": "C:EURUSD", "GBP_USD": "C:GBPUSD", "USD_JPY": "C:USDJPY"}


def build_grid(start: dt.date, end: dt.date) -> list[dt.datetime]:
    """NY ローカル 8 スロット/日のサンプル目標時刻 (UTC aware) を生成。

    市場閉場 (金 17:00 NY 〜 日 17:00 NY) に入るスロットは生成しない。
    スロットの属する「FX 営業日」ではなくカレンダー日ベースで単純に列挙し、
    閉場窓のみ除外する (金 18:00/21:00、土全部、日 0/3/6/9/12/15 が除外される)。
    """
    out: list[dt.datetime] = []
    d = start
    while d <= end:
        for h in NY_SLOTS:
            local = dt.datetime(d.year, d.month, d.day, h, 0, tzinfo=NY)
            wd = local.weekday()  # Mon=0 ... Sun=6
            if wd == 5:  # Saturday: closed all day
                continue
            if wd == 4 and h >= 17:  # Friday after close
                continue
            if wd == 6 and h < 17:  # Sunday before open
                continue
            out.append(local.astimezone(UTC))
        d += dt.timedelta(days=1)
    return sorted(set(out))


def fetch_sample(session: requests.Session, ticker: str, target_utc: dt.datetime,
                 pip_mult: float, max_retries: int = 5) -> dict:
    """1 サンプル = 1 リクエスト。窓内 quote の spread/mid 統計を返す。"""
    ns = int(target_utc.timestamp() * 1e9)
    params = {"timestamp.gte": ns, "limit": LIMIT, "order": "asc", "sort": "timestamp"}
    body = None
    for attempt in range(max_retries):
        try:
            r = session.get(f"{BASE_URL}/{ticker}", params=params, timeout=30)
            if r.status_code == 200:
                body = r.json()
                break
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2.0 * (attempt + 1))
                continue
            # その他 4xx は恒久エラーとして欠測記録
            body = {"results": [], "_http": r.status_code}
            break
        except requests.RequestException:
            time.sleep(2.0 * (attempt + 1))
    row = {
        "ts_utc": target_utc,
        "n_raw": 0, "n_used": 0, "n_crossed": 0,
        "spread_med_pips": None, "spread_p90_pips": None, "spread_max_pips": None,
        "mid_med": None, "first_quote_lag_s": None,
    }
    if body is None:
        row["n_raw"] = -1  # 通信恒久失敗マーカー
        return row
    results = body.get("results", []) or []
    row["n_raw"] = len(results)
    if not results:
        return row
    lo, hi = ns, ns + WINDOW_SEC * int(1e9)
    spreads: list[float] = []
    mids: list[float] = []
    crossed = 0
    first_lag = None
    for q in results:
        ts = q.get("participant_timestamp")
        bid, ask = q.get("bid_price"), q.get("ask_price")
        if ts is None or bid is None or ask is None or bid <= 0 or ask <= 0:
            continue
        if ts < lo or ts > hi:
            continue
        if first_lag is None:
            first_lag = (ts - ns) / 1e9
        sp = (ask - bid) * pip_mult
        if sp <= 0:
            crossed += 1
            continue
        spreads.append(sp)
        mids.append((bid + ask) / 2.0)
    row["n_used"] = len(spreads)
    row["n_crossed"] = crossed
    row["first_quote_lag_s"] = first_lag
    if spreads:
        spreads_sorted = sorted(spreads)
        row["spread_med_pips"] = statistics.median(spreads_sorted)
        row["spread_p90_pips"] = spreads_sorted[min(len(spreads_sorted) - 1,
                                                    int(len(spreads_sorted) * 0.9))]
        row["spread_max_pips"] = spreads_sorted[-1]
        row["mid_med"] = statistics.median(mids)
    return row


def fetch_panel(pair: str, start: dt.date, end: dt.date, api_key: str,
                workers: int = 4) -> pd.DataFrame:
    ticker = TICKER[pair]
    pip_mult = PIP[pair]
    grid = build_grid(start, end)
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {api_key}"
    rows: list[dict] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_sample, session, ticker, ts, pip_mult): ts
                   for ts in grid}
        done = 0
        for fut in as_completed(futures):
            rows.append(fut.result())
            done += 1
            if done % 500 == 0:
                rate = done / max(1e-9, time.time() - t0)
                print(f"  {pair} {done}/{len(grid)} ({rate:.1f} req/s)", flush=True)
    df = pd.DataFrame(rows).sort_values("ts_utc").reset_index(drop=True)
    df["pair"] = pair
    ny_ts = df["ts_utc"].dt.tz_convert("America/New_York")
    df["ny_date"] = ny_ts.dt.date.astype(str)
    df["ny_slot"] = ny_ts.dt.hour
    return df


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", required=True, choices=sorted(TICKER))
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    api_key = os.environ.get("MASSIVE_API_KEY", "")
    if not api_key:
        raise ValueError("MASSIVE_API_KEY not set")
    out = Path(args.out)
    if out.exists():
        print(f"skip (exists): {out}")
        return 0
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    df = fetch_panel(args.pair, start, end, api_key, workers=args.workers)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out)
    summary = {
        "pair": args.pair, "start": args.start, "end": args.end,
        "samples": int(len(df)),
        "valid": int((df["n_used"] >= MIN_QUOTES).sum()),
        "empty": int((df["n_raw"] == 0).sum()),
        "comm_fail": int((df["n_raw"] < 0).sum()),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
