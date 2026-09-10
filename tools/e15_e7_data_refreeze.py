"""E15/E7 phase-1 データ前提修理 — plain 15m parquet の台帳再現復元ツール。

背景 (2026-07-29): E15/E7 pre-reg の coverage 台帳
(`raw/bt-results/e15_e7_pair_coverage.json`, 2026-07-21 凍結) が参照する
plain `{pair}_15m.parquet` 13 本のうち 11 本が、各種 explore の短い --days
フル取得 (`tools/fetch_massive_data.py` の無条件 overwrite) で短縮上書き
され、`event_modality_oos_verdict.py::load_and_verify_bars` の 3 点検証
(first / explore_coverage / rows@ledger_last) を再現できなくなった。
phase-1 discovery (2026-08-21) / OOS verdict (2026-08-28) はこのままでは
BLOCKED になる。

本ツールは MASSIVE からフル歴史を再取得し、台帳 first で head trim した上で
3 点再現を検証、**PASS したペアのみ** plain path へ書き戻す (現ファイルは
.bak 退避)。再現 FAIL は書き戻さず delta を JSON 報告する (観測前
AMENDMENT の判断材料)。--freeze-dir 指定で検証済みファイルの凍結コピー +
sha256 manifest も作成する (cron/explore の再 clobber に対する保険)。

価格データのみ接触。イベント×リターン結合統計は一切計算しない (§10-1)。

Usage:
    python3 tools/e15_e7_data_refreeze.py --dry-run
    python3 tools/e15_e7_data_refreeze.py --pairs USD_JPY,EUR_AUD
    python3 tools/e15_e7_data_refreeze.py --freeze-dir data/cache/massive/e15_e7_frozen
    # phase-1 実行前の pre-flight (API 不要、13 ペア全検証):
    python3 tools/e15_e7_data_refreeze.py --verify-only
    # clobber 再発時の復元 (API 不要、manifest sha256 照合込み):
    python3 tools/e15_e7_data_refreeze.py --restore-from-frozen data/cache/massive/e15_e7_frozen
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

# 台帳検証を verdict ツールと同一実装で行うため tools/ を import path に足す
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_TOOLS_DIR)
for _p in (_PROJECT_ROOT, _TOOLS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

COVERAGE_JSON = "knowledge-base/raw/bt-results/e15_e7_pair_coverage.json"
MASSIVE_DIR = os.path.join("data", "cache", "massive")
BAK_SUFFIX = ".bak-pre-refreeze-2026-07-29"
# 台帳 first 2013-10-24 を確実に含む取得日数 (2026-07-29 起点 4662 日 + margin)
DEFAULT_DAYS = 4675
# 2026-07-29 時点で台帳再現不能だった 11 ペア (EUR_JPY / EUR_GBP は再現 OK)
DEFAULT_BROKEN = [
    "USD_JPY", "EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD", "USD_CAD",
    "USD_CHF", "GBP_JPY", "AUD_JPY", "NZD_JPY", "EUR_AUD",
]


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_against_ledger(df, led: dict, explore_window: list) -> dict:
    """verdict ツールと同じ 3 点検証。戻り値 = 不一致項目 dict (空なら PASS)。"""
    import pandas as pd

    import event_modality_lib as L

    cov = round(
        L.market_time_coverage(df, explore_window[0], explore_window[1]), 4
    )
    led_last = pd.Timestamp(led["last"])
    rows_at_led_last = int((df.index <= led_last).sum())
    checks = {
        "first": (str(df.index[0]), led["first"]),
        "explore_coverage": (cov, led["explore_coverage"]),
        "rows_at_ledger_last": (rows_at_led_last, led["rows"]),
    }
    return {k: v for k, v in checks.items() if v[0] != v[1]}


def refetch_pair(pair: str, led: dict, days: int):
    """MASSIVE フル再取得 → 台帳 first で head trim した frame を返す。"""
    import pandas as pd

    from modules.data import fetch_ohlcv_massive

    df = fetch_ohlcv_massive(pair, "15m", days)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df.loc[df.index >= pd.Timestamp(led["first"])]


def freeze_copy(pairs: list, freeze_dir: str, manifest_path: str) -> dict:
    """検証済み plain parquet を凍結 dir へコピーし sha256 manifest を書く。"""
    os.makedirs(freeze_dir, exist_ok=True)
    manifest = {}
    for pair in pairs:
        src = os.path.join(MASSIVE_DIR, f"{pair}_15m.parquet")
        dst = os.path.join(freeze_dir, f"{pair}_15m.parquet")
        shutil.copy2(src, dst)
        manifest[pair] = {
            "sha256": _sha256(dst),
            "bytes": os.path.getsize(dst),
        }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    return manifest


def _load_plain(pair: str):
    """plain parquet を UTC index で読む。無ければ None。"""
    import pandas as pd

    path = os.path.join(MASSIVE_DIR, f"{pair}_15m.parquet")
    if not os.path.exists(path):
        return None
    df = pd.read_parquet(path)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def verify_all(ledger: dict, explore_window: list) -> dict:
    """13 ペア plain parquet の台帳再現を fetch なしで検証。"""
    status = {}
    for pair in ledger:
        df = _load_plain(pair)
        if df is None:
            status[pair] = {"status": "MISSING"}
            continue
        bad = verify_against_ledger(df, ledger[pair], explore_window)
        status[pair] = ({"status": "OK"} if not bad else
                        {"status": "MISMATCH", "deltas": {
                            k: {"current": v[0], "ledger": v[1]}
                            for k, v in bad.items()}})
    return status


VERDICT_JSON = "knowledge-base/raw/bt-results/e15_phase0_oos_verdict.json"


def restore_from_source(src_dir: str, ledger: dict,
                        explore_window: list) -> dict:
    """任意ソース dir (例: phase-0 実行 worktree) から byte-exact 復元。

    phase-0 verdict の data_ledger sha256 と一致するファイルのみ書き戻す
    (現ファイルは .bak 退避)。ベンダー再取得より強い provenance:
    verdict が実際に走ったバイト列そのものを復元する。
    """
    with open(VERDICT_JSON, encoding="utf-8") as f:
        verdict_ledger = json.load(f)["data_ledger"]
    results = {}
    for pair in ledger:
        src = os.path.join(src_dir, f"{pair}_15m.parquet")
        if not os.path.exists(src):
            results[pair] = {"status": "NO_SOURCE_FILE"}
            continue
        got = _sha256(src)
        want = verdict_ledger.get(pair, {}).get("sha256")
        if got != want:
            results[pair] = {"status": "SOURCE_SHA_MISMATCH",
                             "got": got, "want": want}
            continue
        dst = os.path.join(MASSIVE_DIR, f"{pair}_15m.parquet")
        if os.path.exists(dst) and not os.path.exists(dst + BAK_SUFFIX):
            shutil.copy2(dst, dst + BAK_SUFFIX)
        shutil.copy2(src, dst)
        results[pair] = {"status": "RESTORED_BYTE_EXACT", "sha256": got}
    return results


def restore_from_frozen(frozen_dir: str, ledger: dict,
                        explore_window: list) -> dict:
    """MISSING/MISMATCH の plain を凍結コピーから復元 (manifest sha256 照合)。"""
    manifest_path = os.path.join(
        "knowledge-base", "raw", "bt-results",
        "e15_e7_frozen_manifest_2026-07-29.json")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    results = {}
    for pair, st in verify_all(ledger, explore_window).items():
        if st["status"] == "OK":
            results[pair] = {"status": "OK_UNTOUCHED"}
            continue
        src = os.path.join(frozen_dir, f"{pair}_15m.parquet")
        if not os.path.exists(src):
            results[pair] = {"status": "NO_FROZEN_COPY"}
            continue
        got = _sha256(src)
        want = manifest.get(pair, {}).get("sha256")
        if got != want:
            results[pair] = {"status": "FROZEN_SHA_MISMATCH",
                             "got": got, "want": want}
            continue
        dst = os.path.join(MASSIVE_DIR, f"{pair}_15m.parquet")
        shutil.copy2(src, dst)
        results[pair] = {"status": "RESTORED_FROM_FROZEN"}
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", default=_PROJECT_ROOT,
                        help="repo root (canonical data/cache の場所)")
    parser.add_argument("--pairs", default=",".join(DEFAULT_BROKEN))
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch+verify のみ、書き戻しなし")
    parser.add_argument("--verify-only", action="store_true",
                        help="fetch なしで 13 ペアの台帳再現を検証")
    parser.add_argument("--restore-from", default=None, metavar="DIR",
                        help="任意 dir から byte-exact 復元 (phase-0 verdict "
                             "sha256 照合、fetch なし)")
    parser.add_argument("--restore-from-frozen", default=None, metavar="DIR",
                        help="凍結コピーから MISSING/MISMATCH を復元 (fetch なし)")
    parser.add_argument("--freeze-dir", default=None,
                        help="検証済み 13 ペアの凍結コピー先 (相対=root 基準)")
    parser.add_argument("--out", default=None,
                        help="結果 JSON の出力先 (default: stdout のみ)")
    args = parser.parse_args(argv)

    os.chdir(args.root)
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(args.root, ".env"))
    except ImportError:
        pass

    with open(COVERAGE_JSON, encoding="utf-8") as f:
        cov_doc = json.load(f)
    ledger = cov_doc["ledger"]
    explore_window = cov_doc["explore_window"]

    if args.verify_only or args.restore_from_frozen or args.restore_from:
        if args.restore_from:
            results = restore_from_source(
                args.restore_from, ledger, explore_window)
        elif args.restore_from_frozen:
            results = restore_from_frozen(
                args.restore_from_frozen, ledger, explore_window)
        else:
            results = verify_all(ledger, explore_window)
        for pair, st in results.items():
            print(f"{pair:9s} {st['status']}"
                  + (f" {st.get('deltas')}" if "deltas" in st else ""),
                  flush=True)
        ok = all(st["status"] in ("OK", "OK_UNTOUCHED",
                                  "RESTORED_FROM_FROZEN",
                                  "RESTORED_BYTE_EXACT")
                 for st in results.values())
        if args.verify_only and ok and args.freeze_dir:
            manifest_path = os.path.join(
                "knowledge-base", "raw", "bt-results",
                "e15_e7_frozen_manifest_2026-07-29.json")
            manifest = freeze_copy(
                list(ledger), args.freeze_dir, manifest_path)
            print(f"frozen {len(manifest)}/{len(ledger)} -> "
                  f"{args.freeze_dir} (manifest: {manifest_path})",
                  flush=True)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=1)
                f.write("\n")
        return 0 if ok else 1

    results = {}
    for pair in [p for p in args.pairs.split(",") if p]:
        led = ledger[pair]
        print(f"=== {pair}: fetching {args.days}d ...", flush=True)
        df = refetch_pair(pair, led, args.days)
        bad = verify_against_ledger(df, led, explore_window)
        if bad:
            results[pair] = {"status": "MISMATCH", "deltas": {
                k: {"refetch": v[0], "ledger": v[1]} for k, v in bad.items()}}
            print(f"  MISMATCH {bad}", flush=True)
            continue
        if args.dry_run:
            results[pair] = {"status": "VERIFIED_DRY_RUN", "rows_full": len(df)}
            print(f"  VERIFIED (dry-run) rows={len(df)}", flush=True)
            continue
        path = os.path.join(MASSIVE_DIR, f"{pair}_15m.parquet")
        if os.path.exists(path) and not os.path.exists(path + BAK_SUFFIX):
            shutil.copy2(path, path + BAK_SUFFIX)
        df.to_parquet(path, engine="pyarrow")
        results[pair] = {
            "status": "RESTORED",
            "rows_full": len(df),
            "explore_coverage": led["explore_coverage"],
            "tail_last": str(df.index[-1]),
        }
        print(f"  RESTORED rows={len(df)}", flush=True)

    n_restored = sum(
        1 for r in results.values()
        if r["status"] in ("RESTORED", "VERIFIED_DRY_RUN"))
    print(f"\nverify/restore: {n_restored}/{len(results)} PASS", flush=True)

    if args.freeze_dir and not args.dry_run:
        all_pass = []
        for pair in ledger:
            path = os.path.join(MASSIVE_DIR, f"{pair}_15m.parquet")
            if not os.path.exists(path):
                continue
            import pandas as pd
            df = pd.read_parquet(path)
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")
            if not verify_against_ledger(df, ledger[pair], explore_window):
                all_pass.append(pair)
        manifest_path = os.path.join(
            "knowledge-base", "raw", "bt-results",
            "e15_e7_frozen_manifest_2026-07-29.json")
        manifest = freeze_copy(all_pass, args.freeze_dir, manifest_path)
        print(f"frozen {len(manifest)}/13 -> {args.freeze_dir} "
              f"(manifest: {manifest_path})", flush=True)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=1)
            f.write("\n")
    return 0 if all(
        r["status"] != "MISMATCH" for r in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
