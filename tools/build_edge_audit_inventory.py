"""Generate audits/edge_design/_INVENTORY.md from tier-master.json (W4-EDA Task 1).

Distinct-strategy inventory: one row per strategy file. Multi-pair strategies
collapse into a single row with comma-joined pairs.

Tier mapping:
  Tier 1 = elite_live + pair_promoted   (LIVE, 即影響、最優先)
  Tier 2 = phase0_shadow                (昇格候補、設計欠陥を事前に潰す)
                                          ※ tier-master.json には未収録なので
                                          strategies/ ディレクトリと
                                          all_classified の差分から導出する
  Tier 3 = force_demoted                (思想は正・設計が誤 仮説の本命検証)
  Tier 4 = scalp_sentinel               (既 sentinel 化、最後)

Higher tier wins on dedup: a strategy appearing in both pair_promoted and
force_demoted lands under Tier 1 only.

Schema flexibility (各 tier の entry 形式):
  - list[str]                e.g. ["trendline_sweep"]                 (elite_live, force_demoted, scalp_sentinel)
  - list[list[str, str]]     e.g. [["doji_breakout", "GBP_USD"]]      (pair_promoted, pair_demoted)
  - list[dict]               e.g. [{"strategy": "...", "pair": "..."}] (test fixtures, future schema)
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

TIER_MAP = [
    ("Tier 1 (LIVE)", ["elite_live", "pair_promoted"]),
    ("Tier 2 (Shadow)", ["phase0_shadow"]),
    ("Tier 3 (FORCE_DEMOTED)", ["force_demoted"]),
    ("Tier 4 (SCALP_SENTINEL)", ["scalp_sentinel"]),
]


def _normalize_entries(raw_entries) -> list[tuple[str, str]]:
    """Convert any supported entry shape into list[(strategy, pair)]."""
    out: list[tuple[str, str]] = []
    for e in raw_entries or []:
        if isinstance(e, str):
            out.append((e, "ALL"))
        elif isinstance(e, (list, tuple)):
            strategy = e[0]
            pair = e[1] if len(e) > 1 else "ALL"
            out.append((strategy, pair))
        elif isinstance(e, dict):
            strategy = e["strategy"]
            pair = e.get("pair", "ALL")
            out.append((strategy, pair))
    return out


def _discover_phase0(raw: dict, strategies_dir: Path) -> list[tuple[str, str]]:
    """Phase0 = strategy files not classified by any other tier in tier-master."""
    classified: set[str] = set()
    for key in (
        "elite_live",
        "pair_promoted",
        "force_demoted",
        "scalp_sentinel",
        "universal_sentinel",
        "pair_demoted",
    ):
        for strategy, _pair in _normalize_entries(raw.get(key, [])):
            classified.add(strategy)

    if not strategies_dir.exists():
        return []

    found: list[tuple[str, str]] = []
    for path in sorted(strategies_dir.rglob("*.py")):
        name = path.stem
        if name.startswith("__") or name in {"base", "context", "backtest"}:
            continue
        if name in classified:
            continue
        found.append((name, "ALL"))
    return found


def build(source: Path, out: Path, strategies_dir: Path | None = None) -> None:
    raw = json.loads(source.read_text())
    out.parent.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    lines: list[str] = [
        "# Edge Design Audit — Inventory",
        "",
        "自動生成: `python3 tools/build_edge_audit_inventory.py`",
        "",
    ]

    for tier_label, keys in TIER_MAP:
        lines.append(f"## {tier_label}")
        lines.append("")
        lines.append("| # | Strategy | Pairs | Source Tier |")
        lines.append("|---|---|---|---|")
        idx = 0
        for key in keys:
            if key == "phase0_shadow":
                if strategies_dir is None:
                    entries = _normalize_entries(raw.get("phase0_shadow", []))
                else:
                    entries = _discover_phase0(raw, strategies_dir)
            else:
                entries = _normalize_entries(raw.get(key, []))

            grouped: dict[str, list[str]] = defaultdict(list)
            for strategy, pair in entries:
                grouped[strategy].append(pair)

            for strategy in sorted(grouped):
                if strategy in seen:
                    continue
                seen.add(strategy)
                idx += 1
                pairs = ", ".join(sorted(set(grouped[strategy])))
                lines.append(f"| {idx} | {strategy} | {pairs} | {key} |")
        lines.append("")

    out.write_text("\n".join(lines))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument(
        "--strategies-dir",
        type=Path,
        default=None,
        help="Directory to scan for phase0 (unclassified) strategies. Optional.",
    )
    args = p.parse_args()
    build(args.source, args.out, args.strategies_dir)


if __name__ == "__main__":
    main()
