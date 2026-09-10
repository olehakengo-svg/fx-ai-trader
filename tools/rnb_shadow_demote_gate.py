#!/usr/bin/env python3
"""rnb_support_bounce stage-1 shadow R2 auto-demote gate (read-only).

packet: knowledge-base/wiki/decisions/rnb-support-bounce-r1-packet-2026-09-10.md
        (§5 stage-1 gate / §6 棄却境界、rule:R1 user 承認 2026-09-10)
LOCK:   rnb-support-bounce-shadow-forward
        (registry: knowledge-base/wiki/decisions/prereg-trigger-registry.json)

目的 — 「無条件 emit は EV<0 で汚染源化」教訓の適用: stage-1 shadow-only
登録で開いた観測レーンが shadow DB の汚染源になっていないかを機械監視し、
棄却境界を踏んだら **auto_start=False 化の R2 起案** を fail-loud に出す。

gate (packet §5 / LOCK §6 棄却境界):
    shadow closed N >= 30 (dedup_violation=0) で WR の Wilson_hi < 42.9%
    (gross BEV) → DEMOTE_PROPOSED (exit 1)。
    執行 (MODE_CONFIG["rnb_usdjpy"]["auto_start"]=False) は R2 手続きで
    別 PR — 本ツールは read-only で、env/コード/DB を一切変更しない。

⚠️ P-10 (pre-reg LOCK) 境界: first look (shadow N>=41 or 2027-01-15) まで
採用側 estimand (Wilson_lo / net EV) の中間計算は禁止。本ツールは棄却境界の
評価に必要な n / wins / Wilson_hi **のみ**を計算・出力する (LOCK §6 で
棄却境界は継続監視として事前登録済み — 非対称機動性 Rule 2 側)。

読み手の配線: .github/workflows/r2-alert-scheduled.yml (6h 毎)。
「検知器が write-only」の再発防止として、配線の存在は
tests/test_rnb_shadow_demote_gate.py が pin する。

Usage:
    python3 tools/rnb_shadow_demote_gate.py            # human-readable
    python3 tools/rnb_shadow_demote_gate.py --json     # 構造化出力
    python3 tools/rnb_shadow_demote_gate.py --smoke    # 合成 fixture 検査
Exit codes: 0 = WATCHING / PASS_WATCH, 1 = DEMOTE_PROPOSED (R2 起案),
            2 = API 不達 (DATA_UNAVAILABLE — 「異常なし」に折り畳まない)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_API = "https://fx-ai-trader.onrender.com"
REPORT_DIR = _PROJECT_ROOT / "knowledge-base" / "raw" / "audits"

# ── 凍結パラメータ (packet §5/§6 — 変更は LOCK 改定 = user 決裁) ──────────
ENTRY_TYPE = "rnb_support_bounce"
MODE = "rnb_usdjpy"
INSTRUMENT = "USD_JPY"
DIRECTION = "BUY"
SINCE = "2026-09-10"          # 登録デプロイ日 = LOCK の forward 母集団起点
N_MIN = 30                    # packet §5 stage-1 gate
WILSON_HI_REJECT = 0.429      # gross BEV (packet §5/§6 棄却境界、厳密未満)

_PAGE_SIZE = 500
_MAX_PAGES = 80

_SSL_CTX = ssl.create_default_context()
_SAFE_OPENER = urllib.request.build_opener(
    urllib.request.HTTPHandler(),
    urllib.request.HTTPSHandler(context=_SSL_CTX),
)


class ApiError(RuntimeError):
    """Network/API failure → exit 2 (DATA_UNAVAILABLE)。"""


def _fetch_json(url: str) -> Any:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ApiError(f"refusing invalid URL: {url!r}")
    req = urllib.request.Request(
        url, headers={"User-Agent": "rnb-shadow-demote-gate/1.0"}
    )
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with _SAFE_OPENER.open(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        raise ApiError(f"API fetch failed ({type(e).__name__}: {e})") from e


def fetch_closed_trades(api: str = DEFAULT_API) -> list[dict]:
    """SINCE 以降の closed 行を mode 絞り込み + offset pagination で全量取得。

    単発 limit は希少戦略の N を過小計上する (sweep P-S1(a) 教訓) ため、
    短ページが返るまで反復。max_pages 到達 = 全量保証なし → fail-loud。
    """
    rows: list[dict] = []
    for i in range(_MAX_PAGES):
        qs = urllib.parse.urlencode({
            "status": "closed", "date_from": SINCE, "mode": MODE,
            "limit": _PAGE_SIZE, "offset": i * _PAGE_SIZE,
        })
        payload = _fetch_json(f"{api.rstrip('/')}/api/demo/trades?{qs}")
        page = payload.get("trades", []) if isinstance(payload, dict) else payload
        if not isinstance(page, list):
            raise ApiError("API response has non-list trades payload")
        rows.extend(t for t in page if isinstance(t, dict))
        if len(page) < _PAGE_SIZE:
            return rows
    raise ApiError(f"pagination exceeded {_MAX_PAGES} pages — 全量取得を保証できない")


def filter_gate_population(trades: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """LOCK 母集団 (forward shadow rows: USD_JPY, BUY, dedup_violation=0,
    closed, 厳格 shadow) への絞り込み。

    除外は理由別に計数して返す — no_rows と error、「静かだった」と
    「見えていなかった」を折り畳まない (2026-08-30 教訓)。
    厳格 shadow 分離 (2026-08 恒久指示): shadow = is_shadow=1 **かつ**
    oanda_trade_id 空。is_shadow=1 なのに fill id を持つ行は ambiguous として
    除外・計数する (shadow_only 構造保証の破れを示すので 0 のはず)。
    """
    kept: list[dict] = []
    excluded = {
        "other_entry_type": 0, "other_instrument": 0, "other_direction": 0,
        "not_closed": 0, "dedup_violation": 0, "not_shadow": 0,
        "ambiguous_shadow_with_fill": 0, "pnl_missing": 0,
    }
    for t in trades:
        if str(t.get("entry_type") or "") != ENTRY_TYPE:
            excluded["other_entry_type"] += 1
            continue
        if str(t.get("instrument") or "") != INSTRUMENT:
            excluded["other_instrument"] += 1
            continue
        if str(t.get("direction") or "") != DIRECTION:
            excluded["other_direction"] += 1
            continue
        if str(t.get("status") or "").upper() != "CLOSED":
            excluded["not_closed"] += 1
            continue
        if int(t.get("dedup_violation", 0) or 0) == 1:
            excluded["dedup_violation"] += 1
            continue
        if int(t.get("is_shadow", 0) or 0) != 1:
            excluded["not_shadow"] += 1
            continue
        if str(t.get("oanda_trade_id") or ""):
            excluded["ambiguous_shadow_with_fill"] += 1
            continue
        pnl = t.get("pnl_pips")
        try:
            pnl_f = float(pnl)
        except (TypeError, ValueError):
            excluded["pnl_missing"] += 1
            continue
        row = dict(t)
        row["pnl_pips"] = pnl_f
        kept.append(row)
    return kept, excluded


def wilson_hi(wins: int, n: int, z: float = 1.96) -> float:
    if n <= 0:
        return 0.0
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt((p * (1 - p) / n) + (z * z / (4 * n * n)))) / denom
    return min(1.0, centre + margin)


def decide_gate(n: int, wins: int, *,
                n_min: int = N_MIN,
                wilson_hi_reject: float = WILSON_HI_REJECT) -> dict[str, Any]:
    """純関数 (テスト対象): 棄却境界の判定のみ。

    - n < n_min                      → WATCHING (蓄積継続)
    - n >= n_min ∧ Wilson_hi < 境界 → DEMOTE_PROPOSED (auto_start=False の
                                       R2 起案 — 執行は別 PR / LOCK クローズ提案)
    - n >= n_min ∧ Wilson_hi >= 境界 → PASS_WATCH (棄却されず蓄積継続。採用側
                                       判定は LOCK first look まで計算しない)
    """
    hi = wilson_hi(wins, n)
    if n < n_min:
        return {"state": "WATCHING", "wilson_hi": hi,
                "detail": f"shadow closed N={n}/{n_min} — 蓄積中 (棄却判定は N>={n_min})"}
    if hi < wilson_hi_reject:
        return {"state": "DEMOTE_PROPOSED", "wilson_hi": hi,
                "detail": (f"N={n} wins={wins} Wilson_hi={hi:.3f} < "
                           f"{wilson_hi_reject:.3f} (gross BEV) — auto_start=False の "
                           "R2 起案 + LOCK 棄却クローズ提案 (packet §5/§6)")}
    return {"state": "PASS_WATCH", "wilson_hi": hi,
            "detail": (f"N={n} wins={wins} Wilson_hi={hi:.3f} >= "
                       f"{wilson_hi_reject:.3f} — 棄却されず。採用判定は LOCK first look "
                       "(N>=41 or 2027-01-15) まで凍結 (P-10)")}


def run(trades: list[dict], *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    kept, excluded = filter_gate_population(trades)
    n = len(kept)
    wins = sum(1 for t in kept if t["pnl_pips"] > 0)
    res = decide_gate(n, wins)
    return {
        "generated_at": now.isoformat(),
        "gate": {
            "entry_type": ENTRY_TYPE, "mode": MODE, "instrument": INSTRUMENT,
            "direction": DIRECTION, "since": SINCE,
            "n_min": N_MIN, "wilson_hi_reject": WILSON_HI_REJECT,
        },
        "n": n,
        "wins": wins,
        "excluded": excluded,
        # 採用側 estimand (Wilson_lo / net EV) は LOCK first look まで出力しない
        **res,
    }


def write_report(result: dict[str, Any], report_dir: Path = REPORT_DIR) -> Path:
    """TRIGGERED 時のみ呼ばれる markdown 記録 (R2 起案の一次証跡)。"""
    report_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.fromisoformat(result["generated_at"])
    out = report_dir / f"rnb-shadow-demote-gate-{now.strftime('%Y-%m-%d-%H%M')}.md"
    lines = [
        f"# rnb_shadow_demote_gate — {result['state']} ({result['generated_at']})",
        "",
        f"- gate: shadow closed N>={N_MIN} (dedup_violation=0) ∧ "
        f"Wilson_hi < {WILSON_HI_REJECT} (gross BEV)",
        f"- population: {ENTRY_TYPE} × {INSTRUMENT} × {DIRECTION}, "
        f"mode={MODE}, since {SINCE}, strict shadow (is_shadow=1 ∧ oanda_trade_id 空)",
        f"- n={result['n']} wins={result['wins']} wilson_hi={result['wilson_hi']:.4f}",
        f"- excluded: {json.dumps(result['excluded'], ensure_ascii=False)}",
        f"- detail: {result['detail']}",
        "",
        "次アクション (R2): MODE_CONFIG['rnb_usdjpy']['auto_start']=False 化の PR 起案",
        "+ registry rnb-support-bounce-shadow-forward の棄却クローズ提案。",
        "packet: knowledge-base/wiki/decisions/rnb-support-bounce-r1-packet-2026-09-10.md",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def send_discord_alert(result: dict[str, Any], webhook_url: str | None) -> bool:
    if not webhook_url:
        return False
    content = (
        f"RNB R2 DEMOTE GATE TRIGGERED: {result['detail']}\n"
        f"→ auto_start=False の R2 起案 (packet rnb-support-bounce-r1-packet-2026-09-10 §5)"
    )
    body = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "rnb-shadow-demote-gate/1.0"},
        method="POST",
    )
    try:
        # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        with _SAFE_OPENER.open(req, timeout=15):
            return True
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"WARNING: Discord alert failed ({type(e).__name__}: {e})",
              file=sys.stderr)
        return False


def _smoke_test() -> int:
    """合成 fixture の counterfactual: 悪化データで必ず発火し、境界の
    反対側では発火しないことをネットワーク無しで検査する。"""
    def row(pnl: float, **over) -> dict:
        base = {
            "entry_type": ENTRY_TYPE, "instrument": INSTRUMENT,
            "direction": DIRECTION, "status": "CLOSED", "is_shadow": 1,
            "oanda_trade_id": "", "dedup_violation": 0, "pnl_pips": pnl,
        }
        base.update(over)
        return base

    # 30 行 6 勝 (WR20%) → Wilson_hi ≈ 0.373 < 0.429 → 発火
    bad = [row(1.0) for _ in range(6)] + [row(-1.0) for _ in range(24)]
    assert run(bad)["state"] == "DEMOTE_PROPOSED", run(bad)
    # 29 行では発火しない (N gate)
    assert run(bad[:29])["state"] == "WATCHING", run(bad[:29])
    # 30 行 12 勝 (WR40%, Wilson_hi ≈ 0.577) → 発火しない
    ok = [row(1.0) for _ in range(12)] + [row(-1.0) for _ in range(18)]
    assert run(ok)["state"] == "PASS_WATCH", run(ok)
    # dedup / live-fill / open 行は母集団に入らない
    polluted = bad + [row(-1.0, dedup_violation=1),
                      row(-1.0, oanda_trade_id="OANDA-1"),
                      row(-1.0, status="OPEN")]
    r = run(polluted)
    assert r["n"] == 30 and r["excluded"]["dedup_violation"] == 1, r
    assert r["excluded"]["ambiguous_shadow_with_fill"] == 1, r
    assert r["excluded"]["not_closed"] == 1, r
    print("smoke: OK")
    return 0


def cli(fetcher: Callable[[str], list[dict]] = fetch_closed_trades) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only R2 auto-demote gate for rnb_support_bounce shadow lane."
    )
    parser.add_argument("--api", default=DEFAULT_API, help="API base URL")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON")
    parser.add_argument("--no-report", action="store_true",
                        help="Do not write markdown report on trigger")
    parser.add_argument("--no-discord", action="store_true",
                        help="Do not send Discord webhook alert on trigger")
    parser.add_argument("--smoke", action="store_true",
                        help="Run synthetic fixture checks without network")
    args = parser.parse_args()

    if args.smoke:
        return _smoke_test()

    try:
        trades = fetcher(args.api)
    except ApiError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    result = run(trades)
    triggered = result["state"] == "DEMOTE_PROPOSED"
    if triggered and not args.no_report:
        result["report_path"] = str(write_report(result))
    if triggered and not args.no_discord:
        result["discord_alert_sent"] = send_discord_alert(
            result, os.environ.get("DISCORD_WEBHOOK_URL"))

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        print(f"[rnb_shadow_demote_gate] state={result['state']} "
              f"n={result['n']} wins={result['wins']} "
              f"wilson_hi={result['wilson_hi']:.4f} — {result['detail']}")
    return 1 if triggered else 0


if __name__ == "__main__":
    sys.exit(cli())
