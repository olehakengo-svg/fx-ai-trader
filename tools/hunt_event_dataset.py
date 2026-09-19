"""`knowledge-base/raw/hunt_events/` の読み手 (2026-09-19、rule:R3)。

背景 — 書き手だけがあって読み手が無かった
--------------------------------------
`modules/hunt_event_logger.py` は 2026-04-28 から 89 日分 / 69,577 行を
`raw/hunt_events/*.jsonl` に書き続けてきたが、documented consumer である
`tools/sr_audit.py` は **一度もこのデータセットを読めていなかった**
(`raw/audits/sr_audit_*` の出力が 1 件も存在しない)。PR #253 / #264 の
connector レビュー指摘を起点に実査したところ、読み手側に 5 層の欠陥が
積み上がっていた (詳細と実測値:
`knowledge-base/wiki/analyses/hunt-events-dataset-readout-2026-09-19.md`)。

本モジュールはその読み手を 1 箇所に集約し、**観測データセットが名乗る
estimand を実際に測れる状態か**を読み取り時に判定する。

凍結した 4 つの読み取り規約
-------------------------
D1. **形式** — データセットは JSONL。`json.loads(whole_file)` は 2 行目で
    必ず落ちる。`load_rows()` が JSONL / ディレクトリ / glob を受ける。

D2. **provenance = feed-symbol 不変条件** — 実収集行の `instrument` は
    yfinance の feed symbol (`USDJPY=X` 形式)。実測で 69,577 行中
    **69,576 行が `^[A-Z]{6}=X$` に合致し、残る 1 行が合成行**
    (`modules/hunt_event_logger.py` docstring の例示行そのもの)。
    値ベースの旧署名 (`adx` 整数 ∧ `atr_price == 0.001`) はこの 1 行を
    取りこぼした (adx=18.5 / atr=0.12) が、feed-symbol は**収集経路の
    構造**なので値が変わっても誤らない。
    ⚠️ raw ファイルは観測記録なので**書き換えない** — 除去は読み取り時に行う。

D3. **独立観測の単位** — engine は同じ bar を tick ごとに再評価し、logger は
    評価成功ごとに 1 行書く (`project_engine_reconstruction_live_dedup_dead`)。
    そのため `entry_time` 以外が完全一致する行が実測 **57,656 / 69,577
    (82.9%)** ある。`sr_audit.stage_a_audit` は `n = len(events)` を
    Wilson / 二項検定の分母に直接使うので、素通しすると N が約 5.8 倍に
    膨らむ。identity = `entry_time` を除く全フィールドの完全一致、
    代表行は最初の `entry_time` を持つ行。

D4. **ラベル付き行のみが母集団** — `reversal` が None の行は
    「反転しなかった観測」ではなく「**まだ観測されていない**」。
    旧実装の `sum(1 for e in events if e.get("reversal"))` は None を
    分子から落としつつ分母には数えるので、未ラベル行は自動的に敗北票に
    なる。実測では `reversal` が **69,577 行すべて None** = 分子が
    構造的にゼロ。約束されていた `tools/attribute_hunt_outcomes.py`
    (logger docstring が "deferred" と書いた labeler) は 144 日経っても
    存在しない。未ラベル行は分母から除外し、残 N で validity gate を引く。
"""
from __future__ import annotations

import glob as _glob
import json
import re
from pathlib import Path
from typing import Any, Iterable

# D2: 実収集行の instrument は yfinance feed symbol。
FEED_SYMBOL_PAT = re.compile(r"^[A-Z]{6}=X$")

# D3: 独立観測の identity から外すフィールド (logger が書込み時刻を入れる列)。
IDENTITY_EXCLUDE = frozenset({"entry_time"})

# D4: ラベル付き行がこれを下回れば verdict を出さない。
# Rule 1 の N>=30 と同じ床 (CLAUDE.md 判断プロトコル)。
LABELED_N_FLOOR = 30

