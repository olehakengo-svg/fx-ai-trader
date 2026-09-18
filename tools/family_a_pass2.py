"""family A statement_ladder — pass-2 (frozen measurement).

🔒 Executes the measurement frozen in
knowledge-base/wiki/decisions/family-a-statement-ladder-prereg-2026-08-19.md §10.2,
unlocked by pass-1 (§10.3 Gate A ∧ Gate B, both PASS on 2026-09-18).

    J    = P(armed | intervention day) − P(armed | non-intervention day)
           (day-level Peirce / Youden skill score, m = 1)
    null = episode-block circular shift of the LABEL series, B = 10,000;
           when the number of distinct shifts is below B, all of them are used and
           p = (1 + #{J_shift ≥ J_obs}) / (1 + #shifts)
    α    = 0.05, one-sided (J > 0)

This consumes the family's single explore look. It must run **once**, on the
event set frozen by pass-1 and already landed on main
(`knowledge-base/raw/analysis/family-a-pass1-events-2026-09-18.json`).

Claim ceiling (§5, unchanged): effective N = 4 episode blocks, so **any result is
descriptive**. No edge claim, no live/tier/lot change, ever.

    python3 tools/family_a_pass2.py [--json out.json]
    python3 -m tools.family_a_pass2 [--json out.json]
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import pathlib
import sys

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tools import family_a_ladder_detector as det  # noqa: E402
from tools.family_a_pass1 import EXPLORE_END, EXPLORE_START  # noqa: E402

LABELS_CSV = "data/external/mof_statements/interventions_daily.csv"
FROZEN_EVENTS_JSON = "knowledge-base/raw/analysis/family-a-pass1-events-2026-09-18.json"

# Frozen statistical design (§10.2)
B_SHIFTS = 10_000
ALPHA = 0.05
# Frozen population description (§3) — asserted, never inferred.
DIRECTION = "sell_USD_buy_JPY"
EPISODE_GAP_DAYS = 30
EXPECTED_INTERVENTION_DAYS = 10
EXPECTED_EPISODE_BLOCKS = 4


# --- labels -----------------------------------------------------------------
def load_intervention_days(path: str = LABELS_CSV) -> list[_dt.date]:
    """JPY-buying intervention days inside the frozen explore window."""
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["direction"] != DIRECTION:
                continue
            d = _dt.date.fromisoformat(row["date"])
            if EXPLORE_START <= d <= EXPLORE_END:
                out.append(d)
    return sorted(set(out))


def episode_blocks(days: list[_dt.date], gap: int = EPISODE_GAP_DAYS) -> list[list[_dt.date]]:
    blocks: list[list[_dt.date]] = []
    for d in days:
        if blocks and (d - blocks[-1][-1]).days < gap:
            blocks[-1].append(d)
        else:
            blocks.append([d])
    return blocks


# --- statistic --------------------------------------------------------------
def youden_j(armed: list[bool], label: list[bool]) -> float:
    npos = sum(label)
    nneg = len(label) - npos
    if npos == 0 or nneg == 0:
        return float("nan")
    tp = sum(1 for a, l in zip(armed, label) if l and a)
    fp = sum(1 for a, l in zip(armed, label) if (not l) and a)
    return tp / npos - fp / nneg


def circular_shift(label: list[bool], k: int) -> list[bool]:
    n = len(label)
    k %= n
    return label[-k:] + label[:-k] if k else list(label)


def permutation_p(armed: list[bool], label: list[bool], b: int = B_SHIFTS) -> dict:
    n = len(label)
    shifts = list(range(1, n))
    if len(shifts) > b:                       # subsample evenly, deterministic
        step = len(shifts) / b
        shifts = [shifts[int(i * step)] for i in range(b)]
    j_obs = youden_j(armed, label)
    null = [youden_j(armed, circular_shift(label, k)) for k in shifts]
    ge = sum(1 for j in null if j >= j_obs)
    null_sorted = sorted(null)
    return {
        "j_obs": j_obs,
        "p_one_sided": (1 + ge) / (1 + len(shifts)),
        "n_shifts": len(shifts),
        "null_mean": sum(null) / len(null),
        "null_p95": null_sorted[int(0.95 * len(null_sorted))],
        "null_max": null_sorted[-1],
    }


# --- run --------------------------------------------------------------------
def run() -> dict:
    out = det.build(EXPLORE_START, EXPLORE_END)
    days = out.days

    frozen = json.load(open(FROZEN_EVENTS_JSON, encoding="utf-8"))
    frozen_events = [_dt.date.fromisoformat(d) for d in frozen["events"]]
    if frozen_events != out.events:
        raise SystemExit(
            "ABORT: 凍結イベント集合と再計算が不一致 — pass-2 は凍結集合の上でしか走らせない\n"
            f"  frozen={frozen['events']}\n  rebuilt={[str(d) for d in out.events]}")

    iv_days = load_intervention_days()
    blocks = episode_blocks(iv_days)
    if len(iv_days) != EXPECTED_INTERVENTION_DAYS or len(blocks) != EXPECTED_EPISODE_BLOCKS:
        raise SystemExit(
            "ABORT: ラベル母集団が pre-reg §3 の宣言と不一致 — estimand が凍結時と違う\n"
            f"  期待 {EXPECTED_INTERVENTION_DAYS} 日 / {EXPECTED_EPISODE_BLOCKS} blocks\n"
            f"  実測 {len(iv_days)} 日 / {len(blocks)} blocks: {[str(d) for d in iv_days]}")

    off_bd = [d for d in iv_days if not det.is_business_day(d)]
    iv_set = set(iv_days)

    armed = [d in out.armed for d in days]
    label = [d in iv_set for d in days]
    stat = permutation_p(armed, label)

    npos = sum(label)
    tp = sum(1 for a, l in zip(armed, label) if l and a)
    fp = sum(1 for a, l in zip(armed, label) if (not l) and a)
    nneg = len(label) - npos

    # --- secondary (descriptive only, never decisive — §2 / §10.4 caveat) ---
    # ⚠️ 2 種類の分解を混同しないこと (Codex P2 / PR #270):
    #   contribution : armed をその年の event だけに絞り、**ラベルは全年**のまま
    #                  → 全体 J への**寄与**の分解であって層別 J ではない
    #                  (分母が全 7 陽性なので「その話者の検出器の性能」ではない)
    #   stratified   : armed も label も**その暦年の営業日だけ**に絞った within-year J
    #                  → 話者/年ごとの検出器性能。話者交絡の点検にはこちらを使う
    idx = {d: i for i, d in enumerate(days)}
    all_years = sorted({d.year for d in days})
    per_year = {}
    for yr in all_years:
        ev = [e for e in out.events if e.year == yr]
        armed_y = set()
        for e in ev:
            i = idx[e]
            armed_y.update(days[i: i + det.H_HORIZON_BD + 1])
        # `hit_days` は armed 窓に入った介入「日」数、`events_with_hit` は
        # 窓内に 1 日以上の介入を含む「event」数。1 event が複数の介入日を
        # 覆うため両者は一致しない (2022: 1 event が 10-21 と 10-24 を覆う)。
        ev_hit = sum(
            1 for e in ev
            if any(d in iv_set for d in days[idx[e]: idx[e] + det.H_HORIZON_BD + 1]))
        # contribution (ラベルは全年のまま)
        contrib_j = youden_j([d in armed_y for d in days], label)
        # stratified (armed も label もその年の営業日に限定)
        days_y = [d for d in days if d.year == yr]
        strat_j = youden_j([d in armed_y for d in days_y],
                           [d in iv_set for d in days_y])
        per_year[str(yr)] = {
            "n_events": len(ev),
            "events_with_hit": ev_hit,
            "hit_days": sum(1 for d in iv_days if d in armed_y),
            "n_intervention_days_in_year": sum(1 for d in iv_days if d.year == yr),
            # stratified J の実際の陽性数 (営業日カレンダーに載った分だけ)。
            # §11.3 の欠陥でこれが n_intervention_days_in_year を下回る年がある。
            "n_positive_business_days_in_year": sum(
                1 for d in days if d.year == yr and d in iv_set),
            "contribution_j_labels_all_years": contrib_j,
            "stratified_j_within_year": strat_j,
        }

    lead = []
    for e in out.events:
        i = days.index(e)
        win = days[i: i + det.H_HORIZON_BD + 1]
        nxt = [d for d in iv_days if d in win]
        lead.append(win.index(nxt[0]) if nxt else None)

    verdict = (
        "PASS (記述級)" if stat["p_one_sided"] <= ALPHA and stat["j_obs"] > 0
        else "FAIL")

    curve = power_curve(armed, npos)
    observed_hits = tp
    power_at_observed = next(
        (r["power"] for r in curve if r["hits"] == observed_hits), None)

    return {
        "pre_reg": "family-a-statement-ladder-prereg-2026-08-19.md §10.2 / §10.4",
        "explore_window": [str(EXPLORE_START), str(EXPLORE_END)],
        "n_business_days": len(days),
        "events": [str(d) for d in out.events],
        "intervention_days": [str(d) for d in iv_days],
        "episode_blocks": [[str(d) for d in b] for b in blocks],
        "intervention_days_off_business_calendar": [str(d) for d in off_bd],
        "contingency": {"n_pos": npos, "n_neg": nneg, "armed_and_pos": tp,
                        "armed_and_neg": fp,
                        "tpr": tp / npos if npos else None,
                        "fpr": fp / nneg if nneg else None},
        "statistic": stat,
        "alpha": ALPHA,
        "verdict": verdict,
        "power_analysis_post_hoc": {
            "note": ("凍結時に power analysis を規定しなかったのは設計の不足。"
                     "本曲線は Codex P2 (PR #270) を受けた post-hoc の解釈材料であり、"
                     "verdict の判定には使わない。実 armed 系列 + 合成ラベルのみ。"),
            "reps": POWER_REPS, "seed": POWER_SEED,
            "observed_hits": observed_hits,
            "power_at_observed_effect": power_at_observed,
            "curve": curve,
        },
        "secondary_descriptive": {
            "per_event_year": per_year,
            "lead_business_days_per_event": lead,
        },
        "claim_ceiling": ("有効 N = 4 episode blocks。PASS でも記述級 — "
                          "edge 主張・live/tier/lot 変更は恒久ゼロ (§5)"),
    }


# --- post-hoc power analysis (label-free; 実ラベルは使わない) ------------------
POWER_REPS = 600
POWER_SEED = 20260918


def power_curve(armed: list[bool], n_positives: int, reps: int = POWER_REPS,
                seed: int = POWER_SEED, alpha: float = ALPHA) -> list[dict]:
    """効果量ごとの検出力を、実 armed 系列 + 合成ラベルで測る。

    ⚠️ **post-hoc**。凍結時に power analysis を規定しなかったのは設計の不足で、
    Codex P2 (PR #270) の指摘を受けて事後に追加したもの。**verdict の判定には
    一切使わない** — FAIL は凍結された α 規則のままで、本曲線はその FAIL を
    どう読むべきかの解釈材料。

    `hits` = 7 陽性のうち armed 窓に入る個数 (= 検出器の質)。各 hits について
    合成ラベルを reps 回引き、permutation p <= alpha となる割合を返す。
    """
    import numpy as np

    a = np.asarray(armed, dtype=float)
    n = a.size
    fa = np.fft.rfft(a)
    armed_idx = np.flatnonzero(a)
    non_idx = np.flatnonzero(a == 0)
    rng = np.random.default_rng(seed)

    def _p(lab: "np.ndarray") -> tuple[float, float]:
        tp = np.round(np.fft.irfft(fa * np.conj(np.fft.rfft(lab)), n))
        npos = lab.sum()
        fp = a.sum() - tp
        j = tp / npos - fp / (n - npos)
        null = j[1:]
        return float(j[0]), float((1 + (null >= j[0]).sum()) / (1 + null.size))

    out = []
    for hits in range(n_positives + 1):
        js, sig = [], 0
        for _ in range(reps):
            lab = np.zeros(n)
            lab[rng.choice(armed_idx, hits, replace=False)] = 1
            lab[rng.choice(non_idx, n_positives - hits, replace=False)] = 1
            j, pv = _p(lab)
            js.append(j)
            sig += pv <= alpha
        out.append({"hits": hits, "mean_j": sum(js) / len(js), "power": sig / reps})
    return out


def _nan_to_none(obj):
    """NaN を None に置換して strict JSON でシリアライズ可能にする。"""
    if isinstance(obj, dict):
        return {k: _nan_to_none(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_nan_to_none(v) for v in obj]
    if isinstance(obj, float) and obj != obj:
        return None
    return obj


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", dest="out", default="")
    args = ap.parse_args(argv)
    res = run()
    # NaN は JSON 仕様外 (json.dumps の既定は Python 拡張の `NaN` を書く)。
    # 空の層 (event も介入日も無い年) は `null` としてシリアライズし、
    # 厳格な JSON パーサでも読めるようにする (Codex P2 / PR #270)。
    text = json.dumps(_nan_to_none(res), ensure_ascii=False, indent=2,
                      allow_nan=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
