#!/usr/bin/env python3
"""
Tier C: 異常検知・通知 (15分毎 cron 実行)

Protocol: knowledge-base/wiki/analyses/daily-tierB-protocol.md §6

使用:
    python3 scripts/anomaly_watcher.py              # 1回実行 (cron想定)
    python3 scripts/anomaly_watcher.py --json       # machine-readable

検知項目:
    1. Spread > 2×30d median (per instrument)
    2. OANDA order latency > 3s
    3. Session volume drift (Tokyo <50% of median)
    4. Live N stagnation (市場オープン時間換算で24h増加0件)
    5. Render Disk 使用率 (warn/critical) — 2026-08-26 追加
    6. DB 書込み失敗 (disk_status の write_probe 実測) — 2026-08-26 追加
    7. シグナル評価の停止 (候補行の鮮度、市場オープン6h) — 2026-08-27 追加

**禁止事項**:
    - 判断しない (昇格/降格推奨は出さない)
    - 自動変更しない
    - 仮説生成しない (必要ならTier Bにエスカレート)

出力:
    - stdout に全イベントを 1 行 JSON で出力 — Render cron はクローンごと
      破棄されるため、cron の stdout ログが事実上の恒久記録
    - knowledge-base/raw/anomalies/YYYY-MM-DD.jsonl に追加 (ローカル実行時
      のみ残る。Render cron 上では実行終了とともに消える)
    - Discord 通知 (閾値超え時のみ。継続性イベントは時間バケットで抑制)
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
API_BASE = os.environ.get("API_BASE", "https://fx-ai-trader.onrender.com")

SPREAD_MULTIPLIER_THRESHOLD = 2.0
LATENCY_THRESHOLD_SEC = 3.0
SESSION_VOLUME_RATIO_THRESHOLD = 0.5
N_STAGNATION_HOURS = 24
# 候補行 (バー評価ごと) の停止閾値。実測根拠は check_candidate_stagnation
# の docstring 参照 (自然な最大無風 2.0h の 3 倍を取った暫定値)。
CANDIDATE_STAGNATION_HOURS = 6
# 書込み停止は「取引ゼロ」として現れるが、取引ゼロには市場が閉まっている
# だけの週末も含まれる。そこで検知は2本立てにする (rule:R3, 2026-08-26):
#   - live_n_stagnation: 取引時刻ベース。ただし FX 週末閉場 (金 21:00 →
#     日 21:00 UTC) を除いた「市場オープン時間」で 24h を数える。実時間で
#     数えると金曜夕方の最終取引が毎週末必ず閾値を越えて誤発火する
#   - db_write_failed: /api/admin/disk_status 応答時の実 INSERT (write_probe)
#     の成否。満杯型書込み停止の直接検知で、検知遅延はポーリング間隔の
#     15 分。mtime ベースの staleness は再起動の checkpoint でリセットされ、
#     ENOSPC 下でも確保済み WAL ブロックへの再書込みで前進するため採らない
FX_WEEKEND_CLOSE_HOURS = 48  # 金 21:00 UTC → 日 21:00 UTC

# Discord 通知の時間バケット抑制 (rule:R3, 2026-08-26)。Render cron は毎回
# クリーンな環境で走り「前回いつ通知したか」を保存できないため、レベル
# 変化検知ではなく決定的な時間バケットで通知量に上限を設ける: バケット
# 先頭の cron スロットに当たった実行だけが通知する (warn 最大4通/日、
# critical 最大24通/日)。既知の限界 (許容する妥協):
#   - 初報が最大 1 バケット遅れる (15分ポーリング自体の遅延と同オーダー)
#   - バケット先頭の run 自体が落ちるとそのバケットは無通知になり、次の
#     バケット先頭まで持ち越す。cron run の失敗自体は Render の
#     notifyOnFail が別経路で通知する
# 抑制されても検知自体は毎回 stdout に 1 行 JSON で出る (下記 main 参照)。
# ここに無い type (一過性イベント) は無条件に通知する。
CRON_INTERVAL_MIN = 15  # render.yaml: fx-ai-tier-c-anomaly は */15
NOTIFY_EVERY_HOURS = {
    "disk_capacity:warn": 6,
    "disk_capacity:critical": 1,
    "backup_blocked_low_disk": 1,
    "db_write_failed": 1,
    "live_n_stagnation": 6,
    "stagnation_check_broken": 6,
    "candidate_stagnation": 6,
    "candidate_freshness_error": 6,
}
# Discord に流さない type。write_probe_missing はデプロイ直後の cron/web
# バージョン不一致で必ず一度は起きる (cron は数十秒で新コード化、web は
# build 完了まで旧 API を返す)。web が旧版のまま固着するケースは Render の
# デプロイ失敗通知が受け持つので、ここは記録のみに降格する。
NOTIFY_NEVER = {"write_probe_missing", "candidate_freshness_missing"}


def fetch_json(path: str, timeout: int = 15) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"⚠️  fetch failed: {url} — {e}", file=sys.stderr)
        return {}


# ── 検知ロジック ────────────────────────────────────────

def check_spread_spike(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """instrument別に最新spread vs 30日median比を計算。"""
    events = []
    by_inst: dict[str, list[float]] = {}
    for t in trades:
        inst = t.get("instrument")
        sp = t.get("spread_at_entry")
        if inst and sp is not None and "XAU" not in inst:
            by_inst.setdefault(inst, []).append(float(sp))

    for inst, spreads in by_inst.items():
        if len(spreads) < 10:
            continue
        median = statistics.median(spreads[:-5]) if len(spreads) > 5 else statistics.median(spreads)
        latest = statistics.mean(spreads[-5:]) if len(spreads) >= 5 else spreads[-1]
        if median > 0 and latest / median >= SPREAD_MULTIPLIER_THRESHOLD:
            events.append(
                {
                    "type": "spread_spike",
                    "instrument": inst,
                    "latest_mean_5": round(latest, 2),
                    "median_30d": round(median, 2),
                    "ratio": round(latest / median, 2),
                }
            )
    return events


def check_oanda_latency(oanda_status: dict[str, Any]) -> list[dict[str, Any]]:
    """OANDA API最近の平均latency。"""
    events = []
    latency = oanda_status.get("avg_order_latency_sec")
    if latency is not None and float(latency) > LATENCY_THRESHOLD_SEC:
        events.append(
            {
                "type": "oanda_latency",
                "latency_sec": float(latency),
                "threshold": LATENCY_THRESHOLD_SEC,
            }
        )
    return events


def _market_open_hours(start: datetime, end: datetime) -> float:
    """[start, end] の実時間から FX 週末閉場 (金 21:00 → 日 21:00 UTC) を除いた時間数。

    閉場境界は夏時間で 21:00/22:00 と揺れるが、24h 閾値に対する ±1h の
    誤差は無害なので UTC 21:00 固定とする。
    """
    if end <= start:
        return 0.0
    total = (end - start).total_seconds() / 3600.0
    closed = 0.0
    # start 以前で最も近い金曜 21:00 UTC に錨を置き、週単位で閉場窓を歩く
    anchor = (start - timedelta(days=(start.weekday() - 4) % 7)).replace(
        hour=21, minute=0, second=0, microsecond=0
    )
    if anchor > start:
        anchor -= timedelta(days=7)
    while anchor < end:
        overlap = (
            min(end, anchor + timedelta(hours=FX_WEEKEND_CLOSE_HOURS)) - max(start, anchor)
        ).total_seconds() / 3600.0
        if overlap > 0:
            closed += overlap
        anchor += timedelta(days=7)
    return total - closed


def check_live_n_stagnation(
    status: dict[str, Any], trades: list[dict[str, Any]], now: datetime | None = None
) -> list[dict[str, Any]]:
    """DB への最終書込みからの経過時間で書込み停止を検知する (rule:R3, 2026-08-26).

    **この検知器は 2026-04-22 の作成以来 126 日間 no-op だった。**
    ``status["last_trade_time"]`` を読んでいたが、その key は
    ``/api/demo/status`` にも app.py のどこにも存在しない (全数 grep で
    生成箇所ゼロ)。docstring 自身が「あると仮定。無ければ skip」と書いて
    おり、その仮定は一度も検証されなかった → 常に ``[]`` を返していた。

    代償は実測済み: 2026-08-21〜08-25 に Render Disk 満杯で全 SQLite 書込み
    が 3.5 日停止した際、本来これが鳴るはずだったが沈黙した。ZN 教訓
    (計装契約バグ) の 5 例目・「読まれない計装は劣化を検知できない」の
    直系。

    現行の実装は trades API の実データ (``/api/demo/trades`` の最新行) から
    時刻を取るので、field 契約は呼び出し側で観測可能な形になっている。
    時刻が 1 件も読めない場合は ``no_timestamp_field`` を **異常として報告
    する** — 黙って skip する旧挙動こそが欠陥だったため。

    2026-08-26 同日追記: 閾値は実時間でなく **市場オープン時間**
    (``_market_open_hours``) で数える。FX は金 21:00 → 日 21:00 UTC の
    約 48h 閉場するため、実時間 24h では金曜夕方の最終取引が毎週末
    必ず誤発火する。書込み障害そのものの検知は ``check_db_write_health``
    が受け持つ (write_probe の実 INSERT 成否を見る)。
    """
    events: list[dict[str, Any]] = []

    latest: datetime | None = None
    for t in trades:
        for key in ("open_time", "entry_time", "created_at", "timestamp"):
            raw = t.get(key)
            if not raw:
                continue
            try:
                dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if latest is None or dt > latest:
                latest = dt
            break

    if latest is None:
        # 旧実装はここで沈黙した。契約が壊れたこと自体を異常として上げる。
        events.append(
            {
                "type": "stagnation_check_broken",
                "detail": "no parseable timestamp field in /api/demo/trades",
                "n_trades_seen": len(trades),
            }
        )
        return events

    now = now or datetime.now(timezone.utc)
    wall_hours = (now - latest).total_seconds() / 3600
    open_hours = _market_open_hours(latest, now)
    if open_hours >= N_STAGNATION_HOURS:
        events.append(
            {
                "type": "live_n_stagnation",
                "hours_since_last_trade": round(wall_hours, 1),
                "market_open_hours_since": round(open_hours, 1),
                "threshold_hours": N_STAGNATION_HOURS,
                "last_trade_time": latest.isoformat(),
            }
        )
    return events


def check_disk_capacity(disk_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Render Disk 使用率を /api/admin/disk_status から監視する (rule:R3, 2026-08-26).

    2026-08-21 の満杯事故は「誰も空き容量を測っていなかった」ため 3.5 日
    発見されなかった。閾値は modules/disk_guard.py が API 応答に同梱して
    返すので、判定基準は本番コードと単一ソースになる。
    """
    events: list[dict[str, Any]] = []
    if not disk_payload:
        return events
    disk = disk_payload.get("disk") or {}
    used_pct = disk.get("used_pct")
    if used_pct is None:
        return events

    warn = disk_payload.get("warn_pct", 75.0)
    critical = disk_payload.get("critical_pct", 90.0)
    if used_pct >= warn:
        fp = disk_payload.get("footprint") or {}
        events.append(
            {
                "type": "disk_capacity",
                "severity": "critical" if used_pct >= critical else "warn",
                "used_pct": used_pct,
                "free_bytes": disk.get("free_bytes"),
                "total_bytes": disk.get("total_bytes"),
                "main_db_bytes": fp.get("main_bytes"),
                "backups_total_bytes": fp.get("backups_total_bytes"),
                "backup_preflight_ok": (disk_payload.get("backup_preflight") or {}).get("ok"),
            }
        )

    # 書込み停止そのものの直接検知: backup が低容量でスキップされ続けている
    if (disk_payload.get("backup_preflight") or {}).get("ok") is False:
        events.append(
            {
                "type": "backup_blocked_low_disk",
                "need_bytes": (disk_payload.get("backup_preflight") or {}).get("need_bytes"),
                "free_bytes": (disk_payload.get("backup_preflight") or {}).get("free_bytes"),
            }
        )
    return events


