#!/usr/bin/env python3
"""
Tier C: 異常検知・通知 (15分毎 cron 実行)

Protocol: knowledge-base/wiki/analyses/daily-tierB-protocol.md §6

使用:
    python3 scripts/anomaly_watcher.py              # 1回実行 (cron想定)
    python3 scripts/anomaly_watcher.py --json       # machine-readable

検知項目:
    1. Spread > 2×30d median (per instrument)
    2. OANDA order latency > 3s
    3. Session volume drift (Tokyo <50% of median)
    4. Live N stagnation (24h増加0件)

**禁止事項**:
    - 判断しない (昇格/降格推奨は出さない)
    - 自動変更しない
    - 仮説生成しない (必要ならTier Bにエスカレート)

出力:
    - knowledge-base/raw/anomalies/YYYY-MM-DD.jsonl に追加
    - Discord 通知 (閾値超え時のみ)
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
API_BASE = os.environ.get("API_BASE", "https://fx-ai-trader.onrender.com")

SPREAD_MULTIPLIER_THRESHOLD = 2.0
LATENCY_THRESHOLD_SEC = 3.0
SESSION_VOLUME_RATIO_THRESHOLD = 0.5
N_STAGNATION_HOURS = 24


def fetch_json(path: str, timeout: int = 15) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"⚠️  fetch failed: {url} — {e}", file=sys.stderr)
        return {}


# ── 検知ロジック ────────────────────────────────────────

def check_spread_spike(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """instrument別に最新spread vs 30日median比を計算。"""
    events = []
    by_inst: dict[str, list[float]] = {}
    for t in trades:
        inst = t.get("instrument")
        sp = t.get("spread_at_entry")
        if inst and sp is not None and "XAU" not in inst:
            by_inst.setdefault(inst, []).append(float(sp))

    for inst, spreads in by_inst.items():
        if len(spreads) < 10:
            continue
        median = statistics.median(spreads[:-5]) if len(spreads) > 5 else statistics.median(spreads)
        latest = statistics.mean(spreads[-5:]) if len(spreads) >= 5 else spreads[-1]
        if median > 0 and latest / median >= SPREAD_MULTIPLIER_THRESHOLD:
            events.append(
                {
                    "type": "spread_spike",
                    "instrument": inst,
                    "latest_mean_5": round(latest, 2),
                    "median_30d": round(median, 2),
                    "ratio": round(latest / median, 2),
                }
            )
    return events


def check_oanda_latency(oanda_status: dict[str, Any]) -> list[dict[str, Any]]:
    """OANDA API最近の平均latency。"""
    events = []
    latency = oanda_status.get("avg_order_latency_sec")
    if latency is not None and float(latency) > LATENCY_THRESHOLD_SEC:
        events.append(
            {
                "type": "oanda_latency",
                "latency_sec": float(latency),
                "threshold": LATENCY_THRESHOLD_SEC,
            }
        )
    return events


def check_live_n_stagnation(status: dict[str, Any]) -> list[dict[str, Any]]:
    """Live N が N_STAGNATION_HOURS 増加0件なら警告。

    status APIに last_trade_time があると仮定。無ければ skip。
    """
    events = []
    last_trade = status.get("last_trade_time")
    if not last_trade:
        return events
    try:
        last_dt = datetime.fromisoformat(last_trade.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return events
    hours_since = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
    if hours_since >= N_STAGNATION_HOURS:
        events.append(
            {
                "type": "live_n_stagnation",
                "hours_since_last_trade": round(hours_since, 1),
                "threshold_hours": N_STAGNATION_HOURS,
            }
        )
    return events


def check_session_volume(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tokyo session (UTC 00-06) の直近volumeが30日median比50%未満なら警告。"""
    events = []
    from collections import defaultdict
    by_day = defaultdict(lambda: defaultdict(int))
    for t in trades:
        et = t.get("exit_time", "") or t.get("entry_time", "")
        if len(et) < 13:
            continue
        day = et[:10]
        try:
            hour = int(et[11:13])
        except ValueError:
            continue
        if 0 <= hour < 6:
            by_day[day]["tokyo"] += 1

    if len(by_day) < 7:
        return events
    days = sorted(by_day.keys())
    recent = by_day[days[-1]]["tokyo"]
    historical = [by_day[d]["tokyo"] for d in days[:-1]]
    med = statistics.median(historical) if historical else 0
    if med > 0 and recent / med < SESSION_VOLUME_RATIO_THRESHOLD:
        events.append(
            {
                "type": "session_volume_drift",
                "session": "tokyo",
                "recent_count": recent,
                "median_count": med,
                "ratio": round(recent / med, 2),
            }
        )
    return events


# ── ログ保存 + 通知 ─────────────────────────────────────

def save_events(events: list[dict[str, Any]]) -> Path:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = ROOT / "knowledge-base" / "raw" / "anomalies" / f"{date_str}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with path.open("a") as f:
        for e in events:
            f.write(json.dumps({**e, "ts": ts}, ensure_ascii=False) + "\n")
    return path


def notify_discord(events: list[dict[str, Any]]) -> None:
    if not events:
        return
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        return

    lines = [f"🚨 Tier C Anomaly — {datetime.now(timezone.utc).strftime('%H:%M UTC')}"]
    for e in events:
        et = e.get("type")
        if et == "spread_spike":
            lines.append(f"- spread_spike {e['instrument']}: {e['latest_mean_5']} vs median {e['median_30d']} ({e['ratio']}×)")
        elif et == "oanda_latency":
            lines.append(f"- oanda_latency: {e['latency_sec']:.2f}s (threshold {e['threshold']}s)")
        elif et == "live_n_stagnation":
            lines.append(f"- live_n_stagnation: {e['hours_since_last_trade']}h since last trade")
        elif et == "session_volume_drift":
            lines.append(f"- session_drift {e['session']}: {e['recent_count']} vs median {e['median_count']} ({e['ratio']}×)")
        else:
            lines.append(f"- {et}: {json.dumps(e, ensure_ascii=False)[:150]}")
    lines.append("")
    lines.append("※判断・自動変更なし。通知のみ。")

    try:
        requests.post(webhook, json={"content": "\n".join(lines)[:1900]}, timeout=10)
    except requests.RequestException as e:
        print(f"⚠️  Discord notify failed: {e}", file=sys.stderr)


# ── メイン ──────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    trades_raw = fetch_json("/api/demo/trades?limit=500")
    trades = trades_raw.get("trades", []) if isinstance(trades_raw, dict) else []

    oanda_status = fetch_json("/api/oanda/status")
    status = fetch_json("/api/demo/status")

    all_events: list[dict[str, Any]] = []
    all_events.extend(check_spread_spike(trades))
    all_events.extend(check_oanda_latency(oanda_status))
    all_events.extend(check_live_n_stagnation(status))
    all_events.extend(check_session_volume(trades))

    if all_events:
        path = save_events(all_events)
        notify_discord(all_events)
        print(f"Detected {len(all_events)} anomalies → {path}")
    else:
        print("No anomalies detected.")

    if args.json:
        print(json.dumps(all_events, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
