#!/usr/bin/env python3
"""
Tier B-daily: 仮説生成 → 365d BT 自動検証 → candidate queue への追加

Protocol: knowledge-base/wiki/analyses/daily-tierB-protocol.md §4

使用:
    python3 scripts/daily_hypothesis_scan.py              # 実行 (cron 想定)
    python3 scripts/daily_hypothesis_scan.py --dry-run    # Claude呼び出しまで、BTスキップ
    python3 scripts/daily_hypothesis_scan.py --force      # α予算消費上限を無視 (手動実行用)

環境変数:
    ANTHROPIC_API_KEY        (必須)
    DISCORD_WEBHOOK_URL      (optional: 結果通知)
    API_BASE=https://fx-ai-trader.onrender.com

パイプライン (UTC 00:30 cron 想定):
    1. 本番APIから前日Live trade + shadow pool + anomaly event 取得
    2. hypothesis-generator エージェント呼び出し → 仮説JSON
    3. α予算消費可否チェック (alpha_budget_tracker)
    4. 各仮説を 365d BT + WF 3-bucket で検証
    5. Gate判定 (PF>1.3, Wilson下限>BEV, WF全正, N>=30, Bonferroni p<α_daily)
    6. Pass候補 → knowledge-base/raw/candidates/shadow_queue.jsonl 追加
    7. Fail候補 → shadow_queue.jsonl に "shadow_only" タグで追加
    8. Discord通知 + KB要約 (candidates/YYYY-MM-DD.md)

重要:
    - LIVE変更しない (shadow queue 追加のみ)
    - α予算尽きたらpre-registerスキップ、shadow観察のみ継続
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.bev_table import bev_wr  # noqa: E402
from modules.claude_client import call_agent_json  # noqa: E402
from tools.alpha_budget_tracker import (  # noqa: E402
    compute_per_test_alpha,
    consume,
    load_state,
)

API_BASE = os.environ.get("API_BASE", "https://fx-ai-trader.onrender.com")
FIDELITY_CUTOFF = "2026-04-16T08:00:00"
MAX_HYPOTHESES_PER_DAY = 10

# Gate thresholds (pre-committed)
GATE_PF_MIN = 1.3
GATE_N_MIN = 30
GATE_WF_BUCKETS = 3


# ── データ取得 ────────────────────────────────────────────

def fetch_json(path: str, timeout: int = 30) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"⚠️  fetch failed: {url} — {e}", file=sys.stderr)
        return {}


def fetch_context() -> dict[str, Any]:
    """Claudeに渡す集約データを構築。生JSONは渡さない (lesson-raw-json-to-llm)。"""
    trades_raw = fetch_json("/api/demo/trades?limit=500")
    trades = trades_raw.get("trades", []) if isinstance(trades_raw, dict) else []
    trades = [t for t in trades if (t.get("exit_time", "") or "") >= FIDELITY_CUTOFF]
    trades = [t for t in trades if "XAU" not in (t.get("instrument") or "")]

    from collections import defaultdict
    sp = defaultdict(lambda: {"n": 0, "wins": 0, "pnl": 0.0, "shadow_n": 0})
    for t in trades:
        key = (t.get("entry_type", "?"), t.get("instrument", "?"))
        is_shadow = bool(t.get("is_shadow", False))
        s = sp[key]
        if is_shadow:
            s["shadow_n"] += 1
        else:
            s["n"] += 1
            if t.get("outcome") == "WIN":
                s["wins"] += 1
            s["pnl"] += float(t.get("pnl_pips", 0) or 0)

    live_summary = []
    for (strat, pair), s in sorted(sp.items(), key=lambda x: -x[1]["n"]):
        if s["n"] < 3 and s["shadow_n"] < 5:
            continue
        wr = (s["wins"] / s["n"] * 100) if s["n"] > 0 else 0
        ev = s["pnl"] / s["n"] if s["n"] > 0 else 0
        live_summary.append(
            f"- {strat} × {pair}: Live N={s['n']} WR={wr:.1f}% EV={ev:+.2f} | Shadow N={s['shadow_n']}"
        )

    alpha_state = load_state()

    anomalies_file = ROOT / "knowledge-base" / "raw" / "anomalies" / (
        datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".jsonl"
    )
    anomalies = []
    if anomalies_file.exists():
        for line in anomalies_file.read_text().splitlines()[-20:]:
            try:
                anomalies.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    tier_master_path = ROOT / "knowledge-base" / "wiki" / "tier-master.md"
    tier_master = (
        tier_master_path.read_text(encoding="utf-8")[:3000]
        if tier_master_path.exists() else "(tier-master.md not found)"
    )

    return {
        "live_summary": "\n".join(live_summary) or "(no trades)",
        "alpha_budget": alpha_state,
        "anomalies_last_24h": anomalies,
        "tier_master_excerpt": tier_master,
        "trades_count": len(trades),
    }


# ── BT実行ブリッジ ────────────────────────────────────────

def run_bt_for_hypothesis(hyp: dict[str, Any]) -> dict[str, Any]:
    """仮説の bt_parameters を使って 365d BT + WF 3-bucket を実行。

    **注意**: 現時点では skeleton 実装。完全実装は strategy file 生成が必要で、
    それは次フェーズ (`scripts/agents/strategy-dev.md` 委譲) で実装する。
    このMVPでは既存 tools/bt_365d_runner.py を呼び出す wrapper を返す。

    TODO Phase 2:
    - 仮説 → 一時 strategy file 生成 (strategy-dev agent)
    - BT実行
    - WF bucket split (前/中/後 の 1/3ずつ)
    - PF, Wilson CI, Bonferroni p値計算
    """
    return {
        "hypothesis_id": hyp["id"],
        "bt_executed": False,
        "reason": "skeleton: BT bridge pending Phase 2 implementation",
        "pf": None,
        "wilson_lower": None,
        "wf_buckets": [],
        "n_per_bucket": [],
    }


# ── Gate判定 ────────────────────────────────────────────

def evaluate_gate(
    bt_result: dict[str, Any],
    per_test_alpha: float,
    hypothesis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """5条件ANDで pass/fail 判定。hypothesisから pair×mode BEV を lookup。"""
    if not bt_result.get("bt_executed"):
        return {
            "pass": False,
            "reason": bt_result.get("reason", "bt_not_executed"),
        }

    pf = bt_result.get("pf")
    wl = bt_result.get("wilson_lower")
    wf = bt_result.get("wf_buckets", [])
    n_per_bucket = bt_result.get("n_per_bucket", [])

    bev = 0.42
    if hypothesis:
        bt_params = hypothesis.get("bt_parameters", {})
        insts = bt_params.get("target_instruments", [])
        mode = "scalp" if "scalp" in hypothesis.get("name", "").lower() else "daytrade"
        if insts:
            bev = max(bev_wr(i, mode) for i in insts)  # 最保守

    checks = {
        "pf_gt_1_3": (pf or 0) > GATE_PF_MIN,
        "wilson_gt_bev": (wl or 0) > bev,
        "wf_all_positive": all(x > 0 for x in wf) if wf else False,
        "n_per_bucket_ge_30": all(n >= GATE_N_MIN for n in n_per_bucket) if n_per_bucket else False,
        "p_lt_bonferroni_alpha": bt_result.get("p_value", 1.0) < per_test_alpha,
    }
    all_pass = all(checks.values())
    return {"pass": all_pass, "bev_used": bev, "checks": checks}


# ── Candidate queue 管理 ─────────────────────────────────

def append_to_shadow_queue(entry: dict[str, Any]) -> None:
    path = ROOT / "knowledge-base" / "raw" / "candidates" / "shadow_queue.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_daily_summary(date_str: str, result: dict[str, Any]) -> Path:
    md_dir = ROOT / "knowledge-base" / "wiki" / "analyses" / "candidates"
    md_dir.mkdir(parents=True, exist_ok=True)
    path = md_dir / f"{date_str}.md"

    lines = [f"# Daily Hypothesis Scan — {date_str}", ""]
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Pipeline: Tier B-daily (daily-tierB-protocol.md §4)")
    lines.append("")
    lines.append(f"## α Budget")
    ab = result.get("alpha_state", {})
    daily_consumed = ab.get("consumed", {}).get("daily", 0)
    daily_budget = ab.get("budget", {}).get("daily", 0.02)
    lines.append(f"- daily category: consumed {daily_consumed:.4f} / {daily_budget:.4f}")
    lines.append(f"- per-test α (today): {result.get('per_test_alpha', 0):.6f}")
    lines.append("")
    lines.append(f"## Hypotheses")
    lines.append(f"- Generated: {result.get('num_hypotheses', 0)}")
    lines.append(f"- Pass: {result.get('num_pass', 0)}")
    lines.append(f"- Shadow-only: {result.get('num_shadow', 0)}")
    lines.append("")

    for h in result.get("hypotheses_detail", []):
        gate = h.get("gate", {})
        status = "✅ PASS" if gate.get("pass") else "🔸 SHADOW"
        lines.append(f"### {h['id']}: {h.get('name', '?')} — {status}")
        lines.append(f"- edge_type: {h.get('edge_type', '?')}")
        lines.append(f"- hypothesis: {h.get('hypothesis_1_line', '?')}")
        lines.append(f"- targets: {h.get('bt_parameters', {}).get('target_instruments', [])}")
        if not gate.get("pass"):
            lines.append(f"- reason: {gate.get('reason', gate.get('checks'))}")
        lines.append("")

    path.write_text("\n".join(lines))
    return path


# ── Discord通知 ─────────────────────────────────────────

def notify_discord(message: str) -> None:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        return
    try:
        requests.post(webhook, json={"content": message[:1900]}, timeout=10)
    except requests.RequestException as e:
        print(f"⚠️  Discord notify failed: {e}", file=sys.stderr)


# ── メイン ──────────────────────────────────────────────

def build_user_message(ctx: dict[str, Any]) -> str:
    return f"""# 前日Liveサマリ

