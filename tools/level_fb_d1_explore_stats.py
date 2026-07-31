"""level_failed_break_d1 (台帳 #18) explore frozen statistics.

Protocol (frozen BEFORE observation):
  knowledge-base/wiki/decisions/level-failed-break-d1-explore-prereg-2026-07-31.md

Inputs (verbatim TV table rows):
  pass-1: knowledge-base/raw/bt-results/level-fb-d1-pass1-2026-07-31.json
          rows "date|side|level|entry|mfe5"   (headroom only — no fwd net move)
  pass-2: knowledge-base/raw/bt-results/level-fb-d1-pass2-2026-07-31.json
          rows "date|side|level|entry|net1|net3|net5|net10|mfe5|mae5"

Staged execution (pre-reg §4): run --stage headroom first (Gate A), then
--stage primary only for pairs that survived. The tool refuses to run the
primary stage without an existing headroom verdict file.

No module-level side effects (lesson: tools/*.py are dual script/library).
"""

import argparse
import csv
import datetime as _dt
import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEED = 20260731
N_PERM = 10000

# frozen per-pair RT friction (pips) — wave-1 protocol values, prereg §5 Gate A
RT = {
    "USDJPY": 2.14, "EURUSD": 2.00, "GBPUSD": 4.53, "EURJPY": 2.50,
    "AUDJPY": 3.00, "AUDUSD": 2.50, "NZDUSD": 3.00, "USDCAD": 2.80,
}
RT_FLOOR = 1.30
HEADROOM_MULT = 10.0
MIN_SURVIVING_PAIRS = 3
N_FLOOR_EXPLORE = 200
EXPLORE_YEARS = list(range(2014, 2022))

# swap accounting (prereg §6): e20 BIS CBPOL panel + frozen markup
E20_PANEL = REPO / "knowledge-base" / "raw" / "bt-results" / "e20" / "e20_carry_level.csv"
MARKUP_ANNUAL = 0.0050           # 0.50%/yr against position
MARKUP_SENS = (0.0025, 0.0075)   # ±50%
HOLD_CAL_DAYS = 7.0              # 5 trading days × 1.4

PASS1 = REPO / "knowledge-base" / "raw" / "bt-results" / "level-fb-d1-pass1-2026-07-31.json"
PASS2 = REPO / "knowledge-base" / "raw" / "bt-results" / "level-fb-d1-pass2-2026-07-31.json"
HEADROOM_VERDICT = REPO / "knowledge-base" / "raw" / "bt-results" / "level-fb-d1-headroom-verdict-2026-07-31.json"

# e20 panel column per pair key (panel uses underscore names)
PAIR_COL = {
    "USDJPY": "USD_JPY", "EURUSD": "EUR_USD", "GBPUSD": "GBP_USD",
    "EURJPY": "EUR_JPY", "AUDJPY": "AUD_JPY", "AUDUSD": "AUD_USD",
    "NZDUSD": "NZD_USD", "USDCAD": "USD_CAD",
}


def pip_size(pair):
    return 0.01 if pair.endswith("JPY") else 0.0001


def parse_meta(meta_line):
    out = {}
    for part in meta_line.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def qa_asserts(meta, pair):
    """Feed QA (prereg §3): coverage / weekend bars / capacity."""
    problems = []
    first = meta.get("first", "9999-12-31")
    if first > "2014-01-01":
        problems.append(f"{pair}: coverage FAIL first bar {first} > 2014-01-01 (data-blocked)")
    if int(meta.get("wknd", "0")) != 0:
        problems.append(f"{pair}: weekend bars present ({meta['wknd']}) — offsets invalid")
    if int(meta.get("events", "0")) > 290:
        problems.append(f"{pair}: table capacity risk events={meta['events']}")
    return problems


def parse_pass1(blob):
    out = {}
    problems = []
    for pair, blk in blob["pairs"].items():
        meta = parse_meta(blk["meta"])
        problems += qa_asserts(meta, pair)
        rows = []
        for r in blk["rows"]:
            f = [x.strip() for x in r.split("|")]
            rows.append({"date": f[0], "side": f[1], "level": float(f[2]),
                         "entry": float(f[3]), "mfe5": float(f[4])})
        out[pair] = rows
    return out, problems


