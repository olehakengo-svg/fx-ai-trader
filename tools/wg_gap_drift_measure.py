#!/usr/bin/env python3
"""
weekend_gap 執行契約 R1 改定パケット用 — Sunday open 直後の価格ドリフト +
OANDA 実開場時刻の read-only 実測 (2026-09-10, rule:R3 観測)。

目的 (meta-audit 2026-09-07 §4.2 R1(b) / F2 勧告):
  live fill 0/3 の機構 = 「シグナル発火 (~21:01, MASSIVE forming bar) が
  OANDA 実開場 (~21:04-21:05, MARKET_HALTED 解除) より常に早い」ことの
  定量裏付けとして、
    (1) OANDA 実開場時刻の分布 (= halt 解除時刻 → リトライ/繰下げの fill 成立率)
    (2) Sunday open (MASSIVE 21:00 バー open = OOS estimand の entry 価格) から
        +k 分後までの mid ドリフト (= エントリー繰下げの estimand コスト、
        G1 slippage ゲート +2.0p との整合検査)
  を直近 N 週末 x 3 ペアで実測する。

厳守 (pre-reg §8 / look-burn 回避):
  - 価格データのみ。戦略 outcome (4h PnL/WR/EV) とは一切結合しない。
  - OOS 窓 (2022-2026-07 の凍結統計) の再集計はしない — 対象は直近 N 週末のみ。
  - read-only: MASSIVE aggs GET + OANDA candles GET のみ。注文/口座変更ゼロ。
    (前例: tools/sunday_open_spread_measure.py と同型)

Usage:
  python3 tools/wg_gap_drift_measure.py [--weekends 16] [--date 2026-09-10]
Output:
  bt-results/wg_gap_drift-<date>.json
"""
import argparse
import json
import os
import statistics
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PAIRS = ("EUR_USD", "USD_JPY", "AUD_USD")            # arm B pooled (GBP 除外)
PIP = {"EUR_USD": 1e-4, "USD_JPY": 1e-2, "AUD_USD": 1e-4}
MASSIVE_TICKER = {"EUR_USD": "C:EURUSD", "USD_JPY": "C:USDJPY",
                  "AUD_USD": "C:AUDUSD"}
DRIFT_OFFSETS_MIN = (2, 3, 4, 5, 6, 8, 10, 15)       # Sunday 21:00 からの分
REQUEST_SLEEP_S = 0.2


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


def last_n_sundays(n: int, before: date) -> list:
    d = before - timedelta(days=1)
    while d.weekday() != 6:
        d -= timedelta(days=1)
    return [d - timedelta(weeks=k) for k in range(n)]


def massive_1m_bars(ticker: str, day: date, api_key: str) -> list:
    """MASSIVE 1m aggregates for one UTC day (list of {t(ms), o, c})."""
    from modules.data import _fetch_chunk
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    rows = _fetch_chunk(ticker, 1, "minute", start, start + timedelta(days=1),
                        api_key)
    return rows


def bar_at_or_after(bars: list, ts_ms: int):
    for b in bars:
        if b.get("t", 0) >= ts_ms:
            return b
    return None


def last_bar_before(bars: list, ts_ms: int):
    prev = None
    for b in bars:
        if b.get("t", 0) >= ts_ms:
            break
        prev = b
    return prev


def measure_weekend(pair: str, sun: date, api_key: str, oanda) -> dict:
    pip = PIP[pair]
    tick = MASSIVE_TICKER[pair]
    fri = sun - timedelta(days=2)
    out = {"sunday": sun.isoformat(), "pair": pair}

    fri_bars = massive_1m_bars(tick, fri, api_key)
    time.sleep(REQUEST_SLEEP_S)
    sun_bars = massive_1m_bars(tick, sun, api_key)
    time.sleep(REQUEST_SLEEP_S)

    fri_2100 = int(datetime(fri.year, fri.month, fri.day, 21,
                            tzinfo=timezone.utc).timestamp() * 1000)
    sun_2100 = int(datetime(sun.year, sun.month, sun.day, 21,
                            tzinfo=timezone.utc).timestamp() * 1000)

    fb = last_bar_before(fri_bars, fri_2100)
    sb = bar_at_or_after(sun_bars, sun_2100)
    if fb is None or sb is None:
        out["skip"] = "missing massive bars"
        return out

    fri_close = float(fb["c"])
    sun_open = float(sb["o"])
    sun_open_ts = datetime.fromtimestamp(sb["t"] / 1000, tz=timezone.utc)
    gap_pips = (sun_open - fri_close) / pip
    fade_side = "SELL" if gap_pips > 0 else "BUY"
    sign = 1.0 if fade_side == "BUY" else -1.0   # adverse = fade 方向に価格が先行

    out.update({
        "fri_close": fri_close,
        "sun_open": sun_open,
        "massive_first_bar_utc": sun_open_ts.isoformat(),
        "gap_pips": round(gap_pips, 1),
        "fade_side": fade_side,
        "drift": {},
    })
    for k in DRIFT_OFFSETS_MIN:
        b = bar_at_or_after(sun_bars, sun_2100 + k * 60_000)
        if b is None:
            continue
        drift = (float(b["o"]) - sun_open) / pip
        out["drift"][f"+{k}m"] = {
            "drift_pips": round(drift, 2),
            "adverse_pips": round(sign * drift, 2),
        }

    # OANDA 実開場: Sun 20:55 以降の最初の complete M1 バー (M1 が刻まれる =
    # tradeable の必要条件。halt 中はバーが存在しない)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    t0 = datetime(sun.year, sun.month, sun.day, 20, 55, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=35)
    ok, data = oanda.get_candles(pair, granularity="M1", price="MBA",
                                 from_time=t0.strftime(fmt),
                                 to_time=t1.strftime(fmt))
    if ok:
        for c in data.get("candles", []):
            if not c.get("complete"):
                continue
            ots = c["time"][:19] + "Z"
            mid_o = float(c["mid"]["o"])
            spread_p = (float(c["ask"]["o"]) - float(c["bid"]["o"])) / pip
            out["oanda_first_m1_utc"] = ots
            out["oanda_first_m1_mid_o"] = mid_o
            out["oanda_first_m1_spread_pips"] = round(spread_p, 2)
            out["oanda_vs_massive_open_pips"] = round(
                (mid_o - sun_open) / pip, 2)
            break
    else:
        out["oanda_error"] = str(data)[:120]
    time.sleep(REQUEST_SLEEP_S)
    return out


