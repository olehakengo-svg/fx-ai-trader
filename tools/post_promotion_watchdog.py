#!/usr/bin/env python3
"""Post-Promotion Watchdog — Live N≥30 Kelly-gate monitor for newly promoted cells.

目的 (CLAUDE.md 判断プロトコル準拠)
-----------------------------------
2026-04-22 に PAIR_PROMOTED 昇格した 2 セル
  - (streak_reversal, USD_JPY)
  - (vwap_mean_reversion, USD_JPY)
の post-promotion Live パフォーマンスを Render 本番 API (`/api/demo/trades`)
から毎回フェッチし、

  N < 30               → WATCH (観測継続、判断保留)
  N >= 30 AND kelly<0  → DEMOTE_CANDIDATE (警告 + exit 1)
  N >= 30 AND kelly>=0 → HOLD

を判定する読み取り専用ウォッチドッグ。本番 DB は `/api/demo/trades` 経由で
しかアクセスせず、ローカル demo_trades.db には依存しない (handoff
`/api/demo/stats` の all-time 汚染問題を回避)。

設計原則
--------
- 非侵襲: live path / BT signal 関数は一切変更しない (post-hoc 監視のみ)
- XAU 除外: feedback_exclude_xau memory 通り必須
- graceful fail: ネットワーク不可環境では exit code 2 + stderr メッセージ
- スモークテスト (__main__): `--smoke` で合成 fixture を使った dry-run

Usage
-----
    # 通常実行 (本番 API 参照)
    python3 tools/post_promotion_watchdog.py

    # JSON を stdout で消費 (Markdown report は常に書き出す)
    python3 tools/post_promotion_watchdog.py --json-only

    # ネットワーク無し dry-run (合成 trades で全ロジックを検証)
    python3 tools/post_promotion_watchdog.py --smoke

    # カスタム API エンドポイント (staging 等)
    python3 tools/post_promotion_watchdog.py --api https://staging.example.com

Exit codes
----------
    0  全セル HOLD または WATCH (問題なし)
    1  いずれかのセルが DEMOTE_CANDIDATE
    2  ネットワーク不可 / API エラー / 実行不能
"""
from __future__ import annotations

import argparse
import json
import math
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_API = "https://fx-ai-trader.onrender.com"
DEFAULT_LIMIT = 5000

# Promoted cells whitelist — update only after a new PAIR_PROMOTED event is
# recorded in wiki/tier-master.md and verified with tier_integrity_check.
PROMOTED_AT_DEFAULT = "2026-04-22T12:00:00+00:00"
WATCHED_CELLS: list[dict[str, str]] = [
    {
        "entry_type": "streak_reversal",
        "instrument": "USD_JPY",
        "promoted_at": PROMOTED_AT_DEFAULT,
    },
    {
        "entry_type": "vwap_mean_reversion",
        "instrument": "USD_JPY",
        "promoted_at": PROMOTED_AT_DEFAULT,
    },
]

MIN_N_FOR_JUDGMENT = 30  # CLAUDE.md: Live N>=30 is the decision threshold

# Output directory for daily monitor markdown reports
MONITORS_DIR = _PROJECT_ROOT / "knowledge-base" / "raw" / "monitors"


# ---------------------------------------------------------------------------
# URL safety (mirrors bayesian_edge_check.py pattern, Semgrep CWE-939)
# ---------------------------------------------------------------------------
_ALLOWED_SCHEMES = ("http", "https")


def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"Refusing non-http(s) URL scheme: {parsed.scheme!r}")
    if not parsed.netloc:
        raise ValueError(f"URL must include a hostname (url={url!r})")


