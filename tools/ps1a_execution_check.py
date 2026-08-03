#!/usr/bin/env python3
"""P-S1(a) 執行条件判定 — sweep_reversion_eurgbp_late の凍結文言リプレイ。

user 条件付き承認 (2026-07-24、決裁パケット冒頭決裁記録) の執行条件を
機械的に再現する dry-run 判定器。live には一切触れない (read-only)。

凍結文言 (一次ソース):
  knowledge-base/wiki/decisions/sweep-reversion-ps1a-decision-packet-DRAFT.md
  - 執行条件: unique バー N>=10 到達 ∧ spaced EV>0 → Option B (§3.3 単一 PR)
  - spaced EV<=0 → Option C (retire)。両基準 (unique/spaced) で EV 符号が
    割れた場合は user 再決裁 (§6-2)
  - retire 期日分岐 (T8 DEFER): 2026-09-30 に unique N<5 → retire (R2)
  - 計数: unique = dedup_violation != 1 (§1.4、registry count_basis="unique")
  - spaced = unique に 12-bar (12x15m=3h) min-spacing を entry_time 昇順で適用
    (§7)。境界は研究 grid `dedup_indices(gap=12)` の `i - keep[-1] >= gap` と
    同一 = ちょうど 3h 離れていれば keep (tools/research_sweep_reversion_grid_12y.py L76)
  - データソース: 本番 API /api/demo/trades mode=daytrade_eurgbp 全ページ (§1)。
    since は registry t8-sweep-defer-decision の 2026-07-03 (rescue 開始) を使う —
    パケット §7 の date_from=2026-07-01 とは初発火が 07-06 のため結果同値
    (食い違い記録: 2026-07-31 準備セッション、両者を突合し行集合一致を確認済み)

設計原則 (lessons 準拠):
- モジュールトップの副作用なし (import しても network/env 変更なし)
- 判定ロジックは純関数 — テストはデータ注入で行う (tests/test_ps1a_execution_check.py)
- データ取得は tools/prereg_trigger_watch.fetch_trades_window を再利用
  (pagination 全量 + fail-loud、§1.5 undercount 修正と同一経路)

使用:
    python3 tools/ps1a_execution_check.py           # Markdown dry-run 出力
    python3 tools/ps1a_execution_check.py --json    # JSON 出力
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ENTRY_TYPE = "sweep_reversion_eurgbp_late"
MODE = "daytrade_eurgbp"
SINCE = "2026-07-03"            # registry t8-sweep-defer-decision.since
N_DECIDE = 10                   # unique N>=10 で判定実施
N_FLOOR = 5                     # 期日時 N<5 で retire (R2)
RETIRE_DEADLINE = "2026-09-30"
SPACING_SEC = 12 * 900          # 12 bars x 15m = 3h (research grid DEDUP_GAP=12)
ZERO_FIRE_FORENSIC_DAYS = 30    # LOCK Withdrawal trigger 5: 30日 fire 0 → forensic
APP_BASE_DEFAULT = "https://fx-ai-trader.onrender.com"

VERDICT_WAITING = "WAITING"
VERDICT_OPTION_B = "OPTION_B_EXECUTE"
VERDICT_OPTION_C = "OPTION_C_RETIRE"
VERDICT_USER_REDECISION = "USER_REDECISION_SIGN_SPLIT"
VERDICT_RETIRE_DEADLINE = "RETIRE_R2_DEADLINE"
VERDICT_UNAVAILABLE = "DATA_UNAVAILABLE"


# ── 純関数 (テスト対象) ──────────────────────────────────────────────

def _parse_entry_time(value) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def select_rows(trades: list) -> list[dict]:
    """entry_type 一致行を entry_time 昇順で返す (row 基準)。

    entry_time 不正の行は fail-loud で除外せず ValueError にする —
    silent drop は §1.5 undercount と同型の再発になるため。
    """
    rows = [t for t in trades if t.get("entry_type") == ENTRY_TYPE]
    for t in rows:
        if _parse_entry_time(t.get("entry_time")) is None:
            raise ValueError(
                f"unparseable entry_time in trade id={t.get('id')!r}: "
                f"{t.get('entry_time')!r}")
    return sorted(rows, key=lambda t: _parse_entry_time(t.get("entry_time")))


def unique_rows(rows: list[dict]) -> list[dict]:
    """unique バー基準 = dedup_violation != 1 (§1.4 確定の estimand 忠実計数)。"""
    return [t for t in rows if (t.get("dedup_violation") or 0) != 1]


def spaced_rows(uniq: list[dict]) -> list[dict]:
    """spaced 基準 = unique に 12-bar min-spacing を entry_time 昇順で適用。

    研究 grid dedup_indices と同一意味論: 先頭 keep、以後は最終 keep から
    `>= SPACING_SEC` 離れた行のみ keep (ちょうど 3h は keep)。
    """
    kept: list[dict] = []
    last_ts: datetime | None = None
    for t in uniq:
        ts = _parse_entry_time(t.get("entry_time"))
        if last_ts is None or (ts - last_ts).total_seconds() >= SPACING_SEC:
            kept.append(t)
            last_ts = ts
    return kept


def _basis_stats(rows: list[dict]) -> dict:
    n = len(rows)
    pnls = [float(t.get("pnl_pips") or 0.0) for t in rows]
    total = sum(pnls)
    wins = sum(1 for p in pnls if p > 0)
    return {
        "n": n,
        "sum_pnl_pips": round(total, 2),
        "ev_pips": round(total / n, 4) if n else None,
        "wr": round(wins / n, 4) if n else None,
    }


def evaluate(trades: list, today: str) -> dict:
    """凍結判定規則の完全リプレイ。trades = API 全行 (mode 絞り込み済み)。"""
    rows = select_rows(trades)
    uniq = unique_rows(rows)
    spaced = spaced_rows(uniq)
    stats = {
        "row": _basis_stats(rows),
        "unique": _basis_stats(uniq),
        "spaced": _basis_stats(spaced),
    }
    n_unique = stats["unique"]["n"]
    ev_spaced = stats["spaced"]["ev_pips"]
    ev_unique = stats["unique"]["ev_pips"]

    last_fire = rows[-1].get("entry_time") if rows else None
    days_since_last_fire = None
    if last_fire:
        lf = _parse_entry_time(last_fire)
        td = datetime.fromisoformat(today).replace(tzinfo=timezone.utc)
        days_since_last_fire = round((td - lf).total_seconds() / 86400.0, 1)

    if n_unique >= N_DECIDE:
        # 執行条件到達 — 凍結判定規則 §6-2
        spaced_pos = (ev_spaced or 0.0) > 0
        unique_pos = (ev_unique or 0.0) > 0
        if spaced_pos != unique_pos:
            verdict = VERDICT_USER_REDECISION
            detail = (f"unique N={n_unique}>= {N_DECIDE} 到達だが EV 符号割れ "
                      f"(spaced {ev_spaced:+.2f} / unique {ev_unique:+.2f}) — "
                      f"§6-2 により user 再決裁")
        elif spaced_pos:
            verdict = VERDICT_OPTION_B
            detail = (f"unique N={n_unique}>={N_DECIDE} ∧ spaced EV="
                      f"{ev_spaced:+.2f}p>0 — Option B 執行条件成立 "
                      f"(runbook: sweep-reversion-ps1a-execution-runbook-2026-07-31)")
        else:
            verdict = VERDICT_OPTION_C
            detail = (f"unique N={n_unique}>={N_DECIDE} ∧ spaced EV="
                      f"{ev_spaced:+.2f}p<=0 — Option C (retire、T8 DEFER 機械規定)")
    elif today > RETIRE_DEADLINE and n_unique < N_FLOOR:
        verdict = VERDICT_RETIRE_DEADLINE
        detail = (f"期日 {RETIRE_DEADLINE} 超過かつ unique N={n_unique}<{N_FLOOR} "
                  f"— retire 執行期日 (R2)")
    else:
        verdict = VERDICT_WAITING
        detail = (f"unique N={n_unique}/{N_DECIDE} — トリガ待ち "
                  f"(retire 判定: {RETIRE_DEADLINE} に N<{N_FLOOR})")

    zero_fire_alert = (days_since_last_fire is not None
                       and days_since_last_fire >= ZERO_FIRE_FORENSIC_DAYS)
    return {
        "verdict": verdict,
        "detail": detail,
        "stats": stats,
        "last_fire": last_fire,
        "days_since_last_fire": days_since_last_fire,
        "zero_fire_forensic_alert": zero_fire_alert,
        "frozen_condition": (
            f"unique N>={N_DECIDE} AND spaced EV>0 -> Option B / "
            f"spaced EV<=0 -> Option C / sign split -> user redecision / "
            f"{RETIRE_DEADLINE} N<{N_FLOOR} -> retire R2"),
        "today": today,
    }


def to_markdown(res: dict) -> str:
    lines = [
        "## P-S1(a) 執行条件 dry-run — sweep_reversion_eurgbp_late",
        f"- **verdict: {res['verdict']}** — {res['detail']}",
        f"- 凍結条件: {res['frozen_condition']}",
        "",
        "| 基準 | N | ΣPnL(p) | EV(p/t) | WR |",
        "|---|---|---|---|---|",
    ]
    for name in ("row", "unique", "spaced"):
        s = res["stats"][name]
        ev = f"{s['ev_pips']:+.2f}" if s["ev_pips"] is not None else "—"
        wr = f"{s['wr']:.1%}" if s["wr"] is not None else "—"
        lines.append(f"| {name} | {s['n']} | {s['sum_pnl_pips']:+.1f} | {ev} | {wr} |")
    lines.append("")
    lines.append(f"- 最終発火: {res['last_fire']} "
                 f"({res['days_since_last_fire']} 日前)")
    if res["zero_fire_forensic_alert"]:
        lines.append(
            f"- ⚠️ **fire 0 が {ZERO_FIRE_FORENSIC_DAYS} 日以上継続** — LOCK "
            f"Withdrawal trigger 5 (発火経路の故障調査、kill でなく forensic)")
    return "\n".join(lines)


# ── データ取得 (CLI 実行時のみ) ──────────────────────────────────────

def fetch_and_evaluate(app_base: str, today: str | None = None) -> dict:
    if str(ROOT) not in sys.path:  # 直接実行時 (python3 tools/...) の package 解決
        sys.path.insert(0, str(ROOT))
    from tools.prereg_trigger_watch import fetch_trades_window
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    trades = fetch_trades_window(SINCE, app_base, mode=MODE)
    if trades is None:
        return {"verdict": VERDICT_UNAVAILABLE,
                "detail": "trade API unavailable (pagination fail-loud)",
                "today": today}
    return evaluate(trades, today)


def main() -> int:
    ap = argparse.ArgumentParser(description="P-S1(a) execution-condition dry-run")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--app-base", default=APP_BASE_DEFAULT)
    ap.add_argument("--today", default=None, help="判定基準日 YYYY-MM-DD (test 用)")
    args = ap.parse_args()
    res = fetch_and_evaluate(args.app_base, today=args.today)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        if res["verdict"] == VERDICT_UNAVAILABLE:
            print(f"## P-S1(a) dry-run: {res['verdict']} — {res['detail']}")
        else:
            print(to_markdown(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
