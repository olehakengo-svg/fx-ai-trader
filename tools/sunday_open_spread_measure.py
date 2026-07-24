#!/usr/bin/env python3
"""
Sunday-open spread measurement — weekend_gap family #3 R1 step (i).

Purpose (pre-reg §9 / verdict §11 固定分岐 2-(i)):
  OOS confirm の gate (c) は stressed RT = 「通常 RT の 3 倍」という *仮定*
  (EUR_USD 6.0p / USD_JPY 6.42p / AUD_USD 7.5p) で判定された。
  本ツールは OANDA live feed の歴史 bid/ask candle (price=BA) で直近 N 週末の
  Sunday open スプレッドを遡及実測し、3x 仮定が保守的だったかを検証する。
  AUD_USD の通常 RT 2.5p (KB friction table 外の理論仮置き) も
  火曜 12:00 UTC 実測ベースラインで突合する。

Read-only guarantee:
  GET /v3/instruments/:instrument/candles のみ使用。注文・口座変更 API は
  一切呼ばない。live パラメータ変更ゼロ (pre-reg §9)。

Definitions (task-frozen):
  - Sunday open      = Sun 20:00 UTC 以降の最初の complete M1 バー
                       (夏時間期は実開場 ~21:00 UTC。実測バー時刻を記録)
  - bar spread       = ask.o - bid.o (バー境界の気配。close 側も記録)
  - measured RT      = spread + 0.5p (想定 slippage、KB friction table 準拠)
  - stressed 3x 仮定 = 3 x normal RT (frozen: 6.0 / 6.42 / 7.5p)
    → spread 換算閾値 = 3 x RT - 0.5p slippage
  - normal baseline  = 同週火曜 12:00-13:00 UTC の M1 spread p50

Outputs:
  bt-results/sunday_open_spread-<date>.json  (per-weekend detail + aggregates)
  reports/sunday_open_spread-<date>.md       (summary + 執行設計への入力)

Usage:
  python3 tools/sunday_open_spread_measure.py [--weekends 12] [--date 2026-07-24]

No module-top side effects. No silent excepts. Token is never printed.
"""
import argparse
import json
import os
import statistics
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── frozen constants (pre-reg §2 / §4(c) — 変更禁止) ─────────────────────
PAIRS = ("EUR_USD", "USD_JPY", "AUD_USD")     # arm B pooled set (GBP除外)
PIP = {"EUR_USD": 1e-4, "USD_JPY": 1e-2, "AUD_USD": 1e-4}
NORMAL_RT = {"EUR_USD": 2.0, "USD_JPY": 2.14, "AUD_USD": 2.5}   # KB friction
STRESSED_RT = {p: 3.0 * NORMAL_RT[p] for p in PAIRS}            # gate(c) 仮定
SLIPPAGE_P = 0.5              # KB friction table の per-pair slippage 仮定
STRESSED_RT_ARM_B = 6.56      # pre-reg 凍結 (explore N 加重、参考値)

# ── measurement design ───────────────────────────────────────────────────
# spot offsets (min from actual open bar): task 指定の 初バー/+15m/+30m/+1h/+2h/+4h
SPOT_OFFSETS_MIN = (15, 30, 60, 120, 240)
SPOT_WINDOW_MIN = 5           # offset t の値 = [t, t+5m) 内バー spread の median
# normalization curve buckets (min from open)
BUCKETS = ((0, 5), (5, 15), (15, 30), (30, 60), (60, 120), (120, 240))
SUSTAIN_WIN_MIN = 15          # sustained 判定: [t, t+15m) の median <= 閾値
NORMAL_MULTIPLES = (1.5, 2.0, 3.0)   # 「通常 x Y に収まる」報告用
FETCH_PRE_MIN = 60            # Sun 20:00 UTC から fetch (実開場 21:00/22:00 両対応)
FETCH_POST_MIN = 265          # open+4h の spot window (+245m) まで確実にカバー
BASELINE_HOUR_UTC = 12        # 同週火曜 12:00-13:00 UTC
REQUEST_SLEEP_S = 0.15
MAX_RETRY = 3


def load_env_file(path: Path) -> None:
    """.env を os.environ に読み込む (既存値は上書きしない。値は出力しない)。"""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def last_n_sundays(n: int, before: date) -> List[date]:
    """`before` (exclusive) より前の直近 n 個の日曜を新しい順で返す。"""
    d = before - timedelta(days=1)
    while d.weekday() != 6:  # 6 = Sunday
        d -= timedelta(days=1)
    return [d - timedelta(weeks=k) for k in range(n)]