_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = True
_SSL_CTX.verify_mode = ssl.CERT_REQUIRED
_SAFE_OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(context=_SSL_CTX),
)


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------
def parse_iso(ts: str) -> datetime | None:
    """Tolerant ISO8601 parser. Returns timezone-aware UTC datetime or None."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.strptime(str(ts)[:19], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except Exception:
            return None


# ---------------------------------------------------------------------------
# API fetch (graceful fail)
# ---------------------------------------------------------------------------
def fetch_trades(api: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Fetch /api/demo/trades. On network failure, exits 2 with stderr message."""
    url = f"{api.rstrip('/')}/api/demo/trades?limit={int(limit)}"
    try:
        _validate_url(url)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    req = urllib.request.Request(
        url, headers={"User-Agent": "post-promotion-watchdog/1.0"}
    )
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with _SAFE_OPENER.open(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        print(
            f"ERROR: API fetch failed ({type(e).__name__}: {e}). "
            "Network unavailable or API down — watchdog cannot judge.",
            file=sys.stderr,
        )
        sys.exit(2)
    if isinstance(payload, dict):
        return payload.get("trades", []) or []
    if isinstance(payload, list):
        return payload
    return []


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------
def filter_cell_trades(
    trades: list[dict],
    *,
    entry_type: str,
    instrument: str,
    promoted_at: datetime,
) -> list[dict]:
    """Keep CLOSED non-shadow trades for this cell that occurred after promotion.

    Rules (mirrors handoff contract):
      - is_shadow == 0
      - status.upper() == 'CLOSED'
      - instrument does not contain 'XAU' (feedback_exclude_xau)
      - created_at / entry_time >= promoted_at
      - entry_type == <cell strategy>, instrument == <cell pair>
    """
    kept: list[dict] = []
    for t in trades:
        inst = str(t.get("instrument") or "")
        if "XAU" in inst:
            continue  # XAU exclusion mandate
        if inst != instrument:
            continue
        if str(t.get("entry_type") or "") != entry_type:
            continue
        if int(t.get("is_shadow", 0) or 0) != 0:
            continue
        status = str(t.get("status") or "").upper()
        if status != "CLOSED":
            continue
        ts = parse_iso(t.get("created_at") or t.get("entry_time") or "")
        if ts is None or ts < promoted_at:
            continue
        kept.append(t)
    return kept


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def wilson_interval(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion."""
    if n <= 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt((p * (1 - p) / n) + (z * z / (4 * n * n)))) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def compute_cell_metrics(trades: list[dict]) -> dict[str, Any]:
    """Compute N, WR, PF, avg_win_pip (b), mean_pnl, Kelly edge, Wilson CI."""
    n = len(trades)
    if n == 0:
        return {
            "n": 0,
            "wins": 0,
            "losses": 0,
            "wr": 0.0,
            "wilson_lo": 0.0,
            "wilson_hi": 0.0,
            "mean_pnl_pip": 0.0,
            "avg_win_pip": 0.0,
            "avg_loss_pip": 0.0,
            "profit_factor": None,
            "kelly_edge": None,
        }
    pnls = [float(t.get("pnl_pips") or 0.0) for t in trades]
    wins_list = [p for p in pnls if p > 0]
    losses_list = [p for p in pnls if p <= 0]
    wins = len(wins_list)
    losses = len(losses_list)
    wr = wins / n
    wlo, whi = wilson_interval(wins, n)
    mean_pnl = sum(pnls) / n
    avg_win = (sum(wins_list) / wins) if wins else 0.0
    avg_loss = (sum(losses_list) / losses) if losses else 0.0  # negative or zero
    gross_win = sum(wins_list)
    gross_loss = -sum(losses_list)  # positive magnitude
    pf = (gross_win / gross_loss) if gross_loss > 0 else (None if gross_win == 0 else float("inf"))

    # Kelly edge = p*b - (1-p), where b = avg_win / |avg_loss|
    # If avg_loss == 0 and there are losses, skip (undefined). If no losses, edge
    # trivially positive — fall back to using 1 as denominator (conservative).
    kelly = None
    if losses == 0 and wins > 0:
        # No losses yet — edge is >= 0 but undefined in classic form. Report None
        # so we don't trigger DEMOTE on insufficient loss sample.
        kelly = None
    elif avg_loss < 0:
        b = avg_win / abs(avg_loss)
        kelly = wr * b - (1 - wr)
    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "wr": wr,
        "wilson_lo": wlo,
        "wilson_hi": whi,
        "mean_pnl_pip": mean_pnl,
        "avg_win_pip": avg_win,
        "avg_loss_pip": avg_loss,
        "profit_factor": pf,
        "kelly_edge": kelly,
    }


def verdict_for(metrics: dict[str, Any]) -> str:
    """CLAUDE.md protocol:
      N < 30                         -> WATCH
      N >= 30 AND kelly_edge < 0     -> DEMOTE_CANDIDATE
      N >= 30 AND kelly_edge is None -> WATCH (insufficient loss sample)
      N >= 30 AND kelly_edge >= 0    -> HOLD
    """
    n = metrics["n"]
    if n < MIN_N_FOR_JUDGMENT:
        return "WATCH"
    k = metrics["kelly_edge"]
    if k is None:
        return "WATCH"
    if k < 0:
        return "DEMOTE_CANDIDATE"
    return "HOLD"


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------
def _fmt(val: Any, spec: str = ".4f") -> str:
    if val is None:
        return "n/a"
    if isinstance(val, float) and (math.isinf(val) or math.isnan(val)):
        return str(val)
    try:
        return format(val, spec)
    except Exception:
        return str(val)


def render_markdown(results: dict[str, dict[str, Any]], now: datetime, api: str) -> str:
    lines: list[str] = []
    lines.append(f"# Post-Promotion Watchdog — {now.date().isoformat()}")
    lines.append("")
    lines.append(f"- Generated: `{now.isoformat()}`")
    lines.append(f"- Source: `{api}/api/demo/trades?limit={DEFAULT_LIMIT}`")
    lines.append(f"- Judgment threshold: Live N >= {MIN_N_FOR_JUDGMENT} AND Kelly edge < 0 -> DEMOTE_CANDIDATE")
    lines.append("- XAU excluded (per feedback_exclude_xau memory)")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Cell | N | WR | Wilson 95% CI | Mean PnL (pip) | PF | Kelly | Verdict |")
    lines.append("|------|---|----|---------------|----------------|----|----|---------|")
    for key, data in results.items():
        m = data["metrics"]
        wr_pct = f"{m['wr']*100:.1f}%"
        ci = f"[{m['wilson_lo']*100:.1f}%, {m['wilson_hi']*100:.1f}%]"
        pf_str = _fmt(m["profit_factor"], ".2f")
        kelly_str = _fmt(m["kelly_edge"], "+.4f")
        lines.append(
            f"| `{key}` | {m['n']} | {wr_pct} | {ci} | "
            f"{m['mean_pnl_pip']:+.2f} | {pf_str} | {kelly_str} | **{data['verdict']}** |"
        )
    lines.append("")
    for key, data in results.items():
        m = data["metrics"]
        lines.append(f"## {key}")
        lines.append("")
        lines.append(f"- Promoted at: `{data['promoted_at']}`")
        lines.append(f"- Post-promotion trades: N = {m['n']} (wins={m['wins']}, losses={m['losses']})")
        lines.append(f"- WR = {m['wr']*100:.2f}%  (Wilson 95% CI: {m['wilson_lo']*100:.2f}% - {m['wilson_hi']*100:.2f}%)")
        lines.append(f"- Mean PnL per trade: {m['mean_pnl_pip']:+.3f} pip")
        lines.append(f"- avg_win_pip (b numerator) = {m['avg_win_pip']:.3f}")
        lines.append(f"- avg_loss_pip              = {m['avg_loss_pip']:.3f}")
        lines.append(f"- Profit factor = {_fmt(m['profit_factor'], '.3f')}")
        lines.append(f"- Kelly edge    = {_fmt(m['kelly_edge'], '+.5f')}")
        lines.append(f"- **Verdict: {data['verdict']}**")
        if data["verdict"] == "DEMOTE_CANDIDATE":
            lines.append("")
            lines.append("  > ACTION: Prepare DEMOTE proposal. Cross-check with "
                         "`tier_integrity_check.py` and a fresh 365d BT before "
                         "writing tier_master.md.")
        elif data["verdict"] == "WATCH":
            remaining = max(0, MIN_N_FOR_JUDGMENT - m["n"])
            lines.append(f"")
            lines.append(f"  > Need {remaining} more closed trades before judgment.")
        lines.append("")
    return "\n".join(lines) + "\n"


def write_report(markdown: str, now: datetime) -> Path:
    MONITORS_DIR.mkdir(parents=True, exist_ok=True)
    out = MONITORS_DIR / f"post-promotion-{now.date().isoformat()}.md"
    out.write_text(markdown, encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Core driver
# ---------------------------------------------------------------------------
def run(
    trades: list[dict],
    *,
    cells: list[dict[str, str]] = WATCHED_CELLS,
    now: datetime | None = None,
    api_for_report: str = DEFAULT_API,
    write_md: bool = True,
) -> tuple[dict[str, dict[str, Any]], int, Path | None]:
    """Pure function so the smoke test can reuse the exact same path."""
    now = now or datetime.now(timezone.utc)
    results: dict[str, dict[str, Any]] = {}
    any_demote = False
    for cell in cells:
        et = cell["entry_type"]
        pair = cell["instrument"]
        promoted_at = parse_iso(cell["promoted_at"])
        if promoted_at is None:
            print(
                f"ERROR: bad promoted_at for {et} x {pair}: {cell['promoted_at']!r}",
                file=sys.stderr,
            )
            sys.exit(2)
        cell_trades = filter_cell_trades(
            trades,
            entry_type=et,
            instrument=pair,
            promoted_at=promoted_at,
        )
        metrics = compute_cell_metrics(cell_trades)
        v = verdict_for(metrics)
        if v == "DEMOTE_CANDIDATE":
            any_demote = True
        key = f"{et} x {pair}"
        results[key] = {
            "entry_type": et,
            "instrument": pair,
            "promoted_at": cell["promoted_at"],
            "metrics": metrics,
            "verdict": v,
        }
    report_path: Path | None = None
    if write_md:
        md = render_markdown(results, now, api_for_report)
        report_path = write_report(md, now)
    exit_code = 1 if any_demote else 0
    return results, exit_code, report_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _cli() -> int:
    ap = argparse.ArgumentParser(
        description="Post-promotion Live Kelly-gate watchdog for PAIR_PROMOTED cells."
    )
    ap.add_argument("--api", default=DEFAULT_API, help="API base URL (default: Render production)")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Max trades to fetch")
    ap.add_argument("--json-only", action="store_true",
                    help="Only emit JSON to stdout (markdown report still written)")
    ap.add_argument("--no-report", action="store_true",
                    help="Skip writing the markdown report")
    ap.add_argument("--smoke", action="store_true",
                    help="Dry-run with synthetic fixtures (no network)")
    args = ap.parse_args()

    if args.smoke:
        return _smoke_test()

    trades = fetch_trades(args.api, limit=args.limit)
    results, exit_code, report_path = run(
        trades,
        api_for_report=args.api,
        write_md=not args.no_report,
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api": args.api,
        "report_path": str(report_path) if report_path else None,
        "cells": {
            k: {
                "entry_type": v["entry_type"],
                "instrument": v["instrument"],
                "promoted_at": v["promoted_at"],
                "verdict": v["verdict"],
                **v["metrics"],
            }
            for k, v in results.items()
        },
        "exit_code": exit_code,
    }
    print(json.dumps(payload, indent=2, default=str))
    if not args.json_only and report_path is not None:
        print(f"\n[watchdog] report written to {report_path}", file=sys.stderr)
    return exit_code


# ---------------------------------------------------------------------------
# Smoke test (network-less dry-run)
# ---------------------------------------------------------------------------
def _smoke_test() -> int:
    """Synthetic fixture that exercises every verdict branch.

    Cell 1 (streak_reversal x USD_JPY): 32 trades, negative Kelly -> DEMOTE_CANDIDATE
    Cell 2 (vwap_mean_reversion x USD_JPY): 12 trades -> WATCH
    Plus noise rows that MUST be filtered (XAU, shadow, PENDING, pre-promotion).
    """
    promoted = "2026-04-22T12:00:00+00:00"
    fake: list[dict] = []

    # --- streak_reversal x USD_JPY: 32 trades, 10 wins @ +8pip, 22 losses @ -10pip
    # WR = 0.3125, b = 8/10 = 0.8, kelly = 0.3125*0.8 - 0.6875 = -0.4375 < 0 -> DEMOTE
    for i in range(10):
        fake.append({
            "entry_type": "streak_reversal", "instrument": "USD_JPY",
            "is_shadow": 0, "status": "CLOSED", "pnl_pips": 8.0,
            "created_at": f"2026-04-22T13:{i:02d}:00Z",
        })
    for i in range(22):
        fake.append({
            "entry_type": "streak_reversal", "instrument": "USD_JPY",
            "is_shadow": 0, "status": "CLOSED", "pnl_pips": -10.0,
            "created_at": f"2026-04-22T14:{i:02d}:00Z",
        })

    # --- vwap_mean_reversion x USD_JPY: only 12 trades -> WATCH
    for i in range(7):
        fake.append({
            "entry_type": "vwap_mean_reversion", "instrument": "USD_JPY",
            "is_shadow": 0, "status": "CLOSED", "pnl_pips": 5.0,
            "created_at": f"2026-04-22T15:{i:02d}:00Z",
        })
    for i in range(5):
        fake.append({
            "entry_type": "vwap_mean_reversion", "instrument": "USD_JPY",
            "is_shadow": 0, "status": "CLOSED", "pnl_pips": -4.0,
            "created_at": f"2026-04-22T16:{i:02d}:00Z",
        })

    # --- Noise that MUST be filtered ---
    # XAU row
    fake.append({"entry_type": "streak_reversal", "instrument": "XAU_USD",
                 "is_shadow": 0, "status": "CLOSED", "pnl_pips": 999.0,
                 "created_at": "2026-04-22T13:00:00Z"})
    # shadow row
    fake.append({"entry_type": "streak_reversal", "instrument": "USD_JPY",
                 "is_shadow": 1, "status": "CLOSED", "pnl_pips": 999.0,
                 "created_at": "2026-04-22T13:00:00Z"})
    # PENDING row
    fake.append({"entry_type": "streak_reversal", "instrument": "USD_JPY",
                 "is_shadow": 0, "status": "PENDING", "pnl_pips": 999.0,
                 "created_at": "2026-04-22T13:00:00Z"})
    # pre-promotion row
    fake.append({"entry_type": "streak_reversal", "instrument": "USD_JPY",
                 "is_shadow": 0, "status": "CLOSED", "pnl_pips": 999.0,
                 "created_at": "2026-04-21T12:00:00Z"})
    # different pair
    fake.append({"entry_type": "streak_reversal", "instrument": "EUR_USD",
                 "is_shadow": 0, "status": "CLOSED", "pnl_pips": 999.0,
                 "created_at": "2026-04-22T13:00:00Z"})

    cells = [
        {"entry_type": "streak_reversal", "instrument": "USD_JPY",
         "promoted_at": promoted},
        {"entry_type": "vwap_mean_reversion", "instrument": "USD_JPY",
         "promoted_at": promoted},
    ]
    now = datetime(2026, 4, 22, 18, 0, tzinfo=timezone.utc)
    results, exit_code, report_path = run(
        fake, cells=cells, now=now,
        api_for_report="smoke://dry-run", write_md=False,
    )

    # Render a summary to stdout so the smoke test is verifiable visually.
    print("=== post_promotion_watchdog SMOKE TEST ===")
    print(f"now={now.isoformat()}  cells={len(results)}  report_written={report_path is not None}")
    for key, data in results.items():
        m = data["metrics"]
        print(f"- {key}: N={m['n']} WR={m['wr']*100:.1f}% "
              f"kelly={_fmt(m['kelly_edge'], '+.4f')} -> {data['verdict']}")
    print(f"(exit_code would be {exit_code})")

    # Hard-coded expectations for the fixture above.
    c1 = results["streak_reversal x USD_JPY"]
    c2 = results["vwap_mean_reversion x USD_JPY"]
    assert c1["metrics"]["n"] == 32, f"c1.n expected 32 got {c1['metrics']['n']}"
    assert c1["verdict"] == "DEMOTE_CANDIDATE", f"c1 verdict = {c1['verdict']}"
    assert c2["metrics"]["n"] == 12, f"c2.n expected 12 got {c2['metrics']['n']}"
    assert c2["verdict"] == "WATCH", f"c2 verdict = {c2['verdict']}"
    assert exit_code == 1, f"exit_code expected 1 got {exit_code}"
    print("smoke: OK (all asserts passed)")
    # Smoke test should return 0 regardless of simulated DEMOTE verdict —
    # this is a dry-run self-check, not a real monitoring run.
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
