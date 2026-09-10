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
import ast
import json
import math
import re
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
# 「評価器が落ちた」は「データが取れなかった」と別事象。折り畳むと
# 壊れた監視器が「異常なし」と区別できなくなる (2026-09-08 実発生)。
STATE_ERROR = "EVAL_ERROR"


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


def _iso_age_hours(value: Any, now_iso: str) -> float | None:
    """ISO timestamp (末尾 Z 可) の now からの経過時間 [h]。不正値は None。"""
    if not value:
        return None
    try:
        v = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        n = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if n.tzinfo is None:
            n = n.replace(tzinfo=timezone.utc)
        return (n - v).total_seconds() / 3600.0
    except ValueError:
        return None


def evaluate_ingest_freshness(
    health: dict[str, Any] | None,
    checks: list[dict[str, Any]],
    now_iso: str,
) -> dict[str, Any]:
    """ingest 鮮度監視: health の verified:* age が閾値超で要調査 TRIGGERED。

    checks の各要素は {"key": ..., "max_age_hours": N} (単一キー) または
    {"prefix": ..., "max_age_hours": N, "min_keys": M} (前方一致、M キー未満で
    警報 — 契約単位の verified が 1 本だけ立たない欠落も拾う)。

    キー欠落・prefix 一致ゼロは TRIGGERED (worker 未稼働/thread 死を fail-loud
    に検出 — E1 positioning の thread 死教訓)。API 不達 (None) と health DB
    エラー (_error) は「stale 確定」と区別して DATA_UNAVAILABLE。
    """
    if health is None:
        return {"state": STATE_UNAVAILABLE, "detail": "status API unreachable"}
    if "_error" in health:
        return {"state": STATE_UNAVAILABLE,
                "detail": f"health DB error: {health['_error']}"}
    stale: list[str] = []
    fresh: list[str] = []

    def check_key(key: str, max_h: float) -> None:
        age = _iso_age_hours(health.get(key), now_iso)
        if age is None:
            stale.append(f"{key} verified 記録なし (> {max_h:.0f}h 扱い)")
        elif age > max_h:
            stale.append(f"{key} age={age:.1f}h > {max_h:.0f}h")
        else:
            fresh.append(f"{key} {age:.1f}h")

    for chk in checks:
        max_h = float(chk["max_age_hours"])
        prefix = chk.get("prefix")
        if prefix:
            keys = sorted(k for k in health if k.startswith(prefix))
            min_keys = int(chk.get("min_keys", 1))
            if len(keys) < min_keys:
                stale.append(
                    f"{prefix}* {len(keys)}/{min_keys} キー (min_keys 未達 — "
                    "未 verified/worker 未稼働疑い)")
            for k in keys:
                check_key(k, max_h)
        else:
            check_key(chk["key"], max_h)

    if stale:
        return {"state": STATE_TRIGGERED, "detail": "stale: " + "; ".join(stale)}
    return {"state": STATE_WATCHING,
            "detail": f"fresh ({len(fresh)} keys): " + ", ".join(fresh)}


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


def evaluate_artifact_presence(
    measured: dict[str, int], requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    """成果物着地の機械判定: 全 requirement を満たしたら TRIGGERED。

    「main に着地したら発火」型の条件を人手判定に委ねると、条件成立後も
    watching のまま滞留する (ZN 教訓: 「条件を書く」と「条件が起こりうる」は
    別物)。measured は path パターン -> 実測ファイル数 (scan_artifacts が生成)。
    """
    if measured is None:
        return {"state": STATE_UNAVAILABLE, "detail": "artifact scan unavailable"}
    missing: list[str] = []
    have: list[str] = []
    for req in requirements:
        pat = req["path"]
        need = int(req.get("min_files", 1))
        got = int(measured.get(pat, 0))
        label = req.get("label", pat)
        if got < need:
            missing.append(f"{label} ({got}/{need})")
        else:
            have.append(f"{label} {got}")
    if missing:
        return {"state": STATE_WATCHING,
                "detail": "未着地: " + " / ".join(missing)
                          + (f" — 着地済: {', '.join(have)}" if have else "")}
    return {"state": STATE_TRIGGERED,
            "detail": "成果物着地を確認 (" + ", ".join(have)
                      + ") — 条件成立、resolve して後続レーンへ通知せよ"}


def evaluate_data_coverage(
    max_date: str | None, threshold_date: str,
) -> dict[str, Any]:
    """データ被覆の機械判定: 実測 max 日付が閾値を超えたら TRIGGERED。

    cache 延伸待ちの条件付きエントリ用。取得不能は fail-loud せず
    DATA_UNAVAILABLE (cron を落とさない設計原則)。
    """
    if not max_date:
        return {"state": STATE_UNAVAILABLE, "detail": "coverage 取得不能"}
    if str(max_date)[:10] > threshold_date:
        return {"state": STATE_TRIGGERED,
                "detail": f"被覆 {str(max_date)[:10]} > 閾値 {threshold_date} — 条件成立"}
    return {"state": STATE_WATCHING,
            "detail": f"被覆 {str(max_date)[:10]} / 閾値 {threshold_date} まで延伸待ち"}


_CSV_OPS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _csv_row_predicate(row: dict[str, Any], cond: dict[str, Any]) -> bool:
    """1 条件の評価。value が数値なら数値比較、それ以外は文字列比較。

    数値列に空文字/非数値が入っていたら False — 欠測は「一致」ではない。
    op の妥当性は呼び出し側 (evaluate_csv_row_match) が事前検証する。
    """
    op = _CSV_OPS[str(cond.get("op", "=="))]
    raw = row.get(cond["column"])
    want = cond["value"]
    if isinstance(want, (int, float)) and not isinstance(want, bool):
        try:
            return op(float(raw), float(want))
        except (TypeError, ValueError):
            return False
    return op(str(raw if raw is not None else ""), str(want))


def evaluate_csv_row_match(
    rows: list[dict[str, Any]] | None,
    match: list[dict[str, Any]],
    label_columns: list[str] | None = None,
) -> dict[str, Any]:
    """リポジトリ内 CSV に述語を満たす行が現れたら TRIGGERED。

    背景 (2026-08-31、write-only 6 例目): MoF 月次介入額の開示
    (2026-07-30〜08-26 = 15兆3,993億円) は日次 cron が **08-29 に**
    interventions_monthly_pending.csv へ書き込んでいた。しかし registry 側の
    到達経路は「deadline (08-31) まで無反応 + 人手で公表 URL を直叩き」しか
    無く、値がリポジトリに 2 日間座ったまま誰も読まなかった。しかもその人手
    経路は公表 URL を命名規則から**推測**していたため、実際の
    20260828.html を 20260831.html と取り違えて 404 = 「未公表」と誤読した。

    → 収集済みデータを機械が読む経路を与えるのが本評価器。書き手 (cron) と
    読み手 (本評価器) を必ず対にする。

    設計 (PR #207 の no_rows vs error 教訓): 「取得不能」と「行はあるが
    述語に一致しない」を折り畳まない。ファイル欠落/パース失敗/列欠落/
    述語不正は DATA_UNAVAILABLE、一致ゼロのみ WATCHING。折り畳むと schema が
    壊れた瞬間から永久に「健全に監視中」を表示し続ける。
    """
    if not match:
        return {"state": STATE_UNAVAILABLE,
                "detail": "match 述語が空 — 全行一致の偽発火を防ぐため評価しない"}
    bad_ops = sorted({str(c.get("op", "==")) for c in match} - set(_CSV_OPS))
    if bad_ops:
        return {"state": STATE_UNAVAILABLE,
                "detail": f"未知の op: {', '.join(bad_ops)}"}
    if rows is None:
        return {"state": STATE_UNAVAILABLE, "detail": "CSV 取得不能"}
    needed = {str(c["column"]) for c in match}
    if rows:
        missing = sorted(needed - set(rows[0].keys()))
        if missing:
            return {"state": STATE_UNAVAILABLE,
                    "detail": f"列欠落 (schema 変化?): {', '.join(missing)}"}
    cond_txt = " ∧ ".join(
        f"{c['column']}{c.get('op', '==')}{c['value']}" for c in match)
    hits = [r for r in rows if all(_csv_row_predicate(r, c) for c in match)]
    if not hits:
        return {"state": STATE_WATCHING,
                "detail": f"該当行なし ({len(rows)} 行走査) — 条件 {cond_txt}"}
    cols = label_columns or sorted(needed)
    shown = " ; ".join(
        ", ".join(f"{c}={r.get(c)}" for c in cols) for r in hits[:5])
    return {"state": STATE_TRIGGERED,
            "detail": f"該当 {len(hits)} 行 (条件 {cond_txt}): {shown}"}


def evaluate_manual_info(
    condition: str, deadline: str, today: str, reachability: str,
) -> dict[str, Any]:
    """人手判定エントリ: 機械評価はしないが deadline は必ず効かせる。

    2026-08-19: info/conditional_info が deadline を無視して無期限 watching
    だったため、期日付き手動エントリ (volstate-split 系等) が自分から
    期限切れを名乗れなかった。deadline_info と同じ escalation を与える。
    """
    detail = condition or "info 監視 (手動判定)"
    if deadline and deadline != "no-deadline" and today > deadline:
        return {"state": STATE_TRIGGERED,
                "detail": f"期日 {deadline} 超過 (手動判定エントリ) — {detail}"
                          + (f" / 到達経路: {reachability}" if reachability else "")}
    return {"state": STATE_WATCHING, "detail": detail}


# ── データ取得 (cron 実行時のみ呼ばれる) ─────────────────────────────

def scan_artifacts(requirements: list[dict[str, Any]],
                   root: Path = ROOT) -> dict[str, int]:
    """requirement の path (glob 可) にマッチする実ファイル数を数える。"""
    out: dict[str, int] = {}
    for req in requirements:
        pat = req["path"]
        try:
            matches = [m for m in root.glob(pat) if m.is_file()]
            out[pat] = len(matches)
        except (OSError, ValueError):
            out[pat] = 0
    return out


def fetch_data_coverage_max(spec: dict[str, Any],
                            root: Path = ROOT) -> str | None:
    """cache ファイルの被覆最大日付を返す (parquet index / csv 列)。"""
    path = root / spec["path"]
    if not path.exists():
        return None
    try:
        import pandas as pd
        col = spec.get("date_column", "")
        if path.suffix == ".parquet":
            df = pd.read_parquet(path)
        else:
            df = pd.read_csv(path)
        if col and col in df.columns:
            return str(pd.to_datetime(df[col]).max())
        if isinstance(df.index, pd.DatetimeIndex) and len(df):
            return str(df.index.max())
        return None
    except Exception:
        return None


def read_csv_rows(spec: dict[str, Any],
                  root: Path = ROOT) -> list[dict[str, Any]] | None:
    """registry の source spec が指す CSV を dict 行として読む。

    取得不能 (欠落/パース失敗) は None を返し DATA_UNAVAILABLE にする —
    「空の CSV」と折り畳まないこと (evaluate_csv_row_match の docstring 参照)。
    """
    path = root / spec["path"]
    if not path.exists():
        return None
    try:
        import csv as _csv
        with path.open(newline="", encoding="utf-8") as f:
            return list(_csv.DictReader(f))
    except Exception:
        return None


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
                   instrument: str = "",
                   exclude_dedup_violation: bool = False,
                   direction: str = "",
                   closed_only: bool = False) -> int:
    """entry_type の一致件数。prefix=True で前方一致 (multi-variant 戦略用、
    例: kalman_d7_* 3 variant 合算)。instrument 指定時はセル (戦略×ペア) 粒度
    (ws3-stage2-underpowered-recheck 用 — ペア無指定だと全ペア合算になり
    セル判定を過大計上する)。exclude_dedup_violation=True で dedup_violation=1
    の重複行を除外 = unique バー基準 (registry `count_basis: "unique"`、
    sweep P-S1(a) 決裁パケット §1.4 で確定した estimand 忠実計数)。

    2026-08-18 追加 (sr-anti-hunt forward-confirm 偽発火の修正):
    direction 指定でセル方向粒度、closed_only=True で status=CLOSED 行のみ
    (P&L 確定母集団で判定する decision エントリ用 — open 行込みだと単発 look の
    早期 burn を誘発する。実測: registry 式 40 vs 凍結母集団 22)。"""
    if instrument:
        trades = [t for t in trades if t.get("instrument") == instrument]
    if direction:
        trades = [t for t in trades if t.get("direction") == direction]
    if closed_only:
        trades = [t for t in trades
                  if str(t.get("status") or "").upper() == "CLOSED"]
    if exclude_dedup_violation:
        trades = [t for t in trades if (t.get("dedup_violation") or 0) != 1]
    if prefix:
        return sum(1 for t in trades
                   if str(t.get("entry_type") or "").startswith(entry_type))
    return sum(1 for t in trades if t.get("entry_type") == entry_type)


