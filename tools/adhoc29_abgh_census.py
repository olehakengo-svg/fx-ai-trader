#!/usr/bin/env python3
"""#29 S1 step 1 — ABGH-2019 辞書の価格非接触 census (連続同一 CB 声明ペアの |ΔNH| > τ 割合).

承認: [[external-hypothesis-scan-round6-2026-10-20]] §3-(i) (診断枠、rule:R3、$0) +
#29-L user 承認 2026-11-03 (§9.1、辞書転記 gate 解除)。
クローズ条件 (adhoc-scan-29-step0 §7-3 文言、不改変):
  「ABGH-2019 の適格連続同一 CB 声明ペア (staleness >120 暦日と Fed・ECB 同日衝突は
   分母からも除外、各 CB 初回は分母外) のうち |ΔNH| > τ (τ = 0 凍結) の割合 ≤ 50%
   (過半未達 — 丁度半数は不通過) なら dense primary 不在 → #29 S1 候補なしクローズ」
  スコア式は公刊 as-is: NH = 1 + (h−d)/(h+d)、h+d=0 のみ NH=1 (中立) 代入。

母集団 (E23 ペア規則継承、価格非接触)
-------------------------------------
- コーパス = `tools/e23_corpus_fetch.load_corpus()` (P1 監査後 loader: Fed 非 statement
  除外、窓外除外) の explore 窓 [EXPLORE_START, EXPLORE_END] ∧ n_chars > 0。
- CB = pass-0 生存 3 CB (fed / ecb / boe; BoJ は V3 公開時刻未検証で fail-closed —
  `knowledge-base/raw/analysis/e23-pass1-events-2026-10-01.md`)。
- ペア = 同一 CB の日付順で直前声明とペア。各 CB 初回は分母外。
  staleness (間隔 > 120 暦日) と Fed×ECB 同日衝突 (判定日は 4 CB 全体の usable docs
  から取る、`e23_pass1_events.enumerate_events` と同じ) は **分母からも除外**
  (pass-1 と同じ void 規則。pass-1 10-01 では両 void とも 0 件)。
- 本モジュールは価格・リターン・イベント写像 (t0 / pair / direction) を一切読まない。

出力 (件数・割合のみ)
--------------------
- primary: 適格ペア数 n、|ΔNH| > 0 のペア数 k、割合 k/n、verdict (> 50% 厳密で DENSE_PASS)。
- 記述 secondary: CB 別 n/k、文書 h+d>0 割合、NH≠1 割合、|ΔNH| の分位、h/d 総数。
- 参照値 (記述のみ、ゲート不使用): ABG-2012 監査後 40/228 = 17.5% (pass-1 10-01、
  生存 3 CB) / 監査前 56/323 = 17.3% (pass-1 09-15、4 CB)。

使い方
------
    python3 tools/adhoc29_abgh_census.py            # 標準出力に要約
    python3 tools/adhoc29_abgh_census.py --write    # knowledge-base/raw/analysis/ に json + md
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from adhoc29_lexicon_abgh2019 import (  # noqa: E402
    NEUTRAL_NH,
    count_combinations,
    dictionary_sha256,
    net_hawkishness,
)

SURVIVING_CBS: tuple[str, ...] = ("fed", "ecb", "boe")   # pass-0 再計算 2026-10-01
STALENESS_VOID_DAYS = 120                                # E23 pre-reg §3 (= e23_pass1_events)
TAU = 0.0                                                # step0 §7-3 凍結
DENSE_THRESHOLD = 0.5                                    # 過半 = 厳密不等号 (> 0.5)
REFERENCE_VALUES = {
    "abg2012_post_audit_pass1_2026_10_01": {"k": 40, "n": 228, "share": 40 / 228,
                                             "cbs": ["fed", "ecb", "boe"]},
    "abg2012_pre_audit_pass1_2026_09_15": {"k": 56, "n": 323, "share": 56 / 323,
                                            "cbs": ["fed", "ecb", "boe", "boj"]},
}
OUT_DIR = ROOT / "knowledge-base" / "raw" / "analysis"


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


def wilson_interval(k: int, n: int, z: float = 1.959964) -> dict:
    """二項割合の Wilson 95% 区間 (記述用。ゲートは点推定で事前固定、区間は採否に使わない)。"""
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return {"lo": centre - half, "hi": centre + half, "z": z}


def enumerate_pairs(docs: list[dict], *, cbs: tuple[str, ...] = SURVIVING_CBS,
                    window: tuple[date, date] | None = None,
                    score=net_hawkishness) -> dict:
    """連続同一 CB ペアを列挙し、|ΔNH| > TAU を数える (価格非接触).

    docs: {"cb", "date", "text", "n_chars"} のレコード。window=None なら全件。
    score: text -> NH の関数 (test 用に差し替え可。本番は ABGH-2019)。
    """
    usable_all = [r for r in docs if r.get("n_chars", 0) > 0
                  and (window is None or window[0] <= _d(r["date"]) <= window[1])]
    fed_days = {r["date"] for r in usable_all if r["cb"] == "fed"}
    ecb_days = {r["date"] for r in usable_all if r["cb"] == "ecb"}
    collision_days = fed_days & ecb_days

    by_cb: dict[str, list[dict]] = {}
    for r in sorted((r for r in usable_all if r["cb"] in cbs),
                    key=lambda r: (r["cb"], r["date"])):
        by_cb.setdefault(r["cb"], []).append(r)

    per_cb: dict[str, dict] = {}
    pairs: list[dict] = []
    docs_scored: list[dict] = []
    voids: dict[str, int] = {}

    def bump(k: str) -> None:
        voids[k] = voids.get(k, 0) + 1

    for cb, recs in by_cb.items():
        stats = per_cb.setdefault(cb, {"docs": 0, "docs_with_hits": 0, "docs_nh_ne_neutral": 0,
                                       "first_excluded": 0, "eligible_pairs": 0,
                                       "drift_pairs": 0})
        prev = None
        for r in recs:
            c = count_combinations(r["text"])
            nh = score(r["text"])
            stats["docs"] += 1
            if c["hawk"] + c["dove"] > 0:
                stats["docs_with_hits"] += 1
            if nh != NEUTRAL_NH:
                stats["docs_nh_ne_neutral"] += 1
            docs_scored.append({"cb": cb, "date": r["date"], "hawk": c["hawk"],
                                "dove": c["dove"], "nh": nh})
            if prev is None:
                stats["first_excluded"] += 1
                prev = (r, nh)
                continue
            prev_rec, prev_nh = prev
            prev = (r, nh)
            gap = (_d(r["date"]) - _d(prev_rec["date"])).days
            if gap > STALENESS_VOID_DAYS:
                bump(f"{cb}:staleness_gt_{STALENESS_VOID_DAYS}d")
                continue
            if cb in ("fed", "ecb") and r["date"] in collision_days:
                bump(f"{cb}:fed_ecb_same_day")
                continue
            delta = nh - prev_nh
            drift = abs(delta) > TAU
            stats["eligible_pairs"] += 1
            if drift:
                stats["drift_pairs"] += 1
            pairs.append({"cb": cb, "date": r["date"], "prev_date": prev_rec["date"],
                          "gap_days": gap, "nh": nh, "prev_nh": prev_nh,
                          "abs_delta": abs(delta), "drift": drift})

    n = len(pairs)
    k = sum(1 for p in pairs if p["drift"])
    abs_deltas = sorted(p["abs_delta"] for p in pairs if p["drift"])
    return {
        # 記述のみ (ゲートは点推定の share_drift > 0.5。区間は knife-edge の可視化用)
        "wilson_95": wilson_interval(k, n) if n else None,
        "cbs": list(cbs),
        "n_docs_usable": len(by_cb and [r for recs in by_cb.values() for r in recs]),
        "collision_days": sorted(collision_days),
        "voids": dict(sorted(voids.items())),
        "per_cb": per_cb,
        "n_eligible_pairs": n,
        "k_drift_pairs": k,
        "share_drift": (k / n) if n else None,
        "docs_with_hits": sum(s["docs_with_hits"] for s in per_cb.values()),
        "docs_nh_ne_neutral": sum(s["docs_nh_ne_neutral"] for s in per_cb.values()),
        "hawk_total": sum(d["hawk"] for d in docs_scored),
        "dove_total": sum(d["dove"] for d in docs_scored),
        "abs_delta_quantiles_drift_only": (
            {"min": abs_deltas[0], "p25": statistics.quantiles(abs_deltas, n=4)[0],
             "p50": statistics.median(abs_deltas),
             "p75": statistics.quantiles(abs_deltas, n=4)[2], "max": abs_deltas[-1]}
            if len(abs_deltas) >= 4 else {"values": abs_deltas}),
        "pairs": pairs,
        "docs": docs_scored,
    }


def verdict(share: float | None) -> str:
    if share is None:
        return "NO_ELIGIBLE_PAIRS"
    return "DENSE_PASS" if share > DENSE_THRESHOLD else "NOT_DENSE_CLOSE"


def census(docs: list[dict] | None = None) -> dict:
    if docs is None:
        from e23_corpus_fetch import EXPLORE_END, EXPLORE_START, load_corpus
        docs = load_corpus()
        window = (EXPLORE_START, EXPLORE_END)
    else:
        window = None
    enum = enumerate_pairs(docs, window=window)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "approval": "external-hypothesis-scan-round6-2026-10-20 §3-(i) + §9.1 #29-L (2026-11-03)",
        "close_condition_doc": "adhoc-scan-29-step0-2026-09-22 §7-3 (不改変)",
        "lexicon": "tools/adhoc29_lexicon_abgh2019.py (WP 381 Appendix Tables 4–6 逐語転記)",
        "lexicon_sha256": dictionary_sha256(),
        "tau": TAU,
        "dense_threshold_strict_gt": DENSE_THRESHOLD,
        "reference_values": REFERENCE_VALUES,
        "price_contact": False,
        "enumeration": enum,
        "verdict": verdict(enum["share_drift"]),
    }


def render_md(c: dict, out_date: str) -> str:
    e = c["enumeration"]
    n, k, share = e["n_eligible_pairs"], e["k_drift_pairs"], e["share_drift"]
    share_s = f"{share:.1%}" if share is not None else "n/a"
    lines = [
        f"# #29 S1 step 1 — ABGH-2019 辞書 census (価格非接触) — {out_date}",
        "",
        f"**辞書**: `tools/adhoc29_lexicon_abgh2019.py` (WP 381 Appendix Tables 4–6 逐語転記、"
        f"sha256 `{c['lexicon_sha256'][:16]}…`) / **承認**: {c['approval']} / "
        f"**クローズ条件**: {c['close_condition_doc']} / **生成**: `tools/adhoc29_abgh_census.py` @ {c['generated_at']}",
        "",
        "> **firewall**: 価格・リターン・t0 写像・ペア方向は一切読んでいない。数値は文書数・ペア数・"
        "辞書カウントのみ。閾値・ホライズン・ペア写像の探索はしていない (τ = 0 凍結、> 50% 厳密)。",
        "",
        f"## verdict: **{c['verdict']}**",
        "",
        f"- 適格連続同一 CB ペア n = **{n}** / |ΔNH| > τ (τ = {c['tau']}) のペア k = **{k}** / "
        f"割合 = **{share_s}** (ゲート: > 50% 厳密で dense primary、≤ 50% で #29 S1 候補なしクローズ)",
        (f"- 記述 (ゲート不使用): Wilson 95% 区間 [{e['wilson_95']['lo']:.3f}, {e['wilson_95']['hi']:.3f}]"
         f" — 下限が 0.5 を{'割る' if e['wilson_95']['lo'] <= 0.5 else '上回る'}"
         if e.get("wilson_95") else "- Wilson 区間: n/a"),
        f"- 生存 CB = {', '.join(e['cbs'])} (pass-0 再計算 2026-10-01) / usable 文書 {e['n_docs_usable']} "
        f"/ Fed×ECB 同日 {len(e['collision_days'])} 日 / void = {e['voids'] or '0 件'}",
        "- 参照値 (記述のみ、ゲート不使用): ABG-2012 監査後 40/228 = 17.5% (pass-1 10-01、3 CB) / "
        "監査前 56/323 = 17.3% (pass-1 09-15、4 CB)",
        "",
        "## CB 別 (件数のみ)",
        "",
        "| CB | 文書 | h+d>0 文書 | NH≠1 文書 | 初回 (分母外) | 適格ペア n | \\|ΔNH\\|>0 ペア k | k/n |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for cb, s in e["per_cb"].items():
        r = f"{s['drift_pairs'] / s['eligible_pairs']:.1%}" if s["eligible_pairs"] else "n/a"
        lines.append(f"| {cb} | {s['docs']} | {s['docs_with_hits']} | {s['docs_nh_ne_neutral']} | "
                     f"{s['first_excluded']} | {s['eligible_pairs']} | {s['drift_pairs']} | {r} |")
    q = e["abs_delta_quantiles_drift_only"]
    lines += [
        "",
        "## 記述 secondary (ゲート不使用)",
        "",
        f"- 文書 h+d>0 割合: {e['docs_with_hits']}/{e['n_docs_usable']} / NH≠1 割合: "
        f"{e['docs_nh_ne_neutral']}/{e['n_docs_usable']} / hawk 総数 {e['hawk_total']} / dove 総数 {e['dove_total']}",
        f"- |ΔNH| 分布 (drift ペアのみ): {json.dumps(q)}",
        "",
        "## 凍結規則の再掲 (実装どおり)",
        "",
        "- NH = 1 + (h−d)/(h+d) (WP 381 式 (1))、h+d=0 のみ NH=1 代入。窓 = 同一文内 ≤7 語 (前後どちらも)。"
        "TERM 完全一致・最長一致 1 件、MODIFIER `*` = 語幹前方一致。計数 = TERM 出現 × 窓内 MODIFIER 出現。",
        "- ペア規則 = E23 継承 (同一 CB 直前声明、staleness >120d void、Fed×ECB 同日 void、各 CB 初回は分母外)。"
        "void は分母からも除外。",
        "- Table 5 \"consumer spending\" HAWKISH 列の `soft*` / `weak*` は印字どおり転記 (語彙編集なし)。",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args(argv)
    c = census()
    e = c["enumeration"]
    print(f"verdict={c['verdict']} n={e['n_eligible_pairs']} k={e['k_drift_pairs']} "
          f"share={e['share_drift']} voids={e['voids']} lexicon={c['lexicon_sha256'][:16]}")
    for cb, s in e["per_cb"].items():
        print(f"  {cb}: {s}")
    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        jp = OUT_DIR / f"adhoc29-abgh-census-{args.date}.json"
        mp = OUT_DIR / f"adhoc29-abgh-census-{args.date}.md"
        jp.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        mp.write_text(render_md(c, args.date), encoding="utf-8")
        print(f"wrote {jp}\nwrote {mp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
