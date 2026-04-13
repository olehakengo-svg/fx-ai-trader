#!/usr/bin/env python3
"""
FX AI Trader — 週次アルファスキャン

使用方法:
  python3 scripts/alpha_scan.py

環境変数:
  DISCORD_WEBHOOK_URL       — Discord送信先（必須）
  DISCORD_ERROR_WEBHOOK_URL — エラー通知用（任意）

処理フロー:
  Step 1. /api/demo/factors から4つの因子交差を取得
  Step 2. 結果をMarkdownフォーマットに整形
  Step 3. KB自動保存 → raw/audits/alpha-scan-YYYY-MM-DD.md
  Step 4. Discord送信（Top 3 正EV + Top 3 毒性セル）
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://fx-ai-trader.onrender.com"

FACTOR_COMBINATIONS = [
    ("strategy", "instrument"),
    ("hour", "instrument"),
    ("direction", "instrument"),
    ("direction", "regime"),
]

MIN_N = 5


# ── Utilities ────────────────────────────────────────────

def fetch_json(url: str, timeout: int = 30) -> dict:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FX-AlphaScan/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  ⚠️  fetch failed: {url} — {e}", file=sys.stderr)
        return {}


def send_discord(webhook_url: str, content: str) -> None:
    """Discord にメッセージを分割送信する。"""
    chunks: list[str] = []
    buf = ""
    for line in content.splitlines(keepends=True):
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


def send_error_notification(message: str) -> None:
    webhook = os.environ.get("DISCORD_ERROR_WEBHOOK_URL")
    if not webhook:
        return
    payload = json.dumps({"content": message[:1900]}).encode()
    req = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "FX-KB-Monitor/1.0"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"  ⚠️  Error通知送信失敗: {e}", file=sys.stderr)


# ── Cell label helper ────────────────────────────────────

def cell_label(cell: dict, factors: tuple[str, str]) -> str:
    """セルのラベルを生成する（例: "trend_follow × USD_JPY"）。"""
    f1, f2 = factors
    return f"{cell.get(f1, '?')} x {cell.get(f2, '?')}"


# ── Step 1: Fetch factor data ───────────────────────────

def fetch_all_factors() -> dict[str, list[dict]]:
    """全因子交差のデータを取得。キーは "f1 x f2" 形式。"""
    results = {}
    for f1, f2 in FACTOR_COMBINATIONS:
        key = f"{f1} x {f2}"
        url = f"{BASE_URL}/api/demo/factors?factors={f1},{f2}&min_n={MIN_N}"
        print(f"  Fetching {key}...")
        data = fetch_json(url)
        cells = data.get("cells", [])
        results[key] = cells
        print(f"    -> {len(cells)} cells")
    return results


# ── Step 2: Format to Markdown ──────────────────────────

def format_cross_table(key: str, cells: list[dict], factors: tuple[str, str]) -> str:
    """1つの因子交差テーブルをMarkdown化。"""
    f1, f2 = factors
    if not cells:
        return f"### {key}\nデータなし（min_n={MIN_N}を満たすセルが存在しない）\n"

    # EVでソート
    sorted_cells = sorted(cells, key=lambda c: c.get("ev", 0), reverse=True)

    header = f"| {f1} | {f2} | N | WR% | EV(pip) | PnL(pip) | PF |"
    sep = "|---|---|---|---|---|---|---|"
    rows = []
    for c in sorted_cells:
        n = c.get("n", 0)
        wr = c.get("win_rate", 0) * 100
        ev = c.get("ev", 0)
        pnl = c.get("total_pnl", ev * n)
        pf = c.get("profit_factor", 0)
        rows.append(
            f"| {c.get(f1, '?')} | {c.get(f2, '?')} "
            f"| {n} | {wr:.1f}% | {ev:+.2f} | {pnl:+.1f} | {pf:.2f} |"
        )

    return f"### {key}\n{header}\n{sep}\n" + "\n".join(rows) + "\n"


def build_markdown(all_data: dict[str, list[dict]], date_str: str) -> str:
    """全因子交差結果を1つのMarkdownレポートに集約。"""
    sections = [f"# Alpha Scan: {date_str}\n"]
    sections.append(f"Source: `{BASE_URL}/api/demo/factors` | min_n={MIN_N}\n")

    for (f1, f2), (key, cells) in zip(FACTOR_COMBINATIONS, all_data.items()):
        sections.append(format_cross_table(key, cells, (f1, f2)))

    # サマリー: 全セルを統合してTop正EV / Top毒性を抽出
    all_cells_with_ctx: list[tuple[dict, tuple[str, str]]] = []
    for (f1, f2), (key, cells) in zip(FACTOR_COMBINATIONS, all_data.items()):
        for c in cells:
            all_cells_with_ctx.append((c, (f1, f2)))

    if all_cells_with_ctx:
        # 正EVトップ
        by_ev = sorted(all_cells_with_ctx, key=lambda x: x[0].get("ev", 0), reverse=True)
        sections.append("## Top Positive EV Cells")
        for c, factors in by_ev[:5]:
            ev = c.get("ev", 0)
            n = c.get("n", 0)
            wr = c.get("win_rate", 0) * 100
            label = cell_label(c, factors)
            sections.append(f"- **{label}** — EV={ev:+.2f} pip, N={n}, WR={wr:.1f}%")

        # 毒性トップ
        sections.append("\n## Top Toxic Cells (negative EV)")
        toxic = sorted(all_cells_with_ctx, key=lambda x: x[0].get("ev", 0))
        for c, factors in toxic[:5]:
            ev = c.get("ev", 0)
            n = c.get("n", 0)
            wr = c.get("win_rate", 0) * 100
            label = cell_label(c, factors)
            sections.append(f"- **{label}** — EV={ev:+.2f} pip, N={n}, WR={wr:.1f}%")

    sections.append("\n## Related")
    sections.append("- [[edge-pipeline]]")
    sections.append("- [[changelog]]")
    sections.append("- [[lessons/index]]")

    return "\n".join(sections) + "\n"


# ── Step 3: Save to KB ──────────────────────────────────

def save_to_kb(date_str: str, markdown: str) -> Path:
    kb_dir = ROOT / "knowledge-base" / "raw" / "audits"
    kb_dir.mkdir(parents=True, exist_ok=True)
    path = kb_dir / f"alpha-scan-{date_str}.md"
    try:
        path.write_text(markdown, encoding="utf-8")
        print(f"📝 KB保存: {path.relative_to(ROOT)}")
    except Exception as e:
        print(f"  ⚠️  KB保存失敗: {e}", file=sys.stderr)
    return path


# ── Step 4: Discord notification ────────────────────────

def build_discord_message(
    all_data: dict[str, list[dict]], date_str: str
) -> str:
    """Top 3 正EV + Top 3 毒性セルの要約をDiscordメッセージとして生成。"""
    lines = [f"🔬 **【Alpha Scan {date_str}】** — 因子分解スキャン\n"]

    # 全セルを統合
    all_cells: list[tuple[dict, tuple[str, str]]] = []
    for (f1, f2), (key, cells) in zip(FACTOR_COMBINATIONS, all_data.items()):
        for c in cells:
            all_cells.append((c, (f1, f2)))

    if not all_cells:
        lines.append("⚠️ データ取得失敗またはセルなし")
        return "\n".join(lines)

    # 因子交差ごとの概況
    for (f1, f2), (key, cells) in zip(FACTOR_COMBINATIONS, all_data.items()):
        positive = sum(1 for c in cells if c.get("ev", 0) > 0)
        negative = sum(1 for c in cells if c.get("ev", 0) < 0)
        lines.append(f"**{key}**: {len(cells)} cells ({positive} +EV / {negative} -EV)")

    # Top 3 正EV
    by_ev = sorted(all_cells, key=lambda x: x[0].get("ev", 0), reverse=True)
    lines.append("\n✅ **Top 3 Positive EV:**")
    for c, factors in by_ev[:3]:
        ev = c.get("ev", 0)
        n = c.get("n", 0)
        wr = c.get("win_rate", 0) * 100
        label = cell_label(c, factors)
        lines.append(f"  {label} | EV={ev:+.2f} | N={n} | WR={wr:.1f}%")

    # Top 3 毒性
    toxic = sorted(all_cells, key=lambda x: x[0].get("ev", 0))
    lines.append("\n🚫 **Top 3 Toxic Cells:**")
    for c, factors in toxic[:3]:
        ev = c.get("ev", 0)
        n = c.get("n", 0)
        wr = c.get("win_rate", 0) * 100
        label = cell_label(c, factors)
        lines.append(f"  {label} | EV={ev:+.2f} | N={n} | WR={wr:.1f}%")

    lines.append(f"\n📄 KB: `audits/alpha-scan-{date_str}.md`")
    return "\n".join(lines)


# ── main ─────────────────────────────────────────────────

def main() -> int:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")

    # Step 1: Fetch
    print(f"🔬 [1/4] Factor decomposition fetch...")
    all_data = fetch_all_factors()
    empty_keys = [k for k, v in all_data.items() if not v]
    if empty_keys:
        print(f"  ⚠️  空の因子交差: {', '.join(empty_keys)}")

    total_cells = sum(len(v) for v in all_data.values())
    if total_cells == 0:
        msg = f"❌ **Alpha Scan {date_str}** — 全因子交差でセル取得失敗"
        print(msg)
        send_error_notification(msg)
        return 1

    # Step 2: Format
    print(f"📊 [2/4] Markdown整形中... ({total_cells} cells)")
    markdown = build_markdown(all_data, date_str)

    # Step 3: Save to KB
    print(f"📝 [3/4] KB保存中...")
    save_to_kb(date_str, markdown)
    send_error_notification(
        f"✅ **KB Save** (alpha-scan {date_str})\n"
        f"- audits/alpha-scan-{date_str}.md ({total_cells} cells)"
    )

    # Step 4: Discord
    discord_msg = build_discord_message(all_data, date_str)

    if not webhook:
        print("\n" + "=" * 60)
        print(discord_msg)
        print("=" * 60)
        print("\n⚠️  DISCORD_WEBHOOK_URL 未設定 — 標準出力に出力しました")
        return 0

    print(f"📨 [4/4] Discord に送信中...")
    send_discord(webhook, discord_msg)
    print("✅ 完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
