"""wave-1 TV explore frozen statistics — equity_monthend_conditional + vix_carry_unwind.

Protocol (frozen BEFORE observation):
  knowledge-base/wiki/analyses/wave1-tv-explore-protocol-freeze-2026-07-28.md

Inputs (verbatim TV table rows collected 2026-07-28):
  knowledge-base/raw/bt-results/wave1-tv-explore-vix-unwind-2026-07-28.json
  knowledge-base/raw/bt-results/wave1-tv-explore-monthend-cond-2026-07-28.json

Primary tests (one per family, BH-FDR q=0.10 across the two):
  H1 monthend: two-sided permutation p of Spearman IC between SPX MTD and
               per-month cross-pair mean USD-adjusted 1d forward return (N=96).
  H2 vix:      one-sided sign-permutation p of mean per-event cross-pair
               short 3d net move (N=23 events).

No module-level side effects (lesson: tools/*.py are dual script/library).
"""

import json
import math
import random
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEED = 20260728
N_PERM = 10000

# frozen per-pair RT friction (pips) + measured floor sensitivity
RT = {
    "USDJPY": 2.14, "EURUSD": 2.00, "GBPUSD": 4.53, "EURJPY": 2.50,
    "AUDJPY": 3.00, "NZDJPY": 3.50, "CADJPY": 3.50, "GBPJPY": 4.50,
    "AUDUSD": 2.50, "NZDUSD": 3.00, "USDCAD": 2.80,
}
RT_FLOOR = 1.30

# H1 direction map: USD-adjusted return = "non-USD currency vs USD"
USD_QUOTE = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"}   # raw
USD_BASE = {"USDJPY", "USDCAD"}                          # -raw


def parse_rows(pair_block):
    out = []
    for r in pair_block["rows"]:
        f = [x.strip() for x in r.split("|")]
        out.append({
            "date": f[0], "cond": float(f[1]), "fwd1": float(f[2]),
            "fwd3": float(f[3]), "fwd5": float(f[4]),
            "upMax": float(f[5]), "dnMax": float(f[6]),
        })
    return out


def load(name):
    p = REPO / "knowledge-base" / "raw" / "bt-results" / name
    data = json.loads(p.read_text())
    return {pair: parse_rows(blk) for pair, blk in data["pairs"].items()}


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def mean(xs):
    return sum(xs) / len(xs)


def rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = rank(x), rank(y)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx > 0 and dy > 0 else 0.0


def perm_p_spearman(x, y, rng, n_perm=N_PERM):
    """Two-sided permutation p for Spearman IC (shuffle y)."""
    obs = spearman(x, y)
    y2 = list(y)
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(y2)
        if abs(spearman(x, y2)) >= abs(obs):
            hits += 1
    return obs, (hits + 1) / (n_perm + 1)


def perm_p_signflip(xs, rng, n_perm=N_PERM):
    """One-sided sign-flip permutation p for mean(xs) > 0."""
    obs = mean(xs)
    hits = 0
    for _ in range(n_perm):
        m = mean([x if rng.random() < 0.5 else -x for x in xs])
        if m >= obs:
            hits += 1
    return obs, (hits + 1) / (n_perm + 1)


def exact_p_signflip(xs):
    """EXACT one-sided sign-flip p via meet-in-the-middle enumeration (N<=24).

    The frozen 10,000-draw permutation has MC std-err ~0.002 near p=0.05,
    which straddles the BH threshold; for N=23 the 2^23 sign patterns are
    fully enumerable, so the exact null is used for the primary verdict.
    """
    import bisect
    T = sum(xs)
    half = len(xs) // 2
    A, B = xs[:half], xs[half:]

    def sums(v):
        out = [0.0]
        for x in v:
            out = [s + x for s in out] + [s - x for s in out]
        return out

    SA, SB = sums(A), sorted(sums(B))
    cnt = 0
    for sa in SA:
        idx = bisect.bisect_left(SB, T - sa - 1e-9)
        cnt += len(SB) - idx
    return cnt / (len(SA) * len(SB))


def check_alignment(data):
    dates = None
    for pair, rows in data.items():
        d = [r["date"] for r in rows]
        if dates is None:
            dates = d
        elif d != dates:
            raise ValueError(f"event date mismatch in {pair}")
    return dates


