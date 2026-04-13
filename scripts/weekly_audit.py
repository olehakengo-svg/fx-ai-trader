#!/usr/bin/env python3
"""
FX AI Trader — 週次ストラテジー監査パイプライン

使用方法:
  python3 scripts/weekly_audit.py          # 通常実行（weekly）
  python3 scripts/weekly_audit.py monthly  # 月次監査

環境変数:
  ANTHROPIC_API_KEY     — Claude API キー（必須）
  DISCORD_WEBHOOK_URL   — Discord送信先（必須）

処理フロー:
  Step 1. 本番APIからデータ取得（trades 500件 + risk + regime）
  Step 2. 戦略×ペア分解 + Kelly再計算 をClaude APIで分析
  Step 3. KB自動保存 → raw/audits/{date}-{weekly|monthly}.md
  Step 4. Discord送信
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
    "risk":   "https://fx-ai-trader.onrender.com/api/risk/dashboard",
    "regime": "https://fx-ai-trader.onrender.com/api/market/regime",
}


# ── Utilities (shared with daily_report.py) ─────────────

def fetch_json(url: str, timeout: int = 30) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FX-WeeklyAudit/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️  fetch failed: {url} — {e}", file=sys.stderr)
        return {}


def call_claude(system: str, messages: list[dict], max_tokens: int = 4000) -> str:
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
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.loads(r.read().decode())
    return resp["content"][0]["text"]


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


# ── KBコンテキスト読み込み ──────────────────────────────

def load_kb_context() -> str:
    """KBからTier分類・教訓・edge-pipelineを読み込む。"""
    sections = []
    # Tier分類
    index_path = ROOT / "knowledge-base" / "wiki" / "index.md"
    if index_path.exists():
        lines = index_path.read_text(encoding="utf-8").splitlines()[:80]
        sections.append("### KB: Tier分類・ポートフォリオ\n" + "\n".join(lines))
    # 教訓
    lessons_path = ROOT / "knowledge-base" / "wiki" / "lessons" / "index.md"
    if lessons_path.exists():
        lines = lessons_path.read_text(encoding="utf-8").splitlines()[:30]
        sections.append("### KB: 過去の教訓\n" + "\n".join(lines))
    # Edge Pipeline
    pipeline_path = ROOT / "knowledge-base" / "wiki" / "strategies" / "edge-pipeline.md"
    if pipeline_path.exists():
        lines = pipeline_path.read_text(encoding="utf-8").splitlines()[:50]
        sections.append("### KB: Edge Pipeline\n" + "\n".join(lines))
    return "\n\n".join(sections)[:3000] if sections else ""


# ── Step 2: Audit Analysis ──────────────────────────────

AUDIT_SYSTEM_PROMPT = """あなたはFX AIトレーダーシステムの独立監査クオンツアナリストです。
週次/月次の定期監査を行い、戦略パフォーマンスの客観的評価を提供します。

## 監査の目的
1. 戦略×ペアの統計を定期的に検証し、Kelly入力値のドリフトを検知する
2. Tier分類の妥当性を再評価する
3. DD防御パラメータの適切性を検証する
4. 昇格/降格候補を特定する

## 出力フォーマット（厳守）

### 1. Strategy × Pair Matrix
| Strategy | Pair | N | WR% | EV | PF | Kelly% | Trend |
で全戦略×全ペアを分解。N<10は「データ不足」として灰色表示。

### 2. Kelly Transition Readiness
- 各戦略のKelly%算出（f* = (WR × payoff - (1-WR)) / payoff）
- N>=50到達見込み日
- Kelly Half推奨ロットサイズ

### 3. Parameter Stability
- WR/EVの直近30d vs 60d比較 → 変動が±5pp以上なら警告

### 4. DD Defense Tier
- 現在DD%とlot_mult
- 推奨アクション

### 5. Tier再評価
- 現在のTier分類 vs 実データの乖離
- 昇格/降格候補（根拠付き）

### 6. 市場レジーム相関（regime dataがある場合）
- 各戦略がどのレジームで最も成績が良い/悪いか
- 現在のレジームでの推奨配分

