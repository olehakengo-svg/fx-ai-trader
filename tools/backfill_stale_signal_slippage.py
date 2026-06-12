#!/usr/bin/env python3
"""Backfill stale signal-price slippage diagnostics in production SQLite.

Default mode is dry-run. Intended production use:

    python3 tools/backfill_stale_signal_slippage.py \
      --db /var/data/demo_trades.db --verify-oanda --apply
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.demo_db import pip_multiplier


@dataclass(frozen=True)
class BackfillCandidate:
    trade_id: str
    instrument: str
    entry_type: str
    direction: str
    entry_time: str
    entry_price: float
    signal_price: float
    old_slippage_pips: float
    oanda_trade_id: str
    reason: str


def signed_slippage_pips(direction: str, entry_price: float,
                         signal_price: float, instrument: str) -> float:
    if not entry_price or not signal_price:
        return 0.0
    slip = (float(entry_price) - float(signal_price)) * pip_multiplier(instrument)
    if str(direction).upper() == "SELL":
        slip = -slip
    return round(slip, 2)


def _oanda_open_price(client, oanda_trade_id: str) -> float | None:
    ok, data = client._request(
        "GET",
        f"/v3/accounts/{client._account_id}/trades/{oanda_trade_id}",
        timeout=30,
    )
    if not ok:
        return None
    trade = data.get("trade", data)
    try:
        return float(trade.get("price") or 0.0)
    except (TypeError, ValueError):
        return None


def find_candidates(conn: sqlite3.Connection, *,
                    threshold_pips: float = 10.0,
                    strategy: str | None = None,
                    instrument: str | None = None,
                    include_no_oanda: bool = False,
                    verify_oanda: bool = False,
                    oanda_tolerance_pips: float = 0.3) -> list[BackfillCandidate]:
    conn.row_factory = sqlite3.Row
    where = [
        "COALESCE(signal_price, 0) > 0",
        "COALESCE(entry_price, 0) > 0",
    ]
    params: list[object] = []
    if strategy:
        where.append("entry_type = ?")
        params.append(strategy)
    if instrument:
        where.append("instrument = ?")
        params.append(instrument)
    rows = conn.execute(
        "SELECT trade_id, instrument, entry_type, direction, entry_time, "
        "entry_price, signal_price, slippage_pips, oanda_trade_id "
        "FROM demo_trades WHERE " + " AND ".join(where) + " "
        "ORDER BY entry_time",
        params,
    ).fetchall()

    client = None
    if verify_oanda:
        from modules.oanda_client import OandaClient
        client = OandaClient()
        if not client.configured:
            raise RuntimeError("OANDA client is not configured")

    out: list[BackfillCandidate] = []
    for row in rows:
        entry_price = float(row["entry_price"])
        signal_price = float(row["signal_price"])
        calc = signed_slippage_pips(
            row["direction"], entry_price, signal_price, row["instrument"]
        )
        if abs(calc) <= threshold_pips:
            continue

        oanda_trade_id = str(row["oanda_trade_id"] or "")
        if not oanda_trade_id and not include_no_oanda:
            continue

        reason = "signal_entry_gap"
        if client is not None:
            if not oanda_trade_id:
                continue
            open_price = _oanda_open_price(client, oanda_trade_id)
            if open_price is None:
                continue
            fill_gap_pips = abs(open_price - entry_price) * pip_multiplier(row["instrument"])
            if fill_gap_pips > oanda_tolerance_pips:
                continue
            reason = f"oanda_fill_matches_entry({fill_gap_pips:.2f}p)"

        out.append(BackfillCandidate(
            trade_id=str(row["trade_id"]),
            instrument=str(row["instrument"]),
            entry_type=str(row["entry_type"]),
            direction=str(row["direction"]),
            entry_time=str(row["entry_time"]),
            entry_price=entry_price,
            signal_price=signal_price,
            old_slippage_pips=float(row["slippage_pips"] or calc),
            oanda_trade_id=oanda_trade_id,
            reason=reason,
        ))
    return out


def apply_backfill(conn: sqlite3.Connection,
                   candidates: Iterable[BackfillCandidate]) -> int:
    count = 0
    for cand in candidates:
        conn.execute(
            "UPDATE demo_trades "
            "SET signal_price = entry_price, slippage_pips = 0 "
            "WHERE trade_id = ?",
            (cand.trade_id,),
        )
        count += 1
    conn.commit()
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--threshold-pips", type=float, default=10.0)
    ap.add_argument("--strategy")
    ap.add_argument("--instrument")
    ap.add_argument("--include-no-oanda", action="store_true")
    ap.add_argument("--verify-oanda", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    candidates = find_candidates(
        conn,
        threshold_pips=args.threshold_pips,
        strategy=args.strategy,
        instrument=args.instrument,
        include_no_oanda=args.include_no_oanda,
        verify_oanda=args.verify_oanda,
    )
    print(f"candidates={len(candidates)} apply={args.apply}")
    for cand in candidates:
        print(
            f"{cand.entry_time} {cand.trade_id} {cand.entry_type} "
            f"{cand.instrument} {cand.direction} "
            f"entry={cand.entry_price:.5f} signal={cand.signal_price:.5f} "
            f"old_slip={cand.old_slippage_pips:.2f} "
            f"oanda={cand.oanda_trade_id or '-'} {cand.reason}"
        )
    if args.apply:
        print(f"updated={apply_backfill(conn, candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
