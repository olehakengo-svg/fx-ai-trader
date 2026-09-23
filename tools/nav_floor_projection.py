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
    709548〜709596) を **telemetry から導いた units (volume_usd/rt_count/2)
    で線形スケール**する (SVK_UNITS は 20k まで変えられ、get_status は units
    を出さないが出来高/RT がそれを運ぶ。PR #285 review P2)。月初に集中して
    支出されるので日割りにする — 月内位相に依存しない決定論成分。
  * edge 分 = −(trailing 窓の broker NAV Δ − keeper 支出) ÷ 窓日数。窓は
    直前月の keeper burst を跨がないよう開始日を切り上げ (位相カット回避)、
    窓内 keeper 支出は当月 rt_count (telemetry) で正確に差し引く。窓が
    EDGE_MIN_SPAN_DAYS 未満なら 0 + ``edge_basis`` に unavailable を明示
    (「測れなかった」を「0 だった」と折り畳まない — 列で見える)。
  * telemetry の ``month`` が asof の月と一致しない間は edge を unavailable
    にする — UTC 月替わり直後 (00:00 cron) は keeper loop が
    ``_roll_counters`` を呼ぶ前で、前月の rt_count (26) が当月支出として
    差し引かれ keeper burn を丸ごと打ち消す (PR #285 review P2)。同日の
    06:00 run が当月 telemetry で上書きする (同日行は冪等)。
- reference = ``fit`` (旧 primary)。直近 FIT_WINDOW_ROWS 行の線形回帰。
  keeper が月初 burst で支出されるため、窓が 1 周期未満の間は月内位相で
  振動する (2026-09-16〜09-21 実測: 6 日で burn が半分近くに動いた)。
  参考列 ``burn_fit_per_day_jpy`` / ``days_to_floor_fit`` として併記のみ。
- registry F4 の condition (days_to_floor <= 90) は不変。``days_to_floor``
  列に書くのは decomposed の値。

入出金調整 (2026-09-23 方法変更、rule:R3):
- edge_jpy は broker NAV Δ の残差なので、窓内の入出金 (OANDA v20 tx type
  ``TRANSFER_FUNDS``) がそのまま edge に化ける — 入金 ¥D で burn_edge が負に
  転じ合計 burn ≤ 0 → project() が sentinel 99999 → F4 が最長 30 日発火不能、
  窓を抜けると逆方向に跳ねる (path-to-win-reassessment-2026-09-22 §9-5 /
  integrated-decision-packet D1)。本番 ``/api/oanda/transfers`` (app.py、
  broker 台帳 read-only) から窓内 TRANSFER_FUNDS を取り、edge_jpy から差し引く。
- 窓の両端は **NAV 採取時刻** で判定する (heartbeat.last_check → 当日行の
  ``nav_ts_utc`` 列)。時刻の無い legacy 端 (2026-09-23 以前の行) に同日の
  入出金が載ると前後が決まらないので unavailable (両端対称、fail-closed)。
- 台帳が取得不能 (route 未デプロイ / OANDA 失敗 / 形式不正) なら edge は
  ``unavailable:transfers_unavailable`` — 「入出金ゼロ」と偽らない。keeper 分は残る。
"""

from __future__ import annotations

import csv
import json
import math
import re
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
# units に線形 (USD_JPY 1 pip = ¥0.01 × units) — KEEPER_REF_UNITS 基準値。
KEEPER_JPY_PER_RT = 80.0
KEEPER_REF_UNITS = 10_000
# target も読めない telemetry のフォールバック RT 数: $520k ÷ ($10k × 2 per RT)。
# target が読めるなら target ÷ (KEEPER_REF_UNITS × 2) を使う (basis target_default_units)。
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
    "burn_keeper_per_day_jpy", "burn_edge_per_day_jpy", "edge_basis",
    "nav_ts_utc"]  # NAV 採取時刻 (heartbeat.last_check) — 入出金の窓境界に使う
DAYS_SENTINEL_NO_BURN = 99999  # burn <= 0 (NAV 増加中) の残日数表現
# ── 入出金台帳 (2026-09-23) ─────────────────────────────────────────
# 本番 app.py の read-only route。OANDA v20 transactions を type=TRANSFER_FUNDS で
# 時間窓照会し、入出金 tx (amount: +入金 / −出金、time: ns 精度 Z) を返す。
TRANSFERS_PATH = "/api/oanda/transfers"
TRANSFER_TX_TYPE = "TRANSFER_FUNDS"
# 台帳の取得窓は edge 窓 (最長 EDGE_WINDOW_DAYS) を余裕込みで覆う。窓判定は時刻で行う。
TRANSFERS_FETCH_MARGIN_DAYS = 2


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


_TS_RE = re.compile(r"^(.*T\d{2}:\d{2}:\d{2})(\.\d+)?([+-]\d{2}:\d{2})$")


def _parse_ts(s: Any) -> datetime | None:
    """RFC3339 / isoformat を aware UTC datetime に。OANDA の ns 精度 (9 桁) と
    末尾 Z を受ける。読めなければ None (0 や now に折り畳まない)。"""
    if not s:
        return None
    txt = str(s).strip()
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    m = _TS_RE.match(txt)
    if not m:
        return None
    frac = (m.group(2) or "")[:7]  # '.' + 最大 6 桁 (datetime は µs まで)
    try:
        return datetime.fromisoformat(m.group(1) + frac + m.group(3)).astimezone(timezone.utc)
    except ValueError:
        return None


def nav_ts_from_status(payload: dict[str, Any] | None) -> datetime | None:
    """heartbeat.last_check (NAV 採取時刻)。無ければ None。"""
    hb = ((payload or {}).get("oanda") or {}).get("heartbeat") or {}
    return _parse_ts(hb.get("last_check"))


def fetch_transfers(app_base: str, d_from: date, d_to: date,
                    timeout: int = 30) -> list[dict[str, Any]] | None:
    """本番 TRANSFERS_PATH から [d_from, d_to) の入出金 tx を取る。取得不能は None。

    None は「台帳を見られなかった」であり「入出金ゼロ」ではない — 呼び手は edge を
    unavailable にする。transactions 配列を持たない payload (error JSON / route 未
    デプロイの 404 HTML) も None。
    """
    if not app_base.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        return None  # file:// 等の scheme 混入を遮断 (semgrep CWE-939)
    try:
        req = urllib.request.Request(
            f"{app_base}{TRANSFERS_PATH}?from={d_from.isoformat()}&to={d_to.isoformat()}",
            headers={"User-Agent": "fx-nav-floor-projection/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.load(resp)
    except Exception:
        return None
    txs = (payload or {}).get("transactions") if isinstance(payload, dict) else None
    if not isinstance(txs, list) or not all(isinstance(t, dict) for t in txs):
        return None
    return txs


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

def _keeper_per_rt_volume(keeper: dict[str, Any] | None) -> float | None:
    """1 RT の出来高 [USD] = volume_usd / rt_count (= units × 2)。不能は None。

    比なので telemetry の月が asof と違っても有効 (前月の RT でも units は同じ)。
    """
    try:
        volume = float((keeper or {}).get("volume_usd") or 0)
        rt_count = int((keeper or {}).get("rt_count") or 0)
    except (TypeError, ValueError):
        return None
    if volume > 0 and rt_count > 0 and volume / rt_count > 0:
        return volume / rt_count
    return None


def keeper_units(keeper: dict[str, Any] | None) -> tuple[int, str]:
    """keeper の 1 RT units を telemetry から導く。(units, basis)。

    get_status は units を出さないが、volume_usd は units × 2 / RT で積むので
    出来高/RT ÷ 2 が units。不能はフォールバック KEEPER_REF_UNITS + "default"。
    """
    per_rt = _keeper_per_rt_volume(keeper)
    if per_rt is None:
        return KEEPER_REF_UNITS, "default"
    return max(1, round(per_rt / 2)), "api"


def keeper_jpy_per_rt(keeper: dict[str, Any] | None) -> tuple[float, str]:
    """1 RT の JPY コストを units で線形スケール。(jpy_per_rt, basis)。

    ¥80 は @10,000u の実測 (USD_JPY 1 pip = ¥0.01 × units なので線形)。
    SVK_UNITS=20000 なら ¥160、5000 なら ¥40 — 月次総額 (target 固定) は
    不変で、RT 数と単価が反比例する。
    """
    units, basis = keeper_units(keeper)
    return KEEPER_JPY_PER_RT * units / KEEPER_REF_UNITS, basis


def keeper_month_mismatch(keeper: dict[str, Any] | None, asof: date) -> str | None:
    """telemetry の month が asof の月と一致しなければ理由文字列、一致なら None。

    month が無い payload も「一致が確認できない」として不一致扱い (fail-closed)。
    本番 get_status は必ず month を出す (modules/status_volume_keeper.py)。
    """
    month = (keeper or {}).get("month")
    want = asof.strftime("%Y-%m")
    if not month:
        return f"keeper_month_unknown(asof={want})"
    if str(month) != want:
        return f"keeper_month_mismatch({month}!={want})"
    return None


def keeper_disabled(keeper: dict[str, Any] | None) -> bool:
    """telemetry が keeper の停止を明示しているか (enabled: false)。

    STATUS_VOLUME_KEEPER_ENABLE=0 のとき get_worker_status は
    {"enabled": false, "running": false, "note": ...} を返す (worker 未起動、
    counters/month なし)。enabled キーが無い payload は「不明」= 有効扱い。
    """
    return isinstance(keeper, dict) and keeper.get("enabled") is False


def keeper_rt_per_month(keeper: dict[str, Any] | None) -> tuple[int, str]:
    """月次 RT 数を telemetry から導く。(rt_per_month, basis)。

    enabled: false (明示停止) / target_usd == 0 (明示ゼロ目標) は計画 RT 数 0
    (basis="disabled" / "target_zero") — 「telemetry 不能」の default 26 を
    当てると走らない keeper の ¥68.3/日 を burn に乗せて F4 が早く発火する
    (PR #285 review P2 4 巡目)。

    volume_usd / rt_count = 1 RT の出来高 (units × 2)。target_usd をそれで割り
    **切り上げる** — keeper worker は毎 RT 前に volume_usd >= target_usd を見て
    止まり、届かなければ丸ごと 1 RT 積むので実行数は ceil(target/per_rt)
    (例 8,000u: 520000/16000 = 32.5 → 33 RT。round なら 32 で過小、PR #285
    review P2 2 巡目)。月初で当月 RT がまだ無い (volume/rt_count = 0) 間は
    target_usd を既定 units (KEEPER_REF_UNITS × 2 /RT) で割る
    (basis="target_default_units") — SVK_MONTHLY_TARGET_USD は可変なので
    $260k なら 13 であって 26 ではない (PR #285 review P2 5 巡目)。固定 26 は
    target も読めない telemetry (None / 型不正) のみ (basis="default")。
    """
    if keeper_disabled(keeper):
        return 0, "disabled"
    try:
        target = float((keeper or {}).get("target_usd") or 0)
    except (TypeError, ValueError):
        return KEEPER_RT_PER_MONTH_DEFAULT, "default"
    if isinstance(keeper, dict) and "target_usd" in keeper and target == 0:
        return 0, "target_zero"
    per_rt = _keeper_per_rt_volume(keeper)
    if target > 0 and per_rt is not None:
        return max(1, math.ceil(target / per_rt - 1e-9)), "api"
    if target > 0:
        # 当月 RT ゼロ (月初 / 週末 / guard skip) — per-RT 出来高は未観測だが
        # target は読める。既定 units で割る (jpy_per_rt も既定 ¥80 @10k と整合)。
        return (max(1, math.ceil(target / (KEEPER_REF_UNITS * 2) - 1e-9)),
                "target_default_units")
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


def transfers_in_window(transfers: list[dict[str, Any]],
                        start_bound: datetime | date,
                        end_bound: datetime | date) -> tuple[float, int, str | None]:
    """窓 (start_bound, end_bound] 内の TRANSFER_FUNDS 合計 [JPY]。(sum, n, reason)。

    bound が datetime なら NAV 採取時刻で厳密に切る (start: tx.time > start、
    end: tx.time <= end)。bound が date (時刻の無い legacy 行 / nav_ts 不明) なら
    日付で切るが、**同日に載る tx は前後が決まらない**ので reason を返す
    (両端対称、fail-closed)。TRANSFER_FUNDS 以外 (REJECT / 約定 / financing) は
    残高を動かさないか trade 由来 (edge 側) なので数えない。amount / time が
    読めない TRANSFER_FUNDS は "transfers_malformed"。reason が None のとき有効。
    """
    total, n = 0.0, 0
    for tx in transfers:
        if (tx or {}).get("type") != TRANSFER_TX_TYPE:
            continue
        ts = _parse_ts(tx.get("time"))
        try:
            amount = float(tx.get("amount"))
        except (TypeError, ValueError):
            amount = None
        if ts is None or amount is None or math.isnan(amount):
            return 0.0, 0, f"transfers_malformed(id={tx.get('id')})"
        tx_day = ts.date()
        # start 側: 採取時刻より後の tx のみ Δ に含まれる
        if isinstance(start_bound, datetime):
            if ts <= start_bound:
                continue
        else:
            if tx_day == start_bound:
                return 0.0, 0, f"transfer_on_start_bound({start_bound.isoformat()},id={tx.get('id')})"
            if tx_day < start_bound:
                continue
        # end 側: 採取時刻以前の tx のみ nav_now に反映済み
        if isinstance(end_bound, datetime):
            if ts > end_bound:
                continue
        else:
            if tx_day == end_bound:
                return 0.0, 0, f"transfer_on_asof_bound({end_bound.isoformat()},id={tx.get('id')})"
            if tx_day > end_bound:
                continue
        total += amount
        n += 1
    return total, n, None


def edge_burn_per_day(rows: list[dict[str, str]], nav_now: float, asof: date,
                      keeper: dict[str, Any] | None,
                      jpy_per_rt: float = KEEPER_JPY_PER_RT,
                      transfers: list[dict[str, Any]] | None = None,
                      nav_ts: datetime | None = None) -> tuple[float, str]:
    """edge 30d 実現 PnL を broker NAV Δ の残差で測る。(burn_per_day, basis)。

    edge_jpy = (nav_now − nav_start) − 窓内入出金 + keeper 窓内支出。burn は −edge/日数。
    入出金 (``transfers`` = TRANSFER_FUNDS tx の台帳) は broker NAV Δ に乗るが edge
    ではない — 差し引かないと入金 ¥D が窓の間 burn を負にし F4 を盲目化する
    (2026-09-23)。台帳が None (取得不能) は「ゼロ」と偽らず unavailable。窓の両端は
    NAV 採取時刻 (start_row.nav_ts_utc / ``nav_ts``) で判定、時刻の無い端に同日の
    tx が載れば unavailable (transfers_in_window)。
    窓開始 = max(asof − EDGE_WINDOW_DAYS, 直前月 burst 終了日 + 1) — 直前月の
    keeper burst を跨ぐと窓内 keeper 支出が telemetry で確定できないため。
    窓内 keeper 支出は当月 rt_count で確定する (RT は全て月初以降に起きる)。
    telemetry の month が asof と違えば rt_count は前月分なので unavailable。
    窓開始が当月内 (CSV が若い) のときは rt_count == 0 のみ確定 (当月 RT なし)。
    last_rt_at で前後分割はしない — ``_recover_stale_trades`` は rt_count を
    増やしても last_rt_at を更新しない (status_volume_keeper.py L321-322) ので
    「last_rt_at ≤ 窓開始 ∧ 当月完了」でも窓内に回収 RT の損失が残り得る
    (PR #285 review P2 3 巡目)。測れない場合は (0.0, "unavailable:<理由>")。
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
                start_row = (d, float(r["nav_jpy"]), _parse_ts(r.get("nav_ts_utc")))
            except (KeyError, ValueError):
                continue
    if start_row is None:
        return 0.0, f"unavailable:no_row_since_{window_start.isoformat()}"
    start_date, nav_start, start_ts = start_row
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
    if keeper_disabled(keeper):
        # 停止中の payload は counters/month を持たない。窓の途中で止めた場合
        # 窓内 RT が残り得るので 0 と確定できない (fail-closed)。
        return 0.0, f"unavailable:keeper_disabled(window_rt_unknown,span={span}d)"
    month_reason = keeper_month_mismatch(keeper, asof)
    if month_reason is not None:
        # 月替わり直後は前月の rt_count が残る — 当月支出として差し引くと
        # keeper burn を丸ごと打ち消す。当月 telemetry が来るまで測定不能。
        return 0.0, f"unavailable:{month_reason}(span={span}d)"
    if start_date < month_start:
        keeper_rt_in_window = rt_count  # 当月 RT は全て start_date より後
    elif rt_count == 0:
        keeper_rt_in_window = 0  # 当月 RT なし (回収分も rt_count に乗る)
    else:
        # 窓開始が当月内 (CSV が若い) — 当月 RT の前後分割は telemetry では
        # 確定できない。last_rt_at は回収 (_recover_stale_trades) で更新され
        # ないため「≤ start_date」でも窓内 RT の不在を証明しない。
        return 0.0, f"unavailable:keeper_split_unknown(span={span}d)"
    if transfers is None:
        # 台帳を見られなかった — 入出金ゼロと偽ると入金が edge に化ける (fail-loud)
        return 0.0, f"unavailable:transfers_unavailable(span={span}d)"
    transfer_jpy, n_tx, t_reason = transfers_in_window(
        transfers, start_ts if start_ts is not None else start_date,
        nav_ts if nav_ts is not None else asof)
    if t_reason is not None:
        return 0.0, f"unavailable:{t_reason}(span={span}d)"
    edge_jpy = (nav_now - nav_start) - transfer_jpy + keeper_rt_in_window * jpy_per_rt
    burn = -edge_jpy / span
    basis = (f"nav_delta:{start_date.isoformat()}->{asof.isoformat()}:{span}d,"
             f"keeper_rt_in_window={keeper_rt_in_window},"
             f"transfers_jpy={transfer_jpy:+.0f},n_transfers={n_tx}")
    return burn, basis


def decomposed_burn_per_day(rows: list[dict[str, str]], nav_now: float,
                            asof: date, keeper: dict[str, Any] | None,
                            jpy_per_rt: float | None = None,
                            transfers: list[dict[str, Any]] | None = None,
                            nav_ts: datetime | None = None,
                            ) -> dict[str, Any]:
    """primary 推定器。keeper 確定分 + edge 実測分を分解して返す。

    jpy_per_rt を省略すると telemetry の units でスケールした値を使う
    (SVK_UNITS 変更で F4 トリガが動かない)。明示指定はテスト/監査用。
    transfers (入出金台帳) を省略/None にすると edge は unavailable (台帳未参照を
    ゼロと偽らない)。nav_ts は NAV 採取時刻 (窓の asof 側境界)。
    """
    rt_per_month, rt_basis = keeper_rt_per_month(keeper)
    units, _ = keeper_units(keeper)
    if jpy_per_rt is None:
        jpy_per_rt, _ = keeper_jpy_per_rt(keeper)
    k_burn = keeper_burn_per_day(rt_per_month, jpy_per_rt)
    e_burn, e_basis = edge_burn_per_day(rows, nav_now, asof, keeper, jpy_per_rt,
                                        transfers=transfers, nav_ts=nav_ts)
    return {"burn": k_burn + e_burn, "keeper": k_burn, "edge": e_burn,
            "rt_per_month": rt_per_month, "rt_basis": rt_basis,
            "units": units, "jpy_per_rt": jpy_per_rt,
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
              keeper: dict[str, Any] | None,
              transfers: list[dict[str, Any]] | None = None,
              nav_ts: datetime | None = None) -> dict[str, str]:
    """当日行を組む。days_to_floor = decomposed、fit は参考列。

    decomposed の両成分が未測定 (keeper 計画 0 ∧ edge unavailable) のときは
    burn 0 → sentinel 99999 (「NAV 減っていない」) に折り畳まず、fit (行不足
    なら audit default) を primary に使い method="fit_fallback" で露出する。
    """
    dec = decomposed_burn_per_day(rows, nav_jpy, asof, keeper,
                                  transfers=transfers, nav_ts=nav_ts)
    fitted = fit_burn_per_day(rows)
    fit_burn = fitted if fitted is not None else DEFAULT_BURN_PER_DAY
    days_fit, _ = project(nav_jpy, fit_burn, asof)
    fit_label = "" if fitted is not None else "(audit_default)"
    primary_burn, method = dec["burn"], dec["method"]
    if dec["keeper"] == 0 and dec["edge_basis"].startswith("unavailable:"):
        primary_burn, method = fit_burn, f"fit_fallback{fit_label}"
    days, floor_est = project(nav_jpy, primary_burn, asof)
    return {"date": asof.isoformat(), "nav_jpy": f"{nav_jpy:.0f}",
            "burn_per_day_jpy": f"{primary_burn:.1f}", "days_to_floor": str(days),
            "floor_date_est": floor_est, "method": method,
            "burn_fit_per_day_jpy": f"{fit_burn:.1f}{fit_label}",
            "days_to_floor_fit": str(days_fit),
            "burn_keeper_per_day_jpy": f"{dec['keeper']:.1f}",
            "burn_edge_per_day_jpy": f"{dec['edge']:.1f}",
            "edge_basis": dec["edge_basis"],
            "nav_ts_utc": nav_ts.isoformat() if nav_ts is not None else ""}


def append_row(nav_jpy: float, asof: date | None = None,
               path: Path = CSV_PATH,
               keeper: dict[str, Any] | None = None,
               transfers: list[dict[str, Any]] | None = None,
               nav_ts: datetime | None = None) -> dict[str, str]:
    """当日行を追記 (同日既存行は上書き = 日次 4 回 cron でも冪等)。"""
    asof = asof or datetime.now(timezone.utc).date()
    rows = read_rows(path)
    row = build_row(nav_jpy, asof, rows, keeper, transfers=transfers, nav_ts=nav_ts)
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
    now = datetime.now(timezone.utc)
    asof = now.date()
    # NAV 採取時刻 = heartbeat.last_check (入出金の窓境界)。無ければ取得時刻で代用。
    nav_ts = nav_ts_from_status(payload) or now
    # 入出金台帳 — edge 窓 (最長 EDGE_WINDOW_DAYS) を余裕込みで覆う日付範囲を取り、
    # 窓判定は edge_burn_per_day が時刻で行う。取得不能 (None) はそのまま渡す。
    transfers = fetch_transfers(
        args.app_base,
        asof - timedelta(days=EDGE_WINDOW_DAYS + TRANSFERS_FETCH_MARGIN_DAYS),
        asof + timedelta(days=1))
    if transfers is None:
        print("[nav_floor] WARN: 入出金台帳 (TRANSFER_FUNDS) 取得不能 — edge は "
              "unavailable:transfers_unavailable として記録 (入出金ゼロと偽らない)")
    if args.append:
        row = append_row(nav, asof=asof, keeper=keeper, transfers=transfers, nav_ts=nav_ts)
    else:
        row = dict(build_row(nav, asof, read_rows(), keeper, transfers=transfers,
                             nav_ts=nav_ts), date="(dry-run)")
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
