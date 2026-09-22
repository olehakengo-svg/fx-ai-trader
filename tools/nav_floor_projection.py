"""NAV floor 資金時計 — 実口座 NAV の floor 到達予測日を日次で記録する (F4)。

背景: process-meta-audit-2026-09-07 §2/§6 F4 — NAV floor 到達 (中心推定
2027-02〜04) が M3 ETA (2027-11) より早いのに、枯渇予測日がどの KPI にも
存在しなかった。floor の由来: OANDA JP API 存続条件 = 口座残高 25 万円
(割れると API 停止 = 自動売買の物理停止) + 監査バッファ。

estimand 宣言:
- 測る量   : 本番 OANDA 実口座 NAV (JPY) の実測値と、burn/日 からの floor
             到達推定日 / 残日数。
- 母集団   : /api/demo/status → oanda.heartbeat.nav (実弾口座 heartbeat) と
             status_volume_keeper (keeper telemetry)。
- 時計     : wall (暦日)。市場オープン換算はしない (資金は週末も減らないが
             floor 判定は暦日で行う — 保守側)。
- 読み手   : .github/workflows/daily-report.yml (日次) が --append 実行、
             registry `project-falsification-f4-nav-floor-clock`
             (csv_row_match: days_to_floor <= 90) が毎日読む。
- 注意     : CSV が 7 日以上未更新なら「静か」ではなく「書き手が死んでいる」
             (monitoring-blind 教訓) — 書き手 = daily-report.yml を疑う。

burn 推定器 (2026-09-22 方法変更、rule:R3):
- primary = ``decomposed`` — burn = keeper 確定分 + edge 30d 実現 PnL。
  * keeper 分 = (月次 RT 数 × ¥/RT) ÷ 30.44 [JPY/日]。RT 数は telemetry
    (target_usd ÷ (volume_usd/rt_count)) から、¥/RT は broker tx 実測
    (0.8p RT spread × ¥100/pip @10,000u = ¥80、wiki/index.md L149 tx
    709548〜709596) から取る。月初に集中して支出されるので日割りにする —
    月内位相に依存しない決定論成分。
  * edge 分 = −(trailing 窓の broker NAV Δ − keeper 支出) ÷ 窓日数。窓は
    直前月の keeper burst を跨がないよう開始日を切り上げ (位相カット回避)、
    窓内 keeper 支出は当月 rt_count (telemetry) で正確に差し引く。窓が
    EDGE_MIN_SPAN_DAYS 未満なら 0 + ``edge_basis`` に unavailable を明示
    (「測れなかった」を「0 だった」と折り畳まない — 列で見える)。
- reference = ``fit`` (旧 primary)。直近 FIT_WINDOW_ROWS 行の線形回帰。
  keeper が月初 burst で支出されるため、窓が 1 周期未満の間は月内位相で
  振動する (2026-09-16〜09-21 実測: 6 日で burn が半分近くに動いた)。
  参考列 ``burn_fit_per_day_jpy`` / ``days_to_floor_fit`` として併記のみ。
- registry F4 の condition (days_to_floor <= 90) は不変。``days_to_floor``
  列に書くのは decomposed の値。
"""

from __future__ import annotations

import csv
import json
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "monitoring" / "nav_floor_projection.csv"
APP_BASE_DEFAULT = "https://fx-ai-trader.onrender.com"

