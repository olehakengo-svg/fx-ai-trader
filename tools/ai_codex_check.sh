#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
Usage:
  ./tools/ai_codex_check.sh [N]

Shows a compact completion check for the latest Codex companion runs.
N defaults to 8.
EOF
}

case "${1:-}" in
  --help|-h)
    usage
    exit 0
    ;;
esac

LIMIT="${1:-8}"
if ! [[ "$LIMIT" =~ ^[0-9]+$ ]] || (( LIMIT < 1 )); then
  echo "N must be a positive integer: $LIMIT" >&2
  exit 2
fi

TRACK_FILES=()
while IFS= read -r track_file; do
  TRACK_FILES+=("$track_file")
done < <(find .ai/runs -maxdepth 2 -name codex-job.txt -print | sort | tail -"$LIMIT")
if [[ "${#TRACK_FILES[@]}" -eq 0 ]]; then
  echo "No Codex companion runs found under .ai/runs/."
  exit 0
fi

printf "%-8s %-22s %-11s %-28s %s\n" "STATE" "JOB" "PHASE" "RUN" "SUMMARY"
printf "%-8s %-22s %-11s %-28s %s\n" "--------" "----------------------" "-----------" "----------------------------" "-------"

for track in "${TRACK_FILES[@]}"; do
  job_id="$(awk -F= '$1=="job_id"{print $2; exit}' "$track")"
  run_dir="$(awk -F= '$1=="run_dir"{print $2; exit}' "$track")"
  run_label="$(basename "${run_dir:-$(dirname "$track")}")"

  output="$(./tools/ai_codex_status.sh "$track" 2>&1 || true)"
  status_line="$(grep -m1 "^- $job_id" <<<"$output" || true)"
  status="$(awk -F'|' '{gsub(/^ +| +$/, "", $2); print $2}' <<<"$status_line")"
  phase="$(awk -F'Phase: ' '/  Phase:/{print $2; exit}' <<<"$output")"
  summary="$(awk -F'Summary: ' '/  Summary:/{print $2; exit}' <<<"$output")"

  if [[ -z "$status" ]]; then
    status="missing"
    phase="-"
    summary="$(head -1 <<<"$output")"
  fi
  case "$status" in
    completed) state="DONE" ;;
    running|queued) state="ACTIVE" ;;
    failed|cancelled) state="BAD" ;;
    *) state="CHECK" ;;
  esac

  printf "%-8s %-22s %-11s %-28s %.100s\n" \
    "$state" "$job_id" "${phase:-?}" "$run_label" "${summary:-}"
done

echo
echo "Details: ./tools/ai_codex_status.sh <job_id>"
echo "Result:  ./tools/ai_codex_status.sh --result <job_id>"
