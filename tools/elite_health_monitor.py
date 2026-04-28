"""ELITE/lot_boost 戦略 daily health monitor

deploy 直後の Phase 3 新ゲート (friction-aware EV / Wilson_BF / WF collapse) が
既存 ELITE_LIVE 3 戦略 + lot_boost 11 戦略を**誤 demote** することを早期検出する。

## アラート閾値 (3段階)

🟡 INFO   : wilson_bf_lower < 0.30 (BE_WR ぎりぎり)
🟠 WARN   : N>=15 ∧ ev<-0.5 (auto demote 5 サンプル前)
🟠 WARN   : avg_net_pips < -1.0 (friction 控除後の累積負け)
🟠 WARN   : wf_h1_avg > 0 ∧ wf_h2_avg < 0 (WF sign flip)
🔴 ALERT  : status 遷移 promoted → demoted を観測

## Output

- stdout (JSON-formatted summary)
- 環境変数 DISCORD_WEBHOOK_URL があれば Discord 通知
- raw/audits/elite_health/<date>.jsonl に履歴保存

## Usage

    python3 tools/elite_health_monitor.py
    python3 tools/elite_health_monitor.py --dry-run --window 30
    python3 tools/elite_health_monitor.py --api-base http://127.0.0.1:5000

## Render Cron Job 想定

    Schedule: 0 21,3,9 * * *  # JST 06:00 / 12:00 / 18:00 (UTC 21/3/9)
    Command: python3 tools/elite_health_monitor.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

_ALLOWED_SCHEMES = ("https", "http")


def _validate_url(url: str, *, label: str) -> str:
    """Reject file://, ftp://, etc. — only http(s) is allowed.

    Mitigates SSRF / arbitrary-file-read risk (CWE-939).
    """
    p = urllib.parse.urlparse(url)
    if p.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"{label}: unsupported URL scheme {p.scheme!r}; "
            f"only {_ALLOWED_SCHEMES} allowed"
        )
    if not p.netloc:
        raise ValueError(f"{label}: missing host in URL {url!r}")
    return url

# 監視対象 — tier-master.json から動的に読むことも可能だが、
# deploy 直後の防御層として hardcode しておくほうが意図が明確。
ELITE_LIVE = {"gbp_deep_pullback", "session_time_bias", "trendline_sweep"}
LOT_BOOST = {
    "gbp_deep_pullback", "htf_false_breakout", "london_fix_reversal",
    "london_ny_swing", "mtf_reversal_confluence", "session_time_bias",
    "tokyo_range_breakout_up", "turtle_soup", "vix_carry_unwind",
    "vol_momentum_scalp", "vwap_mean_reversion",
}
WATCHED = ELITE_LIVE | LOT_BOOST

# 閾値
INFO_WILSON_BF_LT = 0.30
WARN_N_MIN = 15
WARN_EV_LT = -0.5
WARN_AVG_NET_LT = -1.0
BREAKEVEN_WR = 0.294


def _http_get_json(url: str, timeout: int = 15) -> dict:
    safe_url = _validate_url(url, label="api")
    r = requests.get(safe_url, timeout=timeout,
                     headers={"User-Agent": "elite-health-monitor/1.0"})
    r.raise_for_status()
    return r.json()


def _classify(strat: dict, prev_status: dict | None) -> tuple[str, list[str]]:
    """Return (severity, reasons) for one strategy snapshot.

    severity: "OK" / "INFO" / "WARN" / "ALERT"
    reasons: list of human-readable strings explaining the flags.
    """
    name = strat["name"]
    tier = strat.get("tier", "?")
    live = strat.get("live", {})
    shadow = strat.get("shadow", {})
    ext = strat.get("extended", {}) or {}

    n_live = int(live.get("n", 0))
    ev_live = float(live.get("pnl", 0)) / max(n_live, 1) if n_live else 0.0
    wr_live = float(live.get("wr", 0))

    avg_net = float(ext.get("avg_net_pips", 0))
    wL_bf = float(ext.get("wilson_bf_lower", 0))
    wf_h1 = float(ext.get("wf_h1_avg", 0))
    wf_h2 = float(ext.get("wf_h2_avg", 0))

    reasons: list[str] = []
    severity = "OK"

    # 🔴 ALERT: status 遷移 promoted -> demoted
    cur_status = "demoted" if tier == "FORCE_DEMOTED" else "active"
    if prev_status and prev_status.get(name) == "active" and cur_status == "demoted":
        severity = "ALERT"
        reasons.append(f"🔴 status transition active → demoted (tier={tier})")

    # 🟠 WARN: N>=15 ∧ ev<-0.5 (demote 5 サンプル前)
    if n_live >= WARN_N_MIN and ev_live < WARN_EV_LT:
        severity = max(severity, "WARN", key=_severity_rank)
        reasons.append(
            f"🟠 demote_imminent N={n_live} EV={ev_live:+.2f} (threshold N>=20 EV<-0.5)"
        )

    # 🟠 WARN: avg_net (friction 控除後) < -1.0pip
    if (n_live + int(shadow.get("n", 0))) >= 10 and avg_net < WARN_AVG_NET_LT:
        severity = max(severity, "WARN", key=_severity_rank)
        reasons.append(f"🟠 friction_loss avg_net={avg_net:+.2f}pip")

    # 🟠 WARN: WF sign flip
    if wf_h1 > 0 and wf_h2 < 0:
        severity = max(severity, "WARN", key=_severity_rank)
        reasons.append(f"🟠 wf_sign_flip h1={wf_h1:+.2f} h2={wf_h2:+.2f}")

    # 🟡 INFO: Wilson_BF lower < 0.30
    if 0 < wL_bf < INFO_WILSON_BF_LT:
        severity = max(severity, "INFO", key=_severity_rank)
        reasons.append(f"🟡 wilson_bf_lower={wL_bf:.3f} (< {BREAKEVEN_WR:.3f} BE)")

    return severity, reasons


_SEV_RANK = {"OK": 0, "INFO": 1, "WARN": 2, "ALERT": 3}


def _severity_rank(s: str) -> int:
    return _SEV_RANK.get(s, 0)


def _load_prev_status(history_path: Path) -> dict[str, str]:
    """Load most recent prior snapshot's tier per strategy."""
    if not history_path.exists():
        return {}
    try:
        # Last line of jsonl
        with history_path.open() as f:
            lines = f.readlines()
        if not lines:
            return {}
        prev = json.loads(lines[-1])
        return {
            s["name"]: ("demoted" if s.get("tier") == "FORCE_DEMOTED" else "active")
            for s in prev.get("strategies", [])
        }
    except Exception:
        return {}


