#!/usr/bin/env python3
"""
Alpha Budget Tracker — 月間α=0.05のfamily-wise error rate制御

Usage:
    python3 tools/alpha_budget_tracker.py                  # 現在の月次状態表示
    python3 tools/alpha_budget_tracker.py --consume daily 5 # dailyカテゴリで5テスト消費
    python3 tools/alpha_budget_tracker.py --reset          # 新月reset (cron 月初実行)
    python3 tools/alpha_budget_tracker.py --json           # machine-readable

Prococol: knowledge-base/wiki/analyses/daily-tierB-protocol.md §3

月間予算 (pre-committed):
    daily    = 0.020  (Tier B-daily 探索用)
    weekly   = 0.020  (Tier B-weekly 審議用)
    anomaly  = 0.005  (Tier C 異常起因の臨時仮説)
    reserve  = 0.005  (ユーザー指名の仮説)
    total    = 0.050

State file: knowledge-base/raw/alpha_budget/YYYY-MM.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BUDGET_DIR = ROOT / "knowledge-base" / "raw" / "alpha_budget"

MONTHLY_BUDGET = {
    "daily": 0.020,
    "weekly": 0.020,
    "anomaly": 0.005,
    "reserve": 0.005,
}

CATEGORIES = tuple(MONTHLY_BUDGET.keys())


def _current_month_key(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def _state_path(month_key: str) -> Path:
    return BUDGET_DIR / f"{month_key}.json"


def _empty_state(month_key: str) -> dict[str, Any]:
    return {
        "month": month_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "budget": dict(MONTHLY_BUDGET),
        "consumed": {k: 0.0 for k in CATEGORIES},
        "events": [],
    }


def load_state(month_key: str | None = None) -> dict[str, Any]:
    month_key = month_key or _current_month_key()
    path = _state_path(month_key)
    if not path.exists():
        BUDGET_DIR.mkdir(parents=True, exist_ok=True)
        state = _empty_state(month_key)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return state
    return json.loads(path.read_text())


def save_state(state: dict[str, Any]) -> None:
    path = _state_path(state["month"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def compute_per_test_alpha(
    category: str,
    num_tests: int,
    days_remaining_in_month: int | None = None,
    state: dict[str, Any] | None = None,
) -> tuple[float, float]:
    """Per-test α (Bonferroni) と current remaining を返す。消費はしない。

    per-test α 計算ロジック:
        daily予算は月内の残り日数で等分配してから num_tests で分割。
        これにより月末に近づくほど per-test α が大きくなる (予算余り回避)。

    Returns:
        (per_test_alpha, category_remaining)
    """
    if category not in CATEGORIES:
        raise ValueError(f"unknown category: {category}")
    if num_tests <= 0:
        return 0.0, 0.0

    state = state or load_state()
    remaining = state["budget"][category] - state["consumed"][category]
    if remaining <= 0:
        return 0.0, remaining

    if category == "daily" and days_remaining_in_month is None:
        now = datetime.now(timezone.utc)
        from calendar import monthrange
        last_day = monthrange(now.year, now.month)[1]
        days_remaining_in_month = max(1, last_day - now.day + 1)

    daily_slice = (
        remaining / days_remaining_in_month
        if category == "daily" and days_remaining_in_month
        else remaining
    )
    per_test = daily_slice / num_tests if num_tests > 0 else 0.0
    return per_test, remaining


def consume(
    category: str,
    num_tests: int,
    note: str = "",
    num_actual_pass: int | None = None,
    state: dict[str, Any] | None = None,
) -> tuple[bool, float, dict[str, Any]]:
    """カテゴリでα予算を消費。pass数ベースで実消費 (v2)。

    num_actual_pass を指定した場合:
        per_test_alpha × num_actual_pass を消費 (pass-based)
    num_actual_pass=None (後方互換):
        per_test_alpha × num_tests を消費 (worst-case想定)

    Returns:
        (ok, per_test_alpha, updated_state)
        ok=False なら予算不足。
    """
    if num_tests <= 0:
        raise ValueError("num_tests must be positive")

    state = state or load_state()
    per_test, remaining = compute_per_test_alpha(category, num_tests, state=state)

    if per_test <= 0:
        return False, 0.0, state

    pass_count = num_actual_pass if num_actual_pass is not None else num_tests
    if pass_count < 0:
        pass_count = 0
    consumed_delta = per_test * pass_count

    state["consumed"][category] = round(
        state["consumed"][category] + consumed_delta, 6
    )
    state["events"].append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "num_tests": num_tests,
            "num_actual_pass": pass_count,
            "per_test_alpha": per_test,
            "consumed_delta": consumed_delta,
            "note": note[:200],
        }
    )
    save_state(state)
    return True, per_test, state


def reset_monthly(month_key: str | None = None) -> dict[str, Any]:
    """月次reset。既存stateは archive として保存、新月空stateを作成。

    cron 月初 UTC 00:00 で実行想定。
    """
    month_key = month_key or _current_month_key()
    path = _state_path(month_key)
    if path.exists():
        archive = BUDGET_DIR / "archive" / f"{month_key}.json"
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_text(path.read_text())
    state = _empty_state(month_key)
    save_state(state)
    return state


def status_summary(state: dict[str, Any]) -> str:
    lines = [f"# Alpha Budget — {state['month']}"]
    lines.append("")
    lines.append("| Category | Budget | Consumed | Remaining | Pct |")
    lines.append("|---|---|---|---|---|")
    for cat in CATEGORIES:
        b = state["budget"][cat]
        c = state["consumed"][cat]
        r = b - c
        pct = (c / b * 100) if b > 0 else 0
        lines.append(f"| {cat} | {b:.4f} | {c:.4f} | {r:.4f} | {pct:.1f}% |")
    total_b = sum(state["budget"].values())
    total_c = sum(state["consumed"].values())
    lines.append(
        f"| **total** | **{total_b:.4f}** | **{total_c:.4f}** | "
        f"**{total_b - total_c:.4f}** | **{total_c / total_b * 100:.1f}%** |"
    )
    lines.append("")
    lines.append(f"Events: {len(state['events'])}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", help="YYYY-MM (default: current UTC)")
    parser.add_argument(
        "--consume",
        nargs=2,
        metavar=("CATEGORY", "NUM_TESTS"),
        help="Consume alpha budget. e.g. --consume daily 5",
    )
    parser.add_argument("--note", default="", help="Note for consume event")
    parser.add_argument("--reset", action="store_true", help="Reset monthly state")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.reset:
        state = reset_monthly(args.month)
        print(f"Reset {state['month']}")
        return 0

    if args.consume:
        cat, n_str = args.consume
        try:
            n = int(n_str)
        except ValueError:
            print(f"NUM_TESTS must be integer, got {n_str!r}", file=sys.stderr)
            return 2
        ok, per_test, state = consume(cat, n, note=args.note)
        if args.json:
            print(json.dumps({"ok": ok, "per_test_alpha": per_test}, indent=2))
        else:
            if ok:
                print(
                    f"Consumed {cat}: {n} tests, per-test α = {per_test:.6f}"
                )
            else:
                print(f"BUDGET EXHAUSTED for {cat}", file=sys.stderr)
        return 0 if ok else 1

    state = load_state(args.month)
    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
    else:
        print(status_summary(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
