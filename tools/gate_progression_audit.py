#!/usr/bin/env python3
"""Gate 1->2 aggregate Kelly + MC ruin audit from Render trade JSON."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.stats_utils import deflated_sharpe_ratio
from research.edge_discovery.significance import binomial_one_sided_p

DECIDED_OUTCOMES = {"WIN", "LOSS", "BREAKEVEN"}
INITIAL_CAPITAL_PIPS = 1000.0
RUIN_DD_PCT = 0.50
EXCLUDED_RISK_INSTRUMENT_PREFIXES = ("XAU",)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _trade_rows(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        rows = payload.get("trades", [])
    else:
        rows = payload
    if not isinstance(rows, list):
        raise ValueError("trade payload must be a list or {'trades': [...]}")
    return [row for row in rows if isinstance(row, dict)]


def filter_closed_live_trades(payload: Any) -> list[dict]:
    out: list[dict] = []
    for row in _trade_rows(payload):
        outcome = str(row.get("outcome") or "").upper()
        status = str(row.get("status") or "").upper()
        if _as_bool(row.get("is_shadow", False)):
            continue
        if status and status != "CLOSED":
            continue
        if outcome not in DECIDED_OUTCOMES:
            continue
        instrument = str(row.get("instrument") or row.get("pair") or "")
        if any(instrument.startswith(prefix) for prefix in EXCLUDED_RISK_INSTRUMENT_PREFIXES):
            continue
        if row.get("pnl_pips") is None:
            continue
        try:
            pnl = float(row.get("pnl_pips"))
        except (TypeError, ValueError):
            continue
        clean = dict(row)
        clean["outcome"] = outcome
        clean["status"] = "CLOSED"
        clean["pnl_pips"] = pnl
        clean["entry_type"] = clean.get("entry_type") or clean.get("strategy") or "unknown"
        clean["instrument"] = instrument or "unknown"
        out.append(clean)
    return out


def filter_closed_shadow_trades(payload: Any) -> list[dict]:
    shadow_payload = {"trades": [row for row in _trade_rows(payload) if _as_bool(row.get("is_shadow", False))]}
    return [
        row for row in filter_closed_live_trades({"trades": [{**r, "is_shadow": 0} for r in shadow_payload["trades"]]})
    ]


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _hour_bucket(row: dict) -> str:
    dt = _parse_dt(row.get("entry_time") or row.get("created_at"))
    if not dt:
        return "unknown"
    return f"{dt.hour:02d}"


def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    phat = wins / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def _kelly(win_rate: float, avg_win: float, avg_loss: float) -> tuple[float, float, float]:
    if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0, 0.0, 0.0
    b = avg_win / avg_loss
    raw = (win_rate * b - (1 - win_rate)) / b
    edge = win_rate * b - (1 - win_rate)
    return raw, max(0.0, raw), edge


def _one_sided_t_p(pnls: list[float]) -> tuple[float, float]:
    n = len(pnls)
    if n < 2:
        return 0.0, 1.0
    arr = np.array(pnls, dtype=float)
    std = float(np.std(arr, ddof=1))
    if std <= 0:
        t_stat = math.inf if float(np.mean(arr)) > 0 else 0.0
        return t_stat, 0.0 if math.isinf(t_stat) else 1.0
    t_stat = float(np.mean(arr)) / (std / math.sqrt(n))
    try:
        from scipy import stats

        p_value = float(stats.t.sf(t_stat, df=n - 1))
    except Exception:
        p_value = 0.5 * math.erfc(t_stat / math.sqrt(2))
    return t_stat, p_value


def _max_dd_pct(pnls: list[float], initial_capital: float = INITIAL_CAPITAL_PIPS) -> float:
    equity = initial_capital
    peak = initial_capital
    max_dd = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return max_dd / initial_capital if initial_capital > 0 else 0.0


def _estimate_forward_trades(rows: list[dict], horizon_days: int) -> tuple[int, float, str, str]:
    dates = [
        dt for dt in (_parse_dt(row.get("exit_time") or row.get("entry_time")) for row in rows)
        if dt is not None
    ]
    if len(dates) < 2:
        return max(1, horizon_days), 1.0, "", ""
    start = min(dates)
    end = max(dates)
    days = max((end - start).total_seconds() / 86400.0, 1.0)
    trades_per_day = len(rows) / days
    return max(1, int(round(trades_per_day * horizon_days))), trades_per_day, start.isoformat(), end.isoformat()


def _mc_ruin(
    pnls: list[float],
    *,
    n_forward: int,
    iterations: int,
    seed: int = 42,
    initial_capital: float = INITIAL_CAPITAL_PIPS,
) -> dict:
    if len(pnls) < 5:
        return {
            "ruin_probability": 0.0,
            "median_max_dd_pct": 0.0,
            "worst_case_dd_99_pct": 0.0,
            "n_simulations": 0,
            "n_trades_forward": n_forward,
            "insufficient": True,
        }
    rng = np.random.RandomState(seed)
    arr = np.array(pnls, dtype=float)
    ruin_threshold = initial_capital * RUIN_DD_PCT
    max_dds = []
    ruined = 0
    for _ in range(iterations):
        sampled = rng.choice(arr, size=n_forward, replace=True)
        equity = initial_capital
        peak = initial_capital
        max_dd = 0.0
        path_ruined = False
        for pnl in sampled:
            equity += float(pnl)
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
            if not path_ruined and max_dd >= ruin_threshold:
                path_ruined = True
        if path_ruined:
            ruined += 1
        max_dds.append(max_dd / initial_capital)
    return {
        "ruin_probability": ruined / iterations,
        "median_max_dd_pct": float(np.median(max_dds)),
        "worst_case_dd_99_pct": float(np.percentile(max_dds, 99)),
        "n_simulations": iterations,
        "n_trades_forward": n_forward,
        "insufficient": False,
    }


def _metrics(rows: list[dict], *, mc_iterations: int, mc_horizon_days: int, n_trials: int = 1) -> dict:
    pnls = [float(row["pnl_pips"]) for row in rows]
    n = len(rows)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    win_count = len(wins)
    loss_count = len(losses)
    wr = win_count / n if n else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = abs(float(np.mean(losses))) if losses else 0.0
    kelly_raw, kelly, edge = _kelly(wr, avg_win, avg_loss)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else (math.inf if gross_profit > 0 else 0.0)
    t_stat, t_p = _one_sided_t_p(pnls)
    sharpe = (float(np.mean(pnls)) / float(np.std(pnls, ddof=1)) * math.sqrt(252)) if n > 1 and float(np.std(pnls, ddof=1)) > 0 else 0.0
    raw_sharpe = (float(np.mean(pnls)) / float(np.std(pnls, ddof=1))) if n > 1 and float(np.std(pnls, ddof=1)) > 0 else 0.0
    n_forward, trades_per_day, live_start, live_end = _estimate_forward_trades(rows, mc_horizon_days)
    mc = _mc_ruin(pnls, n_forward=n_forward, iterations=mc_iterations)
    dsr = deflated_sharpe_ratio(raw_sharpe, n, max(1, n_trials))
    bonf_raw = binomial_one_sided_p(win_count, n, 0.50) if n else 1.0
    return {
        "n": n,
        "wins": win_count,
        "losses": loss_count,
        "breakevens": n - win_count - loss_count,
        "wr": wr,
        "wilson_lo": wilson_lower(win_count, n),
        "ev_pips": float(np.mean(pnls)) if pnls else 0.0,
        "total_pnl_pips": float(sum(pnls)),
        "pf": pf,
        "kelly": kelly,
        "kelly_raw": kelly_raw,
        "kelly_edge": edge,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "t_stat": t_stat,
        "t_one_sided_p": t_p,
        "bonferroni_p": min(1.0, bonf_raw * max(1, n_trials)),
        "max_dd_pct": _max_dd_pct(pnls),
        "sharpe_annualized_1trade": sharpe,
        "dsr": dsr.get("dsr", 0.0),
        "mc_ruin_60d": mc["ruin_probability"],
        "mc": mc,
        "trades_per_day": trades_per_day,
        "live_start": live_start,
        "live_end": live_end,
    }


def summarize_trades(rows: list[dict], *, mc_iterations: int = 1000, mc_horizon_days: int = 60) -> dict:
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_strategy[str(row.get("entry_type") or "unknown")].append(row)
    n_trials = max(1, len(by_strategy))
    aggregate = _metrics(rows, mc_iterations=mc_iterations, mc_horizon_days=mc_horizon_days, n_trials=n_trials)
    strategies = {
        name: _metrics(sub, mc_iterations=mc_iterations, mc_horizon_days=mc_horizon_days, n_trials=n_trials)
        for name, sub in sorted(by_strategy.items())
    }
    return {"aggregate": aggregate, "strategies": strategies}


def verdict_for(aggregate: dict) -> tuple[str, list[str]]:
    reasons: list[str] = []
    kelly_value = float(aggregate.get("kelly_raw", aggregate.get("kelly", 0.0)))
    if kelly_value < 0:
        reasons.append("Kelly<0")
    if float(aggregate.get("mc_ruin_60d", 0.0)) > 0.90:
        reasons.append("MC破産>90%")
    if float(aggregate.get("ev_pips", 0.0)) < 0 and float(aggregate.get("wilson_lo", 0.0)) < 0.45:
        reasons.append("EV<0かつWilson_lo<0.45")
    if reasons:
        return "REJECT", reasons

    accept_checks = [
        (float(aggregate.get("kelly", 0.0)) > 0.05, "Kelly<=0.05"),
        (float(aggregate.get("mc_ruin_60d", 1.0)) < 0.70, "MC破産>=70%"),
        (int(aggregate.get("n", 0)) >= 100, "N<100"),
        (float(aggregate.get("wilson_lo", 0.0)) > 0.50, "Wilson_lo<=0.50"),
        (float(aggregate.get("ev_pips", 0.0)) > 0, "EV<=0"),
        (float(aggregate.get("pf", 0.0)) > 1.0, "PF<=1.0"),
        (float(aggregate.get("max_dd_pct", 1.0)) < 0.30, "maxDD>=30%"),
    ]
    failed = [label for ok, label in accept_checks if not ok]
    if not failed:
        return "ACCEPT", ["全ACCEPT条件を満たす"]
    return "NEEDS_MORE_EVIDENCE", failed


def _extract_risk_values(risk: dict) -> tuple[float | None, float | None, int | None]:
    api_kelly = risk.get("kelly_fraction")
    if api_kelly is None and isinstance(risk.get("kelly"), dict):
        api_kelly = risk["kelly"].get("full_kelly")
    api_mc = risk.get("mc_ruin_60d")
    if api_mc is None and isinstance(risk.get("monte_carlo"), dict):
        api_mc = risk["monte_carlo"].get("ruin_probability")
    n_forward = None
    if isinstance(risk.get("monte_carlo"), dict):
        n_forward = risk["monte_carlo"].get("n_trades_forward")
    return (
        float(api_kelly) if api_kelly is not None else None,
        float(api_mc) if api_mc is not None else None,
        int(n_forward) if n_forward is not None else None,
    )


def _within_5pct(local: float, api: float | None) -> bool:
    if api is None:
        return False
    return abs(local - api) <= 0.05


def compare_risk_dashboard(local: dict, risk: dict) -> dict:
    api_kelly, api_mc, n_forward = _extract_risk_values(risk)
    return {
        "kelly": {
            "local": local.get("kelly"),
            "api": api_kelly,
            "abs_diff": None if api_kelly is None else abs(float(local.get("kelly", 0.0)) - api_kelly),
            "within_5pct": _within_5pct(float(local.get("kelly", 0.0)), api_kelly),
        },
        "mc_ruin": {
            "local": local.get("mc_ruin_60d"),
            "api": api_mc,
            "abs_diff": None if api_mc is None else abs(float(local.get("mc_ruin_60d", 0.0)) - api_mc),
            "within_5pct": _within_5pct(float(local.get("mc_ruin_60d", 0.0)), api_mc),
        },
        "api_mc_n_trades_forward": n_forward,
    }


def portfolio_simulation(
    live_rows: list[dict],
    shadow_rows: list[dict],
    *,
    promote_entry_contains: str = "s2",
    mc_iterations: int = 1000,
    mc_horizon_days: int = 60,
) -> dict:
    needle = promote_entry_contains.lower()
    added = [row for row in shadow_rows if needle in str(row.get("entry_type", "")).lower()]
    baseline = summarize_trades(live_rows, mc_iterations=mc_iterations, mc_horizon_days=mc_horizon_days)["aggregate"]
    promoted = summarize_trades(live_rows + added, mc_iterations=mc_iterations, mc_horizon_days=mc_horizon_days)["aggregate"]
    return {
        "promote_filter": promote_entry_contains,
        "added_shadow_n": len(added),
        "baseline": baseline,
        "with_promoted_shadow": promoted,
        "delta_kelly": promoted["kelly"] - baseline["kelly"],
        "delta_mc_ruin_60d": promoted["mc_ruin_60d"] - baseline["mc_ruin_60d"],
        "delta_ev_pips": promoted["ev_pips"] - baseline["ev_pips"],
    }


def r2_candidate_cells(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("entry_type") or "unknown"), str(row.get("instrument") or "unknown"), _hour_bucket(row))].append(row)
    out = []
    for (strategy, pair, hour), sub in grouped.items():
        if len(sub) < 3:
            continue
        m = _metrics(sub, mc_iterations=100, mc_horizon_days=60)
        if m["ev_pips"] < 0 or m["kelly_raw"] < 0:
            out.append({"entry_type": strategy, "instrument": pair, "hour_bucket": hour, **m})
    out.sort(key=lambda row: (row["ev_pips"], row["kelly_raw"], -row["n"]))
    return out


def _fmt_pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def _fmt_num(value: float, digits: int = 4) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def _metrics_table(rows: dict[str, dict]) -> list[str]:
    lines = [
        "| strategy | N | WR | Wilson lo | EV pip | PF | Kelly | raw Kelly | t p(one-side) | Bonf p | max DD | Sharpe |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, m in rows.items():
        lines.append(
            f"| {name} | {m['n']} | {_fmt_pct(m['wr'])} | {_fmt_pct(m['wilson_lo'])} | "
            f"{m['ev_pips']:+.2f} | {_fmt_num(m['pf'], 3)} | {_fmt_num(m['kelly'])} | "
            f"{m['kelly_raw']:+.4f} | {_fmt_num(m['t_one_sided_p'])} | {_fmt_num(m['bonferroni_p'])} | "
            f"{_fmt_pct(m['max_dd_pct'])} | {m['sharpe_annualized_1trade']:+.2f} |"
        )
    return lines


def render_report(
    *,
    live_rows: list[dict],
    shadow_rows: list[dict],
    summary: dict,
    verdict: str,
    reasons: list[str],
    risk_comparison: dict,
    portfolio: dict,
    source_trades: str,
    source_risk: str,
    mc_iterations: int,
    mc_horizon_days: int,
) -> str:
    agg = summary["aggregate"]
    cells = r2_candidate_cells(live_rows)
    risk_available = risk_comparison["kelly"]["api"] is not None and risk_comparison["mc_ruin"]["api"] is not None
    risk_ok = risk_available and risk_comparison["kelly"]["within_5pct"] and risk_comparison["mc_ruin"]["within_5pct"]
    lines = [
        "# Gate 1->2 Aggregate Kelly + MC破産確率 現状監査 - 2026-05-03",
        "",
        f"{verdict}: Kelly={agg['kelly']:.4f} (raw={agg['kelly_raw']:+.4f}), MC60d破産={agg['mc_ruin_60d']:.4f}, N={agg['n']}, Wilson_lo={agg['wilson_lo']:.4f}, EV={agg['ev_pips']:+.2f}p, PF={agg['pf']:.3f}",
        "",
        "## Source / 分離",
        "",
        f"- 一次ソース: `{source_trades}`",
        f"- risk dashboard検証: `{source_risk}`",
        f"- Live集計: `is_shadow=0`, `status=CLOSED`, `outcome in WIN/LOSS/BREAKEVEN`, `pnl_pips != null`",
        "- XAU除外: `/api/risk/dashboard` と同じ FX-only risk 集計に揃えるため `instrument LIKE 'XAU%'` は除外。",
        f"- Shadow行: {len(shadow_rows)} 件。比較・S2仮想加算のみで、Live Kelly/MCには混入なし。",
        f"- Live期間: {agg.get('live_start') or 'unknown'} -> {agg.get('live_end') or 'unknown'} / 推定 {agg['trades_per_day']:.2f} trades/day",
        "",
        "## Verdict",
        "",
        f"- 判定: **{verdict}**",
        f"- 根拠: {', '.join(reasons)}",
        "- lot変更は本監査では実施しない。ACCEPT時でも司令塔承認後の別PR対象。",
        "",
        "## Aggregate",
        "",
        "| N | wins | losses | BE | WR | Wilson lo | EV pip | total pip | PF | Kelly | raw Kelly | t p | MC ruin 60d | max DD | Sharpe | DSR |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {agg['n']} | {agg['wins']} | {agg['losses']} | {agg['breakevens']} | {_fmt_pct(agg['wr'])} | {_fmt_pct(agg['wilson_lo'])} | {agg['ev_pips']:+.2f} | {agg['total_pnl_pips']:+.1f} | {_fmt_num(agg['pf'], 3)} | {_fmt_num(agg['kelly'])} | {agg['kelly_raw']:+.4f} | {_fmt_num(agg['t_one_sided_p'])} | {_fmt_pct(agg['mc_ruin_60d'])} | {_fmt_pct(agg['max_dd_pct'])} | {agg['sharpe_annualized_1trade']:+.2f} | {_fmt_num(agg['dsr'])} |",
        "",
        f"MC仕様: iterations={mc_iterations}, horizon={mc_horizon_days}日, forward_trades={agg['mc']['n_trades_forward']}, ruin=peak DD {RUIN_DD_PCT:.0%} of {INITIAL_CAPITAL_PIPS:.0f} pips, bootstrap=Live PnL分布。",
        "",
        "## Strategy別",
        "",
        *_metrics_table(summary["strategies"]),
        "",
        "## `/api/risk/dashboard` 照合",
        "",
        f"- Kelly: local={risk_comparison['kelly']['local']}, api={risk_comparison['kelly']['api']}, abs_diff={risk_comparison['kelly']['abs_diff']}, within±5pp={risk_comparison['kelly']['within_5pct']}",
        f"- MC ruin: local={risk_comparison['mc_ruin']['local']}, api={risk_comparison['mc_ruin']['api']}, abs_diff={risk_comparison['mc_ruin']['abs_diff']}, within±5pp={risk_comparison['mc_ruin']['within_5pct']}",
        f"- API MC n_trades_forward={risk_comparison['api_mc_n_trades_forward']}; 照合結果: {'PASS' if risk_ok else ('BLOCKED_API_UNAVAILABLE' if not risk_available else 'MISMATCH')}",
        "",
        "## S2 ShadowをLive化した場合のportfolio影響",
        "",
        f"- S2抽出条件: entry_type contains `{portfolio['promote_filter']}`",
        f"- added_shadow_n={portfolio['added_shadow_n']}",
        f"- Kelly delta={portfolio['delta_kelly']:+.4f}, MC ruin delta={portfolio['delta_mc_ruin_60d']:+.4f}, EV delta={portfolio['delta_ev_pips']:+.2f}p",
        f"- baseline N={portfolio['baseline']['n']} -> promoted N={portfolio['with_promoted_shadow']['n']}",
        "",
        "## R2降格候補 cell",
        "",
    ]
    if cells:
        lines += [
            "| entry_type | instrument | hour_bucket | N | WR | Wilson lo | EV pip | Kelly raw | PF |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in cells[:30]:
            lines.append(
                f"| {row['entry_type']} | {row['instrument']} | {row['hour_bucket']} | {row['n']} | "
                f"{_fmt_pct(row['wr'])} | {_fmt_pct(row['wilson_lo'])} | {row['ev_pips']:+.2f} | "
                f"{row['kelly_raw']:+.4f} | {_fmt_num(row['pf'], 3)} |"
            )
    else:
        lines.append("_該当なし (N>=3 の負EV/負raw Kelly cellなし)_")
    if verdict == "ACCEPT":
        lines += [
            "",
            "## ACCEPT時 PRテンプレート",
            "",
            "- branch: `feat/gate-2-lot-increase-2026-05-03`",
            "- scope: lot 0.3x -> 0.5x 設定変更のみ",
            "- pre-merge gate: 本レポートの ACCEPT 条件と risk dashboard 照合 PASS を添付",
        ]
    elif verdict == "NEEDS_MORE_EVIDENCE":
        low_n = [name for name, m in summary["strategies"].items() if m["n"] < 30]
        lines += [
            "",
            "## 不足N / 次回監査",
            "",
            f"- N<30 strategy: {', '.join(low_n) if low_n else 'なし'}",
            "- 次回監査候補: 2026-06-04 (H-1 PR #16 A/B 1ヶ月並走完了目安) または Wave 3 Tier 2 verdict 出揃い時。",
        ]
    else:
        lines += [
            "",
            "## REJECT時 注意",
            "",
            "- OANDA転送停止やlot変更は未実施。上記cellは司令塔承認待ちの停止候補のみ。",
        ]
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trades", required=True)
    parser.add_argument("--risk", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mc-iterations", type=int, default=1000)
    parser.add_argument("--mc-horizon", type=int, default=60)
    args = parser.parse_args()

    if args.mc_iterations < 1000:
        print("MC iterations must be >= 1000", file=sys.stderr)
        return 2

    trades_payload = json.loads(Path(args.trades).read_text())
    risk_payload = json.loads(Path(args.risk).read_text())
    live_rows = filter_closed_live_trades(trades_payload)
    shadow_rows = filter_closed_shadow_trades(trades_payload)
    summary = summarize_trades(live_rows, mc_iterations=args.mc_iterations, mc_horizon_days=args.mc_horizon)
    verdict, reasons = verdict_for(summary["aggregate"])
    risk_comparison = compare_risk_dashboard(summary["aggregate"], risk_payload)
    portfolio = portfolio_simulation(
        live_rows,
        shadow_rows,
        promote_entry_contains="s2",
        mc_iterations=args.mc_iterations,
        mc_horizon_days=args.mc_horizon,
    )
    report = render_report(
        live_rows=live_rows,
        shadow_rows=shadow_rows,
        summary=summary,
        verdict=verdict,
        reasons=reasons,
        risk_comparison=risk_comparison,
        portfolio=portfolio,
        source_trades=args.trades,
        source_risk=args.risk,
        mc_iterations=args.mc_iterations,
        mc_horizon_days=args.mc_horizon,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(report)
    print(
        f"{verdict}: Kelly={summary['aggregate']['kelly']:.4f} "
        f"MC60d={summary['aggregate']['mc_ruin_60d']:.4f} "
        f"N={summary['aggregate']['n']}"
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
