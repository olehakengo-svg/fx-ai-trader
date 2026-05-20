from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_demo_trader_pep604_is_py39_safe() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "tools/check_no_pep604_until_py310.py",
            "modules/demo_trader.py",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
