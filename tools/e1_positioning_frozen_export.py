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
     **attempt 台帳** (`{base}.attempts.json`): 最初の API 要求の前に「試行開始」を書き、
     取得後の検証失敗 (0 行 instrument / roundtrip 不一致 / 例外) も status=failed で残す。
     台帳に試行があれば marker 不在でも `--force` なしの再実行は拒否 (本番への 2 回目の
     問い合わせを構造的に止める)。ローカルで判る失敗条件 (OHLCV parquet 欠落) は API 要求
     の前に preflight で弾く。
     **staging → 一括公開**: artifact / M15 スライスは staging パスに書き、roundtrip と
     スライスの全検証が通った後にのみ最終パスへ移し、manifest → marker の順で書く。
     --force 中に検証で落ちても前回の凍結 (marker / artifact / manifest) は byte 不改変。
  4. **値の非表示**: stdout/stderr には件数・時刻範囲 (秒精度)・sha256・パスのみ。
     skew/ratio/avg 価格/buckets/IC/EV/PnL は一切出さない (§6-2 中間 peeking 禁止)。
     artifact ファイルの中身を人が開くことも verdict 期日まで禁止 (§6-2)。
  5. M15 parquet の cutoff スライス (`--slice-ohlcv`): `data/cache/massive/{PAIR}_15m.parquet`
     を「open + 900s ≤ cutoff (完結 bar のみ、判定器 clip_bars_to_cutoff と同一規約)」で
     切詰めて `--ohlcv-dst` に書き、sha256/bytes/行数/末尾 bar 時刻を同じ .sha256/.manifest に
     追記する。data/cache/ は gitignored なので raw 側に残るのは sha256 のみ。

  6. **API→artifact roundtrip 突合 (§2.5-5(b))**: artifact 書込み直後にディスクから再読し、
     export レスポンス (メモリ上の 1 回だけの応答) と件数・(instrument, book_type,
     snapshot_time) キー集合・行 canonical digest を突合する。不一致なら marker を書かず
     exit 2 (本番へ再問い合わせしない)。結果は manifest `roundtrip_check` に永続化。
     ページ毎の API 返却件数 / cutoff 超 / dedup 件数は `fetch_ledger` に残す (切詰め検知)。
     `--verify` は記録済み sha256 の再計算 (改竄・破損検知) + manifest の roundtrip 結果表示。
  7. **postpone (§2.5-3 family gate 不成立、1 回限り)**: `--postponed` は first look の
     cutoff・verdict 期日を同幅 4 週スライド (10-08 → 11-05、10-15 → 11-12) した別 marker
     (`e1-first-look-postponed-freeze-2026-11-05.sha256`) を書く。元の first look 凍結は
     不改変 (postpone は元 artifact の gate 判定から生じるため、元 marker 不在は拒否)。

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
from datetime import datetime, timedelta, timezone
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
POSTPONE_WEEKS = 4              # §2.5-3 / §7: cutoff・verdict・窓終端を同幅スライド (1 回限り)
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


def look_spec(look: int, postponed: bool = False) -> Dict[str, Any]:
    """look の cutoff / slug / verdict 期日。postponed=True は §2.5-3 の 4 週スライド。

    pre-reg §7: 「発動時は cutoff・verdict 期日・評価窓終端を同幅 (4 週) スライドし、
    burn-in と評価窓開始は不変」。first look のみ (second look に postpone は無い —
    §4.4 second look の着地は PASS / REJECT-F / REJECT のみ)。
    """
    if look not in LOOKS:
        raise ValueError(f"unknown look {look!r}")
    spec: Dict[str, Any] = dict(LOOKS[look])
    spec.update({"look": look, "postponed": False, "original_cutoff": spec["cutoff"]})
    if postponed:
        if look != 1:
            raise ValueError("postpone (§2.5-3 family gate) は first look のみ")
        shift = timedelta(weeks=POSTPONE_WEEKS)
        spec["cutoff"] = iso_sec(parse_utc(spec["cutoff"]) + shift)
        spec["verdict"] = (parse_utc(spec["verdict"] + "T00:00:00Z") + shift).strftime("%Y-%m-%d")
        spec["slug"] = spec["slug"] + "-postponed"
        spec["postponed"] = True
    return spec


