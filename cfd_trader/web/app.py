"""Flask dashboard for cfd-trader Phase 2 shadow data.

Pure view layer over existing components:
- promotion.tier_engine.evaluate  -> overview stats
- audit.queries.shadow_trades_for -> trade table
- audit.drift_check               -> orphan warnings
- audit.queries.bridge_summary_for / global_counts / recent_entries -> OANDA bridge

Exposed two ways:
- create_app() -> standalone Flask app (legacy entrypoint, kept for tests)
- register(app, url_prefix) -> mount as Blueprint into an existing Flask app
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from flask import Blueprint, Flask, current_app, render_template

from cfd_trader.audit.drift_check import find_orphan_strategies
from cfd_trader.audit.oanda_audit import init_db as _init_audit_db
from cfd_trader.audit.queries import (
    bridge_summary_for,
    global_counts,
    recent_entries,
    shadow_trades_for,
)
from cfd_trader.promotion.gates import H1_N_MIN
from cfd_trader.promotion.tier_engine import evaluate
from cfd_trader.shadow.state import init_state_table as _init_state_table

# Side-effect: registers strategies so drift_check has a baseline.
import cfd_trader.strategies.ported.orb_ny_open_short  # noqa: F401


SHADOW_STRATEGIES = ["orb_ny_open_short"]


cfd_bp = Blueprint("cfd", __name__, template_folder="templates")


def _db_path() -> str:
    return current_app.config.get(
        "CFD_DB_PATH", os.environ.get("CFD_DB_PATH", "./cfd_trader.db")
    )


def _oanda_env_status() -> dict:
    """Inspect process env for OANDA bridge configuration (no network call)."""
    token = os.environ.get("OANDA_API_TOKEN", "")
    account = os.environ.get("OANDA_ACCOUNT_ID", "")
    env = os.environ.get("OANDA_ENV", "live")
    configured = bool(token and account)
    return {
        "configured": configured,
        "account_id": account or None,
        "env": env,
        "token_present": bool(token),
        "token_tail": ("…" + token[-4:]) if token else None,
    }


def _age_seconds(ts: str | None) -> int | None:
    if not ts:
        return None
    try:
        clean = ts.rstrip("Z")
        dt = datetime.fromisoformat(clean).replace(tzinfo=timezone.utc)
        return int((datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return None


@cfd_bp.route("/")
def overview():
    db = _db_path()
    reports = [evaluate(db, strategy_name=s) for s in SHADOW_STRATEGIES]
    orphans = find_orphan_strategies(db)
    counts = global_counts(db)
    bridge_rows = []
    for s in SHADOW_STRATEGIES:
        for row in bridge_summary_for(db, strategy_name=s):
            bridge_rows.append({**row, "strategy_name": s})
    return render_template(
        "overview.html",
        reports=reports,
        orphans=orphans,
        db_path=db,
        h1_n_min=H1_N_MIN,
        counts=counts,
        bridge_rows=bridge_rows,
        oanda_env=_oanda_env_status(),
        last_shadow_age=_age_seconds(counts.get("last_shadow_ts")),
        last_live_age=_age_seconds(counts.get("last_live_ts")),
    )


@cfd_bp.route("/shadow-trades/<strategy_name>")
def shadow_trades(strategy_name: str):
    db = _db_path()
    trades = shadow_trades_for(db, strategy_name=strategy_name)
    trades_sorted = sorted(trades, key=lambda t: t.ts)
    cum = 0.0
    rows = []
    for t in trades_sorted:
        pnl = float(t.pnl_point) if t.pnl_point is not None else 0.0
        cum += pnl
        rows.append({"trade": t, "cum_pnl_point": cum})
    return render_template(
        "shadow_trades.html",
        strategy_name=strategy_name,
        rows=rows,
    )


@cfd_bp.route("/progress")
def progress():
    db = _db_path()
    items = []
    for name in SHADOW_STRATEGIES:
        report = evaluate(db, strategy_name=name)
        items.append({
            "name": name,
            "n": report.n,
            "target": H1_N_MIN,
            "pct": min(100, int(100 * report.n / H1_N_MIN)) if H1_N_MIN else 0,
            "distance": report.h1_gate_distance,
        })
    return render_template("progress.html", items=items, h1_n_min=H1_N_MIN)


@cfd_bp.route("/bridge")
def bridge():
    """OANDA bridge transfer view — per-strategy + recent activity."""
    db = _db_path()
    counts = global_counts(db)
    bridge_rows = []
    for s in SHADOW_STRATEGIES:
        for row in bridge_summary_for(db, strategy_name=s):
            bridge_rows.append({**row, "strategy_name": s})
    recent = recent_entries(db, limit=30)
    return render_template(
        "bridge.html",
        counts=counts,
        bridge_rows=bridge_rows,
        recent=recent,
        oanda_env=_oanda_env_status(),
        last_shadow_age=_age_seconds(counts.get("last_shadow_ts")),
        last_live_age=_age_seconds(counts.get("last_live_ts")),
    )


def create_app(db_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["CFD_DB_PATH"] = db_path or os.environ.get(
        "CFD_DB_PATH", "./cfd_trader.db"
    )
    app.register_blueprint(cfd_bp)
    return app


def register(app: Flask, url_prefix: str = "/cfd", db_path: str | None = None) -> None:
    """Mount the cfd-trader dashboard onto an existing Flask app."""
    resolved_db = db_path or os.environ.get("CFD_DB_PATH", "./cfd_trader.db")
    app.config.setdefault("CFD_DB_PATH", resolved_db)
    try:
        _init_audit_db(resolved_db)
        _init_state_table(resolved_db)
    except Exception:
        pass
    app.register_blueprint(cfd_bp, url_prefix=url_prefix)
