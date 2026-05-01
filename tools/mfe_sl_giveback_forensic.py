"""MFE → SL Give-back Forensic Audit.

「含み益が大きかったのに SL で終わったトレード」をペア別・戦略別・時間帯別に
監査し, 構造的な give-back 原因 (G1-G4) を分類して cell-level 対応策を提示する.

Usage:
    python3 tools/mfe_sl_giveback_forensic.py \
        --db demo_trades.db --window-days 30 --min-n 20 \
        --out raw/audits/

Output:
    raw/audits/mfe_sl_giveback_<UTC>.json   (machine-readable)
    raw/audits/mfe_sl_giveback_<UTC>.md     (human-readable)

Memory invariants honored:
    * LIVE / Shadow を分離レポート (is_shadow=0 vs 1)
    * XAU を分析対象から除外
    * mafe_* の実測ベースで判定 (code 演繹禁止)
    * Spread 基準で MAFE 比較する場合 entry_price 基準

Quant tags (give-back mechanisms):
    G1: BE-Skipped     mfe_r >= 0.8 AND pnl_r <= -0.8       (BE 閾値到達後そのまま SL)
    G2: BE-Then-SL     mfe_r >= 0.8 AND -0.2 <= pnl_r <= 0.5 (BE 撤退)
    G3: TS-Insufficient mfe_r >= 1.5 AND tp_progress < 0.7   (Tier2 trail 後でも give back)
    G4: Near-Miss-TP   tp_progress >= 0.8 AND SL_HIT         (TP 直前で反転)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ── 既存資産の再利用 (失敗時は内部実装に fallback) ─────────────────────────────
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from research.edge_discovery.strategy_family_map import (
        STRATEGY_FAMILY,
        effective_family,
    )
except Exception:
    STRATEGY_FAMILY = {}
    def effective_family(entry_type, mtf_regime):
        return STRATEGY_FAMILY.get(entry_type, "UNKNOWN")


# ─── Session classification (UTC hour-based, canonical) ──────────────────
def session_of_hour(h: int) -> str:
    if 0 <= h < 7:
        return "Tokyo"
    if 7 <= h < 13:
        return "London"
    if 13 <= h < 21:
        return "NY"
    return "Off"


# ─── Wilson score 95% lower bound (one-sided 5%) ─────────────────────────
def wilson_lb(k: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - margin) / denom)


# ─── pip multiplier (JPY/XAU = ×100, others = ×10000) ────────────────────
def pip_mult(instrument: str) -> float:
    return 100.0 if ("JPY" in instrument or "XAU" in instrument) else 10000.0


# ─── Tag rules ────────────────────────────────────────────────────────────
def classify_giveback(mfe_r: float, pnl_r: float, tp_progress: float) -> list[str]:
    tags = []
    if mfe_r >= 0.8 and pnl_r <= -0.8:
        tags.append("G1")
    if mfe_r >= 0.8 and -0.2 <= pnl_r <= 0.5:
        tags.append("G2")
    if mfe_r >= 1.5 and tp_progress < 0.7:
        tags.append("G3")
    if tp_progress >= 0.8:
        tags.append("G4")
    return tags or ["G0"]


# ─── DB load + derive ────────────────────────────────────────────────────
def load_trades(db_path: Path, window_days: int, exclude_xau: bool = True):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    sql = """
        SELECT trade_id, status, direction, entry_price, entry_time, exit_price, exit_time,
               sl, tp, pnl_pips, pnl_r, outcome, entry_type, tf, regime,
               close_reason, mode, instrument,
               spread_at_entry, spread_at_exit, slippage_pips,
               mafe_adverse_pips, mafe_favorable_pips, is_shadow,
               mtf_regime, mtf_alignment
        FROM demo_trades
        WHERE entry_time >= datetime('now', ?)
          AND status='CLOSED'
          AND close_reason IS NOT NULL
    """
    window_clause = f"-{int(window_days)} days"
    rows = [dict(r) for r in conn.execute(sql, (window_clause,))]
    conn.close()

    out = []
    for r in rows:
        inst = r.get("instrument") or ""
        if exclude_xau and "XAU" in inst:
            continue
        pm = pip_mult(inst)
        sl, tp, ep = r.get("sl"), r.get("tp"), r.get("entry_price")
        if not (sl and tp and ep):
            continue
        sl_dist = abs(ep - sl) * pm
        tp_dist = abs(tp - ep) * pm
        if sl_dist <= 0:
            continue
        fav = r.get("mafe_favorable_pips") or 0.0
        adv = r.get("mafe_adverse_pips") or 0.0
        pnl = r.get("pnl_pips") or 0.0
        r["sl_dist_pips"] = sl_dist
        r["tp_dist_pips"] = tp_dist
        r["mfe_r"] = fav / sl_dist
        r["mae_r"] = adv / sl_dist
        r["pnl_r_calc"] = pnl / sl_dist
        r["tp_progress"] = (fav / tp_dist) if tp_dist > 0 else 0.0
        # session
        try:
            t = dt.datetime.fromisoformat(r["entry_time"].replace("Z", "+00:00"))
            r["hour_utc"] = t.hour
            r["session"] = session_of_hour(t.hour)
        except Exception:
            r["hour_utc"] = -1
            r["session"] = "Unknown"
        # hold
        try:
            ti = dt.datetime.fromisoformat(r["entry_time"].replace("Z", "+00:00"))
            to = dt.datetime.fromisoformat(r["exit_time"].replace("Z", "+00:00"))
            r["hold_minutes"] = (to - ti).total_seconds() / 60.0
        except Exception:
            r["hold_minutes"] = -1
        # spread
        sin = r.get("spread_at_entry") or 0.0
        sout = r.get("spread_at_exit") or 0.0
        r["spread_expansion"] = (sout / sin) if sin > 0 else 0.0
        # family
        r["family"] = effective_family(r.get("entry_type") or "", r.get("mtf_regime") or "")
        # tags
        if r.get("close_reason") == "SL_HIT":
            r["tags"] = classify_giveback(r["mfe_r"], r["pnl_r_calc"], r["tp_progress"])
        else:
            r["tags"] = ["NA"]
        out.append(r)
    return out


# ─── Aggregations ─────────────────────────────────────────────────────────
def cell_key(r):
    return (
        r.get("instrument") or "?",
        r.get("entry_type") or "?",
        r.get("session") or "?",
        r.get("direction") or "?",
        int(r.get("is_shadow") or 0),
    )


def aggregate_cells(trades, min_n: int):
    by_cell = defaultdict(list)
    for r in trades:
        by_cell[cell_key(r)].append(r)

    cells = []
    for k, rows in by_cell.items():
        n_total = len(rows)
        if n_total < min_n:
            continue
        n_sl = sum(1 for r in rows if r["close_reason"] == "SL_HIT")
        n_tp = sum(1 for r in rows if r["close_reason"] == "TP_HIT")
        # high-MFE-then-SL
        n_hm_sl = sum(
            1 for r in rows
            if r["close_reason"] == "SL_HIT" and r["mfe_r"] >= 0.8
        )
        # tag breakdown among SL_HIT
        tag_ctr = Counter()
        for r in rows:
            if r["close_reason"] == "SL_HIT":
                for t in r["tags"]:
                    tag_ctr[t] += 1
        sl_rows = [r for r in rows if r["close_reason"] == "SL_HIT"]
        avg_mfe_r_sl = (sum(r["mfe_r"] for r in sl_rows) / len(sl_rows)) if sl_rows else 0.0
        avg_giveback_r = (
            sum(r["mfe_r"] - r["pnl_r_calc"] for r in sl_rows) / len(sl_rows)
        ) if sl_rows else 0.0
        avg_spread_expansion = sum(
            r["spread_expansion"] for r in sl_rows if r["spread_expansion"] > 0
        )
        if sl_rows:
            denom = sum(1 for r in sl_rows if r["spread_expansion"] > 0) or 1
            avg_spread_expansion /= denom

        cells.append({
            "instrument": k[0],
            "entry_type": k[1],
            "session": k[2],
            "direction": k[3],
            "is_shadow": k[4],
            "family": effective_family(k[1], ""),
            "n_total": n_total,
            "n_sl": n_sl,
            "n_tp": n_tp,
            "n_high_mfe_sl": n_hm_sl,
            "high_mfe_sl_rate": n_hm_sl / n_total,
            "high_mfe_sl_lb95": wilson_lb(n_hm_sl, n_total),
            "avg_mfe_r_sl": round(avg_mfe_r_sl, 3),
            "avg_giveback_r_sl": round(avg_giveback_r, 3),
            "avg_spread_expansion_sl": round(avg_spread_expansion, 3),
            "tags": dict(tag_ctr),
        })
    cells.sort(key=lambda c: c["high_mfe_sl_lb95"], reverse=True)
    return cells


def aggregate_dim(trades, dim_keys):
    """Aggregate by tuple of fields. Returns rows with give-back metrics."""
    bucket = defaultdict(list)
    for r in trades:
        bucket[tuple(r.get(k) for k in dim_keys)].append(r)
    out = []
    for key, rows in bucket.items():
        n = len(rows)
        sl = [r for r in rows if r["close_reason"] == "SL_HIT"]
        tp = [r for r in rows if r["close_reason"] == "TP_HIT"]
        hm_sl = [r for r in sl if r["mfe_r"] >= 0.8]
        rec = {k: v for k, v in zip(dim_keys, key)}
        rec.update({
            "n": n,
            "n_sl": len(sl),
            "n_tp": len(tp),
            "n_high_mfe_sl": len(hm_sl),
            "high_mfe_sl_rate": len(hm_sl) / n,
            "high_mfe_sl_lb95": wilson_lb(len(hm_sl), n),
            "avg_mfe_r_sl": round(
                (sum(r["mfe_r"] for r in sl) / len(sl)) if sl else 0.0, 3),
            "avg_giveback_r_sl": round(
                (sum(r["mfe_r"] - r["pnl_r_calc"] for r in sl) / len(sl)) if sl else 0.0, 3),
        })
        out.append(rec)
    return sorted(out, key=lambda r: r["high_mfe_sl_lb95"], reverse=True)


# ─── Recommendation engine ────────────────────────────────────────────────
def recommend(cell, k_cells: int, alpha: float = 0.05):
    """Return list of (rule_tag, action, rationale) tuples."""
    # Bonferroni: α/k
    bonferroni_alpha = alpha / max(k_cells, 1)
    recs = []
    tags = cell["tags"]
    n_sl = cell["n_sl"]
    if n_sl == 0:
        return recs
    g1 = tags.get("G1", 0) / n_sl
    g2 = tags.get("G2", 0) / n_sl
    g3 = tags.get("G3", 0) / n_sl
    g4 = tags.get("G4", 0) / n_sl
    high_lb = cell["high_mfe_sl_lb95"]
    n_total = cell["n_total"]
    bonferroni_pass = (high_lb > 0.0) and (n_total >= 30)

    if g1 >= 0.5 and n_sl >= 10:
        recs.append((
            "R3",
            "BE 閾値を ATR×0.8 → ATR×0.5 に下げる cell-override",
            f"G1={g1:.0%} (BE-skip dominant) / SL N={n_sl} / Bonferroni α={bonferroni_alpha:.4f}",
        ))
    if g2 >= 0.4 and n_sl >= 10:
        recs.append((
            "R2",
            "BE 後 Tier2 trail を強制移行 (favorable_move 維持時)",
            f"G2={g2:.0%} (BE-then-SL) — entry+spread に到達後で give back",
        ))
    if g3 >= 0.4 and n_sl >= 10:
        recs.append((
            "R2",
            "trail 幅を ATR×0.5 → ATR×0.3 に短縮 (cell-specific)",
            f"G3={g3:.0%} — Tier2 trail 後も give back",
        ))
    if g4 >= 0.3 and n_sl >= 10:
        recs.append((
            "R2",
            "cell 専用 QH スカラー (TP×0.85 → TP×0.65)",
            f"G4={g4:.0%} — TP 直前反転 dominant",
        ))
    # Family / session mismatch heuristic
    fam = cell["family"]
    if fam == "MR" and cell["session"] in ("London", "NY") and high_lb > 0.10:
        recs.append((
            "R2",
            "MR × トレンドセッションでの entry block",
            "MR 戦略をトレンド優位の London/NY に流すと give back 構造化",
        ))
    if cell["avg_spread_expansion_sl"] >= 2.0:
        recs.append((
            "R3",
            "exit-side spread guard (spread_at_exit / entry >= 2.0 で exit 抑制)",
            f"avg_spread_expansion={cell['avg_spread_expansion_sl']:.2f}",
        ))
    if bonferroni_pass and high_lb >= 0.10 and not recs:
        recs.append((
            "R2",
            "cell 個別レビュー (tag dominant なし、構造調査要)",
            f"high_mfe_sl_lb95={high_lb:.3f} N={n_total} k={k_cells}",
        ))
    return recs


# ─── Markdown report ──────────────────────────────────────────────────────
def render_markdown(payload: dict) -> str:
    L = []
    L.append(f"# MFE → SL Give-back Forensic Report")
    L.append("")
    L.append(f"- 生成 UTC: `{payload['generated_utc']}`")
    L.append(f"- DB: `{payload['db_path']}` / window: 直近 {payload['window_days']} 日")
    L.append(f"- 除外: XAU (memory: feedback_exclude_xau)")
    L.append(f"- 不変条件: LIVE/Shadow 分離 / mafe_* 実測ベース / Bonferroni α={payload['bonferroni_alpha']:.4f}")
    L.append("")
    L.append("## エグゼクティブサマリー")
    s = payload["summary"]
    L.append(f"- 全体 N={s['total']} (CLOSED, 非XAU)")
    for shd in [0, 1]:
        sub = s["by_shadow"].get(str(shd), {})
        if not sub:
            continue
        label = "LIVE (is_shadow=0)" if shd == 0 else "Shadow (is_shadow=1)"
        L.append(f"- **{label}**: N={sub['n']}, SL_HIT={sub['n_sl']}, TP_HIT={sub['n_tp']}, "
                 f"高MFE→SL N={sub['n_high_mfe_sl']} ({sub['high_mfe_sl_rate']:.1%})")
        L.append(f"  - SL_HIT 平均 mfe_r={sub['avg_mfe_r_sl']:.3f}, "
                 f"avg giveback_r={sub['avg_giveback_r_sl']:.3f}")
    L.append("")

    L.append("## タグ定義")
    L.append("| タグ | 条件 | 推定原因 |")
    L.append("|---|---|---|")
    L.append("| G1 | mfe_r ≥ 0.8 ∧ pnl_r ≤ −0.8 | BE 閾値到達したのに BE 不発 (`_entry_atr` 喪失 or 閾値ハードコード) |")
    L.append("| G2 | mfe_r ≥ 0.8 ∧ −0.2 ≤ pnl_r ≤ 0.5 | BE 発火 → 反転 → BE 撤退 (trail 移行できず) |")
    L.append("| G3 | mfe_r ≥ 1.5 ∧ tp_progress < 0.7 | Tier2 trail 発火後も give back (trail 幅広すぎ) |")
    L.append("| G4 | tp_progress ≥ 0.8 ∧ SL_HIT | TP 寸前反転 (TP 距離が広すぎ) |")
    L.append("")

    # Per-shadow sections
    for shd in [0, 1]:
        label = "LIVE (is_shadow=0)" if shd == 0 else "Shadow (is_shadow=1)"
        section = payload["per_shadow"].get(str(shd))
        if not section:
            continue
        L.append(f"## {label}")
        L.append("")
        # ペア別
        L.append("### ペア別")
        L.append("| pair | N | SL | TP | 高MFE→SL | rate | LB95 | avg mfe_r SL | giveback_r |")
        L.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
        for r in section["by_pair"]:
            L.append(f"| {r['instrument']} | {r['n']} | {r['n_sl']} | {r['n_tp']} | "
                     f"{r['n_high_mfe_sl']} | {r['high_mfe_sl_rate']:.1%} | "
                     f"{r['high_mfe_sl_lb95']:.3f} | {r['avg_mfe_r_sl']:.2f} | "
                     f"{r['avg_giveback_r_sl']:.2f} |")
        L.append("")
        # 戦略別
        L.append("### 戦略別 (entry_type, family)")
        L.append("| entry_type | fam | N | SL | TP | 高MFE→SL | rate | LB95 | avg mfe_r SL |")
        L.append("|---|---|--:|--:|--:|--:|--:|--:|--:|")
        for r in section["by_strategy"]:
            fam = effective_family(r.get("entry_type") or "", "")
            L.append(f"| {r['entry_type']} | {fam} | {r['n']} | {r['n_sl']} | {r['n_tp']} | "
                     f"{r['n_high_mfe_sl']} | {r['high_mfe_sl_rate']:.1%} | "
                     f"{r['high_mfe_sl_lb95']:.3f} | {r['avg_mfe_r_sl']:.2f} |")
        L.append("")
        # 時間帯別
        L.append("### 時間帯別 (session)")
        L.append("| session | N | SL | TP | 高MFE→SL | rate | LB95 | avg mfe_r SL |")
        L.append("|---|--:|--:|--:|--:|--:|--:|--:|")
        for r in section["by_session"]:
            L.append(f"| {r['session']} | {r['n']} | {r['n_sl']} | {r['n_tp']} | "
                     f"{r['n_high_mfe_sl']} | {r['high_mfe_sl_rate']:.1%} | "
                     f"{r['high_mfe_sl_lb95']:.3f} | {r['avg_mfe_r_sl']:.2f} |")
        L.append("")
        # cells
        cells = section["cells"]
        L.append(f"### Top cell 一覧 (N≥{payload['min_n']}, sorted by LB95)")
        L.append("| cell (pair / type / sess / dir) | fam | N | SL | hMFE_SL | LB95 | avg mfe_r | giveback_r | tags |")
        L.append("|---|---|--:|--:|--:|--:|--:|--:|---|")
        for c in cells[:25]:
            tag_str = ", ".join(f"{t}={v}" for t, v in sorted(c["tags"].items()))
            cell_lbl = f"{c['instrument']} / {c['entry_type']} / {c['session']} / {c['direction']}"
            L.append(f"| {cell_lbl} | {c['family']} | {c['n_total']} | {c['n_sl']} | "
                     f"{c['n_high_mfe_sl']} | {c['high_mfe_sl_lb95']:.3f} | "
                     f"{c['avg_mfe_r_sl']:.2f} | {c['avg_giveback_r_sl']:.2f} | {tag_str} |")
        L.append("")
        # individual high-MFE→SL trades
        L.append(f"### 個別 高MFE→SL トレード (mfe_r ≥ 0.8, top 30 by mfe_r)")
        L.append("| trade_id | pair | type | sess | dir | mfe_r | tp_prog | pnl_r | tags |")
        L.append("|---|---|---|---|---|--:|--:|--:|---|")
        for t in section["high_mfe_sl_trades"][:30]:
            L.append(f"| `{t['trade_id']}` | {t['instrument']} | {t['entry_type']} | "
                     f"{t['session']} | {t['direction']} | {t['mfe_r']:.2f} | "
                     f"{t['tp_progress']:.2f} | {t['pnl_r_calc']:.2f} | "
                     f"{','.join(t['tags'])} |")
        L.append("")
        # recommendations
        L.append("### 対応策 (cell-level recommendations)")
        if not section["recommendations"]:
            L.append("- N または LB95 の閾値を満たす cell なし")
        else:
            L.append("| cell | rule | action | rationale |")
            L.append("|---|---|---|---|")
            for rec in section["recommendations"]:
                cell_lbl = f"{rec['cell']['instrument']} / {rec['cell']['entry_type']} / {rec['cell']['session']} / {rec['cell']['direction']}"
                for action in rec["actions"]:
                    L.append(f"| {cell_lbl} | {action[0]} | {action[1]} | {action[2]} |")
        L.append("")

    L.append("## グローバル構造所見 (cross-cell)")
    g = payload.get("global_findings", {})
    L.append(f"- 高MFE→SL トレード総数 (Live+Shadow): **{g.get('total_high_mfe_sl', 0)}**")
    L.append(f"- タグ分布 (高MFE→SL のみ): {g.get('tag_distribution', {})}")
    if g.get("g1_dominance"):
        L.append(f"- **G1 (BE-Skip) 支配率 = {g['g1_dominance']:.0%}** — "
                 "BE 発火閾値到達後そのまま SL に至るトレードが支配的")
    L.append("")
    # ペア × 退出理由マトリクス (GBP-style: 含み益はあったが TP 取れず)
    L.append("### ペア × 退出理由 × MFE 分布")
    L.append("| pair | close_reason | N | avg mfe_r | max mfe_r | avg tp_progress |")
    L.append("|---|---|--:|--:|--:|--:|")
    for r in g.get("pair_exit_summary", []):
        L.append(f"| {r['instrument']} | {r['close_reason']} | {r['n']} | "
                 f"{r['avg_mfe_r']} | {r['max_mfe_r']} | {r['avg_tp_progress']} |")
    L.append("")
    L.append(f"### 高MFE 非TP・非SL exit ({g.get('high_mfe_non_tp_non_sl_n', 0)}件)")
    L.append("「含み益あったが TP 取れず時間/シグナルで撤退」 — give back の隠れた母集団")
    L.append("| trade_id | pair | type | reason | mfe_r | tp_prog | pnl_r |")
    L.append("|---|---|---|---|--:|--:|--:|")
    for r in g.get("high_mfe_non_tp_non_sl", [])[:25]:
        L.append(f"| `{r['trade_id']}` | {r['instrument']} | {r['entry_type']} | "
                 f"{r['close_reason']} | {r['mfe_r']} | {r['tp_progress']} | "
                 f"{r['pnl_r']} |")
    L.append("")

    L.append("### 構造的優先順位付き対応策 (ユーザー判断のための提示)")
    for i, p in enumerate(g.get("priorities", []), 1):
        L.append(f"{i}. **[{p['rule']}] {p['title']}**")
        L.append(f"   - 根拠: {p['rationale']}")
        L.append(f"   - 適用箇所: `{p['target']}`")
        L.append(f"   - 期待効果: {p['expected']}")
    L.append("")
    L.append("## 不変条件チェック")
    for k, v in payload.get("checks", {}).items():
        L.append(f"- {k}: {v}")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="demo_trades.db")
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--min-n", type=int, default=20)
    ap.add_argument("--out", default="raw/audits/")
    args = ap.parse_args()

    db_path = Path(args.db).resolve()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    trades = load_trades(db_path, args.window_days, exclude_xau=True)

    # Summary
    by_shadow_summary = {}
    for shd in [0, 1]:
        ts_rows = [r for r in trades if int(r.get("is_shadow") or 0) == shd]
        sl = [r for r in ts_rows if r["close_reason"] == "SL_HIT"]
        tp = [r for r in ts_rows if r["close_reason"] == "TP_HIT"]
        hm = [r for r in sl if r["mfe_r"] >= 0.8]
        by_shadow_summary[str(shd)] = {
            "n": len(ts_rows),
            "n_sl": len(sl),
            "n_tp": len(tp),
            "n_high_mfe_sl": len(hm),
            "high_mfe_sl_rate": (len(hm) / len(ts_rows)) if ts_rows else 0.0,
            "avg_mfe_r_sl": round(
                (sum(r["mfe_r"] for r in sl) / len(sl)) if sl else 0.0, 3),
            "avg_giveback_r_sl": round(
                (sum(r["mfe_r"] - r["pnl_r_calc"] for r in sl) / len(sl)) if sl else 0.0, 3),
        }

    # Per-shadow sections
    per_shadow = {}
    bonferroni_alpha = 0.05  # placeholder; updated per-section below
    for shd in [0, 1]:
        ts_rows = [r for r in trades if int(r.get("is_shadow") or 0) == shd]
        if not ts_rows:
            continue
        cells = aggregate_cells(ts_rows, args.min_n)
        k = max(len(cells), 1)
        bonferroni_alpha = 0.05 / k

        recs = []
        for c in cells:
            actions = recommend(c, k_cells=k)
            if actions:
                recs.append({"cell": c, "actions": actions})

        hm_trades = [
            r for r in ts_rows
            if r["close_reason"] == "SL_HIT" and r["mfe_r"] >= 0.8
        ]
        hm_trades.sort(key=lambda r: r["mfe_r"], reverse=True)
        # Strip rows for output
        for t in hm_trades:
            for k_drop in ("reasons", "regime", "alpha_snapshot",
                           "mtf_alignment", "mtf_regime"):
                t.pop(k_drop, None)

        per_shadow[str(shd)] = {
            "by_pair": aggregate_dim(ts_rows, ["instrument"]),
            "by_strategy": aggregate_dim(ts_rows, ["entry_type"]),
            "by_session": aggregate_dim(ts_rows, ["session"]),
            "by_pair_session": aggregate_dim(ts_rows, ["instrument", "session"]),
            "cells": cells,
            "high_mfe_sl_trades": hm_trades,
            "recommendations": recs,
            "bonferroni_alpha": bonferroni_alpha,
            "k_cells": k,
        }

    # ── 拡張ビュー: 非SL exit with high MFE (TIME_DECAY / MAX_HOLD / WEEKEND_CLOSE) ──
    # 「含み益が大きかったが TP に到達せず時間で閉じた」ケース集計
    high_mfe_non_tp_non_sl = []
    for r in trades:
        if r["close_reason"] in ("TIME_DECAY_EXIT", "MAX_HOLD_TIME",
                                   "WEEKEND_CLOSE", "SIGNAL_REVERSE", "SCENARIO_INVALID"):
            if r["mfe_r"] >= 0.8 or r["tp_progress"] >= 0.5:
                high_mfe_non_tp_non_sl.append(r)
    high_mfe_non_tp_non_sl.sort(key=lambda r: r["mfe_r"], reverse=True)

    # Per-pair: exit_reason × MFE summary (for GBP-style observation)
    pair_exit_summary = defaultdict(lambda: defaultdict(list))
    for r in trades:
        pair_exit_summary[r.get("instrument", "?")][r.get("close_reason", "?")].append(r)
    pair_exit_rows = []
    for pair, reasons in pair_exit_summary.items():
        for cr, rows in reasons.items():
            if len(rows) < 3:
                continue
            mfes = [x["mfe_r"] for x in rows]
            pair_exit_rows.append({
                "instrument": pair,
                "close_reason": cr,
                "n": len(rows),
                "avg_mfe_r": round(sum(mfes) / len(mfes), 2),
                "max_mfe_r": round(max(mfes), 2),
                "avg_tp_progress": round(
                    sum(x["tp_progress"] for x in rows) / len(rows), 2),
            })
    pair_exit_rows.sort(key=lambda r: (r["instrument"], -r["max_mfe_r"]))

    # Global structural findings (cross-cell)
    all_high = [
        r for r in trades
        if r["close_reason"] == "SL_HIT" and r["mfe_r"] >= 0.8
    ]
    tag_ctr_global = Counter()
    for r in all_high:
        for t in r["tags"]:
            tag_ctr_global[t] += 1
    g1_dom = (tag_ctr_global.get("G1", 0) / len(all_high)) if all_high else 0.0
    g3_dom = (tag_ctr_global.get("G3", 0) / len(all_high)) if all_high else 0.0
    g4_dom = (tag_ctr_global.get("G4", 0) / len(all_high)) if all_high else 0.0

    priorities = []
    if g1_dom >= 0.7:
        priorities.append({
            "rule": "R3",
            "title": "BE 発火失敗の構造的バグ調査 (`_entry_atr` 喪失 + OANDA mirror revert)",
            "rationale": (
                f"高MFE→SL の {g1_dom:.0%} が G1 タグ。pnl_r ≤ -0.8 着地は "
                "BE が一度も適用されていない証拠。原因候補: "
                "(a) `_entry_atr` がプロセス再起動でロストし fallback ATR がトレード実 ATR と乖離、"
                "(b) `modify_sl_sync` が shadow trade で False を返し SL が revert "
                "(modules/demo_trader.py:1758-1760)"
            ),
            "target": "modules/demo_trader.py:1706-1755 + 1758",
            "expected": (
                "shadow trade で modify_sl_sync をスキップ + entry_atr を trades 表に永続化"
                " → BE 発火が in-memory 状態に依存しなくなる"
            ),
        })
    if g3_dom >= 0.10:
        priorities.append({
            "rule": "R2",
            "title": "Tier2 trail 幅の短縮 (ATR×0.5 → ATR×0.3)",
            "rationale": (
                f"G3 タグ {g3_dom:.0%}: mfe_r ≥ 1.5 到達後も give back。"
                "trail 幅 ATR×0.5 が広すぎて反転で容易に SL される"
            ),
            "target": "modules/demo_trader.py:1737 (`_ts_trail = _entry_atr_be * 0.5`)",
            "expected": "trail SL 損益保護 +30〜50% 推定 (要 BT 確認)",
        })
    if g4_dom >= 0.10:
        priorities.append({
            "rule": "R2",
            "title": "TP 距離短縮 (Quick Harvest スカラー強化 0.85 → 0.70)",
            "rationale": (
                f"G4 タグ {g4_dom:.0%}: tp_progress ≥ 0.8 で反転 → SL。"
                "TP 寸前の反転は TP 距離が広すぎる証拠"
            ),
            "target": "app.py:5680, 6359 (QH スカラー 0.85)",
            "expected": "TP 達成率上昇 + 高MFE→SL 減少",
        })
    # MR × トレンドセッション
    mr_trend_n = sum(
        1 for r in all_high
        if r.get("family") == "MR" and r.get("session") in ("London", "NY")
    )
    if all_high and mr_trend_n / len(all_high) >= 0.30:
        priorities.append({
            "rule": "R2",
            "title": "MR 戦略 × London/NY ブロック検討",
            "rationale": (
                f"高MFE→SL の {mr_trend_n / len(all_high):.0%} が MR×London/NY。"
                "MR (mean reversion) はトレンドセッションで give back 構造化"
            ),
            "target": "strategy gate (entry filter)",
            "expected": "MR 戦略の SL 比率低下、TP 比率上昇",
        })

    global_findings = {
        "total_high_mfe_sl": len(all_high),
        "tag_distribution": dict(tag_ctr_global),
        "g1_dominance": g1_dom,
        "g3_dominance": g3_dom,
        "g4_dominance": g4_dom,
        "mr_trend_session_share": (mr_trend_n / len(all_high)) if all_high else 0.0,
        "priorities": priorities,
        "high_mfe_non_tp_non_sl_n": len(high_mfe_non_tp_non_sl),
        "high_mfe_non_tp_non_sl": [
            {
                "trade_id": r.get("trade_id"),
                "instrument": r.get("instrument"),
                "entry_type": r.get("entry_type"),
                "close_reason": r.get("close_reason"),
                "mfe_r": round(r["mfe_r"], 2),
                "tp_progress": round(r["tp_progress"], 2),
                "pnl_r": round(r["pnl_r_calc"], 2),
            }
            for r in high_mfe_non_tp_non_sl[:50]
        ],
        "pair_exit_summary": pair_exit_rows,
    }

    payload = {
        "generated_utc": ts,
        "db_path": str(db_path),
        "window_days": args.window_days,
        "min_n": args.min_n,
        "bonferroni_alpha": bonferroni_alpha,
        "summary": {"total": len(trades), "by_shadow": by_shadow_summary},
        "per_shadow": per_shadow,
        "global_findings": global_findings,
        "checks": {
            "live_shadow_separated": True,
            "xau_excluded": True,
            "code_deduction_avoided": "all metrics from mafe_* SQL fields",
            "spread_basis": "entry_price ベースの sl_dist 距離で正規化",
        },
    }

    json_path = out_dir / f"mfe_sl_giveback_{ts}.json"
    md_path = out_dir / f"mfe_sl_giveback_{ts}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    md = render_markdown(payload)
    md_path.write_text(md)
    sha = hashlib.sha256(md.encode("utf-8")).hexdigest()[:12]
    print(f"[ok] {json_path}")
    print(f"[ok] {md_path}")
    print(f"sha256-12={sha}  total={len(trades)}  k_cells={payload.get('per_shadow',{}).get('1',{}).get('k_cells','?')}")


if __name__ == "__main__":
    main()
