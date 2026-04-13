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

FIDELITY_CUTOFF = "2026-04-08T00:00:00+00:00"
CLAUDE_MODEL = "claude-sonnet-4-6"

PRODUCTION_APIS = {
    "status": "https://fx-ai-trader.onrender.com/api/demo/status",
    "trades": f"https://fx-ai-trader.onrender.com/api/demo/trades?limit=500&date_from={FIDELITY_CUTOFF[:10]}&status=closed",
    "oanda":  "https://fx-ai-trader.onrender.com/api/oanda/status",
    "risk":   "https://fx-ai-trader.onrender.com/api/risk/dashboard",
    "regime": "https://fx-ai-trader.onrender.com/api/market/regime",
}


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


# ── Step 1.5: KBコンテキスト読み込み ──────────────────────

def load_kb_context() -> str:
    """KBからTier分類・教訓・未解決事項を読み込み、レポート品質を向上させる。"""
    sections = []
    # Tier分類（index.md 先頭60行）
    index_path = ROOT / "knowledge-base" / "wiki" / "index.md"
    if index_path.exists():
        lines = index_path.read_text(encoding="utf-8").splitlines()[:60]
        sections.append("### KB: Tier分類\n" + "\n".join(lines))
    # 教訓（lessons/index.md 先頭20行）
    lessons_path = ROOT / "knowledge-base" / "wiki" / "lessons" / "index.md"
    if lessons_path.exists():
        lines = lessons_path.read_text(encoding="utf-8").splitlines()[:20]
        sections.append("### KB: 過去の教訓\n" + "\n".join(lines))
    # 未解決事項（最新セッションログ）
    sessions_dir = ROOT / "knowledge-base" / "wiki" / "sessions"
    if sessions_dir.exists():
        session_files = sorted(sessions_dir.glob("*.md"), reverse=True)
        if session_files:
            text = session_files[0].read_text(encoding="utf-8")
            import re
            m = re.search(r'## 未解決事項.*', text, re.DOTALL)
            if m:
                sections.append("### KB: 未解決事項\n" + m.group()[:500])
    return "\n\n".join(sections)[:2000] if sections else ""


# ── Step 2: Analyst レポート ────────────────────────────

