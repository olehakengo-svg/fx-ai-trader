"""round_number_major_level (台帳 #19) explore frozen statistics.

Protocol (frozen BEFORE observation):
  knowledge-base/wiki/decisions/round-number-level-explore-prereg-2026-07-31.md

Inputs (verbatim TV table rows):
  pass-1: knowledge-base/raw/bt-results/round-number-pass1-2026-07-31.json
          rows "date|side|level|entry|mfe3"
  pass-2: knowledge-base/raw/bt-results/round-number-pass2-2026-07-31.json
          rows "date|side|level|entry|net1|net3|net5|mfe3|mae3"

Staged execution (prereg §4): --stage headroom first (Gate A), then --stage primary.
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

RT = {
    "USDJPY": 2.14, "EURJPY": 2.50, "AUDJPY": 3.00,
    "EURUSD": 2.00, "GBPUSD": 4.53, "AUDUSD": 2.50,
}
RT_FLOOR = 1.30
HEADROOM_MULT = 10.0
MIN_SURVIVING_PAIRS = 3
N_FLOOR_EXPLORE = 200
EXPLORE_YEARS = list(range(2014, 2022))

E20_PANEL = REPO / "knowledge-base" / "raw" / "bt-results" / "e20" / "e20_carry_level.csv"
MOF_CSV = REPO / "data" / "external" / "mof_interventions.csv"
LFB_PASS2 = REPO / "knowledge-base" / "raw" / "bt-results" / "level-fb-d1-pass2-2026-07-31.json"
MARKUP_ANNUAL = 0.0050
MARKUP_SENS = (0.0025, 0.0075)
HOLD_CAL_DAYS = 4.2  # 3 trading days x 1.4

PASS1 = REPO / "knowledge-base" / "raw" / "bt-results" / "round-number-pass1-2026-07-31.json"
PASS2 = REPO / "knowledge-base" / "raw" / "bt-results" / "round-number-pass2-2026-07-31.json"
HEADROOM_VERDICT = REPO / "knowledge-base" / "raw" / "bt-results" / "round-number-headroom-verdict-2026-07-31.json"

PAIR_COL = {
    "USDJPY": "USD_JPY", "EURJPY": "EUR_JPY", "AUDJPY": "AUD_JPY",
    "EURUSD": "EUR_USD", "GBPUSD": "GBP_USD", "AUDUSD": "AUD_USD",
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
    problems = []
    if meta.get("first", "9999") > "2014-01-01":
        problems.append(f"{pair}: coverage FAIL first bar {meta.get('first')} (data-blocked)")
    if int(meta.get("wknd", "0")) != 0:
        problems.append(f"{pair}: weekend bars present ({meta['wknd']})")
    if int(meta.get("events", "0")) > 290:
        problems.append(f"{pair}: table capacity risk events={meta['events']}")
    return problems


def mof_explore_assert():
    """prereg §5 条件7: explore 窓に JPY 介入ゼロを機械 assert."""
    hits = []
    with open(MOF_CSV) as fh:
        for row in csv.DictReader(fh):
            if "JPY" in row["currency_pair"] and "2014-01-01" <= row["date"] <= "2021-12-31":
                hits.append(row["date"])
    return hits


def parse_rows(blob, n_fields):
    out, problems = {}, []
    for pair, blk in blob["pairs"].items():
        meta = parse_meta(blk["meta"])
        problems += qa_asserts(meta, pair)
        rows = []
        for r in blk["rows"]:
            f = [x.strip() for x in r.split("|")]
            if len(f) != n_fields:
                problems.append(f"{pair}: malformed row ({len(f)} fields): {r[:60]}")
                continue
            rows.append(f)
        out[pair] = rows
    return out, problems


def median(xs):
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def iso_week(date_str):
    y, w, _ = _dt.date.fromisoformat(date_str).isocalendar()
    return f"{y}-W{w:02d}"


def stage_headroom():
    mof = mof_explore_assert()
    if mof:
        return {"status": "ASSERT_FAIL", "reason": f"JPY interventions inside explore window: {mof}"}
    blob = json.loads(PASS1.read_text())
    data, problems = parse_rows(blob, 5)
    if problems:
        return {"status": "DATA_BLOCKED", "problems": problems}
    verdict = {"status": "OK", "mof_explore_interventions": 0, "pairs": {}}
    for pair, rows in sorted(data.items()):
        mfe3 = [float(f[4]) for f in rows]
        p50 = median(mfe3) if mfe3 else 0.0
        need = HEADROOM_MULT * RT[pair]
        verdict["pairs"][pair] = {
            "n": len(rows), "mfe3_p50": round(p50, 2), "need": round(need, 2),
            "pass": p50 >= need, "floor_pass": p50 >= HEADROOM_MULT * RT_FLOOR,
        }
    surviving = [p for p, v in verdict["pairs"].items() if v["pass"]]
    verdict["surviving_pairs"] = surviving
    verdict["family"] = ("PROCEED(pass-2 on surviving pairs)" if len(surviving) >= MIN_SURVIVING_PAIRS
                         else "KILL(sub-headroom: <3 pairs)")
    HEADROOM_VERDICT.write_text(json.dumps(verdict, indent=1))
    return verdict


def load_carry():
    table = {}
    with open(E20_PANEL) as fh:
        for row in csv.DictReader(fh):
            table[row["date"]] = row
    return table, sorted(table)


def carry_at(table, dates, date_str, col):
    import bisect
    if date_str in table and table[date_str].get(col):
        try:
            return float(table[date_str][col])
        except ValueError:
            pass
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
    r = carry_at(table, dates, date_str, PAIR_COL[pair])
    if r is None:
        return None
    sign = 1.0 if side == "L" else -1.0
    carry = sign * entry * (r / 100.0) / 365.0 * HOLD_CAL_DAYS / pip_size(pair)
    cost = entry * markup / 365.0 * HOLD_CAL_DAYS / pip_size(pair)
    return carry - cost


def week_block_permutation(events, key="net3", n_perm=N_PERM, seed=SEED):
    weeks = {}
    for e in events:
        weeks.setdefault(iso_week(e["date"]), []).append(e[key])
    keys = sorted(weeks)
    obs = mean([e[key] for e in events])
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
    return obs, (ge + 1) / (n_perm + 1), len(keys)


def lfb_overlap_share(events):
    """prereg §6: pair-ISO週 の #18 イベント重複 share."""
    if not LFB_PASS2.exists():
        return None
    lfb = json.loads(LFB_PASS2.read_text())
    lfb_weeks = set()
    for pair, blk in lfb["pairs"].items():
        for r in blk["rows"]:
            d = r.split("|")[0]
            lfb_weeks.add((pair, iso_week(d)))
    hit = sum(1 for e in events if (e["pair"], iso_week(e["date"])) in lfb_weeks)
    return round(hit / len(events), 3) if events else 0.0


