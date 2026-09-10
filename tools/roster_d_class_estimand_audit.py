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

判定 (per fire) — **名前に条件性を持たせる**
------------------------------------------
    約定時刻にデプロイされていた `_is_promoted()` の**既定**を AST で再構成し、
    静的降格集合との突き合わせと合わせて判定する。

    PERMITTED_NO_GATE
        promotion gate がコードに存在しない時期 (2026-04-02 の e3d02a0f 系)。
        `self._oanda.open_trade(...)` は**無条件**に呼ばれており、live 送信が
        設計そのものだった。→ ランタイム状態に**不感** (照会するコードが無い)
    PERMITTED_ALL_SEND
        `_is_promoted()` の本体が `return True` 単文
        (8a42d776 "temp: disable OANDA strategy promotion filter — send all
        entries to OANDA" 系)。→ ランタイム状態に**不感** (既定 return より
        手前に照会が無い)
    PERMITTED_STATIC_RUNTIME_UNKNOWN
        `_is_promoted()` が末尾 `return True` の allow-by-default 形 (v6.2) で、
        静的降格集合にも不在。**静的コードは許可していた**が、
        ⚠️ この形は既定 return より**手前**で
        `self._oanda.get_strategy_mode()` と `self._promoted_types[et]["status"]`
        を見るため、`"off"` / `"demoted"` なら**ブロック側**に働く。
        これらはランタイム DB 状態で git から再構成できない
        → **条件付き**判定 (「ランタイム降格が無かったならば許可」)
    CONTRADICTS_STATIC_DEMOTE
        約定時刻に entry_type が `_FORCE_DEMOTED`、または
        (entry_type, instrument) が `_PAIR_DEMOTED` に在籍していた。
        静的方針に反する発火 = バグ、または手動 mode override
    DENY_BY_DEFAULT_UNEXPLAINED
        `_is_promoted()` が deny-by-default 形 (末尾 `return False` 等) の時期の
        発火。昇格の再構成が別途必要 → 要説明
    POST_GATE_UNEXPLAINED
        Phase-0 tier gate 後の約定で、現在の昇格集合にも不在 → 要説明
    UNRESOLVED_NO_CODE_STATE
        その時刻のコード状態を再構成できない

⚠️ Limitation (この監査で潰せない自由度)
----------------------------------------
`_is_promoted()` は既定 return より手前に **2 つのランタイム照会**を持つ:

  1. `self._oanda.get_strategy_mode()` — "off" ならブロック、
     "live"/"sentinel" なら全降格を上書き (**両方向**)
  2. `self._promoted_types[et]["status"] == "demoted"` — ブロック方向のみ

いずれも DB / メモリ状態で git から再構成できない。したがって
`PERMITTED_STATIC_RUNTIME_UNKNOWN` は**条件付き**であり、
**「LEGIT 側は override に不感」という主張は成り立たない**
(2026-09-10 PR #230 Codex P1 で指摘され撤回。ブロック方向の照会を
見落としていた)。無条件に確定するのは `PERMITTED_NO_GATE` と
`PERMITTED_ALL_SEND` の 2 verdict だけである。

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

PERMITTED_NO_GATE = "PERMITTED_NO_GATE"
PERMITTED_ALL_SEND = "PERMITTED_ALL_SEND"
PERMITTED_COND = "PERMITTED_STATIC_RUNTIME_UNKNOWN"
CONTRADICTS = "CONTRADICTS_STATIC_DEMOTE"
DENY_UNEXPLAINED = "DENY_BY_DEFAULT_UNEXPLAINED"
POST_GATE = "POST_GATE_UNEXPLAINED"
UNRESOLVED = "UNRESOLVED_NO_CODE_STATE"
VERDICTS = (PERMITTED_NO_GATE, PERMITTED_ALL_SEND, PERMITTED_COND,
            CONTRADICTS, DENY_UNEXPLAINED, POST_GATE, UNRESOLVED)

# ランタイム状態に**不感**な verdict = 無条件に確定するもの。
UNCONDITIONAL_VERDICTS = frozenset({PERMITTED_NO_GATE, PERMITTED_ALL_SEND})

# 「静的コードは許可していた」と言える verdict (条件付きを含む)。
PERMITTED_VERDICTS = frozenset({PERMITTED_NO_GATE, PERMITTED_ALL_SEND,
                                PERMITTED_COND})