# CLI の --side (bull/bear) と行の side 列 (support/resistance) の対応。
# support を突いてからの反転 = 上方向 = bull。
SIDE_ALIASES = {
    "bull": "support",
    "bear": "resistance",
    "support": "support",
    "resistance": "resistance",
}


def _iter_paths(spec: str | Path) -> list[Path]:
    """`.jsonl` ファイル / ディレクトリ / glob パターンを受ける。"""
    p = Path(spec)
    if p.is_dir():
        return sorted(p.glob("*.jsonl"))
    if p.exists():
        return [p]
    matches = sorted(Path(m) for m in _glob.glob(str(spec)))
    if not matches:
        raise FileNotFoundError(f"no hunt-event files matched: {spec}")
    return matches


def load_rows(spec: str | Path) -> list[dict[str, Any]]:
    """D1: JSONL を行単位で読む。空行はスキップ、壊れた行は例外にする。

    `json.loads(path.read_text())` (旧 sr_audit の実装) はデータセットが
    JSONL なので必ず `Extra data: line 2` で落ちる。
    """
    rows: list[dict[str, Any]] = []
    for path in _iter_paths(spec):
        text = path.read_text(encoding="utf-8")
        stripped = text.lstrip()
        # 単一 JSON ドキュメントも受ける — 配列 `[...]` と wrapper `{"events": [...]}`
        # の両方 (旧 sr_audit CLI が受けていた形。2026-09-19 の初版は `[` だけを
        # 見ていたため wrapper 入力が 1 event 扱いで隔離される回帰があった、
        # PR #272 Codex P2)。JSONL の 1 行目も `{` で始まるので、
        # **ドキュメント全体が 1 個の JSON として読めるか**で分岐する。
        if stripped[:1] in ("[", "{"):
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = None          # JSONL (複数行の JSON オブジェクト)
            if isinstance(payload, list):
                rows.extend(payload)
                continue
            if isinstance(payload, dict) and "events" in payload:
                rows.extend(payload["events"])
                continue
            # dict だが wrapper ではない = **1 行だけの JSONL**。下の行単位に落とす
            # (ここで raise すると 1 行ファイルが読めなくなる)。
        for lineno, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno} is not valid JSON: {exc}") from exc
    return rows


