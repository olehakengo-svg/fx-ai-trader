"""Phase 2 catch-up runner: replay shadow strategies on new OANDA M5 candles.

Usage:
    python3 scripts/phase2_shadow_catchup.py SPX500_USD M5
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from cfd_trader.data.oanda_client import OandaClient
from cfd_trader.shadow.runner import run_shadow_cycle

import cfd_trader.strategies.ported.orb_ny_open_short  # noqa: F401


SHADOW_REGISTRATIONS = [
    {
        "strategy_name": "orb_ny_open_short",
        "bonferroni_m": 2,
        "selection_reason": "short_only_post_hoc (P3W1 forensic 2026-05-11)",
    },
]


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: phase2_shadow_catchup.py <instrument> <granularity>")
        return 2
    _, instrument, granularity = argv

    load_dotenv()
    client = OandaClient(
        token=os.environ["OANDA_API_TOKEN"],
        account_id=os.environ["OANDA_ACCOUNT_ID"],
        env=os.environ.get("OANDA_ENV", "live"),
    )
    db_path = os.environ.get("CFD_DB_PATH", "./cfd_trader.db")

    grand_total = 0
    for reg in SHADOW_REGISTRATIONS:
        n = run_shadow_cycle(
            db_path=db_path, oanda_client=client,
            instrument=instrument, granularity=granularity, **reg,
        )
        print(f"{reg['strategy_name']}: +{n} new shadow trades")
        grand_total += n
    print(f"---- total new shadow trades: {grand_total} ----")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
