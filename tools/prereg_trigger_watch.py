#!/usr/bin/env python3
"""Pre-reg トリガー監視 — 「決定したが誰も監視していない」ギャップの構造防止。

背景 (2026-07-06): T5 JPYキャップ撤退 pre-reg のトリガー (USD_JPY D1 close>160.80)
が 2026-06-18 に成立していたのに監視主体が存在せず 18 日間未執行だった。
watchdog API_AUTH_TOKEN / carry dip env gate と同じ「decision-without-provisioning」
クラスの 3 例目。本ツールはその再発防止:

- 機械判定可能な pre-reg トリガー/決定点を registry (JSON) に登録し、毎日評価する
- cron 統合: tools/quant_gate_status.py (Tier A daily) が --json で呼び出して
  Discord レポートに含める

Registry: knowledge-base/wiki/decisions/prereg-trigger-registry.json

使用:
    python3 tools/prereg_trigger_watch.py            # Markdown 出力
    python3 tools/prereg_trigger_watch.py --json     # JSON 出力 (cron 統合用)

設計原則 (lessons 準拠):
- モジュールトップの副作用なし (import しても network/env 変更なし)
- データ取得失敗は DATA_UNAVAILABLE として報告し、cron を落とさない
- 判定ロジックは純関数 (evaluate_*) — テストはデータ注入で行う
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "knowledge-base" / "wiki" / "decisions" / "prereg-trigger-registry.json"
APP_BASE_DEFAULT = "https://fx-ai-trader.onrender.com"

STATE_TRIGGERED = "TRIGGERED"
STATE_WATCHING = "WATCHING"
STATE_UNAVAILABLE = "DATA_UNAVAILABLE"


# ── 純関数 (テスト対象) ──────────────────────────────────────────────

def evaluate_price_below(latest_close: float | None, threshold: float) -> dict[str, Any]:
    if latest_close is None:
        return {"state": STATE_UNAVAILABLE, "detail": "price feed unavailable"}
    if latest_close < threshold:
        return {"state": STATE_TRIGGERED,
                "detail": f"D1 close={latest_close:.3f} < {threshold:.2f}"}
    return {"state": STATE_WATCHING,
            "detail": f"D1 close={latest_close:.3f} >= {threshold:.2f}"}


def evaluate_shadow_count_decision(
    count: int | None,
    n_decide: int,
    n_floor: int,
    deadline: str,
    today: str,
) -> dict[str, Any]:
    """DEFER 決定点: N>=n_decide で判定実施、deadline 超過かつ N<n_floor で retire 期日。"""
    if count is None:
        return {"state": STATE_UNAVAILABLE, "detail": "trade API unavailable"}
    if count >= n_decide:
        return {"state": STATE_TRIGGERED,
                "detail": f"shadow N={count} >= {n_decide} — EV 判定を実施せよ (R1)"}
    if today > deadline and count < n_floor:
        return {"state": STATE_TRIGGERED,
                "detail": f"deadline {deadline} 超過かつ N={count} < {n_floor} — retire 執行期日 (R2)"}
    return {"state": STATE_WATCHING,
            "detail": f"shadow N={count}/{n_decide} (retire 判定: {deadline} に N<{n_floor})"}


def evaluate_live_count_decision(
    count: int | None,
    n_decide: int,
    deadline: str,
    today: str,
) -> dict[str, Any]:
    """live N 蓄積 checkpoint: N>=n_decide または deadline 到達で再評価を実施。

    shadow_count_decision と異なり retire 期日を持たない (pilot 等の
    「継続裁定 + 再評価点」用)。判定自体は R1/R2 手続きで別途行う。"""
    if count is None:
        return {"state": STATE_UNAVAILABLE, "detail": "trade API unavailable"}
    if count >= n_decide:
        return {"state": STATE_TRIGGERED,
                "detail": f"live N={count} >= {n_decide} — 再評価を実施せよ"}
    if today >= deadline:
        return {"state": STATE_TRIGGERED,
                "detail": f"deadline {deadline} 到達 (live N={count}) — 再評価を実施せよ"}
    return {"state": STATE_WATCHING,
            "detail": f"live N={count}/{n_decide} (期日: {deadline})"}


def evaluate_deadline_info(deadline: str, today: str) -> dict[str, Any]:
    """純期日監視: 期日超過で stale アラート (BT verdict 未着等の実行ギャップ検出)。"""
    if today > deadline:
        return {"state": STATE_TRIGGERED,
                "detail": f"期日 {deadline} 超過 — 未完了なら stale、状況確認せよ"}
    return {"state": STATE_WATCHING, "detail": f"期日 {deadline} まで監視"}


def evaluate_shadow_count_info(
    count: int | None, since: str, expected_per_week: float, today: str,
) -> dict[str, Any]:
    if count is None:
        return {"state": STATE_UNAVAILABLE, "detail": "trade API unavailable"}
    try:
        d0 = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
        d1 = datetime.fromisoformat(today).replace(tzinfo=timezone.utc)
        weeks = max((d1 - d0).days / 7.0, 1e-9)
        rate = count / weeks
    except ValueError:
        return {"state": STATE_UNAVAILABLE, "detail": f"bad dates since={since}"}
    return {"state": STATE_WATCHING,
            "detail": f"実測 {rate:.2f}/週 vs 期待 {expected_per_week}/週 (N={count})"}


# ── データ取得 (cron 実行時のみ呼ばれる) ─────────────────────────────

def fetch_latest_daily_close(symbol: str) -> float | None:
    try:
        import yfinance as yf
        df = yf.Ticker(symbol).history(period="5d", interval="1d")
        if df is None or df.empty:
            return None
        return float(df["Close"].dropna().iloc[-1])
    except Exception:
        return None


def count_matching(trades: list, entry_type: str, prefix: bool = False,
                   instrument: str = "") -> int:
    """entry_type の一致件数。prefix=True で前方一致 (multi-variant 戦略用、
    例: kalman_d7_* 3 variant 合算)。instrument 指定時はセル (戦略×ペア) 粒度
    (ws3-stage2-underpowered-recheck 用 — ペア無指定だと全ペア合算になり
    セル判定を過大計上する)。"""
    if instrument:
        trades = [t for t in trades if t.get("instrument") == instrument]
    if prefix:
        return sum(1 for t in trades
                   if str(t.get("entry_type") or "").startswith(entry_type))
    return sum(1 for t in trades if t.get("entry_type") == entry_type)


def count_live_matching(trades: list, entry_type: str, instrument: str,
                        direction: str) -> int:
    """clean live 件数: oanda_trade_id 非空 ∧ dedup_violation != 1 ∧ セル一致。"""
    n = 0
    for t in trades:
        if t.get("entry_type") != entry_type:
            continue
        if instrument and t.get("instrument") != instrument:
            continue
        if direction and t.get("direction") != direction:
            continue
        if not (t.get("oanda_trade_id") or ""):
            continue
        if (t.get("dedup_violation") or 0) == 1:
            continue
        n += 1
    return n


def fetch_live_count(entry_type: str, instrument: str, direction: str,
                     since: str, app_base: str) -> int | None:
    # limit=800 は shadow 大量 emit 下で ~7 日分しか遡れず月次窓を過小計上する
    # (2026-07-07 実測)。live 行は希少なので月次窓全量が要る → 8000。
    try:
        import requests
        r = requests.get(
            f"{app_base}/api/demo/trades",
            params={"date_from": since, "limit": 8000, "status": "all"},
            timeout=60,
        )
        r.raise_for_status()
        d = r.json()
        trades = d if isinstance(d, list) else d.get("trades", [])
        return count_live_matching(trades, entry_type, instrument, direction)
    except Exception:
        return None


def fetch_shadow_count(entry_type: str, since: str, app_base: str,
                       prefix: bool = False, instrument: str = "") -> int | None:
    try:
        import requests
        r = requests.get(
            f"{app_base}/api/demo/trades",
            params={"date_from": since, "limit": 800, "status": "all"},
            timeout=30,
        )
        r.raise_for_status()
        d = r.json()
        trades = d if isinstance(d, list) else d.get("trades", [])
        return count_matching(trades, entry_type, prefix, instrument=instrument)
    except Exception:
        return None


# ── registry 評価 ────────────────────────────────────────────────────

def load_registry(path: Path = REGISTRY_PATH) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [t for t in data.get("triggers", []) if t.get("active", True)]


def evaluate_trigger(trig: dict[str, Any], *, today: str, app_base: str) -> dict[str, Any]:
    ttype = trig.get("type")
    if ttype == "price_below":
        res = evaluate_price_below(
            fetch_latest_daily_close(trig["symbol"]), float(trig["threshold"]))
    elif ttype == "shadow_count_decision":
        res = evaluate_shadow_count_decision(
            fetch_shadow_count(trig["entry_type"], trig["since"], app_base,
                               prefix=trig.get("match") == "prefix",
                               instrument=trig.get("instrument", "")),
            int(trig["n_decide"]), int(trig["n_floor"]), trig["deadline"], today)
    elif ttype == "shadow_count_info":
        res = evaluate_shadow_count_info(
            fetch_shadow_count(trig["entry_type"], trig["since"], app_base,
                               prefix=trig.get("match") == "prefix"),
            trig["since"], float(trig["expected_per_week"]), today)
    elif ttype == "live_count_decision":
        res = evaluate_live_count_decision(
            fetch_live_count(trig["entry_type"], trig.get("instrument", ""),
                             trig.get("direction", ""), trig["since"], app_base),
            int(trig["n_decide"]), trig["deadline"], today)
    elif ttype == "deadline_info":
        res = evaluate_deadline_info(trig["deadline"], today)
    else:
        res = {"state": STATE_UNAVAILABLE, "detail": f"unknown type: {ttype}"}
    return {"id": trig["id"], "doc": trig.get("doc", ""),
            "message": trig.get("message", ""), **res}


def build_report(*, today: str | None = None, app_base: str | None = None) -> dict[str, Any]:
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    app_base = app_base or APP_BASE_DEFAULT
    results = [evaluate_trigger(t, today=today, app_base=app_base)
               for t in load_registry()]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "triggered": [r for r in results if r["state"] == STATE_TRIGGERED],
        "watching": [r for r in results if r["state"] == STATE_WATCHING],
        "unavailable": [r for r in results if r["state"] == STATE_UNAVAILABLE],
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = ["## Pre-reg Trigger Watch"]
    if report["triggered"]:
        lines.append("### 🔴 TRIGGERED — 執行/判定期日")
        for r in report["triggered"]:
            lines.append(f"- **{r['id']}**: {r['detail']} — {r['message']} ({r['doc']})")
    if report["watching"]:
        lines.append("### 👁 watching")
        for r in report["watching"]:
            lines.append(f"- {r['id']}: {r['detail']}")
    if report["unavailable"]:
        lines.append("### ⚠️ data unavailable")
        for r in report["unavailable"]:
            lines.append(f"- {r['id']}: {r['detail']}")
    if not any((report["triggered"], report["watching"], report["unavailable"])):
        lines.append("- (active な trigger なし)")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Pre-reg trigger watch")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(to_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
