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

def load_registry(path: Path = REGISTRY_PATH) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [t for t in data.get("triggers", []) if t.get("active", True)]


def evaluate_trigger(trig: dict[str, Any], *, today: str, app_base: str) -> dict[str, Any]:
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
        res = evaluate_shadow_count_info(
            fetch_shadow_count(trig["entry_type"], trig["since"], app_base,
                               prefix=trig.get("match") == "prefix",
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


MACHINE_EVALUABLE_TYPES = {
    "price_below", "shadow_count_decision", "shadow_count_info",
    "live_count_decision", "deadline_info", "ingest_freshness",
    "artifact_presence", "data_coverage", "csv_row_match",
}


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
    ap.add_argument("--lint", action="store_true",
                    help="到達経路 lint のみ実行 (違反があれば exit 1)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.lint:
        errors = lint_reachability(load_registry())
        for e in errors:
            print(f"ERROR {e}", file=sys.stderr)
        print(f"到達経路 lint: {len(errors)} 件の違反")
        return 1 if errors else 0
    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(to_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