# セル判定の重さ (小さいほど重い)。1 件でも重い判定があればセルはそれ。
VERDICT_SEVERITY = {
    CONTRADICTS: 0,
    DENY_UNEXPLAINED: 1,
    POST_GATE: 2,
    UNRESOLVED: 3,
    PERMITTED_COND: 4,
    PERMITTED_ALL_SEND: 5,
    PERMITTED_NO_GATE: 6,
}

# promotion policy の分類 (`_is_promoted()` の既定)。
POLICY_NO_GATE = "NO_GATE"
POLICY_ALL_SEND = "ALL_SEND"
POLICY_ALLOW_BY_DEFAULT = "ALLOW_BY_DEFAULT"
POLICY_DENY_BY_DEFAULT = "DENY_BY_DEFAULT"
POLICY_UNKNOWN = "UNKNOWN"


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
                    # **fail closed**: 個別代入の解析失敗を `continue` で
                    # 飛ばすと、部分的にしか読めていない集合を「完全に読めた」
                    # として扱い、在籍していたセルを PERMITTED 側へ落とす
                    # (PR #230 Codex P2 2 巡目)。読めない集合が 1 つでも
                    # あれば「コード状態が再構成できない」= None を返す。
                    return None
    return out


def promotion_policy_at(commit: str) -> tuple[str, str]:
    """commit 時点の `_is_promoted()` の**既定**を AST で分類する。

    降格集合の不在は「その 2 定数が無かった」しか示さず、
    `_is_promoted()` が True を返したことを示さない
    (2026-09-10 PR #230 Codex P1 — 04-02 の発火を根拠なく
    `LEGIT_NO_DEMOTE_MECHANISM` と分類していた)。方針そのものを読む。
    """
    src = _git("show", f"{commit}:modules/demo_trader.py")
    if src is None:
        return (POLICY_UNKNOWN, "その commit の demo_trader.py が読めない")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return (POLICY_UNKNOWN, "demo_trader.py が解析できない")
    fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_is_promoted":
            fn = node
    if fn is None:
        # gate 関数が無い時期。`promot` という語が一切無ければ昇格の概念自体が
        # 未実装 = OANDA ミラーは無条件 (実測: e3d02a0f で
        # `self._oanda.open_trade(...)` が if の外にある)。
        if "promot" not in src:
            return (POLICY_NO_GATE,
                    "`_is_promoted` も promot 参照も無い = 昇格ゲート未実装、"
                    "OANDA ミラーは無条件")
        return (POLICY_UNKNOWN,
                "`_is_promoted` 不在だが promot 参照あり — 別名のゲートを"
                "手で確認せよ")
    body = [st for st in fn.body if not isinstance(st, ast.Expr)]
    if not body:
        return (POLICY_UNKNOWN, "`_is_promoted` の本体が空")
    only = body[0]
    if (len(body) == 1 and isinstance(only, ast.Return)
            and isinstance(only.value, ast.Constant)
            and only.value.value is True):
        return (POLICY_ALL_SEND, "`_is_promoted` が `return True` 単文")
    last = body[-1]
    if isinstance(last, ast.Return) and isinstance(last.value, ast.Constant):
        if last.value.value is True:
            return (POLICY_ALLOW_BY_DEFAULT,
                    "`_is_promoted` 末尾が `return True` (guard 通過後の既定許可)")
        return (POLICY_DENY_BY_DEFAULT,
                f"`_is_promoted` 末尾が `return {last.value.value}`")
    return (POLICY_UNKNOWN,
            f"`_is_promoted` 末尾が定数 return でない ({type(last).__name__})")


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
               cache: dict[str, dict[str, set] | None],
               policy_cache: dict[str, tuple[str, str]] | None = None,
               ) -> dict[str, Any]:
    commit = commit_deployed_at(ts, history)
    if commit is None:
        return {"verdict": UNRESOLVED, "commit": None, "policy": POLICY_UNKNOWN,
                "why": "約定時刻より前の main commit が無い"}
    if policy_cache is None:
        policy_cache = {}
    if commit not in policy_cache:
        policy_cache[commit] = promotion_policy_at(commit)
    policy, policy_why = policy_cache[commit]
    if commit not in cache:
        cache[commit] = demote_sets_at(commit)
    sets = cache[commit]

    def out(verdict: str, why: str) -> dict[str, Any]:
        return {"verdict": verdict, "commit": commit[:8], "policy": policy,
                "why": why}

    if policy == POLICY_UNKNOWN:
        return out(UNRESOLVED, f"昇格方針を再構成できない ({policy_why})")
    # ゲートが無い / 全送信の時期は降格集合も参照されないので先に確定する
    # (この 2 つだけがランタイム状態に不感 = 無条件)。
    if policy == POLICY_NO_GATE:
        return out(PERMITTED_NO_GATE, policy_why)
    if policy == POLICY_ALL_SEND:
        return out(PERMITTED_ALL_SEND, policy_why)
    if sets is None:
        return out(UNRESOLVED, "降格集合を読めない/解析できない")
    force = entry_type in sets.get("_FORCE_DEMOTED", set())
    pair = (entry_type, instrument) in sets.get("_PAIR_DEMOTED", set())
    if force or pair:
        which = "_FORCE_DEMOTED" if force else "_PAIR_DEMOTED"
        return out(CONTRADICTS,
                   f"約定時刻に {which} に在籍していた "
                   "(手動 mode override が無かった前提)")
    if ts >= TIER_GATE_UTC:
        return out(POST_GATE,
                   "Phase-0 tier gate 後の約定 — 当時の昇格集合の再構成が別途必要")
    if policy == POLICY_DENY_BY_DEFAULT:
        return out(DENY_UNEXPLAINED,
                   f"{policy_why} — 明示昇格の再構成が別途必要")
    return out(PERMITTED_COND,
               f"{policy_why} かつ静的降格集合に不在。⚠️ ランタイムの "
               "`get_strategy_mode()==\"off\"` / `_promoted_types` の "
               "`status==\"demoted\"` はブロック方向に働くが再構成不能 = 条件付き")


