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
    8. エンジン停止 (tick 前進の実時刻、15分) — 2026-08-28 追加
    9. API 到達不能 (本番 web service そのものの死) — 2026-08-30 追加

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
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, NamedTuple

import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules import freshness_policy as _fp  # noqa: E402

API_BASE = os.environ.get("API_BASE", "https://fx-ai-trader.onrender.com")

SPREAD_MULTIPLIER_THRESHOLD = 2.0
LATENCY_THRESHOLD_SEC = 3.0
SESSION_VOLUME_RATIO_THRESHOLD = 0.5
# 閾値と週末除外の時計は modules/freshness_policy.py が SSOT (rule:R3,
# 2026-08-29)。ダッシュボード表示も同じ定数・同じ時計を使う — 検知器と画面
# で閾値を別々に持つと、片方を上げたときもう片方が古い閾値で判定し続け、
# しかも全テストは green のままになる (PR #199 で実際に踏んだ型)。
# 実測根拠は各 check_* の docstring に残す。
N_STAGNATION_HOURS = _fp.N_STAGNATION_HOURS
CANDIDATE_STAGNATION_HOURS = _fp.CANDIDATE_STAGNATION_HOURS
ENGINE_TICK_STALL_MINUTES = _fp.ENGINE_TICK_STALL_MINUTES
# 書込み停止は「取引ゼロ」として現れるが、取引ゼロには市場が閉まっている
# だけの週末も含まれる。そこで検知は2本立てにする (rule:R3, 2026-08-26):
#   - live_n_stagnation: 取引時刻ベース。ただし FX 週末閉場 (金 21:00 →
#     日 21:00 UTC) を除いた「市場オープン時間」で 24h を数える。実時間で
#     数えると金曜夕方の最終取引が毎週末必ず閾値を越えて誤発火する
#   - db_write_failed: /api/admin/disk_status 応答時の実 INSERT (write_probe)
#     の成否。満杯型書込み停止の直接検知で、検知遅延はポーリング間隔の
#     15 分。mtime ベースの staleness は再起動の checkpoint でリセットされ、
#     ENOSPC 下でも確保済み WAL ブロックへの再書込みで前進するため採らない
FX_WEEKEND_CLOSE_HOURS = _fp.FX_WEEKEND_CLOSE_HOURS  # 金 21:00 UTC → 日 21:00 UTC

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
    "engine_tick_stall": 1,
    "engine_tick_never": 1,
    "api_unreachable": 1,
    "api_endpoint_failed": 6,
}
# Discord に流さない type。write_probe_missing はデプロイ直後の cron/web
# バージョン不一致で必ず一度は起きる (cron は数十秒で新コード化、web は
# build 完了まで旧 API を返す)。web が旧版のまま固着するケースは Render の
# デプロイ失敗通知が受け持つので、ここは記録のみに降格する。
NOTIFY_NEVER = {"write_probe_missing", "candidate_freshness_missing",
                "engine_tick_missing"}


class FetchOutcome(NamedTuple):
    """1 エンドポイントの取得結果.

    ``ok`` と ``payload`` を分けて持つのが要点である。旧実装は失敗時に
    ``{}`` を返しており、**「取りに行けなかった」と「空だった」が呼び出し
    側で区別できなかった** (PR #207 の「``no_rows`` と ``error`` を折り
    畳むな」と同型の欠陥)。実害は 2026-08-29T23:31Z に実測されている:
    デプロイ再起動で 4 本すべてが 502 を返した run で、``live_n_stagnation``
    が「``/api/demo/trades`` に読める時刻フィールドが無い」という**事実と
    異なる診断**を上げた。真因は API の 502 であってペイロード契約ではない。
    """

    path: str
    ok: bool
    payload: dict[str, Any]
    reason: str  # ok のときは ""


