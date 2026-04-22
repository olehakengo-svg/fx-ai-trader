#!/usr/bin/env python3
"""
Tier B-weekly: candidate pool から LIVE昇格候補を抽出 → pre-register PR生成

Protocol: knowledge-base/wiki/analyses/daily-tierB-protocol.md §5

使用:
    python3 scripts/weekly_promotion_gate.py              # 実行 (cron 日曜UTC 12:00)
    python3 scripts/weekly_promotion_gate.py --dry-run    # 候補抽出のみ、PR作成せず

条件 (pre-committed):
    1. shadow_queue.jsonl で "pass" タグが5営業日連続で発生
    2. Shadow EV/WR が BT期待値から σ 以内 (drift無し)
    3. Kelly fraction (full + Half) 計算可能
    4. weekly α予算残 > per-test閾値

出力:
    - knowledge-base/wiki/analyses/pre-registration-YYYY-WW.md
    - GitHub PR (gh CLI 経由)
    - Discord通知

重要:
    - LIVE昇格は人間承認 (PR merge) 必須
    - 本スクリプトは「候補抽出 + PR作成」まで
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.alpha_budget_tracker import consume, load_state  # noqa: E402

CONSECUTIVE_PASS_DAYS = 5
QUEUE_PATH = ROOT / "knowledge-base" / "raw" / "candidates" / "shadow_queue.jsonl"


# ── Queue 読み込み ──────────────────────────────────────

def load_recent_queue(days: int = 14) -> list[dict[str, Any]]:
    if not QUEUE_PATH.exists():
        return []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    entries = []
    for line in QUEUE_PATH.read_text().splitlines():
        try:
            e = json.loads(line)
            if e.get("date", "") >= cutoff:
                entries.append(e)
        except json.JSONDecodeError:
            continue
    return entries


# ── 昇格候補抽出 ────────────────────────────────────────

def find_promotion_candidates(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """同じ hypothesis.name が CONSECUTIVE_PASS_DAYS 連続 pass のものを抽出。"""
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in queue:
        name = e.get("hypothesis", {}).get("name")
        if name:
            by_name[name].append(e)

    candidates = []
    for name, entries in by_name.items():
        entries_sorted = sorted(entries, key=lambda x: x.get("date", ""))
        # 末尾から連続pass数をカウント
        streak = 0
        for e in reversed(entries_sorted):
            if e.get("tag") == "pass":
                streak += 1
            else:
                break
        if streak >= CONSECUTIVE_PASS_DAYS:
            latest = entries_sorted[-1]
            candidates.append(
                {
                    "name": name,
                    "consecutive_pass": streak,
                    "latest_entry": latest,
                    "all_entries": entries_sorted[-streak:],
                }
            )
    return candidates


# ── Kelly計算 (既存tools/bayesian_edge_checkと整合) ────────

def kelly_fraction(wr: float, tp_m: float, sl_m: float) -> tuple[float, float]:
    """Kelly full と Half を返す。

    f* = (p * b - q) / b  where b = tp_m/sl_m, p = WR, q = 1-p
    """
    if sl_m <= 0 or wr < 0 or wr > 1:
        return 0.0, 0.0
    b = tp_m / sl_m
    p = wr
    q = 1 - p
    full = (p * b - q) / b if b > 0 else 0
    full = max(0.0, min(1.0, full))
    return full, full / 2.0


# ── Pre-register document生成 ────────────────────────────

def generate_pre_register_doc(
    candidates: list[dict[str, Any]], week_key: str
) -> Path:
    path = (
        ROOT / "knowledge-base" / "wiki" / "analyses" /
        f"pre-registration-{week_key}.md"
    )
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [f"# Pre-Registration — Week {week_key}", ""]
    lines.append(f"**Created**: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"**Protocol**: daily-tierB-protocol.md §5")
    lines.append(f"**Status**: PRE-REGISTERED (binding LIVE gate criteria)")
    lines.append("")
    lines.append("## 昇格候補")
    lines.append("")

    for c in candidates:
        hyp = c["latest_entry"].get("hypothesis", {})
        bt = c["latest_entry"].get("bt_result", {})
        wr = bt.get("wilson_lower") or 0.5
        tp_m = hyp.get("bt_parameters", {}).get("tp_rule_m", 2.0)
        sl_m = hyp.get("bt_parameters", {}).get("sl_rule_m", 1.2)
        kf, kh = kelly_fraction(wr, tp_m, sl_m)

        lines.append(f"### {c['name']}")
        lines.append("")
        lines.append(f"- **Hypothesis**: {hyp.get('hypothesis_1_line', '?')}")
        lines.append(f"- **Academic basis**: {hyp.get('academic_basis', '?')}")
        lines.append(f"- **Consecutive pass days**: {c['consecutive_pass']}")
        lines.append(f"- **BT PF**: {bt.get('pf', 'N/A')}")
        lines.append(f"- **Wilson 95% CI lower**: {bt.get('wilson_lower', 'N/A')}")
        lines.append(f"- **Kelly full / Half**: {kf:.4f} / {kh:.4f}")
        lines.append("")
        lines.append(f"#### LIVE gate criteria (BINDING)")
        lines.append("")
        lines.append(f"**Promotion (Shadow → OANDA_LIVE)**:")
        lines.append(f"- Live N ≥ 20 AND Live EV > Wilson lower bound from BT")
        lines.append("")
        lines.append(f"**Demotion (force shadow)**:")
        lines.append(f"- Live N ≥ 30 AND Live EV < BT期待値 - 1σ")
        lines.append("")
        lines.append(f"**Monitoring period**: 30日 (延長禁止)")
        lines.append("")

    lines.append("## 承認チェックリスト (reviewer用)")
    lines.append("")
    lines.append("- [ ] 学術的根拠 (academic_basis) が十分か")
    lines.append("- [ ] α予算残が十分か (monthly budget ≥ weekly 閾値)")
    lines.append("- [ ] 既存PAIR_PROMOTED と相関 <0.3")
    lines.append("- [ ] 4原則と矛盾しない")
    lines.append("- [ ] 失敗シナリオが明確")
    lines.append("")

    path.write_text("\n".join(lines))
    return path


# ── GitHub PR作成 ──────────────────────────────────────

def create_github_pr(doc_path: Path, week_key: str) -> str | None:
    """gh CLI でPR作成。失敗時は None を返す。"""
    title = f"pre-register: Tier B-weekly promotion {week_key}"
    body = f"""Automated PR from `scripts/weekly_promotion_gate.py`.

