#!/usr/bin/env python3
"""E23 pass-0: コーパス census + 機械 gate 判定 (outcome 非接触).

pre-reg 🔒 `knowledge-base/wiki/decisions/e23-cb-text-explore-prereg-2026-09-10.md`
§2 の **pass-0 census gates** を機械実行する。

判定する gate (pre-reg §2 転記、逸脱禁止)
------------------------------------------
- per-CB 被覆: explore 窓 (2014-01-01〜2023-12-31) の各年 >=6 声明を
  **80% 以上の年** で確保できない CB は機械的に除外 (件数報告)。
- 生存 CB < 2 → **DATA-BLOCKED** (pass-1 非解錠、設計変更禁止、正直クローズ)。

併せて報告する記述量 (敵対的検証 §7 の監査可能化要求、選択には不使用)
-------------------------------------------------------------------
- V1: Fed/ECB 同一 UTC 日の衝突件数 (§2 両イベント void 規則の該当数)
- V2: 声明間隔の分布 + 定例/非定例の目安 (<20 日間隔 = off-cycle 候補) 件数
- V3: BoJ 英語版に印字された日付 == 会合日 (URL 日付) の一致率
       (= 英語テキストが決定当日付で存在することの機械的確認)
- V4: 極性反転名詞 (unemployment) に該当した bigram の件数
- V5: 照合 bigram の頻度上位 (prefix wildcard の偽陽性を監査可能にする)
- §3 staleness: 直前声明との間隔 > 120 暦日 (当該イベント void) の件数

**やらないこと (pass-1/pass-2 の領分)**
--------------------------------------
- 文書ごとの NH / ΔNH の算出、イベント (ΔNH != 0) の列挙 → pass-1
- 価格・リターンの読み込み → pass-2 (本モジュールは価格を一切開かない)

使い方
------
    python3 tools/e23_corpus_census.py                    # 標準出力に要約
    python3 tools/e23_corpus_census.py --write            # KB へ census 成果物を書く
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from e23_corpus_fetch import (  # noqa: E402
    CBS,
    EXPLORE_END,
    EXPLORE_START,
    load_corpus,
)

# pre-reg §2 / §3 凍結閾値
MIN_DOCS_PER_YEAR = 6
MIN_YEAR_COVERAGE_FRAC = 0.80
MIN_SURVIVING_CBS = 2
STALENESS_VOID_DAYS = 120
OFF_CYCLE_HINT_DAYS = 20  # 記述のみ (判定不使用)

OUT_MD = ROOT / "knowledge-base" / "raw" / "analysis" / "e23-pass0-census-2026-09-15.md"
OUT_JSON = ROOT / "knowledge-base" / "raw" / "analysis" / "e23-pass0-census-2026-09-15.json"

EXPLORE_YEARS = list(range(EXPLORE_START.year, EXPLORE_END.year + 1))


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _in_explore(rec: dict) -> bool:
    return EXPLORE_START <= _d(rec["date"]) <= EXPLORE_END


def census(docs: list[dict]) -> dict:
    from e23_lexicon_apel_grimaldi import count_bigrams

    explore = [r for r in docs if _in_explore(r)]
    usable = [r for r in explore if r.get("n_chars", 0) > 0]
    mechanical_missing = collections.Counter(
        (r["cb"], r.get("missing_reason", "empty_text"))
        for r in explore if r.get("n_chars", 0) == 0
    )

    per_cb: dict[str, dict] = {}
    for cb in CBS:
        recs = sorted((r for r in usable if r["cb"] == cb), key=lambda r: r["date"])
        by_year = collections.Counter(_d(r["date"]).year for r in recs)
        years_ok = [y for y in EXPLORE_YEARS if by_year.get(y, 0) >= MIN_DOCS_PER_YEAR]
        frac = len(years_ok) / len(EXPLORE_YEARS)

        dates = [_d(r["date"]) for r in recs]
        gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
        bi = collections.Counter()
        hawk = dove = inverted = docs_with_match = 0
        for r in recs:
            c = count_bigrams(r["text"])
            if c["hawk"] or c["dove"]:
                docs_with_match += 1
            hawk += c["hawk"]
            dove += c["dove"]
            for pol, adj, noun in c["matches"]:
                bi[f"{adj} {noun}"] += 1
                if noun == "unemployment":
                    inverted += 1

        per_cb[cb] = {
            "n_docs_explore": len(recs),
            "per_year": {str(y): by_year.get(y, 0) for y in EXPLORE_YEARS},
            "years_meeting_min": len(years_ok),
            "year_coverage_frac": round(frac, 3),
            "coverage_gate_pass": frac >= MIN_YEAR_COVERAGE_FRAC,
            "gap_days": {
                "n": len(gaps),
                "median": statistics.median(gaps) if gaps else None,
                "min": min(gaps) if gaps else None,
                "max": max(gaps) if gaps else None,
                "gt_120d_void": sum(1 for g in gaps if g > STALENESS_VOID_DAYS),
                "lt_20d_offcycle_hint": sum(1 for g in gaps if g < OFF_CYCLE_HINT_DAYS),
            },
            "bigrams": {
                "hawk_total": hawk,
                "dove_total": dove,
                "inverted_unemployment_matches": inverted,
                # 辞書の当たり密度 — Gate B (pooled イベント N>=100) の到達可能性に
                # 直結する量。NH の分子は matched bigram のみで決まるため、
                # 無ヒット文書は NH=0 となり ΔNH も 0 になりやすい。
                "docs_with_any_match": docs_with_match,
                "match_density_per_doc": round((hawk + dove) / len(recs), 3)
                if recs else None,
                "top20": bi.most_common(20),
            },
            "n_chars": {
                "median": int(statistics.median([r["n_chars"] for r in recs]))
                if recs else None,
                "min": min((r["n_chars"] for r in recs), default=None),
                "max": max((r["n_chars"] for r in recs), default=None),
                # 年次中央値 — 文書長のレジーム変化 (例: ECB の press release は
                # 2016 年前後で長さが一桁変わる) を隠さず露出させる。判定不使用。
                "median_per_year": {
                    str(y): int(statistics.median(
                        [r["n_chars"] for r in recs if _d(r["date"]).year == y]))
                    for y in EXPLORE_YEARS
                    if any(_d(r["date"]).year == y for r in recs)
                },
            },
        }

    # V1: Fed/ECB 同一 UTC 日衝突 (両イベント void)
    fed_days = {r["date"] for r in usable if r["cb"] == "fed"}
    ecb_days = {r["date"] for r in usable if r["cb"] == "ecb"}
    collisions = sorted(fed_days & ecb_days)

    # V3: BoJ 英語版の当日付一致率
    boj = [r for r in usable if r["cb"] == "boj"]
    boj_attested = sum(1 for r in boj if r.get("same_day_attested") is True)

    survivors = [cb for cb in CBS if per_cb[cb]["coverage_gate_pass"]]
    if "boj" in survivors and boj and boj_attested != len(boj):
        # V3 機械規則: 同時性が確認できない期間があれば当該 CB を除外
        survivors = [cb for cb in survivors if cb != "boj"]

    verdict = "PASS_TO_PASS1" if len(survivors) >= MIN_SURVIVING_CBS else "DATA-BLOCKED"

    # Gate B (pooled イベント N>=100) 到達可能性の**上界** (列挙ではない)。
    # ΔNH_t != 0 には NH_t か NH_{t-1} の少なくとも一方が非ゼロである必要があり、
    # 1 つの非ゼロ文書は最大 2 つの隣接ペアにしか関与できない。よって
    #   events <= 2 * (matched bigram を 1 つ以上持つ文書数)
    # が機械的に従う。実際の N は pass-1 が列挙するまで未知。
    docs_matched = sum(per_cb[cb]["bigrams"]["docs_with_any_match"]
                       for cb in survivors)
    event_bound = 2 * docs_matched

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prereg": "knowledge-base/wiki/decisions/"
                  "e23-cb-text-explore-prereg-2026-09-10.md",
        "pass": "pass-0 census (outcome 非接触 — 価格データ未参照)",
        "explore_window": [EXPLORE_START.isoformat(), EXPLORE_END.isoformat()],
        "frozen_thresholds": {
            "min_docs_per_year": MIN_DOCS_PER_YEAR,
            "min_year_coverage_frac": MIN_YEAR_COVERAGE_FRAC,
            "min_surviving_cbs": MIN_SURVIVING_CBS,
            "staleness_void_days": STALENESS_VOID_DAYS,
        },
        "n_docs_total": len(docs),
        "n_docs_explore": len(explore),
        "n_docs_explore_usable": len(usable),
        "mechanical_missing": {f"{cb}:{why}": n
                               for (cb, why), n in sorted(mechanical_missing.items())},
        "per_cb": per_cb,
        "fed_ecb_same_day_collisions": collisions,
        "boj_same_day_attested": {"n": len(boj), "attested": boj_attested},
        "surviving_cbs": survivors,
        "verdict": verdict,
        "power_flag": {
            "docs_with_any_match_surviving": docs_matched,
            "event_count_upper_bound": event_bound,
            "gate_b_threshold": 100,
            "gate_b_reachable_upper_bound": event_bound >= 100,
            "note": "上界であって列挙ではない (実 N は pass-1 が決める)",
        },
    }


def render_md(c: dict) -> str:
    lines = [
        "# E23 pass-0 コーパス census — 2026-09-15",
        "",
        f"**pre-reg**: [[../../wiki/decisions/e23-cb-text-explore-prereg-2026-09-10|"
        f"E23 explore pre-reg 🔒]] / **pass**: {c['pass']}",
        f"**生成**: `tools/e23_corpus_census.py` @ {c['generated_at']} / "
        f"コーパス取得 = `tools/e23_corpus_fetch.py`",
        f"**explore 窓**: {c['explore_window'][0]} 〜 {c['explore_window'][1]} "
        f"(pre-reg §2 凍結)",
        "",
        f"## verdict: **{c['verdict']}** (生存 CB = "
        f"{', '.join(c['surviving_cbs']) or 'なし'})",
        "",
        f"- コーパス総数 {c['n_docs_total']} 文書 / explore 窓 "
        f"{c['n_docs_explore']} (本文取得成功 {c['n_docs_explore_usable']})",
        f"- 機械的欠測: {c['mechanical_missing'] or 'なし'}",
        "",
        "## per-CB 被覆 gate (pre-reg §2: 各年 ≥6 声明を ≥80% の年で)",
        "",
        "| CB | explore 文書数 | 条件充足年 / 10 | 被覆率 | gate | 中央文字数 |",
        "|---|---|---|---|---|---|",
    ]
    for cb in CBS:
        p = c["per_cb"][cb]
        lines.append(
            f"| {cb} | {p['n_docs_explore']} | {p['years_meeting_min']}/10 | "
            f"{p['year_coverage_frac']:.0%} | "
            f"{'✅ PASS' if p['coverage_gate_pass'] else '❌ 除外'} | "
            f"{p['n_chars']['median']} |"
        )
    lines += ["", "### 年次内訳", "",
              "| CB | " + " | ".join(str(y) for y in EXPLORE_YEARS) + " |",
              "|---|" + "---|" * len(EXPLORE_YEARS)]
    for cb in CBS:
        p = c["per_cb"][cb]
        lines.append(f"| {cb} | " + " | ".join(
            str(p["per_year"][str(y)]) for y in EXPLORE_YEARS) + " |")

    lines += ["", "## 記述量 (敵対的検証 §7 の監査可能化、判定不使用)", "",
              "| CB | 間隔中央/最小/最大 (日) | >120d void | <20d off-cycle 候補 |"
              " hawk / dove bigram | 反転 (unemployment) |",
              "|---|---|---|---|---|---|"]
    for cb in CBS:
        p = c["per_cb"][cb]
        g, b = p["gap_days"], p["bigrams"]
        lines.append(
            f"| {cb} | {g['median']} / {g['min']} / {g['max']} | {g['gt_120d_void']} | "
            f"{g['lt_20d_offcycle_hint']} | {b['hawk_total']} / {b['dove_total']} | "
            f"{b['inverted_unemployment_matches']} |"
        )
    pf = c["power_flag"]
    lines += [
        "",
        "## ⚠️ Gate B (pooled イベント N≥100) 到達可能性の上界",
        "",
        f"- 生存 CB の explore 文書のうち **matched bigram を 1 つ以上持つ文書 = "
        f"{pf['docs_with_any_match_surviving']} 件** → イベント数の機械的上界 = "
        f"**{pf['event_count_upper_bound']}** "
        f"({'≥' if pf['gate_b_reachable_upper_bound'] else '<'} Gate B 閾値 "
        f"{pf['gate_b_threshold']})",
        f"- 導出: ΔNH_t ≠ 0 には NH_t / NH_{{t−1}} の少なくとも一方が非ゼロ必要。"
        "非ゼロ文書 1 件は隣接ペア 2 つにしか関与できない。**上界であって列挙ではない** "
        "(実 N は pass-1 が決める)。",
        "- 当たり密度 (matched bigram / 文書): "
        + ", ".join(f"{cb} {c['per_cb'][cb]['bigrams']['match_density_per_doc']}"
                    for cb in CBS),
        "",
    ]
    coll = c["fed_ecb_same_day_collisions"]
    boj = c["boj_same_day_attested"]
    lines += [
        "",
        f"- **V1 Fed/ECB 同日衝突 (両 void)**: {len(coll)} 件"
        + (f" — {', '.join(coll)}" if coll else ""),
        f"- **V3 BoJ 英語版 当日付一致**: {boj['attested']}/{boj['n']}"
        f" ({'全件一致' if boj['n'] and boj['attested'] == boj['n'] else '⚠️ 不一致あり'})",
        "",
        "### V5 照合 bigram 頻度上位 (prefix wildcard 偽陽性の監査用)",
        "",
    ]
    for cb in CBS:
        top = c["per_cb"][cb]["bigrams"]["top20"][:10]
        if top:
            lines.append(f"- **{cb}**: " + ", ".join(f"`{k}`×{v}" for k, v in top))
    lines += [
        "",
        "## 規律メモ",
        "",
        "- 本 census は**価格データを一切読んでいない** (outcome 非接触)。"
        "文書ごとの NH / ΔNH・イベント列挙は pass-1 の領分で、ここでは算出していない"
        " (報告した bigram 量は §7 V4/V5 が要求する辞書監査の集計のみ)。",
        "- 本文抽出は公式ページの本文コンテナをそのまま採る **無トリム規則**。"
        "定型フッタ (媒体連絡先・転載条項等) は hawk/dove bigram に寄与せず、"
        "かつ ΔNH は定数を打ち消すため、トリム規則を置かないことで抽出 DoF を閉じた。",
        "- BOE のみ公式ページが MPS + minutes を 1 ページに載せるため、MPS 節の"
        "境界語を `tools/e23_corpus_fetch.py` で凍結し `tests/test_e23_corpus_harness.py`"
        " で pin した。境界語が取れない文書は機械的欠測として上表に数える。",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="KB に census 成果物を書く")
    args = ap.parse_args(argv)

    docs = load_corpus()
    if not docs:
        print("corpus empty — run tools/e23_corpus_fetch.py first", file=sys.stderr)
        return 2
    c = census(docs)
    md = render_md(c)
    print(md)
    if args.write:
        OUT_MD.parent.mkdir(parents=True, exist_ok=True)
        OUT_MD.write_text(md, encoding="utf-8")
        OUT_JSON.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")
        print(f"wrote {OUT_MD.relative_to(ROOT)} / {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
