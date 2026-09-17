#!/usr/bin/env python3
"""P-S1(a) 執行条件判定 — sweep_reversion_eurgbp_late の凍結文言リプレイ。

⚠️ **2026-09-17 user 決裁で Option C (retire) 採択済み** — fetch/CLI 層は API を
叩かず恒久的に OPTION_C_RETIRED_USER を返す。以下の凍結文言と evaluate() の
判定ロジックは歴史記録として不変に保つ (根拠:
knowledge-base/wiki/decisions/ps1a-option-c-retire-2026-09-17.md)。

user 条件付き承認 (2026-07-24、決裁パケット冒頭決裁記録) の執行条件を
機械的に再現する dry-run 判定器。live には一切触れない (read-only)。

凍結文言 (一次ソース):
  knowledge-base/wiki/decisions/sweep-reversion-ps1a-decision-packet-DRAFT.md
  - 執行条件: unique バー N>=10 到達 ∧ spaced EV>0 → Option B (§3.3 単一 PR)
  - spaced EV<=0 → Option C (retire)。両基準 (unique/spaced) で EV 符号が
    割れた場合は user 再決裁 (§6-2)
  - retire 期日分岐 (T8 DEFER): 2026-10-28 に unique N<5 → retire (R2)。(旧 09-30 — 2026-08-17 user 決裁で計数器故障 28 日分を繰り延べ)
  - 計数: unique = dedup_violation != 1 (§1.4、registry count_basis="unique")
  - **EV の estimand (2026-09-16 監査で明文化)**: 凍結閾値 (+6.22 p/t) の出所は
    研究 grid の `net = Δprice/psize - SPREAD_PIP[EUR_GBP]` (=1.5p、往復1回控除)
    であり **net-of-spread**。一方 shadow 行の `pnl_pips` は
    `(exit_price - entry_price) * pip_mult` (modules/demo_db.py:1223) で、
    fill は mid (`entry_price == signal_price`、実測 10/10 で差 0.00p) =
    **gross-of-spread**。よって「spaced EV>0」を shadow の生 EV で評価すると
    estimand 不一致になる。本ツールは gross と net を併記し、符号が割れる間は
    USER_REDECISION_ESTIMAND を返して自動執行を止める
    (根拠: knowledge-base/wiki/analyses/ps1a-trigger-estimand-audit-2026-09-16.md)
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
# 2026-08-17 user 決裁 (zero-fire forensic §4-2): 計数器故障期間 (07-16〜08-12、
# gbp_asia rowless drop、PR #180 で修復) の 28 日分を繰り延べ 09-30 → 10-28。
RETIRE_DEADLINE = "2026-10-28"
SPACING_SEC = 12 * 900          # 12 bars x 15m = 3h (research grid DEDUP_GAP=12)
ZERO_FIRE_FORENSIC_DAYS = 30    # LOCK Withdrawal trigger 5: 30日 fire 0 → forensic
# 研究 grid tools/research_sweep_reversion_grid_12y.py SPREAD_PIP["EUR_GBP"]。
# 凍結閾値 +6.22 p/t はこの値を往復1回控除した net。
RESEARCH_SPREAD_PIP = 1.5
# pre-reg 反証チェック #2 の前提 (「実勢 1.5-3p、3.5p でも +4.22p」)。
PREREG_SPREAD_PREMISE_PIPS = 3.5
APP_BASE_DEFAULT = "https://fx-ai-trader.onrender.com"

VERDICT_WAITING = "WAITING"
VERDICT_OPTION_B = "OPTION_B_EXECUTE"
VERDICT_OPTION_C = "OPTION_C_RETIRE"
VERDICT_USER_REDECISION = "USER_REDECISION_SIGN_SPLIT"
VERDICT_USER_REDECISION_ESTIMAND = "USER_REDECISION_ESTIMAND"
VERDICT_RETIRE_DEADLINE = "RETIRE_R2_DEADLINE"
VERDICT_UNAVAILABLE = "DATA_UNAVAILABLE"

# 2026-09-17 user 決裁: estimand 監査 §7 の二択で (a) Option C = retire を採択。
# 以後、CLI/fetch 層は API を叩かず恒久的に本 verdict を返す (live 不触・報告のみ)。
# evaluate() は凍結文言の歴史リプレイとして不変に保つ (test pin 温存)。
# 根拠: knowledge-base/wiki/decisions/ps1a-option-c-retire-2026-09-17.md
RETIRED_ON = "2026-09-17"
VERDICT_RETIRED = "OPTION_C_RETIRED_USER"
RETIRED_DETAIL = (
    f"user 決裁 {RETIRED_ON} で Option C (retire) 採択 — 執行トリガは恒久終了。"
    "shadow rescue は残置 (4原則#3)。根拠 = net spaced EV −3.33p (gross +2.92p "
    "から符号反転) ∧ cap 救済集合空 (ps1a-option-c-retire-2026-09-17)")


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


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    v = sorted(values)
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2.0


def _basis_stats(rows: list[dict]) -> dict:
    """三基準の gross/net 統計。

    `pnl_pips` は mid fill の価格差 = **gross-of-spread** (header 参照)。
    凍結閾値の estimand に合わせるため往復摩擦を控除した net を併記する:

    - `net_ev_pips` (**primary**, 研究 parity): cost = (spread_entry + spread_exit)/2
      — 研究は mid 価格差から往復 spread を 1 回控除 (`- SPREAD_PIP`)。live で
      その 1 回分に相当するのは entry/exit の平均 (buy=ask / sell=bid で各片側)。
    - `net_ev_entry_only`: cost = spread_entry (zero-fire forensic #2 §6 の convention)
    - `net_ev_house_rt`: cost = spread_entry + spread_exit
      (friction-analysis.md の per-pair RT convention = 各レグ全幅)

    `spread_coverage` < 1.0 の基準は net を確定できない (= 執行可否を名乗れない)。
    """
    n = len(rows)
    pnls = [float(t.get("pnl_pips") or 0.0) for t in rows]
    s_ent = [float(t.get("spread_at_entry") or 0.0) for t in rows]
    s_exi = [float(t.get("spread_at_exit") or 0.0) for t in rows]
    total = sum(pnls)
    wins = sum(1 for p in pnls if p > 0)
    net_primary = [p - (a + b) / 2.0 for p, a, b in zip(pnls, s_ent, s_exi)]
    net_entry = [p - a for p, a in zip(pnls, s_ent)]
    net_house = [p - (a + b) for p, a, b in zip(pnls, s_ent, s_exi)]
    covered = sum(1 for a in s_ent if a > 0)

    def _ev(v: list[float]) -> float | None:
        return round(sum(v) / n, 4) if n else None

    return {
        "n": n,
        "sum_pnl_pips": round(total, 2),
        "ev_pips": _ev(pnls),
        "wr": round(wins / n, 4) if n else None,
        "net_ev_pips": _ev(net_primary),
        "net_sum_pnl_pips": round(sum(net_primary), 2) if n else None,
        "net_wr": (round(sum(1 for p in net_primary if p > 0) / n, 4)
                   if n else None),
        "net_ev_entry_only": _ev(net_entry),
        "net_ev_house_rt": _ev(net_house),
        "net_ev_research_assumption": (
            _ev([p - RESEARCH_SPREAD_PIP for p in pnls])),
        "spread_entry_mean": round(sum(s_ent) / n, 2) if n else None,
        "spread_entry_median": _median(s_ent),
        "spread_entry_min": min(s_ent) if n else None,
        "spread_entry_max": max(s_ent) if n else None,
        "spread_coverage": round(covered / n, 4) if n else None,
        "rows_within_prereg_spread_premise": sum(
            1 for a in s_ent if 0 < a <= PREREG_SPREAD_PREMISE_PIPS),
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

    net_spaced = stats["spaced"]["net_ev_pips"]
    net_unique = stats["unique"]["net_ev_pips"]
    spaced_cov = stats["spaced"]["spread_coverage"]

    if n_unique >= N_DECIDE:
        # 執行条件到達 — 凍結判定規則 §6-2
        spaced_pos = (ev_spaced or 0.0) > 0
        unique_pos = (ev_unique or 0.0) > 0
        net_spaced_pos = (net_spaced or 0.0) > 0
        if spaced_pos != unique_pos:
            verdict = VERDICT_USER_REDECISION
            detail = (f"unique N={n_unique}>= {N_DECIDE} 到達だが EV 符号割れ "
                      f"(spaced {ev_spaced:+.2f} / unique {ev_unique:+.2f}) — "
                      f"§6-2 により user 再決裁")
        elif spaced_pos and (spaced_cov or 0.0) < 1.0:
            # net を確定できない基準で Option B は名乗れない (fail-loud)。
            verdict = VERDICT_USER_REDECISION_ESTIMAND
            detail = (f"unique N={n_unique}>={N_DECIDE} ∧ gross spaced EV="
                      f"{ev_spaced:+.2f}p>0 だが spread 記録の被覆が "
                      f"{spaced_cov:.0%} — net EV を確定できないため執行不可 "
                      f"(estimand 未確定)")
        elif spaced_pos != net_spaced_pos:
            # 2026-09-16 監査: 凍結閾値は net、shadow の生 EV は gross。
            # 符号が割れている間は自動執行を止めて user 再決裁へ回す。
            verdict = VERDICT_USER_REDECISION_ESTIMAND
            detail = (
                f"unique N={n_unique}>={N_DECIDE} 到達、しかし gross/net で "
                f"EV 符号が割れる (gross spaced {ev_spaced:+.2f}p / "
                f"net spaced {net_spaced:+.2f}p、往復摩擦 "
                f"{stats['spaced']['spread_entry_mean']:.1f}p entry 平均) — "
                f"凍結閾値 +6.22p は net-of-spread 由来のため gross 単独で "
                f"Option B は執行不可。user 再決裁 "
                f"(ps1a-trigger-estimand-audit-2026-09-16)")
        elif spaced_pos:
            verdict = VERDICT_OPTION_B
            detail = (f"unique N={n_unique}>={N_DECIDE} ∧ spaced EV="
                      f"{ev_spaced:+.2f}p>0 (net {net_spaced:+.2f}p>0) — "
                      f"Option B 執行条件成立 "
                      f"(runbook: sweep-reversion-ps1a-execution-runbook-2026-07-31)")
        else:
            verdict = VERDICT_OPTION_C
            detail = (f"unique N={n_unique}>={N_DECIDE} ∧ spaced EV="
                      f"{ev_spaced:+.2f}p<=0 (net {net_spaced:+.2f}p) — "
                      f"Option C (retire、T8 DEFER 機械規定)")
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
        "estimand_note": (
            "凍結閾値 +6.22 p/t は研究 grid の net-of-spread "
            f"(SPREAD_PIP={RESEARCH_SPREAD_PIP}p 往復1回控除)。shadow の "
            "pnl_pips は mid fill の gross。gross/net で符号が割れる間は "
            "USER_REDECISION_ESTIMAND (自動執行しない)"),
        "today": today,
    }


def to_markdown(res: dict) -> str:
    lines = [
        "## P-S1(a) 執行条件 dry-run — sweep_reversion_eurgbp_late",
        f"- **verdict: {res['verdict']}** — {res['detail']}",
        f"- 凍結条件: {res['frozen_condition']}",
        "",
        "| 基準 | N | ΣPnL(p) | EV gross | WR gross | EV net | WR net | s_entry 平均 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name in ("row", "unique", "spaced"):
        s = res["stats"][name]
        def _f(key, fmt="{:+.2f}"):
            v = s.get(key)
            return fmt.format(v) if v is not None else "—"
        lines.append(
            f"| {name} | {s['n']} | {s['sum_pnl_pips']:+.1f} | "
            f"{_f('ev_pips')} | {_f('wr', '{:.1%}')} | "
            f"{_f('net_ev_pips')} | {_f('net_wr', '{:.1%}')} | "
            f"{_f('spread_entry_mean', '{:.2f}')} |")
    lines.append("")
    sp = res["stats"]["spaced"]
    if sp["n"]:
        lines.append(
            f"- net の内訳 (spaced): 研究 parity (s_e+s_x)/2 = "
            f"{sp['net_ev_pips']:+.2f}p / entry 全幅 = "
            f"{sp['net_ev_entry_only']:+.2f}p / house RT (s_e+s_x) = "
            f"{sp['net_ev_house_rt']:+.2f}p / 研究の仮定 "
            f"{RESEARCH_SPREAD_PIP}p 固定 = "
            f"{sp['net_ev_research_assumption']:+.2f}p")
        lines.append(
            f"- spread 前提の検証: entry spread min/med/max = "
            f"{sp['spread_entry_min']}/{sp['spread_entry_median']}/"
            f"{sp['spread_entry_max']}p、pre-reg 前提 "
            f"(<= {PREREG_SPREAD_PREMISE_PIPS}p) を満たす行 "
            f"{sp['rows_within_prereg_spread_premise']}/{sp['n']}")
    lines.append(f"- 最終発火: {res['last_fire']} "
                 f"({res['days_since_last_fire']} 日前)")
    if res["zero_fire_forensic_alert"]:
        lines.append(
            f"- ⚠️ **fire 0 が {ZERO_FIRE_FORENSIC_DAYS} 日以上継続** — LOCK "
            f"Withdrawal trigger 5 (発火経路の故障調査、kill でなく forensic)")
    return "\n".join(lines)


# ── データ取得 (CLI 実行時のみ) ──────────────────────────────────────

def fetch_and_evaluate(app_base: str, today: str | None = None) -> dict:
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if RETIRED_ON:
        # 退役済み — API を叩かない (network ゼロ、scheduled task は既定分岐で報告のみ)
        return {"verdict": VERDICT_RETIRED, "detail": RETIRED_DETAIL,
                "retired_on": RETIRED_ON, "today": today}
    if str(ROOT) not in sys.path:  # 直接実行時 (python3 tools/...) の package 解決
        sys.path.insert(0, str(ROOT))
    from tools.prereg_trigger_watch import fetch_trades_window
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
        if res["verdict"] in (VERDICT_UNAVAILABLE, VERDICT_RETIRED):
            print(f"## P-S1(a) dry-run: {res['verdict']} — {res['detail']}")
        else:
            print(to_markdown(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
