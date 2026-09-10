#!/usr/bin/env python3
"""D クラス (旧 `D_NEVER_PROMOTED`) の estimand 監査 — 再実行可能な読み手。

なぜこのツールがあるか (2026-09-10)
-----------------------------------
`tools/live_roster_attrition.py` は anchor 窓の LIVE 発火セルを現在の集合と
突き合わせて分類する。B/C/E は **現在形**の問い (「今なにが止めているか」) な
ので現在の集合を読むのが正しい estimand だが、旧 `D_NEVER_PROMOTED` だけは
**過去形**の主張 ——「anchor 当時も未昇格 = 本来出てはいけなかった発火」——
をしていた。根拠は「**現在**の `_PAIR_PROMOTED ∪ _UNIVERSAL_SENTINEL` に
不在」だけであり、これは当時の昇格状態を何も含意しない
(PR #226 Codex P1 finding #2、レビュー到着 1 秒後にマージされ未読だった)。

本モジュールが名乗る estimand
-----------------------------
    「D セルの clean LIVE 約定 1 件ごとに、**その約定時刻に本番へ
      デプロイされていたコード**の live 資格判定で、その約定が
      設計上ありえたか否か」

    再構成は `origin/main` の first-parent 履歴から
    `modules/demo_trader.py` を約定時刻直前の commit で取り出し、
    `_FORCE_DEMOTED` / `_PAIR_DEMOTED` を AST で読む
    (import は本番スレッドを起動しうるので禁止 — 親ツールと同じ規律)。

判定 (per fire)
---------------
    LEGIT_NO_DEMOTE_MECHANISM
        約定時刻のコードに降格集合 (`_FORCE_DEMOTED` / `_PAIR_DEMOTED`) が
        **そもそも存在しなかった** (2026-04 初旬)。この時期の
        `_is_promoted()` は `return True  # 一時的に全戦略をOANDA送信` で、
        commit も "temp: disable OANDA strategy promotion filter — send all
        entries to OANDA" (8a42d776, 2026-04-03) と明示している。
        → 最も明確に「設計どおりの LIVE」
    LEGIT_ALLOW_BY_DEFAULT
        約定時刻が Phase-0 三層化 (`_SHADOW_MODE` + `_ELITE_LIVE`) の導入前。
        当時 `_is_promoted()` は既定 `return True` = **OANDA 送信 allow-by-default**
        で、`_FORCE_DEMOTED` / `_PAIR_DEMOTED` / 自動降格に載っていなければ
        LIVE が設計状態だった (v6.2 の「N<10 は Sentinel lot で保護」)。
        → 「本来出てはいけなかった発火」ではない
    ILLEGIT_DEMOTED_AT_FIRE
        約定時刻に当該 entry_type が `_FORCE_DEMOTED`、または
        (entry_type, instrument) が `_PAIR_DEMOTED` に載っていた
        → 真に設計違反の発火 (ただし下記 limitation を読め)
    POST_GATE_UNEXPLAINED
        Phase-0 ゲート導入後の約定で、現在の昇格集合にも不在
        → 別途の説明が必要 (昇格集合の履歴再構成が必要)

⚠️ Limitation (この監査で潰せない自由度)
----------------------------------------
`_is_promoted()` は静的集合より**先に** `self._oanda.get_strategy_mode()` を
見て、"live"/"sentinel" なら全降格を上書きする。これはランタイム DB 状態で
git から再構成できない。したがって ILLEGIT 判定は
「手動 mode override が無かったならば違反」という条件付きである。
逆に LEGIT_ALLOW_BY_DEFAULT 側はこの自由度に影響されない
(override は LIVE 方向にしか効かないため) — **結論の向きは非対称に安全**。

使用:
    python3 tools/roster_d_class_estimand_audit.py
    python3 tools/roster_d_class_estimand_audit.py --json
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent

# Phase-0 三層化 (`_SHADOW_MODE` + `_ELITE_LIVE` + Phase0 tier gate) を
# 導入した commit の committer time (UTC)。
# 293165ef "feat(v9.0): Phase 0三層化 + BT自動パイプライン" 2026-04-14T17:16:58+09:00
#
# ⚠️ commit 時刻を使うのは Render auto-deploy に数分のラグがあるため
# **保守側**に倒す選択である: commit〜deploy 完了の間の約定は実際には
# ゲート前コードだったが、本ツールは POST_GATE 側 (= 要説明) に落とす。
# 結論 (「D は allow-by-default 期の正当な発火」) を過大に支持しない向き。
TIER_GATE_COMMIT = "293165ef92190868e0722638aabd3efb481474a0"
TIER_GATE_UTC = datetime(2026, 4, 14, 8, 16, 58, tzinfo=timezone.utc)

LEGIT = "LEGIT_ALLOW_BY_DEFAULT"
LEGIT_NO_MECH = "LEGIT_NO_DEMOTE_MECHANISM"
ILLEGIT = "ILLEGIT_DEMOTED_AT_FIRE"
POST_GATE = "POST_GATE_UNEXPLAINED"
UNRESOLVED = "UNRESOLVED_NO_CODE_STATE"
VERDICTS = (LEGIT, LEGIT_NO_MECH, ILLEGIT, POST_GATE, UNRESOLVED)


def _git(*args: str) -> str | None:
    """git を repo root で実行。失敗は None (空文字に畳まない)。"""
    r = subprocess.run(("git", "-C", str(REPO), *args),
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def deploy_history(ref: str = "origin/main") -> list[tuple[datetime, str]]:
    """`modules/demo_trader.py` を触った first-parent commit を時刻昇順で。

    first-parent に限るのは「本番 main に載った状態」だけを見るため
    (side branch の commit は Render にデプロイされていない)。
    """
    log = _git("log", "--first-parent", "--format=%H|%cI", ref,
               "--", "modules/demo_trader.py")
    if log is None:
        raise RuntimeError(f"git log failed for {ref} — 履歴を再構成できない")
    out: list[tuple[datetime, str]] = []
    for line in log.splitlines():
        if "|" not in line:
            continue
        sha, when = line.split("|", 1)
        ts = parse_ts(when)
        if ts is not None:
            out.append((ts, sha))
    if not out:
        raise RuntimeError("demo_trader.py の first-parent 履歴が空")
    out.sort()
    return out


def demote_sets_at(commit: str) -> dict[str, set] | None:
    """commit 時点の `_FORCE_DEMOTED` / `_PAIR_DEMOTED` を AST で読む。

    ⚠️ **空 dict と None を折り畳まない** — 空 dict は「コードは読めたが
    降格集合が存在しない時期」(2026-04 初旬 = 降格機構そのものが未実装)、
    None は「コードが読めない/解析できない」。この 2 つを同じ箱に入れると
    「機構が無かった」を「調べられなかった」と誤読する
    (lesson: `fetch_json` が失敗を {} に潰した 2026-08-30 の監視 blind と同型 —
    自分のツールで同じことをやりかけた)。
    """
    src = _git("show", f"{commit}:modules/demo_trader.py")
    if src is None:
        return None
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    out: dict[str, set] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            name = getattr(target, "id", None) or getattr(target, "attr", None)
            if name in ("_FORCE_DEMOTED", "_PAIR_DEMOTED"):
                try:
                    out[name] = {
                        tuple(x) if isinstance(x, (list, tuple)) else x
                        for x in ast.literal_eval(node.value)
                    }
                except (ValueError, SyntaxError):
                    continue
    return out


def commit_deployed_at(ts: datetime,
                       history: list[tuple[datetime, str]]) -> str | None:
    """ts 時点で本番に載っていた commit (ts 以下で最も新しいもの)。"""
    found = None
    for when, sha in history:
        if when <= ts:
            found = sha
        else:
            break
    return found


def audit_fire(ts: datetime, entry_type: str, instrument: str,
               history: list[tuple[datetime, str]],
               cache: dict[str, dict[str, set] | None]) -> dict[str, Any]:
    commit = commit_deployed_at(ts, history)
    if commit is None:
        return {"verdict": UNRESOLVED, "commit": None,
                "why": "約定時刻より前の main commit が無い"}
    if commit not in cache:
        cache[commit] = demote_sets_at(commit)
    sets = cache[commit]
    if sets is None:
        return {"verdict": UNRESOLVED, "commit": commit[:8],
                "why": "その commit の demo_trader.py が読めない/解析できない"}
    if not sets:
        if ts < TIER_GATE_UTC:
            return {"verdict": LEGIT_NO_MECH, "commit": commit[:8],
                    "why": "降格集合がコードに存在しない時期 "
                           "(`_is_promoted()` が `return True` の全送信期)"}
        return {"verdict": POST_GATE, "commit": commit[:8],
                "why": "tier gate 後なのに降格集合が読めない = 想定外の形"}
    force = entry_type in sets.get("_FORCE_DEMOTED", set())
    pair = (entry_type, instrument) in sets.get("_PAIR_DEMOTED", set())
    if force or pair:
        which = "_FORCE_DEMOTED" if force else "_PAIR_DEMOTED"
        return {"verdict": ILLEGIT, "commit": commit[:8],
                "why": f"約定時刻に {which} に載っていた "
                       "(手動 mode override が無かった前提)"}
    if ts >= TIER_GATE_UTC:
        return {"verdict": POST_GATE, "commit": commit[:8],
                "why": "Phase-0 tier gate 導入後の約定 — 当時の昇格集合の"
                       "再構成が別途必要"}
    return {"verdict": LEGIT, "commit": commit[:8],
            "why": "Phase-0 tier gate 導入前 = `_is_promoted()` 既定 True の "
                   "allow-by-default 期で、降格集合にも不在"}


def audit(fires: dict[str, list[str]],
          ref: str = "origin/main") -> dict[str, Any]:
    """{"entry_type|instrument|direction": [iso ts, ...]} を監査する。"""
    history = deploy_history(ref)
    cache: dict[str, dict[str, set] | None] = {}
    cells: list[dict[str, Any]] = []
    per_fire = Counter()
    for key, stamps in sorted(fires.items()):
        parts = key.split("|")
        if len(parts) != 3:
            raise ValueError(f"cell key は 'type|instrument|direction' 形式: {key!r}")
        entry_type, instrument, direction = parts
        results = []
        for raw in stamps:
            ts = parse_ts(raw)
            if ts is None:
                results.append({"ts": raw, "verdict": UNRESOLVED,
                                "commit": None, "why": "約定時刻が解釈不能"})
                continue
            res = audit_fire(ts, entry_type, instrument, history, cache)
            res["ts"] = ts.isoformat()
            results.append(res)
        for r in results:
            per_fire[r["verdict"]] += 1
        # セル判定 = 最も重い verdict を採る (1 件でも違反があればセルは違反)
        order = {ILLEGIT: 0, POST_GATE: 1, UNRESOLVED: 2,
                 LEGIT: 3, LEGIT_NO_MECH: 4}
        cell_verdict = min((r["verdict"] for r in results),
                           key=lambda v: order.get(v, 9))
        cells.append({
            "entry_type": entry_type, "instrument": instrument,
            "direction": direction, "fires": len(results),
            "cell_verdict": cell_verdict, "per_fire": results,
        })
    per_cell = Counter(c["cell_verdict"] for c in cells)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tier_gate_commit": TIER_GATE_COMMIT[:8],
        "tier_gate_utc": TIER_GATE_UTC.isoformat(),
        "cells": cells,
        "per_cell": {v: per_cell.get(v, 0) for v in VERDICTS},
        "per_fire": {v: per_fire.get(v, 0) for v in VERDICTS},
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = ["# D クラス estimand 監査 — 「本来出てはいけなかった発火」の検証",
             f"_Generated: {report['generated_at']}_", ""]
    lines.append(f"- Phase-0 tier gate: `{report['tier_gate_commit']}` "
                 f"{report['tier_gate_utc'][:19]}Z")
    lines.append(f"- セル判定: {report['per_cell']}")
    lines.append(f"- 約定判定: {report['per_fire']}")
    lines.append("")
    lines.append("| cell | 約定 | セル判定 | 内訳 |")
    lines.append("|---|---|---|---|")
    for c in report["cells"]:
        counts = Counter(r["verdict"] for r in c["per_fire"])
        lines.append(
            f"| {c['entry_type']} × {c['instrument']} × {c['direction']} "
            f"| {c['fires']} | {c['cell_verdict']} "
            f"| {', '.join(f'{k}={v}' for k, v in sorted(counts.items()))} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fires", required=True,
                    help='JSON: {"type|instrument|direction": ["<iso ts>", ...]}')
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    fires = json.loads(Path(args.fires).read_text())
    report = audit(fires, ref=args.ref)
    print(json.dumps(report, ensure_ascii=False, indent=1) if args.json
          else to_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