def parse_pass2(blob):
    out = {}
    problems = []
    for pair, blk in blob["pairs"].items():
        meta = parse_meta(blk["meta"])
        problems += qa_asserts(meta, pair)
        rows = []
        for r in blk["rows"]:
            f = [x.strip() for x in r.split("|")]
            rows.append({
                "date": f[0], "side": f[1], "level": float(f[2]), "entry": float(f[3]),
                "net1": float(f[4]), "net3": float(f[5]), "net5": float(f[6]),
                "net10": float(f[7]), "mfe5": float(f[8]), "mae5": float(f[9]),
            })
        out[pair] = rows
    return out, problems


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def iso_week(date_str):
    d = _dt.date.fromisoformat(date_str)
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def stage_headroom():
    blob = json.loads(PASS1.read_text())
    data, problems = parse_pass1(blob)
    if problems:
        return {"status": "DATA_BLOCKED", "problems": problems}
    verdict = {"status": "OK", "pairs": {}}
    for pair, rows in sorted(data.items()):
        p50 = median([r["mfe5"] for r in rows]) if rows else 0.0
        need = HEADROOM_MULT * RT[pair]
        ok = p50 >= need
        verdict["pairs"][pair] = {
            "n": len(rows), "mfe5_p50": round(p50, 2), "need": round(need, 2),
            "pass": ok, "floor_need": round(HEADROOM_MULT * RT_FLOOR, 2),
            "floor_pass": p50 >= HEADROOM_MULT * RT_FLOOR,
        }
    surviving = [p for p, v in verdict["pairs"].items() if v["pass"]]
    verdict["surviving_pairs"] = surviving
    if len(surviving) < MIN_SURVIVING_PAIRS:
        verdict["family"] = "KILL(sub-headroom: <3 pairs)"
    else:
        verdict["family"] = "PROCEED(pass-2 on surviving pairs)"
    HEADROOM_VERDICT.write_text(json.dumps(verdict, indent=1))
    return verdict


def load_carry():
    table = {}
    with open(E20_PANEL) as fh:
        for row in csv.DictReader(fh):
            table[row["date"]] = row
    dates = sorted(table)
    return table, dates


def carry_at(table, dates, date_str, col):
    # daily ffill: walk back to last available date
    if date_str in table and table[date_str].get(col):
        try:
            return float(table[date_str][col])
        except ValueError:
            pass
    import bisect
    i = bisect.bisect_right(dates, date_str) - 1
    while i >= 0:
        v = table[dates[i]].get(col)
        if v:
            try:
                return float(v)
            except ValueError:
                pass
        i -= 1
    return None


def swap_pips(pair, side, entry, date_str, table, dates, markup=MARKUP_ANNUAL):
    col = PAIR_COL[pair]
    r = carry_at(table, dates, date_str, col)
    if r is None:
        return None
    sign = 1.0 if side == "L" else -1.0
    carry = sign * entry * (r / 100.0) / 365.0 * HOLD_CAL_DAYS / pip_size(pair)
    cost = entry * markup / 365.0 * HOLD_CAL_DAYS / pip_size(pair)
    return carry - cost


def week_block_permutation(events, n_perm=N_PERM, seed=SEED):
    """One-sided sign-flip permutation p for mean(net5) > 0, flipping whole ISO weeks."""
    weeks = {}
    for e in events:
        weeks.setdefault(iso_week(e["date"]), []).append(e["net5"])
    keys = sorted(weeks)
    obs = mean([x for e in events for x in [e["net5"]]])
    rng = random.Random(seed)
    n = len(events)
    ge = 0
    for _ in range(n_perm):
        tot = 0.0
        for k in keys:
            s = sum(weeks[k])
            tot += s if rng.random() < 0.5 else -s
        if tot / n >= obs:
            ge += 1
    p = (ge + 1) / (n_perm + 1)
    return obs, p, len(keys)


