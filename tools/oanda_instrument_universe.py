#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OANDA v20 口座の取引可能銘柄 **全集合** を read-only で凍結する (rule:R3、2026-10-22)。

第6次スキャン §4.3 (c) の決定的確認: v20 口座に貴金属 (XAU/XAG) が無いこと、FX ペアの
全集合 (displayPrecision / pipLocation / marginRate / financing / minimumTradeSize) を
KB に凍結し、残余 (c) = 追加 FX ペアの shadow 蓄積 候補の母集団を固定する。

既存 tools/commodity_cross_g0_rt.py は PAIRS 3 本に絞って financing を読む — 本 tool は
フィルタなしで全件を保存する。シグナル・価格・outcome には一切触れない。

使い方:
    python3 tools/oanda_instrument_universe.py --out knowledge-base/raw/bt-results/oanda-instrument-universe/2026-10-22.json
    (OANDA_TOKEN / OANDA_ACCOUNT_ID は環境変数。値は出力に含めない)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FIELDS = ("name", "type", "displayName", "displayPrecision", "pipLocation",
          "tradeUnitsPrecision", "minimumTradeSize", "maximumOrderUnits",
          "maximumPositionSize", "marginRate", "guaranteedStopLossOrderMode")


def summarize(payload: dict[str, Any]) -> dict[str, Any]:
    """OANDA `GET /v3/accounts/{id}/instruments` 応答 → 凍結用 summary (純関数)。"""
    rows = []
    for i in payload.get("instruments", []):
        row = {k: i.get(k) for k in FIELDS}
        fin = i.get("financing") or {}
        row["financing"] = {"longRate": fin.get("longRate"), "shortRate": fin.get("shortRate")}
        row["tags"] = [t.get("name") for t in (i.get("tags") or []) if isinstance(t, dict)]
        rows.append(row)
    rows.sort(key=lambda r: (str(r.get("type")), str(r.get("name"))))
    by_type = Counter(str(r.get("type")) for r in rows)
    names = [r["name"] for r in rows]
    metals = [n for n in names if n and n.split("_")[0] in {"XAU", "XAG", "XPT", "XPD"}]
    return {
        "tool": "oanda_instrument_universe",
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_instruments": len(rows),
        "by_type": dict(by_type),
        "metals_present": metals,
        "jpy_quote": sorted(n for n in names if n and n.endswith("_JPY")),
        "instruments": rows,
        "note": "read-only snapshot of tradeable instruments for this v20 account; "
                "no prices, signals or outcomes. Token / account id are not recorded.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OANDA v20 口座の銘柄全集合を凍結 (read-only)")
    ap.add_argument("--out", required=True, help="保存先 JSON (knowledge-base/raw/bt-results/oanda-instrument-universe/)")
    args = ap.parse_args(argv)
    sys.path.insert(0, ".")
    from modules.oanda_client import OandaClient
    client = OandaClient()
    if not client.configured:
        print(json.dumps({"tool": "oanda_instrument_universe", "error": "OANDA credentials not configured"}))
        return 1
    ok, payload = client.list_instruments()
    if not ok:
        print(json.dumps({"tool": "oanda_instrument_universe", "error": str(payload)[:300]}))
        return 1
    out = summarize(payload)
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("run_utc", "n_instruments", "by_type", "metals_present")}, ensure_ascii=False))
    print(f"saved {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
