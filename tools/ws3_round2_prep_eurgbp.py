#!/usr/bin/env python3
"""WS3 round-2: EUR_GBP 15m 探索窓 parquet 準備 (rule:R3、純診断データ準備)

pre-reg: knowledge-base/wiki/decisions/ws3-round2-explore-prereg-2026-07-10.md §2(b)
round-1 h24 表に現れなかった production shadow 母集団ペア = EUR_GBP のみ
(MODE_CONFIG compute_daytrade_signal×15m: USD_JPY/EUR_USD/GBP_USD/EUR_JPY/GBP_JPY/EUR_GBP。
 XAU_USD は auto_start=False + Massive 対象外規約で対象外)。

窓の同一性 (look-ahead 遮断):
- round-1 (2026-07-08 実行) の loader 窓 = parquet tail − 365d。round-1 入力の
  EUR_JPY_15m.parquet tail = 2026-07-08T03:45Z → 窓開始 2025-07-08T03:45Z。
- 本スクリプトは EUR_GBP parquet を [2025-07-08T03:45Z, 2026-07-08T03:45Z] に
  正確に切り出して worktree の data/cache/massive/ に書く (loader cutoff =
  tail−365d = 窓開始 = データ先頭 → 全行使用、round-1 と同一窓)。
- OOS 窓 (2024-07-07〜2025-07-07) の行は書き出さない。既存 12y parquet の読込は
  時刻 slice のみで、OOS 行に対する統計計算は一切行わない。
- 2026-05-05 06:00 以降の欠損 tail は Massive API (modules.data.fetch_ohlcv_massive
  = tools/fetch_massive_data.py と同一経路) から取得して連結。

実行: MASSIVE_API_KEY=... python3 tools/ws3_round2_prep_eurgbp.py
"""

import json
import os
import sys

WINDOW_START = "2025-07-08T03:45:00+00:00"  # round-1 EUR_JPY window start
WINDOW_END = "2026-07-08T03:45:00+00:00"    # round-1 EUR_JPY parquet tail
FETCH_DAYS = 75  # now-78d ≈ 2026-04-23 — 既存 parquet tail (2026-05-05) を跨ぐ

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PQ = os.path.join(REPO, "data", "cache", "massive", "EUR_GBP_15m.parquet")


def main() -> None:
    sys.path.insert(0, REPO)
    import pandas as pd
    from modules.data import fetch_ohlcv_massive

    start = pd.Timestamp(WINDOW_START)
    end = pd.Timestamp(WINDOW_END)

    base = pd.read_parquet(PQ)
    if base.index.tz is None:
        base.index = base.index.tz_localize("UTC")
    base_tail = base.index.max()
    # 時刻 slice のみ (OOS 行は統計に触れず捨てる)
    base = base[(base.index >= start) & (base.index <= end)]

    fetched_rows = 0
    if base_tail < end:
        fresh = fetch_ohlcv_massive("EUR_GBP", "15m", FETCH_DAYS)
        fresh = fresh[(fresh.index > base_tail) & (fresh.index <= end)]
        if "vwap" not in fresh.columns:
            fresh["vwap"] = fresh["Close"]
        fetched_rows = len(fresh)
        base = pd.concat([base, fresh[base.columns]])
        base = base[~base.index.duplicated(keep="last")].sort_index()

    # 連結境界の連続性チェック (週末ギャップ以外で3日超の穴がないか)
    deltas = base.index.to_series().diff().dropna()
    big_gaps = deltas[deltas > pd.Timedelta(days=3)]
    meta = {
        "pair": "EUR_GBP", "tf": "15m",
        "window": [str(base.index.min()), str(base.index.max())],
        "rows": len(base),
        "rows_from_existing_parquet": len(base) - fetched_rows,
        "rows_fetched_massive": fetched_rows,
        "gaps_gt_3d": [str(t) for t in big_gaps.index],
        "oos_rows_written": int((base.index < start).sum()),
    }
    assert meta["oos_rows_written"] == 0
    base.to_parquet(PQ)
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
