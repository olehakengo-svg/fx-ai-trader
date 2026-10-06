#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E1 first look 用 M15 OHLCV の vendor 欠落を OANDA v20 mid で埋めた**別ディレクトリの複製**を作る。

背景 (2026-10-06、rule:R3 data-pipeline repair、record-only):
  手順書 [[e1-first-look-runbook-2026-09-22]] §2-3b の `--preflight-only` (10-06 実行) が
  評価窓 [t0, cutoff) 内の **内部欠落** を 8/13 pair で検出した (EUR_JPY 553 本 / AUD_USD 237 /
  GBP_JPY 194 / EUR_AUD 96 / EUR_GBP 30 / USD_CHF 7 / USD_JPY 4 / GBP_USD 4、合計 1,125 本)。
  同じ区間を MASSIVE API に 1m / 15m / 1h で直接問い合わせても 0 本 = **vendor 本体の穴**
  (fetch artifact ではない)。穴は平日 00:00Z 起点のアジア時間帯に集中 (最長 53 本 ≈ 13h)。
  判定器 `tools/e1_positioning_prereg_eval.py` は horizon を**配列位置**で進めるため、欠落は
  forward return / ATR を静かに伸ばす (手順書 (xv))。`--ohlcv-max-gap-bars 553` での受容は
  primary pair の estimand を歪めるので、2026-07-29 の `tools/massive_gap_backfill.py`
  (2019/2020 の vendor 窓を OANDA mid で補填、provenance 付き) と同じ方式で**欠落 bar だけ**を
  OANDA v20 mid M15 (dailyAlignment=0 / alignmentTimezone=UTC) から補う。

設計上の約束:
  - **共有 cache (`data/cache/massive/`) は改変しない** — 補填済みの複製を `--dst`
    (既定 `data/cache/e1_ohlcv/`) に書き、凍結 export は `--ohlcv-src <dst>` でそれを読む。
    E15/E7 台帳 (.bak-pre-refreeze) や他 consumer に触れない。
  - 追加するのは **[t0, min(last_complete, expected_last)] の市場時間 15m スロットのうち src に
    無いもの**だけ。既存行は値・順序とも不改変 (書込み前に assert)。OANDA が返した欠落外の bar は捨てる。
  - 出力は件数・時刻・sha256 のみ (価格値は stdout にも audit にも出さない — E1 の凍結 look 規律
    §6-2 と同じ運用。価格は凍結対象外だが、習慣として値を印字しない)。
  - 埋め残し (OANDA にも無い bar) は `unfilled_bars` として残し、凍結時に
    `--ohlcv-max-gap-bars N` で明示受容する (verdict に併記)。本 tool は黙って受容しない。
  - 窓内の余分な行 (off-grid / 閉場) も数える (`extra_in_window`)。10-06 実測は 13/13 で 0 —
    preflight の `extra_off_grid_or_closed_bars` はファイル全体 (t0 以前の 2014〜2021 年) の
    履歴行で、スライスには入らない。凍結時は `--ohlcv-drop-extra-bars` を併記して通す。

Usage:
  python3 tools/e1_ohlcv_gap_backfill.py --dry-run                 # 計画のみ (ネットワーク・書込みなし)
  python3 tools/e1_ohlcv_gap_backfill.py [--src DIR] [--dst DIR] [--look 1|2] [--postponed] \
      [--audit-out raw/bt-results/e1-ohlcv-gap-backfill-<slug>.json]
  # --postponed (§2.5-3、first look のみ): cutoff 11-05T06:33:31Z、dst 既定 data/cache/e1_ohlcv_postponed/
  # exit 2 = いずれかの pair が missing_src / refused_src_index (その pair の古い dst は削除済み)
  # 凍結手順 (手順書 §3): refresh 15m 13 pair → 本 tool → `--preflight-only --ohlcv-src <dst>`
  #   → `--look 1 --slice-ohlcv --ohlcv-src <dst> --ohlcv-drop-extra-bars [--ohlcv-max-gap-bars N]`
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.e1_positioning_frozen_export import (  # noqa: E402
    BAR_SEC, INSTRUMENTS, LOOKS, T0_ISO, _is_market_open, _on_grid_market_mask,
    expected_last_bar_open, expected_market_slots, iso_sec, look_spec, parse_utc,
)

