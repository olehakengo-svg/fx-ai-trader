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

使用:
    python3 tools/m1_clean_live_monitor.py
    python3 tools/m1_clean_live_monitor.py --json
    python3 tools/m1_clean_live_monitor.py --days 30 --lookback 7
"""
from __future__ import annotations

import argparse
import json
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

_TS_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")


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
    return "\n".join(lines)


def fetch_trades(api: str = DEFAULT_API, limit: int = 100000) -> list[dict[str, Any]]:
    if not api.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        raise ValueError(f"unsupported API base (https required): {api!r}")
    resp = requests.get(f"{api}/api/demo/trades", params={"limit": int(limit)}, timeout=180)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("trades", [])


def build_report(
    api: str = DEFAULT_API,
    days: int = WINDOW_DAYS,
    lookback: int = LOOKBACK_DAYS,
    anchor: datetime | None = None,
) -> dict[str, Any]:
    rows = fetch_trades(api)
    anchor = anchor or datetime.now(timezone.utc).replace(tzinfo=None)
    return summarize(rows, anchor, days, lookback)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="M1 KPI (clean live 30d PnL) readout")
    ap.add_argument("--api", default=DEFAULT_API)
    ap.add_argument("--days", type=int, default=WINDOW_DAYS)
    ap.add_argument("--lookback", type=int, default=LOOKBACK_DAYS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        report = build_report(args.api, args.days, args.lookback)
    except (requests.RequestException, ValueError) as exc:
        print(f"## M1 KPI (clean live 30d PnL)\n- ⚠️ 取得失敗: {exc}")
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else to_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
