#!/usr/bin/env python3
"""WS3 探索2周目 — 方向性非対称の新軸診断スキャン (rule:R3、純研究)

pre-reg DRAFT: knowledge-base/wiki/decisions/ws3-round2-explore-prereg-2026-07-10.md
(branch research/h4-level-edge。§2 の候補生成手続きを機械的に実装)

軸 (round-1 の補集合のみ):
- (a) 方向分割 (entry_type × pair × sig) — round-1 は方向プール
- (b) 未走査ペア = production shadow 母集団 (MODE_CONFIG compute_daytrade_signal×15m)
      のうち round-1 h24 表に現れなかったペア → EUR_GBP のみ (pooled + 方向分割)
- (c) h24/h96 両 horizon 集計 — 持続型 (h96 増幅) の拾い上げ

母集団:
- round-1 entries = `.ws3_mfe_scan_checkpoint.json` (commit 604dcc4f、N=6,995、
  探索窓 2025-07-08〜2026-06-07、診断窓除外済) をそのまま使用 — 窓の同一性を
  構成的に保証 (再BTによる窓ズレなし)。
- EUR_GBP entries = `.ws3_mfe_scan_checkpoint_round2_eurgbp.json`
  (tools/ws3_round2_prep_eurgbp.py で round-1 と同一窓の parquet を構築し
   tools/ws3_mfe_scan.py --pairs EUR_GBP --split-direction で生成)

除外 (§2、機械適用):
- stage-1 判定済み 8 セル (ws3-asymmetry-oos-prereg-2026-07-09.md §2) と
  その方向分割サブセル (多重性ロンダリング防止)
- falsified 6 系統の entry_type: channel→lin_reg_channel /
  水平sweep&reclaim→liquidity_sweep / bb_rsi→dt_bb_rsi_mr (系統パターン掃引、
  bb_rsi_reversion は 1m scalp のため母集団に不存在) /
  H4 level・mtf_regime_switch SELL・T11 counter-USD → 母集団に entry_type 不存在 (非該当ログ)
- trendline_sweep×EUR_USD (stage-1 #2 かつ §8.3(c) live N 蓄積経路限定)

選抜規則 (§2、事前固定): 探索窓 N≥30 ∧ (ratio_h24≥1.3 ∪ 持続型
(ratio_h96≥1.3 ∧ ratio_h96>ratio_h24))。m≤10 (primary ratio 降順で切る)。
ratio = median(MFE)/median(MAE) (stage-1 と同一定義)。

OOS 窓 (2024-07-07〜2025-07-07) のデータ・統計には一切接触しない。
live/shadow/本番への変更なし。出力は診断集計のみ (promote 判定ではない)。

実行: python3 tools/ws3_round2_scan.py
"""

import argparse
import json
import os
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BT_DIR = os.path.join(REPO, "knowledge-base", "raw", "bt-results")

R1_CHECKPOINT = os.path.join(BT_DIR, ".ws3_mfe_scan_checkpoint.json")
EURGBP_CHECKPOINT = os.path.join(BT_DIR, ".ws3_mfe_scan_checkpoint_round2_eurgbp.json")
OUT_JSON = os.path.join(BT_DIR, "ws3_round2_scan_2026_07.json")
OUT_MD = os.path.join(BT_DIR, "ws3_round2_scan_2026_07.md")

R1_PAIRS = {"GBP_USD", "EUR_USD", "USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY"}
RATIO_MIN = 1.3
N_MIN = 30
M_MAX = 10
N_TABLE_MIN = 10
H_PRIMARY, H_SUSTAIN = 24, 96

# stage-1 判定済み 8 セル (ws3-asymmetry-oos-prereg-2026-07-09.md §2) — 方向サブセル含め除外
STAGE1_CELLS = [
    ("htf_false_breakout", "EUR_JPY"),
    ("trendline_sweep", "EUR_USD"),
    ("dt_sr_channel_reversal", "EUR_USD"),
    ("london_fix_reversal", "EUR_USD"),
    ("htf_false_breakout", "AUD_JPY"),
    ("lin_reg_channel", "EUR_USD"),
    ("hull_donchian_fade", "EUR_USD"),
    ("dt_fib_reversal", "USD_JPY"),
]