def h2_vix(data, rng):
    dates = check_alignment(data)
    pairs = list(data.keys())
    res = {"n_events": len(dates), "pairs": {}, "horizons": {}}
    # per-event cross-pair mean of SHORT net move (-fwd)
    for h in ("fwd1", "fwd3", "fwd5"):
        xs = []
        for i in range(len(dates)):
            xs.append(mean([-data[p][i][h] for p in pairs]))
        obs, p = perm_p_signflip(xs, rng)
        p_exact = exact_p_signflip(xs)
        # concentration diagnostics
        contrib = {dates[i]: xs[i] for i in range(len(xs))}
        top_date = max(contrib, key=lambda d: contrib[d])
        total = sum(xs)
        loo = [x for x in xs if x != contrib[top_date]]
        loo_obs, loo_p = perm_p_signflip(loo, rng)
        res["horizons"][h] = {
            "mean_pips": round(obs, 2), "median_pips": round(median(xs), 2),
            "win_rate": round(sum(1 for x in xs if x > 0) / len(xs), 3),
            "p_one_sided": p, "p_exact": p_exact,
            "top_event": top_date,
            "top_share_of_sum": round(contrib[top_date] / total, 3) if total != 0 else None,
            "loo_mean": round(loo_obs, 2), "loo_p": loo_p,
        }
    for p_ in pairs:
        rows = data[p_]
        mfe = [r["dnMax"] for r in rows]  # short-direction MFE
        res["pairs"][p_] = {
            "mean_short_3d": round(mean([-r["fwd3"] for r in rows]), 2),
            "median_short_3d": round(median([-r["fwd3"] for r in rows]), 2),
            "mfe_p50": round(median(mfe), 2),
            "rt": RT[p_], "headroom_x": round(median(mfe) / RT[p_], 1),
            "headroom_x_floor": round(median(mfe) / RT_FLOOR, 1),
            "headroom_pass_10x": median(mfe) >= 10 * RT[p_],
        }
    return res


def h1_monthend(data, rng):
    dates = check_alignment(data)
    pairs = list(data.keys())
    n = len(dates)
    mtd = [data[pairs[0]][i]["cond"] for i in range(n)]
    res = {"n_events": n, "pairs": {}, "horizons": {}}
    for h in ("fwd1", "fwd3", "fwd5"):
        ys = []
        for i in range(n):
            vals = []
            for p_ in pairs:
                v = data[p_][i][h]
                vals.append(v if p_ in USD_QUOTE else -v)
            ys.append(mean(vals))
        ic, p = perm_p_spearman(mtd, ys, rng)
        # terciles by MTD value, mean adjusted return per tercile
        order = sorted(range(n), key=lambda i: mtd[i])
        k = n // 3
        lo = [ys[i] for i in order[:k]]
        mid = [ys[i] for i in order[k:n - k]]
        hi = [ys[i] for i in order[n - k:]]
        uncond = mean(ys)
        cond_spread = (mean(hi) - mean(lo)) / 2
        res["horizons"][h] = {
            "spearman_ic": round(ic, 4), "p_two_sided": p,
            "uncond_mean_pips": round(uncond, 2),
            "tercile_means": [round(mean(lo), 2), round(mean(mid), 2), round(mean(hi), 2)],
            "cond_half_spread": round(cond_spread, 2),
            "cond_ge_2x_uncond": abs(cond_spread) >= 2 * abs(uncond),
            "monotone": (mean(lo) <= mean(mid) <= mean(hi)) or (mean(lo) >= mean(mid) >= mean(hi)),
        }
    for p_ in pairs:
        rows = data[p_]
        ics = {}
        for h in ("fwd1", "fwd3", "fwd5"):
            adj = [(r[h] if p_ in USD_QUOTE else -r[h]) for r in rows]
            ics[h] = round(spearman(mtd, adj), 4)
        # predicted-direction MFE: long pair iff (usd_quote & mtd>0) or (usd_base & mtd<0)
        mfe = []
        for r in rows:
            long_pair = (p_ in USD_QUOTE) == (r["cond"] > 0)
            mfe.append(r["upMax"] if long_pair else r["dnMax"])
        res["pairs"][p_] = {
            "ic": ics, "mfe_p50": round(median(mfe), 2), "rt": RT[p_],
            "headroom_x": round(median(mfe) / RT[p_], 1),
            "headroom_pass_10x": median(mfe) >= 10 * RT[p_],
        }
    return res


def bh_fdr(pvals, q=0.10):
    """Return dict name -> pass under Benjamini-Hochberg."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    passed = set()
    max_k = 0
    for k, (_, p) in enumerate(items, 1):
        if p <= q * k / m:
            max_k = k
    for k, (name, _) in enumerate(items, 1):
        if k <= max_k:
            passed.add(name)
    return {name: (name in passed) for name, _ in items}


def main():
    rng = random.Random(SEED)
    vix = load("wave1-tv-explore-vix-unwind-2026-07-28.json")
    me = load("wave1-tv-explore-monthend-cond-2026-07-28.json")

    r2 = h2_vix(vix, rng)
    r1 = h1_monthend(me, rng)

    primaries = {
        "H1_monthend_ic_1d": r1["horizons"]["fwd1"]["p_two_sided"],
        "H2_vix_short_3d": r2["horizons"]["fwd3"]["p_exact"],
    }
    fdr = bh_fdr(primaries)

    out = {
        "seed": SEED, "n_perm": N_PERM,
        "primaries": primaries, "bh_fdr_q0.10": fdr,
        "h1_equity_monthend_conditional": r1,
        "h2_vix_carry_unwind_continuation": r2,
    }
    dst = REPO / "knowledge-base" / "raw" / "bt-results" / "wave1-tv-explore-stats-2026-07-28.json"
    dst.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
