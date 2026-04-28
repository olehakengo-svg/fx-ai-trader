"""Kelly 再計算 trigger — 「正の指標が見え始めてから」の自動判定

ユーザー指摘 (2026-04-28):
> Kelly計算もプラス指標が見え始めてから再計算をすればいい。
> 「Kelly正転待ち」を発掘段階の gate にすると、新エッジを試さない限り
> Kelly は永久改善しない (鶏と卵問題)。

解決アプローチ: Kelly を**事前 gate** ではなく**事後 lot サイジング指標**として使い、
positive momentum が観測された時点で自動再計算 + lot 拡大 trigger を発火する。

## 再計算 Trigger 階層 (pre-registered)

階層化された trigger を pre-register して HARKing を防止:

### Tier 0 — Baseline (現状)
  Kelly < 0 → recommended_fraction = 0
  → ルール R3: 既存 ELITE のみ default lot で稼働、新規 promote なし

### Tier 1 — Early Positive Signal
  trigger:
    - 7d Live PnL > +20pip (XAU除外)
    - 7d Live WR > 45%
    - aggregate_kelly recompute → edge > -5%
  action:
    - Kelly recompute 強制実行 (cron 24h → 6h)
    - WATCH cell の Wilson_BF 再判定 (Bonferroni-K 動的更新)
    - Discord 通知: 🟡 EARLY_POSITIVE

### Tier 2 — Confirmed Recovery
  trigger:
    - 7d Live PnL > +50pip ∧ live_wr > 50%
    - 14d Live PnL > +30pip
    - aggregate_kelly > 0 (positive)
    - DD < 5%
  action:
    - 既存 ELITE lot=default
    - WATCH 候補 (e.g. bb_rsi_reversion EUR_USD/BUY/Overlap) の mini-pilot 起動許可
    - Discord 通知: 🟢 CONFIRMED_RECOVERY

### Tier 3 — Promoted Scale
  trigger:
    - 14d Live PnL > +100pip
    - aggregate_kelly > 0.05 ∧ N_clean >= 100
    - DD < 2%
  action:
    - A2 lot_mult boost 段階解禁 (1.5x → 2.0x → 3.0x)
    - 新 sentinel 戦略の昇格 fast-track 許可
    - Discord 通知: 🚀 SCALE_AUTHORIZED

## Output

stdout (JSON) + Discord webhook (DISCORD_WEBHOOK_URL env) +
JSONL history (raw/audits/kelly_recompute/history.jsonl)

## Render Cron Job 想定

  Schedule: 0 21 * * *  # JST 06:00 daily
  Command: python3 tools/kelly_recompute_trigger.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

_ALLOWED_SCHEMES = ("https", "http")


def _validate_url(url: str, *, label: str) -> str:
    p = urllib.parse.urlparse(url)
    if p.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"{label}: unsupported scheme {p.scheme!r}")
    if not p.netloc:
        raise ValueError(f"{label}: missing host")
    return url


def _fetch_json(url: str, timeout: int = 30) -> dict:
    safe = _validate_url(url, label="api")
    r = requests.get(safe, timeout=timeout,
                     headers={"User-Agent": "kelly-recompute/1.0"})
    r.raise_for_status()
    return r.json()


# ---- Kelly computation ----------------------------------------------------

def compute_kelly(wins: int, losses: int,
                   gross_profit: float, gross_loss: float) -> dict:
    """Standard Kelly fraction from win/loss counts and PnL.

    Returns: {edge, win_rate, odds_ratio, full_kelly, half_kelly, quarter_kelly}
    """
    n = wins + losses
    if n == 0 or wins == 0 or losses == 0:
        return {"edge": 0.0, "win_rate": 0.0, "odds_ratio": 1.0,
                "full_kelly": 0.0, "half_kelly": 0.0, "quarter_kelly": 0.0,
                "n": n, "insufficient_data": True}
    p = wins / n
    avg_win = gross_profit / wins
    avg_loss = abs(gross_loss / losses) if losses else 1e-9
    if avg_loss <= 0:
        return {"edge": 0.0, "win_rate": p, "odds_ratio": 1.0,
                "full_kelly": 0.0, "half_kelly": 0.0, "quarter_kelly": 0.0,
                "n": n, "insufficient_data": True}
    b = avg_win / avg_loss  # odds ratio (win:loss)
    edge = p - (1 - p) / b  # E[X] / avg_loss = p - q/b
    full_k = (p * (b + 1) - 1) / b if b > 0 else 0
    return {
        "edge": round(edge, 4), "win_rate": round(p, 4),
        "odds_ratio": round(b, 4),
        "full_kelly": round(max(0, full_k), 4),
        "half_kelly": round(max(0, full_k) * 0.5, 4),
        "quarter_kelly": round(max(0, full_k) * 0.25, 4),
        "n": n, "insufficient_data": n < 10,
    }


# ---- Trigger evaluation ----------------------------------------------------

def evaluate_tier(metrics: dict) -> tuple[str, list[str], dict]:
    """Decide which tier (0/1/2/3) the system is at.

    Returns (tier, reasons, actions)
    """
    pnl_7d = metrics["pnl_7d"]
    pnl_14d = metrics["pnl_14d"]
    wr_7d = metrics["wr_7d"]
    edge = metrics["kelly_edge"]
    full_k = metrics["full_kelly"]
    n_clean = metrics["n_clean"]
    dd_pct = metrics["dd_pct"]

    reasons: list[str] = []
    actions: list[str] = []
    tier = 0

    # Tier 1
    t1 = (pnl_7d > 20 and wr_7d > 0.45 and edge > -0.05)
    if t1:
        tier = 1
        reasons.append(
            f"T1: pnl_7d=+{pnl_7d:.1f}>20 ∧ wr_7d={wr_7d*100:.1f}>45 "
            f"∧ edge={edge:+.3f}>-0.05"
        )
        actions += [
            "🟡 EARLY_POSITIVE: Kelly recompute cron を 6h 化",
            "🟡 WATCH cell Wilson_BF 再判定 (Bonferroni K 動的更新)",
        ]

    # Tier 2
    t2 = (pnl_7d > 50 and wr_7d > 0.50 and pnl_14d > 30
          and edge > 0 and dd_pct < 0.05)
    if t2:
        tier = 2
        reasons.append(
            f"T2: pnl_7d=+{pnl_7d:.1f}>50 ∧ wr_7d={wr_7d*100:.1f}>50 "
            f"∧ pnl_14d=+{pnl_14d:.1f}>30 ∧ edge={edge:+.3f}>0 "
            f"∧ dd={dd_pct*100:.1f}%<5%"
        )
        actions += [
            "🟢 CONFIRMED_RECOVERY: ELITE lot=default 維持",
            "🟢 WATCH cand mini-pilot 起動許可 (Pre-reg LOCK 通過時)",
        ]

    # Tier 3
    t3 = (pnl_14d > 100 and full_k > 0.05 and n_clean >= 100
          and dd_pct < 0.02)
    if t3:
        tier = 3
        reasons.append(
            f"T3: pnl_14d=+{pnl_14d:.1f}>100 ∧ full_kelly={full_k:.3f}>0.05 "
            f"∧ n_clean={n_clean}>=100 ∧ dd={dd_pct*100:.1f}%<2%"
        )
        actions += [
            "🚀 SCALE_AUTHORIZED: A2 lot_mult boost 段階解禁",
            "🚀 新 sentinel 戦略の昇格 fast-track 許可",
        ]

    if tier == 0:
        reasons.append(
            f"T0 (baseline): edge={edge:+.3f}, pnl_7d=+{pnl_7d:.1f}, "
            f"wr_7d={wr_7d*100:.1f}%, dd={dd_pct*100:.1f}%"
        )
        actions.append("R3: 既存 ELITE のみ default lot、新規 promote なし")

    return f"T{tier}", reasons, actions


def _post_discord(webhook_url: str, content: str) -> bool:
    try:
        safe = _validate_url(webhook_url, label="discord")
        r = requests.post(safe, json={"content": content}, timeout=10)
        return r.ok
    except Exception as e:
        print(f"[discord] {e}", file=sys.stderr)
        return False


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api-base", default="https://fx-ai-trader.onrender.com")
    p.add_argument("--out-dir", default="raw/audits/kelly_recompute")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    base = args.api_base.rstrip("/")

    # Fetch trades + risk
    try:
        trades_data = _fetch_json(
            f"{base}/api/demo/trades?status=CLOSED&limit=20000")
        trades = trades_data.get("trades") or []
        risk = _fetch_json(f"{base}/api/risk/dashboard")
    except Exception as e:
        print(json.dumps({"error": f"api fetch failed: {e}"}))
        sys.exit(1)

    now = datetime.now(timezone.utc)
    cutoff_7d = (now - timedelta(days=7)).isoformat()
    cutoff_14d = (now - timedelta(days=14)).isoformat()

    # Live trades only (XAU除外, post-cutoff)
    def _live_filter(t, since):
        return (t.get("instrument") != "XAU_USD"
                and not t.get("is_shadow")
                and t.get("entry_time", "") >= since
                and t.get("outcome") in ("WIN", "LOSS"))

    live_7d = [t for t in trades if _live_filter(t, cutoff_7d)]
    live_14d = [t for t in trades if _live_filter(t, cutoff_14d)]

    pnl_7d = sum(float(t.get("pnl_pips") or 0) for t in live_7d)
    wins_7d = sum(1 for t in live_7d if t.get("outcome") == "WIN")
    n_7d = len(live_7d)
    wr_7d = wins_7d / n_7d if n_7d else 0
    pnl_14d = sum(float(t.get("pnl_pips") or 0) for t in live_14d)

    # Recompute Kelly from 14d clean live data (post-cutoff)
    wins_14d = sum(1 for t in live_14d if t.get("outcome") == "WIN")
    losses_14d = sum(1 for t in live_14d if t.get("outcome") == "LOSS")
    gp_14d = sum(float(t.get("pnl_pips") or 0) for t in live_14d
                  if t.get("outcome") == "WIN")
    gl_14d = sum(float(t.get("pnl_pips") or 0) for t in live_14d
                  if t.get("outcome") == "LOSS")
    kelly = compute_kelly(wins_14d, losses_14d, gp_14d, gl_14d)

    # DD from risk dashboard
    dd_status = risk.get("dd_status", {}) if isinstance(risk, dict) else {}
    dd_pct = float(dd_status.get("dd_pct", 0)) if dd_status else 0.0
    if dd_pct > 1:  # already in percent form
        dd_pct = dd_pct / 100.0

    metrics = {
        "pnl_7d": round(pnl_7d, 1),
        "pnl_14d": round(pnl_14d, 1),
        "wr_7d": round(wr_7d, 4),
        "n_7d": n_7d,
        "n_14d": len(live_14d),
        "kelly_edge": kelly["edge"],
        "full_kelly": kelly["full_kelly"],
        "half_kelly": kelly["half_kelly"],
        "n_clean": kelly["n"],
        "dd_pct": round(dd_pct, 4),
    }

    tier, reasons, actions = evaluate_tier(metrics)

    summary = {
        "generated_at": now.isoformat(),
        "tier": tier,
        "metrics": metrics,
        "reasons": reasons,
        "actions": actions,
        "kelly_recomputed": kelly,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # Persist
    if not args.dry_run:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "history.jsonl").open("a") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")

    # Discord on tier change
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook and not args.dry_run and tier != "T0":
        msg = (f"**Kelly Recompute Trigger** — {tier}\n"
               f"_{summary['generated_at']}_\n\n"
               + "\n".join(reasons) + "\n\n**Actions:**\n"
               + "\n".join(actions))
        _post_discord(webhook, msg[:1900])

    # Exit code: 0 T0, 1 T1, 2 T2, 3 T3
    sys.exit({"T0": 0, "T1": 1, "T2": 2, "T3": 3}.get(tier, 0))


if __name__ == "__main__":
    main()
