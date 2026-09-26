#!/usr/bin/env python3
"""[SLTP_CONSTRUCT] / [BROKER_TP] marker の読み手 (rule:R3 2026-09-26、record-only)。

`_tick_entry` が fill 行 reasons に永続する SL/TP 構築 provenance を本番 API から集計し、
entry_type × (live / shadow) ごとに SL 選択枝 (preserve / sr / atr_nosr / atr_rrlow)、
clamp、C0c バッファ発動率、MTF TP ×1.3 率、宣言 SL/TP 距離 vs 実発注距離の中央値を出す。

用途: kalman_d7 制約付き BT (Codex queue 20260925-0300) の「C0 感度を live 実測率に差し替える」
前提 / usdjpy_carry_dip_accumulator の SL 契約破棄 (宣言 150p → 9.8–28.5p) の機構確認。
EV / WR / outcome は読まない (件数と距離のみ — 凍結 pre-reg の outcome 量に触れない)。

使い方:
    python3 tools/sltp_construct_readout.py [--limit 2000] [--since 2026-09-26] [--json]
    python3 tools/sltp_construct_readout.py --file trades.json   # 保存済み JSON から
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.demo_trader import (  # noqa: E402
    _BROKER_TP_REASON_TAG,
    parse_sltp_construct_marker,
)

DEFAULT_URL = "https://fx-ai-trader.onrender.com/api/demo/trades"


def _load_rows(args) -> list:
    if args.file:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    else:
        if not str(args.url).startswith("https://"):
            raise SystemExit("--url は https:// のみ")
        import requests  # 遅延 import (pytest 収集時の依存を避ける)
        resp = requests.get(args.url, params={"limit": int(args.limit),
                                              "include_shadow": "true"}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    if isinstance(data, dict):
        data = data.get("trades") or data.get("data") or []
    return data


def _reasons(row) -> list:
    raw = row.get("reasons")
    if isinstance(raw, list):
        return raw
    try:
        out = json.loads(raw) if raw else []
    except Exception:
        return []
    return out if isinstance(out, list) else []


def _broker_tp(reasons: list) -> dict | None:
    for r in reasons:
        if isinstance(r, str) and r.startswith(_BROKER_TP_REASON_TAG + " "):
            out = {}
            for kv in r[len(_BROKER_TP_REASON_TAG) + 1:].split(" "):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    out[k] = v
            return out
    return None


def _fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def summarize(rows: list, since: str | None) -> dict:
    groups: dict = defaultdict(lambda: {
        "n": 0, "sl": Counter(), "clamp": Counter(), "lowliq": 0, "fastsl": 0, "ct": 0,
        "rn": 0, "mtf_tp_1_3": 0, "range_tp": 0, "decl_sl_p": [], "sl_p": [],
        "decl_tp_p": [], "tp_p": [], "entry_drift_p": [],
        "broker_basis": Counter(), "broker_tp_p": [],
    })
    total = 0
    with_marker = 0
    for row in rows:
        et = row.get("entry_type") or "?"
        ts = str(row.get("entry_time") or "")
        if since and ts[:10] < since:
            continue
        total += 1
        reasons = _reasons(row)
        m = parse_sltp_construct_marker(reasons)
        if m is None:
            continue
        with_marker += 1
        lane = "live" if row.get("oanda_trade_id") else "shadow"
        g = groups[(et, lane)]
        g["n"] += 1
        g["sl"][m.get("sl", "?")] += 1
        g["clamp"][m.get("clamp", "?")] += 1
        for k in ("lowliq", "fastsl", "ct", "rn", "range_tp"):
            if m.get(k) == "1":
                g[k] += 1
        if m.get("mtf_tp") == "1.3":
            g["mtf_tp_1_3"] += 1
        for k in ("decl_sl_p", "sl_p", "decl_tp_p", "tp_p", "entry_drift_p"):
            v = _fnum(m.get(k))
            if v is not None:
                g[k].append(v)
        b = _broker_tp(reasons)
        if b:
            g["broker_basis"][b.get("basis", "?")] += 1
            v = _fnum(b.get("tp_p"))
            if v is not None:
                g["broker_tp_p"].append(v)

    def _med(xs):
        return round(statistics.median(xs), 1) if xs else None

    out = {"rows_in_window": total, "rows_with_marker": with_marker, "groups": []}
    for (et, lane), g in sorted(groups.items(), key=lambda kv: (-kv[1]["n"], kv[0])):
        n = g["n"]
        out["groups"].append({
            "entry_type": et, "lane": lane, "n": n,
            "sl": dict(g["sl"]), "clamp": dict(g["clamp"]),
            "rate": {k: round(g[k] / n, 3) for k in
                     ("lowliq", "fastsl", "ct", "rn", "range_tp", "mtf_tp_1_3")},
            "median_pips": {k: _med(g[k]) for k in
                            ("decl_sl_p", "sl_p", "decl_tp_p", "tp_p", "entry_drift_p",
                             "broker_tp_p")},
            "broker_basis": dict(g["broker_basis"]),
        })
    return out


def _print_table(summary: dict) -> None:
    print(f"rows_in_window={summary['rows_in_window']} "
          f"rows_with_marker={summary['rows_with_marker']}")
    if summary["rows_with_marker"] == 0:
        print("(marker 行なし — デプロイ前の行か、窓が古い。`sl=unset` も 0 件)")
        return
    hdr = ("entry_type", "lane", "n", "sl", "clamp", "lowliq", "fastsl", "rn", "mtf1.3",
           "decl_sl/sl_p", "decl_tp/tp_p/broker")
    print(" | ".join(hdr))
    for g in summary["groups"]:
        mp = g["median_pips"]
        print(" | ".join([
            g["entry_type"], g["lane"], str(g["n"]),
            ",".join(f"{k}:{v}" for k, v in sorted(g["sl"].items())),
            ",".join(f"{k}:{v}" for k, v in sorted(g["clamp"].items())),
            f"{g['rate']['lowliq']:.2f}", f"{g['rate']['fastsl']:.2f}",
            f"{g['rate']['rn']:.2f}", f"{g['rate']['mtf_tp_1_3']:.2f}",
            f"{mp['decl_sl_p']}/{mp['sl_p']}",
            f"{mp['decl_tp_p']}/{mp['tp_p']}/{mp['broker_tp_p']}",
        ]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--since", default=None, help="YYYY-MM-DD (entry_time の下限)")
    ap.add_argument("--file", default=None, help="保存済み trades JSON")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rows = _load_rows(args)
    summary = summarize(rows, args.since)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        _print_table(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
