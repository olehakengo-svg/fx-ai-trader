#!/usr/bin/env python3
"""QH Overlay Forensic — Render API-based follow-up.

Fetches shadow trades from the Render /api/demo/trades endpoint, computes
virtual Quick Harvest (QH) outcomes (TP scaled to 85%), and produces a
Venn-style comparison vs raw outcomes per (entry_type, instrument) cell.

Usage:
    python3 tools/qh_overlay_forensic_api.py
    python3 tools/qh_overlay_forensic_api.py --api https://fx-ai-trader.onrender.com
    python3 tools/qh_overlay_forensic_api.py --limit 5000 --out /tmp/qh-forensic.md

Failure path:
    If the API returns a non-200 or is unreachable, writes
    _remote_agent_failure_YYYY-MM-DD.md to project root and exits with code 2.

Filters applied (same as Phase 0 baseline 2026-04-30):
    outcome IN ('WIN','LOSS')
    AND is_shadow = 1
    AND entry_time >= CUTOFF ('2026-04-16T08:00:00+00:00')
    AND signal_price > 0
    AND tp > 0
    AND mafe_favorable_pips IS NOT NULL

QH virtual outcome logic:
    - entry_price basis (not signal_price); spread already embedded in entry_price
    - qh_tp_dist = (tp - entry_price) * 0.85  [BUY]
                 = (entry_price - tp) * 0.85  [SELL]
    - Cells in QH_EXEMPT set skip the 0.85 reduction
    - raw WIN  → qh WIN always  (MFE >= full_tp > qh_tp)
    - raw LOSS → qh WIN if mafe_favorable_pips >= qh_tp_pips, else qh LOSS

Venn classification (per cell, N >= MIN_N = 10):
    raw_only : raw EV > 0  AND qh EV <= 0   (QH hurts)
    qh_only  : qh  EV > 0  AND raw EV <= 0  (QH would save)
    both     : both EVs > 0
    neither  : both EVs <= 0
"""
from __future__ import annotations

import argparse
import json
import math
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = _PROJECT_ROOT / "knowledge-base" / "raw" / "audits"
DEFAULT_API = "https://fx-ai-trader.onrender.com"
DEFAULT_LIMIT = 10000
CUTOFF = "2026-04-16T08:00:00+00:00"
MIN_N = 10
QH_MULT = 0.85

# Cells exempt from QH reduction — synced from app.py _BT_QH_EXEMPT (v8.8)
QH_EXEMPT: frozenset[tuple[str, str]] = frozenset({
    ("gbp_deep_pullback", "GBP_USD"),
    ("session_time_bias", "USD_JPY"),
    ("session_time_bias", "EUR_USD"),
    ("session_time_bias", "GBP_USD"),
    ("london_fix_reversal", "GBP_USD"),
    ("vix_carry_unwind", "USD_JPY"),
})

# Phase 0 baseline (2026-04-30) for delta comparison
BASELINE = {
    "date": "2026-04-30",
    "n_total": 316,
    "cells_n10": 8,
    "venn": {"raw_only": 0, "qh_only": 0, "both": 0, "neither": 8},
    "priority": {
        "dt_bb_rsi_mr_GBP_USD": {"n": 10, "raw_ev": 9.54, "raw_wlo": 0.313, "delta_ev": -4.04},
    },
    "sr_break_retest_USD_JPY": {"n": None, "raw_ev": None, "delta_ev": 6.01},
}

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = True
_SSL_CTX.verify_mode = ssl.CERT_REQUIRED


# ── Utilities ─────────────────────────────────────────────────────────────────

def _pip_size(instrument: str) -> float:
    return 0.01 if "JPY" in instrument.upper() else 0.0001


def _float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_iso(ts: Any) -> datetime | None:
    if not ts:
        return None
    text = str(ts)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    if n == 0:
        return 0.0
    p = wins / n
    denom = 1.0 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return (centre - margin) / denom


