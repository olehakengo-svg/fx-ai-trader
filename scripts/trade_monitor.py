#!/usr/bin/env python3
"""
FX AI Trader — トレード監視スクリプト

使用方法:
  python3 scripts/trade_monitor.py

環境変数:
  DISCORD_WEBHOOK_URL   — Discord送信先（必須）
  ANTHROPIC_API_KEY     — Claude API キー（問題時の診断に使用）

動作:
  問題なし → Discord送信なし（静粛）
  問題あり → Discord にアラート + LLMによる原因診断
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STATUS_URL = "https://fx-ai-trader.onrender.com/api/demo/status"
LOGS_URL   = "https://fx-ai-trader.onrender.com/api/demo/logs?limit=200"
TRADES_URL = "https://fx-ai-trader.onrender.com/api/demo/trades?limit=100"

# 直近Ntime間トレード0件で警告
NO_TRADE_WARN_HOURS = 4

# block_countがこの値を超えたら異常
BLOCK_ANOMALY_THRESHOLD = 200


def fetch_json(url: str, timeout: int = 15) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FX-Monitor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"_fetch_error": str(e)}


def is_market_open() -> bool:
    """Forexマーケット開場中か（UTC月曜00:00〜金曜22:00）。"""
    now = datetime.now(timezone.utc)
    # 日曜（weekday=6）と土曜（weekday=5）の大半は閉場
    if now.weekday() == 6:
        return False
    if now.weekday() == 5 and now.hour >= 22:
        return False
    return True


def check_system_health(status: dict) -> list[str]:
    issues = []

    if status.get("_fetch_error"):
        issues.append(f"🚨 STATUS API取得失敗: {status['_fetch_error']}")
        return issues

    if not status.get("main_loop_alive", True):
        issues.append("🚨 **main_loop_alive = False** — メインループ停止")

    if not status.get("watchdog_alive", True):
        issues.append("🚨 **watchdog_alive = False** — ウォッチドッグ停止")

    if status.get("emergency_killed"):
        issues.append("🚨 **emergency_killed = True** — 緊急停止中")

    restarts = status.get("main_loop_restarts", 0)
    if restarts >= 3:
        issues.append(f"⚠️ main_loop_restarts = {restarts}（本日{restarts}回再起動）")

    return issues


def check_trade_activity(status: dict, trades: dict) -> list[str]:
    issues = []
    if not is_market_open():
        return []

    # 直近N時間のトレード数を確認
    cutoff = datetime.now(timezone.utc) - timedelta(hours=NO_TRADE_WARN_HOURS)
    trade_list = trades.get("trades", [])
    recent = [
        t for t in trade_list
        if t.get("entry_time", "") >= cutoff.isoformat()
    ]

    if not recent:
        # 全モードのlast_signalもWAITなら警告
        modes = status.get("modes", {})
        all_wait = all(
            m.get("last_signal", "WAIT") == "WAIT"
            for m in modes.values()
            if m.get("running")
        )
        if all_wait:
            issues.append(
                f"⚠️ **直近{NO_TRADE_WARN_HOURS}時間トレード0件** かつ全モードWAIT — "
                "発火条件を満たしていないか、フィルターで全遮断の可能性"
            )
        else:
            issues.append(
                f"⚠️ **直近{NO_TRADE_WARN_HOURS}時間トレード0件** "
                "（一部モードはシグナルあり — 遮断フィルター確認推奨）"
            )

    return issues


def check_block_counts(status: dict) -> list[str]:
    issues = []
    block_counts = status.get("block_counts", {})
    anomalies = {k: v for k, v in block_counts.items() if v > BLOCK_ANOMALY_THRESHOLD}
    if anomalies:
        top = sorted(anomalies.items(), key=lambda x: -x[1])[:5]
        detail = ", ".join(f"{k}={v}" for k, v in top)
        issues.append(f"⚠️ **block_counts異常** — {detail}")
    return issues


def check_logs(logs: dict) -> list[str]:
    issues = []
    if logs.get("_fetch_error"):
        return []

    log_lines = logs.get("logs", [])
    errors = [l for l in log_lines if "ERROR" in l or "Exception" in l or "Traceback" in l]
    if errors:
        sample = errors[:3]
        issues.append(
            f"🚨 **ログにエラー検出** ({len(errors)}件)\n```\n"
            + "\n".join(sample[:200] for sample in sample)
            + "\n```"
        )
    return issues


def diagnose_with_llm(issues: list[str], status: dict, logs: dict) -> str:
    """問題がある場合にLLMで原因と対処を診断する。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ""

    issue_text = "\n".join(f"- {i}" for i in issues)
    log_sample = json.dumps(logs.get("logs", [])[-50:], ensure_ascii=False)[:3000]
    status_sample = json.dumps(status, ensure_ascii=False, indent=2)[:2000]

    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 800,
        "system": (
            "あなたはFX自動トレードシステムのシニア運用エンジニアです。"
            "検出された問題の原因を簡潔に特定し、対処方針を箇条書きで述べてください。"
            "コードは書かない。推測と確認事項を分けて述べること。"
        ),
        "messages": [{
            "role": "user",
            "content": (
                f"以下の問題が検出されました:\n{issue_text}\n\n"
                f"### ステータス\n{status_sample}\n\n"
                f"### ログ（直近）\n{log_sample}\n\n"
                "原因と対処方針を教えてください。"
            ),
        }],
    }).encode()

    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode())
        return resp["content"][0]["text"]
    except Exception as e:
        return f"（診断API失敗: {e}）"


def send_discord(webhook_url: str, message: str) -> None:
    chunks: list[str] = []
    buf = ""
    for line in message.splitlines(keepends=True):
        if len(buf) + len(line) > 1900:
            chunks.append(buf)
            buf = line
        else:
            buf += line
    if buf:
        chunks.append(buf)

    for chunk in chunks:
        payload = json.dumps({"content": chunk}).encode()
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "FX-AI-Trader/1.0",
            },
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"  ⚠️  Discord送信失敗: {e}", file=sys.stderr)


def main() -> int:
    status = fetch_json(STATUS_URL)
    logs   = fetch_json(LOGS_URL)
    trades = fetch_json(TRADES_URL)

    issues: list[str] = []
    issues += check_system_health(status)
    issues += check_trade_activity(status, trades)
    issues += check_block_counts(status)
    issues += check_logs(logs)

    if not issues:
        print("✅ 異常なし")
        return 0

    # 問題あり → 診断 + Discord送信
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    diagnosis = diagnose_with_llm(issues, status, logs)

    issue_block = "\n".join(f"{i}" for i in issues)
    message = (
        f"🚨 **FX AIトレーダー 監視アラート [{now}]**\n\n"
        f"**検出された問題:**\n{issue_block}"
    )
    if diagnosis:
        message += f"\n\n**🤖 診断:**\n{diagnosis}"

    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook:
        send_discord(webhook, message)
        print(f"⚠️ {len(issues)}件の問題を検出 → Discord送信済み")
    else:
        print(message)

    return 1  # 問題あり = 非ゼロ終了


if __name__ == "__main__":
    sys.exit(main())
