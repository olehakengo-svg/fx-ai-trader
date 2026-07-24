#!/usr/bin/env python3
"""W1-F1: Fetch official MoF Japan FX intervention history (外国為替平衡操作の実施状況).

Sources (Ministry of Finance, Japan):
  - Full daily history CSV (April 1991 - latest completed quarter):
      https://www.mof.go.jp/policy/international_policy/reference/feio/foreign_exchange_intervention_operations.csv
  - Monthly aggregate disclosures (cover the period after the last quarterly
    daily disclosure; amount only, no dates/pair):
      https://www.mof.go.jp/policy/international_policy/reference/feio/data/monthly/index.html

Outputs:
  - data/external/mof_interventions.csv  (normalized)
  - bt-results/mof_intervention_w1f1-<date>.json (feasibility stats)

No edge analysis is performed here (W1-F1 scope = data + design feasibility).
"""

import csv
import datetime as dt
import io
import json
import re
import subprocess
import sys

BASE = "https://www.mof.go.jp/policy/international_policy/reference/feio"
CSV_URL = f"{BASE}/foreign_exchange_intervention_operations.csv"
MONTHLY_INDEX_URL = f"{BASE}/data/monthly/index.html"
MONTHLY_PAGE_URL = f"{BASE}/data/monthly/{{stamp}}.html"

REPO = "/Users/jg-n-012/test/fx-ai-trader"
OUT_CSV = f"{REPO}/data/external/mof_interventions.csv"
OUT_JSON = f"{REPO}/bt-results/mof_intervention_w1f1-2026-07-24.json"

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

# English currency-name -> ISO-ish code
CCY_MAP = {
    "US dollar": "USD",
    "Japanese yen": "JPY",
    "German mark": "DEM",
    "Deutsche mark": "DEM",
    "Indonesian rupiah": "IDR",
    "euro": "EUR",
    "Euro": "EUR",
}
# Pair-ordering precedence (standard FX quote convention)
PAIR_PRECEDENCE = ["EUR", "GBP", "AUD", "NZD", "USD", "CAD", "CHF", "DEM", "JPY", "IDR"]

EPISODE_GAP_DAYS = 30  # gap >= this many calendar days starts a new episode


