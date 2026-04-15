#!/usr/bin/env python3
"""
KB Index Sync — demo_trader.py の戦略セットから index.md の Current Portfolio を自動生成

Usage:
    python3 tools/sync_kb_index.py              # --dry-run (default): print output
    python3 tools/sync_kb_index.py --write       # update index.md in-place
    python3 tools/sync_kb_index.py --check       # exit 1 if out of sync (for pre-commit)
"""

import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

# プロジェクトルートをsys.pathに追加（CLIから実行時にmodulesをimport可能にする）
_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# dotenv (optional)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
except ImportError:
    pass

# ── Paths ──
DEMO_TRADER = os.path.join(_PROJECT_ROOT, "modules", "demo_trader.py")
INDEX_MD = os.path.join(_PROJECT_ROOT, "knowledge-base", "wiki", "index.md")
BT_SCAN = os.path.join(
    _PROJECT_ROOT, "knowledge-base", "raw", "bt-results",
    "comprehensive-bt-scan-2026-04-14.md",
)

# Marker comments for in-place replacement
MARKER_START = "<!-- KB_PORTFOLIO_START -->"
MARKER_END = "<!-- KB_PORTFOLIO_END -->"


# ══════════════════════════════════════════════════════════════
# Parsing helpers
# ══════════════════════════════════════════════════════════════


def _parse_simple_set(src: str, name: str) -> set:
    """Parse a simple set like _FORCE_DEMOTED = { "a", "b" }"""
    m = re.search(rf"{name}\s*=\s*\{{([^}}]+)\}}", src, re.DOTALL)
    if not m:
        return set()
    return set(re.findall(r'"([a-z_]+)"', m.group(1)))


def _parse_dict_keys(src: str, name: str) -> set:
    """Parse dict keys like _STRATEGY_LOT_BOOST = { "a": 1.5, ... }"""
    m = re.search(rf"{name}\s*=\s*\{{(.+?)\n\s*\}}", src, re.DOTALL)
    if not m:
        return set()
    return set(re.findall(r'"([a-z_]+)"\s*:', m.group(1)))


def _parse_tuple_set(src: str, name: str) -> set:
    """Parse set of tuples: _PAIR_PROMOTED = { ("strat", "PAIR"), ... }
    Returns set of (strategy, pair) tuples.
    """
    m = re.search(rf"{name}\s*=\s*\{{(.+?)\n\s*\}}", src, re.DOTALL)
    if not m:
        return set()
    tuples = set()
    for match in re.findall(r'\(\s*"([a-z_]+)"\s*,\s*"([A-Z_]+)"\s*\)', m.group(1)):
        tuples.add(match)
    return tuples


def _parse_shadow_mode(src: str) -> bool:
    """Check if _SHADOW_MODE is True by default."""
    m = re.search(r'_SHADOW_MODE\s*=.*?"(\w+)"', src)
    return m.group(1).lower() in ("true", "1", "yes") if m else True


def parse_demo_trader():
    """Read demo_trader.py and extract all strategy classification sets."""
    with open(DEMO_TRADER, "r") as f:
        src = f.read()

    return {
        "elite_live": _parse_simple_set(src, "_ELITE_LIVE"),
        "force_demoted": _parse_simple_set(src, "_FORCE_DEMOTED"),
        "scalp_sentinel": _parse_simple_set(src, "_SCALP_SENTINEL"),
        "universal_sentinel": _parse_simple_set(src, "_UNIVERSAL_SENTINEL"),
        "strategy_lot_boost": _parse_dict_keys(src, "_STRATEGY_LOT_BOOST"),
        "pair_promoted": _parse_tuple_set(src, "_PAIR_PROMOTED"),
        "pair_demoted": _parse_tuple_set(src, "_PAIR_DEMOTED"),
        "shadow_mode": _parse_shadow_mode(src),
    }


def parse_bt_scan():
    """Parse BT scan results into {(strategy, pair): {N, WR, EV, PF, PnL}}."""
    results = {}
    if not os.path.exists(BT_SCAN):
        return results

    with open(BT_SCAN, "r") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|") or line.startswith("|---") or line.startswith("| Strategy"):
                continue
            # Remove bold markers
            line = line.replace("**", "")
            cols = [c.strip() for c in line.split("|")]
            # cols[0] is empty (leading |), cols[-1] is empty (trailing |)
            cols = [c for c in cols if c]
            if len(cols) < 7:
                continue
            strat = cols[0].strip("~ ")
            pair = cols[1]
            try:
                n = int(cols[2])
                wr = cols[3]
                ev = cols[4]
                pf = cols[5]
                pnl = cols[6]
                results[(strat, pair)] = {
                    "N": n, "WR": wr, "EV": ev, "PF": pf, "PnL": pnl,
                }
            except (ValueError, IndexError):
                continue
    return results