def paginate_closed_trades(fetch_page, page_size: int = 500,
                           max_pages: int = 80) -> list | None:
    """fetch_page(offset) -> list[dict] を短ページが返るまで offset 反復。

    2026-07-24 実測バグの構造修正: 単発 limit=800 は全 mode 合算の直近行しか
    見えず、希少戦略の shadow N を 0 に向けて過小計上していた (sweep P-S1(a)
    パケット §1.5 — 放置すると 09-30 retire 分岐が偽 N=0 で誤発動)。
    max_pages 到達 = 全量取得の保証がない → None を返して DATA_UNAVAILABLE に
    する (fail-loud、silent truncation の再発防止)。"""
    rows: list = []
    for i in range(max_pages):
        page = fetch_page(i * page_size)
        if not isinstance(page, list):
            return None
        rows.extend(page)
        if len(page) < page_size:
            return rows
    return None


def count_live_matching(trades: list, entry_type: str, instrument: str,
                        direction: str, prefix: bool = False,
                        reasons_marker: str = "") -> int:
    """clean live 件数: oanda_trade_id 非空 ∧ dedup_violation != 1 ∧ セル一致。

    prefix=True で entry_type を前方一致にする (kalman_d7 の 3 variant 等、
    1 セル = 複数 entry_type の合算監視用)。shadow 側 count_matching と同じ契約。

    reasons_marker: 非空なら reasons にこの literal を含む行のみ数える。
    2026-09-02 (rule:R1 hourblock class exemption): 免除経路で通過した行だけを
    母集団にする estimand ([HOURBLOCK_CLASS_EXEMPT] marker) 用。entry_type="" と
    組み合わせると「marker を持つ全戦略」の class-pooled 計数になる。reasons は
    API では JSON 文字列、DB fixture では list のことがあるため両対応。
    """
    n = 0
    for t in trades:
        _et = t.get("entry_type") or ""
        if entry_type:
            if (not _et.startswith(entry_type)) if prefix else (_et != entry_type):
                continue
        if instrument and t.get("instrument") != instrument:
            continue
        if direction and t.get("direction") != direction:
            continue
        if reasons_marker:
            _r = t.get("reasons") or ""
            if isinstance(_r, list):
                _r = " | ".join(str(x) for x in _r)
            if reasons_marker not in _r:
                continue
        if not (t.get("oanda_trade_id") or ""):
            continue
        if (t.get("dedup_violation") or 0) == 1:
            continue
        n += 1
    return n


def fetch_trades_window(since: str, app_base: str, mode: str = "") -> list | None:
    """date_from 以降の全 trades (open + closed 全ページ)。

    /api/demo/trades は status=all だと open 行が毎ページ先頭に再混入するため、
    closed を offset pagination で全量取得 + open を 1 回取得して id で重複排除。
    mode 指定でサーバ側絞り込み (希少戦略はページ数が桁で減る)。
    取得不能・pagination 打ち切りは None (DATA_UNAVAILABLE)。"""
    try:
        import requests

        def _get(status: str, offset: int, limit: int) -> list | None:
            params: dict[str, Any] = {
                "date_from": since, "limit": limit, "offset": offset,
                "status": status,
            }
            if mode:
                params["mode"] = mode
            r = requests.get(f"{app_base}/api/demo/trades",
                             params=params, timeout=60)
            r.raise_for_status()
            d = r.json()
            rows = d if isinstance(d, list) else d.get("trades", [])
            return rows if isinstance(rows, list) else None

        closed = paginate_closed_trades(
            lambda off: _get("closed", off, 500), page_size=500)
        if closed is None:
            return None
        # open 取得失敗も fail-loud (Codex review 2026-07-24: or [] だと
        # open 行を黙って落として closed だけ数える = 過小計上の再導入)
        open_rows = _get("open", 0, 500)
        if open_rows is None:
            return None
        seen_ids: set = set()
        out: list = []
        for t in open_rows + closed:
            key = t.get("id") if t.get("id") is not None else t.get("trade_id")
            if key is not None and key in seen_ids:
                continue
            if key is not None:
                seen_ids.add(key)
            out.append(t)
        return out
    except Exception:
        return None


