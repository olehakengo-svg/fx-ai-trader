#!/usr/bin/env python3
"""E15 phase-0 discovery ハーネス — pre-reg §5a の執行 (rule:R1 手続き、read-only).

pre-reg SSOT: knowledge-base/wiki/decisions/e15-e7-event-modality-prereg-2026-07-18.md
estimand コア: tools/event_modality_lib.py (§3.5 SSOT)

**設計自由度ゼロ — pre-reg §5a/§5b の執行のみ。** 探索窓 (〜2023-12-31) のみを触り、
OOS 窓 (2024-01-01〜) には一切接触しない (§10-1 中間 peeking 禁止)。

combo 空間 (§5a、= 検定 family):
  fade/follow 系 = 3 event × 2 rule × 2 W0 × 3 h = 36
  uncond 系      = 3 event × 2 dir × 3 h        = 18   (W0=30m 固定)
  計 54 combo。primary block (USD-leg 7 ペア) pooled で判定。

各 combo で time-exit 摩擦調整 EV / first-touch EV / event-block 数 / fold 別 EV を計測。

実行:
  python3 tools/event_modality_explore.py self-test          # 合成データ dry-run (data 不要)
  python3 tools/event_modality_explore.py discovery          # 実データ (calendar+parquet 必須)

**副作用禁止**: import 時に I/O/argparse を実行しない。main() は __main__ ガード内でのみ。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from tools import event_modality_lib as L  # noqa: E402

MASSIVE = os.path.join(_REPO, "data", "cache", "massive")
CALENDAR_JSON = os.path.join(_REPO, "knowledge-base", "raw", "bt-results",
                             "e15_e7_event_calendar.json")
OUTDIR = os.path.join(_REPO, "knowledge-base", "raw", "bt-results")

EXPLORE_END = "2023-12-31"   # §3.4 探索窓終端 (OOS 窓接触禁止)

EVENTS = ["FOMC", "NFP", "CPI"]
FADE_FOLLOW_RULES = ["fade", "follow"]
W0S = [30, 60]
UNCOND_RULES = ["uncond_usd_long", "uncond_usd_short"]


def build_combos() -> list[dict]:
    """§5a の 54 combo を列挙 (pair 単位に展開しない — これが検定 family)。"""
    combos = []
    for ev in EVENTS:
        for rule in FADE_FOLLOW_RULES:
            for w0 in W0S:
                for h in L.E15_HORIZONS:
                    combos.append({"family": "e15", "event": ev, "rule": rule,
                                   "w0": w0, "h": h})
        for rule in UNCOND_RULES:
            for h in L.E15_HORIZONS:
                combos.append({"family": "e15", "event": ev, "rule": rule,
                               "w0": 30, "h": h})
    return combos


def _fold_of(ts, edges) -> int:
    for k, e in enumerate(edges):
        if ts <= e:
            return k
    return len(edges)


def run_combo(combo: dict, calendar: dict, bars: dict,
              friction=None) -> dict | None:
    """1 combo を primary block pooled で計測 (§5a)。

    calendar: {event_type: [ISO t_e_utc, ...]}
    bars    : {pair: (m15_df, daily_df)}
    """
    ev_dates = [pd.Timestamp(x) for x in calendar.get(combo["event"], [])]
    ev_dates = [t if t.tz is not None else t.tz_localize("UTC") for t in ev_dates]
    ev_dates = sorted(t for t in ev_dates if t <= pd.Timestamp(EXPLORE_END, tz="UTC"))
    if not ev_dates:
        return None

    # fold edges = 探索窓を時系列 3 等分 (§5b(iv))
    lo, hi = ev_dates[0], ev_dates[-1]
    span = (hi - lo) / 3
    edges = [lo + span, lo + 2 * span]

    te_pips, ft_pips, folds, blocks = [], [], [], set()
    fold_te = {0: [], 1: [], 2: []}
    for t_e in ev_dates:
        block_had_trade = False
        for pair in L.PRIMARY_PAIRS:
            if pair not in bars:
                continue
            m15, daily = bars[pair]
            out = L.event_trade(m15, daily, t_e, pair, combo["rule"],
                                combo["w0"], combo["h"], friction=friction)
            if out is None:
                continue
            te_pips.append(out.time_exit_pip)
            ft_pips.append(out.first_touch_pip)
            f = _fold_of(t_e, edges)
            fold_te[f].append(out.time_exit_pip)
            block_had_trade = True
        if block_had_trade:
            blocks.add(t_e)

    N = len(te_pips)
    if N == 0:
        return None
    fold_signs = [np.sign(np.mean(v)) for v in fold_te.values() if v]
    return {
        **{k: combo[k] for k in ("family", "event", "rule", "w0", "h")},
        "N": int(N),
        "event_blocks": int(len(blocks)),
        "ev_time_exit": float(np.mean(te_pips)),
        "ev_first_touch": float(np.mean(ft_pips)),
        "te_std": float(np.std(te_pips, ddof=1)) if N > 1 else float("nan"),
        "fold_te_signs": [int(s) for s in fold_signs],
        "fold_sign_agreement": int(max(
            sum(1 for s in fold_signs if s > 0),
            sum(1 for s in fold_signs if s < 0),
        )) if fold_signs else 0,
    }


def select_and_freeze(cells: list[dict], m_cap: int = 8) -> list[dict]:
    """§5b 選抜規則 + 凍結規則 (辞書式)。discovery 出力からの決定的選抜。

    選抜 (全充足): (i) EV_te>0 (ii) EV_ft>0 (iii) N≥60 ∧ blocks≥40
                   (iv) fold 符号一致 ≥2/3
    凍結 (辞書式): (1) fold 一致数 desc (2) EV-per-vol desc
                   (3) event 種分散 (各 event ≤3) → m₀≤8
    """
    passed = [c for c in cells
              if c["ev_time_exit"] > 0 and c["ev_first_touch"] > 0
              and c["N"] >= 60 and c["event_blocks"] >= 40
              and c["fold_sign_agreement"] >= 2]
    for c in passed:
        c["ev_per_vol"] = (c["ev_time_exit"] / c["te_std"]) if c["te_std"] and np.isfinite(c["te_std"]) and c["te_std"] > 0 else 0.0
    passed.sort(key=lambda c: (-c["fold_sign_agreement"], -c["ev_per_vol"]))
    frozen, per_event = [], {}
    for c in passed:
        if per_event.get(c["event"], 0) >= 3:
            continue
        frozen.append(c)
        per_event[c["event"]] = per_event.get(c["event"], 0) + 1
        if len(frozen) >= m_cap:
            break
    return frozen


def _load_pair(pair: str):
    f = os.path.join(MASSIVE, f"{pair}_15m.parquet")
    if not os.path.exists(f):
        return None
    m15 = pd.read_parquet(f)
    if m15.index.tz is None:
        m15.index = m15.index.tz_localize("UTC")
    daily = L.build_daily_from_m15(m15)
    return m15, daily


def discovery() -> int:
    if not os.path.exists(CALENDAR_JSON):
        print(f"[BLOCKED] event calendar not found: {CALENDAR_JSON}", file=sys.stderr)
        print("  → build calendar first (FOMC=federalreserve.gov key-free / "
              "NFP+CPI=FRED release_id 50,10 requires FRED_API_KEY)", file=sys.stderr)
        return 2
    with open(CALENDAR_JSON) as fh:
        cal = json.load(fh)
    calendar = cal.get("events", cal)

    bars, coverage = {}, {}
    for pair in L.PRIMARY_PAIRS:
        loaded = _load_pair(pair)
        if loaded is None:
            coverage[pair] = {"status": "MISSING_PARQUET"}
            continue
        m15, daily = loaded
        cov = L.market_time_coverage(m15, "2014-01-01", EXPLORE_END)
        coverage[pair] = {"coverage": round(cov, 4),
                          "included": cov >= L.COVERAGE_GATE}
        if cov >= L.COVERAGE_GATE:
            bars[pair] = (m15, daily)

    if len(bars) < 5:
        print(f"[DEFERRED] primary block < 5 pairs available ({len(bars)}) — "
              f"§8 DEFERRED. coverage={coverage}", file=sys.stderr)
        _write("e15_discovery_BLOCKED.json",
               {"status": "BLOCKED_INSUFFICIENT_DATA", "coverage": coverage})
        return 3

    cells = [c for c in (run_combo(cb, calendar, bars) for cb in build_combos())
             if c is not None]
    _write("e15_discovery.json",
           {"status": "OK", "n_combos": len(cells), "coverage": coverage,
            "cells": cells})
    frozen = select_and_freeze(cells)
    # §5b 凍結 artifact (runbook 指定: raw/bt-results/e15_frozen_candidates.json)
    _write("e15_frozen_candidates.json",
           {"status": "FROZEN", "prereg": "e15-e7-event-modality-prereg-2026-07-18 §5b",
            "explore_end": EXPLORE_END, "m0": len(frozen), "m_cap": 8,
            "selection_rule": "(i) EV_te>0 (ii) EV_ft>0 (iii) N>=60 & blocks>=40 "
                              "(iv) fold sign agreement >=2/3; freeze lexicographic: "
                              "fold agreement desc -> EV-per-vol desc -> event<=3",
            "candidates": frozen})
    print(f"discovery: {len(cells)}/54 combos computed, "
          f"{len(frozen)} pass selection+freeze")
    return 0


def _write(name: str, obj: dict):
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, name), "w") as fh:
        json.dump(obj, fh, indent=2, default=str)


# ─── 合成 dry-run (data 不要、ハーネスの結線検証) ────────────────────────────
def self_test() -> int:
    """合成カレンダー + 合成 primary frame で 54-combo ループを end-to-end 実行。

    実データ不要。ハーネスの結線 (combo 展開 / pooling / fold / 選抜) が
    finite 出力を返すことを検証する (§10-6 dry-run)。
    """
    n = 96 * 400
    idx = pd.date_range("2020-01-01", periods=n, freq="15min", tz="UTC")
    rng = np.random.default_rng(42)
    bars = {}
    for pair in L.PRIMARY_PAIRS[:5]:
        base = 1.0 + np.cumsum(rng.normal(0, 0.0003, n))
        df = pd.DataFrame({"Open": base, "High": base + 0.0010,
                           "Low": base - 0.0010, "Close": base + rng.normal(0, 0.0002, n)},
                          index=idx)
        bars[pair] = (df, L.build_daily_from_m15(df))
    # 合成カレンダー: 探索窓内に各 event 60 件 (08:30/14:00 ET → M15 境界)
    cal = {}
    for ev in EVENTS:
        hh, mm = L.EVENT_TIME_ET[ev]
        days = pd.date_range("2020-02-01", "2023-11-30", periods=60)
        cal[ev] = [L.et_to_utc(d.date(), hh, mm).isoformat() for d in days]

    combos = build_combos()
    assert len(combos) == 54, f"combo count {len(combos)} != 54"
    cells = [c for c in (run_combo(cb, cal, bars) for cb in combos) if c is not None]
    assert cells, "no cells computed"
    for c in cells:
        assert np.isfinite(c["ev_time_exit"]) and np.isfinite(c["ev_first_touch"])
        assert c["event_blocks"] <= c["N"]
    frozen = select_and_freeze(cells)
    # OOS 非接触の pin: 全 event date ≤ EXPLORE_END
    assert all(pd.Timestamp(x) <= pd.Timestamp(EXPLORE_END, tz="UTC")
               for lst in cal.values() for x in lst)
    print(f"self-test OK: 54 combos → {len(cells)} cells computed, "
          f"{len(frozen)} passed selection (synthetic; no edge expected)")
    return 0


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    mode = argv[0] if argv else "self-test"
    if mode == "self-test":
        return self_test()
    if mode == "discovery":
        return discovery()
    print(f"unknown mode: {mode} (use: self-test | discovery)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
