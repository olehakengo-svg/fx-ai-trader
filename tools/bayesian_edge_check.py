#!/usr/bin/env python3
"""
Bayesian Edge Check — sequential posterior analysis for Sentinel / Live edge.

Usage:
    python3 tools/bayesian_edge_check.py                      # shadow mode (Sentinel)
    python3 tools/bayesian_edge_check.py --live                # Live (is_shadow=0)
    python3 tools/bayesian_edge_check.py --json                # machine-readable
    python3 tools/bayesian_edge_check.py --min-n 10            # skip cells below N

Purpose
-------
Frequentist "wait for N >= 140" analysis blocks decision making for months.
This tool applies a Beta-Binomial conjugate posterior to shadow/live data so
Sentinel promotion candidates can be flagged the moment posterior evidence
is strong, not after an arbitrary sample-size threshold.

Read-only. Does NOT change production behavior. Consumes `/api/demo/trades`
(Render) and aggregates per (entry_type, instrument).

Model
-----
    prior:       Beta(alpha_0, beta_0)        (default: weak Beta(2, 2))
    likelihood:  Binomial(wins | n, p)
    posterior:   Beta(alpha_0 + wins, beta_0 + losses)

Outputs per cell:
    - N, wins, losses, observed WR
    - posterior mean, 95% CI (HDI approx from Monte Carlo)
    - P(WR > BEV | data)      -> break-even certainty
    - P(WR > BEV + 5pp | data) -> promotion-gate certainty
    - P(mean_pnl > 0 | data)  -> heuristic (uses observed mean_pnl as point estimate)

Promotion flag (PP_READY):
    P(WR > BEV + 5pp) > 0.90 AND N >= 30 AND observed mean_pnl > 0

Reference: decision page `defensive-mode-unwind-rule.md`, `edge-pipeline.md`.
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
from datetime import datetime
from typing import Any

try:
    import numpy as np
except ImportError:
    print("ERROR: numpy is required (`pip install numpy>=1.24`)", file=sys.stderr)
    sys.exit(2)

DEFAULT_API = "https://fx-ai-trader.onrender.com"
FIDELITY_CUTOFF = "2026-04-16T08:00:00"  # post-clean-slate start

# BEV_WR (percentage) per (pair, mode). Matches app.py _DEFAULT_BEV_WR.
BEV_WR = {
    ("USD_JPY", "scalp"):    50.0,
    ("USD_JPY", "daytrade"): 40.0,
    ("USD_JPY", "1h"):       35.0,
    ("EUR_USD", "scalp"):    45.0,
    ("EUR_USD", "daytrade"): 38.0,
    ("EUR_USD", "1h"):       33.0,
    ("GBP_USD", "scalp"):    52.0,
    ("GBP_USD", "daytrade"): 42.0,
    ("GBP_USD", "1h"):       36.0,
}
BEV_WR_FALLBACK = 50.0

# Prior: Beta(2, 2) is weakly informative (mode at 0.5, variance wider than uniform).
# Chosen over Beta(1,1) uniform because promotion needs positive evidence, not
# "no evidence against." Flip to --prior-uniform for Beta(1,1) if desired.
DEFAULT_PRIOR_ALPHA = 2.0
DEFAULT_PRIOR_BETA = 2.0

# Monte Carlo samples for posterior integrals.
MC_SAMPLES = 20000


# Allowlist of URL schemes to prevent file:// / ftp:// / gopher:// read via --api.
# (Semgrep: CWE-939. Dynamic --api value is validated before any urllib call.)
_ALLOWED_SCHEMES = ("http", "https")


def _validate_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"Refusing non-http(s) URL scheme: {parsed.scheme!r} (url={url!r})"
        )
    if not parsed.netloc:
        raise ValueError(f"URL must include a hostname (url={url!r})")


# Custom opener installed with only HTTP/HTTPS handlers — no file://, no ftp://.
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = True
_SSL_CTX.verify_mode = ssl.CERT_REQUIRED
_SAFE_OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(context=_SSL_CTX),
)


def fetch_trades(api: str, limit: int = 5000) -> list[dict]:
    url = f"{api.rstrip('/')}/api/demo/trades?limit={int(limit)}"
    try:
        _validate_url(url)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    req = urllib.request.Request(url, headers={"User-Agent": "bayesian-edge-check/1.0"})
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with _SAFE_OPENER.open(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"ERROR: API fetch failed ({e})", file=sys.stderr)
        sys.exit(1)
    trades = payload.get("trades", []) if isinstance(payload, dict) else payload
    return trades


def filter_trades(trades: list[dict], *, shadow: bool,
                  cutoff: str, exclude_xau: bool = True) -> list[dict]:
    kept = []
    for t in trades:
        if t.get("status") != "CLOSED":
            continue
        is_sh = int(t.get("is_shadow", 0) or 0)
        if shadow and is_sh != 1:
            continue
        if (not shadow) and is_sh != 0:
            continue
        et = (t.get("entry_time") or t.get("created_at") or "")
        if et < cutoff:
            continue
        inst = (t.get("instrument") or "")
        if exclude_xau and "XAU" in inst:
            continue
        kept.append(t)
    return kept


def bucket_by_strategy_pair(trades: list[dict]) -> dict[tuple, list[dict]]:
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for t in trades:
        et = t.get("entry_type") or "unknown"
        inst = t.get("instrument") or "unknown"
        buckets[(et, inst)].append(t)
    return buckets


def infer_mode(trades: list[dict]) -> str:
    """Majority mode among bucket trades (scalp / daytrade / 1h)."""
    counts: dict[str, int] = defaultdict(int)
    for t in trades:
        m = (t.get("mode") or "daytrade").lower()
        counts[m] += 1
    if not counts:
        return "daytrade"
    return max(counts.items(), key=lambda kv: kv[1])[0]


def bev_for(pair: str, mode: str) -> float:
    return BEV_WR.get((pair, mode), BEV_WR_FALLBACK)


def posterior_stats(wins: int, losses: int,
                    prior_a: float, prior_b: float,
                    bev_frac: float, gate_frac: float,
                    rng: np.random.Generator) -> dict:
    """Monte Carlo integrals on Beta(prior_a + wins, prior_b + losses)."""
    a = prior_a + wins
    b = prior_b + losses
    samples = rng.beta(a, b, size=MC_SAMPLES)
    mean = float(a / (a + b))
    # 95% equal-tailed credible interval (Beta quantiles via empirical quantiles)
    lo, hi = float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))
    p_above_bev = float(np.mean(samples > bev_frac))
    p_above_gate = float(np.mean(samples > gate_frac))
    return {
        "posterior_alpha": a,
        "posterior_beta": b,
        "posterior_mean": mean,
        "ci95_low": lo,
        "ci95_high": hi,
        "p_wr_above_bev": p_above_bev,
        "p_wr_above_gate": p_above_gate,
    }


def summarize_bucket(et: str, pair: str, trades: list[dict],
                     prior_a: float, prior_b: float,
                     rng: np.random.Generator) -> dict:
    n = len(trades)
    pnls = [float(t.get("pnl_pips", 0) or 0) for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    losses = n - wins
    obs_wr = (wins / n) if n else 0.0
    mean_pnl = (sum(pnls) / n) if n else 0.0
    mode = infer_mode(trades)
    bev = bev_for(pair, mode)
    gate = bev + 5.0  # promotion gate 5pp above BEV

    post = posterior_stats(wins, losses, prior_a, prior_b,
                           bev_frac=bev / 100.0,
                           gate_frac=gate / 100.0,
                           rng=rng)

    # Promotion readiness heuristic
    pp_ready = (post["p_wr_above_gate"] > 0.90
                and n >= 30
                and mean_pnl > 0)
    # Stop-loss flag: high confidence of failure
    force_demote_flag = (post["p_wr_above_bev"] < 0.10
                         and n >= 20)

    return {
        "entry_type": et,
        "instrument": pair,
        "mode": mode,
        "n": n,
        "wins": wins,
        "losses": losses,
        "observed_wr": obs_wr,
        "mean_pnl_pips": mean_pnl,
        "bev_wr_pct": bev,
        "gate_wr_pct": gate,
        **post,
        "pp_ready": pp_ready,
        "force_demote_flag": force_demote_flag,
    }


def print_human(rows: list[dict], *, channel: str) -> None:
    # Sort: pp_ready first, then descending p_wr_above_gate
    rows_sorted = sorted(rows,
                         key=lambda r: (not r["pp_ready"], -r["p_wr_above_gate"]))
    print(f"\n=== Bayesian Edge Check ({channel}) ===")
    print(f"Cutoff: {FIDELITY_CUTOFF}  |  Prior: Beta({DEFAULT_PRIOR_ALPHA},{DEFAULT_PRIOR_BETA})  |  Gate: WR > BEV+5pp")
    print()
    header = (f"{'strategy':30s} {'pair':8s} {'mode':9s} "
              f"{'N':>4s} {'W':>4s} {'WR%':>6s} {'BEV%':>6s} "
              f"{'post_mean':>10s} {'CI95':>16s} "
              f"{'P(>BEV)':>9s} {'P(>gate)':>9s} {'flags':s}")
    print(header)
    print("-" * len(header))
    for r in rows_sorted:
        flags = []
        if r["pp_ready"]:
            flags.append("PP_READY")
        if r["force_demote_flag"]:
            flags.append("FD_FLAG")
        flag_str = " ".join(flags) if flags else ""
        ci = f"[{r['ci95_low']*100:.1f},{r['ci95_high']*100:.1f}]"
        print(f"{r['entry_type'][:30]:30s} {r['instrument']:8s} {r['mode']:9s} "
              f"{r['n']:>4d} {r['wins']:>4d} {r['observed_wr']*100:>5.1f}% "
              f"{r['bev_wr_pct']:>5.1f}% "
              f"{r['posterior_mean']*100:>9.1f}% {ci:>16s} "
              f"{r['p_wr_above_bev']:>8.2f} {r['p_wr_above_gate']:>8.2f} {flag_str:s}")
    n_ready = sum(1 for r in rows if r["pp_ready"])
    n_fd = sum(1 for r in rows if r["force_demote_flag"])
    print(f"\nPP_READY candidates: {n_ready}")
    print(f"FD_FLAG candidates:  {n_fd}")
    print("\nNOTE: PP_READY is NECESSARY but NOT SUFFICIENT. Before promotion:")
    print("  1. Confirm 365d BT EV sign (lesson-orb-trap-bt-divergence)")
    print("  2. Check tier-master.md for FORCE_DEMOTED residue (lesson-kb-blind-pp-proposal)")
    print("  3. Submit pair-promoted-candidates update for review")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--api", default=DEFAULT_API, help="Production API base URL")
    parser.add_argument("--live", action="store_true",
                        help="Use Live (is_shadow=0) instead of Sentinel/Shadow")
    parser.add_argument("--min-n", type=int, default=10,
                        help="Skip (strategy,pair) cells below this N (default: 10)")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    parser.add_argument("--prior-uniform", action="store_true",
                        help="Use Beta(1,1) uniform prior instead of Beta(2,2)")
    parser.add_argument("--seed", type=int, default=0, help="Monte Carlo RNG seed")
    parser.add_argument("--limit", type=int, default=5000,
                        help="API trade-fetch limit (default: 5000)")
    args = parser.parse_args()

    prior_a = 1.0 if args.prior_uniform else DEFAULT_PRIOR_ALPHA
    prior_b = 1.0 if args.prior_uniform else DEFAULT_PRIOR_BETA
    rng = np.random.default_rng(args.seed)

    trades = fetch_trades(args.api, limit=args.limit)
    channel = "Live" if args.live else "Sentinel/Shadow"
    trades = filter_trades(trades, shadow=(not args.live), cutoff=FIDELITY_CUTOFF)
    buckets = bucket_by_strategy_pair(trades)

    rows: list[dict] = []
    for (et, pair), ts in buckets.items():
        if len(ts) < args.min_n:
            continue
        rows.append(summarize_bucket(et, pair, ts, prior_a, prior_b, rng))

    if args.json:
        print(json.dumps({
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "channel": channel,
            "cutoff": FIDELITY_CUTOFF,
            "prior": {"alpha": prior_a, "beta": prior_b},
            "min_n": args.min_n,
            "rows": rows,
        }, indent=2))
    else:
        print_human(rows, channel=channel)

    return 0


if __name__ == "__main__":
    sys.exit(main())