def _save_snapshot(history_path: Path, payload: dict) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _post_discord(webhook_url: str, content: str) -> bool:
    try:
        safe_url = _validate_url(webhook_url, label="discord_webhook")
        r = requests.post(safe_url, json={"content": content}, timeout=10)
        return r.ok
    except ValueError as e:
        print(f"[discord] {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[discord] post failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api-base",
                        default="https://fx-ai-trader.onrender.com",
                        help="API base URL (default: production)")
    parser.add_argument("--window", type=int, default=30,
                        help="rolling_days for /api/strategies/status")
    parser.add_argument("--history-dir", default="raw/audits/elite_health",
                        help="JSONL history directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print only — skip Discord & history persistence")
    parser.add_argument("--include-all", action="store_true",
                        help="Include OK strategies in stdout (default: alerts only)")
    args = parser.parse_args()

    url = f"{args.api_base.rstrip('/')}/api/strategies/status?rolling_days={args.window}"
    try:
        payload = _http_get_json(url)
    except Exception as e:
        print(json.dumps({"error": f"api fetch failed: {e}", "url": url}))
        sys.exit(1)

    strategies = payload.get("strategies") or []
    watched = [s for s in strategies if s["name"] in WATCHED]
    if not watched:
        print(json.dumps({"warning": "no watched strategies in payload"}))
        sys.exit(0)

    history_path = Path(args.history_dir) / f"history.jsonl"
    prev_status = _load_prev_status(history_path) if not args.dry_run else {}

    results = []
    by_severity = {"ALERT": [], "WARN": [], "INFO": [], "OK": []}
    for s in watched:
        sev, reasons = _classify(s, prev_status)
        ext = s.get("extended", {}) or {}
        item = {
            "name": s["name"],
            "tier": s.get("tier"),
            "watched_class": "ELITE" if s["name"] in ELITE_LIVE else "lot_boost",
            "severity": sev,
            "reasons": reasons,
            "live": s.get("live"),
            "shadow": s.get("shadow"),
            "wilson_bf_lower": ext.get("wilson_bf_lower"),
            "avg_net_pips": ext.get("avg_net_pips"),
            "wf_h1_avg": ext.get("wf_h1_avg"),
            "wf_h2_avg": ext.get("wf_h2_avg"),
            "top_cell": ext.get("top_cell"),
        }
        results.append(item)
        by_severity[sev].append(item)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": args.window,
        "api_base": args.api_base,
        "total_watched": len(watched),
        "alert_count": len(by_severity["ALERT"]),
        "warn_count": len(by_severity["WARN"]),
        "info_count": len(by_severity["INFO"]),
        "ok_count": len(by_severity["OK"]),
        "strategies": results,
    }

    # stdout
    if args.include_all:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        non_ok = [r for r in results if r["severity"] != "OK"]
        print(json.dumps({
            "generated_at": summary["generated_at"],
            "window_days": args.window,
            "alerts": summary["alert_count"],
            "warnings": summary["warn_count"],
            "infos": summary["info_count"],
            "ok": summary["ok_count"],
            "non_ok_strategies": non_ok,
        }, ensure_ascii=False, indent=2))

    # Discord (if webhook configured + not dry-run + something non-OK)
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook and not args.dry_run and (by_severity["ALERT"] or by_severity["WARN"]):
        lines = [f"**ELITE Health Monitor** — {args.window}d window",
                 f"_{summary['generated_at']}_", ""]
        for tag, sev in [("🔴 ALERT", "ALERT"), ("🟠 WARN", "WARN")]:
            for it in by_severity[sev]:
                line = (f"{tag} `{it['name']}` ({it['watched_class']}, tier={it['tier']}) "
                        f"— " + "; ".join(it['reasons']))
                lines.append(line)
        if by_severity["INFO"]:
            lines.append(f"\n🟡 INFO ({len(by_severity['INFO'])}): "
                        + ", ".join(it["name"] for it in by_severity["INFO"]))
        _post_discord(webhook, "\n".join(lines)[:1900])

    # Persist history
    if not args.dry_run:
        _save_snapshot(history_path, summary)

    # Exit code: 0 OK, 1 INFO, 2 WARN, 3 ALERT (for cron monitoring)
    if by_severity["ALERT"]:
        sys.exit(3)
    if by_severity["WARN"]:
        sys.exit(2)
    if by_severity["INFO"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