def fetch_outcome(path: str, timeout: int = 15) -> FetchOutcome:
    url = f"{API_BASE}{path}"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return FetchOutcome(path, True, r.json(), "")
    except requests.RequestException as e:
        print(f"⚠️  fetch failed: {url} — {e}", file=sys.stderr)
        return FetchOutcome(path, False, {}, f"{type(e).__name__}: {e}")


def fetch_json(path: str, timeout: int = 15) -> dict[str, Any]:
    """後方互換の薄いラッパ。**新規の呼び出しは fetch_outcome を使うこと** —
    ここで ``{}`` に潰すと上記の「折り畳み」を再導入することになる。
    """
    return fetch_outcome(path, timeout=timeout).payload


# デプロイ再起動と本物の停止を、状態を持たずに区別するためのリトライ間隔。
# Render の web service は KB 実測 (PR #199) で ramp 3.6 分 / 無 tick 59.5 秒
# を要する。全エンドポイントが同時に落ちるのは「ramp 中」か「本当に死んで
# いる」かのどちらかなので、ramp を跨ぐまで待ってから判定する。累積 3.5 分
# (30+60+120) は cron 間隔 15 分に対して十分な余裕がある。
#
# 部分障害 (一部のパスだけ失敗) はリトライしない — ramp では 4 本とも落ちる
# ので、1 本だけの失敗は最初からそのエンドポイント固有の異常である。
API_RETRY_BACKOFF_SEC = (30, 60, 120)

WATCHED_PATHS = (
    "/api/demo/trades?limit=500",
    "/api/oanda/status",
    "/api/demo/status",
    "/api/admin/disk_status",
)


