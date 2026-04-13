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
FACTORS_URL = "https://fx-ai-trader.onrender.com/api/demo/factors"

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


def check_strategy_performance() -> list[str]:
    """v8.9: 自動改善パイプライン — 5パターンの問題を人間の指摘なしで検知。
    auto-improvement-pipeline.md の設計に基づく実装。

    Pattern 1: TPが遠すぎて利確できない (MFE到達率)
    Pattern 2: 特定時間帯で全敗
    Pattern 3: Quick Harvest適用済みなのにWR<30%
    Pattern 4: MFE=0即死 (エントリー方向の問題)
    Pattern 5: Shadowデータから正EV浮上 (復帰候補)
    + 好調/毒性の基本検知
    """
    notifications = []
    try:
        # ── 基本: 戦略×ペア別EV追跡 ──
        d = fetch_json(f"{FACTORS_URL}?factors=strategy,instrument&min_n=5")
        cells = d.get("cells", [])
        for c in cells:
            strat, inst = c.get("strategy", "?"), c.get("instrument", "?")
            n, wr, ev, kelly, pnl = (c.get("n", 0), c.get("wr", 0),
                                      c.get("ev", 0), c.get("kelly", 0), c.get("pnl", 0))
            if n >= 10 and ev > 1.0 and kelly > 20:
                notifications.append(
                    f"🟢 **{strat}×{inst} 好調** — N={n} WR={wr:.1f}% "
                    f"EV={ev:+.2f} Kelly={kelly:+.1f}% PnL={pnl:+.1f}pip"
                )
            if n >= 15 and ev < -1.5:
                notifications.append(
                    f"🔴 **{strat}×{inst} 毒性** — N={n} WR={wr:.1f}% "
                    f"EV={ev:+.2f} PnL={pnl:+.1f}pip → ブロック検討"
                )
            # Pattern 3: QH適用済み(非exempt)なのにWR<30% → 方向が根本的に間違い
            if n >= 10 and wr < 30:
                notifications.append(
                    f"⚠️ **{strat}×{inst} WR壊滅** — N={n} WR={wr:.1f}% "
                    f"→ SL/TP/方向の根本見直し or FORCE_DEMOTED検討"
                )

        # ── Pattern 2: 時間帯×戦略で全敗検知 ──
        d2 = fetch_json(f"{FACTORS_URL}?factors=strategy,hour&min_n=5")
        for c in d2.get("cells", []):
            strat, hour = c.get("strategy", "?"), c.get("hour", "?")
            n, ev, pnl = c.get("n", 0), c.get("ev", 0), c.get("pnl", 0)
            if n >= 5 and ev > 1.5:
                notifications.append(
                    f"⏰ **{strat} H{hour} 好調** — N={n} EV={ev:+.2f} PnL={pnl:+.1f}pip"
                )
            if n >= 5 and ev < -2.0:
                notifications.append(
                    f"🕐 **{strat} H{hour} 時間帯毒性** — N={n} EV={ev:+.2f} "
                    f"PnL={pnl:+.1f}pip → 時間帯ブロック検討"
                )

        # ── Pattern 1 & 4: MFE分析 (トレード個別データから) ──
        trades_d = fetch_json(TRADES_URL)
        trade_list = trades_d.get("trades", [])
        from collections import defaultdict
        strat_mfe = defaultdict(lambda: {"total_loss": 0, "mfe_zero": 0,
                                          "tp_miss": 0, "has_mfe": 0})
        for t in trade_list:
            if t.get("is_shadow", 0) or t.get("outcome") != "LOSS":
                continue
            et = t.get("entry_type", "?")
            mfe = t.get("mafe_favorable_pips", 0) or 0
            strat_mfe[et]["total_loss"] += 1
            if mfe == 0 or mfe < 0.5:
                strat_mfe[et]["mfe_zero"] += 1
            if mfe > 2.0:
                # Pattern 1: 利益方向に動いたのに負けた = TP遠すぎ or SL狭すぎ
                strat_mfe[et]["tp_miss"] += 1
            if mfe > 0:
                strat_mfe[et]["has_mfe"] += 1

        for et, m in strat_mfe.items():
            total = m["total_loss"]
            if total < 5:
                continue
            # Pattern 4: MFE=0即死率
            mfe0_rate = m["mfe_zero"] / total * 100
            if mfe0_rate >= 80:
                notifications.append(
                    f"💀 **{et} 即死率{mfe0_rate:.0f}%** — {m['mfe_zero']}/{total}件が"
                    f"MFE=0 → エントリー方向/タイミングの根本問題"
                )
            # Pattern 1: TP未達反転率
            if m["has_mfe"] >= 3:
                tp_miss_rate = m["tp_miss"] / total * 100
                if tp_miss_rate >= 50:
                    notifications.append(
                        f"📏 **{et} TP未達反転{tp_miss_rate:.0f}%** — {m['tp_miss']}/{total}件が"
                        f"MFE>2pipなのにLOSS → TP縮小 or QH強化を検討"
                    )

        # ── Pattern 5: Shadow正EV浮上 (復帰候補) ──
        d5 = fetch_json(f"{FACTORS_URL}?factors=strategy,instrument&min_n=10&include_shadow=1")
        for c in d5.get("cells", []):
            strat, inst = c.get("strategy", "?"), c.get("instrument", "?")
            n, ev, kelly = c.get("n", 0), c.get("ev", 0), c.get("kelly", 0)
            if n >= 20 and ev > 0.5 and kelly > 10:
                notifications.append(
                    f"🔄 **{strat}×{inst} Shadow復帰候補** — N={n} EV={ev:+.2f} "
                    f"Kelly={kelly:+.1f}% → PROMOTE検討"
                )

    except Exception:
        pass
    return notifications


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


