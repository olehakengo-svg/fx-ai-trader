"""
Claude API client — 共通ラッパー (prompt caching対応)

Tier B-daily / Tier B-weekly / Tier C から利用。

使用:
    from modules.claude_client import call_claude, load_agent_prompt

環境変数:
    ANTHROPIC_API_KEY  (必須)
    CLAUDE_MODEL       (default: claude-sonnet-4-6)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

ROOT = Path(__file__).resolve().parent.parent


def call_claude(
    system: str,
    messages: list[dict],
    max_tokens: int = 2500,
    model: str = DEFAULT_MODEL,
    cache_system: bool = True,
) -> str:
    """Claude Messages API呼び出し。system promptは自動的にcache_control対象。

    Prompt caching はsystem prompt (agent定義 ~1-2KB) の再利用を想定。
    cache hit で入力コスト 90% 削減、TTL 5分。

    Raises:
        RuntimeError: API key未設定 or API error
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません")

    system_payload: Any = system
    if cache_system and len(system) > 500:
        system_payload = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_payload,
        "messages": messages,
    }

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            json=body,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=120,
        )
    except requests.RequestException as e:
        raise RuntimeError(f"Claude API network error: {e}") from e

    if resp.status_code != 200:
        raise RuntimeError(
            f"Claude API HTTP {resp.status_code}: {resp.text[:400]}"
        )

    data = resp.json()
    if "content" not in data or not data["content"]:
        raise RuntimeError(f"Claude API returned no content: {data}")

    return data["content"][0]["text"]


def load_agent_prompt(name: str) -> str:
    """scripts/agents/{name}.md のフロントマター除去後の本文を返す。"""
    candidates = [
        ROOT / "scripts" / "agents" / f"{name}.md",
        ROOT / ".claude" / "agents" / f"{name}.md",
    ]
    for path in candidates:
        if path.exists():
            parts = path.read_text(encoding="utf-8").split("---")
            return (parts[2] if len(parts) >= 3 else parts[-1]).strip()
    raise FileNotFoundError(f"agents/{name}.md が見つかりません")


def call_agent(
    agent_name: str,
    user_message: str,
    max_tokens: int = 2500,
) -> str:
    """エージェントプロンプト + user message の一発呼び出し。"""
    system = load_agent_prompt(agent_name)
    return call_claude(
        system=system,
        messages=[{"role": "user", "content": user_message}],
        max_tokens=max_tokens,
    )


def call_agent_json(
    agent_name: str,
    user_message: str,
    max_tokens: int = 4000,
) -> Any:
    """エージェント呼び出し結果を JSON として parse。

    LLM出力から最初の ```json ... ``` ブロック or 直接JSONを抽出。
    失敗時は raw text と共に ValueError。
    """
    raw = call_agent(agent_name, user_message, max_tokens=max_tokens)
    import re

    m = re.search(r"```(?:json)?\s*\n?(.*?)(?:\n```|$)", raw, re.DOTALL)
    blob = m.group(1) if m else raw.strip()
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        pass

    # Fallback: max_tokens で切り詰められた未閉じJSONを修復試行
    repaired = _repair_truncated_json(blob)
    if repaired is not None:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Agent {agent_name!r} did not return valid JSON. Raw output:\n{raw[:1500]}"
    )


def _repair_truncated_json(blob: str) -> str | None:
    """max_tokensで切り詰められたJSONを修復。hypotheses配列内の最後の完結要素までを残す。

    戦略:
    1. 文字列リテラルを考慮しつつ、hypotheses配列レベル (depth_obj=1, depth_arr=1) での
       最後の完結した `}` を探す
    2. そこまでを切り取って ] } で閉じる
    """
    s = blob.strip()
    depth_obj = 0
    depth_arr = 0
    in_str = False
    escape = False
    last_element_end = -1
    for i, ch in enumerate(s):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth_obj += 1
        elif ch == "}":
            depth_obj -= 1
            if depth_obj == 1 and depth_arr == 1:
                last_element_end = i
        elif ch == "[":
            depth_arr += 1
        elif ch == "]":
            depth_arr -= 1

    if last_element_end < 0:
        return None

    trimmed = s[: last_element_end + 1]
    return trimmed + "]}"
