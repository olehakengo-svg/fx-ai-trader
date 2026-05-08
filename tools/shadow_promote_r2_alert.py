#!/usr/bin/env python3
"""Read-only R2 alert for SHADOW_PROMOTE redesign-v2 strategies.

Fetches Render /api/demo/trades, keeps recent closed Shadow trades, aggregates
(strategy, instrument) cells, writes a markdown audit, and alerts Discord only
for CRITICAL cells. It never edits Render env vars, strategy code, tier-master,
or any production database state.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_API = "https://fx-ai-trader.onrender.com"
DEFAULT_LIMIT = 2000
LOOKBACK_DAYS = 30
WARN_MIN_N = 10
CRITICAL_MIN_N = 30
REPORT_DIR = _PROJECT_ROOT / "knowledge-base" / "raw" / "audits"
REGISTRY_PATH = _PROJECT_ROOT / "modules" / "shadow_demote_registry.py"

PROMOTE_ENV_RE = re.compile(r'os\.environ\.get\("([A-Z0-9_]+_REDESIGN_V2_SHADOW_PROMOTE)"\)')
UNION_RE = re.compile(r"_shadow_always\s*=\s*_shadow_always\s*\|\s*\{([^}]+)\}")
STRING_RE = re.compile(r'"([^"]+)"')
ENV_KEY_RE = re.compile(r"^[A-Z0-9_]+_REDESIGN_V2_SHADOW_PROMOTE$")


class ApiError(RuntimeError):
    """Network/API failure that maps to exit code 2."""


_ALLOWED_SCHEMES = ("http", "https")
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = True
_SSL_CTX.verify_mode = ssl.CERT_REQUIRED
_SAFE_OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(context=_SSL_CTX),
)


def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ApiError(f"Refusing non-http(s) URL scheme: {parsed.scheme!r}")
    if not parsed.netloc:
        raise ApiError(f"URL must include a hostname (url={url!r})")


def parse_iso(ts: Any) -> datetime | None:
    if not ts:
        return None
    text = str(ts)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except Exception:
            return None


def fetch_trades(api: str = DEFAULT_API, limit: int = DEFAULT_LIMIT) -> list[dict]:
    url = f"{api.rstrip('/')}/api/demo/trades?limit={int(limit)}"
    _validate_url(url)
    req = urllib.request.Request(
        url, headers={"User-Agent": "shadow-promote-r2-alert/1.0"}
    )
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with _SAFE_OPENER.open(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        raise ApiError(f"API fetch failed ({type(e).__name__}: {e})") from e
    if isinstance(payload, dict):
        trades = payload.get("trades", []) or []
    elif isinstance(payload, list):
        trades = payload
    else:
        trades = []
    if not isinstance(trades, list):
        raise ApiError("API response has non-list trades payload")
    return [t for t in trades if isinstance(t, dict)]


def discover_shadow_promote_mapping(
    strategy_init_paths: list[Path] | None = None,
) -> dict[str, list[str]]:
    """Map *_SHADOW_PROMOTE env keys to entry_type names via split_shadow_always."""
    if strategy_init_paths is None:
        paths = sorted((_PROJECT_ROOT / "strategies").glob("*/__init__.py"))
    else:
        paths = strategy_init_paths

    mapping: dict[str, list[str]] = {}
    for path in paths:
        pending_envs: list[str] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            pending_envs.extend(PROMOTE_ENV_RE.findall(line))
            union = UNION_RE.search(line)
            if not union:
                continue
            strategies = STRING_RE.findall(union.group(1))
            for env_key in pending_envs:
                bucket = mapping.setdefault(env_key, [])
                for strategy in strategies:
                    if strategy not in bucket:
                        bucket.append(strategy)
            pending_envs = []
    return mapping


def active_shadow_promote_strategies(
    environ: dict[str, str] | None = None,
    mapping: dict[str, list[str]] | None = None,
) -> list[dict[str, str]]:
    env = environ if environ is not None else os.environ
    mapping = mapping if mapping is not None else discover_shadow_promote_mapping()
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for env_key, value in sorted(env.items()):
        if value != "1" or not ENV_KEY_RE.match(env_key):
            continue
        strategies = mapping.get(env_key) or [env_key.removesuffix("_REDESIGN_V2_SHADOW_PROMOTE").lower()]
        for strategy in strategies:
            item = (strategy, env_key)
            if item in seen:
                continue
            seen.add(item)
            out.append({"strategy": strategy, "env_key": env_key})
    return out


def all_static_shadow_promote_strategies(
    mapping: dict[str, list[str]] | None = None,
) -> list[dict[str, str]]:
    mapping = mapping if mapping is not None else discover_shadow_promote_mapping()
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for env_key, strategies in sorted(mapping.items()):
        for strategy in strategies:
            item = (strategy, env_key)
            if item in seen:
                continue
            seen.add(item)
            out.append({"strategy": strategy, "env_key": env_key})
    return out


def _trade_time(trade: dict) -> datetime | None:
    for key in ("close_time", "closed_at", "exit_time", "updated_at", "created_at", "entry_time"):
        dt = parse_iso(trade.get(key))
        if dt is not None:
            return dt
    return None


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_xau_instrument(instrument: str) -> bool:
    return "XAU" in instrument.upper()


def filter_shadow_trades(
    trades: list[dict],
    promoted_strategies: list[dict[str, str]],
    *,
    now: datetime,
    lookback_days: int = LOOKBACK_DAYS,
) -> list[dict]:
    strategy_set = {s["strategy"] for s in promoted_strategies}
    since = now - timedelta(days=lookback_days)
    kept: list[dict] = []
    for trade in trades:
        strategy = str(trade.get("entry_type") or trade.get("strategy") or "")
        instrument = str(trade.get("instrument") or "")
        pnl = _float_or_none(trade.get("pnl_pips"))
        ts = _trade_time(trade)
        if strategy not in strategy_set:
            continue
        if is_xau_instrument(instrument):
            continue
        if int(trade.get("is_shadow", 0) or 0) != 1:
            continue
        if pnl is None:
            continue
        if ts is None or ts < since or ts > now:
            continue
        row = dict(trade)
        row["entry_type"] = strategy
        row["instrument"] = instrument
        row["pnl_pips"] = pnl
        kept.append(row)
    return kept


def wilson_interval(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt((p * (1 - p) / n) + (z * z / (4 * n * n)))) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def compute_metrics(pnls: list[float]) -> dict[str, Any]:
    n = len(pnls)
    if n == 0:
        return {
            "n": 0,
            "wins": 0,
            "losses": 0,
            "wr": 0.0,
            "wilson_lo": 0.0,
            "wilson_hi": 0.0,
            "ev": 0.0,
            "gross_win_pips": 0.0,
            "gross_loss_pips": 0.0,
            "profit_factor": None,
        }
    wins_list = [p for p in pnls if p > 0]
    losses_list = [p for p in pnls if p <= 0]
    wins = len(wins_list)
    gross_win = sum(wins_list)
    gross_loss = -sum(losses_list)
    pf = (gross_win / gross_loss) if gross_loss > 0 else None
    wlo, whi = wilson_interval(wins, n)
    return {
        "n": n,
        "wins": wins,
        "losses": len(losses_list),
        "wr": wins / n,
        "wilson_lo": wlo,
        "wilson_hi": whi,
        "ev": sum(pnls) / n,
        "gross_win_pips": gross_win,
        "gross_loss_pips": gross_loss,
        "profit_factor": pf,
    }


def severity_for(metrics: dict[str, Any]) -> str:
    if metrics["n"] >= CRITICAL_MIN_N and metrics["ev"] < 0:
        return "CRITICAL"
    if metrics["n"] >= WARN_MIN_N and metrics["ev"] < 0:
        return "WARN"
    return "OK"


def aggregate_cells(
    trades: list[dict],
    promoted_strategies: list[dict[str, str]],
) -> list[dict[str, Any]]:
    by_cell: dict[tuple[str, str], list[float]] = defaultdict(list)
    env_by_strategy: dict[str, list[str]] = defaultdict(list)
    for item in promoted_strategies:
        env_by_strategy[item["strategy"]].append(item["env_key"])
    for trade in trades:
        by_cell[(trade["entry_type"], trade["instrument"])].append(float(trade["pnl_pips"]))

    cells: list[dict[str, Any]] = []
    strategies = sorted({s["strategy"] for s in promoted_strategies})
    for strategy in strategies:
        instruments = sorted(inst for (s, inst) in by_cell if s == strategy)
        if not instruments:
            metrics = compute_metrics([])
            cells.append({
                "strategy": strategy,
                "instrument": None,
                "env_keys": sorted(set(env_by_strategy[strategy])),
                "severity": severity_for(metrics),
                **metrics,
            })
            continue
        for instrument in instruments:
            metrics = compute_metrics(by_cell[(strategy, instrument)])
            cells.append({
                "strategy": strategy,
                "instrument": instrument,
                "env_keys": sorted(set(env_by_strategy[strategy])),
                "severity": severity_for(metrics),
                **metrics,
            })
    return cells


def summarize(cells: list[dict[str, Any]], promoted_count: int) -> dict[str, Any]:
    warn = [c for c in cells if c["severity"] == "WARN"]
    critical = [c for c in cells if c["severity"] == "CRITICAL"]
    ok = [c for c in cells if c["severity"] == "OK"]
    return {
        "promoted_strategy_count": promoted_count,
        "cell_count": len(cells),
        "ok_count": len(ok),
        "warn_count": len(warn),
        "critical_count": len(critical),
    }


def _fmt_float(value: Any, spec: str = ".3f") -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and math.isinf(value):
        return "inf"
    try:
        return format(value, spec)
    except Exception:
        return str(value)


def render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines: list[str] = []
    lines.append(f"# SHADOW_PROMOTE R2 Alert - {result['generated_at']}")
    lines.append("")
    lines.append(f"- Source: `{result['source_url']}`")
    lines.append(f"- Lookback: `{result['lookback_days']}d`")
    lines.append("- Filters: `is_shadow=1`, `pnl_pips IS NOT NULL`, XAU instruments excluded")
    lines.append("- Gate: `N >= 10 and EV < 0` -> WARN; `N >= 30 and EV < 0` -> CRITICAL")
    lines.append("- Mode: read-only; no env vars, strategy code, tier-master, or DB writes")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Promoted strategies: {summary['promoted_strategy_count']}")
    lines.append(f"- Cells: {summary['cell_count']}")
    lines.append(f"- OK: {summary['ok_count']}")
    lines.append(f"- WARN: {summary['warn_count']}")
    lines.append(f"- CRITICAL: {summary['critical_count']}")
    lines.append("")
    lines.append("## WARN / CRITICAL")
    lines.append("")
    flagged = [c for c in result["cells"] if c["severity"] in ("WARN", "CRITICAL")]
    if not flagged:
        lines.append("No WARN or CRITICAL cells.")
    else:
        lines.append("| Severity | Strategy | Instrument | N | EV | WR | Wilson lower | PF |")
        lines.append("|---|---|---|---:|---:|---:|---:|---:|")
        for cell in flagged:
            lines.append(
                f"| **{cell['severity']}** | `{cell['strategy']}` | `{cell['instrument'] or '-'}` | "
                f"{cell['n']} | {cell['ev']:+.3f} | {cell['wr']*100:.1f}% | "
                f"{cell['wilson_lo']*100:.1f}% | {_fmt_float(cell['profit_factor'], '.2f')} |"
            )
    lines.append("")
    lines.append("## R2 Demote Manual Action")
    lines.append("")
    lines.append("For each CRITICAL cell, manually verify and then remove the relevant Render env var:")
    lines.append("")
    for cell in [c for c in result["cells"] if c["severity"] == "CRITICAL"]:
        envs = ", ".join(f"`{e}`" for e in cell["env_keys"])
        lines.append(f"- `{cell['strategy']}` x `{cell['instrument']}`: remove {envs}")
    if summary["critical_count"] == 0:
        lines.append("- No CRITICAL cells at this run.")
    lines.append("")
    lines.append("Code review locations if manual demotion is chosen:")
    lines.append("- `strategies/daytrade/__init__.py` `split_shadow_always` / `SHADOW_ALWAYS_STRATEGIES`")
    lines.append("- `strategies/hourly/__init__.py` `split_shadow_always`")
    lines.append("- `strategies/scalp/__init__.py` `split_shadow_always`")
    suggestion = result.get("apply_demote_suggestion") or {}
    if suggestion:
        lines.append("")
        lines.append("## Apply Demote Suggestion")
        lines.append("")
        lines.append(f"- Registry: `{suggestion['registry_path']}`")
        lines.append(f"- Missing CRITICAL cells: `{len(suggestion['missing_cells'])}`")
        for strategy, instrument in suggestion["missing_cells"]:
            lines.append(f"- Add `({strategy!r}, {instrument!r})`")
    lines.append("")
    lines.append("## All Cells")
    lines.append("")
    lines.append("| Severity | Strategy | Instrument | N | Wins | Losses | EV | WR | Wilson 95% | PF | Env |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for cell in result["cells"]:
        ci = f"{cell['wilson_lo']*100:.1f}%-{cell['wilson_hi']*100:.1f}%"
        envs = "<br>".join(f"`{e}`" for e in cell["env_keys"])
        lines.append(
            f"| {cell['severity']} | `{cell['strategy']}` | `{cell['instrument'] or '-'}` | "
            f"{cell['n']} | {cell['wins']} | {cell['losses']} | {cell['ev']:+.3f} | "
            f"{cell['wr']*100:.1f}% | {ci} | {_fmt_float(cell['profit_factor'], '.2f')} | {envs} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_apply_demote_suggestion(
    cells: list[dict[str, Any]],
    *,
    registry_path: Path = REGISTRY_PATH,
) -> dict[str, Any]:
    """Return read-only registry additions for currently CRITICAL cells."""
    try:
        from modules.shadow_demote_registry import SHADOW_DEMOTED_CELLS
    except Exception:
        existing: set[tuple[str, str]] = set()
    else:
        existing = set(SHADOW_DEMOTED_CELLS)
    critical_cells = sorted(
        (str(c["strategy"]), str(c["instrument"]))
        for c in cells
        if c["severity"] == "CRITICAL" and c.get("instrument")
    )
    missing = [cell for cell in critical_cells if cell not in existing]
    return {
        "mode": "read_only",
        "registry_path": str(registry_path),
        "critical_cells": critical_cells,
        "existing_cells": sorted(existing),
        "missing_cells": missing,
        "note": "Review these cells and edit modules/shadow_demote_registry.py in a separate human-approved change.",
    }


def write_report(markdown: str, now: datetime, report_dir: Path = REPORT_DIR) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / f"shadow-promote-r2-alert-{now.strftime('%Y-%m-%d-%H%M')}.md"
    out.write_text(markdown, encoding="utf-8")
    return out


def send_discord_alert(
    critical_cells: list[dict[str, Any]],
    *,
    webhook_url: str | None = None,
    report_path: Path | None = None,
    opener: Any = _SAFE_OPENER,
) -> bool:
    if not critical_cells:
        return False
    lines = [
        f"SHADOW_PROMOTE R2 CRITICAL: {len(critical_cells)} cell(s)",
    ]
    if report_path is not None:
        lines.append(f"Report: {report_path}")
    for cell in critical_cells[:20]:
        lines.append(
            f"- {cell['strategy']} x {cell['instrument']}: "
            f"N={cell['n']} EV={cell['ev']:+.3f} WR={cell['wr']*100:.1f}%"
        )
    content = "\n".join(lines)
    if not webhook_url:
        print(content, file=sys.stderr)
        return False
    _validate_url(webhook_url)
    body = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "shadow-promote-r2-alert/1.0"},
        method="POST",
    )
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with opener.open(req, timeout=15):
            return True
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"WARNING: Discord alert failed ({type(e).__name__}: {e})", file=sys.stderr)
        return False


def run(
    trades: list[dict],
    promoted_strategies: list[dict[str, str]],
    *,
    now: datetime | None = None,
    api: str = DEFAULT_API,
    limit: int = DEFAULT_LIMIT,
    lookback_days: int = LOOKBACK_DAYS,
    write_md: bool = True,
    report_dir: Path = REPORT_DIR,
    alert_discord: bool = False,
    webhook_url: str | None = None,
    apply_demote: bool = False,
) -> tuple[dict[str, Any], int]:
    now = now or datetime.now(timezone.utc)
    filtered = filter_shadow_trades(
        trades, promoted_strategies, now=now, lookback_days=lookback_days
    )
    cells = aggregate_cells(filtered, promoted_strategies)
    result: dict[str, Any] = {
        "generated_at": now.isoformat(),
        "source_url": f"{api.rstrip('/')}/api/demo/trades?limit={int(limit)}",
        "lookback_days": lookback_days,
        "summary": summarize(cells, promoted_count=len({s["strategy"] for s in promoted_strategies})),
        "promoted_strategies": promoted_strategies,
        "cells": cells,
        "report_path": None,
        "discord_alert_sent": False,
        "apply_demote_suggestion": None,
    }
    if apply_demote:
        result["apply_demote_suggestion"] = build_apply_demote_suggestion(cells)
    if write_md:
        result["report_path"] = str(write_report(render_markdown(result), now, report_dir))
    critical = [c for c in cells if c["severity"] == "CRITICAL"]
    if alert_discord:
        result["discord_alert_sent"] = send_discord_alert(
            critical,
            webhook_url=webhook_url,
            report_path=Path(result["report_path"]) if result["report_path"] else None,
        )
    return result, (1 if critical else 0)


def _smoke_trades(now: datetime) -> tuple[list[dict], list[dict[str, str]]]:
    promoted = [
        {"strategy": "n9_no_alert", "env_key": "N9_NO_ALERT_REDESIGN_V2_SHADOW_PROMOTE"},
        {"strategy": "n10_warn", "env_key": "N10_WARN_REDESIGN_V2_SHADOW_PROMOTE"},
        {"strategy": "n30_critical", "env_key": "N30_CRITICAL_REDESIGN_V2_SHADOW_PROMOTE"},
        {"strategy": "n30_positive", "env_key": "N30_POSITIVE_REDESIGN_V2_SHADOW_PROMOTE"},
    ]
    rows: list[dict] = []

    def add(strategy: str, n: int, pnl: float, instrument: str = "USD_JPY") -> None:
        for i in range(n):
            rows.append({
                "entry_type": strategy,
                "instrument": instrument,
                "is_shadow": 1,
                "pnl_pips": pnl,
                "created_at": (now - timedelta(hours=1, minutes=i)).isoformat(),
            })

    add("n9_no_alert", 9, -1.0)
    add("n10_warn", 10, -1.0)
    add("n30_critical", 30, -0.5)
    add("n30_positive", 30, 0.5)
    add("n30_critical", 30, -99.0, instrument="XAU_USD")
    rows.append({
        "entry_type": "n30_critical",
        "instrument": "USD_JPY",
        "is_shadow": 0,
        "pnl_pips": -99.0,
        "created_at": now.isoformat(),
    })
    return rows, promoted


def _smoke_test() -> int:
    now = datetime(2026, 5, 7, 0, 0, tzinfo=timezone.utc)
    trades, promoted = _smoke_trades(now)
    result, exit_code = run(
        trades,
        promoted,
        now=now,
        write_md=False,
        alert_discord=False,
    )
    sev = {(c["strategy"], c["instrument"]): c["severity"] for c in result["cells"]}
    assert sev[("n9_no_alert", "USD_JPY")] == "OK"
    assert sev[("n10_warn", "USD_JPY")] == "WARN"
    assert sev[("n30_critical", "USD_JPY")] == "CRITICAL"
    assert sev[("n30_positive", "USD_JPY")] == "OK"
    assert exit_code == 1
    print(json.dumps(result["summary"], indent=2))
    print("smoke: OK")
    return 0


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and math.isinf(value):
        return "inf"
    return str(value)


def cli(fetcher: Callable[[str, int], list[dict]] = fetch_trades) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only SHADOW_PROMOTE R2 alert for recent Shadow EV<0 cells."
    )
    parser.add_argument("--api", default=DEFAULT_API, help="API base URL")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Max trades to fetch")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON to stdout")
    parser.add_argument("--no-report", action="store_true", help="Do not write markdown report")
    parser.add_argument("--include-all-static", action="store_true",
                        help="Audit all statically discovered SHADOW_PROMOTE strategies, ignoring env values")
    parser.add_argument("--no-discord", action="store_true",
                        help="Do not send Discord webhook alerts")
    parser.add_argument("--apply-demote", action="store_true",
                        help="Read-only: include suggested registry additions for CRITICAL cells")
    parser.add_argument("--smoke", action="store_true", help="Run synthetic fixture checks without network")
    args = parser.parse_args()

    if args.smoke:
        return _smoke_test()

    mapping = discover_shadow_promote_mapping()
    promoted = (
        all_static_shadow_promote_strategies(mapping)
        if args.include_all_static
        else active_shadow_promote_strategies(os.environ, mapping)
    )
    if not promoted:
        print(
            "WARNING: no *_REDESIGN_V2_SHADOW_PROMOTE=1 env vars found; "
            "report will contain zero strategies. Use --include-all-static for local audit.",
            file=sys.stderr,
        )

    try:
        trades = fetcher(args.api, args.limit)
    except ApiError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    result, exit_code = run(
        trades,
        promoted,
        api=args.api,
        limit=args.limit,
        write_md=not args.no_report,
        alert_discord=not args.no_discord,
        webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"),
        apply_demote=args.apply_demote,
    )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=_json_default))
    else:
        s = result["summary"]
        print(
            f"[shadow_promote_r2_alert] strategies={s['promoted_strategy_count']} "
            f"cells={s['cell_count']} OK={s['ok_count']} WARN={s['warn_count']} "
            f"CRITICAL={s['critical_count']} report={result['report_path']}"
        )
    return exit_code


if __name__ == "__main__":
    sys.exit(cli())