def run_analyst(data: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    kb_ctx = load_kb_context()
    kb_section = f"\n\n### KB蓄積知見（Tier分類・教訓・未解決事項）\n{kb_ctx}" if kb_ctx else ""

    # レジームコンテキスト
    regime_data = data.get("regime", {})
    regime_section = ""
    if regime_data and regime_data.get("pairs"):
        regime_section = f"\n\n### MARKET REGIME（レジーム分類）\n{json.dumps(regime_data, ensure_ascii=False, indent=2)[:2000]}"

    user_msg = f"""以下は本日（{now}）の本番システムデータです。
Fidelity Cutoff（{FIDELITY_CUTOFF}）以降のみ有効として分析してください。

### STATUS
{json.dumps(data.get("status", {}), ensure_ascii=False, indent=2)[:3000]}

### TRADES（直近300件）
{json.dumps(data.get("trades", {}), ensure_ascii=False, indent=2)[:5000]}

### OANDA
{json.dumps(data.get("oanda", {}), ensure_ascii=False, indent=2)[:1000]}

### RISK DASHBOARD
{json.dumps(data.get("risk", {}), ensure_ascii=False, indent=2)[:2000]}{regime_section}{kb_section}

---
## 分析ルール（厳守）
1. **is_shadow=1のトレードは全て除外**して集計（Shadow=デモ専用、OANDAに送信されない）
2. **XAU/Gold関連トレードは別枠で集計**（FX統計に混ぜない — lesson-xau-friction-distortion参照）
3. **Risk Dashboardの集計値は参考値のみ**（pre-cutoff+XAU含む。必ずTRADESデータから自分で再計算する）
4. tradesデータは既にFidelity Cutoff以降のclosedのみに絞り込み済み
5. 戦略別N/WR/EVは必ず自分で計算してテーブル化する（「集計不能」は許容しない）

定型レポート（戦略別N/WR/EV、block_counts主因、OANDA転送率、Sentinel進捗）と
クオンツ見解（最重要シグナル・構造的観察・推奨アクション）を生成してください。
KB蓄積知見がある場合、過去の教訓や未解決事項を踏まえた分析を含めてください。
レジームデータがある場合、現在のレジームが各戦略に与える影響を言語化してください
（例: 「bb_rsiが負けたのはRANGING→TRENDING移行のため」）。"""

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

def save_to_kb(date_str: str, analyst_report: str, strategy_report: str) -> None:
    """レポートをKBに自動保存（日次知見の蓄積）。"""
    kb_dir = ROOT / "knowledge-base" / "raw" / "trade-logs"
    kb_dir.mkdir(parents=True, exist_ok=True)
    path = kb_dir / f"{date_str}-daily.md"
    content = (
        f"# Daily Report: {date_str}\n\n"
        f"## Analyst Report\n{analyst_report}\n\n"
        f"## Strategy Planning\n{strategy_report}\n"
    )
    try:
        path.write_text(content, encoding="utf-8")
        print(f"📝 KB保存: {path.relative_to(ROOT)}")
    except Exception as e:
        print(f"  ⚠️  KB保存失敗: {e}", file=sys.stderr)


def update_analyst_memory(date_str: str, analyst_report: str) -> None:
    """Analystレポートの要約をanalyst-memoryに追記（永続的フィードバックループ）。

    Renderのエフェメラルディスクでは _append_analyst_note() の結果が消失するため、
    GitHub Actions上で動くこの関数がanalyst-memoryの唯一の永続的更新経路となる。
    """
    memory_path = ROOT / "knowledge-base" / "raw" / "trade-logs" / "analyst-memory.md"
    if not memory_path.exists():
        return

    # レポートから要約を抽出（先頭500文字 → 主要知見）
    summary_lines = []
    for line in analyst_report.splitlines():
        line_s = line.strip()
        # 重要な知見行を抽出（箇条書き、数値を含む行）
        if line_s and (line_s.startswith("- ") or line_s.startswith("* ")
                       or "WR" in line_s or "EV" in line_s or "PnL" in line_s
                       or "推奨" in line_s or "警告" in line_s or "注意" in line_s):
            summary_lines.append(line_s)
        if len(summary_lines) >= 8:
            break

    if not summary_lines:
        summary_lines = [analyst_report[:300].replace("\n", " ")]

    entry = f"\n### {date_str} (auto-daily)\n" + "\n".join(summary_lines) + "\n"

    try:
        with open(memory_path, "r", encoding="utf-8") as f:
            content = f.read()

        # "## アナリストノート" セクションの末尾（## Related の直前）に挿入
        related_marker = "\n## Related"
        if related_marker in content:
            idx = content.index(related_marker)
            content = content[:idx] + entry + content[idx:]
        else:
            content += entry

        with open(memory_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📝 Analyst Memory更新: {date_str}")
    except Exception as e:
        print(f"  ⚠️  Analyst Memory更新失敗: {e}", file=sys.stderr)


def save_regime_to_kb(date_str: str, regime_data: dict) -> None:
    """市場レジームスナップショットをKBに自動保存。"""
    if not regime_data or not regime_data.get("pairs"):
        return
    kb_dir = ROOT / "knowledge-base" / "raw" / "market-analysis"
    kb_dir.mkdir(parents=True, exist_ok=True)
    path = kb_dir / f"{date_str}-regime.md"

    lines = [f"# Market Regime: {date_str}\n"]
    lines.append(f"**Timestamp**: {regime_data.get('ts', 'N/A')}\n")
    lines.append("## Pair Regime Classification")
    lines.append("| Pair | Regime | ATR%ile(5d) | ATR%ile(20d) | SMA20 Slope | Range(5d) | Last Close |")
    lines.append("|------|--------|-------------|-------------|-------------|-----------|------------|")

    for pair, info in sorted(regime_data.get("pairs", {}).items()):
        if "error" in info:
            lines.append(f"| {pair} | ERROR | - | - | - | - | {info['error']} |")
            continue
        lines.append(
            f"| {pair} | **{info['regime']}** "
            f"| {info['atr_pctile_5d']:.0f}% "
            f"| {info['atr_pctile_20d']:.0f}% "
            f"| {info['sma20_slope']:+.4f} "
            f"| {info['range_5d']:.4f} "
            f"| {info['last_close']} |"
        )

    lines.append("")
    lines.append("## Related")
    lines.append("- [[edge-pipeline]]")
    lines.append("- [[changelog]]")
    lines.append("")

    try:
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"📝 Regime KB保存: {path.relative_to(ROOT)}")
    except Exception as e:
        print(f"  ⚠️  Regime KB保存失敗: {e}", file=sys.stderr)


def main() -> int:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")

    # Step 1: データ取得
    print("🔍 [1/4] 本番APIからデータ取得中...")
    data = {k: fetch_json(url) for k, url in PRODUCTION_APIS.items()}
    failed = [k for k, v in data.items() if not v]
    if failed:
        print(f"  ⚠️  取得失敗: {', '.join(failed)}")

    # Step 2: アナリストレポート
    print("📊 [2/4] Analyst — 運用レポート生成中...")
    try:
        analyst_report = run_analyst(data)
    except Exception as e:
        print(f"  ❌ Analyst エラー: {e}", file=sys.stderr)
        return 1

    # Step 3: 作戦立案
    print("🧠 [3/4] Strategy — 作戦立案中...")
    try:
        strategy_report = run_strategy_planner(analyst_report)
    except Exception as e:
        print(f"  ⚠️  Strategy エラー（スキップ）: {e}", file=sys.stderr)
        strategy_report = "⚠️ 作戦立案の生成に失敗しました。"

    # Step 3.5: KB自動保存
    save_to_kb(date_str, analyst_report, strategy_report)

    # Step 3.5b: レジームスナップショットKB保存
    save_regime_to_kb(date_str, data.get("regime", {}))

    # Step 3.6: Analyst Memory更新（永続フィードバックループ）
    update_analyst_memory(date_str, analyst_report)

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

    print(f"📨 [4/4] Discord に送信中... (URL length={len(webhook)}, prefix={webhook[:45]}...)")
    send_discord_block(webhook, analyst_header, analyst_report)
    send_discord_block(webhook, strategy_header, strategy_report)
    print("✅ 完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