def stage_primary():
    if not HEADROOM_VERDICT.exists():
        return {"status": "REFUSED", "reason": "run --stage headroom first (prereg §4)"}
    hv = json.loads(HEADROOM_VERDICT.read_text())
    if "PROCEED" not in hv.get("family", ""):
        return {"status": "REFUSED", "reason": f"headroom family verdict = {hv.get('family')}"}
    surviving = set(hv["surviving_pairs"])

    blob = json.loads(PASS2.read_text())
    data, problems = parse_rows(blob, 9)
    if problems:
        return {"status": "DATA_BLOCKED", "problems": problems}

    events = []
    for pair in sorted(data):
        if pair not in surviving:
            continue
        for f in data[pair]:
            events.append({"pair": pair, "date": f[0], "side": f[1], "level": float(f[2]),
                           "entry": float(f[3]), "net1": float(f[4]), "net3": float(f[5]),
                           "net5": float(f[6]), "mfe3": float(f[7]), "mae3": float(f[8])})
    events.sort(key=lambda e: e["date"])

    out = {"status": "OK", "n_pooled": len(events)}
    out["gate_B_n_floor"] = {"n": len(events), "floor": N_FLOOR_EXPLORE,
                             "pass": len(events) >= N_FLOOR_EXPLORE}
    if len(events) < N_FLOOR_EXPLORE:
        out["verdict"] = "UNDERPOWERED"
        return out

    obs, p, n_weeks = week_block_permutation(events)
    out["gate_C_primary"] = {"mean_net3_pips": round(obs, 3), "p_one_sided": round(p, 5),
                             "n_weeks_effective": n_weeks, "pass": obs > 0 and p < 0.05}

    table, dates = load_carry()
    def net_ev(markup, rt_map):
        vals, miss = [], 0
        for e in events:
            sw = swap_pips(e["pair"], e["side"], e["entry"], e["date"], table, dates, markup)
            if sw is None:
                miss += 1
                sw = 0.0
            vals.append(e["net3"] - rt_map[e["pair"]] + sw)
        return mean(vals), miss
    ev_base, miss = net_ev(MARKUP_ANNUAL, RT)
    ev_lo, _ = net_ev(MARKUP_SENS[0], RT)
    ev_hi, _ = net_ev(MARKUP_SENS[1], RT)
    ev_floor, _ = net_ev(MARKUP_ANNUAL, {k: RT_FLOOR for k in RT})
    out["gate_D_net_ev"] = {"ev_pips": round(ev_base, 3), "swap_missing_events": miss,
                            "ev_markup_025": round(ev_lo, 3), "ev_markup_075": round(ev_hi, 3),
                            "ev_rt_floor": round(ev_floor, 3),
                            "pass": ev_base > 0 and ev_lo > 0 and ev_hi > 0}

    weeks = {}
    for e in events:
        weeks[iso_week(e["date"])] = weeks.get(iso_week(e["date"]), 0.0) + e["net3"]
    total = sum(weeks.values())
    max_week, max_val = max(weeks.items(), key=lambda kv: abs(kv[1]))
    share = abs(max_val) / abs(total) if total else float("inf")
    out["gate_E_concentration"] = {"max_week": max_week, "share": round(share, 3), "pass": share <= 0.5}

    years = {}
    for e in events:
        years.setdefault(e["date"][:4], []).append(e["net3"])
    ymeans = {y: mean(v) for y, v in sorted(years.items())}
    pos = sum(1 for v in ymeans.values() if v > 0)
    loyo = {y: round(mean([e["net3"] for e in events if e["date"][:4] != y]), 3) for y in ymeans}
    out["gate_F_consistency"] = {"yearly_means": {y: round(v, 2) for y, v in ymeans.items()},
                                 "years_positive": f"{pos}/{len(ymeans)}", "loyo_means": loyo,
                                 "pass": pos >= 6 and all(v > 0 for v in loyo.values())}

    out["diag_horizons"] = {h: round(mean([e[h] for e in events]), 3) for h in ("net1", "net3", "net5")}
    out["diag_per_pair"] = {p: {"n": len([e for e in events if e["pair"] == p]),
                                "mean_net3": round(mean([e["net3"] for e in events if e["pair"] == p]), 2)}
                            for p in sorted({e["pair"] for e in events})}
    out["diag_side"] = {s: round(mean([e["net3"] for e in events if e["side"] == s]), 3) for s in ("L", "S")}
    out["diag_lfb_overlap_share"] = lfb_overlap_share(events)

    gates_pass = all(out[k]["pass"] for k in ("gate_B_n_floor", "gate_C_primary", "gate_D_net_ev",
                                              "gate_E_concentration", "gate_F_consistency"))
    out["verdict"] = "PASS_PENDING_KNIFE_EDGE" if gates_pass else "FAIL"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["headroom", "primary"], required=True)
    args = ap.parse_args(argv)
    res = stage_headroom() if args.stage == "headroom" else stage_primary()
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
