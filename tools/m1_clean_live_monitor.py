#!/usr/bin/env python3
"""M1 KPI readout — roadmap v2.3 の最重要 KPI「clean live 30d PnL > 0」の読み手。

背景 (2026-09-04)
-----------------
roadmap v2.3 は M1 を「clean live 30d rolling PnL > 0」と定義しているが、
**その値を再計算する主体がプロジェクトに存在しなかった**。roadmap の M1 行は
2026-07-06 の手動実測 (N=92 / −242.6p) のまま 60 日間凍結され、その間に
KPI は符号を反転していた (2026-08-31 前後)。「収集済み ≠ 監視済み」型の欠落
(cf. lesson-mof-url-guess-write-only / lesson-live-fill-estimand-shadow-conflation)。

本モジュールが名乗る estimand
-----------------------------
    「**決済済み LIVE 約定** の直近 30 日 `pnl_pips` 合計」

    LIVE   = ``oanda_trade_id`` が非空 (``is_shadow=0`` 単独では判定しない —
             FLAG_DRIFT 行が混入する。MEMORY feedback_live_vs_shadow_strict_separation)
    dedup  = ``dedup_violation != 1``
    XAU    = ``instrument != 'XAU_USD'`` (摩擦 217.5p で桁が違うため roadmap 定義上除外)
    決済済 = ``status == 'CLOSED'`` かつ ``pnl_pips is not None``
    窓     = ``created_at`` が anchor から遡って 30 日 (実時間。市場オープン換算はしない
             — M1 は「暦月の符号」を問う KPI であり、暦時間が正しい時計)

    ⚠️ **pip 合計であって口座損益ではない。** セル毎に lot が異なり
    (defensive 0.2x / T5 JPY cap 0.5x / ladder L1)、pip→JPY 換算はペア依存。
    M1 の定義自体が pip ベースなのでここでも pip で報告するが、
    「+19.8p だから儲かっている」とは読めない。

verdict の 3 状態
-----------------
本モジュールは M1 の **定義を変えない** (定義変更は user 決裁事項)。
生の符号に加えて「その符号が雑音と区別できるか」を併記するだけである:

    NO_DATA          N == 0
    NOT_MET          sum <= 0
    MET_UNDERPOWERED sum > 0 だが bootstrap P(sum<=0) >= 0.05 = 符号が未解決
    MET              sum > 0 かつ bootstrap P(sum<=0) < 0.05

さらに **符号反転の帰属** を必ず出す。rolling 窓の符号は「新しい勝ちが入った」
だけでなく「古い負けが窓から抜けた」でも反転する。後者は成果ではないので
``MECHANICAL_FLIP`` として明示する (2026-09-04 の実例: 新規約定ゼロのまま
2026-07-31 の −123.2p が窓外へ抜けただけで符号が反転した)。

強定義 readout (--strong、2026-09-10 追加 — meta-audit 2026-09-07 §4.2 R4(a) 修復)
--------------------------------------------------------------------------
弱定義 (30d rolling PnL 符号) は分母が縮むほど満たしやすい縮退 KPI
([[m1-kpi-readout-and-mechanical-flip-2026-09-04]] §6)。--strong は弱定義
readout を**残したまま**、承認済み文書 2 系統の強定義を**両方**計算して併記する:

    M1_STRONG_CELL  (rederivation §4 系 / 本修復の主定義):
        セル (entry_type×instrument×direction) 単位で
        clean live 累積 (cutoff 2026-04-08 以降) N ≥ 30
        ∧ 平均 net EV ≥ +1.0 p/t ∧ Wilson 95% 下限 (WR) > 0
        → 該当セル ≥ 1 で達成
    M1_STRONG_BOOK  (m1-kpi-readout §8 案):
        book 全体で 30d sum > 0 ∧ bootstrap P(sum≤0) < 0.05 (= verdict MET)
    M1_STRONG_FULL  (rederivation §4 全文):
        M1_STRONG_CELL ∧ book 全体の統計確認 (「Wilson 下限 > 0 相当」の
        実装として bootstrap MET を使用)

    ⚠️ 文書間矛盾は隠さず両方出す (裁定は user):
    (i) §8 は book bootstrap 資格、rederivation §4 はセル単位資格 — 資格の
        母集団が違う。(ii) rederivation §4 の literal は「正EVセル」(EV>0)
        であり EV≥+1.0p/t とは閾値が違う → 両カウントを併記。
    (iii) WR の Wilson 下限 > 0 は「勝ち 1 件以上」と同値で、EV>0 が必ず
        それを含意する = win-rate 解釈では非拘束条件。参考として repo の
        R1 gate 慣例 (wilson_lo ≥ 0.50) でのカウントも併記する。

M3 の二定義分離 (--strong に含む — meta-audit R4(b)):
    M3a (throughput / roadmap v2.3 KPI 表): clean live 累積 N≥30 のセル数 / 3。
        ETA は直近 30d の N 蓄積レートから線形外挿。
    M3b (return / rederivation §4): 摩擦調整後 (= live 実現 net pips) 正EV
        セルの直近 30d 寄与合計。一次単位は pips。JPY/%NAV は
        units=1000 仮定 + quote→JPY 概算レートによる**推定値** (ラベル明示)。
        目標は +0.5%/月 (2026-09-10 user 指示の分母) を primary とし、
        rederivation §4 の M3 return 版 +2〜3%/月 を併記 (定義併存を明示)。
        線形 N 外挿では月次寄与レートは一定 → ETA は「達成中」か
        「現行ペースで到達不能」の二値になる (これは限界でなく含意)。

使用:
    python3 tools/m1_clean_live_monitor.py
    python3 tools/m1_clean_live_monitor.py --json
    python3 tools/m1_clean_live_monitor.py --days 30 --lookback 7
    python3 tools/m1_clean_live_monitor.py --strong [--nav 278905]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import requests

DEFAULT_API = "https://fx-ai-trader.onrender.com"

#: roadmap v2.3 KPI 表の M1 窓幅 (日)。
WINDOW_DAYS = 30
#: 符号反転の帰属を取るための比較アンカー (日前)。
LOOKBACK_DAYS = 7
#: bootstrap で「符号が解決した」と呼ぶ上限。慣例値 0.05 (curve-fit ではない)。
SIGN_ALPHA = 0.05
#: bootstrap 反復数。
BOOTSTRAP_N = 20000
#: 再現性のための固定 seed (同じ入力なら同じ CI が出ること = テストで pin)。
BOOTSTRAP_SEED = 20260904

#: roadmap 定義で除外される instrument。
EXCLUDED_INSTRUMENTS = frozenset({"XAU_USD"})

# ── 強定義 (--strong) 定数 — 2026-09-10 R4(a)/(b) 修復 ──────────────────
#: clean データ cutoff (FIDELITY_CUTOFF)。clean_n_tracker.py / api_demo_stats と同一。
CLEAN_CUTOFF = "2026-04-08"
#: セル資格の最小 clean live N (rederivation §4 / roadmap M3 と同値)。
STRONG_MIN_N = 30
#: セル資格の最小 平均 net EV (p/t)。2026-09-10 user 指示の閾値。
#: rederivation §4 literal は「正EVセル」(EV>0) — 両カウントを併記する。
STRONG_MIN_EV_PIPS = 1.0
#: Wilson 95% (two-sided z)。repo の _wilson_lower 慣例と同一。
WILSON_Z95 = 1.959963984540054
#: repo R1 gate 慣例の参考閾値 (bb_2sigma_fade G2 等)。
WILSON_GATE_REF = 0.50
#: M3a: clean live N≥30 セルの目標本数 (roadmap v2.3 KPI 表)。
M3A_TARGET_CELLS = 3
#: M3b: 月次寄与の primary 目標 (%/月、2026-09-10 user 指示の分母)。
M3B_TARGET_PCT = 0.5
#: rederivation §4 の M3 return 版レンジ (%/月) — 定義併存として併記。
M3B_REDERIV_BAND = (2.0, 3.0)
#: JPY 推定レイヤの units 仮定 (07-07 live fill #549086 で観測された実効ロット)。
EFFECTIVE_UNITS_ASSUMPTION = 1000.0
#: quote→JPY 概算レート (JPY quote は正確に units×0.01 なので不使用)。
#: **推定レイヤ専用の近似値** — 一次単位は常に pips。テストでは pin しない
#: (lesson: 時変の代理を pin するな)。
QUOTE_JPY_APPROX = {
    "USD": 160.0, "EUR": 175.0, "GBP": 205.0, "CHF": 185.0,
    "CAD": 115.0, "AUD": 105.0, "NZD": 95.0,
}

_TS_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")

# ── broker 両基準 (--strong、D11 2026-10-19 rule:R3) ─────────────────────
#: OANDA v20 trades 一覧の 1 ページ上限 (count ≤500)。
BROKER_PAGE_SIZE = 500
#: beforeID 遡行の安全上限 (clean live 614 行 ≈ 2 ページ、無限ループ防止)。
BROKER_MAX_PAGES = 20
#: broker 基準の口座通貨。Claude_auto_trade_KG は JPY 口座 — realizedPL は JPY。
BROKER_ACCOUNT_CCY = "JPY"


def parse_ts(value: Any) -> datetime | None:
    """``created_at`` を naive UTC datetime に。壊れていれば ``None``。"""
    if not value:
        return None
    text = str(value).strip().replace("Z", "")
    if "+" in text[10:]:
        text = text[: text.index("+", 10)]
    text = text.split(".")[0]
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def is_clean_live(row: dict[str, Any]) -> bool:
    """roadmap v2.3 の "clean live" estimand。全条件を明示的に評価する。

    現時点で一部条件は本番データ上 no-op だが、no-op だから省くと
    estimand が暗黙になり、後から静かに壊れる。条件は残して test で pin する。
    """
    if not str(row.get("oanda_trade_id") or "").strip():
        return False
    if (row.get("instrument") or "") in EXCLUDED_INSTRUMENTS:
        return False
    if row.get("dedup_violation") == 1:
        return False
    if (row.get("status") or "") != "CLOSED":
        return False
    if row.get("pnl_pips") is None:
        return False
    return True


def window_rows(
    rows: Iterable[dict[str, Any]],
    anchor: datetime,
    days: int = WINDOW_DAYS,
) -> list[dict[str, Any]]:
    """anchor から遡って ``days`` 日の clean live 行 (created_at 昇順)。"""
    span = timedelta(days=days)
    out = []
    for row in rows:
        if not is_clean_live(row):
            continue
        ts = parse_ts(row.get("created_at"))
        if ts is None:
            continue
        delta = anchor - ts
        if timedelta(0) <= delta < span:
            out.append((ts, row))
    out.sort(key=lambda pair: pair[0])
    return [row for _, row in out]


def _row_key(row: dict[str, Any]) -> str:
    return str(row.get("trade_id") or row.get("id") or id(row))


def bootstrap_sum(pnls: list[float], iterations: int = BOOTSTRAP_N) -> dict[str, float]:
    """30d 合計の bootstrap 分布。``p_le_zero`` = 符号が雑音と区別できない度合い。"""
    n = len(pnls)
    if n == 0:
        return {"ci_lo": 0.0, "ci_hi": 0.0, "p_le_zero": 1.0}
    rng = random.Random(BOOTSTRAP_SEED)
    sums = [sum(rng.choice(pnls) for _ in range(n)) for _ in range(iterations)]
    sums.sort()
    lo = sums[int(0.025 * iterations)]
    hi = sums[min(int(0.975 * iterations), iterations - 1)]
    p_le = sum(1 for s in sums if s <= 0) / iterations
    return {"ci_lo": lo, "ci_hi": hi, "p_le_zero": p_le}


def verdict_for(total: float, n: int, p_le_zero: float) -> str:
    if n == 0:
        return "NO_DATA"
    if total <= 0:
        return "NOT_MET"
    if p_le_zero >= SIGN_ALPHA:
        return "MET_UNDERPOWERED"
    return "MET"


def attribute_flip(
    rows: Iterable[dict[str, Any]],
    anchor: datetime,
    days: int = WINDOW_DAYS,
    lookback: int = LOOKBACK_DAYS,
) -> dict[str, Any]:
    """符号変化を「新規に入った約定」と「窓から抜けた約定」へ分解する。

    rolling 窓の符号は成果なしでも反転しうる。分解しないと
    「古い負けが抜けただけ」を「黒字転換」と誤読する。
    """
    rows = list(rows)
    prev_anchor = anchor - timedelta(days=lookback)
    now_w = window_rows(rows, anchor, days)
    prev_w = window_rows(rows, prev_anchor, days)
    now_keys = {_row_key(r) for r in now_w}
    prev_keys = {_row_key(r) for r in prev_w}
    added = [r for r in now_w if _row_key(r) not in prev_keys]
    aged_out = [r for r in prev_w if _row_key(r) not in now_keys]
    sum_now = sum(float(r["pnl_pips"]) for r in now_w)
    sum_prev = sum(float(r["pnl_pips"]) for r in prev_w)
    sum_added = sum(float(r["pnl_pips"]) for r in added)
    sum_aged = sum(float(r["pnl_pips"]) for r in aged_out)
    sign_now = 1 if sum_now > 0 else (0 if sum_now == 0 else -1)
    sign_prev = 1 if sum_prev > 0 else (0 if sum_prev == 0 else -1)
    flipped = bool(now_w) and bool(prev_w) and sign_now != sign_prev
    mechanical = flipped and abs(sum_aged) > abs(sum_added)
    return {
        "lookback_days": lookback,
        "prev_anchor": prev_anchor.isoformat(),
        "n_prev": len(prev_w),
        "sum_prev": round(sum_prev, 2),
        "n_added": len(added),
        "sum_added": round(sum_added, 2),
        "n_aged_out": len(aged_out),
        "sum_aged_out": round(sum_aged, 2),
        "delta": round(sum_added - sum_aged, 2),
        "sign_flipped": flipped,
        "mechanical_flip": mechanical,
        "aged_out_detail": [
            {
                "created_at": r.get("created_at"),
                "entry_type": r.get("entry_type"),
                "instrument": r.get("instrument"),
                "pnl_pips": r.get("pnl_pips"),
            }
            for r in sorted(aged_out, key=lambda x: abs(float(x["pnl_pips"])), reverse=True)[:5]
        ],
    }


def leave_one_out_fragility(pnls: list[float]) -> dict[str, Any]:
    """1 件抜くだけで符号が消える約定が何件あるか (正の窓でのみ意味を持つ)。"""
    total = sum(pnls)
    if not pnls or total <= 0:
        return {"n_sign_flipping_trades": 0, "worst_removed": None}
    flippers = [x for x in pnls if total - x <= 0]
    return {
        "n_sign_flipping_trades": len(flippers),
        "worst_removed": round(max(flippers), 2) if flippers else None,
    }


def summarize(
    rows: Iterable[dict[str, Any]],
    anchor: datetime,
    days: int = WINDOW_DAYS,
    lookback: int = LOOKBACK_DAYS,
) -> dict[str, Any]:
    rows = list(rows)
    window = window_rows(rows, anchor, days)
    pnls = [float(r["pnl_pips"]) for r in window]
    total = sum(pnls)
    n = len(pnls)
    wins = sum(1 for x in pnls if x > 0)
    boot = bootstrap_sum(pnls)
    cells: dict[str, dict[str, Any]] = {}
    for r in window:
        key = f"{r.get('entry_type')}×{r.get('instrument')}×{r.get('direction')}"
        c = cells.setdefault(key, {"n": 0, "sum": 0.0})
        c["n"] += 1
        c["sum"] = round(c["sum"] + float(r["pnl_pips"]), 2)
    return {
        "anchor": anchor.isoformat(),
        "window_days": days,
        "estimand": (
            "決済済み LIVE 約定 (oanda_trade_id 非空, dedup_violation!=1, XAU除外, "
            "status=CLOSED) の直近 30 日 pnl_pips 合計"
        ),
        "n": n,
        "sum_pips": round(total, 2),
        "ev_pips": round(total / n, 3) if n else 0.0,
        "win_rate": round(wins / n, 4) if n else 0.0,
        "ci95_lo": round(boot["ci_lo"], 2),
        "ci95_hi": round(boot["ci_hi"], 2),
        "p_le_zero": round(boot["p_le_zero"], 4),
        "verdict": verdict_for(total, n, boot["p_le_zero"]),
        "fragility": leave_one_out_fragility(pnls),
        "flip_attribution": attribute_flip(rows, anchor, days, lookback),
        "cells": dict(sorted(cells.items(), key=lambda kv: -kv[1]["n"])),
    }


# ==========================================================================
# 強定義 (M1_STRONG) + M3 二定義分離 — 2026-09-10 R4(a)/(b)
# ==========================================================================

def wilson_lower(wins: int, n: int, z: float = WILSON_Z95) -> float:
    """WR (勝ち割合) の Wilson score interval 95% 下限。repo 慣例と同式。

    n=0 → 0.0。wins=0 → 正確に 0.0 (「> 0」境界はここで跨ぐ)。
    """
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (center - margin) / denom)


def cumulative_cell_stats(
    rows: Iterable[dict[str, Any]],
    anchor: datetime,
    days: int = WINDOW_DAYS,
    cutoff: str = CLEAN_CUTOFF,
) -> list[dict[str, Any]]:
    """セル (entry_type×instrument×direction) 別の clean live 累積統計。

    母集団 = ``is_clean_live`` ∧ ``cutoff <= created_at <= anchor``。
    セル資格の N は**累積** (rederivation §4 / roadmap M3 の「clean live N≥30」
    は蓄積量であって rolling ではない)。直近 ``days`` 日の N/pips は
    ETA 外挿と M3b の月次寄与に使う。
    """
    cutoff_dt = datetime.strptime(cutoff, "%Y-%m-%d")
    span = timedelta(days=days)
    cells: dict[str, dict[str, Any]] = {}
    for r in rows:
        if not is_clean_live(r):
            continue
        ts = parse_ts(r.get("created_at"))
        if ts is None or ts < cutoff_dt or ts > anchor:
            continue
        key = f"{r.get('entry_type')}×{r.get('instrument')}×{r.get('direction')}"
        c = cells.setdefault(key, {
            "cell": key,
            "instrument": r.get("instrument"),
            "n": 0, "sum": 0.0, "wins": 0,
            "n_recent": 0, "sum_recent": 0.0,
        })
        pnl = float(r["pnl_pips"])
        c["n"] += 1
        c["sum"] += pnl
        if pnl > 0:
            c["wins"] += 1
        if anchor - ts < span:
            c["n_recent"] += 1
            c["sum_recent"] += pnl
    out = []
    for c in cells.values():
        n = c["n"]
        c["sum"] = round(c["sum"], 2)
        c["sum_recent"] = round(c["sum_recent"], 2)
        c["ev"] = round(c["sum"] / n, 3) if n else 0.0
        c["wr"] = round(c["wins"] / n, 4) if n else 0.0
        c["wilson_lo"] = round(wilson_lower(c["wins"], n), 4)
        out.append(c)
    out.sort(key=lambda c: (-c["n"], c["cell"]))
    return out


def _cell_is_strong(c: dict[str, Any], min_ev: float = STRONG_MIN_EV_PIPS) -> bool:
    """M1_STRONG_CELL 資格: N≥30 ∧ EV≥min_ev ∧ Wilson95 下限 > 0。"""
    return (
        c["n"] >= STRONG_MIN_N
        and c["ev"] >= min_ev
        and c["wilson_lo"] > 0.0
    )


def strong_summary(
    rows: Iterable[dict[str, Any]],
    anchor: datetime,
    days: int = WINDOW_DAYS,
    weak: dict[str, Any] | None = None,
    broker: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """M1 強定義 readout。承認済み 2 文書の定義を**両方**計算し矛盾を明示する。

    ``broker`` = {"map": {oanda_trade_id: trade}, "status": {...}} (D11 両基準併記)。
    None なら broker 列は ``skipped``、status.ok=False なら ``unavailable``。
    """
    rows = list(rows)
    weak = weak or summarize(rows, anchor, days)
    cells = cumulative_cell_stats(rows, anchor, days)
    strong_cells = [c for c in cells if _cell_is_strong(c)]
    # rederivation §4 literal: 「正EVセル」= EV > 0 (閾値 +1.0 ではない)
    literal_cells = [c for c in cells if c["n"] >= STRONG_MIN_N and c["ev"] > 0
                     and c["wilson_lo"] > 0.0]
    # 参考: repo R1 gate 慣例 (wilson_lo ≥ 0.50) を課した保守カウント
    gate_ref_cells = [c for c in strong_cells if c["wilson_lo"] >= WILSON_GATE_REF]
    book_met = weak["verdict"] == "MET"
    cell_met = len(strong_cells) >= 1
    # ── D11 両基準併記 (2026-10-19) ──
    reg_literal_demo = [c for c in cells if _pred_reg_literal(c["n"], c["sum"])]
    if broker is None:
        broker_basis: dict[str, Any] = {"status": "skipped",
                                        "reason": "broker fetch not requested (--no-broker)"}
    else:
        bstatus = broker.get("status") or {}
        cells_b = cumulative_cell_stats_broker(rows, anchor, broker.get("map") or {}, days)
        table = basis_table(cells, cells_b)
        broker_basis = {
            "status": "ok" if bstatus.get("ok") else "unavailable",
            "reason": None if bstatus.get("ok") else bstatus.get("reason", "unknown"),
            "fetch": {k: bstatus.get(k) for k in ("pages", "covered", "missing", "oldest_id_seen")},
            "table": table,
        }
    return {
        "anchor": anchor.isoformat(),
        "n_cells_reg_literal_demo": len(reg_literal_demo),
        "broker_basis": broker_basis,
        "estimand_cell": (
            f"セル (entry_type×instrument×direction) 単位 clean live 累積 "
            f"(cutoff {CLEAN_CUTOFF}〜anchor): N≥{STRONG_MIN_N} ∧ "
            f"平均 net EV≥+{STRONG_MIN_EV_PIPS}p/t ∧ Wilson95下限(WR)>0"
        ),
        "n_cells_total": len(cells),
        "n_cells_strong": len(strong_cells),
        "m1_strong_cell_met": cell_met,
        "n_cells_rederivation_literal": len(literal_cells),
        "n_cells_wilson_gate_ref": len(gate_ref_cells),
        "m1_strong_book_met": book_met,
        "m1_strong_full_met": cell_met and book_met,
        "book_verdict": weak["verdict"],
        "qualifying_cells": [
            {k: c[k] for k in ("cell", "n", "sum", "ev", "wr", "wilson_lo")}
            for c in strong_cells
        ],
        "top_cells": [
            {k: c[k] for k in ("cell", "n", "sum", "ev", "wr", "wilson_lo", "n_recent")}
            for c in cells[:5]
        ],
        "definition_conflict": {
            "exists": True,
            "notes": [
                "m1-kpi-readout §8 (book 全体 bootstrap P(sum≤0)<0.05) と "
                "monthly-target-rederivation §4 (セル単位 N≥30 資格) は資格の"
                "母集団が異なる — 両方を計算して併記、裁定は user",
                f"rederivation §4 literal は「正EVセル」(EV>0)、実装主定義は "
                f"EV≥+{STRONG_MIN_EV_PIPS}p/t (2026-09-10 user 指示) — "
                "両カウント併記",
                "WR の Wilson95 下限>0 は「勝ち≥1 件」と同値で EV>0 が含意する "
                f"(win-rate 解釈では非拘束)。参考: wilson_lo≥{WILSON_GATE_REF} "
                "の保守カウントを併記",
            ],
        },
    }


def pip_size(instrument: str) -> float:
    """pip の価格刻み。JPY quote = 0.01、それ以外 = 0.0001 (XAU は roadmap で除外)。"""
    return 0.01 if str(instrument or "").upper().endswith("_JPY") else 0.0001


def broker_trade_metrics(trade: dict[str, Any]) -> dict[str, Any] | None:
    """OANDA v20 trade object → broker 基準の実現値 (純関数)。

    CLOSED 以外・必須キー欠損・units 0 は ``None`` (= 突合不能、0 で埋めない)。
    pips = (averageClosePrice − price) × sign(initialUnits) / pip_size。
    pl_jpy = realizedPL (口座通貨 JPY)、financing は別掲 (net = pl + financing)。
    """
    try:
        if str(trade.get("state", "")).upper() != "CLOSED":
            return None
        units = float(trade["initialUnits"])
        open_px = float(trade["price"])
        close_px = float(trade["averageClosePrice"])
        pl = float(trade["realizedPL"])
        fin = float(trade.get("financing") or 0.0)
    except (KeyError, TypeError, ValueError):
        return None
    if units == 0:
        return None
    sign = 1.0 if units > 0 else -1.0
    instrument = str(trade.get("instrument") or "")
    pips = (close_px - open_px) * sign / pip_size(instrument)
    return {
        "pl_jpy": pl,
        "financing_jpy": fin,
        "net_jpy": pl + fin,
        "pips": round(pips, 2),
        "units": abs(units),
        "instrument": instrument,
        "close_time": trade.get("closeTime"),
    }


def needed_broker_ids(rows: Iterable[dict[str, Any]], anchor: datetime,
                      cutoff: str = CLEAN_CUTOFF) -> set[str]:
    """demo 側 clean live 母集団 (cutoff..anchor) の oanda_trade_id 集合。"""
    cutoff_dt = datetime.strptime(cutoff, "%Y-%m-%d")
    ids: set[str] = set()
    for r in rows:
        if not is_clean_live(r):
            continue
        ts = parse_ts(r.get("created_at"))
        if ts is None or ts < cutoff_dt or ts > anchor:
            continue
        ids.add(str(r.get("oanda_trade_id")).strip())
    return ids


def _default_broker_fetcher(api: str):
    def _fetch(before_id: int | None) -> tuple[bool, Any]:
        params: dict[str, Any] = {"state": "CLOSED", "count": BROKER_PAGE_SIZE}
        if before_id is not None:
            params["before_id"] = int(before_id)
        try:
            resp = requests.get(f"{api}/api/oanda/trades_remote", params=params, timeout=120)
            if resp.status_code != 200:
                return False, f"HTTP {resp.status_code}"
            return True, resp.json()
        except (requests.RequestException, ValueError) as exc:
            return False, str(exc)
    return _fetch


def fetch_broker_closed_trades(
    needed_ids: set[str],
    api: str = DEFAULT_API,
    fetcher=None,
    max_pages: int = BROKER_MAX_PAGES,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """/api/oanda/trades_remote (OANDA closed trades の live proxy) を beforeID で
    遡り、``needed_ids`` を被覆する。戻り = (id→trade, status)。

    status = {ok, pages, reason, oldest_id_seen, covered, missing}。
    失敗時は **部分 map + ok=False** — 読み手は broker 列を unavailable にする
    (lesson: 失敗を 0 件と偽らない)。
    """
    fetcher = fetcher or _default_broker_fetcher(api)
    found: dict[str, dict[str, Any]] = {}
    status: dict[str, Any] = {"ok": True, "pages": 0, "reason": None,
                              "oldest_id_seen": None, "covered": 0,
                              "missing": len(needed_ids)}
    if not needed_ids:
        return found, status
    try:
        min_needed = min(int(i) for i in needed_ids)
    except ValueError:
        status.update(ok=False, reason="non-integer oanda_trade_id in needed_ids")
        return found, status
    before: int | None = None
    while status["pages"] < max_pages:
        ok, payload = fetcher(before)
        status["pages"] += 1
        if not ok:
            status.update(ok=False, reason=f"fetch failed: {payload}")
            break
        trades = (payload or {}).get("trades") or []
        if not trades:
            break
        ids_page: list[int] = []
        for t in trades:
            tid = str(t.get("id", "")).strip()
            try:
                ids_page.append(int(tid))
            except ValueError:
                continue
            if tid in needed_ids:
                found[tid] = t
        if not ids_page:
            status.update(ok=False, reason="page without integer trade ids")
            break
        oldest = min(ids_page)
        status["oldest_id_seen"] = oldest
        if len(found) >= len(needed_ids) or oldest <= min_needed:
            break
        before = oldest
    else:
        status.update(ok=False, reason=f"max_pages {max_pages} reached before coverage")
    status["covered"] = len(found)
    status["missing"] = len(needed_ids) - len(found)
    if status["ok"] and status["missing"] > 0:
        # 被覆範囲に関わらず、必要 id が 1 つでも欠ければ broker 基準は unavailable
        # (0 で埋めない / 部分一致を ok と呼ばない — Codex P2 2026-10-20)
        if status["oldest_id_seen"] is None or status["oldest_id_seen"] > min_needed:
            reason = "coverage stopped before oldest needed id"
        else:
            reason = f"{status['missing']} needed id(s) absent from broker closed trades"
        status.update(ok=False, reason=reason)
    return found, status


def cumulative_cell_stats_broker(
    rows: Iterable[dict[str, Any]],
    anchor: datetime,
    broker_map: dict[str, dict[str, Any]],
    days: int = WINDOW_DAYS,
    cutoff: str = CLEAN_CUTOFF,
) -> list[dict[str, Any]]:
    """セル別 **broker 基準** 累積統計。母集団は demo 側 (``cumulative_cell_stats``)
    と同一 (is_clean_live ∧ cutoff..anchor) — 片寄せしない (D11 pre-reg 規律)。

    broker_map に無い行は ``n_unmatched`` に積み、統計には含めない (0 埋め禁止)。
    ``basis_complete`` = n_unmatched == 0 の時だけ predicate を評価できる。
    """
    cutoff_dt = datetime.strptime(cutoff, "%Y-%m-%d")
    span = timedelta(days=days)
    cells: dict[str, dict[str, Any]] = {}
    for r in rows:
        if not is_clean_live(r):
            continue
        ts = parse_ts(r.get("created_at"))
        if ts is None or ts < cutoff_dt or ts > anchor:
            continue
        key = f"{r.get('entry_type')}×{r.get('instrument')}×{r.get('direction')}"
        c = cells.setdefault(key, {
            "cell": key, "instrument": r.get("instrument"),
            "n": 0, "n_matched": 0, "n_unmatched": 0,
            "sum_pl_jpy": 0.0, "sum_financing_jpy": 0.0, "sum_pips": 0.0,
            "wins": 0, "n_recent": 0, "sum_pips_recent": 0.0,
        })
        c["n"] += 1
        m = broker_trade_metrics(broker_map.get(str(r.get("oanda_trade_id")).strip()) or {})
        if m is None:
            c["n_unmatched"] += 1
            continue
        c["n_matched"] += 1
        c["sum_pl_jpy"] += m["pl_jpy"]
        c["sum_financing_jpy"] += m["financing_jpy"]
        c["sum_pips"] += m["pips"]
        if m["pl_jpy"] > 0:
            c["wins"] += 1
        if anchor - ts < span:
            c["n_recent"] += 1
            c["sum_pips_recent"] += m["pips"]
    out = []
    for c in cells.values():
        nm = c["n_matched"]
        for k in ("sum_pl_jpy", "sum_financing_jpy", "sum_pips", "sum_pips_recent"):
            c[k] = round(c[k], 2)
        c["ev_pips"] = round(c["sum_pips"] / nm, 3) if nm else None
        c["wr"] = round(c["wins"] / nm, 4) if nm else None
        c["wilson_lo"] = round(wilson_lower(c["wins"], nm), 4) if nm else None
        c["basis_complete"] = c["n_unmatched"] == 0 and nm > 0
        out.append(c)
    out.sort(key=lambda c: (-c["n"], c["cell"]))
    return out


def _pred_reg_literal(n: int, total: float) -> bool:
    """REG project-falsification-f3 の condition 字義: clean live N≥30 ∧ PnL>0。"""
    return n >= STRONG_MIN_N and total > 0


def _pred_strong(n: int, ev: float | None, wilson_lo: float | None,
                 min_ev: float = STRONG_MIN_EV_PIPS) -> bool:
    """実装主定義: N≥30 ∧ EV≥+1.0p/t ∧ Wilson95 下限(WR) > 0。"""
    return (n >= STRONG_MIN_N and ev is not None and wilson_lo is not None
            and ev >= min_ev and wilson_lo > 0.0)


def basis_table(cells_demo: list[dict[str, Any]],
                cells_broker: list[dict[str, Any]]) -> dict[str, Any]:
    """同一セル集合で **2 基準 (demo pnl_pips / broker realized) × 2 predicate
    (REG 字義 / STRONG)** を並記する (D11 両基準併記)。

    broker 側は basis_complete の時のみ predicate を評価、それ以外は
    ``"unavailable"`` (不一致でも一致でもない)。基準の選択はしない。
    """
    by_key = {c["cell"]: c for c in cells_broker}
    rows: list[dict[str, Any]] = []
    counts = {"reg_literal_demo": 0, "strong_demo": 0,
              "reg_literal_broker": 0, "strong_broker": 0,
              "broker_unavailable_cells": 0}
    disagreements: list[str] = []
    for d in cells_demo:
        b = by_key.get(d["cell"])
        demo = {
            "sum": d["sum"], "ev": d["ev"], "wilson_lo": d["wilson_lo"],
            "reg_literal": _pred_reg_literal(d["n"], d["sum"]),
            "strong": _pred_strong(d["n"], d["ev"], d["wilson_lo"]),
        }
        counts["reg_literal_demo"] += int(demo["reg_literal"])
        counts["strong_demo"] += int(demo["strong"])
        if b is None or not b["basis_complete"]:
            broker: dict[str, Any] = {
                "status": "unavailable",
                "n_matched": (b or {}).get("n_matched", 0),
                "n_unmatched": (b or {}).get("n_unmatched", d["n"]),
            }
            counts["broker_unavailable_cells"] += 1
        else:
            broker = {
                "status": "ok", "n_matched": b["n_matched"], "n_unmatched": 0,
                "sum_pl_jpy": b["sum_pl_jpy"], "sum_financing_jpy": b["sum_financing_jpy"],
                "sum_pips": b["sum_pips"], "ev_pips": b["ev_pips"],
                "wilson_lo": b["wilson_lo"],
                # REG 字義の「PnL>0」を broker で読む = realizedPL (JPY) 合計 > 0
                "reg_literal": _pred_reg_literal(b["n_matched"], b["sum_pl_jpy"]),
                "strong": _pred_strong(b["n_matched"], b["ev_pips"], b["wilson_lo"]),
            }
            counts["reg_literal_broker"] += int(broker["reg_literal"])
            counts["strong_broker"] += int(broker["strong"])
            if (broker["reg_literal"] != demo["reg_literal"]
                    or broker["strong"] != demo["strong"]):
                disagreements.append(d["cell"])
        rows.append({"cell": d["cell"], "n": d["n"], "demo": demo, "broker": broker})
    return {
        "predicates": {
            "reg_literal": f"clean live N≥{STRONG_MIN_N} ∧ PnL>0 (REG F3 condition 字義)",
            "strong": f"N≥{STRONG_MIN_N} ∧ EV≥+{STRONG_MIN_EV_PIPS}p/t ∧ Wilson95下限(WR)>0",
        },
        "bases": {
            "demo": "demo_trades.pnl_pips (bid/ask 建て、trail/BE 自己約定込み)",
            "broker": f"OANDA closed trade realizedPL ({BROKER_ACCOUNT_CCY}) + price-derived pips",
        },
        "counts": counts,
        "disagreements": disagreements,
        "rows": rows,
    }


def _pip_value_jpy_est(instrument: str, units: float = EFFECTIVE_UNITS_ASSUMPTION) -> float:
    """1 pip の JPY 価値 **推定値**。JPY quote は正確、他 quote は概算レート。

    demo_trades 行に units カラムが無いため units は仮定値
    (EFFECTIVE_UNITS_ASSUMPTION)。一次単位は常に pips — JPY はラベル付き推定。
    """
    try:
        _, quote = (instrument or "").split("_")
    except ValueError:
        return 0.0
    if quote == "JPY":
        return units * 0.01
    return units * 0.0001 * QUOTE_JPY_APPROX.get(quote, 160.0)


def m3_summary(
    rows: Iterable[dict[str, Any]],
    anchor: datetime,
    days: int = WINDOW_DAYS,
    nav_jpy: float | None = None,
) -> dict[str, Any]:
    """M3 の二定義分離: M3a (throughput) / M3b (return) + 線形外挿 ETA。"""
    cells = cumulative_cell_stats(rows, anchor, days)

    # ── M3a: clean live 累積 N≥30 のセル数 / 3 ──
    # ⚠️ 二母集団を混ぜない (ps capture 教訓): 「累積 N≥30」には過去に蓄積して
    # 現在は発火ゼロの休眠セル (R2 demote 済み等) が含まれる。09-04 の再計測
    # 「0 個」は稼働ロースタ側の読みなので、cumulative / active の両方を出す。
    done = [c for c in cells if c["n"] >= STRONG_MIN_N]
    done_active = [c for c in done if c["n_recent"] > 0]
    etas: list[dict[str, Any]] = []
    for c in cells:
        if c["n"] >= STRONG_MIN_N:
            etas.append({"cell": c["cell"], "n": c["n"], "eta_days": 0.0,
                         "rate_per_30d": c["n_recent"]})
            continue
        rate_per_day = c["n_recent"] / days  # 直近 30d の N 蓄積レート (線形外挿)
        if rate_per_day <= 0:
            etas.append({"cell": c["cell"], "n": c["n"], "eta_days": None,
                         "rate_per_30d": 0})
            continue
        eta_days = (STRONG_MIN_N - c["n"]) / rate_per_day
        etas.append({"cell": c["cell"], "n": c["n"],
                     "eta_days": round(eta_days, 1),
                     "eta_date": (anchor + timedelta(days=eta_days)).date().isoformat(),
                     "rate_per_30d": c["n_recent"]})
    finite = sorted([e for e in etas if e["eta_days"] is not None],
                    key=lambda e: e["eta_days"])
    if len(finite) >= M3A_TARGET_CELLS:
        third = finite[M3A_TARGET_CELLS - 1]
        m3a_eta_date = (anchor + timedelta(days=third["eta_days"])).date().isoformat()
        m3a_eta_days = third["eta_days"]
    else:
        m3a_eta_date = None
        m3a_eta_days = None

    # ── M3b: 摩擦調整後 (live 実現 net pips) 正EVセルの直近 30d 寄与 ──
    pos_cells = [c for c in cells if c["ev"] > 0]
    m3b_pips = round(sum(c["sum_recent"] for c in pos_cells), 2)
    m3b_jpy_est = round(sum(
        c["sum_recent"] * _pip_value_jpy_est(c["instrument"] or "")
        for c in pos_cells
    ), 1)
    m3b_pct_est = (
        round(m3b_jpy_est / nav_jpy * 100.0, 4) if nav_jpy and nav_jpy > 0 else None
    )
    m3b_met = m3b_pct_est is not None and m3b_pct_est >= M3B_TARGET_PCT
    if m3b_pct_est is None:
        m3b_eta = "UNKNOWN (NAV 未取得 — %換算不能)"
    elif m3b_met:
        m3b_eta = "達成中"
    else:
        # 線形 N 外挿 = 月次寄与レートは一定 → 現状未達なら同ペースで到達不能
        m3b_eta = "現行ペースで到達不能 (線形 N 外挿では月次寄与レート一定)"

    return {
        "anchor": anchor.isoformat(),
        "m3a": {
            "definition": f"clean live 累積 (cutoff {CLEAN_CUTOFF}) N≥{STRONG_MIN_N} のセル数 / {M3A_TARGET_CELLS} (roadmap v2.3 KPI 表 throughput 版)",
            "cells_done": len(done),
            "cells_done_active": len(done_active),
            "population_note": (
                "cells_done は累積 (休眠セル含む) / cells_done_active は直近 "
                f"{days}d に発火のあるセルのみ — 09-04 再計測の「0 個」は後者の読み"
            ),
            "target": M3A_TARGET_CELLS,
            "met": len(done) >= M3A_TARGET_CELLS,
            "eta_date": m3a_eta_date,
            "eta_days": m3a_eta_days,
            "eta_method": f"直近 {days}d の N 蓄積レートから線形外挿 (セル毎)、{M3A_TARGET_CELLS} 本目の到達日",
            "per_cell": etas[:8],
        },
        "m3b": {
            "definition": (
                "摩擦調整後 (= live 実現 net pips) 正EVセルの直近 30d 寄与合計。"
                f"primary 目標 +{M3B_TARGET_PCT}%/月 (2026-09-10 user 指示)。"
                f"rederivation §4 の M3 return 版は +{M3B_REDERIV_BAND[0]}〜{M3B_REDERIV_BAND[1]}%/月 — 定義併存 (裁定は user)"
            ),
            "n_positive_ev_cells": len(pos_cells),
            "n_positive_ev_cells_n30": sum(1 for c in pos_cells if c["n"] >= STRONG_MIN_N),
            "pips_30d": m3b_pips,
            "jpy_30d_est": m3b_jpy_est,
            "jpy_est_assumptions": (
                f"units={EFFECTIVE_UNITS_ASSUMPTION:.0f} 仮定 + quote→JPY 概算 "
                "(JPY quote は正確) — 一次単位は pips"
            ),
            "nav_jpy": nav_jpy,
            "pct_nav_30d_est": m3b_pct_est,
            "target_pct": M3B_TARGET_PCT,
            "target_pct_rederivation": list(M3B_REDERIV_BAND),
            "met": m3b_met,
            "eta": m3b_eta,
        },
    }


_VERDICT_ICON = {
    "MET": "🟢",
    "MET_UNDERPOWERED": "🟡",
    "NOT_MET": "🔴",
    "NO_DATA": "⚪",
}


def to_markdown(report: dict[str, Any]) -> str:
    icon = _VERDICT_ICON.get(report["verdict"], "?")
    lines = [
        "## M1 KPI (clean live 30d PnL)",
        f"- **{icon} {report['verdict']}** — N={report['n']} / "
        f"sum={report['sum_pips']:+.1f}p / EV={report['ev_pips']:+.2f}p per trade / "
        f"WR={report['win_rate'] * 100:.1f}%",
        f"- bootstrap 95% CI = [{report['ci95_lo']:+.1f}p, {report['ci95_hi']:+.1f}p] / "
        f"P(sum<=0) = {report['p_le_zero']:.3f}",
        f"- estimand: {report['estimand']} ⚠️ pip 合計であって口座損益ではない",
    ]
    frag = report["fragility"]
    if frag["n_sign_flipping_trades"]:
        lines.append(
            f"- ⚠️ 脆弱性: **1 件抜くだけで符号が消える約定が {frag['n_sign_flipping_trades']} 件** "
            f"(最大 {frag['worst_removed']:+.1f}p)"
        )
    fa = report["flip_attribution"]
    lines.append(
        f"- 直近 {fa['lookback_days']}d 差分: 新規 N={fa['n_added']} ({fa['sum_added']:+.1f}p) / "
        f"窓外へ脱落 N={fa['n_aged_out']} ({fa['sum_aged_out']:+.1f}p) → Δ={fa['delta']:+.1f}p"
    )
    if fa["mechanical_flip"]:
        top = fa["aged_out_detail"][0] if fa["aged_out_detail"] else None
        detail = (
            f" 主因 = {top['created_at']} {top['entry_type']} {top['pnl_pips']:+.1f}p"
            if top
            else ""
        )
        lines.append(
            "- 🚨 **MECHANICAL_FLIP — 符号反転は新しい成果ではなく古い約定の窓外脱落による。**"
            + detail
        )
    elif fa["sign_flipped"]:
        lines.append("- ℹ️ 符号は反転したが、寄与は新規約定側が優勢")
    if report["cells"]:
        lines.append("- 窓内セル: " + ", ".join(
            f"{k} (N={v['n']}, {v['sum']:+.1f}p)" for k, v in report["cells"].items()
        ))
    if "strong" in report:
        lines.append("")
        lines.append(to_markdown_strong(report["strong"]))
    if "m3" in report:
        lines.append("")
        lines.append(to_markdown_m3(report["m3"]))
    return "\n".join(lines)


def to_markdown_strong(s: dict[str, Any]) -> str:
    """M1_STRONG セクション (Discord 1900 字制約下でも読める密度で)。"""
    cell_icon = "🟢" if s["m1_strong_cell_met"] else "🔴"
    book_icon = "🟢" if s["m1_strong_book_met"] else "🔴"
    lines = [
        "## M1_STRONG (強定義)",
        f"- {cell_icon} **セル定義 [rederivation §4 系]: {s['n_cells_strong']} セル "
        f"(達成には ≥1)** — {s['estimand_cell']}",
        f"- {book_icon} book 定義 [m1-kpi §8 案]: verdict={s['book_verdict']} "
        f"(MET のみ達成扱い) / FULL (セル∧book) = "
        f"{'達成' if s['m1_strong_full_met'] else '未達'}",
        f"- 併記: 正EV literal (EV>0, N≥{STRONG_MIN_N}) = "
        f"{s['n_cells_rederivation_literal']} セル / "
        f"wilson_lo≥{WILSON_GATE_REF} 保守 = {s['n_cells_wilson_gate_ref']} セル",
        "- ⚠️ 定義矛盾あり (§8 book bootstrap vs rederivation §4 セル単位 / "
        f"EV>0 vs ≥+{STRONG_MIN_EV_PIPS}p/t) — 両方併記、裁定は user",
    ]
    if s["qualifying_cells"]:
        lines.append("- 資格セル: " + ", ".join(
            f"{c['cell']} (N={c['n']}, EV={c['ev']:+.2f}p, w_lo={c['wilson_lo']:.2f})"
            for c in s["qualifying_cells"]
        ))
    elif s["top_cells"]:
        top = s["top_cells"][0]
        lines.append(
            f"- 最接近セル: {top['cell']} (N={top['n']}/{STRONG_MIN_N}, "
            f"EV={top['ev']:+.2f}p, w_lo={top['wilson_lo']:.2f})"
        )
    lines.extend(_markdown_broker_basis(s))
    return "\n".join(lines)


def _markdown_broker_basis(s: dict[str, Any]) -> list[str]:
    """D11 両基準併記の行 (基準は選ばない、unavailable は unavailable と書く)。"""
    bb = s.get("broker_basis")
    if not bb:
        return []
    if bb.get("status") == "skipped":
        return [f"- 両基準 (D11): broker 列 skipped ({bb.get('reason')})"]
    table = bb.get("table") or {}
    counts = table.get("counts") or {}
    head = (
        f"- 両基準 (D11): REG字義(N≥{STRONG_MIN_N}∧PnL>0) demo={counts.get('reg_literal_demo', 0)} / "
        f"broker={counts.get('reg_literal_broker', 0)} | STRONG demo={counts.get('strong_demo', 0)} / "
        f"broker={counts.get('strong_broker', 0)} | 不一致セル={len(table.get('disagreements') or [])}"
    )
    out = [head]
    if bb.get("status") != "ok":
        f = bb.get("fetch") or {}
        out.append(
            f"- ⚠️ broker 列 unavailable ({bb.get('reason')}; covered={f.get('covered')} "
            f"missing={f.get('missing')} pages={f.get('pages')}) — 0 として読まないこと"
        )
    if counts.get("broker_unavailable_cells"):
        out.append(f"- broker 未突合セル = {counts['broker_unavailable_cells']} (predicate 未評価)")
    rows = table.get("rows") or []
    if rows:
        top = rows[0]
        b = top["broker"]
        if b.get("status") == "ok":
            out.append(
                f"- 最接近セル broker: {top['cell']} (N={b['n_matched']}/{top['n']}, "
                f"pl=¥{b['sum_pl_jpy']:+,.0f}, EV={b['ev_pips']:+.2f}p, w_lo={b['wilson_lo']:.2f}; "
                f"demo EV={top['demo']['ev']:+.2f}p)"
            )
    return out


def to_markdown_m3(m3: dict[str, Any]) -> str:
    a, b = m3["m3a"], m3["m3b"]
    a_icon = "🟢" if a["met"] else "🔴"
    b_icon = "🟢" if b["met"] else ("⚪" if b["pct_nav_30d_est"] is None else "🔴")
    lines = [
        "## M3 (二定義分離)",
        f"- {a_icon} **M3a throughput: {a['cells_done']}/{a['target']} セル** "
        f"(clean live 累積 N≥{STRONG_MIN_N}、うち直近30d 稼働 "
        f"{a['cells_done_active']}) / ETA(3本目) = "
        f"{a['eta_date'] or '現行レートで算出不能 (蓄積中セル<3)'}",
    ]
    progress = [e for e in a["per_cell"] if e.get("eta_days") is not None][:3]
    if progress:
        lines.append("- M3a 先頭セル: " + ", ".join(
            f"{e['cell']} N={e['n']} (+{e['rate_per_30d']}/30d"
            + (f", ETA {e['eta_date']}" if e.get("eta_date") else ", 到達済")
            + ")"
            for e in progress
        ))
    pct = b["pct_nav_30d_est"]
    pct_txt = f"{pct:+.3f}%/月" if pct is not None else "N/A (NAV 未取得)"
    lines.append(
        f"- {b_icon} **M3b return: 正EV {b['n_positive_ev_cells']} セル "
        f"(N≥{STRONG_MIN_N} は {b['n_positive_ev_cells_n30']}) の 30d 寄与 = "
        f"{b['pips_30d']:+.1f}p ≈ ¥{b['jpy_30d_est']:+,.0f} ≈ {pct_txt}** "
        f"vs 目標 +{b['target_pct']}% (rederivation M3 は "
        f"+{b['target_pct_rederivation'][0]}〜{b['target_pct_rederivation'][1]}% — 併存)"
    )
    lines.append(f"- M3b ETA: {b['eta']} / JPY は推定 ({b['jpy_est_assumptions']})")
    return "\n".join(lines)


def fetch_trades(api: str = DEFAULT_API, limit: int = 100000) -> list[dict[str, Any]]:
    if not api.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        raise ValueError(f"unsupported API base (https required): {api!r}")
    resp = requests.get(f"{api}/api/demo/trades", params={"limit": int(limit)}, timeout=180)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("trades", [])


def _nav_from_status_payload(payload: dict[str, Any] | None) -> float | None:
    """/api/oanda/status 応答から NAV (JPY) を取り出す (純関数 — test 対象)。

    bridge.get_account_info() は OANDA v20 の {"account": {...}} を
    そのまま返すことがある (実測 2026-09-10) — 一段ネストも受ける。
    """
    account = (payload or {}).get("account") or {}
    if "NAV" not in account and isinstance(account.get("account"), dict):
        account = account["account"]
    for key in ("NAV", "nav", "balance"):
        if account.get(key) is not None:
            try:
                return float(account[key])
            except (ValueError, TypeError):
                return None
    return None


def fetch_nav_jpy(api: str = DEFAULT_API) -> float | None:
    """本番 /api/oanda/status から NAV (JPY) を読む (read-only GET)。

    M3b の %/月換算専用。取得失敗は None (M3b は pips 一次単位で成立する
    ため、NAV 欠損で readout 全体を落とさない)。
    """
    try:
        resp = requests.get(f"{api}/api/oanda/status", timeout=30)
        resp.raise_for_status()
        return _nav_from_status_payload(resp.json())
    except (requests.RequestException, ValueError, TypeError):
        return None


def build_report(
    api: str = DEFAULT_API,
    days: int = WINDOW_DAYS,
    lookback: int = LOOKBACK_DAYS,
    anchor: datetime | None = None,
    strong: bool = False,
    nav_jpy: float | None = None,
    broker: bool = True,
) -> dict[str, Any]:
    rows = fetch_trades(api)
    anchor = anchor or datetime.now(timezone.utc).replace(tzinfo=None)
    report = summarize(rows, anchor, days, lookback)
    if strong:
        # 弱定義 readout はそのまま (キー互換維持)、強定義 + M3 を追記する
        broker_payload = None
        if broker:
            ids = needed_broker_ids(rows, anchor)
            bmap, bstatus = fetch_broker_closed_trades(ids, api=api)
            broker_payload = {"map": bmap, "status": bstatus}
        report["strong"] = strong_summary(rows, anchor, days, weak=report,
                                          broker=broker_payload)
        if nav_jpy is None:
            nav_jpy = fetch_nav_jpy(api)
        report["m3"] = m3_summary(rows, anchor, days, nav_jpy=nav_jpy)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="M1 KPI (clean live 30d PnL) readout")
    ap.add_argument("--api", default=DEFAULT_API)
    ap.add_argument("--days", type=int, default=WINDOW_DAYS)
    ap.add_argument("--lookback", type=int, default=LOOKBACK_DAYS)
    ap.add_argument("--strong", action="store_true",
                    help="M1 強定義 (セル/book 両定義) + M3a/M3b readout を追記")
    ap.add_argument("--nav", type=float, default=None,
                    help="M3b %%換算用 NAV (JPY)。省略時は /api/oanda/status から取得")
    ap.add_argument("--no-broker", action="store_true",
                    help="D11 両基準併記の broker 列 (OANDA closed trades proxy) を取得しない")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        report = build_report(args.api, args.days, args.lookback,
                              strong=args.strong, nav_jpy=args.nav,
                              broker=not args.no_broker)
    except (requests.RequestException, ValueError) as exc:
        print(f"## M1 KPI (clean live 30d PnL)\n- ⚠️ 取得失敗: {exc}")
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else to_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
