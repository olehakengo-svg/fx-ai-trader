#!/usr/bin/env python3
"""365d cell-conditional BT: sr_anti_hunt_bounce × EUR_JPY, direction/session 分解.

R1 昇格パケット (quant-eval-2026-07-31 Next Action #3) の必須証拠。
事前宣言ゲート (実行前に凍結、2026-08-05):
    BUY セル: N >= 30 AND EV_R(摩擦込み) > 0 AND Wilson_lo(95%) > BEV_WR 33.7%
    FAIL なら live 化は起案せず forward 確認枠 (registry) へ転換。
ハーネス: tools/sr_anti_hunt_bounce_shadow_bt.py の strategy-only compute patch を流用
(production daytrade BT path, BT_MODE=1, BT_REQUIRE_MASSIVE_CACHE=1)。
flag 両状態 (V2 off/on) を記録し、判定は本番実効状態 = flag OFF (env 未設定,
strategies/daytrade/sr_anti_hunt_bounce.py:62 は "1" 明示時のみ V2) で行う。
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ["BT_MODE"] = "1"
os.environ["BT_REQUIRE_MASSIVE_CACHE"] = "1"
os.environ["NO_AUTOSTART"] = "1"
sys.modules.setdefault("pytest", object())

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.sr_anti_hunt_bounce_shadow_bt import (  # noqa: E402
    _compute_sr_anti_hunt_only_signal,
    _pnl_r,
    _wilson_lower,
    _pf,
)

PAIR, SYMBOL = "EUR_JPY", "EURJPY=X"
LOOKBACK_DAYS = 365
INTERVAL = "15m"
STRATEGY = "sr_anti_hunt_bounce"
BEV_WR = 0.337
OUTFILE = ROOT / "knowledge-base" / "raw" / "bt-results" / "sr-anti-hunt-eurjpy-cell-bt-2026-08-05.json"


def _sess(entry_time: str) -> str:
    try:
        h = int(str(entry_time)[11:13])
    except (ValueError, IndexError):
        return "unknown"
    if h < 7:
        return "tokyo"
    if h < 12:
        return "london"
    if h < 16:
        return "overlap"
    if h < 21:
        return "ny"
    return "late"


def _cell_stats(trades: list[dict]) -> dict:
    pnls = [_pnl_r(t) for t in trades]
    n = len(trades)
    wins = sum(1 for p in pnls if p > 0)
    pf = _pf(pnls)
    return {
        "N": n,
        "wins": wins,
        "WR": round(wins / n, 4) if n else 0.0,
        "wilson_lo": round(_wilson_lower(wins, n), 4),
        "EV_R": round(sum(pnls) / n, 4) if n else 0.0,
        "PnL_R": round(sum(pnls), 4),
        "PF": round(pf, 4) if math.isfinite(pf) else "inf",
    }


def _decompose(result: dict) -> dict:
    trades = [t for t in result.get("trade_log", [])
              if t.get("entry_type") == STRATEGY]
    out = {"all": _cell_stats(trades)}
    for d in ("BUY", "SELL"):
        out[f"dir_{d}"] = _cell_stats([t for t in trades if t.get("sig") == d])
    for s in ("tokyo", "london", "overlap", "ny", "late"):
        out[f"sess_{s}"] = _cell_stats(
            [t for t in trades if _sess(t.get("entry_time", "")) == s])
    out["dir_BUY_sess_tokyo"] = _cell_stats(
        [t for t in trades if t.get("sig") == "BUY"
         and _sess(t.get("entry_time", "")) == "tokyo"])
    out["bt_error"] = result.get("error")
    out["bars_fetched"] = result.get("bars_fetched")
    out["data_source"] = result.get("data_source")
    return out


def _gate(buy: dict) -> dict:
    checks = {
        "N>=30": buy["N"] >= 30,
        "EV_R>0": buy["EV_R"] > 0,
        "wilson_lo>BEV_33.7%": buy["wilson_lo"] > BEV_WR,
    }
    return {"checks": checks, "verdict": "PASS" if all(checks.values()) else "FAIL"}


def main() -> int:
    started = time.time()
    cache = ROOT / "data" / "cache" / "massive" / f"{PAIR}_{INTERVAL}.parquet"
    assert cache.exists(), f"missing MASSIVE cache: {cache}"

    import app  # noqa: E402
    from modules import data as data_mod  # noqa: E402

    app.compute_daytrade_signal = _compute_sr_anti_hunt_only_signal

    runs = {}
    for label, flag in (("v2_off_production_default", "0"), ("v2_on", "1")):
        os.environ["SR_ANTI_HUNT_BOUNCE_REDESIGN_V2"] = flag
        app._dt_bt_cache.clear()
        data_mod._data_cache.clear()
        from strategies.daytrade.sr_anti_hunt_bounce import SrAntiHuntBounce
        SrAntiHuntBounce._v2_seen_closed_bar_keys.clear()
        print(f"Running {label}: {PAIR} {LOOKBACK_DAYS}d {INTERVAL}", flush=True)
        result = app.run_daytrade_backtest(
            symbol=SYMBOL, lookback_days=LOOKBACK_DAYS,
            interval=INTERVAL, backtest_mode=True)
        runs[label] = _decompose(result)

    primary = runs["v2_off_production_default"]
    verdict = _gate(primary["dir_BUY"])
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "R1 promotion evidence: sr_anti_hunt_bounce × EUR_JPY cell-conditional 365d BT",
        "pre_declared_gate": "BUY cell: N>=30 AND EV_R>0 AND wilson_lo>0.337 (declared 2026-08-05 before run)",
        "pair": PAIR,
        "lookback_days": LOOKBACK_DAYS,
        "interval": INTERVAL,
        "runner": "app.run_daytrade_backtest (production path, strategy-only compute patch, friction-inclusive R units)",
        "runs": runs,
        "gate_on": "v2_off_production_default.dir_BUY",
        "gate": verdict,
        "elapsed_s": round(time.time() - started, 1),
    }
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"gate": verdict,
                      "BUY": primary["dir_BUY"],
                      "SELL": primary["dir_SELL"],
                      "all": primary["all"],
                      "tokyo_BUY": primary["dir_BUY_sess_tokyo"]},
                     ensure_ascii=False, indent=1))
    print(f"saved -> {OUTFILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
