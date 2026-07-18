"""
FF カレンダー歴史 gap の import 経路 (R3 データ基盤、2026-07-18)。

背景 (knowledge-base/wiki/analyses/market-data-ingest-2026-07-18.md §3):
  go-forward capture は modules/market_data_ingest.py が担うが、歴史 gap
  (2023-04〜capture 開始、~170 週) は FF 本体が Cloudflare challenge で
  自動取得不可のため、正規経路で入手した dump (EPSOFT 延長 / 公開 dataset /
  手動 export) を同一テーブル ff_calendar_events へ合流させる。

入力形式: CSV (ヘッダ付き) または JSONL / JSON array。
  必須列: country, title, event_time_utc (ISO8601、'Z' or offset 付き)
  任意列: impact, forecast, previous, actual
  actual を持つ行は actual_source='import:<tag>' で来歴を記録する。
  既存行 (go-forward capture 済み等) は上書きしない —
  actual が NULL の既存行にのみ import の actual を補完する。

usage:
  python3 tools/ff_calendar_import.py --db /path/to/demo_trades.db \
      --input dump.csv --source-tag epsoft-2023-2026 [--dry-run]

モジュールトップ副作用禁止 (lesson): argparse は main() 内。
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import timezone
from typing import Any, Dict, Iterable, List


def normalize_row(raw: Dict[str, Any]) -> Dict[str, str]:
    """入力 1 行 → ff_calendar_events 互換 dict。不正は ValueError (fail-loud)。"""
    from modules.market_data_ingest import _parse_iso
    for key in ("country", "title", "event_time_utc"):
        if not raw.get(key):
            raise ValueError(f"row missing required column: {key} ({raw})")
    dt = _parse_iso(str(raw["event_time_utc"]))
    return {
        "country": str(raw["country"]).strip().upper(),
        "title": str(raw["title"]).strip(),
        "event_time_utc": dt.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "impact": str(raw.get("impact") or ""),
        "forecast": str(raw.get("forecast") or ""),
        "previous": str(raw.get("previous") or ""),
        "actual": str(raw.get("actual") or ""),
    }


def load_input(path: str) -> List[Dict[str, Any]]:
    """CSV / JSONL / JSON array を行 dict list に読む。"""
    if path.endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    with open(path, encoding="utf-8") as fh:
        text = fh.read().strip()
    if text.startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError(f"JSON input is not an array: {path}")
        return data
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def import_rows(db_path: str, rows: Iterable[Dict[str, Any]],
                source_tag: str, dry_run: bool = False) -> Dict[str, int]:
    """行を ff_calendar_events へ合流。counters を返す。

    inserted     — 新規行 (actual があれば同時に記録)
    actual_filled — 既存行の NULL actual を補完
    kept         — 既存行が actual 保持済みで無変更
    invalid      — normalize 失敗 (先頭のエラーは呼び出し側へ raise しない —
                   件数と最初のメッセージを返り値で報告、silent 破棄はしない)
    """
    from modules.market_data_ingest import ensure_market_data_schema
    src = f"import:{source_tag}"
    counters = {"inserted": 0, "actual_filled": 0, "kept": 0, "invalid": 0}
    first_error = ""
    conn = sqlite3.connect(db_path)
    try:
        ensure_market_data_schema(conn)
        now = _now_iso()
        for raw in rows:
            try:
                row = normalize_row(raw)
            except Exception as exc:
                counters["invalid"] += 1
                if not first_error:
                    first_error = f"{type(exc).__name__}: {exc}"
                continue
            existing = conn.execute(
                "SELECT id, actual FROM ff_calendar_events"
                " WHERE country = ? AND title = ? AND event_time_utc = ?",
                (row["country"], row["title"], row["event_time_utc"]),
            ).fetchone()
            if existing is None:
                counters["inserted"] += 1
                if not dry_run:
                    conn.execute(
                        "INSERT INTO ff_calendar_events"
                        " (country, title, event_time_utc, impact, forecast,"
                        "  previous, actual, actual_source,"
                        "  actual_recorded_at, first_seen_at, last_seen_at)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (row["country"], row["title"], row["event_time_utc"],
                         row["impact"], row["forecast"], row["previous"],
                         row["actual"] or None,
                         src if row["actual"] else None,
                         now if row["actual"] else None, now, now),
                    )
            elif existing[1] is None and row["actual"]:
                counters["actual_filled"] += 1
                if not dry_run:
                    conn.execute(
                        "UPDATE ff_calendar_events SET actual = ?,"
                        " actual_source = ?, actual_recorded_at = ?"
                        " WHERE id = ? AND actual IS NULL",
                        (row["actual"], src, now, existing[0]),
                    )
            else:
                counters["kept"] += 1
        if not dry_run:
            conn.commit()
    finally:
        conn.close()
    if first_error:
        counters["first_error"] = first_error  # type: ignore[assignment]
    return counters


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="FF カレンダー歴史 dump を ff_calendar_events へ import")
    parser.add_argument("--db", required=True, help="SQLite DB path")
    parser.add_argument("--input", required=True, help="CSV/JSONL/JSON path")
    parser.add_argument("--source-tag", required=True,
                        help="来歴タグ (actual_source='import:<tag>')")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    rows = load_input(args.input)
    counters = import_rows(args.db, rows, args.source_tag,
                           dry_run=args.dry_run)
    print(json.dumps({"input_rows": len(rows), "dry_run": args.dry_run,
                      **counters}, ensure_ascii=False))
    return 0 if not counters.get("invalid") else 1


def _now_iso() -> str:
    from modules.market_data_ingest import _utcnow_iso
    return _utcnow_iso()


if __name__ == "__main__":
    raise SystemExit(main())
