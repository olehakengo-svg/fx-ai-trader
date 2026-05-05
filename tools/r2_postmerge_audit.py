#!/usr/bin/env python3
"""R2 post-merge Gate 0 audit pre-registered for 2026-05-11.

Read-only. Input must be a Render `/api/demo/trades` JSON export; local DB and
OANDA credentials are intentionally not accessed.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_PREREG = ROOT / "knowledge-base/wiki/decisions/r2-postmerge-audit-prereg-2026-05-11.md"
DEFAULT_R2_LOCK = ROOT / "knowledge-base/wiki/decisions/r2-cell-demotion-lock-2026-05-03.md"

LOCKED_CELL_COUNT = 15
BONFERRONI_ALPHA = 0.05 / LOCKED_CELL_COUNT

N_ACCEPT = 30
N_NEEDS_MORE_MIN = 15
KELLY_ACCEPT = 0.005
KELLY_REJECT = -0.01
EV_ACCEPT = -0.10
EV_REJECT = -0.30
WILSON_MARGIN_REJECT = 0.03

PAIR_BEV_WR = {
    "USD_JPY": 0.344,
    "EUR_USD": 0.397,
    "GBP_USD": 0.379,
    "EUR_JPY": 0.337,
    "EUR_GBP": 0.571,
}

LOCKED_CELLS = [
    ("ema_cross", "USD_JPY", "16"),
    ("vol_surge_detector", "USD_JPY", "00"),
    ("bb_rsi_reversion", "USD_JPY", "13"),
    ("bb_rsi_reversion", "EUR_USD", "06"),
    ("bb_rsi_reversion", "USD_JPY", "18"),
    ("fib_reversal", "EUR_USD", "15"),
    ("macdh_reversal", "EUR_USD", "07"),
    ("bb_rsi_reversion", "USD_JPY", "10"),
    ("bb_rsi_reversion", "USD_JPY", "11"),
    ("macdh_reversal", "EUR_USD", "14"),
    ("bb_rsi_reversion", "USD_JPY", "17"),
    ("bb_rsi_reversion", "EUR_USD", "12"),
    ("bb_rsi_reversion", "USD_JPY", "02"),
    ("fib_reversal", "USD_JPY", "04"),
    ("bb_rsi_reversion", "EUR_USD", "09"),
]


def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    phat = wins / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def _trade_rows(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        rows = payload.get("trades", [])
    else:
        rows = payload
    if not isinstance(rows, list):
        raise ValueError("trade payload must be a list or {'trades': [...]}")
    return [row for row in rows if isinstance(row, dict)]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _parse_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("Z", "+00:00")
    if re.search(r"[+-]\d{4}$", text):
        text = f"{text[:-5]}{text[-5:-2]}:{text[-2:]}"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _row_time(row: dict) -> datetime | None:
    return _parse_dt(row.get("timestamp") or row.get("entry_time") or row.get("created_at"))


def _instrument(row: dict) -> str:
    return str(row.get("instrument") or row.get("pair") or row.get("symbol") or "").replace("/", "_")


def _strategy(row: dict) -> str:
    return str(row.get("entry_type") or row.get("strategy") or "unknown")


def _hour(row: dict) -> str:
    dt = _row_time(row)
    return f"{dt.hour:02d}" if dt else "unknown"


def _oanda_id(row: dict) -> str:
    return str(row.get("oanda_trade_id") or "").strip()


def _pnl(row: dict) -> float:
    return float(row.get("pnl_pips", row.get("pnl_pip")))


def _is_decided_closed(row: dict) -> bool:
    status = str(row.get("status") or "").upper()
    outcome = str(row.get("outcome") or "").upper()
    if status and status != "CLOSED":
        return False
    return outcome in {"WIN", "LOSS", "BREAKEVEN"} and row.get("pnl_pips", row.get("pnl_pip")) is not None


def assert_no_xau(rows: list[dict]) -> None:
    xau = [row for row in rows if _instrument(row).startswith("XAU")]
    if xau:
        raise ValueError(f"XAU rows are forbidden for R2 post-merge audit: {len(xau)} row(s)")


def filter_true_live(
    payload: Any,
    *,
    lock_deploy_ts: datetime | None = None,
    require_post_lock: bool = True,
) -> list[dict]:
    rows = _trade_rows(payload)
    out: list[dict] = []
    contaminated: list[dict] = []
    xau_candidates: list[dict] = []
    for row in rows:
        row_ts = _row_time(row)
        post_lock = lock_deploy_ts is None or (row_ts is not None and row_ts >= lock_deploy_ts)
        if require_post_lock and not post_lock:
            continue
        if _as_bool(row.get("is_shadow", False)):
            if post_lock and _oanda_id(row):
                contaminated.append(row)
            continue
        if not _oanda_id(row):
            continue
        if _instrument(row).startswith("XAU"):
            xau_candidates.append(row)
            continue
        if not _is_decided_closed(row):
            continue
        clean = dict(row)
        clean["pnl_pips"] = _pnl(row)
        clean["instrument"] = _instrument(row)
        clean["entry_type"] = _strategy(row)
        clean["audit_ts"] = row_ts
        out.append(clean)
    if contaminated:
        raise ValueError(f"SHADOW rows carried OANDA ids in audit scope: {len(contaminated)} row(s)")
    if xau_candidates:
        raise ValueError(f"XAU TRUE_LIVE rows are forbidden for R2 post-merge audit: {len(xau_candidates)} row(s)")
    if any(_as_bool(row.get("is_shadow", False)) for row in out):
        raise ValueError("SHADOW rows mixed into TRUE_LIVE bucket")
    return out


def raw_kelly(win_rate: float, avg_win: float, avg_loss: float) -> float:
    if avg_win <= 0 or avg_loss <= 0:
        return 0.0
    return (win_rate * avg_win - (1.0 - win_rate) * avg_loss) / avg_win


def metrics(rows: list[dict]) -> dict:
    pnls = [_pnl(row) for row in rows]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    n = len(pnls)
    wr = len(wins) / n if n else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    return {
        "n": n,
        "wins": len(wins),
        "losses": len(losses),
        "breakevens": n - len(wins) - len(losses),
        "wr": wr,
        "wilson_lo": wilson_lower(len(wins), n),
        "ev_pips": (sum(pnls) / n) if n else 0.0,
        "total_pnl_pips": sum(pnls),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "kelly_raw": raw_kelly(wr, avg_win, avg_loss),
    }


def weighted_bev_wr(rows: list[dict]) -> float:
    values = [PAIR_BEV_WR[_instrument(row)] for row in rows if _instrument(row) in PAIR_BEV_WR]
    if values:
        return sum(values) / len(values)
    return sum(PAIR_BEV_WR[pair] for pair in ("USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY")) / 4


def group_by_locked_cell(rows: list[dict]) -> dict[tuple[str, str, str], list[dict]]:
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    locked = set(LOCKED_CELLS)
    for row in rows:
        key = (_strategy(row), _instrument(row), _hour(row))
        if key in locked:
            grouped[key].append(row)
    return grouped


def cell_snapshot(rows: list[dict]) -> list[dict]:
    grouped = group_by_locked_cell(rows)
    out = []
    for strategy, instrument, hour in LOCKED_CELLS:
        m = metrics(grouped.get((strategy, instrument, hour), []))
        out.append(
            {
                "strategy": strategy,
                "instrument": instrument,
                "hour_bucket": hour,
                **m,
            }
        )
    return out


def load_prereg_snapshot(path: Path = DEFAULT_PREREG) -> dict[tuple[str, str, str], float]:
    if not path.exists():
        return {}
    snapshot: dict[tuple[str, str, str], float] = {}
    in_table = False
    for line in path.read_text().splitlines():
        if line.startswith("| # | strategy | instrument | hour_bucket |"):
            in_table = True
            continue
        if in_table and (not line.startswith("|") or line.startswith("|---")):
            continue
        if in_table and line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 9 or not cells[0].isdigit():
                continue
            key = (cells[1], cells[2], cells[3])
            try:
                snapshot[key] = float(cells[8])
            except ValueError:
                snapshot[key] = 0.0
    return snapshot


def _band(value: float, accept: float, reject: float, *, high_is_good: bool = True) -> str:
    if high_is_good:
        if value >= accept:
            return "ACCEPT"
        if value < reject:
            return "REJECT"
    else:
        if value <= accept:
            return "ACCEPT"
        if value > reject:
            return "REJECT"
    return "NEEDS_MORE_EVIDENCE"


def evaluate(rows: list[dict], *, prelock: dict[tuple[str, str, str], float] | None = None) -> dict:
    agg = metrics(rows)
    bev = weighted_bev_wr(rows)
    n_band = "ACCEPT" if agg["n"] >= N_ACCEPT else ("NEEDS_MORE_EVIDENCE" if agg["n"] >= N_NEEDS_MORE_MIN else "REJECT")
    k_band = _band(agg["kelly_raw"], KELLY_ACCEPT, KELLY_REJECT)
    ev_band = _band(agg["ev_pips"], EV_ACCEPT, EV_REJECT)
    wilson_band = _band(agg["wilson_lo"], bev, bev - WILSON_MARGIN_REJECT)

    prelock = prelock or {}
    post_cells = cell_snapshot(rows)
    cell_rows = []
    improved = 0
    missing_n = 0
    regressed = 0
    for cell in post_cells:
        key = (cell["strategy"], cell["instrument"], cell["hour_bucket"])
        pre_kelly = prelock.get(key, 0.0)
        delta = cell["kelly_raw"] - pre_kelly
        if cell["n"] == 0:
            missing_n += 1
        elif delta < 0:
            regressed += 1
        elif delta > 0:
            improved += 1
        cell_rows.append({**cell, "prelock_kelly_raw": pre_kelly, "kelly_delta": delta})

    if regressed:
        cell_band = "REJECT"
    elif improved == LOCKED_CELL_COUNT and missing_n == 0:
        cell_band = "ACCEPT"
    else:
        cell_band = "NEEDS_MORE_EVIDENCE"

    bands = {
        "N_post_lock": n_band,
        "aggregate_raw_kelly": k_band,
        "aggregate_ev_pips": ev_band,
        "wilson_lower_vs_bev": wilson_band,
        "cell_level_bonferroni": cell_band,
    }
    if any(value == "REJECT" for value in bands.values()):
        verdict = "REJECT"
    elif all(value == "ACCEPT" for value in bands.values()):
        verdict = "ACCEPT"
    else:
        verdict = "NEEDS_MORE_EVIDENCE"
    return {"verdict": verdict, "aggregate": agg, "bev_wr": bev, "bands": bands, "cells": cell_rows}


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _fmt_num(value: float, digits: int = 4) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def _cell_table(cells: list[dict], *, include_delta: bool) -> list[str]:
    if include_delta:
        lines = [
            "| # | strategy | instrument | hour_bucket | N | WR | EV pip | Wilson lo | pre raw Kelly | post raw Kelly | delta | verdict |",
            "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    else:
        lines = [
            "| # | strategy | instrument | hour_bucket | N | WR | EV pip | Wilson lo | raw Kelly |",
            "|---:|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    for idx, cell in enumerate(cells, 1):
        if include_delta:
            delta = cell["kelly_delta"]
            verdict = "NO_POST_N" if cell["n"] == 0 else ("REGRESSED" if delta < 0 else ("IMPROVED" if delta > 0 else "FLAT"))
            lines.append(
                f"| {idx} | {cell['strategy']} | {cell['instrument']} | {cell['hour_bucket']} | {cell['n']} | "
                f"{_fmt_pct(cell['wr'])} | {cell['ev_pips']:+.2f} | {_fmt_pct(cell['wilson_lo'])} | "
                f"{cell['prelock_kelly_raw']:+.4f} | {cell['kelly_raw']:+.4f} | {delta:+.4f} | {verdict} |"
            )
        else:
            lines.append(
                f"| {idx} | {cell['strategy']} | {cell['instrument']} | {cell['hour_bucket']} | {cell['n']} | "
                f"{_fmt_pct(cell['wr'])} | {cell['ev_pips']:+.2f} | {_fmt_pct(cell['wilson_lo'])} | "
                f"{cell['kelly_raw']:+.4f} |"
            )
    return lines


def render_audit_report(
    *,
    source_trades: str,
    lock_deploy_ts: datetime,
    result: dict,
    prereg_path: Path,
) -> str:
    agg = result["aggregate"]
    bands = result["bands"]
    lines = [
        "# R2 Post-Merge Gate 0 Audit - 2026-05-11",
        "",
        f"Verdict: **{result['verdict']}**",
        "",
        "## Source / Separation",
        "",
        f"- Source: `{source_trades}`",
        f"- LOCK deploy timestamp: `{lock_deploy_ts.isoformat()}`",
        "- TRUE_LIVE filter: `is_shadow=0 AND oanda_trade_id != '' AND timestamp >= LOCK_DEPLOY_TS`.",
        "- FLAG_DRIFT and SHADOW rows are excluded; SHADOW rows with OANDA ids in scope abort the run.",
        "- TRUE_LIVE XAU rows abort the run before metrics are computed; non-target XAU rows remain excluded.",
        f"- Pre-LOCK snapshot source: `{prereg_path}`",
        "",
        "## Registered Criteria",
        "",
        "| criterion | value | band | ACCEPT | NEEDS_MORE_EVIDENCE | REJECT |",
        "|---|---:|---|---|---|---|",
        f"| N_post_lock | {agg['n']} | {bands['N_post_lock']} | >=30 | 15-29 | <15 |",
        f"| Aggregate raw Kelly | {agg['kelly_raw']:+.4f} | {bands['aggregate_raw_kelly']} | >=+0.005 | -0.010 to <+0.005 | <-0.010 |",
        f"| Aggregate EV pip | {agg['ev_pips']:+.2f} | {bands['aggregate_ev_pips']} | >=-0.10 | -0.30 to <-0.10 | <-0.30 |",
        f"| Wilson 95% lower WR | {_fmt_pct(agg['wilson_lo'])} vs BEV {_fmt_pct(result['bev_wr'])} | {bands['wilson_lower_vs_bev']} | >=BEV | BEV-3pp to <BEV | <BEV-3pp |",
        f"| Cell-level Bonferroni family | K={LOCKED_CELL_COUNT}, alpha'={BONFERRONI_ALPHA:.6f} | {bands['cell_level_bonferroni']} | all 15 improve vs pre-LOCK | partial/no post-N | any regression |",
        "",
        "## Aggregate",
        "",
        "| N | wins | losses | breakevens | WR | avg win | avg loss | EV pip | total pip | raw Kelly | Wilson lo | BEV_WR |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {agg['n']} | {agg['wins']} | {agg['losses']} | {agg['breakevens']} | {_fmt_pct(agg['wr'])} | {agg['avg_win']:.2f} | {agg['avg_loss']:.2f} | {agg['ev_pips']:+.2f} | {agg['total_pnl_pips']:+.1f} | {agg['kelly_raw']:+.4f} | {_fmt_pct(agg['wilson_lo'])} | {_fmt_pct(result['bev_wr'])} |",
        "",
        "## 15-Cell Post-LOCK Comparison",
        "",
        *_cell_table(result["cells"], include_delta=True),
        "",
        "## Locked Actions",
        "",
        "- ACCEPT: A3-simple dispatch and Gate 1 0.3x lot may proceed only through a separate approval path.",
        "- NEEDS_MORE_EVIDENCE: extend audit window by +7 days with the same frozen criteria.",
        "- REJECT: do not dispatch A3-simple; open a separate cell-level demotion RCA.",
        "",
    ]
    return "\n".join(lines)


def render_prereg_doc(*, source_trades: str, rows: list[dict]) -> str:
    snapshot = cell_snapshot(rows)
    agg = metrics(rows)
    bev = weighted_bev_wr(rows)
    lines = [
        "# Pre-Registration: R2 Post-Merge Gate 0 Audit - 2026-05-11",
        "",
        "Status: **LOCKED at commit time; post-hoc cutoff changes are forbidden.**",
        "",
        "## Scope",
        "",
        "- Primary source: Render API `/api/demo/trades?limit=100000` JSON export only.",
        "- Local DB, `.env`, OANDA credentials, and local `app.py` are out of scope.",
        "- TRUE_LIVE: `is_shadow=0 AND oanda_trade_id != ''`.",
        "- FLAG_DRIFT: `is_shadow=0 AND (oanda_trade_id IS NULL OR oanda_trade_id='')`; excluded.",
        "- SHADOW: `is_shadow=1`; excluded and must not mix into TRUE_LIVE.",
        "- TRUE_LIVE XAU rows are forbidden for this audit; non-target XAU rows are excluded before metrics.",
        "- LOCK deploy timestamp: `TODO_AFTER_C52D8E3_PUSH`.",
        "",
        "## Hypotheses",
        "",
        "- H1: post-LOCK TRUE_LIVE new N has aggregate raw Kelly >= 0 / EV >= 0 enough to ACCEPT Gate 0.",
        "- H0: post-LOCK TRUE_LIVE new N remains raw Kelly < 0, requiring additional cell-level demotion.",
        "",
        "## Frozen Cutoffs",
        "",
        "| metric | ACCEPT | NEEDS_MORE_EVIDENCE | REJECT |",
        "|---|---|---|---|",
        "| N_post_lock TRUE_LIVE | >= 30 | 15 <= N < 30 | < 15 |",
        "| Aggregate raw Kelly | >= +0.005 | -0.010 <= K < +0.005 | < -0.010 |",
        "| Aggregate EV pip | >= -0.10 | -0.30 <= EV < -0.10 | < -0.30 |",
        "| Wilson 95% lower WR | >= BEV_WR | BEV_WR-3pp <= Wilson < BEV_WR | < BEV_WR-3pp |",
        "| Cell-level Bonferroni | all 15 cells improve vs pre-LOCK | partial/no post-N | any cell regresses vs pre-LOCK |",
        "",
        f"- Bonferroni family K: **{LOCKED_CELL_COUNT}** locked cells; alpha' = 0.05 / 15 = **{BONFERRONI_ALPHA:.6f}**.",
        f"- LOCKED_BEV_WR: **{bev:.4f}** from pair-weighted TRUE_LIVE snapshot using `friction-analysis.md` BEV_WR table.",
        "- Final verdict rule: all registered criteria ACCEPT => ACCEPT; any registered criterion REJECT => REJECT; otherwise NEEDS_MORE_EVIDENCE.",
        "",
        "## Pre-LOCK Snapshot",
        "",
        f"- Snapshot source: `{source_trades}`",
        f"- TRUE_LIVE snapshot N: {agg['n']}",
        f"- Snapshot aggregate raw Kelly: {agg['kelly_raw']:+.4f}",
        f"- Snapshot aggregate EV: {agg['ev_pips']:+.2f} pip",
        f"- Snapshot Wilson lower: {_fmt_pct(agg['wilson_lo'])}",
        "",
        *_cell_table(snapshot, include_delta=False),
        "",
        "## Audit Commands",
        "",
        "```bash",
        "curl -sS 'https://fx-ai-trader.onrender.com/api/demo/trades?limit=100000' \\",
        "  -o /tmp/render-trades-20260511.json",
        "python3 tools/r2_postmerge_audit.py \\",
        "  --trades /tmp/render-trades-20260511.json \\",
        "  --lock-deploy-ts TODO_AFTER_C52D8E3_PUSH \\",
        "  --output knowledge-base/wiki/decisions/r2-postmerge-audit-2026-05-11.md",
        "```",
        "",
        "## Locked Actions",
        "",
        "- ACCEPT: unlock only the approval path for A3-simple dispatch and Gate 1 0.3x lot; do not apply those actions in this audit script.",
        "- NEEDS_MORE_EVIDENCE: extend the audit window by +7 days under the same criteria.",
        "- REJECT: keep A3-simple blocked and open a separate cell-level demotion RCA.",
        "",
    ]
    return "\n".join(lines)


def dry_run_text() -> str:
    sample = []
    for i in range(30):
        sample.append(
            {
                "trade_id": f"sample-{i}",
                "oanda_trade_id": f"O-{i}",
                "is_shadow": 0,
                "status": "CLOSED",
                "outcome": "WIN" if i < 18 else "LOSS",
                "instrument": "EUR_USD",
                "entry_type": "bb_rsi_reversion",
                "entry_time": f"2026-05-11T{i % 24:02d}:00:00+00:00",
                "pnl_pips": 2.0 if i < 18 else -1.0,
            }
        )
    lock_ts = _parse_dt("2026-05-11T00:00:00+00:00")
    rows = filter_true_live({"trades": sample}, lock_deploy_ts=lock_ts)
    result = evaluate(rows)
    return render_audit_report(
        source_trades="DRY_RUN_SAMPLE",
        lock_deploy_ts=lock_ts or datetime.now(timezone.utc),
        result=result,
        prereg_path=DEFAULT_PREREG,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades")
    parser.add_argument("--lock-deploy-ts")
    parser.add_argument("--output")
    parser.add_argument("--prereg", default=str(DEFAULT_PREREG))
    parser.add_argument("--snapshot-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print(dry_run_text())
        return 0

    if not args.trades:
        parser.error("--trades is required unless --dry-run is used")
    if not args.output:
        parser.error("--output is required unless --dry-run is used")

    payload = json.loads(Path(args.trades).read_text())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.snapshot_only:
        rows = filter_true_live(payload, lock_deploy_ts=None, require_post_lock=False)
        output.write_text(render_prereg_doc(source_trades=args.trades, rows=rows))
        print(f"snapshot TRUE_LIVE N={len(rows)} wrote {output}")
        return 0

    if not args.lock_deploy_ts:
        parser.error("--lock-deploy-ts is required unless --snapshot-only or --dry-run is used")
    lock_ts = _parse_dt(args.lock_deploy_ts)
    if not lock_ts:
        raise ValueError(f"invalid --lock-deploy-ts: {args.lock_deploy_ts}")
    rows = filter_true_live(payload, lock_deploy_ts=lock_ts)
    prereg_path = Path(args.prereg)
    result = evaluate(rows, prelock=load_prereg_snapshot(prereg_path))
    output.write_text(
        render_audit_report(
            source_trades=args.trades,
            lock_deploy_ts=lock_ts,
            result=result,
            prereg_path=prereg_path,
        )
    )
    print(
        f"Verdict: {result['verdict']} "
        f"N={result['aggregate']['n']} "
        f"K={result['aggregate']['kelly_raw']:+.4f} "
        f"EV={result['aggregate']['ev_pips']:+.2f} "
        f"wrote {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
