#!/usr/bin/env python3
"""Portfolio-Level Risk Preparation — Kelly Half スケールアップ前提条件計算

目的:
  Kelly Half スケールアップ発動前に必要な portfolio 水準の risk 指標を算出する。

  1. 戦略間の daily P&L 相関行列 → correlation > 0.7 のセルは独立エッジではない
  2. per-strategy DD, max DD, DD duration → 戦略別 stop-out rule 設計の根拠
  3. portfolio-level max DD projection → 全体の DD 上限判定
     - sum of strategy DDs (独立仮定) vs realized portfolio DD (非独立性の影響)

データソース:
  Render 本番 API: https://fx-ai-trader.onrender.com/api/demo/trades?limit=5000
  Filter:
    - is_shadow = 0 （Live のみ、Shadow 除外）
    - status = "CLOSED"
    - 非 XAU （pip 単位整合性）
    - entry_time >= 2026-04-08 （post-cutoff, clean-data phase）

出力:
  - knowledge-base/raw/audits/portfolio-risk-{YYYY-MM-DD}.md
    - 相関行列 (markdown table, 小数 2 桁)
    - HIGH_CORR pairs (> 0.7)
    - per-strategy DD 表 (N_days, max_DD, DD_duration_days, current_DD)
    - Portfolio DD summary
    - 推奨事項 (correlation clustering に基づく risk budget 配分)
  - stdout: summary

制約:
  - XAU 除外
  - is_shadow = 0 限定
  - pandas / numpy / scipy 使用可
  - ネットワーク不可時 graceful fail (exit code 2)

Usage:
    # 本番 API からフェッチして audit を生成
    python3 tools/portfolio_risk_prep.py

    # 別 API を参照
    python3 tools/portfolio_risk_prep.py --api https://fx-ai-trader.onrender.com

    # 別のカットオフ・相関閾値
    python3 tools/portfolio_risk_prep.py --cutoff 2026-04-10 --corr-threshold 0.6

    # JSON で stdout のみ（ファイル出力しない）
    python3 tools/portfolio_risk_prep.py --stdout-only --json

主要関数:
    fetch_trades(api, cutoff, limit) -> list[dict]
    build_daily_pnl_by_strategy(trades) -> pd.DataFrame
    compute_correlation_matrix(daily_df, min_days=10) -> tuple[pd.DataFrame, list[dict]]
    compute_per_strategy_dd(daily_df) -> pd.DataFrame
    compute_portfolio_dd(daily_df) -> dict
    build_markdown_report(...) -> str
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Allow local imports (modules/ / tools/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Try to reuse existing risk_analytics.strategy_correlation() if helpful.
# We still implement a daily-PnL variant here because strategy_correlation()
# aligns by index (per-trade), not by calendar day.
try:
    from modules import risk_analytics  # noqa: F401
    _HAS_RISK_ANALYTICS = True
except Exception:
    _HAS_RISK_ANALYTICS = False


# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_API = "https://fx-ai-trader.onrender.com"
DEFAULT_CUTOFF = "2026-04-08"
DEFAULT_CORR_THRESHOLD = 0.7
DEFAULT_MIN_DAYS = 10
DEFAULT_LIMIT = 5000
HTTP_TIMEOUT = 30


# ── HTTP helpers (mirror quant_readiness.py safety pattern) ───────────────────
class _SafeHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        # Keep scheme https only
        if not newurl.lower().startswith("https://"):
            raise urllib.error.URLError("refusing redirect to non-https")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_SAFE_OPENER = urllib.request.build_opener(_SafeHTTPRedirectHandler())


def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"invalid scheme: {parsed.scheme}")
    if not parsed.hostname:
        raise ValueError("empty hostname")


def _http_get_json(url: str, timeout: int = HTTP_TIMEOUT) -> dict:
    _validate_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": "portfolio_risk_prep/1.0"})
    # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
    with _SAFE_OPENER.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_trades(api: str, cutoff: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Fetch closed, non-shadow, non-XAU trades after cutoff from production API.

    Raises:
        ConnectionError: network unreachable (graceful-fail trigger)
    """
    qs = urllib.parse.urlencode({
        "limit": limit,
        "status": "closed",
        "date_from": cutoff,
    })
    url = f"{api.rstrip('/')}/api/demo/trades?{qs}"
    try:
        payload = _http_get_json(url)
    except (urllib.error.URLError, urllib.error.HTTPError,
            socket.timeout, socket.gaierror, ConnectionError) as e:
        raise ConnectionError(f"fetch_trades failed: {e} ({url})") from e

    raw = payload.get("trades") or []
    # Script-side filtering (API layer does not enforce these)
    filtered: list[dict] = []
    for t in raw:
        if str(t.get("status") or "").upper() != "CLOSED":
            continue
        if int(t.get("is_shadow") or 0) != 0:
            continue
        inst = t.get("instrument") or ""
        if "XAU" in inst:
            continue
        et = (t.get("entry_time") or "")
        if et < cutoff:
            continue
        filtered.append(t)
    return filtered