def fetch_live_count(entry_type: str, instrument: str, direction: str,
                     since: str, app_base: str, prefix: bool = False,
                     reasons_marker: str = "") -> int | None:
    # 2026-07-24: 単発 limit=8000 (2026-07-07 の暫定拡大) を pagination 全量取得に
    # 置換 — emit 量が伸びると同じ undercount が再発するため。
    trades = fetch_trades_window(since, app_base)
    if trades is None:
        return None
    return count_live_matching(trades, entry_type, instrument, direction,
                               prefix=prefix, reasons_marker=reasons_marker)


def fetch_shadow_count(entry_type: str, since: str, app_base: str,
                       prefix: bool = False, instrument: str = "",
                       mode: str = "",
                       exclude_dedup_violation: bool = False,
                       direction: str = "",
                       closed_only: bool = False) -> int | None:
    trades = fetch_trades_window(since, app_base, mode=mode)
    if trades is None:
        return None
    return count_matching(trades, entry_type, prefix, instrument=instrument,
                          exclude_dedup_violation=exclude_dedup_violation,
                          direction=direction, closed_only=closed_only)


def fetch_ingest_health(app_base: str, endpoint: str) -> dict[str, Any] | None:
    """ingest status API の health dict。API 不達は None (UNAVAILABLE)、
    worker 未起動レスポンス (health キー欠落) は {} — 評価側で全キー欠落
    として fail-loud TRIGGERED になる。"""
    try:
        import requests
        r = requests.get(f"{app_base}{endpoint}", timeout=30)
        r.raise_for_status()
        d = r.json()
        h = d.get("health") if isinstance(d, dict) else None
        return h if isinstance(h, dict) else {}
    except Exception:
        return None


# ── registry 評価 ────────────────────────────────────────────────────