# OANDA 残高 25 万 + 監査バッファ (process-meta-audit-2026-09-07 §2 goals-1)
FLOOR_JPY = 262_000.0
# 監査中心推定 burn: (276,304 - 262,000) / ~175d ≈ 82 JPY/日
# (keeper ~¥2,080/月 + エッジドリフト)。fit 参考列の行不足時フォールバック。
DEFAULT_BURN_PER_DAY = 82.0
MIN_ROWS_FOR_FIT = 7
FIT_WINDOW_ROWS = 60
# ── decomposed 推定器の定数 ─────────────────────────────────────────
# keeper 1 RT の実測コスト: 0.8p RT spread × ¥100/pip @10,000u。
# 出所: wiki/index.md L149 (tx 709548〜709596) / ground_capital_clock L18。
KEEPER_JPY_PER_RT = 80.0
# telemetry 不能時のフォールバック RT 数: target $520k ÷ ($10k × 2 per RT)。
KEEPER_RT_PER_MONTH_DEFAULT = 26
DAYS_PER_MONTH = 30.44
# edge 実測窓 (暦日)。keeper 1 周期を含む長さ。
EDGE_WINDOW_DAYS = 30
# 直前月 keeper burst の終了日 (day-of-month)。窓開始がこれ以前に落ちる場合は
# 翌日へ切り上げて burst を跨がない (2026-09 実測 last_rt 09-14)。
KEEPER_BURST_END_DAY = 14
# 切り上げ後の最小窓。これ未満は edge 測定不能 (0 + basis に明示)。
# 14 = 28 日の月 (2 月) で asof=翌月 1 日のとき窓が 02-15→03-01 の 14 日になる
# 下限 — これより大きいと毎年 3 月初に 1〜2 日 unavailable へ落ちる。
EDGE_MIN_SPAN_DAYS = 14

# 先頭 6 列は 2026-09-07 以来の既存列 (registry csv_row_match が読む) — 不変。
LEGACY_FIELDNAMES = ["date", "nav_jpy", "burn_per_day_jpy", "days_to_floor",
                     "floor_date_est", "method"]
FIELDNAMES = LEGACY_FIELDNAMES + [
    "burn_fit_per_day_jpy", "days_to_floor_fit",
    "burn_keeper_per_day_jpy", "burn_edge_per_day_jpy", "edge_basis"]
DAYS_SENTINEL_NO_BURN = 99999  # burn <= 0 (NAV 増加中) の残日数表現