DEFAULT_SRC = ROOT / "data" / "cache" / "massive"
DEFAULT_DST = ROOT / "data" / "cache" / "e1_ohlcv"           # look 1 (first look)


def default_dst(look: int, postponed: bool = False) -> Path:
    """look / postponed ごとに別の複製ディレクトリ (first look の複製を postponed 再凍結で上書きしない)。
    look 1 = data/cache/e1_ohlcv/ (手順書 §3)、postponed = …/e1_ohlcv_postponed/、look 2 = …/e1_ohlcv_look2/。"""
    if look == 1 and not postponed:
        return DEFAULT_DST
    suffix = "postponed" if postponed else f"look{look}"
    return ROOT / "data" / "cache" / f"e1_ohlcv_{suffix}"
PROVENANCE = "oanda_v20 mid M15 (price=M, dailyAlignment=0, alignmentTimezone=UTC), complete candles only"

# OANDA fetch は tools/massive_gap_backfill.py のものを再利用 (5000 本上限のスライス・retry 込み)。
# tests は fetch_fn を差し替える。
FetchFn = Callable[[str, "datetime", "datetime"], "Any"]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_index(idx):
    import pandas as pd
    idx = pd.DatetimeIndex(idx)
    return idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")


def _epochs(idx) -> List[int]:
    import pandas as pd
    return [int(t) for t in ((idx - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1)).tolist()]


def _runs(missing: Sequence[int]) -> List[Tuple[int, int, int]]:
    """連続欠落を (start_epoch, end_epoch, n) に畳む。"""
    out: List[List[int]] = []
    for t in missing:
        if out and t - out[-1][1] == BAR_SEC:
            out[-1][1] = t
            out[-1][2] += 1
        else:
            out.append([t, t, 1])
    return [tuple(r) for r in out]  # type: ignore[misc]


def _remove_stale(dp: Path, dry_run: bool) -> bool:
    """src が無い / 拒否された pair の古い dst を消す (前回成功分が今回の入力から作られたふりをして
    preflight を通るのを防ぐ、Codex P2 4191149514)。dry-run は消さず有無だけ返す。"""
    if not dp.exists():
        return False
    if not dry_run:
        dp.unlink()
    return True


def plan_pair(df, t0: datetime, cutoff: datetime) -> Dict[str, Any]:
    """src frame の index だけから、窓内の欠落スロットと余分な行を数える (値は読まない)。"""
    import pandas as pd
    idx = _norm_index(df.index)
    cutoff_ts = pd.Timestamp(cutoff)
    exp_last = expected_last_bar_open(cutoff)
    complete = idx[(idx + pd.Timedelta(seconds=BAR_SEC)) <= cutoff_ts]
    last_c = complete.max().to_pydatetime() if len(complete) else None
    end = min(exp_last, last_c) if last_c is not None else None
    plan: Dict[str, Any] = {
        "rows_src": int(len(idx)), "duplicates": int(idx.duplicated().sum()),
        "monotonic": bool(idx.is_monotonic_increasing),
        "last_complete_src": iso_sec(last_c) if last_c else None,
        "expected_last_bar_open": iso_sec(exp_last),
        "window_end": iso_sec(end) if end else None,
    }
    if end is None or end < t0:
        plan.update({"window_slots": 0, "window_rows_src": 0, "gap_bars": 0, "gap_runs": 0,
                     "gap_max_run_bars": 0, "gap_first": None, "extra_in_window": 0,
                     "missing": [], "runs": []})
        return plan
    slots = expected_market_slots(t0, end)
    have = set(_epochs(idx))
    missing = [t for t in slots if t not in have]
    runs = _runs(missing)
    win = complete[(complete >= pd.Timestamp(t0))]
    ep_win = _epochs(win)
    extra = [t for t, ok in zip(ep_win, _on_grid_market_mask(ep_win)) if not ok]
    plan.update({
        "window_slots": len(slots), "window_rows_src": int(len(win)),
        "gap_bars": len(missing), "gap_runs": len(runs),
        "gap_max_run_bars": max((r[2] for r in runs), default=0),
        "gap_first": iso_sec(datetime.fromtimestamp(missing[0], tz=timezone.utc)) if missing else None,
        "extra_in_window": len(extra),
        "missing": missing, "runs": runs,
    })
    return plan


