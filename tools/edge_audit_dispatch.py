"""Render a Codex queue task file for one strategy edge audit (W4-EDA Task 3).

Reads `_PROMPT_TEMPLATE.md`, substitutes 8 placeholders, writes to
`<queue_dir>/<task_id>.md`. Single strategy only — caller is expected to
invoke this once per strategy in serial order.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


PLACEHOLDERS = (
    "TASK_ID",
    "STRATEGY",
    "STRATEGY_PATH",
    "TIER",
    "SOURCE_TIER",
    "PAIRS",
    "HISTORICAL_METRICS_JSON",
    "CREATED_AT",
)


def _build_task_id(strategy: str, created_at: str) -> str:
    """`<YYYYMMDDTHHMM>-w4-eda-<strategy>` (no separators in timestamp)."""
    digits = re.sub(r"[^0-9]", "", created_at)[:12]  # YYYYMMDDHHMM
    if len(digits) < 12:
        digits = digits.ljust(12, "0")
    return f"{digits[:8]}T{digits[8:12]}-w4-eda-{strategy}"


RENDER_MARKER = "<!-- W4EDA-RENDER-BEGIN -->"


def dispatch(
    *,
    strategy: str,
    strategy_path: str,
    tier: str,
    source_tier: str,
    pairs: str,
    metrics_json: str,
    template_path: Path,
    queue_dir: Path,
    created_at: str,
) -> Path:
    template = template_path.read_text()
    if RENDER_MARKER in template:
        template = template.split(RENDER_MARKER, 1)[1].lstrip()
    task_id = _build_task_id(strategy, created_at)
    substitutions = {
        "TASK_ID": task_id,
        "STRATEGY": strategy,
        "STRATEGY_PATH": strategy_path,
        "TIER": tier,
        "SOURCE_TIER": source_tier,
        "PAIRS": pairs,
        "HISTORICAL_METRICS_JSON": metrics_json,
        "CREATED_AT": created_at,
    }
    body = template
    for key in PLACEHOLDERS:
        body = body.replace("{{" + key + "}}", substitutions[key])

    queue_dir.mkdir(parents=True, exist_ok=True)
    out = queue_dir / f"{task_id}.md"
    out.write_text(body)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", required=True)
    p.add_argument("--strategy-path", required=True)
    p.add_argument("--tier", required=True)
    p.add_argument("--source-tier", required=True)
    p.add_argument("--pairs", required=True)
    p.add_argument("--metrics", required=True, help="JSON string")
    p.add_argument("--template", required=True, type=Path)
    p.add_argument("--queue-dir", required=True, type=Path)
    p.add_argument(
        "--created-at",
        default=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    args = p.parse_args()
    out = dispatch(
        strategy=args.strategy,
        strategy_path=args.strategy_path,
        tier=args.tier,
        source_tier=args.source_tier,
        pairs=args.pairs,
        metrics_json=args.metrics,
        template_path=args.template,
        queue_dir=args.queue_dir,
        created_at=args.created_at,
    )
    print(out)


if __name__ == "__main__":
    main()