def fetch_status(app_base: str = APP_BASE_DEFAULT,
                 timeout: int = 30) -> dict[str, Any] | None:
    """本番 /api/demo/status の payload を取る。取得不能は None。"""
    if not app_base.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        return None  # file:// 等の scheme 混入を遮断 (semgrep CWE-939)
    try:
        req = urllib.request.Request(
            f"{app_base}/api/demo/status",
            headers={"User-Agent": "fx-nav-floor-projection/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.load(resp)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def nav_from_status(payload: dict[str, Any] | None) -> float | None:
    """heartbeat.nav を float で。無ければ None (0 と折り畳まない)。"""
    nav = (((payload or {}).get("oanda") or {}).get("heartbeat") or {}).get("nav")
    try:
        return float(nav) if nav is not None else None
    except (TypeError, ValueError):
        return None


def keeper_from_status(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """status_volume_keeper telemetry。無い/error は None。"""
    k = (payload or {}).get("status_volume_keeper")
    if not isinstance(k, dict) or "error" in k:
        return None
    return k


def fetch_nav(app_base: str = APP_BASE_DEFAULT, timeout: int = 30) -> float | None:
    """本番 heartbeat から NAV (JPY) を取る。取得不能は None (0 と折り畳まない)。"""
    return nav_from_status(fetch_status(app_base, timeout))


def read_rows(path: Path = CSV_PATH) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fit_burn_per_day(rows: list[dict[str, str]]) -> float | None:
    """直近 FIT_WINDOW_ROWS 行の (日付, NAV) 線形回帰から burn/日を出す (参考列)。

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


# ── decomposed 推定器 ──────────────────────────────────────────────

def keeper_rt_per_month(keeper: dict[str, Any] | None) -> tuple[int, str]:
    """月次 RT 数を telemetry から導く。(rt_per_month, basis)。

    volume_usd / rt_count = 1 RT の出来高 (units × 2)。target_usd をそれで割る。
    telemetry 不能 (None / 0 除算) はフォールバック定数 + basis="default"。
    """
    try:
        target = float((keeper or {}).get("target_usd") or 0)
        volume = float((keeper or {}).get("volume_usd") or 0)
        rt_count = int((keeper or {}).get("rt_count") or 0)
    except (TypeError, ValueError):
        return KEEPER_RT_PER_MONTH_DEFAULT, "default"
    if target > 0 and volume > 0 and rt_count > 0:
        per_rt = volume / rt_count
        if per_rt > 0:
            return max(1, round(target / per_rt)), "api"
    return KEEPER_RT_PER_MONTH_DEFAULT, "default"


def keeper_burn_per_day(rt_per_month: int,
                        jpy_per_rt: float = KEEPER_JPY_PER_RT) -> float:
    """keeper 確定分の日割り burn [JPY/日]。月初集中支出を 30.44 日で均す。"""
    return rt_per_month * jpy_per_rt / DAYS_PER_MONTH


def _prev_month_burst_end(asof: date) -> date:
    first = asof.replace(day=1)
    prev_last = first - timedelta(days=1)
    return prev_last.replace(day=min(KEEPER_BURST_END_DAY, prev_last.day))


def _parse_date(s: Any) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def edge_burn_per_day(rows: list[dict[str, str]], nav_now: float, asof: date,
                      keeper: dict[str, Any] | None,
                      rt_per_month: int,
                      jpy_per_rt: float = KEEPER_JPY_PER_RT) -> tuple[float, str]:
    """edge 30d 実現 PnL を broker NAV Δ の残差で測る。(burn_per_day, basis)。

    edge_jpy = (nav_now − nav_start) + keeper 窓内支出。burn は −edge/日数。
    窓開始 = max(asof − EDGE_WINDOW_DAYS, 直前月 burst 終了日 + 1) — 直前月の
    keeper burst を跨ぐと窓内 keeper 支出が telemetry で確定できないため。
    窓内 keeper 支出は当月 rt_count で確定する (RT は全て月初以降に起きる)。
    測れない場合は (0.0, "unavailable:<理由>") — 列に理由が残る。
    """
    month_start = asof.replace(day=1)
    # 窓開始は当月 1 日より前に置く (当月 RT が全て窓内に入り rt_count で
    # 確定できる)。31 日の月で asof − 30 = 1 日となる 1 日だけの穴を塞ぐ。
    window_start = max(min(asof - timedelta(days=EDGE_WINDOW_DAYS),
                           month_start - timedelta(days=1)),
                       _prev_month_burst_end(asof) + timedelta(days=1))
    start_row = None
    for r in rows:
        d = _parse_date(r.get("date"))
        if d is None or d < window_start or d >= asof:
            continue
        if start_row is None or d < start_row[0]:
            try:
                start_row = (d, float(r["nav_jpy"]))
            except (KeyError, ValueError):
                continue
    if start_row is None:
        return 0.0, f"unavailable:no_row_since_{window_start.isoformat()}"
    start_date, nav_start = start_row
    span = (asof - start_date).days
    if span < EDGE_MIN_SPAN_DAYS:
        return 0.0, f"unavailable:span={span}d<{EDGE_MIN_SPAN_DAYS}d"
    rt_count = 0
    try:
        rt_count = int((keeper or {}).get("rt_count") or 0)
    except (TypeError, ValueError):
        rt_count = 0
    if keeper is None:
        return 0.0, f"unavailable:no_keeper_telemetry(span={span}d)"
    if start_date < month_start:
        keeper_rt_in_window = rt_count  # 当月 RT は全て start_date より後
    else:
        # 窓開始が当月内 (CSV が若い) — 当月 RT の前後分割は telemetry で
        # last_rt_at が start_date 以前なら 0 と確定、それ以外は不能。
        last_rt = _parse_date((keeper or {}).get("last_rt_at"))
        if last_rt is not None and last_rt <= start_date and rt_count >= rt_per_month:
            keeper_rt_in_window = 0
        else:
            return 0.0, f"unavailable:keeper_split_unknown(span={span}d)"
    edge_jpy = (nav_now - nav_start) + keeper_rt_in_window * jpy_per_rt
    burn = -edge_jpy / span
    basis = (f"nav_delta:{start_date.isoformat()}->{asof.isoformat()}:{span}d,"
             f"keeper_rt_in_window={keeper_rt_in_window}")
    return burn, basis


def decomposed_burn_per_day(rows: list[dict[str, str]], nav_now: float,
                            asof: date, keeper: dict[str, Any] | None,
                            jpy_per_rt: float = KEEPER_JPY_PER_RT
                            ) -> dict[str, Any]:
    """primary 推定器。keeper 確定分 + edge 実測分を分解して返す。"""
    rt_per_month, rt_basis = keeper_rt_per_month(keeper)
    k_burn = keeper_burn_per_day(rt_per_month, jpy_per_rt)
    e_burn, e_basis = edge_burn_per_day(rows, nav_now, asof, keeper,
                                        rt_per_month, jpy_per_rt)
    return {"burn": k_burn + e_burn, "keeper": k_burn, "edge": e_burn,
            "rt_per_month": rt_per_month, "rt_basis": rt_basis,
            "edge_basis": e_basis, "method": "decomposed"}


def project(nav_jpy: float, burn_per_day: float,
            asof: date) -> tuple[int, str]:
    """(days_to_floor, floor_date_est) を返す。burn<=0 は sentinel。"""
    if nav_jpy <= FLOOR_JPY:
        return 0, asof.isoformat()
    if burn_per_day <= 0:
        return DAYS_SENTINEL_NO_BURN, "n/a"
    days = int((nav_jpy - FLOOR_JPY) / burn_per_day)
    return days, date.fromordinal(asof.toordinal() + days).isoformat()


def build_row(nav_jpy: float, asof: date, rows: list[dict[str, str]],
              keeper: dict[str, Any] | None) -> dict[str, str]:
    """当日行を組む。days_to_floor = decomposed、fit は参考列。"""
    dec = decomposed_burn_per_day(rows, nav_jpy, asof, keeper)
    days, floor_est = project(nav_jpy, dec["burn"], asof)
    fitted = fit_burn_per_day(rows)
    fit_burn = fitted if fitted is not None else DEFAULT_BURN_PER_DAY
    days_fit, _ = project(nav_jpy, fit_burn, asof)
    fit_label = "" if fitted is not None else "(audit_default)"
    return {"date": asof.isoformat(), "nav_jpy": f"{nav_jpy:.0f}",
            "burn_per_day_jpy": f"{dec['burn']:.1f}", "days_to_floor": str(days),
            "floor_date_est": floor_est, "method": dec["method"],
            "burn_fit_per_day_jpy": f"{fit_burn:.1f}{fit_label}",
            "days_to_floor_fit": str(days_fit),
            "burn_keeper_per_day_jpy": f"{dec['keeper']:.1f}",
            "burn_edge_per_day_jpy": f"{dec['edge']:.1f}",
            "edge_basis": dec["edge_basis"]}


def append_row(nav_jpy: float, asof: date | None = None,
               path: Path = CSV_PATH,
               keeper: dict[str, Any] | None = None) -> dict[str, str]:
    """当日行を追記 (同日既存行は上書き = 日次 4 回 cron でも冪等)。"""
    asof = asof or datetime.now(timezone.utc).date()
    rows = read_rows(path)
    row = build_row(nav_jpy, asof, rows, keeper)
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

    payload = fetch_status(args.app_base)
    nav = nav_from_status(payload)
    if nav is None:
        # 「取りに行けなかった」を「安全」と折り畳まない — 行は書かず明示失敗。
        # cron 側 (daily-report.yml) はこの exit 1 を step outcome で露出する。
        print("[nav_floor] ERROR: NAV 取得不能 (API down?) — 行を書かない")
        return 1
    keeper = keeper_from_status(payload)
    if keeper is None:
        print("[nav_floor] WARN: keeper telemetry 無し — RT 数はフォールバック定数、"
              "edge は unavailable として記録")
    asof = datetime.now(timezone.utc).date()
    if args.append:
        row = append_row(nav, asof=asof, keeper=keeper)
    else:
        row = dict(build_row(nav, asof, read_rows(), keeper), date="(dry-run)")
    print(f"[nav_floor] NAV=¥{float(row['nav_jpy']):,.0f} floor=¥{FLOOR_JPY:,.0f} "
          f"burn={row['burn_per_day_jpy']}/日 ({row['method']}: "
          f"keeper {row['burn_keeper_per_day_jpy']} + edge "
          f"{row['burn_edge_per_day_jpy']} [{row['edge_basis']}]) "
          f"days_to_floor={row['days_to_floor']} est={row['floor_date_est']} "
          f"| fit(ref) burn={row['burn_fit_per_day_jpy']} "
          f"days={row['days_to_floor_fit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
