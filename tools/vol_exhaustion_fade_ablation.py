#!/usr/bin/env python3
"""Family A vs current v_reversal ablation entry point."""
from __future__ import annotations

import sys

from tools.vol_exhaustion_fade_bt import main


if __name__ == "__main__":
    # The default runner mode is already Family A + Family B and writes
    # reports/vol_exhaustion_fade_bt/ablation.md.
    raise SystemExit(main())