def default_paths(look: int, out_dir: str = "", postponed: bool = False) -> Dict[str, str]:
    """成果物パス (raw/bt-results/e1-{slug}-freeze-{cutoff日}.*)。postponed は別 marker。"""
    spec = look_spec(look, postponed)
    day = spec["cutoff"][:10]
    base = f"e1-{spec['slug']}-freeze-{day}"
    suffix = "_postponed" if postponed else ""
    root = out_dir or os.path.join(repo_root(), "knowledge-base", "raw", "bt-results")
    artifact = os.path.join(root, base, f"e1_prereg_frozen_export_look{look}{suffix}.json")
    return {
        "dir": os.path.join(root, base),
        "artifact": artifact,
        "artifact_staging": artifact + ".staging",
        "sha256": os.path.join(root, f"{base}.sha256"),      # = 凍結 marker
        "manifest": os.path.join(root, f"{base}.manifest.json"),
        "attempts": os.path.join(root, f"{base}.attempts.json"),   # 試行台帳 (API 要求前に書く)
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
                    page_limit: int = API_PAGE_LIMIT,
                    ledger: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """1 instrument の outlook 行を snapshot_time ≤ cutoff で全取得。

    API は `from=` (snapshot_time >= 下限) + `limit` のみなので、最終行の
    snapshot_time を次ページの下限にして進み、(instrument, book_type, snapshot_time)
    で dedup する。cutoff 超の行はページ内で捨て、以降のページは要求しない。

    ledger (任意 dict) には API が返した件数の内訳を書く — rows_returned =
    rows_kept + rows_dedup + rows_beyond_cutoff が成り立つ (切詰め・欠落の検知用、
    §2.5-5(b))。値フィールドは触らない。
    """
    out: List[Dict[str, Any]] = []
    seen: set = set()
    since = ""
    led = {"pages": 0, "rows_returned": 0, "rows_kept": 0,
           "rows_dedup": 0, "rows_beyond_cutoff": 0}
    for _ in range(MAX_PAGES):
        params: Dict[str, Any] = {"instrument": instrument, "book": BOOK_TYPE,
                                  "limit": page_limit}
        if since:
            params["from"] = since
        data = fetcher("/api/positioning/export", params)
        rows = data.get("rows") or []
        led["pages"] += 1
        led["rows_returned"] += len(rows)
        new = 0
        reached_cutoff = False
        last_ts = since
        for i, r in enumerate(rows):
            ts = r.get("snapshot_time")
            if ts is None:
                raise RuntimeError(f"{instrument}: row without snapshot_time")
            if parse_utc(ts) > cutoff:
                reached_cutoff = True
                led["rows_beyond_cutoff"] += len(rows) - i
                break
            key = (r.get("instrument"), r.get("book_type"), str(ts))
            last_ts = str(ts)
            if key in seen:
                led["rows_dedup"] += 1
                continue
            seen.add(key)
            out.append(r)
            new += 1
        led["rows_kept"] += new
        # 終了条件は「cutoff 到達」か「新規行ゼロ」のみ — `len(rows) < page_limit` で
        # 止めない (サーバが limit を要求より小さく丸めた場合に無言で切詰まる)。
        if reached_cutoff or not rows or new == 0:
            break
        since = last_ts
    else:
        raise RuntimeError(f"{instrument}: pagination exceeded MAX_PAGES={MAX_PAGES}")
    if ledger is not None:
        ledger.update(led)
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
        # since_id は単調増加 → 次ページが空になるまで続ける (limit 丸めで切詰めない)
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
                   frozen_at: Optional[datetime] = None,
                   postponed: bool = False) -> Dict[str, Any]:
    """判定器 load_artifact 互換 dict。synthetic=false (実データ → --verdict-run 必須)。"""
    frozen_at = frozen_at or datetime.now(timezone.utc)
    spec = look_spec(look, postponed)
    return {
        "snapshots": snapshots,
        "health": health,
        "synthetic": False,
        "meta": {
            "tool": "tools/e1_positioning_frozen_export.py",
            "prereg": "knowledge-base/wiki/decisions/e1-positioning-contrarian-prereg-2026-07-16.md",
            "look": look, "cutoff": iso_sec(cutoff), "t0": T0_ISO,
            "postponed": postponed, "original_cutoff": spec["original_cutoff"],
            "postpone_weeks": POSTPONE_WEEKS if postponed else 0,
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
    """記録 sha256 と現ファイルの再計算を比較 (改竄・破損検知)。

    これは **ファイル完全性** の検査であり、API↔artifact の突合 (§2.5-5(b)) は凍結時に
    `roundtrip_check()` が行って manifest に永続化する (本番へ再問い合わせしない)。
    manifest が隣にあればその結果も返す (`roundtrip` キー)。
    """
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
    res: Dict[str, Any] = {"ok": ok, "files": results, "n": len(entries)}
    # manifest は必須: marker だけが残った凍結 (manifest 書込み前のクラッシュ等) は不完全 →
    # FAIL。manifest は marker より先に書かれる (run_freeze の公開順) ので、正常凍結では
    # 常に存在し roundtrip_check.ok = true を持つ。
    man_path = re.sub(r"\.sha256$", ".manifest.json", sha_path)
    rt = None
    if man_path != sha_path and os.path.exists(man_path):
        try:
            with open(man_path, encoding="utf-8") as f:
                rt = json.load(f).get("roundtrip_check")
        except (OSError, ValueError):
            rt = None
    if isinstance(rt, dict):
        res["roundtrip"] = {"ok": bool(rt.get("ok")),
                            "snapshots_rows": rt.get("snapshots", {}).get("artifact_rows"),
                            "health_rows": rt.get("health", {}).get("artifact_rows")}
        res["manifest"] = "OK" if rt.get("ok") else "ROUNDTRIP_FAIL"
    else:
        res["manifest"] = "MISSING" if not os.path.exists(man_path) else "ROUNDTRIP_UNRECORDED"
    res["ok"] = bool(ok and res["manifest"] == "OK")
    return res


def canonical_row_digest(row: Dict[str, Any]) -> str:
    """行の canonical JSON (sort_keys、区切り固定) の sha256。値は返さない。"""
    blob = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def rows_digest(rows: Sequence[Dict[str, Any]]) -> str:
    """順序非依存の集合 digest (行 digest を sort して連結 → sha256)。"""
    h = hashlib.sha256()
    for d in sorted(canonical_row_digest(r) for r in rows):
        h.update(d.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def _snapshot_keys(rows: Sequence[Dict[str, Any]]) -> set:
    return {(r.get("instrument"), r.get("book_type"), str(r.get("snapshot_time")))
            for r in rows}


def roundtrip_check(api_snapshots: Sequence[Dict[str, Any]],
                    api_health: Sequence[Dict[str, Any]],
                    artifact_path: str,
                    fetch_ledger: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """§2.5-5(b) API→artifact roundtrip 突合 (凍結時、1 回だけの応答が手元にある間に)。

    artifact をディスクから再読し、export レスポンス (メモリ) と
      - 件数 (snapshots / health)
      - (instrument, book_type, snapshot_time) キー集合 (欠落・重複・切詰め)
      - 行 canonical digest の集合 digest (直列化の欠損・型変化)
    を比較する。結果は件数・真偽値・digest のみ (値フィールドは含まない)。
    """
    with open(artifact_path, encoding="utf-8") as f:
        art = json.load(f)
    a_snap = art.get("snapshots") or []
    a_health = art.get("health") or []
    api_keys, art_keys = _snapshot_keys(api_snapshots), _snapshot_keys(a_snap)
    snap = {
        "api_rows": len(api_snapshots), "artifact_rows": len(a_snap),
        "api_unique_keys": len(api_keys), "artifact_unique_keys": len(art_keys),
        "keys_match": api_keys == art_keys,
        "keys_missing_in_artifact": len(api_keys - art_keys),
        "keys_extra_in_artifact": len(art_keys - api_keys),
        "api_digest": rows_digest(api_snapshots), "artifact_digest": rows_digest(a_snap),
    }
    snap["digest_match"] = snap["api_digest"] == snap["artifact_digest"]
    hl = {
        "api_rows": len(api_health), "artifact_rows": len(a_health),
        "api_digest": rows_digest(api_health), "artifact_digest": rows_digest(a_health),
    }
    hl["digest_match"] = hl["api_digest"] == hl["artifact_digest"]
    ledger_ok = True
    if fetch_ledger:
        for inst, led in fetch_ledger.items():
            if led.get("rows_returned") != (led.get("rows_kept", 0) + led.get("rows_dedup", 0)
                                            + led.get("rows_beyond_cutoff", 0)):
                ledger_ok = False
    ok = (snap["api_rows"] == snap["artifact_rows"] and snap["keys_match"]
          and snap["digest_match"] and hl["api_rows"] == hl["artifact_rows"]
          and hl["digest_match"] and art.get("synthetic") is False and ledger_ok)
    return {"ok": bool(ok), "snapshots": snap, "health": hl,
            "synthetic_flag_false": art.get("synthetic") is False,
            "fetch_ledger_consistent": ledger_ok,
            "fetch_ledger": dict(fetch_ledger or {}),
            "method": "artifact re-read from disk vs in-memory export response; "
                      "counts + key set + canonical row digests; no second API query"}


# ══════════════════════════════════════════════════════════════════════
# M15 parquet cutoff スライス (§2.3「フル期間版から切詰める」)
# ══════════════════════════════════════════════════════════════════════

def missing_ohlcv(src_dir: str, pairs: Sequence[str] = INSTRUMENTS) -> List[str]:
    """{PAIR}_15m.parquet の欠落 pair (API 要求前の preflight に使う)。"""
    return [p for p in pairs if not os.path.exists(os.path.join(src_dir, f"{p}_15m.parquet"))]


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

def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _journal_write(paths: Dict[str, str], journal: Dict[str, Any]) -> None:
    write_json_atomic(paths["attempts"], journal)


def _journal_load(paths: Dict[str, str], spec: Dict[str, Any]) -> Dict[str, Any]:
    if os.path.exists(paths["attempts"]):
        j = _load_json(paths["attempts"])
        if isinstance(j, dict) and isinstance(j.get("attempts"), list):
            return j
    return {"look": spec["look"], "slug": spec["slug"], "cutoff": spec["cutoff"],
            "postponed": spec["postponed"], "attempts": []}


def run_freeze(fetcher: Fetcher, look: int, paths: Dict[str, str], api_base: str,
               force: bool = False, allow_missing: bool = False,
               ohlcv_src: str = "", ohlcv_dst: str = "",
               now: Optional[datetime] = None,
               out=None, postponed: bool = False) -> int:
    """export → staging artifact → roundtrip 突合 → スライス → 一括公開 (manifest → marker)。

    stdout には値を出さない。前回凍結は全検証が通るまで byte 不改変。
    """
    out = out or sys.stdout
    spec = look_spec(look, postponed)
    cutoff = parse_utc(spec["cutoff"])
    now = now or utc_now()
    root = repo_root()
    marker = paths["sha256"]

    # ── postpone (§2.5-3): 元の first look 凍結が存在し、別 marker であること ──
    if postponed:
        orig = default_paths(1, os.path.dirname(marker), postponed=False)
        if os.path.abspath(orig["sha256"]) == os.path.abspath(marker):
            raise RuntimeError("postponed marker が元 marker と同一パス (設計違反)")
        if not os.path.exists(orig["sha256"]):
            print(f"REFUSED: --postponed は元の first look 凍結 marker "
                  f"({relpath_for_record(orig['sha256'], root)}) が前提 (§2.5-3 family gate は"
                  f" 元 artifact の判定器実行から生じる)。元凍結なしの postpone は不可。",
                  file=sys.stderr)
            return EXIT_FAIL

    # ── 「1 回だけ」ガード (marker + attempt 台帳) ─────────────────
    force_history: List[Dict[str, Any]] = []
    journal = _journal_load(paths, spec)
    if os.path.exists(marker):
        if not force:
            print(f"REFUSED: 凍結 marker が既に存在 ({relpath_for_record(marker, root)})。"
                  f" §2.5-6「1 回だけ export」— 再実行は --force 必須 (manifest に"
                  f" 前回 sha256 を残す)。", file=sys.stderr)
            return EXIT_REFUSED_FROZEN
        prev = read_sha256_record(marker)
        prev_frozen_at = None
        if os.path.exists(paths["manifest"]):
            prev_manifest = _load_json(paths["manifest"])
            force_history = list(prev_manifest.get("force_history", []))
            prev_frozen_at = prev_manifest.get("frozen_at")
        force_history.append({"superseded_at": iso_sec(now),
                              "previous_frozen_at": prev_frozen_at,
                              "previous_sha256": prev})
        print(f"WARNING: --force により凍結 marker を上書き (前回 {len(prev)} file)。",
              file=sys.stderr)
    elif journal["attempts"]:
        if not force:
            last = journal["attempts"][-1]
            print(f"REFUSED: marker は無いが attempt 台帳に {len(journal['attempts'])} 件の"
                  f" 試行 (最終 {last.get('started_at')} status={last.get('status')},"
                  f" api_queried={last.get('api_queried')}) — 本番へは既に問い合わせ済み。"
                  f" §2.5-6「1 回だけ export」— 再実行は --force 必須 (台帳に残す)。"
                  f" 台帳: {relpath_for_record(paths['attempts'], root)}", file=sys.stderr)
            return EXIT_REFUSED_FROZEN
        print(f"WARNING: --force により失敗済み試行 {len(journal['attempts'])} 件の後に再実行。",
              file=sys.stderr)

    if now < cutoff and not force:
        # cutoff 前に凍結すると評価窓を切り捨てた artifact が marker を占有する
        print(f"REFUSED: 現在時刻 {iso_sec(now)} < cutoff {spec['cutoff']} — 凍結は"
              f" cutoff 到達後に 1 回だけ (§2.5-6、手順書 §2)。意図的な早期凍結は"
              f" --force (manifest に記録)。", file=sys.stderr)
        return EXIT_FAIL

    # ── preflight (API 要求前にローカルで判る失敗条件) ───────────────
    if ohlcv_src:
        if not ohlcv_dst:
            ohlcv_dst = os.path.join(root, "data", "cache",
                                     f"e1_frozen_look{look}_{spec['cutoff'][:10]}")
        miss = missing_ohlcv(ohlcv_src)
        if miss:
            print(f"REFUSED (preflight): OHLCV parquet 欠落 ({len(miss)}/{len(INSTRUMENTS)}):"
                  f" {miss} in {ohlcv_src} — API 要求前に停止 (§2.5-1 fail-loud)。"
                  f" `python3 tools/bt_data_cache.py refresh 15m` 後に再実行。", file=sys.stderr)
            return EXIT_FAIL

    # ── attempt 台帳: 最初の API 要求の前に「試行開始」を永続化 ─────────
    attempt: Dict[str, Any] = {"started_at": iso_sec(now), "status": "in_progress",
                               "force": bool(force), "api_queried": True,
                               "api_base": api_base}
    journal["attempts"].append(attempt)
    _journal_write(paths, journal)

    def _fail(reason: str, **extra: Any) -> None:
        attempt.update({"status": "failed", "reason": reason,
                        "finished_at": iso_sec(utc_now())}, **extra)
        _journal_write(paths, journal)

    # ── 取得 ──────────────────────────────────────────────────────
    snapshots: List[Dict[str, Any]] = []
    fetch_ledger: Dict[str, Dict[str, Any]] = {}
    try:
        for inst in INSTRUMENTS:
            led: Dict[str, Any] = {}
            snapshots.extend(fetch_snapshots(fetcher, inst, cutoff, ledger=led))
            fetch_ledger[inst] = led
        health = fetch_health_log(fetcher, cutoff)
    except Exception as e:                      # 台帳に残してから fail-loud
        _fail(f"fetch error: {type(e).__name__}",
              instruments_fetched=len(fetch_ledger))
        raise

    snap_sum = summarize_snapshots(snapshots)
    if snap_sum["instruments_missing"] and not allow_missing:
        _fail("instruments_missing", instruments_missing=snap_sum["instruments_missing"],
              snapshots_rows=snap_sum["rows_total"], health_rows=len(health))
        print(f"REFUSED: snapshots が 0 行の instrument: {snap_sum['instruments_missing']}"
              f" (§2.5-1 fail-loud。ingest 障害を先に切り分ける。記録だけ残すなら"
              f" --force --allow-missing-instruments — 本番へは既に 1 回問い合わせたので"
              f" 再実行は --force 必須、台帳に残る)。", file=sys.stderr)
        return EXIT_FAIL
    if not health:
        print("WARNING: health_log が 0 行 — §2.2 stale cap 主モード不成立 "
              "(判定器は --fallback-mode を要求する)。", file=sys.stderr)

    # ── staging: artifact ─────────────────────────────────────────
    artifact = build_artifact(snapshots, health, look, cutoff, api_base, frozen_at=now,
                              postponed=postponed)
    staging = paths["artifact_staging"]
    write_json_atomic(staging, artifact)

    # ── §2.5-5(b) API→artifact roundtrip (1 回だけの応答が手元にある今、staging で) ──
    rt = roundtrip_check(snapshots, health, staging, fetch_ledger)
    if not rt["ok"]:
        _fail("roundtrip_mismatch", snapshots_rows=snap_sum["rows_total"],
              health_rows=len(health),
              roundtrip={"snapshots": {k: rt["snapshots"][k] for k in
                                       ("api_rows", "artifact_rows", "keys_match", "digest_match")},
                         "health": {k: rt["health"][k] for k in
                                    ("api_rows", "artifact_rows", "digest_match")}})
        print(f"REFUSED: API→artifact roundtrip 不一致 — snapshots api {rt['snapshots']['api_rows']}"
              f" / artifact {rt['snapshots']['artifact_rows']} (keys_match="
              f"{rt['snapshots']['keys_match']}, digest_match={rt['snapshots']['digest_match']}),"
              f" health api {rt['health']['api_rows']} / artifact {rt['health']['artifact_rows']}"
              f" (digest_match={rt['health']['digest_match']}), ledger_consistent="
              f"{rt['fetch_ledger_consistent']}。marker は書かず前回凍結は不改変。staging は"
              f" {relpath_for_record(staging, root)} に残置 (調査用、開かないこと §6-2)。",
              file=sys.stderr)
        return EXIT_FAIL

    # ── staging: M15 parquet スライス (任意) ──────────────────────
    ohlcv_meta: Dict[str, Dict[str, Any]] = {}
    ohlcv_staging = ""
    if ohlcv_src:
        ohlcv_staging = ohlcv_dst.rstrip(os.sep) + ".staging"
        try:
            ohlcv_meta = slice_ohlcv(ohlcv_src, ohlcv_staging, cutoff)
        except Exception as e:
            _fail(f"ohlcv slice error: {type(e).__name__}",
                  snapshots_rows=snap_sum["rows_total"], health_rows=len(health))
            raise

    # ── 公開 (全検証通過後): artifact → parquet → manifest → marker ──
    os.replace(staging, paths["artifact"])
    entries: Dict[str, str] = {
        relpath_for_record(paths["artifact"], root): sha256_file(paths["artifact"])}
    if ohlcv_src:
        os.makedirs(ohlcv_dst, exist_ok=True)
        for pair, m in ohlcv_meta.items():
            final = os.path.join(ohlcv_dst, os.path.basename(m["path"]))
            os.replace(m["path"], final)
            m["path"] = final
            entries[relpath_for_record(final, root)] = m["sha256"]
        try:
            os.rmdir(ohlcv_staging)
        except OSError:
            pass

    manifest = {
        "look": look, "slug": spec["slug"], "cutoff": spec["cutoff"],
        "postponed": postponed, "original_cutoff": spec["original_cutoff"],
        "postpone_weeks": POSTPONE_WEEKS if postponed else 0,
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
        "roundtrip_check": rt,
        "force_history": force_history,
        "attempts": journal["attempts"],
        "attempts_record": relpath_for_record(paths["attempts"], root),
        "peeking_note": ("§6-2: artifact の値 (skew/avg 価格/buckets) を verdict 期日前に"
                         " 開く・集計する・プロットすることは禁止。この manifest は"
                         " 件数/時刻範囲/sha256 のみ"),
    }
    attempt.update({"status": "frozen", "finished_at": iso_sec(utc_now()),
                    "snapshots_rows": snap_sum["rows_total"], "health_rows": len(health),
                    "artifact_sha256": entries[relpath_for_record(paths["artifact"], root)]})
    manifest["attempts"] = journal["attempts"]
    write_json_atomic(paths["manifest"], manifest)      # manifest が先
    write_sha256_record(paths["sha256"], entries)       # marker は最後 (= 凍結成立)
    _journal_write(paths, journal)

    # ── stdout 要約 (値なし) ───────────────────────────────────────
    print(f"E1 frozen export — look {look} ({spec['slug']}), cutoff {spec['cutoff']}"
          + (f" [postponed +{POSTPONE_WEEKS}w from {spec['original_cutoff']}]" if postponed else ""),
          file=out)
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
    print(f"  roundtrip API->artifact: OK (snapshots {rt['snapshots']['artifact_rows']}/"
          f"{rt['snapshots']['api_rows']}, health {rt['health']['artifact_rows']}/"
          f"{rt['health']['api_rows']}, ledger consistent)", file=out)
    for p, h in sorted(entries.items()):
        print(f"  sha256 {h}  {p}", file=out)
    print(f"  manifest: {relpath_for_record(paths['manifest'], root)}", file=out)
    print(f"  attempts: {relpath_for_record(paths['attempts'], root)}"
          f" ({len(journal['attempts'])} attempt)", file=out)
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
    ap.add_argument("--postponed", action="store_true",
                    help="§2.5-3 family gate 不成立による 4 週 postpone 後の凍結 (look 1 のみ、"
                         "cutoff 2026-11-05 / verdict 11-12、別 marker。元凍結は不改変)")
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
                    help="既存 .sha256 記録を再計算して突合 (ファイル完全性) + manifest の"
                         " roundtrip_check (§2.5-5(b)、凍結時に記録済み) を表示")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args(argv)

    if args.postponed and args.look != 1:
        print("ERROR: --postponed は --look 1 のみ (§2.5-3 postpone は first look に限る)",
              file=sys.stderr)
        return EXIT_FAIL

    if args.verify:
        res = verify_record(args.verify)
        for p, st in res["files"].items():
            print(f"  {st:8s} {p}")
        rt = res.get("roundtrip")
        if rt is None:
            print(f"  manifest: {res['manifest']} — roundtrip (§2.5-5(b)) 未記録 = 凍結不完全")
        else:
            print(f"  roundtrip (§2.5-5(b), recorded at freeze): "
                  f"{'OK' if rt['ok'] else 'FAIL'} (snapshots {rt['snapshots_rows']},"
                  f" health {rt['health_rows']}); manifest {res['manifest']}")
        print(f"verify: {'OK' if res['ok'] else 'FAIL'} ({res['n']} files)")
        return EXIT_OK if res["ok"] else EXIT_FAIL

    fetcher = http_fetcher(args.api_base, timeout=args.timeout)
    if args.dry_run_health:
        return run_dry_run_health(fetcher, limit=max(1, min(args.limit, 50)))

    paths = default_paths(args.look, args.out_dir, postponed=args.postponed)
    ohlcv_src = ""
    if args.slice_ohlcv:
        ohlcv_src = args.ohlcv_src or os.path.join(repo_root(), "data", "cache", "massive")
    return run_freeze(fetcher, args.look, paths, api_base=args.api_base,
                      force=args.force, allow_missing=args.allow_missing_instruments,
                      ohlcv_src=ohlcv_src, ohlcv_dst=args.ohlcv_dst,
                      postponed=args.postponed)


if __name__ == "__main__":
    sys.exit(main())
