#!/usr/bin/env python3
"""
Tier A integration: quant gate status + α budget を一枚のMarkdownで出力。

Protocol: knowledge-base/wiki/analyses/daily-tierB-protocol.md §2 (Tier A)

使用:
    python3 tools/quant_gate_status.py                     # Markdown出力
    python3 tools/quant_gate_status.py --json              # JSON出力
    python3 tools/quant_gate_status.py --to-discord        # Discord送信
    python3 tools/quant_gate_status.py --strong            # M1強定義+M3a/M3b込み (Tier A cron はこれ)

daily_report.py の直接編集を避け、独立CLIとして提供。
cron で daily_report.py の直後に実行、結果は別メッセージとしてDiscord送信する想定。

統合する情報:
    1. tools/quant_readiness.py の gate status (既存)
    2. tools/alpha_budget_tracker.py の α予算残 (新規)
    3. candidates/shadow_queue.jsonl の直近7日 pass/shadow 集計 (新規)
    4. M1 KPI (clean live 30d PnL) の読み出し (2026-09-04 追加)

⚠️ send_discord() は 1 メッセージ 1900 字上限。2026-09-10 以降はセクション境界で
最大 4 メッセージに分割送信する (--strong 追加で先頭ブロックが肥大しても既存
読み手 = Readiness / prereg watch を切り落とさないため)。**M1 は最重要 KPI
なので必ず先頭**に置くこと — 末尾に置くと読み手を足したのに誰にも届かない
(write-only の再来)。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.alpha_budget_tracker import load_state, status_summary  # noqa: E402
from tools import m1_clean_live_monitor as m1  # noqa: E402


def run_quant_readiness() -> str:
    """既存 tools/quant_readiness.py を subprocess で呼び出し。"""
    try:
        r = subprocess.run(
            ["python3", str(ROOT / "tools" / "quant_readiness.py")],
            capture_output=True, text=True, timeout=60,
        )
        return r.stdout or r.stderr or "(no output)"
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return f"(quant_readiness.py error: {e})"


def summarize_candidate_queue(days: int = 7) -> dict[str, Any]:
    path = ROOT / "knowledge-base" / "raw" / "candidates" / "shadow_queue.jsonl"
    if not path.exists():
        return {"total": 0, "pass": 0, "shadow_only": 0, "recent_names": []}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    total = 0
    passed = 0
    shadow = 0
    names: list[str] = []
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("date", "") < cutoff:
            continue
        total += 1
        if e.get("tag") == "pass":
            passed += 1
            n = e.get("hypothesis", {}).get("name")
            if n and n not in names:
                names.append(n)
        else:
            shadow += 1
    return {"total": total, "pass": passed, "shadow_only": shadow, "recent_names": names[:10]}


# 監視器自身の故障を示すマーク。Discord は 1 メッセージ 1900 字 × 最大 4 通
# (_discord_chunks) で送られ、watch 節は最後尾なので、溢れ (chunks[:4] の
# 黙った切り捨て / 単一節の hard cut) が起きた日はこの行が読み手に届かない。
# この行だけは M1 より前 (第 1 メッセージの先頭側 = 切られない位置) へ引き上げる
# (PR #227 Codex P1 — 「本文には出ているが読み手には届かない」の再発防止)。
WATCH_ALERT_MARK = "🔴🔴"


# TRIGGERED 節の見出し (prereg_trigger_watch.to_markdown と対で保つ)。
WATCH_TRIGGERED_HEADING = "### 🔴 TRIGGERED"


def extract_watch_alert(watch_text: str) -> str:
    """watch 本文から監視器故障の 1 行だけを抜き出す (無ければ空文字)。"""
    for line in (watch_text or "").splitlines():
        if line.startswith(WATCH_ALERT_MARK):
            return line.strip()
    return ""


def extract_watch_triggered(watch_text: str) -> str:
    """TRIGGERED 節 (執行/判定期日 = 要行動) を抜き出す。

    PR #227 Codex P1 12 巡目: 故障 banner だけを前方へ上げても、**行動を
    要する TRIGGERED** が 1900 字カットの外に残っていては意味がない。
    実際、2026-09-08 に復旧するまでの 2 日間、T5 第1要件 TRIGGERED は
    誰にも届いていなかった。
    """
    out: list[str] = []
    inside = False
    used = 0
    dropped = 0
    budget = TRIGGERED_SECTION_CHARS - TRIGGERED_OVERFLOW_RESERVE
    for line in (watch_text or "").splitlines():
        if line.startswith(WATCH_TRIGGERED_HEADING):
            inside = True
            out.append(line)
            used += len(line) + 1
            continue
        if inside:
            if line.startswith("###"):
                break
            if line.strip():
                # registry の message は数百字あるので、前方枠を守るため
                # id + detail 相当だけを残す (全文は下の watch 節にある)。
                entry = _clip(line.rstrip(), TRIGGERED_LINE_CHARS)
                # 行ごとの clip だけでは合計が縛れない: 220 字 × 8 件で
                # 前方枠を食い潰し、**後続の TRIGGERED と M1 節**を 1900 字
                # カットの外へ押し出す (PR #227 Codex P1 13 巡目 —
                # 「行は縛ったが合計を縛っていない」)。少なくとも 1 件は
                # 必ず出し、溢れた件数は下の watch 節へ送る。
                if out and len(out) > 1 and used + len(entry) + 1 > budget:
                    dropped += 1
                    continue
                out.append(entry)
                used += len(entry) + 1
    if dropped:
        out.append(f"- … 他 {dropped} 件の TRIGGERED は下記 watch 節 "
                   f"(前方枠 {TRIGGERED_SECTION_CHARS} 字)")
    return "\n".join(out).strip()


TRIGGERED_LINE_CHARS = 220
# 前方 (Discord 第 1 メッセージの 1900 字枠) で TRIGGERED 節に割り当てる**総量**。
# M1 は最重要 KPI なので TRIGGERED が枠を食い潰して押し出してはならない。
TRIGGERED_SECTION_CHARS = 700
# 溢れ通知行の分を先に取り置く (通知自体が枠を超えないため)。
TRIGGERED_OVERFLOW_RESERVE = 70


def _clip(line: str, limit: int) -> str:
    return line if len(line) <= limit else line[:limit - 1] + "…"


def run_prereg_trigger_watch() -> str:
    """tools/prereg_trigger_watch.py の Markdown を subprocess で取得。

    pre-reg トリガーの監視主体 (2026-07-06 導入 — T5 の 18 日執行ギャップ再発防止)。
    失敗しても daily レポート全体は落とさない。
    """
    try:
        r = subprocess.run(
            ["python3", str(ROOT / "tools" / "prereg_trigger_watch.py")],
            capture_output=True, text=True, timeout=90,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return (f"## Pre-reg Trigger Watch\n{WATCH_ALERT_MARK} "
                f"**監視器が実行不能**: {e}")
    if r.returncode != 0:
        # 2026-09-08: registry の 1 エントリ欠損で本監視器が KeyError 落ちし、
        # traceback が本文としてそのまま Discord に載っていた (2 日間、51
        # エントリ全て未監視)。returncode を無視すると「監視器が落ちた」と
        # 「監視器が異常なしと言った」が読み手にとって同じに見える。
        #
        # ただし exit 2 = 「一部エントリが EVAL_ERROR、残りは正常評価」なので
        # 本文を捨ててはならない (PR #227 Codex P1)。捨てると壊れた 1 件が
        # 他エントリの TRIGGERED を隠し、隔離ラッパが防ぐはずの盲点が
        # そのまま再現する。構造化レポートが出ていれば必ず併記する。
        err = (r.stderr or "").strip()
        if r.stdout.strip():
            banner = (f"{WATCH_ALERT_MARK} **監視器が exit {r.returncode} — "
                      "一部 trigger が評価不能 (下記 EVAL ERROR 節を見よ)**")
            body = r.stdout.strip()
            if err:
                banner += "\n```\n" + "\n".join(err.splitlines()[-6:]) + "\n```"
            return f"{banner}\n{body}"
        tail = (err or "(no output)").splitlines()[-6:]
        return ("## Pre-reg Trigger Watch\n"
                f"{WATCH_ALERT_MARK} **監視器が exit {r.returncode} で失敗 — "
                "全 trigger 未監視**\n"
                "```\n" + "\n".join(tail) + "\n```")
    return r.stdout or "(no output)"


def run_m1_readout(strong: bool = False) -> dict[str, Any]:
    """M1 KPI (clean live 30d PnL) を読み出す。

    roadmap v2.3 の最重要 KPI だが 2026-09-04 まで再計算する主体が無く、
    roadmap の M1 行は 2026-07-06 の手動実測のまま 60 日凍結されていた
    (その間に符号が反転していた)。失敗しても daily レポート全体は落とさない。

    strong=True (2026-09-10 R4(a)/(b)): 弱定義に加えて M1 強定義
    (セル定義 / book 定義の両方 + 文書間矛盾の明示) と M3a/M3b 分離 readout
    を含める。cron 側 (render.yaml fx-ai-tier-a-gate-status) は --strong で呼ぶ
    — 読み手なしの計装は禁止 (write-only 教訓) なので、強定義の計算主体と
    配信は同一コミットで配線されている。
    """
    try:
        return m1.build_report(strong=strong)
    except Exception as e:  # noqa: BLE001 - 日次レポートを落とさないための境界
        return {"error": f"{type(e).__name__}: {e}"}


def build_report(strong: bool = False) -> dict[str, Any]:
    alpha = load_state()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "m1_readout": run_m1_readout(strong=strong),
        "quant_readiness": run_quant_readiness(),
        "alpha_budget": alpha,
        "candidate_queue_7d": summarize_candidate_queue(7),
        "prereg_trigger_watch": run_prereg_trigger_watch(),
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = ["# Quant Gate Status"]
    lines.append(f"_Generated: {report['generated_at']}_")
    lines.append("")
    # 監視器の故障は M1 より先頭に置く。M1 節はセル数に比例して伸びる
    # (strategy×instrument×direction ごとに 1 行) ので、その後ろに置くと
    # セルが増えた日に第 1 メッセージ (1900 字) の外へ押し出される
    # (PR #227 Codex P1 7 巡目 — 「読み手に届く位置」は相対順序で決まる)。
    # _discord_chunks の分割送信は溢れを軽減するが、chunks[:4] の黙った
    # 切り捨てと単一節の hard cut が残るため、前方固定は依然必要。
    watch_text = report.get("prereg_trigger_watch", "")
    alert = extract_watch_alert(watch_text)
    if alert:
        lines.append("## ⚠️ Pre-reg Trigger Watch — 監視器故障")
        lines.append(alert)
        lines.append("")
    # 要行動 (TRIGGERED) も M1 より前へ。故障だけ届いて執行期日が届かないと
    # 「見えているのに動けない」になる。
    triggered = extract_watch_triggered(watch_text)
    if triggered:
        lines.append("## 🔴 Pre-reg TRIGGERED — 要行動")
        lines.append(triggered)
        lines.append("")
    # M1 は最重要 KPI なので (故障 banner / TRIGGERED の次に) 前方へ固定する。
    m1_report = report.get("m1_readout") or {}
    if m1_report.get("error"):
        lines.append("## M1 KPI (clean live 30d PnL)")
        lines.append(f"- ⚠️ 読み出し失敗: {m1_report['error']}")
    else:
        lines.append(m1.to_markdown(m1_report))
    lines.append("")
    lines.append("## Readiness")
    lines.append("```")
    lines.append(report["quant_readiness"].strip())
    lines.append("```")
    lines.append("")
    lines.append(status_summary(report["alpha_budget"]))
    lines.append("")
    lines.append("## Candidate Queue (last 7d)")
    q = report["candidate_queue_7d"]
    lines.append(f"- total entries: {q['total']}")
    lines.append(f"- pass: {q['pass']}")
    lines.append(f"- shadow_only: {q['shadow_only']}")
    if q["recent_names"]:
        lines.append(f"- recent pass names: {', '.join(q['recent_names'])}")
    lines.append("")
    lines.append(report.get("prereg_trigger_watch", "").strip())
    return "\n".join(lines)


#: Discord 1 メッセージの安全上限 (2000 のマージン込み)。
DISCORD_CHAR_LIMIT = 1900
#: 分割送信の上限メッセージ数 (webhook スパム防止)。
DISCORD_MAX_MESSAGES = 4


def _discord_chunks(
    text: str,
    limit: int = DISCORD_CHAR_LIMIT,
    max_chunks: int = DISCORD_MAX_MESSAGES,
) -> list[str]:
    """Markdown をセクション境界 (## ) 優先で ≤limit のチャンクに分割する。

    2026-09-10 (--strong 追加時): M1 強定義 + M3 で先頭ブロックが ~1900 字に
    達し、従来の text[:1900] 単発送信では Readiness / prereg watch が
    **毎日必ず切り落とされる** (= 既存読み手を殺して新読み手を足す) ため、
    複数メッセージ送信へ変更。単一セクションが limit 超の場合のみ従来通り
    hard cut (先頭優先の原則は不変)。
    """
    parts: list[str] = []
    for i, seg in enumerate(text.split("\n## ")):
        parts.append(seg if i == 0 else "## " + seg)
    chunks: list[str] = []
    cur = ""
    for part in parts:
        candidate = f"{cur}\n{part}" if cur else part
        if len(candidate) <= limit:
            cur = candidate
            continue
        if cur:
            chunks.append(cur)
        cur = part[:limit]
    if cur:
        chunks.append(cur)
    return chunks[:max_chunks]


def send_discord(text: str) -> None:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        print("DISCORD_WEBHOOK_URL not set; skipping", file=sys.stderr)
        return
    for chunk in _discord_chunks(text):
        try:
            resp = requests.post(webhook, json={"content": chunk}, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"⚠️  Discord notify failed: {e}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--to-discord", action="store_true")
    parser.add_argument("--strong", action="store_true",
                        help="M1 強定義 + M3a/M3b 分離 readout を含める (R4 修復)")
    args = parser.parse_args()

    report = build_report(strong=args.strong)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        md = to_markdown(report)
        print(md)
        if args.to_discord:
            send_discord(md)

    return 0


if __name__ == "__main__":
    sys.exit(main())
