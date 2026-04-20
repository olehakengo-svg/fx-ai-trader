#!/usr/bin/env python3
"""
Quant Readiness Dashboard — one-shot state snapshot for session start.

Usage:
    python3 tools/quant_readiness.py                 # human-readable
    python3 tools/quant_readiness.py --json          # machine-readable
    python3 tools/quant_readiness.py --api http://localhost:8000

Fetches canonical metrics from the production API (Render) and reports
data-accumulation, gate-threshold, and regime-coverage status in one
glance. Designed to prevent "Live N=14 forgetfulness" at session start.

Gate thresholds are pre-committed (see knowledge-base/wiki/syntheses/
roadmap-v2.1.md + analyses/regime-2d-v2-preregister-2026-04-20.md):

    Kelly eligible        Live N >= 20
    DSR significant       N >= 50 (clean) with |sharpe| > threshold
    PP review candidate   shadow N >= 30 per (strategy, pair) AND EV > 0
    FD risk               Live N >= 30 AND EV < -0.5 per strategy

Offline grace-degradation: network failures produce an explicit error row
rather than silent success.

Exit codes:
    0 = all fetches succeeded
    1 = at least one metric failed (dashboard still printed)
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

DEFAULT_API = "https://fx-ai-trader.onrender.com"

# Post-Clean-Slate cutoff (matches modules/demo_trader.py / daily_report.py)
FIDELITY_CUTOFF = "2026-04-16"

# Pre-committed gate thresholds
KELLY_MIN_N = 20
DSR_MIN_N = 50
PP_REVIEW_MIN_SHADOW_N = 30
FD_RISK_MIN_LIVE_N = 30
FD_RISK_EV_THRESHOLD = -0.5
REGIME_COVERAGE_TARGET = 0.80   # 80% non-empty mtf_regime
REGIME_COVERAGE_WARN = 0.50

REGIMES_ALL = (
    "trend_up_strong", "trend_up_weak",
    "trend_down_weak", "trend_down_strong",
    "range_tight", "range_wide", "uncertain",
)


# ── Fetch helpers ────────────────────────────────────────────────────────────
# Allowlist of URL schemes to prevent file:// / ftp:// / gopher:// read via --api.
# (Semgrep: CWE-939. Dynamic --api value is validated before any urllib call.)
_ALLOWED_SCHEMES = ("http", "https")


def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"Refusing to fetch URL with scheme {parsed.scheme!r}. "
            f"Only {_ALLOWED_SCHEMES} are allowed."
        )
    if not parsed.netloc:
        raise ValueError(f"URL must include a network host: {url!r}")


# Module-scope opener: handlers are fixed at module load (not user-controlled).
# By building a custom OpenerDirector with ONLY HTTPHandler + HTTPSHandler (the
# latter pinned to a verified default SSL context), we eliminate the ability
# for a malicious --api value to pivot to file:// / ftp:// / gopher:// schemes.
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = True
_SSL_CTX.verify_mode = ssl.CERT_REQUIRED
_SAFE_OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(context=_SSL_CTX),
)


def _http_get_json(url: str, timeout: float = 15.0) -> dict:
    """Fetch JSON over HTTP/HTTPS only.

    CWE-939 mitigation: `_validate_url` enforces http/https scheme; the module
    opener has only HTTP/HTTPS handlers registered (no file/ftp/gopher).
    CWE-295 mitigation: HTTPSHandler uses create_default_context (verified).
    """
    _validate_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "quant_readiness/1.0"})
    # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
    with _SAFE_OPENER.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_metric(base: str, path: str, **params: Any) -> tuple[dict, str | None]:
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{base.rstrip('/')}{path}" + (f"?{qs}" if qs else "")
    try:
        return _http_get_json(url), None
    except urllib.error.HTTPError as e:
        return {}, f"HTTP {e.code}: {url}"
    except urllib.error.URLError as e:
        return {}, f"URLError: {e.reason} ({url})"
    except (socket.timeout, socket.gaierror, ConnectionError) as e:
        return {}, f"Network: {e} ({url})"
    except ValueError as e:
        return {}, f"Invalid URL: {e}"
    except Exception as e:  # noqa: BLE001
        return {}, f"{type(e).__name__}: {e}"


# ── Metric builders ──────────────────────────────────────────────────────────
def build_accumulation(live: dict, shadow: dict) -> dict:
    live_n = int(live.get("total") or live.get("live_count") or 0)
    # shadow-included stats: total - live_count = shadow_count
    shadow_only = int(shadow.get("shadow_count") or 0)
    if not shadow_only:
        total = int(shadow.get("total") or 0)
        live_in_shadow_view = int(shadow.get("live_count") or live_n)
        shadow_only = max(0, total - live_in_shadow_view)
    return {
        "live_n": live_n,
        "shadow_n": shadow_only,
        "live_pct_to_kelly": (live_n / KELLY_MIN_N) if KELLY_MIN_N else 0.0,
        "live_eligible_kelly": live_n >= KELLY_MIN_N,
    }


def build_gate(live: dict, shadow_sentinel: dict) -> dict:
    live_n = int(live.get("total") or 0)
    out = {
        "kelly": {
            "eligible": live_n >= KELLY_MIN_N,
            "live_n": live_n,
            "min_required": KELLY_MIN_N,
        },
        "dsr": {
            "eligible": live_n >= DSR_MIN_N,
            "live_n": live_n,
            "min_required": DSR_MIN_N,
        },
    }
    # PP review candidates (shadow N >= 30 AND EV > 0)
    pp_candidates: list[dict] = []
    fd_risk: list[dict] = []
    by_type_pair = shadow_sentinel.get("by_type_pair") or {}
    for key, rec in by_type_pair.items():
        n = int(rec.get("n") or 0)
        ev = float(rec.get("ev") or 0.0)
        if n >= PP_REVIEW_MIN_SHADOW_N and ev > 0:
            pp_candidates.append({
                "strategy": rec.get("entry_type") or key.split("|")[0],
                "instrument": rec.get("instrument") or key.split("|")[-1],
                "n": n, "ev": ev, "wr": float(rec.get("wr") or 0.0),
            })
    by_type_live = live.get("by_type") or {}
    for et, rec in by_type_live.items():
        n = int(rec.get("trades") or rec.get("n") or 0)
        pnl = float(rec.get("pnl") or 0.0)
        ev = pnl / n if n else 0.0
        if n >= FD_RISK_MIN_LIVE_N and ev < FD_RISK_EV_THRESHOLD:
            fd_risk.append({"strategy": et, "n": n, "ev": ev, "pnl": pnl})
    out["pp_review_candidates"] = sorted(pp_candidates,
                                          key=lambda r: r["ev"], reverse=True)
    out["fd_risk"] = sorted(fd_risk, key=lambda r: r["ev"])
    return out


def build_coverage(trades_payload: dict) -> dict:
    trades = trades_payload.get("trades") or []
    # Filter post-cutoff / FX-only (script layer; API layer doesn't filter)
    post = [t for t in trades
            if (t.get("entry_time", "") or "") >= FIDELITY_CUTOFF
            and "XAU" not in (t.get("instrument") or "")]
    total = len(post)
    labeled = sum(1 for t in post if t.get("mtf_regime"))
    regime_counts: dict[str, int] = {r: 0 for r in REGIMES_ALL}
    for t in post:
        r = t.get("mtf_regime")
        if r in regime_counts:
            regime_counts[r] += 1
    missing_regimes = [r for r, c in regime_counts.items() if c == 0]
    return {
        "total_post_cutoff": total,
        "labeled_n": labeled,
        "coverage_pct": (labeled / total) if total else 0.0,
        "regime_counts": regime_counts,
        "missing_regimes": missing_regimes,
    }


# ── Rendering ────────────────────────────────────────────────────────────────
def _icon(status: str) -> str:
    return {"ok": "[OK]", "warn": "[WARN]", "fail": "[FAIL]", "info": "[..]"}\
        .get(status, "[..]")


def _status_acc(acc: dict) -> str:
    if acc["live_n"] == 0:
        return "fail"
    if acc["live_eligible_kelly"]:
        return "ok"
    return "warn"


def _status_cov(cov: dict) -> str:
    pct = cov["coverage_pct"]
    if pct >= REGIME_COVERAGE_TARGET:
        return "ok"
    if pct >= REGIME_COVERAGE_WARN:
        return "warn"
    return "fail"


def render_text(report: dict) -> str:
    lines: list[str] = []
    lines.append("=== FX-AI-Trader Quant Readiness Dashboard ===")
    lines.append(f"Timestamp: {report['timestamp']}")
    lines.append(f"API:       {report['api']}")
    lines.append(f"Cutoff:    {FIDELITY_CUTOFF}")
    lines.append("")

    errs = [e for e in report.get("errors", []) if e]
    if errs:
        lines.append("## Fetch Errors")
        for e in errs:
            lines.append(f"  {_icon('fail')} {e}")
        lines.append("")

    acc = report.get("accumulation", {})
    lines.append("## Data Accumulation")
    if acc:
        lines.append(f"  {_icon(_status_acc(acc))} Live N (post-cutoff):   "
                     f"{acc['live_n']} / {KELLY_MIN_N} "
                     f"({acc['live_pct_to_kelly']*100:.0f}%) "
                     f"{'Kelly-eligible' if acc['live_eligible_kelly'] else 'need more'}")
        lines.append(f"  {_icon('info')} Shadow N (post-cutoff): {acc['shadow_n']}")
    else:
        lines.append(f"  {_icon('fail')} unavailable")
    lines.append("")

    gate = report.get("gate", {})
    lines.append("## Gate Thresholds")
    if gate:
        k = gate["kelly"]
        lines.append(f"  {_icon('ok' if k['eligible'] else 'fail')} "
                     f"Aggregate Kelly: Live N={k['live_n']} / min {k['min_required']}")
        d = gate["dsr"]
        lines.append(f"  {_icon('ok' if d['eligible'] else 'fail')} "
                     f"DSR significance: N={d['live_n']} / min {d['min_required']}")
        pp = gate.get("pp_review_candidates", [])
        lines.append(f"  {_icon('warn' if not pp else 'ok')} "
                     f"PP review candidates (shadow N>=30, EV>0): {len(pp)}")
        for c in pp[:5]:
            # Sentinel endpoint returns WR in percent already (0-100).
            lines.append(f"      - {c['strategy']} x {c['instrument']} "
                         f"N={c['n']} EV={c['ev']:+.2f} WR={c['wr']:.1f}%")
        fd = gate.get("fd_risk", [])
        lines.append(f"  {_icon('warn' if fd else 'ok')} "
                     f"FD-risk strategies (Live N>=30, EV<-0.5): {len(fd)}")
        for c in fd[:5]:
            lines.append(f"      - {c['strategy']} N={c['n']} EV={c['ev']:+.2f}")
    else:
        lines.append(f"  {_icon('fail')} unavailable")
    lines.append("")

    cov = report.get("coverage", {})
    lines.append("## mtf_regime Coverage")
    if cov:
        pct = cov["coverage_pct"]
        lines.append(f"  {_icon(_status_cov(cov))} coverage: "
                     f"{pct*100:.1f}% "
                     f"({cov['labeled_n']}/{cov['total_post_cutoff']}) "
                     f"[target {REGIME_COVERAGE_TARGET*100:.0f}%]")
        for r, c in cov["regime_counts"].items():
            mark = _icon("warn") if c == 0 else _icon("info")
            lines.append(f"      {mark} {r:20s} N={c}")
        if cov["missing_regimes"]:
            lines.append(f"  {_icon('warn')} missing regimes: "
                         f"{', '.join(cov['missing_regimes'])}")
    else:
        lines.append(f"  {_icon('fail')} unavailable")
    lines.append("")

    alerts = report.get("alerts") or []
    lines.append("## Alerts")
    if not alerts:
        lines.append("  (none)")
    else:
        for a in alerts:
            lines.append(f"  {_icon('warn')} {a}")
    return "\n".join(lines)


def derive_alerts(report: dict) -> list[str]:
    alerts: list[str] = []
    acc = report.get("accumulation") or {}
    cov = report.get("coverage") or {}
    gate = report.get("gate") or {}
    if acc and acc.get("live_n", 0) < KELLY_MIN_N:
        need = KELLY_MIN_N - acc["live_n"]
        alerts.append(f"Live N below Kelly threshold: need +{need} more (current {acc['live_n']}/{KELLY_MIN_N})")
    if cov and cov.get("coverage_pct", 0) < REGIME_COVERAGE_TARGET:
        alerts.append(f"mtf_regime coverage {cov['coverage_pct']*100:.1f}% < {REGIME_COVERAGE_TARGET*100:.0f}% target")
    if cov and "trend_down_strong" in cov.get("missing_regimes", []):
        alerts.append("trend_down_* regime coverage is zero — backfill required before 2D rescan")
    if gate and gate.get("fd_risk"):
        alerts.append(f"{len(gate['fd_risk'])} strategies at FD-risk threshold (Live N>=30, EV<-0.5)")
    return alerts


# ── Main ─────────────────────────────────────────────────────────────────────
def run(api: str) -> tuple[dict, list[str]]:
    errors: list[str] = []

    live_stats, err1 = fetch_metric(
        api, "/api/demo/stats",
        include_shadow=0, exclude_xau=1, date_from=FIDELITY_CUTOFF,
    )
    errors.append(err1) if err1 else None

    shadow_stats, err2 = fetch_metric(
        api, "/api/demo/stats",
        include_shadow=1, exclude_xau=1, date_from=FIDELITY_CUTOFF,
    )
    errors.append(err2) if err2 else None

    sentinel_stats, err3 = fetch_metric(
        api, "/api/sentinel/stats",
        after_date=FIDELITY_CUTOFF, exclude_xau=1,
    )
    errors.append(err3) if err3 else None

    trades_payload, err4 = fetch_metric(
        api, "/api/demo/trades",
        limit=5000, include_shadow=1, status="closed",
        date_from=FIDELITY_CUTOFF,
    )
    errors.append(err4) if err4 else None

    report: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "api": api,
        "cutoff": FIDELITY_CUTOFF,
        "errors": [e for e in errors if e],
    }
    if live_stats or shadow_stats:
        report["accumulation"] = build_accumulation(live_stats, shadow_stats)
    if live_stats or sentinel_stats:
        report["gate"] = build_gate(live_stats or {}, sentinel_stats or {})
    if trades_payload:
        report["coverage"] = build_coverage(trades_payload)
    report["alerts"] = derive_alerts(report)
    return report, [e for e in errors if e]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="FX-AI-Trader Quant Readiness Dashboard")
    p.add_argument("--api", default=DEFAULT_API, help=f"Base URL (default: {DEFAULT_API})")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = p.parse_args(argv)

    report, errors = run(args.api)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(render_text(report))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