# ══════════════════════════════════════════════════════════════
# Classification
# ══════════════════════════════════════════════════════════════


# Manual notes for strategies (override auto-generated notes in SHADOW section)
_SHADOW_NOTES_OVERRIDE = {
    "vol_momentum_scalp": "BT negative EV confirmed (1m/5m), Live WR=80% was N=10 luck",
}


def classify_strategies(sets: dict, bt: dict) -> str:
    """Build the markdown portfolio table from parsed sets and BT data."""
    elite = sets["elite_live"]
    force_demoted = sets["force_demoted"]
    pair_promoted = sets["pair_promoted"]
    pair_demoted = sets["pair_demoted"]
    scalp_sentinel = sets["scalp_sentinel"]
    universal_sentinel = sets["universal_sentinel"]
    lot_boost = sets["strategy_lot_boost"]
    shadow_mode = sets["shadow_mode"]

    # Gather all known strategies
    all_strats = set()
    all_strats |= elite
    all_strats |= force_demoted
    all_strats |= scalp_sentinel
    all_strats |= universal_sentinel
    all_strats |= lot_boost
    all_strats |= {s for s, _ in pair_promoted}
    all_strats |= {s for s, _ in pair_demoted}

    # Pair-promoted strategies (strategy names only)
    pair_promoted_strats = {s for s, _ in pair_promoted}

    today = datetime.now().strftime("%Y-%m-%d")
    lines = []
    lines.append(f"## Current Portfolio (auto-synced, {today})")
    lines.append("")

    # ── ELITE_LIVE ──
    lines.append("### ELITE_LIVE (never shadowed)")
    lines.append("| Strategy | BT Data | Status |")
    lines.append("|----------|---------|--------|")
    for strat in sorted(elite):
        dash_name = strat.replace("_", "-")
        bt_info = _bt_summary(strat, bt)
        lines.append(f"| [[{dash_name}]] | {bt_info} | ELITE_LIVE |")
    lines.append("")

    # ── PAIR_PROMOTED (SENTINEL) ──
    # Strategies that are pair-promoted but not elite
    sentinel_strats = {}
    for strat, pair in sorted(pair_promoted):
        if strat not in elite:
            sentinel_strats.setdefault(strat, []).append(pair)

    lines.append("### PAIR_PROMOTED (SENTINEL)")
    lines.append("| Strategy | Pairs | BT Data | Status |")
    lines.append("|----------|-------|---------|--------|")
    for strat in sorted(sentinel_strats.keys()):
        dash_name = strat.replace("_", "-")
        pairs = ", ".join(sorted(sentinel_strats[strat]))
        bt_info = _bt_summary(strat, bt)
        lines.append(f"| [[{dash_name}]] | {pairs} | {bt_info} | PAIR_PROMOTED |")
    lines.append("")

    # ── SHADOW (Data Collection) ──
    # Not force_demoted, not elite, not pair_promoted-only, but would be shadowed
    shadow_strats = set()
    if shadow_mode:
        for strat in all_strats:
            if (strat not in elite
                    and strat not in force_demoted
                    and strat not in pair_promoted_strats):
                shadow_strats.add(strat)

    # Also include sentinel strategies (scalp + universal) that aren't pair_promoted
    sentinel_only = (scalp_sentinel | universal_sentinel) - elite - force_demoted - pair_promoted_strats
    shadow_strats |= sentinel_only

    # Also include strategies with manual shadow notes
    for strat in _SHADOW_NOTES_OVERRIDE:
        if strat not in elite and strat not in pair_promoted_strats:
            shadow_strats.add(strat)

    if shadow_strats:
        lines.append("### SHADOW (Data Collection)")
        lines.append("| Strategy | BT Data | Notes |")
        lines.append("|----------|---------|-------|")
        for strat in sorted(shadow_strats):
            dash_name = strat.replace("_", "-")
            bt_info = _bt_summary(strat, bt)
            # Use manual override note if available
            if strat in _SHADOW_NOTES_OVERRIDE:
                sentinel_tag = _SHADOW_NOTES_OVERRIDE[strat]
            elif strat in scalp_sentinel:
                sentinel_tag = "SCALP_SENTINEL"
            elif strat in universal_sentinel:
                sentinel_tag = "UNIVERSAL_SENTINEL"
            elif strat in lot_boost:
                sentinel_tag = "LOT_BOOST (not sentinel/elite)"
            else:
                sentinel_tag = "shadow only"
            lines.append(f"| [[{dash_name}]] | {bt_info} | {sentinel_tag} |")
        lines.append("")

    # ── FORCE_DEMOTED ──
    # Skip strategies that are already in ELITE_LIVE or have active PAIR_PROMOTED entries
    force_demoted_display = set()
    for strat in force_demoted:
        if strat in elite:
            continue  # Already shown in ELITE_LIVE
        if strat in pair_promoted_strats:
            continue  # Already shown in PAIR_PROMOTED (SENTINEL)
        force_demoted_display.add(strat)

    lines.append("### FORCE_DEMOTED (stopped)")
    lines.append("| Strategy | BT Data | Status |")
    lines.append("|----------|---------|--------|")
    for strat in sorted(force_demoted_display):
        dash_name = strat.replace("_", "-")
        bt_info = _bt_summary(strat, bt)
        lines.append(f"| [[{dash_name}]] | {bt_info} | FORCE_DEMOTED |")
    lines.append("")

    return "\n".join(lines)


