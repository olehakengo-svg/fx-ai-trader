#!/usr/bin/env python3
"""
FX AI Trader — コードバグ定期チェック

使用方法:
  python3 scripts/bug_check.py              # 直近の変更を審査
  python3 scripts/bug_check.py --full       # 全戦略ファイルを審査

環境変数:
  ANTHROPIC_API_KEY     — Claude API キー（必須）
  DISCORD_WEBHOOK_URL   — Discord送信先（問題時のみ送信）

動作:
  1. flake8 で静的解析（構文・未定義変数・未使用import等）
  2. git diff で直近変更を取得
  3. LLMで意味的バグ（論理エラー・既知バグパターン）を審査
  4. 問題なし → 静粛 / 問題あり → Discord送信
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 過去Nコミット分の変更を審査
REVIEW_COMMITS = 3

# LLMに渡すdiffの最大文字数
MAX_DIFF_CHARS = 8000

# 既知の高頻度バグパターン（プロジェクト固有）
KNOWN_BUG_PATTERNS = """
このFX自動トレードシステムで過去に発生した高頻度バグパターン:

1. **NameError（未定義変数）**: `_outside_active_hours` 等、関数内で使う前に定義されていない変数。
   全エントリーが停止する致命的バグになる。

2. **QUALIFIED_TYPES 未登録**: 戦略をDaytradeEngine/ScalperEngineに追加したが
   `QUALIFIED_TYPES`（demo_trader.py）や`DT_QUALIFIED`（app.py）に追加し忘れ。
   戦略が評価されてもエントリーが常にブロックされる。

3. **None/空チェック漏れ**: `ctx.df` や `ctx.htf` が None のまま属性アクセスする。
   特に `ctx.htf.get(...)` — htfがNoneだとAttributeError。

4. **float比較の方向ミス**: `>`/`<` の逆、`>=`/`>` の混同。
   SL/TPの符号ミスが特に危険（損失方向にTPが設定される）。

5. **signalのtypo**: `"BUY"`/`"SELL"` を `"buy"`/`"sell"` と書く。
   小文字だとシグナルが正常に処理されない。

6. **Shadow/isPromoted副作用**: `_is_shadow=True` なのに `_is_promoted=True` が
   残っているとOANDA実発注される。

7. **ATR=0 ガード漏れ**: `ctx.atr <= 0` のチェックなしでATR除算するとZeroDivisionError。

8. **SL/TP符号ミス**: BUYなのにSLがentryより上、またはTPがentryより下。
"""


def run_flake8() -> tuple[bool, str]:
    """flake8で静的解析。戻り値: (問題あり, 出力)"""
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "flake8",
                "strategies/", "modules/", "app.py",
                "--max-line-length=120",
                "--extend-ignore=E501,W503,E302,E303,W291,W293,E501",
                "--select=E9,F4,F8,F9,W6",  # 致命的エラーのみ
            ],
            capture_output=True, text=True, cwd=ROOT,
        )
        output = (result.stdout + result.stderr).strip()
        return bool(output), output
    except FileNotFoundError:
        return False, "（flake8未インストール — スキップ）"


def get_recent_diff(n_commits: int = REVIEW_COMMITS) -> str:
    """直近Nコミットのgit diffを取得。"""
    try:
        result = subprocess.run(
            ["git", "diff", f"HEAD~{n_commits}..HEAD", "--", "*.py"],
            capture_output=True, text=True, cwd=ROOT,
        )
        diff = result.stdout.strip()
        return diff[:MAX_DIFF_CHARS] if len(diff) > MAX_DIFF_CHARS else diff
    except Exception as e:
        return f"（git diff失敗: {e}）"


def get_all_strategy_files() -> str:
    """全戦略ファイルの内容を結合（--full モード用）。"""
    parts = []
    for d in ["strategies/daytrade", "strategies/scalp"]:
        for f in sorted((ROOT / d).glob("*.py")):
            if f.name == "__init__.py":
                continue
            content = f.read_text(encoding="utf-8")
            parts.append(f"### {f.relative_to(ROOT)}\n{content[:2000]}")
    combined = "\n\n".join(parts)
    return combined[:MAX_DIFF_CHARS]


def review_with_llm(code_context: str, context_label: str) -> tuple[bool, str]:
    """LLMでコードを審査。戻り値: (問題あり, 審査結果)"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return False, "（ANTHROPIC_API_KEY未設定 — LLM審査スキップ）"

    if not code_context or code_context.startswith("（"):
        return False, "（審査対象コードなし）"

    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 1200,
        "system": (
            "あなたはFX自動トレードシステムの専門コードレビュアーです。\n"
            "以下の既知バグパターンに照らして、コードの問題点を指摘してください。\n\n"
            + KNOWN_BUG_PATTERNS
            + "\n\n審査の出力形式:\n"
            "- 問題なし: 「✅ 問題なし」とだけ書く\n"
            "- 問題あり: 各問題をファイル名+行番号+問題内容+深刻度（🔴致命的/🟡警告/🟢軽微）で列挙\n"
            "不確かな場合は「要確認」と書くこと。誤検知より見落としを避ける。"
        ),
        "messages": [{
            "role": "user",
            "content": f"以下の{context_label}を審査してください:\n\n```\n{code_context}\n```",
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
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode())
        result = resp["content"][0]["text"]
        has_issue = "問題なし" not in result and "✅" not in result
        return has_issue, result
    except Exception as e:
        return False, f"（LLM審査失敗: {e}）"


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
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"  ⚠️  Discord送信失敗: {e}", file=sys.stderr)


def main() -> int:
    full_mode = "--full" in sys.argv

    sections: list[str] = []
    has_any_issue = False

    # ── 1. flake8 静的解析 ──
    print("🔍 [1/2] flake8 静的解析中...")
    flake_issue, flake_output = run_flake8()
    if flake_issue:
        has_any_issue = True
        sections.append(f"**🔴 flake8 静的解析 — 問題あり**\n```\n{flake_output[:1500]}\n```")
        print(f"  ⚠️  flake8: {flake_output[:200]}")
    else:
        print(f"  ✅ flake8: {flake_output or 'クリーン'}")

    # ── 2. LLM コードレビュー ──
    print("🤖 [2/2] LLMコードレビュー中...")
    if full_mode:
        code_ctx = get_all_strategy_files()
        label = "全戦略ファイル"
    else:
        code_ctx = get_recent_diff()
        label = f"直近{REVIEW_COMMITS}コミットの変更差分"

    llm_issue, llm_output = review_with_llm(code_ctx, label)
    if llm_issue:
        has_any_issue = True
        sections.append(f"**🤖 LLMコードレビュー（{label}）— 問題あり**\n{llm_output}")
        print(f"  ⚠️  LLM審査: 問題検出")
    else:
        print(f"  ✅ LLM審査: {llm_output[:80]}")

    if not has_any_issue:
        print("✅ バグチェック完了 — 問題なし")
        return 0

    # 問題あり → Discord送信
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    message = (
        f"🐛 **FX AIトレーダー バグチェック [{now}]** — 問題が検出されました\n\n"
        + "\n\n---\n\n".join(sections)
    )

    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook:
        send_discord(webhook, message)
        print(f"⚠️ Discord送信済み")
    else:
        print("\n" + message)

    return 1


if __name__ == "__main__":
    sys.exit(main())