def fill_pair(df, plan: Dict[str, Any], pair: str, fetch_fn: FetchFn) -> Tuple[Any, Dict[str, Any]]:
    """欠落スロットだけを fetch_fn の bar で埋めた新 frame と、件数の summary を返す。

    既存行は不改変 (assert)。fetch_fn が返した欠落外の bar は捨てる。
    """
    import pandas as pd
    from tools.massive_gap_backfill import adapt_schema
    missing = set(plan["missing"])
    fetched_idx: List[Any] = []
    fetched_rows: List[Dict[str, float]] = []
    fetched_total = 0
    for s, e, _n in plan["runs"]:
        ws = datetime.fromtimestamp(s, tz=timezone.utc)
        we = datetime.fromtimestamp(e, tz=timezone.utc) + timedelta(seconds=BAR_SEC)
        got = fetch_fn(pair, ws, we)
        if got is None or len(got) == 0:
            continue
        gidx = _norm_index(got.index)
        fetched_total += int(len(gidx))
        for ts, ep in zip(gidx, _epochs(gidx)):
            if ep in missing:
                row = got.loc[ts]
                fetched_idx.append(ts)
                fetched_rows.append({"o": float(row["o"]), "h": float(row["h"]),
                                     "l": float(row["l"]), "c": float(row["c"]),
                                     "volume": float(row.get("volume", 0.0))})
    summary = {"fetched_bars_total": fetched_total, "filled_bars": 0,
               "unfilled_bars": plan["gap_bars"], "unfilled_first": plan["gap_first"]}
    if not fetched_rows:
        return df, summary
    fill = pd.DataFrame(fetched_rows, index=pd.DatetimeIndex(fetched_idx))
    fill = fill[~fill.index.duplicated(keep="last")].sort_index()
    fill = adapt_schema(fill, df)
    src_idx = _norm_index(df.index)
    src = df.copy()
    src.index = src_idx
    assert not fill.index.isin(src_idx).any(), "fill に既存 timestamp が混入"
    new = pd.concat([src, fill]).sort_index()
    # 既存行は値・dtype とも不改変
    back = new.loc[src_idx]
    if not back.equals(src):
        raise RuntimeError(f"{pair}: 既存行が改変される (refusing to write)")
    still = [t for t in plan["missing"] if t not in set(_epochs(_norm_index(new.index)))]
    summary.update({"filled_bars": int(len(fill)), "unfilled_bars": len(still),
                    "unfilled_first": iso_sec(datetime.fromtimestamp(still[0], tz=timezone.utc))
                    if still else None})
    return new, summary


def default_fetch_fn(client) -> FetchFn:
    from tools.massive_gap_backfill import fetch_oanda_window

    def _f(pair: str, ws: datetime, we: datetime):
        import pandas as pd
        return fetch_oanda_window(client, pair, "15m", pd.Timestamp(ws), pd.Timestamp(we))
    return _f