def save_to_kb(issues: list[str], diagnosis: str) -> None:
    """アラート結果をKBに保存（障害履歴の蓄積）。"""
    kb_dir = ROOT / "knowledge-base" / "raw" / "trade-logs"
    kb_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M UTC")
    path = kb_dir / f"{date_str}-monitor.md"

    issue_block = "\n".join(f"- {i}" for i in issues)
    entry = (
        f"\n## Alert: {time_str}\n\n"
        f"### 検出された問題\n{issue_block}\n"
    )
    if diagnosis:
        entry += f"\n### 診断\n{diagnosis}\n"

    try:
        with open(path, "a", encoding="utf-8") as f:
            if f.tell() == 0:
                f.write(f"# Trade Monitor Alerts: {date_str}\n")
            f.write(entry)
        print(f"📝 KB保存: {path.relative_to(ROOT)}")
    except Exception as e:
        print(f"  ⚠️  KB保存失敗: {e}", file=sys.stderr)


def main() -> int:
    status = fetch_json(STATUS_URL)
    logs   = fetch_json(LOGS_URL)
    trades = fetch_json(TRADES_URL)

    issues: list[str] = []
    issues += check_system_health(status)
    issues += check_trade_activity(status, trades)
    issues += check_block_counts(status)
    issues += check_logs(logs)

    # v8.9: 戦略パフォーマンス通知（問題がなくても好調戦略は通知）
    perf_notes = check_strategy_performance()
    if perf_notes and not issues:
        # 異常なしだが戦略通知あり → Discord送信（軽量）
        webhook = os.environ.get("DISCORD_WEBHOOK_URL")
        if webhook:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            perf_msg = (
                f"📊 **戦略パフォーマンス [{now}]**\n\n"
                + "\n".join(perf_notes[:10])
            )
            send_discord(webhook, perf_msg)
            print(f"📊 {len(perf_notes)}件の戦略通知 → Discord送信済み")
        else:
            for p in perf_notes:
                print(p)

    if not issues:
        print("✅ 異常なし")
        return 0

    # 問題あり → 診断 + KB保存 + Discord送信
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    diagnosis = diagnose_with_llm(issues, status, logs)

    # KB保存
    save_to_kb(issues, diagnosis)

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