def split_provenance(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """D2: (実収集行, 隔離行) に分ける。feed-symbol 不変条件で判定。"""
    collected: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    for row in rows:
        inst = row.get("instrument")
        if isinstance(inst, str) and FEED_SYMBOL_PAT.match(inst):
            collected.append(row)
        else:
            quarantined.append(row)
    return collected, quarantined


def identity(row: dict[str, Any]) -> tuple:
    """D3: 独立観測の identity — `entry_time` 以外の全フィールド。"""
    return tuple(sorted(
        (k, json.dumps(v, sort_keys=True))
        for k, v in row.items() if k not in IDENTITY_EXCLUDE
    ))


def collapse_repeats(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """D3: 同一 identity の行を 1 件に潰す。

    Returns (代表行のリスト, 潰した行数)。代表は最初に現れた行 =
    最も早い書込み時刻の評価。
    """
    seen: dict[tuple, dict[str, Any]] = {}
    repeats = 0
    for row in rows:
        key = identity(row)
        if key in seen:
            repeats += 1
            continue
        seen[key] = row
    return list(seen.values()), repeats


def select_cell(
    rows: Iterable[dict[str, Any]],
    *,
    pair: str | None = None,
    side: str | None = None,
) -> list[dict[str, Any]]:
    """pair / side でセルを切り出す。

    旧 sr_audit は `--pair` / `--side` を出力ファイル名と payload に書くだけで
    **母集団を絞っていなかった** — 全ペア pooled の結果に `USD_JPY` という
    ラベルが付いていた (名乗る estimand と測る estimand の不一致)。
    `pair` は `USD_JPY` / `USDJPY=X` の双方を受ける。
    """
    out = list(rows)
    if pair:
        norm = lambda s: str(s).upper().replace("=X", "").replace("_", "")  # noqa: E731
        want = norm(pair)
        out = [r for r in out if norm(r.get("instrument", "")) == want]
    if side and side != "both":
        want_side = SIDE_ALIASES.get(side.lower())
        if want_side is None:
            raise ValueError(f"unknown side: {side!r} (expected {sorted(SIDE_ALIASES)})")
        out = [r for r in out if r.get("side") == want_side]
    return out


def split_labels(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """D4: (ラベル付き行, 未ラベル行) に分ける。`reversal is None` = 未ラベル。"""
    labeled: list[dict[str, Any]] = []
    unlabeled: list[dict[str, Any]] = []
    for row in rows:
        (labeled if row.get("reversal") is not None else unlabeled).append(row)
    return labeled, unlabeled


def prepare(
    spec: str | Path,
    *,
    pair: str | None = None,
    side: str | None = None,
    labeled_n_floor: int = LABELED_N_FLOOR,
) -> dict[str, Any]:
    """読み取り〜validity gate までを 1 本にした入口。

    Returns a dict with:
        events        — 統計にかけてよい母集団 (provenance/dedup/cell/label 済)
        accounting    — 各層で何行落ちたかの内訳 (readout 用)
        ok            — validity gate 通過か
        blocked_reasons — 通過しなかった理由 (空なら ok)
    """
    raw = load_rows(spec)
    collected, quarantined = split_provenance(raw)
    deduped, repeats = collapse_repeats(collected)
    cell = select_cell(deduped, pair=pair, side=side)
    labeled, unlabeled = split_labels(cell)

    reasons: list[str] = []
    if not raw:
        reasons.append("dataset is empty")
    if len(labeled) < labeled_n_floor:
        reasons.append(
            f"labeled rows {len(labeled)} < floor {labeled_n_floor} "
            f"(unlabeled {len(unlabeled)} — `reversal` は "
            "tools/attribute_hunt_outcomes.py が埋める約束のまま未実装)"
        )

    return {
        "events": labeled,
        "ok": not reasons,
        "blocked_reasons": reasons,
        "accounting": {
            "rows_read": len(raw),
            "quarantined_provenance": len(quarantined),
            "collapsed_repeats": repeats,
            "distinct_observations": len(deduped),
            "in_cell": len(cell),
            "labeled": len(labeled),
            "unlabeled": len(unlabeled),
            "pair": pair,
            "side": side,
            "labeled_n_floor": labeled_n_floor,
        },
    }


def _main(argv: list[str] | None = None) -> int:
    """`python3 tools/hunt_event_dataset.py [path]` で会計だけを出す。"""
    import argparse

    ap = argparse.ArgumentParser(description="hunt_events データセットの読み取り会計")
    ap.add_argument("path", nargs="?", default="knowledge-base/raw/hunt_events")
    ap.add_argument("--pair", default=None)
    ap.add_argument("--side", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    result = prepare(args.path, pair=args.pair, side=args.side)
    if args.json:
        print(json.dumps(result["accounting"] | {
            "ok": result["ok"], "blocked_reasons": result["blocked_reasons"]},
            ensure_ascii=False, indent=2))
    else:
        acc = result["accounting"]
        print(f"[hunt_events] rows_read={acc['rows_read']} "
              f"quarantined={acc['quarantined_provenance']} "
              f"repeats_collapsed={acc['collapsed_repeats']} "
              f"distinct={acc['distinct_observations']}")
        print(f"[hunt_events] in_cell={acc['in_cell']} "
              f"labeled={acc['labeled']} unlabeled={acc['unlabeled']}")
        print(f"[hunt_events] validity gate: {'PASS' if result['ok'] else 'DATA-BLOCKED'}")
        for r in result["blocked_reasons"]:
            print(f"  - {r}")
    return 0 if result["ok"] else 5


if __name__ == "__main__":
    raise SystemExit(_main())
