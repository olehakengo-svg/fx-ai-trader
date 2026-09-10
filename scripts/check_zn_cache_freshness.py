#!/usr/bin/env python3
"""ZN=F 1h キャッシュの右端鮮度 pin — zn-cache-refresh.yml の「読み手」(rule:R3).

背景 (2026-09-10):
  zn-cache-refresh.yml は 2026-08-17〜09-07 の 4/4 全 run が失敗していた。
  fetch は成功し (rows 14225→14537, 右端 2026-09-04 まで取得)、commit 段の
  素の `git add data/cache/yield/ZN_F_1h.parquet` が .gitignore の
  `data/cache/` に拒否され exit 1 — 取得したデータは毎回そのまま捨てられた。
  run は 4 回赤かったが、赤を読む者がいなかった。「収集済み ≠ 監視済み」。

  放置すると registry `ws3-round4-eur-divergence-conditional` の発火条件
  (cache 被覆 2026-11-15+ へ延伸) が永遠に不成立 = E1 FAIL 時の代替供給
  1 本が無期限死亡する。yfinance 1h 窓は rolling 730d なので、止まった
  キャッシュは左端の歴史も毎日失う。

このスクリプトの契約:
  - data/cache/yield/ZN_F_1h.parquet の右端 (index.max) を読み、実時間で
    ``ZN_CACHE_MAX_AGE_DAYS`` (SSOT: modules/freshness_policy.py) を超えて
    いたら exit 1。weekly-audit.yml が週次で実行する (配線 pin は
    tests/test_zn_cache_freshness_pin.py)。
  - ファイル欠損 / 空 / 読取り不能も **stale 側に倒して exit 1**。
    「無ければ skip」は 126 日 no-op の原因そのもの (freshness_policy 参照)。
  - stale 時は DISCORD_ERROR_WEBHOOK_URL があれば Discord へも通知する
    (best-effort)。run の赤だけを読み手にしない — それが今回の故障型。

使用方法:
  python3 scripts/check_zn_cache_freshness.py [--path <parquet>]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.freshness_policy import ZN_CACHE_MAX_AGE_DAYS  # noqa: E402

DEFAULT_CACHE_PATH = ROOT / "data" / "cache" / "yield" / "ZN_F_1h.parquet"


def run_check(
    path: Path | str = DEFAULT_CACHE_PATH, now: datetime | None = None
) -> tuple[bool, str]:
    """右端鮮度を判定する。戻り値は (ok, 人間可読メッセージ)。

    ok=False は「stale」だけでなく「読めない / 無い / 空」を含む —
    unknown を ok 側に畳むと沈黙するため、必ず fail 側に倒す。
    """
    now = now or datetime.now(timezone.utc)
    path = Path(path)

    if not path.exists():
        return False, f"ZN cache が存在しない: {path}"

    try:
        import pandas as pd

        df = pd.read_parquet(path)
    except Exception as exc:  # 読取り不能 = unknown → fail 側
        return False, f"ZN cache が読めない ({type(exc).__name__}: {exc})"

    if len(df) == 0:
        return False, f"ZN cache が空 (0 行): {path}"

    right_edge = pd.Timestamp(df.index.max())
    if right_edge.tzinfo is None:
        right_edge = right_edge.tz_localize("UTC")
    age_days = (now - right_edge.to_pydatetime()) / timedelta(days=1)

    detail = (
        f"右端 {right_edge.isoformat()} / 年齢 {age_days:.1f} 日 "
        f"(閾値 {ZN_CACHE_MAX_AGE_DAYS} 日, {len(df)} 行)"
    )
    if age_days > ZN_CACHE_MAX_AGE_DAYS:
        return False, (
            f"ZN cache STALE: {detail} — zn-cache-refresh.yml が失敗している"
            f"可能性が高い。run log を確認せよ (2026-08〜09 の故障型: fetch"
            f" 成功 → commit 段で死亡)"
        )
    return True, f"ZN cache OK: {detail}"


def _notify_discord(message: str) -> None:
    """DISCORD_ERROR_WEBHOOK_URL へ best-effort 通知 (失敗しても判定は変えない)."""
    url = os.environ.get("DISCORD_ERROR_WEBHOOK_URL", "").strip()
    # scheme guard: env 由来の URL を https 以外 (file:// 等) で開かない
    if not url.startswith("https://"):
        return
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(
                {"content": f"🔴 **ZN cache freshness FAIL** — {message}"}
            ).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "FX-KB-Monitor/1.0",
            },
        )
        # https:// 固定 (上の scheme guard) — file:// 等は到達しない
        urllib.request.urlopen(req, timeout=15)  # nosemgrep: dynamic-urllib-use-detected
    except Exception as exc:  # 通知失敗は stderr に残すのみ
        print(f"discord notify failed: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path", default=str(DEFAULT_CACHE_PATH), help="parquet path (test 用)"
    )
    args = parser.parse_args(argv)

    ok, message = run_check(args.path)
    print(message)
    if not ok:
        _notify_discord(message)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