# ── Daily aggregation ─────────────────────────────────────────────────────────
def _parse_day(ts_str: str) -> str | None:
    """Extract YYYY-MM-DD from an ISO-ish timestamp."""
    if not ts_str:
        return None
    # Both 'YYYY-MM-DD HH:MM:SS' and 'YYYY-MM-DDTHH:MM:SS[Z]' are handled
    return ts_str[:10] if len(ts_str) >= 10 else None


def build_daily_pnl_by_strategy(trades: list[dict]) -> pd.DataFrame:
    """Aggregate pnl_pips into a (date x strategy) DataFrame.

    Uses exit_time (closed_at) for bucketing since a strategy's DD is realized
    on exit. Missing days become 0 (no trade → 0 P&L), aligned across strategies.
    """
    rows: list[dict] = []
    for t in trades:
        et = t.get("entry_type")
        if not et:
            continue
        day = _parse_day(t.get("exit_time") or t.get("entry_time") or "")
        if not day:
            continue
        try:
            pnl = float(t.get("pnl_pips") or 0.0)
        except (TypeError, ValueError):
            continue
        rows.append({"date": day, "strategy": et, "pnl": pnl})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    pivot = (
        df.groupby(["date", "strategy"])["pnl"].sum()
        .unstack(fill_value=0.0)
        .sort_index()
    )
    # Reindex to continuous date range so gaps become zero-P&L days
    if not pivot.empty:
        idx = pd.date_range(pivot.index.min(), pivot.index.max(), freq="D")
        pivot.index = pd.to_datetime(pivot.index)
        pivot = pivot.reindex(idx, fill_value=0.0)
        pivot.index = pivot.index.strftime("%Y-%m-%d")
    return pivot


# ── 1. Correlation matrix ─────────────────────────────────────────────────────
def compute_correlation_matrix(
    daily_df: pd.DataFrame,
    corr_threshold: float = DEFAULT_CORR_THRESHOLD,
    min_days: int = DEFAULT_MIN_DAYS,
) -> tuple[pd.DataFrame, list[dict]]:
    """Pearson correlation of daily P&L across strategies.

    Strategies with < min_days of non-zero days are excluded.
    Returns (correlation_matrix, high_corr_pairs).
    """
    if daily_df.empty:
        return pd.DataFrame(), []
    # Drop strategies whose non-zero-day count < min_days
    active_days = (daily_df != 0).sum(axis=0)
    kept = active_days[active_days >= min_days].index.tolist()
    df = daily_df[kept]
    if df.shape[1] < 2:
        return pd.DataFrame(index=kept, columns=kept), []
    corr = df.corr(method="pearson", min_periods=min_days).round(4)

    high_corr: list[dict] = []
    names = list(corr.columns)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            v = corr.loc[a, b]
            if pd.isna(v):
                continue
            if abs(v) > corr_threshold:
                high_corr.append({
                    "pair": [a, b],
                    "correlation": round(float(v), 4),
                    "direction": "positive" if v > 0 else "negative",
                })
    high_corr.sort(key=lambda r: abs(r["correlation"]), reverse=True)
    return corr, high_corr