def fetch_ba_bars(client, pair: str, t0: datetime, t1: datetime) -> List[dict]:
    """M1 BA candles を取得し、complete バーの spread 系列を返す。

    Returns: [{"time": datetime, "spread_o": pips, "spread_c": pips,
               "volume": int}, ...]  (時刻昇順)
    Raises RuntimeError on persistent API failure (silent except 禁止).
    """
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    last_err = None
    for attempt in range(MAX_RETRY):
        ok, data = client.get_candles(
            pair, granularity="M1", price="BA",
            from_time=t0.strftime(fmt), to_time=t1.strftime(fmt))
        if ok:
            bars = []
            for c in data.get("candles", []):
                if not c.get("complete"):
                    continue
                ts = datetime.strptime(
                    c["time"][:19], "%Y-%m-%dT%H:%M:%S").replace(
                    tzinfo=timezone.utc)
                pip = PIP[pair]
                bars.append({
                    "time": ts,
                    "spread_o": (float(c["ask"]["o"]) - float(c["bid"]["o"])) / pip,
                    "spread_c": (float(c["ask"]["c"]) - float(c["bid"]["c"])) / pip,
                    "volume": int(c.get("volume", 0)),
                })
            return bars
        last_err = data
        time.sleep(1.0 + attempt)
    raise RuntimeError(
        f"OANDA candles fetch failed for {pair} {t0}..{t1}: {last_err}")


