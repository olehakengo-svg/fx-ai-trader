"""E7 phase-1 サプライズパネル構築 + power pre-flight (rule:R1 手続きの pre-flight 部).

pre-reg SSOT: knowledge-base/wiki/decisions/e15-e7-event-modality-prereg-2026-07-18.md
  - §6   : z = (actual - consensus) / σ_trailing (直近 24 releases、strictly trailing、
           当該 release 自身を含まない) / 対象 = NFP headline + CPI headline m/m /
           θ ∈ {0.5, 1.0} / combo 空間 24
  - §3.3b: 系列指定・forecast 意味論・actual = BLS first print・単位・既知欠落 (凍結済)
  - §3.4 : discovery 窓 (≥2014-01 〜 2023-12-31) / OOS 窓 (2024-01-01 〜 2026-06-30)
  - §5b  : discovery 選抜ゲート (iii) blocks >= 40 / §5c レグ B(d) OOS blocks >= 15

**価格データに一切接触しない** (カレンダー値のみ)。イベント×リターン結合統計は計算
しない (§10-1 遵守) — 本ツールの出力は「サプライズ標本の可用性と block 数」= §9 の
power 開示に相当する data-availability 統計であり、outcome の peeking ではない。

Usage:
    python3 tools/e7_surprise_panel.py                       # panel + coverage を stdout
    python3 tools/e7_surprise_panel.py --write               # 成果物を raw/bt-results/e7/ へ
"""
import argparse
import csv
import json
import os
import statistics
import sys

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_TOOLS_DIR)

CALENDAR_JSON = os.path.join("knowledge-base", "raw", "bt-results",
                             "e15_e7_event_calendar.json")
R4F_CSV = os.path.join("knowledge-base", "raw", "bt-results", "e7",
                       "ff_calendar_r4f_2014_2026.csv")
BLS_CSV = os.path.join("knowledge-base", "raw", "bt-results", "e7",
                       "ff_gap_bls_first_prints.csv")
OUT_PANEL = os.path.join("knowledge-base", "raw", "bt-results", "e7",
                         "e7_surprise_panel.csv")
OUT_COVERAGE = os.path.join("knowledge-base", "raw", "bt-results", "e7",
                            "e7_surprise_coverage.json")

# §3.3b-2 対象系列 (canonical キー -> R4F title)
SERIES = {
    "NFP": {"title": "Non-Farm Employment Change", "unit": "K"},
    "CPI": {"title": "CPI m/m", "unit": "%"},
}
TRAILING_N = 24          # §6 σ_trailing 窓 (releases)
THETAS = (0.5, 1.0)      # §6 θ grid
DISCOVERY_END = "2023-12-31"
OOS_START = "2024-01-01"
OOS_END = "2026-06-30"
# §5b(iii) / §5c B(d) の block ゲート (pooled は primary block 7 ペアで展開されるため
# block = イベント数。N ゲート (60 / 30) は blocks × ペア数で自動充足する)
DISCOVERY_BLOCK_GATE = 40
OOS_BLOCK_GATE = 15
PRIMARY_PAIRS = 7        # §4 primary block


