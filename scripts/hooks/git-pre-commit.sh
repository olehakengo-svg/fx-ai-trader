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

echo "[pre-commit] All checks passed."