def _bt_summary(strat: str, bt: dict) -> str:
    """Get a compact BT summary for a strategy across all pairs."""
    entries = [(pair, data) for (s, pair), data in bt.items() if s == strat]
    if not entries:
        return "no BT data"
    parts = []
    for pair, data in sorted(entries, key=lambda x: x[0]):
        parts.append(f"{pair}: EV={data['EV']} WR={data['WR']}")
    # Limit to top 3 to keep table readable
    if len(parts) > 3:
        return "; ".join(parts[:3]) + f" (+{len(parts)-3} more)"
    return "; ".join(parts)


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(description="Sync KB index.md with demo_trader.py strategy sets")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", action="store_true", help="Update index.md in-place")
    group.add_argument("--check", action="store_true", help="Exit 1 if out of sync")
    group.add_argument("--dry-run", action="store_true", default=True, help="Print output (default)")
    args = parser.parse_args()

    if not os.path.exists(DEMO_TRADER):
        print(f"ERROR: demo_trader.py not found at {DEMO_TRADER}", file=sys.stderr)
        sys.exit(2)

    sets = parse_demo_trader()
    bt = parse_bt_scan()
    output = classify_strategies(sets, bt)

    if args.check:
        # Check mode: compare generated output with current index.md
        if not os.path.exists(INDEX_MD):
            print("index.md not found — out of sync", file=sys.stderr)
            sys.exit(1)

        with open(INDEX_MD, "r") as f:
            current = f.read()

        if MARKER_START in current and MARKER_END in current:
            # Extract current portfolio section between markers
            m = re.search(
                rf"{re.escape(MARKER_START)}\n(.+?)\n{re.escape(MARKER_END)}",
                current, re.DOTALL,
            )
            if m:
                current_section = m.group(1).strip()
                if current_section == output.strip():
                    print("index.md is in sync.")
                    sys.exit(0)
                else:
                    print("index.md is out of sync with demo_trader.py strategy sets.")
                    sys.exit(1)

        # No markers found — always out of sync
        print("index.md is out of sync (no sync markers found).")
        sys.exit(1)

    elif args.write:
        if not os.path.exists(INDEX_MD):
            print(f"ERROR: index.md not found at {INDEX_MD}", file=sys.stderr)
            sys.exit(2)

        with open(INDEX_MD, "r") as f:
            current = f.read()

        wrapped = f"{MARKER_START}\n{output}\n{MARKER_END}"

        if MARKER_START in current and MARKER_END in current:
            # Replace between markers
            updated = re.sub(
                rf"{re.escape(MARKER_START)}\n.+?\n{re.escape(MARKER_END)}",
                wrapped,
                current,
                flags=re.DOTALL,
            )
        else:
            # Insert markers around the existing "Current Portfolio" section
            # Try to find and replace the section header
            m = re.search(r"(## Current Portfolio[^\n]*\n)", current)
            if m:
                # Find the next ## header after Current Portfolio
                rest = current[m.end():]
                next_header = re.search(r"\n## ", rest)
                if next_header:
                    end_pos = m.end() + next_header.start()
                    updated = current[:m.start()] + wrapped + "\n\n" + current[end_pos:]
                else:
                    updated = current[:m.start()] + wrapped + "\n\n"
            else:
                # Append after the first heading
                first_heading_end = current.find("\n", current.find("# "))
                if first_heading_end > 0:
                    updated = (
                        current[:first_heading_end + 1] + "\n" + wrapped + "\n\n"
                        + current[first_heading_end + 1:]
                    )
                else:
                    updated = wrapped + "\n\n" + current

        with open(INDEX_MD, "w") as f:
            f.write(updated)
        print(f"index.md updated with {MARKER_START}...{MARKER_END} section.")

    else:
        # Dry-run: just print
        print(output)


if __name__ == "__main__":
    main()
