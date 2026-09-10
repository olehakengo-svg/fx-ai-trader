#!/usr/bin/env python3
"""mof_intervention_watch.py — E-A 介入検知器の defensive alert 化 (監視のみ).

凍結 rule (mof-intervention-forward-prereg-2026-07-24.md §2.2 / §4.1 / §5.2 — LOCKED):
  candidate(d) = 1 ⟺ UTC-day バーで close/open − 1 ≤ −Y% かつ
                      range(d) ≥ X × trailing-20d median range
  凍結 (X, Y) = (2.0, 0.25%) — **再校正禁止・as-is 流用のみ**
  (intervention-history-anatomy-2026-08-18.md: 「再校正禁止、as-is 流用のみ」)。
  E-A は 2026-08 verdict で forward 的中 p=0.0143 (検知器の real-time 実行可能性は実証済み)。

スコープ境界 (絶対):
  - **監視 + 通知 + KB 記録のみ**。live gating (発火後 48h 新規ロング禁止等) の自動執行は
    実装しない — それは §5.5 Variant B の別 pre-reg + user 最終承認事項 (E-C FAIL により
    SELL 執行系は stage-2 進行不可)。本ツールは order/gating 系 module を import しない。
  - **candidate ≠ 介入ラベル**。公式ラベルは MoF 開示のみ (価格推定でのラベリングは
    #4 再判定 OOS burn で禁止 — project_t5_restore_mof_crosslock_2026_08_10)。
  - 判定 grade = alert (yfinance 1h → UTC-day 集計)。verdict-grade 測定 (11-14 再判定) は
    凍結どおり Massive 15m mid — 本ツールの記録を S (candidate list) に流用してはならない。
    yfinance **日足** は UTC ずれ lesson があるため使わない (intraday 集計はずれの対象外だが
    grade フィールドでベンダー系統を永続記録する)。

実行: GitHub Actions cron (.github/workflows/intervention-watch.yml) が UTC-day 完成後に
  前 UTC 営業日を 1 回評価 → knowledge-base/raw/intervention_watch/YYYY-MM.jsonl に追記
  (この JSONL が dedup 状態を兼ねる — 同日再評価は no-op)。candidate=1 なら Discord 通知。

CLI:
  python3 tools/mof_intervention_watch.py run [--day YYYY-MM-DD] [--to-discord]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

# 凍結識別 rule (§5.2) — 変更・再校正禁止。校正は 2022/2024 の 7 日 + placebo のみ (§4.1)。
FROZEN_X = 2.0    # range(d) >= X * trailing-20d median range
FROZEN_Y = 0.25   # close/open - 1 <= -Y%
RANGE_MED_LOOKBACK = 20

OUT_DIR = os.path.join(_REPO, "knowledge-base", "raw", "intervention_watch")
GRADE = "alert(yfinance-1h-utc-day)"  # verdict-grade は Massive 15m (§2.2) — 別系統

_DISCORD_PREFIXES = ("https://discord.com/api/webhooks/",
                     "https://discordapp.com/api/webhooks/")


# ─── data layer (network) ────────────────────────────────────────────────────
def fetch_bars_yf(period: str = "3mo") -> pd.DataFrame:
    """USD/JPY 1h bars (yfinance JPY=X) → tz-aware UTC OHLC frame。"""
    import yfinance as yf

    df = yf.download("JPY=X", period=period, interval="1h", progress=False)
    if df is None or df.empty:
        raise RuntimeError("yfinance returned no data for JPY=X 1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close"]].copy()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    return df.sort_index()


# ─── 凍結 rule (pure — offline テスト対象) ───────────────────────────────────
def build_daily(bars: pd.DataFrame) -> pd.DataFrame:
    """intraday bars → UTC-day バー + trailing-20d median range (§2.2 凍結集計).

    tools/mof_forward_verdict.py (verdict-grade 実装) と同一の構成:
    UTC-day 集計 → weekday<5 → range / co_ret → rolling(20).median().shift(1)。
    """
    g = bars.groupby(bars.index.date)
    daily = pd.DataFrame({
        "open": g["Open"].first(),
        "high": g["High"].max(),
        "low": g["Low"].min(),
        "close": g["Close"].last(),
        "n_bars": g.size(),
    })
    daily = daily[[d.weekday() < 5 for d in daily.index]]
    daily["range"] = daily["high"] - daily["low"]
    daily["co_ret_pct"] = (daily["close"] / daily["open"] - 1.0) * 100.0
    daily["med20_range"] = daily["range"].rolling(RANGE_MED_LOOKBACK).median().shift(1)
    daily["range_ratio"] = daily["range"] / daily["med20_range"]
    return daily


def rule_candidate(co_ret_pct: float, range_ratio: float) -> bool:
    """凍結 rule as-is: co_ret ≤ −0.25% ∧ range ≥ 2.0 × med20。"""
    return bool(co_ret_pct <= -FROZEN_Y and range_ratio >= FROZEN_X)


def last_completed_utc_weekday(today: dt.date) -> dt.date:
    """直近の完了 UTC 営業日 (today の前日から土日を遡ってスキップ)。"""
    d = today - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def evaluate_day(daily: pd.DataFrame, day: dt.date) -> dict:
    """1 営業日を凍結 rule で評価して record dict を返す。"""
    base = {"day": day.isoformat(), "rule": f"(X,Y)=({FROZEN_X},{FROZEN_Y}%)",
            "grade": GRADE}
    if day not in daily.index:
        return {**base, "status": "no_data",
                "note": "UTC-day バー不在 (休場 or ベンダー欠損) — candidate 判定なし"}
    row = daily.loc[day]
    if pd.isna(row["med20_range"]) or row["med20_range"] <= 0:
        raise RuntimeError(f"med20_range 不成立 @ {day} — 取得窓が短すぎる (構造エラー)")
    rec = {
        **base,
        "status": "evaluated",
        "co_ret_pct": round(float(row["co_ret_pct"]), 4),
        "range": round(float(row["range"]), 4),
        "med20_range": round(float(row["med20_range"]), 4),
        "range_ratio": round(float(row["range_ratio"]), 3),
        "n_bars": int(row["n_bars"]),
        "candidate": rule_candidate(float(row["co_ret_pct"]), float(row["range_ratio"])),
    }
    if rec["n_bars"] < 12:
        rec["note"] = "thin_data (n_bars<12) — 判定値は参考扱い"
    return rec


# ─── KB 記録 (JSONL = dedup 状態) ────────────────────────────────────────────
def record_path(day: dt.date, out_dir: str = OUT_DIR) -> str:
    return os.path.join(out_dir, f"{day.strftime('%Y-%m')}.jsonl")


def already_recorded(day: dt.date, out_dir: str = OUT_DIR) -> bool:
    p = record_path(day, out_dir)
    if not os.path.exists(p):
        return False
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            if line.strip() and json.loads(line).get("day") == day.isoformat():
                return True
    return False


def append_record(rec: dict, out_dir: str = OUT_DIR) -> str:
    os.makedirs(out_dir, exist_ok=True)
    p = record_path(dt.date.fromisoformat(rec["day"]), out_dir)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return p


# ─── 通知 ────────────────────────────────────────────────────────────────────
def format_alert(rec: dict) -> str:
    return (
        "🚨 **E-A 介入シグネチャ検知 (defensive alert — 監視のみ)**\n"
        f"UTC-day {rec['day']} (東京営業日): co_ret {rec['co_ret_pct']:+.2f}% ≤ −{FROZEN_Y}%"
        f" ∧ range {rec['range']:.2f} = med20×{rec['range_ratio']:.2f} ≥ ×{FROZEN_X}\n"
        "・凍結 rule as-is (#4 §2.2、E-A forward 実証 p=0.0143)。**candidate ≠ 介入ラベル**"
        " (公式確定は MoF 開示のみ)\n"
        "・自動 gating はしない。参考 prior: 初撃後の追撃は 48h 帯に集中 (N=7 記述)、"
        "介入後 10d は +188p リトレース実測 (E-C) — 対応は user 判断\n"
        "・記録: knowledge-base/raw/intervention_watch/ (grade=alert、verdict 流用禁止)"
    )


def post_discord(content: str, webhook_url: str) -> bool:
    import requests

    if not webhook_url.startswith(_DISCORD_PREFIXES):
        raise ValueError("DISCORD_WEBHOOK_URL が Discord webhook 形式でない")
    resp = requests.post(webhook_url, json={"content": content[:2000]}, timeout=10)
    return resp.status_code in (200, 204)


# ─── 実行フロー ──────────────────────────────────────────────────────────────
def run(day: dt.date | None = None, to_discord: bool = False,
        out_dir: str = OUT_DIR) -> dict:
    if day is None:
        day = last_completed_utc_weekday(dt.datetime.now(dt.timezone.utc).date())
    if already_recorded(day, out_dir):
        print(f"already recorded: {day} — no-op (dedup)")
        return {"day": day.isoformat(), "status": "already_recorded"}

    daily = build_daily(fetch_bars_yf())
    rec = evaluate_day(daily, day)

    if rec.get("candidate"):
        rec["alerted"] = False
        if to_discord:
            url = os.environ.get("DISCORD_WEBHOOK_URL", "")
            if url:
                rec["alerted"] = post_discord(format_alert(rec), url)
            else:
                print("WARN: DISCORD_WEBHOOK_URL 未設定 — 通知スキップ (記録は残す)")

    p = append_record(rec, out_dir)
    print(f"recorded: {p}")
    print(json.dumps(rec, ensure_ascii=False))
    return rec


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode")
    sp = sub.add_parser("run")
    sp.add_argument("--day", default=None, help="評価する UTC 営業日 (default: 直近完了日)")
    sp.add_argument("--to-discord", action="store_true")
    sp.add_argument("--out-dir", default=OUT_DIR)
    args = parser.parse_args(argv)
    if args.mode == "run":
        day = dt.date.fromisoformat(args.day) if args.day else None
        run(day=day, to_discord=args.to_discord, out_dir=args.out_dir)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
