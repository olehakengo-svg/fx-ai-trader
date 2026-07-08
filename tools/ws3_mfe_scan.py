#!/usr/bin/env python3
"""WS3 MFE 分布診断 — 現行シグナル母集団の entry 後 forward MFE/MAE を exit 非依存で計測 (rule:R3)

タスク: .ai/tasks/queue/20260708-1130-ws3-mfe-distribution-diagnosis.md
背景: T2 exit-repair FAIL (exit-repair-tp-sl-prereg-2026-07-07.md §8) → WS3 の初手。

- 母集団: 本番 signal 関数 365d BT baseline (倍率なし) の全エントリー (全 entry_type)
- 計測: forward H ∈ {6,12,24,48,96} bars の MFE/MAE (pips)。exit 設計 (TP/SL/trail) 非依存
- 診断窓 2026-06-07〜 は除外 (exit-repair と同基準)
- read-only 純診断。live パラメータ変更なし

実行: BT_MODE=1 NO_AUTOSTART=1 BT_REQUIRE_MASSIVE_CACHE=1 python3 tools/ws3_mfe_scan.py
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

PAIRS = ["GBP_USD", "EUR_USD", "USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY"]
SYMBOLS = {p: p.replace("_", "") + "=X" for p in PAIRS}
HORIZONS = [6, 12, 24, 48, 96]  # 15m bars: 1.5h / 3h / 6h / 12h / 24h
DIAG_START_UTC = "2026-06-07"
LOOKBACK_DAYS = 365
MIN_N = 10  # md 表の掲載足切り (JSON は全量)

# BT/本番 parity (exit_repair_tp_sl_grid_bt.py と同一根拠)
PARITY_ENV = {
    "WICK_IMBALANCE_REVERSION_REDESIGN_V2": "1",
    "DT_SR_CHANNEL_REDESIGN_V2": "1",
    "VSG_JPY_REVERSAL_REDESIGN_V2": "1",
}
BASE_ENV = {"BT_MODE": "1", "NO_AUTOSTART": "1", "BT_REQUIRE_MASSIVE_CACHE": "1"}

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(REPO, "knowledge-base", "raw", "bt-results",
                        "ws3_mfe_scan_2026_07.json")
OUT_MD = os.path.join(REPO, "knowledge-base", "raw", "bt-results",
                      "ws3_mfe_scan_2026_07.md")


def _pip(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


def forward_mfe(df, pos: int, sig: str, ep: float, horizon: int):
    """entry バー (pos) から horizon 本先までの MFE/MAE (価格単位)"""
    import numpy as np
    end = min(pos + horizon + 1, len(df))
    if end <= pos:
        return None, None
    hi = df["High"].values[pos:end]
    lo = df["Low"].values[pos:end]
    if sig == "BUY":
        return float(np.max(hi) - ep), float(ep - np.min(lo))
    return float(ep - np.min(lo)), float(np.max(hi) - ep)


def main() -> None:
    os.environ.update(BASE_ENV)
    os.environ.update(PARITY_ENV)
    # baseline: 倍率 env は明示的に unset (安全)
    for k in ("BT_TP_MULT", "BT_SL_MULT", "BT_TPSL_MULT_TYPES"):
        os.environ.pop(k, None)

    sys.path.insert(0, REPO)
    os.chdir(REPO)
    import pandas as pd
    import numpy as np
    import app

    entries = []  # {entry_type, pair, sig, entry_time, ep, mfe_pips@H, mae_pips@H}
    t0 = time.time()
    for pair in PAIRS:
        app._dt_bt_cache.clear()
        res = app.run_daytrade_backtest(SYMBOLS[pair], lookback_days=LOOKBACK_DAYS,
                                        interval="15m")
        if "error" in res:
            print(f"[mfe] {pair}: BT error {res['error']}", file=sys.stderr, flush=True)
            continue
        # forward 計測は BT ローダーと同じ parquet を直接読む
        pq = os.path.join(REPO, "data", "cache", "massive", f"{pair}_15m.parquet")
        df = pd.read_parquet(pq)
        idx = df.index
        pip = _pip(pair)
        n_in, n_skip = 0, 0
        for t in res.get("trade_log", []):
            et_time = t.get("entry_time")
            ep = t.get("ep")
            sig = t.get("sig")
            if not et_time or ep is None or sig not in ("BUY", "SELL"):
                n_skip += 1
                continue
            if et_time[:10] >= DIAG_START_UTC:
                continue  # 診断窓除外
            ts = pd.Timestamp(et_time)
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            pos = idx.searchsorted(ts)
            # entry はシグナルバーの次バー (BT 仕様)
            if pos >= len(idx) or idx[pos] != ts:
                n_skip += 1
                continue
            entry_pos = pos + 1
            row = {"entry_type": t.get("entry_type"), "pair": pair, "sig": sig,
                   "entry_time": et_time, "outcome": t.get("outcome")}
            ok = True
            for h in HORIZONS:
                mfe, mae = forward_mfe(df, entry_pos, sig, ep, h)
                if mfe is None:
                    ok = False
                    break
                row[f"mfe_{h}"] = round(mfe / pip, 2)
                row[f"mae_{h}"] = round(mae / pip, 2)
            if ok:
                entries.append(row)
                n_in += 1
            else:
                n_skip += 1
        print(f"[mfe] {pair}: total={res.get('trades')} kept={n_in} skip={n_skip} "
              f"({time.time()-t0:.0f}s)", file=sys.stderr, flush=True)
        # per-pair checkpoint (kill 耐性)
        ck = os.path.join(REPO, "knowledge-base", "raw", "bt-results",
                          ".ws3_mfe_scan_checkpoint.json")
        with open(ck, "w") as f:
            json.dump(entries, f)

    # ── 集計 (entry_type × pair) ──
    def q(vals, p):
        return round(float(np.percentile(vals, p)), 2) if len(vals) else None

    cells = {}
    for r in entries:
        cells.setdefault((r["entry_type"], r["pair"]), []).append(r)
    summary = {}
    for (et, pair), rs in sorted(cells.items()):
        s = {"n": len(rs)}
        for h in HORIZONS:
            m = np.array([r[f"mfe_{h}"] for r in rs], dtype=float)
            a = np.array([r[f"mae_{h}"] for r in rs], dtype=float)
            s[f"h{h}"] = {
                "mfe_p50": q(m, 50), "mfe_p75": q(m, 75), "mfe_p90": q(m, 90),
                "p_mfe_ge15": round(float((m >= 15).mean()), 3),
                "p_mfe_ge20": round(float((m >= 20).mean()), 3),
                "mae_p50": q(a, 50),
            }
        summary[f"{et}__{pair}"] = s

    out = {
        "task": "20260708-1130-ws3-mfe-distribution-diagnosis",
        "rule": "R3",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "engine": "app.run_daytrade_backtest baseline (倍率なし) + parquet forward scan",
        "lookback_days": LOOKBACK_DAYS, "horizons_bars": HORIZONS,
        "diag_window_excluded_from": DIAG_START_UTC,
        "pairs": PAIRS, "env": {**BASE_ENV, **PARITY_ENV},
        "n_entries": len(entries),
        "cells": summary,
        "caveats": [
            "MFE はバー粒度 (tick 未満不可視)。live 実測 (payoff-asymmetry §1) と比較時に明記",
            "ep は摩擦込み fill 価格 — MFE は実質 net 方向の走り",
            "screen であり promote 判定ではない。閾値の事前固定は次の pre-reg で行う",
        ],
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[mfe] saved {OUT_JSON}", file=sys.stderr, flush=True)

    # ── md: h24 (6時間) を代表 horizon として表化 ──
    lines = [
        "# WS3 MFE 分布スキャン (機械集計、rule:R3)",
        "",
        f"- 生成: {out['generated_utc']} / entries={len(entries)} / "
        f"365d baseline、診断窓除外、horizon 表は 24 bars (6h)",
        "",
        "| cell | N | MFE p50 | p75 | p90 | P(≥15p) | P(≥20p) | MAE p50 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    rows = [(k, v) for k, v in summary.items() if v["n"] >= MIN_N]
    rows.sort(key=lambda kv: -(kv[1]["h24"]["p_mfe_ge20"] or 0))
    for k, v in rows:
        h = v["h24"]
        lines.append(f"| {k} | {v['n']} | {h['mfe_p50']} | {h['mfe_p75']} "
                     f"| {h['mfe_p90']} | {h['p_mfe_ge15']} | {h['p_mfe_ge20']} "
                     f"| {h['mae_p50']} |")
    lines += ["", f"N<{MIN_N} セルと他 horizon は JSON 参照。", ""]
    with open(OUT_MD, "w") as f:
        f.write("\n".join(lines))
    print(f"[mfe] saved {OUT_MD}", file=sys.stderr, flush=True)
    print(json.dumps({"n_entries": len(entries),
                      "n_cells": len(summary),
                      "elapsed_sec": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    main()
