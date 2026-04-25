#!/usr/bin/env python3
"""
EDGE.md Export — convert EDGE.md manifest to runtime routing_table.json.

Usage:
    python3 tools/edge_md_export.py                       # write modules/routing_table.json
    python3 tools/edge_md_export.py --stdout              # print JSON to stdout
    python3 tools/edge_md_export.py --check               # exit 1 if EDGE.md fails lint

The output schema is consumed by modules/cell_routing.py at runtime.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
sys.path.insert(0, str(_PROJECT_ROOT))

from tools.edge_md_lint import _extract_yaml_block, _yaml_load, lint  # noqa: E402

EDGE_MD = _PROJECT_ROOT / "knowledge-base" / "wiki" / "manifests" / "EDGE.md"
OUTPUT = _PROJECT_ROOT / "modules" / "routing_table.json"


def build_routing(edges: list) -> dict:
    """Project edges -> {block, kelly_half, kelly_full} keyed by (strategy, cell)."""
    block, kh, kf = [], [], []
    for e in edges:
        rt = e.get("routing")
        s, c = e.get("strategy"), e.get("cell")
        if not s or not c:
            continue
        pair = [s, c]
        if rt == "BLOCK":
            block.append(pair)
        elif rt == "KELLY_HALF":
            kh.append(pair + [e.get("routing_lot_multiplier", 0.5)])
        elif rt == "KELLY_FULL":
            kf.append(pair + [e.get("routing_lot_multiplier", 1.0)])
    return {
        "block": block,
        "kelly_half": kh,
        "kelly_full": kf,
    }


def export(path: Path) -> dict:
    text = path.read_text()
    yaml_text = _extract_yaml_block(text)
    data = _yaml_load(yaml_text) or {}
    edges = data.get("edges", []) or []

    routing = build_routing(edges)
    return {
        "version": data.get("version", "0.1"),
        "classifier": data.get("classifier", "v6"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(path.relative_to(_PROJECT_ROOT)),
        "edges_count": len(edges),
        **routing,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default=str(EDGE_MD))
    ap.add_argument("--stdout", action="store_true",
                    help="Print to stdout instead of writing routing_table.json")
    ap.add_argument("--check", action="store_true",
                    help="Lint EDGE.md before export; exit 1 on errors")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"error: {path} not found", file=sys.stderr)
        return 1

    if args.check:
        report = lint(path)
        if report["summary"]["errors"] > 0:
            for f in report["findings"]:
                if f["severity"] == "error":
                    print(f"  [ERROR] {f.get('rule','?')}: {f['message']}", file=sys.stderr)
            return 1

    result = export(path)
    text = json.dumps(result, indent=2)

    if args.stdout:
        print(text)
    else:
        OUTPUT.write_text(text + "\n")
        print(f"wrote {OUTPUT.relative_to(_PROJECT_ROOT)} "
              f"(edges={result['edges_count']}, "
              f"block={len(result['block'])}, "
              f"kelly_half={len(result['kelly_half'])}, "
              f"kelly_full={len(result['kelly_full'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
