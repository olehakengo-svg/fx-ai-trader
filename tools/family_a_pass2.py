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

# 凍結測定を実行したときの営業日系列と armed マスクの指紋 (先頭 16 hex)。
# pass-1 の凍結成果物はマスクを保存していなかったため (設計の不足)、
# ここを基準点として **系列そのものの drift** を検出する。
# 日数と armed 率だけの照合では、営業日を 1 日入れ替えても通ってしまう
# (自分で再構成した armed と比べても系列が同じなので一致してしまう) — Codex P2 第10波。
EXPECTED_DAYS_SHA16 = "83a8291d1bfd1542"
EXPECTED_ARMED_SHA16 = "0828367a8a8645a7"


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
    idx = {d: i for i, d in enumerate(days)}

    frozen = json.load(open(FROZEN_EVENTS_JSON, encoding="utf-8"))
    # 凍結成果物との照合は **events だけでは足りない** (Codex P2 第9波)。
    # H や営業日カレンダーが変われば events が同じでも days / armed が変わり、
    # 「凍結された測定」と名乗ったまま別の J / p が出てしまう。
    mismatches = []
    frozen_events = [_dt.date.fromisoformat(d) for d in frozen["events"]]
    if frozen_events != out.events:
        mismatches.append(f"events: frozen={frozen['events']} rebuilt={[str(d) for d in out.events]}")
    want_params = {"T": det.T_CARRY_BD, "R": det.R_REARM_BD,
                   "H": det.H_HORIZON_BD, "trigger": det.TRIGGER_LEVEL}
    if frozen.get("params") != want_params:
        mismatches.append(f"params: frozen={frozen.get('params')} current={want_params}")
    if frozen.get("explore_window") != [str(EXPLORE_START), str(EXPLORE_END)]:
        mismatches.append(f"window: frozen={frozen.get('explore_window')}")
    fg = frozen.get("gates", {})
    if fg.get("n_business_days") != len(days):
        mismatches.append(f"n_business_days: frozen={fg.get('n_business_days')} rebuilt={len(days)}")
    armed_n = len(out.armed)
    if fg.get("armed_fraction") is not None and \
            abs(fg["armed_fraction"] - armed_n / len(days)) > 1e-9:
        mismatches.append(
            f"armed: frozen_fraction={fg['armed_fraction']} rebuilt={armed_n}/{len(days)}")
    # 日数と armed 率だけでは、営業日が 1 日入れ替わっても通ってしまう
    # (Codex P2 第10波)。**凍結 events から armed を独立に再構成**して
    # 日付の同一性まで照合する。
    missing = [str(d) for d in frozen_events if d not in idx]
    if missing:
        mismatches.append(f"frozen events not in business-day series: {missing}")
    else:
        rebuilt_armed = set()
        for e in frozen_events:
            i = idx[e]
            rebuilt_armed.update(days[i: i + det.H_HORIZON_BD + 1])
        if rebuilt_armed != out.armed:
            only_a = sorted(str(d) for d in rebuilt_armed - out.armed)[:5]
            only_b = sorted(str(d) for d in out.armed - rebuilt_armed)[:5]
            mismatches.append(
                f"armed mask mismatch: from_frozen_only={only_a} detector_only={only_b}")
    import hashlib as _hl

    def _sha16(seq):
        return _hl.sha256("\n".join(str(x) for x in seq).encode()).hexdigest()[:16]

    days_sha, armed_sha = _sha16(days), _sha16(sorted(out.armed))
    if days_sha != EXPECTED_DAYS_SHA16:
        mismatches.append(f"days series drift: {days_sha} != {EXPECTED_DAYS_SHA16}")
    if armed_sha != EXPECTED_ARMED_SHA16:
        mismatches.append(f"armed mask drift: {armed_sha} != {EXPECTED_ARMED_SHA16}")
    if mismatches:
        raise SystemExit(
            "ABORT: 凍結設定と再計算が不一致 — pass-2 は凍結された構成の上でしか走らせない\n  "
            + "\n  ".join(mismatches))

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

    # 観測 block 構造 (営業日系列上) を保存して power を測る
    iv_bd = [d for d in iv_days if d in idx]
    bd_blocks = episode_blocks(iv_bd)
    block_offsets = [[idx[d] - idx[b[0]] for d in b] for b in bd_blocks]
    observed_hit_blocks = sum(1 for b in bd_blocks if any(d in out.armed for d in b))
    curve = power_curve(armed, block_offsets, days=days)
    power_at_observed = next(
        (r["power"] for r in curve if r["hit_blocks"] == observed_hit_blocks), None)

    return {
        "pre_reg": "family-a-statement-ladder-prereg-2026-08-19.md §10.2 / §10.4",
        "series_fingerprint": {
            "days_sha256_16": days_sha,
            "armed_sha256_16": armed_sha,
            "expected_days_sha256_16": EXPECTED_DAYS_SHA16,
            "expected_armed_sha256_16": EXPECTED_ARMED_SHA16,
            "note": ("凍結 pass-1 成果物は days/armed のマスクを保存していなかったため "
                     "(設計の不足)、本 pass-2 実行時点の指紋をここに記録して以後の "
                     "drift 検出の基準点にする。照合自体は凍結 events から armed を "
                     "独立再構成して日付同一性まで行っている。"),
        },
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
        "frozen_null_structure_diagnostic": null_structure_diagnostic(days, iv_days),
        "power_analysis_post_hoc": {
            "note": ("凍結時に power analysis を規定しなかったのは設計の不足。"
                     "本曲線は Codex P2 (PR #270) を受けた post-hoc の解釈材料であり、"
                     "verdict の判定には使わない。実 armed 系列 + 合成ラベルのみ。"),
            "reps": POWER_REPS, "seed": POWER_SEED,
            "block_sizes_business_days": [len(b) for b in bd_blocks],
            "observed_hit_blocks": observed_hit_blocks,
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


def power_curve(armed: list[bool], block_offsets: list[list[int]],
                days: list | None = None,
                reps: int = POWER_REPS, seed: int = POWER_SEED,
                alpha: float = ALPHA) -> list[dict]:
    """効果量ごとの検出力を、実 armed 系列 + 合成ラベルで測る。

    ⚠️ **post-hoc**。凍結時に power analysis を規定しなかったのは設計の不足で、
    Codex P2 (PR #270) の指摘を受けて事後に追加したもの。**verdict の判定には
    一切使わない** — FAIL は凍結された α 規則のままで、本曲線はその FAIL を
    どう読むべきかの解釈材料。

    **episode block 構造を保存する** (Codex P2 第5波)。実ラベルは営業日系列上で
    [3, 1, 2, 1] 日の 4 block に集中しており、7 陽性を一様ランダムに散らすと
    実際より独立な試行を仮定して検出力を過大評価する。ここでは各 block を
    内部間隔ごと丸ごとランダム位置へ置き、**armed 窓に入る block 数**を
    効果量の軸にする。

    block_offsets: 各 block 先頭からの営業日オフセット (実測値)。
    """
    import numpy as np

    a = np.asarray(armed, dtype=float)
    n = a.size
    fa = np.fft.rfft(a)
    armed_idx = np.flatnonzero(a)
    non_idx = np.flatnonzero(a == 0)
    rng = np.random.default_rng(seed)
    n_blocks = len(block_offsets)
    n_positives = sum(len(b) for b in block_offsets)
    # episode 個別化規約 (gap >= 30 暦日) を営業日で近似した最小間隔。
    # これを下回る配置は `episode_blocks` で 1 block に潰れてしまう。
    _GAP_BD = 21

    def _p(lab):
        tp = np.round(np.fft.irfft(fa * np.conj(np.fft.rfft(lab)), n))
        npos = lab.sum()
        fp = a.sum() - tp
        j = tp / npos - fp / (n - npos)
        null = j[1:]
        return float(j[0]), float((1 + (null >= j[0]).sum()) / (1 + null.size))

    def _place(hit_blocks: int):
        """block を丸ごと配置し、**要求した hit/miss を全日で強制**する。

        hit  = その block の **いずれかの日**が armed (検出器の event 意味論と一致)
        miss = その block の **すべての日**が非 armed

        先頭日だけで判定すると、miss 指定の block が後続日で armed に掛かったり、
        hit 指定の block が実は 1 日しか掛かっていなかったりする
        (Codex P2 第6波)。ここでは生成位置の全日を検査して棄却サンプリングする。
        """
        lab = np.zeros(n)
        taken: list[tuple[int, int]] = []          # 配置済み block の [start, end]
        order = rng.permutation(n_blocks)
        for rank, bi in enumerate(order):
            offs = block_offsets[bi]
            span = offs[-1]
            want_hit = rank < hit_blocks
            placed = False
            for _ in range(4000):
                start = int(rng.integers(0, n - span))
                end = start + span
                # 他 block の episode-gap 近傍に入る配置は棄却 (4 block を保つ)
                if any(start - _GAP_BD <= e and s0 - _GAP_BD <= end
                       for s0, e in taken):
                    continue
                pos = [start + o for o in offs]
                if any(a[q] for q in pos) != want_hit:
                    continue
                for q in pos:
                    lab[q] = 1
                taken.append((start, end))
                placed = True
                break
            if not placed:
                return None
        return lab

    out = []
    for hb in range(n_blocks + 1):
        js, sig, kept, attempts = [], 0, 0, 0
        # `reps` は **受理された draw の数** であって試行回数ではない
        # (Codex P2 第9波: 442-498 本しか集まっていないのに reps=600 と名乗っていた)。
        while kept < reps and attempts < reps * 50:
            attempts += 1
            lab = _place(hb)
            if lab is None or lab.sum() != n_positives:
                continue
            if days is not None:              # 完成サンプルが 4 block か検証
                pos_days = [days[i] for i in np.flatnonzero(lab)]
                if len(episode_blocks(pos_days)) != n_blocks:
                    continue
            j, pv = _p(lab)
            js.append(j)
            sig += pv <= alpha
            kept += 1
        out.append({"hit_blocks": hb, "n_blocks": n_blocks,
                    "mean_j": sum(js) / kept, "power": sig / kept,
                    "reps_kept": kept, "attempts": attempts,
                    "reached_target_reps": kept == reps})
    return out


def null_structure_diagnostic(days: list, iv_days: list) -> dict:
    """凍結 null (label 系列の circular shift) が 4 block を保つかの診断。

    ⚠️ **これは検定ではない** — signal (armed) を一切参照せず、
    「ラベル × カレンダー × シフト」だけの構造的性質を数える。
    J も p も計算しないので explore の look を消費しない。

    凍結 null は「ラベル系列を一様に circular shift」と規定されており、
    実装はそのとおり。ただし営業日 index 上で一様にずらしても、
    **暦日ベースの episode 規約 (gap >= 30 暦日) は保たれない**ことがある
    (span 20 営業日の block が祝日の多い区間に落ちると 2 episode に割れる)。
    その割合をここで可視化する (Codex P2 第8波)。
    """
    n = len(days)
    idx = {d: i for i, d in enumerate(days)}
    iv_bd = [d for d in iv_days if d in idx]
    lab = [d in set(iv_bd) for d in days]
    base = len(episode_blocks(iv_bd))
    counts: dict[int, int] = {}
    for k in range(1, n):
        sh = circular_shift(lab, k)
        nb = len(episode_blocks([days[i] for i, v in enumerate(sh) if v]))
        counts[nb] = counts.get(nb, 0) + 1
    non_preserving = sum(v for b, v in counts.items() if b != base)
    return {
        "observed_blocks": base,
        "n_shifts": n - 1,
        "block_count_distribution": {str(k): v for k, v in sorted(counts.items())},
        "non_preserving_shifts": non_preserving,
        "non_preserving_fraction": non_preserving / (n - 1),
        "note": ("凍結 null は『ラベル系列の一様 circular shift』であり実装はそのとおり。"
                 "ただし営業日 index 上の一様シフトは暦日 episode 規約 (gap>=30d) を"
                 "厳密には保たない。**事後修正は §10.5 で禁止** (null を変えると p が変わる = "
                 "凍結された primary の作り替え) — verdict は FAIL のまま、"
                 "本診断は限界の開示であって再解析ではない。"),
    }


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
