#!/usr/bin/env python3
"""E23 pass-1: イベント列挙 + Gate A/B 判定 (forward 非接触).

位置づけ
--------
pre-reg 🔒 `knowledge-base/wiki/decisions/e23-cb-text-explore-prereg-2026-09-10.md`
§9-2 の pass-1。pass-0 (コーパス census、コミット済) の後段。

**firewall (family C §7 の明文 pin を踏襲)**: 本ハーネスの成果物に
**per-date の forward 値を一切含めない**。価格を開くのは
  (a) t0 を「valid D1」へ写像するための D1 カレンダー構築
  (b) Gate A (headroom) が要求する **シグナル非依存の無条件 |fwd5| 分布** (集計値のみ)
の 2 用途に限る。イベント×リターンの結合統計は pass-2 の領分で、ここでは計算しない。

凍結仕様 (pre-reg §2/§3 転記)
-----------------------------
- D1 再構築: UTC-day group / valid = n_bars >= 24 かつ weekday < 5 / close = 最終バー close
- ΔNH_t = NH_t − NH_{t−1} (同一中銀・同一文書種の直前声明比)
- staleness: 直前声明との間隔 > 120 暦日 → void
- イベント = ΔNH != 0 (閾値・大きさ加重なし、等加重)
- t0 = 公表 UTC 日。valid D1 でなければ**次の** valid D1
- horizon PRIMARY = +5 valid D1
- CB→ペアと方向: ECB→EUR_USD(+d) / BOE→GBP_USD(+d) / BoJ→USD_JPY(−d) / Fed→EUR_USD(−d)
- 同日衝突: Fed と ECB が同一 UTC 日 → **両イベント void**
- Gate A: 各生存ペアの無条件 median |fwd5| >= 10 x RT(point)
- Gate B: pooled イベント N >= 100 (未達 = UNDERPOWERED、窓拡張・閾値救済禁止)

価格ソース (family C と同じ規律)
--------------------------------
`{PAIR}_15m_2014_2026.parquet` (**gap-fill 済の凍結体系ファイル**) のみを使う。
bare `{PAIR}_15m.parquet` は直近ローリングキャッシュ (2026-06 以降しか無い) のため**使用禁止**。
初回実行で sha256 + 行数の manifest を生成し、以後は毎回 assert する。

使い方
------
    python3 tools/e23_pass1_events.py --price-dir /abs/path/to/data/cache/massive
    python3 tools/e23_pass1_events.py --price-dir ... --freeze-manifest   # 初回 pin 生成
    python3 tools/e23_pass1_events.py --price-dir ... --write             # KB へ出力
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from e23_corpus_fetch import EXPLORE_END, EXPLORE_START, load_corpus  # noqa: E402
from e23_lexicon_apel_grimaldi import net_hawkishness  # noqa: E402

# pre-reg §2 凍結: CB → (pair, 方向係数)
CB_MAP = {
    "ecb": ("EUR_USD", +1),
    "boe": ("GBP_USD", +1),
    "boj": ("USD_JPY", -1),
    "fed": ("EUR_USD", -1),
}
PAIRS = ("EUR_USD", "GBP_USD", "USD_JPY")

STALENESS_VOID_DAYS = 120
HORIZON_D1 = 5
GATE_B_N = 100
MIN_BARS_PER_D1 = 24

# per-pair RT friction (pips) — wiki/analyses/friction-analysis.md
RT_PIPS = {"EUR_USD": 2.00, "GBP_USD": 4.53, "USD_JPY": 2.14}
GATE_A_MULTIPLE = 10
PIP = {"EUR_USD": 0.0001, "GBP_USD": 0.0001, "USD_JPY": 0.01}

PRICE_FILE_TMPL = "{pair}_15m_2014_2026.parquet"
MANIFEST = ROOT / "knowledge-base" / "raw" / "bt-results" / "e23" / \
    "data_freeze_manifest_2026-09-15.json"
OUT_MD = ROOT / "knowledge-base" / "raw" / "analysis" / "e23-pass1-events-2026-09-15.md"
OUT_JSON = ROOT / "knowledge-base" / "raw" / "analysis" / "e23-pass1-events-2026-09-15.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def build_d1(price_dir: Path, pair: str) -> tuple[list[date], dict[date, float], dict]:
    """15m バーから UTC-day D1 を再構築 (valid = n_bars>=24 かつ平日)."""
    import pandas as pd

    path = price_dir / PRICE_FILE_TMPL.format(pair=pair)
    df = pd.read_parquet(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        raise SystemExit(f"{path}: DatetimeIndex ではない")
    idx = df.index.tz_convert("UTC") if df.index.tz is not None else \
        df.index.tz_localize("UTC")
    days = idx.date
    grouped = df.groupby(days)
    closes: dict[date, float] = {}
    n_void_bars = n_void_weekend = 0
    for day, g in grouped:
        if day.weekday() >= 5:
            n_void_weekend += 1
            continue
        if len(g) < MIN_BARS_PER_D1:
            n_void_bars += 1
            continue
        closes[day] = float(g["Close"].iloc[-1])
    valid = sorted(closes)
    stats = {
        "path": str(path),
        "rows": int(len(df)),
        "sha256": _sha256(path),
        "span": [str(idx.min()), str(idx.max())],
        "valid_d1": len(valid),
        "void_low_bars": n_void_bars,
        "void_weekend": n_void_weekend,
    }
    return valid, closes, stats


def unconditional_fwd5(valid: list[date], closes: dict[date, float],
                       pair: str) -> dict:
    """Gate A 用の**シグナル非依存**な無条件 |fwd5| 分布 (集計値のみ)."""
    moves = []
    for i in range(len(valid) - HORIZON_D1):
        a, b = valid[i], valid[i + HORIZON_D1]
        if (b - a).days > 14:          # 長期休場跨ぎは void (family C の span 規約準拠)
            continue
        moves.append(abs(closes[b] - closes[a]) / PIP[pair])
    moves.sort()
    if not moves:
        return {"n": 0}
    return {
        "n": len(moves),
        "median_abs_fwd5_pips": round(statistics.median(moves), 2),
        "p25": round(moves[len(moves) // 4], 2),
        "p75": round(moves[3 * len(moves) // 4], 2),
        "rt_pips": RT_PIPS[pair],
        "gate_a_threshold_pips": GATE_A_MULTIPLE * RT_PIPS[pair],
        "gate_a_pass": statistics.median(moves) >= GATE_A_MULTIPLE * RT_PIPS[pair],
    }


def enumerate_events(docs: list[dict], d1: dict[str, tuple[list[date], dict]]) -> dict:
    explore = sorted(
        (r for r in docs
         if EXPLORE_START <= _d(r["date"]) <= EXPLORE_END and r.get("n_chars", 0) > 0),
        key=lambda r: (r["cb"], r["date"]),
    )
    by_cb: dict[str, list[dict]] = {}
    for r in explore:
        by_cb.setdefault(r["cb"], []).append(r)

    # 同日衝突 (Fed x ECB) — 両イベント void
    fed_days = {r["date"] for r in by_cb.get("fed", [])}
    ecb_days = {r["date"] for r in by_cb.get("ecb", [])}
    collision_days = fed_days & ecb_days

    events: list[dict] = []
    voids: dict[str, int] = {}
    nh_zero_docs = 0

    def bump(k: str) -> None:
        voids[k] = voids.get(k, 0) + 1

    for cb, recs in by_cb.items():
        pair, sign = CB_MAP[cb]
        valid, closes = d1[pair]
        prev = None
        for r in recs:
            nh = net_hawkishness(r["text"])
            if nh == 0.0:
                nh_zero_docs += 1
            if prev is None:
                prev = (r, nh)
                continue
            prev_rec, prev_nh = prev
            prev = (r, nh)
            gap = (_d(r["date"]) - _d(prev_rec["date"])).days
            if gap > STALENESS_VOID_DAYS:
                bump(f"{cb}:staleness_gt_{STALENESS_VOID_DAYS}d")
                continue
            delta = nh - prev_nh
            if delta == 0.0:
                bump(f"{cb}:delta_nh_zero")
                continue
            if r["date"] in collision_days and cb in ("fed", "ecb"):
                bump(f"{cb}:fed_ecb_same_day")
                continue
            pub = _d(r["date"])
            t0 = next((v for v in valid if v >= pub), None)
            if t0 is None:
                bump(f"{cb}:no_valid_t0")
                continue
            i = valid.index(t0)
            if i + HORIZON_D1 >= len(valid):
                bump(f"{cb}:no_t0_plus_h")
                continue
            events.append({
                "cb": cb,
                "statement_date": r["date"],
                "t0_d1": t0.isoformat(),
                "pair": pair,
                # d = 方向写像後の符号のみ (|ΔNH| は等加重なので使わない)
                "d": sign * (1 if delta > 0 else -1),
                "delta_nh_sign": 1 if delta > 0 else -1,
                "gap_days": gap,
            })

    events.sort(key=lambda e: (e["statement_date"], e["cb"]))
    return {
        "n_docs_explore_usable": len(explore),
        "n_docs_nh_zero": nh_zero_docs,
        "collision_days": sorted(collision_days),
        "voids": dict(sorted(voids.items())),
        "events": events,
    }


def run(price_dir: Path, freeze: bool) -> dict:
    d1: dict[str, tuple[list[date], dict]] = {}
    price_stats: dict[str, dict] = {}
    gate_a: dict[str, dict] = {}
    for pair in PAIRS:
        valid, closes, stats = build_d1(price_dir, pair)
        d1[pair] = (valid, closes)
        price_stats[pair] = stats
        gate_a[pair] = unconditional_fwd5(valid, closes, pair)

    pins = {p: {"sha256": price_stats[p]["sha256"], "rows": price_stats[p]["rows"]}
            for p in PAIRS}
    if freeze:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(
            {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "purpose": "E23 pass-1/pass-2 価格ソースの sha256 + 行数 pin",
             "files": pins}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    elif MANIFEST.exists():
        pinned = json.loads(MANIFEST.read_text())["files"]
        for p in PAIRS:
            if pinned.get(p) != pins[p]:
                raise SystemExit(
                    f"価格ソースが manifest pin と不一致: {p}\n"
                    f"  pinned={pinned.get(p)}\n  actual={pins[p]}")
    else:
        raise SystemExit(f"manifest が無い。初回は --freeze-manifest で pin を作る: "
                         f"{MANIFEST}")

    enum = enumerate_events(load_corpus(), d1)
    n = len(enum["events"])
    gate_a_pairs = {p: gate_a[p]["gate_a_pass"] for p in PAIRS}
    surviving_pairs = [p for p, ok in gate_a_pairs.items() if ok]
    n_after_gate_a = sum(1 for e in enum["events"] if e["pair"] in surviving_pairs)

    if not surviving_pairs:
        verdict = "FAMILY_KILL"        # pre-reg §4 Gate A: 全滅なら family KILL
    elif n_after_gate_a >= GATE_B_N:
        verdict = "PASS_TO_PASS2"
    else:
        verdict = "UNDERPOWERED"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prereg": "knowledge-base/wiki/decisions/"
                  "e23-cb-text-explore-prereg-2026-09-10.md",
        "pass": "pass-1 イベント列挙 (forward 非接触 — 無条件 |fwd5| 集計のみ)",
        "explore_window": [EXPLORE_START.isoformat(), EXPLORE_END.isoformat()],
        "price_sources": price_stats,
        "gate_a": gate_a,
        "gate_a_surviving_pairs": surviving_pairs,
        "gate_b": {"threshold": GATE_B_N, "n_events_all": n,
                   "n_events_after_gate_a": n_after_gate_a,
                   "pass": n_after_gate_a >= GATE_B_N},
        "enumeration": enum,
        "verdict": verdict,
    }


def render_md(c: dict) -> str:
    enum = c["enumeration"]
    ev = enum["events"]
    per_cb = {}
    for e in ev:
        per_cb[e["cb"]] = per_cb.get(e["cb"], 0) + 1
    lines = [
        "# E23 pass-1 イベント列挙 — 2026-09-15",
        "",
        "**pre-reg**: [[e23-cb-text-explore-prereg-2026-09-10]] 🔒 / **pass**: " + c["pass"],
        f"**生成**: `tools/e23_pass1_events.py` @ {c['generated_at']}",
        "",
        "> **firewall**: 本成果物に per-date の forward 値は含まれない。"
        "価格は (a) t0→valid D1 写像 (b) Gate A の**シグナル非依存**な無条件 |fwd5| 集計 "
        "の 2 用途のみに使用。イベント×リターン結合は pass-2 の領分。",
        "",
        f"## verdict: **{c['verdict']}**",
        "",
        f"- Gate A 生存ペア: {', '.join(c['gate_a_surviving_pairs']) or 'なし'}",
        f"- Gate B: pooled イベント **N = {c['gate_b']['n_events_after_gate_a']}** "
        f"(閾値 {c['gate_b']['threshold']}) → "
        f"{'✅ PASS' if c['gate_b']['pass'] else '❌ 未達 = UNDERPOWERED'}",
        "",
        "## Gate A (headroom): 無条件 median |fwd5| ≥ 10 × RT",
        "",
        "| pair | valid D1 | median \\|fwd5\\| (pips) | p25 / p75 | RT | 閾値 | gate |",
        "|---|---|---|---|---|---|---|",
    ]
    for pair, g in c["gate_a"].items():
        lines.append(
            f"| {pair} | {c['price_sources'][pair]['valid_d1']} | "
            f"{g['median_abs_fwd5_pips']} | {g['p25']} / {g['p75']} | "
            f"{g['rt_pips']} | {g['gate_a_threshold_pips']} | "
            f"{'✅' if g['gate_a_pass'] else '❌'} |")
    lines += [
        "",
        "## イベント内訳",
        "",
        f"- explore 窓の使用可能文書 {enum['n_docs_explore_usable']} 件 / "
        f"うち NH = 0 の文書 **{enum['n_docs_nh_zero']}** 件",
        f"- 列挙イベント (全ペア) **{c['gate_b']['n_events_all']}** 件: "
        + (", ".join(f"{k} {v}" for k, v in sorted(per_cb.items())) or "なし"),
        f"- Fed/ECB 同日 (両 void): {len(enum['collision_days'])} 日",
        "",
        "### void 内訳",
        "",
        "| 理由 | 件数 |",
        "|---|---|",
    ]
    for k, v in enum["voids"].items():
        lines.append(f"| `{k}` | {v} |")
    lines += [
        "",
        "## 価格ソース (sha256 pin)",
        "",
        "| pair | file | rows | sha256 (先頭16) |",
        "|---|---|---|---|",
    ]
    for pair, s in c["price_sources"].items():
        lines.append(f"| {pair} | `{Path(s['path']).name}` | {s['rows']} | "
                     f"`{s['sha256'][:16]}` |")
    lines += ["", "## イベント一覧 (forward 値なし)", "",
              "| # | 声明日 | CB | t0 (valid D1) | pair | d |", "|---|---|---|---|---|---|"]
    for i, e in enumerate(ev, 1):
        lines.append(f"| {i} | {e['statement_date']} | {e['cb']} | {e['t0_d1']} | "
                     f"{e['pair']} | {e['d']:+d} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--price-dir", required=True, type=Path,
                    help="{PAIR}_15m_2014_2026.parquet が置かれたディレクトリ "
                         "(bare *_15m.parquet は使用禁止)")
    ap.add_argument("--freeze-manifest", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    c = run(args.price_dir, args.freeze_manifest)
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