def stage_primary():
    if not HEADROOM_VERDICT.exists():
        return {"status": "REFUSED", "reason": "headroom verdict missing — run --stage headroom first (prereg §4)"}
    hv = json.loads(HEADROOM_VERDICT.read_text())
    if "PROCEED" not in hv.get("family", ""):
        return {"status": "REFUSED", "reason": f"headroom family verdict = {hv.get('family')}"}
    surviving = set(hv["surviving_pairs"])

    blob = json.loads(PASS2.read_text())
    data, problems = parse_pass2(blob)
    if problems:
        return {"status": "DATA_BLOCKED", "problems": problems}

    events = []
    for pair in sorted(data):
        if pair not in surviving:
            continue
        for r in data[pair]:
            e = dict(r)
            e["pair"] = pair
            events.append(e)
    events.sort(key=lambda e: e["date"])

    out = {"status": "OK", "n_pooled": len(events)}

    # Gate B: power floor
    out["gate_B_n_floor"] = {"n": len(events), "floor": N_FLOOR_EXPLORE,
                             "pass": len(events) >= N_FLOOR_EXPLORE}
    if len(events) < N_FLOOR_EXPLORE:
        out["verdict"] = "UNDERPOWERED"
        return out

    # Gate C: primary
    obs, p, n_weeks = week_block_permutation(events)
    out["gate_C_primary"] = {"mean_net5_pips": round(obs, 3), "p_one_sided": round(p, 5),
                             "n_weeks_effective": n_weeks, "pass": obs > 0 and p < 0.05}

    # Gate D: net EV (RT theoretical table + historical swap proxy)
    table, dates = load_carry()
    def net_ev(markup, rt_map):
        vals, miss = [], 0
        for e in events:
            sw = swap_pips(e["pair"], e["side"], e["entry"], e["date"], table, dates, markup)
            if sw is None:
                miss += 1
                sw = 0.0
            vals.append(e["net5"] - rt_map[e["pair"]] + sw)
        return mean(vals), miss
    ev_base, miss = net_ev(MARKUP_ANNUAL, RT)
    ev_lo, _ = net_ev(MARKUP_SENS[0], RT)
    ev_hi, _ = net_ev(MARKUP_SENS[1], RT)
    ev_floor, _ = net_ev(MARKUP_ANNUAL, {k: RT_FLOOR for k in RT})
    out["gate_D_net_ev"] = {
        "ev_pips": round(ev_base, 3), "swap_missing_events": miss,
        "ev_markup_025": round(ev_lo, 3), "ev_markup_075": round(ev_hi, 3),
        "ev_rt_floor": round(ev_floor, 3),
        "pass": ev_base > 0 and ev_lo > 0 and ev_hi > 0,
    }

    # Gate E: single-week concentration
    weeks = {}
    for e in events:
        weeks.setdefault(iso_week(e["date"]), 0.0)
        weeks[iso_week(e["date"])] += e["net5"]
    total = sum(weeks.values())
    max_week, max_val = max(weeks.items(), key=lambda kv: abs(kv[1]))
    share = abs(max_val) / abs(total) if total else float("inf")
    out["gate_E_concentration"] = {"max_week": max_week, "share": round(share, 3),
                                   "pass": share <= 0.5}

    # Gate F: yearly consistency + LOYO
    years = {}
    for e in events:
        years.setdefault(e["date"][:4], []).append(e["net5"])
    ymeans = {y: mean(v) for y, v in sorted(years.items())}
    pos = sum(1 for v in ymeans.values() if v > 0)
    loyo = {}
    for y in ymeans:
        rest = [x for e in events for x in [e["net5"]] if e["date"][:4] != y]
        loyo[y] = round(mean(rest), 3)
    out["gate_F_consistency"] = {
        "yearly_means": {y: round(v, 2) for y, v in ymeans.items()},
        "years_positive": f"{pos}/{len(ymeans)}",
        "loyo_means": loyo,
        "pass": pos >= 6 and all(v > 0 for v in loyo.values()),
    }

    # diagnostics (non-binding, per prereg: other horizons / per-pair / side split)
    out["diag_horizons"] = {h: round(mean([e[h] for e in events]), 3)
                            for h in ("net1", "net3", "net5", "net10")}
    out["diag_per_pair"] = {p: {"n": len([e for e in events if e["pair"] == p]),
                                 "mean_net5": round(mean([e["net5"] for e in events if e["pair"] == p]), 2)}
                            for p in sorted({e["pair"] for e in events})}
    out["diag_side"] = {s: round(mean([e["net5"] for e in events if e["side"] == s]), 3)
                        for s in ("L", "S")}

    gates_pass = all(out[k]["pass"] for k in
                     ("gate_B_n_floor", "gate_C_primary", "gate_D_net_ev",
                      "gate_E_concentration", "gate_F_consistency"))
    out["verdict"] = ("PASS_PENDING_KNIFE_EDGE" if gates_pass else "FAIL")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["headroom", "primary"], required=True)
    args = ap.parse_args(argv)
    res = stage_headroom() if args.stage == "headroom" else stage_primary()
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