def pctile(vals: List[float], q: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = q * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    frac = idx - lo
    return round(s[lo] * (1 - frac) + s[hi] * frac, 3)


def window_median(bars: List[dict], open_t: datetime,
                  lo_min: float, hi_min: float) -> Optional[float]:
    vals = [b["spread_o"] for b in bars
            if lo_min <= (b["time"] - open_t).total_seconds() / 60.0 < hi_min]
    return round(statistics.median(vals), 3) if vals else None


def sustained_below(bars: List[dict], open_t: datetime,
                    threshold_p: float) -> Optional[float]:
    """[t, t+15m) の median spread <= threshold となる最初の t (min from open)。

    バーが存在する時刻のみ候補 (Sunday open は板が薄くバーが疎)。
    4h 窓内で未達なら None。
    """
    times = sorted((b["time"] - open_t).total_seconds() / 60.0 for b in bars)
    for t in times:
        if t > 240:
            break
        med = window_median(bars, open_t, t, t + SUSTAIN_WIN_MIN)
        if med is not None and med <= threshold_p:
            return round(t, 1)
    return None


def measure_weekend(client, pair: str, sunday: date) -> dict:
    """1 ペア x 1 週末の Sunday open spread プロファイルを実測する。"""
    t0 = datetime(sunday.year, sunday.month, sunday.day, 20, 0,
                  tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=FETCH_PRE_MIN + FETCH_POST_MIN)
    bars = fetch_ba_bars(client, pair, t0, t1)
    if not bars:
        return {"sunday": sunday.isoformat(), "status": "no_data"}

    open_bar = bars[0]
    open_t = open_bar["time"]

    # 同週火曜 12:00-13:00 UTC baseline
    tue = sunday + timedelta(days=2)
    b0 = datetime(tue.year, tue.month, tue.day, BASELINE_HOUR_UTC, 0,
                  tzinfo=timezone.utc)
    tue_bars = fetch_ba_bars(client, pair, b0, b0 + timedelta(hours=1))
    tue_p50 = (round(statistics.median([b["spread_o"] for b in tue_bars]), 3)
               if tue_bars else None)

    spots = {"first_bar": round(open_bar["spread_o"], 3)}
    for off in SPOT_OFFSETS_MIN:
        spots[f"+{off}m"] = window_median(bars, open_t, off, off + SPOT_WINDOW_MIN)

    bucket_stats = {}
    for lo, hi in BUCKETS:
        vals = [b["spread_o"] for b in bars
                if lo <= (b["time"] - open_t).total_seconds() / 60.0 < hi]
        bucket_stats[f"{lo}-{hi}m"] = {
            "n": len(vals), "p50": pctile(vals, 0.5), "p90": pctile(vals, 0.9),
            "max": round(max(vals), 3) if vals else None,
        }

    # normalization times
    stressed_spread_thr = STRESSED_RT[pair] - SLIPPAGE_P   # RT→spread 換算
    norm_times = {
        "below_3xRT_assumption": sustained_below(bars, open_t, stressed_spread_thr),
    }
    if tue_p50 is not None:
        for m in NORMAL_MULTIPLES:
            norm_times[f"below_{m}x_normal"] = sustained_below(
                bars, open_t, m * tue_p50)

    return {
        "sunday": sunday.isoformat(),
        "status": "ok",
        "open_bar_utc": open_t.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_bars_4h": len(bars),
        "spots_p": spots,
        "buckets_p": bucket_stats,
        "tuesday_baseline_p50_p": tue_p50,
        "sustained_norm_min": norm_times,
    }


def aggregate(weekends: List[dict], key_path: List[str]) -> dict:
    """週末横断の p50/p90 (key_path で per-weekend 値を引く)。"""
    vals = []
    for w in weekends:
        v = w
        for k in key_path:
            v = v.get(k) if isinstance(v, dict) else None
            if v is None:
                break
        if isinstance(v, (int, float)):
            vals.append(float(v))
    return {"n": len(vals), "p50": pctile(vals, 0.5), "p90": pctile(vals, 0.9),
            "max": round(max(vals), 3) if vals else None}


def build_pair_summary(pair: str, weekends: List[dict]) -> dict:
    ok_w = [w for w in weekends if w.get("status") == "ok"]
    spot_agg = {}
    for label in ["first_bar"] + [f"+{o}m" for o in SPOT_OFFSETS_MIN]:
        spot_agg[label] = aggregate(ok_w, ["spots_p", label])
    bucket_agg = {}
    for lo, hi in BUCKETS:
        lbl = f"{lo}-{hi}m"
        bucket_agg[lbl] = {
            "p50_of_p50": aggregate(ok_w, ["buckets_p", lbl, "p50"]),
            "p90_of_p90": aggregate(ok_w, ["buckets_p", lbl, "p90"]),
        }
    norm_agg = {}
    for k in (["below_3xRT_assumption"]
              + [f"below_{m}x_normal" for m in NORMAL_MULTIPLES]):
        vals = [w["sustained_norm_min"].get(k) for w in ok_w
                if w.get("sustained_norm_min", {}).get(k) is not None]
        never = sum(1 for w in ok_w
                    if w.get("sustained_norm_min", {}).get(k) is None)
        norm_agg[k] = {"n": len(vals), "p50_min": pctile(vals, 0.5),
                       "p90_min": pctile(vals, 0.9),
                       "max_min": round(max(vals), 1) if vals else None,
                       "never_within_4h": never}
    tue = aggregate(ok_w, ["tuesday_baseline_p50_p"])
    stressed_thr = STRESSED_RT[pair] - SLIPPAGE_P
    return {
        "pair": pair,
        "n_weekends_ok": len(ok_w),
        "n_weekends_skipped": len(weekends) - len(ok_w),
        "normal_rt_frozen_p": NORMAL_RT[pair],
        "stressed_rt_3x_p": STRESSED_RT[pair],
        "stressed_spread_threshold_p": round(stressed_thr, 3),
        "tuesday_baseline_spread_p50_p": tue,
        "measured_normal_rt_p": (round(tue["p50"] + SLIPPAGE_P, 3)
                                 if tue["p50"] is not None else None),
        "sunday_open_spots_p": spot_agg,
        "sunday_open_buckets_p": bucket_agg,
        "sustained_normalization_min": norm_agg,
        "weekends": weekends,
    }


def render_md(result: dict) -> str:
    """report markdown を組み立てる。"""
    L = []
    L.append(f"# Sunday open 実スプレッド実測 — weekend_gap family #3 R1 step (i) ({result['run_date']})")
    L.append("")
    L.append("**目的**: OOS confirm gate (c) の stressed friction 仮定 (通常 RT x3) を"
             " OANDA live feed の歴史 BA candle 実測で検証・置換する"
             " ([[weekend-gap-oos-prereg-2026-07-24]] §9 R1 手続き 1)。")
    L.append(f"**測定**: 直近 {result['n_weekends']} 週末 "
             f"({result['weekend_range'][1]} 〜 {result['weekend_range'][0]}) x "
             f"{'/'.join(PAIRS)}、M1 price=BA、spread = ask.o − bid.o、"
             f"RT = spread + slippage {SLIPPAGE_P}p (KB friction table 準拠)。")
    L.append("**read-only**: GET candles のみ。live 変更ゼロ。")
    L.append("")
    L.append("## サマリ表 (spread は pips、p50 = 週末横断中央値)")
    L.append("")
    L.append("| pair | 通常RT(凍結) | 火曜実測 spread p50 | 実測通常RT | 3xRT仮定 | 初バー spread p50/p90 | +15m | +30m | +1h | +2h | +4h |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for p in PAIRS:
        s = result["pairs"][p]
        sp = s["sunday_open_spots_p"]

        def cell(lbl):
            a = sp[lbl]
            if a["p50"] is None:
                return "-"
            return f"{a['p50']:.2f}/{a['p90']:.2f}"
        L.append(
            f"| {p} | {s['normal_rt_frozen_p']}p | "
            f"{s['tuesday_baseline_spread_p50_p']['p50']}p | "
            f"{s['measured_normal_rt_p']}p | {s['stressed_rt_3x_p']}p | "
            f"{cell('first_bar')} | {cell('+15m')} | {cell('+30m')} | "
            f"{cell('+60m')} | {cell('+120m')} | {cell('+240m')} |")
    L.append("")
    L.append("## 3x 仮定の検証 — sustained normalization (open からの分数、p50/p90 across weekends)")
    L.append("")
    L.append("| pair | spread ≤ 3xRT−slip 閾値 | ≤ 1.5x通常 | ≤ 2x通常 | ≤ 3x通常 |")
    L.append("|---|---|---|---|---|")
    for p in PAIRS:
        na = result["pairs"][p]["sustained_normalization_min"]

        def ncell(k):
            a = na.get(k)
            if a is None or a["p50_min"] is None:
                return "-"
            nv = f"{a['p50_min']:.0f}m/{a['p90_min']:.0f}m"
            if a["never_within_4h"]:
                nv += f" (未達{a['never_within_4h']}週)"
            return nv
        L.append(f"| {p} | {ncell('below_3xRT_assumption')} | "
                 f"{ncell('below_1.5x_normal')} | {ncell('below_2.0x_normal')} | "
                 f"{ncell('below_3.0x_normal')} |")
    L.append("")
    L.append("詳細な数値 (週末別・バケット別) は JSON 成果物を参照。")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--weekends", type=int, default=12,
                    help="遡及する週末数 (>=8 が R1 要件、default 12)")
    ap.add_argument("--date", default=None,
                    help="基準日 YYYY-MM-DD (この日より前の日曜を対象、default=today)")
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--force-md", action="store_true",
                    help="既存 report md を上書き (分析追記が消えるため既定は保護)")
    args = ap.parse_args()

    if args.weekends < 8:
        print("WARN: R1 step (i) は >=8 週末を要求 (pre-reg §9)", file=sys.stderr)

    load_env_file(REPO_ROOT / ".env")
    sys.path.insert(0, str(REPO_ROOT))
    from modules.oanda_client import OandaClient  # noqa: E402 (env 読込後)
    client = OandaClient()
    if not client.configured:
        print("ERROR: OANDA_TOKEN / OANDA_ACCOUNT_ID が未設定", file=sys.stderr)
        return 1

    ref = (date.fromisoformat(args.date) if args.date
           else datetime.now(timezone.utc).date())
    sundays = last_n_sundays(args.weekends, ref)
    run_date = ref.isoformat()

    result = {
        "run_date": run_date,
        "purpose": "weekend_gap family #3 R1 step (i): Sunday open spread 実測",
        "prereg": "knowledge-base/wiki/decisions/weekend-gap-oos-prereg-2026-07-24.md §9",
        "read_only": True,
        "granularity": "M1", "price": "BA",
        "spread_def": "ask.o - bid.o (pips)",
        "rt_def": f"spread + {SLIPPAGE_P}p slippage (KB friction table)",
        "slippage_assumption_p": SLIPPAGE_P,
        "stressed_rt_arm_b_frozen_p": STRESSED_RT_ARM_B,
        "n_weekends": args.weekends,
        "weekend_range": [sundays[0].isoformat(), sundays[-1].isoformat()],
        "pairs": {},
    }

    for pair in PAIRS:
        weekends = []
        for sun in sundays:
            print(f"measuring {pair} {sun} ...", file=sys.stderr)
            weekends.append(measure_weekend(client, pair, sun))
            time.sleep(REQUEST_SLEEP_S)
        result["pairs"][pair] = build_pair_summary(pair, weekends)

    out_json = Path(args.out_json) if args.out_json else (
        REPO_ROOT / "bt-results" / f"sunday_open_spread-{run_date}.json")
    out_md = Path(args.out_md) if args.out_md else (
        REPO_ROOT / "reports" / f"sunday_open_spread-{run_date}.md")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"saved: {out_json}", file=sys.stderr)
    if out_md.exists() and not args.force_md:
        print(f"skip (exists, analyst 追記保護): {out_md} — 上書きは --force-md",
              file=sys.stderr)
    else:
        out_md.write_text(render_md(result))
        print(f"saved: {out_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
