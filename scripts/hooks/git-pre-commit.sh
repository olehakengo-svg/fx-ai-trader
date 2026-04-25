#!/usr/bin/env bash
# FX AI Trader — pre-commit hook
# Runs fast checks (<10s) before allowing a commit.
# Install: ln -sf ../../scripts/hooks/git-pre-commit.sh .git/hooks/pre-commit

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"

echo "[pre-commit] Running tests..."
python3 -m pytest "$REPO_ROOT/tests/" -x -q || {
    echo "[pre-commit] Tests failed. Commit blocked."
    exit 1
}

echo "[pre-commit] Running consistency check..."
python3 "$REPO_ROOT/scripts/check.py" --quiet || {
    echo "[pre-commit] Consistency check failed. Commit blocked."
    exit 1
}

# v8.9: 宣言トラッカー — 未完了の宣言がないか確認
echo "[pre-commit] Checking declaration tracker..."
TODAY=$(date +%Y-%m-%d)
SESSION_FILE="$REPO_ROOT/knowledge-base/wiki/sessions/${TODAY}-session.md"
if [[ -f "$SESSION_FILE" ]]; then
    PENDING=$(grep -c '^\- \[ \].*🔊' "$SESSION_FILE" 2>/dev/null || true)
    PENDING=${PENDING:-0}
    if [[ "$PENDING" =~ ^[0-9]+$ ]] && [[ "$PENDING" -gt 0 ]]; then
        echo ""
        echo "⚠️  未完了の宣言が${PENDING}件あります:"
        grep '^\- \[ \].*🔊' "$SESSION_FILE" 2>/dev/null | head -5
        echo ""
        echo "コミット前に完了させるか、意図的にスキップする場合はこのまま続行。"
        echo "(ブロックはしません — 警告のみ)"
    fi
fi

# ── KB Integrity: Strategy Wiki Check ──
# For each strategy in QUALIFIED sets, verify a wiki page exists
echo "[pre-commit] Checking strategy wiki pages..."
STRATEGIES_DIR="$REPO_ROOT/knowledge-base/wiki/strategies"
DEMO_TRADER="$REPO_ROOT/modules/demo_trader.py"
WIKI_MISSING=0

