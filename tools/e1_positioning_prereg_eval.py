#!/usr/bin/env python3
"""E1 positioning contrarian pre-reg 判定ハーネス (rule:R3、LOCK 後成果物)

仕様 SSOT (一言一句準拠、変更禁止):
  knowledge-base/wiki/decisions/e1-positioning-contrarian-prereg-2026-07-16.md
  (🔒 LOCKED 2026-07-17 self-LOCK)

§7 成果物規定:「判定器 tools/e1_positioning_prereg_eval.py (LOCK 後実装、seed 固定。
LOCF resampler / rank タイ規約 / DST 跨ぎ週 / ATR / join / canary leak test を
tests/ に pin してから verdict データに触れる)」— 本ファイルはその判定器。
verdict 実行期日 = first look 2026-10-15 (cutoff 2026-10-08) / second look 2027-01-06。
本日 (実装日 2026-07-17) は合成データ dry-run のみ (§6-2)。

構造的強制 (§6-1 / §6-2):
  - 入力 = 凍結 export artifact (JSON/CSV) + OHLCV M15 parquet のみ。
    本番 API / 本番 DB へのアクセス経路をこのファイルは一切含まない。
  - 生行 (非 LOCF) での signal-return 分析禁止 — 全分析は §2.2 の
    規則グリッド LOCF 系列上でのみ行う (resample_locf が唯一の入口)。
  - 実データへの初適用は verdict 期日 (§6-2)。artifact が "synthetic": true を
    宣言しない限り --verdict-run フラグ必須 (中間 peeking の構造的抑止)。
  - 全 bootstrap は seed 引数必須。default seed = SEED_DEFAULT (固定定数)。

段階分離 (§ 実装規律、関数単位):
  resample → signals → events → ic_leg → ev_legs → gate1 → gate2
  → classify → knife_edge → quality_gates → verdict

実行例 (verdict 期日まで実データに使わないこと):
  python3 tools/e1_positioning_prereg_eval.py \
      --artifact knowledge-base/raw/bt-results/e1_prereg_frozen_export.json \
      --ohlcv-dir data/cache/massive --cutoff 2026-10-08T06:33:31Z \
      --look 1 --verdict-run \
      --out knowledge-base/raw/bt-results/e1_prereg_first_look_2026-10-15.json
  python3 tools/e1_positioning_prereg_eval.py --self-check   # canary suite のみ

モジュールトップ副作用禁止 — env/argparse/network/tzdata 読込は全て関数内。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

# ══════════════════════════════════════════════════════════════════════
# 定数 (全て pre-reg LOCK 済み値 — 変更は pre-reg 改訂 PR 必須)
# ══════════════════════════════════════════════════════════════════════

# seed: 「default seed は pre-reg 実行時に固定する定数」 = verdict 期日 20261015
SEED_DEFAULT = 20261015
N_BOOT_DEFAULT = 10000          # §4.1/§4.2 B=10,000

GRID_STEP_SEC = 20 * 60         # §2.2 20 分規則グリッド (UTC :00/:20/:40)
LOCF_MARGIN_SEC = 60            # §2.2 snapshot_time ≤ t − 60s
STALE_CAP_SEC = 2 * 3600        # §2.2 主モード: verified age > 2h → NA (市場時間)
CYCLE_WINDOW_SEC = 90 * 60      # §2.2 cycle 証跡 (t−90min, t] (市場時間)

SLOTS_PER_BDAY = 72             # 20 分グリッド × 24h
W_SLOTS = 20 * SLOTS_PER_BDAY   # §3.1 W = 20 営業日 ≈ 1,440 スロット
W10_SLOTS = 10 * SLOTS_PER_BDAY # 感度 (Secondary / knife #2-iii)
RANK_MIN_COVERAGE = 0.70        # §3.1 窓内有効被覆 < 70% → rank NA
BURNIN_BDAYS = 20               # §3.1 burn-in = t0 + 20 営業日
S2_LAG_SLOTS = 72               # §3.2 Δ₂₄ = skew(t) − skew(t−72 slots、market-time)

STATS = ("S1", "S2", "S3")      # §3.2 一次統計 3 本 (追加禁止)
H_GRID = (("4h", 16), ("24h", 96))  # §3.3 h grid (M15 bars、拡張禁止)
COMBOS = tuple((s, hname) for s in STATS for hname, _ in H_GRID)  # m=6
H_BARS = dict(H_GRID)

ENTRY_HI, ENTRY_LO = 0.90, 0.10   # §3.4 エントリー閾値 (grid にしない)
REARM_HI, REARM_LO = 0.80, 0.20   # §3.4 hysteresis re-arm
KNIFE_THRESHOLDS = (0.85, 0.95)   # §4.5-2(i) ナイフエッジ近傍のみ
EVENT_RESET_GAP_SEC = STALE_CAP_SEC  # §3.4 直前有効スロットとのギャップ > 2h → リセット

FT_SIGMA_MULT = 1.0               # §3.4 first-touch TP=SL=1.0×σ_h
ATR_N = 14                        # §2.3 ATR14d (NY17:00 roll、完結 daily bar のみ)
ATR_MIN_DAYS = ATR_N + 1          # TR は前日 close を要するため 15 本完結が最小

MIN_TRADES_GATE2 = 60             # §4.2(d) N gate
GATE1_FDR_Q = 0.05                # §4.1 BH-FDR q=0.05 (look 毎分割、§5 α 会計)
GATE2_FDR_Q = 0.05                # §4.2 Gate1 通過 combo への BH
GATE2_P = 0.05                    # §4.2 片側 p ≤ 0.05
STAGEB_FDR_Q = 0.10               # §4.3 Stage B (記述のみ)
MBB_L_BDAYS = 5                   # §4.1 block 長 L=5 営業日
MBB_L_SENS = (3, 10)              # §4.1 感度 (Secondary、判定不使用)
IM_BLOCK_BDAYS = 5                # §4.1 IM 検定 5 営業日 block

JUMP_PP = 20.0                    # §2.5-7 |Δskew| > 20pp
JUMP_MIN_PAIRS = 4                # §2.5-7 primary 6 中 ≥4 ペア同時
JUMP_FWD_SEC = 24 * 3600          # §2.5-7 前方 +24h (市場時間) のみ除外

COVERAGE_MIN = 0.90               # §2.5-1 coverage ≥ 90%
STALE_GAP_SEC = 24 * 3600         # §2.5-2 連続欠測 > 24h (市場時間)
STALE_GAP_FRAC = 0.20             # §2.5-2 除外日 > 評価窓の 20% → ペア除外
FAMILY_MIN_PAIRS = 4              # §2.5-3 primary < 4 → postpone
SANITY_PCT_SUM_TOL = 1.0          # §2.5-4 |long+short−100| > 1.0pp
SANITY_AVG_BAND = 0.10            # §2.5-4 avg 価格が当日レンジ ±10% 外
SANITY_INVESTIGATE_FRAC = 0.01    # §2.5-4 >1% で要調査フラグ

CONF_MIN_WEEKS = 6                # §2.4 confirmatory 評価期間 ≥6 週
CONF_MIN_TRADES = 30              # §2.4 confirmatory pooled trade N ≥ 30

# §2.4 ペア族 (入れ替え禁止) / 付録 A t0 台帳
PRIMARY = ("USD_JPY", "EUR_USD", "GBP_USD", "EUR_JPY", "GBP_JPY", "AUD_JPY")
CONFIRMATORY = ("AUD_USD", "NZD_USD", "USD_CAD", "USD_CHF",
                "NZD_JPY", "EUR_AUD", "EUR_GBP")
JPY_BLOCK = ("USD_JPY", "EUR_JPY", "GBP_JPY", "AUD_JPY")  # §2.4/§4.5-4
T0_PRIMARY = "2026-07-16T06:33:31Z"
T0_CONFIRMATORY = "2026-07-16T07:51:18Z"

# §3.4 摩擦判定値 (往復 pips、今固定 — 実測が後で判明しても変更しない)
FRICTION = {
    "USD_JPY": 2.14, "EUR_USD": 2.00, "GBP_USD": 4.53, "EUR_JPY": 2.50,
    "GBP_JPY": 4.50, "AUD_JPY": 3.125, "EUR_GBP": 3.00, "AUD_USD": 2.50,
    "NZD_USD": 3.00, "USD_CAD": 3.00, "USD_CHF": 3.00, "NZD_JPY": 4.50,
    "EUR_AUD": 4.50,
}

# §7 期日 (データ非依存の固定): cutoff #1 = t0+12 週ちょうど
DEFAULT_CUTOFF_LOOK1 = "2026-10-08T06:33:31Z"
DEFAULT_CUTOFF_LOOK2 = "2026-12-30T06:33:31Z"
YEAR_END_EXCL = ("2026-12-19T00:00:00Z", "2027-01-03T00:00:00Z")  # §7 second look のみ

FRIDAY_BLOCK_NY_HOUR = 15         # §3.4 NY Fri 15:00–17:00 新規 event 禁止


def _pip(pair: str) -> float:
    """§2.3 pip 定義: JPY クロス = 0.01、それ以外 = 0.0001 (EUR_GBP 含む)。"""
    return 0.01 if pair.endswith("_JPY") else 0.0001


# ══════════════════════════════════════════════════════════════════════
# 市場時間 (§2.2 — America/New_York Sun 17:00 open 〜 Fri 17:00 close、DST 追随)
# ══════════════════════════════════════════════════════════════════════

_NY_TZ = None


def _ny():
    """tzdata 読込は初回アクセス時 (モジュールトップ副作用禁止)。"""
    global _NY_TZ
    if _NY_TZ is None:
        from zoneinfo import ZoneInfo
        _NY_TZ = ZoneInfo("America/New_York")
    return _NY_TZ


def _utc(ts: Any) -> datetime:
    """ISO8601 ('Z' / offset / naive=UTC 扱い) → tz-aware UTC datetime。"""
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    txt = str(ts).strip()
    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"
    dt = datetime.fromisoformat(txt)
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ep(dt: datetime) -> float:
    return dt.timestamp()


def is_market_open(ts: datetime) -> bool:
    """§2.2 市場時間: NY ローカル Sun 17:00 open 〜 Fri 17:00 close (DST 追随)。

    境界規約: Sun 17:00:00 ちょうど = open、Fri 17:00:00 ちょうど = closed。
    """
    ny = ts.astimezone(_ny())
    wd = ny.weekday()  # Mon=0 .. Sun=6
    hm = (ny.hour, ny.minute, ny.second, ny.microsecond)
    if wd == 5:                       # Sat
        return False
    if wd == 4:                       # Fri: 17:00 で close
        return hm < (17, 0, 0, 0)
    if wd == 6:                       # Sun: 17:00 で open
        return hm >= (17, 0, 0, 0)
    return True


def _next_transition_utc(ts: datetime) -> datetime:
    """ts より厳密に後の次の open/close 境界 (NY Fri/Sun 17:00) を UTC で返す。

    NY ローカルで境界 datetime を構築するため DST に自動追随する (§2.2 M11)。
    """
    ny = ts.astimezone(_ny())
    d0 = ny.date()
    for k in range(0, 9):
        cd = d0 + timedelta(days=k)
        if cd.weekday() in (4, 6):    # Fri close / Sun open
            cand = datetime(cd.year, cd.month, cd.day, 17, 0, tzinfo=_ny())
            if cand > ny:
                return cand.astimezone(timezone.utc)
    raise RuntimeError("market transition not found (unreachable)")


def market_seconds_between(a: datetime, b: datetime) -> float:
    """a→b の市場時間 (open 区間のみ) 経過秒。b ≤ a は 0。

    §2.2 の age 計測・stale gap・cycle 窓・censoring が全てこれを参照する。
    fast path: 壁時計差が区間内に境界を含まない場合は壁時計差そのもの。
    """
    if b <= a:
        return 0.0
    total = 0.0
    cur = a
    while cur < b:
        nxt = _next_transition_utc(cur)
        seg_end = min(nxt, b)
        if is_market_open(cur):
            total += (seg_end - cur).total_seconds()
        cur = seg_end
    return total


def market_age_exceeds(a: datetime, b: datetime, cap_sec: float) -> bool:
    """market_seconds_between(a, b) > cap_sec か (壁時計 fast path 付き)。

    市場時間 ⊆ 壁時計時間なので、壁時計差 ≤ cap なら市場時間差も ≤ cap。
    """
    wall = (b - a).total_seconds()
    if wall <= cap_sec:
        return False
    return market_seconds_between(a, b) > cap_sec


def market_elapsed_within(a: datetime, b: datetime, window_sec: float) -> bool:
    """a ≤ b かつ market_elapsed(a,b) < window_sec — (b−window, b] 半開窓の判定。"""
    if a > b:
        return False
    wall = (b - a).total_seconds()
    if wall < window_sec:
        return True
    return market_seconds_between(a, b) < window_sec


def build_grid(start: datetime, end: datetime) -> List[datetime]:
    """§2.2 グリッド = UTC :00/:20/:40 の 20 分規則スロットのうち市場時間内のみ。

    start ≤ t ≤ end。週末スロットはここで構造的に存在しない (テスト pin)。
    """
    first = start.replace(second=0, microsecond=0)
    first = first.replace(minute=first.minute - first.minute % 20)
    if first < start:
        first += timedelta(seconds=GRID_STEP_SEC)
    out: List[datetime] = []
    t = first
    step = timedelta(seconds=GRID_STEP_SEC)
    while t <= end:
        if is_market_open(t):
            out.append(t)
        t += step
    return out


def add_business_days(dt: datetime, n: int) -> datetime:
    """UTC 暦の営業日 (Mon–Fri) を n 日進める (時刻保存)。§3.1 burn-in 用。

    NOTE: pre-reg §5 の評価窓例 (t0 2026-07-16 + 20 営業日 = 2026-08-13) と一致。
    """
    d = dt
    added = 0
    while added < n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d


def trading_day(ts: datetime) -> date:
    """NY17:00 roll の取引日 (§2.3 daily bar 境界 / §4.1 営業日 block と同一定義)。

    NY ローカル 17:00 以降は翌暦日に属する。
    """
    ny = ts.astimezone(_ny())
    if (ny.hour, ny.minute, ny.second, ny.microsecond) >= (17, 0, 0, 0):
        return ny.date() + timedelta(days=1)
    return ny.date()


def ny17_utc(d: date) -> datetime:
    """取引日 d の終了境界 (NY ローカル d 17:00) を UTC で返す (DST 追随)。"""
    return datetime(d.year, d.month, d.day, 17, 0, tzinfo=_ny()).astimezone(timezone.utc)


# ══════════════════════════════════════════════════════════════════════
# 入力 (凍結 artifact / OHLCV parquet) — §2.5-6 / §6-1 構造的強制
# ══════════════════════════════════════════════════════════════════════

def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_artifact(path: str, health_path: str = "") -> Dict[str, Any]:
    """凍結 export artifact を読む (JSON / CSV)。

    受理形式:
      - JSON dict: {"snapshots": [...], "health": [...], "synthetic": bool}
      - JSON list: snapshots のみ (health は --health で別ファイル指定)
      - CSV: export_snapshots 列 (buckets_json は JSON 文字列列)
    health 行: {"key": "verified:{inst}:{book}" | "last_cycle_at", "value": iso}
    の**系列** (同一 key の複数観測可)。positioning_health テーブルは 1 行
    upsert (最新のみ) のため、凍結 export は定期 export の追記系列であることを
    想定する — 行 snapshot_time も検証成功の証跡として union する (§2.2)。
    """
    if path.endswith(".csv"):
        import pandas as pd
        df = pd.read_csv(path)
        snaps = df.to_dict("records")
        for r in snaps:
            bj = r.get("buckets_json") or r.get("buckets")
            if isinstance(bj, str):
                try:
                    r["buckets"] = json.loads(bj)
                except Exception:
                    r["buckets"] = None
        data: Dict[str, Any] = {"snapshots": snaps, "health": [], "synthetic": False}
    else:
        with open(path) as f:
            raw = json.load(f)
        if isinstance(raw, list):
            data = {"snapshots": raw, "health": [], "synthetic": False}
        else:
            data = {"snapshots": raw.get("snapshots", []),
                    "health": raw.get("health", []),
                    "synthetic": bool(raw.get("synthetic", False))}
    if health_path:
        with open(health_path) as f:
            hraw = json.load(f)
        rows = hraw if isinstance(hraw, list) else (
            [{"key": k, "value": v} for k, v in hraw.items()])
        data["health"] = list(data.get("health", [])) + rows
    return data


def load_bars(ohlcv_dir: str, pair: str) -> Dict[str, np.ndarray]:
    """OHLCV M15 parquet → numpy 化 (§2.3: 隔離 worktree の cutoff 切詰め parquet)。"""
    import pandas as pd
    fp = os.path.join(ohlcv_dir, f"{pair}_15m.parquet")
    df = pd.read_parquet(fp)
    idx = df.index
    if getattr(idx, "tz", None) is None:
        idx = idx.tz_localize("UTC")
    ep = idx.view("int64").astype(np.int64) // 10 ** 9
    return bars_from_arrays(ep.astype(np.float64),
                            df["Open"].to_numpy(dtype=np.float64),
                            df["High"].to_numpy(dtype=np.float64),
                            df["Low"].to_numpy(dtype=np.float64),
                            df["Close"].to_numpy(dtype=np.float64),
                            source=fp)


def bars_from_arrays(ep, o, h, l, c, source: str = "synthetic") -> Dict[str, np.ndarray]:
    """M15 bar 配列コンテナ (テストは合成配列からここを直接呼ぶ)。"""
    order = np.argsort(ep)
    return {"ep": np.asarray(ep, dtype=np.float64)[order],
            "open": np.asarray(o, dtype=np.float64)[order],
            "high": np.asarray(h, dtype=np.float64)[order],
            "low": np.asarray(l, dtype=np.float64)[order],
            "close": np.asarray(c, dtype=np.float64)[order],
            "source": source}


# ══════════════════════════════════════════════════════════════════════
# 品質 sanity (§2.5-4) — LOCF より前の行レベル機械除外
# ══════════════════════════════════════════════════════════════════════

def sanity_filter(snapshots: List[Dict[str, Any]],
                  bars: Dict[str, Dict[str, np.ndarray]],
                  instruments: Sequence[str]) -> Tuple[Dict[str, Dict[str, np.ndarray]], Dict[str, Any]]:
    """outlook 行の整合 sanity (§2.5-4) を適用し instrument 別 numpy 行列へ。

    - book_type == 'outlook' のみ (OANDA 旧行は型で除外 — §2.1)
    - |pct_long + pct_short − 100| > 1.0pp → 行除外 (件数報告)
    - avg 価格が当日 (NY17 roll 取引日) 価格レンジ ±10% 外 → 行除外 (件数報告)。
      当日 bar が無い (週末 fetch 等) 場合は検査不能 — 除外せず件数記録
    - snapshot_time 単調性確認 (違反は fail-loud フラグ、除外はしない)
    - avg 価格 0/欠損/非正 → 行は残し avg のみ NaN (S3 を当該スロット NA、§2.1)
    """
    rows_by_inst: Dict[str, List[Tuple[float, float, float, float, float]]] = {
        i: [] for i in instruments}
    stats = {"rows_total": 0, "excluded_pct_sum": 0, "excluded_avg_range": 0,
             "avg_range_uncheckable": 0, "monotonicity_violations": 0,
             "rows_kept": 0}
    prev_t: Dict[str, float] = {}
    day_ranges: Dict[str, Dict[date, Tuple[float, float]]] = {}
    for inst in instruments:
        b = bars.get(inst)
        if b is None or len(b["ep"]) == 0:
            day_ranges[inst] = {}
            continue
        dr: Dict[date, Tuple[float, float]] = {}
        days = [trading_day(datetime.fromtimestamp(e, tz=timezone.utc))
                for e in b["ep"]]
        for j, d in enumerate(days):
            lo, hi = dr.get(d, (math.inf, -math.inf))
            dr[d] = (min(lo, b["low"][j]), max(hi, b["high"][j]))
        day_ranges[inst] = dr

    for r in snapshots:
        if r.get("book_type") != "outlook":
            continue
        inst = r.get("instrument")
        if inst not in rows_by_inst:
            continue
        stats["rows_total"] += 1
        t = _utc(r["snapshot_time"])
        tep = _ep(t)
        if inst in prev_t and tep < prev_t[inst]:
            stats["monotonicity_violations"] += 1
        prev_t[inst] = tep
        lt = float(r.get("pct_long_total") or 0.0)
        st = float(r.get("pct_short_total") or 0.0)
        if abs(lt + st - 100.0) > SANITY_PCT_SUM_TOL:
            stats["excluded_pct_sum"] += 1
            continue
        # avg 価格: buckets_json が JSON object (raw payload) の場合のみ (§2.1)
        raw = r.get("buckets")
        avg_l = avg_s = float("nan")
        if isinstance(raw, dict):
            try:
                v = float(raw.get("avgLongPrice") or 0.0)
                avg_l = v if v > 0 else float("nan")
            except (TypeError, ValueError):
                avg_l = float("nan")
            try:
                v = float(raw.get("avgShortPrice") or 0.0)
                avg_s = v if v > 0 else float("nan")
            except (TypeError, ValueError):
                avg_s = float("nan")
        if not (math.isnan(avg_l) and math.isnan(avg_s)):
            dr = day_ranges.get(inst, {}).get(trading_day(t))
            if dr is None:
                stats["avg_range_uncheckable"] += 1
            else:
                lo_b = dr[0] * (1.0 - SANITY_AVG_BAND)
                hi_b = dr[1] * (1.0 + SANITY_AVG_BAND)
                bad = False
                for v in (avg_l, avg_s):
                    if not math.isnan(v) and not (lo_b <= v <= hi_b):
                        bad = True
                if bad:
                    stats["excluded_avg_range"] += 1
                    continue
        rows_by_inst[inst].append((tep, lt, st, avg_l, avg_s))
        stats["rows_kept"] += 1

    out: Dict[str, Dict[str, np.ndarray]] = {}
    for inst, rows in rows_by_inst.items():
        rows.sort(key=lambda x: x[0])
        arr = np.array(rows, dtype=np.float64) if rows else np.zeros((0, 5))
        out[inst] = {"ep": arr[:, 0] if len(rows) else np.zeros(0),
                     "long": arr[:, 1] if len(rows) else np.zeros(0),
                     "short": arr[:, 2] if len(rows) else np.zeros(0),
                     "avg_long": arr[:, 3] if len(rows) else np.zeros(0),
                     "avg_short": arr[:, 4] if len(rows) else np.zeros(0)}
    excl = stats["excluded_pct_sum"] + stats["excluded_avg_range"]
    stats["investigate_flag"] = bool(
        stats["rows_total"] and excl / stats["rows_total"] > SANITY_INVESTIGATE_FRAC)
    return out, stats


def extract_health_events(health: List[Dict[str, Any]],
                          instruments: Sequence[str]) -> Tuple[Dict[str, List[float]], List[float]]:
    """positioning_health 系列 → per-instrument 検証成功時刻 + cycle heartbeat。

    §2.2: verified:{inst}:{book} = fetch+parse 成功 (dedup skip 含む) の時刻。
    last_cycle_at = poll cycle heartbeat (永続化後はこちらを正とする)。
    """
    verified: Dict[str, List[float]] = {i: [] for i in instruments}
    cycles: List[float] = []
    for row in health or []:
        key = str(row.get("key", ""))
        val = row.get("value")
        if not val:
            continue
        try:
            tep = _ep(_utc(val))
        except (ValueError, TypeError):
            continue
        if key == "last_cycle_at":
            cycles.append(tep)
        elif key.startswith("verified:"):
            parts = key.split(":")
            if len(parts) >= 3 and parts[1] in verified:
                verified[parts[1]].append(tep)
    return verified, cycles


# ══════════════════════════════════════════════════════════════════════
# resample (§2.2) — LOCF + stale cap (verified 基準) + cycle 証跡
# ══════════════════════════════════════════════════════════════════════

def resample_locf(rows_by_inst: Dict[str, Dict[str, np.ndarray]],
                  verified_by_inst: Dict[str, List[float]],
                  cycle_events: List[float],
                  grid: List[datetime],
                  stale_cap_sec: float = STALE_CAP_SEC,
                  margin_sec: float = LOCF_MARGIN_SEC,
                  cycle_window_sec: float = CYCLE_WINDOW_SEC) -> Dict[str, Any]:
    """§2.2 の LOCF リサンプル契約 (全分析共通の唯一の入口)。

    - 各 (instrument, t): snapshot_time ≤ t − 60s の最新行を LOCF
    - stale cap (主モード): 検証成功 (verified ∪ 行時刻) からの市場時間 age > 2h → NA
    - cycle 証跡: (t − 90min, t] (市場時間) に heartbeat/検証成功が無ければ
      全ペア NA (worker 死の推定、因果方向は後方のみ)
    返り値 panel: {"slots", "slot_ep", inst: {"long","short","avg_long",
    "avg_short","skew","valid"}, "cycle_ok", "stats"}
    """
    n = len(grid)
    slot_ep = np.array([_ep(t) for t in grid], dtype=np.float64)
    # cycle 証跡イベント = heartbeat ∪ 全 instrument の検証成功時刻
    cyc = sorted(set(list(cycle_events)
                     + [e for evs in verified_by_inst.values() for e in evs]
                     + [e for r in rows_by_inst.values() for e in r["ep"].tolist()]))
    cyc_arr = np.array(cyc, dtype=np.float64)
    cycle_ok = np.zeros(n, dtype=bool)
    for i, t in enumerate(grid):
        pos = int(np.searchsorted(cyc_arr, slot_ep[i], side="right")) - 1
        if pos >= 0:
            ev = datetime.fromtimestamp(cyc_arr[pos], tz=timezone.utc)
            cycle_ok[i] = market_elapsed_within(ev, t, cycle_window_sec)

    panel: Dict[str, Any] = {"slots": grid, "slot_ep": slot_ep,
                             "cycle_ok": cycle_ok}
    na_stats: Dict[str, Dict[str, int]] = {}
    for inst, rows in rows_by_inst.items():
        vals = {k: np.full(n, np.nan) for k in ("long", "short",
                                                "avg_long", "avg_short")}
        valid = np.zeros(n, dtype=bool)
        ver = np.array(sorted(set(list(verified_by_inst.get(inst, []))
                                  + rows["ep"].tolist())), dtype=np.float64)
        st = {"na_no_row": 0, "na_stale": 0, "na_cycle": 0, "valid": 0}
        if len(rows["ep"]):
            locf_pos = np.searchsorted(rows["ep"], slot_ep - margin_sec,
                                       side="right") - 1
        else:
            locf_pos = np.full(n, -1, dtype=int)
        ver_pos = (np.searchsorted(ver, slot_ep, side="right") - 1
                   if len(ver) else np.full(n, -1, dtype=int))
        for i, t in enumerate(grid):
            if not cycle_ok[i]:
                st["na_cycle"] += 1
                continue
            lp = int(locf_pos[i])
            if lp < 0:
                st["na_no_row"] += 1
                continue
            vp = int(ver_pos[i])
            if vp < 0:
                st["na_stale"] += 1
                continue
            last_ver = datetime.fromtimestamp(float(ver[vp]), tz=timezone.utc)
            if market_age_exceeds(last_ver, t, stale_cap_sec):
                st["na_stale"] += 1
                continue
            vals["long"][i] = rows["long"][lp]
            vals["short"][i] = rows["short"][lp]
            vals["avg_long"][i] = rows["avg_long"][lp]
            vals["avg_short"][i] = rows["avg_short"][lp]
            valid[i] = True
            st["valid"] += 1
        panel[inst] = {"long": vals["long"], "short": vals["short"],
                       "avg_long": vals["avg_long"],
                       "avg_short": vals["avg_short"],
                       "skew": vals["long"] - vals["short"], "valid": valid}
        na_stats[inst] = st
    panel["stats"] = na_stats
    return panel


# ══════════════════════════════════════════════════════════════════════
# OHLCV 派生 (§2.3) — mid / daily bar (NY17 roll) / ATR14d / join / 前方リターン
# ══════════════════════════════════════════════════════════════════════

def mid_at_slots(bars: Dict[str, np.ndarray], slot_ep: np.ndarray) -> np.ndarray:
    """mid(t) = t 以前に**確定した**最後の M15 bar の close (§2.3)。

    bar は open + 15min で確定 → open ≤ t − 900 の最後の bar。進行中 bar 禁止。
    """
    pos = np.searchsorted(bars["ep"], slot_ep - 900.0, side="right") - 1
    out = np.full(len(slot_ep), np.nan)
    ok = pos >= 0
    out[ok] = bars["close"][pos[ok]]
    return out


def build_daily_bars(bars: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """M15 mid から NY17:00 roll の daily bar を構築 (§2.3 — MASSIVE の
    daily 集計規約への暗黙依存を断つ)。

    返り値: day (取引日 date list) / end_ep (NY17 境界 UTC) / high / low / close。
    """
    n = len(bars["ep"])
    days: List[date] = []
    hi: List[float] = []
    lo: List[float] = []
    cl: List[float] = []
    cur: Optional[date] = None
    for j in range(n):
        d = trading_day(datetime.fromtimestamp(bars["ep"][j], tz=timezone.utc))
        if d != cur:
            days.append(d)
            hi.append(bars["high"][j])
            lo.append(bars["low"][j])
            cl.append(bars["close"][j])
            cur = d
        else:
            hi[-1] = max(hi[-1], bars["high"][j])
            lo[-1] = min(lo[-1], bars["low"][j])
            cl[-1] = bars["close"][j]
    end_ep = np.array([_ep(ny17_utc(d)) for d in days], dtype=np.float64)
    return {"day": days, "end_ep": end_ep,
            "high": np.array(hi), "low": np.array(lo), "close": np.array(cl)}


def atr_series(daily: Dict[str, np.ndarray], n_atr: int = ATR_N) -> np.ndarray:
    """daily bar 列の ATR (true range 平均、前日 close 必須)。

    index k の値 = day k **までの** 14 本 TR 平均 (day k を含む)。
    有効になるのは k ≥ ATR_MIN_DAYS − 1 (= 14、TR 14 本全てに前日 close がある
    最小)。atr_at() 側が「t より厳密に前に完結した直近 14 本」への割当を行う。
    """
    m = len(daily["end_ep"])
    tr = np.full(m, np.nan)
    for k in range(1, m):
        pc = daily["close"][k - 1]
        tr[k] = max(daily["high"][k] - daily["low"][k],
                    abs(daily["high"][k] - pc),
                    abs(daily["low"][k] - pc))
    atr = np.full(m, np.nan)
    for k in range(n_atr, m):
        atr[k] = float(np.mean(tr[k - n_atr + 1: k + 1]))
    return atr


def atr_at(daily: Dict[str, np.ndarray], atr: np.ndarray, t_ep: float) -> float:
    """ATR14d(t) = t より**厳密に前に完結**した直近 14 本 (§2.3 look-ahead 封鎖)。

    完結 = end_ep < t (境界ちょうど t は「厳密に前」でないため不使用)。
    当日 (進行中) レンジの不混入はテストで pin (§4.5-3 canary 対象)。
    """
    k = int(np.searchsorted(daily["end_ep"], t_ep, side="left")) - 1
    if k < 0 or math.isnan(atr[k]):
        return float("nan")
    return float(atr[k])


def entry_positions(bars: Dict[str, np.ndarray], slot_ep: np.ndarray) -> np.ndarray:
    """エントリー bar = grid t より**厳密に後**に open する最初の M15 bar (§2.3)。

    範囲外は len(bars)。呼び出し側で存在確認。open_time > t は構造 assert 対象。
    """
    return np.searchsorted(bars["ep"], slot_ep, side="right")


def forward_returns(bars: Dict[str, np.ndarray], slot_ep: np.ndarray,
                    h_bars: int) -> np.ndarray:
    """前方リターン (IC レグ、§2.3 一意化) = entry bar open →
    entry + h_bars 番目 bar の open (price 差)。終端 bar が無ければ NaN。"""
    n = len(slot_ep)
    pos = entry_positions(bars, slot_ep)
    out = np.full(n, np.nan)
    nb = len(bars["ep"])
    ok = (pos + h_bars) < nb
    idx = pos[ok]
    # 構造 assert: entry bar open は grid t より厳密に後 (§2.3 契約)
    if len(idx) and not np.all(bars["ep"][idx] > slot_ep[ok]):
        raise RuntimeError("join contract violation: entry bar open <= grid t")
    out[ok] = bars["open"][idx + h_bars] - bars["open"][idx]
    return out


# ══════════════════════════════════════════════════════════════════════
# signals (§3.1/§3.2) — mid-rank / strictly trailing / W=20 営業日
# ══════════════════════════════════════════════════════════════════════

def trailing_rank(values: np.ndarray, w_slots: int = W_SLOTS,
                  min_coverage: float = RANK_MIN_COVERAGE,
                  expanding: bool = False) -> np.ndarray:
    """§3.1 rank 式 (S1/S2/S3 共通、数式固定):
        r(t) = (#{x < v(t)} + 0.5 · #{x = v(t)}) / N_valid  (mid-rank 規約)
    x = t 自身を**含まない** strictly trailing window W 内の有効スロット値。
    窓内有効被覆 < 70% は NA (補間しない)。expanding は感度/knife 専用
    (被覆条件は同じ絶対床 0.70 × W_SLOTS を適用)。
    """
    n = len(values)
    out = np.full(n, np.nan)
    floor_n = min_coverage * w_slots
    for i in range(n):
        v = values[i]
        if math.isnan(v):
            continue
        lo = 0 if expanding else max(0, i - w_slots)
        win = values[lo:i]                      # t 自身を含まない (半開 [lo, i))
        finite = win[~np.isnan(win)]
        nv = finite.size
        if nv < floor_n:
            continue
        out[i] = (float(np.count_nonzero(finite < v))
                  + 0.5 * float(np.count_nonzero(finite == v))) / nv
    return out


def compute_stat_series(panel: Dict[str, Any], inst: str,
                        mid: np.ndarray, atr_slot: np.ndarray) -> Dict[str, np.ndarray]:
    """§3.2 一次統計 3 本の raw 系列 (rank 前) を LOCF グリッド上で計算。"""
    p = panel[inst]
    n = len(panel["slot_ep"])
    skew = np.where(p["valid"], p["skew"], np.nan)
    # S2: Δ₂₄(t) = skew(t) − skew(t−72 slots、market-time)。両端点有効時のみ。
    d24 = np.full(n, np.nan)
    if n > S2_LAG_SLOTS:
        cur = skew[S2_LAG_SLOTS:]
        prev = skew[:-S2_LAG_SLOTS]
        d24[S2_LAG_SLOTS:] = cur - prev
    # S3: pain(t) = [L/100·(avgL−mid) − S/100·(mid−avgS)] / ATR14d(t)。
    # クリップなし。avg 0/欠損/非正は sanity 段で NaN 化済み → 当該スロット NA。
    pain = np.full(n, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        num = (p["long"] / 100.0 * (p["avg_long"] - mid)
               - p["short"] / 100.0 * (mid - p["avg_short"]))
        ok = (p["valid"] & ~np.isnan(num) & ~np.isnan(atr_slot)
              & (atr_slot > 0))
        pain[ok] = num[ok] / atr_slot[ok]
    return {"S1": skew, "S2": d24, "S3": pain}


# ══════════════════════════════════════════════════════════════════════
# jump detector (§2.5-7) — 前方 +24h (市場時間) のみ除外、遡及禁止
# ══════════════════════════════════════════════════════════════════════

def jump_exclusion_mask(panel: Dict[str, Any], pairs: Sequence[str],
                        jump_pp: float = JUMP_PP,
                        min_pairs: int = JUMP_MIN_PAIRS,
                        fwd_sec: float = JUMP_FWD_SEC) -> Tuple[np.ndarray, List[int]]:
    """Δskew = 直前**有効**スロットとの 1-step 差 (LOCF グリッド上)。
    同一スロットで primary ≥4 ペアが |Δskew| > 20pp → イベント時点から
    前方 +24h (市場時間) を全ペア解析除外。後方への遡及除外は行わない (M2)。
    返り値: (除外 mask, jump イベント slot index 一覧)。
    """
    slots = panel["slots"]
    n = len(slots)
    counts = np.zeros(n, dtype=int)
    for inst in pairs:
        skew = np.where(panel[inst]["valid"], panel[inst]["skew"], np.nan)
        prev_val = np.nan
        for i in range(n):
            v = skew[i]
            if math.isnan(v):
                continue
            if not math.isnan(prev_val) and abs(v - prev_val) > jump_pp:
                counts[i] += 1
            prev_val = v
    jump_idx = [i for i in range(n) if counts[i] >= min_pairs]
    mask = np.zeros(n, dtype=bool)
    for i in jump_idx:
        t_e = slots[i]
        j = i
        while j < n:
            # イベント時点を含む前方 [t_e, t_e + 24h (market)] を除外
            wall = (slots[j] - t_e).total_seconds()
            if wall > fwd_sec and market_seconds_between(t_e, slots[j]) > fwd_sec:
                break
            mask[j] = True
            j += 1
    return mask, jump_idx


# ══════════════════════════════════════════════════════════════════════
# events (§3.4) — 交差 + hysteresis + NA リセット + 発火禁止フィルタ
# ══════════════════════════════════════════════════════════════════════

def in_friday_block(ts: datetime) -> bool:
    """§3.4 金曜クローズ前 2h = NY Fri 15:00–17:00 (§2.2 定義参照、DST 追随)。"""
    ny = ts.astimezone(_ny())
    return ny.weekday() == 4 and FRIDAY_BLOCK_NY_HOUR <= ny.hour < 17


def crossing_events(ranks: np.ndarray, slots: List[datetime],
                    entry_hi: float = ENTRY_HI, entry_lo: float = ENTRY_LO,
                    rearm_hi: float = REARM_HI, rearm_lo: float = REARM_LO,
                    reset_gap_sec: float = EVENT_RESET_GAP_SEC,
                    jump_mask: Optional[np.ndarray] = None,
                    year_end: Optional[Tuple[datetime, datetime]] = None,
                    delay_slots: int = 0) -> List[Dict[str, Any]]:
    """§3.4 エントリー event 抽出 (1 ペア × 1 統計)。

    - 交差判定は「直前の**有効**スロットの rank」との比較 (NA を挟む交差規約)
    - 直前有効スロットとのギャップ (市場時間) > 2h → 状態リセット
      (交差不成立・hysteresis 解除、リセット直後の最初の有効スロットは発火しない)
    - hysteresis: 0.80/0.20 を戻すまで同方向再エントリー禁止
    - 発火禁止 (金曜 NY15-17 / jump 除外窓 / 年末窓) は blocked として記録し
      entry は生成しない。交差自体は arm を消費する (保守側 — 発火禁止窓の
      交差を「初回交差」として後で再発火させない)
    - delay_slots: ナイフエッジ #3-(ii) の +1 グリッド slot 遅延機構。
      rank 系列を後方へ shift してから同一機械を回す
    """
    r = ranks
    if delay_slots > 0:
        r = np.concatenate([np.full(delay_slots, np.nan), ranks[:-delay_slots]])
    ye_lo, ye_hi = (year_end if year_end else (None, None))
    events: List[Dict[str, Any]] = []
    prev_r: Optional[float] = None
    prev_slot: Optional[datetime] = None
    armed_hi = True
    armed_lo = True
    for i in range(len(r)):
        v = r[i]
        if math.isnan(v):
            continue
        t = slots[i]
        if prev_slot is not None and market_age_exceeds(prev_slot, t,
                                                        reset_gap_sec):
            prev_r = None
            armed_hi = armed_lo = True
        if prev_r is None:
            prev_r, prev_slot = v, t
            continue
        for direction, armed, crossed in (
                (-1, armed_hi, prev_r < entry_hi <= v),    # 0.90 上抜き → short
                (+1, armed_lo, prev_r > entry_lo >= v)):   # 0.10 下抜き → long
            if not (armed and crossed):
                continue
            blocked = ""
            if jump_mask is not None and jump_mask[i]:
                blocked = "jump"
            elif in_friday_block(t):
                blocked = "friday"
            elif ye_lo is not None and ye_lo <= t < ye_hi:
                blocked = "year_end"
            events.append({"i": i, "dir": direction, "blocked": blocked})
            if direction < 0:
                armed_hi = False
            else:
                armed_lo = False
        if not armed_hi and v <= rearm_hi:
            armed_hi = True
        if not armed_lo and v >= rearm_lo:
            armed_lo = True
        prev_r, prev_slot = v, t
    return events


def first_touch(hi: np.ndarray, lo: np.ndarray, cl: np.ndarray,
                entry_px: float, direction: int, tp_px: float, sl_px: float,
                tie: str = "sl") -> Tuple[float, str]:
    """§3.4 first-touch レグ: TP=SL=1.0×σ_h、timeout=h (close 決済)、
    同一バー内 TP+SL 両ヒットは SL 優先 (ハウス保守規約、stage-2 §3 と同一)。
    tie="fut_close" は Secondary 併記用 (両ヒット bar の close 決済)。
    返り値 = (pnl price 差、leg)。"""
    d = float(direction)
    tp_lvl = entry_px + d * tp_px
    sl_lvl = entry_px - d * sl_px
    for i in range(len(hi)):
        hit_tp = hi[i] >= tp_lvl if d > 0 else lo[i] <= tp_lvl
        hit_sl = lo[i] <= sl_lvl if d > 0 else hi[i] >= sl_lvl
        if hit_tp and hit_sl:
            if tie == "fut_close":
                return float((cl[i] - entry_px) * d), "tie_close"
            return float(-sl_px), "sl"
        if hit_sl:
            return float(-sl_px), "sl"
        if hit_tp:
            return float(tp_px), "tp"
    return float((cl[-1] - entry_px) * d), "timeout"


def build_trades(events: List[Dict[str, Any]], bars: Dict[str, np.ndarray],
                 slots: List[datetime], slot_ep: np.ndarray,
                 daily: Dict[str, np.ndarray], atr: np.ndarray,
                 pair: str, stat: str, hname: str,
                 cutoff: datetime, burnin: datetime,
                 jump_mask: Optional[np.ndarray] = None) -> List[Dict[str, Any]]:
    """EV レグのトレード構築 (§3.4 凍結ルール、combo = stat × h)。

    - 新規 event 受付終端 = cutoff − h (market-time) (§2.3 censoring)。
      さらに first-touch timeout=h が cutoff 内に完結する entry のみ算入
      (窓外にはみ出すトレードの事後裁量処理を構造的に排除)
    - 同一ペア×方向でホールド中の重複エントリー禁止 (h 依存 → combo 毎)
    - exit 主レグ = entry + h_bars の bar open (time-exit)
    - σ_h = daily ATR14(t) × √(h/24h)、ATR は §2.3 定義 (slot t 時点)
    """
    h_bars = H_BARS[hname]
    h_market_sec = h_bars * 900.0
    pip = _pip(pair)
    friction = FRICTION[pair]
    stress_fr = max(friction * 1.25, friction + 1.0)   # §3.4 stress レグ
    nb = len(bars["ep"])
    trades: List[Dict[str, Any]] = []
    open_until = {-1: -math.inf, +1: -math.inf}        # 方向別 exit epoch
    for ev in events:
        if ev["blocked"]:
            continue
        i = ev["i"]
        t = slots[i]
        if t < burnin:
            continue
        # censoring: slot ≤ cutoff − h (market-time)
        if market_seconds_between(t, cutoff) < h_market_sec:
            continue
        d = ev["dir"]
        if slot_ep[i] < open_until[d]:
            continue                                    # ホールド中 (同方向)
        pos = int(np.searchsorted(bars["ep"], slot_ep[i], side="right"))
        if pos + h_bars >= nb:
            continue                                    # cutoff 内に完結しない
        assert bars["ep"][pos] > slot_ep[i], "entry bar open must be > grid t"
        entry_ep = float(bars["ep"][pos])
        entry_px = float(bars["open"][pos])
        exit_pos = pos + h_bars
        exit_ep = float(bars["ep"][exit_pos])
        if exit_ep > _ep(cutoff):
            continue                                    # cutoff 打ち切り
        exit_px = float(bars["open"][exit_pos])
        a = atr_at(daily, atr, slot_ep[i])
        if math.isnan(a) or a <= 0:
            continue                                    # ATR 未定義は算入不能
        pnl_pips = d * (exit_px - entry_px) / pip
        sigma_h = a * math.sqrt(h_bars * 900.0 / (24 * 3600.0))
        w = slice(pos, exit_pos)                        # entry〜entry+h−1 の h 本
        ft_pnl, ft_leg = first_touch(bars["high"][w], bars["low"][w],
                                     bars["close"][w], entry_px, d,
                                     FT_SIGMA_MULT * sigma_h,
                                     FT_SIGMA_MULT * sigma_h)
        ftc_pnl, ftc_leg = first_touch(bars["high"][w], bars["low"][w],
                                       bars["close"][w], entry_px, d,
                                       FT_SIGMA_MULT * sigma_h,
                                       FT_SIGMA_MULT * sigma_h,
                                       tie="fut_close")
        entry_dt = datetime.fromtimestamp(entry_ep, tz=timezone.utc)
        exit_dt = datetime.fromtimestamp(exit_ep, tz=timezone.utc)
        weekend_span = (market_seconds_between(entry_dt, exit_dt)
                        < (exit_ep - entry_ep) - 1.0)
        jump_overlap = False
        if jump_mask is not None:
            j0 = int(np.searchsorted(slot_ep, entry_ep, side="left"))
            j1 = int(np.searchsorted(slot_ep, exit_ep, side="right"))
            jump_overlap = bool(np.any(jump_mask[j0:j1]))
        trades.append({
            "pair": pair, "stat": stat, "h": hname, "dir": d,
            "slot": _iso(t), "entry_time": _iso(entry_dt),
            "exit_time": _iso(exit_dt), "entry_px": entry_px,
            "entry_day": trading_day(entry_dt).isoformat(),
            "pnl_pips": pnl_pips, "net_pips": pnl_pips - friction,
            "stress_net_pips": pnl_pips - stress_fr,
            "ft_pnl_pips": ft_pnl / pip, "ft_net_pips": ft_pnl / pip - friction,
            "ft_leg": ft_leg,
            "ftc_net_pips": ftc_pnl / pip - friction, "ftc_leg": ftc_leg,
            "atr_pips": a / pip,
            "norm_net": (pnl_pips - friction) / (a / pip),
            "weekend_span": bool(weekend_span), "jump_overlap": jump_overlap,
        })
        open_until[d] = exit_ep
    return trades


# ══════════════════════════════════════════════════════════════════════
# ic_leg (§4.1) — contrarian score × 前方リターン、pooled Spearman IC
# ══════════════════════════════════════════════════════════════════════

def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman ρ (rankdata average → Pearson)。N<3 / 定数列は NaN。"""
    if len(x) < 3:
        return float("nan")
    from scipy.stats import rankdata
    rx = rankdata(x)
    ry = rankdata(y)
    sx = np.std(rx)
    sy = np.std(ry)
    if sx == 0 or sy == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def censor_mask(slots: List[datetime], cutoff: datetime,
                h_bars: int) -> np.ndarray:
    """§2.3 censoring: 最終シグナルスロット = cutoff − h (market-time)。
    True = スロット算入可。IC 観測・EV エントリー・coverage 分母に一律適用。"""
    h_sec = h_bars * 900.0
    return np.array([market_seconds_between(t, cutoff) >= h_sec
                     for t in slots], dtype=bool)


def ic_observations(ranks: np.ndarray, fwd: np.ndarray,
                    slots: List[datetime], burnin: datetime,
                    cutoff: datetime, h_bars: int,
                    jump_mask: Optional[np.ndarray] = None,
                    censor_ok: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
    """IC レグの観測点 (1 ペア × 1 combo): burn-in 後・市場時間・品質有効
    スロット全点 (§4.1)。censoring = cutoff − h (coverage 分母と同一規約 §2.3)。
    返り値: {"score", "fwd", "day"(取引日 ordinal), "slot_i"}。
    """
    if censor_ok is None:
        censor_ok = censor_mask(slots, cutoff, h_bars)
    idx: List[int] = []
    for i, t in enumerate(slots):
        if math.isnan(ranks[i]) or math.isnan(fwd[i]):
            continue
        if t < burnin:
            continue
        if jump_mask is not None and jump_mask[i]:
            continue
        if not censor_ok[i]:
            continue
        idx.append(i)
    ii = np.array(idx, dtype=int)
    score = -(ranks[ii] - 0.5) if len(ii) else np.zeros(0)  # §3.2 contrarian
    day = np.array([trading_day(slots[i]).toordinal() for i in idx], dtype=int)
    return {"score": score, "fwd": fwd[ii] if len(ii) else np.zeros(0),
            "day": day, "slot_i": ii}


def pooled_ic(obs_by_pair: Dict[str, Dict[str, np.ndarray]]) -> Tuple[float, Dict[str, Any], int]:
    """pooled IC = per-pair Spearman IC の有効 N 加重平均 (§4.1)。"""
    num = 0.0
    den = 0
    per_pair: Dict[str, Any] = {}
    for pair, o in obs_by_pair.items():
        n = len(o["score"])
        ic = spearman(o["score"], o["fwd"]) if n >= 3 else float("nan")
        per_pair[pair] = {"ic": None if math.isnan(ic) else round(ic, 5), "n": n}
        if not math.isnan(ic):
            num += n * ic
            den += n
    return (num / den if den else float("nan")), per_pair, den


def _day_blocks_draw(days: np.ndarray, L: int, rng: np.random.Generator) -> np.ndarray:
    """営業日 moving-block bootstrap の 1 draw: 暦ブロック (連続 L 営業日)
    を復元抽出し D 日ぶんへ切詰めた「日リスト」を返す (§4.1 — 全ペア同時)。"""
    D = len(days)
    if D <= L:
        return days.copy()
    n_blocks = int(math.ceil(D / L))
    starts = rng.integers(0, D - L + 1, size=n_blocks)
    picked: List[int] = []
    for s in starts:
        picked.extend(range(int(s), int(s) + L))
    return days[np.array(picked[:D], dtype=int)]


def mbb_pvalue(obs_by_pair: Dict[str, Dict[str, np.ndarray]],
               stat_fn, n_boot: int, seed_key: Sequence[int],
               L: int = MBB_L_BDAYS) -> Dict[str, Any]:
    """営業日 MBB (§4.1): 暦ブロックを全ペア同時に resample、per-combo 中心化
    null、片側 p (宣言符号 H1: stat > 0)。両側 p (SIGN-FLIP 用) も併記。

    stat_fn(obs_by_pair_subset) → float。seed_key で決定論 (seed 引数必須)。
    """
    days_all = np.array(sorted(set(
        int(d) for o in obs_by_pair.values() for d in o["day"])), dtype=int)
    point = stat_fn(obs_by_pair)
    if math.isnan(point) or len(days_all) < L + 1:
        return {"point": None, "p_one": None, "p_two": None, "p_neg": None,
                "n_days": int(len(days_all)), "B": 0, "L": L}
    # 日 → 観測 index の索引 (ペア毎)
    day_index: Dict[str, Dict[int, np.ndarray]] = {}
    for pair, o in obs_by_pair.items():
        di: Dict[int, np.ndarray] = {}
        for d in np.unique(o["day"]):
            di[int(d)] = np.where(o["day"] == d)[0]
        day_index[pair] = di
    rng = np.random.default_rng(list(seed_key))
    boots = np.full(n_boot, np.nan)
    for b in range(n_boot):
        sampled_days = _day_blocks_draw(days_all, L, rng)
        sub: Dict[str, Dict[str, np.ndarray]] = {}
        for pair, o in obs_by_pair.items():
            di = day_index[pair]
            parts = [di[int(d)] for d in sampled_days if int(d) in di]
            if not parts:
                continue
            sel = np.concatenate(parts)
            sub[pair] = {"score": o["score"][sel], "fwd": o["fwd"][sel],
                         "day": o["day"][sel]}
        boots[b] = stat_fn(sub) if sub else np.nan
    ok = boots[~np.isnan(boots)]
    if len(ok) == 0:
        return {"point": round(point, 5), "p_one": None, "p_two": None,
                "p_neg": None, "n_days": int(len(days_all)), "B": 0, "L": L}
    null = ok - point                     # per-combo 中心化 null (§4.1 [^10])
    p_one = (1.0 + float(np.sum(null >= point))) / (len(ok) + 1.0)
    p_neg = (1.0 + float(np.sum(null <= point))) / (len(ok) + 1.0)
    p_two = min(1.0, 2.0 * min(p_one, p_neg))
    return {"point": round(point, 5), "p_one": round(p_one, 5),
            "p_neg": round(p_neg, 5), "p_two": round(p_two, 5),
            "n_days": int(len(days_all)), "B": int(len(ok)), "L": L}


def im_test(obs_by_pair: Dict[str, Dict[str, np.ndarray]],
            block_days: int = IM_BLOCK_BDAYS) -> Dict[str, Any]:
    """Ibragimov–Müller 型併設検定 (§4.1 M10): 評価窓を 5 営業日 block に等分し、
    block 毎の pooled IC の平均に片側 1 標本 t 検定 (df = block 数 − 1)。
    first look 40 営業日 / L=5 → 8 block → df=7 (テストで pin)。端数 block は
    捨てて記録する。"""
    from scipy.stats import t as t_dist
    days_all = sorted(set(int(d) for o in obs_by_pair.values()
                          for d in o["day"]))
    n_blocks = len(days_all) // block_days
    if n_blocks < 2:
        return {"p": None, "t": None, "df": None, "n_blocks": n_blocks,
                "block_ics": [], "dropped_days": len(days_all) % block_days}
    block_ics: List[float] = []
    for k in range(n_blocks):
        dset = set(days_all[k * block_days:(k + 1) * block_days])
        sub: Dict[str, Dict[str, np.ndarray]] = {}
        for pair, o in obs_by_pair.items():
            sel = np.array([j for j in range(len(o["day"]))
                            if int(o["day"][j]) in dset], dtype=int)
            if len(sel):
                sub[pair] = {"score": o["score"][sel], "fwd": o["fwd"][sel],
                             "day": o["day"][sel]}
        ic, _, _ = pooled_ic(sub) if sub else (float("nan"), {}, 0)
        if not math.isnan(ic):
            block_ics.append(ic)
    nb = len(block_ics)
    if nb < 2:
        return {"p": None, "t": None, "df": None, "n_blocks": nb,
                "block_ics": [round(v, 5) for v in block_ics],
                "dropped_days": len(days_all) % block_days}
    arr = np.array(block_ics)
    se = float(np.std(arr, ddof=1)) / math.sqrt(nb)
    tval = float(np.mean(arr)) / se if se > 0 else float("inf")
    df = nb - 1
    p = float(t_dist.sf(tval, df))
    return {"p": round(p, 6), "t": round(tval, 5), "df": df, "n_blocks": nb,
            "block_ics": [round(v, 5) for v in block_ics],
            "dropped_days": len(days_all) % block_days}


def bh_fdr(pvals: Dict[str, Optional[float]], q: float,
           m: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
    """Benjamini–Hochberg FDR。m は family 全体で固定可 (§4.1 m=6 —
    p 未定義 combo があっても分母は縮めない)。"""
    defined = {k: v for k, v in pvals.items() if v is not None}
    m_eff = m if m is not None else len(defined)
    order = sorted(defined.items(), key=lambda kv: kv[1])
    k_max = 0
    for rank_i, (_, p) in enumerate(order, start=1):
        if p <= q * rank_i / max(1, m_eff):
            k_max = rank_i
    out: Dict[str, Dict[str, Any]] = {}
    for rank_i, (key, p) in enumerate(order, start=1):
        out[key] = {"p": p, "rank": rank_i,
                    "threshold": round(q * rank_i / max(1, m_eff), 6),
                    "survive": rank_i <= k_max}
    for key, p in pvals.items():
        if p is None:
            out[key] = {"p": None, "rank": None, "threshold": None,
                        "survive": False}
    return out


def gate1_combo(obs_by_pair: Dict[str, Dict[str, np.ndarray]],
                n_boot: int, seed: int, combo_idx: int, look: int,
                sens_boot: Optional[int] = None) -> Dict[str, Any]:
    """Gate 1 (§4.1): p = max(p_MBB, p_IM) の二重検定 (first look)。
    second look は bootstrap 単独 (今固定 — block ≈20 個で粗さ解消)。"""
    def _stat(sub):
        ic, _, _ = pooled_ic(sub)
        return ic
    point, per_pair, n_total = pooled_ic(obs_by_pair)
    mbb = mbb_pvalue(obs_by_pair, _stat, n_boot, (seed, 1, combo_idx))
    im = im_test(obs_by_pair) if look == 1 else {
        "p": None, "t": None, "df": None, "n_blocks": None, "block_ics": [],
        "dropped_days": None, "skipped": "second look は bootstrap 単独 (§4.1)"}
    ps = [p for p in (mbb["p_one"], im.get("p")) if p is not None]
    if look == 1:
        p_gate = (max(mbb["p_one"], im["p"])
                  if (mbb["p_one"] is not None and im.get("p") is not None)
                  else None)
    else:
        p_gate = mbb["p_one"]
    sens = {}
    sb = sens_boot if sens_boot is not None else n_boot
    for L in MBB_L_SENS:
        s = mbb_pvalue(obs_by_pair, _stat, sb, (seed, 1, combo_idx, L), L=L)
        sens[f"L{L}"] = {"p_one": s["p_one"], "B": s["B"]}
    return {"pooled_ic": None if math.isnan(point) else round(point, 5),
            "per_pair": per_pair, "n_obs": n_total,
            "p_mbb": mbb["p_one"], "p_mbb_two_sided": mbb["p_two"],
            "p_mbb_neg": mbb["p_neg"], "mbb_days": mbb["n_days"],
            "im": im, "p_gate1": p_gate,
            "sens_L": sens, "_ps_available": ps}


# ══════════════════════════════════════════════════════════════════════
# ev_legs / gate2 (§4.2) — time-exit / first-touch / stress、day-block bootstrap
# ══════════════════════════════════════════════════════════════════════

def ev_point_stats(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """点推定 (raw pips = M6 の単位): time-exit / first-touch / stress。"""
    n = len(trades)
    if n == 0:
        return {"n": 0, "ev_time_exit": None, "ev_first_touch": None,
                "ev_stress": None, "ev_ftc": None, "wr_time_exit": None}
    net = np.array([t["net_pips"] for t in trades])
    ft = np.array([t["ft_net_pips"] for t in trades])
    stress = np.array([t["stress_net_pips"] for t in trades])
    ftc = np.array([t["ftc_net_pips"] for t in trades])
    return {"n": n,
            "ev_time_exit": round(float(net.mean()), 4),
            "ev_first_touch": round(float(ft.mean()), 4),
            "ev_stress": round(float(stress.mean()), 4),
            "ev_ftc": round(float(ftc.mean()), 4),   # Secondary (§4.6)
            "wr_time_exit": round(float(np.mean(net > 0)), 4)}


def gate2_combo(trades: List[Dict[str, Any]], n_boot: int, seed: int,
                combo_idx: int) -> Dict[str, Any]:
    """Gate 2 (§4.2): trade を entry 営業日でクラスタ化した day-block bootstrap
    (L=5、B、seed 固定)、片側 p。検定統計 = ATR 正規化 net return、
    経済条件 = raw pips。N < 60 は検定せず点推定のみ (§4.2(d))。"""
    pt = ev_point_stats(trades)
    out = dict(pt)
    out["n_lt_60"] = pt["n"] < MIN_TRADES_GATE2
    if pt["n"] == 0 or out["n_lt_60"]:
        out["p_ev"] = None
        return out
    obs = {"_trades": {
        "score": np.array([t["norm_net"] for t in trades]),
        "fwd": np.zeros(len(trades)),
        "day": np.array([date.fromisoformat(t["entry_day"]).toordinal()
                         for t in trades], dtype=int)}}

    def _stat(sub):
        vals = sub.get("_trades", {}).get("score")
        return float(np.mean(vals)) if vals is not None and len(vals) else float("nan")
    mbb = mbb_pvalue(obs, _stat, n_boot, (seed, 2, combo_idx))
    out["p_ev"] = mbb["p_one"]
    out["norm_net_mean"] = mbb["point"]
    out["ev_days"] = mbb["n_days"]
    return out


# ══════════════════════════════════════════════════════════════════════
# partial IC (§4.4 CONFOUNDED) — 直近 24h/120h リターンを rank 回帰で統制
# ══════════════════════════════════════════════════════════════════════

def partial_spearman(score: np.ndarray, fwd: np.ndarray,
                     controls: List[np.ndarray]) -> float:
    """rank 回帰統制の残差 IC: score/fwd/controls を rank 化し、controls への
    OLS 残差同士の Pearson (= partial Spearman)。"""
    if len(score) < 6:
        return float("nan")
    from scipy.stats import rankdata
    X = np.column_stack([np.ones(len(score))]
                        + [rankdata(c) for c in controls])
    ry = rankdata(fwd)
    rs = rankdata(score)
    try:
        beta_s, *_ = np.linalg.lstsq(X, rs, rcond=None)
        beta_y, *_ = np.linalg.lstsq(X, ry, rcond=None)
    except np.linalg.LinAlgError:
        return float("nan")
    # BLAS matvec (X @ beta) は macOS Accelerate で spurious FP warning を
    # 出すことがあるため要素積 + sum で予測値を計算する (数値は同一)
    res_s = rs - (X * beta_s).sum(axis=1)
    res_y = ry - (X * beta_y).sum(axis=1)
    if np.std(res_s) == 0 or np.std(res_y) == 0:
        return float("nan")
    return float(np.corrcoef(res_s, res_y)[0, 1])


def partial_ic_combo(obs_by_pair: Dict[str, Dict[str, np.ndarray]],
                     mid_by_pair: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """§4.4 CONFOUNDED 用 partial IC (事前定義): 直近 24h (72 slots)・
    120h (360 slots) の mid リターンを rank 回帰で統制した残差 IC を
    per-pair → 有効 N 加重 pooling。"""
    num = 0.0
    den = 0
    per_pair: Dict[str, Any] = {}
    for pair, o in obs_by_pair.items():
        mid = mid_by_pair[pair]
        ii = o["slot_i"]
        keep: List[int] = []
        c24: List[float] = []
        c120: List[float] = []
        for j, i in enumerate(ii):
            i = int(i)
            if i < 360:
                continue
            m0, m24, m120 = mid[i], mid[i - 72], mid[i - 360]
            if math.isnan(m0) or math.isnan(m24) or math.isnan(m120):
                continue
            keep.append(j)
            c24.append(m0 - m24)
            c120.append(m0 - m120)
        if len(keep) < 6:
            per_pair[pair] = {"partial_ic": None, "n": len(keep)}
            continue
        k = np.array(keep, dtype=int)
        pic = partial_spearman(o["score"][k], o["fwd"][k],
                               [np.array(c24), np.array(c120)])
        per_pair[pair] = {"partial_ic": None if math.isnan(pic)
                          else round(pic, 5), "n": len(keep)}
        if not math.isnan(pic):
            num += len(keep) * pic
            den += len(keep)
    pooled = num / den if den else float("nan")
    return {"pooled_partial_ic": None if math.isnan(pooled)
            else round(pooled, 5), "per_pair": per_pair, "n": den}


# ══════════════════════════════════════════════════════════════════════
# classify (§4.4 Step 1) — combo 順序付き排他分類 C1〜C5 + 付帯フラグ
# ══════════════════════════════════════════════════════════════════════

def classify_combo(gate1_survive: bool, ic_point: Optional[float],
                   n_trades: int, ev_time_exit: Optional[float],
                   ev_first_touch: Optional[float],
                   ev_stress: Optional[float],
                   gate2_p_ok: bool, knife_pass: Optional[bool],
                   confirmatory_ok: Optional[bool],
                   signflip_significant: bool,
                   partial_ic_point: Optional[float]) -> Tuple[str, List[str]]:
    """§4.4 Step 1: この順で評価し**最初に該当したクラスに一意分類** (排他)。

      C1: Gate1 ∧ Gate2(a)(b)(c) ∧ N≥60 ∧ ナイフエッジ4点 ∧ confirmatory
      C2: IC 宣言符号 ∧ time-exit 点 EV>0 ∧ first-touch 点 EV≤0 (sequencing 反転)
      C3: IC 宣言符号 ∧ time-exit 点 EV>0 ∧ first-touch 点 EV>0 (UNDERPOWERED 適格)
      C4: Gate1 通過 ∧ time-exit 点 EV≤0 (REJECT-F 型)
      C5: それ以外
    N<60 combo は §4.2(d) により検定なし・点推定で C2〜C5 に回る (C1 不可)。
    付帯フラグ: SIGN-FLIP (C5 + 両側有意逆符号)、CONFOUNDED (C1 + partial IC
    符号逆転 → PASS-with-flag、分類自体は変えない)。
    confirmatory_ok=None は「データ不揃い → 実装 pre-reg へ繰延」(C1 を止めない
    が『confirmatory 未検査』を verdict に明記、§2.4 [^4])。
    """
    flags: List[str] = []
    ev_t = ev_time_exit if ev_time_exit is not None else float("nan")
    ev_f = ev_first_touch if ev_first_touch is not None else float("nan")
    ev_s = ev_stress if ev_stress is not None else float("nan")
    ic = ic_point if ic_point is not None else float("nan")
    conf_gate = confirmatory_ok is not False    # None (未検査) は止めない
    if confirmatory_ok is None:
        flags.append("CONFIRMATORY_UNTESTED")
    c1 = (gate1_survive and n_trades >= MIN_TRADES_GATE2 and gate2_p_ok
          and not math.isnan(ev_t) and ev_t > 0
          and not math.isnan(ev_f) and ev_f > 0
          and not math.isnan(ev_s) and ev_s > 0
          and bool(knife_pass) and conf_gate)
    if c1:
        cls = "C1"
        if (partial_ic_point is not None and not math.isnan(ic)
                and partial_ic_point * ic < 0):
            flags.append("CONFOUNDED")          # PASS-with-flag、user 裁定
    elif (not math.isnan(ic) and ic > 0
          and not math.isnan(ev_t) and ev_t > 0
          and not math.isnan(ev_f) and ev_f <= 0):
        cls = "C2"
    elif (not math.isnan(ic) and ic > 0
          and not math.isnan(ev_t) and ev_t > 0
          and not math.isnan(ev_f) and ev_f > 0):
        cls = "C3"
    elif gate1_survive and (math.isnan(ev_t) or ev_t <= 0):
        cls = "C4"
    else:
        cls = "C5"
    if cls == "C5" and signflip_significant:
        flags.append("SIGN-FLIP")               # 追うなら新規 pre-reg (§4.4)
    return cls, flags


def overall_verdict(classes: Dict[str, str],
                    quality_postponed: bool,
                    postponed_before: bool) -> str:
    """§4.4 Step 2: PASS > UNDERPOWERED > REJECT-F > REJECT の優先順位で一意。
    品質 gate 不成立は POSTPONE (1 回限り) / 2 回目は DEFERRED (§2.5-3)。"""
    if quality_postponed:
        return "DEFERRED" if postponed_before else "POSTPONE"
    vals = set(classes.values())
    if "C1" in vals:
        return "PASS"
    if "C3" in vals:
        return "UNDERPOWERED"
    if "C4" in vals:
        return "REJECT-F"
    if vals <= {"C2", "C5"} and vals:
        return "REJECT"
    return "DEFERRED"                           # 排他設計の外 = 設計違反を記録


# ══════════════════════════════════════════════════════════════════════
# canary leak test (§4.5-3 / §2.5-5d) — verdict 実行前の構造的 self-check
# ══════════════════════════════════════════════════════════════════════

def _canary_world() -> Dict[str, Any]:
    """canary 用の決定論的合成ワールド (2026-03 の平週、market open 帯)。"""
    start = _utc("2026-03-02T00:00:00Z")        # Mon
    ep0 = _ep(start)
    n_bars = 4 * 24 * 5                        # 5 日ぶんの M15
    ep = ep0 + 900.0 * np.arange(n_bars)
    rng = np.random.default_rng(7)
    px = 150.0 + np.cumsum(rng.normal(0, 0.03, n_bars))
    o = px.copy()
    c = px + rng.normal(0, 0.01, n_bars)
    h = np.maximum(o, c) + 0.02
    l = np.minimum(o, c) - 0.02
    bars = bars_from_arrays(ep, o, h, l, c)
    return {"bars": bars, "start": start}


def run_canary_suite(locf_impl=None, atr_impl=None, fwd_impl=None) -> Dict[str, Any]:
    """§4.5-3(i): 未来情報を注入した合成データで「エンジンが使わない」ことを
    機械検証する。注入が結果を動かしたら FAIL (リーク検出)。
    注入対象に ATR 経路 (S3 分母・σ_h・Gate 2 正規化) を明示的に含める (§2.3)。
    テストは locf_impl/atr_impl/fwd_impl に故意にリークする実装を渡し、
    本 suite が検出 (fail) することを pin する。"""
    locf = locf_impl or resample_locf
    atrf = atr_impl or atr_at
    fwdf = fwd_impl or forward_returns
    checks: Dict[str, Dict[str, Any]] = {}
    w = _canary_world()
    bars = w["bars"]

    # (1) LOCF 未来 snapshot 注入: t−60s 規約 (§2.2) — t−30s / t+5min の行は
    #     スロット t に影響してはならない
    t_slot = _utc("2026-03-03T12:00:00Z")
    grid = [t_slot]
    base_ep = _ep(t_slot)
    mk = lambda eps_vals: {"ep": np.array([e for e, _ in eps_vals]),
                           "long": np.array([v for _, v in eps_vals]),
                           "short": np.array([100.0 - v for _, v in eps_vals]),
                           "avg_long": np.full(len(eps_vals), 150.0),
                           "avg_short": np.full(len(eps_vals), 150.0)}
    clean_rows = mk([(base_ep - 7200, 60.0)])
    poisoned = mk([(base_ep - 7200, 60.0), (base_ep - 30, 99.0),
                   (base_ep + 300, 99.0)])
    ver = {"X": [base_ep - 7200, base_ep - 30, base_ep + 300]}
    cyc = [base_ep - 600]
    p_clean = locf({"X": clean_rows}, {"X": [base_ep - 7200]}, cyc, grid)
    p_poison = locf({"X": poisoned}, ver, cyc, grid)
    v0 = p_clean["X"]["long"][0]
    v1 = p_poison["X"]["long"][0]
    checks["locf_future_injection"] = {
        "pass": bool(np.isclose(v0, v1) and np.isclose(v0, 60.0)),
        "detail": f"clean={v0} poisoned={v1} (expected 60.0)"}

    # (2) ATR 経路注入 (§2.3 M3): t 時点の ATR は「t より厳密に前に完結した
    #     daily bar」のみ — 進行中の当日レンジ・未来 bar の注入は無効のはず
    t_atr = _utc("2026-03-05T12:00:00Z")        # Thu 昼 (当日 = 進行中)
    daily_c = build_daily_bars(bars)
    atr_c = atr_series(daily_c, n_atr=2)        # 合成 5 日ワールドでは短縮 ATR
    bars_poison = {k: (v.copy() if isinstance(v, np.ndarray) else v)
                   for k, v in bars.items()}
    future_sel = bars_poison["ep"] > _ep(t_atr) - 900
    bars_poison["high"][future_sel] += 50.0     # 未来/進行中バーへ巨大レンジ注入
    bars_poison["low"][future_sel] -= 50.0
    daily_p = build_daily_bars(bars_poison)
    atr_p = atr_series(daily_p, n_atr=2)
    a0 = atrf(daily_c, atr_c, _ep(t_atr))
    a1 = atrf(daily_p, atr_p, _ep(t_atr))
    checks["atr_future_injection"] = {
        "pass": bool(not math.isnan(a0) and np.isclose(a0, a1)),
        "detail": f"clean={a0} poisoned={a1}"}

    # (3) join/前方リターン: 前方リターンへの「過去バー注入」が効かない +
    #     entry bar が grid t より厳密に後 (契約 assert が生きている)
    slot_ep = np.array([_ep(_utc("2026-03-03T10:00:00Z"))])
    f0 = fwdf(bars, slot_ep, 16)[0]
    bars_p2 = {k: (v.copy() if isinstance(v, np.ndarray) else v)
               for k, v in bars.items()}
    past_sel = bars_p2["ep"] <= slot_ep[0]
    bars_p2["open"][past_sel] += 99.0   # t 以前 (t ちょうど含む) の open は fwd に無関係
    f1 = fwdf(bars_p2, slot_ep, 16)[0]
    checks["fwd_return_window"] = {
        "pass": bool(np.isclose(f0, f1)),
        "detail": f"clean={f0} past-poisoned={f1}"}

    # (4) シグナル注入 canary: 未来リターンをそのまま値に持つ snapshot を
    #     「未来時刻で」注入 — スロット t のシグナルが不変であること。
    #     全スロットを stale cap (2h) 内に収め、注入行は全スロットの未来に置く
    #     (margin 破りのリーク実装が確実に注入行へ届く配置)
    grid2 = build_grid(_utc("2026-03-03T08:00:00Z"), _utc("2026-03-03T09:00:00Z"))
    eps2 = [(_ep(grid2[0]) - 3600, 55.0)]
    rows_c = mk(eps2)
    fut_ep = _ep(grid2[-1]) + 120               # 最終スロットの未来
    rows_p = mk(eps2 + [(fut_ep, 95.0)])
    ver2 = {"X": [eps2[0][0], fut_ep]}
    cyc2 = [_ep(g) for g in grid2]
    pc = locf({"X": rows_c}, {"X": [eps2[0][0]]}, cyc2, grid2)
    pp = locf({"X": rows_p}, ver2, cyc2, grid2)
    same = bool(np.allclose(np.nan_to_num(pc["X"]["skew"]),
                            np.nan_to_num(pp["X"]["skew"])))
    checks["signal_future_value_injection"] = {
        "pass": same,
        "detail": "future-timestamped snapshot must not move any slot value"}

    all_pass = all(c["pass"] for c in checks.values())
    return {"pass": all_pass, "checks": checks}


# ══════════════════════════════════════════════════════════════════════
# knife_edge (§4.5) — PASS 必須 4 点 (C1 候補 combo のみ実行)
# ══════════════════════════════════════════════════════════════════════

def _fold_split(days: List[int], k: int = 3) -> List[set]:
    """評価窓営業日を時系列 k 等分 (§4.5-1)。"""
    if not days:
        return []
    chunks = np.array_split(np.array(sorted(days)), k)
    return [set(int(d) for d in c) for c in chunks if len(c)]


def knife_edge_combo(ctx: Dict[str, Any], stat: str, hname: str) -> Dict[str, Any]:
    """§4.5 ナイフエッジ 4 点。#1〜#3 が PASS gate、#4 は限定 PASS 降格フラグ。"""
    combo = f"{stat}x{hname}"
    obs = ctx["ic_obs"][combo]
    trades = ctx["trades"][combo]
    pairs = ctx["pairs"]
    out: Dict[str, Any] = {}

    # ── #1 fold 集中: 最良 fold 除外の残り 2 fold pooled IC / net EV 符号維持 ──
    days = sorted(set(int(d) for o in obs.values() for d in o["day"]))
    folds = _fold_split(days, 3)
    fold_ic: List[float] = []
    fold_ev: List[Optional[float]] = []
    for fs in folds:
        sub = {}
        for pair, o in obs.items():
            sel = np.array([j for j in range(len(o["day"]))
                            if int(o["day"][j]) in fs], dtype=int)
            if len(sel):
                sub[pair] = {"score": o["score"][sel], "fwd": o["fwd"][sel],
                             "day": o["day"][sel]}
        ic, _, _ = pooled_ic(sub) if sub else (float("nan"), {}, 0)
        fold_ic.append(ic)
        tv = [t["net_pips"] for t in trades
              if date.fromisoformat(t["entry_day"]).toordinal() in fs]
        fold_ev.append(float(np.mean(tv)) if tv else None)
    fold_ok = False
    if len(folds) == 3:
        # IC は最良 IC fold を、EV は最良 EV fold をそれぞれ除外 (各指標が
        # 自分の最良 fold を落とす保守側)
        ic_arr = np.array(fold_ic)
        if not np.any(np.isnan(ic_arr)):
            rest_ic = [f for k, f in enumerate(folds)
                       if k != int(np.argmax(ic_arr))]
            merged_ic = set().union(*rest_ic)
            sub = {}
            for pair, o in obs.items():
                sel = np.array([j for j in range(len(o["day"]))
                                if int(o["day"][j]) in merged_ic], dtype=int)
                if len(sel):
                    sub[pair] = {"score": o["score"][sel], "fwd": o["fwd"][sel],
                                 "day": o["day"][sel]}
            rest_pooled_ic, _, _ = pooled_ic(sub) if sub else (float("nan"), {}, 0)
            ev_vals = [v if v is not None else -math.inf for v in fold_ev]
            rest_ev_folds = [f for k, f in enumerate(folds)
                             if k != int(np.argmax(ev_vals))]
            merged_ev = set().union(*rest_ev_folds)
            tv = [t["net_pips"] for t in trades
                  if date.fromisoformat(t["entry_day"]).toordinal() in merged_ev]
            rest_ev = float(np.mean(tv)) if tv else float("nan")
            fold_ok = (not math.isnan(rest_pooled_ic) and rest_pooled_ic > 0
                       and not math.isnan(rest_ev) and rest_ev > 0)
            out["fold"] = {"fold_ic": [None if math.isnan(v) else round(v, 5)
                                       for v in fold_ic],
                           "fold_ev": [None if v is None else round(v, 4)
                                       for v in fold_ev],
                           "rest_ic": None if math.isnan(rest_pooled_ic)
                           else round(rest_pooled_ic, 5),
                           "rest_ev": None if math.isnan(rest_ev)
                           else round(rest_ev, 4), "pass": fold_ok}
    if "fold" not in out:
        out["fold"] = {"fold_ic": [], "fold_ev": [], "pass": False,
                       "note": "fold 構成不能 (営業日不足)"}

    # ── #2 孤立格子点 ──
    # (i) entry 閾値近傍 {0.85, 0.95} の event net EV 符号一致 ≥ 1/2
    thr_evs: Dict[str, Optional[float]] = {}
    for q in KNIFE_THRESHOLDS:
        nets: List[float] = []
        for pair in pairs:
            evs = crossing_events(
                ctx["ranks"][stat][pair], ctx["slots"],
                entry_hi=q, entry_lo=round(1 - q, 4),
                rearm_hi=round(q - 0.10, 4), rearm_lo=round(1 - q + 0.10, 4),
                jump_mask=ctx["jump_mask"], year_end=ctx["year_end"])
            tr = build_trades(evs, ctx["bars"][pair], ctx["slots"],
                              ctx["slot_ep"], ctx["daily"][pair],
                              ctx["atr"][pair], pair, stat, hname,
                              ctx["cutoff"], ctx["burnin"][pair],
                              jump_mask=ctx["jump_mask"])
            nets.extend(t["net_pips"] for t in tr)
        thr_evs[str(q)] = float(np.mean(nets)) if nets else None
    n_pos_thr = sum(1 for v in thr_evs.values() if v is not None and v > 0)
    # (ii) 隣接 combo (同統計×他 h、同 h×他統計) の点 EV > 0 が ≥1 (grid 最小)
    adjacent = ([f"{stat}x{hn}" for hn, _ in H_GRID if hn != hname]
                + [f"{s}x{hname}" for s in STATS if s != stat])
    adj_pos = 0
    adj_detail = {}
    for a in adjacent:
        ev = ctx["gate2"].get(a, {}).get("ev_time_exit")
        adj_detail[a] = ev
        if ev is not None and ev > 0:
            adj_pos += 1
    # (iii) W=10 / expanding 感度で IC 符号が反転しない
    sens_ic: Dict[str, Optional[float]] = {}
    for name, kw in (("W10", {"w_slots": W10_SLOTS}),
                     ("expanding", {"expanding": True})):
        sub = {}
        h_bars = H_BARS[hname]
        for pair in pairs:
            rr = trailing_rank(ctx["raw_stats"][pair][stat], **kw)
            o = ic_observations(rr, ctx["fwd"][pair][hname], ctx["slots"],
                                ctx["burnin"][pair], ctx["cutoff"], h_bars,
                                jump_mask=ctx["jump_mask"],
                                censor_ok=ctx["censor_ok"][hname])
            if len(o["score"]):
                sub[pair] = o
        ic, _, _ = pooled_ic(sub) if sub else (float("nan"), {}, 0)
        sens_ic[name] = None if math.isnan(ic) else round(ic, 5)
    grid_ok = (n_pos_thr >= 1 and adj_pos >= 1
               and all(v is not None and v > 0 for v in sens_ic.values()))
    out["grid"] = {"threshold_evs": {k: None if v is None else round(v, 4)
                                     for k, v in thr_evs.items()},
                   "threshold_pos": f"{n_pos_thr}/2",
                   "adjacent_ev": adj_detail, "adjacent_pos": adj_pos,
                   "sens_ic": sens_ic, "pass": grid_ok}

    # ── #3 閾値リーク / 遅延頑健性 ──
    canary = ctx["canary"]
    delay_nets: List[float] = []
    for pair in pairs:
        evs = crossing_events(ctx["ranks"][stat][pair], ctx["slots"],
                              jump_mask=ctx["jump_mask"],
                              year_end=ctx["year_end"], delay_slots=1)
        tr = build_trades(evs, ctx["bars"][pair], ctx["slots"], ctx["slot_ep"],
                          ctx["daily"][pair], ctx["atr"][pair], pair, stat,
                          hname, ctx["cutoff"], ctx["burnin"][pair],
                          jump_mask=ctx["jump_mask"])
        delay_nets.extend(t["net_pips"] for t in tr)
    delay_ev = float(np.mean(delay_nets)) if delay_nets else None
    leak_ok = bool(canary["pass"] and delay_ev is not None and delay_ev > 0)
    out["leak"] = {"canary_pass": canary["pass"],
                   "delay1_ev": None if delay_ev is None else round(delay_ev, 4),
                   "delay1_n": len(delay_nets), "pass": leak_ok}

    # ── #4 クロスペア集中 (記録 + 限定 PASS 降格フラグ、PASS gate ではない) ──
    net_all = [(t["pair"], t["net_pips"]) for t in trades]
    ev_no_jpy = [v for p, v in net_all if p not in JPY_BLOCK]
    ev_jpy = [v for p, v in net_all if p in JPY_BLOCK]
    lj = float(np.mean(ev_no_jpy)) if ev_no_jpy else None
    ln = float(np.mean(ev_jpy)) if ev_jpy else None
    limited = None
    if lj is not None and ln is not None:
        if lj <= 0 and ln > 0:
            limited = "JPY_BLOCK_ONLY"
        elif ln <= 0 and lj > 0:
            limited = "NON_JPY_ONLY"
    out["cross_pair"] = {"leave_jpy_out_ev": None if lj is None else round(lj, 4),
                         "leave_non_jpy_out_ev": None if ln is None else round(ln, 4),
                         "limited_pass": limited}

    out["pass"] = bool(out["fold"]["pass"] and grid_ok and leak_ok)
    return out


# ══════════════════════════════════════════════════════════════════════
# quality_gates (§2.5) — 統計計算より先に機械判定
# ══════════════════════════════════════════════════════════════════════

def quality_gates(panel: Dict[str, Any], pairs: Sequence[str],
                  burnin: Dict[str, datetime], cutoff: datetime,
                  sanity_stats: Dict[str, Any],
                  censor_ok_by_h: Optional[Dict[str, np.ndarray]] = None) -> Dict[str, Any]:
    """§2.5-1〜3 + 7: coverage / stale gap / family gate / 量子化粒度。
    coverage の分母は censoring (cutoff − h) 適用後 (§2.3) — h 毎に併記し、
    gate は両 h の min で判定 (保守側)。"""
    slots = panel["slots"]
    slot_ep = panel["slot_ep"]
    if censor_ok_by_h is None:
        censor_ok_by_h = {hname: censor_mask(slots, cutoff, hb)
                          for hname, hb in H_GRID}
    out: Dict[str, Any] = {"pairs": {}, "excluded_pairs": [],
                           "sanity": sanity_stats}
    surviving: List[str] = []
    for pair in pairs:
        valid = panel[pair]["valid"] & panel["cycle_ok"]
        info: Dict[str, Any] = {}
        cov_by_h = {}
        for hname, h_bars in H_GRID:
            cok = censor_ok_by_h[hname]
            denom = num = 0
            for i, t in enumerate(slots):
                if t < burnin[pair]:
                    continue
                if not cok[i]:
                    continue
                denom += 1
                if valid[i]:
                    num += 1
            cov_by_h[hname] = (num / denom) if denom else 0.0
        info["coverage"] = {k: round(v, 4) for k, v in cov_by_h.items()}
        cov_min = min(cov_by_h.values()) if cov_by_h else 0.0
        cov_ok = cov_min >= COVERAGE_MIN

        # stale gap (§2.5-2): 連続欠測 > 24h (市場時間) の区間検出
        gap_days = 0.0
        eval_days = 0.0
        gap_start: Optional[datetime] = None
        prev_t: Optional[datetime] = None
        first_eval: Optional[datetime] = None
        for i, t in enumerate(slots):
            if t < burnin[pair] or t > cutoff:
                continue
            if first_eval is None:
                first_eval = t
            if valid[i]:
                if gap_start is not None and prev_t is not None:
                    g = market_seconds_between(gap_start, t)
                    if g > STALE_GAP_SEC:
                        gap_days += g / (24 * 3600.0)
                    gap_start = None
            else:
                if gap_start is None:
                    gap_start = t
            prev_t = t
        if gap_start is not None:
            g = market_seconds_between(gap_start, cutoff)
            if g > STALE_GAP_SEC:
                gap_days += g / (24 * 3600.0)
        if first_eval is not None:
            eval_days = market_seconds_between(first_eval, cutoff) / (24 * 3600.0)
        gap_frac = (gap_days / eval_days) if eval_days > 0 else 0.0
        gap_ok = gap_frac <= STALE_GAP_FRAC
        info["stale_gap"] = {"excluded_days": round(gap_days, 2),
                             "eval_days": round(eval_days, 2),
                             "frac": round(gap_frac, 4)}

        # 量子化粒度 (§2.5-7 / §3.1): 窓 W 内の skew distinct 値数 (最終スロット)
        skew = np.where(panel[pair]["valid"], panel[pair]["skew"], np.nan)
        tail = skew[-W_SLOTS:]
        finite = tail[~np.isnan(tail)]
        info["skew_distinct_in_W"] = int(len(np.unique(finite)))

        info["pass"] = bool(cov_ok and gap_ok)
        if not info["pass"]:
            info["fail_reason"] = ("coverage<90%" if not cov_ok
                                   else "stale_gap>20%")
            out["excluded_pairs"].append(pair)   # 機械除外 (裁量なし、fail-loud)
        else:
            surviving.append(pair)
        out["pairs"][pair] = info
    out["surviving_pairs"] = surviving
    out["family_gate_pass"] = len(surviving) >= FAMILY_MIN_PAIRS
    out["postpone"] = not out["family_gate_pass"]
    _ = slot_ep  # (未使用警告避け: 分母は slots 走査で計算)
    return out


# ══════════════════════════════════════════════════════════════════════
# 補助レポート (§4.3 Stage B / §4.6 Secondary / §2.4 confirmatory)
# ══════════════════════════════════════════════════════════════════════

def stage_b_localization(ctx: Dict[str, Any], combo: str, n_boot: int,
                         seed: int, combo_idx: int) -> Dict[str, Any]:
    """§4.3 Stage B (記述のみ、verdict に不使用): per-pair IC を同一 bootstrap
    で評価し BH-FDR q=0.10 (m=6 ペア)。"""
    obs = ctx["ic_obs"][combo]
    pvals: Dict[str, Optional[float]] = {}
    detail: Dict[str, Any] = {}
    for pair, o in obs.items():
        def _stat(sub, _p=pair):
            oo = sub.get(_p)
            return spearman(oo["score"], oo["fwd"]) if oo is not None else float("nan")
        # seed key はペアの固定 index (hash() は PYTHONHASHSEED 依存で非決定)
        pair_idx = list(ctx["pairs"]).index(pair)
        r = mbb_pvalue({pair: o}, lambda sub: _stat(sub), n_boot,
                       (seed, 3, combo_idx, pair_idx))
        pvals[pair] = r["p_one"]
        detail[pair] = {"ic": r["point"], "p": r["p_one"], "n": len(o["score"])}
    fdr = bh_fdr(pvals, STAGEB_FDR_Q, m=len(ctx["pairs"]))
    for pair in detail:
        detail[pair]["fdr_survive"] = fdr.get(pair, {}).get("survive", False)
    return {"per_pair": detail, "note": "記述のみ (§4.3) — PASS/REJECT に不使用"}


def secondary_descriptives(ctx: Dict[str, Any], combo: str) -> Dict[str, Any]:
    """§4.6 Secondary (記述のみ、判定・確認的引用禁止) の機械計算分。"""
    trades = ctx["trades"][combo]
    out: Dict[str, Any] = {}
    for flag in ("weekend_span", "jump_overlap"):
        yes = [t["net_pips"] for t in trades if t[flag]]
        no = [t["net_pips"] for t in trades if not t[flag]]
        out[flag] = {"n_true": len(yes),
                     "ev_true": round(float(np.mean(yes)), 4) if yes else None,
                     "n_false": len(no),
                     "ev_false": round(float(np.mean(no)), 4) if no else None}
    # セッション別 IC 記述 (UTC 帯の粗い区分 — 判定に入れない)
    obs = ctx["ic_obs"][combo]
    sessions = {"asia": (22, 7), "ldn": (7, 13), "ny": (13, 22)}
    sess_out = {}
    for name, (h0, h1) in sessions.items():
        sub = {}
        for pair, o in obs.items():
            hrs = np.array([ctx["slots"][int(i)].hour for i in o["slot_i"]])
            sel = (np.where((hrs >= h0) | (hrs < h1))[0] if h0 > h1
                   else np.where((hrs >= h0) & (hrs < h1))[0])
            if len(sel):
                sub[pair] = {"score": o["score"][sel], "fwd": o["fwd"][sel],
                             "day": o["day"][sel]}
        ic, _, n = pooled_ic(sub) if sub else (float("nan"), {}, 0)
        sess_out[name] = {"ic": None if math.isnan(ic) else round(ic, 5), "n": n}
    out["session_ic"] = sess_out
    return out


def confirmatory_check(ctx_conf: Optional[Dict[str, Any]], combo: str,
                       n_boot: int, seed: int, combo_idx: int) -> Dict[str, Any]:
    """§2.4 out-of-family 複製検査 (PASS 候補 combo のみ判定に使用)。

    - 揃う条件: post-burn-in 評価期間 ≥6 週 ∧ pooled trade N ≥ 30
      → 点 net EV ≥ 0 が PASS 必須条件
    - per-pair IC 符号一致数/7 を併記
    - pooled IC が宣言と逆符号で両側 α=0.05 有意 → PASS 保留 (user 裁定)
    - 揃わない → ok=None (実装 pre-reg へ繰延、「confirmatory 未検査」明記)
    """
    if ctx_conf is None:
        return {"ok": None, "note": "confirmatory データなし — 未検査 (§2.4)"}
    obs = ctx_conf["ic_obs"][combo]
    trades = ctx_conf["trades"][combo]
    pt = ev_point_stats(trades)
    ic, per_pair, _ = pooled_ic(obs)
    sign_agree = sum(1 for v in per_pair.values()
                     if v["ic"] is not None and v["ic"] > 0)
    span_wk = ctx_conf["eval_span_weeks"]
    eligible = span_wk >= CONF_MIN_WEEKS and pt["n"] >= CONF_MIN_TRADES
    result: Dict[str, Any] = {
        "eligible": eligible, "eval_span_weeks": round(span_wk, 2),
        "pooled_trades": pt["n"], "point_net_ev": pt["ev_time_exit"],
        "pooled_ic": None if math.isnan(ic) else round(ic, 5),
        "ic_sign_agree": f"{sign_agree}/{len(per_pair)}",
        "per_pair_ic": per_pair}
    if not eligible:
        result["ok"] = None
        result["note"] = ("confirmatory 未検査 (≥6 週 ∧ N≥30 不成立) — "
                          "実装 pre-reg へ繰延 (§2.4 [^4])")
        return result
    # 有意逆転検査 (両側 α=0.05)
    def _stat(sub):
        v, _, _ = pooled_ic(sub)
        return v
    mbb = mbb_pvalue(obs, _stat, n_boot, (seed, 4, combo_idx))
    reversed_sig = (mbb["point"] is not None and mbb["point"] < 0
                    and mbb["p_two"] is not None and mbb["p_two"] < 0.05)
    result["reversal_two_sided_p"] = mbb["p_two"]
    if reversed_sig:
        result["ok"] = False
        result["note"] = "IC 符号の有意逆転 → PASS 保留 + user 裁定 (§2.4)"
        result["user_review_required"] = True
        return result
    result["ok"] = bool(pt["ev_time_exit"] is not None
                        and pt["ev_time_exit"] >= 0)
    if not result["ok"]:
        result["note"] = "confirmatory 点 net EV < 0 → PASS 必須条件不成立 (§2.4)"
    return result


# ══════════════════════════════════════════════════════════════════════
# orchestration — resample → signals → events → ic → ev → gates → verdict
# ══════════════════════════════════════════════════════════════════════

def build_context(pairs: Sequence[str], panel: Dict[str, Any],
                  bars_by_pair: Dict[str, Dict[str, np.ndarray]],
                  burnin: Dict[str, datetime], cutoff: datetime,
                  jump_mask: np.ndarray,
                  year_end: Optional[Tuple[datetime, datetime]],
                  canary: Dict[str, Any]) -> Dict[str, Any]:
    """family 単位の評価コンテキスト (signals → events → trades → ic_obs)。"""
    slots = panel["slots"]
    slot_ep = panel["slot_ep"]
    ctx: Dict[str, Any] = {
        "pairs": list(pairs), "slots": slots, "slot_ep": slot_ep,
        "bars": bars_by_pair, "burnin": burnin, "cutoff": cutoff,
        "jump_mask": jump_mask, "year_end": year_end, "canary": canary,
        "daily": {}, "atr": {}, "mid": {}, "raw_stats": {}, "ranks":
        {s: {} for s in STATS}, "fwd": {}, "events": {s: {} for s in STATS},
        "trades": {}, "ic_obs": {}, "censor_ok": {}}
    for hname, hb in H_GRID:
        ctx["censor_ok"][hname] = censor_mask(slots, cutoff, hb)
    for pair in pairs:
        bars = bars_by_pair[pair]
        daily = build_daily_bars(bars)
        atr = atr_series(daily)
        ctx["daily"][pair] = daily
        ctx["atr"][pair] = atr
        mid = mid_at_slots(bars, slot_ep)
        ctx["mid"][pair] = mid
        atr_slot = np.array([atr_at(daily, atr, e) for e in slot_ep])
        raw = compute_stat_series(panel, pair, mid, atr_slot)
        ctx["raw_stats"][pair] = raw
        ctx["fwd"][pair] = {hname: forward_returns(bars, slot_ep, hb)
                            for hname, hb in H_GRID}
        for s in STATS:
            ranks = trailing_rank(raw[s])
            ctx["ranks"][s][pair] = ranks
            ctx["events"][s][pair] = crossing_events(
                ranks, slots, jump_mask=jump_mask, year_end=year_end)
    for s, hname in COMBOS:
        combo = f"{s}x{hname}"
        hb = H_BARS[hname]
        trades: List[Dict[str, Any]] = []
        obs: Dict[str, Dict[str, np.ndarray]] = {}
        for pair in pairs:
            trades.extend(build_trades(
                ctx["events"][s][pair], bars_by_pair[pair], slots, slot_ep,
                ctx["daily"][pair], ctx["atr"][pair], pair, s, hname,
                cutoff, burnin[pair], jump_mask=jump_mask))
            o = ic_observations(ctx["ranks"][s][pair], ctx["fwd"][pair][hname],
                                slots, burnin[pair], cutoff, hb,
                                jump_mask=jump_mask,
                                censor_ok=ctx["censor_ok"][hname])
            if len(o["score"]):
                obs[pair] = o
        trades.sort(key=lambda t: t["entry_time"])
        ctx["trades"][combo] = trades
        ctx["ic_obs"][combo] = obs
    return ctx


def run_eval(artifact: Dict[str, Any],
             bars_by_pair: Dict[str, Dict[str, np.ndarray]],
             cutoff: datetime, look: int = 1,
             seed: int = SEED_DEFAULT, n_boot: int = N_BOOT_DEFAULT,
             sens_boot: Optional[int] = None,
             postponed_before: bool = False,
             look2_combos: Optional[List[str]] = None,
             t0_overrides: Optional[Dict[str, str]] = None,
             input_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """判定本体 (§4 全段)。artifact/bars は呼び出し側でロード済み (I/O 分離)。

    look=1: p = max(p_MBB, p_IM)、BH m=6。
    look=2: bootstrap 単独、対象 = look2_combos (first look C3 のみ、BH m=|C3|)、
            年末窓 (§7) の新規 event 除外。
    """
    # ── 引数契約: second look は first look C3 combo の明示指定必須 (§4.4) ──
    if look == 2 and not look2_combos:
        raise RuntimeError("look=2 は first look C3 combo の明示指定必須 "
                           "(§4.4 — 敗者復活の封鎖)")

    # ── 0. canary suite (§2.5-5d): green でなければ verdict データに触れない ──
    canary = run_canary_suite()
    if not canary["pass"]:
        raise RuntimeError(f"canary leak test FAILED — verdict 中止: {canary}")

    instruments = [p for p in list(PRIMARY) + list(CONFIRMATORY)
                   if p in bars_by_pair]
    t0_map: Dict[str, datetime] = {}
    for p in instruments:
        default_t0 = T0_PRIMARY if p in PRIMARY else T0_CONFIRMATORY
        t0_map[p] = _utc((t0_overrides or {}).get(p, default_t0))
    burnin = {p: add_business_days(t0_map[p], BURNIN_BDAYS)
              for p in instruments}

    # ── 1. sanity → resample (LOCF が唯一の入口、§6-1) ──
    rows_by_inst, sanity_stats = sanity_filter(
        artifact.get("snapshots", []), bars_by_pair, instruments)
    verified, cycles = extract_health_events(
        artifact.get("health", []), instruments)
    grid_start = min(t0_map.values())
    grid = build_grid(grid_start, cutoff)
    if not grid:
        raise RuntimeError("empty grid — t0/cutoff を確認")
    panel = resample_locf(rows_by_inst, verified, cycles, grid)

    # ── 2. jump detector (§2.5-7、primary 基準・全ペア適用) ──
    primary_present = [p for p in PRIMARY if p in instruments]
    jump_mask, jump_idx = jump_exclusion_mask(panel, primary_present)

    # ── 3. 品質 gate (§2.5、統計計算より先) ──
    censor_by_h = {hname: censor_mask(grid, cutoff, hb) for hname, hb in H_GRID}
    quality = quality_gates(panel, primary_present, burnin, cutoff,
                            sanity_stats, censor_ok_by_h=censor_by_h)
    quality["jump_events"] = [_iso(grid[i]) for i in jump_idx]
    quality["resample_na_stats"] = panel["stats"]
    result: Dict[str, Any] = {
        "prereg": ("knowledge-base/wiki/decisions/"
                   "e1-positioning-contrarian-prereg-2026-07-16.md (LOCKED)"),
        "harness": "tools/e1_positioning_prereg_eval.py (§7 成果物)",
        "generated_utc": _iso(datetime.now(timezone.utc)),
        "look": look, "cutoff": _iso(cutoff), "seed": seed, "n_boot": n_boot,
        "inputs": input_meta or {}, "synthetic": bool(artifact.get("synthetic")),
        "canary": canary, "quality_gates": quality,
    }
    if quality["postpone"]:
        # §2.5-3: 機械延期 — look を消費しない = 統計段を一切実行しない
        result["verdict"] = {
            "overall": overall_verdict({}, True, postponed_before),
            "reason": (f"family gate 不成立 (残存 "
                       f"{len(quality['surviving_pairs'])} < {FAMILY_MIN_PAIRS})"),
            "action": ("cutoff・verdict 期日・評価窓終端を 4 週スライド "
                       "(burn-in と評価窓開始は不変、§2.5-3/§7)"
                       if not postponed_before else
                       "postpone 2 回目 → DEFERRED (user 裁定、§2.5-3)")}
        return result

    surviving = quality["surviving_pairs"]
    year_end = ((_utc(YEAR_END_EXCL[0]), _utc(YEAR_END_EXCL[1]))
                if look == 2 else None)

    # ── 4. primary family コンテキスト (signals → events → trades → obs) ──
    ctx = build_context(surviving, panel, bars_by_pair, burnin, cutoff,
                        jump_mask, year_end, canary)

    # ── 5. Gate 1 (§4.1) ──
    target_combos = [f"{s}x{h}" for s, h in COMBOS]
    if look == 2:
        target_combos = [c for c in target_combos if c in set(look2_combos)]
    gate1: Dict[str, Any] = {}
    for k, (s, hname) in enumerate(COMBOS):
        combo = f"{s}x{hname}"
        if combo not in target_combos:
            continue
        gate1[combo] = gate1_combo(ctx["ic_obs"][combo], n_boot, seed, k,
                                   look, sens_boot=sens_boot)
    m_gate1 = 6 if look == 1 else len(target_combos)
    fdr1 = bh_fdr({c: gate1[c]["p_gate1"] for c in gate1}, GATE1_FDR_Q,
                  m=m_gate1)

    # ── 6. Gate 2 (§4.2): 点推定は全 combo、検定は Gate1 通過 ∧ N≥60 のみ ──
    gate2: Dict[str, Any] = {}
    g1_passers = [c for c in gate1 if fdr1[c]["survive"]]
    for k, (s, hname) in enumerate(COMBOS):
        combo = f"{s}x{hname}"
        if combo not in target_combos:
            continue
        trades = ctx["trades"][combo]
        if combo in g1_passers:
            gate2[combo] = gate2_combo(trades, n_boot, seed, k)
        else:
            gate2[combo] = ev_point_stats(trades)
            gate2[combo]["p_ev"] = None
            gate2[combo]["n_lt_60"] = gate2[combo]["n"] < MIN_TRADES_GATE2
    ctx["gate2"] = gate2
    fdr2 = bh_fdr({c: gate2[c].get("p_ev") for c in g1_passers},
                  GATE2_FDR_Q, m=max(1, len(g1_passers)))

    # ── 7. partial IC (§4.4 CONFOUNDED、Secondary 併記) ──
    partial: Dict[str, Any] = {}
    for combo in target_combos:
        partial[combo] = partial_ic_combo(ctx["ic_obs"][combo], ctx["mid"])

    # ── 8. C1 候補のみ knife_edge (§4.5) + confirmatory (§2.4) ──
    conf_present = [p for p in CONFIRMATORY if p in instruments]
    ctx_conf: Optional[Dict[str, Any]] = None
    if conf_present:
        ctx_conf = build_context(conf_present, panel, bars_by_pair, burnin,
                                 cutoff, jump_mask, year_end, canary)
        conf_burnin = max(burnin[p] for p in conf_present)
        ctx_conf["eval_span_weeks"] = ((cutoff - conf_burnin).days / 7.0)
    knife: Dict[str, Any] = {}
    confirmatory: Dict[str, Any] = {}
    combos_out: Dict[str, Any] = {}
    classes: Dict[str, str] = {}
    for k, (s, hname) in enumerate(COMBOS):
        combo = f"{s}x{hname}"
        if combo not in target_combos:
            continue
        g1 = gate1[combo]
        g2 = gate2[combo]
        g1_ok = bool(fdr1[combo]["survive"])
        g2_p_ok = bool(combo in fdr2 and fdr2[combo]["survive"]
                       and g2.get("p_ev") is not None
                       and g2["p_ev"] <= GATE2_P)
        c1_candidate = (g1_ok and g2_p_ok and g2["n"] >= MIN_TRADES_GATE2
                        and (g2["ev_time_exit"] or 0) > 0
                        and (g2["ev_first_touch"] or 0) > 0
                        and (g2["ev_stress"] or 0) > 0)
        if c1_candidate:
            knife[combo] = knife_edge_combo(ctx, s, hname)
            confirmatory[combo] = confirmatory_check(ctx_conf, combo, n_boot,
                                                     seed, k)
        signflip_sig = bool(
            g1["pooled_ic"] is not None and g1["pooled_ic"] < 0
            and g1["p_mbb_two_sided"] is not None
            and g1["p_mbb_two_sided"] < 0.05)
        conf_ok = confirmatory.get(combo, {}).get("ok") if c1_candidate else None
        cls, flags = classify_combo(
            gate1_survive=g1_ok, ic_point=g1["pooled_ic"],
            n_trades=g2["n"], ev_time_exit=g2["ev_time_exit"],
            ev_first_touch=g2["ev_first_touch"], ev_stress=g2["ev_stress"],
            gate2_p_ok=g2_p_ok,
            knife_pass=knife.get(combo, {}).get("pass") if c1_candidate else None,
            confirmatory_ok=conf_ok, signflip_significant=signflip_sig,
            partial_ic_point=partial[combo]["pooled_partial_ic"])
        if c1_candidate and knife.get(combo, {}).get("cross_pair", {}).get("limited_pass"):
            flags.append(
                f"LIMITED_PASS:{knife[combo]['cross_pair']['limited_pass']}")
        if (confirmatory.get(combo, {}) or {}).get("user_review_required"):
            flags.append("CONFIRMATORY_REVERSAL_USER_REVIEW")
        classes[combo] = cls
        combos_out[combo] = {
            "class": cls, "flags": flags, "gate1": g1,
            "gate1_fdr": fdr1[combo], "gate2": g2,
            "gate2_fdr": fdr2.get(combo), "partial_ic": partial[combo],
            "knife_edge": knife.get(combo), "confirmatory": confirmatory.get(combo),
            "secondary": secondary_descriptives(ctx, combo),
        }
        if cls == "C1":
            combos_out[combo]["stage_b"] = stage_b_localization(
                ctx, combo, n_boot, seed, k)

    # ── 9. Step 2 全体 verdict (§4.4) ──
    verdict = overall_verdict(classes, False, postponed_before)
    result["combos"] = combos_out
    result["bh_fdr_gate1"] = fdr1
    result["bh_fdr_gate2"] = fdr2
    result["verdict"] = {
        "overall": verdict, "classes": classes,
        "priority": "PASS > UNDERPOWERED > REJECT-F > REJECT (§4.4 Step 2)",
        "notes": _verdict_notes(verdict, classes, look),
    }
    result["trade_list"] = {c: ctx["trades"][c] for c in target_combos}
    result["surviving_pairs"] = surviving
    return result


def _verdict_notes(verdict: str, classes: Dict[str, str], look: int) -> List[str]:
    notes: List[str] = []
    c3 = [c for c, v in classes.items() if v == "C3"]
    c4 = [c for c, v in classes.items() if v == "C4"]
    if verdict == "PASS":
        notes.append("実装 pre-reg (D4 準拠、shadow 起点) を別途起案し user 最終承認へ")
        if c3:
            notes.append(f"併存 C3 {c3} の second look は行わない (α 節約、§4.4)")
    elif verdict == "UNDERPOWERED" and look == 1:
        notes.append(f"second look (2027-01-06) へ — 対象 = C3 combo のみ {c3}、"
                     "BH m=|C3|、累積標本、年末窓除外 (§4.4/§7)")
        if c4:
            notes.append(f"併存 C4 {c4} の REJECT-F 処置 (decision memo) は "
                         "second look verdict まで保留 (§4.4)")
    elif verdict == "REJECT-F":
        notes.append("aggregate 版クローズ + 有償 bucket 級 (KB §8c オプション C) "
                     "decision memo 起案 (契約判断は user)")
    elif verdict == "REJECT":
        notes.append("E1 aggregate 版クローズ — KB §8c 残オプションの再決裁へ")
    if look == 2:
        notes.append("second look の着地は PASS / REJECT-F / REJECT のみ "
                     "(3 回目の look 禁止、§4.4)")
    return notes


# ══════════════════════════════════════════════════════════════════════
# main — env/argparse/IO はここに集約 (モジュールトップ副作用禁止)
# ══════════════════════════════════════════════════════════════════════

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="E1 positioning contrarian pre-reg 判定ハーネス "
                    "(spec: e1-positioning-contrarian-prereg-2026-07-16.md)")
    ap.add_argument("--artifact", help="凍結 export artifact (JSON/CSV)")
    ap.add_argument("--health", default="",
                    help="positioning_health 系列 (JSON、artifact に無い場合)")
    ap.add_argument("--ohlcv-dir", default="",
                    help="OHLCV M15 parquet ディレクトリ ({PAIR}_15m.parquet、"
                         "cutoff 切詰め版)")
    ap.add_argument("--cutoff", default="",
                    help=f"データ cutoff (ISO8601)。省略時 look1="
                         f"{DEFAULT_CUTOFF_LOOK1} / look2={DEFAULT_CUTOFF_LOOK2}")
    ap.add_argument("--look", type=int, choices=(1, 2), default=1)
    ap.add_argument("--look2-combos", default="",
                    help="second look 対象 (first look C3、カンマ区切り。例 "
                         "S1x4h,S2x4h)")
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT,
                    help=f"bootstrap seed (default 固定定数 {SEED_DEFAULT})")
    ap.add_argument("--n-boot", type=int, default=N_BOOT_DEFAULT)
    ap.add_argument("--sens-boot", type=int, default=None,
                    help="L 感度 (Secondary) の B (default: --n-boot と同じ)")
    ap.add_argument("--out", default="",
                    help="出力 JSON (default: knowledge-base/raw/bt-results/"
                         "e1_prereg_look{N}_{date}.json)")
    ap.add_argument("--postponed-before", action="store_true",
                    help="§2.5-3 postpone 発動済み (2 回目不達 = DEFERRED)")
    ap.add_argument("--verdict-run", action="store_true",
                    help="実データ実行の明示宣言 (§6-2 — synthetic 宣言の無い "
                         "artifact はこのフラグ無しでは拒否)")
    ap.add_argument("--self-check", action="store_true",
                    help="canary leak suite のみ実行して終了")
    args = ap.parse_args(argv)

    if args.self_check:
        res = run_canary_suite()
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0 if res["pass"] else 1

    if not args.artifact or not args.ohlcv_dir:
        ap.error("--artifact と --ohlcv-dir は必須 (--self-check 以外)")
    artifact = load_artifact(args.artifact, args.health)
    if not artifact.get("synthetic") and not args.verdict_run:
        print("REFUSED: artifact に synthetic 宣言が無く --verdict-run も無い。\n"
              "§6-2: 実データへの初適用は verdict 期日 (first look 2026-10-15)。\n"
              "合成 dry-run は artifact に \"synthetic\": true を付けること。",
              file=sys.stderr)
        return 2

    cutoff = _utc(args.cutoff or (DEFAULT_CUTOFF_LOOK1 if args.look == 1
                                  else DEFAULT_CUTOFF_LOOK2))
    bars_by_pair: Dict[str, Dict[str, np.ndarray]] = {}
    for pair in list(PRIMARY) + list(CONFIRMATORY):
        fp = os.path.join(args.ohlcv_dir, f"{pair}_15m.parquet")
        if os.path.exists(fp):
            bars_by_pair[pair] = load_bars(args.ohlcv_dir, pair)
    if not bars_by_pair:
        ap.error(f"OHLCV parquet が {args.ohlcv_dir} に見つからない")

    input_meta = {"artifact": args.artifact, "artifact_sha256":
                  _sha256(args.artifact),
                  "health": args.health or None,
                  "ohlcv": {p: {"path": bars_by_pair[p]["source"],
                                "sha256": _sha256(bars_by_pair[p]["source"])}
                            for p in bars_by_pair
                            if os.path.exists(str(bars_by_pair[p]["source"]))}}
    look2_combos = ([c.strip() for c in args.look2_combos.split(",") if c.strip()]
                    or None)
    result = run_eval(artifact, bars_by_pair, cutoff, look=args.look,
                      seed=args.seed, n_boot=args.n_boot,
                      sens_boot=args.sens_boot,
                      postponed_before=args.postponed_before,
                      look2_combos=look2_combos, input_meta=input_meta)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = args.out or os.path.join(
        repo, "knowledge-base", "raw", "bt-results",
        f"e1_prereg_look{args.look}_{datetime.now(timezone.utc):%Y-%m-%d}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps({"verdict": result["verdict"],
                      "quality_postpone": result["quality_gates"].get("postpone")
                      if "quality_gates" in result else None},
                     ensure_ascii=False))
    print(f"saved: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
