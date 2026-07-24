#!/usr/bin/env python3
"""E15 phase-0 OOS 判定器 — pre-reg §5c/§8 の執行 (rule:R1 手続き、純研究).

pre-reg SSOT: knowledge-base/wiki/decisions/e15-e7-event-modality-prereg-2026-07-18.md
estimand コア: tools/event_modality_lib.py (§3.5 SSOT — 判定ロジックの重複実装禁止)
凍結候補    : knowledge-base/raw/bt-results/e15_frozen_candidates.json (§5b、m0=6)
sanity 検出器: tools/event_calendar_build.py の window 共有 scan (§3.2b-7 —
              OOS 窓イベントの sanity は verdict 実行時に行う)

**設計自由度ゼロ — §5c/§8 の固定判定の執行のみ。** OOS 窓 = 2024-01-01〜2026-06-30
(イベント t_e 基準で帰属、§3.4)。--extract/--sim 分離 + seed 固定 (§11)。
test pin 先行 (§10-6) — tests/test_event_modality_oos_verdict.py。

判定 (§5c、事前固定):
  レグ A (方向性): pooled per-trade net return (ATR14d 正規化 = net_pips×pip/ATR。
    経済条件は raw pips) の **イベント日ブロック bootstrap** (event block = 同一
    イベントの全ペア・トレードを 1 ブロックとして resample、B=10,000、seed 固定、
    片側、中心化 null — E1 前例と同型) + **Ibragimov–Müller 型併設検定**
    (event-block 毎の平均 net return への片側 1 標本 t、df=blocks−1 — E1 §4.1 M10)。
    combo p = max(p_boot, p_IM)。判定: BH-FDR q=0.05 (m=m0 固定)。
  レグ B (経済性、全て充足): (a) OOS pooled time-exit 摩擦調整 EV>0
    (b) first-touch 点推定>0 (te>0 ∧ ft≤0 = sequencing 反転 → C2/REJECT 側)
    (c) stress レグ 2 種 (§3.5) 点推定>0 (d) pooled N≥30 ∧ event blocks≥15。
  ナイフエッジ 4 点 (PASS 必須): #1 fold LOFO (2024/2025/2026H1、最良 fold 除外で
    符号維持) / #2 隣接格子点 (同 event×rule で W0 or h 隣接の ≥1 が OOS 点 EV>0) /
    #3 リーク canary (unit test pin + 実データ全 sweep) + entry +1 バー遅延の符号維持 /
    #4 集中度 (LOPO 7 通り符号維持・トップ block 寄与≤40%∧除外後符号維持・
    collision 除外後符号維持)。

combo 分類 (§8、排他・この順): C1 PASS / C2 sequencing 反転 / C3 UNDERPOWERED 適格
  (te>0 ∧ ft>0 ∧ レグB(d) 不達) / C4 REJECT-F (レグA 通過 ∧ EV≤0) / C5 REJECT。
全体: C1≥1 → PASS / (C1=0 ∧ ∃C3) → UNDERPOWERED / else FAIL。

摩擦 (§3.5 凍結、判定値 f は lib.FRICTION):
  stress1 = max(1.25f, f+1.0p)
  stress2 = stress1 × 1.25 (イベント時スプレッド追加ストレス — entry 側半分
            (stress1/2) を「さらに +50%」= stress1×(0.5×1.5+0.5)。保守側の読み)

実行:
  python3 tools/event_modality_oos_verdict.py self-test   # 合成 dry-run (実データ不要)
  python3 tools/event_modality_oos_verdict.py extract     # OOS trades 抽出 (--extract)
  python3 tools/event_modality_oos_verdict.py verdict     # 統計+判定 (--sim)

**副作用禁止**: import 時に I/O/argparse を実行しない。main() は __main__ ガード内のみ。
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from tools import event_modality_lib as L  # noqa: E402

# ─── 固定定数 (§5c/§11 — seed 固定、B=10,000。verdict 前に確定、変更禁止) ────────
SEED = 20260718          # pre-reg 起案日 (固定定数)
B_BOOT = 10_000
Q_FDR = 0.05
OOS_START = "2024-01-01"
OOS_END = "2026-06-30"   # §3.4。cutoff = この日の末尾 (末尾切詰め、§3.1)
MIN_N = 30               # レグ B(d)
MIN_BLOCKS = 15          # レグ B(d)
TOP_BLOCK_SHARE_MAX = 0.40  # ナイフエッジ #4(ii)
H_CHAIN = ["h4", "h12", "h24"]  # §5a horizon grid (隣接判定用)

MASSIVE = os.path.join(_REPO, "data", "cache", "massive")
BTDIR = os.path.join(_REPO, "knowledge-base", "raw", "bt-results")
CALENDAR_JSON = os.path.join(BTDIR, "e15_e7_event_calendar.json")
FROZEN_JSON = os.path.join(BTDIR, "e15_frozen_candidates.json")
COVERAGE_JSON = os.path.join(BTDIR, "e15_e7_pair_coverage.json")
TRADES_JSON = os.path.join(BTDIR, "e15_phase0_oos_trades.json")
VERDICT_JSON = os.path.join(BTDIR, "e15_phase0_oos_verdict.json")


# ─── §3.5 摩擦バリアント ─────────────────────────────────────────────────────
def friction_variants(pair: str) -> dict:
    """base = §3.5 凍結判定値 / stress1 = max(1.25f, f+1.0) /
    stress2 = stress1×1.25 (entry 側半分をさらに +50% — docstring 参照)。"""
    f = L.FRICTION[pair]
    s1 = max(1.25 * f, f + 1.0)
    s2 = s1 * 1.25
    return {"base": f, "stress1": s1, "stress2": s2}


# ─── §5c-1 fold (OOS 年次 fold: 2024 / 2025 / 2026H1) ───────────────────────
def fold_label(t_e: pd.Timestamp) -> str:
    y = int(pd.Timestamp(t_e).year)
    if y <= 2024:
        return "2024"
    if y == 2025:
        return "2025"
    return "2026H1"   # OOS 窓は 2026-06-30 迄なので 2026 = H1


# ─── §5c-2 隣接 combo (同 event×rule で W0 または h が隣) ─────────────────────
def neighbors_of(combo: dict) -> list:
    """隣接格子点の列挙。W0 ∈ {30,60} は相互隣接、h は H_CHAIN 上の隣。
    uncond 系は W0=30 固定 (§5a) のため h 隣接のみ。"""
    out = []
    if combo["rule"] in ("fade", "follow"):
        for w0 in (30, 60):
            if w0 != combo["w0"]:
                out.append({"family": combo["family"], "event": combo["event"],
                            "rule": combo["rule"], "w0": w0, "h": combo["h"]})
    i = H_CHAIN.index(combo["h"])
    for j in (i - 1, i + 1):
        if 0 <= j < len(H_CHAIN):
            out.append({"family": combo["family"], "event": combo["event"],
                        "rule": combo["rule"], "w0": combo["w0"],
                        "h": H_CHAIN[j]})
    return out


def combo_key(c: dict) -> str:
    return f"{c['event']}|{c['rule']}|w0{c['w0']}|{c['h']}"


# ─── §5c レグ A: event-block bootstrap + Ibragimov–Müller ────────────────────
def event_block_bootstrap(values: np.ndarray, block_ids: np.ndarray,
                          n_boot: int, seed_key) -> dict:
    """event block resample (復元、block 数固定)、per-combo 中心化 null、
    片側 p (E1 mbb_pvalue と同じ規約: p=(1+#{null≥point})/(B+1))。"""
    values = np.asarray(values, dtype=float)
    point = float(np.mean(values))
    blocks = np.unique(block_ids)
    nb = int(len(blocks))
    if nb < 2 or not np.isfinite(point):
        return {"point": None if not np.isfinite(point) else round(point, 6),
                "p_one": None, "B": 0, "n_blocks": nb}
    idx_by_block = [np.where(block_ids == b)[0] for b in blocks]
    rng = np.random.default_rng(list(seed_key))
    boots = np.empty(n_boot)
    for i in range(n_boot):
        draw = rng.integers(0, nb, size=nb)
        sel = np.concatenate([idx_by_block[j] for j in draw])
        boots[i] = values[sel].mean()
    null = boots - point            # 中心化 null
    p_one = (1.0 + float(np.sum(null >= point))) / (n_boot + 1.0)
    return {"point": round(point, 6), "p_one": round(p_one, 6),
            "B": n_boot, "n_blocks": nb}


def im_block_test(values: np.ndarray, block_ids: np.ndarray) -> dict:
    """Ibragimov–Müller 型併設検定 (§5c レグ A): event-block 毎の平均 net return
    への片側 1 標本 t、df = blocks − 1。退化ケースの処置は E1 im_test と同一。"""
    from scipy.stats import t as t_dist
    values = np.asarray(values, dtype=float)
    blocks = np.unique(block_ids)
    means = [float(values[block_ids == b].mean()) for b in blocks]
    nb = len(means)
    if nb < 2:
        return {"p": None, "t": None, "df": None, "n_blocks": nb}
    arr = np.array(means)
    mean = float(arr.mean())
    se = float(arr.std(ddof=1)) / math.sqrt(nb)
    df = nb - 1
    if se > 0:
        tval = mean / se
        p = float(t_dist.sf(tval, df))
    elif mean > 0:
        tval, p = float("inf"), 0.0    # 全 block 同値かつ宣言符号 → 最有意
    elif mean < 0:
        tval, p = float("-inf"), 1.0   # 宣言と逆符号の退化 → 有意にしない
    else:
        tval, p = float("nan"), None   # 全 block 0 — 検定不能
    return {"p": None if p is None else round(p, 6),
            "t": (None if isinstance(tval, float) and math.isnan(tval)
                  else (tval if math.isinf(tval) else round(tval, 5))),
            "df": df, "n_blocks": nb,
            "block_mean": round(mean, 6), "block_se": round(se, 6)}


def bh_fdr(pvals: dict, q: float, m: int) -> dict:
    """Benjamini–Hochberg FDR。m は family 全体で固定 (m=m0 — p 未定義 combo が
    あっても分母は縮めない。E1 bh_fdr と同一規約)。"""
    defined = {k: v for k, v in pvals.items() if v is not None}
    order = sorted(defined.items(), key=lambda kv: kv[1])
    k_max = 0
    for rank_i, (_, p) in enumerate(order, start=1):
        if p <= q * rank_i / max(1, m):
            k_max = rank_i
    out = {}
    for rank_i, (key, p) in enumerate(order, start=1):
        out[key] = {"p": p, "rank": rank_i,
                    "threshold": round(q * rank_i / max(1, m), 6),
                    "survive": rank_i <= k_max}
    for key, p in pvals.items():
        if p is None:
            out[key] = {"p": None, "rank": None, "threshold": None,
                        "survive": False}
    return out


# ─── §5c ナイフエッジ (純関数 — trade 配列から計算) ──────────────────────────
def _sign_maintained(full: float, rest: float) -> bool:
    """符号維持 = 全標本 pooled EV と同符号 (非ゼロ)。"""
    return bool(full > 0 and rest > 0) or bool(full < 0 and rest < 0)


def knife_fold_lofo(net: np.ndarray, folds: np.ndarray) -> dict:
    """#1 fold 集中: 最良 fold (pooled EV 最大) 除外の残り pooled EV 符号維持。"""
    full = float(np.mean(net))
    labels = sorted(set(folds.tolist()))
    fold_ev = {f: float(net[folds == f].mean()) for f in labels
               if int((folds == f).sum()) > 0}
    if len(fold_ev) < 2:
        return {"pass": False, "reason": "folds<2", "fold_ev": fold_ev,
                "full_ev": round(full, 4)}
    best = max(fold_ev, key=fold_ev.get)
    rest = net[folds != best]
    rest_ev = float(rest.mean()) if len(rest) else float("nan")
    ok = len(rest) > 0 and _sign_maintained(full, rest_ev)
    return {"pass": bool(ok), "best_fold": best,
            "fold_ev": {k: round(v, 4) for k, v in fold_ev.items()},
            "rest_ev": None if math.isnan(rest_ev) else round(rest_ev, 4),
            "full_ev": round(full, 4)}


def knife_top_block(net: np.ndarray, block_ids: np.ndarray) -> dict:
    """#4(ii) トップ 1 event block の寄与 ≤ 40% ∧ 除外後符号維持。
    寄与 = 最大 block 純益合計 / 全体純益合計 (全体 > 0 が前提 — レグ B(a))。"""
    full = float(np.mean(net))
    total = float(np.sum(net))
    blocks = np.unique(block_ids)
    sums = {str(b): float(net[block_ids == b].sum()) for b in blocks}
    top = max(sums, key=sums.get)
    share = (sums[top] / total) if total > 0 else None
    rest = net[block_ids != top]
    rest_ev = float(rest.mean()) if len(rest) else float("nan")
    ok = (share is not None and share <= TOP_BLOCK_SHARE_MAX
          and len(rest) > 0 and _sign_maintained(full, rest_ev))
    return {"pass": bool(ok), "top_block": top,
            "top_share": None if share is None else round(share, 4),
            "rest_ev": None if math.isnan(rest_ev) else round(rest_ev, 4)}


def knife_lopo(net: np.ndarray, pairs: np.ndarray) -> dict:
    """#4(i) leave-one-pair-out 全通りで pooled EV 符号維持。"""
    full = float(np.mean(net))
    detail = {}
    ok = True
    for p in sorted(set(pairs.tolist())):
        rest = net[pairs != p]
        ev = float(rest.mean()) if len(rest) else float("nan")
        keep = len(rest) > 0 and _sign_maintained(full, ev)
        detail[p] = {"ev_excl": None if math.isnan(ev) else round(ev, 4),
                     "sign_maintained": bool(keep)}
        ok = ok and keep
    return {"pass": bool(ok), "detail": detail}


def knife_excl_mask(net: np.ndarray, mask_excl: np.ndarray,
                    label: str) -> dict:
    """フラグ付き trade 除外後の pooled EV 符号維持 (#4(iii) collision 等)。
    フラグ 0 件なら vacuous pass (除外対象なし)。"""
    full = float(np.mean(net))
    n_excl = int(mask_excl.sum())
    if n_excl == 0:
        return {"pass": True, "n_excluded": 0, "rest_ev": round(full, 4),
                "note": f"no {label}-flagged trades (vacuous)"}
    rest = net[~mask_excl]
    if len(rest) == 0:
        return {"pass": False, "n_excluded": n_excl, "rest_ev": None,
                "note": f"all trades {label}-flagged"}
    ev = float(rest.mean())
    return {"pass": bool(_sign_maintained(full, ev)), "n_excluded": n_excl,
            "rest_ev": round(ev, 4)}


# ─── §8 combo 分類 (排他、この順) ────────────────────────────────────────────
def classify_combo(s: dict) -> str:
    """s: leg_a_pass / ev_te / ev_ft / leg_b_d / leg_b_all / knife_all。"""
    if s["leg_a_pass"] and s["leg_b_all"] and s["knife_all"]:
        return "C1"
    if s["ev_te"] > 0 and s["ev_ft"] <= 0:
        return "C2"    # sequencing 反転 (REJECT 側)
    if s["ev_te"] > 0 and s["ev_ft"] > 0 and not s["leg_b_d"]:
        return "C3"    # UNDERPOWERED 適格
    if s["leg_a_pass"] and s["ev_te"] <= 0:
        return "C4"    # REJECT-F
    return "C5"        # REJECT


def overall_verdict(classes) -> str:
    if any(c == "C1" for c in classes):
        return "PASS"
    if any(c == "C3" for c in classes):
        return "UNDERPOWERED"
    return "FAIL"


# ─── extract: OOS trades 抽出 (--extract。gross 記録、摩擦は stats 層で適用) ──
def oos_events(calendar: dict, event_type: str) -> list:
    lo = pd.Timestamp(OOS_START, tz="UTC")
    hi = pd.Timestamp(OOS_END, tz="UTC") + pd.Timedelta(days=1) \
        - pd.Timedelta(seconds=1)
    ts = [pd.Timestamp(x) for x in calendar.get(event_type, [])]
    ts = [t if t.tz is not None else t.tz_localize("UTC") for t in ts]
    return sorted(t for t in ts if lo <= t <= hi)


def all_calendar_events(calendar: dict) -> list:
    """collision 判定用: 全イベント (種別問わず) の (ts, type) リスト。"""
    out = []
    for ev, lst in calendar.items():
        for x in lst:
            t = pd.Timestamp(x)
            out.append((t if t.tz is not None else t.tz_localize("UTC"), ev))
    return sorted(out, key=lambda p: p[0])


def has_collision(t_e: pd.Timestamp, term_ts: pd.Timestamp, own_event: str,
                  all_events: list) -> bool:
    """horizon 窓 [t_e, term_ts] 内に他イベント発表を含むか (§3.2)。
    自イベント自身 (同時刻・同種) は除く。"""
    for ts, ev in all_events:
        if ts > term_ts:
            break
        if ts < t_e:
            continue
        if ts == t_e and ev == own_event:
            continue
        return True
    return False


def extract_combo_trades(combo: dict, calendar: dict, bars: dict,
                         all_events: list, pair_list) -> list:
    """1 combo × pair_list の OOS per-trade 抽出。gross (friction=0) で記録し、
    摩擦バリアントは stats 層で線形適用 (event_trade の friction 減算と等価 —
    test pin 済)。遅延レグ (entry +1 バー) も同時抽出。"""
    trades = []
    for t_e in oos_events(calendar, combo["event"]):
        for pair in pair_list:
            if pair not in bars:
                continue
            m15, daily = bars[pair]
            out = L.event_trade(m15, daily, t_e, pair, combo["rule"],
                                combo["w0"], combo["h"], friction=0.0)
            if out is None:
                continue
            delayed = L.event_trade(m15, daily, t_e, pair, combo["rule"],
                                    combo["w0"], combo["h"], friction=0.0,
                                    entry_delay_bars=1)
            term_pos = out.entry_pos + L.HORIZON_BARS[combo["h"]]
            term_ts = m15.index[term_pos]
            entry_ts = m15.index[out.entry_pos]
            trades.append({
                "event": combo["event"], "t_e": t_e.isoformat(), "pair": pair,
                "direction": int(out.direction),
                "entry_ts": entry_ts.isoformat(), "term_ts": term_ts.isoformat(),
                "gross_te_pip": round(float(out.time_exit_pip), 4),
                "gross_ft_pip": round(float(out.first_touch_pip), 4),
                "gross_te_delay_pip": (None if delayed is None
                                       else round(float(delayed.time_exit_pip), 4)),
                "atr": float(out.atr), "pip": L.pip_size(pair),
                "fold": fold_label(t_e),
                "weekend_span": bool(out.weekend_span),
                "collision": has_collision(t_e, term_ts, combo["event"],
                                           all_events),
            })
    return trades


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_and_verify_bars(coverage: dict) -> tuple:
    """13 ペア parquet を読み、coverage 台帳との再現を検証 (部分 parquet 罠の
    機械ガード)。検証不変量: (a) first = 台帳 first (フル歴史起点)、
    (b) explore_coverage = 台帳値と完全一致 (§3.1 の凍結量)、
    (c) 台帳 last 時点までの行数 = 台帳 rows (共通窓での bar 数一致 —
    台帳スナップショット後に fetch された末尾余剰バーは OOS cutoff で
    切詰められるため判定に無関係)。
    OOS_END で末尾切詰め (§3.1 cutoff — フル期間版から切詰める) した frame を返す。"""
    ledger = coverage["ledger"]
    bars, data_ledger = {}, {}
    cutoff = pd.Timestamp(OOS_END, tz="UTC") + pd.Timedelta(days=1) \
        - pd.Timedelta(seconds=1)
    errors = []
    for pair in L.ALL_PAIRS:
        f = os.path.join(MASSIVE, f"{pair}_15m.parquet")
        if not os.path.exists(f):
            errors.append(f"{pair}: parquet missing")
            continue
        m15 = pd.read_parquet(f)
        if m15.index.tz is None:
            m15.index = m15.index.tz_localize("UTC")
        led = ledger.get(pair, {})
        cov = round(L.market_time_coverage(
            m15, coverage["explore_window"][0], coverage["explore_window"][1]), 4)
        led_last = pd.Timestamp(led.get("last"))
        rows_at_led_last = int((m15.index <= led_last).sum())
        checks = {
            "first": (str(m15.index[0]), led.get("first")),
            "explore_coverage": (cov, led.get("explore_coverage")),
            "rows_at_ledger_last": (rows_at_led_last, led.get("rows")),
        }
        bad = {k: v for k, v in checks.items() if v[0] != v[1]}
        if bad:
            errors.append(f"{pair}: ledger mismatch {bad}")
            continue
        full_rows = len(m15)
        m15 = m15.loc[m15.index <= cutoff]
        bars[pair] = (m15, L.build_daily_from_m15(m15))
        data_ledger[pair] = {
            "sha256": _sha256(f), "rows_full": full_rows,
            "rows_at_ledger_last": rows_at_led_last,
            "rows_after_cutoff": len(m15), "explore_coverage": cov,
            "tail_surplus_rows": full_rows - rows_at_led_last,
            "ledger_match": True,
        }
    return bars, data_ledger, errors


def canary_sweep(candidates: list, calendar: dict, bars: dict) -> dict:
    """§5c-3 リーク canary の実データ全 sweep — 全 (event, pair, rule, w0) 重複排除。
    horizon は canary に影響しないため代表 1 点。40 日 slice で高速化 (等価:
    canary は slice 内部の相対比較のみ)。"""
    seen = set()
    n_checked, n_dirty, dirty = 0, 0, []
    for c in candidates:
        for t_e in oos_events(calendar, c["event"]):
            for pair in L.PRIMARY_PAIRS:
                key = (c["event"], str(t_e), pair, c["rule"], c["w0"])
                if key in seen or pair not in bars:
                    continue
                seen.add(key)
                m15, _ = bars[pair]
                lo = t_e - pd.Timedelta(days=40)
                hi = t_e + pd.Timedelta(days=3)
                sl = m15.loc[(m15.index >= lo) & (m15.index <= hi)]
                if sl.empty:
                    continue
                daily_sl = L.build_daily_from_m15(sl)
                n_checked += 1
                ok = L.leak_canary(sl, daily_sl, t_e, pair, c["rule"],
                                   c["w0"], c["h"])
                if not ok:
                    n_dirty += 1
                    dirty.append({"event": c["event"], "t_e": str(t_e),
                                  "pair": pair, "rule": c["rule"],
                                  "w0": c["w0"]})
    return {"n_checked": n_checked, "n_dirty": n_dirty,
            "all_clean": n_dirty == 0, "dirty": dirty}


def extract() -> int:
    for path, name in ((CALENDAR_JSON, "calendar"), (FROZEN_JSON, "frozen"),
                       (COVERAGE_JSON, "coverage")):
        if not os.path.exists(path):
            print(f"[BLOCKED] {name} not found: {path}", file=sys.stderr)
            return 2
    with open(CALENDAR_JSON) as fh:
        cal = json.load(fh)
    calendar = cal.get("events", cal)
    with open(FROZEN_JSON) as fh:
        frozen = json.load(fh)
    with open(COVERAGE_JSON) as fh:
        coverage = json.load(fh)
    if frozen.get("status") != "FROZEN":
        print("[BLOCKED] frozen candidates not FROZEN", file=sys.stderr)
        return 2
    candidates = frozen["candidates"]

    bars, data_ledger, errors = load_and_verify_bars(coverage)
    if errors or len([p for p in L.PRIMARY_PAIRS if p in bars]) < 5:
        print(f"[BLOCKED] parquet/ledger verification failed: {errors}",
              file=sys.stderr)
        return 4
    print(f"parquet ledger reproduction OK: {len(bars)}/13 pairs")

    # §3.2b-7: OOS 窓イベントの sanity は verdict 実行時に行う (range のみ)
    from tools import event_calendar_build as C
    lo = pd.Timestamp(OOS_START, tz="UTC")
    hi = pd.Timestamp(OOS_END, tz="UTC") + pd.Timedelta(days=1) \
        - pd.Timedelta(seconds=1)
    bars_m15 = {p: b[0] for p, b in bars.items() if p in L.PRIMARY_PAIRS}
    sanity_res, worst_rate = C.range_sanity_scan(cal, bars_m15, lo, hi)
    peak_res, all_peak_zero = C.offset_peak_scan(cal, bars_m15, lo, hi)
    oos_sanity = {
        "scope": f"OOS window {OOS_START}..{OOS_END} (§3.2b-7)",
        "results": sanity_res, "worst_rate": round(worst_rate, 4),
        "offset_peak": peak_res, "all_peak_zero": bool(all_peak_zero),
    }
    if worst_rate > 0.05 and not all_peak_zero:
        # 時刻破損の徴候 (offset ピーク ≠ 0) — user 裁定へ (§8 DEFERRED)
        print(f"[DEFERRED] OOS sanity {worst_rate:.1%} > 5% AND offset peak "
              f"anomaly — §8 user 裁定。verdict を実行しない", file=sys.stderr)
        _write(TRADES_JSON, {"status": "DEFERRED_SANITY", "sanity": oos_sanity})
        return 5
    if worst_rate > 0.05:
        # 2026-07-22 user 裁定と同一シグネチャ (低インパクト由来、offset +0 ピーク
        # = 時刻正常) — 裁定済み事項として続行し記録する
        print(f"[NOTE] OOS sanity {worst_rate:.1%} > 5% but offset peak +0 "
              f"(時刻正常) — 2026-07-22 user 裁定 (低インパクト由来) と同一事象"
              f"として続行・記録", file=sys.stderr)

    all_events = all_calendar_events(calendar)

    # 凍結 6 候補 (primary block) + 隣接格子点 (#2) + cross block (記述のみ)
    cand_out, neigh_out, cross_out = [], {}, []
    for i, c in enumerate(candidates):
        trades = extract_combo_trades(c, calendar, bars, all_events,
                                      L.PRIMARY_PAIRS)
        cand_out.append({"combo": {k: c[k] for k in
                                   ("family", "event", "rule", "w0", "h")},
                         "key": combo_key(c), "cand_idx": i, "trades": trades})
        for nb in neighbors_of(c):
            k = combo_key(nb)
            if k in neigh_out or any(combo_key(x) == k for x in candidates):
                continue   # 凍結候補自身が隣接の場合は candidates 側で計算
            neigh_out[k] = {
                "combo": nb,
                "trades": extract_combo_trades(nb, calendar, bars, all_events,
                                               L.PRIMARY_PAIRS)}
        cross_trades = extract_combo_trades(c, calendar, bars, all_events,
                                            L.CROSS_PAIRS)
        cross_out.append({"key": combo_key(c), "n": len(cross_trades),
                          "trades": cross_trades})

    canary = canary_sweep(candidates, calendar, bars)
    print(f"canary sweep: {canary['n_checked']} checked, "
          f"dirty={canary['n_dirty']}")

    _write(TRADES_JSON, {
        "status": "EXTRACTED",
        "prereg": "e15-e7-event-modality-prereg-2026-07-18 §5c",
        "extracted_utc": datetime.now(timezone.utc).isoformat(),
        "oos_window": [OOS_START, OOS_END],
        "cutoff_rule": f"m15 tail-truncated at {OOS_END} end-of-day (§3.1)",
        "m0": frozen["m0"],
        "data_ledger": data_ledger,
        "oos_sanity": oos_sanity,
        "canary": canary,
        "candidates": cand_out,
        "neighbors": neigh_out,
        "cross_block_descriptive": cross_out,
    })
    n_tr = sum(len(c["trades"]) for c in cand_out)
    print(f"extract OK: {len(cand_out)} candidates, {n_tr} trades, "
          f"{len(neigh_out)} neighbor combos → {TRADES_JSON}")
    return 0


# ─── verdict: 統計 + 判定 (--sim) ────────────────────────────────────────────
def _arrays(trades: list) -> dict:
    f_base = np.array([friction_variants(t["pair"])["base"] for t in trades])
    f_s1 = np.array([friction_variants(t["pair"])["stress1"] for t in trades])
    f_s2 = np.array([friction_variants(t["pair"])["stress2"] for t in trades])
    gross_te = np.array([t["gross_te_pip"] for t in trades], dtype=float)
    gross_ft = np.array([t["gross_ft_pip"] for t in trades], dtype=float)
    atr = np.array([t["atr"] for t in trades], dtype=float)
    pip = np.array([t["pip"] for t in trades], dtype=float)
    return {
        "net_te": gross_te - f_base,
        "net_ft": gross_ft - f_base,
        "net_te_s1": gross_te - f_s1,
        "net_te_s2": gross_te - f_s2,
        "net_ft_s1": gross_ft - f_s1,
        "net_ft_s2": gross_ft - f_s2,
        "norm_te": (gross_te - f_base) * pip / atr,
        "delay_net_te": np.array(
            [(t["gross_te_delay_pip"] - fb) if t["gross_te_delay_pip"]
             is not None else np.nan
             for t, fb in zip(trades, f_base)], dtype=float),
        "blocks": np.array([t["t_e"] for t in trades]),
        "folds": np.array([t["fold"] for t in trades]),
        "pairs": np.array([t["pair"] for t in trades]),
        "collision": np.array([t["collision"] for t in trades], dtype=bool),
        "weekend": np.array([t["weekend_span"] for t in trades], dtype=bool),
    }


def evaluate_candidate(trades: list, cand_idx: int, neighbor_evs: list,
                       canary_all_clean: bool, n_boot: int = B_BOOT,
                       seed: int = SEED) -> dict:
    """1 candidate の §5c 全レグ + ナイフエッジ (BH は family 一括で後段)。"""
    a = _arrays(trades)
    N = len(trades)
    n_blocks = int(len(np.unique(a["blocks"])))
    ev_te = float(np.mean(a["net_te"]))
    ev_ft = float(np.mean(a["net_ft"]))

    # レグ A (BH survive は後段で確定)
    boot = event_block_bootstrap(a["norm_te"], a["blocks"], n_boot,
                                 (seed, cand_idx))
    im = im_block_test(a["norm_te"], a["blocks"])
    p_combo = (max(boot["p_one"], im["p"])
               if (boot["p_one"] is not None and im["p"] is not None) else None)

    # レグ B
    leg_b = {
        "a_ev_te_pos": ev_te > 0,
        "b_ev_ft_pos": ev_ft > 0,
        "c_stress": {
            "ev_te_stress1": round(float(np.mean(a["net_te_s1"])), 4),
            "ev_te_stress2": round(float(np.mean(a["net_te_s2"])), 4),
            "ev_ft_stress1": round(float(np.mean(a["net_ft_s1"])), 4),
            "ev_ft_stress2": round(float(np.mean(a["net_ft_s2"])), 4),
            "pass": bool(np.mean(a["net_te_s1"]) > 0
                         and np.mean(a["net_te_s2"]) > 0),
        },
        "d_power": {"N": N, "blocks": n_blocks,
                    "pass": bool(N >= MIN_N and n_blocks >= MIN_BLOCKS)},
    }
    leg_b_all = bool(leg_b["a_ev_te_pos"] and leg_b["b_ev_ft_pos"]
                     and leg_b["c_stress"]["pass"] and leg_b["d_power"]["pass"])

    # ナイフエッジ
    k1 = knife_fold_lofo(a["net_te"], a["folds"])
    k2_pass = any(ev is not None and ev > 0 for ev in neighbor_evs)
    delay_vals = a["delay_net_te"][~np.isnan(a["delay_net_te"])]
    delay_ev = float(np.mean(delay_vals)) if len(delay_vals) else float("nan")
    k3 = {"canary_all_clean": bool(canary_all_clean),
          "delay_ev": None if math.isnan(delay_ev) else round(delay_ev, 4),
          "n_delay": int(len(delay_vals)),
          "pass": bool(canary_all_clean and len(delay_vals) > 0
                       and _sign_maintained(ev_te, delay_ev))}
    k4_lopo = knife_lopo(a["net_te"], a["pairs"])
    k4_top = knife_top_block(a["net_te"], a["blocks"])
    k4_coll = knife_excl_mask(a["net_te"], a["collision"], "collision")
    knife = {
        "k1_fold_lofo": k1,
        "k2_neighbor": {"neighbor_evs": neighbor_evs, "pass": bool(k2_pass)},
        "k3_leak_delay": k3,
        "k4_concentration": {"lopo": k4_lopo, "top_block": k4_top,
                             "collision_excl": k4_coll,
                             "pass": bool(k4_lopo["pass"] and k4_top["pass"]
                                          and k4_coll["pass"])},
    }
    knife_all = bool(k1["pass"] and k2_pass and k3["pass"]
                     and knife["k4_concentration"]["pass"])

    # Secondary 記述 (週末跨ぎ層別 — 判定不使用、§3.5)
    wk = a["weekend"]
    weekend_strat = {
        "n_weekend": int(wk.sum()),
        "ev_te_weekend": (round(float(a["net_te"][wk].mean()), 4)
                          if wk.any() else None),
        "ev_te_non_weekend": (round(float(a["net_te"][~wk].mean()), 4)
                              if (~wk).any() else None),
    }

    return {
        "N": N, "event_blocks": n_blocks,
        "ev_time_exit": round(ev_te, 4), "ev_first_touch": round(ev_ft, 4),
        "ev_te_norm_atr": boot["point"],
        "leg_a": {"p_boot": boot["p_one"], "boot_B": boot["B"],
                  "im": im, "p_combo": p_combo},
        "leg_b": leg_b, "leg_b_all": leg_b_all,
        "knife": knife, "knife_all": knife_all,
        "secondary_weekend": weekend_strat,
        "n_collision": int(a["collision"].sum()),
    }


def run_verdict(extracted: dict, n_boot: int = B_BOOT,
                seed: int = SEED) -> dict:
    """--sim 本体: 抽出済み trades → §5c 統計 → BH → §8 分類 → 全体 verdict。
    純関数 (I/O なし) — self-test と本番の両方から呼ぶ。"""
    m0 = int(extracted["m0"])
    canary_clean = bool(extracted["canary"]["all_clean"])

    # 隣接格子点の pooled EV (base 摩擦) — #2 用。凍結候補自身も隣接になり得る
    neigh_ev = {}
    for k, rec in extracted["neighbors"].items():
        tr = rec["trades"]
        if tr:
            arr = _arrays(tr)
            neigh_ev[k] = {"ev_te": round(float(np.mean(arr["net_te"])), 4),
                           "N": len(tr),
                           "blocks": int(len(np.unique(arr["blocks"])))}
        else:
            neigh_ev[k] = {"ev_te": None, "N": 0, "blocks": 0}
    cand_ev = {}
    for rec in extracted["candidates"]:
        tr = rec["trades"]
        if tr:
            cand_ev[rec["key"]] = round(
                float(np.mean(_arrays(tr)["net_te"])), 4)

    results = []
    pvals = {}
    for rec in extracted["candidates"]:
        key, i = rec["key"], rec["cand_idx"]
        if not rec["trades"]:
            # fail-loud stub: OOS trade ゼロは C5 (REJECT) — 点推定不能
            results.append({
                "key": key, "combo": rec["combo"], "N": 0, "event_blocks": 0,
                "ev_time_exit": None, "ev_first_touch": None,
                "ev_te_norm_atr": None,
                "leg_a": {"p_boot": None, "boot_B": 0,
                          "im": {"p": None}, "p_combo": None, "pass": False},
                "leg_b": None, "leg_b_all": False,
                "knife": None, "knife_all": False,
                "classification": "C5", "note": "no OOS trades (fail-loud)"})
            pvals[key] = None
            continue
        nb_evs = []
        for nb in neighbors_of(rec["combo"]):
            k = combo_key(nb)
            if k in cand_ev:
                nb_evs.append(cand_ev[k])
            elif k in neigh_ev:
                nb_evs.append(neigh_ev[k]["ev_te"])
        r = evaluate_candidate(rec["trades"], i, nb_evs, canary_clean,
                               n_boot=n_boot, seed=seed)
        r["key"] = key
        r["combo"] = rec["combo"]
        results.append(r)
        pvals[key] = r["leg_a"]["p_combo"]

    bh = bh_fdr(pvals, Q_FDR, m0)
    classes = []
    for r in results:
        r["bh"] = bh[r["key"]]
        r["leg_a"]["pass"] = bool(bh[r["key"]]["survive"])
        if r["N"] == 0:
            classes.append(r["classification"])   # fail-loud stub (C5)
            continue
        cls = classify_combo({
            "leg_a_pass": r["leg_a"]["pass"], "ev_te": r["ev_time_exit"],
            "ev_ft": r["ev_first_touch"],
            "leg_b_d": r["leg_b"]["d_power"]["pass"],
            "leg_b_all": r["leg_b_all"], "knife_all": r["knife_all"]})
        r["classification"] = cls
        classes.append(cls)

    verdict = overall_verdict(classes)
    counts = {c: classes.count(c) for c in ("C1", "C2", "C3", "C4", "C5")}
    branch = {
        "PASS": "§8 phase-0 PASS ≥ 1 → D4 準拠の実装 pre-reg 起案 + user 最終"
                "承認 (S5)。phase-1 は α 予算どおり継続 (併走)",
        "UNDERPOWERED": "§8 UNDERPOWERED (∃C3 ∧ C1 ゼロ) → cache が 2027-07-01 "
                        "以降へ延伸した時点で C3 combo のみ・同一 spec・1 回限りの"
                        "再判定 (BH m=|C3|、q=0.05 新規予算を family 外で明示計上 — "
                        "registry 条件付きエントリ)。phase-1 は予定どおり実行",
        "FAIL": "§8 phase-0 PASS = 0 → phase-1 は予定どおり実行 (無条件仮説の "
                "FAIL はサプライズ条件付き仮説を falsify しない — 今宣言)",
    }[verdict]

    # cross block out-of-block 複製記録 (§4 — PASS 候補のみ、記述専用)
    cross_desc = []
    for rec in extracted.get("cross_block_descriptive", []):
        key = rec["key"]
        cls = next((r["classification"] for r in results if r["key"] == key),
                   None)
        if cls == "C1" and rec["trades"]:
            arr = _arrays(rec["trades"])
            cross_desc.append({
                "key": key, "n": len(rec["trades"]),
                "ev_te": round(float(np.mean(arr["net_te"])), 4),
                "ev_ft": round(float(np.mean(arr["net_ft"])), 4)})
    return {
        "results": results, "bh": bh, "class_counts": counts,
        "verdict": verdict, "branch": branch,
        "neighbor_evs": neigh_ev, "cross_block_pass_replication": cross_desc,
    }


def verdict() -> int:
    if not os.path.exists(TRADES_JSON):
        print(f"[BLOCKED] run extract first: {TRADES_JSON}", file=sys.stderr)
        return 2
    with open(TRADES_JSON) as fh:
        extracted = json.load(fh)
    if extracted.get("status") != "EXTRACTED":
        print(f"[BLOCKED] trades status={extracted.get('status')}",
              file=sys.stderr)
        return 2

    out = run_verdict(extracted)
    artifact = {
        "status": "VERDICT",
        "prereg": "e15-e7-event-modality-prereg-2026-07-18 §5c/§8",
        "rule": "R1 手続き (pre-reg 執行、判定は機械)",
        "executed_utc": datetime.now(timezone.utc).isoformat(),
        "oos_window": [OOS_START, OOS_END],
        "seed": SEED, "B": B_BOOT, "q_fdr": Q_FDR, "m0": extracted["m0"],
        "friction_rule": "base=§3.5 凍結判定値 / stress1=max(1.25f,f+1.0) / "
                         "stress2=stress1*1.25 (entry 側半分をさらに+50%)",
        "leg_a_stat": "pooled per-trade net time-exit return, ATR14d-normalized "
                      "(net_pips*pip/ATR); one-sided event-block bootstrap "
                      "(centered null) + Ibragimov-Muller block t (df=blocks-1); "
                      "p=max(p_boot,p_IM); BH-FDR q=0.05 m=m0",
        "overall": {"verdict": out["verdict"],
                    "class_counts": out["class_counts"],
                    "branch": out["branch"]},
        "candidates": out["results"],
        "neighbor_grid_evs": out["neighbor_evs"],
        "cross_block_pass_replication": out["cross_block_pass_replication"],
        "data_ledger": extracted["data_ledger"],
        "oos_sanity": extracted["oos_sanity"],
        "canary": extracted["canary"],
        "trades": {rec["key"]: rec["trades"]
                   for rec in extracted["candidates"]},
    }
    _write(VERDICT_JSON, artifact)
    print(f"verdict: {out['verdict']} (classes={out['class_counts']}) "
          f"→ {VERDICT_JSON}")
    for r in out["results"]:
        print(f"  {r['key']}: {r['classification']} | N={r['N']} "
              f"blocks={r['event_blocks']} EV_te={r['ev_time_exit']} "
              f"EV_ft={r['ev_first_touch']} p={r['leg_a']['p_combo']} "
              f"BH={r['bh']['survive']}")
    return 0


def _write(path: str, obj: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2, default=str)


# ─── self-test: 合成 dry-run (実データ不要、§10-6) ───────────────────────────
def _synth_extracted(effect_pip: float, n_events: int = 24,
                     seed: int = 7) -> dict:
    """合成 trades で extract 出力と同形の dict を作る (判定パイプ結線検証)。"""
    rng = np.random.default_rng(seed)
    combo = {"family": "e15", "event": "FOMC", "rule": "follow",
             "w0": 60, "h": "h12"}
    trades = []
    months = pd.date_range("2024-02-01", periods=n_events, freq="MS")
    for k, day in enumerate(months):
        t_e = L.et_to_utc(day.date(), 14, 0)
        block_shift = rng.normal(0, 5.0)
        for pair in L.PRIMARY_PAIRS[:5]:
            gross = effect_pip + block_shift + rng.normal(0, 8.0)
            trades.append({
                "event": "FOMC", "t_e": t_e.isoformat(), "pair": pair,
                "direction": 1, "entry_ts": t_e.isoformat(),
                "term_ts": (t_e + pd.Timedelta(hours=12)).isoformat(),
                "gross_te_pip": round(gross, 4),
                "gross_ft_pip": round(gross, 4),
                "gross_te_delay_pip": round(gross * 0.9, 4),
                "atr": 0.0060, "pip": 0.0001,
                "fold": fold_label(t_e),
                "weekend_span": False, "collision": (k % 11 == 0),
            })
    nb_key = combo_key({"event": "FOMC", "rule": "follow", "w0": 30,
                        "h": "h12"})
    return {
        "status": "EXTRACTED", "m0": 6,
        "canary": {"n_checked": 1, "n_dirty": 0, "all_clean": True,
                   "dirty": []},
        "candidates": [{"combo": combo, "key": combo_key(combo),
                        "cand_idx": 0, "trades": trades}],
        "neighbors": {nb_key: {"combo": {"family": "e15", "event": "FOMC",
                                         "rule": "follow", "w0": 30,
                                         "h": "h12"},
                               "trades": trades[: len(trades) // 2]}},
        "cross_block_descriptive": [],
        "data_ledger": {}, "oos_sanity": {"note": "synthetic"},
    }


def self_test() -> int:
    """合成データで判定パイプを end-to-end 実行 (実 OOS 不使用、決定論)。"""
    # 強い正効果 → レグ A 有意側、null → 非有意側 (B は速度優先で縮小)
    strong = run_verdict(_synth_extracted(effect_pip=25.0), n_boot=500)
    null = run_verdict(_synth_extracted(effect_pip=0.0), n_boot=500)
    s = strong["results"][0]
    n = null["results"][0]
    assert s["leg_a"]["p_combo"] < 0.05, f"strong p={s['leg_a']['p_combo']}"
    assert n["leg_a"]["p_combo"] > 0.05, f"null p={n['leg_a']['p_combo']}"
    assert n["classification"] in ("C5", "C2"), n["classification"]
    # 決定論: 同 seed 再実行で p 一致
    strong2 = run_verdict(_synth_extracted(effect_pip=25.0), n_boot=500)
    assert (strong2["results"][0]["leg_a"]["p_boot"]
            == s["leg_a"]["p_boot"]), "seed determinism broken"
    # OOS 窓ガード: oos_events は窓外を返さない
    cal = {"FOMC": ["2023-12-13T19:00:00+00:00", "2024-01-31T19:00:00+00:00",
                    "2026-07-29T18:00:00+00:00"]}
    evs = oos_events(cal, "FOMC")
    assert len(evs) == 1 and evs[0].year == 2024
    print(f"self-test OK: strong p={s['leg_a']['p_combo']} cls="
          f"{s['classification']} / null p={n['leg_a']['p_combo']} cls="
          f"{n['classification']} / verdicts: {strong['verdict']}/"
          f"{null['verdict']}")
    return 0


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    mode = argv[0] if argv else "self-test"
    if mode == "self-test":
        return self_test()
    if mode == "extract":
        return extract()
    if mode == "verdict":
        return verdict()
    print(f"unknown mode: {mode} (use: self-test | extract | verdict)",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