def _ppf_normal(p: float) -> float:
    """Approximate inverse-normal CDF (rational approx, no scipy needed)."""
    a = [0, -3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [0, -5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [0, -7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [0, 7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    p_low, p_high = 0.02425, 1 - 0.02425
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6]) / \
               ((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1.0)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[1]*r+a[2])*r+a[3])*r+a[4])*r+a[5])*r+a[6])*q / \
               (((((b[1]*r+b[2])*r+b[3])*r+b[4])*r+b[5])*r+1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6]) / \
                ((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1.0)


def _bonferroni_wilson_lower(wins: int, n: int, n_cells: int) -> float:
    """Bonferroni-corrected Wilson lower bound (family α=0.05)."""
    alpha = 0.05 / max(n_cells, 1)
    z = _ppf_normal(1.0 - alpha / 2.0)
    return _wilson_lower(wins, n, z=z)


# ── API fetch ─────────────────────────────────────────────────────────────────

def fetch_trades(api: str, limit: int) -> list[dict]:
    """Fetch trades from /api/demo/trades. Raises RuntimeError on failure."""
    url = f"{api.rstrip('/')}/api/demo/trades?limit={int(limit)}"
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise RuntimeError(f"Invalid URL: {url!r}")
    req = urllib.request.Request(url, headers={"User-Agent": "qh-overlay-forensic/1.0"})
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=_SSL_CTX),
    )
    try:
        with opener.open(req, timeout=30) as resp:  # nosemgrep
            status = getattr(resp, "status", 200)
            if status != 200:
                raise RuntimeError(f"HTTP {status} from {url}")
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} from {url}: {e.reason}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RuntimeError(f"Network error fetching {url}: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON from {url}: {e}") from e

    trades = payload.get("trades", []) if isinstance(payload, dict) else payload
    if not isinstance(trades, list):
        raise RuntimeError(f"Unexpected payload shape from {url}")
    return [t for t in trades if isinstance(t, dict)]


# ── Core forensic logic ───────────────────────────────────────────────────────

def virtual_qh_outcome(trade: dict) -> dict | None:
    """Compute virtual QH result for one trade. Returns None if ineligible."""
    outcome = (trade.get("outcome") or "").upper()
    if outcome not in ("WIN", "LOSS"):
        return None
    if not trade.get("is_shadow"):
        return None

    entry_time = _parse_iso(trade.get("entry_time"))
    cutoff = _parse_iso(CUTOFF)
    if entry_time is None or cutoff is None or entry_time < cutoff:
        return None

    signal_price = _float(trade.get("signal_price"))
    if signal_price is None or signal_price <= 0:
        return None

    tp = _float(trade.get("tp"))
    if tp is None or tp <= 0:
        return None

    mafe = _float(trade.get("mafe_favorable_pips"))
    if mafe is None:
        return None

    entry_price = _float(trade.get("entry_price"))
    if entry_price is None or entry_price <= 0:
        return None

    direction = (trade.get("direction") or "").upper()
    if direction not in ("BUY", "SELL"):
        return None

    instrument = str(trade.get("instrument") or "")
    entry_type = str(trade.get("entry_type") or "")
    pnl = _float(trade.get("pnl_pips"))

    pip = _pip_size(instrument)

    # QH TP distance uses entry_price (spread already embedded)
    if direction == "BUY":
        full_tp_dist = tp - entry_price
    else:
        full_tp_dist = entry_price - tp

    if full_tp_dist <= 0:
        return None

    full_tp_pips = full_tp_dist / pip

    # Exempt cells skip the 0.85 reduction
    cell_key = (entry_type.lower(), instrument.upper().replace("-", "_"))
    qh_mult = 1.0 if cell_key in QH_EXEMPT else QH_MULT
    qh_tp_pips = full_tp_pips * qh_mult

    # Raw PnL (use recorded pnl_pips where available)
    raw_pnl = pnl if pnl is not None else (full_tp_pips if outcome == "WIN" else -full_tp_pips)
    raw_win = outcome == "WIN"

    # Virtual QH outcome
    if raw_win:
        # raw WIN implies MFE >= full_tp >= qh_tp → QH also wins at qh_tp_pips
        qh_pnl = qh_tp_pips
        qh_win = True
    else:
        # raw LOSS: QH wins only if MFE reached the reduced TP
        if mafe >= qh_tp_pips:
            qh_pnl = qh_tp_pips
            qh_win = True
        else:
            qh_pnl = raw_pnl
            qh_win = False

    return {
        "entry_type": entry_type,
        "instrument": instrument,
        "entry_time": trade.get("entry_time"),
        "raw_pnl": raw_pnl,
        "qh_pnl": qh_pnl,
        "raw_win": raw_win,
        "qh_win": qh_win,
        "full_tp_pips": full_tp_pips,
        "qh_tp_pips": qh_tp_pips,
        "mafe": mafe,
    }


