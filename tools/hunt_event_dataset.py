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
    そのため `entry_time` 以外が完全一致する行が大量にある。
    `sr_audit.stage_a_audit` は `n = len(events)` を Wilson / 二項検定の
    分母に直接使うので、素通しすると N が膨らむ。
    identity = `entry_time` を除く全フィールドの完全一致 + **時間窓**
    (`DEDUP_WINDOW_SEC`、下記)、代表行は窓内で**最も早い** `entry_time` の行。

    実測 (as-of 2026-09-22、**provenance フィルタ後 69,576 行**、
    identity ごとに時刻昇順へ並べた anchored 窓):
      - **既定 1h**: collapse **48,884 行 (70.3%)** → 相異なる観測 **20,692**
        = **3.36 倍**
      - 窓なし (最も攻撃的な端): collapse 59,630 行 (85.7%) → 9,946 = 7.00 倍
    ⚠️ **膨張率は窓に依存するので単一の点推定として引用してはいけない** —
    窓と基数を必ず併記する。
    🔴 **旧値 (57,656 / 82.9% / 5.8 倍) は撤回** (Codex P2、PR #272 第10巡)。
    あれは identity に post-hoc の outcome 列が残っていた頃の推定量の出力で、
    **現行のどのモードにも一致しない**。数値は estimator が変わった瞬間に
    陳腐化する ⇒ **この契約節の数字は §D3 の感度表と同じ estimator で
    再計算したものだけを書く**。

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

# D3: 独立観測の identity から外すフィールド。
#
# `entry_time` は logger が書込み時刻を入れる列。
# `reversal` / `actual_outcome` / `actual_pnl_pips` は **post-hoc に付与される
# outcome 列**で、signal 時点の観測ではない (PR #272 Codex P2)。
# ⚠️ これを identity に残すと、labeler が同一 signal の反復発火に**異なるラベルを
# 付けた瞬間に dedup が collapse をやめ**、N 膨張が復活する — しかも
# **validity gate が通り始めるのと同じタイミングで**。今日は全行 None なので
# 実害が出ず、「意味を持つようになった日」に静かに壊れる形だった。
# identity は signal 時点のフィールドだけで組む。
IDENTITY_EXCLUDE = frozenset({
    "entry_time", "reversal", "actual_outcome", "actual_pnl_pips",
})

# collapse したグループ内で outcome が食い違ったら、それは labeler のバグであって
# 黙って片方を採る場面ではない。会計に載せて validity gate で止める。
OUTCOME_FIELDS = ("reversal", "actual_outcome", "actual_pnl_pips")

# dedup の粒度は**母集団ごとに違う** (PR #272 Codex P2、3 巡目)。
# `entry_time` が何を指すかが母集団で異なるのが理由:
#   "signal" — hunt_events: engine が同じ bar を tick ごとに再評価し、`entry_time` は
#              **書込み時刻**。同一 bar の反復発火は 1 観測なので除外する
#   "bar"    — sr_audit の benchmark (「SR 近接 全 bar」): 1 bar 1 行で
#              `entry_time` は **bar の identity**。除外すると相異なる bar が
#              全部 1 群に潰れ、偽の outcome 衝突が出て N が床を割る
# どちらも outcome 列は除外する (post-hoc なので観測の identity ではない)。
DEDUP_MODES = {
    "signal": IDENTITY_EXCLUDE,
    "bar": frozenset(OUTCOME_FIELDS),
}

# "signal" 粒度は `entry_time` を identity から外すので、**時間窓で区切らないと
# データセット全期間にわたって payload 一致だけで潰れる** (PR #272 Codex P2、5 巡目)。
# 実測: 同一 identity の群が **2026-05-01〜2026-07-08 = 68.5 日**にまたがる例があり、
# これは単一 bar の tick 再評価では説明できない = **別観測を消している**。
#
# 窓は anchored (先頭からの経過で区切る、chaining しない)。既定 3600 秒 =
# sr 系が使う最長 bar (1h) — 同一 bar の再評価はその長さを超えられない、という
# 機構からの導出であって、データに合わせた較正ではない。
#
# ⚠️ **distinct 数は窓に強く依存する。**
# 実測 (as-of 2026-09-19、**provenance フィルタ後 69,576 行** = collected 69,577 −
# 合成行 1、**下の anchored 実装で再計算**):
#     15m → 27,565 (2.52x) / 1h → 20,692 (3.36x) /
#     4h → 14,953 (4.65x) / 24h → 11,614 (5.99x) / 無制限 → 9,946 (7.00x)
#   ⇒ **単一の点推定として引用してはいけない。** 窓と基数を併記すること。
#
# 🔴 **旧表 (15m 24,356 / 1h 18,812 / 4h 13,208 / 24h 11,213) は撤回**
# (Codex P2、PR #272 第7巡)。あれは窓を **chaining する**旧実装の出力で、
# 5 巡目に anchored へ変えたとき再計算しなかった。chaining は「窓内に次の行が
# 来る限り窓を延長する」ので**より多く潰す** ⇒ distinct が小さく出る。
# **数値は estimator が変わった瞬間に陳腐化する** — 無制限 (9,946) だけが
# 一致していたのは、その列が窓に依存しない唯一の列だったから。
# 🔑 読み手への含意: 1h 基準の膨張係数 3.36 倍 (= 69,576/20,692) は
# [[hunt-events-dataset-readout-2026-09-19]] と registry の値と一致する。
DEDUP_WINDOW_SEC = 3600.0

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


def identity(row: dict[str, Any], *, dedup: str = "signal") -> tuple:
    """D3: 独立観測の identity。`dedup` で粒度を選ぶ (`DEDUP_MODES` 参照)。

    - `"signal"` (既定): 書込み時刻 + post-hoc outcome 列を除く
    - `"bar"`: outcome 列のみ除く (`entry_time` = bar identity を保つ)
    """
    try:
        exclude = DEDUP_MODES[dedup]
    except KeyError:
        raise ValueError(
            f"unknown dedup mode: {dedup!r} (expected {sorted(DEDUP_MODES)})") from None
    return tuple(sorted(
        (k, json.dumps(v, sort_keys=True))
        for k, v in row.items() if k not in exclude
    ))


def merge_outcomes(
    group: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, list]]:
    """グループの outcome 列を**フィールドごとに**マージする。

    Returns (マージ済み outcome, 不一致フィールド → 相異なる非 None 値)。

    ⚠️ 2026-09-19 (PR #272 Codex P2、4 巡目): タプル一致で衝突判定すると
    `(True, None, None)` と `(True, "WIN", 10.0)` が**衝突扱い**になる。
    logger は 3 列を独立に初期化し、反復発火のうち**実約定に対応するのは
    1 本だけ**という部分帰属が自然な状態なので、これは正常入力。
    ⇒ フィールドごとに非 None 値を集め、**同一フィールドに相異なる非 None 値が
    2 つ以上あるときだけ**衝突とする。
    """
    merged: dict[str, Any] = {}
    disagreements: dict[str, list] = {}
    for field in OUTCOME_FIELDS:
        values = []
        for row in group:
            v = row.get(field)
            if v is None:
                continue
            if v not in values:
                values.append(v)
        if len(values) > 1:
            disagreements[field] = values
        elif values:
            merged[field] = values[0]
    return merged, disagreements


