#!/usr/bin/env python3
"""Sanity checks for W6-MR-Cross Wave 1 JSON reports."""
from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_CELL_KEYS = {
    "cell",
    "pair",
    "window",
    "status",
    "N",
    "WR",
    "EV",
    "PF",
    "wilson_lower",
    "bonferroni_p",
    "wf_ev_positive_folds",
    "wf_wr_above_half_folds",
    "verdict",
}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: tools/sanity_check_bt_report.py REPORT.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    cells = data.get("cells")
    if not isinstance(cells, list) or len(cells) != 10:
        print("FAIL: expected 10 cells", file=sys.stderr)
        return 1
    for cell in cells:
        missing = REQUIRED_CELL_KEYS - set(cell)
        if missing:
            print(f"FAIL: {cell.get('cell')} missing {sorted(missing)}", file=sys.stderr)
            return 1
    if data.get("wave1_verdict") not in {"Wave 2 GO", "NEEDS_MORE_EVIDENCE", "REJECT", "BLOCKED_PRECONDITION"}:
        print("FAIL: invalid wave1_verdict", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
