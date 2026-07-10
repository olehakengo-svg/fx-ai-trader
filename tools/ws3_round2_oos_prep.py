#!/usr/bin/env python3
"""WS3 round-2 OOS 検証 — 切詰め parquet 準備 (rule:R1、pre-reg §3)

pre-reg: knowledge-base/wiki/decisions/ws3-round2-explore-prereg-2026-07-10.md §3
OOS 窓 = 2024-07-07〜2025-07-07。stage-1 と同方式の look-ahead 遮断:
末尾 2025-07-07 で切詰めた parquet を配置し lookback 365d (loader は tail−365d 窓)。

- EUR_USD / USD_JPY / GBP_USD: main repo の 12y/長期 Massive キャッシュを
  末尾 2025-07-07T23:59:59Z で切詰めて worktree data/cache/massive/ に配置
  (worktree では全て未追跡ファイル — コミットされない)
- GBP_JPY: ローカル 15m が 2025-04-11〜 のみのため Massive API から遡及取得
  (fetch_ohlcv_massive = 既存経路) し、同じ末尾で切詰め
- OOS エントリー抽出は tools/ws3_mfe_scan.py --pairs GBP_USD,GBP_JPY
  --split-direction --out-suffix _round2_oos で行う (stage-1 OOS 実行と同一エンジン)。
  EUR_USD / USD_JPY のエントリーは stage-1 凍結資産
  raw/bt-results/ws3_asymmetry_oos_2026_07_entries.json (全セル N=4,980) を再利用

実行: MASSIVE_API_KEY=... python3 tools/ws3_round2_oos_prep.py --main-repo <path>
"""

import argparse
import json
import os
import sys

TAIL_CUT = "2025-07-07T23:59:59+00:00"   # stage-1 と同一の切詰め末尾
GBPJPY_FETCH_DAYS = 740                   # now−743d ≈ 2024-06-27 (窓開始+warmup を被覆)
SLICE_PAIRS = ["EUR_USD", "USD_JPY", "GBP_USD"]

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "data", "cache", "massive")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--main-repo", default="/Users/jg-n-012/test/fx-ai-trader",
                    help="長期 parquet キャッシュの取得元リポジトリ")
    args = ap.parse_args()

    sys.path.insert(0, REPO)
    import pandas as pd
    from modules.data import fetch_ohlcv_massive

    cut = pd.Timestamp(TAIL_CUT)
    meta = {}

    for pair in SLICE_PAIRS:
        src = os.path.join(args.main_repo, "data", "cache", "massive",
                           f"{pair}_15m.parquet")
        df = pd.read_parquet(src)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        df = df[df.index <= cut]
        out = os.path.join(OUT_DIR, f"{pair}_15m.parquet")
        df.to_parquet(out)
        meta[pair] = {"source": "main-repo slice", "rows": len(df),
                      "tail": str(df.index.max()),
                      "window_start_365d": str(df.index.max() - pd.Timedelta(days=365))}

    # GBP_JPY: Massive 遡及取得
    fresh = fetch_ohlcv_massive("GBP_JPY", "15m", GBPJPY_FETCH_DAYS)
    fresh = fresh[fresh.index <= cut]
    if "vwap" not in fresh.columns:
        fresh["vwap"] = fresh["Close"]
    out = os.path.join(OUT_DIR, "GBP_JPY_15m.parquet")
    fresh.to_parquet(out)
    deltas = fresh.index.to_series().diff().dropna()
    big_gaps = deltas[deltas > pd.Timedelta(days=3)]
    meta["GBP_JPY"] = {"source": f"Massive API fetch (days={GBPJPY_FETCH_DAYS})",
                       "rows": len(fresh),
                       "head": str(fresh.index.min()),
                       "tail": str(fresh.index.max()),
                       "window_start_365d": str(fresh.index.max() - pd.Timedelta(days=365)),
                       "gaps_gt_3d": [str(t) for t in big_gaps.index]}

    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
