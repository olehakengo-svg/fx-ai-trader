#!/usr/bin/env python3
"""E1 positioning pre-reg — 凍結 export tool (§2.5-6「1 回だけ export + sha256」の機械担保、rule:R3)

仕様 SSOT (変更禁止):
  knowledge-base/wiki/decisions/e1-positioning-contrarian-prereg-2026-07-16.md (🔒 LOCKED)
手順書:
  knowledge-base/wiki/decisions/e1-first-look-runbook-2026-09-22.md

役割 (§2.5-6 / §6-1 / §6-2):
  1. `/api/positioning/export` から 13 instrument の outlook snapshots
     (snapshot_time ≤ cutoff、t0 以降の全行 — burn-in/評価窓の切り出しは判定器側) と
     `table=health_log` (value ≤ cutoff) を取得し、判定器
     `tools/e1_positioning_prereg_eval.py --artifact` がそのまま読める JSON dict
     {"snapshots": [...], "health": [...], "synthetic": false, "meta": {...}} に保存する。
  2. sha256 を `knowledge-base/raw/bt-results/e1-{look}-freeze-{cutoff日}.sha256`
     (sha256sum -c 互換) に記録し、同名 `.manifest.json` に件数・時刻範囲・cutoff・
     tool/API の出所を書く。**この .sha256 が「凍結済み」marker**。
  3. 「1 回だけ」ガード: marker が既に存在すれば `--force` なしでは再実行を拒否する
     (exit 3)。--force 時は manifest の `force_history` に前回 sha256 を残す (fail-loud)。
  4. **値の非表示**: stdout/stderr には件数・時刻範囲 (秒精度)・sha256・パスのみ。
     skew/ratio/avg 価格/buckets/IC/EV/PnL は一切出さない (§6-2 中間 peeking 禁止)。
     artifact ファイルの中身を人が開くことも verdict 期日まで禁止 (§6-2)。
  5. M15 parquet の cutoff スライス (`--slice-ohlcv`): `data/cache/massive/{PAIR}_15m.parquet`
     を「open + 900s ≤ cutoff (完結 bar のみ、判定器 clip_bars_to_cutoff と同一規約)」で
     切詰めて `--ohlcv-dst` に書き、sha256/bytes/行数/末尾 bar 時刻を同じ .sha256/.manifest に
     追記する。data/cache/ は gitignored なので raw 側に残るのは sha256 のみ。

本番への試走は `--dry-run-health` (table=health_log、limit 小、ファイル書込みなし) のみ。
snapshots の limit=1 試走は生 skew 値 1 行の閲覧に当たり §6-2 許可リスト外 — 実装しない。

モジュールトップ副作用禁止 — env/argparse/network は全て関数内。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# ══════════════════════════════════════════════════════════════════════
# 定数 (pre-reg LOCK 済み値。判定器と同値であることを tests で pin)
# ══════════════════════════════════════════════════════════════════════

DEFAULT_API_BASE = "https://fx-ai-trader.onrender.com"

PRIMARY: Tuple[str, ...] = ("USD_JPY", "EUR_USD", "GBP_USD",
                            "EUR_JPY", "GBP_JPY", "AUD_JPY")
CONFIRMATORY: Tuple[str, ...] = ("AUD_USD", "NZD_USD", "USD_CAD", "USD_CHF",
                                 "NZD_JPY", "EUR_AUD", "EUR_GBP")
INSTRUMENTS: Tuple[str, ...] = PRIMARY + CONFIRMATORY      # 13 (§2.4)
BOOK_TYPE = "outlook"                                       # §2.1 estimand

T0_ISO = "2026-07-16T06:33:31Z"                             # 付録 A primary t0
LOOKS: Dict[int, Dict[str, str]] = {
    1: {"cutoff": "2026-10-08T06:33:31Z", "slug": "first-look",
        "verdict": "2026-10-15"},
    2: {"cutoff": "2026-12-30T06:33:31Z", "slug": "second-look",
        "verdict": "2027-01-06"},
}
API_PAGE_LIMIT = 20000          # app.py /api/positioning/export の上限
MAX_PAGES = 200                 # 無限ループ保険 (13 × 20000 行 ≫ 想定)
BAR_SEC = 900                   # M15 完結 = open + 900s ≤ cutoff (判定器と同一)

EXIT_OK, EXIT_FAIL, EXIT_REFUSED_FROZEN = 0, 2, 3

Fetcher = Callable[[str, Dict[str, Any]], Dict[str, Any]]


# ══════════════════════════════════════════════════════════════════════
# 小道具
# ══════════════════════════════════════════════════════════════════════

def parse_utc(ts: Any) -> datetime:
    """ISO8601 / sqlite datetime('now') 形 → aware UTC datetime。"""
    s = str(ts).strip().replace(" ", "T")
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso_sec(dt: datetime) -> str:
    """秒精度 ISO (stdout 用 — 小数点を含む数値列を出さない)。"""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def utc_now() -> datetime:
    """現在時刻 (tests が monkeypatch する唯一の時計)。"""
    return datetime.now(timezone.utc)


def default_paths(look: int, out_dir: str = "") -> Dict[str, str]:
    """成果物パス (raw/bt-results/e1-{slug}-freeze-{cutoff日}.*)。"""
    spec = LOOKS[look]
    day = spec["cutoff"][:10]
    base = f"e1-{spec['slug']}-freeze-{day}"
    root = out_dir or os.path.join(repo_root(), "knowledge-base", "raw", "bt-results")
    return {
        "dir": os.path.join(root, base),
        "artifact": os.path.join(root, base, f"e1_prereg_frozen_export_look{look}.json"),
        "sha256": os.path.join(root, f"{base}.sha256"),      # = 凍結 marker
        "manifest": os.path.join(root, f"{base}.manifest.json"),
    }


def http_fetcher(base_url: str, timeout: float = 120.0) -> Fetcher:
    """`/api/positioning/export` を GET する fetcher (fail-loud)。"""
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        # file:// 等のスキームを構造的に拒否 (CWE-939)
        raise ValueError(f"api base must be http(s)://host — got {base_url!r}")

    def _fetch(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not path.startswith("/api/positioning/"):
            raise ValueError(f"path outside /api/positioning/: {path!r}")
        url = base_url.rstrip("/") + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "e1-frozen-export"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec: scheme pinned above
            body = resp.read()
        data = json.loads(body)
        if not isinstance(data, dict):
            raise RuntimeError(f"unexpected response type {type(data).__name__} for {path}")
        if "error" in data:
            raise RuntimeError(f"API error for {path}: {data['error']}")
        return data
    return _fetch


# ══════════════════════════════════════════════════════════════════════
# 取得 (ページング + cutoff フィルタ + dedup)
# ══════════════════════════════════════════════════════════════════════

def fetch_snapshots(fetcher: Fetcher, instrument: str, cutoff: datetime,
                    page_limit: int = API_PAGE_LIMIT) -> List[Dict[str, Any]]:
    """1 instrument の outlook 行を snapshot_time ≤ cutoff で全取得。

    API は `from=` (snapshot_time >= 下限) + `limit` のみなので、最終行の
    snapshot_time を次ページの下限にして進み、(instrument, book_type, snapshot_time)
    で dedup する。cutoff 超の行はページ内で捨て、以降のページは要求しない。
    """
    out: List[Dict[str, Any]] = []
    seen: set = set()
    since = ""
    for _ in range(MAX_PAGES):
        params: Dict[str, Any] = {"instrument": instrument, "book": BOOK_TYPE,
                                  "limit": page_limit}
        if since:
            params["from"] = since
        data = fetcher("/api/positioning/export", params)
        rows = data.get("rows") or []
        new = 0
        reached_cutoff = False
        last_ts = since
        for r in rows:
            ts = r.get("snapshot_time")
            if ts is None:
                raise RuntimeError(f"{instrument}: row without snapshot_time")
            if parse_utc(ts) > cutoff:
                reached_cutoff = True
                break
            key = (r.get("instrument"), r.get("book_type"), str(ts))
            last_ts = str(ts)
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
            new += 1
        if reached_cutoff or len(rows) < page_limit or new == 0:
            break
        since = last_ts
    else:
        raise RuntimeError(f"{instrument}: pagination exceeded MAX_PAGES={MAX_PAGES}")
    return out


def fetch_health_log(fetcher: Fetcher, cutoff: datetime,
                     page_limit: int = API_PAGE_LIMIT) -> List[Dict[str, Any]]:
    """positioning_health_log を id 増分で全取得 (value ≤ cutoff)。

    判定器 load_artifact の health 行契約 = {"key", "value"} (id は保持して無害)。
    """
    out: List[Dict[str, Any]] = []
    since_id = 0
    for _ in range(MAX_PAGES):
        data = fetcher("/api/positioning/export",
                       {"table": "health_log", "since_id": since_id,
                        "limit": page_limit})
        rows = data.get("rows") or []
        if not rows:
            break
        for r in rows:
            rid = int(r.get("id", 0))
            since_id = max(since_id, rid)
            val = r.get("value")
            if not val:
                continue
            try:
                if parse_utc(val) > cutoff:
                    continue          # id 順 ≠ 厳密な時刻順の可能性 → 行単位で捨てる
            except ValueError:
                continue              # 非時刻 value は判定器側でも無視される
            out.append({"id": rid, "key": r.get("key"), "value": val})
        if len(rows) < page_limit:
            break
    else:
        raise RuntimeError(f"health_log: pagination exceeded MAX_PAGES={MAX_PAGES}")
    return out


# ══════════════════════════════════════════════════════════════════════
# 要約 (値を含まない) / artifact 書込み / sha256 記録
# ══════════════════════════════════════════════════════════════════════

_VALUE_FIELDS = ("pct_long_total", "pct_short_total", "near_imbalance",
                 "price", "bucket_width", "buckets", "buckets_json")


def summarize_snapshots(snapshots: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """instrument 別 件数 + snapshot_time 範囲 (秒精度)。値フィールドは触らない。"""
    per: Dict[str, Dict[str, Any]] = {}
    for r in snapshots:
        inst = str(r.get("instrument"))
        t = parse_utc(r["snapshot_time"])
        d = per.setdefault(inst, {"rows": 0, "first": None, "last": None})
        d["rows"] += 1
        d["first"] = t if d["first"] is None or t < d["first"] else d["first"]
        d["last"] = t if d["last"] is None or t > d["last"] else d["last"]
    for d in per.values():
        d["first"] = iso_sec(d["first"])
        d["last"] = iso_sec(d["last"])
    return {"rows_total": len(snapshots),
            "instruments_present": sorted(per),
            "instruments_missing": [i for i in INSTRUMENTS if i not in per],
            "per_instrument": {i: per[i] for i in sorted(per)}}


def summarize_health(health: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    keys: Dict[str, int] = {}
    ids = [int(r.get("id", 0)) for r in health]
    ts = [parse_utc(r["value"]) for r in health if r.get("value")]
    for r in health:
        k = str(r.get("key"))
        keys[k] = keys.get(k, 0) + 1
    return {"rows_total": len(health),
            "id_min": min(ids) if ids else None,
            "id_max": max(ids) if ids else None,
            "first": iso_sec(min(ts)) if ts else None,
            "last": iso_sec(max(ts)) if ts else None,
            "keys": dict(sorted(keys.items()))}


def build_artifact(snapshots: List[Dict[str, Any]], health: List[Dict[str, Any]],
                   look: int, cutoff: datetime, api_base: str,
                   frozen_at: Optional[datetime] = None) -> Dict[str, Any]:
    """判定器 load_artifact 互換 dict。synthetic=false (実データ → --verdict-run 必須)。"""
    frozen_at = frozen_at or datetime.now(timezone.utc)
    return {
        "snapshots": snapshots,
        "health": health,
        "synthetic": False,
        "meta": {
            "tool": "tools/e1_positioning_frozen_export.py",
            "prereg": "knowledge-base/wiki/decisions/e1-positioning-contrarian-prereg-2026-07-16.md",
            "look": look, "cutoff": iso_sec(cutoff), "t0": T0_ISO,
            "book_type": BOOK_TYPE, "instruments": list(INSTRUMENTS),
            "api_base": api_base, "frozen_at": iso_sec(frozen_at),
            "snapshots_summary": summarize_snapshots(snapshots),
            "health_summary": summarize_health(health),
        },
    }


def write_json_atomic(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=0, sort_keys=True, default=str)
    os.replace(tmp, path)


def relpath_for_record(path: str, root: str) -> str:
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        return path
    return path if rel.startswith("..") else rel


def write_sha256_record(sha_path: str, entries: Dict[str, str]) -> None:
    """sha256sum -c 互換 (`<hex>  <path>`、path は repo 相対)。"""
    os.makedirs(os.path.dirname(sha_path), exist_ok=True)
    lines = [f"{h}  {p}" for p, h in sorted(entries.items())]
    with open(sha_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def read_sha256_record(sha_path: str) -> Dict[str, str]:
    entries: Dict[str, str] = {}
    with open(sha_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^([0-9a-f]{64})  (.+)$", line)
            if not m:
                raise RuntimeError(f"malformed sha256 line: {line!r}")
            entries[m.group(2)] = m.group(1)
    return entries


def verify_record(sha_path: str, root: str = "") -> Dict[str, Any]:
    """§2.5-5(b) roundtrip 突合: 記録 sha256 と現ファイルの再計算を比較。"""
    root = root or repo_root()
    entries = read_sha256_record(sha_path)
    results: Dict[str, str] = {}
    ok = True
    for rel, want in entries.items():
        fp = rel if os.path.isabs(rel) else os.path.join(root, rel)
        if not os.path.exists(fp):
            results[rel] = "MISSING"
            ok = False
            continue
        got = sha256_file(fp)
        results[rel] = "OK" if got == want else "MISMATCH"
        ok = ok and got == want
    return {"ok": ok, "files": results, "n": len(entries)}


# ══════════════════════════════════════════════════════════════════════
# M15 parquet cutoff スライス (§2.3「フル期間版から切詰める」)
# ══════════════════════════════════════════════════════════════════════

def slice_ohlcv(src_dir: str, dst_dir: str, cutoff: datetime,
                pairs: Sequence[str] = INSTRUMENTS) -> Dict[str, Dict[str, Any]]:
    """{PAIR}_15m.parquet を「open + 900s ≤ cutoff」で切詰めて dst へ書く。

    判定器 clip_bars_to_cutoff と同一規約 (完結 bar のみ)。値 (OHLC) は返さない —
    返すのは bytes / sha256 / 行数 / 末尾 bar open 時刻のみ。欠落 pair は fail-loud。
    """
    import pandas as pd
    os.makedirs(dst_dir, exist_ok=True)
    cutoff_ts = pd.Timestamp(cutoff)
    out: Dict[str, Dict[str, Any]] = {}
    missing: List[str] = []
    for pair in pairs:
        src = os.path.join(src_dir, f"{pair}_15m.parquet")
        if not os.path.exists(src):
            missing.append(pair)
            continue
        df = pd.read_parquet(src)
        idx = df.index
        if getattr(idx, "tz", None) is None:
            idx = idx.tz_localize("UTC")
            df.index = idx
        keep = (idx + pd.Timedelta(seconds=BAR_SEC)) <= cutoff_ts
        sliced = df.loc[keep]
        dst = os.path.join(dst_dir, f"{pair}_15m.parquet")
        sliced.to_parquet(dst)
        out[pair] = {
            "path": dst, "bytes": os.path.getsize(dst), "sha256": sha256_file(dst),
            "rows": int(len(sliced)), "rows_dropped": int(len(df) - len(sliced)),
            "source_sha256": sha256_file(src),
            "last_bar_open": iso_sec(sliced.index.max().to_pydatetime()) if len(sliced) else None,
        }
    if missing:
        raise RuntimeError(f"OHLCV parquet 欠落 ({len(missing)}/{len(pairs)}): {missing} "
                           f"in {src_dir} (§2.5-1 fail-loud)")
    return out


# ══════════════════════════════════════════════════════════════════════
# 凍結本体
# ══════════════════════════════════════════════════════════════════════

def run_freeze(fetcher: Fetcher, look: int, paths: Dict[str, str], api_base: str,
               force: bool = False, allow_missing: bool = False,
               ohlcv_src: str = "", ohlcv_dst: str = "",
               now: Optional[datetime] = None,
               out=None) -> int:
    """export → artifact → sha256 記録。stdout には値を出さない。"""
    out = out or sys.stdout
    spec = LOOKS[look]
    cutoff = parse_utc(spec["cutoff"])
    now = now or utc_now()
    root = repo_root()

    # ── 「1 回だけ」ガード ────────────────────────────────────────
    marker = paths["sha256"]
    force_history: List[Dict[str, Any]] = []
    if os.path.exists(marker):
        if not force:
            print(f"REFUSED: 凍結 marker が既に存在 ({relpath_for_record(marker, root)})。"
                  f" §2.5-6「1 回だけ export」— 再実行は --force 必須 (manifest に"
                  f" 前回 sha256 を残す)。", file=sys.stderr)
            return EXIT_REFUSED_FROZEN
        prev = read_sha256_record(marker)
        if os.path.exists(paths["manifest"]):
            with open(paths["manifest"], encoding="utf-8") as f:
                prev_manifest = json.load(f)
            force_history = list(prev_manifest.get("force_history", []))
            prev_frozen_at = prev_manifest.get("frozen_at")
        else:
            prev_frozen_at = None
        force_history.append({"superseded_at": iso_sec(now),
                              "previous_frozen_at": prev_frozen_at,
                              "previous_sha256": prev})
        print(f"WARNING: --force により凍結 marker を上書き (前回 {len(prev)} file)。",
              file=sys.stderr)

    if now < cutoff and not force:
        # cutoff 前に凍結すると評価窓を切り捨てた artifact が marker を占有する
        print(f"REFUSED: 現在時刻 {iso_sec(now)} < cutoff {spec['cutoff']} — 凍結は"
              f" cutoff 到達後に 1 回だけ (§2.5-6、手順書 §2)。意図的な早期凍結は"
              f" --force (manifest に記録)。", file=sys.stderr)
        return EXIT_FAIL

    # ── 取得 ──────────────────────────────────────────────────────
    snapshots: List[Dict[str, Any]] = []
    for inst in INSTRUMENTS:
        snapshots.extend(fetch_snapshots(fetcher, inst, cutoff))
    health = fetch_health_log(fetcher, cutoff)

    snap_sum = summarize_snapshots(snapshots)
    if snap_sum["instruments_missing"] and not allow_missing:
        print(f"REFUSED: snapshots が 0 行の instrument: {snap_sum['instruments_missing']}"
              f" (§2.5-1 fail-loud。ingest 障害を先に切り分ける。記録だけ残すなら"
              f" --allow-missing-instruments)。", file=sys.stderr)
        return EXIT_FAIL
    if not health:
        print("WARNING: health_log が 0 行 — §2.2 stale cap 主モード不成立 "
              "(判定器は --fallback-mode を要求する)。", file=sys.stderr)

    # ── artifact ─────────────────────────────────────────────────
    artifact = build_artifact(snapshots, health, look, cutoff, api_base, frozen_at=now)
    write_json_atomic(paths["artifact"], artifact)
    entries: Dict[str, str] = {
        relpath_for_record(paths["artifact"], root): sha256_file(paths["artifact"])}

    # ── M15 parquet スライス (任意) ────────────────────────────────
    ohlcv_meta: Dict[str, Dict[str, Any]] = {}
    if ohlcv_src:
        if not ohlcv_dst:
            ohlcv_dst = os.path.join(root, "data", "cache",
                                     f"e1_frozen_look{look}_{spec['cutoff'][:10]}")
        ohlcv_meta = slice_ohlcv(ohlcv_src, ohlcv_dst, cutoff)
        for pair, m in ohlcv_meta.items():
            entries[relpath_for_record(m["path"], root)] = m["sha256"]

    # ── 記録 (sha256 = marker、manifest = 出所) ───────────────────
    manifest = {
        "look": look, "slug": spec["slug"], "cutoff": spec["cutoff"],
        "verdict_deadline": spec["verdict"], "frozen_at": iso_sec(now),
        "api_base": api_base, "tool": "tools/e1_positioning_frozen_export.py",
        "artifact": relpath_for_record(paths["artifact"], root),
        "artifact_bytes": os.path.getsize(paths["artifact"]),
        "snapshots_summary": snap_sum,
        "health_summary": summarize_health(health),
        "ohlcv_slice": {p: dict(m, path=relpath_for_record(m["path"], root))
                        for p, m in ohlcv_meta.items()},
        "ohlcv_dst": relpath_for_record(ohlcv_dst, root) if ohlcv_dst else None,
        "sha256_record": relpath_for_record(paths["sha256"], root),
        "force_history": force_history,
        "peeking_note": ("§6-2: artifact の値 (skew/avg 価格/buckets) を verdict 期日前に"
                         " 開く・集計する・プロットすることは禁止。この manifest は"
                         " 件数/時刻範囲/sha256 のみ"),
    }
    write_sha256_record(paths["sha256"], entries)
    write_json_atomic(paths["manifest"], manifest)

    # ── stdout 要約 (値なし) ───────────────────────────────────────
    print(f"E1 frozen export — look {look} ({spec['slug']}), cutoff {spec['cutoff']}", file=out)
    print(f"  snapshots: {snap_sum['rows_total']} rows, "
          f"{len(snap_sum['instruments_present'])}/{len(INSTRUMENTS)} instruments", file=out)
    for inst, d in snap_sum["per_instrument"].items():
        print(f"    {inst}: {d['rows']} rows  {d['first']} .. {d['last']}", file=out)
    if snap_sum["instruments_missing"]:
        print(f"    MISSING: {snap_sum['instruments_missing']}", file=out)
    hs = manifest["health_summary"]
    print(f"  health_log: {hs['rows_total']} rows, id {hs['id_min']}..{hs['id_max']}, "
          f"{hs['first']} .. {hs['last']}, {len(hs['keys'])} keys", file=out)
    for pair, m in ohlcv_meta.items():
        print(f"  ohlcv {pair}: {m['rows']} bars (dropped {m['rows_dropped']}), "
              f"last open {m['last_bar_open']}", file=out)
    for p, h in sorted(entries.items()):
        print(f"  sha256 {h}  {p}", file=out)
    print(f"  manifest: {relpath_for_record(paths['manifest'], root)}", file=out)
    print(f"  marker:   {relpath_for_record(paths['sha256'], root)}", file=out)
    return EXIT_OK


def run_dry_run_health(fetcher: Fetcher, limit: int, out=None) -> int:
    """本番試走 (許可範囲 §6-2): table=health_log を limit 小で 1 回 GET、書込みなし。"""
    out = out or sys.stdout
    data = fetcher("/api/positioning/export",
                   {"table": "health_log", "since_id": 0, "limit": limit})
    rows = data.get("rows") or []
    hs = summarize_health(rows)
    print(f"dry-run health_log: {hs['rows_total']} rows (limit {limit}), "
          f"id {hs['id_min']}..{hs['id_max']}, {hs['first']} .. {hs['last']}", file=out)
    print(f"  keys: {sorted(hs['keys'])}", file=out)
    print("  (no files written)", file=out)
    return EXIT_OK


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="E1 positioning pre-reg 凍結 export (§2.5-6 1 回だけ + sha256)")
    ap.add_argument("--look", type=int, choices=(1, 2), default=1,
                    help="1 = first look (cutoff 2026-10-08) / 2 = second look (12-30)")
    ap.add_argument("--api-base", default=DEFAULT_API_BASE)
    ap.add_argument("--out-dir", default="",
                    help="記録先 root (default knowledge-base/raw/bt-results)")
    ap.add_argument("--force", action="store_true",
                    help="凍結 marker 存在時も再実行 (manifest に前回 sha256 を残す)")
    ap.add_argument("--allow-missing-instruments", action="store_true",
                    help="snapshots 0 行 instrument があっても凍結を続行 (記録のみ)")
    ap.add_argument("--slice-ohlcv", action="store_true",
                    help="M15 parquet を cutoff で切詰めて --ohlcv-dst へ書き sha256 を記録")
    ap.add_argument("--ohlcv-src", default="",
                    help="フル期間 parquet dir (default data/cache/massive)")
    ap.add_argument("--ohlcv-dst", default="",
                    help="切詰め parquet dir (default data/cache/e1_frozen_look{N}_{cutoff日})")
    ap.add_argument("--dry-run-health", action="store_true",
                    help="本番試走: table=health_log を limit 小で GET のみ (書込みなし)")
    ap.add_argument("--limit", type=int, default=5, help="--dry-run-health の limit")
    ap.add_argument("--verify", default="",
                    help="既存 .sha256 記録を再計算して突合 (§2.5-5(b))")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args(argv)

    if args.verify:
        res = verify_record(args.verify)
        for p, st in res["files"].items():
            print(f"  {st:8s} {p}")
        print(f"verify: {'OK' if res['ok'] else 'FAIL'} ({res['n']} files)")
        return EXIT_OK if res["ok"] else EXIT_FAIL

    fetcher = http_fetcher(args.api_base, timeout=args.timeout)
    if args.dry_run_health:
        return run_dry_run_health(fetcher, limit=max(1, min(args.limit, 50)))

    paths = default_paths(args.look, args.out_dir)
    ohlcv_src = ""
    if args.slice_ohlcv:
        ohlcv_src = args.ohlcv_src or os.path.join(repo_root(), "data", "cache", "massive")
    return run_freeze(fetcher, args.look, paths, api_base=args.api_base,
                      force=args.force, allow_missing=args.allow_missing_instruments,
                      ohlcv_src=ohlcv_src, ohlcv_dst=args.ohlcv_dst)


if __name__ == "__main__":
    sys.exit(main())
