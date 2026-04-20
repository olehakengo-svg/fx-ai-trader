#!/usr/bin/env python3
"""
Strategies Drift Checker — wiki/strategies/*.md と tier-master.json の整合検証

Usage:
    python3 tools/strategies_drift_check.py            # 全ページ検証、exit 0/1
    python3 tools/strategies_drift_check.py --verbose  # 全戦略の判定理由表示

Purpose:
    bb-rsi-reversion.md 等で "Tier 1 (PAIR_PROMOTED x USD_JPY)" のような
    古い Status 記述が残り、コード実態と乖離するドリフトを検出する。
    lesson-kb-drift-on-context-limit / lesson-strategies-page-drift の再発防止。

Source of Truth:
    knowledge-base/wiki/tier-master.json (tier_integrity_check.py --write で生成)

Checks per wiki/strategies/*.md:
    1. ファイル冒頭 (~40 行) に "Status" / "Stage" セクションが存在
    2. 宣言された主分類 (ELITE_LIVE / PAIR_PROMOTED / FORCE_DEMOTED /
       SCALP_SENTINEL / UNIVERSAL_SENTINEL / SHADOW / Phase0) が実態と整合
    3. 宣言された PAIR_PROMOTED ペアが実際に pair_promoted に存在
    4. 歴史的記述は "履歴" / "Previously" / "Historical" ラベルで明示されている
       (これらは無視される — 現行 Status 行のみ検証)

Heuristics:
    - filename "bb-rsi-reversion.md" → canonical "bb_rsi_reversion"
    - 例外リスト (research-only / meta pages) は _SKIP_FILES で除外
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(os.path.dirname(os.path.abspath(__file__))).parent)
_STRATEGIES_DIR = os.path.join(
    _PROJECT_ROOT, "knowledge-base", "wiki", "strategies"
)
_TIER_JSON = os.path.join(
    _PROJECT_ROOT, "knowledge-base", "wiki", "tier-master.json"
)

# Pages that are not 1:1 strategy refs — skip drift check
_SKIP_FILES = {
    "edge-pipeline.md",           # meta: pipeline stage ladder
    "force-demoted-strategies.md",  # meta: aggregation page
    "xs-momentum-dispersion.md",  # research-only hypothesis page
    "hmm-regime-overlay.md",      # overlay utility, not a tradable strategy
    "hmm-regime-filter.md",       # utility module (evaluate() returns None)
}

# filename → canonical strategy name overrides (when hyphen→underscore fails)
_NAME_OVERRIDES = {
    "rnb-usdjpy.md": "rnb_usdjpy",
}

# Lines containing these phrases are treated as historical context and skipped
# (must be prefixed phrases or clearly retrospective; avoid over-matching current
# words like "recovery path" that can describe ACTIVE states).
_HISTORY_MARKERS = (
    "履歴:",
    "履歴**",
    "**履歴**",
    "historical:",
    "previously ",
    "旧bt",
    "was:",
    "was previously",
    "pre-cutoff (",
    "deprecated",
)


def _canonical_name(filename: str) -> str:
    if filename in _NAME_OVERRIDES:
        return _NAME_OVERRIDES[filename]
    return filename[:-3].replace("-", "_")


def _load_truth() -> dict:
    with open(_TIER_JSON) as f:
        data = json.load(f)
    return {
        "elite_live": set(data["elite_live"]),
        "force_demoted": set(data["force_demoted"]),
        "scalp_sentinel": set(data["scalp_sentinel"]),
        "universal_sentinel": set(data["universal_sentinel"]),
        "pair_promoted": {tuple(x) for x in data["pair_promoted"]},
        "pair_demoted": {tuple(x) for x in data["pair_demoted"]},
    }


def _is_historical(line: str) -> bool:
    low = line.lower()
    return any(m in low for m in _HISTORY_MARKERS)


def _extract_status_lines(path: str) -> list:
    """Extract lines that declare a *current* tier claim.

    We scan the first 40 lines of the file and collect any line that contains
    a tier keyword (PAIR_PROMOTED / FORCE_DEMOTED / ELITE_LIVE / etc.), EXCEPT
    lines marked as historical.

    Also extract the Status / Stage header line (line 3 conventionally) as
    the primary claim — this is what humans read first.
    """
    with open(path) as f:
        lines = f.readlines()[:40]

    claims = []
    for i, raw in enumerate(lines, 1):
        if _is_historical(raw):
            continue
        line = raw.rstrip("\n")
        # match header-style Status / Stage declarations
        if re.match(r"^\s*##?\s*(Status|Stage)\s*[:：]", line, re.IGNORECASE):
            claims.append((i, line, "header"))
            continue
        # bullet "- **Status**: ..."
        if re.match(r"^\s*[-*]\s*\*\*(Status|Stage)\*\*\s*[:：]", line, re.IGNORECASE):
            claims.append((i, line, "bullet"))
            continue
    return claims


def _extract_pairs_in_line(line: str) -> set:
    return set(re.findall(r"\b([A-Z]{3}_[A-Z]{3})\b", line))


_TIER_KEYWORDS = (
    "PAIR_PROMOTED", "PAIR_DEMOTED", "FORCE_DEMOTED",
    "ELITE_LIVE", "SCALP_SENTINEL", "UNIVERSAL_SENTINEL",
)


def _pairs_in_scope(line: str, keyword: str) -> set:
    """Extract pairs that appear after `keyword` but before the next tier keyword.

    Example:
        "UNIVERSAL_SENTINEL + PAIR_PROMOTED (GBP_USD, EUR_USD) + PAIR_DEMOTED (USD_JPY)"
        -> _pairs_in_scope(..., "PAIR_PROMOTED") == {"GBP_USD", "EUR_USD"}
    """
    idx = line.upper().find(keyword)
    if idx < 0:
        return set()
    tail = line[idx + len(keyword):]
    # truncate at next tier keyword occurrence
    next_idx = len(tail)
    tail_upper = tail.upper()
    for kw in _TIER_KEYWORDS:
        if kw == keyword:
            continue
        j = tail_upper.find(kw)
        if j >= 0 and j < next_idx:
            next_idx = j
    scope = tail[:next_idx]
    return _extract_pairs_in_line(scope)


def _check_strategy(strat: str, path: str, truth: dict) -> list:
    """Return list of drift issues for a single strategy page."""
    issues = []
    claims = _extract_status_lines(path)

    in_elite = strat in truth["elite_live"]
    in_fd = strat in truth["force_demoted"]
    in_scalp = strat in truth["scalp_sentinel"]
    in_uni = strat in truth["universal_sentinel"]
    pp_pairs = {p for s, p in truth["pair_promoted"] if s == strat}
    pd_pairs = {p for s, p in truth["pair_demoted"] if s == strat}

    if not claims:
        issues.append(f"[{strat}] no Status/Stage header found in first 40 lines")
        return issues

    # Negative-context patterns: "not in ELITE_LIVE", "but not PAIR_PROMOTED" etc.
    # These are descriptive ("not X"), not tier claims, so must be ignored.
    _NEG_RE = re.compile(
        r"\bnot\s+(in\s+)?(any\s+)?(promotion\S*|demotion\S*|ELITE_LIVE|PAIR_PROMOTED|PAIR_DEMOTED|FORCE_DEMOTED|list)",
        re.IGNORECASE,
    )

    for ln, line, _kind in claims:
        upper = line.upper()
        is_negative_ctx = bool(_NEG_RE.search(line))

        # --- forbidden ELITE_LIVE claim if not actually ELITE ---
        if "ELITE_LIVE" in upper and not in_elite and not is_negative_ctx:
            # ELITE_LIVE bypasses PAIR_PROMOTED, but claiming ELITE on non-elite is drift
            issues.append(
                f"[{strat}] L{ln}: claims ELITE_LIVE but not in truth.elite_live"
            )

        # --- forbidden FORCE_DEMOTED claim if not in FD ---
        # (allow mention like "FORCE_DEMOTED globally but..." only if actually FD)
        if "FORCE_DEMOTED" in upper and not in_fd and not is_negative_ctx:
            issues.append(
                f"[{strat}] L{ln}: claims FORCE_DEMOTED but not in truth.force_demoted"
            )

        # --- PAIR_PROMOTED pair claims must be in truth ---
        if "PAIR_PROMOTED" in upper:
            # Extract only pairs in the PAIR_PROMOTED scope (same parenthetical
            # or to the next qualifier like PAIR_DEMOTED / FORCE_DEMOTED).
            pp_scope_pairs = _pairs_in_scope(line, "PAIR_PROMOTED")
            for p in pp_scope_pairs:
                if (strat, p) not in truth["pair_promoted"]:
                    # Tolerate if strategy is ELITE_LIVE (PP is redundant — handled elsewhere)
                    if in_elite:
                        issues.append(
                            f"[{strat}] L{ln}: stale PAIR_PROMOTED({p}) mention "
                            f"on ELITE_LIVE strategy — PP is redundant/removed"
                        )
                    else:
                        issues.append(
                            f"[{strat}] L{ln}: claims PAIR_PROMOTED x {p} but "
                            f"({strat}, {p}) not in truth.pair_promoted"
                        )

        # --- SCALP_SENTINEL claim must be actual ---
        if "SCALP_SENTINEL" in upper and not in_scalp:
            issues.append(
                f"[{strat}] L{ln}: claims SCALP_SENTINEL but not in truth.scalp_sentinel"
            )

        # --- UNIVERSAL_SENTINEL claim must be actual ---
        if "UNIVERSAL_SENTINEL" in upper and not in_uni:
            issues.append(
                f"[{strat}] L{ln}: claims UNIVERSAL_SENTINEL but not in "
                f"truth.universal_sentinel"
            )

    # --- strategy IS in truth.force_demoted but header doesn't say so ---
    if in_fd:
        header_text = " ".join(c[1].upper() for c in claims)
        if "FORCE_DEMOTED" not in header_text and "FD" not in header_text:
            issues.append(
                f"[{strat}] truth says FORCE_DEMOTED but Status header missing the label"
            )

    # --- strategy IS ELITE_LIVE but header doesn't mention it ---
    if in_elite:
        header_text = " ".join(c[1].upper() for c in claims)
        if "ELITE_LIVE" not in header_text and "ELITE" not in header_text:
            issues.append(
                f"[{strat}] truth says ELITE_LIVE but Status header missing the label"
            )

    # --- strategy is PAIR_DEMOTED on all the pairs that the file claims as PP ---
    # (catches "PAIR_PROMOTED x USD_JPY" on a strategy whose USD_JPY is PAIR_DEMOTED)
    if pd_pairs:
        for ln, line, _ in claims:
            if "PAIR_PROMOTED" in line.upper():
                pp_pairs_claimed = _pairs_in_scope(line, "PAIR_PROMOTED")
                conflict = pp_pairs_claimed & pd_pairs
                if conflict:
                    issues.append(
                        f"[{strat}] L{ln}: claims PAIR_PROMOTED x "
                        f"{sorted(conflict)} but those pairs are PAIR_DEMOTED in truth"
                    )

    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description="Strategies page drift checker")
    ap.add_argument("--verbose", action="store_true",
                    help="Print per-strategy verdict even when clean")
    args = ap.parse_args()

    if not os.path.exists(_TIER_JSON):
        print(f"❌ tier-master.json not found: {_TIER_JSON}")
        print("   Run: python3 tools/tier_integrity_check.py --write")
        return 2

    truth = _load_truth()
    all_strats = (
        truth["elite_live"] | truth["force_demoted"] | truth["scalp_sentinel"]
        | truth["universal_sentinel"]
        | {s for s, _ in truth["pair_promoted"]}
        | {s for s, _ in truth["pair_demoted"]}
    )

    md_files = sorted(
        f for f in os.listdir(_STRATEGIES_DIR)
        if f.endswith(".md") and f not in _SKIP_FILES
    )

    total_issues = []
    checked = 0

    print("=" * 60)
    print("  Strategies Page Drift Check")
    print("=" * 60)
    print(f"Truth source: {os.path.relpath(_TIER_JSON, _PROJECT_ROOT)}")
    print(f"Pages scanned: {len(md_files)} (skipped: {len(_SKIP_FILES)})")
    print()

    for f in md_files:
        strat = _canonical_name(f)
        path = os.path.join(_STRATEGIES_DIR, f)
        issues = _check_strategy(strat, path, truth)
        checked += 1
        if issues:
            total_issues.extend(issues)
            for msg in issues:
                print(f"  ✗ {msg}")
        elif args.verbose:
            known = strat in all_strats
            tag = "known" if known else "orphan"
            print(f"  ✓ {f} ({tag})")

    print()
    if total_issues:
        print(f"❌ {len(total_issues)} drift issue(s) across {checked} pages")
        return 1
    print(f"✅ All {checked} pages integrity-clean vs tier-master.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
