"""#21 commodity_cross_range_mr — G0 RT 実測サンプラー (measurement only, no verdict).

Ledger #21 (hypothesis-catalog-2026-07-24.md) の必須事前ゲート G0:
「OANDA 3 クロス (AUD_NZD/AUD_CAD/NZD_CAD) RT 実測 (rollover 込み) >= 1 週間」。

このツールは**計測のみ**を行い、G0 の PASS/FAIL 判定はしない (判定基準は
explore pre-reg 起案時に凍結する — 計測器に verdict を埋め込まない規律)。

- OANDA v20 BA (bid/ask) M5 candles を遡及取得し spread 分布を出力
  (count=4032 ~= 14 日 — 「>=1 週間」を初回実行で遡及充足)
- financing (rollover) は list_instruments の当日 snapshot
  (日次 cron 実行で >=1 週間分の系列が Render ログに蓄積される)
- 出力は stdout に JSON 1 行 (Render cron ログから回収して KB へ永続化する運用)

シグナル計算・forward return への接触はゼロ (G0 は摩擦測定のみ)。
Module-level 副作用なし (tools/*.py 二重存在の教訓)。
"""

import json
import sys
from datetime import datetime, timezone

PAIRS = ("AUD_NZD", "AUD_CAD", "NZD_CAD")
GRANULARITY = "M5"
CANDLE_COUNT = 4032  # ~14 trading-ish days of M5 bars
PIP = 0.0001  # all three crosses are non-JPY

# UTC session blocks + rollover window (matching KB session conventions)
BLOCKS = {
    "asia_00_07": range(0, 7),
    "london_07_14": range(7, 14),
    "ny_14_21": range(14, 21),
    "late_21_24": range(21, 24),
}
ROLLOVER_HHMM = ((20, 45), (21, 15))  # 20:45-21:15 UTC window


def _percentiles(xs, ps=(25, 50, 75, 90, 99)):
    if not xs:
        return {}
    s = sorted(xs)
    n = len(s)
    return {f"p{p}": round(s[min(n - 1, int(n * p / 100))], 3) for p in ps}


def _in_rollover(dt):
    (h1, m1), (h2, m2) = ROLLOVER_HHMM
    t = dt.hour * 60 + dt.minute
    return h1 * 60 + m1 <= t <= h2 * 60 + m2


def collect(client):
    out = {
        "tool": "commodity_cross_g0_rt",
        "ledger": 21,
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "granularity": GRANULARITY,
        "candle_count_requested": CANDLE_COUNT,
        "pairs": {},
        "financing": {},
        "note": "measurement only — G0 verdict criteria live in the pre-reg, not here",
    }

    ok, inst = client.list_instruments()
    if ok:
        for i in inst.get("instruments", []):
            if i.get("name") in PAIRS:
                fin = i.get("financing", {})
                out["financing"][i["name"]] = {
                    "longRate": fin.get("longRate"),
                    "shortRate": fin.get("shortRate"),
                    "marginRate": i.get("marginRate"),
                }
    else:
        out["financing_error"] = str(inst)[:200]

    for pair in PAIRS:
        ok, data = client.get_candles(
            instrument=pair, granularity=GRANULARITY,
            count=CANDLE_COUNT, price="BA")
        if not ok:
            out["pairs"][pair] = {"error": str(data)[:200]}
            continue
        spreads_all, by_block, roll = [], {k: [] for k in BLOCKS}, []
        first_t = last_t = None
        for c in data.get("candles", []):
            if not c.get("complete"):
                continue
            try:
                spr = (float(c["ask"]["c"]) - float(c["bid"]["c"])) / PIP
                dt = datetime.fromisoformat(
                    c["time"].replace("Z", "+00:00").split(".")[0] + "+00:00")
            except (KeyError, ValueError):
                continue
            spreads_all.append(spr)
            first_t = first_t or c["time"][:16]
            last_t = c["time"][:16]
            for name, hours in BLOCKS.items():
                if dt.hour in hours:
                    by_block[name].append(spr)
            if _in_rollover(dt):
                roll.append(spr)
        out["pairs"][pair] = {
            "n_candles": len(spreads_all),
            "window": [first_t, last_t],
            "coverage_days": round(len(spreads_all) / 288.0, 1),
            "spread_pips": _percentiles(spreads_all),
            "by_block": {k: _percentiles(v, (50, 90)) for k, v in by_block.items()},
            "rollover_2045_2115": _percentiles(roll, (50, 90)),
        }
    return out


def main(argv=None):
    sys.path.insert(0, ".")
    from modules.oanda_client import OandaClient
    client = OandaClient()
    if not client.configured:
        print(json.dumps({"tool": "commodity_cross_g0_rt",
                          "error": "OANDA credentials not configured"}))
        return 1
    print(json.dumps(collect(client), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