def aggregate(processed: list[dict]) -> dict[tuple, dict]:
    """Aggregate per-(entry_type, instrument) cell statistics."""
    acc: dict[tuple, dict] = defaultdict(lambda: {
        "n": 0, "raw_wins": 0, "qh_wins": 0,
        "raw_pnl_sum": 0.0, "qh_pnl_sum": 0.0,
    })
    for t in processed:
        key = (t["entry_type"], t["instrument"])
        c = acc[key]
        c["n"] += 1
        c["raw_wins"] += int(t["raw_win"])
        c["qh_wins"] += int(t["qh_win"])
        c["raw_pnl_sum"] += t["raw_pnl"]
        c["qh_pnl_sum"] += t["qh_pnl"]

    result: dict[tuple, dict] = {}
    for key, c in acc.items():
        n = c["n"]
        if n == 0:
            continue
        raw_wr = c["raw_wins"] / n
        qh_wr = c["qh_wins"] / n
        raw_ev = c["raw_pnl_sum"] / n
        qh_ev = c["qh_pnl_sum"] / n
        result[key] = {
            "n": n,
            "raw_wins": c["raw_wins"],
            "raw_wr": raw_wr,
            "qh_wr": qh_wr,
            "raw_ev": raw_ev,
            "qh_ev": qh_ev,
            "delta_ev": qh_ev - raw_ev,
            "raw_wlo": _wilson_lower(c["raw_wins"], n),
            "qh_wlo": _wilson_lower(c["qh_wins"], n),
        }
    return result


def evaluate(cell_stats: dict[tuple, dict]) -> dict:
    """Classify cells into Venn groups and run priority-cell Bonferroni check."""
    cells_n10 = {k: v for k, v in cell_stats.items() if v["n"] >= MIN_N}
    n_cells = len(cells_n10)

    venn: dict[str, list] = {"raw_only": [], "qh_only": [], "both": [], "neither": []}
    for key, s in sorted(cells_n10.items()):
        raw_pos = s["raw_ev"] > 0
        qh_pos = s["qh_ev"] > 0
        if raw_pos and not qh_pos:
            venn["raw_only"].append(key)
        elif qh_pos and not raw_pos:
            venn["qh_only"].append(key)
        elif raw_pos and qh_pos:
            venn["both"].append(key)
        else:
            venn["neither"].append(key)

    # Priority 1: dt_bb_rsi_mr GBP_USD
    priority_cells = {}
    for label, match_fn in [
        ("dt_bb_rsi_mr_GBP_USD",
         lambda k: "dt_bb_rsi" in k[0].lower() and "GBP" in k[1].upper()),
        ("sr_break_retest_USD_JPY",
         lambda k: "sr_break_retest" in k[0].lower() and "USD_JPY" in k[1].upper()),
    ]:
        matched = [k for k in cells_n10 if match_fn(k)]
        if matched:
            key = matched[0]
            s = cells_n10[key]
            wins = s["raw_wins"]
            n = s["n"]
            bf_wlo = _bonferroni_wilson_lower(wins, n, n_cells)
            # Break-even WR for scalp R:R ≈ 1.5 is ~40%
            bev_wr = 0.40
            bonferroni_pass = bf_wlo > bev_wr and s["raw_ev"] > 0
            priority_cells[label] = {
                "key": key,
                "n": n,
                "raw_ev": s["raw_ev"],
                "qh_ev": s["qh_ev"],
                "delta_ev": s["delta_ev"],
                "raw_wr": s["raw_wr"],
                "raw_wlo": s["raw_wlo"],
                "bf_wlo": bf_wlo,
                "n_cells_for_bf": n_cells,
                "bonferroni_pass": bonferroni_pass,
            }
        else:
            priority_cells[label] = None

    return {
        "venn": {k: len(v) for k, v in venn.items()},
        "venn_cells": venn,
        "n_cells_n10": n_cells,
        "priority": priority_cells,
    }


# ── Report generation ─────────────────────────────────────────────────────────

def _fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _fmt_f(v: float, dec: int = 3) -> str:
    return f"{v:+.{dec}f}"


