"""Pre-reg LOCK trigger monitor

`knowledge-base/wiki/decisions/pre-reg-bbrsi-eurusd-2026-04-27.md` で定義した
trigger 条件を毎日自動評価する。通過時に Discord ALERT 通知 + JSONL 履歴保存。

## 監視対象 (将来 YAML 化)

bb_rsi_reversion × EUR_USD × BUY × Scalp × Overlap
  - shadow_n >= 30
  - Wilson_BF (k=624, z=3.94) > 0.294
  - binomial p_bonferroni < 0.05
  - WF halves verdict in {stable, borderline}
  - avg_net (post pair-friction) > 0
  - unique_days >= 7
  - 期限: 2026-05-25 までに全条件通過

## Usage

    python3 tools/prereg_lock_monitor.py
    python3 tools/prereg_lock_monitor.py --dry-run

## Render Cron Job 想定

    Schedule: 0 21 * * *  # JST 06:00 daily
    Command: python3 tools/prereg_lock_monitor.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# Pre-reg LOCK definitions (将来は YAML / JSON schema 化)
PREREG_LOCKS = [
    {
        "id": "bbrsi_eurusd_buy_overlap_2026-04-27",
        "strategy": "bb_rsi_reversion",
        "pair": "EUR_USD",
        "direction": "BUY",
        "session": "Overlap",  # UTC 12-16
        "expires": "2026-05-25",
        "trigger": {
            "shadow_n_min": 30,
            "wilson_bf_624_min": 0.294,
            "p_bonferroni_max": 0.05,
            "wf_verdict_in": ["stable", "borderline"],
            "avg_net_min": 0.0,
            "unique_days_min": 7,
        },
    },
    {
        # Discovered 2026-04-28 in 86-cell v3 audit
        # see: wiki/decisions/pre-reg-overlap-cells-2026-04-28.md
        "id": "volsurge_usdjpy_sell_overlap_2026-04-28",
        "strategy": "vol_surge_detector",
        "pair": "USD_JPY",
        "direction": "SELL",
        "session": "Overlap",
        "expires": "2026-05-26",
        "trigger": {
            "shadow_n_min": 30,
            "wilson_bf_624_min": 0.294,
            "p_bonferroni_max": 0.05,
            "wf_verdict_in": ["stable", "borderline"],
            "avg_net_min": 0.0,
            "unique_days_min": 7,
        },
    },
    {
        "id": "emacross_usdjpy_sell_overlap_2026-04-28",
        "strategy": "ema_cross",
        "pair": "USD_JPY",
        "direction": "SELL",
        "session": "Overlap",
        "expires": "2026-05-26",
        "trigger": {
            "shadow_n_min": 30,
            "wilson_bf_624_min": 0.294,
            "p_bonferroni_max": 0.05,
            "wf_verdict_in": ["stable", "borderline"],
            "avg_net_min": 0.0,
            "unique_days_min": 7,
        },
    },
]

_ALLOWED_SCHEMES = ("https", "http")


def _validate_url(url: str, *, label: str) -> str:
    p = urllib.parse.urlparse(url)
    if p.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"{label}: unsupported scheme {p.scheme!r}")
    if not p.netloc:
        raise ValueError(f"{label}: missing host")
    return url


def _wilson_lower(wins: int, n: int, z: float) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - spread) / den)


def _binomial_p(wins: int, n: int, p0: float = 0.5) -> float:
    """Two-sided normal-approx p-value vs p0=0.5."""
    if n <= 0:
        return 1.0
    var = n * p0 * (1 - p0)
    if var <= 0:
        return 1.0
    z = (wins - n * p0) / math.sqrt(var)
    return max(0.0, min(1.0,
        2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2.0))))))


def _derive_session(entry_time: str) -> str:
    """Map UTC hour → session label (matches cell_edge_audit.py)."""
    if not entry_time:
        return "default"
    try:
        ts = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
        h = ts.astimezone(timezone.utc).hour
    except Exception:
        return "default"
    if h < 7:
        return "Tokyo"
    if h < 12:
        return "London"
    if h < 16:
        return "Overlap"
    if h < 21:
        return "NewYork"
    return "Sydney"


def _evaluate_lock(lock: dict, trades: list[dict],
                    p_bonferroni_k: int = 624) -> dict:
    """Evaluate one Pre-reg LOCK against fresh trade data.

    Returns {
        triggered: bool,
        passed_count: int,
        total_conditions: int,
        details: {condition: {value, threshold, pass}},
        cell_stats: {n, wr, ev, ...}
    }
    """
    cell = [
        t for t in trades
        if t.get("entry_type") == lock["strategy"]
        and t.get("instrument") == lock["pair"]
        and (t.get("direction") or "").upper() == lock["direction"].upper()
        and _derive_session(t.get("entry_time", "")) == lock["session"]
        and (t.get("outcome") in ("WIN", "LOSS"))
    ]
    n = len(cell)
    wins = sum(1 for t in cell if t.get("outcome") == "WIN")
    pnls = [float(t.get("pnl_pips") or 0) for t in cell]
    ev = sum(pnls) / n if n else 0.0
    fric_per = [
        (float(t.get("spread_at_entry") or 0)
         + float(t.get("spread_at_exit") or 0)
         + float(t.get("slippage_pips") or 0))
        for t in cell
    ]
    avg_fric = sum(fric_per) / n if n else 0.0
    avg_net = ev - avg_fric

    # WF halves
    sorted_t = sorted(cell, key=lambda t: t.get("entry_time", ""))
    half = n // 2
    h1 = [float(t.get("pnl_pips") or 0) for t in sorted_t[:half]] if half else []
    h2 = [float(t.get("pnl_pips") or 0) for t in sorted_t[half:]]
    h1_avg = sum(h1) / len(h1) if h1 else 0.0
    h2_avg = sum(h2) / len(h2) if h2 else 0.0
    if n < 4:
        wf_verdict = "insufficient_data"
    elif h1_avg > 0 and h2_avg < 0:
        wf_verdict = "collapse"
    elif h1_avg <= 0 and h2_avg <= 0:
        wf_verdict = "both_negative"
    elif abs(h1_avg) > 1e-6:
        ratio = h2_avg / abs(h1_avg)
        wf_verdict = "stable" if ratio >= 0.5 else "borderline"
    else:
        wf_verdict = "h1_zero"

    days = {(t.get("entry_time") or "")[:10] for t in cell if t.get("entry_time")}
    unique_days = len(days)

    wL_624 = _wilson_lower(wins, n, 3.94)
    p_raw = _binomial_p(wins, n, 0.5)
    p_bonf = min(1.0, p_raw * p_bonferroni_k)

    trig = lock["trigger"]
    details = {
        "shadow_n": {"value": n, "threshold": trig["shadow_n_min"],
                     "pass": n >= trig["shadow_n_min"]},
        "wilson_bf_624": {"value": round(wL_624, 4),
                          "threshold": trig["wilson_bf_624_min"],
                          "pass": wL_624 > trig["wilson_bf_624_min"]},
        "p_bonferroni": {"value": round(p_bonf, 5),
                         "threshold": trig["p_bonferroni_max"],
                         "pass": p_bonf < trig["p_bonferroni_max"]},
        "wf_verdict": {"value": wf_verdict,
                       "threshold": trig["wf_verdict_in"],
                       "pass": wf_verdict in trig["wf_verdict_in"]},
        "avg_net": {"value": round(avg_net, 3),
                    "threshold": trig["avg_net_min"],
                    "pass": avg_net > trig["avg_net_min"]},
        "unique_days": {"value": unique_days,
                        "threshold": trig["unique_days_min"],
                        "pass": unique_days >= trig["unique_days_min"]},
    }
    passed = sum(1 for d in details.values() if d["pass"])
    total = len(details)

    return {
        "lock_id": lock["id"],
        "strategy": lock["strategy"],
        "pair": lock["pair"],
        "direction": lock["direction"],
        "session": lock["session"],
        "expires": lock["expires"],
        "expires_in_days": (
            (datetime.fromisoformat(lock["expires"]).date()
             - datetime.now(timezone.utc).date()).days
        ),
        "triggered": passed == total,
        "passed_count": passed,
        "total_conditions": total,
        "details": details,
        "cell_stats": {
            "n": n, "wins": wins, "wr": round(wins / n * 100, 2) if n else 0,
            "ev_raw": round(ev, 3),
            "avg_friction": round(avg_fric, 3),
            "avg_net": round(avg_net, 3),
            "wf_h1_avg": round(h1_avg, 3),
            "wf_h2_avg": round(h2_avg, 3),
            "wf_verdict": wf_verdict,
            "unique_days": unique_days,
            "wilson_bf_624": round(wL_624, 4),
            "p_bonferroni": round(p_bonf, 5),
        },
    }


def _post_discord(webhook_url: str, content: str) -> bool:
    try:
        safe = _validate_url(webhook_url, label="discord")
        r = requests.post(safe, json={"content": content}, timeout=10)
        return r.ok
    except Exception as e:
        print(f"[discord] {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api-base",
                        default="https://fx-ai-trader.onrender.com")
    parser.add_argument("--limit", type=int, default=20000,
                        help="trades fetch limit")
    parser.add_argument("--out-dir", default="raw/audits/prereg_history")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    url = f"{args.api_base.rstrip('/')}/api/demo/trades?status=CLOSED&limit={args.limit}"
    safe_url = _validate_url(url, label="api")
    try:
        r = requests.get(safe_url, timeout=30,
                         headers={"User-Agent": "prereg-monitor/1.0"})
        r.raise_for_status()
        trades = r.json().get("trades") or []
    except Exception as e:
        print(json.dumps({"error": f"api fetch failed: {e}", "url": url}))
        sys.exit(1)

    # 30d window
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    trades = [t for t in trades
              if t.get("instrument") != "XAU_USD"
              and t.get("entry_time", "") >= cutoff]

    results = [_evaluate_lock(lock, trades) for lock in PREREG_LOCKS]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_locks": len(results),
        "triggered_count": sum(1 for r in results if r["triggered"]),
        "expired_count": sum(1 for r in results if r["expires_in_days"] < 0),
        "locks": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # Discord on TRIGGER or EXPIRY warning
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook and not args.dry_run:
        for r in results:
            if r["triggered"]:
                msg = (f"🟢 **Pre-reg LOCK TRIGGERED**: `{r['lock_id']}`\n"
                       f"All {r['total_conditions']} conditions passed. "
                       f"Strategy: {r['strategy']} × {r['pair']} × {r['direction']} × {r['session']}\n"
                       f"```{json.dumps(r['cell_stats'], ensure_ascii=False, indent=2)}```")
                _post_discord(webhook, msg[:1900])
            elif 0 <= r["expires_in_days"] <= 7:
                fail = [k for k, v in r["details"].items() if not v["pass"]]
                msg = (f"🟡 **Pre-reg LOCK expiring**: `{r['lock_id']}` in {r['expires_in_days']}d\n"
                       f"Passed {r['passed_count']}/{r['total_conditions']} — failing: {fail}")
                _post_discord(webhook, msg[:1900])
            elif r["expires_in_days"] < 0:
                msg = f"🔴 **Pre-reg LOCK EXPIRED**: `{r['lock_id']}` (DISQUALIFY) — {r['cell_stats']}"
                _post_discord(webhook, msg[:1900])

    # Persist
    if not args.dry_run:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).date().isoformat()
        with (out_dir / f"history.jsonl").open("a") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    sys.exit(0 if not summary["triggered_count"] else 0)


if __name__ == "__main__":
    main()