def parse_value(raw, unit):
    """FF 表示規約の値をスカラーへ (§3.3b-5: NFP=千人 'K'、CPI='%' 小数1桁)。

    欠損 (空文字 / None) は None。単位記号の不一致は ValueError (較正で強制)。
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = s.replace(",", "")
    if unit == "K":
        if not s.endswith("K"):
            raise ValueError(f"NFP 値の単位が K でない: {raw!r}")
        return float(s[:-1])
    if unit == "%":
        if not s.endswith("%"):
            raise ValueError(f"CPI 値の単位が %% でない: {raw!r}")
        return float(s[:-1])
    raise ValueError(f"未知の単位: {unit!r}")


def trailing_sigma(prior_surprises, n=TRAILING_N):
    """直近 n 件の *過去* サプライズの標本 SD。n 件未満なら None (warm-up)。

    prior_surprises は時系列昇順で、当該 release 自身を含まないことが呼出側の契約。
    """
    if len(prior_surprises) < n:
        return None
    window = prior_surprises[-n:]
    sd = statistics.stdev(window)          # 標本 SD (ddof=1)
    return sd if sd > 0 else None


def build_panel(events_by_series):
    """{series: [ {event_time, forecast, actual}, ... ] } -> パネル行 (時系列昇順)。

    surprise = actual - forecast。z は strictly trailing σ で正規化し、
    warm-up (過去サプライズ < TRAILING_N) の行は z=None のまま残す (除外理由を記録)。
    """
    rows = []
    for series, evs in events_by_series.items():
        prior = []
        for ev in sorted(evs, key=lambda e: e["event_time"]):
            fc, ac = ev.get("forecast"), ev.get("actual")
            row = {
                "series": series,
                "event_time_utc": ev["event_time"],
                "forecast": fc,
                "actual": ac,
                "surprise": None,
                "sigma_trailing": None,
                "z": None,
                "prior_n": len(prior),
                "exclude_reason": "",
            }
            if fc is None or ac is None:
                row["exclude_reason"] = ("missing_forecast" if fc is None
                                         else "missing_actual")
                rows.append(row)
                continue
            surprise = ac - fc
            row["surprise"] = surprise
            sigma = trailing_sigma(prior)
            if sigma is None:
                row["exclude_reason"] = "warmup_lt_%d_prior" % TRAILING_N
            else:
                row["sigma_trailing"] = sigma
                row["z"] = surprise / sigma
            # サプライズ標本は「当該 release の後」に初めて trailing 母集団へ入る
            prior.append(surprise)
            rows.append(row)
    rows.sort(key=lambda r: (r["event_time_utc"], r["series"]))
    return rows


def _window_of(event_time):
    day = event_time[:10]
    if day <= DISCOVERY_END:
        return "discovery"
    if OOS_START <= day <= OOS_END:
        return "oos"
    return "outside"


def coverage(rows, thetas=THETAS):
    """窓 × 系列 × θ の block 数 (= 発火イベント数) と N 見込み、ゲート判定。"""
    out = {}
    for series in SERIES:
        for window in ("discovery", "oos"):
            sel = [r for r in rows
                   if r["series"] == series and _window_of(r["event_time_utc"]) == window]
            usable = [r for r in sel if r["z"] is not None]
            entry = {
                "events_in_window": len(sel),
                "z_usable": len(usable),
                "excluded": {},
                "by_theta": {},
            }
            for r in sel:
                if r["exclude_reason"]:
                    entry["excluded"][r["exclude_reason"]] = \
                        entry["excluded"].get(r["exclude_reason"], 0) + 1
            gate = DISCOVERY_BLOCK_GATE if window == "discovery" else OOS_BLOCK_GATE
            for th in thetas:
                blocks = sum(1 for r in usable if abs(r["z"]) > th)
                entry["by_theta"]["%.1f" % th] = {
                    "blocks": blocks,
                    "n_pooled_est": blocks * PRIMARY_PAIRS,
                    "block_gate": gate,
                    "gate_pass": blocks >= gate,
                }
            out["%s/%s" % (series, window)] = entry
    return out


def load_inputs(root):
    """凍結済み artifact 3 本からイベント辞書を組む (network 非接触)。"""
    with open(os.path.join(root, CALENDAR_JSON), encoding="utf-8") as f:
        cal = json.load(f)
    canonical = {s: [t.replace("+00:00", "Z") for t in cal["events"][s]]
                 for s in SERIES}

    r4f = {}
    with open(os.path.join(root, R4F_CSV), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["country"] != "USD":
                continue
            for series, spec in SERIES.items():
                if r["title"] == spec["title"]:
                    # §3.3b-6(ii): 同系列の重複は canonical 時刻一致行 (H) のみが拾われる
                    r4f.setdefault((series, r["event_time_utc"]), r)

    bls = {}
    with open(os.path.join(root, BLS_CSV), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for series, spec in SERIES.items():
                if r["title"] == spec["title"]:
                    bls[(series, r["event_time_utc"])] = r

    events, provenance = {}, {"r4f_actual": 0, "bls_actual": 0, "no_actual": 0,
                              "no_r4f_row": 0}
    for series, times in canonical.items():
        unit = SERIES[series]["unit"]
        evs = []
        for t in times:
            row = r4f.get((series, t))
            if row is None:
                provenance["no_r4f_row"] += 1
                evs.append({"event_time": t, "forecast": None, "actual": None})
                continue
            fc = parse_value(row["forecast"], unit)
            ac = parse_value(row["actual"], unit)
            if ac is not None:
                provenance["r4f_actual"] += 1
            else:
                # §3.3b-4: R4F actual は 2023-08 で充填停止 → BLS first print で補完
                brow = bls.get((series, t))
                ac = parse_value(brow["actual"], unit) if brow else None
                provenance["bls_actual" if ac is not None else "no_actual"] += 1
            evs.append({"event_time": t, "forecast": fc, "actual": ac})
        events[series] = evs
    return events, provenance


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=_PROJECT_ROOT)
    ap.add_argument("--write", action="store_true",
                    help="panel CSV + coverage JSON を成果物パスへ書く")
    args = ap.parse_args(argv)

    events, provenance = load_inputs(args.root)
    rows = build_panel(events)
    cov = coverage(rows)
    doc = {
        "tool": "e7_surprise_panel",
        "prereg": "e15-e7-event-modality-prereg-2026-07-18 §6/§3.3b/§3.4",
        "price_data_contact": False,
        "trailing_n": TRAILING_N,
        "thetas": list(THETAS),
        "windows": {"discovery_end": DISCOVERY_END,
                    "oos": [OOS_START, OOS_END]},
        "actual_provenance": provenance,
        "coverage": cov,
    }
    print(json.dumps(doc, ensure_ascii=False, indent=1))

    if args.write:
        panel_path = os.path.join(args.root, OUT_PANEL)
        with open(panel_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        with open(os.path.join(args.root, OUT_COVERAGE), "w",
                  encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("wrote %s (%d rows) + %s" % (OUT_PANEL, len(rows), OUT_COVERAGE),
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