# ── 2. Per-strategy drawdown ──────────────────────────────────────────────────
def _drawdown_series(cum: pd.Series) -> tuple[float, int, float]:
    """Return (max_dd, dd_duration_days, current_dd) from a cumulative-P&L series.

    max_dd: peak - trough (positive number, in pips).
    dd_duration_days: longest underwater stretch (peak -> recovery or end).
    current_dd: (running peak) - (last value). 0 if at new high.
    """
    if cum.empty:
        return 0.0, 0, 0.0
    values = cum.values.astype(float)
    peak = values[0]
    max_dd = 0.0
    longest = 0
    current_run = 0
    for v in values:
        if v >= peak:
            peak = v
            current_run = 0
        else:
            current_run += 1
            dd = peak - v
            if dd > max_dd:
                max_dd = dd
            if current_run > longest:
                longest = current_run
    current_dd = float(peak - values[-1])
    return float(max_dd), int(longest), float(current_dd)


def compute_per_strategy_dd(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Per-strategy DD table: n_days, max_dd, dd_duration_days, current_dd, total_pnl."""
    if daily_df.empty:
        return pd.DataFrame()
    records: list[dict] = []
    for strat in daily_df.columns:
        series = daily_df[strat]
        n_days = int((series != 0).sum())
        cum = series.cumsum()
        max_dd, duration, cur_dd = _drawdown_series(cum)
        records.append({
            "strategy": strat,
            "n_days": n_days,
            "total_pnl_pips": round(float(cum.iloc[-1]), 2),
            "max_dd_pips": round(max_dd, 2),
            "dd_duration_days": duration,
            "current_dd_pips": round(cur_dd, 2),
        })
    out = pd.DataFrame(records).sort_values("max_dd_pips", ascending=False)
    return out.reset_index(drop=True)


# ── 3. Portfolio DD ───────────────────────────────────────────────────────────
def compute_portfolio_dd(daily_df: pd.DataFrame) -> dict:
    """Equal-weight portfolio DD vs independent-sum DD.

    independent_sum_dd: naive worst-case assuming perfect independence
        (sum of per-strategy max_dd). This is a theoretical upper bound only
        if losses never overlap in time.
    realized_portfolio_dd: DD computed on the equal-weighted daily sum series.
    ratio: realized / independent_sum. Ratio ≥ 1 → correlation amplifies DD;
        ratio < 1 → diversification reduces DD.
    """
    if daily_df.empty:
        return {"insufficient": True}
    # Equal weight across strategies (1/K each day)
    k = daily_df.shape[1]
    portfolio = daily_df.sum(axis=1) / max(k, 1)
    cum = portfolio.cumsum()
    max_dd, duration, cur_dd = _drawdown_series(cum)

    # Independent-sum benchmark: sum of individual max DDs (scaled by equal weight)
    individual_dd = 0.0
    for s in daily_df.columns:
        md, _, _ = _drawdown_series(daily_df[s].cumsum())
        individual_dd += md
    independent_sum = individual_dd / max(k, 1)  # scaled for equal-weight comparability

    ratio = (max_dd / independent_sum) if independent_sum > 0 else None
    return {
        "insufficient": False,
        "n_days": int((portfolio != 0).sum()),
        "portfolio_total_pnl_pips": round(float(cum.iloc[-1]), 2),
        "portfolio_max_dd_pips": round(max_dd, 2),
        "portfolio_dd_duration_days": int(duration),
        "portfolio_current_dd_pips": round(cur_dd, 2),
        "independent_sum_dd_pips": round(float(independent_sum), 2),
        "dd_ratio_realized_over_independent": (
            round(float(ratio), 3) if ratio is not None else None
        ),
    }


# ── Report rendering ──────────────────────────────────────────────────────────
def _corr_table_md(corr: pd.DataFrame) -> str:
    if corr.empty:
        return "_(no strategies with sufficient data)_"
    cols = list(corr.columns)
    head = "| strategy | " + " | ".join(cols) + " |"
    sep = "|" + "---|" * (len(cols) + 1)
    lines = [head, sep]
    for r in cols:
        row = [r]
        for c in cols:
            v = corr.loc[r, c]
            row.append("—" if pd.isna(v) else f"{v:.2f}")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _dd_table_md(dd_df: pd.DataFrame) -> str:
    if dd_df.empty:
        return "_(no strategies)_"
    cols = ["strategy", "n_days", "total_pnl_pips",
            "max_dd_pips", "dd_duration_days", "current_dd_pips"]
    head = "| " + " | ".join(cols) + " |"
    sep = "|" + "---|" * len(cols)
    lines = [head, sep]
    for _, row in dd_df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def _recommendations(high_corr: list[dict], pf: dict, dd_df: pd.DataFrame) -> list[str]:
    recs: list[str] = []
    if high_corr:
        clusters: dict[str, set[str]] = {}
        for hp in high_corr:
            a, b = hp["pair"]
            clusters.setdefault(a, set()).add(b)
            clusters.setdefault(b, set()).add(a)
        top_pair = high_corr[0]
        recs.append(
            f"HIGH_CORR detected ({len(high_corr)} pairs > 0.7). "
            f"強相関ペア {top_pair['pair']} (ρ={top_pair['correlation']}) は "
            f"独立エッジとしてカウントせず、risk budget を共有させる。"
        )
        recs.append(
            "相関クラスタ単位で Kelly 分母を合算（same-cluster sizing）。"
            "K個の戦略全てに fractional Kelly を掛けると over-sized になる。"
        )
    else:
        recs.append(
            "HIGH_CORR ペアなし (> 0.7)。Kelly Half を各戦略に独立配分する余地あり。"
            "ただし N が小さい場合は相関推定自体が不安定なので保守運用。"
        )

    ratio = pf.get("dd_ratio_realized_over_independent")
    if ratio is not None:
        if ratio >= 0.9:
            recs.append(
                f"Portfolio DD ratio = {ratio:.2f} — 非独立性が強く、分散効果が乏しい。"
                "Kelly スケールアップ発動は 1/4 Kelly から始めるべき。"
            )
        elif ratio <= 0.6:
            recs.append(
                f"Portfolio DD ratio = {ratio:.2f} — 分散効果あり。"
                "Kelly Half を equal-weight 配分で運用可能（要 live 再検証）。"
            )
        else:
            recs.append(
                f"Portfolio DD ratio = {ratio:.2f} — 中程度の分散。"
                "Kelly Half 発動は可だが、DD 監視を daily で実施。"
            )

    if not dd_df.empty:
        worst = dd_df.iloc[0]
        recs.append(
            f"最大 DD 戦略: {worst['strategy']} (max_dd={worst['max_dd_pips']} pips, "
            f"duration={worst['dd_duration_days']}日)。"
            "戦略別 stop-out rule: max_dd × 1.5 を circuit-breaker にするのが目安。"
        )
        currently_underwater = dd_df[dd_df["current_dd_pips"] > 0]
        if not currently_underwater.empty:
            recs.append(
                f"現在 drawdown 中の戦略 ({len(currently_underwater)}件): "
                + ", ".join(currently_underwater["strategy"].tolist())
                + " — これらは Kelly スケールアップ対象から除外を推奨。"
            )
    return recs


def build_markdown_report(
    api: str,
    cutoff: str,
    corr_threshold: float,
    daily_df: pd.DataFrame,
    corr: pd.DataFrame,
    high_corr: list[dict],
    dd_df: pd.DataFrame,
    portfolio: dict,
    timestamp: str,
) -> str:
    lines: list[str] = []
    lines.append(f"# Portfolio Risk Preparation — {timestamp[:10]}")
    lines.append("")
    lines.append(
        "Kelly Half スケールアップ発動前に算出する portfolio 水準の risk 指標。"
        "(1) 戦略相関, (2) 戦略別 DD, (3) portfolio DD と独立仮定との乖離。"
    )
    lines.append("")
    lines.append("## Meta")
    lines.append(f"- API: `{api}`")
    lines.append(f"- Cutoff: `{cutoff}` (post-cutoff, clean-data phase)")
    lines.append(f"- Correlation threshold: `{corr_threshold}`")
    lines.append(f"- Generated: `{timestamp}`")
    if not daily_df.empty:
        lines.append(
            f"- Daily matrix: `{daily_df.shape[0]} days × {daily_df.shape[1]} strategies`"
        )
    lines.append("")

    lines.append("## 1. Daily P&L Correlation Matrix (Pearson)")
    lines.append("")
    lines.append(_corr_table_md(corr))
    lines.append("")
    lines.append(f"### HIGH_CORR pairs (|ρ| > {corr_threshold})")
    if high_corr:
        lines.append("")
        lines.append("| strategy_A | strategy_B | correlation | direction |")
        lines.append("|---|---|---|---|")
        for hp in high_corr:
            a, b = hp["pair"]
            lines.append(
                f"| {a} | {b} | {hp['correlation']:.2f} | {hp['direction']} |"
            )
    else:
        lines.append("")
        lines.append(f"_(なし — 閾値 {corr_threshold} を超えるペアなし)_")
    lines.append("")

    lines.append("## 2. Per-Strategy Drawdown")
    lines.append("")
    lines.append(_dd_table_md(dd_df))
    lines.append("")

    lines.append("## 3. Portfolio Drawdown")
    lines.append("")
    if portfolio.get("insufficient"):
        lines.append("_(データ不足)_")
    else:
        lines.append(
            f"- portfolio_max_dd_pips: **{portfolio['portfolio_max_dd_pips']}** "
            f"(duration {portfolio['portfolio_dd_duration_days']}日)"
        )
        lines.append(
            f"- portfolio_current_dd_pips: {portfolio['portfolio_current_dd_pips']}"
        )
        lines.append(
            f"- portfolio_total_pnl_pips: {portfolio['portfolio_total_pnl_pips']}"
        )
        lines.append(
            f"- independent_sum_dd_pips (equal-weight scaled): "
            f"{portfolio['independent_sum_dd_pips']}"
        )
        ratio = portfolio.get("dd_ratio_realized_over_independent")
        if ratio is not None:
            lines.append(
                f"- dd_ratio (realized / independent): **{ratio:.3f}** "
                f"{'→ 分散効果あり' if ratio < 0.6 else ('→ 非独立性が強い' if ratio >= 0.9 else '→ 中程度')}"
            )
    lines.append("")

    lines.append("## 4. Recommendations")
    lines.append("")
    for r in _recommendations(high_corr, portfolio, dd_df):
        lines.append(f"- {r}")
    lines.append("")
    lines.append("---")
    lines.append("_Generated by `tools/portfolio_risk_prep.py`. XAU 除外 / is_shadow=0 限定。_")
    lines.append("")
    return "\n".join(lines)


def build_stdout_summary(
    corr: pd.DataFrame,
    high_corr: list[dict],
    dd_df: pd.DataFrame,
    portfolio: dict,
    n_trades: int,
) -> str:
    lines = [
        "=== Portfolio Risk Prep — Summary ===",
        f"Trades loaded (post-filter): {n_trades}",
        f"Strategies in corr matrix:   {corr.shape[0]}",
        f"HIGH_CORR pairs:             {len(high_corr)}",
    ]
    if high_corr:
        top = high_corr[0]
        lines.append(
            f"  top pair: {top['pair'][0]} / {top['pair'][1]} "
            f"ρ={top['correlation']:.2f} ({top['direction']})"
        )
    if not dd_df.empty:
        w = dd_df.iloc[0]
        lines.append(
            f"Worst-DD strategy: {w['strategy']} "
            f"(max_dd={w['max_dd_pips']} pips, dur={w['dd_duration_days']}d)"
        )
    if not portfolio.get("insufficient"):
        lines.append(
            f"Portfolio max DD: {portfolio['portfolio_max_dd_pips']} pips "
            f"(duration {portfolio['portfolio_dd_duration_days']}d)"
        )
        r = portfolio.get("dd_ratio_realized_over_independent")
        if r is not None:
            lines.append(f"DD ratio (realized / independent-sum): {r:.3f}")
    return "\n".join(lines)


# ── Main orchestration ────────────────────────────────────────────────────────
def run(
    api: str = DEFAULT_API,
    cutoff: str = DEFAULT_CUTOFF,
    corr_threshold: float = DEFAULT_CORR_THRESHOLD,
    min_days: int = DEFAULT_MIN_DAYS,
    limit: int = DEFAULT_LIMIT,
    out_dir: Path | None = None,
    write_file: bool = True,
) -> dict:
    """Execute end-to-end and return a dict with report + artifacts."""
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    trades = fetch_trades(api, cutoff=cutoff, limit=limit)
    daily = build_daily_pnl_by_strategy(trades)
    corr, high_corr = compute_correlation_matrix(
        daily, corr_threshold=corr_threshold, min_days=min_days
    )
    dd_df = compute_per_strategy_dd(daily)
    pf = compute_portfolio_dd(daily)

    md = build_markdown_report(
        api=api, cutoff=cutoff, corr_threshold=corr_threshold,
        daily_df=daily, corr=corr, high_corr=high_corr,
        dd_df=dd_df, portfolio=pf, timestamp=ts,
    )
    summary = build_stdout_summary(corr, high_corr, dd_df, pf, len(trades))

    out_path: Path | None = None
    if write_file:
        day = ts[:10]
        target_dir = out_dir or (_PROJECT_ROOT / "knowledge-base" / "raw" / "audits")
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / f"portfolio-risk-{day}.md"
        out_path.write_text(md, encoding="utf-8")

    return {
        "timestamp": ts,
        "n_trades": len(trades),
        "daily_df_shape": list(daily.shape) if not daily.empty else [0, 0],
        "correlation_matrix": corr.round(4).to_dict() if not corr.empty else {},
        "high_corr_pairs": high_corr,
        "per_strategy_dd": dd_df.to_dict(orient="records") if not dd_df.empty else [],
        "portfolio_dd": pf,
        "markdown_path": str(out_path) if out_path else None,
        "stdout_summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Portfolio-level risk prep for Kelly Half scale-up decisions."
    )
    p.add_argument("--api", default=DEFAULT_API, help=f"Base URL (default {DEFAULT_API})")
    p.add_argument("--cutoff", default=DEFAULT_CUTOFF,
                   help=f"ISO date inclusive (default {DEFAULT_CUTOFF})")
    p.add_argument("--corr-threshold", type=float, default=DEFAULT_CORR_THRESHOLD,
                   help=f"|ρ| threshold (default {DEFAULT_CORR_THRESHOLD})")
    p.add_argument("--min-days", type=int, default=DEFAULT_MIN_DAYS,
                   help=f"Drop strategies with < N active days (default {DEFAULT_MIN_DAYS})")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                   help=f"Trade fetch cap (default {DEFAULT_LIMIT})")
    p.add_argument("--out-dir", default=None,
                   help="Override audit output directory (default knowledge-base/raw/audits/)")
    p.add_argument("--stdout-only", action="store_true",
                   help="Do not write markdown file; only print to stdout")
    p.add_argument("--json", action="store_true",
                   help="Emit full result as JSON to stdout (in addition to summary/MD)")
    args = p.parse_args(argv)

    try:
        result = run(
            api=args.api,
            cutoff=args.cutoff,
            corr_threshold=args.corr_threshold,
            min_days=args.min_days,
            limit=args.limit,
            out_dir=Path(args.out_dir) if args.out_dir else None,
            write_file=not args.stdout_only,
        )
    except ConnectionError as e:
        print(f"[portfolio_risk_prep] NETWORK FAIL: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"[portfolio_risk_prep] ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    print(result["stdout_summary"])
    if result.get("markdown_path"):
        print(f"\nWrote: {result['markdown_path']}")
    if args.json:
        print("\n--- JSON ---")
        print(json.dumps({k: v for k, v in result.items()
                          if k != "correlation_matrix"},
                         indent=2, default=str))
    return 0


if __name__ == "__main__":
    # Smoke run: when executed directly, hit production API and write the audit.
    # Use --stdout-only to skip file writes during local experiments.
    sys.exit(main())