def run(src_dir: Path, dst_dir: Path, t0: datetime, cutoff: datetime, *,
        pairs: Sequence[str] = INSTRUMENTS, dry_run: bool = False,
        fetch_fn: Optional[FetchFn] = None, audit_out: Optional[Path] = None,
        out=None) -> Dict[str, Any]:
    import pandas as pd
    out = out or sys.stdout
    audit: Dict[str, Any] = {
        "tool": "tools/e1_ohlcv_gap_backfill.py", "created_at": iso_sec(datetime.now(timezone.utc)),
        "t0": iso_sec(t0), "cutoff": iso_sec(cutoff), "src_dir": str(src_dir), "dst_dir": str(dst_dir),
        "provenance": PROVENANCE, "dry_run": bool(dry_run), "pairs": {},
        "note": ("追加したのは窓内の市場時間 15m スロットのうち src に無い bar のみ。既存行は不改変。"
                 "OANDA の volume は tick 数で MASSIVE の volume と意味が異なる (判定器は mid OHLC のみ使用)。"
                 "値は記録しない (件数・時刻・sha256 のみ)。"),
    }
    print(f"E1 OHLCV gap backfill — t0 {iso_sec(t0)}, cutoff {iso_sec(cutoff)}, src {src_dir}, "
          f"dst {dst_dir}{' (DRY-RUN: ネットワーク・書込みなし)' if dry_run else ''}", file=out)
    if not dry_run:
        dst_dir.mkdir(parents=True, exist_ok=True)
    totals = {"gap_bars": 0, "filled_bars": 0, "unfilled_bars": 0}
    for pair in pairs:
        sp = src_dir / f"{pair}_15m.parquet"
        rec: Dict[str, Any] = {"src": str(sp)}
        dp = dst_dir / f"{pair}_15m.parquet"
        if not sp.exists():
            rec.update({"status": "missing_src", "dst_removed": _remove_stale(dp, dry_run)})
            audit["pairs"][pair] = rec
            print(f"  MISSING {pair}: src parquet なし"
                  f"{' (古い dst を削除)' if rec['dst_removed'] else ''}", file=out)
            continue
        df = pd.read_parquet(sp)
        plan = plan_pair(df, t0, cutoff)
        rec.update({k: v for k, v in plan.items() if k not in ("missing", "runs")})
        rec["runs"] = [{"start": iso_sec(datetime.fromtimestamp(s, tz=timezone.utc)),
                        "end": iso_sec(datetime.fromtimestamp(e, tz=timezone.utc)), "n": n}
                       for s, e, n in plan["runs"]]
        rec["src_sha256"] = _sha256(sp)
        totals["gap_bars"] += plan["gap_bars"]
        if plan["duplicates"] or not plan["monotonic"]:
            rec.update({"status": "refused_src_index", "dst_removed": _remove_stale(dp, dry_run)})
            audit["pairs"][pair] = rec
            print(f"  REFUSED {pair}: src index が一意/単調でない (dup {plan['duplicates']})"
                  f"{' (古い dst を削除)' if rec['dst_removed'] else ''}", file=out)
            continue
        if dry_run:
            rec["status"] = "planned"
            audit["pairs"][pair] = rec
            print(f"  PLAN {pair}: window rows {plan['window_rows_src']}/{plan['window_slots']} slots, "
                  f"gaps {plan['gap_bars']} (runs {plan['gap_runs']}, max run {plan['gap_max_run_bars']}, "
                  f"first {plan['gap_first']}), extra_in_window {plan['extra_in_window']}, "
                  f"last complete {plan['last_complete_src']}", file=out)
            continue
        if plan["gap_bars"] == 0:
            shutil.copy2(sp, dp)
            rec.update({"status": "copied_unchanged", "filled_bars": 0, "unfilled_bars": 0,
                        "dst": str(dp), "dst_sha256": _sha256(dp), "rows_dst": int(len(df))})
            audit["pairs"][pair] = rec
            print(f"  COPY {pair}: gaps 0 → byte copy (rows {len(df)})", file=out)
            continue
        if fetch_fn is None:
            raise RuntimeError("fetch_fn が無い (--dry-run 以外は OANDA client が必要)")
        new, summ = fill_pair(df, plan, pair, fetch_fn)
        new.to_parquet(dp, engine="pyarrow")
        # 書いたものを読み戻して既存行の不改変と行数を再確認
        back = pd.read_parquet(dp)
        if int(len(back)) != int(len(df)) + summ["filled_bars"]:
            raise RuntimeError(f"{pair}: 書込み後の行数不一致")
        rec.update(summ)
        rec.update({"status": "filled" if summ["unfilled_bars"] == 0 else "filled_partial",
                    "dst": str(dp), "dst_sha256": _sha256(dp), "rows_dst": int(len(back))})
        totals["filled_bars"] += summ["filled_bars"]
        totals["unfilled_bars"] += summ["unfilled_bars"]
        audit["pairs"][pair] = rec
        print(f"  FILL {pair}: gaps {plan['gap_bars']} (runs {plan['gap_runs']}) → filled "
              f"{summ['filled_bars']}, unfilled {summ['unfilled_bars']}"
              f"{' (first ' + str(summ['unfilled_first']) + ')' if summ['unfilled_bars'] else ''}, "
              f"rows {len(df)} → {len(back)}", file=out)
    failed = sorted(p for p, r in audit["pairs"].items()
                    if r.get("status") in ("missing_src", "refused_src_index"))
    audit["totals"] = totals
    audit["failed_pairs"] = failed
    audit["ok"] = not failed
    print(f"  totals: gap_bars {totals['gap_bars']}, filled {totals['filled_bars']}, "
          f"unfilled {totals['unfilled_bars']}"
          f"{'  FAILED pairs: ' + ','.join(failed) if failed else ''}", file=out)
    if audit_out is not None and not dry_run:
        audit_out.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_out, "w", encoding="utf-8") as f:
            json.dump(audit, f, ensure_ascii=False, indent=1, sort_keys=True)
        print(f"  audit → {audit_out}", file=out)
    return audit


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    ap.add_argument("--dst", default="", help="既定 = default_dst(--look, --postponed)")
    ap.add_argument("--look", type=int, default=1, choices=sorted(LOOKS))
    ap.add_argument("--postponed", action="store_true",
                    help="§2.5-3 の 4 週スライド (first look のみ): cutoff と既定 dst / audit 名を postponed 版にする")
    ap.add_argument("--cutoff", default="", help="既定 = look_spec(--look, --postponed).cutoff")
    ap.add_argument("--t0", default=T0_ISO)
    ap.add_argument("--pairs", default="", help="カンマ区切り (既定 13 pair)")
    ap.add_argument("--audit-out", default="",
                    help="既定 raw/bt-results/e1-ohlcv-gap-backfill-<slug>-<date>.json")
    ap.add_argument("--dry-run", action="store_true", help="計画のみ (ネットワーク・書込みなし)")
    args = ap.parse_args(argv)
    spec = look_spec(args.look, args.postponed)          # postponed は look 1 のみ (ValueError)
    cutoff = parse_utc(args.cutoff or spec["cutoff"])
    t0 = parse_utc(args.t0)
    pairs = tuple(p for p in args.pairs.split(",") if p) if args.pairs else INSTRUMENTS
    src = Path(args.src).resolve()
    dst = Path(args.dst).resolve() if args.dst else default_dst(args.look, args.postponed)
    if src == dst:
        print("REFUSED: --dst は --src と別ディレクトリにすること (共有 cache は改変しない)", file=sys.stderr)
        return 2
    slug = spec["slug"]        # look_spec が postponed なら既に "-postponed" 付き (二重付与しない、Codex P2 4191189958)
    audit_out = Path(args.audit_out) if args.audit_out else (
        ROOT / "raw" / "bt-results" /
        f"e1-ohlcv-gap-backfill-{slug}-{datetime.now(timezone.utc):%Y-%m-%d}.json")
    fetch_fn = None
    if not args.dry_run:
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
            if not os.environ.get("OANDA_TOKEN"):
                load_dotenv(src.parents[2] / ".env")   # worktree は .env を持たない
        except Exception:
            pass
        from modules.oanda_client import OandaClient
        fetch_fn = default_fetch_fn(OandaClient())
    audit = run(src, dst, t0, cutoff, pairs=pairs, dry_run=args.dry_run, fetch_fn=fetch_fn,
                audit_out=audit_out)
    if not audit["ok"]:
        print(f"FAILED: {','.join(audit['failed_pairs'])} が missing_src / refused — 複製は不完全 "
              f"(当該 pair の古い dst は削除済み)。凍結へ進まない", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
