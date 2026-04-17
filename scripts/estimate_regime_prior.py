#!/usr/bin/env python3
"""
Estimate π_long_run — long-run regime distribution per instrument
═════════════════════════════════════════════════════════════════

OANDA OHLC を独立 source として各ペアの regime 時間比率を推定する.
[[conditional-edge-estimand-2026-04-17]] §6 の π_long_run 推定実装.

Usage:
    python3 scripts/estimate_regime_prior.py
    python3 scripts/estimate_regime_prior.py --chunks 8 --granularity H1

出力:
    stdout に π 表
    --write 指定で KB (conditional-edge-estimand-2026-04-17.md) の暫定表を更新
"""
from __future__ import annotations
import argparse
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


INSTRUMENTS = ["EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD"]
# XAU_USD: feedback_exclude_xau により除外


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", type=int, default=4,
                        help="OANDA 5000-bar chunks to walk back (default 4)")
    parser.add_argument("--granularity", default="H1",
                        choices=["M30", "H1", "H4"])
    parser.add_argument("--instruments", nargs="+", default=INSTRUMENTS)
    parser.add_argument("--write", action="store_true",
                        help="Update KB file with resulting table")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    from research.edge_discovery.regime_labeler import estimate_pi_long_run
    from modules.oanda_client import OandaClient

    client = OandaClient()

    print("=" * 80)
    print("π_long_run ESTIMATION")
    print(f"granularity={args.granularity}  chunks={args.chunks}  "
          f"(max ~{args.chunks * 5000} bars per pair)")
    print("=" * 80)

    results = {}
    for inst in args.instruments:
        print(f"\n[{inst}]")
        try:
            pi = estimate_pi_long_run(
                instrument=inst,
                n_chunks=args.chunks,
                granularity=args.granularity,
                client=client,
                verbose=args.verbose,
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        results[inst] = pi
        n = pi["n_bars"]
        print(f"  N={n}  period: {pi['start']} → {pi['end']}")
        print(f"    up_trend   {pi['up_trend']*100:5.1f}%")
        print(f"    down_trend {pi['down_trend']*100:5.1f}%")
        print(f"    range      {pi['range']*100:5.1f}%")
        print(f"    uncertain  {pi['uncertain']*100:5.1f}%")

    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"{'Pair':12s} {'up':>8s} {'down':>8s} {'range':>8s} "
          f"{'uncertain':>10s} {'n_bars':>8s}")
    for inst, pi in results.items():
        print(f"{inst:12s} {pi['up_trend']*100:7.1f}% "
              f"{pi['down_trend']*100:7.1f}% "
              f"{pi['range']*100:7.1f}% "
              f"{pi['uncertain']*100:9.1f}% "
              f"{pi['n_bars']:8d}")

    # Write to KB
    if args.write:
        kb_path = ROOT / "knowledge-base/wiki/analyses/conditional-edge-estimand-2026-04-17.md"
        if not kb_path.exists():
            print(f"\n⚠ KB file not found: {kb_path}")
            return

        table_lines = [
            "```",
            f"π_long_run ({args.granularity}, "
            f"~{args.chunks * 5000} bars, est. 2026-04-17):",
            f"  Pair        up_trend  down_trend  range   uncertain  n_bars",
        ]
        for inst in args.instruments:
            if inst not in results:
                continue
            pi = results[inst]
            table_lines.append(
                f"  {inst:10s}  {pi['up_trend']*100:6.1f}%  "
                f"{pi['down_trend']*100:8.1f}%  "
                f"{pi['range']*100:5.1f}%  "
                f"{pi['uncertain']*100:7.1f}%    "
                f"{pi['n_bars']}"
            )
        table_lines.append("```")

        import re
        content = kb_path.read_text()
        old_block = re.search(
            r"```\nπ_long_run \(provisional.*?\n```", content, re.DOTALL
        )
        if old_block:
            new_content = content[:old_block.start()] + "\n".join(table_lines) + content[old_block.end():]
            kb_path.write_text(new_content)
            print(f"\n✅ Updated KB: {kb_path}")
        else:
            print(f"\n⚠ Could not locate provisional block in KB; printing only")
            print("\n".join(table_lines))


if __name__ == "__main__":
    main()