def audit(fires: dict[str, list[str]],
          ref: str = "origin/main") -> dict[str, Any]:
    """{"entry_type|instrument|direction": [iso ts, ...]} を監査する。"""
    history = deploy_history(ref)
    cache: dict[str, dict[str, set] | None] = {}
    policy_cache: dict[str, tuple[str, str]] = {}
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
                                "commit": None, "policy": POLICY_UNKNOWN,
                                "why": "約定時刻が解釈不能"})
                continue
            res = audit_fire(ts, entry_type, instrument, history, cache,
                             policy_cache)
            res["ts"] = ts.isoformat()
            results.append(res)
        for r in results:
            per_fire[r["verdict"]] += 1
        # セル判定 = 最も重い verdict を採る (1 件でも違反があればセルは違反)
        cell_verdict = min((r["verdict"] for r in results),
                           key=lambda v: VERDICT_SEVERITY.get(v, 9))
        cells.append({
            "entry_type": entry_type, "instrument": instrument,
            "direction": direction, "fires": len(results),
            "cell_verdict": cell_verdict, "per_fire": results,
        })
    per_cell = Counter(c["cell_verdict"] for c in cells)
    n_fires = sum(per_fire.values())
    return {
        "unconditional_permitted_fires": sum(
            per_fire[v] for v in UNCONDITIONAL_VERDICTS),
        "conditional_permitted_fires": per_fire[PERMITTED_COND],
        "contradicting_fires": per_fire[CONTRADICTS],
        "total_fires": n_fires,
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
    lines.append(
        f"- **無条件に許可と確定した約定: {report['unconditional_permitted_fires']}"
        f" / {report['total_fires']}** "
        f"(条件付き {report['conditional_permitted_fires']} / "
        f"静的方針に反する {report['contradicting_fires']})")
    lines.append("  ⚠️ 条件付き = ランタイム降格 (`get_strategy_mode()==\"off\"` / "
                 "`_promoted_types` の `status==\"demoted\"`) はブロック方向に"
                 "働くが git から再構成できない")
    lines.append("")
    lines.append("| cell | 約定 | セル判定 | policy | 内訳 |")
    lines.append("|---|---|---|---|---|")
    for c in report["cells"]:
        counts = Counter(r["verdict"] for r in c["per_fire"])
        pols = sorted({r.get("policy", "") for r in c["per_fire"]})
        lines.append(
            f"| {c['entry_type']} × {c['instrument']} × {c['direction']} "
            f"| {c['fires']} | {c['cell_verdict']} | {', '.join(pols)} "
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