# falsified 6 系統 → 母集団 entry_type への機械マッピング
# (entry_type 単位。マッチしない系統は「非該当」としてログに残す)
FALSIFIED_ENTRY_TYPES = {
    "channel (回帰±2σ/swing平行, project-channel-edge-falsified)": ["lin_reg_channel"],
    "水平sweep&reclaim (project-sweep-reclaim-horizontal-falsified)": ["liquidity_sweep"],
    "bb_rsi (bb_rsi_reversion T10 KILL — 系統パターン掃引。dt_bb_rsi_mr は同系統"
    " (BB+RSI MR) の 15m 版のため保守的に除外。LOCK 前に親判断で復活可": ["dt_bb_rsi_mr"],
    "H4 level (project-h4-level-edge-falsified)": [],       # 母集団に不存在
    "mtf_regime_switch SELL (project-mtf-regime-switch-falsified)": [],  # 同上
    "T11 LDN朝×counter-USD MR (project-t11-ldn-counter-usd-falsified)": [],  # 同上
}


def _median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return None
    mid = n // 2
    return float(s[mid]) if n % 2 else float((s[mid - 1] + s[mid]) / 2.0)


def _cell_stats(rows):
    out = {"n": len(rows)}
    for h in (H_PRIMARY, H_SUSTAIN):
        mfe = _median([r[f"mfe_{h}"] for r in rows])
        mae = _median([r[f"mae_{h}"] for r in rows])
        ratio = round(mfe / mae, 3) if (mfe is not None and mae and mae > 0) else None
        out[f"h{h}"] = {"mfe_p50": round(mfe, 3) if mfe is not None else None,
                        "mae_p50": round(mae, 3) if mae is not None else None,
                        "ratio": ratio}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--r1-checkpoint", default=R1_CHECKPOINT)
    ap.add_argument("--eurgbp-checkpoint", default=EURGBP_CHECKPOINT)
    ap.add_argument("--out-json", default=OUT_JSON)
    ap.add_argument("--out-md", default=OUT_MD)
    args = ap.parse_args()

    with open(args.r1_checkpoint) as f:
        r1_entries = json.load(f)
    # EUR_GBP: BT baseline が engine の最小サンプルガード (<20 trades/365d) に
    # 抵触し entries=0 (ws3_mfe_scan_2026_07_round2_eurgbp.json 参照)。
    # checkpoint 不在時は空扱いで軸(b) の結果として記録する。
    if os.path.exists(args.eurgbp_checkpoint):
        with open(args.eurgbp_checkpoint) as f:
            extra_entries = json.load(f)
    else:
        extra_entries = []

    extra_pairs = sorted({r["pair"] for r in extra_entries})
    entries = r1_entries + extra_entries

    # ── セル構築 ──
    pooled, split = {}, {}
    for r in entries:
        pooled.setdefault((r["entry_type"], r["pair"]), []).append(r)
        split.setdefault((r["entry_type"], r["pair"], r["sig"]), []).append(r)

    stage1 = set(STAGE1_CELLS)
    excl_log = []

    def _excluded(et, pair):
        """除外判定 → (True, 理由) or (False, None)"""
        if (et, pair) in stage1:
            return True, f"stage-1 判定済みセル (ws3-asymmetry-oos-prereg §2)"
        for family, ets in FALSIFIED_ENTRY_TYPES.items():
            if et in ets:
                return True, f"falsified 系統: {family}"
        return False, None

    # ── 集計 + 除外適用 ──
    def _build(cells, kind):
        table, excluded = [], []
        for key, rows in sorted(cells.items()):
            et, pair = key[0], key[1]
            sig = key[2] if len(key) > 2 else None
            name = f"{et}×{pair}" + (f"×{sig}" if sig else "")
            st = _cell_stats(rows)
            hit, reason = _excluded(et, pair)
            rec = {"cell": name, "entry_type": et, "pair": pair, "sig": sig,
                   "kind": kind, **st}
            if hit:
                if st["n"] >= N_TABLE_MIN:
                    excluded.append({**rec, "excl_reason": reason})
                continue
            table.append(rec)
        return table, excluded

    pooled_table, pooled_excl = _build(pooled, "pooled")
    split_table, split_excl = _build(split, "split")
    excl_log.extend(pooled_excl + split_excl)

    # 非該当系統のログ (機械確認: マッチ entry_type ゼロ)
    ets_all = {r["entry_type"] for r in entries}
    family_log = []
    for family, ets in FALSIFIED_ENTRY_TYPES.items():
        present = [t for t in ets if t in ets_all]
        family_log.append({
            "family": family, "mapped_entry_types": ets,
            "present_in_population": present,
            "status": "適用" if present else "非該当 (母集団に entry_type 不存在)",
        })

    # ── 選抜規則 (§2 固定) ──
    def _select(table):
        cands = []
        for rec in table:
            n = rec["n"]
            r24 = rec["h24"]["ratio"]
            r96 = rec["h96"]["ratio"]
            if n < N_MIN or r24 is None:
                continue
            sustained = (r96 is not None and r96 >= RATIO_MIN and r96 > r24)
            if r24 >= RATIO_MIN or sustained:
                primary = "h96" if sustained else "h24"
                cands.append({**rec,
                              "type": "持続" if sustained else "減衰",
                              "primary_horizon": primary,
                              "primary_ratio": r96 if sustained else r24})
        return cands

    candidates = _select(split_table) + _select(
        [r for r in pooled_table if r["pair"] in extra_pairs])
    # axis (c): round-1 ペアの pooled 持続型 (h24 枝は stage-1 で判定済みのため
    # 新規は持続型枝からのみ発生し得る — 機械的に全規則を当て、結果を軸cとして記録)
    pooled_r1_cands = _select([r for r in pooled_table if r["pair"] in R1_PAIRS])
    for c in pooled_r1_cands:
        c["axis"] = "c (round-1 pooled 持続型)"
    for c in candidates:
        c.setdefault("axis", "a (方向分割)" if c["sig"] else "b (新ペア pooled)")
    candidates += pooled_r1_cands

    candidates.sort(key=lambda c: -c["primary_ratio"])
    overflow = candidates[M_MAX:]
    candidates = candidates[:M_MAX]
    for c in overflow:
        excl_log.append({**c, "excl_reason": f"m>{M_MAX} 上限超過 (ratio 降順で切断 — pre-reg §2 宣言)"})

    # ── 出力 ──
    out = {
        "task": "20260710-ws3-round2-explore (診断スキャン)",
        "rule": "R3",
        "prereg": "knowledge-base/wiki/decisions/ws3-round2-explore-prereg-2026-07-10.md (DRAFT, branch research/h4-level-edge)",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "population": {
            "r1_checkpoint": os.path.relpath(args.r1_checkpoint, REPO),
            "r1_entries": len(r1_entries),
            "r1_pairs": sorted(R1_PAIRS),
            "extra_pairs": extra_pairs,
            "extra_entries": len(extra_entries),
            "explore_window": "2025-07-08〜2026-06-07 (365d baseline, 診断窓 2026-06-07〜 除外)",
            "oos_window_untouched": "2024-07-07〜2025-07-07",
        },
        "selection_rule": {
            "ratio_def": "median(MFE)/median(MAE)",
            "rule": f"N≥{N_MIN} ∧ (ratio_h24≥{RATIO_MIN} ∪ 持続型(ratio_h96≥{RATIO_MIN} ∧ h96>h24))",
            "m_max": M_MAX,
            "tie_break": "primary ratio 降順",
        },
        "n_cells": {"pooled": len(pooled_table), "split": len(split_table)},
        "candidates": candidates,
        "candidates_overflow_cut": overflow,
        "exclusion_log": {
            "stage1_cells": [f"{et}×{p}" for et, p in STAGE1_CELLS],
            "falsified_families": family_log,
            "excluded_cells_n_ge_10": excl_log,
        },
        "cells_pooled": pooled_table,
        "cells_split": split_table,
    }
    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    with open(args.out_json, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"[round2] saved {args.out_json}")

    # md は別途 (呼び出し側スクリプト or 手動整形)。ここでは機械表のみ生成
    md = _render_md(out)
    with open(args.out_md, "w") as f:
        f.write(md)
    print(f"[round2] saved {args.out_md}")
    print(json.dumps({"n_candidates": len(candidates),
                      "n_split_cells": len(split_table),
                      "n_pooled_cells": len(pooled_table)}))