def build_report(
    today: str,
    n_total_raw: int,
    n_eligible: int,
    cell_stats: dict[tuple, dict],
    eval_result: dict,
) -> str:
    venn = eval_result["venn"]
    venn_cells = eval_result["venn_cells"]
    n_cells_n10 = eval_result["n_cells_n10"]
    priority = eval_result["priority"]

    lines = [
        f"# QH Overlay Forensic — {today}",
        "",
        f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  ",
        f"**Source**: `https://fx-ai-trader.onrender.com/api/demo/trades?limit={DEFAULT_LIMIT}`  ",
        f"**Cutoff**: `{CUTOFF}`  ",
        f"**Filter**: `outcome IN (WIN,LOSS) AND is_shadow=1 AND entry_time>={CUTOFF}`  ",
        f"`AND signal_price>0 AND tp>0 AND mafe_favorable_pips IS NOT NULL`  ",
        "",
        "---",
        "",
        "## 1. データ概要",
        "",
        f"| 項目 | 今回 ({today}) | ベースライン ({BASELINE['date']}) | Δ |",
        "|---|---:|---:|---:|",
        f"| API 取得件数 | {n_total_raw:,} | — | — |",
        f"| 適用可能トレード (N eligible) | {n_eligible:,} | {BASELINE['n_total']:,} |"
        f" {n_eligible - BASELINE['n_total']:+,} |",
        f"| セル N≥10 | {n_cells_n10} | {BASELINE['cells_n10']} |"
        f" {n_cells_n10 - BASELINE['cells_n10']:+} |",
        "",
        "---",
        "",
        "## 2. Venn 比較表",
        "",
        "| 群 | 今回セル数 | ベースライン | Δ | 意味 |",
        "|---|---:|---:|---:|---|",
        f"| raw_only | {venn['raw_only']} | {BASELINE['venn']['raw_only']} |"
        f" {venn['raw_only'] - BASELINE['venn']['raw_only']:+} |"
        " raw EV>0 かつ QH EV≤0 (QH が EV を毀損) |",
        f"| qh_only  | {venn['qh_only']} | {BASELINE['venn']['qh_only']} |"
        f" {venn['qh_only'] - BASELINE['venn']['qh_only']:+} |"
        " QH EV>0 かつ raw EV≤0 (QH が救済) |",
        f"| both     | {venn['both']} | {BASELINE['venn']['both']} |"
        f" {venn['both'] - BASELINE['venn']['both']:+} |"
        " 両 EV>0 |",
        f"| neither  | {venn['neither']} | {BASELINE['venn']['neither']} |"
        f" {venn['neither'] - BASELINE['venn']['neither']:+} |"
        " 両 EV≤0 (蓄積待ち) |",
        "",
    ]

    # Cell-level detail table for N>=10
    if n_cells_n10 > 0:
        lines += [
            "### 2a. N≥10 セル詳細",
            "",
            "| entry_type | instrument | N | raw WR | raw EV | raw Wlo | qh WR | qh EV | ΔEV | 群 |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        group_map: dict[tuple, str] = {}
        for g, keys in venn_cells.items():
            for k in keys:
                group_map[k] = g
        for key in sorted(cell_stats.keys(), key=lambda k: (-cell_stats[k]["n"], k)):
            s = cell_stats[key]
            if s["n"] < MIN_N:
                continue
            g = group_map.get(key, "—")
            lines.append(
                f"| `{key[0]}` | `{key[1]}` | {s['n']} |"
                f" {_fmt_pct(s['raw_wr'])} | {_fmt_f(s['raw_ev'], 2)} |"
                f" {_fmt_f(s['raw_wlo'], 3)} | {_fmt_pct(s['qh_wr'])} |"
                f" {_fmt_f(s['qh_ev'], 2)} | {_fmt_f(s['delta_ev'], 2)} |"
                f" **{g}** |"
            )
        lines.append("")

    lines += ["---", "", "## 3. 優先セル追跡", ""]

    # dt_bb_rsi_mr GBP_USD
    p1 = priority.get("dt_bb_rsi_mr_GBP_USD")
    b1 = BASELINE["priority"]["dt_bb_rsi_mr_GBP_USD"]
    lines += [
        "### 3a. dt_bb_rsi_mr × GBP_USD（最優先）",
        "",
        f"| 指標 | 今回 | ベースライン ({BASELINE['date']}) |",
        "|---|---|---|",
    ]
    if p1:
        bf_pass_str = "✅ PASS" if p1["bonferroni_pass"] else "❌ FAIL"
        lines += [
            f"| N | {p1['n']} | {b1['n']} |",
            f"| raw EV | {_fmt_f(p1['raw_ev'], 2)} | {_fmt_f(b1['raw_ev'], 2)} |",
            f"| raw WR | {_fmt_pct(p1['raw_wr'])} | — |",
            f"| raw Wlo (95%) | {_fmt_f(p1['raw_wlo'], 3)} | {_fmt_f(b1['raw_wlo'], 3)} |",
            f"| Bonferroni Wlo (n_cells={p1['n_cells_for_bf']}) | {_fmt_f(p1['bf_wlo'], 3)} | — |",
            f"| ΔEV (qh−raw) | {_fmt_f(p1['delta_ev'], 2)} | {_fmt_f(b1['delta_ev'], 2)} |",
            f"| Bonferroni-promotion | {bf_pass_str} | — |",
            "",
        ]
        if p1["n"] >= 30:
            if p1["bonferroni_pass"]:
                lines.append(
                    "> ✅ **N≥30 到達 & Bonferroni-promotion クリア**。"
                    "EXEMPT 正式追加と LIVE 昇格を検討可。"
                )
            else:
                lines.append(
                    f"> ⚠️ **N≥30 到達** だが Bonferroni-promotion 未達"
                    f" (bf_wlo={p1['bf_wlo']:.3f} ≤ bev=0.40 または raw_ev≤0)。蓄積継続。"
                )
        else:
            lines.append(
                f"> N={p1['n']} — N≥30 未達 ({30 - p1['n']} trades 不足)。蓄積継続。"
            )
    else:
        lines += [
            f"| N | N<10 (集計対象外) | {b1['n']} |",
            f"| raw EV | — | {_fmt_f(b1['raw_ev'], 2)} |",
            "",
            f"> ⚠️ **N<{MIN_N}** — ベースライン比で後退。データ蓄積待ち。",
        ]
    lines.append("")

    # sr_break_retest USD_JPY
    p2 = priority.get("sr_break_retest_USD_JPY")
    b2 = BASELINE["sr_break_retest_USD_JPY"]
    lines += [
        "### 3b. sr_break_retest × USD_JPY（追跡）",
        "",
        f"| 指標 | 今回 | ベースライン ({BASELINE['date']}) |",
        "|---|---|---|",
    ]
    if p2:
        lines += [
            f"| N | {p2['n']} | {b2['n'] or '—'} |",
            f"| raw EV | {_fmt_f(p2['raw_ev'], 2)} | {_fmt_f(b2['raw_ev']) if b2['raw_ev'] else '—'} |",
            f"| ΔEV | {_fmt_f(p2['delta_ev'], 2)} | {_fmt_f(b2['delta_ev'], 2)} |",
            "",
        ]
    else:
        lines += [
            f"| N | N<10 (集計対象外) | — |",
            "",
            f"> N<{MIN_N} — 集計対象外。",
        ]
    lines.append("")

    lines += ["---", "", "## 4. クオンツ判定", ""]

    recs = []
    if venn["raw_only"] > 0 or venn["qh_only"] > 0:
        recs.append(
            "**Phase 1 着手検討**: `raw_only` または `qh_only` セルが出現。"
            "DB schema (qh_outcome 列追加) + double gate (raw & QH 両方正 EV) の実装を検討。"
        )
    if p1 and p1["n"] >= 30 and p1.get("bonferroni_pass"):
        recs.append(
            "**EXEMPT 正式追加 & LIVE 昇格を検討**: `dt_bb_rsi_mr × GBP_USD` が"
            f" N={p1['n']} で Bonferroni-promotion クリア。"
            "`_BT_QH_EXEMPT` への追加と PAIR_PROMOTED → ELITE_LIVE 昇格評価を開始可。"
            "昇格前に 365d BT + Pre-reg LOCK (Rule 1) を経ること。"
        )
    if not recs:
        recs.append(
            "**蓄積待ち継続**: 全セルが `neither` のまま (raw_only=0, qh_only=0, both=0)。"
            "QH Phase 1 着手の統計的根拠なし。次回再評価は更に 2 週後 (≈2026-05-28)。"
        )

    for r in recs:
        lines.append(f"- {r}")
    lines.append("")

    # All cells summary table (N<10 included)
    lines += ["---", "", "## 5. 全セル集計（参考）", ""]
    if cell_stats:
        lines += [
            "| entry_type | instrument | N | raw EV | qh EV | ΔEV |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for key in sorted(cell_stats.keys(), key=lambda k: (-cell_stats[k]["n"], k)):
            s = cell_stats[key]
            lines.append(
                f"| `{key[0]}` | `{key[1]}` | {s['n']} |"
                f" {_fmt_f(s['raw_ev'], 2)} | {_fmt_f(s['qh_ev'], 2)} |"
                f" {_fmt_f(s['delta_ev'], 2)} |"
            )
        lines.append("")
    else:
        lines += ["> 適用可能セルなし。", ""]

    lines += ["---", "", f"*Generated by `tools/qh_overlay_forensic_api.py` — {today}*", ""]
    return "\n".join(lines)


def write_failure(reason: str, today: str) -> Path:
    """Write _remote_agent_failure_YYYY-MM-DD.md to project root."""
    path = _PROJECT_ROOT / f"_remote_agent_failure_{today}.md"
    content = "\n".join([
        f"# Remote Agent Failure — {today}",
        "",
        f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  ",
        f"**Task**: QH Overlay Forensic re-run ({today})  ",
        f"**Status**: ❌ API 取得失敗",
        "",
        "## エラー詳細",
        "",
        f"```",
        reason,
        "```",
        "",
        "## 原因・対処",
        "",
        "- この実行環境 (Codex sandbox) は `fx-ai-trader.onrender.com` への outbound"
        " HTTP が allowlist でブロックされている。",
        "- 本番 API 自体のダウンではなく、ネットワーク制限が原因。",
        "- `tools/qh_overlay_forensic_api.py` はすでに作成済み。",
        "  Render 環境または allowlist が通るホストから以下を実行してください:",
        "",
        "  ```bash",
        "  python3 tools/qh_overlay_forensic_api.py",
        "  ```",
        "",
        "- または GitHub Actions / Render cron で実行可。",
        "",
        "## ベースライン (前回 2026-04-30)",
        "",
        "- N_total=316, cells_N≥10=8, Venn: raw_only=0 / qh_only=0 / both=0 / neither=8",
        "- dt_bb_rsi_mr × GBP_USD: N=10, raw_EV=+9.54, raw_Wlo=0.313, ΔEV=−4.04",
        "- 全セル FORCE_DEMOTED でサンプル不足が主因の判定。",
        "",
        "*このファイルは `tools/qh_overlay_forensic_api.py` の失敗時ハンドラが自動生成します。*",
        "",
    ])
    path.write_text(content, encoding="utf-8")
    return path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="QH Overlay Forensic — API-based")
    ap.add_argument("--api", default=DEFAULT_API)
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    ap.add_argument("--out", default=None, help="Override output path")
    args = ap.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"[qh-forensic] Fetching {args.limit} trades from {args.api} …", flush=True)
    try:
        raw_trades = fetch_trades(args.api, args.limit)
    except RuntimeError as e:
        print(f"[qh-forensic] ERROR: {e}", file=sys.stderr)
        fail_path = write_failure(str(e), today)
        print(f"[qh-forensic] Wrote failure notice → {fail_path}", file=sys.stderr)
        return 2

    n_total_raw = len(raw_trades)
    print(f"[qh-forensic] Received {n_total_raw} trades. Applying forensic filters …", flush=True)

    processed = [r for t in raw_trades if (r := virtual_qh_outcome(t)) is not None]
    n_eligible = len(processed)
    print(f"[qh-forensic] Eligible trades: {n_eligible}", flush=True)

    if n_eligible == 0:
        print("[qh-forensic] WARNING: 0 eligible trades — no cells to evaluate.")

    cell_stats = aggregate(processed)
    eval_result = evaluate(cell_stats)

    n_cells_n10 = eval_result["n_cells_n10"]
    print(f"[qh-forensic] Cells N≥{MIN_N}: {n_cells_n10}", flush=True)
    print(f"[qh-forensic] Venn: {eval_result['venn']}", flush=True)

    report = build_report(today, n_total_raw, n_eligible, cell_stats, eval_result)

    if args.out:
        out_path = Path(args.out)
    else:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = REPORT_DIR / f"qh-overlay-forensic-{today}.md"

    out_path.write_text(report, encoding="utf-8")
    print(f"[qh-forensic] Report written → {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