{ctx['live_summary']}

トレード総数 (cutoff後、XAU除外): {ctx['trades_count']}

# α予算残 ({ctx['alpha_budget']['month']})

daily:   {ctx['alpha_budget']['budget']['daily'] - ctx['alpha_budget']['consumed']['daily']:.4f} 残
weekly:  {ctx['alpha_budget']['budget']['weekly'] - ctx['alpha_budget']['consumed']['weekly']:.4f} 残
anomaly: {ctx['alpha_budget']['budget']['anomaly'] - ctx['alpha_budget']['consumed']['anomaly']:.4f} 残

# 直近24h異常イベント

{json.dumps(ctx['anomalies_last_24h'], ensure_ascii=False, indent=2)[:1500] if ctx['anomalies_last_24h'] else '(なし)'}

# Tier Master (抜粋)

{ctx['tier_master_excerpt']}

---

上記を踏まえ、本日の仮説候補 (最大10件) を JSON で出力してください。
α予算残が少ない場合は高確度なもののみ、多い場合は多様性を優先してください。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Claudeまで、BTスキップ")
    parser.add_argument("--force", action="store_true", help="α予算尽きても続行")
    parser.add_argument("--json", action="store_true", help="JSON出力")
    args = parser.parse_args()

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[{date_str}] Tier B-daily hypothesis scan starting...")
    ctx = fetch_context()
    print(f"  Live trades: {ctx['trades_count']}, anomalies: {len(ctx['anomalies_last_24h'])}")

    remaining_daily = (
        ctx["alpha_budget"]["budget"]["daily"]
        - ctx["alpha_budget"]["consumed"]["daily"]
    )
    if remaining_daily <= 0 and not args.force:
        msg = f"🛑 Tier B-daily skipped: daily α budget exhausted ({remaining_daily:.4f})"
        print(msg)
        notify_discord(msg)
        return 0

    user_msg = build_user_message(ctx)

    try:
        hypotheses_json = call_agent_json(
            "hypothesis-generator", user_msg, max_tokens=16000
        )
    except (RuntimeError, ValueError) as e:
        err = f"🛑 hypothesis-generator failed: {e}"
        print(err, file=sys.stderr)
        notify_discord(err)
        return 2

    hypotheses = hypotheses_json.get("hypotheses", [])[:MAX_HYPOTHESES_PER_DAY]
    num_h = len(hypotheses)
    print(f"  Generated {num_h} hypotheses")

    if num_h == 0:
        notify_discord(f"✅ [{date_str}] Tier B-daily: 0 hypotheses generated (no actionable signals)")
        write_daily_summary(date_str, {"num_hypotheses": 0, "alpha_state": ctx["alpha_budget"]})
        return 0

    # per_test_alpha は事前固定 (BT前に確定、post-hoc bias排除)
    per_test_alpha, _ = compute_per_test_alpha("daily", num_h)
    if per_test_alpha <= 0 and not args.force:
        msg = f"🛑 Alpha budget exhausted. Skipping BT stage."
        print(msg)
        notify_discord(msg)
        return 1
    print(f"  per-test α (pre-fixed): {per_test_alpha:.6f}")

    if args.dry_run:
        print("  --dry-run: skipping BT stage, α未消費")
        result = {
            "num_hypotheses": num_h,
            "num_pass": 0,
            "num_shadow": num_h,
            "per_test_alpha": per_test_alpha,
            "alpha_state": load_state(),
            "hypotheses_detail": [
                {**h, "gate": {"pass": False, "reason": "dry_run"}} for h in hypotheses
            ],
        }
    else:
        details = []
        num_pass = 0
        num_shadow = 0
        for h in hypotheses:
            bt_result = run_bt_for_hypothesis(h)
            gate = evaluate_gate(bt_result, per_test_alpha, hypothesis=h)
            tag = "pass" if gate["pass"] else "shadow_only"
            if gate["pass"]:
                num_pass += 1
            else:
                num_shadow += 1
            entry = {
                "date": date_str,
                "hypothesis": h,
                "bt_result": bt_result,
                "gate": gate,
                "tag": tag,
                "per_test_alpha": per_test_alpha,
            }
            append_to_shadow_queue(entry)
            details.append({**h, "bt": bt_result, "gate": gate})

        # α消費: pass数ベース (v2), BT後に確定
        _, _, updated_state = consume(
            "daily",
            num_tests=num_h,
            num_actual_pass=num_pass,
            note=f"daily_scan {date_str}: {num_h} tests, {num_pass} pass",
        )

        result = {
            "num_hypotheses": num_h,
            "num_pass": num_pass,
            "num_shadow": num_shadow,
            "per_test_alpha": per_test_alpha,
            "alpha_state": updated_state,
            "hypotheses_detail": details,
        }

    summary_path = write_daily_summary(date_str, result)
    print(f"  Summary written: {summary_path}")

    alpha_state = result["alpha_state"]
    notify_msg = (
        f"📊 [{date_str}] Tier B-daily: {num_h} hypotheses → "
        f"pass={result['num_pass']} / shadow={result['num_shadow']}"
        f"{' (dry-run)' if args.dry_run else ''}\n"
        f"α consumed (daily): {alpha_state['consumed']['daily']:.4f} / "
        f"{alpha_state['budget']['daily']:.4f}\n"
        f"Summary: `knowledge-base/wiki/analyses/candidates/{date_str}.md`"
    )
    notify_discord(notify_msg)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
