#!/usr/bin/env python3
"""LIVE 発火セルの減耗 (roster attrition) 帰属 — M3 スループット問題の読み手。

背景 (2026-09-06)
-----------------
[[m1-kpi-readout-and-mechanical-flip-2026-09-04]] §6 は LIVE 発火セル数が
**124 セル/30d (2026-05) → 3 セル/30d (現在)** へ崩壊したことを実測し、
M3 (clean live N>=30 のセルを 3 個) の到達を最短 ~14 ヶ月と見積もった。
同 §6 は縮小を「7-8 月の R2 降格バッチによるもの = 設計通り」と解釈したが、
**その帰属は検証されていなかった** — どのセルがどの停止機構で止まったかを
機械的に突き合わせた主体がプロジェクトに存在しなかった。

本モジュールが名乗る estimand
-----------------------------
    「anchor 窓 (既定 2026-05-01 で終わる 30 日) で **clean LIVE 約定**を
      出していたセル (entry_type × instrument × direction) の集合が、
      現在窓 (既定 today で終わる 30 日) で LIVE 約定を出さなくなった理由の帰属」

    clean LIVE = ``oanda_trade_id`` 非空 ∧ ``dedup_violation != 1``
                 ∧ ``instrument != 'XAU_USD'``
                 (``is_shadow=0`` 単独では判定しない — FLAG_DRIFT 行が混入する。
                  MEMORY feedback_live_vs_shadow_strict_separation)

    ⚠️ **本モジュールは「なぜ LIVE 転送されなかったか」を測っていない。**
    測っているのは「コード上の停止機構・昇格集合との突き合わせで、
    LIVE 消滅が説明できるか否か」だけである。CLAUDE.md 原則 3 のとおり
    LIVE 転送側は winning-location フィルタ (session_pair / alpha_scan 等) を
    **意図的に**維持しており、昇格済みセルが LIVE ゼロであること自体は
    正常でありうる。したがって E クラスは「バグ」ではなく **未帰属** である。

分類 (優先順位順、先に一致したものを採る)
------------------------------------------
    A_STILL_LIVE          現在窓でも LIVE 約定がある
    B_LIVE_STOPPED        コード上の live 停止集合に載っている
                          (_FORCE_DEMOTED / _PAIR_DEMOTED / HTF_MIXED_LIVE_STOP_CELLS)
    C_SHADOW_DEMOTED      shadow 降格/退役registry・SHADOW_ALWAYS に載っている
    D_NEVER_PROMOTED      昇格集合 (_PAIR_PROMOTED ∪ _UNIVERSAL_SENTINEL) に無い
                          → shadow のみが設計状態であり、**anchor 窓の LIVE 行の方が異常**
                          (2026-07 の watchdog DECREMENT 再武装バグ / preserve 型バグ期と整合)
    E_PROMOTED_UNATTRIBUTED
                          昇格集合にあり、どの停止機構にも載らず、LIVE ゼロ
                          E1_SUPPLY_PRESENT : 現在窓でも候補行は出ている = 供給あり/転換ゼロ
                          E2_SILENT         : 現在窓の行が全くゼロ = rnb 型の沈黙シグネチャ
                                              (cf. analyses/rnb-dead-mode-and-block-estimand-2026-09-05)

使用:
    python3 tools/live_roster_attrition.py
    python3 tools/live_roster_attrition.py --json
    python3 tools/live_roster_attrition.py --anchor 2026-05-01 --days 30
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

DEFAULT_API = "https://fx-ai-trader.onrender.com"
DEFAULT_ANCHOR = "2026-05-01"
DEFAULT_DAYS = 30
REPO = Path(__file__).resolve().parent.parent

CLASSES = (
    "A_STILL_LIVE",
    "B_LIVE_STOPPED",
    "C_SHADOW_DEMOTED",
    "D_NEVER_PROMOTED",
    "E_PROMOTED_UNATTRIBUTED",
)


# ---------------------------------------------------------------- stop sets
def _literal_sets_from_demo_trader(names: set[str]) -> dict[str, set]:
    """modules/demo_trader.py のクラス属性 literal を AST で抽出する。

    import せずに読むのは、demo_trader の import が本番スレッドを起動しうる
    ため (lesson: tools/*.py はスクリプトかつライブラリ / モジュールトップの
    副作用禁止)。
    """
    tree = ast.parse((REPO / "modules" / "demo_trader.py").read_text())
    out: dict[str, set] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            name = getattr(target, "id", None) or getattr(target, "attr", None)
            if name in names:
                try:
                    out[name] = set(ast.literal_eval(node.value))
                except (ValueError, SyntaxError):
                    continue
    missing = names - set(out)
    if missing:
        raise RuntimeError(f"demo_trader から抽出できない集合: {sorted(missing)}")
    return out


def load_stop_sets() -> dict[str, set]:
    """live 停止 / shadow 降格 / 昇格の全集合を集める。

    ⚠️ ここに新しい停止機構を足し忘れると、その機構で止めたセルが
    E_PROMOTED_UNATTRIBUTED に化けて「未帰属が増えた」と誤読される。
    停止機構を追加したら本関数と test_live_roster_attrition を同時に直すこと。
    """
    sets = _literal_sets_from_demo_trader(
        {"_FORCE_DEMOTED", "_PAIR_DEMOTED", "_PAIR_PROMOTED", "_UNIVERSAL_SENTINEL"}
    )
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from strategies.daytrade import DaytradeEngine  # noqa: PLC0415
    from modules import shadow_demote_registry as sdr  # noqa: PLC0415

    return {
        "force_demoted": set(sets["_FORCE_DEMOTED"]),
        "pair_demoted": {tuple(x) for x in sets["_PAIR_DEMOTED"]},
        "pair_promoted": {tuple(x) for x in sets["_PAIR_PROMOTED"]},
        "universal_sentinel": set(sets["_UNIVERSAL_SENTINEL"]),
        "htf_mixed_stop": {tuple(x) for x in DaytradeEngine.HTF_MIXED_LIVE_STOP_CELLS},
        "shadow_always": set(DaytradeEngine.SHADOW_ALWAYS_STRATEGIES),
        "shadow_demoted": {tuple(x) for x in sdr.SHADOW_DEMOTED_CELLS},
        "shadow_retired": set(sdr.SHADOW_RETIRED_STRATEGIES),
    }


# ------------------------------------------------------------------- rows
def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def is_clean_live(row: dict[str, Any]) -> bool:
    return (
        str(row.get("oanda_trade_id") or "").strip() != ""
        and row.get("dedup_violation") != 1
        and row.get("instrument") != "XAU_USD"
    )


def cell_of(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("entry_type") or ""),
        str(row.get("instrument") or ""),
        str(row.get("direction") or ""),
    )


def fetch_trades(api: str = DEFAULT_API, limit: int = 200000) -> list[dict[str, Any]]:
    """本番 API から全 trade 行を取る。

    ⚠️ 失敗を空リストに畳まない (lesson: `fetch_json` が失敗を {} に潰して
    「取りに行けなかった」と「空だった」を折り畳んだ 2026-08-30 の監視 blind)。
    """
    if not api.startswith("https://"):
        raise ValueError(f"unsupported API base (https required): {api!r}")
    resp = requests.get(f"{api}/api/demo/trades", params={"limit": int(limit)}, timeout=300)
    resp.raise_for_status()
    payload = resp.json()
    rows = payload.get("trades", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise RuntimeError(f"unexpected /api/demo/trades payload: {type(rows).__name__}")
    return rows


# --------------------------------------------------------------- classify
def classify(cell: tuple[str, str, str], *, still_live: bool, stops: dict[str, set]) -> str:
    entry_type, instrument, _direction = cell
    if still_live:
        return "A_STILL_LIVE"
    if (
        entry_type in stops["force_demoted"]
        or (entry_type, instrument) in stops["pair_demoted"]
        or (entry_type, instrument) in stops["htf_mixed_stop"]
    ):
        return "B_LIVE_STOPPED"
    if (
        entry_type in stops["shadow_retired"]
        or (entry_type, instrument) in stops["shadow_demoted"]
        or entry_type in stops["shadow_always"]
    ):
        return "C_SHADOW_DEMOTED"
    if (entry_type, instrument) not in stops["pair_promoted"] and entry_type not in stops["universal_sentinel"]:
        return "D_NEVER_PROMOTED"
    return "E_PROMOTED_UNATTRIBUTED"


def build_report(
    rows: list[dict[str, Any]],
    *,
    anchor: str = DEFAULT_ANCHOR,
    days: int = DEFAULT_DAYS,
    now: datetime | None = None,
    stops: dict[str, set] | None = None,
) -> dict[str, Any]:
    stops = stops if stops is not None else load_stop_sets()
    anchor_end = datetime.fromisoformat(anchor).replace(tzinfo=timezone.utc)
    cur_end = now or datetime.now(timezone.utc)
    span = timedelta(days=days)

    baseline: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    current_live: set[tuple[str, str, str]] = set()
    cur_rows_by_cell: Counter = Counter()
    for row in rows:
        stamp = parse_ts(row.get("created_at"))
        if stamp is None:
            continue
        if is_clean_live(row) and anchor_end - span <= stamp <= anchor_end:
            baseline[cell_of(row)].append(row)
        if cur_end - span <= stamp <= cur_end:
            cur_rows_by_cell[cell_of(row)] += 1
            if is_clean_live(row):
                current_live.add(cell_of(row))

    cells: list[dict[str, Any]] = []
    for cell, cell_rows in baseline.items():
        klass = classify(cell, still_live=cell in current_live, stops=stops)
        supply = cur_rows_by_cell.get(cell, 0)
        subclass = None
        if klass == "E_PROMOTED_UNATTRIBUTED":
            subclass = "E1_SUPPLY_PRESENT" if supply > 0 else "E2_SILENT"
        cells.append(
            {
                "entry_type": cell[0],
                "instrument": cell[1],
                "direction": cell[2],
                "anchor_live_n": len(cell_rows),
                "anchor_live_pips": round(sum(float(r.get("pnl_pips") or 0.0) for r in cell_rows), 1),
                "current_rows_any": supply,
                "class": klass,
                "subclass": subclass,
            }
        )
    cells.sort(key=lambda c: (c["class"], -c["anchor_live_n"]))

    counts = Counter(c["class"] for c in cells)
    sub = Counter(c["subclass"] for c in cells if c["subclass"])
    total = len(cells)
    explained = sum(counts[k] for k in ("A_STILL_LIVE", "B_LIVE_STOPPED", "C_SHADOW_DEMOTED", "D_NEVER_PROMOTED"))
    return {
        "generated_at": cur_end.isoformat(),
        "anchor_window_end": anchor_end.isoformat(),
        "current_window_end": cur_end.isoformat(),
        "days": days,
        "baseline_cells": total,
        "current_live_cells": len(current_live),
        "counts": dict(counts),
        "subcounts": dict(sub),
        "attributed_share": round(explained / total, 4) if total else None,
        "cells": cells,
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = ["## LIVE Roster Attrition", ""]
    lines.append(
        f"- anchor 窓終端 **{report['anchor_window_end'][:10]}** / 現在窓終端 "
        f"**{report['current_window_end'][:10]}** ({report['days']}d)"
    )
    lines.append(
        f"- anchor 窓の LIVE 発火セル **{report['baseline_cells']}** → 現在窓 "
        f"**{report['current_live_cells']}**"
    )
    share = report.get("attributed_share")
    lines.append(f"- 帰属済み割合 **{share:.1%}**" if share is not None else "- 帰属済み割合 n/a")
    lines.append("")
    lines.append("| class | cells |")
    lines.append("|---|---:|")
    for klass in CLASSES:
        if klass in report["counts"]:
            lines.append(f"| {klass} | {report['counts'][klass]} |")
    for name, num in sorted(report.get("subcounts", {}).items()):
        lines.append(f"| ↳ {name} | {num} |")
    unattributed = [c for c in report["cells"] if c["class"] == "E_PROMOTED_UNATTRIBUTED"]
    if unattributed:
        lines += ["", "### E: 昇格済みだが LIVE ゼロ (未帰属 — バグとは限らない)", ""]
        lines.append("| cell | anchor N | 現在窓 行数 | subclass |")
        lines.append("|---|---:|---:|---|")
        for c in unattributed:
            lines.append(
                f"| {c['entry_type']} × {c['instrument']} × {c['direction']} "
                f"| {c['anchor_live_n']} | {c['current_rows_any']} | {c['subclass']} |"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--api", default=DEFAULT_API)
    ap.add_argument("--anchor", default=DEFAULT_ANCHOR)
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    report = build_report(fetch_trades(args.api), anchor=args.anchor, days=args.days)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else to_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
