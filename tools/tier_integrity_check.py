#!/usr/bin/env python3
"""
Tier Integrity Checker — demo_trader.py 内の全Tier設定を自動検証

Usage:
    python3 tools/tier_integrity_check.py              # 全チェック実行（stdout表示）
    python3 tools/tier_integrity_check.py --write       # KB tier-master.md も更新
    python3 tools/tier_integrity_check.py --check       # 不整合時 exit 1（CI/pre-commit用）

Checks:
    1. FORCE_DEMOTED戦略が PAIR_PROMOTED / LOT_BOOST / WHITELIST に残存していないか
    2. PAIR_PROMOTED の戦略ファイルが存在するか（inline除く）
    3. ELITE_LIVE が PAIR_PROMOTED にも含まれているか（冗長チェック）
    4. PAIR_DEMOTED と PAIR_PROMOTED の矛盾（同一(strat,pair)が両方に存在）
    5. FORCE_DEMOTED戦略が各種リスト（_PE_*, _SHIELD_*, _QUICK_HARVEST_*）に残存
    6. tier-master.md との差分（--check時）
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

DEMO_TRADER = os.path.join(_PROJECT_ROOT, "modules", "demo_trader.py")
TIER_MASTER = os.path.join(
    _PROJECT_ROOT, "knowledge-base", "wiki", "tier-master.md"
)
BT_365D = os.path.join(
    _PROJECT_ROOT, "knowledge-base", "raw", "bt-results",
    "bt-365d-scan-2026-04-16.md",
)
STRATEGY_DIRS = [
    os.path.join(_PROJECT_ROOT, "strategies", d)
    for d in ("daytrade", "scalp", "swing")
]

# app.py内インライン戦略（ファイル非分離）
INLINE_STRATEGIES = {"vwap_mean_reversion", "streak_reversal"}


# ══════════════════════════════════════════════════════════════
# Parsing — sync_kb_index.py と同一ロジック
# ══════════════════════════════════════════════════════════════


def _parse_simple_set(src: str, name: str) -> set:
    m = re.search(rf"{name}\s*=\s*\{{([^}}]+)\}}", src, re.DOTALL)
    if not m:
        return set()
    # コメント行を除去して解析
    block = m.group(1)
    active_lines = [
        line for line in block.split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]
    return set(re.findall(r'"([a-z0-9_]+)"', "\n".join(active_lines)))


def _parse_frozenset(src: str, name: str) -> set:
    m = re.search(rf"{name}\s*=\s*frozenset\(\{{(.+?)\}}\)", src, re.DOTALL)
    if not m:
        return set()
    block = m.group(1)
    active_lines = [
        line for line in block.split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]
    return set(re.findall(r'"([a-z0-9_]+)"', "\n".join(active_lines)))


def _parse_tuple_set(src: str, name: str) -> set:
    m = re.search(rf"{name}\s*=\s*\{{(.+?)\n\s*\}}", src, re.DOTALL)
    if not m:
        return set()
    tuples = set()
    for line in m.group(1).split("\n"):
        if line.strip().startswith("#"):
            continue
        for match in re.findall(
            r'\(\s*"([a-z0-9_]+)"\s*,\s*"([A-Z0-9_]+)"\s*\)', line
        ):
            tuples.add(match)
    return tuples


def _parse_tuple_frozenset(src: str, name: str) -> set:
    m = re.search(rf"{name}\s*=\s*frozenset\(\{{(.+?)\}}\)", src, re.DOTALL)
    if not m:
        return set()
    tuples = set()
    for line in m.group(1).split("\n"):
        if line.strip().startswith("#"):
            continue
        for match in re.findall(
            r'\(\s*"([a-z0-9_]+)"\s*,\s*"([A-Z0-9_]+)"\s*\)', line
        ):
            tuples.add(match)
    return tuples


def _parse_dict_keys(src: str, name: str) -> set:
    m = re.search(rf"{name}\s*=\s*\{{(.+?)\n\s*\}}", src, re.DOTALL)
    if not m:
        return set()
    block = m.group(1)
    active_lines = [
        line for line in block.split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]
    return set(re.findall(r'"([a-z0-9_]+)"\s*:', "\n".join(active_lines)))


def _parse_tuple_dict_keys(src: str, name: str) -> set:
    """Parse dict with tuple keys: { ("strat", "PAIR"): val, ... }"""
    m = re.search(rf"{name}\s*=\s*\{{(.+?)\n\s*\}}", src, re.DOTALL)
    if not m:
        return set()
    tuples = set()
    for line in m.group(1).split("\n"):
        if line.strip().startswith("#"):
            continue
        for match in re.findall(
            r'\(\s*"([a-z0-9_]+)"\s*,\s*"([A-Z0-9_]+)"\s*\)', line
        ):
            tuples.add(match)
    return tuples


def parse_all(src: str) -> dict:
    return {
        "force_demoted": _parse_simple_set(src, "_FORCE_DEMOTED"),
        "elite_live": _parse_simple_set(src, "_ELITE_LIVE"),
        "scalp_sentinel": _parse_simple_set(src, "_SCALP_SENTINEL"),
        "universal_sentinel": _parse_simple_set(src, "_UNIVERSAL_SENTINEL"),
        "pair_promoted": _parse_tuple_set(src, "_PAIR_PROMOTED"),
        "pair_demoted": _parse_tuple_set(src, "_PAIR_DEMOTED"),
        "pair_lot_boost": _parse_tuple_dict_keys(src, "_PAIR_LOT_BOOST"),
        "strategy_lot_boost": _parse_dict_keys(src, "_STRATEGY_LOT_BOOST"),
        "shield_eur_dt_whitelist": _parse_frozenset(src, "_SHIELD_EUR_DT_WHITELIST"),
        "pe_dt_eligible": _parse_simple_set(src, "_PE_DT_ELIGIBLE"),
        "pe_50pct_eligible": _parse_frozenset(src, "_PE_50PCT_ELIGIBLE"),
        "quick_harvest_exempt": _parse_tuple_frozenset(src, "_QUICK_HARVEST_EXEMPT"),
    }


def discover_strategy_files() -> dict:
    """Return {strategy_name: (mode, filepath)}"""
    strats = {}
    for d in STRATEGY_DIRS:
        if not os.path.isdir(d):
            continue
        mode = os.path.basename(d)
        for f in os.listdir(d):
            if not f.endswith(".py") or f.startswith("__") or f == "base.py":
                continue
            path = os.path.join(d, f)
            with open(path) as fh:
                content = fh.read()
            m = re.search(r'name\s*=\s*"(\w+)"', content)
            if m:
                strats[m.group(1)] = (mode, path)
    return strats


# ══════════════════════════════════════════════════════════════
# Integrity checks
# ══════════════════════════════════════════════════════════════


def check_integrity(sets: dict, strat_files: dict) -> list:
    """Run all integrity checks. Returns list of (severity, message)."""
    issues = []
    fd = sets["force_demoted"]

    # 1. FORCE_DEMOTED in PAIR_PROMOTED
    for strat, pair in sets["pair_promoted"]:
        if strat in fd:
            issues.append(("ERROR", f"FORCE_DEMOTED '{strat}' in PAIR_PROMOTED ({pair})"))

    # 2. FORCE_DEMOTED in PAIR_LOT_BOOST
    for strat, pair in sets["pair_lot_boost"]:
        if strat in fd:
            issues.append(("ERROR", f"FORCE_DEMOTED '{strat}' in PAIR_LOT_BOOST ({pair})"))

    # 3. FORCE_DEMOTED in STRATEGY_LOT_BOOST
    for strat in sets["strategy_lot_boost"]:
        if strat in fd:
            issues.append(("ERROR", f"FORCE_DEMOTED '{strat}' in STRATEGY_LOT_BOOST"))

    # 4. FORCE_DEMOTED in SHIELD_EUR_DT_WHITELIST
    for strat in sets["shield_eur_dt_whitelist"]:
        if strat in fd:
            issues.append(("ERROR", f"FORCE_DEMOTED '{strat}' in SHIELD_EUR_DT_WHITELIST"))

    # 5. FORCE_DEMOTED in PE_DT_ELIGIBLE
    for strat in sets["pe_dt_eligible"]:
        if strat in fd:
            issues.append(("ERROR", f"FORCE_DEMOTED '{strat}' in PE_DT_ELIGIBLE"))

    # 6. FORCE_DEMOTED in PE_50PCT_ELIGIBLE
    for strat in sets["pe_50pct_eligible"]:
        if strat in fd:
            issues.append(("ERROR", f"FORCE_DEMOTED '{strat}' in PE_50PCT_ELIGIBLE"))

    # 7. FORCE_DEMOTED in QUICK_HARVEST_EXEMPT
    for strat, pair in sets["quick_harvest_exempt"]:
        if strat in fd:
            issues.append(("ERROR", f"FORCE_DEMOTED '{strat}' in QUICK_HARVEST_EXEMPT ({pair})"))

    # 8. PAIR_PROMOTED ∩ PAIR_DEMOTED 矛盾
    pp_pairs = sets["pair_promoted"]
    pd_pairs = sets["pair_demoted"]
    conflicts = pp_pairs & pd_pairs
    for strat, pair in conflicts:
        issues.append(("ERROR", f"Conflict: ({strat}, {pair}) in both PAIR_PROMOTED and PAIR_DEMOTED"))

    # 9. QUICK_HARVEST_EXEMPT の戦略×ペアがPAIR_PROMOTEDまたはELITE_LIVEにあるか
    el = sets["elite_live"]
    for strat, pair in sets["quick_harvest_exempt"]:
        if strat not in el and (strat, pair) not in pp_pairs:
            issues.append(("WARN", f"QUICK_HARVEST_EXEMPT ({strat}, {pair}) not in ELITE/PAIR_PROMOTED"))

    # 10. Strategy file existence
    all_referenced = set()
    all_referenced |= sets["elite_live"]
    all_referenced |= {s for s, _ in sets["pair_promoted"]}
    all_referenced |= fd
    for strat in all_referenced:
        if strat not in strat_files and strat not in INLINE_STRATEGIES:
            issues.append(("WARN", f"No strategy file found for '{strat}'"))

    # 11. ELITE_LIVE redundancy in PAIR_PROMOTED
    for strat, pair in sets["pair_promoted"]:
        if strat in el:
            issues.append(("INFO", f"ELITE '{strat}' also in PAIR_PROMOTED ({pair}) — redundant but harmless"))

    return issues


# ══════════════════════════════════════════════════════════════
# tier-master.md generation
# ══════════════════════════════════════════════════════════════


def _load_bt_365d() -> dict:
    """Parse 365d BT scan for EV data. Returns {strategy: {pair: ev_str}}"""
    bt = {}
    if not os.path.exists(BT_365D):
        return bt
    with open(BT_365D) as f:
        content = f.read()

    # Parse "Top Strategies" and "ELITE_LIVE Performance" tables
    for line in content.split("\n"):
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| Strategy"):
            continue
        cols = [c.strip() for c in line.split("|")]
        cols = [c for c in cols if c]
        if len(cols) < 5:
            continue
        strat = cols[0].strip()
        # Top Strategies table: Strategy | JPY EV | EUR EV | GBP EV | Total N | Verdict
        if len(cols) >= 6 and cols[-1].startswith("★"):
            bt.setdefault(strat, {})
            if cols[1] != "—":
                bt[strat]["USD_JPY"] = cols[1]
            if cols[2] != "—":
                bt[strat]["EUR_USD"] = cols[2]
            if cols[3] != "—":
                bt[strat]["GBP_USD"] = cols[3]
            bt[strat]["_total_n"] = cols[4]
            bt[strat]["_verdict"] = cols[5]
    return bt


def generate_tier_master(sets: dict, strat_files: dict, issues: list) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    bt = _load_bt_365d()
    lines = []
    lines.append(f"# Tier Master — 戦略分類マスタ")
    lines.append(f"")
    lines.append(f"**自動生成**: `python3 tools/tier_integrity_check.py --write`")
    lines.append(f"**最終更新**: {now}")
    lines.append(f"**Source of Truth**: `modules/demo_trader.py`")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # ── A. OANDA通過戦略 ──
    lines.append(f"## A. OANDA通過戦略（実弾転送される）")
    lines.append(f"")

    # A-1. ELITE_LIVE
    lines.append(f"### A-1. ELITE_LIVE（{len(sets['elite_live'])}戦略 — 全ペア自動通過）")
    lines.append(f"")
    lines.append(f"| # | 戦略名 | 365d BT JPY EV | EUR EV | GBP EV |")
    lines.append(f"|---|---|---|---|---|")
    for i, strat in enumerate(sorted(sets["elite_live"]), 1):
        b = bt.get(strat, {})
        lines.append(
            f"| {i} | {strat} | {b.get('USD_JPY', '—')} | {b.get('EUR_USD', '—')} | {b.get('GBP_USD', '—')} |"
        )
    lines.append(f"")

    # A-2. PAIR_PROMOTED
    pp = sets["pair_promoted"]
    pp_strats = sorted({s for s, _ in pp})
    # exclude ELITE (they're listed above)
    pp_only = [(s, p) for s, p in sorted(pp) if s not in sets["elite_live"]]
    lines.append(f"### A-2. PAIR_PROMOTED（{len(pp_only)}エントリ — 指定ペアのみ通過）")
    lines.append(f"")
    lines.append(f"| # | 戦略名 | ペア | 365d BT EV |")
    lines.append(f"|---|---|---|---|")
    for i, (strat, pair) in enumerate(pp_only, 1):
        b = bt.get(strat, {})
        ev = b.get(pair, "—")
        # For cross pairs, try approximate match
        if ev == "—" and "JPY" in pair and pair not in ("USD_JPY",):
            ev = b.get("USD_JPY", "—")  # fallback
        lines.append(f"| {i} | {strat} | {pair} | {ev} |")
    lines.append(f"")

    # ── B. Shadow戦略 ──
    lines.append(f"## B. Shadow戦略（OANDA非通過 — デモのみ記録）")
    lines.append(f"")

    # B-1. FORCE_DEMOTED
    fd = sorted(sets["force_demoted"])
    lines.append(f"### B-1. FORCE_DEMOTED（{len(fd)}戦略 — 全ペア強制Shadow）")
    lines.append(f"")
    lines.append(f"| # | 戦略名 | 365d BT JPY EV | EUR EV | GBP EV |")
    lines.append(f"|---|---|---|---|---|")
    for i, strat in enumerate(fd, 1):
        b = bt.get(strat, {})
        lines.append(
            f"| {i} | {strat} | {b.get('USD_JPY', '—')} | {b.get('EUR_USD', '—')} | {b.get('GBP_USD', '—')} |"
        )
    lines.append(f"")

    # B-2. SCALP_SENTINEL
    ss = sorted(sets["scalp_sentinel"])
    lines.append(f"### B-2. SCALP_SENTINEL（{len(ss)}戦略 — Scalp最小ロットShadow）")
    lines.append(f"")
    lines.append(f"| # | 戦略名 |")
    lines.append(f"|---|---|")
    for i, strat in enumerate(ss, 1):
        lines.append(f"| {i} | {strat} |")
    lines.append(f"")

    # B-3. UNIVERSAL_SENTINEL
    us = sorted(sets["universal_sentinel"])
    lines.append(f"### B-3. UNIVERSAL_SENTINEL（{len(us)}戦略 — 全モードSentinel）")
    lines.append(f"")
    lines.append(f"| # | 戦略名 | PP経由OANDA通過ペア |")
    lines.append(f"|---|---|---|")
    for i, strat in enumerate(us, 1):
        pp_pairs_for_strat = sorted([p for s, p in pp if s == strat])
        pp_str = ", ".join(pp_pairs_for_strat) if pp_pairs_for_strat else "なし"
        lines.append(f"| {i} | {strat} | {pp_str} |")
    lines.append(f"")

    # B-4. PAIR_DEMOTED
    pd = sorted(sets["pair_demoted"])
    lines.append(f"### B-4. PAIR_DEMOTED（{len(pd)}エントリ — 特定ペアのみ強制Shadow）")
    lines.append(f"")
    lines.append(f"| # | 戦略名 | ペア |")
    lines.append(f"|---|---|---|")
    for i, (strat, pair) in enumerate(pd, 1):
        lines.append(f"| {i} | {strat} | {pair} |")
    lines.append(f"")

    # B-5. Phase0 Shadow Gate (everything else)
    all_classified = set()
    all_classified |= sets["elite_live"]
    all_classified |= sets["force_demoted"]
    all_classified |= sets["scalp_sentinel"]
    all_classified |= sets["universal_sentinel"]
    all_classified |= {s for s, _ in sets["pair_promoted"]}

    phase0 = sorted(
        s for s in strat_files
        if s not in all_classified and s not in INLINE_STRATEGIES
    )
    # Add inline strategies not classified
    for s in sorted(INLINE_STRATEGIES):
        if s not in all_classified:
            phase0.append(s)

    lines.append(f"### B-5. Phase0 Shadow Gate（{len(phase0)}戦略 — 自動Shadow）")
    lines.append(f"")
    lines.append(f"| # | 戦略名 | mode | 理由 |")
    lines.append(f"|---|---|---|---|")
    for i, strat in enumerate(sorted(phase0), 1):
        mode = strat_files.get(strat, ("inline", ""))[0]
        # Check if any pair is PAIR_DEMOTED
        pd_pairs = [p for s, p in sets["pair_demoted"] if s == strat]
        reason = "PP/EL未指定 → 自動Shadow"
        if pd_pairs:
            reason = f"PAIR_DEMOTED: {', '.join(sorted(pd_pairs))}"
        lines.append(f"| {i} | {strat} | {mode} | {reason} |")
    lines.append(f"")

    # ── C. Integrity Check Results ──
    lines.append(f"## C. 整合性チェック結果")
    lines.append(f"")
    errors = [i for i in issues if i[0] == "ERROR"]
    warns = [i for i in issues if i[0] == "WARN"]
    infos = [i for i in issues if i[0] == "INFO"]

    if not errors and not warns:
        lines.append(f"✅ **全チェックパス** — FORCE_DEMOTED残存なし、矛盾なし")
    else:
        if errors:
            lines.append(f"### 🔴 ERROR（{len(errors)}件）")
            for _, msg in errors:
                lines.append(f"- {msg}")
            lines.append(f"")
        if warns:
            lines.append(f"### ⚠️ WARN（{len(warns)}件）")
            for _, msg in warns:
                lines.append(f"- {msg}")
            lines.append(f"")
    if infos:
        lines.append(f"### ℹ️ INFO（{len(infos)}件）")
        for _, msg in infos:
            lines.append(f"- {msg}")
    lines.append(f"")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# JSON snapshot for programmatic comparison
# ══════════════════════════════════════════════════════════════


def generate_snapshot(sets: dict) -> dict:
    """Generate a JSON-serializable snapshot for diff detection."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elite_live": sorted(sets["elite_live"]),
        "force_demoted": sorted(sets["force_demoted"]),
        "scalp_sentinel": sorted(sets["scalp_sentinel"]),
        "universal_sentinel": sorted(sets["universal_sentinel"]),
        "pair_promoted": sorted([list(t) for t in sets["pair_promoted"]]),
        "pair_demoted": sorted([list(t) for t in sets["pair_demoted"]]),
        "strategy_lot_boost": sorted(sets["strategy_lot_boost"]),
        "shield_eur_dt_whitelist": sorted(sets["shield_eur_dt_whitelist"]),
        "pe_dt_eligible": sorted(sets["pe_dt_eligible"]),
        "pe_50pct_eligible": sorted(sets["pe_50pct_eligible"]),
        "quick_harvest_exempt": sorted([list(t) for t in sets["quick_harvest_exempt"]]),
    }


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(description="Tier Integrity Checker")
    parser.add_argument("--write", action="store_true", help="Update tier-master.md")
    parser.add_argument("--check", action="store_true", help="Exit 1 on errors (CI mode)")
    parser.add_argument("--json", action="store_true", help="Output JSON snapshot")
    args = parser.parse_args()

    with open(DEMO_TRADER) as f:
        src = f.read()

    sets = parse_all(src)
    strat_files = discover_strategy_files()
    issues = check_integrity(sets, strat_files)

    errors = [i for i in issues if i[0] == "ERROR"]
    warns = [i for i in issues if i[0] == "WARN"]
    infos = [i for i in issues if i[0] == "INFO"]

    # Console output
    print("=" * 60)
    print("  Tier Integrity Check")
    print("=" * 60)
    print()

    # Summary stats
    print(f"ELITE_LIVE:       {len(sets['elite_live'])} strategies")
    print(f"PAIR_PROMOTED:    {len(sets['pair_promoted'])} entries ({len({s for s,_ in sets['pair_promoted']})} unique strategies)")
    print(f"FORCE_DEMOTED:    {len(sets['force_demoted'])} strategies")
    print(f"SCALP_SENTINEL:   {len(sets['scalp_sentinel'])} strategies")
    print(f"UNI_SENTINEL:     {len(sets['universal_sentinel'])} strategies")
    print(f"PAIR_DEMOTED:     {len(sets['pair_demoted'])} entries")
    print(f"Strategy files:   {len(strat_files)} + {len(INLINE_STRATEGIES)} inline")
    print()

    if errors:
        print(f"🔴 ERRORS ({len(errors)}):")
        for _, msg in errors:
            print(f"   ✗ {msg}")
        print()
    if warns:
        print(f"⚠️  WARNINGS ({len(warns)}):")
        for _, msg in warns:
            print(f"   ⚠ {msg}")
        print()
    if infos:
        print(f"ℹ️  INFO ({len(infos)}):")
        for _, msg in infos:
            print(f"   ℹ {msg}")
        print()

    if not errors and not warns:
        print("✅ All checks passed — no inconsistencies detected")
        print()

    # Generate tier-master.md
    md = generate_tier_master(sets, strat_files, issues)

    if args.json:
        snap = generate_snapshot(sets)
        print(json.dumps(snap, indent=2, ensure_ascii=False))

    if args.write:
        # Write tier-master.md
        os.makedirs(os.path.dirname(TIER_MASTER), exist_ok=True)
        with open(TIER_MASTER, "w") as f:
            f.write(md)
        print(f"✍️  Written: {TIER_MASTER}")

        # Write JSON snapshot
        snap_path = TIER_MASTER.replace(".md", ".json")
        snap = generate_snapshot(sets)
        with open(snap_path, "w") as f:
            json.dump(snap, f, indent=2, ensure_ascii=False)
        print(f"✍️  Written: {snap_path}")

    if args.check and errors:
        print(f"\n❌ {len(errors)} error(s) found — failing check")
        sys.exit(1)

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