def load_registry_raw(path: Path = REGISTRY_PATH) -> list[dict[str, Any]]:
    """active フィルタ前の全エントリ。lint は必ずこちらを見る。

    2026-09-08 (PR #227 Codex P2 9 巡目): `active` は truthiness で消費される
    ため `active: "false"` は **true** 扱いで評価され、逆に壊れた falsey 値は
    lint に届く前に消える。フィルタ後だけを検査する lint は `active` 自身の
    不正を構造的に見られない。
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    # `.get("triggers", [])` は root キーの綴り違い/欠落を**空の台帳**に畳んで
    # しまう。すると check.py も本監視器も exit 0 のまま「active な trigger は
    # 無い」と報告し、**51 エントリ全部が黙って消える** — 本 PR が直している
    # 2 日間 blind と同じ帰結を、もっと静かな形で作る (Codex P1 16 巡目)。
    # 監視器の不変条件: **検査不能を「異常なし」に折り畳まない**。
    if not isinstance(data, dict):
        raise RuntimeError(
            f"{path}: registry の root が dict でない "
            f"({type(data).__name__}) — 台帳として読めない")
    if "triggers" not in data:
        near = [k for k in data if "trig" in k.lower()]
        raise RuntimeError(
            f"{path}: root に 'triggers' キーが無い (実在キー: {sorted(data)})"
            + (f" — 綴り違いの候補: {near}" if near else "")
            + "。空の台帳に畳むと全 trigger が黙って消える")
    trigs = data["triggers"]
    if not isinstance(trigs, list):
        raise RuntimeError(
            f"{path}: 'triggers' が list でない ({type(trigs).__name__})")
    if not trigs:
        # 「意図的に空」と「台帳が消えた」を区別できないので、監視器としては
        # 後者を仮定する。本当に空の台帳を運用するなら本 guard を明示的に外す。
        raise RuntimeError(
            f"{path}: 'triggers' が空 — 監視器は「意図的に空」と「台帳が"
            "消えた」を区別できないため異常として扱う")
    return list(trigs)


def load_registry(path: Path = REGISTRY_PATH) -> list[dict[str, Any]]:
    """active フィルタ後のエントリ。

    ⚠️ `active` フィルタの前に**要素が dict であること**を確かめる。
    `{"triggers": [null, {...}]}` は list 形の検査を通るが `null.get()` で
    ここが落ち、`evaluate_trigger` の隔離ラッパに届く前に**後続の正常な
    trigger すべてが未評価**になる (PR #227 Codex P2 18 巡目) —
    隔離ラッパが防ぐはずの盲点を、その手前の層で作り直していた。
    """
    raw = load_registry_raw(path)
    bad = [i for i, t in enumerate(raw) if not isinstance(t, dict)]
    if bad:
        kinds = {i: type(raw[i]).__name__ for i in bad}
        raise RuntimeError(
            f"{path}: triggers の要素が dict でない (index→型: {kinds}) — "
            "active フィルタより手前で落ちるため隔離ラッパでは救えない")
    return [t for t in raw if t.get("active", True)]


def _evaluate_trigger_impl(
    trig: dict[str, Any], *, today: str, app_base: str,
) -> dict[str, Any]:
    ttype = trig.get("type")
    if ttype == "price_below":
        res = evaluate_price_below(
            fetch_latest_daily_close(trig["symbol"]), float(trig["threshold"]))
    elif ttype == "shadow_count_decision":
        # 2026-08-18: direction / dedup_violation:0 / closed_only を契約どおり解釈
        # (sr-anti-hunt forward-confirm が方向・dedup 無視 + open 込みで N=40 と
        # 偽発火 — 凍結母集団の実測は 22。entry のフィールドを黙って無視しない)
        res = evaluate_shadow_count_decision(
            fetch_shadow_count(trig["entry_type"], trig["since"], app_base,
                               prefix=trig.get("match") == "prefix",
                               instrument=trig.get("instrument", ""),
                               mode=trig.get("mode", ""),
                               exclude_dedup_violation=(
                                   trig.get("count_basis") == "unique"
                                   or trig.get("dedup_violation") == 0),
                               direction=trig.get("direction", ""),
                               closed_only=bool(trig.get("closed_only"))),
            int(trig["n_decide"]), int(trig["n_floor"]), trig["deadline"], today)
    elif ttype == "shadow_count_info":
        # 2026-09-10 (PR #227 Codex P2 14 巡目): instrument / direction は
        # allowlist にあるのに評価器へ渡されていなかった = 綴りが正しくても
        # **黙って全ペア/全方向を計上**する。shadow_count_decision 側は
        # 2026-08-18 に同じ穴を塞いでいる (sr-anti-hunt 偽発火)。
        # allowlist に入れた selector は必ず評価器まで配線すること。
        res = evaluate_shadow_count_info(
            fetch_shadow_count(trig["entry_type"], trig["since"], app_base,
                               prefix=trig.get("match") == "prefix",
                               instrument=trig.get("instrument", ""),
                               direction=trig.get("direction", ""),
                               mode=trig.get("mode", ""),
                               exclude_dedup_violation=(
                                   trig.get("count_basis") == "unique")),
            trig["since"], float(trig["expected_per_week"]), today)
    elif ttype == "live_count_decision":
        res = evaluate_live_count_decision(
            fetch_live_count(trig["entry_type"], trig.get("instrument", ""),
                             trig.get("direction", ""), trig["since"], app_base,
                             prefix=trig.get("match") == "prefix",
                             reasons_marker=trig.get("reasons_marker", "")),
            int(trig["n_decide"]), trig["deadline"], today)
    elif ttype == "deadline_info":
        res = evaluate_deadline_info(trig["deadline"], today)
    elif ttype == "ingest_freshness":
        # today (date 粒度) では時間単位の鮮度を測れないため実時刻を使う。
        res = evaluate_ingest_freshness(
            fetch_ingest_health(
                app_base, trig.get("endpoint", "/api/marketdata/status")),
            trig["checks"],
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    elif ttype == "artifact_presence":
        reqs = trig["requirements"]
        res = evaluate_artifact_presence(scan_artifacts(reqs), reqs)
    elif ttype == "data_coverage":
        res = evaluate_data_coverage(
            fetch_data_coverage_max(trig["source"]), trig["threshold_date"])
    elif ttype == "csv_row_match":
        src = trig["source"]
        res = evaluate_csv_row_match(
            read_csv_rows(src), src["match"], src.get("label_columns"))
    elif ttype in ("info", "conditional_info"):
        # 手動判定/条件待ちの常時 watching エントリ (機械評価なし)。
        # 2026-07-14: e1-positioning-ingest-freshness (info) 追加に合わせ、
        # 既存 conditional_info と共に UNAVAILABLE (unknown type) 扱いだった
        # ものを watching に分類 (daily report のノイズ解消)。
        # 2026-08-19: deadline を無視して無期限 watching だったのを修正
        # (期日付き手動エントリが自分から期限切れを名乗れなかった)。
        res = evaluate_manual_info(
            trig.get("condition", ""), trig.get("deadline", "no-deadline"),
            today, trig.get("reachability", ""))
    else:
        res = {"state": STATE_UNAVAILABLE, "detail": f"unknown type: {ttype}"}
    return {"id": trig["id"], "doc": trig.get("doc", ""),
            "message": trig.get("message", ""), **res}


def evaluate_trigger(trig: dict[str, Any], *, today: str, app_base: str) -> dict[str, Any]:
    """1 エントリの評価を隔離する。

    2026-09-08: registry の 1 エントリ (roster-e2-silent-promoted-cells) が
    type に必要なフィールドを欠いていたため `trig["requirements"]` が
    KeyError を投げ、**51 エントリ全ての監視が 2 日間停止**した。1 件の
    不整合が全体を落とす設計は監視器として不可。壊れたエントリは自分だけ
    EVAL_ERROR を名乗り、残りは通常どおり評価される。
    """
    try:
        return _evaluate_trigger_impl(trig, today=today, app_base=app_base)
    except Exception as exc:  # noqa: BLE001 - 監視器を 1 件で落とさない境界
        return {"id": trig.get("id", "(no id)"), "doc": trig.get("doc", ""),
                "message": trig.get("message", ""),
                "state": STATE_ERROR,
                "detail": f"評価器が例外で停止: {type(exc).__name__}: {exc}"}


MACHINE_EVALUABLE_TYPES = {
    "price_below", "shadow_count_decision", "shadow_count_info",
    "live_count_decision", "deadline_info", "ingest_freshness",
    "artifact_presence", "data_coverage", "csv_row_match",
}


# type ごとに評価器が「必ず添字アクセスする」フィールド。
# 欠けたエントリは実行時 KeyError になるため、authoring 時に落とす。
REQUIRED_FIELDS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "price_below": ("symbol", "threshold"),
    "shadow_count_decision": ("entry_type", "since", "n_decide", "n_floor",
                              "deadline"),
    "shadow_count_info": ("entry_type", "since", "expected_per_week"),
    "live_count_decision": ("entry_type", "since", "n_decide", "deadline"),
    "deadline_info": ("deadline",),
    "ingest_freshness": ("checks",),
    "artifact_presence": ("requirements",),
    "data_coverage": ("source", "source.path", "threshold_date"),
    "csv_row_match": ("source", "source.path", "source.match"),
    "info": (),
    "conditional_info": (),
}

# コレクション型フィールドの要素スキーマ: (dotted path, 要素が持つべきキー)。
# 上の top-level 検査だけでは `requirements: [{}]` のような形が素通りし、
# 実行時に scan_artifacts / evaluate_ingest_freshness が KeyError を投げる
# (PR #227 Codex P2)。評価器が添字アクセスする深さまで authoring 時に見る。
# 空文字が「ワイルドカード (絞り込まない)」として正当な意味を持つフィールド。
# 例: hourblock-class-exempt-r2-rollback は entry_type="" で全戦略を対象にし、
# 母集団は reasons_marker で定義する。ただし**何かが母集団を定義している**ことは
# 下の ALTERNATIVE_FIELDS_BY_TYPE で必須にする — 両方空なら全 live トレードを
# 数える無言の過大計上になる (sr-anti-hunt 偽発火と同型)。
# 空文字が「絞り込まない」の正当な表明である絞り込み系フィールド。
# 型 (str) は要求するが空であること自体は違反にしない。
# 純粋な絞り込み (空 = 全件、母集団は entry_type が定義する) — 全 type 共通。
EMPTY_OK_FIELDS = frozenset({"instrument", "direction", "mode",
                             "reasons_marker"})

# entry_type 自体を空にできるのは、母集団を別の field が定義する type だけ。
# shadow_count 系は entry_type が唯一の母集団定義なので、空 + match:"prefix" は
# `startswith("")` で全 shadow トレードを数え判定を極端に早める
# (PR #227 Codex P2 10 巡目)。
EMPTY_ENTRY_TYPE_OK_TYPES = frozenset({"live_count_decision"})

# type ごとの「いずれか 1 つは非空でなければならない」トップレベル field 群。
ALTERNATIVE_FIELDS_BY_TYPE: dict[str, tuple[tuple[str, ...], ...]] = {
    "live_count_decision": (("entry_type", "reasons_marker"),),
}

# 各要素は (dotted path, 常に必要なキー, 「いずれか 1 つ」で足りるキー群)。
# ingest_freshness の check は prefix があれば key 不要、無ければ chk["key"] を
# 添字アクセスする — 「どちらか必須」を表現できないと片方の欠落を見逃す
# (PR #227 Codex P2 の 2 巡目)。
# dict 型の入れ子 spec — 中の既知フィールドは任意でも検査する。
# `source.label_columns: 1` は top-level 走査では見つからず、行が一致した
# 瞬間に TypeError になる (PR #227 Codex P2 10 巡目)。
#
# 値は**その spec 内で許可されるキー**の集合 = 評価器が実際に添字 / `get` する
# キーだけを列挙する (SSOT)。top-level と コレクション要素は
# reject-by-default にしたが、**その間の層**は素通りしていた:
# `source.date_colum` は lint を通り、`fetch_data_coverage_max` が
# `spec.get("date_column", "")` で空に落ちて日付列なしのまま毎日
# DATA_UNAVAILABLE を返し続ける (PR #227 Codex P2 14 巡目)。
# ⚠️ 「走査対象の一覧」と「許可キー」を**別の定数に分けない** — 14 巡目で
# 一度分けたら名前衝突で既存の走査を静かに壊した。1 本に保つこと。
NESTED_SPEC_ALLOWED_KEYS: dict[str, dict[str, frozenset[str]]] = {
    "data_coverage": {"source": frozenset({"path", "date_column"})},
    "csv_row_match": {"source": frozenset({"path", "match",
                                           "label_columns"})},
}

# コレクション要素内で**排他**の selector 群。少なくとも 1 つ必須
# (ALTERNATIVE 側) に加えて、2 つ以上あってはならない: 評価器は
# `if prefix:` で分岐するため `key` を黙って無視し、明示したキーが
# 完全に未監視になる (PR #227 Codex P2 18 巡目)。
EXCLUSIVE_ELEMENT_GROUPS: dict[str, tuple[tuple[str, ...], ...]] = {
    "ingest_freshness": (("key", "prefix"),),
}

# list[str] を要求するフィールド。
STRING_LIST_FIELDS = frozenset({"label_columns"})


# (dotted, 必須キー, 択一グループ, 任意キー)。任意キー = 評価器が
# `elem.get(...)` で読む field。ここに無いキーは**綴り違い**として落とす:
# `{"column": "n", "value": 10, "opp": ">"}` は要素キー allow-by-default だと
# lint を通り、_csv_row_predicate が op 既定値 "==" で**別の条件**を黙って
# 監視し続ける (PR #227 Codex P2 13 巡目 — top-level と同じ reject-by-default
# を要素レベルまで降ろす)。
COLLECTION_ELEMENT_FIELDS: dict[
    str,
    tuple[
        tuple[str, tuple[str, ...], tuple[tuple[str, ...], ...],
              tuple[str, ...]],
        ...,
    ],
] = {
    "artifact_presence": (
        ("requirements", ("path",), (), ("min_files", "label")),),
    "ingest_freshness": (
        ("checks", ("max_age_hours",), (("key", "prefix"),), ("min_keys",)),),
    "csv_row_match": (
        ("source.match", ("column", "value"), (), ("op",)),),
}


# 評価器が float()/int() で数値化するフィールド (dotted / 要素キー)。
# 値の型まで見ないと `max_age_hours: null` が lint を通り実行時に落ちる
# (PR #227 Codex P2 4 巡目)。
NUMERIC_FIELDS = frozenset({
    "threshold", "n_decide", "n_floor", "expected_per_week", "max_age_hours",
    "min_files", "min_keys",
})

# 評価器が文字列として扱うフィールド (Path.glob / 日付比較 / API パラメータ)。
# 型を見ないと `deadline: 123` が lint を通り `today > deadline` で TypeError、
# `path: 123` が Path.glob(123) で落ちる (PR #227 Codex P2 5 巡目)。
STRING_FIELDS = frozenset({
    "path", "deadline", "since", "symbol", "threshold_date", "key", "prefix",
    "column", "entry_type", "instrument", "direction", "reasons_marker",
    "mode", "date_column", "label", "endpoint",
})
# int() で消費される field。float() だけ通る "1.5" を素通りさせない
# (PR #227 Codex P2 6 巡目)。
INT_FIELDS = frozenset({"n_decide", "n_floor", "min_files", "min_keys"})

# 日付として比較される field。`deadline: "soon"` は文字列比較で常に
# `today > deadline` が false になり、**永久に watching のまま**期日に
# 到達しない — 「watching 表示を健全性の証拠と誤読する」ZN 教訓の型。
DATE_FIELDS = frozenset({"deadline", "since", "threshold_date"})
# **辞書順比較**される日付 field。評価器は `today > deadline` のように
# YYYY-MM-DD の today と文字列比較するので、`"2026-09-10T23:00:00"` は
# `"2026-09-10"` より辞書順で**後ろ**になり、期日当日に成立しない
# = 予定されたレビューが黙って 1 日以上遅れる (PR #227 Codex P2 17 巡目)。
# `since` は `fromisoformat` で**パースされる**ので datetime 可。
LEXICAL_DATE_FIELDS = frozenset({"deadline", "threshold_date"})
# sentinel を実装しているのは deadline を読む評価器だけ。
# threshold_date / since に "no-deadline" が入ると通常の ISO 日付と比較され
# 永久 WATCHING / DATA_UNAVAILABLE になる (PR #227 Codex P2 10 巡目)。
DATE_SENTINELS_BY_FIELD: dict[str, frozenset[str]] = {
    "deadline": frozenset({"no-deadline"}),
}
# sentinel 分岐を実際に実装しているのは evaluate_manual_info だけ
# (`deadline != "no-deadline"` を明示チェックする)。evaluate_deadline_info は
# `today > deadline` しか見ないので、"no-deadline" を渡すと永久 WATCHING に
# なる (PR #227 Codex P2 11 巡目)。deadline を消費しない type は無害なので許可。
DEADLINE_CONSUMING_TYPES = frozenset({"deadline_info", "info",
                                      "conditional_info",
                                      "shadow_count_decision",
                                      "live_count_decision"})
SENTINEL_OK_TYPES = frozenset({"info", "conditional_info"})

# 評価器が bool として消費するフィールド。`closed_only: "false"` は
# `bool(trig.get("closed_only"))` で **true** になり、監視母集団を黙って
# 変える (PR #227 Codex P2 8 巡目)。
BOOL_FIELDS = frozenset({"closed_only"})

# 評価器が `== 0` 等の値一致で消費するフィールド (文字列 "0" は一致しない)。
EXACT_INT_FIELDS = frozenset({"dedup_violation"})

# top-level のみで解釈される列挙フィールド (leaf 名 "match" は
# source.match のリストと衝突するので **top-level 限定**で扱う)。
ENUM_FIELDS: dict[str, frozenset[Any]] = {
    "match": frozenset({"prefix"}),
    "count_basis": frozenset({"unique"}),
    # 評価器は `trig.get("dedup_violation") == 0` でしか dedup を有効にしない。
    # 1 や 2 は黙って無視され重複行が母集団に入る (PR #227 Codex P2 12 巡目)。
    "dedup_violation": frozenset({0}),
}

# 空文字が正当なワイルドカードである field の enum。空なら絞り込まない
# (= ENUM_FIELDS には入れられない) が、**非空なら評価器が解釈できる値**
# でなければならない。`direction: "BYU"` は `t.get("direction") == "BYU"` が
# 全行 false になり、母集団が**黙って空**になる → N ベースの判定が永久に
# WATCHING に留まるか、低 N の deadline 分岐 (retire) を誤って踏む
# (PR #227 Codex P2 15 巡目)。ENUM_FIELDS と同じ「評価器が解釈する値だけ」
# の原則を、ワイルドカード許容 field にも適用する。
ENUM_FIELDS_IF_NONEMPTY: dict[str, frozenset[Any]] = {
    "direction": frozenset({"BUY", "SELL"}),
}

# 非空なら形が決まっている field の正規表現。instrument は新ペア追加が
# 常時ありうるので閉じた enum にはできないが、**形**は OANDA の
# `CCY_CCY` に固定されている。`USDJPY` / `USD_JPYY` のような綴り違いは
# 同じ「母集団が黙って空になる」故障を起こすので形で落とす
# (値そのものの妥当性は落とせない — 限界を明示しておく)。
SHAPE_IF_NONEMPTY: dict[str, str] = {
    "instrument": r"^[A-Z]{3}_[A-Z]{3}$",
    # `fetch_ingest_health` は `f"{app_base}{endpoint}"` と**素の連結**をする。
    # `"api/..."` だと `https://host.comapi/...` という壊れた URL になり、
    # lint は通ったまま毎日 DATA_UNAVAILABLE を返し続ける
    # (PR #227 Codex P2 17 巡目)。絶対パスを要求する。
    "endpoint": r"^/[^\s]*$",
}

# `mode` は `/api/demo/trades` へ素通しされ、open/closed 両経路で完全一致に
# 使われる。`mode: "daytrade_eurgpp"` は API 呼び出しが**成功して 0 行**を
# 返すので、判定は永久 WATCHING か低 N の deadline 分岐を誤って踏む
# (Codex P2 16 巡目 — direction/instrument と同クラスの 3 例目)。
#
# 許可集合は**ハンドコピーせず** `modules/demo_trader.py` の `MODE_CONFIG` を
# AST で読む (9 巡目の学び: lint は評価器の写しなので写し間違いが必ず起きる)。
# import しないのは demo_trader の import が本番スレッドを起動しうるため。
DEMO_TRADER_PATH = ROOT / "modules" / "demo_trader.py"

# MODE_CONFIG から退役したが registry が参照し続けてよい歴史的 mode。
# 退役 mode を持つ既存エントリを壊さずに guard を入れるための明示的な逃げ道。
# ⚠️ ここに足すのは「その mode の行が DB に残っていて母集団として正当」な
# 場合のみ。単に綴りを通したいだけなら足さないこと。
HISTORICAL_MODES: frozenset[str] = frozenset()


def app_mode_names(path: Path | None = None) -> frozenset[str]:
    """`MODE_CONFIG` のキー = アプリが実際に produce しうる mode 名。

    読めない/形が違う場合は **例外**。空集合に畳むと「mode の検査をした」と
    「検査できなかった」が区別できなくなる (本ファイル全体の不変条件)。
    """
    target = path or DEMO_TRADER_PATH
    tree = ast.parse(target.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if getattr(t, "id", None) == "MODE_CONFIG":
                if not isinstance(node.value, ast.Dict):
                    raise RuntimeError(
                        f"{target}: MODE_CONFIG が dict literal でない — "
                        "mode の許可集合を導出できない")
                names = {k.value for k in node.value.keys
                         if isinstance(k, ast.Constant)
                         and isinstance(k.value, str)}
                if len(names) != len(node.value.keys):
                    raise RuntimeError(
                        f"{target}: MODE_CONFIG に非文字列リテラルのキーが"
                        "ある — 許可集合が不完全になる")
                return frozenset(names)
    raise RuntimeError(f"{target}: MODE_CONFIG が見つからない")

# 各カウント field の下限 (評価器の意味論)。n_decide=-1 は即時 TRIGGERED、
# min_files=-1 は不在の成果物を「充足」と報告する。
INT_MIN = {"n_decide": 1, "n_floor": 0, "min_files": 1, "min_keys": 1}

# int() を経ない (float のまま使われる) 数値 field の**下限 (排他)**。
# INT_FIELDS は INT_MIN 側で見ているので、ここは float のまま比較に入る
# field だけを持つ。非正値は「型は通るが比較の意味が反転/到達不能」になる:
#   max_age_hours <= 0 → `age > max_h` が常に true = 1 秒前の記録まで stale
#     と報告し、毎日 false TRIGGERED を出す (PR #227 Codex P2 13 巡目)
#   threshold <= 0     → FX 価格として到達不能 = 永久 watching (期日が来ない)
FLOAT_MIN_EXCLUSIVE = {"max_age_hours": 0.0, "threshold": 0.0}
# 下限 (包含)。0/週 を期待値に置くのは authoring 誤りだが gate はしないので
# 負値のみ落とす。
FLOAT_MIN_INCLUSIVE = {"expected_per_week": 0.0}

# 全 type 共通のメタデータ (評価に使われないが台帳として必要)。
META_FIELDS = frozenset({
    "id", "active", "type", "doc", "message", "condition", "reachability",
    "resolved", "resolved_at", "resolution", "eval_record", "note", "notes",
    # 実行主体メタ (2026-09-10 救済時に main 側 ps-seat-supply-remeasure-30d が
    # 既に使用): 評価器は読まないが「誰が/何で状態を進めるか」を台帳に運ぶ。
    # ad-hoc な日付付きキー (診断スナップショット等) はここに足さず
    # `note` の下に入れ子で置くこと — reject-by-default を保つ。
    "harness", "execution_command", "execution_subject",
})

# type ごとに評価器が実際に読む selector。ここに無いキーは**綴り違い**として
# 落とす。`instrumnt: "USD_JPY"` は黙って無視され全ペアを計上する
# (PR #227 Codex P2 12 巡目) — allow-by-default をやめ reject-by-default へ。
OPTIONAL_FIELDS_BY_TYPE: dict[str, frozenset[str]] = {
    "price_below": frozenset(),
    "shadow_count_decision": frozenset({
        "instrument", "direction", "match", "mode", "count_basis",
        "closed_only", "dedup_violation"}),
    "shadow_count_info": frozenset({"instrument", "direction", "match", "mode",
                                    "count_basis"}),
    "live_count_decision": frozenset({"instrument", "direction", "match",
                                      "reasons_marker"}),
    "deadline_info": frozenset(),
    "ingest_freshness": frozenset({"endpoint"}),
    "artifact_presence": frozenset({"deadline"}),
    "data_coverage": frozenset({"deadline"}),
    "csv_row_match": frozenset({"deadline"}),
    "info": frozenset({"deadline"}),
    "conditional_info": frozenset({"deadline"}),
}


# 値の形が分かっている全フィールド。必須/任意・top-level/要素を問わず
# 存在すれば検査する唯一の集合 (軸ごとに検査漏れを作らないため)。
KNOWN_VALUE_FIELDS = (NUMERIC_FIELDS | STRING_FIELDS | DATE_FIELDS
                      | BOOL_FIELDS | EXACT_INT_FIELDS)

# 注: "match" は leaf 名が衝突する — shadow/live count 系では文字列 "prefix"、
# csv_row_match では述語のリスト。leaf 名だけでは型を決められないので
# STRING_FIELDS には入れない。


def _unusable_reason(field: str, value: Any, *,
                     empty_ok: frozenset[str] = EMPTY_OK_FIELDS,
                     date_sentinels: frozenset[str] = frozenset()) -> str | None:
    """必須値が「存在するが評価器が使えない」ケースを名指しする。

    presence だけの検査は `path: null` / `max_age_hours: null` を通してしまい、
    scan_artifacts の Path.glob(None) や float(None) が daily 実行時に落ちる。
    """
    leaf = field.rsplit(".", 1)[-1]
    if value is None:
        return "null"
    if isinstance(value, str) and not value.strip():
        # 絞り込み系は空 = ワイルドカードが正当 (母集団が誰かに定義されて
        # いることは ALTERNATIVE_FIELDS_BY_TYPE 側で別途担保する)。
        return None if leaf in empty_ok else "空文字"
    if isinstance(value, (list, dict)) and not value:
        return "空のコレクション"
    if leaf in BOOL_FIELDS:
        if not isinstance(value, bool):
            return (f"bool でない ({type(value).__name__}: {value!r}) — "
                    'bool("false") は true になり母集団が黙って変わる')
        return None
    if leaf in EXACT_INT_FIELDS:
        if isinstance(value, bool) or not isinstance(value, int):
            return (f"int でない ({type(value).__name__}: {value!r}) — "
                    "評価器は値一致 (== 0) で比較する")
        return None
    if leaf in NUMERIC_FIELDS:
        if isinstance(value, bool):
            return f"数値でなく bool ({value!r})"
        try:
            num = float(value)
        except (TypeError, ValueError, OverflowError):
            return f"数値化できない ({value!r})"
        if leaf in INT_FIELDS:
            # 評価器と**同じ変換** (int(value)) で検査する。float 経由だと
            # `"1.0"` が通り int("1.0") が ValueError になる
            # (PR #227 Codex P2 9 巡目)。lint は評価器の写しではなく
            # 評価器と同じ呼び出しをすること。
            try:
                as_int = int(value)
            except (TypeError, ValueError, OverflowError):
                return f"int() で変換できない ({value!r})"
            if not math.isfinite(num) or num != as_int:
                return f"整数でない ({value!r}) — int() が黙って切り捨てる"
            low = INT_MIN.get(leaf, 0)
            if as_int < low:
                return (f"下限 {low} 未満 ({value!r}) — "
                        "閾値が即時成立/常時充足になる")
        # nan/inf は変換は通るが比較を静かに壊す: max_age_hours=nan は
        # `age > max_h` が常に false になり、古い ingest を fresh と報告する
        # (PR #227 Codex P2 7 巡目)。
        if not math.isfinite(num):
            return f"有限数でない ({value!r}) — 比較が静かに壊れる"
        low_x = FLOAT_MIN_EXCLUSIVE.get(leaf)
        if low_x is not None and num <= low_x:
            return (f"{low_x:g} 以下 ({value!r}) — "
                    "比較の向きが反転し常時成立/到達不能になる")
        low_i = FLOAT_MIN_INCLUSIVE.get(leaf)
        if low_i is not None and num < low_i:
            return f"{low_i:g} 未満 ({value!r}) — 期待レートが負になる"
    elif leaf in STRING_FIELDS and not isinstance(value, str):
        return f"文字列でない ({type(value).__name__}: {value!r})"
    if leaf in DATE_FIELDS and isinstance(value, str):
        # 評価器は**元の文字列**を消費するので、lint 側で strip して
        # 判定すると `" 2026-09-10"` が通る。先頭空白は辞書順で数字より
        # 前に来るため `today > deadline` が常に真 = **前日から期限切れ**扱い
        # になり、`since` では `fromisoformat` が落ちて DATA_UNAVAILABLE
        # (PR #227 Codex P2 18 巡目)。**書かれたまま**の正準性を要求する。
        if value != value.strip():
            return (f"前後に空白がある ({value!r}) — 評価器は strip しないので"
                    "辞書順比較が前倒しになり、パースは失敗する")
        v = value.strip()
        if (leaf in LEXICAL_DATE_FIELDS and v not in date_sentinels
                and len(v) != 10 and _is_iso_date(v)):
            return (f"日付のみ (YYYY-MM-DD) でない ({value!r}) — この field は "
                    "today と**辞書順比較**されるので時刻が付くと期日当日に"
                    "成立せず、判定が黙って遅れる")
        if v not in date_sentinels and not _is_iso_date(v):
            return (f"日付として解釈できない ({value!r}) — "
                    "文字列比較で永久に watching になる")
    return None


def _is_iso_date(value: str) -> bool:
    """評価器が today (YYYY-MM-DD) と辞書順比較し、since は fromisoformat する。

    2026-09-08 (PR #227 Codex P2 8 巡目): 先頭 10 文字だけ見て残りを
    素通りさせると `2026-01-01Tgarbage` が lint を通り、
    fromisoformat() が毎回 DATA_UNAVAILABLE を返し続ける。**全体**を解釈する。
    """
    try:
        d = datetime.strptime(value[:10], "%Y-%m-%d")
        if len(value) > 10:
            datetime.fromisoformat(value)
    except ValueError:
        return False
    # strptime は `2026-9-1` を受けるが辞書順比較では 2026-12-31 より後ろに
    # なり、期限切れが永久 WATCHING になる。**正準形 (0 埋め) を要求する**
    # (PR #227 Codex P2 9 巡目)。
    return value[:10] == d.strftime("%Y-%m-%d")


def _scalar_predicate_reason(value: Any) -> str | None:
    """CSV 述語の `value` はスカラー限定 (PR #227 Codex P2 17 巡目)。

    `_csv_row_predicate` は数値なら `float()`、それ以外は `str()` で潰すので
    dict / list を渡すと「`{'a': 1}` という文字列」との比較になる。
    `op: "!="` ならほぼ全ての通常値に一致し**偽 TRIGGERED** を出す。
    """
    if value is None:
        return "null"
    if isinstance(value, (dict, list, tuple, set)):
        return f"コレクション ({type(value).__name__})"
    if isinstance(value, bool):
        return None  # str(True) との比較は意図的に使える
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            return f"有限数でない ({value!r}) — 比較が静かに壊れる"
        return None
    if isinstance(value, str):
        return None
    return f"スカラーでない ({type(value).__name__})"


def _get_path(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        cur = cur[part]
    return cur


def _has_path(obj: Any, dotted: str) -> bool:
    """"a.b" 形式のネストしたキー存在チェック (評価器の添字と同じ深さで見る)。"""
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def lint_schema(triggers: list[dict[str, Any]]) -> list[str]:
    """type が要求するフィールドの欠落を authoring 時に検出する。

    2026-09-08: artifact_presence を名乗りながら requirements を持たない
    エントリが main に着地し、daily の trigger watch 全体 (51 件) が
    KeyError で 2 日間停止した。lint_reachability は機械評価型を素通り
    させる設計だったため、この層に穴が空いていた。
    """
    errors: list[str] = []
    for t in triggers:
        tid = t.get("id", "(no id)")
        ttype = t.get("type")
        # id は全 type 共通の必須。_evaluate_trigger_impl が trig["id"] を
        # 添字アクセスするので、欠けると daily 実行時 EVAL_ERROR になる
        # (PR #227 Codex P2)。
        if "active" in t and not isinstance(t["active"], bool):
            errors.append(
                f"{tid}: active が bool でない "
                f"({type(t['active']).__name__}: {t['active']!r}) — "
                'truthiness で消費されるので "false" は true になる')
        if not str(t.get("id", "")).strip():
            errors.append(
                f"(no id): id が無い/空 — 評価器が trig[\"id\"] を添字アクセスする")
            continue
        if ttype not in REQUIRED_FIELDS_BY_TYPE:
            errors.append(f"{tid}: unknown type {ttype!r} — 評価器が無い")
            continue
        missing = [f for f in REQUIRED_FIELDS_BY_TYPE[ttype]
                   if not _has_path(t, f)]
        if missing:
            errors.append(
                f"{tid}: type={ttype} に必須の {missing} が無い — "
                "実行時 KeyError で監視器全体が落ちる")
            continue
        # 必須だけでなく **存在する既知フィールドを全て** 検査する。
        # 「必須は見るが任意は見ない」「top-level は見るが要素は見ない」で
        # 同じ欠陥クラスを 3 巡繰り返したため、両軸を統一した
        # (PR #227 Codex P2 7 巡目)。
        present = [f for f in REQUIRED_FIELDS_BY_TYPE[ttype] if _has_path(t, f)]
        present += [k for k in t if k in KNOWN_VALUE_FIELDS and k not in present]
        empty_ok = EMPTY_OK_FIELDS
        if ttype in EMPTY_ENTRY_TYPE_OK_TYPES:
            empty_ok = empty_ok | {"entry_type"}
        for f in present:
            leaf = f.rsplit(".", 1)[-1]
            sentinels = DATE_SENTINELS_BY_FIELD.get(leaf, frozenset())
            # sentinel は「実装している評価器」+「その field を消費しない
            # type」でのみ許可する。
            if (sentinels and ttype in DEADLINE_CONSUMING_TYPES
                    and ttype not in SENTINEL_OK_TYPES):
                sentinels = frozenset()
            why = _unusable_reason(
                f, _get_path(t, f), empty_ok=frozenset(empty_ok),
                date_sentinels=sentinels)
            if why:
                errors.append(
                    f"{tid}: type={ttype} の {f} が使えない値 ({why}) — "
                    "評価器が実行時に落ちる")
        for f, allowed in ENUM_FIELDS_IF_NONEMPTY.items():
            v = t.get(f)
            if isinstance(v, str) and v.strip() and v not in allowed:
                errors.append(
                    f"{tid}: type={ttype} の {f}={v!r} は評価器が解釈しない値 "
                    f"— 解釈するのは {sorted(allowed)} のみ (空文字 = 絞り込まない)。"
                    "綴り違いは母集団が**黙って空**になり、N ベースの判定が"
                    "永久 WATCHING か低 N の retire 分岐を誤って踏む")
        mode_v = t.get("mode")
        if isinstance(mode_v, str) and mode_v.strip():
            allowed_modes = app_mode_names() | HISTORICAL_MODES
            if mode_v not in allowed_modes:
                near = sorted(m for m in allowed_modes
                              if m.startswith(mode_v[:6]))
                errors.append(
                    f"{tid}: type={ttype} の mode={mode_v!r} は "
                    "MODE_CONFIG に無い — API 呼び出しは成功して **0 行**を"
                    "返すので、判定が永久 WATCHING か低 N の retire 分岐を"
                    f"誤って踏む{f' (近い mode: {near})' if near else ''}")
        for f, pattern in SHAPE_IF_NONEMPTY.items():
            v = t.get(f)
            if isinstance(v, str) and v.strip() and not re.match(pattern, v):
                errors.append(
                    f"{tid}: type={ttype} の {f}={v!r} は形が {pattern} に"
                    "合わない — 綴り違いなら母集団が黙って空になる")
        for f, allowed in ENUM_FIELDS.items():
            if f in t and t[f] not in allowed:
                errors.append(
                    f"{tid}: type={ttype} の {f}={t[f]!r} は未知の値 — "
                    f"評価器が解釈するのは {sorted(allowed)} のみ "
                    "(綴り違いは黙って無効化される)")
        for group in ALTERNATIVE_FIELDS_BY_TYPE.get(ttype, ()):
            if not any(str(t.get(k) or "").strip() for k in group):
                errors.append(
                    f"{tid}: type={ttype} は {list(group)} のいずれかが"
                    "非空で必須 — 全て空だと母集団が定義されず過大計上する")
        for spec_key in NESTED_SPEC_ALLOWED_KEYS.get(ttype, {}):
            spec = t.get(spec_key)
            if not isinstance(spec, dict):
                continue
            for k, v in spec.items():
                if k in STRING_LIST_FIELDS:
                    if not (isinstance(v, list) and v
                            and all(isinstance(x, str) and x.strip()
                                    for x in v)):
                        errors.append(
                            f"{tid}: {spec_key}.{k} が非空の文字列リストでない "
                            f"({v!r}) — 評価器が要素を走査して落ちる")
                elif k in KNOWN_VALUE_FIELDS:
                    why = _unusable_reason(
                        k, v, date_sentinels=DATE_SENTINELS_BY_FIELD.get(
                            k, frozenset()))
                    if why:
                        errors.append(
                            f"{tid}: {spec_key}.{k} が使えない値 ({why}) — "
                            "評価器が実行時に落ちる")
        allowed = (META_FIELDS | OPTIONAL_FIELDS_BY_TYPE.get(ttype, frozenset())
                   | {f.split(".", 1)[0] for f in REQUIRED_FIELDS_BY_TYPE[ttype]})
        for k in sorted(set(t) - allowed):
            errors.append(
                f"{tid}: type={ttype} に未知のキー {k!r} — 評価器は読まないので "
                "綴り違いなら母集団が黙って広がる (許可キー: "
                f"{sorted(allowed - META_FIELDS)} + メタ)")
        errors.extend(_lint_nested_specs(t, tid, ttype))
        errors.extend(_lint_collections(t, tid, ttype))
    return errors


def _lint_nested_specs(t: dict[str, Any], tid: str,
                       ttype: str) -> list[str]:
    """ネストした dict spec の未知キーを落とす (reject-by-default の 3 層目)。"""
    errors: list[str] = []
    for dotted, allowed in NESTED_SPEC_ALLOWED_KEYS.get(ttype, {}).items():
        spec = _get_path(t, dotted)
        if not isinstance(spec, dict):
            continue  # 形の検査は REQUIRED_FIELDS_BY_TYPE 側の責務
        for k in sorted(set(spec) - allowed):
            errors.append(
                f"{tid}: {dotted}.{k} は未知のキー — 評価器は読まないので、"
                "綴り違いなら既定値に落ちて毎日 DATA_UNAVAILABLE を返し"
                f"続ける (許可キー: {sorted(allowed)})")
    return errors


def _lint_collections(t: dict[str, Any], tid: str, ttype: str) -> list[str]:
    """コレクション型フィールドの形と要素キーを検査する。"""
    errors: list[str] = []
    for dotted, keys, alternatives, optional in COLLECTION_ELEMENT_FIELDS.get(
            ttype, ()):
        allowed = (set(keys) | set(optional)
                   | {k for g in alternatives for k in g})
        coll = _get_path(t, dotted)
        if not isinstance(coll, list) or not coll:
            errors.append(
                f"{tid}: type={ttype} の {dotted} が非空のリストでない "
                f"({type(coll).__name__}) — 評価器が要素を走査できない")
            continue
        for i, elem in enumerate(coll):
            if not isinstance(elem, dict):
                errors.append(
                    f"{tid}: {dotted}[{i}] が dict でない "
                    f"({type(elem).__name__})")
                continue
            lack = [k for k in keys if k not in elem]
            if lack:
                errors.append(
                    f"{tid}: {dotted}[{i}] に必須の {lack} が無い — "
                    "実行時 KeyError")
            # 必須キーだけでなく、要素に**存在する**既知フィールドは全て
            # 型検査する。min_files / min_keys は任意だが評価器が int() する
            # ので null が入ると実行時 TypeError になる (PR #227 Codex P2)。
            checked = set(keys) | {k for g in alternatives for k in g}
            checked |= {k for k in elem if k in KNOWN_VALUE_FIELDS}
            for k in sorted(checked):
                if k in elem:
                    why = _unusable_reason(
                        k, elem[k],
                        date_sentinels=DATE_SENTINELS_BY_FIELD.get(
                            k, frozenset()))
                    if why:
                        errors.append(
                            f"{tid}: {dotted}[{i}].{k} が使えない値 ({why}) — "
                            "評価器が実行時に落ちる")
            for k in sorted(set(elem) - allowed):
                errors.append(
                    f"{tid}: {dotted}[{i}] に未知のキー {k!r} — 評価器は"
                    "読まないので、綴り違いなら既定値で**別の条件**を"
                    f"黙って監視し続ける (許可キー: {sorted(allowed)})")
            if dotted == "source.match" and "value" in elem:
                why = _scalar_predicate_reason(elem["value"])
                if why:
                    errors.append(
                        f"{tid}: {dotted}[{i}].value が使えない値 ({why}) — "
                        "評価器は str()/float() で潰すので、コレクションは"
                        "ほぼ全ての通常値に `!=` で一致し偽 TRIGGERED を出す")
            if "op" in elem and elem["op"] not in _CSV_OPS:
                errors.append(
                    f"{tid}: {dotted}[{i}].op={elem['op']!r} は未知の演算子 — "
                    f"評価器は {sorted(_CSV_OPS)} のみ解釈し、"
                    "それ以外は毎日 DATA_UNAVAILABLE を返し続ける")
            for group in EXCLUSIVE_ELEMENT_GROUPS.get(ttype, ()):
                present = [k for k in group
                           if str(elem.get(k) or "").strip()]
                if len(present) > 1:
                    errors.append(
                        f"{tid}: {dotted}[{i}] は {list(group)} の"
                        f"**どちらか一方のみ**指定すること (両方あり: {present}) "
                        "— 評価器は `if prefix:` で分岐するので key は黙って"
                        "無視され、明示したキーが完全に未監視になる")
            for group in alternatives:
                # 存在だけでは足りない: evaluate_ingest_freshness は
                # `if prefix:` で分岐するので prefix="" は key 側へ落ち、
                # 欠けた chk["key"] を添字アクセスする (PR #227 Codex P2)。
                # 評価器の truthiness と同じ判定で見る。
                if not any(str(elem.get(k) or "").strip() for k in group):
                    errors.append(
                        f"{tid}: {dotted}[{i}] は {list(group)} の"
                        "いずれか 1 つが**非空の値**で必須 — "
                        "空文字は評価器の分岐で false 扱いになり KeyError")
    return errors


def lint_registry(triggers: list[dict[str, Any]] | None = None) -> list[str]:
    """authoring 時 lint の入口 (schema + 到達経路)。

    既定は **active フィルタ前**の全エントリ — `active` 自身の不正や、
    誤って falsey になって消えたエントリを見るため。
    """
    if triggers is None:
        triggers = load_registry_raw()
    return lint_schema(triggers) + lint_reachability(triggers)


def lint_reachability(triggers: list[dict[str, Any]]) -> list[str]:
    """到達経路 lint — 「条件を書いた」だけで前進経路が無いエントリを検出。

    ZN 教訓 (2026-08-14) の再発防止。機械評価型でない (= 人手判定の)
    エントリは、誰/どのジョブが状態を進めるかを reachability に明記させる。
    これが無いと watching 表示が健全性の証拠と誤読される。
    """
    errors: list[str] = []
    for t in triggers:
        ttype = t.get("type")
        if ttype in MACHINE_EVALUABLE_TYPES:
            continue
        if ttype not in ("info", "conditional_info"):
            errors.append(f"{t['id']}: unknown type {ttype!r}")
            continue
        if not str(t.get("reachability", "")).strip():
            errors.append(
                f"{t['id']}: 手動判定エントリに reachability (到達経路) が無い — "
                "誰/どのジョブが状態を進めるかを明記せよ")
    return errors


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
        # 評価器自身の故障。DATA_UNAVAILABLE に混ぜると「取れなかった」と
        # 「壊れている」が区別できなくなる。
        "errors": [r for r in results if r["state"] == STATE_ERROR],
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
    if report.get("errors"):
        lines.append("### 🔴 EVAL ERROR — 監視器自身の故障 (registry を直せ)")
        for r in report["errors"]:
            lines.append(f"- **{r['id']}**: {r['detail']}")
    if not any((report["triggered"], report["watching"], report["unavailable"],
                report.get("errors"))):
        lines.append("- (active な trigger なし)")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Pre-reg trigger watch")
    ap.add_argument("--lint", action="store_true",
                    help="registry lint のみ実行 (schema + 到達経路、違反で exit 1)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.lint:
        errors = lint_registry()
        for e in errors:
            print(f"ERROR {e}", file=sys.stderr)
        print(f"registry lint (schema + 到達経路): {len(errors)} 件の違反")
        return 1 if errors else 0
    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(to_markdown(report))
    # 評価器が壊れているときは exit code でも名乗る (呼び出し側が
    # 「壊れた」と「異常なし」を区別できるように)。
    return 2 if report.get("errors") else 0


if __name__ == "__main__":
    sys.exit(main())
