#!/usr/bin/env python3
"""
FX AI Trader — 日次自動レポート＋作戦立案パイプライン

使用方法:
  python3 scripts/daily_report.py

環境変数:
  ANTHROPIC_API_KEY     — Claude API キー（必須）
  DISCORD_WEBHOOK_URL   — Discord送信先（必須）

処理フロー:
  Step 1. 本番APIからデータ取得
  Step 2. Analyst  → 運用レポート＋クオンツ見解
  Step 3. Strategy → アナリストレポートを読んで作戦立案（GO/NO-GO判断材料）
  Step 4. Discord  → 両レポートを送信 → ユーザーが最終判断
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PRODUCTION_APIS = {
    "status": "https://fx-ai-trader.onrender.com/api/demo/status",
    "trades": "https://fx-ai-trader.onrender.com/api/demo/trades?limit=300",
    "oanda":  "https://fx-ai-trader.onrender.com/api/oanda/status",
    "risk":   "https://fx-ai-trader.onrender.com/api/risk/dashboard",
}

FIDELITY_CUTOFF = "2026-04-08T00:00:00+00:00"
CLAUDE_MODEL = "claude-sonnet-4-6"


# ── API ────────────────────────────────────────────────

def fetch_json(url: str, timeout: int = 15) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FX-DailyReport/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️  fetch failed: {url} — {e}", file=sys.stderr)
        return {}


def call_claude(system: str, messages: list[dict], max_tokens: int = 2500) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません")

    payload = json.dumps({
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        resp = json.loads(r.read().decode())
    return resp["content"][0]["text"]


# ── エージェントプロンプト読み込み ──────────────────────

def load_agent_prompt(name: str) -> str:
    """agents/{name}.md のフロントマター除去後の本文を返す。"""
    # scripts/agents/ (git tracked) を優先、.claude/agents/ にフォールバック
    path = ROOT / "scripts" / "agents" / f"{name}.md"
    if not path.exists():
        path = ROOT / ".claude" / "agents" / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"agents/{name}.md が見つかりません (scripts/agents/ と .claude/agents/ を探索)")
    parts = path.read_text(encoding="utf-8").split("---")
    return (parts[2] if len(parts) >= 3 else parts[-1]).strip()


# ── Step 2: Analyst レポート ────────────────────────────

def run_analyst(data: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    user_msg = f"""以下は本日（{now}）の本番システムデータです。
Fidelity Cutoff（{FIDELITY_CUTOFF}）以降のみ有効として分析してください。

### STATUS
{json.dumps(data.get("status", {}), ensure_ascii=False, indent=2)[:3000]}

### TRADES（直近300件）
{json.dumps(data.get("trades", {}), ensure_ascii=False, indent=2)[:5000]}

### OANDA
{json.dumps(data.get("oanda", {}), ensure_ascii=False, indent=2)[:1000]}

### RISK DASHBOARD
{json.dumps(data.get("risk", {}), ensure_ascii=False, indent=2)[:2000]}

---
定型レポート（戦略別N/WR/EV、block_counts主因、OANDA転送率、Sentinel進捗）と
クオンツ見解（最重要シグナル・構造的観察・推奨アクション）を生成してください。"""

    return call_claude(load_agent_prompt("analyst"), [{"role": "user", "content": user_msg}])


# ── Step 3: Strategy 作戦立案 ──────────────────────────

STRATEGY_PLANNING_SUFFIX = """
---

## 作戦立案モード（自動レポート用）

上記のシニアクオンツとしての設計原則に加え、アナリストレポートを受け取ったときは
**コードは書かず**、以下の形式で「試す価値があるか」の判断材料のみを提示する。

### 出力フォーマット

**【作戦候補 #N】戦略名（仮）**
- **仮説**: 何の非効率を突くか（1文）
- **根拠**: なぜ今このデータがその機会を示しているか
- **学術的裏付け**: 著者(年) + 知見（1行）
- **失敗シナリオ**: この戦略が機能しない状況
- **摩擦試算**: spread_cost概算（閾値と比較）
- **GO基準**: 実装に進むべき条件（例: 「N=20後WR>55%」）
- **推奨優先度**: 🔴高 / 🟡中 / 🟢低（理由1文）

候補は最大3件。優先度順に並べる。
候補がない（データ不足・現状の戦略で十分）場合は「現状維持推奨」と明記。
"""


def run_strategy_planner(analyst_report: str) -> str:
    system = load_agent_prompt("strategy-dev") + STRATEGY_PLANNING_SUFFIX

    user_msg = f"""以下はアナリストが生成した本日の運用レポートです。
このデータ・見解をもとに、次に試すべき戦略の作戦を立案してください。

---
{analyst_report}
---

コードは不要です。「試す価値があるか」の判断材料だけを提示してください。"""

    return call_claude(system, [{"role": "user", "content": user_msg}])


# ── Step 4: Discord 送信 ────────────────────────────────

def send_discord_block(webhook_url: str, title: str, body: str) -> None:
    """タイトル付きブロックを Discord に分割送信する。"""
    full = f"{title}\n\n{body}"
    chunks: list[str] = []
    buf = ""
    for line in full.splitlines(keepends=True):
        if len(buf) + len(line) > 1900:
            chunks.append(buf)
            buf = line
        else:
            buf += line
    if buf:
        chunks.append(buf)

    for i, chunk in enumerate(chunks):
        suffix = f"\n*(part {i+1}/{len(chunks)})*" if len(chunks) > 1 else ""
        payload = json.dumps({"content": chunk + suffix}).encode()
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
            print(f"  ⚠️  Discord送信失敗 (part {i+1}): {e}", file=sys.stderr)


# ── main ────────────────────────────────────────────────

def main() -> int:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")

    # Step 1: データ取得
    print("🔍 [1/3] 本番APIからデータ取得中...")
    data = {k: fetch_json(url) for k, url in PRODUCTION_APIS.items()}
    failed = [k for k, v in data.items() if not v]
    if failed:
        print(f"  ⚠️  取得失敗: {', '.join(failed)}")

    # Step 2: アナリストレポート
    print("📊 [2/3] Analyst — 運用レポート生成中...")
    try:
        analyst_report = run_analyst(data)
    except Exception as e:
        print(f"  ❌ Analyst エラー: {e}", file=sys.stderr)
        return 1

    # Step 3: 作戦立案
    print("🧠 [3/3] Strategy — 作戦立案中...")
    try:
        strategy_report = run_strategy_planner(analyst_report)
    except Exception as e:
        print(f"  ⚠️  Strategy エラー（スキップ）: {e}", file=sys.stderr)
        strategy_report = "⚠️ 作戦立案の生成に失敗しました。"

    # Step 4: 送信 or 標準出力
    analyst_header  = f"📊 **【運用レポート {date_str}】**"
    strategy_header = f"🧠 **【作戦立案 {date_str}】** — GO/NO-GO はあなたが判断"

    if not webhook:
        print("\n" + "=" * 60)
        print(analyst_header)
        print(analyst_report)
        print("\n" + "=" * 60)
        print(strategy_header)
        print(strategy_report)
        print("=" * 60)
        print("\n⚠️  DISCORD_WEBHOOK_URL 未設定 — 標準出力に出力しました")
        return 0

    print(f"📨 Discord に送信中... (URL length={len(webhook)}, prefix={webhook[:45]}...)")
    send_discord_block(webhook, analyst_header, analyst_report)
    send_discord_block(webhook, strategy_header, strategy_report)
    print("✅ 完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