if [[ -f "$DEMO_TRADER" ]]; then
    # Extract strategy names from all QUALIFIED sets in demo_trader.py
    # Targets: _FORCE_DEMOTED, _SCALP_SENTINEL, _UNIVERSAL_SENTINEL, _PAIR_PROMOTED (strategy only), _ELITE_LIVE, _STRATEGY_LOT_BOOST
    STRATEGIES=$(python3 -c "
import re, ast

with open('$DEMO_TRADER', 'r') as f:
    src = f.read()

names = set()

# Simple sets: _FORCE_DEMOTED, _SCALP_SENTINEL, _UNIVERSAL_SENTINEL, _ELITE_LIVE
for set_name in ['_FORCE_DEMOTED', '_SCALP_SENTINEL', '_UNIVERSAL_SENTINEL', '_ELITE_LIVE']:
    m = re.search(rf'{set_name}\s*=\s*\{{([^}}]+)\}}', src, re.DOTALL)
    if m:
        for item in re.findall(r'\"([a-z_]+)\"', m.group(1)):
            names.add(item)

# Dict: _STRATEGY_LOT_BOOST — keys are strategy names
m = re.search(r'_STRATEGY_LOT_BOOST\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', src, re.DOTALL)
if m:
    for item in re.findall(r'\"([a-z_]+)\"\s*:', m.group(1)):
        names.add(item)

# Tuple set: _PAIR_PROMOTED — first element of each tuple is the strategy
m = re.search(r'_PAIR_PROMOTED\s*=\s*\{(.+?)\n\s*\}', src, re.DOTALL)
if m:
    for item in re.findall(r'\(\"([a-z_]+)\"', m.group(1)):
        names.add(item)

for n in sorted(names):
    print(n)
" 2>/dev/null || true)

    if [[ -n "$STRATEGIES" ]]; then
        while IFS= read -r strat; do
            WIKI_FILE="$STRATEGIES_DIR/$(echo "$strat" | tr '_' '-').md"
            if [[ ! -f "$WIKI_FILE" ]]; then
                WIKI_MISSING=$((WIKI_MISSING + 1))
                if [[ "$WIKI_MISSING" -eq 1 ]]; then
                    echo ""
                    echo "WARNING: Missing strategy wiki pages:"
                fi
                echo "  - $strat -> $(echo "$strat" | tr '_' '-').md"
            fi
        done <<< "$STRATEGIES"
    fi

    if [[ "$WIKI_MISSING" -gt 0 ]]; then
        echo ""
        echo "WARNING: $WIKI_MISSING strategy wiki page(s) missing in knowledge-base/wiki/strategies/"
        echo "(Commit not blocked — create wiki pages when convenient)"
        echo ""
    fi
fi

# ── KB Integrity: index.md Sync Check ──
echo "[pre-commit] Checking index.md sync status..."
SYNC_SCRIPT="$REPO_ROOT/tools/sync_kb_index.py"
if [[ -f "$SYNC_SCRIPT" ]]; then
    SYNC_OUTPUT=$(python3 "$SYNC_SCRIPT" --check 2>/dev/null || true)
    SYNC_EXIT=$?
    if [[ "$SYNC_EXIT" -ne 0 ]] || echo "$SYNC_OUTPUT" | grep -qi "out of sync"; then
        echo ""
        echo "WARNING: index.md may be out of sync with demo_trader.py strategy sets."
        echo "Run 'python3 tools/sync_kb_index.py --write' to update."
        echo "(Commit not blocked — update when convenient)"
        echo ""
    fi
fi

# ── KB Integrity: tier_integrity_check ──
# Added 2026-04-20: Verify code ↔ tier-master.md integrity
echo "[pre-commit] Checking tier integrity..."
TIER_CHECK="$REPO_ROOT/tools/tier_integrity_check.py"
if [[ -f "$TIER_CHECK" ]]; then
    if ! python3 "$TIER_CHECK" --check >/dev/null 2>&1; then
        echo ""
        echo "❌ tier_integrity_check.py --check FAILED"
        echo "   demo_trader.py の Tier 定義と wiki/tier-master.md が不整合。"
        echo "   Run 'python3 tools/tier_integrity_check.py --write' to regenerate."
        echo ""
        exit 1
    fi
fi

# ── KB Integrity: strategies_drift_check ──
# Added 2026-04-20 (P4): Verify wiki/strategies/*.md Status lines vs tier-master.json
echo "[pre-commit] Checking wiki/strategies drift..."
DRIFT_CHECK="$REPO_ROOT/tools/strategies_drift_check.py"
if [[ -f "$DRIFT_CHECK" ]]; then
    if ! python3 "$DRIFT_CHECK" >/dev/null 2>&1; then
        echo ""
        echo "❌ strategies_drift_check.py FAILED"
        echo "   wiki/strategies/*.md の Status 行が tier-master.json と不整合。"
        echo "   Run 'python3 tools/strategies_drift_check.py' for details."
        echo ""
        exit 1
    fi
fi

# ── KB Integrity: edge_md_lint (EDGE.md manifest) ──
# Added 2026-04-26: Validate cell-aware routing manifest
echo "[pre-commit] Checking EDGE.md manifest..."
EDGE_LINT="$REPO_ROOT/tools/edge_md_lint.py"
EDGE_MD="$REPO_ROOT/knowledge-base/wiki/manifests/EDGE.md"
if [[ -f "$EDGE_LINT" && -f "$EDGE_MD" ]]; then
    if ! python3 "$EDGE_LINT" --check "$EDGE_MD" >/dev/null 2>&1; then
        echo ""
        echo "❌ edge_md_lint.py --check FAILED"
        echo "   EDGE.md manifest is invalid. Run:"
        echo "     python3 tools/edge_md_lint.py knowledge-base/wiki/manifests/EDGE.md"
        echo ""
        exit 1
    fi
fi

# ── KB Integrity: routing_table.json sync with EDGE.md ──
# Added 2026-04-26: Ensure exported routing matches manifest
echo "[pre-commit] Checking routing_table.json sync..."
EDGE_EXPORT="$REPO_ROOT/tools/edge_md_export.py"
ROUTING_TABLE="$REPO_ROOT/modules/routing_table.json"
if [[ -f "$EDGE_EXPORT" && -f "$EDGE_MD" && -f "$ROUTING_TABLE" ]]; then
    # Compare ignoring generated_at field
    EXPECTED=$(python3 "$EDGE_EXPORT" --stdout 2>/dev/null \
        | python3 -c "import sys, json; d=json.load(sys.stdin); d.pop('generated_at',None); print(json.dumps(d, sort_keys=True))")
    ACTUAL=$(python3 -c "import json; d=json.load(open('$ROUTING_TABLE')); d.pop('generated_at',None); print(json.dumps(d, sort_keys=True))")
    if [[ "$EXPECTED" != "$ACTUAL" ]]; then
        echo ""
        echo "❌ routing_table.json out of sync with EDGE.md"
        echo "   Run: python3 tools/edge_md_export.py"
        echo ""
        exit 1
    fi
fi

echo "[pre-commit] All checks passed."