def fetch_all(
    paths: tuple[str, ...] = WATCHED_PATHS,
    *,
    backoff: tuple[int, ...] = API_RETRY_BACKOFF_SEC,
    fetcher: Callable[[str], FetchOutcome] | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> tuple[dict[str, FetchOutcome], int, float]:
    """全エンドポイントを取得し、**全滅時のみ** backoff で再試行する.

    戻り値は (path→FetchOutcome, 試行回数, 費やした待機秒)。待機秒は
    ``api_unreachable`` イベントに載せる — 「何分待ってもダメだった」を
    読み手が判断できないと、デプロイ blip と本物の停止が区別できない。
    """
    fetcher = fetcher or fetch_outcome
    sleeper = sleeper or time.sleep

    attempts = 0
    waited = 0.0
    outcomes: dict[str, FetchOutcome] = {}
    for wait in (0, *backoff):
        if wait:
            sleeper(wait)
            waited += wait
        attempts += 1
        outcomes = {p: fetcher(p) for p in paths}
        if any(o.ok for o in outcomes.values()):
            break
    return outcomes, attempts, waited


# ── 検知ロジック ────────────────────────────────────────

def check_api_reachability(
    outcomes: dict[str, FetchOutcome], attempts: int = 1, waited_sec: float = 0.0
) -> list[dict[str, Any]]:
    """本番 web service そのものの死を検知する (rule:R3, 2026-08-30).

    **他の 8 検知器は全て「API が答えること」を前提にしている。** 実測
    (2026-08-29T23:31Z) では 4 エンドポイント全てが 502 を返した run で、
    8 検知器のうち 7 個が完全に沈黙し、残る 1 個 (``live_n_stagnation``) が
    事実と異なる診断を上げた。つまり **API が落ちている間、監視スタックは
    落ちていることを報告できない** — 2026-08-21 の Disk 満杯事故で「凍結
    した画面は静かな相場と区別がつかない」と学んだ構図の、監視器側での
    再演である (MEMORY: 「検知器そのものも write-only になりうる」)。

    cron の exit code は 0 のままにする。Render の notifyOnFail は cron
    自身の異常を担当する経路であり、そこに web service の停止を混ぜると
    「どちらが壊れたか」が通知から読めなくなる。この検知器の出力先は
    Discord (バケット 1h) と stdout の恒久ログ。

    ``attempts``/``waited_sec`` を必ずイベントに載せる: デプロイ ramp
    (実測 3.6 分, PR #199) を待った上でなお全滅だったのか、1 回で諦めた
    のかが読み手に分からないと、blip と本物の停止を区別できない。
    """
    failed = [o for o in outcomes.values() if not o.ok]
    if not failed:
        return []

    total = len(outcomes)
    return [
        {
            # 全滅は「サービスが死んだ」、部分失敗は「そのendpointが壊れた」。
            # 同じ type に畳むと原因の切り分けが通知から消えるので分ける。
            "type": "api_unreachable" if len(failed) == total else "api_endpoint_failed",
            "failed": [o.path for o in failed],
            "n_failed": len(failed),
            "n_watched": total,
            "attempts": attempts,
            "waited_sec": round(waited_sec, 1),
            "reasons": {o.path: o.reason for o in failed},
        }
    ]


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
    """[start, end] の実時間から FX 週末閉場を除いた時間数.

    実体は ``modules/freshness_policy.market_open_hours`` (SSOT)。ダッシュ
    ボード表示が同じ時計で「なぜ古くて正常なのか」を説明できるよう、
    検知器と画面で 1 つの実装を共有する。
    """
    return _fp.market_open_hours(start, end)


def check_live_n_stagnation(
    status: dict[str, Any],
    trades: list[dict[str, Any]],
    now: datetime | None = None,
    *,
    trades_ok: bool = True,
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

    2026-08-30 追記 (rule:R3): ``trades_ok=False`` = trades API の取得自体が
    失敗した場合は何も上げない。旧実装は失敗を ``{}``/``[]`` として受け取り
    「読める時刻フィールドが無い」と報告していたが、これは**事実と異なる
    診断**である (2026-08-29T23:31Z の 502 で実際に誤発火)。API に到達でき
    ないこと自体は ``check_api_reachability`` が真の理由付きで報告する。
    「黙って skip するな」という本検知器の設計思想はここでも守られている —
    沈黙するのは**別の検知器が同じ事実をより正確に報告するとき**だけ。
    """
    events: list[dict[str, Any]] = []

    if not trades_ok:
        return events

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
        # ここに来るのは取得に成功した場合だけなので、detail は「0 行だった」
        # と「行はあるが時刻が読めない」を区別して書く — 両方を同じ文言に
        # 畳むと、次に読む人が存在しない契約破綻を追いかけることになる。
        events.append(
            {
                "type": "stagnation_check_broken",
                "detail": (
                    "/api/demo/trades returned 0 rows"
                    if not trades
                    else "no parseable timestamp field in /api/demo/trades"
                ),
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
    (本番実測 315,173 行 vs 約定 16,548 行) なので、約定より遥かに速く
    劣化を捉えられる。

    ⚠️ **estimand の限界 (2026-08-27 本番で実測確認)**: 行は app.py で
    **v9.1 HTF Hard Block が counter-HTF 候補を除去した後**に書かれる。
    したがって本検知器が測るのは「エンジンが評価しているか」ではなく
    **「候補が select_best 段階まで到達したか」**である。実際 08-27T02:25〜
    03:40 の 73 分間は本テーブルがゼロ行だったが、これは障害ではなく
    **DTE 候補が eurgbp_daily_mr のみで、その全件が HTF Hard Block
    (htf=bull) に除去されていた**ためだった (Render ログで確認、同時刻に
    tick_counts は前進、block_counts も 154 件計上)。
    → **発火しても「engine 停止」と断定するな**。まず (a) Render ログの
    ``[DTE] HTF_HARD_BLOCK``、(b) ``tick_counts`` の前進、(c) 薄商い帯かを
    確認する。真の engine 停止判定には tick_counts の差分監視が必要だが、
    cron は状態を持てないため別途 (未実装 — 本 PR の残タスク)。

    **閾値の実測根拠 (2026-08-26 18:17〜08-27 02:25 UTC, 2,000 行)**:
    候補行は「1 バー評価で複数戦略ぶんが一斉に書かれる」**バースト構造**を
    持つ (2,000 行 = distinct 時刻 1,608 = **16 バースト**)。したがって素の
    行間隔 (median 0.10 分) は *バースト内*の密度であって停止判定の
    ケイデンスではない — 混同すると閾値を桁で誤る。停止判定に使うべきは
    **バースト間ギャップ** (60 秒許容でクラスタリング):

        median 3.2 分 / p90 59.7 分 / **max 120.3 分**

    max は NY クローズ〜アジア early (水 22:00→00:00 UTC) の薄商い帯で、
    自然な無風として 2h は起こりうる。``CANDIDATE_STAGNATION_HOURS = 6`` は
    この **max の 3 倍**で、``live_n_stagnation`` の 24h に対し 4 倍速い。

    ⚠️ **暫定値**: 観測窓 8 時間 = **バースト実効 N=16** しかなく p90/max は
    非常に粗い推定。1〜2 週の実運用後に**バースト間**ギャップ分布を取り直す
    こと。誤発火が出たら上げる (下げる方向の調整は実測なしに行わない)。

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


def check_engine_tick_stall(
    status: dict[str, Any], now: datetime | None = None
) -> list[dict[str, Any]]:
    """取引エンジン本体の停止を検知する (rule:R3, 2026-08-28).

    2026-08-27 の積み残し「engine 生存の真の検知」。既存の検知器が全て
    **エンジンの下流**を見ていたのを、tick 前進そのものに置き換える:

    ==========================  ====================================  ========
    検知器                       実際の estimand                        閾値
    ==========================  ====================================  ========
    ``live_n_stagnation``       約定が出たか (ゲート通過後)              24h
    ``candidate_stagnation``    候補が select_best に到達したか          6h
                                (HTF Hard Block の **後**)
    ``db_write_failed``         書込み経路が生きているか                  15分
    ``main_loop_alive``         Thread.is_alive() — **詰まりを検知不能**  n/a
    **``engine_tick_stall``**   **tick が完遂しているか**                **15分**
    ==========================  ====================================  ========

    tick カウンタの前進は HTF ゲートにもシグナル有無にも市場の開閉にも
    依存しない (加算は ``_tick`` が戻った後で、``_tick`` は週末なら
    early-return するだけ)。したがって ``candidate_stagnation`` と違い
    **発火 = エンジン異常**と読んでよい唯一の系列である。実際 08-27 の
    73 分候補ゼロは HTF block が実体で、その間 tick は前進していた。

    差分は**サーバ側**で取る (``_engine_tick_payload``)。Render cron は毎回
    クリーンなクローンで走り前回値を保存できないため、カウンタの絶対値を
    渡されても watcher 側では前進を判定できない — これが 08-27 に本項目を
    「設計が要る」として見送った理由だった。``write_probe.last_ok_at`` と
    同じく、状態を持つ側 (常駐プロセス) が経過秒を出すのが正しい分業。

    **閾値の実測根拠 (2026-08-28, 本番 24 モード稼働中を 20 秒間隔 x 8 標本 =
    142 秒窓で観測、前進イベント n=89)**:

    - 走っている全 **24/24** モードが窓内で漏れなく前進 (前進ゼロのモード無し)
    - **モード別**の前進間隔: median 40.4 秒 / p90 60.9 秒 / max 81.2 秒
      (``MODE_CONFIG`` の interval_sec 10-60 秒と整合。max が 60 秒を超えるのは
      単一 main loop が 24 モードを順に回す直列化のぶん)
    - engine レベル (= 全モードで最も新しい前進) は最速モード (scalp, 10 秒)
      に律速されるので通常 20 秒未満

    ⚠️ 標本化間隔 20 秒による **aliasing** で上記のギャップは 20 秒の倍数に
    量子化され、真値より**上振れ**している (真の間隔 <= 測定値)。閾値の側に
    安全なバイアスなので補正しない。

    定常の天井は「最長 interval 60 秒 + tick タイムアウト 30 秒」≈ 1.5 分。
    デプロイ再起動は PR #199 の実測で **無 tick 59.5 秒 + ramp 2 分 39 秒
    ≈ 3.6 分**。``ENGINE_TICK_STALL_MINUTES = 15`` はデプロイ ramp の約 4 倍、
    engine レベル定常値の約 30 倍。検知遅延は cron 間隔の 15 分で上限 30 分。
    ⚠️ 誤発火が出たら**上げる** (下げるのは実測を取り直してから)。

    **意図的な非目標**: 個別モードの wedge (main loop は生きているが 1 つの
    モードだけ 30 秒タイムアウトを繰り返す) は検知しない。閾値がモード別
    interval 10-60 秒に依存し較正が別問題になるため。判断材料としての
    ``engine_tick_stalest_mode`` / ``engine_tick_stalest_age_sec`` は
    payload に露出済みなので、必要になった時点で実測して足すこと。
    """
    events: list[dict[str, Any]] = []
    if not status:
        return events

    st = status.get("engine_tick_status")
    if st is None:
        # web が旧版 (デプロイ直後のバージョン不一致)。黙って skip せず
        # 記録は残す — 沈黙こそが 126 日 no-op の原因だった。通知はしない。
        events.append(
            {
                "type": "engine_tick_missing",
                "detail": "no engine_tick_status in /api/demo/status (version skew?)",
            }
        )
        return events

    if st == "not_running":
        # 全モード停止中。エンジンは「止まっている」のではなく「止められて
        # いる」— 資格 (eligible) と実状態 (effective) を混同しない。
        return events

    age = status.get("engine_tick_age_sec")
    if age is None:
        # ``never_ticked`` で age が無いのは **最悪ケース** (モードは running
        # なのに tick ゼロ)。これを version skew と同じ袋に入れると
        # NOTIFY_NEVER で沈黙する — 本検知器が存在する理由そのものを潰す。
        # 産出側は必ず数値を返すが (プロセス起動時刻フォールバック)、契約が
        # 破れた場合も鳴らす側に倒す。
        if st == "never_ticked":
            events.append(
                {
                    "type": "engine_tick_never",
                    "minutes_since_last_tick": None,
                    "threshold_minutes": ENGINE_TICK_STALL_MINUTES,
                    "running_modes": status.get("engine_tick_running_modes"),
                    "detail": "never_ticked かつ経過秒不明 — 起動失敗の疑い",
                }
            )
            return events
        events.append(
            {
                "type": "engine_tick_missing",
                "detail": f"engine_tick_age_sec is None (status={st!r})",
            }
        )
        return events

    try:
        age_min = float(age) / 60.0
    except (TypeError, ValueError):
        events.append(
            {
                "type": "engine_tick_missing",
                "detail": f"unparseable engine_tick_age_sec: {age!r}",
            }
        )
        return events

    if age_min < ENGINE_TICK_STALL_MINUTES:
        return events

    # 週末除外は **しない**: tick は市場が閉まっていても前進する。ここで
    # _market_open_hours を噛ませると、本物の週末停止を毎回見逃す。
    common = {
        "minutes_since_last_tick": round(age_min, 1),
        "threshold_minutes": ENGINE_TICK_STALL_MINUTES,
        "running_modes": status.get("engine_tick_running_modes"),
    }
    if st == "never_ticked":
        events.append({"type": "engine_tick_never", **common})
    else:
        events.append(
            {
                "type": "engine_tick_stall",
                **common,
                "stalest_mode": status.get("engine_tick_stalest_mode"),
                "stalest_age_sec": status.get("engine_tick_stalest_age_sec"),
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
            f" — 候補が select_best 段階まで 1 件も到達していない。"
            f"benign な既知要因を先に潰すこと: (a) HTF Hard Block が全候補を"
            f"除去中 (Render ログ '[DTE] HTF_HARD_BLOCK')、(b) 薄商い帯。"
            f"engine 停止と断定するな"
        )
    if et in ("candidate_freshness_error", "candidate_freshness_missing"):
        return f"- {et}: {e.get('detail')} — 鮮度計装の契約が破れている"
    if et == "engine_tick_stall":
        return (
            f"- 🛑 **エンジン停止の疑い**: tick 前進が "
            f"{e.get('minutes_since_last_tick')} 分止まっている "
            f"(閾値 {e.get('threshold_minutes')} 分、稼働 {e.get('running_modes')} モード、"
            f"最古 {e.get('stalest_mode')} {e.get('stalest_age_sec')}s)。"
            f"tick 前進は市場の開閉にもゲートにも依存しないので、"
            f"candidate_stagnation と違い **benign な説明は無い**。"
            f"/healthz と Render ログの [MainLoop] を確認"
        )
    if et == "engine_tick_never":
        return (
            f"- 🛑 **エンジンが一度も tick していない**: プロセス起動から "
            f"{e.get('minutes_since_last_tick')} 分 "
            f"(閾値 {e.get('threshold_minutes')} 分、稼働 {e.get('running_modes')} モード)。"
            f"起動失敗を疑う — Render の直近デプロイログを確認"
        )
    if et == "engine_tick_missing":
        return f"- {et}: {e.get('detail')} — engine 生存計装の契約が破れている"
    if et == "api_unreachable":
        return (
            f"- 🛑 **本番 API に到達できない**: 監視対象 {e.get('n_watched')} 本すべてが失敗 "
            f"({e.get('attempts')} 回試行 / {e.get('waited_sec')}s 待機)。"
            f"理由: {json.dumps(e.get('reasons'), ensure_ascii=False)[:200]}。"
            f"**この間、他の全検知器は盲目である** (取引停止も書込み停止も報告されない)。"
            f"Render の web service ステータスとデプロイログを確認"
        )
    if et == "api_endpoint_failed":
        return (
            f"- api_endpoint_failed: {e.get('n_failed')}/{e.get('n_watched')} 本が失敗 "
            f"({', '.join(e.get('failed', []))})。サービス全体は生きているので"
            f"当該エンドポイント固有の異常。依存する検知器だけが盲目になっている"
        )
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

    # 全滅時は ramp を跨ぐまで再試行する (fetch_all の docstring 参照)。
    # ここで待つぶん now が古くなるが、now は「観測を開始した時刻」であって
    # 判定はどれも経過時間の下側評価になるため、誤発火の方向には倒れない。
    outcomes, attempts, waited = fetch_all()
    trades_out = outcomes["/api/demo/trades?limit=500"]
    trades_raw = trades_out.payload
    trades = trades_raw.get("trades", []) if isinstance(trades_raw, dict) else []

    oanda_status = outcomes["/api/oanda/status"].payload
    status = outcomes["/api/demo/status"].payload
    disk_payload = outcomes["/api/admin/disk_status"].payload

    all_events: list[dict[str, Any]] = []
    # 他の検知器は全て「API が答えること」を前提にしている。到達不能の検知は
    # 先頭に置く — これが無いと、本番が死んだ run は「異常なし」と出力される。
    all_events.extend(check_api_reachability(outcomes, attempts, waited))
    all_events.extend(check_spread_spike(trades))
    all_events.extend(check_oanda_latency(oanda_status))
    all_events.extend(
        check_live_n_stagnation(status, trades, now=now, trades_ok=trades_out.ok)
    )
    all_events.extend(check_session_volume(trades))
    all_events.extend(check_disk_capacity(disk_payload))
    all_events.extend(check_db_write_health(disk_payload))
    all_events.extend(check_candidate_stagnation(status, now=now))
    all_events.extend(check_engine_tick_stall(status, now=now))

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
