"""
Alert Manager — Discord Webhook 外部通知システム
═══════════════════════════════════════════════════

目的:
  重要イベント（DD閾値超過、OANDA接続断、連敗、EV急落等）を
  Discord Webhook 経由で即時外部通知。
  深夜の異常事態を人間が気づけるようにする。

設定:
  環境変数 DISCORD_WEBHOOK_URL にWebhook URLを設定。
  未設定の場合は全通知がサイレント（ログのみ）。

レート制限:
  同一アラートタイプは5分間に1回まで（スパム防止）。
"""
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional

try:
    import requests as _requests
except ImportError:
    _requests = None


class AlertManager:
    """Discord Webhook ベースの外部アラートシステム"""

    _COOLDOWN_SEC = 300   # 同一タイプの再送クールダウン (5分)
    # アラートタイプ別クールダウン上書き — 高頻度ブロックは長めに抑制
    _COOLDOWN_OVERRIDES = {
        "exposure": 14400,   # 4時間 — 評価サイクル毎に発火するため
    }

    def __init__(self):
        self._webhook_url: str = os.environ.get("DISCORD_WEBHOOK_URL", "")
        self._enabled: bool = bool(self._webhook_url)
        self._rate_limit: dict = {}   # alert_type → last_sent_epoch
        self._lock = threading.Lock()
        self._send_count: int = 0
        self._fail_count: int = 0

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def stats(self) -> dict:
        return {
            "enabled": self._enabled,
            "sent": self._send_count,
            "failed": self._fail_count,
        }

    # ── 内部ヘルパー ──

    def _now_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def _check_cooldown(self, alert_type: str) -> bool:
        """True = 送信OK（クールダウン外）"""
        with self._lock:
            last = self._rate_limit.get(alert_type, 0)
            now = time.time()
            # アラートタイプのプレフィックスで上書きクールダウンを検索
            cooldown = self._COOLDOWN_SEC
            for prefix, override in self._COOLDOWN_OVERRIDES.items():
                if alert_type.startswith(prefix):
                    cooldown = override
                    break
            if now - last < cooldown:
                return False
            self._rate_limit[alert_type] = now
            return True

    def _send_webhook(self, content: str, username: str = "FX-AI-Trader") -> bool:
        """Discord Webhook 送信 (同期、タイムアウト5秒)"""
        if not self._enabled or _requests is None:
            return False
        try:
            payload = {"username": username, "content": content[:2000]}
            resp = _requests.post(self._webhook_url, json=payload, timeout=5)
            if resp.status_code in (200, 204):
                self._send_count += 1
                return True
            else:
                self._fail_count += 1
                return False
        except Exception:
            self._fail_count += 1
            return False

    def _send_async(self, content: str):
        """非同期送信 (トレードスレッドをブロックしない)"""
        t = threading.Thread(target=self._send_webhook, args=(content,), daemon=True)
        t.start()

    # ── アラートタイプ別メソッド ──

    def alert_drawdown(self, current_dd_pips: float, threshold_pips: float,
                       mode: str = "", extra: str = ""):
        """ドローダウン閾値超過"""
        if not self._check_cooldown(f"dd_{mode}"):
            return
        msg = (f":warning: **DD WARNING** [{mode}]\n"
               f"Current DD: **{current_dd_pips:.1f} pips** "
               f"(threshold: {threshold_pips} pips)\n"
               f"{extra}\n"
               f":clock1: {self._now_str()}")
        self._send_async(msg)

    def alert_consecutive_losses(self, count: int, mode: str = "",
                                 pair: str = ""):
        """連敗検出"""
        if not self._check_cooldown(f"loss_{mode}_{pair}"):
            return
        msg = (f":red_circle: **{count} CONSECUTIVE LOSSES** [{mode}] {pair}\n"
               f":clock1: {self._now_str()}")
        self._send_async(msg)

    def alert_oanda_disconnect(self, error: str = ""):
        """OANDA接続断"""
        if not self._check_cooldown("oanda_disconnect"):
            return
        msg = (f":rotating_light: **OANDA DISCONNECTED**\n"
               f"Error: {error[:300]}\n"
               f":clock1: {self._now_str()}")
        self._send_async(msg)

    def alert_ev_drop(self, strategy: str, ev_before: float, ev_after: float):
        """戦略EV急落"""
        if not self._check_cooldown(f"ev_{strategy}"):
            return
        msg = (f":chart_with_downwards_trend: **EV DROP** [{strategy}]\n"
               f"EV: {ev_before:+.2f} -> {ev_after:+.2f}\n"
               f":clock1: {self._now_str()}")
        self._send_async(msg)

    def alert_exposure_blocked(self, instrument: str, direction: str,
                               reason: str):
        """エクスポージャー制限によるトレードブロック"""
        if not self._check_cooldown(f"exposure_{instrument}"):
            return
        msg = (f":shield: **EXPOSURE BLOCK** [{instrument} {direction}]\n"
               f"Reason: {reason}\n"
               f":clock1: {self._now_str()}")
        self._send_async(msg)

    def alert_oanda_kill(self, reason: str = ""):
        """OANDA全停止 (サーキットブレーカー発動)"""
        if not self._check_cooldown("oanda_kill"):
            return
        msg = (f":octagonal_sign: **OANDA KILLED** (Circuit Breaker)\n"
               f"Reason: {reason}\n"
               f":clock1: {self._now_str()}")
        self._send_async(msg)

    def alert_promotion(self, strategy: str, instrument: str, action: str):
        """戦略昇格/降格"""
        if not self._check_cooldown(f"promo_{strategy}_{instrument}"):
            return
        icon = ":arrow_up:" if action == "promoted" else ":arrow_down:"
        msg = (f"{icon} **STRATEGY {action.upper()}** [{strategy}] {instrument}\n"
               f":clock1: {self._now_str()}")
        self._send_async(msg)

    def alert_system_health(self, message: str):
        """システムヘルスチェック"""
        if not self._check_cooldown("health"):
            return
        msg = (f":hospital: **SYSTEM HEALTH**\n"
               f"{message[:500]}\n"
               f":clock1: {self._now_str()}")
        self._send_async(msg)

    def alert_custom(self, title: str, body: str):
        """カスタムアラート"""
        if not self._check_cooldown(f"custom_{title[:30]}"):
            return
        msg = (f":loudspeaker: **{title}**\n"
               f"{body[:500]}\n"
               f":clock1: {self._now_str()}")
        self._send_async(msg)