def _fmt_row(r):
    r24, r96 = r["h24"]["ratio"], r["h96"]["ratio"]
    return (f"| {r['cell']} | {r['n']} | {r['h24']['mfe_p50']} | {r['h24']['mae_p50']} "
            f"| {r24 if r24 is not None else '—'} | {r96 if r96 is not None else '—'} |")


def _render_md(out) -> str:
    L = [
        "# WS3 探索2周目 — 新軸診断スキャン (機械集計、rule:R3)",
        "",
        f"- 生成: {out['generated_utc']} / pre-reg: {out['prereg']}",
        f"- 母集団: round-1 checkpoint {out['population']['r1_entries']} entries "
        f"(6 pairs) + EUR_GBP {out['population']['extra_entries']} entries / "
        f"探索窓 {out['population']['explore_window']}",
        f"- OOS 窓 ({out['population']['oos_window_untouched']}) 非接触",
        f"- 選抜規則: {out['selection_rule']['rule']}, m≤{out['selection_rule']['m_max']}, "
        f"ratio = {out['selection_rule']['ratio_def']}",
        "",
        "## 候補リスト (選抜規則適用後)",
        "",
        "| # | cell | axis | 型 | N | ratio h24 | ratio h96 | primary |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, c in enumerate(out["candidates"], 1):
        L.append(f"| {i} | {c['cell']} | {c['axis']} | {c['type']} | {c['n']} "
                 f"| {c['h24']['ratio']} | {c['h96']['ratio']} | {c['primary_horizon']} |")
    L += ["", "## 全セル ratio 表 (N≥10)", ""]
    for title, key in (("方向分割セル (axis a)", "cells_split"),
                       ("pooled セル (axis b/c)", "cells_pooled")):
        L += [f"### {title}", "",
              "| cell | N | MFE p50 (h24) | MAE p50 (h24) | ratio h24 | ratio h96 |",
              "|---|---|---|---|---|---|"]
        rows = [r for r in out[key] if r["n"] >= 10]
        rows.sort(key=lambda r: -(r["h24"]["ratio"] or 0))
        L += [_fmt_row(r) for r in rows]
        L.append("")
    L += ["## 除外適用ログ", ""]
    L.append("- stage-1 判定済み 8 セル (方向サブセル含め除外): "
             + ", ".join(out["exclusion_log"]["stage1_cells"]))
    for fl in out["exclusion_log"]["falsified_families"]:
        L.append(f"- {fl['family']}: {fl['status']}"
                 + (f" → {fl['present_in_population']}" if fl["present_in_population"] else ""))
    L += ["", "除外された個別セル (N≥10):", "",
          "| cell | N | ratio h24 | ratio h96 | 理由 |", "|---|---|---|---|---|"]
    for r in out["exclusion_log"]["excluded_cells_n_ge_10"]:
        r24 = r["h24"]["ratio"] if r["h24"]["ratio"] is not None else "—"
        r96 = r["h96"]["ratio"] if r["h96"]["ratio"] is not None else "—"
        L.append(f"| {r['cell']} | {r['n']} | {r24} | {r96} "
                 f"| {r['excl_reason']} |")
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    main()