def agg(vals: list) -> dict:
    if not vals:
        return {}
    s = sorted(vals)
    n = len(s)
    return {
        "n": n,
        "mean": round(statistics.fmean(s), 2),
        "p50": round(s[n // 2], 2),
        "p90": round(s[min(n - 1, int(0.9 * (n - 1) + 0.5))], 2),
        "min": round(s[0], 2),
        "max": round(s[-1], 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weekends", type=int, default=16)
    ap.add_argument("--date", default=None)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--env-file", default=None,
                    help=".env の場所 (worktree 実行時に main repo の .env を指す)")
    args = ap.parse_args()

    load_env_file(Path(args.env_file) if args.env_file else REPO_ROOT / ".env")
    sys.path.insert(0, str(REPO_ROOT))
    from modules.oanda_client import OandaClient
    oanda = OandaClient()
    if not oanda.configured:
        print("ERROR: OANDA creds 未設定", file=sys.stderr)
        return 1
    api_key = os.environ.get("MASSIVE_API_KEY", "")
    if not api_key:
        print("ERROR: MASSIVE_API_KEY 未設定", file=sys.stderr)
        return 1

    ref = (date.fromisoformat(args.date) if args.date
           else datetime.now(timezone.utc).date())
    sundays = last_n_sundays(args.weekends, ref)

    result = {
        "run_date": ref.isoformat(),
        "purpose": ("weekend_gap 執行契約 R1 改定パケット: OANDA 実開場時刻 + "
                    "Sunday open 後ドリフト実測 (価格データのみ、outcome 非結合)"),
        "read_only": True,
        "n_weekends": args.weekends,
        "weekend_range": [sundays[-1].isoformat(), sundays[0].isoformat()],
        "drift_def": ("MASSIVE 1m: drift(+k) = mid_open(21:00+k) - "
                      "mid_open(first bar >= Sun 21:00 UTC), pips. "
                      "adverse = fade 方向符号 (BUY:+drift / SELL:-drift)"),
        "weekends": [],
        "aggregates": {},
    }

    for sun in sundays:
        for pair in PAIRS:
            print(f"measuring {pair} {sun} ...", file=sys.stderr)
            try:
                result["weekends"].append(
                    measure_weekend(pair, sun, api_key, oanda))
            except Exception as e:
                result["weekends"].append(
                    {"sunday": sun.isoformat(), "pair": pair,
                     "skip": f"error: {e}"})

    ok_rows = [w for w in result["weekends"] if "drift" in w]
    # OANDA 実開場時刻 (open からの秒)
    open_delays = []
    for w in ok_rows:
        ots = w.get("oanda_first_m1_utc")
        if not ots:
            continue
        dt = datetime.strptime(ots, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        base = dt.replace(hour=21, minute=0, second=0)
        open_delays.append((dt - base).total_seconds() / 60.0)
    result["aggregates"]["oanda_first_m1_delay_min"] = agg(open_delays)
    result["aggregates"]["open_by"] = {
        f"<= +{m}m": (round(sum(1 for d in open_delays if d <= m)
                            / len(open_delays), 3) if open_delays else None)
        for m in (5, 6, 8, 10, 15)
    }
    for k in DRIFT_OFFSETS_MIN:
        vals = [w["drift"][f"+{k}m"]["adverse_pips"] for w in ok_rows
                if f"+{k}m" in w.get("drift", {})]
        result["aggregates"][f"adverse_drift_+{k}m_pips"] = agg(vals)
        avals = [abs(w["drift"][f"+{k}m"]["drift_pips"]) for w in ok_rows
                 if f"+{k}m" in w.get("drift", {})]
        result["aggregates"][f"abs_drift_+{k}m_pips"] = agg(avals)
    basis = [w["oanda_vs_massive_open_pips"] for w in ok_rows
             if "oanda_vs_massive_open_pips" in w]
    result["aggregates"]["oanda_vs_massive_open_basis_pips"] = agg(basis)

    out_json = Path(args.out_json) if args.out_json else (
        REPO_ROOT / "bt-results" / f"wg_gap_drift-{ref.isoformat()}.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"saved: {out_json}", file=sys.stderr)
    print(json.dumps(result["aggregates"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