def check_db_write_health(disk_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """write_probe (実 INSERT の成否) で書込み障害を直接検知する (rule:R3, 2026-08-26).

    ``live_n_stagnation`` は「取引が無い」の proxy であり、取引が無い正当な
    時間帯 (週末閉場・閑散) と書込み障害を区別できない。こちらは
    ``/api/admin/disk_status`` が応答時に実行する 1 行 upsert
    (``disk_guard.write_probe``) の結果を見る。commit が成功したという
    事実そのものなので、再起動にも ENOSPC 下の WAL 再書込みにも騙されず、
    2026-08-21 の満杯事故なら最初のポーリング (15 分以内) で鳴っていた。

    fetch 失敗 ({}) は沈黙する (false alarm を作らない、既存方針)。payload
    はあるのに ``write_probe`` キーが無い場合は ``write_probe_missing`` を
    記録する — 黙って skip する検知器こそが 126 日 no-op の原因だったため。
    ただしこれはデプロイ直後のバージョン不一致で必ず一度は起きるので、
    Discord には流さない (NOTIFY_NEVER)。
    """
    events: list[dict[str, Any]] = []
    if not disk_payload:
        return events
    probe = disk_payload.get("write_probe")
    if not isinstance(probe, dict):
        events.append(
            {
                "type": "write_probe_missing",
                "detail": "no write_probe in /api/admin/disk_status (version skew?)",
            }
        )
        return events
    if probe.get("ok") is False:
        events.append(
            {
                "type": "db_write_failed",
                "error": str(probe.get("error"))[:200],
                "last_ok_at": probe.get("last_ok_at"),
            }
        )
    return events


def check_candidate_stagnation(
    status: dict[str, Any], now: datetime | None = None
) -> list[dict[str, Any]]:
    """シグナル評価そのものの停止を検知する (rule:R3, 2026-08-27).

    既存 3 検知器がいずれも見ていない故障モードを埋める:

    - ``db_write_failed`` (write_probe) は **書込み経路**の生死しか見ない。
      評価スレッドが死んで候補が 1 件も出なくなっても probe は ok を返す。
    - ``live_n_stagnation`` は約定ベースなので閾値が 24 市場オープン時間。
      「ゲートが弾いているだけ」と区別するため意図的に鈍い。
    - watcher は ``main_loop_alive`` 等のスレッド生存を **一切見ていない**
      (2026-08-27 時点で全数 grep 済み)。

    ``evaluated_candidates`` はバー評価ごとに書かれる高頻度系列
    (本番実測 315,173 行 vs 約定 16,548 行) なので、これが止まることは
    「エンジンが評価していない」とほぼ同値であり、約定より遥かに速く
    劣化を捉えられる。

    **閾値の実測根拠 (2026-08-26 18:17〜08-27 02:25 UTC, 2,000 行)**:
    行間隔の median 0.10 分 / p99 0.80 分。最大は 120.3 分 = NY クローズ〜
    アジア early (水 22:00→00:00 UTC) の薄商い帯。よって自然な無風で 2h は
    起こりうる。閾値 ``CANDIDATE_STAGNATION_HOURS = 6`` は実測最大の 3 倍を
    取ったもので、``live_n_stagnation`` の 24h に対し検知を 4 倍速める。
    観測窓が 8 時間しかないため **暫定値**であり、誤発火が出たら実測を
    延長して上げること (下げる方向の調整は実測なしに行わない)。

    週末閉場は ``_market_open_hours`` で除外する — 実時間で数えると
    毎週末必ず誤発火する (``live_n_stagnation`` で踏んだのと同じ罠)。
    """
    events: list[dict[str, Any]] = []
    if not status:
        return events

    st = status.get("last_candidate_row_status")
    if st is None:
        # デプロイ直後の web 旧版など。黙って skip せず記録だけ残す
        # (沈黙こそが 126 日 no-op の原因だった)。通知はしない。
        events.append(
            {
                "type": "candidate_freshness_missing",
                "detail": "no last_candidate_row_status in /api/demo/status (version skew?)",
            }
        )
        return events

    # no_table / no_rows は初期状態。error は本物の異常。
    if st == "error":
        events.append(
            {
                "type": "candidate_freshness_error",
                "detail": str(status.get("row_freshness_error"))[:200],
            }
        )
        return events
    if st != "ok":
        return events

    raw_at = status.get("last_candidate_row_at")
    try:
        latest = datetime.fromisoformat(str(raw_at).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        events.append(
            {
                "type": "candidate_freshness_error",
                "detail": f"unparseable last_candidate_row_at: {raw_at!r}",
            }
        )
        return events
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)

    now = now or datetime.now(timezone.utc)
    open_hours = _market_open_hours(latest, now)
    if open_hours >= CANDIDATE_STAGNATION_HOURS:
        events.append(
            {
                "type": "candidate_stagnation",
                "market_open_hours_since": round(open_hours, 1),
                "hours_since_last_candidate": round(
                    (now - latest).total_seconds() / 3600, 1
                ),
                "threshold_hours": CANDIDATE_STAGNATION_HOURS,
                "last_candidate_row_at": str(raw_at),
            }
        )
    return events


def check_session_volume(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tokyo session (UTC 00-06) の直近volumeが30日median比50%未満なら警告。"""
    events = []
    from collections import defaultdict
    by_day = defaultdict(lambda: defaultdict(int))
    for t in trades:
        et = t.get("exit_time", "") or t.get("entry_time", "")
        if len(et) < 13:
            continue
        day = et[:10]
        try:
            hour = int(et[11:13])
        except ValueError:
            continue
        if 0 <= hour < 6:
            by_day[day]["tokyo"] += 1

    if len(by_day) < 7:
        return events
    days = sorted(by_day.keys())
    recent = by_day[days[-1]]["tokyo"]
    historical = [by_day[d]["tokyo"] for d in days[:-1]]
    med = statistics.median(historical) if historical else 0
    if med > 0 and recent / med < SESSION_VOLUME_RATIO_THRESHOLD:
        events.append(
            {
                "type": "session_volume_drift",
                "session": "tokyo",
                "recent_count": recent,
                "median_count": med,
                "ratio": round(recent / med, 2),
            }
        )
    return events


# ── ログ保存 + 通知 ─────────────────────────────────────

def save_events(events: list[dict[str, Any]]) -> Path:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = ROOT / "knowledge-base" / "raw" / "anomalies" / f"{date_str}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with path.open("a") as f:
        for e in events:
            f.write(json.dumps({**e, "ts": ts}, ensure_ascii=False) + "\n")
    return path


def _notify_key(event: dict[str, Any]) -> str:
    et = str(event.get("type"))
    if et == "disk_capacity":
        return f"{et}:{event.get('severity', 'warn')}"
    return et


def _should_notify(event: dict[str, Any], now: datetime) -> bool:
    """継続性イベントの通知可否。NOTIFY_EVERY_HOURS のバケット先頭スロット
    (now.hour がバケット幅の倍数 かつ minute が最初の cron 間隔内) に
    当たった実行だけ True。NOTIFY_NEVER は常に False、それ以外の表に無い
    type (一過性イベント) は常に True。"""
    key = _notify_key(event)
    if key in NOTIFY_NEVER:
        return False
    every = NOTIFY_EVERY_HOURS.get(key)
    if every is None:
        return True
    return now.hour % every == 0 and now.minute < CRON_INTERVAL_MIN


def _fmt_mb(n: Any) -> str:
    try:
        return f"{int(n) / 1_048_576:.0f}MB"
    except (TypeError, ValueError):
        return "?"


def _event_line(e: dict[str, Any]) -> str:
    et = e.get("type")
    if et == "spread_spike":
        return f"- spread_spike {e['instrument']}: {e['latest_mean_5']} vs median {e['median_30d']} ({e['ratio']}×)"
    if et == "oanda_latency":
        return f"- oanda_latency: {e['latency_sec']:.2f}s (threshold {e['threshold']}s)"
    if et == "live_n_stagnation":
        return (
            f"- live_n_stagnation: {e['hours_since_last_trade']}h since last trade"
            f" (市場オープン {e.get('market_open_hours_since', '?')}h)"
        )
    if et == "session_volume_drift":
        return f"- session_drift {e['session']}: {e['recent_count']} vs median {e['median_count']} ({e['ratio']}×)"
    if et == "disk_capacity":
        return (
            f"- disk_{e.get('severity')}: {e.get('used_pct')}% used,"
            f" free {_fmt_mb(e.get('free_bytes'))}"
            f" (backups {_fmt_mb(e.get('backups_total_bytes'))})"
        )
    if et == "backup_blocked_low_disk":
        return (
            f"- backup_blocked_low_disk: need {_fmt_mb(e.get('need_bytes'))},"
            f" free {_fmt_mb(e.get('free_bytes'))} — 日次バックアップがスキップされ続けている"
        )
    if et == "db_write_failed":
        return (
            f"- db_write_failed: {e.get('error')}"
            f" (last ok {e.get('last_ok_at')}) — DB 書込みが今まさに失敗している"
        )
    if et == "stagnation_check_broken":
        return f"- {et}: {e.get('detail')} — 検知器の計装契約が破れている"
    if et == "candidate_stagnation":
        return (
            f"- candidate_stagnation: 市場オープン {e.get('market_open_hours_since')}h"
            f" 候補行ゼロ (実時間 {e.get('hours_since_last_candidate')}h,"
            f" 閾値 {e.get('threshold_hours')}h, 最終 {e.get('last_candidate_row_at')})"
            f" — シグナル評価が止まっている疑い (書込みは生存)"
        )
    if et in ("candidate_freshness_error", "candidate_freshness_missing"):
        return f"- {et}: {e.get('detail')} — 鮮度計装の契約が破れている"
    return f"- {et}: {json.dumps(e, ensure_ascii=False)[:150]}"


def notify_discord(events: list[dict[str, Any]], now: datetime | None = None) -> None:
    if not events:
        return
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        return

    now = now or datetime.now(timezone.utc)
    to_send = [e for e in events if _should_notify(e, now)]
    suppressed = len(events) - len(to_send)
    if not to_send:
        print(f"[notify] {suppressed} event(s) suppressed by time-bucket throttle")
        return

    lines = [f"🚨 Tier C Anomaly — {now.strftime('%H:%M UTC')}"]
    lines.extend(_event_line(e) for e in to_send)
    if suppressed:
        kinds = sorted({_notify_key(e) for e in events if not _should_notify(e, now)})
        lines.append(
            f"(+{suppressed} 件抑制中: {', '.join(kinds)} — 詳細は cron ログ)"
        )
    lines.append("")
    lines.append("※判断・自動変更なし。通知のみ。")

    try:
        requests.post(webhook, json={"content": "\n".join(lines)[:1900]}, timeout=10)
    except requests.RequestException as e:
        print(f"⚠️  Discord notify failed: {e}", file=sys.stderr)


# ── メイン ──────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    # now は run の先頭で 1 回だけ取る: fetch (最大 4 本、timeout 15s) の
    # 後に取ると、バケット先頭スロットの run が判定時刻だけ minute 15 を
    # 越えて通知を落とすことがある
    now = datetime.now(timezone.utc)

    trades_raw = fetch_json("/api/demo/trades?limit=500")
    trades = trades_raw.get("trades", []) if isinstance(trades_raw, dict) else []

    oanda_status = fetch_json("/api/oanda/status")
    status = fetch_json("/api/demo/status")
    disk_payload = fetch_json("/api/admin/disk_status")

    all_events: list[dict[str, Any]] = []
    all_events.extend(check_spread_spike(trades))
    all_events.extend(check_oanda_latency(oanda_status))
    all_events.extend(check_live_n_stagnation(status, trades, now=now))
    all_events.extend(check_session_volume(trades))
    all_events.extend(check_disk_capacity(disk_payload))
    all_events.extend(check_db_write_health(disk_payload))
    all_events.extend(check_candidate_stagnation(status, now=now))

    if all_events:
        path = save_events(all_events)
        # Render cron はクローンごと破棄されるので上の JSONL は本番では
        # 残らない。cron の stdout ログが恒久記録 — 全件を 1 行 JSON で出す
        # (Discord は時間バケット抑制で間引かれるため、ここが全量)
        for e in all_events:
            print(f"[event] {json.dumps(e, ensure_ascii=False)}")
        notify_discord(all_events, now=now)
        print(f"Detected {len(all_events)} anomalies → {path}")
    else:
        print("No anomalies detected.")

    if args.json:
        print(json.dumps(all_events, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