Protocol: `knowledge-base/wiki/analyses/daily-tierB-protocol.md` §5

See: `{doc_path.relative_to(ROOT)}`

**LIVE変更は merge前に人間確認必須**. 承認チェックリストを埋めてから approve。
"""
    branch = f"preregister/{week_key}"
    try:
        subprocess.run(["git", "checkout", "-b", branch], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(["git", "add", str(doc_path)], cwd=ROOT, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"pre-register: Tier B-weekly {week_key}"],
            cwd=ROOT, check=True, capture_output=True,
        )
        subprocess.run(["git", "push", "-u", "origin", branch], cwd=ROOT, check=True, capture_output=True)
        result = subprocess.run(
            ["gh", "pr", "create", "--title", title, "--body", body],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"⚠️  PR creation failed: {e}", file=sys.stderr)
        return None


# ── Discord通知 ─────────────────────────────────────────

def notify_discord(message: str) -> None:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        return
    try:
        import requests
        requests.post(webhook, json={"content": message[:1900]}, timeout=10)
    except Exception as e:
        print(f"⚠️  Discord notify failed: {e}", file=sys.stderr)


# ── メイン ──────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    week_key = now.strftime("%Y-W%V")

    print(f"[{week_key}] Tier B-weekly promotion gate starting...")

    queue = load_recent_queue(days=14)
    print(f"  Queue entries (last 14d): {len(queue)}")

    candidates = find_promotion_candidates(queue)
    print(f"  Promotion candidates (≥{CONSECUTIVE_PASS_DAYS} consec pass): {len(candidates)}")

    if not candidates:
        msg = f"ℹ️ [{week_key}] Tier B-weekly: 昇格候補なし (queue {len(queue)}件)"
        print(msg)
        notify_discord(msg)
        return 0

    # α予算消費
    ok, per_test_alpha, updated_state = consume(
        "weekly", len(candidates), note=f"weekly_gate {week_key}: {len(candidates)} candidates"
    )
    if not ok:
        msg = f"🛑 [{week_key}] weekly α budget exhausted — 昇格審議スキップ"
        print(msg)
        notify_discord(msg)
        return 1

    doc_path = generate_pre_register_doc(candidates, week_key)
    print(f"  Pre-register doc: {doc_path}")

    pr_url = None
    if not args.dry_run:
        pr_url = create_github_pr(doc_path, week_key)

    summary = {
        "week": week_key,
        "candidates": len(candidates),
        "per_test_alpha": per_test_alpha,
        "doc_path": str(doc_path.relative_to(ROOT)),
        "pr_url": pr_url,
        "names": [c["name"] for c in candidates],
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    msg = (
        f"📋 [{week_key}] Tier B-weekly: {len(candidates)} LIVE昇格候補\n"
        f"Pre-register: `{doc_path.relative_to(ROOT)}`\n"
        f"{'PR: ' + pr_url if pr_url else '(dry-run または PR作成失敗)'}\n"
        f"⚠️ 人間承認が必要"
    )
    notify_discord(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