def fetch(url: str) -> bytes:
    """Download a URL with curl; raise on non-2xx or empty body."""
    proc = subprocess.run(
        ["curl", "-sS", "--fail", "--max-time", "60", url],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: rc={proc.returncode} stderr={proc.stderr.decode('utf-8', 'replace')[:500]}")
    if not proc.stdout:
        raise RuntimeError(f"empty body for {url}")
    return proc.stdout


def decode_mof(raw: bytes) -> str:
    """MoF pages/CSV are CP932 (Shift-JIS superset); some pages are UTF-8."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp932")  # raises on failure — no silent fallback


def parse_currency_pair(english_text: str):
    """Parse e.g. 'the US dollar (sold) the Japanese yen (bought)'.

    Returns (pair_str like 'USD/JPY', direction_str like 'sell_USD_buy_JPY').
    """
    hits = re.findall(
        r"(US dollar|Japanese yen|German mark|Deutsche mark|Indonesian rupiah|[Ee]uro)\s*\((sold|bought)\)",
        english_text,
    )
    if len(hits) != 2:
        raise ValueError(f"cannot parse currency-pair text: {english_text!r} (hits={hits})")
    legs = {}
    for name, action in hits:
        code = CCY_MAP[name if name in CCY_MAP else name.capitalize()]
        legs[code] = action
    codes = sorted(legs.keys(), key=PAIR_PRECEDENCE.index)
    pair = f"{codes[0]}/{codes[1]}"
    sold = [c for c, a in legs.items() if a == "sold"]
    bought = [c for c, a in legs.items() if a == "bought"]
    if len(sold) != 1 or len(bought) != 1:
        raise ValueError(f"bad sold/bought split in: {english_text!r}")
    direction = f"sell_{sold[0]}_buy_{bought[0]}"
    return pair, direction


def parse_amount_oku(cell: str) -> float:
    """'28,382' -> 28382.0 (oku-yen = 100 million yen units)."""
    v = cell.replace(",", "").replace('"', "").strip()
    if not v:
        raise ValueError("empty amount cell")
    return float(v)


def parse_daily_csv(text: str):
    """Parse the MoF full-history CSV. Returns (events, quarter_totals, last_quarter_end).

    events: list of dicts with date/pair/direction/amount_oku
    quarter_totals: list of (label_en, total_oku) for cross-validation
    """
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    events = []
    quarter_totals = []
    cur_year = None
    cur_month = None
    last_quarter_end = None
    for row in rows:
        if len(row) < 9:
            continue
        year_en, month_en, day_en, amount, ccy_en = row[3].strip(), row[4].strip(), row[5].strip(), row[6].strip(), row[8].strip()
        # quarterly total rows: english label like 'April - June 1991' in col 3, no day
        if year_en and not day_en and "-" in year_en and amount != "":
            quarter_totals.append((year_en, parse_amount_oku(amount)))
            m = re.search(r"(\w+)\s*-\s*(\w+)\s+(\d{4})", year_en)
            if m:
                end_month = MONTH_MAP[m.group(2).lower()[:4] if m.group(2).lower().startswith("sept") else m.group(2).lower()[:3]]
                yr = int(m.group(3))
                nxt = dt.date(yr + (1 if end_month == 12 else 0), 1 if end_month == 12 else end_month + 1, 1)
                q_end = nxt - dt.timedelta(days=1)
                if last_quarter_end is None or q_end > last_quarter_end:
                    last_quarter_end = q_end
            continue
        # daily rows: numeric day + currency text present (skips header row 'Day'/'Currency pairs')
        if day_en.isdigit() and ccy_en:
            if year_en:
                cur_year = int(year_en)
            if month_en:
                cur_month = MONTH_MAP[month_en.lower()[:4] if month_en.lower().startswith("sept") else month_en.lower()[:3]]
            if cur_year is None or cur_month is None:
                raise ValueError(f"daily row before year/month context: {row}")
            date = dt.date(cur_year, cur_month, int(day_en))
            pair, direction = parse_currency_pair(ccy_en)
            events.append({
                "date": date,
                "currency_pair": pair,
                "direction": direction,
                "amount_oku": parse_amount_oku(amount),
            })
    return events, quarter_totals, last_quarter_end


def parse_wareki_date(s: str) -> dt.date:
    """'令和8年4月28日' -> date(2026,4,28). Also handles 平成."""
    m = re.search(r"(令和|平成)(\d+|元)年(\d+)月(\d+)日", s)
    if not m:
        raise ValueError(f"cannot parse wareki date: {s!r}")
    era, y, mo, d = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
    yy = 1 if y == "元" else int(y)
    year = (2018 + yy) if era == "令和" else (1988 + yy)
    return dt.date(year, mo, d)


def parse_amount_yen_text(s: str) -> float:
    """'11兆7,349億' or '28,382億' or '0' (yen) -> oku-yen float."""
    s = s.replace(",", "").replace(" ", "")
    if s in ("0円", "0"):
        return 0.0
    total = 0.0
    m = re.search(r"(\d+)兆", s)
    if m:
        total += int(m.group(1)) * 10000
    m = re.search(r"(?:兆)?(\d+)億", s)
    if m:
        total += int(m.group(1))
    if total == 0.0:
        raise ValueError(f"cannot parse yen amount: {s!r}")
    return total


def fetch_monthly_aggregates(after: dt.date):
    """Fetch monthly disclosure pages whose window ends after `after`.

    Returns list of dicts {window_start, window_end, amount_oku, source_url}.
    """
    idx = decode_mof(fetch(MONTHLY_INDEX_URL))
    stamps = sorted(set(re.findall(r'href="[^"]*?(\d{8})\.html"', idx)))
    out = []
    for stamp in stamps:
        pub = dt.date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8]))
        if pub <= after:
            continue
        url = MONTHLY_PAGE_URL.format(stamp=stamp)
        body = re.sub(r"<[^>]+>", " ", decode_mof(fetch(url)))
        body = re.sub(r"\s+", " ", body)
        m = re.search(
            r"○\s*((?:令和|平成)\d+年\d+月\d+日)\s*[～〜]\s*((?:令和|平成)\d+年\d+月\d+日)における外国為替平衡操作額\s*([0-9,兆億円\s]+?)円",
            body,
        )
        if not m:
            raise ValueError(f"cannot find aggregate amount on {url}")
        w_start, w_end = parse_wareki_date(m.group(1)), parse_wareki_date(m.group(2))
        amt_txt = m.group(3).strip()
        amount = 0.0 if amt_txt == "0" else parse_amount_yen_text(amt_txt)
        if w_end <= after:
            continue
        out.append({"window_start": w_start, "window_end": w_end, "amount_oku": amount, "source_url": url})
    return out


def cluster_episodes(dates, gap_days=EPISODE_GAP_DAYS):
    """Group sorted dates into episodes separated by >= gap_days."""
    episodes = []
    for d in sorted(dates):
        if episodes and (d - episodes[-1][-1]).days < gap_days:
            episodes[-1].append(d)
        else:
            episodes.append([d])
    return episodes


def main():
    import os
    os.makedirs(f"{REPO}/data/external", exist_ok=True)

    print(f"[fetch] {CSV_URL}")
    raw = fetch(CSV_URL)
    text = decode_mof(raw)
    events, quarter_totals, last_q_end = parse_daily_csv(text)
    print(f"[parse] daily events: {len(events)}  quarter-total rows: {len(quarter_totals)}  last quarter end: {last_q_end}")
    if not events:
        raise RuntimeError("0 daily events parsed — parser bug or source format change")

    # cross-validation: sum of dailies vs sum of quarterly totals (note2: daily rounding)
    sum_daily = sum(e["amount_oku"] for e in events)
    sum_q = sum(t for _, t in quarter_totals)
    print(f"[validate] sum(daily)={sum_daily:,.0f} oku  sum(quarterly totals)={sum_q:,.0f} oku  diff={sum_daily - sum_q:,.0f}")
    if abs(sum_daily - sum_q) > 0.001 * max(sum_daily, sum_q):
        raise RuntimeError("daily vs quarterly totals diverge by >0.1% — parsing bug")

    # monthly aggregates after last quarterly-covered date
    print(f"[fetch] monthly aggregate pages after {last_q_end}")
    monthly = fetch_monthly_aggregates(after=last_q_end)
    nonzero_monthly = [m for m in monthly if m["amount_oku"] > 0]
    for m in monthly:
        print(f"[monthly] {m['window_start']}..{m['window_end']}  {m['amount_oku']:,.0f} oku  {m['source_url']}")

    # ---- write normalized CSV ----
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "currency_pair", "direction", "amount_yen_billions", "source_url", "notes"])
        for e in events:
            w.writerow([
                e["date"].isoformat(),
                e["currency_pair"],
                e["direction"],
                round(e["amount_oku"] * 0.1, 1),  # oku (1e8 yen) -> billions (1e9 yen)
                CSV_URL,
                "",
            ])
        for m in nonzero_monthly:
            w.writerow([
                m["window_end"].isoformat(),
                "UNDISCLOSED",
                "undisclosed_monthly_aggregate",
                round(m["amount_oku"] * 0.1, 1),
                m["source_url"],
                f"monthly aggregate window {m['window_start']}..{m['window_end']}; "
                f"daily dates/pair/direction not yet disclosed (quarterly disclosure pending)",
            ])
    print(f"[write] {OUT_CSV}: {len(events)} daily rows + {len(nonzero_monthly)} pending monthly-aggregate rows")

    # ---- feasibility stats ----
    dates = [e["date"] for e in events]
    span = (min(dates), max(dates))
    by_pair = {}
    by_dir = {}
    for e in events:
        by_pair[e["currency_pair"]] = by_pair.get(e["currency_pair"], 0) + 1
        by_dir[e["direction"]] = by_dir.get(e["direction"], 0) + 1
    ev_2010 = [e for e in events if e["date"] >= dt.date(2010, 1, 1)]
    episodes_all = cluster_episodes(dates)
    episodes_2010 = cluster_episodes([e["date"] for e in ev_2010])
    by_year = {}
    for e in events:
        by_year[e["date"].year] = by_year.get(e["date"].year, 0) + 1

    must_have = [dt.date(2022, 9, 22), dt.date(2022, 10, 21), dt.date(2022, 10, 24),
                 dt.date(2024, 4, 29), dt.date(2024, 5, 1), dt.date(2024, 7, 11), dt.date(2024, 7, 12)]
    missing = [d.isoformat() for d in must_have if d not in set(dates)]
    if missing:
        raise RuntimeError(f"required episode dates missing from parsed data: {missing}")
    print(f"[validate] all {len(must_have)} required 2022/2024 dates present")

    result = {
        "task": "W1-F1 MoF intervention data fetch + design feasibility",
        "run_date": "2026-07-24",
        "source_csv": CSV_URL,
        "output_csv": OUT_CSV,
        "n_daily_events_total": len(events),
        "date_span": [span[0].isoformat(), span[1].isoformat()],
        "n_daily_events_2010plus": len(ev_2010),
        "events_by_pair": by_pair,
        "events_by_direction": by_dir,
        "events_by_year": by_year,
        "n_episodes_all_gap30d": len(episodes_all),
        "n_episodes_2010plus_gap30d": len(episodes_2010),
        "episodes_2010plus": [
            {"start": ep[0].isoformat(), "end": ep[-1].isoformat(), "n_days": len(ep)}
            for ep in episodes_2010
        ],
        "pending_monthly_aggregates_nonzero": [
            {"window": [m["window_start"].isoformat(), m["window_end"].isoformat()],
             "amount_yen_billions": round(m["amount_oku"] * 0.1, 1),
             "source_url": m["source_url"]}
            for m in nonzero_monthly
        ],
        "quarterly_daily_sum_check": {
            "sum_daily_oku": sum_daily, "sum_quarterly_oku": sum_q, "diff_oku": sum_daily - sum_q,
        },
        "last_quarterly_covered_date": last_q_end.isoformat(),
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[write] {OUT_JSON}")
    print(json.dumps({k: result[k] for k in (
        "n_daily_events_total", "n_daily_events_2010plus",
        "n_episodes_all_gap30d", "n_episodes_2010plus_gap30d")}, indent=2))
    return result


if __name__ == "__main__":
    main()
