"""OANDA 会員ステータス維持用の出来高キーパー (2026-09-01 user 決裁 案 A)。

OANDA Japan の REST API 利用条件 = Gold ステータス (前月取引量 USD 50 万、
新規+決済の双方でカウント) + プロコース + 口座残高 25 万円。条件は利用中
ずっと継続充足が必要で、割れると API 停止 + トークン再発行 (FAQ 720/1730)。
エッジトレードは MIN lot 契約下で月 ~$28k しか出来高を生まないため、
ステータス維持専用に USD_JPY の小口即時往復で出来高を積む。

設計原則:
  - demo DB には一切書かない (Kelly / quant-eval / 鮮度検知の母集団を汚染しない)。
    トレードの識別は OANDA 側 tradeClientExtensions tag ("SVK") と本モジュールの
    状態ファイルのみ。
  - 口座に 1 つでも open trade がある間は発注しない (エンジン/手動ポジションとの
    netting 干渉をゼロにする)。決済は trade_id 指定 close のみ。
  - スプレッド異常時は skip (デスゾーンは動的検出のみ、の原則に整合)。
  - NAV floor (API のもう 1 つの存続条件 = 残高 25 万円) を下回りそうなら発注しない。
  - fork-safety §11: thread は serving プロセスの before_request heartbeat
    (ensure_worker_running) からのみ起動する。import 時には何も走らない。

決裁: knowledge-base/wiki/decisions/status-volume-keeper-2026-09-01.md
分析: knowledge-base/wiki/analyses/live-frequency-and-oanda-status-survival-2026-09-01.md
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

_LOCK = threading.Lock()
_worker: Optional["StatusVolumeKeeper"] = None

_PIP = 0.01  # USD_JPY
_INSTRUMENT = "USD_JPY"  # units = USD notional。他ペアは volume 換算が変わるため固定
_TAG = "SVK"


def _log(msg: str) -> None:
    print(f"[svk] {msg}", flush=True)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StatusVolumeKeeper:
    """月間出来高を SVK_MONTHLY_TARGET_USD まで小口往復で積むワーカー。"""

    def __init__(self, client: Any = None,
                 state_path: str = None,
                 now_fn=None) -> None:
        self.enabled = os.environ.get(
            "STATUS_VOLUME_KEEPER_ENABLE", "0") == "1"
        self.target_usd = float(os.environ.get(
            "SVK_MONTHLY_TARGET_USD", "520000"))
        # hard cap 20k: margin (25x) と瞬間エクスポージャの上限を code で固定
        self.units = min(int(os.environ.get("SVK_UNITS", "10000")), 20000)
        self.max_spread_pips = float(os.environ.get(
            "SVK_MAX_SPREAD_PIPS", "1.0"))
        self.nav_floor_jpy = float(os.environ.get(
            "SVK_NAV_FLOOR_JPY", "262000"))
        self.max_rt_per_day = int(os.environ.get("SVK_MAX_RT_PER_DAY", "3"))
        self.min_spacing_sec = int(os.environ.get(
            "SVK_MIN_SPACING_SEC", "3600"))
        hours = os.environ.get("SVK_WINDOW_HOURS_UTC", "0,1,2,3,4,5")
        self.window_hours = {int(h) for h in hours.split(",") if h.strip()}
        self.poll_sec = int(os.environ.get("SVK_POLL_SEC", "300"))
        self.state_path = state_path or os.environ.get(
            "SVK_STATE_PATH", "/var/data/status_volume_keeper.json")
        self._now_fn = now_fn or _utcnow
        self._client = client
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.last_skip_reason = ""
        self.last_skip_at = ""
        self.last_error = ""
        self.state = self._load_state()

    # ── state ─────────────────────────────────────────

    def _default_state(self, month: str) -> dict:
        return {"month": month, "volume_usd": 0.0, "rt_count": 0,
                "last_rt_at": "", "last_day": "", "rt_today": 0,
                "open_trade_ids": [], "history": []}

    def _load_state(self) -> dict:
        month = self._now_fn().strftime("%Y-%m")
        try:
            with open(self.state_path) as f:
                st = json.load(f)
            if st.get("month") != month:
                st = self._default_state(month)
            return st
        except Exception:
            return self._default_state(month)

    def _save_state(self) -> None:
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.state, f)
        os.replace(tmp, self.state_path)

    def _roll_counters(self, now: datetime) -> None:
        month = now.strftime("%Y-%m")
        day = now.strftime("%Y-%m-%d")
        if self.state.get("month") != month:
            self.state = self._default_state(month)
        if self.state.get("last_day") != day:
            self.state["last_day"] = day
            self.state["rt_today"] = 0

    # ── client ────────────────────────────────────────

    def _get_client(self):
        if self._client is None:
            from modules.oanda_client import OandaClient
            self._client = OandaClient()
        return self._client

    # ── guards → 実行 ─────────────────────────────────

    def _skip(self, reason: str) -> None:
        self.last_skip_reason = reason
        self.last_skip_at = self._now_fn().isoformat()

    def maybe_execute(self) -> bool:
        """guard chain を通過したら 1 往復だけ実行。実行したら True。"""
        if not self.enabled:
            self._skip("disabled")
            return False
        now = self._now_fn()
        self._roll_counters(now)

        # 事故復旧を最優先: 前回 close に失敗した SVK 玉が残っていれば閉じるだけ
        if self.state.get("open_trade_ids"):
            self._recover_stale_trades()
            return False

        if now.weekday() >= 5:
            self._skip("weekend")
            return False
        if now.hour not in self.window_hours:
            self._skip(f"outside_window(h={now.hour})")
            return False
        if self.state["volume_usd"] >= self.target_usd:
            self._skip("target_reached")
            return False
        if self.state["rt_today"] >= self.max_rt_per_day:
            self._skip("daily_cap")
            return False
        last_rt = self.state.get("last_rt_at") or ""
        if last_rt:
            elapsed = (now - datetime.fromisoformat(last_rt)).total_seconds()
            if elapsed < self.min_spacing_sec:
                self._skip(f"spacing({int(elapsed)}s)")
                return False

        client = self._get_client()
        ok, acct = client.get_account()
        if not ok:
            self._skip("account_fetch_failed")
            return False
        a = acct.get("account", acct)
        nav = float(a.get("NAV", a.get("nav", 0)) or 0)
        margin_avail = float(a.get("marginAvailable", 0) or 0)
        open_count = int(a.get("openTradeCount", -1))
        if nav < self.nav_floor_jpy:
            self._skip(f"nav_floor({nav:.0f}<{self.nav_floor_jpy:.0f})")
            return False
        if open_count != 0:
            # netting 干渉ゼロ原則: エンジン/手動ポジションが 1 つでもあれば見送る
            self._skip(f"account_not_flat({open_count})")
            return False

        ok, px = client.get_price(_INSTRUMENT)
        if not ok:
            self._skip("pricing_failed")
            return False
        try:
            p = px["prices"][0]
            bid = float(p["bids"][0]["price"])
            ask = float(p["asks"][0]["price"])
            tradeable = p.get("tradeable", True)
        except (KeyError, IndexError, ValueError, TypeError):
            self._skip("pricing_parse_failed")
            return False
        if not tradeable:
            self._skip("not_tradeable")
            return False
        spread_pips = (ask - bid) / _PIP
        if spread_pips > self.max_spread_pips:
            self._skip(f"spread({spread_pips:.1f}p)")
            return False
        # margin 概算 (25x): units × mid ÷ 25 [JPY]。1.5 倍の余裕を要求
        mid = (bid + ask) / 2
        need_margin = self.units * mid / 25 * 1.5
        if margin_avail < need_margin:
            self._skip(f"margin({margin_avail:.0f}<{need_margin:.0f})")
            return False

        return self._execute_round_trip(client, spread_pips)

    def _execute_round_trip(self, client, spread_pips: float) -> bool:
        ok, data = client.market_order(
            "buy", self.units, instrument=_INSTRUMENT,
            client_tag=_TAG, client_comment="status volume keeper")
        if not ok:
            self.last_error = f"open_failed: {str(data)[:200]}"
            _log(self.last_error)
            return False
        fill = (data or {}).get("orderFillTransaction", {})
        trade_id = (fill.get("tradeOpened") or {}).get("tradeID", "")
        if not trade_id:
            # FOK 不成立等 — 玉は立っていない
            self.last_error = f"no_fill: {str(data)[:200]}"
            _log(self.last_error)
            return False
        # close 失敗に備え、close 前に必ず永続化 (crash-safe)
        self.state["open_trade_ids"] = [trade_id]
        self._save_state()

        ok2, closed = client.close_trade(trade_id)
        if not ok2:
            self.last_error = f"close_failed trade={trade_id}: {str(closed)[:200]}"
            _log(self.last_error + " — 次 cycle で回収")
            return False
        pl = float(((closed or {}).get("orderFillTransaction") or {})
                   .get("pl", 0) or 0)
        now = self._now_fn()
        self.state["open_trade_ids"] = []
        self.state["volume_usd"] += self.units * 2  # 新規+決済の双方カウント
        self.state["rt_count"] += 1
        self.state["rt_today"] += 1
        self.state["last_rt_at"] = now.isoformat()
        self.state["history"] = (self.state.get("history", []) + [{
            "at": now.isoformat(), "trade_id": trade_id,
            "units": self.units, "pl_jpy": pl,
            "spread_pips": round(spread_pips, 2)}])[-20:]
        self._save_state()
        self.last_error = ""
        _log(f"RT done trade={trade_id} units={self.units} pl=¥{pl:.0f} "
             f"spread={spread_pips:.1f}p month_vol=${self.state['volume_usd']:,.0f}"
             f"/{self.target_usd:,.0f}")
        return True

    def _recover_stale_trades(self) -> None:
        client = self._get_client()
        remaining = []
        for tid in self.state.get("open_trade_ids", []):
            ok, closed = client.close_trade(tid)
            if ok:
                _log(f"stale SVK trade {tid} closed (recovery)")
                # 出来高は open 時に未計上なので回収時にまとめて計上
                self.state["volume_usd"] += self.units * 2
                self.state["rt_count"] += 1
            else:
                err = str(closed)[:200]
                # 既に閉じている (doesn't exist 等) なら在庫から外すだけ
                if "TRADE_DOESNT_EXIST" in err or "does not exist" in err:
                    _log(f"stale SVK trade {tid} already closed")
                else:
                    _log(f"stale SVK trade {tid} close failed: {err}")
                    remaining.append(tid)
        self.state["open_trade_ids"] = remaining
        self._save_state()

    # ── thread ────────────────────────────────────────

    def _loop(self) -> None:
        _log(f"worker loop start (target=${self.target_usd:,.0f}, "
             f"units={self.units}, windows={sorted(self.window_hours)}UTC)")
        while not self._stop.is_set():
            try:
                self.maybe_execute()
            except Exception as e:  # fail-loud、loop は殺さない
                self.last_error = f"{type(e).__name__}: {e}"
                _log(f"cycle error: {self.last_error}")
            self._stop.wait(self.poll_sec)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="status-volume-keeper")
        self._thread.start()

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── telemetry (/api/demo/status から読む) ─────────

    def get_status(self) -> dict:
        now = self._now_fn()
        day = now.day
        # 月の経過割合に対する達成ペース (毎月 $target を積む前提の粗い指標)
        expected = self.target_usd * min(day / 24.0, 1.0)  # 営業日 ~24 日換算
        return {
            "enabled": self.enabled,
            "running": self.is_alive(),
            "month": self.state.get("month"),
            "volume_usd": round(self.state.get("volume_usd", 0.0), 0),
            "target_usd": self.target_usd,
            "rt_count": self.state.get("rt_count", 0),
            "last_rt_at": self.state.get("last_rt_at", ""),
            "open_trade_ids": self.state.get("open_trade_ids", []),
            "last_skip_reason": self.last_skip_reason,
            "last_skip_at": self.last_skip_at,
            "last_error": self.last_error,
            "behind_pace": bool(self.enabled
                                and self.state.get("volume_usd", 0) < expected * 0.6
                                and day >= 10),
        }


def ensure_worker_running(client: Any = None) -> Optional[StatusVolumeKeeper]:
    """before_request heartbeat から呼ぶ (fork-safety §11 準拠の唯一の起動経路)。

    STATUS_VOLUME_KEEPER_ENABLE=1 でなければ何も起動しない。
    """
    global _worker
    with _LOCK:
        if os.environ.get("STATUS_VOLUME_KEEPER_ENABLE", "0") != "1":
            return None
        if _worker is None:
            _worker = StatusVolumeKeeper(client=client)
        if not _worker.is_alive():
            _worker.start()
            _log("worker (re)started by heartbeat heal")
        return _worker


def get_worker_status() -> dict:
    """API telemetry。worker 未起動でも enabled/disabled が分かる形で返す。"""
    if _worker is not None:
        return _worker.get_status()
    enabled = os.environ.get("STATUS_VOLUME_KEEPER_ENABLE", "0") == "1"
    return {"enabled": enabled, "running": False,
            "note": "worker not started in this process"}