### 7. 監査所見
- 最重要アクション（1-2件）
- リスク警告（あれば）
- 次回監査までの注視事項

## ルール
- Fidelity Cutoff以降のデータのみ使用
- N<10は判断不能として扱う
- コード変更の提案は不要。「何をすべきか」の判断のみ
- 数値は必ず根拠付きで述べる
"""


def run_audit(data: dict, audit_type: str = "weekly") -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    kb_ctx = load_kb_context()
    kb_section = f"\n\n{kb_ctx}" if kb_ctx else ""

    regime_data = data.get("regime", {})
    regime_section = ""
    if regime_data and regime_data.get("pairs"):
        regime_section = f"\n\n### MARKET REGIME\n{json.dumps(regime_data, ensure_ascii=False, indent=2)[:2000]}"

    lookback = "30日" if audit_type == "weekly" else "90日"
    user_msg = f"""# {audit_type.upper()} AUDIT — {now}

Fidelity Cutoff: {FIDELITY_CUTOFF}
分析期間: 直近{lookback}のトレードデータを対象

### STATUS
{json.dumps(data.get("status", {}), ensure_ascii=False, indent=2)[:3000]}

### TRADES（直近500件）
{json.dumps(data.get("trades", {}), ensure_ascii=False, indent=2)[:8000]}

### RISK DASHBOARD
{json.dumps(data.get("risk", {}), ensure_ascii=False, indent=2)[:2000]}{regime_section}{kb_section}

---
上記データに基づき、{audit_type}監査レポートを生成してください。
フォーマットを厳守し、全戦略×全ペアのマトリクスを含めてください。"""

    return call_claude(AUDIT_SYSTEM_PROMPT, [{"role": "user", "content": user_msg}])


# ── Step 3: KB保存 ───────────────────────────────────────

def save_to_kb(date_str: str, audit_report: str, audit_type: str) -> None:
    """監査レポートをKBに自動保存。"""
    kb_dir = ROOT / "knowledge-base" / "raw" / "audits"
    kb_dir.mkdir(parents=True, exist_ok=True)
    path = kb_dir / f"{date_str}-{audit_type}.md"
    content = (
        f"# {audit_type.title()} Audit: {date_str}\n\n"
        f"{audit_report}\n\n"
        f"## Related\n"
        f"- [[edge-pipeline]]\n"
        f"- [[changelog]]\n"
        f"- [[lessons/index]]\n"
    )
    try:
        path.write_text(content, encoding="utf-8")
        print(f"📝 KB保存: {path.relative_to(ROOT)}")
    except Exception as e:
        print(f"  ⚠️  KB保存失敗: {e}", file=sys.stderr)


# ── main ──────────────────────────────────────────────────

def main() -> int:
    audit_type = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("weekly", "monthly") else "weekly"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")

    # Step 1: データ取得
    print(f"🔍 [1/3] 本番APIからデータ取得中（{audit_type} audit）...")
    data = {k: fetch_json(url) for k, url in PRODUCTION_APIS.items()}
    failed = [k for k, v in data.items() if not v]
    if failed:
        print(f"  ⚠️  取得失敗: {', '.join(failed)}")

    # Step 2: 監査分析
    print(f"📊 [2/3] {audit_type.title()} Audit — 分析中...")
    try:
        audit_report = run_audit(data, audit_type)
    except Exception as e:
        print(f"  ❌ Audit エラー: {e}", file=sys.stderr)
        return 1

    # Step 2.5: KB自動保存
    save_to_kb(date_str, audit_report, audit_type)

    # Step 3: Discord送信 or 標準出力
    header = f"🔍 **【{audit_type.title()} Audit {date_str}】** — 戦略×ペア監査"

    if not webhook:
        print("\n" + "=" * 60)
        print(header)
        print(audit_report)
        print("=" * 60)
        print("\n⚠️  DISCORD_WEBHOOK_URL 未設定 — 標準出力に出力しました")
        return 0

    print(f"📨 [3/3] Discord に送信中...")
    send_discord_block(webhook, header, audit_report)
    print("✅ 完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
