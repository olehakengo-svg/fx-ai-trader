#!/usr/bin/env bash
# Wrap _bt_profile_runner.py with py-spy to produce a sampling flamegraph.
#
# Usage:
#   ./scripts/profile_bt.sh [SYMBOL] [DAYS]
#   ./scripts/profile_bt.sh USDJPY=X 1
#
# Output:
#   profile_<sym>_<days>d_<ts>.svg  — open in any browser
#
# py-spy is sampling-based, so wall-clock impact is small and the time
# distribution closely tracks reality. Pair this with a cProfile run for
# call-count accuracy (cProfile is more invasive but catches every call).

set -euo pipefail

SYMBOL="${1:-USDJPY=X}"
DAYS="${2:-1}"
SAFE_SYM="${SYMBOL//=/}"
SAFE_SYM="${SAFE_SYM//\//_}"
TS="$(date +%Y%m%d_%H%M%S)"
OUT="profile_${SAFE_SYM}_${DAYS}d_${TS}.svg"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

if ! command -v py-spy >/dev/null 2>&1; then
  echo "py-spy not installed. Run: pip install -r requirements-dev.txt" >&2
  exit 1
fi

echo "[profile_bt] symbol=${SYMBOL} days=${DAYS} → ${OUT}"
py-spy record -o "${OUT}" --rate 100 --subprocesses -- \
  python3 _bt_profile_runner.py --symbol "${SYMBOL}" --days "${DAYS}" --no-cprofile

echo "[profile_bt] flamegraph: ${PROJECT_ROOT}/${OUT}"
echo "[profile_bt] open in browser to inspect."