def _dt_min():
    """Sort sentinel: rows whose entry_time cannot be parsed sort LAST.

    They are kept as separate observations either way (see below), so their
    position only needs to be deterministic.
    """
    import datetime as _dt
    return _dt.datetime.min


def _parse_entry_time(row: dict[str, Any]):
    """Parse `entry_time` to a tz-NAIVE UTC datetime, or None.

    Normalizing here rather than at each call site is deliberate: both the
    per-identity sort and the window arithmetic `(ts - anchor)` compare these
    values, and Python raises `TypeError: can't compare offset-naive and
    offset-aware datetimes` when a corpus mixes the two forms.  One
    differently formatted event would abort the whole audit (Codex P2,
    PR #272 第9巡).

    A naive timestamp is treated as UTC, which is what
    `modules/hunt_event_logger.py` writes; an aware one is converted to UTC
    and then made naive so the two forms are directly comparable.
    """
    raw = row.get("entry_time")
    if not isinstance(raw, str):
        return None
    try:
        import datetime as _dt
        ts = _dt.datetime.fromisoformat(raw)
    except ValueError:
        return None
    if ts.tzinfo is not None:
        ts = ts.astimezone(_dt.timezone.utc).replace(tzinfo=None)
    return ts


def collapse_repeats(
    rows: Iterable[dict[str, Any]],
    *,
    dedup: str = "signal",
    window_sec: "float | None" = DEDUP_WINDOW_SEC,
) -> tuple[list[dict[str, Any]], int, list[dict[str, Any]]]:
    """D3: 同一 signal identity の行を 1 件に潰す。

    Returns (代表行, 潰した行数, ラベル衝突リスト)。

    代表は最初に現れた行 (= 最も早い書込み時刻) をベースに、グループ内に
    非 None の outcome があればそれを引き継ぐ — 反復発火のうち 1 本だけが
    labeler に拾われるのが自然な形なので、代表が未ラベルだからといって
    観測を捨てない。

    **非 None の outcome が 2 通り以上あれば衝突**として返す。同一 signal に
    2 つの結果が付くのは labeler のバグであり、黙って片方を採ってはいけない。
    """
    # identity だけでなく **時間窓** でも区切る (anchored)。窓を跨いだ同一 payload は
    # 別観測として残す — payload 一致は「同じ bar の再評価」の十分条件ではない。
    #
    # ⚠️ anchored な窓は**行の到着順に依存する**。古い timestamp が後から来ると
    # `(ts - anchor)` が負になり、どれだけ離れていても必ず現在の窓に入る
    # (24 時間離れた 2 観測が Jan2 → Jan1 の順なら 1 件に潰れる)。`load_rows()` は
    # 入力順を保つので、**identity ごとに時刻昇順へ並べてから**窓を張る
    # (Codex P2、PR #272 第8巡)。実測: committed データセットで
    # **9,946 identity のうち 205 件が逆順ペアを含む** (計 429 箇所) ため、
    # これは理論上の懸念ではなく現に N を過小計数していた。
    # 並びは stable sort なので同時刻の行の相対順序 (= 代表行の選択) は変わらない。
    rows = list(rows)
    if window_sec is not None:
        decorated = []
        for i, r in enumerate(rows):
            ts = _parse_entry_time(r)
            decorated.append(((ts is None, ts or _dt_min(), i), r))
        decorated.sort(key=lambda pair: pair[0])
        rows = [r for _, r in decorated]
    order: list[tuple] = []
    groups: dict[tuple, list[dict[str, Any]]] = {}
    anchors: dict[tuple, Any] = {}     # identity -> 現在の窓の起点
    seq: dict[tuple, int] = {}         # identity -> 窓の連番
    repeats = 0
    for row in rows:
        base = identity(row, dedup=dedup)
        if window_sec is None:
            key = base
        else:
            ts = _parse_entry_time(row)
            if ts is None:
                # 時刻が読めない行は窓を張れないので、必ず別観測として残す
                # (黙って潰すと観測を消す方向に倒れる)。
                key = (base, "no-entry-time", len(order))
            else:
                anchor = anchors.get(base)
                if anchor is None or (ts - anchor).total_seconds() > window_sec:
                    anchors[base] = ts
                    seq[base] = seq.get(base, -1) + 1
                key = (base, seq[base])
        if key in groups:
            repeats += 1
            groups[key].append(row)
        else:
            order.append(key)
            groups[key] = [row]

    out: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for key in order:
        group = groups[key]
        rep = dict(group[0])
        merged, disagreements = merge_outcomes(group)
        if disagreements:
            conflicts.append({
                "n_rows": len(group),
                "fields": {f: sorted(map(str, v)) for f, v in disagreements.items()},
                "representative_entry_time": rep.get("entry_time"),
                # cell 絞りの前に検出されるので、gate では **選択セルに属する
                # 衝突だけ**を数える (PR #272 Codex P2、4 巡目)。
                "representative": rep,
            })
        else:
            rep.update(merged)
        out.append(rep)
    return out, repeats, conflicts


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
    enforce_provenance: bool = True,
    dedup: str = "signal",
    window_sec: "float | None" = DEDUP_WINDOW_SEC,
) -> dict[str, Any]:
    """読み取り〜validity gate までを 1 本にした入口。

    Returns a dict with:
        events        — 統計にかけてよい母集団 (provenance/dedup/cell/label 済)
        accounting    — 各層で何行落ちたかの内訳 (readout 用)
        ok            — validity gate 通過か
        blocked_reasons — 通過しなかった理由 (空なら ok)

    `enforce_provenance=False` で D2 (feed-symbol 不変条件) を外す。
    `dedup` で独立観測の粒度を選ぶ ("signal" / "bar"、`DEDUP_MODES` 参照)。
    `window_sec` で collapse の時間窓を選ぶ (既定 `DEDUP_WINDOW_SEC`、None で無制限)。

    ⚠️ **D2 は hunt logger 固有の規約であって母集団一般の規約ではない**
    (PR #272 Codex P2)。`sr_audit` の benchmark は「SR 近接 全 bar の reversal」
    という**別母集団**で、`modules/hunt_event_logger.py` 由来とは限らない。
    そこに feed-symbol を強制すると、ラベル完備で妥当な baseline (repo 慣行の
    `instrument: "USD_JPY"` 表記) が全行隔離されて exit 5 になる。

    ⇒ **対称にすべきなのは「ラベル検査」と「独立観測の単位」で、
    「provenance 規約」は母集団ごとに違う。** 直前の修正で benchmark を
    同じ `prepare()` に通したのは、対称性を 1 段取り違えていた。
    """
    raw = load_rows(spec)
    if enforce_provenance:
        collected, quarantined = split_provenance(raw)
    else:
        collected, quarantined = list(raw), []
    # A row whose `entry_time` cannot be parsed CANNOT have the dedup window
    # applied to it, so `collapse_repeats` keeps each one as its own
    # observation.  That is the right call inside the collapser (never delete
    # an observation silently) and the WRONG direction for a promotion gate:
    # 30 identical labeled repeats with `entry_time: "bad"` would enter the
    # population as 30 independent events and manufacture significance
    # (Codex P2, PR #272 第11巡).  Fail closed here instead — the population
    # must only contain rows whose independence we can actually check.
    # Current corpus: 0 such rows, so no published figure moves.
    if window_sec is not None:
        undatable = [r for r in collected if _parse_entry_time(r) is None]
        if undatable:
            keep = {id(r) for r in collected} - {id(r) for r in undatable}
            collected = [r for r in collected if id(r) in keep]
    else:
        undatable = []
    deduped, repeats, conflicts = collapse_repeats(
        collected, dedup=dedup, window_sec=window_sec)
    cell = select_cell(deduped, pair=pair, side=side)
    labeled, unlabeled = split_labels(cell)

    # ⚠️ 衝突は cell 絞りの**前**に検出されるので、そのまま gate に使うと
    # 別ペア/別 side の衝突 1 件で無関係なセルが DATA-BLOCKED になる
    # (PR #272 Codex P2、4 巡目)。選択セルに属する衝突だけを数える。
    cell_conflicts = [
        c for c in conflicts
        if select_cell([c["representative"]], pair=pair, side=side)
    ]

    reasons: list[str] = []
    if not raw:
        reasons.append("dataset is empty")
    if undatable:
        reasons.append(
            f"{len(undatable)} row(s) have a missing/unparseable `entry_time` "
            "— 独立観測の窓を当てられないので母集団に入れない (各行を独立と "
            "数えると N が水増しされ偽の有意が出る)"
        )
    if cell_conflicts:
        reasons.append(
            f"{len(cell_conflicts)} signal group(s) in this cell carry "
            "conflicting outcomes — 同一 signal の同一フィールドに相異なる "
            "非 None 値がある = labeler のバグ (黙って片方を採らない)"
        )
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
            "quarantined_undatable": len(undatable),
            "collapsed_repeats": repeats,
            "outcome_conflicts": len(cell_conflicts),
            "outcome_conflicts_all_cells": len(conflicts),
            "distinct_observations": len(deduped),
            "in_cell": len(cell),
            "labeled": len(labeled),
            "unlabeled": len(unlabeled),
            "pair": pair,
            "side": side,
            "labeled_n_floor": labeled_n_floor,
            "enforce_provenance": enforce_provenance,
            "dedup": dedup,
            "dedup_window_sec": window_sec,
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
