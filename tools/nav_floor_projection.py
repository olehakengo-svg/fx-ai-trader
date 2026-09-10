"""NAV floor 資金時計 — 実口座 NAV の floor 到達予測日を日次で記録する (F4)。

背景: process-meta-audit-2026-09-07 §2/§6 F4 — NAV floor 到達 (中心推定
2027-02〜04) が M3 ETA (2027-11) より早いのに、枯渇予測日がどの KPI にも
存在しなかった。floor の由来: OANDA JP API 存続条件 = 口座残高 25 万円
(割れると API 停止 = 自動売買の物理停止) + 監査バッファ。

estimand 宣言:
- 測る量   : 本番 OANDA 実口座 NAV (JPY) の実測値と、trailing 線形 burn
             からの floor 到達推定日 / 残日数。
- 母集団   : /api/demo/status → oanda.heartbeat.nav (実弾口座 heartbeat)。
- 時計     : wall (暦日)。市場オープン換算はしない (資金は週末も減らないが
             floor 判定は暦日で行う — 保守側)。
- 読み手   : .github/workflows/daily-report.yml (日次) が --append 実行、
             registry `project-falsification-f4-nav-floor-clock`
             (csv_row_match: days_to_floor <= 90) が毎日読む。
- 注意     : CSV が 7 日以上未更新なら「静か」ではなく「書き手が死んでいる」
             (monitoring-blind 教訓) — 書き手 = daily-report.yml を疑う。
"""

from __future__ import annotations

import csv
import json
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "monitoring" / "nav_floor_projection.csv"
APP_BASE_DEFAULT = "https://fx-ai-trader.onrender.com"

# OANDA 残高 25 万 + 監査バッファ (process-meta-audit-2026-09-07 §2 goals-1)
FLOOR_JPY = 262_000.0
# 監査中心推定 burn: (276,304 - 262,000) / ~175d ≈ 82 JPY/日
# (keeper ~¥2,080/月 + エッジドリフト)。実測行が MIN_ROWS_FOR_FIT 未満の間の
# フォールバック。実測 fit が立ったら使われない。
DEFAULT_BURN_PER_DAY = 82.0
MIN_ROWS_FOR_FIT = 7
FIT_WINDOW_ROWS = 60
FIELDNAMES = ["date", "nav_jpy", "burn_per_day_jpy", "days_to_floor",
              "floor_date_est", "method"]
DAYS_SENTINEL_NO_BURN = 99999  # burn <= 0 (NAV 増加中) の残日数表現


def fetch_nav(app_base: str = APP_BASE_DEFAULT, timeout: int = 30) -> float | None:
    """本番 heartbeat から NAV (JPY) を取る。取得不能は None (0 と折り畳まない)。"""
    if not app_base.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        return None  # file:// 等の scheme 混入を遮断 (semgrep CWE-939)
    try:
        req = urllib.request.Request(
            f"{app_base}/api/demo/status",
            headers={"User-Agent": "fx-nav-floor-projection/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.load(resp)
        nav = (((payload or {}).get("oanda") or {}).get("heartbeat") or {}).get("nav")
        return float(nav) if nav is not None else None
    except Exception:
        return None


def read_rows(path: Path = CSV_PATH) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fit_burn_per_day(rows: list[dict[str, str]]) -> float | None:
    """直近 FIT_WINDOW_ROWS 行の (日付, NAV) 線形回帰から burn/日を出す。

    行数 < MIN_ROWS_FOR_FIT では None (フォールバックへ)。NAV 増加中 (slope
    >= 0) は burn 0 扱いではなく slope をそのまま返す — days_to_floor 側で
    sentinel 化する (「増えているから安全」を silent に固定しない)。
    """
    pts = []
    for r in rows[-FIT_WINDOW_ROWS:]:
        try:
            pts.append((date.fromisoformat(r["date"]).toordinal(),
                        float(r["nav_jpy"])))
        except (KeyError, ValueError):
            continue
    if len(pts) < MIN_ROWS_FOR_FIT:
        return None
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    denom = sum((p[0] - mx) ** 2 for p in pts)
    if denom == 0:
        return None
    slope = sum((p[0] - mx) * (p[1] - my) for p in pts) / denom  # JPY/日 (負=減少)
    return -slope  # burn は「減る速さ」を正で返す


def project(nav_jpy: float, burn_per_day: float,
            asof: date) -> tuple[int, str]:
    """(days_to_floor, floor_date_est) を返す。burn<=0 は sentinel。"""
    if nav_jpy <= FLOOR_JPY:
        return 0, asof.isoformat()
    if burn_per_day <= 0:
        return DAYS_SENTINEL_NO_BURN, "n/a"
    days = int((nav_jpy - FLOOR_JPY) / burn_per_day)
    return days, date.fromordinal(asof.toordinal() + days).isoformat()


def append_row(nav_jpy: float, asof: date | None = None,
               path: Path = CSV_PATH) -> dict[str, str]:
    """当日行を追記 (同日既存行は上書き = 日次 4 回 cron でも冪等)。"""
    asof = asof or datetime.now(timezone.utc).date()
    rows = read_rows(path)
    fitted = fit_burn_per_day(rows)
    if fitted is None:
        burn, method = DEFAULT_BURN_PER_DAY, "audit_default"
    else:
        burn, method = fitted, "fit"
    days, floor_est = project(nav_jpy, burn, asof)
    row = {"date": asof.isoformat(), "nav_jpy": f"{nav_jpy:.0f}",
           "burn_per_day_jpy": f"{burn:.1f}", "days_to_floor": str(days),
           "floor_date_est": floor_est, "method": method}
    rows = [r for r in rows if r.get("date") != row["date"]] + [row]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDNAMES})
    return row


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--append", action="store_true",
                    help="本番 NAV を取得して CSV へ当日行を追記")
    ap.add_argument("--app-base", default=APP_BASE_DEFAULT)
    args = ap.parse_args(argv)

    nav = fetch_nav(args.app_base)
    if nav is None:
        # 「取りに行けなかった」を「安全」と折り畳まない — 行は書かず明示失敗
        print("[nav_floor] ERROR: NAV 取得不能 (API down?) — 行を書かない")
        return 1
    if args.append:
        row = append_row(nav)
    else:
        rows = read_rows()
        fitted = fit_burn_per_day(rows)
        burn = fitted if fitted is not None else DEFAULT_BURN_PER_DAY
        days, floor_est = project(nav, burn, datetime.now(timezone.utc).date())
        row = {"date": "(dry-run)", "nav_jpy": f"{nav:.0f}",
               "burn_per_day_jpy": f"{burn:.1f}", "days_to_floor": str(days),
               "floor_date_est": floor_est,
               "method": "fit" if fitted is not None else "audit_default"}
    print(f"[nav_floor] NAV=¥{float(row['nav_jpy']):,.0f} floor=¥{FLOOR_JPY:,.0f} "
          f"burn={row['burn_per_day_jpy']}/日 ({row['method']}) "
          f"days_to_floor={row['days_to_floor']} est={row['floor_date_est']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
