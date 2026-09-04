#!/usr/bin/env python3
"""
Tier A integration: quant gate status + α budget を一枚のMarkdownで出力。

Protocol: knowledge-base/wiki/analyses/daily-tierB-protocol.md §2 (Tier A)

使用:
    python3 tools/quant_gate_status.py                     # Markdown出力
    python3 tools/quant_gate_status.py --json              # JSON出力
    python3 tools/quant_gate_status.py --to-discord        # Discord送信

daily_report.py の直接編集を避け、独立CLIとして提供。
cron で daily_report.py の直後に実行、結果は別メッセージとしてDiscord送信する想定。

統合する情報:
    1. tools/quant_readiness.py の gate status (既存)
    2. tools/alpha_budget_tracker.py の α予算残 (新規)
    3. candidates/shadow_queue.jsonl の直近7日 pass/shadow 集計 (新規)
    4. M1 KPI (clean live 30d PnL) の読み出し (2026-09-04 追加)

⚠️ send_discord() は 1900 字で切り詰める。**M1 は最重要 KPI なので必ず先頭**に
置くこと — 末尾に置くと読み手を足したのに誰にも届かない (write-only の再来)。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.alpha_budget_tracker import load_state, status_summary  # noqa: E402
from tools import m1_clean_live_monitor as m1  # noqa: E402


def run_quant_readiness() -> str:
    """既存 tools/quant_readiness.py を subprocess で呼び出し。"""
    try:
        r = subprocess.run(
            ["python3", str(ROOT / "tools" / "quant_readiness.py")],
            capture_output=True, text=True, timeout=60,
        )
        return r.stdout or r.stderr or "(no output)"
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return f"(quant_readiness.py error: {e})"


def summarize_candidate_queue(days: int = 7) -> dict[str, Any]:
    path = ROOT / "knowledge-base" / "raw" / "candidates" / "shadow_queue.jsonl"
    if not path.exists():
        return {"total": 0, "pass": 0, "shadow_only": 0, "recent_names": []}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    total = 0
    passed = 0
    shadow = 0
    names: list[str] = []
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("date", "") < cutoff:
            continue
        total += 1
        if e.get("tag") == "pass":
            passed += 1
            n = e.get("hypothesis", {}).get("name")
            if n and n not in names:
                names.append(n)
        else:
            shadow += 1
    return {"total": total, "pass": passed, "shadow_only": shadow, "recent_names": names[:10]}


def run_prereg_trigger_watch() -> str:
    """tools/prereg_trigger_watch.py の Markdown を subprocess で取得。

    pre-reg トリガーの監視主体 (2026-07-06 導入 — T5 の 18 日執行ギャップ再発防止)。
    失敗しても daily レポート全体は落とさない。
    """
    try:
        r = subprocess.run(
            ["python3", str(ROOT / "tools" / "prereg_trigger_watch.py")],
            capture_output=True, text=True, timeout=90,
        )
        return r.stdout or r.stderr or "(no output)"
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return f"(prereg_trigger_watch.py error: {e})"


def run_m1_readout() -> dict[str, Any]:
    """M1 KPI (clean live 30d PnL) を読み出す。

    roadmap v2.3 の最重要 KPI だが 2026-09-04 まで再計算する主体が無く、
    roadmap の M1 行は 2026-07-06 の手動実測のまま 60 日凍結されていた
    (その間に符号が反転していた)。失敗しても daily レポート全体は落とさない。
    """
    try:
        return m1.build_report()
    except Exception as e:  # noqa: BLE001 - 日次レポートを落とさないための境界
        return {"error": f"{type(e).__name__}: {e}"}


def build_report() -> dict[str, Any]:
    alpha = load_state()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "m1_readout": run_m1_readout(),
        "quant_readiness": run_quant_readiness(),
        "alpha_budget": alpha,
        "candidate_queue_7d": summarize_candidate_queue(7),
        "prereg_trigger_watch": run_prereg_trigger_watch(),
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = ["# Quant Gate Status"]
    lines.append(f"_Generated: {report['generated_at']}_")
    lines.append("")
    # M1 は最重要 KPI かつ Discord 側で 1900 字に切られるので先頭に固定する。
    m1_report = report.get("m1_readout") or {}
    if m1_report.get("error"):
        lines.append("## M1 KPI (clean live 30d PnL)")
        lines.append(f"- ⚠️ 読み出し失敗: {m1_report['error']}")
    else:
        lines.append(m1.to_markdown(m1_report))
    lines.append("")
    lines.append("## Readiness")
    lines.append("```")
    lines.append(report["quant_readiness"].strip())
    lines.append("```")
    lines.append("")
    lines.append(status_summary(report["alpha_budget"]))
    lines.append("")
    lines.append("## Candidate Queue (last 7d)")
    q = report["candidate_queue_7d"]
    lines.append(f"- total entries: {q['total']}")
    lines.append(f"- pass: {q['pass']}")
    lines.append(f"- shadow_only: {q['shadow_only']}")
    if q["recent_names"]:
        lines.append(f"- recent pass names: {', '.join(q['recent_names'])}")
    lines.append("")
    lines.append(report.get("prereg_trigger_watch", "").strip())
    return "\n".join(lines)


def send_discord(text: str) -> None:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        print("DISCORD_WEBHOOK_URL not set; skipping", file=sys.stderr)
        return
    try:
        resp = requests.post(webhook, json={"content": text[:1900]}, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠️  Discord notify failed: {e}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--to-discord", action="store_true")
    args = parser.parse_args()

    report = build_report()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        md = to_markdown(report)
        print(md)
        if args.to_discord:
            send_discord(md)

    return 0


if __name__ == "__main__":
    sys.exit(main())
